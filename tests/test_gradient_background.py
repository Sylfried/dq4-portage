"""Test du fond des villes en degrade (#111) : le moteur envoie, par le paquet 8 (`cmd_back_color`, RVA 0xD14F44), DEUX couleurs (haut et bas de l'image) et le jeu les donne a `BackColor.SetColor(topmost, bottom, 0)`
(RVA 0xCC43F8) : un quadrilatere plein ecran dont les deux sommets du haut ont la couleur haut et ceux du bas la couleur bas (shader « BackColor » : `gl_Position = in_POSITION0`, `SV_Target0 = vs_COLOR0`,
file Background, ZTest Always, ZWrite Off, sans fusion). La visionneuse n'en gardait que la moyenne (fond uni).

  1. decodage du paquet 8 dans `State.apply` : `top_background`, `bottom_background`, `background` (moyenne : couleur d'effacement) ; remis a zero a chaque chargement de carte ; anciens etats enregistres ;
  2. `background_gradient` : vrai seulement si les deux couleurs different (sinon rien ne change, au pixel pres, par rapport a avant) ;
  3. rendu : un vrai degrade vertical lineaire (partie GL, facultative : ignoree s'il n'y a pas de contexte GL) ;
  4. moteur reel facultatif (DQ_APK et DQ_SAVES) : a l'heure du soir (heure du monde 1984 : zone 3), `mlout1` (village du prologue) recoit un degrade ; en journee (heure 1000) les deux couleurs sont egales.

    python3 tools/test_gradient_background.py        (Linux sans ecran : pyglet en mode « headless » ; DQ_APK=<dossier des APK patches> DQ_SAVES=<dossier des sauvegardes> pour la partie moteur reel)
Les sauvegardes ne sont ouvertes qu'en lecture (le moteur ecrit dans un dossier temporaire).
"""
import os, pickle, struct, sys, tempfile, types, unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import pyglet
if sys.platform.startswith('linux') and not os.environ.get('DISPLAY'): pyglet.options['headless'] = True; pyglet.options['shadow_window'] = False
from dq4_pc.core import engine as ENGINE
from dq4_pc.window import game as F

APK, SAVES = os.environ.get('DQ_APK'), os.environ.get('DQ_SAVES')
EVENING = [0.645, 0.516, 0.581, 0.839, 0.419, 0.194]               # mlout1 le soir (zone 3) : rose-gris en haut, orange en bas (entree 3 de param_map_backcolor, valeurs sur 31)


def pkt(*packets): return [(t, list(a), list(f)) for t, a, f in packets]


class StateDecoding(unittest.TestCase):
    def test_packet_8_keeps_both_colors(self):
        e = ENGINE.State(); e.apply(pkt((8, [], EVENING)), lambda: 'x')
        self.assertEqual(e.top_background, tuple(EVENING[:3])); self.assertEqual(e.bottom_background, tuple(EVENING[3:]))
        for a, h, b in zip(e.background, EVENING[:3], EVENING[3:]): self.assertAlmostEqual(a, (h + b) / 2, 9)           # couleur d'effacement = moyenne, comme avant

    def test_incomplete_packet_ignored(self):
        e = ENGINE.State(); e.apply(pkt((8, [], EVENING[:5])), lambda: 'x')
        self.assertIsNone(e.top_background); self.assertIsNone(e.bottom_background); self.assertEqual(e.background, (0.0, 0.0, 0.0))

    def test_last_color_wins(self):
        e = ENGINE.State(); e.apply(pkt((8, [], EVENING)), lambda: 'x'); e.apply(pkt((8, [], [0.1, 0.2, 0.3, 0.4, 0.5, 0.6])), lambda: 'x')           # fondu de couleur du jeu : un paquet par image
        self.assertEqual(e.top_background, (0.1, 0.2, 0.3)); self.assertEqual(e.bottom_background, (0.4, 0.5, 0.6))

    def test_new_map_resets_to_zero(self):
        e = ENGINE.State(); e.apply(pkt((8, [], EVENING)), lambda: 'x')
        e.apply(pkt((0, [0], [])), lambda: 'mlb1a')
        self.assertIsNone(e.top_background); self.assertIsNone(e.bottom_background); self.assertEqual(e.background, (0.0, 0.0, 0.0))
        e.apply(pkt((0, [0], []), (8, [], EVENING)), lambda: 'mlb1a')                       # le moteur envoie la couleur APRES le paquet 0, dans la meme image
        self.assertEqual(e.top_background, tuple(EVENING[:3]))

    def test_old_stored_state(self):
        e = ENGINE.State(); d = dict(e.__dict__); del d['top_background']; del d['bottom_background']
        e2 = ENGINE.State.__new__(ENGINE.State); e2.__setstate__(d)
        self.assertIsNone(e2.top_background); self.assertIsNone(e2.bottom_background)
        e3 = pickle.loads(pickle.dumps(ENGINE.State())); self.assertIsNone(e3.top_background)


class Gradient(unittest.TestCase):
    def test_real_gradient_only_if_the_colors_differ(self):
        self.assertTrue(F.background_gradient(EVENING[:3], EVENING[3:]))
        self.assertTrue(F.background_gradient((0.032, 0.323, 0.581), (0.032, 0.258, 0.516)))                  # nuit : degrade discret, mais un degrade
        self.assertFalse(F.background_gradient((0.452, 0.581, 1.0), (0.452, 0.581, 1.0)), 'jour : fond uni, comme avant')
        self.assertFalse(F.background_gradient(None, None), 'sans paquet 8')
        self.assertFalse(F.background_gradient(None, (1.0, 1.0, 1.0)))
        self.assertFalse(F.background_gradient((0.0, 0.0, 0.0), (0.0, 0.0, 0.0)), 'interieurs : noir')

    def test_shader_like_back_color(self):
        """Le sommet est ecrit tel quel en espace de decoupe (gl_Position = in_POSITION0) : pas de matrice ; la couleur est celle de sommet, sans autre terme (SV_Target0 = vs_COLOR0)."""
        self.assertIn('gl_Position = vec4(position, 0.0, 1.0)', F.VERTEX_GRADIENT); self.assertNotIn('mvp', F.VERTEX_GRADIENT)
        self.assertIn('fragColor = vec4(v_col, 1.0)', F.FRAG_GRADIENT); self.assertNotIn('tex', F.FRAG_GRADIENT)


def gl_window(l=64, h=64):
    try:
        return pyglet.window.Window(l, h, visible=False)
    except Exception:
        return None


class GLRender(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.win = gl_window()
        if cls.win is None: raise unittest.SkipTest('pas de contexte GL ici')

    @classmethod
    def tearDownClass(cls):
        if cls.win is not None: cls.win.close()

    def read(self, topmost, bottom):
        from pyglet import gl
        self.win.switch_to(); gl.glViewport(0, 0, self.win.width, self.win.height); gl.glClearColor(0.0, 0.0, 0.0, 1.0); gl.glClear(gl.GL_COLOR_BUFFER_BIT | gl.GL_DEPTH_BUFFER_BIT)
        game = types.SimpleNamespace(program_gradient=None, gradient_vl=None)
        F.Game._paint_background_gradient(game, topmost, bottom)
        data = pyglet.image.get_buffer_manager().get_color_buffer().get_image_data().get_data('RGB', self.win.width * 3)
        return [[tuple(data[(y * self.win.width + x) * 3:(y * self.win.width + x) * 3 + 3]) for x in range(self.win.width)] for y in range(self.win.height)]      # ligne 0 = bas de l'image

    def test_linear_vertical_gradient(self):
        """Tolerance de 9 niveaux : le tampon d'image du contexte sans ecran (EGL) est en 5-6-5 bits (marches de 8 / 4 / 8 niveaux) ; un degrade a l'envers ou non lineaire s'ecarterait de 50 a 100 niveaux."""
        img = self.read(EVENING[:3], EVENING[3:]); h = len(img)
        topmost = tuple(round(255 * c) for c in EVENING[:3]); bottom = tuple(round(255 * c) for c in EVENING[3:])
        for x in (0, 31, 63):
            for a, b in zip(img[h - 1][x], topmost): self.assertLessEqual(abs(a - b), 9, 'haut de l\'image')
            for a, b in zip(img[0][x], bottom): self.assertLessEqual(abs(a - b), 9, 'bas de l\'image')
        for y in range(h):
            t = (y + 0.5) / h                                                            # 0 en bas, 1 en haut
            expected = [255 * (EVENING[3 + i] * (1 - t) + EVENING[i] * t) for i in range(3)]
            for a, b in zip(img[y][10], expected): self.assertLessEqual(abs(a - b), 9, 'ligne %d' % y)
            self.assertEqual(img[y][0], img[y][63], 'la couleur ne depend que de la hauteur (ligne %d)' % y)

    def test_equal_colors_give_flat(self):
        img = self.read((0.452, 0.581, 1.0), (0.452, 0.581, 1.0))
        self.assertEqual(img[0][0], img[63][63])


@unittest.skipUnless(APK and SAVES, 'moteur reel : DQ_APK=<dossier des APK patches> DQ_SAVES=<dossier des sauvegardes>')
class RealEngine(unittest.TestCase):
    @staticmethod
    def backgrounds(hour):
        eng = ENGINE.Engine(APK, SAVES, tempfile.mkdtemp(prefix='sv_fond_'))
        for _ in range(3): eng.step(0, 0)
        eng.load_save(1)
        for _ in range(10): eng.step(0, 0)
        c = eng.core; g = struct.unpack('<Q', bytes(c.mem(eng.L + 0x23d430, 8)))[0]                   # StageStatus : heure du monde en + 0xcc
        c.mem_w(g + 0xcc, struct.pack('<i', hour))
        c.call(eng.E('_ZN3cmn13WorldLocation18setCurrentTimeZoneEv'), c.call(eng.E('_ZN3cmn13WorldLocation12getSingletonEv'), label='wl'), label='zone')
        eng.start_town('caf1')
        for _ in range(40): eng.step(0, 0)
        eng.start_town('mlout1')
        for _ in range(120): eng.step(0, 0)
        return eng.state

    def test_prologue_village_depending_on_the_hour(self):
        evening = self.backgrounds(1984)
        self.assertEqual(evening.game_map, 'mlout1')
        self.assertTrue(F.background_gradient(evening.top_background, evening.bottom_background), 'le soir : degrade')
        for a, b in zip(evening.top_background, EVENING[:3]): self.assertAlmostEqual(a, b, 3)
        for a, b in zip(evening.bottom_background, EVENING[3:]): self.assertAlmostEqual(a, b, 3)
        day = self.backgrounds(1000)
        self.assertFalse(F.background_gradient(day.top_background, day.bottom_background), 'le jour : aplat (les deux couleurs de la table sont egales)')


if __name__ == '__main__':
    unittest.main(verbosity=2)
