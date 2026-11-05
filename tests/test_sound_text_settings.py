"""Test des reglages ajoutes (son par categorie, vitesse du texte, defilement des combats, vitesses x1 a x4) : un ancien reglages.json reste valide (migration des anciens curseurs et de l'ancien defilement des combats), les valeurs absurdes sont ramenees.

    python3 tools/test_sound_text_settings.py
"""
import json, os, sys, tempfile, unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from dq4_pc.persistence import settings as RG


def load(content):
    f = os.path.join(tempfile.mkdtemp(prefix='rg_test_'), 'reglages.json')
    with open(f, 'w', encoding='utf-8') as fh: json.dump(content, fh)
    return RG.Settings(f), f


class Settings(unittest.TestCase):
    def test_old_file(self):
        r, _ = load({'son': False, 'volume_musique': 0.4, 'volume_bruitages': 0.7, 'touches_v': 4, 'mode_sprites': 2})
        self.assertEqual((r['son'], r['volume_musique'], r['volume_bruitages']), (False, 0.4, 0.7))      # les anciens reglages sont conserves
        self.assertEqual((r['volume_general'], r['volume_jingles'], r['volume_interface']), (1.0, 1.0, 1.0))
        self.assertTrue(all(r[k] for k in ('musique_active', 'jingles_actifs', 'bruitages_actifs', 'interface_active')))
        self.assertEqual((r['vitesse_texte'], r['vitesse_combat']), (4.0, 1.0))      # = le comportement d'avant : Normal (vitesse et messages d'origine)
        self.assertNotIn('defilement_force', r.v); self.assertNotIn('defilement_combat', r.v)
        self.assertEqual((r['vitesse_marche'], r['vitesse_camera']), (1.0, 1.0))

    def test_absurd_values(self):
        r, _ = load({'volume_general': 5, 'volume_jingles': -2, 'volume_interface': 'fort', 'musique_active': 'oui', 'interface_active': None, 'vitesse_combat': 'vite',
                        'vitesse_texte': 3.1, 'vitesse_marche': 'vite', 'vitesse_camera': True})
        self.assertEqual((r['volume_general'], r['volume_jingles'], r['volume_interface']), (1.0, 0.0, 1.0))
        self.assertIs(r['musique_active'], True); self.assertIs(r['interface_active'], True); self.assertEqual(r['vitesse_combat'], 1.0)
        self.assertEqual(r['vitesse_texte'], 4.0)
        self.assertEqual((r['vitesse_marche'], r['vitesse_camera']), (1.0, 1.0))      # valeurs absurdes : celles par defaut

    def test_text_speed_clamped_to_one_notch(self):
        for raw_value, notch in ((0.1, 0.5), (0.8, 1.0), (1.5, 2.0), (5.0, 4.0), (7.0, 8.0), (100.0, 16.0), (100000, 4000.0)):
            r, _ = load({'vitesse_texte': raw_value}); self.assertEqual(r['vitesse_texte'], notch, raw_value)

    def test_round_trip(self):
        r, f = load({})
        r['volume_interface'] = 0.35; r['jingles_actifs'] = False; r['vitesse_texte'] = 16.0; r['vitesse_combat'] = 0.0
        r['vitesse_marche'] = 4.0; r['vitesse_camera'] = 3.0
        r.store()
        r2 = RG.Settings(f)
        self.assertEqual((r2['volume_interface'], r2['jingles_actifs'], r2['vitesse_texte'], r2['vitesse_combat']), (0.35, False, 16.0, 0.0))
        self.assertEqual((r2['vitesse_marche'], r2['vitesse_camera']), (4.0, 3.0))

    def test_battle_scroll_migration(self):
        """Anciens reglages « Defilement automatique » (oui / non) + « Vitesse de defilement » (0 a 3), puis « Messages en combat » (0 Rapide, 2 Moyen, 3 Lent, 4 Manuel) -> « Vitesse de combat » : seul « a la main » (impose) a un equivalent : Manuel."""
        for old, expected in (({'defilement_auto': True, 'defilement_vitesse': 0}, 1.0), ({'defilement_auto': True, 'defilement_vitesse': 3}, 1.0), ({'defilement_auto': False, 'defilement_vitesse': 0}, 0.0),
                                ({'defilement_auto': False}, 0.0), ({'defilement_auto': True}, 1.0), ({'defilement_combat': 4}, 0.0), ({'defilement_combat': 0}, 1.0), ({'defilement_combat': 3}, 1.0),
                                ({'defilement_combat': 4, 'vitesse_combat': 3.0}, 0.0), ({'defilement_combat': 2, 'vitesse_combat': 3.0}, 3.0)):
            r, _ = load(dict(old, defilement_force=True))
            self.assertEqual(r['vitesse_combat'], expected, old)
            for k in ('defilement_auto', 'defilement_vitesse', 'defilement_force', 'defilement_combat'): self.assertNotIn(k, r.v)
        r, _ = load({'defilement_auto': False, 'defilement_vitesse': 1}); self.assertEqual(r['vitesse_combat'], 1.0)      # rien n'etait impose : rien ne l'est apres la migration
        r, _ = load({'defilement_force': False, 'defilement_combat': 4}); self.assertEqual(r['vitesse_combat'], 1.0)

    def test_notch_like_game_is_engine_standard(self):
        """Le cran « Normal » (4 lettres par image) est la vitesse standard du jeu : c'est la valeur que la regle de priorite du jeu (game_priority.letters_per_frame) remplace par le reglage du joueur, et celle qui ne change rien."""
        from dq4_pc.core import game_priority as PJ
        self.assertEqual(RG.DEFAULT['vitesse_texte'], PJ.STANDARD_LETTERS)
        self.assertIn(float(PJ.STANDARD_LETTERS), RG.TEXT_SPEEDS)
        for v in RG.TEXT_SPEEDS: self.assertEqual(PJ.letters_per_frame(v, 400), 400, 'fenetres de combat : jamais touchees')

    def test_no_more_transition_speed_setting(self):
        """#101 : les transitions restent a la duree du jeu (x1), ce n'est plus un reglage. Un ancien fichier qui avait x2, x3 ou x4 se charge sans erreur, la cle est ignoree et n'est plus reecrite."""
        for lookup_key in ('vitesse_fondu', 'vitesse_fondu_v'): self.assertNotIn(lookup_key, RG.DEFAULT); self.assertNotIn(lookup_key, RG.Settings(None).v); self.assertNotIn(lookup_key, RG.BOUNDS)
        self.assertNotIn('vitesse_fondu', RG.SPEEDS_X_KEYS)
        for old in (1.0, 2.0, 3.0, 4.0):
            r, f = load({'vitesse_fondu': old, 'vitesse_fondu_v': 2, 'vitesse_marche': 3.0}); self.assertNotIn('vitesse_fondu', r.v); self.assertEqual(r['vitesse_marche'], 3.0)
            r.store()
            with open(f, encoding='utf-8') as fh: self.assertNotIn('vitesse_fondu', json.load(fh))
        from dq4_pc.core import engine as ENGINE
        self.assertEqual(ENGINE.State.fade_speed, 1.0)                                                            # (le moteur garde la duree d'origine)

    def test_speeds_to_x_migration(self):
        """Anciens curseurs (0,5 a 2) -> le cran x1 a x4 le plus proche (a egalite le plus rapide), jamais moins que x1."""
        for old, expected in ((0.5, 1.0), (0.9, 1.0), (1.0, 1.0), (1.25, 1.0), (1.4, 1.0), (1.5, 2.0), (1.75, 2.0), (2.0, 2.0), (2.6, 3.0), (3, 3.0), (4, 4.0), (9, 4.0), (-3, 1.0)):
            r, _ = load({'vitesse_marche': old, 'vitesse_camera': old})
            self.assertEqual((r['vitesse_marche'], r['vitesse_camera']), (expected,) * 2, old)
            self.assertTrue(all(r[k] in RG.SPEEDS_X for k in RG.SPEEDS_X_KEYS))
        self.assertEqual(RG.DEFAULT['vitesse_accel'], 1.5)                                                      # l'accelerateur garde son curseur (1 a 2)
        r, _ = load({'vitesse_accel': 1.37}); self.assertEqual(r['vitesse_accel'], 1.37)


if __name__ == '__main__':
    unittest.main(verbosity=2)
