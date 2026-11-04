"""Description d'un objet qui ne tient pas dans son cadre (retour de 13 h 30, #190) : en combat, « Peut aussi etre utilisee comme objet au / combat. » sortait de la cellule de gauche de la fiche de l'objet (type 38)
et recouvrait la cellule « Attaque E 74 » ; dans le menu Objets (type 10) une description d'une seule ligne de 50 caracteres allait sous le bouton du sac. Le texte francais du patch a des lignes de 38 caracteres, la
mise en page du jeu a ete faite pour 2 lignes de ~28 : Rendu._texte recoupe maintenant la description a la largeur de son cadre (UM.DESCRIPTIONS) et, si 2 lignes ne suffisent pas, la comprime (jusqu'a COMPRESSION_MIN).

    python3 outils/test_description_objet.py
    DQ_APK=<APK patches> [DQ_UI_CACHE=<cache de l'interface>] python3 outils/test_description_objet.py        (ajoute les 360 descriptions reelles du patch avec la vraie police)"""
import os, re, sys, types, unittest, zipfile

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ICI, '..', 'dq4_pc'))
import pyglet
pyglet.options['shadow_window'] = False
if sys.platform.startswith('linux') and not os.environ.get('DISPLAY'): pyglet.options['headless'] = True
import ui_menu as UM

APK = os.environ.get('DQ_APK')
CACHE = os.environ.get('DQ_UI_CACHE', '/tmp/uicache47_camera')
U = 9.945 * 0.1                                                      # unites d'interface par pixel de police (characterSize 9,945 des descriptions)
DISPO_COMBAT = UM.DESC_COMBAT_X_MAX + 214.0                          # type 38 : texte ancre a x = -214
DISPO_OBJETS = UM.DESC_FICHE_X_MAX + 211.0                           # type 10 : texte ancre a x = -211


def rendu(largeur):
    r = object.__new__(UM.Rendu)
    r.textes = types.SimpleNamespace(bitmap=types.SimpleNamespace(largeur=largeur))
    return r


def ajuste(r, texte, dispo, nd=None):
    return r._ajuste_description({} if nd is None else nd, texte.split('\n'), dispo, 2, r.textes.bitmap, 1.0, 1.0, 1.0, 9.0)


class TestFenetres(unittest.TestCase):
    def fenetre(self, typ, noeuds):
        def texte(nid): return {'id': nid, 'par': 1, 'pos': [-214.0, 4.0, -197.0], 'act': True, 'text': {'font': 'font', 'characterSize': 9.945, 'text': None, 'anchor': 3, 'alignment': 0, 'lineSpacing': 1.0}, 'mats': []}
        t = {'name': 'Make_Test()', 'err': None, 'nodes': [{'id': 1, 'par': None, 'pos': [0.0, 0.0, 0.0], 'act': True, 'mats': []}] + [texte(10 + k) for k in range(noeuds)],
             'parts': [{'node': 1, 'ib': [{'k': 'text', 'go': 10 + k, 'variant': 0} for k in range(noeuds)]}], 'params': [{'id': 0, 'no': k, 'parts': 0, 'base': k} for k in range(noeuds)], 'codes': [], 'builds': []}
        return UM.Fenetre(types.SimpleNamespace(types={str(typ): t}, infos=[], cadres=[], hdr={'lang': {'hiro': 1.0}}, pousse=(0.0, 0.0)), typ)

    def test_table_des_descriptions(self):
        self.assertEqual(UM.DESCRIPTIONS, {(7, 1): UM.DESC_FICHE_X_MAX, (10, 4): UM.DESC_FICHE_X_MAX, (38, 3): UM.DESC_COMBAT_X_MAX})
        self.assertLess(UM.DESC_COMBAT_X_MAX, 63.0)                  # la cellule « Attaque » commence a x = 63 : la description s'arrete avant son cadre

    def test_fiche_d_objet_en_combat(self):
        fe = self.fenetre(38, 5)
        for no, s in enumerate(('Ragnar', 'Objets', 'Épée de cuivre', "Peut aussi être utilisée comme objet au\r\ncombat.", 'Attaque\n   E 24')): fe.param_str(0, no, s)
        self.assertEqual([(fe.N[10 + k].get('wrap_x'), fe.N[10 + k].get('wrap_n')) for k in range(5)], [(None, None)] * 3 + [(UM.DESC_COMBAT_X_MAX, 2), (None, None)])
        self.assertEqual(fe.N[13]['text']['text'], "Peut aussi être utilisée comme objet au\r\ncombat.")       # le texte du moteur n'est pas modifie (c'est le rendu qui recoupe)

    def test_menu_objets(self):
        fe = self.fenetre(10, 6)
        for no, s in enumerate(('Arme', 'Lance de fer', 'Attaque\n     E 50', "Ne semble pas avoir d'effets\r\nparticuliers.\n", '')): fe.param_str(0, no, s)
        self.assertEqual([fe.N[10 + k].get('wrap_x') for k in range(6)], [None, None, None, None, UM.DESC_FICHE_X_MAX, None])

    def test_une_autre_fenetre_n_est_pas_touchee(self):
        fe = self.fenetre(36, 5)
        for no in range(5): fe.param_str(0, no, 'x' * 60)
        self.assertTrue(all(fe.N[10 + k].get('wrap_x') is None for k in range(5)))


class TestAjuste(unittest.TestCase):
    """Police fictive : 8 pixels par caractere (U = 0,9945 : 8 unites par caractere a peu pres), cellule de combat = 270 unites (33 caracteres), cadre du menu Objets = 359 unites (44 caracteres)."""
    def setUp(self): self.r = rendu(lambda x: 8.0 * len(x) / U)

    def larg(self, l): return 8.0 * len(l.strip())

    def test_un_texte_qui_tient_est_laisse_tel_quel(self):
        t = "Ne semble pas avoir d'effets\r\nparticuliers.\n"
        out, f = ajuste(self.r, t, DISPO_COMBAT)
        self.assertEqual((out, f), (t.split('\n'), 1.0))                    # memes lignes, memes retours a la ligne, ligne vide finale comprise

    def test_ligne_trop_large_recoupee(self):
        out, f = ajuste(self.r, "Peut aussi être utilisée comme objet au\r\ncombat.", DISPO_COMBAT)           # 1re ligne de 39 caracteres = 312 unites > 270
        self.assertEqual((out, f), (['Peut aussi être utilisée comme', 'objet au combat.'], 1.0))

    def test_ligne_unique_de_cinquante_caracteres(self):
        t = "Au combat, ils peuvent inverser le cours du temps."
        out, f = ajuste(self.r, t, DISPO_COMBAT)
        self.assertEqual((len(out), f), (2, 1.0)); self.assertEqual(' '.join(out), t)
        self.assertTrue(all(self.larg(l) <= DISPO_COMBAT for l in out), out)
        out, f = ajuste(self.r, t, DISPO_OBJETS)                            # menu Objets : 400 unites > 359
        self.assertEqual((len(out), f), (2, 1.0)); self.assertTrue(all(self.larg(l) <= DISPO_OBJETS for l in out), out)

    def test_deux_lignes_longues_comprimees(self):
        t = "Sonnez-le avant le combat final pour\r\nfaire apparaître votre chariot."           # 36 + 31 caracteres : trois lignes a 270 unites, deux en comprimant
        out, f = ajuste(self.r, t, DISPO_COMBAT)
        self.assertEqual(len(out), 2, out); self.assertTrue(UM.COMPRESSION_MIN <= f < 1.0, f)
        self.assertTrue(all(self.larg(l) * f <= DISPO_COMBAT + 0.5 for l in out), (out, f))
        self.assertEqual(' '.join(out), "Sonnez-le avant le combat final pour faire apparaître votre chariot.")

    def test_texte_sans_espoir_comprime_au_minimum(self):
        out, f = ajuste(self.r, "mot " * 80, DISPO_COMBAT)
        self.assertEqual(f, UM.COMPRESSION_MIN); self.assertGreater(len(out), 2)           # (ne plante pas : le texte deborde, comme avant)

    def test_mot_plus_large_que_le_cadre(self):
        out, f = ajuste(self.r, "x" * 40, DISPO_COMBAT)                    # 320 unites : un seul mot, 1 ligne, comprime pour tenir
        self.assertEqual(len(out), 1); self.assertAlmostEqual(self.larg(out[0]) * f, DISPO_COMBAT, delta=17.0); self.assertLessEqual(self.larg(out[0]) * f, DISPO_COMBAT + 0.5)

    def test_textes_vides(self):
        for t in ('', '\n\n', ' \r\n'):
            out, f = ajuste(self.r, t, DISPO_COMBAT); self.assertEqual((out, f), (t.split('\n'), 1.0))

    def test_codes_de_couleur_sans_largeur(self):
        out, f = ajuste(self.r, "@c1" + "a" * 30 + "@c0", DISPO_COMBAT)           # 30 caracteres = 240 unites : tient (les codes @cN ne comptent pas)
        self.assertEqual(f, 1.0); self.assertEqual(len(out), 1)

    def test_resultat_garde_en_memoire(self):
        nd = {}; t = "Peut aussi être utilisée comme objet au\r\ncombat."
        a = ajuste(self.r, t, DISPO_COMBAT, nd); self.assertIn('_adj', nd)
        self.r.textes.bitmap.largeur = lambda x: 1 / 0                      # le deuxieme appel (meme texte, meme cadre) ne mesure plus rien
        self.assertIs(ajuste(self.r, t, DISPO_COMBAT, nd), a)


@unittest.skipUnless(APK and os.path.exists(os.path.join(CACHE, 'ui_garrir.json')) and os.path.exists(os.path.join(CACHE, 'ui_garrir.png')), 'police et descriptions reelles : DQ_APK=<dossier des APK patches> et le cache de l\'interface (ui_garrir.*)')
class TestDescriptionsReelles(unittest.TestCase):
    """Les 360 descriptions du patch (assets/msg/en/b0831000.mpt et b0835000.mpt : deux tables jumelles de 180 objets) avec la vraie police SE-GARRIR : aucune ne sort du cadre, ni en combat (type 38) ni dans le menu Objets (type 10)."""
    SEP = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f�]+|@c\d@(?:@a@b)?|@a@b")

    @classmethod
    def setUpClass(cls):
        cls.bm = UM.PoliceBitmap(os.path.join(CACHE, 'ui_garrir.json'), os.path.join(CACHE, 'ui_garrir.png'))
        z = zipfile.ZipFile(os.path.join(APK, 'split_UnityDataAssetPack.apk')); cls.textes = []
        for nom in ('assets/msg/en/b0831000.mpt', 'assets/msg/en/b0835000.mpt'):
            b = z.read(nom).decode('utf-8', 'replace'); cls.textes += [e for e in cls.SEP.split(b[b.find('@a@b'):]) if len(e.strip()) >= 6]
        cls.r = rendu(cls.bm.largeur); cls.r.textes.bitmap = cls.bm

    def verifie(self, dispo):
        n_avant = n_comprimes = 0; fmin = 1.0
        for e in self.textes:
            lignes = e.split('\n'); utiles = [l for l in lignes]
            while utiles and not utiles[-1].strip(): utiles.pop()
            if len(utiles) > 2 or max(self.bm.largeur(l.strip()) * U for l in utiles) > dispo + 0.5: n_avant += 1
            out, f = self.r._ajuste_description({}, lignes, dispo, 2, self.bm, U, 1.0, 1.0, U)
            out = [l for l in out]
            while out and not out[-1].strip(): out.pop()
            self.assertLessEqual(len(out), 2, e); self.assertLessEqual(max(self.bm.largeur(l.strip()) * U for l in out) * f, dispo + 0.5, e)
            self.assertEqual(' '.join(x.strip() for x in utiles if x.strip()).split(), ' '.join(x.strip() for x in out).split(), e)        # aucun mot perdu, ajoute ou deplace
            n_comprimes += f < 1.0; fmin = min(fmin, f)
        return n_avant, n_comprimes, fmin

    def test_il_y_a_bien_les_descriptions_du_patch(self):
        self.assertGreaterEqual(len(self.textes), 300)
        self.assertTrue(any('Peut aussi être utilisée comme objet au' in t for t in self.textes))

    def test_combat(self):
        n_avant, n_comprimes, fmin = self.verifie(DISPO_COMBAT)
        self.assertGreater(n_avant, 100)                             # (le constat : la majorite des descriptions debordait de la cellule de gauche)
        self.assertGreaterEqual(fmin, 0.75 - 1e-9)                   # compression la plus forte : x 0,75

    def test_menu_objets(self):
        n_avant, n_comprimes, fmin = self.verifie(DISPO_OBJETS)
        self.assertGreater(n_avant, 0); self.assertEqual(n_comprimes, 0)       # aucune n'a besoin d'etre comprimee : le recoupage suffit


if __name__ == '__main__':
    unittest.main()
