"""Probe 4 (temoin) : en VILLE, le meme montage : le moteur emet-il les paquets 19 / 20 (emplacement 15, icone 188) quand le heros fait face a quelqu'un ?
Marche aleatoire (graine fixe) sur la carte de la sauvegarde ; crochets sur TownPlayerEtc::setTalkIcon / setSearchIcon ; journal des paquets 19 / 20."""
import os, sys, struct, tempfile, shutil, random
sys.path.insert(0, '/home/claude/dq4-portage')
import unicorn
from dq4_pc.core import engine as ENGINE
folder = tempfile.mkdtemp(prefix='signs_p4_')
m = ENGINE.Engine(os.environ['DQ_APK'], os.environ['DQ_SAVES'], folder)
c = m.core
ev = []
for name, tag in (('_ZN13TownPlayerEtc11setTalkIconEi', 'setTalkIcon'), ('_ZN13TownPlayerEtc13setSearchIconEiii', 'setSearchIcon')):
    ad = c.export(name)
    c.uc.hook_add(unicorn.UC_HOOK_CODE, (lambda t: lambda uc, a, sz, u: ev.append((m.frames, t, uc.reg_read(c.XREG[1]) & 0xffffffff, uc.reg_read(c.XREG[2]) & 0xffffffff)))(tag), None, ad, ad)
for _ in range(3): m.step(0, 0)
m.load_save(int(os.environ.get('SLOT', '1')))
for i in range(900):                           # ferme le message d'arrivee
    if m.msg_visible and i % 12 < 3: m.step(ENGINE.A, ENGINE.A)
    else: m.step(0, 0)
    if i > 150 and not m.msg_visible and not m.flags() & ENGINE.PLAYER_LOCKED_FLAG: break
print('map', m.state.game_map, 'part', hex(m.state.part), 'hero', m.state.sprites.get(0, {}).get('pos'))
rnd = random.Random(int(os.environ.get('SEED', '5')))
pk19 = []
dirs = [ENGINE.UP, ENGINE.DOWN, ENGINE.LEFT, ENGINE.RIGHT]
held = 0
for i in range(int(os.environ.get('N', '2500'))):
    if i % 25 == 0: held = rnd.choice(dirs) if rnd.random() < 0.85 else 0
    pk = m.step(held, 0)
    for t, a, f in pk:
        if t == 19 or (t == 20 and i % 15 == 0): pk19.append((m.frames, t, a[:3], [round(x, 2) for x in f[:4]]))
    if ev and len(ev) > 6 and len(pk19) > 4: break
print('hooks TownPlayerEtc :', ev[:8])
for p in pk19[:14]: print('paquet', p)
print('map finale', m.state.game_map, 'hero', m.state.sprites.get(0, {}).get('pos'))
shutil.rmtree(folder, ignore_errors=True)
