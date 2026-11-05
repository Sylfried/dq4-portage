"""Effet de sortie de donjon (Capture.Riremito, valeur du paquet 34 & 0xf = 6) : la capture de l'ecran est affichee en QUATRE copies translucides superposees qui s'ecartent en diagonale en tournant tres legerement,
pendant que la camera du jeu est coupee ; derriere elles, un plan plein ecran montre le rendu precedent (remanence floue a mi-resolution) ; des l'image 30 les copies noircissent, tout s'eteint, puis noir net
(Fade.SetFadeOutBlack(0)). 63 appels de MoveNext : 2 de preparation (le jeu reste affiche), 59 mises a jour du maillage (compteur 1 a 59), 1 de noir net, 1 de nettoyage (MoveNext rend faux : le bit 1 retombe).
Regles de Capture.<Riremito>d__48.MoveNext (libil2cpp, RVA 0xCC97FC), en float32 comme le jeu (adresses en commentaire) :
  * a la mise a jour de compteur c : la rotation (degres) croit de 0,11 par image ; la copie i (0 a 3) est le carre [-1, 1]^2 tourne de cet angle autour de Z, puis decale de (+-3 u, +-u) avec u = 10 (i + 1) c x 0,00005
    (diagonales : i = 0 droite-bas, 1 droite-haut, 2 gauche-haut, 3 gauche-bas) ;
  * mises a jour 1 a 9 : le fond passe a (b, b, b, 1) avec b = 0,1 c, l'opacite des copies a 0,9 - 0,08 c (0,18 a l'image 9, puis constante) ;
  * a partir de c = 30 : la couleur des copies (r = g = b) baisse de 1/30 par image jusqu'a 0 (atteint a c = 59).
Le maillage fait toujours 20 sommets (il ne depend pas de l'ecran) et les positions sont en coordonnees d'ecran normalisees : les copies couvrent tout l'ecran quel que soit son rapport (en 16/9 le deplacement,
en fractions de l'ecran, est plus horizontal qu'en portrait : reproduit tel quel)."""
import numpy as np
from dq4_pc.render import capture_effects as EC
from dq4_pc.render.capture_effects import F32, f32

CLONE_COUNT = 4
ROT_STEP = f32(0x3DE147AE)       # 0,11 degre par image (pool 0x4C1304)
DEG_RAD = f32(0x3C8EFA35)       # pi / 180 (pool 0x4C13A0)
STEP_B = f32(0x3DCCCCCD)         # 0,1 : pas du fond ET ecart en z entre copies (pool 0x4C136C ; le z n'a pas d'effet : ZTest Always)
STEP_C = f32(0xBDA3D70A)         # -0,08 : pas de l'opacite des copies (pool 0x4C1508)
K_DEP = f32(0xB851B717)         # -0,00005 : facteur des deplacements (pool 0x4C1490)
FADE_STEP = f32(0xBD088889)      # -1/30 (pool 0x4C13E0)
INIT_C_ALPHA, INIT_B_ALPHA, INIT_ROT, INIT_FADE = f32(0x3F666666), F32(0.0), F32(0.0), F32(1.0)      # 0,9 ; 0 ; 0 ; 1 (pool 0x4DBB00)
LIMIT_B, FADE_START, END = 9, 30, 60                         # 0xCCA248, 0xCCA404, 0xCC9E28
CORNERS = np.array([[-1, 1], [-1, -1], [1, 1], [1, -1]], F32)    # sommets d'une copie : haut gauche, bas gauche, haut droit, bas droit
TRIANGLES = np.array([0, 2, 1, 2, 3, 1])                            # triangles d'une copie (boucle 0xCC9B48)


class RiremitoEffect(EC.CaptureEffect):
    def __init__(self):
        super().__init__()
        self.duration = EC.FRAMES['riremito']
        self.state = 0                                         # <>1__state
        self.counter = 0; self.c_alpha = INIT_C_ALPHA; self.b_alpha = INIT_B_ALPHA; self.rot = INIT_ROT; self.fade = INIT_FADE
        self.vt = np.zeros((4 * CLONE_COUNT, 3), F32)           # sommets des quatre copies (x, y, z)
        self.background_mat = np.ones(4, F32); self.mat_capture = np.ones(4, F32)     # _Color des materiaux Custom/CaptureBlur et Custom/Capture
        idx = (np.arange(CLONE_COUNT)[:, None] * 4 + TRIANGLES[None, :]).ravel()
        self._idx = idx; self._uv = np.tile(EC.BACKGROUND_UV[TRIANGLES], (CLONE_COUNT, 1))
        self._background_uv = EC.BACKGROUND_UV[EC.BACKGROUND_TRIANGLES]; self._background_pos = EC.BACKGROUND_CORNERS[EC.BACKGROUND_TRIANGLES]

    # ------------------------------------------------------------------ un appel de MoveNext
    def _move_next(self):
        e = self.state
        if e == 0:                                            # 0xCC98F4 : SetBlur(true), Snap()
            self._blur = True; self._capture = True; self.state = 1
            return True
        if e == 1:                                            # 0xCC99B0 : maillage
            self.state = 2
            return True
        if e == 2:                                            # 0xCC9DC4 : une fois la capture faite : debut de l'affichage et mise a jour 1
            if self._capture: return True
            self.render_active = True
            self.c_alpha, self.b_alpha, self.rot, self.fade = INIT_C_ALPHA, INIT_B_ALPHA, INIT_ROT, INIT_FADE
            self.counter = 1; self._update(); self.state = 3
            return True
        if e == 3:                                            # 0xCC9E18
            self.counter += 1
            if self.counter < END:
                self._update()
                return True
            self._blur = False; self.state = 4                 # 0xCC9E38 : SetBlur(false) ; l'hote rend l'ecran noir (Fade.SetFadeOutBlack(0))
            return True
        self.render_active = False; self.state = 5               # 0xCC9EDC : nettoyage, MoveNext rend faux
        return False

    def _update(self):
        """Mise a jour du maillage et des materiaux pour le compteur courant (0xCCA204-0xCCA4C0)."""
        c = self.counter
        self.rot = F32(self.rot + ROT_STEP)
        half = F32(F32(self.rot * DEG_RAD) * F32(0.5))
        sz, cw = F32(np.sin(half)), F32(np.cos(half))        # Quaternion.Internal_FromEulerRad(0, 0, angle) = (0, 0, sin(angle / 2), cos(angle / 2))
        n3 = F32(sz * F32(2.0)); a = F32(F32(1.0) - F32(sz * n3)); n12 = F32(cw * n3)         # Quaternion * Vector3 (formule de Unity)
        if c <= LIMIT_B:
            self.b_alpha = F32(self.b_alpha + STEP_B); self.background_mat[:] = (self.b_alpha, self.b_alpha, self.b_alpha, 1)
            self.c_alpha = F32(self.c_alpha + STEP_C); self.mat_capture[:] = (1, 1, 1, self.c_alpha)
        for i in range(CLONE_COUNT):
            t = F32(F32(10 * (i + 1)) * F32(c))
            dx = F32(F32(t * F32(3.0)) * K_DEP); dy = F32(t * K_DEP)
            if i == 0: dx = -dx
            elif i == 1: dx = -dx; dy = -dy
            elif i == 2: dy = -dy
            dz = F32(F32(i) * STEP_B)
            for j in range(4):
                px, py = CORNERS[j]
                self.vt[4 * i + j] = (F32(dx + F32(F32(a * px) + F32(-n12 * py))), F32(dy + F32(F32(n12 * px) + F32(a * py))), dz)
        if c >= FADE_START and self.fade > 0:
            self.fade = F32(max(F32(self.fade + FADE_STEP), F32(0.0)))
            self.mat_capture[:] = (self.fade, self.fade, self.fade, self.c_alpha)

    # ------------------------------------------------------------------ dessin
    def drawings(self):
        if not self.render_active: return []
        n = len(self._idx)
        return [('flou', self._background_pos, self._background_uv, np.tile(self.background_mat, (6, 1))),
                ('capture', self.vt[self._idx, :2], self._uv, np.tile(self.mat_capture, (n, 1)))]
