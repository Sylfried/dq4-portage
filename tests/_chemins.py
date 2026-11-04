"""Aide des tests : retrouver le code source apres le rangement du 04/11/2026 (dq4_pc est maintenant un paquet avec des sous-dossiers ; l'ancien fenetre.py est un dossier de modules)."""
import os

ICI = os.path.dirname(os.path.abspath(__file__))
RACINE = os.path.dirname(ICI)
CODE = os.path.join(RACINE, 'dq4_pc')
LOGIQUE_PURE = ('entrees.py', 'ecrans.py')          # modules de dq4_pc/fenetre qui ne faisaient pas partie de l'ancien fenetre.py


def trouver(nom):
    """Chemin du module `nom` (ex. 'pause.py') dans dq4_pc, quel que soit son sous-dossier."""
    for dossier, _, fichiers in os.walk(CODE):
        if '__pycache__' in dossier: continue
        if nom in fichiers: return os.path.join(dossier, nom)
    raise FileNotFoundError(nom)


def source(nom):
    """Texte du module `nom` ; 'fenetre.py' = tout l'ancien fichier : la classe Jeu, ses modules par theme, les constantes et les fonctions (dq4_pc/fenetre/*.py sauf les deux modules de logique pure)."""
    if nom == 'fenetre.py':
        dossier = os.path.join(CODE, 'fenetre'); morceaux = []
        for f in sorted(os.listdir(dossier)):
            if f.endswith('.py') and f not in LOGIQUE_PURE and f != '__init__.py':
                with open(os.path.join(dossier, f), encoding='utf-8') as fh: morceaux.append(fh.read())
        return '\n'.join(morceaux)
    with open(trouver(nom), encoding='utf-8') as fh: return fh.read()


def poser_global(nom, valeur):
    """Remplace la valeur du global `nom` dans tous les modules de dq4_pc.fenetre qui le portent (l'ancien fenetre.py etait un seul module : un `F.time = faux` agissait partout). -> fonction qui remet les anciennes valeurs."""
    import sys
    anciens = [(m, getattr(m, nom)) for n, m in list(sys.modules.items()) if n.startswith('dq4_pc.fenetre') and m is not None and hasattr(m, nom)]
    for m, _ in anciens: setattr(m, nom, valeur)
    def remettre():
        for m, v in anciens: setattr(m, nom, v)
    return remettre
