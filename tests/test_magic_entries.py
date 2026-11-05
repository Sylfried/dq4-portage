"""Menu Magie du terrain (Make_NameButton, Make_MagicInfo, Make_TargetCharaList) et usages sans effet : le moteur d'origine decide.

    python3 tools/test_magic_entries.py                                          (partie interface : Linux sans ecran, pyglet en mode « headless »)
    DQ_APK=<dossier des APK patches> DQ_SAVES=<dossier des sauvegardes> python3 tools/test_magic_entries.py      (ajoute les scenarios du moteur reel)

Partie interface (sans moteur) : la liste de boutons nommes (type 8) recoit du moteur son code 6 = preset de mise en page (`MenuPortItemTable.name_button_param`). Sans lui, la 5e rangee restait
visible et cliquable : un toucher y envoyait au moteur un sort inexistant (<ERR 0x07000000.0> a l'ecran, « Cout en PM  0/ 30 »).
  1. preset 0 (4 rangees : liste des sorts) : seules les rangees dont le code n'est pas 0 sont des zones tactiles ; les rangees 4 et 5 n'existent pas ;
  2. preset 1 (5 rangees : menu Utiliser / Transferer / Abandonner) ; presets 2 a 4 : ordonnee de la premiere rangee, rangees suivantes a 67 au-dessous ;
  3. le code 6 rejoue (ou arrive apres les codes de rangee) ne decale pas deux fois ; un preset inconnu est ignore ; revenir au preset 0 remet les rangees en place ;
  4. la ligne de cout « Cout en PM:<tab>  2 » (TextMesh.tabSize 8) : la tabulation devient 8 espaces dans la liste des magies seulement (un texte sans tabulation ou sans tabSize ne change pas).

  4 bis. la ligne de cout de la fiche d'un sort (type 7, texte 2) porte la limite droite de son cadre (Render._texte la comprime pour qu'elle y tienne) ; les autres textes de la fiche ne le sont pas.

Partie moteur (DQ_APK et DQ_SAVES : les sauvegardes sont ouvertes en lecture seule, le moteur ecrit dans un dossier temporaire ; groupe de l'emplacement 1 : Ragnar sans PM et Doc, 30 PM, qui sait « Premiers secours ») :
  5. liste de Doc : une seule rangee, « Premiers secours », code de rangee 2, rangees 1 a 3 cachees ;
  6. Premiers secours sur Ragnar blesse : PM 30 -> 28, PV 20 -> 47 ; sur Ragnar aux PV pleins : AUCUN PM depense (BaseAction::useMp ne depense que si l'action a eu un effet) et, hors combat, « Mais il ne se passe rien. » (message officiel d'Evac', id 0xc3d6d) a la place du message de succes
     des soins (crochet Engine._magic_hooks ; ATTENDU CHANGE VOLONTAIREMENT : avant, le moteur affichait « Les blessures de Ragnar guerissent ! » sans depenser de PM) ;
  7. usages sans effet decides par le moteur : Rappel sur un vivant, Antipoison sans poison : « Mais rien ne se passe. », aucun PM depense ; PM insuffisants : « Pas assez de PM ! » ;
  8. Rappel sur un mort : « revient a la vie », PM depenses ; Antipoison sur un empoisonne : « n'est plus empoisonne » ;
  9. regle « sort qui coute des PM et n'en depense aucun » : soins a PV pleins (Premiers secours, Soins partiels, Soins complets), soin de groupe (Multisoin : un seul message, pas de bruitage de soin en attente) ;
     non-regressions : sort a effet (PM depenses, message du jeu), Multisoin avec un blesse (messages de soin gardes), messages d'echec propres au jeu (Evac' hors donjon), sorts a 0 PM (Mappille, Sifflet).
 10. bruitages (SoundManager::playSe, #137) : le bruitage de lancement (306, le meme pour tous les sorts) est joue dans tous les cas ; le bruitage de soin (501) n'est PAS joue quand le sort n'a eu aucun effet (Premiers secours, Soins partiels,
     Soins complets sur PV pleins ; Multisoin en pleine forme) et reste joue quand le sort sert (deux fois pour un soin sur une cible, une fois par cible pour Multisoin) ; un soin utile apres un soin inutile joue de nouveau son bruitage."""
import os, struct, sys, tempfile, types, unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import pyglet
if sys.platform.startswith('linux') and not os.environ.get('DISPLAY'): pyglet.options['headless'] = True; pyglet.options['shadow_window'] = False
from dq4_pc.menus import ui_menu as UM

APK, SAVES = os.environ.get('DQ_APK'), os.environ.get('DQ_SAVES')


def list_type():
    """Make_NameButton minimal : la racine puis 6 rangees (parts[1 + k], bouton k, ordonnee 382 - 67 k) avec un texte fils chacune."""
    square = {'vtx': [[-100.0, 10.0], [100.0, 10.0], [100.0, -10.0], [-100.0, -10.0]], 'uv': [[0, 0], [1, 0], [1, 1], [0, 1]], 'sub': {'0': [0, 1, 2, 0, 2, 3]}}
    nodes = [{'id': 1, 'par': None, 'pos': [0.0, 0.0, 0.0], 'act': True, 'mats': []}]; parts = [{'node': 1, 'ib': []}]
    for k in range(6):
        z = 382.0 - 67.0 * k
        nodes.append({'id': 100 + k, 'par': 1, 'pos': [0.0, 4.0, z], 'act': True, 'mats': [{'sheet': 1, 'part': 7, 'color': [1, 1, 1, 1], 'shader': 'parts', 'offset': None}], 'mesh': square, 'parts': {'buttonId': k, 'gamepad': 16}})
        nodes.append({'id': 200 + k, 'par': 100 + k, 'pos': [0.0, 8.0, z - 5.0], 'act': True, 'text': {'font': 'font', 'characterSize': 10.0, 'text': None}, 'mats': []})
        parts.append({'node': 100 + k, 'ib': [{'k': 'button'}, {'k': 'text', 'go': 200 + k, 'variant': 0}]})
    nodes.append({'id': 300, 'par': 100, 'pos': [20.0, 12.0, 340.0], 'act': True, 'text': {'font': 'font', 'characterSize': 6.63, 'text': None, 'anchor': 3, 'alignment': 0, 'lineSpacing': 0.84, 'tabSize': 8.0}, 'mats': []})      # ligne de cout de la rangee 0
    nodes.append({'id': 301, 'par': 100, 'pos': [20.0, 12.0, 340.0], 'act': True, 'text': {'font': 'font', 'characterSize': 6.63, 'text': None, 'anchor': 3, 'alignment': 0, 'lineSpacing': 0.84}, 'mats': []})              # meme ancrage, sans tabSize
    return {'name': 'Make_NameButton()', 'err': None, 'nodes': nodes, 'parts': parts,
            'params': [{'id': k, 'no': 0, 'parts': 1 + k, 'base': 0} for k in range(6)], 'builds': [],
            'codes': [{'id': k, 'kind': 'func', 'method': 'Sub_NameButton', 'fx': {'-1': {'err': None, 'd': {}}, '0': {'err': None, 'd': {str(100 + k): {'act': False}}}, '1': {'err': None, 'd': {}}, '2': {'err': None, 'd': {}}}} for k in range(5)]}


def window():
    ml = types.SimpleNamespace(types={'8': list_type()}, info=[], borders=[], hdr={'lang': {'hiro': 1.0}}, pushed=(0.0, 0.0))
    return UM.Window(ml, 8)


def zones(wnd): return sorted(b[0] for b in wnd.buttons())
def z_row(wnd, k): return wnd.N[100 + k]['pos'][2]


class TestNameEntries(unittest.TestCase):
    def test_exported_presets(self):
        """Les 5 presets du moteur (NAME_BUTTON_Y / NAME_BUTTON_DY) : nombre de rangees, ordonnee de la premiere, pas."""
        self.assertEqual(UM.NAMES_PRESETS[0], (4, 382.0, 67.0)); self.assertEqual(UM.NAMES_PRESETS[1], (5, 382.0, 67.0)); self.assertEqual(len(UM.NAMES_PRESETS), 5)
        self.assertEqual((UM.NAMES_START, UM.NAMES_STEP), (382.0, 67.0))

    def test_spell_entries_one_row(self):
        """Doc sait un sort : codes 0 = 2 (deux lignes), 1 a 3 = 0, code 6 = 0. Seule la rangee 0 est une zone tactile (la 5e, fantome, menait a <ERR 0x07000000.0>)."""
        wnd = window()
        self.assertEqual(zones(wnd), [0, 1, 2, 3, 4, 5], 'avant le code 6 : tout est visible (etat exporte)')
        for i, v in ((0, 2), (1, 0), (2, 0), (3, 0), (6, 0)): wnd.code(i, v)
        self.assertEqual(zones(wnd), [0])
        for k in range(1, 6): self.assertFalse(wnd.N[100 + k]['act'], k)

    def test_spell_entries_four_rows(self):
        wnd = window()
        wnd.code(6, 0)
        for i in range(4): wnd.code(i, 2)
        self.assertEqual(zones(wnd), [0, 1, 2, 3])                          # 4 rangees au plus : ni la 5e ni la 6e
        wnd.code(2, 0)
        self.assertEqual(zones(wnd), [0, 1, 3])

    def test_code_6_before_or_after_row_codes(self):
        wnd = window()
        for i, v in ((0, 1), (1, 0), (2, 0), (3, 0), (4, 0)): wnd.code(i, v)           # rejeu d'une fenetre : les codes de rangee d'abord
        wnd.code(6, 1)
        self.assertEqual(zones(wnd), [0])
        fe2 = window(); fe2.code(6, 1)
        for i, v in ((0, 1), (1, 1), (2, 1), (3, 0), (4, 0)): fe2.code(i, v)
        self.assertEqual(zones(fe2), [0, 1, 2])                            # menu Utiliser / Transferer / Abandonner : preset 1, trois rangees

    def test_preset_positions(self):
        wnd = window()
        base = [z_row(wnd, k) for k in range(6)]
        for preset, (num, initial, step) in enumerate(UM.NAMES_PRESETS):
            wnd.code(6, preset)
            for k in range(6):
                self.assertAlmostEqual(z_row(wnd, k), base[k] + (initial - step * k) - (382.0 - 67.0 * k), msg=(preset, k))
                self.assertAlmostEqual(wnd.N[200 + k]['pos'][2], base[k] - 5.0 + (initial - step * k) - (382.0 - 67.0 * k), msg=('texte', preset, k))      # le texte suit sa plaque
        wnd.code(6, 0)
        self.assertEqual([z_row(wnd, k) for k in range(6)], base)        # retour au preset 0 : tout est remis en place

    def test_no_double_offset(self):
        wnd = window(); wnd.code(6, 2); a = [z_row(wnd, k) for k in range(6)]
        wnd.code(6, 2); wnd.code(6, 2)
        self.assertEqual([z_row(wnd, k) for k in range(6)], a)

    def test_unknown_preset_ignored(self):
        wnd = window(); before = [(z_row(wnd, k), wnd.N[100 + k]['act']) for k in range(6)]
        for c in (-1, 5, 99, None, 'x', 1.5): wnd.code(6, c)
        self.assertEqual([(z_row(wnd, k), wnd.N[100 + k]['act']) for k in range(6)], before)


class TestCostLine(unittest.TestCase):
    """« Cout en PM:<tab>  2 » : TextMesh.tabSize (8) fait de la tabulation 8 espaces ; la police du jeu n'a pas de glyphe pour la tabulation (largeur nulle) et le nombre collait a l'etiquette au lieu d'etre dans la colonne de droite."""
    def test_cost_line_tab(self):
        wnd = window()
        wnd.params[(0, 1)] = {'id': 0, 'no': 1, 'parts': 1, 'base': 2}
        wnd.parts[1]['ib'].append({'k': 'text', 'go': 300, 'variant': 0})
        self.assertEqual(wnd.N[300]['text'].get('tabSize'), 8.0)
        wnd.param_str(0, 1, 'Coût en PM:\t  2')
        self.assertEqual(wnd.N[300]['text']['text'], 'Coût en PM:' + ' ' * 8 + '  2')
        wnd.param_str(0, 1, 'Coût en PM:\t 10')
        self.assertEqual(wnd.N[300]['text']['text'], 'Coût en PM:' + ' ' * 8 + ' 10')           # le champ du nombre garde sa largeur : la colonne reste alignee

    def test_text_without_tab_unchanged(self):
        wnd = window()
        wnd.params[(0, 1)] = {'id': 0, 'no': 1, 'parts': 1, 'base': 2}
        wnd.parts[1]['ib'].append({'k': 'text', 'go': 300, 'variant': 0})
        wnd.param_str(0, 1, 'Premiers secours'); self.assertEqual(wnd.N[300]['text']['text'], 'Premiers secours')

    def test_without_tabsize_the_tab_remains(self):
        wnd = window()                                                     # le texte 301 n'a pas de tabSize : rien n'est remplace
        wnd.params[(0, 1)] = {'id': 0, 'no': 1, 'parts': 1, 'base': 2}
        wnd.parts[1]['ib'].append({'k': 'text', 'go': 301, 'variant': 0})
        wnd.param_str(0, 1, 'a\tb'); self.assertEqual(wnd.N[301]['text']['text'], 'a\tb')


class TestSpellCard(unittest.TestCase):
    """Fiche d'un sort (Make_MagicInfo, type 7) : « Cout en PM 10/ 30 » (FR) est plus long que « MP Cost 10/ 30 » et sortait de son cadre : la ligne de cout (texte 2) porte la limite droite de son cadre (fit_x) : Render._texte la comprime pour qu'elle y tienne
    meme avec la police d'origine ; le nom, la description et « Lancer » gardent leur mise en page."""
    def window(self):
        def text(nid, anchor): return {'id': nid, 'par': 1, 'pos': [75.0, 12.0, 103.0], 'act': True, 'text': {'font': 'font', 'characterSize': 9.945, 'text': None, 'anchor': anchor, 'alignment': 0, 'lineSpacing': 0.88}, 'mats': []}
        t = {'name': 'Make_MagicInfo()', 'err': None, 'nodes': [{'id': 1, 'par': None, 'pos': [0.0, 0.0, 0.0], 'act': True, 'mats': []}] + [text(10 + k, 0) for k in range(4)],
             'parts': [{'node': 1, 'ib': [{'k': 'text', 'go': 10 + k, 'variant': 0} for k in range(4)]}], 'params': [{'id': 0, 'no': k, 'parts': 0, 'base': k} for k in range(4)], 'codes': [], 'builds': []}
        return UM.Window(types.SimpleNamespace(types={'7': t}, info=[], borders=[], hdr={'lang': {'hiro': 1.0}}, pushed=(0.0, 0.0)), 7)

    def test_only_the_cost_line_is_marked(self):
        wnd = self.window()
        for no, s in enumerate(('Premiers secours', "Restaure au moins 30\r\nPV d'un seul allié.", 'Coût en PM  2/ 30', 'Lancer')): wnd.param_str(0, no, s)
        self.assertEqual([wnd.N[10 + k].get('fit_x') for k in range(4)], [None, None, UM.CARD_COST_X_MAX, None])
        self.assertEqual(wnd.N[12]['text']['text'], 'Coût en PM  2/ 30')           # le texte lui-meme n'est pas modifie

    def test_description_carries_its_border_width(self):
        wnd = self.window()
        for no, s in enumerate(('Premiers secours', "Restaure au moins 30\r\nPV d'un seul allié.", 'Coût en PM  2/ 30', 'Lancer')): wnd.param_str(0, no, s)
        self.assertEqual([(wnd.N[10 + k].get('wrap_x'), wnd.N[10 + k].get('wrap_n')) for k in range(4)], [(None, None), (UM.CARD_DESC_X_MAX, 2), (None, None), (None, None)])
        self.assertEqual(wnd.N[11]['text']['text'], "Restaure au moins 30\r\nPV d'un seul allié.")           # le texte du moteur n'est pas modifie (c'est le rendu qui recoupe)


class TestRewrapDescription(unittest.TestCase):
    """Render._adjust_description : la description francaise d'un sort a 3 ou 4 lignes (cadre de 2) est recoupee a la largeur du cadre (police fictive : 9 unites par caractere, cadre de 361 unites = 40 caracteres)."""
    LAYOUT = 148.0 + 213.0
    def rewrap(self, text):
        r = object.__new__(UM.Render)
        r.texts = types.SimpleNamespace(bitmap=types.SimpleNamespace(width_px=lambda x: 9.0 * len(x)))
        return r._adjust_description({}, text.split('\n'), self.LAYOUT, 2, r.texts.bitmap, 1.0, 1.0, 1.0, 9.0)

    def test_four_lines_into_two(self):
        for t in ("Permet de sortir\r\nimmédiatement des\r\ndonjons, grottes et\r\ntours.", "Génère une aura\r\nsacrée qui éloigne les\r\nmonstres les plus\r\nfaibles."):
            out, f = self.rewrap(t)
            self.assertEqual((len(out), f), (2, 1.0), out)
            self.assertEqual(' '.join(out), ' '.join(l.strip() for l in t.split('\n')))          # aucun mot perdu ni ajoute
            self.assertTrue(all(9.0 * len(l) <= self.LAYOUT for l in out), out)

    def test_three_lines_in_two(self):
        out, f = self.rewrap("Ressuscite un allié\r\nmort en lui octroyant\r\nla moitié de ses PV.")
        self.assertEqual((len(out), f), (2, 1.0), out)

    def test_three_too_long_lines_compressed(self):
        t = "\r\n".join(" ".join([c * 4] * 6) for c in "abc")                                         # 3 lignes de 29 caracteres : recoupees a 40 elles feraient encore 3 lignes : le texte est comprime pour tenir en 2
        out, f = self.rewrap(t)
        self.assertEqual(len(out), 2, out); self.assertTrue(UM.COMPRESSION_MIN <= f < 1.0, f)
        self.assertTrue(all(9.0 * len(l) * f <= self.LAYOUT + 0.5 for l in out), (out, f))


def _stat(eng, i):
    return struct.unpack_from('<4H', eng.core.mem(eng.core.export('_ZN6status9PartyData15originalPlayer_E') + 0x530 * i + 0x58, 0x30), 0x22)          # PV, PV max, PM, PM max


@unittest.skipUnless(APK and SAVES, 'moteur reel : DQ_APK=<dossier des APK patches> DQ_SAVES=<dossier des sauvegardes>')
class RealEngine(unittest.TestCase):
    RAGNAR, DOC = 3, 12                                                   # emplacements de PlayerStatus dans originalPlayer_ (groupe de l'emplacement 1)
    FIRST_AID, REVIVE, ANTIDOTE = 196, 200, 202                   # identifiants d'action des sorts du terrain
    MULTIHEAL, EVAC, SAFE_PASSAGE, MAPPILLE, WHISTLE = 199, 204, 206, 209, 216          # (Multisoin : 10 PM, sans cible ; Evac' : 1 PM ; Passage sur : 2 PM ; Mappille et Sifflet : 0 PM)
    BTN_MENU, BTN_TALK = 0x800, 0x100

    def advance(self, eng, n, decl=0):
        for i in range(n): eng.step(0, decl if i == 0 else 0)

    def ready(self, sort=None, hit_points=None, mp=30, poison=False):
        from dq4_pc.core import engine as ENGINE
        eng = ENGINE.Engine(APK, SAVES, tempfile.mkdtemp(prefix='sv_magie_')); eng.load_save(1); self.advance(eng, 120)
        for _ in range(30):                                                # le dialogue d'ouverture doit etre ferme et le joueur libre
            self.advance(eng, 1, self.BTN_TALK); self.advance(eng, 20)
            if not eng.msg_visible and not (eng.flags() & 4): break
        self.advance(eng, 30); c = eng.core
        orig = c.export('_ZN6status9PartyData15originalPlayer_E'); hs = lambda i: orig + 0x530 * i + 0x58
        if sort is not None:
            ha = orig + 0x530 * self.DOC + 0xd0
            c.call(c.export('_ZN6status10HaveAction5clearEv'), ha); c.call(c.export('_ZN6status10HaveAction3addEii'), ha, sort, 0)
        c.mem_w(hs(self.DOC) + 0x26, struct.pack('<H', mp))
        for i, v in (hit_points or {}).items(): c.mem_w(hs(i) + 0x22, struct.pack('<H', v))
        if poison: c.call(c.export('_ZN6status14HaveStatusInfo9setPoisonEv'), hs(self.RAGNAR) - 0x48)          # HaveStatusInfo = HaveStatus - 0x48
        eng.sensor.drain()
        return eng

    def open_list(self, eng):
        self.advance(eng, 1, self.BTN_MENU); self.advance(eng, 20)
        eng.send_menu(4, 1, 1, 0x10); self.advance(eng, 20)               # menu racine : « Magie »
        eng.send_menu(5, 1, 3, 0x10); self.advance(eng, 25)               # liste des personnages : Doc

    def launch(self, eng, target=0):
        self.open_list(eng)
        eng.send_menu(8, 1, 0, 0x10); self.advance(eng, 20)               # le sort de la rangee 0
        eng.send_menu(6, 1, target, 0x10); self.advance(eng, 3)            # la cible
        return self.messages(eng)

    def launch_group(self, eng):
        """Sort de groupe ou sans cible : la fiche du sort (port 8, bouton « Lancer » = rangee 2), pas de choix de cible."""
        self.open_list(eng)
        eng.send_menu(8, 1, 0, 0x10); self.advance(eng, 20)
        self.assertEqual(eng.ui.f[8]['cases'].get((2, 0)), 'Lancer')
        eng.send_menu(8, 1, 2, 0x10); self.advance(eng, 3)
        return self.messages(eng)

    def messages(self, eng):
        texts = []
        for k in range(500):
            self.advance(eng, 1)
            for t in (x['texte'] for x in eng.sensor.drain()):
                if not texts or texts[-1] != t: texts.append(t)
            if eng.msg_visible and k % 30 == 29: self.advance(eng, 1, self.BTN_TALK)
            if not eng.msg_visible and k > 60: break
        return [t.replace('\xa0', ' ').replace(';', '').strip() for t in texts]

    LAUNCH, HEAL_SFX = 306, 501                                              # SoundManager::playSe : bruitage de lancement (tous les sorts) ; bruitage de soin

    def sounds(self, eng):
        """Liste (remplie au fil de l'eau) des bruitages `SoundManager::playSe` joues par le moteur a partir de maintenant ; le bruitage 300 (validation d'une touche dans les messages) est ecarte."""
        import unicorn
        c = eng.core; entries = []; a = c.export('_ZN12SoundManager6playSeEi')
        c.uc.hook_add(unicorn.UC_HOOK_CODE, lambda uc, ad, sz, u: entries.append(uc.reg_read(c.XREG[0]) & 0xffffffff), None, a, a); c.uc.ctl_flush_tb()
        return entries

    def sound_effects(self, sort, hit_points, group=False):
        eng = self.ready(sort=sort, hit_points=hit_points); sounds = self.sounds(eng)
        texts = self.launch_group(eng) if group else self.launch(eng)
        return texts, [x for x in sounds if x != 300]

    def test_heal_sfx_without_effect(self):
        for sort in (self.FIRST_AID, self.FIRST_AID + 1, self.FIRST_AID + 2):
            texts, sounds = self.sound_effects(sort, {self.RAGNAR: 47})
            self.assertEqual(texts[-1], 'Mais il ne se passe rien.'); self.assertEqual(sounds, [self.LAUNCH], 'sort %d : le lancement reste, le bruitage de soin est coupe' % sort)

    def test_useful_heal_sfx_kept(self):
        for sort in (self.FIRST_AID, self.FIRST_AID + 1, self.FIRST_AID + 2):
            texts, sounds = self.sound_effects(sort, {self.RAGNAR: 20})
            self.assertIn('Les blessures de Ragnar guérissent !', texts); self.assertEqual(sounds, [self.LAUNCH, self.HEAL_SFX, self.HEAL_SFX], 'sort %d' % sort)

    def test_group_heal_sfx(self):
        texts, sounds = self.sound_effects(self.MULTIHEAL, {self.RAGNAR: 47, self.DOC: 35}, group=True)
        self.assertEqual(texts[-1], 'Mais il ne se passe rien.'); self.assertEqual(sounds, [self.LAUNCH])
        texts, sounds = self.sound_effects(self.MULTIHEAL, {self.RAGNAR: 20, self.DOC: 35}, group=True)
        self.assertEqual(sounds, [self.LAUNCH, self.HEAL_SFX, self.HEAL_SFX], 'un bruitage de soin par cible soignee')

    def test_heal_sfx_returns_after_failure(self):
        eng = self.ready(hit_points={self.RAGNAR: 47}); sounds = self.sounds(eng)
        self.launch(eng); self.assertEqual([x for x in sounds if x != 300], [self.LAUNCH])
        c = eng.core; orig = c.export('_ZN6status9PartyData15originalPlayer_E'); c.mem_w(orig + 0x530 * self.RAGNAR + 0x58 + 0x22, struct.pack('<H', 20))
        self.advance(eng, 60); del sounds[:]
        texts = self.launch(eng)
        self.assertIn('Les blessures de Ragnar guérissent !', texts); self.assertEqual([x for x in sounds if x != 300], [self.LAUNCH, self.HEAL_SFX, self.HEAL_SFX])

    def test_doc_entries(self):
        eng = self.ready(); self.open_list(eng)
        f = eng.ui.f[8]
        self.assertEqual(f['type'], 8)
        self.assertEqual(f['cases'][(0, 0)], 'Premiers secours'); self.assertTrue(f['cases'][(0, 1)].startswith('Coût en PM'))
        self.assertEqual([f['indic'].get(i) for i in (0, 1, 2, 3, 6)], [2, 0, 0, 0, 0])      # rangee 0 sur deux lignes, 1 a 3 cachees, preset 0

    def test_heal_on_wounded(self):
        eng = self.ready(hit_points={self.RAGNAR: 20}); texts = self.launch(eng)
        self.assertEqual(_stat(eng, self.RAGNAR)[0], 47); self.assertEqual(_stat(eng, self.DOC)[2], 28)
        self.assertIn('Les blessures de Ragnar guérissent !', texts)

    def test_heal_on_full_hp_spends_no_mp(self):
        eng = self.ready(hit_points={self.RAGNAR: 47}); texts = self.launch(eng)
        self.assertEqual(_stat(eng, self.DOC)[2], 30, 'le moteur ne depense pas de PM quand le soin n\'a servi a rien')
        self.assertEqual(_stat(eng, self.RAGNAR)[0], 47)
        self.assertEqual(texts, ['Doc lance le sort Premiers secours !', 'Mais il ne se passe rien.'])          # le message officiel d'Evac' (id 0xc3d6d), pas « Les blessures de Ragnar guérissent ! »

    def test_insufficient_mp(self):
        eng = self.ready(hit_points={self.RAGNAR: 20}, mp=1); texts = self.launch(eng)
        self.assertEqual(texts, ['Pas assez de PM !'])
        self.assertEqual(_stat(eng, self.DOC)[2], 1); self.assertEqual(_stat(eng, self.RAGNAR)[0], 20)

    def test_revive_spell_on_living(self):
        eng = self.ready(sort=self.REVIVE, hit_points={self.RAGNAR: 47}); texts = self.launch(eng)
        self.assertEqual(texts[-1], 'Mais rien ne se passe.'); self.assertEqual(_stat(eng, self.DOC)[2], 30)

    def spell_on(self, sort, hit_points, group=False, **kw):
        eng = self.ready(sort=sort, hit_points=hit_points, **kw); pm0 = _stat(eng, self.DOC)[2]
        texts = self.launch_group(eng) if group else self.launch(eng)
        return eng, texts, pm0, _stat(eng, self.DOC)[2]

    def test_heals_at_full_hp_all_powers(self):
        for sort, name_str in ((self.FIRST_AID + 1, 'Soins partiels'), (self.FIRST_AID + 2, 'Soins complets')):
            eng, texts, pm0, pm1 = self.spell_on(sort, {self.RAGNAR: 47})
            self.assertEqual(texts, ['Doc lance le sort %s !' % name_str, 'Mais il ne se passe rien.']); self.assertEqual((pm0, pm1), (30, 30), name_str)

    def test_group_heal_at_full_health(self):
        eng, texts, pm0, pm1 = self.spell_on(self.MULTIHEAL, {self.RAGNAR: 47, self.DOC: 35}, group=True)
        self.assertEqual(texts, ['Doc lance le sort Multisoin !', 'Mais il ne se passe rien.'], 'une seule fois, pas une fois par personnage'); self.assertEqual((pm0, pm1), (30, 30))
        self.assertEqual(eng.core.mem(eng.L + 0x257f84, 1)[0], 0, 'plus de bruitage de soin en attente (le moteur en joue un par cible restante)')

    def test_group_heal_with_wounded_member_keeps_messages_and_mp(self):
        eng, texts, pm0, pm1 = self.spell_on(self.MULTIHEAL, {self.RAGNAR: 20, self.DOC: 35}, group=True)
        self.assertEqual(texts, ['Doc lance le sort Multisoin !', 'Les blessures de Ragnar guérissent !', 'Les blessures de Doc guérissent !']); self.assertEqual((pm0, pm1), (30, 20))
        self.assertGreater(_stat(eng, self.RAGNAR)[0], 20)

    def test_spell_with_effect_but_no_result_message_spends_its_mp(self):
        eng, texts, pm0, pm1 = self.spell_on(self.SAFE_PASSAGE, {self.RAGNAR: 47}, group=True)
        self.assertEqual(texts, ['Doc lance le sort Passage sûr !']); self.assertEqual((pm0, pm1), (30, 28))

    def test_game_own_failure_message_kept(self):
        eng, texts, pm0, pm1 = self.spell_on(self.EVAC, {self.RAGNAR: 47}, group=True)                       # Evac' a Strattbourg : le jeu a son propre message (« Mais il ne se passe rien. »)
        self.assertEqual(texts, ["Doc lance le sort Évac' !", 'Mais il ne se passe rien.']); self.assertEqual((pm0, pm1), (30, 30))

    def test_zero_mp_spells_not_concerned(self):
        for sort, last in ((self.MAPPILLE, "Mais il n'a pas une bonne visibilité."), (self.WHISTLE, 'Mais rien ne se passe.')):
            eng, texts, pm0, pm1 = self.spell_on(sort, {self.RAGNAR: 47}, group=True)
            self.assertEqual(texts[-1], last, texts); self.assertEqual((pm0, pm1), (30, 30)); self.assertEqual(len(texts), 2, texts)

    def test_antidote_without_poison(self):
        eng = self.ready(sort=self.ANTIDOTE); texts = self.launch(eng)
        self.assertEqual(texts[-1], 'Mais rien ne se passe.'); self.assertEqual(_stat(eng, self.DOC)[2], 30)

    def test_antidote_on_poisoned(self):
        eng = self.ready(sort=self.ANTIDOTE, poison=True); texts = self.launch(eng)
        self.assertEqual(texts[-1], "Ragnar n'est plus empoisonné !"); self.assertEqual(_stat(eng, self.DOC)[2], 28)

    def test_revive_spell_on_dead(self):
        eng = self.ready(sort=self.REVIVE, hit_points={self.RAGNAR: 0}); texts = self.launch(eng)
        self.assertEqual(texts[-1], 'Ragnar revient à la vie !'); self.assertGreater(_stat(eng, self.RAGNAR)[0], 0); self.assertEqual(_stat(eng, self.DOC)[2], 22)


if __name__ == '__main__':
    unittest.main()
