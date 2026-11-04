"""Effet « Ranaruta » (Capture.DarkLamp, valeur du paquet 34 & 0xf = 5 ; bit 7 = bMorning) : la capture de l'ecran, plaquee sur une grille de 16 x 14 cases, se « pince » verticalement autour de sa colonne centrale (une paupiere
en cloche qui se ferme puis se rouvre), se teinte (nuit : bleu ; matin : jaune), laisse une remanence floue, puis s'assombrit jusqu'au noir.
Regles de Capture.<DarkLamp>d__47.MoveNext (libil2cpp, RVA 0xCC8520), en float32 comme le jeu, a l'instruction pres (adresses en commentaire) : maillage, couleurs et champs identiques au bit pres au code machine
execute sous Unicorn. 64 appels de MoveNext : 2 de preparation (le jeu reste affiche), 60 mises a jour du maillage (compteur 0 a 59), 1 de noir immediat (SetBlur(false), Fade.SetFadeOutBlack(0)), 1 de nettoyage
(MoveNext rend faux : le bit 1 retombe) ; l'ecran reste noir ensuite, jusqu'au fondu d'entree du moteur.
Seul le nombre de rangees depend de l'ecran (`h_divY = m_divY >> 2`, m_divY = int(32 / aspect) : 14 en portrait 9/16, 4 en 16/9) : on garde les 14 rangees du mobile, car la courbe de la « paupiere » est en
coordonnees d'ecran normalisees (4 rangees en feraient un contour anguleux)."""
import numpy as np
from dq4_pc.rendu import effets_capture as EC
from dq4_pc.rendu.effets_capture import F32, f32

H_DIV_X = 16                    # 0xCC8624 : cases par rangee
DIV_X = H_DIV_X + 1             # sommets par rangee
RANGEES = 14                    # h_divY = m_divY >> 2 (0xCC8E24) avec m_divY = 56
Z_GRILLE = f32(0x3E828F5C)      # 0,255 : registre de calcul (la valeur 0..255 d'un sommet / 1000), pas un z d'affichage (ZTest Always)
ECHELLE_X = f32(0x3F803127)     # 1,0015 : etirement horizontal des sommets interieurs par image (0xCC90D8)
PAS_MOUV = f32(0xBC7A0000)      # -0,0152587890625 : vitesse initiale de `movement` (pool 0x4C1228)
SEUIL_BAS, SEUIL_HAUT = f32(0x3F19999A), f32(0x3F99999A)      # 0,6 et 1,2 : bornes de `bias` (pools 0x4C1348, 0x4C139C)
DECAL = f32(0xBDCCCCCD)         # -0,1 : decalage de |y| pour les colonnes voisines (pool 0x4C1520)
CBIAS_MAX, CBIAS_PAS = F32(5.0), F32(0.25)                    # 0xCC9580, 0xCC958C
K_MILLE, K_Z = F32(1000.0), f32(0x3A83126F)                   # z -> valeur 0..255 ; valeur -> z (0,001)
C_ALPHA0 = f32(0x3F69999A)      # 0,9125 : alpha initial de la grille (pool 0x4C0BE4)
B_ALPHA_PAS, C_ALPHA_PAS = f32(0x3DB33333), f32(0xBC23D70A)   # +0,0875 (fond), -0,01 (grille) pendant les 10 premieres mises a jour (pools 0x4C12A4, 0x4C13C0)
FADE_PAS = f32(0xBD088889)      # -1/30 : noircissement de la capture des la mise a jour 30 (pool 0x4C13E0)
COMPTEUR_ALPHA, COMPTEUR_FADE, COMPTEUR_FIN = 9, 30, 60       # 0xCC8BE4, 0xCC9628, 0xCC8BD8


class EffetLampe(EC.EffetCapture):
    def __init__(self, matin=False, rangees=RANGEES):
        """matin = bMorning (bit 7 de la valeur) : seul le bleu baisse (teinte jaune) au lieu du rouge et du vert (teinte bleue) ; rangees = h_divY."""
        super().__init__()
        self.matin = bool(matin)
        self.h_div_y = max(1, int(rangees)); self.div_y = self.h_div_y + 1; self.nb = DIV_X * self.div_y
        self.duree = EC.IMAGES['lampe']
        self.etat = 0                                       # <>1__state
        self.movement = PAS_MOUV; self.bias = F32(1.0); self.cbias = F32(0.0) if self.matin else F32(1.0)
        self.fade = F32(1.0); self.c_alpha = C_ALPHA0; self.b_alpha = F32(0.0); self.counter = 0
        self.hx = DIV_X >> 1
        self.mat_fond = np.ones(4, F32); self.mat_grille = np.ones(4, F32)        # _Color des materiaux Custom/CaptureBlur et Custom/Capture
        # maillage (0xCC873C-0xCC89F0) : x += 2/16, y -= 2/h_divY, u += 1/16, v -= 1/h_divY, cumules en float32 comme le jeu
        pas_x = F32(F32(2.0) / F32(H_DIV_X)); pas_u = F32(F32(1.0) / F32(H_DIV_X)); pas_v = F32(F32(1.0) / F32(self.h_div_y)); ay = F32(F32(2.0) / F32(self.h_div_y))
        x = np.add.accumulate(np.concatenate(([F32(-1.0)], np.full(DIV_X - 1, pas_x, F32))), dtype=F32)
        u = np.add.accumulate(np.concatenate(([F32(0.0)], np.full(DIV_X - 1, pas_u, F32))), dtype=F32)
        y = np.add.accumulate(np.concatenate(([F32(1.0)], np.full(self.div_y - 1, -ay, F32))), dtype=F32)
        v = np.add.accumulate(np.concatenate(([F32(1.0)], np.full(self.div_y - 1, -pas_v, F32))), dtype=F32)
        self.pt = y.copy()                                  # y initial de chaque rangee (pt[], jamais modifie)
        self.g = np.zeros((self.div_y, DIV_X, 3), F32)      # sommets (rangee, colonne, xyz)
        self.g[:, :, 0] = x[None, :]; self.g[:, :, 1] = y[:, None]; self.g[:, :, 2] = Z_GRILLE
        self.cl = np.full((self.div_y, DIV_X, 4), 255, np.uint8)       # Color32 (c_white)
        self._tri = EC.grille_triangles(H_DIV_X, self.h_div_y)
        self._uv = np.stack([np.tile(u, self.div_y), np.repeat(v, DIV_X)], 1).astype(F32)[self._tri]
        self._uv_fond = EC.UV_FOND[EC.TRI_FOND]; self._pos_fond = EC.COIN_FOND[EC.TRI_FOND]

    # ------------------------------------------------------------------ un appel de MoveNext
    def _move_next(self):
        e = self.etat
        if e == 0:                                          # 0xCC8620 : SetBlur(true), Snap()
            self._flou = True; self._capture = True; self.etat = 1
            return True
        if e == 1:                                          # 0xCC864C : maillage construit ; la capture a ete faite au debut de cet appel
            self.etat = 2
            return True
        if e == 2:                                          # 0xCC8B74 : une fois la capture faite, l'effet commence : mise a jour 0
            if self._capture: return True
            self.rendu_actif = True; self.counter = 0
            self._maj(); self.etat = 3
            return True
        if e == 3:                                          # 0xCC8BC8
            self.counter += 1
            if self.counter >= COMPTEUR_FIN:                # 0xCC8CD0 : SetBlur(false) ; l'hote rend l'ecran noir (Fade.SetFadeOutBlack(0))
                self._flou = False; self.etat = 4
                return True
            self._maj()
            return True
        self.rendu_actif = False                            # 0xCC8BF0 : Mesh.Clear, rendu coupe : MoveNext rend faux
        self.etat = 5
        return False

    def _maj(self):
        """Une mise a jour du maillage (0xCC903C-0xCC9624) : appel 3 (compteur 0) a appel 62 (compteur 59)."""
        g, c = self.g, self.cl
        if self.counter <= COMPTEUR_ALPHA:                  # opacites (10 premieres mises a jour) : fond 0,0875 -> 0,875, grille 0,9125 -> 0,8125
            self.b_alpha = F32(self.b_alpha + B_ALPHA_PAS); self.mat_fond[:] = (1, 1, 1, self.b_alpha)
            self.c_alpha = F32(self.c_alpha + C_ALPHA_PAS); self.mat_grille[:] = (1, 1, 1, self.c_alpha)
        if self.div_y > 2: g[1:self.div_y - 1, 1:DIV_X - 1, 0] *= ECHELLE_X       # passe 1 : les sommets interieurs s'etirent en x (son calcul de y est ecrase par la passe 2)
        pt = self.pt; b = self.bias; a0 = np.abs(pt)        # passe 2 : « paupiere » : y = pt (1 - a) + a (bias pt) sur les colonnes hx - 7 a hx + 7 ; les colonnes 0 et 16 gardent leur y initial
        g[:, self.hx, 1] = (pt * (F32(1.0) - a0)) + (a0 * (pt * b))
        a = a0 + DECAL
        for k in range(1, self.hx):
            y = (pt * (F32(1.0) - a)) + (a * (b * pt))
            g[:, self.hx - k, 1] = y; g[:, self.hx + k, 1] = y
            a = a * a
        t = F32(2.0) - np.abs(g[0, :, 0])                   # passe 3 : valeur 0..255 par colonne (plus vite au centre), teinte et z = valeur / 1000
        seuil = t * (self.cbias * t)
        s4 = (g[:, :, 2] * K_MILLE) - seuil[None, :]
        val = np.where(s4 < 0, F32(0.0), np.where(s4 > F32(255.0), F32(255.0), s4)).astype(F32)
        octet = val.astype(np.uint8)
        if self.matin: c[:, :, 2] = octet
        else: c[:, :, 0] = octet; c[:, :, 1] = octet
        g[:, :, 2] = val * K_Z
        if self.cbias < CBIAS_MAX: self.cbias = F32(self.cbias + CBIAS_PAS)
        self.bias = F32(self.bias + self.movement)
        if self.bias < SEUIL_BAS or (self.movement > 0 and self.bias > SEUIL_HAUT): self.movement = F32(-self.movement)
        if self.counter >= COMPTEUR_FADE and self.fade > 0:  # noircissement de la capture
            self.fade = max(F32(self.fade + FADE_PAS), F32(0.0))
            self.mat_grille[:] = (self.fade, self.fade, self.fade, self.c_alpha)

    # ------------------------------------------------------------------ dessin
    def dessins(self):
        if not self.rendu_actif: return []
        n = len(self._tri)
        cl = (self.cl.reshape(-1, 4).astype(F32) / F32(255.0))[self._tri] * self.mat_grille[None, :]      # vs_COLOR0 = couleur du sommet x _Color
        return [('flou', self._pos_fond, self._uv_fond, np.tile(self.mat_fond, (6, 1))),
                ('capture', self.g.reshape(-1, 3)[self._tri, :2], self._uv, cl)]
