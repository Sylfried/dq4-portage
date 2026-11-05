"""Mesures homogenes sur la capture du mobile et les rendus t33 : python3 analysis.py img1 [img2 ...]
Pour chaque image : trait du corps, onglet « Ragnar » (ligne de base et marge sous la base jusqu'au trait), bouton de gauche (bords, centre), « Rat volant » (ligne de base), bouton de droite : lignes de base de « Scarapince » et « x2 » ;
tout en px et en unites (1,688 px / unite), relatif au centre du bouton."""
import sys
import numpy as np
from PIL import Image
SCALE = 1.688
def do_load(p): return np.asarray(Image.open(p).convert('RGB')).astype(int).sum(2) / 3
def dense_base(L, x0, x1, y0, y1, th=170):
    sub = (L[y0:y1, x0:x1] > th).sum(1); m = sub.max()
    ys = [y0 + i for i, c in enumerate(sub) if c >= 0.45 * m]; return ys[-1] + 1
def ink_lines(L, x0, x1, y0, y1, th=170):
    sub = (L[y0:y1, x0:x1] > th).sum(1); ys = [y0 + i for i, c in enumerate(sub) if c > 0]; return (min(ys), max(ys) + 1) if ys else None
def measure(p):
    L = do_load(p); r = {}
    body = [y for y in range(60, 140) if (L[y, 40:700] > 200).sum() >= 400]; r["trait_corps"] = body[0]
    # onglet : texte entre le haut de l'onglet et le trait
    tab_baseline = dense_base(L, 55, 150, body[0] - 40, body[0] - 3); r['base_onglet'] = tab_baseline; r['marge_onglet'] = body[0] - tab_baseline
    r['encre_onglet'] = ink_lines(L, 55, 150, body[0] - 40, body[0] - 3)
    col = L[:, 250]; top = next(y for y in range(body[0] + 8, 300) if col[y] >= 100); bottom = top + 82
    r['bouton'] = (top, bottom); c = (top + bottom) / 2; r['centre'] = c
    r['base_rat'] = dense_base(L, 95, 300, top + 10, bottom - 2); r['encre_rat'] = ink_lines(L, 95, 300, top + 6, bottom + 3)
    e = ink_lines(L, 440, 700, top + 6, bottom + 3); r['encre_scar'] = e
    # lignes de base de la 2e colonne : rangees denses
    sub = (L[top + 6:bottom + 3, 440:700] > 170).sum(1); ys = [top + 6 + i for i, v in enumerate(sub) if v >= 20]
    grp = []; 
    for y in ys:
        if grp and y - grp[-1][-1] <= 2: grp[-1].append(y)
        else: grp.append([y])
    r['groupes_denses'] = [(g[0], g[-1] + 1) for g in grp]
    return r, c
for p in sys.argv[1:]:
    r, c = measure(p); print(p)
    for k, v in r.items(): print('  ', k, v)
    print('   base_rat sous le centre : %.1f px = %.2f u' % (r['base_rat'] - c, (r['base_rat'] - c) / SCALE))
    print('   base_onglet au-dessus du trait : %d px' % r['marge_onglet'])
    gd = r['groupes_denses']; print('   bases scar/x2 sous le centre (u) :', [round((g[1] - c) / SCALE, 2) for g in gd])
