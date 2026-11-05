"""Tous les dossiers et fichiers du portage, en un seul endroit (rangement du 04/11/2026).

Tout ce qui t'appartient (APK, sauvegardes, caches, reglages) est dans UN dossier, `data\\`, a la racine du projet ; il n'est jamais envoye sur GitHub (.gitignore) :

    donnees\\
      apk\\                      les 3 APK francais (base.apk, split_config.arm64_v8a.apk, split_UnityDataAssetPack.apk)
      sauvegardes\\            UN SEUL dossier (D-232) : le contenu exact du .zip d'export, pour copier d'un coup les sauvegardes du telephone
        data1.dat ... data5.dat, data9.dat   les journaux du jeu (lus et ecrits par le moteur ; ceux du telephone se copient ici)
        etats\\                les etats instantanes (etat_01.dqs ...)
        avant_import_<date>\\    copies de securite faites avant chaque import de sauvegardes
        avant_rangement_<date>\\ anciens dossiers `portage\\` et `mobile\\` rangés tels quels par la reprise (voir `migrate`) : sans danger a effacer une fois la partie verifiee
      cache\\                    ce que le portage calcule a partir des APK (cartes, sprites, sons, menus) : sans danger a effacer
      reglages\\                 reglages.json, historique_favoris.json, historique_messages.json
      journaux\\                 erreurs_fenetre.log
      reprise.json               les etapes de la reprise de l'ancienne disposition deja faites (D-235)

Deux variables d'environnement, pour les tests et les installations particulieres :
  DQ4_DONNEES : un autre emplacement pour tout le dossier `data`.
  DQ4_JEUX    : (ancien fonctionnement) un dossier « jeux\\DQ4 » contenant `patched_apks` et `saves\\<date>` ; il remplace `data\\apk`, et `saves\\<date>` reste une copie LUE SEULEMENT de sauvegardes (tests, installations particulieres).

`migrate()` reprend l'ancienne disposition (jeux\\DQ4, dq4_pc\\cache, dq4_pc\\sauvegardes, dq4_pc\\reglages.json ...) : elle COPIE (ou, pour le cache seulement, deplace) vers la nouvelle,
sans jamais ecraser un fichier deja present et sans rien supprimer. Chaque reprise n'a lieu QU'UNE FOIS (D-235) : `data\\resume.json` note les etapes faites, pour que ce que tu effaces dans `data\\`
(un dossier `avant_import_...`, un journal, des reglages) ne soit pas recopie depuis l'ancien dossier au demarrage suivant. Une disposition deja en service (journaux, etats, reglages ou cache dans `data\\`) compte comme reprise faite."""
import glob
import json
import os
import shutil
import time

from dq4_pc import language as LG
from dq4_pc.language import tr

CODE = os.path.dirname(os.path.abspath(__file__))                 # .../dq4-portage/dq4_pc
ROOT = os.path.dirname(CODE)                                    # .../dq4-portage
RESUME_FILE = 'reprise.json'                                      # dans donnees\ : les etapes de la reprise deja faites (D-235)
LOGFILE_NAMES = tuple('data%d.dat' % n for n in (1, 2, 3, 4, 5, 9))     # les fichiers du jeu : data1 a data3 = journaux, data4 = suspension, data5 = sauvegarde auto, data9 = journal le plus recent


def _norm(p):
    return os.path.normpath(os.path.abspath(p))


class Folders:
    """Les dossiers et fichiers, calcules a partir de la racine des donnees (et des deux variables d'environnement)."""

    def __init__(self, root=ROOT, env=None):
        env = os.environ if env is None else env
        self.root = _norm(root)
        self.data = _norm(env['DQ4_DONNEES']) if env.get('DQ4_DONNEES') else os.path.join(self.root, 'donnees')
        self.old_games = _norm(env['DQ4_JEUX']) if env.get('DQ4_JEUX') else None        # variable d'avant le rangement
        self.apk = os.path.join(self.old_games, 'patched_apks') if self.old_games else os.path.join(self.data, 'apk')
        self.saves = os.path.join(self.data, 'sauvegardes')
        self.mobile = os.path.join(self.old_games, 'saves') if self.old_games else os.path.join(self.saves, 'mobile')       # (ancien dossier de la copie du telephone, repris par `migrate` ; DQ4_JEUX : une copie lue seulement)
        self.portage = self.saves                                                  # D-232 : un seul dossier, ou le jeu lit ET ecrit ses journaux (data1.dat...), a cote de `savestates\\`
        self.old_port_dir = os.path.join(self.saves, 'portage')                  # (ancien dossier d'ecriture, repris par `migrate`)
        self.savestates = os.path.join(self.saves, 'etats')
        self.cache = os.path.join(self.data, 'cache')
        self.settings_dir = os.path.join(self.data, 'reglages')
        self.settings = os.path.join(self.settings_dir, 'reglages.json')
        self.favorites = os.path.join(self.settings_dir, 'historique_favoris.json')
        self.resume_file = os.path.join(self.data, RESUME_FILE)
        self.logfiles = os.path.join(self.data, 'journaux')
        self.window_logfile = os.path.join(self.logfiles, 'erreurs_fenetre.log')

    # ---- sauvegardes -------------------------------------------------------------------------------------------------------------
    def recent_mobile_save(self):
        """Dossier de la copie du telephone la plus recente (`mobile\\<date>` : l'ancien rangement, ou DQ4_JEUX\\saves\\<date>, la date se trie comme l'ordre alphabetique), ou None."""
        folders = sorted(d for d in glob.glob(os.path.join(self.mobile, '*')) if os.path.isdir(d))
        return folders[-1] if folders else None

    def savestates_folder(self, write_dir):
        """Dossier des etats instantanes pour ce dossier d'ecriture : `saves\\savestates` avec l'emplacement habituel (`saves`), sinon `<write_dir>\\savestates` (tests, --saves-ecriture)."""
        return self.savestates if _norm(write_dir) == _norm(self.portage) else os.path.join(write_dir, 'etats')

    def clones_folder(self, write_dir):
        """Dossier qui recoit les copies `avant_import_<date>` : `saves\\` avec l'emplacement habituel, sinon le dossier d'ecriture lui-meme."""
        return self.saves if _norm(write_dir) == _norm(self.portage) else write_dir

    def errors_logfile(self):
        return os.environ.get('DQ_JOURNAL_FENETRE') or self.window_logfile


FOLDERS = Folders()


# ---- migration de l'ancienne disposition ------------------------------------------------------------------------------------------
def _clone(src, dst, log, num):
    """Copie un fichier s'il n'existe pas encore a destination ; renvoie 1 si copie."""
    if os.path.exists(dst): return 0
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    tmp = dst + '.tmp'
    shutil.copy2(src, tmp); os.replace(tmp, dst)
    return 1


def _clone_tree(src, dst, log, num):
    n = 0
    for root, _, files in os.walk(src):
        rel = os.path.relpath(root, src)
        for f in files:
            n += _clone(os.path.join(root, f), os.path.normpath(os.path.join(dst, rel, f)), log, num)
    return n


def _merge_saves(sources, destination, log):
    """Copie les fichiers du jeu (data1.dat... data9.dat) des dossiers `sources` (par ordre de priorite) dans `destination`, sans rien ecraser : le premier dossier qui a le fichier gagne. -> nombre de fichiers copies."""
    n = 0
    for src in sources:
        for name_str in LOGFILE_NAMES:
            p = os.path.join(src, name_str)
            if os.path.isfile(p): n += _clone(p, os.path.join(destination, name_str), log, 0)
    return n


def _tidy_old_folders(d, log):
    """D-232 : un seul dossier de sauvegardes. Les journaux de l'ancien `saves\\portage` (prioritaire : c'est ce que le jeu ecrivait) puis ceux de la copie du telephone la plus recente (`saves\\mobile\\<date>`)
    sont copies dans `saves\\`, sans rien ecraser (ce que le jeu lisait avant, fichier par fichier, dans cet ordre) ; puis, une fois chaque fichier retrouve a sa place, les deux anciens dossiers sont deplaces
    tels quels dans `saves\\avant_rangement_<date>\\` : rien n'est supprime. Un echec laisse les anciens dossiers en place (le jeu les lit encore). Avec DQ4_JEUX (copie du telephone ailleurs, lue seulement) : sans effet.
    -> phrases decrivant ce qui a ete fait."""
    if d.old_games: return []
    old_dirs = [p for p in (d.old_port_dir, d.mobile) if os.path.isdir(p)]
    if not old_dirs: return []
    done = []
    try:
        recent = d.recent_mobile_save()
        sources = [d.old_port_dir] + ([recent] if recent else [])
        n = _merge_saves(sources, d.saves, log)
        if n: done.append(tr('%d fichier(s) de sauvegardes copie(s) dans donnees\\sauvegardes (portage\\ puis mobile\\)') % n)
        missing = [name_str for name_str in LOGFILE_NAMES if any(os.path.isfile(os.path.join(s, name_str)) for s in sources) and not os.path.isfile(os.path.join(d.saves, name_str))]
        if missing: raise OSError(tr('fichiers non retrouves dans sauvegardes : %s') % ', '.join(missing))
        base = os.path.join(d.saves, 'avant_rangement_' + time.strftime('%Y%m%d_%H%M%S')); target = base; k = 1
        while os.path.exists(target): k += 1; target = '%s_%d' % (base, k)
        os.makedirs(target)
        for p in old_dirs: os.replace(p, os.path.join(target, os.path.basename(p)))
        done.append(tr('anciens dossiers ranges : %s -> %s') % (', '.join('sauvegardes\\' + os.path.basename(p) for p in old_dirs), 'sauvegardes\\' + os.path.basename(target)))
    except OSError as ex:
        done.append(tr('anciens dossiers de sauvegardes NON ranges (%s) : ils restent en place') % ex)
    return done


STAGES = ('cache', 'apk', 'sauvegardes_portage', 'sauvegardes_telephone', 'reglages', 'journal')       # les reprises qui ne se font qu'une fois (D-235)


def _read_resume(d):
    """Les etapes deja faites (`data\\resume.json`) : dict nom -> date, ou {} (fichier absent ou illisible)."""
    try:
        with open(d.resume_file, encoding='utf-8') as f: stages = json.load(f).get('etapes', {})
        return {k: str(v) for k, v in stages.items()} if isinstance(stages, dict) else {}
    except (OSError, ValueError, AttributeError):
        return {}


def _note_resume(d, stages):
    try:
        os.makedirs(d.data, exist_ok=True)
        tmp = d.resume_file + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as f: json.dump({'etapes': stages}, f, ensure_ascii=False, indent=1)
        os.replace(tmp, d.resume_file)
    except OSError:
        pass                          # (sans le fichier la reprise se refait au prochain demarrage : elle ne ecrase rien)


def _already_in_service(d):
    """Pour chaque etape : sa destination sert deja dans `data\\` (une version d'avant D-235 a deja fait la reprise, ou tu as copie tes fichiers toi-meme) -> rien a recopier."""
    logfiles = any(os.path.isfile(os.path.join(d.saves, name_str)) for name_str in LOGFILE_NAMES) or os.path.isdir(d.savestates)
    return {'cache': os.path.exists(d.cache), 'apk': bool(glob.glob(os.path.join(d.apk, '*.apk'))),
            'sauvegardes_portage': logfiles, 'sauvegardes_telephone': logfiles,
            'reglages': bool(glob.glob(os.path.join(d.settings_dir, '*.json'))), 'journal': os.path.isfile(d.window_logfile)}


def migrate(d=None, log=print):
    """Reprend l'ancienne disposition dans `data\\`. -> liste de phrases decrivant ce qui a ete fait (vide : rien a faire).
    Copie sans jamais ecraser ni supprimer, sauf le cache (deplace d'un coup si `data\\cache` n'existe pas, sinon laisse tel quel) et les anciens dossiers `saves\\portage` et `mobile` (deplaces dans `avant_rangement_<date>` apres copie) ; ne fait rien avec DQ4_DONNEES / DQ4_JEUX non reconnus.
    Chaque reprise ne se fait qu'une fois (D-235) : ce que tu effaces ensuite dans `data\\` (un dossier `avant_import_...`, un journal, des reglages) ne revient pas depuis l'ancien dossier."""
    d = d or FOLDERS
    done = []
    code = os.path.join(d.root, 'dq4_pc')
    games = os.path.join(d.root, 'jeux', 'DQ4')
    noted = _read_resume(d); in_service = _already_in_service(d); new_entries = {}

    def is_pending(name_str):
        """L'etape reste a faire ? Sinon (faite avant, ou destination deja en service) on la note faite, sans rien copier."""
        if name_str in noted: return False
        if in_service[name_str]: new_entries[name_str] = 'en place'; return False
        return True

    def mark_done(name_str): new_entries[name_str] = time.strftime('%d/%m/%Y %H:%M:%S')

    # 1. cache : meme volume, donc un simple renommage (il pese plusieurs centaines de Mo)
    old = os.path.join(code, 'cache')
    if is_pending('cache') and os.path.isdir(old):
        try:
            os.makedirs(os.path.dirname(d.cache), exist_ok=True); os.replace(old, d.cache)
            done.append(tr('cache deplace : dq4_pc\\cache -> donnees\\cache')); mark_done('cache')
        except OSError as ex:
            done.append(tr('cache NON deplace (%s) : il sera recalcule') % ex)
    # 2. APK francais : copies (jeux\DQ4\patched_apks -> donnees\apk)
    if is_pending('apk') and not d.old_games and os.path.isdir(os.path.join(games, 'patched_apks')):
        n = _clone_tree(os.path.join(games, 'patched_apks'), d.apk, log, 0)
        if n: done.append(tr('%d fichier(s) APK copie(s) : jeux\\DQ4\\patched_apks -> donnees\\apk') % n)
        mark_done('apk')
    # 3. D-232 : les anciens dossiers donnees\sauvegardes\portage et \mobile\<date> sont remontes dans donnees\sauvegardes puis ranges (AVANT les reprises plus anciennes : ce que le jeu ecrivait ces derniers jours est prioritaire sur de vieilles copies)
    #    (se fait toujours : elle deplace ces deux dossiers, donc ne se repete pas d'elle-meme)
    done += _tidy_old_folders(d, log)
    # 4. sauvegardes du portage d'avant : dq4_pc\sauvegardes\{data*.dat, etats\, avant_import_*\} -> donnees\sauvegardes (D-232 : un seul dossier)
    old = os.path.join(code, 'sauvegardes')
    if is_pending('sauvegardes_portage') and os.path.isdir(old):
        n = 0
        for f in glob.glob(os.path.join(old, '*')):
            name_str = os.path.basename(f)
            if os.path.isfile(f): n += _clone(f, os.path.join(d.saves, name_str), log, 0)
            elif name_str == 'etats': n += _clone_tree(f, d.savestates, log, 0)
            elif name_str.startswith('avant_import_'): n += _clone_tree(f, os.path.join(d.saves, name_str), log, 0)
        if n: done.append(tr('%d fichier(s) de sauvegardes du portage copie(s) : dq4_pc\\sauvegardes -> donnees\\sauvegardes') % n)
        mark_done('sauvegardes_portage')
    # 5. sauvegardes du telephone d'avant : jeux\DQ4\saves\<date la plus recente> -> donnees\sauvegardes (ce que le jeu lisait en second, fichier par fichier)
    if is_pending('sauvegardes_telephone') and not d.old_games and os.path.isdir(os.path.join(games, 'saves')):
        recents = sorted(x for x in glob.glob(os.path.join(games, 'saves', '*')) if os.path.isdir(x))
        n = _merge_saves(recents[-1:], d.saves, log)
        if n: done.append(tr('%d fichier(s) de sauvegardes du telephone copie(s) : jeux\\DQ4\\saves -> donnees\\sauvegardes') % n)
        mark_done('sauvegardes_telephone')
    # 6. reglages et favoris de l'historique
    if is_pending('reglages'):
        n = 0; found = False
        for name_str in ('reglages.json', 'historique_favoris.json', 'historique_messages.json'):
            src = os.path.join(code, name_str)
            if os.path.isfile(src): found = True; n += _clone(src, os.path.join(d.settings_dir, name_str), log, 0)
        if n: done.append(tr('%d fichier(s) de reglages copie(s) : dq4_pc -> donnees\\reglages') % n)
        if found: mark_done('reglages')
    # 7. journal des erreurs de la fenetre
    src = os.path.join(code, 'erreurs_fenetre.log')
    if is_pending('journal') and os.path.isfile(src):
        if _clone(src, d.window_logfile, log, 0): done.append(tr('journal des erreurs copie : donnees\\journaux'))
        mark_done('journal')
    if new_entries: _note_resume(d, dict(noted, **new_entries))
    for ph in done: log(tr('Migration : %s') % ph)
    return done


if __name__ == '__main__':           # `python -m dq4_pc.paths` : la reprise seule (lancee par launch_dq4.bat avant le jeu)
    LG.select_language(LG.read_setting(FOLDERS.settings))          # (D-238 : les messages de la reprise sont dans la langue de l'outil)
    migrate()
