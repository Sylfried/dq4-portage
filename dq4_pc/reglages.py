"""Reglages du joueur (menu Echap) : affichage, son, touches. Enregistres dans reglages.json (a cote de fenetre.py, ignore par git)."""
import json, os
import pyglet

# Touches par defaut : action -> [touche principale, touche secondaire] (noms pyglet.window.key)
TOUCHES_DEF = {
    'gauche': ['Q', None], 'droite': ['D', None], 'haut': ['Z', None], 'bas': ['S', None],
    'cam_gauche': ['LEFT', None], 'cam_droite': ['RIGHT', None], 'cam_haut': ['UP', None], 'cam_bas': ['DOWN', None],
    'menu': ['RETURN', None], 'discussion': ['LALT', 'RALT'], 'carte': ['M', None],
    'A': ['SPACE', None], 'B': ['BACKSPACE', None], 'courir': ['LSHIFT', 'RSHIFT'], 'courir_bascule': [None, None], 'cam_accel': ['LSHIFT', 'RSHIFT'], 'cam_accel_bascule': [None, None],
    'L': ['A', 'PAGEUP'], 'R': ['R', 'PAGEDOWN'], 'infos': ['F1', None], 'modif': ['LCTRL', 'RCTRL'],
}
# libelles des actions (menu Commandes : dans cet ordre, avec les curseurs de vitesse entre elles, voir pause.py ; L / R : pages des menus du jeu, touches fixes absentes du menu)
ACTIONS = [('haut', 'Haut'), ('bas', 'Bas'), ('gauche', 'Gauche'), ('droite', 'Droite'),
           ('courir', 'Courir (maintenir)'), ('courir_bascule', 'Courir (appuyer)'),
           ('cam_haut', 'Caméra (Haut)'), ('cam_bas', 'Caméra (Bas)'), ('cam_gauche', 'Caméra (Gauche)'), ('cam_droite', 'Caméra (Droite)'),
           ('cam_accel', 'Accélérer la caméra (maintenir)'), ('cam_accel_bascule', 'Accélérer la caméra (appuyer)'), ('modif', 'Touche spéciale'),
           ('A', 'Action'), ('menu', 'Menu'), ('B', 'Annuler/Retour'), ('carte', 'Carte'), ('discussion', 'Discussion de groupe'),
           ('infos', 'Infos à l\'écran'), ('L', 'Page précédente'), ('R', 'Page suivante')]
RESERVEES = ('ESCAPE',)                # Echap ouvre le menu : non reattribuable
PARTAGE = ('courir', 'courir_bascule', 'cam_accel', 'cam_accel_bascule')      # actions qui peuvent partager une touche (Maj : courir et accelerer la camera) ; toute autre touche ne sert qu'a une action
NOMS = {'LEFT': '←', 'RIGHT': '→', 'UP': '↑', 'DOWN': '↓', 'LSHIFT': 'Maj gauche', 'RSHIFT': 'Maj droite', 'LCTRL': 'Ctrl gauche', 'RCTRL': 'Ctrl droite',
        'LALT': 'Alt gauche', 'RALT': 'Alt droite', 'SPACE': 'Espace', 'RETURN': 'Entrée', 'ENTER': 'Entrée pavé', 'BACKSPACE': 'Retour arrière', 'TAB': 'Tab',
        'DELETE': 'Suppr', 'INSERT': 'Inser', 'HOME': 'Début', 'END': 'Fin', 'PAGEUP': 'Page haut', 'PAGEDOWN': 'Page bas', 'CAPSLOCK': 'Verr Maj',
        'COMMA': ',', 'PERIOD': '.', 'SEMICOLON': ';', 'COLON': ':', 'EXCLAMATION': '!', 'MINUS': '-', 'PLUS': '+', 'EQUAL': '=', 'SLASH': '/', 'BACKSLASH': '\\'}

DEFAUT = {
    'mode_sprites': 4,            # « Shader » : 0 originaux, 1 EPX x8, 4 pixel perfect (voir hd.py) ; 2 (regions lissees) et 3 (bicubique), retires car ils ne faisaient que flouter, valent 1 a la lecture
    'distance_camera': 100,       # distance de la camera en pourcentage (50 a 200) : villes, donjons, tours et carte du monde ; 100 = vue habituelle, 50 = deux fois plus pres, 200 = deux fois plus loin ; ne depend pas du shader
    'camera_centree': True,       # villes, donjons, tours : la camera reste centree sur le heros meme pres du bord de la carte (le jeu et la visionneuse la bornent sinon : le bord de la carte resterait hors champ)
    'lissage': True,              # agrandissement lineaire des textures (non : plus proche voisin)
    'plein_ecran': False,
    'msaa': 4,                    # anticrenelage MSAA (0, 2, 4, 8) : la scene est dessinee hors ecran (postfx.py), le changement est immediat ; limite par la carte graphique
    'echelle_rendu': 1.0,         # suréchantillonnage : la scene est dessinee a cette echelle (1 a 2) puis reduite (1 = normal ; 2 = 4 fois plus de pixels calcules, scintillement et bords en escalier tres reduits)
    'nettete': 0.0,               # 0 a 1 : accentuation adaptative des contours de la scene (0 = aucune)
    'luminosite': 1.0,            # 0,5 a 1,5 : courbe de gamma de la scene (1 = comme le jeu ; plus haut = plus clair)
    'infos': False,               # F1 : lignes d'information
    'son': True, 'volume_musique': 1.0, 'volume_bruitages': 1.0,
    'resolution': [1920, 1080],   # taille de la fenetre [largeur, hauteur] (ramenee a l'ecran si elle est trop grande) ; en plein ecran : mode d'affichage choisi
    'angle_camera': 0.0,          # degres ajoutes a l'inclinaison de la camera des villes et donjons (0 = comme le jeu) ; se regle avec les fleches haut / bas (Commandes : Camera)
    'vignette': 0.3,              # assombrissement des bords de l'image de jeu (0 = aucun, 1 = coins noirs) : donne du volume aux decors et sprites 2D, cache le fond uni hors de la carte
    'vitesse_marche': 1.0,        # facteur de vitesse du jeu quand le heros marche (0,5 a 2)
    'vitesse_camera': 1.0,        # vitesse de rotation / d'inclinaison de la camera aux fleches et du recentrage (0,5 a 2)
    'accel_camera': 1.5,          # multiplicateur de la vitesse de la camera aux fleches quand on l'accelere (1 a 2) ; accelere tant que la touche « Accélérer la caméra (maintenir) » est tenue ou apres un appui sur « (appuyer) »
    'vitesse_fondu': 2.0,         # transitions : les fondus au noir (changement de carte...) durent 1 / ce facteur de leur duree d'origine (1 = comme le jeu ; 0,5 a 2)
    'vitesse_course': 1.5,        # multiplicateur de la vitesse quand on court (1 a 2) ; on court tant que la touche « Courir (maintenir) » est tenue ou apres un appui sur « Courir (appuyer) »
    'taille_degats': 1.6,         # taille des nombres de degats sur les monstres (1 = taille de la mise en page d'origine, tres petite sur un grand ecran)
    'grille_edition': True,       # editeur d'interface : grille de placement affichee (32 x 18 cases)
    'boutons': True,              # boutons tactiles de la version mobile (Carte, Commandes, Discussion) affiches a l'ecran, hors combat
    'croix': True, 'croix_taille': 1.0,      # croix (manette tactile) a l'ecran, utilisable a la souris : affichee ou non ; taille relative (en plus de l'option « Taille de la croix » du jeu)
    'boutons_taille': 1.0, 'boutons_aimant': True,       # taille relative ; positions posees sur une grille (aimantation)
    'interface_fenetres': {},     # fenetres du jeu : nom (Make_* de MenuPortItemTable, ou 'msg' pour les dialogues) -> [taille relative, decalage x, decalage y en fraction de l'ecran] ; absent : comme le jeu (voir pause.py, editeur d'interface)
    'boutons_pos': {},            # bouton ou 'croix' -> [colonne, ligne] de son coin superieur gauche sur la grille de l'ecran (vide : positions d'origine, voir hud_mobile.py)
    'touches_v': 4,               # version des reglages : une liste de touches plus ancienne que la v3 est abandonnee (v3 : ZQSD pour marcher, fleches = camera, Espace = action) ; v3 -> v4 : Discussion de groupe = Alt / Alt Gr (si ces touches sont libres), course x1,5 (si elle etait au x2 d'origine) ; une action ajoutee depuis prend sa touche par defaut
    'touches': {k: list(v) for k, v in TOUCHES_DEF.items()},
}


MODES_SPRITES = (0, 1, 4)      # valeurs possibles de 'mode_sprites' (le 4 garde son numero : les anciens fichiers de reglages et les options --hd restent valables)
MSAA_VALEURS = (0, 2, 4, 8)


def mode_sprites_valide(v):
    """Valeur lue (ancien fichier de reglages, option --hd) -> mode existant : 2 (regions lissees) et 3 (bicubique) sont devenus 1 (EPX x8, le plus proche : meme agrandissement x8 des contours, sans le flou) ; tout le reste -> pixel perfect."""
    try: v = int(v)
    except (TypeError, ValueError): return DEFAUT['mode_sprites']
    if v in (2, 3): return 1
    return v if v in MODES_SPRITES else DEFAUT['mode_sprites']


BORNES = {'distance_camera': (50, 200), 'vitesse_marche': (0.5, 2.0), 'vitesse_camera': (0.5, 2.0), 'vitesse_fondu': (0.5, 2.0), 'vitesse_course': (1.0, 2.0), 'accel_camera': (1.0, 2.0), 'vignette': (0.0, 1.0), 'croix_taille': (0.5, 2.0), 'echelle_rendu': (1.0, 2.0), 'nettete': (0.0, 1.0), 'luminosite': (0.5, 1.5)}      # bornes des curseurs du menu Echap


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
                v_enreg = d.get('touches_v')
                for k, x in d.items():
                    if k == 'touches' and v_enreg not in (3, DEFAUT['touches_v']): continue
                    if k == 'touches' and isinstance(x, dict):
                        for a, ts in x.items():
                            if a in TOUCHES_DEF and isinstance(ts, list): self.v['touches'][a] = (list(ts) + [None, None])[:2]
                    elif k in DEFAUT and k != 'touches' and k != 'taille_degats': self.v[k] = x          # (la taille des nombres de degats n'est plus un reglage : valeur fixe)
                if v_enreg == 3:                                      # v3 -> v4 : nouvelles valeurs par defaut, sans toucher a ce que le joueur a regle lui-meme
                    ts = self.v['touches']
                    if ts['discussion'] == [None, None] and not any(n in (a for l in ts.values() for a in l) for n in ('LALT', 'RALT')): ts['discussion'] = list(TOUCHES_DEF['discussion'])
                    for a in ('modif',):
                        for i, n in enumerate(ts[a]):
                            if n and any(n in l for b, l in ts.items() if b != a): ts[a][i] = None        # une touche deja prise par une autre action lui reste
                    if self.v['vitesse_course'] == 2.0: self.v['vitesse_course'] = DEFAUT['vitesse_course']
                if d.get('accel_camera') == 2.0: self.v['accel_camera'] = DEFAUT['accel_camera']      # ancienne valeur par defaut (x2) : la nouvelle est x1,5 (plage de 1 a 2)
                if d.get('camera_maj') is False and 'cam_accel' not in (d.get('touches') or {}): self.v['touches']['cam_accel'] = [None, None]      # ancien reglage « Maj : camera plus rapide » = Non : plus de touche d'acceleration
                saved = d.get('touches') if isinstance(d.get('touches'), dict) else {}
                for a in TOUCHES_DEF:                                  # action ajoutee depuis : sa touche d'origine est abandonnee si une autre action (hors partage) l'a prise
                    if a in saved: continue
                    ts = self.v['touches']
                    for i, n in enumerate(ts[a]):
                        if n and any(n in l for b, l in ts.items() if b != a and not (a in PARTAGE and b in PARTAGE)): ts[a][i] = None
                self.v['touches_v'] = DEFAUT['touches_v']
                for k, (mi, ma) in BORNES.items(): self.v[k] = min(ma, max(mi, self.v[k])) if isinstance(self.v[k], (int, float)) else DEFAUT[k]       # valeurs d'anciennes versions ramenees aux curseurs
                self.v['mode_sprites'] = mode_sprites_valide(self.v['mode_sprites'])
                if self.v['msaa'] not in MSAA_VALEURS: self.v['msaa'] = DEFAUT['msaa']
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
        """Action liee a une touche (ou None) ; si la touche sert a plusieurs actions (Maj : courir et accelerer la camera), la premiere de la liste."""
        nom = nom_de(symbol)
        for a, ts in self.v['touches'].items():
            if nom in ts: return a
        return None

    def actions_de(self, symbol):
        """Toutes les actions liees a une touche."""
        nom = nom_de(symbol)
        return [a for a, ts in self.v['touches'].items() if nom in ts]

    def lier(self, action, colonne, symbol):
        """Lie une touche a (action, colonne 0/1) ; la touche est retiree de toute autre action. -> nom de l'action qui l'avait, ou None."""
        nom = nom_de(symbol); avait = None
        for a, ts in self.v['touches'].items():
            if action in PARTAGE and a in PARTAGE: continue                  # courir / accelerer la camera : la touche peut servir aux deux
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
                if action in PARTAGE and a in PARTAGE: continue
                for i in range(2):
                    if autres[i] == nom and (a, i) != (action, col): autres[i] = None; perdu.append(a)
            ts[action][col] = nom
        self.codes_cache = {}
        return perdu

    def est_par_defaut(self, action):
        return list(self.v['touches'][action]) == list(TOUCHES_DEF[action])

    def touches_par_defaut(self):
        self.v['touches'] = {k: list(x) for k, x in TOUCHES_DEF.items()}; self.codes_cache = {}
