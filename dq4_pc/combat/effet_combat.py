"""Effet de debut de combat (Capture.BattleEffect de la couche Unity) : une capture de l'ecran, decoupee en 32 colonnes de morceaux, se brise et tombe
rangee apres rangee, du haut vers le bas, puis s'assombrit jusqu'au noir.

Reproduit les regles du jeu, une mise a jour par image (30 Hz) :
  * deux compteurs : A (0, 1, 2...) et B (0 jusqu'a l'image 21, puis il suit A avec 20 images de retard) ; a chaque image et pour chaque morceau, le jeu tire
    au hasard (1 chance sur 3 pour B) le compteur qui commande ce morceau ;
  * un morceau de la rangee r bouge si l'un des deux compteurs depasse r ; la vitesse de chute est -0,001953125 - (32 - r - colonne + compteur) * 0,0015625
    (en coordonnees d'ecran normalisees, -1..1), la moitie quand c'est le compteur « de retard » qui l'a fait bouger ; les bords gauche et droit se rapprochent
    d'environ 0,001 par image (le morceau s'etrecit) et le morceau derive de 0,002 vers la gauche ;
  * l'opacite d'un morceau perd 8/255 par image de mouvement ;
  * quand A depasse la moitie de la hauteur, la luminosite de la capture baisse de 2/56 par image ; l'effet s'arrete quand A depasse 56.
Le jeu d'origine decoupe l'ecran portrait en 32 x 56 morceaux carres (56 = 32 / 0,5625). Sur un ecran 16/9 on garde des morceaux carres (32 x 18) et chaque rangee
prend la place de 56 / 18 rangees d'origine, donc le deroulement dans le temps (57 images) est le meme."""
import numpy as np

COLS = 32
DIV_Y = 56                 # int(32 / ASPECT_DEF) de l'original : fixe la duree de l'effet
IMAGES = DIV_Y + 1         # nombre de mises a jour avant la fin (A de 0 a 56)
DERIVE = -0.001953125
G_VITESSE = -0.0015625
CISAILLE = 0.001
# sommets d'un morceau : 0 haut gauche, 1 bas gauche, 2 haut droit, 3 bas droit -> deux triangles
TRI = np.array([0, 1, 2, 2, 1, 3])


class EffetTuiles:
    def __init__(self, aspect, graine=1234):
        self.rows = max(4, int(COLS / max(aspect, 0.1)))
        R, C = self.rows, COLS
        self.rng = np.random.default_rng(graine)
        self.k = DIV_Y / float(R)                                   # rangees d'origine par rangee affichee
        self.ligne = (np.arange(R) * self.k)[:, None]               # numero de rangee d'origine (flottant)
        self.col = np.arange(C)[None, :]
        x0 = -1.0 + np.arange(C) * (2.0 / C); x1 = x0 + 2.0 / C
        yh = 1.0 - np.arange(R) * (2.0 / R); yb = yh - 2.0 / R
        P = np.empty((R, C, 4, 2), np.float32)
        P[..., 0, 0] = x0[None, :]; P[..., 1, 0] = x0[None, :]; P[..., 2, 0] = x1[None, :]; P[..., 3, 0] = x1[None, :]
        P[..., 0, 1] = yh[:, None]; P[..., 2, 1] = yh[:, None]; P[..., 1, 1] = yb[:, None]; P[..., 3, 1] = yb[:, None]
        self.P = P; self.dec = np.zeros_like(P)
        u0 = np.arange(C) / float(C); u1 = u0 + 1.0 / C
        vh = 1.0 - np.arange(R) / float(R); vb = vh - 1.0 / R
        UV = np.empty((R, C, 4, 2), np.float32)
        UV[..., 0, 0] = u0[None, :]; UV[..., 1, 0] = u0[None, :]; UV[..., 2, 0] = u1[None, :]; UV[..., 3, 0] = u1[None, :]
        UV[..., 0, 1] = vh[:, None]; UV[..., 2, 1] = vh[:, None]; UV[..., 1, 1] = vb[:, None]; UV[..., 3, 1] = vb[:, None]
        self.UV = UV[:, :, TRI, :].reshape(-1, 2)
        self.alpha = np.full((R, C), 255, np.int32)
        self.A = 0; self.B = 0; self.lum = 1.0

    @property
    def images(self):
        return self.A

    def etape(self):
        """Une mise a jour (une image du jeu)."""
        R, C = self.rows, COLS; A, B = self.A, self.B
        sur_b = self.rng.integers(0, 3, size=(R, C)) == 0
        choisi = np.where(sur_b, B, A).astype(np.float64); autre = np.where(sur_b, A, B).astype(np.float64)
        plein = choisi > self.ligne
        actif = plein | (autre > self.ligne)
        dy = DERIVE + ((32.0 - self.ligne - self.col) + choisi) * G_VITESSE
        sh = np.sin((choisi * 120.0 + 49152.0) / 65535.0) * CISAILLE
        dy = np.where(plein, dy, dy * 0.5); sh = np.where(plein, sh, sh * 0.5)
        dx_g = np.where(actif, sh + DERIVE, 0.0); dx_d = np.where(actif, DERIVE - sh, 0.0); dy = np.where(actif, dy, 0.0)
        self.dec[:, :, 0, 0] += dx_g; self.dec[:, :, 1, 0] += dx_g; self.dec[:, :, 2, 0] += dx_d; self.dec[:, :, 3, 0] += dx_d
        self.dec[:, :, :, 1] += dy[:, :, None]
        a = self.alpha
        bas = actif & (a > 0) & (a <= 7); haut = actif & (a > 7)
        a[haut] -= 8; a[bas] = 0
        self.A += 1
        if self.A >= 21: self.B += 1
        if self.A > DIV_Y // 2: self.lum = max(self.lum - 2.0 / DIV_Y, 0.0)

    @property
    def fini(self):
        return self.A > DIV_Y

    def positions(self):
        return (self.P + self.dec)[:, :, TRI, :].reshape(-1, 2)

    def couleurs(self):
        """Un RGBA par sommet : blanc, opacite du morceau."""
        a = np.clip(self.alpha, 0, 255).astype(np.float32) / 255.0
        c = np.ones((self.rows, COLS, 6, 4), np.float32); c[..., 3] = a[:, :, None]
        return c.reshape(-1, 4)
