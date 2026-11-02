"""Test de la logique pure des objets animes des cartes (sans fenetre, sans moteur, sans APK) : orientation propre des objets et sens des animations (coffres, tiroirs, portes) :

  1. `donnees.euler_mat` = FldObject.rotateXZY (0xCD47F0) : q = (AngleAxis(ry, haut) * AngleAxis(-rz, avant)) * AngleAxis(-rx, droite) : X appliquee d'abord, puis Z, puis Y (le cap en dernier).
     Re-calcule a part avec le produit de quaternions de Unity (celui du desassemblage : R = q2 * q3 puis R * q1) ;
  2. coffre qui s'ouvre (couvercle : mouvement commun, rotation -60 en X) : le couvercle pivote autour de la charniere DU COFFRE, quel que soit son cap (0, 90, -90, 180, -27 degres : tous les coffres de la
     meme famille s'ouvrent « vers l'arriere du coffre », jamais de cote), et a la meme vitesse ;
  3. tiroir (mouvement commun avec une cle de position) : le deplacement est dans le repere de l'objet (FldObject.c_pmv_func : MultiplyPoint(TRS(position, rotateXZY(rotation), echelle)) ; un
     mouvement ordinaire (pmv_func) ajoute le deplacement tel quel ;
  4. porte (rotation autour de Y seulement) : inchangee (cap de la porte + cap du mouvement) ;
  5. (si le cache de cartes existe : DQ_CACHE_CARTES, sinon /tmp/uicache_coffres) les VRAIS objets : les 194 coffres, les tiroirs et des portes de toutes les cartes.

    python3 outils/test_objets_carte.py
"""
import math, os, sys, unittest

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'dq4_pc'))
from donnees import euler_mat
import objets_carte as OC


# ---- reference independante : quaternions de Unity
def qaxe(angle_deg, axe):
    a = math.radians(angle_deg) / 2; s = math.sin(a); return np.array([axe[0] * s, axe[1] * s, axe[2] * s, math.cos(a)])      # (x, y, z, w)


def qmul(a, b):
    """Produit de Hamilton a * b (b appliquee d'abord), (x, y, z, w) : formules du desassemblage."""
    ax, ay, az, aw = a; bx, by, bz, bw = b
    return np.array([aw * bx + ax * bw + ay * bz - az * by, aw * by - ax * bz + ay * bw + az * bx, aw * bz + ax * by - ay * bx + az * bw, aw * bw - ax * bx - ay * by - az * bz])


def qmat(q):
    x, y, z, w = q
    return np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)], [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)], [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])


def rotate_xzy_jeu(rx, ry, rz):
    """FldObject.rotateXZY lue au desassemblage : q1 = AngleAxis(-rx, droite), q2 = AngleAxis(ry, haut), q3 = AngleAxis(-rz, avant) ; R = q2 * q3 ; resultat = R * q1."""
    q1 = qaxe(-rx, (1, 0, 0)); q2 = qaxe(ry, (0, 1, 0)); q3 = qaxe(-rz, (0, 0, 1))
    return qmat(qmul(qmul(q2, q3), q1))


def ry_mat(deg):
    b = math.radians(deg); return np.array([[math.cos(b), 0, math.sin(b)], [0, 1, 0], [-math.sin(b), 0, math.cos(b)]])


# ---- cartes minuscules
def carte_objet(pos, rot, pts_locaux, cles, flag_mouvement=4, scl=(1.0, 1.0, 1.0), fin=10):
    """Une carte d'un objet : sommets `pts_locaux` (repere du modele) cuits a la position / rotation / echelle d'origine, une table d'animations communes a 4 entrees dont la 2e (numero 2) est
    un mouvement a deux cles (image 0 : rien ; image `fin` : `cles`)."""
    pts = np.array(pts_locaux, np.float64)
    monde = (np.array(pos, np.float64) + (euler_mat(*rot) @ np.diag(scl) @ pts.T).T).astype(np.float32)
    n = len(pts)
    ident = ((0.0, 0.0, 0.0), (0.0, 0.0, 0.0), (1.0, 1.0, 1.0))
    def mot(derniere): return dict(flag=flag_mouvement, nkey=2, repeat=1, delai=0, rdelai=0, fin=fin, keys=[(0,) + ident, (fin,) + derniere])
    mots = [mot(ident), mot(cles), mot(cles), mot(ident)]
    mots[0]['fin'] = 2; mots[0]['keys'] = [(0,) + ident, (2,) + ident]
    obj = dict(i=0, pos=tuple(pos), rot=tuple(rot), scl=tuple(scl), mdl=1, canim=0, flag=0, seqobj=-1, pmv=-1, id=0, com=0, uid=0, prio=0, rest='')
    return {'objets': [obj], 'groupes': {'k': (monde, np.zeros((n, 2), np.float32), np.ones((n, 4), np.float32))}, 'plages': {0: [('k', 0, n)]}, 'var': {},
            'tabs': [[(1, -1, 0), (1, -1, 1), (1, -1, 2), (1, -1, 3)]], 'mots': mots, 'seqs': [], 'seqent': [], 'imgobj': {}}


def jouer(c, no=2, images=20):
    oc = OC.ObjetsCarte(c)
    oc.anim_commune(0, no)
    for _ in range(images): oc.tick()
    return oc.cur['k'].astype(np.float64)


# couvercle de coffre : charniere le long de l'axe X local (au pied du modele : origine = charniere), s'etend vers l'avant du coffre (-Z local), un peu d'epaisseur (Y)
COUVERCLE = [(-0.4, 0, 0), (0.4, 0, 0), (-0.4, 0, -0.6), (0.4, 0, -0.6), (-0.4, 0.1, -0.3)]
OUVERT = ((0.0, 0.0, 0.0), (-60.0, 0.0, 0.0), (1.0, 1.0, 1.0))                  # cle d'ouverture des 194 coffres du jeu : rotation X = -60


class TestRotationJeu(unittest.TestCase):
    def test_ordre_des_rotations_comme_le_jeu(self):
        rng = np.random.RandomState(7)
        for _ in range(50):
            rx, ry, rz = rng.uniform(-180, 180, 3)
            np.testing.assert_allclose(euler_mat(rx, ry, rz), rotate_xzy_jeu(rx, ry, rz), atol=1e-9)

    def test_x_en_premier_dans_le_repere_de_l_objet(self):
        """La bascule en X (couvercle) se fait dans le repere de l'objet, puis le cap le tourne : Ry . Rx."""
        for cap in (0, 90, -90, 180, -27, 133):
            np.testing.assert_allclose(euler_mat(-60, cap, 0), euler_mat(0, cap, 0) @ euler_mat(-60, 0, 0), atol=1e-9)

    def test_rotations_simples_inchangees(self):
        for cap in (0, 45, 90, -90, 180):
            np.testing.assert_allclose(euler_mat(0, cap, 0), ry_mat(cap), atol=1e-12)
        r = euler_mat(-60, 0, 0) @ np.array([0, 0, -1.0])                           # cle -60 : le bord avant du couvercle monte et recule
        self.assertAlmostEqual(r[1], math.sin(math.radians(60))); self.assertAlmostEqual(r[2], -0.5); self.assertAlmostEqual(r[0], 0.0)


class TestCoffre(unittest.TestCase):
    def test_l_ouverture_suit_le_cap_du_coffre(self):
        """Quel que soit le cap, le couvercle fini = celui du coffre de cap 0, tourne du cap (autour de la charniere)."""
        pos = (3.0, 0.5, -2.0)
        ref = jouer(carte_objet(pos, (0, 0, 0), COUVERCLE, OUVERT)) - np.array(pos)
        self.assertGreater(ref[2][1], 0.4)                                          # coffre de cap 0 : le bord avant se leve (0,6 x sin 60 = 0,52)
        for cap in (90, -90, 180, -27, 133):
            fini = jouer(carte_objet(pos, (0, cap, 0), COUVERCLE, OUVERT)) - np.array(pos)
            attendu = (ry_mat(cap) @ ref.T).T
            np.testing.assert_allclose(fini, attendu, atol=1e-5, err_msg='cap %d' % cap)

    def test_la_charniere_reste_en_place_et_le_couvercle_ne_roule_jamais(self):
        pos = (0.0, 0.5, 0.0)
        for cap in (0, 90, -90, 180, -27):
            c = carte_objet(pos, (0, cap, 0), COUVERCLE, OUVERT); avant = c['groupes']['k'][0].astype(np.float64).copy()
            fini = jouer(c)
            np.testing.assert_allclose(fini[:2], avant[:2], atol=1e-6)               # les deux sommets de la charniere ne bougent pas
            avant_f = ry_mat(cap) @ np.array([0, 0, -1.0])                           # l'avant du coffre (axe de la charniere vers l'avant)
            d = (fini[2] - fini[0]); d = d / np.linalg.norm(d)                       # axe de la charniere -> bord avant du couvercle ouvert : dans le plan vertical de l'avant du coffre
            lateral = ry_mat(cap) @ np.array([1.0, 0, 0])                            # axe de la charniere : le deplacement lateral doit rester nul (ouverture « en livre », pas de roulis)
            self.assertAlmostEqual(float(d @ lateral), 0.0, places=5, msg='cap %d' % cap)
            self.assertGreater(float(d @ avant_f), 0.0)

    def test_milieu_de_course_meme_vitesse_a_tous_les_caps(self):
        pos = (0.0, 0.5, 0.0)
        ref0 = None
        for cap in (0, 90, 180):
            oc = OC.ObjetsCarte(carte_objet(pos, (0, cap, 0), COUVERCLE, OUVERT)); oc.anim_commune(0, 2)
            for _ in range(3): oc.tick()                                             # 3 images du jeu = 6 / 60 s sur 10
            p = (ry_mat(cap).T @ (oc.cur['k'].astype(np.float64)[2] - np.array(pos)))
            if ref0 is None: ref0 = p
            np.testing.assert_allclose(p, ref0, atol=1e-5)
            self.assertTrue(0.05 < p[1] < 0.5)                                       # entre fermé et ouvert


class TestMouvements(unittest.TestCase):
    CLE_TIROIR = ((0.0, 0.0, -0.5), (0.0, 0.0, 0.0), (1.0, 1.0, 1.0))             # le tiroir sort de 0,5 vers l'avant du meuble

    def test_mouvement_commun_dans_le_repere_de_l_objet(self):
        pos = (1.0, 0.0, 1.0); pts = [(0, 0, 0), (0.2, 0.1, 0)]
        for cap in (0, 90, -90, 180, -27):
            c = carte_objet(pos, (0, cap, 0), pts, self.CLE_TIROIR); avant = c['groupes']['k'][0].astype(np.float64).copy()
            fini = jouer(c)
            np.testing.assert_allclose(fini - avant, np.tile(ry_mat(cap) @ np.array([0, 0, -0.5]), (2, 1)), atol=1e-5, err_msg='cap %d' % cap)

    def test_mouvement_commun_avec_echelle(self):
        pos = (0.0, 0.0, 0.0); pts = [(0, 0, 0)]
        c = carte_objet(pos, (0, 90, 0), pts, self.CLE_TIROIR, scl=(2.0, 1.0, 3.0)); avant = c['groupes']['k'][0].astype(np.float64).copy()
        fini = jouer(c)
        np.testing.assert_allclose(fini - avant, [(-0.5 * 3.0, 0, 0)], atol=1e-5)    # MultiplyPoint(TRS) : l'echelle de l'objet s'applique aussi au deplacement (z x 3, tourne de 90 degres)

    def test_mouvement_ordinaire_deplacement_tel_quel(self):
        pos = (0.0, 0.0, 0.0); pts = [(0, 0, 0)]
        c = carte_objet(pos, (0, 90, 0), pts, self.CLE_TIROIR, flag_mouvement=0); avant = c['groupes']['k'][0].astype(np.float64).copy()
        fini = jouer(c)
        np.testing.assert_allclose(fini - avant, [(0, 0, -0.5)], atol=1e-5)          # pmv_func : position de l'objet + cle, sans rotation

    def test_ordre_du_moteur_position_et_cap(self):
        """SetMapObjPos / SetMapObjRot (paquets 3 et 4) puis mouvement commun : la base du mouvement est la position et le cap COURANTS de l'objet (c_pmv_func lit les champs de l'objet)."""
        pts = [(0, 0, 0)]
        c = carte_objet((0.0, 0.0, 0.0), (0, 0, 0), pts, self.CLE_TIROIR); oc = OC.ObjetsCarte(c)
        oc.position(0, (5.0, 0.0, 5.0)); oc.rotation(0, (0.0, 90.0)); oc.anim_commune(0, 2)
        for _ in range(20): oc.tick()
        np.testing.assert_allclose(oc.cur['k'].astype(np.float64)[0], (5.0 - 0.5, 0.0, 5.0), atol=1e-5)

    def test_porte_autour_de_y_inchangee(self):
        pts = [(0, 0, 0), (0.0, 0.0, 1.0), (0.0, 1.0, 1.0)]
        for cap in (0, 90, -90, 180):
            c = carte_objet((0, 0, 0), (0, cap, 0), pts, ((0, 0, 0), (0, -90, 0), (1, 1, 1))); fini = jouer(c)
            np.testing.assert_allclose(fini, np.array([ry_mat(cap - 90) @ np.array(p, float) for p in pts]), atol=1e-5)


def cartes_reelles():
    """Cartes du cache de l'utilisateur (carte9_*.pkl) : `DQ_CACHE_CARTES`, sinon /tmp/uicache_coffres ; vide si le cache n'existe pas (les tests ci-dessous sont alors ignores)."""
    import glob
    return sorted(glob.glob(os.path.join(os.environ.get('DQ_CACHE_CARTES', '/tmp/uicache_coffres'), 'carte9_*.pkl')))


@unittest.skipUnless(cartes_reelles(), 'pas de cache de cartes (carte9_*.pkl)')
class TestCartesReelles(unittest.TestCase):
    """Les vrais objets du jeu : tous les coffres (modele `tbox02` = le couvercle, `tbox01` = le corps), tiroirs (`hikidashi1b`) et portes de toutes les cartes, joues de bout en bout."""

    @staticmethod
    def charger(f):
        import pickle
        with open(f, 'rb') as fh: return pickle.load(fh)

    @staticmethod
    def sommets(c, oc, i):
        return np.concatenate([oc.cur[key][d:d + n] for key, d, n in c['plages'][i]]).astype(np.float64)

    def objets(self, motif):
        """[(carte, c, i)] des objets dont le nom de modele finit par `motif` et qui ont des animations communes."""
        res = []
        for f in cartes_reelles():
            c = self.charger(f)
            for i, o in enumerate(c['objets']):
                if c['noms'].get(i, '').endswith(motif) and 0 <= o['canim'] < len(c['tabs']) and i in c['plages']: res.append((os.path.basename(f), c, i))
        return res

    def test_tous_les_coffres_s_ouvrent_autour_de_leur_charniere(self):
        coffres = self.objets('tbox02'); self.assertGreater(len(coffres), 150)
        caps = set()
        for nom, c, i in coffres:
            o = c['objets'][i]; pos = np.array(o['pos'], np.float64); R = euler_mat(*o['rot']); caps.add(round(o['rot'][1]))
            oc = OC.ObjetsCarte(c); ferme = self.sommets(c, oc, i)
            oc.anim_commune(i, 2)                                                    # SetCommonAnimation 2 = ouverture (TownFurnitureObject::openObject), 4 = fermeture
            for _ in range(20): oc.tick()
            ouvert = self.sommets(c, oc, i); msg = '%s objet %d cap %s' % (nom, i, o['rot'])
            np.testing.assert_allclose(np.linalg.norm(ouvert - pos, axis=1), np.linalg.norm(ferme - pos, axis=1), atol=1e-4, err_msg=msg)       # rotation rigide autour de l'origine du modele (la charniere)
            axe = R @ np.array([1.0, 0.0, 0.0])                                      # la charniere est l'axe X du coffre
            np.testing.assert_allclose((ouvert - ferme) @ axe, 0.0, atol=1e-4, err_msg=msg)       # aucun mouvement le long de la charniere : le couvercle ne roule jamais de cote
            haut = np.argmax(ouvert[:, 1]); self.assertGreater(ouvert[haut, 1] - ferme[:, 1].max(), 0.1, msg)    # le bord libre monte...
            dec = (ouvert[haut] - ferme[haut]) @ (R @ np.array([0.0, 0.0, 1.0]))     # ... et recule vers l'arriere du coffre (+Z du modele, le devant est -Z)
            self.assertGreater(dec, 0.1, msg)
        self.assertTrue({90, -90, 180, -180, -27} <= caps or len(caps) > 1, caps)    # les caps non nuls existent dans les donnees (ss5b1b, hcy1b1, tcf1, mdi1f1...)

    def test_les_coffres_se_referment_comme_au_depart(self):
        for nom, c, i in self.objets('tbox02')[:40]:
            oc = OC.ObjetsCarte(c); ferme = self.sommets(c, oc, i)
            oc.anim_commune(i, 2)
            for _ in range(20): oc.tick()
            oc.anim_commune(i, 4)                                                    # fermeture
            for _ in range(20): oc.tick()
            np.testing.assert_allclose(self.sommets(c, oc, i), ferme, atol=1e-4, err_msg='%s objet %d' % (nom, i))

    def test_tiroirs_sortent_vers_l_avant_de_leur_meuble(self):
        tiroirs = self.objets('hikidashi1b'); self.assertGreater(len(tiroirs), 10)
        vu = set()
        for nom, c, i in tiroirs:
            o = c['objets'][i]; oc = OC.ObjetsCarte(c); ferme = self.sommets(c, oc, i)
            oc.anim_commune(i, 2)
            for _ in range(20): oc.tick()
            dep = self.sommets(c, oc, i) - ferme
            cle = np.array(c['mots'][c['tabs'][o['canim']][1][2]]['keys'][-1][1], np.float64)       # cle d'arrivee de l'animation 2 : un tiroir sort vers l'avant (-Z) de son meuble, de 0,25 (ou 1) selon le modele
            self.assertEqual((cle[0], cle[1]), (0.0, 0.0)); self.assertLess(cle[2], 0.0)
            attendu = euler_mat(*o['rot']) @ (np.array(o['scl'], np.float64) * cle)  # tournee du cap du meuble (repere de l'objet)
            np.testing.assert_allclose(dep, np.tile(attendu, (len(dep), 1)), atol=1e-4, err_msg='%s objet %d cap %s' % (nom, i, o['rot']))
            vu.add(round(o['rot'][1]))
        self.assertGreater(len(vu), 1)                                               # des tiroirs de caps differents (0, 90, -90, -6, -2)

    def test_portes_ouvertes_autour_de_leur_charniere_verticale(self):
        for motif in ('door01', 'wdoor04'):
            for nom, c, i in self.objets(motif)[:60]:
                o = c['objets'][i]; pos = np.array(o['pos'], np.float64); oc = OC.ObjetsCarte(c); ferme = self.sommets(c, oc, i)
                oc.anim_commune(i, 2)
                for _ in range(20): oc.tick()
                ouvert = self.sommets(c, oc, i); msg = '%s objet %d' % (nom, i)
                np.testing.assert_allclose(ouvert[:, 1], ferme[:, 1], atol=1e-4, err_msg=msg)            # la porte tourne autour de la verticale : aucune hauteur ne change
                np.testing.assert_allclose(np.hypot(ouvert[:, 0] - pos[0], ouvert[:, 2] - pos[2]), np.hypot(ferme[:, 0] - pos[0], ferme[:, 2] - pos[2]), atol=1e-4, err_msg=msg)


if __name__ == '__main__':
    unittest.main(verbosity=2)
