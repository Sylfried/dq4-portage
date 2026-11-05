"""Rend des lignes par le vrai SDrawCTRL::PutChar du moteur (Unicorn) et les compare a MessageFont.pixels ; sauvegarde les canevas en .npy."""
import os, sys, struct, tempfile
sys.path.insert(0, '/home/claude/dq4-portage')
import numpy as np
from dq4_pc.core import engine as ENGINE
from dq4_pc.menus.message_font import MessageFont, extract_message_font
APK = os.environ['DQ_APK']; SAVES = os.environ['DQ_SAVES']; OUT = sys.argv[1]
tmp = tempfile.mkdtemp(dir=OUT)
assert extract_message_font(APK, tmp, print)
mp = MessageFont(os.path.join(tmp, 'ui_messages.font'))
eng = ENGINE.Engine(APK, SAVES, tempfile.mkdtemp(dir=tmp)); eng.load_save(1)
for i in range(80):
    eng.step(0, 0x10 if i % 9 == 5 else 0)
    cv = eng.read_canvas()
    if i > 30 and cv is not None and cv.max() > 100: break
c = eng.core; obj = eng.obj_msg
print('espace/large/tab du moteur', struct.unpack('<3H', c.mem(obj + 0x38, 6)))
c.mem_w(obj + 0x38, struct.pack('<3H', 6, 6, 15))
put = c.export('_ZN9SDrawCTRL7PutCharEt')
def render(text, x=6, y=0):
    buffer = struct.unpack('<Q', c.mem(obj + 0x10, 8))[0]
    c.mem_w(buffer, bytes(512 * 512))
    c.mem_w(obj + 0x46, struct.pack('<H', x)); c.mem_w(obj + 0x48, struct.pack('<H', y))
    for ch in text: c.call(put, obj, ord(ch), label='putchar')
    cv = eng.read_canvas(); end = struct.unpack('<H', c.mem(obj + 0x46, 2))[0]
    return cv[y:y + 24].copy(), end - x
tests = ['*: Ouaf-ouaf.', '*: Ouaf-ouaf\xa0! Gяяя...\xa0!', '*: Ouaf‑ouaf.', '*: Ouaf‐ouaf.', '*: Ouaf–ouaf.', '*: Ouaf­ouaf.', '*: Ouaf ouaf.', '*: Ouaf -ouaf.', 'Va-t-en, petit-fils !', 'Ouaf—ouaf']
res = {}
for t in tests:
    vu, adv = render(t)
    x = 6; a = mp.pixels(t); exp = np.zeros_like(vu); w = min(a.shape[1], vu.shape[1] - (x - mp.PAD)); exp[:, x - mp.PAD:x - mp.PAD + w] = a[:, :w]
    same = bool((vu == exp).all()) and adv == mp.width_px(t)
    print(repr(t), 'avance moteur', adv, 'police python', mp.width_px(t), 'pixels identiques:', same, 'diff', int((vu != exp).sum()))
    res[t] = vu
np.savez(os.path.join(OUT, 'real_canvas.npz'), **{str(i): v for i, v in enumerate(res.values())})
open(os.path.join(OUT, 'real_canvas_keys.txt'), 'w').write('\n'.join(repr(k) for k in res))
