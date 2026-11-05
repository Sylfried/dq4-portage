"""Ecriture de fichier sans jamais en laisser un a moitie ecrit (sauvegardes du jeu, import de sauvegardes)."""
import os
import time


def atomic_write(path, raw, attempts=2, pause=0.25):
    """Ecrit `raw` dans `path` : fichier temporaire a cote puis remplacement d'un coup (jamais de fichier a moitie ecrit) ; en cas d'erreur d'E/S (antivirus qui verrouille le fichier, disque plein, dossier en
    lecture seule) le tout est retente `attempts` fois, espacees de `pause` s. -> None si tout va bien, sinon l'exception de la derniere tentative ; l'ancien fichier reste alors intact."""
    last = None
    for i in range(max(1, attempts)):
        tmp = path + '.tmp'
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(tmp, 'wb') as fh: fh.write(raw); fh.flush(); os.fsync(fh.fileno())
            os.replace(tmp, path); return None
        except OSError as ex:
            last = ex
            try: os.remove(tmp)
            except OSError: pass
            if i + 1 < attempts: time.sleep(pause)
    return last
