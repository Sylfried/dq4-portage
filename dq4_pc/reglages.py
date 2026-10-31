"""Reglages du joueur (menu Echap) : affichage, son, touches. Enregistres dans reglages.json (a cote de fenetre.py, ignore par git)."""
import json, os
import pyglet

# Touches par defaut : action -> [touche principale, touche secondaire] (noms pyglet.window.key)
TOUCHES_DEF = {
    'gauche': ['Q', 'LEFT'], 'droite': ['D', 'RIGHT'], 'haut': ['Z', 'UP'], 'bas': ['S', 'DOWN'],
    'A': ['M', None], 'B': ['L', None], 'X': ['O', None], 'Y': ['K', None],
    'start': ['LSHIFT', 'RSHIFT'], 'select': ['LCTRL', 'RCTRL'],
    'L': ['A', 'I'], 'R': ['E', 'P'],
}
ACTIONS = [('haut', 'Haut'), ('bas', 'Bas'), ('gauche', 'Gauche'), ('droite', 'Droite'), ('A', 'A : valider, parler'), ('B', 'B : annuler, menu'), ('X', 'X : menu'),
           ('Y', 'Y (sans effet pour l\'instant)'), ('start', 'Start : menu'), ('select', 'Select (sans effet pour l\'instant)'), ('L', 'L : page précédente'), ('R', 'R : page suivante')]
RESERVEES = ('ESCAPE', 'F1')           # Echap ouvre le menu, F1 affiche les infos : non reattribuables
NOMS = {'LEFT': '←', 'RIGHT': '→', 'UP': '↑', 'DOWN': '↓', 'LSHIFT': 'Maj gauche', 'RSHIFT': 'Maj droite', 'LCTRL': 'Ctrl gauche', 'RCTRL': 'Ctrl droite',
        'LALT': 'Alt gauche', 'RALT': 'Alt droite', 'SPACE': 'Espace', 'RETURN': 'Entrée', 'ENTER': 'Entrée pavé', 'BACKSPACE': 'Retour arrière', 'TAB': 'Tab',
        'DELETE': 'Suppr', 'INSERT': 'Inser', 'HOME': 'Début', 'END': 'Fin', 'PAGEUP': 'Page haut', 'PAGEDOWN': 'Page bas', 'CAPSLOCK': 'Verr Maj',
        'COMMA': ',', 'PERIOD': '.', 'SEMICOLON': ';', 'COLON': ':', 'EXCLAMATION': '!', 'MINUS': '-', 'PLUS': '+', 'EQUAL': '=', 'SLASH': '/', 'BACKSLASH': '\\'}

DEFAUT = {
    'mode_sprites': 4,            # 0 originaux, 1 EPX, 2 regions lissees, 3 bicubique, 4 pixel perfect (voir hd.py)
    'echelle_pp': 0,              # pixel perfect sur la carte du monde : 0 = automatique (selon la taille de la fenetre), sinon 1, 2, 4 ou 8
    'lissage': True,              # agrandissement lineaire des textures (non : plus proche voisin)
    'zoom_carte': 1.0,            # zoom de la carte du monde (1 = heros a la taille des villes)
    'plein_ecran': False,
    'msaa': 4,                    # anticrenelage materiel (pris en compte au prochain lancement)
    'infos': False,               # F1 : lignes d'information
    'son': True, 'volume_musique': 0.7, 'volume_bruitages': 0.8,
    'touches': {k: list(v) for k, v in TOUCHES_DEF.items()},
}


def nom_touche(nom):
    """Nom lisible d'une touche (nom pyglet) pour le menu."""
    if not nom: return '—'
    return NOMS.get(nom, nom.replace('NUM_', 'Pavé ') if nom.startswith('NUM_') else (nom[1:] if nom.startswith('_') and nom[1:].isdigit() else nom))


def symbole(nom):
    """Nom pyglet -> code de touche (None si inconnu)."""
    return getattr(pyglet.window.key, nom, None) if nom else None


def nom_de(symbol):
    """Code de touche -> nom pyglet."""
    return pyglet.window.key.symbol_string(symbol)


class Reglages:
    def __init__(self, chemin=None):
        self.chemin = chemin; self.v = json.loads(json.dumps(DEFAUT))
        if chemin and os.path.exists(chemin):
            try:
                with open(chemin, encoding='utf-8') as f: d = json.load(f)
                for k, x in d.items():
                    if k == 'touches' and isinstance(x, dict):
                        for a, ts in x.items():
                            if a in TOUCHES_DEF and isinstance(ts, list): self.v['touches'][a] = (list(ts) + [None, None])[:2]
                    elif k in DEFAUT and k != 'touches': self.v[k] = x
            except Exception as ex:
                print('Reglages illisibles (%s) : valeurs par defaut (%r)' % (chemin, ex), flush=True)
        self.codes_cache = {}

    def __getitem__(self, k): return self.v[k]

    def __setitem__(self, k, x):
        self.v[k] = x; self.codes_cache = {}

    def enregistrer(self):
        if not self.chemin: return
        try:
            tmp = self.chemin + '.tmp'
            with open(tmp, 'w', encoding='utf-8') as f: json.dump(self.v, f, indent=1, ensure_ascii=False)
            os.replace(tmp, self.chemin)
        except Exception as ex:
            print('Reglages non enregistres :', ex, flush=True)

    # ---- touches
    def codes(self, action):
        """Codes pyglet des touches d'une action."""
        c = self.codes_cache.get(action)
        if c is None:
            c = self.codes_cache[action] = tuple(s for s in (symbole(n) for n in self.v['touches'][action]) if s is not None)
        return c

    def action_de(self, symbol):
        """Action liee a une touche (ou None)."""
        nom = nom_de(symbol)
        for a, ts in self.v['touches'].items():
            if nom in ts: return a
        return None

    def lier(self, action, colonne, symbol):
        """Lie une touche a (action, colonne 0/1) ; la touche est retiree de toute autre action. -> nom de l'action qui l'avait, ou None."""
        nom = nom_de(symbol); avait = None
        for a, ts in self.v['touches'].items():
            for i in range(2):
                if ts[i] == nom and (a, i) != (action, colonne): ts[i] = None; avait = a
        self.v['touches'][action][colonne] = nom; self.codes_cache = {}
        return avait

    def delier(self, action, colonne):
        self.v['touches'][action][colonne] = None; self.codes_cache = {}

    def touches_par_defaut(self):
        self.v['touches'] = {k: list(x) for k, x in TOUCHES_DEF.items()}; self.codes_cache = {}
