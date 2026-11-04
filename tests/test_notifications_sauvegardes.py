"""Notifications en haut de l'ecran : seulement celles des sauvegardes (D-228 les avait toutes retirees le 04/11/2026 a 22 h 14 ; D-230 rend celles des sauvegardes, demande de Sylfried de 23 h 02 : « Remets les notifications
pour les sauvegardes alors... »).

  1. liste blanche : chaque appel `toast(...)` du code est un message de sauvegarde (etats instantanes enregistre / charge / vide / annule / echecs, sauvegarde du jeu impossible, sauvegardes importees) ; ni vitesse de combat, ni plein
     ecran, ni memoire du moteur, ni reglages du moteur, ni son, ni ouverture de page ne s'annoncent a l'ecran ;
  2. les messages sont produits : etats (enregistrer / charger / vide, annuler le chargement, echec), echec d'ecriture d'une sauvegarde (test_ecriture_sauvegarde), import ;
  3. `Jeu.toast` pose un message qui expire ; changer la vitesse de combat ne montre rien (et rend la nouvelle vitesse).

    python3 tests/test_notifications_sauvegardes.py
"""
import ast, os, shutil, sys, tempfile, time, types, unittest

RACINE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
sys.path.insert(0, RACINE)

PERMIS = ('État %d enregistré', 'État %d chargé', 'État %d vide', 'Chargement annulé', 'Aucun chargement à annuler', '%s impossible : %r', 'Sauvegarde impossible', 'Sauvegardes importées')     # (début du texte de chaque appel)


def appels_toast():
    """[(fichier, ligne, texte de l'appel)] de tous les `.toast(...)` du code de dq4_pc (texte = 1er argument : chaine ou formatage d'une chaine ; None si ce n'est pas une chaine)."""
    out = []
    for dossier, _d, fichiers in os.walk(os.path.join(RACINE, 'dq4_pc')):
        for nom in fichiers:
            if not nom.endswith('.py'): continue
            with open(os.path.join(dossier, nom), encoding='utf-8') as f: arbre = ast.parse(f.read())
            for n in ast.walk(arbre):
                if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == 'toast' and n.args:
                    a = n.args[0]
                    if isinstance(a, ast.BinOp) and isinstance(a.op, ast.Mod): a = a.left
                    out.append((nom, n.lineno, a.value if isinstance(a, ast.Constant) and isinstance(a.value, str) else None))
    return out


class Code(unittest.TestCase):
    def test_seuls_les_messages_de_sauvegarde_existent(self):
        appels = appels_toast(); self.assertGreaterEqual(len(appels), 8)
        for nom, ligne, texte in appels:
            self.assertTrue(texte is not None and texte.startswith(PERMIS), '%s:%d : notification hors sauvegardes : %r' % (nom, ligne, texte))

    def test_tout_ce_qui_est_permis_est_utilise(self):
        textes = [t for _n, _l, t in appels_toast()]
        for p in PERMIS: self.assertTrue(any(t.startswith(p) for t in textes), p)

    def test_les_autres_alertes_n_ont_pas_de_message_a_l_ecran(self):
        for nom in ('plein_ecran.py', 'scene_combat.py', 'son.py'):
            chemin = os.path.join(RACINE, 'dq4_pc', 'fenetre' if nom != 'son.py' else '', nom)
            with open(chemin, encoding='utf-8') as f: self.assertNotIn('toast', f.read(), nom)
        with open(os.path.join(RACINE, 'dq4_pc', 'fenetre', 'jeu.py'), encoding='utf-8') as f: src = f.read()
        self.assertNotIn('alerte=lambda', src)                           # (le crochet « alerte » du son n'est pas branche)
        for mot in ('Mémoire du moteur', 'réglages du moteur', 'ne sont pas appliqués'): self.assertNotIn("toast('" + mot, src)


class Comportement(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            from dq4_pc.fenetre import jeu as F, instantanes as I
        except Exception as ex: raise unittest.SkipTest('fenetre non importable ici (%r)' % (ex,))
        cls.F, cls.I = F, I

    def faux(self):
        j = types.SimpleNamespace(msgs=[]); j.toast = lambda t, duree=1.8: j.msgs.append(t); return j

    def test_toast_expire(self):
        from dq4_pc.fenetre import affichage_menus as AM
        j = types.SimpleNamespace(toasts=[]); AM.MenusMixin.toast(j, 'État 1 enregistré', 0.05)
        self.assertEqual(j.toasts[0][0], 'État 1 enregistré'); self.assertGreater(j.toasts[0][1], time.time()); time.sleep(0.07); self.assertLess(j.toasts[0][1], time.time())
        AM.MenusMixin.toast(j, 'Autre'); self.assertEqual(len(j.toasts), 1)                    # un seul message a la fois

    def test_annuler_le_chargement(self):
        j = self.faux(); j.etat_annul = None
        self.assertFalse(self.I.InstantanesMixin.annuler_chargement(j)); self.assertEqual(j.msgs, ['Aucun chargement à annuler'])
        j = self.faux(); j.etat_annul = {'a': 1}; j._etat_complet = lambda: {'b': 2}; j._appliquer_etat = lambda d: None
        self.assertTrue(self.I.InstantanesMixin.annuler_chargement(j)); self.assertEqual(j.msgs, ['Chargement annulé'])

    def test_echec_d_etat_console_journal_et_message(self):
        d = tempfile.mkdtemp(); self.addCleanup(shutil.rmtree, d, True)
        os.environ['DQ_JOURNAL_FENETRE'] = os.path.join(d, 'journaux', 'erreurs_fenetre.log'); self.addCleanup(os.environ.pop, 'DQ_JOURNAL_FENETRE', None)
        j = self.faux(); self.F.Jeu._noter_echec_etat(j, "Chargement de l'état 3", OSError('disque'))
        with open(os.environ['DQ_JOURNAL_FENETRE'], encoding='utf-8') as f: txt = f.read()
        self.assertIn("Chargement de l'état 3 impossible", txt); self.assertIn('disque', txt)
        self.assertEqual(len(j.msgs), 1); self.assertIn("Chargement de l'état 3 impossible", j.msgs[0]); self.assertIn('disque', j.msgs[0])

    def test_import_des_sauvegardes(self):
        from dq4_pc.fenetre import titre as T
        j = self.faux(); j.sauv = types.SimpleNamespace(a_recharger=True); j._apres_import = lambda: T.TitreMixin._apres_import(j)
        T.TitreMixin._sauv_fermer(j); self.assertIsNone(j.sauv); self.assertEqual(j.msgs, ['Sauvegardes importées'])
        j = self.faux(); j.sauv = types.SimpleNamespace(a_recharger=False); j._apres_import = lambda: T.TitreMixin._apres_import(j)
        T.TitreMixin._sauv_fermer(j); self.assertEqual(j.msgs, [])                              # rien d'importe : aucun message

    def test_vitesse_de_combat_ne_montre_rien(self):
        from dq4_pc.fenetre import scene_combat as SC
        from dq4_pc.persistance import reglages as RG
        class Reglages(dict):
            def enregistrer(self): pass
        j = self.faux(); j.reg = Reglages(vitesse_combat=0); j.appliquer_defilement = lambda: None; j.hud = types.SimpleNamespace(visibles=lambda: [])
        v = SC.CombatMixin.changer_vitesse_combat(j); self.assertEqual(v, RG.combat_suivant(0)); self.assertEqual(j.msgs, [])


if __name__ == '__main__':
    unittest.main()
