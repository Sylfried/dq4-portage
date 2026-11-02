"""Menu Magie du terrain (Make_NameButton, Make_MagicInfo, Make_TargetCharaList) et usages sans effet : le moteur d'origine decide.

    python3 outils/test_magie_liste.py                                          (partie interface : Linux sans ecran, pyglet en mode « headless »)
    DQ_APK=<dossier des APK patches> DQ_SAVES=<dossier des sauvegardes> python3 outils/test_magie_liste.py      (ajoute les scenarios du moteur reel)

Partie interface (sans moteur) : la liste de boutons nommes (type 8) recoit du moteur son code 6 = preset de mise en page (`MenuPortItemTable.name_button_param`). Sans lui, la 5e rangee restait
visible et cliquable : un toucher y envoyait au moteur un sort inexistant (<ERR 0x07000000.0> a l'ecran, « Cout en PM  0/ 30 »).
  1. preset 0 (4 rangees : liste des sorts) : seules les rangees dont le code n'est pas 0 sont des zones tactiles ; les rangees 4 et 5 n'existent pas ;
  2. preset 1 (5 rangees : menu Utiliser / Transferer / Abandonner) ; presets 2 a 4 : ordonnee de la premiere rangee, rangees suivantes a 67 au-dessous ;
  3. le code 6 rejoue (ou arrive apres les codes de rangee) ne decale pas deux fois ; un preset inconnu est ignore ; revenir au preset 0 remet les rangees en place ;
  4. la ligne de cout « Cout en PM:<tab>  2 » (TextMesh.tabSize 8) : la tabulation devient 8 espaces dans la liste des magies seulement (un texte sans tabulation ou sans tabSize ne change pas).

Partie moteur (DQ_APK et DQ_SAVES : les sauvegardes sont ouvertes en lecture seule, le moteur ecrit dans un dossier temporaire ; groupe de l'emplacement 1 : Ragnar sans PM et Doc, 30 PM, qui sait « Premiers secours ») :
  5. liste de Doc : une seule rangee, « Premiers secours », code de rangee 2, rangees 1 a 3 cachees ;
  6. Premiers secours sur Ragnar blesse : PM 30 -> 28, PV 20 -> 47 ; sur Ragnar aux PV pleins : les messages de soin mais AUCUN PM depense (BaseAction::useMp ne depense que si l'action a eu un effet) ;
  7. usages sans effet decides par le moteur : Rappel sur un vivant, Antipoison sans poison : « Mais rien ne se passe. », aucun PM depense ; PM insuffisants : « Pas assez de PM ! » ;
  8. Rappel sur un mort : « revient a la vie », PM depenses ; Antipoison sur un empoisonne : « n'est plus empoisonne »."""
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


def _stat(mo, i):
    return struct.unpack_from('<4H', mo.core.mem(mo.core.export('_ZN6status9PartyData15originalPlayer_E') + 0x530 * i + 0x58, 0x30), 0x22)          # PV, PV max, PM, PM max


@unittest.skipUnless(APK and SAVES, 'moteur reel : DQ_APK=<dossier des APK patches> DQ_SAVES=<dossier des sauvegardes>')
class MoteurReel(unittest.TestCase):
    RAGNAR, DOC = 3, 12                                                   # emplacements de PlayerStatus dans originalPlayer_ (groupe de l'emplacement 1)
    PREMIERS_SECOURS, RAPPEL, ANTIPOISON = 196, 200, 202                   # identifiants d'action des sorts du terrain
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
        textes = []
        for k in range(500):
            self.avance(mo, 1)
            for t in (x['texte'] for x in mo.capteur.vider()):
                if not textes or textes[-1] != t: textes.append(t)
            if mo.msg_visible and k % 30 == 29: self.avance(mo, 1, self.BTN_PAROLE)
            if not mo.msg_visible and k > 60: break
        return [t.replace('\xa0', ' ').replace(';', '').strip() for t in textes]

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
        self.assertTrue(any('lance le sort' in t for t in textes), textes)

    def test_pm_insuffisants(self):
        mo = self.pret(pv={self.RAGNAR: 20}, pm=1); textes = self.lancer(mo)
        self.assertEqual(textes, ['Pas assez de PM !'])
        self.assertEqual(_stat(mo, self.DOC)[2], 1); self.assertEqual(_stat(mo, self.RAGNAR)[0], 20)

    def test_rappel_sur_un_vivant(self):
        mo = self.pret(sort=self.RAPPEL, pv={self.RAGNAR: 47}); textes = self.lancer(mo)
        self.assertEqual(textes[-1], 'Mais rien ne se passe.'); self.assertEqual(_stat(mo, self.DOC)[2], 30)

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
