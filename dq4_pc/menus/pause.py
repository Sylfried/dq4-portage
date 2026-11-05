"""Menu Echap : reprendre, etats instantanes (savestates), affichage, son, commandes (vitesses, touches, interface), retour a l'ecran titre.

Pendant que le menu est ouvert le jeu CONTINUE de tourner derriere lui, sur toutes les pages, sans recevoir ni touche ni clic (#178 : aucune pause dans aucun menu ; la scene reste affichee, assombrie). Navigation : fleches ou touches haut / bas / gauche / droite / A / B reglees,
Entree / Espace = valider, Echap / Retour arriere = retour, souris (survol, clic, clic droit ou bouton « retour » en bas a droite de la fenetre = retour, molette, barre de defilement).
Deux modes de selection : au clavier, le curseur dore (fixe) devant la ligne ; a la souris, rien n'est encadre : comme au toucher sur mobile, la plaque (ou le bouton) sous le pointeur s'assombrit et se rallume quand il sort.
Les reglages sont enregistres dans reglages.json. Fenetres noires, curseur dore et bouton retour : ceux des menus du jeu (feuilles MenuTexture et Button)."""
import math, os, sys, time
import numpy as np
import pyglet
from pyglet import gl
from dq4_pc.persistence import settings as RG
from dq4_pc import language as LG
from dq4_pc.language import N_, tr
from dq4_pc.world import hd as HD
from dq4_pc.menus import hud_mobile as HM
from dq4_pc.window import inputs as EN
from dq4_pc.menus import ui_history as UH

SAVESTATE_COUNT = 9                 # emplacements d'etats instantanes (touches 1 a 9)
REPEAT_DELAY, REPEAT_STEP = 0.40, 0.07
# Palette de texte du jeu (MenuPortItemTable : blanc, jaune, rouge, gris) ; fenetres noires cadrees de blanc et boutons dans le style du menu des commandes du jeu mobile (voir hud_mobile.cadre et hud_mobile.plaque)
GOLD = (255, 235, 4, 255); WHITE = (255, 255, 255, 255); GRAY = (128, 128, 128, 255); HELPTEXT = (170, 170, 170, 255); RED = (255, 80, 80, 255)
HEADING = (146, 140, 112, 255); HEADING_RULE = (72, 69, 54)          # intertitres de groupe des listes deroulantes (« Écran tactile », « Dialogues »...) : gris dore terne, plus petits ; l'or (OR) est reserve a la valeur courante
HEADING_SIZE = 0.76                                                   # (fraction de la taille des valeurs)


def heading_style(fs):
    """(taille, couleur) d'un intertitre de groupe d'une liste deroulante : plus petit que les valeurs et d'un gris dore terne, jamais en or (l'or marque la valeur courante)."""
    return fs * HEADING_SIZE, HEADING
YELLOW = GOLD[:3]; LIGHT = (236, 236, 232)
NO_DEFAULT = object()                                  # « pas de valeur par defaut » (None et False sont des valeurs possibles)
BLACK = (0, 0, 0)                                  # fond des fenetres du menu : noir, avec l'opacite des fenetres des autres menus (hud_mobile.GAME_OPACITY, mesuree sur les fenetres du jeu)
CELL_WIDTH, CELL_SPACING = 150.0, 10.0       # menu Commandes : largeur d'une case de touche et ecart entre les deux (a 900 px de haut, multiplies par k)
BAR_WIDTH = 12.0                                 # barre de defilement
CURSOR = (194, 297, 238, 328)                    # curseur dore des menus du jeu dans la feuille MenuTexture (x0, y0, x1, y1)
DPAD = (50, 291, 61, 301)                        # croix rouge du jeu (effacer une touche)
BACK_ICON = (352, 224, 384, 256)               # icone du bouton retour du jeu (case 11 de la rangee d'icones)
WIDTH_SW, HEIGHT_SW = 46.0, 24.0                    # interrupteur Oui / Non : taille a 900 px de haut (multipliee par k)
GAME_SIZE = 1.0                                  # echelle des textes en police du jeu (par rapport aux polices du systeme)
MSAA_CHOICES = (0, 2, 4, 8)
# gestes de la souris sur le terrain (page Commandes, lecture seule : ce ne sont pas des touches) : (geste, effet) ; la camera ne fait que tourner a gauche / a droite et se recentrer (D-233)
MOUSE_GESTURES = ((N_('Clic molette maintenu + déplacement'), N_('Tourne la caméra')),
                 (N_('Clic molette'), N_('Recentre la caméra')))          # (D-238 : textes français, traduits en les dessinant)
# editeur d'interface : noms des fenetres du jeu (fonctions Make_* de MenuPortItemTable ; 'boutons' = boutons et croix de l'ecran, 'msg' = dialogues) et regroupements de la liste « Interface a modifier ».
# Une fenetre du jeu n'y figure que si elle a un maillage a regler (RG.REMOVED_WINDOWS : lancement du jeu, reseau, fenetres sans maillage) ; une fenetre inconnue va dans « Autres ».
WINDOW_NAMES = {'boutons': N_("Boutons et croix de l'écran"), 'bouton_vitesse': N_('Combat : bouton de vitesse'), 'msg': N_('Dialogues (messages)'), 'YesNo': N_('Oui / Non'), 'Chapter': N_('Titre du chapitre'),
                 'RootMenu': N_('Menu principal'), 'LeftCharaList': N_('Liste des personnages'), 'TargetCharaList': N_('Choix du personnage'), 'Money': N_('Argent'), 'Pageing': N_('Flèches de page'),
                 'ItemList': N_('Liste des objets'), 'ItemInfo': N_("Infos de l'objet"), 'OperationItemList': N_('Actions sur les objets'),
                 'Status': N_('Statut du personnage'), 'Chapter2Status': N_('Chapitre 2 : statut'), 'MemberShift': N_("Ordre de l'équipe"), 'MemberShiftButton': N_("Ordre de l'équipe : boutons"),
                 'NameButton': N_('Divers : liste des boutons'), 'BCInfo': N_('Sauvegarde rapide'), 'Senreki': N_('Journal de bord'), 'MonsterEncyclopedia': N_('Bestiaire'),
                 'CityMap': N_('Carte : plan (ville, monde)'), 'WorldLargeMap': N_('Carte : grande carte du monde'), 'MapButton': N_('Carte : boutons Mode et retour'), 'ShopMap': N_('Carte : liste des boutiques'),
                 'BattleUpStatus': N_("Combat : bandeau de l'équipe"), 'BattleRoot': N_('Combat : menu principal'), 'BattleAction': N_('Combat : actions'), 'BattleTarget': N_('Combat : cibles'), 'BattleGo': N_('Combat : en avant'),
                 'BattleIM': N_('Combat : objets et sorts'), 'BattleInfo': N_("Combat : infos de l'équipe"), 'BattleEnemyTarget': N_('Combat : cible ennemie'), 'BattlePartyTarget': N_('Combat : cible alliée'),
                 'BattleChangeButton': N_('Combat : changement'), 'BattleChangeInfo': N_('Combat : infos du changement'),
                 'ShopRoot': N_('Boutique : menu'), 'ShopBuy': N_('Boutique : achat'), 'ShopBuyInfo': N_("Boutique : infos de l'objet"), 'ShopSellItemList': N_('Boutique : vente'), 'ShopSellItemInfo': N_('Boutique : infos de vente'),
                 'TorunekoMiseban': N_('Boutique de Torneko'), 'BankDeposit': N_('Banque : dépôt'), 'BankDraw': N_('Banque : retrait'), 'ChurchRoot': N_('Église : menu'), 'ChurchWork': N_('Église : services'),
                 'Casino_CoinShop': N_('Casino : jetons'), 'Casino_GiftList': N_('Casino : cadeaux'), 'Casino_GiftTarget': N_('Casino : destinataire'), 'Casino_Slot': N_('Casino : machine à sous'), 'Casino_Poker': N_('Casino : poker'),
                 'Casino_FightStadiumSelect': N_('Casino : choix du stade'), 'Casino_FightStadiumBet': N_('Casino : pari du stade'), 'Casino_FightStadiumCoin': N_('Casino : jetons du stade'), 'FightStadiumAbort': N_('Casino : abandon du stade')}
INTERFACE_GROUPS = ((N_("Écran tactile"), ('boutons',)),
                     (N_("Dialogues"), ('msg', 'YesNo', 'Chapter')),
                     (N_("Menu en jeu"), ('RootMenu', 'LeftCharaList', 'TargetCharaList', 'Money', 'Pageing')),
                     (N_("Objets"), ('ItemList', 'ItemInfo', 'OperationItemList')),
                     (N_("Équipe et statut"), ('Status', 'Chapter2Status', 'MemberShift', 'MemberShiftButton')),
                     (N_("Divers"), ('NameButton', 'BCInfo', 'Senreki', 'MonsterEncyclopedia')),
                     (N_("Cartes"), ('CityMap', 'WorldLargeMap', 'MapButton', 'ShopMap')),
                     (N_("Combat"), ('bouton_vitesse', 'BattleUpStatus', 'BattleRoot', 'BattleAction', 'BattleTarget', 'BattleGo', 'BattleIM', 'BattleInfo', 'BattleEnemyTarget', 'BattlePartyTarget', 'BattleChangeButton', 'BattleChangeInfo')),
                     (N_("Boutiques et banque"), ('ShopRoot', 'ShopBuy', 'ShopBuyInfo', 'ShopSellItemList', 'ShopSellItemInfo', 'TorunekoMiseban', 'BankDeposit', 'BankDraw')),
                     (N_("Églises"), ('ChurchRoot', 'ChurchWork')),
                     (N_("Casino"), ('Casino_CoinShop', 'Casino_GiftList', 'Casino_GiftTarget', 'Casino_Slot', 'Casino_Poker', 'Casino_FightStadiumSelect', 'Casino_FightStadiumBet', 'Casino_FightStadiumCoin', 'FightStadiumAbort')))
OWN_INTERFACES = (RG.SCREEN_TARGET, 'msg', RG.SPEED_TARGET)         # interfaces de l'editeur qui ne sont pas des fenetres Make_* du moteur : boutons et croix de l'ecran, dialogues, bouton de vitesse de combat
HEADER = '#'                                                    # valeur d'une liste deroulante qui est un intertitre de groupe (« #Dialogues ») : jamais choisie, sautee par le curseur
WITHOUT_EDITING = RG.REMOVED_WINDOWS
LONG_PRESS_DELAY = float(os.environ.get('DQ_APPUI_LONG', '0.35'))      # panneau de l'editeur : appui maintenu sans bouger (secondes) avant qu'il se souleve ; en dessous, sans bouger, c'est un appui court (replier / deplier)
DOUBLE_CLICK_DELAY = float(os.environ.get('DQ_DOUBLE_CLIC', '0.50'))        # double clic sur la barre de titre : delai par defaut (secondes) entre le DEBUT du premier appui et celui du second, quand le systeme ne le dit pas (defaut de Windows : 500 ms)
RECT_DOUBLE_CLICK = (4, 4)                                       # rectangle du double clic par defaut (pixels, centre sur le premier appui ; defaut de Windows : 4 x 4)


def system_double_click():
    """Reglage de double clic du systeme, relu a chaque appui : (delai en secondes, largeur, hauteur en pixels du rectangle autour du premier appui). Windows : GetDoubleClickTime et SM_CXDOUBLECLK / SM_CYDOUBLECLK (le curseur
    « Vitesse du double-clic » du panneau Souris de Windows) ; la variable d'environnement DQ_DOUBLE_CLIC (secondes) force le delai ; sans Windows, les valeurs par defaut de Windows (0,5 s, 4 x 4)."""
    delay, (w, h) = DOUBLE_CLICK_DELAY, RECT_DOUBLE_CLICK
    if sys.platform == 'win32':
        try:
            import ctypes; u = ctypes.windll.user32
            if not os.environ.get('DQ_DOUBLE_CLIC'): delay = max(0.05, u.GetDoubleClickTime() / 1000.0)
            w, h = max(1, int(u.GetSystemMetrics(36))), max(1, int(u.GetSystemMetrics(37)))
        except Exception: pass
    return delay, w, h

PRESS_TOLERANCE = 8.0                                           # deplacement (pixels) du pointeur, depuis le point d'appui sur la barre de titre du panneau, a partir duquel le panneau se deplace (en dessous : appui court)
SELECTION_BORDER = (255, 235, 130)                               # cadre jaune de l'element choisi dans l'apercu de l'editeur (le meme que celui des boutons de l'ecran : hud_mobile.py)
HIDDEN_WORDS = (N_('Masquée'), N_('Masqué'))                             # etiquette d'un element masque dans l'apercu de l'editeur : feminin (fenetre, croix), masculin (boutons)


class Pause:
    def __init__(self, game):
        self.J = game; self.hist = UH.HistoryView(self); self.opened = False; self.stack = []; self.selected = {}; self.capture = None; self.message = None
        self.zones = []; self.zones_off = []; self.bars = {}; self.zones_val = {}; self.zones_col = 0.0; self.minis = {}; self.rep = None; self.wants_thumbnail = False; self.mini_tex = None; self.confirmed = None
        self.panel_border = None                          # (x0, y0, x1, y1) du cadre dessine a la derniere image (placement des boutons : un clic hors du cadre saisit un bouton)
        self.default_zones = {}; self.zones_mute = {}          # ligne -> (x0, y0, x1, y1) du bouton « valeur par defaut » des curseurs ; du bouton « muet » des lignes de la page Son
        self.dragging = None; self.entry = None            # curseur maintenu par la souris (numero de ligne) ; valeur en cours de saisie [ligne, texte]
        self.open_dropdown = None; self.zones_pop = []          # liste deroulante ouverte [ligne, valeur survolee] ; zones de ses valeurs (x0, y0, x1, y1, numero)
        self.pos_sw = {}; self.t_sw = time.time(); self.dt_sw = 0.0         # interrupteurs : position du bouton (0 = Non, 1 = Oui) par libelle, pour l'animation
        self._pol = None; self._caps = {}                 # familles de la police du jeu (None : pas encore cherchee) ; hauteur des capitales par taille

        self.rep_pos = None                               # (ecran, ligne) sur lesquels la repetition d'une touche maintenue a commence
        self.begin = {}; self.seen_selected = {}; self.barre = None; self.dragging_bar = None      # defilement : premiere ligne visible par ecran, derniere selection vue (la vue la suit quand elle change), barre dessinee, prise du curseur de la barre
        self.zone_ret = None; self.on_back = False; self.zones_eff = {}                      # bouton retour (x0, y0, x1, y1), pointeur dessus ; (ligne, colonne) -> croix « effacer la touche »
        self._pil = {}; self._img = {}                    # feuilles du jeu (PIL) et textures des sprites du menu
        self.mouse_mode = False; self.mouse_pos = None   # selection a la souris (la plaque sous le pointeur s'assombrit, comme au toucher sur mobile) ou au clavier (curseur dore) ; derniere position du pointeur
        self.popup = None; self.zones_popup = []                                          # fenetre modale Oui / Non : {'titre', 'detail', 'oui', 'sel' (0 Oui, 1 Non)} ; zones de ses boutons
        self.folded = False; self.fold_zone = None; self.tt = None                          # editeur d'interface : panneau replie ; barre de titre (plier / deplier) ; ligne survolee depuis (cle, instant) pour l'infobulle
        self.state_action = 'creer'; self.state_delete = None                                  # menu des etats : action choisie (creer, charger, supprimer) ; emplacement dont la suppression est a confirmer
        self.list_bar = None; self.dragging_entries = None; self.entries_top = None; self.entries_cur_seen = None      # liste deroulante : barre de defilement, prise du curseur, premiere valeur visible
        self.target = 'boutons'; self.drag = None; self.rect_preview = None           # editeur d'interface : element modifie ('boutons', 'msg' ou nom Make_* d'une fenetre du jeu) ; deplacement en cours (x, y de depart, decalage de depart)
        self.pan_pos = None; self.pan_pressed = None; self.pan_click_t = 0.0; self.pan_click_pos = None; self.pan_fold_at = None             # editeur d'interface, panneau deplacable : coin haut droit (x, y) apres un deplacement (le temps de la session ; None = position d'origine, calculee d'apres l'interface choisie) ;
        self.list_border = None; self.pan_dim = None                                    # appui en cours sur la barre de titre {t0, x, y, dx, dy, long (souleve : suit le pointeur), double} ; instant du dernier appui court (double clic) ; cadre de la liste deroulante ouverte

    def _label(self, text, size_value, color=WHITE):
        """Etiquette en police du jeu (GMaruGoPro-M, cache/ui_font.otf, enregistree au premier appel) ; a defaut, les polices du systeme."""
        if self._pol is None:
            self._pol = ()
            f = os.path.join(self.J.args.cache, 'ui_font.otf')
            if os.path.exists(f):
                try: pyglet.font.add_file(f); self._pol = ('FOT-GMaruGo Pro', 'FOT-GMaruGo Pro M', 'GMaruGoPro-M')
                except Exception as ex: print('game font not loaded:', ex, flush=True)
        return self.J._lbl(tr(text), size_value * (1.0 if not self._pol else GAME_SIZE), color, self._pol)          # (D-238 : tout texte dessiné par les pages passe par la traduction ; un texte sans traduction reste tel quel)

    # ---- sprites des menus du jeu
    def _sheet(self, name_str):
        """Feuille de texture du jeu (cache/<nom>, PIL RGBA) ; None si elle est absente."""
        f = self._pil.get(name_str)
        if f is None:
            try:
                from PIL import Image
                f = Image.open(os.path.join(self.J.args.cache, name_str)).convert('RGBA')
            except Exception: f = False
            self._pil[name_str] = f
        return f or None

    def _tex_pil(self, im, lookup_key):
        """Texture (filtre lineaire) d'une image PIL RGBA, gardee sous `lookup_key`."""
        t = self._img.get(lookup_key)
        if t is None:
            a = np.asarray(im.convert('RGBA'))
            t = pyglet.image.ImageData(im.width, im.height, 'RGBA', np.ascontiguousarray(a[::-1]).tobytes(), pitch=im.width * 4).get_texture()
            gl.glBindTexture(t.target, t.id); gl.glTexParameteri(t.target, gl.GL_TEXTURE_MIN_FILTER, gl.GL_LINEAR); gl.glTexParameteri(t.target, gl.GL_TEXTURE_MAG_FILTER, gl.GL_LINEAR)
            self._img[lookup_key] = t
        return t

    def _sliced_tex(self, lookup_key, name_str, box):
        """Texture d'un morceau de la feuille `name_str` (boite x0, y0, x1, y1), couleur des pixels transparents propagee d'un pixel (pas de liseré sombre au filtrage) ; None si la feuille manque."""
        t = self._img.get(lookup_key)
        if t is None:
            f = self._sheet(name_str)
            if f is None: return None
            from PIL import Image
            t = self._tex_pil(Image.fromarray(HD._dilate(np.array(f.crop(box)), 1)), lookup_key)
        return t

    @staticmethod
    def _restore_blend():
        """Les formes de pyglet coupent le melange alpha a la fin de leur dessin : on le remet avant une texture."""
        gl.glEnable(gl.GL_BLEND); gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)

    def _pointer_in(self, z):
        """Le pointeur de la souris est-il dans la zone z (x0, y0, x1, y1) ? Seulement en mode souris : au clavier, rien n'est survole."""
        return bool(self.mouse_mode and self.mouse_pos is not None and z is not None and self._inside(z, *self.mouse_pos))

    def _hovered(self, z):
        """Zone survolee et active : comme _pointer_in, sauf sous une fenetre modale (fenetre Oui / Non, liste deroulante ouverte, attente d'une touche) qui garde le survol pour elle."""
        return self.popup is None and self.open_dropdown is None and self.capture is None and self._pointer_in(z)

    def _cursor(self, x, yc, topmost):
        """Curseur dore des menus du jeu (pointe vers la droite), de `topmost` pixels de haut, a gauche en x, centre verticalement en yc ; il reste fixe."""
        t = self._sliced_tex('curseur', 'ui_MenuTexture.png', CURSOR)
        dx = 0.0
        if t is None:
            pyglet.shapes.Triangle(x, yc + topmost / 2, x, yc - topmost / 2, x + topmost * 0.7, yc, color=YELLOW).draw(); return
        e = topmost / float(CURSOR[3] - CURSOR[1]); self._restore_blend(); t.blit(x + dx, yc - topmost / 2, width=(CURSOR[2] - CURSOR[0]) * e, height=topmost)

    def _back_button(self, x, y, w, h, pushed):
        """Bouton retour des menus du jeu : fenetre-bouton de la feuille Button (neuf morceaux, 32 px d'angle reduits de moitie, version enfoncee a 96 px a droite) et son icone fleche de retour."""
        from PIL import Image
        lookup_key = ('retour', int(w), int(h), bool(pushed)); t = self._img.get(lookup_key); w, h = int(round(w)), int(round(h))
        if t is None:
            f = self._sheet('ui_Button.png')
            if f is not None:
                src = f.crop((96 if pushed else 0, 0, 96 + (96 if pushed else 0), 96)); c = max(2, int(round(w / 4.0)))
                im = Image.new('RGBA', (w, h)); xs = (0, c, w - c, w); ys = (0, c, h - c, h); sx = (0, 32, 64, 96)
                for i in range(3):
                    for j in range(3): im.paste(src.crop((sx[i], sx[j], sx[i + 1], sx[j + 1])).resize((xs[i + 1] - xs[i], ys[j + 1] - ys[j]), Image.LANCZOS), (xs[i], ys[j]))
                t = self._tex_pil(im, lookup_key)
        ic = self._sliced_tex('ic_retour', 'ui_MenuTexture.png', BACK_ICON)
        self._restore_blend()
        if t is not None: t.blit(x, y)
        else: self._plate(x, y, w, h, w / 64.0, pushed)
        if ic is not None:
            e = 62.4 / 64.0 * w; ic.blit(x + (w - e) / 2, y + (h - e) / 2, width=e, height=e)

    # ---- ouverture / fermeture
    FROZEN_PAGES = ()                                 # pages qui arretent le jeu derriere elles : AUCUNE (#178, D-229 : « il ne faut aucune pause dans aucun menu » ; l'historique et la question « Quitter » arretaient le jeu jusque-la). Le jeu tourne derriere toutes les pages, sans touche ni clic (voir Window.tick)

    def freezes_game(self):
        """Le jeu est-il arrete derriere le menu ? Non, sur aucune page (racine « Paramètres », reglages, historique, question « Quitter ») : le jeu tourne, il ne recoit aucune entree. Reste vrai seulement pour une page ajoutee a FROZEN_PAGES (vide : voir la regle ci-dessus)."""
        return self.opened and self.screen_page in self.FROZEN_PAGES

    def open_menu(self, page=None):
        if self.opened: return
        self.opened = True; self.stack = ['racine']; self.selected = {}; self.capture = None; self.message = None; self.confirmed = None; self.popup = None; self.folded = False; self.tt = None; self.begin = {}; self.seen_selected = {}; self.dragging_bar = None
        self.wants_thumbnail = True; self.minis = {}; self.rep = None; self.dragging = None; self.entry = None; self.open_dropdown = None
        self.mouse_mode = False; self.mouse_pos = getattr(self.J, 'mouse', None); self.drag = None; self.pan_pressed = None; self.pan_fold_at = None; self.pan_click_pos = None
        self._guard().keyboard(self.mouse_pos)                    # la selection est au clavier tant que le pointeur ne s'est pas vraiment deplace (ecart cumule depuis son point d'ouverture : entrees.MouseGuard)
        if page: self.stack = [page]; self.selected[page] = 2           # ouvre directement cette page (question de sortie : « Non » preselectionne, « Non » ou Echap ferment tout)
        self.J.pause_game(True)
        if page == 'historique': self.hist.enter()

    def shutdown(self):
        if not self.opened: return
        self.opened = False; self.capture = None; self.popup = None; self.dragging = None; self.entry = None; self.open_dropdown = None; self.J.reg.store(); self.J.pause_game(False)
        if self.mini_tex is not None:
            try: self.mini_tex.delete()
            except Exception: pass
            self.mini_tex = None

    @property
    def screen_page(self): return self.stack[-1]

    def back(self):
        if self.screen_page == 'interface': self.J.reg.store(); self.drag = None; self.pan_pressed = None; self.pan_fold_at = None; self.pan_click_pos = None                # fin de l'edition de l'interface
        if len(self.stack) > 1: self.stack.pop()
        else: self.shutdown()

    # ---- entrees des ecrans : liste de dicts {'t': 'act'|'choix'|'curs'|'touche'|'sep', 'l': libelle, 'v': valeur affichee, 'ok', 'moins', 'plus', 'off'}
    PAGE_ENTRIES = {'racine': '_entries_root', 'affichage': '_entries_display', 'interface': '_entries_interface', 'son': '_entries_sound', 'modifications': '_entries_changes', 'commandes': '_entries_commands',
                    'etats': '_entries_savestates', 'quitter': '_entries_quit', 'historique': '_entries_history'}      # identifiant de page (chaine) -> methode qui donne ses lignes
    def _entries(self):
        return getattr(self, self.PAGE_ENTRIES[self.screen_page])()

    def _entries_history(self): return []                                     # (page dessinee par ui_history.HistoryView : aucune ligne de menu)

    def _go(self, name_str):
        def va():
            self.stack.append(name_str)
            if name_str == 'quitter': self.selected[name_str] = 2        # « Non » preselectionne
        return va

    def _entries_root(self):
        return [dict(t='act', l='Reprendre', ok=self.shutdown),
                dict(t='act', l='Historique', ok=lambda: (self.hist.enter(), self._go('historique')()), sous=True, off=lambda: not getattr(self.J, 'history_possible', lambda: True)(),
                     aide="Disponible seulement quand vous avez la main sur votre personnage : ni pendant un combat, ni pendant un dialogue, une scène ou un événement du jeu, ni dans un menu du jeu"),
                dict(t='act', l='États', ok=self._go('etats'), sous=True),
                dict(t='act', l='Affichage', ok=self._go('affichage'), sous=True),
                dict(t='act', l='Son', ok=self._go('son'), sous=True),
                dict(t='act', l='Commandes', ok=self._go('commandes'), sous=True),
                dict(t='act', l='Modifications', ok=self._go('modifications'), sous=True),
                dict(t='act', l="Revenir à l'écran titre", ok=self._return_to_title, off=lambda: not getattr(self.J, 'back_to_title_possible', lambda: True)(),
                     aide="Disponible en ville et sur la carte du monde seulement : la boîte du jeu (Oui / Non) n'est prévue que là")]          # (le menu se ferme, le jeu ouvre sa boite Oui / Non : le seul chemin de retour au titre du jeu ; la question « quitter l'application » n'est posee que par le menu de depart, page 'quitter')

    def _choice(self, label, value_list, get, set_, off=False, default=NO_DEFAULT, restore_default=None, is_default=None):
        """Entree a valeurs : Oui / Non = interrupteur (valider ou cliquer le bascule ; gauche = Non, droite = Oui) ; tout autre choix, meme a deux valeurs = liste deroulante
        (valider ou cliquer l'ouvre ; gauche / droite passent a la valeur precedente / suivante). `off` : la ligne ne peut pas etre modifiee dans l'etat courant (voir _inactif : grisee, ni choisie ni survolee ni cliquee).
        `default` : valeur d'origine du reglage (bouton rond « valeur par defaut » a droite de la ligne, Suppr / Debut) ; `restore_default` / `is_default` : a la place, pour un reglage qui se rend au jeu (fonction qui le remet, fonction qui dit s'il l'est)."""
        sw = len(value_list) == 2 and all(isinstance(v, bool) for v in value_list)
        def step(d):
            i = (value_list.index(get()) + d) % len(value_list) if get() in value_list else 0
            i = self._outside_header(value_list, i, d)
            set_(value_list[i])
        def fix_value(x):
            if get() != x: set_(x)
        if sw: minus, plus, ok = (lambda: fix_value(False)), (lambda: fix_value(True)), (lambda: set_(not get()))
        else: minus, plus, ok = (lambda: step(-1)), (lambda: step(1)), (lambda: step(1))
        d = dict(t='choix', l=label, vals=value_list, v=lambda: self._value_name(label, get()), moins=minus, plus=plus, ok=ok, off=off, get=get, set=set_, sw=sw, liste=not sw)
        if restore_default is not None: d['defaut'] = restore_default; d['est_defaut'] = is_default or (lambda: False)
        elif default is not NO_DEFAULT: d['defaut'] = lambda: fix_value(default); d['est_defaut'] = lambda: get() == default
        return d

    def _values(self, entry): return entry['vals']

    @staticmethod
    def _inactive(entry):
        """La ligne ne peut pas etre modifiee dans l'etat courant (`off` : un booleen, ou une fonction relue a chaque appel ; les entrees sont de toute facon refaites a chaque image : une ligne grisee par une autre valeur
        redevient active des que cette valeur change). Une ligne inactive est grisee en entier (libelle, valeur, fleche, bouton rond, case) ; elle n'est ni choisie (le curseur dore et les fleches la sautent), ni survolee
        (pas de plaque assombrie), ni cliquee, ni validee, ni reglee (gauche / droite, Suppr, Debut) ; seule son infobulle (`helptext`, si elle en a une) reste. Valable pour tous les types de lignes de toutes les pages."""
        o = entry.get('off'); return bool(o() if callable(o) else o)

    def _active(self, entry):
        """Ligne que le curseur peut choisir : ni intertitre (ou ligne d'information), ni ligne inactive."""
        return entry['t'] != 'sep' and not self._inactive(entry)

    @staticmethod
    def _header(v):
        """Vrai si la valeur d'une liste deroulante est un intertitre de groupe (« #Dialogues »)."""
        return isinstance(v, str) and v[:1] == HEADER

    def _outside_header(self, vals, i, d):
        """Indice de la premiere valeur qui n'est pas un intertitre, a partir de i dans le sens de d."""
        n = len(vals)
        for _ in range(n):
            if not self._header(vals[i]): break
            i = (i + (1 if d >= 0 else -1)) % n
        return i

    def _value_name(self, label, v):
        if label == 'Interface à modifier': return self.target_name(v)
        n = self.names.get(label, {}).get(v)
        if n is not None: return n
        if isinstance(v, bool): return N_('Oui') if v else N_('Non')
        return '%d x %d' % v if isinstance(v, tuple) else str(v)

    def _curs(self, label, get, apply, minimum, maximum, step, step_f, fmt, mult=1.0, default=None):
        """Curseur numerique de `minimum` a `maximum` (valeurs arrondies a `step`, fleches : `step_f`). Cliquer sur la valeur ou valider permet de la saisir au clavier : `mult` = facteur entre la valeur
        interne et celle qui est affichee et saisie (100 pour des pourcentages). `default` : valeur d'origine du reglage (bouton « valeur par defaut » a gauche du curseur, touche Suppr)."""
        def pose(v): apply(min(maximum, max(minimum, round(round(v / step) * step, 4))))
        d = dict(t='curs', l=label, v=lambda: fmt(get()), frac=lambda: (get() - minimum) / (maximum - minimum), moins=lambda: pose(get() - step_f), plus=lambda: pose(get() + step_f),
                 fixe=lambda f: pose(minimum + f * (maximum - minimum)), saisie=lambda x: pose(x / mult), raw_value=lambda: ('%g' % round(get() * mult, 2)))
        if default is not None: d['defaut'] = lambda: pose(default); d['est_defaut'] = lambda: abs(get() - default) < step / 2
        return d

    names = {
        'Langue': {'systeme': N_('Système'), 'en': N_('Anglais'), 'fr': N_('Français')},
        'Shader': {0: N_('Aucun'), 1: 'EPX x8', 4: 'Pixel perfect'},
        'Antialiasing': {0: N_('Aucun'), 2: 'x2', 4: 'x4', 8: 'x8'},
        'Suréchantillonnage': {1.0: N_('Aucun'), 1.5: N_('x1,5'), 2.0: 'x2'},
        'Action': {'creer': N_('Créer un état'), 'charger': N_('Charger un état'), 'supprimer': N_('Supprimer un état')},
    }
    names['Vitesse du texte'] = {0.5: N_('Très lent'), 1.0: N_('Lent'), 2.0: N_('Assez lent'), 4.0: N_('Normal'), 8.0: N_('Rapide'), 16.0: N_('Très rapide'), 4000.0: N_('Instantané')}      # (D-238 : noms français, traduits en les dessinant : `_value_name` rend des donnees)
    names['Vitesse de combat'] = RG.BATTLE_SPEED_NAMES                                                    # Manuel, Normal, Rapide, Très rapide (jamais x1, x2, x3)
    for lib in ('Vitesse de marche', 'Vitesse de caméra'): names[lib] = {v: 'x%d' % v for v in RG.SPEEDS_X}
    del lib

    def _entries_display(self):
        J, R = self.J, self.J.reg
        def set_(k, f=None):
            def s(v):
                R[k] = v
                if f: f(v)                 # (les reglages sont enregistres a la fermeture du menu)
            return s
        lang = self._choice('Langue', list(LG.CHOICES), lambda: R['langue'], set_('langue', LG.select_language), default=RG.DEFAULT['langue'])          # (D-238 : au-dessus de « Plein écran » ; s'applique tout de suite)
        lang['aide'] = "Langue de l'outil : paramètres, historique, sauvegardes, licence, informations...   Système : français si Windows est en français (quelle que soit la variante), sinon anglais   Les textes du jeu ne changent pas"
        win = self._choice('Plein écran', [False, True], lambda: J.is_fullscreen, J.set_full_screen, default=False)          # (interrupteur : l'ancien reglage d'avant la #42 ; F11 et Alt + Entree font la meme chose)
        win['aide'] = "Plein écran : fenêtre sans bordure à la résolution de l'écran où se trouve la fenêtre (l'affichage de l'écran ne change pas)   F11 ou Alt + Entrée : passe du plein écran à la fenêtre et inversement"
        res = self._choice('Résolution', J.resolutions(), J.current_resolution, lambda v: (J.set_resolution(v), R.__setitem__('resolution', list(v))), off=J.is_fullscreen, default=tuple(RG.DEFAULT['resolution']))          # (plein ecran : ligne inactive, relue a chaque image : voir _inactif)
        res['aide'] = "Fenêtré : taille de la fenêtre   Plein écran : sans effet, la fenêtre prend la résolution de l'écran"
        msaa = self._choice('Antialiasing', list(MSAA_CHOICES), lambda: R['msaa'], set_('msaa'), default=RG.DEFAULT['msaa'])
        if J.post.max_msaa is not None and R['msaa'] > J.post.max_msaa: msaa['aide'] = tr('Limité à x%d par cette carte graphique') % J.post.max_msaa          # (ancienne note rouge : plus qu'une infobulle)
        return [lang, win, res,
                self._curs('Netteté', lambda: R['nettete'], lambda v: R.__setitem__('nettete', v), 0.0, 1.0, 0.05, 0.1, lambda v: '%d %%' % round(v * 100), 100.0, default=RG.DEFAULT['nettete']),
                self._choice('Shader', list(RG.MODES_SPRITES), lambda: J.mode, set_('mode_sprites', J.set_mode), default=RG.DEFAULT['mode_sprites']),
                self._curs('Effet de vignetage', lambda: R['vignette'], lambda v: R.__setitem__('vignette', v), 0.0, 1.0, 0.01, 0.05, lambda v: '%d %%' % round(v * 100), 100.0, default=RG.DEFAULT['vignette']),
                msaa,
                self._choice('Suréchantillonnage', [1.0, 1.5, 2.0], lambda: R['echelle_rendu'], set_('echelle_rendu'), default=RG.DEFAULT['echelle_rendu']),
                self._curs('Luminosité', lambda: R['luminosite'], lambda v: R.__setitem__('luminosite', v), 0.5, 1.5, 0.05, 0.1, lambda v: '%d %%' % round(v * 100), 100.0, default=RG.DEFAULT['luminosite']),
                dict(t='act', l='Interface', ok=self._go('interface'), sous=True)]          # (editeur de l'interface a l'ecran : boutons, dialogues, fenetres du jeu)

    # ---- editeur d'interface : boutons de l'ecran, fenetre de dialogue et fenetres du jeu (taille, position, affichage)
    def targets(self):
        """Valeurs de la liste « Interface a modifier » : les elements modifiables par groupe (INTERFACE_GROUPS), chaque groupe precede de son intertitre (« #Dialogues ») ; seules les fenetres du jeu qui ont une mise en page y figurent."""
        names = self.J.window_names(); out = []; seen = set()
        for title_screen, ids in INTERFACE_GROUPS:
            l = [i for i in ids if i in OWN_INTERFACES or i in names]; seen.update(ids)
            if l: out += [HEADER + title_screen] + l
        remainder = sorted((n for n in names if n not in seen and n not in RG.REMOVED_WINDOWS), key=lambda n: n.lower())
        return out + ([HEADER + N_('Autres')] + remainder if remainder else [])

    def target_name(self, c):
        return c[len(HEADER):] if self._header(c) else WINDOW_NAMES.get(c, c)

    def _ov(self):
        """[taille, decalage x, decalage y] de l'element choisi (fenetre du jeu)."""
        return self.J.reg['interface_fenetres'].get(self.target) or list(RG.default_window(self.target))

    def _set_ov(self, i, v):
        d = dict(self.J.reg['interface_fenetres']); o = list(self._ov()); o[i] = v
        if self.target not in RG.DEFAULT['interface_fenetres'] and all(abs(a - b) < 1e-6 for a, b in zip(o, RG.DEFAULT_WINDOW)): d.pop(self.target, None)          # (une fenetre qui a une taille par defaut propre garde son entree, meme a 100 %)
        else: d[self.target] = [round(o[0], 4), round(o[1], 4), round(o[2], 4)]
        self.J.reg['interface_fenetres'] = d

    def _set_target(self, v):
        """Interface a modifier choisie : pour les dialogues, un nouveau message d'essai au hasard."""
        if v != self.target and v == 'msg': self.J.new_sample()
        self.target = v

    def _visible(self, c):
        """L'interface c est-elle affichee a l'ecran ? Boutons et croix : reglage 'boutons' ; fenetre du jeu : absente de la liste des interfaces masquees. Chaque interface a son propre reglage."""
        if c == RG.SPEED_TARGET: return bool(self.J.reg['bouton_vitesse'])
        return bool(self.J.reg['boutons']) if c == RG.SCREEN_TARGET else c not in self.J.reg['interface_masquees']

    def _set_visible(self, c, v):
        R = self.J.reg
        if c == RG.SCREEN_TARGET: R['boutons'] = v; return
        if c == RG.SPEED_TARGET: R['bouton_vitesse'] = v; return
        l = [n for n in R['interface_masquees'] if n != c]
        if not v: l.append(c)
        R['interface_masquees'] = l

    def _entries_interface(self):
        """Page Interface : d'abord l'interface a modifier (liste par groupes), puis son affichage (propre a chaque interface), puis ses reglages."""
        R = self.J.reg; c = self.target
        e = [self._choice('Interface à modifier', self.targets(), lambda: self.target, self._set_target),
             self._choice("Afficher cette interface à l'écran", [True, False], lambda: self._visible(self.target), lambda v: self._set_visible(self.target, v), default=True)]
        if c == RG.SCREEN_TARGET:
            e.append(self._curs('Taille des boutons', lambda: R['boutons_taille'], lambda v: R.__setitem__('boutons_taille', v), 0.5, 2.0, 0.05, 0.1, lambda v: '%d %%' % round(v * 100), 100.0, default=RG.DEFAULT['boutons_taille']))
            e.append(self._choice('Afficher la croix', [True, False], lambda: R['croix'], lambda v: R.__setitem__('croix', v), default=RG.DEFAULT['croix']))
            e.append(self._curs('Taille de la croix', lambda: R['croix_taille'], lambda v: R.__setitem__('croix_taille', v), 0.5, 2.0, 0.05, 0.1, lambda v: '%d %%' % round(v * 100), 100.0, default=RG.DEFAULT['croix_taille']))
        elif c == RG.SPEED_TARGET:                                                   # bouton de vitesse de combat : sa taille ; sa position se regle en le glissant (ou « Replacer sous la boîte »)
            e.append(self._curs('Taille du bouton', lambda: R['bouton_vitesse_taille'], lambda v: R.__setitem__('bouton_vitesse_taille', v), 0.5, 2.0, 0.05, 0.1, lambda v: '%d %%' % round(v * 100), 100.0, default=RG.DEFAULT['bouton_vitesse_taille']))
            if HM.speed_anchor(): e.append(dict(t='act', l='Replacer sous la boîte de combat', ok=lambda: R.__setitem__('bouton_vitesse_pos', []), aide="Le bouton revient collé au coin bas gauche de la boîte du bas (position d'origine) ; glisse-le pour le placer ailleurs"))
            else: e.append(dict(t='act', l="Replacer sur le bord gauche", ok=lambda: R.__setitem__('bouton_vitesse_pos', []), aide="Le bouton revient sur le bord gauche de l'écran (position d'origine) ; glisse-le pour le placer ailleurs"))
        else:
            e += [self._curs('Taille', lambda: self._ov()[0], lambda v: self._set_ov(0, v), 0.5, 2.0, 0.05, 0.1, lambda v: '%d %%' % round(v * 100), 100.0, default=RG.default_window(self.target)[0]),
                  self._curs('Position horizontale', lambda: self._ov()[1], lambda v: self._set_ov(1, v), -0.5, 0.5, 0.01, 0.05, lambda v: '%+d %%' % round(v * 100), 100.0, default=RG.default_window(self.target)[1]),
                  self._curs('Position verticale', lambda: self._ov()[2], lambda v: self._set_ov(2, v), -0.5, 0.5, 0.01, 0.05, lambda v: '%+d %%' % round(v * 100), 100.0, default=RG.default_window(self.target)[2])]
        e += [self._choice('Aimantation à la grille', [True, False], lambda: R['boutons_aimant'], lambda v: R.__setitem__('boutons_aimant', v), default=RG.DEFAULT['boutons_aimant']),            # (pour toutes les interfaces)
              self._choice('Afficher la grille', [True, False], lambda: R['grille_edition'], lambda v: R.__setitem__('grille_edition', v), default=RG.DEFAULT['grille_edition'])]
        this_ = dict(t='act', l='Rétablir cette interface', ok=self._reset_this)
        this_['aide'] = ("Remet les boutons et la croix comme dans le jeu : affichage, tailles et positions   Les fenêtres du jeu et le bouton de vitesse de combat ne changent pas" if c == RG.SCREEN_TARGET
                         else "Remet le bouton de vitesse de combat comme dans le jeu : affichage, taille et position   Les autres interfaces ne changent pas" if c == RG.SPEED_TARGET
                         else "Remet cette fenêtre comme dans le jeu : affichage, taille et position   Les autres interfaces ne changent pas")
        all_entry = dict(t='act', l='Rétablir toutes les interfaces', ok=self._reset_all, aide="Remet toutes les interfaces comme dans le jeu, ainsi que la grille, l'aimantation et la place de ce panneau")
        e += [this_, all_entry, dict(t='act', l='Terminer', ok=self.back)]
        return e

    def _reset_this(self):
        """« Rétablir cette interface » : l'interface choisie revient entièrement à son état d'origine (RG.Settings.reset_interface : position, taille, affichage et toutes ses options, et elle seule).
        Rien d'autre à faire : l'aperçu et le jeu relisent les réglages à chaque image."""
        self.J.reg.reset_interface(self.target)

    def _reset_all(self):
        """« Rétablir toutes les interfaces » : toutes les interfaces et les options de l'éditeur (grille, aimantation) à leur défaut (RG.Settings.reset_interfaces), et le panneau reprend sa place d'origine."""
        self.J.reg.reset_interfaces(); self.pan_pos = None

    def _set_sound(self, lookup_key, category=None):
        """Reglage de son (interrupteur ou volume) : enregistre la valeur, l'applique tout de suite aux sons en cours, et pour un volume fait entendre un bruitage d'essai (la musique, elle, joue pendant la page)."""
        def place(v):
            self.J.reg[lookup_key] = v; self.J.apply_mix()
            if category and not isinstance(v, bool): self.J.preview_sound(category)
        return place

    def _sound_line(self, lib, vol_key, category, active, helptext):
        """Ligne de la page Son : le nom du son, sa barre de volume (et sa valeur), le bouton muet (`active` = (lire, ecrire) l'interrupteur du son), le bouton « par defaut » (volume d'origine et son remis).
        Clavier : haut / bas change de ligne, gauche / droite regle le volume, Entree coupe ou remet le son, Suppr ou Debut remet la ligne par defaut."""
        R = self.J.reg; read, write = active; place = self._set_sound(vol_key, category); default = RG.DEFAULT[vol_key]
        d = self._curs(lib, lambda: R[vol_key], place, 0.0, 1.0, 0.01, 0.05, lambda v: '%d %%' % round(v * 100), 100.0)
        def do_toggle():
            write(not read()); self.J.apply_mix()
            if read(): self.J.preview_sound(category)                                                 # (le son revient : on l'entend)
        def reset():
            write(True); place(default)                                                       # volume d'origine ET son remis
        d.update(actif=read, ok=do_toggle, defaut=reset, est_defaut=lambda: abs(R[vol_key] - default) < 0.005 and read(), aide=helptext)
        return d

    def _entries_sound(self):
        """Une ligne par son (son.CATEGORIES, plus le son en general) : nom | barre de volume | bouton muet | bouton « par defaut » ; plus de sections."""
        J, R = self.J, self.J.reg
        def lookup_key(c): return (lambda: R[c]), self._set_sound(c)
        gen = (lambda: J.sound.active, lambda v: (J.set_sound(v), R.__setitem__('son', v)))
        return [self._sound_line('Général', 'volume_general', 'general', gen, 'Tout le son du jeu : multiplie les autres volumes (et se combine avec le volume réglé dans la fenêtre Paramètres du jeu)   Le son reprend ici pour que tu entendes tes réglages ; le jeu, lui, reste en pause'),
                self._sound_line('Musique', 'volume_musique', 'musique', lookup_key('musique_active'), 'Musique de fond des cartes, villes et combats   Coupée, elle continue en silence et reprend là où elle en est   Le volume change la musique en cours tout de suite'),
                self._sound_line('Jingles et fanfares', 'volume_jingles', 'jingles', lookup_key('jingles_actifs'), 'Morceaux courts joués une seule fois (le reste de la musique est réglé au-dessus)   Le volume se fait entendre à la prochaine fanfare'),
                self._sound_line('Bruitages', 'volume_bruitages', 'effets', lookup_key('bruitages_actifs'), "Effets sonores du jeu : combats, sorts, objets, pas...   Sans les sons de l'interface (ligne du dessous)   Un bruitage d'essai est joué quand tu changes le volume"),
                self._sound_line('Interface', 'volume_interface', 'interface', lookup_key('interface_active'), "Bip des pages de message, validation des menus et des boutons   Un son de bouton est joué quand tu changes le volume")]

    def _text_scroll(self):
        """Section « Défilement du texte » de la page Commandes (juste sous la section Vitesses ; elle etait la page « Vitesse de defilement du texte » du menu racine) : « Vitesse du texte » (vitesse d'ecriture des dialogues),
        puis « Vitesse de combat » (Manuel, Normal, Rapide, Tres rapide : horloge du moteur pendant les combats et defilement des messages de combat)."""
        J, R = self.J, self.J.reg
        vt = self._choice('Vitesse du texte', list(RG.TEXT_SPEEDS), lambda: R['vitesse_texte'], lambda v: (R.__setitem__('vitesse_texte', v), J.apply_text()), default=RG.DEFAULT['vitesse_texte'])
        vt['aide'] = 'Vitesse d\'écriture des dialogues (lettres par image du jeu)   « Normal » : comme dans le jeu d\'origine'
        cb = self._choice('Vitesse de combat', list(RG.BATTLE_SPEEDS), lambda: R['vitesse_combat'], J.set_battle_speed, default=RG.DEFAULT['vitesse_combat'])
        cb['aide'] = "Combats seulement : les animations s'enchaînent sans temps mort (le nombre de dégâts apparaît vite après le coup) ; Rapide, Très rapide : animations, déplacements et messages 2 ou 3 fois plus rapides   Manuel : vitesse normale, on passe chaque message avec Entrée, Espace ou un clic   La musique et les bruitages gardent leur vitesse   Se règle aussi en plein combat (touche « Changer la vitesse en combat », bouton à l'écran)"
        return [dict(t='sep', l='Défilement du texte'), vt, cb]

    def _entries_changes(self):
        """Page « Modifications » (ex-« Jeu »), juste sous « Commandes » dans le menu racine : les modificateurs des regles du jeu, desactives par defaut (= comme le jeu d'origine) ; pour l'instant PV et PM restaures a chaque niveau gagne."""
        J, R = self.J, self.J.reg
        sn = self._choice('PV et PM restaurés au niveau supérieur', [True, False], lambda: R['soin_niveau'], lambda v: (R.__setitem__('soin_niveau', v), J.apply_game()), default=RG.DEFAULT['soin_niveau'])
        sn['aide'] = "Quand un personnage gagne un niveau, il retrouve tous ses PV et tous ses PM (au maximum qu'il vient d'atteindre)   Non : comme le jeu d'origine, la montée de niveau ne soigne pas"
        return [sn]

    def _key_row(self, action):
        """Ligne d'une action au clavier : deux cases (touche principale, secondaire) ; Suppr efface la case choisie, le bouton rond (ou Debut) remet les touches d'origine."""
        R = self.J.reg
        def default():
            for a in R.reset_to_default(action): self._info(N_("Une touche d'origine est retirée de « %s »."), False, dict(RG.ACTIONS)[a])
            R.store()
        return dict(t='touche', l=dict(RG.ACTIONS)[action], act=action, v=[RG.key_name(n) for n in R['touches'][action]], defaut=default, est_defaut=lambda: R.is_default_binding(action))

    def _entries_commands(self):
        """Sections (intertitres) : deplacement (touches), « Camera » (touches gauche / droite, souris, sens, vitesse de camera ; un seul groupe depuis D-237), vitesses (marche, accelerateur : choix x1 a x4 ; touche et multiplicateur de l'accelerateur : curseur ; puis la touche « Changer la vitesse en combat »), defilement du texte (« Vitesse du texte » et « Vitesse de combat » : voir _text_scroll), actions du jeu, autres (touche speciale, infos) ; puis le retablissement des touches."""
        R = self.J.reg; T = self._key_row
        def speed_choice(lib, lookup_key, helptext, f=None):
            d = self._choice(lib, list(RG.SPEEDS_X), lambda: R[lookup_key], lambda v: (R.__setitem__(lookup_key, v), f(v) if f else None), default=RG.DEFAULT[lookup_key]); d['aide'] = helptext; return d
        def speed_accel_cursor(lib, lookup_key, minimum, maximum):
            return self._curs(lib, lambda: R[lookup_key], lambda v: R.__setitem__(lookup_key, v), minimum, maximum, 0.05, 0.1, lambda v: 'x%.2f' % v, 1.0, default=RG.DEFAULT[lookup_key])
        def inverse(lib, lookup_key, helptext):
            d = self._choice(lib, [False, True], lambda: R[lookup_key], lambda v: R.__setitem__(lookup_key, v), default=RG.DEFAULT[lookup_key]); d['aide'] = helptext; return d
        edit = T('modif'); edit['aide'] = "Avec un chiffre : charge un état   Avec Maj : annule le dernier chargement d'état"
        accel = T('accel'); accel['aide'] = "Maintenue : accélère la marche (réglage « Multiplicateur de l'accélérateur »)   Sans effet en combat   " + self.KEY_HELPTEXT
        info = T('infos'); info['aide'] = "Affiche ou masque, en haut à droite de l'écran, le lieu, les réglages d'affichage, le son et les performances   " + self.KEY_HELPTEXT
        speed_accel = speed_accel_cursor("Multiplicateur de l'accélérateur", 'vitesse_accel', 1.0, 2.0); speed_accel['aide'] = "Multiplie la vitesse de marche tant que la touche d'accélérateur est tenue   Rencontres aléatoires et arrivée de la nuit : (1 + x) / 2 fois plus vite (x2 : 1,5 fois ; x1,5 : 1,25 fois)   Les combats ne l'utilisent pas : ils ont leur propre vitesse"
        key_battle = T('vit_combat'); key_battle['aide'] = "Passe de Manuel à Normal, Rapide, Très rapide, puis revient à Manuel   Marche aussi en plein combat (le réglage est dans la section Défilement du texte)   " + self.KEY_HELPTEXT
        return [dict(t='sep', l='Déplacement'),
                T('haut'), T('bas'), T('gauche'), T('droite'),
                dict(t='sep', l='Caméra'),
                *[dict(T(a), aide="Tourne la caméra autour du héros (villes, donjons et tours)   Les deux flèches ensemble : recentre la caméra (animation)   Souris : clic molette maintenu + déplacement = tourne la caméra   Clic molette : recentre la caméra   Dans un menu ou un message, ces flèches sont des directions   " + self.KEY_HELPTEXT) for a in ('cam_gauche', 'cam_droite')],
                inverse('Inverser gauche / droite', 'camera_inverser_gd', "Caméra déplacée à la souris (clic molette maintenu + déplacement) : inverse le sens gauche / droite   Non : glisser vers la droite tourne comme la flèche droite   Les flèches du clavier ne changent pas"),
                *[dict(t='sep', l=g, v=e) for g, e in MOUSE_GESTURES],          # (lecture seule : lignes d'information, ni choisies ni cliquables)
                speed_choice('Vitesse de caméra', 'vitesse_camera', 'Rotation de la caméra aux flèches gauche / droite, et recentrage : x1 à x4   La touche d\'accélérateur n\'y change rien'),
                dict(t='sep', l='Vitesses'),
                speed_choice('Vitesse de marche', 'vitesse_marche', 'Vitesse du héros et du jeu quand on marche : x1 comme le jeu, jusqu\'à x4 (les menus et les messages gardent leur vitesse ; les combats ont leur propre vitesse)   Rencontres aléatoires par seconde et arrivée de la nuit sur la carte du monde : (1 + x) / 2 fois plus (x2 : 1,5 fois, x4 : 2,5 fois)'),
                accel, speed_accel, key_battle,
                *self._text_scroll(),
                dict(t='sep', l='Actions du jeu'),
                T('A'), T('menu'), T('B'), T('carte'), T('discussion'), T('historique'),
                dict(t='sep', l='Autres'),
                edit, info,
                dict(t='act', l='Rétablir les touches par défaut', ok=lambda: (R.default_keys(), R.store()))]

    def _savestate_path(self, n): return self.J.state_path(n)

    @staticmethod
    def _date_fr(date):
        """'2026-10-31 19:21:05' -> '31/10/2026  19:21:05' (nom d'un etat : sa date et son heure d'enregistrement)."""
        try: return time.strftime('%d/%m/%Y  %H:%M:%S', time.strptime(date, '%Y-%m-%d %H:%M:%S'))
        except Exception: return ''

    @staticmethod
    def _readable_location(inf):
        """Lieu de l'etat seulement s'il parle a un joueur (le nom technique d'une carte, comme « mak1f1 », n'est pas montre)."""
        return inf.get('lieu', '') if inf.get('lieu') in ('Carte du monde', 'Combat') else ''

    def _entries_savestates(self):
        """Etats instantanes : une liste deroulante choisit l'action (creer, charger, supprimer) appliquee a l'emplacement valide ; la suppression passe par une fenetre de confirmation."""
        action = self.state_action
        e = [self._choice('Action', ['creer', 'charger', 'supprimer'], lambda: self.state_action, lambda v: setattr(self, 'state_action', v))]
        for n in range(1, SAVESTATE_COUNT + 1):
            inf = self.J.state_info(n)
            if inf: lib = self._date_fr(inf[0].get('date')) or 'Sans date'; val = self._readable_location(inf[0])
            else: lib = '— vide —'; val = ''
            if action == 'creer': e.append(dict(t='slot', l=lib, v=val, n=n, off=False, ok=(lambda n=n: self._save(n))))
            elif action == 'charger': e.append(dict(t='slot', l=lib, v=val, n=n, off=inf is None, ok=(lambda n=n: self._load(n))))
            else: e.append(dict(t='slot', l=lib, v=val, n=n, off=inf is None, ok=(lambda n=n: self._request_deletion(n))))
        return e

    def _entries_quit(self):
        return [dict(t='sep', l='En êtes-vous sûr ?'), dict(t='act', l='Oui', ok=self.J.quit_game), dict(t='act', l='Non', ok=self.back)]

    def _return_to_title(self):
        """« Revenir à l'écran titre » : le menu se ferme (le jeu reprend) et le moteur ouvre la boite d'origine du bouton des Paramètres du jeu (texte du jeu, Oui / Non) ; la suite (Oui : fondu puis titre, Non : retour au jeu)
        est le travail du moteur (Engine.request_return_to_title)."""
        self.shutdown(); self.J.back_to_title()

    # ---- actions
    def _info(self, model, error=False, *value_list):
        """Message d'information (4 secondes, au-dessus du cadre) : `model` est le texte FRANCAIS, a trous (%d, %s) s'il y a des `value_list`. `message[0]` est le texte francais complet ; l'affichage (`_message_text`) traduit le modele AVANT de mettre
        les valeurs (D-238 : l'anglais n'a pas le meme ordre des mots), et traduit aussi les valeurs qui sont des textes de l'outil (nom d'une action, nom d'une touche)."""
        self.message = (model % value_list if value_list else model, time.time(), error, model, value_list)

    def _message_text(self):
        """Le message d'information dans la langue de l'outil ('' s'il n'y en a pas, ou s'il date de plus de 4 secondes)."""
        m = self.message
        if not m or time.time() - m[1] >= 4.0: return ''
        return tr(m[3]) % tuple(tr(v) for v in m[4]) if m[4] else tr(m[3])

    def _save(self, n):
        try:
            self.J.save_state(n, self.J._png_thumbnail(self.mini_tex))
            self.minis.pop(n, None); self._info(N_("État enregistré dans l'emplacement %d."), False, n)
        except Exception as ex:
            self._info(N_("Impossible d'enregistrer l'état : %r"), True, ex)

    def _load(self, n):
        try:
            self.J.load_state(n); self.shutdown()
        except Exception as ex:
            self._info(N_("Impossible de charger l'état : %r"), True, ex)

    def _request_deletion(self, n):
        """Supprimer l'etat n : une fenetre modale demande confirmation (Non preselectionne)."""
        inf = self.J.state_info(n); date = self._date_fr(inf[0].get('date')).strip() if inf else ''
        model = N_("Supprimer l'état %d ?")
        self.popup = dict(titre=model % n, modele=model, valeurs=(n,), detail=date, oui=lambda: self._delete(n), sel=1)          # (`model` + `value_list` : le titre est traduit avant d'y mettre le numero, voir _draw_popup)

    def _popup_key(self, symbol, action):
        K = pyglet.window.key; p = self.popup
        if symbol in (K.ESCAPE, K.BACKSPACE) or action == 'B': self.popup = None
        elif symbol in (K.LEFT, K.RIGHT, K.UP, K.DOWN) or action in ('gauche', 'droite', 'haut', 'bas'): p['sel'] = 1 - p['sel']
        elif symbol in (K.RETURN, K.ENTER, K.SPACE) or action == 'A': self._validate_popup(p['sel'] == 0)

    def _validate_popup(self, yes):
        p, self.popup = self.popup, None
        if yes and p and p.get('oui'): p['oui']()

    def _delete(self, n):
        try:
            os.remove(self.J.state_path(n))
            t = self.minis.pop(n, None)
            if t is not None:
                try: t.delete()
                except Exception: pass
            self._info(N_('État %d supprimé.'), False, n)
        except Exception as ex:
            self._info(N_("Impossible de supprimer l'état : %r"), True, ex)

    # ---- touches clavier
    def key_press(self, symbol, modifiers=0):
        """True si la touche est consommee (le menu est ouvert)."""
        K = pyglet.window.key; R = self.J.reg
        self.mouse_mode = False; self._guard().keyboard(self.mouse_pos)       # une touche : retour a la selection au clavier (curseur dore), le pointeur reprend la main au premier vrai mouvement (ou au clic)
        if self.screen_page == 'historique': return self.hist.key_press(symbol, modifiers)
        if self.capture is not None: self._capture(symbol); return True
        if self.entry is not None: self._entry_key(symbol); return True
        action = R.action_of(symbol)
        if self.popup is not None: self._popup_key(symbol, action); return True
        if self.screen_page == 'interface' and symbol == K.TAB: self.folded = not self.folded; self.pan_fold_at = None; self.pan_click_pos = None; return True              # (editeur : plier / deplier le panneau)
        if self.screen_page == 'interface' and self.folded and not (symbol in (K.ESCAPE, K.BACKSPACE) or action == 'B'): return True
        if self.open_dropdown is not None: self._list_key(symbol, action); return True
        if symbol in (K.ESCAPE, K.BACKSPACE) or action == 'B': self.back(); return True
        if action == 'infos': self.J.set_info(not self.J.helptext); R['infos'] = self.J.helptext; return True          # (la touche des infos a l'ecran se regle dans Commandes)
        if symbol == K.DELETE: self._delete_key(); return True
        if symbol == K.HOME: self._default(); return True
        if symbol in (K.UP,) or action == 'haut': self._move(-1); self._repeat(symbol, 'v', -1)
        elif symbol in (K.DOWN,) or action == 'bas': self._move(1); self._repeat(symbol, 'v', 1)
        elif symbol in (K.LEFT,) or action == 'gauche': self._change_value(-1); self._repeat(symbol, 'h', -1)
        elif symbol in (K.RIGHT,) or action == 'droite': self._change_value(1); self._repeat(symbol, 'h', 1)
        elif symbol in (K.RETURN, K.ENTER, K.SPACE) or action == 'A': self._validate()
        return True

    def _repeat(self, symbol, direction, d):
        """Une direction est enfoncee : elle se repetera (maj) tant qu'elle est maintenue, sur la ligne et l'ecran ou elle a commence."""
        t = time.time(); self.rep = (symbol, t, t, direction, d); self.rep_pos = (self.screen_page, self.selected.get(self.screen_page, 0))

    def do_update(self):
        """Repetition des directions maintenues, appui long sur le panneau de l'editeur (appelee a chaque image). Page Son : les sons jouent (le jeu est arrete) pour qu'on entende les volumes qu'on regle."""
        S = self.J.sound; listening = self.screen_page == 'son'
        if self.screen_page == 'historique':
            if not getattr(self.J, 'history_possible', lambda: True)(): self.back()          # le jeu a repris la main (combat, dialogue, scene : le jeu tourne derriere le menu, #178) : l'historique n'est accessible qu'avec la main sur son personnage (#187)
            else: self.hist.follow_game()          # le jeu tourne derriere l'historique (#178) : ce qu'il y ecrit s'ajoute en bas de la liste
        if listening != S.listening: S.listen(listening)
        if listening: S.tick()
        if self.pan_fold_at is not None and self.pan_pressed is None and time.time() >= self.pan_fold_at: self._fold_pending()          # clic simple sur la barre de titre : le pliage a lieu quand le delai du double clic est ecoule sans second appui (#145)
        a = self.pan_pressed
        if a is not None and not (a['long'] or a['double']) and time.time() - a['t0'] >= LONG_PRESS_DELAY: a['long'] = True          # appui maintenu sans bouger : le panneau se soulève (il suivra le pointeur au premier mouvement)
        if not self.rep: return
        sym, t0, tl, direction, d = self.rep; t = time.time()
        if not self.J.key_list[sym]: self.rep = None; return
        if direction == 'h' and self.rep_pos != (self.screen_page, self.selected.get(self.screen_page, 0)): self.rep = None; return       # la selection a change (souris, autre ecran) : la repetition s'arrete, elle ne doit jamais toucher un autre reglage
        if t - t0 > REPEAT_DELAY and t - tl > REPEAT_STEP:
            self.rep = (sym, t0, t, direction, d)
            if direction == 'v': self._move(d)
            else: self._change_value(d)

    # ---- liste deroulante
    def _open_list(self):
        i = self.selected.get(self.screen_page, 0); entry = self._entries()[i]; cur = entry['get']()
        self.open_dropdown = [i, entry['vals'].index(cur) if cur in entry['vals'] else 0]; self.entries_top = None; self.entries_cur_seen = None; self.dragging_entries = None

    def _entries_end(self, valid):
        d, self.open_dropdown = self.open_dropdown, None
        if not valid or d is None: return
        e = self._entries()
        if d[0] < len(e) and e[d[0]]['t'] == 'choix' and not self._inactive(e[d[0]]) and not self._header(e[d[0]]['vals'][d[1]]): e[d[0]]['set'](e[d[0]]['vals'][d[1]])

    def _move_entries(self, d):
        e = self._entries()
        if self.open_dropdown[0] >= len(e) or e[self.open_dropdown[0]]['t'] != 'choix' or self._inactive(e[self.open_dropdown[0]]): self.open_dropdown = None; return
        vals = e[self.open_dropdown[0]]['vals']; n = len(vals); self.open_dropdown[1] = self._outside_header(vals, (self.open_dropdown[1] + d) % n, d)          # (les intertitres de groupe sont sautes)

    def _list_key(self, symbol, action):
        K = pyglet.window.key
        if symbol in (K.ESCAPE, K.BACKSPACE) or action == 'B': self._entries_end(False)
        elif symbol == K.UP or action == 'haut': self._move_entries(-1); self._repeat(symbol, 'v', -1)
        elif symbol == K.DOWN or action == 'bas': self._move_entries(1); self._repeat(symbol, 'v', 1)
        elif symbol == K.PAGEUP: self._move_entries(-7)
        elif symbol == K.PAGEDOWN: self._move_entries(7)
        elif symbol in (K.RETURN, K.ENTER, K.SPACE) or action == 'A': self._entries_end(True)

    def _set_top(self, t):
        """Premiere valeur visible de la liste deroulante (la barre de defilement la deplace sans changer la valeur surlignee)."""
        b = self.list_bar
        if b: self.entries_top = max(0, min(int(t), b['n'] - b['vis']))

    def _click_entries_bar(self, x, y):
        b = self.list_bar; top = self.entries_top or 0
        if y > b['ptop']: self._set_top(top - 1)
        elif y < b['pbot']: self._set_top(top + 1)
        elif b['pouce'][0] <= y <= b['pouce'][1]: self.dragging_entries = b['pouce'][1] - y
        elif y > b['pouce'][1]: self._set_top(top - (b['vis'] - 1))
        else: self._set_top(top + (b['vis'] - 1))

    def _drag_entries_bar(self, y):
        b = self.list_bar
        if not b: self.dragging_entries = None; return
        free = b['ptop'] - b['pbot'] - b['th']
        if free > 0: self._set_top(round(max(0.0, min(1.0, (b['ptop'] - (y + self.dragging_entries)) / free)) * (b['n'] - b['vis'])))

    def _list_zone(self, x, y):
        for (x0, y0, x1, y1, j) in self.zones_pop:
            if x0 <= x <= x1 and y0 <= y <= y1: return j
        return None

    def _move(self, d):
        if self.screen_page == 'historique': return self.hist.move_by(d)
        if self.open_dropdown is not None: self._move_entries(d); return
        e = self._entries(); n = len(e)
        if not n: return
        i = self.selected.get(self.screen_page, 0)
        for _ in range(n):
            i = (i + d) % n
            if self._active(e[i]): self.selected[self.screen_page] = i; break              # (les intertitres et les lignes inactives sont sautes ; page sans ligne active : la selection ne bouge pas)

    def _current(self):
        """Ligne choisie, ou None quand elle est inactive (aucune action ne l'atteint : gauche / droite, Suppr, Debut, Entree) ; un intertitre cede la place a la ligne suivante."""
        e = self._entries(); i = min(self.selected.get(self.screen_page, 0), len(e) - 1)
        if e and e[i]['t'] == 'sep':
            self._move(1); i = min(self.selected.get(self.screen_page, 0), len(e) - 1)
        return e[i] if e and e[i]['t'] != 'sep' and not self._inactive(e[i]) else None

    def _active_line(self, e, i):
        """Indice de la ligne que le curseur doit occuper : i s'il est actif, sinon la premiere ligne active apres lui, puis avant lui ; i si aucune ligne n'est active (page sans rien a choisir : le curseur n'est pas dessine)."""
        for j in list(range(i, len(e))) + list(range(i - 1, -1, -1)):
            if self._active(e[j]): return j
        return i

    def _purge_inactive(self, e):
        """Ce qui tenait une ligne devenue inactive s'arrete : liste deroulante ouverte, curseur maintenu a la souris, valeur en cours de saisie."""
        def inactive(i): return i is not None and 0 <= i < len(e) and e[i]['t'] != 'sep' and self._inactive(e[i])
        if self.open_dropdown is not None and inactive(self.open_dropdown[0]): self.open_dropdown = None
        if self.dragging is not None and inactive(self.dragging): self.dragging = None
        if self.entry is not None and inactive(self.entry[0]): self.entry = None

    def _change_value(self, d):
        if self.open_dropdown is not None: return
        entry = self._current()
        if not entry: return
        if entry['t'] in ('choix', 'curs'): (entry['moins'] if d < 0 else entry['plus'])()
        elif entry['t'] == 'touche':
            c = self.selected.get('col', 0); self.selected['col'] = min(1, max(0, c + d))

    def _default(self):
        """Remet le curseur, le choix ou les touches de la ligne choisie a leur valeur d'origine."""
        entry = self._current()
        if entry and entry['t'] in ('curs', 'touche', 'choix') and 'defaut' in entry: entry['defaut']()

    def _delete_key(self):
        """Suppr : curseur ou choix -> valeur d'origine ; touche -> la case choisie est videe."""
        entry = self._current()
        if not entry: return
        if entry['t'] == 'touche': self.J.reg.unbind(entry['act'], self.selected.get('col', 0)); self.J.reg.store()
        else: self._default()

    def _validate(self):
        entry = self._current()
        if not entry: return
        if entry['t'] == 'touche': self.capture = (entry['act'], self.selected.get('col', 0)); return
        if entry['t'] == 'curs' and 'ok' not in entry: self.entry = [self.selected.get(self.screen_page, 0), '']          # (une ligne de la page Son a son 'ok' : Entree coupe / remet le son ; la valeur se tape en cliquant dessus)
        elif entry['t'] == 'choix' and entry.get('liste'): self._open_list()
        elif 'ok' in entry: entry['ok']()

    def _capture(self, symbol):
        K = pyglet.window.key; R = self.J.reg; action, col = self.capture
        if symbol == K.ESCAPE: self.capture = None; return
        if symbol in (K.DELETE, K.BACKSPACE): R.unbind(action, col); self.capture = None; R.store(); return
        if RG.name_of(symbol) in RG.RESERVED: self._info(N_('Cette touche est réservée (%s).'), True, RG.key_name(RG.name_of(symbol))); return
        previous = R.bind(action, col, symbol); self.capture = None; R.store()
        if previous and previous != action: self._info(N_('%s retirée de « %s ».'), False, RG.key_name(RG.name_of(symbol)), dict(RG.ACTIONS)[previous].split(' :')[0])

    # ---- souris
    def _zone(self, x, y):
        for (x0, y0, x1, y1, i) in self.zones:
            if x0 <= x <= x1 and y0 <= y <= y1: return i, (x - x0) / max(1.0, x1 - x0)
        return None, 0.0

    def _guard(self):
        """Memoire clavier / souris de la fenetre (Game.mouse_guard), ou la notre quand le menu est essaye sans fenetre."""
        g = getattr(self.J, 'mouse_guard', None)
        if g is None: g = self.__dict__.setdefault('_garde_locale', EN.MouseGuard())
        return g

    def hovered(self, x, y):
        """Le pointeur bouge. Au clavier, la selection ne change que si le pointeur s'est ecarte de plus de EN.MOUSE_TOLERANCE pixels de l'endroit ou il etait a la derniere touche (ecart CUMULE : avant, le test portait sur
        un evenement a l'autre, et une souris qui envoie des mouvements de 1 a 2 pixels ne reprenait jamais la main avant un clic ou un geste tres rapide) ; ensuite la selection suit le pointeur."""
        if self.screen_page == 'historique': return self.hist.hovered(x, y)
        self.mouse_pos = (x, y)
        if self.pan_fold_at is not None and self.pan_pressed is None and not self._double_possible(x, y, time.time()): self._fold_pending()          # le pointeur a quitte le rectangle du double clic : le clic simple est acquis, le panneau replie / deplie sans attendre la fin du delai (#145)
        if not self.mouse_mode and not self._guard().has_moved((x, y)): return          # le pointeur n'a pas vraiment bouge : la selection au clavier reste
        self.mouse_mode = True
        if self.popup is not None:
            for (x0, y0, x1, y1, i) in self.zones_popup:
                if x0 <= x <= x1 and y0 <= y <= y1: self.popup['sel'] = i
            return
        if self.capture is not None: return
        if self.open_dropdown is not None:
            j = self._list_zone(x, y)
            if j is not None: self.open_dropdown[1] = j
            return
        self.on_back = bool(self.zone_ret and self._inside(self.zone_ret, x, y))
        if self.on_back: return
        i, _ = self._zone(x, y)
        if i is not None: self.selected[self.screen_page] = i

    def output(self):
        """Le pointeur a quitte la fenetre : plus rien n'est survole."""
        self.mouse_pos = None; self.on_back = False; self.tt = None

    @staticmethod
    def _inside(z, x, y):
        return z[0] <= x <= z[2] and z[1] <= y <= z[3]

    def _set_view(self, start_idx):
        """Premiere ligne visible de l'ecran courant (la selection ne change pas : la vue ne revient pas dessus tant qu'elle ne bouge pas)."""
        b = self.barre
        if b: self.begin[self.screen_page] = max(b['base'], min(int(start_idx), b['base'] + b['n'] - b['vis']))

    def _click_bar(self, x, y):
        """Clic sur la barre de defilement : fleches (une ligne), curseur (prise pour le glisser), fond de barre (une page)."""
        b = self.barre; start_idx = self.begin.get(self.screen_page, 0)
        if y > b['ptop']: self._set_view(start_idx - 1)
        elif y < b['pbot']: self._set_view(start_idx + 1)
        elif b['pouce'][0] <= y <= b['pouce'][1]: self.dragging_bar = b['pouce'][1] - y
        elif y > b['pouce'][1]: self._set_view(start_idx - (b['vis'] - 1))
        else: self._set_view(start_idx + (b['vis'] - 1))

    def _drag_bar(self, y):
        b = self.barre
        if not b: self.dragging_bar = None; return
        free = b['ptop'] - b['pbot'] - b['th']
        if free > 0: self._set_view(b['base'] + round(max(0.0, min(1.0, (b['ptop'] - (y + self.dragging_bar)) / free)) * (b['n'] - b['vis'])))

    def click(self, x, y, button):
        M = pyglet.window.mouse
        if self.screen_page == 'historique': return self.hist.click(x, y, button)
        self.mouse_mode = True; self.mouse_pos = (x, y)
        if self.pan_fold_at is not None and not self._double_possible(x, y, time.time()): self._fold_pending()          # tout autre appui (ailleurs, trop tard) : le clic simple en attente replie / deplie aussitot, il ne peut plus devenir un double clic
        if self.capture is not None: self.capture = None; return
        if self.popup is not None:                                    # fenetre de confirmation : un bouton la valide, un clic droit ou ailleurs la ferme
            if button != M.RIGHT:
                for (x0, y0, x1, y1, i) in self.zones_popup:
                    if x0 <= x <= x1 and y0 <= y <= y1: self._validate_popup(i == 0); return
            else: self.popup = None
            return
        if self.screen_page == 'interface' and self.fold_zone and self._inside(self.fold_zone, x, y) and button != M.RIGHT: self._press_bar(x, y); return          # barre de titre du panneau : appui court = replier / deplier, appui long = deplacer, double clic = position d'origine
        if self.open_dropdown is not None:                                  # liste deroulante ouverte : un clic sur une valeur la choisit, ailleurs (ou clic droit) la ferme
            b = self.list_bar
            if button != M.RIGHT and b and b['x0'] <= x <= b['x1'] and b['y0'] <= y <= b['y1']: self._click_entries_bar(x, y); return          # barre de defilement de la liste
            j = self._list_zone(x, y) if button != M.RIGHT else None
            c = self.list_border
            if j is not None: self.open_dropdown[1] = j; self._entries_end(True)
            elif button != M.RIGHT and c and c[0] <= x <= c[2] and c[1] <= y <= c[3]: pass          # (clic sur un intertitre ou la marge de la liste : elle reste ouverte)
            else: self.open_dropdown = None
            return
        if button == M.RIGHT:
            if self.entry is not None: self.entry = None
            else: self.back()
            return
        if self.zone_ret and self._inside(self.zone_ret, x, y): self.entry = None; self.back(); return          # bouton retour (en bas a droite de la fenetre)
        i, f = self._zone(x, y)
        if self.screen_page == 'interface' and i is None and self.entry is None:       # editeur : hors du panneau, un clic saisit l'element choisi (un bouton de l'ecran, ou la fenetre montree en apercu)
            c = self.panel_border
            if not (c and c[0] <= x <= c[2] and c[1] <= y <= c[3]):
                if self.target in (RG.SCREEN_TARGET, RG.SPEED_TARGET): self.J.hud.take(x, y, HM.editor_names(self.target))
                else: self.drag = (x, y, list(self._ov()), self.rect_preview)
            return
        if self.entry is not None:                                   # un clic ailleurs que sur la valeur en cours de saisie la valide
            line = self.entry[0]; zv = self.zones_val.get(line)
            if i == line and zv and zv[0] <= x <= zv[1]: return
            self._end_entry(True)
        b = self.barre
        if b and b['x0'] <= x <= b['x1'] and b['y0'] <= y <= b['y1']: self._click_bar(x, y); return
        if i is None: return
        es = self._entries()
        if i >= len(es) or self._inactive(es[i]): return                                              # (ligne devenue inactive depuis la derniere image : le clic ne l'atteint pas)
        self.selected[self.screen_page] = i; entry = es[i]
        bar = self.bars.get(i)
        zv = self.zones_val.get(i); zd = self.default_zones.get(i); zm = self.zones_mute.get(i)
        if entry['t'] == 'curs' and zm and self._inside(zm, x, y): entry['ok']()                           # bouton muet de la page Son : coupe ou remet le son
        elif entry['t'] in ('curs', 'touche', 'choix') and zd and zd[0] <= x <= zd[2] and zd[1] <= y <= zd[3]:       # bouton rond « valeur par defaut » (curseurs, choix, touches d'origine)
            if 'defaut' in entry: entry['defaut']()
        elif entry['t'] == 'curs' and bar and bar[0] - 6 <= x <= bar[1] + 6:       # curseur : le clic maintenu le fait glisser (glisser)
            self.dragging = i; entry['fixe'](min(1.0, max(0.0, (x - bar[0]) / (bar[1] - bar[0]))))
        elif entry['t'] == 'curs' and zv and zv[0] - 8 <= x <= zv[1] + 8: self.entry = [i, '']     # clic sur la valeur : saisie au clavier
        elif entry['t'] == 'touche':
            for c in range(2):
                ze = self.zones_eff.get((i, c))
                if ze and self._inside(ze, x, y): self.selected['col'] = c; self.J.reg.unbind(entry['act'], c); self.J.reg.store(); return          # croix : efface la touche de la case
            col = 1 if x > self.zones_col else 0; self.selected['col'] = col; self._validate()
        elif entry['t'] == 'curs' and 'ok' in entry: pass                                                  # ligne de la page Son : un clic a cote des boutons ne coupe pas le son
        else: self._validate()

    @staticmethod
    def _snap(r, dx, dy, W, H):
        """Deplacement (dx, dy) de la fenetre de cadre r = (x0, y0, x1, y1), corrige pour que l'un de ses bords (ou son milieu) tombe sur une ligne de la grille (32 x 18 cases) : celui qui en est le plus pres."""
        def step(a, b, g, d):
            best = None
            for p in (a, (a + b) / 2.0, b):
                c = round((p + d) / g) * g - (p + d)
                if best is None or abs(c) < abs(best): best = c
            return d + best
        return step(r[0], r[2], W / float(HM.COLS), dx), step(r[1], r[3], H / float(HM.LINES), dy)

    def _press_bar(self, x, y):
        """Appui sur la barre de titre du panneau de l'editeur (le geste se joue dans glisser, maj et relache) : le panneau suit le pointeur des que celui-ci s'eloigne de plus de PRESS_TOLERANCE du point d'appui (glisser
        tout de suite, sans attendre) ou apres un appui maintenu LONG_PRESS_DELAY (il se souleve) ; appui court sans bouger = replier / deplier, une fois le delai du double clic ecoule sans second appui ; deuxieme appui court
        dans DOUBLE_CLICK_DELAY = retour a la position d'origine, sans aucun pliage (#145)."""
        t = time.time(); c = self.panel_border
        if not c: return
        if self.open_dropdown is not None: self.open_dropdown = None
        if self.entry is not None: self._end_entry(True)
        self.pan_pressed = dict(t0=t, x=x, y=y, dx=x - c[2], dy=y - c[3], long=False, double=self._double_possible(x, y, t))         # (dx, dy : decalage du pointeur par rapport au coin haut droit du panneau)

    def _double_possible(self, x, y, t):
        """Un appui en (x, y) a l'instant t serait-il le second d'un double clic, comme Windows en juge : le premier appui court date de moins de GetDoubleClickTime (depuis SON DEBUT, pas depuis son relachement) et le second
        tombe dans le rectangle de SM_CXDOUBLECLK x SM_CYDOUBLECLK pixels centre sur le premier."""
        if self.pan_click_pos is None: return False
        delay, w, h = system_double_click()
        return 0.0 <= t - self.pan_click_t <= delay and abs(x - self.pan_click_pos[0]) <= w / 2.0 and abs(y - self.pan_click_pos[1]) <= h / 2.0

    def _fold_pending(self):
        """Le pliage d'un clic simple sur la barre de titre (editeur d'interface) n'a lieu qu'une fois le delai du double clic ecoule : replie / deplie le panneau et n'attend plus rien (sans effet si aucun clic n'attend)."""
        if self.pan_fold_at is None: return
        self.pan_fold_at = None; self.pan_click_pos = None; self.folded = not self.folded          # (le clic simple est acquis : plus de double clic possible sur lui)

    def release(self, x, y, button):
        if self.screen_page == 'historique': return self.hist.release(x, y, button)
        self.dragging = None; self.dragging_bar = None; self.dragging_entries = None
        a, self.pan_pressed = self.pan_pressed, None
        if a is not None and not a['long']:                                       # appui court (sans mouvement) : un clic simple replie / deplie APRES le delai du double clic (voir maj) ; deuxieme appui d'un double clic : position d'origine, sans plier ni deplier (#145)
            if a['double']: self.pan_pos = None; self.pan_fold_at = None; self.pan_click_pos = None; self.pan_click_t = 0.0
            else:                                                                                  # clic simple : le delai du double clic court depuis le DEBUT de l'appui (comme Windows) ; deja ecoule au relachement (appui long de plus de ce delai) : replie / deplie tout de suite
                self.pan_click_t = a['t0']; self.pan_click_pos = (a['x'], a['y']); self.pan_fold_at = a['t0'] + system_double_click()[0]
                if time.time() >= self.pan_fold_at: self._fold_pending()
        if self.screen_page == 'interface' and self.J.hud.taken is not None: self.J.hud.place(); self.J.reg.store()
        if self.drag is not None: self.drag = None; self.J.reg.store()

    def drag_to(self, x, y):
        """Souris deplacee bouton enfonce : le curseur maintenu (ou celui de la barre de defilement) suit."""
        if self.screen_page == 'historique': return self.hist.drag_to(x, y)
        a = self.pan_pressed
        if a is not None:                                                                    # panneau de l'editeur : il suit le pointeur des que celui-ci a quitte le point d'appui (le panneau se souleve, ni pliage ni double clic), ou apres un appui maintenu
            if not a['long'] and math.hypot(x - a['x'], y - a['y']) > PRESS_TOLERANCE: a['long'] = True; a['double'] = False; self._fold_pending()          # un clic puis un glisser tout de suite : le clic plie d'abord, puis le panneau suit le pointeur
            if a['long']: self.pan_pos = (x - a['dx'], y - a['dy'])
            return
        if self.dragging_entries is not None: self._drag_entries_bar(y); return
        if self.dragging_bar is not None: self._drag_bar(y); return
        if self.dragging is None:
            if self.screen_page == 'interface':
                if self.drag is not None:                              # fenetre du jeu : elle suit le pointeur (decalage en fraction de l'ecran), aimantee a la grille si le reglage est actif
                    x0, y0, o, r0 = self.drag; W, H = self.J.width, self.J.height; dx, dy = x - x0, y - y0
                    if self.J.reg['boutons_aimant'] and r0: dx, dy = self._snap(r0, dx, dy, W, H)
                    self._set_ov(1, max(-0.5, min(0.5, o[1] + dx / W))); self._set_ov(2, max(-0.5, min(0.5, o[2] + dy / H)))
                else: self.J.hud.move_to(x, y)
            return
        bar = self.bars.get(self.dragging); e = self._entries()
        if bar is None or self.dragging >= len(e) or e[self.dragging]['t'] != 'curs' or self._inactive(e[self.dragging]): self.dragging = None; return
        e[self.dragging]['fixe'](min(1.0, max(0.0, (x - bar[0]) / (bar[1] - bar[0]))))

    def text(self, t):
        """Caracteres tapes pendant la saisie d'une valeur."""
        if self.entry is None: return
        for c in t.replace(',', '.'):
            if (c.isdigit() or (c in '.-' and c not in self.entry[1])) and len(self.entry[1]) < 7: self.entry[1] += c

    def _entry_key(self, symbol):
        K = pyglet.window.key
        if symbol in (K.RETURN, K.ENTER): self._end_entry(True)
        elif symbol == K.ESCAPE: self._end_entry(False)
        elif symbol == K.BACKSPACE:
            if self.entry[1]: self.entry[1] = self.entry[1][:-1]
            else: self._end_entry(False)

    def _end_entry(self, valid):
        line, txt = self.entry; self.entry = None
        if not valid or txt in ('', '-', '.'): return
        e = self._entries()
        if line < len(e) and e[line]['t'] == 'curs' and 'saisie' in e[line] and not self._inactive(e[line]):
            try: e[line]['saisie'](float(txt))
            except ValueError: pass

    def wheel(self, sy):
        if self.screen_page == 'historique': return self.hist.wheel(sy)
        if self.popup is not None or (self.screen_page == 'interface' and self.folded): return
        b = self.barre
        if b and self.open_dropdown is None and b['n'] > b['vis']: self._set_view(self.begin.get(self.screen_page, 0) - 2 * (1 if sy > 0 else -1)); return      # liste qui defile : la molette fait defiler la vue (comme la barre)
        self._move(1 if sy > 0 else -1)                                    # (sinon, sens inverse : molette vers le haut = ligne suivante)

    # ---- dessin
    @staticmethod
    def _border(x, y, w, h, k):
        """Fenetre a la maniere des menus du jeu mobile : fond noir de meme opacite que les autres menus, cadre blanc en cinq traits, coins arrondis et transparents (hud_mobile.cadre)."""
        HM.border(x, y, w, h, k, background=BLACK, opacity=HM.GAME_OPACITY)

    def _plate(self, x, y, w, h, k, chosen=False, outline=None, grayed=False):
        """Fond d'un bouton : la plaque des fenetres du jeu (feuille Button, comme « Soigner tous »), enfoncee (assombrie) quand elle est choisie ou survolee. `outline` (encadrement colore) : plus utilise par la page Pause,
        garde pour les ecrans d'avant-partie (sauvegardes, nom, licence). `grayed` : ligne inactive, plaque sans couleur et assombrie (shader gris du jeu). Sans les menus d'origine : plaque dessinee (hud_mobile), voilee si grisee."""
        r = getattr(self.J, 'ui_render', None); vp = (self.J.width, self.J.height)
        if r is not None and (r.plate(x, y, w, h, vp, chosen, grayed=True) if grayed else r.plate(x, y, w, h, vp, chosen)):
            if outline is not None: HM.outline(x, y, w, h, k, outline)
        else:
            HM.plate(x, y, w, h, k, chosen, outline)
            if grayed: v = pyglet.shapes.Rectangle(x + 2 * k, y + 2 * k, w - 4 * k, h - 4 * k, color=(24, 24, 24)); v.opacity = 140; v.draw()

    def _default_button(self, idx, x, y, c, is_default, selected, k, grayed=False):
        """Bouton carre « valeur par defaut » (fleche en cercle) : clair quand la valeur differe de celle d'origine, terne sinon ; s'assombrit (75 %, comme un bouton-icone du jeu appuye) sous le pointeur.
        `grayed` (ligne inactive) : terne, sans zone de clic ni assombrissement."""
        z = (x - 3 * k, y - 3 * k, x + c + 3 * k, y + c + 3 * k)
        if not grayed: self.default_zones[idx] = z
        f = 0.75 if not grayed and self._hovered(z) else 1.0
        if grayed: is_default = True
        clr = tuple(int(a * f) for a in ((90, 90, 90) if is_default else LIGHT))
        r = pyglet.shapes.BorderedRectangle(x, y, c, c, border=max(1, int(2 * k)), color=(255, 255, 255), border_color=clr[:3]); r.opacity = int((30 if is_default else 70) * f); r.draw()
        cx, cy, ra = x + c / 2, y + c / 2, c * 0.28; t0, t1 = math.radians(55), math.radians(55 + 270)
        pts = [(cx + ra * math.cos(t0 + (t1 - t0) * i / 14), cy + ra * math.sin(t0 + (t1 - t0) * i / 14)) for i in range(15)]
        for a, b in zip(pts, pts[1:]): pyglet.shapes.Line(a[0], a[1], b[0], b[1], thickness=max(1.5, 2 * k), color=clr[:3]).draw()
        ex, ey = pts[0]; tg = t0 - math.pi / 2                                       # pointe de fleche au debut de l'arc
        h = c * 0.2
        pyglet.shapes.Triangle(ex + h * math.cos(tg), ey + h * math.sin(tg), ex + h * math.cos(tg + 2.4), ey + h * math.sin(tg + 2.4), ex + h * math.cos(tg - 2.4), ey + h * math.sin(tg - 2.4), color=clr[:3]).draw()

    def _mute_button(self, idx, x, y, c, cut, k, grayed=False):
        """Bouton carre « muet » de la page Son : haut-parleur et ondes quand le son joue, haut-parleur grise barre d'une croix rouge quand il est coupe ; s'assombrit (75 %) sous le pointeur.
        `grayed` (ligne inactive) : terne, sans zone de clic ni assombrissement."""
        z = (x - 3 * k, y - 3 * k, x + c + 3 * k, y + c + 3 * k)
        if not grayed: self.zones_mute[idx] = z
        f = 0.75 if not grayed and self._hovered(z) else 1.0
        clr = tuple(int(a * f) for a in (GRAY[:3] if cut or grayed else LIGHT))
        r = pyglet.shapes.BorderedRectangle(x, y, c, c, border=max(1, int(2 * k)), color=(255, 255, 255), border_color=(90, 90, 90) if grayed else tuple(int(a * f) for a in LIGHT)); r.opacity = int((30 if grayed else 70) * f); r.draw()
        cy = y + c / 2; ep = max(1.5, 2 * k)
        x0 = x + c * 0.14; x1 = x + c * 0.32; x2 = x + c * 0.54                    # caisse du haut-parleur (x0 a x1), puis le cone qui s'evase (x1 a x2)
        pyglet.shapes.Rectangle(x0, cy - c * 0.13, x1 - x0, c * 0.26, color=clr).draw()
        pyglet.shapes.Triangle(x1, cy + c * 0.13, x1, cy - c * 0.13, x2, cy - c * 0.32, color=clr).draw(); pyglet.shapes.Triangle(x1, cy + c * 0.13, x2, cy + c * 0.32, x2, cy - c * 0.32, color=clr).draw()
        if cut:                                                                    # croix rouge a la place des ondes
            rc = tuple(int(a * f) for a in RED[:3]); xc = x + c * 0.76; d = c * 0.14
            pyglet.shapes.Line(xc - d, cy - d, xc + d, cy + d, thickness=ep * 1.3, color=rc).draw(); pyglet.shapes.Line(xc - d, cy + d, xc + d, cy - d, thickness=ep * 1.3, color=rc).draw()
        else:
            for ra in (c * 0.17, c * 0.31):                                          # deux ondes (arcs de cercle) a droite du cone
                pts = [(x2 - c * 0.04 + ra * math.cos(math.radians(a)), cy + ra * math.sin(math.radians(a))) for a in range(-50, 51, 10)]
                for p0, p1 in zip(pts, pts[1:]): pyglet.shapes.Line(p0[0], p0[1], p1[0], p1[1], thickness=ep, color=clr).draw()

    @staticmethod
    def _pill(x, yc, w, h, color):
        """Rectangle a bouts ronds, centre verticalement en yc."""
        r = h / 2
        for sh in (pyglet.shapes.Rectangle(x + r, yc - r, w - 2 * r, h, color=color), pyglet.shapes.Circle(x + r, yc, r, segments=24, color=color), pyglet.shapes.Circle(x + w - r, yc, r, segments=24, color=color)): sh.draw()

    def _switch(self, lookup_key, x, yc, active, selected, grayed, k):
        """Interrupteur coulissant (piste arrondie, bouton rond) : or quand c'est active, gris sinon ; le bouton glisse d'une position a l'autre (animation courte) ; contour or s'il est selectionne."""
        target = 1.0 if active else 0.0; p = self.pos_sw.get(lookup_key, target)                   # premiere apparition : pas d'animation
        p = target if abs(target - p) < 0.02 else p + (target - p) * min(1.0, self.dt_sw * 16.0); self.pos_sw[lookup_key] = p
        w, h = WIDTH_SW * k, HEIGHT_SW * k; r = h / 2
        track = (30, 32, 36) if grayed else tuple(int(a + (b - a) * p) for a, b in zip((20, 22, 26), (225, 207, 3)))
        if selected and not grayed: e = max(1.5, 2 * k); self._pill(x - e, yc, w + 2 * e, h + 2 * e, LIGHT)
        self._pill(x, yc, w, h, track)
        pyglet.shapes.Circle(x + r + (w - 2 * r) * p, yc, r - 3 * k, segments=24, color=(128, 128, 128) if grayed else (255, 255, 255)).draw()

    def _thumbnail(self, n):
        """Texture de la miniature d'un etat (None s'il n'y en a pas)."""
        if n in self.minis: return self.minis[n]
        t = None; inf = self.J.state_info(n)
        if inf and inf[1]:
            try:
                import io
                from PIL import Image
                import numpy as np
                im = Image.open(io.BytesIO(inf[1])).convert('RGBA'); a = np.asarray(im)
                t = pyglet.image.ImageData(im.width, im.height, 'RGBA', np.ascontiguousarray(a[::-1]).tobytes(), pitch=im.width * 4).get_texture()
            except Exception: t = None
        self.minis[n] = t
        return t

    def _scroll_bar(self, x1, ptop, pbot, n, vis, start_idx, k, active, base=0):
        """Barre de defilement a droite de la liste : fleche haut, piste, curseur, fleche bas (haut de la liste en ptop, bas en pbot). Renvoie la geometrie de la barre (pour les clics)."""
        w = BAR_WIDTH * k; x0 = x1 - w; fl = 14 * k; th0, th1 = ptop - fl - 2 * k, pbot + fl + 2 * k          # piste entre les deux fleches
        track = pyglet.shapes.Rectangle(x0, th1, w, th0 - th1, color=(34, 36, 42)); track.draw()
        th = max(26 * k, (th0 - th1) * vis / float(n)); f = start_idx / float(max(1, n - vis)); hau = th0 - f * (th0 - th1 - th)
        self._plate(x0, hau - th, w, th, k * 0.8, active or self._hovered((x0, hau - th, x1, hau)))                       # curseur de la barre : assombri quand on le tient ou qu'on le survole
        clr = LIGHT if n > vis else GRAY[:3]
        for yb, yt, tri_indices in ((ptop - fl, ptop, (x0 + 1.5 * k, ptop - fl + 3 * k, x1 - 1.5 * k, ptop - fl + 3 * k, (x0 + x1) / 2, ptop - 2 * k)), (pbot, pbot + fl, (x0 + 1.5 * k, pbot + fl - 3 * k, x1 - 1.5 * k, pbot + fl - 3 * k, (x0 + x1) / 2, pbot + 2 * k))):
            pyglet.shapes.Triangle(*tri_indices, color=tuple(int(a * 0.75) for a in clr) if n > vis and self._hovered((x0, yb, x1, yt)) else clr).draw()             # fleches : 75 % sous le pointeur
        return dict(x0=x0 - 3 * k, x1=x1 + 3 * k, y0=pbot, y1=ptop, ptop=th0, pbot=th1, th=th, pouce=(hau - th, hau), n=n, vis=vis, base=base)

    def _dpad(self, x, y, c, dark=False, grayed=False):
        """Croix rouge du jeu (effacer une touche), de c pixels, coin bas gauche en (x, y) ; sombre : a 75 % (sous le pointeur, comme un bouton-icone du jeu appuye) ; grise : ligne inactive, croix terne."""
        t = self._sliced_tex('croix', 'ui_MenuTexture.png', DPAD)
        if t is None: return
        self._restore_blend()
        if grayed: dark = True
        if not dark: t.blit(x, y, width=c, height=c * (DPAD[3] - DPAD[1]) / float(DPAD[2] - DPAD[0])); return
        spr = pyglet.sprite.Sprite(t, x=x, y=y); spr.scale_x = c / t.width; spr.scale_y = c * (DPAD[3] - DPAD[1]) / float(DPAD[2] - DPAD[0]) / t.height; spr.color = (110, 110, 110) if grayed else (191, 191, 191); spr.opacity = 110 if grayed else 191; spr.draw()

    def _chevron(self, x, yc, k, grayed=False):
        """Chevron « > » : la ligne ouvre un autre menu (gris quand la ligne est inactive)."""
        for a, b in (((x - 4 * k, yc + 8 * k), (x + 4 * k, yc)), ((x + 4 * k, yc), (x - 4 * k, yc - 8 * k))):
            pyglet.shapes.Line(a[0], a[1], b[0], b[1], thickness=max(2.0, 2.6 * k), color=GRAY[:3] if grayed else (255, 255, 255)).draw()

    def _cap(self, fz):
        """Hauteur des capitales (pixels) d'un texte de taille `fz` (points, 96 ppp) dans la police du jeu : sert a centrer verticalement un texte dans sa case, quelle que soit la police."""
        px = max(6, int(round(fz * 96.0 / 72.0))); c = self._caps.get(px)
        if c is None:
            c = 0.72 * px
            try:
                from PIL import ImageFont
                f = os.path.join(self.J.args.cache, 'ui_font.otf')
                c = float(-ImageFont.truetype(f if self._pol and os.path.exists(f) else 'DejaVuSans.ttf', px).getbbox('H', anchor='ls')[1])
            except Exception: pass
            self._caps[px] = c
        return c

    def _adjust(self, text, size_value, color, maxw):
        """Etiquette de `text` qui tient dans `maxw` pixels (la taille diminue au besoin)."""
        label = self._label(text, size_value, color)
        if label.content_width > maxw > 0: label = self._label(text, size_value * maxw / label.content_width, color)
        return label

    def _preview_elements(self):
        """Elements montres a l'ecran pour l'interface choisie (boutons et croix de l'ecran, ou la fenetre du jeu en apercu) : [(x0, y0, x1, y1, masque, masculin)].
        `mask` : l'element n'est pas dessine en jeu : toute l'interface masquee (« Afficher cette interface a l'ecran » = Non : boutons, croix, fenetre) ou, pour la croix seule, « Afficher la croix » = Non.
        `masculine` : accord de l'etiquette « Masquée » (boutons : « Masqué »)."""
        R = self.J.reg
        if self.target in (RG.SCREEN_TARGET, RG.SPEED_TARGET):
            everything = not self._visible(self.target); out = []
            for n in HM.editor_names(self.target):
                x, y, w, h = self.J.hud.rect(n); out.append((x, y, x + w, y + h, everything or (n == HM.DPAD and not R['croix']), n != HM.DPAD))
            return out
        return [tuple(self.rect_preview) + (not self._visible(self.target), False)] if self.rect_preview else []

    def _shown_rects(self):
        """Rectangles (x0, y0, x1, y1) montres a l'ecran pour l'interface choisie (voir _preview_elements)."""
        return [e[:4] for e in self._preview_elements()]

    def _origin_corner(self, pw, h, W, H, m):
        """Position d'origine du panneau de l'editeur (coin haut droit) : en haut a droite (les boutons sont a gauche, la croix en bas a droite) ; si cela cache l'interface choisie, le premier des autres coins de l'ecran
        (haut gauche, bas droite, bas gauche) qui ne la cache pas, sinon celui qui en cache le moins. Calculee sur la taille du panneau deplie (le panneau replie ne change pas de coin)."""
        pw, h = self.pan_dim or (pw, h); targets = self._shown_rects(); best = None
        for x1, y1 in ((W - m, H - m), (pw + m, H - m), (W - m, h + m), (pw + m, h + m)):
            r = (x1 - pw, y1 - h, x1, y1)
            sc = sum(max(0.0, min(r[2], q[2]) - max(r[0], q[0])) * max(0.0, min(r[3], q[3]) - max(r[1], q[1])) for q in targets)
            if sc <= 0: return x1, y1
            if best is None or sc < best[0]: best = (sc, x1, y1)
        return best[1], best[2]

    def _panel_pos(self, pw, h, W, H, k):
        """Coin haut gauche (x0, y1) du panneau de l'editeur d'interface : position du joueur (apres un appui long et un glissement, gardee le temps de la session) ou position d'origine (_origin_corner),
        toujours ramenee dans l'ecran."""
        x1, y1 = self.pan_pos if self.pan_pos is not None else self._origin_corner(pw, h, W, H, 22 * k)
        x1 = min(max(x1, pw + 4 * k), W - 4 * k); y1 = min(max(y1, h + 4 * k), H - 4 * k)
        return x1 - pw, y1

    def _preview(self):
        """Editeur d'interface : le jeu reste visible ; l'element choisi est montre (boutons de l'ecran avec leur grille, ou fenetre du jeu en apercu, a sa taille et sa place) ; les autres boutons restent a l'ecran."""
        J = self.J; self.rect_preview = None
        if self.target in (RG.SCREEN_TARGET, RG.SPEED_TARGET): J.hud.draw_all(HM.editor_names(self.target), True, J.reg['grille_edition'])              # seuls les boutons de l'ecran (les fenetres du jeu ne sont pas dessinees pendant l'edition)
        else:
            veil = pyglet.shapes.Rectangle(0, 0, J.width, J.height, color=(0, 0, 0)); veil.opacity = 90; veil.draw()
            if J.reg['grille_edition']: HM.draw_grid(J.width, J.height)
            self.rect_preview = J.preview_interface(self.target)                                                    # seule la fenetre choisie (ni les autres fenetres, ni les boutons)
        k = max(0.75, J.height / 900.0)
        for x0, y0, x1, y1, mask, masculine in self._preview_elements():                                           # element non affiche en jeu (toute l'interface, ou la croix seule) : l'apercu reste visible pour le placer, mais assombri et marque
            if not mask: continue
            v = pyglet.shapes.Rectangle(x0, y0, x1 - x0, y1 - y0, color=(0, 0, 0)); v.opacity = 150; v.draw()
            label = self._adjust(HIDDEN_WORDS[masculine], 20 * k, RED, max(x1 - x0 - 18 * k, 36 * k)); label.x = (x0 + x1) / 2 - label.content_width / 2; label.y = (y0 + y1) / 2 - label.content_height / 2
            dot = pyglet.shapes.Rectangle(label.x - 8 * k, label.y - 4 * k, label.content_width + 16 * k, label.content_height + 8 * k, color=(0, 0, 0)); dot.opacity = 200; dot.draw(); label.draw()          # (sur un fond sombre : le texte du message d'essai passe dessous)
            pyglet.shapes.Box(x0, y0, x1 - x0, y1 - y0, thickness=2, color=SELECTION_BORDER).draw()                  # le cadre jaune de selection reste aussi net que sur un element affiche (le voile le couvrait)

    def draw_all(self):
        if self.screen_page == 'historique': return self.hist.draw_all()
        J = self.J; W, H = J.width, J.height; k = max(0.75, H / 900.0)
        editor = self.screen_page == 'interface'
        gl.glDisable(gl.GL_DEPTH_TEST); gl.glEnable(gl.GL_BLEND); gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)
        if editor: self._preview()
        else:
            veil = pyglet.shapes.Rectangle(0, 0, W, H, color=(0, 0, 0)); veil.opacity = 90; veil.draw()
        t = time.time(); self.dt_sw = min(0.1, t - self.t_sw); self.t_sw = t               # (animation des interrupteurs)
        wdir = self.screen_page; e = self._entries(); n = len(e)
        if editor and self.folded: e = []; n = 0                                           # panneau de l'editeur replie : seule la barre de titre reste
        self._purge_inactive(e)
        i_selected = min(self.selected.get(wdir, 0), max(0, n - 1))
        if n and (wdir != 'quitter' or e[i_selected]['t'] != 'sep'): i_selected = self.selected[wdir] = self._active_line(e, i_selected)          # (la selection saute les intertitres et les lignes inactives, y compris a l'ouverture de l'ecran ou quand la ligne choisie vient de devenir inactive)
        n_f = 1 if e and e[0].get('fixe') is True else 0                                 # ligne fixe en haut (aucune page n'en a plus) : elle ne defile pas ; (`fixe` d'un curseur est une fonction, pas True : une page peut commencer par un curseur)
        fs, fst, fsp = 18 * k, 24 * k, 13 * k; pad = 30 * k
        titles = {'racine': N_('Paramètres'), 'affichage': N_('Affichage'), 'son': N_('Son'), 'commandes': N_('Commandes'), 'interface': N_('Interface'), 'etats': N_('États'), 'quitter': N_('Quitter')}
        titles['modifications'] = 'Modifications'                                    # (identique en anglais : rien a traduire ; `_label` le traduirait au besoin)
        with_mini = wdir == 'etats'
        msg = self._message_text()
        # hauteurs : le bouton retour est sous la fenetre ; si les lignes ne tiennent pas, elles defilent (barre a droite, dans la marge)
        with_back = not editor and wdir != 'racine'                                  # (pas de bouton retour a la racine : « Reprendre » ferme le menu)
        kb = 1.1 * k; bw, bh = 64 * kb, 55.5 * kb; back_margin = bh + 10 * k if with_back else 0.0
        foot = 0.0                                          # (plus de ligne d'aide en bas : les aides sont des infobulles ; le message d'information est dessine au-dessus du cadre)
        hmax = H - 2 * 36 * k - back_margin; h_title = 78 * k + (22 * k if wdir == 'commandes' else 0.0)
        if editor: h_title = 64 * k
        rh = max(34 * k, min(52 * k, (hmax - h_title - pad / 2 - foot) / max(1, n)))
        if editor: rh = 38 * k                                                    # panneau compact
        elif wdir == 'commandes': rh = 46 * k                                       # lignes hautes : les cases de touches ne touchent pas les bords (la liste defile)
        fs = min(fs, rh * 0.5)                                                     # lignes serrees : texte plus petit, pour qu'il tienne dans le bouton
        h_title += n_f * rh
        n_s = n - n_f
        h = min(hmax, h_title + n_s * rh + pad / 2 + foot)
        visible_ones = max(1, int((h - h_title - pad / 2 - foot) / rh + 0.02)); barre = n_s > visible_ones
        if barre: h = h_title + visible_ones * rh + pad / 2 + foot                     # (la fenetre se referme sur la derniere ligne visible)
        rdr = 56 * k                                                               # marge droite du contenu des lignes (boutons : 42 px de marge a gauche comme a droite ; la barre de defilement est dans la marge)
        # largeur : le plus long libelle + la place des valeurs / curseurs / cases de touches
        lw = max([self._label(x['l'], fs).content_width for x in e if not (wdir == 'etats' and x['t'] == 'slot')] + [0.0]); vw = 0.0       # (etats : la date des emplacements ne compte pas, la fenetre garde la meme taille avec ou sans etat enregistre ; la date se reduit au besoin)
        for x in e:
            if x['t'] == 'choix':
                tw = max(self._label(self._value_name(x['l'], v), fs).content_width for v in x['vals'])
                vw = max(vw, tw + 24 * k if x.get('liste') else tw + 14 * k + WIDTH_SW * k)               # liste : valeur + fleche ; interrupteur : Oui / Non puis l'interrupteur
        pw = max(540 * k, 52 * k + lw + 40 * k + vw + rdr)
        if wdir in ('affichage', 'son', 'commandes', 'interface'): pw = max(pw, 52 * k + lw + 40 * k + 44 * k + 200 * k + 20 * k + 90 * k + rdr + (36 * k if wdir == 'son' else 0.0))          # (son : plus le bouton muet)
        if wdir == 'modifications': pw = max(pw, 52 * k + lw + 40 * k + vw + rdr + 20 * k)
        if wdir == 'commandes': pw = max(pw, 52 * k + lw + 30 * k + 40 * k + 2 * CELL_WIDTH * k + CELL_SPACING * k + rdr)
        wmini = 360 * k if with_mini else 0.0; gap = 24 * k if with_mini else 0.0
        x0 = (W - pw - wmini - gap) / 2; y1 = (H + h + back_margin) / 2; y0 = y1 - h
        if editor:                                                                 # replie : la barre de titre seule, pour voir tout l'ecran ; position : celle du joueur apres un deplacement, sinon celle d'origine (voir _panel_pos)
            if self.folded and self.pan_dim: pw = self.pan_dim[0]                       # replie : la barre de titre garde la largeur du panneau deplie (elle reste sous le pointeur : appui court puis double clic)
            elif self.folded: pw = max(300 * k, self._label(titles['interface'], fst).content_width + 130 * k)
            else: self.pan_dim = (pw, h)
            x0, y1 = self._panel_pos(pw, h, W, H, k); y0 = y1 - h
        self.panel_border = (x0, y0, x0 + pw, y1) if editor else None
        self.fold_zone = (x0, y1 - h_title, x0 + pw, y1) if editor else None
        a_pan = self.pan_pressed if editor else None; lifted = bool(a_pan and a_pan['long'])          # appui sur la barre de titre : titre dore ; apres l'appui long, le panneau « se souleve » (cadre agrandi, contour dore)
        if lifted:
            g = 7 * k; self._border(x0 - g, y0 - g, pw + 2 * g, h + 2 * g, k)
            pyglet.shapes.Box(x0 - g, y0 - g, pw + 2 * g, h + 2 * g, thickness=max(2.0, 3 * k), color=GOLD[:3]).draw()
        else: self._border(x0, y0, pw, h, k)
        e_t = self._label(titles.get(wdir, ''), fst, GOLD if (a_pan and not a_pan['double']) else WHITE); e_t.x = x0 + (pw - e_t.content_width) / 2; e_t.y = y1 - (44 if editor else 52) * k; e_t.draw()
        if editor:                                                                 # plier / deplier le panneau : fleche dans la barre de titre (vers le haut = replier, vers le bas = deplier)
            fx, fy = e_t.x + e_t.content_width + 26 * k, y1 - 32 * k                  # (collee au titre : elle le suit quand le panneau change de largeur)
            over = self.mouse_mode and self.mouse_pos and self._inside(self.fold_zone, *self.mouse_pos)
            clr = GOLD[:3] if over else (200, 200, 200)
            if self.folded: pyglet.shapes.Triangle(fx - 9 * k, fy + 5 * k, fx + 9 * k, fy + 5 * k, fx, fy - 6 * k, color=clr).draw()
            else: pyglet.shapes.Triangle(fx - 9 * k, fy - 5 * k, fx + 9 * k, fy - 5 * k, fx, fy + 6 * k, color=clr).draw()
        # vue : la selection reste visible quand elle change ; sinon la vue ne bouge que par la barre ou la molette
        start_idx = self.begin.get(wdir, n_f)
        if self.seen_selected.get(wdir) != i_selected:
            if i_selected >= n_f:
                if i_selected < start_idx: start_idx = i_selected
                elif i_selected >= start_idx + visible_ones: start_idx = i_selected - visible_ones + 1
            self.seen_selected[wdir] = i_selected
        begin = self.begin[wdir] = max(n_f, min(start_idx, max(n_f, n - visible_ones)))
        anc = (self.default_zones, self.zones_mute, self.zones_eff)                                  # boutons de chaque ligne a l'image precedente : sous le pointeur, c'est le bouton qui s'assombrit, pas la plaque de la ligne
        self.zones = []; self.zones_off = []; self.bars = {}; self.zones_val = {}; self.default_zones = {}; self.zones_mute = {}; self.zones_eff = {}; self.zones_pop = []; lines = {}; self.barre = None; self.list_bar = None; self.list_border = None
        xr = x0 + pw - rdr                                                        # bord droit du contenu des lignes
        cx2 = xr - 40 * k - CELL_WIDTH * k; cx1 = cx2 - CELL_SPACING * k - CELL_WIDTH * k; self.zones_col = cx2 - CELL_SPACING * k / 2
        plx = x0 + 42 * k; plw = pw - 84 * k                                      # boutons : meme marge a gauche et a droite
        if wdir == 'commandes':
            for c, cx in enumerate((cx1, cx2)):
                eh = self._label(tr('Touche %d') % (c + 1), fsp, GRAY); eh.x = cx + (CELL_WIDTH * k - eh.content_width) / 2; eh.y = y1 - h_title + 6 * k; eh.draw()
        pos = []
        if n_f: pos.append((0, y1 - 66 * k))
        yy = y1 - h_title
        for idx in range(begin, min(n, begin + visible_ones)): pos.append((idx, yy)); yy -= rh
        mouse = self.mouse_mode; modal = self.popup is not None or self.open_dropdown is not None or self.capture is not None
        for idx, ytop in pos:
            entry = e[idx]; ybottom = ytop - rh; lines[idx] = (ybottom, ytop)
            off = entry['t'] != 'sep' and self._inactive(entry)                                       # ligne inactive (relue a chaque image) : toute la case est grisee, jamais choisie ni survolee, sans zone de clic
            if mouse:                                                                         # souris : la ligne est assombrie tant que le pointeur est sur elle (et pas sur l'un de ses boutons) ; il n'y a plus de selection quand il en sort
                selected = (not modal and not off and entry['t'] != 'sep' and self._pointer_in((plx, ybottom + 3 * k, plx + plw, ytop - 3 * k))
                       and not self._pointer_in(anc[0].get(idx)) and not self._pointer_in(anc[1].get(idx)) and not any(self._pointer_in(z) for (i_, c_), z in anc[2].items() if i_ == idx))
            else: selected = idx == i_selected and entry['t'] != 'sep' and not off                          # clavier : la ligne choisie, avec le curseur dore
            if entry['t'] != 'sep': self._plate(plx, ybottom + 3 * k, plw, rh - 6 * k, k, selected, grayed=off)       # fond du bouton, comme ceux du menu des commandes du jeu mobile : la plaque s'assombrit quand elle est choisie (clavier) ou survolee (souris), sans encadrement
            if selected and not mouse: self._cursor(x0 + 6 * k, ybottom + rh / 2, min(rh * 0.6, 26 * k))             # curseur dore des menus du jeu (selection au clavier)
            mute = entry['t'] == 'curs' and 'actif' in entry and not entry['actif']()                  # ligne de la page Son dont le son est coupe : nom, valeur et jauge grises
            clr = GRAY if off or mute else WHITE
            base = ybottom + rh / 2 - 0.45 * fs                                                  # texte centre dans le bouton
            lx = x0 + 52 * k
            if entry['t'] == 'sep' and entry.get('v'):                                               # ligne d'information (geste de la souris) : le geste a gauche, son effet a droite en gris, sans plaque, ni selection, ni zone de clic
                label = self._label(entry['l'], fs, WHITE); label.x = lx; label.y = base; label.draw()
                ev = self._adjust(entry['v'], fs, GRAY, xr - 24 * k - (lx + label.content_width)); ev.x = xr - ev.content_width; ev.y = base; ev.draw()
                continue
            if entry['t'] == 'sep':                                                              # intertitre : au centre de la fenetre
                label = self._label(entry['l'], fs, GOLD); label.x = x0 + (pw - label.content_width) / 2; label.y = base; label.draw()
                self.zones.append((plx, ybottom + 3 * k, plx + plw, ytop - 3 * k, idx))
                continue
            maxw_lab = 0.0                                                                    # largeur permise au libelle (0 : aucune limite)
            if entry['t'] == 'slot':
                nu = self._label('%d' % entry['n'], fs, clr); nu.x = lx; nu.y = base; nu.draw(); lx += 44 * k
                maxw_lab = x0 + pw - 66 * k - (self._label(entry['v'], fsp * 1.2, GRAY).content_width + 12 * k if entry['v'] else 0.0) - lx           # (jusqu'au lieu, a droite)
            lab = self._adjust(entry['l'], fs, clr, maxw_lab) if maxw_lab else self._label(entry['l'], fs, clr); lab.x = lx; lab.y = base; lab.draw()
            if entry['t'] == 'act' and entry.get('sous'): self._chevron(xr - 6 * k, ybottom + rh / 2, k, off)
            xc = xr - (34 * k if entry['t'] == 'choix' and 'defaut' in entry else 0.0)                 # (place du bouton rond « valeur par defaut » des choix, a droite de la ligne)
            if entry['t'] == 'choix' and 'defaut' in entry: self._default_button(idx, xr - 26 * k, ybottom + rh / 2 - 13 * k, 26 * k, entry['est_defaut'](), selected, k, off)
            if entry['t'] == 'choix' and entry.get('liste'):                                        # liste deroulante : valeur courante et petite fleche vers le bas
                vl = self._label(entry['v'](), fs, clr); vl.x = xc - 24 * k - vl.content_width; vl.y = base; vl.draw()
                fx, fy = xc - 8 * k, ybottom + rh / 2
                pyglet.shapes.Triangle(fx - 7 * k, fy + 4 * k, fx + 7 * k, fy + 4 * k, fx, fy - 5 * k, color=GOLD[:3] if selected else clr[:3]).draw()
                if not off: self.zones_val[idx] = (vl.x - 10 * k, xc + 10 * k)
            elif entry['t'] == 'choix':                                                          # interrupteur Oui / Non : le texte de la valeur, puis l'interrupteur
                sw_x = xc - WIDTH_SW * k; active = bool(entry['get']())
                vl = self._label(entry['v'](), fs, clr if not active or off else GOLD); vl.x = sw_x - 14 * k - vl.content_width; vl.y = base; vl.draw()
                self._switch(entry['l'], sw_x, ybottom + rh / 2, active, selected and not mouse, off, k)
                if not off: self.zones_val[idx] = (vl.x - 10 * k, sw_x + WIDTH_SW * k + 10 * k)
            elif entry['t'] == 'curs':
                if self.entry is not None and self.entry[0] == idx: txt = (self.entry[1] + ('_' if int(time.time() * 2) % 2 == 0 else ' ')).rjust(3)
                else: txt = entry['v']()
                dm = 36 * k if 'actif' in entry else 0.0                                         # place du bouton muet (page Son), entre la valeur et le bouton « valeur par defaut »
                dr = xr - 40 * k - dm                                                         # bord droit de la valeur : le bouton « valeur par defaut » est a sa droite
                vl = self._label(txt, fs, GOLD if self.entry is not None and self.entry[0] == idx else clr); vl.x = dr - vl.content_width; vl.y = base; vl.draw()
                bw_ = 200 * k; bx1 = dr - 90 * k - 20 * k; bx0 = bx1 - bw_; by = ybottom + rh / 2 - 5 * k
                if not off: self.zones_val[idx] = (vl.x - 10 * k, dr + 10 * k); self.bars[idx] = (bx0, bx1)
                background = pyglet.shapes.Rectangle(bx0, by, bw_, 10 * k, color=(16, 18, 22)); background.draw()
                rem = pyglet.shapes.Rectangle(bx0, by, bw_ * max(0.0, min(1.0, entry['frac']())), 10 * k, color=(110, 110, 104) if mute or off else YELLOW); rem.draw()            # (jauge jaune ; grise quand le son est coupe ou la ligne inactive)
                cur = pyglet.shapes.Rectangle(bx0 + bw_ * max(0.0, min(1.0, entry['frac']())) - 3 * k, by - 4 * k, 6 * k, 18 * k, color=(150, 150, 150) if off else (255, 255, 255)); cur.draw()
                if 'actif' in entry: self._mute_button(idx, xr - 62 * k, ybottom + rh / 2 - 13 * k, 26 * k, mute, k, off)
                if 'defaut' in entry: self._default_button(idx, xr - 26 * k, ybottom + rh / 2 - 13 * k, 26 * k, entry['est_defaut'](), selected, k, off)
            elif entry['t'] == 'slot':
                if entry['v']: vl = self._label(entry['v'], fsp * 1.2, GRAY); vl.x = x0 + pw - 24 * k - 42 * k - vl.content_width; vl.y = base; vl.draw()
            elif entry['t'] == 'touche':
                for c, cx in enumerate((cx1, cx2)):
                    txt = entry['v'][c]; active = (selected and not mouse and self.selected.get('col', 0) == c) or self.capture == (entry['act'], c); empty = txt == RG.key_name(None)          # (case choisie : au clavier, ou en attente d'une touche ; a la souris c'est la plaque qui s'assombrit)
                    if self.capture is not None and self.capture == (entry['act'], c): txt = '…'
                    HM.border(cx, ybottom + 9 * k, CELL_WIDTH * k, rh - 18 * k, k * 0.5, 0.5 if active else 0.0, background=BLACK, opacity=0.75)          # case de la touche (plus claire quand elle est choisie), a distance des bords du bouton
                    zone_t = CELL_WIDTH * k - (0 if empty else 2 * 22 * k); fz = fs * 0.8                 # texte centre dans la case (marges egales : la croix rouge est a droite, hors de la zone du texte)
                    vl = self._label(txt, fz, GOLD if active else (GRAY if empty or off else WHITE))
                    if vl.content_width > zone_t - 8 * k: fz *= (zone_t - 8 * k) / vl.content_width; vl = self._label(txt, fz, GOLD if active else (GRAY if off else WHITE))
                    vl.x = cx + (CELL_WIDTH * k - vl.content_width) / 2; vl.y = ybottom + rh / 2 - self._cap(fz) / 2; vl.draw()               # (ligne de base : le milieu de la hauteur des capitales sur le milieu de la case)
                    if not empty and self.capture != (entry['act'], c):
                        cc = 12 * k; cxx = cx + CELL_WIDTH * k - cc - 8 * k; ze = (cxx - 4 * k, ybottom + 9 * k, cx + CELL_WIDTH * k, ybottom + rh - 9 * k)
                        if not off: self.zones_eff[(idx, c)] = ze
                        self._dpad(cxx, ybottom + rh / 2 - cc * 0.45, cc, not off and self._hovered(ze), off)                  # (a 75 % sous le pointeur ; terne quand la ligne est inactive)
                self._default_button(idx, xr - 26 * k, ybottom + rh / 2 - 13 * k, 26 * k, entry['est_defaut'](), selected, k, off)
            (self.zones_off if off else self.zones).append((plx, ybottom + 3 * k, plx + plw, ytop - 3 * k, idx))          # (une ligne inactive n'a pas de zone : ni survol, ni clic ; sa zone ne sert qu'a l'infobulle)
        if barre: self.barre = self._scroll_bar(x0 + pw - 14 * k, y1 - h_title, y1 - h_title - visible_ones * rh, n_s, visible_ones, begin - n_f, k, self.dragging_bar is not None, n_f)
        # pied du cadre : aide (centree, toujours dans le cadre)
        if msg:
            em = self._adjust(msg, fsp * 1.1, RED if self.message[2] else GOLD, W - 24 * k); em.x = min(max(12 * k, x0 + (pw - em.content_width) / 2), W - em.content_width - 12 * k); em.y = min(H - 24 * k, y1 + 12 * k); em.draw()
        # bouton retour, en bas a droite de la fenetre
        self.zone_ret = None
        if with_back:
            bx = x0 + pw - bw - 8 * k; by = y0 - 8 * k - bh; self.zone_ret = (bx, by, bx + bw, by + bh)
            self._back_button(bx, by, bw, bh, self._hovered(self.zone_ret))                    # (version enfoncee de la feuille Button sous le pointeur)
        # miniature de l'etat survole
        if with_mini:
            mx = x0 + pw + gap
            self._border(mx, y1 - h, wmini, h, k)
            if e and e[i_selected]['t'] == 'slot':
                n_e = e[i_selected]['n']; t = self._thumbnail(n_e); inf = J.state_info(n_e)
                if t is not None:
                    w_i = wmini - 40 * k; h_i = w_i * t.height / t.width
                    spr = pyglet.sprite.Sprite(t, x=mx + 20 * k, y=y1 - 40 * k - h_i); spr.scale_x = w_i / t.width; spr.scale_y = h_i / t.height; spr.draw()
                    entries = []
                    if inf:
                        entries = [self._date_fr(inf[0].get('date')) or 'Sans date', self._readable_location(inf[0])]
                    for j, line in enumerate(entries):
                        el = self._label(line, fsp * 1.1, WHITE if j == 0 else GRAY); el.x = mx + (wmini - el.content_width) / 2; el.y = y1 - 40 * k - h_i - 34 * k - j * 30 * k; el.draw()
                else:
                    el = self._label('Emplacement vide' if not inf else 'Pas de miniature', fs, GRAY); el.x = mx + (wmini - el.content_width) / 2; el.y = y1 - h / 2; el.draw()
        if self.open_dropdown is not None and self.open_dropdown[0] in lines and self.open_dropdown[0] < n and e[self.open_dropdown[0]]['t'] == 'choix':
            self._draw_entries(e[self.open_dropdown[0]], lines[self.open_dropdown[0]], xr + 6 * k, k, fs)
        self._draw_tooltip(e, n, lines, plx, plw, k, fsp, W, H)
        self._draw_popup(k, fs, fsp, W, H)

    # ---- infobulles (aides au survol de la souris) et fenetre modale
    # (D-238 : les aides sont des textes francais ; `_helptext_lines` traduit chaque phrase separee par trois espaces, voir le catalogue texts_en\pause.py : une aide assemblee (« ... » + KEY_HELPTEXT) se traduit donc phrase par phrase)
    KEY_HELPTEXT = "Entrée : changer la touche   ←/→ : case   Suppr : effacer   Début ou bouton rond : touche d'origine"
    SAVESTATES_HELPTEXT = {'creer': N_("Entrée : enregistrer ici (écrase l'état)"), 'charger': N_('Entrée : charger cet état'), 'supprimer': N_('Entrée : supprimer cet état')}

    def _line_helptext(self, entry):
        """Texte d'aide d'une ligne du menu ('   ' separe les lignes de l'infobulle) ; '' s'il n'y en a pas."""
        t = entry['t']
        if t != 'sep' and self._inactive(entry): return entry.get('aide') or ''                   # ligne inactive : pas de consigne de clavier ou de souris, seulement son aide propre (elle dit pourquoi)
        if t == 'touche': return entry.get('aide') or self.KEY_HELPTEXT
        prefix = entry['aide'] + '   ' if entry.get('aide') and t != 'act' else ''          # texte propre a la ligne, avant la consigne generale
        if t == 'curs' and 'actif' in entry: return prefix + 'Glisser ou ←/→ : volume   Entrée ou haut-parleur : couper / remettre   Clic sur la valeur : la taper   Suppr ou bouton rond : volume et son par défaut'
        if t == 'curs': return prefix + 'Glisser ou ←/→ : changer la valeur   Clic sur la valeur : la taper   Suppr ou bouton rond : valeur par défaut'
        if t == 'choix':
            return prefix + ('Entrée ou clic : activer / désactiver   ←  : Non   →  : Oui' if entry.get('sw') else 'Entrée ou clic : ouvrir la liste   ←/→ : valeur précédente / suivante') + ('   Suppr ou bouton rond : valeur par défaut' if 'defaut' in entry else '')
        if t == 'act' and entry.get('aide'): return entry['aide']
        if t == 'slot': return self.SAVESTATES_HELPTEXT[self.state_action]
        if self.screen_page == 'interface': return "Glisse l'élément choisi pour le placer   Échap ou clic droit : terminer   Tab : replier le panneau"
        return ''

    def _helptext_lines(self, text, maxw, fz):
        """Lignes d'une infobulle : coupees aux espaces triples, puis a la largeur maxw. Chaque phrase (entre deux espaces triples) est traduite AVANT d'etre coupee a la largeur : une ligne coupee n'est plus une phrase du catalogue (D-238)."""
        import re
        out = []
        for l in re.split(r'\s{3,}', text.strip()):
            l = tr(l); cur = ''
            for word in l.split(' '):
                attempt = (cur + ' ' + word).strip()
                if cur and self._label(attempt, fz).content_width > maxw: out.append(cur); cur = word
                else: cur = attempt
            if cur: out.append(cur)
        return out

    def _draw_tooltip(self, e, n, lines, plx, plw, k, fsp, W, H):
        """Infobulle : aide de la ligne survolee par la souris (apres 0,4 s), ou consigne de la saisie / de la capture d'une touche sous la ligne choisie."""
        if self.popup is not None: self.tt = None; return
        fz = fsp * 1.05; text = ''; anchor = None
        i_selected = min(self.selected.get(self.screen_page, 0), max(0, n - 1))
        if self.capture is not None: text = tr("Appuie sur la touche pour « %s »") % tr(dict(RG.ACTIONS)[self.capture[0]]) + "   Échap : annuler   Suppr : effacer"; anchor = i_selected
        elif self.entry is not None: text = 'Tape la valeur   Entrée : valider   Échap : annuler'; anchor = self.entry[0]
        elif self.open_dropdown is not None: self.tt = None; return
        elif self.pan_pressed is not None: self.tt = None; return                       # (pas d'infobulle pendant un appui sur la barre de titre)
        elif self.fold_zone and self.mouse_mode and self.mouse_pos and self._inside(self.fold_zone, *self.mouse_pos):
            lookup_key = ('plier', 0)
            if self.tt is None or self.tt[0] != lookup_key: self.tt = (lookup_key, time.time())
            if time.time() - self.tt[1] > 0.4: text = "Appui court : replier / déplier le panneau (Tab)   Appui long : le déplacer   Double clic : le remettre à sa place"
        elif self.mouse_mode and self.mouse_pos and self.capture is None:
            i, _ = self._zone(*self.mouse_pos)
            if i is None: i = next((j for (x0, y0, x1, y1, j) in self.zones_off if self._inside((x0, y0, x1, y1), *self.mouse_pos)), None)          # (ligne inactive : seule son aide, si elle en a une, s'affiche)
            lookup_key = (self.screen_page, i)
            if i is None or i >= n: self.tt = None; return
            if self.tt is None or self.tt[0] != lookup_key: self.tt = (lookup_key, time.time())
            if time.time() - self.tt[1] > 0.4: text = self._line_helptext(e[i])
        else: self.tt = None
        if not text: return
        ls = self._helptext_lines(text, 520 * k, fz)
        if not ls: return
        ets = [self._label(l, fz, WHITE) for l in ls]; lh = fz * 1.65
        w = max(label.content_width for label in ets) + 28 * k; h = len(ets) * lh + 18 * k
        if anchor is not None and anchor in lines:                                   # consigne : sous la ligne choisie (au-dessus s'il n'y a pas la place)
            yb, yt = lines[anchor]; x = plx + 24 * k; y = yb - 8 * k - h
            if y < 8 * k: y = yt + 8 * k
        else:
            mx, my = self.mouse_pos; x = mx + 14 * k; y = my - 20 * k - h
            if y < 8 * k: y = my + 22 * k
        x = max(8 * k, min(x, W - w - 8 * k)); y = max(8 * k, min(y, H - h - 8 * k))
        HM.border(x, y, w, h, k * 0.5, 0.0, background=BLACK, opacity=0.94)
        for j, label in enumerate(ets): label.x = x + 14 * k; label.y = y + h - 9 * k - lh * (j + 1) + (lh - fz * 1.0) * 0.45; label.draw()

    def _draw_popup(self, k, fs, fsp, W, H):
        """Fenetre modale Oui / Non (suppression d'un etat) : le menu reste visible, assombri ; Non est preselectionne."""
        self.zones_popup = []
        p = self.popup
        if p is None: return
        veil = pyglet.shapes.Rectangle(0, 0, W, H, color=(0, 0, 0)); veil.opacity = 120; veil.draw()
        title_screen = tr(p['modele']) % p['valeurs'] if p.get('modele') else p['titre']
        label = self._label(title_screen, fs * 1.2, WHITE); ed = self._label(p['detail'], fsp * 1.15, GRAY) if p.get('detail') else None
        bw, bh = 150 * k, 46 * k; w = max(2 * bw + 60 * k, label.content_width + 80 * k, (ed.content_width + 80 * k) if ed else 0); h = 200 * k
        x, y = (W - w) / 2, (H - h) / 2
        self._border(x, y, w, h, k)
        label.x = x + (w - label.content_width) / 2; label.y = y + h - 62 * k; label.draw()
        if ed: ed.x = x + (w - ed.content_width) / 2; ed.y = y + h - 92 * k; ed.draw()
        for i, lib in enumerate(('Oui', 'Non')):
            bx = x + w / 2 + (-bw - 14 * k if i == 0 else 14 * k); by = y + 28 * k
            selected = self._pointer_in((bx, by, bx + bw, by + bh)) if self.mouse_mode else p['sel'] == i                  # souris : le bouton sous le pointeur s'assombrit ; clavier : le bouton choisi, avec le curseur dore
            self._plate(bx, by, bw, bh, k, selected)
            if selected and not self.mouse_mode: self._cursor(bx - 24 * k, by + bh / 2, min(bh * 0.6, 26 * k))
            lb = self._label(lib, fs, WHITE); lb.x = bx + (bw - lb.content_width) / 2; lb.y = by + bh / 2 - 0.45 * fs; lb.draw()
            self.zones_popup.append((bx, by, bx + bw, by + bh, i))

    def _draw_entries(self, entry, line, xd, k, fs):
        """Liste deroulante d'un choix : sous la ligne (au-dessus s'il n'y a pas la place), valeur courante en or, curseur dore comme dans les menus du jeu ; une barre de defilement
        (fleches, curseur, clic sur la piste, molette = valeur suivante) quand toutes les valeurs ne tiennent pas."""
        J = self.J; vals = entry['vals']; names = [self._value_name(entry['l'], v) for v in vals]; cur = self.open_dropdown[1]; H = J.height; n = len(vals)
        ih = 36 * k; nvis = max(1, min(n, 8, int((H - 40 * k) // ih)))
        barre = n > nvis; lb = (BAR_WIDTH + 12) * k if barre else 0.0                          # place de la barre de defilement, a droite des valeurs
        w = max(max(self._label(t, fs).content_width for t in names) + 90 * k + lb, 240 * k); h = nvis * ih + 20 * k
        ybottom, ytop = line; y1 = ybottom - 4 * k; y0 = y1 - h
        if y0 < 8 * k: y1 = ytop + 4 * k; y0 = y1 - h
        if y0 < 8 * k: y0 = 8 * k; y1 = y0 + h
        x1 = xd; x0 = x1 - w
        self._border(x0, y0, w, h, k); self.list_border = (x0, y0, x1, y1)
        if self.entries_top is None: self.entries_top = max(0, min(cur - nvis // 2, n - nvis)); self.entries_cur_seen = cur
        elif self.entries_cur_seen != cur:                                                         # la valeur surlignee a change : la vue la suit ; sinon seule la barre ou la molette la deplace
            if cur < self.entries_top or (cur - 1 < self.entries_top and cur > 0 and self._header(vals[cur - 1])): self.entries_top = cur - 1 if cur > 0 and self._header(vals[cur - 1]) else cur          # (le premier choix d'un groupe montre son intertitre)
            elif cur >= self.entries_top + nvis: self.entries_top = cur - nvis + 1
            self.entries_cur_seen = cur
        top = self.entries_top = max(0, min(self.entries_top, n - nvis))
        self.zones_pop = []; y = y1 - 10 * k
        for j in range(top, top + nvis):
            yb = y - ih; current_item = vals[j] == entry['get']()
            if self._header(vals[j]):                                                          # intertitre de groupe : au centre de la liste, en gris dore terne et plus petit (l'or est celui de la valeur courante), sans zone de clic
                size_i, clr_i = heading_style(fs); label = self._label(names[j], size_i, clr_i); label.x = x0 + (w - lb - label.content_width) / 2; label.y = yb + (ih - fs * 1.33) / 2 + 5 * k; label.draw()
                pyglet.shapes.Rectangle(x0 + 14 * k, yb + 3 * k, w - lb - 28 * k, max(1, int(k)), color=HEADING_RULE).draw(); y -= ih; continue
            if self.mouse_mode:                                                               # souris : la valeur sous le pointeur est assombrie (plaque enfoncee), sans encadrement
                if self._pointer_in((x0 + 6 * k, yb, x1 - 6 * k - lb, yb + ih)): self._plate(x0 + 6 * k, yb + 2 * k, w - 12 * k - lb, ih - 4 * k, k * 0.8, True)
            elif j == cur: self._cursor(x0 + 8 * k, yb + ih / 2, 22 * k)                       # clavier : curseur dore
            label = self._label(names[j], fs, GOLD if current_item else WHITE); label.x = x0 + 44 * k; label.y = yb + (ih - fs * 1.33) / 2 + 5 * k; label.draw()
            self.zones_pop.append((x0 + 6 * k, yb, x1 - 6 * k - lb, y, j)); y -= ih
        if barre: self.list_bar = self._scroll_bar(x1 - 8 * k, y1 - 10 * k, y0 + 10 * k, n, nvis, top, k, self.dragging_entries is not None, 0)
        else: self.list_bar = None
