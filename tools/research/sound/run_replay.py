"""usage: run_replay.py SCENARIO [facteur] ; SCENARIO : niveau | wipe"""
import sys, time as _time
sys.path.insert(0, '/tmp/claude-0/-home-claude/17145693-c62f-5af6-a741-2d4f94a36edf/scratchpad/son45_work')
from replay import *
from h45 import *
sc = sys.argv[1]; fac = float(sys.argv[2]) if len(sys.argv) > 2 else 1.0
eng = new('rp_' + sc); c = eng.core; tr = Trace(eng)
eng.load_save(1)
for _ in range(200): eng.step(0, 0)
orig = c.export('_ZN6status9PartyData15originalPlayer_E')
if sc == 'niveau':
    hs = orig + PLAYER_STRIDE * 3 + OFF_HS
    need = struct.unpack_from('<I', c.mem(hs, 0x30), 0x18)[0]; c.mem_w(hs + 8, struct.pack('<I', need - 1))
    monsters, hp = [(3, 1)], None
else:
    monsters, hp = [(3, 4), (4, 4), (5, 4)], [1, 1, 1, 1, 1]
rj = Replay(eng.apk_data)
rj.s.play_bgm(14)                                         # la musique du village tourne avant le combat
rj.wait_decoding(); rj.s.tick(); H.t += 1.0
if RT:
    if hasattr(rj.s, 'preload_music') and not os.environ.get('SANS_PRECHARGE'): rj.s.preload_music()
    for _ in range(int(float(os.environ.get('MARCHE', '12')) * 30)): rj.image([]) if False else (rj.s.tick(), _time.sleep(1 / 30))      # le joueur marche un moment avant la rencontre
    rj.talk('  (before the battle: %d music tracks in memory, %d jobs)' % (len(rj.s.dec), len(rj.s.jobs)))
    H.t0 = _time.time()
cb = Battle(eng, tr, monsters=monsters, hp=hp)
# on branche le rejeu sur chaque image du moteur : seul le temps change (facteur de vitesse : t avance de 1/(30 x facteur) par image moteur)
orig_step = eng.step
def step(*a, **k):
    pkt = orig_step(*a, **k)
    rj.image(pkt_sounds(pkt), dt=1.0 / (30.0 * fac), e=eng.frames)
    return pkt
eng.step = step
end = cb.launch(max_step=3000, after_battle=300)
print('battle end frame', end)
if RT:                                                    # le jeu continue : on laisse tourner l'horloge (le moteur ne donne plus d'ordres) pour voir partir les ordres retenus
    for _ in range(int(float(os.environ.get('SUITE', '8')) * 30)): rj.s.tick(); _time.sleep(1 / 30)
    print('  (end of the sequence: %d orders still held)' % len(getattr(rj.s, 'bgm_queue', ())))
