"""Ecriture de fichier sans jamais en laisser un a moitie ecrit (sauvegardes du jeu, import de sauvegardes)."""
import os
import time


def ecrire_atomique(chemin, octets, essais=2, pause=0.25):
    """Ecrit `octets` dans `chemin` : fichier temporaire a cote puis remplacement d'un coup (jamais de fichier a moitie ecrit) ; en cas d'erreur d'E/S (antivirus qui verrouille le fichier, disque plein, dossier en
    lecture seule) le tout est retente `essais` fois, espacees de `pause` s. -> None si tout va bien, sinon l'exception de la derniere tentative ; l'ancien fichier reste alors intact."""
    dernier = None
    for i in range(max(1, essais)):
        tmp = chemin + '.tmp'
        try:
            os.makedirs(os.path.dirname(chemin), exist_ok=True)
            with open(tmp, 'wb') as fh: fh.write(octets); fh.flush(); os.fsync(fh.fileno())
            os.replace(tmp, chemin); return None
        except OSError as ex:
            dernier = ex
            try: os.remove(tmp)
            except OSError: pass
            if i + 1 < essais: time.sleep(pause)
    return dernier
