"""Fenetre « Historique » (page 'historique' du menu Pause, voir pause.py) : deux onglets, Dialogues (hors combat) et Combats ; le plus recent en bas. Une case a cocher « Favoris seulement » (a droite des onglets) ne garde dans
la liste de l'onglet ouvert que ses favoris ; elle est commune aux deux onglets (elle reste cochee quand on change d'onglet et quand on rouvre la fenetre) et son etat est enregistre dans les reglages (cle `historique_favoris_seuls`, ecrite a chaque changement) :
elle est retrouvee telle quelle d'une session a l'autre, comme les favoris eux-memes (fichier historique_favoris.json, voir historique.py).

LA LISTE EST UNE SEULE COLONNE CONTINUE : les plus anciennes entrees en haut, les plus recentes en bas, et la vue s'ouvre tout en bas (derniere entree visible). Le defilement est continu, au pixel : aucune page, aucun cran, aucune
mise en page qui depend de la position (les boites sont posees une fois pour toutes, la position ne fait que les deplacer) ; une entree qui depasse du bord de la liste est simplement coupee par un cadre de decoupe (glScissor), comme du
texte qui defile. Liste plus courte que la fenetre : collee en bas, comme un fil de messages (le plus recent reste toujours au meme endroit, en bas). Fonctions pures : `disposer` (empilement), `element_au_repere`.

Chaque element est dessine dans une BOITE DE DIALOGUE du jeu (la fenetre de message du terrain, 3 lignes : cadre 452 x 126 unites d'interface, tire de la mise en page d'origine ; meme echelle que dans le jeu ; classe
`Boite`), avec le cadre et l'onglet du nom du jeu (frameData 192 et 191, dessines par ui_menu.FenetreMessage), la police d'origine SE-GARRIR et les lignes posees comme dans le jeu : un dialogue avec le nom du locuteur
dans l'onglet SEULEMENT si le jeu l'affichait quand il a ete dit ; un combat avec son issue, chaque espece d'ennemis (qui est vaincu, enfui, disparu ou reste), l'or et l'experience gagnes et les objets obtenus.
Un dialogue tient dans une boite de 3 lignes (la suite est dans une boite suivante, « 2/2 » : simple etiquette, le defilement ne s'y arrete pas). Un COMBAT GRANDIT EN HAUTEUR pour tout contenir (#141) : la boite a autant
de lignes que le combat en demande, au moins 3 ; le cadre du jeu est etire (c'est un cadre a neuf morceaux : seul le milieu s'allonge, les coins gardent leur taille) ; au-dela de MAX_LIGNES_COMBAT lignes, le reste
continue dans une boite suivante. Une etoile en haut a droite de chaque element le met en favori (il est alors garde
dans un fichier jusqu'a ce qu'on retire l'etoile ; le reste de l'historique disparait quand on ferme la visionneuse). Le fond de la fenetre est aussi transparent que les autres fenetres du jeu (hud_mobile.OPACITE_JEU).
Le jeu NE S'ARRETE PAS tant que la fenetre est ouverte (#178 : aucune pause dans aucun menu) : aucune touche ni clic n'arrive au jeu, mais il continue de tourner et d'ecrire dans l'historique ; la liste suit (`suivre_le_jeu` : les nouveaux
messages s'ajoutent en bas quand la vue est en bas ; quand on lit plus haut, la liste ne bouge pas, elle se met a jour au retour en bas).
Clavier : haut / bas (message precedent / suivant, repete si la touche est maintenue), page precedente / suivante (une page de la fenetre moins deux lignes), debut / fin, gauche / droite (onglet), Entree, Menu ou Action
(etoile du message choisi), F ou Carte (case « Favoris seulement »), la touche de l'historique (Dialogues -> Combats -> ferme), Echap / Annuler (retour). Souris : molette (2 lignes par cran), barre de defilement (fleches : une ligne,
piste : une page, curseur : glisser), glisser dans la liste (le contenu suit le pointeur), clic sur un onglet, sur la case ou sur une etoile.
MESSAGE CHOISI (`sel`, cible de la touche Entree) : haut / bas passent de message en message (ils ne font pas defiler la liste) ; la vue ne defile QUE pour montrer en entier le message choisi, quand il est coupe par un bord de la
fenetre ou hors de la fenetre, et du minimum necessaire (son bord rejoint le bord de la fenetre : `decalage_pour_voir`). A la souris, le message survole est le message choisi. Le message choisi porte la petite fleche doree, au clavier
comme a la souris, et rien d'autre : ni grisé ni eclairci au survol ou au choix (derogation a la regle generale des menus). Defiler a la molette, a la barre ou en glissant ne change pas le message choisi ; au clavier, un message
choisi qui n'est plus du tout dans la fenetre est d'abord remplace par le plus proche message visible."""
import pyglet
from pyglet import gl
from dq4_pc.noyau import historique as HI
from dq4_pc.menus import hud_mobile as HM
from dq4_pc.persistance import reglages as RG
from dq4_pc.menus import ui_menu as UM

OR = (255, 235, 4); BLANC = (255, 255, 255); GRIS = (150, 150, 150); AIDE = (175, 175, 175); ETOILE = (255, 210, 40); VIDE_ETOILE = (20, 20, 20)
TOLERANCE_GLISSE = 6.0               # pixels : en dessous, un appui dans la liste n'est pas un glissement
ONGLETS = (('Dialogues', 'dialogues'), ('Combats', 'combats'))
O_DIALOGUES, O_COMBATS = 0, 1
LIBELLE_FILTRE = 'Favoris seulement'
ECHELLE_BOITE = 1.12                 # agrandissement des fenetres du jeu par rapport a H / 800 (= fenetre.UI_ZOOM) : la boite de l'historique a la taille d'une boite de dialogue du jeu a l'ecran
TEXTE_ECH = 1.09                     # un pixel de la police d'origine (SE-GARRIR) = 1,09 unite d'interface dans le canevas de message du jeu (mesure : ligne de 371 pixels de police = 407 pixels a l'ecran a l'echelle 1,008 ; l'en-tete de la mise en page annonce 1,105, le moteur arrondit les avances)
VIDES = {'dialogues': 'Aucun dialogue pour l\'instant.', 'combats': 'Aucun combat pour l\'instant.'}
VIDES_FAVORIS = {'dialogues': 'Aucun dialogue en favori : décoche « Favoris seulement », choisis un dialogue et appuie sur Entrée (ou clique son étoile) pour le garder.',
                 'combats': 'Aucun combat en favori : décoche « Favoris seulement », choisis un combat et appuie sur Entrée (ou clique son étoile) pour le garder.'}


def couper_mots(texte, largeur, larg_max):
    """Coupe `texte` en lignes aux espaces pour qu'aucune ne depasse `larg_max` (largeur(t) = largeur d'une ligne t, dans l'unite de larg_max). Un mot seul plus large que la limite reste seul sur sa ligne (il ne peut pas etre coupe). -> liste de lignes, jamais vide."""
    lignes = []; cur = ''
    for mot in texte.split():
        cand = mot if not cur else cur + ' ' + mot
        if cur and largeur(cand) > larg_max: lignes.append(cur); cur = mot
        else: cur = cand
    lignes.append(cur)
    return lignes


PAS_MOLETTE = 2.0                    # lignes de texte (Boite.PAS : 28 unites) par cran de molette : un pas fin et constant, jamais une entree entiere
MARGE_LISTE = 6.0                    # (en k) vide au-dessus de la premiere boite et sous la derniere de la liste (le contenu n'est jamais colle au bord de la fenetre de decoupe)
TOLERANCE_PX = 0.5                   # pixels : en dessous, un message est « entierement visible » (arrondis du dessin)
ECART_ELEMENTS, ECART_PAGES = 12.0, 4.0      # (en k) vide entre deux elements, entre deux boites d'un meme element
MAX_LIGNES_COMBAT = 12               # lignes de texte (entete comprise) qu'une boite de combat peut contenir avant de continuer dans une boite suivante (la boite fait alors 126 + 9 x 28 = 378 unites de haut)


def disposer(entrees, haut_cadre, haut_onglet, ecart, ecart_page, marge):
    """Empile toute la liste dans UNE colonne, du plus ancien (en haut) au plus recent (en bas). `entrees` : un tuple par element, (nombre de boites, onglet du nom sur la premiere ?) ou (nombre de boites, onglet ?,
    [hauteur du cadre de chaque boite]) quand les boites n'ont pas toutes la meme hauteur (un combat grandit avec son texte) ; `haut_cadre` est la hauteur des autres. Distances en pixels, comptees depuis
    le haut du contenu (vers le bas) : -> (boites, debuts, fins, hauteur).
    boites : (element, boite, nombre de boites, haut, haut de l'onglet, haut du cadre) ; `haut` = bord superieur de la boite, onglet du nom compris (le cadre commence `haut_onglet` plus bas) ;
    debuts[i], fins[i] : haut de la premiere boite et bas de la derniere de l'element i ; hauteur : hauteur du contenu, marges haute et basse comprises (0 si la liste est vide).
    Ne depend d'aucune position de defilement : la position ne fait que deplacer le tout."""
    boites = []; debuts = []; fins = []; y = marge
    for i, ent in enumerate(entrees):
        nb, avec_nom = ent[0], ent[1]; hauts = ent[2] if len(ent) > 2 else ()
        debuts.append(y)
        for p in range(max(1, nb)):
            hn = haut_onglet if (p == 0 and avec_nom) else 0.0; hc = hauts[p] if p < len(hauts) else haut_cadre
            boites.append((i, p, max(1, nb), y, hn, hc)); y += hn + hc
            if p < max(1, nb) - 1: y += ecart_page
        fins.append(y); y += ecart
    return boites, debuts, fins, ((y - ecart + marge) if entrees else 0.0)


def etendue(debuts, fins, hc, i):
    """Ce qu'il faut montrer pour que le message i soit « entierement visible » : (haut, bas) en pixels depuis le haut du contenu. Le message lui-meme (debuts[i] : onglet du nom compris, fins[i]) ; pour le premier et le dernier
    de la liste, la marge de la liste en plus (le premier va jusqu'au haut du contenu, le dernier jusqu'au bas : quand on y arrive, la liste est tout en haut / tout en bas)."""
    return (0.0 if i == 0 else debuts[i]), (hc if i == len(debuts) - 1 else fins[i])


def decalage_pour_voir(debuts, fins, hc, hv, decal, i):
    """Nouveau decalage de la vue (pixels depuis le bas : 0 = tout en bas) qui montre le message i en entier, en changeant le decalage DU MINIMUM : inchange si le message est deja entierement visible, sinon juste ce qu'il faut pour que
    son bord coupe rejoigne le bord de la fenetre (haut ou bas). Un message plus haut que la fenetre : son debut en haut de la fenetre. La fenetre fait hv pixels et montre, depuis le haut du contenu, de hc - decal - hv a hc - decal."""
    haut, bas = etendue(debuts, fins, hc, i); top = hc - decal - hv
    if bas - haut >= hv: top = haut
    elif haut < top - TOLERANCE_PX: top = haut
    elif bas > top + hv + TOLERANCE_PX: top = bas - hv
    else: return decal
    return min(max(0.0, hc - hv), max(0.0, hc - hv - top))


def elements_visibles(debuts, fins, hc, hv, decal, entiers):
    """Indices des messages visibles dans la fenetre (voir decalage_pour_voir) : ceux qui y sont entierement (`entiers`), sinon ceux dont une partie au moins y est."""
    top = hc - decal - hv; r = []
    for i in range(len(debuts)):
        haut, bas = etendue(debuts, fins, hc, i)
        if (haut >= top - TOLERANCE_PX and bas <= top + hv + TOLERANCE_PX) if entiers else (fins[i] > top and debuts[i] < top + hv): r.append(i)
    return r


def heure_jeu(t):
    """Temps de jeu (1/60 s) -> « 1:05:12 »."""
    s = max(0, int(t)) // 60
    return '%d:%02d:%02d' % (s // 3600, s % 3600 // 60, s % 60)


def onglet_suivant(i, d=1): return (i + d) % len(ONGLETS)


def touche_suivante(onglet):
    """Touche de l'historique dans la fenetre : Dialogues -> Combats ; Combats -> fermer (None)."""
    return O_COMBATS if onglet == O_DIALOGUES else None


class Boite:
    """Boite de dialogue du terrain (MenuMessage type 0) a 3 lignes, en unites d'interface du jeu (800 de haut) : la taille du cadre (frameData 192), de l'onglet du nom (frameData 191) et le placement des lignes
    de texte. Les dimensions viennent de la mise en page d'origine quand elle est chargee (`depuis`), sinon des valeurs mesurees sur les captures du jeu. Une seule boite pour tout : 1, 2 ou 3 lignes, dialogue ou combat."""
    LARG, HAUT = 452.0, 126.0                  # cadre : x -223 a 229, z -251 a -125
    ONGLET_L, ONGLET_H = 246.0, 32.0           # onglet du nom : x -223 a 23, z -125 a -93 (depasse au-dessus du cadre)
    LIGNES, PAS = 3, 28.0                      # trois lignes de 28 (MiseEnPage : limiter_lignes(types[0], 3, 28.0))
    TEXTE_X, BASE_1 = 12.0, 37.2               # bord gauche du texte et ligne de base de la 1re ligne : distances au coin haut gauche du cadre (mesurees sur une capture du jeu : texte a 11 px du trait gauche du cadre, 1re ligne de base a 31 px du trait haut, a l'echelle 1,008)
    NOM_X, NOM_HAUT = 118.5, -21.0             # milieu du nom (depuis le bord gauche du cadre) et haut du texte du nom (depuis le haut du cadre : MenuMessage.m_who, 21 au-dessus) -- repli sans mise en page

    def __init__(self, larg=None, haut=None, onglet=None, x0=-223.0, z0=-251.0, win=(0.0, 10.0, 86.0), texte_ech=TEXTE_ECH):
        if larg: self.LARG = larg
        if haut: self.HAUT = haut
        if onglet: self.ONGLET_L, self.ONGLET_H = onglet
        self.x0, self.z0, self.win, self.texte_ech = x0, z0, tuple(win), texte_ech

    @classmethod
    def depuis(cls, ml):
        """Boite lue dans la mise en page d'origine (MiseEnPage) ; les valeurs mesurees si elle manque ou est inutilisable."""
        try:
            t = ml.message['types'][0]; vt = t['frame_mesh']['vtx']; xs = [v[0] for v in vt]; zs = [v[1] for v in vt]
            onglet = None
            if len(ml.cadres) > UM.CADRE_AVEC_NOM:
                c = ml.cadres[UM.CADRE_AVEC_NOM]['vtx']; hs = [v for v in c if v[1] > max(zs) + 0.5]
                if hs: onglet = (max(v[0] for v in hs) - min(v[0] for v in hs), max(v[1] for v in hs) - max(zs))
            return cls(max(xs) - min(xs), max(zs) - min(zs), onglet, min(xs), min(zs), t['win'])
        except Exception:
            return cls()

    MARGES = 120.0                              # (en unites de k) marges de la fenetre de l'historique autour de la boite : gauche, colonne de l'etoile, barre de defilement

    def echelle(self, H, W, k):
        """Pixels par unite : celle des fenetres du jeu (H / 800 x ECHELLE_BOITE), reduite pour que la boite, sa colonne d'etoile et les marges tiennent dans la fenetre de la visionneuse."""
        return max(0.3, min(H / 800.0 * ECHELLE_BOITE, (W - 40 * k - self.MARGES * k) / self.LARG))

    def base(self, rang):
        """Distance de la ligne de base de la ligne `rang` (0, 1, 2...) au haut du cadre, unites."""
        return self.BASE_1 + rang * self.PAS

    BASE_MSG = 35.0                            # idem avec la police des messages du jeu (celle du canevas du moteur) : le canevas commence 15 unites sous le haut du cadre, la cellule d'une ligne a 20 rangees au-dessus de la ligne de base

    def base_msg(self, rang):
        """Comme `base`, pour le texte dessine avec la police des messages du jeu."""
        return self.BASE_MSG + rang * self.PAS

    def haut_pour(self, lignes):
        """Hauteur du cadre (unites) pour `lignes` lignes de texte : celle de la boite du jeu jusqu'a 3 lignes, puis une ligne (PAS) de plus par ligne."""
        return self.HAUT + max(0, int(lignes) - self.LIGNES) * self.PAS

    def largeur_texte(self):
        """Largeur utile d'une ligne de texte (unites) : du bord gauche du texte a la marge droite du canevas (le canevas est large de LARG - 18)."""
        return self.LARG - self.TEXTE_X - 12.0


def etirer_cadre(vtx, extra):
    """Sommets d'un cadre a neuf morceaux (frameData 192 : coins de 12 unites, milieu qui s'etire) allonges de `extra` unites vers le haut : tout sommet de la moitie haute monte, les coins du haut gardent leur taille, le
    milieu s'allonge (ses UV ne changent pas : le motif du milieu est etire, comme le fait le jeu quand il agrandit un cadre). -> nouvelle liste (la mise en page d'origine n'est jamais modifiee)."""
    if not vtx: return []
    zs = [v[1] for v in vtx]; mi = (min(zs) + max(zs)) / 2.0
    return [[v[0], v[1] + (extra if v[1] > mi else 0.0)] + list(v[2:]) for v in vtx]


def lignes_de_boite(page, premiere, combat):
    """Nombre de lignes de texte d'une boite : les rangees de la page, plus l'entete (issue et heure) sur la premiere boite d'un combat ; trois au moins (la boite du jeu)."""
    return max(Boite.LIGNES, len(page) + (1 if (combat and premiere) else 0))


def paginer(rangees, avec_entete, lignes=3):
    """Rangees de texte -> pages de `lignes` rangees au plus (au moins une page, meme vide) ; sur la 1re page d'un combat, l'entete (issue et heure) prend une rangee."""
    pages = []; cap = max(1, lignes - (1 if avec_entete else 0)); i = 0
    while True:
        pages.append(list(rangees[i:i + cap])); i += cap; cap = lignes
        if i >= len(rangees): return pages


def couper_comme_le_jeu(police, texte):
    """Lignes de `texte` coupees comme le moteur coupe un message (PoliceMessages.couper : les retours a la ligne du texte gardes, sans espace en fin de ligne ni ligne vide a la fin ; au moins une ligne)."""
    lignes = [l.rstrip(' ') for l in police.couper(texte)]
    while lignes and not lignes[-1]: lignes.pop()
    return lignes or ['']


def rangees_de(e, mesure, largeur, police=None):
    """Rangees de texte d'un element, coupees a `largeur` (mesure(chaine) -> largeur dans la meme unite) : le texte d'un dialogue (ses retours a la ligne gardes) ; pour un combat une rangee par espece d'ennemis (avec le
    sort de chacun), puis l'or et l'experience, puis les objets (HI.lignes_combat) ; une ligne trop large pour la boite continue sur la rangee suivante. L'issue et l'heure sont dans l'entete.
    Avec `police` (la police des messages du jeu, PoliceMessages) les lignes sont coupees exactement comme le moteur coupe les siennes et `mesure`, `largeur` ne servent pas."""
    coupe = (lambda t: couper_comme_le_jeu(police, t)) if police is not None else (lambda t: HI.envelopper(t, largeur, mesure))
    if e.type != HI.TYPE_COMBAT: return coupe(e.texte)
    out = []
    for l in HI.lignes_combat(e): out.extend(coupe(l))
    return out


class VueHistorique:
    def __init__(self, pause):
        self.P = pause; self.J = pause.J
        self.onglet = O_DIALOGUES; self.elements = []
        self.pos = 0.0                                                  # position de defilement, en pixels : 0 = tout en bas (le plus recent visible), plus grand = plus ancien (voir decal et repere)
        self.sel = 0                                                    # message choisi (fleche doree, touche Entree) : choisi par haut / bas, par un clic ou, a la souris, par le survol (voir dessiner)
        self.hc = self.hv = 0.0; self.pas = Boite.PAS                  # hauteur du contenu, de la fenetre de la liste (pixels) et d'une ligne de texte (pixels), mesures a la derniere image ; avant la premiere image : rien a defiler
        self.centrer = None                                             # element a ramener au milieu de la vue des que la liste est mesuree (aller)
        self.debuts = []; self.fins = []                               # haut de la premiere boite et bas de la derniere de chaque element, pixels depuis le haut du contenu (mesures a la derniere image ; vides tant que la liste n'est pas mesuree)
        self.zones = []; self.zones_etoile = []; self.zones_onglet = []; self.barre = None; self.glisse_barre = None
        self.zone_ret = None
        self.favoris_seuls = self._lire_filtre(); self.zone_filtre = None  # case « Favoris seulement » : cochee ? (reglage enregistre) ; sa zone a l'ecran (clic)
        self.drag = None                                               # glissement dans la liste : [y de depart, decalage de depart, deplace ?]
        self._spr = {}; self._lignes = {}; self._mise = None; self._s_prec = None
        self._boite = None; self._boite_ml = None; self._fens = {}              # boite de dialogue standard (Boite) et les deux fenetres de message du jeu qui servent a dessiner son cadre (avec / sans onglet)

    # ---- donnees
    def entrer(self, onglet=O_DIALOGUES):
        """A l'ouverture de la page : recharge la liste, tout en bas sur l'element le plus recent (ensuite elle suit le jeu : `suivre_le_jeu`)."""
        self.onglet = onglet if 0 <= onglet < len(ONGLETS) else O_DIALOGUES
        self.glisse_barre = None; self.drag = None; self._lignes.clear()
        self.favoris_seuls = self._lire_filtre()
        h = getattr(self.J, 'historique', None)
        if h is not None and hasattr(h, 'actualiser'): h.actualiser()          # (les favoris ranges par la cle : leur texte est redemande au jeu, voir Historique.actualiser)
        self.recharger()

    def recharger(self, garder=False):
        h = getattr(self.J, 'historique', None)
        self.elements = h.liste(ONGLETS[self.onglet][1], self.favoris_seuls) if h is not None else []
        n = len(self.elements); self._mise = None; self.centrer = None; self.debuts = []; self.fins = []
        if garder: self.sel = max(0, min(n - 1, self.sel))
        else: self.pos = 0.0; self.sel = max(0, n - 1)
        self.zones = []; self.zones_etoile = []

    def suivre_le_jeu(self):
        """Le jeu tourne derriere la fenetre (#178) et peut ecrire dans l'historique (un dialogue, la fin d'un combat). Appele a chaque image : quand la vue est tout en bas (rien n'est cache plus bas), la liste est remplacee par la
        liste a jour ; le message choisi reste le meme (reconnu par son objet), sauf s'il etait le dernier : le choix suit alors le plus recent. Quand on lit plus haut, un glissement ou la barre est en cours, la liste ne bouge pas
        (la lecture ne saute pas) ; elle se met a jour des qu'on revient en bas. -> True si la liste a change."""
        h = getattr(self.J, 'historique', None)
        if h is None or self.decal() > 0.5 or self.drag is not None or self.glisse_barre is not None: return False
        el = h.liste(ONGLETS[self.onglet][1], self.favoris_seuls); anc = self.elements
        if len(el) == len(anc) and all(a is b for a, b in zip(el, anc)): return False
        cur = self.courant(); suivre = cur is None or self.sel >= len(anc) - 1
        self.elements = el; n = len(el); self._mise = None; self.centrer = None; self.debuts = []; self.fins = []; self.zones = []; self.zones_etoile = []; self.pos = 0.0
        i = None if suivre else next((k for k, e in enumerate(el) if e is cur), None)
        self.sel = max(0, n - 1) if i is None else i
        return True

    def changer_onglet(self, i):
        i %= len(ONGLETS)
        if i != self.onglet: self.onglet = i; self.recharger()

    # ---- case « Favoris seulement » : son etat est un reglage (historique_favoris_seuls), garde d'une session a l'autre
    def _lire_filtre(self):
        try: return self.J.reg['historique_favoris_seuls'] is True
        except Exception: return False

    def _ecrire_filtre(self, on):
        """Enregistre l'etat de la case dans les reglages (reglages.json, tout de suite : une fermeture brutale ne le perd pas). Une erreur n'empeche jamais de cocher ou de decocher."""
        try: reg = self.J.reg; reg['historique_favoris_seuls'] = bool(on); reg.enregistrer()
        except Exception: pass

    def basculer_filtre(self):
        """Coche ou decoche « Favoris seulement » (valable pour les deux onglets, enregistre dans les reglages). L'element choisi, s'il est dans la nouvelle liste, reste choisi (et la vue se recentre sur lui) ; sinon on se place sur le plus recent."""
        cur = self.courant(); cle = cur.cle() if cur is not None else None
        self.favoris_seuls = not self.favoris_seuls; self._ecrire_filtre(self.favoris_seuls); self.recharger()
        if cle is not None:
            for i in range(len(self.elements) - 1, -1, -1):
                if self.elements[i].cle() == cle: self.aller(i); break
        return self.favoris_seuls

    def courant(self):
        return self.elements[self.sel] if 0 <= self.sel < len(self.elements) else None

    def etoile(self, i=None):
        """Met en favori (ou retire des favoris) l'element i (l'element actif par defaut) ; -> True si c'est maintenant un favori. Avec « Favoris seulement », l'element retire disparait de la liste (la vue reste ou elle est)."""
        h = getattr(self.J, 'historique', None)
        if h is None: return False
        e = self.courant() if i is None else (self.elements[i] if 0 <= i < len(self.elements) else None)
        if e is None: return False
        r = h.basculer_favori(e)
        if self.favoris_seuls: self.recharger(garder=True)
        return r

    # ---- defilement continu (aucune page, aucun cran : la position est un nombre de pixels)
    def plage(self):
        """Distance (pixels) dont la vue peut monter depuis le bas : 0 quand toute la liste tient dans la fenetre."""
        return max(0.0, self.hc - self.hv)

    def decal(self):
        """Decalage reel de la vue (pixels) : la position bornee a la plage de defilement."""
        return min(max(self.pos, 0.0), self.plage())

    def page_px(self): return max(self.pas, self.hv - 2 * self.pas)

    def _visibles(self, entiers):
        n = len(self.elements)
        if not n or len(self.debuts) != n: return []
        return elements_visibles(self.debuts, self.fins, self.hc, self.hv, self.decal(), entiers)

    def _ramener(self, entiers=False):
        """Le message choisi doit etre dans la fenetre : sinon (la liste a defile sans lui : molette, barre, glissement, page), c'est le plus proche message visible (le premier s'il est au-dessus de la fenetre, le dernier s'il est
        en dessous). `entiers` : seuls comptent les messages entierement visibles (a defaut, ceux qui le sont en partie). -> True si le message choisi a change."""
        v = self._visibles(entiers) or (self._visibles(False) if entiers else [])
        if not v or self.sel in v: return False
        self.sel = v[0] if self.sel < v[0] else v[-1]; return True

    def _montrer(self, i):
        """Defile du minimum pour montrer le message i en entier (rien si la liste n'est pas encore mesuree : la vue se placera des qu'elle le sera)."""
        if len(self.debuts) != len(self.elements): self.centrer = i; return
        self.pos = decalage_pour_voir(self.debuts, self.fins, self.hc, self.hv, self.decal(), i)

    def bouger(self, d):
        """Haut / bas : le message d rangs plus loin (negatif : plus ancien, vers le haut de l'ecran), borne a la liste ; la vue defile seulement si ce message n'est pas entierement visible, du minimum necessaire. Repete par Pause.maj tant que la touche est maintenue."""
        n = len(self.elements)
        if not n: return
        if not self._ramener(): self.sel = max(0, min(n - 1, self.sel + int(d)))          # (un message choisi sorti de la fenetre par la molette ou la barre : cet appui le remplace par le plus proche message visible, sans avancer d'un rang de plus)
        self._montrer(self.sel)

    def page(self, d):
        """Page precedente (d negatif) / suivante : la vue defile de la hauteur de la fenetre moins deux lignes ; le message choisi, s'il sort de la fenetre, devient le plus proche message entierement visible."""
        self.pos = min(self.plage(), max(0.0, self.decal() - d * self.page_px())); self._ramener(True)

    def vers_haut(self):
        if self.elements: self.sel = 0; self.pos = self.plage()
    def vers_bas(self):
        if self.elements: self.sel = len(self.elements) - 1; self.pos = 0.0

    def defiler(self, px):
        """Souris (molette, barre, glissement) : la vue monte de `px` pixels vers les anciens (positif) ou descend vers les recents (negatif), bornee a la plage de defilement."""
        self.pos = min(self.plage(), max(0.0, self.decal() + px))

    def aller(self, i):
        """Choisit l'element i ; la vue se recentre sur lui des que la liste est mesuree (dessin suivant)."""
        n = len(self.elements)
        if not n: return
        self.sel = max(0, min(n - 1, i)); self.centrer = self.sel

    # ---- entrees
    def touche(self, symbol, modifiers=0):
        K = pyglet.window.key; P = self.P; act = self.J.reg.action_de(symbol)
        P.mode_souris = False
        if symbol in (K.ESCAPE, K.BACKSPACE) or act == 'B': P.retour(); return True
        if act == 'historique':                                               # la touche qui ouvre l'historique : Dialogues -> Combats -> ferme tout
            suite = touche_suivante(self.onglet)
            if suite is None: P.fermer()
            else: self.changer_onglet(suite)
            return True
        if symbol == K.UP or act == 'haut': self.bouger(-1); P._repeter(symbol, 'v', -1)
        elif symbol == K.DOWN or act == 'bas': self.bouger(1); P._repeter(symbol, 'v', 1)
        elif symbol == K.PAGEUP or act == 'L': self.page(-1)
        elif symbol == K.PAGEDOWN or act == 'R': self.page(1)
        elif symbol == K.HOME: self.vers_haut()
        elif symbol == K.END: self.vers_bas()
        elif symbol == K.LEFT or act == 'gauche': self.changer_onglet(self.onglet - 1)
        elif symbol == K.RIGHT or act == 'droite': self.changer_onglet(self.onglet + 1)
        elif symbol == K.F or act == 'carte': self.basculer_filtre()                          # (F, ou la touche Carte : « Favoris seulement »)
        elif symbol in (K.RETURN, K.ENTER) or act in ('menu', 'A'): self.etoile()
        return True

    def molette(self, sy):
        """Un cran de molette = PAS_MOLETTE lignes de texte, vers les anciens quand on remonte la molette (un pas fin et constant ; proportionnel au mouvement pour les pavés tactiles)."""
        self.P.mode_souris = True
        self.defiler(max(-5.0, min(5.0, float(sy))) * PAS_MOLETTE * self.pas)

    def survol(self, x, y):
        P = self.P; p = P.pos_souris; P.pos_souris = (x, y)
        if p is None or abs(x - p[0]) + abs(y - p[1]) < 3: return
        P.mode_souris = True

    @staticmethod
    def _dans(z, x, y): return z is not None and z[0] <= x <= z[2] and z[1] <= y <= z[3]

    def clic(self, x, y, bouton):
        M = pyglet.window.mouse; P = self.P
        P.mode_souris = True; P.pos_souris = (x, y)
        if bouton == M.RIGHT: P.retour(); return
        if self._dans(self.zone_ret, x, y): P.retour(); return
        for z in self.zones_onglet:
            if self._dans(z, x, y): self.changer_onglet(z[4]); return
        if self._dans(self.zone_filtre, x, y): self.basculer_filtre(); return
        b = self.barre
        if b and b['x0'] <= x <= b['x1'] and b['y0'] <= y <= b['y1']:
            if y > b['ptop']: self.defiler(self.pas)                                 # fleche du haut : une ligne vers les anciens
            elif y < b['pbot']: self.defiler(-self.pas)
            elif b['pouce'][0] <= y <= b['pouce'][1]: self.glisse_barre = b['pouce'][1] - y
            elif y > b['pouce'][1]: self.defiler(self.page_px())                       # piste au-dessus du curseur : une page vers les anciens
            else: self.defiler(-self.page_px())
            return
        for z in self.zones_etoile:
            if self._dans(z, x, y): self.sel = z[4]; self.etoile(z[4]); return
        for (x0, y0, x1, y1, i) in self.zones:
            if x0 <= x <= x1 and y0 <= y <= y1: self.sel = i; break
        self.drag = [y, self.decal(), False]

    def relache(self, x, y, bouton):
        self.glisse_barre = None; self.drag = None

    def glisser(self, x, y):
        b = self.barre
        if self.glisse_barre is not None:
            if not b: self.glisse_barre = None; return
            libre = b['ptop'] - b['pbot'] - b['th']
            if libre > 0:
                depuis_le_haut = max(0.0, min(1.0, (b['ptop'] - (y + self.glisse_barre)) / libre)) * (b['n'] - b['vis'])      # le curseur de la barre donne la distance depuis le haut du contenu
                self.pos = min(self.plage(), max(0.0, self.plage() - depuis_le_haut))
            return
        d = self.drag
        if d is None: return
        if not d[2] and abs(y - d[0]) < TOLERANCE_GLISSE: return
        d[2] = True
        self.pos = min(self.plage(), max(0.0, d[1] + (d[0] - y)))                    # le contenu suit le pointeur, pixel par pixel (le pointeur descend : la liste descend, on remonte vers les plus anciens)

    # ---- dessin
    def _bm(self):
        r = getattr(self.J, 'ui_rendu', None)
        return r.textes.bitmap if r is not None and getattr(r, 'textes', None) is not None else None

    def _bmm(self):
        """Police des messages du jeu (celle du canevas de texte du moteur : tous les glyphes du jeu, avec ses regles de placement et de coupure) pour le texte des boites ; None si elle n'a pas ete extraite (on garde SE-GARRIR)."""
        r = getattr(self.J, 'ui_rendu', None); t = getattr(r, 'textes', None) if r is not None else None
        return getattr(t, 'messages', None)

    def _larg(self, bm, texte, sc, taille):
        if bm: return bm.largeur(texte) * sc
        return self.P._et(texte, taille).content_width

    def _ligne(self, bm, texte, x, ybase, sc, coul, taille):
        """Une ligne de texte dont la ligne de base est en ybase : police bitmap du jeu (une texture par ligne, teintee), sinon police du systeme."""
        if not texte.strip(): return
        if bm:
            tex, w, h, base = bm.ligne(texte)
            cle = (texte, coul); sp = self._spr.get(cle)
            if sp is None or sp.image is not tex:
                if len(self._spr) > 600: self._spr.clear()
                sp = self._spr[cle] = pyglet.sprite.Sprite(tex); sp.color = coul[:3]
            sp.update(x=x - bm.PAD * sc, y=ybase - (h - base) * sc, scale=sc); sp.draw()
        else:
            et = self.P._et(texte, taille, tuple(coul) + (255,)); et.x = x; et.y = ybase; et.draw()

    def _boite_jeu(self):
        """Boite de dialogue standard (dimensions de la mise en page d'origine si elle est chargee) ; gardee."""
        r = getattr(self.J, 'ui_rendu', None); ml = getattr(r, 'ml', None)
        if self._boite is None or self._boite_ml is not ml: self._boite = Boite.depuis(ml) if ml is not None else Boite(); self._boite_ml = ml
        return self._boite

    def _pages_de(self, bm, e, B, s, taille):
        """Pages d'un element : liste de listes de rangees de texte (3 rangees au plus, l'entete d'un combat comprise). Gardees (cle : element, echelle)."""
        cle = (e.n, e.type, int(s * 100))
        r = self._lignes.get(cle)
        if r is None:
            if len(self._lignes) > 4000: self._lignes.clear()
            if bm: mes = lambda t: bm.largeur(t) * B.texte_ech
            else: mes = lambda t: self.P._et(t, taille).content_width * 0.9 / s
            combat = e.type == HI.TYPE_COMBAT
            r = self._lignes[cle] = paginer(rangees_de(e, mes, B.largeur_texte(), self._bmm()), combat, MAX_LIGNES_COMBAT if combat else B.LIGNES)
        return r

    def _etoile(self, cx, cy, rayon, pleine):
        """Etoile de favori : doree quand l'element est en favori, grise et creuse sinon."""
        if pleine:
            pyglet.shapes.Star(cx, cy, rayon, rayon * 0.45, 5, rotation=0, color=ETOILE + (255,)).draw()
        else:
            pyglet.shapes.Star(cx, cy, rayon, rayon * 0.45, 5, rotation=0, color=GRIS + (255,)).draw()
            pyglet.shapes.Star(cx, cy, rayon * 0.6, rayon * 0.27, 5, rotation=0, color=VIDE_ETOILE + (255,)).draw()

    def _largeur_filtre(self, bm, sc, taille, k):
        """Largeur de la plaque de la case « Favoris seulement » : marge, case, marge, petite etoile, libelle, marge."""
        return 14 * k + 18 * k + 9 * k + 2 * 8 * k + 7 * k + self._larg(bm, LIBELLE_FILTRE, sc, taille) + 14 * k

    def _filtre(self, bm, sc, taille, asc, k, fx, ty, th):
        """Case a cocher « Favoris seulement » : une plaque a la hauteur des onglets, a droite du dernier onglet (le groupe onglets + case est centre dans la fenetre), avec la case, une petite etoile et le libelle ;
        doree quand elle est cochee. Sa zone (clic) est gardee dans `zone_filtre`."""
        P = self.P; cb = 18 * k; rs = 8 * k
        fw = self._largeur_filtre(bm, sc, taille, k)
        zone = (fx, ty, fx + fw, ty + th); self.zone_filtre = zone
        sur = (P._sur(zone) if hasattr(P, '_sur') else False) and P.mode_souris
        self._plaque(fx, ty, fw, th, k, sur)
        on = self.favoris_seuls; coul = OR if on else BLANC
        bx, by = fx + 14 * k, ty + (th - cb) / 2
        pyglet.shapes.Rectangle(bx, by, cb, cb, color=(0, 0, 0)).draw()
        for (xa, ya, xb, yb) in ((bx, by, bx + cb, by), (bx, by + cb, bx + cb, by + cb), (bx, by, bx, by + cb), (bx + cb, by, bx + cb, by + cb)):
            pyglet.shapes.Line(xa, ya, xb, yb, thickness=max(1.5, 1.6 * k), color=coul + (255,)).draw()
        if on:                                                                      # la coche (deux traits)
            pyglet.shapes.Line(bx + cb * 0.2, by + cb * 0.5, bx + cb * 0.42, by + cb * 0.22, thickness=max(2.0, 2.6 * k), color=OR + (255,)).draw()
            pyglet.shapes.Line(bx + cb * 0.42, by + cb * 0.22, bx + cb * 0.84, by + cb * 0.82, thickness=max(2.0, 2.6 * k), color=OR + (255,)).draw()
        ex = bx + cb + 9 * k + rs; ey = ty + th / 2
        pyglet.shapes.Star(ex, ey, rs * 1.15, rs * 0.5, 5, rotation=0, color=(ETOILE if on else GRIS) + (255,)).draw()
        self._ligne(bm, LIBELLE_FILTRE, ex + rs + 7 * k, ty + th / 2 - (asc * 0.37 if bm else 6 * k), sc, coul, taille)

    def _plaque(self, x, y, w, h, k, choisi):
        J = self.J; r = getattr(J, 'ui_rendu', None)
        if r is not None and r.plaque(x, y, w, h, (J.width, J.height), choisi, coin=14 * k): return
        HM.plaque(x, y, w, h, k, choisi, None)

    def _fenetre_boite(self, avec, extra=0):
        """Fenetre de message du jeu (ui_menu.FenetreMessage) qui dessine le cadre d'une boite : avec l'onglet du nom (frameData 191) ou sans (192), sans le canevas ni le curseur de fin de page ; None si la mise en page
        d'origine n'est pas chargee (la boite est alors dessinee avec un cadre simple). `extra` : lignes de texte en plus des 3 de la boite du jeu (un combat) : le cadre (sans onglet) est allonge d'autant (etirer_cadre)."""
        cle = (avec, int(extra) if not avec else 0)
        f = self._fens.get(cle)
        if f is None:
            f = False
            r = getattr(self.J, 'ui_rendu', None); ml = getattr(r, 'ml', None)
            if ml is not None and getattr(ml, 'message', None):
                try:
                    g = UM.FenetreMessage(ml); g.regler(0, 0, False, 'x' if avec else '')
                    if g.avec_nom == avec:
                        g.N['canevas']['act'] = False; g.N['curseur']['act'] = False; f = g
                        if cle[1] > 0: g.N['cadre']['vtx'] = etirer_cadre(g.N['cadre']['vtx'], cle[1] * Boite.PAS)
                except Exception: f = False
            self._fens[cle] = f
        return f or None

    def _boite_dessin(self, B, bx, by, s, k, nom, bm, taille, extra=0):
        """Cadre de la boite dont le coin bas gauche est (bx, by), a l'echelle s : le cadre du jeu (et l'onglet du nom avec son texte, comme le jeu les pose), sinon un cadre simple. Toujours le meme : le message choisi n'est ni
        grise ni eclairci (il porte seulement la petite fleche, voir dessiner)."""
        J = self.J; r = getattr(J, 'ui_rendu', None); f = self._fenetre_boite(bool(nom), extra) if r is not None else None
        fait = False
        if f is not None:
            try:
                if nom: f.N['qui']['text']['text'] = nom
                r.dessiner([f], bx - (B.win[0] + B.x0) * s, by - (B.win[2] + B.z0) * s, s, (J.width, J.height)); fait = True
            except Exception: self._fens[(bool(nom), int(extra) if not nom else 0)] = False
        if not fait:                                                      # (repli : cadre noir translucide du menu et, pour un nom, un petit cadre collé en haut a gauche)
            HM.cadre(bx + 4 * s, by + 4 * s, (B.LARG - 8) * s, (B.HAUT + extra * B.PAS - 8) * s, k, fond=(0, 0, 0), opacite=HM.OPACITE_JEU)
            if nom:
                HM.cadre(bx + 4 * s, by + (B.HAUT + extra * B.PAS - 6) * s, (B.ONGLET_L - 8) * s, (B.ONGLET_H + 2) * s, k, fond=(0, 0, 0), opacite=HM.OPACITE_JEU)
                sc = s * B.texte_ech if bm else 1.0; lw = self._larg(bm, nom, sc, taille)
                self._ligne(bm, nom, bx + (B.NOM_X - 0.0) * s - lw / 2, by + (B.HAUT + extra * B.PAS + 7) * s, sc, BLANC, taille)

    def _mesurer(self, bm, B, s, k, taille, hv):
        """Pose TOUTE la liste dans une colonne (disposer : un dialogue a la hauteur de la boite de dialogue du jeu, que le texte tienne sur 1, 2 ou 3 rangees, et l'onglet du nom, sur la premiere boite d'un
        dialogue avec nom, s'y ajoute au-dessus ; un combat a autant de lignes que son texte en demande, trois au moins : lignes_de_boite), pour l'echelle s et une fenetre de liste de hauteur hv (pixels). La mise en page ne depend jamais de la position de defilement. Met a jour la geometrie du defilement (hauteur du contenu,
        de la fenetre, d'une ligne), garde la position proportionnelle quand l'echelle change, ramene au milieu l'element demande par `aller`, borne la position et garde les bords des elements (debuts, fins) pour la navigation
        au clavier. -> boites : (element, boite, nombre de boites, haut, haut de l'onglet, haut du cadre, rangees de texte) ; haut = pixels depuis le haut du contenu."""
        els = self.elements; n = len(els)
        cle = (id(els), n, int(s * 100), int(k * 100), bm is not None, self._bmm() is not None)
        if self._mise is None or self._mise[0] != cle:
            pages = [self._pages_de(bm, e, B, s, taille) for e in els]
            ent = [(len(pg), e.type == HI.TYPE_DIALOGUE and bool(e.nom), [B.haut_pour(lignes_de_boite(page, j == 0, e.type == HI.TYPE_COMBAT)) * s for j, page in enumerate(pg)]) for pg, e in zip(pages, els)]
            boites, debuts, fins, hc = disposer(ent, B.HAUT * s, B.ONGLET_H * s, ECART_ELEMENTS * k, ECART_PAGES * k, MARGE_LISTE * k)
            self._mise = (cle, [(i, p, nb, h, hn, hb, pages[i][p]) for (i, p, nb, h, hn, hb) in boites], debuts, fins, hc)
        boites, debuts, fins, hc = self._mise[1:]
        self._geometrie(debuts, fins, hc, hv, B.PAS * s, s)
        return boites

    def _geometrie(self, debuts, fins, hc, hv, pas, s):
        """Partie pure de _mesurer (testee sans police ni GL) : la liste fait `hc` pixels de haut (debuts / fins : haut de la premiere boite et bas de la derniere de chaque element), la fenetre de la liste `hv`, une ligne de texte `pas`,
        a l'echelle s. Garde la position proportionnelle quand l'echelle change, ramene au milieu l'element demande par `aller`, borne la position et garde les bords des elements pour la navigation au clavier."""
        n = len(debuts)
        if self._s_prec and abs(s - self._s_prec) > 1e-6: self.pos *= s / self._s_prec                 # fenetre redimensionnee : la vue reste au meme endroit de la liste
        self._s_prec = s; self.hc, self.hv, self.pas = hc, float(hv), pas
        if self.centrer is not None:
            i, self.centrer = self.centrer, None
            if 0 <= i < n: self.pos = min(self.plage(), max(0.0, hc - (debuts[i] + fins[i]) / 2.0 - self.hv / 2.0)); self.sel = i
        self.debuts, self.fins = list(debuts), list(fins)
        self.pos = min(self.plage(), max(0.0, self.pos))
        self.sel = max(0, min(n - 1, self.sel)) if n else 0

    def _decouper(self, x, y, w, h):
        """Cadre de decoupe (glScissor) sur le rectangle (x, y, w, h) de la fenetre (pixels de la fenetre : mis a l'echelle du tampon d'image sur un ecran a forte densite) : ce qui deborde de la liste est coupe, comme un texte qui defile.
        -> True si le cadre est actif (a fermer par glDisable(GL_SCISSOR_TEST)) ; False si on n'a pas pu l'installer (les boites coupees ne sont alors pas dessinees)."""
        try:
            W, H = self.J.width, self.J.height; fb = self.J.get_framebuffer_size() if hasattr(self.J, 'get_framebuffer_size') else (W, H)
            rx, ry = fb[0] / float(max(1, W)), fb[1] / float(max(1, H))
            gl.glEnable(gl.GL_SCISSOR_TEST); gl.glScissor(int(max(0, x * rx)), int(max(0, y * ry)), int(max(1, round(w * rx))), int(max(1, round(h * ry))))
            return True
        except Exception:
            return False

    def dessiner(self):
        J = self.J; P = self.P; W, H = J.width, J.height; k = max(0.75, H / 900.0)
        gl.glDisable(gl.GL_DEPTH_TEST); gl.glEnable(gl.GL_BLEND); gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)
        voile = pyglet.shapes.Rectangle(0, 0, W, H, color=(0, 0, 0)); voile.opacity = 90; voile.draw()
        bm = self._bm(); B = self._boite_jeu(); s = B.echelle(H, W, k)                      # s : pixels par unite d'interface = ceux d'une boite de dialogue du jeu
        su = max(0.8, min(2.4, H / 700.0)) if bm else 1.0; taille = 17 * k                  # su : un pixel de police du jeu = su pixels d'ecran (titre, onglets, aide) ; taille : police du systeme (repli)
        sc = s * B.texte_ech if bm else 1.0; taille_b = 20 * s                               # idem pour le texte des boites : comme dans le jeu (1,105 unite par pixel de police)
        fm = self._bmm()                                                                       # texte des boites : la police des messages du jeu quand elle est la (un pixel de son canevas = une unite d'interface), sinon SE-GARRIR
        if fm is not None: sc = s * fm.ECH; base_texte = B.base_msg
        else: fm = bm; base_texte = B.base
        asc = (bm.ascent * su) if bm else 18 * k
        kb = 1.1 * k; bw, bh = 64 * kb, 55.5 * kb
        lgs = [self._larg(bm, nom, su, taille) + 44 * k for nom, _ in ONGLETS]; tw = max(lgs + [120 * k]); gap = 10 * k
        larg_onglets = tw * len(ONGLETS) + gap * (len(ONGLETS) - 1); fw = self._largeur_filtre(bm, su, taille, k)
        larg_ligne = larg_onglets + 14 * k + fw                                                       # la ligne des onglets : les onglets puis la case « Favoris seulement »
        pw = min(W - 20 * k, max(B.LARG * s + B.MARGES * k, larg_ligne + 2 * 34 * k)); h = H - 2 * 30 * k - bh - 10 * k
        x0 = (W - pw) / 2; y1 = (H + h + bh + 10 * k) / 2; y0 = y1 - h
        HM.cadre(x0, y0, pw, h, k, fond=(0, 0, 0), opacite=HM.OPACITE_JEU)                # aussi transparent que les autres fenetres du jeu
        titre = 'Historique'
        wt = self._larg(bm, titre, su * 1.25, taille * 1.3)
        self._ligne(bm, titre, x0 + (pw - wt) / 2, y1 - 24 * k - asc * 1.25, su * 1.25, BLANC, taille * 1.3)
        # onglets (plaques du jeu : l'onglet ouvert est la plaque « choisie »)
        th = 34 * k; ty = y1 - 100 * k; self.zones_onglet = []                      # (sous le titre : ses plaques ne doivent pas le recouvrir)
        tx = x0 + (pw - larg_ligne) / 2
        for i, (nom, cle) in enumerate(ONGLETS):
            zx = tx + i * (tw + gap); zone = (zx, ty, zx + tw, ty + th); self.zones_onglet.append(zone + (i,))
            sur = (P._sur(zone) if hasattr(P, '_sur') else False) and P.mode_souris
            self._plaque(zx, ty, tw, th, k, i == self.onglet or sur)
            lf = self._larg(bm, nom, su, taille); self._ligne(bm, nom, zx + (tw - lf) / 2, ty + th / 2 - (asc * 0.37 if bm else 6 * k), su, OR if i == self.onglet else BLANC, taille)
        self._filtre(bm, su, taille, asc, k, tx + larg_onglets + 14 * k, ty, th)                  # case « Favoris seulement » (a droite des onglets)
        # aide (une ou deux lignes, selon la largeur de la fenetre)
        ks = (J.reg['touches'].get('historique') or [None])[0] if hasattr(J.reg, '__getitem__') else None
        kn = RG.nom_touche(ks) if ks else None
        aide = ['Haut / Bas : message précédent / suivant', 'Molette : défiler', 'Gauche / Droite : onglet', 'Entrée : favori ★', 'F : favoris seulement'] + (['%s : suite' % kn] if kn else []) + ['Échap : fermer']
        la_max = pw - 24 * k; mes_aide = lambda t: self._larg(bm, t, su * 0.72, taille * 0.72)
        lignes_aide = []; cur = ''
        for a in aide:
            cand = a if not cur else cur + '     ' + a
            if cur and mes_aide(cand) > la_max: lignes_aide.append(cur); cur = a
            else: cur = cand
        lignes_aide.append(cur)
        pas_aide = (bm.interligne * su * 0.72) if bm else 17 * k
        # zone de la liste : la boite (taille du jeu) a gauche, la colonne de l'etoile a sa droite, la barre de defilement au bord
        groupe = B.LARG * s + 44 * k; lx0 = x0 + (pw - groupe) / 2; lx1 = lx0 + groupe; ly1 = ty - 14 * k; ly0 = y0 + 40 * k + (len(lignes_aide) - 1) * pas_aide
        self.zones = []; self.zones_etoile = []; self.barre = None
        n = len(self.elements)
        if not n:
            self.hc = self.hv = 0.0; self.pos = 0.0; self._mise = None
            msg = (VIDES_FAVORIS if self.favoris_seuls else VIDES)[ONGLETS[self.onglet][1]]
            vl = couper_mots(msg, lambda t: self._larg(bm, t, su, taille), pw - 40 * k)                 # le message tient dans la fenetre : coupe en plusieurs lignes, centrees (il debordait du cadre quand il etait long)
            pas_v = (bm.interligne * su) if bm else 28 * k; y_v = (ly0 + ly1) / 2 + (len(vl) - 1) * pas_v / 2
            for j, l in enumerate(vl): self._ligne(bm, l, x0 + (pw - self._larg(bm, l, su, taille)) / 2, y_v - j * pas_v, su, GRIS, taille)
        else:
            mouse = P.mode_souris; hv = ly1 - ly0
            boites = self._mesurer(bm, B, s, k, taille_b, hv)
            haut_ecran = ly0 + self.hc - round(self.decal())                      # ordonnee du haut du contenu (position entiere : le texte garde le meme dessin a chaque position) ; le contenu est colle en bas quand il est plus court que la fenetre
            decoupe = self._decouper(x0, ly0, pw, hv)                              # tout ce qui deborde de la liste est coupe
            glisse = self.drag is not None and self.drag[2]
            try:
                vues = []; haut_de = {}
                for b in boites:                                                    # seules les boites qui touchent la fenetre de la liste sont dessinees (de la plus ancienne, en haut, a la plus recente)
                    (i, p, np_, haut, hn, hb, rangees) = b; yb = haut_ecran - haut - hn - hb; yt = yb + hb + hn
                    if yt <= ly0 or yb >= ly1 or (not decoupe and (yb < ly0 or yt > ly1)): continue
                    vues.append((b, yb, yt)); haut_de[i] = min(haut_de.get(i, p), p)       # (page la plus haute montree de chaque element : la fleche dorée n'y est dessinee qu'une fois)
                    if mouse and self.glisse_barre is None and not glisse and P._pointeur_dans((lx0, max(yb, ly0), lx1, min(yt, ly1))): self.sel = i      # a la souris, le message survole est le message choisi (choisi avant le dessin : une seule fleche)
                for ((i, p, np_, haut, hn, hb, rangees), yb, yt) in vues:
                    e = self.elements[i]; nom = e.nom if (e.type == HI.TYPE_DIALOGUE and p == 0 and e.nom) else None
                    zone = (lx0, max(yb, ly0), lx1, min(yt, ly1)); self.zones.append(zone + (i,))                      # (la zone d'une boite coupee ne depasse pas la fenetre de la liste : pas de clic sur les onglets ou l'aide)
                    extra = max(0, lignes_de_boite(rangees, p == 0, e.type == HI.TYPE_COMBAT) - B.LIGNES)                # lignes en plus de la boite du jeu (un combat)
                    self._boite_dessin(B, lx0, yb, s, k, nom, bm, taille_b, extra)                      # cadre du jeu (+ onglet et nom) : aucun grisé au survol ni au choix
                    if i == self.sel and p == haut_de[i]: P._curseur(x0 + 4 * k, yb + hb / 2, min(hb * 0.7, 28 * k))      # le message choisi (clavier ou souris) : la petite fleche, et rien d'autre
                    rang = 0
                    if e.type == HI.TYPE_COMBAT and p == 0:                                # entete : l'issue du combat a gauche, l'heure de jeu a droite
                        base = yb + hb - base_texte(0) * s; self._ligne(fm, HI.LIBELLE_ISSUE.get(e.issue, ''), lx0 + B.TEXTE_X * s, base, sc, OR, taille_b)
                        ht = heure_jeu(e.t); self._ligne(fm, ht, lx0 + (B.LARG - 14) * s - self._larg(fm, ht, sc * 0.8, taille_b * 0.8), base, sc * 0.8, AIDE, taille_b * 0.8); rang = 1
                    for l in rangees:
                        self._ligne(fm, l, lx0 + B.TEXTE_X * s, yb + hb - base_texte(rang) * s, sc, BLANC, taille_b); rang += 1
                    rs = 11 * k; ex = lx0 + B.LARG * s + 22 * k; ey = yb + hb - (B.BASE_1 - 7) * s     # etoile dans la colonne a droite de la boite, a la hauteur de la 1re ligne
                    z = (ex - rs * 1.3, max(ey - rs * 1.3, ly0), ex + rs * 1.3, min(ey + rs * 1.3, ly1))
                    if z[1] < z[3]: self.zones_etoile.append(z + (i,))
                    self._etoile(ex, ey, rs * (1.15 if (mouse and P._pointeur_dans(z)) else 1.0), e.fav is not None)
                    if np_ > 1:                                                          # « 1/2 » sous l'etoile : la boite fait partie d'une suite (simple etiquette)
                        t = '%d/%d' % (p + 1, np_); self._ligne(bm, t, ex - self._larg(bm, t, su * 0.72, taille * 0.72) / 2, ey - rs * 1.3 - 6 * k - (asc * 0.72 if bm else 12 * k), su * 0.72, AIDE, taille * 0.72)
            finally:
                if decoupe: gl.glDisable(gl.GL_SCISSOR_TEST)
            if self.hc > self.hv + 0.5: self.barre = P._barre_defilement(x0 + pw - 14 * k, ly1, ly0, self.hc, self.hv, self.plage() - self.decal(), k, self.glisse_barre is not None)      # curseur proportionnel, position continue (distance depuis le haut du contenu)
        for j, l in enumerate(lignes_aide):                                          # aide et bouton retour
            la = self._larg(bm, l, su * 0.72, taille * 0.72); self._ligne(bm, l, x0 + (pw - la) / 2, y0 + 14 * k + (len(lignes_aide) - 1 - j) * pas_aide, su * 0.72, AIDE, taille * 0.72)
        bx = x0 + pw - bw - 8 * k; by = y0 - 8 * k - bh; self.zone_ret = (bx, by, bx + bw, by + bh)
        P._bouton_retour(bx, by, bw, bh, P._sur(self.zone_ret))
