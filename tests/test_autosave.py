"""Test de la sauvegarde automatique du jeu (issue #128) : le jeu d'origine n'ecrit AUCUNE sauvegarde automatique en se fermant. Elle est ecrite par le moteur lui-meme, a deux endroits seulement
(`TownPart::initialize` et `FieldPart::initialize` de libdq4core, selon les conditions du jeu : arrivee sur la carte du monde, arrivee dans un donjon...). La visionneuse n'ajoute rien : la fermeture de la fenetre
(croix, Alt + F4, menu Quitter...) enregistre les reglages et l'historique, point. (Le code de fermeture de #124, qui forcait `AutoSave(true)` et replacait le joueur « au pixel pres », est retire.)

    python3 tools/test_autosave.py [--apk <dossier des APK patches> --saves <dossier des sauvegardes>]
(ou DQ_APK et DQ_SAVES ; sans eux seules les parties 1 et 2 tournent). La partie 3 charge le vrai moteur (environ 1 minute) : a lancer par `tools/session_flow/engine_slot.sh`.

Partie 1 (sans moteur) : plus rien dans Moteur ni dans Jeu qui force une sauvegarde automatique, ou qui surveille la console, les signaux, la fin de session.
Partie 2 (fenetre simulee) : Game.on_close ne touche pas au moteur ; le menu Quitter passe par on_close.
Partie 3 (vrai moteur) : l'arrivee en ville n'ecrit pas la banque 4 ; l'arrivee sur la carte du monde l'ecrit (le moteur seul) ; fermer la fenetre n'ecrit rien ; « Revenir a l'ecran titre » l'efface et elle ne revient pas.
"""
import argparse, hashlib, inspect, os, sys, tempfile, types, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..'))
import _paths          # (aide des tests : retrouver le code source dans les sous-dossiers de dq4_pc)
import pyglet
pyglet.options['shadow_window'] = False                     # (pas d'affichage necessaire : on ne dessine rien)
from dq4_pc.core import engine as ENGINE
from dq4_pc.window import game as F

APK = os.environ.get('DQ_APK'); SAVES = os.environ.get('DQ_SAVES'); REST = sys.argv[1:]
if __name__ == '__main__':
    _ap = argparse.ArgumentParser(); _ap.add_argument('--apk'); _ap.add_argument('--saves'); _a, REST = _ap.parse_known_args()
    APK = _a.apk or APK; SAVES = _a.saves or SAVES
PAD_A = 0x10


# ---------------------------------------------------------------------------------------------------------------------------------- 1. le code
class NothingForcesSave(unittest.TestCase):
    def test_engine_no_longer_has_forced_save(self):
        for name_str in ('sauvegarde_auto', 'sauvegarde_auto_possible', 'retour_titre_fait'):
            self.assertFalse(hasattr(ENGINE.Engine, name_str), name_str)
        self.assertNotIn('_Z8AutoSaveb', inspect.getsource(ENGINE))                                    # AutoSave n'est plus appelee par la visionneuse (le moteur l'appelle seul)
        self.assertNotIn('retour_titre_fait', inspect.getsource(ENGINE))

    def test_window_no_longer_has_special_closing(self):
        for name_str in ('_sauvegarde_fermeture', '_installer_arret_externe', '_arret_console', '_arret_externe_traiter'):
            self.assertFalse(hasattr(F.Game, name_str), name_str)
        src = _paths.source('window.py')
        for pattern in ('_event_endsession', 'SetConsoleCtrlHandler', '_arret_externe', '_arret_motif', '_auto_faite', 'DQ_SAUVEGARDE_FERMETURE', 'sauvegarde_auto'):
            self.assertNotIn(pattern, src, pattern)

    def test_loop_no_longer_looks_at_other_threads_requests(self):
        self.assertNotIn('_arret', inspect.getsource(F.Game._loop))

    def test_on_close_saves_settings_history_and_closes_sound(self):
        src = inspect.getsource(F.Game.on_close)
        self.assertTrue(src.index('self._ready') < src.index('self.reg.store()') < src.index('self.sound.shutdown()'))
        self.assertIn('self.history.store(True)', src); self.assertNotIn('engine', src)

    def test_quit_menu_goes_through_on_close(self):
        src = inspect.getsource(F.Game.quit_game); self.assertIn('self.on_close()', src); self.assertNotIn('self.close()', src)

    def test_returning_to_title_always_clears_bank_4(self):
        src = inspect.getsource(ENGINE.Engine.back_to_title); self.assertIn('killbank', src); self.assertIn('startTitle', src)


# ---------------------------------------------------------------------------------------------------------------------------------- 2. la fenetre (simulee)
class UntouchableEngine:
    """Un moteur qui leve une erreur au moindre acces : la fermeture n'a rien a lui demander."""
    def __getattr__(self, name_str): raise AssertionError('la fermeture a touche au moteur : %s' % name_str)


class FakeWindow:
    """Ce que la fermeture lit de Jeu ; la vraie methode on_close lui est liee."""
    def __init__(self, ready=True, engine=None):
        self._ready = ready; self._closed = False; self.calls = []; self.engine = engine if engine is not None else UntouchableEngine()
        self.reg = types.SimpleNamespace(store=lambda: self.calls.append('reglages'))
        self.history = types.SimpleNamespace(store=lambda force=False: self.calls.append('historique'))
        self.sound = types.SimpleNamespace(shutdown=lambda: self.calls.append('son'))
    def on_close(self):
        # (la derniere ligne de Game.on_close est super().on_close() : la fenetre de pyglet, absente ici)
        try: F.Game.on_close(self)
        except (TypeError, RuntimeError, AttributeError) as ex:
            if 'super' not in str(ex) and 'argument' not in str(ex) and 'Game' not in str(ex): raise


class SimulatedClosing(unittest.TestCase):
    def test_closing_does_not_touch_engine(self):
        J = FakeWindow(); J.on_close()
        self.assertEqual(J.calls, ['reglages', 'historique', 'son'])                                # tout ce que fait la fermeture ; aucune sauvegarde du jeu

    def test_during_logos_window_closes_without_writing_anything(self):
        J = FakeWindow(ready=False); J.on_close(); self.assertTrue(J._closed); self.assertEqual(J.calls, [])


# ---------------------------------------------------------------------------------------------------------------------------------- 3. le vrai moteur
def md5(path):
    with open(path, 'rb') as f: return hashlib.md5(f.read()).hexdigest()


@unittest.skipUnless(APK and SAVES, 'moteur reel : --apk et --saves (ou DQ_APK et DQ_SAVES)')
class RealEngine(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.wdir = tempfile.mkdtemp(prefix='sv_auto_'); cls.eng = ENGINE.Engine(APK, SAVES, cls.wdir); cls.c = cls.eng.core
        cls.f5 = os.path.join(cls.wdir, 'data5.dat')

    def step(self, n=1, p=0, d=0):
        for _ in range(n): self.eng.step(p, d); self.eng.ui.damage = []; p = d = 0

    def key_press(self, pad):
        port = self.eng.active_menu(); self.assertIsNotNone(port, 'aucun menu du moteur n\'attend de touche')
        self.eng.send_menu(port, 1, -1, pad); self.step(1); self.eng.send_menu(port, 1, -1, 0); self.step(1); self.step(8)

    def status(self):
        """Masque des banques valides (getCatalogStatus : bit 0 a 2 les journaux, 3 la suspension, 4 la sauvegarde automatique), apres relecture des fichiers (getCatalogView)."""
        self.c.call(self.c.export('_ZN7profile8SaveLoad14getCatalogViewEv')); return self.c.call(self.c.export('_ZN7profile8SaveLoad16getCatalogStatusEv')) & 0xffffffff

    def load(self, number, expected_part):
        self.assertTrue(self.eng.load_save(number)); self.step(200)
        if self.eng.state.part != expected_part: self.skipTest('la sauvegarde %d de cet echantillon n\'est pas en partie %d (%d)' % (number, expected_part, self.eng.state.part))

    def test_1_arrival_in_town_engine_does_not_write_autosave(self):
        self.assertFalse(os.path.exists(self.f5))
        self.load(1, ENGINE.PART_TOWN)
        self.assertFalse(os.path.exists(self.f5), 'le moteur ne sauvegarde pas a l\'arrivee dans une ville (TownPart::initialize : AutoSave(false) refuse)')

    def test_2_arrival_on_world_map_engine_writes_it_alone(self):
        self.load(4, ENGINE.PART_FIELD)
        self.assertTrue(os.path.isfile(self.f5), 'FieldPart::initialize appelle AutoSave(false) : la banque 4 est ecrite sans aucun appel de la visionneuse')
        self.assertEqual(os.path.getsize(self.f5), 0x3c00); self.assertTrue(self.status() & 0x10)         # la cellule « Sauvegarde automatique » du menu de depart existe

    def test_3_closing_window_writes_nothing(self):
        self.load(4, ENGINE.PART_FIELD)
        before = {f: md5(os.path.join(self.wdir, f)) for f in sorted(os.listdir(self.wdir))}
        J = FakeWindow(engine=self.eng); J.on_close()
        self.assertEqual(J.calls, ['reglages', 'historique', 'son'])
        after = {f: md5(os.path.join(self.wdir, f)) for f in sorted(os.listdir(self.wdir))}
        self.assertEqual(before, after, 'fermer la fenetre ne doit modifier aucun fichier de sauvegarde')

    def test_4_return_to_title_erases_and_nothing_restores_it(self):
        self.load(4, ENGINE.PART_FIELD); self.eng.back_to_title_state = None
        self.assertTrue(self.status() & 0x10)
        self.assertTrue(self.eng.request_return_to_title()); self.step(150)                                      # la boite Oui / Non du jeu
        self.assertEqual(self.eng.back_to_title_state, 'dialogue')
        self.key_press(PAD_A)                                                                                   # « Oui » : killbank(4) puis le fondu
        self.assertFalse(self.status() & 0x10)                                                               # la banque 4 est effacee
        for n in range(1, 140):
            self.step(1)
            if n % 10 == 0 or self.eng.state.game_map == ENGINE.TITLE_MAP: self.assertFalse(self.status() & 0x10, 'image %d (carte %s)' % (n, self.eng.state.game_map))      # fondu puis titre : rien n'est ecrit
            if self.eng.state.game_map == ENGINE.TITLE_MAP: break
        self.assertEqual(self.eng.state.game_map, ENGINE.TITLE_MAP); self.assertFalse(self.status() & 0x10)


if __name__ == '__main__':
    unittest.main(argv=[sys.argv[0]] + REST)
