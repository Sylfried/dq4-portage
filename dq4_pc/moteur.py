"""Le moteur du jeu (libdq4core.so, ARM64) execute dans un emulateur + decodage de ce qu'il demande a Unity."""
import os, re, struct, zipfile, unicorn
import numpy as np
import emu_core as T
from pktlog import PacketLog

CUR_I, CUR_F = 0x258278, 0x258280          # curseurs d'ecriture (entiers / flottants) dans la bibliotheque
PARTIE_DEPART = 0x3                         # menu de depart (GameStartPart : liste des journaux, creation, suppression, licence)
PARTIE_VILLE = 0xc                         # ville, donjon, tour (decor 3D)
PARTIE_COMBAT = 0xd
PARTIE_CHAMP = 0xe                         # FieldPart : carte du monde
MSGDBG = bool(os.environ.get('DQ_MSGDBG'))     # (test) journal des etats du message du moteur
GLOBAL_PTR = 0x23d438                       # singleton Global
NOM_RESSOURCE = 0x258290                    # nom de la ressource carte demandee a Unity (ex. m/ma/in/mak1f1)
ECRAN_ETAT = 0xd8                           # Global+0xd8 : copie, a chaque GameUpdate, du premier entier du tampon de sortie (mot d'etat partage avec Unity) ; son bit 1 = « effet d'ecran en cours » (Global::IsScreenEffectEnd attend qu'il retombe)
G_IS_AMAZON = 0x24f684                      # octet g_isAmazon du moteur : a 1, la case « Sauv. cloud » du menu de depart n'existe pas
EFFET_COMBAT = 4                            # paquet 34 (cmd_screen_effect) : valeur & 0xf = 4, Capture.BattleEffect (les morceaux de l'ecran tombent)
EFFET_COMBAT_IMAGES = 57                    # Capture.BattleEffect : le compteur va de 0 a divY (56) inclus, une image du jeu chacun
ATTENTE_CHARGE_MAX = 240                    # images (30 Hz) d'ecran noir avant de renoncer a attendre le chargement de la scene de combat
LIB_APK = 'lib/arm64-v8a/libdq4core.so'

# touches (masque envoye a GameUpdate) : haut, bas, gauche, droite verifies ; A/B a confirmer
HAUT, BAS, GAUCHE, DROITE, A, B = 0x1, 0x2, 0x4, 0x8, 0x10, 0x20
OBJ_MESSAGE = 0x252330                     # objet SDrawCTRL (canevas de texte des messages) dans la bibliotheque
CANEVAS_L, CANEVAS_H = 512, 512            # texture du canevas de message d'Unity (MenuMessage : Texture2D(512, 512)) ; le moteur y ecrit en boucle
PILE_SHORTS = 4096                         # taille reelle allouee pour la file des messages (Unity en annonce 1089)
MSG_ACTIF, MSG_ETAT, MSG_COURANT, MSG_FIN, MSG_VITESSE = 0x25238e, 0x25238c, 0x2523cc, 0x2523ce, 0x2523b0      # ui_MsgLoop : message ouvert (octet), etat (1 lecture d'un code, 2 ecriture des lettres, 3 / 5 attente d'une touche), indice de la lettre courante et de la fin de ligne, lettres par image / 4 du type de fenetre
UI_MSGLOOP_ECRITURE = 0x128                # ui_MsgLoop + 0x128 : `sxth w20, w8` apres `lsl w8, w8, #2` (etat 2 : nombre de lettres ecrites a cette image)
SXTH_W20_W8 = 0x13003d14
COMBAT_MANUEL = 4                          # OptionStatus.battleSpeed : 0 a 3 = attente de 12 / 22 / 32 / 42 images entre deux messages de combat (BattleAutoFeed::setMessageSpeed), 4 = pas d'avance automatique
DUREE_ANIM = 18                            # images (30 Hz) avant de dire au moteur qu'une animation d'objet (porte...) est finie


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
        self.sprites = {}; self.cartes_chargees = 0; self.objets_cmd = []; self.fond = (0.0, 0.0, 0.0)       # objets_cmd : ordres sur les objets de la carte (paquets 2 a 5 et 7), vides par la fenetre : (genre, objet, valeurs...)
        self.partie = 0; self.champ = None        # partie du jeu (0xc ville, 0xe carte du monde) ; carte du monde : tuiles a afficher
        self.maillages_vus = set()                # combat : emplacements dont le maillage (paquet 22) est arrive a CETTE image : Unity dessine en mode immediat, pas de paquet = rien a l'ecran (clignotement d'un coup recu, monstre vaincu)
        self.fondu = self._plan_fondu(); self.fondu_fond = self._plan_fondu()      # Fade.FadePlane : opacite courante, opacite visee, pas par image, images restantes, couleur, images passees tout noir. DEUX plans (Fade.l_fade, bit 14 de l'entier du paquet 9 = Fade.l_targetLayer) : 0 = « FadeForMenu » (shader Custom/FrontFade, file Overlay : devant tout, fenetres et messages compris) ; 1 = « FadeForBG » (Custom/BackFade, file Background : devant la scene, derriere les fenetres)
        self.sons = []; self.musique = None       # paquets 35/36/37 : ordres de son en attente (type, valeur), vides par la fenetre a chaque image ; musique demandee en dernier (None = arret)
        self.effet = None                         # effet d'ecran de debut de combat en cours : {'n': images ecoulees} (le moteur attend sa fin, voir Moteur._effet_combat)
        self.attente_charge = None                # {'base': nombre de chargements de scene deja vus, 'n': images attendues} : ecran noir tant que la scene du combat n'est pas arrivee
        self.monde = None                         # carte du monde entiere lue dans le moteur : {'ids': tuiles (H x L) apres animation, 'l', 'h'} ; None hors de la carte du monde
        self.fbx = {}; self.image = 0             # modeles 3D animes (paquets 31 / 32 : le dragon du titre) : emplacement -> {'id', 'vis', 'pos', 'rot', 'scl', 'col', 'anim': [(image du moteur, numero de sequence, force)]} ; image : numero du pas du moteur en cours (rempli par Moteur.step)

    @staticmethod
    def _plan_fondu(): return {'a': 0.0, 'fin': 0.0, 'pas': 0.0, 'n': 0, 'col': (0.0, 0.0, 0.0), 'noir': 0}

    def __setstate__(self, d):                  # etats enregistres avant les deux plans de fondu
        self.__dict__.update(d); self.__dict__.setdefault('fondu_fond', self._plan_fondu()); self.__dict__.setdefault('fbx', {}); self.__dict__.setdefault('image', 0)

    def fondu_en_cours(self): return self.fondu['n'] >= 1 or self.fondu_fond['n'] >= 1      # Fade.FadePlane.CheckFade : images restantes > 0 sur l'un des deux plans

    def appliquer(self, paquets, lire_nom):
        self.maillages_vus = set()
        for t, a, f in paquets:
            if t == 0:
                self.carte = lire_nom(); self.cartes_chargees += 1; self.sprites.clear(); self.fond = (0.0, 0.0, 0.0); self.modeles.clear(); self.maillages.clear(); self.mesh_etat.clear(); self.objets_cmd = [('carte',)]; self.cam_rot = None; self.cam_fov = None; self.cam_near = None; self.cam_far = None; self.cam_yoff = None; self.cam_libre = False; self.symboles.clear(); self.icones.clear(); self.fbx.clear()
            elif t == 8 and len(f) >= 6:
                self.fond = tuple((f[i] + f[i + 3]) / 2 for i in range(3))     # couleur de fond (ciel) : deux teintes, on prend la moyenne
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
                if a[1] >= 0: self.sprites[a[0]] = {'id': a[1], 'pos': None, 'col': (1, 1, 1, 1), 'pose': 0, 'dir': 0, 'vis': True}
                else: self.sprites.pop(a[0], None)
            elif t == 14 and len(a) >= 2:           # cmd_chara_on_off : Chara.SetVisible(valeur != 0) = Renderer.enabled du personnage (et de son ombre)
                if a[0] in self.sprites: self.sprites[a[0]]['vis'] = a[1] != 0
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
                fl = list(f)
                if a[0] & 1 and len(fl) >= 3: self.cam_pos = tuple(fl[:3]); fl = fl[3:]
                if a[0] & 2 and len(fl) >= 3: self.cam_cible = tuple(fl[:3]); fl = fl[3:]
                if a[0] & 4 and len(fl) >= 3: self.cam_rot = tuple(fl[:3])        # combat : rotation (tangage, lacet, roulis) en degres
            elif t == 21 and len(a) >= 2:           # DSSAObject::send_unity_load(emplacement, id de modele) ; id < 0 = liberation
                if a[1] >= 0:
                    self.modeles[a[0]] = a[1]
                    self.mesh_etat[a[0]] = {'shader': 3 if a[1] > 999 else 1, 'vis': True, 'col': (1.0, 1.0, 1.0), 'off': (0.0, 0.0)}      # MeshChara..ctor : shader 1 (DssaMonster0) sauf id > 999 (DssaCharaTransparent) ; couleur blanche
                else: self.modeles.pop(a[0], None); self.maillages.pop(a[0], None); self.mesh_etat.pop(a[0], None)
            elif t == 31 and len(a) >= 2:           # cmd_fbx_load : emplacement, numero de modele (« fbx/c<numero> », FbxObject) ; < 0 = liberation. Le modele est cree cache, tourne de (0, 180, 0), echelle 1
                if a[1] >= 0: self.fbx[a[0]] = {'id': a[1], 'vis': False, 'pos': (0.0, 0.0, 0.0), 'rot': (0.0, 180.0, 0.0), 'scl': (1.0, 1.0, 1.0), 'col': (1.0, 1.0, 1.0, 1.0), 'anim': []}
                else: self.fbx.pop(a[0], None)
            elif t == 32 and a:                     # cmd_fbx : emplacement = v & 0xff ; bits 8-9 : visibilite (bit 8 = visible) ; 10 : forcer l'animation ; 11 : echelle (3 flottants) ; 12 : couleur (4) ; 13 : position (3) ; 14 : rotation, degres (3) ; 15 : animation (un entier : sequence)
                v = a[0]; m = self.fbx.get(v & 0xff); fl = list(f)
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
                if flags & 0x800: fl = fl[1:]
                if flags & 0x1000: s['col'] = tuple(fl[:4]); fl = fl[4:]
                if flags & 0x2000 or flags & 0x8000: s['pos'] = tuple(fl[:3]); fl = fl[3:]      # 0x8000 : meme position, version carte du monde (pixels)
                if flags & 0x4000 and len(a) > 1: s['pose'] = a[1] & 0xff; s['dir'] = (a[1] >> 8) & 0xff

    def _fondu(self, v, f):
        """Fade.SetFadeIn / SetFadeOutBlack / SetFadeOutWhite / SetFadeOutColor (FadePlane.Command) : sortie = vers l'opacite 1 depuis l'opacite courante ;
        entree = le plan repart de l'opacite 1 vers 0 (Unity part de l'opacite courante du plan : meme chose apres une sortie terminee). Duree <= 1 image : immediat."""
        d = v & 0x7ff; fd = self.fondu_fond if v & 0x4000 else self.fondu; fd['noir'] = 0      # bit 14 : Fade.l_targetLayer (NativeManager.cmd_fade D14D10), le plan qui recoit la commande
        if d > 1 and not v & (0x800 | 0x2000) and Etat.vitesse_fondu > 1.0: d = max(1, int(round(d / Etat.vitesse_fondu)))       # fondu au noir (changement de carte...) plus court : reglage « vitesse des transitions »
        if v & 0x1000:
            fd['col'] = tuple(f[:3]) if v & 0x800 and len(f) >= 3 else ((1.0, 1.0, 1.0) if v & 0x2000 else (0.0, 0.0, 0.0))
            fd['fin'] = 1.0
            if d <= 1: fd['a'] = 1.0; fd['n'] = 0; fd['pas'] = 0.0
            else: fd['pas'] = (1.0 - fd['a']) / d; fd['n'] = d
        else:
            fd['fin'] = 0.0
            if d <= 1: fd['a'] = 0.0; fd['n'] = 0; fd['pas'] = 0.0
            else: fd['a'] = 1.0; fd['pas'] = -1.0 / d; fd['n'] = d

    def tick_fondu(self):
        """FadePlane.Update : une fois par image du jeu, pour chacun des deux plans. Garde-fou (plan de devant seulement) : un ecran reste tout noir plus de 6 s (fondu d'entree lance par Unity lui-meme, pas par le moteur) est rouvert ;
        le plan de fond n'en a pas : le moteur le tient noir de lui-meme (titre de chapitre, 160 images) et le rouvre par une commande."""
        for fd, garde in ((self.fondu, True), (self.fondu_fond, False)):
            if fd['n'] >= 1:
                fd['n'] -= 1
                if fd['n'] < 1: fd['a'] = fd['fin']
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
        self.msg = {'type': 0, 'y': 0, 'feed': False, 'shake': 0}      # fenetre de message (port 1) : type de fenetre, defilement du canevas, curseur de fin de page
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
            if port == 1:                                       # fenetre de message : dessinee d'apres le canevas du moteur ; MenuMessage.NoticeReceive : 0 type, 1 curseur, 2 secousse, 3 defilement
                if len(a) >= 2:
                    c, v = a[0], a[1]
                    if c == 0: self.msg['type'] = v
                    elif c == 1: self.msg['feed'] = (v & 0xffff) == 1
                    elif c == 3: self.msg['y'] = v
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
        self.images = 0
        # animations d'objets de la carte (portes...) : le moteur attend qu'Unity les termine (bit0 de l'octet +0x14 de l'entree)
        self.anims = []                          # [(image d'echeance, index d'objet)]
        self.duree_anim = None                   # (objet, numero) -> images avant la fin de l'animation commune (donnee par la fenetre, d'apres les donnees de la carte) ; None = DUREE_ANIM
        self.fldobj = 0
        self.msg_visible = False                 # fenetre de message affichee ? (MenuPort::SetVisible sur le port du message)
        def _sv(uc, a, sz, u):
            port = uc.reg_read(c.XREG[0]) & 0xffffffffffff
            if port and port == struct.unpack('<Q', c.mem(self.L + OBJ_MESSAGE + 0x30, 8))[0]:
                self.msg_visible = bool(uc.reg_read(c.XREG[1]) & 0xff)
                if not self.msg_visible: self._acc_texte = 0.0
        hv = c.export('_ZN8MenuPort10SetVisibleEb')
        c.uc.hook_add(unicorn.UC_HOOK_CODE, _sv, None, hv, hv)
        self.fielddata = 0; self._grille = None; self._grille_img = -999
        self.demande_pause = False               # le joueur a choisi « Paramètres » dans le menu Divers : la visionneuse ouvre son menu Pause (voir _detourner_parametres)
        self._detourner_parametres()
        def _fd(uc, a, sz, u): self.fielddata = uc.reg_read(c.XREG[0]) & 0xffffffffffff          # FieldData::drawBlock(this) : l'objet qui porte la carte du monde
        hfd = c.export('_ZN9FieldData9drawBlockEv')
        c.uc.hook_add(unicorn.UC_HOOK_CODE, _fd, None, hfd, hfd)
        def _sca(uc, a, sz, u): self.fldobj = uc.reg_read(c.XREG[0])
        uc_hook = c.export('_ZN9FLDObject18SetCommonAnimationEii')
        c.uc.hook_add(unicorn.UC_HOOK_CODE, _sca, None, uc_hook, uc_hook)
        self._crochets_texte()
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
                    v = self.vitesse_texte
                    if v == 4.0 or uc.reg_read(c.XREG[8]) & 0xffff != 4: return           # 4 : comme le jeu ; autre que 4 (vitesse 100 des fenetres de combat) : inchange
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
        """Retour a l'ecran-titre : ce que fait le bouton « Revenir à l'écran titre » des Parametres d'origine du jeu quand on repond « Oui » (TownMenu_OPERATION_SETTING::menuUpdate, etat 5) : efface la banque 4
        (sauvegarde automatique, killbank), verrouille le joueur, puis Global::startTitle() (fondu au noir, chapitre 0, la partie suivante est le titre). Les menus et le message du moteur doivent etre fermes."""
        c = self.core
        c.call(self.E('_ZN7profile8SaveLoad8killbankEib'), 4, 0, label='killbank')
        c.call(self.E('_ZN3cmn11GameManager12getSingletonEv'), label='getSingleton')
        c.call(self.E('_ZN3cmn13PlayerManager7setLockEb'), 1, label='setLock')
        c.call(self.E('_ZN6Global10startTitleEv'), self._global(), label='startTitle')

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
        self.etat.effet = {'n': 0}; self._drapeau_effet(True)
        if self.etat.attente_charge is None: self.etat.attente_charge = {'base': avant, 'n': 0}

    def _effet_combat(self):
        """Une image du jeu : avance l'effet de debut de combat, abaisse le drapeau a la fin (le moteur reprend a l'image suivante) ; compte l'attente du chargement."""
        ef = self.etat.effet
        if ef is not None:
            ef['n'] += 1
            if ef['n'] >= EFFET_COMBAT_IMAGES: self._drapeau_effet(False); self.etat.effet = None
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
        r = c.call(self.E('GameUpdate'), tenu, decl, label='GameUpdate')
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
        for t, a, f in pq:
            if t == 34 and a and (a[0] & 0xf) == EFFET_COMBAT: self._debut_effet_combat(avant)
        ac = self.etat.attente_charge
        if ac is not None and self.etat.effet is None and self.etat.cartes_chargees > ac['base']: self.etat.attente_charge = None      # la scene du combat est arrivee
        self.etat.tick_fondu()
        prec = self.etat.partie
        self.etat.partie = struct.unpack('<H', c.mem(self._global() + 0xee, 2))[0]
        if self.etat.partie == PARTIE_COMBAT and prec != PARTIE_COMBAT and self.etat.attente_charge is None and self.etat.cartes_chargees <= avant:
            self.etat.attente_charge = {'base': avant, 'n': 0}      # combat sans effet d'ecran (scenario...) : la scene d'avant ne doit pas apparaitre avant le chargement de celle du combat
        if self.etat.partie != PARTIE_CHAMP: self.etat.champ = None; self.etat.monde = None
        else: self._lire_monde()
        self.images += 1
        return pq

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
