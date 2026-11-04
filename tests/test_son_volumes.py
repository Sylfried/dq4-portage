"""#237 (audit SND-01, sondage du 04/11/2026 : « aligner sur l'original ») : le volume de chaque son est celui de l'en-tete du fichier multiplie par `assets/sound/snd_vol.dat` (1171 flottants, indices = numero de fichier
BGM ou numero de bruitage), comme `SoundControl.Play` d'Unity : 49 musiques de 0,7 a 0,95 et la fanfare SE0409 a 0,6. Fichier absent ou indice hors table : 1,0.
Sans fenetre ni carte son (faux lecteurs, faux APK).
    python3 tests/test_son_volumes.py"""
import os, sys, tempfile, unittest, zipfile
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
sys.modules['pyglet'] = None                                             # pas de pyglet : Son le prend pour « son indisponible », on lui donne de faux lecteurs
from dq4_pc import son as SON


class FauxLecteur:
    def __init__(self): self.playing = False; self.volume = 1.0
    def queue(self, src): pass
    def play(self): self.playing = True
    def pause(self): self.playing = False
    def delete(self): self.playing = False


class FauxMedia:
    Player = FauxLecteur


class FauxSource:
    def __init__(self, *a): self.pos = 0


def apk_avec(table):
    """Un faux APK (zip) qui contient assets/sound/snd_vol.dat (ou rien si table est None)."""
    f = os.path.join(tempfile.mkdtemp(prefix='apk_vol_'), 'faux.apk')
    with zipfile.ZipFile(f, 'w') as z:
        z.writestr('assets/readme.txt', 'x')
        if table is not None: z.writestr('assets/sound/snd_vol.dat', np.asarray(table, '<f4').tobytes())
    return f


def table_standard():
    t = np.ones(1171, np.float32); t[1] = 0.7; t[2] = 0.8; t[14] = 1.0; t[409] = 0.6
    return t


def nouveau_son(apk, **kw):
    s = SON.Son(apk, tempfile.mkdtemp(prefix='cache_son_'), log=lambda *a: None, journal=lambda *a: None, alerte=lambda *a: None, **kw)
    s.ok = True; s.ogg = True; s.media = FauxMedia; s.AudioFormat = lambda **kw: kw; s.AudioData = None
    SON.SourceBoucle = FauxSource
    return s


def donnees(volume, boucle=True, secondes=2.0):
    n = int(secondes * 1000)
    return dict(pcm=np.zeros((n, 1), np.int16), frequence=1000, debut=0, fin=n if boucle else 0, volume=volume, boucle=boucle)


class TableDeVolumes(unittest.TestCase):
    def test_lecture(self):
        s = nouveau_son(apk_avec(table_standard()))
        for ident, v in ((1, 0.7), (2, 0.8), (14, 1.0), (409, 0.6), (300, 1.0), (1170, 1.0)): self.assertAlmostEqual(s.vol_snd(ident), v, 6, ident)

    def test_hors_table(self):
        s = nouveau_son(apk_avec(table_standard()))
        for ident in (-1, 1171, 5000): self.assertEqual(s.vol_snd(ident), 1.0, ident)

    def test_fichier_absent_ou_illisible(self):
        self.assertEqual(nouveau_son(apk_avec(None)).vol_snd(1), 1.0)
        self.assertEqual(nouveau_son('inexistant.apk').vol_snd(409), 1.0)
        self.assertEqual(nouveau_son(apk_avec([0.5, 0.5, 0.5])).vol_snd(1), 0.5)               # (table plus courte : valable pour ses indices, 1,0 au-dela)
        self.assertEqual(nouveau_son(apk_avec([0.5, 0.5, 0.5])).vol_snd(500), 1.0)

    def test_valeur_absurde_ignoree(self):
        t = table_standard(); t[3] = 0.0; t[4] = 7.5; t[5] = float('nan'); t[6] = -1.0; s = nouveau_son(apk_avec(t))
        for ident in (3, 4, 5, 6): self.assertEqual(s.vol_snd(ident), 1.0, ident)            # (0, > 1, nan, negatif : pas de silence ni de gain)

    def test_lue_une_seule_fois(self):
        s = nouveau_son(apk_avec(table_standard())); s.vol_snd(1); t = s._table_vol; s.vol_snd(2); self.assertIs(s._table_vol, t)


class VolumeJoue(unittest.TestCase):
    def test_musique(self):
        s = nouveau_son(apk_avec(table_standard()))
        s.bgm_demande = 1; s._lancer_bgm(1, donnees(0.65))
        self.assertAlmostEqual(s.bgm.volume, 0.65 * 0.7, 6); self.assertAlmostEqual(s.bgm_propre, 0.65 * 0.7, 6)
        s.bgm_demande = 14; s._lancer_bgm(14, donnees(0.9))
        self.assertAlmostEqual(s.bgm.volume, 0.9, 6)                                         # (BGM14 : 1,0, inchangee)

    def test_bruitage_fanfare(self):
        s = nouveau_son(apk_avec(table_standard()))
        s._lancer_se(409, donnees(1.0, False)); self.assertAlmostEqual(s.se[-1].p.volume, 0.6, 6); self.assertAlmostEqual(s.se[-1].propre, 0.6, 6)
        s._lancer_se(300, donnees(1.0, False)); self.assertAlmostEqual(s.se[-1].p.volume, 1.0, 6)

    def test_curseurs_et_options_restent_multiplies(self):
        s = nouveau_son(apk_avec(table_standard()), volume_musique=0.5)
        s.mix.jeu['musique'] = 0.8
        s.bgm_demande = 2; s._lancer_bgm(2, donnees(0.75))
        self.assertAlmostEqual(s.bgm.volume, 0.5 * 0.8 * 0.75 * 0.8, 6)                       # curseur x option du jeu x en-tete x snd_vol
        s.mix.vol['musique'] = 1.0; s._appliquer_volumes(); self.assertAlmostEqual(s.bgm.volume, 1.0 * 0.8 * 0.75 * 0.8, 6)      # (un reglage change plus tard garde le facteur du fichier)

    def test_sans_table_rien_ne_change(self):
        s = nouveau_son(apk_avec(None)); s.bgm_demande = 1; s._lancer_bgm(1, donnees(0.65)); self.assertAlmostEqual(s.bgm.volume, 0.65, 6)


if __name__ == '__main__':
    unittest.main(verbosity=2)
