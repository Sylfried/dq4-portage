"""Fuite en combat : bouton « Fuir » du menu racine ; usage fuite.py [nb essais de seed] """
import sys
sys.path.insert(0, '/tmp/claude-0/-home-claude/17145693-c62f-5af6-a741-2d4f94a36edf/scratchpad/son45_work')
from h45 import *
mo = nouveau('fuite'); c = mo.core; tr = Trace(mo)
mo.charger_sauvegarde(1)
for _ in range(200): mo.step(0, 0)
tr.evt.clear(); mo.capteur.vider()
cb = Combat(mo, tr, monstres=[(3, 3), (4, 3)], hp=[999, 999], verbeux=True)
etat = {'vu': set()}
def avant(cb_, k):
    port = mo.menu_actif()
    if port is not None and not mo.msg_visible and port not in etat['vu']:
        etat['vu'].add(port); print('   MENU port', port, mo.ui.f[port].get('type'), {a: b[:12] for a, b in mo.ui.f[port]['cases'].items()})
cb.bouton = {30: 3}
cb.lancer(max_pas=1500, avant_boucle=avant, apres_combat=200)
