"""Point d'entree du portage : `python -m dq4_pc` (c'est ce que fait `lancer_dq4.bat`, a la racine du projet).

Lit les arguments, reprend l'ancienne disposition des fichiers si besoin (chemins.migrer), puis ouvre la fenetre du jeu (fenetre/jeu.py).
Tous les dossiers par defaut viennent de chemins.py (dossier `donnees` a la racine du projet)."""
import argparse
import os
import sys
import pyglet
from dq4_pc import chemins as CH
from dq4_pc import langue as LG
from dq4_pc.langue import tr
from dq4_pc.fenetre.jeu import Jeu
from dq4_pc.persistance import reglages as RG


def fichier_reglages(argv, d):
    """Le fichier de reglages de cette execution : `--reglages` de la ligne de commande s'il est donne, sinon celui par defaut (c'est de lui qu'on lit la langue AVANT de construire le parseur : son aide est dans cette langue)."""
    a = list(sys.argv[1:] if argv is None else argv)
    for i, x in enumerate(a):
        if x == '--reglages' and i + 1 < len(a): return a[i + 1]
        if x.startswith('--reglages='): return x.split('=', 1)[1]
    return d.reglages


def regler_langue(argv, d):
    """D-238 : la langue de l'outil (reglage « langue » de reglages.json) pour les messages de la console et l'aide, avant que les reglages soient charges. -> 'fr' ou 'en'."""
    return LG.regler(LG.lire_reglage(fichier_reglages(argv, d)))


def construire_parseur(d):
    """Le parseur de la ligne de commande, dans la langue courante (voir regler_langue) : `python -m dq4_pc --help`."""
    ap = argparse.ArgumentParser(prog='dq4_pc')
    ap.add_argument('--apk', default=d.apk, help=tr('dossier des 3 APK (version francaise) ; par defaut donnees\\apk'))
    ap.add_argument('--saves-lecture', default=None, help=tr('dossier de lecture supplementaire contenant data1.dat... (tests ; par defaut : aucun, le jeu lit et ecrit dans donnees\\sauvegardes)'))
    ap.add_argument('--saves-ecriture', default=d.portage, help=tr('dossier des sauvegardes (data1.dat... lus et ecrits par le jeu) ; par defaut donnees\\sauvegardes (les etats instantanes sont dans donnees\\sauvegardes\\etats)'))
    ap.add_argument('--cache', default=d.cache, help=tr('dossier des fichiers calcules a partir des APK ; par defaut donnees\\cache'))
    ap.add_argument('--slot', type=int, default=0, help=tr('numero de sauvegarde a charger directement (1-5) en sautant l\'ecran-titre ; 0 (defaut) = le jeu demarre par ses logos, son titre et son menu de depart'))
    ap.add_argument('--sans-logos', action='store_true', help=tr('saute les logos d\'entree (SQUARE ENIX, ArtePiazza)'))
    ap.add_argument('--logos', action='store_true', help=tr('(test) joue les logos meme pour une capture'))
    ap.add_argument('--largeur', type=int, default=None, help=tr('largeur de la fenetre (par defaut : celle du menu Echap, sinon 1280)')); ap.add_argument('--hauteur', type=int, default=None)
    ap.add_argument('--auto-message', type=int, default=0, help=tr('ferme automatiquement le message affiche apres le chargement'))
    ap.add_argument('--ui-simple', action='store_true', help=tr('menus simples (zones de texte) au lieu des fenetres d\'origine'))
    ap.add_argument('--clics', default=None, help=tr('(test) clics de souris simules : "image:x:y,image:x:y:d,..." (d = 1 clic droit, 2 survol sans clic)'))
    ap.add_argument('--msg-origine', action='store_true', help=tr('garde la fenetre de message du terrain a sa place d\'origine (portrait) au lieu de la descendre en bas de l\'ecran'))
    ap.add_argument('--ui-pos', default='centre', choices=['centre', 'droite', 'gauche'], help=tr('position de la colonne d\'interface d\'origine (portrait 450 x 800) dans la fenetre 16/9'))
    ap.add_argument('--sans-preparation', action='store_true', help=tr('(test) ne prepare pas le cache des cartes, sprites et monstres en arriere-plan'))
    ap.add_argument('--hd', type=int, default=None, help=tr('sprites : 0 originaux (pixels nets), 1 EPX, 4 pixel perfect (2 et 3, retires, valent 1) ; par defaut celui du menu Echap'))
    ap.add_argument('--sans-son', action='store_true', help=tr('coupe le son pour cette session (le menu Echap permet de le remettre)'))
    ap.add_argument('--volume-musique', type=float, default=None, help=tr('volume des musiques (0 a 1) ; par defaut celui du menu Echap'))
    ap.add_argument('--volume-bruitages', type=float, default=None, help=tr('volume des bruitages (0 a 1) ; par defaut celui du menu Echap'))
    ap.add_argument('--plein-ecran', type=int, choices=(0, 1, 2), default=None, help=tr('0 = lance le jeu en fenetre, 1 = en plein ecran (fenetre sans bordure a la resolution du bureau) ; 2 (ancien plein ecran exclusif, supprime) vaut 1 ; la fenetre est creee directement dans ce mode ; par defaut le reglage du menu Echap (les captures de test restent en fenetre)'))
    ap.add_argument('--correction-bords', type=int, default=None, choices=range(0, 101), metavar='0-100', help=tr("(debogage) correction de l'inclinaison des sprites des villes pres des bords gauche / droit de l'ecran, en pourcentage : 0 = aucune (le panneau d'origine, penche vers l'exterieur), 100 = complete ; par defaut toujours complete, ce n'est plus un reglage du joueur (variable d'environnement DQ_CORRECTION_BORDS pour la meme chose)"))
    ap.add_argument('--msaa', type=int, default=None, help=tr('anticrenelage materiel (0 = aucun, 4 = x4) ; par defaut celui du menu Echap'))
    ap.add_argument('--reglages', default=d.reglages, help=tr('fichier des reglages du joueur (menu Echap : affichage, son, touches)'))
    ap.add_argument('--historique', default=d.favoris, help=tr('fichier des favoris de l\'historique (dans donnees\\reglages, jamais dans le dossier des sauvegardes) ; le reste de l\'historique n\'est pas conserve'))
    ap.add_argument('--script-combat', default=None, help=tr('(test) touches pendant un combat : "n:masque,..." (n = images depuis le debut du combat)'))
    ap.add_argument('--shots-effet', default=None, help=tr('(test) captures a ces images de l\'effet de debut de combat : "1,10,30,..."'))
    ap.add_argument('--shots-combat', default=None, help=tr('(test) captures intermediaires a ces images de combat : "30,60,..."'))
    ap.add_argument('--images-combat', type=int, default=0, help=tr('(test) prend la capture N images apres le debut d\'un combat'))
    ap.add_argument('--force-champ', type=int, default=0, help=tr('(test) force le passage a la carte du monde a cette image'))
    ap.add_argument('--touches-test', default=None, help=tr('(test) touches pressees : "image_de_boucle:NOM,..." (noms pyglet : ESCAPE, DOWN, RETURN...)'))
    ap.add_argument('--options-test', default=None, help=tr('(test) options de la page Affichage appliquees en cours de route : "image:Libelle=valeur;image:Libelle=valeur" (valeur JSON)'))
    ap.add_argument('--shots-boucle', default=None, help=tr('(test) captures <shot>_b<n>.png a ces images de boucle (menu Echap compris) ; la derniere quitte'))
    ap.add_argument('--shot', default=None, help=tr('(test) enregistre une capture puis quitte'))
    ap.add_argument('--images', type=int, default=60)
    ap.add_argument('--script', default=None, help=tr('(test) ex. "20:2,30:0" : image:masque de touches'))
    return ap


def main(argv=None):
    d = CH.DOSSIERS
    regler_langue(argv, d)             # (avant la migration : ses messages sont dans la langue de l'outil)
    try: CH.migrer(d)
    except Exception as ex: print(tr('Migration des fichiers impossible (%r) : le jeu continue avec les dossiers actuels.') % (ex,), flush=True)
    regler_langue(argv, d)             # (la migration a pu amener reglages.json a sa place)
    ap = construire_parseur(d)
    a = ap.parse_args(argv)
    reg = RG.Reglages(a.reglages)
    LG.regler(reg['langue'])          # langue de l'outil (D-238) ; les textes du jeu ne changent pas
    if a.hd is None: a.hd = reg['mode_sprites']
    else: a.hd = reg['mode_sprites'] = RG.mode_sprites_valide(a.hd)
    if a.msaa is None: a.msaa = reg['msaa']
    else: reg['msaa'] = a.msaa
    if a.plein_ecran is None: a.plein_ecran = 0 if a.shot else reg['mode_fenetre']
    else: a.plein_ecran = reg['mode_fenetre'] = RG.mode_fenetre_valide(a.plein_ecran)          # (2 = l'ancien plein ecran exclusif : 1)
    rs = reg['resolution'] if isinstance(reg['resolution'], (list, tuple)) and len(reg['resolution']) == 2 else (1920, 1080)
    if a.largeur is None: a.largeur = int(rs[0]) if a.hauteur is None else int(round(a.hauteur * 16 / 9))
    if a.hauteur is None: a.hauteur = int(rs[1]) if a.largeur == int(rs[0]) else int(round(a.largeur * 9 / 16))
    if a.volume_musique is None: a.volume_musique = reg['volume_musique']
    if a.volume_bruitages is None: a.volume_bruitages = reg['volume_bruitages']
    print(tr('Jeu : APK dans %s') % a.apk, flush=True)
    if not os.path.isfile(os.path.join(a.apk, 'base.apk')):
        print(tr('\nLes APK francais sont introuvables.\nMets base.apk, split_config.arm64_v8a.apk et split_UnityDataAssetPack.apk dans :\n   %s\n(et, si tu en as une, les fichiers data1.dat... de ta sauvegarde du telephone dans %s). Autre dossier : set DQ4_DONNEES=chemin\\vers\\donnees') % (os.path.normpath(a.apk), d.sauvegardes), flush=True)
        sys.exit(1)
    sys.setswitchinterval(0.001)      # le calcul HD en tache de fond ne doit pas retarder le dessin
    if a.saves_lecture is None:
        a.saves_lecture = d.sauvegarde_mobile_recente() or a.saves_ecriture
    if a.script is not None:
        sc = {}; cur = 0; pts = sorted((int(x.split(':')[0]), int(x.split(':')[1], 0)) for x in a.script.split(','))
        a.script = {}
        for n in range(0, 100000):
            if n > a.images + 5: break
            for (i, m) in pts:
                if n >= i: cur = m
            a.script[n] = cur
    cle = lambda t: (int(t[1:].split('+')[0]), int((t[1:].split('+') + ['0'])[1])) if t[:1] == 'c' else int(t)
    a.touches_test = [(cle(x.split(':')[0]), x.split(':')[1]) for x in a.touches_test.split(',')] if a.touches_test else []
    a.options_test = [(int(x.split(':', 1)[0]),) + tuple(x.split(':', 1)[1].split('=', 1)) for x in a.options_test.split(';')] if a.options_test else []
    a.shots_boucle = set(cle(x) for x in a.shots_boucle.split(',')) if a.shots_boucle else set()
    if a.shots_combat: a.shots_combat = set(int(x) for x in a.shots_combat.split(','))
    if a.shots_effet: a.shots_effet = set(int(x) for x in a.shots_effet.split(','))
    if a.clics: a.clics = [tuple(int(v) for v in c.split(':')) + (0,) * (4 - len(c.split(':'))) for c in a.clics.split(',')]
    if a.script_combat is not None:
        pts = sorted((int(x.split(':')[0]), int(x.split(':')[1], 0)) for x in a.script_combat.split(','))
        sc = {}; cur = 0
        for n in range(0, 20000):
            for (i, m) in pts:
                if n >= i: cur = m
            sc[n] = cur
        a.script_combat = sc
    Jeu(a, reg)
    pyglet.app.run(interval=0)       # la boucle fixe (Jeu._boucle) tourne avant chaque dessin ; le dessin suit la synchronisation verticale


if __name__ == '__main__':
    main()
