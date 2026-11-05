"""Langue de l'outil (D-238) : francais ou anglais pour tout ce qui est propre au portage (parametres, historique, sauvegardes, licence, informations F1, messages de la console...).
Les textes DU JEU (dialogues, menus du jeu, noms) viennent des fichiers du jeu et ne changent pas.

Reglage « Langue » (page Affichage) : `systeme` (defaut : francais si Windows est en francais, quelle que soit la variante, sinon anglais), `en`, `fr`.

Principe : le texte source est le texte FRANCAIS ecrit dans le code ; `tr(texte)` rend le meme texte en francais, et sa traduction anglaise (`textes_en\\`) en anglais. Un texte sans traduction reste en francais (jamais d'erreur) ;
le francais reste donc identique a lui-meme par construction. Les textes a trous restent des modeles a formater APRES la traduction : `tr('%d fichier(s)') % n`.
Les constantes de module sont marquees avec `N_` (le texte est rendu tel quel, traduit a l'affichage) : `ACTIONS = (('haut', N_('Haut')), ...)` puis `tr(libelle)` au moment de dessiner."""
import importlib
import os
import sys

CHOIX = ('systeme', 'en', 'fr')                         # valeurs du reglage « Langue »
DEFAUT = 'systeme'
MODULES_EN = ('pause', 'menus', 'fenetre', 'divers')    # les fichiers de textes_en\ (chacun definit EN = {texte francais: texte anglais})
_demande = DEFAUT
_courante = None
_catalogue = None


def langue_du_systeme(lecteur=None):
    """'fr' si l'ordinateur est en francais (n'importe quelle variante : France, Belgique, Canada, Suisse...), sinon 'en'. `lecteur` : fonction sans argument qui rend la langue de l'interface (tests)."""
    code = None
    try:
        code = lecteur() if lecteur else _langue_interface()
    except Exception:
        code = None
    return 'fr' if _est_francais(code) else 'en'


def _est_francais(code):
    """`code` : identifiant Windows de langue (entier, ex. 0x040C), ou texte « fr_FR.UTF-8 » / « fr-BE » / « French_France »."""
    if code is None: return False
    if isinstance(code, int): return (code & 0x3FF) == 0x0C              # identifiant primaire 0x0C = francais (toutes les variantes)
    t = str(code).strip().lower().replace('-', '_')
    return t.startswith('fr') and (len(t) == 2 or t[2] in '_.@' or t.startswith('french'))


def _langue_interface():
    """La langue d'affichage de l'ordinateur : Windows (GetUserDefaultUILanguage), sinon les variables d'environnement, sinon la locale."""
    if sys.platform == 'win32':
        import ctypes
        return ctypes.windll.kernel32.GetUserDefaultUILanguage()
    for k in ('LC_ALL', 'LC_MESSAGES', 'LANG', 'LANGUAGE'):
        v = os.environ.get(k)
        if v: return v.split(':')[0]
    import locale
    return (locale.getlocale()[0] or '')


def regler(choix, lecteur=None):
    """Fixe la langue : `choix` parmi CHOIX (autre valeur : `systeme`). -> 'fr' ou 'en'."""
    global _demande, _courante
    _demande = choix if choix in CHOIX else DEFAUT
    _courante = langue_du_systeme(lecteur) if _demande == 'systeme' else _demande
    return _courante


def courante():
    """'fr' ou 'en'."""
    global _courante
    if _courante is None: regler(DEFAUT)
    return _courante


def demande():
    """Le reglage choisi : 'systeme', 'en' ou 'fr'."""
    return _demande


def catalogue():
    """Le catalogue francais -> anglais (les fichiers de textes_en\\, charges une fois)."""
    global _catalogue
    if _catalogue is None:
        c = {}
        for nom in MODULES_EN:
            c.update(importlib.import_module('dq4_pc.textes_en.' + nom).EN)
        _catalogue = c
    return _catalogue


def tr(texte):
    """Le texte dans la langue de l'outil (le texte francais lui-meme en francais, ou quand il n'a pas de traduction)."""
    if courante() != 'en' or not isinstance(texte, str): return texte
    return catalogue().get(texte, texte)


def N_(texte):
    """Marque une constante de module a traduire au moment de l'afficher (rend le texte tel quel)."""
    return texte


def lire_reglage(chemin):
    """Le reglage « langue » d'un fichier reglages.json (pour les messages de la console, avant que les reglages soient charges) ; 'systeme' si absent ou illisible."""
    try:
        import json
        with open(chemin, encoding='utf-8') as f: v = json.load(f).get('langue', DEFAUT)
        return v if v in CHOIX else DEFAUT
    except Exception:
        return DEFAUT
