"""Lanceur d'essai (hors depot) : demarre la visionneuse normale, puis, a l'image CAS_N de la boucle, lance un mini-jeu du casino dans le moteur
(Global::setMinigame(CAS_JEU) + Global::startCasino ; 500 jetons ecrits dans le moteur de TEST). CAS_JEU=0 : poker (ev04), 1 : machine a sous (ev05).
Meme ligne de commande que fenetre.py. Aucune modification du depot."""
import sys, os, struct
sys.path.insert(0, '/home/claude/wt-audit/dq4_pc'); os.chdir('/home/claude/wt-audit/dq4_pc')
from dq4_pc.fenetre import jeu as F
orig = F.Jeu.tick
def tick(self, dt):
    if self.n == int(os.environ.get('CAS_N', '150')) and not getattr(self, '_cas', False):
        self._cas = True; mo = self.moteur; c = mo.core; L = mo.L; G = mo._global()
        slotobj = struct.unpack('<Q', c.mem(L + 0x23db38, 8))[0]; joueur = struct.unpack('<Q', c.mem(L + 0x23d428, 8))[0]
        c.mem_w(joueur + 0x2e8, struct.pack('<i', 500))
        if os.environ.get('CAS_MODE') == 'book':
            c.call(mo.E('_ZN6Global9startBookEv'), G, label='book'); print('BESTIAIRE lance a l image', self.n, flush=True)
        else:
            c.call(mo.E('_ZN6Global11setMinigameEi'), G, int(os.environ.get('CAS_JEU', '0')), label='a')
            c.call(mo.E('_ZN17MaterielMenu_SLOT11setSlotTypeEi'), slotobj, 0, label='b')
            c.call(mo.E('_ZN6Global11startCasinoEv'), G, label='c')
            print('CASINO lance a l image', self.n, flush=True)
    r = orig(self, dt)
    if os.environ.get('CAS_FORCEVILLE') and self.moteur.etat.partie in (0xf, 0x10): self.moteur.etat.partie = 0xc     # (essai) affiche la partie casino / bestiaire comme une ville : sert a prouver la cause du rendu manquant
    if os.environ.get('CAS_MODE') == 'book' and self.n == int(os.environ.get('CAS_N', '150')) + 1: pass
    return r
F.Jeu.tick = tick
F.main()
