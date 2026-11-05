"""Petites fonctions de la fenetre (sans etat) : zone utile de l'ecran, rang de profondeur, camera libre, hauteur de camera, matrice de projection..."""
import math, sys
import numpy as np
import pyglet
from dq4_pc.language import tr
from dq4_pc.core import engine as ENGINE
from dq4_pc.window.constants import GROUP_SLOTS, WINDOW_MARGIN


def useful_zone():
    """(largeur, hauteur) maximales d'une zone de dessin qui tient sur l'ecran principal avec sa barre de titre et la barre des taches ; None si l'ecran est inconnu."""
    try:
        ec = pyglet.display.get_display().get_default_screen()
        try: k = max(1.0, float(ec.get_dpi()) / 96.0)
        except Exception: k = 1.0
        return int(ec.width - 16 * k), int(ec.height - WINDOW_MARGIN * k)
    except Exception: return None


def adjust_size(w, h):
    """Ramene une taille de fenetre trop grande pour l'ecran a la plus grande taille de meme forme qui tient : Windows reduit alors la fenetre sans prevenir et le dessin gardait la taille demandee (scene zoomee, en partie hors de la fenetre)."""
    zu = useful_zone()
    if zu is None or (w <= zu[0] and h <= zu[1]): return int(w), int(h)
    k = min(zu[0] / float(w), zu[1] / float(h)); nw, nh = max(320, int(w * k)), max(180, int(h * k))
    print(tr('Fenêtre %d x %d trop grande pour l\'écran : %d x %d') % (w, h, nw, nh), flush=True)
    return nw, nh


def field_depth_rank(sprites):
    """Carte du monde : rang de superposition de chaque sprite place (le plus grand rang est devant ; il pose la hauteur 0,04 + rang x 0,0005 du sprite a plat).
    Le jeu (FieldPartyDraw::draw, libdq4core 0x1ec5a8) trie les membres du groupe par profondeur decroissante (tri par selection ; a profondeur egale, l'emplacement le plus bas garde la tete) puis leur donne
    SpriteCharacter::setDepth 10, 9, 8... dans cet ordre : a profondeur egale, le heros (emplacement 0) est devant son equipier. Ordre ici : hauteur z du moteur (3e valeur de la position), puis le plus au sud
    (un equipier au sud du heros est devant lui), puis, a position egale (atterrissage d'une aile de chimere ou de Zoom : le groupe est empile sur un seul point, issue #135), l'emplacement le plus BAS devant
    pour le groupe ; les vehicules (emplacements >= 10) gardent le plus recent devant."""
    seen = [(float(s['pos'][2]) if len(s['pos']) > 2 else 0.0, float(s['pos'][1]), -sl if sl < GROUP_SLOTS else sl, sl) for sl, s in sprites.items() if s['pos'] is not None]
    return {sl: i for i, (_, _, _, sl) in enumerate(sorted(seen))}


def rot_unity(ex, ey, ez):
    """Matrice 3x3 d'une rotation Unity (angles d'Euler en degres, ordre z puis x puis y, espace gauche) : colonne = axe local dans le monde."""
    cx, sx, cy, sy, cz, sz = (math.cos(math.radians(ex)), math.sin(math.radians(ex)), math.cos(math.radians(ey)), math.sin(math.radians(ey)), math.cos(math.radians(ez)), math.sin(math.radians(ez)))
    Rx = np.array([[1, 0, 0], [0, cx, -sx], [0, sx, cx]]); Ry = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]]); Rz = np.array([[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]])
    return Ry @ Rx @ Rz


def camera_free(e):
    """Camera libre : position + rotation (comme en combat), pas de cible. Paquet 11 bit 7 (scenes, titre) ; casino : le moteur envoie la position et la rotation (paquet 10, masque 5) sans paquet 11."""
    return bool(e.cam_free or (getattr(e, 'part', None) == ENGINE.PART_CASINO and e.cam_rot is not None))


def background_gradient(topmost, bottom):
    """Le fond de la ville est-il un vrai degrade (paquet 8 : couleurs du haut et du bas de l'image, `State.top_background` / `bottom_background`) ? Faux sans paquet 8 (None) ou si les deux couleurs sont egales : l'effacement
    de l'image, de cette couleur, suffit (aucune difference avec avant #111)."""
    return topmost is not None and bottom is not None and max(abs(float(a) - float(b)) for a, b in zip(topmost, bottom)) > 1e-6


def without_validation(eng, ui_g, port):
    """Fenetre ouverte sans bouton de validation (manette 0x10) ni curseur du moteur (Oui / Non) : elle n'a rien a faire de la touche A (ex. « Quitter » de l'arene des monstres, un seul bouton de retour 0x400)."""
    if ui_g is None: return False
    f = eng.ui.f.get(port); wnd = ui_g.f.get(port)
    return bool(f and wnd and not f.get('grille') and not any(b[1] & 0x10 for b in wnd.buttons()))


def matrix(cam, target, fov, aspect, n=1.0, f=200.0, topmost=(0, 1, 0)):
    pos = np.array(cam, float); fw = np.array(target, float) - pos; fw /= np.linalg.norm(fw)
    right = np.cross(topmost, fw); right /= np.linalg.norm(right); topmost = np.cross(fw, right)
    th = math.tan(math.radians(fov) / 2)
    M = np.zeros((4, 4))
    M[0, :3] = right / (th * aspect); M[0, 3] = -pos @ right / (th * aspect)
    M[1, :3] = topmost / th; M[1, 3] = -pos @ topmost / th
    k = (f + n) / (f - n)
    M[2, :3] = fw * k; M[2, 3] = -pos @ fw * k - 2 * f * n / (f - n)
    M[3, :3] = fw; M[3, 3] = -pos @ fw
    return M, right


def transitions_dwm(window, active):
    """Windows seulement : active ou coupe les animations de la fenetre faites par le gestionnaire de fenetres (DWM : ouverture en fondu / zoom, reduction, restauration ; DWMWA_TRANSITIONS_FORCEDISABLED).
    Coupees pendant l'ouverture de la fenetre du jeu, elles ne s'ajoutent pas (un fondu de la fenetre elle-meme, par-dessus le noir puis les logos, ressemble a un rideau) ; remises ensuite (voir on_draw).
    Aucune erreur ne remonte (systeme sans DWM, poignee absente : rien ne change). -> True si le systeme a accepte."""
    if not sys.platform.startswith('win'): return False
    try:
        import ctypes
        hwnd = getattr(window, '_hwnd', None)
        if not hwnd: return False
        v = ctypes.c_int(0 if active else 1)
        return ctypes.windll.dwmapi.DwmSetWindowAttribute(ctypes.c_void_p(hwnd), 3, ctypes.byref(v), ctypes.sizeof(v)) == 0
    except Exception as ex:
        print(tr('Transitions de fenêtre (DWM) inchangées : %r') % (ex,), flush=True); return False
