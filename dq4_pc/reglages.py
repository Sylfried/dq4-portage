"""Reglages du joueur (menu Echap) : affichage, son, touches. Enregistres dans reglages.json (a cote de fenetre.py, ignore par git)."""
import json, os
import pyglet

# Touches par defaut : action -> [touche principale, touche secondaire] (noms pyglet.window.key)
TOUCHES_DEF = {
    'gauche': ['Q', None], 'droite': ['D', None], 'haut': ['Z', None], 'bas': ['S', None],
    'cam_gauche': ['LEFT', None], 'cam_droite': ['RIGHT', None], 'cam_haut': ['UP', None], 'cam_bas': ['DOWN', None],
    'menu': ['RETURN', None], 'discussion': [None, None], 'carte': ['M', None],
    'A': ['SPACE', None], 'B': ['BACKSPACE', None], 'courir': ['LSHIFT', 'RSHIFT'],
    'L': ['A', 'PAGEUP'], 'R': ['R', 'PAGEDOWN'], 'infos': ['F1', None],
}
ACTIONS = [('haut', 'Haut'), ('bas', 'Bas'), ('gauche', 'Gauche'), ('droite', 'Droite'),
           ('cam_gauche', 'Caméra : tourner à gauche'), ('cam_droite', 'Caméra : tourner à droite'), ('cam_haut', 'Caméra : relever l\'angle'), ('cam_bas', 'Caméra : abaisser l\'angle'),
           ('A', 'Action (parler, examiner, ouvrir, valider)'), ('menu', 'Menu de commandes (valider dans un menu)'), ('B', 'Annuler / retour'), ('carte', 'Carte'), ('discussion', 'Discussion de groupe'),
           ('courir', 'Courir (maintenir)'), ('L', 'Page précédente'), ('R', 'Page suivante'),
           ('infos', 'Afficher les infos à l\'écran')]
RESERVEES = ('ESCAPE',)                # Echap ouvre le menu : non reattribuable
NOMS = {'LEFT': '←', 'RIGHT': '→', 'UP': '↑', 'DOWN': '↓', 'LSHIFT': 'Maj gauche', 'RSHIFT': 'Maj droite', 'LCTRL': 'Ctrl gauche', 'RCTRL': 'Ctrl droite',
        'LALT': 'Alt gauche', 'RALT': 'Alt droite', 'SPACE': 'Espace', 'RETURN': 'Entrée', 'ENTER': 'Entrée pavé', 'BACKSPACE': 'Retour arrière', 'TAB': 'Tab',
        'DELETE': 'Suppr', 'INSERT': 'Inser', 'HOME': 'Début', 'END': 'Fin', 'PAGEUP': 'Page haut', 'PAGEDOWN': 'Page bas', 'CAPSLOCK': 'Verr Maj',
        'COMMA': ',', 'PERIOD': '.', 'SEMICOLON': ';', 'COLON': ':', 'EXCLAMATION': '!', 'MINUS': '-', 'PLUS': '+', 'EQUAL': '=', 'SLASH': '/', 'BACKSLASH': '\\'}

DEFAUT = {
    'mode_sprites': 4,            # 0 originaux, 1 EPX, 2 regions lissees, 3 bicubique, 4 pixel perfect (voir hd.py)
    'zoom': 100,                  # zoom en pourcentage (40 a 400) : villes, donjons, tours et carte du monde ; 100 = vue habituelle ; ne depend pas du shader
    'lissage': True,              # agrandissement lineaire des textures (non : plus proche voisin)
    'plein_ecran': False,
    'msaa': 4,                    # anticrenelage materiel (pris en compte au prochain lancement)
    'infos': False,               # F1 : lignes d'information
    'son': True, 'volume_musique': 1.0, 'volume_bruitages': 1.0,
    'resolution': [1920, 1080],   # taille de la fenetre [largeur, hauteur] (ramenee a l'ecran si elle est trop grande) ; en plein ecran : mode d'affichage choisi
    'angle_camera': 0.0,          # degres ajoutes a l'inclinaison de la camera des villes et donjons (0 = comme le jeu) ; se regle avec les fleches haut / bas (Commandes : Camera)
    'vignette': 0.3,              # assombrissement des bords de l'image de jeu (0 = aucun, 1 = coins noirs) : donne du volume aux decors et sprites 2D, cache le fond uni hors de la carte
    'vitesse_marche': 1.0,        # facteur de vitesse du jeu quand le heros marche
    'vitesse_fondu': 2.0,         # transitions : les fondus au noir (changement de carte...) durent 1 / ce facteur de leur duree d'origine (1 = comme le jeu)
    'course': True, 'vitesse_course': 2.0,     # course : touche maintenue (action « courir »), facteur de vitesse
    'taille_degats': 1.6,         # taille des nombres de degats sur les monstres (1 = taille de la mise en page d'origine, tres petite sur un grand ecran)
    'boutons': True,              # boutons tactiles de la version mobile (Carte, Commandes, Discussion) affiches a l'ecran, hors combat
    'boutons_taille': 1.0, 'boutons_aimant': True,       # taille relative ; positions posees sur une grille (aimantation)
    'boutons_pos': {},            # bouton -> [colonne, ligne] de son coin superieur gauche sur la grille de l'ecran (vide : positions d'origine, voir hud_mobile.py)
    'touches_v': 3,               # version des touches par defaut : une liste enregistree plus ancienne est abandonnee (v3 : ZQSD pour marcher, fleches = camera, Espace = action)
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
                    if k == 'touches' and d.get('touches_v') != DEFAUT['touches_v']: continue
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
