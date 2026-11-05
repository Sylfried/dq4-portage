"""Langue de l'outil (D-238) : pages du menu Paramètres (Pause), en anglais et en français.

Le menu est piloté avec un faux « jeu » (voir test_pause_pages.py) et DESSINÉ pour de vrai dans une fenêtre pyglet cachée (EGL sans écran sous Linux) ; chaque étiquette demandée à la fenêtre (`_etiq`) est notée.
Le parcours couvre toutes les pages (racine, Affichage, Interface avec chacun de ses éléments, Son, Commandes, Modifications, États, Quitter), toutes les valeurs de toutes les listes, l'aide de chaque ligne, les consignes
de capture d'une touche et de saisie d'une valeur, l'infobulle de la barre de titre, la fenêtre de confirmation, les messages d'information (par leurs vrais appels), les noms de toutes les touches du clavier.

    python3 tests/test_langue_pause.py

Règles : (1) en anglais, aucun texte dessiné n'est du français ; (2) tout texte français dessiné a sa traduction (liste blanche : les mots identiques dans les deux langues) et l'anglais dessiné est bien celle du catalogue ;
(3) en français, les textes sont exactement ceux d'avant (le catalogue vidé donne, en mode anglais, les mêmes textes que le français : la traduction est la seule différence) ; (4) les DONNÉES du menu (libellés, noms de valeurs,
noms de touches, messages) restent en français, elles sont traduites en les dessinant (les autres tests et les autres écrans, comme l'historique, s'y fient) ; (5) pas de clé inutile ni de traduction vide ou identique dans
textes_en\\pause.py ; (6) mutations de contrôle : une clé retirée, un `tr` retiré de plusieurs endroits, une traduction vidée ou laissée en français font échouer la vérification."""
import contextlib, inspect, io, os, re, sys, tempfile, textwrap, time, types, unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import _chemins
import pyglet
if sys.platform.startswith('linux') and not os.environ.get('DISPLAY'): pyglet.options['headless'] = True; pyglet.options['shadow_window'] = False
import test_pause_pages as TP
import test_langue as TL
from dq4_pc import langue as LG
from dq4_pc.persistance import reglages as RG
from dq4_pc.menus import pause as PA
from dq4_pc.textes_en import pause as EN_PAUSE

K = pyglet.window.key
PAGES = ('racine', 'affichage', 'son', 'commandes', 'modifications', 'etats', 'quitter', 'interface')
# Mots identiques en français et en anglais, ou noms techniques : dessinés tels quels dans les deux langues, sans entrée dans le catalogue (une entrée identique ferait un doublon avec les autres fichiers).
NEUTRES = {'Interface', 'Modifications', 'Casino', 'Menu', 'Normal', 'Action', 'Tab', 'Shader', 'Antialiasing', 'EPX x8', 'Pixel perfect', 'x2', 'x4', 'x8',
           'FenetreInconnue'}          # (le faux nom que le faux jeu donne à une fenêtre que l'outil ne connaît pas)
_fen = []
CONSOLE = {'police du jeu non chargee :', 'Reglages illisibles (%s) : valeurs par defaut (%r)', 'Reglages non enregistres :'}          # messages de la console (testés dans la classe Console)


def fenetre():
    """Fenêtre pyglet cachée (le dessin du menu a besoin d'un contexte GL) ; SkipTest si la machine ne peut pas en ouvrir une."""
    if not _fen:
        try: _fen.append(pyglet.window.Window(width=1280, height=720, visible=False))
        except Exception as ex: raise unittest.SkipTest('pas de fenetre pyglet possible : %r' % (ex,))
    return _fen[0]


def png(couleur=(40, 90, 160)):
    from PIL import Image
    b = io.BytesIO(); Image.new('RGB', (64, 36), couleur).save(b, 'PNG'); return b.getvalue()


class FauxHud:
    pris = None
    def dessiner(self, *a): pass
    def rect(self, n): return (60.0 + 40 * len(n), 120.0, 90.0, 70.0)
    def prendre(self, *a): pass
    def deplacer(self, *a): pass


class FauxJeu(TP.FauxJeu):
    """Le faux jeu des pages avec ce que `dessiner()` lui demande. `vus` : les textes demandés à `_etiq`, notés avec le moment du parcours (`moment`)."""
    est_plein = False; mode = 4; res = (1280, 720); aide = False
    NOMS = {n: [1] for n in PA.NOMS_FENETRES if n not in PA.INTERFACES_PROPRES}

    def __init__(self, etats=True):
        super().__init__(); self.post = types.SimpleNamespace(max_msaa=None); self.hud = FauxHud(); self.vus = []; self.moment = 'page'; self.cache_etiq = {}; self.echec = None
        self.etats = {1: ({'date': '2026-10-31 19:21:05', 'lieu': 'Carte du monde'}, png()), 2: ({'date': '2026-11-02 08:05:59', 'lieu': 'Combat'}, png((160, 60, 40))),
                      3: ({'lieu': 'mak1f1'}, None), 5: ({'date': '2026-11-03 23:59:00', 'lieu': 'Combat'}, None)} if etats else {}
        self.son = types.SimpleNamespace(actif=True, ecoute=False, ecouter=lambda b: None, tick=lambda: None)
    def regler_plein_ecran(self, v): self.est_plein = v
    def resolutions(self): return [(1280, 720), (1920, 1080)]
    def resolution_courante(self): return self.res
    def regler_resolution(self, v): self.res = v
    def regler_mode(self, v): self.mode = v
    def noms_fenetres(self): return dict(self.NOMS, FenetreInconnue=[1])          # (+ une fenêtre inconnue de l'outil : groupe « Autres »)
    def infos_etat(self, n): return self.etats.get(n)
    def chemin_etat(self, n): return os.path.join(tempfile.gettempdir(), 'dq4_test_langue_etat_inexistant_%d' % n)
    def sauver_etat(self, n, miniature=b''):
        if self.echec: raise OSError(self.echec)
    def charger_etat(self, n):
        if self.echec: raise OSError(self.echec)
    def _png_miniature(self, t): return b''
    def apercu_interface(self, cible): return (300.0, 200.0, 700.0, 420.0)
    def nouvel_echantillon(self): pass
    def regler_infos(self, v): self.aide = v
    def quitter(self): pass
    def retour_titre(self): pass
    def _etiq(self, texte, taille, couleur=(255, 255, 255, 255), polices=()):
        self.vus.append((self.moment, texte)); fenetre()
        k = (texte, round(taille, 1), couleur)
        if k not in self.cache_etiq: self.cache_etiq[k] = pyglet.text.Label(texte, font_size=taille, color=couleur, anchor_x='left', anchor_y='baseline')
        return self.cache_etiq[k]


class PauseEspion(PA.Pause):
    """Le menu qui note chaque appel de `_lignes_aide` : (texte brut reçu, lignes rendues)."""
    def __init__(self, jeu): super().__init__(jeu); self.aides = []
    def _lignes_aide(self, texte, maxw, fz):
        ls = super()._lignes_aide(texte, maxw, fz); self.aides.append((texte, ls)); return ls


def menu(page, jeu=None, **attrs):
    J = jeu or FauxJeu(); p = PauseEspion(J); p.ouvert = True; p.pile = [page]
    for k, v in attrs.items(): setattr(p, k, v)
    return J, p


def dessine(p):
    fenetre().switch_to(); fenetre().clear(); p.dessiner()


class HorlogeFigee:
    """Le module `time` du menu, dont l'heure ne bouge plus (le curseur clignotant de la saisie, les animations : le dessin est le même d'un parcours à l'autre)."""
    def __getattr__(self, nom): return getattr(time, nom)
    @staticmethod
    def time(): return 1000.0


PARTIES = tuple('page_' + n for n in PAGES) + ('messages', 'touches')


class Visite:
    """Le parcours de l'interface du menu dans une langue : `vus` = [(moment, texte)] dessinés (moment : page, aide, infobulle, message) ; `aides` = [(texte brut, lignes rendues)]. `parties` : les morceaux
    du parcours (par défaut tous : les pages, les messages d'information, les noms de touches)."""
    def __init__(self, langue, parties=PARTIES):
        self.langue = langue; self.vus = []; self.aides = []; horloge = PA.time
        LG.regler(langue); PA.time = HorlogeFigee(); self.catalogue = LG.catalogue()          # (le catalogue en vigueur pendant ce parcours)
        try:
            for nom in parties: getattr(self, nom)()
        finally: LG.regler('fr'); PA.time = horloge

    def noter(self, J, p):
        self.vus.extend(J.vus); self.aides.extend(p.aides); J.vus.clear(); p.aides.clear()

    def image(self, J, p, moment='page'):
        J.moment = moment; dessine(p); J.moment = 'page'; self.noter(J, p)

    def lignes(self, J, p):
        """Les noms de toutes les valeurs des listes, et l'aide de chaque ligne (comme l'infobulle : phrases coupées à la largeur)."""
        for en in p._entrees():
            if en['t'] == 'choix':
                for v in en['vals']: p._et(p._nom_valeur(en['l'], v), 12.0)
        J.moment = 'aide'
        for en in p._entrees():
            texte = p._aide_ligne(en)
            if texte:
                for l in p._lignes_aide(texte, 520.0, 12.0): p._et(l, 12.0)
        J.moment = 'page'; self.noter(J, p)

    def page(self, nom, J=None, **attrs):
        J, p = menu(nom, J, **attrs); self.image(J, p)
        b = p.barre                                                                    # page qui defile : chaque ligne passe dans la fenetre
        if b:
            d, fin = b['base'], b['base'] + b['n'] - b['vis']
            while d < fin: d = min(d + b['vis'] - 1, fin); p.debut[nom] = d; self.image(J, p)          # (une page de lignes a la fois, avec une ligne de recouvrement)
        self.lignes(J, p)
        return J, p

    def page_racine(self): self.page('racine')
    def page_modifications(self): self.page('modifications')
    def page_quitter(self): self.page('quitter')

    def page_etats(self):
        for act in ('creer', 'charger', 'supprimer'):
            J, p = self.page('etats', action_etat=act)
            if act == 'creer':
                for i in range(1, 6): p.sel['etats'] = i; self.image(J, p)             # chaque sorte d'emplacement : miniature et date, date seule, rien, vide (« Pas de miniature », « Emplacement vide »)
        self.page('etats', FauxJeu(etats=False))
        for n in (1, 9):
            J, p = menu('etats'); p._demander_suppression(n); self.image(J, p)          # fenetre de confirmation (n = 9 : emplacement vide, sans date)

    def page_affichage(self):
        self.page('affichage')
        J = FauxJeu(); J.reg['msaa'] = 8; J.post.max_msaa = 4; J.est_plein = True; self.page('affichage', J)          # « Limité à x4... » ; resolution grisee en plein ecran
        self.listes_et_saisie('affichage')

    def page_son(self): self.page('son'); self.listes_et_saisie('son')

    def page_commandes(self):
        self.page('commandes')
        for act in ('haut', 'accel', 'cam_gauche'):
            for col in (0, 1):
                J, p = menu('commandes'); p.capture = (act, col); self.image(J, p, 'infobulle')                       # « Appuie sur la touche pour... »
        self.listes_et_saisie('commandes')

    def listes_et_saisie(self, nom):
        J, p = menu(nom); i = next(i for i, x in enumerate(p._entrees()) if x['t'] == 'curs'); p.sel[nom] = i; p.saisie = [i, '4']; self.image(J, p, 'infobulle')       # saisie d'une valeur
        for i, en in enumerate(p._entrees()):                                           # chaque liste deroulante ouverte
            if en['t'] == 'choix' and en.get('liste'):
                J, p = menu(nom); p.sel[nom] = i; p.deroule = [i, 0]; self.image(J, p)

    def page_interface(self):
        sauve = os.environ.get('DQ_VITESSE_ANCRE')
        try:
            for ancre in ('1', '0'):                                                    # « Replacer sous la boîte de combat » / « Replacer sur le bord gauche »
                os.environ['DQ_VITESSE_ANCRE'] = ancre; self.page('interface', cible='bouton_vitesse')
        finally:
            if sauve is None: os.environ.pop('DQ_VITESSE_ANCRE', None)
            else: os.environ['DQ_VITESSE_ANCRE'] = sauve
        for cible in ('boutons', 'bouton_vitesse', 'msg', 'RootMenu', 'FenetreInconnue'):
            for masque in (False, True):                                                # masque : « Masquée » / « Masqué » sur l'apercu
                J = FauxJeu(); J.reg['boutons'] = J.reg['bouton_vitesse'] = J.reg['croix'] = not masque; J.reg['interface_masquees'] = ['msg', 'RootMenu', 'FenetreInconnue'] if masque else []
                self.page('interface', J, cible=cible)
        J, p = menu('interface'); dessine(p); z = p.zone_plier                          # infobulle de la barre de titre
        p.mode_souris = True; p.pos_souris = ((z[0] + z[2]) / 2, (z[1] + z[3]) / 2); p.tt = (('plier', 0), PA.time.time() - 1); self.image(J, p, 'infobulle')
        J, p = menu('interface'); p.plie = True; self.image(J, p)                       # panneau replie
        J, p = menu('interface'); p.deroule = [0, 0]; self.image(J, p)                  # liste « Interface à modifier » ouverte (intertitres de groupe)

    def messages(self):
        """Les messages d'information, par leurs vrais appels."""
        J, p = menu('etats'); p._sauver(2); self.image(J, p, 'message')                # « État enregistré dans l'emplacement 2. »
        J, p = menu('etats'); J.echec = 'disque plein'; p._sauver(2); self.image(J, p, 'message')
        J, p = menu('etats'); J.echec = 'disque plein'; p._charger(2); self.image(J, p, 'message')
        J, p = menu('etats'); p._supprimer(2); self.image(J, p, 'message')              # (le fichier n'existe pas : « Impossible de supprimer l'état »)
        J, p = menu('etats'); fichier = J.chemin_etat(2)
        try:
            open(fichier, 'w').close(); p._supprimer(2); self.image(J, p, 'message')       # « État 2 supprimé. »
        finally:
            if os.path.exists(fichier): os.remove(fichier)
        J, p = menu('commandes'); p.capture = ('menu', 1); p.touche(K.F11); p.capture = None; self.image(J, p, 'message')             # « Cette touche est réservée (F11). »
        J, p = menu('commandes'); J.reg.lier('infos', 0, K.TAB); p.capture = ('menu', 1); p.touche(K.TAB); self.image(J, p, 'message')       # « Tab retirée de « Infos à l'écran ». »
        J, p = menu('commandes'); J.reg.lier('infos', 0, K.TAB); TP.par_libelle(p, 'Menu')['defaut'](); self.image(J, p, 'message')       # « Une touche d'origine est retirée de « Infos à l'écran ». »
        for action, _ in RG.ACTIONS:                                                    # « X retirée de « <chaque action, meme celles qui ne sont pas dans la page> ». »
            J, p = menu('commandes'); nom = next(n for n in RG.TOUCHES_DEF[action] if n)
            p.capture = ('haut' if action != 'haut' else 'bas', 0); p.touche(RG.symbole(nom)); self.image(J, p, 'message')

    def touches(self):
        """Les noms de toutes les touches que le clavier peut donner."""
        J, p = menu('commandes')
        for nom in sorted(n for n in dir(K) if n.isupper() and not n.startswith(('MOD_', 'MOTION'))): p._et(RG.nom_touche(nom), 12.0)
        self.noter(J, p)

    # ---- ce qu'on en tire
    def textes(self, *moments):
        return [t for m, t in self.vus if m in moments]

    def lignes_aide(self): return [l for _, ls in self.aides for l in ls]


def phrases(texte): return [ph for ph in re.split(r'\s{3,}', texte.strip()) if ph]


def _decoupe(cle):
    """Découpe `cle` en [texte, trou, texte, trou, ..., texte]."""
    out = []; pos = 0
    for m in TL.TROUS.finditer(cle): out += [cle[pos:m.start()], m.group()]; pos = m.end()
    return out + [cle[pos:]]


def gabarit(cle):
    """Expression régulière d'un texte à trous (%d, %s...) du catalogue."""
    return re.compile('^' + ''.join('.+' if i % 2 else re.escape(x) for i, x in enumerate(_decoupe(cle))) + '$')


def sans_lettres(t):
    """Rien à traduire : pas de mot (chiffres, dates, signes) ou nom brut d'une touche (« BRACKETLEFT », « F5 » : les noms de pyglet, techniques)."""
    return not re.search(r'[^\W\d_]{2,}', t) or re.fullmatch(r'[A-Z][A-Z0-9_]*', t) is not None


def problemes(fr, en, cat):
    """Ce qui cloche entre le parcours en français `fr` et le parcours en anglais `en` (Visite) selon le catalogue `cat` : liste de textes, vide si tout va bien."""
    pb = []; trous = [(gabarit(k), k) for k in cat if TL.TROUS.search(k)]
    en_page = set(en.textes('page', 'infobulle', 'message'))
    for t in sorted(en_page | set(en.lignes_aide())):
        if TL.francais(t): pb.append('du francais dessine en anglais : %r' % t)
    for k, v in cat.items():
        if not v.strip(): pb.append('traduction vide : %r' % k)
        if v == k: pb.append('traduction identique au francais : %r' % k)
    for t in sorted({t for m, t in fr.vus if m in ('page', 'message')}):               # chaque texte francais dessine : sa traduction (ou un mot identique) est dessinee en anglais
        if sans_lettres(t) or t in NEUTRES: continue
        if t in cat:
            if cat[t] not in en_page: pb.append('traduction non dessinee : %r -> %r' % (t, cat[t]))
            continue
        cles = [k for g, k in trous if g.match(t)]
        if not cles: pb.append('texte sans traduction : %r' % t); continue
        if not any(gabarit(cat[k]).match(x) for k in cles for x in en_page): pb.append('texte a trous non traduit a l\'ecran : %r' % t)
    for texte, _ in fr.aides:                                                           # chaque phrase d'aide
        for ph in phrases(texte):
            if ph in NEUTRES or ph in cat: continue
            if not any(g.match(ph) for g, k in trous): pb.append('phrase d\'aide sans traduction : %r' % ph)
    for texte, lignes in en.aides:                                                      # en anglais, chaque phrase recue est rendue traduite (rejointe : l'infobulle la coupe a sa largeur)
        rendu = re.sub(r'\s+', ' ', ' '.join(lignes))
        for ph in phrases(texte):
            tr = en.catalogue.get(ph, ph)          # (la traduction selon le catalogue du parcours en anglais)
            if not sans_lettres(tr) and re.sub(r'\s+', ' ', tr) not in rendu: pb.append('phrase d\'aide non rendue traduite : %r (rendu %r)' % (ph, rendu[:80]))
    return pb


_visites = {}


def visite(langue, parties=PARTIES):
    """Le parcours d'une langue avec le vrai catalogue, fait une seule fois pour tous les tests (le menu et le catalogue ne changent pas d'un test à l'autre)."""
    if (langue, parties) not in _visites: _visites[(langue, parties)] = Visite(langue, parties)
    return _visites[(langue, parties)]


class Base(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fenetre(); LG.regler('fr')
        cls.fr = visite('fr'); cls.en = visite('en'); cls.cat = dict(EN_PAUSE.EN)
    def tearDown(self): LG.regler('fr')


class Parcours(Base):
    def test_le_parcours_est_complet(self):
        textes = {t for m, t in self.fr.vus if m == 'page'}
        for attendu in ('Paramètres', 'Reprendre', 'Plein écran', 'Replacer sous la boîte de combat', 'Replacer sur le bord gauche', 'Masquée', 'Masqué', 'Touche 2', 'Pas de miniature', 'Emplacement vide', '— vide —', 'Sans date',
                        'Casino : abandon du stade', 'Autres', 'Très rapide', 'En êtes-vous sûr ?', 'Maj gauche', 'Pavé 7', 'Clic molette maintenu + déplacement'):
            self.assertIn(attendu, textes, attendu)
        self.assertIn('Limité à x4 par cette carte graphique', [ph for t, _ in self.fr.aides for ph in phrases(t)])
        self.assertGreater(len(textes), 250); self.assertGreater(len(self.fr.aides), 80)
        for m in ('infobulle', 'message'): self.assertTrue(self.fr.textes(m), m)

    def test_aucun_probleme(self):
        self.assertEqual(problemes(self.fr, self.en, self.cat), [])

    def test_en_anglais_aucun_texte_dessine_n_est_du_francais(self):
        self.assertEqual(sorted({t for t in self.en.textes('page', 'aide', 'infobulle', 'message') if TL.francais(t)}), [])

    def test_en_anglais_on_voit_la_traduction(self):
        textes = set(self.en.textes('page'))
        for t in ('Settings', 'Resume', 'Display', 'Fullscreen', 'Resolution', 'Sharpness', 'Vignette effect', 'Supersampling', 'Brightness', 'Language', 'Sound', 'Controls', 'Save states', 'Quit', 'Yes', 'No', 'Are you sure?',
                  'Walking speed', 'Camera speed', 'Text speed', 'Battle speed', 'Very fast', 'Hold middle click + move', 'Key 1', 'Key 2', 'Restore default keys', 'Left Shift', 'Numpad 7', 'Hidden', 'Casino: prizes',
                  'HP and MP restored on level up', 'Empty slot', 'World map', 'Battle'):
            self.assertIn(t, textes, t)

    def test_les_aides_sont_rendues_traduites_et_coupees_a_la_largeur(self):
        lignes = self.en.lignes_aide()
        self.assertIn('Only available in towns and on the world map: the', ' '.join(lignes)); self.assertGreater(len(lignes), 150)
        self.assertTrue(all(len(l) < 120 for l in lignes))

    def test_le_francais_ne_change_pas_tout_passe_par_tr(self):
        """Catalogue vidé, en mode anglais = exactement les textes du français : la traduction est la seule différence entre les deux langues (les textes français sont ceux d'avant)."""
        sauve = LG._catalogue; LG._catalogue = {}
        try: vide = Visite('en')
        finally: LG._catalogue = sauve
        self.assertEqual(vide.vus, self.fr.vus); self.assertEqual(vide.aides, self.fr.aides)

    def test_chaque_cle_du_catalogue_sert(self):
        """Une clé qui ne sert nulle part est une faute de frappe (le vrai texte resterait en français) ou un reste."""
        vus = {t for m, t in self.fr.vus} | {ph for t, _ in self.fr.aides for ph in phrases(t)} | CONSOLE          # (la console : voir la classe Console)
        messages = ' '.join(self.fr.textes('message'))                                                              # (un nom d'action n'est dessiné que dans un message : « ... retirée de « Page suivante ». »)
        gab = [(gabarit(k), k) for k in self.cat if TL.TROUS.search(k)]
        inutiles = [k for k in self.cat if k not in vus and '« %s »' % k not in messages and not any(k == kk and any(g.match(v) for v in vus) for g, kk in gab)]
        self.assertEqual(sorted(inutiles), [])


class Donnees(unittest.TestCase):
    """Les données du menu restent en français quelle que soit la langue : les autres tests, la fenêtre et l'historique s'y fient ; la traduction se fait en dessinant."""
    def setUp(self): LG.regler('en')
    def tearDown(self): LG.regler('fr')

    def test_libelles_valeurs_et_touches(self):
        J, p = menu('commandes')
        self.assertEqual(dict(RG.ACTIONS)['haut'], 'Haut'); self.assertEqual(dict(RG.ACTIONS)['infos'], "Infos à l'écran")
        self.assertEqual(RG.nom_touche('LSHIFT'), 'Maj gauche'); self.assertEqual(RG.nom_touche('NUM_7'), 'Pavé 7'); self.assertEqual(RG.nom_touche(None), '—')
        self.assertEqual(RG.NOMS_VITESSE_COMBAT[3.0], 'Très rapide'); self.assertEqual(p._nom_valeur('Vitesse du texte', 0.5), 'Très lent'); self.assertEqual(p._nom_valeur('Interface à modifier', 'boutons'), "Boutons et croix de l'écran")
        self.assertEqual(p._nom_valeur('Langue', 'en'), 'Anglais'); self.assertEqual(p._nom_valeur('Vitesse de marche', 2.0), 'x2'); self.assertEqual(p._nom_valeur('Plein écran', True), 'Oui')
        e = TP.par_libelle(p, 'Menu'); self.assertEqual((e['l'], e['v']), ('Menu', ['Entrée', 'Tab']))
        self.assertTrue(PA.Pause.AIDE_TOUCHE.startswith('Entrée : changer la touche'))

    def test_et_se_traduisent_en_les_dessinant(self):
        self.assertEqual(LG.tr(dict(RG.ACTIONS)['haut']), 'Up'); self.assertEqual(LG.tr(RG.nom_touche('LSHIFT')), 'Left Shift'); self.assertEqual(LG.tr(RG.nom_touche('NUM_7')), 'Numpad 7')
        self.assertEqual(LG.tr(RG.NOMS_VITESSE_COMBAT[3.0]), 'Very fast'); self.assertEqual(LG.tr(RG.nom_touche('F5')), 'F5'); self.assertEqual(LG.tr(RG.nom_touche(None)), '—')

    def test_le_message_garde_son_texte_francais_et_s_affiche_traduit(self):
        J, p = menu('commandes'); J.reg.lier('infos', 0, K.TAB); TP.par_libelle(p, 'Menu')['defaut']()
        self.assertEqual(p.message[0], "Une touche d'origine est retirée de « Infos à l'écran »."); self.assertFalse(p.message[2])
        self.assertEqual(p._texte_message(), 'A default key is removed from "On-screen info".')
        p.message = (p.message[0], p.message[1] - 5.0) + p.message[2:]; self.assertEqual(p._texte_message(), '')              # (plus de 4 secondes : disparu)
        J, p = menu('etats'); J.echec = 'disque plein'; p._sauver(3)
        self.assertEqual(p.message[0], "Impossible d'enregistrer l'état : OSError('disque plein')"); self.assertTrue(p.message[2])
        self.assertEqual(p._texte_message(), "Could not save the state: OSError('disque plein')")
        LG.regler('fr'); self.assertEqual(p._texte_message(), p.message[0])

    def test_la_fenetre_de_suppression_garde_son_titre_francais(self):
        J, p = menu('etats'); p._demander_suppression(4)
        self.assertEqual(p.popup['titre'], "Supprimer l'état 4 ?"); self.assertEqual(p.popup['sel'], 1)

    def test_les_aides_des_lignes_restent_francaises(self):
        J, p = menu('affichage')
        self.assertIn('Plein écran : fenêtre sans bordure', p._aide_ligne(TP.par_libelle(p, 'Plein écran')))
        J.post.max_msaa = 2; J.reg['msaa'] = 8; self.assertEqual(TP.par_libelle(p, 'Antialiasing')['aide'], 'Limited to x2 by this graphics card')       # (texte à trou : traduit puis rempli, voir Pause._e_affichage)


class Touches(unittest.TestCase):
    def tearDown(self): LG.regler('fr')

    def test_tous_les_noms_de_touches_en_anglais(self):
        LG.regler('en')
        noms = sorted({n for n in dir(K) if n.isupper() and not n.startswith(('MOD_', 'MOTION'))})
        self.assertGreater(len(noms), 100)
        for n in noms:
            fr = RG.nom_touche(n); en = LG.tr(fr)
            self.assertFalse(TL.francais(en), '%s : %r -> %r' % (n, fr, en)); self.assertNotIn('Pavé', en)
            if fr != n and fr in EN_PAUSE.EN: self.assertNotEqual(en, fr)
        self.assertEqual([LG.tr(RG.nom_touche(n)) for n in ('LSHIFT', 'RSHIFT', 'LCTRL', 'RCTRL', 'LALT', 'RALT', 'SPACE', 'RETURN', 'ENTER', 'BACKSPACE', 'DELETE', 'INSERT', 'HOME', 'END', 'PAGEUP', 'PAGEDOWN', 'CAPSLOCK', 'NUM_ADD', 'NUM_SUBTRACT')],
                         ['Left Shift', 'Right Shift', 'Left Ctrl', 'Right Ctrl', 'Left Alt', 'Right Alt', 'Space', 'Enter', 'Numpad Enter', 'Backspace', 'Delete', 'Insert', 'Home', 'End', 'Page Up', 'Page Down', 'Caps Lock', 'Numpad +', 'Numpad -'])

    def test_en_francais_rien_ne_change(self):
        LG.regler('fr')
        for n, att in (('LSHIFT', 'Maj gauche'), ('RETURN', 'Entrée'), ('NUM_3', 'Pavé 3'), ('F1', 'F1'), ('BACKSPACE', 'Retour arrière')): self.assertEqual(LG.tr(RG.nom_touche(n)), att)

    def test_tout_le_pave_numerique_de_pyglet_est_traduit(self):
        for n in dir(K):
            if n.startswith('NUM_'): self.assertIn(RG.nom_touche(n), EN_PAUSE.EN, n)


class Console(unittest.TestCase):
    """Les messages de la console de reglages.py et de pause.py."""
    def tearDown(self): LG.regler('fr')

    def sortie(self, f):
        s = io.StringIO()
        with contextlib.redirect_stdout(s): f()
        return s.getvalue().strip()

    def test_reglages_illisibles(self):
        with tempfile.TemporaryDirectory() as t:
            chemin = os.path.join(t, 'reglages.json')
            with open(chemin, 'w', encoding='utf-8') as f: f.write('{pas du json')
            LG.regler('fr'); fr = self.sortie(lambda: RG.Reglages(chemin))
            LG.regler('en'); en = self.sortie(lambda: RG.Reglages(chemin))
        self.assertTrue(fr.startswith('Reglages illisibles (%s) : valeurs par defaut (' % chemin), fr); self.assertTrue(en.startswith('Unreadable settings (%s): default values (' % chemin), en)

    def test_reglages_non_enregistres(self):
        with tempfile.TemporaryDirectory() as t:
            r = RG.Reglages(os.path.join(t, 'dossier_absent', 'reglages.json'))
            LG.regler('fr'); fr = self.sortie(r.enregistrer)
            LG.regler('en'); en = self.sortie(r.enregistrer)
        self.assertTrue(fr.startswith('Reglages non enregistres : '), fr); self.assertTrue(en.startswith('Settings not saved: '), en)

    def test_police_du_jeu_non_chargee(self):
        """Le fichier de police du jeu existe mais pyglet ne peut pas le charger (ici : refusé exprès) : la console le dit dans la langue de l'outil."""
        add_file = pyglet.font.add_file
        def refuse(*a, **k): raise OSError('police refusee')
        sorties = []
        try:
            pyglet.font.add_file = refuse
            with tempfile.TemporaryDirectory() as t:
                open(os.path.join(t, 'ui_font.otf'), 'wb').close()
                for langue in ('fr', 'en'):
                    J = FauxJeu(); J.args = types.SimpleNamespace(cache=t); p = PA.Pause(J); LG.regler(langue); sorties.append(self.sortie(lambda: p._et('Son', 12.0)))
        finally: pyglet.font.add_file = add_file
        self.assertTrue(sorties[0].startswith('police du jeu non chargee : police refusee'), sorties[0]); self.assertTrue(sorties[1].startswith('game font not loaded: police refusee'), sorties[1])


class Catalogue(unittest.TestCase):
    """Les règles du catalogue (tests/test_langue.py) pour textes_en\\pause.py seul, plus : pas de traduction vide ni identique, une traduction n'est pas elle-même une clé."""
    def test_regles(self):
        for fr, en in EN_PAUSE.EN.items():
            self.assertTrue(en.strip() and en != fr, '%r -> %r' % (fr, en))
            self.assertEqual(TL.TROUS.findall(fr), TL.TROUS.findall(en), fr)
            self.assertEqual((fr[:len(fr) - len(fr.lstrip())], fr[len(fr.rstrip()):]), (en[:len(en) - len(en.lstrip())], en[len(en.rstrip()):]), fr)
            self.assertEqual(fr.count('\n'), en.count('\n'), fr); self.assertFalse(TL.francais(en), '%r -> %r' % (fr, en))
            self.assertNotIn('   ', fr.strip(), 'une cle est UNE phrase d\'aide : %r' % fr); self.assertNotIn('   ', en.strip())

    def test_traduire_deux_fois_ne_change_rien(self):
        """Le menu traduit parfois un texte déjà traduit (aide assemblée, message dont les valeurs sont traduites) : l'anglais ne doit pas être lui-même une clé du catalogue."""
        for fr, en in EN_PAUSE.EN.items(): self.assertNotIn(en, EN_PAUSE.EN, '%r -> %r est aussi une cle' % (fr, en))

    def test_pas_de_doublon_avec_les_autres_fichiers_du_socle(self):
        autres = {}
        for nom, c in TL.catalogue_par_fichier().items():
            if nom != 'pause': autres.update(c)
        self.assertEqual(sorted(set(EN_PAUSE.EN) & set(autres)), [])


class Mutations(Base):
    """Le contrôle de la vérification elle-même : chaque faute introduite à la main est vue par `problemes`."""

    def anglais(self, parties, catalogue=None):
        sauve = LG._catalogue
        try:
            if catalogue is not None: LG._catalogue = catalogue
            return Visite('en', parties)
        finally: LG._catalogue = sauve

    def verifier(self, parties, catalogue=None, cat=None):
        """`problemes` pour ces morceaux du parcours, avec ce catalogue (None : le vrai) ; cat : le catalogue de pause.py selon `problemes`."""
        return problemes(visite('fr', parties), self.anglais(parties, catalogue), self.cat if cat is None else cat)

    @contextlib.contextmanager
    def muter(self, classe, nom, ancien, nouveau):
        """Remplace, le temps du bloc, la méthode `classe.nom` par une copie dont le texte `ancien` est devenu `nouveau` (exécutée avec les globales du module de la classe)."""
        f = getattr(classe, nom); src = textwrap.dedent(inspect.getsource(f))
        self.assertIn(ancien, src, 'la mutation ne porte sur rien : %r' % ancien)
        ns = dict(vars(sys.modules[classe.__module__])); exec(compile(src.replace(ancien, nouveau, 1), '<mutation>', 'exec'), ns)
        setattr(classe, nom, types.FunctionType(ns[nom].__code__, vars(sys.modules[classe.__module__]), nom))          # (avec les globales du module telles qu'elles sont pendant le parcours : l'horloge figée, par exemple)
        try: yield
        finally: setattr(classe, nom, f)

    def sans(self, *cles):
        """Le catalogue du parcours et celui de `problemes` sans ces clés."""
        return {k: v for k, v in LG.catalogue().items() if k not in cles}, {k: v for k, v in self.cat.items() if k not in cles}

    def test_ligne_de_base_sans_probleme(self):
        for parties in (('page_racine',), ('page_commandes',), ('messages',), ('page_etats',)): self.assertEqual(self.verifier(parties), [], parties)

    def test_une_cle_retiree_du_catalogue(self):
        c, c_pause = self.sans('Reprendre')
        pb = self.verifier(('page_racine',), c, c_pause)
        self.assertTrue(any('Reprendre' in x for x in pb), pb)

    def test_une_phrase_d_aide_retiree_du_catalogue(self):
        c, c_pause = self.sans("Langue de l'outil : paramètres, historique, sauvegardes, licence, informations...")
        pb = self.verifier(('page_affichage',), c, c_pause)
        self.assertTrue(any("Langue de l'outil" in x for x in pb), pb)

    def test_un_nom_de_touche_retire_du_catalogue(self):
        c, c_pause = self.sans('Maj gauche')
        pb = self.verifier(('touches',), c, c_pause)
        self.assertTrue(any('Maj gauche' in x for x in pb), pb)

    def test_le_tr_des_aides_retire(self):
        with self.muter(PA.Pause, '_lignes_aide', 'l = tr(l); cur', 'cur'): pb = self.verifier(('page_racine',))
        self.assertTrue(any('aide' in x for x in pb), pb)

    def test_le_tr_de_Touche_n_retire(self):
        with self.muter(PA.Pause, 'dessiner', "self._et(tr('Touche %d') % (c + 1)", "self._et('Touche %d' % (c + 1)"): pb = self.verifier(('page_commandes',))
        self.assertTrue(any('Touche' in x for x in pb), pb)

    def test_le_tr_des_messages_retire(self):
        with self.muter(PA.Pause, '_texte_message', 'return tr(m[3]) % tuple(tr(v) for v in m[4]) if m[4] else tr(m[3])', 'return m[0]'): pb = self.verifier(('messages',))
        self.assertTrue(any('tat' in x or 'touche' in x.lower() for x in pb), pb)

    def test_le_tr_des_valeurs_du_message_retire(self):
        """Le nom de l'action dans « Tab retirée de « Infos à l'écran » » est traduit lui aussi."""
        with self.muter(PA.Pause, '_texte_message', 'tuple(tr(v) for v in m[4])', 'm[4]'): pb = self.verifier(('messages',))
        self.assertTrue(any('removed from' in x for x in pb), pb)

    def test_le_tr_du_titre_de_la_confirmation_retire(self):
        with self.muter(PA.Pause, '_dessiner_popup', "tr(p['modele']) % p['valeurs'] if p.get('modele') else p['titre']", "p['titre']"): pb = self.verifier(('page_etats',))
        self.assertTrue(any("Supprimer l'état" in x for x in pb), pb)

    def test_une_traduction_videe(self):
        c = dict(LG.catalogue(), **{'Résolution': ''})
        pb = self.verifier(('page_affichage',), c, dict(self.cat, **{'Résolution': ''}))
        self.assertTrue(any('vide' in x for x in pb), pb)

    def test_une_traduction_laissee_en_francais(self):
        c = dict(LG.catalogue(), **{'Reprendre': 'Reprendre'})
        pb = self.verifier(('page_racine',), c, dict(self.cat, **{'Reprendre': 'Reprendre'}))
        self.assertTrue(any('identique' in x for x in pb), pb)

    def test_sans_tr_le_francais_ne_change_pas(self):
        """Un menu sans le `tr` des aides rend en français exactement les mêmes textes (le français est la clé)."""
        with self.muter(PA.Pause, '_lignes_aide', 'l = tr(l); cur', 'cur'): f = Visite('fr', ('page_racine', 'page_commandes'))
        self.assertEqual(f.vus, visite('fr', ('page_racine', 'page_commandes')).vus)


if __name__ == '__main__':
    unittest.main(verbosity=1)
