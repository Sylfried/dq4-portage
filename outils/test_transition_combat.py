"""Transitions d'un combat (retours de 22 h 29, #47 ; avant : #45, retour de 14 h 08).

Sylfried : « L'accélération du combat doit être prise en compte dès la fin de l'animation de transition en cascade et dès l'apparition du message indiquant qu'un ennemi apparaît, et finalement je veux qu'elle dure
jusqu'à la fin donc pendant le fondu au noir » ; « Les effets de transitions au début et à la fin d'un combat eux doivent en tous cas être affectés par l'accélération de transition des paramètres, comme tout effet de transition ».

La transition = effet d'ecran de debut (la « cascade » : 57 images du jeu), ecran noir qui attend la scene, fondu d'arrivee du combat, fondus de sortie du combat, fondu de retour a la carte. Regles verifiees :
  - DUREE (images du moteur) : la cascade et chaque fondu durent ce que demande le jeu divise par « Vitesse de transition » (x1 a x4), comme un fondu de changement de carte (priorite_jeu.duree_fondu) ;
  - HORLOGE (temps reel) : la cascade est a l'horloge du jeu (30 images par seconde) quels que soient « Vitesse de combat », vitesse de marche et accelerateur ; des la fin de la cascade (ecran noir, fondu d'arrivee,
    message « X apparait ») et jusqu'au fondu de fin de combat compris, « Vitesse de combat » (x1, x1, x2, x3) s'applique ; le retour a la carte est a l'horloge du jeu tant que le joueur est verrouille (flag 4) ; des qu'il est libre (image 12 du retour, le heros marche des la 13), la marche acceleree et l'accelerateur agissent (#127, comme #107 pour un changement de carte).

    python3 outils/test_transition_combat.py        (Linux sans ecran : pyglet en mode « headless »)
    DQ_APK=<dossier des APK patches> DQ_SAVES=<dossier des sauvegardes> outils/flux_session/moteur_slot.sh python3 -W ignore outils/test_transition_combat.py     (ajoute le rejeu d'un vrai combat du moteur)
Les sauvegardes ne sont ouvertes qu'en lecture : le moteur ecrit dans un dossier temporaire."""
import itertools, os, sys, tempfile, types, unittest

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ICI, '..', 'dq4_pc'))
try:
    import pyglet
    if sys.platform.startswith('linux') and not os.environ.get('DISPLAY'): pyglet.options['headless'] = True; pyglet.options['shadow_window'] = False
    import fenetre as F
except Exception as ex:
    F = None; ERREUR_IMPORT = ex
import moteur as MO
import priorite_jeu as PJ

APK, SAVES = os.environ.get('DQ_APK'), os.environ.get('DQ_SAVES')
PAS = 1.0 / 30.0
FONDU_COMBAT = 0x1000 | 30              # paquet 9 : sortie au noir en 30 images (4126, vu a la fin de chaque combat)
ENTREE_30 = 30                          # paquet 9 : entree en 30 images


def etat(partie=MO.PARTIE_CHAMP, vitesse_fondu=1.0):
    e = MO.Etat(); e.partie = partie; MO.Etat.vitesse_fondu = vitesse_fondu; return e


class Fondus(unittest.TestCase):
    def tearDown(self): MO.Etat.vitesse_fondu = 1.0

    def test_hors_combat_le_reglage_raccourcit_toujours(self):
        for vf, attendu in ((1.0, 30), (2.0, 15), (4.0, 8)):
            e = etat(MO.PARTIE_CHAMP, vf); e.appliquer([(9, [ENTREE_30], [])], lambda: ''); self.assertEqual(e.fondu['n'], attendu, 'x%g' % vf); self.assertFalse(e.fondu['combat'])
            self.assertFalse(e.transition_combat())

    def test_fondu_d_arrivee_du_combat_suit_la_vitesse_de_transition(self):
        for vf in (1.0, 2.0, 3.0, 4.0):
            d = PJ.duree_fondu(30, vf)
            e = etat(MO.PARTIE_CHAMP, vf); e.appliquer([(0, [0x100], []), (9, [ENTREE_30], [])], lambda: 'btl_pl_d')           # chargement de la scene de combat (bit 8) puis fondu d'entree, meme image du moteur
            self.assertEqual(e.fondu['n'], d, 'x%g' % vf); self.assertTrue(e.fondu['combat']); self.assertTrue(e.transition_combat())
            e.chargement = None                                                                                                      # (la retenue du dessin apres un chargement retarde le DEBUT du fondu, pas sa duree : test_chargement)
            for i in range(d - 1): e.tick_fondu(); e.tick_transition(); self.assertTrue(e.transition_combat(), 'image %d' % i)
            e.tick_fondu(); self.assertEqual(e.fondu['n'], 0)
        self.assertEqual([PJ.duree_fondu(30, v) for v in (1.0, 2.0, 3.0, 4.0)], [30, 15, 10, 8])

    def test_fondu_de_fin_de_combat_et_retour_a_la_carte_suivent_la_vitesse_de_transition(self):
        for vf in (1.0, 2.0, 4.0):
            d, d3 = PJ.duree_fondu(30, vf), PJ.duree_fondu(3, vf)
            e = etat(MO.PARTIE_COMBAT, vf); e.appliquer([(9, [FONDU_COMBAT], [])], lambda: '')
            self.assertEqual(e.fondu['n'], d, 'x%g' % vf); self.assertTrue(e.transition_combat())
            for _ in range(d): e.tick_fondu(); e.tick_transition()
            self.assertEqual(e.fondu['n'], 0); self.assertGreater(e.garde_trans, 0); self.assertTrue(e.transition_combat())       # le moteur change de scene 1 a 3 images plus tard
            e.appliquer([(9, [0x4000 | 3], [])], lambda: ''); self.assertEqual(e.fondu_fond['n'], d3 if d3 > 1 else 0)           # fondu du plan de fond (encore dans la partie combat) : meme regle
            e.tick_fondu(); e.tick_transition()
            e.partie = MO.PARTIE_CHAMP; e.fen_retour = MO.FENETRE_RETOUR_COMBAT                                                   # (Moteur.step : la partie quitte le combat)
            e.appliquer([(9, [ENTREE_30], [])], lambda: ''); self.assertEqual(e.fondu['n'], d, 'retour x%g' % vf); self.assertTrue(e.fondu['combat'])
            for _ in range(d): self.assertTrue(e.transition_combat()); e.tick_fondu(); e.tick_transition()
            for _ in range(MO.GARDE_TRANSITION + 2): e.tick_fondu(); e.tick_transition()
            self.assertFalse(e.transition_combat())                                                                               # la transition est finie : la marche reprend ses reglages

    def test_cascade_suit_la_vitesse_de_transition(self):
        """Moteur._debut_effet_combat / _effet_combat (sans moteur : le drapeau d'effet est simule) : 57 images a x1, 57 / facteur ensuite ; la simulation de la visionneuse atteint ses 57 images au dernier dessin."""
        import math
        for vf in (1.0, 2.0, 3.0, 4.0):
            MO.Etat.vitesse_fondu = vf; e = MO.Etat(); mo = types.SimpleNamespace(etat=e, _drapeau_effet=lambda a: None)
            MO.Moteur._debut_effet_combat(mo, 0); d = PJ.duree_fondu(MO.EFFET_COMBAT_IMAGES, vf); self.assertEqual(e.effet['duree'], d); n = 0; cibles = []
            while e.effet is not None:
                cibles.append(math.ceil(e.effet['n'] * MO.EFFET_COMBAT_IMAGES / e.effet['duree'])); MO.Moteur._effet_combat(mo); n += 1
            self.assertEqual(n, d, 'x%g' % vf); self.assertEqual(cibles[0], 0); self.assertGreaterEqual(cibles[-1], MO.EFFET_COMBAT_IMAGES - math.ceil(MO.EFFET_COMBAT_IMAGES / d))      # (dernier dessin : la cascade est quasi finie)
            self.assertTrue(all(b >= a for a, b in zip(cibles, cibles[1:])))
        self.assertEqual([PJ.duree_fondu(MO.EFFET_COMBAT_IMAGES, v) for v in (1.0, 2.0, 4.0)], [57, 28, 14])
        e = MO.Etat(); e.effet = {'n': 3}; mo = types.SimpleNamespace(etat=e, _drapeau_effet=lambda a: None)           # (etat enregistre avant la cle 'duree' : 57 images)
        for _ in range(MO.EFFET_COMBAT_IMAGES - 4): MO.Moteur._effet_combat(mo)
        self.assertIsNotNone(e.effet); MO.Moteur._effet_combat(mo); self.assertIsNone(e.effet)

    def test_la_fenetre_d_arrivee_s_ecoule(self):
        """Un fondu lance bien apres le chargement du combat (ou une carte ordinaire) reste soumis a « Vitesse de transition »."""
        e = etat(MO.PARTIE_CHAMP, 2.0); e.appliquer([(0, [0x100], [])], lambda: 'btl_pl_d')
        for _ in range(MO.FENETRE_ENTREE_COMBAT + 1): e.tick_transition()
        e.attente_charge = None; e.partie = MO.PARTIE_CHAMP
        e.appliquer([(9, [ENTREE_30], [])], lambda: ''); self.assertEqual(e.fondu['n'], 15); self.assertFalse(e.fondu['combat']); self.assertFalse(e.transition_combat())
        e2 = etat(MO.PARTIE_CHAMP, 2.0); e2.appliquer([(0, [0], []), (9, [ENTREE_30], [])], lambda: 'mak1f1'); self.assertEqual(e2.fondu['n'], 15)       # un changement de carte ordinaire reste raccourci
        self.assertFalse(e2.transition_combat())

    def test_fondus_de_script_et_de_couleur_inchanges(self):
        e = etat(MO.PARTIE_COMBAT, 4.0); e.appliquer([(9, [0x1000 | 0x800 | 20], [1.0, 0.0, 0.0])], lambda: ''); self.assertEqual(e.fondu['n'], 20)
        e = etat(MO.PARTIE_CHAMP, 4.0); e.appliquer([(9, [PJ.MARQUE_FONDU_SCRIPT | 0x1000 | 60], [])], lambda: ''); self.assertEqual(e.fondu['n'], 60)

    def test_etat_enregistre_avant_la_transition(self):
        e = etat(); d = dict(e.__dict__)
        for k in ('fen_entree', 'fen_retour', 'garde_trans'): d.pop(k)
        e2 = MO.Etat.__new__(MO.Etat); e2.__setstate__(d); self.assertFalse(e2.transition_combat()); self.assertEqual(e2.garde_trans, 0)
        d['fondu'] = {k: v for k, v in d['fondu'].items() if k != 'combat'}
        e3 = MO.Etat.__new__(MO.Etat); e3.__setstate__(d); self.assertFalse(e3.transition_combat())                       # (plan de fondu sans la cle 'combat')


@unittest.skipIf(F is None, 'fenetre.py non importable ici')
class Horloge(unittest.TestCase):
    @staticmethod
    def jeu(e, vitesse_combat=1.0, marche=1.0, accel=1.0, accel_tenue=False, direction=True, menu=None, drapeaux=0x28):
        j = types.SimpleNamespace(reg={'vitesse_combat': vitesse_combat, 'vitesse_marche': marche, 'vitesse_accel': accel})
        j.moteur = types.SimpleNamespace(etat=e, msg_visible=False, menu_actif=lambda: menu, drapeaux=lambda: drapeaux, ui=types.SimpleNamespace(msg={'feed': False}))
        j.pad = lambda: MO.HAUT if direction else 0; j._tenue = lambda a: accel_tenue and a == 'accel'; j.hud = types.SimpleNamespace(croix_course=lambda: False)
        for nom in ('_horloge_combat', '_attend_joueur'): setattr(j, nom, types.MethodType(getattr(F.Jeu, nom), j))
        j.facteur = lambda: F.Jeu._facteur_vitesse(j)
        return j

    REGLAGES = list(itertools.product((0.0, 1.0, 2.0, 3.0), (1.0, 2.0, 4.0), (1.0, 1.5, 2.0), (False, True)))

    def test_cascade_a_l_horloge_du_jeu(self):
        for vc, marche, accel, tenue in self.REGLAGES:
            e = etat(MO.PARTIE_CHAMP); e.effet = {'n': 5}
            self.assertEqual(self.jeu(e, vc, marche, accel, tenue).facteur(), 1.0, 'cascade %s' % ((vc, marche, accel, tenue),))

    def test_des_la_fin_de_la_cascade_la_vitesse_de_combat_s_applique_jusqu_au_fondu_de_fin_compris(self):
        for vc, marche, accel, tenue in self.REGLAGES:
            attendu = max(1.0, vc); r = (vc, marche, accel, tenue)
            e = etat(MO.PARTIE_CHAMP); e.attente_charge = {'base': 0, 'n': 1}
            self.assertEqual(self.jeu(e, *r).facteur(), attendu, 'ecran noir apres la cascade %s' % (r,))
            e = etat(MO.PARTIE_COMBAT); e.fen_entree = 5; e.appliquer([(9, [ENTREE_30], [])], lambda: '')
            self.assertEqual(self.jeu(e, *r).facteur(), attendu, 'fondu d\'arrivee et message « X apparait » %s' % (r,))
            e = etat(MO.PARTIE_COMBAT); e.appliquer([(9, [FONDU_COMBAT], [])], lambda: ''); self.assertTrue(e.transition_combat())
            self.assertEqual(self.jeu(e, *r).facteur(), attendu, 'fondu au noir de fin de combat %s' % (r,))
            e.garde_trans = 5; e.fondu['n'] = 0
            self.assertEqual(self.jeu(e, *r).facteur(), attendu, 'images entre deux fondus, encore dans la partie combat %s' % (r,))

    def test_retour_a_la_carte_horloge_du_jeu_tant_que_le_joueur_est_verrouille(self):
        """Fondu de retour : horloge du jeu tant que le joueur est verrouille (flag 4, images 1 a 11) et entre deux fondus ; des que le verrou tombe, la marche et l'accelerateur agissent (#127)."""
        for vc, marche, accel, tenue in self.REGLAGES:
            r = (vc, marche, accel, tenue)
            e = etat(MO.PARTIE_CHAMP); e.fen_retour = 5; e.appliquer([(9, [ENTREE_30], [])], lambda: ''); self.assertTrue(e.transition_combat())
            self.assertEqual(self.jeu(e, *r, drapeaux=0x2d).facteur(), 1.0, 'fondu de retour, joueur verrouille %s' % (r,))
            attendu = max(0.25, min(8.0, marche * (accel if tenue else 1.0)))
            self.assertEqual(self.jeu(e, *r, drapeaux=0x29).facteur(), attendu, 'fondu de retour, joueur libre %s' % (r,))
            e.fondu['n'] = 0; e.garde_trans = 4
            self.assertEqual(self.jeu(e, *r, drapeaux=0x1).facteur(), 1.0, 'entre deux fondus sur la carte %s' % (r,))

    def test_les_tours_du_combat_continuent_d_accelerer(self):
        for vc in (0.0, 1.0, 2.0, 3.0):
            for marche, accel, tenue in ((1.0, 1.0, False), (4.0, 2.0, True)):
                self.assertEqual(self.jeu(etat(MO.PARTIE_COMBAT), vc, marche, accel, tenue).facteur(), max(1.0, vc))                     # hors transition : la vitesse de combat s'applique
                self.assertEqual(self.jeu(etat(MO.PARTIE_COMBAT), vc, marche, accel, tenue, menu=13).facteur(), max(1.0, vc))           # (les attentes du joueur aussi : les monstres gardent leur allure)

    def test_la_marche_garde_ses_reglages_hors_transition(self):
        self.assertEqual(self.jeu(etat(MO.PARTIE_CHAMP), 3.0, 2.0, 1.5, True).facteur(), 3.0)
        self.assertEqual(self.jeu(etat(MO.PARTIE_CHAMP), 3.0, 4.0, 2.0, True).facteur(), 8.0)

    def test_le_pas_qui_declenche_la_cascade_arrete_le_rattrapage(self):
        """Marche acceleree (jusqu'a 8 pas par image) : quand un des pas leve l'effet de debut de combat, les pas restants de l'image n'ont pas a raccourcir la cascade : le rattrapage s'arrete (True = on continue)."""
        e = etat(MO.PARTIE_CHAMP); appels = []
        j = types.SimpleNamespace(moteur=types.SimpleNamespace(etat=e), _pas=lambda muet=False: appels.append(muet))
        self.assertTrue(F.Jeu._pas_terrain(j)); self.assertTrue(F.Jeu._faire_pas_combat(types.SimpleNamespace(moteur=j.moteur, _t_pas_reel=0.0, _attend_joueur=lambda: False, _pas=j._pas)))
        def lever(muet=False): e.effet = {'n': 0}
        j._pas = lever; self.assertFalse(F.Jeu._pas_terrain(j))                                       # la cascade vient de commencer pendant ce pas : stop
        self.assertTrue(F.Jeu._pas_terrain(j))                                                         # (deja en transition : on continue normalement)
        e.effet = None
        jc = types.SimpleNamespace(moteur=types.SimpleNamespace(etat=e), _t_pas_reel=0.0, _attend_joueur=lambda: False, _pas=lever)
        self.assertFalse(F.Jeu._faire_pas_combat(jc))                                                  # idem pendant un combat accelere (fondu de sortie)


@unittest.skipUnless(APK and SAVES and F is not None, 'moteur reel : DQ_APK=<dossier des APK patches> DQ_SAVES=<dossier des sauvegardes>')
class MoteurReel(unittest.TestCase):
    """Rejoue de vraies rencontres (carte du monde, rencontre forcee, attaque jusqu'a la victoire) avec « Vitesse de transition » x1, x2 et x4 : durees en images du moteur ; temps reel simule avec la vraie fonction
    Jeu._facteur_vitesse pour toutes les combinaisons de reglages (vitesse de combat x marche x accelerateur x touche tenue)."""
    @classmethod
    def setUpClass(cls):
        cls.reglages = Horloge.REGLAGES
        cls.parcours = {vf: cls.rejouer(vf) for vf in (1.0, 2.0, 4.0)}

    @classmethod
    def rejouer(cls, vitesse_fondu):
        MO.Etat.vitesse_fondu = vitesse_fondu
        mo = MO.Moteur(APK, SAVES, tempfile.mkdtemp(prefix='sv_trans_'))
        for _ in range(3): mo.step(0, 0)
        mo.charger_sauvegarde(4)
        for i in range(100): mo.step(0, 0x10 if i % 10 == 0 else 0)
        if mo.etat.partie != MO.PARTIE_CHAMP:
            mo.demarrer_champ()
            for i in range(120): mo.step(0, 0)
        c = mo.core
        c.call(mo.E('_ZN7Encount12forceEncountEv'), c.call(mo.E('_ZN7Encount12getSingletonEv'), label='enc'), label='force')
        pas = []; paquets9 = []                                                          # une entree par pas du moteur (etat APRES le pas) : image, partie, cascade, ecran noir, plan de devant (n, sortie ?), transition ?, facteurs par reglage
        att = 0; rel = None; fin = None; vu_combat = False
        for i in range(6000):
            p = d = 0
            if rel is not None: mo.envoyer_menu(rel, 1, -1, 0); rel = None
            port = mo.menu_actif()
            if mo.etat.partie == MO.PARTIE_COMBAT and port is not None and not mo.msg_visible:
                att += 1
                if att % 4 == 0: mo.envoyer_menu(port, 1, -1, 0x10); rel = port
            elif mo.etat.partie == MO.PARTIE_COMBAT and mo.msg_visible and mo.etat_message()[1] in (3, 5):
                att += 1
                if att > 100 and att % 4 == 0: p = d = MO.A
            else: att = 0
            if not vu_combat: p = [0x4, 0x8][(i // 20) % 2]; d = 0                    # (marche : la rencontre forcee se declenche en marchant)
            prec = mo.etat.partie; pq = mo.step(p, d); mo.ui.degats = []
            for t, a, f in pq:
                if t == 9: paquets9.append((mo.images, a[0] & 0x7ff, bool(a[0] & 0x1000), bool(a[0] & 0x4000)))
            if mo.etat.partie == MO.PARTIE_COMBAT: vu_combat = True
            e = mo.etat
            jeux = [Horloge.jeu(e, vc, marche, accel, tenue, menu=mo.menu_actif(), drapeaux=mo.drapeaux()) for vc, marche, accel, tenue in cls.reglages]
            pas.append(dict(im=mo.images, partie=e.partie, effet=e.effet is not None, attente=e.attente_charge is not None, fn=e.fondu['n'], fsortie=e.fondu['fin'] >= 1.0, trans=e.transition_combat(), verrou=bool(mo.drapeaux() & MO.DRAPEAU_JOUEUR_VERROUILLE), garde=e.garde_trans,
                            facteurs=[j.facteur() for j in jeux]))
            if vu_combat and prec == MO.PARTIE_COMBAT and e.partie != MO.PARTIE_COMBAT: fin = mo.images
            if fin and mo.images > fin + 90: break
        assert fin is not None, 'le combat ne s\'est pas termine'
        MO.Etat.vitesse_fondu = 1.0
        return dict(pas=pas, paquets9=paquets9)

    def tearDown(self): MO.Etat.vitesse_fondu = 1.0

    @staticmethod
    def suites(pas, cond):
        """Suites d'images consecutives qui verifient `cond` : [(indice du premier pas, nombre de pas)]."""
        out = []; deb = None
        for k, x in enumerate(pas):
            if cond(x) and deb is None: deb = k
            if not cond(x) and deb is not None: out.append((deb, k - deb)); deb = None
        if deb is not None: out.append((deb, len(pas) - deb))
        return out

    def test_la_cascade_dure_57_images_divisees_par_la_vitesse_de_transition(self):
        for vf, par in self.parcours.items():
            casc = self.suites(par['pas'], lambda x: x['effet']); self.assertEqual(len(casc), 1, 'x%g : une cascade par combat (%r)' % (vf, casc))
            self.assertEqual(casc[0][1], PJ.duree_fondu(MO.EFFET_COMBAT_IMAGES, vf), 'Vitesse de transition x%g' % vf)

    def test_les_fondus_de_fin_de_combat_et_de_retour_suivent_la_vitesse_de_transition(self):
        """Fondu au noir de fin (dans la partie combat) : le moteur le demande en 30 images ; Etat le rejoue en 30 / facteur."""
        for vf, par in self.parcours.items():
            d = PJ.duree_fondu(30, vf); self.assertIn(30, [x[1] for x in par['paquets9']])
            fins = self.suites(par['pas'], lambda x: x['partie'] == MO.PARTIE_COMBAT and x['fsortie'] and x['fn'] >= 1)
            self.assertTrue(fins, 'x%g : fondu de fin non vu' % vf); self.assertEqual(max(n for _, n in fins), d - 1, 'fin de combat, x%g' % vf)          # (apres le pas qui le lance : d - 1 images restantes)
            retour = self.suites(par['pas'], lambda x: x['partie'] != MO.PARTIE_COMBAT and not x['effet'] and not x['attente'] and x['fn'] >= 1 and not x['fsortie'] and x['trans'])
            self.assertTrue(retour and max(n for _, n in retour) in (d - 1, d), 'retour a la carte, x%g : %r' % (vf, retour))

    def test_l_acceleration_commence_a_la_fin_de_la_cascade_et_dure_jusqu_au_fondu_de_fin_compris(self):
        for vf, par in self.parcours.items():
            pas = par['pas']; casc = self.suites(pas, lambda x: x['effet'])[0]; fin_casc = casc[0] + casc[1]
            for k in range(casc[0], fin_casc):
                for r, regl in enumerate(self.reglages): self.assertEqual(pas[k]['facteurs'][r], 1.0, 'cascade, image %d, %s' % (k, regl))
            fins = self.suites(pas, lambda x: x['partie'] == MO.PARTIE_COMBAT and x['fsortie'] and x['fn'] >= 1)
            for k, x in enumerate(pas):
                if k < fin_casc or not (x['partie'] == MO.PARTIE_COMBAT or x['attente']): continue
                for r, (vc, *_r) in enumerate(self.reglages): self.assertEqual(x['facteurs'][r], max(1.0, vc), 'vf x%g image %d (partie %#x), vitesse de combat %g' % (vf, k, x['partie'], vc))
            for deb, n in fins:                                                                  # le fondu au noir de fin : encore accelere
                for k in range(deb, deb + n):
                    for r, (vc, *_r) in enumerate(self.reglages): self.assertEqual(pas[k]['facteurs'][r], max(1.0, vc))
            self.assertTrue(any(x['attente'] and not x['effet'] for x in pas[fin_casc:fin_casc + 8]) or pas[fin_casc]['partie'] == MO.PARTIE_COMBAT)      # (la premiere image apres la cascade est deja de l'ecran noir ou du combat)

    def test_temps_reel(self):
        """Temps reel = somme des 1 / (30 x facteur) : la cascade dure (57 / vitesse de transition) / 30 s quels que soient les reglages ; le fondu de fin de combat, lui, suit la vitesse de combat ; le retour a la carte reste a l'horloge du jeu tant que le joueur est verrouille, puis suit la marche (#127)."""
        for vf, par in self.parcours.items():
            pas = par['pas']; deb, n = self.suites(pas, lambda x: x['effet'])[0]
            retour = self.suites(pas, lambda x: x['partie'] != MO.PARTIE_COMBAT and not x['effet'] and not x['attente'] and x['trans'])
            fins = self.suites(pas, lambda x: x['partie'] == MO.PARTIE_COMBAT and x['fsortie'] and x['fn'] >= 1)
            for r, (vc, marche, accel, tenue) in enumerate(self.reglages):
                self.assertAlmostEqual(sum(PAS / pas[k]['facteurs'][r] for k in range(deb, deb + n)), PJ.duree_fondu(MO.EFFET_COMBAT_IMAGES, vf) * PAS, 9, 'cascade %s x%g' % ((vc, marche, accel, tenue), vf))
                for d0, m in fins: self.assertAlmostEqual(sum(PAS / pas[k]['facteurs'][r] for k in range(d0, d0 + m)), m * PAS / max(1.0, vc), 9, 'fondu de fin %s x%g' % ((vc, marche, accel, tenue), vf))
                for d0, m in retour:
                    for k in range(d0, d0 + m):                                          # le retour a la carte : horloge du jeu tant que le joueur est verrouille ou entre deux fondus ; le reglage de marche des que le verrou tombe (#127)
                        attendu = 1.0 if pas[k]['verrou'] or pas[k]['garde'] > 0 else max(0.25, min(8.0, marche * (accel if tenue else 1.0)))
                        self.assertEqual(pas[k]['facteurs'][r], attendu, 'retour a la carte, pas %d, %s x%g' % (k, (vc, marche, accel, tenue), vf))

if __name__ == '__main__':
    unittest.main()
