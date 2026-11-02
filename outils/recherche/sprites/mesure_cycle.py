"""(test #45) Duree reelle d'un cycle jour / nuit de la carte du monde : un robot marche sur la carte (direction tenue, change de direction quand le temps du monde ne bouge plus),
les rencontres sont coupees (Encount +0x18 = 0), on journalise (heure reelle, temps du monde g_Stage+0xcc, images du moteur). Usage : mesure_cycle.py ETIQUETTE DUREE_MAX_S [CYCLES]"""
import sys, os, time, json, struct, atexit
WT = '/home/claude/wt45-sprites'
sys.path.insert(0, WT + '/dq4_pc'); os.chdir(WT + '/dq4_pc')
import fenetre as F, moteur as MO, pyglet
tag, dmax, cycles = sys.argv[1], float(sys.argv[2]), float(sys.argv[3]); sys.argv = [sys.argv[0]] + sys.argv[4:]
log = []; etat = {'dir': 0, 'sans': 0, 'fin': False, 'depart': None}
DIRS = (MO.HAUT, MO.DROITE, MO.BAS, MO.GAUCHE)
orig_pad, orig_pas = F.Jeu.pad, F.Jeu._pas
def pad(self):
    p = orig_pad(self)
    if self.moteur.etat.partie == MO.PARTIE_CHAMP and self.n > 60 and not etat['fin']: p |= DIRS[etat['dir']]
    return p
def pas(self, muet=False):
    r = orig_pas(self, muet)
    mo = self.moteur; c = mo.core
    if self.n < 60: return r
    if etat.get('dbg_t') is None or time.perf_counter() - etat['dbg_t'] > 5: etat['dbg_t'] = time.perf_counter(); print('DIAG n=%d partie=%#x carte=%s msg=%s pos=%s' % (self.n, mo.etat.partie, mo.etat.carte, mo.msg_visible, None if 0 not in mo.etat.sprites else mo.etat.sprites[0].get('pos')), flush=True)
    if mo.etat.partie != MO.PARTIE_CHAMP: return r
    G = c.export('_ZN6status7g_StageE'); t = struct.unpack('<i', c.mem(G + 0xcc, 4))[0]
    enc = c.call(c.export('_ZN7Encount12getSingletonEv')); c.mem_w(enc + 0x18, b'\x00')
    now = time.perf_counter()
    if log and t == log[-1][1]:
        etat['sans'] += 1
        if etat['sans'] >= 4: etat['dir'] = (etat['dir'] + 1) % 4; etat['sans'] = 0
    else: etat['sans'] = 0
    log.append((now, t, self.n))
    BOX = (2300, 2480, 342, 362)
    if 0 in mo.etat.sprites:
        x, y = float(mo.etat.sprites[0]['pos'][0]), float(mo.etat.sprites[0]['pos'][1])
        if not (BOX[0] < x < BOX[1] and BOX[2] < y < BOX[3]):          # couloir sans entree (voir outils/simuler_rencontres.py) : la ville est au sud et au nord de la case de depart
            cx, cy = (BOX[0] + BOX[1]) / 2, (BOX[2] + BOX[3]) / 2
            etat['dir'] = (1 if x < cx else 3) if abs(x - cx) / (BOX[1] - BOX[0]) > abs(y - cy) / (BOX[3] - BOX[2]) else (2 if y < cy else 0)
    if etat['depart'] is None: etat['depart'] = (now, t)
    cum = 0; prev = None
    for _, tt, _ in log[-2:]: pass
    tot = sum(((b[1] - a[1]) % 3392) for a, b in zip(log, log[1:]))                  # temps du monde gagne (modulo le cycle)
    if (tot >= 3392 * cycles or now - etat['depart'][0] > dmax) and not etat['fin']:
        etat['fin'] = True; self.on_close(); pyglet.app.exit()
    return r
F.Jeu.pad, F.Jeu._pas = pad, pas
def ecrire():
    tot = 0; deb = log[0] if log else None
    gagne = [0]
    for a, b in zip(log, log[1:]): gagne.append(gagne[-1] + ((b[1] - a[1]) % 3392))
    json.dump({'log': log, 'gagne': gagne}, open('/tmp/sp45/cycle_%s.json' % tag, 'w'))
atexit.register(ecrire)
F.main()
