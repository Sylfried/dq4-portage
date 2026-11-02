"""Scenarios de combat : usage scen_combat.py SCENARIO ; SCENARIO = niveau | fuite | boss"""
import sys; sys.path.insert(0, '/tmp/claude-0/-home-claude/17145693-c62f-5af6-a741-2d4f94a36edf/scratchpad/son45_work')
from h45 import *
sc = sys.argv[1]
mo = nouveau('sc_' + sc); c = mo.core; tr = Trace(mo)
mo.charger_sauvegarde(1)
for _ in range(200): mo.step(0, 0)
orig = c.export('_ZN6status9PartyData15originalPlayer_E')
if sc == 'niveau':
    for i in (3, 12):
        hs = orig + PAS_JOUEUR * i + OFF_HS
        need = struct.unpack_from('<I', c.mem(hs, 0x30), 0x18)[0]
        print('membre', i, 'xp requise', need)
        if need > 0: c.mem_w(hs + 8, struct.pack('<I', need - 1))
tr.evt.clear(); mo.capteur.vider()
cb = Combat(mo, tr, monstres=[(3, 1)] if sc != 'fuite' else [(3, 4), (4, 4)], hp=None, verbeux=True)
if sc == 'fuite':
    orig_lancer = cb.lancer
    # on envoie le bouton « Fuir » (n°2 ?) sur le menu racine du combat (port 13, type 30)
    def avant(cb_, k):
        pass
    fin = cb.lancer(max_pas=3000, apres_combat=300)
else:
    fin = cb.lancer(max_pas=3000, apres_combat=300)
