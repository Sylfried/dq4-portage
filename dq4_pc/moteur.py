"""Le moteur du jeu (libdq4core.so, ARM64) execute dans un emulateur + decodage de ce qu'il demande a Unity."""
import os, re, struct, zipfile, unicorn
import numpy as np
import emu_core as T
import priorite_jeu as PJ
import pose_couchee as PC
import rencontres as RE
from pktlog import PacketLog
from historique import Capteur
from historique_combat import CapteurCombat

CUR_I, CUR_F = 0x258278, 0x258280          # curseurs d'ecriture (entiers / flottants) dans la bibliotheque
PARTIE_DEPART = 0x3                         # menu de depart (GameStartPart : liste des journaux, creation, suppression, licence)
PARTIE_VILLE = 0xc                         # ville, donjon, tour (decor 3D)
PARTIE_COMBAT = 0xd
PARTIE_CHAMP = 0xe                         # FieldPart : carte du monde
PARTIE_CASINO = 0xf                        # Global::startCasino : machine a sous (carte ev05) et poker (carte ev04), fenetres des types 44-48
PARTIE_BESTIAIRE = 0x10                    # Global::startBook : livre des monstres (fenetre de type 28) ; garde la carte de la ville
CARTE_TITRE = 'ev01'                       # carte de l'ecran-titre (ciel, logo, ile, dragon : scene sans heros)
PARTIES_MINIJEU = (PARTIE_CASINO, PARTIE_BESTIAIRE)        # parties « plein ecran » du moteur qui dessinent leurs elements par maillages dynamiques (paquets 21 / 22) avec leur propre camera
MSGDBG = bool(os.environ.get('DQ_MSGDBG'))     # (test) journal des etats du message du moteur
FBXLOG = bool(os.environ.get('DQ_FBXLOG'))     # (test) journal des paquets 32 (dragon du titre : position, rotation, couleur, sequence)
GLOBAL_PTR = 0x23d438                       # singleton Global
NOM_RESSOURCE = 0x258290                    # nom de la ressource carte demandee a Unity (ex. m/ma/in/mak1f1)
ECRAN_ETAT = 0xd8                           # Global+0xd8 : copie, a chaque GameUpdate, du premier entier du tampon de sortie (mot d'etat partage avec Unity) ; son bit 1 = « effet d'ecran en cours » (Global::IsScreenEffectEnd attend qu'il retombe)
G_IS_AMAZON = 0x24f684                      # octet g_isAmazon du moteur : a 1, la case « Sauv. cloud » du menu de depart n'existe pas
MSG_RETOUR_TITRE = 0xcba2f                     # identifiant du message de la boite « Revenir a l'ecran titre » des Parametres d'origine (TownMenu_OPERATION_SETTING::menuUpdate + 0x1c8 : `mov w1, #0xba2f ; movk w1, #0xc, lsl #16` puis TownMenu_MESSAGE::addMessage(int)) : b0834000.mpt, 834095
MESSAGE_RESULTAT = 0x10                        # TownMenu_MESSAGE + 0x10 : reponse de la boite (1 = Oui, 2 = Non ; remis a 0 a l'ouverture) ; lue par TownMenu_OPERATION_SETTING::menuUpdate (etat 5)
EFFET_COMBAT = 4                            # paquet 34 (cmd_screen_effect) : valeur & 0xf = 4, Capture.BattleEffect (les morceaux de l'ecran tombent)
EFFET_COMBAT_IMAGES = 57                    # Capture.BattleEffect : le compteur va de 0 a divY (56) inclus, une image du jeu chacun
CHARGEMENT_COUVERT = 0.9                    # opacite (0 a 1) d'un plan de fondu a partir de laquelle l'ecran est « couvert » : un chargement de carte qui arrive alors n'est montre qu'une fois la scene en place (Etat.chargement)
CHARGEMENT_MIN, CHARGEMENT_PLACEMENT, CHARGEMENT_MAX = 1, 2, 6      # images du moteur apres le paquet 0 : au moins 1 (le moteur place la camera et les personnages a l'image suivante, sur 529 cartes), 2 au plus pour attendre les positions des personnages visibles, 6 : garde-fou (jamais d'attente plus longue)
ATTENTE_CHARGE_MAX = 240                    # images (30 Hz) d'ecran noir avant de renoncer a attendre le chargement de la scene de combat
FENETRE_ENTREE_COMBAT = 12                  # images apres le chargement de la scene d'un combat (paquet 0, bit 8) pendant lesquelles un fondu lance par le moteur est le fondu d'arrivee du combat (Etat.transition_combat)
FENETRE_RETOUR_COMBAT = 12                  # images apres la sortie de la partie combat pendant lesquelles un fondu lance par le moteur est le fondu de retour a la carte
GARDE_TRANSITION = 8                        # images ou la transition de combat reste « en cours » apres la fin de l'un de ses fondus (le moteur change de scene 1 a 3 images plus tard, puis lance le fondu suivant)
LIB_APK = 'lib/arm64-v8a/libdq4core.so'
DECOMPTE_SORTIE = 0x258254                  # octet de la bibliotheque lu par Global::NativeExec : decompte (en images) du bruitage de sortie ; startTown, startField, ChangeGamePart, startFirstTown et startDebugTown l'arment a 15 quand le jeu quitte une ville ou la carte du monde,
                                            # NativeExec le decremente a chaque image et, a 0, appelle TownSystem::playTownExitSE / FieldSystem::playFieldExitSE (bruitage 305 : seulement si l'ancienne scene vit encore, son octet 0 = 1) ; voir Moteur._decompte_sortie

# touches (masque envoye a GameUpdate) : haut, bas, gauche, droite verifies ; A/B a confirmer
HAUT, BAS, GAUCHE, DROITE, A, B = 0x1, 0x2, 0x4, 0x8, 0x10, 0x20
OBJ_MESSAGE = 0x252330                     # objet SDrawCTRL (canevas de texte des messages) dans la bibliotheque
CANEVAS_L, CANEVAS_H = 512, 512            # texture du canevas de message d'Unity (MenuMessage : Texture2D(512, 512)) ; le moteur y ecrit en boucle
PILE_SHORTS = 4096                         # taille reelle allouee pour la file des messages (Unity en annonce 1089)
MSG_ACTIF, MSG_ETAT, MSG_COURANT, MSG_FIN, MSG_VITESSE = 0x25238e, 0x25238c, 0x2523cc, 0x2523ce, 0x2523b0      # ui_MsgLoop : message ouvert (octet), etat (1 lecture d'un code, 2 ecriture des lettres, 3 / 5 attente d'une touche), indice de la lettre courante et de la fin de ligne, lettres par image / 4 du type de fenetre
UI_MSGLOOP_ECRITURE = 0x128                # ui_MsgLoop + 0x128 : `sxth w20, w8` apres `lsl w8, w8, #2` (etat 2 : nombre de lettres ecrites a cette image)
SXTH_W20_W8 = 0x13003d14
COMBAT_MANUEL = 4                          # OptionStatus.battleSpeed : 0 a 3 = attente de 12 / 22 / 32 / 42 images entre deux messages de combat (BattleAutoFeed::setMessageSpeed), 4 = pas d'avance automatique
DRAPEAU_FONDU, DRAPEAU_JOUEUR_VERROUILLE = 0x1, 0x4        # Global.Flag (mot d'etat partage, Moteur.drapeaux) : un fondu est en cours ; le jeu a verrouille le joueur (evenement, scene : Global.PLAYER_LOCK)
HAVESTATUS_LEVELUP_FIN = 0x3f8             # status::HaveStatus::levelup(bool) + 0x3f8 : `tbz w20, #0, ...` (w20 = l'argument ; vrai : le personnage retrouve tous ses PV et PM, ses PV max/PM max venant d'etre recalcules)
TBZ_W20_0 = 0x36000094
COUNTDOWN_EXEC_ECRITURE = 0xc               # CountDown::exec + 0xc : `str w8, [x0]` (w9 = compteur de rencontres avant, w8 = compteur apres avoir perdu 2 x [x0 + 0x10])
STR_W8_X0 = 0xb9000008
MAGIE_CHARSELECT_BL, MAGIE_SANS_CIBLE_BL, MAGIE_EXECUSE_STUB = 0x428, 0x188, 0x2269c0      # TownMenu_MAGIC_CHARSELECT::menuUpdate + 0x428 et TownMenu_MAGIC_ROOT::useMagicNoTarget + 0x188 : `bl UseAction::execUse` (via le stub PLT 0x2269c0) du menu Magie du terrain
MAGIE_PM, MAGIE_RESULTAT, MAGIE_ACTION = 0x7e, 0x210, 0x1d8        # PlayerStatus + 0x7e : PM courants ; UseActionParam + 0x210 : liste des messages de resultat (se termine par 0), + 0x1d8 : numero de l'action
MAGIE_NB_CIBLES, MAGIE_FIN_BOUCLE = 0x257f84, 0x2e0       # gTownMenuItemUseManager + 0xaa : nombre de cibles dont le moteur affiche le resultat (et dont il joue le bruitage de soin, une fois chacune) ; useMagicNoTarget + 0x2e0 : sortie de cette boucle
MSG_RIEN_NE_SE_PASSE = 0xc3d6b             # identifiant du message du moteur « Mais rien ne se passe. » (champ d'echec de la table des actions : Resurrection, Antipoison, Sifflet...) ; sert de repere de version du moteur (action 201) : il n'est plus affiche par la regle des sorts sans effet
MSG_IL_NE_SE_PASSE_RIEN = 0xc3d6d          # identifiant du message du moteur « Mais il ne se passe rien. » (celui qu'Evac' hors donjon met dans param + MAGIE_RESULTAT ; mesure : le champ 5 de la table des actions donne 0xaae7e pour l'action 204, mais ce n'est pas le message affiche) : texte officiel affiche par la regle « sort qui coute des PM sans effet » (demande de Sylfried, #48)
DUREE_ANIM = 18                            # images (30 Hz) avant de dire au moteur qu'une animation d'objet (porte...) est finie
ORIGINE_APRES = 3                            # images apres sa creation au bout desquelles un personnage anime sans position est place a l'origine (voir Etat.appliquer, paquet 13)


class Silencieux:
    def __init__(self): self.lignes = []
    def __call__(self, *a):
        self.lignes.append(' '.join(str(x) for x in a)); del self.lignes[:-200]


class CoreJeu(T.Core):
    """Core + sauvegardes : lecture dans un dossier reel, ecriture persistante (jamais dans les originaux)."""
    dossier_lecture = None
    dossier_ecriture = None

    def h_fopen(self, path, mode, *a):
        p = self.read_cstr(path).decode('latin-1'); m = self.read_cstr(mode).decode()
        mm = re.search(r'(data\d+\.dat)$', p)
        if mm and os.environ.get('DQ_SAVEDBG'): print('fopen %s mode %s' % (p, m), flush=True)           # (test) quand le moteur ouvre un fichier de sauvegarde
        if mm:
            nom = mm.group(1)
            if 'w' in m or 'a' in m:
                r = super().h_fopen(path, mode, *a)
                if r: self.files[r]['persist'] = os.path.join(self.dossier_ecriture, nom)
                return r
            for d in (self.dossier_ecriture, self.dossier_lecture):
                if d and os.path.exists(os.path.join(d, nom)):
                    self.real_files[p] = os.path.join(d, nom); break
        return super().h_fopen(path, mode, *a)

    def h_fclose(self, h, *a):
        f = self.files.get(h)
        if f and f.get('persist'):
            os.makedirs(os.path.dirname(f['persist']), exist_ok=True)
            with open(f['persist'], 'wb') as fh: fh.write(bytes(f['d']))
        return super().h_fclose(h, *a)


class Etat:
    """Ce que Unity saurait a l'ecran : decode des paquets du moteur."""
    vitesse_fondu = 1.0                        # reglage du joueur : les fondus au noir durent 1 / vitesse_fondu de leur duree d'origine
    def __init__(self):
        self.carte = None; self.cam_pos = None; self.cam_cible = None; self.cam_rot = None
        self.symboles = {}                            # carte du monde : icones (paquet 29) idx -> {genre, x, y (coin haut-gauche en px), alpha, visible}
        self.modeles = {}; self.maillages = {}       # combat : emplacement -> id de modele (texture m<id>) ; emplacement -> maillage dynamique (paquet 22)
        self.mesh_etat = {}                           # combat : emplacement -> {'shader', 'vis', 'col', 'off'} (paquets 21, 23, 24, 25, 26 : MeshChara cote Unity)
        self.cam_near = None; self.cam_far = None; self.cam_yoff = None; self.cam_libre = False; self.cam_bas = None      # paquet 11 : near, far, yOffset (None = valeurs de Global.CameraInitParams), camera libre (sans cible), lookDownAdjust (None = 0,2 du .cctor de SceneCamera)
        self.cam_fov = None                           # paquet 11 (camera_sub) : champ de vision nominal en degres (Unity le multiplie par 4/3, SceneCamera.Update) ; None = valeur du combat (48)
        self.icones = {}                              # paquets 19/20 (Riseup) : emplacement (0..15) -> {'id' (case 32 x 32 de la feuille MenuTexture), 'pos', 'alpha'} : bulle « ! » au-dessus d'un personnage
        self.sprites = {}; self.cartes_chargees = 0; self.objets_cmd = []; self.fond = (0.0, 0.0, 0.0); self.fond_haut = None; self.fond_bas = None       # fond : moyenne des deux teintes du paquet 8 ; fond_haut / fond_bas : teintes du haut et du bas de l'ecran (BackColor, degrade ; None = pas de paquet 8) ; objets_cmd : ordres sur les objets de la carte (paquets 2 a 5 et 7), vides par la fenetre : (genre, objet, valeurs...)
        self.partie = 0; self.champ = None        # partie du jeu (0xc ville, 0xe carte du monde) ; carte du monde : tuiles a afficher
        self.maillages_vus = set()                # combat : emplacements dont le maillage (paquet 22) est arrive a CETTE image : Unity dessine en mode immediat, pas de paquet = rien a l'ecran (clignotement d'un coup recu, monstre vaincu)
        self.fondu = self._plan_fondu(); self.fondu_fond = self._plan_fondu()      # Fade.FadePlane : opacite courante, opacite visee, pas par image, images restantes, couleur, images passees tout noir. DEUX plans (Fade.l_fade, bit 14 de l'entier du paquet 9 = Fade.l_targetLayer) : 0 = « FadeForMenu » (shader Custom/FrontFade, file Overlay : devant tout, fenetres et messages compris) ; 1 = « FadeForBG » (Custom/BackFade, file Background : devant la scene, derriere les fenetres)
        self.sons = []; self.musique = None       # paquets 35/36/37 : ordres de son en attente (type, valeur), vides par la fenetre a chaque image ; musique demandee en dernier (None = arret)
        self.effet = None                         # effet d'ecran de debut de combat en cours : {'n': images ecoulees} (le moteur attend sa fin, voir Moteur._effet_combat)
        self.chargement = None                    # chargement de carte (paquet 0) alors que l'ecran est couvert par un fondu : {'n': images du moteur depuis le paquet 0, 'cam': paquet 10 recu depuis} tant que la scene n'est pas en place ; la fenetre ne dessine alors que le fondu (voir maj_chargement)
        self.rapport_fondu = (-99, 1.0)             # dernier fondu au noir lance par le moteur : (image du moteur, duree jouee / duree d'origine) ; 1.0 = duree du jeu (voir Moteur._decompte_sortie)
        self.fen_entree = 0; self.fen_retour = 0; self.garde_trans = 0      # transition de combat (voir transition_combat) : images restantes de la fenetre « arrivee en combat », de la fenetre « retour a la carte », de la garde entre deux fondus
        self.attente_charge = None                # {'base': nombre de chargements de scene deja vus, 'n': images attendues} : ecran noir tant que la scene du combat n'est pas arrivee
        self.monde = None                         # carte du monde entiere lue dans le moteur : {'ids': tuiles (H x L) apres animation, 'l', 'h'} ; None hors de la carte du monde
        self.teinte = (1.0, 1.0, 1.0)             # paquet 33 (cmd_map_color_rate) : teinte du decor (FldObject.m_color, ou Field.SetColor sur la carte du monde) : multiplie la couleur de chaque materiau du decor (sauf les textures « tz_ » : lampes, bougies, vagues) ; 1, 1, 1 = neutre
        self.dort_haut = 0.0                          # paquet 17 (Chara.SetSleepNear) : hauteur du corps des personnages couches (composante Y de s_lieOffset, statique de Chara : elle survit aux changements de carte) ; 0 tant que le moteur n'a rien envoye
        self.fbx = {}; self.image = 0             # modeles 3D animes (paquets 31 / 32 : le dragon du titre) : emplacement -> {'id', 'vis', 'pos', 'rot', 'scl', 'col', 'anim': [(image du moteur, numero de sequence, force)]} ; image : numero du pas du moteur en cours (rempli par Moteur.step)

    @staticmethod
    def _plan_fondu(): return {'a': 0.0, 'fin': 0.0, 'pas': 0.0, 'n': 0, 'col': (0.0, 0.0, 0.0), 'noir': 0, 'combat': False}      # 'combat' : fondu de la transition d'un combat (duree du jeu, voir transition_combat)

    def __setstate__(self, d):                  # etats enregistres avant les deux plans de fondu
        self.__dict__.update(d); self.__dict__.setdefault('fondu_fond', self._plan_fondu()); self.__dict__.setdefault('fbx', {}); self.__dict__.setdefault('image', 0); self.__dict__.setdefault('teinte', (1.0, 1.0, 1.0)); self.__dict__.setdefault('chargement', None); self.__dict__.setdefault('dort_haut', 0.0); self.__dict__.setdefault('fond_haut', None); self.__dict__.setdefault('fond_bas', None)
        self.__dict__.setdefault('fen_entree', 0); self.__dict__.setdefault('fen_retour', 0); self.__dict__.setdefault('garde_trans', 0); self.__dict__.setdefault('rapport_fondu', (-99, 1.0))

    def fondu_en_cours(self): return self.fondu['n'] >= 1 or self.fondu_fond['n'] >= 1      # Fade.FadePlane.CheckFade : images restantes > 0 sur l'un des deux plans

    def transition_combat(self):
        """Le jeu est-il dans la transition d'un combat : effet d'ecran de debut (la « cascade »), ecran noir qui attend la scene, fondus d'arrivee et de sortie du combat, fondu de retour a la carte (et les 1 a 3 images
        entre deux de ces fondus) ? Depuis #47 sa duree en images suit « Vitesse de transition » (Etat._fondu, Moteur._debut_effet_combat) comme tout fondu ; son horloge reste celle du jeu pour la cascade et, au retour a la
        carte, tant que le joueur est verrouille ou entre deux fondus (Jeu._facteur_vitesse : des qu'il est libre, la marche acceleree et l'accelerateur agissent, #127), alors que « Vitesse de combat » agit des la fin de la cascade (ecran noir, fondu d'arrivee, messages) jusqu'au fondu de fin compris."""
        return (self.effet is not None or self.attente_charge is not None or self.garde_trans > 0
                or (self.fondu['n'] >= 1 and bool(self.fondu.get('combat'))) or (self.fondu_fond['n'] >= 1 and bool(self.fondu_fond.get('combat'))))

    def tick_transition(self):
        """Une image du jeu (apres tick_fondu) : les fenetres et la garde de la transition de combat s'ecoulent."""
        if self.fen_entree > 0: self.fen_entree -= 1
        if self.fen_retour > 0: self.fen_retour -= 1
        if self.garde_trans > 0: self.garde_trans -= 1

    def appliquer(self, paquets, lire_nom):
        self.maillages_vus = set()
        couvert = max(self.fondu['a'], self.fondu_fond['a']) >= CHARGEMENT_COUVERT; charge = False; cam_vue = False      # ecran deja couvert par un fondu au moment du chargement de carte ?
        for t, a, f in paquets:
            if t == 0:
                charge = True; cam_vue = False
                if a and a[0] & 0x100: self.fen_entree = FENETRE_ENTREE_COMBAT          # scene de combat (cmd_fld_load, bit 8) : le fondu lance dans la foulee est le fondu d'arrivee du combat
                self.carte = lire_nom(); self.cartes_chargees += 1; self.sprites.clear(); self.fond = (0.0, 0.0, 0.0); self.fond_haut = self.fond_bas = None; self.modeles.clear(); self.maillages.clear(); self.mesh_etat.clear(); self.objets_cmd = [('carte',)]; self.cam_rot = None; self.cam_fov = None; self.cam_near = None; self.cam_far = None; self.cam_yoff = None; self.cam_libre = False; self.symboles.clear(); self.icones.clear(); self.fbx.clear(); self.teinte = (1.0, 1.0, 1.0)      # nouvelle carte : FldObject neuf, m_color blanche (FldObject.init_fld) ; le moteur renvoie la teinte de la carte apres le paquet 0
            elif t == 8 and len(f) >= 6:
                self.fond = tuple((f[i] + f[i + 3]) / 2 for i in range(3))     # couleur d'effacement : moyenne des deux teintes (repli, rendu hors ecran) ; le fond lui-meme est un degrade vertical (#111)
                self.fond_haut = tuple(float(f[i]) for i in range(3)); self.fond_bas = tuple(float(f[i + 3]) for i in range(3))      # cmd_back_color (RVA 0xD14F44) : 6 flottants -> BackColor.SetColor(haut, bas, 0) (0xCC43F8) : haut = sommets 0 et 1 du quadrilatere plein ecran, bas = sommets 2 et 3
            elif t == 33 and len(f) >= 3:           # cmd_map_color_rate (D14E44) : r, g, b ; FldObject.m_color = (r, g, b, 1) (decor des villes et des combats : FldObject.update_material_color, a chaque image, Material.color = _OrgColor (1, 1, 1, alpha) x m_color, sauf les materiaux dont la texture a « tz_ » dans son nom) ; sur la carte du monde : Field.SetColor (tuiles et symboles)
                self.teinte = (float(f[0]), float(f[1]), float(f[2]))
            elif t == 27:                           # cmd_field_load : Field.Init, materiau neuf (couleur blanche) ; le moteur renvoie la teinte de la carte du monde ensuite
                self.teinte = (1.0, 1.0, 1.0)
            elif t == 28 and len(a) >= 4:           # FieldData::drawBlock : fenetre de tuiles 16x16 de la carte du monde (cols x lignes) autour de la camera
                self.champ = {'x0': a[0], 'y0': a[1], 'cols': a[2], 'tuiles': a[4:4 + a[3]], 'cam': (f[0], f[1]) if len(f) >= 2 else None}
            elif t == 29 and a:                     # FieldData::draw_symbol : idx | genre << 8 + [x, y, alpha] ; 0x8000 | idx = cacher ; 0xc000 | idx = remontrer
                v = a[0]; i = v & 0xff
                if v & 0xc000 == 0xc000:
                    if i in self.symboles: self.symboles[i]['vis'] = True
                elif v & 0x8000:
                    if i in self.symboles: self.symboles[i]['vis'] = False
                elif len(f) >= 3: self.symboles[i] = {'genre': (v >> 8) & 0x7f, 'x': f[0], 'y': f[1], 'alpha': f[2], 'vis': True}
            elif t == 12 and len(a) >= 2:
                if a[1] >= 0: self.sprites[a[0]] = {'id': a[1], 'pos': None, 'col': (1, 1, 1, 1), 'pose': 0, 'dir': 0, 'vis': True, 'ech': 1.0, 'cree': self.image}
                else: self.sprites.pop(a[0], None)
            elif t == 14 and len(a) >= 2:           # cmd_chara_on_off : Chara.SetVisible(valeur != 0) = Renderer.enabled du personnage (et de son ombre)
                if a[0] in self.sprites: self.sprites[a[0]]['vis'] = a[1] != 0
            elif t == 16 and a:                     # cmd_chara_sleep_pose (D132FC) : personnage = v & 0xff ; bits 8-9 : Chara.SetSleepPose(bit 8) ; bit 10 : Chara.SetSleepDir(v >> 12) (voir pose_couchee.py)
                v = a[0]; s = self.sprites.get(v & 0xff)
                if s is not None:
                    if v & 0x300:
                        s['dort'] = bool(v & 0x100)
                        if s['dort']: s['dort_rot'] = (0.0, 0)          # SetSleepPose(vrai) : quadrant 0, rotation identite (la direction suit dans le meme paquet)
                    if v & 0x400: s['dort_rot'] = PC.direction_paquet(v)
            elif t == 17 and len(a) >= 2:           # cmd_chara_sleep_near (D133E4) : (defNear, decalage) ; Chara.SetSleepNear : hauteur du corps couche
                self.dort_haut = PC.hauteur_paquet(a[1])
            elif t == 18 and a:                     # cmd_chara_pose (D13474) : v = personnage | numero << 8 : Chara.SetTexture(numero) = le personnage change de feuille de sprites (TownCharacterDraw::changePose)
                s = self.sprites.get(a[0] & 0xff)
                if s is not None and (a[0] >> 8) >= 0: s['id'] = (a[0] >> 8) | (s['id'] & 4096)
            elif t == 15 and a:                     # cmd_chara_shadow (D13150) : personnage = v & 0xff ; bits 8-9 : ombre visible (bit 8) ; bits 10-11 : ombre separee (bit 10) ; bit 12 : position de l'ombre (3 flottants,
                v = a[0]; s = self.sprites.get(v & 0xff)        # SetShadowPosition) ; bit 13 : opacite (SetShadowAlpha) ; bit 14 : position de l'ombre sur la carte du monde (SetFieldShadowPosition)
                if s is not None:
                    fl = list(f)
                    if v & 0x300: s['ombre'] = bool(v & 0x100)
                    if v & 0xc00: s['ombre_sep'] = bool(v & 0x400)
                    if v & 0x1000 and len(fl) >= 3: s['ombre_pos'] = tuple(fl[:3]); fl = fl[3:]
                    if v & 0x2000 and fl: s['ombre_a'] = float(fl[0])
            elif t == 19 and len(a) >= 2 and 0 <= a[0] < 16:        # cmd_rise_icon_load : emplacement, numero d'icone (< 0 = liberation) ; objet Riseup, materiau Custom/Riseup sur la feuille MenuTexture
                if a[1] >= 0: self.icones[a[0]] = {'id': a[1], 'pos': None, 'alpha': 1.0}
                else: self.icones.pop(a[0], None)
            elif t == 20 and a and len(f) >= 4:     # cmd_rise_icon : emplacement ; x, y, z (SetPosition) puis alpha (Material.color = 1, 1, 1, alpha)
                ic = self.icones.get(a[0])
                if ic is not None: ic['pos'] = tuple(f[:3]); ic['alpha'] = f[3]
            elif t == 9 and a:                      # cmd_fade : duree en images = v & 0x7ff ; bit 12 : sortie vers une couleur (sinon entree) ; bit 11 : couleur r, g, b en flottants ; bit 13 : blanc (sinon noir) ; bit 14 : plan de fond « FadeForBG » (derriere les fenetres ; sinon plan « FadeForMenu », devant tout : voir Etat._fondu)
                self._fondu(a[0], f)
            elif t == 5 and a:                      # cmd_fld_common_anim : objet = v & 0xffff, numero d'animation commune = v >> 16 (FldObject.SetCommonAnimation)
                self.objets_cmd.append(('anim', a[0] & 0xffff, (a[0] >> 16) & 0xffff))
            elif t == 7 and a:                      # cmd_fld_on_off : objet = v & 0xffff, drapeau = v >> 16 (SetMapObjOnOff : drapeau non nul = objet masque)
                self.objets_cmd.append(('onoff', a[0] & 0xffff, (a[0] >> 16) & 0xffff))
            elif t == 2 and a:                      # cmd_fld_alpha : objet = v & 0xffff, niveau (0..31) = v >> 16 & 0xff (SetMapObjAlpha : opacite = niveau / 31)
                self.objets_cmd.append(('alpha', a[0] & 0xffff, (a[0] >> 16) & 0xff))
            elif t == 3 and a and len(f) >= 3:      # cmd_fld_pos : objet ; x, y, z
                self.objets_cmd.append(('pos', a[0] & 0xffff, tuple(f[:3])))
            elif t == 4 and a and len(f) >= 2:      # cmd_fld_rot : objet ; rotation x, y (z = 0)
                self.objets_cmd.append(('rot', a[0] & 0xffff, tuple(f[:2])))
            elif t == 10 and a:
                if charge: cam_vue = True
                elif self.chargement is not None: self.chargement['cam'] = True
                fl = list(f)
                if a[0] & 1 and len(fl) >= 3: self.cam_pos = tuple(fl[:3]); fl = fl[3:]
                if a[0] & 2 and len(fl) >= 3: self.cam_cible = tuple(fl[:3]); fl = fl[3:]
                if a[0] & 4 and len(fl) >= 3: self.cam_rot = tuple(fl[:3])        # combat : rotation (tangage, lacet, roulis) en degres
            elif t == 21 and len(a) >= 2:           # DSSAObject::send_unity_load(emplacement, id de modele) ; id < 0 = liberation
                if a[1] >= 0:
                    self.modeles[a[0]] = a[1]
                    self.mesh_etat[a[0]] = {'shader': 3 if a[1] > 999 else 1, 'vis': True, 'col': (1.0, 1.0, 1.0), 'off': (0.0, 0.0)}      # MeshChara..ctor : shader 1 (DssaMonster0) sauf id > 999 (DssaCharaTransparent) ; couleur blanche
                else: self.modeles.pop(a[0], None); self.maillages.pop(a[0], None); self.mesh_etat.pop(a[0], None)
            elif t == 31 and len(a) >= 2:           # cmd_fbx_load : emplacement, numero de modele (« fbx/c<numero> », FbxObject) ; < 0 = liberation. Le modele est cree cache, sans rotation (le constructeur de FbxObject n'en pose pas ; le moteur envoie la rotation absolue au 1er paquet 32 : FbxObject.SetRotation = Quaternion.Euler puis Transform.set_rotation, 0xCD1748), echelle 1
                if a[1] >= 0: self.fbx[a[0]] = {'id': a[1], 'vis': False, 'pos': (0.0, 0.0, 0.0), 'rot': (0.0, 0.0, 0.0), 'scl': (1.0, 1.0, 1.0), 'col': (1.0, 1.0, 1.0, 1.0), 'anim': []}
                else: self.fbx.pop(a[0], None)
            elif t == 32 and a:                     # cmd_fbx : emplacement = v & 0xff ; bits 8-9 : visibilite (bit 8 = visible) ; 10 : forcer l'animation ; 11 : echelle (3 flottants) ; 12 : couleur (4) ; 13 : position (3) ; 14 : rotation, degres (3) ; 15 : animation (un entier : sequence)
                v = a[0]; m = self.fbx.get(v & 0xff); fl = list(f)
                if FBXLOG: print('FBX image %d paquet 32 : v=%#x ints=%s flottants=%s' % (self.image, v & 0xffff, list(a[1:]), [round(x, 4) for x in fl]), flush=True)         # (test) DQ_FBXLOG=1 : tous les paquets 32 (position, rotation, echelle, couleur, sequence)
                if m is not None:
                    if v & 0x300: m['vis'] = bool(v & 0x100)
                    if v & 0x800 and len(fl) >= 3: m['scl'] = tuple(fl[:3]); fl = fl[3:]
                    if v & 0x1000 and len(fl) >= 4: m['col'] = tuple(fl[:4]); fl = fl[4:]
                    if v & 0x2000 and len(fl) >= 3: m['pos'] = tuple(fl[:3]); fl = fl[3:]
                    if v & 0x4000 and len(fl) >= 3: m['rot'] = tuple(fl[:3]); fl = fl[3:]
                    if v & 0x8000 and len(a) >= 2: m['anim'].append((self.image, int(a[1]), bool(v & 0x400)))
            elif t == 23 and len(a) >= 2:           # cmd_mesh_on_off : emplacement, visible
                if a[0] in self.mesh_etat: self.mesh_etat[a[0]]['vis'] = bool(a[1])
            elif t == 24 and a:                     # cmd_mesh_shader : emplacement | numero de shader << 8 (0 Chara, 1 DssaMonster0, 2 DssaMonster1, 3 DssaCharaTransparent)
                if (a[0] & 0xff) in self.mesh_etat: self.mesh_etat[a[0] & 0xff]['shader'] = a[0] >> 8
            elif t == 25 and a and len(f) >= 3:     # cmd_mesh_color : emplacement ; r, g, b (Material.color, alpha 1)
                if a[0] in self.mesh_etat: self.mesh_etat[a[0]]['col'] = tuple(f[:3])
            elif t == 26 and a and len(f) >= 2:     # cmd_mesh_tex_offset : emplacement ; u, v (Material.SetTextureOffset)
                if a[0] in self.mesh_etat: self.mesh_etat[a[0]]['off'] = tuple(f[:2])
            elif t == 11 and a:        # cmd_camera_sub : bit 0 near, 1 far, 2 fov, 4 yOffset, 5 lookDownAdjust (un flottant chacun, dans l'ordre des bits), 7 camera libre (s_targetCamera = faux)
                k = 0
                for bit, nom in ((0, 'cam_near'), (1, 'cam_far'), (2, 'cam_fov'), (4, 'cam_yoff'), (5, 'cam_bas')):
                    if a[0] >> bit & 1 and k < len(f):
                        v = f[k]; k += 1
                        setattr(self, nom, min(max(v, 0.0), 78.0) if nom == 'cam_fov' else v)       # SceneCamera.SetFOV2 : borne a 78
                if a[0] & 128: self.cam_libre = True
            elif t == 22 and len(a) >= 2:           # maillage dynamique : [emplacement, nb sommets, couleurs (1 octet/sommet, 4 par entier), indices...] + flottants [x, y, z, (u, v, x, y, z) * nb sommets]
                nv = a[1]; nc = (nv + 3) // 4; idx = a[2 + nc:]
                if len(f) >= 3 + 5 * nv and idx:
                    v = [f[3 + 5 * i:8 + 5 * i] for i in range(nv)]
                    self.maillages[a[0]] = {'pos': tuple(f[:3]), 'v': v, 'idx': list(idx), 'col': list(a[2:2 + nc])}       # col : un octet par quad (4 sommets), 255 = opaque
                    self.maillages_vus.add(a[0])
            elif t in (35, 36, 37) and a:           # cmd_se_play / cmd_se_stop / cmd_bgm (Sound.PlaySE, StopSE, PlayBGM ; valeur >= 4096 = StopBGM)
                self.sons.append((t, a[0]))
                if t == 37: self.musique = a[0] if 0 <= a[0] < 4096 else None
            elif t == 13 and a:
                fl = list(f); flags = a[0]; s = self.sprites.get(flags & 0x7ff)
                if s is None: continue
                if flags & 0x800 and fl:                # cmd_chara (D12EA8) : bit 11 = Chara.SetScale(echelle) : Transform.localScale = 1,8 x echelle sur le panneau du personnage (pas sur son ombre)
                    if s['pos'] is not None: s['ech'] = float(fl[0])      # (la 1re mise a jour d'un personnage, celle qui le place, porte une valeur de depart sans suite : 0,0253 a 0,08 puis 1,0 en une image ; observee sur 529 cartes, 1062 personnages : ignoree)
                    fl = fl[1:]
                if flags & 0x1000: s['col'] = tuple(fl[:4]); fl = fl[4:]
                if flags & 0x2000 or flags & 0x8000: s['pos'] = tuple(fl[:3]); fl = fl[3:]      # 0x8000 : meme position, version carte du monde (pixels)
                if flags & 0x4000 and len(a) > 1:
                    s['pose'] = a[1] & 0xff; s['dir'] = (a[1] >> 8) & 0xff
                    if s['pos'] is None and self.image - s.get('cree', 0) >= ORIGINE_APRES: s['pos'] = (0.0, 0.0, 0.0)       # le moteur n'envoie une position que si elle change de celle qu'il croit deja posee (son enregistrement du personnage : (0, 0, 0)) :
                                                                          # un personnage anime qui n'en a pas recu au bout de quelques images est a l'origine (Chara cree a (0, 0, 0) par Unity) ; mqtf3, mom2f1, msm1f1, emplacement 8 : le PNJ
                                                                          # du milieu de la piece n'etait pas dessine. (Les positions des autres arrivent 1 image apres la creation : pas d'apparition d'une image a l'origine.)
        if charge:         # chargement de carte : dessin retenu (voir maj_chargement) si l'ecran est couvert, soit par un fondu deja la, soit par le fondu d'entree lance avec ce chargement (il repart de l'opacite 1)
            if couvert or any(fd['a'] >= CHARGEMENT_COUVERT and fd['fin'] == 0.0 and fd['n'] >= 1 for fd in (self.fondu, self.fondu_fond)): self.chargement = {'n': -1, 'cam': cam_vue}
            else: self.chargement = None

    def _fondu(self, v, f):
        """Fade.SetFadeIn / SetFadeOutBlack / SetFadeOutWhite / SetFadeOutColor (FadePlane.Command) : sortie = vers l'opacite 1 depuis l'opacite courante ;
        entree = le plan repart de l'opacite 1 vers 0 (Unity part de l'opacite courante du plan : meme chose apres une sortie terminee). Duree <= 1 image : immediat."""
        script = bool(v & PJ.MARQUE_FONDU_SCRIPT)                                          # fondu lance par une commande de script du jeu (marque posee par Moteur._crochets_fondu) : sa duree est celle du script
        d = v & 0x7ff; fd = self.fondu_fond if v & 0x4000 else self.fondu; fd['noir'] = 0      # bit 14 : Fade.l_targetLayer (NativeManager.cmd_fade D14D10), le plan qui recoit la commande
        fd['combat'] = self.partie == PARTIE_COMBAT or self.fen_entree > 0 or self.fen_retour > 0        # fondu d'un combat (arrivee dans la scene, sortie, retour a la carte) : marque pour transition_combat (sa duree suit « Vitesse de transition » comme tout fondu au noir, #47)
        d0 = d
        if not v & (0x800 | 0x2000): d = PJ.duree_fondu(d, Etat.vitesse_fondu, script)       # fondu au noir (changement de carte, arrivee en combat, fin de combat, retour a la carte) plus court : reglage « vitesse des transitions » (pas pour un fondu de script)
        self.rapport_fondu = (self.image, (d / d0) if d0 > 1 and v & 0x1000 else 1.0)      # fondu au noir raccourci : le decompte du bruitage de sortie du moteur suit (Moteur._decompte_sortie)
        if v & 0x1000:
            fd['col'] = tuple(f[:3]) if v & 0x800 and len(f) >= 3 else ((1.0, 1.0, 1.0) if v & 0x2000 else (0.0, 0.0, 0.0))
            fd['fin'] = 1.0
            if d <= 1: fd['a'] = 1.0; fd['n'] = 0; fd['pas'] = 0.0
            else: fd['pas'] = (1.0 - fd['a']) / d; fd['n'] = d
        else:
            fd['fin'] = 0.0
            if d <= 1: fd['a'] = 0.0; fd['n'] = 0; fd['pas'] = 0.0
            else: fd['a'] = 1.0; fd['pas'] = -1.0 / d; fd['n'] = d

    def maj_chargement(self):
        """Fin de la retenue du dessin apres un chargement de carte (une fois par image du moteur, apres `appliquer`). La visionneuse n'a vu que le paquet 0 (nouveau decor) a l'image du chargement : camera de la scene
        d'avant, personnages sans position, ni teinte ni ordres d'objets ; le moteur envoie la camera (paquet 10) et les positions (paquet 13) a l'image suivante (59 cartes essayees, 529 cartes comptees : toujours le decalage 1).
        Tant que `chargement` existe, la fenetre ne dessine que les plans de fondu (noir de l'ecran couvert) et les fondus d'entree sont suspendus (`tick_fondu`) : le fondu du jeu garde toute sa duree, il commence juste
        une image plus tard, sur une scene complete. Prete : au moins CHARGEMENT_MIN image, camera recue, et personnages visibles tous places (au plus CHARGEMENT_PLACEMENT images d'attente) ; garde-fou CHARGEMENT_MAX."""
        ch = self.chargement
        if ch is None: return
        ch['n'] += 1                                                       # images du moteur depuis le chargement (0 a l'image du chargement : compte propre, pas de difference d'images : un etat charge peut remettre le compteur d'images a zero)
        places = all(sp['pos'] is not None for sp in self.sprites.values() if sp.get('vis', True))
        monde = self.partie != PARTIE_CHAMP or self.champ is not None      # carte du monde : attendre aussi ses tuiles (paquet 28)
        if ch['n'] >= CHARGEMENT_MAX or (ch['n'] >= CHARGEMENT_MIN and monde and ch['cam'] and (places or ch['n'] >= CHARGEMENT_PLACEMENT)): self.chargement = None

    def tick_fondu(self):
        """FadePlane.Update : une fois par image du jeu, pour chacun des deux plans. Garde-fou (plan de devant seulement) : un ecran reste tout noir plus de 6 s (fondu d'entree lance par Unity lui-meme, pas par le moteur) est rouvert ;
        le plan de fond n'en a pas : le moteur le tient noir de lui-meme (titre de chapitre, 160 images) et le rouvre par une commande."""
        for fd, garde in ((self.fondu, True), (self.fondu_fond, False)):
            if self.chargement is not None and fd['fin'] == 0.0 and fd['n'] >= 1: continue      # retenue du dessin apres un chargement : un fondu d'entree ne commence qu'avec la scene en place
            if fd['n'] >= 1:
                fd['n'] -= 1
                if fd['n'] < 1:
                    fd['a'] = fd['fin']
                    if fd.get('combat') and fd['fin'] >= 1.0: self.garde_trans = GARDE_TRANSITION      # sortie au noir d'un combat finie : le moteur change de scene dans 1 a 3 images, puis lance le fondu d'entree ; l'horloge ne doit pas changer entre les deux
                else: fd['a'] += fd['pas']
            if garde and fd['a'] >= 0.999 and fd['n'] < 1:
                fd['noir'] += 1
                if fd['noir'] > 180: fd['fin'] = 0.0; fd['pas'] = -1.0 / 15; fd['n'] = 15; fd['noir'] = 0
            else: fd['noir'] = 0


DBG = bool(os.environ.get('DQ_UIDBG'))


class Interface:
    """Ce que l'interface Unity memorise des messages du moteur : une fenetre par port (liste de textes, curseur, ouverte ou non).
    Messages d'un port (apres le premier octet = nombre d'arguments) : [1,..] ouvre ; [7,0] ferme ; [11,ligne,colonne] annonce
    que le message suivant du port est le texte de cette case ; [4,i] curseur sur la ligne i ; [12,ligne,x] et [10,..] reglages."""
    def __init__(self):
        self.f = {}; self.attente = {}; self.ordre = 0
        self.msg = {'type': 0, 'y': 0, 'feed': False, 'shake': 0, 'qui': '', 'qui_att': False}      # fenetre de message (port 1) : type de fenetre, defilement du canevas, curseur de fin de page, nom de l'interlocuteur (« qui ») ; qui_att : le paquet suivant du port porte ce nom
        self.degats = []           # nombres de degats a faire sauter sur les monstres : (monstre, hauteur, degats), vides par la visionneuse
        self.systeme = []          # messages du port 0 adresses a l'hote : (code, arguments...) ; 999 = quitter (MenuPortSendQuit), 6 = portail, 4 / 5 = volumes, 7 = taille du nom, 8 = manette
        self.obs = None            # observateur facultatif (visionneuse) : ouvrir(port, type), fermer(port), param_int/param_str/code/selection

    def fen(self, port):
        if port not in self.f: self.f[port] = {'cases': {}, 'vis': False, 'cur': 0, 'ordre': 0, 'indic': {}, 'type': None, 'act': False, 'req': False, 'draw': False, 'force': False, 'ign': False, 'sv': True}
        return self.f[port]

    def appliquer(self, liste):
        if DBG:
            for port, a in liste:
                if port in (0, 1) or port >= 12: print('MSG image %s port %d %s' % (getattr(self, 'image', '?'), port, a[:10]), flush=True)
        for port, a in liste:
            if port == 1:                                       # fenetre de message : dessinee d'apres le canevas du moteur ; MenuMessage.NoticeReceive : 0 type, 1 curseur, 2 secousse, 3 defilement, 4 nom de l'interlocuteur
                if self.msg['qui_att']:                         # [4, 1] a annonce un nom : le paquet suivant du port en est le texte (un entier par caractere, comme les textes des cases des menus)
                    self.msg['qui_att'] = False; self.msg['qui'] = ''.join(chr(v & 0xffff) for v in a if v).strip()
                    continue
                if len(a) >= 2:
                    c, v = a[0], a[1]
                    if c == 0: self.msg['type'] = v
                    elif c == 1: self.msg['feed'] = (v & 0xffff) == 1
                    elif c == 3: self.msg['y'] = v
                    elif c == 4:                                # [4, 0] : pas de nom (cadre sans onglet) ; [4, 1] : le nom suit (cadre avec onglet, seulement pour la fenetre du terrain : MenuMessage.NoticeReceive, commande 4)
                        if (v & 0xffff) != 0: self.msg['qui_att'] = True
                        else: self.msg['qui'] = ''
                continue
            if port == 0:
                if len(a) >= 2 and a[0] == 0: self.systeme.append(tuple(a[1:]))
                if len(a) >= 2 and 2 <= a[0] < 32:
                    if a[1] == 3: self.fen(a[0])['sv'] = bool(a[2]) if len(a) > 2 else True       # [fenetre, 3, visible] : MenuPort.SetVisible
                    elif a[1] == 2:                                                                # [fenetre, 2] : fermee
                        f = self.fen(a[0]); f['act'] = f['vis'] = False; f['ferme'] = True          # (les messages d'arret du moteur peuvent remettre « act » : « ferme » reste jusqu'a la creation suivante)
                        if self.obs: self.obs.fermer(a[0])
                    elif a[1] == 1 and len(a) >= 4:                                                # [fenetre, 1, categorie, type] : cree un menu du type donne (MenuPortItemTable.Make_*)
                        f = self.fen(a[0]); f['type'] = a[3]; f['cases'] = {}; f['indic'] = {}; f['cur'] = 0; f['ints'] = {}; f['dispo'] = None; f['listes'] = {}; f['suite'] = None
                        f['act'] = f['req'] = f['draw'] = f['force'] = f['ign'] = False; f['sv'] = True; f['vis'] = False; f['att'] = None; f['plaq'] = {}; f['n_codes'] = {}; f['ferme'] = False
                        if self.obs: self.obs.ouvrir(a[0], a[3])
                continue
            f = self.fen(port)
            if f.get('ferme'):                                  # MenuPortSystem.internalUpdate (D10A54) : [port, 2] detruit l'element (`s_ports[port] = null`), les messages du port recus ensuite (meme image : les ports 12 a 31 sont lus apres le port 0)
                self.attente.pop(port, None)                    # n'ont plus de destinataire (`if (item != null) item.NoticeReceive`) ; avant, la fin de la liste des journaux (5, 6, 4) rouvrait la fenetre fermee une image : boite « simple » violette
                continue
            if f['type'] == 43:                                 # Make_BattleHoppingNumber : [12, 0, 0] puis [monstre, hauteur, degats] (BattleMenu_setHoppingNumbers)
                if f.get('dgt'):
                    f['dgt'] = False
                    if len(a) >= 3: self.degats.append(tuple(a[:3]))
                    continue
                if len(a) >= 3 and a[0] == 12: f['dgt'] = True; continue
            if port in self.attente:                            # texte de la case annoncee
                cle = self.attente.pop(port); txt = ''.join(chr(v & 0xffff) for v in a if v); f['cases'][cle] = txt
                if self.obs: self.obs.param_str(port, cle[0], cle[1], txt)
                continue
            if f.get('suite') is not None:                      # fenetre de carte (type 25) : la liste de nombres qui suit les codes 3 (lieux decouverts) et 5 (voile) du moteur (MenuPort.Receive des fonctions de Make_CityMap), pas une commande
                f.setdefault('listes', {})[f['suite']] = [v & 0xffff for v in a]; f['suite'] = None
                continue
            if f['type'] == 31 and f.get('att'):               # plaque de monstre : messages qui suivent un code > 0 (nom, puis [x, y, ...])
                i, etape = f['att']
                if etape == 'nom': f['plaq'][i]['nom'] = ''.join(chr(v & 0xffff) for v in a if v); f['att'] = (i, 'prm')
                else:
                    f['plaq'][i]['prm'] = list(a); f['att'] = None
                    if self.obs and hasattr(self.obs, 'plaque'): self.obs.plaque(port, i, f['plaq'][i]['nom'], f['plaq'][i]['prm'], f['plaq'][i]['code'])
                continue
            if not a: continue
            cmd = a[0]
            if cmd != 7 and not f['act']: f['act'] = True; f['force'] = True       # MenuPortItem.NoticeReceive : premiere commande -> parties activees, dessin force
            if cmd == 11 and len(a) >= 3: self.attente[port] = (a[1], a[2])
            elif cmd == 1:
                if port >= 12: f['cases'] = {}; f['indic'] = {}; f['cur'] = 0; f['ints'] = {}; f['listes'] = {}; f['suite'] = None           # fenetre dynamique : contenu neuf
                self.ordre += 1; f['ordre'] = self.ordre
            elif cmd == 2 and len(a) >= 3: f['grille'] = tuple(a[1:4])                 # setItemMenu : colonnes, lignes, nombre de cases du curseur du moteur
            elif cmd == 6: f['inp'] = True                                              # demande de saisie (a chaque image tant que le menu attend une touche)
            elif cmd == 5: f['req'] = True                                             # demande de dessin : le moteur la renvoie a chaque image tant que la fenetre doit etre vue
            elif cmd == 7: f['act'] = False                                            # arret : parties desactivees
            elif cmd == 8 and len(a) >= 2: f['ign'] = (a[1] & 0xffff) != 0            # ignorer les demandes de dessin (toujours visible)
            elif cmd == 4 and len(a) >= 2:
                f['cur'] = a[1]
                if self.obs: self.obs.selection(port, a[1])
            elif cmd == 10 and len(a) >= 5:                    # setItemParamInt [id, no, bas, haut] : valeur 32 bits
                v = (a[3] & 0xffff) | ((a[4] & 0xffff) << 16); v = v - (1 << 32) if v & 0x80000000 else v
                f.setdefault('ints', {})[(a[1], a[2])] = v                                   # gardes pour rejouer la fenetre (etats instantanes)
                if self.obs: self.obs.param_int(port, a[1], a[2], v)
            elif cmd == 12 and len(a) >= 3:
                f['indic'][a[1]] = a[2]; f.setdefault('n_codes', {})[a[1]] = f.get('n_codes', {}).get(a[1], 0) + 1          # nombre de fois que chaque code est arrive (le titre : TapToStart.CountReset = code 0 du port 12)
                if f['type'] == 25 and a[1] in (3, 5): f['suite'] = a[1]               # ICityMap : code 3 = lieux decouverts (x + 256 y, un par nombre), code 5 = voile (16 nombres : un bit par bloc de 10 x 10 pixels non explore)
                if f['type'] == 31 and a[1] < 4 and a[2] >= 1:                                  # MonsterNamePlate.ReceiveParameters(code >= 1)
                    f.setdefault('plaq', {})[a[1]] = {'code': a[2]}; f['att'] = (a[1], 'nom')
                elif f['type'] == 31 and a[1] == 5:                                             # disposition des plaques (nombre de plaques)
                    f['dispo'] = a[2]
                    if self.obs and hasattr(self.obs, 'disposer'): self.obs.disposer(port, a[2])
                elif self.obs: self.obs.code(port, a[1], a[2])

        for f in self.f.values():                              # MenuPortItem.Update : visible tant que le moteur demande le dessin a chaque image
            if not f['ign']:
                if f['force']: f['force'] = False; f['draw'] = f['req']
                elif f['draw'] != f['req']: f['draw'] = f['req']
            f['req'] = False; f['entree'] = f.get('inp', False); f['inp'] = False
            f['vis'] = f['act'] and f['sv'] and (f['draw'] or f['ign'])

    def visibles(self):
        return sorted(((p, f) for p, f in self.f.items() if f['vis'] and f['cases']), key=lambda x: x[1]['ordre'])


class Moteur:
    def __init__(self, dossier_apk, dossier_lecture, dossier_ecriture, langue=1):
        self.log = Silencieux()
        lib = zipfile.ZipFile(os.path.join(dossier_apk, 'split_config.arm64_v8a.apk')).read(LIB_APK)
        pack = os.path.join(dossier_apk, 'split_UnityDataAssetPack.apk')
        self.apk_donnees = pack
        CoreJeu.dossier_lecture, CoreJeu.dossier_ecriture = dossier_lecture, dossier_ecriture
        c = self.core = CoreJeu(lib, T.ApkFs([pack]), self.log, real_files={'/dq/assets.apk': pack})
        self.E = c.export; self.L = c.LIB_BASE
        self._elargir_symboles()
        if not c.run_init(): raise RuntimeError('constructeurs C++ en echec')
        c.call(self.E('DevInit'), c.cstr('/dq/assets.apk'), c.cstr('/dq/'), langue)
        self.buf1, self.buf2 = c.malloc(0x2000), c.malloc(0x2000)          # files de messages interface <-> moteur (allouees par l'appelant)
        c.call(self.E('MenuPortInit'), 32, self.buf1, 129, self.buf2, 1089)
        NB = 0x40000
        c.inp, c.outp, c.outf, c.strb = c.malloc(NB), c.malloc(NB), c.malloc(NB), c.malloc(0x10000)
        c.call(self.E('GameInit'), c.inp, c.outp, c.outf, c.strb)
        c.mem_w(self.L + G_IS_AMAZON, b'\x01')              # menu de depart : pas de « Sauv. cloud » (Google Play Games / serveur Square Enix absents sur PC) ; l'original retire la meme case pour la version Amazon
        self.pk = PacketLog(c)
        self.etat = Etat()
        self.msgs_ui = []                        # messages moteur -> interface (menus), derniere image
        self.ui = Interface()                    # fenetres de menu memorisees
        self.images = 0; self._decompte = 0; self._decompte_arme = -99; self._decompte_fait = True      # decompte du bruitage de sortie (voir _decompte_sortie)
        # animations d'objets de la carte (portes...) : le moteur attend qu'Unity les termine (bit0 de l'octet +0x14 de l'entree)
        self.anims = []                          # [(image d'echeance, index d'objet)]
        self.duree_anim = None                   # (objet, numero) -> images avant la fin de l'animation commune (donnee par la fenetre, d'apres les donnees de la carte) ; None = DUREE_ANIM
        self.fldobj = 0
        self.msg_visible = False                 # fenetre de message affichee ? (MenuPort::SetVisible sur le port du message)
        def _sv(uc, a, sz, u):
            port = uc.reg_read(c.XREG[0]) & 0xffffffffffff
            if port and port == struct.unpack('<Q', c.mem(self.L + OBJ_MESSAGE + 0x30, 8))[0]:
                self.msg_visible = bool(uc.reg_read(c.XREG[1]) & 0xff)
                if not self.msg_visible: self._acc_texte = 0.0; self.ui.msg['qui'] = ''; self.ui.msg['qui_att'] = False        # MenuMessage.SetVisible(false) efface le texte du nom (m_who)
        hv = c.export('_ZN8MenuPort10SetVisibleEb')
        c.uc.hook_add(unicorn.UC_HOOK_CODE, _sv, None, hv, hv)
        self.fielddata = 0; self._grille = None; self._grille_img = -999
        self.retour_titre_etat = None            # retour au titre : None, 'ouvrir' (a lancer au prochain pas) ou 'dialogue' (la boite Oui / Non du jeu attend la reponse) ; voir demander_retour_titre
        self.demande_pause = False               # le joueur a choisi « Paramètres » dans le menu Divers : la visionneuse ouvre son menu Pause (voir _detourner_parametres)
        self._detourner_parametres()
        def _fd(uc, a, sz, u): self.fielddata = uc.reg_read(c.XREG[0]) & 0xffffffffffff          # FieldData::drawBlock(this) : l'objet qui porte la carte du monde
        hfd = c.export('_ZN9FieldData9drawBlockEv')
        c.uc.hook_add(unicorn.UC_HOOK_CODE, _fd, None, hfd, hfd)
        def _sca(uc, a, sz, u): self.fldobj = uc.reg_read(c.XREG[0])
        uc_hook = c.export('_ZN9FLDObject18SetCommonAnimationEii')
        c.uc.hook_add(unicorn.UC_HOOK_CODE, _sca, None, uc_hook, uc_hook)
        self._crochets_texte()
        self._crochets_fondu()
        self._crochets_niveau()
        self._crochets_rencontres()
        self._crochets_magie()
        self.capteur = Capteur(self)             # historique des dialogues : crochet sur TextBuffer::cat (installe avant la premiere image : Unicorn garde les blocs deja traduits)
        self.capteur_combat = CapteurCombat.pour(self)       # historique des combats : crochets en lecture seule (ennemis vaincus, or, experience ; voir historique_combat.py)
        for _ in range(3): self.step(0, 0)       # le titre tourne quelques images (curseurs initialises)
        self._creer_canevas()

    def _crochets_texte(self):
        """Vitesse du texte des dialogues et defilement des combats (reglages du joueur, menu Echap).
        - Texte : ui_MsgLoop ecrit, a chaque image du moteur (30 Hz), `vitesse x 4` lettres (vitesse = mot a MSG_VITESSE, copie du tableau du type de fenetre : 1 pour les dialogues, 100 pour les fenetres de combat qui
          affichent leur ligne d'un coup). Un crochet sur `sxth w20, w8` remplace ce nombre par celui du reglage (`vitesse_texte`, lettres par image, fractions cumulees ; 4 = comme le jeu : le crochet ne fait rien).
        - Combats : BattleAutoFeed lit OptionStatus.battleSpeed (g_Option + 5, option « Vitesse des messages » du jeu, enregistree dans la sauvegarde) a chaque message : `defilement` (None = on ne touche a rien)
          est ecrit a cette adresse avant chaque image ; un changement fait par le joueur dans la fenetre Parametres du jeu (setBattleSpeed appele depuis TownMenu_OPERATION_SETTING::menuUpdate) est
          signale a `rappel_defilement(valeur)` (le chargement d'une sauvegarde, lui, passe par Profile::deliverDATA_PARTY et ne declenche rien)."""
        c = self.core
        self.vitesse_texte = 4.0; self._acc_texte = 0.0
        self.defilement = None; self.rappel_defilement = None; self._defil_origine = None
        try:
            a = c.export('_Z10ui_MsgLoopv')
            if a and struct.unpack('<I', c.mem(a + UI_MSGLOOP_ECRITURE, 4))[0] == SXTH_W20_W8:        # autre version du moteur : on ne touche a rien
                def _vt(uc, ad, sz, u):
                    jeu = uc.reg_read(c.XREG[8]) & 0xffff                                  # lettres que le moteur s'apprete a ecrire (mot de vitesse de la fenetre x 4)
                    v = PJ.lettres_par_image(self.vitesse_texte, jeu)                      # reglage du joueur seulement tant que le jeu est a sa vitesse standard (4) ; une autre valeur (100 des fenetres de combat, vitesse fixee par le jeu) est la sienne
                    if v == jeu: return                                                    # vitesse du jeu : inchange (aussi quand le reglage est « comme le jeu », 4)
                    self._acc_texte += v; n = int(self._acc_texte); self._acc_texte -= n
                    uc.reg_write(c.XREG[8], min(n, 4000))
                c.uc.hook_add(unicorn.UC_HOOK_CODE, _vt, None, a + UI_MSGLOOP_ECRITURE, a + UI_MSGLOOP_ECRITURE)
            else: print('vitesse du texte : ui_MsgLoop inattendu, reglage sans effet', flush=True)
        except Exception as ex: print('vitesse du texte non installee :', ex, flush=True)
        try:
            sb = c.export('_ZN6status12OptionStatus14setBattleSpeedEc'); mu = c.export('_ZN26TownMenu_OPERATION_SETTING10menuUpdateEv')
            if sb and mu:
                def _sb(uc, ad, sz, u):
                    if self.defilement is not None and self.rappel_defilement is not None and mu <= uc.reg_read(c.XREG[30]) < mu + 0x400: self.rappel_defilement(uc.reg_read(c.XREG[1]) & 0xff)
                c.uc.hook_add(unicorn.UC_HOOK_CODE, _sb, None, sb, sb)
        except Exception as ex: print('defilement des combats : crochet non installe :', ex, flush=True)

    def _crochets_niveau(self):
        """Option « PV et PM restaures au niveau superieur » (`soin_niveau`, faux = comme le jeu). Toute montee de niveau passe par `HaveStatus::levelup(bool)` : elle recalcule les caracteristiques, puis, si l'argument est vrai
        (c'est le cas de `debugLevelup`), remet PV et PM a leur maximum (`tbz w20, #0` a +0x3f8 : PV <- PV max, PM <- PM max). Un crochet sur cette instruction force le bit quand l'option est active ; le reste du calcul est celui du jeu."""
        c = self.core; self.soin_niveau = False
        try:
            a = c.export('_ZN6status10HaveStatus7levelupEb')
            if not a or struct.unpack('<I', c.mem(a + HAVESTATUS_LEVELUP_FIN, 4))[0] != TBZ_W20_0:
                print('PV/PM au niveau superieur : HaveStatus::levelup inattendu, option sans effet', flush=True); return
            def _soin(uc, ad, sz, u):
                if self.soin_niveau: uc.reg_write(c.XREG[20], uc.reg_read(c.XREG[20]) | 1)
            c.uc.hook_add(unicorn.UC_HOOK_CODE, _soin, None, a + HAVESTATUS_LEVELUP_FIN, a + HAVESTATUS_LEVELUP_FIN)
            try: c.uc.ctl_flush_tb()
            except Exception: pass
        except Exception as ex: print('PV/PM au niveau superieur : crochet non installe :', ex, flush=True)

    def _crochets_rencontres(self):
        """Rencontres aleatoires et marche acceleree (voir rencontres.py). `vitesse_marche` (ecrit par la visionneuse avant chaque pas : facteur d'acceleration de la marche, 1 = normale ; toujours 1 en combat)
        > 1 : le crochet sur `str w8, [x0]` de `CountDown::exec` (w9 = compteur avant, w8 = apres) remplace la perte du compteur par (1 + a) / (2 a) fois celle du jeu, de sorte que les rencontres par seconde
        reelle soient (1 + a) / 2 fois celles de x1 et non a fois. A 1 (ou moins) : le crochet ne fait rien (le jeu d'origine, a l'identique)."""
        c = self.core; self.vitesse_marche = 1.0; self.rencontres = RE.Reducteur()
        try:
            a = c.export('_ZN9CountDown4execEv')
            if not a or struct.unpack('<I', c.mem(a + COUNTDOWN_EXEC_ECRITURE, 4))[0] != STR_W8_X0:
                print('rencontres : CountDown::exec inattendu, vitesse de marche sans effet sur la frequence des rencontres', flush=True); return
            def _cd(uc, ad, sz, u):
                v = self.vitesse_marche
                if v <= 1.0: return                                                          # x1 : le jeu tel quel
                r = self.rencontres; r.facteur = RE.facteur_par_pas(v)
                avant = uc.reg_read(c.XREG[9]) & 0xffffffff; apres = uc.reg_read(c.XREG[8]) & 0xffffffff
                avant -= (avant & 0x80000000) << 1; apres -= (apres & 0x80000000) << 1      # entiers signes de 32 bits (le compteur devient negatif au declenchement)
                uc.reg_write(c.XREG[8], (avant - r.retenir(avant - apres)) & 0xffffffff)
            c.uc.hook_add(unicorn.UC_HOOK_CODE, _cd, None, a + COUNTDOWN_EXEC_ECRITURE, a + COUNTDOWN_EXEC_ECRITURE)
            try: c.uc.ctl_flush_tb()
            except Exception: pass
        except Exception as ex: print('rencontres : crochet non installe :', ex, flush=True)

    def _crochets_magie(self):
        """Sorts du menu Magie (hors combat) qui coutent des PM mais n'en depensent aucun : le moteur ne depense les PM que si le sort a eu un effet (`BaseAction::useMp`), mais pour les soins il annonce quand meme le message
        de succes (la table des actions donne le meme texte au succes et a l'echec : « Les blessures de X guerissent ! » a PV pleins). Le menu Magie lance le sort par `UseAction::execUse` a deux endroits (choix d'une
        cible : `TownMenu_MAGIC_CHARSELECT::menuUpdate` ; sort de groupe ou sans cible : `TownMenu_MAGIC_ROOT::useMagicNoTarget`) puis affiche `param + 0x1f8` (« X lance le sort Y ! ») et la liste `param + 0x210`.
        Un crochet avant l'appel note les PM du lanceur, un crochet apres compare : si le sort coute des PM (table `excelParam`), que les PM n'ont pas baisse et que le jeu annonce son message de succes (champs 1 / 3 de la
        table des messages) ou aucun, la liste devient le message du jeu « Mais il ne se passe rien. » (`MSG_IL_NE_SE_PASSE_RIEN`, une seule fois, meme pour un groupe). Les messages d'echec propres au jeu (Rappel, Antipoison, Evac'...) et le combat ne changent pas."""
        c = self.core; self._magie = None; self._magie_muet = False
        try:
            cs, nt = c.export('_ZN25TownMenu_MAGIC_CHARSELECT10menuUpdateEv'), c.export('_ZN19TownMenu_MAGIC_ROOT16useMagicNoTargetEv')
            msg, exc = c.export('_ZN6status17BaseActionMessage12actionParam_E'), c.export('_ZN6status10excelParamE')
            u32 = lambda a: struct.unpack('<I', c.mem(a, 4))[0]; u64 = lambda a: struct.unpack('<Q', c.mem(a, 8))[0]
            def est_execuse(a):                                                            # `bl` vers le stub de UseAction::execUse ?
                w = u32(a); return w & 0xfc000000 == 0x94000000 and a + ((((w & 0x3ffffff) ^ 0x2000000) - 0x2000000) << 2) == c.LIB_BASE + MAGIE_EXECUSE_STUB
            sites = [(cs + MAGIE_CHARSELECT_BL, False), (nt + MAGIE_SANS_CIBLE_BL, True)] if cs and nt and msg and exc else []
            if not sites or not all(est_execuse(a) for a, _ in sites) or u32(u64(msg) + 0x48 * 201 + 0x14) != MSG_RIEN_NE_SE_PASSE:
                print('sorts sans effet : menu Magie inattendu, le message de succes est garde', flush=True); return
            def _avant(uc, ad, sz, u):
                p = uc.reg_read(c.XREG[0]) & 0xffffffffffff; lanceur = u64(p); action = u32(p + MAGIE_ACTION)
                cout = c.mem(u64(exc + 0x70) + 0x48 * action + 0x3a, 1)[0]                  # UseAction::getUseMp
                self._magie = (p, lanceur, struct.unpack('<H', c.mem(lanceur + MAGIE_PM, 2))[0], cout, action) if lanceur and cout else None
            def poser(groupe):
                def _apres(uc, ad, sz, u):
                    m, self._magie = self._magie, None
                    if not m: return
                    p, lanceur, pm, cout, action = m
                    if struct.unpack('<H', c.mem(lanceur + MAGIE_PM, 2))[0] < pm: return        # PM depenses : le sort a eu un effet
                    e = u64(msg) + 0x48 * action; r = u32(p + MAGIE_RESULTAT)
                    if r and r not in (u32(e + 4), u32(e + 0xc)): return                    # le jeu a deja son message d'echec
                    c.mem_w(p + MAGIE_RESULTAT, struct.pack('<II', MSG_IL_NE_SE_PASSE_RIEN, 0))
                    if groupe: c.mem_w(self.L + MAGIE_NB_CIBLES, b'\x01'); self._magie_muet = True      # un seul exemplaire du message (le moteur l'affiche une fois par cible vivante)
                return _apres
            for (a, groupe) in sites:
                c.uc.hook_add(unicorn.UC_HOOK_CODE, _avant, None, a, a); c.uc.hook_add(unicorn.UC_HOOK_CODE, poser(groupe), None, a + 4, a + 4)
            def _fin(uc, ad, sz, u):                                                       # sortie de la boucle des cibles : plus de bruitage de soin en attente (menuUpdate en joue un par cible restante) si rien ne s'est passe
                if self._magie_muet: self._magie_muet = False; c.mem_w(self.L + MAGIE_NB_CIBLES, b'\x00')
            c.uc.hook_add(unicorn.UC_HOOK_CODE, _fin, None, nt + MAGIE_FIN_BOUCLE, nt + MAGIE_FIN_BOUCLE)
            try: c.uc.ctl_flush_tb()
            except Exception: pass
        except Exception as ex: print('sorts sans effet : crochet non installe :', ex, flush=True)

    def _crochets_fondu(self):
        """Fondus lances par une commande de SCRIPT du jeu (fade_in / fade_out : `__cmd_fade_in::initialize`, `__cmd_fade_out::initialize`, qui appellent Global::fadeIn / fadeOutBlack... puis UnitySetFade avec la duree
        du script, et attendent eux-memes ce nombre d'images : `isEnd` compte les images) : le paquet 9 recoit la marque PJ.MARQUE_FONDU_SCRIPT, et Etat._fondu ne raccourcit pas ce fondu (reglage « vitesse des
        transitions » : il vaut pour les fondus du moteur, changements de carte..., pas pour ceux qu'un script a fixes). Sans la marque, le fondu raccourci laisserait l'ecran noir jusqu'a la fin de l'attente du script."""
        c = self.core; self._fondu_script = False
        try:
            ini = [c.export('_ZN13__cmd_fade_in10initializeEPc'), c.export('_ZN14__cmd_fade_out10initializeEPc')]; usf = c.export('_Z12UnitySetFadei')
            if not all(ini) or not usf: print('fondus de script : fonctions du moteur introuvables, reglage applique a tous les fondus', flush=True); return
            def fin_de(a):                                                       # adresse apres le `ret` de la fonction
                for k in range(80):
                    if struct.unpack('<I', c.mem(a + 4 * k, 4))[0] == 0xd65f03c0: return a + 4 * (k + 1)
                return None
            fins = [fin_de(a) for a in ini]
            if None in fins or struct.unpack('<I', c.mem(usf + 8, 4))[0] != 0x5280012a:        # UnitySetFade : `mov w10, #9` (type du paquet) a +8 ; autre version du moteur : on ne touche a rien
                print('fondus de script : UnitySetFade inattendu, reglage applique a tous les fondus', flush=True); return
            def _entree(uc, ad, sz, u): self._fondu_script = True
            def _sortie(uc, ad, sz, u): self._fondu_script = False
            def _paquet(uc, ad, sz, u):
                if self._fondu_script:
                    self._fondu_script = False
                    uc.reg_write(c.XREG[0], (uc.reg_read(c.XREG[0]) & 0xffffffff) | PJ.MARQUE_FONDU_SCRIPT)
            for a, f in zip(ini, fins):
                c.uc.hook_add(unicorn.UC_HOOK_CODE, _entree, None, a, a); c.uc.hook_add(unicorn.UC_HOOK_CODE, _sortie, None, f - 4, f - 4)
            c.uc.hook_add(unicorn.UC_HOOK_CODE, _paquet, None, usf, usf)
            try: c.uc.ctl_flush_tb()                                             # (blocs deja traduits avant les crochets)
            except Exception: pass
        except Exception as ex: print('fondus de script : crochet non installe :', ex, flush=True)

    def _option(self, decalage):
        """Adresse d'un octet de status::g_Option (OptionStatus : +1 volume de la musique, +2 volume des bruitages (0 a 4), +5 vitesse des messages de combat)."""
        ad = self.core.export('_ZN6status8g_OptionE')
        return (ad if ad else self.L + 0x25b564) + decalage

    def options_jeu(self):
        """(volume musique, volume bruitages, vitesse des messages de combat) des options du jeu (fenetre Parametres, enregistrees dans la sauvegarde)."""
        c = self.core
        return c.mem(self._option(1), 1)[0], c.mem(self._option(2), 1)[0], c.mem(self._option(5), 1)[0]

    def imposer_defilement(self, code):
        """Defilement des messages de combat impose a chaque image (code 0 a 3 : attente de 12 / 22 / 32 / 42 images, 4 : a la main) ; None : on rend la valeur du jeu (celle de la sauvegarde, ou choisie dans ses Parametres)."""
        if code is None:
            if self.defilement is not None and self._defil_origine is not None: self.core.mem_w(self._option(5), bytes([self._defil_origine]))
            self.defilement = None; self._defil_origine = None
        else:
            if self.defilement is None: self._defil_origine = self.options_jeu()[2]
            self.defilement = int(code) & 0xff; self.core.mem_w(self._option(5), bytes([self.defilement]))

    def ecrire_defilement(self):
        """Avant chaque image du moteur : la valeur imposee est ecrite ; si le jeu en avait mis une autre (chargement d'une sauvegarde ou d'un etat, fenetre Parametres), c'est elle qu'on rendra."""
        if self.defilement is None: return
        ad = self._option(5); cur = self.core.mem(ad, 1)[0]
        if cur != self.defilement: self._defil_origine = cur
        self.core.mem_w(ad, bytes([self.defilement]))

    def etat_message(self):
        """(test) (message ouvert, etat de ui_MsgLoop, lettre courante, fin de ligne, vitesse du type de fenetre)."""
        c = self.core; g = lambda off: struct.unpack('<H', c.mem(self.L + off, 2))[0]
        return c.mem(self.L + MSG_ACTIF, 1)[0], g(MSG_ETAT), g(MSG_COURANT), g(MSG_FIN), g(MSG_VITESSE)

    def reappliquer_correctifs(self):
        """Remet les correctifs que la visionneuse pose dans la memoire du moteur (fenetre des lieux elargie, pas de « Sauv. cloud », bouton « Paramètres », vitesses de marche d'origine). Appelee apres le chargement d'un etat
        (etats.appliquer) : l'image d'origine de la bibliotheque est rechargee d'abord, et un etat enregistre par une version qui n'avait pas encore un correctif ne le contient pas. Chacun est idempotent."""
        self._elargir_symboles()
        self.core.mem_w(self.L + G_IS_AMAZON, b'\x01')
        self.remettre_vitesses()
        self.patcher_parametres()
        self.retour_titre_etat = None            # un etat charge pendant la boite du retour au titre : la boite n'existe plus (memoire du moteur remplacee)

    def _elargir_symboles(self):
        """FieldData::drawSymbol ne montre les lieux de la carte du monde (villes, grottes...) que dans la fenetre de l'ecran portrait d'origine autour du heros
        (x de -192 a +448, y de -192 a +788 pixels, plus une marge) : en 16/9 les lieux des cotes n'apparaissaient qu'une fois tout pres. Les trois constantes de
        la fonction (add w22/w23/w24, w9, #imm) sont portees a 1600 pixels : la fenetre couvre tout ce que la visionneuse peut montrer, meme dezoomee."""
        c = self.core
        try:
            a = c.export('_ZN9FieldData10drawSymbolEv')
            for dec, imm in ((0x44, 0xc0), (0x48, 0x1c0), (0x4c, 0x314)):
                w = struct.unpack('<I', c.mem(a + dec, 4))[0]
                if w & 0xffc003e0 != 0x11000120 or (w >> 10) & 0xfff != imm: return        # autre version du moteur : on ne touche a rien
            for dec in (0x44, 0x48, 0x4c):
                w = struct.unpack('<I', c.mem(a + dec, 4))[0]
                c.mem_w(a + dec, struct.pack('<I', (w & ~(0xfff << 10)) | (1600 << 10)))
        except Exception as ex:
            print('fenetre des lieux non elargie :', ex, flush=True)

    # TownMenu_OPERATION_ROOT::menuUpdate (liste du menu Divers) : « cmp w8, #7 » (0x16ef28) suivi de « b.ne » vers la sortie « bouton inconnu » ; le bouton 7 (« Paramètres ») ferme le menu et ouvre TownMenu_OPERATION_SETTING
    CMP_PARAMETRES = 0x16ef28

    def patcher_parametres(self):
        """Le bouton « Paramètres » du menu Divers ouvre le menu Pause de la visionneuse, pas les reglages d'origine du jeu (volumes, vitesse, taille de la croix, retour au titre) : la comparaison du numero du bouton choisi a 7
        est portee a 4095 (jamais egale : le moteur traite l'appui comme celui d'un bouton inconnu, ne ferme pas le menu Divers et n'entre pas dans l'etat « Parametres »). Sans effet si c'est deja fait ou si le moteur est une autre
        version. Rappelee apres le chargement d'un etat (etats.appliquer remet l'image d'origine de la bibliotheque)."""
        c = self.core; ad = c.LIB_BASE + self.CMP_PARAMETRES; w = struct.unpack('<I', c.mem(ad, 4))[0]
        if w == 0x71001d1f: c.mem_w(ad, struct.pack('<I', (w & ~(0xfff << 10)) | (0xfff << 10)))       # « cmp w8, #7 » -> « cmp w8, #4095 »

    def _detourner_parametres(self):
        """Patch du bouton « Paramètres » (patcher_parametres) et crochet sur la comparaison : il leve `demande_pause` quand le bouton choisi est le 7 ; la visionneuse n'a plus qu'a ouvrir son menu Pause (Jeu.tick)."""
        c = self.core
        try:
            self.patcher_parametres(); ad = c.LIB_BASE + self.CMP_PARAMETRES
            def _p(uc, a, sz, u):
                if uc.reg_read(c.XREG[8]) & 0xffffffff == 7: self.demande_pause = True
            c.uc.hook_add(unicorn.UC_HOOK_CODE, _p, None, ad, ad)
        except Exception as ex:
            print('bouton Paramètres non detourne :', ex, flush=True)

    def _creer_canevas(self):
        c = self.core
        # canevas de texte des messages : Unity le cree par un message de port (largeur, hauteur) ; on appelle directement le gestionnaire
        self.obj_msg = self.L + OBJ_MESSAGE
        shorts = [0]
        for v in (1, 0, CANEVAS_L, CANEVAS_H, 0): shorts += [v & 0xffff, (v >> 16) & 0xffff]
        pm = c.malloc(64); c.mem_w(pm, struct.pack('<%dH' % len(shorts), *shorts))
        c.call(self.E('_ZN9SDrawCTRL11CanvasSetupEPvPKs'), self.obj_msg, pm, label='CanvasSetup')

    def _global(self):
        return struct.unpack('<Q', self.core.mem(self.L + GLOBAL_PTR, 8))[0]

    def demarrer_champ(self):
        """(essai) force le passage a la carte du monde : Global::startField()."""
        self.core.call(self.E('_ZN6Global10startFieldEv'), self._global(), label='startField')

    def retour_titre(self):
        """Retour a l'ecran-titre : la fin du bouton « Revenir à l'écran titre » des Parametres d'origine du jeu quand on repond « Oui » (TownMenu_OPERATION_SETTING::menuUpdate, etat 5) : efface la banque 4
        (sauvegarde automatique, killbank), ferme la boite, verrouille le joueur, puis Global::startTitle() (fondu au noir de 30 images lance par UnitySetFade(0x101e), chapitre 0, la partie suivante est le titre). A
        appeler PENDANT un pas (voir _retour_titre_apres) : le paquet du fondu doit etre lu avec ceux du pas, sinon le fondu est perdu (le tampon est remis a zero au pas suivant) et l'ecran passe au noir d'un coup."""
        c = self.core
        c.call(self.E('_ZN7profile8SaveLoad8killbankEib'), 4, 0, label='killbank')
        self._fermer_boite_titre()
        c.call(self.E('_ZN3cmn11GameManager12getSingletonEv'), label='getSingleton')
        c.call(self.E('_ZN3cmn13PlayerManager7setLockEb'), 1, label='setLock')
        c.call(self.E('_ZN6Global10startTitleEv'), self._global(), label='startTitle')

    def demander_retour_titre(self):
        """Menu Pause > « Revenir à l'écran titre » : ouvre la boite du jeu (son texte, Oui / Non) au prochain pas, comme le bouton des Parametres d'origine. -> faux si une demande est deja en cours.
        « Non » ferme la boite et rend la main au joueur ; « Oui » lance retour_titre, avec le fondu du jeu. Les deux suites sont jouees par `_retour_titre_apres`, apres chaque GameUpdate.
        Seulement en ville et sur la carte du monde, les deux parties ou le menu des Parametres d'origine existe et ou la boite repond (essai : en combat, la boite s'ouvre mais ne recoit ni les touches ni
        les clics, le menu de commandes du combat garde la main ; non verifie dans les boutiques et les jeux du casino)."""
        if self.retour_titre_etat is not None or self.etat.partie not in (PARTIE_VILLE, PARTIE_CHAMP): return False
        self.retour_titre_etat = 'ouvrir'; return True

    def _boite_titre(self): return self.core.export('gTownMenu_MESSAGE')

    def _fermer_boite_titre(self):
        c = self.core; m = self._boite_titre()
        if m and c.call(self.E('_ZN8MenuBase6isOpenEv'), m, label='isOpen') & 1: c.call(self.E('_ZN8MenuBase5closeEv'), m, label='close')

    def _retour_titre_avant(self):
        """Avant GameUpdate : ouvre la boite. Meme suite d'appels que l'etat 5 du menu des Parametres d'origine (menuUpdate + 0x1ac) : openMessageForMENU, addMessage(0xCBA2F), setYesNo() (curseur sur « Oui »),
        setYesNoSuperCancel(false) ; le joueur est verrouille comme dans le menu du jeu (PlayerManager::setLock(true), rendu par « Non »)."""
        if self.retour_titre_etat != 'ouvrir': return
        c = self.core; m = self._boite_titre(); self.retour_titre_etat = 'dialogue'
        c.call(self.E('_ZN3cmn11GameManager12getSingletonEv'), label='getSingleton')
        c.call(self.E('_ZN3cmn13PlayerManager7setLockEb'), 1, label='setLock')
        c.call(self.E('_ZN16TownMenu_MESSAGE18openMessageForMENUEv'), m, label='openMessageForMENU')
        c.call(self.E('_ZN16TownMenu_MESSAGE10addMessageEi'), m, MSG_RETOUR_TITRE, label='addMessage')
        c.call(self.E('_ZN16TownMenu_MESSAGE8setYesNoEv'), m, label='setYesNo')
        c.call(self.E('_ZN16TownMenu_MESSAGE19setYesNoSuperCancelEb'), m, 0, label='setYesNoSuperCancel')
        c.mem_w(m + MESSAGE_RESULTAT, bytes(4))                # la reponse d'une boite precedente ne compte pas (MenuBase::menuBaseSetup la remet a 0 quand le menu est ajoute ; ici il peut deja l'etre : message d'un PNJ en cours)

    def _retour_titre_apres(self):
        """Apres GameUpdate, avant la lecture des paquets : la reponse de la boite (TownMenu_MESSAGE + 0x10, comme le fait menuUpdate du menu des Parametres d'origine). 2 = Non : on ferme la boite et on
        rend la main (setLock(false), l'inverse de l'ouverture). 1 = Oui : retour_titre, dans ce pas, donc avec son fondu."""
        if self.retour_titre_etat != 'dialogue': return
        c = self.core; r = struct.unpack('<I', c.mem(self._boite_titre() + MESSAGE_RESULTAT, 4))[0]
        if r == 2:
            self.retour_titre_etat = None; self._fermer_boite_titre()
            c.call(self.E('_ZN3cmn11GameManager12getSingletonEv'), label='getSingleton')
            c.call(self.E('_ZN3cmn13PlayerManager7setLockEb'), 0, label='setLock')
        elif r == 1:
            self.retour_titre_etat = None; self.retour_titre()
        elif not c.call(self.E('_ZN8MenuBase6isOpenEv'), self._boite_titre(), label='isOpen') & 1:          # fermee sans reponse (la scene du moteur a repris la boite : un message de plus d'un script, par exemple) : la demande tombe, le joueur est libere
            self.retour_titre_etat = None
            c.call(self.E('_ZN3cmn11GameManager12getSingletonEv'), label='getSingleton')
            c.call(self.E('_ZN3cmn13PlayerManager7setLockEb'), 0, label='setLock')

    def demarrer_ville(self, nom):
        """(essai) charge une ville ou un donjon : Global::startTown(nom)."""
        self.core.call(self.E('_ZN6Global9startTownEPKc'), self._global(), self.core.cstr(nom.encode()), label='startTown')

    # vitesse de marche du heros (Fix32 par pas du moteur, valeurs d'origine de libdq4core) : villes (deux variables), carte du monde (Speed, plus les deux constantes locales 0x27520c et 0x275210 que
    # FieldPlayer::move lit en diagonale). La course accelere l'horloge du moteur (viewer, _boucle), pas ces valeurs ; on ne les remet a l'origine qu'au chargement d'un etat (voir remettre_vitesses)
    VITESSES_ORIGINE = (('_ZN16TownPlayerAction9walkSpeedE', 819), ('_ZN16TownPlayerAction10walkSpeed2E', 655), ('_ZN11FieldPlayer5SpeedE', 12288), (0x27520c, 8192), (0x275210, 8192))

    def remettre_vitesses(self):
        """Remet les vitesses de marche du heros a leurs valeurs d'origine : un etat enregistre par une ancienne version pendant une course les contient majorees (la course n'y touche plus)."""
        c = self.core
        for n, base in self.VITESSES_ORIGINE:
            ad = c.LIB_BASE + n if isinstance(n, int) else c.export(n)
            if ad: c.mem_w(ad, struct.pack('<i', base))

    def boutiques(self):
        """(indice courant, nombre) des boutiques de la liste de la carte d'une ville (TownImageMap::execute : deux statiques locales, 0x2750c4 et 0x2750c8 ; la liste est la fenetre de type 24)."""
        c = self.core; b = c.LIB_BASE
        return struct.unpack('<hh', c.mem(b + 0x2750c4, 2) + c.mem(b + 0x2750c8, 2))

    def camera_ville(self):
        """Camera des villes du moteur d'origine (TownCamera, objet statique) : (limite gauche, limite droite, verrou) ; limite = 0 : rotation libre, < 0 : rotation interdite, > 0 : angle borne (unites de 1 / 4096 de tour) ; verrou : camera verrouillee par un evenement."""
        c = self.core; ad = c.export('_ZN10TownCamera11m_singletonE')
        if ad is None: return 0, 0, False
        lg, ld = struct.unpack('<ii', c.mem(ad + 0x34, 8)); return lg, ld, bool(c.mem(ad + 0x3e, 1)[0])

    def camera_jeu(self):
        """Etat de la TownCamera du moteur (objet statique), pour savoir si le jeu pilote la camera : (verrou +0x3e, mode de cible +0x48, verrou de point de vue +0x40, deplacement en cours +0x43)."""
        c = self.core; ad = c.export('_ZN10TownCamera11m_singletonE')
        if ad is None: return 0, 0, 0, 0
        b = c.mem(ad + 0x3e, 6); return b[0], struct.unpack('<i', c.mem(ad + 0x48, 4))[0], b[2], b[5]

    def taille_croix(self):
        """Option « Taille de la croix » du jeu (g_pad_size) : 0 Grande, 1 Moyenne (par defaut), 2 Petite."""
        v = self.core.mem(self.core.LIB_BASE + 0x24a779, 1)[0]
        return v if v in (0, 1, 2) else 1

    def drapeaux(self):
        """Global.Flag : premier mot de la sortie du moteur (bit 3 : manette tactile presente ; 4 verrou du joueur, 0x20 carte autorisee, 0x40 interface verrouillee...)."""
        return struct.unpack('<I', self.core.mem(self.core.outp, 4))[0]

    def _drapeau_effet(self, actif):
        """Bit 1 de Global+0xd8 : Unity (Capture.ScreenEffect) le leve au debut d'un effet d'ecran et l'abaisse a la fin ; le moteur attend qu'il retombe."""
        ad = self.core.outp; v = struct.unpack('<I', self.core.mem(ad, 4))[0]
        self.core.mem_w(ad, struct.pack('<I', (v | 2) if actif else (v & ~2)))

    def _debut_effet_combat(self, avant):
        """Paquet 34 (valeur 4) : l'ecran se brise en morceaux (EFFET_COMBAT_IMAGES images) pendant que le moteur attend ; ensuite l'ecran reste noir jusqu'au chargement de la scene du combat."""
        if self.etat.effet is not None: return
        self.etat.effet = {'n': 0, 'duree': PJ.duree_fondu(EFFET_COMBAT_IMAGES, Etat.vitesse_fondu)}; self._drapeau_effet(True)      # la cascade suit « Vitesse de transition » comme les fondus : 57 images a x1, 57 / facteur ensuite (la simulation avance de 57 images au total, voir Jeu._dessiner_effet)
        if self.etat.attente_charge is None: self.etat.attente_charge = {'base': avant, 'n': 0}

    def _effet_combat(self):
        """Une image du jeu : avance l'effet de debut de combat, abaisse le drapeau a la fin (le moteur reprend a l'image suivante) ; compte l'attente du chargement."""
        ef = self.etat.effet
        if ef is not None:
            ef['n'] += 1
            if ef['n'] >= ef.get('duree', EFFET_COMBAT_IMAGES): self._drapeau_effet(False); self.etat.effet = None
        ac = self.etat.attente_charge
        if ac is not None:
            ac['n'] += 1
            if ac['n'] > ATTENTE_CHARGE_MAX + EFFET_COMBAT_IMAGES: self.etat.attente_charge = None

    def _nom_carte(self):
        s = self.core.read_cstr(self.L + NOM_RESSOURCE).decode('latin-1')
        return s.split('/')[-1]

    def step(self, tenu=0, decl=None):
        """Une image du jeu. tenu = touches maintenues (marche) ; decl = touches qui viennent d'etre pressees (boutons, menus).
        Les fondus d ecran sont rejoues dans Etat (tick_fondu). -> liste de paquets"""
        if decl is None: decl = tenu
        c = self.core
        w = struct.unpack('<I', c.mem(c.outp, 4))[0]            # bit 0 : « un fondu est en cours » (Fade.FadePlane.CheckFade : images restantes > 0). Le moteur le leve lui-meme en lancant un fondu (UnitySetFade) puis attend qu'il retombe
        w2 = (w | 1) if self.etat.fondu_en_cours() else (w & ~1)      # (Global::IsFadeEnd : auberge, titres de chapitre, ecran de chargement, ouverture des menus, sifflet...)
        if w2 != w: c.mem_w(c.outp, struct.pack('<I', w2))
        self._finir_anims()
        self._effet_combat()
        if os.environ.get('DQ_CALLHOP'):                                       # (test) "image:monstre:hauteur:degats,..." : appelle BattleMenu_setHoppingNumbers comme le moteur apres un coup
            for spec in os.environ['DQ_CALLHOP'].split(','):
                im, ch, hh, nn = [int(x) for x in spec.split(':')]
                if self.images == im: self.ui.image = self.images; c.call(self.E('_Z27BattleMenu_setHoppingNumbersss'), ch, hh, nn, label='hop')
        self.pk.begin()
        if self.defilement is not None: self.ecrire_defilement()
        self._retour_titre_avant()
        r = c.call(self.E('GameUpdate'), tenu, decl, label='GameUpdate')
        self._retour_titre_apres()
        if MSGDBG: self._journal_message()
        if r is None: raise RuntimeError('le moteur s est arrete :\n' + '\n'.join(self.log.lignes[-12:]))
        pq = self.pk.packets()
        if os.environ.get('DQ_PKT') and self.etat.partie == PARTIE_COMBAT:       # (test) journal des paquets de combat : image, [(type, ints...)]
            with open(os.environ['DQ_PKT'], 'a') as fj:
                fj.write('%d %s\n' % (self.images, [(t, a[:2]) if t != 22 else (22, a[0], a[1], [round(x, 2) for x in f[:3]], [round(min(f[3 + 5 * i + 2] for i in range(a[1])), 2), round(max(f[3 + 5 * i + 2] for i in range(a[1])), 2), round(min(f[3 + 5 * i + 3] for i in range(a[1])), 2), round(max(f[3 + 5 * i + 3] for i in range(a[1])), 2)]) for t, a, f in pq if t not in (12, 13, 14)]))
        if os.environ.get('DQ_PKTALL'):       # (test temporaire) tous les paquets sauf 22/28/29
            with open(os.environ['DQ_PKTALL'], 'a') as fj:
                for t, a, f in pq:
                    if t not in (22, 28, 29): fj.write('%d p=%#x %d %s %s\n' % (self.images, self.etat.partie, t, a[:6], [round(x, 3) for x in f[:6]]))
        self.ui.image = self.images
        self._consommer_messages()
        for p in pq:
            if p[0] == 5 and p[1]:
                d = self.duree_anim(p[1][0] & 0xffff, (p[1][0] >> 16) & 0xffff) if self.duree_anim else None
                self.anims.append((self.images + (d or DUREE_ANIM), p[1][0] & 0xffff))
        avant = self.etat.cartes_chargees
        self.etat.image = self.images
        self.etat.appliquer(pq, self._nom_carte)
        self._decompte_sortie()
        for t, a, f in pq:
            if t == 34 and a and (a[0] & 0xf) == EFFET_COMBAT: self._debut_effet_combat(avant)
        ac = self.etat.attente_charge
        if ac is not None and self.etat.effet is None and self.etat.cartes_chargees > ac['base']: self.etat.attente_charge = None      # la scene du combat est arrivee
        self.etat.maj_chargement()
        self.etat.tick_fondu(); self.etat.tick_transition()
        prec = self.etat.partie
        self.etat.partie = struct.unpack('<H', c.mem(self._global() + 0xee, 2))[0]
        if prec == PARTIE_COMBAT and self.etat.partie != PARTIE_COMBAT: self.etat.fen_retour = FENETRE_RETOUR_COMBAT      # fin du combat : le fondu d'entree qui suit sur la carte est celui du retour (duree du jeu)
        if self.etat.partie == PARTIE_COMBAT and prec != PARTIE_COMBAT and self.etat.attente_charge is None and self.etat.cartes_chargees <= avant:
            self.etat.attente_charge = {'base': avant, 'n': 0}      # combat sans effet d'ecran (scenario...) : la scene d'avant ne doit pas apparaitre avant le chargement de celle du combat
        if self.etat.partie != PARTIE_CHAMP: self.etat.champ = None; self.etat.monde = None
        else: self._lire_monde()
        self.images += 1
        return pq

    def _decompte_sortie(self):
        """Bruitage de transition de carte (porte, sortie, entree de village, escalier, carte du monde <-> ville) : cause de sa perte avec les fondus raccourcis (« Vitesse de transition » x3 et plus, marginal a x2).
        Quand le jeu quitte une ville ou la carte du monde, il lance un fondu au noir de 30 images ET arme un decompte de 15 images (DECOMPTE_SORTIE) ; a 0, NativeExec appelle playTownExitSE / playFieldExitSE, qui ne jouent le
        bruitage 305 que si l'ancienne scene vit encore. Dans le jeu d'origine, le chargement de la carte suivante n'arrive qu'a la fin du fondu (30 images) : le bruitage est demande a mi-fondu. Le fondu raccourci de la
        visionneuse (Etat._fondu) amene le chargement avant les 15 images : l'ancienne scene est detruite, le moteur ne demande plus rien (aucun paquet 35). On remet donc le decompte a la meme proportion que le fondu
        (duree jouee / duree d'origine) : le bruitage reste demande a mi-fondu, la duree du fondu et celle du bruitage ne changent pas. Sans fondu raccourci (rapport 1), rien n'est touche."""
        c = self.core; b = c.mem(self.L + DECOMPTE_SORTIE, 1)[0]
        if b > self._decompte: self._decompte_arme = self.images; self._decompte_fait = False       # armé pendant ce pas (le moteur l'a deja decremente une fois)
        self._decompte = b
        if self._decompte_fait or b == 0 or b > 15: return
        im, r = self.etat.rapport_fondu
        if self.images - self._decompte_arme > 2: self._decompte_fait = True; return
        if im < self._decompte_arme - 2 or im > self.images: return           # le fondu de cette sortie n'est pas (encore) arrive
        self._decompte_fait = True
        if r < 1.0:
            nb = max(1, int(round(b * r))); c.mem_w(self.L + DECOMPTE_SORTIE, bytes([nb])); self._decompte = nb

    def _journal_message(self):
        """(test, DQ_MSGDBG=1) une ligne a chaque changement d'etat du message : image du moteur, etat, lettres ecrites / lettres de la ligne, vitesse du type de fenetre."""
        o = self.options_jeu()
        if o != getattr(self, '_opt_vu', None): self._opt_vu = o; print('MSGDBG image %d options du jeu : volume musique %d, volume bruitages %d, vitesse des messages de combat %d (impose : %s)' % ((self.images,) + o + (self.defilement,)), flush=True)
        e = self.etat_message()
        if (e[0], e[1], e[4]) != getattr(self, '_msg_vu', None) or (e[1] == 2 and e[2] == e[3]):
            self._msg_vu = (e[0], e[1], e[4]); print('MSGDBG image %d actif %d etat %d lettres %d/%d vitesse %d combat=%d' % ((self.images,) + e + (self.etat.partie == PARTIE_COMBAT,)), flush=True)

    def _lire_monde(self):
        """Carte du monde entiere (FieldData : grille CWorldMap +0x188 de 256 x 256 numeros de bloc, table des blocs +0x180 de 6 octets,
        decalages d'animation de l'eau aux adresses 0x275830/34/38). Meme regle que FieldData::drawBlock (verifiee : 1300 tuiles sur 1300).
        Le moteur n'envoie que 25 colonnes autour du heros ; ici on peut dessiner autour de lui autant qu'on veut."""
        c, fd = self.core, self.fielddata
        if not fd: return
        try:
            if self._grille is None or self.images - self._grille_img >= 30:
                gp, = struct.unpack('<Q', c.mem(fd + 0x188, 8)); l, h = struct.unpack('<ii', c.mem(fd + 0x198, 8))
                if not gp or not (0 < l <= 1024 and 0 < h <= 1024): return
                self._grille = np.frombuffer(c.mem(gp, l * h * 2), '<u2').reshape(h, l).astype(np.int32); self._grille_img = self.images
            tbl, = struct.unpack('<Q', c.mem(fd + 0x180, 8))
            ch = np.frombuffer(c.mem(tbl, 1024 * 6), np.uint8).reshape(1024, 6)
            b0, b1, b2 = (struct.unpack('<h', c.mem(self.L + a, 2))[0] for a in (0x275830, 0x275834, 0x275838))
            t = ch[:, 1]; s2 = np.ascontiguousarray(ch[:, 2:4]).view('<i2').ravel().astype(np.int32); s4 = np.ascontiguousarray(ch[:, 4:6]).view('<i2').ravel().astype(np.int32)
            tuile = np.where(t == 0, s4 + b0, np.where(t == 0x18, s2 + b2, np.where(t == 8, s2 + b1, s2)))
            h, l = self._grille.shape
            self.etat.monde = {'ids': tuile[(self._grille - 1) & 0x3ff], 'l': l, 'h': h}
        except Exception:
            self.etat.monde = None

    def lire_canevas(self):
        """Bitmap du texte du message (hauteur x largeur, 0-255 = opacite), ou None si le canevas n'existe pas encore."""
        c = self.core
        buf = struct.unpack('<Q', c.mem(self.obj_msg + 0x10, 8))[0]
        if not buf: return None
        import numpy as np
        return np.frombuffer(c.mem(buf, CANEVAS_L * CANEVAS_H), np.uint8).reshape(CANEVAS_H, CANEVAS_L)

    def _consommer_messages(self):
        """Fait ce que ferait l'interface Unity : lit les messages que le moteur a poses pour chaque port (menus, fenetres...)
        puis vide la file. Sans cela la file grossit sans fin et finit par ecraser la memoire voisine."""
        c = self.core
        b2 = self.buf2
        a = struct.unpack('<%dh' % PILE_SHORTS, c.mem(b2, 2 * PILE_SHORTS))
        out = []
        for port in range(32):
            idx = a[port] & 0xffff; garde = 0
            while 0 < idx < PILE_SHORTS - 2 and garde < 600:
                n = a[idx]
                if n < 0 or idx + n + 1 >= PILE_SHORTS: break
                out.append((port, a[idx + 1: idx + 1 + n]))
                idx = a[idx + 1 + n] & 0xffff; garde += 1
        self.msgs_ui = out
        self.ui.appliquer(out)
        c.mem_w(b2, b'\0' * 128 + struct.pack('<h', 65))              # tetes/queues a 0, pointeur libre = 65

    def menu_actif(self):
        """Port de la fenetre de menu qui attend les touches (active et acceptant la saisie), ou None."""
        c = self.core; L = self.L
        u = lambda a, n, sg=False: int.from_bytes(c.mem(a, n), 'little', signed=sg)
        base = u(L + 0x252098, 8); cnt = u(L + 0x252094, 2, True)
        if not base: return None
        cand = []
        for i in range(1, cnt):
            e = base + 0x20 * i
            port = u(e + 0x28, 2, True); this = u(e + 0x30, 8)
            if this and u(e + 0x38, 8) and port > 1 and u(this + 8, 1) == 1 and u(this + 0x50, 2):
                f = self.ui.f.get(port)
                if f and f['vis'] and f['cases']: cand.append((f['ordre'], port))
        if not cand:                                 # sinon : menu dont le moteur demande la saisie (commande 6 a chaque image), meme sous un message : Oui / Non d'une question
            cand = [(self.ui.f[p]['ordre'], p) for p in self.menus_saisie()]
        return max(cand)[1] if cand else None

    def menus_saisie(self):
        """Tous les ports de menu dont le moteur demande la saisie (le toucher agit sur chacun d'eux) : le plus recent d'abord."""
        return sorted((p for p, f in self.ui.f.items() if p > 1 and f.get('entree') and f['vis'] and f['cases']), key=lambda p: -self.ui.f[p]['ordre'])

    def envoyer_menu(self, port, *args):
        """Ce que fait Unity : depose un message [n, args...] dans la file moteur<-interface du port (touches/pointeur des menus)."""
        if os.environ.get('DQ_MENUDBG'): print('ENVOI image %d port %d %s' % (self.images, port, list(args)), flush=True)         # (test) messages interface -> moteur
        c = self.core
        a = list(struct.unpack('<%dh' % PILE_SHORTS, c.mem(self.buf1, 2 * PILE_SHORTS)))
        n = len(args); idx = a[64] or 65
        a[idx] = n
        for i, v in enumerate(args): a[idx + 1 + i] = v
        a[idx + n + 1] = 0
        if a[port]: a[a[32 + port]] = idx
        else: a[port] = idx
        a[32 + port] = idx + n + 1
        a[64] = idx + n + 2
        c.mem_w(self.buf1, struct.pack('<%dh' % PILE_SHORTS, *a))

    def params_message(self):
        """(nombre de lignes visibles - 1, hauteur d'une ligne, defilement) du canevas de message, tels que le moteur les tient."""
        c = self.core; i16 = lambda ad: struct.unpack('<h', c.mem(ad, 2))[0]
        return i16(self.L + 0x2523a0), i16(self.obj_msg + 0x42), i16(self.obj_msg + 0x4a)

    def lire_message(self):
        """Partie du canevas actuellement visible dans la fenetre de message : n lignes a partir du defilement courant.
        -> tableau (hauteur x largeur) de 0-255, ou None."""
        a = self.lire_canevas()
        if a is None: return None
        c = self.core
        i16 = lambda ad: struct.unpack('<h', c.mem(ad, 2))[0]
        lignes = i16(self.L + 0x2523a0) + 1            # nombre de lignes visibles de la fenetre (reglage du moteur)
        lh = i16(self.obj_msg + 0x42)                  # hauteur d'une ligne (pixels du canevas)
        defil = i16(self.obj_msg + 0x4a)               # defilement courant (le moteur l'anime de 8 pixels par image)
        if not (1 <= lignes <= 8 and 8 <= lh <= 64): lignes, lh, defil = 4, 28, -3
        h = lignes * lh; top = max(0, defil + 3)
        sub = a[top:top + h]
        if len(sub) < h:
            import numpy as np
            sub = np.vstack([sub, np.zeros((h - len(sub), a.shape[1]), np.uint8)])
        return sub

    def _finir_anims(self):
        c = self.core
        due = [a for a in self.anims if a[0] <= self.images]
        if not due: return
        self.anims = [a for a in self.anims if a[0] > self.images]
        table = struct.unpack('<Q', c.mem(self.fldobj + 8, 8))[0]
        for _, idx in due:
            ad = table + idx * 32 + 0x14
            c.mem_w(ad, bytes([c.mem(ad, 1)[0] & ~1]))

    def statut_catalogue(self):
        """Masque de `getCatalogStatus` : bits 0-4 = banque valide, 5-9 = illisible, 10-14 = corrompue, 15 = un fichier manque."""
        return int(self.core.call(self.E('_ZN7profile8SaveLoad16getCatalogStatusEv'), label='getCatalogStatus')) & 0xffff

    def relire_journaux(self):
        """Apres un import de sauvegardes : le moteur ne releve les fichiers data1..5 / data9 qu'a la creation du menu de depart ; on lui refait relever le catalogue (noms, chapitres, durees des listes). -> nouveau masque de statut."""
        for nom in ('getCatalogView', 'getCatalogRecent'):
            self.core.call(self.E('_ZN7profile8SaveLoad%d%sEv' % (len(nom), nom)), label=nom)
        return self.statut_catalogue()

    @staticmethod
    def etat_boutons_depart(statut):
        """Ce que le moteur fixe a la creation du menu de depart (`updateActiveDiary`) : (une banque 0-2 contient des donnees, la banque 3 est valide, la banque 4 est valide) -> boutons grises ou absents."""
        return (bool(statut & 0x0007 or statut & 0x00e0 or statut & 0x1c00), bool(statut & 0x0008), bool(statut & 0x0010))

    def charger_sauvegarde(self, numero):
        """numero 1..5 -> lit data<numero>.dat ; le moteur relance la ville sauvegardee"""
        r = self.core.call(self.E('_ZN7profile8SaveLoad8loadbankEi'), numero - 1, label='loadbank')
        return bool(r)
