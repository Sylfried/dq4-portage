"""Test (sans fenetre ni moteur) de l'historique : dq4_pc/historique.py (donnees pures, favoris, pages d'un message, crochet du moteur avec un faux emulateur) et ui_historique.py (onglets, touche H, etoile, defilement).

    python3 outils/test_historique_messages.py

Verifie : nettoyage du texte (le « *: » des paroles sans nom est garde), coupure des lignes, doublons, bornes de taille, mise en forme des combats, favoris (seuls conserves : fichier ecrit tout de suite,
relu a l'ouverture, retrait par l'etoile, fichier corrompu / entrees invalides / version inconnue), pages d'un message (notees quand le joueur les a lues), messages de combat jamais ranges dans les dialogues,
combats termines recus du CapteurCombat, crochet TextBuffer::cat (nom affiche ou non, combat), onglets (Dialogues, Combats : plus d'onglet Favoris), case « Favoris seulement » (clavier, souris, conservee d'un onglet a l'autre,
favoris des sessions precedentes), touche H en cycle (Dialogues -> Combats -> ferme), etoile au clavier et a la souris, defilement ; haut / bas message par message (defilement du minimum necessaire, #48), aucun grisé sur le message choisi.
Taille unique des boites (la boite de dialogue du jeu : 1, 2 ou 3 lignes, dialogue ou combat ; une page de plus au-dela de 3 lignes).
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

    def test_point_virgule_du_patch_retire(self):
        """#139 : le « ; » des noms d'objets du patch (marque de coupure, toujours apres une espace) ne s'affiche pas dans l'historique ; l'espace qui le precede reste."""
        self.assertEqual(HI.nettoyer("Ragnar obtient l'herbe ;médicinale."), "Ragnar obtient l'herbe médicinale.")
        self.assertEqual(HI.nettoyer('Un bâton de ;cyprès et une épée de ;cuivre !\n;Fin'), 'Un bâton de cyprès et une épée de cuivre !\nFin')
        self.assertEqual(HI.nettoyer(';'), '')
        h = HI.Historique(None); h.ajouter("Il trouve l'herbe ;médicinale.", 'Mar;chand', 10)
        e = h.dialogues[-1]; self.assertEqual((e.nom, e.texte), ('Marchand', "Il trouve l'herbe médicinale."))
        f = HI.Element.depuis_dict({'k': HI.TYPE_DIALOGUE, 'id': 1, 't': 5, 'nom': None, 'texte': "l'herbe ;médicinale"}, 1)
        self.assertEqual(f.texte, "l'herbe médicinale")                                          # un favori enregistre avant la correction se relit sans « ; » (et reste reconnu)

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
         (None, '*: On dit qu\'il y a un trésor au fond de la grotte, mais personne n\'en est jamais revenu.'), (None, '*: Bonjour, voyageur !'),
         ('Roi Bastien', 'Les enfants ont disparu en une seule nuit, sans qu\'un seul garde ait rien vu. Fouillez le village, interrogez chaque habitant et n\'oubliez pas la forêt.'),
         (None, 'Ragnar a trouvé une Potion.\nRagnar a trouvé une Herbe médicinale.\nRagnar a trouvé 25 pièces d\'or.')]
    t = 400
    for i, (nom, texte) in enumerate(L): t += 300 if i % 5 else 1800; h.ajouter(texte, nom, t)
    for i, (en, g, x, issue) in enumerate([([('Gluant', 3, 3)], 21, 38, 'victoire'), ([('Chauve-souris', 2, 2), ('Gluant', 1, 1)], 14, 25, 'victoire'), ([('Golem', 2, 1)], 0, 0, 'fuite'),
                                           ([('Glacyclone', 4, 4), ('Mage-fantôme', 1, 1)], 96, 210, 'victoire'), ([('Dragon bleu', 1, 0)], 0, 0, 'defaite'),
                                           ([('Gluant', 3, 3), ('Chauve-souris', 2, 2), ('Golem', 1, 1), ('Mage-fantôme', 2, 2), ('Glacyclone', 4, 4), ('Dragon bleu', 1, 1)], 250, 480, 'victoire')]):
        h.ajouter_combat(combat(t=600 + 4000 * i, issue=issue, ennemis=[{'nom': n, 'total': a, 'vaincus': b} for n, a, b in en], or_=g, xp=x))
    for e in (h.dialogues[2], h.dialogues[10], h.combats[3]): h.basculer_favori(e)


def vue(n=20, hv=500.0, combats=0):
    h = nouveau(None)
    for i in range(n): h.ajouter('m%d' % i, 'Perso %d' % i if i % 2 else None, 200 + 5000 * i)
    for i in range(combats): h.ajouter_combat(combat(t=100 + i))
    appels = []
    P = types.SimpleNamespace(mode_souris=False, pos_souris=None, retour=lambda: appels.append('retour'), fermer=lambda: appels.append('fermer'), _repeter=lambda *a: appels.append(('repeter',) + a))
    P.J = types.SimpleNamespace(historique=h, reg=RG.Reglages(None), height=720)
    v = UH.VueHistorique(P); v.entrer(); v.appels = appels; v.hv0 = hv; poser(v)
    return v


def poser(v, hv=None):
    """Ce que dessiner() fait a chaque image, sans police ni GL : empile les elements de v (boites de 126 pixels, onglet de 32 pour un dialogue avec nom, ecarts du dessin a l'echelle 1) et met a jour la geometrie du defilement
    (hauteur du contenu, repere, element actif). A appeler apres chaque action qui change la liste ou la position."""
    if hv is not None: v.hv0 = hv
    ent = [(1, e.type == HI.TYPE_DIALOGUE and bool(e.nom)) for e in v.elements]
    boites, debuts, fins, hc = UH.disposer(ent, 126.0, 32.0, UH.ECART_ELEMENTS, UH.ECART_PAGES, UH.MARGE_LISTE)
    v._geometrie(debuts, fins, hc, v.hv0, 28.0, 1.0)
    return boites


def frappe(v, *touches):
    """Des touches, avec une image dessinee entre deux."""
    for t in touches: v.touche(t); poser(v)


class TestBoite(unittest.TestCase):
    """Taille unique des boites de l'historique : la boite de dialogue du jeu (3 lignes), que le texte fasse 1, 2 ou 3 lignes, dialogue ou combat ; au-dela de 3 lignes : une page de plus."""
    @staticmethod
    def mes(t): return 9.0 * len(t)                                            # largeur d'une chaine (unites) : 9 par caractere

    def vue_boites(self, elements, haut=900.0):
        """Boites calculees comme dessiner() les place (sans GL) : police du systeme simulee (P._et), echelle 1, fenetre de la liste de `haut` pixels. -> (vue, boite, boites du plus ancien en haut au plus recent en bas,
        chacune (element, boite, nombre de boites, haut, haut du cadre, haut de l'onglet, rangees de texte))."""
        v = vue(0); v.elements = elements; v._mise = None
        v.P._et = lambda t, taille: types.SimpleNamespace(content_width=self.mes(t) / 0.9)
        B = UH.Boite(); bs = v._mesurer(None, B, 1.0, 1.0, 20.0, haut)
        return v, B, [(i, p, nb, h, hb, hn, r) for (i, p, nb, h, hn, hb, r) in bs]

    @staticmethod
    def dialogue(n, texte, nom=None): return HI.Element(n, HI.TYPE_DIALOGUE, 0, nom=nom, texte=texte)

    def test_dimensions_du_jeu(self):
        B = UH.Boite(); self.assertEqual((B.LARG, B.HAUT, B.LIGNES, B.PAS), (452.0, 126.0, 3, 28.0)); self.assertEqual((B.ONGLET_L, B.ONGLET_H), (246.0, 32.0))
        self.assertEqual([B.base(i) for i in range(3)], [B.BASE_1, B.BASE_1 + 28.0, B.BASE_1 + 56.0])
        self.assertLess(B.base(2), B.HAUT)                                         # la 3e ligne tient dans le cadre
        self.assertGreater(B.largeur_texte(), 400)

    def test_dimensions_lues_dans_la_mise_en_page(self):
        import test_nom_dialogue as N
        B = UH.Boite.depuis(N.faux_ml()); self.assertEqual((B.LARG, B.HAUT, B.ONGLET_L, B.ONGLET_H, B.x0, B.z0, B.win), (452.0, 126.0, 246.0, 32.0, -223.0, -251.0, (0.0, 10.0, 86.0)))
        self.assertEqual((UH.Boite.depuis(None).LARG, UH.Boite.depuis(object()).HAUT), (452.0, 126.0))               # (mise en page absente ou inutilisable : valeurs mesurees)

    def test_dimensions_des_vrais_cadres(self):
        import test_nom_dialogue as N, ui_menu as UM
        l, c = os.path.join(N.CACHE, 'ui_layout.json'), os.path.join(N.CACHE, 'ui_frameData.bin')
        if not (os.path.exists(l) and os.path.exists(c)): self.skipTest('cache d\'interface absent')
        B = UH.Boite.depuis(UM.MiseEnPage(l, c)); d = UH.Boite()
        self.assertEqual((B.LARG, B.HAUT, B.ONGLET_L, B.ONGLET_H), (d.LARG, d.HAUT, d.ONGLET_L, d.ONGLET_H)); self.assertEqual(B.texte_ech, UH.TEXTE_ECH)

    def test_echelle_de_la_boite_du_jeu(self):
        """Meme echelle que les fenetres du jeu a l'ecran : H / 800 x UI_ZOOM (fenetre.py) ; reduite si la fenetre de la visionneuse est trop etroite."""
        src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'dq4_pc', 'fenetre.py'), encoding='utf-8').read()
        import re; zoom = float(re.search(r'^UI_ZOOM = ([0-9.]+)', src, re.M).group(1)); self.assertEqual(UH.ECHELLE_BOITE, zoom)
        B = UH.Boite(); self.assertAlmostEqual(B.echelle(720, 1280, 0.8), 720 / 800 * zoom); self.assertLess(B.echelle(720, 500, 0.8), 720 / 800 * zoom)

    def test_meme_cadre_pour_une_deux_trois_lignes(self):
        els = [self.dialogue(1, 'Oui.'), self.dialogue(2, 'Une ligne.\nDeux lignes.'), self.dialogue(3, 'Une.\nDeux.\nTrois.'), self.dialogue(4, 'Bonjour !', 'Alena'),
               self.dialogue(5, 'Une.\nDeux.\nTrois.', 'Roi Bastien')]
        v, B, blocs = self.vue_boites(els)
        self.assertEqual(len(blocs), 5); self.assertEqual({b[4] for b in blocs}, {B.HAUT * 1.0})               # hauteur du cadre : une seule valeur
        self.assertEqual([len(b[6]) for b in blocs], [1, 2, 3, 1, 3])                                  # (le texte, lui, garde ses lignes)
        self.assertEqual([b[5] for b in blocs], [0.0, 0.0, 0.0, B.ONGLET_H, B.ONGLET_H])               # l'onglet du nom s'ajoute au-dessus, seulement avec un nom

    def test_texte_de_plus_de_trois_lignes_une_page_de_plus(self):
        long = self.dialogue(1, 'a\nb\nc\nd\ne\nf\ng', 'Alena'); v, B, blocs = self.vue_boites([long])
        self.assertEqual(len(blocs), 3); self.assertEqual({b[4] for b in blocs}, {B.HAUT * 1.0}); self.assertEqual([b[6] for b in blocs], [['a', 'b', 'c'], ['d', 'e', 'f'], ['g']])
        self.assertEqual([b[5] for b in blocs], [B.ONGLET_H, 0.0, 0.0])                                 # le nom n'est que sur la premiere page
        self.assertEqual({(b[0], b[2]) for b in blocs}, {(0, 3)})

    def test_dialogue_coupe_a_la_largeur_de_la_boite(self):
        B = UH.Boite(); mot = 'mot '; texte = (mot * 60).strip(); r = UH.rangees_de(self.dialogue(1, texte), self.mes, B.largeur_texte())
        self.assertTrue(all(self.mes(l) <= B.largeur_texte() for l in r)); self.assertEqual(' '.join(r), texte)

    def combat(self, ennemis, issue='victoire'):
        return HI.Element(1, HI.TYPE_COMBAT, 0, ennemis=[{'nom': n, 'total': a, 'vaincus': b} for n, a, b in ennemis], or_=21, xp=38, issue=issue)

    def test_combat_courant_tient_dans_une_boite(self):
        B = UH.Boite()
        for en in ([('Gluant', 3, 3)], [('Chauve-souris', 2, 2), ('Gluant', 1, 1)], [('Glacyclone', 4, 4), ('Mage-fantôme', 1, 1), ('Golem', 1, 1)]):
            e = self.combat(en); p = UH.paginer(UH.rangees_de(e, self.mes, B.largeur_texte()), True, B.LIGNES)
            self.assertEqual(len(p), 1, en); self.assertLessEqual(len(p[0]) + 1, B.LIGNES)                          # (+ l'entete : issue et heure)
            self.assertTrue(p[0][-1].startswith('Or'))                                                          # l'or et l'experience : derniere rangee

    def test_combat_defaite_ou_fuite_sans_gain(self):
        B = UH.Boite(); e = self.combat([('Golem', 2, 1)], 'fuite'); self.assertEqual(UH.rangees_de(e, self.mes, B.largeur_texte()), ['Golem : 1 vaincu sur 2'])

    def test_combat_trop_long_une_page_de_plus_et_meme_cadre(self):
        en = [('Monstre numéro %d' % i, 3, 3) for i in range(12)]; e = self.combat(en)
        v, B, blocs = self.vue_boites([e]); self.assertGreater(len(blocs), 1)
        self.assertEqual({b[4] for b in blocs}, {B.HAUT * 1.0})
        pages = [b[6] for b in blocs]; self.assertLessEqual(len(pages[0]) + 1, B.LIGNES); self.assertTrue(all(len(p) <= B.LIGNES for p in pages[1:]))
        self.assertTrue(pages[-1][-1].startswith('Or'))                                                           # le gain est dans la derniere page

    def test_combat_sans_ennemi_connu(self):
        B = UH.Boite(); e = self.combat([], 'defaite'); self.assertEqual(UH.rangees_de(e, self.mes, B.largeur_texte()), ['Ennemis inconnus'])

    def test_une_seule_colonne_toute_la_liste(self):
        """Toute la liste est posee d'un coup, du plus ancien (en haut) au plus recent (en bas), sans trou ni chevauchement, QUELLE QUE SOIT la hauteur de la fenetre : plus de pages, plus de « dernier element visible »."""
        els = [self.dialogue(i, 'Texte %d.' % i, 'Alena' if i % 2 else None) for i in range(10)]
        for haut in (200.0, 500.0, 5000.0):
            v, B, blocs = self.vue_boites(els, haut=haut)
            self.assertEqual(len(blocs), 10); self.assertEqual([b[0] for b in blocs], list(range(10)))             # le plus ancien en haut
            ys = [b[3] for b in blocs]; self.assertEqual(ys, sorted(ys)); self.assertEqual(ys[0], UH.MARGE_LISTE)
            for a, b in zip(blocs, blocs[1:]): self.assertAlmostEqual(b[3] - (a[3] + a[4] + a[5]), UH.ECART_ELEMENTS)           # meme ecart partout
        self.assertAlmostEqual(v.hc, blocs[-1][3] + blocs[-1][4] + blocs[-1][5] + UH.MARGE_LISTE)                   # hauteur du contenu : marges comprises

    def test_position_ne_change_pas_la_mise_en_page(self):
        """Aucun cran : la position du defilement ne fait que deplacer le contenu, les boites ne bougent pas les unes par rapport aux autres."""
        els = [self.dialogue(i, 'Texte %d.' % i, 'Alena' if i % 2 else None) for i in range(30)]
        v, B, avant = self.vue_boites(els, haut=500.0)
        for pos in (0.0, 1.0, 37.5, 1234.0, 1e9): v.pos = pos; apres = v._mesurer(None, B, 1.0, 1.0, 20.0, 500.0); self.assertEqual(apres, v._mise[1]); self.assertEqual([b[3] for b in apres], [b[3] for b in avant])

    def test_disposer_pur(self):
        b, d, f, h = UH.disposer([(1, False), (3, True), (1, True)], 100.0, 30.0, 10.0, 2.0, 5.0)
        self.assertEqual([(x[0], x[1], x[2], x[3], x[4], x[5]) for x in b], [(0, 0, 1, 5.0, 0.0, 100.0), (1, 0, 3, 115.0, 30.0, 100.0), (1, 1, 3, 247.0, 0.0, 100.0), (1, 2, 3, 349.0, 0.0, 100.0), (2, 0, 1, 459.0, 30.0, 100.0)])
        self.assertEqual((d, f, h), ([5.0, 115.0, 459.0], [105.0, 449.0, 589.0], 594.0))
        self.assertEqual(UH.disposer([], 100.0, 30.0, 10.0, 2.0, 5.0), ([], [], [], 0.0))

    GEO = dict(zip(('b', 'd', 'f', 'hc'), UH.disposer([(1, False)] * 5, 100.0, 30.0, 10.0, 2.0, 5.0)))          # 5 messages de 100 : debuts 5, 115, 225, 335, 445 ; fins 105, ..., 545 ; hauteur 550

    def test_decalage_pour_voir_du_minimum(self):
        """Message deja entierement visible : rien ne bouge. Coupe en haut ou en bas, ou hors fenetre : la vue ne defile que de ce qui manque (le bord du message rejoint le bord de la fenetre). Premier et dernier : avec la marge de la liste."""
        g = self.GEO; d, f, hc, hv = g['d'], g['f'], g['hc'], 250.0                 # fenetre de 250 : a decal 0, elle montre de 300 a 550 depuis le haut du contenu
        voir = lambda decal, i: UH.decalage_pour_voir(d, f, hc, hv, decal, i)
        self.assertEqual([UH.etendue(d, f, hc, i) for i in (0, 1, 4)], [(0.0, 105.0), (115.0, 215.0), (445.0, 550.0)])      # (le premier va jusqu'au haut du contenu, le dernier jusqu'au bas)
        self.assertEqual((voir(0.0, 4), voir(0.0, 3)), (0.0, 0.0))                      # entierement visibles : inchange
        self.assertEqual(voir(0.0, 2), 75.0)                                            # 225 a 325 : coupe en haut (la fenetre commence a 300) : il faut monter de 75 exactement
        self.assertEqual((voir(0.0, 1), voir(0.0, 0)), (185.0, 300.0))                  # hors fenetre : son bord haut en haut de la fenetre ; le premier : jusqu'au haut du contenu (marge comprise)
        self.assertEqual((voir(300.0, 0), voir(300.0, 1)), (300.0, 300.0))              # fenetre en haut (0 a 250) : les deux premiers y sont deja
        self.assertEqual((voir(300.0, 2), voir(300.0, 3), voir(300.0, 4)), (225.0, 115.0, 0.0))      # coupe ou hors fenetre en bas : son bord bas rejoint le bas de la fenetre (le dernier : jusqu'au bas du contenu)
        self.assertEqual((voir(100.0, 4), voir(100.0, 3), voir(100.0, 2), voir(100.0, 1)), (0.0, 100.0, 100.0, 185.0))

    def test_decalage_pour_voir_bornes_et_grand_message(self):
        g = self.GEO; d, f, hc = g['d'], g['f'], g['hc']
        for decal in (0.0, 40.0, 150.0, 300.0):
            for i in range(5):
                n = UH.decalage_pour_voir(d, f, hc, 250.0, decal, i); self.assertTrue(0.0 <= n <= hc - 250.0, (decal, i, n))
                top = hc - n - 250.0; haut, bas = UH.etendue(d, f, hc, i); self.assertTrue(haut >= top - 0.5 and bas <= top + 250.5, (decal, i))         # toujours entierement visible
        self.assertEqual(UH.decalage_pour_voir(d, f, hc, 90.0, 0.0, 2), hc - 90.0 - d[2])          # un message plus haut que la fenetre (100 > 90) : son debut en haut de la fenetre
        c = dict(zip(('b', 'd', 'f', 'hc'), UH.disposer([(1, False)] * 2, 100.0, 30.0, 10.0, 2.0, 5.0)))
        self.assertEqual([UH.decalage_pour_voir(c['d'], c['f'], c['hc'], 250.0, 0.0, i) for i in (0, 1)], [0.0, 0.0])      # liste plus courte que la fenetre : rien a defiler

    def test_elements_visibles(self):
        g = self.GEO; d, f, hc = g['d'], g['f'], g['hc']
        self.assertEqual(UH.elements_visibles(d, f, hc, 250.0, 0.0, True), [3, 4]); self.assertEqual(UH.elements_visibles(d, f, hc, 250.0, 0.0, False), [2, 3, 4])      # l'element 2 (225 a 325) est coupe : visible en partie seulement
        self.assertEqual(UH.elements_visibles(d, f, hc, 250.0, 300.0, True), [0, 1]); self.assertEqual(UH.elements_visibles(d, f, hc, 1000.0, 0.0, True), [0, 1, 2, 3, 4])
        self.assertEqual(UH.elements_visibles([], [], 0.0, 250.0, 0.0, True), [])

    def test_page_sans_texte(self):
        self.assertEqual(UH.paginer([], False), [[]]); self.assertEqual(UH.paginer([], True), [[]]); self.assertEqual(UH.paginer(['a', 'b', 'c'], True), [['a', 'b'], ['c']]); self.assertEqual(UH.paginer(['a', 'b', 'c'], False), [['a', 'b', 'c']])


class TestVue(unittest.TestCase):
    """Onglets, touche H, etoile et defilement (sans dessin : la geometrie du defilement est simulee par `poser`, comme dessiner() la met a jour a chaque image)."""

    @staticmethod
    def geom(v):
        """(debuts, fins) des elements de v comme poser() les place."""
        ent = [(1, e.type == HI.TYPE_DIALOGUE and bool(e.nom)) for e in v.elements]
        return UH.disposer(ent, 126.0, 32.0, UH.ECART_ELEMENTS, UH.ECART_PAGES, UH.MARGE_LISTE)[1:3]

    def test_ouverture_en_bas(self):
        v = vue(); self.assertEqual((v.onglet, v.pos, v.sel, len(v.elements)), (UH.O_DIALOGUES, 0.0, 19, 20))        # tout en bas : le plus recent visible, et actif
        self.assertGreater(v.plage(), 0); self.assertEqual(v.decal(), 0.0)

    @staticmethod
    def entier(v, i):
        """Le message i est-il entierement dans la fenetre de la liste ?"""
        haut, bas = UH.etendue(v.debuts, v.fins, v.hc, i); top = v.hc - v.decal() - v.hv
        return haut >= top - 0.5 and bas <= top + v.hv + 0.5

    def test_fleches_message_par_message(self):
        """Haut / bas : le message precedent / suivant, un a la fois (jamais une ligne ni une page) ; la vue ne defile que si ce message n'est pas entierement visible, du minimum necessaire (son bord rejoint le bord de la fenetre)."""
        K = pyglet.window.key; v = vue(); self.assertTrue(self.entier(v, 19)); defiles = 0
        for i in range(18, -1, -1):
            avant, vis = v.decal(), self.entier(v, i); frappe(v, K.UP)
            self.assertEqual(v.sel, i); self.assertTrue(self.entier(v, i), i)                                  # le message choisi est toujours entierement visible
            if vis: self.assertEqual(v.decal(), avant, 'deja visible en entier : la vue ne bouge pas (%d)' % i)
            else:
                defiles += 1; haut, bas = UH.etendue(v.debuts, v.fins, v.hc, i); self.assertAlmostEqual(haut, v.hc - v.decal() - v.hv, places=6)      # son bord haut est exactement en haut de la fenetre : pas un pixel de plus
        self.assertGreater(defiles, 0); self.assertLess(defiles, 19)                                          # (la vue a defile par moments seulement)
        frappe(v, K.UP); self.assertEqual(v.sel, 0)                                                              # butee en haut
        for i in range(1, 20):
            avant, vis = v.decal(), self.entier(v, i); frappe(v, K.DOWN)
            self.assertEqual(v.sel, i); self.assertTrue(self.entier(v, i), i)
            if vis: self.assertEqual(v.decal(), avant)
            else: haut, bas = UH.etendue(v.debuts, v.fins, v.hc, i); self.assertAlmostEqual(bas, v.hc - v.decal(), places=6)           # son bord bas est exactement en bas de la fenetre
        self.assertEqual((v.pos, v.sel), (0.0, 19)); self.assertIn(('repeter', K.DOWN, 'v', 1), v.appels)         # (repetition de la touche maintenue : Pause.maj)
        frappe(v, K.DOWN); self.assertEqual((v.pos, v.sel), (0.0, 19))                                              # butee en bas

    def test_fleche_sur_un_message_coupe_le_montre_en_entier(self):
        """Un message coupe par le haut de la fenetre : un seul appui sur Haut le choisit ET defile juste de ce qui manque ; un message coupe par le bas, de meme avec Bas."""
        K = pyglet.window.key; v = vue(n=40, hv=500.0); v.sel = 30; v.pos = 700.0; poser(v)
        vus = [i for i in range(40) if self.entier(v, i)]; premier, dernier = vus[0], vus[-1]
        self.assertGreater(premier, 0); v.sel = premier; avant = v.decal()                                       # le message juste au-dessus du premier entier est coupe (ou tout juste hors fenetre)
        frappe(v, K.UP); self.assertEqual(v.sel, premier - 1); self.assertTrue(self.entier(v, premier - 1)); self.assertGreater(v.decal(), avant); self.assertLess(v.decal() - avant, 126.0 + 32.0 + UH.ECART_ELEMENTS + 1)
        v.sel = dernier; poser(v); avant = v.decal(); frappe(v, K.DOWN)
        self.assertEqual(v.sel, dernier + 1); self.assertTrue(self.entier(v, dernier + 1))

    def test_pages_debut_fin(self):
        K = pyglet.window.key; v = vue(hv=500.0)
        frappe(v, K.PAGEUP); self.assertEqual(v.pos, 500.0 - 2 * 28.0)                                           # une page : la fenetre moins deux lignes (le contexte reste visible)
        self.assertTrue(self.entier(v, v.sel)); self.assertEqual(v.sel, [i for i in range(20) if self.entier(v, i)][-1])      # le message choisi est sorti de la fenetre : il devient le dernier message entierement visible
        frappe(v, K.PAGEUP); self.assertEqual(v.pos, 2 * (500.0 - 56.0)); self.assertTrue(self.entier(v, v.sel))
        frappe(v, K.PAGEDOWN, K.PAGEDOWN); self.assertEqual(v.pos, 0.0); self.assertTrue(self.entier(v, v.sel))
        frappe(v, K.HOME); self.assertEqual((v.pos, v.sel), (v.plage(), 0)); frappe(v, K.UP); self.assertEqual((v.pos, v.sel), (v.plage(), 0))      # butee en haut : le premier message
        frappe(v, K.END); self.assertEqual((v.pos, v.sel), (0.0, 19))

    def test_actions_du_jeu_pour_les_pages(self):
        """Les touches « Page precedente / suivante » du jeu (L / R : A et R par defaut, PAGE_UP / PAGE_DOWN) font les memes pages."""
        K = pyglet.window.key; v = vue(); v.touche(K.A); self.assertEqual(v.pos, 444.0); v.touche(K.R); self.assertEqual(v.pos, 0.0)

    def test_molette(self):
        v = vue(); pas = 28.0 * UH.PAS_MOLETTE
        v.molette(1); self.assertEqual(v.pos, pas)                                                              # molette vers le haut : les plus anciens, un pas fin et constant
        v.molette(1); self.assertEqual(v.pos, 2 * pas); v.molette(-1); v.molette(-1); self.assertEqual(v.pos, 0.0)
        v.molette(-1); self.assertEqual(v.pos, 0.0)                                                              # butee en bas
        v.defiler(10 ** 9); self.assertEqual(v.pos, v.plage()); v.defiler(-10 ** 9); self.assertEqual(v.pos, 0.0)   # (jamais au-dela de la liste)
        v.molette(3.0); self.assertEqual(v.pos, 3 * pas)                                                         # pave tactile : proportionnel au mouvement

    def test_barre_de_defilement(self):
        M = pyglet.window.mouse; v = vue(); p = v.plage(); pas = 28.0
        v.barre = dict(x0=0, x1=10, y0=0, y1=500, ptop=480, pbot=20, th=40, pouce=(20, 60), n=v.hc, vis=v.hv, base=0)               # curseur en bas (position 0)
        v.clic(5, 495, M.LEFT); self.assertEqual(v.pos, pas)                                                    # fleche du haut : une ligne
        v.clic(5, 10, M.LEFT); self.assertEqual(v.pos, 0.0)                                                     # fleche du bas
        v.barre['pouce'] = (400, 440); v.clic(5, 470, M.LEFT); self.assertEqual(v.pos, v.page_px())          # piste au-dessus du curseur : une page
        v.clic(5, 100, M.LEFT); self.assertEqual(v.pos, 0.0)
        v.barre['pouce'] = (20, 60); v.clic(5, 40, M.LEFT); self.assertEqual(v.glisse_barre, 20)                 # curseur saisi : il se deplace sans cran
        v.glisser(5, 500); self.assertAlmostEqual(v.pos, p, places=6)                                           # tire tout en haut : le plus ancien
        v.glisser(5, 0); self.assertEqual(v.pos, 0.0)
        v.glisser(5, 20 + 20 + 440 / 2.0 - 20 + 0); self.assertGreater(v.pos, 0.0); self.assertLess(v.pos, p)  # milieu : position intermediaire, proportionnelle
        v.relache(5, 0, M.LEFT); self.assertIsNone(v.glisse_barre)

    def test_glissement_dans_la_liste(self):
        """Le contenu suit le pointeur, pixel par pixel (aucun palier)."""
        v = vue(); v.drag = [300, v.decal(), False]
        v.glisser(5, 301); self.assertEqual(v.pos, 0.0)                                                         # sous la tolerance : pas un glissement
        v.glisser(5, 300 - 160); self.assertEqual(v.pos, 160.0)                                                 # le pointeur descend de 160 : le contenu descend de 160 (on voit des plus anciens)
        v.glisser(5, 300 - 161); self.assertEqual(v.pos, 161.0)                                                 # un pixel de plus : un pixel de plus (pas de palier)
        v.glisser(5, 300 + 50); self.assertEqual(v.pos, 0.0)                                                    # le pointeur remonte au-dela de son point de depart : butee en bas
        v.relache(5, 0, 1); self.assertIsNone(v.drag)

    def test_message_choisi_toujours_visible_apres_une_touche(self):
        """Apres n'importe quelle touche de la liste, le message choisi (cible de la touche Entree) est entierement visible (si la fenetre peut le contenir)."""
        K = pyglet.window.key; v = vue(n=40, hv=500.0)
        for t in (K.UP, K.UP, K.PAGEUP, K.DOWN, K.PAGEUP, K.PAGEUP, K.UP, K.PAGEDOWN, K.DOWN, K.DOWN, K.HOME, K.DOWN, K.END, K.UP):
            frappe(v, t); self.assertTrue(self.entier(v, v.sel), (t, v.sel, v.pos))
            self.assertTrue(0 <= v.sel < 40)

    def test_tous_les_messages_au_clavier(self):
        """Quelle que soit la longueur de la liste et la hauteur de la fenetre, des appuis sur Haut parcourent TOUS les messages un par un (du dernier au premier), puis Bas les reparcourent (liste plus courte que la fenetre comprise : la vue ne bouge pas)."""
        K = pyglet.window.key
        for n, hv in ((1, 500.0), (2, 500.0), (3, 500.0), (5, 500.0), (7, 500.0), (20, 500.0), (4, 1000.0), (8, 900.0), (3, 120.0), (40, 300.0), (6, 1300.0), (5, 90.0)):
            v = vue(n=n, hv=hv); vus = [v.sel]
            for _ in range(n + 5): frappe(v, K.UP); vus.append(v.sel)
            self.assertEqual(vus[:n], list(range(n - 1, -1, -1)), (n, hv)); self.assertEqual(v.sel, 0)                  # un par un, sans en sauter un seul
            vus = [v.sel]
            for _ in range(n + 5): frappe(v, K.DOWN); vus.append(v.sel)
            self.assertEqual(vus[:n], list(range(n)), (n, hv)); self.assertEqual(v.sel, n - 1)
            if hv >= 160.0: self.assertEqual(v.pos, 0.0)                                                          # (fenetre plus basse qu'un message : le dernier est montre par son debut)
            if v.plage() == 0: self.assertEqual(v.decal(), 0.0)

    def test_liste_courte_collee_en_bas(self):
        """Liste plus courte que la fenetre : rien a defiler (la molette ne fait rien), le dessin la colle en bas de la fenetre (hc < hv) ; Haut / Bas deplacent le message choisi sans bouger la vue."""
        K = pyglet.window.key; v = vue(n=3, hv=900.0); self.assertLess(v.hc, v.hv); self.assertEqual(v.plage(), 0.0)
        v.molette(1); v.defiler(500); poser(v); self.assertEqual((v.pos, v.sel), (0.0, 2))
        frappe(v, K.UP); self.assertEqual(v.sel, 1); frappe(v, K.UP, K.UP, K.UP); self.assertEqual(v.sel, 0)
        self.assertEqual((v.decal(), v.pos), (0.0, 0.0))                                                           # ... et la vue n'a pas bouge

    def test_clic_choisit_et_le_defilement_a_la_souris_n_y_change_rien(self):
        M = pyglet.window.mouse; K = pyglet.window.key; v = vue(n=40, hv=500.0); v.zones = [(0, 0, 10, 10, 5)]
        v.clic(5, 5, M.LEFT); poser(v); self.assertEqual(v.sel, 5)                                              # un clic choisit le message
        v.relache(5, 5, M.LEFT); v.molette(1); poser(v); self.assertEqual(v.sel, 5)                              # la molette defile, le message choisi reste le meme
        v.sel = 39; v.pos = 0.0; v.molette(5); v.molette(5); v.molette(5); poser(v); self.assertEqual(v.sel, 39); self.assertFalse(self.entier(v, 39))      # ... meme s'il sort de la fenetre
        frappe(v, K.UP); self.assertTrue(self.entier(v, v.sel)); self.assertLess(v.sel, 39)                        # au clavier : le plus proche message visible remplace le message sorti (le dernier de la fenetre) ...
        dernier = v.sel; self.assertEqual(dernier, [i for i in range(40) if self.entier(v, i) or v.sel == i][-1]); frappe(v, K.UP); self.assertEqual(v.sel, dernier - 1)      # ... sans avancer d'un rang de plus ; l'appui suivant avance

    def test_aucun_grise_sur_le_message_choisi(self):
        """Derogation a la regle generale des menus : ni eclairci ni grise au survol ou au choix (souris ou clavier), seule la petite fleche marque le message choisi. La boite est dessinee de la meme facon qu'elle soit choisie ou non."""
        import inspect, hud_mobile as HM
        self.assertNotIn('choisi', inspect.signature(UH.VueHistorique._boite_dessin).parameters)
        dessins = []; v = vue(); B = UH.Boite(); orig = (pyglet.shapes.Rectangle, HM.cadre)
        class Faux:
            def __init__(self, *a, **k): dessins.append(('rectangle', a, k)); self.opacity = 255
            def draw(self): dessins.append('draw')
        pyglet.shapes.Rectangle = Faux; HM.cadre = lambda *a, **k: dessins.append('cadre')
        try:
            v._boite_dessin(B, 10.0, 20.0, 1.0, 1.0, None, None, 20.0)
            self.assertEqual(dessins, ['cadre'])                                                                 # le cadre seul : aucun rectangle blanc translucide par-dessus
            for mouse in (False, True): v.P.mode_souris = mouse; dessins.clear(); v._boite_dessin(B, 10.0, 20.0, 1.0, 1.0, None, None, 20.0); self.assertEqual(dessins, ['cadre'])
        finally: pyglet.shapes.Rectangle, HM.cadre = orig

    def test_aller_centre_l_element(self):
        v = vue(n=40, hv=500.0); d, f = self.geom(v); v.aller(10); poser(v)
        self.assertEqual(v.sel, 10); milieu = v.hc - (d[10] + f[10]) / 2.0 - v.decal(); self.assertAlmostEqual(milieu, v.hv / 2.0, places=6)    # au milieu de la fenetre
        v.aller(0); poser(v); self.assertEqual((v.sel, v.pos), (0, v.plage()))                                  # (bornee : jamais au-dela du haut de la liste)
        v.aller(39); poser(v); self.assertEqual((v.sel, v.pos), (39, 0.0))

    def test_redimensionnement_garde_l_endroit(self):
        v = vue(n=40, hv=500.0); v.pos = 400.0; ent = [(1, False)] * 40
        b, d, f, hc = UH.disposer(ent, 252.0, 64.0, 24.0, 8.0, 12.0); v._geometrie(d, f, hc, 1000.0, 56.0, 2.0)
        self.assertAlmostEqual(v.pos, 800.0)                                                                    # l'echelle double : la position aussi (meme endroit de la liste)

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
        v.molette(1); v.defiler(-3); poser(v)
        self.assertEqual((v.elements, v.sel, v.pos), ([], 0, 0.0)); self.assertFalse(v.etoile()); self.assertIsNone(v.courant())
        v2 = vue(); v2.J.historique = None; v2.entrer(); self.assertEqual(v2.elements, [])                       # pas d'historique du tout (jeu lance sans)
        self.assertFalse(v2.etoile())

    def test_etoile_au_clavier(self):
        K = pyglet.window.key; v = vue(n=4); h = v.J.historique
        self.assertEqual(v.sel, 3); self.assertTrue(v.etoile() is True); self.assertEqual((v.elements[3].fav, len(h.favoris)), (1, 1))       # l'element actif a l'ouverture : le plus recent
        v.touche(K.RETURN); self.assertIsNone(v.elements[3].fav); self.assertEqual(h.favoris, [])                  # Entree : bascule
        v.aller(2); poser(v); v.touche(K.RETURN)                                                                   # (un element choisi par un clic ou par la liste : actif jusqu'au prochain defilement)
        v.aller(3); poser(v); v.touche(K.RETURN); self.assertEqual(sorted(e.fav for e in h.dialogues if e.fav), [2, 3])

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
        self.assertEqual([(e.type, e.fav) for e in v.elements], [('d', 1), ('d', 2)]); self.assertEqual((v.sel, v.pos), (1, 0.0))      # les favoris de l'onglet, dans l'ordre ou ils ont ete mis
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
        K = pyglet.window.key; v = vue(n=30, hv=500.0)
        for i in (3, 10, 11, 12, 20, 25, 26): v.etoile(i)
        v.aller(11); poser(v); v.touche(K.F); poser(v)
        self.assertEqual(len(v.elements), 7); self.assertEqual(v.courant().texte, 'm11')                         # l'element choisi, s'il est un favori, reste choisi (la vue se recentre sur lui)
        frappe(v, K.HOME); self.assertEqual((v.sel, v.pos), (0, v.plage())); frappe(v, K.END); self.assertEqual((v.sel, v.pos), (6, 0.0))
        v.defiler(10 ** 9); poser(v); self.assertEqual(v.pos, v.plage()); v.defiler(-10 ** 9); poser(v); self.assertEqual((v.pos, v.sel), (0.0, 6))      # molette et glissement bornes a la liste filtree (le message choisi ne change pas)
        frappe(v, K.PAGEUP); self.assertEqual(v.pos, v.plage() if v.plage() < v.page_px() else v.page_px())
        avant = v.courant().texte; v.touche(K.F); poser(v); self.assertEqual((len(v.elements), v.courant().texte), (30, avant))                 # decoche : la liste complete, l'element actif (un favori) reste actif
        v.aller(7); poser(v); v.touche(K.F); poser(v); self.assertEqual((v.sel, v.courant().texte), (6, 'm26'))      # l'element choisi n'est pas un favori : on se place sur le plus recent de la liste filtree

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
        self.assertEqual((len(v.elements), v.sel, v.pos), (3, 2, 0.0)); v.entrer(UH.O_COMBATS); self.assertEqual(v.onglet, UH.O_COMBATS); v.entrer(99); self.assertEqual(v.onglet, UH.O_DIALOGUES)
        v.etoile(0); v.basculer_filtre(); v.entrer(); self.assertTrue(v.favoris_seuls); self.assertEqual(len(v.elements), 1)                         # « Favoris seulement » reste coche quand on rouvre la fenetre

    def test_heure_et_onglets_suivants(self):
        self.assertEqual(UH.heure_jeu(60 * (3600 + 5 * 60 + 12)), '1:05:12'); self.assertEqual(UH.heure_jeu(-5), '0:00:00')
        self.assertEqual((UH.touche_suivante(UH.O_DIALOGUES), UH.touche_suivante(UH.O_COMBATS)), (UH.O_COMBATS, None))
        self.assertEqual((UH.onglet_suivant(1), UH.onglet_suivant(0, -1)), (0, 1))


class TestPersistance(unittest.TestCase):
    """Point 2 : les favoris (historique_favoris.json) ET l'etat de la case « Favoris seulement » (reglage historique_favoris_seuls dans reglages.json) survivent a la fermeture et a un nouveau lancement. Fichiers temporaires seulement."""
    def setUp(self):
        self.d = tempfile.mkdtemp(prefix='persist_'); self.addCleanup(shutil.rmtree, self.d, True)
        self.fav = os.path.join(self.d, 'historique_favoris.json'); self.rg = os.path.join(self.d, 'reglages.json')

    def session(self):
        """Une « session » du jeu : Historique (fichier des favoris), Reglages (reglages.json) et la fenetre d'historique, comme fenetre.py les cree."""
        P = types.SimpleNamespace(mode_souris=False, pos_souris=None, retour=lambda: None, fermer=lambda: None, _repeter=lambda *a: None)
        P.J = types.SimpleNamespace(historique=nouveau(self.fav), reg=RG.Reglages(self.rg), height=720)
        v = UH.VueHistorique(P); v.entrer(); v.hv0 = 500.0; poser(v); return v

    @staticmethod
    def fermer(v):
        """Fermeture de la visionneuse (Fenetre.on_close) : reglages et favoris ecrits."""
        v.J.reg.enregistrer(); v.J.historique.enregistrer(True)

    def test_cle_et_valeur_par_defaut(self):
        self.assertIs(RG.DEFAUT['historique_favoris_seuls'], False); self.assertIn('historique_favoris_seuls', RG.BOOLEENS_SON_TEXTE)           # (decochee par defaut ; une valeur invalide y revient)
        self.assertIs(RG.Reglages(None)['historique_favoris_seuls'], False)
        src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'dq4_pc', 'pause.py'), encoding='utf-8').read()
        self.assertNotIn('historique_favoris_seuls', src)                                                         # pas de ligne dans le menu Pause : la case est dans la fenetre elle-meme

    def test_etat_enregistre_a_chaque_changement(self):
        v = self.session(); self.assertFalse(v.favoris_seuls); self.assertFalse(os.path.exists(self.rg))
        v.touche(pyglet.window.key.F)                                                                              # coche : ecrit tout de suite, sans attendre la fermeture
        with open(self.rg, encoding='utf-8') as f: self.assertIs(json.load(f)['historique_favoris_seuls'], True)
        v.basculer_filtre()
        with open(self.rg, encoding='utf-8') as f: self.assertIs(json.load(f)['historique_favoris_seuls'], False)

    def test_aller_retour_des_reglages(self):
        for etat in (True, False):
            r = RG.Reglages(self.rg); r['vignette'] = 0.8; r['historique_favoris_seuls'] = etat; r.enregistrer()
            r2 = RG.Reglages(self.rg); self.assertIs(r2['historique_favoris_seuls'], etat); self.assertEqual(r2['vignette'], 0.8)             # (les autres reglages ne bougent pas)

    def test_valeurs_invalides_ou_absentes(self):
        for brut in ('"oui"', '1', '0', 'null', '[true]', '{"a": 1}'):
            with open(self.rg, 'w', encoding='utf-8') as f: f.write('{"historique_favoris_seuls": %s, "vignette": 0.5}' % brut)
            r = RG.Reglages(self.rg); self.assertIs(r['historique_favoris_seuls'], False, brut); self.assertEqual(r['vignette'], 0.5)
        with open(self.rg, 'w', encoding='utf-8') as f: f.write('{"vignette": 0.5}')                              # fichier d'avant cette cle : decoche
        self.assertIs(RG.Reglages(self.rg)['historique_favoris_seuls'], False)
        with open(self.rg, 'w', encoding='utf-8') as f: f.write('pas du json')                                  # illisible : valeurs par defaut, sans erreur
        self.assertIs(RG.Reglages(self.rg)['historique_favoris_seuls'], False)

    def test_deux_sessions_favoris_et_case(self):
        """Session 1 : un dialogue et un combat en favori, case cochee, fermeture. Session 2 (nouveaux objets, memes fichiers) : la case est cochee a l'ouverture de la fenetre et les favoris sont dans la liste, avec leur etoile."""
        v = self.session(); h = v.J.historique
        h.ajouter('Un dialogue.', 'Alena', 100); h.ajouter('Un autre.', None, 900); h.ajouter_combat(combat(t=50)); v.entrer()
        v.etoile(0); v.changer_onglet(UH.O_COMBATS); v.etoile(0); v.changer_onglet(UH.O_DIALOGUES); v.touche(pyglet.window.key.F); self.assertTrue(v.favoris_seuls)
        self.fermer(v)
        v2 = self.session()                                                                                       # nouveau lancement
        self.assertTrue(v2.favoris_seuls); self.assertEqual([(e.nom, e.texte, e.fav is not None) for e in v2.elements], [('Alena', 'Un dialogue.', True)])
        v2.changer_onglet(UH.O_COMBATS); self.assertEqual([(e.type, e.issue, e.fav is not None) for e in v2.elements], [('c', 'victoire', True)])
        v2.touche(pyglet.window.key.F); self.assertEqual(len(v2.elements), 0)                                       # decochee : la session est vide (le reste de l'historique n'est pas conserve)
        self.fermer(v2)
        v3 = self.session(); self.assertFalse(v3.favoris_seuls)                                                   # ... et la case decochee est conservee aussi
        v3.touche(pyglet.window.key.F); self.assertEqual(len(v3.elements), 1)                                       # les favoris, eux, sont toujours la

    def test_favoris_survivent_sans_fermeture_propre(self):
        """Les favoris sont ecrits au moment de l'etoile : une fermeture brutale (sans on_close) ne les perd pas."""
        v = self.session(); v.J.historique.ajouter('Garde-moi.', 'Roi', 10); v.entrer(); v.etoile(0)
        h2 = nouveau(self.fav); self.assertEqual([(e.nom, e.texte) for e in h2.liste('dialogues', True)], [('Roi', 'Garde-moi.')])

    def test_erreur_d_ecriture_n_empeche_pas_de_cocher(self):
        v = self.session()
        def casse(): raise OSError('disque plein')
        v.J.reg.enregistrer = casse
        self.assertTrue(v.basculer_filtre()); self.assertTrue(v.favoris_seuls)
        v.J.reg = None; self.assertFalse(v.basculer_filtre())                                                       # (pas de reglages du tout : la case marche quand meme)
        v.entrer(); self.assertFalse(v.favoris_seuls)

    def test_la_fenetre_relit_l_etat_a_l_ouverture(self):
        v = self.session(); v.J.reg['historique_favoris_seuls'] = True; v.entrer(); self.assertTrue(v.favoris_seuls)


class TestPause(unittest.TestCase):
    """L'historique dans le menu Pause : entree de la racine, ouverture par la touche (page directe), cycle de la touche H, retour, ligne de la page Commandes."""
    def jeu(self):
        import pause as PA
        h = nouveau(None); h.ajouter('Bonjour.', 'Alena', 200); h.ajouter_combat(combat())
        self.pauses = []
        J = types.SimpleNamespace(reg=RG.Reglages(None), historique=h, width=1280, height=720, souris=None, args=types.SimpleNamespace(cache='/inexistant'),
                                  pause_jeu=lambda oui: self.pauses.append(oui), son=types.SimpleNamespace(actif=True, ecoute=False))
        J.reg.enregistrer = lambda: None; J.regler_fondu = lambda v: None; J.regler_vitesse_combat = lambda v: None; J.appliquer_texte = lambda: None          # (la page Commandes porte la section « Défilement du texte »)
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


class TestMessageVide(unittest.TestCase):
    """#140 : le message de la liste vide (surtout « Aucun dialogue en favori : ... », long) etait dessine sur une seule ligne et depassait du cadre : il est coupe aux espaces."""
    larg = staticmethod(lambda t: 10.0 * len(t))                      # police d'essai : 10 unites par caractere

    def test_aucune_ligne_ne_depasse(self):
        for msg in list(UH.VIDES.values()) + list(UH.VIDES_FAVORIS.values()):
            for limite in (200.0, 400.0, 800.0, 1600.0):
                ls = UH.couper_mots(msg, self.larg, limite)
                self.assertEqual(' '.join(ls).split(), msg.split())                                       # aucun mot perdu ni change
                for l in ls: self.assertLessEqual(self.larg(l), max(limite, max(self.larg(m) for m in msg.split())), (limite, l))

    def test_message_court_reste_sur_une_ligne(self):
        self.assertEqual(UH.couper_mots(UH.VIDES['dialogues'], self.larg, 10000.0), [UH.VIDES['dialogues']])
        self.assertEqual(UH.couper_mots('', self.larg, 100.0), [''])

    def test_message_long_est_coupe(self):
        ls = UH.couper_mots(UH.VIDES_FAVORIS['dialogues'], self.larg, 600.0); self.assertGreater(len(ls), 1)

    def test_mot_trop_large_reste_seul(self):
        self.assertEqual(UH.couper_mots('a ABCDEFGHIJ b', self.larg, 50.0), ['a', 'ABCDEFGHIJ', 'b'])

    def test_le_dessin_coupe_le_message(self):
        src = open(os.path.join(os.path.dirname(UH.__file__), 'ui_historique.py'), encoding='utf-8').read()
        self.assertIn('couper_mots(msg,', src)                                                              # la liste vide passe par la coupure (plus de ligne unique)


if __name__ == '__main__':
    unittest.main(verbosity=1)
