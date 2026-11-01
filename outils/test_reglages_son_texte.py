"""Test des reglages ajoutes (son par categorie, vitesse du texte, defilement des combats) : un ancien reglages.json reste valide, les valeurs absurdes sont ramenees.

    python3 outils/test_reglages_son_texte.py
"""
import json, os, sys, tempfile, unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'dq4_pc'))
import reglages as RG


def charger(contenu):
    f = os.path.join(tempfile.mkdtemp(prefix='rg_test_'), 'reglages.json')
    with open(f, 'w', encoding='utf-8') as fh: json.dump(contenu, fh)
    return RG.Reglages(f), f


class Reglages(unittest.TestCase):
    def test_ancien_fichier(self):
        r, _ = charger({'son': False, 'volume_musique': 0.4, 'volume_bruitages': 0.7, 'touches_v': 4, 'mode_sprites': 2})
        self.assertEqual((r['son'], r['volume_musique'], r['volume_bruitages']), (False, 0.4, 0.7))      # les anciens reglages sont conserves
        self.assertEqual((r['volume_general'], r['volume_jingles'], r['volume_interface']), (1.0, 1.0, 1.0))
        self.assertTrue(all(r[k] for k in ('musique_active', 'jingles_actifs', 'bruitages_actifs', 'interface_active')))
        self.assertEqual((r['vitesse_texte'], r['defilement_force'], r['defilement_auto'], r['defilement_vitesse']), (4.0, False, True, 2))      # = le comportement d'avant

    def test_valeurs_absurdes(self):
        r, _ = charger({'volume_general': 5, 'volume_jingles': -2, 'volume_interface': 'fort', 'musique_active': 'oui', 'interface_active': None, 'defilement_auto': 1,
                        'vitesse_texte': 3.1, 'defilement_vitesse': 9})
        self.assertEqual((r['volume_general'], r['volume_jingles'], r['volume_interface']), (1.0, 0.0, 1.0))
        self.assertIs(r['musique_active'], True); self.assertIs(r['interface_active'], True); self.assertIs(r['defilement_auto'], True)
        self.assertEqual(r['vitesse_texte'], 4.0); self.assertEqual(r['defilement_vitesse'], 3)

    def test_vitesse_du_texte_ramenee_a_un_cran(self):
        for brut, cran in ((0.1, 0.5), (0.8, 1.0), (1.5, 2.0), (5.0, 4.0), (7.0, 8.0), (100.0, 16.0), (100000, 4000.0)):
            r, _ = charger({'vitesse_texte': brut}); self.assertEqual(r['vitesse_texte'], cran, brut)

    def test_aller_retour(self):
        r, f = charger({})
        r['volume_interface'] = 0.35; r['jingles_actifs'] = False; r['vitesse_texte'] = 16.0; r['defilement_force'] = True; r['defilement_auto'] = False; r['defilement_vitesse'] = 1
        r.enregistrer()
        r2 = RG.Reglages(f)
        self.assertEqual((r2['volume_interface'], r2['jingles_actifs'], r2['vitesse_texte'], r2['defilement_force'], r2['defilement_auto'], r2['defilement_vitesse']), (0.35, False, 16.0, True, False, 1))


if __name__ == '__main__':
    unittest.main(verbosity=2)
