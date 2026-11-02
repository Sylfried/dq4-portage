"""Tests des poses couchees (paquets 16 / 17 / 18, #45) : decodage des paquets (Etat.appliquer, sans moteur) et geometrie (pose_couchee.py, sans fenetre) ; avec le vrai moteur (si DQ_APK et DQ_SAVES
sont donnes) : la carte taf1 (chateau a dalles vertes, soldat en armure bleue emplacement 8) envoie bien le paquet 16 0x0c000508 et le paquet 17 [1040, 1863].

    python3 outils/test_pose_couchee.py
    DQ_APK=... DQ_SAVES=... python3 outils/test_pose_couchee.py      (ajoute le test du vrai moteur)
"""
import os, sys, math, shutil, unittest
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'dq4_pc'))
import moteur as MO
import pose_couchee as PC


def nom_carte(): return 'carte_test'


def camera(tangage_deg=47.03, lacet_deg=0.0, position=(0.0, 28.94, -26.96)):
    """Camera de ville : (droite, haut, avant) et position ; le tangage regarde vers le bas, le lacet tourne vers +X."""
    t, l = math.radians(tangage_deg), math.radians(lacet_deg)
    f = np.array([math.sin(l) * math.cos(t), -math.sin(t), math.cos(l) * math.cos(t)])
    r = np.cross([0.0, 1.0, 0.0], f); r /= np.linalg.norm(r)
    u = np.cross(f, r)
    return (r, u, f), np.array(position, float)


def ecran(P, cam, cadre):
    """Coordonnees ecran (focale 1) d'un point monde et profondeur."""
    r, u, f = cadre; v = np.asarray(P, float) - cam; z = float(v @ f)
    return float(v @ r) / z, float(v @ u) / z, z


class TestPaquets(unittest.TestCase):
    def setUp(self): self.e = MO.Etat(); self.e.appliquer([(12, [8, 18], []), (12, [9, 7], [])], nom_carte)

    def appliquer(self, *p): self.e.appliquer(list(p), nom_carte)

    def test_valeurs_reelles_de_taf1(self):
        self.appliquer((17, [1040, 1863], []), (16, [0x0c000508], []))
        s = self.e.sprites[8]
        self.assertTrue(s['dort'])
        self.assertAlmostEqual(s['dort_rot'][0], -90.0, places=3)             # 0xc000 / -182,0444 + 180
        self.assertEqual(s['dort_rot'][1], 3)
        self.assertAlmostEqual(self.e.dort_haut, 1863 * 1.6 / 8192, places=6)

    def test_valeurs_mlb1a(self):
        self.appliquer((16, [0x500], []), (16, [0x501], []))                    # se couchent sans angle precis : 0 -> 180 degres
        self.assertNotIn('dort', self.e.sprites[8])                              # (aucun paquet pour l'emplacement 8)
        self.appliquer((12, [0, 106], []), (12, [1, 130], []), (16, [0x0c000500], []), (16, [0x08000501], []))
        self.assertAlmostEqual(self.e.sprites[0]['dort_rot'][0], -90.0, places=3); self.assertEqual(self.e.sprites[0]['dort_rot'][1], 3)
        self.assertAlmostEqual(self.e.sprites[1]['dort_rot'][0], 0.0, places=3); self.assertEqual(self.e.sprites[1]['dort_rot'][1], 2)

    def test_se_relever(self):
        self.appliquer((16, [0x0c000508], []))
        self.assertTrue(self.e.sprites[8]['dort'])
        self.appliquer((16, [0x208], []))                                       # DisplayCharacter::setSleepFlag(0)
        self.assertFalse(self.e.sprites[8]['dort'])

    def test_changement_de_direction_en_dormant(self):
        self.appliquer((16, [0x0c000508], []), (16, [0x08000408], []))          # DisplayCharacter::draw : 0x400 | angle << 12 (sans les bits 8 / 9 : le sommeil continue)
        s = self.e.sprites[8]
        self.assertTrue(s['dort']); self.assertAlmostEqual(s['dort_rot'][0], 0.0, places=3)

    def test_hauteur_par_defaut_et_persistance(self):
        self.assertEqual(self.e.dort_haut, 0.0)                                 # Chara..cctor : y = 0 tant qu'aucun paquet 17
        self.appliquer((17, [1105, 0], []))
        self.assertAlmostEqual(self.e.dort_haut, 0.3104, places=6)
        self.appliquer((17, [1105, 794], []))
        self.assertAlmostEqual(self.e.dort_haut, 794 * 1.6 / 8192, places=6)
        self.appliquer((0, [], []))                                             # nouvelle carte : la statique de Chara reste
        self.assertAlmostEqual(self.e.dort_haut, 794 * 1.6 / 8192, places=6)

    def test_pose_change_la_feuille(self):
        self.appliquer((18, [8 | (21 << 8)], []))
        self.assertEqual(self.e.sprites[8]['id'], 21)
        self.appliquer((18, [9 | (4 << 8)], []))
        self.assertEqual(self.e.sprites[9]['id'], 4)
        self.appliquer((18, [77 | (4 << 8)], []))                               # emplacement inconnu : sans effet, sans plantage
        self.assertNotIn(77, self.e.sprites)

    def test_paquet_sans_sprite(self):
        self.appliquer((16, [0x0c000563], []))                                  # emplacement inconnu
        self.assertNotIn(0x63, self.e.sprites)

    def test_ancien_etat_sans_dort_haut(self):
        e = MO.Etat(); d = dict(e.__dict__); d.pop('dort_haut'); e2 = MO.Etat.__new__(MO.Etat); e2.__setstate__(d)
        self.assertEqual(e2.dort_haut, 0.0)


class TestGeometrie(unittest.TestCase):
    def test_decodage(self):
        self.assertEqual(PC.direction_paquet(0x500), (180.0, 0))
        a, q = PC.direction_paquet(0x0c000500); self.assertAlmostEqual(a, -90.0, places=3); self.assertEqual(q, 3)
        a, q = PC.direction_paquet(0x04000500); self.assertAlmostEqual(a, 90.0, places=3); self.assertEqual(q, 1)
        a, q = PC.direction_paquet(0x08000500); self.assertAlmostEqual(a, 0.0, places=3); self.assertEqual(q, 2)

    def test_tete_a_l_ecran(self):
        # direction 0 = tete en haut, 0x4000 = a gauche, 0x8000 = en bas, 0xc000 = a droite
        for d16, attendu in ((0x0, 0), (0xc000, 90), (0x8000, 180), (0x4000, 270)):
            a, _ = PC.direction_paquet(0x400 | (d16 << 12)); self.assertAlmostEqual(PC.tete_a_l_ecran(a), attendu, places=2)

    def corners(self, d16, tang=47.03, lacet=0.0, haut=0.0, ech=2.25, pos=(0.0, 0.0, 0.0)):
        cadre, cam = camera(tang, lacet); a, q = PC.direction_paquet(0x400 | (d16 << 12))
        return PC.sommets(pos, a, q, haut, ech, cadre, cam), cadre, cam

    def test_taille_a_l_ecran_sans_raccourci(self):
        # le corps a plat garde sa taille de feuille a l'ecran : largeur 0,48 x 2,25 = 1,08, hauteur 1,44, quelle que soit l'inclinaison de la camera
        for tang in (30.0, 47.03, 70.0):
            for d16 in (0, 0x8000):
                (a, b, c, d), cadre, cam = self.corners(d16, tang)
                pa, pb, pc, pd = (np.array(ecran(P, cam, cadre)[:2]) for P in (a, b, c, d))
                z = float(np.mean([ecran(P, cam, cadre)[2] for P in (a, b, c, d)]))           # profondeur du centre du corps
                self.assertAlmostEqual(np.linalg.norm(pb - pa) * z, 1.08, delta=0.02)          # bas gauche -> bas droit
                self.assertAlmostEqual(np.linalg.norm(pd - pa) * z, 1.44, delta=0.02)          # bas gauche -> haut gauche
                self.assertAlmostEqual(float((pb - pa) @ (pd - pa)), 0.0, delta=1e-3)          # rectangle, aucun cisaillement

    def test_tete_vers_le_haut_pour_la_direction_0(self):
        (a, b, c, d), cadre, cam = self.corners(0)
        pa, pd = np.array(ecran(a, cam, cadre)[:2]), np.array(ecran(d, cam, cadre)[:2])
        self.assertGreater(pd[1], pa[1] + 0.01); self.assertAlmostEqual(pd[0], pa[0], delta=1e-3)         # le haut de la feuille est en haut de l'ecran

    def test_quatre_directions(self):
        attendu = {0x0: (0, 1), 0xc000: (1, 0), 0x8000: (0, -1), 0x4000: (-1, 0)}           # vecteur « pieds -> tete » a l'ecran
        for d16, v in attendu.items():
            (a, b, c, d), cadre, cam = self.corners(d16)
            pa, pd = np.array(ecran(a, cam, cadre)[:2]), np.array(ecran(d, cam, cadre)[:2]); w = (pd - pa) / np.linalg.norm(pd - pa)
            self.assertAlmostEqual(w[0], v[0], delta=0.01, msg=hex(d16)); self.assertAlmostEqual(w[1], v[1], delta=0.01, msg=hex(d16))

    def test_pas_de_miroir(self):
        # bas gauche -> bas droit puis bas gauche -> haut gauche : meme sens de rotation que la feuille debout (produit vectoriel positif a l'ecran)
        for d16 in (0, 0x4000, 0x8000, 0xc000):
            (a, b, c, d), cadre, cam = self.corners(d16)
            pa, pb, pd = (np.array(ecran(P, cam, cadre)[:2]) for P in (a, b, d))
            v1, v2 = pb - pa, pd - pa; self.assertGreater(v1[0] * v2[1] - v1[1] * v2[0], 0.0, msg=hex(d16))

    def test_la_camera_tournee_tourne_le_corps(self):
        # la camera tourne de 90 degres : le corps (monde) tourne a l'ecran dans l'autre sens : tete a droite (0xc000) devient tete en haut quand la camera tourne de 90 degres
        (a, b, c, d), cadre, cam = self.corners(0xc000, lacet=90.0, pos=(0.0, 0.0, 0.0))
        pa, pd = np.array(ecran(a, cam, cadre)[:2]), np.array(ecran(d, cam, cadre)[:2]); w = (pd - pa) / np.linalg.norm(pd - pa)
        self.assertAlmostEqual(abs(w[0]) + abs(w[1]), 1.0, delta=0.05)            # reste un quart de tour exact (pas un angle quelconque)
        self.assertGreater(abs(w[1]), 0.99)

    def test_profondeur_du_corps_a_plat(self):
        # z-buffer : la profondeur des 4 coins est celle du rectangle a plat (a 0,1 + hauteur du sol), pas celle d'un panneau debout
        (a, b, c, d), cadre, cam = self.corners(0, haut=0.3639)
        zs = [ecran(P, cam, cadre)[2] for P in (a, b, c, d)]
        cadre_, cam_ = cadre, cam
        plat = [float((np.array([0.0 + dx, 0.3639 + 0.1, 0.2 + dz]) - cam_) @ cadre_[2]) for dx, dz in ((-0.54, -0.72), (0.54, -0.72), (0.54, 0.72), (-0.54, 0.72))]
        for z, p in zip(zs, plat): self.assertAlmostEqual(z, p, delta=1e-3)

    def test_derriere_la_camera(self):
        cadre, cam = camera(); self.assertIsNone(PC.sommets((0.0, 0.0, -100.0), 0.0, 0, 0.0, 2.25, cadre, cam))

    def test_hauteur_decale_vers_le_haut(self):
        (a0, *_), cadre, cam = self.corners(0, haut=0.0); (a1, *_), _, _ = self.corners(0, haut=0.36)
        self.assertGreater(ecran(a1, cam, cadre)[1], ecran(a0, cam, cadre)[1])


@unittest.skipUnless(os.environ.get('DQ_APK') and os.environ.get('DQ_SAVES'), 'DQ_APK et DQ_SAVES requis (vrai moteur)')
class TestVraiMoteur(unittest.TestCase):
    def test_taf1(self):
        ecr = '/tmp/sv_test_pose_couchee'; shutil.rmtree(ecr, ignore_errors=True); os.makedirs(ecr)
        m = MO.Moteur(os.environ['DQ_APK'], os.environ['DQ_SAVES'], ecr)
        self.assertTrue(m.charger_sauvegarde(1))
        for _ in range(10): m.step(0, 0)
        m.demarrer_ville('taf1'); vus = []
        for _ in range(80):
            for t, a, f in m.step(0, 0):
                if t in (16, 17) and a: vus.append((t, list(a)))
        self.assertIn((17, [1040, 1863]), vus)
        self.assertIn((16, [0x0c000508]), vus)
        s = m.etat.sprites[8]
        self.assertEqual(s['id'], 18)                                        # soldat en armure bleue
        self.assertTrue(s['dort']); self.assertAlmostEqual(s['dort_rot'][0], -90.0, places=3)
        self.assertAlmostEqual(m.etat.dort_haut, 1863 * 1.6 / 8192, places=6)


if __name__ == '__main__': unittest.main(verbosity=1)
