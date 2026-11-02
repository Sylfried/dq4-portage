"""Journal horodate du demarrage et des changements de carte (outil de diagnostic, sans effet hors test).

    DQ_SUIVI=1          : une ligne par evenement sur la console, « SUIVI +12.345s evenement cle=valeur ... » (temps depuis le lancement du programme)
    DQ_SUIVI=<fichier>  : la meme chose dans ce fichier (ajout)

Ce qui est note (voir fenetre.py et moteur.py) : creation de la fenetre, premieres images noires, affichage de la fenetre, images des logos, fin du chargement du moteur, premiere image du jeu, duree de chaque
chargement de carte (`_charger_carte`), image par image apres un changement de carte (ce qui est dessine : noir retenu ou scene, camera, personnages places, opacite des fondus), retenue du dessin
(`Etat.chargement`). Sans la variable d'environnement, chaque appel ne coute qu'un test de booleen."""
import os, time

_VAL = os.environ.get('DQ_SUIVI', '')
ACTIF = bool(_VAL) and _VAL != '0'
_FICHIER = _VAL if ACTIF and _VAL != '1' else None
_T0 = time.perf_counter()


def temps():
    """Secondes depuis le lancement du programme (horloge monotone)."""
    return time.perf_counter() - _T0


def noter(evenement, **champs):
    """Une ligne de journal (sans effet si DQ_SUIVI n'est pas defini)."""
    if not ACTIF: return
    ligne = 'SUIVI +%.3fs %s' % (temps(), evenement)
    if champs: ligne += ' ' + ' '.join('%s=%s' % (k, v) for k, v in champs.items())
    try:
        if _FICHIER:
            with open(_FICHIER, 'a') as f: f.write(ligne + '\n')
        else: print(ligne, flush=True)
    except Exception: pass


def arrondi(v, n=2):
    """Tuple de flottants arrondis pour le journal (None reste None)."""
    return None if v is None else tuple(round(float(x), n) for x in v)
