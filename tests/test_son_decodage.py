"""Decodage des fichiers AKB (son.py) : Ogg ecrete (#200, audit SND-02), boucle des bruitages (#201, audit SND-03).
Lancer depuis la racine : PYTHONPATH=. python3 tests/test_son_decodage.py (sans carte son ; soundfile necessaire pour les cas Ogg)."""
import io, os, shutil, struct, sys, tempfile, threading, unittest, zipfile
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


def akb_ogg(n_ech=4000, debut=0, fin=0, volume=1.0):
    """Un AKB (codec 5 = Ogg) minimal : un son de n_ech echantillons, avec un debut et une fin de boucle declares dans l'en-tete."""
    sr = 22050; x = (0.3 * np.sin(2 * np.pi * 330 * np.arange(n_ech) / sr)).astype('float32')[:, None]
    b = io.BytesIO(); sf.write(b, x, sr, format='OGG', subtype='VORBIS')
    entete = bytearray(S.DEBUT_DONNEES); entete[:4] = b'AKB '
    struct.pack_into('<BBHIII', entete, 0x0c, 5, 1, sr, n_ech, debut, fin); struct.pack_into('<f', entete, 0x20, volume)
    return bytes(entete) + b.getvalue()


@unittest.skipIf(sf is None, 'soundfile absent')
class BoucleQuiDepasse(unittest.TestCase):
    """#201 (audit SND-03) : une fin de boucle qui depasse de quelques echantillons la fin des donnees (reste d'un bloc ADPCM) est ramenee a la fin des donnees."""
    def test_fin_juste_apres_les_donnees_boucle_jusqu_a_la_fin(self):
        n = len(S.decoder_akb(akb_ogg(4000))['pcm'])
        r = S.decoder_akb(akb_ogg(4000, debut=100, fin=n + 5))
        self.assertTrue(r['boucle']); self.assertEqual(r['debut'], 100); self.assertEqual(r['fin'], n)

    def test_fin_exactement_a_la_fin_inchange(self):
        n = len(S.decoder_akb(akb_ogg(4000))['pcm']); r = S.decoder_akb(akb_ogg(4000, debut=0, fin=n))
        self.assertTrue(r['boucle']); self.assertEqual(r['fin'], n)

    def test_fin_tres_au_dela_reste_sans_boucle(self):
        n = len(S.decoder_akb(akb_ogg(4000))['pcm'])
        r = S.decoder_akb(akb_ogg(4000, debut=0, fin=n + S.TOLERANCE_FIN_BOUCLE + 1))
        self.assertFalse(r['boucle']); self.assertEqual((r['debut'], r['fin']), (0, 0))

    def test_sans_boucle_et_debut_apres_la_fin(self):
        self.assertFalse(S.decoder_akb(akb_ogg(4000, debut=0, fin=0))['boucle'])
        n = len(S.decoder_akb(akb_ogg(4000))['pcm']); self.assertFalse(S.decoder_akb(akb_ogg(4000, debut=n + 3, fin=n + 4))['boucle'])


@unittest.skipIf(sf is None, 'soundfile absent')
class CacheDesBruitages(unittest.TestCase):
    """Le cache disque des bruitages (son_SE*.npz) d'une ancienne version (sans les boucles de #201) est refait."""
    def setUp(self):
        self.d = tempfile.mkdtemp(); self.addCleanup(shutil.rmtree, self.d, True)
        self.apk = os.path.join(self.d, 'sons.apk')
        n = len(S.decoder_akb(akb_ogg(4000))['pcm'])
        with zipfile.ZipFile(self.apk, 'w') as z: z.writestr('assets/sound/SE0001.akb', akb_ogg(4000, debut=0, fin=n + 5))
        self.cache = os.path.join(self.d, 'cache'); os.makedirs(self.cache)
        self.son = object.__new__(S.Son); self.son.apk, self.son.cache, self.son.log = self.apk, self.cache, print; self.son.verrou = threading.Lock(); self.son.zip = None
        self.n = n

    def test_cache_ancien_refait(self):
        f = os.path.join(self.cache, 'son_SE0001.npz')
        np.savez(f, pcm=np.zeros((self.n, 1), np.int16), p=np.array([22050, 0, 0, 0], np.int64), v=np.array([1.0], np.float32))          # ancien format : 4 valeurs, sans boucle
        r = self.son._decode('SE0001')
        self.assertTrue(r['boucle']); self.assertEqual(r['fin'], self.n); self.assertGreater(int(np.abs(r['pcm']).max()), 100)     # re-decode (pas les zeros du cache)
        self.assertEqual(int(np.load(f)['p'][4]), S.VERSION_CACHE_SON)                                                              # et cache reecrit a la version courante

    def test_cache_courant_relu(self):
        self.son._decode('SE0001'); os.remove(self.apk); self.son.zip = None                                                         # plus de source : seul le cache peut repondre
        r = self.son._decode('SE0001'); self.assertTrue(r['boucle']); self.assertEqual(r['fin'], self.n)


if __name__ == '__main__': unittest.main(verbosity=1)
