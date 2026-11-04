"""Effets d'ecran de la classe `Capture` (paquet 34, valeurs 3 : voyage / ailes de Chimere, 5 : lampe / Ranaruta, 6 : Riremito ; audit UNI-06) :

  1. modules purs (rendu/effet_tabi.py, effet_lampe.py, effet_riremito.py) : nombre d'appels de MoveNext (64, 45 a l'arrivee, 64, 63), moment ou le rendu s'allume et s'eteint, valeurs de controle lues dans la
     specification (sommets de Tabi, octets de la lampe, deplacements de Riremito), passes de flou (une par image, deux textures en alternance, la premiere lit « rien ») et tampons de dessin ;
  2. moteur (Moteur._debut_effet_ecran / _effet_ecran, sans moteur : le drapeau est simule) : bit 7 de la valeur (arrivee, matin), duree qui suit « Vitesse de transition », noir immediat de la lampe et de Riremito
     (Etat.fondu_noir_net), fondu d'entree et fin de l'ecran noir a l'arrivee d'un voyage, garde-fous, un seul effet a la fois, un etat enregistre avant le correctif.

    python3 tests/test_effets_capture.py
"""
import os, sys, types, unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import numpy as np
from dq4_pc.noyau import moteur as MO
from dq4_pc.noyau import priorite_jeu as PJ
from dq4_pc.rendu import effets_capture as EF
from dq4_pc.rendu.effet_lampe import EffetLampe
from dq4_pc.rendu.effet_riremito import EffetRiremito
from dq4_pc.rendu.effet_tabi import EffetTabi


def jouer(effet, vers=None):
    """Fait tourner l'effet jusqu'a sa fin (ou jusqu'a l'appel `vers`) ; rend la liste des (appel, rendu_actif)."""
    etats = []
    while not effet.fini and (vers is None or effet.images < vers):
        effet.etape(); etats.append((effet.images, effet.rendu_actif))
    return etats


class Durees(unittest.TestCase):
    def test_nombre_d_appels_de_move_next(self):
        for nom, fabrique, attendu in (('tabi', lambda: EffetTabi(False), 64), ('tabi_retour', lambda: EffetTabi(True), 45), ('lampe', EffetLampe, 64), ('riremito', EffetRiremito, 63)):
            e = fabrique(); etats = jouer(e)
            self.assertEqual(e.images, attendu, nom); self.assertEqual(EF.IMAGES[nom], attendu); self.assertTrue(e.fini); self.assertEqual(e.duree, attendu)
        self.assertEqual(EF.images_de('tabi', True), 45); self.assertEqual(EF.images_de('tabi', False), 64); self.assertEqual(EF.images_de('lampe', True), 64)       # (bit 7 : sans effet hors voyage)
        self.assertEqual(EF.GENRES, {3: 'tabi', 5: 'lampe', 6: 'riremito'})

    def test_le_jeu_reste_normal_les_deux_premiers_appels(self):
        for fabrique in (lambda: EffetTabi(False), EffetLampe, EffetRiremito):
            e = fabrique(); etats = jouer(e, 3)
            self.assertEqual(etats, [(1, False), (2, False), (3, True)])                              # le rendu s'allume au 3e appel (la capture a ete faite au debut du 2e)

    def test_fin_du_rendu(self):
        e = EffetTabi(False); etats = jouer(e); self.assertTrue(etats[-1][1])                          # le depart n'eteint rien : l'ecran reste noir (les deux materiaux a l'alpha 0)
        d = {n: c for n, p, u, c in e.dessins()}; self.assertTrue(np.all(d['flou'] == 0) and np.all(d['capture'] == 0))
        e = EffetTabi(True); etats = jouer(e); self.assertTrue(etats[-2][1]); self.assertFalse(etats[-1][1]); self.assertEqual(e.dessins(), [])         # l'arrivee remet le jeu : dernier appel = rendu coupe
        e = EffetLampe(); etats = jouer(e); self.assertEqual([a for a, r in etats if r], list(range(3, 64))); self.assertFalse(etats[-1][1])
        e = EffetRiremito(); etats = jouer(e); self.assertEqual([a for a, r in etats if r], list(range(3, 63))); self.assertFalse(etats[-1][1])

    def test_appels_faits_suit_la_vitesse_de_transition(self):
        self.assertEqual([EF.appels_faits(n, 64, 64) for n in (0, 1, 62, 63, 64)], [1, 2, 63, 64, 64])                       # x1 : un appel par image du moteur (le premier a l'image du paquet)
        d = PJ.duree_fondu(64, 2.0); self.assertEqual(d, 32)
        v = [EF.appels_faits(n, d, 64) for n in range(d)]
        self.assertEqual(v[0], 2); self.assertEqual(v[-1], 64); self.assertTrue(all(b >= a for a, b in zip(v, v[1:])))


class Tabi(unittest.TestCase):
    def test_sommets_de_controle(self):
        """Tableau de la specification (ecran 16/9 : 9 rangees, 170 sommets) : coin haut gauche (sommet 0) et bas droit (dernier) aux appels cites."""
        for inv, appel, s0, sn in ((False, 3, (-1.0, 1.0), (1.0, -1.0)), (False, 4, (-0.97416, 1.00887), (0.97416, -1.00887)), (False, 33, (-0.27309, 1.02490), (0.27309, -1.02490)),
                                   (False, 63, (0.18492, 0.68250), (-0.18492, -0.68250)), (True, 3, (-0.08043, 0.93937), (0.08043, -0.93937)), (True, 43, (-1.0, 1.0), (1.0, -1.0))):
            e = EffetTabi(inv, 9); self.assertEqual(e.nb, 170); jouer(e, appel)
            np.testing.assert_allclose(e._vt[0], s0, atol=2e-5, err_msg='%s appel %d' % ('arrivee' if inv else 'depart', appel)); np.testing.assert_allclose(e._vt[-1], sn, atol=2e-5)

    def test_alphas(self):
        """Montee sur 4 images (bAlpha : 0,23125 par pas au depart, cAlpha : 0,70625 puis -0,0625 par pas), puis decroissance a partir du compteur 30 (depart seulement) ; arrivee : 0,24375 / +0,0625."""
        e = EffetTabi(False); jouer(e, 3); self.assertAlmostEqual(float(e.alpha_flou), 0.23125, 5); self.assertAlmostEqual(float(e.alpha_capture), 0.70625, 5)
        jouer(e, 6); self.assertAlmostEqual(float(e.alpha_flou), 0.925, 5); self.assertAlmostEqual(float(e.alpha_capture), 0.51875, 5)
        jouer(e); self.assertEqual(float(e.alpha_capture), 0.0); self.assertAlmostEqual(float(e.alpha_flou), 0.6925, 4)                  # cAlpha tombe a 0 avant la fin, bAlpha pas
        a = EffetTabi(True); jouer(a, 6); self.assertAlmostEqual(float(a.alpha_flou), 0.975, 5); self.assertAlmostEqual(float(a.alpha_capture), 0.25, 5); jouer(a, 44); self.assertAlmostEqual(float(a.alpha_flou), 0.975, 5)

    def test_maillage_du_mobile_par_defaut(self):
        """28 rangees (m_divY = 56 de l'ecran portrait d'origine) : 17 x 29 sommets, 2 x 16 x 28 triangles ; les uv couvrent la capture."""
        e = EffetTabi(False); self.assertEqual((e.lignes, e.nb), (28, 17 * 29)); jouer(e, 3)
        nom, pos, uv, rgba = e.dessins()[1]; self.assertEqual(nom, 'capture'); self.assertEqual(pos.shape, (2 * 3 * 16 * 28, 2)); self.assertEqual(uv.shape, pos.shape)
        self.assertEqual((float(uv.min()), float(uv.max())), (0.0, 1.0)); self.assertLessEqual(float(np.abs(pos).max()), 1.0 + 1e-5)         # a l'appel 3 : la grille est reguliere, tout l'ecran


class Lampe(unittest.TestCase):
    def suivre(self, matin):
        l = EffetLampe(matin); suite = []
        while not l.fini:
            l.etape()
            if l.rendu_actif: suite.append((int(l.cl[3, 8, 0 if not matin else 2]), int(l.cl[3, 0, 0 if not matin else 2]), float(l.bias), l.cl[3, 8].tolist(), l.cl[3, 0].tolist()))
        return l, suite

    def test_valeurs_de_la_nuit(self):
        l, s = self.suivre(False); c8 = [x[0] for x in s]; c0 = [x[1] for x in s]
        self.assertEqual(c8[:9], [251, 246, 240, 233, 225, 216, 206, 195, 183]); self.assertEqual(c8.index(0), 19)                         # colonne centrale : tombe a 0 au compteur 19
        self.assertEqual(c0[0], 254); self.assertEqual(c0.index(0), 57)                                                                       # colonnes du bord : tres lentement, 0 au compteur 57
        self.assertEqual(s[0][3], [251, 251, 255, 255]); self.assertEqual(s[-1][3], [0, 0, 255, 255])                                       # nuit : rouge et vert baissent, bleu (et alpha) restent a 255
        self.assertAlmostEqual(min(x[2] for x in s), 0.5880126953125, 12); self.assertAlmostEqual(max(x[2] for x in s), 1.091552734375, 12)         # « paupiere » : bias de 1 a 0,588 (compteur 27), puis jusqu'a 1,09
        self.assertAlmostEqual(float(l.b_alpha), 0.875, 5); self.assertAlmostEqual(float(l.c_alpha), 0.8125, 5); self.assertEqual(float(l.fade), 0.0)

    def test_valeurs_du_matin(self):
        l, s = self.suivre(True)
        self.assertEqual([x[3] for x in s[:4]], [[255, 255, 255, 255], [255, 255, 254, 255], [255, 255, 252, 255], [255, 255, 249, 255]])           # matin : seul le bleu baisse (teinte jaune) ; cbias part de 0 : rien n'est retire a la 1re mise a jour
        self.assertEqual(s[-1][3], [255, 255, 0, 255]); self.assertTrue(0 < s[-1][4][2] <= 8)                                                      # fin : centre a 0, colonnes du bord jamais a 0 (7)
        self.assertEqual(s[0][0], 255)

    def test_pincement(self):
        """Colonnes 0 et 16 : y inchange ; rangee du haut (y = 1) : la colonne centrale prend la valeur de `bias`, sa voisine 0,1 + 0,9 bias ; `bias` oscille entre 0,588 et 1,09."""
        l = EffetLampe(False); vus = []; orig = l._maj
        def maj(): vus.append(float(l.bias)); orig()
        l._maj = maj; jouer(l, 3 + 28)
        self.assertEqual(l.counter, 28)
        np.testing.assert_array_equal(l.g[:, 0, 1], l.pt); np.testing.assert_array_equal(l.g[:, 16, 1], l.pt)
        self.assertAlmostEqual(float(l.g[0, 8, 1]), vus[-1], 5); self.assertAlmostEqual(float(l.g[0, 7, 1]), 0.1 + 0.9 * vus[-1], 5); self.assertAlmostEqual(float(l.g[0, 9, 1]), float(l.g[0, 7, 1]), 7)
        self.assertEqual(l.h_div_y, 14); self.assertEqual(l.g.shape, (15, 17, 3)); self.assertAlmostEqual(min(vus), 0.5880126953125, 12)


class Riremito(unittest.TestCase):
    def test_deplacements_a_la_derniere_mise_a_jour(self):
        r = EffetRiremito(); jouer(r, 2 + 59); self.assertEqual(r.compteur, 59)
        moy = [r.vt[4 * i:4 * i + 4, :2].mean(0) for i in range(4)]                                                                           # centre de chaque copie : (+-3 u, +-u), u = 0,0005 (i + 1) c
        np.testing.assert_allclose(moy, [(0.0885, -0.0295), (0.177, 0.059), (-0.2655, 0.0885), (-0.354, -0.118)], atol=1e-5)
        self.assertAlmostEqual(float(r.rot), 6.49, 4)                                                                                         # 0,11 degre par image
        np.testing.assert_allclose(r.mat_fond, (0.9, 0.9, 0.9, 1.0), atol=1e-6); np.testing.assert_allclose(r.mat_capture, (0.0, 0.0, 0.0, 0.18), atol=1e-6)      # fond (b, b, b, 1) ; copies : noircies, opacite 0,18

    def test_premier_pas_et_noircissement(self):
        r = EffetRiremito(); jouer(r, 3)
        np.testing.assert_allclose(r.vt[0:4, :2].mean(0), (0.0015, -0.0005), atol=1e-6); np.testing.assert_allclose(r.mat_capture, (1, 1, 1, 0.82), atol=1e-6)      # c = 1 : u = 0,0005, copie 0 vers la droite et le bas
        jouer(r, 2 + 29); self.assertEqual(r.compteur, 29); self.assertEqual(float(r.fade), 1.0)
        jouer(r, 2 + 30); self.assertAlmostEqual(float(r.fade), 1 - 1 / 30, 6)                                                                # le noircissement commence au compteur 30


class Flou(unittest.TestCase):
    def test_passes_de_flou(self):
        """La passe a lieu avant chaque appel tant que SetBlur est vrai (a partir du 2e) ; deux textures en alternance ; la premiere passe lit « rien » ; le rendu repasse sur l'etat de l'image PRECEDENTE."""
        for fabrique, derniere in ((lambda: EffetTabi(False), 64), (EffetLampe, 63), (EffetRiremito, 62)):
            e = fabrique(); vu = []
            e.sur_flou = lambda ef, i: vu.append((ef.images + 1, i, ef.flou_lu, bool(ef.dessins())))
            jouer(e)
            self.assertEqual([a for a, i, l, d in vu], list(range(2, derniere + 1)))
            self.assertEqual([i for a, i, l, d in vu], [k % 2 for k in range(len(vu))]); self.assertIsNone(vu[0][2]); self.assertEqual([l for a, i, l, d in vu[1:]], [1 - i for a, i, l, d in vu[1:]])
            self.assertFalse(vu[0][3]); self.assertFalse(vu[1][3]); self.assertTrue(vu[2][3])               # appels 2 et 3 : le rendu n'est pas encore allume dans l'etat de l'image precedente

    def test_tampons_de_dessin(self):
        """Fond d'abord (texture floue x couleur, remplace l'ecran), puis la capture ; positions en coordonnees d'ecran normalisees ; une couleur par sommet."""
        for e in (EffetTabi(False), EffetLampe(False), EffetLampe(True), EffetRiremito()):
            self.assertEqual(e.dessins(), []); jouer(e, 20); d = e.dessins()
            self.assertEqual([n for n, p, u, c in d], ['flou', 'capture'])
            for n, p, u, c in d: self.assertEqual((p.shape[1], u.shape[1], c.shape[1]), (2, 2, 4)); self.assertEqual(len(p), len(u)); self.assertEqual(len(p), len(c)); self.assertTrue(np.isfinite(p).all())
            np.testing.assert_array_equal(d[0][1], [(-1, 1), (1, 1), (-1, -1), (1, 1), (1, -1), (-1, -1)])              # fond : l'ecran entier
            self.assertEqual(len(d[0][1]), 6)
        e = EffetRiremito(); jouer(e, 20); self.assertEqual(len(e.dessins()[1][1]), 24)                                 # quatre copies
        e = EffetLampe(False); jouer(e, 5); r = e.dessins()[1][3]; self.assertTrue(np.all(r[:, 2] == 1.0)); jouer(e, 40); self.assertTrue(np.all(e.dessins()[1][3][:, 3] == e.mat_grille[3]))


def moteur_faux(vitesse=1.0):
    MO.Etat.vitesse_fondu = vitesse; e = MO.Etat(); drapeau = []
    return types.SimpleNamespace(etat=e, _drapeau_effet=lambda a: drapeau.append(a), drapeau=drapeau, images=0)


def lancer(mo, valeur):
    MO.Moteur._debut_effet_ecran(mo, valeur)


def pas(mo):
    MO.Moteur._effet_ecran(mo); mo.images += 1; mo.etat.tick_fondu()


class Moteur(unittest.TestCase):
    def tearDown(self): MO.Etat.vitesse_fondu = 1.0

    def test_valeurs_du_paquet(self):
        for valeur, genre, inverse, matin, images in ((3, 'tabi', False, False, 64), (0x83, 'tabi', True, False, 45), (5, 'lampe', False, False, 64), (0x85, 'lampe', False, True, 64), (6, 'riremito', False, False, 63), (0x86, 'riremito', False, False, 63)):
            mo = moteur_faux(); lancer(mo, valeur); ef = mo.etat.effet_ecran
            self.assertEqual((ef['genre'], ef['inverse'], ef['matin'], ef['images'], ef['duree'], ef['n']), (genre, inverse, matin, images, images, 0), hex(valeur)); self.assertEqual(mo.drapeau, [True])
        for valeur in (0, 1, 2, 4, 7, 0x84):
            mo = moteur_faux(); lancer(mo, valeur); self.assertIsNone(mo.etat.effet_ecran, hex(valeur)); self.assertEqual(mo.drapeau, [])        # 4 : debut de combat (autre effet, Moteur._debut_effet_combat)
        mo = moteur_faux(); lancer(mo, 5); lancer(mo, 6); self.assertEqual(mo.etat.effet_ecran['genre'], 'lampe'); self.assertEqual(mo.drapeau, [True])              # un seul effet a la fois

    def test_le_drapeau_retombe_apres_la_duree(self):
        for valeur, images in ((3, 64), (0x83, 45), (5, 64), (6, 63)):
            for vitesse in (1.0, 2.0, 4.0):
                mo = moteur_faux(vitesse); lancer(mo, valeur); d = PJ.duree_fondu(images, vitesse); self.assertEqual(mo.etat.effet_ecran['duree'], d); n = 0
                while mo.etat.effet_ecran is not None: self.assertEqual(mo.drapeau, [True]); pas(mo); n += 1
                self.assertEqual(n, d, 'valeur %s x%g' % (hex(valeur), vitesse)); self.assertEqual(mo.drapeau, [True, False])
        self.assertFalse(moteur_faux().etat.transition_combat())                                                                    # (ce n'est pas la transition d'un combat)
        mo = moteur_faux(); lancer(mo, 3); self.assertFalse(mo.etat.transition_combat()); self.assertIsNone(mo.etat.effet)

    def test_noir_immediat_de_la_lampe_et_de_riremito(self):
        for valeur, appel in ((5, 63), (6, 62)):
            mo = moteur_faux(); lancer(mo, valeur); self.assertEqual(mo.etat.fondu['a'], 0.0); n = 0
            while mo.etat.effet_ecran is not None:
                pas(mo); n += 1
                self.assertEqual(mo.etat.fondu['a'], 1.0 if n + 1 >= appel else 0.0, (valeur, n))                                   # appel d'origine = n + 1 (le premier a l'image du paquet)
            self.assertEqual((mo.etat.fondu['a'], mo.etat.fondu['n'], mo.etat.fondu['col']), (1.0, 0, (0.0, 0.0, 0.0))); self.assertFalse(mo.etat.fondu_en_cours())          # opaque, noir, immediat ; il reste ainsi
            self.assertIsNone(mo.etat.ecran_noir)

    def test_voyage_depart_arrivee(self):
        mo = moteur_faux(); lancer(mo, 3)
        for _ in range(63): pas(mo); self.assertIsNone(mo.etat.ecran_noir)
        pas(mo); self.assertIsNone(mo.etat.effet_ecran); self.assertEqual(mo.etat.ecran_noir, {'n': 0})                              # fin du depart : l'ecran reste noir
        for _ in range(100): pas(mo)
        self.assertEqual(mo.etat.ecran_noir['n'], 100); self.assertEqual(mo.etat.fondu['a'], 0.0)                                    # (le noir n'est pas un plan de fondu : l'interface reste dessinee)
        mo.etat.fondu['a'] = 0.5; lancer(mo, 0x83)
        for n in range(1, 46):
            pas(mo)
            if n == 1: self.assertEqual(mo.etat.fondu['n'], 0)
            if n == 2: self.assertEqual((mo.etat.fondu['n'], round(mo.etat.fondu['pas'], 6), mo.etat.fondu['fin']), (EF.FONDU_ENTRANT - 1, round(-0.5 / 30, 6), 0.0))     # Fade.SetFadeIn(30) a l'appel 3 : de l'opacite courante a 0 (30 images, une deja ecoulee a la fin de cette image)
            if n < 44: self.assertIsNotNone(mo.etat.ecran_noir, n)
            if n == 44: self.assertIsNone(mo.etat.ecran_noir); self.assertIsNotNone(mo.etat.effet_ecran)                             # dernier appel (etat 4) : la scene reparait ; le drapeau retombe a l'image suivante
        self.assertIsNone(mo.etat.effet_ecran); self.assertEqual(mo.drapeau, [True, False, True, False])

    def test_fondu_d_entree_depuis_un_plan_transparent(self):
        e = MO.Etat(); e.fondu_entree_courant(30); self.assertEqual((e.fondu['a'], e.fondu['n'], e.fondu['pas']), (0.0, 30, -0.0))
        for _ in range(30): e.tick_fondu()
        self.assertEqual((e.fondu['a'], e.fondu['n']), (0.0, 0)); self.assertFalse(e.fondu_en_cours())

    def test_garde_fous_de_l_ecran_noir(self):
        mo = moteur_faux(); mo.etat.ecran_noir = {'n': 0}
        for _ in range(MO.ECRAN_NOIR_MAX): pas(mo)
        self.assertIsNotNone(mo.etat.ecran_noir); pas(mo); self.assertIsNone(mo.etat.ecran_noir)                                        # jamais d'arrivee : le jeu est rouvert au bout de 60 s
        for cond in ({'carte': MO.CARTE_TITRE}, {'partie': MO.PARTIE_DEPART}):
            mo = moteur_faux(); mo.etat.ecran_noir = {'n': 0}
            for k, v in cond.items(): setattr(mo.etat, k, v)
            pas(mo); self.assertIsNone(mo.etat.ecran_noir, cond)                                                                    # retour au titre : plus de noir

    def test_etat_enregistre_avant_le_correctif(self):
        e = MO.Etat(); e.__dict__.pop('effet_ecran', None); e.__dict__.pop('ecran_noir', None); self.assertIsNone(e.effet_ecran); self.assertIsNone(e.ecran_noir)      # attributs de classe


if __name__ == '__main__':
    unittest.main(verbosity=2)
