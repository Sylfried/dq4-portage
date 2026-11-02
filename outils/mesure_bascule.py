"""Mesure ce qui se passe a chaque bascule fenetre <-> plein ecran du jeu : nombre d'appels a pyglet (set_fullscreen, recreation de la fenetre, cacher / montrer, changements de mode du moniteur), d'evenements de
redimensionnement, de trames dessinees (et combien ont une taille qui n'est pas la taille finale) et de reconstructions des tampons du rendu hors ecran (postfx.py). Sert a comparer deux etats du code : on lance le meme
scenario sur chacun et on compare les lignes « BASCULE ».

    python3 outils/mesure_bascule.py <dossier dq4_pc a mesurer> [options de fenetre.py...]

Le jeu est lance tel quel (fenetre.main) : les compteurs sont poses de l'exterieur sur la classe Jeu, sur PostFX et sur l'ecran, sans rien changer au code mesure. Une bascule est detectee a l'entree de
Jeu.regler_plein_ecran (code d'aujourd'hui) ou de Jeu.regler_mode_fenetre (code de la #42) ; le compte s'arrete 12 trames apres la fin de l'appel. Une ligne par bascule :
    BASCULE n=1 vers=1 : set_fullscreen=1 recreations=1 cache/montre=1/1 mode_moniteur=0 (restore_mode=0) redimensionnements=3 trames=14 (instables=0) tampons=1 ...
A lancer sous xvfb (un seul a la fois sur la machine : voir /tmp/run_wt.sh). Les bascules se declenchent par les touches du harnais :
    --touches-test "60:F11,120:F11"                       (F11 : code d'aujourd'hui = fenetre <-> plein ecran ; code de la #42 = plein ecran exclusif)
    --options-test "60:Fenêtre=1;120:Fenêtre=0"            (code de la #42 : plein ecran sans bordure) ; "60:Plein écran=true;120:Plein écran=false" (code d'aujourd'hui)

LIMITE : X11 (xvfb, sans gestionnaire de fenetres) n'est pas Windows. Les nombres d'evenements de pyglet different (sous Windows, set_fullscreen = cacher, changer le style, redimensionner, montrer, replacer, plus les messages
WM_SIZE / WM_MOVE) ; ils montrent ce que le code du jeu demande et fait faire, pas ce que l'ecran du joueur affiche.
"""
import os, sys, time, json

if len(sys.argv) < 2 or not os.path.isdir(sys.argv[1]):
    print(__doc__); sys.exit(2)
ARBRE = os.path.abspath(sys.argv[1])
sys.argv = [os.path.join(ARBRE, 'fenetre.py')] + sys.argv[2:]
sys.path.insert(0, ARBRE)
import pyglet
import fenetre as FE
import postfx as PF

TRAMES_APRES = 12            # trames comptees apres la fin de l'appel de bascule
ETAT = {'rec': None, 'n': 0, 'fait': []}


def evt(*e):
    r = ETAT['rec']
    if r is not None: r['ev'].append(e)


def finir(r):
    ev = r['ev']; trames = [e for e in ev if e[0] == 'trame']
    final = trames[-1][1:] if trames else None
    c = lambda nom: sum(1 for e in ev if e[0] == nom)
    montre = sum(1 for e in ev if e[0] == 'visible' and e[1]); cache = sum(1 for e in ev if e[0] == 'visible' and not e[1])
    d = dict(n=r['n'], vers=r['vers'], set_fullscreen=c('set_fullscreen'), recreations=c('recreate'), cache_montre='%d/%d' % (cache, montre), mode_moniteur=c('set_mode'), restore_mode=c('restore_mode'), set_size=c('set_size'), set_location=c('set_location'),
             redimensionnements=c('resize'), trames=len(trames), instables=sum(1 for t in trames if t[1:] != final), tampons=c('tampons'), flips=c('flip'), duree_ms=round(r['duree'] * 1000, 1))
    seq = []                                    # sequence compacte (les repetitions consecutives sont regroupees)
    for e in ev:
        s = e[0] if len(e) == 1 else '%s(%s)' % (e[0], ','.join(str(x) for x in e[1:]))
        if seq and seq[-1][0] == s: seq[-1][1] += 1
        else: seq.append([s, 1])
    d['sequence'] = ' '.join(s if k == 1 else '%sx%d' % (s, k) for s, k in seq)
    ligne = 'BASCULE n=%(n)d vers=%(vers)s : set_fullscreen=%(set_fullscreen)d recreations=%(recreations)d cache/montre=%(cache_montre)s mode_moniteur=%(mode_moniteur)d (restore_mode=%(restore_mode)d) set_size=%(set_size)d set_location=%(set_location)d redimensionnements=%(redimensionnements)d trames=%(trames)d (instables=%(instables)d) tampons=%(tampons)d flips=%(flips)d duree=%(duree_ms)sms' % d
    print(ligne, flush=True); print('   sequence :', d['sequence'], flush=True); print('BASCULE_JSON', json.dumps(d, ensure_ascii=False), flush=True)
    ETAT['fait'].append(d)


def envelopper(cls, nom, avant=None, apres=None):
    orig = getattr(cls, nom)
    def f(self, *a, **k):
        if avant: avant(self, *a, **k)
        r = orig(self, *a, **k)
        if apres: apres(self, *a, **k)
        return r
    f.__name__ = nom
    setattr(cls, nom, f)


def entree_bascule(vers):
    def f(self, *a, **k):
        if ETAT['rec'] is not None: return orig(self, *a, **k)
        ETAT['n'] += 1
        ETAT['rec'] = rec = dict(n=ETAT['n'], vers=vers(self, *a), ev=[], duree=0.0, t0=time.perf_counter(), fin=False, apres=0)
        try: return orig(self, *a, **k)
        finally: rec['duree'] = time.perf_counter() - rec['t0']; rec['fin'] = True
    return f


# ---- crochets sur la classe du jeu
Jeu = FE.Jeu
envelopper(Jeu, 'set_fullscreen', lambda self, fs=True, *a, **k: evt('set_fullscreen', bool(fs)))
envelopper(Jeu, '_recreate', lambda self, ch: evt('recreate'))
envelopper(Jeu, 'set_visible', lambda self, v=True: evt('visible', bool(v)))
envelopper(Jeu, 'set_size', lambda self, w, h: evt('set_size', w, h))
envelopper(Jeu, 'set_location', lambda self, x, y: evt('set_location', x, y))
envelopper(Jeu, 'flip', lambda self: evt('flip'))
envelopper(Jeu, '_on_internal_resize', lambda self, w, h: evt('resize', w, h))
orig_draw = Jeu.on_draw


def on_draw(self):
    r = ETAT['rec']
    if r is not None: r['ev'].append(('trame',) + tuple(self.get_framebuffer_size()))
    ret = orig_draw(self)
    if r is not None and r['fin']:
        r['apres'] += 1
        if r['apres'] >= TRAMES_APRES: ETAT['rec'] = None; finir(r)
    return ret


Jeu.on_draw = on_draw
orig_creer = PF.PostFX._creer


def creer(self, w, h, ms): evt('tampons', w, h, ms); return orig_creer(self, w, h, ms)


PF.PostFX._creer = creer
for nom in ('regler_plein_ecran', 'regler_mode_fenetre'):          # selon l'etat du code mesure
    if hasattr(Jeu, nom):
        orig = getattr(Jeu, nom)
        setattr(Jeu, nom, entree_bascule(lambda self, v, *a: v))
        break

# changements de mode du moniteur (ancien plein ecran exclusif) : set_mode ; restore_mode est appele par pyglet a chaque retour en fenetre, sans effet sous Windows tant que set_mode n'a jamais ete appele
try:
    ecran = type(pyglet.display.get_display().get_default_screen())
    for nom in ('set_mode', 'restore_mode'):
        if hasattr(ecran, nom): envelopper(ecran, nom, (lambda n: (lambda self, *a, **k: evt(n)))(nom))
except Exception as ex: print('mesure_bascule : ecran illisible (%r)' % (ex,), flush=True)

print('mesure_bascule : %s' % ARBRE, flush=True)
FE.main()
print('mesure_bascule : %d bascule(s) mesuree(s)' % len(ETAT['fait']), flush=True)
