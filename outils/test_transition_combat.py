"""Transition d'un combat (retour de Sylfried, 14 h 08) : « l'animation de cascade avant une rencontre ne doit pas etre modifiee par aucun accelerateur quelconque, pareil pour le fondu a la fin du combat ».

La transition = effet d'ecran de debut (la « cascade » : 57 images), ecran noir qui attend la scene, fondu d'arrivee du combat, fondus de sortie du combat, fondu de retour a la carte.
Elle doit durer EXACTEMENT ce que dure le jeu d'origine (30 images par seconde, durees des fondus telles que le moteur les demande) quels que soient :
  « Vitesse de combat » (Manuel / Normal / Rapide / Tres rapide), vitesse de marche, « Multiplicateur de l'accelerateur » (touche tenue ou non), « Vitesse de transition » (x1 a x4).

    python3 outils/test_transition_combat.py        (Linux sans ecran : pyglet en mode « headless »)
    DQ_APK=<dossier des APK patches> DQ_SAVES=<dossier des sauvegardes> python3 outils/test_transition_combat.py     (ajoute le rejeu d'un vrai combat du moteur)
Les sauvegardes ne sont ouvertes qu'en lecture : le moteur ecrit dans un dossier temporaire."""
import itertools, os, sys, tempfile, types, unittest

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ICI, '..', 'dq4_pc'))
try:
    import pyglet
    if sys.platform.startswith('linux') and not os.environ.get('DISPLAY'): pyglet.options['headless'] = True; pyglet.options['shadow_window'] = False
    import fenetre as F
except Exception as ex:
    F = None; ERREUR_IMPORT = ex
import moteur as MO
import priorite_jeu as PJ

APK, SAVES = os.environ.get('DQ_APK'), os.environ.get('DQ_SAVES')
PAS = 1.0 / 30.0
FONDU_COMBAT = 0x1000 | 30              # paquet 9 : sortie au noir en 30 images (4126, vu a la fin de chaque combat)
ENTREE_30 = 30                          # paquet 9 : entree en 30 images


def etat(partie=MO.PARTIE_CHAMP, vitesse_fondu=1.0):
    e = MO.Etat(); e.partie = partie; MO.Etat.vitesse_fondu = vitesse_fondu; return e


class Fondus(unittest.TestCase):
    def tearDown(self): MO.Etat.vitesse_fondu = 1.0

    def test_hors_combat_le_reglage_raccourcit_toujours(self):
        for vf, attendu in ((1.0, 30), (2.0, 15), (4.0, 8)):
            e = etat(MO.PARTIE_CHAMP, vf); e.appliquer([(9, [ENTREE_30], [])], lambda: ''); self.assertEqual(e.fondu['n'], attendu, 'x%g' % vf); self.assertFalse(e.fondu['combat'])
            self.assertFalse(e.transition_combat())

    def test_fondu_d_arrivee_du_combat_garde_ses_30_images(self):
        for vf in (1.0, 2.0, 3.0, 4.0):
            e = etat(MO.PARTIE_CHAMP, vf); e.appliquer([(0, [0x100], []), (9, [ENTREE_30], [])], lambda: 'btl_pl_d')           # chargement de la scene de combat (bit 8) puis fondu d'entree, meme image du moteur
            self.assertEqual(e.fondu['n'], 30, 'x%g' % vf); self.assertTrue(e.fondu['combat']); self.assertTrue(e.transition_combat())
            e.chargement = None                                                                                                      # (la retenue du dessin apres un chargement retarde le DEBUT du fondu, pas sa duree : test_chargement)
            for i in range(29): e.tick_fondu(); e.tick_transition(); self.assertTrue(e.transition_combat(), 'image %d' % i)
            e.tick_fondu(); self.assertEqual(e.fondu['n'], 0)

    def test_fondu_de_fin_de_combat_et_retour_a_la_carte(self):
        for vf in (1.0, 2.0, 4.0):
            e = etat(MO.PARTIE_COMBAT, vf); e.appliquer([(9, [FONDU_COMBAT], [])], lambda: '')
            self.assertEqual(e.fondu['n'], 30, 'x%g' % vf); self.assertTrue(e.transition_combat())
            for _ in range(30): e.tick_fondu(); e.tick_transition()
            self.assertEqual(e.fondu['n'], 0); self.assertGreater(e.garde_trans, 0); self.assertTrue(e.transition_combat())       # le moteur change de scene 1 a 3 images plus tard : l'horloge ne change pas entre les deux
            e.appliquer([(9, [0x4000 | 3], [])], lambda: ''); self.assertEqual(e.fondu_fond['n'], 3)                           # fondu du plan de fond (encore dans la partie combat) : duree du jeu
            e.tick_fondu(); e.tick_transition()
            e.partie = MO.PARTIE_CHAMP; e.fen_retour = MO.FENETRE_RETOUR_COMBAT                                                   # (Moteur.step : la partie quitte le combat)
            e.appliquer([(9, [ENTREE_30], [])], lambda: ''); self.assertEqual(e.fondu['n'], 30, 'retour x%g' % vf); self.assertTrue(e.fondu['combat'])
            for _ in range(30): self.assertTrue(e.transition_combat()); e.tick_fondu(); e.tick_transition()
            for _ in range(MO.GARDE_TRANSITION + 2): e.tick_fondu(); e.tick_transition()
            self.assertFalse(e.transition_combat())                                                                               # la transition est finie : la marche reprend ses reglages

    def test_la_fenetre_d_arrivee_s_ecoule(self):
        """Un fondu lance bien apres le chargement du combat (ou une carte ordinaire) reste soumis a « Vitesse de transition »."""
        e = etat(MO.PARTIE_CHAMP, 2.0); e.appliquer([(0, [0x100], [])], lambda: 'btl_pl_d')
        for _ in range(MO.FENETRE_ENTREE_COMBAT + 1): e.tick_transition()
        e.attente_charge = None; e.partie = MO.PARTIE_CHAMP
        e.appliquer([(9, [ENTREE_30], [])], lambda: ''); self.assertEqual(e.fondu['n'], 15); self.assertFalse(e.fondu['combat']); self.assertFalse(e.transition_combat())
        e2 = etat(MO.PARTIE_CHAMP, 2.0); e2.appliquer([(0, [0], []), (9, [ENTREE_30], [])], lambda: 'mak1f1'); self.assertEqual(e2.fondu['n'], 15)       # un changement de carte ordinaire reste raccourci
        self.assertFalse(e2.transition_combat())

    def test_fondus_de_script_et_de_couleur_inchanges(self):
        e = etat(MO.PARTIE_COMBAT, 4.0); e.appliquer([(9, [0x1000 | 0x800 | 20], [1.0, 0.0, 0.0])], lambda: ''); self.assertEqual(e.fondu['n'], 20)
        e = etat(MO.PARTIE_CHAMP, 4.0); e.appliquer([(9, [PJ.MARQUE_FONDU_SCRIPT | 0x1000 | 60], [])], lambda: ''); self.assertEqual(e.fondu['n'], 60)

    def test_etat_enregistre_avant_la_transition(self):
        e = etat(); d = dict(e.__dict__)
        for k in ('fen_entree', 'fen_retour', 'garde_trans'): d.pop(k)
        e2 = MO.Etat.__new__(MO.Etat); e2.__setstate__(d); self.assertFalse(e2.transition_combat()); self.assertEqual(e2.garde_trans, 0)
        d['fondu'] = {k: v for k, v in d['fondu'].items() if k != 'combat'}
        e3 = MO.Etat.__new__(MO.Etat); e3.__setstate__(d); self.assertFalse(e3.transition_combat())                       # (plan de fondu sans la cle 'combat')


@unittest.skipIf(F is None, 'fenetre.py non importable ici')
class Horloge(unittest.TestCase):
    @staticmethod
    def jeu(e, vitesse_combat=1.0, marche=1.0, accel=1.0, accel_tenue=False, direction=True, menu=None):
        j = types.SimpleNamespace(reg={'vitesse_combat': vitesse_combat, 'vitesse_marche': marche, 'vitesse_accel': accel})
        j.moteur = types.SimpleNamespace(etat=e, msg_visible=False, menu_actif=lambda: menu, drapeaux=lambda: 0x28, ui=types.SimpleNamespace(msg={'feed': False}))
        j.pad = lambda: MO.HAUT if direction else 0; j._tenue = lambda a: accel_tenue and a == 'accel'
        for nom in ('_horloge_combat', '_attend_joueur'): setattr(j, nom, types.MethodType(getattr(F.Jeu, nom), j))
        j.facteur = lambda: F.Jeu._facteur_vitesse(j)
        return j

    REGLAGES = list(itertools.product((0.0, 1.0, 2.0, 3.0), (1.0, 2.0, 4.0), (1.0, 1.5, 2.0), (False, True)))

    def test_cascade_ecran_noir_et_fondus_toujours_a_l_horloge_du_jeu(self):
        for vc, marche, accel, tenue in self.REGLAGES:
            e = etat(MO.PARTIE_CHAMP); e.effet = {'n': 5}
            self.assertEqual(self.jeu(e, vc, marche, accel, tenue).facteur(), 1.0, 'cascade %s' % ((vc, marche, accel, tenue),))
            e = etat(MO.PARTIE_CHAMP); e.attente_charge = {'base': 0, 'n': 1}
            self.assertEqual(self.jeu(e, vc, marche, accel, tenue).facteur(), 1.0, 'ecran noir')
            e = etat(MO.PARTIE_COMBAT); e.appliquer([(9, [FONDU_COMBAT], [])], lambda: '')
            self.assertEqual(self.jeu(e, vc, marche, accel, tenue).facteur(), 1.0, 'fondu de sortie')
            e = etat(MO.PARTIE_CHAMP); e.fen_retour = 5; e.appliquer([(9, [ENTREE_30], [])], lambda: '')
            self.assertEqual(self.jeu(e, vc, marche, accel, tenue).facteur(), 1.0, 'fondu de retour')

    def test_les_tours_du_combat_continuent_d_accelerer(self):
        for vc in (0.0, 1.0, 2.0, 3.0):
            for marche, accel, tenue in ((1.0, 1.0, False), (4.0, 2.0, True)):
                self.assertEqual(self.jeu(etat(MO.PARTIE_COMBAT), vc, marche, accel, tenue).facteur(), max(1.0, vc))                     # hors transition : la vitesse de combat s'applique
                self.assertEqual(self.jeu(etat(MO.PARTIE_COMBAT), vc, marche, accel, tenue, menu=13).facteur(), max(1.0, vc))           # (les attentes du joueur aussi : les monstres gardent leur allure)

    def test_la_marche_garde_ses_reglages_hors_transition(self):
        self.assertEqual(self.jeu(etat(MO.PARTIE_CHAMP), 3.0, 2.0, 1.5, True).facteur(), 3.0)
        self.assertEqual(self.jeu(etat(MO.PARTIE_CHAMP), 3.0, 4.0, 2.0, True).facteur(), 8.0)

    def test_le_pas_qui_declenche_la_cascade_arrete_le_rattrapage(self):
        """Marche acceleree (jusqu'a 8 pas par image) : quand un des pas leve l'effet de debut de combat, les pas restants de l'image n'ont pas a raccourcir la cascade : le rattrapage s'arrete (True = on continue)."""
        e = etat(MO.PARTIE_CHAMP); appels = []
        j = types.SimpleNamespace(moteur=types.SimpleNamespace(etat=e), _pas=lambda muet=False: appels.append(muet))
        self.assertTrue(F.Jeu._pas_terrain(j)); self.assertTrue(F.Jeu._faire_pas_combat(types.SimpleNamespace(moteur=j.moteur, _t_pas_reel=0.0, _attend_joueur=lambda: False, _pas=j._pas)))
        def lever(muet=False): e.effet = {'n': 0}
        j._pas = lever; self.assertFalse(F.Jeu._pas_terrain(j))                                       # la cascade vient de commencer pendant ce pas : stop
        self.assertTrue(F.Jeu._pas_terrain(j))                                                         # (deja en transition : on continue normalement)
        e.effet = None
        jc = types.SimpleNamespace(moteur=types.SimpleNamespace(etat=e), _t_pas_reel=0.0, _attend_joueur=lambda: False, _pas=lever)
        self.assertFalse(F.Jeu._faire_pas_combat(jc))                                                  # idem pendant un combat accelere (fondu de sortie)


@unittest.skipUnless(APK and SAVES and F is not None, 'moteur reel : DQ_APK=<dossier des APK patches> DQ_SAVES=<dossier des sauvegardes>')
class MoteurReel(unittest.TestCase):
    """Rejoue de vraies rencontres (carte du monde, rencontre forcee, attaque jusqu'a la victoire) avec « Vitesse de transition » x1, x2 et x4 : memes durees en images du moteur ; temps reel simule avec
    la vraie fonction Jeu._facteur_vitesse pour toutes les combinaisons de reglages (rien ne change d'un reglage a l'autre)."""
    @classmethod
    def setUpClass(cls):
        cls.reglages = Horloge.REGLAGES
        cls.parcours = {vf: cls.rejouer(vf) for vf in (1.0, 2.0, 4.0)}

    @classmethod
    def rejouer(cls, vitesse_fondu):
        MO.Etat.vitesse_fondu = vitesse_fondu
        mo = MO.Moteur(APK, SAVES, tempfile.mkdtemp(prefix='sv_trans_'))
        for _ in range(3): mo.step(0, 0)
        mo.charger_sauvegarde(4)
        for i in range(100): mo.step(0, 0x10 if i % 10 == 0 else 0)
        if mo.etat.partie != MO.PARTIE_CHAMP:
            mo.demarrer_champ()
            for i in range(120): mo.step(0, 0)
        c = mo.core
        c.call(mo.E('_ZN7Encount12forceEncountEv'), c.call(mo.E('_ZN7Encount12getSingletonEv'), label='enc'), label='force')
        facteurs = []; images = []; paquets9 = []                                       # une entree par pas du moteur : (facteur pour chaque combinaison de reglages), transition ?, partie
        att = 0; rel = None; fin = None; vu_combat = False
        for i in range(6000):
            p = d = 0
            if rel is not None: mo.envoyer_menu(rel, 1, -1, 0); rel = None
            port = mo.menu_actif()
            if mo.etat.partie == MO.PARTIE_COMBAT and port is not None and not mo.msg_visible:
                att += 1
                if att % 4 == 0: mo.envoyer_menu(port, 1, -1, 0x10); rel = port
            elif mo.etat.partie == MO.PARTIE_COMBAT and mo.msg_visible and mo.etat_message()[1] in (3, 5):
                att += 1
                if att > 100 and att % 4 == 0: p = d = MO.A
            else: att = 0
            if not vu_combat: p = [0x4, 0x8][(i // 20) % 2]; d = 0                    # (marche : la rencontre forcee se declenche en marchant)
            prec = mo.etat.partie; pq = mo.step(p, d); mo.ui.degats = []
            for t, a, f in pq:
                if t == 9: paquets9.append((mo.images, a[0] & 0x7ff, bool(a[0] & 0x1000), bool(a[0] & 0x4000)))
            if mo.etat.partie == MO.PARTIE_COMBAT: vu_combat = True
            e = mo.etat
            jeux = [Horloge.jeu(e, vc, marche, accel, tenue, menu=mo.menu_actif()) for vc, marche, accel, tenue in cls.reglages]
            facteurs.append([j.facteur() for j in jeux]); images.append((mo.images, e.transition_combat(), e.partie, e.effet is not None, e.attente_charge is not None))
            if vu_combat and prec == MO.PARTIE_COMBAT and e.partie != MO.PARTIE_COMBAT: fin = mo.images
            if fin and mo.images > fin + 90: break
        assert fin is not None, 'le combat ne s\'est pas termine'
        MO.Etat.vitesse_fondu = 1.0
        return dict(facteurs=facteurs, images=images, paquets9=paquets9)

    def tearDown(self): MO.Etat.vitesse_fondu = 1.0

    @staticmethod
    def segments(par):
        """Suites d'images consecutives de la transition : [(premiere image, nombre d'images, indice dans la liste)]."""
        seg = []; deb = None
        for k, (im, tr, *_r) in enumerate(par['images']):
            if tr and deb is None: deb = k
            if not tr and deb is not None: seg.append((par['images'][deb][0], k - deb, deb)); deb = None
        if deb is not None: seg.append((par['images'][deb][0], len(par['images']) - deb, deb))
        return seg

    def test_deux_transitions_par_combat(self):
        for vf, par in self.parcours.items():
            seg = self.segments(par)
            self.assertEqual(len(seg), 2, 'x%g : entree et sortie, soit 2 segments (%r)' % (vf, seg))

    def test_memes_durees_en_images_du_moteur_pour_toutes_les_vitesses_de_transition(self):
        ref = [n for _, n, _ in self.segments(self.parcours[1.0])]
        for vf in (2.0, 4.0): self.assertEqual([n for _, n, _ in self.segments(self.parcours[vf])], ref, 'Vitesse de transition x%g' % vf)
        entree, sortie = ref
        self.assertGreaterEqual(entree, MO.EFFET_COMBAT_IMAGES + 30); self.assertLess(entree, MO.EFFET_COMBAT_IMAGES + 30 + 8)                # cascade 57 + ecran noir 1 a 3 + fondu d'arrivee 30
        self.assertGreaterEqual(sortie, 60)                                                                                                   # fondu de sortie 30 + fondu de retour 30 (+ gardes)

    def test_les_fondus_demandes_par_le_moteur_sont_ceux_du_combat(self):
        """Les durees demandees (paquet 9) : 30 images pour l'arrivee, 30 pour la sortie, 30 pour le retour ; Etat les rejoue sans les raccourcir."""
        durees = [d for _, d, sortie, fond in self.parcours[1.0]['paquets9']]
        self.assertIn(30, durees); self.assertEqual(durees, [d for _, d, *_ in self.parcours[4.0]['paquets9']])

    def test_temps_reel_independant_de_tous_les_reglages(self):
        """Temps reel d'un segment = somme des 1 / (30 x facteur) de ses images ; le facteur vaut 1,0 partout : exactement images / 30 s, pour les 72 combinaisons de reglages et les 3 vitesses de transition."""
        for vf, par in self.parcours.items():
            for im0, n, k0 in self.segments(par):
                attendu = n * PAS
                for r, regl in enumerate(self.reglages):
                    t = sum(PAS / par['facteurs'][k][r] for k in range(k0, k0 + n))
                    self.assertAlmostEqual(t, attendu, 9, 'segment a l image %d, reglages %s, transition x%g' % (im0, regl, vf))

    def test_hors_transition_la_vitesse_de_combat_s_applique_toujours(self):
        par = self.parcours[2.0]
        for k, (im, tr, partie, eff, att) in enumerate(par['images']):
            if partie == MO.PARTIE_COMBAT and not tr:
                for r, (vc, marche, accel, tenue) in enumerate(self.reglages): self.assertEqual(par['facteurs'][k][r], max(1.0, vc))


if __name__ == '__main__':
    unittest.main()
