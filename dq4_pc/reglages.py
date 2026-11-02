"""Reglages du joueur (menu Echap) : affichage, son, touches. Enregistres dans reglages.json (a cote de fenetre.py, ignore par git)."""
import json, os
import pyglet

# Touches par defaut : action -> [touche principale, touche secondaire] (noms pyglet.window.key)
TOUCHES_DEF = {
    'gauche': ['Q', None], 'droite': ['D', None], 'haut': ['Z', None], 'bas': ['S', None],
    'cam_gauche': ['LEFT', None], 'cam_droite': ['RIGHT', None], 'cam_haut': ['UP', None], 'cam_bas': ['DOWN', None],
    'menu': ['RETURN', None], 'discussion': ['LALT', 'RALT'], 'carte': ['M', None],
    'A': ['SPACE', None], 'B': ['BACKSPACE', None], 'accel': ['LSHIFT', 'RSHIFT'],
    'L': ['A', 'PAGEUP'], 'R': ['R', 'PAGEDOWN'], 'infos': ['F1', None], 'modif': ['LCTRL', 'RCTRL'],
    'vit_combat': ['V', None],        # fait defiler la vitesse des combats (Normal, Rapide, Tres rapide) : en combat comme ailleurs ; V = « vitesse » (libre : ni ZQSD, ni fleches, ni F1, ni les chiffres des etats)
}
# libelles des actions (menu Commandes : la page range les lignes par sections, voir pause.py ; L / R : pages des menus du jeu, touches fixes absentes du menu)
ACTIONS = [('haut', 'Haut'), ('bas', 'Bas'), ('gauche', 'Gauche'), ('droite', 'Droite'),
           ('cam_haut', 'Caméra (Haut)'), ('cam_bas', 'Caméra (Bas)'), ('cam_gauche', 'Caméra (Gauche)'), ('cam_droite', 'Caméra (Droite)'),
           ('accel', "Touche d'accélérateur"), ('vit_combat', 'Touche de vitesse des combats'), ('modif', 'Touche spéciale'),
           ('A', 'Action'), ('menu', 'Menu'), ('B', 'Annuler/Retour'), ('carte', 'Carte'), ('discussion', 'Discussion de groupe'),
           ('infos', 'Infos à l\'écran'), ('L', 'Page précédente'), ('R', 'Page suivante')]
RESERVEES = ('ESCAPE', 'F11')          # Echap ouvre le menu, F11 bascule le plein ecran exclusif (avec Alt + Entree) : non reattribuables
NOMS = {'LEFT': '←', 'RIGHT': '→', 'UP': '↑', 'DOWN': '↓', 'LSHIFT': 'Maj gauche', 'RSHIFT': 'Maj droite', 'LCTRL': 'Ctrl gauche', 'RCTRL': 'Ctrl droite',
        'LALT': 'Alt gauche', 'RALT': 'Alt droite', 'SPACE': 'Espace', 'RETURN': 'Entrée', 'ENTER': 'Entrée pavé', 'BACKSPACE': 'Retour arrière', 'TAB': 'Tab',
        'DELETE': 'Suppr', 'INSERT': 'Inser', 'HOME': 'Début', 'END': 'Fin', 'PAGEUP': 'Page haut', 'PAGEDOWN': 'Page bas', 'CAPSLOCK': 'Verr Maj',
        'COMMA': ',', 'PERIOD': '.', 'SEMICOLON': ';', 'COLON': ':', 'EXCLAMATION': '!', 'MINUS': '-', 'PLUS': '+', 'EQUAL': '=', 'SLASH': '/', 'BACKSLASH': '\\'}

DEFAUT = {
    'mode_sprites': 4,            # « Shader » : 0 originaux, 1 EPX x8, 4 pixel perfect (voir hd.py) ; 2 (regions lissees) et 3 (bicubique), retires car ils ne faisaient que flouter, valent 1 a la lecture
    'distance_camera': 100,       # distance de la camera en pourcentage (50 a 200) : villes, donjons, tours et carte du monde ; 100 = vue habituelle, 50 = deux fois plus pres, 200 = deux fois plus loin ; ne depend pas du shader
    'camera_centree': True,       # villes, donjons, tours : la camera reste centree sur le heros meme pres du bord de la carte (le jeu et la visionneuse la bornent sinon : le bord de la carte resterait hors champ)
    'lissage': True,              # agrandissement lineaire des textures (non : plus proche voisin)
    'mode_fenetre': 0,            # fenetre : 0 fenetre, 1 plein ecran (fenetre sans bordure a la resolution du bureau, l'affichage du moniteur ne change pas : le plein ecran d'avant, ex-booleen « plein_ecran »), 2 plein ecran exclusif (le moniteur passe a la resolution du reglage « resolution ») ; F11 / Alt + Entree : bascule vers 2, puis retour
    'mode_fenetre_retour': 0,     # dernier mode non exclusif (0 ou 1) : F11 / Alt + Entree depuis le plein ecran exclusif y revient
    'correction_bords': True,     # villes, donjons, tours : les personnages ne penchent plus vers l'exterieur pres des bords gauche / droit de l'ecran (1 / True = corrige, 0 / False = comme avant ; une valeur entre 0 et 1 = correction partielle ; voir Jeu._panneau_ville)
    'msaa': 4,                    # anticrenelage MSAA (0, 2, 4, 8) : la scene est dessinee hors ecran (postfx.py), le changement est immediat ; limite par la carte graphique
    'echelle_rendu': 1.0,         # suréchantillonnage : la scene est dessinee a cette echelle (1 a 2) puis reduite (1 = normal ; 2 = 4 fois plus de pixels calcules, scintillement et bords en escalier tres reduits)
    'nettete': 0.0,               # 0 a 1 : accentuation adaptative des contours de la scene (0 = aucune)
    'luminosite': 1.0,            # 0,5 a 1,5 : courbe de gamma de la scene (1 = comme le jeu ; plus haut = plus clair)
    'infos': False,               # F1 : lignes d'information
    'son': True, 'volume_musique': 1.0, 'volume_bruitages': 1.0,
    'volume_general': 1.0, 'volume_jingles': 1.0, 'volume_interface': 1.0,      # son : volume general, des jingles et fanfares, des sons de l'interface (categories : voir son.py ; « bruitages » = les effets sonores du jeu)
    'musique_active': True, 'jingles_actifs': True, 'bruitages_actifs': True, 'interface_active': True,       # interrupteurs par categorie
    'vitesse_texte': 4.0,         # dialogues : lettres affichees par image du moteur (30 par seconde) ; 4 = comme le jeu (voir VITESSES_TEXTE)
    'defilement_force': False,    # combats : impose le defilement ci-dessous (non : celui de la sauvegarde, regle dans la fenetre Parametres du jeu)
    'defilement_combat': 2,       # combats, « Messages en combat » : OptionStatus.battleSpeed impose si 'defilement_force' ; 0 Rapide (attente de 12 images), 2 Moyen (32 images, la valeur d'origine du jeu), 3 Lent (42 images), 4 Manuel (touche) ; voir CRANS_DEFILEMENT
    'resolution': [1920, 1080],   # fenetre : taille de la fenetre [largeur, hauteur] (ramenee a l'ecran si elle est trop grande) ; plein ecran exclusif : mode d'affichage du moniteur ; plein ecran : sans effet (resolution du bureau)
    'angle_camera': 0.0,          # degres ajoutes a l'inclinaison de la camera des villes et donjons (0 = comme le jeu) ; se regle avec les fleches haut / bas (Commandes : Camera)
    'vignette': 0.3,              # assombrissement des bords de l'image de jeu (0 = aucun, 1 = coins noirs) : donne du volume aux decors et sprites 2D, cache le fond uni hors de la carte
    'vitesse_marche': 1.0,        # facteur de vitesse du jeu quand le heros marche : x1, x2, x3 ou x4 (VITESSES_X)
    'vitesse_camera': 1.0,        # vitesse de rotation / d'inclinaison de la camera aux fleches et du recentrage : x1 a x4
    'vitesse_fondu': 2.0,         # transitions : les fondus au noir (changement de carte...) durent 1 / ce facteur de leur duree d'origine (x1 = comme le jeu ; x1 a x4)
    'vitesse_accel': 1.5,         # « Multiplicateur de l'accélérateur » (1 a 2) : multiplicateur de la marche (on court) et de la rotation / inclinaison de la camera aux fleches tant que la « Touche d'accélérateur » est tenue (ex-« vitesse_course ») ; ne s'applique JAMAIS aux combats (voir vitesse_combat)
    'vitesse_combat': 1.0,        # « Vitesse des combats » : 1 Normal, 2 Rapide, 3 Tres rapide (VITESSES_COMBAT) : le moteur fait 1, 2 ou 3 fois plus de pas par seconde pendant un combat (animations, deplacements, delais, messages, fondus) ; la musique et les bruitages gardent leur vitesse (voir vitesse_combat.py)
    'taille_degats': 1.6,         # taille des nombres de degats sur les monstres (1 = taille de la mise en page d'origine, tres petite sur un grand ecran)
    'grille_edition': True,       # editeur d'interface : grille de placement affichee (32 x 18 cases)
    'boutons': True,              # boutons tactiles de la version mobile (Carte, Commandes, Discussion) affiches a l'ecran, hors combat
    'croix': True, 'croix_taille': 1.0,      # croix (manette tactile) a l'ecran, utilisable a la souris : affichee ou non ; taille relative (en plus de l'option « Taille de la croix » du jeu)
    'boutons_taille': 1.0, 'boutons_aimant': True,       # taille relative ; positions posees sur une grille (aimantation)
    'interface_fenetres': {},     # fenetres du jeu : nom (Make_* de MenuPortItemTable, ou 'msg' pour les dialogues) -> [taille relative, decalage x, decalage y en fraction de l'ecran] ; absent : comme le jeu (voir pause.py, editeur d'interface)
    'boutons_pos': {},            # bouton ou 'croix' -> [colonne, ligne] de son coin superieur gauche sur la grille de l'ecran (vide : positions d'origine, voir hud_mobile.py)
    'interface_masquees': [],     # editeur d'interface, « Afficher cette interface a l'ecran » = Non : noms des fenetres du jeu (Make_*, ou 'msg' pour les dialogues) qui ne sont pas dessinees ; pour les boutons et la croix de l'ecran, c'est le reglage 'boutons'
    'touches_v': 4,               # version des reglages : une liste de touches plus ancienne que la v3 est abandonnee (v3 : ZQSD pour marcher, fleches = camera, Espace = action) ; v3 -> v4 : Discussion de groupe = Alt / Alt Gr (si ces touches sont libres), accelerateur x1,5 (si la course etait au x2 d'origine) ; une action ajoutee depuis prend sa touche par defaut
    'touches': {k: list(v) for k, v in TOUCHES_DEF.items()},
}


# Fenetres du jeu absentes de l'editeur d'interface (pause.py) : lancement du jeu (menu de depart, nom, titre, licence, reseau : gerees a part), sans maillage (rien a regler), sans objet sur PC
# ou qui suivent les monstres a l'ecran. Leurs reglages enregistres par une ancienne version sont abandonnes au chargement (ils decalaient un texte seul ou une fenetre du lancement).
FENETRES_RETIREES = ('StartMenuFirst', 'StartMenuSecond', 'StartMenuSelect', 'StartNameEntry', 'SaveOverwrite', 'TitleTouch', 'PortalButton', 'NetworkRoot', 'NetworkPLST', 'NetworkCODE', 'NetworkITEM',
                     'ViewVolumeDecision', 'License', 'MagicInfo', 'Config', 'NENE_ItemView', 'MonsterName', 'BattleHoppingNumber')

# Editeur d'interface (pause.py : Affichage > Interface) : classement des reglages et remises a zero. Toute cle de DEFAUT qui touche l'interface doit figurer dans l'un de ces trois groupes
# (outils/test_reglages_interface.py le verifie : une cle ajoutee sans classement fait echouer le test).
CIBLE_ECRAN = 'boutons'                                    # « Boutons et croix de l'ecran » : l'une des interfaces de l'editeur (les autres : 'msg' et les fenetres du jeu, par leur nom Make_*)
CLES_ECRAN = ('boutons', 'croix', 'croix_taille', 'boutons_taille', 'boutons_pos')      # reglages de CIBLE_ECRAN : affichage des boutons et de la croix, tailles, positions
CLES_FENETRES = ('interface_fenetres', 'interface_masquees')                       # reglages par fenetre du jeu (ou 'msg') : taille et position, affichage
CLES_EDITEUR = ('grille_edition', 'boutons_aimant')                                # options de l'editeur lui-meme, communes a toutes les interfaces : grille affichee, aimantation
CLES_INTERFACE = CLES_ECRAN + CLES_FENETRES + CLES_EDITEUR
FENETRE_DEFAUT = (1.0, 0.0, 0.0)                           # fenetre du jeu sans reglage enregistre : taille relative, decalage x, decalage y (fractions de l'ecran)

MODES_FENETRE = (0, 1, 2)      # valeurs possibles de 'mode_fenetre' : fenetre, plein ecran (sans bordure), plein ecran exclusif
NOMS_MODES_FENETRE = {0: 'Fenêtré', 1: 'Plein écran', 2: 'Plein écran exclusif'}
MODES_SPRITES = (0, 1, 4)      # valeurs possibles de 'mode_sprites' (le 4 garde son numero : les anciens fichiers de reglages et les options --hd restent valables)
MSAA_VALEURS = (0, 2, 4, 8)


def mode_sprites_valide(v):
    """Valeur lue (ancien fichier de reglages, option --hd) -> mode existant : 2 (regions lissees) et 3 (bicubique) sont devenus 1 (EPX x8, le plus proche : meme agrandissement x8 des contours, sans le flou) ; tout le reste -> pixel perfect."""
    try: v = int(v)
    except (TypeError, ValueError): return DEFAUT['mode_sprites']
    if v in (2, 3): return 1
    return v if v in MODES_SPRITES else DEFAUT['mode_sprites']


def mode_fenetre_valide(v):
    """Valeur lue (reglages.json, option --plein-ecran) -> 0, 1 ou 2. Un booleen est l'ancien reglage « plein_ecran » (vrai = 1 : plein ecran sans bordure, le comportement qu'il avait) ; tout ce qui est invalide -> fenetre."""
    if isinstance(v, bool): return 1 if v else 0
    try: n = int(v)
    except (TypeError, ValueError, OverflowError): return DEFAUT['mode_fenetre']
    return n if n in MODES_FENETRE and n == v else DEFAUT['mode_fenetre']


BORNES = {'distance_camera': (50, 200), 'vitesse_marche': (1.0, 4.0), 'vitesse_camera': (1.0, 4.0), 'vitesse_fondu': (1.0, 4.0), 'vitesse_accel': (1.0, 2.0), 'vignette': (0.0, 1.0), 'croix_taille': (0.5, 2.0)}      # bornes des curseurs du menu Echap
BORNES.update({'echelle_rendu': (1.0, 2.0), 'nettete': (0.0, 1.0), 'luminosite': (0.5, 1.5)})
BORNES.update({'volume_musique': (0.0, 1.0), 'volume_bruitages': (0.0, 1.0), 'volume_general': (0.0, 1.0), 'volume_jingles': (0.0, 1.0), 'volume_interface': (0.0, 1.0), 'vitesse_texte': (0.25, 4000.0)})
BOOLEENS_SON_TEXTE = ('musique_active', 'jingles_actifs', 'bruitages_actifs', 'interface_active', 'defilement_force')
VITESSES_TEXTE = (0.5, 1.0, 2.0, 4.0, 8.0, 16.0, 4000.0)     # crans de la vitesse du texte (lettres par image) ; 4 = le jeu, 4000 = tout d'un coup
VITESSES_X = (1.0, 2.0, 3.0, 4.0)                            # crans de la vitesse de marche, de la camera et des transitions (x1 = comme le jeu)
VITESSES_X_CLES = ('vitesse_marche', 'vitesse_camera', 'vitesse_fondu')
VITESSES_COMBAT = (1.0, 2.0, 3.0)                            # crans de « Vitesse des combats » (x1 = comme le jeu)
NOMS_VITESSE_COMBAT = {1.0: 'Normal', 2.0: 'Rapide', 3.0: 'Très rapide'}      # libelles montres au joueur (page Commandes, bouton de l'ecran de combat) : jamais « x1 », « x2 », « x3 »
# « Messages en combat » : OptionStatus.battleSpeed (g_Option + 5, valeur d'origine 2 : OptionStatus::initialize) ; BattleAutoFeed::setMessageSpeed : 0 / 1 / 2 / 3 = attente de 12 / 22 / 32 / 42 images (0,4 / 0,73 / 1,07 / 1,4 s) avant le message suivant, 4 = pas
# d'avance automatique (touche). Le jeu d'origine propose ces cinq crans (« Vitesse texte » 1 a 5) ; la page en garde quatre : Rapide (0), Moyen (2 : la valeur d'origine), Lent (3), Manuel (4). Le cran 1 (22 images) n'a pas de nom : il
# s'affiche comme Moyen (le plus proche en rapport de durees : 22 / 12 = 1,8 contre 32 / 22 = 1,45), et reste tel quel dans la sauvegarde tant qu'on ne touche pas au reglage.
CRANS_DEFILEMENT = (0, 2, 3, 4)
COMBAT_MANUEL = 4


def cran_defilement(code):
    """Valeur de OptionStatus.battleSpeed (0 a 4) -> le cran de CRANS_DEFILEMENT qui la represente (1 -> 2) ; toute autre valeur -> celle d'origine."""
    try: code = int(code)
    except (TypeError, ValueError): return DEFAUT['defilement_combat']
    if code == 1: return 2
    return code if code in CRANS_DEFILEMENT else DEFAUT['defilement_combat']


def cran_x(v, defaut=1.0):
    """Vitesse lue (ancien curseur de 0,5 a 2 ou valeur absurde) -> le cran x1 a x4 le plus proche (a egalite le plus rapide), jamais moins que x1."""
    if isinstance(v, bool) or not isinstance(v, (int, float)): return defaut
    return float(min(VITESSES_X[-1], max(VITESSES_X[0], int(v + 0.5))))


def cran_combat(v, defaut=1.0):
    """Valeur lue (reglages.json, saisie) -> le cran de VITESSES_COMBAT le plus proche (a egalite le plus rapide) ; tout ce qui n'est pas un nombre (texte, booleen, None, nan) -> `defaut`."""
    if isinstance(v, bool) or not isinstance(v, (int, float)) or v != v: return defaut
    v = min(VITESSES_COMBAT[-1], max(VITESSES_COMBAT[0], v))                                  # (bornes : jamais plus lent que Normal, ni plus rapide que Très rapide)
    return min(VITESSES_COMBAT, key=lambda c: (abs(c - v), -c))


def combat_suivant(v):
    """Touche « Vitesse des combats » : Normal -> Rapide -> Très rapide -> Normal (une valeur invalide est lue comme Normal, une valeur hors bornes comme le cran le plus proche)."""
    v = cran_combat(v)
    return VITESSES_COMBAT[(VITESSES_COMBAT.index(v) + 1) % len(VITESSES_COMBAT)]


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
                if 'mode_fenetre' not in d and 'plein_ecran' in d: d['mode_fenetre'] = d['plein_ecran']      # ancien reglage « Plein écran » (booleen) -> mode 1 (plein ecran sans bordure, comme avant) ou 0 ; le booleen n'est plus enregistre
                if 'distance_camera' not in d and isinstance(d.get('zoom'), (int, float)) and d['zoom'] > 0: d['distance_camera'] = min(200, max(50, round(10000.0 / d['zoom'])))      # ancien reglage « Zoom » (40 a 400 %) -> distance de la camera
                if 'vitesse_accel' not in d and isinstance(d.get('vitesse_course'), (int, float)) and not isinstance(d.get('vitesse_course'), bool): d['vitesse_accel'] = d['vitesse_course']      # ancien « Multiplicateur de la course » -> vitesse de l'accelerateur (l'ancien multiplicateur de la camera, accel_camera, est abandonne : un seul facteur pour les deux)
                if isinstance(d.get('touches'), dict) and 'accel' not in d['touches']:       # anciennes touches de course et d'acceleration de la camera -> une seule « Touche d'accélérateur » : « Courir (maintenir) », a defaut les trois autres (« appuyer » n'existe plus)
                    for ancien in ('courir', 'courir_bascule', 'cam_accel', 'cam_accel_bascule'):
                        l = d['touches'].get(ancien)
                        if isinstance(l, list) and any(l): d['touches']['accel'] = l; break
                    else:
                        if isinstance(d['touches'].get('courir'), list): d['touches']['accel'] = [None, None]        # le joueur avait vide ces touches : l'accelerateur n'a pas de touche
                if 'defilement_combat' not in d and ('defilement_auto' in d or 'defilement_vitesse' in d):         # anciens reglages « Defilement automatique » (oui / non) + « Vitesse de defilement » (0 a 3) -> un seul reglage « Messages en combat »
                    vit = d.get('defilement_vitesse'); vit = 2 if isinstance(vit, bool) or not isinstance(vit, (int, float)) else min(3, max(0, int(round(vit))))
                    d['defilement_combat'] = COMBAT_MANUEL if d.get('defilement_auto') is False else cran_defilement(vit)
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
                    if self.v['vitesse_accel'] == 2.0: self.v['vitesse_accel'] = DEFAUT['vitesse_accel']
                saved = d.get('touches') if isinstance(d.get('touches'), dict) else {}
                for a in TOUCHES_DEF:                                  # action ajoutee depuis : sa touche d'origine est abandonnee si une autre action l'a prise
                    if a in saved: continue
                    ts = self.v['touches']
                    for i, n in enumerate(ts[a]):
                        if n and any(n in l for b, l in ts.items() if b != a): ts[a][i] = None
                self.v['touches_v'] = DEFAUT['touches_v']
                for ts in self.v['touches'].values():                   # une touche reservee (F11 : bascule du plein ecran exclusif) ne peut plus etre une touche d'action : retiree d'un ancien fichier
                    for i in range(2):
                        if ts[i] in RESERVEES: ts[i] = None
                for k, (mi, ma) in BORNES.items(): self.v[k] = min(ma, max(mi, self.v[k])) if isinstance(self.v[k], (int, float)) and not isinstance(self.v[k], bool) else DEFAUT[k]       # valeurs d'anciennes versions ramenees aux curseurs
                for k in BOOLEENS_SON_TEXTE:
                    if not isinstance(self.v[k], bool): self.v[k] = DEFAUT[k]
                self.v['defilement_combat'] = cran_defilement(self.v['defilement_combat']) if isinstance(self.v['defilement_combat'], int) and not isinstance(self.v['defilement_combat'], bool) else DEFAUT['defilement_combat']
                for k in VITESSES_X_CLES: self.v[k] = cran_x(self.v[k], DEFAUT[k])                       # ancien curseur (0,5 a 2) -> x1 a x4
                self.v['vitesse_combat'] = cran_combat(self.v['vitesse_combat'], DEFAUT['vitesse_combat'])
                if not isinstance(self.v['correction_bords'], (bool, int, float)): self.v['correction_bords'] = DEFAUT['correction_bords']        # (0 a 1 accepte : correction partielle ; autre chose : valeur par defaut)
                self.v['vitesse_texte'] = min(VITESSES_TEXTE, key=lambda x: max(x, self.v['vitesse_texte']) / min(x, self.v['vitesse_texte']))        # un des crans du menu
                fw = self.v['interface_fenetres']; self.v['interface_fenetres'] = {n: x for n, x in fw.items() if n not in FENETRES_RETIREES and isinstance(x, list) and len(x) == 3} if isinstance(fw, dict) else {}      # editeur d'interface : fenetres retirees de l'editeur
                ms = self.v['interface_masquees']; self.v['interface_masquees'] = [n for n in ms if isinstance(n, str) and n not in FENETRES_RETIREES] if isinstance(ms, list) else []
                self.v['mode_sprites'] = mode_sprites_valide(self.v['mode_sprites'])
                self.v['mode_fenetre'] = mode_fenetre_valide(self.v['mode_fenetre']); self.v['mode_fenetre_retour'] = 1 if mode_fenetre_valide(self.v['mode_fenetre_retour']) == 1 else 0       # (le retour de l'exclusif n'est jamais l'exclusif)
                if self.v['msaa'] not in MSAA_VALEURS: self.v['msaa'] = DEFAUT['msaa']
            except Exception as ex:
                print('Reglages illisibles (%s) : valeurs par defaut (%r)' % (chemin, ex), flush=True)
        self.codes_cache = {}

    def __getitem__(self, k): return self.v[k]

    def __setitem__(self, k, x):
        self.v[k] = x; self.codes_cache = {}

    # ---- editeur d'interface : remises a zero (toujours a partir de DEFAUT, jamais de valeurs recopiees)
    @staticmethod
    def defaut(cle):
        """Copie (modifiable) de la valeur par defaut d'un reglage."""
        return json.loads(json.dumps(DEFAUT[cle]))

    def remettre_interface(self, cible):
        """« Retablir cette interface » : l'interface `cible` de l'editeur (CIBLE_ECRAN, 'msg' ou nom Make_* d'une fenetre du jeu) revient entierement a son etat d'origine, et elle seule :
        position, taille, affichage (« Afficher cette interface a l'ecran ») et ses autres options. Boutons et croix de l'ecran : tout CLES_ECRAN (affichage, taille de la croix et des boutons, positions).
        Fenetre du jeu : son entree de CLES_FENETRES (absente de DEFAUT = taille, position et affichage du jeu). Les options de l'editeur (CLES_EDITEUR) ne bougent pas."""
        if cible == CIBLE_ECRAN:
            for k in CLES_ECRAN: self[k] = self.defaut(k)
            return
        fen = dict(self['interface_fenetres']); fen.pop(cible, None)
        if cible in DEFAUT['interface_fenetres']: fen[cible] = self.defaut('interface_fenetres')[cible]
        self['interface_fenetres'] = fen
        masquees = [n for n in self['interface_masquees'] if n != cible]
        if cible in DEFAUT['interface_masquees']: masquees.append(cible)
        self['interface_masquees'] = masquees

    def remettre_interfaces(self):
        """« Retablir toutes les interfaces » : toutes les interfaces (CLES_ECRAN et CLES_FENETRES) et les options de l'editeur (CLES_EDITEUR : grille, aimantation) reviennent a DEFAUT."""
        for k in CLES_INTERFACE: self[k] = self.defaut(k)

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
        """Action liee a une touche (ou None) : une touche ne sert qu'a une action."""
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
