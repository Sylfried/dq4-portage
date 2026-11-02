"""Test de la vitesse des combats (Normal / Rapide / Tres rapide) : reglage, cycle, horloge du moteur, independance de l'accelerateur, musique et bruitages non accelerees, bouton de l'ecran de combat.
Sans fenetre ni moteur (faux objets) ; la partie « moteur reel » est facultative : DQ_APK=<dossier des APK> DQ_SAVES=<dossier des sauvegardes> la lance (rejeu d'un combat a 1, 2 et 3 pas par image).

    python3 outils/test_vitesse_combat.py       (Linux sans ecran : pyglet en mode « headless »)
"""
import json, math, os, random, re, sys, tempfile, types, unittest

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ICI, '..', 'dq4_pc'))
import reglages as RG
import vitesse_combat as VC

try:
    import pyglet
    if sys.platform.startswith('linux') and not os.environ.get('DISPLAY'): pyglet.options['headless'] = True; pyglet.options['shadow_window'] = False
    import fenetre as F
    import hud_mobile as HM
    import moteur as MO
except Exception as ex:                                                     # (pas de pyglet / moteur ici : les tests qui en ont besoin sont ignores)
    F = HM = MO = None; ERREUR_IMPORT = ex

PAS = VC.PAS_MOTEUR


def charger(contenu):
    f = os.path.join(tempfile.mkdtemp(prefix='rg_test_'), 'reglages.json')
    with open(f, 'w', encoding='utf-8') as fh: json.dump(contenu, fh)
    return RG.Reglages(f), f


class Reglage(unittest.TestCase):
    def test_defaut_normal(self):
        r = RG.Reglages(None); self.assertEqual(r['vitesse_combat'], 1.0); self.assertEqual(RG.DEFAUT['vitesse_combat'], 1.0)
        self.assertEqual(RG.VITESSES_COMBAT, (1.0, 2.0, 3.0))

    def test_libelles_jamais_x(self):
        self.assertEqual([RG.NOMS_VITESSE_COMBAT[v] for v in RG.VITESSES_COMBAT], ['Normal', 'Rapide', 'Très rapide'])
        self.assertFalse(any(re.search(r'\bx\d', n) for n in RG.NOMS_VITESSE_COMBAT.values()))

    def test_validation(self):
        for brut, attendu in ((1, 1.0), (2, 2.0), (3, 3.0), (1.0, 1.0), (2.4, 2.0), (1.5, 2.0), (2.5, 3.0), (0, 1.0), (-4, 1.0), (4, 3.0), (99, 3.0), (float('inf'), 3.0), (float('-inf'), 1.0),
                              (float('nan'), 1.0), ('2', 1.0), ('x', 1.0), (None, 1.0), (True, 1.0), (False, 1.0), ([2], 1.0), ({'a': 2}, 1.0)):
            self.assertEqual(RG.cran_combat(brut), attendu, repr(brut))
            r, _ = charger({'vitesse_combat': brut}); self.assertEqual(r['vitesse_combat'], attendu, 'fichier : %r' % (brut,))
        r, _ = charger({'son': False}); self.assertEqual(r['vitesse_combat'], 1.0)                      # absent : Normal

    def test_cycle(self):
        v = 1.0; vus = []
        for _ in range(7): v = RG.combat_suivant(v); vus.append(v)
        self.assertEqual(vus, [2.0, 3.0, 1.0, 2.0, 3.0, 1.0, 2.0])                                   # Normal -> Rapide -> Très rapide -> Normal
        self.assertEqual(RG.combat_suivant('x'), 2.0); self.assertEqual(RG.combat_suivant(None), 2.0)    # valeur invalide : lue comme Normal

    def test_enregistrement(self):
        r, f = charger({}); r['vitesse_combat'] = 3.0; r.enregistrer()
        self.assertEqual(RG.Reglages(f)['vitesse_combat'], 3.0)
        with open(f, encoding='utf-8') as fh: self.assertEqual(json.load(fh)['vitesse_combat'], 3.0)

    def test_touche_par_defaut_libre(self):
        d = RG.TOUCHES_DEF['vit_combat']; self.assertEqual(d, ['V', None])
        for a, ts in RG.TOUCHES_DEF.items():
            if a != 'vit_combat': self.assertNotIn('V', ts, a)                                      # aucun conflit avec les touches existantes
        self.assertNotIn('V', RG.RESERVEES)
        self.assertIn('vit_combat', dict(RG.ACTIONS)); self.assertEqual(dict(RG.ACTIONS)['vit_combat'], 'Touche de vitesse des combats')
        r = RG.Reglages(None); self.assertEqual(r['touches']['vit_combat'], ['V', None]); self.assertEqual(r.action_de(RG.symbole('V')), 'vit_combat')

    def test_ancien_fichier_prend_la_touche_par_defaut(self):
        r, _ = charger({'touches_v': 4, 'touches': {'carte': ['M', None]}}); self.assertEqual(r['touches']['vit_combat'], ['V', None])
        r, _ = charger({'touches_v': 4, 'touches': {'carte': ['V', None]}})                            # une autre action a deja pris V : la nouvelle action n'a pas de touche (et la sienne est gardee)
        self.assertEqual(r['touches']['vit_combat'], [None, None]); self.assertEqual(r['touches']['carte'], ['V', None])

    def test_classement_interface(self):
        self.assertNotIn('vitesse_combat', RG.CLES_INTERFACE)                                         # un reglage de jeu, pas d'interface ; la position du bouton est dans 'boutons_pos'


class Facteur(unittest.TestCase):
    def test_hors_combat_rien(self):
        for v in (1.0, 2.0, 3.0): self.assertIsNone(VC.facteur(v, False, False))

    def test_combat(self):
        self.assertEqual([VC.facteur(v, True, False) for v in (1.0, 2.0, 3.0)], [1.0, 2.0, 3.0])

    def test_attente_du_joueur_vitesse_normale(self):
        for v in (1.0, 2.0, 3.0): self.assertEqual(VC.facteur(v, True, True), 1.0)

    def test_valeurs_absurdes(self):
        self.assertEqual(VC.facteur(9, True, False), 3.0); self.assertEqual(VC.facteur(0.2, True, False), 1.0)
        for v in (None, 'x', float('nan')): self.assertEqual(VC.facteur(v, True, False), 1.0)


class Horloge(unittest.TestCase):
    @staticmethod
    def simuler(f, secondes=10.0, cout=0.0, fps=60.0, attente=None, budget=VC.BUDGET_PAS):
        """Rejoue `secondes` d'images affichees a `fps` avec un moteur factice de `cout` secondes par pas -> (nombre de pas, temps de pas maximal dans une image, nombre d'images coupees)."""
        h = [0.0]; acc = 0.0; pas = [0]; max_img = 0.0; coupes = 0
        def faire():
            pas[0] += 1; h[0] += cout
            return not (attente and attente(pas[0]))
        for _ in range(int(secondes * fps)):
            t0 = h[0]; h[0] += 0.0                                                  # (le temps d'affichage n'entre pas dans le budget des pas)
            acc, n, coupe = VC.avancer(acc, 1.0 / fps, f, faire, lambda: h[0], PAS, budget)
            max_img = max(max_img, h[0] - t0); coupes += coupe; h[0] += 1.0 / fps
        return pas[0], max_img, coupes

    def test_nombre_de_pas_par_seconde(self):
        for f in (1.0, 2.0, 3.0):
            n, _, _ = self.simuler(f); self.assertAlmostEqual(n / 10.0, 30.0 * f, delta=0.6, msg='x%g' % f)       # 30, 60, 90 pas par seconde reelle (60 Hz)

    def test_autres_cadences_d_affichage(self):
        for fps in (30.0, 75.0, 144.0, 240.0):
            for f in (1.0, 2.0, 3.0):
                n, _, _ = self.simuler(f, fps=fps); self.assertAlmostEqual(n / 10.0, 30.0 * f, delta=0.04 * 30.0 * f + 0.6, msg='x%g a %g Hz' % (f, fps))

    def test_budget_de_calcul_borne(self):
        """Pas du moteur plus couteux que ce que le PC supporte : le temps de calcul d'une image reste borne (budget + un pas), le jeu ralentit au lieu de geler l'affichage."""
        n, max_img, coupes = self.simuler(3.0, cout=0.012); self.assertAlmostEqual(n / 10.0, 90.0, delta=0.6); self.assertEqual(coupes, 0)         # pas bon marche (12 ms) : cadence complete, rien n'est coupe
        n, max_img, coupes = self.simuler(3.0, cout=0.035)                                                                                        # pas lourd (35 ms) : un seul pas par image, donc 60 pas par seconde (x2 au lieu de x3)
        self.assertLessEqual(max_img, VC.BUDGET_PAS + 0.035 + 1e-9); self.assertAlmostEqual(n / 10.0, 60.0, delta=0.6); self.assertGreater(coupes, 0)
        n, max_img, coupes = self.simuler(2.0, cout=0.035); self.assertAlmostEqual(n / 10.0, 60.0, delta=0.6)                                     # x2 demande un pas par image a 60 Hz : tient meme avec un pas lourd
        for f in (2.0, 3.0):
            for cout in (0.012, 0.02, 0.035, 0.08):
                n, max_img, _ = self.simuler(f, cout=cout); self.assertLessEqual(max_img, VC.BUDGET_PAS + cout + 1e-9, 'x%g %g s' % (f, cout)); self.assertGreaterEqual(n / 10.0, 59.4, 'x%g %g s' % (f, cout))     # jamais sous x2 par image affichee

    def test_budget_sans_effet_a_vitesse_normale(self):
        n, _, coupes = self.simuler(1.0, cout=0.05); self.assertEqual(coupes, 0); self.assertAlmostEqual(n / 10.0, 30.0, delta=0.6)      # (a x1 le budget ne s'applique pas : comme avant)

    def test_le_moteur_attend_le_joueur(self):
        """Quand un pas ouvre un menu (faire_pas renvoie False) on n'enchaine pas d'autres pas dans la meme image, et le reste d'horloge est oublie."""
        acc, n, coupe = VC.avancer(0.0, 0.05, 3.0, lambda: False, lambda: 0.0)       # 0,15 s de moteur a faire (4 pas) : un seul est fait
        self.assertEqual((n, acc, coupe), (1, 0.0, False))
        compte = [0]
        def faire(): compte[0] += 1; return compte[0] != 2                            # le 2e pas ouvre un menu
        acc, n, _ = VC.avancer(0.0, 0.05, 3.0, faire, lambda: 0.0); self.assertEqual((n, acc), (2, 0.0))

    def test_identique_a_l_ancienne_boucle(self):
        """La boucle deplacee dans VC.avancer fait exactement ce que faisait Jeu._boucle (marche acceleree comprise)."""
        def ancienne(acc, dt, f, faire, horloge, budget):
            acc += min(dt * f, 3 * PAS * max(1.0, f)); n = 0; nmax = 3 * max(1, math.ceil(f)); coupe = False; t0 = horloge()
            while acc >= PAS * 0.85 and n < nmax:
                faire(); acc -= PAS; n += 1
                if f > 1.0 and horloge() - t0 > budget: coupe = True; break
            if n == nmax or coupe: acc = 0.0
            return acc, n, coupe
        rnd = random.Random(7)
        for f in (0.25, 1.0, 1.5, 2.0, 3.0, 4.0, 8.0):
            for cout in (0.0, 0.004, 0.02):
                a1 = a2 = 0.0; h1 = [0.0]; h2 = [0.0]
                for _ in range(400):
                    dt = rnd.choice((1 / 60.0, 1 / 60.0, 1 / 30.0, 1 / 144.0, 0.1, 0.4))
                    def f1(): h1[0] += cout
                    def f2(): h2[0] += cout
                    r1 = ancienne(a1, dt, f, f1, lambda: h1[0], VC.BUDGET_PAS); r2 = VC.avancer(a2, dt, f, f2, lambda: h2[0], PAS, VC.BUDGET_PAS)
                    self.assertEqual(r1[1:], r2[1:]); self.assertAlmostEqual(r1[0], r2[0], places=12); a1, a2 = r1[0], r2[0]; h1[0] += dt; h2[0] += dt


class Sons(unittest.TestCase):
    def test_pas_de_doublon_dans_une_image(self):
        deja = set()
        pas1 = VC.sons_a_jouer([(35, 412), (37, 30)], deja); pas2 = VC.sons_a_jouer([(35, 412), (35, 402)], deja); pas3 = VC.sons_a_jouer([(35, 402), (35, 412)], deja)
        self.assertEqual(pas1, [(35, 412), (37, 30)]); self.assertEqual(pas2, [(35, 402)]); self.assertEqual(pas3, [])
        self.assertEqual(VC.sons_a_jouer([(35, 412)], set()), [(35, 412)])                       # image suivante : de nouveau joue

    def test_une_image_ne_filtre_que_les_bruitages(self):
        deja = set(); self.assertEqual(VC.sons_a_jouer([(37, 30), (37, 30), (36, 412), (36, 412)], deja), [(37, 30), (37, 30), (36, 412), (36, 412)])     # musique et arrets : intacts

    def test_depart_arret_depart(self):
        deja = set(); self.assertEqual(VC.sons_a_jouer([(35, 311), (36, 311), (35, 311)], deja), [(35, 311), (36, 311), (35, 311)])                    # un arret libere le bruitage

    def test_sans_filtre_tout_passe(self):
        evts = [(35, 412), (35, 412), (37, 5)]; self.assertEqual(VC.sons_a_jouer(evts, None), evts)

    def test_vitesse_de_lecture_et_duree_inchangees(self):
        """Une image affichee a x3 envoie plusieurs pas : le bruitage est lance une seule fois, avec la duree de son fichier (aucune notion de vitesse dans le module son) ; la musique garde son horloge reelle."""
        try:
            sys.modules.setdefault('pyglet', None)
            import son as SON
        except Exception as ex: self.skipTest('son.py non importable ici (%r)' % (ex,))
        lancees = []
        class Lecteur:
            def __init__(self): self.volume = 1.0; self.playing = False
            def queue(self, src): pass
            def play(self): self.playing = True; lancees.append(self)
            def pause(self): self.playing = False
            def delete(self): self.playing = False
        s = SON.Son('inexistant.apk', '/tmp', log=lambda *a: None)
        s.ok = True; s.ogg = True; s.media = types.SimpleNamespace(Player=Lecteur, Source=object); s.AudioFormat = lambda **kw: kw; s.AudioData = None; SON.SourceBoucle = lambda *a: None
        s.dec['SE0412'] = dict(pcm=__import__('numpy').zeros((11025, 1), 'int16'), frequence=22050, debut=0, fin=0, volume=0.5, boucle=False)       # 0,5 s
        import time
        for f in (1.0, 3.0):
            lancees.clear(); s.se.clear(); deja = set() if f > 1.0 else None
            t0 = time.time()
            for _ in range(3): s.evenements(VC.sons_a_jouer([(35, 412)], deja))                # trois pas du moteur dans la meme image affichee
            self.assertEqual(len(lancees), 1 if f > 1.0 else 3, 'x%g' % f)
            for x in s.se: self.assertAlmostEqual(x.fin - t0, 0.5 + 0.5, delta=0.1)          # duree du fichier (0,5 s) + marge de liberation : la meme a toutes les vitesses
        with open(SON.__file__, encoding='utf-8') as fh: src = fh.read()
        for mot in ('vitesse_combat', 'vitesse_marche', 'vitesse_accel', 'import vitesse_combat'): self.assertNotIn(mot, src, mot)         # le module son ne connait pas l'horloge acceleree


@unittest.skipIf(F is None, 'fenetre.py non importable ici')
class IndependanceAccelerateur(unittest.TestCase):
    @staticmethod
    def faux(partie, vitesse_combat=1.0, marche=1.0, accel=1.0, accel_tenue=False, direction=True, effet=None, attente=None, menu=None, msg=False, feed=False):
        j = types.SimpleNamespace(reg={'vitesse_combat': vitesse_combat, 'vitesse_marche': marche, 'vitesse_accel': accel})
        j.moteur = types.SimpleNamespace(etat=types.SimpleNamespace(partie=partie, effet=effet, attente_charge=attente), msg_visible=msg, menu_actif=lambda: menu, drapeaux=lambda: 0x28, ui=types.SimpleNamespace(msg={'feed': feed}))
        j.pad = lambda: MO.HAUT if direction else 0
        j._tenue = lambda a: accel_tenue and a == 'accel'
        for nom in ('_horloge_combat', '_attend_joueur'): setattr(j, nom, types.MethodType(getattr(F.Jeu, nom), j))
        j.facteur = lambda: F.Jeu._facteur_vitesse(j)
        return j

    def test_l_accelerateur_n_accelere_pas_le_combat(self):
        for v in (1.0, 2.0, 3.0):
            for marche, accel, tenue in ((1.0, 1.0, False), (4.0, 2.0, True), (4.0, 2.0, False), (1.0, 2.0, True), (3.0, 1.5, True)):
                j = self.faux(MO.PARTIE_COMBAT, v, marche, accel, tenue); self.assertEqual(j.facteur(), v, 'combat x%g, marche x%g, accelerateur x%g tenu=%s' % (v, marche, accel, tenue))      # ni cumule ni applique

    def test_hors_combat_la_marche_garde_ses_reglages(self):
        for partie in (MO.PARTIE_VILLE, MO.PARTIE_CHAMP):
            self.assertEqual(self.faux(partie, 3.0, 1.0, 1.0).facteur(), 1.0)                                   # la vitesse des combats n'agit pas sur le terrain
            self.assertEqual(self.faux(partie, 3.0, 2.0, 1.5).facteur(), 2.0)                                   # marche x2
            self.assertEqual(self.faux(partie, 1.0, 2.0, 1.5, accel_tenue=True).facteur(), 3.0)                 # marche x2 x accelerateur x1,5 : comme avant
            self.assertEqual(self.faux(partie, 1.0, 4.0, 2.0, accel_tenue=True).facteur(), 8.0)
            self.assertEqual(self.faux(partie, 3.0, 2.0, 1.5, accel_tenue=True, direction=False).facteur(), 1.0)  # (arret : vitesse normale)

    def test_effet_de_debut_et_ecran_noir_font_partie_du_combat(self):
        self.assertEqual(self.faux(MO.PARTIE_CHAMP, 3.0, 4.0, 2.0, True, effet={'n': 3}).facteur(), 3.0)       # effet qui brise l'ecran
        self.assertEqual(self.faux(MO.PARTIE_CHAMP, 2.0, 4.0, 2.0, True, attente={'base': 0, 'n': 3}).facteur(), 2.0)      # ecran noir avant la scene du combat
        self.assertEqual(self.faux(MO.PARTIE_CHAMP, 1.0, 4.0, 2.0, True, effet={'n': 3}).facteur(), 1.0)       # Normal : comme avant (marche et accelerateur n'y comptaient deja pas)

    def test_attentes_de_saisie_a_vitesse_normale(self):
        self.assertEqual(self.faux(MO.PARTIE_COMBAT, 3.0, menu=13).facteur(), 1.0)                              # menu de commandes, de cible...
        self.assertEqual(self.faux(MO.PARTIE_COMBAT, 3.0, msg=True, feed=True).facteur(), 1.0)                  # message « Manuel » qui attend une touche (curseur ▼)
        self.assertEqual(self.faux(MO.PARTIE_COMBAT, 3.0, msg=True, feed=False).facteur(), 3.0)                 # message qui defile seul : accelere
        self.assertEqual(self.faux(MO.PARTIE_COMBAT, 2.0).facteur(), 2.0)

    def test_se_changer_sans_quitter_le_combat(self):
        """Touche ou bouton : le reglage change, est enregistre et pris en compte au pas suivant ; un message bref l'annonce si le bouton n'est pas a l'ecran."""
        r = RG.Reglages(None); sauve = []; r.enregistrer = lambda: sauve.append(r['vitesse_combat'])
        toasts = []; vis = [()]
        j = types.SimpleNamespace(reg=r, hud=types.SimpleNamespace(visibles=lambda: vis[0]), toast=toasts.append)
        for attendu in (2.0, 3.0, 1.0, 2.0): F.Jeu.changer_vitesse_combat(j); self.assertEqual(r['vitesse_combat'], attendu)
        self.assertEqual(sauve, [2.0, 3.0, 1.0, 2.0]); self.assertEqual(toasts, ['Vitesse des combats : Rapide', 'Vitesse des combats : Très rapide', 'Vitesse des combats : Normal', 'Vitesse des combats : Rapide'])
        vis[0] = (HM.COMBAT,); toasts.clear(); F.Jeu.changer_vitesse_combat(j); F.Jeu.changer_vitesse_combat(j, 'bouton'); self.assertEqual(toasts, [])      # bouton a l'ecran : il montre deja la vitesse
        vis[0] = (); toasts.clear(); F.Jeu.changer_vitesse_combat(j, 'bouton'); self.assertEqual(toasts, [])


@unittest.skipIf(F is None, 'fenetre.py non importable ici')
class HorlogeDuMoteur(unittest.TestCase):
    """Tout ce que la visionneuse anime pendant un combat doit suivre les pas du moteur (moteur.images + alpha), pas l'horloge reelle : sinon, a x2 / x3, ils se desynchronisent des actions."""
    def test_animations_de_combat_sans_horloge_reelle(self):
        import inspect
        for objet in (F.Jeu._dessiner_degats, F.Jeu._tracer_fbx, F.Jeu._dessiner_effet, F.Jeu._dessiner_fondu, F.Jeu._maillages_combat, F.EC.EffetTuiles, MO.Etat.tick_fondu):
            src = inspect.getsource(objet)
            self.assertIsNone(re.search(r'time\.(time|perf_counter|monotonic)\(', src), objet.__name__)
        self.assertIn('moteur.images', inspect.getsource(F.Jeu._dessiner_degats)); self.assertIn('moteur.images', inspect.getsource(F.Jeu._tracer_fbx))

    def test_seule_horloge_reelle_de_l_interface_de_combat_est_la_fleche_de_cible(self):
        """ui_menu : la fleche de cible clignote en temps reel (BattleUpCursor, 0,7 s) : c'est une attente de saisie du joueur, qui n'est pas acceleree (la vitesse n'agit pas quand un menu a la saisie)."""
        with open(os.path.join(ICI, '..', 'dq4_pc', 'ui_menu.py'), encoding='utf-8') as fh: src = fh.read()
        self.assertEqual(sorted(set(re.findall(r'time\.(?:time|perf_counter|monotonic)\(\)', src))), ['time.monotonic()'])
        lignes = [l.strip() for l in src.splitlines() if 'time.monotonic' in l]
        self.assertEqual(len(lignes), 3)                                                                        # curseur de cible (2) et clignotement des lieux de la carte du monde (1)


@unittest.skipIf(HM is None, 'hud_mobile.py non importable ici')
class BoutonDeLEcran(unittest.TestCase):
    @staticmethod
    def faux(W=1280, H=720, boutons=True, partie=None, effet=None, attente=None, fondu=None, pause=False, pos=None, flag=0x28, carte=False):
        MOd = MO or types.SimpleNamespace(PARTIE_COMBAT=13)
        plan = lambda **k: dict(dict(a=0.0, fin=0.0, pas=0.0, n=0, col=(0, 0, 0), noir=0), **k)
        f = fondu or {}
        etat = types.SimpleNamespace(partie=MOd.PARTIE_COMBAT if partie is None else partie, effet=effet, attente_charge=attente, fondu=plan(**f.get('devant', {})), fondu_fond=plan(**f.get('fond', {})))
        J = types.SimpleNamespace(width=W, height=H, reg={'boutons': boutons, 'croix': True, 'boutons_taille': 1.0, 'croix_taille': 1.0, 'boutons_pos': pos or {}, 'boutons_aimant': True},
                                  pause=types.SimpleNamespace(ouvert=pause), carte_ouverte=carte, args=types.SimpleNamespace(cache='/inexistant'))
        J.moteur = types.SimpleNamespace(etat=etat, drapeaux=lambda: flag, taille_croix=lambda: 1)
        return J, HM.Boutons(J)

    def test_en_combat_seul_le_bouton_de_vitesse(self):
        J, b = self.faux(); self.assertEqual(b.visibles(), (HM.COMBAT,))

    def test_sur_le_terrain_pas_le_bouton_de_vitesse(self):
        J, b = self.faux(partie=12); vis = b.visibles(); self.assertNotIn(HM.COMBAT, vis); self.assertEqual(set(vis), {'carte', 'menu', 'discussion', HM.CROIX})
        J, b = self.faux(partie=14); self.assertNotIn(HM.COMBAT, b.visibles())

    def test_masque_comme_les_autres(self):
        self.assertEqual(self.faux(boutons=False)[1].visibles(), ())                                               # « Afficher cette interface » = Non
        self.assertEqual(self.faux(pause=True)[1].visibles(), ())                                                  # menu Pause ouvert

    def test_pas_pendant_l_ecran_noir_ni_les_fondus_au_noir(self):
        self.assertEqual(self.faux(attente={'base': 0, 'n': 5})[1].visibles(), ())
        self.assertEqual(self.faux(effet={'n': 5})[1].visibles(), ())
        self.assertEqual(self.faux(fondu={'devant': dict(a=0.3, pas=0.03, n=20)})[1].visibles(), ())                  # fondu au noir qui monte (fin de combat)
        self.assertEqual(self.faux(fondu={'devant': dict(a=1.0)})[1].visibles(), ())                                  # ecran noir
        self.assertEqual(self.faux(fondu={'fond': dict(a=0.5, pas=0.03, n=5)})[1].visibles(), ())                      # (plan de fond aussi)
        self.assertEqual(self.faux(fondu={'devant': dict(a=0.5, pas=-0.03, n=15)})[1].visibles(), (HM.COMBAT,))        # fondu d'entree : le bouton apparait

    def test_clic(self):
        J, b = self.faux(); x, y, w, h = b.rect(HM.COMBAT)
        self.assertEqual(b.appuyer(x + w / 2, y + h / 2, (HM.COMBAT,)), HM.COMBAT); self.assertEqual(b.relacher(x + w / 2, y + h / 2, (HM.COMBAT,)), HM.COMBAT)
        self.assertEqual(b.appuyer(x + w / 2, y + h / 2, (HM.COMBAT,)), HM.COMBAT); self.assertIsNone(b.relacher(x + w + 40, y + h / 2, (HM.COMBAT,)))     # relache ailleurs : pas de clic
        self.assertIsNone(b.sous(x + w / 2, y + h / 2, ('carte', 'menu')))                                          # pas visible : pas atteignable
        self.assertNotIn(HM.COMBAT, HM.DECL)                                                                        # ne passe rien au moteur

    def test_position_par_defaut_ne_cache_aucun_element_du_jeu(self):
        """A gauche de la colonne portrait (450 x 800 centree) des fenetres du jeu, aux formats usuels ; sans recouvrir les autres boutons montres dans l'editeur."""
        for W, H in ((1280, 720), (1920, 1080), (2560, 1080), (3440, 1440), (1366, 768), (1600, 900), (1280, 800)):
            J, b = self.faux(W, H); x, y, w, h = b.rect(HM.COMBAT); col0 = (W - 450.0 * H / 800.0) / 2.0
            self.assertGreaterEqual(x, 0); self.assertLessEqual(x + w, col0 - 4, '%dx%d : le bouton touche la colonne des fenetres du jeu' % (W, H)); self.assertTrue(0 <= y and y + h <= H)
            for n in ('carte', 'menu', 'discussion', HM.CROIX):
                a = b.rect(n); self.assertFalse(x < a[0] + a[2] and a[0] < x + w and y < a[1] + a[3] and a[1] < y + h, '%dx%d : recouvre %s' % (W, H, n))

    def test_deplacable_dans_l_editeur_et_retablissable(self):
        J, b = self.faux(); x, y, w, h = b.rect(HM.COMBAT); self.assertIn(HM.COMBAT, HM.NOMS_ED)
        self.assertEqual(b.prendre(x + 5, y + 5), HM.COMBAT); b.deplacer(x + 5 + 400, y + 5 - 100); b.poser()
        self.assertIn(HM.COMBAT, J.reg['boutons_pos']); x2, y2, _, _ = b.rect(HM.COMBAT); self.assertGreater(x2, x + 300); self.assertLess(y2, y)
        r = RG.Reglages(None); r['boutons_pos'] = dict(J.reg['boutons_pos']); r.remettre_interface(RG.CIBLE_ECRAN); self.assertEqual(r['boutons_pos'], {})        # « Rétablir cette interface » le remet en place

    def test_libelle_de_l_editeur(self):
        self.assertEqual(HM.LIBELLE[HM.COMBAT], 'Vitesse des combats')


@unittest.skipUnless(os.environ.get('DQ_APK') and os.environ.get('DQ_SAVES') and MO is not None, 'moteur reel : DQ_APK et DQ_SAVES requis')
class RejeuMoteur(unittest.TestCase):
    """Moteur reel : meme combat (memes entrees par pas du moteur) rejoue a 1, 2 et 3 pas par image affichee avec la boucle de la visionneuse (VC.avancer) : memes paquets, memes messages, meme fin ; seul le temps change."""
    PAS_MAX = int(os.environ.get('DQ_PAS_MAX') or 1100)                       # pas du moteur compares (1100 = 37 s de combat, une trentaine de secondes de test)

    def rejouer(self, f):
        sys.path.insert(0, os.environ.get('DQ_OUTILS', ICI))
        ecr = tempfile.mkdtemp(prefix='sv_vc_'); mo = MO.Moteur(os.environ['DQ_APK'], os.environ['DQ_SAVES'], ecr); mo.charger_sauvegarde(4)
        for _ in range(200): mo.step(0, 0)
        mo.imposer_defilement(2)
        dirs = [MO.GAUCHE, MO.HAUT, MO.DROITE, MO.BAS]; n = 0
        while mo.etat.partie != MO.PARTIE_COMBAT and n < 6000: d = dirs[(n // 24) % 4]; mo.step(d, d if n % 24 == 0 else 0); n += 1
        self.assertEqual(mo.etat.partie, MO.PARTIE_COMBAT)
        trace = []; etat = {'rel': None, 'att': 0, 'k': 0}
        def entree():
            p = decl = 0
            if etat['rel'] is not None: mo.envoyer_menu(etat['rel'], 1, -1, 0); etat['rel'] = None
            port = mo.menu_actif()
            if port is not None and not mo.msg_visible:
                etat['att'] += 1
                if etat['att'] % 4 == 0: mo.envoyer_menu(port, 1, -1, 0x10); etat['rel'] = port
            elif mo.msg_visible and mo.ui.msg.get('feed'):
                etat['att'] += 1
                if etat['att'] % 4 == 0: p = decl = MO.A
            else: etat['att'] = 0
            return p, decl
        def faire():
            p, decl = entree(); pq = mo.step(p, decl); etat['k'] += 1
            trace.append((etat['k'], [(t, tuple(a[:6]), tuple(round(x, 3) for x in fl[:6])) for t, a, fl in pq if t not in (22, 28, 29)], tuple(sorted(mo.ui.msg.items())), mo.etat.partie, mo.msg_visible, mo.menu_actif(), tuple(mo.ui.degats)))      # (+ nombres de degats, que la visionneuse prend puis vide a chaque pas)
            mo.ui.degats = []
            return not (mo.menu_actif() is not None or (mo.msg_visible and mo.ui.msg.get('feed')))
        h = [0.0]; acc = 0.0; images = 0
        while mo.etat.partie == MO.PARTIE_COMBAT and etat['k'] < self.PAS_MAX:
            fac = VC.facteur(f, True, mo.menu_actif() is not None or bool(mo.msg_visible and mo.ui.msg.get('feed')))
            acc, _, _ = VC.avancer(acc, 1.0 / 60.0, fac, faire, lambda: h[0]); h[0] += 1.0 / 60.0; images += 1
        return trace[:self.PAS_MAX], images

    def test_meme_combat_a_toutes_les_vitesses(self):
        ref, im1 = self.rejouer(1.0)
        for f in (2.0, 3.0):
            tr, im = self.rejouer(f); n = min(len(ref), len(tr)); self.assertGreater(n, self.PAS_MAX * 0.7)
            self.assertEqual(tr[:n], ref[:n], 'x%g : le combat n\'est pas identique' % f)                       # memes paquets (hors maillages), memes messages, meme etat, pas pour pas
            self.assertLess(im, im1, 'x%g : pas plus rapide' % f)


if __name__ == '__main__':
    unittest.main(verbosity=2)
