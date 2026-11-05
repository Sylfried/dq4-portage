"""Tous les dossiers et fichiers du portage, en un seul endroit (rangement du 04/11/2026).

Tout ce qui t'appartient (APK, sauvegardes, caches, reglages) est dans UN dossier, `donnees\\`, a la racine du projet ; il n'est jamais envoye sur GitHub (.gitignore) :

    donnees\\
      apk\\                      les 3 APK francais (base.apk, split_config.arm64_v8a.apk, split_UnityDataAssetPack.apk)
      sauvegardes\\            UN SEUL dossier (D-232) : le contenu exact du .zip d'export, pour copier d'un coup les sauvegardes du telephone
        data1.dat ... data5.dat, data9.dat   les journaux du jeu (lus et ecrits par le moteur ; ceux du telephone se copient ici)
        etats\\                les etats instantanes (etat_01.dqs ...)
        avant_import_<date>\\    copies de securite faites avant chaque import de sauvegardes
        avant_rangement_<date>\\ anciens dossiers `portage\\` et `mobile\\` rangés tels quels par la reprise (voir `migrer`) : sans danger a effacer une fois la partie verifiee
      cache\\                    ce que le portage calcule a partir des APK (cartes, sprites, sons, menus) : sans danger a effacer
      reglages\\                 reglages.json, historique_favoris.json, historique_messages.json
      journaux\\                 erreurs_fenetre.log
      reprise.json               les etapes de la reprise de l'ancienne disposition deja faites (D-235)

Deux variables d'environnement, pour les tests et les installations particulieres :
  DQ4_DONNEES : un autre emplacement pour tout le dossier `donnees`.
  DQ4_JEUX    : (ancien fonctionnement) un dossier « jeux\\DQ4 » contenant `patched_apks` et `saves\\<date>` ; il remplace `donnees\\apk`, et `saves\\<date>` reste une copie LUE SEULEMENT de sauvegardes (tests, installations particulieres).

`migrer()` reprend l'ancienne disposition (jeux\\DQ4, dq4_pc\\cache, dq4_pc\\sauvegardes, dq4_pc\\reglages.json ...) : elle COPIE (ou, pour le cache seulement, deplace) vers la nouvelle,
sans jamais ecraser un fichier deja present et sans rien supprimer. Chaque reprise n'a lieu QU'UNE FOIS (D-235) : `donnees\\reprise.json` note les etapes faites, pour que ce que tu effaces dans `donnees\\`
(un dossier `avant_import_...`, un journal, des reglages) ne soit pas recopie depuis l'ancien dossier au demarrage suivant. Une disposition deja en service (journaux, etats, reglages ou cache dans `donnees\\`) compte comme reprise faite."""
import glob
import json
import os
import shutil
import time

CODE = os.path.dirname(os.path.abspath(__file__))                 # .../dq4-portage/dq4_pc
RACINE = os.path.dirname(CODE)                                    # .../dq4-portage
FICHIER_REPRISE = 'reprise.json'                                      # dans donnees\ : les etapes de la reprise deja faites (D-235)
NOMS_JOURNAUX = tuple('data%d.dat' % n for n in (1, 2, 3, 4, 5, 9))     # les fichiers du jeu : data1 a data3 = journaux, data4 = suspension, data5 = sauvegarde auto, data9 = journal le plus recent


def _norm(p):
    return os.path.normpath(os.path.abspath(p))


class Dossiers:
    """Les dossiers et fichiers, calcules a partir de la racine des donnees (et des deux variables d'environnement)."""

    def __init__(self, racine=RACINE, env=None):
        env = os.environ if env is None else env
        self.racine = _norm(racine)
        self.donnees = _norm(env['DQ4_DONNEES']) if env.get('DQ4_DONNEES') else os.path.join(self.racine, 'donnees')
        self.jeux_ancien = _norm(env['DQ4_JEUX']) if env.get('DQ4_JEUX') else None        # variable d'avant le rangement
        self.apk = os.path.join(self.jeux_ancien, 'patched_apks') if self.jeux_ancien else os.path.join(self.donnees, 'apk')
        self.sauvegardes = os.path.join(self.donnees, 'sauvegardes')
        self.mobile = os.path.join(self.jeux_ancien, 'saves') if self.jeux_ancien else os.path.join(self.sauvegardes, 'mobile')       # (ancien dossier de la copie du telephone, repris par `migrer` ; DQ4_JEUX : une copie lue seulement)
        self.portage = self.sauvegardes                                                  # D-232 : un seul dossier, ou le jeu lit ET ecrit ses journaux (data1.dat...), a cote de `etats\\`
        self.ancien_portage = os.path.join(self.sauvegardes, 'portage')                  # (ancien dossier d'ecriture, repris par `migrer`)
        self.etats = os.path.join(self.sauvegardes, 'etats')
        self.cache = os.path.join(self.donnees, 'cache')
        self.reglages_dir = os.path.join(self.donnees, 'reglages')
        self.reglages = os.path.join(self.reglages_dir, 'reglages.json')
        self.favoris = os.path.join(self.reglages_dir, 'historique_favoris.json')
        self.fichier_reprise = os.path.join(self.donnees, FICHIER_REPRISE)
        self.journaux = os.path.join(self.donnees, 'journaux')
        self.journal_fenetre = os.path.join(self.journaux, 'erreurs_fenetre.log')

    # ---- sauvegardes -------------------------------------------------------------------------------------------------------------
    def sauvegarde_mobile_recente(self):
        """Dossier de la copie du telephone la plus recente (`mobile\\<date>` : l'ancien rangement, ou DQ4_JEUX\\saves\\<date>, la date se trie comme l'ordre alphabetique), ou None."""
        dossiers = sorted(d for d in glob.glob(os.path.join(self.mobile, '*')) if os.path.isdir(d))
        return dossiers[-1] if dossiers else None

    def dossier_etats(self, ecriture):
        """Dossier des etats instantanes pour ce dossier d'ecriture : `sauvegardes\\etats` avec l'emplacement habituel (`sauvegardes`), sinon `<ecriture>\\etats` (tests, --saves-ecriture)."""
        return self.etats if _norm(ecriture) == _norm(self.portage) else os.path.join(ecriture, 'etats')

    def dossier_copies(self, ecriture):
        """Dossier qui recoit les copies `avant_import_<date>` : `sauvegardes\\` avec l'emplacement habituel, sinon le dossier d'ecriture lui-meme."""
        return self.sauvegardes if _norm(ecriture) == _norm(self.portage) else ecriture

    def journal_erreurs(self):
        return os.environ.get('DQ_JOURNAL_FENETRE') or self.journal_fenetre


DOSSIERS = Dossiers()


# ---- migration de l'ancienne disposition ------------------------------------------------------------------------------------------
def _copier(src, dst, log, nb):
    """Copie un fichier s'il n'existe pas encore a destination ; renvoie 1 si copie."""
    if os.path.exists(dst): return 0
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    tmp = dst + '.tmp'
    shutil.copy2(src, tmp); os.replace(tmp, dst)
    return 1


def _copier_arbre(src, dst, log, nb):
    n = 0
    for racine, _, fichiers in os.walk(src):
        rel = os.path.relpath(racine, src)
        for f in fichiers:
            n += _copier(os.path.join(racine, f), os.path.normpath(os.path.join(dst, rel, f)), log, nb)
    return n


def _remonter(sources, destination, log):
    """Copie les fichiers du jeu (data1.dat... data9.dat) des dossiers `sources` (par ordre de priorite) dans `destination`, sans rien ecraser : le premier dossier qui a le fichier gagne. -> nombre de fichiers copies."""
    n = 0
    for src in sources:
        for nom in NOMS_JOURNAUX:
            p = os.path.join(src, nom)
            if os.path.isfile(p): n += _copier(p, os.path.join(destination, nom), log, 0)
    return n


def _ranger_anciens_dossiers(d, log):
    """D-232 : un seul dossier de sauvegardes. Les journaux de l'ancien `sauvegardes\\portage` (prioritaire : c'est ce que le jeu ecrivait) puis ceux de la copie du telephone la plus recente (`sauvegardes\\mobile\\<date>`)
    sont copies dans `sauvegardes\\`, sans rien ecraser (ce que le jeu lisait avant, fichier par fichier, dans cet ordre) ; puis, une fois chaque fichier retrouve a sa place, les deux anciens dossiers sont deplaces
    tels quels dans `sauvegardes\\avant_rangement_<date>\\` : rien n'est supprime. Un echec laisse les anciens dossiers en place (le jeu les lit encore). Avec DQ4_JEUX (copie du telephone ailleurs, lue seulement) : sans effet.
    -> phrases decrivant ce qui a ete fait."""
    if d.jeux_ancien: return []
    anciens = [p for p in (d.ancien_portage, d.mobile) if os.path.isdir(p)]
    if not anciens: return []
    fait = []
    try:
        recente = d.sauvegarde_mobile_recente()
        sources = [d.ancien_portage] + ([recente] if recente else [])
        n = _remonter(sources, d.sauvegardes, log)
        if n: fait.append('%d fichier(s) de sauvegardes copie(s) dans donnees\\sauvegardes (portage\\ puis mobile\\)' % n)
        manque = [nom for nom in NOMS_JOURNAUX if any(os.path.isfile(os.path.join(s, nom)) for s in sources) and not os.path.isfile(os.path.join(d.sauvegardes, nom))]
        if manque: raise OSError('fichiers non retrouves dans sauvegardes : %s' % ', '.join(manque))
        base = os.path.join(d.sauvegardes, 'avant_rangement_' + time.strftime('%Y%m%d_%H%M%S')); cible = base; k = 1
        while os.path.exists(cible): k += 1; cible = '%s_%d' % (base, k)
        os.makedirs(cible)
        for p in anciens: os.replace(p, os.path.join(cible, os.path.basename(p)))
        fait.append('anciens dossiers ranges : %s -> %s' % (', '.join('sauvegardes\\' + os.path.basename(p) for p in anciens), 'sauvegardes\\' + os.path.basename(cible)))
    except OSError as ex:
        fait.append('anciens dossiers de sauvegardes NON ranges (%s) : ils restent en place' % ex)
    return fait


ETAPES = ('cache', 'apk', 'sauvegardes_portage', 'sauvegardes_telephone', 'reglages', 'journal')       # les reprises qui ne se font qu'une fois (D-235)


def _lire_reprise(d):
    """Les etapes deja faites (`donnees\\reprise.json`) : dict nom -> date, ou {} (fichier absent ou illisible)."""
    try:
        with open(d.fichier_reprise, encoding='utf-8') as f: etapes = json.load(f).get('etapes', {})
        return {k: str(v) for k, v in etapes.items()} if isinstance(etapes, dict) else {}
    except (OSError, ValueError, AttributeError):
        return {}


def _noter_reprise(d, etapes):
    try:
        os.makedirs(d.donnees, exist_ok=True)
        tmp = d.fichier_reprise + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as f: json.dump({'etapes': etapes}, f, ensure_ascii=False, indent=1)
        os.replace(tmp, d.fichier_reprise)
    except OSError:
        pass                          # (sans le fichier la reprise se refait au prochain demarrage : elle ne ecrase rien)


def _deja_en_service(d):
    """Pour chaque etape : sa destination sert deja dans `donnees\\` (une version d'avant D-235 a deja fait la reprise, ou tu as copie tes fichiers toi-meme) -> rien a recopier."""
    journaux = any(os.path.isfile(os.path.join(d.sauvegardes, nom)) for nom in NOMS_JOURNAUX) or os.path.isdir(d.etats)
    return {'cache': os.path.exists(d.cache), 'apk': bool(glob.glob(os.path.join(d.apk, '*.apk'))),
            'sauvegardes_portage': journaux, 'sauvegardes_telephone': journaux,
            'reglages': bool(glob.glob(os.path.join(d.reglages_dir, '*.json'))), 'journal': os.path.isfile(d.journal_fenetre)}


def migrer(d=None, log=print):
    """Reprend l'ancienne disposition dans `donnees\\`. -> liste de phrases decrivant ce qui a ete fait (vide : rien a faire).
    Copie sans jamais ecraser ni supprimer, sauf le cache (deplace d'un coup si `donnees\\cache` n'existe pas, sinon laisse tel quel) et les anciens dossiers `sauvegardes\\portage` et `mobile` (deplaces dans `avant_rangement_<date>` apres copie) ; ne fait rien avec DQ4_DONNEES / DQ4_JEUX non reconnus.
    Chaque reprise ne se fait qu'une fois (D-235) : ce que tu effaces ensuite dans `donnees\\` (un dossier `avant_import_...`, un journal, des reglages) ne revient pas depuis l'ancien dossier."""
    d = d or DOSSIERS
    fait = []
    code = os.path.join(d.racine, 'dq4_pc')
    jeux = os.path.join(d.racine, 'jeux', 'DQ4')
    notees = _lire_reprise(d); en_service = _deja_en_service(d); nouvelles = {}

    def a_faire(nom):
        """L'etape reste a faire ? Sinon (faite avant, ou destination deja en service) on la note faite, sans rien copier."""
        if nom in notees: return False
        if en_service[nom]: nouvelles[nom] = 'en place'; return False
        return True

    def faite(nom): nouvelles[nom] = time.strftime('%d/%m/%Y %H:%M:%S')

    # 1. cache : meme volume, donc un simple renommage (il pese plusieurs centaines de Mo)
    ancien = os.path.join(code, 'cache')
    if a_faire('cache') and os.path.isdir(ancien):
        try:
            os.makedirs(os.path.dirname(d.cache), exist_ok=True); os.replace(ancien, d.cache)
            fait.append('cache deplace : dq4_pc\\cache -> donnees\\cache'); faite('cache')
        except OSError as ex:
            fait.append('cache NON deplace (%s) : il sera recalcule' % ex)
    # 2. APK francais : copies (jeux\DQ4\patched_apks -> donnees\apk)
    if a_faire('apk') and not d.jeux_ancien and os.path.isdir(os.path.join(jeux, 'patched_apks')):
        n = _copier_arbre(os.path.join(jeux, 'patched_apks'), d.apk, log, 0)
        if n: fait.append('%d fichier(s) APK copie(s) : jeux\\DQ4\\patched_apks -> donnees\\apk' % n)
        faite('apk')
    # 3. D-232 : les anciens dossiers donnees\sauvegardes\portage et \mobile\<date> sont remontes dans donnees\sauvegardes puis ranges (AVANT les reprises plus anciennes : ce que le jeu ecrivait ces derniers jours est prioritaire sur de vieilles copies)
    #    (se fait toujours : elle deplace ces deux dossiers, donc ne se repete pas d'elle-meme)
    fait += _ranger_anciens_dossiers(d, log)
    # 4. sauvegardes du portage d'avant : dq4_pc\sauvegardes\{data*.dat, etats\, avant_import_*\} -> donnees\sauvegardes (D-232 : un seul dossier)
    ancien = os.path.join(code, 'sauvegardes')
    if a_faire('sauvegardes_portage') and os.path.isdir(ancien):
        n = 0
        for f in glob.glob(os.path.join(ancien, '*')):
            nom = os.path.basename(f)
            if os.path.isfile(f): n += _copier(f, os.path.join(d.sauvegardes, nom), log, 0)
            elif nom == 'etats': n += _copier_arbre(f, d.etats, log, 0)
            elif nom.startswith('avant_import_'): n += _copier_arbre(f, os.path.join(d.sauvegardes, nom), log, 0)
        if n: fait.append('%d fichier(s) de sauvegardes du portage copie(s) : dq4_pc\\sauvegardes -> donnees\\sauvegardes' % n)
        faite('sauvegardes_portage')
    # 5. sauvegardes du telephone d'avant : jeux\DQ4\saves\<date la plus recente> -> donnees\sauvegardes (ce que le jeu lisait en second, fichier par fichier)
    if a_faire('sauvegardes_telephone') and not d.jeux_ancien and os.path.isdir(os.path.join(jeux, 'saves')):
        recentes = sorted(x for x in glob.glob(os.path.join(jeux, 'saves', '*')) if os.path.isdir(x))
        n = _remonter(recentes[-1:], d.sauvegardes, log)
        if n: fait.append('%d fichier(s) de sauvegardes du telephone copie(s) : jeux\\DQ4\\saves -> donnees\\sauvegardes' % n)
        faite('sauvegardes_telephone')
    # 6. reglages et favoris de l'historique
    if a_faire('reglages'):
        n = 0; trouve = False
        for nom in ('reglages.json', 'historique_favoris.json', 'historique_messages.json'):
            src = os.path.join(code, nom)
            if os.path.isfile(src): trouve = True; n += _copier(src, os.path.join(d.reglages_dir, nom), log, 0)
        if n: fait.append('%d fichier(s) de reglages copie(s) : dq4_pc -> donnees\\reglages' % n)
        if trouve: faite('reglages')
    # 7. journal des erreurs de la fenetre
    src = os.path.join(code, 'erreurs_fenetre.log')
    if a_faire('journal') and os.path.isfile(src):
        if _copier(src, d.journal_fenetre, log, 0): fait.append('journal des erreurs copie : donnees\\journaux')
        faite('journal')
    if nouvelles: _noter_reprise(d, dict(notees, **nouvelles))
    for ph in fait: log('Migration : ' + ph)
    return fait


if __name__ == '__main__':           # `python -m dq4_pc.chemins` : la reprise seule (lancee par lancer_dq4.bat avant le jeu)
    migrer()
