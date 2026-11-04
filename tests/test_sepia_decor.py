"""Effet « sepia » des retours en arriere (paquet 1, `cmd_map_effect_sepia` ; audit UNI-04 / MAP-04) :

  1. `Etat` : le paquet 1 (sans argument) passe le decor en sepia ; il reste ainsi (le jeu ne le retire pas) jusqu'au chargement de carte suivant (paquet 0), qui le remet a faux ; les autres paquets n'y touchent pas ;
  2. un etat enregistre avant ce correctif (sans l'attribut) se comporte comme neuf (pas de sepia) ;
  3. le shader du decor reprend la formule de `Custom/fld_normal_sepia` du jeu (lue dans le paquet de donnees, GLSL ES) : gris (0,299 ; 0,587 ; 0,114) de texture x couleur de sommet x teinte, plus
     (0,109375 ; -0,0546875 ; 0), alpha inchange ; applique AVANT l'ecriture bornee a 0-1 ; sans effet tant que le uniforme `sepia` est a 0 (valeur par defaut d'un uniforme).

    python3 tests/test_sepia_decor.py
"""
import os, re, sys, unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from dq4_pc.noyau import moteur as MO
from dq4_pc.fenetre import shaders as SH


def envoyer(e, *paquets):
    e.appliquer(list(paquets), lambda: 'ceout')


class Paquet1(unittest.TestCase):
    def test_defaut_et_paquet(self):
        e = MO.Etat(); self.assertFalse(e.sepia)
        envoyer(e, (1, [], [])); self.assertTrue(e.sepia)
        envoyer(e, (1, [], [])); self.assertTrue(e.sepia)                     # pas une bascule : un second paquet ne l'annule pas

    def test_autres_paquets_sans_effet(self):
        e = MO.Etat(); envoyer(e, (1, [], []))
        envoyer(e, (33, [], [1.25, 0.65, 0.75]), (8, [], [0.0] * 6), (2, [0], [0.5]), (30, [-1], [1.25]))
        self.assertTrue(e.sepia)

    def test_chargement_de_carte(self):
        e = MO.Etat(); envoyer(e, (1, [], []))
        envoyer(e, (0, [], [])); self.assertFalse(e.sepia)                    # FldObject neuf : materiaux d'origine
        envoyer(e, (1, [], [])); self.assertTrue(e.sepia)                     # un nouveau retour en arriere, apres le chargement

    def test_ancien_etat(self):
        e = MO.Etat.__new__(MO.Etat); self.assertFalse(e.sepia)


class Shader(unittest.TestCase):
    def test_formule(self):
        src = SH.FRAG
        self.assertIn('uniform float sepia', src)
        m = re.search(r'if \(sepia > 0\.5\) m = vec3\(dot\(vec3\(([\d.]+), ([\d.]+), ([\d.]+)\), m\)\) \+ vec3\(([\d.]+), (-[\d.]+), ([\d.]+)\);', src)
        self.assertIsNotNone(m, 'ligne sepia du shader')
        poids = [float(x) for x in m.groups()[:3]]; decalage = [float(x) for x in m.groups()[3:]]
        self.assertEqual(poids, [0.299, 0.587, 0.114]); self.assertAlmostEqual(sum(poids), 1.0)
        self.assertEqual(decalage, [0.109375, -0.0546875, 0.0])

    def test_avant_la_borne_et_alpha_intact(self):
        src = SH.FRAG
        self.assertLess(src.index('if (sepia > 0.5)'), src.index('c.rgb = clamp(m, 0.0, 1.0)'))          # le gris est calcule sur la couleur non bornee, comme le shader du jeu
        self.assertLess(src.index('vec3 m = c.rgb * teinte'), src.index('if (sepia > 0.5)'))             # apres texture x sommet x teinte
        ligne = [l for l in src.split('\n') if 'sepia > 0.5' in l][0]; self.assertNotIn('c.a', ligne)    # l'alpha n'est pas touche


if __name__ == '__main__':
    unittest.main(verbosity=2)
