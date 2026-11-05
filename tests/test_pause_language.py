"""Langue de l'outil (D-238) : pages du menu Paramètres (Pause), en anglais et en français.

Le menu est piloté avec un faux « jeu » (voir test_pause_pages.py) et DESSINÉ pour de vrai dans une fenêtre pyglet cachée (EGL sans écran sous Linux) ; chaque étiquette demandée à la fenêtre (`_lbl`) est notée.
Le parcours couvre toutes les pages (racine, Affichage, Interface avec chacun de ses éléments, Son, Commandes, Modifications, États, Quitter), toutes les valeurs de toutes les listes, l'aide de chaque ligne, les consignes
de capture d'une touche et de saisie d'une valeur, l'infobulle de la barre de titre, la fenêtre de confirmation, les messages d'information (par leurs vrais appels), les noms de toutes les touches du clavier.

    python3 tests/test_pause_language.py

Règles : (1) en anglais, aucun texte dessiné n'est du français ; (2) tout texte français dessiné a sa traduction (liste blanche : les mots identiques dans les deux langues) et l'anglais dessiné est bien celle du catalogue ;
(3) en français, les textes sont exactement ceux d'avant (le catalogue vidé donne, en mode anglais, les mêmes textes que le français : la traduction est la seule différence) ; (4) les DONNÉES du menu (libellés, noms de valeurs,
noms de touches, messages) restent en français, elles sont traduites en les dessinant (les autres tests et les autres écrans, comme l'historique, s'y fient) ; (5) pas de clé inutile ni de traduction vide ou identique dans
texts_en\\pause.py ; (6) mutations de contrôle : une clé retirée, un `tr` retiré de plusieurs endroits, une traduction vidée ou laissée en français font échouer la vérification."""
import contextlib, inspect, io, os, re, sys, tempfile, textwrap, time, types, unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import _paths
import pyglet
if sys.platform.startswith('linux') and not os.environ.get('DISPLAY'): pyglet.options['headless'] = True; pyglet.options['shadow_window'] = False
import test_pause_pages as TP
import test_language as TL
from dq4_pc import language as LG
from dq4_pc.persistence import settings as RG
from dq4_pc.menus import pause as PA
from dq4_pc.texts_en import pause as EN_PAUSE

K = pyglet.window.key
PAGES = ('racine', 'affichage', 'son', 'commandes', 'modifications', 'etats', 'quitter', 'interface')
# Mots identiques en français et en anglais, ou noms techniques : dessinés tels quels dans les deux langues, sans entrée dans le catalogue (une entrée identique ferait un doublon avec les autres fichiers).
NEUTRES = {'Interface', 'Modifications', 'Casino', 'Menu', 'Normal', 'Action', 'Tab', 'Shader', 'Antialiasing', 'EPX x8', 'Pixel perfect', 'x2', 'x4', 'x8',
           'FenetreInconnue'}          # (le faux nom que le faux jeu donne à une fenêtre que l'outil ne connaît pas)
_win = []
CONSOLE = {'police du jeu non chargee :', 'Reglages illisibles (%s) : valeurs par defaut (%r)', 'Reglages non enregistres :'}          # messages de la console (testés dans la classe Console)


def window():
    """Fenêtre pyglet cachée (le dessin du menu a besoin d'un contexte GL) ; SkipTest si la machine ne peut pas en ouvrir une."""
    if not _win:
        try: _win.append(pyglet.window.Window(width=1280, height=720, visible=False))
        except Exception as ex: raise unittest.SkipTest('pas de fenetre pyglet possible : %r' % (ex,))
    return _win[0]


def png(color=(40, 90, 160)):
    from PIL import Image
    b = io.BytesIO(); Image.new('RGB', (64, 36), color).save(b, 'PNG'); return b.getvalue()


class FakeHud:
    taken = None
    def draw_all(self, *a): pass
    def rect(self, n): return (60.0 + 40 * len(n), 120.0, 90.0, 70.0)
    def take(self, *a): pass
    def move_to(self, *a): pass


class FakeGame(TP.FakeGame):
    """Le faux jeu des pages avec ce que `draw_all()` lui demande. `seen` : les textes demandés à `_lbl`, notés avec le moment du parcours (`moment`)."""
    is_fullscreen = False; mode = 4; res = (1280, 720); helptext = False
    NAMES = {n: [1] for n in PA.WINDOW_NAMES if n not in PA.OWN_INTERFACES}

    def __init__(self, savestates=True):
        super().__init__(); self.post = types.SimpleNamespace(max_msaa=None); self.hud = FakeHud(); self.seen = []; self.moment = 'page'; self.cache_label = {}; self.failure = None
        self.savestates = {1: ({'date': '2026-10-31 19:21:05', 'lieu': 'Carte du monde'}, png()), 2: ({'date': '2026-11-02 08:05:59', 'lieu': 'Combat'}, png((160, 60, 40))),
                      3: ({'lieu': 'mak1f1'}, None), 5: ({'date': '2026-11-03 23:59:00', 'lieu': 'Combat'}, None)} if savestates else {}
        self.sound = types.SimpleNamespace(active=True, listening=False, listen=lambda b: None, tick=lambda: None)
    def set_full_screen(self, v): self.is_fullscreen = v
    def resolutions(self): return [(1280, 720), (1920, 1080)]
    def current_resolution(self): return self.res
    def set_resolution(self, v): self.res = v
    def set_mode(self, v): self.mode = v
    def window_names(self): return dict(self.NAMES, FenetreInconnue=[1])          # (+ une fenêtre inconnue de l'outil : groupe « Autres »)
    def state_info(self, n): return self.savestates.get(n)
    def state_path(self, n): return os.path.join(tempfile.gettempdir(), 'dq4_test_langue_etat_inexistant_%d' % n)
    def save_state(self, n, thumbnail=b''):
        if self.failure: raise OSError(self.failure)
    def load_state(self, n):
        if self.failure: raise OSError(self.failure)
    def _png_thumbnail(self, t): return b''
    def preview_interface(self, target): return (300.0, 200.0, 700.0, 420.0)
    def new_sample(self): pass
    def set_info(self, v): self.helptext = v
    def quit_game(self): pass
    def back_to_title(self): pass
    def _lbl(self, text, size_value, color=(255, 255, 255, 255), fonts=()):
        self.seen.append((self.moment, text)); window()
        k = (text, round(size_value, 1), color)
        if k not in self.cache_label: self.cache_label[k] = pyglet.text.Label(text, font_size=size_value, color=color, anchor_x='left', anchor_y='baseline')
        return self.cache_label[k]


class PauseSpy(PA.Pause):
    """Le menu qui note chaque appel de `_helptext_lines` : (texte brut reçu, lignes rendues)."""
    def __init__(self, game): super().__init__(game); self.helpers = []
    def _helptext_lines(self, text, maxw, fz):
        ls = super()._helptext_lines(text, maxw, fz); self.helpers.append((text, ls)); return ls


def menu(page, game=None, **attrs):
    J = game or FakeGame(); p = PauseSpy(J); p.opened = True; p.stack = [page]
    for k, v in attrs.items(): setattr(p, k, v)
    return J, p


def draw_page(p):
    window().switch_to(); window().clear(); p.draw_all()


class FrozenClock:
    """Le module `time` du menu, dont l'heure ne bouge plus (le curseur clignotant de la saisie, les animations : le dessin est le même d'un parcours à l'autre)."""
    def __getattr__(self, name_str): return getattr(time, name_str)
    @staticmethod
    def time(): return 1000.0


PAGE_METHODS = {'racine': 'root', 'affichage': 'display', 'son': 'sound', 'commandes': 'commands', 'modifications': 'changes', 'etats': 'savestates', 'quitter': 'quit', 'interface': 'interface'}      # identifiant de page (chaine) -> fin du nom de la methode `page_...` de Visite
PARTS = tuple('page_' + PAGE_METHODS[n] for n in PAGES) + ('messages', 'key_list')


class Visite:
    """Le parcours de l'interface du menu dans une langue : `seen` = [(moment, texte)] dessinés (moment : page, aide, infobulle, message) ; `helpers` = [(texte brut, lignes rendues)]. `parts` : les morceaux
    du parcours (par défaut tous : les pages, les messages d'information, les noms de touches)."""
    def __init__(self, language, parts=PARTS):
        self.language = language; self.seen = []; self.helpers = []; clock = PA.time
        LG.select_language(language); PA.time = FrozenClock(); self.catalog = LG.catalog()          # (le catalogue en vigueur pendant ce parcours)
        try:
            for name_str in parts: getattr(self, name_str)()
        finally: LG.select_language('fr'); PA.time = clock

    def note(self, J, p):
        self.seen.extend(J.seen); self.helpers.extend(p.helpers); J.seen.clear(); p.helpers.clear()

    def image(self, J, p, moment='page'):
        J.moment = moment; draw_page(p); J.moment = 'page'; self.note(J, p)

    def lines(self, J, p):
        """Les noms de toutes les valeurs des listes, et l'aide de chaque ligne (comme l'infobulle : phrases coupées à la largeur)."""
        for entry in p._entries():
            if entry['t'] == 'choix':
                for v in entry['vals']: p._label(p._value_name(entry['l'], v), 12.0)
        J.moment = 'aide'
        for entry in p._entries():
            text = p._line_helptext(entry)
            if text:
                for l in p._helptext_lines(text, 520.0, 12.0): p._label(l, 12.0)
        J.moment = 'page'; self.note(J, p)

    def page(self, name_str, J=None, **attrs):
        J, p = menu(name_str, J, **attrs); self.image(J, p)
        b = p.barre                                                                    # page qui defile : chaque ligne passe dans la fenetre
        if b:
            d, end = b['base'], b['base'] + b['n'] - b['vis']
            while d < end: d = min(d + b['vis'] - 1, end); p.begin[name_str] = d; self.image(J, p)          # (une page de lignes a la fois, avec une ligne de recouvrement)
        self.lines(J, p)
        return J, p

    def page_root(self): self.page('racine')
    def page_changes(self): self.page('modifications')
    def page_quit(self): self.page('quitter')

    def page_savestates(self):
        for action in ('creer', 'charger', 'supprimer'):
            J, p = self.page('etats', state_action=action)
            if action == 'creer':
                for i in range(1, 6): p.selected['etats'] = i; self.image(J, p)             # chaque sorte d'emplacement : miniature et date, date seule, rien, vide (« Pas de miniature », « Emplacement vide »)
        self.page('etats', FakeGame(savestates=False))
        for n in (1, 9):
            J, p = menu('etats'); p._request_deletion(n); self.image(J, p)          # fenetre de confirmation (n = 9 : emplacement vide, sans date)

    def page_display(self):
        self.page('affichage')
        J = FakeGame(); J.reg['msaa'] = 8; J.post.max_msaa = 4; J.is_fullscreen = True; self.page('affichage', J)          # « Limité à x4... » ; resolution grisee en plein ecran
        self.lists_and_inputs('affichage')

    def page_sound(self): self.page('son'); self.lists_and_inputs('son')

    def page_commands(self):
        self.page('commandes')
        for action in ('haut', 'accel', 'cam_gauche'):
            for col in (0, 1):
                J, p = menu('commandes'); p.capture = (action, col); self.image(J, p, 'infobulle')                       # « Appuie sur la touche pour... »
        self.lists_and_inputs('commandes')

    def lists_and_inputs(self, name_str):
        J, p = menu(name_str); i = next(i for i, x in enumerate(p._entries()) if x['t'] == 'curs'); p.selected[name_str] = i; p.entry = [i, '4']; self.image(J, p, 'infobulle')       # saisie d'une valeur
        for i, entry in enumerate(p._entries()):                                           # chaque liste deroulante ouverte
            if entry['t'] == 'choix' and entry.get('liste'):
                J, p = menu(name_str); p.selected[name_str] = i; p.open_dropdown = [i, 0]; self.image(J, p)

    def page_interface(self):
        saved = os.environ.get('DQ_VITESSE_ANCRE')
        try:
            for anchor in ('1', '0'):                                                    # « Replacer sous la boîte de combat » / « Replacer sur le bord gauche »
                os.environ['DQ_VITESSE_ANCRE'] = anchor; self.page('interface', target='bouton_vitesse')
        finally:
            if saved is None: os.environ.pop('DQ_VITESSE_ANCRE', None)
            else: os.environ['DQ_VITESSE_ANCRE'] = saved
        for target in ('boutons', 'bouton_vitesse', 'msg', 'RootMenu', 'FenetreInconnue'):
            for mask in (False, True):                                                # masque : « Masquée » / « Masqué » sur l'apercu
                J = FakeGame(); J.reg['boutons'] = J.reg['bouton_vitesse'] = J.reg['croix'] = not mask; J.reg['interface_masquees'] = ['msg', 'RootMenu', 'FenetreInconnue'] if mask else []
                self.page('interface', J, target=target)
        J, p = menu('interface'); draw_page(p); z = p.fold_zone                          # infobulle de la barre de titre
        p.mouse_mode = True; p.mouse_pos = ((z[0] + z[2]) / 2, (z[1] + z[3]) / 2); p.tt = (('plier', 0), PA.time.time() - 1); self.image(J, p, 'infobulle')
        J, p = menu('interface'); p.folded = True; self.image(J, p)                       # panneau replie
        J, p = menu('interface'); p.open_dropdown = [0, 0]; self.image(J, p)                  # liste « Interface à modifier » ouverte (intertitres de groupe)

    def messages(self):
        """Les messages d'information, par leurs vrais appels."""
        J, p = menu('etats'); p._save(2); self.image(J, p, 'message')                # « État enregistré dans l'emplacement 2. »
        J, p = menu('etats'); J.failure = 'disque plein'; p._save(2); self.image(J, p, 'message')
        J, p = menu('etats'); J.failure = 'disque plein'; p._load(2); self.image(J, p, 'message')
        J, p = menu('etats'); p._delete(2); self.image(J, p, 'message')              # (le fichier n'existe pas : « Impossible de supprimer l'état »)
        J, p = menu('etats'); file = J.state_path(2)
        try:
            open(file, 'w').close(); p._delete(2); self.image(J, p, 'message')       # « État 2 supprimé. »
        finally:
            if os.path.exists(file): os.remove(file)
        J, p = menu('commandes'); p.capture = ('menu', 1); p.key_press(K.F11); p.capture = None; self.image(J, p, 'message')             # « Cette touche est réservée (F11). »
        J, p = menu('commandes'); J.reg.bind('infos', 0, K.TAB); p.capture = ('menu', 1); p.key_press(K.TAB); self.image(J, p, 'message')       # « Tab retirée de « Infos à l'écran ». »
        J, p = menu('commandes'); J.reg.bind('infos', 0, K.TAB); TP.by_caption(p, 'Menu')['defaut'](); self.image(J, p, 'message')       # « Une touche d'origine est retirée de « Infos à l'écran ». »
        for action, _ in RG.ACTIONS:                                                    # « X retirée de « <chaque action, meme celles qui ne sont pas dans la page> ». »
            J, p = menu('commandes'); name_str = next(n for n in RG.DEFAULT_KEYS[action] if n)
            p.capture = ('haut' if action != 'haut' else 'bas', 0); p.key_press(RG.key_symbol(name_str)); self.image(J, p, 'message')

    def key_list(self):
        """Les noms de toutes les touches que le clavier peut donner."""
        J, p = menu('commandes')
        for name_str in sorted(n for n in dir(K) if n.isupper() and not n.startswith(('MOD_', 'MOTION'))): p._label(RG.key_name(name_str), 12.0)
        self.note(J, p)

    # ---- ce qu'on en tire
    def texts(self, *moments):
        return [t for m, t in self.seen if m in moments]

    def help_lines(self): return [l for _, ls in self.helpers for l in ls]


def phrases(text): return [ph for ph in re.split(r'\s{3,}', text.strip()) if ph]


def _sliced(lookup_key):
    """Découpe `lookup_key` en [texte, trou, texte, trou, ..., texte]."""
    out = []; pos = 0
    for m in TL.TROUS.finditer(lookup_key): out += [lookup_key[pos:m.start()], m.group()]; pos = m.end()
    return out + [lookup_key[pos:]]


def template(lookup_key):
    """Expression régulière d'un texte à trous (%d, %s...) du catalogue."""
    return re.compile('^' + ''.join('.+' if i % 2 else re.escape(x) for i, x in enumerate(_sliced(lookup_key))) + '$')


def without_letters(t):
    """Rien à traduire : pas de mot (chiffres, dates, signes) ou nom brut d'une touche (« BRACKETLEFT », « F5 » : les noms de pyglet, techniques)."""
    return not re.search(r'[^\W\d_]{2,}', t) or re.fullmatch(r'[A-Z][A-Z0-9_]*', t) is not None


def problemes(fr, entry, category):
    """Ce qui cloche entre le parcours en français `fr` et le parcours en anglais `entry` (Visite) selon le catalogue `category` : liste de textes, vide si tout va bien."""
    pb = []; trous = [(template(k), k) for k in category if TL.TROUS.search(k)]
    in_page = set(entry.texts('page', 'infobulle', 'message'))
    for t in sorted(in_page | set(entry.help_lines())):
        if TL.french(t): pb.append('du francais dessine en anglais : %r' % t)
    for k, v in category.items():
        if not v.strip(): pb.append('traduction vide : %r' % k)
        if v == k: pb.append('traduction identique au francais : %r' % k)
    for t in sorted({t for m, t in fr.seen if m in ('page', 'message')}):               # chaque texte francais dessine : sa traduction (ou un mot identique) est dessinee en anglais
        if without_letters(t) or t in NEUTRES: continue
        if t in category:
            if category[t] not in in_page: pb.append('traduction non dessinee : %r -> %r' % (t, category[t]))
            continue
        lookup_keys = [k for g, k in trous if g.match(t)]
        if not lookup_keys: pb.append('texte sans traduction : %r' % t); continue
        if not any(template(category[k]).match(x) for k in lookup_keys for x in in_page): pb.append('texte a trous non traduit a l\'ecran : %r' % t)
    for text, _ in fr.helpers:                                                           # chaque phrase d'aide
        for ph in phrases(text):
            if ph in NEUTRES or ph in category: continue
            if not any(g.match(ph) for g, k in trous): pb.append('phrase d\'aide sans traduction : %r' % ph)
    for text, lines in entry.helpers:                                                      # en anglais, chaque phrase recue est rendue traduite (rejointe : l'infobulle la coupe a sa largeur)
        render = re.sub(r'\s+', ' ', ' '.join(lines))
        for ph in phrases(text):
            tr = entry.catalog.get(ph, ph)          # (la traduction selon le catalogue du parcours en anglais)
            if not without_letters(tr) and re.sub(r'\s+', ' ', tr) not in render: pb.append('phrase d\'aide non rendue traduite : %r (rendu %r)' % (ph, render[:80]))
    return pb


_visites = {}


def visite(language, parts=PARTS):
    """Le parcours d'une langue avec le vrai catalogue, fait une seule fois pour tous les tests (le menu et le catalogue ne changent pas d'un test à l'autre)."""
    if (language, parts) not in _visites: _visites[(language, parts)] = Visite(language, parts)
    return _visites[(language, parts)]


class Base(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        window(); LG.select_language('fr')
        cls.fr = visite('fr'); cls.entry = visite('en'); cls.category = dict(EN_PAUSE.EN)
    def tearDown(self): LG.select_language('fr')


class Walkthrough(Base):
    def test_walkthrough_is_complete(self):
        texts = {t for m, t in self.fr.seen if m == 'page'}
        for expected in ('Paramètres', 'Reprendre', 'Plein écran', 'Replacer sous la boîte de combat', 'Replacer sur le bord gauche', 'Masquée', 'Masqué', 'Touche 2', 'Pas de miniature', 'Emplacement vide', '— vide —', 'Sans date',
                        'Casino : abandon du stade', 'Autres', 'Très rapide', 'En êtes-vous sûr ?', 'Maj gauche', 'Pavé 7', 'Clic molette maintenu + déplacement'):
            self.assertIn(expected, texts, expected)
        self.assertIn('Limité à x4 par cette carte graphique', [ph for t, _ in self.fr.helpers for ph in phrases(t)])
        self.assertGreater(len(texts), 250); self.assertGreater(len(self.fr.helpers), 80)
        for m in ('infobulle', 'message'): self.assertTrue(self.fr.texts(m), m)

    def test_no_problem(self):
        self.assertEqual(problemes(self.fr, self.entry, self.category), [])

    def test_in_english_no_drawn_text_is_french(self):
        self.assertEqual(sorted({t for t in self.entry.texts('page', 'aide', 'infobulle', 'message') if TL.french(t)}), [])

    def test_in_english_translation_is_shown(self):
        texts = set(self.entry.texts('page'))
        for t in ('Settings', 'Resume', 'Display', 'Fullscreen', 'Resolution', 'Sharpness', 'Vignette effect', 'Supersampling', 'Brightness', 'Language', 'Sound', 'Controls', 'Save states', 'Quit', 'Yes', 'No', 'Are you sure?',
                  'Walking speed', 'Camera speed', 'Text speed', 'Battle speed', 'Very fast', 'Hold middle click + move', 'Key 1', 'Key 2', 'Restore default keys', 'Left Shift', 'Numpad 7', 'Hidden', 'Casino: prizes',
                  'HP and MP restored on level up', 'Empty slot', 'World map', 'Battle'):
            self.assertIn(t, texts, t)

    def test_helptexts_rendered_translated_and_cut_to_width(self):
        lines = self.entry.help_lines()
        self.assertIn('Only available in towns and on the world map: the', ' '.join(lines)); self.assertGreater(len(lines), 150)
        self.assertTrue(all(len(l) < 120 for l in lines))

    def test_french_does_not_change_everything_goes_through_tr(self):
        """Catalogue vidé, en mode anglais = exactement les textes du français : la traduction est la seule différence entre les deux langues (les textes français sont ceux d'avant)."""
        saved = LG._catalog; LG._catalog = {}
        try: empty = Visite('en')
        finally: LG._catalog = saved
        self.assertEqual(empty.seen, self.fr.seen); self.assertEqual(empty.helpers, self.fr.helpers)

    def test_each_catalog_key_is_used(self):
        """Une clé qui ne sert nulle part est une faute de frappe (le vrai texte resterait en français) ou un reste."""
        seen = {t for m, t in self.fr.seen} | {ph for t, _ in self.fr.helpers for ph in phrases(t)} | CONSOLE          # (la console : voir la classe Console)
        messages = ' '.join(self.fr.texts('message'))                                                              # (un nom d'action n'est dessiné que dans un message : « ... retirée de « Page suivante ». »)
        gab = [(template(k), k) for k in self.category if TL.TROUS.search(k)]
        inutiles = [k for k in self.category if k not in seen and '« %s »' % k not in messages and not any(k == kk and any(g.match(v) for v in seen) for g, kk in gab)]
        self.assertEqual(sorted(inutiles), [])


class Data(unittest.TestCase):
    """Les données du menu restent en français quelle que soit la langue : les autres tests, la fenêtre et l'historique s'y fient ; la traduction se fait en dessinant."""
    def setUp(self): LG.select_language('en')
    def tearDown(self): LG.select_language('fr')

    def test_labels_values_and_keys(self):
        J, p = menu('commandes')
        self.assertEqual(dict(RG.ACTIONS)['haut'], 'Haut'); self.assertEqual(dict(RG.ACTIONS)['infos'], "Infos à l'écran")
        self.assertEqual(RG.key_name('LSHIFT'), 'Maj gauche'); self.assertEqual(RG.key_name('NUM_7'), 'Pavé 7'); self.assertEqual(RG.key_name(None), '—')
        self.assertEqual(RG.BATTLE_SPEED_NAMES[3.0], 'Très rapide'); self.assertEqual(p._value_name('Vitesse du texte', 0.5), 'Très lent'); self.assertEqual(p._value_name('Interface à modifier', 'boutons'), "Boutons et croix de l'écran")
        self.assertEqual(p._value_name('Langue', 'en'), 'Anglais'); self.assertEqual(p._value_name('Vitesse de marche', 2.0), 'x2'); self.assertEqual(p._value_name('Plein écran', True), 'Oui')
        e = TP.by_caption(p, 'Menu'); self.assertEqual((e['l'], e['v']), ('Menu', ['Entrée', 'Tab']))
        self.assertTrue(PA.Pause.KEY_HELPTEXT.startswith('Entrée : changer la touche'))

    def test_and_are_translated_when_drawn(self):
        self.assertEqual(LG.tr(dict(RG.ACTIONS)['haut']), 'Up'); self.assertEqual(LG.tr(RG.key_name('LSHIFT')), 'Left Shift'); self.assertEqual(LG.tr(RG.key_name('NUM_7')), 'Numpad 7')
        self.assertEqual(LG.tr(RG.BATTLE_SPEED_NAMES[3.0]), 'Very fast'); self.assertEqual(LG.tr(RG.key_name('F5')), 'F5'); self.assertEqual(LG.tr(RG.key_name(None)), '—')

    def test_message_keeps_french_text_and_is_displayed_translated(self):
        J, p = menu('commandes'); J.reg.bind('infos', 0, K.TAB); TP.by_caption(p, 'Menu')['defaut']()
        self.assertEqual(p.message[0], "Une touche d'origine est retirée de « Infos à l'écran »."); self.assertFalse(p.message[2])
        self.assertEqual(p._message_text(), 'A default key is removed from "On-screen info".')
        p.message = (p.message[0], p.message[1] - 5.0) + p.message[2:]; self.assertEqual(p._message_text(), '')              # (plus de 4 secondes : disparu)
        J, p = menu('etats'); J.failure = 'disque plein'; p._save(3)
        self.assertEqual(p.message[0], "Impossible d'enregistrer l'état : OSError('disque plein')"); self.assertTrue(p.message[2])
        self.assertEqual(p._message_text(), "Could not save the state: OSError('disque plein')")
        LG.select_language('fr'); self.assertEqual(p._message_text(), p.message[0])

    def test_deletion_window_keeps_its_french_title(self):
        J, p = menu('etats'); p._request_deletion(4)
        self.assertEqual(p.popup['titre'], "Supprimer l'état 4 ?"); self.assertEqual(p.popup['sel'], 1)

    def test_line_helptexts_remain_french(self):
        J, p = menu('affichage')
        self.assertIn('Plein écran : fenêtre sans bordure', p._line_helptext(TP.by_caption(p, 'Plein écran')))
        J.post.max_msaa = 2; J.reg['msaa'] = 8; self.assertEqual(TP.by_caption(p, 'Antialiasing')['aide'], 'Limited to x2 by this graphics card')       # (texte à trou : traduit puis rempli, voir Pause._entries_display)


class Keys(unittest.TestCase):
    def tearDown(self): LG.select_language('fr')

    def test_all_key_names_in_english(self):
        LG.select_language('en')
        names = sorted({n for n in dir(K) if n.isupper() and not n.startswith(('MOD_', 'MOTION'))})
        self.assertGreater(len(names), 100)
        for n in names:
            fr = RG.key_name(n); entry = LG.tr(fr)
            self.assertFalse(TL.french(entry), '%s : %r -> %r' % (n, fr, entry)); self.assertNotIn('Pavé', entry)
            if fr != n and fr in EN_PAUSE.EN: self.assertNotEqual(entry, fr)
        self.assertEqual([LG.tr(RG.key_name(n)) for n in ('LSHIFT', 'RSHIFT', 'LCTRL', 'RCTRL', 'LALT', 'RALT', 'SPACE', 'RETURN', 'ENTER', 'BACKSPACE', 'DELETE', 'INSERT', 'HOME', 'END', 'PAGEUP', 'PAGEDOWN', 'CAPSLOCK', 'NUM_ADD', 'NUM_SUBTRACT')],
                         ['Left Shift', 'Right Shift', 'Left Ctrl', 'Right Ctrl', 'Left Alt', 'Right Alt', 'Space', 'Enter', 'Numpad Enter', 'Backspace', 'Delete', 'Insert', 'Home', 'End', 'Page Up', 'Page Down', 'Caps Lock', 'Numpad +', 'Numpad -'])

    def test_in_french_nothing_changes(self):
        LG.select_language('fr')
        for n, att in (('LSHIFT', 'Maj gauche'), ('RETURN', 'Entrée'), ('NUM_3', 'Pavé 3'), ('F1', 'F1'), ('BACKSPACE', 'Retour arrière')): self.assertEqual(LG.tr(RG.key_name(n)), att)

    def test_whole_pyglet_numpad_is_translated(self):
        for n in dir(K):
            if n.startswith('NUM_'): self.assertIn(RG.key_name(n), EN_PAUSE.EN, n)


class Console(unittest.TestCase):
    """Les messages de la console de settings.py et de pause.py."""
    def tearDown(self): LG.select_language('fr')

    def output(self, f):
        s = io.StringIO()
        with contextlib.redirect_stdout(s): f()
        return s.getvalue().strip()

    def test_unreadable_settings(self):
        with tempfile.TemporaryDirectory() as t:
            path = os.path.join(t, 'settings.json')
            with open(path, 'w', encoding='utf-8') as f: f.write('{pas du json')
            LG.select_language('fr'); fr = self.output(lambda: RG.Settings(path))
            LG.select_language('en'); entry = self.output(lambda: RG.Settings(path))
        self.assertTrue(fr.startswith('Reglages illisibles (%s) : valeurs par defaut (' % path), fr); self.assertTrue(entry.startswith('Unreadable settings (%s): default values (' % path), entry)

    def test_settings_not_stored(self):
        with tempfile.TemporaryDirectory() as t:
            r = RG.Settings(os.path.join(t, 'dossier_absent', 'settings.json'))
            LG.select_language('fr'); fr = self.output(r.store)
            LG.select_language('en'); entry = self.output(r.store)
        self.assertTrue(fr.startswith('Reglages non enregistres : '), fr); self.assertTrue(entry.startswith('Settings not saved: '), entry)

    def test_game_font_not_loaded(self):
        """Le fichier de police du jeu existe mais pyglet ne peut pas le charger (ici : refusé exprès) : la console le dit dans la langue de l'outil."""
        add_file = pyglet.font.add_file
        def refused(*a, **k): raise OSError('police refusee')
        outputs = []
        try:
            pyglet.font.add_file = refused
            with tempfile.TemporaryDirectory() as t:
                open(os.path.join(t, 'ui_font.otf'), 'wb').close()
                for language in ('fr', 'en'):
                    J = FakeGame(); J.args = types.SimpleNamespace(cache=t); p = PA.Pause(J); LG.select_language(language); outputs.append(self.output(lambda: p._label('Son', 12.0)))
        finally: pyglet.font.add_file = add_file
        self.assertTrue(outputs[0].startswith('police du jeu non chargee : police refusee'), outputs[0]); self.assertTrue(outputs[1].startswith('game font not loaded: police refusee'), outputs[1])


class Catalog(unittest.TestCase):
    """Les règles du catalogue (tests/test_language.py) pour texts_en\\pause.py seul, plus : pas de traduction vide ni identique, une traduction n'est pas elle-même une clé."""
    def test_rules(self):
        for fr, entry in EN_PAUSE.EN.items():
            self.assertTrue(entry.strip() and entry != fr, '%r -> %r' % (fr, entry))
            self.assertEqual(TL.TROUS.findall(fr), TL.TROUS.findall(entry), fr)
            self.assertEqual((fr[:len(fr) - len(fr.lstrip())], fr[len(fr.rstrip()):]), (entry[:len(entry) - len(entry.lstrip())], entry[len(entry.rstrip()):]), fr)
            self.assertEqual(fr.count('\n'), entry.count('\n'), fr); self.assertFalse(TL.french(entry), '%r -> %r' % (fr, entry))
            self.assertNotIn('   ', fr.strip(), 'une cle est UNE phrase d\'aide : %r' % fr); self.assertNotIn('   ', entry.strip())

    def test_translating_twice_changes_nothing(self):
        """Le menu traduit parfois un texte déjà traduit (aide assemblée, message dont les valeurs sont traduites) : l'anglais ne doit pas être lui-même une clé du catalogue."""
        for fr, entry in EN_PAUSE.EN.items(): self.assertNotIn(entry, EN_PAUSE.EN, '%r -> %r est aussi une cle' % (fr, entry))

    def test_no_duplicate_with_other_base_files(self):
        others = {}
        for name_str, c in TL.catalog_by_file().items():
            if name_str != 'pause': others.update(c)
        self.assertEqual(sorted(set(EN_PAUSE.EN) & set(others)), [])


class Mutations(Base):
    """Le contrôle de la vérification elle-même : chaque faute introduite à la main est vue par `problemes`."""

    def anglais(self, parts, catalog=None):
        saved = LG._catalog
        try:
            if catalog is not None: LG._catalog = catalog
            return Visite('en', parts)
        finally: LG._catalog = saved

    def check(self, parts, catalog=None, category=None):
        """`problemes` pour ces morceaux du parcours, avec ce catalogue (None : le vrai) ; cat : le catalogue de pause.py selon `problemes`."""
        return problemes(visite('fr', parts), self.anglais(parts, catalog), self.category if category is None else category)

    @contextlib.contextmanager
    def muter(self, klass, name_str, old, new):
        """Remplace, le temps du bloc, la méthode `klass.name_str` par une copie dont le texte `old` est devenu `new` (exécutée avec les globales du module de la classe)."""
        f = getattr(klass, name_str); src = textwrap.dedent(inspect.getsource(f))
        self.assertIn(old, src, 'la mutation ne porte sur rien : %r' % old)
        ns = dict(vars(sys.modules[klass.__module__])); exec(compile(src.replace(old, new, 1), '<mutation>', 'exec'), ns)
        setattr(klass, name_str, types.FunctionType(ns[name_str].__code__, vars(sys.modules[klass.__module__]), name_str))          # (avec les globales du module telles qu'elles sont pendant le parcours : l'horloge figée, par exemple)
        try: yield
        finally: setattr(klass, name_str, f)

    def without(self, *lookup_keys):
        """Le catalogue du parcours et celui de `problemes` sans ces clés."""
        return {k: v for k, v in LG.catalog().items() if k not in lookup_keys}, {k: v for k, v in self.category.items() if k not in lookup_keys}

    def test_baseline_without_problem(self):
        for parts in (('page_root',), ('page_commands',), ('messages',), ('page_savestates',)): self.assertEqual(self.check(parts), [], parts)

    def test_a_key_removed_from_the_catalog(self):
        c, c_pause = self.without('Reprendre')
        pb = self.check(('page_root',), c, c_pause)
        self.assertTrue(any('Reprendre' in x for x in pb), pb)

    def test_a_help_sentence_removed_from_the_catalog(self):
        c, c_pause = self.without("Langue de l'outil : paramètres, historique, sauvegardes, licence, informations...")
        pb = self.check(('page_display',), c, c_pause)
        self.assertTrue(any("Langue de l'outil" in x for x in pb), pb)

    def test_a_key_name_removed_from_the_catalog(self):
        c, c_pause = self.without('Maj gauche')
        pb = self.check(('key_list',), c, c_pause)
        self.assertTrue(any('Maj gauche' in x for x in pb), pb)

    def test_tr_of_helptexts_removed(self):
        with self.muter(PA.Pause, '_helptext_lines', 'l = tr(l); cur', 'cur'): pb = self.check(('page_root',))
        self.assertTrue(any('aide' in x for x in pb), pb)

    def test_tr_of_key_n_removed(self):
        with self.muter(PA.Pause, 'draw_all', "self._label(tr('Touche %d') % (c + 1)", "self._label('Touche %d' % (c + 1)"): pb = self.check(('page_commands',))
        self.assertTrue(any('Touche' in x for x in pb), pb)

    def test_tr_of_messages_removed(self):
        with self.muter(PA.Pause, '_message_text', 'return tr(m[3]) % tuple(tr(v) for v in m[4]) if m[4] else tr(m[3])', 'return m[0]'): pb = self.check(('messages',))
        self.assertTrue(any('tat' in x or 'touche' in x.lower() for x in pb), pb)

    def test_tr_of_message_values_removed(self):
        """Le nom de l'action dans « Tab retirée de « Infos à l'écran » » est traduit lui aussi."""
        with self.muter(PA.Pause, '_message_text', 'tuple(tr(v) for v in m[4])', 'm[4]'): pb = self.check(('messages',))
        self.assertTrue(any('removed from' in x for x in pb), pb)

    def test_tr_of_confirmation_title_removed(self):
        with self.muter(PA.Pause, '_draw_popup', "tr(p['modele']) % p['valeurs'] if p.get('modele') else p['titre']", "p['titre']"): pb = self.check(('page_savestates',))
        self.assertTrue(any("Supprimer l'état" in x for x in pb), pb)

    def test_an_emptied_translation(self):
        c = dict(LG.catalog(), **{'Résolution': ''})
        pb = self.check(('page_display',), c, dict(self.category, **{'Résolution': ''}))
        self.assertTrue(any('vide' in x for x in pb), pb)

    def test_a_translation_left_in_french(self):
        c = dict(LG.catalog(), **{'Reprendre': 'Reprendre'})
        pb = self.check(('page_root',), c, dict(self.category, **{'Reprendre': 'Reprendre'}))
        self.assertTrue(any('identique' in x for x in pb), pb)

    def test_without_tr_french_is_unchanged(self):
        """Un menu sans le `tr` des aides rend en français exactement les mêmes textes (le français est la clé)."""
        with self.muter(PA.Pause, '_helptext_lines', 'l = tr(l); cur', 'cur'): f = Visite('fr', ('page_root', 'page_commands'))
        self.assertEqual(f.seen, visite('fr', ('page_root', 'page_commands')).seen)


if __name__ == '__main__':
    unittest.main(verbosity=1)
