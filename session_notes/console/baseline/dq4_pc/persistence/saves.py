"""Export et import des fichiers de sauvegarde (bouton « Sauvegardes » du menu de depart, a la place de « Sauv. cloud »).

Ce qui s'exporte : les six fichiers du jeu (data1.dat a data3.dat = journaux, data4.dat = suspension, data5.dat = sauvegarde auto, data9.dat = journal le plus recent) tels que le moteur les lit
(le dossier d'ecriture d'abord, sinon celui de lecture) et les etats instantanes du portage (savestates/state_NN.dqs). Un fichier .zip les contient a plat (`data1.dat`, `savestates/state_01.dqs`).
Ce qui s'importe : un .zip de ce genre, ou des fichiers dataN.dat isoles (par exemple ceux copies depuis un telephone Android) ; les noms sont reconnus meme dans des sous-dossiers du .zip.
Rien n'est jamais ecrase sans copie : avant l'import, les fichiers du dossier d'ecriture qui vont etre remplaces sont copies dans `data\\saves\\before_import_<date>\\` ; les dossiers de lecture (tes sauvegardes d'origine) ne sont jamais modifies.
Les fichiers ne sont pas interpretes ici, seulement controles : taille (journal : 15 360 octets ; data9 : 512) et somme de controle d'un journal (logfile_format : un fichier abime ou qui n'est pas un journal du jeu est refuse, avec la raison, au lieu de donner une « banque vide » au chargement) ; chaque fichier est ecrit en entier ou pas du tout (fichier temporaire puis remplacement)."""
import glob
import os
import re
import shutil
import threading
import time
import zipfile

from dq4_pc import paths as CH
from dq4_pc.language import tr
from dq4_pc.persistence import logfile_format as FJ
from dq4_pc.persistence.write_dir import atomic_write

NAMES = CH.LOGFILE_NAMES
SIZES = {'data1.dat': 0x3c00, 'data2.dat': 0x3c00, 'data3.dat': 0x3c00, 'data4.dat': 0x3c00, 'data5.dat': 0x3c00, 'data9.dat': 512}
RE_LOGFILE = re.compile(r'(?:^|[\\/])(data[1-59]\.dat)$', re.I)
RE_SAVESTATE = re.compile(r'(?:^|[\\/])(?:savestates|etats)[\\/]((?:state|etat)_\d\d\.dqs)$', re.I)          # (D-239 : `etats/etat_NN.dqs` des .zip d'avant est reconnu aussi)
RE_SAVESTATE_ISOLATED = re.compile(r'^((?:state|etat)_\d\d\.dqs)$', re.I)


def savestate_name(name_str):
    """Le nom d'un etat instantane tel qu'il s'ecrit maintenant : `etat_03.dqs` (ancien nom) -> `state_03.dqs`."""
    return re.sub(r'^etat_', 'state_', name_str.lower())


def timestamp():
    return time.strftime('%Y%m%d_%H%M%S')


def effective_files(write_dir, read_dir):
    """Les fichiers de journaux que le moteur lit : {nom: chemin} (le dossier d'ecriture passe avant celui de lecture, comme GameCore.h_fopen)."""
    out = {}
    for name_str in NAMES:
        for d in (write_dir, read_dir):
            if d and os.path.isfile(os.path.join(d, name_str)): out[name_str] = os.path.join(d, name_str); break
    return out


def savestates(write_dir):
    """Etats instantanes du portage : {nom: chemin}."""
    return {os.path.basename(p): p for p in sorted(glob.glob(os.path.join(CH.FOLDERS.savestates_folder(write_dir), 'state_??.dqs')))}


def default_export_name():
    return 'dq4_saves_%s.zip' % timestamp()


def export_saves(write_dir, read_dir, destination):
    """Ecrit le .zip. -> (nombre de journaux, nombre d'etats). Leve ValueError s'il n'y a rien a exporter."""
    j = effective_files(write_dir, read_dir); e = savestates(write_dir)
    if not j and not e: raise ValueError(tr("Aucune sauvegarde a exporter (ni journal, ni etat instantane)."))
    folder = os.path.dirname(os.path.abspath(destination))
    if folder: os.makedirs(folder, exist_ok=True)
    tmp = destination + '.tmp'
    with zipfile.ZipFile(tmp, 'w', zipfile.ZIP_DEFLATED) as z:
        for name_str, p in j.items(): z.write(p, name_str)
        for name_str, p in e.items(): z.write(p, 'savestates/' + name_str)
    os.replace(tmp, destination)
    return len(j), len(e)


def read_sources(paths):
    """Fichiers a importer : -> ({nom de journal: octets}, {nom d'etat: octets}, [problemes]). Chemins : .zip, dossiers (journaux / etats a l'interieur) ou fichiers isoles."""
    jr, label, pb = {}, {}, []

    def add(full_name, read, origin):
        m = RE_LOGFILE.search(full_name)
        if m:
            name_str = m.group(1).lower(); d = read()
            if len(d) != SIZES[name_str]: pb.append(tr('%s : taille %d au lieu de %d (%s)') % (name_str, len(d), SIZES[name_str], origin)); return
            reason = FJ.check(name_str, d)
            if reason: pb.append(tr('%s : %s (%s)') % (name_str, reason, origin)); return
            jr[name_str] = d; return
        m = RE_SAVESTATE.search(full_name) or RE_SAVESTATE_ISOLATED.match(os.path.basename(full_name))
        if m:
            d = read()
            if len(d) < 1024: pb.append(tr('%s : fichier trop petit (%s)') % (savestate_name(m.group(1)), origin)); return
            label[savestate_name(m.group(1))] = d

    for c in paths:
        if os.path.isdir(c):
            for root, _, files in os.walk(c):
                for f in files:
                    p = os.path.join(root, f); add(os.path.relpath(p, c), lambda p=p: open(p, 'rb').read(), c)
        elif c.lower().endswith('.zip'):
            try:
                with zipfile.ZipFile(c) as z:
                    for i in z.infolist():
                        if not i.is_dir() and i.file_size < 64 * 1024 * 1024: add(i.filename, lambda i=i, z=z: z.read(i), os.path.basename(c))
            except zipfile.BadZipFile: pb.append(tr("%s : ce n'est pas un .zip valide") % os.path.basename(c))
        else: add(os.path.basename(c), lambda c=c: open(c, 'rb').read(), os.path.dirname(c))
    return jr, label, pb


def import_saves(paths, write_dir, read_dir):
    """Copie les journaux / etats trouves dans le dossier d'ecriture, apres avoir copie ceux qu'ils remplacent dans `before_import_<date>`. -> (nb journaux, nb etats, dossier de copie ou None, problemes).
    Leve ValueError si rien d'utilisable n'a ete trouve."""
    jr, label, pb = read_sources(paths)
    if not jr and not label: raise ValueError(tr('Aucun fichier de sauvegarde reconnu (%s).') % ('; '.join(pb) if pb else tr('data1.dat a data5.dat, data9.dat ou savestates/state_NN.dqs attendus')))
    os.makedirs(write_dir, exist_ok=True)
    savestates_folder = CH.FOLDERS.savestates_folder(write_dir)
    copied = os.path.join(CH.FOLDERS.clones_folder(write_dir), 'before_import_' + timestamp()); n_clone = 0
    existing = {name_str: os.path.join(write_dir, name_str) for name_str in NAMES if os.path.isfile(os.path.join(write_dir, name_str))}        # (le dossier de lecture n'est jamais modifie : ses fichiers restent intacts, inutile de les copier)
    for name_str in jr:
        if name_str in existing:
            os.makedirs(copied, exist_ok=True); shutil.copy2(existing[name_str], os.path.join(copied, name_str)); n_clone += 1
    for name_str in label:
        p = os.path.join(savestates_folder, name_str)
        if os.path.isfile(p):
            os.makedirs(os.path.join(copied, 'savestates'), exist_ok=True); shutil.copy2(p, os.path.join(copied, 'savestates', name_str)); n_clone += 1
    written_j = written_e = 0
    for name_str, d in jr.items():
        ex = atomic_write(os.path.join(write_dir, name_str), d)
        if ex is None: written_j += 1
        else: pb.append(tr('%s : ecriture impossible (%s) ; le fichier actuel est inchange') % (name_str, ex))
    for name_str, d in label.items():
        ex = atomic_write(os.path.join(savestates_folder, name_str), d)
        if ex is None: written_e += 1
        else: pb.append(tr('%s : ecriture impossible (%s) ; le fichier actuel est inchange') % (name_str, ex))
    if not written_j and not written_e: raise ValueError(tr("Aucun fichier n'a pu etre ecrit (%s).") % '; '.join(pb))
    return written_j, written_e, (copied if n_clone else None), pb


# ---- boites de dialogue de fichiers (tkinter, dans un fil a part pour que la fenetre du jeu reste vivante)
class Dialogue:
    """Une boite « Enregistrer sous » ou « Ouvrir » ; `result` reste None tant qu'elle est ouverte, puis liste de chemins (vide = annule) ; `unavailable` vrai sans tkinter."""
    def __init__(self, mode, title_screen, initial_folder=None, initial_name=None):
        self.result = None; self.unavailable = False; self.error = None
        threading.Thread(target=self._body, args=(mode, title_screen, initial_folder, initial_name), daemon=True, name='dialogue').start()

    def _body(self, mode, title_screen, folder, name_str):
        try:
            import tkinter as tk
            from tkinter import filedialog
        except Exception as ex:
            self.unavailable = True; self.error = repr(ex); self.result = []; return
        root = None
        try:
            root = tk.Tk(); root.withdraw()
            try: root.attributes('-topmost', True)
            except Exception: pass
            kw = dict(parent=root, title=title_screen)
            if folder and os.path.isdir(folder): kw['initialdir'] = folder
            if mode == 'enregistrer':
                p = filedialog.asksaveasfilename(defaultextension='.zip', filetypes=[(tr('Archive zip'), '*.zip')], initialfile=name_str or default_export_name(), **kw)
                self.result = [p] if p else []
            else:
                ps = filedialog.askopenfilenames(filetypes=[(tr('Sauvegardes (zip, data*.dat, state_*.dqs)'), '*.zip *.dat *.dqs'), (tr('Tous les fichiers'), '*.*')], **kw)
                self.result = list(ps) if ps else []
        except Exception as ex:
            self.unavailable = True; self.error = repr(ex); self.result = []
        finally:
            try:
                if root is not None: root.destroy()
            except Exception: pass
