"""Notifications en haut de l'ecran : seulement celles des sauvegardes (D-228 les avait toutes retirees le 04/11/2026 a 22 h 14 ; D-230 rend celles des sauvegardes, demande de Sylfried de 23 h 02 : « Remets les notifications
pour les sauvegardes alors... »).

  1. liste blanche : chaque appel `toast(...)` du code est un message de sauvegarde (etats instantanes enregistre / charge / vide / annule / echecs, sauvegarde du jeu impossible, sauvegardes importees) ; ni vitesse de combat, ni plein
     ecran, ni memoire du moteur, ni reglages du moteur, ni son, ni ouverture de page ne s'annoncent a l'ecran ;
  2. les messages sont produits : etats (enregistrer / charger / vide, annuler le chargement, echec), echec d'ecriture d'une sauvegarde (test_save_writing), import ;
  3. `Game.toast` pose un message qui expire ; changer la vitesse de combat ne montre rien (et rend la nouvelle vitesse).

    python3 tests/test_save_notifications.py
"""
import ast, os, shutil, sys, tempfile, time, types, unittest

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
sys.path.insert(0, ROOT)
from dq4_pc import language as _LANGUAGE; _LANGUAGE.select_language('fr')          # (D-238 : ces tests attendent les textes francais, quelle que soit la langue de l'ordinateur)

ALLOWED = ('État %d enregistré', 'État %d chargé', 'État %d vide', 'Chargement annulé', 'Aucun chargement à annuler', '%s impossible : %r', 'Sauvegarde impossible', 'Sauvegardes importées')     # (début du texte de chaque appel)


def toast_calls():
    """[(fichier, ligne, texte de l'appel)] de tous les `.toast(...)` du code de dq4_pc (texte = 1er argument : chaine ou formatage d'une chaine ; None si ce n'est pas une chaine)."""
    out = []
    for folder, _d, files in os.walk(os.path.join(ROOT, 'dq4_pc')):
        for name_str in files:
            if not name_str.endswith('.py'): continue
            with open(os.path.join(folder, name_str), encoding='utf-8') as f: tree = ast.parse(f.read())
            for n in ast.walk(tree):
                if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == 'toast' and n.args:
                    a = n.args[0]
                    if isinstance(a, ast.BinOp) and isinstance(a.op, ast.Mod): a = a.left
                    if isinstance(a, ast.Call) and getattr(a.func, 'id', None) in ('tr', 'N_') and a.args: a = a.args[0]                    # (D-238 : tr('texte') % x ou N_('texte') : le texte francais est dedans)
                    out.append((name_str, n.lineno, a.value if isinstance(a, ast.Constant) and isinstance(a.value, str) else None))
    return out


class Code(unittest.TestCase):
    def test_only_save_messages_exist(self):
        calls = toast_calls(); self.assertGreaterEqual(len(calls), 8)
        for name_str, line, text in calls:
            self.assertTrue(text is not None and text.startswith(ALLOWED), '%s:%d : notification hors sauvegardes : %r' % (name_str, line, text))

    def test_everything_allowed_is_used(self):
        texts = [t for _n, _l, t in toast_calls()]
        for p in ALLOWED: self.assertTrue(any(t.startswith(p) for t in texts), p)

    def test_other_alerts_have_no_message_on_screen(self):
        for name_str in ('full_screen.py', 'battle_scene.py', 'sound.py'):
            path = os.path.join(ROOT, 'dq4_pc', 'window' if name_str != 'sound.py' else '', name_str)
            with open(path, encoding='utf-8') as f: self.assertNotIn('toast', f.read(), name_str)
        with open(os.path.join(ROOT, 'dq4_pc', 'window', 'game.py'), encoding='utf-8') as f: src = f.read()
        self.assertNotIn('alert=lambda', src)                           # (le crochet « alerte » du son n'est pas branche)
        for word in ('Mémoire du moteur', 'réglages du moteur', 'ne sont pas appliqués'): self.assertNotIn("toast('" + word, src)


class Behavior(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            from dq4_pc.window import game as F, snapshots as I
        except Exception as ex: raise unittest.SkipTest('fenetre non importable ici (%r)' % (ex,))
        cls.F, cls.I = F, I

    def fake(self):
        j = types.SimpleNamespace(msgs=[]); j.toast = lambda t, duration=1.8: j.msgs.append(t); return j

    def test_toast_expire(self):
        from dq4_pc.window import menu_display as AM
        j = types.SimpleNamespace(toasts=[]); AM.MenusMixin.toast(j, 'État 1 enregistré', 0.05)
        self.assertEqual(j.toasts[0][0], 'État 1 enregistré'); self.assertGreater(j.toasts[0][1], time.time()); time.sleep(0.07); self.assertLess(j.toasts[0][1], time.time())
        AM.MenusMixin.toast(j, 'Autre'); self.assertEqual(len(j.toasts), 1)                    # un seul message a la fois

    def test_cancel_load(self):
        j = self.fake(); j.undo_state = None
        self.assertFalse(self.I.SnapshotsMixin.cancel_loading(j)); self.assertEqual(j.msgs, ['Aucun chargement à annuler'])
        j = self.fake(); j.undo_state = {'a': 1}; j._complete_savestate = lambda: {'b': 2}; j._apply_savestate = lambda d: None
        self.assertTrue(self.I.SnapshotsMixin.cancel_loading(j)); self.assertEqual(j.msgs, ['Chargement annulé'])

    def test_savestate_failure_console_log_and_message(self):
        d = tempfile.mkdtemp(); self.addCleanup(shutil.rmtree, d, True)
        os.environ['DQ_JOURNAL_FENETRE'] = os.path.join(d, 'logs', 'window_errors.log'); self.addCleanup(os.environ.pop, 'DQ_JOURNAL_FENETRE', None)
        j = self.fake(); self.F.Game._note_state_failure(j, "Chargement de l'état 3", OSError('disque'))
        with open(os.environ['DQ_JOURNAL_FENETRE'], encoding='utf-8') as f: txt = f.read()
        self.assertIn("Chargement de l'état 3 impossible", txt); self.assertIn('disque', txt)
        self.assertEqual(len(j.msgs), 1); self.assertIn("Chargement de l'état 3 impossible", j.msgs[0]); self.assertIn('disque', j.msgs[0])

    def test_import_of_saves(self):
        from dq4_pc.window import title_screen as T
        j = self.fake(); j.saves_screen = types.SimpleNamespace(needs_reload=True); j._after_import = lambda: T.TitleMixin._after_import(j)
        T.TitleMixin._close_saves(j); self.assertIsNone(j.saves_screen); self.assertEqual(j.msgs, ['Sauvegardes importées'])
        j = self.fake(); j.saves_screen = types.SimpleNamespace(needs_reload=False); j._after_import = lambda: T.TitleMixin._after_import(j)
        T.TitleMixin._close_saves(j); self.assertEqual(j.msgs, [])                              # rien d'importe : aucun message

    def test_battle_speed_shows_nothing(self):
        from dq4_pc.window import battle_scene as SC
        from dq4_pc.persistence import settings as RG
        class Settings(dict):
            def store(self): pass
        j = self.fake(); j.reg = Settings(vitesse_combat=0); j.apply_scroll = lambda: None; j.hud = types.SimpleNamespace(visible_ones=lambda: [])
        v = SC.BattleMixin.change_battle_speed(j); self.assertEqual(v, RG.next_battle_speed(0)); self.assertEqual(j.msgs, [])


if __name__ == '__main__':
    unittest.main()
