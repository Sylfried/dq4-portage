"""Probe 5 : valide la lecture de FieldSystem::draw / g_field_pad_blink. On leve le bit 0 de l'octet a chaque appel de FieldPlayer::fldSearch
(ce que fait le jeu quand le heros est a cote du ballon) puis on le cesse : on attend (19, [16, 188]) puis (19, [16, -1]) sur la carte du monde."""
import os, sys, tempfile, shutil
sys.path.insert(0, '/home/claude/dq4-portage')
import unicorn
from dq4_pc.core import engine as ENGINE
folder = tempfile.mkdtemp(prefix='signs_p5_')
m = ENGINE.Engine(os.environ['DQ_APK'], os.environ['DQ_SAVES'], folder)
c = m.core; PAD = c.LIB_BASE + 0x275156
force = [False]
def arm(uc, a, sz, u):
    if force[0]: c.mem_w(PAD, bytes([c.mem(PAD, 1)[0] | 1]))
ad = c.export('_ZN11FieldPlayer9fldSearchEv'); c.uc.hook_add(unicorn.UC_HOOK_CODE, arm, None, ad, ad)
for _ in range(3): m.step(0, 0)
m.load_save(4)
for i in range(100): m.step(0, 0x10 if i % 10 == 0 else 0)
print('part', hex(m.state.part))
def run(n, label):
    for _ in range(n):
        pk = m.step(0, 0)
        ic = [(t, a[:2]) for t, a, f in pk if t in (19, 20)]
        if ic or m.frames % 10 == 0: print(label, 'image', m.frames, 'paquets 19/20', ic, 'pad_blink viewer', m.state.pad_blink, 'icons', dict(m.state.icons))
run(5, 'sans')
force[0] = True; run(5, 'pres du ballon (simule)')
force[0] = False; run(5, 'apres')
shutil.rmtree(folder, ignore_errors=True)
