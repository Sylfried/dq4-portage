"""Un etat instantane (savestate) enregistre par une version qui n'avait pas encore un correctif memoire de la visionneuse (fenetre des lieux elargie, « Sauv. cloud » retiree, bouton « Paramètres »)
ne doit pas les faire perdre : etats.appliquer recharge l'image d'origine de la bibliotheque puis rejoue `Moteur.reappliquer_correctifs`.
(Ignore sans l'APK : DQ_APK, sinon /mnt/user-data/uploads/DQ Patch/jeux/DQ4/patched_apks ; ecritures dans un dossier temporaire, jamais dans les sauvegardes de l'utilisateur.)

    python3 outils/test_etats_correctifs.py
"""
import os, shutil, struct, sys, tempfile, unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'dq4_pc'))
APK = os.environ.get('DQ_APK', '/mnt/user-data/uploads/DQ Patch/jeux/DQ4/patched_apks')


@unittest.skipUnless(os.path.exists(os.path.join(APK, 'split_config.arm64_v8a.apk')), 'pas d\'APK du jeu')
class TestEtatAncien(unittest.TestCase):
    def test_correctifs_rejoues(self):
        import moteur as MO, etats
        ecr = tempfile.mkdtemp(prefix='sv_test_etats_'); lec = tempfile.mkdtemp(prefix='sv_test_lec_')
        try:
            m = MO.Moteur(APK, lec, ecr)
            for _ in range(5): m.step(0, 0)
            c = m.core; a = c.export('_ZN9FieldData10drawSymbolEv')
            immediat = lambda dec: (struct.unpack('<I', c.mem(a + dec, 4))[0] >> 10) & 0xfff
            self.assertEqual([immediat(d) for d in (0x44, 0x48, 0x4c)], [1600] * 3)      # moteur neuf : correctif pose
            d = etats.instantane(m)
            img = bytes(c.elf.img); P = etats.PAGE
            ancien = [(a - c.LIB_BASE + k, 4) for k in (0x44, 0x48, 0x4c)] + [(m.CMP_PARAMETRES, 4), (MO.G_IS_AMAZON, 1)]       # etat « ancien » : ces octets de la bibliotheque sont ceux de l'image d'origine
            pages = dict(d['lib'])
            for off, n in ancien:
                pg = bytearray(pages.get(off // P) or img[(off // P) * P:(off // P + 1) * P]); pg[off % P:off % P + n] = img[off:off + n]; pages[off // P] = bytes(pg)
            d['lib'] = sorted(pages.items())
            self.assertEqual(c.mem(m.L + MO.G_IS_AMAZON, 1), b'\x01')
            etats.appliquer(m, d)
            self.assertEqual([immediat(x) for x in (0x44, 0x48, 0x4c)], [1600] * 3)
            self.assertEqual(c.mem(m.L + MO.G_IS_AMAZON, 1), b'\x01')
            w = struct.unpack('<I', c.mem(c.LIB_BASE + m.CMP_PARAMETRES, 4))[0]
            self.assertEqual((w >> 10) & 0xfff, 0xfff)
            for _ in range(5): m.step(0, 0)                  # le moteur tourne toujours
        finally:
            shutil.rmtree(ecr, ignore_errors=True); shutil.rmtree(lec, ignore_errors=True)


if __name__ == '__main__':
    unittest.main(verbosity=1)
