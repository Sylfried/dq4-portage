import sys
sys.path.insert(0, '/home/claude/wt45-chargement/dq4_pc')
import pyglet
pyglet.options['headless'] = True; pyglet.options['shadow_window'] = False
from dq4_pc.window import game as F
F.main()
