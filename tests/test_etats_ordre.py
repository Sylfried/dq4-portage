"""#206 (audit ENG-06) : charger un etat instantane ne touche pas au moteur si l'etat est inutilisable (fichier abime, autre bibliotheque) ; l'empreinte de la bibliotheque est enregistree.
Sans APK : cas avec faux moteur. Avec l'APK (DQ_APK) : le meme essai sur le vrai moteur.
    python3 tests/test_etats_ordre.py"""
import hashlib, os, shutil, sys, tempfile, types, unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from dq4_pc.persistance import etats
APK = os.environ.get('DQ_APK', '/mnt/user-data/uploads/DQ Patch/jeux/DQ4/patched_apks')


def faux_moteur(ecritures, img=b'bibliotheque'):
    uc = types.SimpleNamespace(mem_write=lambda *a: ecritures.append(a))
    core = types.SimpleNamespace(uc=uc, LIB_BASE=0x1000, elf=types.SimpleNamespace(img=img), heap_ptr=0, HEAP_BASE=0, DATA_BASE=0, TLS_BASE=0, data_ptr=0, next_file=0, files={})
    return types.SimpleNamespace(core=core, log=lambda *a: None, ui=types.SimpleNamespace(obs=None))


def etat_vide(**plus):
    d = {'version': etats.VERSION, 'lib': [], 'heap': b'', 'heap_ptr': 0, 'data': b'', 'tls': b'', 'data_ptr': 0, 'next_file': 0, 'fichiers': {}, 'python': b'pas un pickle', 'viewer': b''}
    d.update(plus); return d


class SansMoteurReel(unittest.TestCase):
    def test_empreinte(self):
        m = faux_moteur([], img=b'abc'); self.assertEqual(etats.empreinte_lib(m.core), hashlib.sha256(b'abc').hexdigest()[:16])

    def test_autre_bibliotheque_refusee_sans_rien_ecrire(self):
        ecr = []; m = faux_moteur(ecr)
        with self.assertRaises(ValueError) as cm: etats.appliquer(m, etat_vide(lib_sha='0' * 16))
        self.assertIn('bibliotheque', str(cm.exception)); self.assertEqual(ecr, [])

    def test_python_illisible_ne_touche_pas_au_moteur(self):
        ecr = []; m = faux_moteur(ecr)
        with self.assertRaises(Exception): etats.appliquer(m, etat_vide(lib_sha=etats.empreinte_lib(m.core)))
        self.assertEqual(ecr, [])                                                   # avant : la memoire du moteur etait deja ecrasee

    def test_etat_ancien_sans_empreinte_passe_la_porte_et_echoue_plus_loin_sans_ecrire(self):
        ecr = []; m = faux_moteur(ecr)
        with self.assertRaises(Exception) as cm: etats.appliquer(m, etat_vide())
        self.assertNotIn('bibliotheque', str(cm.exception)); self.assertEqual(ecr, [])

    def test_version_refusee(self):
        ecr = []; m = faux_moteur(ecr)
        with self.assertRaises(ValueError): etats.appliquer(m, etat_vide(version=99))
        self.assertEqual(ecr, [])


@unittest.skipUnless(os.path.exists(os.path.join(APK, 'split_config.arm64_v8a.apk')), 'pas d\'APK du jeu')
class AvecLeVraiMoteur(unittest.TestCase):
    def test_echec_laisse_le_moteur_intact_et_l_empreinte_est_la(self):
        from dq4_pc.noyau import moteur as MO
        ecr = tempfile.mkdtemp(prefix='sv_test_ordre_'); lec = tempfile.mkdtemp(prefix='sv_test_ordre_l_')
        try:
            m = MO.Moteur(APK, lec, ecr)
            for _ in range(5): m.step(0, 0)
            d = etats.instantane(m); c = m.core
            self.assertEqual(d['lib_sha'], etats.empreinte_lib(c)); self.assertEqual(len(d['lib_sha']), 16)
            for _ in range(10): m.step(0, 0)                                          # le moteur avance : sa memoire differe maintenant de celle de l'etat
            avant = hashlib.sha256(c.mem(c.DATA_BASE, c.DATA_SIZE) + c.mem(c.HEAP_BASE, c.heap_ptr - c.HEAP_BASE)).hexdigest(); ptr = c.heap_ptr
            abime = dict(d, python=d['python'][:20])                                    # pickle tronque
            with self.assertRaises(Exception): etats.appliquer(m, abime)
            apres = hashlib.sha256(c.mem(c.DATA_BASE, c.DATA_SIZE) + c.mem(c.HEAP_BASE, c.heap_ptr - c.HEAP_BASE)).hexdigest()
            self.assertEqual((avant, ptr), (apres, c.heap_ptr))
            etats.appliquer(m, d)                                                        # l'etat sain se charge encore
            self.assertEqual(c.heap_ptr, d['heap_ptr'])
        finally: shutil.rmtree(ecr, True); shutil.rmtree(lec, True)


if __name__ == '__main__': unittest.main(verbosity=1)
