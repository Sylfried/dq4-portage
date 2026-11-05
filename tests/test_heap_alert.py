"""Alerte du tas du moteur (ENG-01, audit du 04/11/2026) : le tas n'est jamais libere et fait 256 Mo ; la fenetre le note dans le journal des erreurs a 200 Mo puis a 240 Mo (plus de message a l'ecran depuis #267).

  1. `Core.heap_used` : octets alloues (heap_ptr - HEAP_BASE) ; seuils 200 et 240 Mo sous la taille du tas ;
  2. `Game._watch_heap` : rien sous 200 Mo ; une ligne du journal a 200 Mo, une autre a 240 Mo, chacune UNE fois, et aucun message a l'ecran (le faux jeu n'a pas de `toast`) ; le tas qui redescend (chargement d'un etat) rearme les alertes ;
     un saut direct au-dela de 240 Mo donne une seule ligne ; aucun etat instantane n'est ecrit (il garderait le tas plein).

    python3 tests/test_heap_alert.py
"""
import os, sys, types, unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from dq4_pc import language as _LANGUAGE; _LANGUAGE.select_language('fr')          # (D-238 : ces tests attendent les textes francais, quelle que soit la langue de l'ordinateur)
from dq4_pc.core import emu_core as EC

try:
    import pyglet
    pyglet.options['shadow_window'] = False
    from dq4_pc.window import game as WND
except Exception as ex:          # fenetre/jeu.py a besoin de pyglet, numpy, unicorn... (l'import seul suffit)
    WND = None; ERROR_WND = ex

ENGINE = 1 << 20


def fake_core_heap(mb_used):
    return types.SimpleNamespace(HEAP_BASE=EC.Core.HEAP_BASE, HEAP_SIZE=EC.Core.HEAP_SIZE, heap_ptr=EC.Core.HEAP_BASE + int(mb_used * ENGINE), HEAP_ALERT=EC.Core.HEAP_ALERT, HEAP_CRITICAL=EC.Core.HEAP_CRITICAL,
                                 heap_used=lambda: None)


def core(mb_used):
    c = fake_core_heap(mb_used); c.heap_used = types.MethodType(EC.Core.heap_used, c); return c


class Thresholds(unittest.TestCase):
    def test_heap_used(self):
        self.assertEqual(core(0).heap_used(), 0); self.assertEqual(core(13).heap_used(), 13 * ENGINE)

    def test_thresholds(self):
        self.assertEqual(EC.Core.HEAP_ALERT, 200 * ENGINE); self.assertEqual(EC.Core.HEAP_CRITICAL, 240 * ENGINE)
        self.assertLess(EC.Core.HEAP_ALERT, EC.Core.HEAP_CRITICAL); self.assertLess(EC.Core.HEAP_CRITICAL, EC.Core.HEAP_SIZE); self.assertEqual(EC.Core.HEAP_SIZE, 256 * ENGINE)


@unittest.skipIf(WND is None, 'fenetre/jeu.py non importable ici')
class Alert(unittest.TestCase):
    def setUp(self):
        self.logfile = []
        self.j = types.SimpleNamespace(_heap_level=0)
        self.j._watch_heap = types.MethodType(WND.Game._watch_heap, self.j)
        self.old = WND.note_error; WND.note_error = lambda t: self.logfile.append(t)

    def tearDown(self): WND.note_error = self.old

    def test_nothing_below_200_mb(self):
        for u in (0, 14, 150, 199.9): self.j._watch_heap(core(u))
        self.assertEqual(self.logfile, [])

    def test_one_message_per_tier(self):
        for u in (100, 200, 205, 230, 239.9): self.j._watch_heap(core(u))
        self.assertEqual(len(self.logfile), 1); self.assertIn('200 Mo sur 256 Mo', self.logfile[0]); self.assertIn('a 78 %', self.logfile[0])
        for u in (240, 245, 255): self.j._watch_heap(core(u))
        self.assertEqual(len(self.logfile), 2); self.assertIn('a 94 %', self.logfile[1])

    def test_direct_jump_beyond_240(self):
        self.j._watch_heap(core(250)); self.assertEqual(len(self.logfile), 1); self.assertIn('a 98 %', self.logfile[0])
        self.j._watch_heap(core(252)); self.assertEqual(len(self.logfile), 1)

    def test_heap_dropping_back_rearms(self):
        self.j._watch_heap(core(210)); self.j._watch_heap(core(12)); self.j._watch_heap(core(12)); self.assertEqual(len(self.logfile), 1)             # (etat charge : tas de 12 Mo)
        self.j._watch_heap(core(210)); self.assertEqual(len(self.logfile), 2)
        self.j._watch_heap(core(245)); self.j._watch_heap(core(215)); self.assertEqual(len(self.logfile), 3)                                       # 94 % puis retour a 84 % : pas de nouvelle alerte (le palier bas est deja passe)
        self.j._watch_heap(core(215)); self.assertEqual(len(self.logfile), 3)


if __name__ == '__main__':
    unittest.main()
