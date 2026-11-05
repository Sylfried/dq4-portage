"""Appelle les vraies fonctions du moteur MenuSoundManager::setPlaySound(type) puis isPlaySound() une fois par image (comme MaterielMenu_INN_ROOT::fadeEffect) et note les appels SoundManager."""
import sys, os, struct, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from h import *
import zipfile
from dq4_pc import sound as S
m = new(1); c = m.core
tr = Trace(m)
mgr = c.export('gMenuSoundManager'); setp = m.E('_ZN16MenuSoundManager12setPlaySoundENS_10MENU_SOUNDE'); isp = m.E('_ZN16MenuSoundManager11isPlaySoundEv')
z = zipfile.ZipFile(os.path.join(APK, 'split_UnityDataAssetPack.apk'))
def dur(b):
    d = z.read('assets/sound/BGM%02d.akb' % b); h = S.read_header(d); return h['echantillons'] / h['frequence']
out = []
for t in range(1, 16):
    tr.evt.clear()
    c.call(setp, mgr, t, label='set')
    frame = 0; ev = []; ret_frames = []
    n0 = 0
    for frame in range(1, 900):
        m.frames = frame               # horodatage des crochets (la trace lit eng.frames)
        r = c.call(isp, mgr, label='isp')
        ret_frames.append(r & 0xffffffff)
        if (r & 0xffffffff) == 0 and frame > 1: break
    evs = [(e[0], e[1].replace('_ZN12SoundManager', '').replace('Ei', ''), e[2]) for e in tr.evt]
    plays = [(f, n, a) for f, n, a in evs if n in ('7playBgm', '4play', '9playStart', '11playRestart')]
    stops = [(f, n, a) for f, n, a in evs if n in ('7stopBgm', '4stop')]
    others = [(f, n, a) for f, n, a in evs if (f, n, a) not in plays and (f, n, a) not in stops]
    out.append(dict(type=t, plays=plays, stops=stops, others=others, last_frame=frame))
    p0 = plays[0] if plays else None
    s_ = [x for x in stops if p0 and x[0] > p0[0]]
    line = 'type %2d : ' % t
    if p0:
        d = dur(p0[2]); w = (s_[0][0] - p0[0]) / 30.0 if s_ else None
        line += 'play BGM%02d a l\'image %d ; arret a l\'image %s ; fenetre %.3f s ; fichier %.3f s ; ' % (p0[2], p0[0], s_[0][0] if s_ else '-', w or 0, d)
    line += 'isPlaySound rend 0 a l\'image %d ; appels : %s' % (frame, [(f, n, hex(a)) for f, n, a in evs])
    print(line)
json.dump(out, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'menu_sound_real.json'), 'w'))
