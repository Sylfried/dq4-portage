"""Version anglaise de l'outil (D-238), lot « menus » : tout ce que l'outil ecrit lui-meme hors des pages Parametres, en anglais puis en francais, avec de faux objets (ni fenetre, ni moteur, ni GL).

  - ecran Sauvegardes (menu de depart) : titre, boutons, explications, messages de resultat d'un export / import (reussi, annule, ignores, echec), boites de dialogue de fichiers (titres, filtres) ;
  - fenetre Historique : titre, onglets, case « Favoris seulement », aide, listes vides, entete et lignes d'un combat (textes que l'outil compose autour de ceux du jeu), favori dont le message manque ;
  - saisie du nom, licence (titre ; le texte d'origine du jeu et le « Privacy Policy » ne changent pas), noms des elements de l'editeur d'interface, textes d'essai des dialogues, infos F1, notifications,
    lieu des etats instantanes, messages de la console de ces modules ;
  - en anglais : aucun mot francais ne reste (hors la liste blanche, courte et justifiee) ; en francais : exactement les textes d'avant ;
  - le catalogue (textes_en\\menus.py) n'a pas d'entree orpheline.
Les regles generales du catalogue (memes trous, memes bords, pas de francais dans l'anglais, pas de doublon, tout `tr('...')` / `N_('...')` du code a sa traduction) sont dans tests/test_langue.py.

    python3 tests/test_langue_menus.py"""
import ast, contextlib, io, json, os, shutil, sys, tempfile, types, unittest, zipfile
from unittest import mock

ICI = os.path.dirname(os.path.abspath(__file__))
RACINE = os.path.join(ICI, '..')
sys.path.insert(0, RACINE)
sys.path.insert(0, ICI)
import _chemins          # (aide des tests : retrouver le code source dans les sous-dossiers de dq4_pc)
import pyglet
pyglet.options['shadow_window'] = False                     # (pas d'affichage necessaire : on ne dessine rien)
from dq4_pc import chemins as CH
from dq4_pc import langue as LG
from dq4_pc.combat import historique_combat as HC
from dq4_pc.fenetre import affichage_menus as AM
from dq4_pc.fenetre import instantanes as IN
from dq4_pc.fenetre import titre as TI
from dq4_pc.menus import avant_partie as AP
from dq4_pc.menus import ecran_sauvegardes as ES
from dq4_pc.menus import hud_mobile as HM
from dq4_pc.menus import pause as PA
from dq4_pc.menus import saisie_nom as SN
from dq4_pc.menus import ui_historique as UH
from dq4_pc.menus import ui_menu as UM
from dq4_pc.noyau import historique as HI
from dq4_pc.persistance import format_journal as FJ
from dq4_pc.persistance import reglages as RG
from dq4_pc.persistance import sauvegardes as S
from test_langue import francais, catalogue_par_fichier
import test_import_sauvegardes as TIS
import test_historique_cle as THC

LG.regler('fr')          # (la langue de l'ordinateur ne compte pas ici : chaque test choisit la sienne)


def en(): LG.regler('en')


class Langue(unittest.TestCase):
    """Chaque test choisit sa langue ; on revient au francais a la fin (les autres tests ont des attentes francaises)."""
    def setUp(self): LG.regler('fr')
    def tearDown(self): LG.regler('fr')

    def aucun_francais(self, textes, blanc=()):
        """Aucun des `textes` ne contient de francais (hors `blanc` : textes du jeu, noms propres), et il y en a."""
        textes = [t for t in textes if t not in blanc]
        self.assertTrue(textes)
        for t in textes: self.assertFalse(francais(t), 'reste du francais : %r' % (t,))


# ---------------------------------------------------------------------------------------------------------------------------------- faux objets
class Etiq:
    """Faux pyglet.text.Label : memorise le texte et le releve quand il est dessine."""
    def __init__(self, J, texte): self.J = J; self.text = texte; self.content_width = 5.0 * len(texte); self.content_height = 12.0; self.x = self.y = 0.0
    def draw(self): self.J.dessines.append(self.text)


class FauxJeu(types.SimpleNamespace):
    """Ce que les ecrans demandent a la fenetre : `_etiq` (fait les etiquettes), `pause` (les pages), taille, peripherique."""
    def __init__(self, **kw):
        super().__init__(width=1280, height=720, dessines=[], dernier_peripherique='clavier', **kw)
        self.pause = faux_pause(self)

    def _etiq(self, texte, taille, couleur=None, polices=()): return Etiq(self, texte)


def faux_pause(J):
    """La page-outil `Pause` sans ses dessins : `_et` est la vraie (elle traduit), le reste ne fait rien."""
    P = mock.MagicMock()
    P.J = J; P._pol = (); P.mode_souris = False; P.pos_souris = None
    P._et = lambda texte, taille, couleur=(255, 255, 255, 255): PA.Pause._et(P, texte, taille, couleur)
    P._sur = lambda z: False; P._pointeur_dans = lambda z: False; P._barre_defilement = lambda *a, **k: None
    return P


@contextlib.contextmanager
def sans_ecran(*modules):
    """Pas de GL : `gl` des modules et les formes de pyglet.shapes sont remplaces par des objets muets."""
    with contextlib.ExitStack() as st:
        for m in modules:
            if hasattr(m, 'gl'): st.enter_context(mock.patch.object(m, 'gl', mock.MagicMock()))
        for nom in ('Rectangle', 'BorderedRectangle', 'Star', 'Line', 'Box', 'Triangle'): st.enter_context(mock.patch('pyglet.shapes.' + nom, mock.MagicMock()))
        for nom in ('glDisable', 'glEnable', 'glBlendFunc'): st.enter_context(mock.patch('pyglet.gl.' + nom, mock.MagicMock()))
        yield


# ---------------------------------------------------------------------------------------------------------------------------------- ecran Sauvegardes : messages de resultat
class FauxDialogue:
    """Remplace S.Dialogue (tkinter) : memorise ce qu'on lui demande."""
    appels = []
    def __init__(self, mode, titre, initial_dossier=None, initial_nom=None):
        self.resultat = None; self.indisponible = False; FauxDialogue.appels.append((mode, titre))


class Sauvegardes(Langue):
    def setUp(self):
        super().setUp()
        self.t = tempfile.mkdtemp(prefix='lm_sauv_'); self.addCleanup(shutil.rmtree, self.t, True)
        self.d = CH.Dossiers(self.t, env={}); avant = CH.DOSSIERS; CH.DOSSIERS = self.d; self.addCleanup(setattr, CH, 'DOSSIERS', avant)
        self.ecr, self.lec = self.d.portage, self.d.mobile
        self.zip = os.path.join(self.t, 'i.zip')
        mo = types.SimpleNamespace(relire_journaux=lambda: 'nouveau', etat_boutons_depart=lambda x: x)
        self.J = FauxJeu(args=types.SimpleNamespace(saves_ecriture=self.ecr, saves_lecture=self.lec), moteur=mo, statut_depart='ancien')
        self.e = ES.EcranSauvegardes(self.J)

    def zipper(self, **fichiers):
        with zipfile.ZipFile(self.zip, 'w') as z:
            for nom, d in fichiers.items(): z.writestr(nom.replace('__', '/'), d)

    def reponse(self, action, resultat, indisponible=False):
        self.e.dialogue = types.SimpleNamespace(resultat=resultat, indisponible=indisponible); self.e.action = action; self.e.maj()
        return list(self.e.msg)

    def jeu_de_donnees(self):
        TIS.ecrire(os.path.join(self.ecr, 'data1.dat'), TIS.journal(1)); TIS.ecrire(os.path.join(self.ecr, 'data2.dat'), TIS.journal(2))
        TIS.ecrire(os.path.join(CH.DOSSIERS.dossier_etats(self.ecr), 'etat_01.dqs'), b'x' * 2000)

    # -- ce que les boutons demandent
    def test_ouverture_des_boites_de_dialogue(self):
        for langue, titres, msgs in (('fr', ('Exporter les sauvegardes', 'Importer des sauvegardes'),
                                      ["Choisis où enregistrer le fichier dans la fenêtre qui vient de s'ouvrir…", "Choisis le .zip ou les fichiers de sauvegarde dans la fenêtre qui vient de s'ouvrir…"]),
                                     ('en', ('Export saves', 'Import saves'), ['Choose where to save the file in the window that just opened…', 'Choose the .zip or the save files in the window that just opened…'])):
            LG.regler(langue); FauxDialogue.appels = []
            with mock.patch.object(S, 'Dialogue', FauxDialogue):
                e = ES.EcranSauvegardes(self.J); e.exporter(); m1 = list(e.msg); e.dialogue = None; e.importer(); m2 = list(e.msg)
            self.assertEqual(FauxDialogue.appels, [('enregistrer', titres[0]), ('ouvrir', titres[1])], langue); self.assertEqual([m1, m2], [[msgs[0]], [msgs[1]]], langue)

    def test_filtres_des_boites_de_fichiers(self):
        """Les filtres du « Enregistrer sous » / « Ouvrir » (tkinter) : memes motifs, libelles traduits."""
        vus = []
        class FauxFiledialog:
            @staticmethod
            def asksaveasfilename(**kw): vus.append(kw['filetypes']); return ''
            @staticmethod
            def askopenfilenames(**kw): vus.append(kw['filetypes']); return ()
        class FauxTk:
            def withdraw(self): pass
            def attributes(self, *a): pass
            def destroy(self): pass
        faux_tk = types.SimpleNamespace(Tk=FauxTk, filedialog=FauxFiledialog)
        for langue, att in (('fr', [[('Archive zip', '*.zip')], [('Sauvegardes (zip, data*.dat, etat_*.dqs)', '*.zip *.dat *.dqs'), ('Tous les fichiers', '*.*')]]),
                            ('en', [[('Zip archive', '*.zip')], [('Saves (zip, data*.dat, etat_*.dqs)', '*.zip *.dat *.dqs'), ('All files', '*.*')]])):
            LG.regler(langue); vus.clear()
            with mock.patch.dict(sys.modules, {'tkinter': faux_tk, 'tkinter.filedialog': FauxFiledialog}), mock.patch.object(faux_tk, 'filedialog', FauxFiledialog, create=True):
                for mode in ('enregistrer', 'ouvrir'):
                    d = S.Dialogue.__new__(S.Dialogue); d.resultat = None; d.indisponible = False; d.erreur = None; d._corps(mode, 'titre', None, None)
            self.assertEqual(vus, att, langue)

    # -- export
    def test_export_annule_reussi_et_vide(self):
        self.jeu_de_donnees(); chemin = os.path.join(self.t, 'sortie', 'sauv.zip')
        for langue, annule, ok, vide in (('fr', 'Export annulé.', 'Exporté : 2 fichiers de sauvegarde et 1 état instantané.', 'Impossible : Aucune sauvegarde a exporter (ni journal, ni etat instantane).'),
                                         ('en', 'Export canceled.', 'Exported: 2 save files and 1 save state.', 'Failed: Nothing to export (no adventure log, no save state).')):
            LG.regler(langue); e = self.e = ES.EcranSauvegardes(self.J)
            self.assertEqual(self.reponse('export', []), [annule], langue); self.assertEqual(e.msg_coul, ES.AIDE)
            self.assertEqual(self.reponse('export', [chemin]), [ok, chemin], langue); self.assertEqual(e.msg_coul, ES.VERT)
            self.J.args.saves_ecriture = os.path.join(self.t, 'rien'); self.J.args.saves_lecture = os.path.join(self.t, 'rien2')
            self.assertEqual(self.reponse('export', [os.path.join(self.t, 'x.zip')]), [vide], langue); self.assertEqual(e.msg_coul, ES.ROUGE)
            self.J.args.saves_ecriture, self.J.args.saves_lecture = self.ecr, self.lec

    def test_un_seul_fichier_et_un_seul_etat(self):
        TIS.ecrire(os.path.join(self.ecr, 'data1.dat'), TIS.journal(1)); TIS.ecrire(os.path.join(CH.DOSSIERS.dossier_etats(self.ecr), 'etat_01.dqs'), b'x' * 2000)
        for langue, att in (('fr', 'Exporté : 1 fichier de sauvegarde et 1 état instantané.'), ('en', 'Exported: 1 save file and 1 save state.')):
            LG.regler(langue); self.assertEqual(self.reponse('export', [os.path.join(self.t, langue + '.zip')])[0], att)

    # -- import
    def test_import_annule(self):
        for langue, att in (('fr', 'Import annulé.'), ('en', 'Import canceled.')):
            LG.regler(langue); self.assertEqual(self.reponse('import', []), [att], langue)

    def test_import_reussi_avec_copie_et_fichier_ignore(self):
        for langue, ligne1, copie, ignores, maj in (('fr', 'Importé : 1 fichier de sauvegarde et 0 état instantané.', 'Anciens fichiers copiés dans : ', 'Ignorés : data2.dat : fichier abime (somme de controle incorrecte) (i.zip)',
                                                     'Pour mettre à jour les boutons grisés du menu de départ, relance le jeu.'),
                                                    ('en', 'Imported: 1 save file and 0 save states.', 'Previous files copied to: ', 'Skipped: data2.dat: damaged file (checksum mismatch) (i.zip)',
                                                     'To update the grayed-out buttons of the start menu, restart the game.')):
            LG.regler(langue); shutil.rmtree(self.ecr, ignore_errors=True); self.e = ES.EcranSauvegardes(self.J)
            TIS.ecrire(os.path.join(self.ecr, 'data1.dat'), TIS.journal(1)); mauvais = bytearray(TIS.journal(3)); mauvais[100] ^= 1
            self.zipper(**{'data1.dat': TIS.journal(2), 'data2.dat': bytes(mauvais)})
            lignes = self.reponse('import', [self.zip])
            self.assertEqual(len(lignes), 4, langue); self.assertEqual(lignes[0], ligne1, langue); self.assertTrue(lignes[1].startswith(copie) and 'avant_import_' in lignes[1], lignes[1])
            self.assertEqual((lignes[2], lignes[3]), (ignores, maj), langue); self.assertEqual(self.e.msg_coul, ES.VERT); self.assertTrue(self.e.a_recharger)

    def test_import_sans_boite_de_dialogue(self):
        os.makedirs(os.path.join(self.ecr, 'import'), exist_ok=True)
        for langue, att in (('fr', ['Pas de boîte de dialogue disponible : dépose tes fichiers (.zip, data1.dat…) dans', os.path.join(self.ecr, 'import'), 'puis clique de nouveau sur Importer.']),
                            ('en', ['No file dialog available: put your files (.zip, data1.dat…) in', os.path.join(self.ecr, 'import'), 'then click Import again.'])):
            LG.regler(langue)
            with mock.patch.object(os, 'startfile', create=True):
                self.assertEqual(self.reponse('import', [], indisponible=True), att, langue)
            self.assertEqual(self.e.msg_coul, ES.ROUGE)

    def test_import_impossible(self):
        zip_vide = lambda: self.zipper(**{'lisez_moi.txt': b'rien'})
        faux_zip = os.path.join(self.t, 'z.zip'); TIS.ecrire(faux_zip, b'pas un zip')
        petit = os.path.join(self.t, 'etat_01.dqs'); TIS.ecrire(petit, b'x')
        court = os.path.join(self.t, 'data1.dat'); TIS.ecrire(court, b'abc')
        att = {'fr': ('Impossible : Aucun fichier de sauvegarde reconnu (data1.dat a data5.dat, data9.dat ou etats/etat_NN.dqs attendus).',
                      "Impossible : Aucun fichier de sauvegarde reconnu (z.zip : ce n'est pas un .zip valide).",
                      'Impossible : Aucun fichier de sauvegarde reconnu (etat_01.dqs : fichier trop petit (%s)).',
                      'Impossible : Aucun fichier de sauvegarde reconnu (data1.dat : taille 3 au lieu de 15360 (%s)).'),
               'en': ('Failed: No save file recognized (expected data1.dat to data5.dat, data9.dat or etats/etat_NN.dqs).',
                      'Failed: No save file recognized (z.zip: not a valid .zip file).',
                      'Failed: No save file recognized (etat_01.dqs: file too small (%s)).',
                      'Failed: No save file recognized (data1.dat: size 3 instead of 15360 (%s)).')}
        for langue in ('fr', 'en'):
            LG.regler(langue); rien, mauvais_zip, trop_petit, taille = att[langue]
            zip_vide(); self.assertEqual(self.reponse('import', [self.zip]), [rien], langue)
            self.assertEqual(self.reponse('import', [faux_zip]), [mauvais_zip], langue)
            self.assertEqual(self.reponse('import', [petit]), [trop_petit % self.t], langue); self.assertEqual(self.reponse('import', [court]), [taille % self.t], langue)
            self.assertEqual(self.e.msg_coul, ES.ROUGE)

    def test_journal_refuse_dit_pourquoi(self):
        for langue, bruit, abime in (('fr', "ce n'est pas un journal du jeu (en-tete inconnu)", 'fichier abime (somme de controle incorrecte)'),
                                     ('en', 'not a game adventure log (unknown header)', 'damaged file (checksum mismatch)')):
            LG.regler(langue); j = bytearray(TIS.journal(1)); j[0x500] ^= 1
            self.assertEqual(FJ.verifier('data1.dat', bytes(j)), abime, langue); self.assertEqual(FJ.verifier('data1.dat', bytes(range(256)) * 60), bruit, langue)

    def test_ecriture_impossible(self):
        TIS.ecrire(self.zip, b'')
        self.zipper(**{'data1.dat': TIS.journal(2)})
        for langue, att in (('fr', "Impossible : Aucun fichier n'a pu etre ecrit (data1.dat : ecriture impossible (disque) ; le fichier actuel est inchange)."),
                            ('en', 'Failed: No file could be written (data1.dat: could not be written (disque); the current file is unchanged).')):
            LG.regler(langue)
            with mock.patch.object(S, 'ecrire_atomique', lambda chemin, octets, **kw: 'disque'):
                self.assertEqual(self.reponse('import', [self.zip]), [att], langue)

    # -- dessin de l'ecran
    def test_dessin_de_l_ecran(self):
        explication = {'fr': ['Exporter : enregistre tes journaux (data1 à data5, data9) et tes états instantanés dans un fichier .zip.',
                              'Importer : lit un .zip de ce genre, ou des fichiers data1.dat, data2.dat… (par exemple copiés depuis un téléphone Android).',
                              "Les fichiers remplacés sont d'abord copiés dans le dossier « avant_import_… » de tes sauvegardes."],
                       'en': ['Export: saves your adventure logs (data1 to data5, data9) and your save states into a .zip file.',
                              'Import: reads a .zip like that, or data1.dat, data2.dat… files (for example copied from an Android phone).',
                              'Replaced files are first copied to the "avant_import_…" folder in your saves folder.']}
        titres = {'fr': ('Sauvegardes', 'Exporter', 'Importer'), 'en': ('Saves', 'Export', 'Import')}
        for langue in ('fr', 'en'):
            LG.regler(langue); J = FauxJeu(); e = ES.EcranSauvegardes(J); e._dire(['Un message.'], ES.VERT)
            with sans_ecran(ES): e.dessiner(J, 640.0, 360.0, 2.0)
            self.assertEqual(J.dessines, [titres[langue][0]] + explication[langue] + [titres[langue][1], titres[langue][2], 'Un message.'], langue)
        self.aucun_francais(J.dessines, blanc=('Un message.',))

    def test_explication_traduite_en_entier_avant_d_etre_coupee(self):
        """Fenetre etroite : les phrases d'aide passent sur plusieurs lignes. L'anglais n'a pas le meme ordre des mots : la phrase est traduite
        d'un bloc PUIS coupee (sinon les morceaux francais n'ont pas de traduction et restent en francais)."""
        for langue in ('fr', 'en'):
            LG.regler(langue); J = FauxJeu(); e = ES.EcranSauvegardes(J)
            with sans_ecran(ES): e.dessiner(J, 640.0, 360.0, 0.4)
            lignes = J.dessines[1:-2]                                                  # (sans le titre ni les deux boutons)
            self.assertGreater(len(lignes), len(ES.EXPLICATION), 'la fenetre doit etre assez etroite pour couper les phrases')
            recolle = ' '.join(lignes)
            for phrase in ES.EXPLICATION: self.assertIn(LG.tr(phrase), recolle, langue)
            if langue == 'en': self.aucun_francais(lignes, blanc=('avant_import_…',))

    def test_bouton_du_menu_de_depart(self):
        """Le portage pose son bouton « Sauvegardes » dans le menu de depart (a la place de « Sauv. cloud »)."""
        ml = types.SimpleNamespace(types={'53': {'nodes': [], 'parts': [], 'params': [], 'codes': [], 'name': 'Make_StartMenuSecond'}})
        for langue, att in (('fr', 'Sauvegardes'), ('en', 'Saves')):
            LG.regler(langue)
            with mock.patch.object(UM.Fenetre, 'param_str') as ps: UM.Fenetre(ml, 53)
            self.assertEqual([c.args for c in ps.call_args_list], [(5, 0, att)], langue)


# ---------------------------------------------------------------------------------------------------------------------------------- historique
def historique_de_test():
    """Dialogues et combats d'essai (textes neutres : les noms et les dialogues sont ceux du jeu, jamais traduits)."""
    h = HI.Historique(None, lambda: 1000.0)
    h.ajouter('Hello there.', 'Alena', 200); h.ajouter('Welcome.', None, 5200)
    for i in range(1, 7):
        h.ajouter_combat({'t': 100 * i, 'issue': ('victoire', 'fuite', 'defaite')[i % 3], 'or': 21, 'xp': 38,
                          'ennemis': [{'nom': 'Slime', 'total': 3, 'vaincus': 3}, {'nom': 'Golem', 'total': 2, 'vaincus': 1}], 'objets': [{'nom': 'Medicinal herb'}, {'nom': 'Life stone'}]})
    return h


class FauxBM:
    """Police bitmap du jeu : seulement ce que dessiner() lui demande."""
    ascent = 18.0; interligne = 24.0; PAD = 0.0
    def largeur(self, texte): return 6.0 * len(texte)


class Historique(Langue):
    def vue(self, h, onglet=UH.O_DIALOGUES, favoris_seuls=False, avec_police=True):
        J = FauxJeu(historique=h, reg=RG.Reglages(None))
        if avec_police: J.ui_rendu = types.SimpleNamespace(textes=types.SimpleNamespace(bitmap=FauxBM(), messages=None), ml=None, plaque=lambda *a, **k: True, dessiner=lambda *a, **k: None)
        J.reg['historique_favoris_seuls'] = favoris_seuls
        v = UH.VueHistorique(J.pause); v.entrer(onglet); v.rec = []
        v._ligne = lambda bm, texte, x, y, sc, coul, taille: v.rec.append(texte)                    # (la ligne de texte : police bitmap du jeu ou du systeme)
        return v

    def dessiner(self, v):
        with sans_ecran(UH), mock.patch.object(UH, 'HM', mock.MagicMock()): v.dessiner()
        return v.rec

    # -- l'entete, les onglets, l'aide
    def test_cadre_de_la_fenetre(self):
        h = historique_de_test()
        att = {'fr': ('Historique', ('Dialogues', 'Combats'), 'Favoris seulement',
                      ['Haut / Bas : message précédent / suivant', 'Molette : défiler', 'Gauche / Droite : onglet', 'Entrée : favori ★', 'F : favoris seulement', 'H : suite', 'Échap : fermer']),
               'en': ('History', ('Dialogue', 'Battles'), 'Favorites only',
                      ['Up / Down: previous / next message', 'Mouse wheel: scroll', 'Left / Right: tab', 'Enter: favorite ★', 'F: favorites only', 'H: next', 'Esc: close'])}
        for langue in ('fr', 'en'):
            LG.regler(langue); titre, onglets, filtre, aide = att[langue]
            for avec_police in (True, False):                                                                  # (police bitmap du jeu, ou repli sur la police du systeme)
                rec = self.dessiner(self.vue(h, avec_police=avec_police)); aide_vue = ' | '.join(rec)
                self.assertIn(titre, rec); self.assertEqual([t for t in rec if t in onglets], list(onglets)); self.assertIn(filtre, rec)
                for ligne in aide: self.assertIn(ligne, aide_vue, (langue, ligne))
        self.aucun_francais([t for t in rec if t not in ('Alena',)])

    def test_aide_sans_touche_historique(self):
        """Quand la touche de l'historique est retiree, la ligne « H : suite » disparait (comme avant)."""
        h = historique_de_test()
        for langue, ligne in (('fr', 'H : suite'), ('en', 'H: next')):
            LG.regler(langue); v = self.vue(h); self.assertIn(ligne, ' | '.join(self.dessiner(v)))
            v = self.vue(h); v.J.reg['touches']['historique'] = [None, None]; self.assertNotIn(ligne, ' | '.join(self.dessiner(v)))

    def test_listes_vides(self):
        h = HI.Historique(None, lambda: 1000.0)
        att = {('fr', False, UH.O_DIALOGUES): "Aucun dialogue pour l'instant.", ('fr', False, UH.O_COMBATS): "Aucun combat pour l'instant.",
               ('fr', True, UH.O_DIALOGUES): 'Aucun dialogue en favori : décoche « Favoris seulement », choisis un dialogue et appuie sur Entrée (ou clique son étoile) pour le garder.',
               ('fr', True, UH.O_COMBATS): 'Aucun combat en favori : décoche « Favoris seulement », choisis un combat et appuie sur Entrée (ou clique son étoile) pour le garder.',
               ('en', False, UH.O_DIALOGUES): 'No dialogue yet.', ('en', False, UH.O_COMBATS): 'No battle yet.',
               ('en', True, UH.O_DIALOGUES): 'No favorite dialogue: uncheck "Favorites only", choose a dialogue and press Enter (or click its star) to keep it.',
               ('en', True, UH.O_COMBATS): 'No favorite battle: uncheck "Favorites only", choose a battle and press Enter (or click its star) to keep it.'}
        for (langue, fav, onglet), msg in att.items():
            LG.regler(langue); rec = self.dessiner(self.vue(h, onglet, fav))
            self.assertIn(msg, ' '.join(rec), (langue, fav, onglet))                       # (le message, coupe en lignes aux espaces : les lignes mises bout a bout le redonnent)
            if langue == 'en': self.aucun_francais(rec)

    # -- un combat : entete (issue), lignes composees autour des noms du jeu
    def test_entete_et_lignes_d_un_combat(self):
        h = historique_de_test()
        att = {'fr': (('Victoire', 'Fuite', 'Défaite'), 'Slime ×3', 'Golem ×2 : 1 vaincu, 1 resté', 'Or : 21\u00a0\u00a0\u00a0\u00a0\u00a0Expérience : 38', 'Objets : Medicinal herb, Life stone'),
               'en': (('Victory', 'Escaped', 'Defeat'), 'Slime ×3', 'Golem ×2: 1 defeated, 1 remained', 'Gold: 21\u00a0\u00a0\u00a0\u00a0\u00a0Experience: 38', 'Items: Medicinal herb, Life stone')}
        for langue in ('fr', 'en'):
            LG.regler(langue); rec = self.dessiner(self.vue(h, UH.O_COMBATS)); issues = att[langue][0]
            for t in issues: self.assertIn(t, rec, (langue, t))                              # (l'entete de chaque boite : l'issue du combat)
            for t in att[langue][1:]: self.assertIn(t, rec, (langue, t))                     # (les noms de Slime, Golem, objets : ceux du jeu, jamais traduits)
        self.aucun_francais(rec)

    def test_lignes_d_un_combat_toutes_les_issues(self):
        fabrique = lambda **kw: HI.element_de_combat(1, dict({'t': 5, 'issue': 'victoire', 'or': 0, 'xp': 0, 'ennemis': []}, **kw))
        def nom(**kw): return {'nom': 'Bat', 'total': 1, 'vaincus': 0, **kw}
        cas = [fabrique(issue='defaite'),                                                                                           # aucun ennemi connu
               fabrique(issue='fuite', ennemis=[nom(fuis=1)]), fabrique(issue='fuite', ennemis=[nom(disparus=1)]), fabrique(issue='fuite', ennemis=[nom()]),
               fabrique(issue='fuite', ennemis=[{'nom': 'Golem', 'total': 5, 'vaincus': 2, 'fuis': 1, 'disparus': 1}]),
               fabrique(issue='fuite', ennemis=[{'nom': 'Golem', 'total': 5, 'vaincus': 1, 'fuis': 2, 'disparus': 2}]),
               fabrique(**{'or': 3, 'xp': 4})]                                                                                   # victoire sans ennemi connu
        att = {'fr': [['Ennemis inconnus'], ['Bat : enfui'], ['Bat : disparu'], ['Bat : resté'], ['Golem ×5 : 2 vaincus, 1 enfui, 1 disparu, 1 resté'], ['Golem ×5 : 1 vaincu, 2 enfuis, 2 disparus'],
                      ['Ennemis inconnus', 'Or : 3\u00a0\u00a0\u00a0\u00a0\u00a0Expérience : 4']],
               'en': [['Unknown enemies'], ['Bat: fled'], ['Bat: vanished'], ['Bat: remained'], ['Golem ×5: 2 defeated, 1 fled, 1 vanished, 1 remained'], ['Golem ×5: 1 defeated, 2 fled, 2 vanished'],
                      ['Unknown enemies', 'Gold: 3\u00a0\u00a0\u00a0\u00a0\u00a0Experience: 4']]}
        for langue in ('fr', 'en'):
            LG.regler(langue); self.assertEqual([HI.lignes_combat(c) for c in cas], att[langue], langue)
        self.aucun_francais([l for ls in att['en'] for l in ls])

    def test_libelles_des_issues(self):
        for langue, att in (('fr', {'victoire': 'Victoire', 'fuite': 'Fuite', 'defaite': 'Défaite'}), ('en', {'victoire': 'Victory', 'fuite': 'Escaped', 'defaite': 'Defeat'})):
            LG.regler(langue); self.assertEqual({k: LG.tr(v) for k, v in HI.LIBELLE_ISSUE.items()}, att, langue)

    def test_noms_de_remplacement_quand_le_moteur_ne_repond_pas(self):
        for langue, monstre, objet in (('fr', 'Monstre', 'Objet n°12'), ('en', 'Monster', 'Item #12')):
            LG.regler(langue)
            s = HC.Suivi(); s.mort(4, 7); self.assertEqual(s.ennemis()[0]['nom'], monstre, langue)
            c = types.SimpleNamespace(_noms_objets={}, _texte_moteur=lambda genre, numero: None); self.assertEqual(HC.CapteurCombat._nom_objet(c, 12), objet, langue)

    def test_favori_dont_le_message_manque(self):
        class Dossier(THC.Base): pass
        b = Dossier(); b.setUp()
        try:
            h = b.hist({802199: THC.BRUT_SIMPLE}); h.basculer_favori(h.ajouter(HI.nettoyer(THC.BRUT_SIMPLE), None, 1, 802199))
            for langue, att in (('fr', '(Message introuvable dans les fichiers du jeu : b0802000#199)'), ('en', '(Message not found in the game files: b0802000#199)')):
                LG.regler(langue); self.assertEqual(b.hist({}).favoris[0].texte, att, langue)
        finally: b.tearDown()

    # -- la console
    def test_messages_de_la_console(self):
        t = tempfile.mkdtemp(prefix='lm_hist_'); self.addCleanup(shutil.rmtree, t, True)
        def sortie(f):
            tampon = io.StringIO()
            with contextlib.redirect_stdout(tampon): f()
            return tampon.getvalue()
        for langue, illisible, non_ecrit in (('fr', "Favoris de l'historique illisibles (", "Favoris de l'historique non enregistres : "), ('en', 'History favorites unreadable (', 'History favorites not saved: ')):
            LG.regler(langue)
            p = os.path.join(t, 'fav_%s.json' % langue)
            with open(p, 'w', encoding='utf-8') as f: f.write('{pas du json')
            s = sortie(lambda: HI.Historique(p, lambda: 1.0)); self.assertTrue(s.startswith(illisible), (langue, s)); self.assertTrue(os.path.exists(p + '.corrompu'))
            bloc = os.path.join(t, 'un_fichier_%s' % langue)
            with open(bloc, 'w') as f: f.write('x')
            h = HI.Historique(os.path.join(bloc, 'fav.json'), lambda: 1.0); h.ajouter('Hello.', None, 1); h._sale = True
            s = sortie(lambda: h.enregistrer(True)); self.assertTrue(s.startswith(non_ecrit), (langue, s))
        def refus(sym): raise OSError('pas de symbole')
        for langue, capteur, combat in (('fr', 'Historique : crochets non installes (', 'Historique des combats : '), ('en', 'History: hooks not installed (', 'Battle history: ')):
            LG.regler(langue)
            moteur = types.SimpleNamespace(core=types.SimpleNamespace(export=refus))
            s = sortie(lambda: HI.Capteur(moteur)); self.assertTrue(s.startswith(capteur), (langue, s))
            s = sortie(lambda: HC.CapteurCombat(moteur)); self.assertTrue(s.startswith(combat + ('crochets non installes (' if langue == 'fr' else 'hooks not installed (')), (langue, s))
            moteur = types.SimpleNamespace(core=types.SimpleNamespace(export=lambda sym: 0))                          # un moteur sans les symboles attendus
            s = sortie(lambda: HC.CapteurCombat(moteur)); self.assertTrue(s.startswith(combat), (langue, s)); self.assertFalse(francais(s) and langue == 'en', s)


# ---------------------------------------------------------------------------------------------------------------------------------- saisie du nom, licence, editeur d'interface, notifications...
class Autres(Langue):
    def test_saisie_du_nom(self):
        fonctions = list(SN.FONCTIONS)
        for langue, att in (('fr', ['Saisir un nom', 'Clavier : taper le nom', 'Entrée : valider · Échap : retour']), ('en', ['Enter a name', 'Keyboard: type the name', 'Enter: confirm · Esc: back'])):
            LG.regler(langue); J = FauxJeu(); s = SN.SaisieNom(J); s.ouvrir(8)
            with sans_ecran(SN): s.dessiner(640.0, 360.0, 1.6)
            self.assertIn(att[0], J.dessines); self.assertIn(att[1], J.dessines); self.assertIn(att[2], J.dessines)
            self.assertEqual([t for t in J.dessines if t in fonctions], fonctions, langue)                    # (les libelles des boutons de fonction viennent du jeu : non traduits)
        self.aucun_francais(J.dessines, blanc=('à À',))                                                         # liste blanche : « à À » = le libelle du jeu (C_ALPHABET_ETC) du bouton de la page des lettres accentuees

    def test_licence(self):
        for langue, titre in (('fr', 'Licence'), ('en', 'License')):
            LG.regler(langue); J = FauxJeu(); lic = AP.Licence(None)
            lay = types.SimpleNamespace(content_height=1000.0, height=500.0, x=0, y=0, view_y=0, draw=lambda: None)
            lic._mise = lambda J, ech: lay
            with sans_ecran(): lic.dessiner(J, 640.0, 360.0, 1.5)
            self.assertEqual(J.dessines, [titre, 'Privacy Policy'], langue)                                    # « Privacy Policy » : le texte du jeu
        # le texte d'en-tete du portage est deja en anglais, la liste d'origine suit : rien de tout cela ne depend de la langue
        for langue in ('fr', 'en'):
            LG.regler(langue); self.assertEqual(AP.Licence(None).texte.replace('\n', ' ').count('This is an unofficial'), 1)
        self.assertFalse(francais(AP.LICENCE_PROJET))

    def test_noms_des_elements_de_l_editeur_d_interface(self):
        att = {'fr': {'carte': 'Carte', 'menu': 'Commandes', 'discussion': 'Discussion', HM.COMBAT: 'Vitesse de combat', HM.CROIX: 'Croix'},
               'en': {'carte': 'Map', 'menu': 'Controls', 'discussion': 'Talk', HM.COMBAT: 'Battle speed', HM.CROIX: 'D-pad'}}
        for langue in ('fr', 'en'):
            LG.regler(langue); self.assertEqual({k: LG.tr(v) for k, v in HM.LIBELLE.items()}, att[langue], langue)
            J = FauxJeu(reg=RG.Reglages(None), moteur=types.SimpleNamespace(taille_croix=lambda: 1)); b = HM.Boutons(J)
            with sans_ecran(HM), mock.patch.object(HM, 'cadre'), mock.patch.object(HM, 'tracer_grille'), mock.patch.object(b, '_plaque', return_value=True), mock.patch.object(b, '_sprite', return_value=(mock.MagicMock(), 1)), \
                    mock.patch.object(b, '_fleches_combat'), mock.patch.object(b, '_croix'):
                b.dessiner(list(HM.BOUTONS) + [HM.CROIX], edition=True)
            self.assertEqual(sorted(J.dessines), sorted(att[langue].values()), langue)                         # (en edition, chaque element porte son nom)

    def test_textes_d_essai_des_dialogues(self):
        """Chaque ligne d'essai de l'editeur est traduite, et c'est la ligne traduite qui est ecrite dans le canevas."""
        for langue in ('fr', 'en'):
            LG.regler(langue); ecrits = []
            dessin = mock.MagicMock(); dessin.text = lambda xy, t, **kw: ecrits.append(t)
            j = types.SimpleNamespace(ESSAIS=AM.MenusMixin.ESSAIS, H_ECH=AM.MenusMixin.H_ECH, args=types.SimpleNamespace(cache='/inexistant'), _essai=1, nouvel_echantillon=lambda: None)
            with mock.patch('PIL.ImageDraw.Draw', return_value=dessin): AM.MenusMixin._canevas_apercu(j)
            self.assertEqual(ecrits, [LG.tr(t) for t in AM.MenusMixin.ESSAIS[1]], langue)
            if langue == 'en': self.assertEqual(ecrits, ['This is a test text.', 'It is used to adjust the size and', 'position of the dialogue boxes.'])
        en(); self.aucun_francais([LG.tr(t) for lignes in AM.MenusMixin.ESSAIS for t in lignes])                    # (tous les textes d'essai, pas seulement celui du test)

    def test_infos_f1(self):
        att = {'fr': '50 images/s | moteur 1.0 pas/s (5.0 ms) | pire image 20 ms | dessin Python 3.0 ms', 'en': '50 frames/s | engine 1.0 steps/s (5.0 ms) | worst frame 20 ms | Python drawing 3.0 ms'}
        for langue in ('fr', 'en'):
            LG.regler(langue)
            etiq = lambda: types.SimpleNamespace(text='', width=0, x=0, y=0, content_width=100.0, content_height=10.0, draw=lambda: None)
            j = types.SimpleNamespace(aide=True, stats=True, ecarts=[0.02] * 50, pas_t=[0.0, 1.0, 2.0], dt_moteur=0.005, dt_dessin=0.003, n=0, etiq_stats=etiq(), etiquette=etiq(), etiq_hd=etiq(), height=720, width=1280,
                                      aide_cle=None, aide_larg=0.0, cadre_aide=etiq(), _infos=lambda: None, _marge_aide=lambda: ('droite', 400))
            with sans_ecran(AM): AM.MenusMixin._dessiner_aide(j)
            self.assertEqual(j.etiq_stats.text, att[langue], langue)
        self.aucun_francais([j.etiq_stats.text])

    def test_notifications(self):
        """Annulation d'un chargement (rien a annuler, puis annule) et import des sauvegardes : les trois messages que l'outil ecrit lui-meme."""
        for langue, att in (('fr', ['Aucun chargement à annuler', 'Chargement annulé', 'Sauvegardes importées']), ('en', ['No load to undo', 'Load undone', 'Saves imported'])):
            LG.regler(langue); msgs = []
            def toast(texte, duree=1.8):
                j = types.SimpleNamespace(toasts=[]); AM.MenusMixin.toast(j, texte, duree); msgs.append(j.toasts[0][0])
            j = types.SimpleNamespace(toast=toast, etat_annul=None)
            self.assertFalse(IN.InstantanesMixin.annuler_chargement(j))                                         # rien a annuler
            j.etat_annul = {'a': 1}; j._etat_complet = lambda: {'b': 2}; j._appliquer_etat = lambda d: None; self.assertTrue(IN.InstantanesMixin.annuler_chargement(j))
            j.sauv = types.SimpleNamespace(a_recharger=True); j._apres_import = lambda: TI.TitreMixin._apres_import(j); TI.TitreMixin._sauv_fermer(j)
            self.assertEqual(msgs, att, langue)

    def test_un_texte_deja_formate_reste_tel_quel(self):
        """Les messages a trous (« État 3 enregistré ») sont formates AVANT d'arriver a toast : ils passent sans changement."""
        en(); j = types.SimpleNamespace(toasts=[]); AM.MenusMixin.toast(j, 'État 3 enregistré'); self.assertEqual(j.toasts[0][0], 'État 3 enregistré')

    def test_lieu_des_etats_instantanes(self):
        """Le lieu ecrit dans un fichier d'etat est un texte francais stable (traduit par la page qui l'affiche), quelle que soit la langue."""
        from dq4_pc.noyau import moteur as MO
        casos = [(MO.PARTIE_CASINO, 'ev04', 'Casino : poker'), (MO.PARTIE_CASINO, 'ev05', 'Casino : machine à sous'), (MO.PARTIE_CASINO, 'ev99', 'Casino'), (MO.PARTIE_BESTIAIRE, 'x', 'Bestiaire'),
                 (MO.PARTIE_CHAMP, 'x', 'Carte du monde'), (MO.PARTIE_COMBAT, 'x', 'Combat'), (MO.PARTIE_VILLE, 'dnb1b2', 'dnb1b2')]
        for langue in ('fr', 'en'):
            LG.regler(langue)
            for partie, carte, att in casos:
                j = types.SimpleNamespace(moteur=types.SimpleNamespace(etat=types.SimpleNamespace(partie=partie, carte=carte))); self.assertEqual(IN.InstantanesMixin._lieu(j), att, (langue, att))
        en()
        self.assertEqual([LG.tr(a) for _, _, a in casos[:6]], ['Casino: poker', 'Casino: slot machine', 'Casino', 'Bestiary', 'World map', 'Battle'])      # (la page des etats affiche « Carte du monde » et « Combat » avec Pause._et : la traduction doit exister)

    def test_messages_de_la_console_des_modules(self):
        """Les messages de la console des ecrans et des ressources (appeles pour de vrai avec un jeu absent ou en panne) : anglais sans francais, francais comme avant."""
        from dq4_pc.menus import police_messages as PM
        t = tempfile.mkdtemp(prefix='lm_cons_'); self.addCleanup(shutil.rmtree, t, True)
        def panne(*a, **kw): raise OSError('disque')
        for langue in ('fr', 'en'):
            LG.regler(langue)
            lus = []; PM.extraire_police_messages(os.path.join(t, 'inexistant'), os.path.join(t, 'cache'), log=lus.append)
            lus_ap = []; AP.preparer(os.path.join(t, 'inexistant'), os.path.join(t, 'cache_ap'), log=lus_ap.append)
            lus_um = []; UM.preparer_ressources(os.path.join(t, 'inexistant'), os.path.join(t, 'cache_um'), log=lus_um.append)
            sortie = io.StringIO()
            j = types.SimpleNamespace(_etat_complet=panne, _appliquer_etat=lambda d: None, chemin_etat=lambda n: 'x', get_framebuffer_size=panne)
            with contextlib.redirect_stdout(sortie), mock.patch.object(IN.ET, 'lire', return_value={}):
                IN.InstantanesMixin.charger_etat(j, 1); IN.InstantanesMixin._copier_miniature(j)
            debuts = {'fr': ['Police des messages non extraite (', 'Images du titre indisponibles', 'Ressources de menu indisponibles'], 'en': ['Message font not extracted (', 'Title images unavailable', 'Menu resources unavailable']}[langue]
            self.assertTrue(lus[-1].startswith(debuts[0]) and lus_ap[-1].startswith(debuts[1]) and lus_um[-1].startswith(debuts[2]), (langue, lus, lus_ap, lus_um))
            lignes = sortie.getvalue().splitlines(); self.assertEqual(len(lignes), 2, lignes)
            self.assertEqual([l.split(':')[0].strip() for l in lignes], {'fr': ['etat avant chargement non garde', 'miniature impossible'], 'en': ['state before loading not kept', 'thumbnail failed']}[langue])
            if langue == 'en': self.aucun_francais([m.replace('SE-GARRIR', '') for m in lus + lus_ap + lus_um] + lignes)


# ---------------------------------------------------------------------------------------------------------------------------------- le catalogue
SOURCES = ('menus/ecran_sauvegardes.py', 'menus/ui_historique.py', 'noyau/historique.py', 'combat/historique_combat.py', 'menus/ui_menu.py', 'menus/avant_partie.py', 'menus/saisie_nom.py', 'menus/hud_mobile.py',
           'menus/police_messages.py', 'fenetre/titre.py', 'fenetre/instantanes.py', 'fenetre/affichage_menus.py', 'persistance/sauvegardes.py', 'persistance/format_journal.py')


def textes_marques(fichiers):
    """{texte: [fichier:ligne]} des textes passes a tr(...) / N_(...) dans ces fichiers de dq4_pc."""
    out = {}
    for f in fichiers:
        with open(os.path.join(RACINE, 'dq4_pc', f), encoding='utf-8') as fh: arbre = ast.parse(fh.read())
        for n in ast.walk(arbre):
            if isinstance(n, ast.Call) and getattr(n.func, 'id', None) in ('tr', 'N_') and n.args and isinstance(n.args[0], ast.Constant) and isinstance(n.args[0].value, str): out.setdefault(n.args[0].value, []).append('%s:%d' % (f, n.lineno))
    return out


class Catalogue(Langue):
    def test_chaque_entree_sert(self):
        """Pas d'entree orpheline : chaque texte du catalogue `menus` est marque dans le code (tr / N_) ou dessine par Pause._et sous une constante marquee. Une faute de frappe dans une cle ne laisse plus passer un texte en francais."""
        marques = textes_marques(SOURCES)
        orphelines = [k for k in catalogue_par_fichier()['menus'] if k not in marques]
        self.assertEqual(orphelines, [])

    def test_chaque_texte_marque_est_traduit_ou_identique(self):
        cat = {k: v for f in catalogue_par_fichier().values() for k, v in f.items()}                       # (tout le catalogue : un texte commun n'a qu'une entree, dans le fichier du premier lot qui l'a ecrit)
        for t, ou in textes_marques(SOURCES).items():
            if t in cat: continue
            self.assertFalse(francais(t), 'sans traduction : %r (%s)' % (t, ou))                                # (identiques en anglais : « Dialogues », « Casino »...)

    def test_en_francais_rien_ne_change(self):
        for t in catalogue_par_fichier()['menus']: self.assertEqual(LG.tr(t), t)

    def test_en_anglais_tout_change_sauf_les_identiques(self):
        en()
        for fr, anglais in catalogue_par_fichier()['menus'].items(): self.assertEqual(LG.tr(fr), anglais)


if __name__ == '__main__':
    unittest.main(verbosity=1)
