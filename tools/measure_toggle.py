"""Mesure ce qui se passe a chaque bascule fenetre <-> plein ecran du jeu : nombre d'appels a pyglet (set_fullscreen, recreation de la fenetre, cacher / montrer, changements de mode du moniteur), d'evenements de
redimensionnement, de trames dessinees (et combien ont une taille qui n'est pas la taille finale) et de reconstructions des tampons du rendu hors ecran (postfx.py). Sert a comparer deux etats du code : on lance le meme
scenario sur chacun et on compare les lignes « BASCULE ».

    python3 tools/measure_toggle.py <dossier dq4_pc a mesurer> [options de window.py...]

Le jeu est lance tel quel (fenetre.main) : les compteurs sont poses de l'exterieur sur la classe Jeu, sur PostFX et sur l'ecran, sans rien changer au code mesure. Une bascule est detectee a l'entree de
Game.set_full_screen (code d'aujourd'hui) ou de Game.regler_mode_fenetre (code de la #42) ; le compte s'arrete 12 trames apres la fin de l'appel. Une ligne par bascule :
    BASCULE n=1 vers=1 : set_fullscreen=1 recreations=1 cache/montre=1/1 mode_moniteur=0 (restore_mode=0) redimensionnements=3 trames=14 (instables=0) tampons=1 ... || fenetre visible sans image : 0.0 ms (tampons refaits pendant ce temps : 0, deplacements : 0)
« fenetre visible sans image » = temps entre l'affichage de la fenetre (visible(True)) et le premier flip qui la remplit : 0 si une image complete a deja ete affichee avant de la montrer (code d'aujourd'hui) ; avec le code
de la #42, la fenetre apparait d'abord, l'image n'arrive qu'a la trame suivante (apres la reconstruction des tampons du rendu hors ecran et, au retour en fenetre, le deplacement de la fenetre). Sous Mesa / xvfb : 250 a 280 ms
vers le plein ecran, 65 a 70 ms au retour, contre 0 ; sur un vrai GPU les durees seront bien plus courtes, la structure (fenetre visible avant sa premiere image) est la meme.
A lancer sous xvfb (un seul a la fois sur la machine : voir /tmp/run_wt.sh). Les bascules se declenchent par les touches du harnais :
    --touches-test "60:F11,120:F11"                       (F11 : code d'aujourd'hui = fenetre <-> plein ecran ; code de la #42 = plein ecran exclusif)
    --options-test "60:Fenêtre=1;120:Fenêtre=0"            (code de la #42 : plein ecran sans bordure) ; "60:Plein écran=true;120:Plein écran=false" (code d'aujourd'hui)

LIMITE : X11 (xvfb, sans gestionnaire de fenetres) n'est pas Windows. Les nombres d'evenements de pyglet different (sous Windows, set_fullscreen = cacher, changer le style, redimensionner, montrer, replacer, plus les messages
WM_SIZE / WM_MOVE) ; ils montrent ce que le code du jeu demande et fait faire, pas ce que l'ecran du joueur affiche.
"""
import os, sys, time, json

if len(sys.argv) < 2 or not os.path.isdir(sys.argv[1]):
    print(__doc__); sys.exit(2)
TREE = os.path.abspath(sys.argv[1])
sys.argv = [os.path.join(TREE, 'window.py')] + sys.argv[2:]
sys.path.insert(0, TREE)
import pyglet
from dq4_pc.window import game as WND
from dq4_pc.render import postfx as PF

FRAMES_AFTER = 12            # trames comptees apres la fin de l'appel de bascule
STATE = {'rec': None, 'n': 0, 'fait': []}


def evt(*e):
    r = STATE['rec']
    if r is not None: r['ev'].append(e); r['t'].append(time.perf_counter())


def finish(r):
    ev = r['ev']; drawn_frames = [e for e in ev if e[0] == 'trame']
    final = drawn_frames[-1][1:] if drawn_frames else None
    c = lambda name_str: sum(1 for e in ev if e[0] == name_str)
    shown = sum(1 for e in ev if e[0] == 'visible' and e[1]); cache = sum(1 for e in ev if e[0] == 'visible' and not e[1])
    d = dict(n=r['n'], vers=r['vers'], set_fullscreen=c('set_fullscreen'), recreations=c('recreate'), cache_montre='%d/%d' % (cache, shown), mode_moniteur=c('set_mode'), restore_mode=c('restore_mode'), set_size=c('set_size'), set_location=c('set_location'),
             redimensionnements=c('resize'), drawn_frames=len(drawn_frames), instables=sum(1 for t in drawn_frames if t[1:] != final), tampons=c('tampons'), flips=c('flip'), duree_ms=round(r['duree'] * 1000, 1))
    # ce que le joueur voit : la fenetre est « montree » (visible(True)) ; une image complete est « affichee » par le premier flip ; ce qui est dessine ou deplace entre les deux se voit
    names = [e[0] for e in ev]; t = r['t']; i_shown = next((i for i, e in enumerate(ev) if e[0] == 'visible' and e[1]), None)
    if i_shown is None: d['montree_sans_image_ms'] = None; d['image_avant_montrer'] = None; d['tampons_fenetre_visible'] = 0; d['deplacements_fenetre_visible'] = 0
    else:
        i_recreated = max([i for i, n in enumerate(names) if n == 'recreate' and i <= i_shown] or [-1])
        before = any(names[i] == 'flip' for i in range(i_recreated + 1, i_shown))                  # une image a deja ete affichee depuis la recreation : la fenetre apparait avec son contenu
        i_flip = next((i for i in range(i_shown, len(ev)) if names[i] == 'flip'), None)
        d['image_avant_montrer'] = before
        d['montree_sans_image_ms'] = 0.0 if before or i_flip is None else round((t[i_flip] - t[i_shown]) * 1000, 1)
        end = len(ev) if before else (i_flip if i_flip is not None else len(ev))
        d['tampons_fenetre_visible'] = sum(1 for i in range(i_shown, end) if names[i] == 'tampons') if not before else 0       # reconstructions des tampons du rendu hors ecran pendant que la fenetre est visible sans image
        d['deplacements_fenetre_visible'] = sum(1 for i in range(i_shown, end) if names[i] in ('set_location', 'set_size')) if not before else 0
    seq = []                                    # sequence compacte (les repetitions consecutives sont regroupees)
    for e in ev:
        s = e[0] if len(e) == 1 else '%s(%s)' % (e[0], ','.join(str(x) for x in e[1:]))
        if seq and seq[-1][0] == s: seq[-1][1] += 1
        else: seq.append([s, 1])
    d['sequence'] = ' '.join(s if k == 1 else '%sx%d' % (s, k) for s, k in seq)
    line = 'BASCULE n=%(n)d vers=%(vers)s : set_fullscreen=%(set_fullscreen)d recreations=%(recreations)d cache/montre=%(cache_montre)s mode_moniteur=%(mode_moniteur)d (restore_mode=%(restore_mode)d) set_size=%(set_size)d set_location=%(set_location)d redimensionnements=%(redimensionnements)d trames=%(trames)d (instables=%(instables)d) tampons=%(tampons)d flips=%(flips)d duree=%(duree_ms)sms || fenetre visible sans image : %(montree_sans_image_ms)s ms (tampons refaits pendant ce temps : %(tampons_fenetre_visible)s, deplacements : %(deplacements_fenetre_visible)s)' % d
    print(line, flush=True); print('   sequence :', d['sequence'], flush=True); print('BASCULE_JSON', json.dumps(d, ensure_ascii=False), flush=True)
    STATE['fait'].append(d)


def wrap_text(cls, name_str, before=None, after=None):
    orig = getattr(cls, name_str)
    def f(self, *a, **k):
        if before: before(self, *a, **k)
        r = orig(self, *a, **k)
        if after: after(self, *a, **k)
        return r
    f.__name__ = name_str
    setattr(cls, name_str, f)


def toggle_entry(toward):
    def f(self, *a, **k):
        if STATE['rec'] is not None: return orig(self, *a, **k)
        STATE['n'] += 1
        STATE['rec'] = rec = dict(n=STATE['n'], vers=toward(self, *a), ev=[], t=[], duree=0.0, t0=time.perf_counter(), fin=False, apres=0)
        try: return orig(self, *a, **k)
        finally: rec['duree'] = time.perf_counter() - rec['t0']; rec['fin'] = True
    return f


# ---- crochets sur la classe du jeu
Game = WND.Game
wrap_text(Game, 'set_fullscreen', lambda self, fs=True, *a, **k: evt('set_fullscreen', bool(fs)))
wrap_text(Game, '_recreate', lambda self, ch: evt('recreate'))
wrap_text(Game, 'set_visible', lambda self, v=True: evt('visible', bool(v)))
wrap_text(Game, 'set_size', lambda self, w, h: evt('set_size', w, h))
wrap_text(Game, 'set_location', lambda self, x, y: evt('set_location', x, y))
wrap_text(Game, 'flip', lambda self: evt('flip'))
wrap_text(Game, '_on_internal_resize', lambda self, w, h: evt('resize', w, h))
orig_draw = Game.on_draw


def on_draw(self):
    r = STATE['rec']
    if r is not None: r['ev'].append(('trame',) + tuple(self.get_framebuffer_size())); r['t'].append(time.perf_counter())
    ret = orig_draw(self)
    if r is not None and r['fin']:
        r['apres'] += 1
        if r['apres'] >= FRAMES_AFTER: STATE['rec'] = None; finish(r)
    return ret


Game.on_draw = on_draw
orig_create = PF.PostFX._create


def create(self, w, h, ms): evt('tampons', w, h, ms); return orig_create(self, w, h, ms)


PF.PostFX._create = create
for name_str in ('set_full_screen', 'regler_mode_fenetre'):          # selon l'etat du code mesure
    if hasattr(Game, name_str):
        orig = getattr(Game, name_str)
        setattr(Game, name_str, toggle_entry(lambda self, v, *a: v))
        break

# changements de mode du moniteur (ancien plein ecran exclusif) : set_mode ; restore_mode est appele par pyglet a chaque retour en fenetre, sans effet sous Windows tant que set_mode n'a jamais ete appele
try:
    screen_page = type(pyglet.display.get_display().get_default_screen())
    for name_str in ('set_mode', 'restore_mode'):
        if hasattr(screen_page, name_str): wrap_text(screen_page, name_str, (lambda n: (lambda self, *a, **k: evt(n)))(name_str))
except Exception as ex: print('mesure_bascule : ecran illisible (%r)' % (ex,), flush=True)

print('mesure_bascule : %s' % TREE, flush=True)
WND.main()
print('mesure_bascule : %d bascule(s) mesuree(s)' % len(STATE['fait']), flush=True)
