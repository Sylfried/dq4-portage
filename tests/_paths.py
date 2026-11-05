"""Aide des tests : retrouver le code source apres le rangement du 04/11/2026 (dq4_pc est maintenant un paquet avec des sous-dossiers ; l'ancien window.py est un dossier de modules)."""
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CODE = os.path.join(ROOT, 'dq4_pc')
PURE_LOGIC = ('inputs.py', 'screens.py')          # modules de dq4_pc/fenetre qui ne faisaient pas partie de l'ancien window.py


def find_file(name_str):
    """Chemin du module `name_str` (ex. 'pause.py') dans dq4_pc, quel que soit son sous-dossier."""
    for folder, _, files in os.walk(CODE):
        if '__pycache__' in folder: continue
        if name_str in files: return os.path.join(folder, name_str)
    raise FileNotFoundError(name_str)


def source(name_str):
    """Texte du module `name_str` ; 'window.py' = tout l'ancien fichier : la classe Jeu, ses modules par theme, les constantes et les fonctions (dq4_pc/window/*.py sauf les deux modules de logique pure)."""
    if name_str == 'window.py':
        folder = os.path.join(CODE, 'window'); chunks = []
        for f in sorted(os.listdir(folder)):
            if f.endswith('.py') and f not in PURE_LOGIC and f != '__init__.py':
                with open(os.path.join(folder, f), encoding='utf-8') as fh: chunks.append(fh.read())
        return '\n'.join(chunks)
    with open(find_file(name_str), encoding='utf-8') as fh: return fh.read()


def set_global(name_str, value):
    """Remplace la valeur du global `name_str` dans tous les modules de dq4_pc.window qui le portent (l'ancien window.py etait un seul module : un `F.time = fake` agissait partout). -> fonction qui remet les anciennes valeurs."""
    import sys
    old_dirs = [(m, getattr(m, name_str)) for n, m in list(sys.modules.items()) if n.startswith('dq4_pc.window') and m is not None and hasattr(m, name_str)]
    for m, _ in old_dirs: setattr(m, name_str, value)
    def reset():
        for m, v in old_dirs: setattr(m, name_str, v)
    return reset
