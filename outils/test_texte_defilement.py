"""Tests objectifs (sans fenetre) de la vitesse du texte et du defilement des messages de combat.

Le moteur d'origine tourne sous Unicorn ; on compte des IMAGES DU MOTEUR (30 par seconde), pas du temps :
  - texte : images entre l'ouverture d'un message de dialogue (ui_MsgLoop actif) et la fin de l'ecriture de sa premiere page (etat 3 ou 5 : attente d'une touche) ;
  - defilement : images pendant lesquelles un message de combat attend avant de passer seul au suivant (ui_MsgLoop etat 5 sans menu de commandes), selon OptionStatus.battleSpeed.

Usage (depuis la racine du depot) :
    python3 outils/test_texte_defilement.py --apk "<dossier des APK patches>" --saves "<dossier des sauvegardes>" [--slot 4]
Les sauvegardes ne sont ouvertes qu'en lecture : le moteur ecrit dans un dossier temporaire.
"""
import argparse, os, sys, tempfile, unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'dq4_pc'))
import moteur as MO

ARGS = None
VITESSES = (0.5, 1.0, 2.0, 4.0, 8.0, 16.0, 4000.0)


def demarrer(slot):
    mo = MO.Moteur(ARGS.apk, ARGS.saves, tempfile.mkdtemp(prefix='sv_test_texte_'))
    for _ in range(3): mo.step(0, 0)
    mo.charger_sauvegarde(slot)
    return mo


def images_texte(vitesse, slot):
    """(images entre l'ouverture du message et la fin de sa premiere page, lettres de la page)."""
    mo = demarrer(slot); mo.vitesse_texte = vitesse
    for _ in range(70): mo.step(0, 0)
    mo.step(0, 0x800)                                               # menu de commandes -> « Parler » : le message de la scene s'ouvre
    t_ouv = None; ok = 0
    for i in range(1500):
        p = mo.menu_actif()
        if mo.msg_visible: pass
        elif p is not None and i % 14 == 4 and ok < 4: mo.envoyer_menu(p, 1, -1, 0x10); ok += 1
        elif p is not None and i % 14 == 5: mo.envoyer_menu(p, 1, -1, 0)
        mo.step(0, 0)
        actif, etat, _, fin, _ = mo.etat_message()
        if actif == 1 and t_ouv is None: t_ouv = mo.images
        if t_ouv is not None and etat in (3, 5): return mo.images - t_ouv, fin
    return None, None


def entrer_en_combat(mo):
    for i in range(100): mo.step(0, 0x10 if i % 10 == 0 else 0)
    if mo.etat.partie != MO.PARTIE_CHAMP:
        mo.demarrer_champ()
        for i in range(120): mo.step(0, 0)
    c = mo.core
    c.call(mo.E('_ZN7Encount12forceEncountEv'), c.call(mo.E('_ZN7Encount12getSingletonEv'), label='enc'), label='force')
    for i in range(600):
        mo.step([0x4, 0x8][(i // 20) % 2], 0)
        if mo.etat.partie == MO.PARTIE_COMBAT: return True
    return False


def attentes_combat(code, slot, n=900):
    """Attentes (en images) des messages de combat qui passent seuls, defilement impose = code. Renvoie (liste des attentes, option du jeu a la fin)."""
    mo = demarrer(slot); mo.imposer_defilement(code)
    assert entrer_en_combat(mo), 'pas de combat'
    t5 = None; menu_vu = False; res = []
    for i in range(n):
        p = mo.menu_actif()
        if p is not None and i % 15 == 0: mo.envoyer_menu(p, 1, -1, 0x10)
        elif p is not None and i % 15 == 1: mo.envoyer_menu(p, 1, -1, 0)
        mo.step(0, 0)
        etat = mo.etat_message()[1]
        if p is not None: menu_vu = True
        if etat == 5 and t5 is None: t5 = mo.images; menu_vu = p is not None
        elif etat != 5 and t5 is not None:
            if not menu_vu: res.append(mo.images - t5)
            t5 = None
        if mo.etat.partie != MO.PARTIE_COMBAT and i > 100: break
    return res, mo.options_jeu()[2]


def manuel_attend_une_touche(slot):
    """Defilement a la main : un message de combat reste affiche tant qu'on n'appuie pas (150 images sans touche), puis passe a la touche A."""
    mo = demarrer(slot); mo.imposer_defilement(MO.COMBAT_MANUEL)
    assert entrer_en_combat(mo), 'pas de combat'
    t5 = None
    for i in range(900):
        p = mo.menu_actif()
        if p is not None and i % 15 == 0: mo.envoyer_menu(p, 1, -1, 0x10)
        elif p is not None and i % 15 == 1: mo.envoyer_menu(p, 1, -1, 0)
        mo.step(0, 0)
        if mo.etat_message()[1] == 5 and p is None and mo.menu_actif() is None:
            t5 = t5 or mo.images
            if mo.images - t5 >= 150: break
        else: t5 = None
    else: return None
    for _ in range(150): mo.step(0, 0)                                  # (le message ne doit toujours pas bouger : la boucle ci-dessus avait deja attendu 150 images)
    reste = mo.etat_message()[1] == 5
    mo.step(0, 0x10)
    for _ in range(40): mo.step(0, 0)
    return reste, mo.etat_message()[1] != 5 or mo.menu_actif() is not None


def dialogue_hors_combat(code, slot):
    """Un message de dialogue (hors combat) attend la touche 400 images meme avec le defilement automatique de la sauvegarde : renvoie True s'il n'est pas passe seul."""
    mo = demarrer(slot); mo.imposer_defilement(code)
    for _ in range(70): mo.step(0, 0)
    mo.step(0, 0x800); ok = 0; t5 = None
    for i in range(1500):
        p = mo.menu_actif()
        if mo.msg_visible: pass
        elif p is not None and i % 14 == 4 and ok < 4: mo.envoyer_menu(p, 1, -1, 0x10); ok += 1
        elif p is not None and i % 14 == 5: mo.envoyer_menu(p, 1, -1, 0)
        mo.step(0, 0)
        etat = mo.etat_message()[1]
        if etat == 5 and t5 is None: t5 = mo.images
        if t5 is not None:
            if etat != 5: return False
            if mo.images - t5 >= 400: return True
    return None


class TexteEtDefilement(unittest.TestCase):
    def test_vitesse_du_texte(self):
        mesures = {v: images_texte(v, ARGS.slot) for v in VITESSES}
        for v, (n, lettres) in mesures.items(): print('vitesse %6.1f lettres/image : %4s images (%s lettres)' % (v, n, lettres))
        images = [mesures[v][0] for v in VITESSES]
        self.assertTrue(all(n is not None for n in images))
        self.assertEqual(images, sorted(images, reverse=True), 'plus la vitesse monte, moins il faut d\'images')
        self.assertGreater(images[0], 4 * images[3], 'x1/8 de la vitesse du jeu : au moins 4 fois plus long')
        self.assertLessEqual(images[-1], images[3] // 2, 'instantane : au plus la moitie du temps du jeu')
        lettres = mesures[4.0][1]
        for v in (0.5, 1.0, 2.0):                                         # ecriture lente : le temps est dans les lettres, a l'image pres
            self.assertAlmostEqual(mesures[v][0], lettres / v, delta=lettres / v * 0.08 + 6)

    def test_defilement_des_combats(self):
        attendu = {0: 12, 1: 22, 2: 32, 3: 42}                            # BattleAutoFeed::setMessageSpeed : attente en images selon OptionStatus.battleSpeed
        for code, n in attendu.items():
            res, option = attentes_combat(code, ARGS.slot)
            print('defilement %d : attentes %s' % (code, res))
            self.assertEqual(option, code)
            self.assertGreaterEqual(len(res), 3)
            self.assertEqual(min(res), n)
        res, option = attentes_combat(MO.COMBAT_MANUEL, ARGS.slot)
        print('defilement manuel : attentes %s' % (res,))
        self.assertEqual(res, [], 'a la main : aucun message ne passe seul')

    def test_manuel_attend_la_touche(self):
        r = manuel_attend_une_touche(ARGS.slot)
        print('manuel : message encore la apres 300 images sans touche = %s, passe a la touche A = %s' % r if r else 'manuel : pas de message mesurable')
        self.assertIsNotNone(r)
        self.assertTrue(r[0] and r[1])

    def test_dialogue_hors_combat_jamais_automatique(self):
        for code in (0, 2):
            self.assertTrue(dialogue_hors_combat(code, ARGS.slot), 'defilement %d : le dialogue ne doit pas passer seul' % code)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--apk', required=True); ap.add_argument('--saves', required=True); ap.add_argument('--slot', type=int, default=4)
    ARGS, reste = ap.parse_known_args()
    unittest.main(argv=[sys.argv[0]] + reste, verbosity=2)
