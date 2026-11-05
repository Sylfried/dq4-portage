"""Lanceur d'essai (hors depot) : demarre la visionneuse normale, puis, a l'image CAS_N de la boucle, lance un mini-jeu du casino dans le moteur
(Global::setMinigame(CAS_JEU) + Global::startCasino ; 500 jetons ecrits dans le moteur de TEST). CAS_JEU=0 : poker (ev04), 1 : machine a sous (ev05).
Meme ligne de commande que window.py. Aucune modification du depot."""
import sys, os, struct
sys.path.insert(0, '/home/claude/wt-audit/dq4_pc'); os.chdir('/home/claude/wt-audit/dq4_pc')
from dq4_pc.window import game as F
orig = F.Game.tick
def tick(self, dt):
    if self.n == int(os.environ.get('CAS_N', '150')) and not getattr(self, '_casino', False):
        self._casino = True; eng = self.engine; c = eng.core; L = eng.L; G = eng._global()
        slotobj = struct.unpack('<Q', c.mem(L + 0x23db38, 8))[0]; player = struct.unpack('<Q', c.mem(L + 0x23d428, 8))[0]
        c.mem_w(player + 0x2e8, struct.pack('<i', 500))
        if os.environ.get('CAS_MODE') == 'book':
            c.call(eng.E('_ZN6Global9startBookEv'), G, label='book'); print('BESTIAIRE lance a l image', self.n, flush=True)
        else:
            c.call(eng.E('_ZN6Global11setMinigameEi'), G, int(os.environ.get('CAS_JEU', '0')), label='a')
            c.call(eng.E('_ZN17MaterielMenu_SLOT11setSlotTypeEi'), slotobj, 0, label='b')
            c.call(eng.E('_ZN6Global11startCasinoEv'), G, label='c')
            print('CASINO lance a l image', self.n, flush=True)
    r = orig(self, dt)
    if os.environ.get('CAS_FORCEVILLE') and self.engine.state.part in (0xf, 0x10): self.engine.state.part = 0xc     # (essai) affiche la partie casino / bestiaire comme une ville : sert a prouver la cause du rendu manquant
    if os.environ.get('CAS_MODE') == 'book' and self.n == int(os.environ.get('CAS_N', '150')) + 1: pass
    return r
F.Game.tick = tick
F.main()
