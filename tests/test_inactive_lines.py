"""Test des lignes inactives du menu Pause (page Affichage : « Résolution » en plein écran ; page États : emplacements vides) et du libellé « Modifications ».

    python3 tools/test_inactive_lines.py

Une ligne qui ne peut pas être modifiée dans l'état courant (`off`) est grisée en entier (libellé, valeur, flèche, bouton ↺, case), jamais choisie (le curseur doré et le clavier la sautent), jamais survolée (aucun
surlignage), jamais cliquée ni validée ; plus aucun texte rouge de note sous les valeurs. Le test couvre tous les types de lignes de toutes les pages : il marque chaque ligne, une à une, comme inactive (PauseMarked)
et vérifie qu'aucune action ne l'atteint (clavier, clic, survol, molette, glisser, saisie, liste déroulante). Le menu est piloté avec un faux « jeu » ; le dessin se fait dans une fenêtre pyglet cachée (EGL sans écran) :
le survol est vérifié sur les pixels (la ligne inactive ne change pas quand le pointeur la survole, une ligne active si).
"""
import copy, os, sys, types, unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import _paths          # (aide des tests : retrouver le code source dans les sous-dossiers de dq4_pc)
import pyglet
if sys.platform.startswith('linux') and not os.environ.get('DISPLAY'): pyglet.options['headless'] = True; pyglet.options['shadow_window'] = False
import numpy as np
from dq4_pc.persistence import settings as RG
from dq4_pc.menus import pause as PA

K = pyglet.window.key
LEFT = 1
PAGES = ('racine', 'affichage', 'son', 'commandes', 'modifications', 'etats', 'quitter', 'interface')
DRAWN_PAGES = tuple(p for p in PAGES if p != 'interface')          # (la page Interface dessine l'apercu du jeu : le faux jeu n'en a pas)
CACHE = os.environ.get('DQ_UICACHE', '/inexistant')                    # (facultatif : cache d'interface du jeu pour la police et les icones ; sans lui, polices du systeme et plaque de repli)


class FakeGame:
    """Ce que le menu Pause demande à la fenêtre ; `full` peut changer à tout moment (les lignes se recalculent à chaque image)."""
    mode = 4; zoom = 1.0

    def __init__(self, full=False):
        self.reg = RG.Settings(None); self.full = full; self.res = (1280, 720); self.calls = []; self.lbl = {}
        self.width, self.height = 1280, 720; self.args = types.SimpleNamespace(cache=CACHE); self.mouse = None
        self.post = types.SimpleNamespace(max_msaa=None); self.sound = types.SimpleNamespace(active=True, listening=False, listen=lambda b: None, tick=lambda: None)

    is_fullscreen = property(lambda self: self.full)
    def set_full_screen(self, v): self.full = bool(v); self.calls.append(('plein', bool(v)))
    def resolutions(self): return [(1280, 720), (1920, 1080), (2560, 1440)]
    def current_resolution(self): return self.res
    def set_resolution(self, v): self.res = tuple(v); self.calls.append(('res', tuple(v)))
    def set_mode(self, v): self.calls.append(('mode', v))
    def set_distance(self, v): self.calls.append(('distance', v))
    def set_sound(self, yes): self.calls.append(('son', yes))
    def apply_mix(self): self.calls.append('mixage')
    def preview_sound(self, category): self.calls.append(('apercu', category))
    def set_fade(self, v): self.calls.append(('fondu', v))
    def apply_text(self): self.calls.append('texte')
    def apply_game(self): self.calls.append('jeu')
    def set_battle_speed(self, v): self.calls.append(('combat', v))
    def window_names(self): return {}
    def state_info(self, n): return None
    def pause_game(self, yes): pass
    def quit_game(self): self.calls.append('quitter')
    def back_to_title(self): self.calls.append('titre')

    def _lbl(self, text, size_value, color=(255, 255, 255, 255), fonts=()):
        k = (text, round(size_value, 1), color, fonts)
        if k not in self.lbl: self.lbl[k] = pyglet.text.Label(text, font_size=size_value, color=color, anchor_x='left', anchor_y='baseline')
        return self.lbl[k]


class PauseMarked(PA.Pause):
    """Menu Pause dont certaines lignes (libellés de `inactive`, sur toutes les pages) sont marquées inactives : permet d'éprouver chaque type de ligne."""
    inactive = ()

    def _entries(self):
        e = super()._entries()
        for x in e:
            if x['t'] != 'sep' and x.get('l') in self.inactive: x['off'] = True
        return e


def menu(page, full=False, klass=PA.Pause, **attrs):
    J = FakeGame(full); p = klass(J); p.opened = True; p.stack = [page]
    for k, v in attrs.items(): setattr(p, k, v)
    return J, p


def state(J, p):
    """Tout ce qu'une action sur une ligne pourrait changer."""
    return repr((copy.deepcopy(J.reg.v), list(J.calls), list(p.stack), p.capture, p.entry, p.open_dropdown, p.popup, p.dragging, J.full, J.res, p.state_action))


def labels(e): return [x.get('l') for x in e]


_win = []
def window():
    """Fenêtre pyglet cachée (une seule pour tout le test) ; None si le contexte graphique manque ici."""
    if not _win:
        try:
            import pyglet.window
            _win.append(pyglet.window.Window(width=1280, height=720, visible=False))
        except Exception as ex: _win.append(ex)
    if isinstance(_win[0], Exception): raise unittest.SkipTest('pas de contexte graphique ici (%r)' % (_win[0],))
    return _win[0]


def render_texture(p):
    """Dessine le menu puis rend l'image (tableau RGBA, origine en bas à gauche)."""
    w = window(); w.switch_to(); w.clear(); p.draw_all()
    im = pyglet.image.get_buffer_manager().get_color_buffer().get_image_data()
    return np.frombuffer(im.get_data('RGBA', im.width * 4), np.uint8).reshape(im.height, im.width, 4).copy()


def crop(img, z, margin=2): return img[int(z[1]) + margin:int(z[3]) - margin, int(z[0]) + margin:int(z[2]) - margin]


def zone_of(p, idx):
    """Zone (x0, y0, x1, y1) de la ligne idx à la dernière image : (zone, active ?)."""
    for z in p.zones:
        if z[4] == idx: return z[:4], True
    for z in p.zones_off:
        if z[4] == idx: return z[:4], False
    return None, None


class DisplayPage(unittest.TestCase):
    """« Résolution » est inactive en plein écran (le choix du moniteur du plein écran n'existe plus : le plein écran se fait sur l'écran de la fenêtre)."""
    def lines(self, full):
        J, p = menu('affichage', full); e = p._entries(); return J, p, e, {x['l']: i for i, x in enumerate(e)}

    def test_line_states(self):
        for full in (False, True):
            J, p, e, n = self.lines(full)
            self.assertEqual(p._inactive(e[n['Résolution']]), full, full); self.assertNotIn('Écran du plein écran', n)
            self.assertFalse(p._inactive(e[n['Plein écran']])); self.assertFalse(p._inactive(e[n['Netteté']])); self.assertFalse(p._inactive(e[n['Interface']]))

    def test_no_more_red_note_text(self):
        for full in (False, True):
            J, p, e, n = self.lines(full)
            for x in e: self.assertNotIn('note', x, x.get('l'))
        with open(PA.__file__, encoding='utf-8') as f: src = f.read()
        self.assertNotIn("entry['note']", src); self.assertNotIn('note=', src); self.assertNotIn('dec = ', src)                    # (plus de paramètre `note`, plus de place réservée sous la valeur ; restent en rouge : le message d'erreur du pied du cadre et « Masquée » de l'éditeur, qui ne sont pas des notes sous les valeurs)
        for text in ('Un seul écran détecté', 'Sans effet en plein écran'): self.assertNotIn("'%s" % text, src)

    def test_navigation_skips_inactive_lines(self):
        J, p, e, n = self.lines(False); p.selected['affichage'] = n['Plein écran']                      # fenêtre : rien n'est sauté
        p.key_press(K.DOWN); self.assertEqual(p.selected['affichage'], n['Résolution'])
        p.key_press(K.UP); self.assertEqual(p.selected['affichage'], n['Plein écran'])
        J, p, e, n = self.lines(True); p.selected['affichage'] = n['Plein écran']                       # plein écran : « Résolution » est sautée
        p.key_press(K.DOWN); self.assertEqual(p.selected['affichage'], n['Netteté'])
        p.key_press(K.UP); self.assertEqual(p.selected['affichage'], n['Plein écran'])
        p.key_press(K.UP); self.assertEqual(p.selected['affichage'], n['Langue'])                           # (« Langue » est la premiere ligne de la page, D-238)
        p.key_press(K.UP); self.assertEqual(p.selected['affichage'], n['Interface'])                        # (le tour de la liste reprend par la fin)
        p.key_press(K.DOWN); self.assertEqual(p.selected['affichage'], n['Langue'])
        p.key_press(K.DOWN); self.assertEqual(p.selected['affichage'], n['Plein écran'])

    def test_wheel_skips_inactive_lines(self):
        J, p, e, n = self.lines(True); p.selected['affichage'] = n['Plein écran']
        p.wheel(1); self.assertEqual(p.selected['affichage'], n['Netteté'])                            # (molette vers le haut = ligne suivante)

    def test_keyboard_without_effect_on_inactive_line(self):
        for full, lib in ((True, 'Résolution'),):
            J, p, e, n = self.lines(full); p.selected['affichage'] = n[lib]; before = state(J, p)
            for t in (K.RETURN, K.SPACE, K.LEFT, K.RIGHT, K.DELETE, K.HOME): p.key_press(t); p.selected['affichage'] = n[lib]
            self.assertEqual(state(J, p), before, (full, lib)); self.assertIsNone(p._current())

    def test_active_line_always_adjustable(self):
        J, p, e, n = self.lines(False); p.selected['affichage'] = n['Résolution']; p.key_press(K.RIGHT)          # fenêtre : la résolution se règle
        self.assertEqual(J.calls, [('res', (1920, 1080))])

    def test_state_recomputed_each_frame(self):
        """Une ligne grisée parce qu'une autre valeur la rend sans effet redevient active dès que cette valeur change (et inversement)."""
        J, p = menu('affichage', False); n = {x['l']: i for i, x in enumerate(p._entries())}
        self.assertFalse(p._inactive(p._entries()[n['Résolution']]))
        p.selected['affichage'] = n['Plein écran']; p.key_press(K.RETURN)                                          # Entrée sur l'interrupteur : plein écran
        self.assertTrue(J.full); self.assertTrue(p._inactive(p._entries()[n['Résolution']]))              # ... « Résolution » est grisée tout de suite
        p.key_press(K.RETURN); self.assertFalse(J.full); self.assertFalse(p._inactive(p._entries()[n['Résolution']]))      # ... et se rallume au retour en fenêtre

    def test_selection_leaves_line_that_became_inactive(self):
        J, p = menu('affichage', False); n = {x['l']: i for i, x in enumerate(p._entries())}; window()
        p.selected['affichage'] = n['Résolution']; render_texture(p); self.assertEqual(p.selected['affichage'], n['Résolution'])
        J.full = True; render_texture(p); self.assertEqual(p.selected['affichage'], n['Netteté'])                      # F11 pendant que « Résolution » est choisie : le curseur passe à la ligne active suivante
        J.full = False; render_texture(p); self.assertEqual(p.selected['affichage'], n['Netteté'])                    # (revenue en fenêtre : la ligne se rallume, le curseur reste où il est)

    def test_click_hover_and_tooltip(self):
        J, p = menu('affichage', True); n = {x['l']: i for i, x in enumerate(p._entries())}; window(); render_texture(p)
        for lib in ('Résolution',):
            z, active = zone_of(p, n[lib]); self.assertFalse(active, lib)
            for f in (0.05, 0.3, 0.5, 0.7, 0.95):                                                          # (libellé, valeur, flèche, bouton ↺ : n'importe où dans la case)
                x, y = z[0] + f * (z[2] - z[0]), (z[1] + z[3]) / 2; before = state(J, p); selected = p.selected['affichage']
                p.hovered(x, y); self.assertTrue(p.mouse_mode); self.assertEqual(p.selected['affichage'], selected, 'survol')
                p.click(x, y, LEFT); self.assertEqual(state(J, p), before, 'clic'); self.assertEqual(p.selected['affichage'], selected)
                p.release(x, y, LEFT)
            self.assertTrue(p._line_helptext(p._entries()[n[lib]]), lib)                                      # (elle garde son aide : elle dit pourquoi)
        self.assertNotIn('Entrée', p._line_helptext(p._entries()[n['Résolution']]))                           # (mais plus de consigne « Entrée ou clic : ouvrir la liste »)
        z, active = zone_of(p, n['Netteté']); self.assertTrue(active)                                      # une ligne active, elle, répond
        p.hovered((z[0] + z[2]) / 2, (z[1] + z[3]) / 2); self.assertEqual(p.selected['affichage'], n['Netteté'])

    def test_pixels_no_highlight_on_hover(self):
        """La ligne inactive est identique avec ou sans pointeur dessus ; une ligne active change (contrôle du test)."""
        J, p = menu('affichage', True); n = {x['l']: i for i, x in enumerate(p._entries())}; window(); far = (5.0, 5.0)
        p.mouse_mode = True; p.mouse_pos = far; render_texture(p); background = render_texture(p)
        for lib, change in (('Résolution', False), ('Netteté', True), ('Luminosité', True)):
            z, active = zone_of(p, n[lib]); self.assertEqual(active, change, lib)
            p.mouse_pos = ((z[0] + z[2]) / 2, (z[1] + z[3]) / 2); p.tt = None; above = render_texture(p); p.mouse_pos = far; p.tt = None
            equal = np.array_equal(crop(background, z), crop(above, z))
            self.assertEqual(equal, not change, '%s : %s' % (lib, 'identique' if equal else 'différente'))
        p.mouse_pos = far

    def test_whole_cell_grayed(self):
        """La plaque d'une ligne inactive est plus sombre que celle d'une ligne active, et son texte est gris (pas blanc)."""
        J, p = menu('affichage', True); n = {x['l']: i for i, x in enumerate(p._entries())}; window(); p.mouse_mode = False; img = render_texture(p)
        zr, _ = zone_of(p, n['Résolution']); zn, _ = zone_of(p, n['Netteté'])
        def lum(z): c = crop(img, z, 6).astype(float); return c[..., :3].mean(), c[..., :3].max()
        (m_r, max_r), (m_n, max_n) = lum(zr), lum(zn)
        self.assertLess(m_r, m_n); self.assertLess(max_r, 200); self.assertGreater(max_n, 240)             # (grisée : pas de blanc franc ; active : texte blanc)


class AllTypes(unittest.TestCase):
    """Chaque ligne de chaque page, marquée inactive à son tour : aucune action ne l'atteint, le curseur l'évite, elle n'a pas de zone de clic."""
    def lines_of(self, page):
        J, p = menu(page); return [x for x in p._entries() if x['t'] != 'sep']

    def test_no_action_reaches_inactive_line(self):
        seen = set()
        for page in PAGES:
            for line in self.lines_of(page):
                lib = line['l']; J, p = menu(page, klass=PauseMarked, inactive=(lib,)); e = p._entries(); idx = labels(e).index(lib); seen.add(line['t'])
                self.assertTrue(p._inactive(e[idx]), (page, lib)); self.assertFalse(p._active(e[idx]))
                p.selected[page] = idx; before = state(J, p)
                for t in (K.RETURN, K.SPACE, K.LEFT, K.RIGHT, K.DELETE, K.HOME):
                    p.selected[page] = idx; p.key_press(t); self.assertEqual(state(J, p), before, (page, lib, t)); self.assertIsNone(p._current())
                self.assertIsNone(p._current(), (page, lib))
                p.selected[page] = idx; p.entry = None
                for direction in (K.DOWN, K.UP) if any(p._active(x) for x in e) else ():                          # navigation : jamais sur la ligne inactive (si une autre ligne est active)
                    p.selected[page] = idx
                    for _ in range(len(e) + 2):
                        p.key_press(direction); self.assertNotEqual(p.selected[page], idx, (page, lib, direction))
        self.assertGreaterEqual(seen, {'act', 'choix', 'curs', 'touche', 'slot'})                            # (tous les types de lignes ont été éprouvés)

    def test_drawing_click_hover_of_each_inactive_line(self):
        window(); seen = set()
        for page in DRAWN_PAGES:
            for line in self.lines_of(page):
                lib = line['l']; J, p = menu(page, klass=PauseMarked, inactive=(lib,)); e = p._entries(); idx = labels(e).index(lib); seen.add(line['t'])
                p.selected[page] = idx; render_texture(p)
                if any(p._active(x) for x in e): self.assertNotEqual(p.selected[page], idx, (page, lib, 'le curseur quitte la ligne inactive'))          # (page d'une seule ligne : le curseur n'a nulle part ou aller)
                z, active = zone_of(p, idx)
                if z is None: continue                                                                      # (ligne hors de la vue d'une liste qui défile : rien à cliquer)
                self.assertFalse(active, (page, lib)); self.assertNotIn(idx, p.bars); self.assertNotIn(idx, p.zones_val); self.assertNotIn(idx, p.default_zones); self.assertNotIn(idx, p.zones_mute)
                self.assertFalse([k for k in p.zones_eff if k[0] == idx])
                for f in (0.05, 0.25, 0.5, 0.75, 0.95):
                    x, y = z[0] + f * (z[2] - z[0]), (z[1] + z[3]) / 2; before = state(J, p); selected = p.selected[page]
                    p.hovered(x, y); self.assertEqual(p.selected[page], selected, (page, lib, 'survol')); p.click(x, y, LEFT); self.assertEqual(state(J, p), before, (page, lib, f, 'clic'))
                    self.assertEqual(p.selected[page], selected); p.release(x, y, LEFT); p.drag_to(x, y); self.assertEqual(state(J, p), before, (page, lib, 'glisser'))
                    render_texture(p)
        self.assertGreaterEqual(seen, {'act', 'choix', 'curs', 'touche', 'slot'})

    def test_page_without_any_active_line(self):
        """Toutes les lignes inactives : ni erreur ni action ; la sélection ne bouge pas, le curseur n'est pas dessiné."""
        window()
        for page in DRAWN_PAGES:
            J, p = menu(page); libs = tuple(x['l'] for x in p._entries() if x['t'] != 'sep')
            J, p = menu(page, klass=PauseMarked, inactive=libs); p.selected[page] = 2 if page == 'quitter' else 0; selected = p.selected[page]; before = state(J, p)
            render_texture(p); self.assertEqual(p.selected[page], selected, page)
            for t in (K.DOWN, K.UP, K.LEFT, K.RIGHT, K.RETURN, K.SPACE, K.DELETE, K.HOME, K.PAGEDOWN): p.key_press(t)
            p.wheel(1); p.wheel(-1); self.assertEqual(p.selected[page], selected, page)
            for z in p.zones_off:
                x, y = (z[0] + z[2]) / 2, (z[1] + z[3]) / 2; p.hovered(x, y); p.click(x, y, LEFT); p.release(x, y, LEFT); p.drag_to(x, y)
            self.assertEqual(p.selected[page], selected, page); render_texture(p); self.assertIsNone(p._current())
            self.assertEqual(state(J, p), before, page)

    def test_an_active_line_stays_usable(self):
        """Marquer les autres lignes ne gêne pas celle qui reste (contrôle du test)."""
        window(); J, p = menu('quitter', klass=PauseMarked, inactive=('Oui',)); p.selected['quitter'] = 2; render_texture(p)
        p.key_press(K.UP); self.assertEqual(p.selected['quitter'], 2)                                               # « Oui » est inactive : le curseur reste sur « Non »
        z, active = zone_of(p, 1); self.assertFalse(active)
        p.click((z[0] + z[2]) / 2, (z[1] + z[3]) / 2, LEFT); self.assertNotIn('quitter', J.calls); self.assertEqual(p.stack, ['quitter'])          # clic sur « Oui » inactive : l'application ne se ferme pas
        z, active = zone_of(p, 2); self.assertTrue(active); p.click((z[0] + z[2]) / 2, (z[1] + z[3]) / 2, LEFT); self.assertFalse(p.opened)          # clic sur « Non » (active) : le menu se ferme


class ChangesDuringAction(unittest.TestCase):
    """Une ligne qui devient inactive pendant qu'on la tient (curseur glissé, valeur tapée, liste ouverte) est lâchée sans rien changer."""
    def test_slider_dragged_value_typed_list_opened(self):
        window(); J, p = menu('affichage', klass=PauseMarked); n = {x['l']: i for i, x in enumerate(p._entries())}; render_texture(p)
        z, _ = zone_of(p, n['Netteté']); bx0, bx1 = p.bars[n['Netteté']]
        p.click(bx0 + 0.8 * (bx1 - bx0), (z[1] + z[3]) / 2, LEFT); self.assertEqual(p.dragging, n['Netteté']); self.assertAlmostEqual(J.reg['nettete'], 0.8, 1)       # (active : le clic règle le curseur)
        p.inactive = ('Netteté',); p.drag_to(bx0 + 0.2 * (bx1 - bx0), (z[1] + z[3]) / 2); self.assertIsNone(p.dragging); self.assertAlmostEqual(J.reg['nettete'], 0.8, 1)   # (devenue inactive en la tenant : lâchée)
        p.inactive = (); p.entry = [n['Netteté'], '5']; p.inactive = ('Netteté',); render_texture(p); self.assertIsNone(p.entry)
        p.inactive = (); p.selected['affichage'] = n['Shader']; p.key_press(K.RETURN); self.assertIsNotNone(p.open_dropdown)                                  # liste ouverte sur « Shader »
        p.inactive = ('Shader',); render_texture(p); self.assertIsNone(p.open_dropdown)


class ChangesCaption(unittest.TestCase):
    def test_caption_everywhere(self):
        J, p = menu('racine'); libs = labels(p._entries())
        self.assertIn('Modifications', libs); self.assertNotIn('Triches', libs); self.assertEqual(libs.index('Modifications'), libs.index('Commandes') + 1)
        e = next(x for x in p._entries() if x['l'] == 'Modifications'); e['ok'](); self.assertEqual(p.screen_page, 'modifications'); self.assertEqual([x['l'] for x in p._entries()], ['PV et PM restaurés au niveau supérieur'])
        base = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
        for file_name in ('pause.py', 'window.py', 'settings.py'): self.assertNotIn('triche', _paths.source(file_name).lower(), file_name)
        for file_name in ('README.md',) + tuple('tests/' + f for f in sorted(os.listdir(os.path.join(base, 'tests'))) if f.endswith('.py') and f != os.path.basename(__file__)):
            with open(os.path.join(base, file_name), encoding='utf-8') as f: self.assertNotIn('triche', f.read().lower(), file_name)


if __name__ == '__main__':
    unittest.main(verbosity=1)
