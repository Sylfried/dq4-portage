import sys, pickle, collections, unicodedata, json
sys.path.insert(0,'/home/claude/dq4-portage')
from dq4_pc.menus.message_font import MessageFont
import numpy as np
E=MessageFont('apk/English.font')
S={int(g[0]):g for g in json.load(open('/tmp/audit_final/interface/uicache/ui_garrir.json'))['glyphes']}
dec=pickle.load(open('dec.pkl','rb'))
cnt=collections.Counter(); files=collections.defaultdict(set)
for base,eid,s in dec:
    # texte affichable : on retire le balisage @a..@b, @cN@ (approximation, '@' non compte)
    for ch in s:
        cnt[ch]+=1; files[ch].add(base)
def eng(c):
    if ord(c) not in E: return None
    fl,w,bm=E.glyph(ord(c))
    cols=np.where(bm.any(0))[0]
    if len(cols)==0: return dict(adv=(w-2 if fl else w), w=w, lb=None, rb=None, flag=fl)
    return dict(adv=(w-2 if fl else w), w=w, lb=int(cols[0]), rb=int(w-1-cols[-1]), flag=fl)
def gar(c):
    g=S.get(ord(c))
    if not g: return None
    return dict(adv=g[5], vx=g[1], vw=g[3], ink_rb=g[5]-(g[1]+g[3]))
rows=[]
for ch,n in sorted(cnt.items(), key=lambda kv: ord(kv[0])):
    if ch.isascii() and ch.isalnum(): continue
    rows.append((ch,n,len(files[ch]),eng(ch),gar(ch)))
for ch,n,nf,e,g in rows:
    print('U+%04X %-3r %-42s n=%-6d files=%-3d ENG=%s GAR=%s' % (ord(ch), ch, unicodedata.name(ch,'?')[:42], n, nf, e, g))
