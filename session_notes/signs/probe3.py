"""Probe 3 : carte du monde (chapitre 1, sauvegarde 4), heros qui marche vers le panneau (kanban 2, x 2552, y 380) puis face a lui, A.
Journalise a chaque image : position, resultat de FieldData::searchKanban (crochet), octet g_field_pad_blink, paquets 19 / 20 (tous), message affiche."""
import os, sys, struct, tempfile, shutil
sys.path.insert(0, '/home/claude/dq4-portage')
import unicorn
from dq4_pc.core import engine as ENGINE
folder = tempfile.mkdtemp(prefix='signs_p3_')
m = ENGINE.Engine(os.environ['DQ_APK'], os.environ['DQ_SAVES'], folder)
c = m.core; L = c.LIB_BASE
PAD = L + 0x275156                                  # g_field_pad_blink (octet)
kan = []
def at_kanban(uc, a, sz, u):
    kan.append(('call', uc.reg_read(c.XREG[1]) & 0xffffffff, uc.reg_read(c.XREG[2]) & 0xffffffff))
ad = c.export('_ZN9FieldData12searchKanbanEiiPN3dss7Vector2INS0_5Fix32EEE'); print('searchKanban', hex(ad) if ad else None)
if ad: c.uc.hook_add(unicorn.UC_HOOK_CODE, at_kanban, None, ad, ad)
sym = []
ad2 = c.export('_ZN18FieldSymbolManager11checkSymbolEi'); print('checkSymbol', hex(ad2))
c.uc.hook_add(unicorn.UC_HOOK_CODE, lambda uc, a, sz, u: sym.append(uc.reg_read(c.XREG[1]) & 0xffffffff), None, ad2, ad2)
for _ in range(3): m.step(0, 0)
m.load_save(4)
for i in range(100): m.step(0, 0x10 if i % 10 == 0 else 0)
print('part', hex(m.state.part))
log = []
def run(label, n, held, decl=None):
    global kan
    for i in range(n):
        kan = []
        pk = m.step(held, decl if decl is not None else held if label == 'A' else 0)
        icon = [(t, a[:2], [round(x, 1) for x in f[:4]]) for t, a, f in pk if t in (19, 20)]
        p = m.state.sprites.get(0, {}).get('pos')
        res = kan[-1] if kan else None
        log.append((label, m.frames, tuple(round(x, 2) for x in p[:2]) if p else None, 'pad', c.mem(PAD, 1)[0], 'msg', m.msg_visible, 'icons', icon, 'kan', [(round(k[1] / 4096.0, 1), round(k[2] / 4096.0, 1), tile_match(k)) for k in kan][:1], 'checkSymbol', list(sym)))
        yield
TILES = [(776, 988), (2680, 764), (2552, 380), (1722, 1576), (904, 3256)]
def tile_match(k):
    fx, fy = k[1] / 4096.0, k[2] / 4096.0
    return [i for i, (kx, ky) in enumerate(TILES) if int(fx) >> 4 == kx >> 4 and int(fy) >> 4 == ky >> 4]
def pos(): return m.state.sprites[0]['pos']
for _ in run('settle', 10, 0): pass
for _ in run('right1', 40, ENGINE.RIGHT):
    if pos()[0] >= 2530: break
for _ in run('down', 20, ENGINE.DOWN):
    if pos()[1] >= 394: break
for _ in run('right2', 30, ENGINE.RIGHT):
    if pos()[0] >= 2549: break
for _ in run('up', 30, ENGINE.UP):
    if sym: break
for _ in run('stop', 20, 0): pass
n_before = len(sym)
for _ in run('A', 1, 0, 0x100): pass
for _ in run('wait', 90, 0): pass
for l in log:
    if l[0] not in ('settle', 'right1', 'down', 'right2') or l is log[-1]: print(*l)
# bilan : paquets 19/20 vus dans toute la session
alls = [x for l in log for x in l[8]]
print('PAQUETS 19/20 vus sur la carte du monde :', alls)
print('octet g_field_pad_blink observe :', sorted(set(l[4] for l in log)))
shutil.rmtree(folder, ignore_errors=True)
