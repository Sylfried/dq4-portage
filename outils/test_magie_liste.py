"""Menu Magie du terrain (Make_NameButton, Make_MagicInfo, Make_TargetCharaList) et usages sans effet : le moteur d'origine decide.

    python3 outils/test_magie_liste.py                                          (partie interface : Linux sans ecran, pyglet en mode « headless »)
    DQ_APK=<dossier des APK patches> DQ_SAVES=<dossier des sauvegardes> python3 outils/test_magie_liste.py      (ajoute les scenarios du moteur reel)

Partie interface (sans moteur) : la liste de boutons nommes (type 8) recoit du moteur son code 6 = preset de mise en page (`MenuPortItemTable.name_button_param`). Sans lui, la 5e rangee restait
visible et cliquable : un toucher y envoyait au moteur un sort inexistant (<ERR 0x07000000.0> a l'ecran, « Cout en PM  0/ 30 »).
  1. preset 0 (4 rangees : liste des sorts) : seules les rangees dont le code n'est pas 0 sont des zones tactiles ; les rangees 4 et 5 n'existent pas ;
  2. preset 1 (5 rangees : menu Utiliser / Transferer / Abandonner) ; presets 2 a 4 : ordonnee de la premiere rangee, rangees suivantes a 67 au-dessous ;
  3. le code 6 rejoue (ou arrive apres les codes de rangee) ne decale pas deux fois ; un preset inconnu est ignore ; revenir au preset 0 remet les rangees en place ;
  4. la ligne de cout « Cout en PM:<tab>  2 » (TextMesh.tabSize 8) : la tabulation devient 8 espaces dans la liste des magies seulement (un texte sans tabulation ou sans tabSize ne change pas).

  4 bis. la ligne de cout de la fiche d'un sort (type 7, texte 2) porte la limite droite de son cadre (Rendu._texte la comprime pour qu'elle y tienne) ; les autres textes de la fiche ne le sont pas.

Partie moteur (DQ_APK et DQ_SAVES : les sauvegardes sont ouvertes en lecture seule, le moteur ecrit dans un dossier temporaire ; groupe de l'emplacement 1 : Ragnar sans PM et Doc, 30 PM, qui sait « Premiers secours ») :
  5. liste de Doc : une seule rangee, « Premiers secours », code de rangee 2, rangees 1 a 3 cachees ;
  6. Premiers secours sur Ragnar blesse : PM 30 -> 28, PV 20 -> 47 ; sur Ragnar aux PV pleins : AUCUN PM depense (BaseAction::useMp ne depense que si l'action a eu un effet) et, hors combat, « Mais il ne se passe rien. » (message officiel d'Evac', id 0xc3d6d) a la place du message de succes
     des soins (crochet Moteur._crochets_magie ; ATTENDU CHANGE VOLONTAIREMENT : avant, le moteur affichait « Les blessures de Ragnar guerissent ! » sans depenser de PM) ;
  7. usages sans effet decides par le moteur : Rappel sur un vivant, Antipoison sans poison : « Mais rien ne se passe. », aucun PM depense ; PM insuffisants : « Pas assez de PM ! » ;
  8. Rappel sur un mort : « revient a la vie », PM depenses ; Antipoison sur un empoisonne : « n'est plus empoisonne » ;
  9. regle « sort qui coute des PM et n'en depense aucun » : soins a PV pleins (Premiers secours, Soins partiels, Soins complets), soin de groupe (Multisoin : un seul message, pas de bruitage de soin en attente) ;
     non-regressions : sort a effet (PM depenses, message du jeu), Multisoin avec un blesse (messages de soin gardes), messages d'echec propres au jeu (Evac' hors donjon), sorts a 0 PM (Mappille, Sifflet).
 10. bruitages (SoundManager::playSe, #137) : le bruitage de lancement (306, le meme pour tous les sorts) est joue dans tous les cas ; le bruitage de soin (501) n'est PAS joue quand le sort n'a eu aucun effet (Premiers secours, Soins partiels,
     Soins complets sur PV pleins ; Multisoin en pleine forme) et reste joue quand le sort sert (deux fois pour un soin sur une cible, une fois par cible pour Multisoin) ; un soin utile apres un soin inutile joue de nouveau son bruitage."""
import os, struct, sys, tempfile, types, unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'dq4_pc'))
import pyglet
if sys.platform.startswith('linux') and not os.environ.get('DISPLAY'): pyglet.options['headless'] = True; pyglet.options['shadow_window'] = False
import ui_menu as UM

APK, SAVES = os.environ.get('DQ_APK'), os.environ.get('DQ_SAVES')


def type_liste():
    """Make_NameButton minimal : la racine puis 6 rangees (parts[1 + k], bouton k, ordonnee 382 - 67 k) avec un texte fils chacune."""
    carre = {'vtx': [[-100.0, 10.0], [100.0, 10.0], [100.0, -10.0], [-100.0, -10.0]], 'uv': [[0, 0], [1, 0], [1, 1], [0, 1]], 'sub': {'0': [0, 1, 2, 0, 2, 3]}}
    nodes = [{'id': 1, 'par': None, 'pos': [0.0, 0.0, 0.0], 'act': True, 'mats': []}]; parts = [{'node': 1, 'ib': []}]
    for k in range(6):
        z = 382.0 - 67.0 * k
        nodes.append({'id': 100 + k, 'par': 1, 'pos': [0.0, 4.0, z], 'act': True, 'mats': [{'sheet': 1, 'part': 7, 'color': [1, 1, 1, 1], 'shader': 'parts', 'offset': None}], 'mesh': carre, 'parts': {'buttonId': k, 'gamepad': 16}})
        nodes.append({'id': 200 + k, 'par': 100 + k, 'pos': [0.0, 8.0, z - 5.0], 'act': True, 'text': {'font': 'font', 'characterSize': 10.0, 'text': None}, 'mats': []})
        parts.append({'node': 100 + k, 'ib': [{'k': 'button'}, {'k': 'text', 'go': 200 + k, 'variant': 0}]})
    nodes.append({'id': 300, 'par': 100, 'pos': [20.0, 12.0, 340.0], 'act': True, 'text': {'font': 'font', 'characterSize': 6.63, 'text': None, 'anchor': 3, 'alignment': 0, 'lineSpacing': 0.84, 'tabSize': 8.0}, 'mats': []})      # ligne de cout de la rangee 0
    nodes.append({'id': 301, 'par': 100, 'pos': [20.0, 12.0, 340.0], 'act': True, 'text': {'font': 'font', 'characterSize': 6.63, 'text': None, 'anchor': 3, 'alignment': 0, 'lineSpacing': 0.84}, 'mats': []})              # meme ancrage, sans tabSize
    return {'name': 'Make_NameButton()', 'err': None, 'nodes': nodes, 'parts': parts,
            'params': [{'id': k, 'no': 0, 'parts': 1 + k, 'base': 0} for k in range(6)], 'builds': [],
            'codes': [{'id': k, 'kind': 'func', 'method': 'Sub_NameButton', 'fx': {'-1': {'err': None, 'd': {}}, '0': {'err': None, 'd': {str(100 + k): {'act': False}}}, '1': {'err': None, 'd': {}}, '2': {'err': None, 'd': {}}}} for k in range(5)]}


def fenetre():
    ml = types.SimpleNamespace(types={'8': type_liste()}, infos=[], cadres=[], hdr={'lang': {'hiro': 1.0}}, pousse=(0.0, 0.0))
    return UM.Fenetre(ml, 8)


def zones(fe): return sorted(b[0] for b in fe.boutons())
def z_rangee(fe, k): return fe.N[100 + k]['pos'][2]


class TestListeNoms(unittest.TestCase):
    def test_presets_exportes(self):
        """Les 5 presets du moteur (NAME_BUTTON_Y / NAME_BUTTON_DY) : nombre de rangees, ordonnee de la premiere, pas."""
        self.assertEqual(UM.NOMS_PRESETS[0], (4, 382.0, 67.0)); self.assertEqual(UM.NOMS_PRESETS[1], (5, 382.0, 67.0)); self.assertEqual(len(UM.NOMS_PRESETS), 5)
        self.assertEqual((UM.NOMS_DEPART, UM.NOMS_PAS), (382.0, 67.0))

    def test_liste_des_sorts_une_rangee(self):
        """Doc sait un sort : codes 0 = 2 (deux lignes), 1 a 3 = 0, code 6 = 0. Seule la rangee 0 est une zone tactile (la 5e, fantome, menait a <ERR 0x07000000.0>)."""
        fe = fenetre()
        self.assertEqual(zones(fe), [0, 1, 2, 3, 4, 5], 'avant le code 6 : tout est visible (etat exporte)')
        for i, v in ((0, 2), (1, 0), (2, 0), (3, 0), (6, 0)): fe.code(i, v)
        self.assertEqual(zones(fe), [0])
        for k in range(1, 6): self.assertFalse(fe.N[100 + k]['act'], k)

    def test_liste_des_sorts_quatre_rangees(self):
        fe = fenetre()
        fe.code(6, 0)
        for i in range(4): fe.code(i, 2)
        self.assertEqual(zones(fe), [0, 1, 2, 3])                          # 4 rangees au plus : ni la 5e ni la 6e
        fe.code(2, 0)
        self.assertEqual(zones(fe), [0, 1, 3])

    def test_code_6_avant_ou_apres_les_codes_de_rangee(self):
        fe = fenetre()
        for i, v in ((0, 1), (1, 0), (2, 0), (3, 0), (4, 0)): fe.code(i, v)           # rejeu d'une fenetre : les codes de rangee d'abord
        fe.code(6, 1)
        self.assertEqual(zones(fe), [0])
        fe2 = fenetre(); fe2.code(6, 1)
        for i, v in ((0, 1), (1, 1), (2, 1), (3, 0), (4, 0)): fe2.code(i, v)
        self.assertEqual(zones(fe2), [0, 1, 2])                            # menu Utiliser / Transferer / Abandonner : preset 1, trois rangees

    def test_positions_des_presets(self):
        fe = fenetre()
        base = [z_rangee(fe, k) for k in range(6)]
        for preset, (nb, depart, pas) in enumerate(UM.NOMS_PRESETS):
            fe.code(6, preset)
            for k in range(6):
                self.assertAlmostEqual(z_rangee(fe, k), base[k] + (depart - pas * k) - (382.0 - 67.0 * k), msg=(preset, k))
                self.assertAlmostEqual(fe.N[200 + k]['pos'][2], base[k] - 5.0 + (depart - pas * k) - (382.0 - 67.0 * k), msg=('texte', preset, k))      # le texte suit sa plaque
        fe.code(6, 0)
        self.assertEqual([z_rangee(fe, k) for k in range(6)], base)        # retour au preset 0 : tout est remis en place

    def test_pas_de_double_decalage(self):
        fe = fenetre(); fe.code(6, 2); a = [z_rangee(fe, k) for k in range(6)]
        fe.code(6, 2); fe.code(6, 2)
        self.assertEqual([z_rangee(fe, k) for k in range(6)], a)

    def test_preset_inconnu_ignore(self):
        fe = fenetre(); avant = [(z_rangee(fe, k), fe.N[100 + k]['act']) for k in range(6)]
        for c in (-1, 5, 99, None, 'x', 1.5): fe.code(6, c)
        self.assertEqual([(z_rangee(fe, k), fe.N[100 + k]['act']) for k in range(6)], avant)


class TestLigneDeCout(unittest.TestCase):
    """« Cout en PM:<tab>  2 » : TextMesh.tabSize (8) fait de la tabulation 8 espaces ; la police du jeu n'a pas de glyphe pour la tabulation (largeur nulle) et le nombre collait a l'etiquette au lieu d'etre dans la colonne de droite."""
    def test_tabulation_de_la_ligne_de_cout(self):
        fe = fenetre()
        fe.params[(0, 1)] = {'id': 0, 'no': 1, 'parts': 1, 'base': 2}
        fe.parts[1]['ib'].append({'k': 'text', 'go': 300, 'variant': 0})
        self.assertEqual(fe.N[300]['text'].get('tabSize'), 8.0)
        fe.param_str(0, 1, 'Coût en PM:\t  2')
        self.assertEqual(fe.N[300]['text']['text'], 'Coût en PM:' + ' ' * 8 + '  2')
        fe.param_str(0, 1, 'Coût en PM:\t 10')
        self.assertEqual(fe.N[300]['text']['text'], 'Coût en PM:' + ' ' * 8 + ' 10')           # le champ du nombre garde sa largeur : la colonne reste alignee

    def test_texte_sans_tabulation_inchange(self):
        fe = fenetre()
        fe.params[(0, 1)] = {'id': 0, 'no': 1, 'parts': 1, 'base': 2}
        fe.parts[1]['ib'].append({'k': 'text', 'go': 300, 'variant': 0})
        fe.param_str(0, 1, 'Premiers secours'); self.assertEqual(fe.N[300]['text']['text'], 'Premiers secours')

    def test_sans_tabsize_la_tabulation_reste(self):
        fe = fenetre()                                                     # le texte 301 n'a pas de tabSize : rien n'est remplace
        fe.params[(0, 1)] = {'id': 0, 'no': 1, 'parts': 1, 'base': 2}
        fe.parts[1]['ib'].append({'k': 'text', 'go': 301, 'variant': 0})
        fe.param_str(0, 1, 'a\tb'); self.assertEqual(fe.N[301]['text']['text'], 'a\tb')


class TestFicheDuSort(unittest.TestCase):
    """Fiche d'un sort (Make_MagicInfo, type 7) : « Cout en PM 10/ 30 » (FR) est plus long que « MP Cost 10/ 30 » et sortait de son cadre : la ligne de cout (texte 2) porte la limite droite de son cadre (fit_x) : Rendu._texte la comprime pour qu'elle y tienne
    meme avec la police d'origine ; le nom, la description et « Lancer » gardent leur mise en page."""
    def fenetre(self):
        def texte(nid, ancre): return {'id': nid, 'par': 1, 'pos': [75.0, 12.0, 103.0], 'act': True, 'text': {'font': 'font', 'characterSize': 9.945, 'text': None, 'anchor': ancre, 'alignment': 0, 'lineSpacing': 0.88}, 'mats': []}
        t = {'name': 'Make_MagicInfo()', 'err': None, 'nodes': [{'id': 1, 'par': None, 'pos': [0.0, 0.0, 0.0], 'act': True, 'mats': []}] + [texte(10 + k, 0) for k in range(4)],
             'parts': [{'node': 1, 'ib': [{'k': 'text', 'go': 10 + k, 'variant': 0} for k in range(4)]}], 'params': [{'id': 0, 'no': k, 'parts': 0, 'base': k} for k in range(4)], 'codes': [], 'builds': []}
        return UM.Fenetre(types.SimpleNamespace(types={'7': t}, infos=[], cadres=[], hdr={'lang': {'hiro': 1.0}}, pousse=(0.0, 0.0)), 7)

    def test_seule_la_ligne_de_cout_est_marquee(self):
        fe = self.fenetre()
        for no, s in enumerate(('Premiers secours', "Restaure au moins 30\r\nPV d'un seul allié.", 'Coût en PM  2/ 30', 'Lancer')): fe.param_str(0, no, s)
        self.assertEqual([fe.N[10 + k].get('fit_x') for k in range(4)], [None, None, UM.COUT_FICHE_X_MAX, None])
        self.assertEqual(fe.N[12]['text']['text'], 'Coût en PM  2/ 30')           # le texte lui-meme n'est pas modifie

    def test_la_description_porte_la_largeur_de_son_cadre(self):
        fe = self.fenetre()
        for no, s in enumerate(('Premiers secours', "Restaure au moins 30\r\nPV d'un seul allié.", 'Coût en PM  2/ 30', 'Lancer')): fe.param_str(0, no, s)
        self.assertEqual([(fe.N[10 + k].get('wrap_x'), fe.N[10 + k].get('wrap_n')) for k in range(4)], [(None, None), (UM.DESC_FICHE_X_MAX, 2), (None, None), (None, None)])
        self.assertEqual(fe.N[11]['text']['text'], "Restaure au moins 30\r\nPV d'un seul allié.")           # le texte du moteur n'est pas modifie (c'est le rendu qui recoupe)


class TestRecoupeDescription(unittest.TestCase):
    """Rendu._recoupe : la description francaise d'un sort a 3 ou 4 lignes (cadre de 2) est recoupee a la largeur du cadre (police fictive : 9 unites par caractere, cadre de 361 unites = 40 caracteres)."""
    DISPO = 148.0 + 213.0
    def recoupe(self, texte):
        r = object.__new__(UM.Rendu)
        r.textes = types.SimpleNamespace(bitmap=types.SimpleNamespace(largeur=lambda x: 9.0 * len(x)))
        return r._recoupe(texte.split('\n'), self.DISPO, r.textes.bitmap, 1.0, 1.0, 1.0, 9.0)

    def test_quatre_lignes_en_deux(self):
        for t in ("Permet de sortir\r\nimmédiatement des\r\ndonjons, grottes et\r\ntours.", "Génère une aura\r\nsacrée qui éloigne les\r\nmonstres les plus\r\nfaibles."):
            out = self.recoupe(t)
            self.assertEqual(len(out), 2, out)
            self.assertEqual(' '.join(out), ' '.join(l.strip() for l in t.split('\n')))          # aucun mot perdu ni ajoute
            self.assertTrue(all(9.0 * len(l) <= self.DISPO for l in out), out)

    def test_trois_lignes_en_deux(self):
        out = self.recoupe("Ressuscite un allié\r\nmort en lui octroyant\r\nla moitié de ses PV.")
        self.assertEqual(len(out), 2, out)

    def test_pas_plus_de_lignes_qu_avant(self):
        t = "a" * 30 + "\r\n" + "b" * 30 + "\r\n" + "c" * 30                                      # 3 lignes de 30 : recoupees a 40 elles feraient encore 3 lignes : texte laisse tel quel
        self.assertEqual(self.recoupe(t), t.split('\n'))


def _stat(mo, i):
    return struct.unpack_from('<4H', mo.core.mem(mo.core.export('_ZN6status9PartyData15originalPlayer_E') + 0x530 * i + 0x58, 0x30), 0x22)          # PV, PV max, PM, PM max


@unittest.skipUnless(APK and SAVES, 'moteur reel : DQ_APK=<dossier des APK patches> DQ_SAVES=<dossier des sauvegardes>')
class MoteurReel(unittest.TestCase):
    RAGNAR, DOC = 3, 12                                                   # emplacements de PlayerStatus dans originalPlayer_ (groupe de l'emplacement 1)
    PREMIERS_SECOURS, RAPPEL, ANTIPOISON = 196, 200, 202                   # identifiants d'action des sorts du terrain
    MULTISOIN, EVAC, PASSAGE_SUR, MAPPILLE, SIFFLET = 199, 204, 206, 209, 216          # (Multisoin : 10 PM, sans cible ; Evac' : 1 PM ; Passage sur : 2 PM ; Mappille et Sifflet : 0 PM)
    BTN_MENU, BTN_PAROLE = 0x800, 0x100

    def avance(self, mo, n, decl=0):
        for i in range(n): mo.step(0, decl if i == 0 else 0)

    def pret(self, sort=None, pv=None, pm=30, poison=False):
        import moteur as MO
        mo = MO.Moteur(APK, SAVES, tempfile.mkdtemp(prefix='sv_magie_')); mo.charger_sauvegarde(1); self.avance(mo, 120)
        for _ in range(30):                                                # le dialogue d'ouverture doit etre ferme et le joueur libre
            self.avance(mo, 1, self.BTN_PAROLE); self.avance(mo, 20)
            if not mo.msg_visible and not (mo.drapeaux() & 4): break
        self.avance(mo, 30); c = mo.core
        orig = c.export('_ZN6status9PartyData15originalPlayer_E'); hs = lambda i: orig + 0x530 * i + 0x58
        if sort is not None:
            ha = orig + 0x530 * self.DOC + 0xd0
            c.call(c.export('_ZN6status10HaveAction5clearEv'), ha); c.call(c.export('_ZN6status10HaveAction3addEii'), ha, sort, 0)
        c.mem_w(hs(self.DOC) + 0x26, struct.pack('<H', pm))
        for i, v in (pv or {}).items(): c.mem_w(hs(i) + 0x22, struct.pack('<H', v))
        if poison: c.call(c.export('_ZN6status14HaveStatusInfo9setPoisonEv'), hs(self.RAGNAR) - 0x48)          # HaveStatusInfo = HaveStatus - 0x48
        mo.capteur.vider()
        return mo

    def ouvrir_liste(self, mo):
        self.avance(mo, 1, self.BTN_MENU); self.avance(mo, 20)
        mo.envoyer_menu(4, 1, 1, 0x10); self.avance(mo, 20)               # menu racine : « Magie »
        mo.envoyer_menu(5, 1, 3, 0x10); self.avance(mo, 25)               # liste des personnages : Doc

    def lancer(self, mo, cible=0):
        self.ouvrir_liste(mo)
        mo.envoyer_menu(8, 1, 0, 0x10); self.avance(mo, 20)               # le sort de la rangee 0
        mo.envoyer_menu(6, 1, cible, 0x10); self.avance(mo, 3)            # la cible
        return self.messages(mo)

    def lancer_groupe(self, mo):
        """Sort de groupe ou sans cible : la fiche du sort (port 8, bouton « Lancer » = rangee 2), pas de choix de cible."""
        self.ouvrir_liste(mo)
        mo.envoyer_menu(8, 1, 0, 0x10); self.avance(mo, 20)
        self.assertEqual(mo.ui.f[8]['cases'].get((2, 0)), 'Lancer')
        mo.envoyer_menu(8, 1, 2, 0x10); self.avance(mo, 3)
        return self.messages(mo)

    def messages(self, mo):
        textes = []
        for k in range(500):
            self.avance(mo, 1)
            for t in (x['texte'] for x in mo.capteur.vider()):
                if not textes or textes[-1] != t: textes.append(t)
            if mo.msg_visible and k % 30 == 29: self.avance(mo, 1, self.BTN_PAROLE)
            if not mo.msg_visible and k > 60: break
        return [t.replace('\xa0', ' ').replace(';', '').strip() for t in textes]

    LANCEMENT, SOIN = 306, 501                                              # SoundManager::playSe : bruitage de lancement (tous les sorts) ; bruitage de soin

    def sons(self, mo):
        """Liste (remplie au fil de l'eau) des bruitages `SoundManager::playSe` joues par le moteur a partir de maintenant ; le bruitage 300 (validation d'une touche dans les messages) est ecarte."""
        import unicorn
        c = mo.core; liste = []; a = c.export('_ZN12SoundManager6playSeEi')
        c.uc.hook_add(unicorn.UC_HOOK_CODE, lambda uc, ad, sz, u: liste.append(uc.reg_read(c.XREG[0]) & 0xffffffff), None, a, a); c.uc.ctl_flush_tb()
        return liste

    def bruitages(self, sort, pv, groupe=False):
        mo = self.pret(sort=sort, pv=pv); sons = self.sons(mo)
        textes = self.lancer_groupe(mo) if groupe else self.lancer(mo)
        return textes, [x for x in sons if x != 300]

    def test_bruitages_soin_sans_effet(self):
        for sort in (self.PREMIERS_SECOURS, self.PREMIERS_SECOURS + 1, self.PREMIERS_SECOURS + 2):
            textes, sons = self.bruitages(sort, {self.RAGNAR: 47})
            self.assertEqual(textes[-1], 'Mais il ne se passe rien.'); self.assertEqual(sons, [self.LANCEMENT], 'sort %d : le lancement reste, le bruitage de soin est coupe' % sort)

    def test_bruitages_soin_utile_gardes(self):
        for sort in (self.PREMIERS_SECOURS, self.PREMIERS_SECOURS + 1, self.PREMIERS_SECOURS + 2):
            textes, sons = self.bruitages(sort, {self.RAGNAR: 20})
            self.assertIn('Les blessures de Ragnar guérissent !', textes); self.assertEqual(sons, [self.LANCEMENT, self.SOIN, self.SOIN], 'sort %d' % sort)

    def test_bruitages_soin_de_groupe(self):
        textes, sons = self.bruitages(self.MULTISOIN, {self.RAGNAR: 47, self.DOC: 35}, groupe=True)
        self.assertEqual(textes[-1], 'Mais il ne se passe rien.'); self.assertEqual(sons, [self.LANCEMENT])
        textes, sons = self.bruitages(self.MULTISOIN, {self.RAGNAR: 20, self.DOC: 35}, groupe=True)
        self.assertEqual(sons, [self.LANCEMENT, self.SOIN, self.SOIN], 'un bruitage de soin par cible soignee')

    def test_bruitage_de_soin_revient_apres_un_echec(self):
        mo = self.pret(pv={self.RAGNAR: 47}); sons = self.sons(mo)
        self.lancer(mo); self.assertEqual([x for x in sons if x != 300], [self.LANCEMENT])
        c = mo.core; orig = c.export('_ZN6status9PartyData15originalPlayer_E'); c.mem_w(orig + 0x530 * self.RAGNAR + 0x58 + 0x22, struct.pack('<H', 20))
        self.avance(mo, 60); del sons[:]
        textes = self.lancer(mo)
        self.assertIn('Les blessures de Ragnar guérissent !', textes); self.assertEqual([x for x in sons if x != 300], [self.LANCEMENT, self.SOIN, self.SOIN])

    def test_liste_de_doc(self):
        mo = self.pret(); self.ouvrir_liste(mo)
        f = mo.ui.f[8]
        self.assertEqual(f['type'], 8)
        self.assertEqual(f['cases'][(0, 0)], 'Premiers secours'); self.assertTrue(f['cases'][(0, 1)].startswith('Coût en PM'))
        self.assertEqual([f['indic'].get(i) for i in (0, 1, 2, 3, 6)], [2, 0, 0, 0, 0])      # rangee 0 sur deux lignes, 1 a 3 cachees, preset 0

    def test_soin_sur_blesse(self):
        mo = self.pret(pv={self.RAGNAR: 20}); textes = self.lancer(mo)
        self.assertEqual(_stat(mo, self.RAGNAR)[0], 47); self.assertEqual(_stat(mo, self.DOC)[2], 28)
        self.assertIn('Les blessures de Ragnar guérissent !', textes)

    def test_soin_sur_pv_pleins_sans_pm(self):
        mo = self.pret(pv={self.RAGNAR: 47}); textes = self.lancer(mo)
        self.assertEqual(_stat(mo, self.DOC)[2], 30, 'le moteur ne depense pas de PM quand le soin n\'a servi a rien')
        self.assertEqual(_stat(mo, self.RAGNAR)[0], 47)
        self.assertEqual(textes, ['Doc lance le sort Premiers secours !', 'Mais il ne se passe rien.'])          # le message officiel d'Evac' (id 0xc3d6d), pas « Les blessures de Ragnar guérissent ! »

    def test_pm_insuffisants(self):
        mo = self.pret(pv={self.RAGNAR: 20}, pm=1); textes = self.lancer(mo)
        self.assertEqual(textes, ['Pas assez de PM !'])
        self.assertEqual(_stat(mo, self.DOC)[2], 1); self.assertEqual(_stat(mo, self.RAGNAR)[0], 20)

    def test_rappel_sur_un_vivant(self):
        mo = self.pret(sort=self.RAPPEL, pv={self.RAGNAR: 47}); textes = self.lancer(mo)
        self.assertEqual(textes[-1], 'Mais rien ne se passe.'); self.assertEqual(_stat(mo, self.DOC)[2], 30)

    def sort_sur(self, sort, pv, groupe=False, **kw):
        mo = self.pret(sort=sort, pv=pv, **kw); pm0 = _stat(mo, self.DOC)[2]
        textes = self.lancer_groupe(mo) if groupe else self.lancer(mo)
        return mo, textes, pm0, _stat(mo, self.DOC)[2]

    def test_soins_a_pv_pleins_toutes_puissances(self):
        for sort, nom in ((self.PREMIERS_SECOURS + 1, 'Soins partiels'), (self.PREMIERS_SECOURS + 2, 'Soins complets')):
            mo, textes, pm0, pm1 = self.sort_sur(sort, {self.RAGNAR: 47})
            self.assertEqual(textes, ['Doc lance le sort %s !' % nom, 'Mais il ne se passe rien.']); self.assertEqual((pm0, pm1), (30, 30), nom)

    def test_soin_de_groupe_en_pleine_forme(self):
        mo, textes, pm0, pm1 = self.sort_sur(self.MULTISOIN, {self.RAGNAR: 47, self.DOC: 35}, groupe=True)
        self.assertEqual(textes, ['Doc lance le sort Multisoin !', 'Mais il ne se passe rien.'], 'une seule fois, pas une fois par personnage'); self.assertEqual((pm0, pm1), (30, 30))
        self.assertEqual(mo.core.mem(mo.L + 0x257f84, 1)[0], 0, 'plus de bruitage de soin en attente (le moteur en joue un par cible restante)')

    def test_soin_de_groupe_avec_un_blesse_garde_ses_messages_et_ses_pm(self):
        mo, textes, pm0, pm1 = self.sort_sur(self.MULTISOIN, {self.RAGNAR: 20, self.DOC: 35}, groupe=True)
        self.assertEqual(textes, ['Doc lance le sort Multisoin !', 'Les blessures de Ragnar guérissent !', 'Les blessures de Doc guérissent !']); self.assertEqual((pm0, pm1), (30, 20))
        self.assertGreater(_stat(mo, self.RAGNAR)[0], 20)

    def test_sort_avec_effet_sans_message_de_resultat_depense_ses_pm(self):
        mo, textes, pm0, pm1 = self.sort_sur(self.PASSAGE_SUR, {self.RAGNAR: 47}, groupe=True)
        self.assertEqual(textes, ['Doc lance le sort Passage sûr !']); self.assertEqual((pm0, pm1), (30, 28))

    def test_message_d_echec_propre_au_jeu_garde(self):
        mo, textes, pm0, pm1 = self.sort_sur(self.EVAC, {self.RAGNAR: 47}, groupe=True)                       # Evac' a Strattbourg : le jeu a son propre message (« Mais il ne se passe rien. »)
        self.assertEqual(textes, ["Doc lance le sort Évac' !", 'Mais il ne se passe rien.']); self.assertEqual((pm0, pm1), (30, 30))

    def test_sorts_a_zero_pm_non_concernes(self):
        for sort, dernier in ((self.MAPPILLE, "Mais il n'a pas une bonne visibilité."), (self.SIFFLET, 'Mais rien ne se passe.')):
            mo, textes, pm0, pm1 = self.sort_sur(sort, {self.RAGNAR: 47}, groupe=True)
            self.assertEqual(textes[-1], dernier, textes); self.assertEqual((pm0, pm1), (30, 30)); self.assertEqual(len(textes), 2, textes)

    def test_antipoison_sans_poison(self):
        mo = self.pret(sort=self.ANTIPOISON); textes = self.lancer(mo)
        self.assertEqual(textes[-1], 'Mais rien ne se passe.'); self.assertEqual(_stat(mo, self.DOC)[2], 30)

    def test_antipoison_sur_empoisonne(self):
        mo = self.pret(sort=self.ANTIPOISON, poison=True); textes = self.lancer(mo)
        self.assertEqual(textes[-1], "Ragnar n'est plus empoisonné !"); self.assertEqual(_stat(mo, self.DOC)[2], 28)

    def test_rappel_sur_un_mort(self):
        mo = self.pret(sort=self.RAPPEL, pv={self.RAGNAR: 0}); textes = self.lancer(mo)
        self.assertEqual(textes[-1], 'Ragnar revient à la vie !'); self.assertGreater(_stat(mo, self.RAGNAR)[0], 0); self.assertEqual(_stat(mo, self.DOC)[2], 22)


if __name__ == '__main__':
    unittest.main()
