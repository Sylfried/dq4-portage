"""Test des reglages ajoutes (son par categorie, vitesse du texte, defilement des combats, vitesses x1 a x4) : un ancien reglages.json reste valide (migration des anciens curseurs et de l'ancien defilement des combats), les valeurs absurdes sont ramenees.

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
        self.assertEqual((r['vitesse_texte'], r['defilement_force'], r['defilement_combat']), (4.0, False, 2))      # = le comportement d'avant : rien n'est impose, valeur d'origine du jeu (Moyen)
        self.assertEqual((r['vitesse_marche'], r['vitesse_camera'], r['vitesse_fondu']), (1.0, 1.0, 2.0))

    def test_valeurs_absurdes(self):
        r, _ = charger({'volume_general': 5, 'volume_jingles': -2, 'volume_interface': 'fort', 'musique_active': 'oui', 'interface_active': None, 'defilement_force': 1,
                        'vitesse_texte': 3.1, 'defilement_combat': 9, 'vitesse_marche': 'vite', 'vitesse_camera': True, 'vitesse_fondu': None})
        self.assertEqual((r['volume_general'], r['volume_jingles'], r['volume_interface']), (1.0, 0.0, 1.0))
        self.assertIs(r['musique_active'], True); self.assertIs(r['interface_active'], True); self.assertIs(r['defilement_force'], False)
        self.assertEqual(r['vitesse_texte'], 4.0); self.assertEqual(r['defilement_combat'], 2)
        self.assertEqual((r['vitesse_marche'], r['vitesse_camera'], r['vitesse_fondu']), (1.0, 1.0, 2.0))      # valeurs absurdes : celles par defaut

    def test_vitesse_du_texte_ramenee_a_un_cran(self):
        for brut, cran in ((0.1, 0.5), (0.8, 1.0), (1.5, 2.0), (5.0, 4.0), (7.0, 8.0), (100.0, 16.0), (100000, 4000.0)):
            r, _ = charger({'vitesse_texte': brut}); self.assertEqual(r['vitesse_texte'], cran, brut)

    def test_aller_retour(self):
        r, f = charger({})
        r['volume_interface'] = 0.35; r['jingles_actifs'] = False; r['vitesse_texte'] = 16.0; r['defilement_force'] = True; r['defilement_combat'] = 3
        r['vitesse_marche'] = 4.0; r['vitesse_camera'] = 3.0; r['vitesse_fondu'] = 1.0
        r.enregistrer()
        r2 = RG.Reglages(f)
        self.assertEqual((r2['volume_interface'], r2['jingles_actifs'], r2['vitesse_texte'], r2['defilement_force'], r2['defilement_combat']), (0.35, False, 16.0, True, 3))
        self.assertEqual((r2['vitesse_marche'], r2['vitesse_camera'], r2['vitesse_fondu']), (4.0, 3.0, 1.0))

    def test_migration_defilement_des_combats(self):
        """Anciens reglages « Defilement automatique » (oui / non) + « Vitesse de defilement » (0 a 3) -> « Messages en combat » : 0 Rapide, 2 Moyen (valeur d'origine du jeu), 3 Lent, 4 Manuel ; le cran 1 (22 images) devient Moyen."""
        for ancien, attendu in (({'defilement_auto': True, 'defilement_vitesse': 0}, 0), ({'defilement_auto': True, 'defilement_vitesse': 1}, 2), ({'defilement_auto': True, 'defilement_vitesse': 2}, 2),
                                ({'defilement_auto': True, 'defilement_vitesse': 3}, 3), ({'defilement_auto': False, 'defilement_vitesse': 0}, 4), ({'defilement_auto': False}, 4),
                                ({'defilement_auto': True}, 2), ({'defilement_vitesse': 3}, 3), ({'defilement_auto': True, 'defilement_vitesse': 9}, 3), ({'defilement_auto': True, 'defilement_vitesse': 'x'}, 2)):
            r, _ = charger(dict(ancien, defilement_force=True))
            self.assertEqual(r['defilement_combat'], attendu, ancien); self.assertIs(r['defilement_force'], True)
            self.assertNotIn('defilement_auto', r.v); self.assertNotIn('defilement_vitesse', r.v)
        r, _ = charger({'defilement_auto': False, 'defilement_vitesse': 0, 'defilement_combat': 3})          # le nouveau reglage l'emporte sur les anciens
        self.assertEqual(r['defilement_combat'], 3)
        r, _ = charger({'defilement_auto': False, 'defilement_vitesse': 1})                                   # rien n'etait impose : rien ne l'est apres la migration
        self.assertIs(r['defilement_force'], False)

    def test_cran_comme_le_jeu_est_le_standard_du_moteur(self):
        """Le cran « Normal » (4 lettres par image) est la vitesse standard du jeu : c'est la valeur que la regle de priorite du jeu (priorite_jeu.lettres_par_image) remplace par le reglage du joueur, et celle qui ne change rien."""
        import priorite_jeu as PJ
        self.assertEqual(RG.DEFAUT['vitesse_texte'], PJ.LETTRES_STANDARD)
        self.assertIn(float(PJ.LETTRES_STANDARD), RG.VITESSES_TEXTE)
        for v in RG.VITESSES_TEXTE: self.assertEqual(PJ.lettres_par_image(v, 400), 400, 'fenetres de combat : jamais touchees')

    def test_crans_du_defilement(self):
        self.assertEqual(RG.CRANS_DEFILEMENT, (0, 2, 3, 4))
        for code, cran in ((0, 0), (1, 2), (2, 2), (3, 3), (4, 4), (5, 2), (-1, 2), (None, 2), ('a', 2)): self.assertEqual(RG.cran_defilement(code), cran, code)

    def test_migration_des_vitesses_en_x(self):
        """Anciens curseurs (0,5 a 2) -> le cran x1 a x4 le plus proche (a egalite le plus rapide), jamais moins que x1."""
        for ancien, attendu in ((0.5, 1.0), (0.9, 1.0), (1.0, 1.0), (1.25, 1.0), (1.4, 1.0), (1.5, 2.0), (1.75, 2.0), (2.0, 2.0), (2.6, 3.0), (3, 3.0), (4, 4.0), (9, 4.0), (-3, 1.0)):
            r, _ = charger({'vitesse_marche': ancien, 'vitesse_camera': ancien, 'vitesse_fondu': ancien})
            self.assertEqual((r['vitesse_marche'], r['vitesse_camera'], r['vitesse_fondu']), (attendu,) * 3, ancien)
            self.assertTrue(all(r[k] in RG.VITESSES_X for k in RG.VITESSES_X_CLES))
        self.assertEqual(RG.DEFAUT['vitesse_accel'], 1.5)                                                      # l'accelerateur garde son curseur (1 a 2)
        r, _ = charger({'vitesse_accel': 1.37}); self.assertEqual(r['vitesse_accel'], 1.37)


if __name__ == '__main__':
    unittest.main(verbosity=2)
