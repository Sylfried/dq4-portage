"""Tous les dossiers et fichiers du portage, en un seul endroit (rangement du 04/11/2026).

Tout ce qui t'appartient (APK, sauvegardes, caches, reglages) est dans UN dossier, `donnees\\`, a la racine du projet ; il n'est jamais envoye sur GitHub (.gitignore) :

    donnees\\
      apk\\                      les 3 APK francais (base.apk, split_config.arm64_v8a.apk, split_UnityDataAssetPack.apk)
      sauvegardes\\
        mobile\\<date>\\          copie de tes sauvegardes du telephone (data1.dat ...) : lues, jamais modifiees ; la plus recente est utilisee
        portage\\                les sauvegardes ecrites par le portage (data1.dat a data5.dat, data9.dat)
        etats\\                  les etats instantanes (etat_01.dqs ...)
        avant_import_<date>\\    copies de securite faites avant chaque import de sauvegardes
      cache\\                    ce que le portage calcule a partir des APK (cartes, sprites, sons, menus) : sans danger a effacer
      reglages\\                 reglages.json, historique_favoris.json, historique_messages.json
      journaux\\                 erreurs_fenetre.log

Deux variables d'environnement, pour les tests et les installations particulieres :
  DQ4_DONNEES : un autre emplacement pour tout le dossier `donnees`.
  DQ4_JEUX    : (ancien fonctionnement) un dossier « jeux\\DQ4 » contenant `patched_apks` et `saves\\<date>` ; il remplace `donnees\\apk` et `donnees\\sauvegardes\\mobile`.

`migrer()` reprend l'ancienne disposition (jeux\\DQ4, dq4_pc\\cache, dq4_pc\\sauvegardes, dq4_pc\\reglages.json ...) : elle COPIE (ou, pour le cache seulement, deplace) vers la nouvelle,
sans jamais ecraser un fichier deja present et sans rien supprimer. Elle est relancee a chaque demarrage (sans effet quand il n'y a plus rien a reprendre)."""
import glob
import os
import shutil

CODE = os.path.dirname(os.path.abspath(__file__))                 # .../dq4-portage/dq4_pc
RACINE = os.path.dirname(CODE)                                    # .../dq4-portage


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
        self.mobile = os.path.join(self.jeux_ancien, 'saves') if self.jeux_ancien else os.path.join(self.sauvegardes, 'mobile')
        self.portage = os.path.join(self.sauvegardes, 'portage')
        self.etats = os.path.join(self.sauvegardes, 'etats')
        self.cache = os.path.join(self.donnees, 'cache')
        self.reglages_dir = os.path.join(self.donnees, 'reglages')
        self.reglages = os.path.join(self.reglages_dir, 'reglages.json')
        self.favoris = os.path.join(self.reglages_dir, 'historique_favoris.json')
        self.journaux = os.path.join(self.donnees, 'journaux')
        self.journal_fenetre = os.path.join(self.journaux, 'erreurs_fenetre.log')

    # ---- sauvegardes -------------------------------------------------------------------------------------------------------------
    def sauvegarde_mobile_recente(self):
        """Dossier de la sauvegarde du telephone la plus recente (`mobile\\<date>`, la date se trie comme l'ordre alphabetique), ou None."""
        dossiers = sorted(d for d in glob.glob(os.path.join(self.mobile, '*')) if os.path.isdir(d))
        return dossiers[-1] if dossiers else None

    def dossier_etats(self, ecriture):
        """Dossier des etats instantanes pour ce dossier d'ecriture : `sauvegardes\\etats` avec l'emplacement habituel (`sauvegardes\\portage`), sinon `<ecriture>\\etats` (tests, --saves-ecriture)."""
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


def migrer(d=None, log=print):
    """Reprend l'ancienne disposition dans `donnees\\`. -> liste de phrases decrivant ce qui a ete fait (vide : rien a faire).
    Copie sans jamais ecraser ni supprimer, sauf le cache (deplace d'un coup si `donnees\\cache` n'existe pas, sinon laisse tel quel) ; ne fait rien avec DQ4_DONNEES / DQ4_JEUX non reconnus."""
    d = d or DOSSIERS
    fait = []
    code = os.path.join(d.racine, 'dq4_pc')
    # 1. cache : meme volume, donc un simple renommage (il pese plusieurs centaines de Mo)
    ancien = os.path.join(code, 'cache')
    if os.path.isdir(ancien) and not os.path.exists(d.cache):
        try:
            os.makedirs(os.path.dirname(d.cache), exist_ok=True); os.replace(ancien, d.cache)
            fait.append('cache deplace : dq4_pc\\cache -> donnees\\cache')
        except OSError as ex:
            fait.append('cache NON deplace (%s) : il sera recalcule' % ex)
    # 2. APK francais : copies (jeux\DQ4\patched_apks -> donnees\apk)
    jeux = os.path.join(d.racine, 'jeux', 'DQ4')
    if not d.jeux_ancien and os.path.isdir(os.path.join(jeux, 'patched_apks')) and not glob.glob(os.path.join(d.apk, '*.apk')):
        n = _copier_arbre(os.path.join(jeux, 'patched_apks'), d.apk, log, 0)
        if n: fait.append('%d fichier(s) APK copie(s) : jeux\\DQ4\\patched_apks -> donnees\\apk' % n)
    # 3. sauvegardes du telephone : jeux\DQ4\saves\<date> -> donnees\sauvegardes\mobile\<date>
    if not d.jeux_ancien and os.path.isdir(os.path.join(jeux, 'saves')):
        n = 0
        for dossier in sorted(glob.glob(os.path.join(jeux, 'saves', '*'))):
            if os.path.isdir(dossier): n += _copier_arbre(dossier, os.path.join(d.mobile, os.path.basename(dossier)), log, 0)
        if n: fait.append('%d fichier(s) de sauvegardes du telephone copie(s) : jeux\\DQ4\\saves -> donnees\\sauvegardes\\mobile' % n)
    # 4. sauvegardes du portage : dq4_pc\sauvegardes\{data*.dat, etats\, avant_import_*\}
    ancien = os.path.join(code, 'sauvegardes')
    if os.path.isdir(ancien):
        n = 0
        for f in glob.glob(os.path.join(ancien, '*')):
            nom = os.path.basename(f)
            if os.path.isfile(f): n += _copier(f, os.path.join(d.portage, nom), log, 0)
            elif nom == 'etats': n += _copier_arbre(f, d.etats, log, 0)
            elif nom.startswith('avant_import_'): n += _copier_arbre(f, os.path.join(d.sauvegardes, nom), log, 0)
        if n: fait.append('%d fichier(s) de sauvegardes du portage copie(s) : dq4_pc\\sauvegardes -> donnees\\sauvegardes' % n)
    # 5. reglages et favoris de l'historique
    n = 0
    for nom in ('reglages.json', 'historique_favoris.json', 'historique_messages.json'):
        src = os.path.join(code, nom)
        if os.path.isfile(src): n += _copier(src, os.path.join(d.reglages_dir, nom), log, 0)
    if n: fait.append('%d fichier(s) de reglages copie(s) : dq4_pc -> donnees\\reglages' % n)
    # 6. journal des erreurs de la fenetre
    src = os.path.join(code, 'erreurs_fenetre.log')
    if os.path.isfile(src) and _copier(src, d.journal_fenetre, log, 0): fait.append('journal des erreurs copie : donnees\\journaux')
    for ph in fait: log('Migration : ' + ph)
    return fait


if __name__ == '__main__':           # `python -m dq4_pc.chemins` : la reprise seule (lancee par lancer_dq4.bat avant le jeu)
    migrer()
