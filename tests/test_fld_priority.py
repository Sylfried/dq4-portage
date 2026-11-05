"""#203 (audit MAP-01) : priorite des objets de carte (FMAP) : entier de 32 bits en +52 (file de rendu 3000 + priorite), drapeaux = entier de 32 bits en +48.
Lancer depuis la racine : python3 tests/test_fld_priority.py"""
import os, struct, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dq4_pc.world import fld


def fmap(objects):
    """Un chunk FMAP minimal : en-tete de 0x20 octets (tag, taille, nombre d'objets) puis 0x50 octets par objet ; `objects` = [(drapeaux int32, priorite int32)]."""
    body = bytearray()
    for flag32, prio in objects:
        o = bytearray(0x50); struct.pack_into('<ii', o, 48, flag32, prio); struct.pack_into('<hh', o, 64, 3, 4); struct.pack_into('<h', o, 74, 5); body += o
    t = 0x20 + len(body); ent = bytearray(0x20); ent[:4] = b'FMAP'; struct.pack_into('<I', ent, 4, t); struct.pack_into('<I', ent, 8, len(objects))
    return bytes(ent + body)


class ItemPriority(unittest.TestCase):
    def test_priority_at_plus_52_not_high_half_of_flags(self):
        n, objs = fld.map_objs(fmap([(0x40000, 23), (0, 10), (0x40004, 12)]))
        self.assertEqual(n, 3); self.assertEqual([o['prio'] for o in objs], [23, 10, 12])         # avant : 4, 0, 4 (la moitie haute des drapeaux)

    def test_flags_unchanged(self):
        n, objs = fld.map_objs(fmap([(0x40024, 18), (0x20, 11), (0x0, 10)]))
        self.assertEqual([o['flag'] for o in objs], [0x24, 0x20, 0])                              # billboards (& 36) : seuls les 16 bits bas, comme avant

    def test_other_fields_unchanged(self):
        _, objs = fld.map_objs(fmap([(0, 10)]))
        self.assertEqual((objs[0]['seqobj'], objs[0]['pmv'], objs[0]['canim']), (3, 4, 5))


class CacheVersion(unittest.TestCase):
    def test_version_11_maps_and_old_ones_purged(self):
        from dq4_pc.world import data as DO
        import inspect
        src = inspect.getsource(DO)
        self.assertIn("'carte11_%s.pkl'", src); self.assertNotIn("carte10_%s", src)               # le cache d'avant (priorite fausse) n'est jamais relu
        import tempfile, shutil
        d = tempfile.mkdtemp()
        try:
            for f in ('carte9_a.pkl', 'carte10_a.pkl', 'carte11_a.pkl'): open(os.path.join(d, f), 'wb').close()
            o = DO.Data.__new__(DO.Data); o.cache = d; o.log = lambda *a: None; o._purge_old()
            self.assertEqual(os.listdir(d), ['carte11_a.pkl'])
        finally: shutil.rmtree(d, ignore_errors=True)


if __name__ == '__main__': unittest.main(verbosity=1)
