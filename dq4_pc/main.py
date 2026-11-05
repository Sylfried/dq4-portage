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
    ap.add_argument('--apk', default=d.apk, help='folder of the 3 APK files (French version); default data\\apk')
    ap.add_argument('--saves-lecture', dest='saves_read', default=None, help='extra read-only folder containing data1.dat... (tests; default: none, the game reads and writes in data\\saves)')
    ap.add_argument('--saves-ecriture', dest='saves_write', default=d.portage, help='saves folder (data1.dat... read and written by the game); default data\\saves (savestates are in data\\saves\\savestates)')
    ap.add_argument('--cache', default=d.cache, help='folder of the files computed from the APKs; default data\\cache')
    ap.add_argument('--slot', type=int, default=0, help='save number to load directly (1-5), skipping the title screen; 0 (default) = the game starts with its logos, its title and its start menu')
    ap.add_argument('--sans-logos', action='store_true', help='skips the intro logos (SQUARE ENIX, ArtePiazza)')
    ap.add_argument('--logos', action='store_true', help='(test) plays the logos even for a screenshot')
    ap.add_argument('--largeur', dest='width_px', type=int, default=None, help='window width (default: the one from the Esc menu, otherwise 1280)'); ap.add_argument('--hauteur', dest='height_px', type=int, default=None)
    ap.add_argument('--auto-message', type=int, default=0, help='automatically closes the message shown after loading')
    ap.add_argument('--ui-simple', action='store_true', help='simple menus (text boxes) instead of the original windows')
    ap.add_argument('--clics', dest='clicks', default=None, help='(test) simulated mouse clicks: "frame:x:y,frame:x:y:d,..." (d = 1 right click, 2 hover without click)')
    ap.add_argument('--msg-origine', action='store_true', help='keeps the field message window at its original (portrait) position instead of moving it to the bottom of the screen')
    ap.add_argument('--ui-pos', default='centre', choices=['centre', 'droite', 'gauche'], help='position of the original interface column (portrait 450 x 800) in the 16/9 window')
    ap.add_argument('--sans-preparation', action='store_true', help='(test) does not prepare the map, sprite and monster cache in the background')
    ap.add_argument('--hd', type=int, default=None, help='sprites: 0 original (sharp pixels), 1 EPX, 4 pixel perfect (2 and 3, removed, count as 1); default: the one from the Esc menu')
    ap.add_argument('--sans-son', action='store_true', help='turns the sound off for this session (the Esc menu can turn it back on)')
    ap.add_argument('--volume-musique', dest='music_volume', type=float, default=None, help='music volume (0 to 1); default: the one from the Esc menu')
    ap.add_argument('--volume-bruitages', dest='sfx_volume', type=float, default=None, help='sound effects volume (0 to 1); default: the one from the Esc menu')
    ap.add_argument('--plein-ecran', dest='full_screen', type=int, choices=(0, 1, 2), default=None, help='0 = starts the game in a window, 1 = full screen (borderless window at the desktop resolution); 2 (former exclusive full screen, removed) counts as 1; the window is created directly in this mode; default: the Esc menu setting (test screenshots stay windowed)')
    ap.add_argument('--correction-bords', dest='edge_correction', type=int, default=None, choices=range(0, 101), metavar='0-100', help="(debug) correction of the tilt of town sprites near the left / right edges of the screen, as a percentage: 0 = none (the original billboard, leaning outwards), 100 = full; default always full, it is no longer a player setting (environment variable DQ_CORRECTION_BORDS for the same thing)")
    ap.add_argument('--msaa', type=int, default=None, help='hardware antialiasing (0 = none, 4 = x4); default: the one from the Esc menu')
    ap.add_argument('--reglages', dest='settings', default=d.settings, help='player settings file (Esc menu: display, sound, keys)')
    ap.add_argument('--historique', dest='history', default=d.favorites, help='history favorites file (in data\\settings, never in the saves folder); the rest of the history is not kept')
    ap.add_argument('--script-combat', dest='battle_script', default=None, help='(test) keys during a battle: "n:mask,..." (n = frames since the start of the battle)')
    ap.add_argument('--shots-effet', dest='shots_effect', default=None, help='(test) screenshots at these frames of the battle start effect: "1,10,30,..."')
    ap.add_argument('--shots-combat', dest='shots_battle', default=None, help='(test) intermediate screenshots at these battle frames: "30,60,..."')
    ap.add_argument('--images-combat', type=int, default=0, help='(test) takes the screenshot N frames after the start of a battle')
    ap.add_argument('--force-champ', type=int, default=0, help='(test) forces the switch to the world map at this frame')
    ap.add_argument('--touches-test', dest='keys_test', default=None, help='(test) pressed keys: "loop_frame:NAME,..." (pyglet names: ESCAPE, DOWN, RETURN...)')
    ap.add_argument('--options-test', default=None, help='(test) Display page options applied along the way: "frame:Label=value;frame:Label=value" (JSON value)')
    ap.add_argument('--shots-boucle', dest='shots_loop', default=None, help='(test) screenshots <shot>_b<n>.png at these loop frames (Esc menu included); the last one quits')
    ap.add_argument('--shot', default=None, help='(test) saves a screenshot then quits')
    ap.add_argument('--images', dest='frames', type=int, default=60)
    ap.add_argument('--script', default=None, help='(test) e.g. "20:2,30:0": frame:key mask')
    return ap


def main(argv=None):
    d = CH.FOLDERS
    set_language(argv, d)             # (avant la migration : ses messages sont dans la langue de l'outil)
    try: CH.migrate(d)
    except Exception as ex: print('File migration failed (%r): the game continues with the current folders.' % (ex,), flush=True)
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
    print('Game: APK files in %s' % a.apk, flush=True)
    if not os.path.isfile(os.path.join(a.apk, 'base.apk')):
        print('\nThe French APK files were not found.\nPut base.apk, split_config.arm64_v8a.apk and split_UnityDataAssetPack.apk in:\n   %s\n(and, if you have one, the data1.dat... files of your phone save in %s). Other folder: set DQ4_DATA=path\\to\\data' % (os.path.normpath(a.apk), d.saves), flush=True)
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
