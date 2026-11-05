import sys, os
os.environ.setdefault('PYGLET_HEADLESS','1')
sys.path.insert(0,'/home/claude/dq4-portage')
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import pyglet
pyglet.options['shadow_window']=False
from dq4_pc.menus import ui_menu as UM
from dq4_pc.menus.message_font import MessageFont
E=MessageFont('apk/English.font')
G=UM.BitmapFont('/tmp/audit_final/interface/uicache/ui_garrir.json','/tmp/audit_final/interface/uicache/ui_garrir.png')
SCALE=1.52     # pixels d'ecran par pixel du canevas, mesure sur la capture (180 px pour 118 px de canevas)
BG=(10,18,22)
def composite(a, scale, up):
    """a : alpha (h x w) ; blanc sur fond sombre, filtre bilineaire a `scale`, puis agrandissement `up` au plus proche (pour la lisibilite)."""
    im=Image.fromarray(a).resize((max(1,round(a.shape[1]*scale)),max(1,round(a.shape[0]*scale))), Image.BILINEAR)
    al=np.asarray(im).astype(float)/255
    rgb=np.zeros(al.shape+(3,)); rgb[:]=BG; rgb=rgb*(1-al[...,None])+255*al[...,None]
    out=Image.fromarray(rgb.astype(np.uint8))
    return out.resize((out.width*up,out.height*up),Image.NEAREST)
def garrir_alpha(text):
    # meme composition que BitmapFont.line (sans GL)
    W=int(G.width_px(text))+2*G.PAD; H=G.UP+G.DOWN; a=np.zeros((H,W),np.uint8); x=G.PAD
    for c in text:
        g=G._glyph(c) or G.G[32]; adv,vx,top,b=g
        if b.size:
            y0=G.UP+top; x0=x+vx; h,w=b.shape
            sub=a[max(y0,0):y0+h,max(x0,0):x0+w]; bb=b[max(-y0,0):max(-y0,0)+sub.shape[0],max(-x0,0):max(-x0,0)+sub.shape[1]]
            sub[...]=np.maximum(sub,bb)
        x+=adv
    return a
shot=Image.open('/mnt/user-data/attachments/45fdf246-f4ad-5078-9633-8be9ccf9e9c9/d591f83e-image.png').convert('RGB')
UP=3
rows=[]   # (legende, image)
rows.append(('1. Capture de Sylfried (x3)', shot.crop((0,20,249,75)).resize((249*UP,55*UP),Image.LANCZOS)))
def eng_line(t):
    a=E.pixels(t)           # identique au canevas du vrai moteur (verifie : 0 pixel de difference)
    return a
for lab,t in [('2. Dialogue, vrai moteur : « *: Ouaf-ouaf. » avec U+002D (x1,52 bilineaire, x3)', '*: Ouaf-ouaf.'),
              ('3. Meme ligne avec le demi-cadratin U+2013', '*: Ouaf–ouaf.'),
              ('4. Meme ligne avec le tiret conditionnel U+00AD (meme dessin et meme avance que « - »)', '*: Ouaf­ouaf.'),
              ('5. Meme ligne avec U+2011 (absent de la police : glyphe du « @ »)', '*: Ouaf‑ouaf.')]:
    rows.append((lab, composite(eng_line(t),SCALE,UP)))
# menu : SE-GARRIR, glyphes a 1 px police = 1 unite ; meme echelle d'affichage
rows.append(('6. Police des menus SE-GARRIR (TextMesh Unity) : « Ouaf-ouaf. » (x1,52, x3)', composite(garrir_alpha('Ouaf-ouaf.'),SCALE,UP)))
W=max(i.width for _,i in rows)+20; 
font=ImageFont.load_default()
H=sum(i.height+22 for _,i in rows)+10
canvas=Image.new('RGB',(W,H),(30,30,30)); d=ImageDraw.Draw(canvas); y=5
for lab,i in rows:
    d.text((10,y),lab,fill=(255,255,255),font=font); y+=14; canvas.paste(i,(10,y)); y+=i.height+8
canvas.save('out/compare_ouaf.png'); print(canvas.size)
# Gros plan des pixels natifs du canevas (x10), grille de 8 px autour de f - o
a=E.pixels('*: Ouaf-ouaf.')
x0=6+9+6+6+10+12+10   # pas utilise
im=Image.fromarray(255-a).resize((a.shape[1]*8,a.shape[0]*8),Image.NEAREST).convert('RGB'); d=ImageDraw.Draw(im)
pen=E.PAD; xs=[]
for ch in '*: Ouaf-ouaf.':
    xs.append((ch,pen)); pen+= (6 if ch==' ' else E.glyph(ord(ch))[1])
for ch,x in xs:
    d.line([(x*8,0),(x*8,im.height)],fill=(255,120,120) if ch=='-' else (200,200,255),width=1)
im.save('out/native_cells_x8.png'); print(im.size)
