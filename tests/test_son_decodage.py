"""Decodage des fichiers AKB (son.py) : Ogg ecrete (#200, audit SND-02), boucle des bruitages (#201, audit SND-03).
Lancer depuis la racine : PYTHONPATH=. python3 tests/test_son_decodage.py (sans carte son ; soundfile necessaire pour les cas Ogg)."""
import io, os, struct, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
from dq4_pc import son as S

try: import soundfile as sf
except Exception: sf = None


def ogg_surmodule():
    """Un Ogg Vorbis d'un signal carre presque plein : apres decodage il depasse +-1,0 (surmodulation normale de Vorbis)."""
    sr = 44100; t = np.arange(sr * 2) / sr
    x = np.sign(np.sin(2 * np.pi * 440 * t)) * 0.999
    x = np.stack([x, x], 1).astype('float32')
    b = io.BytesIO(); sf.write(b, x, sr, format='OGG', subtype='VORBIS'); return b.getvalue()


@unittest.skipIf(sf is None, 'soundfile absent')
class OggEcrete(unittest.TestCase):
    def test_le_signal_surmodule_depasse_bien_en_flottant(self):
        f, _ = sf.read(io.BytesIO(ogg_surmodule()), dtype='float32', always_2d=True)
        self.assertGreater(float(np.abs(f).max()), 1.05)                       # (le cas test est bien un cas de depassement)

    def test_pas_de_debordement(self):
        d = ogg_surmodule(); f, _ = sf.read(io.BytesIO(d), dtype='float32', always_2d=True)
        pcm = S.decoder_ogg(d)
        self.assertEqual(pcm.dtype, np.int16); self.assertEqual(pcm.shape, f.shape)
        ref = np.clip(np.rint(f * 32767.0), -32768, 32767)
        self.assertEqual(int(np.abs(pcm.astype(np.int64) - ref.astype(np.int64)).max()), 0)
        # un pic positif reste positif (la lecture directe en int16 le retournait en pic negatif)
        i = int(np.argmax(f[:, 0])); self.assertGreater(int(pcm[i, 0]), 30000)
        i = int(np.argmin(f[:, 0])); self.assertLess(int(pcm[i, 0]), -30000)
        self.assertEqual(int(pcm.max()), 32767); self.assertEqual(int(pcm.min()), -32768)

    def test_signal_normal_inchange_a_un_pres(self):
        sr = 22050; t = np.arange(sr) / sr; x = (0.3 * np.sin(2 * np.pi * 330 * t)).astype('float32')[:, None]
        b = io.BytesIO(); sf.write(b, x, sr, format='OGG', subtype='VORBIS')
        direct, _ = sf.read(io.BytesIO(b.getvalue()), dtype='int16', always_2d=True)
        self.assertLessEqual(int(np.abs(S.decoder_ogg(b.getvalue()).astype(np.int64) - direct.astype(np.int64)).max()), 1)

    def test_decoder_akb_passe_par_decoder_ogg(self):
        entete = bytearray(S.DEBUT_DONNEES); entete[:4] = b'AKB '
        ogg = ogg_surmodule(); struct.pack_into('<BBHIII', entete, 0x0c, 5, 2, 44100, 88200, 0, 0); struct.pack_into('<f', entete, 0x20, 1.0)
        r = S.decoder_akb(bytes(entete) + ogg)
        self.assertEqual(r['pcm'].dtype, np.int16); self.assertEqual(int(r['pcm'].max()), 32767); self.assertFalse(r['boucle'])


if __name__ == '__main__': unittest.main(verbosity=1)
