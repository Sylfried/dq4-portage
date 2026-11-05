"""Test du plantage du 05/11/2026 (Windows, premier lancement apres le passage du code en anglais, D-239) : la methode `_cachee` de la fenetre du jeu est devenue `_hidden`, et la fenetre
Windows de pyglet (`Win32Window`) a deja un attribut `_hidden = False` : il masquait la methode et le premier dessin d'un menu plantait (`'bool' object is not callable`).
Linux (tests, captures) n'a pas cet attribut : rien ne l'avait vu.

Ce test lit le code source de pyglet pour TOUTES les plateformes (Windows, X11, macOS, Wayland, sans tete), donc il tourne partout, et refuse qu'un nom de la fenetre du jeu
(methode, attribut de classe, `self.x = ...` des fichiers de dq4_pc/window) soit aussi un nom de la fenetre de pyglet, sauf ceux ecrits expres (liste ci-dessous).
Il verifie aussi qu'un clic de souris pendant le chargement du moteur (les logos) est ignore au lieu de lire `self.engine` avant qu'il existe.

    python3 tests/test_window_name_collisions.py
"""
import ast, glob, os, sys, types, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..')
sys.path.insert(0, ROOT)
import pyglet
pyglet.options['shadow_window'] = False
from dq4_pc.window import game as F
from dq4_pc.window import keyboard_mouse as KM

PYGLET_FILES = ('window/__init__.py', 'window/win32/__init__.py', 'window/xlib/__init__.py', 'window/cocoa/__init__.py',
                'window/wayland/__init__.py', 'window/headless/__init__.py', 'event.py')

# ecrits expres par le jeu (full_screen.py : taille et ecran de la fenetre pyglet, remis a jour a la main au changement de mode)
DELIBERATE = {'_width', '_height', '_screen'}


def names_in(path):
    """Noms definis par un fichier : fonctions, attributs de classe, `self.x = ...`."""
    with open(path, encoding='utf-8') as fh: tree = ast.parse(fh.read())
    out = set()
    for n in ast.walk(tree):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)): out.add(n.name)
        elif isinstance(n, ast.ClassDef):
            for b in n.body:
                if isinstance(b, ast.Assign): out.update(t.id for t in b.targets if isinstance(t, ast.Name))
                elif isinstance(b, ast.AnnAssign) and isinstance(b.target, ast.Name): out.add(b.target.id)
        if isinstance(n, (ast.Assign, ast.AugAssign, ast.AnnAssign)):
            for tg in (n.targets if isinstance(n, ast.Assign) else [n.target]):
                for x in ast.walk(tg):
                    if isinstance(x, ast.Attribute) and isinstance(x.value, ast.Name) and x.value.id == 'self': out.add(x.attr)
    return out


class WindowNames(unittest.TestCase):
    def test_no_name_shared_with_pyglet_windows(self):
        pyglet_dir = os.path.dirname(pyglet.__file__); theirs = {}
        for f in PYGLET_FILES:
            p = os.path.join(pyglet_dir, *f.split('/'))
            if os.path.exists(p):
                for k in names_in(p): theirs.setdefault(k, []).append(f)
        self.assertIn('_hidden', theirs, 'la lecture du code de pyglet ne trouve plus Win32Window._hidden : ce test ne verifie plus rien')
        ours = {}
        for p in sorted(glob.glob(os.path.join(ROOT, 'dq4_pc', 'window', '*.py'))):
            for k in names_in(p): ours.setdefault(k, []).append(os.path.basename(p))
        shared = sorted(k for k in set(ours) & set(theirs) if not k.startswith('__') and not k.startswith('on_') and k not in DELIBERATE)
        self.assertEqual(shared, [], 'noms de la fenetre du jeu deja pris par pyglet (voir les fichiers) : ' + '; '.join(f'{k} {ours[k]} / {theirs[k]}' for k in shared))

    def test_menu_method_renamed(self):
        self.assertTrue(callable(F.Game._menu_hidden))
        self.assertFalse(hasattr(F.Game, '_hidden'))

    def test_event_handlers_only_overridden_on_purpose(self):
        """Les `on_*` du jeu doivent etre de vrais evenements de pyglet (une faute de frappe ferait un gestionnaire qui ne sert a rien)."""
        events = set(pyglet.window.BaseWindow.event_types)
        for p in sorted(glob.glob(os.path.join(ROOT, 'dq4_pc', 'window', '*.py'))):
            with open(p, encoding='utf-8') as fh: body = ast.parse(fh.read()).body
            for n in body:
                if isinstance(n, ast.ClassDef) and n.name.endswith('Mixin'):
                    for f in n.body:
                        if isinstance(f, ast.FunctionDef) and f.name.startswith('on_'): self.assertIn(f.name, events, f'{os.path.basename(p)} : {f.name}')


class MouseBeforeEngine(unittest.TestCase):
    def test_click_during_loading_is_ignored(self):
        """Pendant les logos, `Game._ready` est faux et `self.engine` n'existe pas encore : le clic saute le logo, sans rien lire d'autre."""
        g = types.SimpleNamespace(_ready=False, _logo_touched=False)
        self.assertIsNone(KM.KeyboardMouseMixin.on_mouse_press(g, 10, 10, pyglet.window.mouse.LEFT, 0))
        self.assertTrue(g._logo_touched)
        self.assertFalse(hasattr(g, 'engine'))


if __name__ == '__main__':
    unittest.main()
