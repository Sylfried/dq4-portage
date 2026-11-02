"""Test de la priorite du jeu sur les reglages du joueur : « quand le jeu fixe lui-meme une valeur par script, il prime sur le reglage du joueur ».

  1. regles pures (priorite_jeu.py) : valeur_effective, facteur_effectif, lettres_par_image, duree_fondu ;
  2. vitesse de marche (`Jeu._facteur_vitesse`, sur un faux objet) : sans effet pendant un evenement (verrou du joueur) ou un fondu, appliquee en terrain libre ;
  3. zoom de la camera (`Jeu._camera_ville`, faux objet) : appliquee, sauf camera libre d'une scene (cadrage du jeu) ;
  4. moteur d'origine (si --apk et --saves sont donnes) : vitesse du texte fixee par le jeu (le mot de vitesse du message est modifie en cours de route) ; fondu lance par une commande de script du jeu
     (la sauvegarde --slot-fondu, par defaut 2 : debut du prologue, commande fade_out de 30 images) non raccourci, fondu du moteur raccourci.

    python3 outils/test_priorite_jeu.py [--apk "<dossier des APK patches>" --saves "<dossier des sauvegardes>" [--slot 4] [--slot-fondu 2]]
Les sauvegardes ne sont ouvertes qu'en lecture : le moteur ecrit dans un dossier temporaire.
"""
import argparse, os, sys, tempfile, types, unittest

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'dq4_pc'))
import pyglet
if sys.platform.startswith('linux') and not os.environ.get('DISPLAY'): pyglet.options['headless'] = True; pyglet.options['shadow_window'] = False
import priorite_jeu as PJ
import moteur as MO
import fenetre as F

ARGS = None


class ReglesPures(unittest.TestCase):
    def test_valeur_effective(self):
        for joueur, jeu in ((4.0, None), (16.0, None), (0.5, 8), (4000.0, 0), (0, 0.0), (None, 3)):
            self.assertEqual(PJ.valeur_effective(joueur, jeu), joueur if jeu is None else jeu, (joueur, jeu))
        self.assertEqual(PJ.valeur_effective(16.0), 16.0)
        self.assertEqual(PJ.valeur_effective(16.0, 0), 0, 'une valeur du jeu egale a zero est une valeur du jeu')

    def test_facteur_effectif(self):
        self.assertEqual(PJ.facteur_effectif(2.0, False), 2.0)
        self.assertEqual(PJ.facteur_effectif(2.0, True), 1.0)
        self.assertEqual(PJ.facteur_effectif(0.5, True), 1.0)
        self.assertEqual(PJ.facteur_effectif(3.0, True, neutre=1.5), 1.5)

    def test_lettres_par_image(self):
        for joueur in (0.5, 1.0, 2.0, 4.0, 8.0, 16.0, 4000.0):
            self.assertEqual(PJ.lettres_par_image(joueur, PJ.LETTRES_STANDARD), joueur, 'dialogue ordinaire : le reglage du joueur')
            self.assertEqual(PJ.lettres_par_image(joueur, 400), 400, 'fenetre de combat (vitesse 100) : celle du jeu')
            self.assertEqual(PJ.lettres_par_image(joueur, 8), 8, 'vitesse fixee par le jeu (mot 2) : celle du jeu, quel que soit le reglage')
            self.assertEqual(PJ.lettres_par_image(joueur, 2), 2, 'vitesse fixee par le jeu (mot 0,5) : plus lente que le standard, elle prime aussi')
        self.assertEqual(PJ.lettres_par_image(16.0, 8, standard=8), 16.0, 'un autre standard (autre jeu) : le reglage s\'applique a celui-la')

    def test_duree_fondu(self):
        for duree, facteur, attendu in ((30, 1.0, 30), (30, 2.0, 15), (45, 2.0, 22), (60, 4.0, 15), (1, 4.0, 1), (0, 4.0, 0), (3, 4.0, 1), (30, 0.5, 30)):
            self.assertEqual(PJ.duree_fondu(duree, facteur), attendu, (duree, facteur))
            self.assertEqual(PJ.duree_fondu(duree, facteur, script=True), duree, 'fondu de script : duree du script')
        self.assertEqual(PJ.duree_fondu(30, 2.0, script=False), 15)

    def test_marque_hors_champs_du_paquet(self):
        """La marque des fondus de script n'empiete sur aucun champ de l'entier du paquet 9 (duree 0x7ff, couleur 0x800, sortie 0x1000, blanc 0x2000, plan de fond 0x4000)."""
        self.assertEqual(PJ.MARQUE_FONDU_SCRIPT & 0x7fff, 0)
        e = MO.Etat(); MO.Etat.vitesse_fondu = 2.0
        try:
            e._fondu(0x1000 | 30, ()); self.assertEqual(e.fondu['n'], 15, 'fondu du moteur raccourci')
            e._fondu(0x1000 | 30 | PJ.MARQUE_FONDU_SCRIPT, ()); self.assertEqual(e.fondu['n'], 30, 'fondu de script : intact')
            e._fondu(0x5000 | 30 | PJ.MARQUE_FONDU_SCRIPT, ()); self.assertEqual(e.fondu_fond['n'], 30); self.assertEqual(e.fondu_fond['fin'], 1.0, 'les autres champs sont lus comme avant')
            e._fondu(0x1000 | 0x800 | 30, (0.1, 0.2, 0.3)); self.assertEqual(e.fondu['n'], 30, 'fondu en couleur : jamais raccourci'); self.assertEqual(e.fondu['col'], (0.1, 0.2, 0.3))
        finally: MO.Etat.vitesse_fondu = 1.0


def faux_jeu_marche(marche=2.0, accel=1.5, drapeaux=0x28, msg=False, partie=MO.PARTIE_VILLE, direction=MO.DROITE, accel_tenue=False):
    mo = types.SimpleNamespace(etat=types.SimpleNamespace(partie=partie, effet=None, attente_charge=None), msg_visible=msg, menu_actif=lambda: None, drapeaux=lambda: drapeaux)
    return types.SimpleNamespace(reg={'vitesse_marche': marche, 'vitesse_accel': accel}, moteur=mo, pad=lambda: direction, _tenue=lambda a: accel_tenue and a == 'accel')


class VitesseDeMarche(unittest.TestCase):
    def facteur(self, **kw): return F.Jeu._facteur_vitesse(faux_jeu_marche(**kw))

    def test_terrain_libre(self):
        self.assertEqual(self.facteur(), 2.0)
        self.assertEqual(self.facteur(accel_tenue=True), 3.0, 'accelerateur tenu : x2 x 1,5')
        self.assertEqual(self.facteur(drapeaux=0x28 | 0x40), 2.0, 'verrou de l\'interface seul (bit 0x40) : sans effet ici')

    def test_le_jeu_a_la_main(self):
        self.assertEqual(self.facteur(drapeaux=0x28 | 0x4), 1.0, 'verrou du joueur (evenement, scene) sans message : marche non acceleree')
        self.assertEqual(self.facteur(drapeaux=0x3c, accel_tenue=True), 1.0)
        self.assertEqual(self.facteur(drapeaux=0x28 | 0x1), 1.0, 'fondu en cours : non acceleree')
        self.assertEqual(self.facteur(drapeaux=0x28 | 0x5), 1.0)

    def test_inchange(self):
        self.assertEqual(self.facteur(msg=True), 1.0)
        self.assertEqual(self.facteur(partie=MO.PARTIE_COMBAT), 1.0)
        self.assertEqual(self.facteur(direction=0), 1.0, 'aucune direction tenue')
        self.assertEqual(self.facteur(marche=1.0, accel=1.0), 1.0)


class ZoomDeCamera(unittest.TestCase):
    """Zoom du reglage « distance de la camera » : divise le champ vertical de la camera des villes ; une camera libre de scene (paquet 11, bit 7) garde le cadrage du jeu."""
    def setUp(self):
        self.temps_avant = F.time
        F.time = types.SimpleNamespace(perf_counter=lambda: 0.0, time=lambda: 0.0, sleep=lambda *a: None)

    def tearDown(self): F.time = self.temps_avant

    def champ(self, zoom, libre):
        j = types.SimpleNamespace(zoom=zoom, reg={'camera_centree': False}, cam_jeu=False, cam_saut=True, cam_dec=[0.0, 0.0], cam_res=[0.0, 0.0], cam_centre=False, cam_poids=1.0, t_centre=None, fixe_test=True,
                                  bornes_x=None, lacet=0.0, angle_cam=0.0, cam_bloquee=False, carte_nom='x', n_boucle=0, _cadre_vue=None)
        j._rot_camera = lambda e: np.eye(3)
        cib = np.array([0.0, 0.0, 0.0])
        e = types.SimpleNamespace(cam_pos=cib + np.array([0.0, 28.94, -27.0]), cam_cible=cib, cam_fov=None, cam_near=None, cam_far=None, cam_yoff=None, cam_bas=None, cam_libre=libre,
                                  cam_rot=(40.0, 0.0, 0.0) if libre else None, sprites={0: {'pos': (0.0, 0.0, 0.0)}})
        M, _ = F.Jeu._camera_ville(j, e, 16.0 / 9.0)
        return M[0, 0] if abs(M[0, 0]) > abs(M[1, 1]) else M[1, 1]

    def test_zoom_applique_en_exploration(self):
        self.assertAlmostEqual(self.champ(2.0, False) / self.champ(1.0, False), 2.0, places=6, msg='zoom x2 : le champ est deux fois plus etroit')
        self.assertAlmostEqual(self.champ(0.5, False) / self.champ(1.0, False), 0.5, places=6)

    def test_camera_libre_de_scene_sans_zoom(self):
        ref = self.champ(1.0, True)
        for z in (0.5, 2.0): self.assertAlmostEqual(self.champ(z, True), ref, places=9, msg='camera libre : zoom %s sans effet' % z)


def images_texte_mot(vitesse, mot_jeu, slot):
    """Comme test_texte_defilement.images_texte, mais le mot de vitesse de la fenetre de message est ecrit a `mot_jeu` (un script du jeu qui fixe la vitesse) des l'ouverture du message ; None = non touche.
    Renvoie (images entre l'ouverture du message et la fin de sa premiere page, lettres de la page)."""
    mo = MO.Moteur(ARGS.apk, ARGS.saves, tempfile.mkdtemp(prefix='sv_test_prio_'))
    for _ in range(3): mo.step(0, 0)
    mo.charger_sauvegarde(slot); mo.vitesse_texte = vitesse
    for _ in range(70): mo.step(0, 0)
    mo.step(0, 0x800)
    t_ouv = None; ok = 0
    for i in range(1500):
        p = mo.menu_actif()
        if mo.msg_visible: pass
        elif p is not None and i % 14 == 4 and ok < 4: mo.envoyer_menu(p, 1, -1, 0x10); ok += 1
        elif p is not None and i % 14 == 5: mo.envoyer_menu(p, 1, -1, 0)
        if mot_jeu is not None and t_ouv is not None: mo.core.mem_w(mo.L + MO.MSG_VITESSE, int(mot_jeu).to_bytes(2, 'little'))
        mo.step(0, 0)
        actif, etat, _, fin, mot = mo.etat_message()
        if actif == 1 and t_ouv is None:
            t_ouv = mo.images
            if mot_jeu is not None: mo.core.mem_w(mo.L + MO.MSG_VITESSE, int(mot_jeu).to_bytes(2, 'little'))
        if t_ouv is not None and etat in (3, 5): return mo.images - t_ouv, fin
    return None, None


def fondus_du_prologue(facteur, slot, n=450):
    """[(image, duree d'origine, duree appliquee, fondu de script ?)] des fondus au noir du moteur depuis le chargement de la sauvegarde `slot`."""
    mo = MO.Moteur(ARGS.apk, ARGS.saves, tempfile.mkdtemp(prefix='sv_test_prio_'))
    for _ in range(3): mo.step(0, 0)
    res = []; orig = MO.Etat._fondu
    def espion(self, v, f):
        r = orig(self, v, f)
        if not v & (0x800 | 0x2000): res.append((mo.images, v & 0x7ff, (self.fondu_fond if v & 0x4000 else self.fondu)['n'] if (v & 0x7ff) > 1 else 0, bool(v & PJ.MARQUE_FONDU_SCRIPT)))
        return r
    MO.Etat._fondu = espion; MO.Etat.vitesse_fondu = facteur
    try:
        mo.charger_sauvegarde(slot)
        for i in range(n): mo.step(0, 0x10 if i % 40 == 0 else 0)
    finally: MO.Etat._fondu = orig; MO.Etat.vitesse_fondu = 1.0
    return res


@unittest.skipIf(ARGS is None and '--apk' not in sys.argv, 'moteur d\'origine : --apk et --saves requis')
class Moteur(unittest.TestCase):
    def test_texte_fixe_par_le_jeu(self):
        """Mot de vitesse fixe par le jeu (2 = 8 lettres par image) : meme duree quel que soit le reglage du joueur ; sans cela le reglage s'applique."""
        sans = {v: images_texte_mot(v, None, ARGS.slot)[0] for v in (0.5, 16.0)}
        avec = {v: images_texte_mot(v, 2, ARGS.slot) for v in (0.5, 4.0, 16.0, 4000.0)}
        print('reglage seul : %s ; mot fixe a 2 par le jeu : %s' % (sans, avec))
        self.assertGreater(sans[0.5], 3 * sans[16.0], 'sans valeur du jeu, le reglage change la duree')
        self.assertEqual(len({n for n, _ in avec.values()}), 1, 'le jeu a fixe sa vitesse : le reglage du joueur n\'y change rien')
        equivalent = images_texte_mot(8.0, None, ARGS.slot)                  # reglage du joueur = 8 lettres par image, rien fixe par le jeu : la meme duree que le mot 2 du jeu
        self.assertEqual(avec[4.0], equivalent, 'la vitesse du jeu (mot 2 = 8 lettres par image) est bien celle qui s\'applique : %s contre %s' % (avec[4.0], equivalent))

    def test_fondu_de_script(self):
        brut = fondus_du_prologue(1.0, ARGS.slot_fondu); rapide = fondus_du_prologue(4.0, ARGS.slot_fondu)
        print('fondus x1 : %s\nfondus x4 : %s' % (brut, rapide))
        self.assertTrue(any(s for _, _, _, s in brut), 'un fondu lance par un script du jeu est reconnu (fade_out du debut du prologue)')
        self.assertTrue(any(not s and d > 4 for _, d, _, s in brut), 'et des fondus du moteur aussi')
        for (_, d, ap, s), (_, d4, ap4, s4) in zip(brut, rapide):
            self.assertEqual((d, s), (d4, s4))
            self.assertEqual(ap, d if d > 1 else 0, 'x1 : duree d\'origine')
            if s: self.assertEqual(ap4, ap, 'fondu de script : jamais raccourci')
            elif d > 1: self.assertEqual(ap4, max(1, round(d / 4.0)), 'fondu du moteur : divise par 4')


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--apk'); ap.add_argument('--saves'); ap.add_argument('--slot', type=int, default=4); ap.add_argument('--slot-fondu', type=int, default=2, dest='slot_fondu')
    ARGS, reste = ap.parse_known_args()
    if not (ARGS.apk and ARGS.saves): ARGS = None
    unittest.main(argv=[sys.argv[0]] + reste, verbosity=2)
