"""Bouton de vitesse de combat (retours de 22 h 29, #47) : il ne doit jamais « apparaitre » au mauvais endroit (une image a gauche de l'ecran, ou sous le bandeau de l'equipe), et il ne doit pas se decaler quand un message
d'action remplace le menu de commandes au debut d'un tour (cadre des commandes a la largeur des dialogues).

    python3 outils/test_bouton_vitesse.py                                    (parties sans moteur : reglages, migration, ancre)
    DQ_APK=<APK patches> DQ_SAVES=<sauvegardes> outils/flux_session/moteur_slot.sh python3 -W ignore outils/test_bouton_vitesse.py
        (ajoute le vrai combat : une rencontre forcee sur la carte du monde, position du bouton a CHAQUE image dessinee du debut du combat, en fenetre 1280 x 720 sans ecran (PYGLET_HEADLESS=1))
Les sauvegardes ne sont ouvertes qu'en lecture. La « sonde » (--sonde journal.jsonl) est le programme que le test lance : une session complete de la visionneuse qui note le rectangle du bouton a chaque dessin."""
import contextlib, json, os, subprocess, sys, tempfile, types, unittest

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ICI, '..', 'dq4_pc'))
import pyglet
pyglet.options['shadow_window'] = False
if sys.platform.startswith('linux') and not os.environ.get('DISPLAY'): pyglet.options['headless'] = True
import reglages as RG
import moteur as MO
import hud_mobile as HM
try:
    import fenetre as F
except Exception as ex:
    F = None; ERREUR_IMPORT = ex

APK, SAVES = os.environ.get('DQ_APK'), os.environ.get('DQ_SAVES')
L, H = 1280, 720


def sonde(journal, images=520):
    """Lance une session (slot 4, rencontre forcee, on valide tout) et note, a chaque dessin du bouton en combat, son rectangle, le type du message et le menu actif."""
    cache = os.environ.get('DQ_UI_CACHE', '/tmp/uicache47_vitesse')
    sys.argv = ['fenetre.py', '--apk', APK, '--saves-lecture', SAVES, '--saves-ecriture', tempfile.mkdtemp(prefix='sv_bouton_'), '--reglages', os.path.join(tempfile.mkdtemp(prefix='rg_bouton_'), 'r.json'), '--slot', '4',
                '--cache', cache, '--msaa', '0', '--largeur', str(L), '--hauteur', str(H), '--sans-preparation', '--sans-son', '--shot', os.path.join(tempfile.gettempdir(), 'm_bouton.png'), '--images', '999999']
    J = {}; ini = F.Jeu.__init__
    def ini2(self, *a, **k): ini(self, *a, **k); J['j'] = self
    F.Jeu.__init__ = ini2
    out = open(journal, 'w'); dessiner = HM.Boutons.dessiner
    def dessiner2(self, visibles, edition=False, grille=True):
        j = self.J; e = j.moteur.etat
        if e.partie == MO.PARTIE_COMBAT or e.effet is not None or e.attente_charge is not None:
            r = self.rect(HM.COMBAT) if HM.COMBAT in visibles else None
            out.write(json.dumps(dict(boucle=j.n_boucle, partie=e.partie, effet=e.effet is not None, attente=e.attente_charge is not None, visible=r is not None, rect=None if r is None else [float(v) for v in r],
                                      msg=bool(j.moteur.msg_visible), type_msg=getattr(j.ui_msg, 'type', None), menu=j.moteur.menu_actif())) + '\n'); out.flush()
        return dessiner(self, visibles, edition, grille)
    HM.Boutons.dessiner = dessiner2; etat = {'force': False}
    def crochet(dt):
        j = J.get('j')
        if j is None: return
        mo = j.moteur
        if not etat['force'] and mo.etat.partie == MO.PARTIE_CHAMP and j.n > 150:
            c = mo.core; c.call(mo.E('_ZN7Encount12forceEncountEv'), c.call(mo.E('_ZN7Encount12getSingletonEv'), label='enc'), label='force'); etat['force'] = True
            j.args.script = {n: [0x4, 0x8][(n // 20) % 2] for n in range(100000)}
        if mo.etat.partie == MO.PARTIE_COMBAT: j.args.script = None
        if j.args.script_combat is None and mo.etat.partie == MO.PARTIE_COMBAT: j.args.script_combat = {n: (MO.A if (n > 60 and n % 10 == 0) else 0) for n in range(100000)}
        if j.n_boucle > images: out.close(); pyglet.app.exit()
    pyglet.clock.schedule(crochet)
    F.main()


class Cadre(unittest.TestCase):
    def test_fenetres_de_commandes_a_la_largeur_des_dialogues(self):
        r = RG.Reglages(None)
        for n in RG.FENETRES_COMMANDES_COMBAT:
            self.assertEqual(r['interface_fenetres'][n], [RG.LARGEUR_COMMANDES, 0.0, 0.0], n)
            self.assertEqual(RG.fenetre_defaut(n), (RG.LARGEUR_COMMANDES, 0.0, 0.0))
        self.assertAlmostEqual(459.0 * RG.LARGEUR_COMMANDES, 510.0, delta=0.1)          # cadre des commandes 459 unites x 1,1111 = messages d'action du combat (types 2 et 3 : 510 unites)
        self.assertEqual(RG.fenetre_defaut('RootMenu'), RG.FENETRE_DEFAUT)

    def test_retablir_remet_la_taille_par_defaut_des_commandes(self):
        r = RG.Reglages(None); r['interface_fenetres'] = {'BattleRoot': [0.7, 0.1, 0.1], 'Status': [0.8, 0.0, 0.0]}
        r.remettre_interface('BattleRoot'); self.assertEqual(r['interface_fenetres']['BattleRoot'], [RG.LARGEUR_COMMANDES, 0.0, 0.0]); self.assertEqual(r['interface_fenetres']['Status'], [0.8, 0.0, 0.0])
        r.remettre_interfaces(); self.assertEqual(r['interface_fenetres'], RG.DEFAUT['interface_fenetres'])

    def test_largeur_reelle_des_cadres(self):
        """Sur la vraie mise en page : cadre des commandes x taille par defaut = cadre des messages d'action (a un demi-unite pres)."""
        lay = os.path.join(os.environ.get('DQ_UI_CACHE', '/tmp/uicache47_vitesse'), 'ui_layout.json')
        if not os.path.exists(lay): self.skipTest('ui_layout.json absent')
        import ui_menu as UI
        ml = UI.MiseEnPage(lay, os.path.join(os.path.dirname(lay), 'ui_frameData.bin')); noms = {}
        for num, t in ml.types.items():
            if t.get('err') in (None, 'None') and t.get('nodes'): noms.setdefault(t.get('name', '').replace('Make_', '').replace('()', ''), []).append(int(num))
        fm = UI.FenetreMessage(ml); fm.regler(2, 0, False); lm = fm.etendue_x(); larg_msg = lm[1] - lm[0]
        for n in RG.FENETRES_COMMANDES_COMBAT:
            for num in noms[n]:
                cad = max(UI.Fenetre(ml, num).rects(), key=lambda r: (r[2] - r[0]) * (r[3] - r[1]))
                self.assertAlmostEqual((cad[2] - cad[0]) * RG.LARGEUR_COMMANDES, larg_msg, delta=0.6, msg=n)
                self.assertAlmostEqual((cad[0] + cad[2]) / 2 * RG.LARGEUR_COMMANDES, (lm[0] + lm[1]) / 2, delta=0.6, msg=n)           # et centre au meme endroit : meme bord gauche


class Migration(unittest.TestCase):
    def charger(self, d):
        with tempfile.TemporaryDirectory() as t:
            c = os.path.join(t, 'reglages.json')
            with open(c, 'w', encoding='utf-8') as f: json.dump(d, f)
            return RG.Reglages(c)

    def test_ancien_fichier_recoit_la_nouvelle_taille(self):
        for ancien in ({}, {'interface_fenetres': {}}, {'interface_fenetres': {'BattleRoot': [1.0, 0.0, 0.0]}}):
            r = self.charger(ancien); self.assertEqual(r['interface_v'], RG.DEFAUT['interface_v'])
            for n in RG.FENETRES_COMMANDES_COMBAT: self.assertEqual(r['interface_fenetres'][n], [RG.LARGEUR_COMMANDES, 0.0, 0.0], (ancien, n))

    def test_reglages_du_joueur_gardes(self):
        r = self.charger({'interface_fenetres': {'BattleAction': [0.8, 0.1, -0.1], 'Status': [0.7, 0.0, 0.0], 'msg': [1.5, 0.0, 0.1]}})
        self.assertEqual(r['interface_fenetres']['BattleAction'], [0.8, 0.1, -0.1]); self.assertEqual(r['interface_fenetres']['Status'], [0.7, 0.0, 0.0]); self.assertEqual(r['interface_fenetres']['msg'], [1.5, 0.0, 0.1])
        self.assertEqual(r['interface_fenetres']['BattleRoot'], [RG.LARGEUR_COMMANDES, 0.0, 0.0])

    def test_une_seule_fois(self):
        r = self.charger({'interface_v': RG.DEFAUT['interface_v'], 'interface_fenetres': {'BattleRoot': [1.0, 0.0, 0.0]}})
        self.assertEqual(r['interface_fenetres'], {'BattleRoot': [1.0, 0.0, 0.0]})          # le joueur a remis 100 % apres la migration : son choix fait foi

    def test_fichier_illisible_ou_valeur_invalide(self):
        r = self.charger({'interface_fenetres': 'n importe quoi'}); self.assertEqual(r['interface_fenetres'], {})
        self.assertEqual(RG.Reglages(None)['interface_fenetres'], RG.DEFAUT['interface_fenetres'])


@unittest.skipIf(F is None, 'fenetre.py non importable ici')
class Ancre(unittest.TestCase):
    """Fenetre factice : seules comptent la boite des messages et les fenetres de commandes ; entre deux boites l'ancre ne bouge pas ; au tout premier dessin du combat elle existe deja."""
    @staticmethod
    def faux(partie=MO.PARTIE_COMBAT):
        cadre = dict(pos=[0.0, 0.0, -338.0], vtx=[[-225.0, -100.0], [234.0, -100.0], [234.0, 30.0], [-225.0, 30.0]])
        msg = types.SimpleNamespace(N={'cadre': cadre}, bas=lambda: -338.0 - 100.0)
        def fenetre(typ, rects): return types.SimpleNamespace(typ=typ, rects=lambda: rects)
        j = types.SimpleNamespace(moteur=types.SimpleNamespace(etat=types.SimpleNamespace(partie=partie)), ui_msg=msg, ancre_combat=None, ui_suit=set(), reg={'interface_fenetres': {}}, ui_tf={},
                                  ui_g=types.SimpleNamespace(f={29: fenetre(29, [(-219.0, 255.0, -107.0, 375.0)]), 32: fenetre(32, [(-225.0, -402.0, 234.0, -144.0), (156.0, -397.0, 220.0, -335.0)])}))
        j._cachee = lambda typ: False; j._nom_de_type = lambda typ: {29: 'BattleUpStatus', 32: 'BattleAction'}.get(typ)
        j._ui_perso = lambda mode, s, v: (640.0, 400.0 * s * v[0], s * v[0])
        j.appel = lambda liste, msg, dz: F.Jeu._ancrer_vitesse_combat(j, liste, msg, dz, 1.0, 640.0, lambda cle: (400.0, 1.0), None)
        return j

    def test_le_bandeau_de_l_equipe_n_attire_pas_le_bouton(self):
        j = self.faux(); j.ui_tf = {29: (640.0, 400.0, 1.0)}
        j.appel([(0, 29)], False, 0.0)
        self.assertIsNotNone(j.ancre_combat); self.assertLess(j.ancre_combat['y'], 100.0)           # ancre de secours (boite des messages), pas le bas du bandeau (y = 655)
        avant = dict(j.ancre_combat); j.appel([(0, 29)], False, 0.0); self.assertEqual(j.ancre_combat, avant)

    def test_commandes_puis_entre_deux_boites(self):
        j = self.faux(); j.ui_tf = {29: (640.0, 400.0, 1.0), 32: (640.0, 400.0, 1.1111)}
        j.appel([(0, 29), (1, 32)], False, 0.0)
        self.assertAlmostEqual(j.ancre_combat['x'], 640.0 - 225.0 * 1.1111, places=3); self.assertAlmostEqual(j.ancre_combat['y'], 400.0 - 402.0 * 1.1111, places=3)
        commandes = dict(j.ancre_combat); j.appel([(0, 29)], False, 0.0); self.assertEqual(j.ancre_combat, commandes)           # plus de boite : l'ancre reste
        j.appel([], False, 0.0); self.assertEqual(j.ancre_combat, commandes)

    def test_hors_combat_pas_d_ancre(self):
        j = self.faux(MO.PARTIE_CHAMP); j.ancre_combat = {'x': 1.0, 'y': 2.0, 'w': None, 'h': None}; j.appel([], False, 0.0); self.assertIsNone(j.ancre_combat)

    def test_bouton_cache_tant_qu_il_n_a_pas_de_place(self):
        """Mode rattache a la boite du bas (DQ_VITESSE_ANCRE=1, defaut de #47) : le bouton n'est montre que s'il a une place."""
        J = types.SimpleNamespace(reg={'bouton_vitesse_pos': [], 'bouton_vitesse': True}, ui_msg=object(), ancre_combat=None)
        b = HM.Boutons.__new__(HM.Boutons); b.J = J
        with env_ancrage('1'):
            self.assertFalse(b._ancre_prete()); J.ancre_combat = {'x': 0.0, 'y': 0.0}; self.assertTrue(b._ancre_prete())
            J.ancre_combat = None; J.reg['bouton_vitesse_pos'] = [4.0, 6.0]; self.assertTrue(b._ancre_prete())           # place choisie par le joueur
            J.reg['bouton_vitesse_pos'] = []; J.ui_msg = None; self.assertTrue(b._ancre_prete())                       # menus simples : position de la grille


@contextlib.contextmanager
def env_ancrage(valeur):
    """DQ_VITESSE_ANCRE fixee (ou retiree : None) le temps d'un bloc."""
    ancien = os.environ.get('DQ_VITESSE_ANCRE')
    if valeur is None: os.environ.pop('DQ_VITESSE_ANCRE', None)
    else: os.environ['DQ_VITESSE_ANCRE'] = valeur
    try: yield
    finally:
        if ancien is None: os.environ.pop('DQ_VITESSE_ANCRE', None)
        else: os.environ['DQ_VITESSE_ANCRE'] = ancien


def faux_boutons(largeur=1280, hauteur=720, pos=None, ancre=None):
    """Boutons sur une fenetre factice (seuls comptent la taille de la fenetre, les reglages du bouton de vitesse et l'ancre eventuelle)."""
    J = types.SimpleNamespace(width=largeur, height=hauteur, ui_msg=object(), ancre_combat=ancre, moteur=types.SimpleNamespace(etat=types.SimpleNamespace(partie=MO.PARTIE_COMBAT)),
                              reg={'bouton_vitesse_pos': pos or [], 'bouton_vitesse': True, 'bouton_vitesse_taille': 1.0, 'boutons_pos': {}, 'boutons_taille': 1.0})
    b = HM.Boutons.__new__(HM.Boutons); b.J = J; b.edition = False; return b, J


class BordGauche(unittest.TestCase):
    """#188 (« pour le bouton d'acceleration du combat remets-le sur le bord gauche pour le moment ») : par defaut le bouton de vitesse de combat est a sa case de la grille, sur le bord gauche de l'ecran, jamais rattache a la boite
    du bas (DQ_VITESSE_ANCRE=1 redonne le rattachement de #47)."""
    ANCRE = {'x': 430.0, 'y': 30.0, 'w': 85.0, 'h': 40.0}

    def test_defaut_pas_d_ancrage(self):
        self.assertFalse(HM.ANCRAGE_VITESSE_DEF)
        with env_ancrage(None): self.assertFalse(HM.ancrage_vitesse())
        for v in ('', '  ', 'x?'):
            with env_ancrage(v): self.assertFalse(HM.ancrage_vitesse(), repr(v))                    # absente, vide ou illisible : le defaut
        for v in ('1', 'oui', 'True'):
            with env_ancrage(v): self.assertTrue(HM.ancrage_vitesse(), v)
        for v in ('0', 'non', 'False', 'FAUX'):
            with env_ancrage(v): self.assertFalse(HM.ancrage_vitesse(), v)

    def test_bord_gauche_meme_avec_une_ancre_connue(self):
        b, J = faux_boutons(ancre=self.ANCRE)
        with env_ancrage(None):
            self.assertIsNone(b.ancre()); self.assertTrue(b._ancre_prete())
            x, y, w, h = b.rect(HM.COMBAT)
            self.assertAlmostEqual(x, 0.4 * 1280 / HM.COLS, places=6); self.assertAlmostEqual(y, 720 - 8 * 720 / HM.LIGNES - h, places=6)           # case (0,4 ; 8) de la grille : bord gauche
            self.assertLess(x, 0.02 * 1280)                                                                                                       # (jamais sous la boite du bas : x ~ 380 a 460)
            self.assertEqual((w, h), (HM.PLAQUE_DQ[HM.COMBAT][0] * 720 / 800.0, HM.PLAQUE_DQ[HM.COMBAT][1] * 720 / 800.0))                       # plaque d'origine du bouton, pas celle de « Fuir »

    def test_visible_des_la_premiere_image_sans_ancre(self):
        b, J = faux_boutons(ancre=None)
        with env_ancrage(None): self.assertTrue(b._ancre_prete())
        with env_ancrage('1'): self.assertFalse(b._ancre_prete())

    def test_position_du_joueur_gardee(self):
        b, J = faux_boutons(pos=[10.0, 4.0], ancre=self.ANCRE)
        for v in (None, '1'):
            with env_ancrage(v): x, y, w, h = b.rect(HM.COMBAT); self.assertAlmostEqual(x, 10.0 * 1280 / HM.COLS, places=6)

    def test_ancrage_demande_redonne_le_rattachement(self):
        b, J = faux_boutons(ancre=self.ANCRE)
        with env_ancrage('1'):
            self.assertEqual(b.ancre(), self.ANCRE); x, y, w, h = b.rect(HM.COMBAT); self.assertAlmostEqual(x, 430.0); self.assertGreater(w, 0)

    def test_aucun_changement_hors_combat(self):
        b, J = faux_boutons(ancre=self.ANCRE); J.moteur.etat.partie = MO.PARTIE_CHAMP
        for v in (None, '1'):
            with env_ancrage(v): self.assertIsNone(b.ancre())


@unittest.skipUnless(APK and SAVES and F is not None, 'moteur reel : DQ_APK=<dossier des APK patches> DQ_SAVES=<dossier des sauvegardes>')
class CombatReel(unittest.TestCase):
    ENV = {'DQ_VITESSE_ANCRE': '1'}                                    # mode rattache a la boite du bas (defaut de #47) ; le defaut depuis #188 (bord gauche) : CombatReelBordGauche
    @classmethod
    def setUpClass(cls):
        cls.journal = os.path.join(tempfile.mkdtemp(prefix='bouton_'), 'journal.jsonl')
        env = {k: v for k, v in os.environ.items() if k != 'DQ_VITESSE_ANCRE'}; env.update(PYGLET_HEADLESS='1', PYGLET_AUDIO='silent', **cls.ENV)
        r = subprocess.run([sys.executable, '-W', 'ignore', os.path.abspath(__file__), '--sonde', cls.journal], capture_output=True, text=True, timeout=900, env=env)
        if not os.path.exists(cls.journal): raise RuntimeError('sonde sans journal : ' + r.stdout[-600:] + r.stderr[-600:])
        cls.lignes = [json.loads(l) for l in open(cls.journal)]
        cls.vues = [l for l in cls.lignes if l['visible']]

    def test_le_combat_a_ete_joue(self):
        self.assertGreater(len(self.vues), 150); self.assertTrue(any(l['effet'] for l in self.lignes)); self.assertTrue(any(l['menu'] is not None for l in self.vues)); self.assertTrue(any(l['type_msg'] in (2, 3) and l['msg'] for l in self.vues))

    def test_a_chaque_image_le_bouton_est_sous_la_boite_du_bas_a_gauche(self):
        """Toutes les images dessinees du combat (de l'ecran noir qui suit la cascade au dernier message) : bouton en bas de l'ecran, au bord gauche des boites (x de 380 a 460 pixels sur 1280)."""
        for l in self.vues:
            x, y, w, h = l['rect']; self.assertLess(y, 0.1 * H, l); self.assertTrue(380.0 < x < 460.0, l)

    def test_premiere_image_deja_au_bon_endroit(self):
        premiere = self.vues[0]; x, y, w, h = premiere['rect']; self.assertTrue(380.0 < x < 460.0 and y < 0.1 * H, premiere)           # (avant : x = 16, y = 346 pendant 4 images)

    def test_pas_de_decalage_au_debut_d_un_tour(self):
        """Le menu de commandes puis le premier message d'action (type 2 ou 3) : meme bord gauche, a une fraction de pixel pres."""
        menus = [l['rect'][0] for l in self.vues if l['menu'] is not None and not l['msg']]; actions = [l['rect'][0] for l in self.vues if l['msg'] and l['type_msg'] in (2, 3)]
        self.assertTrue(menus and actions)
        for x in menus + actions: self.assertAlmostEqual(x, menus[0], delta=1.0)


@unittest.skipUnless(APK and SAVES and F is not None, 'moteur reel : DQ_APK=<dossier des APK patches> DQ_SAVES=<dossier des sauvegardes>')
class CombatReelBordGauche(CombatReel):
    """Defaut depuis #188 (aucune variable) : a CHAQUE image dessinee du combat le bouton est sur le bord gauche de l'ecran, a sa case de la grille, et ne bouge jamais."""
    ENV = {}

    def test_a_chaque_image_le_bouton_est_sous_la_boite_du_bas_a_gauche(self):
        for l in self.vues: x, y, w, h = l['rect']; self.assertAlmostEqual(x, 0.4 * L / HM.COLS, delta=0.5, msg=l); self.assertAlmostEqual(y, H - 8 * H / HM.LIGNES - h, delta=0.5, msg=l)

    def test_premiere_image_deja_au_bon_endroit(self):
        x, y, w, h = self.vues[0]['rect']; self.assertAlmostEqual(x, 0.4 * L / HM.COLS, delta=0.5); self.assertAlmostEqual(y, H - 8 * H / HM.LIGNES - h, delta=0.5)

    def test_pas_de_decalage_au_debut_d_un_tour(self):
        xs = {round(l['rect'][0], 2) for l in self.vues}; ys = {round(l['rect'][1], 2) for l in self.vues}; self.assertEqual((len(xs), len(ys)), (1, 1))


if __name__ == '__main__':
    if '--sonde' in sys.argv:
        i = sys.argv.index('--sonde'); sonde(sys.argv[i + 1])
    else:
        unittest.main()
