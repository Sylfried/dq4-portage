"""Test du bruitage de transition de carte (porte, sortie / entree de village, escalier, carte du monde <-> ville) avec la « Vitesse de transition » de la visionneuse.

Cause (retours de 22 h 29 : « il n'y a toujours pas les bruitages de transition de map ») : le bruitage 305 de la transition n'est pas lance par Unity ni par la porte (celle-ci joue le 309 a l'ouverture) mais par
Global::NativeExec, 15 images apres que startTown / startField ont lance le fondu au noir de 30 images (decompte de l'octet LIB + 0x258254) ; il n'est joue que si l'ancienne scene vit encore. Le chargement de la carte suivante
arrive a la fin du fondu : dans le jeu d'origine, le bruitage est demande a mi-fondu. Avec un fondu raccourci (x3 : 10 images, x4 : 8 images ; marginal a x2 : 15 images), l'ancienne scene etait detruite avant les 15 images
et le moteur ne demandait plus rien. Moteur._decompte_sortie remet le decompte a la meme proportion que le fondu ; la duree des fondus ne change pas.

  1. calcul pur : proportion du fondu memorisee par Etat._fondu, ajustement du decompte (faux coeur) ;
  2. moteur d'origine (DQ_APK + DQ_SAVES, sauvegarde 1 : Ragnar a Strattbourg) : la porte de l'eglise et la sortie du village vers la carte du monde, dans les deux sens, a chaque « Vitesse de transition » (x1 a x4) : un seul bruitage 305, demande entre le debut du fondu et
     le chargement de la carte, apres le 309 de la porte ; fondu de la duree reglee ;
  3. visionneuse (Son, faux lecteurs) : les deux bruitages restent joues jusqu'a leur fin quand le chargement de la carte bloque la boucle (voir test_son_mixage).

    DQ_APK=... DQ_SAVES=... python3 outils/test_bruitage_transition.py
"""
import os, sys, tempfile, unittest

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ICI, '..'))
APK, SAVES = os.environ.get('DQ_APK'), os.environ.get('DQ_SAVES')
VITESSES = (1.0, 1.5, 2.0, 3.0, 4.0)       # « Vitesse de transition » : 1.0 = comme le jeu ; 4.0 = le maximum du menu
FONDU_JEU = 30                              # images du fondu au noir de startTown / startField (UnitySetFade(0x101e))


class FauxCoeur:
    """Memoire du moteur reduite a l'octet du decompte."""
    def __init__(self): self.octet = 0; self.ecrits = []
    def mem(self, adr, n): return bytes([self.octet])
    def mem_w(self, adr, donnees): self.octet = donnees[0]; self.ecrits.append(donnees[0])


def moteur_factice():
    from dq4_pc.noyau import moteur as MO
    m = MO.Moteur.__new__(MO.Moteur)
    m.core = FauxCoeur(); m.L = 0; m.etat = MO.Etat(); m.images = 0; m._decompte = 0; m._decompte_arme = -99; m._decompte_fait = True
    return m


class Calcul(unittest.TestCase):
    def setUp(self):
        from dq4_pc.noyau import moteur as MO
        self.MO = MO; self.vitesse = MO.Etat.vitesse_fondu

    def tearDown(self): self.MO.Etat.vitesse_fondu = self.vitesse

    def fondu(self, v, partie=None, image=7):
        e = self.MO.Etat(); e.image = image
        if partie is not None: e.partie = partie
        e.appliquer([(9, [v], [])], lambda: 'x')
        return e

    def test_proportion_memorisee_par_etat(self):
        from dq4_pc.noyau import priorite_jeu as PJ
        for vf in VITESSES:
            self.MO.Etat.vitesse_fondu = vf
            e = self.fondu(0x1000 | FONDU_JEU)
            self.assertEqual(e.rapport_fondu[0], 7)
            self.assertAlmostEqual(e.rapport_fondu[1], PJ.duree_fondu(FONDU_JEU, vf) / FONDU_JEU, 6, 'x%s' % vf)
        self.MO.Etat.vitesse_fondu = 1.0
        self.assertEqual(self.fondu(0x1000 | FONDU_JEU).rapport_fondu[1], 1.0, 'x1 : duree du jeu')

    def test_combat_raccourci_comme_les_autres_et_entree_sans_decompte(self):
        from dq4_pc.noyau import priorite_jeu as PJ
        self.MO.Etat.vitesse_fondu = 4.0
        self.assertAlmostEqual(self.fondu(0x1000 | FONDU_JEU, partie=self.MO.PARTIE_COMBAT).rapport_fondu[1], PJ.duree_fondu(FONDU_JEU, 4.0) / FONDU_JEU, 6, 'fondu d\'un combat : suit « Vitesse de transition » (#47)')
        self.assertEqual(self.fondu(FONDU_JEU).rapport_fondu[1], 1.0, 'fondu d\'entree (vers la scene) : pas de decompte a ajuster')

    def arme(self, m, octet, rapport, image_fondu=None):
        """Un pas ou le moteur arme le decompte (15, deja decremente une fois : 14) et ou le fondu de cette sortie arrive."""
        m.etat.rapport_fondu = (m.images if image_fondu is None else image_fondu, rapport)
        m.core.octet = octet; m._decompte_sortie()

    def test_decompte_remis_a_la_proportion_du_fondu(self):
        for r, attendu in ((1.0, 14), (0.5, 7), (10 / 30, 5), (8 / 30, 4)):
            m = moteur_factice(); self.arme(m, 14, r)
            self.assertEqual(m.core.octet, attendu, 'rapport %.2f' % r)
            m.images += 1; m._decompte_sortie(); self.assertEqual(m.core.octet, attendu, 'une seule fois')
        m = moteur_factice(); self.arme(m, 1, 0.1); self.assertEqual(m.core.octet, 1, 'jamais 0 : le bruitage est demande a l\'image suivante, pas annule')

    def test_rapport_un_ne_touche_a_rien(self):
        m = moteur_factice(); self.arme(m, 14, 1.0); self.assertEqual(m.core.ecrits, [], 'aucune ecriture dans le moteur')

    def test_fondu_arrive_une_image_apres_l_armement(self):
        m = moteur_factice(); m.core.octet = 14; m._decompte_sortie(); self.assertEqual(m.core.octet, 14, 'pas de fondu connu : rien')
        m.images += 1; m.core.octet = 13; m.etat.rapport_fondu = (m.images, 0.5); m._decompte_sortie()
        self.assertEqual(m.core.octet, 6, 'le fondu de la sortie est arrive juste apres : decompte restant (13) remis a la proportion (13 x 0,5 arrondi)')

    def test_fondu_sans_rapport_avec_le_decompte(self):
        m = moteur_factice(); m.etat.rapport_fondu = (-50, 0.25); m.core.octet = 14; m._decompte_sortie()
        self.assertEqual(m.core.octet, 14, 'un fondu ancien n\'est pas celui de cette sortie')
        m.images += 3; m.etat.rapport_fondu = (m.images, 0.25); m._decompte_sortie()
        self.assertEqual(m.core.octet, 14, 'passe 2 images, plus d\'ajustement')


@unittest.skipUnless(APK and SAVES, 'moteur reel : DQ_APK=<dossier des APK patches> DQ_SAVES=<dossier des sauvegardes>')
class MoteurReel(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from dq4_pc.noyau import moteur as MO; from dq4_pc.persistance import etats as ET
        cls.MO, cls.ET = MO, ET
        cls.mo = MO.Moteur(APK, SAVES, tempfile.mkdtemp(prefix='sv_bruit_trans_'))
        cls.mo.charger_sauvegarde(1)
        for _ in range(250): cls.mo.step(0, 0)
        n = 0
        while (cls.mo.msg_visible or cls.mo.menu_actif() is not None) and n < 1500:           # message d'accueil de la sauvegarde : A jusqu'a sa fermeture
            n += 1; cls.mo.step(MO.A, MO.A) if n % 6 == 0 else cls.mo.step(0, 0)
        for _ in range(40): cls.mo.step(0, 0)
        cls.depart = ET.instantane(cls.mo)
        cls.vitesse = MO.Etat.vitesse_fondu

    @classmethod
    def tearDownClass(cls): cls.MO.Etat.vitesse_fondu = cls.vitesse

    def trajet(self, direction):
        """Marche dans `direction` jusqu'a la porte (ou la sortie du village) puis laisse la carte suivante se charger. -> [(image, genre, valeur)] : SE (paquet 35), FONDU (duree, paquet 9 vers le noir), CHARGE (premier paquet 0 ou 27 :
        decor de ville ou carte du monde), N (images du fondu apres son 1er pas : duree reglee - 1)."""
        mo, e = self.mo, self.mo.etat; apres = None; log = []; charge = False
        for i in range(1500):
            pq = mo.step(direction if apres is None else 0, direction if i == 0 else 0)
            for t, a, f in pq:
                if t == 35: log.append((mo.images, 'SE', a[0]))
                elif t == 9 and a[0] & 0x1000: log.append((mo.images, 'FONDU', a[0] & 0x7ff)); log.append((mo.images, 'N', e.fondu['n']))
                elif t in (0, 27) and not charge: log.append((mo.images, 'CHARGE', t)); charge = True
            if charge and apres is None: apres = 0
            if apres is not None:
                apres += 1
                if apres > 30: return log
        self.fail('la transition n\'a pas eu lieu : %r' % (log,))

    def remettre(self, vf):
        self.ET.appliquer(self.mo, self.depart); self.MO.Etat.vitesse_fondu = vf
        self.mo._decompte = 0; self.mo._decompte_arme = -99; self.mo._decompte_fait = True

    def verifier(self, log, vf, nom):
        from dq4_pc.noyau import priorite_jeu as PJ
        im = {g: [x[0] for x in log if x[1] == g] for g in ('FONDU', 'CHARGE')}
        ses = [(x[0], x[2]) for x in log if x[1] == 'SE']
        self.assertEqual(len(im['FONDU']), 1, nom); self.assertEqual(len(im['CHARGE']), 1, nom)
        fondu, charge = im['FONDU'][0], im['CHARGE'][0]
        n = next(x[2] for x in log if x[1] == 'N')
        self.assertEqual(n + 1, PJ.duree_fondu(FONDU_JEU, vf), '%s : le fondu garde la duree reglee (x%s)' % (nom, vf))
        sorties = [i for i, v in ses if v == 305]
        self.assertEqual(len(sorties), 1, '%s (x%s) : un bruitage de transition 305 demande : %r' % (nom, vf, log))
        self.assertTrue(fondu <= sorties[0] < charge, '%s (x%s) : demande entre le debut du fondu (%d) et le chargement (%d), pas apres : %d' % (nom, vf, fondu, charge, sorties[0]))
        return ses

    def test_porte_de_l_eglise_dans_les_deux_sens(self):
        for vf in VITESSES:
            self.remettre(vf)
            aller = self.trajet(self.MO.BAS)
            ses = self.verifier(aller, vf, 'eglise > village')
            self.assertEqual([v for _, v in ses], [309, 305], 'x%s : la porte (309) puis la transition (305)' % vf)
            for _ in range(80): self.mo.step(0, 0)
            retour = self.trajet(self.MO.HAUT)
            self.verifier(retour, vf, 'village > eglise')
            self.assertEqual(self.mo.etat.carte, 'mak1f1')

    def test_sortie_du_village_vers_la_carte_du_monde_et_retour(self):
        """Le village (`maout`) s'ouvre sur la carte du monde a droite : sortie (startField, TownSystem::playTownExitSE) puis retour (startTown, FieldSystem::playFieldExitSE), memes bruitages 305."""
        for vf in VITESSES:
            self.remettre(vf)
            self.trajet(self.MO.BAS)
            for _ in range(80): self.mo.step(0, 0)
            self.verifier(self.trajet(self.MO.DROITE), vf, 'village > carte du monde')
            self.assertEqual(self.mo.etat.partie, self.MO.PARTIE_CHAMP)
            for _ in range(120): self.mo.step(self.MO.DROITE, 0)               # (quelques pas sur la carte du monde, l'entree du village est a gauche)
            for _ in range(40): self.mo.step(0, 0)
            self.verifier(self.trajet(self.MO.GAUCHE), vf, 'carte du monde > village')
            self.assertEqual(self.mo.etat.partie, self.MO.PARTIE_VILLE)

    def test_x1_comme_le_jeu(self):
        """Sans fondu raccourci, rien ne change : le bruitage 305 est demande 14 images apres le fondu, comme avant."""
        self.remettre(1.0)
        log = self.trajet(self.MO.BAS)
        fondu = next(x[0] for x in log if x[1] == 'FONDU'); se = next(x[0] for x in log if x[1:] == ('SE', 305))
        self.assertEqual(se - fondu, 14)


if __name__ == '__main__':
    unittest.main(verbosity=2)
