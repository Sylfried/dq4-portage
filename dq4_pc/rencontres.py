"""Rencontres aleatoires et vitesse de marche (#45).

Ce que fait le jeu d'origine (lu au desassemblage de libdq4core.so) :
  - Chaque image du moteur ou la position du heros a change (carte du monde : FieldPlayerDoku::checkDokuDamage ; villes et donjons : TownDamageFloor::checkDamageFloor, tous deux par
    CommonWalkDamage::checkWalk) appelle `Encount::execWalk`. Il compte 16 appels, puis lance `Encount::exec` (une fois, ou cinq fois quand [+0x2c] est non nul).
  - `Encount::exec` appelle `CountDown::exec` (0x1f454c) : le compteur [Encount+0x134] perd `2 x [Encount+0x144]` ; la rencontre est declenchee quand il devient negatif (etat [+0x1c] : 0 -> 1 -> 2, puis `brew`
    et `Global::startBattle`). Le compteur est tire par `CountDown::setup` (0x1e00 + table[rand(31)]) a chaque initialisation de la carte (`Encount::setup`, donc aussi au retour d'un combat) ;
    sa perte par appel (`[+0x144]`) vient de `TileSubtractValue[tuile] x table du terrain >> 8` (setTileIdRate / setLandType, recalcules a chaque `exec`).
  - Rien de tout cela ne depend du temps reel : le jeu compte des IMAGES DU MOTEUR ou le heros avance (donc des pas).

Ce que fait la visionneuse : la marche acceleree (« Vitesse de marche », accelerateur) fait tourner le moteur `a` fois plus vite, donc le heros fait `a` fois plus de pas par seconde reelle, et, sans correction,
`a` fois plus de rencontres par seconde. On veut (1 + a) / 2 : x1 inchange, x2 = 1,5 fois, x3 = 2 fois, x4 = 2,5 fois (la marche accelere sans que les combats deviennent insupportables). Chaque pas compte donc
(1 + a) / (2 a) fois ce qu'il comptait : `facteur_par_pas`. La correction est faite sur le compteur du moteur lui-meme (un crochet sur l'ecriture de `CountDown::exec`, voir Moteur._crochets_rencontres),
pas par un tirage supplementaire : la perte du compteur a chaque appel est multipliee par ce facteur (fractions cumulees : `Reducteur`), la distribution des groupes de monstres, le tirage du compteur et tout le
reste restent ceux du jeu. Seulement quand a > 1 (x1 : le crochet ne fait rien).
"""


def facteur_par_pas(a):
    """Part de la perte du compteur de rencontres qui reste appliquee a chaque pas quand le moteur tourne a la vitesse `a` (1 = normale) : (1 + a) / (2 a) si a > 1, sinon 1 (jamais plus que le jeu)."""
    a = float(a)
    return 1.0 if a <= 1.0 else (1.0 + a) / (2.0 * a)


def rencontres_par_seconde(a):
    """Rencontres par seconde reelle, en multiples de celles de x1, a la vitesse `a` : a x facteur_par_pas(a) = (1 + a) / 2 pour a > 1."""
    return float(a) * facteur_par_pas(a)


class Reducteur:
    """Multiplie la perte du compteur par `facteur` (0 a 1), avec report des fractions : la somme des pertes appliquees est, a une unite pres, `facteur` x la somme des pertes du jeu."""

    def __init__(self, facteur=1.0):
        self.facteur = facteur; self.reste = 0.0

    def retenir(self, perte):
        """Perte (entier >= 0) du compteur du jeu pour cet appel -> perte a appliquer."""
        if self.facteur >= 1.0 or perte <= 0: return perte
        self.reste += perte * self.facteur
        n = int(self.reste); self.reste -= n
        return n
