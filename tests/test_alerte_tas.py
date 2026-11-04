"""Alerte du tas du moteur (ENG-01, audit du 04/11/2026) : le tas n'est jamais libere et fait 256 Mo ; la fenetre previent le joueur a 200 Mo puis a 240 Mo.

  1. `Core.tas_utilise` : octets alloues (heap_ptr - HEAP_BASE) ; seuils 200 et 240 Mo sous la taille du tas ;
  2. `Jeu._surveiller_tas` : rien sous 200 Mo ; un message (et une ligne du journal) a 200 Mo, un autre a 240 Mo, chacun UNE fois ; le tas qui redescend (chargement d'un etat) rearme les alertes ;
     un saut direct au-dela de 240 Mo donne le message pressant ; aucun etat instantane n'est ecrit (il garderait le tas plein).

    python3 tests/test_alerte_tas.py
"""
import os, sys, types, unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from dq4_pc.noyau import emu_core as EC

try:
    import pyglet
    pyglet.options['shadow_window'] = False
    from dq4_pc.fenetre import jeu as FE
except Exception as ex:          # fenetre/jeu.py a besoin de pyglet, numpy, unicorn... (l'import seul suffit)
    FE = None; ERREUR_FE = ex

MO = 1 << 20


def faux_core(mo_utilises):
    return types.SimpleNamespace(HEAP_BASE=EC.Core.HEAP_BASE, HEAP_SIZE=EC.Core.HEAP_SIZE, heap_ptr=EC.Core.HEAP_BASE + int(mo_utilises * MO), TAS_ALERTE=EC.Core.TAS_ALERTE, TAS_CRITIQUE=EC.Core.TAS_CRITIQUE,
                                 tas_utilise=lambda: None)


def core(mo_utilises):
    c = faux_core(mo_utilises); c.tas_utilise = types.MethodType(EC.Core.tas_utilise, c); return c


class Seuils(unittest.TestCase):
    def test_tas_utilise(self):
        self.assertEqual(core(0).tas_utilise(), 0); self.assertEqual(core(13).tas_utilise(), 13 * MO)

    def test_seuils(self):
        self.assertEqual(EC.Core.TAS_ALERTE, 200 * MO); self.assertEqual(EC.Core.TAS_CRITIQUE, 240 * MO)
        self.assertLess(EC.Core.TAS_ALERTE, EC.Core.TAS_CRITIQUE); self.assertLess(EC.Core.TAS_CRITIQUE, EC.Core.HEAP_SIZE); self.assertEqual(EC.Core.HEAP_SIZE, 256 * MO)


@unittest.skipIf(FE is None, 'fenetre/jeu.py non importable ici')
class Alerte(unittest.TestCase):
    def setUp(self):
        self.toasts = []; self.journal = []
        self.j = types.SimpleNamespace(_tas_niveau=0, toast=lambda t, duree=1.8: self.toasts.append((t, duree)))
        self.j._surveiller_tas = types.MethodType(FE.Jeu._surveiller_tas, self.j)
        self.ancien = FE.noter_erreur; FE.noter_erreur = lambda t: self.journal.append(t)

    def tearDown(self): FE.noter_erreur = self.ancien

    def test_rien_sous_200_mo(self):
        for u in (0, 14, 150, 199.9): self.j._surveiller_tas(core(u))
        self.assertEqual(self.toasts, []); self.assertEqual(self.journal, [])

    def test_un_message_par_palier(self):
        for u in (100, 200, 205, 230, 239.9): self.j._surveiller_tas(core(u))
        self.assertEqual(len(self.toasts), 1); self.assertIn('78 %', self.toasts[0][0]); self.assertIn('relancer', self.toasts[0][0]); self.assertGreaterEqual(self.toasts[0][1], 8.0)
        self.assertEqual(len(self.journal), 1); self.assertIn('200 Mo sur 256 Mo', self.journal[0])
        for u in (240, 245, 255): self.j._surveiller_tas(core(u))
        self.assertEqual(len(self.toasts), 2); self.assertIn('94 %', self.toasts[1][0]); self.assertIn('maintenant', self.toasts[1][0]); self.assertEqual(len(self.journal), 2)

    def test_saut_direct_au_dela_de_240(self):
        self.j._surveiller_tas(core(250)); self.assertEqual(len(self.toasts), 1); self.assertIn('presque pleine', self.toasts[0][0])
        self.j._surveiller_tas(core(252)); self.assertEqual(len(self.toasts), 1)

    def test_le_tas_qui_redescend_rearme(self):
        self.j._surveiller_tas(core(210)); self.j._surveiller_tas(core(12)); self.j._surveiller_tas(core(12)); self.assertEqual(len(self.toasts), 1)             # (etat charge : tas de 12 Mo)
        self.j._surveiller_tas(core(210)); self.assertEqual(len(self.toasts), 2)
        self.j._surveiller_tas(core(245)); self.j._surveiller_tas(core(215)); self.assertEqual(len(self.toasts), 3)                                       # 94 % puis retour a 84 % : pas de nouvelle alerte (le palier bas est deja passe)
        self.j._surveiller_tas(core(215)); self.assertEqual(len(self.toasts), 3)


if __name__ == '__main__':
    unittest.main()
