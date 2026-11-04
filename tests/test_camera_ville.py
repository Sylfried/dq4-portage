"""Test de la camera des villes (sans fenetre ni moteur : `Jeu._camera_ville` est appelee sur un faux objet). Depuis #264 elle est celle du jeu, et le joueur n'y change que la rotation gauche / droite (D-233) :

  1. la matrice du portage = le pipeline d'Unity re-ecrit a part (SceneCamera.Update : LookAt, tangage - lookDownAdjust, avance de distanceAdjust, Perspective(fov x 4/3, 1/aspect) dont on echange
     [0] et [5], s_yOffset) a l'ecran portrait d'origine (0,5625) ;
  2. sans rotation du joueur, elle ne depend QUE de ce que le moteur envoie (position, cible, champ, decalage, rotation libre) : ni du heros, ni de l'historique des images (aucun lissage, aucun centrage,
     aucun reste qui glisse), ni zoom, ni inclinaison ;
  3. la rotation du joueur tourne la camera autour de la cible du jeu (distance, tangage et position de la cible a l'ecran inchanges), s'efface en douceur quand le jeu tient la camera (scene, verrou, lieu qui
     interdit de la tourner) et n'agit ni sur la carte du monde, ni sur l'ecran-titre, ni en camera libre ;
  4. les autres reglages et gestes du joueur sur la camera n'existent plus (zoom, distance, inclinaison, centrage, acceleration, molette).

    python3 tests/test_camera_ville.py        (Linux sans ecran : pyglet en mode « headless »)
"""
import math, os, sys, types, unittest, inspect

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import _chemins          # (aide des tests : retrouver le code source dans les sous-dossiers de dq4_pc)
import pyglet
if sys.platform.startswith('linux') and not os.environ.get('DISPLAY'): pyglet.options['headless'] = True; pyglet.options['shadow_window'] = False
from dq4_pc.fenetre import jeu as F
from dq4_pc.noyau import moteur as MO
from dq4_pc.persistance import reglages as RG

ASPECT_16_9 = 16.0 / 9.0


def faux_jeu(lacet=0.0, **kw):
    """Le strict necessaire : si la camera relisait un reglage du joueur retire (zoom, angle, distance...), ce faux jeu leverait AttributeError. `lacet` = la rotation du joueur ; `cam_saut` vrai au depart (premiere image :
    le poids du jeu est pris tel quel, sans transition)."""
    j = types.SimpleNamespace(n_boucle=0, _cadre_vue=None, _cadre_sprites=None, fixe_test=True, t_centre=None, cam_jeu=False, cam_bloquee=False, cam_saut=True, cam_w=0.0, lacet=lacet, carte_nom=None,
                              moteur=types.SimpleNamespace(etat=types.SimpleNamespace(partie=None, cam_libre=False, cam_rot=None)))
    j._rot_camera = lambda e: F.Jeu._rot_camera(j, e)
    j._lacet_eff = lambda: F.Jeu._lacet_eff(j)
    for k, v in kw.items(): setattr(j, k, v)
    return j


def vue(e, aspect=None, lacet=0.0, j=None, **kw):
    """-> (matrice, repere, faux jeu) : la camera de la ville pour l'etat `e` (le faux moteur est celui de `e`)."""
    j = j or faux_jeu(lacet, **kw); j.moteur.etat = e
    M, rep = F.Jeu._camera_ville(j, e, ASPECT_16_9 if aspect is None else aspect)
    return M, rep, j


def faux_etat(cib, hero, fov=None, yoff=None, partie=None, libre=False, rot=None, pos=None):
    cib = np.array(cib, float)
    return types.SimpleNamespace(cam_pos=cib + np.array([0.0, 28.94, -27.0]) if pos is None else np.array(pos, float), cam_cible=cib, cam_fov=fov, cam_near=None, cam_far=None, cam_yoff=yoff, cam_bas=None, cam_libre=libre, cam_rot=rot,
                                 sprites={0: {'pos': tuple(hero)}} if hero is not None else {}, partie=partie)


def ndc(M, p):
    c = M @ np.array([p[0], p[1], p[2], 1.0]); return c[0] / c[3], c[1] / c[3]


def unity_ndc(pos, cib, fov, near, far, yoff, aspect_cam, pts, bas=0.2, dist_adj=4.0):
    """SceneCamera.Update (mode avec cible) + NativeManager.cmd_camera, d'apres le code d'origine."""
    pos = np.array(pos, float); cib = np.array(cib, float)
    f0 = cib - pos; f0 /= np.linalg.norm(f0)
    ry, rx = math.atan2(f0[0], f0[2]), math.asin(-f0[1]) - math.radians(bas)                            # euler Unity : cap, tangage vers le bas ; eulerAngles.x -= s_lookDownAdjust
    Ry = np.array([[math.cos(ry), 0, math.sin(ry)], [0, 1, 0], [-math.sin(ry), 0, math.cos(ry)]])
    Rx = np.array([[1, 0, 0], [0, math.cos(rx), -math.sin(rx)], [0, math.sin(rx), math.cos(rx)]])
    R = Ry @ Rx; pos = pos + R @ np.array([0, 0, 1.0]) * dist_adj                                      # avance de s_distanceAdjust
    V = np.eye(4); V[:3, :3] = R.T; V[:3, 3] = -R.T @ pos; V = np.diag([1, 1, -1, 1.0]) @ V            # worldToCamera d'Unity (regarde vers -z)
    fv = math.radians(fov * 4.0 / 3.0)
    m11 = 1 / math.tan(fv / 2); m00 = m11 / (1.0 / aspect_cam)                                          # Matrix4x4.Perspective(fov x 4/3, 1 / aspect, near, far)
    P = np.zeros((4, 4)); P[0, 0] = m00; P[1, 1] = m11; P[2, 2] = -(far + near) / (far - near); P[2, 3] = -2 * far * near / (far - near); P[3, 2] = -1
    P[0, 0], P[1, 1] = P[1, 1], P[0, 0]                                                                 # [0] et [5] echanges : champ horizontal fixe
    Ty = np.eye(4); Ty[1, 3] = yoff                                                                     # s_yOffset
    out = []
    for p in pts:
        c = Ty @ P @ V @ np.array([*p, 1.0]); out.append((c[0] / c[3], c[1] / c[3]))
    return np.array(out)


class TestCameraVille(unittest.TestCase):
    def test_projection_comme_unity(self):
        rng = np.random.default_rng(1); pire = 0.0
        for _ in range(100):
            cib = rng.uniform(-30, 30, 3); cib[1] = 0
            pos = cib + np.array([rng.uniform(-8, 8), 29.0 + rng.uniform(-3, 3), -27.0 + rng.uniform(-3, 3)])
            fov = float(rng.choice([9.5, 10.0])); yoff = float(rng.choice([0.0, 0.05]))
            pts = [cib + np.array([dx, dy, dz]) for dx in (-5, 0, 5) for dy in (0, 1.5) for dz in (-6, 0, 6)]
            ref = unity_ndc(pos, cib, fov, F.VILLE_NEAR, F.VILLE_FAR, yoff, F.ASPECT_PORTRAIT, pts)
            e = faux_etat(cib, cib, fov, yoff, pos=pos)
            M, _ = F.Jeu._camera_ville(faux_jeu(), e, F.ASPECT_PORTRAIT)
            pire = max(pire, float(np.abs(np.array([ndc(M, p) for p in pts]) - ref).max()))
        self.assertLess(pire, 1e-9)

    def test_independante_du_heros(self):
        """Le heros au centre, a l'autre bout de la carte, absent : meme image (la cible du jeu, bornee aux bords de la carte, fait foi ; la visionneuse ne recentre plus)."""
        refs = []
        for hero in ((0.0, 0.0, 0.0), (7.0, 0.0, -3.0), (40.0, 5.0, 40.0), None):
            M, _ = F.Jeu._camera_ville(faux_jeu(), faux_etat((5.0, 0.0, 4.0), hero), ASPECT_16_9); refs.append(M)
        for M in refs[1:]: self.assertLess(float(np.abs(M - refs[0]).max()), 1e-12)
        self.assertGreater(abs(ndc(refs[0], (0.0, 0.0, 0.0))[0]), 0.05, 'le heros n\'est pas recentre quand la cible du jeu est ailleurs (bord de la carte)')

    def test_sans_memoire(self):
        """Aucun lissage, aucun reste : l'image ne depend que de l'etat envoye par le moteur a cet instant (marche, escalier, coupure de scene, retour de scene...)."""
        j = faux_jeu(); trajet = [((0.0, 0.0, 0.0), 0.0), ((1.0, 0.0, 0.5), 0.3), ((1.0, 4.0, 0.5), 4.0), ((30.0, 4.0, -9.0), 4.0), ((30.0, 0.0, -9.0), 0.0), ((2.0, 0.0, 2.0), 0.0)]
        for cib, y in trajet:
            e = faux_etat((cib[0], y, cib[2]), (cib[0], y, cib[2]))
            M1, _ = F.Jeu._camera_ville(j, e, ASPECT_16_9); M2, _ = F.Jeu._camera_ville(faux_jeu(), e, ASPECT_16_9)
            self.assertLess(float(np.abs(M1 - M2).max()), 1e-12, cib)
            self.assertLess(abs(ndc(M1, (cib[0], y, cib[2]))[0]) + abs(ndc(M1, (cib[0], y, cib[2]))[1] - ndc(M2, (cib[0], y, cib[2]))[1]), 1e-6, 'la cible du jeu reste ou le jeu la met')

    def test_hauteur_telle_que_le_jeu(self):
        """Un escalier : la cible du jeu monte de 4 unites, l'image suit tout de suite (aucun retard comme l'ancien lissage de hauteur)."""
        j = faux_jeu(); M0, _ = F.Jeu._camera_ville(j, faux_etat((0.0, 0.0, 0.0), (0.0, 0.0, 0.0)), ASPECT_16_9)
        e = faux_etat((0.0, 4.0, 0.0), (0.0, 4.0, 0.0)); M1, _ = F.Jeu._camera_ville(j, e, ASPECT_16_9)
        self.assertLess(abs(ndc(M1, (0.0, 4.0, 0.0))[1] - ndc(M0, (0.0, 0.0, 0.0))[1]), 1e-9, 'le heros reste ou il etait a l\'ecran, sans glissement')

    def test_camera_libre_et_decalage(self):
        """Camera libre d'une scene (paquet 11, bit 7 : position + angles) et decalage vertical : ce que le jeu commande, rien de plus."""
        e = faux_etat((0.0, 0.0, 0.0), (9.0, 0.0, 9.0), libre=True, rot=(30.0, 20.0, 0.0), pos=(1.0, 12.0, -10.0))
        M, rep = F.Jeu._camera_ville(faux_jeu(), e, ASPECT_16_9); e2 = faux_etat((0.0, 0.0, 0.0), None, libre=True, rot=(30.0, 20.0, 0.0), pos=(1.0, 12.0, -10.0))
        M2, _ = F.Jeu._camera_ville(faux_jeu(), e2, ASPECT_16_9); self.assertLess(float(np.abs(M - M2).max()), 1e-12)
        d = faux_etat((3.0, 0.0, 3.0), (3.0, 0.0, 3.0), yoff=0.05); d0 = faux_etat((3.0, 0.0, 3.0), (3.0, 0.0, 3.0), yoff=0.0)
        Ma, _ = F.Jeu._camera_ville(faux_jeu(), d, ASPECT_16_9); Mb, _ = F.Jeu._camera_ville(faux_jeu(), d0, ASPECT_16_9)
        self.assertAlmostEqual(ndc(Ma, (3.0, 0.0, 3.0))[1] - ndc(Mb, (3.0, 0.0, 3.0))[1], 0.05, places=6)

    def cap(self, rep):
        fw = rep[2]; return math.degrees(math.atan2(fw[0], fw[2]))

    def test_rotation_autour_de_la_cible(self):
        """Le lacet du joueur tourne la camera autour de la cible du jeu : distance, tangage et place de la cible a l'ecran inchanges, cap = cap du jeu + lacet (positif = vers +X, comme la fleche droite)."""
        cib = (5.0, 0.0, 4.0); e0 = faux_etat(cib, cib, partie=MO.PARTIE_VILLE); M0, rep0, j0 = vue(e0)
        pos0, fw0 = j0._cadre_vue[0], j0._cadre_vue[3]
        for lacet in (-120.0, -45.0, 30.0, 90.0, 179.0):
            e = faux_etat(cib, cib, partie=MO.PARTIE_VILLE); M, rep, j = vue(e, lacet=lacet); pos, fw = j._cadre_vue[0], j._cadre_vue[3]
            self.assertLess(abs(ndc(M, cib)[0] - ndc(M0, cib)[0]) + abs(ndc(M, cib)[1] - ndc(M0, cib)[1]), 1e-9, lacet)          # la cible reste ou le jeu la met
            self.assertAlmostEqual(float(np.linalg.norm(pos - np.array(cib))), float(np.linalg.norm(pos0 - np.array(cib))), places=9)       # meme distance
            self.assertAlmostEqual(float(pos[1]), float(pos0[1]), places=9); self.assertAlmostEqual(float(fw[1]), float(fw0[1]), places=9)   # meme hauteur, meme tangage
            ecart = (self.cap(rep) - self.cap(rep0) - lacet + 180.0) % 360.0 - 180.0; self.assertLess(abs(ecart), 1e-6, lacet)             # cap + lacet
        self.assertAlmostEqual(self.cap(vue(faux_etat(cib, cib, partie=MO.PARTIE_VILLE), lacet=90.0)[1]) - self.cap(rep0), 90.0, places=6)       # (vers +X : la fleche droite)
        e = faux_etat(cib, cib, partie=MO.PARTIE_VILLE); M, rep, j = vue(e, lacet=90.0); self.assertLess(float(np.abs(np.array(j._cadre_sprites[2]) - np.array(rep[2])).max()), 1e-12)

    def test_lacet_nul_ou_effacee_la_ou_le_joueur_ne_tourne_pas(self):
        """Rotation sans effet : carte du monde, ecran-titre, camera libre d'une scene, lieu qui interdit de la tourner (verrou ou limite negative), scene ou le jeu tient la camera : la matrice est celle du jeu."""
        cib = (5.0, 0.0, 4.0); ref = vue(faux_etat(cib, cib, partie=MO.PARTIE_VILLE))[0]
        cas = {'champ': (dict(partie=MO.PARTIE_CHAMP), {}), 'titre': (dict(partie=MO.PARTIE_VILLE), dict(carte_nom=F.CARTE_TITRE)), 'bloquee': (dict(partie=MO.PARTIE_VILLE), dict(cam_bloquee=True)),
               'scene': (dict(partie=MO.PARTIE_VILLE), dict(cam_jeu=True)), 'libre': (dict(partie=MO.PARTIE_VILLE, libre=True, rot=(30.0, 20.0, 0.0), pos=(1.0, 12.0, -10.0)), {})}
        for nom, (etat, jeu) in cas.items():
            e = faux_etat(cib, cib, **etat); sans = vue(e)[0]; avec = vue(e, lacet=70.0, **jeu)[0]
            self.assertLess(float(np.abs(avec - sans).max()), 1e-12, nom)
            if nom != 'libre': self.assertLess(float(np.abs(avec - ref).max()), 1e-12, nom)
        e = faux_etat(cib, cib, partie=MO.PARTIE_VILLE); self.assertGreater(float(np.abs(vue(e, lacet=70.0)[0] - ref).max()), 0.1)             # (et ici, en ville, la rotation agit bien)

    def test_efface_en_douceur_pendant_une_scene_et_revient_de_meme(self):
        """Le jeu prend la camera (cam_jeu) : le lacet du joueur s'efface en exp(-CAM_SCENE_TAU t), sans a-coup ; la scene finie, il revient de la meme facon. Une coupure (cam_saut) est immediate."""
        cib = (5.0, 0.0, 4.0); e = faux_etat(cib, cib, partie=MO.PARTIE_VILLE); j = faux_jeu(100.0); j.cam_saut = False
        M, rep, j = vue(e, j=j); self.assertAlmostEqual(self.cap(rep) - self.cap(vue(e)[1]), 100.0, places=6); self.assertEqual(j.cam_w, 0.0)
        j.cam_jeu = True; caps = []
        for _ in range(180): M, rep, j = vue(e, j=j); caps.append(self.cap(rep) - self.cap(vue(e)[1]))
        self.assertLess(abs(caps[-1]), 0.01); self.assertTrue(all(b < a for a, b in zip(caps, caps[1:])), 'diminue a chaque image')
        self.assertLess(max(a - b for a, b in zip([100.0] + caps, caps)), 100.0 * (1.0 - math.exp(-F.CAM_SCENE_TAU / 60.0)) + 1e-6, 'a-coup')
        self.assertAlmostEqual(caps[5], 100.0 * math.exp(-F.CAM_SCENE_TAU * 6 / 60.0), places=4)
        j.cam_jeu = False; caps = []
        for _ in range(180): M, rep, j = vue(e, j=j); caps.append(self.cap(rep) - self.cap(vue(e)[1]))
        self.assertAlmostEqual(caps[-1], 100.0, places=1); self.assertTrue(all(b > a for a, b in zip(caps, caps[1:])), 'revient a chaque image')
        j.cam_jeu = True; j.cam_saut = True; M, rep, j = vue(e, j=j); self.assertAlmostEqual(self.cap(rep) - self.cap(vue(e)[1]), 0.0, places=6)       # coupure : immediat
        j.cam_jeu = False; j.cam_saut = True; M, rep, j = vue(e, j=j); self.assertAlmostEqual(self.cap(rep) - self.cap(vue(e)[1]), 100.0, places=6)

    def test_seule_la_rotation_reste_au_joueur(self):
        """Retires en #264 et qui ne reviennent pas : zoom / distance, inclinaison, centrage sur le heros, lissage de hauteur, acceleration de la camera. Reviennent en D-233 : la rotation gauche / droite et son recentrage."""
        src = inspect.getsource(F.Jeu._camera_ville)
        for mot in ('self.zoom', 'angle_cam', 'cam_dec', 'cam_res', 'cam_ref_y', 'hauteur_camera'): self.assertNotIn(mot, src, mot)
        for nom in ('_maj_distance_clavier', 'regler_zoom', 'regler_distance', 'reinitialiser_camera', 'distance_par_defaut', '_zoom_possible', '_suivre_scene', '_ctrl_actif'): self.assertFalse(hasattr(F.Jeu, nom), nom)
        for nom in ('_maj_camera', 'recentrer_camera', '_camera_pilotable', '_molette_appui', '_molette_glisse', '_molette_relache', '_camera_menee', '_coupure_camera', '_lacet_eff', '_tourner_dir', '_etat_axe'):
            self.assertTrue(hasattr(F.Jeu, nom), nom)
        src = inspect.getsource(F.Jeu._maj_camera)
        for mot in ("'accel'", 'vitesse_accel', 'angle_cam', 'cam_haut', 'cam_bas'): self.assertNotIn(mot, src, mot)         # la camera ne s'accelere plus, et n'a plus d'inclinaison
        for cle in ('distance_camera', 'angle_camera', 'camera_inverser_hb'): self.assertNotIn(cle, RG.DEFAUT, cle)
        for act in ('cam_pres', 'cam_loin'): self.assertNotIn(act, RG.TOUCHES_DEF, act)
        for cle in ('distance_camera', 'angle_camera', 'camera_inverser_hb'): self.assertIn(cle, RG.CLES_OBSOLETES, cle)

    def test_branchement_dans_la_boucle_et_le_dessin(self):
        """Les fils qui relient la camera au reste (on ne peut pas faire tourner la vraie boucle ici) : la mise a jour des fleches a chaque image, l'etat de la TownCamera du jeu a chaque pas (verrou, limite, scene, coupure),
        l'orientation des sprites et le deplacement du heros qui suivent la rotation."""
        boucle = inspect.getsource(F.Jeu._boucle)
        self.assertIn('self._maj_camera()', boucle)
        etat = [inspect.getsource(f) for n, f in inspect.getmembers(F.Jeu, inspect.isfunction) if 'lg, ld, vr = mo.camera_ville()' in inspect.getsource(f)]
        self.assertEqual(len(etat), 1, 'un seul endroit lit la TownCamera du jeu')
        for mot in ('self.cam_bloquee = lg < 0 or ld < 0 or vr', 'self._camera_menee(mo)', 'self._coupure_camera(mo.etat)', 'self.cam_saut = True', "self.cam_limite = min(lg, ld) * 360.0 / 4096.0", 'math.copysign(self.cam_limite, self.lacet)'): self.assertIn(mot, etat[0], mot)
        dessin = [inspect.getsource(f) for n, f in inspect.getmembers(F.Jeu, inspect.isfunction) if 'phi = ' in inspect.getsource(f) and '_lacet_eff' in inspect.getsource(f)]
        self.assertEqual(len(dessin), 1); self.assertIn('self._lacet_eff() if cam3d is not None else 0.0', dessin[0])
        self.assertIn('self._tourner_dir(p, int(round(self._lacet_eff() / 45.0)))', inspect.getsource(F.Jeu.pad))
        self.assertIn('self._molette_appui(x, y)', inspect.getsource(F.Jeu.on_mouse_press)); self.assertIn('self._molette_relache()', inspect.getsource(F.Jeu.on_mouse_release))
        self.assertIn('self.molette.annuler()', inspect.getsource(F.Jeu.on_deactivate)); self.assertIn('self.molette.annuler()', inspect.getsource(F.Jeu.on_mouse_motion))

    def test_reglages_de_la_camera(self):
        """Par defaut : Gauche > fleche gauche, Droite > fleche droite, vitesse de camera x1, sens du glissement non inverse. Visibles dans Commandes (voir test_pause_pages)."""
        self.assertEqual(RG.TOUCHES_DEF['cam_gauche'], ['LEFT', None]); self.assertEqual(RG.TOUCHES_DEF['cam_droite'], ['RIGHT', None])
        self.assertEqual(RG.DEFAUT['vitesse_camera'], 1.0); self.assertIs(RG.DEFAUT['camera_inverser_gd'], False)
        self.assertIn('vitesse_camera', RG.VITESSES_X_CLES); self.assertEqual(RG.BORNES['vitesse_camera'], (1.0, 4.0))
        for cle in ('vitesse_camera', 'camera_inverser_gd'): self.assertNotIn(cle, RG.CLES_OBSOLETES, cle)
        self.assertEqual(dict(RG.ACTIONS)['cam_gauche'], 'Caméra (Gauche)'); self.assertEqual(dict(RG.ACTIONS)['cam_droite'], 'Caméra (Droite)')
        self.assertEqual(F.CAM_LACET_VIT, 100.0)

    def test_ancien_fichier_de_reglages_lisible(self):
        """Un reglages.json d'avant #264 (distance, angle, vitesse de camera, touches Page haut / Page bas) se lit sans erreur : la vitesse de camera et le sens du glissement sont de nouveau valides et gardes ;
        les cles retirees (distance, angle, inversion haut / bas) ne sont pas reecrites."""
        import json, tempfile
        with tempfile.TemporaryDirectory() as d:
            ch = os.path.join(d, 'reglages.json')
            with open(ch, 'w', encoding='utf-8') as f: json.dump({'distance_camera': 150, 'angle_camera': 12.0, 'vitesse_camera': 3.0, 'camera_inverser_gd': True, 'camera_inverser_hb': True, 'vitesse_marche': 2.0, 'touches': {'cam_pres': ['PAGEUP', None], 'haut': ['W', None]}, 'touches_v': RG.DEFAUT['touches_v']}, f)
            r = RG.Reglages(ch); r.enregistrer()
            with open(ch, encoding='utf-8') as f: ecrit = json.load(f)
        self.assertEqual(r['vitesse_marche'], 2.0); self.assertEqual(r['touches']['haut'][0], 'W')
        self.assertEqual(r['vitesse_camera'], 3.0); self.assertIs(r['camera_inverser_gd'], True)
        for cle in ('distance_camera', 'angle_camera', 'camera_inverser_hb'): self.assertNotIn(cle, ecrit, cle)
        self.assertEqual(ecrit['vitesse_camera'], 3.0); self.assertIs(ecrit['camera_inverser_gd'], True); self.assertNotIn('cam_pres', ecrit['touches'])

    def test_camera_menee_predicat(self):
        def mo(cj, hero, cib):
            e = types.SimpleNamespace(sprites={0: {'pos': hero}} if hero else {}, cam_cible=cib)
            return types.SimpleNamespace(camera_jeu=lambda: cj, etat=e)
        cas = [((1, 6, 0, 0), (0, 0, 0), (0, 0, 0), False),          # verrou, cible = le joueur : rien ne change
               ((1, 0, 0, 0), (0, 0, 0), (0.3, 0, 0.2), False),      # verrou sans cible, camera sur le heros : rien ne change
               ((1, 0, 0, 0), (0, 0, 0), (3, 0, 0), True),           # plan fixe, heros ailleurs
               ((1, 5, 0, 0), (0, 0, 0), (0, 0, 0), True),           # cible = un personnage (grenouille)
               ((1, 4, 0, 1), (0, 0, 0), (0, 0, 0), True),           # retour vers le joueur : deplacement en cours
               ((1, 1, 0, 1), (0, 0, 0), (0, 0, 0), True),           # travelling
               ((1, 0, 0, 0), None, (0, 0, 0), True),                # heros hors champ
               ((1, 6, 0, 0), None, (9, 0, 9), False)]
        for cj, h, c, attendu in cas: self.assertEqual(F.Jeu._camera_menee(None, mo(cj, h, c)), attendu, (cj, h, c))

    def test_coupure_camera_predicat(self):
        """La cible du jeu a saute (changement de carte, plan de scene) : coupure ; un pas de marche : non."""
        def jeu(prec): return types.SimpleNamespace(prec=prec)
        def etat(carte, cib): return types.SimpleNamespace(partie=MO.PARTIE_VILLE, carte=carte, cam_cible=cib)
        pr = dict(cle=(MO.PARTIE_VILLE, 3), cam_cible=(0.0, 0.0, 0.0))
        self.assertTrue(F.Jeu._coupure_camera(jeu(None), etat(3, (0.0, 0.0, 0.0))))
        self.assertTrue(F.Jeu._coupure_camera(jeu(pr), etat(4, (0.0, 0.0, 0.0))))
        self.assertFalse(F.Jeu._coupure_camera(jeu(pr), etat(3, (0.3, 0.0, 0.1))))
        self.assertTrue(F.Jeu._coupure_camera(jeu(pr), etat(3, (F.CAM_SAUT_VILLE + 0.5, 0.0, 0.0))))
        self.assertTrue(F.Jeu._coupure_camera(jeu(pr), etat(3, None)))


if __name__ == '__main__':
    unittest.main(verbosity=2)
