"""Effets de combat faits d'un quad plein ecran (teinte, flash) : calles sur l'ecran 4:3 du jeu d'origine, donc trop etroits quand le combat est elargi en 16/9 (#223, audit CMB-02)."""
import numpy as np

# Modeles d'effets (5000 + numero de l'effet) dont le quad couvre tout le champ 4:3 : l'effet 35 (paquet 25, quad de 12,9 x 12,9 : une teinte violette sur tout l'ecran). Les autres quads larges (l'effet 9, 7 unites) sont
# plus grands que le champ et restent corrects ; ajouter ici un modele seulement apres l'avoir vu a cote d'une bande non teintee.
MODELES_PLEIN_ECRAN = frozenset({5035})
ASPECT_ORIGINE = 4.0 / 3.0          # le quad a ete dessine pour cet ecran


def elargir(loc, modele, aspect):
    """Coordonnees locales (n x 3, axe 0 = horizontal de l'ecran) d'un maillage de combat : celles d'un quad plein ecran sont etirees en largeur de aspect / (4/3) autour de leur centre, pour couvrir tout l'ecran large. Les
    autres maillages, et un ecran de proportions 4:3 ou plus etroites, sont rendus tels quels (meme objet). -> coordonnees a utiliser."""
    if modele not in MODELES_PLEIN_ECRAN or aspect <= ASPECT_ORIGINE: return loc
    loc = np.array(loc, np.float32, copy=True)
    if len(loc) == 0: return loc
    c = (float(loc[:, 0].min()) + float(loc[:, 0].max())) / 2.0
    loc[:, 0] = c + (loc[:, 0] - c) * np.float32(aspect / ASPECT_ORIGINE)
    return loc
