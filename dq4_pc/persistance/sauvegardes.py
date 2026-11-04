"""Export et import des fichiers de sauvegarde (bouton « Sauvegardes » du menu de depart, a la place de « Sauv. cloud »).

Ce qui s'exporte : les six fichiers du jeu (data1.dat a data3.dat = journaux, data4.dat = suspension, data5.dat = sauvegarde auto, data9.dat = journal le plus recent) tels que le moteur les lit
(le dossier d'ecriture d'abord, sinon celui de lecture) et les etats instantanes du portage (etats/etat_NN.dqs). Un fichier .zip les contient a plat (`data1.dat`, `etats/etat_01.dqs`).
Ce qui s'importe : un .zip de ce genre, ou des fichiers dataN.dat isoles (par exemple ceux copies depuis un telephone Android) ; les noms sont reconnus meme dans des sous-dossiers du .zip.
Rien n'est jamais ecrase sans copie : avant l'import, les fichiers du dossier d'ecriture qui vont etre remplaces sont copies dans `donnees\\sauvegardes\\avant_import_<date>\\` ; les dossiers de lecture (tes sauvegardes d'origine) ne sont jamais modifies.
Les fichiers ne sont pas interpretes ici, seulement controles : taille (journal : 15 360 octets ; data9 : 512) et somme de controle d'un journal (format_journal : un fichier abime ou qui n'est pas un journal du jeu est refuse, avec la raison, au lieu de donner une « banque vide » au chargement) ; chaque fichier est ecrit en entier ou pas du tout (fichier temporaire puis remplacement)."""
import glob
import os
import re
import shutil
import threading
import time
import zipfile

from dq4_pc import chemins as CH
from dq4_pc.persistance import format_journal as FJ
from dq4_pc.persistance.ecriture import ecrire_atomique

NOMS = CH.NOMS_JOURNAUX
TAILLES = {'data1.dat': 0x3c00, 'data2.dat': 0x3c00, 'data3.dat': 0x3c00, 'data4.dat': 0x3c00, 'data5.dat': 0x3c00, 'data9.dat': 512}
RE_JOURNAL = re.compile(r'(?:^|[\\/])(data[1-59]\.dat)$', re.I)
RE_ETAT = re.compile(r'(?:^|[\\/])etats[\\/](etat_\d\d\.dqs)$', re.I)
RE_ETAT_ISOLE = re.compile(r'^(etat_\d\d\.dqs)$', re.I)


def horodatage():
    return time.strftime('%Y%m%d_%H%M%S')


def fichiers_effectifs(ecriture, lecture):
    """Les fichiers de journaux que le moteur lit : {nom: chemin} (le dossier d'ecriture passe avant celui de lecture, comme CoreJeu.h_fopen)."""
    out = {}
    for nom in NOMS:
        for d in (ecriture, lecture):
            if d and os.path.isfile(os.path.join(d, nom)): out[nom] = os.path.join(d, nom); break
    return out


def etats(ecriture):
    """Etats instantanes du portage : {nom: chemin}."""
    return {os.path.basename(p): p for p in sorted(glob.glob(os.path.join(CH.DOSSIERS.dossier_etats(ecriture), 'etat_??.dqs')))}


def nom_export_par_defaut():
    return 'dq4_sauvegardes_%s.zip' % horodatage()


def exporter(ecriture, lecture, destination):
    """Ecrit le .zip. -> (nombre de journaux, nombre d'etats). Leve ValueError s'il n'y a rien a exporter."""
    j = fichiers_effectifs(ecriture, lecture); e = etats(ecriture)
    if not j and not e: raise ValueError("Aucune sauvegarde a exporter (ni journal, ni etat instantane).")
    dossier = os.path.dirname(os.path.abspath(destination))
    if dossier: os.makedirs(dossier, exist_ok=True)
    tmp = destination + '.tmp'
    with zipfile.ZipFile(tmp, 'w', zipfile.ZIP_DEFLATED) as z:
        for nom, p in j.items(): z.write(p, nom)
        for nom, p in e.items(): z.write(p, 'etats/' + nom)
    os.replace(tmp, destination)
    return len(j), len(e)


def lire_sources(chemins):
    """Fichiers a importer : -> ({nom de journal: octets}, {nom d'etat: octets}, [problemes]). Chemins : .zip, dossiers (journaux / etats a l'interieur) ou fichiers isoles."""
    jr, et, pb = {}, {}, []

    def ajouter(nom_complet, lire, origine):
        m = RE_JOURNAL.search(nom_complet)
        if m:
            nom = m.group(1).lower(); d = lire()
            if len(d) != TAILLES[nom]: pb.append('%s : taille %d au lieu de %d (%s)' % (nom, len(d), TAILLES[nom], origine)); return
            raison = FJ.verifier(nom, d)
            if raison: pb.append('%s : %s (%s)' % (nom, raison, origine)); return
            jr[nom] = d; return
        m = RE_ETAT.search(nom_complet) or RE_ETAT_ISOLE.match(os.path.basename(nom_complet))
        if m:
            d = lire()
            if len(d) < 1024: pb.append('%s : fichier trop petit (%s)' % (m.group(1), origine)); return
            et[m.group(1).lower()] = d

    for c in chemins:
        if os.path.isdir(c):
            for racine, _, fichiers in os.walk(c):
                for f in fichiers:
                    p = os.path.join(racine, f); ajouter(os.path.relpath(p, c), lambda p=p: open(p, 'rb').read(), c)
        elif c.lower().endswith('.zip'):
            try:
                with zipfile.ZipFile(c) as z:
                    for i in z.infolist():
                        if not i.is_dir() and i.file_size < 64 * 1024 * 1024: ajouter(i.filename, lambda i=i, z=z: z.read(i), os.path.basename(c))
            except zipfile.BadZipFile: pb.append('%s : ce n\'est pas un .zip valide' % os.path.basename(c))
        else: ajouter(os.path.basename(c), lambda c=c: open(c, 'rb').read(), os.path.dirname(c))
    return jr, et, pb


def importer(chemins, ecriture, lecture):
    """Copie les journaux / etats trouves dans le dossier d'ecriture, apres avoir copie ceux qu'ils remplacent dans `avant_import_<date>`. -> (nb journaux, nb etats, dossier de copie ou None, problemes).
    Leve ValueError si rien d'utilisable n'a ete trouve."""
    jr, et, pb = lire_sources(chemins)
    if not jr and not et: raise ValueError('Aucun fichier de sauvegarde reconnu (%s).' % ('; '.join(pb) if pb else 'data1.dat a data5.dat, data9.dat ou etats/etat_NN.dqs attendus'))
    os.makedirs(ecriture, exist_ok=True)
    dossier_etats = CH.DOSSIERS.dossier_etats(ecriture)
    copie = os.path.join(CH.DOSSIERS.dossier_copies(ecriture), 'avant_import_' + horodatage()); n_copie = 0
    actuels = {nom: os.path.join(ecriture, nom) for nom in NOMS if os.path.isfile(os.path.join(ecriture, nom))}        # (le dossier de lecture n'est jamais modifie : ses fichiers restent intacts, inutile de les copier)
    for nom in jr:
        if nom in actuels:
            os.makedirs(copie, exist_ok=True); shutil.copy2(actuels[nom], os.path.join(copie, nom)); n_copie += 1
    for nom in et:
        p = os.path.join(dossier_etats, nom)
        if os.path.isfile(p):
            os.makedirs(os.path.join(copie, 'etats'), exist_ok=True); shutil.copy2(p, os.path.join(copie, 'etats', nom)); n_copie += 1
    ecrits_j = ecrits_e = 0
    for nom, d in jr.items():
        ex = ecrire_atomique(os.path.join(ecriture, nom), d)
        if ex is None: ecrits_j += 1
        else: pb.append('%s : ecriture impossible (%s) ; le fichier actuel est inchange' % (nom, ex))
    for nom, d in et.items():
        ex = ecrire_atomique(os.path.join(dossier_etats, nom), d)
        if ex is None: ecrits_e += 1
        else: pb.append('%s : ecriture impossible (%s) ; le fichier actuel est inchange' % (nom, ex))
    if not ecrits_j and not ecrits_e: raise ValueError('Aucun fichier n\'a pu etre ecrit (%s).' % '; '.join(pb))
    return ecrits_j, ecrits_e, (copie if n_copie else None), pb


# ---- boites de dialogue de fichiers (tkinter, dans un fil a part pour que la fenetre du jeu reste vivante)
class Dialogue:
    """Une boite « Enregistrer sous » ou « Ouvrir » ; `resultat` reste None tant qu'elle est ouverte, puis liste de chemins (vide = annule) ; `indisponible` vrai sans tkinter."""
    def __init__(self, mode, titre, initial_dossier=None, initial_nom=None):
        self.resultat = None; self.indisponible = False; self.erreur = None
        threading.Thread(target=self._corps, args=(mode, titre, initial_dossier, initial_nom), daemon=True, name='dialogue').start()

    def _corps(self, mode, titre, dossier, nom):
        try:
            import tkinter as tk
            from tkinter import filedialog
        except Exception as ex:
            self.indisponible = True; self.erreur = repr(ex); self.resultat = []; return
        racine = None
        try:
            racine = tk.Tk(); racine.withdraw()
            try: racine.attributes('-topmost', True)
            except Exception: pass
            kw = dict(parent=racine, title=titre)
            if dossier and os.path.isdir(dossier): kw['initialdir'] = dossier
            if mode == 'enregistrer':
                p = filedialog.asksaveasfilename(defaultextension='.zip', filetypes=[('Archive zip', '*.zip')], initialfile=nom or nom_export_par_defaut(), **kw)
                self.resultat = [p] if p else []
            else:
                ps = filedialog.askopenfilenames(filetypes=[('Sauvegardes (zip, data*.dat, etat_*.dqs)', '*.zip *.dat *.dqs'), ('Tous les fichiers', '*.*')], **kw)
                self.resultat = list(ps) if ps else []
        except Exception as ex:
            self.indisponible = True; self.erreur = repr(ex); self.resultat = []
        finally:
            try:
                if racine is not None: racine.destroy()
            except Exception: pass
