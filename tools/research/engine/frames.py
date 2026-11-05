"""Cadres du frameData : python3 frames.py <i0> <i1>  (sous xvfb-run : ui_menu importe pyglet)"""
import sys; sys.path.insert(0,'/home/claude/dq4-portage/dq4_pc')
from dq4_pc.menus import ui_menu as U
c=U.read_borders('/tmp/r3_res/ui_frameData.bin')
a=int(sys.argv[1]) if len(sys.argv)>1 else 0; b=int(sys.argv[2]) if len(sys.argv)>2 else len(c)
print('UI frames',len(c))
for i in range(a,min(b,len(c))):
    v=c[i]['vtx']; xs=[p[0] for p in v]; ys=[p[1] for p in v]
    print(i,'x',min(xs),max(xs),'y',min(ys),max(ys),'nv',len(v))
