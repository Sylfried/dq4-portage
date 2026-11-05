"""Tous les dossiers et fichiers du portage, en un seul endroit (rangement du 04/11/2026, noms en anglais du 05/11/2026 : D-239).

Tout ce qui t'appartient (APK, sauvegardes, caches, reglages) est dans UN dossier, `data\\`, a la racine du projet ; il n'est jamais envoye sur GitHub (.gitignore) :

    data\\
      apk\\                      les 3 APK francais (base.apk, split_config.arm64_v8a.apk, split_UnityDataAssetPack.apk)
      saves\\                  UN SEUL dossier (D-232) : le contenu exact du .zip d'export, pour copier d'un coup les sauvegardes du telephone
        data1.dat ... data5.dat, data9.dat   les journaux du jeu (lus et ecrits par le moteur ; ceux du telephone se copient ici)
        savestates\\           les etats instantanes (state_01.dqs ...)
        before_import_<date>\\   copies de securite faites avant chaque import de sauvegardes
        before_tidy_<date>\\     anciens dossiers `portage\\` et `mobile\\` ranges tels quels par la reprise (voir `migrate`) : sans danger a effacer une fois la partie verifiee
      cache\\                    ce que le portage calcule a partir des APK (cartes, sprites, sons, menus) : sans danger a effacer
      settings\\               settings.json, history_favorites.json, history_messages.json
      logs\\                   window_errors.log
      resume.json               les etapes de la reprise de l'ancienne disposition deja faites (D-235)

Deux variables d'environnement, pour les tests et les installations particulieres (les anciens noms DQ4_DONNEES et DQ4_JEUX marchent toujours) :
  DQ4_DATA  : un autre emplacement pour tout le dossier `data`.
  DQ4_GAMES : (ancien fonctionnement) un dossier « jeux\\DQ4 » contenant `patched_apks` et `saves\\<date>` ; il remplace `data\\apk`, et `saves\\<date>` reste une copie LUE SEULEMENT de sauvegardes (tests, installations particulieres).

Noms en anglais (D-239) : les dossiers et fichiers que les versions d'avant creaient en francais (`donnees`, `sauvegardes`, `etats\\etat_NN.dqs`, `reglages`, `journaux`, `avant_import_...`, `reprise.json`...) sont RENOMMES sur place au premier demarrage
(`english_names` dans `resume.json`) : un simple renommage, sans copie, sans rien ecraser ni supprimer ; si un nom existe deja a la nouvelle place, l'ancien fichier reste ou il est et le renommage est refait au demarrage suivant.

`migrate()` reprend aussi l'ancienne disposition (jeux\\DQ4, dq4_pc\\cache, dq4_pc\\sauvegardes, dq4_pc\\reglages.json ...) : elle COPIE (ou, pour le cache seulement, deplace) vers la nouvelle,
sans jamais ecraser un fichier deja present et sans rien supprimer. Chaque reprise n'a lieu QU'UNE FOIS (D-235) : `data\\resume.json` note les etapes faites, pour que ce que tu effaces dans `data\\`
(un dossier `before_import_...`, un journal, des reglages) ne soit pas recopie depuis l'ancien dossier au demarrage suivant. Une disposition deja en service (journaux, etats, reglages ou cache dans `data\\`) compte comme reprise faite."""
import glob
import json
import os
import re
import shutil
import time

from dq4_pc import language as LG
from dq4_pc.language import tr

CODE = os.path.dirname(os.path.abspath(__file__))                 # .../dq4-portage/dq4_pc
ROOT = os.path.dirname(CODE)                                    # .../dq4-portage
RESUME_FILE = 'resume.json'                                        # dans data\ : les etapes de la reprise deja faites (D-235)
OLD_RESUME_FILE = 'reprise.json'                                   # (son nom d'avant D-239 ; renomme au premier demarrage)
LOGFILE_NAMES = tuple('data%d.dat' % n for n in (1, 2, 3, 4, 5, 9))     # les fichiers du jeu : data1 a data3 = journaux, data4 = suspension, data5 = sauvegarde auto, data9 = journal le plus recent


def _norm(p):
    return os.path.normpath(os.path.abspath(p))


class Folders:
    """Les dossiers et fichiers, calcules a partir de la racine des donnees (et des deux variables d'environnement)."""

    def __init__(self, root=ROOT, env=None):
        env = os.environ if env is None else env
        self.root = _norm(root)
        data_env = env.get('DQ4_DATA') or env.get('DQ4_DONNEES')            # (DQ4_DONNEES : son nom d'avant D-239)
        games_env = env.get('DQ4_GAMES') or env.get('DQ4_JEUX')             # (DQ4_JEUX : idem)
        self.data = _norm(data_env) if data_env else os.path.join(self.root, 'data')
        self.custom_data = bool(data_env)
        self.old_games = _norm(games_env) if games_env else None        # variable d'avant le rangement
        self.apk = os.path.join(self.old_games, 'patched_apks') if self.old_games else os.path.join(self.data, 'apk')
        self.saves = os.path.join(self.data, 'saves')
        self.mobile = os.path.join(self.old_games, 'saves') if self.old_games else os.path.join(self.saves, 'mobile')       # (ancien dossier de la copie du telephone, repris par `migrate` ; DQ4_JEUX : une copie lue seulement)
        self.portage = self.saves                                                  # D-232 : un seul dossier, ou le jeu lit ET ecrit ses journaux (data1.dat...), a cote de `savestates\\`
        self.old_port_dir = os.path.join(self.saves, 'portage')                  # (ancien dossier d'ecriture, repris par `migrate`)
        self.savestates = os.path.join(self.saves, 'savestates')
        self.cache = os.path.join(self.data, 'cache')
        self.settings_dir = os.path.join(self.data, 'settings')
        self.settings = os.path.join(self.settings_dir, 'settings.json')
        self.favorites = os.path.join(self.settings_dir, 'history_favorites.json')
        self.resume_file = os.path.join(self.data, RESUME_FILE)
        self.logfiles = os.path.join(self.data, 'logs')
        self.window_logfile = os.path.join(self.logfiles, 'window_errors.log')

    # ---- sauvegardes -------------------------------------------------------------------------------------------------------------
    def recent_mobile_save(self):
        """Dossier de la copie du telephone la plus recente (`mobile\\<date>` : l'ancien rangement, ou DQ4_JEUX\\saves\\<date>, la date se trie comme l'ordre alphabetique), ou None."""
        folders = sorted(d for d in glob.glob(os.path.join(self.mobile, '*')) if os.path.isdir(d))
        return folders[-1] if folders else None

    def savestates_folder(self, write_dir):
        """Dossier des etats instantanes pour ce dossier d'ecriture : `saves\\savestates` avec l'emplacement habituel (`saves`), sinon `<write_dir>\\savestates` (tests, --saves-ecriture)."""
        return self.savestates if _norm(write_dir) == _norm(self.portage) else os.path.join(write_dir, 'savestates')

    def clones_folder(self, write_dir):
        """Dossier qui recoit les copies `before_import_<date>` : `saves\\` avec l'emplacement habituel, sinon le dossier d'ecriture lui-meme."""
        return self.saves if _norm(write_dir) == _norm(self.portage) else write_dir

    def errors_logfile(self):
        return os.environ.get('DQ_JOURNAL_FENETRE') or self.window_logfile


FOLDERS = Folders()


# ---- noms en anglais (D-239) -------------------------------------------------------------------------------------------------------
OLD_FOLDER_NAMES = {'sauvegardes': 'saves', 'reglages': 'settings', 'journaux': 'logs', 'etats': 'savestates'}       # dossiers : ancien nom -> nouveau
OLD_FILE_PREFIXES = (('reglages.json', 'settings.json'), ('historique_favoris.json', 'history_favorites.json'), ('historique_messages.json', 'history_messages.json'),
                     ('erreurs_fenetre.log', 'window_errors.log'))                # fichiers (et leurs copies `.tmp`, `.bak`... : le debut du nom suffit)
OLD_FOLDER_PREFIXES = (('avant_import_', 'before_import_'), ('avant_rangement_', 'before_tidy_'))
RE_OLD_SAVESTATE = re.compile(r'^etat_(\d\d)\.dqs$', re.I)
OLD_STAGES = {'sauvegardes_portage': 'saves_pc_port', 'sauvegardes_telephone': 'saves_phone', 'reglages': 'settings', 'journal': 'log'}       # etapes de resume.json d'avant D-239 -> nouveau nom
ENGLISH_STAGE = 'english_names'


def english_name(name_str, is_dir):
    """Le nom anglais d'un dossier ou fichier cree par les versions d'avant D-239 (`etats` -> `savestates`, `etat_01.dqs` -> `state_01.dqs`, `avant_import_<date>` -> `before_import_<date>`...), ou None s'il n'a pas change."""
    if is_dir:
        if name_str in OLD_FOLDER_NAMES: return OLD_FOLDER_NAMES[name_str]
        for old, new in OLD_FOLDER_PREFIXES:
            if name_str.startswith(old): return new + name_str[len(old):]
        return None
    m = RE_OLD_SAVESTATE.match(name_str)
    if m: return 'state_%s.dqs' % m.group(1)
    for old, new in OLD_FILE_PREFIXES:
        if name_str.startswith(old): return new + name_str[len(old):]
    if name_str == OLD_RESUME_FILE: return RESUME_FILE
    return None


def _move(src, dst, moves, problems):
    """Renomme `src` en `dst` (meme dossier ou dossiers voisins, donc sans copie) sans rien ecraser ni supprimer : `dst` absent -> simple renommage ; deux dossiers -> le contenu de `src` est remis un par un dans `dst`
    (puis `src` est retire s'il est vide) ; deux fichiers -> `src` reste ou il est (probleme note). Ajoute (src, dst) a `moves` pour chaque renommage fait, (src, dst, raison) a `problems` sinon."""
    if not os.path.lexists(src): return
    if os.path.isdir(src) and not os.path.islink(src) and (os.path.isdir(dst) or not os.path.lexists(dst)):
        if not os.path.lexists(dst):
            try: os.replace(src, dst); moves.append((src, dst, True)); return
            except OSError: pass                           # (par ex. un dossier ouvert dans l'Explorateur : on essaie contenu par contenu)
            try: os.makedirs(dst)
            except OSError as ex: problems.append((src, dst, str(ex))); return
        for child in sorted(os.listdir(src)): _move(os.path.join(src, child), os.path.join(dst, child), moves, problems)
        try: os.rmdir(src)
        except OSError: pass                                   # (pas vide ou verrouille : il reste, rien n'est perdu)
        return
    if not os.path.lexists(dst):
        try: os.replace(src, dst); moves.append((src, dst, False))
        except OSError as ex: problems.append((src, dst, str(ex)))
        return
    problems.append((src, dst, 'exists'))


def _rename_children(folder, moves, problems, deep=False):
    """Renomme les entrees de `folder` qui ont encore un ancien nom ; `deep` : descend dans les sous-dossiers, sauf les copies archivees par la reprise (`portage`, `mobile`, `before_tidy_...`) qui restent telles quelles."""
    try: names = sorted(os.listdir(folder))
    except OSError: return
    for name_str in names:
        p = os.path.join(folder, name_str); is_dir = os.path.isdir(p)
        new = english_name(name_str, is_dir)
        if new and new != name_str:
            target = os.path.join(folder, new)
            _move(p, target, moves, problems)
            if os.path.lexists(target): p, name_str = target, new
        if deep and os.path.isdir(p) and name_str not in ('portage', 'mobile') and not name_str.startswith(('before_tidy_', 'avant_rangement_')): _rename_children(p, moves, problems, True)


def english_names(d):
    """D-239 : renomme sur place les dossiers et fichiers que les versions d'avant creaient en francais. -> (renommages, problemes) ; voir `_move`."""
    moves, problems = [], []
    if not d.custom_data:                                        # (avec DQ4_DATA / DQ4_DONNEES, le dossier est a toi : on n'y touche pas, seul son contenu est renomme)
        _move(os.path.join(d.root, 'donnees'), d.data, moves, problems)
    if os.path.isdir(d.data):
        _rename_children(d.data, moves, problems)                # sauvegardes, reglages, journaux, reprise.json
        _rename_children(d.saves, moves, problems, deep=True)    # etats, etat_NN.dqs, avant_import_..., avant_rangement_...
        _rename_children(d.settings_dir, moves, problems)
        _rename_children(d.logfiles, moves, problems)
    return moves, problems


def _describe_english_names(d, moves, problems):
    """Les phrases qui disent ce que `english_names` a fait (vide : rien)."""
    out = []
    folders = [m for m in moves if m[2]]; files = [m for m in moves if not m[2]]
    rel = lambda p: os.path.relpath(p, d.root) if _norm(p).startswith(d.root) else p
    if folders: out.append(tr('dossiers renommes en anglais : %s') % ', '.join('%s -> %s' % (rel(a), rel(b)) for a, b, _ in folders[:12]))
    if files: out.append(tr('%d fichier(s) renomme(s) en anglais (reglages, historique, journaux, etats instantanes...)') % len(files))
    for a, b, reason in problems:
        if reason == 'exists': out.append(tr('NON renomme : %s -> %s existe deja, l\'ancien reste en place (rien n\'est ecrase)') % (rel(a), rel(b)))
        else: out.append(tr('NON renomme : %s (%s). Ferme les fenetres ou programmes qui utilisent ce dossier, puis relance : le renommage se refait tout seul') % (rel(a), reason))
    return out


# ---- migration de l'ancienne disposition ------------------------------------------------------------------------------------------
def _clone(src, dst, log, num):
    """Copie un fichier s'il n'existe pas encore a destination ; renvoie 1 si copie."""
    if os.path.exists(dst): return 0
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    tmp = dst + '.tmp'
    shutil.copy2(src, tmp); os.replace(tmp, dst)
    return 1


def _english_path(rel):
    """Un chemin relatif d'une ancienne disposition, avec chaque nom mis en anglais (`etats\\etat_01.dqs` -> `savestates\\state_01.dqs`)."""
    parts = [x for x in rel.split(os.sep) if x and x != '.']
    return os.path.join(*[english_name(x, i < len(parts) - 1) or x for i, x in enumerate(parts)]) if parts else ''


def _clone_tree(src, dst, log, num):
    n = 0
    for root, _, files in os.walk(src):
        rel = os.path.relpath(root, src)
        for f in files:
            n += _clone(os.path.join(root, f), os.path.normpath(os.path.join(dst, _english_path(os.path.join(rel, f)))), log, num)
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
    tels quels dans `saves\\before_tidy_<date>\\` : rien n'est supprime. Un echec laisse les anciens dossiers en place (le jeu les lit encore). Avec DQ4_JEUX (copie du telephone ailleurs, lue seulement) : sans effet.
    -> phrases decrivant ce qui a ete fait."""
    if d.old_games: return []
    old_dirs = [p for p in (d.old_port_dir, d.mobile) if os.path.isdir(p)]
    if not old_dirs: return []
    done = []
    try:
        recent = d.recent_mobile_save()
        sources = [d.old_port_dir] + ([recent] if recent else [])
        n = _merge_saves(sources, d.saves, log)
        if n: done.append(tr('%d fichier(s) de sauvegardes copie(s) dans data\\saves (portage\\ puis mobile\\)') % n)
        missing = [name_str for name_str in LOGFILE_NAMES if any(os.path.isfile(os.path.join(s, name_str)) for s in sources) and not os.path.isfile(os.path.join(d.saves, name_str))]
        if missing: raise OSError(tr('fichiers non retrouves dans sauvegardes : %s') % ', '.join(missing))
        base = os.path.join(d.saves, 'before_tidy_' + time.strftime('%Y%m%d_%H%M%S')); target = base; k = 1
        while os.path.exists(target): k += 1; target = '%s_%d' % (base, k)
        os.makedirs(target)
        for p in old_dirs: os.replace(p, os.path.join(target, os.path.basename(p)))
        done.append(tr('anciens dossiers ranges : %s -> %s') % (', '.join('saves\\' + os.path.basename(p) for p in old_dirs), 'saves\\' + os.path.basename(target)))
    except OSError as ex:
        done.append(tr('anciens dossiers de sauvegardes NON ranges (%s) : ils restent en place') % ex)
    return done


STAGES = ('cache', 'apk', 'saves_pc_port', 'saves_phone', 'settings', 'log', ENGLISH_STAGE)       # les reprises qui ne se font qu'une fois (D-235)


def _read_resume(d):
    """Les etapes deja faites (`data\\resume.json`, ou `reprise.json` si son renommage n'a pas encore eu lieu) : dict nom -> date, ou {} (fichier absent ou illisible). Les noms d'etapes d'avant D-239 sont traduits."""
    for path in (d.resume_file, os.path.join(d.data, OLD_RESUME_FILE)):
        try:
            with open(path, encoding='utf-8') as f: content = json.load(f)
            stages = content.get('stages', content.get('etapes', {}))
            if isinstance(stages, dict): return {OLD_STAGES.get(k, k): str(v) for k, v in stages.items()}
        except (OSError, ValueError, AttributeError):
            continue
    return {}


def _note_resume(d, stages):
    try:
        os.makedirs(d.data, exist_ok=True)
        tmp = d.resume_file + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as f: json.dump({'stages': stages}, f, ensure_ascii=False, indent=1)
        os.replace(tmp, d.resume_file)
    except OSError:
        pass                          # (sans le fichier la reprise se refait au prochain demarrage : elle ne ecrase rien)


def _already_in_service(d):
    """Pour chaque etape : sa destination sert deja dans `data\\` (une version d'avant D-235 a deja fait la reprise, ou tu as copie tes fichiers toi-meme) -> rien a recopier."""
    logfiles = any(os.path.isfile(os.path.join(d.saves, name_str)) for name_str in LOGFILE_NAMES) or os.path.isdir(d.savestates)
    return {'cache': os.path.exists(d.cache), 'apk': bool(glob.glob(os.path.join(d.apk, '*.apk'))),
            'saves_pc_port': logfiles, 'saves_phone': logfiles,
            'settings': bool(glob.glob(os.path.join(d.settings_dir, '*.json'))), 'log': os.path.isfile(d.window_logfile)}


def migrate(d=None, log=print):
    """Reprend l'ancienne disposition dans `data\\`. -> liste de phrases decrivant ce qui a ete fait (vide : rien a faire).
    Copie sans jamais ecraser ni supprimer, sauf le cache (deplace d'un coup si `data\\cache` n'existe pas, sinon laisse tel quel) et les anciens dossiers `saves\\portage` et `mobile` (deplaces dans `avant_rangement_<date>` apres copie) ; ne fait rien avec DQ4_DONNEES / DQ4_JEUX non reconnus.
    Chaque reprise ne se fait qu'une fois (D-235) : ce que tu effaces ensuite dans `data\\` (un dossier `before_import_...`, un journal, des reglages) ne revient pas depuis l'ancien dossier.
    D-239 : tout commence par le renommage en anglais des dossiers et fichiers des versions d'avant (`english_names`), pour que les reprises suivantes arrivent deja dans les bons noms."""
    d = d or FOLDERS
    done = []
    code = os.path.join(d.root, 'dq4_pc')
    games = os.path.join(d.root, 'jeux', 'DQ4')
    noted = _read_resume(d); new_entries = {}
    if ENGLISH_STAGE not in noted:
        moves, problems = english_names(d)
        done += _describe_english_names(d, moves, problems)
        noted = _read_resume(d)                                    # (le fichier de reprise vient peut-etre de changer de dossier ou de nom)
        if moves and not problems: new_entries[ENGLISH_STAGE] = time.strftime('%d/%m/%Y %H:%M:%S')       # (un probleme : le renommage est refait au demarrage suivant ; rien a renommer : rien a noter)
    in_service = _already_in_service(d)

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
            done.append(tr('cache deplace : dq4_pc\\cache -> data\\cache')); mark_done('cache')
        except OSError as ex:
            done.append(tr('cache NON deplace (%s) : il sera recalcule') % ex)
    # 2. APK francais : copies (jeux\DQ4\patched_apks -> data\apk)
    if is_pending('apk') and not d.old_games and os.path.isdir(os.path.join(games, 'patched_apks')):
        n = _clone_tree(os.path.join(games, 'patched_apks'), d.apk, log, 0)
        if n: done.append(tr('%d fichier(s) APK copie(s) : jeux\\DQ4\\patched_apks -> data\\apk') % n)
        mark_done('apk')
    # 3. D-232 : les anciens dossiers data\saves\portage et \mobile\<date> sont remontes dans data\saves puis ranges (AVANT les reprises plus anciennes : ce que le jeu ecrivait ces derniers jours est prioritaire sur de vieilles copies)
    #    (se fait toujours : elle deplace ces deux dossiers, donc ne se repete pas d'elle-meme)
    done += _tidy_old_folders(d, log)
    # 4. sauvegardes du portage d'avant : dq4_pc\sauvegardes\{data*.dat, etats\, avant_import_*\} -> data\saves (D-232 : un seul dossier ; D-239 : et mis en anglais au passage)
    old = os.path.join(code, 'sauvegardes')
    if is_pending('saves_pc_port') and os.path.isdir(old):
        n = 0
        for f in glob.glob(os.path.join(old, '*')):
            name_str = os.path.basename(f)
            if os.path.isfile(f): n += _clone(f, os.path.join(d.saves, english_name(name_str, False) or name_str), log, 0)
            elif name_str == 'etats': n += _clone_tree(f, d.savestates, log, 0)
            elif name_str.startswith('avant_import_'): n += _clone_tree(f, os.path.join(d.saves, english_name(name_str, True)), log, 0)
        if n: done.append(tr('%d fichier(s) de sauvegardes du portage copie(s) : dq4_pc\\sauvegardes -> data\\saves') % n)
        mark_done('saves_pc_port')
    # 5. sauvegardes du telephone d'avant : jeux\DQ4\saves\<date la plus recente> -> data\saves (ce que le jeu lisait en second, fichier par fichier)
    if is_pending('saves_phone') and not d.old_games and os.path.isdir(os.path.join(games, 'saves')):
        recents = sorted(x for x in glob.glob(os.path.join(games, 'saves', '*')) if os.path.isdir(x))
        n = _merge_saves(recents[-1:], d.saves, log)
        if n: done.append(tr('%d fichier(s) de sauvegardes du telephone copie(s) : jeux\\DQ4\\saves -> data\\saves') % n)
        mark_done('saves_phone')
    # 6. reglages et favoris de l'historique
    if is_pending('settings'):
        n = 0; found = False
        for name_str in ('reglages.json', 'historique_favoris.json', 'historique_messages.json'):
            src = os.path.join(code, name_str)
            if os.path.isfile(src): found = True; n += _clone(src, os.path.join(d.settings_dir, english_name(name_str, False)), log, 0)
        if n: done.append(tr('%d fichier(s) de reglages copie(s) : dq4_pc -> data\\settings') % n)
        if found: mark_done('settings')
    # 7. journal des erreurs de la fenetre
    src = os.path.join(code, 'erreurs_fenetre.log')
    if is_pending('log') and os.path.isfile(src):
        if _clone(src, d.window_logfile, log, 0): done.append(tr('journal des erreurs copie : data\\logs'))
        mark_done('log')
    if new_entries: _note_resume(d, dict(noted, **new_entries))
    for ph in done: log(tr('Migration : %s') % ph)
    return done


if __name__ == '__main__':           # `python -m dq4_pc.paths` : la reprise seule (lancee par launch_dq4.bat avant le jeu)
    LG.select_language(LG.read_setting(FOLDERS.settings))          # (D-238 : les messages de la reprise sont dans la langue de l'outil)
    migrate()
