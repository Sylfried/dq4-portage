"""Test (sans fenetre ni moteur) de l'historique : dq4_pc/historique.py (donnees pures, favoris, pages d'un message, crochet du moteur avec un faux emulateur) et ui_history.py (onglets, touche H, etoile, defilement).

    python3 tools/test_message_history.py

Verifie : nettoyage du texte (le « *: » des paroles sans nom est garde), coupure des lignes, doublons, bornes de taille, mise en forme des combats, favoris (seuls conserves : fichier ecrit tout de suite,
relu a l'ouverture, retrait par l'etoile, fichier corrompu / entrees invalides / version inconnue), pages d'un message (notees quand le joueur les a lues), messages de combat jamais ranges dans les dialogues,
combats termines recus du BattleSensor, crochet TextBuffer::cat (nom affiche ou non, combat), onglets (Dialogues, Combats : plus d'onglet Favoris), case « Favoris seulement » (clavier, souris, conservee d'un onglet a l'autre,
favoris des sessions precedentes), touche H en cycle (Dialogues -> Combats -> ferme), etoile au clavier et a la souris, defilement ; haut / bas message par message (defilement du minimum necessaire, #48), aucun grisé sur le message choisi.
Taille unique des boites (la boite de dialogue du jeu : 1, 2 ou 3 lignes, dialogue ou combat ; une page de plus au-dela de 3 lignes).
`fill(h)` met une trentaine d'elements varies dans un Historique (captures d'ecran).
"""
import inspect, json, os, shutil, struct, sys, tempfile, types, unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import _paths          # (aide des tests : retrouver le code source dans les sous-dossiers de dq4_pc)
import pyglet
pyglet.options['shadow_window'] = False                     # (pas d'affichage necessaire : on ne dessine rien)
from dq4_pc import language as LG
LG.select_language('fr')          # (D-238 : les attentes de ce test sont en francais, quelle que soit la langue de l'ordinateur)
from dq4_pc.core import history as HI
from dq4_pc.persistence import settings as RG
from dq4_pc.menus import ui_history as UH


class Clock:
    def __init__(self): self.t = 1000.0
    def __call__(self): return self.t


def new(path=None, clock=None):
    return HI.History(path, clock or Clock())


def battle(t=500, outcome='victoire', enemies=None, gold=21, xp=38, objects=None):
    d = {'t': t, 'issue': outcome, 'or': gold, 'xp': xp, 'ennemis': enemies if enemies is not None else [{'nom': 'Gluant', 'total': 3, 'vaincus': 3}]}
    if objects is not None: d['objets'] = objects
    return d


class TestText(unittest.TestCase):
    def test_clean(self):
        self.assertEqual(HI.clean('*: Bonjour, voyageur.\n'), '*: Bonjour, voyageur.')                      # le « *: » est le texte du jeu : garde
        self.assertEqual(HI.clean('Texte @c1rouge@c0 et suite\r\n\n\n\nFin   \n'), 'Texte rouge et suite\n\nFin')
        self.assertEqual(HI.clean('A\x01BC\x7f'), 'ABC')
        self.assertEqual(HI.clean('Que faites-vous ?'), 'Que faites-vous ?')                         # l'espace insecable (typographie francaise) est gardee
        self.assertEqual(HI.clean('   \n  '), '')
        self.assertEqual(HI.clean(None), '')
        self.assertEqual(len(HI.clean('x' * 5000)), HI.MAX_TEXT)

    def test_patch_semicolon_removed(self):
        """#139 : le « ; » des noms d'objets du patch (marque de coupure, toujours apres une espace) ne s'affiche pas dans l'historique ; l'espace qui le precede reste."""
        self.assertEqual(HI.clean("Ragnar obtient l'herbe ;médicinale."), "Ragnar obtient l'herbe médicinale.")
        self.assertEqual(HI.clean('Un bâton de ;cyprès et une épée de ;cuivre !\n;Fin'), 'Un bâton de cyprès et une épée de cuivre !\nFin')
        self.assertEqual(HI.clean(';'), '')
        h = HI.History(None); h.add("Il trouve l'herbe ;médicinale.", 'Mar;chand', 10)
        e = h.dialogues[-1]; self.assertEqual((e.name_str, e.text), ('Marchand', "Il trouve l'herbe médicinale."))
        f = HI.Element.from_dict({'k': HI.TYPE_DIALOGUE, 'id': 1, 't': 5, 'nom': None, 'texte': "l'herbe ;médicinale"}, 1)
        self.assertEqual(f.text, "l'herbe médicinale")                                          # un favori enregistre avant la correction se relit sans « ; » (et reste reconnu)

    def test_wrap(self):
        mes = len
        self.assertEqual(HI.wrap_text('un deux trois quatre', 9, mes), ['un deux', 'trois', 'quatre'])
        self.assertEqual(HI.wrap_text('ligne un\nligne deux', 80, mes), ['ligne un', 'ligne deux'])        # les retours a la ligne du texte sont gardes
        self.assertEqual(HI.wrap_text('a\n\nb', 80, mes), ['a', '', 'b'])
        self.assertEqual(HI.wrap_text('abcdefghij', 4, mes), ['abcd', 'efgh', 'ij'])                          # mot plus large que la ligne
        self.assertEqual(HI.wrap_text('', 10, mes), [''])
        self.assertEqual(HI.wrap_text('Que faites-vous ? Allez', 14, mes), ['Que', 'faites-vous ?', 'Allez'])      # jamais coupee a l'espace insecable
        for t in ('Je suis sûr que vous avez tous entendu les rumeurs', 'a b c d e f g h'):
            for wid in (5, 12, 30):
                self.assertTrue(all(len(l) <= wid or ' ' not in l for l in HI.wrap_text(t, wid, mes)))


class TestDialogues(unittest.TestCase):
    def test_with_and_without_name(self):
        h = new()
        a = h.add('Repos, soldats.', 'Roi Bastien', 100); b = h.add('*: Bonjour, voyageur !', None, 400); c = h.add('Voici l\'histoire.', '   ', 800)
        self.assertEqual([(e.name_str, e.text) for e in h.dialogues], [('Roi Bastien', 'Repos, soldats.'), (None, '*: Bonjour, voyageur !'), (None, 'Voici l\'histoire.')])
        self.assertTrue(all(e.type == HI.TYPE_DIALOGUE and e.fav is None for e in (a, b, c)))
        self.assertEqual(len({a.n, b.n, c.n}), 3)                                                                 # numeros d'ordre distincts
        self.assertEqual(h.entries('dialogues'), h.dialogues); self.assertIsNot(h.entries('dialogues'), h.dialogues); self.assertEqual(h.entries('inconnu'), [])

    def test_empty_and_duplicates(self):
        h = new()
        self.assertIsNone(h.add('   ', 'X', 1)); self.assertIsNone(h.add(None, None, 1)); self.assertEqual(h.dialogues, [])
        self.assertIsNotNone(h.add('Bonjour.', 'Alena', 1000))
        self.assertIsNone(h.add('Bonjour.', 'Alena', 1000 + HI.TIME_MARGIN))                                      # le moteur a reaffiche le message
        self.assertIsNotNone(h.add('Bonjour.', 'Alena', 1000 + HI.TIME_MARGIN + 1))                               # plus tard : un autre dialogue
        self.assertIsNotNone(h.add('Bonjour.', 'Ragnar', 1000 + HI.TIME_MARGIN + 2))                              # autre nom affiche : un autre dialogue
        self.assertIsNotNone(h.add('Bonjour.', None, 1000 + HI.TIME_MARGIN + 3))
        self.assertEqual(len(h.dialogues), 4)

    def test_bounds(self):
        h = new()
        for i in range(HI.MAX_DIALOGUES + 25): h.add('Message %d' % i, None, i * 1000)
        self.assertEqual(len(h.dialogues), HI.MAX_DIALOGUES); self.assertEqual(h.dialogues[0].text, 'Message 25'); self.assertEqual(h.dialogues[-1].text, 'Message %d' % (HI.MAX_DIALOGUES + 24))
        self.assertEqual(len(h.add('x' * 9000, 'N' * 300, 10 ** 9).name_str), 60)


class TestBattles(unittest.TestCase):
    def test_lines(self):
        e = HI.battle_element(1, battle(enemies=[{'nom': 'Gluant', 'total': 3, 'vaincus': 3}, {'nom': 'Chauve-souris', 'total': 1, 'vaincus': 1}, {'nom': 'Golem', 'total': 2, 'vaincus': 1}]))
        self.assertEqual(HI.battle_lines(e), ['Gluant ×3', 'Chauve-souris', 'Golem ×2 : 1 vaincu, 1 resté', 'Or : 21\u00a0\u00a0\u00a0\u00a0\u00a0Expérience : 38'])
        e2 = HI.battle_element(2, battle(outcome='fuite', enemies=[{'nom': 'Golem', 'total': 4, 'vaincus': 2}]))
        self.assertEqual(HI.battle_lines(e2), ['Golem ×4 : 2 vaincus, 2 restés'])                              # pas d'or ni d'experience sans victoire
        self.assertEqual(HI.battle_lines(HI.battle_element(3, battle(enemies=[]))), ['Ennemis inconnus', 'Or : 21\u00a0\u00a0\u00a0\u00a0\u00a0Expérience : 38'])

    def test_battle_element(self):
        e = HI.battle_element(7, battle(t=1234)); self.assertEqual((e.n, e.type, e.t, e.outcome, e.gold, e.xp, e.fav), (7, HI.BATTLE_TYPE, 1234, 'victoire', 21, 38, None))
        for bad in (None, {}, {'issue': 'nul'}, battle(outcome='nul'), {'t': 1, 'issue': 'victoire', 'or': 1, 'xp': 1}, battle(enemies=[{'nom': 'X'}])): self.assertIsNone(HI.battle_element(1, bad))
        self.assertEqual(HI.battle_element(1, battle(gold=-5, xp=-1)).gold, 0)
        self.assertEqual(len(HI.battle_element(1, battle(enemies=[{'nom': 'M%d' % i, 'total': 1, 'vaincus': 1} for i in range(30)])).enemies), 12)

    def test_add_and_bounds(self):
        h = new()
        self.assertIsNone(h.add_battle({'issue': 'x'})); self.assertEqual(h.battles, [])
        for i in range(HI.MAX_BATTLES + 5): h.add_battle(battle(t=i))
        self.assertEqual((len(h.battles), h.battles[0].t, h.battles[-1].t), (HI.MAX_BATTLES, 5, HI.MAX_BATTLES + 4))
        self.assertEqual(h.entries('combats')[-1].t, HI.MAX_BATTLES + 4); self.assertEqual(h.dialogues, [])


class TestFavorites(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.mkdtemp(prefix='fav_'); self.f = os.path.join(self.folder, 'favoris.json')

    def read(self):
        with open(self.f, encoding='utf-8') as fo: return json.load(fo)['favoris']

    def filled(self, h):
        d = h.add('Voici l\'histoire.', 'Alena', 100); h.add('Autre.', None, 5000); c = h.add_battle(battle(t=900)); return d, c

    def test_immediate_write_and_reread(self):
        h = new(self.f); d, c = self.filled(h)
        self.assertFalse(os.path.exists(self.f))                                                                  # rien n'est ecrit tant qu'il n'y a pas de favori
        self.assertTrue(h.toggle_favorite(d)); self.assertTrue(os.path.exists(self.f))                           # ecrit tout de suite
        self.assertEqual(d.fav, 1); self.assertEqual(len(h.favorites), 1); self.assertFalse(os.path.exists(self.f + '.tmp'))
        self.assertTrue(h.toggle_favorite(c)); self.assertEqual((c.fav, len(h.favorites), h.next_id), (2, 2, 3))
        h2 = new(self.f)                                                                                      # nouvelle session : les dialogues et combats ont disparu, les favoris restent
        self.assertEqual((h2.dialogues, h2.battles, h2.next_id), ([], [], 3)); self.assertEqual([(e.type, e.fav) for e in h2.favorites], [('d', 1), ('c', 2)])
        self.assertEqual((h2.favorites[0].name_str, h2.favorites[0].text), ('Alena', 'Voici l\'histoire.'))
        self.assertEqual((h2.favorites[1].enemies, h2.favorites[1].gold, h2.favorites[1].xp, h2.favorites[1].outcome), ([{'nom': 'Gluant', 'total': 3, 'vaincus': 3, 'fuis': 0, 'disparus': 0}], 21, 38, 'victoire'))
        self.assertEqual(h2.entries('favoris'), h2.favorites)
        self.assertEqual([f.fav for f in h2.entries('dialogues', True)], [f.fav for f in h2.favorites if f.type == 'd'])          # « Favoris seulement » : les favoris du fichier, du type de la liste (aussi ceux d'une session precedente)
        self.assertEqual([f.type for f in h2.entries('combats', True)], ['c'] * len([f for f in h2.favorites if f.type == 'c'])); self.assertEqual(h2.entries('dialogues'), [])
        self.assertEqual(len({e.n for e in h2.favorites + h2.dialogues}), 2)

    def test_complete_battle_favorite_round_trip_and_old_format(self):
        """#141 : les enfuis, les disparus et les objets sont gardes dans le fichier des favoris ; un favori d'avant le #141 (ni fuis, ni disparus, ni objets) est relu tel quel."""
        h = new(self.f)
        c = h.add_battle(battle(t=900, enemies=[{'nom': 'Gluant', 'total': 3, 'vaincus': 1, 'fuis': 1, 'disparus': 1}], objects=[{'nom': 'herbe ;médicinale'}, {'nom': 'pierre de vie'}]))
        self.assertEqual(c.objects, [{'nom': 'herbe médicinale'}, {'nom': 'pierre de vie'}]); h.toggle_favorite(c)
        self.assertEqual(self.read()[0]['objets'], c.objects); self.assertEqual(self.read()[0]['ennemis'][0]['fuis'], 1)
        f = new(self.f).favorites[0]; self.assertEqual((f.enemies, f.objects), (c.enemies, c.objects)); self.assertEqual(f.lookup_key(), c.lookup_key())
        self.assertIsNot(h.favorites[0].objects, c.objects)                                                            # (copie independante)
        old = {'version': HI.VERSION, 'suivant': 2, 'favoris': [{'k': 'c', 'id': 1, 't': 5, 'ennemis': [{'nom': 'Gluant', 'total': 3, 'vaincus': 2}], 'or': 4, 'xp': 5, 'issue': 'victoire'}]}
        with open(self.f, 'w', encoding='utf-8') as fo: json.dump(old, fo)
        a = new(self.f).favorites; self.assertEqual(len(a), 1); self.assertEqual((a[0].enemies, a[0].objects), ([{'nom': 'Gluant', 'total': 3, 'vaincus': 2, 'fuis': 0, 'disparus': 0}], []))
        for bad in ({'objets': 'x'}, {'objets': [{'x': 1}]}, {'objets': [{'nom': 3}]}, {'ennemis': [{'nom': 'G', 'total': 1, 'vaincus': 0, 'fuis': -1}]}):
            d = dict(old['favoris'][0]); d.update(bad); old['favoris'] = [d]
            with open(self.f, 'w', encoding='utf-8') as fo: json.dump(old, fo)
            self.assertEqual(new(self.f).favorites, [], bad)                                                   # (favori invalide : ignore)

    def test_battle_key_accounts_for_detail(self):
        h = new(); a = h.add_battle(battle(enemies=[{'nom': 'G', 'total': 2, 'vaincus': 1, 'fuis': 1, 'disparus': 0}])); b = h.add_battle(battle(enemies=[{'nom': 'G', 'total': 2, 'vaincus': 1, 'fuis': 0, 'disparus': 1}]))
        c = h.add_battle(battle(enemies=[{'nom': 'G', 'total': 2, 'vaincus': 1, 'fuis': 1, 'disparus': 0}], objects=[{'nom': 'x'}]))
        self.assertEqual(len({a.lookup_key(), b.lookup_key(), c.lookup_key()}), 3)

    def test_independent_copy(self):
        h = new(self.f); d, _ = self.filled(h); h.toggle_favorite(d)
        self.assertIsNot(h.favorites[0], d); self.assertEqual(h.favorites[0].fav, 1)
        h.dialogues.clear()                                                                                       # la liste de session est vidée : le favori reste
        self.assertEqual(len(h.favorites), 1)

    def test_removal(self):
        h = new(self.f); d, c = self.filled(h); h.toggle_favorite(d); h.toggle_favorite(c)
        self.assertFalse(h.toggle_favorite(d))                                                                    # deuxieme appui sur l'etoile : retire
        self.assertIsNone(d.fav); self.assertEqual([e.fav for e in h.favorites], [2]); self.assertEqual(c.fav, 2)
        self.assertEqual([e['id'] for e in self.read()], [2])
        h2 = new(self.f); self.assertEqual([e.fav for e in h2.favorites], [2])

    def test_removal_from_the_favorites_tab(self):
        h = new(self.f); d, _ = self.filled(h); h.toggle_favorite(d)
        copied = h.favorites[0]; self.assertFalse(h.toggle_favorite(copied))                                           # « desetoiler » le favori lui-meme
        self.assertEqual(h.favorites, []); self.assertIsNone(d.fav)                                                  # l'element de la session perd son etoile aussi
        self.assertEqual(self.read(), [])

    def test_numbers_never_reused(self):
        h = new(self.f); d, c = self.filled(h); h.toggle_favorite(d); h.toggle_favorite(c); h.remove_favorite(2)
        h2 = new(self.f); self.assertEqual(h2.next_id, 3)
        e = h2.add('Neuf.', None, 10); h2.toggle_favorite(e); self.assertEqual(e.fav, 3)

    def test_without_file(self):
        h = new(None); d, _ = self.filled(h)
        self.assertTrue(h.toggle_favorite(d)); self.assertEqual(len(h.favorites), 1); self.assertFalse(h.toggle_favorite(None))      # pas de chemin : tout reste en memoire, sans erreur
        self.assertIsNone(h.error)

    def test_bounds(self):
        h = new(None)
        for i in range(HI.MAX_FAVORITES + 3): h.toggle_favorite(h.add('m%d' % i, None, i * 1000))
        self.assertEqual((len(h.favorites), h.favorites[0].text), (HI.MAX_FAVORITES, 'm3'))

    def test_corrupted_file(self):
        for content in ('{pas du json', '[1, 2]', json.dumps({'version': 1, 'parties': {}}), json.dumps({'version': HI.VERSION, 'favoris': 'x'}), ''):
            with open(self.f, 'w', encoding='utf-8') as fo: fo.write(content)
            h = new(self.f)
            self.assertEqual((h.favorites, h.next_id), ([], 1), content); self.assertTrue(os.path.exists(self.f + '.corrompu')); self.assertFalse(os.path.exists(self.f))
            os.remove(self.f + '.corrompu')

    def test_invalid_entries_ignored(self):
        good_entries = [{'k': 'd', 'id': 1, 't': 10, 'nom': 'Alena', 'texte': 'Bonjour.'}, {'k': 'c', 'id': 4, 't': 20, 'ennemis': [{'nom': 'Gluant', 'total': 2, 'vaincus': 1}], 'or': 3, 'xp': 4, 'issue': 'fuite'}]
        bad = [{'k': 'd', 'id': 2, 't': 10, 'texte': ''}, {'k': 'd', 'id': 'x', 't': 10, 'texte': 'a'}, {'k': 'd', 'id': 3, 't': -1, 'texte': 'a'}, {'k': 'z', 'id': 5, 't': 1},
                   {'k': 'c', 'id': 6, 't': 1, 'ennemis': [{'nom': 'X', 'total': -1, 'vaincus': 0}], 'issue': 'victoire'}, {'k': 'c', 'id': 7, 't': 1, 'ennemis': [], 'issue': 'nul'},
                   {'k': 'd', 'id': 1, 't': 99, 'texte': 'doublon d\'identifiant'}, {'k': 'd', 'id': True, 't': 1, 'texte': 'a'}, {'k': 'd', 'id': 8, 't': 1, 'nom': 5, 'texte': 'a'}, 'texte', None, 12]
        with open(self.f, 'w', encoding='utf-8') as fo: json.dump({'version': HI.VERSION, 'suivant': 2, 'favoris': bad[:4] + good_entries[:1] + bad[4:] + good_entries[1:]}, fo)
        h = new(self.f)
        self.assertEqual([(e.type, e.fav) for e in h.favorites], [('d', 1), ('c', 4)])
        self.assertEqual((h.favorites[1].outcome, h.favorites[1].enemies), ('fuite', [{'nom': 'Gluant', 'total': 2, 'vaincus': 1, 'fuis': 0, 'disparus': 0}]))
        self.assertEqual(h.next_id, 5)                                                                            # jamais un numero deja pris
        self.assertFalse(os.path.exists(self.f + '.corrompu'))                                                    # le fichier est garde : seules les entrees invalides sont ignorees

    def test_grouped_writes(self):
        clock = Clock(); h = new(self.f, clock); d, _ = self.filled(h); h.toggle_favorite(d)
        h._dirty = True; self.assertFalse(h.store())                                                         # trop tot : groupee
        clock.t += HI.STORAGE_DELAY + 1; self.assertTrue(h.store()); self.assertFalse(h.store(True))        # (plus rien a ecrire)
        h._dirty = True; self.assertTrue(h.store(True))                                                      # la fermeture force l'ecriture

    def test_write_error_without_stop(self):
        h = new(os.path.join(self.folder, 'fichier.json', 'sous', 'x.json')); open(os.path.join(self.folder, 'fichier.json'), 'w').close()      # un fichier a la place d'un dossier
        d = h.add('Bonjour.', None, 1); self.assertTrue(h.toggle_favorite(d)); self.assertIsNotNone(h.error); self.assertEqual(len(h.favorites), 1)


class FakeEngine:
    """Moteur minimal pour History.maj : capteur (sortie, actif), etat, ui.msg['feed'], msg_visible, battle_sensor."""
    def __init__(self, part=HI.PART_TOWN):
        self.output = []
        self.sensor = types.SimpleNamespace(active=True, drain=self._clear)
        self.state = types.SimpleNamespace(part=part, game_map='mak1f1'); self.ui = types.SimpleNamespace(msg={'feed': False}); self.msg_visible = True

    def _clear(self):
        r, self.output = self.output, []
        return r


def page(text, t=500, category=None, name_str=None):
    return {'texte': text, 'genre': 'n' if name_str else 'g', 'val': name_str, 'cat': category or HI.CATEGORY_TERRAIN, 'carte': 'mak1f1', 't': t}


class TestPagesMessage(unittest.TestCase):
    """Le moteur prepare toutes les pages d'un message d'un coup : l'historique ne doit noter la page suivante qu'une fois la precedente lue (curseur de fin de page eteint) ou la fenetre fermee."""

    def texts(self, h): return [e.text for e in h.dialogues]

    def test_names_and_no_name(self):
        h = new(); m = FakeEngine(); m.output += [page('Repos, soldats.', name_str='Roi Bastien', t=100), page('*: Bonjour.', t=900)]
        h.do_update(m); self.assertEqual([(e.name_str, e.text) for e in h.dialogues], [('Roi Bastien', 'Repos, soldats.'), (None, '*: Bonjour.')])

    def test_next_page_noted_after_read(self):
        h = new(); m = FakeEngine(); m.output += [page('Page 1.'), page('Page 2.')]
        h.do_update(m); self.assertEqual(self.texts(h), ['Page 1.'])                                                    # la page 2 n'a pas encore ete lue
        m.ui.msg['feed'] = True; h.do_update(m); self.assertEqual(self.texts(h), ['Page 1.'])                           # fin de la page 1 : curseur allume
        m.ui.msg['feed'] = False; h.do_update(m); self.assertEqual(self.texts(h), ['Page 1.', 'Page 2.'])               # le joueur tourne la page

    def test_three_pages_one_by_one(self):
        h = new(); m = FakeEngine(); m.output += [page('A.'), page('B.'), page('C.')]
        h.do_update(m); self.assertEqual(self.texts(h), ['A.'])
        for expected in (['A.', 'B.'], ['A.', 'B.', 'C.']):
            m.ui.msg['feed'] = True; h.do_update(m); m.ui.msg['feed'] = False; h.do_update(m); self.assertEqual(self.texts(h), expected)

    def test_window_closing_releases_the_rest(self):
        h = new(); m = FakeEngine(); m.output += [page('A.'), page('B.')]
        h.do_update(m); h.do_update(m); self.assertEqual(self.texts(h), ['A.'])
        m.msg_visible = False; h.do_update(m); self.assertEqual(self.texts(h), ['A.', 'B.'])

    def test_not_yet_opened_window_does_not_release(self):
        h = new(); m = FakeEngine(); m.msg_visible = False                                                      # la fenetre s'ouvre une image apres le texte
        m.output += [page('A.'), page('B.')]; h.do_update(m); h.do_update(m); self.assertEqual(self.texts(h), ['A.'])
        m.msg_visible = True; h.do_update(m); h.do_update(m); self.assertEqual(self.texts(h), ['A.'])

    def test_never_opened_window_still_gets_released(self):
        h = new(); m = FakeEngine(); m.msg_visible = False; m.output += [page('A.'), page('B.')]; h.do_update(m)
        for _ in range(HI.WINDOW_WAIT + 2): h.do_update(m)
        self.assertEqual(self.texts(h), ['A.', 'B.'])

    def test_new_message_releases_remaining_pages_in_order(self):
        h = new(); m = FakeEngine(); m.output += [page('A.'), page('B.')]; h.do_update(m)
        m.output += [page('Autre.', t=900)]; h.do_update(m); self.assertEqual(self.texts(h), ['A.', 'B.', 'Autre.'])

    def test_battle_never_retained(self):
        h = new(); m = FakeEngine(HI.PART_BATTLE)
        m.output += [page('Le monstre attaque !', category=HI.CATEGORY_BATTLE), page('Ragnar subit 3 points.', category=HI.CATEGORY_BATTLE)]; h.do_update(m)
        self.assertEqual((h.dialogues, h.battles), ([], []))                                                       # ni dans les dialogues, ni dans les combats (ceux-ci viennent du BattleSensor)

    def test_distinct_messages_same_frame_not_retained(self):
        h = new(); m = FakeEngine(); m.output += [page('A.'), page('B.', name_str='Alena')]; h.do_update(m)
        self.assertEqual(self.texts(h), ['A.', 'B.'])                                                              # noms differents : deux messages, pas deux pages

    def test_outside_game_nothing_retained(self):
        h = new(); m = FakeEngine(part=0); m.output += [page('Titre.')]; h.do_update(m); self.assertEqual(h.dialogues, [])

    def test_without_sensor_or_battle(self):
        h = new(); h.do_update(types.SimpleNamespace()); self.assertIsNone(h.error)                                  # (visionneuse sans moteur de messages : rien ne casse)

    def test_finished_battles_of_sensor(self):
        h = new(); m = FakeEngine(); batches = [[battle(t=1), battle(t=2, outcome='fuite', enemies=[{'nom': 'Golem', 'total': 1, 'vaincus': 0}])], [], [{'issue': 'invalide'}, battle(t=3)]]
        m.battle_sensor = types.SimpleNamespace(do_update=lambda eng: batches.pop(0))
        for _ in range(3): h.do_update(m)
        self.assertEqual([(c.t, c.outcome) for c in h.battles], [(1, 'victoire'), (2, 'fuite'), (3, 'victoire')]); self.assertEqual(h.dialogues, [])

    def test_an_error_does_not_stop_the_game(self):
        h = new(); m = FakeEngine(); m.battle_sensor = types.SimpleNamespace(do_update=lambda eng: 1 / 0)
        h.do_update(m); h.do_update(m); self.assertIsNotNone(h.error)


class FakeCore:
    """Emulateur factice pour Sensor._cat : registres, chaines C, memoire et noms de fonctions."""
    XREG = list(range(100, 131)); LIB_BASE = 0

    def __init__(self, chaines, memory, names): self.chaines, self.memory, self.names = chaines, memory, names; self.regs = {}
    def read_cstr(self, a): return self.chaines[a]
    def mem(self, a, n): return self.memory[a][:n]
    def where(self, a): return self.names.get(a, '?+0')


class TestSensor(unittest.TestCase):
    """Le crochet de TextBuffer::cat : texte, nom que le jeu affiche (2e argument), combat ou terrain, heure de jeu."""

    def sensor(self, text, name_str, part=HI.PART_TOWN, stack=('Foo::bar',), clock=777):
        names, memory, fp = {0x1000: stack[0] + '+8'}, {0x9000 + 4: struct.pack('<2I', clock, 66)}, 0x2000
        for i, n in enumerate(stack[1:]):                                       # chaine des pointeurs de cadre
            memory[fp] = struct.pack('<QQ', fp + 0x100, 0x1100 + i); names[0x1100 + i] = n + '+4'; fp += 0x100
        memory[fp] = struct.pack('<QQ', 0, 0)
        c = FakeCore({0x10: text.encode('utf-8'), 0x20: name_str.encode('utf-8')} if name_str is not None else {0x10: text.encode('utf-8')}, memory, names)
        regs = {c.XREG[1]: 0x10 if text is not None else 0, c.XREG[2]: 0x20 if name_str is not None else 0, c.XREG[30]: 0x1000, c.XREG[29]: 0x2000}
        cap = HI.Sensor.__new__(HI.Sensor); cap.active = True; cap.output = []; cap.c = c; cap.g_game = 0x9000
        cap.m = types.SimpleNamespace(state=types.SimpleNamespace(part=part, game_map='caf1'))
        uc = types.SimpleNamespace(reg_read=lambda r: regs[r]); cap._cat(uc, 0, 0, None)
        return cap.drain()

    def test_displayed_name(self):
        (r,) = self.sensor('Repos, soldats.', 'Roi Bastien')
        self.assertEqual((r['texte'], r['genre'], r['val'], r['cat'], r['carte'], r['t']), ('Repos, soldats.', 'n', 'Roi Bastien', 't', 'caf1', 777))

    def test_without_name(self):
        for name_str in (None, '', '  '):
            (r,) = self.sensor('*: Bonjour.', name_str); self.assertEqual((r['genre'], r['val'], r['cat']), ('g', None, 't'))

    def test_empty_ignored(self):
        self.assertEqual(self.sensor('   ', 'Alena'), [])

    def test_battle_by_part_or_stack(self):
        self.assertEqual(self.sensor('Le gluant attaque !', None, part=HI.PART_BATTLE)[0]['cat'], 'c')
        self.assertEqual(self.sensor('Texte.', None, stack=('Foo::bar', 'BattleRoot::exec', 'main'))[0]['cat'], 'c')          # message de combat lance depuis un menu de combat
        self.assertEqual(self.sensor('Texte.', None, stack=('Foo::bar', 'Scene::exec', 'main'))[0]['cat'], 't')

    def test_field(self):
        (r,) = self.sensor('Texte.', None, part=HI.PART_FIELD); self.assertEqual(r['carte'], 'monde')

    def test_end_to_end_in_history(self):
        h = new(); m = FakeEngine()
        m.output += self.sensor('Repos, soldats.', 'Roi Bastien') + self.sensor('Le gluant attaque !', None, part=HI.PART_BATTLE); h.do_update(m)
        self.assertEqual([(e.name_str, e.text) for e in h.dialogues], [('Roi Bastien', 'Repos, soldats.')])


class TestKey(unittest.TestCase):
    def test_default_key(self):
        reg = RG.Settings(None)
        self.assertEqual(reg['touches']['historique'], ['H', None])
        ts = {a: [n for n in l if n] for a, l in reg['touches'].items()}
        others = [n for a, l in ts.items() if a != 'historique' for n in l]
        self.assertNotIn('H', others)                                                                          # pas de conflit avec une autre action
        self.assertTrue(all(n not in RG.RESERVED for n in ts['historique']))
        self.assertEqual(reg.action_of(pyglet.window.key.H), 'historique')
        self.assertEqual(dict(RG.ACTIONS)['historique'], 'Historique')


def fill(h):
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
    for i, (name_str, text) in enumerate(L): t += 300 if i % 5 else 1800; h.add(text, name_str, t)
    for i, (entry, g, x, outcome) in enumerate([([('Gluant', 3, 3)], 21, 38, 'victoire'), ([('Chauve-souris', 2, 2), ('Gluant', 1, 1)], 14, 25, 'victoire'), ([('Golem', 2, 1)], 0, 0, 'fuite'),
                                           ([('Glacyclone', 4, 4), ('Mage-fantôme', 1, 1)], 96, 210, 'victoire'), ([('Dragon bleu', 1, 0)], 0, 0, 'defaite'),
                                           ([('Gluant', 3, 3), ('Chauve-souris', 2, 2), ('Golem', 1, 1), ('Mage-fantôme', 2, 2), ('Glacyclone', 4, 4), ('Dragon bleu', 1, 1)], 250, 480, 'victoire')]):
        h.add_battle(battle(t=600 + 4000 * i, outcome=outcome, enemies=[{'nom': n, 'total': a, 'vaincus': b} for n, a, b in entry], gold=g, xp=x))
    for e in (h.dialogues[2], h.dialogues[10], h.battles[3]): h.toggle_favorite(e)


def make_view(n=20, hv=500.0, battles=0):
    h = new(None)
    for i in range(n): h.add('m%d' % i, 'Perso %d' % i if i % 2 else None, 200 + 5000 * i)
    for i in range(battles): h.add_battle(battle(t=100 + i))
    calls = []
    P = types.SimpleNamespace(mouse_mode=False, mouse_pos=None, back=lambda: calls.append('retour'), shutdown=lambda: calls.append('fermer'), _repeat=lambda *a: calls.append(('repeter',) + a))
    P.J = types.SimpleNamespace(history=h, reg=RG.Settings(None), height=720)
    v = UH.HistoryView(P); v.enter(); v.calls = calls; v.hv0 = hv; place(v)
    return v


def place(v, hv=None):
    """Ce que dessiner() fait a chaque image, sans police ni GL : empile les elements de v (boites de 126 pixels, onglet de 32 pour un dialogue avec nom, ecarts du dessin a l'echelle 1) et met a jour la geometrie du defilement
    (hauteur du contenu, repere, element actif). A appeler apres chaque action qui change la liste ou la position."""
    if hv is not None: v.hv0 = hv
    ent = [(1, e.type == HI.TYPE_DIALOGUE and bool(e.name_str)) for e in v.elements]
    boxes, starts, ends, hc = UH.arrange(ent, 126.0, 32.0, UH.ELEMENT_SPACING, UH.PAGE_SPACING, UH.ENTRIES_MARGIN)
    v._geometry(starts, ends, hc, v.hv0, 28.0, 1.0)
    return boxes


def keystroke(v, *key_list):
    """Des touches, avec une image dessinee entre deux."""
    for t in key_list: v.key_press(t); place(v)


class TestBox(unittest.TestCase):
    """Taille des boites de l'historique : la boite de dialogue du jeu (3 lignes) pour un dialogue, que le texte fasse 1, 2 ou 3 lignes (au-dela : une page de plus) ; un combat grandit avec son texte (#141)."""
    @staticmethod
    def mes(t): return 9.0 * len(t)                                            # largeur d'une chaine (unites) : 9 par caractere

    def boxes_view(self, elements, topmost=900.0):
        """Boites calculees comme dessiner() les place (sans GL) : police du systeme simulee (P._et), echelle 1, fenetre de la liste de `topmost` pixels. -> (vue, boite, boites du plus ancien en haut au plus recent en bas,
        chacune (element, boite, nombre de boites, haut, haut du cadre, haut de l'onglet, rangees de texte))."""
        v = make_view(0); v.elements = elements; v._layout = None
        v.P._label = lambda t, size_value: types.SimpleNamespace(content_width=self.mes(t) / 0.9)
        B = UH.Box(); bs = v._measure(None, B, 1.0, 1.0, 20.0, topmost)
        return v, B, [(i, p, num, h, hb, hn, r) for (i, p, num, h, hn, hb, r) in bs]

    @staticmethod
    def dialogue(n, text, name_str=None): return HI.Element(n, HI.TYPE_DIALOGUE, 0, name_str=name_str, text=text)

    def test_game_dimensions(self):
        B = UH.Box(); self.assertEqual((B.WIDTH, B.UP, B.LINES, B.STEP), (452.0, 126.0, 3, 28.0)); self.assertEqual((B.TAB_L, B.TAB_H), (246.0, 32.0))
        self.assertEqual([B.base(i) for i in range(3)], [B.BASE_1, B.BASE_1 + 28.0, B.BASE_1 + 56.0])
        self.assertLess(B.base(2), B.UP)                                         # la 3e ligne tient dans le cadre
        self.assertGreater(B.text_width(), 400)

    def test_dimensions_read_from_page_layout(self):
        import test_dialogue_name as N
        B = UH.Box.from_ml(N.fake_ml()); self.assertEqual((B.WIDTH, B.UP, B.TAB_L, B.TAB_H, B.x0, B.z0, B.win), (452.0, 126.0, 246.0, 32.0, -223.0, -251.0, (0.0, 10.0, 86.0)))
        self.assertEqual((UH.Box.from_ml(None).WIDTH, UH.Box.from_ml(object()).UP), (452.0, 126.0))               # (mise en page absente ou inutilisable : valeurs mesurees)

    def test_dimensions_of_real_borders(self):
        import test_dialogue_name as N; from dq4_pc.menus import ui_menu as UM
        l, c = os.path.join(N.CACHE, 'ui_layout.json'), os.path.join(N.CACHE, 'ui_frameData.bin')
        if not (os.path.exists(l) and os.path.exists(c)): self.skipTest('cache d\'interface absent')
        B = UH.Box.from_ml(UM.PageLayout(l, c)); d = UH.Box()
        self.assertEqual((B.WIDTH, B.UP, B.TAB_L, B.TAB_H), (d.WIDTH, d.UP, d.TAB_L, d.TAB_H)); self.assertEqual(B.text_scale, UH.TEXT_SCALE)

    def test_game_box_scale(self):
        """Meme echelle que les fenetres du jeu a l'ecran : H / 800 x UI_ZOOM (window.py) ; reduite si la fenetre de la visionneuse est trop etroite."""
        src = _paths.source('window.py')
        import re; zoom = float(re.search(r'^UI_ZOOM = ([0-9.]+)', src, re.M).group(1)); self.assertEqual(UH.BOX_SCALE, zoom)
        B = UH.Box(); self.assertAlmostEqual(B.scale_factor(720, 1280, 0.8), 720 / 800 * zoom); self.assertLess(B.scale_factor(720, 500, 0.8), 720 / 800 * zoom)

    def test_same_border_for_one_two_three_lines(self):
        els = [self.dialogue(1, 'Oui.'), self.dialogue(2, 'Une ligne.\nDeux lignes.'), self.dialogue(3, 'Une.\nDeux.\nTrois.'), self.dialogue(4, 'Bonjour !', 'Alena'),
               self.dialogue(5, 'Une.\nDeux.\nTrois.', 'Roi Bastien')]
        v, B, blocks = self.boxes_view(els)
        self.assertEqual(len(blocks), 5); self.assertEqual({b[4] for b in blocks}, {B.UP * 1.0})               # hauteur du cadre : une seule valeur
        self.assertEqual([len(b[6]) for b in blocks], [1, 2, 3, 1, 3])                                  # (le texte, lui, garde ses lignes)
        self.assertEqual([b[5] for b in blocks], [0.0, 0.0, 0.0, B.TAB_H, B.TAB_H])               # l'onglet du nom s'ajoute au-dessus, seulement avec un nom

    def test_text_over_three_lines_one_more_page(self):
        long = self.dialogue(1, 'a\nb\nc\nd\ne\nf\ng', 'Alena'); v, B, blocks = self.boxes_view([long])
        self.assertEqual(len(blocks), 3); self.assertEqual({b[4] for b in blocks}, {B.UP * 1.0}); self.assertEqual([b[6] for b in blocks], [['a', 'b', 'c'], ['d', 'e', 'f'], ['g']])
        self.assertEqual([b[5] for b in blocks], [B.TAB_H, 0.0, 0.0])                                 # le nom n'est que sur la premiere page
        self.assertEqual({(b[0], b[2]) for b in blocks}, {(0, 3)})

    def test_dialogue_cut_to_box_width(self):
        B = UH.Box(); word = 'mot '; text = (word * 60).strip(); r = UH.rows_of(self.dialogue(1, text), self.mes, B.text_width())
        self.assertTrue(all(self.mes(l) <= B.text_width() for l in r)); self.assertEqual(' '.join(r), text)

    def battle(self, enemies, outcome='victoire', objects=None):
        return HI.Element(1, HI.BATTLE_TYPE, 0, enemies=[dict(nom=n, total=a, vaincus=v, fuis=f, disparus=d) for n, a, v, f, d in [(x + (0, 0))[:5] for x in enemies]], gold=21, xp=38, outcome=outcome, objects=objects)

    def test_battle_grows_with_its_text(self):
        """#141 : un combat n'est plus coupe en pages de 3 lignes : sa boite a autant de lignes que son texte (entete comprise), 3 au moins, et le cadre du jeu s'allonge d'autant."""
        B = UH.Box()
        for entry, lines in (([('Gluant', 3, 3)], 3), ([('Chauve-souris', 2, 2), ('Gluant', 1, 1)], 4), ([('Glacyclone', 4, 4), ('Mage-fantôme', 1, 1), ('Golem', 1, 1)], 5)):
            e = self.battle(entry); v, B, blocks = self.boxes_view([e]); self.assertEqual(len(blocks), 1, entry)                        # une seule boite
            self.assertEqual(len(blocks[0][6]), len(entry) + 1)                                                                     # une rangee par espece + l'or et l'experience
            self.assertEqual(blocks[0][4], B.top_for(lines) * 1.0); self.assertEqual(UH.box_lines(blocks[0][6], True, True), lines)
        self.assertEqual(B.top_for(3), B.UP); self.assertEqual(B.top_for(1), B.UP); self.assertEqual(B.top_for(5), B.UP + 2 * B.STEP)

    def test_detailed_battle_row_per_species_then_gains_then_items(self):
        B = UH.Box(); e = self.battle([('Gluant', 3, 1, 1, 1), ('Golem', 1, 0, 0, 0), ('Dragon', 1, 1, 0, 0)], objects=[{'nom': 'herbe médicinale'}, {'nom': 'pierre de vie'}])
        self.assertEqual(UH.rows_of(e, lambda t: 6.0 * len(t), B.text_width()), ['Gluant ×3 : 1 vaincu, 1 enfui, 1 disparu', 'Golem : resté', 'Dragon', 'Or : 21\u00a0\u00a0\u00a0\u00a0\u00a0Expérience : 38',
                                                                       'Objets : herbe médicinale, pierre de vie'])

    def test_battle_defeat_or_escape_without_gain(self):
        B = UH.Box(); e = self.battle([('Golem', 2, 1)], 'fuite'); self.assertEqual(UH.rows_of(e, self.mes, B.text_width()), ['Golem ×2 : 1 vaincu, 1 resté'])
        e = self.battle([('Golem', 2, 0, 1, 0)], 'defaite', objects=[{'nom': 'x'}]); self.assertEqual(UH.rows_of(e, self.mes, B.text_width()), ['Golem ×2 : 1 enfui, 1 resté'])   # pas d'or, d'experience ni d'objets sans victoire

    def test_battle_too_long_continues_in_next_box(self):
        entry = [('Monstre numéro %d' % i, 3, 3) for i in range(20)]; e = self.battle(entry)
        v, B, blocks = self.boxes_view([e]); self.assertGreater(len(blocks), 1)
        pages = [b[6] for b in blocks]; self.assertEqual(len(pages[0]) + 1, UH.MAX_BATTLE_LINES); self.assertTrue(all(len(p) <= UH.MAX_BATTLE_LINES for p in pages[1:]))
        self.assertEqual(blocks[0][4], B.top_for(UH.MAX_BATTLE_LINES)); self.assertEqual(sum(len(p) for p in pages), 21)           # (20 especes + l'or et l'experience)
        self.assertEqual(blocks[-1][4], B.top_for(UH.box_lines(pages[-1], False, True)))                                    # la derniere boite a la hauteur de son texte, pas plus

    def test_dialogue_keeps_game_box(self):
        v, B, blocks = self.boxes_view([self.dialogue(1, 'Oui.'), self.battle([('Gluant', 3, 3), ('Golem', 2, 2), ('Dragon', 1, 1)]), self.dialogue(3, 'Une.\nDeux.\nTrois.')])
        self.assertEqual([b[4] for b in blocks], [B.UP, B.top_for(5), B.UP])

    def test_arrange_different_heights(self):
        boxes, starts, ends, hc = UH.arrange([(1, False), (2, True, [200.0, 130.0]), (1, False, [300.0])], 100.0, 30.0, 10.0, 5.0, 8.0)
        self.assertEqual([(b[0], b[1], b[3], b[4], b[5]) for b in boxes], [(0, 0, 8.0, 0.0, 100.0), (1, 0, 118.0, 30.0, 200.0), (1, 1, 353.0, 0.0, 130.0), (2, 0, 493.0, 0.0, 300.0)])
        self.assertEqual((starts, ends, hc), ([8.0, 118.0, 493.0], [108.0, 483.0, 793.0], 801.0))

    def test_stretch_border(self):
        """Cadre a neuf morceaux (coins de 12 unites) : seuls les sommets de la moitie haute montent ; la mise en page d'origine n'est pas modifiee."""
        vtx = [[-223.0, -251.0], [-211.0, -251.0], [-211.0, -239.0], [-223.0, -239.0], [-211.0, -137.0], [-223.0, -137.0], [-211.0, -125.0], [-223.0, -125.0], [229.0, -125.0]]
        copied = [list(v) for v in vtx]; r = UH.stretch_border(vtx, 56.0); self.assertEqual(vtx, copied)
        self.assertEqual([v[1] for v in r], [-251.0, -251.0, -239.0, -239.0, -81.0, -81.0, -69.0, -69.0, -69.0]); self.assertEqual([v[0] for v in r], [v[0] for v in vtx])
        self.assertEqual(UH.stretch_border(vtx, 0.0), vtx); self.assertEqual(UH.stretch_border([], 5.0), [])

    def test_stretched_game_border(self):
        """Avec la vraie mise en page : le cadre d'un combat de 5 lignes est plus haut de 2 lignes (56 unites), ses coins gardent leur taille, le cadre d'un dialogue n'est pas touche."""
        import test_dialogue_name as N; from dq4_pc.menus import ui_menu as UM
        l, c = os.path.join(N.CACHE, 'ui_layout.json'), os.path.join(N.CACHE, 'ui_frameData.bin')
        if not (os.path.exists(l) and os.path.exists(c)): self.skipTest('cache d\'interface absent')
        ml = UM.PageLayout(l, c); v = make_view(0); v.J.ui_render = types.SimpleNamespace(ml=ml)
        f0 = v._box_window(False); f2 = v._box_window(False, 2); self.assertIsNot(f0, f2)
        h = lambda f: max(x[1] for x in f.N['cadre']['vtx']) - min(x[1] for x in f.N['cadre']['vtx'])
        self.assertEqual(h(f0), 126.0); self.assertEqual(h(f2), 126.0 + 2 * UH.Box.STEP)
        bottoms = lambda f: sorted(x[1] for x in f.N['cadre']['vtx'] if x[1] < -200); self.assertEqual(bottoms(f0), bottoms(f2))        # le bas ne bouge pas
        self.assertEqual(len(f0.N['cadre']['vtx']), len(f2.N['cadre']['vtx'])); self.assertIs(v._box_window(False, 2), f2)       # (gardee)
        vt = ml.message['types'][0]['frame_mesh']['vtx']; self.assertEqual(max(x[1] for x in vt) - min(x[1] for x in vt), 126.0)                    # (la mise en page d'origine n'a pas ete modifiee)

    def test_battle_without_known_enemy(self):
        B = UH.Box(); e = self.battle([], 'defaite'); self.assertEqual(UH.rows_of(e, self.mes, B.text_width()), ['Ennemis inconnus'])

    def test_a_single_column_the_whole_list(self):
        """Toute la liste est posee d'un coup, du plus ancien (en haut) au plus recent (en bas), sans trou ni chevauchement, QUELLE QUE SOIT la hauteur de la fenetre : plus de pages, plus de « dernier element visible »."""
        els = [self.dialogue(i, 'Texte %d.' % i, 'Alena' if i % 2 else None) for i in range(10)]
        for topmost in (200.0, 500.0, 5000.0):
            v, B, blocks = self.boxes_view(els, topmost=topmost)
            self.assertEqual(len(blocks), 10); self.assertEqual([b[0] for b in blocks], list(range(10)))             # le plus ancien en haut
            ys = [b[3] for b in blocks]; self.assertEqual(ys, sorted(ys)); self.assertEqual(ys[0], UH.ENTRIES_MARGIN)
            for a, b in zip(blocks, blocks[1:]): self.assertAlmostEqual(b[3] - (a[3] + a[4] + a[5]), UH.ELEMENT_SPACING)           # meme ecart partout
        self.assertAlmostEqual(v.hc, blocks[-1][3] + blocks[-1][4] + blocks[-1][5] + UH.ENTRIES_MARGIN)                   # hauteur du contenu : marges comprises

    def test_position_does_not_change_layout(self):
        """Aucun cran : la position du defilement ne fait que deplacer le contenu, les boites ne bougent pas les unes par rapport aux autres."""
        els = [self.dialogue(i, 'Texte %d.' % i, 'Alena' if i % 2 else None) for i in range(30)]
        v, B, before = self.boxes_view(els, topmost=500.0)
        for pos in (0.0, 1.0, 37.5, 1234.0, 1e9): v.pos = pos; after = v._measure(None, B, 1.0, 1.0, 20.0, 500.0); self.assertEqual(after, v._layout[1]); self.assertEqual([b[3] for b in after], [b[3] for b in before])

    def test_arrange_is_pure(self):
        b, d, f, h = UH.arrange([(1, False), (3, True), (1, True)], 100.0, 30.0, 10.0, 2.0, 5.0)
        self.assertEqual([(x[0], x[1], x[2], x[3], x[4], x[5]) for x in b], [(0, 0, 1, 5.0, 0.0, 100.0), (1, 0, 3, 115.0, 30.0, 100.0), (1, 1, 3, 247.0, 0.0, 100.0), (1, 2, 3, 349.0, 0.0, 100.0), (2, 0, 1, 459.0, 30.0, 100.0)])
        self.assertEqual((d, f, h), ([5.0, 115.0, 459.0], [105.0, 449.0, 589.0], 594.0))
        self.assertEqual(UH.arrange([], 100.0, 30.0, 10.0, 2.0, 5.0), ([], [], [], 0.0))

    GEO = dict(zip(('b', 'd', 'f', 'hc'), UH.arrange([(1, False)] * 5, 100.0, 30.0, 10.0, 2.0, 5.0)))          # 5 messages de 100 : debuts 5, 115, 225, 335, 445 ; fins 105, ..., 545 ; hauteur 550

    def test_offset_to_see_minimum(self):
        """Message deja entierement visible : rien ne bouge. Coupe en haut ou en bas, ou hors fenetre : la vue ne defile que de ce qui manque (le bord du message rejoint le bord de la fenetre). Premier et dernier : avec la marge de la liste."""
        g = self.GEO; d, f, hc, hv = g['d'], g['f'], g['hc'], 250.0                 # fenetre de 250 : a decal 0, elle montre de 300 a 550 depuis le haut du contenu
        see = lambda scroll_offset, i: UH.offset_to_see(d, f, hc, hv, scroll_offset, i)
        self.assertEqual([UH.extent(d, f, hc, i) for i in (0, 1, 4)], [(0.0, 105.0), (115.0, 215.0), (445.0, 550.0)])      # (le premier va jusqu'au haut du contenu, le dernier jusqu'au bas)
        self.assertEqual((see(0.0, 4), see(0.0, 3)), (0.0, 0.0))                      # entierement visibles : inchange
        self.assertEqual(see(0.0, 2), 75.0)                                            # 225 a 325 : coupe en haut (la fenetre commence a 300) : il faut monter de 75 exactement
        self.assertEqual((see(0.0, 1), see(0.0, 0)), (185.0, 300.0))                  # hors fenetre : son bord haut en haut de la fenetre ; le premier : jusqu'au haut du contenu (marge comprise)
        self.assertEqual((see(300.0, 0), see(300.0, 1)), (300.0, 300.0))              # fenetre en haut (0 a 250) : les deux premiers y sont deja
        self.assertEqual((see(300.0, 2), see(300.0, 3), see(300.0, 4)), (225.0, 115.0, 0.0))      # coupe ou hors fenetre en bas : son bord bas rejoint le bas de la fenetre (le dernier : jusqu'au bas du contenu)
        self.assertEqual((see(100.0, 4), see(100.0, 3), see(100.0, 2), see(100.0, 1)), (0.0, 100.0, 100.0, 185.0))

    def test_offset_to_see_bounds_and_large_message(self):
        g = self.GEO; d, f, hc = g['d'], g['f'], g['hc']
        for scroll_offset in (0.0, 40.0, 150.0, 300.0):
            for i in range(5):
                n = UH.offset_to_see(d, f, hc, 250.0, scroll_offset, i); self.assertTrue(0.0 <= n <= hc - 250.0, (scroll_offset, i, n))
                top = hc - n - 250.0; topmost, bottom = UH.extent(d, f, hc, i); self.assertTrue(topmost >= top - 0.5 and bottom <= top + 250.5, (scroll_offset, i))         # toujours entierement visible
        self.assertEqual(UH.offset_to_see(d, f, hc, 90.0, 0.0, 2), hc - 90.0 - d[2])          # un message plus haut que la fenetre (100 > 90) : son debut en haut de la fenetre
        c = dict(zip(('b', 'd', 'f', 'hc'), UH.arrange([(1, False)] * 2, 100.0, 30.0, 10.0, 2.0, 5.0)))
        self.assertEqual([UH.offset_to_see(c['d'], c['f'], c['hc'], 250.0, 0.0, i) for i in (0, 1)], [0.0, 0.0])      # liste plus courte que la fenetre : rien a defiler

    def test_visible_elements(self):
        g = self.GEO; d, f, hc = g['d'], g['f'], g['hc']
        self.assertEqual(UH.visible_elements(d, f, hc, 250.0, 0.0, True), [3, 4]); self.assertEqual(UH.visible_elements(d, f, hc, 250.0, 0.0, False), [2, 3, 4])      # l'element 2 (225 a 325) est coupe : visible en partie seulement
        self.assertEqual(UH.visible_elements(d, f, hc, 250.0, 300.0, True), [0, 1]); self.assertEqual(UH.visible_elements(d, f, hc, 1000.0, 0.0, True), [0, 1, 2, 3, 4])
        self.assertEqual(UH.visible_elements([], [], 0.0, 250.0, 0.0, True), [])

    def test_page_without_text(self):
        self.assertEqual(UH.paginate([], False), [[]]); self.assertEqual(UH.paginate([], True), [[]]); self.assertEqual(UH.paginate(['a', 'b', 'c'], True), [['a', 'b'], ['c']]); self.assertEqual(UH.paginate(['a', 'b', 'c'], False), [['a', 'b', 'c']])


class TestView(unittest.TestCase):
    """Onglets, touche H, etoile et defilement (sans dessin : la geometrie du defilement est simulee par `place`, comme dessiner() la met a jour a chaque image)."""

    @staticmethod
    def geom(v):
        """(debuts, fins) des elements de v comme poser() les place."""
        ent = [(1, e.type == HI.TYPE_DIALOGUE and bool(e.name_str)) for e in v.elements]
        return UH.arrange(ent, 126.0, 32.0, UH.ELEMENT_SPACING, UH.PAGE_SPACING, UH.ENTRIES_MARGIN)[1:3]

    def test_opening_at_bottom(self):
        v = make_view(); self.assertEqual((v.tab, v.pos, v.selected, len(v.elements)), (UH.O_DIALOGUES, 0.0, 19, 20))        # tout en bas : le plus recent visible, et actif
        self.assertGreater(v.span(), 0); self.assertEqual(v.scroll_offset(), 0.0)

    @staticmethod
    def fully_visible(v, i):
        """Le message i est-il entierement dans la fenetre de la liste ?"""
        topmost, bottom = UH.extent(v.starts, v.ends, v.hc, i); top = v.hc - v.scroll_offset() - v.hv
        return topmost >= top - 0.5 and bottom <= top + v.hv + 0.5

    def test_arrows_message_by_message(self):
        """Haut / bas : le message precedent / suivant, un a la fois (jamais une ligne ni une page) ; la vue ne defile que si ce message n'est pas entierement visible, du minimum necessaire (son bord rejoint le bord de la fenetre)."""
        K = pyglet.window.key; v = make_view(); self.assertTrue(self.fully_visible(v, 19)); scrolled = 0
        for i in range(18, -1, -1):
            before, vis = v.scroll_offset(), self.fully_visible(v, i); keystroke(v, K.UP)
            self.assertEqual(v.selected, i); self.assertTrue(self.fully_visible(v, i), i)                                  # le message choisi est toujours entierement visible
            if vis: self.assertEqual(v.scroll_offset(), before, 'deja visible en entier : la vue ne bouge pas (%d)' % i)
            else:
                scrolled += 1; topmost, bottom = UH.extent(v.starts, v.ends, v.hc, i); self.assertAlmostEqual(topmost, v.hc - v.scroll_offset() - v.hv, places=6)      # son bord haut est exactement en haut de la fenetre : pas un pixel de plus
        self.assertGreater(scrolled, 0); self.assertLess(scrolled, 19)                                          # (la vue a defile par moments seulement)
        keystroke(v, K.UP); self.assertEqual(v.selected, 0)                                                              # butee en haut
        for i in range(1, 20):
            before, vis = v.scroll_offset(), self.fully_visible(v, i); keystroke(v, K.DOWN)
            self.assertEqual(v.selected, i); self.assertTrue(self.fully_visible(v, i), i)
            if vis: self.assertEqual(v.scroll_offset(), before)
            else: topmost, bottom = UH.extent(v.starts, v.ends, v.hc, i); self.assertAlmostEqual(bottom, v.hc - v.scroll_offset(), places=6)           # son bord bas est exactement en bas de la fenetre
        self.assertEqual((v.pos, v.selected), (0.0, 19)); self.assertIn(('repeter', K.DOWN, 'v', 1), v.calls)         # (repetition de la touche maintenue : Pause.maj)
        keystroke(v, K.DOWN); self.assertEqual((v.pos, v.selected), (0.0, 19))                                              # butee en bas

    def test_arrow_on_cut_message_shows_it_in_full(self):
        """Un message coupe par le haut de la fenetre : un seul appui sur Haut le choisit ET defile juste de ce qui manque ; un message coupe par le bas, de meme avec Bas."""
        K = pyglet.window.key; v = make_view(n=40, hv=500.0); v.selected = 30; v.pos = 700.0; place(v)
        seen = [i for i in range(40) if self.fully_visible(v, i)]; first, last = seen[0], seen[-1]
        self.assertGreater(first, 0); v.selected = first; before = v.scroll_offset()                                       # le message juste au-dessus du premier entier est coupe (ou tout juste hors fenetre)
        keystroke(v, K.UP); self.assertEqual(v.selected, first - 1); self.assertTrue(self.fully_visible(v, first - 1)); self.assertGreater(v.scroll_offset(), before); self.assertLess(v.scroll_offset() - before, 126.0 + 32.0 + UH.ELEMENT_SPACING + 1)
        v.selected = last; place(v); before = v.scroll_offset(); keystroke(v, K.DOWN)
        self.assertEqual(v.selected, last + 1); self.assertTrue(self.fully_visible(v, last + 1))

    def test_pages_start_end(self):
        K = pyglet.window.key; v = make_view(hv=500.0)
        keystroke(v, K.PAGEUP); self.assertEqual(v.pos, 500.0 - 2 * 28.0)                                           # une page : la fenetre moins deux lignes (le contexte reste visible)
        self.assertTrue(self.fully_visible(v, v.selected)); self.assertEqual(v.selected, [i for i in range(20) if self.fully_visible(v, i)][-1])      # le message choisi est sorti de la fenetre : il devient le dernier message entierement visible
        keystroke(v, K.PAGEUP); self.assertEqual(v.pos, 2 * (500.0 - 56.0)); self.assertTrue(self.fully_visible(v, v.selected))
        keystroke(v, K.PAGEDOWN, K.PAGEDOWN); self.assertEqual(v.pos, 0.0); self.assertTrue(self.fully_visible(v, v.selected))
        keystroke(v, K.HOME); self.assertEqual((v.pos, v.selected), (v.span(), 0)); keystroke(v, K.UP); self.assertEqual((v.pos, v.selected), (v.span(), 0))      # butee en haut : le premier message
        keystroke(v, K.END); self.assertEqual((v.pos, v.selected), (0.0, 19))

    def test_game_actions_for_pages(self):
        """Les touches « Page precedente / suivante » du jeu (L / R : A et R par defaut, PAGE_UP / PAGE_DOWN) font les memes pages."""
        K = pyglet.window.key; v = make_view(); v.key_press(K.A); self.assertEqual(v.pos, 444.0); v.key_press(K.R); self.assertEqual(v.pos, 0.0)

    def test_wheel(self):
        v = make_view(); step = 28.0 * UH.WHEEL_STEP
        v.wheel(1); self.assertEqual(v.pos, step)                                                              # molette vers le haut : les plus anciens, un pas fin et constant
        v.wheel(1); self.assertEqual(v.pos, 2 * step); v.wheel(-1); v.wheel(-1); self.assertEqual(v.pos, 0.0)
        v.wheel(-1); self.assertEqual(v.pos, 0.0)                                                              # butee en bas
        v.scroll_by(10 ** 9); self.assertEqual(v.pos, v.span()); v.scroll_by(-10 ** 9); self.assertEqual(v.pos, 0.0)   # (jamais au-dela de la liste)
        v.wheel(3.0); self.assertEqual(v.pos, 3 * step)                                                         # pave tactile : proportionnel au mouvement

    def test_scroll_bar(self):
        M = pyglet.window.mouse; v = make_view(); p = v.span(); step = 28.0
        v.barre = dict(x0=0, x1=10, y0=0, y1=500, ptop=480, pbot=20, th=40, pouce=(20, 60), n=v.hc, vis=v.hv, base=0)               # curseur en bas (position 0)
        v.click(5, 495, M.LEFT); self.assertEqual(v.pos, step)                                                    # fleche du haut : une ligne
        v.click(5, 10, M.LEFT); self.assertEqual(v.pos, 0.0)                                                     # fleche du bas
        v.barre['pouce'] = (400, 440); v.click(5, 470, M.LEFT); self.assertEqual(v.pos, v.page_px())          # piste au-dessus du curseur : une page
        v.click(5, 100, M.LEFT); self.assertEqual(v.pos, 0.0)
        v.barre['pouce'] = (20, 60); v.click(5, 40, M.LEFT); self.assertEqual(v.dragging_bar, 20)                 # curseur saisi : il se deplace sans cran
        v.drag_to(5, 500); self.assertAlmostEqual(v.pos, p, places=6)                                           # tire tout en haut : le plus ancien
        v.drag_to(5, 0); self.assertEqual(v.pos, 0.0)
        v.drag_to(5, 20 + 20 + 440 / 2.0 - 20 + 0); self.assertGreater(v.pos, 0.0); self.assertLess(v.pos, p)  # milieu : position intermediaire, proportionnelle
        v.release(5, 0, M.LEFT); self.assertIsNone(v.dragging_bar)

    def test_sliding_in_the_list(self):
        """Le contenu suit le pointeur, pixel par pixel (aucun palier)."""
        v = make_view(); v.drag = [300, v.scroll_offset(), False]
        v.drag_to(5, 301); self.assertEqual(v.pos, 0.0)                                                         # sous la tolerance : pas un glissement
        v.drag_to(5, 300 - 160); self.assertEqual(v.pos, 160.0)                                                 # le pointeur descend de 160 : le contenu descend de 160 (on voit des plus anciens)
        v.drag_to(5, 300 - 161); self.assertEqual(v.pos, 161.0)                                                 # un pixel de plus : un pixel de plus (pas de palier)
        v.drag_to(5, 300 + 50); self.assertEqual(v.pos, 0.0)                                                    # le pointeur remonte au-dela de son point de depart : butee en bas
        v.release(5, 0, 1); self.assertIsNone(v.drag)

    def test_chosen_message_always_visible_after_key(self):
        """Apres n'importe quelle touche de la liste, le message choisi (cible de la touche Entree) est entierement visible (si la fenetre peut le contenir)."""
        K = pyglet.window.key; v = make_view(n=40, hv=500.0)
        for t in (K.UP, K.UP, K.PAGEUP, K.DOWN, K.PAGEUP, K.PAGEUP, K.UP, K.PAGEDOWN, K.DOWN, K.DOWN, K.HOME, K.DOWN, K.END, K.UP):
            keystroke(v, t); self.assertTrue(self.fully_visible(v, v.selected), (t, v.selected, v.pos))
            self.assertTrue(0 <= v.selected < 40)

    def test_all_messages_on_the_keyboard(self):
        """Quelle que soit la longueur de la liste et la hauteur de la fenetre, des appuis sur Haut parcourent TOUS les messages un par un (du dernier au premier), puis Bas les reparcourent (liste plus courte que la fenetre comprise : la vue ne bouge pas)."""
        K = pyglet.window.key
        for n, hv in ((1, 500.0), (2, 500.0), (3, 500.0), (5, 500.0), (7, 500.0), (20, 500.0), (4, 1000.0), (8, 900.0), (3, 120.0), (40, 300.0), (6, 1300.0), (5, 90.0)):
            v = make_view(n=n, hv=hv); seen = [v.selected]
            for _ in range(n + 5): keystroke(v, K.UP); seen.append(v.selected)
            self.assertEqual(seen[:n], list(range(n - 1, -1, -1)), (n, hv)); self.assertEqual(v.selected, 0)                  # un par un, sans en sauter un seul
            seen = [v.selected]
            for _ in range(n + 5): keystroke(v, K.DOWN); seen.append(v.selected)
            self.assertEqual(seen[:n], list(range(n)), (n, hv)); self.assertEqual(v.selected, n - 1)
            if hv >= 160.0: self.assertEqual(v.pos, 0.0)                                                          # (fenetre plus basse qu'un message : le dernier est montre par son debut)
            if v.span() == 0: self.assertEqual(v.scroll_offset(), 0.0)

    def test_short_entries_glued_to_bottom(self):
        """Liste plus courte que la fenetre : rien a defiler (la molette ne fait rien), le dessin la colle en bas de la fenetre (hc < hv) ; Haut / Bas deplacent le message choisi sans bouger la vue."""
        K = pyglet.window.key; v = make_view(n=3, hv=900.0); self.assertLess(v.hc, v.hv); self.assertEqual(v.span(), 0.0)
        v.wheel(1); v.scroll_by(500); place(v); self.assertEqual((v.pos, v.selected), (0.0, 2))
        keystroke(v, K.UP); self.assertEqual(v.selected, 1); keystroke(v, K.UP, K.UP, K.UP); self.assertEqual(v.selected, 0)
        self.assertEqual((v.scroll_offset(), v.pos), (0.0, 0.0))                                                           # ... et la vue n'a pas bouge

    def test_click_chooses_mouse_scroll_changes_nothing(self):
        M = pyglet.window.mouse; K = pyglet.window.key; v = make_view(n=40, hv=500.0); v.zones = [(0, 0, 10, 10, 5)]
        v.click(5, 5, M.LEFT); place(v); self.assertEqual(v.selected, 5)                                              # un clic choisit le message
        v.release(5, 5, M.LEFT); v.wheel(1); place(v); self.assertEqual(v.selected, 5)                              # la molette defile, le message choisi reste le meme
        v.selected = 39; v.pos = 0.0; v.wheel(5); v.wheel(5); v.wheel(5); place(v); self.assertEqual(v.selected, 39); self.assertFalse(self.fully_visible(v, 39))      # ... meme s'il sort de la fenetre
        keystroke(v, K.UP); self.assertTrue(self.fully_visible(v, v.selected)); self.assertLess(v.selected, 39)                        # au clavier : le plus proche message visible remplace le message sorti (le dernier de la fenetre) ...
        last = v.selected; self.assertEqual(last, [i for i in range(40) if self.fully_visible(v, i) or v.selected == i][-1]); keystroke(v, K.UP); self.assertEqual(v.selected, last - 1)      # ... sans avancer d'un rang de plus ; l'appui suivant avance

    def test_no_graying_on_chosen_message(self):
        """Derogation a la regle generale des menus : ni eclairci ni grise au survol ou au choix (souris ou clavier), seule la petite fleche marque le message choisi. La boite est dessinee de la meme facon qu'elle soit choisie ou non."""
        import inspect; from dq4_pc.menus import hud_mobile as HM
        self.assertNotIn('choisi', inspect.signature(UH.HistoryView._draw_box).parameters)
        drawings = []; v = make_view(); B = UH.Box(); orig = (pyglet.shapes.Rectangle, HM.border)
        class Fake:
            def __init__(self, *a, **k): drawings.append(('rectangle', a, k)); self.opacity = 255
            def draw(self): drawings.append('draw')
        pyglet.shapes.Rectangle = Fake; HM.border = lambda *a, **k: drawings.append('cadre')
        try:
            v._draw_box(B, 10.0, 20.0, 1.0, 1.0, None, None, 20.0)
            self.assertEqual(drawings, ['cadre'])                                                                 # le cadre seul : aucun rectangle blanc translucide par-dessus
            for mouse in (False, True): v.P.mouse_mode = mouse; drawings.clear(); v._draw_box(B, 10.0, 20.0, 1.0, 1.0, None, None, 20.0); self.assertEqual(drawings, ['cadre'])
        finally: pyglet.shapes.Rectangle, HM.border = orig

    def test_go_to_centers_the_item(self):
        v = make_view(n=40, hv=500.0); d, f = self.geom(v); v.go_to(10); place(v)
        self.assertEqual(v.selected, 10); middle = v.hc - (d[10] + f[10]) / 2.0 - v.scroll_offset(); self.assertAlmostEqual(middle, v.hv / 2.0, places=6)    # au milieu de la fenetre
        v.go_to(0); place(v); self.assertEqual((v.selected, v.pos), (0, v.span()))                                  # (bornee : jamais au-dela du haut de la liste)
        v.go_to(39); place(v); self.assertEqual((v.selected, v.pos), (39, 0.0))

    def test_resizing_keeps_the_spot(self):
        v = make_view(n=40, hv=500.0); v.pos = 400.0; ent = [(1, False)] * 40
        b, d, f, hc = UH.arrange(ent, 252.0, 64.0, 24.0, 8.0, 12.0); v._geometry(d, f, hc, 1000.0, 56.0, 2.0)
        self.assertAlmostEqual(v.pos, 800.0)                                                                    # l'echelle double : la position aussi (meme endroit de la liste)

    def test_tabs(self):
        K = pyglet.window.key; v = make_view(n=6, battles=3)
        self.assertEqual((len(v.elements), v.elements[0].type), (6, 'd'))
        self.assertEqual([n for n, _ in UH.TABS], ['Dialogues', 'Combats'])                                   # plus d'onglet « Favoris » : c'est une case a cocher
        v.key_press(K.RIGHT); self.assertEqual((v.tab, len(v.elements), v.elements[0].type, v.selected), (UH.O_BATTLES, 3, 'c', 2))
        v.key_press(K.RIGHT); self.assertEqual((v.tab, len(v.elements)), (UH.O_DIALOGUES, 6))                    # retour au premier
        v.key_press(K.LEFT); self.assertEqual(v.tab, UH.O_BATTLES)

    def test_h_key_cycles(self):
        K = pyglet.window.key; v = make_view(n=3, battles=2)
        self.assertEqual(v.tab, UH.O_DIALOGUES)
        self.assertTrue(v.key_press(K.H)); self.assertEqual(v.tab, UH.O_BATTLES); self.assertNotIn('fermer', v.calls)       # 2e appui : les combats
        self.assertTrue(v.key_press(K.H)); self.assertEqual(v.calls[-1], 'fermer')                                              # 3e appui : ferme tout
        v.toggle_filter(); self.assertTrue(v.key_press(K.H)); self.assertEqual(v.calls.count('fermer'), 2)                      # « Favoris seulement » coche : le cycle de H ne change pas (ici sur les combats : ferme)
        v.change_tab(UH.O_DIALOGUES); v.key_press(K.H); self.assertEqual((v.tab, v.favorites_only, v.calls.count('fermer')), (UH.O_BATTLES, True, 2))

    def test_closing(self):
        K = pyglet.window.key; v = make_view()
        v.key_press(K.ESCAPE); v.key_press(K.BACKSPACE); self.assertEqual(v.calls.count('retour'), 2)
        self.assertTrue(v.key_press(K.F5))                                                                        # toute touche est consommee : rien n'arrive au jeu

    def test_empty_entries(self):
        v = make_view(n=0); K = pyglet.window.key
        for t in (K.UP, K.DOWN, K.PAGEUP, K.PAGEDOWN, K.HOME, K.END, K.RIGHT, K.LEFT, K.RETURN): v.key_press(t)
        v.wheel(1); v.scroll_by(-3); place(v)
        self.assertEqual((v.elements, v.selected, v.pos), ([], 0, 0.0)); self.assertFalse(v.star()); self.assertIsNone(v.current_item())
        v2 = make_view(); v2.J.history = None; v2.enter(); self.assertEqual(v2.elements, [])                       # pas d'historique du tout (jeu lance sans)
        self.assertFalse(v2.star())

    def test_star_with_keyboard(self):
        K = pyglet.window.key; v = make_view(n=4); h = v.J.history
        self.assertEqual(v.selected, 3); self.assertTrue(v.star() is True); self.assertEqual((v.elements[3].fav, len(h.favorites)), (1, 1))       # l'element actif a l'ouverture : le plus recent
        v.key_press(K.RETURN); self.assertIsNone(v.elements[3].fav); self.assertEqual(h.favorites, [])                  # Entree : bascule
        v.go_to(2); place(v); v.key_press(K.RETURN)                                                                   # (un element choisi par un clic ou par la liste : actif jusqu'au prochain defilement)
        v.go_to(3); place(v); v.key_press(K.RETURN); self.assertEqual(sorted(e.fav for e in h.dialogues if e.fav), [2, 3])

    def test_star_with_mouse(self):
        M = pyglet.window.mouse; v = make_view(n=4); h = v.J.history
        v.star_zones = [(100, 100, 120, 120, 1), (100, 200, 120, 220, 3)]
        v.click(110, 210, M.LEFT); self.assertEqual((v.selected, h.dialogues[3].fav, h.dialogues[1].fav), (3, 1, None))
        v.click(110, 110, M.LEFT); self.assertEqual((v.selected, h.dialogues[1].fav), (1, 2))
        v.click(110, 210, M.LEFT); self.assertIsNone(h.dialogues[3].fav); self.assertEqual(len(h.favorites), 1)
        self.assertTrue(v.P.mouse_mode)

    def test_tab_click_and_back(self):
        M = pyglet.window.mouse; v = make_view(n=3, battles=2)
        v.tab_zones = [(0, 0, 10, 10, 0), (20, 0, 30, 10, 1)]
        v.click(25, 5, M.LEFT); self.assertEqual((v.tab, len(v.elements)), (UH.O_BATTLES, 2))
        v.click(5, 5, M.LEFT); self.assertEqual(v.tab, UH.O_DIALOGUES)
        v.click(500, 500, M.RIGHT); self.assertEqual(v.calls[-1], 'retour')                                      # clic droit : retour
        v.zone_ret = (60, 0, 70, 10); v.click(65, 5, M.LEFT); self.assertEqual(v.calls.count('retour'), 2)

    def test_favorites_only_filter(self):
        """Case « Favoris seulement » : ne garde, dans l'onglet ouvert, que ses favoris ; l'etoile retire l'element de la liste filtree ; la case reste cochee quand on change d'onglet."""
        K = pyglet.window.key; v = make_view(n=3, battles=2); h = v.J.history
        self.assertFalse(v.favorites_only)
        v.star(0); v.star(2); v.change_tab(UH.O_BATTLES); v.star(1); v.change_tab(UH.O_DIALOGUES)       # deux dialogues et un combat en favori
        self.assertEqual(len(v.elements), 3)                                                                      # (case decochee : toute la session)
        self.assertTrue(v.toggle_filter())
        self.assertEqual([(e.type, e.fav) for e in v.elements], [('d', 1), ('d', 2)]); self.assertEqual((v.selected, v.pos), (1, 0.0))      # les favoris de l'onglet, dans l'ordre ou ils ont ete mis
        v.change_tab(UH.O_BATTLES)                                                                            # le filtre est conserve d'un onglet a l'autre
        self.assertTrue(v.favorites_only); self.assertEqual([(e.type, e.fav) for e in v.elements], [('c', 3)])
        v.change_tab(UH.O_DIALOGUES); v.key_press(K.RETURN)                                                       # etoile retiree : l'element disparait de la liste filtree
        self.assertEqual([e.fav for e in v.elements], [1]); self.assertEqual(v.selected, 0); self.assertEqual(len(h.favorites), 2)
        self.assertIsNone(h.dialogues[2].fav); self.assertEqual(len(v.elements), 1)                                # (et l'element de la session perd son etoile)
        v.key_press(K.RETURN); self.assertEqual((v.elements, v.selected), ([], 0)); self.assertEqual([f.type for f in h.favorites], ['c'])
        v.key_press(K.RETURN); self.assertFalse(v.star())                                                           # liste vide : rien a basculer
        self.assertFalse(v.toggle_filter()); self.assertEqual(len(v.elements), 3)                                # case decochee : toute la session de nouveau

    def test_filter_by_keyboard_mouse_and_map_key(self):
        K = pyglet.window.key; M = pyglet.window.mouse; v = make_view(n=4)
        v.star(1); v.key_press(K.F); self.assertTrue(v.favorites_only); self.assertEqual(len(v.elements), 1)       # F : coche
        v.key_press(K.F); self.assertFalse(v.favorites_only); self.assertEqual(len(v.elements), 4)                   # F : decoche
        v.key_press(K.M); self.assertTrue(v.favorites_only)                                                           # la touche Carte (M) fait de meme
        v.filter_zone = (100, 100, 200, 130); v.click(150, 115, M.LEFT); self.assertFalse(v.favorites_only)         # clic sur la case : decoche
        v.click(150, 115, M.LEFT); self.assertTrue(v.favorites_only); self.assertEqual(len(v.elements), 1); self.assertTrue(v.P.mouse_mode)
        v.click(300, 115, M.LEFT); self.assertTrue(v.favorites_only)                                                # (a cote de la case : rien)
        self.assertTrue(v.key_press(K.F))                                                                             # (la touche est consommee : rien n'arrive au jeu)

    def test_filter_keeps_chosen_element_and_scrolls(self):
        K = pyglet.window.key; v = make_view(n=30, hv=500.0)
        for i in (3, 10, 11, 12, 20, 25, 26): v.star(i)
        v.go_to(11); place(v); v.key_press(K.F); place(v)
        self.assertEqual(len(v.elements), 7); self.assertEqual(v.current_item().text, 'm11')                         # l'element choisi, s'il est un favori, reste choisi (la vue se recentre sur lui)
        keystroke(v, K.HOME); self.assertEqual((v.selected, v.pos), (0, v.span())); keystroke(v, K.END); self.assertEqual((v.selected, v.pos), (6, 0.0))
        v.scroll_by(10 ** 9); place(v); self.assertEqual(v.pos, v.span()); v.scroll_by(-10 ** 9); place(v); self.assertEqual((v.pos, v.selected), (0.0, 6))      # molette et glissement bornes a la liste filtree (le message choisi ne change pas)
        keystroke(v, K.PAGEUP); self.assertEqual(v.pos, v.span() if v.span() < v.page_px() else v.page_px())
        before = v.current_item().text; v.key_press(K.F); place(v); self.assertEqual((len(v.elements), v.current_item().text), (30, before))                 # decoche : la liste complete, l'element actif (un favori) reste actif
        v.go_to(7); place(v); v.key_press(K.F); place(v); self.assertEqual((v.selected, v.current_item().text), (6, 'm26'))      # l'element choisi n'est pas un favori : on se place sur le plus recent de la liste filtree

    def test_favorites_from_previous_sessions(self):
        """Les favoris du fichier (sessions precedentes) ne sont pas dans la session : seule la case « Favoris seulement » les montre, avec leur etoile."""
        d = tempfile.mkdtemp(prefix='fav_'); self.addCleanup(shutil.rmtree, d, True); f = os.path.join(d, 'fav.json'); h = new(f)
        h.add('Hier.', 'Alena', 100); h.add_battle(battle(t=50)); h.toggle_favorite(h.dialogues[0]); h.toggle_favorite(h.battles[0])
        P = types.SimpleNamespace(mouse_mode=False, mouse_pos=None, back=lambda: None, shutdown=lambda: None, _repeat=lambda *a: None)
        P.J = types.SimpleNamespace(history=new(f), reg=RG.Settings(None), height=720)                    # nouvelle session : lit le fichier
        v = UH.HistoryView(P); v.enter()
        self.assertEqual((v.elements, v.selected), ([], 0))
        v.key_press(pyglet.window.key.F); self.assertEqual([(e.name_str, e.text, e.fav) for e in v.elements], [('Alena', 'Hier.', 1)])
        v.change_tab(UH.O_BATTLES); self.assertEqual([(e.type, e.fav) for e in v.elements], [('c', 2)])
        v.key_press(pyglet.window.key.RETURN); self.assertEqual(v.elements, []); self.assertEqual([e.type for e in P.J.history.favorites], ['d'])      # etoile retiree : le fichier suit

    def test_empty_with_the_filter(self):
        v = make_view(n=2); self.assertIn('Aucun dialogue', UH.EMPTY_MESSAGES['dialogues']); v.toggle_filter()
        self.assertEqual(v.elements, []); self.assertIn('Favoris seulement', UH.EMPTY_FAVORITES['dialogues']); self.assertIn('Favoris seulement', UH.EMPTY_FAVORITES['combats'])
        self.assertEqual(set(UH.EMPTY_FAVORITES), {c for _, c in UH.TABS}); self.assertEqual(set(UH.EMPTY_MESSAGES), {c for _, c in UH.TABS})

    def test_reload_on_each_opening(self):
        v = make_view(n=2); v.J.history.add('Nouveau.', None, 10 ** 6); v.enter()
        self.assertEqual((len(v.elements), v.selected, v.pos), (3, 2, 0.0)); v.enter(UH.O_BATTLES); self.assertEqual(v.tab, UH.O_BATTLES); v.enter(99); self.assertEqual(v.tab, UH.O_DIALOGUES)
        v.star(0); v.toggle_filter(); v.enter(); self.assertTrue(v.favorites_only); self.assertEqual(len(v.elements), 1)                         # « Favoris seulement » reste coche quand on rouvre la fenetre

    def test_play_time_and_next_tabs(self):
        self.assertEqual(UH.game_time(60 * (3600 + 5 * 60 + 12)), '1:05:12'); self.assertEqual(UH.game_time(-5), '0:00:00')
        self.assertEqual((UH.next_key(UH.O_DIALOGUES), UH.next_key(UH.O_BATTLES)), (UH.O_BATTLES, None))
        self.assertEqual((UH.next_tab(1), UH.next_tab(0, -1)), (0, 1))


class TestFollowTheGame(unittest.TestCase):
    """#178 : le jeu ne s'arrete plus derriere l'historique (aucune pause dans aucun menu) : ce qu'il y ecrit pendant que la fenetre est ouverte s'ajoute a la liste (`follow_game`, appele a chaque image par Pause.maj)."""
    def test_nothing_new_nothing_changes(self):
        v = make_view(n=5); selected, els = v.selected, list(v.elements); self.assertFalse(v.follow_game()); self.assertEqual((v.selected, v.elements), (selected, els))

    def test_at_bottom_new_message_added_and_choice_follows_last(self):
        v = make_view(n=5); self.assertEqual(v.selected, 4)
        v.J.history.add('Neuf.', 'Alena', 10 ** 6); self.assertTrue(v.follow_game()); place(v)
        self.assertEqual((len(v.elements), v.selected, v.pos), (6, 5, 0.0)); self.assertEqual(v.elements[-1].text, 'Neuf.')
        self.assertFalse(v.follow_game())                                                                              # (puis plus rien a faire)

    def test_at_bottom_choice_elsewhere_does_not_jump(self):
        v = make_view(n=8); v.selected = 3; cur = v.current_item(); self.assertEqual(v.scroll_offset(), 0.0)
        for i in range(2): v.J.history.add('Neuf %d.' % i, None, 10 ** 6 + i * 5000)
        self.assertTrue(v.follow_game()); self.assertEqual(len(v.elements), 10); self.assertIs(v.current_item(), cur); self.assertEqual(v.selected, 3)    # le message choisi reste le meme

    def test_reading_higher_up_list_stays_then_updates_at_bottom(self):
        v = make_view(n=20); v.pos = 400.0; place(v); self.assertGreater(v.scroll_offset(), 0.5); before = list(v.elements); selected = v.selected
        v.J.history.add('Neuf.', None, 10 ** 6)
        self.assertFalse(v.follow_game()); self.assertEqual((v.elements, v.selected), (before, selected))                       # la lecture ne saute pas
        v.pos = 0.0; place(v); self.assertTrue(v.follow_game()); self.assertEqual(len(v.elements), 21)                  # retour en bas : mise a jour

    def test_not_during_sliding(self):
        v = make_view(n=5); v.J.history.add('Neuf.', None, 10 ** 6)
        v.drag = [0.0, 0.0, True]; self.assertFalse(v.follow_game()); v.drag = None; v.dragging_bar = 1.0; self.assertFalse(v.follow_game())
        v.dragging_bar = None; self.assertTrue(v.follow_game())

    def test_battles_tab(self):
        v = make_view(n=3, battles=2); v.change_tab(UH.O_BATTLES); place(v); self.assertEqual(len(v.elements), 2)
        v.J.history.add('Neuf.', None, 10 ** 6); self.assertFalse(v.follow_game())                              # un dialogue ne change pas l'onglet des combats
        v.J.history.add_battle(battle(t=500)); self.assertTrue(v.follow_game()); self.assertEqual((len(v.elements), v.selected), (3, 2))

    def test_full_entries_oldest_leaves_last_enters(self):
        v = make_view(n=5); h = v.J.history; h.dialogues.pop(0); h.add('Neuf.', None, 10 ** 6)                              # (meme longueur : la limite de l'historique)
        self.assertEqual(len(h.dialogues), len(v.elements)); self.assertTrue(v.follow_game()); self.assertEqual(v.elements[-1].text, 'Neuf.')

    def test_favorites_only_does_not_change_with_game(self):
        v = make_view(n=5); v.star(1); v.toggle_filter(); place(v); self.assertEqual(len(v.elements), 1)
        v.J.history.add('Neuf.', None, 10 ** 6); self.assertFalse(v.follow_game()); self.assertEqual(len(v.elements), 1)

    def test_without_history(self):
        v = make_view(n=2); v.J.history = None; self.assertFalse(v.follow_game())

    def test_pause_update_runs_every_frame_on_history_page(self):
        from dq4_pc.menus import pause as PA
        src = inspect.getsource(PA.Pause.do_update)
        self.assertIn("self.hist.follow_game()", src)                          # depuis #187 : seulement quand l'historique est accessible (sinon la page se referme)
        self.assertIn("if self.screen_page == 'historique':", src)


class TestPersistence(unittest.TestCase):
    """Point 2 : les favoris (historique_favoris.json) ET l'etat de la case « Favoris seulement » (reglage historique_favoris_seuls dans reglages.json) survivent a la fermeture et a un nouveau lancement. Fichiers temporaires seulement."""
    def setUp(self):
        self.d = tempfile.mkdtemp(prefix='persist_'); self.addCleanup(shutil.rmtree, self.d, True)
        self.fav = os.path.join(self.d, 'history_favorites.json'); self.rg = os.path.join(self.d, 'settings.json')

    def session(self):
        """Une « session » du jeu : Historique (fichier des favoris), Reglages (reglages.json) et la fenetre d'historique, comme window.py les cree."""
        P = types.SimpleNamespace(mouse_mode=False, mouse_pos=None, back=lambda: None, shutdown=lambda: None, _repeat=lambda *a: None)
        P.J = types.SimpleNamespace(history=new(self.fav), reg=RG.Settings(self.rg), height=720)
        v = UH.HistoryView(P); v.enter(); v.hv0 = 500.0; place(v); return v

    @staticmethod
    def shutdown(v):
        """Fermeture de la visionneuse (Window.on_close) : reglages et favoris ecrits."""
        v.J.reg.store(); v.J.history.store(True)

    def test_key_and_default_value(self):
        self.assertIs(RG.DEFAULT['historique_favoris_seuls'], False); self.assertIn('historique_favoris_seuls', RG.SOUND_TEXT_BOOLEANS)           # (decochee par defaut ; une valeur invalide y revient)
        self.assertIs(RG.Settings(None)['historique_favoris_seuls'], False)
        src = _paths.source('pause.py')
        self.assertNotIn('historique_favoris_seuls', src)                                                         # pas de ligne dans le menu Pause : la case est dans la fenetre elle-meme

    def test_state_stored_on_each_change(self):
        v = self.session(); self.assertFalse(v.favorites_only); self.assertFalse(os.path.exists(self.rg))
        v.key_press(pyglet.window.key.F)                                                                              # coche : ecrit tout de suite, sans attendre la fermeture
        with open(self.rg, encoding='utf-8') as f: self.assertIs(json.load(f)['historique_favoris_seuls'], True)
        v.toggle_filter()
        with open(self.rg, encoding='utf-8') as f: self.assertIs(json.load(f)['historique_favoris_seuls'], False)

    def test_round_trip_settings(self):
        for state in (True, False):
            r = RG.Settings(self.rg); r['vignette'] = 0.8; r['historique_favoris_seuls'] = state; r.store()
            r2 = RG.Settings(self.rg); self.assertIs(r2['historique_favoris_seuls'], state); self.assertEqual(r2['vignette'], 0.8)             # (les autres reglages ne bougent pas)

    def test_invalid_or_absent_values(self):
        for raw_value in ('"oui"', '1', '0', 'null', '[true]', '{"a": 1}'):
            with open(self.rg, 'w', encoding='utf-8') as f: f.write('{"historique_favoris_seuls": %s, "vignette": 0.5}' % raw_value)
            r = RG.Settings(self.rg); self.assertIs(r['historique_favoris_seuls'], False, raw_value); self.assertEqual(r['vignette'], 0.5)
        with open(self.rg, 'w', encoding='utf-8') as f: f.write('{"vignette": 0.5}')                              # fichier d'avant cette cle : decoche
        self.assertIs(RG.Settings(self.rg)['historique_favoris_seuls'], False)
        with open(self.rg, 'w', encoding='utf-8') as f: f.write('pas du json')                                  # illisible : valeurs par defaut, sans erreur
        self.assertIs(RG.Settings(self.rg)['historique_favoris_seuls'], False)

    def test_two_sessions_favorites_and_checkbox(self):
        """Session 1 : un dialogue et un combat en favori, case cochee, fermeture. Session 2 (nouveaux objets, memes fichiers) : la case est cochee a l'ouverture de la fenetre et les favoris sont dans la liste, avec leur etoile."""
        v = self.session(); h = v.J.history
        h.add('Un dialogue.', 'Alena', 100); h.add('Un autre.', None, 900); h.add_battle(battle(t=50)); v.enter()
        v.star(0); v.change_tab(UH.O_BATTLES); v.star(0); v.change_tab(UH.O_DIALOGUES); v.key_press(pyglet.window.key.F); self.assertTrue(v.favorites_only)
        self.shutdown(v)
        v2 = self.session()                                                                                       # nouveau lancement
        self.assertTrue(v2.favorites_only); self.assertEqual([(e.name_str, e.text, e.fav is not None) for e in v2.elements], [('Alena', 'Un dialogue.', True)])
        v2.change_tab(UH.O_BATTLES); self.assertEqual([(e.type, e.outcome, e.fav is not None) for e in v2.elements], [('c', 'victoire', True)])
        v2.key_press(pyglet.window.key.F); self.assertEqual(len(v2.elements), 0)                                       # decochee : la session est vide (le reste de l'historique n'est pas conserve)
        self.shutdown(v2)
        v3 = self.session(); self.assertFalse(v3.favorites_only)                                                   # ... et la case decochee est conservee aussi
        v3.key_press(pyglet.window.key.F); self.assertEqual(len(v3.elements), 1)                                       # les favoris, eux, sont toujours la

    def test_favorites_survive_without_clean_close(self):
        """Les favoris sont ecrits au moment de l'etoile : une fermeture brutale (sans on_close) ne les perd pas."""
        v = self.session(); v.J.history.add('Garde-moi.', 'Roi', 10); v.enter(); v.star(0)
        h2 = new(self.fav); self.assertEqual([(e.name_str, e.text) for e in h2.entries('dialogues', True)], [('Roi', 'Garde-moi.')])

    def test_write_error_does_not_prevent_checking(self):
        v = self.session()
        def breaks(): raise OSError('disque plein')
        v.J.reg.store = breaks
        self.assertTrue(v.toggle_filter()); self.assertTrue(v.favorites_only)
        v.J.reg = None; self.assertFalse(v.toggle_filter())                                                       # (pas de reglages du tout : la case marche quand meme)
        v.enter(); self.assertFalse(v.favorites_only)

    def test_window_rereads_state_on_opening(self):
        v = self.session(); v.J.reg['historique_favoris_seuls'] = True; v.enter(); self.assertTrue(v.favorites_only)


class TestPause(unittest.TestCase):
    """L'historique dans le menu Pause : entree de la racine, ouverture par la touche (page directe), cycle de la touche H, retour, ligne de la page Commandes."""
    def game(self):
        from dq4_pc.menus import pause as PA
        h = new(None); h.add('Bonjour.', 'Alena', 200); h.add_battle(battle())
        self.pauses = []
        J = types.SimpleNamespace(reg=RG.Settings(None), history=h, width=1280, height=720, mouse=None, args=types.SimpleNamespace(cache='/inexistant'),
                                  pause_game=lambda yes: self.pauses.append(yes), sound=types.SimpleNamespace(active=True, listening=False))
        J.reg.store = lambda: None; J.set_fade = lambda v: None; J.set_battle_speed = lambda v: None; J.apply_text = lambda: None          # (la page Commandes porte la section « Défilement du texte »)
        return J, PA.Pause(J)

    def test_h_opens_then_battles_then_closes(self):
        K = pyglet.window.key; J, p = self.game()
        p.open_menu('historique')
        self.assertTrue(p.opened); self.assertEqual((p.screen_page, p.hist.tab, self.pauses), ('historique', UH.O_DIALOGUES, [True]))      # 1er appui : les messages, le moteur est arrete
        self.assertEqual(len(p.hist.elements), 1)
        self.assertTrue(p.key_press(K.H, 0)); self.assertTrue(p.opened); self.assertEqual((p.hist.tab, len(p.hist.elements), p.hist.elements[0].type), (UH.O_BATTLES, 1, 'c'))      # 2e : les combats
        self.assertTrue(p.key_press(K.H, 0)); self.assertFalse(p.opened); self.assertEqual(self.pauses, [True, False])                                                         # 3e : tout est ferme
        p.open_menu('historique'); self.assertEqual(p.hist.tab, UH.O_DIALOGUES)                                                        # (rouvert : de nouveau sur les messages)

    def test_esc_and_other_keys(self):
        K = pyglet.window.key; J, p = self.game()
        p.open_menu('historique'); p.key_press(K.ESCAPE, 0); self.assertFalse(p.opened)                                  # Echap : retour = fermeture (page unique de la pile)
        p.open_menu('historique'); p.key_press(K.B, 0); self.assertTrue(p.opened)                                        # (B n'est « Annuler » que si c'est la touche reglee : ici B n'est pas attribuee)

    def test_menu_entry(self):
        K = pyglet.window.key; J, p = self.game()
        p.open_menu(); e = next(x for x in p._entries() if x['l'] == 'Historique')
        e['ok'](); self.assertEqual(p.screen_page, 'historique'); self.assertEqual(len(p.hist.elements), 1)
        p.key_press(K.BACKSPACE, 0); self.assertEqual(p.screen_page, 'racine'); self.assertTrue(p.opened)                  # retour au menu Pause, pas au jeu
        self.assertEqual(p._entries_history(), [])
        e['ok'](); p.key_press(K.H, 0); p.key_press(K.H, 0); self.assertFalse(p.opened)                                  # depuis le menu : H, H ferme aussi tout le menu

    def test_commands_line(self):
        J, p = self.game(); p.open_menu('commandes')
        e = next(x for x in p._entries() if x.get('act') == 'historique')
        self.assertEqual((e['l'], e['v'][0]), ('Historique', 'H'))

    def test_neither_click_nor_wheel_breaks(self):
        M = pyglet.window.mouse; J, p = self.game(); p.open_menu('historique')
        p.hovered(100, 100); p.click(100, 100, M.LEFT); p.drag_to(100, 120); p.release(100, 120, M.LEFT); p.wheel(1); p.output()
        p.click(100, 100, M.RIGHT); self.assertFalse(p.opened)                                                      # clic droit : retour, comme dans les autres pages


class TestEmptyMessage(unittest.TestCase):
    """#140 : le message de la liste vide (surtout « Aucun dialogue en favori : ... », long) etait dessine sur une seule ligne et depassait du cadre : il est coupe aux espaces."""
    wid = staticmethod(lambda t: 10.0 * len(t))                      # police d'essai : 10 unites par caractere

    def test_no_line_exceeds(self):
        for msg in list(UH.EMPTY_MESSAGES.values()) + list(UH.EMPTY_FAVORITES.values()):
            for limit in (200.0, 400.0, 800.0, 1600.0):
                ls = UH.wrap_words(msg, self.wid, limit)
                self.assertEqual(' '.join(ls).split(), msg.split())                                       # aucun mot perdu ni change
                for l in ls: self.assertLessEqual(self.wid(l), max(limit, max(self.wid(m) for m in msg.split())), (limit, l))

    def test_short_message_stays_on_one_line(self):
        self.assertEqual(UH.wrap_words(UH.EMPTY_MESSAGES['dialogues'], self.wid, 10000.0), [UH.EMPTY_MESSAGES['dialogues']])
        self.assertEqual(UH.wrap_words('', self.wid, 100.0), [''])

    def test_long_message_is_cut(self):
        ls = UH.wrap_words(UH.EMPTY_FAVORITES['dialogues'], self.wid, 600.0); self.assertGreater(len(ls), 1)

    def test_too_wide_word_stays_alone(self):
        self.assertEqual(UH.wrap_words('a ABCDEFGHIJ b', self.wid, 50.0), ['a', 'ABCDEFGHIJ', 'b'])

    def test_drawing_cuts_the_message(self):
        src = _paths.source('ui_history.py')
        self.assertIn('wrap_words(msg,', src)                                                              # la liste vide passe par la coupure (plus de ligne unique)


if __name__ == '__main__':
    unittest.main(verbosity=1)
