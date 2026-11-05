"""Langue de l'outil (D-238) : francais ou anglais pour tout ce qui est propre au portage (parametres, historique, sauvegardes, licence, informations F1, messages de la console...).
Les textes DU JEU (dialogues, menus du jeu, noms) viennent des fichiers du jeu et ne changent pas.

Reglage « Langue » (page Affichage) : `system` (defaut : francais si Windows est en francais, quelle que soit la variante, sinon anglais), `entry`, `fr`.

Principe : le texte source est le texte FRANCAIS ecrit dans le code ; `tr(text)` rend le meme texte en francais, et sa traduction anglaise (`texts_en\\`) en anglais. Un texte sans traduction reste en francais (jamais d'erreur) ;
le francais reste donc identique a lui-meme par construction. Les textes a trous restent des modeles a formater APRES la traduction : `tr('%d fichier(s)') % n`.
Les constantes de module sont marquees avec `N_` (le texte est rendu tel quel, traduit a l'affichage) : `ACTIONS = (('haut', N_('Haut')), ...)` puis `tr(label_text)` au moment de dessiner."""
import importlib
import os
import sys

CHOICES = ('systeme', 'en', 'fr')                         # valeurs du reglage « Langue »
DEFAULT = 'systeme'
MODULES_EN = ('pause', 'menus', 'window', 'divers')    # les fichiers de texts_en\ (chacun definit EN = {texte francais: texte anglais})
_request = DEFAULT
_current = None
_catalog = None


def system_language(reader=None):
    """'fr' si l'ordinateur est en francais (n'importe quelle variante : France, Belgique, Canada, Suisse...), sinon 'en'. `reader` : fonction sans argument qui rend la langue de l'interface (tests)."""
    code = None
    try:
        code = reader() if reader else _interface_language()
    except Exception:
        code = None
    return 'fr' if _is_french(code) else 'en'


def _is_french(code):
    """`code` : identifiant Windows de langue (entier, ex. 0x040C), ou texte « fr_FR.UTF-8 » / « fr-BE » / « French_France »."""
    if code is None: return False
    if isinstance(code, int): return (code & 0x3FF) == 0x0C              # identifiant primaire 0x0C = francais (toutes les variantes)
    t = str(code).strip().lower().replace('-', '_')
    return t.startswith('fr') and (len(t) == 2 or t[2] in '_.@' or t.startswith('french'))


def _interface_language():
    """La langue d'affichage de l'ordinateur : Windows (GetUserDefaultUILanguage), sinon les variables d'environnement, sinon la locale."""
    if sys.platform == 'win32':
        import ctypes
        return ctypes.windll.kernel32.GetUserDefaultUILanguage()
    for k in ('LC_ALL', 'LC_MESSAGES', 'LANG', 'LANGUAGE'):
        v = os.environ.get(k)
        if v: return v.split(':')[0]
    import locale
    return (locale.getlocale()[0] or '')


def select_language(choice, reader=None):
    """Fixe la langue : `choice` parmi CHOICES (autre valeur : `system`). -> 'fr' ou 'en'."""
    global _request, _current
    _request = choice if choice in CHOICES else DEFAULT
    _current = system_language(reader) if _request == 'systeme' else _request
    return _current


def current_language():
    """'fr' ou 'en'."""
    global _current
    if _current is None: select_language(DEFAULT)
    return _current


def requested():
    """Le reglage choisi : 'systeme', 'en' ou 'fr'."""
    return _request


def catalog():
    """Le catalogue francais -> anglais (les fichiers de texts_en\\, charges une fois)."""
    global _catalog
    if _catalog is None:
        c = {}
        for name_str in MODULES_EN:
            c.update(importlib.import_module('dq4_pc.texts_en.' + name_str).EN)
        _catalog = c
    return _catalog


def tr(text):
    """Le texte dans la langue de l'outil (le texte francais lui-meme en francais, ou quand il n'a pas de traduction)."""
    if current_language() != 'en' or not isinstance(text, str): return text
    return catalog().get(text, text)


def N_(text):
    """Marque une constante de module a traduire au moment de l'afficher (rend le texte tel quel)."""
    return text


def read_setting(path):
    """Le reglage « langue » d'un fichier reglages.json (pour les messages de la console, avant que les reglages soient charges) ; 'systeme' si absent ou illisible."""
    try:
        import json
        with open(path, encoding='utf-8') as f: v = json.load(f).get('langue', DEFAULT)
        return v if v in CHOICES else DEFAULT
    except Exception:
        return DEFAULT
