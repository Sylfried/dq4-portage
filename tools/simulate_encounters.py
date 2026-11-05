"""Simulation statistique des rencontres aleatoires a marche acceleree (#45), sur le VRAI moteur (libdq4core.so emule) : combien de rencontres par pas a x1, x2, x4 ?

Un robot fait marcher le heros (direction tenue, il change de direction quand il est bloque) pendant un nombre fixe de PAS (images du moteur ou la position du heros change : ce que compte le jeu, voir
encounters.py) avec `Engine.walking_speed` = a, le reglage qu'ecrit la visionneuse avant chaque pas. Les declenchements sont comptes ([Encount+0x1c] >= 1) ; `Encount::brew` renvoie faux (pas de combat : le robot
reste sur la carte) et le compteur est retire comme au retour d'un combat (`Encount::setup(0, 0)`, appelee par FieldSystem::initialize et TownSystem::initialize quand la carte se recharge). Rien d'autre n'est touche : le
tirage du compteur, la perte par appel et la formation des groupes sont ceux du jeu.

Ce qu'on attend : rencontres par pas (a) / rencontres par pas (x1) = (1 + a) / (2 a), donc « rencontres par pas x a » = (1 + a) / 2 x le taux de x1 (x2 : 1,5 ; x4 : 2,5). Le tableau donne aussi la perte
du compteur par appel de `CountDown::exec` avant et apres le crochet (exacte, sans hasard : rapport = (1 + a) / (2 a)).

    DQ_APK=... DQ_SAVES=... python3 tools/simulate_encounters.py [--lieu monde|donjon] [--pas 24000] [--vitesses 1,2,4] [--graine 1]
      monde  : carte du monde, sauvegarde 4 (le heros va et vient dans un couloir sans entree ni sortie) ; donjon : sauvegarde 5 (salle dab1).
Les sauvegardes sont lues sans etre modifiees (ecriture dans /tmp/sv_simrenc_*).
"""
import os, sys, struct, shutil, random, argparse, math

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from dq4_pc.core import engine as ENGINE
from dq4_pc.core import encounters as RE
import unicorn

LOCATIONS = {'monde': dict(sauvegarde=4, zone=(2300, 2480, 342, 362), va_et_vient=True),          # carte du monde : couloir sans entree (la ville est au sud et au nord de la case de depart)
         'donjon': dict(sauvegarde=5, zone=None, va_et_vient=False)}                           # donjon dab1 : une salle fermee
DIRS = (ENGINE.UP, ENGINE.RIGHT, ENGINE.DOWN, ENGINE.LEFT)


def simulate(apk, saves, location, speed, step, seed=1):
    cfg = LOCATIONS[location]; rnd = random.Random(seed)
    wdir = '/tmp/sv_simrenc_%s_%s_%s' % (location, speed, seed); shutil.rmtree(wdir, ignore_errors=True); os.makedirs(wdir)
    m = ENGINE.Engine(apk, saves, wdir); c = m.core
    m.load_save(cfg['sauvegarde'])
    for i in range(700):
        m.step(0, 0)
        if i >= 130 and 0 in m.state.sprites: break
    enc = c.call(c.export('_ZN7Encount12getSingletonEv')); setup = c.export('_ZN7Encount5setupE11EncountPart8LandType')
    c.mem_w(c.export('_ZN7Encount4brewEv'), struct.pack('<II', 0x52800000, 0xd65f03c0))        # brew : mov w0, #0 ; ret -> pas de combat (la simulation compte les declenchements)
    st = dict(rencontres=0, pas=0, images=0, appels=0, perte_jeu=0, perte_appliquee=0)
    cd = c.export('_ZN9CountDown4execEv')

    def before(uc, ad, sz, u):
        st['appels'] += 1; st['perte_jeu'] += 2 * struct.unpack('<i', c.mem(enc + 0x144, 4))[0]
    def after(uc, ad, sz, u):                                                                  # ajoute apres le crochet du moteur (meme adresse : ordre d'installation)
        w9 = uc.reg_read(c.XREG[9]) & 0xffffffff; w8 = uc.reg_read(c.XREG[8]) & 0xffffffff
        st['perte_appliquee'] += (w9 - ((w9 & 0x80000000) << 1)) - (w8 - ((w8 & 0x80000000) << 1))
    c.uc.hook_add(unicorn.UC_HOOK_CODE, before, None, cd, cd); c.uc.hook_add(unicorn.UC_HOOK_CODE, after, None, cd + ENGINE.COUNTDOWN_EXEC_WRITE, cd + ENGINE.COUNTDOWN_EXEC_WRITE)
    try: c.uc.ctl_flush_tb()
    except Exception: pass
    m.walking_speed = float(speed)
    d = rnd.randrange(4); held = 0; without = 0; prev = tuple(m.state.sprites[0]['pos']); zone = cfg['zone']
    while st['pas'] < step and st['images'] < step * 8:
        m.step(DIRS[d], DIRS[d]); st['images'] += 1; held += 1
        if 0 not in m.state.sprites: raise RuntimeError('le heros a quitte la carte (image %d)' % st['images'])
        pos = tuple(m.state.sprites[0]['pos'])
        if pos != prev: st['pas'] += 1; without = 0
        else:
            without += 1
            if without >= 3: d = rnd.randrange(4); without = 0; held = 0
        if cfg['va_et_vient'] and held >= rnd.randrange(20, 80): d = rnd.randrange(4); held = 0
        prev = pos
        if zone and not (zone[0] < pos[0] < zone[1] and zone[2] < pos[1] < zone[3]):          # hors du couloir : retour vers le centre (UP diminue y, DOWN l'augmente)
            cx, cy = (zone[0] + zone[1]) / 2, (zone[2] + zone[3]) / 2
            d = (1 if pos[0] < cx else 3) if abs(pos[0] - cx) / (zone[1] - zone[0]) > abs(pos[1] - cy) / (zone[3] - zone[2]) else (2 if pos[1] < cy else 0)
        if struct.unpack('<i', c.mem(enc + 0x1c, 4))[0] >= 1:
            st['rencontres'] += 1; c.call(setup, enc, 0, 0)
    return st


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--apk', default=os.environ.get('DQ_APK')); ap.add_argument('--saves', default=os.environ.get('DQ_SAVES'))
    ap.add_argument('--lieu', dest='location', choices=sorted(LOCATIONS), default='monde'); ap.add_argument('--pas', dest='step', type=int, default=24000)
    ap.add_argument('--vitesses', default='1,2,4'); ap.add_argument('--graine', dest='seed', type=int, default=1)
    a = ap.parse_args()
    if not a.apk or not a.saves: sys.exit('DQ_APK et DQ_SAVES (ou --apk / --saves) requis')
    res = []
    for v in [float(x) for x in a.vitesses.split(',')]:
        r = simulate(a.apk, a.saves, a.location, v, a.step, a.seed); r['v'] = v; res.append(r)
        print('x%g : %d rencontres en %d pas (%d images)' % (v, r['rencontres'], r['pas'], r['images']), flush=True)
    base = res[0]; p1 = base['rencontres'] / base['pas']
    print('\n%s, graine %d, %d pas par vitesse. Reference : %s' % (a.location, a.seed, a.step, 'x%g' % base['v']))
    print('%6s %12s %12s %14s %12s %14s %12s' % ('vitesse', 'rencontres', 'par pas', 'par pas x a', 'attendu', 'perte/appel', 'attendu'))
    for r in res:
        v = r['v']; pp = r['rencontres'] / r['pas']
        print('%6s %12d %12.5f %14.2f %12.2f %14.3f %12.3f' % ('x%g' % v, r['rencontres'], pp, pp * v / p1 if p1 else float('nan'), (RE.encounters_per_second(v) / RE.encounters_per_second(base['v'])),
              r['perte_appliquee'] / r['perte_jeu'], RE.factor_per_step(v) / RE.factor_per_step(base['v'])))
        err = 1.0 / math.sqrt(max(1, r['rencontres']))
        print('       (incertitude statistique : +/- %.0f %%)' % (100 * err))


if __name__ == '__main__': main()
