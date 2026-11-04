"""Test des reglages ajoutes (son par categorie, vitesse du texte, defilement des combats, vitesses x1 a x4) : un ancien reglages.json reste valide (migration des anciens curseurs et de l'ancien defilement des combats), les valeurs absurdes sont ramenees.

    python3 outils/test_reglages_son_texte.py
"""
import json, os, sys, tempfile, unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from dq4_pc.persistance import reglages as RG


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
        self.assertEqual((r['vitesse_texte'], r['vitesse_combat']), (4.0, 1.0))      # = le comportement d'avant : Normal (vitesse et messages d'origine)
        self.assertNotIn('defilement_force', r.v); self.assertNotIn('defilement_combat', r.v)
        self.assertEqual((r['vitesse_marche'], r['vitesse_camera']), (1.0, 1.0))

    def test_valeurs_absurdes(self):
        r, _ = charger({'volume_general': 5, 'volume_jingles': -2, 'volume_interface': 'fort', 'musique_active': 'oui', 'interface_active': None, 'vitesse_combat': 'vite',
                        'vitesse_texte': 3.1, 'vitesse_marche': 'vite', 'vitesse_camera': True})
        self.assertEqual((r['volume_general'], r['volume_jingles'], r['volume_interface']), (1.0, 0.0, 1.0))
        self.assertIs(r['musique_active'], True); self.assertIs(r['interface_active'], True); self.assertEqual(r['vitesse_combat'], 1.0)
        self.assertEqual(r['vitesse_texte'], 4.0)
        self.assertEqual((r['vitesse_marche'], r['vitesse_camera']), (1.0, 1.0))      # valeurs absurdes : celles par defaut

    def test_vitesse_du_texte_ramenee_a_un_cran(self):
        for brut, cran in ((0.1, 0.5), (0.8, 1.0), (1.5, 2.0), (5.0, 4.0), (7.0, 8.0), (100.0, 16.0), (100000, 4000.0)):
            r, _ = charger({'vitesse_texte': brut}); self.assertEqual(r['vitesse_texte'], cran, brut)

    def test_aller_retour(self):
        r, f = charger({})
        r['volume_interface'] = 0.35; r['jingles_actifs'] = False; r['vitesse_texte'] = 16.0; r['vitesse_combat'] = 0.0
        r['vitesse_marche'] = 4.0; r['vitesse_camera'] = 3.0
        r.enregistrer()
        r2 = RG.Reglages(f)
        self.assertEqual((r2['volume_interface'], r2['jingles_actifs'], r2['vitesse_texte'], r2['vitesse_combat']), (0.35, False, 16.0, 0.0))
        self.assertEqual((r2['vitesse_marche'], r2['vitesse_camera']), (4.0, 3.0))

    def test_migration_defilement_des_combats(self):
        """Anciens reglages « Defilement automatique » (oui / non) + « Vitesse de defilement » (0 a 3), puis « Messages en combat » (0 Rapide, 2 Moyen, 3 Lent, 4 Manuel) -> « Vitesse de combat » : seul « a la main » (impose) a un equivalent : Manuel."""
        for ancien, attendu in (({'defilement_auto': True, 'defilement_vitesse': 0}, 1.0), ({'defilement_auto': True, 'defilement_vitesse': 3}, 1.0), ({'defilement_auto': False, 'defilement_vitesse': 0}, 0.0),
                                ({'defilement_auto': False}, 0.0), ({'defilement_auto': True}, 1.0), ({'defilement_combat': 4}, 0.0), ({'defilement_combat': 0}, 1.0), ({'defilement_combat': 3}, 1.0),
                                ({'defilement_combat': 4, 'vitesse_combat': 3.0}, 0.0), ({'defilement_combat': 2, 'vitesse_combat': 3.0}, 3.0)):
            r, _ = charger(dict(ancien, defilement_force=True))
            self.assertEqual(r['vitesse_combat'], attendu, ancien)
            for k in ('defilement_auto', 'defilement_vitesse', 'defilement_force', 'defilement_combat'): self.assertNotIn(k, r.v)
        r, _ = charger({'defilement_auto': False, 'defilement_vitesse': 1}); self.assertEqual(r['vitesse_combat'], 1.0)      # rien n'etait impose : rien ne l'est apres la migration
        r, _ = charger({'defilement_force': False, 'defilement_combat': 4}); self.assertEqual(r['vitesse_combat'], 1.0)

    def test_cran_comme_le_jeu_est_le_standard_du_moteur(self):
        """Le cran « Normal » (4 lettres par image) est la vitesse standard du jeu : c'est la valeur que la regle de priorite du jeu (priorite_jeu.lettres_par_image) remplace par le reglage du joueur, et celle qui ne change rien."""
        from dq4_pc.noyau import priorite_jeu as PJ
        self.assertEqual(RG.DEFAUT['vitesse_texte'], PJ.LETTRES_STANDARD)
        self.assertIn(float(PJ.LETTRES_STANDARD), RG.VITESSES_TEXTE)
        for v in RG.VITESSES_TEXTE: self.assertEqual(PJ.lettres_par_image(v, 400), 400, 'fenetres de combat : jamais touchees')

    def test_plus_de_reglage_de_vitesse_de_transition(self):
        """#101 : les transitions restent a la duree du jeu (x1), ce n'est plus un reglage. Un ancien fichier qui avait x2, x3 ou x4 se charge sans erreur, la cle est ignoree et n'est plus reecrite."""
        for cle in ('vitesse_fondu', 'vitesse_fondu_v'): self.assertNotIn(cle, RG.DEFAUT); self.assertNotIn(cle, RG.Reglages(None).v); self.assertNotIn(cle, RG.BORNES)
        self.assertNotIn('vitesse_fondu', RG.VITESSES_X_CLES)
        for ancien in (1.0, 2.0, 3.0, 4.0):
            r, f = charger({'vitesse_fondu': ancien, 'vitesse_fondu_v': 2, 'vitesse_marche': 3.0}); self.assertNotIn('vitesse_fondu', r.v); self.assertEqual(r['vitesse_marche'], 3.0)
            r.enregistrer()
            with open(f, encoding='utf-8') as fh: self.assertNotIn('vitesse_fondu', json.load(fh))
        from dq4_pc.noyau import moteur as MO
        self.assertEqual(MO.Etat.vitesse_fondu, 1.0)                                                            # (le moteur garde la duree d'origine)

    def test_migration_des_vitesses_en_x(self):
        """Anciens curseurs (0,5 a 2) -> le cran x1 a x4 le plus proche (a egalite le plus rapide), jamais moins que x1."""
        for ancien, attendu in ((0.5, 1.0), (0.9, 1.0), (1.0, 1.0), (1.25, 1.0), (1.4, 1.0), (1.5, 2.0), (1.75, 2.0), (2.0, 2.0), (2.6, 3.0), (3, 3.0), (4, 4.0), (9, 4.0), (-3, 1.0)):
            r, _ = charger({'vitesse_marche': ancien, 'vitesse_camera': ancien})
            self.assertEqual((r['vitesse_marche'], r['vitesse_camera']), (attendu,) * 2, ancien)
            self.assertTrue(all(r[k] in RG.VITESSES_X for k in RG.VITESSES_X_CLES))
        self.assertEqual(RG.DEFAUT['vitesse_accel'], 1.5)                                                      # l'accelerateur garde son curseur (1 a 2)
        r, _ = charger({'vitesse_accel': 1.37}); self.assertEqual(r['vitesse_accel'], 1.37)


if __name__ == '__main__':
    unittest.main(verbosity=2)
