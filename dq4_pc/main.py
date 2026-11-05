"""Point d'entree du portage : `python -m dq4_pc` (c'est ce que fait `launch_dq4.bat`, a la racine du projet).

Lit les arguments, reprend l'ancienne disposition des fichiers si besoin (chemins.migrer), puis ouvre la fenetre du jeu (fenetre/jeu.py).
Tous les dossiers par defaut viennent de paths.py (dossier `data` a la racine du projet)."""
import argparse
import os
import sys
import pyglet
from dq4_pc import paths as CH
from dq4_pc import language as LG
from dq4_pc.language import tr
from dq4_pc.window.game import Game
from dq4_pc.persistence import settings as RG


def settings_file(argv, d):
    """Le fichier de reglages de cette execution : `--settings` de la ligne de commande s'il est donne, sinon celui par defaut (c'est de lui qu'on lit la langue AVANT de construire le parseur : son aide est dans cette langue)."""
    a = list(sys.argv[1:] if argv is None else argv)
    for i, x in enumerate(a):
        if x == '--reglages' and i + 1 < len(a): return a[i + 1]
        if x.startswith('--reglages='): return x.split('=', 1)[1]
    return d.settings


def set_language(argv, d):
    """D-238 : la langue de l'outil (reglage « langue » de reglages.json) pour les messages de la console et l'aide, avant que les reglages soient charges. -> 'fr' ou 'en'."""
    return LG.select_language(LG.read_setting(settings_file(argv, d)))


def build_parser(d):
    """Le parseur de la ligne de commande, dans la langue courante (voir set_language) : `python -m dq4_pc --help`."""
    ap = argparse.ArgumentParser(prog='dq4_pc')
    ap.add_argument('--apk', default=d.apk, help=tr('dossier des 3 APK (version francaise) ; par defaut donnees\\apk'))
    ap.add_argument('--saves-lecture', dest='saves_read', default=None, help=tr('dossier de lecture supplementaire contenant data1.dat... (tests ; par defaut : aucun, le jeu lit et ecrit dans donnees\\sauvegardes)'))
    ap.add_argument('--saves-ecriture', dest='saves_write', default=d.portage, help=tr('dossier des sauvegardes (data1.dat... lus et ecrits par le jeu) ; par defaut donnees\\sauvegardes (les etats instantanes sont dans donnees\\sauvegardes\\etats)'))
    ap.add_argument('--cache', default=d.cache, help=tr('dossier des fichiers calcules a partir des APK ; par defaut donnees\\cache'))
    ap.add_argument('--slot', type=int, default=0, help=tr('numero de sauvegarde a charger directement (1-5) en sautant l\'ecran-titre ; 0 (defaut) = le jeu demarre par ses logos, son titre et son menu de depart'))
    ap.add_argument('--sans-logos', action='store_true', help=tr('saute les logos d\'entree (SQUARE ENIX, ArtePiazza)'))
    ap.add_argument('--logos', action='store_true', help=tr('(test) joue les logos meme pour une capture'))
    ap.add_argument('--largeur', dest='width_px', type=int, default=None, help=tr('largeur de la fenetre (par defaut : celle du menu Echap, sinon 1280)')); ap.add_argument('--hauteur', dest='height_px', type=int, default=None)
    ap.add_argument('--auto-message', type=int, default=0, help=tr('ferme automatiquement le message affiche apres le chargement'))
    ap.add_argument('--ui-simple', action='store_true', help=tr('menus simples (zones de texte) au lieu des fenetres d\'origine'))
    ap.add_argument('--clics', dest='clicks', default=None, help=tr('(test) clics de souris simules : "image:x:y,image:x:y:d,..." (d = 1 clic droit, 2 survol sans clic)'))
    ap.add_argument('--msg-origine', action='store_true', help=tr('garde la fenetre de message du terrain a sa place d\'origine (portrait) au lieu de la descendre en bas de l\'ecran'))
    ap.add_argument('--ui-pos', default='centre', choices=['centre', 'droite', 'gauche'], help=tr('position de la colonne d\'interface d\'origine (portrait 450 x 800) dans la fenetre 16/9'))
    ap.add_argument('--sans-preparation', action='store_true', help=tr('(test) ne prepare pas le cache des cartes, sprites et monstres en arriere-plan'))
    ap.add_argument('--hd', type=int, default=None, help=tr('sprites : 0 originaux (pixels nets), 1 EPX, 4 pixel perfect (2 et 3, retires, valent 1) ; par defaut celui du menu Echap'))
    ap.add_argument('--sans-son', action='store_true', help=tr('coupe le son pour cette session (le menu Echap permet de le remettre)'))
    ap.add_argument('--volume-musique', dest='music_volume', type=float, default=None, help=tr('volume des musiques (0 a 1) ; par defaut celui du menu Echap'))
    ap.add_argument('--volume-bruitages', dest='sfx_volume', type=float, default=None, help=tr('volume des bruitages (0 a 1) ; par defaut celui du menu Echap'))
    ap.add_argument('--plein-ecran', dest='full_screen', type=int, choices=(0, 1, 2), default=None, help=tr('0 = lance le jeu en fenetre, 1 = en plein ecran (fenetre sans bordure a la resolution du bureau) ; 2 (ancien plein ecran exclusif, supprime) vaut 1 ; la fenetre est creee directement dans ce mode ; par defaut le reglage du menu Echap (les captures de test restent en fenetre)'))
    ap.add_argument('--correction-bords', dest='edge_correction', type=int, default=None, choices=range(0, 101), metavar='0-100', help=tr("(debogage) correction de l'inclinaison des sprites des villes pres des bords gauche / droit de l'ecran, en pourcentage : 0 = aucune (le panneau d'origine, penche vers l'exterieur), 100 = complete ; par defaut toujours complete, ce n'est plus un reglage du joueur (variable d'environnement DQ_CORRECTION_BORDS pour la meme chose)"))
    ap.add_argument('--msaa', type=int, default=None, help=tr('anticrenelage materiel (0 = aucun, 4 = x4) ; par defaut celui du menu Echap'))
    ap.add_argument('--reglages', dest='settings', default=d.settings, help=tr('fichier des reglages du joueur (menu Echap : affichage, son, touches)'))
    ap.add_argument('--historique', dest='history', default=d.favorites, help=tr('fichier des favoris de l\'historique (dans donnees\\reglages, jamais dans le dossier des sauvegardes) ; le reste de l\'historique n\'est pas conserve'))
    ap.add_argument('--script-combat', dest='battle_script', default=None, help=tr('(test) touches pendant un combat : "n:masque,..." (n = images depuis le debut du combat)'))
    ap.add_argument('--shots-effet', dest='shots_effect', default=None, help=tr('(test) captures a ces images de l\'effet de debut de combat : "1,10,30,..."'))
    ap.add_argument('--shots-combat', dest='shots_battle', default=None, help=tr('(test) captures intermediaires a ces images de combat : "30,60,..."'))
    ap.add_argument('--images-combat', type=int, default=0, help=tr('(test) prend la capture N images apres le debut d\'un combat'))
    ap.add_argument('--force-champ', type=int, default=0, help=tr('(test) force le passage a la carte du monde a cette image'))
    ap.add_argument('--touches-test', dest='keys_test', default=None, help=tr('(test) touches pressees : "image_de_boucle:NOM,..." (noms pyglet : ESCAPE, DOWN, RETURN...)'))
    ap.add_argument('--options-test', default=None, help=tr('(test) options de la page Affichage appliquees en cours de route : "image:Libelle=valeur;image:Libelle=valeur" (valeur JSON)'))
    ap.add_argument('--shots-boucle', dest='shots_loop', default=None, help=tr('(test) captures <shot>_b<n>.png a ces images de boucle (menu Echap compris) ; la derniere quitte'))
    ap.add_argument('--shot', default=None, help=tr('(test) enregistre une capture puis quitte'))
    ap.add_argument('--images', dest='frames', type=int, default=60)
    ap.add_argument('--script', default=None, help=tr('(test) ex. "20:2,30:0" : image:masque de touches'))
    return ap


def main(argv=None):
    d = CH.FOLDERS
    set_language(argv, d)             # (avant la migration : ses messages sont dans la langue de l'outil)
    try: CH.migrate(d)
    except Exception as ex: print(tr('Migration des fichiers impossible (%r) : le jeu continue avec les dossiers actuels.') % (ex,), flush=True)
    set_language(argv, d)             # (la migration a pu amener reglages.json a sa place)
    ap = build_parser(d)
    a = ap.parse_args(argv)
    reg = RG.Settings(a.settings)
    LG.select_language(reg['langue'])          # langue de l'outil (D-238) ; les textes du jeu ne changent pas
    if a.hd is None: a.hd = reg['mode_sprites']
    else: a.hd = reg['mode_sprites'] = RG.valid_sprites_mode(a.hd)
    if a.msaa is None: a.msaa = reg['msaa']
    else: reg['msaa'] = a.msaa
    if a.full_screen is None: a.full_screen = 0 if a.shot else reg['mode_fenetre']
    else: a.full_screen = reg['mode_fenetre'] = RG.valid_window_mode(a.full_screen)          # (2 = l'ancien plein ecran exclusif : 1)
    rs = reg['resolution'] if isinstance(reg['resolution'], (list, tuple)) and len(reg['resolution']) == 2 else (1920, 1080)
    if a.width_px is None: a.width_px = int(rs[0]) if a.height_px is None else int(round(a.height_px * 16 / 9))
    if a.height_px is None: a.height_px = int(rs[1]) if a.width_px == int(rs[0]) else int(round(a.width_px * 9 / 16))
    if a.music_volume is None: a.music_volume = reg['volume_musique']
    if a.sfx_volume is None: a.sfx_volume = reg['volume_bruitages']
    print(tr('Jeu : APK dans %s') % a.apk, flush=True)
    if not os.path.isfile(os.path.join(a.apk, 'base.apk')):
        print(tr('\nLes APK francais sont introuvables.\nMets base.apk, split_config.arm64_v8a.apk et split_UnityDataAssetPack.apk dans :\n   %s\n(et, si tu en as une, les fichiers data1.dat... de ta sauvegarde du telephone dans %s). Autre dossier : set DQ4_DONNEES=chemin\\vers\\donnees') % (os.path.normpath(a.apk), d.saves), flush=True)
        sys.exit(1)
    sys.setswitchinterval(0.001)      # le calcul HD en tache de fond ne doit pas retarder le dessin
    if a.saves_read is None:
        a.saves_read = d.recent_mobile_save() or a.saves_write
    if a.script is not None:
        sc = {}; cur = 0; pts = sorted((int(x.split(':')[0]), int(x.split(':')[1], 0)) for x in a.script.split(','))
        a.script = {}
        for n in range(0, 100000):
            if n > a.frames + 5: break
            for (i, m) in pts:
                if n >= i: cur = m
            a.script[n] = cur
    lookup_key = lambda t: (int(t[1:].split('+')[0]), int((t[1:].split('+') + ['0'])[1])) if t[:1] == 'c' else int(t)
    a.keys_test = [(lookup_key(x.split(':')[0]), x.split(':')[1]) for x in a.keys_test.split(',')] if a.keys_test else []
    a.options_test = [(int(x.split(':', 1)[0]),) + tuple(x.split(':', 1)[1].split('=', 1)) for x in a.options_test.split(';')] if a.options_test else []
    a.shots_loop = set(lookup_key(x) for x in a.shots_loop.split(',')) if a.shots_loop else set()
    if a.shots_battle: a.shots_battle = set(int(x) for x in a.shots_battle.split(','))
    if a.shots_effect: a.shots_effect = set(int(x) for x in a.shots_effect.split(','))
    if a.clicks: a.clicks = [tuple(int(v) for v in c.split(':')) + (0,) * (4 - len(c.split(':'))) for c in a.clicks.split(',')]
    if a.battle_script is not None:
        pts = sorted((int(x.split(':')[0]), int(x.split(':')[1], 0)) for x in a.battle_script.split(','))
        sc = {}; cur = 0
        for n in range(0, 20000):
            for (i, m) in pts:
                if n >= i: cur = m
            sc[n] = cur
        a.battle_script = sc
    Game(a, reg)
    pyglet.app.run(interval=0)       # la boucle fixe (Game._boucle) tourne avant chaque dessin ; le dessin suit la synchronisation verticale


if __name__ == '__main__':
    main()
