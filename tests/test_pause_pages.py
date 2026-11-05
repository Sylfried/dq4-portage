"""Test (sans fenetre) des pages du menu Pause : racine, Son (une ligne par son : nom, volume, muet, par defaut), Commandes (vitesses x1 a x4, section « Defilement du texte »), Modifications (ex-« Jeu »).

    python3 tools/test_pause_pages.py

Le menu est pilote avec un faux « jeu » (reglages reels, son et fenetre simules) : les memes fonctions que celles du menu, clavier compris (Pause.touche).
"""
import os, sys, tempfile, types, unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import _paths          # (aide des tests : retrouver le code source dans les sous-dossiers de dq4_pc)
import pyglet
pyglet.options['shadow_window'] = False                     # (pas d'affichage necessaire : on ne dessine rien)
from dq4_pc.persistence import settings as RG
from dq4_pc.menus import pause as PA

K = pyglet.window.key
SOUND_LABELS = ['Général', 'Musique', 'Jingles et fanfares', 'Bruitages', 'Interface']
SOUND_KEYS = {'Musique': ('musique_active', 'volume_musique'), 'Jingles et fanfares': ('jingles_actifs', 'volume_jingles'), 'Bruitages': ('bruitages_actifs', 'volume_bruitages'),
            'Interface': ('interface_active', 'volume_interface'), 'Général': ('son', 'volume_general')}


class FakeSound:
    active = True; listening = False


class FakeGame:
    """Ce que le menu Pause demande a la fenetre."""
    def window_names(self): return {'BattleRoot': [1], 'BattleAction': [2], 'RootMenu': [3], 'Status': [4]}
    def __init__(self):
        self.reg = RG.Settings(os.path.join(tempfile.mkdtemp(prefix='pause_test_'), 'reglages.json'))
        self.sound = FakeSound(); self.args = types.SimpleNamespace(cache='/inexistant'); self.width, self.height = 1280, 720; self.mouse = None
        self.calls = []; self.fade = None
    def set_sound(self, yes): self.sound.active = bool(yes)
    def apply_mix(self): self.calls.append('mixage')
    def preview_sound(self, category): self.calls.append(('apercu', category))
    def set_fade(self, v): self.fade = v
    def apply_text(self): self.calls.append('texte')
    def apply_game(self): self.calls.append('jeu')
    def set_battle_speed(self, v): self.reg['vitesse_combat'] = RG.battle_notch(v); self.calls.append(('combat', RG.scroll_code(v)))
    def pause_game(self, yes): pass


def menu(screen_page):
    J = FakeGame(); p = PA.Pause(J); p.opened = True; p.stack = [screen_page]
    return J, p


def by_caption(p, lib):
    return next(e for e in p._entries() if e['l'] == lib)


class Headings(unittest.TestCase):
    """Liste deroulante « Interface à modifier » : les intertitres de groupe (« Écran tactile », « Dialogues »...) sont discrets, jamais en or (l'or est celui de la valeur courante)."""
    def test_headings_neither_gold_nor_as_large_as_values(self):
        t, c = PA.heading_style(20.0)
        self.assertLess(t, 20.0 * 0.9); self.assertNotEqual(c, PA.GOLD); self.assertNotEqual(c[:3], PA.WHITE[:3])               # plus petit, ni or ni blanc
        lum = lambda x: 0.3 * x[0] + 0.59 * x[1] + 0.11 * x[2]
        self.assertLess(lum(c), lum(PA.WHITE) * 0.7); self.assertLess(c[2], c[0])                                              # terne (moins lumineux que le blanc) mais encore un gris dore (pas un gris neutre)
        self.assertLess(c[0] - c[2], 60); self.assertLess(lum(c), lum(PA.GOLD) - 40)                                             # (et nettement moins vif que l'or de la valeur courante)
        self.assertEqual(PA.GOLD, (255, 235, 4, 255))                                                                            # l'or reste celui de la valeur courante

    def test_list_code_uses_heading_style(self):
        src = _paths.source('pause.py')
        i = src.index('if self._header(vals[j]):'); block = src[i:i + 700]
        self.assertIn('heading_style(fs)', block); self.assertNotIn(', OR)', block)                                           # l'intertitre n'est plus dessine en or


class Root(unittest.TestCase):
    def test_entries(self):
        _, p = menu('racine'); libs = [e['l'] for e in p._entries()]
        for old in ('Vitesse de défilement du texte', 'Texte et défilement'): self.assertNotIn(old, libs)             # plus de page du texte : ses deux options sont dans Commandes
        self.assertEqual(libs, ['Reprendre', 'Historique', 'États', 'Affichage', 'Son', 'Commandes', 'Modifications', "Revenir à l'écran titre"])
        self.assertNotIn('Jeu', libs); self.assertEqual(libs.index('Modifications'), libs.index('Commandes') + 1)                # « Modifications » (ex-« Jeu ») : juste sous « Commandes »
        self.assertFalse(hasattr(p, '_e_texte'))


class SoundPage(unittest.TestCase):
    def test_one_line_per_sound(self):
        _, p = menu('son'); e = p._entries()
        self.assertEqual([x['l'] for x in e], SOUND_LABELS)
        self.assertNotIn('sep', [x['t'] for x in e], 'plus de sections')
        for x in e:                                                                    # chaque ligne : une barre de volume (curseur), un bouton muet, un bouton « par defaut »
            self.assertEqual(x['t'], 'curs'); self.assertTrue(all(k in x for k in ('fixe', 'actif', 'ok', 'defaut', 'est_defaut')), x['l'])

    def test_mute_cuts_and_restores_correct_switch(self):
        J, p = menu('son')
        for lib in SOUND_LABELS:
            active_key, vol_key = SOUND_KEYS[lib]; x = by_caption(p, lib)
            read = (lambda: J.sound.active) if lib == 'Général' else (lambda c=active_key: J.reg[c])
            self.assertTrue(read() and x['actif']())
            x['ok'](); self.assertFalse(read(), lib); self.assertFalse(by_caption(p, lib)['actif']())
            if lib == 'Général': self.assertIs(J.reg['son'], False)
            others = [l for l in SOUND_LABELS if l != lib]
            self.assertTrue(all(by_caption(p, o)['actif']() for o in others), 'une ligne ne coupe que son propre son')
            self.assertEqual(J.reg[vol_key], 1.0, 'couper ne change pas le volume')
            x['ok'](); self.assertTrue(read(), lib)

    def test_default_resets_volume_and_sound(self):
        J, p = menu('son')
        for lib in SOUND_LABELS:
            active_key, vol_key = SOUND_KEYS[lib]; x = by_caption(p, lib)
            self.assertTrue(x['est_defaut']())
            x['fixe'](0.3); x['ok']()
            self.assertFalse(x['est_defaut']()); self.assertAlmostEqual(J.reg[vol_key], 0.3, 2)
            x['defaut'](); self.assertAlmostEqual(J.reg[vol_key], RG.DEFAULT[vol_key], 3); self.assertTrue(x['actif']()); self.assertTrue(x['est_defaut']())
            x['fixe'](0.3); self.assertFalse(x['est_defaut'](), 'un volume different suffit')
            x['defaut']()
        J2, p2 = menu('son'); x = by_caption(p2, 'Musique'); x['ok'](); self.assertFalse(x['est_defaut'](), 'coupe : pas par defaut'); x['defaut'](); self.assertTrue(J2.reg['musique_active'])

    def test_keyboard(self):
        J, p = menu('son')
        p.key_press(K.DOWN); self.assertEqual(p.selected['son'], 1)                            # Musique
        p.key_press(K.LEFT); self.assertAlmostEqual(J.reg['volume_musique'], 0.95, 2)
        p.key_press(K.LEFT); p.key_press(K.RIGHT); self.assertAlmostEqual(J.reg['volume_musique'], 0.95, 2)
        p.key_press(K.RETURN); self.assertFalse(J.reg['musique_active'])                  # Entree : muet
        self.assertIsNone(p.entry, 'Entree ne lance pas la saisie du volume sur cette page')
        p.key_press(K.RETURN); self.assertTrue(J.reg['musique_active'])
        p.key_press(K.SPACE); self.assertFalse(J.reg['musique_active']); p.key_press(K.SPACE)
        p.key_press(K.DELETE); self.assertAlmostEqual(J.reg['volume_musique'], 1.0, 3)    # Suppr : par defaut
        p.key_press(K.LEFT); p.key_press(K.LEFT); p.key_press(K.RETURN); p.key_press(K.HOME)       # Debut : aussi
        self.assertAlmostEqual(J.reg['volume_musique'], 1.0, 3); self.assertTrue(J.reg['musique_active'])
        p.key_press(K.UP); p.key_press(K.UP); self.assertEqual(p.selected['son'], 4)              # bouclage : en haut de la liste on arrive en bas
        p.key_press(K.DOWN); self.assertEqual(p.selected['son'], 0)

    def test_clicking_value_allows_typing(self):
        J, p = menu('son'); x = by_caption(p, 'Bruitages')
        x['saisie'](40); self.assertAlmostEqual(J.reg['volume_bruitages'], 0.4, 3)

    def test_volume_plays_a_preview_and_so_does_unmuting(self):
        J, p = menu('son'); x = by_caption(p, 'Bruitages')
        J.calls.clear(); x['moins'](); self.assertIn(('apercu', 'effets'), J.calls)
        x['ok'](); J.calls.clear(); x['ok'](); self.assertIn(('apercu', 'effets'), J.calls, 'le son revient : on l\'entend'); self.assertIn('mixage', J.calls)


class ScrollSection(unittest.TestCase):
    """Commandes > « Défilement du texte » : « Vitesse du texte » et « Vitesse de combat » (ex-page « Vitesse de défilement du texte » du menu racine), nouvelle section juste sous « Vitesses »."""

    @staticmethod
    def lines(p): return p._entries()

    def test_section_below_the_speeds(self):
        _, p = menu('commandes'); e = self.lines(p); ls = [(x['t'], x['l']) for x in e]
        i = ls.index(('sep', 'Défilement du texte'))
        self.assertEqual(ls[i + 1:i + 3], [('choix', 'Vitesse du texte'), ('choix', 'Vitesse de combat')]); self.assertEqual(e[i + 3]['t'], 'sep')          # deux options, puis la section suivante
        self.assertEqual(ls[i + 3], ('sep', 'Actions du jeu'))
        k = ls.index(('sep', 'Vitesses')); self.assertLess(k, i)
        self.assertEqual([t for t, _ in ls[k + 1:i]].count('sep'), 0, 'aucune section entre « Vitesses » et « Défilement du texte » : elle est juste dessous')
        self.assertEqual(ls[i - 1], ('touche', 'Changer la vitesse en combat'))                                                                          # (derniere ligne des vitesses)
        self.assertEqual([l for t, l in ls if t == 'sep'], ['Déplacement', 'Caméra', 'Clic molette maintenu + déplacement', 'Clic molette', 'Vitesses', 'Défilement du texte', 'Actions du jeu', 'Autres'])        # (la camera ne fait que tourner et se recentrer : D-233 ; plus de zoom ni de molette)

    def test_all_camera_options_in_a_single_group(self):                 # D-237 : « Regroupe toutes les options de caméra directement dans un groupe nommé "Caméra" »
        _, p = menu('commandes'); e = self.lines(p); ls = [(x['t'], x['l']) for x in e]
        i = ls.index(('sep', 'Caméra')); j = ls.index(('sep', 'Vitesses'))
        self.assertEqual(ls.count(('sep', 'Caméra')), 1); self.assertNotIn('Caméra au clavier', [l for _, l in ls]); self.assertNotIn('Caméra à la souris', [l for _, l in ls])
        group = ls[i + 1:j]
        self.assertEqual(group, [('touche', 'Caméra (Gauche)'), ('touche', 'Caméra (Droite)'), ('choix', 'Inverser gauche / droite'),
                                  ('sep', 'Clic molette maintenu + déplacement'), ('sep', 'Clic molette'), ('choix', 'Vitesse de caméra')])
        self.assertTrue(all(l != 'Vitesse de caméra' for _, l in ls[j:]), 'la vitesse de caméra n\'est plus dans « Vitesses »')
        self.assertEqual(ls.index(('touche', 'Caméra (Gauche)')) > ls.index(('touche', 'Droite')), True)                                  # (le groupe vient apres le deplacement)
        info = {x['l']: x.get('v') for x in e if x['t'] == 'sep' and x.get('v')}
        self.assertEqual(info, {'Clic molette maintenu + déplacement': 'Tourne la caméra', 'Clic molette': 'Recentre la caméra'})

    def test_no_more_text_page(self):
        _, p = menu('racine'); self.assertNotIn('texte', [e['l'] for e in p._entries()])
        with open(PA.__file__, encoding='utf-8') as f: src = f.read()
        self.assertNotIn("_go('texte')", src); self.assertNotIn("titles['texte']", src)

    def test_names(self):
        _, p = menu('commandes')
        vt = by_caption(p, 'Vitesse du texte')
        self.assertEqual([p._value_name('Vitesse du texte', v) for v in vt['vals']], ['Très lent', 'Lent', 'Assez lent', 'Normal', 'Rapide', 'Très rapide', 'Instantané'])
        cb = by_caption(p, 'Vitesse de combat')
        self.assertEqual([p._value_name('Vitesse de combat', v) for v in cb['vals']], ['Manuel', 'Normal', 'Rapide', 'Très rapide'])
        self.assertEqual(cb['vals'], [0.0, 1.0, 2.0, 3.0])

    def test_text_speed(self):
        J, p = menu('commandes'); vt = by_caption(p, 'Vitesse du texte')
        self.assertEqual((vt['get'](), vt['v']()), (4.0, 'Normal')); self.assertTrue(vt['est_defaut']())
        vt['set'](16.0); self.assertEqual(J.reg['vitesse_texte'], 16.0); self.assertEqual(J.calls[-1], 'texte'); self.assertFalse(vt['est_defaut']())        # la fenetre est prevenue
        vt['defaut'](); self.assertEqual(J.reg['vitesse_texte'], 4.0); self.assertEqual(J.calls[-1], 'texte'); self.assertTrue(vt['est_defaut']())
        self.assertTrue(vt.get('aide'))

    def test_choice_changes_speed_and_scroll(self):
        """« Vitesse de combat » : le menu previent la fenetre (qui impose aussi le defilement : 4 en Manuel, 2 sinon) ; la liste boucle ; ↺ remet Normal (au clavier : la ligne est choisie dans la page Commandes)."""
        J, p = menu('commandes'); cb = by_caption(p, 'Vitesse de combat')
        self.assertEqual((cb['get'](), cb['v']()), (1.0, 'Normal')); self.assertTrue(cb['est_defaut']())
        p.selected['commandes'] = [x['l'] for x in p._entries()].index('Vitesse de combat'); p.key_press(K.RIGHT); self.assertEqual(J.reg['vitesse_combat'], 2.0)
        p.key_press(K.RIGHT); self.assertEqual(J.reg['vitesse_combat'], 3.0)
        p.key_press(K.RIGHT); self.assertEqual(J.reg['vitesse_combat'], 0.0)                                       # (la liste boucle) Très rapide -> Manuel
        self.assertEqual(J.calls[-1], ('combat', 4)); self.assertFalse(cb['est_defaut']())
        cb['defaut'](); self.assertEqual(J.reg['vitesse_combat'], 1.0); self.assertEqual(J.calls[-1], ('combat', 0)); self.assertTrue(cb['est_defaut']())      # ↺ : Normal
        self.assertTrue(cb.get('aide')); self.assertNotIn('x2', cb['aide'])

    def test_no_old_setting(self):
        _, p = menu('commandes'); ls = [x.get('l') for x in p._entries()]
        for old in ('Défilement automatique', 'Vitesse de défilement', 'Messages en combat', 'Rétablir le réglage du jeu'): self.assertNotIn(old, ls)


class ChangesPage(unittest.TestCase):
    LIB = 'PV et PM restaurés au niveau supérieur'

    def test_option_disabled_by_default_with_restoration(self):
        """Page « Modifications » (ex-« Jeu ») : un interrupteur Oui / Non, Non par defaut (comme le jeu), qui previent la fenetre ; ↺ le remet sur Non."""
        J, p = menu('modifications'); x = by_caption(p, self.LIB)
        self.assertEqual(x['vals'], [True, False]); self.assertFalse(J.reg['soin_niveau']); self.assertTrue(x['est_defaut']())
        x['set'](True); self.assertTrue(J.reg['soin_niveau']); self.assertEqual(J.calls[-1], 'jeu'); self.assertFalse(x['est_defaut']())
        x['defaut'](); self.assertFalse(J.reg['soin_niveau']); self.assertEqual(J.calls[-1], 'jeu'); self.assertTrue(x['est_defaut']())
        self.assertTrue(x.get('aide'))

    def test_one_line_and_entry_of_the_root(self):
        J, p = menu('modifications'); self.assertEqual([e['l'] for e in p._entries()], [self.LIB])
        p.stack = ['racine']; e = next(e for e in p._entries() if e['l'] == 'Modifications'); e['ok'](); self.assertEqual(p.screen_page, 'modifications')
        self.assertFalse(hasattr(p, '_e_jeu')); self.assertNotIn('Jeu', [e['l'] for e in p._entries()])
        with open(PA.__file__, encoding='utf-8') as f: src = f.read()
        self.assertIn("titles['modifications'] = 'Modifications'", src); self.assertNotIn("_go('jeu')", src)                                          # titre de la page : « Modifications »

    def test_setting_stored(self):
        J = FakeGame(); J.reg['soin_niveau'] = True; J.reg.store()
        self.assertTrue(RG.Settings(J.reg.path)['soin_niveau'])
        J.reg.v['soin_niveau'] = 'oui'; J.reg.store(); self.assertFalse(RG.Settings(J.reg.path)['soin_niveau'])        # valeur invalide : retour au defaut (Non)


class CommandsPage(unittest.TestCase):
    LIBS = ('Vitesse de marche', 'Vitesse de caméra')                                          # (plus de « Vitesse de transition » depuis #101 : fixe a x1)

    def test_speeds_in_options(self):
        J, p = menu('commandes')
        for lib in self.LIBS:
            x = by_caption(p, lib); self.assertEqual(x['t'], 'choix'); self.assertEqual(x['vals'], [1.0, 2.0, 3.0, 4.0])
            self.assertEqual([p._value_name(lib, v) for v in x['vals']], ['x1', 'x2', 'x3', 'x4'])
        x = by_caption(p, "Multiplicateur de l'accélérateur"); self.assertEqual(x['t'], 'curs'); self.assertAlmostEqual(x['v'] and J.reg['vitesse_accel'], 1.5)    # l'accelerateur garde son curseur
        self.assertNotIn("Vitesse de l'accélérateur", [e.get('l') for e in p._entries()])                                                                                       # (ancien libelle : renomme)

    def test_battle_speed_key(self):
        """Commandes > Vitesses : pas de reglage de vitesse de combat (il est dans la section « Défilement du texte », juste dessous), seulement la touche « Changer la vitesse en combat », juste sous le multiplicateur de l'accelerateur."""
        J, p = menu('commandes'); e = p._entries(); ls = [x['l'] for x in e]
        i = ls.index("Multiplicateur de l'accélérateur"); self.assertEqual(ls[i - 1], "Touche d'accélérateur")
        self.assertEqual(ls[i + 1], 'Changer la vitesse en combat'); self.assertEqual(e[i + 2]['t'], 'sep'); self.assertEqual(ls[i + 2], 'Défilement du texte')      # (puis la section suivante)
        self.assertEqual(ls.count('Vitesse de combat'), 1)                                                         # (un seul reglage : dans la section Défilement du texte, pas dans Vitesses)
        for old in ('Vitesse des combats', 'Touche de vitesse des combats'): self.assertNotIn(old, ls)
        t = by_caption(p, 'Changer la vitesse en combat'); self.assertEqual((t['t'], t['act']), ('touche', 'vit_combat')); self.assertEqual(t['v'], ['V', '—'])
        self.assertIn('Manuel', t['aide']); self.assertNotIn('x2', t['aide'])

    def test_value_change(self):
        J, p = menu('commandes')
        for lib, lookup_key in zip(self.LIBS, RG.SPEEDS_X_KEYS):
            x = by_caption(p, lib)
            for v in (4.0, 3.0, 2.0, 1.0): x['set'](v); self.assertEqual(J.reg[lookup_key], v); self.assertEqual(x['v'](), 'x%d' % v)
        self.assertNotIn('Vitesse de transition', [e.get('l') for e in p._entries()])                           # (#101 : retiree, les transitions restent a x1)

    def test_helptexts(self):
        _, p = menu('commandes')
        for lib in self.LIBS: self.assertTrue(by_caption(p, lib).get('aide'), lib)


class Hover(unittest.TestCase):
    """Plus d'encadre jaune : sous le pointeur (mode souris), une zone s'assombrit ; au clavier, rien n'est survole."""
    def test_pointer(self):
        _, p = menu('racine'); z = (10, 10, 50, 30)
        p.mouse_mode = False; p.mouse_pos = (20, 20); self.assertFalse(p._pointer_in(z)); self.assertFalse(p._hovered(z))
        p.mouse_mode = True; self.assertTrue(p._pointer_in(z)); self.assertTrue(p._hovered(z))
        p.mouse_pos = (60, 20); self.assertFalse(p._hovered(z))                                # le pointeur sort : la zone se rallume
        p.mouse_pos = (20, 20); p.popup = {'titre': 'x', 'sel': 1}; self.assertFalse(p._hovered(z)); self.assertTrue(p._pointer_in(z))        # sous une fenetre modale : le survol lui appartient
        self.assertFalse(p._pointer_in(None))
        p.popup = None; p.mouse_pos = (20, 20); self.assertTrue(p._hovered(z)); p.output(); self.assertFalse(p._hovered(z), 'le pointeur a quitte la fenetre : plus rien n\'est survole')

    def test_no_more_yellow_border_in_page_code(self):
        with open(PA.__file__, encoding='utf-8') as f: src = f.read()
        self.assertNotIn('JAUNE if sel', src); self.assertNotIn(', YELLOW)', src.replace('color=YELLOW)', ''))


class InterfaceEntries(unittest.TestCase):
    """Liste « Interface à modifier » : bouton de vitesse de combat dans son propre element du groupe « Combat », avec ses propres reglages."""
    def test_groups(self):
        J, p = menu('interface'); v = p.targets()
        screen_page = v[v.index('#Écran tactile') + 1:v.index('#Dialogues')]; self.assertEqual(screen_page, ['boutons'])                  # « Boutons et croix de l'écran » reste seul dans son groupe
        i = v.index('#Combat'); self.assertEqual(v[i + 1], 'bouton_vitesse')                                                   # le bouton de vitesse : premier element du groupe « Combat »
        self.assertEqual(v[i + 1:i + 4], ['bouton_vitesse', 'BattleRoot', 'BattleAction'])
        self.assertEqual(p.target_name('bouton_vitesse'), 'Combat : bouton de vitesse'); self.assertEqual(p.target_name('boutons'), "Boutons et croix de l'écran")
        self.assertEqual(sum(1 for x in v if x == 'bouton_vitesse'), 1)

    def test_speed_button_page(self):
        J, p = menu('interface'); p.target = RG.SPEED_TARGET; libs = [e['l'] for e in p._entries()]
        self.assertIn('Taille du bouton', libs); self.assertIn('Replacer sur le bord gauche', libs); self.assertIn("Afficher cette interface à l'écran", libs)
        for other in ('Taille des boutons', 'Afficher la croix', 'Taille de la croix', 'Position horizontale'): self.assertNotIn(other, libs)
        p.target = RG.SCREEN_TARGET; libs = [e['l'] for e in p._entries()]
        self.assertIn('Taille des boutons', libs); self.assertIn('Afficher la croix', libs); self.assertNotIn('Taille du bouton', libs)

    def test_settings_specific_to_the_button(self):
        J, p = menu('interface'); R = J.reg; p.target = RG.SPEED_TARGET
        p._set_visible(RG.SPEED_TARGET, False); self.assertEqual((R['bouton_vitesse'], R['boutons']), (False, True)); self.assertFalse(p._visible(RG.SPEED_TARGET)); self.assertTrue(p._visible(RG.SCREEN_TARGET))
        p._set_visible(RG.SCREEN_TARGET, False); p._set_visible(RG.SPEED_TARGET, True); self.assertEqual((R['bouton_vitesse'], R['boutons']), (True, False))
        e = by_caption(p, 'Taille du bouton'); e['plus'](); e['plus'](); self.assertAlmostEqual(R['bouton_vitesse_taille'], 1.2); self.assertEqual(R['boutons_taille'], 1.0); e['defaut'](); self.assertEqual(R['bouton_vitesse_taille'], 1.0)
        R['bouton_vitesse_pos'] = [3.0, 4.0]; by_caption(p, 'Replacer sur le bord gauche')['ok'](); self.assertEqual(R['bouton_vitesse_pos'], [])
        R['bouton_vitesse_pos'] = [3.0, 4.0]; R['boutons_pos'] = {'carte': [1, 1]}; by_caption(p, 'Rétablir cette interface')['ok']()
        self.assertEqual((R['bouton_vitesse_pos'], R['bouton_vitesse_taille'], R['bouton_vitesse'], R['boutons_pos']), ([], 1.0, True, {'carte': [1, 1]}))      # la remise ne touche que le bouton

    def test_editor_shows_the_right_element(self):
        from dq4_pc.menus import hud_mobile as HM
        self.assertEqual(HM.editor_names(RG.SCREEN_TARGET), ('carte', 'menu', 'discussion', HM.DPAD)); self.assertEqual(HM.editor_names(RG.SPEED_TARGET), (HM.BATTLE,)); self.assertEqual(HM.editor_names('msg'), ())
        self.assertNotIn(HM.BATTLE, HM.editor_names(RG.SCREEN_TARGET))                                                               # plus dans « Boutons et croix de l'écran »


if __name__ == '__main__':
    unittest.main(verbosity=2)
