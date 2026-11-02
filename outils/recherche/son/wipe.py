"""Tout le groupe est battu (PV forces a 1, monstres nombreux) ; usage: wipe.py CHAPITRE [slot] [max_pas] -> journal des sons / textes"""
import sys; sys.path.insert(0, '/tmp/claude-0/-home-claude/17145693-c62f-5af6-a741-2d4f94a36edf/scratchpad/son45_work')
from h45 import *
chap = int(sys.argv[1]); slot = int(sys.argv[2]) if len(sys.argv) > 2 else 1; maxp = int(sys.argv[3]) if len(sys.argv) > 3 else 3500
mo = nouveau('wipe%d' % chap); c = mo.core; tr = Trace(mo)
mo.charger_sauvegarde(slot)
for _ in range(200): mo.step(0, 0)
gs = c.export('_ZN6status7g_StoryE')
if chap > 1:
    c.call(c.export('_ZN6status11StoryStatus10setChapterEi'), gs, chap, label='setChapter')
print('chapitre', struct.unpack('<I', c.mem(gs + 4, 4))[0], 'carte', mo.etat.carte, 'membres', membres(mo))
tr.evt.clear(); mo.capteur.vider()
cb = Combat(mo, tr, monstres=[(3, 4), (4, 4), (5, 4)], hp=[1, 1, 1, 1, 1], verbeux=True)
fin = cb.lancer(max_pas=maxp, apres_combat=500)
