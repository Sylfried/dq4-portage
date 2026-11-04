"""Effets d'ecran de la classe `Capture` de la couche Unity (paquet 34, valeur & 0xf = 3 : voyage / ailes de Chimere, 5 : lampe / Ranaruta, 6 : Riremito ; le 4, debut de combat, est dans combat/effet_combat.py).

Module pur (numpy seulement, rien de graphique) : constantes communes et squelette de la boucle de `Capture`. Chaque effet est une coroutine C# (`Capture.<Tabi>d__49`, `<DarkLamp>d__47`, `<Riremito>d__48`)
que `Capture.Caputer` fait avancer d'UN pas a chaque LateUpdate (30 Hz), dans cet ordre :
  1. si une capture est demandee (`Snap`) : la camera du jeu (sans l'interface) est rendue dans une texture, la « capture » ;
  2. si le flou est actif (`SetBlur(vrai)`) : la camera de l'interface rend l'etat de l'image PRECEDENTE (fond flou + maillage de l'effet) dans une texture de DEMI-resolution (deux textures en alternance) :
     c'est le fond flou de l'image courante, une remanence ;
  3. un appel de `MoveNext` (un pas : sommets et couleurs du maillage) ; quand la coroutine rend faux, le jeu abaisse le bit 1 de `Global.Flag` que le moteur attendait (`IsScreenEffectEnd`).
Les sommets sont en coordonnees d'ecran normalisees (-1..1 : les shaders `Custom/Capture` et `Custom/CaptureBlur` recopient la position dans `gl_Position`, sans matrice) ; le dessin est decrit par `dessins()` :
d'abord le fond (`Blend SrcAlpha Zero` : texture floue x couleur, remplace l'ecran), puis la capture (`Blend SrcAlpha OneMinusSrcAlpha`), sur un fond noir uni, la camera du jeu etant coupee.
Les durees ne dependent ni du hasard (aucun `Random`) ni d'une horloge : tout est fonction du nombre d'images. Les regles de chaque effet ont ete lues dans le desassemblage de libil2cpp (adresses en commentaire),
puis comparees au vrai code machine execute sous Unicorn (Tabi et lampe : sommets, couleurs, champs identiques au bit pres)."""
import math
import struct
import numpy as np

F32 = np.float32

GENRES = {3: 'tabi', 5: 'lampe', 6: 'riremito'}           # paquet 34 : valeur & 0xf -> effet (Capture.ScreenEffect, 0xCC6474)
IMAGES = {'tabi': 64, 'tabi_retour': 45, 'lampe': 64, 'riremito': 63}      # appels de MoveNext jusqu'a celui qui rend faux (le bit 1 retombe a cet appel)
APPEL_NOIR = {'lampe': 63, 'riremito': 62}                # appel (numerote a partir de 1) ou `Fade.SetFadeOutBlack(0)` rend l'ecran tout noir d'un coup (il le reste jusqu'au fondu d'entree lance par le moteur)
APPEL_FONDU_ENTRANT = 3                                   # voyage, arrivee : `Fade.SetFadeIn(30)` est lance a l'appel 3 (mise en place de l'effet)
FONDU_ENTRANT = 30                                        # images de ce fondu d'entree


def f32(bits):
    """Flottant 32 bits a partir de son motif binaire (les litteraux de libil2cpp, lus tels quels)."""
    return F32(struct.unpack('<f', struct.pack('<I', bits))[0])


def images_de(genre, inverse=False):
    """Nombre d'appels de MoveNext d'un effet (`inverse` : arrivee du voyage, bit 7 de la valeur du paquet)."""
    return IMAGES['tabi_retour' if genre == 'tabi' and inverse else genre]


def appels_faits(n, duree, images):
    """Appels de MoveNext faits quand l'effet a vecu `n` images du moteur (0 = celle ou le paquet est arrive : le premier appel a lieu la meme image). `duree` = images du moteur de l'effet
    (`images` quand « Vitesse de transition » est a x1, moins ensuite : l'effet est alors rejoue plus vite, comme la cascade du combat), `images` = ses appels d'origine."""
    return min(images, int(math.ceil((n + 1) * images / float(duree))))


class EffetCapture:
    """Squelette de `Capture` : la capture et la passe de flou sont faites par l'hote (fenetre), qui s'inscrit dans `sur_flou` ; les sous-classes donnent `_move_next` et `dessins`."""

    def __init__(self):
        self.images = 0               # appels de MoveNext deja faits
        self.fini = False             # MoveNext a rendu faux : le jeu a abaisse le bit 1 de Global.Flag
        self.rendu_actif = False      # MeshRenderer de l'objet Capture : tant qu'il est coupe, le jeu reste affiche normalement
        self.sur_flou = None          # rappel sur_flou(effet, indice) : « rendre dessins() (etat de l'image precedente) dans la texture de flou n° indice, de demi-resolution »
        self.flou_lu = None           # indice de la texture de flou que lit le fond de l'image courante ; None tant qu'aucune passe n'a eu lieu (texture noire)
        self.flou_ecrit = 0           # Capture.l_blurTexNum
        self._flou = False            # Capture.l_bBlur
        self._capture = False         # Capture.l_bCapture (Snap)

    def etape(self):
        """Un LateUpdate de `Capture` : capture (faite par l'hote avant le premier appel), passe de flou, un appel de MoveNext. Rend vrai tant que l'effet continue."""
        self._capture = False                 # Caputer : la capture est prise avant MoveNext de l'appel suivant (la fenetre l'a deja copiee)
        if self._flou:
            i = self.flou_ecrit
            if self.sur_flou: self.sur_flou(self, i)
            self.flou_lu = i; self.flou_ecrit = i ^ 1       # le fond lit la texture qui vient d'etre ecrite ; la premiere image fait une seconde passe dans l'autre texture, ecrasee avant d'etre lue : rien a faire
        suite = self._move_next()
        self.images += 1
        if not suite: self.fini = True
        return suite

    def _move_next(self):
        return False

    def dessins(self):
        """Liste de dessins (nom, positions (n, 2), uv (n, 2), rgba (n, 4)), dans l'ordre du jeu : 'flou' (fond, remplace l'ecran : texture de flou) puis 'capture' (melange alpha : texture de la capture).
        Triangles non indexes. Vide quand le MeshRenderer est coupe."""
        return []


def grille_triangles(colonnes, rangees):
    """Indices des triangles d'une grille de `colonnes` x `rangees` cases dont les sommets sont ranges rangee par rangee (colonnes + 1 par rangee) : (a, a+1, b) et (a+1, b+1, b), a = r * (colonnes + 1) + c, b = a + colonnes + 1
    (boucle 0xCCB71C de Tabi, 0xCC895C de la lampe : les deux ont le meme sens)."""
    nx = colonnes + 1
    a = (np.arange(rangees)[:, None] * nx + np.arange(colonnes)[None, :]).reshape(-1, 1)
    return (a + np.array([0, 1, nx, 1, nx + 1, nx])[None, :]).reshape(-1).astype(np.int32)


# les deux triangles du fond plein ecran (sommets : 0 haut gauche, 1 bas gauche, 2 haut droit, 3 bas droit) et ses uv
TRI_FOND = np.array([0, 2, 1, 2, 3, 1])
COIN_FOND = np.array([[-1, 1], [-1, -1], [1, 1], [1, -1]], F32)
UV_FOND = np.array([[0, 1], [0, 0], [1, 1], [1, 0]], F32)
