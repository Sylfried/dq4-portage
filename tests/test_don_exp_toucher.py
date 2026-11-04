"""Le don d'experience du roi (chapitre 1) fige le jeu au dernier message de niveau (#261).

Le menu `MaterielMenu_EXTRA_PRESENT_EXP` (ajout du mobile) attend, une fois les niveaux montres, un declenchement du pad du jeu (`dss::g_Pad + 2`, rempli par `Global::NativeExec` d'apres le 2e argument de `GameUpdate`) :
le toucher d'ecran exactement 0x100, ou les boutons 0x400 a 0x2000. La touche A d'un message (0x10) ne le leve jamais.

  1. `Moteur.attend_toucher` (sans moteur : la memoire est simulee) : vrai seulement si le menu est dans le tableau du gestionnaire de menus ET a son dernier etat ;
  2. `entrees.toucher_pour_le_moteur` : A envoie 0x100 seul quand le menu attend, rien ne change sinon ;
  3. un modele de `Global::NativeExec + 0x74` (code machine relu) montre pourquoi 0x10 et 0x110 ne suffisent pas et 0x100 ou 0x400 oui ;
  4. branchement : `Jeu._entrees` appelle bien la conversion quand un message est ouvert (le test lit le code, sans pyglet).

    python3 tests/test_don_exp_toucher.py
"""
import os, sys, types, unittest

RACINE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
sys.path.insert(0, RACINE)
from dq4_pc.fenetre import entrees as EN
from dq4_pc.noyau import moteur as MO

A, B, PAROLE = 0x10, 0x20, 0x100          # (touches du portage ; toucher d'ecran, voir fenetre/constantes.BTN_PAROLE)
L = 0x10000000


def pad_du_jeu(decl):
    """g_Pad + 2 d'apres le 2e argument de GameUpdate (Global::NativeExec + 0x38 a + 0x74) : les bits 10 a 13 de `decl` (decalages -5, -5, -5, -3, masques 0x20, 0x40, 0x80, 0x400), plus 0x10 quand
    `decl & 0x7fff` vaut exactement 0x100 (le toucher)."""
    v = ((decl >> 5) & 0x20) | ((decl >> 5) & 0x40) | ((decl >> 5) & 0x80) | ((decl >> 3) & 0x400)
    return v | (0x10 if (decl & 0x7fff) == 0x100 else 0)


def moteur_faux(ouvert=True, etat=2, place=0, gestionnaire=True, plante=False):
    """Un moteur dont seule `mem` existe : gestionnaire de menus a GES, tableau de 8 pointeurs a GES + 8, menu du don d'experience a L + 0x24c730 (etat a + 0x30)."""
    GES = L + 0x300000; menu = L + MO.MENU_DON_EXP
    m = {}
    m[(L + MO.GESTIONNAIRE_MENUS, 8)] = (GES if gestionnaire else 0).to_bytes(8, 'little')
    for i in range(8): m[(GES + 8 + 8 * i, 8)] = (menu if (ouvert and i == place) else L + 0x2000 + i).to_bytes(8, 'little')      # (les autres cases : d'autres menus)
    m[(menu + MO.MENU_DON_EXP_ETAT, 1)] = bytes([etat])
    def mem(ad, n):
        if plante: raise RuntimeError('memoire illisible')
        return m[(ad, n)]
    return types.SimpleNamespace(core=types.SimpleNamespace(mem=mem), L=L)


def attend(mo): return MO.Moteur.attend_toucher(mo)


class DetectionDuMenu(unittest.TestCase):
    def test_ouvert_au_dernier_etat(self): self.assertTrue(attend(moteur_faux()))

    def test_toutes_les_cases_du_tableau(self):
        for i in range(8): self.assertTrue(attend(moteur_faux(place=i)), i)

    def test_autres_etats_du_menu(self):
        for etat in (0, 1, 3): self.assertFalse(attend(moteur_faux(etat=etat)), etat)          # comptage de l'experience, niveaux, ... : A tourne les pages du message comme d'habitude

    def test_menu_ferme_meme_si_l_etat_est_reste_a_2(self):
        self.assertFalse(attend(moteur_faux(ouvert=False)))                                    # l'etat reste a 2 apres la fermeture : sans le tableau, chaque message suivant du jeu recevrait le toucher au lieu de A

    def test_sans_gestionnaire(self): self.assertFalse(attend(moteur_faux(gestionnaire=False)))

    def test_memoire_illisible(self): self.assertFalse(attend(moteur_faux(plante=True)))      # jamais d'exception dans la boucle des touches

    def test_adresses_du_jeu(self):
        self.assertEqual((MO.GESTIONNAIRE_MENUS, MO.MENU_DON_EXP, MO.MENU_DON_EXP_ETAT, MO.MENU_DON_EXP_ATTENTE, MO.MENUS_OUVERTS), (0x252078, 0x24c730, 0x30, 2, 8))      # MenuManager::execute et gMaterielMenu_EXTRA_PRESENT_EXP (relus dans la bibliotheque)


class ConversionDeLaTouche(unittest.TestCase):
    def test_a_devient_le_toucher_seul(self):
        p, decl = EN.toucher_pour_le_moteur(A | 0x1, A, A, B, PAROLE, True)
        self.assertEqual(decl, PAROLE); self.assertEqual(p, 0x1)                               # A et B retires des touches tenues, la direction reste
        p, decl = EN.toucher_pour_le_moteur(A | B, A | B, A, B, PAROLE, True)
        self.assertEqual((p, decl), (0, PAROLE))                                               # exactement 0x100 : 0x110 ne passerait pas

    def test_sans_attente_rien_ne_change(self):
        for p, decl in ((A, A), (0, 0), (B, B), (A | 0x4, A | 0x4)): self.assertEqual(EN.toucher_pour_le_moteur(p, decl, A, B, PAROLE, False), (p, decl))

    def test_une_autre_touche_ne_declenche_pas(self):
        self.assertEqual(EN.toucher_pour_le_moteur(0x4, 0x4, A, B, PAROLE, True), (0x4, 0x4))        # une direction, B seul : seul A (ou clic, Entree, Espace qui deviennent A) vaut un toucher
        self.assertEqual(EN.toucher_pour_le_moteur(B, B, A, B, PAROLE, True), (B, B))


class PadDuJeu(unittest.TestCase):
    def test_pourquoi_a_ne_suffisait_pas(self):
        self.assertEqual(pad_du_jeu(A), 0)                    # touche A : g_Pad + 2 reste nul, le menu attend sans fin (le blocage)
        self.assertEqual(pad_du_jeu(A | PAROLE), 0)           # 0x110 non plus : le toucher doit etre seul
        self.assertEqual(pad_du_jeu(0), 0)
        self.assertEqual(pad_du_jeu(PAROLE), 0x10)            # le toucher de l'ecran : il passe
        self.assertEqual(pad_du_jeu(0x400), 0x20); self.assertEqual(pad_du_jeu(0x800), 0x40); self.assertEqual(pad_du_jeu(0x1000), 0x80); self.assertEqual(pad_du_jeu(0x2000), 0x400)

    def test_la_conversion_leve_l_attente(self):
        p, decl = EN.toucher_pour_le_moteur(A, A, A, B, PAROLE, True)
        self.assertNotEqual(pad_du_jeu(decl), 0)


class Branchement(unittest.TestCase):
    def test_entrees_appelle_la_conversion(self):
        """Jeu._entrees (fenetre/clavier_souris.py, a besoin de pyglet : lu comme du texte) envoie A au moteur apres la conversion, seulement quand un message est ouvert (sur le terrain, A = parler, deja 0x100)."""
        with open(os.path.join(RACINE, 'dq4_pc', 'fenetre', 'clavier_souris.py'), encoding='utf-8') as f: src = f.read()
        self.assertIn('from dq4_pc.fenetre import entrees as EN', src)
        ligne = [l for l in src.split('\n') if 'EN.toucher_pour_le_moteur(' in l]
        self.assertEqual(len(ligne), 1)
        self.assertIn('elif decl & MO.A:', ligne[0]); self.assertIn('mo.attend_toucher()', ligne[0]); self.assertIn('BTN_PAROLE', ligne[0])
        i = src.index('elif not mo.msg_visible:'); j = src.index('EN.toucher_pour_le_moteur(')
        self.assertLess(i, j)                                  # apres la branche du terrain (sans message) : elle garde la priorite


if __name__ == '__main__':
    unittest.main(verbosity=1)
