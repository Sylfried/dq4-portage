import sys, pickle, re, collections
sys.path.insert(0,'/home/claude/dq4-portage')
from dq4_pc.menus.message_font import MessageFont
import numpy as np
E=MessageFont('apk/English.font')
dec=pickle.load(open('dec.pkl','rb'))
hy=E.glyph(ord('-'))[2]
rows=np.where(hy.any(1))[0]; print('rangees du tiret', rows.tolist(), 'colonnes', np.where(hy.any(0))[0].tolist())
r0,r1=rows.min(),rows.max()
def ink_right(c):   # colonne d'encre la plus a droite (indice dans la cellule) aux rangees du tiret, -1 si aucune
    fl,w,bm=E.glyph(ord(c)); band=bm[r0:r1+1]; cols=np.where(band.any(0))[0]
    return (w-1-cols[-1]) if len(cols) else w     # marge droite (colonnes vides apres l'encre, a la hauteur du tiret)
def ink_left(c):
    fl,w,bm=E.glyph(ord(c)); band=bm[r0:r1+1]; cols=np.where(band.any(0))[0]
    return cols[0] if len(cols) else w
hy_l=np.where(hy.any(0))[0][0]; hy_r=8-1-np.where(hy.any(0))[0][-1]
pat=re.compile(r"([A-Za-zÀ-ÿœŒ])-([A-Za-zÀ-ÿœŒ])")
before=[];after=[]; pairs=collections.Counter()
for base,eid,s in dec:
    for m in pat.finditer(s):
        a,b=m.group(1),m.group(2)
        g_before=ink_right(a)+hy_l     # colonnes vides entre l'encre de a (a la hauteur du tiret) et le tiret
        g_after=hy_r+ink_left(b)
        before.append(g_before); after.append(g_after); pairs[(a,b)]+=1
before=np.array(before); after=np.array(after)
print('occurrences lettre-tiret-lettre', len(before))
print('colonnes vides avant le tiret : moyenne %.2f, min %d, max %d ; apres : moyenne %.2f, min %d, max %d' % (before.mean(),before.min(),before.max(),after.mean(),after.min(),after.max()))
print('avant > apres dans %.1f %% des cas ; egal %.1f %%' % (100*(before>after).mean(), 100*(before==after).mean()))
print('repartition avant', collections.Counter(before.tolist()).most_common(), 'apres', collections.Counter(after.tolist()).most_common())
print('f-o :', ink_right('f')+hy_l, hy_r+ink_left('o'))
# comparaison : espace entre 2 lettres ordinaires adjacentes (hauteur du tiret), pour reference
import itertools
txt=collections.Counter()
for base,eid,s in dec:
    for m in re.finditer(r"[a-z][a-z]", s): txt[m.group(0)]+=1
tot=sum(txt.values()); mean=sum(n*(ink_right(k[0])+ink_left(k[1])) for k,n in txt.items())/tot
print('espace moyen entre deux lettres minuscules adjacentes (hauteur du tiret) : %.2f colonnes' % mean)
print('ex.:', [(k,v) for k,v in pairs.most_common(8)])
