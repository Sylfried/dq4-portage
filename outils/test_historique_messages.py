"""Test (sans fenetre ni moteur) de l'historique des messages : dq4_pc/historique.py (donnees pures) et le regroupement de ui_historique.py.

    python3 outils/test_historique_messages.py
    python3 outils/test_historique_messages.py --fixture FICHIER.json [CLE]    (ecrit une trentaine de messages varies pour les captures d'ecran ; CLE = partie, « 4 » par defaut = sauvegarde 2)

Verifie : nettoyage du texte, doublons, en-tete (« locuteur · lieu », libelles.py present, absent ou casse), retour en arriere au rechargement d'une sauvegarde plus ancienne, bornes de taille,
serialisation tolerante (fichier corrompu, entrees invalides, version inconnue), ecritures groupees et atomiques, coupure des lignes, touche par defaut sans conflit.
"""
import json, os, sys, tempfile, types, unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'dq4_pc'))
import pyglet
pyglet.options['shadow_window'] = False                     # (pas d'affichage necessaire : on ne dessine rien)
import historique as HI
import reglages as RG
import ui_historique as UH


def faux_libelles():
    """Module libelles.py factice : « Un soldat » (modele 17), « Une jarre » (tubo01), lieux de Bastione et de la grotte."""
    m = types.ModuleType('libelles')
    sources = {17: 'Un soldat', 1: 'Une jeune femme', 'tubo01': 'Une jarre', '012_tubo01': 'Une jarre', '015_hondana1': 'Une étagère'}
    lieux = {'caf1': 'Château de Bastione', 'mak1f1': 'Grotte', 'monde': 'Monde', 'mab1': 'Bastione'}
    m.libelle_source = lambda x: sources.get(x)
    m.libelle_lieu = lambda c: lieux.get(c)
    return m


class Horloge:
    def __init__(self): self.t = 1000.0
    def __call__(self): return self.t


def nouveau(chemin=None, horloge=None, cle='66', t=100):
    h = HI.Historique(chemin, horloge or Horloge())
    h.synchroniser(cle, t)
    return h


class TestTexte(unittest.TestCase):
    def test_nettoyer(self):
        self.assertEqual(HI.nettoyer('*: Bonjour, voyageur.\n'), ('Bonjour, voyageur.', True))
        self.assertEqual(HI.nettoyer('Texte @c1rouge@c0 et suite\r\n\n\n\nFin   \n'), ('Texte rouge et suite\n\nFin', False))
        self.assertEqual(HI.nettoyer('A\x01BC\x7f'), ('ABC', False))
        self.assertEqual(HI.nettoyer('Que faites-vous\u00a0?')[0], 'Que faites-vous\u00a0?')                   # l'espace insecable (typographie francaise) est gardee
        self.assertEqual(HI.nettoyer('   \n  '), ('', False))
        self.assertEqual(len(HI.nettoyer('x' * 5000)[0]), HI.MAX_TEXTE)

    def test_envelopper(self):
        mes = len
        self.assertEqual(HI.envelopper('un deux trois quatre', 9, mes), ['un deux', 'trois', 'quatre'])
        self.assertEqual(HI.envelopper('ligne un\nligne deux', 80, mes), ['ligne un', 'ligne deux'])        # les retours a la ligne du texte sont gardes
        self.assertEqual(HI.envelopper('a\n\nb', 80, mes), ['a', '', 'b'])
        self.assertEqual(HI.envelopper('abcdefghij', 4, mes), ['abcd', 'efgh', 'ij'])                          # mot plus large que la ligne
        self.assertEqual(HI.envelopper('', 10, mes), [''])
        self.assertEqual(HI.envelopper('Que faites-vous\u00a0? Allez', 14, mes), ['Que', 'faites-vous\u00a0?', 'Allez'])      # jamais coupee a l'espace insecable
        for t in ('Je suis sûr que vous avez tous entendu les rumeurs', 'a b c d e f g h'):
            for larg in (5, 12, 30):
                self.assertTrue(all(len(l) <= larg or ' ' not in l for l in HI.envelopper(t, larg, mes)))


class TestEnTete(unittest.TestCase):
    def e(self, genre, val, carte='caf1', texte='Bonjour.'): return HI.Entree(1, 0, 't', genre, val, carte, texte)

    def test_avec_libelles(self):
        L = faux_libelles()
        self.assertEqual(HI.en_tete(self.e('p', 17), L), 'Un soldat · Château de Bastione')
        self.assertEqual(HI.en_tete(self.e('p', 1, 'mak1f1'), L), 'Une jeune femme · Grotte')
        self.assertEqual(HI.en_tete(self.e('o', '012_tubo01', 'mab1'), L), 'Une jarre · Bastione')
        self.assertEqual(HI.en_tete(self.e('o', '015_hondana1'), L), 'Une étagère · Château de Bastione')
        self.assertEqual(HI.en_tete(self.e('n', 'Alena'), L), 'Alena')                                           # un nom donne par le moteur : seul
        self.assertEqual(HI.en_tete(self.e('g', None), L), 'Message général')
        self.assertEqual(HI.en_tete(self.e('c', None, 'btl_x'), L), 'Combat')
        self.assertEqual(HI.en_tete(self.e('f', 'Boutique'), L), 'Boutique · Château de Bastione')
        self.assertEqual(HI.en_tete(self.e('p', None), L), 'Personnage · Château de Bastione')               # personnage non identifie
        self.assertEqual(HI.en_tete(self.e('p', 17, 'monde'), L), 'Un soldat · Monde')

    def test_lieu_inconnu_omis(self):
        L = faux_libelles()
        self.assertEqual(HI.en_tete(self.e('p', 17, 'zzz'), L), 'Un soldat')
        self.assertEqual(HI.en_tete(self.e('p', 17, None), L), 'Un soldat')

    def test_sans_libelles(self):
        self.assertEqual(HI.en_tete(self.e('p', 17), None), 'Personnage')                                      # module absent : mots generiques, pas de lieu
        self.assertEqual(HI.en_tete(self.e('o', 'tubo01'), None), 'Objet')
        self.assertEqual(HI.en_tete(self.e('n', 'Alena'), None), 'Alena')
        self.assertEqual(HI.en_tete(self.e('g', None), None), 'Message général')

    def test_libelles_casse(self):
        m = types.ModuleType('libelles')
        def boum(x): raise RuntimeError('casse')
        m.libelle_source = boum; m.libelle_lieu = boum
        self.assertEqual(HI.en_tete(self.e('p', 17), m), 'Personnage')
        self.assertEqual(HI.en_tete(self.e('o', 'tubo01'), types.ModuleType('vide')), 'Objet')                 # module sans les fonctions

    def test_nom_vide(self):
        self.assertEqual(HI.en_tete(self.e('n', '  ')), 'Message général')

    def test_vrai_module_s_il_existe(self):
        L = HI.libelles()
        if L is None: self.skipTest('libelles.py absent de cette branche')
        self.assertIsInstance(HI.en_tete(self.e('p', 17), L), str)


class TestAjout(unittest.TestCase):
    def test_numeros_et_ordre(self):
        h = nouveau()
        for i in range(3): h.ajouter('Message %d' % i, 'g', None, 'caf1', 200 + 600 * i)
        self.assertEqual([e.n for e in h.entrees()], [1, 2, 3])
        self.assertEqual([e.texte for e in h.entrees()], ['Message 0', 'Message 1', 'Message 2'])

    def test_doublon(self):
        h = nouveau()
        self.assertIsNotNone(h.ajouter('Bonjour.', 'p', 17, 'caf1', 200))
        self.assertIsNone(h.ajouter('Bonjour.', 'p', 17, 'caf1', 230))                                         # reaffiche a 0,5 s : ignore
        self.assertIsNone(h.ajouter('Bonjour.\n', 'p', 17, 'caf1', 200))                                      # (un retour a la ligne final n'en fait pas un autre message)
        self.assertIsNotNone(h.ajouter('Bonjour.', 'p', 17, 'caf1', 200 + HI.MARGE_T + 10))                   # reparle 2 s plus tard : nouveau message
        self.assertIsNotNone(h.ajouter('Bonjour.', 'p', 15, 'caf1', 200 + HI.MARGE_T + 12))                   # autre personnage : nouveau message
        self.assertEqual(len(h.entrees()), 3)

    def test_vide_et_sans_partie(self):
        h = HI.Historique(None)
        self.assertIsNone(h.ajouter('Texte', 'g', None, 'caf1', 5))                                            # aucune partie en cours (titre)
        h.synchroniser('66', 100)
        self.assertIsNone(h.ajouter('  \n ', 'g', None, 'caf1', 5))
        self.assertIsNone(h.ajouter('@c1@c0', 'g', None, 'caf1', 5))

    def test_anonyme(self):
        h = nouveau()
        e = h.ajouter('*: Bienvenue.', 'g', None, 'caf1', 100)
        self.assertEqual((e.genre, e.val, e.texte), ('p', None, 'Bienvenue.'))                                # « *: » sans personnage identifie : Personnage
        e = h.ajouter('*: Salut.', 'p', 17, 'caf1', 900)
        self.assertEqual((e.genre, e.val, e.texte), ('p', 17, 'Salut.'))

    def test_dernier_lieu_connu(self):
        old = HI._lib_cache[:]; HI._lib_cache[:] = [faux_libelles()]
        try:
            h = nouveau()
            h.ajouter('A', 'g', None, 'caf1', 200)
            e = h.ajouter('B', 'g', None, 'ev05', 900)                                                         # carte d'evenement : pas de lieu, on garde Bastione
            self.assertEqual(e.carte, 'caf1')
            e = h.ajouter('C', 'c', None, 'btl_pl_d', 1500, 'c')                                              # combat : la carte du combat n'est pas remplacee
            self.assertEqual(e.carte, 'btl_pl_d')
            e = h.ajouter('D', 'g', None, 'monde', 2100)
            self.assertEqual(e.carte, 'monde')
        finally: HI._lib_cache[:] = old

    def test_taille_bornee(self):
        h = nouveau()
        for i in range(HI.MAX_ENTREES + 50): h.ajouter('Message %d' % i, 'g', None, 'caf1', 200 + 200 * i)
        es = h.entrees()
        self.assertEqual(len(es), HI.MAX_ENTREES)
        self.assertEqual(es[-1].texte, 'Message %d' % (HI.MAX_ENTREES + 49))                                   # les plus anciens sortent
        self.assertEqual(es[0].n, 51)

    def test_parties_bornees(self):
        h = nouveau(cle='0')
        h.ajouter('x', 'g', None, 'caf1', 200)
        for i in range(1, 12): h.horloge.t += 10; h.parties[str(i)] = {'vu': h.horloge(), 'entrees': []}
        h._elaguer_parties()
        self.assertLessEqual(len(h.parties), HI.MAX_PARTIES)
        self.assertIn('0', h.parties)                                                                          # la partie en cours n'est jamais retiree


class TestRetourEnArriere(unittest.TestCase):
    def remplir(self):
        h = nouveau(t=100)
        for i in range(10): h.ajouter('Message %d' % i, 'g', None, 'caf1', 1000 + 1000 * i)                   # t = 1000 ... 10000
        return h

    def images(self, h, cle, t, n=HI.CONFIRMATIONS):
        for _ in range(n): h.synchroniser(cle, t)

    def test_temps_qui_avance(self):
        h = self.remplir()
        for t in range(10000, 12000, 2): h.synchroniser('66', t)
        self.assertEqual(len(h.entrees()), 10)

    def test_sauvegarde_plus_ancienne(self):
        h = self.remplir()
        h.synchroniser('66', 10100)
        self.images(h, '66', 4500)                                                                             # une sauvegarde faite a 4500 est rechargee
        self.assertEqual([e.texte for e in h.entrees()][-1], 'Message 3')
        self.assertEqual(len(h.entrees()), 4)
        h.ajouter('Apres', 'g', None, 'caf1', 4600)
        self.assertEqual(h.entrees()[-1].n, 5)                                                                 # la numerotation reprend apres la derniere entree gardee

    def test_instant_incoherent_ignore(self):
        h = self.remplir()
        h.synchroniser('66', 10100)
        h.synchroniser('66', 0); h.synchroniser('66', 0)                                                       # deux images de suite seulement (chargement en cours) : rien n'est retire
        h.synchroniser('66', 10102)
        self.assertEqual(len(h.entrees()), 10)
        self.images(h, '66', 0, HI.CONFIRMATIONS - 1); h.synchroniser('66', 10104)
        self.assertEqual(len(h.entrees()), 10)

    def test_petit_recul_ignore(self):
        h = self.remplir()
        h.synchroniser('66', 10100)
        self.images(h, '66', 10100 - HI.MARGE_T + 5, 20)
        self.assertEqual(len(h.entrees()), 10)

    def test_autre_aventure(self):
        h = self.remplir()
        h.synchroniser('66', 10100)
        self.images(h, '04', 38510)                                                                            # on charge une sauvegarde d'une autre aventure
        self.assertEqual(h.cle, '04'); self.assertEqual(h.entrees(), [])
        h.ajouter('Autre', 'g', None, 'caf1', 38600)
        self.images(h, '66', 10100)                                                                            # retour a la premiere : son historique est la, intact
        self.assertEqual(h.cle, '66'); self.assertEqual(len(h.entrees()), 10)
        self.assertEqual(len(h.parties['04']['entrees']), 1)

    def test_nouvelle_partie_meme_cle(self):
        h = self.remplir()
        h.synchroniser('66', 10100)
        self.images(h, '66', 6)                                                                                # nouvelle partie qui tire la meme cle : le temps revient a zero, l'ancien futur disparait
        self.assertEqual(h.entrees(), [])

    def test_chargement_au_demarrage(self):
        with tempfile.TemporaryDirectory() as d:
            ch = os.path.join(d, 'h.json'); h = self.remplir(); h.chemin = ch; h.enregistrer(True)
            h2 = HI.Historique(ch); h2.synchroniser('66', 5500)                                                # session suivante : la sauvegarde chargee est a 5500
            self.assertEqual([e.n for e in h2.entrees()], [1, 2, 3, 4, 5])
            h3 = HI.Historique(ch); h3.synchroniser('66', 99999)
            self.assertEqual(len(h3.entrees()), 10)


class TestFichier(unittest.TestCase):
    def test_aller_retour(self):
        with tempfile.TemporaryDirectory() as d:
            ch = os.path.join(d, 'sous', 'h.json'); h = nouveau(ch)
            h.ajouter('Voilà, «\u00a0un test\u00a0» é\nsur deux lignes', 'p', 17, 'caf1', 300)
            h.ajouter('Fouille', 'o', '015_hondana1', 'caf1', 900)
            self.assertTrue(h.enregistrer(True))
            self.assertEqual(sorted(os.listdir(os.path.dirname(ch))), ['h.json'])                              # pas de fichier temporaire laisse
            h2 = HI.Historique(ch); h2.synchroniser('66', 5000)
            self.assertEqual([e.vers_liste() for e in h2.entrees()], [e.vers_liste() for e in h.entrees()])

    def test_ecritures_groupees(self):
        with tempfile.TemporaryDirectory() as d:
            ch = os.path.join(d, 'h.json'); hor = Horloge(); h = nouveau(ch, hor)
            h.ajouter('A', 'g', None, 'caf1', 300)
            self.assertTrue(h.enregistrer())                                                                   # premiere ecriture : tout de suite
            h.ajouter('B', 'g', None, 'caf1', 900)
            self.assertFalse(h.enregistrer())                                                                  # trop tot : groupee avec la suite
            hor.t += HI.DELAI_ENREGISTREMENT - 1; self.assertFalse(h.enregistrer())
            hor.t += 2; self.assertTrue(h.enregistrer())
            self.assertFalse(h.enregistrer(True))                                                              # rien de nouveau : pas d'ecriture
            h.ajouter('C', 'g', None, 'caf1', 1500); self.assertTrue(h.enregistrer(True))                      # a la fermeture : force

    def test_fichier_corrompu(self):
        with tempfile.TemporaryDirectory() as d:
            ch = os.path.join(d, 'h.json')
            with open(ch, 'w') as f: f.write('{"version": 1, "parties": {"66": {"entre')
            h = HI.Historique(ch)
            self.assertEqual(h.parties, {}); self.assertIsNotNone(h.erreur)
            self.assertTrue(os.path.exists(ch + '.corrompu'))                                                  # mis de cote, pas perdu
            h.synchroniser('66', 10); h.ajouter('Neuf', 'g', None, 'caf1', 20)
            self.assertTrue(h.enregistrer(True)); self.assertEqual(len(HI.Historique(ch).parties['66']['entrees']), 1)

    def test_formats_inconnus(self):
        with tempfile.TemporaryDirectory() as d:
            for i, contenu in enumerate(('[]', '{"version": 99, "parties": {}}', '{"version": 1}', '{"version": 1, "parties": []}', '', 'null')):
                ch = os.path.join(d, 'h%d.json' % i)
                with open(ch, 'w') as f: f.write(contenu)
                self.assertEqual(HI.Historique(ch).parties, {}, contenu)

    def test_entrees_invalides_ignorees(self):
        bonne = [1, 100, 't', 'p', 17, 'caf1', 'Bonjour']
        mauvaises = [None, 5, 'x', [], [1, 2], [1, 100, 'z', 'p', 17, 'caf1', 'Bonjour'], [1, 100, 't', 'q', 17, 'caf1', 'Bonjour'], [1, -5, 't', 'p', 17, 'caf1', 'Bonjour'],
                     [1, 100, 't', 'p', 17, 'caf1', ''], [1, 100, 't', 'p', 17, 'caf1', 12], [True, 100, 't', 'p', 17, 'caf1', 'x'], [1, 100, 't', 'p', [1], 'caf1', 'x'], [1, 100, 't', 'p', 17, 3, 'x'],
                     [1, 100, 't', 'p', 17, 'caf1', 'Bonjour', 'en trop']]
        with tempfile.TemporaryDirectory() as d:
            ch = os.path.join(d, 'h.json')
            with open(ch, 'w') as f: json.dump({'version': 1, 'parties': {'66': {'vu': 5, 'entrees': mauvaises + [bonne]}, 'bizarre': 3, 7: {}, '5': {'entrees': 'non'}, '6': {'vu': 'hier', 'entrees': [bonne]}}}, f)
            h = HI.Historique(ch)
            self.assertEqual([e.texte for e in h.parties['66']['entrees']], ['Bonjour'])
            self.assertEqual(h.parties['6']['vu'], 0.0)
            self.assertNotIn('bizarre', h.parties); self.assertNotIn('5', h.parties)

    def test_fichier_trop_gros(self):
        with tempfile.TemporaryDirectory() as d:
            ch = os.path.join(d, 'h.json')
            with open(ch, 'w') as f: json.dump({'version': 1, 'parties': {'66': {'vu': 1, 'entrees': [[i, i, 't', 'g', None, 'caf1', 'm%d' % i] for i in range(HI.MAX_ENTREES + 100)]}}}, f)
            self.assertEqual(len(HI.Historique(ch).parties['66']['entrees']), HI.MAX_ENTREES)

    def test_ecriture_impossible(self):
        with tempfile.TemporaryDirectory() as d:
            ch = os.path.join(d, 'h.json', 'x.json'); open(os.path.join(d, 'h.json'), 'w').close()           # le « dossier » est un fichier
            h = nouveau(ch); h.ajouter('A', 'g', None, 'caf1', 300)
            self.assertFalse(h.enregistrer(True)); self.assertIsNotNone(h.erreur)                              # pas d'exception : le jeu continue

    def test_sans_chemin(self):
        h = nouveau(None); h.ajouter('A', 'g', None, 'caf1', 300); self.assertFalse(h.enregistrer(True))


class TestObjet(unittest.TestCase):
    def test_nom_objet(self):
        objets = [{'i': 0, 'uid': 0}, {'i': 9, 'uid': 1007}, {'i': 13, 'uid': 1007}, {'i': 63, 'uid': 1014}]
        noms = {0: '000_bkdana1', 9: '004_hikidashi1', 13: '005_hikidashi1b', 63: '015_hondana1'}
        self.assertEqual(HI.nom_objet(objets, noms, 1014), '015_hondana1')
        self.assertEqual(HI.nom_objet(objets, noms, 1007), '004_hikidashi1')                                   # variantes ferme / ouvert : la premiere
        self.assertIsNone(HI.nom_objet(objets, noms, 4242)); self.assertIsNone(HI.nom_objet(objets, noms, 0)); self.assertIsNone(HI.nom_objet(None, None, 1014))


class TestGroupes(unittest.TestCase):
    def test_groupes(self):
        L = faux_libelles()
        def e(n, t, genre, val, carte='caf1'): return HI.Entree(n, t, 't', genre, val, carte, 'x%d' % n)
        es = [e(1, 100, 'n', 'Roi'), e(2, 150, 'n', 'Roi'), e(3, 200, 'n', 'Roi'), e(4, 300, 'p', 17), e(5, 400, 'p', 17), e(6, 400 + HI.DELAI_GROUPE + 1, 'p', 17), e(7, 5000 + HI.DELAI_GROUPE, 'n', 'Roi')]
        self.assertEqual([[x.n for x in g] for g in UH.grouper(es, L)], [[1, 2, 3], [4, 5], [6], [7]])
        long = [e(i, 100 + i, 'n', 'Roi') for i in range(1, 15)]
        self.assertEqual([len(g) for g in UH.grouper(long, L)], [UH.MAX_GROUPE, UH.MAX_GROUPE, 2])
        self.assertEqual(UH.grouper([], L), [])

    def test_heure(self):
        self.assertEqual(UH.heure_jeu(0), '0:00:00'); self.assertEqual(UH.heure_jeu(60 * 3725), '1:02:05'); self.assertEqual(UH.heure_jeu(-5), '0:00:00')


class TestTouche(unittest.TestCase):
    def test_touche_par_defaut(self):
        reg = RG.Reglages(None)
        self.assertEqual(reg['touches']['historique'], ['H', None])
        ts = {a: [n for n in l if n] for a, l in reg['touches'].items()}
        autres = [n for a, l in ts.items() if a != 'historique' for n in l]
        self.assertNotIn('H', autres)                                                                          # pas de conflit avec une autre action
        self.assertTrue(all(n not in RG.RESERVEES for n in ts['historique']))
        self.assertEqual(reg.action_de(pyglet.window.key.H), 'historique')
        self.assertIn('historique', dict(RG.ACTIONS))

    def test_touche_non_chiffre(self):
        K = pyglet.window.key
        for n in ('H',): self.assertNotIn(getattr(K, n), (K._1, K._2, K._9, K.F11, K.ESCAPE, K.F1))


class TestPause(unittest.TestCase):
    """L'historique dans le menu Pause : entree de la racine, ouverture par la touche (page directe), retour, ligne de la page Commandes."""
    def jeu(self):
        import pause as PA
        h = HI.Historique(None); h.synchroniser('66', 100); h.ajouter('Bonjour.', 'n', 'Alena', 'caf1', 200)
        self.pauses = []
        J = types.SimpleNamespace(reg=RG.Reglages(None), historique=h, width=1280, height=720, souris=None, args=types.SimpleNamespace(cache='/inexistant'),
                                  pause_jeu=lambda oui: self.pauses.append(oui), son=types.SimpleNamespace(actif=True, ecoute=False))
        J.reg.enregistrer = lambda: None; J.regler_fondu = lambda v: None
        return J, PA.Pause(J)

    def test_ouverture_par_la_touche(self):
        K = pyglet.window.key; J, p = self.jeu()
        p.ouvrir('historique')
        self.assertTrue(p.ouvert); self.assertEqual(p.ecran, 'historique'); self.assertEqual(self.pauses, [True])        # le moteur est arrete
        self.assertEqual(len(p.hist.groupes), 1)
        self.assertTrue(p.touche(K.H, 0)); self.assertFalse(p.ouvert); self.assertEqual(self.pauses, [True, False])      # la meme touche referme
        p.ouvrir('historique'); p.touche(K.ESCAPE, 0); self.assertFalse(p.ouvert)                                         # Echap : retour = fermeture (page unique de la pile)
        p.ouvrir('historique'); p.touche(K.B, 0); self.assertTrue(p.ouvert)                                               # (B n'est « Annuler » que si c'est la touche reglee : ici B n'est pas attribuee)

    def test_entree_du_menu(self):
        K = pyglet.window.key; J, p = self.jeu()
        p.ouvrir(); e = next(x for x in p._entrees() if x['l'] == 'Historique des messages')
        e['ok'](); self.assertEqual(p.ecran, 'historique'); self.assertEqual(len(p.hist.groupes), 1)
        p.touche(K.BACKSPACE, 0); self.assertEqual(p.ecran, 'racine'); self.assertTrue(p.ouvert)                          # retour au menu Pause, pas au jeu
        self.assertEqual(p._e_historique(), [])

    def test_ligne_des_commandes(self):
        J, p = self.jeu(); p.ouvrir('commandes')
        e = next(x for x in p._entrees() if x.get('act') == 'historique')
        self.assertEqual((e['l'], e['v'][0]), ('Historique des messages', 'H'))

    def test_ni_clic_ni_molette_ne_cassent(self):
        M = pyglet.window.mouse; J, p = self.jeu(); p.ouvrir('historique')
        p.survol(100, 100); p.clic(100, 100, M.LEFT); p.glisser(100, 120); p.relache(100, 120, M.LEFT); p.molette(1); p.sortie()
        p.clic(100, 100, M.RIGHT); self.assertFalse(p.ouvert)                                                              # clic droit : retour, comme dans les autres pages


class TestContexte(unittest.TestCase):
    """Qui parle, d'apres la pile d'appels du moteur (Capteur._contexte) : priorites et cas limites, avec un faux moteur (pile et memoire simulees)."""
    def capteur(self, pile, partie=0xc, placement=2, modele=17, meuble=None, images=100, perso_ok=True, table=True):
        import struct
        c = HI.Capteur.__new__(HI.Capteur)
        c.m = types.SimpleNamespace(images=images, etat=types.SimpleNamespace(partie=partie, carte='caf1')); c.L = 0x10000000; c.perso_ok = perso_ok; c._meuble = meuble
        mem = {c.L + c.OFF_PLACEMENT: struct.pack('<i', placement)}
        if table:
            mem[c.L + c.OFF_PERSONNAGES + 8 + 8 * placement] = struct.pack('<Q', 0x5000); mem[0x5000 + 0x14] = struct.pack('<i', modele)
        else: mem[c.L + c.OFF_PERSONNAGES + 8 + 8 * placement] = struct.pack('<Q', 0)
        c.c = types.SimpleNamespace(mem=lambda a, n: mem[a][:n])
        c._pile = lambda uc, n=24: pile
        return c

    def ctx(self, c, nom=''): return c._contexte(None, nom, c.m.etat)

    SCRIPT = ['_Z9ui_MsgAddib', '_Z12cmd_message2P16CommandParameter', '_ZN10ScriptTree13recursiveTreeEv', '_ZN11ScriptGroup7executeEv', '_ZN10TownSystem7executeEv']

    def test_personnage(self):
        self.assertEqual(self.ctx(self.capteur(self.SCRIPT, placement=2, modele=17)), ('p', 17, 't'))
        self.assertEqual(self.ctx(self.capteur(self.SCRIPT, placement=12, modele=0)), ('p', 0, 't'))                    # le modele 0 est un vrai modele (jeune homme)

    def test_narration_et_cas_limites(self):
        self.assertEqual(self.ctx(self.capteur(self.SCRIPT, placement=0)), ('g', None, 't'))                           # emplacement 0 : script global du scenario
        self.assertEqual(self.ctx(self.capteur(self.SCRIPT, placement=2, table=False)), ('g', None, 't'))              # pas de personnage a cet emplacement
        self.assertEqual(self.ctx(self.capteur(self.SCRIPT, perso_ok=False)), ('g', None, 't'))                         # moteur inconnu : jamais de faux nom
        self.assertEqual(self.ctx(self.capteur(['_Z9ui_MsgAddib', '_ZN10TownSystem7executeEv'], placement=2)), ('g', None, 't'))    # hors script, l'emplacement est perime : on ne s'en sert pas
        self.assertEqual(self.ctx(self.capteur(self.SCRIPT, placement=99, table=False)), ('g', None, 't'))

    def test_nom_du_moteur_d_abord(self):
        self.assertEqual(self.ctx(self.capteur(self.SCRIPT, placement=20, modele=36), 'Roi Bastien'), ('n', 'Roi Bastien', 't'))
        self.assertEqual(self.ctx(self.capteur(['_Z9ui_MsgAddib', 'BattleMessage'], partie=0xd), 'Ragnar'), ('n', 'Ragnar', 'c'))

    def test_objet_fouille(self):
        pile = ['_Z9ui_MsgAddib', '_ZN19TownFurnitureObject15setFirstMessageEv', '_ZN19TownFurnitureObject7executeEv', '_ZN20TownFurnitureManager7executeEv']
        self.assertEqual(self.ctx(self.capteur(pile, meuble=(1014, 100))), ('o', 1014, 't'))
        self.assertEqual(self.ctx(self.capteur(pile, meuble=(1014, 100 - 601))), ('g', None, 't'))                      # numero d'objet trop ancien : pas le bon objet
        self.assertEqual(self.ctx(self.capteur(pile, meuble=None)), ('g', None, 't'))
        self.assertEqual(self.ctx(self.capteur(pile, meuble=(0, 100))), ('g', None, 't'))
        self.assertEqual(self.ctx(self.capteur(self.SCRIPT, meuble=(1014, 100), placement=2)), ('p', 17, 't'))          # un objet fouille plus tot ne vole pas la parole d'un personnage
        self.assertEqual(self.ctx(self.capteur(pile, meuble=(1014, 100), placement=2)), ('o', 1014, 't'))               # (meme avec un emplacement de script perime)

    def test_installations(self):
        for symbole, libelle in (('_ZN22MaterielMenu_SHOP_ROOT4initEv', 'Boutique'), ('_ZN23MaterielMenu_CHURCH_ROOT4initEv', 'Église'), ('_ZN17TownPlayerManager10loadChurchEv', 'Église'),
                                 ('_ZN20MaterielMenu_INN_ROOT4initEv', 'Auberge'), ('_ZN21MaterielMenu_BANK_ROOT4initEv', 'Banque'), ('_ZN18MaterielMenu_SLOT3runEv', 'Casino')):
            self.assertEqual(self.ctx(self.capteur(['_Z9ui_MsgAddib', symbole] + self.SCRIPT)), ('f', libelle, 's'), symbole)           # l'installation l'emporte sur l'emplacement perime
        self.assertEqual(self.ctx(self.capteur(['_Z9ui_MsgAddib', '_ZN16MaterielMenu_Name4initEv'] + self.SCRIPT[:1])), ('g', None, 't'))        # un menu qui n'est pas une installation connue

    def test_combat(self):
        self.assertEqual(self.ctx(self.capteur(['_Z9ui_MsgAddib', '_ZN13BattleMessage17addEncountMessageEi'], partie=0xd)), ('c', None, 'c'))
        self.assertEqual(self.ctx(self.capteur(['_Z9ui_MsgAddib', '_ZN13BattleMessage17addEncountMessageEi'], partie=0xc)), ('c', None, 'c'))   # (la pile suffit)
        self.assertEqual(self.ctx(self.capteur(self.SCRIPT, partie=0xd)), ('c', None, 'c'))


class TestDefilement(unittest.TestCase):
    """Defilement et touches de la fenetre (sans dessin : la geometrie est donnee par `vis`, le nombre de groupes visibles a la derniere image)."""
    def vue(self, n=20, vis=5):
        h = HI.Historique(None); h.synchroniser('66', 100)
        for i in range(n): h.ajouter('m%d' % i, 'n', 'Perso %d' % i, 'caf1', 200 + 5000 * i, 'c' if i % 4 == 3 else 't')
        self.appels = []
        P = types.SimpleNamespace(mode_souris=False, pos_souris=None, retour=lambda: self.appels.append('retour'), fermer=lambda: self.appels.append('fermer'),
                                  _repeter=lambda *a: self.appels.append(('repeter',) + a))
        P.J = types.SimpleNamespace(historique=h, reg=RG.Reglages(None), height=720)
        v = UH.VueHistorique(P); v.entrer(); v.vis = vis
        return v

    def test_ouverture_en_bas(self):
        v = self.vue()
        self.assertEqual((v.fin, v.sel, len(v.groupes)), (19, 19, 20))                                         # le plus recent en bas, choisi

    def test_fleches_et_pages(self):
        K = pyglet.window.key; v = self.vue()
        v.touche(K.UP); self.assertEqual((v.sel, v.fin), (18, 19))
        for _ in range(5): v.touche(K.UP)
        self.assertEqual((v.sel, v.fin), (13, 17))                                                             # la vue suit la selection quand elle sort par le haut (13 en haut des 5 visibles)
        v.touche(K.PAGEDOWN); self.assertEqual(v.sel, 17)
        v.touche(K.HOME); self.assertEqual((v.sel, v.fin), (0, 4))
        v.touche(K.UP); self.assertEqual((v.sel, v.fin), (0, 4))                                               # butee en haut
        v.touche(K.END); self.assertEqual((v.sel, v.fin), (19, 19))
        v.touche(K.DOWN); self.assertEqual((v.sel, v.fin), (19, 19))                                           # butee en bas
        self.assertIn(('repeter', K.DOWN, 'v', 1), self.appels)

    def test_molette_et_barre(self):
        v = self.vue()
        v.molette(1); self.assertEqual(v.fin, 17); self.assertLessEqual(v.sel, v.fin)                           # molette vers le haut : les plus anciens
        v.molette(-1); v.molette(-1); self.assertEqual(v.fin, 19)
        v.decaler(-100); self.assertEqual(v.fin, 4)                                                            # jamais plus haut que la premiere page pleine
        self.assertGreaterEqual(v.sel, v.fin - v.vis + 1)
        v.decaler(100); self.assertEqual(v.fin, 19)

    def test_glissement(self):
        v = self.vue(); v.P.J.height = 700
        v.drag = [300, v.fin, False]
        v.glisser(5, 301); self.assertEqual(v.fin, 19)                                                         # sous la tolerance : pas un glissement
        v.glisser(5, 300 - 160); self.assertLess(v.fin, 19)                                                    # le doigt descend : la liste descend (messages plus anciens)
        v.relache(5, 0, 1); self.assertIsNone(v.drag)

    def test_filtre_combat(self):
        K = pyglet.window.key; v = self.vue()
        v.touche(K.RIGHT); self.assertEqual(UH.FILTRES[v.filtre][0], 'Combats')
        self.assertEqual(len(v.entrees), 5); self.assertTrue(all(e.cat == 'c' for e in v.entrees))
        self.assertEqual(v.sel, len(v.groupes) - 1)
        v.touche(K.LEFT); self.assertEqual(len(v.entrees), 20)

    def test_fermeture(self):
        K = pyglet.window.key; v = self.vue()
        v.touche(K.ESCAPE); v.touche(K.BACKSPACE); self.assertEqual(self.appels.count('retour'), 2)
        v.touche(K.H); self.assertEqual(self.appels[-1], 'fermer')                                             # la touche de l'historique le ferme (et tout le menu avec)
        self.assertTrue(v.touche(K.F5))                                                                        # toute touche est consommee : rien n'arrive au jeu

    def test_liste_vide(self):
        v = self.vue(n=0); K = pyglet.window.key
        for t in (K.UP, K.DOWN, K.PAGEUP, K.PAGEDOWN, K.HOME, K.END, K.RIGHT): v.touche(t)
        v.molette(1); v.decaler(-3)
        self.assertEqual((v.groupes, v.sel, v.fin), ([], 0, 0))
        v2 = self.vue(); v2.P.J.historique = None; v2.entrer(); self.assertEqual(v2.groupes, [])               # pas d'historique du tout (jeu lance sans)


def ecrire_fixture(chemin, cle='4'):
    """Une trentaine de messages varies (noms, personnages, objets, installations, combats, lieux), pour les captures d'ecran. t < 38000 (sauvegarde 2 = 38510 ; sauvegarde 1 : cle « 66 »)."""
    L = [('g', None, 'caf1', 'Voici l\'histoire des gardes du palais d\'un petit royaume appelé Bastione.', 't'),
         ('g', None, 'caf1', 'Parmi ces gardes se trouve un courageux soldat, répondant au nom de Ragnar McRyan.', 't'),
         ('p', 34, 'caf1', 'Sa Majesté va vous faire une annonce. À présent, calmez-vous et écoutez.', 't'),
         ('n', 'Roi Bastien', 'caf1', 'Repos, soldats.', 't'), ('n', 'Roi Bastien', 'caf1', 'J\'imagine que vous savez ce dont je veux vous parler.', 't'),
         ('n', 'Roi Bastien', 'caf1', 'Je suis sûr que vous avez tous entendu les rumeurs à propos des récentes disparitions d\'enfants.', 't'),
         ('n', 'Roi Bastien', 'caf1', 'Gardes, découvrez ce qui se trame et revenez me faire un rapport. Allez, mes braves\u00a0!', 't'),
         ('p', 1, 'caf1', 'Messire, je vous en supplie\u00a0! Ramenez-moi mon enfant sain et sauf\u00a0!', 't'),
         ('p', 17, 'caf1', 'Ne vous épuisez pas, Ragnar. Si vous êtes blessé au combat, revenez vous reposer à l\'auberge.', 't'),
         ('o', '015_hondana1', 'caf1', 'Ragnar examine les étagères.\nIl ne semble y avoir aucun livre particulièrement intéressant.', 't'),
         ('o', '009_tbox01', 'caf1', 'Ragnar ouvre le coffre.\nIl y a une Potion à l\'intérieur\u00a0!', 't'),
         ('f', 'Boutique', 'mab1', 'Bienvenue\u00a0! Que puis-je pour vous\u00a0?', 's'), ('f', 'Boutique', 'mab1', 'Merci, et à bientôt\u00a0!', 's'),
         ('n', 'Alena', 'mab1', 'Hé, attendez-moi\u00a0! Je viens avec vous\u00a0!', 't'),
         ('p', 4, 'mak1f1', 'Cette grotte est dangereuse, vous savez. Des monstres rôdent dans les profondeurs.', 't'),
         ('o', '012_tubo01', 'mak1f1', 'Ragnar fouille la jarre.\nIl a trouvé 12 pièces d\'or\u00a0!', 't'),
         ('c', None, 'btl_pl_d', 'Des glacyclones apparaissent\u00a0!', 'c'), ('c', None, 'btl_pl_d', 'Ragnar attaque\u00a0!\nLe glacyclone subit 7 points de dégâts.', 'c'),
         ('c', None, 'btl_pl_d', 'Le glacyclone est vaincu\u00a0!', 'c'), ('c', None, 'btl_pl_d', 'Ragnar gagne 38 points d\'expérience et 21 pièces d\'or.', 'c'),
         ('f', 'Église', 'mab1', 'Que la Déesse veille sur vous, mon enfant. Souhaitez-vous sauvegarder votre aventure\u00a0?', 's'),
         ('g', None, 'monde', 'Ragnar a trouvé une Herbe médicinale.', 't'), ('p', 5, 'mab1', 'On dit qu\'il y a un trésor au fond de la grotte, mais personne n\'en est jamais revenu.', 't'),
         ('o', '010_taru01', 'mab1', 'Ragnar fouille le tonneau.\nIl ne trouve rien.', 't'), ('p', None, 'mab1', 'Bonjour, voyageur\u00a0!', 't')]
    es = []; t = 400
    for i, (genre, val, carte, texte, cat) in enumerate(L):
        t += 300 if i % 5 else 1800
        es.append(HI.Entree(i + 1, t, cat, genre, val, carte, texte).vers_liste())
    with open(chemin, 'w', encoding='utf-8') as f: json.dump({'version': HI.VERSION, 'parties': {cle: {'vu': 1.0, 'entrees': es}}}, f, ensure_ascii=False)


if __name__ == '__main__':
    if '--fixture' in sys.argv:
        i = sys.argv.index('--fixture'); ecrire_fixture(sys.argv[i + 1], sys.argv[i + 2] if len(sys.argv) > i + 2 else '4'); print('ecrit', sys.argv[i + 1])
    else:
        unittest.main(verbosity=1)
