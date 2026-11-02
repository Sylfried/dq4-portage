"""Test (sans fenetre ni moteur) de l'historique : dq4_pc/historique.py (donnees pures, favoris, pages d'un message, crochet du moteur avec un faux emulateur) et ui_historique.py (onglets, touche H, etoile, defilement).

    python3 outils/test_historique_messages.py

Verifie : nettoyage du texte (le « *: » des paroles sans nom est garde), coupure des lignes, doublons, bornes de taille, mise en forme des combats, favoris (seuls conserves : fichier ecrit tout de suite,
relu a l'ouverture, retrait par l'etoile, fichier corrompu / entrees invalides / version inconnue), pages d'un message (notees quand le joueur les a lues), messages de combat jamais ranges dans les dialogues,
combats termines recus du CapteurCombat, crochet TextBuffer::cat (nom affiche ou non, combat), onglets (Dialogues, Combats : plus d'onglet Favoris), case « Favoris seulement » (clavier, souris, conservee d'un onglet a l'autre,
favoris des sessions precedentes), touche H en cycle (Dialogues -> Combats -> ferme), etoile au clavier et a la souris, defilement.
`remplir(h)` met une trentaine d'elements varies dans un Historique (captures d'ecran).
"""
import json, os, shutil, struct, sys, tempfile, types, unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'dq4_pc'))
import pyglet
pyglet.options['shadow_window'] = False                     # (pas d'affichage necessaire : on ne dessine rien)
import historique as HI
import reglages as RG
import ui_historique as UH


class Horloge:
    def __init__(self): self.t = 1000.0
    def __call__(self): return self.t


def nouveau(chemin=None, horloge=None):
    return HI.Historique(chemin, horloge or Horloge())


def combat(t=500, issue='victoire', ennemis=None, or_=21, xp=38):
    return {'t': t, 'issue': issue, 'or': or_, 'xp': xp, 'ennemis': ennemis if ennemis is not None else [{'nom': 'Gluant', 'total': 3, 'vaincus': 3}]}


class TestTexte(unittest.TestCase):
    def test_nettoyer(self):
        self.assertEqual(HI.nettoyer('*: Bonjour, voyageur.\n'), '*: Bonjour, voyageur.')                      # le « *: » est le texte du jeu : garde
        self.assertEqual(HI.nettoyer('Texte @c1rouge@c0 et suite\r\n\n\n\nFin   \n'), 'Texte rouge et suite\n\nFin')
        self.assertEqual(HI.nettoyer('A\x01BC\x7f'), 'ABC')
        self.assertEqual(HI.nettoyer('Que faites-vous ?'), 'Que faites-vous ?')                         # l'espace insecable (typographie francaise) est gardee
        self.assertEqual(HI.nettoyer('   \n  '), '')
        self.assertEqual(HI.nettoyer(None), '')
        self.assertEqual(len(HI.nettoyer('x' * 5000)), HI.MAX_TEXTE)

    def test_envelopper(self):
        mes = len
        self.assertEqual(HI.envelopper('un deux trois quatre', 9, mes), ['un deux', 'trois', 'quatre'])
        self.assertEqual(HI.envelopper('ligne un\nligne deux', 80, mes), ['ligne un', 'ligne deux'])        # les retours a la ligne du texte sont gardes
        self.assertEqual(HI.envelopper('a\n\nb', 80, mes), ['a', '', 'b'])
        self.assertEqual(HI.envelopper('abcdefghij', 4, mes), ['abcd', 'efgh', 'ij'])                          # mot plus large que la ligne
        self.assertEqual(HI.envelopper('', 10, mes), [''])
        self.assertEqual(HI.envelopper('Que faites-vous ? Allez', 14, mes), ['Que', 'faites-vous ?', 'Allez'])      # jamais coupee a l'espace insecable
        for t in ('Je suis sûr que vous avez tous entendu les rumeurs', 'a b c d e f g h'):
            for larg in (5, 12, 30):
                self.assertTrue(all(len(l) <= larg or ' ' not in l for l in HI.envelopper(t, larg, mes)))


class TestDialogues(unittest.TestCase):
    def test_avec_et_sans_nom(self):
        h = nouveau()
        a = h.ajouter('Repos, soldats.', 'Roi Bastien', 100); b = h.ajouter('*: Bonjour, voyageur !', None, 400); c = h.ajouter('Voici l\'histoire.', '   ', 800)
        self.assertEqual([(e.nom, e.texte) for e in h.dialogues], [('Roi Bastien', 'Repos, soldats.'), (None, '*: Bonjour, voyageur !'), (None, 'Voici l\'histoire.')])
        self.assertTrue(all(e.type == HI.TYPE_DIALOGUE and e.fav is None for e in (a, b, c)))
        self.assertEqual(len({a.n, b.n, c.n}), 3)                                                                 # numeros d'ordre distincts
        self.assertEqual(h.liste('dialogues'), h.dialogues); self.assertIsNot(h.liste('dialogues'), h.dialogues); self.assertEqual(h.liste('inconnu'), [])

    def test_vide_et_doublons(self):
        h = nouveau()
        self.assertIsNone(h.ajouter('   ', 'X', 1)); self.assertIsNone(h.ajouter(None, None, 1)); self.assertEqual(h.dialogues, [])
        self.assertIsNotNone(h.ajouter('Bonjour.', 'Alena', 1000))
        self.assertIsNone(h.ajouter('Bonjour.', 'Alena', 1000 + HI.MARGE_T))                                      # le moteur a reaffiche le message
        self.assertIsNotNone(h.ajouter('Bonjour.', 'Alena', 1000 + HI.MARGE_T + 1))                               # plus tard : un autre dialogue
        self.assertIsNotNone(h.ajouter('Bonjour.', 'Ragnar', 1000 + HI.MARGE_T + 2))                              # autre nom affiche : un autre dialogue
        self.assertIsNotNone(h.ajouter('Bonjour.', None, 1000 + HI.MARGE_T + 3))
        self.assertEqual(len(h.dialogues), 4)

    def test_bornes(self):
        h = nouveau()
        for i in range(HI.MAX_DIALOGUES + 25): h.ajouter('Message %d' % i, None, i * 1000)
        self.assertEqual(len(h.dialogues), HI.MAX_DIALOGUES); self.assertEqual(h.dialogues[0].texte, 'Message 25'); self.assertEqual(h.dialogues[-1].texte, 'Message %d' % (HI.MAX_DIALOGUES + 24))
        self.assertEqual(len(h.ajouter('x' * 9000, 'N' * 300, 10 ** 9).nom), 60)


class TestCombats(unittest.TestCase):
    def test_lignes(self):
        e = HI.element_de_combat(1, combat(ennemis=[{'nom': 'Gluant', 'total': 3, 'vaincus': 3}, {'nom': 'Chauve-souris', 'total': 1, 'vaincus': 1}, {'nom': 'Golem', 'total': 2, 'vaincus': 1}]))
        self.assertEqual(HI.lignes_combat(e), ['Gluant ×3', 'Chauve-souris', 'Golem : 1 vaincu sur 2', 'Or : 21\u00a0\u00a0\u00a0\u00a0\u00a0Expérience : 38'])
        e2 = HI.element_de_combat(2, combat(issue='fuite', ennemis=[{'nom': 'Golem', 'total': 4, 'vaincus': 2}]))
        self.assertEqual(HI.lignes_combat(e2), ['Golem : 2 vaincus sur 4'])                                      # pas d'or ni d'experience sans victoire
        self.assertEqual(HI.lignes_combat(HI.element_de_combat(3, combat(ennemis=[]))), ['Ennemis inconnus', 'Or : 21\u00a0\u00a0\u00a0\u00a0\u00a0Expérience : 38'])

    def test_element_de_combat(self):
        e = HI.element_de_combat(7, combat(t=1234)); self.assertEqual((e.n, e.type, e.t, e.issue, e.or_, e.xp, e.fav), (7, HI.TYPE_COMBAT, 1234, 'victoire', 21, 38, None))
        for mauvais in (None, {}, {'issue': 'nul'}, combat(issue='nul'), {'t': 1, 'issue': 'victoire', 'or': 1, 'xp': 1}, combat(ennemis=[{'nom': 'X'}])): self.assertIsNone(HI.element_de_combat(1, mauvais))
        self.assertEqual(HI.element_de_combat(1, combat(or_=-5, xp=-1)).or_, 0)
        self.assertEqual(len(HI.element_de_combat(1, combat(ennemis=[{'nom': 'M%d' % i, 'total': 1, 'vaincus': 1} for i in range(30)])).ennemis), 12)

    def test_ajouter_et_bornes(self):
        h = nouveau()
        self.assertIsNone(h.ajouter_combat({'issue': 'x'})); self.assertEqual(h.combats, [])
        for i in range(HI.MAX_COMBATS + 5): h.ajouter_combat(combat(t=i))
        self.assertEqual((len(h.combats), h.combats[0].t, h.combats[-1].t), (HI.MAX_COMBATS, 5, HI.MAX_COMBATS + 4))
        self.assertEqual(h.liste('combats')[-1].t, HI.MAX_COMBATS + 4); self.assertEqual(h.dialogues, [])


class TestFavoris(unittest.TestCase):
    def setUp(self):
        self.dossier = tempfile.mkdtemp(prefix='fav_'); self.f = os.path.join(self.dossier, 'favoris.json')

    def lire(self):
        with open(self.f, encoding='utf-8') as fo: return json.load(fo)['favoris']

    def rempli(self, h):
        d = h.ajouter('Voici l\'histoire.', 'Alena', 100); h.ajouter('Autre.', None, 5000); c = h.ajouter_combat(combat(t=900)); return d, c

    def test_ecriture_immediate_et_relecture(self):
        h = nouveau(self.f); d, c = self.rempli(h)
        self.assertFalse(os.path.exists(self.f))                                                                  # rien n'est ecrit tant qu'il n'y a pas de favori
        self.assertTrue(h.basculer_favori(d)); self.assertTrue(os.path.exists(self.f))                           # ecrit tout de suite
        self.assertEqual(d.fav, 1); self.assertEqual(len(h.favoris), 1); self.assertFalse(os.path.exists(self.f + '.tmp'))
        self.assertTrue(h.basculer_favori(c)); self.assertEqual((c.fav, len(h.favoris), h.suivant), (2, 2, 3))
        h2 = nouveau(self.f)                                                                                      # nouvelle session : les dialogues et combats ont disparu, les favoris restent
        self.assertEqual((h2.dialogues, h2.combats, h2.suivant), ([], [], 3)); self.assertEqual([(e.type, e.fav) for e in h2.favoris], [('d', 1), ('c', 2)])
        self.assertEqual((h2.favoris[0].nom, h2.favoris[0].texte), ('Alena', 'Voici l\'histoire.'))
        self.assertEqual((h2.favoris[1].ennemis, h2.favoris[1].or_, h2.favoris[1].xp, h2.favoris[1].issue), ([{'nom': 'Gluant', 'total': 3, 'vaincus': 3}], 21, 38, 'victoire'))
        self.assertEqual(h2.liste('favoris'), h2.favoris)
        self.assertEqual([f.fav for f in h2.liste('dialogues', True)], [f.fav for f in h2.favoris if f.type == 'd'])          # « Favoris seulement » : les favoris du fichier, du type de la liste (aussi ceux d'une session precedente)
        self.assertEqual([f.type for f in h2.liste('combats', True)], ['c'] * len([f for f in h2.favoris if f.type == 'c'])); self.assertEqual(h2.liste('dialogues'), [])
        self.assertEqual(len({e.n for e in h2.favoris + h2.dialogues}), 2)

    def test_copie_independante(self):
        h = nouveau(self.f); d, _ = self.rempli(h); h.basculer_favori(d)
        self.assertIsNot(h.favoris[0], d); self.assertEqual(h.favoris[0].fav, 1)
        h.dialogues.clear()                                                                                       # la liste de session est vidée : le favori reste
        self.assertEqual(len(h.favoris), 1)

    def test_retrait(self):
        h = nouveau(self.f); d, c = self.rempli(h); h.basculer_favori(d); h.basculer_favori(c)
        self.assertFalse(h.basculer_favori(d))                                                                    # deuxieme appui sur l'etoile : retire
        self.assertIsNone(d.fav); self.assertEqual([e.fav for e in h.favoris], [2]); self.assertEqual(c.fav, 2)
        self.assertEqual([e['id'] for e in self.lire()], [2])
        h2 = nouveau(self.f); self.assertEqual([e.fav for e in h2.favoris], [2])

    def test_retrait_depuis_l_onglet_favoris(self):
        h = nouveau(self.f); d, _ = self.rempli(h); h.basculer_favori(d)
        copie = h.favoris[0]; self.assertFalse(h.basculer_favori(copie))                                           # « desetoiler » le favori lui-meme
        self.assertEqual(h.favoris, []); self.assertIsNone(d.fav)                                                  # l'element de la session perd son etoile aussi
        self.assertEqual(self.lire(), [])

    def test_numeros_jamais_reutilises(self):
        h = nouveau(self.f); d, c = self.rempli(h); h.basculer_favori(d); h.basculer_favori(c); h.retirer_favori(2)
        h2 = nouveau(self.f); self.assertEqual(h2.suivant, 3)
        e = h2.ajouter('Neuf.', None, 10); h2.basculer_favori(e); self.assertEqual(e.fav, 3)

    def test_sans_fichier(self):
        h = nouveau(None); d, _ = self.rempli(h)
        self.assertTrue(h.basculer_favori(d)); self.assertEqual(len(h.favoris), 1); self.assertFalse(h.basculer_favori(None))      # pas de chemin : tout reste en memoire, sans erreur
        self.assertIsNone(h.erreur)

    def test_bornes(self):
        h = nouveau(None)
        for i in range(HI.MAX_FAVORIS + 3): h.basculer_favori(h.ajouter('m%d' % i, None, i * 1000))
        self.assertEqual((len(h.favoris), h.favoris[0].texte), (HI.MAX_FAVORIS, 'm3'))

    def test_fichier_corrompu(self):
        for contenu in ('{pas du json', '[1, 2]', json.dumps({'version': 1, 'parties': {}}), json.dumps({'version': HI.VERSION, 'favoris': 'x'}), ''):
            with open(self.f, 'w', encoding='utf-8') as fo: fo.write(contenu)
            h = nouveau(self.f)
            self.assertEqual((h.favoris, h.suivant), ([], 1), contenu); self.assertTrue(os.path.exists(self.f + '.corrompu')); self.assertFalse(os.path.exists(self.f))
            os.remove(self.f + '.corrompu')

    def test_entrees_invalides_ignorees(self):
        bons = [{'k': 'd', 'id': 1, 't': 10, 'nom': 'Alena', 'texte': 'Bonjour.'}, {'k': 'c', 'id': 4, 't': 20, 'ennemis': [{'nom': 'Gluant', 'total': 2, 'vaincus': 1}], 'or': 3, 'xp': 4, 'issue': 'fuite'}]
        mauvais = [{'k': 'd', 'id': 2, 't': 10, 'texte': ''}, {'k': 'd', 'id': 'x', 't': 10, 'texte': 'a'}, {'k': 'd', 'id': 3, 't': -1, 'texte': 'a'}, {'k': 'z', 'id': 5, 't': 1},
                   {'k': 'c', 'id': 6, 't': 1, 'ennemis': [{'nom': 'X', 'total': -1, 'vaincus': 0}], 'issue': 'victoire'}, {'k': 'c', 'id': 7, 't': 1, 'ennemis': [], 'issue': 'nul'},
                   {'k': 'd', 'id': 1, 't': 99, 'texte': 'doublon d\'identifiant'}, {'k': 'd', 'id': True, 't': 1, 'texte': 'a'}, {'k': 'd', 'id': 8, 't': 1, 'nom': 5, 'texte': 'a'}, 'texte', None, 12]
        with open(self.f, 'w', encoding='utf-8') as fo: json.dump({'version': HI.VERSION, 'suivant': 2, 'favoris': mauvais[:4] + bons[:1] + mauvais[4:] + bons[1:]}, fo)
        h = nouveau(self.f)
        self.assertEqual([(e.type, e.fav) for e in h.favoris], [('d', 1), ('c', 4)])
        self.assertEqual((h.favoris[1].issue, h.favoris[1].ennemis), ('fuite', [{'nom': 'Gluant', 'total': 2, 'vaincus': 1}]))
        self.assertEqual(h.suivant, 5)                                                                            # jamais un numero deja pris
        self.assertFalse(os.path.exists(self.f + '.corrompu'))                                                    # le fichier est garde : seules les entrees invalides sont ignorees

    def test_ecritures_groupees(self):
        horloge = Horloge(); h = nouveau(self.f, horloge); d, _ = self.rempli(h); h.basculer_favori(d)
        h._sale = True; self.assertFalse(h.enregistrer())                                                         # trop tot : groupee
        horloge.t += HI.DELAI_ENREGISTREMENT + 1; self.assertTrue(h.enregistrer()); self.assertFalse(h.enregistrer(True))        # (plus rien a ecrire)
        h._sale = True; self.assertTrue(h.enregistrer(True))                                                      # la fermeture force l'ecriture

    def test_erreur_d_ecriture_sans_arret(self):
        h = nouveau(os.path.join(self.dossier, 'fichier.json', 'sous', 'x.json')); open(os.path.join(self.dossier, 'fichier.json'), 'w').close()      # un fichier a la place d'un dossier
        d = h.ajouter('Bonjour.', None, 1); self.assertTrue(h.basculer_favori(d)); self.assertIsNotNone(h.erreur); self.assertEqual(len(h.favoris), 1)


class FauxMoteur:
    """Moteur minimal pour Historique.maj : capteur (sortie, actif), etat, ui.msg['feed'], msg_visible, capteur_combat."""
    def __init__(self, partie=HI.PARTIE_VILLE):
        self.sortie = []
        self.capteur = types.SimpleNamespace(actif=True, vider=self._vider)
        self.etat = types.SimpleNamespace(partie=partie, carte='mak1f1'); self.ui = types.SimpleNamespace(msg={'feed': False}); self.msg_visible = True

    def _vider(self):
        r, self.sortie = self.sortie, []
        return r


def page(texte, t=500, cat=None, nom=None):
    return {'texte': texte, 'genre': 'n' if nom else 'g', 'val': nom, 'cat': cat or HI.CAT_TERRAIN, 'carte': 'mak1f1', 't': t}


class TestPagesMessage(unittest.TestCase):
    """Le moteur prepare toutes les pages d'un message d'un coup : l'historique ne doit noter la page suivante qu'une fois la precedente lue (curseur de fin de page eteint) ou la fenetre fermee."""

    def textes(self, h): return [e.texte for e in h.dialogues]

    def test_noms_et_sans_nom(self):
        h = nouveau(); m = FauxMoteur(); m.sortie += [page('Repos, soldats.', nom='Roi Bastien', t=100), page('*: Bonjour.', t=900)]
        h.maj(m); self.assertEqual([(e.nom, e.texte) for e in h.dialogues], [('Roi Bastien', 'Repos, soldats.'), (None, '*: Bonjour.')])

    def test_page_suivante_notee_apres_lecture(self):
        h = nouveau(); m = FauxMoteur(); m.sortie += [page('Page 1.'), page('Page 2.')]
        h.maj(m); self.assertEqual(self.textes(h), ['Page 1.'])                                                    # la page 2 n'a pas encore ete lue
        m.ui.msg['feed'] = True; h.maj(m); self.assertEqual(self.textes(h), ['Page 1.'])                           # fin de la page 1 : curseur allume
        m.ui.msg['feed'] = False; h.maj(m); self.assertEqual(self.textes(h), ['Page 1.', 'Page 2.'])               # le joueur tourne la page

    def test_trois_pages_une_par_une(self):
        h = nouveau(); m = FauxMoteur(); m.sortie += [page('A.'), page('B.'), page('C.')]
        h.maj(m); self.assertEqual(self.textes(h), ['A.'])
        for attendu in (['A.', 'B.'], ['A.', 'B.', 'C.']):
            m.ui.msg['feed'] = True; h.maj(m); m.ui.msg['feed'] = False; h.maj(m); self.assertEqual(self.textes(h), attendu)

    def test_fermeture_de_la_fenetre_libere_le_reste(self):
        h = nouveau(); m = FauxMoteur(); m.sortie += [page('A.'), page('B.')]
        h.maj(m); h.maj(m); self.assertEqual(self.textes(h), ['A.'])
        m.msg_visible = False; h.maj(m); self.assertEqual(self.textes(h), ['A.', 'B.'])

    def test_fenetre_pas_encore_ouverte_ne_libere_pas(self):
        h = nouveau(); m = FauxMoteur(); m.msg_visible = False                                                      # la fenetre s'ouvre une image apres le texte
        m.sortie += [page('A.'), page('B.')]; h.maj(m); h.maj(m); self.assertEqual(self.textes(h), ['A.'])
        m.msg_visible = True; h.maj(m); h.maj(m); self.assertEqual(self.textes(h), ['A.'])

    def test_fenetre_jamais_ouverte_finit_par_liberer(self):
        h = nouveau(); m = FauxMoteur(); m.msg_visible = False; m.sortie += [page('A.'), page('B.')]; h.maj(m)
        for _ in range(HI.ATTENTE_FENETRE + 2): h.maj(m)
        self.assertEqual(self.textes(h), ['A.', 'B.'])

    def test_nouveau_message_libere_les_pages_restantes_dans_l_ordre(self):
        h = nouveau(); m = FauxMoteur(); m.sortie += [page('A.'), page('B.')]; h.maj(m)
        m.sortie += [page('Autre.', t=900)]; h.maj(m); self.assertEqual(self.textes(h), ['A.', 'B.', 'Autre.'])

    def test_combat_jamais_retenu(self):
        h = nouveau(); m = FauxMoteur(HI.PARTIE_COMBAT)
        m.sortie += [page('Le monstre attaque !', cat=HI.CAT_COMBAT), page('Ragnar subit 3 points.', cat=HI.CAT_COMBAT)]; h.maj(m)
        self.assertEqual((h.dialogues, h.combats), ([], []))                                                       # ni dans les dialogues, ni dans les combats (ceux-ci viennent du CapteurCombat)

    def test_messages_distincts_meme_image_pas_retenus(self):
        h = nouveau(); m = FauxMoteur(); m.sortie += [page('A.'), page('B.', nom='Alena')]; h.maj(m)
        self.assertEqual(self.textes(h), ['A.', 'B.'])                                                              # noms differents : deux messages, pas deux pages

    def test_hors_jeu_rien_n_est_retenu(self):
        h = nouveau(); m = FauxMoteur(partie=0); m.sortie += [page('Titre.')]; h.maj(m); self.assertEqual(h.dialogues, [])

    def test_sans_capteur_ni_combat(self):
        h = nouveau(); h.maj(types.SimpleNamespace()); self.assertIsNone(h.erreur)                                  # (visionneuse sans moteur de messages : rien ne casse)

    def test_combats_termines_du_capteur(self):
        h = nouveau(); m = FauxMoteur(); lots = [[combat(t=1), combat(t=2, issue='fuite', ennemis=[{'nom': 'Golem', 'total': 1, 'vaincus': 0}])], [], [{'issue': 'invalide'}, combat(t=3)]]
        m.capteur_combat = types.SimpleNamespace(maj=lambda mo: lots.pop(0))
        for _ in range(3): h.maj(m)
        self.assertEqual([(c.t, c.issue) for c in h.combats], [(1, 'victoire'), (2, 'fuite'), (3, 'victoire')]); self.assertEqual(h.dialogues, [])

    def test_une_erreur_n_arrete_pas_le_jeu(self):
        h = nouveau(); m = FauxMoteur(); m.capteur_combat = types.SimpleNamespace(maj=lambda mo: 1 / 0)
        h.maj(m); h.maj(m); self.assertIsNotNone(h.erreur)


class FauxCore:
    """Emulateur factice pour Capteur._cat : registres, chaines C, memoire et noms de fonctions."""
    XREG = list(range(100, 131)); LIB_BASE = 0

    def __init__(self, chaines, memoire, noms): self.chaines, self.memoire, self.noms = chaines, memoire, noms; self.regs = {}
    def read_cstr(self, a): return self.chaines[a]
    def mem(self, a, n): return self.memoire[a][:n]
    def where(self, a): return self.noms.get(a, '?+0')


class TestCapteur(unittest.TestCase):
    """Le crochet de TextBuffer::cat : texte, nom que le jeu affiche (2e argument), combat ou terrain, heure de jeu."""

    def capteur(self, texte, nom, partie=HI.PARTIE_VILLE, pile=('Foo::bar',), temps=777):
        noms, memoire, fp = {0x1000: pile[0] + '+8'}, {0x9000 + 4: struct.pack('<2I', temps, 66)}, 0x2000
        for i, n in enumerate(pile[1:]):                                       # chaine des pointeurs de cadre
            memoire[fp] = struct.pack('<QQ', fp + 0x100, 0x1100 + i); noms[0x1100 + i] = n + '+4'; fp += 0x100
        memoire[fp] = struct.pack('<QQ', 0, 0)
        c = FauxCore({0x10: texte.encode('utf-8'), 0x20: nom.encode('utf-8')} if nom is not None else {0x10: texte.encode('utf-8')}, memoire, noms)
        regs = {c.XREG[1]: 0x10 if texte is not None else 0, c.XREG[2]: 0x20 if nom is not None else 0, c.XREG[30]: 0x1000, c.XREG[29]: 0x2000}
        cap = HI.Capteur.__new__(HI.Capteur); cap.actif = True; cap.sortie = []; cap.c = c; cap.g_game = 0x9000
        cap.m = types.SimpleNamespace(etat=types.SimpleNamespace(partie=partie, carte='caf1'))
        uc = types.SimpleNamespace(reg_read=lambda r: regs[r]); cap._cat(uc, 0, 0, None)
        return cap.vider()

    def test_nom_affiche(self):
        (r,) = self.capteur('Repos, soldats.', 'Roi Bastien')
        self.assertEqual((r['texte'], r['genre'], r['val'], r['cat'], r['carte'], r['t']), ('Repos, soldats.', 'n', 'Roi Bastien', 't', 'caf1', 777))

    def test_sans_nom(self):
        for nom in (None, '', '  '):
            (r,) = self.capteur('*: Bonjour.', nom); self.assertEqual((r['genre'], r['val'], r['cat']), ('g', None, 't'))

    def test_vide_ignore(self):
        self.assertEqual(self.capteur('   ', 'Alena'), [])

    def test_combat_par_la_partie_ou_la_pile(self):
        self.assertEqual(self.capteur('Le gluant attaque !', None, partie=HI.PARTIE_COMBAT)[0]['cat'], 'c')
        self.assertEqual(self.capteur('Texte.', None, pile=('Foo::bar', 'BattleRoot::exec', 'main'))[0]['cat'], 'c')          # message de combat lance depuis un menu de combat
        self.assertEqual(self.capteur('Texte.', None, pile=('Foo::bar', 'Scene::exec', 'main'))[0]['cat'], 't')

    def test_champ(self):
        (r,) = self.capteur('Texte.', None, partie=HI.PARTIE_CHAMP); self.assertEqual(r['carte'], 'monde')

    def test_de_bout_en_bout_dans_l_historique(self):
        h = nouveau(); m = FauxMoteur()
        m.sortie += self.capteur('Repos, soldats.', 'Roi Bastien') + self.capteur('Le gluant attaque !', None, partie=HI.PARTIE_COMBAT); h.maj(m)
        self.assertEqual([(e.nom, e.texte) for e in h.dialogues], [('Roi Bastien', 'Repos, soldats.')])


class TestTouche(unittest.TestCase):
    def test_touche_par_defaut(self):
        reg = RG.Reglages(None)
        self.assertEqual(reg['touches']['historique'], ['H', None])
        ts = {a: [n for n in l if n] for a, l in reg['touches'].items()}
        autres = [n for a, l in ts.items() if a != 'historique' for n in l]
        self.assertNotIn('H', autres)                                                                          # pas de conflit avec une autre action
        self.assertTrue(all(n not in RG.RESERVEES for n in ts['historique']))
        self.assertEqual(reg.action_de(pyglet.window.key.H), 'historique')
        self.assertEqual(dict(RG.ACTIONS)['historique'], 'Historique')


def remplir(h):
    """Une trentaine d'elements varies (dialogues avec ou sans nom affiche, combats) : captures d'ecran. Les dialogues sont dans h.dialogues, les combats dans h.combats."""
    L = [(None, 'Voici l\'histoire des gardes du palais d\'un petit royaume appelé Bastione.'), (None, 'Parmi ces gardes se trouve un courageux soldat, répondant au nom de Ragnar McRyan.'),
         ('Roi Bastien', 'Repos, soldats.'), ('Roi Bastien', 'J\'imagine que vous savez ce dont je veux vous parler.'),
         ('Roi Bastien', 'Je suis sûr que vous avez tous entendu les rumeurs à propos des récentes disparitions d\'enfants.'),
         ('Roi Bastien', 'Gardes, découvrez ce qui se trame et revenez me faire un rapport. Allez, mes braves !'),
         (None, '*: Messire, je vous en supplie ! Ramenez-moi mon enfant sain et sauf !'), (None, '*: Ne vous épuisez pas, Ragnar. Si vous êtes blessé au combat, revenez vous reposer à l\'auberge.'),
         (None, 'Ragnar examine les étagères.\nIl ne semble y avoir aucun livre particulièrement intéressant.'), (None, 'Ragnar ouvre le coffre.\nIl y a une Potion à l\'intérieur !'),
         ('Aubergiste', 'Bienvenue ! Que puis-je pour vous ?'), ('Aubergiste', 'Merci, et à bientôt !'), ('Alena', 'Hé, attendez-moi ! Je viens avec vous !'),
         (None, '*: Cette grotte est dangereuse, vous savez. Des monstres rôdent dans les profondeurs.'), (None, 'Ragnar fouille la jarre.\nIl a trouvé 12 pièces d\'or !'),
         ('Prêtre', 'Que la Déesse veille sur vous, mon enfant. Souhaitez-vous sauvegarder votre aventure ?'), (None, 'Ragnar a trouvé une Herbe médicinale.'),
         (None, '*: On dit qu\'il y a un trésor au fond de la grotte, mais personne n\'en est jamais revenu.'), (None, '*: Bonjour, voyageur !')]
    t = 400
    for i, (nom, texte) in enumerate(L): t += 300 if i % 5 else 1800; h.ajouter(texte, nom, t)
    for i, (en, g, x, issue) in enumerate([([('Gluant', 3, 3)], 21, 38, 'victoire'), ([('Chauve-souris', 2, 2), ('Gluant', 1, 1)], 14, 25, 'victoire'), ([('Golem', 2, 1)], 0, 0, 'fuite'),
                                           ([('Glacyclone', 4, 4), ('Mage-fantôme', 1, 1)], 96, 210, 'victoire'), ([('Dragon bleu', 1, 0)], 0, 0, 'defaite')]):
        h.ajouter_combat(combat(t=600 + 4000 * i, issue=issue, ennemis=[{'nom': n, 'total': a, 'vaincus': b} for n, a, b in en], or_=g, xp=x))
    for e in (h.dialogues[2], h.dialogues[10], h.combats[3]): h.basculer_favori(e)


def vue(n=20, vis=5, combats=0):
    h = nouveau(None)
    for i in range(n): h.ajouter('m%d' % i, 'Perso %d' % i if i % 2 else None, 200 + 5000 * i)
    for i in range(combats): h.ajouter_combat(combat(t=100 + i))
    appels = []
    P = types.SimpleNamespace(mode_souris=False, pos_souris=None, retour=lambda: appels.append('retour'), fermer=lambda: appels.append('fermer'), _repeter=lambda *a: appels.append(('repeter',) + a))
    P.J = types.SimpleNamespace(historique=h, reg=RG.Reglages(None), height=720)
    v = UH.VueHistorique(P); v.entrer(); v.vis = vis; v.appels = appels
    return v


class TestVue(unittest.TestCase):
    """Onglets, touche H, etoile et defilement (sans dessin : la geometrie est donnee par `vis`, le nombre d'elements visibles a la derniere image)."""

    def test_ouverture_en_bas(self):
        v = vue(); self.assertEqual((v.onglet, v.fin, v.sel, len(v.elements)), (UH.O_DIALOGUES, 19, 19, 20))        # le plus recent en bas, choisi

    def test_fleches_et_pages(self):
        K = pyglet.window.key; v = vue()
        v.touche(K.UP); self.assertEqual((v.sel, v.fin), (18, 19))
        for _ in range(5): v.touche(K.UP)
        self.assertEqual((v.sel, v.fin), (13, 17))                                                             # la vue suit la selection quand elle sort par le haut
        v.touche(K.PAGEDOWN); self.assertEqual(v.sel, 17)
        v.touche(K.HOME); self.assertEqual((v.sel, v.fin), (0, 4))
        v.touche(K.UP); self.assertEqual((v.sel, v.fin), (0, 4))                                               # butee en haut
        v.touche(K.END); self.assertEqual((v.sel, v.fin), (19, 19))
        v.touche(K.DOWN); self.assertEqual((v.sel, v.fin), (19, 19))                                           # butee en bas
        self.assertIn(('repeter', K.DOWN, 'v', 1), v.appels)

    def test_molette_et_barre(self):
        v = vue()
        v.molette(1); self.assertEqual(v.fin, 17); self.assertLessEqual(v.sel, v.fin)                           # molette vers le haut : les plus anciens
        v.molette(-1); v.molette(-1); self.assertEqual(v.fin, 19)
        v.decaler(-100); self.assertEqual(v.fin, 4)                                                            # jamais plus haut que la premiere page pleine
        self.assertGreaterEqual(v.sel, v.fin - v.vis + 1)
        v.decaler(100); self.assertEqual(v.fin, 19)

    def test_glissement(self):
        v = vue(); v.P.J.height = 700; v.drag = [300, v.fin, False]
        v.glisser(5, 301); self.assertEqual(v.fin, 19)                                                         # sous la tolerance : pas un glissement
        v.glisser(5, 300 - 160); self.assertLess(v.fin, 19)
        v.relache(5, 0, 1); self.assertIsNone(v.drag)

    def test_onglets(self):
        K = pyglet.window.key; v = vue(n=6, combats=3)
        self.assertEqual((len(v.elements), v.elements[0].type), (6, 'd'))
        self.assertEqual([n for n, _ in UH.ONGLETS], ['Dialogues', 'Combats'])                                   # plus d'onglet « Favoris » : c'est une case a cocher
        v.touche(K.RIGHT); self.assertEqual((v.onglet, len(v.elements), v.elements[0].type, v.sel), (UH.O_COMBATS, 3, 'c', 2))
        v.touche(K.RIGHT); self.assertEqual((v.onglet, len(v.elements)), (UH.O_DIALOGUES, 6))                    # retour au premier
        v.touche(K.LEFT); self.assertEqual(v.onglet, UH.O_COMBATS)

    def test_touche_h_en_cycle(self):
        K = pyglet.window.key; v = vue(n=3, combats=2)
        self.assertEqual(v.onglet, UH.O_DIALOGUES)
        self.assertTrue(v.touche(K.H)); self.assertEqual(v.onglet, UH.O_COMBATS); self.assertNotIn('fermer', v.appels)       # 2e appui : les combats
        self.assertTrue(v.touche(K.H)); self.assertEqual(v.appels[-1], 'fermer')                                              # 3e appui : ferme tout
        v.basculer_filtre(); self.assertTrue(v.touche(K.H)); self.assertEqual(v.appels.count('fermer'), 2)                      # « Favoris seulement » coche : le cycle de H ne change pas (ici sur les combats : ferme)
        v.changer_onglet(UH.O_DIALOGUES); v.touche(K.H); self.assertEqual((v.onglet, v.favoris_seuls, v.appels.count('fermer')), (UH.O_COMBATS, True, 2))

    def test_fermeture(self):
        K = pyglet.window.key; v = vue()
        v.touche(K.ESCAPE); v.touche(K.BACKSPACE); self.assertEqual(v.appels.count('retour'), 2)
        self.assertTrue(v.touche(K.F5))                                                                        # toute touche est consommee : rien n'arrive au jeu

    def test_liste_vide(self):
        v = vue(n=0); K = pyglet.window.key
        for t in (K.UP, K.DOWN, K.PAGEUP, K.PAGEDOWN, K.HOME, K.END, K.RIGHT, K.LEFT, K.RETURN): v.touche(t)
        v.molette(1); v.decaler(-3)
        self.assertEqual((v.elements, v.sel, v.fin), ([], 0, 0)); self.assertFalse(v.etoile()); self.assertIsNone(v.courant())
        v2 = vue(); v2.J.historique = None; v2.entrer(); self.assertEqual(v2.elements, [])                       # pas d'historique du tout (jeu lance sans)
        self.assertFalse(v2.etoile())

    def test_etoile_au_clavier(self):
        K = pyglet.window.key; v = vue(n=4); h = v.J.historique
        v.touche(K.UP); self.assertTrue(v.etoile() is True); self.assertEqual((v.elements[2].fav, len(h.favoris)), (1, 1))
        v.touche(K.RETURN); self.assertIsNone(v.elements[2].fav); self.assertEqual(h.favoris, [])                  # Entree : bascule
        v.touche(K.RETURN); v.touche(K.DOWN); v.touche(K.RETURN); self.assertEqual(sorted(e.fav for e in h.dialogues if e.fav), [2, 3])

    def test_etoile_a_la_souris(self):
        M = pyglet.window.mouse; v = vue(n=4); h = v.J.historique
        v.zones_etoile = [(100, 100, 120, 120, 1), (100, 200, 120, 220, 3)]
        v.clic(110, 210, M.LEFT); self.assertEqual((v.sel, h.dialogues[3].fav, h.dialogues[1].fav), (3, 1, None))
        v.clic(110, 110, M.LEFT); self.assertEqual((v.sel, h.dialogues[1].fav), (1, 2))
        v.clic(110, 210, M.LEFT); self.assertIsNone(h.dialogues[3].fav); self.assertEqual(len(h.favoris), 1)
        self.assertTrue(v.P.mode_souris)

    def test_clic_onglet_et_retour(self):
        M = pyglet.window.mouse; v = vue(n=3, combats=2)
        v.zones_onglet = [(0, 0, 10, 10, 0), (20, 0, 30, 10, 1)]
        v.clic(25, 5, M.LEFT); self.assertEqual((v.onglet, len(v.elements)), (UH.O_COMBATS, 2))
        v.clic(5, 5, M.LEFT); self.assertEqual(v.onglet, UH.O_DIALOGUES)
        v.clic(500, 500, M.RIGHT); self.assertEqual(v.appels[-1], 'retour')                                      # clic droit : retour
        v.zone_ret = (60, 0, 70, 10); v.clic(65, 5, M.LEFT); self.assertEqual(v.appels.count('retour'), 2)

    def test_filtre_favoris_seulement(self):
        """Case « Favoris seulement » : ne garde, dans l'onglet ouvert, que ses favoris ; l'etoile retire l'element de la liste filtree ; la case reste cochee quand on change d'onglet."""
        K = pyglet.window.key; v = vue(n=3, combats=2); h = v.J.historique
        self.assertFalse(v.favoris_seuls)
        v.etoile(0); v.etoile(2); v.changer_onglet(UH.O_COMBATS); v.etoile(1); v.changer_onglet(UH.O_DIALOGUES)       # deux dialogues et un combat en favori
        self.assertEqual(len(v.elements), 3)                                                                      # (case decochee : toute la session)
        self.assertTrue(v.basculer_filtre())
        self.assertEqual([(e.type, e.fav) for e in v.elements], [('d', 1), ('d', 2)]); self.assertEqual((v.sel, v.fin), (1, 1))      # les favoris de l'onglet, dans l'ordre ou ils ont ete mis
        v.changer_onglet(UH.O_COMBATS)                                                                            # le filtre est conserve d'un onglet a l'autre
        self.assertTrue(v.favoris_seuls); self.assertEqual([(e.type, e.fav) for e in v.elements], [('c', 3)])
        v.changer_onglet(UH.O_DIALOGUES); v.touche(K.RETURN)                                                       # etoile retiree : l'element disparait de la liste filtree
        self.assertEqual([e.fav for e in v.elements], [1]); self.assertEqual(v.sel, 0); self.assertEqual(len(h.favoris), 2)
        self.assertIsNone(h.dialogues[2].fav); self.assertEqual(len(v.elements), 1)                                # (et l'element de la session perd son etoile)
        v.touche(K.RETURN); self.assertEqual((v.elements, v.sel), ([], 0)); self.assertEqual([f.type for f in h.favoris], ['c'])
        v.touche(K.RETURN); self.assertFalse(v.etoile())                                                           # liste vide : rien a basculer
        self.assertFalse(v.basculer_filtre()); self.assertEqual(len(v.elements), 3)                                # case decochee : toute la session de nouveau

    def test_filtre_au_clavier_a_la_souris_et_par_la_touche_carte(self):
        K = pyglet.window.key; M = pyglet.window.mouse; v = vue(n=4)
        v.etoile(1); v.touche(K.F); self.assertTrue(v.favoris_seuls); self.assertEqual(len(v.elements), 1)       # F : coche
        v.touche(K.F); self.assertFalse(v.favoris_seuls); self.assertEqual(len(v.elements), 4)                   # F : decoche
        v.touche(K.M); self.assertTrue(v.favoris_seuls)                                                           # la touche Carte (M) fait de meme
        v.zone_filtre = (100, 100, 200, 130); v.clic(150, 115, M.LEFT); self.assertFalse(v.favoris_seuls)         # clic sur la case : decoche
        v.clic(150, 115, M.LEFT); self.assertTrue(v.favoris_seuls); self.assertEqual(len(v.elements), 1); self.assertTrue(v.P.mode_souris)
        v.clic(300, 115, M.LEFT); self.assertTrue(v.favoris_seuls)                                                # (a cote de la case : rien)
        self.assertTrue(v.touche(K.F))                                                                             # (la touche est consommee : rien n'arrive au jeu)

    def test_filtre_garde_l_element_choisi_et_defile(self):
        K = pyglet.window.key; v = vue(n=30, vis=5)
        for i in (3, 10, 11, 12, 20, 25, 26): v.etoile(i)
        v.aller(11); v.touche(K.F)
        self.assertEqual(len(v.elements), 7); self.assertEqual(v.courant().texte, 'm11')                         # l'element choisi, s'il est un favori, reste choisi
        v.touche(K.HOME); self.assertEqual((v.sel, v.fin), (0, 4)); v.touche(K.END); self.assertEqual((v.sel, v.fin), (6, 6))
        v.molette(1); self.assertEqual(v.fin, 4); v.decaler(100); self.assertEqual(v.fin, 6)                       # molette et glissement bornes a la liste filtree
        v.touche(K.PAGEUP); self.assertEqual(v.sel, 0)
        v.touche(K.F); self.assertEqual(len(v.elements), 30)                                                       # decoche : la liste complete
        v.aller(7); v.touche(K.F); self.assertEqual((v.sel, v.courant().texte), (6, 'm26'))                         # l'element choisi n'est pas un favori : on se place sur le plus recent de la liste filtree

    def test_favoris_des_sessions_precedentes(self):
        """Les favoris du fichier (sessions precedentes) ne sont pas dans la session : seule la case « Favoris seulement » les montre, avec leur etoile."""
        d = tempfile.mkdtemp(prefix='fav_'); self.addCleanup(shutil.rmtree, d, True); f = os.path.join(d, 'fav.json'); h = nouveau(f)
        h.ajouter('Hier.', 'Alena', 100); h.ajouter_combat(combat(t=50)); h.basculer_favori(h.dialogues[0]); h.basculer_favori(h.combats[0])
        P = types.SimpleNamespace(mode_souris=False, pos_souris=None, retour=lambda: None, fermer=lambda: None, _repeter=lambda *a: None)
        P.J = types.SimpleNamespace(historique=nouveau(f), reg=RG.Reglages(None), height=720)                    # nouvelle session : lit le fichier
        v = UH.VueHistorique(P); v.entrer()
        self.assertEqual((v.elements, v.sel), ([], 0))
        v.touche(pyglet.window.key.F); self.assertEqual([(e.nom, e.texte, e.fav) for e in v.elements], [('Alena', 'Hier.', 1)])
        v.changer_onglet(UH.O_COMBATS); self.assertEqual([(e.type, e.fav) for e in v.elements], [('c', 2)])
        v.touche(pyglet.window.key.RETURN); self.assertEqual(v.elements, []); self.assertEqual([e.type for e in P.J.historique.favoris], ['d'])      # etoile retiree : le fichier suit

    def test_vide_avec_le_filtre(self):
        v = vue(n=2); self.assertIn('Aucun dialogue', UH.VIDES['dialogues']); v.basculer_filtre()
        self.assertEqual(v.elements, []); self.assertIn('Favoris seulement', UH.VIDES_FAVORIS['dialogues']); self.assertIn('Favoris seulement', UH.VIDES_FAVORIS['combats'])
        self.assertEqual(set(UH.VIDES_FAVORIS), {c for _, c in UH.ONGLETS}); self.assertEqual(set(UH.VIDES), {c for _, c in UH.ONGLETS})

    def test_rechargement_a_chaque_ouverture(self):
        v = vue(n=2); v.J.historique.ajouter('Nouveau.', None, 10 ** 6); v.entrer()
        self.assertEqual((len(v.elements), v.sel, v.fin), (3, 2, 2)); v.entrer(UH.O_COMBATS); self.assertEqual(v.onglet, UH.O_COMBATS); v.entrer(99); self.assertEqual(v.onglet, UH.O_DIALOGUES)
        v.etoile(0); v.basculer_filtre(); v.entrer(); self.assertTrue(v.favoris_seuls); self.assertEqual(len(v.elements), 1)                         # « Favoris seulement » reste coche quand on rouvre la fenetre (pas enregistre sur disque)

    def test_heure_et_onglets_suivants(self):
        self.assertEqual(UH.heure_jeu(60 * (3600 + 5 * 60 + 12)), '1:05:12'); self.assertEqual(UH.heure_jeu(-5), '0:00:00')
        self.assertEqual((UH.touche_suivante(UH.O_DIALOGUES), UH.touche_suivante(UH.O_COMBATS)), (UH.O_COMBATS, None))
        self.assertEqual((UH.onglet_suivant(1), UH.onglet_suivant(0, -1)), (0, 1))


class TestPause(unittest.TestCase):
    """L'historique dans le menu Pause : entree de la racine, ouverture par la touche (page directe), cycle de la touche H, retour, ligne de la page Commandes."""
    def jeu(self):
        import pause as PA
        h = nouveau(None); h.ajouter('Bonjour.', 'Alena', 200); h.ajouter_combat(combat())
        self.pauses = []
        J = types.SimpleNamespace(reg=RG.Reglages(None), historique=h, width=1280, height=720, souris=None, args=types.SimpleNamespace(cache='/inexistant'),
                                  pause_jeu=lambda oui: self.pauses.append(oui), son=types.SimpleNamespace(actif=True, ecoute=False))
        J.reg.enregistrer = lambda: None; J.regler_fondu = lambda v: None
        return J, PA.Pause(J)

    def test_h_ouvre_puis_combats_puis_ferme(self):
        K = pyglet.window.key; J, p = self.jeu()
        p.ouvrir('historique')
        self.assertTrue(p.ouvert); self.assertEqual((p.ecran, p.hist.onglet, self.pauses), ('historique', UH.O_DIALOGUES, [True]))      # 1er appui : les messages, le moteur est arrete
        self.assertEqual(len(p.hist.elements), 1)
        self.assertTrue(p.touche(K.H, 0)); self.assertTrue(p.ouvert); self.assertEqual((p.hist.onglet, len(p.hist.elements), p.hist.elements[0].type), (UH.O_COMBATS, 1, 'c'))      # 2e : les combats
        self.assertTrue(p.touche(K.H, 0)); self.assertFalse(p.ouvert); self.assertEqual(self.pauses, [True, False])                                                         # 3e : tout est ferme
        p.ouvrir('historique'); self.assertEqual(p.hist.onglet, UH.O_DIALOGUES)                                                        # (rouvert : de nouveau sur les messages)

    def test_echap_et_autres_touches(self):
        K = pyglet.window.key; J, p = self.jeu()
        p.ouvrir('historique'); p.touche(K.ESCAPE, 0); self.assertFalse(p.ouvert)                                  # Echap : retour = fermeture (page unique de la pile)
        p.ouvrir('historique'); p.touche(K.B, 0); self.assertTrue(p.ouvert)                                        # (B n'est « Annuler » que si c'est la touche reglee : ici B n'est pas attribuee)

    def test_entree_du_menu(self):
        K = pyglet.window.key; J, p = self.jeu()
        p.ouvrir(); e = next(x for x in p._entrees() if x['l'] == 'Historique')
        e['ok'](); self.assertEqual(p.ecran, 'historique'); self.assertEqual(len(p.hist.elements), 1)
        p.touche(K.BACKSPACE, 0); self.assertEqual(p.ecran, 'racine'); self.assertTrue(p.ouvert)                  # retour au menu Pause, pas au jeu
        self.assertEqual(p._e_historique(), [])
        e['ok'](); p.touche(K.H, 0); p.touche(K.H, 0); self.assertFalse(p.ouvert)                                  # depuis le menu : H, H ferme aussi tout le menu

    def test_ligne_des_commandes(self):
        J, p = self.jeu(); p.ouvrir('commandes')
        e = next(x for x in p._entrees() if x.get('act') == 'historique')
        self.assertEqual((e['l'], e['v'][0]), ('Historique', 'H'))

    def test_ni_clic_ni_molette_ne_cassent(self):
        M = pyglet.window.mouse; J, p = self.jeu(); p.ouvrir('historique')
        p.survol(100, 100); p.clic(100, 100, M.LEFT); p.glisser(100, 120); p.relache(100, 120, M.LEFT); p.molette(1); p.sortie()
        p.clic(100, 100, M.RIGHT); self.assertFalse(p.ouvert)                                                      # clic droit : retour, comme dans les autres pages


if __name__ == '__main__':
    unittest.main(verbosity=1)
