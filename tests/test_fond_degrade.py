"""Test du fond des villes en degrade (#111) : le moteur envoie, par le paquet 8 (`cmd_back_color`, RVA 0xD14F44), DEUX couleurs (haut et bas de l'image) et le jeu les donne a `BackColor.SetColor(haut, bas, 0)`
(RVA 0xCC43F8) : un quadrilatere plein ecran dont les deux sommets du haut ont la couleur haut et ceux du bas la couleur bas (shader « BackColor » : `gl_Position = in_POSITION0`, `SV_Target0 = vs_COLOR0`,
file Background, ZTest Always, ZWrite Off, sans fusion). La visionneuse n'en gardait que la moyenne (fond uni).

  1. decodage du paquet 8 dans `Etat.appliquer` : `fond_haut`, `fond_bas`, `fond` (moyenne : couleur d'effacement) ; remis a zero a chaque chargement de carte ; anciens etats enregistres ;
  2. `degrade_fond` : vrai seulement si les deux couleurs different (sinon rien ne change, au pixel pres, par rapport a avant) ;
  3. rendu : un vrai degrade vertical lineaire (partie GL, facultative : ignoree s'il n'y a pas de contexte GL) ;
  4. moteur reel facultatif (DQ_APK et DQ_SAVES) : a l'heure du soir (heure du monde 1984 : zone 3), `mlout1` (village du prologue) recoit un degrade ; en journee (heure 1000) les deux couleurs sont egales.

    python3 outils/test_fond_degrade.py        (Linux sans ecran : pyglet en mode « headless » ; DQ_APK=<dossier des APK patches> DQ_SAVES=<dossier des sauvegardes> pour la partie moteur reel)
Les sauvegardes ne sont ouvertes qu'en lecture (le moteur ecrit dans un dossier temporaire).
"""
import os, pickle, struct, sys, tempfile, types, unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import pyglet
if sys.platform.startswith('linux') and not os.environ.get('DISPLAY'): pyglet.options['headless'] = True; pyglet.options['shadow_window'] = False
from dq4_pc.noyau import moteur as MO
from dq4_pc.fenetre import jeu as F

APK, SAVES = os.environ.get('DQ_APK'), os.environ.get('DQ_SAVES')
SOIR = [0.645, 0.516, 0.581, 0.839, 0.419, 0.194]               # mlout1 le soir (zone 3) : rose-gris en haut, orange en bas (entree 3 de param_map_backcolor, valeurs sur 31)


def pq(*paquets): return [(t, list(a), list(f)) for t, a, f in paquets]


class DecodageEtat(unittest.TestCase):
    def test_paquet_8_garde_les_deux_couleurs(self):
        e = MO.Etat(); e.appliquer(pq((8, [], SOIR)), lambda: 'x')
        self.assertEqual(e.fond_haut, tuple(SOIR[:3])); self.assertEqual(e.fond_bas, tuple(SOIR[3:]))
        for a, h, b in zip(e.fond, SOIR[:3], SOIR[3:]): self.assertAlmostEqual(a, (h + b) / 2, 9)           # couleur d'effacement = moyenne, comme avant

    def test_paquet_incomplet_ignore(self):
        e = MO.Etat(); e.appliquer(pq((8, [], SOIR[:5])), lambda: 'x')
        self.assertIsNone(e.fond_haut); self.assertIsNone(e.fond_bas); self.assertEqual(e.fond, (0.0, 0.0, 0.0))

    def test_la_derniere_couleur_gagne(self):
        e = MO.Etat(); e.appliquer(pq((8, [], SOIR)), lambda: 'x'); e.appliquer(pq((8, [], [0.1, 0.2, 0.3, 0.4, 0.5, 0.6])), lambda: 'x')           # fondu de couleur du jeu : un paquet par image
        self.assertEqual(e.fond_haut, (0.1, 0.2, 0.3)); self.assertEqual(e.fond_bas, (0.4, 0.5, 0.6))

    def test_nouvelle_carte_remet_a_zero(self):
        e = MO.Etat(); e.appliquer(pq((8, [], SOIR)), lambda: 'x')
        e.appliquer(pq((0, [0], [])), lambda: 'mlb1a')
        self.assertIsNone(e.fond_haut); self.assertIsNone(e.fond_bas); self.assertEqual(e.fond, (0.0, 0.0, 0.0))
        e.appliquer(pq((0, [0], []), (8, [], SOIR)), lambda: 'mlb1a')                       # le moteur envoie la couleur APRES le paquet 0, dans la meme image
        self.assertEqual(e.fond_haut, tuple(SOIR[:3]))

    def test_ancien_etat_enregistre(self):
        e = MO.Etat(); d = dict(e.__dict__); del d['fond_haut']; del d['fond_bas']
        e2 = MO.Etat.__new__(MO.Etat); e2.__setstate__(d)
        self.assertIsNone(e2.fond_haut); self.assertIsNone(e2.fond_bas)
        e3 = pickle.loads(pickle.dumps(MO.Etat())); self.assertIsNone(e3.fond_haut)


class Degrade(unittest.TestCase):
    def test_vrai_degrade_seulement_si_les_couleurs_different(self):
        self.assertTrue(F.degrade_fond(SOIR[:3], SOIR[3:]))
        self.assertTrue(F.degrade_fond((0.032, 0.323, 0.581), (0.032, 0.258, 0.516)))                  # nuit : degrade discret, mais un degrade
        self.assertFalse(F.degrade_fond((0.452, 0.581, 1.0), (0.452, 0.581, 1.0)), 'jour : fond uni, comme avant')
        self.assertFalse(F.degrade_fond(None, None), 'sans paquet 8')
        self.assertFalse(F.degrade_fond(None, (1.0, 1.0, 1.0)))
        self.assertFalse(F.degrade_fond((0.0, 0.0, 0.0), (0.0, 0.0, 0.0)), 'interieurs : noir')

    def test_shader_comme_back_color(self):
        """Le sommet est ecrit tel quel en espace de decoupe (gl_Position = in_POSITION0) : pas de matrice ; la couleur est celle de sommet, sans autre terme (SV_Target0 = vs_COLOR0)."""
        self.assertIn('gl_Position = vec4(position, 0.0, 1.0)', F.VERT_DEGRADE); self.assertNotIn('mvp', F.VERT_DEGRADE)
        self.assertIn('fragColor = vec4(v_col, 1.0)', F.FRAG_DEGRADE); self.assertNotIn('tex', F.FRAG_DEGRADE)


def fenetre_gl(l=64, h=64):
    try:
        return pyglet.window.Window(l, h, visible=False)
    except Exception:
        return None


class RenduGL(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.win = fenetre_gl()
        if cls.win is None: raise unittest.SkipTest('pas de contexte GL ici')

    @classmethod
    def tearDownClass(cls):
        if cls.win is not None: cls.win.close()

    def lire(self, haut, bas):
        from pyglet import gl
        self.win.switch_to(); gl.glViewport(0, 0, self.win.width, self.win.height); gl.glClearColor(0.0, 0.0, 0.0, 1.0); gl.glClear(gl.GL_COLOR_BUFFER_BIT | gl.GL_DEPTH_BUFFER_BIT)
        jeu = types.SimpleNamespace(prog_degrade=None, degrade_vl=None)
        F.Jeu._tracer_degrade_fond(jeu, haut, bas)
        data = pyglet.image.get_buffer_manager().get_color_buffer().get_image_data().get_data('RGB', self.win.width * 3)
        return [[tuple(data[(y * self.win.width + x) * 3:(y * self.win.width + x) * 3 + 3]) for x in range(self.win.width)] for y in range(self.win.height)]      # ligne 0 = bas de l'image

    def test_degrade_vertical_lineaire(self):
        """Tolerance de 9 niveaux : le tampon d'image du contexte sans ecran (EGL) est en 5-6-5 bits (marches de 8 / 4 / 8 niveaux) ; un degrade a l'envers ou non lineaire s'ecarterait de 50 a 100 niveaux."""
        img = self.lire(SOIR[:3], SOIR[3:]); h = len(img)
        haut = tuple(round(255 * c) for c in SOIR[:3]); bas = tuple(round(255 * c) for c in SOIR[3:])
        for x in (0, 31, 63):
            for a, b in zip(img[h - 1][x], haut): self.assertLessEqual(abs(a - b), 9, 'haut de l\'image')
            for a, b in zip(img[0][x], bas): self.assertLessEqual(abs(a - b), 9, 'bas de l\'image')
        for y in range(h):
            t = (y + 0.5) / h                                                            # 0 en bas, 1 en haut
            attendu = [255 * (SOIR[3 + i] * (1 - t) + SOIR[i] * t) for i in range(3)]
            for a, b in zip(img[y][10], attendu): self.assertLessEqual(abs(a - b), 9, 'ligne %d' % y)
            self.assertEqual(img[y][0], img[y][63], 'la couleur ne depend que de la hauteur (ligne %d)' % y)

    def test_couleurs_egales_donnent_un_aplat(self):
        img = self.lire((0.452, 0.581, 1.0), (0.452, 0.581, 1.0))
        self.assertEqual(img[0][0], img[63][63])


@unittest.skipUnless(APK and SAVES, 'moteur reel : DQ_APK=<dossier des APK patches> DQ_SAVES=<dossier des sauvegardes>')
class MoteurReel(unittest.TestCase):
    @staticmethod
    def fonds(heure):
        mo = MO.Moteur(APK, SAVES, tempfile.mkdtemp(prefix='sv_fond_'))
        for _ in range(3): mo.step(0, 0)
        mo.charger_sauvegarde(1)
        for _ in range(10): mo.step(0, 0)
        c = mo.core; g = struct.unpack('<Q', bytes(c.mem(mo.L + 0x23d430, 8)))[0]                   # StageStatus : heure du monde en + 0xcc
        c.mem_w(g + 0xcc, struct.pack('<i', heure))
        c.call(mo.E('_ZN3cmn13WorldLocation18setCurrentTimeZoneEv'), c.call(mo.E('_ZN3cmn13WorldLocation12getSingletonEv'), label='wl'), label='zone')
        mo.demarrer_ville('caf1')
        for _ in range(40): mo.step(0, 0)
        mo.demarrer_ville('mlout1')
        for _ in range(120): mo.step(0, 0)
        return mo.etat

    def test_village_du_prologue_selon_l_heure(self):
        soir = self.fonds(1984)
        self.assertEqual(soir.carte, 'mlout1')
        self.assertTrue(F.degrade_fond(soir.fond_haut, soir.fond_bas), 'le soir : degrade')
        for a, b in zip(soir.fond_haut, SOIR[:3]): self.assertAlmostEqual(a, b, 3)
        for a, b in zip(soir.fond_bas, SOIR[3:]): self.assertAlmostEqual(a, b, 3)
        jour = self.fonds(1000)
        self.assertFalse(F.degrade_fond(jour.fond_haut, jour.fond_bas), 'le jour : aplat (les deux couleurs de la table sont egales)')


if __name__ == '__main__':
    unittest.main(verbosity=2)
