"""Poses couchees des personnages de ville (paquets 16 / 17 / 18 du moteur, #45).

Ce que fait le jeu d'origine (lu au desassemblage, Unity IL2CPP + moteur) :
  - Paquet 16 `cmd_chara_sleep_pose` D132FC, un entier v : personnage = v & 0xff ; si v & 0x300 : Chara.SetSleepPose(bit 8) (CCC234) ; si v & 0x400 : Chara.SetSleepDir(v >> 12) (CCC5A0).
    Envoye par `DisplayCharacter::setSleepFlag` (moteur 0x17c918 : 0x500 | angle << 12 pour se coucher, 0x200 pour se relever) et, quand la direction change pendant le sommeil,
    par `DisplayCharacter::draw` (0x400 | angle << 12). SetSleepDir(d) : angle = (d & 0xffff) / -182,0444 + 180 degres, rotation Y ; quadrant = bits 14-15 de d.
  - Paquet 17 `cmd_chara_sleep_near` D133E4, deux entiers (defNear, decalage) : Chara.SetSleepNear (CCD494) : hauteur du corps couche = 0,3104 si decalage = 0, sinon decalage x 1,6 / 8192 ;
    elle est ecrite dans la composante Y des 4 decalages `s_lieOffset` (statique : elle reste d'une carte a l'autre). Envoye par `cmd_set_sleep_near` (moteur 0x219e1c).
  - Paquet 18 `cmd_chara_pose` D13474 : v = emplacement | numero << 8 : Chara.SetTexture(numero) : le personnage change de feuille de sprites (`TownCharacterDraw::changePose`).
  - Maillage couche `Chara.s_meshLie4 / 8` : le meme rectangle que le panneau (0,48 x 0,64) mais A PLAT (plan XZ, y = 0), retourne d'un demi-tour (haut de la feuille vers -Z), d'ou le + 180 degres de SetSleepDir.
  - Shader `Custom/CharaSleep` : la position ecran (x, y) vient de la transformation du personnage, dont la rotation est celle de la camera inversee x la rotation de sommeil (s_lieBillboardRot,
    Chara.CalcLieBillboard) : le plan couche est vu exactement DE DESSUS, sans raccourci : le sprite apparait a l'ecran comme sa feuille tournee d'un angle, a pleine taille. Le z et le w (profondeur,
    division perspective) viennent de la matrice `_sleepMatrix` = TRS(position + (0, 0,1, 0), rotation de sommeil, echelle) : le corps est a plat dans le monde pour le z-buffer et les recouvrements.
  - Position : P + s_lieOffset[quadrant] ; s_lieOffset (Chara..cctor CCE364) = (0, h, 0,2), (-0,1, h, 0), (0, h, -0,2), (0,1, h, 0) ; h = hauteur de SetSleepNear (0 tant qu'aucun paquet 17).
  - L'ombre n'est pas tracee (Chara.lieBillboard la pousse de 64 sous le sol quand elle n'est pas separee).

Ce module ne contient que de la geometrie (numpy) : testable sans fenetre.
"""
import math
import numpy as np

HALF_L, HALF_H = 0.24, 0.32                                  # moitie du maillage couche (0,48 x 0,64), avant l'echelle du personnage
OFFSETS = ((0.0, 0.2), (-0.1, 0.0), (0.0, -0.2), (0.1, 0.0))   # s_lieOffset[quadrant] : (x, z) ; la composante y est la hauteur de SetSleepNear
HEIGHT_DEFAULT = 0.3104                                         # SetSleepNear : decalage 0
MATRIX_HEIGHT = 0.1                                           # lieBillboard : la matrice _sleepMatrix est relevee de 0,1
DEG_PER_UNIT = -182.04444885253906                          # SetSleepDir : angle 16 bits / -182,0444 + 180 (65536 / 360, signe inverse)


def packet_height(offset):
    """Hauteur du corps couche (paquet 17, second entier) : Chara.SetSleepNear."""
    return HEIGHT_DEFAULT if offset == 0 else offset * (1.0 / 8192.0) * 1.6


def packet_direction(value):
    """(angle de la rotation Y en degres, quadrant 0 a 3) d'un paquet 16 portant le bit 0x400 : Chara.SetSleepDir(valeur >> 12)."""
    d = int(value) >> 12
    return (d & 0xffff) / DEG_PER_UNIT + 180.0, (d >> 14) & 3


def head_on_screen(angle_deg):
    """Direction de la tete du personnage couche a l'ecran (vue de dessus, camera de lacet nul) en degres dans le sens des aiguilles d'une montre : 0 = vers le haut, 90 = vers la droite : sert aux tests."""
    return (angle_deg + 180.0) % 360.0


def vertices(p, angle_deg, quadrant, topmost, scale_factor, border, cam):
    """Les 4 sommets MONDE (bas gauche, bas droit, haut droit, haut gauche DE LA FEUILLE) du panneau d'un personnage couche dont les pieds sont en p.
    echelle : taille du maillage (largeur du panneau a l'ecran / 0,48, avec l'echelle SetScale du personnage) ; cadre = (droite, haut, avant) de la camera, cam = sa position.
    Les points sont sur les rayons de vue : a l'ecran le panneau est la feuille tournee d'un angle, a pleine taille (aucun raccourci, aucune inclinaison), mais sa profondeur est celle du corps a plat
    (voir l'en-tete) ; None si le corps est derriere la camera."""
    r_, u_, f_ = border; p = np.asarray(p, float); cam = np.asarray(cam, float)
    ox, oz = OFFSETS[quadrant & 3]
    c0 = p + np.array([ox, topmost, oz])                                   # centre du maillage (Transform.position)
    w0 = c0 + np.array([0.0, MATRIX_HEIGHT, 0.0])                       # centre pour la profondeur (_sleepMatrix)
    z0 = float((w0 - cam) @ f_)
    if z0 <= 1e-3: return None
    th = math.radians(angle_deg); ct, st = math.cos(th), math.sin(th)
    rh = np.array([r_[0], 0.0, r_[2]]); rh /= (np.linalg.norm(rh) or 1.0)       # lacet seul de la camera : vue de dessus orientee par la camera
    fh = np.array([f_[0], 0.0, f_[2]]); fh /= (np.linalg.norm(fh) or 1.0)
    cv = c0 - cam; xc, yc = float(cv @ r_), float(cv @ u_)
    out = []
    for cx, cy in ((-HALF_L, -HALF_H), (HALF_L, -HALF_H), (HALF_L, HALF_H), (-HALF_L, HALF_H)):       # coins de la feuille, centres : bas gauche, bas droit, haut droit, haut gauche
        mx, mz = -cx * scale_factor, -cy * scale_factor                           # sommet du maillage couche : droite de la feuille = -X, haut = -Z
        dx, dz = mx * ct + mz * st, -mx * st + mz * ct                   # rotation Y (Quaternion.Euler(0, angle, 0))
        d = np.array([dx, 0.0, dz])
        zi = float((w0 + d - cam) @ f_)                                  # profondeur du corps a plat
        xs, ys = xc + float(d @ rh), yc + float(d @ fh)                  # position ecran (focale 1 a la profondeur z0) : plan XZ vu de dessus, sans raccourci
        k = zi / z0
        out.append(cam + r_ * (xs * k) + u_ * (ys * k) + f_ * zi)
    return tuple(out)
