"""Favoris de l'historique des dialogues rangés par la CLÉ du message (#265) : le fichier des favoris garde le numéro du message dans les fichiers du jeu (« b0802000#199 »), pas son texte ; le texte est
redemandé au moteur (TextAPI::extractText), donc un message modifié dans le patch change aussi dans les favoris.

  1. fonctions pures : `cle_message`, `valeurs` (variables « [NONE 1,0] » du jeu), `liaison` (message entier ou page séparée par ㈡), `texte_lie` ;
  2. `Historique` avec un faux moteur : le favori n'est rangé par la clé que si le texte des fichiers redonne EXACTEMENT ce qui a été lu ; sinon il garde son texte (comme avant) ; le fichier ne contient alors aucun texte ;
     relu avec un autre texte dans les fichiers, le favori montre le nouveau texte ; message disparu : une ligne le dit avec la clé ; anciens fichiers (avec « texte ») et entrées invalides ;
  3. `Capteur` (faux émulateur) : le numéro vient de ui_MsgAdd, seulement quand TextBuffer::cat en est appelée directement ; `Capteur.modele` interroge TextAPI::extractText (genre 1) ;
  4. avec le vrai moteur (si DQ_APK et DQ_SAVES sont donnés) : les numéros captés pendant le prologue, un favori rangé par la clé puis relu dans un second moteur, un texte modifié qui se répercute.

    python3 tests/test_historique_cle.py
"""
import json, os, shutil, sys, tempfile, types, unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from dq4_pc.noyau import historique as HI

BRUT_SIMPLE = "Il était une fois, dans un pays lointain.\n"
BRUT_PAGES = "*: Vous êtes née dans cette ville, n'est-ce pas\xa0?\nIl ne manquerait plus que je vous fasse\npayer.\n㈡\n*: Alors, vous restez\xa0?\n"
BRUT_VAR = "*: Je vais vous prendre [NONE 10,0]. Je peux vous en donner [NONE 62,0] pièces d'or.\n"


class FauxCap:
    """Capteur factice : `fichiers` = {numéro: texte des fichiers du jeu} ; `appels` = numéros demandés."""
    def __init__(self, fichiers): self.actif = True; self.fichiers = fichiers; self.appels = []; self.sortie = []
    def vider(self): return []
    def modele(self, mid): self.appels.append(mid); return self.fichiers.get(mid)


class FauxMoteur:
    def __init__(self, cap): self.capteur = cap; self.etat = types.SimpleNamespace(partie=0xc, carte='x'); self.ui = types.SimpleNamespace(msg={'feed': False}); self.msg_visible = True


class Horloge:
    def __call__(self): return 1000.0


class TestFonctionsPures(unittest.TestCase):
    def test_cle_message(self):
        self.assertEqual(HI.cle_message(802199), 'b0802000#199')
        self.assertEqual(HI.cle_message(2002), 'b0002000#2')
        self.assertEqual(HI.cle_message(1004957), 'b1004000#957')
        self.assertEqual(HI.cle_message(1000), 'b0001000#0')

    def test_valeurs_texte_identique(self):
        self.assertEqual(HI.valeurs(BRUT_SIMPLE, HI.nettoyer(BRUT_SIMPLE)), {})
        self.assertIsNone(HI.valeurs(BRUT_SIMPLE, 'Autre texte.'))

    def test_valeurs_variables_remplacees(self):
        lu = "*: Je vais vous prendre Ragnar. Je peux vous en donner 120 pièces d'or."
        self.assertEqual(HI.valeurs(BRUT_VAR, lu), {'[NONE 10,0]': 'Ragnar', '[NONE 62,0]': '120'})
        self.assertEqual(HI.valeurs(BRUT_VAR, HI.nettoyer(BRUT_VAR)), {})                                  # (variables laissées telles quelles par le jeu : rien à retenir)
        self.assertIsNone(HI.valeurs(BRUT_VAR, "*: Je vais vous prendre Ragnar. Je peux autre chose."))     # le texte autour a changé : pas ce message
        self.assertIsNone(HI.valeurs("[NONE 1,0] et [NONE 1,0]", 'Ragnar et Alena'))                       # (même variable, deux valeurs : refusé)
        self.assertEqual(HI.valeurs("[NONE 1,0] et [NONE 1,0]", 'Ragnar et Ragnar'), {'[NONE 1,0]': 'Ragnar'})

    def test_variable_sur_plusieurs_lignes_ou_avec_point_virgule(self):
        self.assertEqual(HI.valeurs("Bonjour [NONE 1,0] !\n", 'Bonjour Maître\nZoom !'), {'[NONE 1,0]': 'Maître\nZoom'})
        self.assertEqual(HI.valeurs("Il trouve [NONE 3,0].", "Il trouve l'herbe médicinale."), {'[NONE 3,0]': "l'herbe médicinale"})        # (le « ; » du patch est déjà retiré du texte lu)

    def test_liaison_message_entier(self):
        self.assertEqual(HI.liaison(BRUT_SIMPLE, HI.nettoyer(BRUT_SIMPLE)), (None, {}))

    def test_liaison_page_d_un_message_a_pages(self):
        pages = BRUT_PAGES.split(HI.PAGE)
        self.assertEqual(HI.liaison(BRUT_PAGES, HI.nettoyer(pages[0])), (0, {}))
        self.assertEqual(HI.liaison(BRUT_PAGES, HI.nettoyer(pages[1])), (1, {}))
        self.assertEqual(HI.liaison(BRUT_PAGES, HI.nettoyer(BRUT_PAGES)), (None, {}))                      # (le moteur peut aussi donner tout le message d'un coup)
        self.assertIsNone(HI.liaison(BRUT_PAGES, 'Rien à voir.'))

    def test_liaison_page_avec_variable(self):
        brut = "Page un.\n㈡\n*: [NONE 1,0] arrive.\n"
        self.assertEqual(HI.liaison(brut, '*: Alena arrive.'), (1, {'[NONE 1,0]': 'Alena'}))

    def test_texte_lie(self):
        self.assertEqual(HI.texte_lie(BRUT_SIMPLE, None, {}), 'Il était une fois, dans un pays lointain.')
        self.assertEqual(HI.texte_lie(BRUT_PAGES, 1, {}), "*: Alors, vous restez\xa0?")
        self.assertEqual(HI.texte_lie(BRUT_PAGES, 0, {}), "*: Vous êtes née dans cette ville, n'est-ce pas\xa0?\nIl ne manquerait plus que je vous fasse\npayer.")
        self.assertEqual(HI.texte_lie(BRUT_VAR, None, {'[NONE 10,0]': 'Ragnar', '[NONE 62,0]': '120'}), "*: Je vais vous prendre Ragnar. Je peux vous en donner 120 pièces d'or.")
        self.assertEqual(HI.texte_lie(BRUT_VAR, None, {'[NONE 10,0]': 'Ragnar'}), "*: Je vais vous prendre Ragnar. Je peux vous en donner [NONE 62,0] pièces d'or.")      # variable inconnue : laissée
        self.assertEqual(HI.texte_lie(BRUT_PAGES, 5, {}), '')                                                # plus cette page
        self.assertEqual(HI.texte_lie(None, None, {}), '')
        self.assertLessEqual(len(HI.texte_lie('x' * 5000, None, {})), HI.MAX_TEXTE)

    def test_aller_retour_liaison_puis_texte(self):
        for brut, lu in ((BRUT_SIMPLE, HI.nettoyer(BRUT_SIMPLE)), (BRUT_VAR, "*: Je vais vous prendre Ragnar. Je peux vous en donner 120 pièces d'or."), (BRUT_PAGES, "*: Alors, vous restez\xa0?")):
            seg, val = HI.liaison(brut, lu); self.assertEqual(HI.texte_lie(brut, seg, val), lu)


class Base(unittest.TestCase):
    def setUp(self):
        self.dossier = tempfile.mkdtemp(prefix='hist_cle_'); self.chemin = os.path.join(self.dossier, 'fav.json')

    def tearDown(self): shutil.rmtree(self.dossier, ignore_errors=True)

    def hist(self, fichiers=None, maj=True):
        h = HI.Historique(self.chemin, Horloge())
        if fichiers is not None:
            h.cap = FauxCap(fichiers); h.m = FauxMoteur(h.cap)
            if maj: h.maj(h.m)
        return h

    def fichier(self):
        with open(self.chemin, encoding='utf-8') as f: return json.load(f)

    def brut(self):
        with open(self.chemin, encoding='utf-8') as f: return f.read()


class TestFavorisParCle(Base):
    def test_range_par_la_cle_sans_texte(self):
        h = self.hist({2002: BRUT_SIMPLE}); e = h.ajouter(HI.nettoyer(BRUT_SIMPLE), None, 10, 2002)
        self.assertTrue(h.basculer_favori(e))
        (d,) = self.fichier()['favoris']
        self.assertEqual((d['k'], d['mid'], d['nom']), ('d', 2002, None)); self.assertNotIn('texte', d); self.assertNotIn('s', d); self.assertNotIn('v', d)
        self.assertNotIn('Il était', self.brut())                           # (le texte n'est nulle part dans le fichier)

    def test_relu_avec_un_texte_modifie_dans_les_fichiers(self):
        h = self.hist({2002: BRUT_SIMPLE}); h.basculer_favori(h.ajouter(HI.nettoyer(BRUT_SIMPLE), 'Alena', 10, 2002))
        h2 = self.hist({2002: "Il était une autre fois.\n"})
        (f,) = h2.favoris; self.assertEqual((f.texte, f.nom, f.fav), ('Il était une autre fois.', 'Alena', 1))
        h3 = self.hist({2002: BRUT_SIMPLE}); self.assertEqual(h3.favoris[0].texte, 'Il était une fois, dans un pays lointain.')

    def test_page_et_variables(self):
        h = self.hist({7: BRUT_PAGES, 8: BRUT_VAR})
        h.basculer_favori(h.ajouter(HI.nettoyer(BRUT_PAGES.split(HI.PAGE)[1]), None, 1, 7))
        h.basculer_favori(h.ajouter("*: Je vais vous prendre Ragnar. Je peux vous en donner 120 pièces d'or.", None, 2, 8))
        d1, d2 = self.fichier()['favoris']
        self.assertEqual((d1['mid'], d1['s']), (7, 1)); self.assertEqual((d2['mid'], d2['v']), (8, {'[NONE 10,0]': 'Ragnar', '[NONE 62,0]': '120'}))
        h2 = self.hist({7: BRUT_PAGES.replace('restez', 'partez'), 8: BRUT_VAR.replace('prendre', 'acheter')})
        self.assertEqual([f.texte for f in h2.favoris], ["*: Alors, vous partez\xa0?", "*: Je vais vous acheter Ragnar. Je peux vous en donner 120 pièces d'or."])

    def test_garde_son_texte_quand_les_fichiers_ne_le_redonnent_pas(self):
        h = self.hist({2002: BRUT_SIMPLE}); e = h.ajouter('Un texte construit par le programme.', None, 10, 2002)        # (le numéro ne correspond pas à ce texte)
        h.basculer_favori(e); (d,) = self.fichier()['favoris']
        self.assertEqual(d['texte'], 'Un texte construit par le programme.'); self.assertNotIn('mid', d)

    def test_sans_numero_ou_sans_moteur_le_texte_est_garde(self):
        h = self.hist({2002: BRUT_SIMPLE}); h.basculer_favori(h.ajouter('Sans numéro.', None, 1))
        h2 = self.hist(); h2.basculer_favori(h2.ajouter(HI.nettoyer(BRUT_SIMPLE), None, 2, 2002))             # (pas de moteur : on ne peut pas vérifier)
        self.assertTrue(all('texte' in d for d in self.fichier()['favoris']))

    def test_message_disparu(self):
        h = self.hist({802199: BRUT_SIMPLE}); h.basculer_favori(h.ajouter(HI.nettoyer(BRUT_SIMPLE), None, 1, 802199))
        (f,) = self.hist({}).favoris
        self.assertEqual(f.texte, '(Message introuvable dans les fichiers du jeu : b0802000#199)')
        self.assertEqual((self.fichier()['favoris'][0]['mid']), 802199)                                    # (le fichier garde la clé : on peut la retrouver)
        (f,) = self.hist({802199: BRUT_PAGES}).favoris; self.assertTrue(f.texte.startswith('*: Vous êtes née'))   # le message est de retour : le texte revient

    def test_page_disparue(self):
        h = self.hist({7: BRUT_PAGES}); h.basculer_favori(h.ajouter('*: Alors, vous restez\xa0?', None, 1, 7))
        (f,) = self.hist({7: BRUT_SIMPLE}).favoris; self.assertIn('introuvable', f.texte)

    def test_le_texte_resolu_n_est_jamais_ecrit(self):
        h = self.hist({2002: BRUT_SIMPLE}); h.basculer_favori(h.ajouter(HI.nettoyer(BRUT_SIMPLE), None, 1, 2002))
        h2 = self.hist({2002: 'Nouveau.\n'}); h2.basculer_favori(h2.ajouter('Autre.', None, 5))              # un autre favori : le fichier est réécrit en entier
        d = self.fichier()['favoris'][0]; self.assertNotIn('texte', d); self.assertNotIn('Nouveau', self.brut())

    def test_retrait_du_favori(self):
        h = self.hist({2002: BRUT_SIMPLE}); e = h.ajouter(HI.nettoyer(BRUT_SIMPLE), None, 1, 2002); h.basculer_favori(e); self.assertFalse(h.basculer_favori(e))
        self.assertEqual(self.fichier()['favoris'], [])

    def test_avant_le_moteur_le_texte_attend_puis_arrive(self):
        h = self.hist({2002: BRUT_SIMPLE}); h.basculer_favori(h.ajouter(HI.nettoyer(BRUT_SIMPLE), None, 1, 2002))
        h2 = self.hist(); (f,) = h2.favoris; self.assertEqual((f.texte, f.attente), ('', True))
        h2.maj(FauxMoteur(FauxCap({2002: BRUT_SIMPLE}))); self.assertEqual((f.texte, f.attente), ('Il était une fois, dans un pays lointain.', False))

    def test_actualiser_redemande_les_textes(self):
        fichiers = {2002: BRUT_SIMPLE}; h = self.hist(fichiers); h.basculer_favori(h.ajouter(HI.nettoyer(BRUT_SIMPLE), None, 1, 2002))
        h2 = self.hist(fichiers); (f,) = h2.favoris; n0 = f.n; nb = len(h2.cap.appels); self.assertEqual(f.texte, 'Il était une fois, dans un pays lointain.')
        fichiers[2002] = 'Autre.\n'; self.assertEqual(f.texte, 'Il était une fois, dans un pays lointain.')            # (rien ne change tant qu'on ne redemande pas)
        h2.actualiser(); self.assertEqual(f.texte, 'Autre.'); self.assertNotEqual(f.n, n0); self.assertEqual(len(h2.cap.appels), nb + 1)

    def test_un_numero_d_une_autre_sorte_est_ignore(self):
        h = self.hist(); self.assertIsNone(h.ajouter('A.', None, 1, 0).mid); self.assertIsNone(h.ajouter('B.', None, 2, -4).mid)
        self.assertIsNone(h.ajouter('C.', None, 3, True).mid); self.assertIsNone(h.ajouter('D.', None, 4, 1 << 24).mid); self.assertEqual(h.ajouter('E.', None, 5, 12).mid, 12)

    def test_moteur_qui_plante(self):
        h = self.hist({2002: BRUT_SIMPLE}); h.basculer_favori(h.ajouter(HI.nettoyer(BRUT_SIMPLE), None, 1, 2002))
        h2 = self.hist()
        class Mauvais(FauxCap):
            def modele(self, mid): raise RuntimeError('émulateur')
        h2.maj(FauxMoteur(Mauvais({}))); self.assertIn('introuvable', h2.favoris[0].texte)                 # (pas d'arrêt du jeu : le favori dit que le texte manque)


class TestFichier(Base):
    def ecrire(self, favoris):
        with open(self.chemin, 'w', encoding='utf-8') as f: json.dump({'version': 2, 'suivant': 99, 'favoris': favoris}, f)

    def test_ancien_fichier_avec_texte(self):
        self.ecrire([{'k': 'd', 'id': 1, 't': 5, 'nom': 'Alena', 'texte': 'Un vieux texte.'}])
        (f,) = self.hist({1: 'Autre.\n'}).favoris; self.assertEqual((f.texte, f.lie, f.mid), ('Un vieux texte.', False, None))      # (le texte enregistré fait foi : rien n'est redemandé)

    def test_entrees_invalides_ignorees(self):
        bons = {'k': 'd', 'id': 1, 't': 5, 'nom': None, 'mid': 12}
        self.ecrire([bons, {'k': 'd', 'id': 2, 't': 5, 'nom': None, 'mid': 'x'}, {'k': 'd', 'id': 3, 't': 5, 'nom': None, 'mid': 0}, {'k': 'd', 'id': 4, 't': 5, 'nom': None, 'mid': True},
                     {'k': 'd', 'id': 5, 't': 5, 'nom': None, 'mid': 12, 's': -1}, {'k': 'd', 'id': 6, 't': 5, 'nom': None, 'mid': 12, 'v': {'a': 1}}, {'k': 'd', 'id': 7, 't': 5, 'nom': None, 'mid': 1 << 24},
                     {'k': 'd', 'id': 8, 't': 5, 'nom': None}, {'k': 'd', 'id': 9, 't': 5, 'nom': 3, 'mid': 12}, {'k': 'd', 'id': 10, 't': 5, 'nom': None, 'mid': 12, 'v': {'x' * 50: 'y'}}])
        h = HI.Historique(self.chemin, Horloge()); self.assertEqual([f.fav for f in h.favoris], [1])

    def test_aller_retour_du_dictionnaire(self):
        e = HI.Element(1, 'd', 5, 'Alena', '', fav=3, mid=802199, seg=1, val={'[NONE 1,0]': 'Ragnar'}); e.lie = True
        self.assertEqual(e.vers_dict(), {'k': 'd', 'id': 3, 't': 5, 'nom': 'Alena', 'mid': 802199, 's': 1, 'v': {'[NONE 1,0]': 'Ragnar'}})
        f = HI.Element.depuis_dict(e.vers_dict(), 9); self.assertEqual((f.mid, f.seg, f.val, f.lie, f.attente, f.nom), (802199, 1, {'[NONE 1,0]': 'Ragnar'}, True, True, 'Alena'))


class FauxCore:
    """Émulateur factice : registres, chaînes C, mémoire, noms de fonctions, appels."""
    XREG = list(range(100, 131)); LIB_BASE = 0

    def __init__(self, chaines=None, memoire=None, noms=None, exports=None, texte_moteur=None):
        self.chaines = chaines or {}; self.memoire = memoire or {}; self.noms = noms or {}; self.exports = exports or {}; self.texte_moteur = texte_moteur or {}; self.appels = []; self.tampon = 0x5000
    def read_cstr(self, a): return self.chaines[a] if a in self.chaines else self.memoire.get(('s', a), b'')
    def mem(self, a, n): return self.memoire[a][:n]
    def where(self, a): return self.noms.get(a, '?+0')
    def export(self, nom): return self.exports.get(nom)
    def malloc(self, n): return self.tampon
    def mem_w(self, a, b): self.memoire[('s', a)] = b''
    def call(self, f, tampon, ident, label='', timeout_s=0):
        self.appels.append((f, tampon, ident)); self.memoire[('s', tampon)] = self.texte_moteur.get(ident, ('<ERR 0x%08x.%d>' % (ident & 0xff000000, ident & 0xffffff)).encode())


class TestCapteur(unittest.TestCase):
    def capteur(self, pile, mid=802199, texte='Bonjour.'):
        noms, memoire, fp = {0x1000: pile[0] + '+8'}, {0x9000 + 4: b'\x05\x00\x00\x00\x42\x00\x00\x00'}, 0x2000
        for i, n in enumerate(pile[1:]):
            memoire[fp] = (fp + 0x100).to_bytes(8, 'little') + (0x1100 + i).to_bytes(8, 'little'); noms[0x1100 + i] = n + '+4'; fp += 0x100
        memoire[fp] = bytes(16)
        c = FauxCore({0x10: texte.encode()}, memoire, noms)
        regs = {c.XREG[0]: 0x100000000 | mid if mid is not None else 0, c.XREG[1]: 0x10, c.XREG[2]: 0, c.XREG[30]: 0x1000, c.XREG[29]: 0x2000}
        cap = HI.Capteur.__new__(HI.Capteur); cap.actif = True; cap.sortie = []; cap.c = c; cap.g_game = 0x9000; cap._mid = None; cap._tampon = None
        cap.m = types.SimpleNamespace(etat=types.SimpleNamespace(partie=0xc, carte='caf1'))
        uc = types.SimpleNamespace(reg_read=lambda r: regs[r])
        if mid is not None: cap._add(uc, 0, 0, None)
        cap._cat(uc, 0, 0, None)
        return cap, cap.vider()

    def test_numero_capte_quand_cat_est_appelee_par_ui_msgadd(self):
        cap, (r,) = self.capteur((HI.SYM_UI_MSGADD, 'addMessageCount', 'racine')); self.assertEqual((r['mid'], r['texte']), (802199, 'Bonjour.')); self.assertEqual(cap._mid, 802199)      # (le 32 bits bas seulement)

    def test_pas_de_numero_quand_cat_vient_d_ailleurs(self):
        for pile in (('Foo::bar', HI.SYM_UI_MSGADD, 'racine'), ('Foo::bar', 'racine')):
            _cap, (r,) = self.capteur(pile); self.assertIsNone(r['mid'], pile)

    def test_numero_ancien_non_reutilise_sans_ui_msgadd(self):
        cap, _ = self.capteur((HI.SYM_UI_MSGADD, 'racine'), mid=12)
        c = cap.c; regs = {c.XREG[1]: 0x10, c.XREG[2]: 0, c.XREG[30]: 0x1000, c.XREG[29]: 0x2000}; c.noms[0x1000] = 'Foo::bar+8'
        cap._cat(types.SimpleNamespace(reg_read=lambda r: regs[r]), 0, 0, None); self.assertIsNone(cap.vider()[0]['mid'])

    def test_historique_recoit_le_numero(self):
        _cap, rs = self.capteur((HI.SYM_UI_MSGADD, 'racine'), mid=2002)
        h = HI.Historique(None); m = FauxMoteur(FauxCap({})); m.capteur.vider = lambda: rs; h.maj(m); self.assertEqual([(e.mid, e.texte) for e in h.dialogues], [(2002, 'Bonjour.')])

    def test_modele(self):
        c = FauxCore(exports={HI.SYM_EXTRACT: 0x777}, texte_moteur={(1 << 24) | 2002: 'Il était une fois.\n'.encode()})
        cap = HI.Capteur.__new__(HI.Capteur); cap.c = c; cap._tampon = None
        self.assertEqual(cap.modele(2002), 'Il était une fois.\n'); self.assertEqual(c.appels[0][0], 0x777); self.assertEqual(c.appels[0][2], (1 << 24) | 2002)      # genre 1 : message
        self.assertIsNone(cap.modele(5)); self.assertIsNone(cap.modele(0)); self.assertIsNone(cap.modele(-3)); self.assertIsNone(cap.modele('x')); self.assertIsNone(cap.modele(1 << 24))      # (« <ERR ... > » : inconnu)
        cap2 = HI.Capteur.__new__(HI.Capteur); cap2.c = FauxCore(); cap2._tampon = None; self.assertIsNone(cap2.modele(2002))                                                        # (symbole absent)


@unittest.skipUnless(os.environ.get('DQ_APK') and os.environ.get('DQ_SAVES'), 'moteur : DQ_APK et DQ_SAVES')
class TestVraiMoteur(unittest.TestCase):
    """Le debut d'une sauvegarde de prologue avec le vrai moteur (sauvegarde 1 : messages 2002 a 2011 du fichier b0002000) : numeros captes, favori range par la cle, relu dans un second moteur."""
    @classmethod
    def setUpClass(cls):
        from dq4_pc.noyau import moteur as MO
        cls.MO = MO; cls.dossier = tempfile.mkdtemp(prefix='hist_cle_mo_')

    @classmethod
    def tearDownClass(cls): shutil.rmtree(cls.dossier, ignore_errors=True)

    def moteur(self): return self.MO.Moteur(os.environ['DQ_APK'], os.environ['DQ_SAVES'], tempfile.mkdtemp(dir=self.dossier))

    def jouer(self, chemin):
        """Premiere sauvegarde (la 1 par defaut, ou DQ_SLOT_PROLOGUE, puis les autres) dont le debut dit au moins 3 dialogues avec la touche A : (moteur, historique) ; None si aucune."""
        essais = [int(os.environ['DQ_SLOT_PROLOGUE'])] if os.environ.get('DQ_SLOT_PROLOGUE') else [1, 2, 3, 5, 9]
        for slot in essais:
            mo = self.moteur(); h = HI.Historique(chemin)
            for _ in range(3): mo.step(0, 0); h.maj(mo)
            try:
                if not mo.charger_sauvegarde(slot): continue
            except Exception: continue
            for i in range(1800): mo.step(0, 0x10 if i % 9 == 5 else 0); h.maj(mo)
            if len(h.dialogues) >= 3: return mo, h
        return None

    def test_de_bout_en_bout(self):
        chemin = os.path.join(self.dossier, 'fav.json'); r = self.jouer(chemin)
        if r is None: self.skipTest('aucune de ces sauvegardes ne commence par des dialogues (DQ_SLOT_PROLOGUE : le numero de la sauvegarde du prologue)')
        mo, h = r; self.assertTrue(all(e.mid for e in h.dialogues))
        premier = h.dialogues[0]
        self.assertTrue(h.basculer_favori(premier))
        with open(chemin, encoding='utf-8') as f: d = json.load(f)['favoris'][0]
        self.assertEqual(d['mid'], premier.mid); self.assertNotIn('texte', d)
        mo2 = self.moteur(); h2 = HI.Historique(chemin)
        for _ in range(5): mo2.step(0, 0); h2.maj(mo2)
        self.assertEqual(h2.favoris[0].texte, premier.texte)                                               # (le moteur redonne le texte lu)
        vrai = mo2.capteur.modele; mo2.capteur.modele = lambda mid: (vrai(mid) or '').replace(premier.texte[:2], '##') if mid == premier.mid else vrai(mid)
        h3 = HI.Historique(chemin); h3.maj(mo2); self.assertTrue(h3.favoris[0].texte.startswith('##'))     # (un texte modifie dans le patch se repercute)


if __name__ == '__main__':
    unittest.main(verbosity=1)
