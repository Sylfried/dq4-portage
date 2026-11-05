"""#241 (audit ENG-05, sondage du 04/11/2026 : « liste blanche de classes ») : un fichier d'etat (.dqs) recu d'une autre personne ne doit pas pouvoir executer de code a la lecture (le pickle peut appeler n'importe quelle
fonction d'un module importable). `savestates._Unpickler` n'accepte que les classes du portage (`State`, `Interface`), les conteneurs de base, les tableaux numpy et trois conteneurs de `collections`.
Sans APK : pickles fabriques (dont des pieges : os.system, eval, subprocess, noms avec point, classes du portage hors liste). Avec l'APK (DQ_APK, DQ_SAVES) : de vrais etats (ville, carte du monde, combat) restent lisibles.
    python3 tests/test_savestates_whitelist.py"""
import collections, io, os, pickle, shutil, struct, sys, tempfile, unittest, zlib

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from dq4_pc import language as _LANGUAGE; _LANGUAGE.select_language('fr')          # (D-238 : ces tests attendent les textes francais, quelle que soit la langue de l'ordinateur)
import numpy as np
from dq4_pc.persistence import savestates as SS
APK, SAVES = os.environ.get('DQ_APK'), os.environ.get('DQ_SAVES')


def control():
    d = tempfile.mkdtemp(prefix='dqs_piege_'); return os.path.join(d, 'execute.txt')


class Trap:
    """Un objet dont le pickle appelle `function(*args)` a la lecture (la technique classique)."""
    def __init__(self, function, *args): self.f, self.a = function, args
    def __reduce__(self): return (self.f, self.a)


class Readable(unittest.TestCase):
    def test_base_containers_and_numpy(self):
        d = {'a': [1, 2.5, 'x', b'y', (3, 4), {5, 6}, frozenset({7}), None, True, bytearray(b'z'), 3 + 4j, slice(1, 2), range(3)], 'tab': np.arange(12, dtype=np.float32).reshape(3, 4),
             'sc': np.float32(2.5), 'od': collections.OrderedDict(a=1), 'dd': collections.defaultdict(list, {1: [2]}), 'dq': collections.deque([1, 2])}
        for proto in (4, 5):
            r = SS._load(pickle.dumps(d, protocol=proto))
            self.assertEqual(r['a'], d['a']); self.assertTrue((r['tab'] == d['tab']).all()); self.assertEqual(r['sc'], d['sc']); self.assertEqual(r['od'], d['od']); self.assertEqual(r['dq'], d['dq']); self.assertEqual(dict(r['dd']), {1: [2]})

    def test_port_classes(self):
        from dq4_pc.core import engine as ENGINE
        e = ENGINE.State(); e.game_map = 'ev01'; e.sprites = {1: {'pos': np.zeros(3, np.float32), 'id': 7}}
        r = SS._load(pickle.dumps({'etat': e}, protocol=pickle.HIGHEST_PROTOCOL))['etat']
        self.assertIsInstance(r, ENGINE.State); self.assertEqual(r.game_map, 'ev01'); self.assertEqual(r.sprites[1]['id'], 7)

    def test_old_module_names(self):
        """Un etat d'avant le rangement du 04/11/2026 dit `engine.State` : relu (le nom est traduit d'abord, la liste blanche s'applique ensuite)."""
        from dq4_pc.core import engine as ENGINE
        raw_value = pickle.dumps(ENGINE.State(), protocol=3); self.assertIn(b'cdq4_pc.core.engine\nState\n', raw_value)
        old = raw_value.replace(b'cdq4_pc.core.engine\nState\n', b'cmoteur\nEtat\n')
        self.assertIsInstance(SS._load(old), ENGINE.State)

    def test_names_before_the_english_rename(self):
        """Un etat enregistre avant le passage a l'anglais (05/11/2026) dit `dq4_pc.noyau.moteur.Etat` et garde les anciens noms d'attributs (`carte`, `partie`, `fondu`...) : relu, il porte les noms actuels."""
        from dq4_pc.core import engine as ENGINE
        new_state = ENGINE.State(); new_state.game_map = 'ev01'; new_state.part = 12; new_state.fade['n'] = 3
        inverse = {v: k for k, v in ENGINE.OLD_ATTRIBUTES.items()}
        old_state = ENGINE.State.__new__(ENGINE.State); old_state.__dict__.update({inverse.get(k, k): v for k, v in new_state.__dict__.items()})        # (sans passer par __setstate__ : l'objet garde les anciens noms)
        self.assertIn('carte', old_state.__dict__); self.assertNotIn('game_map', old_state.__dict__)
        raw_value = pickle.dumps(old_state, protocol=3).replace(b'cdq4_pc.core.engine\nState\n', b'cdq4_pc.noyau.moteur\nEtat\n')
        r = SS._load(raw_value)
        self.assertIsInstance(r, ENGINE.State); self.assertEqual((r.game_map, r.part, r.fade['n']), ('ev01', 12, 3)); self.assertNotIn('carte', r.__dict__); self.assertNotIn('partie', r.__dict__)
        self.assertEqual(r.__dict__.keys(), new_state.__dict__.keys())
        ui = ENGINE.Interface(); ui.damage.append((1, 2, 3)); old_ui = ENGINE.Interface.__new__(ENGINE.Interface); old_ui.__dict__.update({inverse.get(k, k): v for k, v in ui.__dict__.items()})
        r_ui = SS._load(pickle.dumps(old_ui, protocol=3)); self.assertEqual(r_ui.damage, [(1, 2, 3)]); self.assertNotIn('degats', r_ui.__dict__)

    def test_complete_file_write_read(self):
        d = {'version': SS.VERSION, 'lib': [(3, b'\x00' * 8)], 'heap': b'abc', 'python': pickle.dumps({'etat': None}), 'viewer': pickle.dumps({'k': np.ones(2)})}
        f = os.path.join(tempfile.mkdtemp(prefix='dqs_ok_'), 'state_01.dqs'); SS.write(f, d, {'lieu': 'x'})
        r = SS.read(f); self.assertEqual(r['heap'], b'abc'); self.assertEqual(r['lib'], [(3, b'\x00' * 8)])
        self.assertEqual(SS._load(r['python']), {'etat': None}); self.assertTrue((SS._load(r['viewer'])['k'] == np.ones(2)).all())


class Refused(unittest.TestCase):
    def verify(self, trap, expected=None, proto=pickle.HIGHEST_PROTOCOL):
        f = control()
        with self.assertRaises(pickle.UnpicklingError) as cm: SS._load(pickle.dumps(trap(f), protocol=proto))
        self.assertFalse(os.path.exists(f), 'le piege a ete execute')
        if expected: self.assertIn(expected, str(cm.exception))

    def test_os_system(self):
        for proto in (0, 2, 4, 5): self.verify(lambda f: Trap(os.system, 'echo piege > ' + f), 'system', proto)

    def test_eval_exec_open_import(self):
        self.verify(lambda f: Trap(eval, "open(%r, 'w').write('x')" % f), 'builtins.eval')
        self.verify(lambda f: Trap(exec, "open(%r, 'w').write('x')" % f), 'builtins.exec')
        self.verify(lambda f: Trap(open, f, 'w'), '.open')                                  # (open est pickle sous le nom _io.open)
        self.verify(lambda f: Trap(__import__, 'os'), 'builtins.__import__')
        self.verify(lambda f: Trap(getattr, 'x', 'upper'), 'builtins.getattr')

    def test_subprocess_and_other_modules(self):
        import subprocess, shutil as sh
        self.verify(lambda f: Trap(subprocess.Popen, ['touch', f]), 'subprocess')
        self.verify(lambda f: Trap(subprocess.check_output, ['touch', f]), 'subprocess')
        self.verify(lambda f: Trap(sh.copyfile, __file__, f), 'shutil')

    def test_numpy_outside_allowlist(self):
        self.verify(lambda f: Trap(np.save, f, np.zeros(1)), 'numpy')                    # (numpy.save : un module de numpy que la liste ne contient pas)
        self.verify(lambda f: Trap(np.load, f), 'numpy')

    def test_port_classes_off_allowlist(self):
        from dq4_pc.core import engine as ENGINE
        self.verify(lambda f: Trap(ENGINE.Engine, f, f, f), 'Engine')                          # (le constructeur du moteur ne doit pas etre appelable par un fichier)
        self.verify(lambda f: Trap(ENGINE.GameCore), 'GameCore')

    def test_names_with_dot_on_allowed_module(self):
        """Protocole 4 : `STACK_GLOBAL` accepte « os.system » comme nom dans le module `dq4_pc.core.engine` (qui importe os) ; la liste blanche compare le nom entier : refuse."""
        f = control()
        for module, name_str in (('dq4_pc.core.engine', 'os.system'), ('collections', 'sys.modules'), ('builtins', 'eval.__self__')):
            raw = (b'\x80\x04\x95' + struct.pack('<Q', 0)) if False else None
            raw_value = b'\x80\x04' + b'\x8c' + bytes([len(module)]) + module.encode() + b'\x8c' + bytes([len(name_str)]) + name_str.encode() + b'\x93' + b'.'          # PROTO 4, SHORT_BINUNICODE, SHORT_BINUNICODE, STACK_GLOBAL, STOP
            with self.assertRaises(pickle.UnpicklingError): SS._load(raw_value)
        self.assertFalse(os.path.exists(f))

    def test_trap_in_complete_file(self):
        """Un etat dont la partie `python` ou `viewer` est piegee : `read` rend le dictionnaire (rien d'execute, ce sont des octets), `apply` refuse AVANT d'ecrire dans le moteur (#206)."""
        f = control(); word = control()
        d = {'version': SS.VERSION, 'lib': [], 'heap': b'', 'heap_ptr': 0, 'data': b'', 'tls': b'', 'data_ptr': 0, 'next_file': 0, 'fichiers': {}, 'python': pickle.dumps(Trap(os.system, 'echo x > ' + word)), 'viewer': b''}
        path = os.path.join(os.path.dirname(f), 'state_09.dqs'); SS.write(path, d, {})
        read_value = SS.read(path); self.assertFalse(os.path.exists(word))
        import types
        writes = []
        core = types.SimpleNamespace(uc=types.SimpleNamespace(mem_write=lambda *a: writes.append(a)), LIB_BASE=0, elf=types.SimpleNamespace(img=b'x'), heap_ptr=0, HEAP_BASE=0, DATA_BASE=0, TLS_BASE=0, data_ptr=0, next_file=0, files={})
        m = types.SimpleNamespace(core=core, log=lambda *a: None, ui=types.SimpleNamespace(obs=None))
        with self.assertRaises(pickle.UnpicklingError): SS.apply(m, read_value)
        self.assertEqual(writes, []); self.assertFalse(os.path.exists(word))

    def test_trap_in_external_container(self):
        f = control(); path = os.path.join(os.path.dirname(f), 'state_08.dqs')
        with open(path, 'wb') as fh:
            fh.write(SS.MAGIC); ent = b'{}'; fh.write(struct.pack('<I', len(ent))); fh.write(ent); fh.write(struct.pack('<I', 0))
            fh.write(zlib.compress(pickle.dumps(Trap(os.system, 'echo x > ' + f))))
        with self.assertRaises(pickle.UnpicklingError): SS.read(path)
        self.assertFalse(os.path.exists(f))

    def test_message_and_class_name(self):
        try: SS._load(pickle.dumps(Trap(os.system, 'x')))
        except pickle.UnpicklingError as ex: msg = str(ex)
        self.assertIn('refused', msg); self.assertIn('system', msg); self.assertIn('was not executed', msg)


@unittest.skipUnless(APK and SAVES, 'moteur reel : DQ_APK=<dossier des APK patches> DQ_SAVES=<dossier des sauvegardes>')
class RealSavestates(unittest.TestCase):
    """Les etats que le portage ecrit vraiment (carte du monde, ville, combat force, apres un menu) restent lisibles : la liste blanche ne doit jamais empecher de recharger un etat legitime."""
    @classmethod
    def setUpClass(cls):
        import unicorn
        from dq4_pc.core import engine as ENGINE
        cls.ENGINE, cls.unicorn = ENGINE, unicorn
        cls.wdir = tempfile.mkdtemp(prefix='sv_liste_blanche_')
        cls.eng = ENGINE.Engine(APK, SAVES, cls.wdir); cls.c = cls.eng.core

    def reread(self, tag_label):
        viewer = {'objets_etat': {'a': np.zeros((2, 3), np.float32), 'b': [np.arange(3)]}, 'carte_nom': 'x', 'motif_n': 1, 'motif_acc': np.zeros(2), 'musique': None, 'palettes': {1: (1, 2)}}
        d = SS.snapshot(self.eng, viewer); f = os.path.join(self.wdir, 'e_%s.dqs' % tag_label); SS.write(f, d, {'lieu': tag_label})
        r = SS.read(f); p = SS._load(r['python']); v = SS._load(r['viewer'])
        self.assertIsInstance(p['etat'], self.ENGINE.State); self.assertIsInstance(p['ui'], self.ENGINE.Interface); self.assertTrue((v['objets_etat']['a'] == 0).all())
        SS.apply(self.eng, r)                                                            # (et il s'applique)

    def test_town_and_world(self):
        for slot in (1, 4):
            self.eng.load_save(slot)
            for k in range(250):
                self.eng.step(0, 0)
                if k in (60, 249): self.reread('slot%d_%d' % (slot, k))

    def test_battle(self):
        ENGINE, eng, c = self.ENGINE, self.eng, self.c
        eng.load_save(1)
        for _ in range(200): eng.step(0, 0)
        enc = c.call(c.export('_ZN7Encount12getSingletonEv'), label='enc')
        def group(u, addr, sz, ud):
            for j in range(4):
                i, n = (3, 1) if j == 0 else (0, 0)
                c.mem_w(enc + 0x34 + 4 * j, struct.pack('<I', i)); c.mem_w(enc + 0x44 + 4 * j, struct.pack('<I', n))
        a = c.export('_ZN10BattleRoot12setupMonsterEv'); c.uc.hook_add(self.unicorn.UC_HOOK_CODE, group, None, a, a); c.uc.ctl_flush_tb()
        for _ in range(3): eng.step(0, 0)
        c.call(c.export('_ZN6Global11startBattleEv'), eng._global(), label='startBattle')
        n = 0
        while eng.state.part != ENGINE.PART_BATTLE and n < 1500: eng.step(0, 0); n += 1
        self.assertEqual(eng.state.part, ENGINE.PART_BATTLE)
        for i in range(120):
            eng.step(0, 0); eng.ui.damage = []
            if i % 40 == 0: self.reread('combat_%d' % i)


if __name__ == '__main__':
    unittest.main(verbosity=1)
