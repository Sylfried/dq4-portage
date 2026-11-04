"""Effet de voyage (Capture.Tabi : ailes de Chimere, valeur du paquet 34 & 0xf = 3) : la capture de l'ecran, posee sur une grille de 16 colonnes de cases, est aspiree dans un tourbillon (zoom arriere + rotation
+ pincement vers le centre) pendant que deux couches se superposent : la capture (alpha « cAlpha ») et une copie floue de l'image precedente (alpha « bAlpha », remanence).
  * depart (bit 7 de la valeur a 0) : le tourbillon se resserre pendant 61 images (temps 0 -> 1, pas de 1/60), puis les deux couches passent a l'alpha 0 : ecran noir, la camera du jeu reste coupee ; 64 appels de MoveNext ;
  * arrivee (bit 7 a 1, apres le changement de carte) : le meme tourbillon parcouru a l'envers (temps 2/3 -> 0, 41 images) avec un fondu d'entree de 30 images, puis le jeu est remis en etat ; 45 appels.
Regles de Capture.<Tabi>d__49.MoveNext (libil2cpp, RVA 0xCCAC3C), a l'instruction pres (adresses en commentaire) : sommets identiques au bit pres au code machine execute sous Unicorn.
Le maillage de l'original depend de l'ecran (`Capture.m_divY` = int(32 / aspect) lu sur la camera du jeu : 56 en portrait 9/16, donc 28 rangees de cases ; 18 en 16/9, donc 9) : on garde ici les 28 rangees du mobile, car
les formules sont en coordonnees d'ecran normalisees (le tourbillon a la meme forme a l'ecran, mieux echantillonnee ; 9 rangees feraient des facettes visibles). Ces coordonnees rendent le tourbillon elliptique sur
un ecran 16/9 (comme il l'est, dans l'autre sens, sur le mobile) : reproduit tel quel."""
import numpy as np
from dq4_pc.rendu import effets_capture as EC
from dq4_pc.rendu.effets_capture import F32, f32

COLS = 16                       # h_divX (0xCCAD38) : cases par rangee
NX = COLS + 1                   # divX : sommets par rangee
RANGEES = 28                    # h_divY = m_divY >> 1 (0xCCAD74) avec m_divY = 56 (ecran portrait d'origine)
EPS = f32(0x38D1B717)           # 1e-4 : valeur de repli d'un sommet qui franchit le centre (pool 0x4C1258)
R_COIN = f32(0x3FB50481)        # 1,4142 (pas la vraie racine de 2) : pool 0x4C1438
K_PINCE = F32(1.75)             # fmov 0xCCB2BC
K_ZOOM = F32(-0.5)              # fmov 0xCCB25C
K_DEC_FLOU = f32(0xBC23D70A)    # -0,01 : decroissance de bAlpha par unite de temps (pool 0x4C13C0)
K_DEC_CAPT = f32(0xBD99999A)    # -0,075 : decroissance de cAlpha (pool 0x4C1278)
ROT_ACC = f32(0xBF866666)       # -1,05 : rotAcc (pool 0x4DC044)
PAS_TEMPS = f32(0x3C888889)     # +1/60 : timeAcc du depart (pool 0x4DC04C)
T0_RETOUR = f32(0x3F2AAAAA)     # 2/3 : temps initial de l'arrivee (pool 0x4C0CC8)
PAS_TEMPS_RETOUR = f32(0xBC888889)    # -1/60
ACC_FLOU = {False: f32(0x3E6CCCCD), True: f32(0x3E79999A)}      # 0,23125 (depart) / 0,24375 (arrivee) : montee de bAlpha par image (pool 0x4C0B68)
ACC_CAPT_ALLER = f32(0xBD800000)      # -0,0625 : pas de cAlpha au depart (pool 0x4DC040)
ACC_CAPT_RETOUR = f32(0x3D800000)     # +0,0625 : pas de cAlpha a l'arrivee (pool 0x4C0FF8)
FIN_COMPTEUR = 61               # 0xCCB0D4 : fin quand le compteur atteint 61
DEBUT_DECROISSANCE = 30         # 0xCCB170 : le depart seulement
F_ALPHA = {False: 4, True: 24}  # fAlpha : les alphas montent tant que compteur < fAlpha (4 images)
COMPTEUR_RETOUR = 20            # 0xCCBA7C : compteur initial de l'arrivee
Z_GRILLE = f32(0x3E828F5C)      # 0,255 (sans effet : ZTest Always)


class EffetTabi(EC.EffetCapture):
    def __init__(self, inverse=False, rangees=RANGEES):
        """inverse = bReverse (arrivee) ; rangees = h_divY (28 : le maillage du mobile)."""
        super().__init__()
        self.inverse = bool(inverse)
        self.lignes = max(1, int(rangees)); self.ny = self.lignes + 1
        self.nb = NX * self.ny                                    # sommets de la grille
        self.duree = EC.images_de('tabi', self.inverse)
        ax = F32(F32(2.0) / F32(COLS)); ay = F32(F32(2.0) / F32(self.lignes))            # pas de la grille (0xCCAD94), cumules en float32 comme le jeu (0xCCAF4C)
        self._gx = np.add.accumulate(np.concatenate(([F32(-1.0)], np.full(NX - 1, ax, F32))), dtype=F32)
        self._gy = np.add.accumulate(np.concatenate(([F32(1.0)], np.full(self.ny - 1, -ay, F32))), dtype=F32)
        u = np.add.accumulate(np.concatenate(([F32(0.0)], np.full(NX - 1, F32(F32(1.0) / F32(COLS)), F32))), dtype=F32)
        v = np.add.accumulate(np.concatenate(([F32(1.0)], np.full(self.ny - 1, -F32(F32(1.0) / F32(self.lignes)), F32))), dtype=F32)
        self._tri = EC.grille_triangles(COLS, self.lignes)
        self._uv = np.stack([np.tile(u, self.ny), np.repeat(v, NX)], 1).astype(F32)[self._tri]       # (3 * 2 * cases, 2) : constant
        self._vt = np.zeros((self.nb, 2), F32)                    # x, y des sommets de la grille (z sans effet)
        self._uv_fond = EC.UV_FOND[EC.TRI_FOND]; self._pos_fond = EC.COIN_FOND[EC.TRI_FOND]
        self.etat = 0                                             # <>1__state
        self.compteur = 0; self.temps = F32(0.0); self.pas_temps = PAS_TEMPS; self.rot_acc = ROT_ACC; self.f_alpha = 4
        self.alpha_flou = F32(0.0); self.acc_flou = F32(0.0); self.alpha_capture = F32(0.0); self.acc_capture = F32(0.0)
        self.noir_final = False                                   # fin du depart : _Color des deux materiaux = (0, 0, 0, 0)

    # ------------------------------------------------------------------ un appel de MoveNext
    def _move_next(self):
        e = self.etat
        if e == 0:                                    # 0xCCAD34 : SetBlur(true), Snap()
            self._flou = True; self._capture = True; self.etat = 1
            return True
        if e == 1:                                    # 0xCCADCC : maillage (la grille est ecrite telle quelle par l'etat 2)
            self.etat = 2
            return True
        if e == 2:                                    # 0xCCAF80 : une fois la capture faite : mise en place, puis premiere image du tourbillon
            if self._capture: return True
            self._demarrer(); self._corps(); self.etat = 3
            return True
        if e == 3:                                    # 0xCCB0C0
            self.compteur += 1
            if self.compteur >= FIN_COMPTEUR:         # 0xCCB510
                if not self.inverse:                  # 0xCCB9A8 : les deux materiaux a (0, 0, 0, 0) : ecran noir ; rien n'est remis en etat (la camera du jeu reste coupee jusqu'a l'arrivee)
                    self.noir_final = True; self.etat = -1
                    return False
                self._flou = False; self.etat = 4     # 0xCCB530 : SetBlur(false), puis une image de plus
                return True
            self._corps()
            return True
        if e == 4:                                    # 0xCCB430 : Mesh.Clear, rendu coupe, camera du jeu reactivee : fin de l'arrivee
            self.rendu_actif = False; self.etat = -1
            return False
        return False

    def _demarrer(self):
        """Etat 2 (0xCCAFE8-0xCCBAF4) : rendu active, fond noir, camera du jeu coupee ; variables du depart ou de l'arrivee."""
        self.rendu_actif = True
        inv = self.inverse
        self.acc_flou = ACC_FLOU[inv]; self.alpha_flou = F32(0.0)
        self.alpha_capture = F32(F32(1.0) - self.acc_flou); self.acc_capture = ACC_CAPT_ALLER
        self.rot_acc = ROT_ACC; self.temps = F32(0.0); self.pas_temps = PAS_TEMPS; self.f_alpha = F_ALPHA[False]; self.compteur = 0
        if inv:                                       # 0xCCBA60
            self.temps = T0_RETOUR; self.pas_temps = PAS_TEMPS_RETOUR; self.compteur = COMPTEUR_RETOUR; self.f_alpha = F_ALPHA[True]
            self.alpha_capture = F32(0.0); self.acc_capture = ACC_CAPT_RETOUR

    def _corps(self):
        """Une image du tourbillon (0xCCB0DC-0xCCB3D8) : alphas des deux couches, puis sommets de la grille."""
        t = self.temps
        if self.compteur < self.f_alpha:              # montee des alphas (4 images)
            self.alpha_flou = F32(self.alpha_flou + self.acc_flou)
            self.alpha_capture = F32(self.alpha_capture + self.acc_capture)
        if (not self.inverse) and self.compteur >= DEBUT_DECROISSANCE:      # decroissance (depart seulement) : cAlpha = 0 des l'image 41, bAlpha 0,69 a l'image 60
            if self.alpha_flou > 0:
                self.alpha_flou = F32(self.alpha_flou + F32(t * K_DEC_FLOU))
                if self.alpha_flou < 0: self.alpha_flou = F32(0.0)
            if self.alpha_capture > 0:
                self.alpha_capture = F32(self.alpha_capture + F32(t * K_DEC_CAPT))
                if self.alpha_capture < 0: self.alpha_capture = F32(0.0)
        X = self._gx[None, :]; Y = self._gy[:, None]
        r = np.sqrt(Y * Y + X * X)                    # distance au centre
        d = R_COIN - r                                # 0 aux coins, 1,4142 au centre
        s12 = ((d * d) * t) * K_PINCE                 # pincement vers le centre
        angle = (t * self.rot_acc) + t * (d * self.rot_acc)
        zoom = F32(F32(t * K_ZOOM) + F32(1.0))        # 1 - t / 2
        xp = zoom * (X - X * s12); yp = zoom * (Y - Y * s12)
        xp = np.where(((X > 0) & (xp < 0)) | ((X < 0) & (xp > 0)), X * EPS, xp).astype(F32)      # un sommet qui changerait de cote du centre y est ramene (position x 1e-4)
        yp = np.where(((Y > 0) & (yp < 0)) | ((Y < 0) & (yp > 0)), Y * EPS, yp).astype(F32)
        a = np.asarray(angle, F32).astype(np.float64); s = np.sin(a).astype(F32); c = np.cos(a).astype(F32)      # sincosf de bionic, a 1 ulp pres
        self._vt[:, 0] = (c * xp - s * yp).reshape(-1)
        self._vt[:, 1] = (s * xp + c * yp).reshape(-1)
        self.temps = F32(t + self.pas_temps)

    # ------------------------------------------------------------------ dessin
    def dessins(self):
        if not self.rendu_actif: return []
        if self.noir_final: cf = cc = (0.0, 0.0, 0.0, 0.0)
        else: cf = (1.0, 1.0, 1.0, float(self.alpha_flou)); cc = (1.0, 1.0, 1.0, float(self.alpha_capture))
        return [('flou', self._pos_fond, self._uv_fond, np.tile(np.array(cf, F32), (6, 1))),
                ('capture', self._vt[self._tri], self._uv, np.tile(np.array(cc, F32), (len(self._tri), 1)))]
