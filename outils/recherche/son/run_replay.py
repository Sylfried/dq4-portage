"""usage: run_replay.py SCENARIO [facteur] ; SCENARIO : niveau | wipe"""
import sys, time as _time
sys.path.insert(0, '/tmp/claude-0/-home-claude/17145693-c62f-5af6-a741-2d4f94a36edf/scratchpad/son45_work')
from replay import *
from h45 import *
sc = sys.argv[1]; fac = float(sys.argv[2]) if len(sys.argv) > 2 else 1.0
mo = nouveau('rp_' + sc); c = mo.core; tr = Trace(mo)
mo.charger_sauvegarde(1)
for _ in range(200): mo.step(0, 0)
orig = c.export('_ZN6status9PartyData15originalPlayer_E')
if sc == 'niveau':
    hs = orig + PAS_JOUEUR * 3 + OFF_HS
    need = struct.unpack_from('<I', c.mem(hs, 0x30), 0x18)[0]; c.mem_w(hs + 8, struct.pack('<I', need - 1))
    monstres, hp = [(3, 1)], None
else:
    monstres, hp = [(3, 4), (4, 4), (5, 4)], [1, 1, 1, 1, 1]
rj = Rejeu(mo.apk_donnees)
rj.s.jouer_bgm(14)                                         # la musique du village tourne avant le combat
rj.attendre_decodage(); rj.s.tick(); H.t += 1.0
if RT:
    if hasattr(rj.s, 'precharger_musiques') and not os.environ.get('SANS_PRECHARGE'): rj.s.precharger_musiques()
    for _ in range(int(float(os.environ.get('MARCHE', '12')) * 30)): rj.image([]) if False else (rj.s.tick(), _time.sleep(1 / 30))      # le joueur marche un moment avant la rencontre
    rj.talk('  (avant le combat : %d musiques en memoire, %d travaux)' % (len(rj.s.dec), len(rj.s.jobs)))
    H.t0 = _time.time()
cb = Combat(mo, tr, monstres=monstres, hp=hp)
# on branche le rejeu sur chaque image du moteur : seul le temps change (facteur de vitesse : t avance de 1/(30 x facteur) par image moteur)
orig_step = mo.step
def step(*a, **k):
    pq = orig_step(*a, **k)
    rj.image(pq_sons(pq), dt=1.0 / (30.0 * fac), e=mo.images)
    return pq
mo.step = step
fin = cb.lancer(max_pas=3000, apres_combat=300)
print('fin combat image', fin)
if RT:                                                    # le jeu continue : on laisse tourner l'horloge (le moteur ne donne plus d'ordres) pour voir partir les ordres retenus
    for _ in range(int(float(os.environ.get('SUITE', '8')) * 30)): rj.s.tick(); _time.sleep(1 / 30)
    print('  (fin de la suite : %d ordres encore retenus)' % len(getattr(rj.s, 'attente_bgm', ())))
