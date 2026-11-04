"""#241 (audit ENG-05, sondage du 04/11/2026 : « liste blanche de classes ») : un fichier d'etat (.dqs) recu d'une autre personne ne doit pas pouvoir executer de code a la lecture (le pickle peut appeler n'importe quelle
fonction d'un module importable). `etats._Depickler` n'accepte que les classes du portage (`Etat`, `Interface`), les conteneurs de base, les tableaux numpy et trois conteneurs de `collections`.
Sans APK : pickles fabriques (dont des pieges : os.system, eval, subprocess, noms avec point, classes du portage hors liste). Avec l'APK (DQ_APK, DQ_SAVES) : de vrais etats (ville, carte du monde, combat) restent lisibles.
    python3 tests/test_etats_liste_blanche.py"""
import collections, io, os, pickle, shutil, struct, sys, tempfile, unittest, zlib

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import numpy as np
from dq4_pc.persistance import etats as ET
APK, SAVES = os.environ.get('DQ_APK'), os.environ.get('DQ_SAVES')


def temoin():
    d = tempfile.mkdtemp(prefix='dqs_piege_'); return os.path.join(d, 'execute.txt')


class Piege:
    """Un objet dont le pickle appelle `fonction(*args)` a la lecture (la technique classique)."""
    def __init__(self, fonction, *args): self.f, self.a = fonction, args
    def __reduce__(self): return (self.f, self.a)


class Lisible(unittest.TestCase):
    def test_conteneurs_de_base_et_numpy(self):
        d = {'a': [1, 2.5, 'x', b'y', (3, 4), {5, 6}, frozenset({7}), None, True, bytearray(b'z'), 3 + 4j, slice(1, 2), range(3)], 'tab': np.arange(12, dtype=np.float32).reshape(3, 4),
             'sc': np.float32(2.5), 'od': collections.OrderedDict(a=1), 'dd': collections.defaultdict(list, {1: [2]}), 'dq': collections.deque([1, 2])}
        for proto in (4, 5):
            r = ET._charger(pickle.dumps(d, protocol=proto))
            self.assertEqual(r['a'], d['a']); self.assertTrue((r['tab'] == d['tab']).all()); self.assertEqual(r['sc'], d['sc']); self.assertEqual(r['od'], d['od']); self.assertEqual(r['dq'], d['dq']); self.assertEqual(dict(r['dd']), {1: [2]})

    def test_classes_du_portage(self):
        from dq4_pc.noyau import moteur as MO
        e = MO.Etat(); e.carte = 'ev01'; e.sprites = {1: {'pos': np.zeros(3, np.float32), 'id': 7}}
        r = ET._charger(pickle.dumps({'etat': e}, protocol=pickle.HIGHEST_PROTOCOL))['etat']
        self.assertIsInstance(r, MO.Etat); self.assertEqual(r.carte, 'ev01'); self.assertEqual(r.sprites[1]['id'], 7)

    def test_anciens_noms_de_modules(self):
        """Un etat d'avant le rangement du 04/11/2026 dit `moteur.Etat` : relu (le nom est traduit d'abord, la liste blanche s'applique ensuite)."""
        from dq4_pc.noyau import moteur as MO
        brut = pickle.dumps(MO.Etat(), protocol=3); self.assertIn(b'cdq4_pc.noyau.moteur\nEtat\n', brut)
        ancien = brut.replace(b'cdq4_pc.noyau.moteur\nEtat\n', b'cmoteur\nEtat\n')
        self.assertIsInstance(ET._charger(ancien), MO.Etat)

    def test_fichier_complet_ecrire_lire(self):
        d = {'version': ET.VERSION, 'lib': [(3, b'\x00' * 8)], 'heap': b'abc', 'python': pickle.dumps({'etat': None}), 'viewer': pickle.dumps({'k': np.ones(2)})}
        f = os.path.join(tempfile.mkdtemp(prefix='dqs_ok_'), 'etat_01.dqs'); ET.ecrire(f, d, {'lieu': 'x'})
        r = ET.lire(f); self.assertEqual(r['heap'], b'abc'); self.assertEqual(r['lib'], [(3, b'\x00' * 8)])
        self.assertEqual(ET._charger(r['python']), {'etat': None}); self.assertTrue((ET._charger(r['viewer'])['k'] == np.ones(2)).all())


class Refuse(unittest.TestCase):
    def verifie(self, piege, attendu=None, proto=pickle.HIGHEST_PROTOCOL):
        f = temoin()
        with self.assertRaises(pickle.UnpicklingError) as cm: ET._charger(pickle.dumps(piege(f), protocol=proto))
        self.assertFalse(os.path.exists(f), 'le piege a ete execute')
        if attendu: self.assertIn(attendu, str(cm.exception))

    def test_os_system(self):
        for proto in (0, 2, 4, 5): self.verifie(lambda f: Piege(os.system, 'echo piege > ' + f), 'system', proto)

    def test_eval_exec_open_import(self):
        self.verifie(lambda f: Piege(eval, "open(%r, 'w').write('x')" % f), 'builtins.eval')
        self.verifie(lambda f: Piege(exec, "open(%r, 'w').write('x')" % f), 'builtins.exec')
        self.verifie(lambda f: Piege(open, f, 'w'), '.open')                                  # (open est pickle sous le nom _io.open)
        self.verifie(lambda f: Piege(__import__, 'os'), 'builtins.__import__')
        self.verifie(lambda f: Piege(getattr, 'x', 'upper'), 'builtins.getattr')

    def test_subprocess_et_autres_modules(self):
        import subprocess, shutil as sh
        self.verifie(lambda f: Piege(subprocess.Popen, ['touch', f]), 'subprocess')
        self.verifie(lambda f: Piege(subprocess.check_output, ['touch', f]), 'subprocess')
        self.verifie(lambda f: Piege(sh.copyfile, __file__, f), 'shutil')

    def test_numpy_hors_liste(self):
        self.verifie(lambda f: Piege(np.save, f, np.zeros(1)), 'numpy')                    # (numpy.save : un module de numpy que la liste ne contient pas)
        self.verifie(lambda f: Piege(np.load, f), 'numpy')

    def test_classes_du_portage_hors_liste(self):
        from dq4_pc.noyau import moteur as MO
        self.verifie(lambda f: Piege(MO.Moteur, f, f, f), 'Moteur')                          # (le constructeur du moteur ne doit pas etre appelable par un fichier)
        self.verifie(lambda f: Piege(MO.CoreJeu), 'CoreJeu')

    def test_noms_avec_point_sur_un_module_autorise(self):
        """Protocole 4 : `STACK_GLOBAL` accepte « os.system » comme nom dans le module `dq4_pc.noyau.moteur` (qui importe os) ; la liste blanche compare le nom entier : refuse."""
        f = temoin()
        for module, nom in (('dq4_pc.noyau.moteur', 'os.system'), ('collections', 'sys.modules'), ('builtins', 'eval.__self__')):
            octets = (b'\x80\x04\x95' + struct.pack('<Q', 0)) if False else None
            brut = b'\x80\x04' + b'\x8c' + bytes([len(module)]) + module.encode() + b'\x8c' + bytes([len(nom)]) + nom.encode() + b'\x93' + b'.'          # PROTO 4, SHORT_BINUNICODE, SHORT_BINUNICODE, STACK_GLOBAL, STOP
            with self.assertRaises(pickle.UnpicklingError): ET._charger(brut)
        self.assertFalse(os.path.exists(f))

    def test_piege_dans_un_fichier_complet(self):
        """Un etat dont la partie `python` ou `viewer` est piegee : `lire` rend le dictionnaire (rien d'execute, ce sont des octets), `appliquer` refuse AVANT d'ecrire dans le moteur (#206)."""
        f = temoin(); mot = temoin()
        d = {'version': ET.VERSION, 'lib': [], 'heap': b'', 'heap_ptr': 0, 'data': b'', 'tls': b'', 'data_ptr': 0, 'next_file': 0, 'fichiers': {}, 'python': pickle.dumps(Piege(os.system, 'echo x > ' + mot)), 'viewer': b''}
        chemin = os.path.join(os.path.dirname(f), 'etat_09.dqs'); ET.ecrire(chemin, d, {})
        lu = ET.lire(chemin); self.assertFalse(os.path.exists(mot))
        import types
        ecritures = []
        core = types.SimpleNamespace(uc=types.SimpleNamespace(mem_write=lambda *a: ecritures.append(a)), LIB_BASE=0, elf=types.SimpleNamespace(img=b'x'), heap_ptr=0, HEAP_BASE=0, DATA_BASE=0, TLS_BASE=0, data_ptr=0, next_file=0, files={})
        m = types.SimpleNamespace(core=core, log=lambda *a: None, ui=types.SimpleNamespace(obs=None))
        with self.assertRaises(pickle.UnpicklingError): ET.appliquer(m, lu)
        self.assertEqual(ecritures, []); self.assertFalse(os.path.exists(mot))

    def test_piege_dans_le_conteneur_externe(self):
        f = temoin(); chemin = os.path.join(os.path.dirname(f), 'etat_08.dqs')
        with open(chemin, 'wb') as fh:
            fh.write(ET.MAGIE); ent = b'{}'; fh.write(struct.pack('<I', len(ent))); fh.write(ent); fh.write(struct.pack('<I', 0))
            fh.write(zlib.compress(pickle.dumps(Piege(os.system, 'echo x > ' + f))))
        with self.assertRaises(pickle.UnpicklingError): ET.lire(chemin)
        self.assertFalse(os.path.exists(f))

    def test_message_en_francais_et_nom_de_la_classe(self):
        try: ET._charger(pickle.dumps(Piege(os.system, 'x')))
        except pickle.UnpicklingError as ex: msg = str(ex)
        self.assertIn('refusé', msg); self.assertIn('system', msg); self.assertIn('pas été exécuté', msg)


@unittest.skipUnless(APK and SAVES, 'moteur reel : DQ_APK=<dossier des APK patches> DQ_SAVES=<dossier des sauvegardes>')
class VraisEtats(unittest.TestCase):
    """Les etats que le portage ecrit vraiment (carte du monde, ville, combat force, apres un menu) restent lisibles : la liste blanche ne doit jamais empecher de recharger un etat legitime."""
    @classmethod
    def setUpClass(cls):
        import unicorn
        from dq4_pc.noyau import moteur as MO
        cls.MO, cls.unicorn = MO, unicorn
        cls.ecr = tempfile.mkdtemp(prefix='sv_liste_blanche_')
        cls.mo = MO.Moteur(APK, SAVES, cls.ecr); cls.c = cls.mo.core

    def relire(self, etiquette):
        viewer = {'objets_etat': {'a': np.zeros((2, 3), np.float32), 'b': [np.arange(3)]}, 'carte_nom': 'x', 'motif_n': 1, 'motif_acc': np.zeros(2), 'musique': None, 'palettes': {1: (1, 2)}}
        d = ET.instantane(self.mo, viewer); f = os.path.join(self.ecr, 'e_%s.dqs' % etiquette); ET.ecrire(f, d, {'lieu': etiquette})
        r = ET.lire(f); p = ET._charger(r['python']); v = ET._charger(r['viewer'])
        self.assertIsInstance(p['etat'], self.MO.Etat); self.assertIsInstance(p['ui'], self.MO.Interface); self.assertTrue((v['objets_etat']['a'] == 0).all())
        ET.appliquer(self.mo, r)                                                            # (et il s'applique)

    def test_ville_et_monde(self):
        for slot in (1, 4):
            self.mo.charger_sauvegarde(slot)
            for k in range(250):
                self.mo.step(0, 0)
                if k in (60, 249): self.relire('slot%d_%d' % (slot, k))

    def test_combat(self):
        MO, mo, c = self.MO, self.mo, self.c
        mo.charger_sauvegarde(1)
        for _ in range(200): mo.step(0, 0)
        enc = c.call(c.export('_ZN7Encount12getSingletonEv'), label='enc')
        def groupe(u, adr, sz, ud):
            for j in range(4):
                i, n = (3, 1) if j == 0 else (0, 0)
                c.mem_w(enc + 0x34 + 4 * j, struct.pack('<I', i)); c.mem_w(enc + 0x44 + 4 * j, struct.pack('<I', n))
        a = c.export('_ZN10BattleRoot12setupMonsterEv'); c.uc.hook_add(self.unicorn.UC_HOOK_CODE, groupe, None, a, a); c.uc.ctl_flush_tb()
        for _ in range(3): mo.step(0, 0)
        c.call(c.export('_ZN6Global11startBattleEv'), mo._global(), label='startBattle')
        n = 0
        while mo.etat.partie != MO.PARTIE_COMBAT and n < 1500: mo.step(0, 0); n += 1
        self.assertEqual(mo.etat.partie, MO.PARTIE_COMBAT)
        for i in range(120):
            mo.step(0, 0); mo.ui.degats = []
            if i % 40 == 0: self.relire('combat_%d' % i)


if __name__ == '__main__':
    unittest.main(verbosity=1)
