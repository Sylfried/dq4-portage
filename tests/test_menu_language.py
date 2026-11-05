"""Version anglaise de l'outil (D-238), lot « menus » : tout ce que l'outil ecrit lui-meme hors des pages Parametres, en anglais puis en francais, avec de faux objets (ni fenetre, ni moteur, ni GL).

  - ecran Sauvegardes (menu de depart) : titre, boutons, explications, messages de resultat d'un export / import (reussi, annule, ignores, echec), boites de dialogue de fichiers (titres, filtres) ;
  - fenetre Historique : titre, onglets, case « Favoris seulement », aide, listes vides, entete et lignes d'un combat (textes que l'outil compose autour de ceux du jeu), favori dont le message manque ;
  - saisie du nom, licence (titre ; le texte d'origine du jeu et le « Privacy Policy » ne changent pas), noms des elements de l'editeur d'interface, textes d'essai des dialogues, infos F1, notifications,
    lieu des etats instantanes, messages de la console de ces modules ;
  - en anglais : aucun mot francais ne reste (hors la liste blanche, courte et justifiee) ; en francais : exactement les textes d'avant ;
  - le catalogue (texts_en\\menus.py) n'a pas d'entree orpheline.
Les regles generales du catalogue (memes trous, memes bords, pas de francais dans l'anglais, pas de doublon, tout `tr('...')` / `N_('...')` du code a sa traduction) sont dans tests/test_language.py.

    python3 tests/test_menu_language.py"""
import ast, contextlib, io, json, os, shutil, sys, tempfile, types, unittest, zipfile
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..')
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)
import _paths          # (aide des tests : retrouver le code source dans les sous-dossiers de dq4_pc)
import pyglet
pyglet.options['shadow_window'] = False                     # (pas d'affichage necessaire : on ne dessine rien)
from dq4_pc import paths as CH
from dq4_pc import language as LG
from dq4_pc.battle import battle_history as HC
from dq4_pc.window import menu_display as AM
from dq4_pc.window import snapshots as IN
from dq4_pc.window import title_screen as TI
from dq4_pc.menus import pre_game as AP
from dq4_pc.menus import saves_screen as ES
from dq4_pc.menus import hud_mobile as HM
from dq4_pc.menus import pause as PA
from dq4_pc.menus import name_entry as SN
from dq4_pc.menus import ui_history as UH
from dq4_pc.menus import ui_menu as UM
from dq4_pc.core import history as HI
from dq4_pc.persistence import logfile_format as FJ
from dq4_pc.persistence import settings as RG
from dq4_pc.persistence import saves as S
from test_language import french, catalog_by_file
import test_saves_import as TIS
import test_history_key as THC

LG.select_language('fr')          # (la langue de l'ordinateur ne compte pas ici : chaque test choisit la sienne)


def entry(): LG.select_language('en')


class Language(unittest.TestCase):
    """Chaque test choisit sa langue ; on revient au francais a la fin (les autres tests ont des attentes francaises)."""
    def setUp(self): LG.select_language('fr')
    def tearDown(self): LG.select_language('fr')

    def assert_no_french(self, texts, whitelist=()):
        """Aucun des `texts` ne contient de francais (hors `whitelist` : textes du jeu, noms propres), et il y en a."""
        texts = [t for t in texts if t not in whitelist]
        self.assertTrue(texts)
        for t in texts: self.assertFalse(french(t), 'reste du francais : %r' % (t,))


# ---------------------------------------------------------------------------------------------------------------------------------- faux objets
class FakeLabel:
    """Faux pyglet.text.Label : memorise le texte et le releve quand il est dessine."""
    def __init__(self, J, text): self.J = J; self.text = text; self.content_width = 5.0 * len(text); self.content_height = 12.0; self.x = self.y = 0.0
    def draw(self): self.J.dessines.append(self.text)


class FakeGame(types.SimpleNamespace):
    """Ce que les ecrans demandent a la fenetre : `_lbl` (fait les etiquettes), `pause` (les pages), taille, peripherique."""
    def __init__(self, **kw):
        super().__init__(width=1280, height=720, dessines=[], last_device='clavier', **kw)
        self.pause = fake_pause(self)

    def _lbl(self, text, size_value, color=None, fonts=()): return FakeLabel(self, text)


def fake_pause(J):
    """La page-outil `Pause` sans ses dessins : `_label` est la vraie (elle traduit), le reste ne fait rien."""
    P = mock.MagicMock()
    P.J = J; P._pol = (); P.mouse_mode = False; P.mouse_pos = None
    P._label = lambda text, size_value, color=(255, 255, 255, 255): PA.Pause._label(P, text, size_value, color)
    P._hovered = lambda z: False; P._pointer_in = lambda z: False; P._scroll_bar = lambda *a, **k: None
    return P


@contextlib.contextmanager
def without_screen(*modules):
    """Pas de GL : `gl` des modules et les formes de pyglet.shapes sont remplaces par des objets muets."""
    with contextlib.ExitStack() as st:
        for m in modules:
            if hasattr(m, 'gl'): st.enter_context(mock.patch.object(m, 'gl', mock.MagicMock()))
        for name_str in ('Rectangle', 'BorderedRectangle', 'Star', 'Line', 'Box', 'Triangle'): st.enter_context(mock.patch('pyglet.shapes.' + name_str, mock.MagicMock()))
        for name_str in ('glDisable', 'glEnable', 'glBlendFunc'): st.enter_context(mock.patch('pyglet.gl.' + name_str, mock.MagicMock()))
        yield


# ---------------------------------------------------------------------------------------------------------------------------------- ecran Sauvegardes : messages de resultat
class FakeDialogue:
    """Remplace S.Dialogue (tkinter) : memorise ce qu'on lui demande."""
    calls = []
    def __init__(self, mode, title_screen, initial_folder=None, initial_name=None):
        self.result = None; self.unavailable = False; FakeDialogue.calls.append((mode, title_screen))


class Saves(Language):
    def setUp(self):
        super().setUp()
        self.t = tempfile.mkdtemp(prefix='lm_sauv_'); self.addCleanup(shutil.rmtree, self.t, True)
        self.d = CH.Folders(self.t, env={}); before = CH.FOLDERS; CH.FOLDERS = self.d; self.addCleanup(setattr, CH, 'DOSSIERS', before)
        self.wdir, self.rdir = self.d.portage, self.d.mobile
        self.zip = os.path.join(self.t, 'i.zip')
        eng = types.SimpleNamespace(reread_savefiles=lambda: 'nouveau', initial_buttons_state=lambda x: x)
        self.J = FakeGame(args=types.SimpleNamespace(saves_write=self.wdir, saves_read=self.rdir), engine=eng, initial_status='ancien')
        self.e = ES.SavesScreen(self.J)

    def make_zip(self, **files):
        with zipfile.ZipFile(self.zip, 'w') as z:
            for name_str, d in files.items(): z.writestr(name_str.replace('__', '/'), d)

    def answer(self, action, result, unavailable=False):
        self.e.dialogue = types.SimpleNamespace(result=result, unavailable=unavailable); self.e.action = action; self.e.do_update()
        return list(self.e.msg)

    def dataset(self):
        TIS.write(os.path.join(self.wdir, 'data1.dat'), TIS.logfile(1)); TIS.write(os.path.join(self.wdir, 'data2.dat'), TIS.logfile(2))
        TIS.write(os.path.join(CH.FOLDERS.savestates_folder(self.wdir), 'state_01.dqs'), b'x' * 2000)

    # -- ce que les boutons demandent
    def test_dialog_boxes_opening(self):
        for language, titles, msgs in (('fr', ('Exporter les sauvegardes', 'Importer des sauvegardes'),
                                      ["Choisis où enregistrer le fichier dans la fenêtre qui vient de s'ouvrir…", "Choisis le .zip ou les fichiers de sauvegarde dans la fenêtre qui vient de s'ouvrir…"]),
                                     ('en', ('Export saves', 'Import saves'), ['Choose where to save the file in the window that just opened…', 'Choose the .zip or the save files in the window that just opened…'])):
            LG.select_language(language); FakeDialogue.calls = []
            with mock.patch.object(S, 'Dialogue', FakeDialogue):
                e = ES.SavesScreen(self.J); e.export_saves(); m1 = list(e.msg); e.dialogue = None; e.import_saves(); m2 = list(e.msg)
            self.assertEqual(FakeDialogue.calls, [('enregistrer', titles[0]), ('ouvrir', titles[1])], language); self.assertEqual([m1, m2], [[msgs[0]], [msgs[1]]], language)

    def test_file_dialog_filters(self):
        """Les filtres du « Enregistrer sous » / « Ouvrir » (tkinter) : memes motifs, libelles traduits."""
        seen = []
        class FakeFiledialog:
            @staticmethod
            def asksaveasfilename(**kw): seen.append(kw['filetypes']); return ''
            @staticmethod
            def askopenfilenames(**kw): seen.append(kw['filetypes']); return ()
        class FakeTk:
            def withdraw(self): pass
            def attributes(self, *a): pass
            def destroy(self): pass
        fake_tk = types.SimpleNamespace(Tk=FakeTk, filedialog=FakeFiledialog)
        for language, att in (('fr', [[('Archive zip', '*.zip')], [('Sauvegardes (zip, data*.dat, state_*.dqs)', '*.zip *.dat *.dqs'), ('Tous les fichiers', '*.*')]]),
                            ('en', [[('Zip archive', '*.zip')], [('Saves (zip, data*.dat, state_*.dqs)', '*.zip *.dat *.dqs'), ('All files', '*.*')]])):
            LG.select_language(language); seen.clear()
            with mock.patch.dict(sys.modules, {'tkinter': fake_tk, 'tkinter.filedialog': FakeFiledialog}), mock.patch.object(fake_tk, 'filedialog', FakeFiledialog, create=True):
                for mode in ('enregistrer', 'ouvrir'):
                    d = S.Dialogue.__new__(S.Dialogue); d.result = None; d.unavailable = False; d.error = None; d._body(mode, 'titre', None, None)
            self.assertEqual(seen, att, language)

    # -- export
    def test_export_cancelled_successful_and_empty(self):
        self.dataset(); path = os.path.join(self.t, 'sortie', 'sauv.zip')
        for language, canceled, ok, empty in (('fr', 'Export annulé.', 'Exporté : 2 fichiers de sauvegarde et 1 état instantané.', 'Impossible : Aucune sauvegarde a exporter (ni journal, ni etat instantane).'),
                                         ('en', 'Export canceled.', 'Exported: 2 save files and 1 save state.', 'Failed: Nothing to export (no adventure log, no save state).')):
            LG.select_language(language); e = self.e = ES.SavesScreen(self.J)
            self.assertEqual(self.answer('export', []), [canceled], language); self.assertEqual(e.msg_clr, ES.HELPTEXT)
            self.assertEqual(self.answer('export', [path]), [ok, path], language); self.assertEqual(e.msg_clr, ES.GREEN)
            self.J.args.saves_write = os.path.join(self.t, 'rien'); self.J.args.saves_read = os.path.join(self.t, 'rien2')
            self.assertEqual(self.answer('export', [os.path.join(self.t, 'x.zip')]), [empty], language); self.assertEqual(e.msg_clr, ES.RED)
            self.J.args.saves_write, self.J.args.saves_read = self.wdir, self.rdir

    def test_a_single_file_and_a_single_state(self):
        TIS.write(os.path.join(self.wdir, 'data1.dat'), TIS.logfile(1)); TIS.write(os.path.join(CH.FOLDERS.savestates_folder(self.wdir), 'state_01.dqs'), b'x' * 2000)
        for language, att in (('fr', 'Exporté : 1 fichier de sauvegarde et 1 état instantané.'), ('en', 'Exported: 1 save file and 1 save state.')):
            LG.select_language(language); self.assertEqual(self.answer('export', [os.path.join(self.t, language + '.zip')])[0], att)

    # -- import
    def test_import_cancelled(self):
        for language, att in (('fr', 'Import annulé.'), ('en', 'Import canceled.')):
            LG.select_language(language); self.assertEqual(self.answer('import', []), [att], language)

    def test_successful_import_with_copy_and_ignored_file(self):
        for language, ligne1, copied, ignores, do_update in (('fr', 'Importé : 1 fichier de sauvegarde et 0 état instantané.', 'Anciens fichiers copiés dans : ', 'Ignorés : data2.dat : fichier abime (somme de controle incorrecte) (i.zip)',
                                                     'Pour mettre à jour les boutons grisés du menu de départ, relance le jeu.'),
                                                    ('en', 'Imported: 1 save file and 0 save states.', 'Previous files copied to: ', 'Skipped: data2.dat: damaged file (checksum mismatch) (i.zip)',
                                                     'To update the grayed-out buttons of the start menu, restart the game.')):
            LG.select_language(language); shutil.rmtree(self.wdir, ignore_errors=True); self.e = ES.SavesScreen(self.J)
            TIS.write(os.path.join(self.wdir, 'data1.dat'), TIS.logfile(1)); bad = bytearray(TIS.logfile(3)); bad[100] ^= 1
            self.make_zip(**{'data1.dat': TIS.logfile(2), 'data2.dat': bytes(bad)})
            lines = self.answer('import', [self.zip])
            self.assertEqual(len(lines), 4, language); self.assertEqual(lines[0], ligne1, language); self.assertTrue(lines[1].startswith(copied) and 'before_import_' in lines[1], lines[1])
            self.assertEqual((lines[2], lines[3]), (ignores, do_update), language); self.assertEqual(self.e.msg_clr, ES.GREEN); self.assertTrue(self.e.needs_reload)

    def test_import_without_dialog_box(self):
        os.makedirs(os.path.join(self.wdir, 'import'), exist_ok=True)
        for language, att in (('fr', ['Pas de boîte de dialogue disponible : dépose tes fichiers (.zip, data1.dat…) dans', os.path.join(self.wdir, 'import'), 'puis clique de nouveau sur Importer.']),
                            ('en', ['No file dialog available: put your files (.zip, data1.dat…) in', os.path.join(self.wdir, 'import'), 'then click Import again.'])):
            LG.select_language(language)
            with mock.patch.object(os, 'startfile', create=True):
                self.assertEqual(self.answer('import', [], unavailable=True), att, language)
            self.assertEqual(self.e.msg_clr, ES.RED)

    def test_import_impossible(self):
        empty_zip = lambda: self.make_zip(**{'lisez_moi.txt': b'rien'})
        fake_zip = os.path.join(self.t, 'z.zip'); TIS.write(fake_zip, b'pas un zip')
        small = os.path.join(self.t, 'state_01.dqs'); TIS.write(small, b'x')
        short = os.path.join(self.t, 'data1.dat'); TIS.write(short, b'abc')
        att = {'fr': ('Impossible : Aucun fichier de sauvegarde reconnu (data1.dat a data5.dat, data9.dat ou savestates/state_NN.dqs attendus).',
                      "Impossible : Aucun fichier de sauvegarde reconnu (z.zip : ce n'est pas un .zip valide).",
                      'Impossible : Aucun fichier de sauvegarde reconnu (state_01.dqs : fichier trop petit (%s)).',
                      'Impossible : Aucun fichier de sauvegarde reconnu (data1.dat : taille 3 au lieu de 15360 (%s)).'),
               'en': ('Failed: No save file recognized (expected data1.dat to data5.dat, data9.dat or savestates/state_NN.dqs).',
                      'Failed: No save file recognized (z.zip: not a valid .zip file).',
                      'Failed: No save file recognized (state_01.dqs: file too small (%s)).',
                      'Failed: No save file recognized (data1.dat: size 3 instead of 15360 (%s)).')}
        for language in ('fr', 'en'):
            LG.select_language(language); nothing, bad_zip, too_small, size_value = att[language]
            empty_zip(); self.assertEqual(self.answer('import', [self.zip]), [nothing], language)
            self.assertEqual(self.answer('import', [fake_zip]), [bad_zip], language)
            self.assertEqual(self.answer('import', [small]), [too_small % self.t], language); self.assertEqual(self.answer('import', [short]), [size_value % self.t], language)
            self.assertEqual(self.e.msg_clr, ES.RED)

    def test_refused_savefile_says_why(self):
        for language, junk, damaged in (('fr', "ce n'est pas un journal du jeu (en-tete inconnu)", 'fichier abime (somme de controle incorrecte)'),
                                     ('en', 'not a game adventure log (unknown header)', 'damaged file (checksum mismatch)')):
            LG.select_language(language); j = bytearray(TIS.logfile(1)); j[0x500] ^= 1
            self.assertEqual(FJ.check('data1.dat', bytes(j)), damaged, language); self.assertEqual(FJ.check('data1.dat', bytes(range(256)) * 60), junk, language)

    def test_write_not_possible(self):
        TIS.write(self.zip, b'')
        self.make_zip(**{'data1.dat': TIS.logfile(2)})
        for language, att in (('fr', "Impossible : Aucun fichier n'a pu etre ecrit (data1.dat : ecriture impossible (disque) ; le fichier actuel est inchange)."),
                            ('en', 'Failed: No file could be written (data1.dat: could not be written (disque); the current file is unchanged).')):
            LG.select_language(language)
            with mock.patch.object(S, 'atomic_write', lambda path, raw, **kw: 'disque'):
                self.assertEqual(self.answer('import', [self.zip]), [att], language)

    # -- dessin de l'ecran
    def test_screen_drawing(self):
        explanation = {'fr': ['Exporter : enregistre tes journaux (data1 à data5, data9) et tes états instantanés dans un fichier .zip.',
                              'Importer : lit un .zip de ce genre, ou des fichiers data1.dat, data2.dat… (par exemple copiés depuis un téléphone Android).',
                              "Les fichiers remplacés sont d'abord copiés dans le dossier « before_import_… » de tes sauvegardes."],
                       'en': ['Export: saves your adventure logs (data1 to data5, data9) and your save states into a .zip file.',
                              'Import: reads a .zip like that, or data1.dat, data2.dat… files (for example copied from an Android phone).',
                              'Replaced files are first copied to the "before_import_…" folder in your saves folder.']}
        titles = {'fr': ('Sauvegardes', 'Exporter', 'Importer'), 'en': ('Saves', 'Export', 'Import')}
        for language in ('fr', 'en'):
            LG.select_language(language); J = FakeGame(); e = ES.SavesScreen(J); e._say(['Un message.'], ES.GREEN)
            with without_screen(ES): e.draw_all(J, 640.0, 360.0, 2.0)
            self.assertEqual(J.dessines, [titles[language][0]] + explanation[language] + [titles[language][1], titles[language][2], 'Un message.'], language)
        self.assert_no_french(J.dessines, whitelist=('Un message.',))

    def test_explanation_translated_in_full_before_being_cut(self):
        """Fenetre etroite : les phrases d'aide passent sur plusieurs lignes. L'anglais n'a pas le meme ordre des mots : la phrase est traduite
        d'un bloc PUIS coupee (sinon les morceaux francais n'ont pas de traduction et restent en francais)."""
        for language in ('fr', 'en'):
            LG.select_language(language); J = FakeGame(); e = ES.SavesScreen(J)
            with without_screen(ES): e.draw_all(J, 640.0, 360.0, 0.4)
            lines = J.dessines[1:-2]                                                  # (sans le titre ni les deux boutons)
            self.assertGreater(len(lines), len(ES.EXPLANATION), 'la fenetre doit etre assez etroite pour couper les phrases')
            recolle = ' '.join(lines)
            for phrase in ES.EXPLANATION: self.assertIn(LG.tr(phrase), recolle, language)
            if language == 'en': self.assert_no_french(lines, whitelist=('before_import_…',))

    def test_start_menu_button(self):
        """Le portage pose son bouton « Sauvegardes » dans le menu de depart (a la place de « Sauv. cloud »)."""
        ml = types.SimpleNamespace(types={'53': {'nodes': [], 'parts': [], 'params': [], 'codes': [], 'name': 'Make_StartMenuSecond'}})
        for language, att in (('fr', 'Sauvegardes'), ('en', 'Saves')):
            LG.select_language(language)
            with mock.patch.object(UM.Window, 'param_str') as ps: UM.Window(ml, 53)
            self.assertEqual([c.args for c in ps.call_args_list], [(5, 0, att)], language)


# ---------------------------------------------------------------------------------------------------------------------------------- historique
def test_history():
    """Dialogues et combats d'essai (textes neutres : les noms et les dialogues sont ceux du jeu, jamais traduits)."""
    h = HI.History(None, lambda: 1000.0)
    h.add('Hello there.', 'Alena', 200); h.add('Welcome.', None, 5200)
    for i in range(1, 7):
        h.add_battle({'t': 100 * i, 'issue': ('victoire', 'fuite', 'defaite')[i % 3], 'or': 21, 'xp': 38,
                          'ennemis': [{'nom': 'Slime', 'total': 3, 'vaincus': 3}, {'nom': 'Golem', 'total': 2, 'vaincus': 1}], 'objets': [{'nom': 'Medicinal herb'}, {'nom': 'Life stone'}]})
    return h


class FakeBitmapFont:
    """Police bitmap du jeu : seulement ce que dessiner() lui demande."""
    ascent = 18.0; leading = 24.0; PAD = 0.0
    def width_px(self, text): return 6.0 * len(text)


class History(Language):
    def make_view(self, h, tab=UH.O_DIALOGUES, favorites_only=False, with_font=True):
        J = FakeGame(history=h, reg=RG.Settings(None))
        if with_font: J.ui_render = types.SimpleNamespace(texts=types.SimpleNamespace(bitmap=FakeBitmapFont(), messages=None), ml=None, plate=lambda *a, **k: True, draw_all=lambda *a, **k: None)
        J.reg['historique_favoris_seuls'] = favorites_only
        v = UH.HistoryView(J.pause); v.enter(tab); v.rec = []
        v._line = lambda bm, text, x, y, sc, clr, size_value: v.rec.append(text)                    # (la ligne de texte : police bitmap du jeu ou du systeme)
        return v

    def draw_all(self, v):
        with without_screen(UH), mock.patch.object(UH, 'HM', mock.MagicMock()): v.draw_all()
        return v.rec

    # -- l'entete, les onglets, l'aide
    def test_window_border(self):
        h = test_history()
        att = {'fr': ('Historique', ('Dialogues', 'Combats'), 'Favoris seulement',
                      ['Haut / Bas : message précédent / suivant', 'Molette : défiler', 'Gauche / Droite : onglet', 'Entrée : favori ★', 'F : favoris seulement', 'H : suite', 'Échap : fermer']),
               'en': ('History', ('Dialogue', 'Battles'), 'Favorites only',
                      ['Up / Down: previous / next message', 'Mouse wheel: scroll', 'Left / Right: tab', 'Enter: favorite ★', 'F: favorites only', 'H: next', 'Esc: close'])}
        for language in ('fr', 'en'):
            LG.select_language(language); title_screen, tabs, sieve, helptext = att[language]
            for with_font in (True, False):                                                                  # (police bitmap du jeu, ou repli sur la police du systeme)
                rec = self.draw_all(self.make_view(h, with_font=with_font)); helptext_view = ' | '.join(rec)
                self.assertIn(title_screen, rec); self.assertEqual([t for t in rec if t in tabs], list(tabs)); self.assertIn(sieve, rec)
                for line in helptext: self.assertIn(line, helptext_view, (language, line))
        self.assert_no_french([t for t in rec if t not in ('Alena',)])

    def test_helptext_without_history_key(self):
        """Quand la touche de l'historique est retiree, la ligne « H : suite » disparait (comme avant)."""
        h = test_history()
        for language, line in (('fr', 'H : suite'), ('en', 'H: next')):
            LG.select_language(language); v = self.make_view(h); self.assertIn(line, ' | '.join(self.draw_all(v)))
            v = self.make_view(h); v.J.reg['touches']['historique'] = [None, None]; self.assertNotIn(line, ' | '.join(self.draw_all(v)))

    def test_empty_entries_texts(self):
        h = HI.History(None, lambda: 1000.0)
        att = {('fr', False, UH.O_DIALOGUES): "Aucun dialogue pour l'instant.", ('fr', False, UH.O_BATTLES): "Aucun combat pour l'instant.",
               ('fr', True, UH.O_DIALOGUES): 'Aucun dialogue en favori : décoche « Favoris seulement », choisis un dialogue et appuie sur Entrée (ou clique son étoile) pour le garder.',
               ('fr', True, UH.O_BATTLES): 'Aucun combat en favori : décoche « Favoris seulement », choisis un combat et appuie sur Entrée (ou clique son étoile) pour le garder.',
               ('en', False, UH.O_DIALOGUES): 'No dialogue yet.', ('en', False, UH.O_BATTLES): 'No battle yet.',
               ('en', True, UH.O_DIALOGUES): 'No favorite dialogue: uncheck "Favorites only", choose a dialogue and press Enter (or click its star) to keep it.',
               ('en', True, UH.O_BATTLES): 'No favorite battle: uncheck "Favorites only", choose a battle and press Enter (or click its star) to keep it.'}
        for (language, fav, tab), msg in att.items():
            LG.select_language(language); rec = self.draw_all(self.make_view(h, tab, fav))
            self.assertIn(msg, ' '.join(rec), (language, fav, tab))                       # (le message, coupe en lignes aux espaces : les lignes mises bout a bout le redonnent)
            if language == 'en': self.assert_no_french(rec)

    # -- un combat : entete (issue), lignes composees autour des noms du jeu
    def test_battle_header_and_lines(self):
        h = test_history()
        att = {'fr': (('Victoire', 'Fuite', 'Défaite'), 'Slime ×3', 'Golem ×2 : 1 vaincu, 1 resté', 'Or : 21\u00a0\u00a0\u00a0\u00a0\u00a0Expérience : 38', 'Objets : Medicinal herb, Life stone'),
               'en': (('Victory', 'Escaped', 'Defeat'), 'Slime ×3', 'Golem ×2: 1 defeated, 1 remained', 'Gold: 21\u00a0\u00a0\u00a0\u00a0\u00a0Experience: 38', 'Items: Medicinal herb, Life stone')}
        for language in ('fr', 'en'):
            LG.select_language(language); rec = self.draw_all(self.make_view(h, UH.O_BATTLES)); outcomes = att[language][0]
            for t in outcomes: self.assertIn(t, rec, (language, t))                              # (l'entete de chaque boite : l'issue du combat)
            for t in att[language][1:]: self.assertIn(t, rec, (language, t))                     # (les noms de Slime, Golem, objets : ceux du jeu, jamais traduits)
        self.assert_no_french(rec)

    def test_battle_lines_all_outcomes(self):
        factory = lambda **kw: HI.battle_element(1, dict({'t': 5, 'issue': 'victoire', 'or': 0, 'xp': 0, 'ennemis': []}, **kw))
        def name_str(**kw): return {'nom': 'Bat', 'total': 1, 'vaincus': 0, **kw}
        scenario = [factory(issue='defaite'),                                                                                           # aucun ennemi connu
               factory(issue='fuite', ennemis=[name_str(fuis=1)]), factory(issue='fuite', ennemis=[name_str(disparus=1)]), factory(issue='fuite', ennemis=[name_str()]),
               factory(issue='fuite', ennemis=[{'nom': 'Golem', 'total': 5, 'vaincus': 2, 'fuis': 1, 'disparus': 1}]),
               factory(issue='fuite', ennemis=[{'nom': 'Golem', 'total': 5, 'vaincus': 1, 'fuis': 2, 'disparus': 2}]),
               factory(**{'or': 3, 'xp': 4})]                                                                                   # victoire sans ennemi connu
        att = {'fr': [['Ennemis inconnus'], ['Bat : enfui'], ['Bat : disparu'], ['Bat : resté'], ['Golem ×5 : 2 vaincus, 1 enfui, 1 disparu, 1 resté'], ['Golem ×5 : 1 vaincu, 2 enfuis, 2 disparus'],
                      ['Ennemis inconnus', 'Or : 3\u00a0\u00a0\u00a0\u00a0\u00a0Expérience : 4']],
               'en': [['Unknown enemies'], ['Bat: fled'], ['Bat: vanished'], ['Bat: remained'], ['Golem ×5: 2 defeated, 1 fled, 1 vanished, 1 remained'], ['Golem ×5: 1 defeated, 2 fled, 2 vanished'],
                      ['Unknown enemies', 'Gold: 3\u00a0\u00a0\u00a0\u00a0\u00a0Experience: 4']]}
        for language in ('fr', 'en'):
            LG.select_language(language); self.assertEqual([HI.battle_lines(c) for c in scenario], att[language], language)
        self.assert_no_french([l for ls in att['en'] for l in ls])

    def test_outcome_labels(self):
        for language, att in (('fr', {'victoire': 'Victoire', 'fuite': 'Fuite', 'defaite': 'Défaite'}), ('en', {'victoire': 'Victory', 'fuite': 'Escaped', 'defaite': 'Defeat'})):
            LG.select_language(language); self.assertEqual({k: LG.tr(v) for k, v in HI.OUTCOME_CAPTION.items()}, att, language)

    def test_replacement_names_when_engine_does_not_respond(self):
        for language, monster, item in (('fr', 'Monstre', 'Objet n°12'), ('en', 'Monster', 'Item #12')):
            LG.select_language(language)
            s = HC.Tracking(); s.dead(4, 7); self.assertEqual(s.enemies()[0]['nom'], monster, language)
            c = types.SimpleNamespace(_item_names={}, _engine_text=lambda kind, number: None); self.assertEqual(HC.BattleSensor._item_name(c, 12), item, language)

    def test_favorite_whose_message_is_missing(self):
        class Folder(THC.Base): pass
        b = Folder(); b.setUp()
        try:
            h = b.hist({802199: THC.RAW_SIMPLE}); h.toggle_favorite(h.add(HI.clean(THC.RAW_SIMPLE), None, 1, 802199))
            for language, att in (('fr', '(Message introuvable dans les fichiers du jeu : b0802000#199)'), ('en', '(Message not found in the game files: b0802000#199)')):
                LG.select_language(language); self.assertEqual(b.hist({}).favorites[0].text, att, language)
        finally: b.tearDown()

    # -- la console
    def test_console_messages(self):
        t = tempfile.mkdtemp(prefix='lm_hist_'); self.addCleanup(shutil.rmtree, t, True)
        def output(f):
            buffer = io.StringIO()
            with contextlib.redirect_stdout(buffer): f()
            return buffer.getvalue()
        for language, unreadable, not_written in (('fr', "Favoris de l'historique illisibles (", "Favoris de l'historique non enregistres : "), ('en', 'History favorites unreadable (', 'History favorites not saved: ')):
            LG.select_language(language)
            p = os.path.join(t, 'fav_%s.json' % language)
            with open(p, 'w', encoding='utf-8') as f: f.write('{pas du json')
            s = output(lambda: HI.History(p, lambda: 1.0)); self.assertTrue(s.startswith(unreadable), (language, s)); self.assertTrue(os.path.exists(p + '.corrompu'))
            block = os.path.join(t, 'un_fichier_%s' % language)
            with open(block, 'w') as f: f.write('x')
            h = HI.History(os.path.join(block, 'fav.json'), lambda: 1.0); h.add('Hello.', None, 1); h._dirty = True
            s = output(lambda: h.store(True)); self.assertTrue(s.startswith(not_written), (language, s))
        def refus(sym): raise OSError('pas de symbole')
        for language, sensor, battle in (('fr', 'Historique : crochets non installes (', 'Historique des combats : '), ('en', 'History: hooks not installed (', 'Battle history: ')):
            LG.select_language(language)
            engine = types.SimpleNamespace(core=types.SimpleNamespace(export=refus))
            s = output(lambda: HI.Sensor(engine)); self.assertTrue(s.startswith(sensor), (language, s))
            s = output(lambda: HC.BattleSensor(engine)); self.assertTrue(s.startswith(battle + ('crochets non installes (' if language == 'fr' else 'hooks not installed (')), (language, s))
            engine = types.SimpleNamespace(core=types.SimpleNamespace(export=lambda sym: 0))                          # un moteur sans les symboles attendus
            s = output(lambda: HC.BattleSensor(engine)); self.assertTrue(s.startswith(battle), (language, s)); self.assertFalse(french(s) and language == 'en', s)


# ---------------------------------------------------------------------------------------------------------------------------------- saisie du nom, licence, editeur d'interface, notifications...
class Other(Language):
    def test_name_entry(self):
        functions = list(SN.FUNCTIONS)
        for language, att in (('fr', ['Saisir un nom', 'Clavier : taper le nom', 'Entrée : valider · Échap : retour']), ('en', ['Enter a name', 'Keyboard: type the name', 'Enter: confirm · Esc: back'])):
            LG.select_language(language); J = FakeGame(); s = SN.NameEntry(J); s.open_menu(8)
            with without_screen(SN): s.draw_all(640.0, 360.0, 1.6)
            self.assertIn(att[0], J.dessines); self.assertIn(att[1], J.dessines); self.assertIn(att[2], J.dessines)
            self.assertEqual([t for t in J.dessines if t in functions], functions, language)                    # (les libelles des boutons de fonction viennent du jeu : non traduits)
        self.assert_no_french(J.dessines, whitelist=('à À',))                                                         # liste blanche : « à À » = le libelle du jeu (C_ALPHABET_ETC) du bouton de la page des lettres accentuees

    def test_license(self):
        for language, title_screen in (('fr', 'Licence'), ('en', 'License')):
            LG.select_language(language); J = FakeGame(); lic = AP.License(None)
            lay = types.SimpleNamespace(content_height=1000.0, height=500.0, x=0, y=0, view_y=0, draw=lambda: None)
            lic._layout = lambda J, ui_scale: lay
            with without_screen(): lic.draw_all(J, 640.0, 360.0, 1.5)
            self.assertEqual(J.dessines, [title_screen, 'Privacy Policy'], language)                                    # « Privacy Policy » : le texte du jeu
        # le texte d'en-tete du portage est deja en anglais, la liste d'origine suit : rien de tout cela ne depend de la langue
        for language in ('fr', 'en'):
            LG.select_language(language); self.assertEqual(AP.License(None).text.replace('\n', ' ').count('This is an unofficial'), 1)
        self.assertFalse(french(AP.PROJECT_LICENSE))

    def test_interface_editor_element_names(self):
        att = {'fr': {'carte': 'Carte', 'menu': 'Commandes', 'discussion': 'Discussion', HM.BATTLE: 'Vitesse de combat', HM.DPAD: 'Croix'},
               'en': {'carte': 'Map', 'menu': 'Controls', 'discussion': 'Talk', HM.BATTLE: 'Battle speed', HM.DPAD: 'D-pad'}}
        for language in ('fr', 'en'):
            LG.select_language(language); self.assertEqual({k: LG.tr(v) for k, v in HM.CAPTION.items()}, att[language], language)
            J = FakeGame(reg=RG.Settings(None), engine=types.SimpleNamespace(dpad_size=lambda: 1)); b = HM.Buttons(J)
            with without_screen(HM), mock.patch.object(HM, 'border'), mock.patch.object(HM, 'draw_grid'), mock.patch.object(b, '_plate', return_value=True), mock.patch.object(b, '_sprite', return_value=(mock.MagicMock(), 1)), \
                    mock.patch.object(b, '_battle_arrows'), mock.patch.object(b, '_dpad'):
                b.draw_all(list(HM.BUTTONS) + [HM.DPAD], editing=True)
            self.assertEqual(sorted(J.dessines), sorted(att[language].values()), language)                         # (en edition, chaque element porte son nom)

    def test_sample_texts_of_the_dialogues(self):
        """Chaque ligne d'essai de l'editeur est traduite, et c'est la ligne traduite qui est ecrite dans le canevas."""
        for language in ('fr', 'en'):
            LG.select_language(language); written_items = []
            drawing = mock.MagicMock(); drawing.text = lambda xy, t, **kw: written_items.append(t)
            j = types.SimpleNamespace(SAMPLE_TEXTS=AM.MenusMixin.SAMPLE_TEXTS, SAMPLE_HEIGHT=AM.MenusMixin.SAMPLE_HEIGHT, args=types.SimpleNamespace(cache='/inexistant'), _trial=1, new_sample=lambda: None)
            with mock.patch('PIL.ImageDraw.Draw', return_value=drawing): AM.MenusMixin._preview_canvas(j)
            self.assertEqual(written_items, [LG.tr(t) for t in AM.MenusMixin.SAMPLE_TEXTS[1]], language)
            if language == 'en': self.assertEqual(written_items, ['This is a test text.', 'It is used to adjust the size and', 'position of the dialogue boxes.'])
        entry(); self.assert_no_french([LG.tr(t) for lines in AM.MenusMixin.SAMPLE_TEXTS for t in lines])                    # (tous les textes d'essai, pas seulement celui du test)

    def test_f1_info(self):
        att = {'fr': '50 images/s | moteur 1.0 pas/s (5.0 ms) | pire image 20 ms | dessin Python 3.0 ms', 'en': '50 frames/s | engine 1.0 steps/s (5.0 ms) | worst frame 20 ms | Python drawing 3.0 ms'}
        for language in ('fr', 'en'):
            LG.select_language(language)
            lbl = lambda: types.SimpleNamespace(text='', width=0, x=0, y=0, content_width=100.0, content_height=10.0, draw=lambda: None)
            j = types.SimpleNamespace(helptext=True, stats=True, spacings=[0.02] * 50, step_times=[0.0, 1.0, 2.0], dt_engine=0.005, dt_drawing=0.003, n=0, lbl_stats=lbl(), tag_label=lbl(), lbl_hd=lbl(), height=720, width=1280,
                                      helptext_key=None, helptext_width=0.0, helptext_border=lbl(), _info=lambda: None, _helptext_margin=lambda: ('droite', 400))
            with without_screen(AM): AM.MenusMixin._draw_helptext(j)
            self.assertEqual(j.lbl_stats.text, att[language], language)
        self.assert_no_french([j.lbl_stats.text])

    def test_notifications(self):
        """Annulation d'un chargement (rien a annuler, puis annule) et import des sauvegardes : les trois messages que l'outil ecrit lui-meme."""
        for language, att in (('fr', ['Aucun chargement à annuler', 'Chargement annulé', 'Sauvegardes importées']), ('en', ['No load to undo', 'Load undone', 'Saves imported'])):
            LG.select_language(language); msgs = []
            def toast(text, duration=1.8):
                j = types.SimpleNamespace(toasts=[]); AM.MenusMixin.toast(j, text, duration); msgs.append(j.toasts[0][0])
            j = types.SimpleNamespace(toast=toast, undo_state=None)
            self.assertFalse(IN.SnapshotsMixin.cancel_loading(j))                                         # rien a annuler
            j.undo_state = {'a': 1}; j._complete_savestate = lambda: {'b': 2}; j._apply_savestate = lambda d: None; self.assertTrue(IN.SnapshotsMixin.cancel_loading(j))
            j.saves_screen = types.SimpleNamespace(needs_reload=True); j._after_import = lambda: TI.TitleMixin._after_import(j); TI.TitleMixin._close_saves(j)
            self.assertEqual(msgs, att, language)

    def test_an_already_formatted_text_stays_as_is(self):
        """Les messages a trous (« État 3 enregistré ») sont formates AVANT d'arriver a toast : ils passent sans changement."""
        entry(); j = types.SimpleNamespace(toasts=[]); AM.MenusMixin.toast(j, 'État 3 enregistré'); self.assertEqual(j.toasts[0][0], 'État 3 enregistré')

    def test_savestates_location(self):
        """Le lieu ecrit dans un fichier d'etat est un texte francais stable (traduit par la page qui l'affiche), quelle que soit la langue."""
        from dq4_pc.core import engine as ENGINE
        casos = [(ENGINE.PART_CASINO, 'ev04', 'Casino : poker'), (ENGINE.PART_CASINO, 'ev05', 'Casino : machine à sous'), (ENGINE.PART_CASINO, 'ev99', 'Casino'), (ENGINE.PART_BESTIARY, 'x', 'Bestiaire'),
                 (ENGINE.PART_FIELD, 'x', 'Carte du monde'), (ENGINE.PART_BATTLE, 'x', 'Combat'), (ENGINE.PART_TOWN, 'dnb1b2', 'dnb1b2')]
        for language in ('fr', 'en'):
            LG.select_language(language)
            for part, game_map, att in casos:
                j = types.SimpleNamespace(engine=types.SimpleNamespace(state=types.SimpleNamespace(part=part, game_map=game_map))); self.assertEqual(IN.SnapshotsMixin._location(j), att, (language, att))
        entry()
        self.assertEqual([LG.tr(a) for _, _, a in casos[:6]], ['Casino: poker', 'Casino: slot machine', 'Casino', 'Bestiary', 'World map', 'Battle'])      # (la page des etats affiche « Carte du monde » et « Combat » avec Pause._et : la traduction doit exister)

    def test_module_console_messages(self):
        """Les messages de la console des ecrans et des ressources (appeles pour de vrai avec un jeu absent ou en panne) : anglais sans francais, francais comme avant."""
        from dq4_pc.menus import message_font as MF
        t = tempfile.mkdtemp(prefix='lm_cons_'); self.addCleanup(shutil.rmtree, t, True)
        def outage(*a, **kw): raise OSError('disque')
        for language in ('fr', 'en'):
            LG.select_language(language)
            lus = []; MF.extract_message_font(os.path.join(t, 'inexistant'), os.path.join(t, 'cache'), log=lus.append)
            lus_ap = []; AP.prepare(os.path.join(t, 'inexistant'), os.path.join(t, 'cache_ap'), log=lus_ap.append)
            lus_um = []; UM.prepare_resources(os.path.join(t, 'inexistant'), os.path.join(t, 'cache_um'), log=lus_um.append)
            output = io.StringIO()
            j = types.SimpleNamespace(_complete_savestate=outage, _apply_savestate=lambda d: None, state_path=lambda n: 'x', get_framebuffer_size=outage)
            with contextlib.redirect_stdout(output), mock.patch.object(IN.SS, 'read', return_value={}):
                IN.SnapshotsMixin.load_state(j, 1); IN.SnapshotsMixin._clone_thumbnail(j)
            starts = {'fr': ['Police des messages non extraite (', 'Images du titre indisponibles', 'Ressources de menu indisponibles'], 'en': ['Message font not extracted (', 'Title images unavailable', 'Menu resources unavailable']}[language]
            self.assertTrue(lus[-1].startswith(starts[0]) and lus_ap[-1].startswith(starts[1]) and lus_um[-1].startswith(starts[2]), (language, lus, lus_ap, lus_um))
            lines = output.getvalue().splitlines(); self.assertEqual(len(lines), 2, lines)
            self.assertEqual([l.split(':')[0].strip() for l in lines], {'fr': ['etat avant chargement non garde', 'miniature impossible'], 'en': ['state before loading not kept', 'thumbnail failed']}[language])
            if language == 'en': self.assert_no_french([m.replace('SE-GARRIR', '') for m in lus + lus_ap + lus_um] + lines)


# ---------------------------------------------------------------------------------------------------------------------------------- le catalogue
SOURCES = ('menus/saves_screen.py', 'menus/ui_history.py', 'core/history.py', 'battle/battle_history.py', 'menus/ui_menu.py', 'menus/pre_game.py', 'menus/name_entry.py', 'menus/hud_mobile.py',
           'menus/message_font.py', 'window/title_screen.py', 'window/snapshots.py', 'window/menu_display.py', 'persistence/saves.py', 'persistence/logfile_format.py')


def marked_texts(files):
    """{texte: [fichier:ligne]} des textes passes a tr(...) / N_(...) dans ces fichiers de dq4_pc."""
    out = {}
    for f in files:
        with open(os.path.join(ROOT, 'dq4_pc', f), encoding='utf-8') as fh: tree = ast.parse(fh.read())
        for n in ast.walk(tree):
            if isinstance(n, ast.Call) and getattr(n.func, 'id', None) in ('tr', 'N_') and n.args and isinstance(n.args[0], ast.Constant) and isinstance(n.args[0].value, str): out.setdefault(n.args[0].value, []).append('%s:%d' % (f, n.lineno))
    return out


class Catalog(Language):
    def test_each_entry_is_used(self):
        """Pas d'entree orpheline : chaque texte du catalogue `menus` est marque dans le code (tr / N_) ou dessine par Pause._et sous une constante marquee. Une faute de frappe dans une cle ne laisse plus passer un texte en francais."""
        marks = marked_texts(SOURCES)
        orphelines = [k for k in catalog_by_file()['menus'] if k not in marks]
        self.assertEqual(orphelines, [])

    def test_each_marked_text_is_translated_or_identical(self):
        category = {k: v for f in catalog_by_file().values() for k, v in f.items()}                       # (tout le catalogue : un texte commun n'a qu'une entree, dans le fichier du premier lot qui l'a ecrit)
        for t, locations in marked_texts(SOURCES).items():
            if t in category: continue
            self.assertFalse(french(t), 'sans traduction : %r (%s)' % (t, locations))                                # (identiques en anglais : « Dialogues », « Casino »...)

    def test_in_french_nothing_changes(self):
        for t in catalog_by_file()['menus']: self.assertEqual(LG.tr(t), t)

    def test_in_english_all_changes_except_identical(self):
        entry()
        for fr, anglais in catalog_by_file()['menus'].items(): self.assertEqual(LG.tr(fr), anglais)


if __name__ == '__main__':
    unittest.main(verbosity=1)
