"""Reglages du joueur (menu Echap) : affichage, son, touches. Enregistres dans reglages.json (a cote de fenetre.py, ignore par git)."""
import json, os
import pyglet

# Touches par defaut : action -> [touche principale, touche secondaire] (noms pyglet.window.key)
TOUCHES_DEF = {
    'gauche': ['Q', None], 'droite': ['D', None], 'haut': ['Z', None], 'bas': ['S', None],
    'cam_gauche': ['LEFT', None], 'cam_droite': ['RIGHT', None], 'cam_haut': ['UP', None], 'cam_bas': ['DOWN', None],
    'menu': ['RETURN', None], 'discussion': [None, None], 'carte': ['M', None],
    'A': ['SPACE', None], 'B': ['BACKSPACE', None], 'courir': ['LSHIFT', 'RSHIFT'], 'courir_bascule': [None, None],
    'L': ['A', 'PAGEUP'], 'R': ['R', 'PAGEDOWN'], 'infos': ['F1', None],
}
# libelles des actions (menu Commandes : dans cet ordre, avec les curseurs de vitesse entre elles, voir pause.py ; L / R : pages des menus du jeu, touches fixes absentes du menu)
ACTIONS = [('haut', 'Haut'), ('bas', 'Bas'), ('gauche', 'Gauche'), ('droite', 'Droite'),
           ('courir', 'Courir (maintenir)'), ('courir_bascule', 'Courir (appuyer)'),
           ('cam_haut', 'Caméra (Haut)'), ('cam_bas', 'Caméra (Bas)'), ('cam_gauche', 'Caméra (Gauche)'), ('cam_droite', 'Caméra (Droite)'),
           ('A', 'Action'), ('menu', 'Menu'), ('B', 'Annuler/Retour'), ('carte', 'Carte'), ('discussion', 'Discussion de groupe'),
           ('infos', 'Infos à l\'écran'), ('L', 'Page précédente'), ('R', 'Page suivante')]
RESERVEES = ('ESCAPE',)                # Echap ouvre le menu : non reattribuable
NOMS = {'LEFT': '←', 'RIGHT': '→', 'UP': '↑', 'DOWN': '↓', 'LSHIFT': 'Maj gauche', 'RSHIFT': 'Maj droite', 'LCTRL': 'Ctrl gauche', 'RCTRL': 'Ctrl droite',
        'LALT': 'Alt gauche', 'RALT': 'Alt droite', 'SPACE': 'Espace', 'RETURN': 'Entrée', 'ENTER': 'Entrée pavé', 'BACKSPACE': 'Retour arrière', 'TAB': 'Tab',
        'DELETE': 'Suppr', 'INSERT': 'Inser', 'HOME': 'Début', 'END': 'Fin', 'PAGEUP': 'Page haut', 'PAGEDOWN': 'Page bas', 'CAPSLOCK': 'Verr Maj',
        'COMMA': ',', 'PERIOD': '.', 'SEMICOLON': ';', 'COLON': ':', 'EXCLAMATION': '!', 'MINUS': '-', 'PLUS': '+', 'EQUAL': '=', 'SLASH': '/', 'BACKSLASH': '\\'}

DEFAUT = {
    'mode_sprites': 4,            # 0 originaux, 1 EPX, 2 regions lissees, 3 bicubique, 4 pixel perfect (voir hd.py)
    'distance_camera': 100,       # distance de la camera en pourcentage (50 a 200) : villes, donjons, tours et carte du monde ; 100 = vue habituelle, 50 = deux fois plus pres, 200 = deux fois plus loin ; ne depend pas du shader
    'lissage': True,              # agrandissement lineaire des textures (non : plus proche voisin)
    'plein_ecran': False,
    'msaa': 4,                    # anticrenelage materiel (pris en compte au prochain lancement)
    'infos': False,               # F1 : lignes d'information
    'son': True, 'volume_musique': 1.0, 'volume_bruitages': 1.0,
    'resolution': [1920, 1080],   # taille de la fenetre [largeur, hauteur] (ramenee a l'ecran si elle est trop grande) ; en plein ecran : mode d'affichage choisi
    'angle_camera': 0.0,          # degres ajoutes a l'inclinaison de la camera des villes et donjons (0 = comme le jeu) ; se regle avec les fleches haut / bas (Commandes : Camera)
    'vignette': 0.3,              # assombrissement des bords de l'image de jeu (0 = aucun, 1 = coins noirs) : donne du volume aux decors et sprites 2D, cache le fond uni hors de la carte
    'vitesse_marche': 1.0,        # facteur de vitesse du jeu quand le heros marche (0,5 a 2)
    'vitesse_camera': 1.0,        # vitesse de rotation / d'inclinaison de la camera aux fleches et du recentrage (0,5 a 2)
    'vitesse_fondu': 2.0,         # transitions : les fondus au noir (changement de carte...) durent 1 / ce facteur de leur duree d'origine (1 = comme le jeu ; 0,5 a 2)
    'vitesse_course': 2.0,        # multiplicateur de la vitesse quand on court (1 a 2) ; on court tant que la touche « Courir (maintenir) » est tenue ou apres un appui sur « Courir (appuyer) »
    'taille_degats': 1.6,         # taille des nombres de degats sur les monstres (1 = taille de la mise en page d'origine, tres petite sur un grand ecran)
    'boutons': True,              # boutons tactiles de la version mobile (Carte, Commandes, Discussion) affiches a l'ecran, hors combat
    'boutons_taille': 1.0, 'boutons_aimant': True,       # taille relative ; positions posees sur une grille (aimantation)
    'boutons_pos': {},            # bouton -> [colonne, ligne] de son coin superieur gauche sur la grille de l'ecran (vide : positions d'origine, voir hud_mobile.py)
    'touches_v': 3,               # version des touches par defaut : une liste enregistree plus ancienne est abandonnee (v3 : ZQSD pour marcher, fleches = camera, Espace = action) ; une action ajoutee depuis (Courir (appuyer)) prend sa touche par defaut
    'touches': {k: list(v) for k, v in TOUCHES_DEF.items()},
}


BORNES = {'distance_camera': (50, 200), 'vitesse_marche': (0.5, 2.0), 'vitesse_camera': (0.5, 2.0), 'vitesse_fondu': (0.5, 2.0), 'vitesse_course': (1.0, 2.0), 'vignette': (0.0, 1.0)}      # bornes des curseurs du menu Echap


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
                if 'distance_camera' not in d and isinstance(d.get('zoom'), (int, float)) and d['zoom'] > 0: d['distance_camera'] = min(200, max(50, round(10000.0 / d['zoom'])))      # ancien reglage « Zoom » (40 a 400 %) -> distance de la camera
                for k, x in d.items():
                    if k == 'touches' and d.get('touches_v') != DEFAUT['touches_v']: continue
                    if k == 'touches' and isinstance(x, dict):
                        for a, ts in x.items():
                            if a in TOUCHES_DEF and isinstance(ts, list): self.v['touches'][a] = (list(ts) + [None, None])[:2]
                    elif k in DEFAUT and k != 'touches' and k != 'taille_degats': self.v[k] = x          # (la taille des nombres de degats n'est plus un reglage : valeur fixe)
                for k, (mi, ma) in BORNES.items(): self.v[k] = min(ma, max(mi, self.v[k])) if isinstance(self.v[k], (int, float)) else DEFAUT[k]       # valeurs d'anciennes versions ramenees aux curseurs
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

    def action_par_defaut(self, action):
        """Remet les touches d'une action a leurs valeurs d'origine (une touche d'origine prise depuis par une autre action lui est retiree). -> noms des actions qui l'ont perdue."""
        perdu = []; ts = self.v['touches']; ts[action] = [None, None]
        for col, nom in enumerate(TOUCHES_DEF[action]):
            if not nom: continue
            for a, autres in ts.items():
                for i in range(2):
                    if autres[i] == nom and (a, i) != (action, col): autres[i] = None; perdu.append(a)
            ts[action][col] = nom
        self.codes_cache = {}
        return perdu

    def est_par_defaut(self, action):
        return list(self.v['touches'][action]) == list(TOUCHES_DEF[action])

    def touches_par_defaut(self):
        self.v['touches'] = {k: list(x) for k, x in TOUCHES_DEF.items()}; self.codes_cache = {}
