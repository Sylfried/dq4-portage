"""Carte du monde : ordre de superposition des membres du groupe a l'atterrissage (issue #135 : « une fois atterri, Doc s'est retrouve devant Ragnar »).

    python3 outils/test_ordre_groupe_champ.py                                                    (partie sans moteur : Linux sans ecran, pyglet en mode « headless »)
    DQ_APK=<dossier des APK patches> DQ_SAVES=<dossier des sauvegardes> python3 outils/test_ordre_groupe_champ.py      (ajoute le scenario du moteur reel)

Origine : FieldPartyDraw::draw (libdq4core 0x1ec5a8) trie les membres du groupe par profondeur decroissante (tri par selection, a profondeur egale l'emplacement le plus bas garde la tete) puis leur
donne SpriteCharacter::setDepth 10, 9, 8... : a profondeur egale, le heros est DEVANT ses equipiers. Un atterrissage (Zoom, aile de chimere) empile le groupe sur un seul point (mesure sur le vrai moteur : heros
et Doc a (2495,967 ; 391,967 ; z 200) apres la descente), c'est donc la regle d'egalite qui decide. Avant : `sorted((z, y, emplacement))` mettait le plus grand emplacement devant (Doc).

  1. sans moteur (`rang_profondeur_champ`) : position egale -> heros devant ; hauteur z, puis « plus au sud », priment toujours ; vehicules (>= 10) : le plus recent devant, sans changer le groupe ;
  2. moteur reel (sauvegarde 1, groupe Ragnar + Doc) : sort Teleportation (action 203) lance depuis le village de maout vers le 2e lieu (carte du monde), descente jusqu'a l'arret : le groupe est empile
     (memes x, y, z) et le heros est devant Doc ; pendant la descente, Doc (au nord, z plus petit) reste derriere le heros."""
import os, sys, tempfile, unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'dq4_pc'))
import pyglet
if sys.platform.startswith('linux') and not os.environ.get('DISPLAY'): pyglet.options['headless'] = True; pyglet.options['shadow_window'] = False
import fenetre as F

APK, SAVES = os.environ.get('DQ_APK'), os.environ.get('DQ_SAVES')


def sp(x, y, z=None): return {'pos': (x, y) if z is None else (x, y, z)}


class OrdreSansMoteur(unittest.TestCase):
    def test_position_egale_le_heros_est_devant(self):
        r = F.rang_profondeur_champ({0: sp(2495.967, 391.967, 200.0), 1: sp(2495.967, 391.967, 200.0)})
        self.assertGreater(r[0], r[1])

    def test_groupe_de_quatre_empile_dans_l_ordre_du_groupe(self):
        r = F.rang_profondeur_champ({n: sp(10.0, 20.0, 200.0) for n in range(4)})
        self.assertEqual(sorted(r, key=lambda n: -r[n]), [0, 1, 2, 3])          # devant -> derriere

    def test_la_hauteur_prime(self):
        r = F.rang_profondeur_champ({0: sp(10.0, 20.0, 180.0), 1: sp(10.0, 20.0, 200.0)})
        self.assertGreater(r[1], r[0])

    def test_le_plus_au_sud_prime_sur_l_emplacement(self):
        r = F.rang_profondeur_champ({0: sp(10.0, 20.0, 200.0), 1: sp(10.0, 26.0, 200.0)})
        self.assertGreater(r[1], r[0])
        r = F.rang_profondeur_champ({0: sp(10.0, 26.0, 200.0), 1: sp(10.0, 20.0, 200.0)})
        self.assertGreater(r[0], r[1])

    def test_vehicules_le_plus_recent_devant_et_groupe_inchange(self):
        r = F.rang_profondeur_champ({0: sp(1.0, 2.0, 200.0), 1: sp(1.0, 2.0, 200.0), 10: sp(1.0, 2.0, 200.0), 11: sp(1.0, 2.0, 200.0)})
        self.assertGreater(r[11], r[10]); self.assertGreater(r[0], r[1])

    def test_sprite_sans_position_ignore_et_z_absent(self):
        r = F.rang_profondeur_champ({0: sp(1.0, 2.0), 1: {'pos': None}, 2: sp(1.0, 2.0)})
        self.assertEqual(set(r), {0, 2}); self.assertGreater(r[0], r[2])


@unittest.skipUnless(APK and SAVES, 'moteur reel : DQ_APK=<dossier des APK patches> DQ_SAVES=<dossier des sauvegardes>')
class AtterrissageMoteurReel(unittest.TestCase):
    BTN_PAROLE, BTN_MENU = 0x100, 0x800

    def avance(self, mo, n, tenu=0, decl=None):
        for i in range(n): mo.step(tenu, (tenu if decl is None else (decl if i == 0 else 0)))

    def test_atterrissage_sur_la_carte_du_monde(self):
        import moteur as MO
        mo = MO.Moteur(APK, SAVES, tempfile.mkdtemp(prefix='sv_135_')); mo.charger_sauvegarde(1); self.avance(mo, 120)
        for _ in range(30):
            self.avance(mo, 1, 0, self.BTN_PAROLE); self.avance(mo, 20)
            if not mo.msg_visible and not (mo.drapeaux() & 4): break
        self.avance(mo, 30); c = mo.core
        ha = c.export('_ZN6status9PartyData15originalPlayer_E') + 0x530 * 12 + 0xd0                     # Doc (emplacement 12 de PlayerStatus)
        c.call(c.export('_ZN6status10HaveAction5clearEv'), ha); c.call(c.export('_ZN6status10HaveAction3addEii'), ha, 203, 0)       # 203 = Teleportation
        mo.capteur.vider(); depart = mo._nom_carte()
        for _ in range(300):                                                  # sortir de l'eglise (haut) : village de maout, en plein air
            self.avance(mo, 1, 2)
            if mo._nom_carte() != depart: break
        self.assertEqual(mo._nom_carte(), 'maout'); self.avance(mo, 70)
        self.avance(mo, 1, 0, self.BTN_MENU); self.avance(mo, 20)
        mo.envoyer_menu(4, 1, 1, 0x10); self.avance(mo, 20)                   # menu racine : Magie
        mo.envoyer_menu(5, 1, 3, 0x10); self.avance(mo, 25)                   # Doc
        mo.envoyer_menu(8, 1, 0, 0x10); self.avance(mo, 20)                   # le sort
        mo.envoyer_menu(8, 1, 1, 0x10)                                        # 2e lieu : sur la carte du monde
        egaux, descente = 0, 0
        for _ in range(900):
            self.avance(mo, 1)
            if mo.msg_visible and mo.images % 20 == 0: self.avance(mo, 1, 0, self.BTN_PAROLE)
            if mo.etat.partie != MO.PARTIE_CHAMP: continue
            s0, s1 = mo.etat.sprites.get(0), mo.etat.sprites.get(1)
            if not s0 or not s1 or s0['pos'] is None or s1['pos'] is None: continue
            r = F.rang_profondeur_champ(mo.etat.sprites)
            if s0['pos'] == s1['pos']: egaux += 1; self.assertGreater(r[0], r[1], 'empiles : le heros doit etre devant (%s)' % (s0['pos'],))
            elif s1['pos'][2] < s0['pos'][2]: descente += 1; self.assertGreater(r[0], r[1], 'Doc (z plus petit) doit rester derriere le heros')
        print('\n  images de descente (Doc au nord, z plus petit) : %d ; images empilees : %d ; positions finales : %s / %s' % (descente, egaux, mo.etat.sprites[0]['pos'], mo.etat.sprites[1]['pos']), flush=True)
        self.assertGreater(descente, 5); self.assertGreater(egaux, 5)          # la descente a bien ete vue, et l'arret empile aussi


if __name__ == '__main__':
    unittest.main(verbosity=2)
