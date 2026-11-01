"""Menu Echap : reprendre, etats instantanes (savestates), affichage, son, commandes (vitesses, touches, interface), retour a l'ecran titre.

Pendant que le menu est ouvert le moteur est arrete (la scene reste affichee, assombrie). Navigation : fleches ou touches haut / bas / gauche / droite / A / B reglees,
Entree / Espace = valider, Echap / Retour arriere = retour, souris (survol, clic, clic droit ou bouton « retour » en bas a droite de la fenetre = retour, molette, barre de defilement).
Deux modes de selection : au clavier, le curseur dore (fixe) devant la ligne ; a la souris, la ligne est encadree de jaune.
Les reglages sont enregistres dans reglages.json. Fenetres noires, curseur dore et bouton retour : ceux des menus du jeu (feuilles MenuTexture et Button)."""
import math, os, time
import numpy as np
import pyglet
from pyglet import gl
import reglages as RG
import hd as HD
import hud_mobile as HM

NB_ETATS = 9                 # emplacements d'etats instantanes (touches 1 a 9)
DELAI_REPETITION, PAS_REPETITION = 0.40, 0.07
# Palette de texte du jeu (MenuPortItemTable : blanc, jaune, rouge, gris) ; fenetres noires cadrees de blanc et boutons dans le style du menu des commandes du jeu mobile (voir hud_mobile.cadre et hud_mobile.plaque)
OR = (255, 235, 4, 255); BLANC = (255, 255, 255, 255); GRIS = (128, 128, 128, 255); AIDE = (170, 170, 170, 255); ROUGE = (255, 80, 80, 255)
JAUNE = OR[:3]; CLAIR = (236, 236, 232)
NOIR = (0, 0, 0)                                  # fond des fenetres du menu : noir, avec l'opacite des fenetres des autres menus (hud_mobile.OPACITE_JEU, mesuree sur les fenetres du jeu)
LARG_CELLULE, ECART_CELLULES = 150.0, 10.0       # menu Commandes : largeur d'une case de touche et ecart entre les deux (a 900 px de haut, multiplies par k)
LARG_BARRE = 12.0                                 # barre de defilement
CURSEUR = (194, 297, 238, 328)                    # curseur dore des menus du jeu dans la feuille MenuTexture (x0, y0, x1, y1)
CROIX = (50, 291, 61, 301)                        # croix rouge du jeu (effacer une touche)
ICONE_RETOUR = (352, 224, 384, 256)               # icone du bouton retour du jeu (case 11 de la rangee d'icones)
LARG_SW, HAUT_SW = 46.0, 24.0                    # interrupteur Oui / Non : taille a 900 px de haut (multipliee par k)
TAILLE_JEU = 1.0                                  # echelle des textes en police du jeu (par rapport aux polices du systeme)
MSAA_CHOIX = (0, 2, 4, 8)
# editeur d'interface : noms des fenetres du jeu (fonctions Make_* de MenuPortItemTable ; 'boutons' = boutons et croix de l'ecran, 'msg' = dialogues) et regroupements de la liste « Interface a modifier ».
# Une fenetre du jeu n'y figure que si elle a un maillage a regler (RG.FENETRES_RETIREES : lancement du jeu, reseau, fenetres sans maillage) ; une fenetre inconnue va dans « Autres ».
NOMS_FENETRES = {'boutons': "Boutons et croix de l'écran", 'msg': 'Dialogues (messages)', 'YesNo': 'Oui / Non', 'Chapter': 'Titre du chapitre',
                 'RootMenu': 'Menu principal', 'LeftCharaList': 'Liste des personnages', 'TargetCharaList': 'Choix du personnage', 'Money': 'Argent', 'Pageing': 'Flèches de page',
                 'ItemList': 'Liste des objets', 'ItemInfo': "Infos de l'objet", 'OperationItemList': 'Actions sur les objets',
                 'Status': 'Statut du personnage', 'Chapter2Status': 'Chapitre 2 : statut', 'MemberShift': "Ordre de l'équipe", 'MemberShiftButton': "Ordre de l'équipe : boutons",
                 'NameButton': 'Divers : liste des boutons', 'BCInfo': 'Sauvegarde rapide', 'Senreki': 'Journal de bord', 'MonsterEncyclopedia': 'Bestiaire',
                 'CityMap': 'Carte : plan (ville, monde)', 'WorldLargeMap': 'Carte : grande carte du monde', 'MapButton': 'Carte : boutons Mode et retour', 'ShopMap': 'Carte : liste des boutiques',
                 'BattleUpStatus': "Combat : bandeau de l'équipe", 'BattleRoot': 'Combat : menu principal', 'BattleAction': 'Combat : actions', 'BattleTarget': 'Combat : cibles', 'BattleGo': 'Combat : en avant',
                 'BattleIM': 'Combat : objets et sorts', 'BattleInfo': "Combat : infos de l'équipe", 'BattleEnemyTarget': 'Combat : cible ennemie', 'BattlePartyTarget': 'Combat : cible alliée',
                 'BattleChangeButton': 'Combat : changement', 'BattleChangeInfo': 'Combat : infos du changement',
                 'ShopRoot': 'Boutique : menu', 'ShopBuy': 'Boutique : achat', 'ShopBuyInfo': "Boutique : infos de l'objet", 'ShopSellItemList': 'Boutique : vente', 'ShopSellItemInfo': 'Boutique : infos de vente',
                 'TorunekoMiseban': 'Boutique de Torneko', 'BankDeposit': 'Banque : dépôt', 'BankDraw': 'Banque : retrait', 'ChurchRoot': 'Église : menu', 'ChurchWork': 'Église : services',
                 'Casino_CoinShop': 'Casino : jetons', 'Casino_GiftList': 'Casino : cadeaux', 'Casino_GiftTarget': 'Casino : destinataire', 'Casino_Slot': 'Casino : machine à sous', 'Casino_Poker': 'Casino : poker',
                 'Casino_FightStadiumSelect': 'Casino : choix du stade', 'Casino_FightStadiumBet': 'Casino : pari du stade', 'Casino_FightStadiumCoin': 'Casino : jetons du stade', 'FightStadiumAbort': 'Casino : abandon du stade'}
GROUPES_INTERFACE = (("Écran tactile", ('boutons',)),
                     ("Dialogues", ('msg', 'YesNo', 'Chapter')),
                     ("Menu en jeu", ('RootMenu', 'LeftCharaList', 'TargetCharaList', 'Money', 'Pageing')),
                     ("Objets", ('ItemList', 'ItemInfo', 'OperationItemList')),
                     ("Équipe et statut", ('Status', 'Chapter2Status', 'MemberShift', 'MemberShiftButton')),
                     ("Divers", ('NameButton', 'BCInfo', 'Senreki', 'MonsterEncyclopedia')),
                     ("Cartes", ('CityMap', 'WorldLargeMap', 'MapButton', 'ShopMap')),
                     ("Combat", ('BattleUpStatus', 'BattleRoot', 'BattleAction', 'BattleTarget', 'BattleGo', 'BattleIM', 'BattleInfo', 'BattleEnemyTarget', 'BattlePartyTarget', 'BattleChangeButton', 'BattleChangeInfo')),
                     ("Boutiques et banque", ('ShopRoot', 'ShopBuy', 'ShopBuyInfo', 'ShopSellItemList', 'ShopSellItemInfo', 'TorunekoMiseban', 'BankDeposit', 'BankDraw')),
                     ("Églises", ('ChurchRoot', 'ChurchWork')),
                     ("Casino", ('Casino_CoinShop', 'Casino_GiftList', 'Casino_GiftTarget', 'Casino_Slot', 'Casino_Poker', 'Casino_FightStadiumSelect', 'Casino_FightStadiumBet', 'Casino_FightStadiumCoin', 'FightStadiumAbort')))
ENTETE = '#'                                                    # valeur d'une liste deroulante qui est un intertitre de groupe (« #Dialogues ») : jamais choisie, sautee par le curseur
SANS_EDITION = RG.FENETRES_RETIREES
DELAI_APPUI_LONG = float(os.environ.get('DQ_APPUI_LONG', '0.35'))      # panneau de l'editeur : appui maintenu sans bouger (secondes) avant qu'il se souleve ; en dessous, sans bouger, c'est un appui court (replier / deplier)
DELAI_DOUBLE_CLIC = float(os.environ.get('DQ_DOUBLE_CLIC', '0.40'))        # double clic sur la barre de titre : secondes entre la fin du premier appui et le debut du second
TOLERANCE_APPUI = 8.0                                           # deplacement (pixels) du pointeur, depuis le point d'appui sur la barre de titre du panneau, a partir duquel le panneau se deplace (en dessous : appui court)
CADRE_SELECTION = (255, 235, 130)                               # cadre jaune de l'element choisi dans l'apercu de l'editeur (le meme que celui des boutons de l'ecran : hud_mobile.py)
MOTS_MASQUE = ('Masquée', 'Masqué')                             # etiquette d'un element masque dans l'apercu de l'editeur : feminin (fenetre, croix), masculin (boutons)


class Pause:
    def __init__(self, jeu):
        self.J = jeu; self.ouvert = False; self.pile = []; self.sel = {}; self.capture = None; self.message = None
        self.zones = []; self.barres = {}; self.zones_val = {}; self.zones_col = 0.0; self.minis = {}; self.rep = None; self.veut_miniature = False; self.mini_tex = None; self.confirme = None
        self.cadre_panneau = None                          # (x0, y0, x1, y1) du cadre dessine a la derniere image (placement des boutons : un clic hors du cadre saisit un bouton)
        self.zones_def = {}                                # ligne -> (x0, y0, x1, y1) du bouton « valeur par defaut » des curseurs
        self.glisse = None; self.saisie = None            # curseur maintenu par la souris (numero de ligne) ; valeur en cours de saisie [ligne, texte]
        self.deroule = None; self.zones_pop = []          # liste deroulante ouverte [ligne, valeur survolee] ; zones de ses valeurs (x0, y0, x1, y1, numero)
        self.pos_sw = {}; self.t_sw = time.time(); self.dt_sw = 0.0         # interrupteurs : position du bouton (0 = Non, 1 = Oui) par libelle, pour l'animation
        self._pol = None; self._caps = {}                 # familles de la police du jeu (None : pas encore cherchee) ; hauteur des capitales par taille

        self.rep_pos = None                               # (ecran, ligne) sur lesquels la repetition d'une touche maintenue a commence
        self.debut = {}; self.vu_sel = {}; self.barre = None; self.glisse_barre = None      # defilement : premiere ligne visible par ecran, derniere selection vue (la vue la suit quand elle change), barre dessinee, prise du curseur de la barre
        self.zone_ret = None; self.sur_ret = False; self.zones_eff = {}                      # bouton retour (x0, y0, x1, y1), pointeur dessus ; (ligne, colonne) -> croix « effacer la touche »
        self._pil = {}; self._img = {}                    # feuilles du jeu (PIL) et textures des sprites du menu
        self.mode_souris = False; self.pos_souris = None   # selection a la souris (encadrement jaune) ou au clavier (curseur dore) ; derniere position du pointeur
        self.popup = None; self.zones_popup = []                                          # fenetre modale Oui / Non : {'titre', 'detail', 'oui', 'sel' (0 Oui, 1 Non)} ; zones de ses boutons
        self.plie = False; self.zone_plier = None; self.tt = None                          # editeur d'interface : panneau replie ; barre de titre (plier / deplier) ; ligne survolee depuis (cle, instant) pour l'infobulle
        self.action_etat = 'creer'; self.etat_suppr = None                                  # menu des etats : action choisie (creer, charger, supprimer) ; emplacement dont la suppression est a confirmer
        self.barre_liste = None; self.glisse_liste = None; self.liste_top = None; self.liste_cur_vu = None      # liste deroulante : barre de defilement, prise du curseur, premiere valeur visible
        self.cible = 'boutons'; self.drag = None; self.rect_apercu = None           # editeur d'interface : element modifie ('boutons', 'msg' ou nom Make_* d'une fenetre du jeu) ; deplacement en cours (x, y de depart, decalage de depart)
        self.pan_pos = None; self.pan_appui = None; self.pan_clic_t = 0.0             # editeur d'interface, panneau deplacable : coin haut droit (x, y) apres un deplacement (le temps de la session ; None = position d'origine, calculee d'apres l'interface choisie) ;
        self.cadre_liste = None; self.pan_dim = None                                    # appui en cours sur la barre de titre {t0, x, y, dx, dy, long (souleve : suit le pointeur), double} ; instant du dernier appui court (double clic) ; cadre de la liste deroulante ouverte

    def _et(self, texte, taille, couleur=BLANC):
        """Etiquette en police du jeu (GMaruGoPro-M, cache/ui_font.otf, enregistree au premier appel) ; a defaut, les polices du systeme."""
        if self._pol is None:
            self._pol = ()
            f = os.path.join(self.J.args.cache, 'ui_font.otf')
            if os.path.exists(f):
                try: pyglet.font.add_file(f); self._pol = ('FOT-GMaruGo Pro', 'FOT-GMaruGo Pro M', 'GMaruGoPro-M')
                except Exception as ex: print('police du jeu non chargee :', ex, flush=True)
        return self.J._etiq(texte, taille * (1.0 if not self._pol else TAILLE_JEU), couleur, self._pol)

    # ---- sprites des menus du jeu
    def _feuille(self, nom):
        """Feuille de texture du jeu (cache/<nom>, PIL RGBA) ; None si elle est absente."""
        f = self._pil.get(nom)
        if f is None:
            try:
                from PIL import Image
                f = Image.open(os.path.join(self.J.args.cache, nom)).convert('RGBA')
            except Exception: f = False
            self._pil[nom] = f
        return f or None

    def _tex_pil(self, im, cle):
        """Texture (filtre lineaire) d'une image PIL RGBA, gardee sous `cle`."""
        t = self._img.get(cle)
        if t is None:
            a = np.asarray(im.convert('RGBA'))
            t = pyglet.image.ImageData(im.width, im.height, 'RGBA', np.ascontiguousarray(a[::-1]).tobytes(), pitch=im.width * 4).get_texture()
            gl.glBindTexture(t.target, t.id); gl.glTexParameteri(t.target, gl.GL_TEXTURE_MIN_FILTER, gl.GL_LINEAR); gl.glTexParameteri(t.target, gl.GL_TEXTURE_MAG_FILTER, gl.GL_LINEAR)
            self._img[cle] = t
        return t

    def _tex_decoupe(self, cle, nom, boite):
        """Texture d'un morceau de la feuille `nom` (boite x0, y0, x1, y1), couleur des pixels transparents propagee d'un pixel (pas de liseré sombre au filtrage) ; None si la feuille manque."""
        t = self._img.get(cle)
        if t is None:
            f = self._feuille(nom)
            if f is None: return None
            from PIL import Image
            t = self._tex_pil(Image.fromarray(HD._dilater(np.array(f.crop(boite)), 1)), cle)
        return t

    @staticmethod
    def _melange():
        """Les formes de pyglet coupent le melange alpha a la fin de leur dessin : on le remet avant une texture."""
        gl.glEnable(gl.GL_BLEND); gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)

    def _curseur(self, x, yc, haut):
        """Curseur dore des menus du jeu (pointe vers la droite), de `haut` pixels de haut, a gauche en x, centre verticalement en yc ; il reste fixe."""
        t = self._tex_decoupe('curseur', 'ui_MenuTexture.png', CURSEUR)
        dx = 0.0
        if t is None:
            pyglet.shapes.Triangle(x, yc + haut / 2, x, yc - haut / 2, x + haut * 0.7, yc, color=JAUNE).draw(); return
        e = haut / float(CURSEUR[3] - CURSEUR[1]); self._melange(); t.blit(x + dx, yc - haut / 2, width=(CURSEUR[2] - CURSEUR[0]) * e, height=haut)

    def _bouton_retour(self, x, y, w, h, pousse):
        """Bouton retour des menus du jeu : fenetre-bouton de la feuille Button (neuf morceaux, 32 px d'angle reduits de moitie, version enfoncee a 96 px a droite) et son icone fleche de retour."""
        from PIL import Image
        cle = ('retour', int(w), int(h), bool(pousse)); t = self._img.get(cle); w, h = int(round(w)), int(round(h))
        if t is None:
            f = self._feuille('ui_Button.png')
            if f is not None:
                src = f.crop((96 if pousse else 0, 0, 96 + (96 if pousse else 0), 96)); c = max(2, int(round(w / 4.0)))
                im = Image.new('RGBA', (w, h)); xs = (0, c, w - c, w); ys = (0, c, h - c, h); sx = (0, 32, 64, 96)
                for i in range(3):
                    for j in range(3): im.paste(src.crop((sx[i], sx[j], sx[i + 1], sx[j + 1])).resize((xs[i + 1] - xs[i], ys[j + 1] - ys[j]), Image.LANCZOS), (xs[i], ys[j]))
                t = self._tex_pil(im, cle)
        ic = self._tex_decoupe('ic_retour', 'ui_MenuTexture.png', ICONE_RETOUR)
        self._melange()
        if t is not None: t.blit(x, y)
        else: self._plaque(x, y, w, h, w / 64.0, pousse)
        if ic is not None:
            e = 62.4 / 64.0 * w; ic.blit(x + (w - e) / 2, y + (h - e) / 2, width=e, height=e)

    # ---- ouverture / fermeture
    def ouvrir(self, page=None):
        if self.ouvert: return
        self.ouvert = True; self.pile = ['racine']; self.sel = {}; self.capture = None; self.message = None; self.confirme = None; self.popup = None; self.plie = False; self.tt = None; self.debut = {}; self.vu_sel = {}; self.glisse_barre = None
        self.veut_miniature = True; self.minis = {}; self.rep = None; self.glisse = None; self.saisie = None; self.deroule = None
        self.mode_souris = False; self.pos_souris = getattr(self.J, 'souris', None); self.drag = None; self.pan_appui = None
        if page: self.pile = [page]; self.sel[page] = 2           # ouvre directement cette page (question de sortie : « Non » preselectionne, « Non » ou Echap ferment tout)
        self.J.pause_jeu(True)

    def fermer(self):
        if not self.ouvert: return
        self.ouvert = False; self.capture = None; self.popup = None; self.glisse = None; self.saisie = None; self.deroule = None; self.J.reg.enregistrer(); self.J.pause_jeu(False)
        if self.mini_tex is not None:
            try: self.mini_tex.delete()
            except Exception: pass
            self.mini_tex = None

    @property
    def ecran(self): return self.pile[-1]

    def retour(self):
        if self.ecran == 'interface': self.J.reg.enregistrer(); self.drag = None; self.pan_appui = None                # fin de l'edition de l'interface
        if len(self.pile) > 1: self.pile.pop()
        else: self.fermer()

    # ---- entrees des ecrans : liste de dicts {'t': 'act'|'choix'|'curs'|'touche'|'sep', 'l': libelle, 'v': valeur affichee, 'ok', 'moins', 'plus', 'off'}
    def _entrees(self):
        return getattr(self, '_e_' + self.ecran)()

    def _aller(self, nom):
        def va():
            self.pile.append(nom)
            if nom in ('quitter', 'titre'): self.sel[nom] = 2        # « Non » preselectionne
        return va

    def _e_racine(self):
        return [dict(t='act', l='Reprendre', ok=self.fermer),
                dict(t='act', l='États', ok=self._aller('etats'), sous=True),
                dict(t='act', l='Affichage', ok=self._aller('affichage'), sous=True),
                dict(t='act', l='Son', ok=self._aller('son'), sous=True),
                dict(t='act', l='Texte et défilement', ok=self._aller('texte'), sous=True),
                dict(t='act', l='Commandes', ok=self._aller('commandes'), sous=True),
                dict(t='act', l="Revenir à l'écran titre", ok=self._aller('titre'))]          # (confirmation, puis retour au titre : le seul chemin de retour au titre du jeu ; la question « quitter l'application » n'est posee que par le menu de depart, page 'quitter')

    def _choix(self, label, valeurs, get, set_, off=False, note=None):
        """Entree a valeurs : Oui / Non = interrupteur (valider ou cliquer le bascule ; gauche = Non, droite = Oui) ; tout autre choix, meme a deux valeurs = liste deroulante
        (valider ou cliquer l'ouvre ; gauche / droite passent a la valeur precedente / suivante). `note` : fonction donnant un texte rouge affiche sous la valeur (ou '')."""
        sw = len(valeurs) == 2 and all(isinstance(v, bool) for v in valeurs)
        def pas(d):
            i = (valeurs.index(get()) + d) % len(valeurs) if get() in valeurs else 0
            i = self._hors_entete(valeurs, i, d)
            set_(valeurs[i])
        def fixer(x):
            if get() != x: set_(x)
        if sw: moins, plus, ok = (lambda: fixer(False)), (lambda: fixer(True)), (lambda: set_(not get()))
        else: moins, plus, ok = (lambda: pas(-1)), (lambda: pas(1)), (lambda: pas(1))
        return dict(t='choix', l=label, vals=valeurs, v=lambda: self._nom_valeur(label, get()), moins=moins, plus=plus, ok=ok, off=off, get=get, set=set_, sw=sw, liste=not sw, note=note)

    def _valeurs(self, en): return en['vals']

    @staticmethod
    def _entete(v):
        """Vrai si la valeur d'une liste deroulante est un intertitre de groupe (« #Dialogues »)."""
        return isinstance(v, str) and v[:1] == ENTETE

    def _hors_entete(self, vals, i, d):
        """Indice de la premiere valeur qui n'est pas un intertitre, a partir de i dans le sens de d."""
        n = len(vals)
        for _ in range(n):
            if not self._entete(vals[i]): break
            i = (i + (1 if d >= 0 else -1)) % n
        return i

    def _nom_valeur(self, label, v):
        if label == 'Interface à modifier': return self.nom_cible(v)
        n = self.noms.get(label, {}).get(v)
        if n is not None: return n
        if isinstance(v, bool): return 'Oui' if v else 'Non'
        return '%d x %d' % v if isinstance(v, tuple) else str(v)

    def _curs(self, label, get, appliquer, mini, maxi, pas, pas_f, fmt, mult=1.0, defaut=None):
        """Curseur numerique de `mini` a `maxi` (valeurs arrondies a `pas`, fleches : `pas_f`). Cliquer sur la valeur ou valider permet de la saisir au clavier : `mult` = facteur entre la valeur
        interne et celle qui est affichee et saisie (100 pour des pourcentages). `defaut` : valeur d'origine du reglage (bouton « valeur par defaut » a gauche du curseur, touche Suppr)."""
        def pose(v): appliquer(min(maxi, max(mini, round(round(v / pas) * pas, 4))))
        d = dict(t='curs', l=label, v=lambda: fmt(get()), frac=lambda: (get() - mini) / (maxi - mini), moins=lambda: pose(get() - pas_f), plus=lambda: pose(get() + pas_f),
                 fixe=lambda f: pose(mini + f * (maxi - mini)), saisie=lambda x: pose(x / mult), brut=lambda: ('%g' % round(get() * mult, 2)))
        if defaut is not None: d['defaut'] = lambda: pose(defaut); d['est_defaut'] = lambda: abs(get() - defaut) < pas / 2
        return d

    noms = {
        'Shader': {0: 'Aucun', 1: 'EPX x8', 4: 'Pixel perfect'},
        'Anticrénelage': {0: 'Aucun', 2: 'x2', 4: 'x4', 8: 'x8'},
        'Suréchantillonnage': {1.0: 'Aucun', 1.5: 'x1,5', 2.0: 'x2'},
        'Action': {'creer': 'Créer un état', 'charger': 'Charger un état', 'supprimer': 'Supprimer un état'},
    }
    noms['Vitesse du texte'] = {0.5: 'Très lent', 1.0: 'Lent', 2.0: 'Assez lent', 4.0: 'Normal (jeu)', 8.0: 'Rapide', 16.0: 'Très rapide', 4000.0: 'Instantané'}
    noms['Vitesse de défilement'] = {0: '1 (rapide)', 1: '2', 2: '3', 3: '4 (lent)'}

    def _e_affichage(self):
        J, R = self.J, self.J.reg
        def set_(k, f=None):
            def s(v):
                R[k] = v
                if f: f(v)                 # (les reglages sont enregistres a la fermeture du menu)
            return s
        return [self._choix('Plein écran', [False, True], lambda: J.est_plein, set_('plein_ecran', J.regler_plein_ecran)),
                self._choix('Résolution', J.resolutions(), J.resolution_courante, lambda v: (J.regler_resolution(v), R.__setitem__('resolution', list(v)))),
                self._choix('Shader', list(RG.MODES_SPRITES), lambda: J.mode, set_('mode_sprites', J.regler_mode)),
                self._choix('Lissage des textures', [True, False], lambda: J.lissage, set_('lissage', J.regler_lissage)),
                self._curs('Distance caméra', lambda: round(100.0 / J.zoom), J.regler_distance, 50.0, 200.0, 5.0, 10.0, lambda v: '%d %%' % round(v), 1.0, defaut=float(RG.DEFAUT['distance_camera'])),
                self._choix('Centrer la caméra sur le joueur', [True, False], lambda: R['camera_centree'], lambda v: R.__setitem__('camera_centree', v)),
                self._curs('Effet de vignetage', lambda: R['vignette'], lambda v: R.__setitem__('vignette', v), 0.0, 1.0, 0.01, 0.05, lambda v: '%d %%' % round(v * 100), 100.0, defaut=RG.DEFAUT['vignette']),
                self._choix('Anticrénelage', list(MSAA_CHOIX), lambda: R['msaa'], set_('msaa'), note=lambda: 'Limité à x%d par cette carte graphique' % J.post.max_msaa if J.post.max_msaa is not None and R['msaa'] > J.post.max_msaa else ''),
                self._choix('Suréchantillonnage', [1.0, 1.5, 2.0], lambda: R['echelle_rendu'], set_('echelle_rendu')),
                self._curs('Netteté', lambda: R['nettete'], lambda v: R.__setitem__('nettete', v), 0.0, 1.0, 0.05, 0.1, lambda v: '%d %%' % round(v * 100), 100.0, defaut=RG.DEFAUT['nettete']),
                self._curs('Luminosité', lambda: R['luminosite'], lambda v: R.__setitem__('luminosite', v), 0.5, 1.5, 0.05, 0.1, lambda v: '%d %%' % round(v * 100), 100.0, defaut=RG.DEFAUT['luminosite']),
                dict(t='act', l='Interface', ok=self._aller('interface'), sous=True)]          # (editeur de l'interface a l'ecran : boutons, dialogues, fenetres du jeu)

    # ---- editeur d'interface : boutons de l'ecran, fenetre de dialogue et fenetres du jeu (taille, position, affichage)
    def cibles(self):
        """Valeurs de la liste « Interface a modifier » : les elements modifiables par groupe (GROUPES_INTERFACE), chaque groupe precede de son intertitre (« #Dialogues ») ; seules les fenetres du jeu qui ont une mise en page y figurent."""
        noms = self.J.noms_fenetres(); out = []; vus = set()
        for titre, ids in GROUPES_INTERFACE:
            l = [i for i in ids if i in ('boutons', 'msg') or i in noms]; vus.update(ids)
            if l: out += [ENTETE + titre] + l
        reste = sorted((n for n in noms if n not in vus and n not in RG.FENETRES_RETIREES), key=lambda n: n.lower())
        return out + ([ENTETE + 'Autres'] + reste if reste else [])

    def nom_cible(self, c):
        return c[len(ENTETE):] if self._entete(c) else NOMS_FENETRES.get(c, c)

    def _ov(self):
        """[taille, decalage x, decalage y] de l'element choisi (fenetre du jeu)."""
        return self.J.reg['interface_fenetres'].get(self.cible) or list(RG.FENETRE_DEFAUT)

    def _poser_ov(self, i, v):
        d = dict(self.J.reg['interface_fenetres']); o = list(self._ov()); o[i] = v
        if all(abs(a - b) < 1e-6 for a, b in zip(o, RG.FENETRE_DEFAUT)): d.pop(self.cible, None)
        else: d[self.cible] = [round(o[0], 4), round(o[1], 4), round(o[2], 4)]
        self.J.reg['interface_fenetres'] = d

    def _poser_cible(self, v):
        """Interface a modifier choisie : pour les dialogues, un nouveau message d'essai au hasard."""
        if v != self.cible and v == 'msg': self.J.nouvel_echantillon()
        self.cible = v

    def _visible(self, c):
        """L'interface c est-elle affichee a l'ecran ? Boutons et croix : reglage 'boutons' ; fenetre du jeu : absente de la liste des interfaces masquees. Chaque interface a son propre reglage."""
        return bool(self.J.reg['boutons']) if c == RG.CIBLE_ECRAN else c not in self.J.reg['interface_masquees']

    def _poser_visible(self, c, v):
        R = self.J.reg
        if c == RG.CIBLE_ECRAN: R['boutons'] = v; return
        l = [n for n in R['interface_masquees'] if n != c]
        if not v: l.append(c)
        R['interface_masquees'] = l

    def _e_interface(self):
        """Page Interface : d'abord l'interface a modifier (liste par groupes), puis son affichage (propre a chaque interface), puis ses reglages."""
        R = self.J.reg; c = self.cible
        e = [self._choix('Interface à modifier', self.cibles(), lambda: self.cible, self._poser_cible),
             self._choix("Afficher cette interface à l'écran", [True, False], lambda: self._visible(self.cible), lambda v: self._poser_visible(self.cible, v))]
        if c == RG.CIBLE_ECRAN:
            e.append(self._curs('Taille des boutons', lambda: R['boutons_taille'], lambda v: R.__setitem__('boutons_taille', v), 0.5, 2.0, 0.05, 0.1, lambda v: '%d %%' % round(v * 100), 100.0, defaut=RG.DEFAUT['boutons_taille']))
            e.append(self._choix('Afficher la croix', [True, False], lambda: R['croix'], lambda v: R.__setitem__('croix', v)))
            e.append(self._curs('Taille de la croix', lambda: R['croix_taille'], lambda v: R.__setitem__('croix_taille', v), 0.5, 2.0, 0.05, 0.1, lambda v: '%d %%' % round(v * 100), 100.0, defaut=RG.DEFAUT['croix_taille']))
        else:
            e += [self._curs('Taille', lambda: self._ov()[0], lambda v: self._poser_ov(0, v), 0.5, 2.0, 0.05, 0.1, lambda v: '%d %%' % round(v * 100), 100.0, defaut=RG.FENETRE_DEFAUT[0]),
                  self._curs('Position horizontale', lambda: self._ov()[1], lambda v: self._poser_ov(1, v), -0.5, 0.5, 0.01, 0.05, lambda v: '%+d %%' % round(v * 100), 100.0, defaut=RG.FENETRE_DEFAUT[1]),
                  self._curs('Position verticale', lambda: self._ov()[2], lambda v: self._poser_ov(2, v), -0.5, 0.5, 0.01, 0.05, lambda v: '%+d %%' % round(v * 100), 100.0, defaut=RG.FENETRE_DEFAUT[2])]
        e += [self._choix('Aimantation à la grille', [True, False], lambda: R['boutons_aimant'], lambda v: R.__setitem__('boutons_aimant', v)),            # (pour toutes les interfaces)
              self._choix('Afficher la grille', [True, False], lambda: R['grille_edition'], lambda v: R.__setitem__('grille_edition', v))]
        cette = dict(t='act', l='Rétablir cette interface', ok=self._remettre_cette)
        cette['aide'] = ("Remet les boutons et la croix comme dans le jeu : affichage, tailles et positions   Les fenêtres du jeu ne changent pas" if c == RG.CIBLE_ECRAN
                         else "Remet cette fenêtre comme dans le jeu : affichage, taille et position   Les autres interfaces ne changent pas")
        toutes = dict(t='act', l='Rétablir toutes les interfaces', ok=self._tout_remettre, aide="Remet toutes les interfaces comme dans le jeu, ainsi que la grille, l'aimantation et la place de ce panneau")
        e += [cette, toutes, dict(t='act', l='Terminer', ok=self.retour)]
        return e

    def _remettre_cette(self):
        """« Rétablir cette interface » : l'interface choisie revient entièrement à son état d'origine (RG.Reglages.remettre_interface : position, taille, affichage et toutes ses options, et elle seule).
        Rien d'autre à faire : l'aperçu et le jeu relisent les réglages à chaque image."""
        self.J.reg.remettre_interface(self.cible)

    def _tout_remettre(self):
        """« Rétablir toutes les interfaces » : toutes les interfaces et les options de l'éditeur (grille, aimantation) à leur défaut (RG.Reglages.remettre_interfaces), et le panneau reprend sa place d'origine."""
        self.J.reg.remettre_interfaces(); self.pan_pos = None

    def _poser_son(self, cle, cat=None):
        """Reglage de son (interrupteur ou volume) : enregistre la valeur, l'applique tout de suite aux sons en cours, et pour un volume fait entendre un bruitage d'essai (la musique, elle, joue pendant la page)."""
        def poser(v):
            self.J.reg[cle] = v; self.J.appliquer_mixage()
            if cat and not isinstance(v, bool): self.J.apercu_son(cat)
        return poser

    def _e_son(self):
        """Interrupteur general, volume general, puis une section par categorie de sons (son.CATEGORIES) : un interrupteur et un volume chacune."""
        J, R = self.J, self.J.reg
        def sw(lib, cle, aide):
            d = self._choix(lib, [True, False], lambda: R[cle], self._poser_son(cle)); d['aide'] = aide; return d
        def vol(lib, cle, cat, aide):
            d = self._curs(lib, lambda: R[cle], self._poser_son(cle, cat), 0.0, 1.0, 0.01, 0.05, lambda v: '%d %%' % round(v * 100), 100.0, defaut=RG.DEFAUT[cle]); d['aide'] = aide; return d
        general = self._choix('Son', [True, False], lambda: J.son.actif, lambda v: (J.regler_son(v), R.__setitem__('son', v)))
        general['aide'] = 'Coupe ou remet tout le son du jeu   Le son reprend ici pour que tu entendes tes réglages ; le jeu, lui, reste en pause'
        return [dict(t='sep', l='Général'), general,
                vol('Volume général', 'volume_general', 'general', 'Multiplie tous les autres volumes   Se combine avec le volume réglé dans la fenêtre Paramètres du jeu'),
                dict(t='sep', l='Musique'),
                sw('Musique', 'musique_active', 'Musique de fond des cartes, villes et combats   Coupée, elle continue en silence et reprend là où elle en est'),
                vol('Volume de la musique', 'volume_musique', 'musique', 'La musique en cours change tout de suite'),
                dict(t='sep', l='Jingles et fanfares'),
                sw('Jingles et fanfares', 'jingles_actifs', 'Morceaux courts joués une seule fois (le reste de la musique est réglé au-dessus)'),
                vol('Volume des jingles', 'volume_jingles', 'jingles', 'Se fait entendre à la prochaine fanfare'),
                dict(t='sep', l='Bruitages'),
                sw('Bruitages', 'bruitages_actifs', 'Effets sonores du jeu : combats, sorts, objets, pas...   Sans les sons de l\'interface (réglés plus bas)'),
                vol('Volume des bruitages', 'volume_bruitages', 'effets', 'Un bruitage d\'essai est joué quand tu changes la valeur'),
                dict(t='sep', l='Interface'),
                sw('Sons de l\'interface', 'interface_active', 'Bip des pages de message, validation des menus et des boutons'),
                vol('Volume de l\'interface', 'volume_interface', 'interface', 'Un son de bouton est joué quand tu changes la valeur')]

    def _e_texte(self):
        """Dialogues : vitesse d'affichage du texte. Combats : defilement automatique des messages (interrupteur) et sa vitesse. Le defilement ne concerne que les combats : dans les dialogues normaux, on passe toujours chaque page a la main."""
        J, R = self.J, self.J.reg
        vt = self._choix('Vitesse du texte', list(RG.VITESSES_TEXTE), lambda: R['vitesse_texte'], lambda v: (R.__setitem__('vitesse_texte', v), J.appliquer_texte()))
        vt['aide'] = 'Vitesse d\'écriture des dialogues (lettres par image du jeu)   « Normal (jeu) » : comme dans le jeu d\'origine'
        auto = self._choix('Défilement automatique', [True, False], lambda: J.defilement_actuel()[0], lambda v: J.regler_defilement(auto=v))
        auto['aide'] = 'Combats seulement : les messages défilent seuls   Désactivé : on passe chaque message à la main (c\'est le 5e cran de « Vitesse texte » dans Divers > Paramètres du jeu)   Les dialogues hors combat ne défilent jamais seuls'
        vit = self._choix('Vitesse de défilement', [0, 1, 2, 3], lambda: J.defilement_actuel()[1], lambda v: J.regler_defilement(vitesse=v), off=not J.defilement_actuel()[0])
        vit['aide'] = 'Combats seulement : crans 1 à 4 de « Vitesse texte » dans Divers > Paramètres du jeu (attente de 0,4 / 0,7 / 1,1 / 1,4 s avant le message suivant)   Sans effet quand le défilement automatique est désactivé'
        retab = dict(t='act', l='Rétablir le réglage du jeu', ok=J.retablir_defilement)
        retab['aide'] = 'Combats : reprend la vitesse des messages enregistrée dans la sauvegarde (fenêtre Paramètres du jeu)'
        return [dict(t='sep', l='Dialogues'), vt, dict(t='sep', l='Combats'), auto, vit, retab]

    def _touche(self, act):
        """Ligne d'une action au clavier : deux cases (touche principale, secondaire) ; Suppr efface la case choisie, le bouton rond (ou Debut) remet les touches d'origine."""
        R = self.J.reg
        def defaut():
            for a in R.action_par_defaut(act): self._info('Une touche d\'origine est retirée de « %s ».' % dict(RG.ACTIONS)[a])
            R.enregistrer()
        return dict(t='touche', l=dict(RG.ACTIONS)[act], act=act, v=[RG.nom_touche(n) for n in R['touches'][act]], defaut=defaut, est_defaut=lambda: R.est_par_defaut(act))

    def _e_commandes(self):
        """Cinq sections (intertitres) : deplacement (touches), camera (touches), vitesses (marche, camera, transition, touche et vitesse de l'accelerateur), actions du jeu, autres (touche speciale, infos) ; puis le retablissement des touches."""
        R = self.J.reg; T = self._touche
        def vit(lib, cle, mini, maxi, f=None):
            return self._curs(lib, lambda: R[cle], lambda v: (R.__setitem__(cle, v), f(v) if f else None), mini, maxi, 0.05, 0.1, lambda v: 'x%.2f' % v, 1.0, defaut=RG.DEFAUT[cle])
        modif = T('modif'); modif['aide'] = 'Avec un chiffre : charge un état   Avec une touche de caméra : remet la caméra à zéro'
        accel = T('accel'); accel['aide'] = "Maintenue : accélère la marche et la caméra (réglage « Vitesse de l'accélérateur »)   " + self.AIDE_TOUCHE
        vit_acc = vit("Vitesse de l'accélérateur", 'vitesse_accel', 1.0, 2.0); vit_acc['aide'] = "Multiplie la vitesse de marche et de caméra tant que la touche d'accélérateur est tenue"
        return [dict(t='sep', l='Déplacement'),
                T('haut'), T('bas'), T('gauche'), T('droite'),
                dict(t='sep', l='Caméra'),
                T('cam_haut'), T('cam_bas'), T('cam_gauche'), T('cam_droite'),
                dict(t='sep', l='Vitesses'),
                vit('Vitesse de marche', 'vitesse_marche', 0.5, 2.0),
                vit('Vitesse de caméra', 'vitesse_camera', 0.5, 2.0),
                vit('Vitesse de transition', 'vitesse_fondu', 0.5, 2.0, self.J.regler_fondu),
                accel, vit_acc,
                dict(t='sep', l='Actions du jeu'),
                T('A'), T('menu'), T('B'), T('carte'), T('discussion'),
                dict(t='sep', l='Autres'),
                modif, T('infos'),
                dict(t='act', l='Rétablir les touches par défaut', ok=lambda: (R.touches_par_defaut(), R.enregistrer()))]

    def _chemin_etat(self, n): return self.J.chemin_etat(n)

    @staticmethod
    def _date_fr(date):
        """'2026-10-31 19:21:05' -> '31/10/2026  19:21:05' (nom d'un etat : sa date et son heure d'enregistrement)."""
        try: return time.strftime('%d/%m/%Y  %H:%M:%S', time.strptime(date, '%Y-%m-%d %H:%M:%S'))
        except Exception: return ''

    @staticmethod
    def _lieu_lisible(inf):
        """Lieu de l'etat seulement s'il parle a un joueur (le nom technique d'une carte, comme « mak1f1 », n'est pas montre)."""
        return inf.get('lieu', '') if inf.get('lieu') in ('Carte du monde', 'Combat') else ''

    def _e_etats(self):
        """Etats instantanes : une liste deroulante choisit l'action (creer, charger, supprimer) appliquee a l'emplacement valide ; la suppression passe par une fenetre de confirmation."""
        R = self.J.reg; act = self.action_etat
        e = [self._choix('Action', ['creer', 'charger', 'supprimer'], lambda: self.action_etat, lambda v: setattr(self, 'action_etat', v))]
        for n in range(1, NB_ETATS + 1):
            inf = self.J.infos_etat(n)
            if inf: lib = self._date_fr(inf[0].get('date')) or 'Sans date'; val = self._lieu_lisible(inf[0])
            else: lib = '— vide —'; val = ''
            if act == 'creer': e.append(dict(t='slot', l=lib, v=val, n=n, off=False, ok=(lambda n=n: self._sauver(n))))
            elif act == 'charger': e.append(dict(t='slot', l=lib, v=val, n=n, off=inf is None, ok=(lambda n=n: self._charger(n))))
            else: e.append(dict(t='slot', l=lib, v=val, n=n, off=inf is None, ok=(lambda n=n: self._demander_suppression(n))))
        return e

    def _e_quitter(self):
        return [dict(t='sep', l='En êtes-vous sûr ?'), dict(t='act', l='Oui', ok=self.J.quitter), dict(t='act', l='Non', ok=self.retour)]

    def _e_titre(self):
        return [dict(t='sep', l='En êtes-vous sûr ?'), dict(t='act', l='Oui', ok=self._vers_titre), dict(t='act', l='Non', ok=self.retour)]

    def _vers_titre(self):
        """« Oui » : le menu se ferme (le jeu reprend) puis le moteur revient a son ecran-titre."""
        self.fermer(); self.J.retour_titre()

    # ---- actions
    def _info(self, texte, erreur=False): self.message = (texte, time.time(), erreur)

    def _sauver(self, n):
        try:
            self.J.sauver_etat(n, self.J._png_miniature(self.mini_tex))
            self.minis.pop(n, None); self._info('État enregistré dans l\'emplacement %d.' % n)
        except Exception as ex:
            self._info('Impossible d\'enregistrer l\'état : %r' % (ex,), True)

    def _charger(self, n):
        try:
            self.J.charger_etat(n); self.fermer()
        except Exception as ex:
            self._info('Impossible de charger l\'état : %r' % (ex,), True)

    def _demander_suppression(self, n):
        """Supprimer l'etat n : une fenetre modale demande confirmation (Non preselectionne)."""
        inf = self.J.infos_etat(n); date = self._date_fr(inf[0].get('date')).strip() if inf else ''
        self.popup = dict(titre="Supprimer l'état %d ?" % n, detail=date, oui=lambda: self._supprimer(n), sel=1)

    def _touche_popup(self, symbol, act):
        K = pyglet.window.key; p = self.popup
        if symbol in (K.ESCAPE, K.BACKSPACE) or act == 'B': self.popup = None
        elif symbol in (K.LEFT, K.RIGHT, K.UP, K.DOWN) or act in ('gauche', 'droite', 'haut', 'bas'): p['sel'] = 1 - p['sel']
        elif symbol in (K.RETURN, K.ENTER, K.SPACE) or act == 'A': self._valider_popup(p['sel'] == 0)

    def _valider_popup(self, oui):
        p, self.popup = self.popup, None
        if oui and p and p.get('oui'): p['oui']()

    def _supprimer(self, n):
        try:
            os.remove(self.J.chemin_etat(n))
            t = self.minis.pop(n, None)
            if t is not None:
                try: t.delete()
                except Exception: pass
            self._info('État %d supprimé.' % n)
        except Exception as ex:
            self._info('Impossible de supprimer l\'état : %r' % (ex,), True)

    # ---- touches clavier
    def touche(self, symbol, modifiers=0):
        """True si la touche est consommee (le menu est ouvert)."""
        K = pyglet.window.key; R = self.J.reg
        self.mode_souris = False                                  # une touche : retour a la selection au clavier (curseur dore)
        if self.capture is not None: self._capturer(symbol); return True
        if self.saisie is not None: self._touche_saisie(symbol); return True
        act = R.action_de(symbol)
        if self.popup is not None: self._touche_popup(symbol, act); return True
        if self.ecran == 'interface' and symbol == K.TAB: self.plie = not self.plie; return True              # (editeur : plier / deplier le panneau)
        if self.ecran == 'interface' and self.plie and not (symbol in (K.ESCAPE, K.BACKSPACE) or act == 'B'): return True
        if self.deroule is not None: self._touche_liste(symbol, act); return True
        if symbol in (K.ESCAPE, K.BACKSPACE) or act == 'B': self.retour(); return True
        if act == 'infos': self.J.regler_infos(not self.J.aide); R['infos'] = self.J.aide; return True          # (la touche des infos a l'ecran se regle dans Commandes)
        if symbol == K.DELETE: self._suppr(); return True
        if symbol == K.HOME: self._defaut(); return True
        if symbol in (K.UP,) or act == 'haut': self._bouger(-1); self._repeter(symbol, 'v', -1)
        elif symbol in (K.DOWN,) or act == 'bas': self._bouger(1); self._repeter(symbol, 'v', 1)
        elif symbol in (K.LEFT,) or act == 'gauche': self._regler(-1); self._repeter(symbol, 'h', -1)
        elif symbol in (K.RIGHT,) or act == 'droite': self._regler(1); self._repeter(symbol, 'h', 1)
        elif symbol in (K.RETURN, K.ENTER, K.SPACE) or act == 'A': self._valider()
        return True

    def _repeter(self, symbol, sens, d):
        """Une direction est enfoncee : elle se repetera (maj) tant qu'elle est maintenue, sur la ligne et l'ecran ou elle a commence."""
        t = time.time(); self.rep = (symbol, t, t, sens, d); self.rep_pos = (self.ecran, self.sel.get(self.ecran, 0))

    def maj(self):
        """Repetition des directions maintenues, appui long sur le panneau de l'editeur (appelee a chaque image). Page Son : les sons jouent (le jeu est arrete) pour qu'on entende les volumes qu'on regle."""
        S = self.J.son; ecoute = self.ecran == 'son'
        if ecoute != S.ecoute: S.ecouter(ecoute)
        if ecoute: S.tick()
        a = self.pan_appui
        if a is not None and not (a['long'] or a['double']) and time.time() - a['t0'] >= DELAI_APPUI_LONG: a['long'] = True          # appui maintenu sans bouger : le panneau se soulève (il suivra le pointeur au premier mouvement)
        if not self.rep: return
        sym, t0, tl, sens, d = self.rep; t = time.time()
        if not self.J.touches[sym]: self.rep = None; return
        if sens == 'h' and self.rep_pos != (self.ecran, self.sel.get(self.ecran, 0)): self.rep = None; return       # la selection a change (souris, autre ecran) : la repetition s'arrete, elle ne doit jamais toucher un autre reglage
        if t - t0 > DELAI_REPETITION and t - tl > PAS_REPETITION:
            self.rep = (sym, t0, t, sens, d)
            if sens == 'v': self._bouger(d)
            else: self._regler(d)

    # ---- liste deroulante
    def _ouvrir_liste(self):
        i = self.sel.get(self.ecran, 0); en = self._entrees()[i]; cur = en['get']()
        self.deroule = [i, en['vals'].index(cur) if cur in en['vals'] else 0]; self.liste_top = None; self.liste_cur_vu = None; self.glisse_liste = None

    def _fin_liste(self, valide):
        d, self.deroule = self.deroule, None
        if not valide or d is None: return
        e = self._entrees()
        if d[0] < len(e) and e[d[0]]['t'] == 'choix' and not self._entete(e[d[0]]['vals'][d[1]]): e[d[0]]['set'](e[d[0]]['vals'][d[1]])

    def _bouger_liste(self, d):
        e = self._entrees()
        if self.deroule[0] >= len(e) or e[self.deroule[0]]['t'] != 'choix': self.deroule = None; return
        vals = e[self.deroule[0]]['vals']; n = len(vals); self.deroule[1] = self._hors_entete(vals, (self.deroule[1] + d) % n, d)          # (les intertitres de groupe sont sautes)

    def _touche_liste(self, symbol, act):
        K = pyglet.window.key
        if symbol in (K.ESCAPE, K.BACKSPACE) or act == 'B': self._fin_liste(False)
        elif symbol == K.UP or act == 'haut': self._bouger_liste(-1); self._repeter(symbol, 'v', -1)
        elif symbol == K.DOWN or act == 'bas': self._bouger_liste(1); self._repeter(symbol, 'v', 1)
        elif symbol == K.PAGEUP: self._bouger_liste(-7)
        elif symbol == K.PAGEDOWN: self._bouger_liste(7)
        elif symbol in (K.RETURN, K.ENTER, K.SPACE) or act == 'A': self._fin_liste(True)

    def _fixer_top(self, t):
        """Premiere valeur visible de la liste deroulante (la barre de defilement la deplace sans changer la valeur surlignee)."""
        b = self.barre_liste
        if b: self.liste_top = max(0, min(int(t), b['n'] - b['vis']))

    def _clic_barre_liste(self, x, y):
        b = self.barre_liste; top = self.liste_top or 0
        if y > b['ptop']: self._fixer_top(top - 1)
        elif y < b['pbot']: self._fixer_top(top + 1)
        elif b['pouce'][0] <= y <= b['pouce'][1]: self.glisse_liste = b['pouce'][1] - y
        elif y > b['pouce'][1]: self._fixer_top(top - (b['vis'] - 1))
        else: self._fixer_top(top + (b['vis'] - 1))

    def _glisser_barre_liste(self, y):
        b = self.barre_liste
        if not b: self.glisse_liste = None; return
        libre = b['ptop'] - b['pbot'] - b['th']
        if libre > 0: self._fixer_top(round(max(0.0, min(1.0, (b['ptop'] - (y + self.glisse_liste)) / libre)) * (b['n'] - b['vis'])))

    def _zone_liste(self, x, y):
        for (x0, y0, x1, y1, j) in self.zones_pop:
            if x0 <= x <= x1 and y0 <= y <= y1: return j
        return None

    def _bouger(self, d):
        if self.deroule is not None: self._bouger_liste(d); return
        e = self._entrees(); n = len(e)
        if not n: return
        i = self.sel.get(self.ecran, 0)
        for _ in range(n):
            i = (i + d) % n
            if e[i]['t'] != 'sep': break
        self.sel[self.ecran] = i

    def _courante(self):
        e = self._entrees(); i = min(self.sel.get(self.ecran, 0), len(e) - 1)
        if e and e[i]['t'] == 'sep':
            self._bouger(1); i = self.sel.get(self.ecran, 0)
        return e[i] if e else None

    def _regler(self, d):
        if self.deroule is not None: return
        en = self._courante()
        if not en: return
        if en['t'] in ('choix', 'curs'): (en['moins'] if d < 0 else en['plus'])()
        elif en['t'] == 'touche':
            c = self.sel.get('col', 0); self.sel['col'] = min(1, max(0, c + d))

    def _defaut(self):
        """Remet le curseur ou les touches de la ligne choisie a leur valeur d'origine."""
        en = self._courante()
        if en and en['t'] in ('curs', 'touche') and 'defaut' in en: en['defaut']()

    def _suppr(self):
        """Suppr : curseur -> valeur d'origine ; touche -> la case choisie est videe."""
        en = self._courante()
        if not en: return
        if en['t'] == 'touche': self.J.reg.delier(en['act'], self.sel.get('col', 0)); self.J.reg.enregistrer()
        else: self._defaut()

    def _valider(self):
        en = self._courante()
        if not en or en.get('off'): return
        if en['t'] == 'touche': self.capture = (en['act'], self.sel.get('col', 0)); return
        if en['t'] == 'curs': self.saisie = [self.sel.get(self.ecran, 0), '']
        elif en['t'] == 'choix' and en.get('liste'): self._ouvrir_liste()
        elif 'ok' in en: en['ok']()

    def _capturer(self, symbol):
        K = pyglet.window.key; R = self.J.reg; act, col = self.capture
        if symbol == K.ESCAPE: self.capture = None; return
        if symbol in (K.DELETE, K.BACKSPACE): R.delier(act, col); self.capture = None; R.enregistrer(); return
        if RG.nom_de(symbol) in RG.RESERVEES: self._info('Cette touche est réservée (%s).' % RG.nom_touche(RG.nom_de(symbol)), True); return
        avait = R.lier(act, col, symbol); self.capture = None; R.enregistrer()
        if avait and avait != act: self._info('%s retirée de « %s ».' % (RG.nom_touche(RG.nom_de(symbol)), dict(RG.ACTIONS)[avait].split(' :')[0]))

    # ---- souris
    def _zone(self, x, y):
        for (x0, y0, x1, y1, i) in self.zones:
            if x0 <= x <= x1 and y0 <= y <= y1: return i, (x - x0) / max(1.0, x1 - x0)
        return None, 0.0

    def survol(self, x, y):
        p = self.pos_souris; self.pos_souris = (x, y)
        if p is None or abs(x - p[0]) + abs(y - p[1]) < 3: return          # le pointeur n'a pas vraiment bouge : la selection au clavier reste
        self.mode_souris = True
        if self.popup is not None:
            for (x0, y0, x1, y1, i) in self.zones_popup:
                if x0 <= x <= x1 and y0 <= y <= y1: self.popup['sel'] = i
            return
        if self.capture is not None: return
        if self.deroule is not None:
            j = self._zone_liste(x, y)
            if j is not None: self.deroule[1] = j
            return
        self.sur_ret = bool(self.zone_ret and self._dans(self.zone_ret, x, y))
        if self.sur_ret: return
        i, _ = self._zone(x, y)
        if i is not None: self.sel[self.ecran] = i

    @staticmethod
    def _dans(z, x, y):
        return z[0] <= x <= z[2] and z[1] <= y <= z[3]

    def _fixer_vue(self, deb):
        """Premiere ligne visible de l'ecran courant (la selection ne change pas : la vue ne revient pas dessus tant qu'elle ne bouge pas)."""
        b = self.barre
        if b: self.debut[self.ecran] = max(b['base'], min(int(deb), b['base'] + b['n'] - b['vis']))

    def _clic_barre(self, x, y):
        """Clic sur la barre de defilement : fleches (une ligne), curseur (prise pour le glisser), fond de barre (une page)."""
        b = self.barre; deb = self.debut.get(self.ecran, 0)
        if y > b['ptop']: self._fixer_vue(deb - 1)
        elif y < b['pbot']: self._fixer_vue(deb + 1)
        elif b['pouce'][0] <= y <= b['pouce'][1]: self.glisse_barre = b['pouce'][1] - y
        elif y > b['pouce'][1]: self._fixer_vue(deb - (b['vis'] - 1))
        else: self._fixer_vue(deb + (b['vis'] - 1))

    def _glisser_barre(self, y):
        b = self.barre
        if not b: self.glisse_barre = None; return
        libre = b['ptop'] - b['pbot'] - b['th']
        if libre > 0: self._fixer_vue(b['base'] + round(max(0.0, min(1.0, (b['ptop'] - (y + self.glisse_barre)) / libre)) * (b['n'] - b['vis'])))

    def clic(self, x, y, bouton):
        M = pyglet.window.mouse
        self.mode_souris = True; self.pos_souris = (x, y)
        if self.capture is not None: self.capture = None; return
        if self.popup is not None:                                    # fenetre de confirmation : un bouton la valide, un clic droit ou ailleurs la ferme
            if bouton != M.RIGHT:
                for (x0, y0, x1, y1, i) in self.zones_popup:
                    if x0 <= x <= x1 and y0 <= y <= y1: self._valider_popup(i == 0); return
            else: self.popup = None
            return
        if self.ecran == 'interface' and self.zone_plier and self._dans(self.zone_plier, x, y) and bouton != M.RIGHT: self._appui_barre(x, y); return          # barre de titre du panneau : appui court = replier / deplier, appui long = deplacer, double clic = position d'origine
        if self.deroule is not None:                                  # liste deroulante ouverte : un clic sur une valeur la choisit, ailleurs (ou clic droit) la ferme
            b = self.barre_liste
            if bouton != M.RIGHT and b and b['x0'] <= x <= b['x1'] and b['y0'] <= y <= b['y1']: self._clic_barre_liste(x, y); return          # barre de defilement de la liste
            j = self._zone_liste(x, y) if bouton != M.RIGHT else None
            c = self.cadre_liste
            if j is not None: self.deroule[1] = j; self._fin_liste(True)
            elif bouton != M.RIGHT and c and c[0] <= x <= c[2] and c[1] <= y <= c[3]: pass          # (clic sur un intertitre ou la marge de la liste : elle reste ouverte)
            else: self.deroule = None
            return
        if bouton == M.RIGHT:
            if self.saisie is not None: self.saisie = None
            else: self.retour()
            return
        if self.zone_ret and self._dans(self.zone_ret, x, y): self.saisie = None; self.retour(); return          # bouton retour (en bas a droite de la fenetre)
        i, f = self._zone(x, y)
        if self.ecran == 'interface' and i is None and self.saisie is None:       # editeur : hors du panneau, un clic saisit l'element choisi (un bouton de l'ecran, ou la fenetre montree en apercu)
            c = self.cadre_panneau
            if not (c and c[0] <= x <= c[2] and c[1] <= y <= c[3]):
                if self.cible == 'boutons': self.J.hud.prendre(x, y)
                else: self.drag = (x, y, list(self._ov()), self.rect_apercu)
            return
        if self.saisie is not None:                                   # un clic ailleurs que sur la valeur en cours de saisie la valide
            ligne = self.saisie[0]; zv = self.zones_val.get(ligne)
            if i == ligne and zv and zv[0] <= x <= zv[1]: return
            self._fin_saisie(True)
        b = self.barre
        if b and b['x0'] <= x <= b['x1'] and b['y0'] <= y <= b['y1']: self._clic_barre(x, y); return
        if i is None: return
        self.sel[self.ecran] = i; en = self._entrees()[i]
        bar = self.barres.get(i)
        zv = self.zones_val.get(i); zd = self.zones_def.get(i)
        if en['t'] in ('curs', 'touche') and zd and zd[0] <= x <= zd[2] and zd[1] <= y <= zd[3]:       # bouton rond « valeur par defaut » (curseurs, touches d'origine)
            if 'defaut' in en: en['defaut']()
        elif en['t'] == 'curs' and bar and bar[0] - 6 <= x <= bar[1] + 6:       # curseur : le clic maintenu le fait glisser (glisser)
            self.glisse = i; en['fixe'](min(1.0, max(0.0, (x - bar[0]) / (bar[1] - bar[0]))))
        elif en['t'] == 'curs' and zv and zv[0] - 8 <= x <= zv[1] + 8: self.saisie = [i, '']     # clic sur la valeur : saisie au clavier
        elif en['t'] == 'touche':
            for c in range(2):
                ze = self.zones_eff.get((i, c))
                if ze and self._dans(ze, x, y): self.sel['col'] = c; self.J.reg.delier(en['act'], c); self.J.reg.enregistrer(); return          # croix : efface la touche de la case
            col = 1 if x > self.zones_col else 0; self.sel['col'] = col; self._valider()
        else: self._valider()

    @staticmethod
    def _aimanter(r, dx, dy, W, H):
        """Deplacement (dx, dy) de la fenetre de cadre r = (x0, y0, x1, y1), corrige pour que l'un de ses bords (ou son milieu) tombe sur une ligne de la grille (32 x 18 cases) : celui qui en est le plus pres."""
        def pas(a, b, g, d):
            best = None
            for p in (a, (a + b) / 2.0, b):
                c = round((p + d) / g) * g - (p + d)
                if best is None or abs(c) < abs(best): best = c
            return d + best
        return pas(r[0], r[2], W / float(HM.COLS), dx), pas(r[1], r[3], H / float(HM.LIGNES), dy)

    def _appui_barre(self, x, y):
        """Appui sur la barre de titre du panneau de l'editeur (le geste se joue dans glisser, maj et relache) : le panneau suit le pointeur des que celui-ci s'eloigne de plus de TOLERANCE_APPUI du point d'appui (glisser
        tout de suite, sans attendre) ou apres un appui maintenu DELAI_APPUI_LONG (il se souleve) ; appui court sans bouger = replier / deplier ; deuxieme appui court dans DELAI_DOUBLE_CLIC = retour a la position
        d'origine (les deux pliages s'annulent)."""
        t = time.time(); c = self.cadre_panneau
        if not c: return
        if self.deroule is not None: self.deroule = None
        if self.saisie is not None: self._fin_saisie(True)
        self.pan_appui = dict(t0=t, x=x, y=y, dx=x - c[2], dy=y - c[3], long=False, double=t - self.pan_clic_t < DELAI_DOUBLE_CLIC)         # (dx, dy : decalage du pointeur par rapport au coin haut droit du panneau)

    def relache(self, x, y, bouton):
        self.glisse = None; self.glisse_barre = None; self.glisse_liste = None
        a, self.pan_appui = self.pan_appui, None
        if a is not None and not a['long']:                                       # appui court (sans mouvement) : replier / deplier ; deuxieme appui d'un double clic : position d'origine, le pliage du premier est annule
            if a['double']: self.pan_pos = None
            self.plie = not self.plie; self.pan_clic_t = 0.0 if a['double'] else time.time()
        if self.ecran == 'interface' and self.J.hud.pris is not None: self.J.hud.poser(); self.J.reg.enregistrer()
        if self.drag is not None: self.drag = None; self.J.reg.enregistrer()

    def glisser(self, x, y):
        """Souris deplacee bouton enfonce : le curseur maintenu (ou celui de la barre de defilement) suit."""
        a = self.pan_appui
        if a is not None:                                                                    # panneau de l'editeur : il suit le pointeur des que celui-ci a quitte le point d'appui (le panneau se souleve, ni pliage ni double clic), ou apres un appui maintenu
            if not a['long'] and math.hypot(x - a['x'], y - a['y']) > TOLERANCE_APPUI: a['long'] = True; a['double'] = False
            if a['long']: self.pan_pos = (x - a['dx'], y - a['dy'])
            return
        if self.glisse_liste is not None: self._glisser_barre_liste(y); return
        if self.glisse_barre is not None: self._glisser_barre(y); return
        if self.glisse is None:
            if self.ecran == 'interface':
                if self.drag is not None:                              # fenetre du jeu : elle suit le pointeur (decalage en fraction de l'ecran), aimantee a la grille si le reglage est actif
                    x0, y0, o, r0 = self.drag; W, H = self.J.width, self.J.height; dx, dy = x - x0, y - y0
                    if self.J.reg['boutons_aimant'] and r0: dx, dy = self._aimanter(r0, dx, dy, W, H)
                    self._poser_ov(1, max(-0.5, min(0.5, o[1] + dx / W))); self._poser_ov(2, max(-0.5, min(0.5, o[2] + dy / H)))
                else: self.J.hud.deplacer(x, y)
            return
        bar = self.barres.get(self.glisse); e = self._entrees()
        if bar is None or self.glisse >= len(e) or e[self.glisse]['t'] != 'curs': self.glisse = None; return
        e[self.glisse]['fixe'](min(1.0, max(0.0, (x - bar[0]) / (bar[1] - bar[0]))))

    def texte(self, t):
        """Caracteres tapes pendant la saisie d'une valeur."""
        if self.saisie is None: return
        for c in t.replace(',', '.'):
            if (c.isdigit() or (c in '.-' and c not in self.saisie[1])) and len(self.saisie[1]) < 7: self.saisie[1] += c

    def _touche_saisie(self, symbol):
        K = pyglet.window.key
        if symbol in (K.RETURN, K.ENTER): self._fin_saisie(True)
        elif symbol == K.ESCAPE: self._fin_saisie(False)
        elif symbol == K.BACKSPACE:
            if self.saisie[1]: self.saisie[1] = self.saisie[1][:-1]
            else: self._fin_saisie(False)

    def _fin_saisie(self, valide):
        ligne, txt = self.saisie; self.saisie = None
        if not valide or txt in ('', '-', '.'): return
        e = self._entrees()
        if ligne < len(e) and e[ligne]['t'] == 'curs' and 'saisie' in e[ligne]:
            try: e[ligne]['saisie'](float(txt))
            except ValueError: pass

    def molette(self, sy):
        if self.popup is not None or (self.ecran == 'interface' and self.plie): return
        b = self.barre
        if b and self.deroule is None and b['n'] > b['vis']: self._fixer_vue(self.debut.get(self.ecran, 0) - 2 * (1 if sy > 0 else -1)); return      # liste qui defile : la molette fait defiler la vue (comme la barre)
        self._bouger(1 if sy > 0 else -1)                                    # (sinon, sens inverse : molette vers le haut = ligne suivante)

    # ---- dessin
    @staticmethod
    def _cadre(x, y, w, h, k):
        """Fenetre a la maniere des menus du jeu mobile : fond noir de meme opacite que les autres menus, cadre blanc en cinq traits, coins arrondis et transparents (hud_mobile.cadre)."""
        HM.cadre(x, y, w, h, k, fond=NOIR, opacite=HM.OPACITE_JEU)

    def _plaque(self, x, y, w, h, k, choisi=False, contour=None):
        """Fond d'un bouton : la plaque des fenetres du jeu (feuille Button, comme « Soigner tous »), enfoncee quand elle est choisie ; encadrement colore a la souris. Sans les menus d'origine : plaque dessinee (hud_mobile)."""
        r = getattr(self.J, 'ui_rendu', None)
        if r is not None and r.plaque(x, y, w, h, (self.J.width, self.J.height), choisi):
            if contour is not None: HM.contour(x, y, w, h, k, contour)
        else: HM.plaque(x, y, w, h, k, choisi, contour)

    def _bouton_defaut(self, idx, x, y, c, est_defaut, sel, k):
        """Bouton carre « valeur par defaut » (fleche en cercle) : clair quand la valeur differe de celle d'origine, terne sinon."""
        self.zones_def[idx] = (x - 3 * k, y - 3 * k, x + c + 3 * k, y + c + 3 * k)
        coul = (90, 90, 90) if est_defaut else CLAIR
        r = pyglet.shapes.BorderedRectangle(x, y, c, c, border=max(1, int(2 * k)), color=(255, 255, 255), border_color=coul[:3]); r.opacity = 30 if est_defaut else 70; r.draw()
        cx, cy, ra = x + c / 2, y + c / 2, c * 0.28; t0, t1 = math.radians(55), math.radians(55 + 270)
        pts = [(cx + ra * math.cos(t0 + (t1 - t0) * i / 14), cy + ra * math.sin(t0 + (t1 - t0) * i / 14)) for i in range(15)]
        for a, b in zip(pts, pts[1:]): pyglet.shapes.Line(a[0], a[1], b[0], b[1], thickness=max(1.5, 2 * k), color=coul[:3]).draw()
        ex, ey = pts[0]; tg = t0 - math.pi / 2                                       # pointe de fleche au debut de l'arc
        h = c * 0.2
        pyglet.shapes.Triangle(ex + h * math.cos(tg), ey + h * math.sin(tg), ex + h * math.cos(tg + 2.4), ey + h * math.sin(tg + 2.4), ex + h * math.cos(tg - 2.4), ey + h * math.sin(tg - 2.4), color=coul[:3]).draw()

    @staticmethod
    def _pilule(x, yc, w, h, couleur):
        """Rectangle a bouts ronds, centre verticalement en yc."""
        r = h / 2
        for sh in (pyglet.shapes.Rectangle(x + r, yc - r, w - 2 * r, h, color=couleur), pyglet.shapes.Circle(x + r, yc, r, segments=24, color=couleur), pyglet.shapes.Circle(x + w - r, yc, r, segments=24, color=couleur)): sh.draw()

    def _interrupteur(self, cle, x, yc, actif, sel, grise, k):
        """Interrupteur coulissant (piste arrondie, bouton rond) : or quand c'est active, gris sinon ; le bouton glisse d'une position a l'autre (animation courte) ; contour or s'il est selectionne."""
        cible = 1.0 if actif else 0.0; p = self.pos_sw.get(cle, cible)                   # premiere apparition : pas d'animation
        p = cible if abs(cible - p) < 0.02 else p + (cible - p) * min(1.0, self.dt_sw * 16.0); self.pos_sw[cle] = p
        w, h = LARG_SW * k, HAUT_SW * k; r = h / 2
        piste = (30, 32, 36) if grise else tuple(int(a + (b - a) * p) for a, b in zip((20, 22, 26), (225, 207, 3)))
        if sel and not grise: e = max(1.5, 2 * k); self._pilule(x - e, yc, w + 2 * e, h + 2 * e, CLAIR)
        self._pilule(x, yc, w, h, piste)
        pyglet.shapes.Circle(x + r + (w - 2 * r) * p, yc, r - 3 * k, segments=24, color=(128, 128, 128) if grise else (255, 255, 255)).draw()

    def _miniature(self, n):
        """Texture de la miniature d'un etat (None s'il n'y en a pas)."""
        if n in self.minis: return self.minis[n]
        t = None; inf = self.J.infos_etat(n)
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

    def _barre_defilement(self, x1, ptop, pbot, n, vis, deb, k, actif, base=0):
        """Barre de defilement a droite de la liste : fleche haut, piste, curseur, fleche bas (haut de la liste en ptop, bas en pbot). Renvoie la geometrie de la barre (pour les clics)."""
        w = LARG_BARRE * k; x0 = x1 - w; fl = 14 * k; th0, th1 = ptop - fl - 2 * k, pbot + fl + 2 * k          # piste entre les deux fleches
        piste = pyglet.shapes.Rectangle(x0, th1, w, th0 - th1, color=(34, 36, 42)); piste.draw()
        th = max(26 * k, (th0 - th1) * vis / float(n)); f = deb / float(max(1, n - vis)); hau = th0 - f * (th0 - th1 - th)
        self._plaque(x0, hau - th, w, th, k * 0.8, actif)
        coul = CLAIR if n > vis else GRIS[:3]
        pyglet.shapes.Triangle(x0 + 1.5 * k, ptop - fl + 3 * k, x1 - 1.5 * k, ptop - fl + 3 * k, (x0 + x1) / 2, ptop - 2 * k, color=coul).draw()
        pyglet.shapes.Triangle(x0 + 1.5 * k, pbot + fl - 3 * k, x1 - 1.5 * k, pbot + fl - 3 * k, (x0 + x1) / 2, pbot + 2 * k, color=coul).draw()
        return dict(x0=x0 - 3 * k, x1=x1 + 3 * k, y0=pbot, y1=ptop, ptop=th0, pbot=th1, th=th, pouce=(hau - th, hau), n=n, vis=vis, base=base)

    def _croix(self, x, y, c):
        """Croix rouge du jeu (effacer une touche), de c pixels, coin bas gauche en (x, y)."""
        t = self._tex_decoupe('croix', 'ui_MenuTexture.png', CROIX)
        if t is None: return
        self._melange(); t.blit(x, y, width=c, height=c * (CROIX[3] - CROIX[1]) / float(CROIX[2] - CROIX[0]))

    def _chevron(self, x, yc, k):
        """Chevron « > » : la ligne ouvre un autre menu."""
        for a, b in (((x - 4 * k, yc + 8 * k), (x + 4 * k, yc)), ((x + 4 * k, yc), (x - 4 * k, yc - 8 * k))):
            pyglet.shapes.Line(a[0], a[1], b[0], b[1], thickness=max(2.0, 2.6 * k), color=(255, 255, 255)).draw()

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

    def _ajuster(self, texte, taille, couleur, maxw):
        """Etiquette de `texte` qui tient dans `maxw` pixels (la taille diminue au besoin)."""
        et = self._et(texte, taille, couleur)
        if et.content_width > maxw > 0: et = self._et(texte, taille * maxw / et.content_width, couleur)
        return et

    def _elements_apercu(self):
        """Elements montres a l'ecran pour l'interface choisie (boutons et croix de l'ecran, ou la fenetre du jeu en apercu) : [(x0, y0, x1, y1, masque, masculin)].
        `masque` : l'element n'est pas dessine en jeu : toute l'interface masquee (« Afficher cette interface a l'ecran » = Non : boutons, croix, fenetre) ou, pour la croix seule, « Afficher la croix » = Non.
        `masculin` : accord de l'etiquette « Masquée » (boutons : « Masqué »)."""
        R = self.J.reg
        if self.cible == RG.CIBLE_ECRAN:
            tout = not R['boutons']; out = []
            for n in HM.NOMS_ED:
                x, y, w, h = self.J.hud.rect(n); out.append((x, y, x + w, y + h, tout or (n == HM.CROIX and not R['croix']), n != HM.CROIX))
            return out
        return [tuple(self.rect_apercu) + (not self._visible(self.cible), False)] if self.rect_apercu else []

    def _rects_montres(self):
        """Rectangles (x0, y0, x1, y1) montres a l'ecran pour l'interface choisie (voir _elements_apercu)."""
        return [e[:4] for e in self._elements_apercu()]

    def _coin_origine(self, pw, h, W, H, m):
        """Position d'origine du panneau de l'editeur (coin haut droit) : en haut a droite (les boutons sont a gauche, la croix en bas a droite) ; si cela cache l'interface choisie, le premier des autres coins de l'ecran
        (haut gauche, bas droite, bas gauche) qui ne la cache pas, sinon celui qui en cache le moins. Calculee sur la taille du panneau deplie (le panneau replie ne change pas de coin)."""
        pw, h = self.pan_dim or (pw, h); cibles = self._rects_montres(); best = None
        for x1, y1 in ((W - m, H - m), (pw + m, H - m), (W - m, h + m), (pw + m, h + m)):
            r = (x1 - pw, y1 - h, x1, y1)
            sc = sum(max(0.0, min(r[2], q[2]) - max(r[0], q[0])) * max(0.0, min(r[3], q[3]) - max(r[1], q[1])) for q in cibles)
            if sc <= 0: return x1, y1
            if best is None or sc < best[0]: best = (sc, x1, y1)
        return best[1], best[2]

    def _pos_panneau(self, pw, h, W, H, k):
        """Coin haut gauche (x0, y1) du panneau de l'editeur d'interface : position du joueur (apres un appui long et un glissement, gardee le temps de la session) ou position d'origine (_coin_origine),
        toujours ramenee dans l'ecran."""
        x1, y1 = self.pan_pos if self.pan_pos is not None else self._coin_origine(pw, h, W, H, 22 * k)
        x1 = min(max(x1, pw + 4 * k), W - 4 * k); y1 = min(max(y1, h + 4 * k), H - 4 * k)
        return x1 - pw, y1

    def _apercu(self):
        """Editeur d'interface : le jeu reste visible ; l'element choisi est montre (boutons de l'ecran avec leur grille, ou fenetre du jeu en apercu, a sa taille et sa place) ; les autres boutons restent a l'ecran."""
        J = self.J; self.rect_apercu = None
        if self.cible == 'boutons': J.hud.dessiner(HM.NOMS_ED, True, J.reg['grille_edition'])              # seuls les boutons de l'ecran (les fenetres du jeu ne sont pas dessinees pendant l'edition)
        else:
            voile = pyglet.shapes.Rectangle(0, 0, J.width, J.height, color=(0, 0, 0)); voile.opacity = 90; voile.draw()
            if J.reg['grille_edition']: HM.tracer_grille(J.width, J.height)
            self.rect_apercu = J.apercu_interface(self.cible)                                                    # seule la fenetre choisie (ni les autres fenetres, ni les boutons)
        k = max(0.75, J.height / 900.0)
        for x0, y0, x1, y1, masque, masculin in self._elements_apercu():                                           # element non affiche en jeu (toute l'interface, ou la croix seule) : l'apercu reste visible pour le placer, mais assombri et marque
            if not masque: continue
            v = pyglet.shapes.Rectangle(x0, y0, x1 - x0, y1 - y0, color=(0, 0, 0)); v.opacity = 150; v.draw()
            et = self._ajuster(MOTS_MASQUE[masculin], 20 * k, ROUGE, max(x1 - x0 - 18 * k, 36 * k)); et.x = (x0 + x1) / 2 - et.content_width / 2; et.y = (y0 + y1) / 2 - et.content_height / 2
            pastille = pyglet.shapes.Rectangle(et.x - 8 * k, et.y - 4 * k, et.content_width + 16 * k, et.content_height + 8 * k, color=(0, 0, 0)); pastille.opacity = 200; pastille.draw(); et.draw()          # (sur un fond sombre : le texte du message d'essai passe dessous)
            pyglet.shapes.Box(x0, y0, x1 - x0, y1 - y0, thickness=2, color=CADRE_SELECTION).draw()                  # le cadre jaune de selection reste aussi net que sur un element affiche (le voile le couvrait)

    def dessiner(self):
        J = self.J; W, H = J.width, J.height; k = max(0.75, H / 900.0)
        editeur = self.ecran == 'interface'
        gl.glDisable(gl.GL_DEPTH_TEST); gl.glEnable(gl.GL_BLEND); gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)
        if editeur: self._apercu()
        else:
            voile = pyglet.shapes.Rectangle(0, 0, W, H, color=(0, 0, 0)); voile.opacity = 90; voile.draw()
        t = time.time(); self.dt_sw = min(0.1, t - self.t_sw); self.t_sw = t               # (animation des interrupteurs)
        ecr = self.ecran; e = self._entrees(); n = len(e)
        if editeur and self.plie: e = []; n = 0                                           # panneau de l'editeur replie : seule la barre de titre reste
        i_sel = min(self.sel.get(ecr, 0), max(0, n - 1))
        while i_sel < n - 1 and e[i_sel]['t'] == 'sep' and ecr not in ('quitter', 'titre'): i_sel += 1; self.sel[ecr] = i_sel          # (la selection saute les intertitres, y compris a l'ouverture de l'ecran)
        n_f = 1 if e and e[0].get('fixe') else 0                                          # ligne fixe en haut (bouton Interface de Commandes) : elle ne defile pas
        fs, fst, fsp = 18 * k, 24 * k, 13 * k; pad = 30 * k
        titres = {'racine': 'Pause', 'affichage': 'Affichage', 'son': 'Son', 'commandes': 'Commandes', 'interface': 'Interface', 'etats': 'États', 'quitter': 'Quitter', 'titre': 'Écran titre'}
        titres['texte'] = 'Texte et défilement'
        avec_mini = ecr == 'etats'
        msg = self.message[0] if self.message and time.time() - self.message[1] < 4.0 else ''
        # hauteurs : le bouton retour est sous la fenetre ; si les lignes ne tiennent pas, elles defilent (barre a droite, dans la marge)
        avec_ret = not editeur and ecr != 'racine'                                  # (pas de bouton retour a la racine : « Reprendre » ferme le menu)
        kb = 1.1 * k; bw, bh = 64 * kb, 55.5 * kb; marge_ret = bh + 10 * k if avec_ret else 0.0
        pied = 0.0                                          # (plus de ligne d'aide en bas : les aides sont des infobulles ; le message d'information est dessine au-dessus du cadre)
        hmax = H - 2 * 36 * k - marge_ret; h_titre = 78 * k + (22 * k if ecr == 'commandes' else 0.0)
        if editeur: h_titre = 64 * k
        rh = max(34 * k, min(52 * k, (hmax - h_titre - pad / 2 - pied) / max(1, n)))
        if editeur: rh = 38 * k                                                    # panneau compact
        elif ecr == 'commandes': rh = 46 * k                                       # lignes hautes : les cases de touches ne touchent pas les bords (la liste defile)
        fs = min(fs, rh * 0.5)                                                     # lignes serrees : texte plus petit, pour qu'il tienne dans le bouton
        h_titre += n_f * rh
        n_s = n - n_f
        h = min(hmax, h_titre + n_s * rh + pad / 2 + pied)
        visibles = max(1, int((h - h_titre - pad / 2 - pied) / rh + 0.02)); barre = n_s > visibles
        if barre: h = h_titre + visibles * rh + pad / 2 + pied                     # (la fenetre se referme sur la derniere ligne visible)
        rdr = 56 * k                                                               # marge droite du contenu des lignes (boutons : 42 px de marge a gauche comme a droite ; la barre de defilement est dans la marge)
        # largeur : le plus long libelle + la place des valeurs / curseurs / cases de touches
        lw = max([self._et(x['l'], fs).content_width for x in e if not (ecr == 'etats' and x['t'] == 'slot')] + [0.0]); vw = 0.0       # (etats : la date des emplacements ne compte pas, la fenetre garde la meme taille avec ou sans etat enregistre ; la date se reduit au besoin)
        for x in e:
            if x['t'] == 'choix':
                tw = max(self._et(self._nom_valeur(x['l'], v), fs).content_width for v in x['vals'])
                vw = max(vw, tw + 24 * k if x.get('liste') else tw + 14 * k + LARG_SW * k)               # liste : valeur + fleche ; interrupteur : Oui / Non puis l'interrupteur
        pw = max(540 * k, 52 * k + lw + 40 * k + vw + rdr)
        if ecr in ('affichage', 'son', 'commandes', 'interface'): pw = max(pw, 52 * k + lw + 40 * k + 44 * k + 200 * k + 20 * k + 90 * k + rdr)
        if ecr in ('texte',): pw = max(pw, 52 * k + lw + 40 * k + vw + rdr + 20 * k)
        if ecr == 'commandes': pw = max(pw, 52 * k + lw + 30 * k + 40 * k + 2 * LARG_CELLULE * k + ECART_CELLULES * k + rdr)
        wmini = 360 * k if avec_mini else 0.0; gap = 24 * k if avec_mini else 0.0
        x0 = (W - pw - wmini - gap) / 2; y1 = (H + h + marge_ret) / 2; y0 = y1 - h
        if editeur:                                                                 # replie : la barre de titre seule, pour voir tout l'ecran ; position : celle du joueur apres un deplacement, sinon celle d'origine (voir _pos_panneau)
            if self.plie and self.pan_dim: pw = self.pan_dim[0]                       # replie : la barre de titre garde la largeur du panneau deplie (elle reste sous le pointeur : appui court puis double clic)
            elif self.plie: pw = max(300 * k, self._et(titres['interface'], fst).content_width + 130 * k)
            else: self.pan_dim = (pw, h)
            x0, y1 = self._pos_panneau(pw, h, W, H, k); y0 = y1 - h
        self.cadre_panneau = (x0, y0, x0 + pw, y1) if editeur else None
        self.zone_plier = (x0, y1 - h_titre, x0 + pw, y1) if editeur else None
        a_pan = self.pan_appui if editeur else None; leve = bool(a_pan and a_pan['long'])          # appui sur la barre de titre : titre dore ; apres l'appui long, le panneau « se souleve » (cadre agrandi, contour dore)
        if leve:
            g = 7 * k; self._cadre(x0 - g, y0 - g, pw + 2 * g, h + 2 * g, k)
            pyglet.shapes.Box(x0 - g, y0 - g, pw + 2 * g, h + 2 * g, thickness=max(2.0, 3 * k), color=OR[:3]).draw()
        else: self._cadre(x0, y0, pw, h, k)
        e_t = self._et(titres.get(ecr, ''), fst, OR if (a_pan and not a_pan['double']) else BLANC); e_t.x = x0 + (pw - e_t.content_width) / 2; e_t.y = y1 - (44 if editeur else 52) * k; e_t.draw()
        if editeur:                                                                 # plier / deplier le panneau : fleche dans la barre de titre (vers le haut = replier, vers le bas = deplier)
            fx, fy = e_t.x + e_t.content_width + 26 * k, y1 - 32 * k                  # (collee au titre : elle le suit quand le panneau change de largeur)
            sur = self.mode_souris and self.pos_souris and self._dans(self.zone_plier, *self.pos_souris)
            coul = OR[:3] if sur else (200, 200, 200)
            if self.plie: pyglet.shapes.Triangle(fx - 9 * k, fy + 5 * k, fx + 9 * k, fy + 5 * k, fx, fy - 6 * k, color=coul).draw()
            else: pyglet.shapes.Triangle(fx - 9 * k, fy - 5 * k, fx + 9 * k, fy - 5 * k, fx, fy + 6 * k, color=coul).draw()
        # vue : la selection reste visible quand elle change ; sinon la vue ne bouge que par la barre ou la molette
        deb = self.debut.get(ecr, n_f)
        if self.vu_sel.get(ecr) != i_sel:
            if i_sel >= n_f:
                if i_sel < deb: deb = i_sel
                elif i_sel >= deb + visibles: deb = i_sel - visibles + 1
            self.vu_sel[ecr] = i_sel
        debut = self.debut[ecr] = max(n_f, min(deb, max(n_f, n - visibles)))
        self.zones = []; self.barres = {}; self.zones_val = {}; self.zones_def = {}; self.zones_eff = {}; self.zones_pop = []; lignes = {}; self.barre = None; self.barre_liste = None; self.cadre_liste = None
        xr = x0 + pw - rdr                                                        # bord droit du contenu des lignes
        cx2 = xr - 40 * k - LARG_CELLULE * k; cx1 = cx2 - ECART_CELLULES * k - LARG_CELLULE * k; self.zones_col = cx2 - ECART_CELLULES * k / 2
        plx = x0 + 42 * k; plw = pw - 84 * k                                      # boutons : meme marge a gauche et a droite
        if ecr == 'commandes':
            for c, cx in enumerate((cx1, cx2)):
                eh = self._et('Touche %d' % (c + 1), fsp, GRIS); eh.x = cx + (LARG_CELLULE * k - eh.content_width) / 2; eh.y = y1 - h_titre + 6 * k; eh.draw()
        pos = []
        if n_f: pos.append((0, y1 - 66 * k))
        yy = y1 - h_titre
        for idx in range(debut, min(n, debut + visibles)): pos.append((idx, yy)); yy -= rh
        mouse = self.mode_souris
        for idx, ytop in pos:
            en = e[idx]; ybas = ytop - rh; sel = idx == i_sel and en['t'] != 'sep'; lignes[idx] = (ybas, ytop)
            note = en['note']() if en.get('note') else ''
            dec = max(0.0, min(8 * k, (rh - 36 * k) * 0.6)) if note else 0.0                  # note rouge sous la valeur : la ligne monte un peu pour lui laisser la place
            if en['t'] != 'sep': self._plaque(plx, ybas + 3 * k, plw, rh - 6 * k, k, sel, JAUNE if sel and mouse else None)       # fond du bouton, comme ceux du menu des commandes du jeu mobile (la selection l'eclaircit ; a la souris : encadrement jaune)
            if sel and not mouse: self._curseur(x0 + 6 * k, ybas + rh / 2 + dec, min(rh * 0.6, 26 * k))             # curseur dore des menus du jeu (selection au clavier)
            coul = GRIS if en.get('off') else BLANC
            base = ybas + rh / 2 - 0.45 * fs                                                  # texte centre dans le bouton
            lx = x0 + 52 * k
            if en['t'] == 'sep':                                                              # intertitre : au centre de la fenetre
                et = self._et(en['l'], fs, OR); et.x = x0 + (pw - et.content_width) / 2; et.y = base; et.draw()
                self.zones.append((plx, ybas + 3 * k, plx + plw, ytop - 3 * k, idx))
                continue
            maxw_lab = 0.0                                                                    # largeur permise au libelle (0 : aucune limite)
            if en['t'] == 'slot':
                nu = self._et('%d' % en['n'], fs, coul); nu.x = lx; nu.y = base; nu.draw(); lx += 44 * k
                maxw_lab = x0 + pw - 66 * k - (self._et(en['v'], fsp * 1.2, GRIS).content_width + 12 * k if en['v'] else 0.0) - lx           # (jusqu'au lieu, a droite)
            base += dec
            lab = self._ajuster(en['l'], fs, coul, maxw_lab) if maxw_lab else self._et(en['l'], fs, coul); lab.x = lx; lab.y = base; lab.draw()
            if note:
                en_ = self._et(note, fsp * 0.95, ROUGE); en_.x = xr - en_.content_width; en_.y = ybas + 9 * k; en_.draw()
            if en['t'] == 'act' and en.get('sous'): self._chevron(xr - 6 * k, ybas + rh / 2 + dec, k)
            if en['t'] == 'choix' and en.get('liste'):                                        # liste deroulante : valeur courante et petite fleche vers le bas
                vl = self._et(en['v'](), fs, coul); vl.x = xr - 24 * k - vl.content_width; vl.y = base; vl.draw()
                fx, fy = xr - 8 * k, ybas + rh / 2 + dec
                pyglet.shapes.Triangle(fx - 7 * k, fy + 4 * k, fx + 7 * k, fy + 4 * k, fx, fy - 5 * k, color=OR[:3] if sel else coul[:3]).draw()
                self.zones_val[idx] = (vl.x - 10 * k, xr + 10 * k)
            elif en['t'] == 'choix':                                                          # interrupteur Oui / Non : le texte de la valeur, puis l'interrupteur
                sw_x = xr - LARG_SW * k; actif = bool(en['get']())
                vl = self._et(en['v'](), fs, coul if not actif or en.get('off') else OR); vl.x = sw_x - 14 * k - vl.content_width; vl.y = base; vl.draw()
                self._interrupteur(en['l'], sw_x, ybas + rh / 2, actif, sel and not mouse, en.get('off'), k)
                self.zones_val[idx] = (vl.x - 10 * k, sw_x + LARG_SW * k + 10 * k)
            elif en['t'] == 'curs':
                if self.saisie is not None and self.saisie[0] == idx: txt = (self.saisie[1] + ('_' if int(time.time() * 2) % 2 == 0 else ' ')).rjust(3)
                else: txt = en['v']()
                dr = xr - 40 * k                                                              # bord droit de la valeur : le bouton « valeur par defaut » est a sa droite
                vl = self._et(txt, fs, OR if self.saisie is not None and self.saisie[0] == idx else coul); vl.x = dr - vl.content_width; vl.y = base; vl.draw()
                self.zones_val[idx] = (vl.x - 10 * k, dr + 10 * k)
                bw_ = 200 * k; bx1 = dr - 90 * k - 20 * k; bx0 = bx1 - bw_; by = ybas + rh / 2 - 5 * k; self.barres[idx] = (bx0, bx1)
                fond = pyglet.shapes.Rectangle(bx0, by, bw_, 10 * k, color=(16, 18, 22)); fond.draw()
                rem = pyglet.shapes.Rectangle(bx0, by, bw_ * max(0.0, min(1.0, en['frac']())), 10 * k, color=JAUNE); rem.draw()
                cur = pyglet.shapes.Rectangle(bx0 + bw_ * max(0.0, min(1.0, en['frac']())) - 3 * k, by - 4 * k, 6 * k, 18 * k, color=(255, 255, 255)); cur.draw()
                if 'defaut' in en: self._bouton_defaut(idx, xr - 26 * k, ybas + rh / 2 - 13 * k, 26 * k, en['est_defaut'](), sel, k)
            elif en['t'] == 'slot':
                if en['v']: vl = self._et(en['v'], fsp * 1.2, GRIS); vl.x = x0 + pw - 24 * k - 42 * k - vl.content_width; vl.y = base; vl.draw()
            elif en['t'] == 'touche':
                for c, cx in enumerate((cx1, cx2)):
                    txt = en['v'][c]; actif = sel and self.sel.get('col', 0) == c; vide = txt == RG.nom_touche(None)
                    if self.capture is not None and self.capture == (en['act'], c): txt = '…'
                    HM.cadre(cx, ybas + 9 * k, LARG_CELLULE * k, rh - 18 * k, k * 0.5, 0.5 if actif else 0.0, fond=NOIR, opacite=0.75)          # case de la touche (plus claire quand elle est choisie), a distance des bords du bouton
                    zone_t = LARG_CELLULE * k - (0 if vide else 2 * 22 * k); fz = fs * 0.8                 # texte centre dans la case (marges egales : la croix rouge est a droite, hors de la zone du texte)
                    vl = self._et(txt, fz, OR if actif else (GRIS if vide else BLANC))
                    if vl.content_width > zone_t - 8 * k: fz *= (zone_t - 8 * k) / vl.content_width; vl = self._et(txt, fz, OR if actif else BLANC)
                    vl.x = cx + (LARG_CELLULE * k - vl.content_width) / 2; vl.y = ybas + rh / 2 - self._cap(fz) / 2 + dec; vl.draw()               # (ligne de base : le milieu de la hauteur des capitales sur le milieu de la case)
                    if not vide and self.capture != (en['act'], c):
                        cc = 12 * k; cxx = cx + LARG_CELLULE * k - cc - 8 * k; self._croix(cxx, ybas + rh / 2 - cc * 0.45 + dec, cc)
                        self.zones_eff[(idx, c)] = (cxx - 4 * k, ybas + 9 * k, cx + LARG_CELLULE * k, ybas + rh - 9 * k)
                self._bouton_defaut(idx, xr - 26 * k, ybas + rh / 2 - 13 * k, 26 * k, en['est_defaut'](), sel, k)
            self.zones.append((plx, ybas + 3 * k, plx + plw, ytop - 3 * k, idx))
        if barre: self.barre = self._barre_defilement(x0 + pw - 14 * k, y1 - h_titre, y1 - h_titre - visibles * rh, n_s, visibles, debut - n_f, k, self.glisse_barre is not None, n_f)
        # pied du cadre : aide (centree, toujours dans le cadre)
        yp = y0 + 12 * k
        if msg:
            em = self._ajuster(msg, fsp * 1.1, ROUGE if self.message[2] else OR, W - 24 * k); em.x = min(max(12 * k, x0 + (pw - em.content_width) / 2), W - em.content_width - 12 * k); em.y = min(H - 24 * k, y1 + 12 * k); em.draw()
        # bouton retour, en bas a droite de la fenetre
        self.zone_ret = None
        if avec_ret:
            bx = x0 + pw - bw - 8 * k; by = y0 - 8 * k - bh; self.zone_ret = (bx, by, bx + bw, by + bh)
            self._bouton_retour(bx, by, bw, bh, self.sur_ret)
        # miniature de l'etat survole
        if avec_mini:
            mx = x0 + pw + gap; mh = min(h, 270 * k)
            self._cadre(mx, y1 - h, wmini, h, k)
            if e and e[i_sel]['t'] == 'slot':
                n_e = e[i_sel]['n']; t = self._miniature(n_e); inf = J.infos_etat(n_e)
                if t is not None:
                    w_i = wmini - 40 * k; h_i = w_i * t.height / t.width
                    spr = pyglet.sprite.Sprite(t, x=mx + 20 * k, y=y1 - 40 * k - h_i); spr.scale_x = w_i / t.width; spr.scale_y = h_i / t.height; spr.draw()
                    liste = []
                    if inf:
                        liste = [self._date_fr(inf[0].get('date')) or 'Sans date', self._lieu_lisible(inf[0])]
                    for j, ligne in enumerate(liste):
                        el = self._et(ligne, fsp * 1.1, BLANC if j == 0 else GRIS); el.x = mx + (wmini - el.content_width) / 2; el.y = y1 - 40 * k - h_i - 34 * k - j * 30 * k; el.draw()
                else:
                    el = self._et('Emplacement vide' if not inf else 'Pas de miniature', fs, GRIS); el.x = mx + (wmini - el.content_width) / 2; el.y = y1 - h / 2; el.draw()
        if self.deroule is not None and self.deroule[0] in lignes and self.deroule[0] < n and e[self.deroule[0]]['t'] == 'choix':
            self._dessiner_liste(e[self.deroule[0]], lignes[self.deroule[0]], xr + 6 * k, k, fs)
        self._dessiner_infobulle(e, n, lignes, plx, plw, k, fsp, W, H)
        self._dessiner_popup(k, fs, fsp, W, H)

    # ---- infobulles (aides au survol de la souris) et fenetre modale
    AIDE_TOUCHE = "Entrée : changer la touche   ←/→ : case   Suppr : effacer   Début ou bouton rond : touche d'origine"
    AIDE_ETATS = {'creer': "Entrée : enregistrer ici (écrase l'état)", 'charger': 'Entrée : charger cet état', 'supprimer': 'Entrée : supprimer cet état'}

    def _aide_ligne(self, en):
        """Texte d'aide d'une ligne du menu ('   ' separe les lignes de l'infobulle) ; '' s'il n'y en a pas."""
        t = en['t']
        if t == 'touche': return en.get('aide') or self.AIDE_TOUCHE
        sup = en['aide'] + '   ' if en.get('aide') and t != 'act' else ''          # texte propre a la ligne, avant la consigne generale
        if t == 'curs': return sup + 'Glisser ou ←/→ : changer la valeur   Clic sur la valeur : la taper   Suppr ou bouton rond : valeur par défaut'
        if t == 'choix':
            return sup + ('Entrée ou clic : activer / désactiver   ←  : Non   →  : Oui' if en.get('sw') else 'Entrée ou clic : ouvrir la liste   ←/→ : valeur précédente / suivante')
        if t == 'act' and en.get('aide'): return en['aide']
        if t == 'slot': return self.AIDE_ETATS[self.action_etat]
        if self.ecran == 'interface': return "Glisse l'élément choisi pour le placer   Échap ou clic droit : terminer   Tab : replier le panneau"
        return ''

    def _lignes_aide(self, texte, maxw, fz):
        """Lignes d'une infobulle : coupees aux espaces triples, puis a la largeur maxw."""
        import re
        out = []
        for l in re.split(r'\s{3,}', texte.strip()):
            cur = ''
            for mot in l.split(' '):
                essai = (cur + ' ' + mot).strip()
                if cur and self._et(essai, fz).content_width > maxw: out.append(cur); cur = mot
                else: cur = essai
            if cur: out.append(cur)
        return out

    def _dessiner_infobulle(self, e, n, lignes, plx, plw, k, fsp, W, H):
        """Infobulle : aide de la ligne survolee par la souris (apres 0,4 s), ou consigne de la saisie / de la capture d'une touche sous la ligne choisie."""
        if self.popup is not None: self.tt = None; return
        fz = fsp * 1.05; texte = ''; ancre = None
        i_sel = min(self.sel.get(self.ecran, 0), max(0, n - 1))
        if self.capture is not None: texte = "Appuie sur la touche pour « %s »   Échap : annuler   Suppr : effacer" % dict(RG.ACTIONS)[self.capture[0]]; ancre = i_sel
        elif self.saisie is not None: texte = 'Tape la valeur   Entrée : valider   Échap : annuler'; ancre = self.saisie[0]
        elif self.deroule is not None: self.tt = None; return
        elif self.pan_appui is not None: self.tt = None; return                       # (pas d'infobulle pendant un appui sur la barre de titre)
        elif self.zone_plier and self.mode_souris and self.pos_souris and self._dans(self.zone_plier, *self.pos_souris):
            cle = ('plier', 0)
            if self.tt is None or self.tt[0] != cle: self.tt = (cle, time.time())
            if time.time() - self.tt[1] > 0.4: texte = "Appui court : replier / déplier le panneau (Tab)   Appui long : le déplacer   Double clic : le remettre à sa place"
        elif self.mode_souris and self.pos_souris and self.capture is None:
            i, _ = self._zone(*self.pos_souris); cle = (self.ecran, i)
            if i is None or i >= n: self.tt = None; return
            if self.tt is None or self.tt[0] != cle: self.tt = (cle, time.time())
            if time.time() - self.tt[1] > 0.4: texte = self._aide_ligne(e[i])
        else: self.tt = None
        if not texte: return
        ls = self._lignes_aide(texte, 520 * k, fz)
        if not ls: return
        ets = [self._et(l, fz, BLANC) for l in ls]; lh = fz * 1.65
        w = max(et.content_width for et in ets) + 28 * k; h = len(ets) * lh + 18 * k
        if ancre is not None and ancre in lignes:                                   # consigne : sous la ligne choisie (au-dessus s'il n'y a pas la place)
            yb, yt = lignes[ancre]; x = plx + 24 * k; y = yb - 8 * k - h
            if y < 8 * k: y = yt + 8 * k
        else:
            mx, my = self.pos_souris; x = mx + 14 * k; y = my - 20 * k - h
            if y < 8 * k: y = my + 22 * k
        x = max(8 * k, min(x, W - w - 8 * k)); y = max(8 * k, min(y, H - h - 8 * k))
        HM.cadre(x, y, w, h, k * 0.5, 0.0, fond=NOIR, opacite=0.94)
        for j, et in enumerate(ets): et.x = x + 14 * k; et.y = y + h - 9 * k - lh * (j + 1) + (lh - fz * 1.0) * 0.45; et.draw()

    def _dessiner_popup(self, k, fs, fsp, W, H):
        """Fenetre modale Oui / Non (suppression d'un etat) : le menu reste visible, assombri ; Non est preselectionne."""
        self.zones_popup = []
        p = self.popup
        if p is None: return
        voile = pyglet.shapes.Rectangle(0, 0, W, H, color=(0, 0, 0)); voile.opacity = 120; voile.draw()
        et = self._et(p['titre'], fs * 1.2, BLANC); ed = self._et(p['detail'], fsp * 1.15, GRIS) if p.get('detail') else None
        bw, bh = 150 * k, 46 * k; w = max(2 * bw + 60 * k, et.content_width + 80 * k, (ed.content_width + 80 * k) if ed else 0); h = 200 * k
        x, y = (W - w) / 2, (H - h) / 2
        self._cadre(x, y, w, h, k)
        et.x = x + (w - et.content_width) / 2; et.y = y + h - 62 * k; et.draw()
        if ed: ed.x = x + (w - ed.content_width) / 2; ed.y = y + h - 92 * k; ed.draw()
        for i, lib in enumerate(('Oui', 'Non')):
            bx = x + w / 2 + (-bw - 14 * k if i == 0 else 14 * k); by = y + 28 * k; sel = p['sel'] == i
            self._plaque(bx, by, bw, bh, k, sel, JAUNE if sel and self.mode_souris else None)
            if sel and not self.mode_souris: self._curseur(bx - 24 * k, by + bh / 2, min(bh * 0.6, 26 * k))
            lb = self._et(lib, fs, BLANC); lb.x = bx + (bw - lb.content_width) / 2; lb.y = by + bh / 2 - 0.45 * fs; lb.draw()
            self.zones_popup.append((bx, by, bx + bw, by + bh, i))

    def _dessiner_liste(self, en, ligne, xd, k, fs):
        """Liste deroulante d'un choix : sous la ligne (au-dessus s'il n'y a pas la place), valeur courante en or, curseur dore comme dans les menus du jeu ; une barre de defilement
        (fleches, curseur, clic sur la piste, molette = valeur suivante) quand toutes les valeurs ne tiennent pas."""
        J = self.J; vals = en['vals']; noms = [self._nom_valeur(en['l'], v) for v in vals]; cur = self.deroule[1]; H = J.height; n = len(vals)
        ih = 36 * k; nvis = max(1, min(n, 8, int((H - 40 * k) // ih)))
        barre = n > nvis; lb = (LARG_BARRE + 12) * k if barre else 0.0                          # place de la barre de defilement, a droite des valeurs
        w = max(max(self._et(t, fs).content_width for t in noms) + 90 * k + lb, 240 * k); h = nvis * ih + 20 * k
        ybas, ytop = ligne; y1 = ybas - 4 * k; y0 = y1 - h
        if y0 < 8 * k: y1 = ytop + 4 * k; y0 = y1 - h
        if y0 < 8 * k: y0 = 8 * k; y1 = y0 + h
        x1 = xd; x0 = x1 - w
        self._cadre(x0, y0, w, h, k); self.cadre_liste = (x0, y0, x1, y1)
        if self.liste_top is None: self.liste_top = max(0, min(cur - nvis // 2, n - nvis)); self.liste_cur_vu = cur
        elif self.liste_cur_vu != cur:                                                         # la valeur surlignee a change : la vue la suit ; sinon seule la barre ou la molette la deplace
            if cur < self.liste_top or (cur - 1 < self.liste_top and cur > 0 and self._entete(vals[cur - 1])): self.liste_top = cur - 1 if cur > 0 and self._entete(vals[cur - 1]) else cur          # (le premier choix d'un groupe montre son intertitre)
            elif cur >= self.liste_top + nvis: self.liste_top = cur - nvis + 1
            self.liste_cur_vu = cur
        top = self.liste_top = max(0, min(self.liste_top, n - nvis))
        self.zones_pop = []; y = y1 - 10 * k
        for j in range(top, top + nvis):
            yb = y - ih; courant = vals[j] == en['get']()
            if self._entete(vals[j]):                                                          # intertitre de groupe : au centre de la liste, en or, sans zone de clic
                et = self._et(noms[j], fs * 0.92, OR); et.x = x0 + (w - lb - et.content_width) / 2; et.y = yb + (ih - fs * 1.33) / 2 + 5 * k; et.draw()
                pyglet.shapes.Rectangle(x0 + 14 * k, yb + 3 * k, w - lb - 28 * k, max(1, int(k)), color=(120, 110, 40)).draw(); y -= ih; continue
            if j == cur:
                if self.mode_souris: self._plaque(x0 + 6 * k, yb + 2 * k, w - 12 * k - lb, ih - 4 * k, k * 0.8, True, JAUNE)
                else: self._curseur(x0 + 8 * k, yb + ih / 2, 22 * k)
            et = self._et(noms[j], fs, OR if courant else BLANC); et.x = x0 + 44 * k; et.y = yb + (ih - fs * 1.33) / 2 + 5 * k; et.draw()
            self.zones_pop.append((x0 + 6 * k, yb, x1 - 6 * k - lb, y, j)); y -= ih
        if barre: self.barre_liste = self._barre_defilement(x1 - 8 * k, y1 - 10 * k, y0 + 10 * k, n, nvis, top, k, self.glisse_liste is not None, 0)
        else: self.barre_liste = None
