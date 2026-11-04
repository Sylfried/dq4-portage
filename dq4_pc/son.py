"""Son du jeu : musiques et bruitages d'origine (assets/sound/*.akb du paquet de donnees), joues par pyglet.

Format AKB (conteneur Square Enix, lu dans libsdlib_android.so : akbMaterial*) :
  0x00 'AKB ' ; 0x04 u16 version ; 0x06 u16 taille de l'en-tete ; 0x08 u32 taille du fichier ; 0x0c u8 codec (2 = MS-ADPCM, 5 = Ogg Vorbis) ;
  0x0d u8 canaux ; 0x0e u16 frequence ; 0x10 u32 nombre d'echantillons ; 0x14 u32 debut de boucle ; 0x18 u32 fin de boucle (0 = pas de boucle) ;
  0x20 float volume ; donnees a 0xcc : Ogg complet (codec 5), ou 4 octets puis blocs MS-ADPCM (codec 2, taille de bloc = u16 a 0xc2).
Les paquets du moteur : 35 = bruitage (SE%04d), 36 = arret d'un bruitage, 37 = musique (BGM%02d ; valeur >= 4096 = arret).
Rien n'est ecrit hors du dossier cache ; aucun fichier du jeu n'est modifie.
"""
import os, io, time, struct, zipfile, threading, collections
from concurrent.futures import ThreadPoolExecutor
import numpy as np

DEBUT_DONNEES = 0xcc
ADAPT = (230, 230, 230, 230, 307, 409, 512, 614, 768, 614, 512, 409, 307, 230, 230, 230)
COEF = ((256, 0), (512, -256), (0, 0), (192, 64), (240, 0), (460, -208), (392, -232))


def lire_entete(d):
    """-> dict (codec, canaux, frequence, echantillons, debut, fin, volume, bloc) ou None si ce n'est pas un AKB."""
    if len(d) < DEBUT_DONNEES or d[:4] != b'AKB ': return None
    codec, canaux, freq, n, deb, fin = struct.unpack_from('<BBHIII', d, 0x0c)
    volume = struct.unpack_from('<f', d, 0x20)[0]
    bloc = struct.unpack_from('<H', d, 0xc2)[0]              # bloc d'extra a 0xc0 (u16 a 0xc0 : 0, taille de bloc a 0xc2, echantillons u32 a 0xc4, debut de boucle u32 a 0xc8)
    return dict(codec=codec, canaux=canaux, frequence=freq, echantillons=n, debut=deb, fin=fin, volume=volume if 0.0 < volume <= 2.0 else 1.0, bloc=bloc)


def decoder_msadpcm(d, canaux, bloc):
    """MS-ADPCM par blocs (quatre bits par echantillon) -> int16 (n, canaux). Les blocs sont independants (leur en-tete donne l'etat) : on decode tous les blocs a la fois."""
    nb = len(d) // bloc
    if nb == 0: return np.zeros((0, canaux), np.int16)
    b = np.frombuffer(d[:nb * bloc], np.uint8).reshape(nb, bloc)
    ent = 7 * canaux
    pred = [b[:, c].astype(np.int64) for c in range(canaux)]
    # en-tete : indices de prediction (1 octet par canal), deltas (s16), echantillon 1 (s16), echantillon 2 (s16), chacun regroupe par canal
    def s16(o): return (b[:, o].astype(np.int64) | (b[:, o + 1].astype(np.int64) << 8)).astype(np.int16).astype(np.int64)
    delta = [s16(canaux + 2 * c) for c in range(canaux)]
    s1 = [s16(canaux + 2 * canaux + 2 * c) for c in range(canaux)]
    s2 = [s16(canaux + 4 * canaux + 2 * c) for c in range(canaux)]
    k1 = np.array([k[0] for k in COEF], np.int64); k2 = np.array([k[1] for k in COEF], np.int64)
    c1 = [k1[np.minimum(pc, 6)] for pc in pred]; c2 = [k2[np.minimum(pc, 6)] for pc in pred]
    octets = b[:, ent:]
    nibs = np.empty((nb, octets.shape[1] * 2), np.int64)
    nibs[:, 0::2] = octets >> 4; nibs[:, 1::2] = octets & 15
    par_canal = nibs.shape[1] // canaux
    sortie = np.zeros((nb, 2 + par_canal, canaux), np.int64)
    adapt = np.array(ADAPT, np.int64)
    for c in range(canaux):
        sortie[:, 0, c] = s2[c]; sortie[:, 1, c] = s1[c]
        a, z = s1[c].copy(), s2[c].copy(); dl = delta[c].copy()
        nc = nibs[:, c::canaux]                       # stereo : les quartets alternent gauche (poids fort) / droite
        for i in range(par_canal):
            n = nc[:, i]; sn = n - ((n & 8) << 1)
            t = a * c1[c] + z * c2[c]; p = np.where(t < 0, -((-t) >> 8), t >> 8)         # division entiere vers zero (code de reference Microsoft)
            p = np.clip(p + sn * dl, -32768, 32767)
            z = a; a = p
            dl = np.maximum(16, (adapt[n] * dl) >> 8)
            sortie[:, 2 + i, c] = p
    return sortie.reshape(-1, canaux).astype(np.int16)


VERSION_CACHE_SON = 2             # version des bruitages gardes dans le cache disque (son_SE*.npz) : 2 depuis #201 (boucles des SE 329, 331, 1118) ; un cache d'une autre version est refait
TOLERANCE_FIN_BOUCLE = 2048     # echantillons : au-dela, l'en-tete est juge incoherent et le son n'est pas bouclé (garde d'origine du portage)


def decoder_ogg(octets):
    """Ogg Vorbis -> int16 (n, canaux). Lu en flottants puis ECRETE a la pleine echelle : Vorbis depasse parfois +-1,0 apres decodage, et la lecture directe en int16 faisait deborder ces echantillons
    (un pic devenait un pic de signe oppose : BGM 14, 3 echantillons vers 91 s ; BGM 34, 7 echantillons ; #200)."""
    import soundfile as sf
    x, _ = sf.read(io.BytesIO(octets), dtype='float32', always_2d=True)
    return np.clip(np.rint(x * 32767.0), -32768, 32767).astype(np.int16)


def decoder_akb(d):
    """Fichier AKB -> dict (pcm int16 (n, canaux), frequence, debut, fin, volume) ou None."""
    h = lire_entete(d)
    if h is None: return None
    if h['codec'] == 2:
        pcm = decoder_msadpcm(d[DEBUT_DONNEES + 4:], h['canaux'], h['bloc'] or 512)
    elif h['codec'] == 5:
        pcm = decoder_ogg(d[DEBUT_DONNEES:])
    else:
        return None
    n = len(pcm)
    deb, fin = h['debut'], h['fin']
    if n < fin <= n + TOLERANCE_FIN_BOUCLE: fin = n          # fin de boucle qui depasse de quelques echantillons la fin des donnees (reste d'un bloc ADPCM : SE 329, 331, 1118 ; #201) : la boucle va jusqu'a la fin des donnees
    boucle = 0 < fin <= n and deb < fin
    return dict(pcm=np.ascontiguousarray(pcm), frequence=h['frequence'], debut=deb if boucle else 0, fin=fin if boucle else 0, volume=h['volume'], boucle=boucle)


BGM_RELANCE = 0x1000        # cmd_bgm : valeur >= 0x1000 = Sound.PlayBGM(valeur - 0x1000) avec reprise : la musique en cours est memorisee et reprise (depuis le debut) quand ce morceau est fini (jingle)
BGM_ARRET = 0x4000           # valeur >= 0x4000 = Sound.StopBGM (SoundManager::stopBgm envoie 0x4000 | duree, battleStop 0x4008) ; la duree est ignoree par Unity (arret immediat)
SE_GRACE = 0.4               # secondes : un bruitage qui vient d'etre lance n'est jamais libere parce que son lecteur ne se dit pas encore « en lecture » (marche acceleree : le moteur fait plusieurs pas, donc plusieurs tick(), a la suite dans la meme image affichee, juste apres l'ordre du bruitage de porte ou de sortie de village)
SE_BOUCLE_MAX = 120.0        # secondes : un bruitage en boucle dont le moteur n'enverrait jamais l'arret est coupe
ECHECS_MAX = 3               # echecs de lecture consecutifs (bruitage ou musique) avant de couper le son un moment (peripherique retire ou change, pilote : #221, audit SND-10)
DELAIS_REESSAI = (2.0, 10.0, 30.0)   # secondes avant le nouvel essai, selon le nombre de coupures deja subies (le dernier delai se repete)
NOTES_MAX = 40               # lignes de journal au plus par session (une panne qui dure ne remplit pas le fichier)
IMAGES_MOTEUR_PAR_S = 30.0   # images du moteur par seconde a vitesse normale (un pas du moteur = 1/30 s)
# Musiques decodees d'avance (tache de fond, un fil a part, une a la fois, quand rien d'autre n'est a decoder) et gardees en memoire (jamais chassees par le cache ; 59 Mo en tout) : le decodage d'une musique longue prend du temps
# (BGM 23, 113 s : 0,6 a 1,2 s ici, plus sur un PC lent ; les jingles : 0,01 a 0,14 s), alors que le moteur arrete une musique demandee pendant un combat accelere 2,7 a 3,9 s apres l'avoir lancee (x3) : sans cela, la musique
# de la defaite (BGM 23, demandee quand tout le groupe est battu) n'etait decodee qu'a ce moment-la (elle partait en retard, et un arret du moteur arrive avant la fin du decodage la supprimait : le groupe mourait en silence).
BGM_PRECHARGES = (6, 8, 10, 13) + tuple(range(35, 51)) + (30, 23)

# ---- categories de sons (menu Echap > Son). Unity ne connait que PlayBGM / PlaySE (classe Sound) : ni voix, ni canal « ME » a part. Les categories sont celles que le MOTEUR distingue par la facon de jouer un son :
# musique (PlayBGM, avec boucle) ; jingles et fanfares (PlayBGM sans boucle : BGM 6, 8, 10, 13, 35 a 50 de 2,9 a 23,2 s, ou demande avec la reprise de la musique d'avant, 0x1000 | n = SoundManager::playRestart) ;
# bruitages (PlaySE) ; sons de l'interface (bruitages 300 a 304 : 300 = bouton de menu joue par Unity et page de message jouee par ui_MsgLoop, 301 = menu EXTRA_PRESENT_EXP, 304 = ouverture d'un Oui / Non ;
# 302 et 303 : meme bloc de la banque, jamais appeles directement par le moteur, donc supposes de l'interface).
CATEGORIES = ('musique', 'jingles', 'effets', 'interface')
SE_INTERFACE = frozenset(range(300, 305))
SE_JINGLES = frozenset({409})   # fanfare de victoire (BattleEndTask : SoundManager::play(409), 2,9 s) : jouee comme un bruitage mais c'est une fanfare ; reglee avec « Jingles et fanfares » (volume de l'option « bruitages » du jeu conservee)
JINGLE_DUREE_MAX = 30.0       # secondes : un morceau sans boucle plus court que cela est un jingle ; BGM 1 (111 s) et 34 (655 s), sans boucle, sont de vraies musiques (sauf demande avec reprise)


def categorie_se(ident):
    return 'interface' if ident in SE_INTERFACE else 'jingles' if ident in SE_JINGLES else 'effets'


def categorie_bgm(relance, boucle, duree):
    """'jingles' pour un morceau sans boucle demande avec reprise de la musique d'avant, ou court ; 'musique' sinon (un morceau en boucle ne revient jamais a la musique d'avant : c'est une musique)."""
    return 'jingles' if (not boucle and (relance or duree <= JINGLE_DUREE_MAX)) else 'musique'


def volume_option_jeu(indice):
    """Option « volume » de la fenetre Parametres du jeu (OptionStatus, 0 a 4, enregistree dans la sauvegarde) -> facteur : Sound.SetVolumeBGM / SetVolumeSE font s_bgmVolume = s_seVolume = (indice + 1) x 0,2."""
    return (min(4, max(0, int(indice))) + 1) * 0.2


class Mixage:
    """Volumes (0 a 1) et interrupteurs par categorie. gain(categorie, volume propre au fichier) = volume general x volume de la categorie x volume propre x option « volume » du jeu
    (musique et jingles : celle de la musique ; bruitages et interface : celle des bruitages), 0 si la categorie est coupee. Pur calcul : aucun lecteur audio."""
    def __init__(self, general=1.0, musique=1.0, jingles=1.0, effets=1.0, interface=1.0):
        self.general = float(general)
        self.vol = dict(musique=float(musique), jingles=float(jingles), effets=float(effets), interface=float(interface))
        self.actif = {c: True for c in CATEGORIES}
        self.jeu = dict(musique=1.0, effets=1.0)              # options « volume » du jeu (fenetre Parametres) : facteurs 0,2 a 1

    def gain(self, cat, propre=1.0, option=None):
        """option : « musique » ou « effets » = quelle option « volume » du jeu s'applique ; par defaut celle de la musique pour la musique et les jingles, celle des bruitages pour le reste (un bruitage range dans « jingles » passe option='effets')."""
        if not self.actif.get(cat, True): return 0.0
        g = self.general * self.vol.get(cat, 1.0) * propre * self.jeu[option or ('musique' if cat in ('musique', 'jingles') else 'effets')]
        return max(0.0, min(1.0, g))


class _SE:
    """Un bruitage en cours : identifiant, lecteur, heure de fin, categorie, volume propre du fichier."""
    __slots__ = ('ident', 'p', 'fin', 'cat', 'propre', 'debut')
    def __init__(self, ident, p, fin, cat, propre, debut=None): self.ident, self.p, self.fin, self.cat, self.propre = ident, p, fin, cat, propre; self.debut = time.time() if debut is None else debut


class Son:
    """Lecture : une musique a la fois (avec boucle), des bruitages en parallele. Le decodage se fait en tache de fond."""
    def __init__(self, apk, cache, log=print, volume_musique=1.0, volume_bruitages=1.0, actif=True, journal=None, alerte=None):
        self.apk, self.cache, self.log = apk, cache, log
        self.journal, self.alerte = journal, alerte                        # journal(texte) : ligne ajoutee au journal des erreurs ; alerte(texte) : petit message a l'ecran (coupure et retour du son)
        self.echecs = 0; self.pannes = 0; self.reessai = None; self.bgm_perdue = None      # echecs de lecture consecutifs ; coupures subies ; heure du nouvel essai (None = pas de coupure en cours) ; musique a relancer au retour du son
        self._notes = 0; self._vus = set(); self._en_panne = False
        self.mix = Mixage(musique=volume_musique, effets=volume_bruitages)
        self.actif = actif; self.ok = False
        self.pool = ThreadPoolExecutor(max_workers=1)
        self.pool_fond = ThreadPoolExecutor(max_workers=1)                 # prechargement des musiques : un fil a part, pour qu'il ne retarde jamais un son demande par le moteur
        self.dec = collections.OrderedDict(); self.jobs = {}
        self.fond = []; self.epingles = set()                              # musiques a decoder d'avance (noms), noms gardes en memoire
        self.attente_bgm = collections.deque(); self.e_req = None          # ordres de musique retenus pendant un jingle (valeur, image du moteur) ; image du moteur de l'ordre qui a lance la musique en cours
        self.bgm = None; self.bgm_id = None; self.bgm_demande = None
        self.reprise = None; self.bgm_fin = None                           # jingle : musique a reprendre, heure de fin du jingle
        self.bgm_t0 = None; self.bgm_pos0 = 0.0; self.bgm_decalage = 0.0     # heure et position (secondes) du depart de la lecture ; position demandee pour la prochaine musique (chargement d'un etat)
        self.se = []                                                       # [_SE]
        self.bgm_propre = 1.0; self.bgm_cat = 'musique'; self.t_pause = None   # volume propre a la musique en cours et sa categorie ; heure du debut de la pause (menu Echap)
        self.suspendu = False; self.ecoute = False                         # menu Echap ouvert ; page Son du menu (les sons jouent pendant que le moteur est arrete)
        self.hors_focus = False                                            # la fenetre n'a plus le focus (Alt + Tab, minimisee) : tout est en pause, meme pendant l'ecoute de la page Son (#235)
        self.verrou = threading.Lock(); self.zip = None; self.ogg = False; self._table_vol = None           # (snd_vol.dat : lu a la premiere utilisation, voir vol_snd)
        try:
            import soundfile                                               # lecture des musiques (Ogg Vorbis) ; les bruitages n'en ont pas besoin
            self.ogg = True
        except Exception:
            self.log('Musiques indisponibles : module "soundfile" absent (pip install soundfile). Les bruitages restent actifs.')
        try:
            import pyglet
            from pyglet.media.codecs.base import AudioFormat, AudioData
            self.pyglet = pyglet; self.media = pyglet.media; self.AudioFormat = AudioFormat; self.AudioData = AudioData
            self.ok = True
        except Exception as e:
            self.log('Son indisponible (%r)' % (e,))

    # ---- echecs de lecture (#221, audit SND-10 et SND-12)
    def _noter(self, texte, alerte=None):
        """Une ligne dans la console et dans le journal des erreurs (au plus NOTES_MAX par session) ; `alerte` : le meme fait, en bref, a l'ecran."""
        self.log('Son : ' + texte)
        if self._notes < NOTES_MAX:
            self._notes += 1
            if self.journal is not None:
                try: self.journal(texte)
                except Exception: pass
        if alerte and self.alerte is not None:
            try: self.alerte(alerte)
            except Exception: pass

    def _une_fois(self, cle, e):
        """Erreur sans consequence immediate (volume, reprise apres pause) : notee une seule fois par session."""
        if cle not in self._vus: self._vus.add(cle); self._noter('%s impossible (%r), note une seule fois' % (cle, e))

    def _echec(self, quoi, e):
        """Un bruitage ou une musique n'a pas pu etre lance : ECHECS_MAX echecs de suite coupent le son un moment (nouvel essai tout seul, voir tick) au lieu de le couper jusqu'a la fermeture du jeu."""
        self.echecs += 1; self._noter('%s impossible (%r), echec %d' % (quoi, e, self.echecs))
        if self.echecs >= ECHECS_MAX:
            d = DELAIS_REESSAI[min(self.pannes, len(DELAIS_REESSAI) - 1)]; self.pannes += 1
            self.ok = False; self.reessai = time.time() + d; self._en_panne = True
            self._noter('son interrompu, nouvel essai dans %d s' % d, alerte='Son interrompu : nouvel essai automatique')

    def _succes(self):
        """Un son vient de partir : la serie d'echecs est finie (et, apres une coupure, le son est retabli)."""
        if self._en_panne: self._en_panne = False; self._noter('son retabli', alerte='Son rétabli')
        self.echecs = 0

    def _reessayer(self):
        """Fin de la coupure : le son est rouvert ; un seul echec de plus le recoupe aussitot (delai plus long). La musique demandee pendant la coupure est relancee."""
        self.ok = True; self.reessai = None; self.echecs = ECHECS_MAX - 1
        v, self.bgm_perdue = self.bgm_perdue, None
        if v is not None and self.bgm is None: self.jouer_bgm(v)

    def _suivre_pendant_la_panne(self, evts):
        """Pendant la coupure les ordres du moteur sont perdus, sauf la musique de fond : la derniere demandee est relancee au retour du son (un arret la supprime ; un jingle a reprise est ignore)."""
        for t, v in evts:
            if t == 37: self.bgm_perdue = None if v >= BGM_ARRET else (v if v < BGM_RELANCE else self.bgm_perdue)

    # ---- volume propre de chaque son (snd_vol.dat)
    def vol_snd(self, ident):
        """Facteur de `assets/sound/snd_vol.dat` pour un son : musique `BGM%02d` = indice du numero de fichier, bruitage `SE%04d` = indice de son numero (1171 flottants ; 1,0 pour presque tous). L'original joue en-tete x snd_vol x option (`SoundControl.Play`) : 49 musiques de 0,7 a 0,95 et le bruitage 409 (fanfare) a 0,6 (audit SND-01, #237). 1,0 si le fichier manque ou si l'indice est hors table."""
        t = self._table_vol
        if t is None:
            with self.verrou:
                t = self._table_vol
                if t is None:
                    try:
                        if self.zip is None: self.zip = zipfile.ZipFile(self.apk)
                        t = np.frombuffer(self.zip.read('assets/sound/snd_vol.dat'), '<f4').copy()
                    except Exception: t = np.ones(0, np.float32)
                    self._table_vol = t
        return float(t[ident]) if 0 <= ident < len(t) and 0.0 < float(t[ident]) <= 1.0 else 1.0

    # ---- lecture des fichiers
    def _octets(self, nom):
        with self.verrou:
            if self.zip is None: self.zip = zipfile.ZipFile(self.apk)
            try: return self.zip.read('assets/sound/%s.akb' % nom)
            except KeyError: return None

    def _decode(self, nom):
        f = os.path.join(self.cache, 'son_%s.npz' % nom)
        try:
            if os.path.exists(f):
                z = np.load(f)
                if len(z['p']) > 4 and int(z['p'][4]) == VERSION_CACHE_SON: return dict(pcm=z['pcm'], frequence=int(z['p'][0]), debut=int(z['p'][1]), fin=int(z['p'][2]), volume=float(z['v'][0]), boucle=bool(z['p'][3]))        # (cache d'une ancienne version : refait)
        except Exception: pass
        d = self._octets(nom)
        if d is None: return None
        r = decoder_akb(d)
        if r is not None and nom.startswith('SE'):                        # les bruitages sont petits : cache disque (une musique longue, elle, prend plus d'une seconde : voir BGM_PRECHARGES)
            try: np.savez(f, pcm=r['pcm'], p=np.array([r['frequence'], r['debut'], r['fin'], int(r['boucle']), VERSION_CACHE_SON], np.int64), v=np.array([r['volume']], np.float32))
            except Exception: pass
        return r

    def _obtenir(self, nom, rappel, fond=False):
        """Appelle rappel(donnees) : tout de suite si `nom` est deja decode, sinon depuis tick() quand la tache de fond a fini."""
        if nom in self.dec: self.dec.move_to_end(nom); rappel(self.dec[nom]); return
        if nom in self.jobs: self.jobs[nom][1].append(rappel); return
        self.jobs[nom] = ((self.pool_fond if fond else self.pool).submit(self._decode_sur, nom), [rappel])

    def _decode_sur(self, nom):
        try: return self._decode(nom)
        except Exception as e:
            self.log('Son : %s illisible (%r)' % (nom, e)); return None

    def precharger(self, ids):
        """Decode en tache de fond les bruitages courants."""
        if not (self.ok and self.actif): return
        for i in ids: self._obtenir('SE%04d' % i, lambda r: None)

    def precharger_musiques(self, ids=BGM_PRECHARGES):
        """Musiques a decoder d'avance : une par image du jeu, seulement quand aucun autre decodage n'attend (la premiere musique du jeu passe donc la premiere) et une fois qu'une musique joue. Elles restent en memoire."""
        if not (self.ok and self.ogg): return                                # (meme son coupe au depart : le prechargement attend qu'une musique joue)
        for i in ids:
            nom = 'BGM%02d' % i
            self.epingles.add(nom)
            if nom not in self.fond: self.fond.append(nom)

    def _purger(self):
        """Cache de decodage : 80 sons (hors musiques epinglees) et 400 Mo au plus ; les plus anciennement utilises partent les premiers."""
        while True:
            libres = [k for k in self.dec if k not in self.epingles]
            if len(libres) <= 80 and sum(x['pcm'].nbytes for x in self.dec.values()) <= 400 * 2 ** 20: return
            if not libres: return
            del self.dec[libres[0]]

    # ---- appele a chaque image
    def tick(self):
        if not self.ok:
            if self.reessai is not None and time.time() >= self.reessai: self._reessayer()
            return
        for nom, (fut, rappels) in list(self.jobs.items()):
            if not fut.done(): continue
            r = fut.result(); del self.jobs[nom]
            if r is None: continue
            self.dec[nom] = r; self._purger()
            for cb in rappels: cb(r)
        if self.fond and not self.jobs and self.bgm is not None:             # rien d'autre a decoder et une musique joue : on avance le prechargement d'une musique
            nom = self.fond.pop(0)
            if nom not in self.dec: self._obtenir(nom, lambda r: None, fond=True)
        maintenant = time.time()
        self._liberer_ordres(maintenant)
        if self.reprise is not None and self.bgm_fin is not None and maintenant >= self.bgm_fin:       # Sound.SystemUpdate : le jingle est fini, la musique d'avant reprend
            n = self.reprise; self.reprise = None; self.bgm_fin = None
            self.arreter_bgm(); self.jouer_bgm(n)
        vivants = []
        for x in self.se:                                                  # un bruitage termine (ou depasse sa duree) est libere
            if maintenant < x.fin and (x.p.playing or maintenant - x.debut < SE_GRACE): vivants.append(x)
            else:
                try: x.p.delete()
                except Exception: pass
        self.se = vivants

    # ---- ordres du moteur
    def evenements(self, evts, image_moteur=None):
        """evts : [(type de paquet, valeur)] de l'image : 35 bruitage, 36 arret de bruitage, 37 musique. image_moteur : numero de la derniere image du moteur (30 par seconde a vitesse normale) :
        sert a ne pas couper un jingle quand le jeu tourne plus vite que la normale (voir _jingle_protege)."""
        if not (self.ok and self.actif):
            if self.reessai is not None and self.actif: self._suivre_pendant_la_panne(evts)
            return
        if os.environ.get('DQ_SON'): self.log('Son : image %s ordres %s' % (getattr(self, 'image', '?'), evts))       # (test) journal des ordres du moteur
        for t, v in evts:
            if t == 35: self.jouer_se(v)
            elif t == 36: self.arreter_se(v)
            elif t == 37: self._ordre_bgm(v, image_moteur)

    def _ordre_bgm(self, v, e):
        """Ordre de musique du moteur (image e) : appliques tout de suite, ou retenu tant qu'un jingle le meriterait (et derriere ceux qui attendent deja : l'ordre des ordres est garde)."""
        if self.attente_bgm or self._jingle_protege(e): self.attente_bgm.append((v, e))
        else: self._appliquer_ordre(v, e)

    def _appliquer_ordre(self, v, e):
        self.jouer_bgm(v); self.e_req = e

    def _jingle_protege(self, e):
        """Vrai si un jingle joue encore ET que l'ordre du moteur d'image e serait arrive apres lui a vitesse normale. Un combat accelere enchaine ses ordres (arret, reprise de la musique, ...) 2 a 3 fois plus tot : la fanfare etait coupee
        (montee de niveau, BGM 47 de 3,1 s : jouee 1,75 s a x3). L'ordre attend donc l'heure a laquelle il serait arrive a vitesse normale (image e - image de l'ordre qui a lance le jingle, a 30 par seconde) ou la fin du jingle, la premiere des deux."""
        if e is None or self.e_req is None or self.bgm is None or self.bgm_fin is None or self.bgm_cat != 'jingles' or self.bgm_t0 is None: return False
        if not self.mix.actif.get('jingles', True): return False          # jingles coupes : rien a proteger
        return time.time() < min(self.bgm_fin, self.bgm_t0 + (e - self.e_req) / IMAGES_MOTEUR_PAR_S)

    def _liberer_ordres(self, maintenant):
        """Ordres de musique retenus : appliques dans l'ordre des que le jingle n'a plus de raison de les retenir. Jingle fini et ordre suivant = un autre jingle (avec reprise) : la musique d'avant reprend d'abord, comme sans retard (Sound.SystemUpdate)."""
        if self.t_pause is not None: return
        while self.attente_bgm:
            v, e = self.attente_bgm[0]
            if self._jingle_protege(e): return
            if BGM_RELANCE <= v < BGM_ARRET and self.reprise is not None and self.bgm_fin is not None and maintenant >= self.bgm_fin:
                n = self.reprise; self.reprise = None; self.bgm_fin = None; self.arreter_bgm(); self.jouer_bgm(n)
            self.attente_bgm.popleft(); self._appliquer_ordre(v, e)

    def jouer_se(self, ident):
        if os.environ.get('DQ_SON'): self.log('Son : image %s bruitage %d' % (getattr(self, 'image', '?'), ident))
        if ident <= 0: return                                                         # bruitage 0 : « aucun » (le moteur l'envoie avec chaque coup critique, SE0000 n'existe pas dans les donnees)
        nom = 'SE%04d' % ident
        self._obtenir(nom, lambda r, i=ident: self._lancer_se(i, r))

    def _lancer_se(self, ident, r):
        if not self.ok: return                                                         # son coupe (panne en cours, ou pas de pilote audio) : rien n'est tente, les echecs ne s'accumulent pas
        try:
            fmt = self.AudioFormat(channels=r['pcm'].shape[1], sample_size=16, sample_rate=r['frequence'])
            boucle = r['boucle']                                                            # bruitages en boucle (14 sur 634) : jusqu'a l'ordre d'arret du moteur (paquet 36)
            src = SourceBoucle(self.media, self.AudioData, fmt, r['pcm'], r['debut'] if boucle else 0, r['fin'] if boucle else 0)
            cat = categorie_se(ident); propre = r['volume'] * self.vol_snd(ident); g = self.mix.gain(cat, propre, 'effets')
            if g <= 0.0 and not boucle: return                                 # categorie coupee (ou volume a zero) : un bruitage court n'est pas joue ; un bruitage en boucle l'est a volume nul : il s'entend si on rouvre la categorie
            p = self.media.Player(); p.queue(src); p.volume = g; p.play()
            self.se.append(_SE(ident, p, time.time() + (SE_BOUCLE_MAX if boucle else len(r['pcm']) / r['frequence'] + 0.5), cat, propre))
            if len(self.se) > 24:
                try: self.se[0].p.delete()
                except Exception: pass
                del self.se[0]
            self._succes()
        except Exception as e:
            self._echec('bruitage %d' % ident, e)

    def arreter_se(self, ident):
        for x in list(self.se):
            if x.ident == ident:
                try: x.p.pause(); x.p.delete()
                except Exception: pass
        self.se = [x for x in self.se if x.ident != ident]

    def jouer_bgm(self, v, decalage=0.0):
        if v >= BGM_ARRET:                                         # cmd_bgm : >= 0x4000 = Sound.StopBGM
            n, self.reprise, self.e_req = self.reprise, None, None; self.arreter_bgm()
            if n is not None: self.jouer_bgm(n)                  # arret pendant un jingle a reprise : StopBGM d'Unity ne remet pas son etat a zero, la musique d'avant repart (audit SND-05)
            return
        if not self.ogg: return
        reprise = None; relance = v >= BGM_RELANCE
        if relance: v -= BGM_RELANCE; reprise = self.bgm_id                 # Sound.PlayBGM avec reprise : jingle, puis retour a la musique en cours
        elif v == self.bgm_id and self.bgm is not None and not self._bgm_finie(): self.reprise = None; return       # deja en cours (un morceau sans boucle arrive a sa fin n'est plus « en cours » : le redemander le relance, audit SND-06)
        else: self.reprise = None
        self.arreter_bgm(); self.bgm_id = v; self.bgm_demande = v; self.reprise = reprise; self.bgm_fin = None; self.bgm_decalage = decalage; self.e_req = None
        self._obtenir('BGM%02d' % v, lambda r, i=v, rl=relance: self._lancer_bgm(i, r, rl))

    def _bgm_finie(self):
        """Vrai si le morceau sans boucle en cours est arrive a sa fin (le lecteur reste en place, `bgm_id` aussi : seule l'heure de fin le dit)."""
        return self.bgm_fin is not None and self.t_pause is None and time.time() >= self.bgm_fin

    def _lancer_bgm(self, ident, r, relance=False):
        if self.bgm_demande != ident: return                        # une autre musique a ete demandee entre-temps
        if not self.ok:
            if not relance: self.bgm_perdue = ident                  # son coupe : a relancer au retour
            return
        try:
            fmt = self.AudioFormat(channels=r['pcm'].shape[1], sample_size=16, sample_rate=r['frequence'])
            src = SourceBoucle(self.media, self.AudioData, fmt, r['pcm'], r['debut'], r['fin'] if r['boucle'] else 0)
            dec, self.bgm_decalage = self.bgm_decalage, 0.0
            if dec > 0: src.pos = min(int(dec * r['frequence']), max(0, len(r['pcm']) - 1))              # reprise au moment enregistre (etat charge)
            depart = src.pos / r['frequence']                                                                # (avant play : le lecteur lit tout de suite quelques secondes d'avance)
            cat = categorie_bgm(relance, r['boucle'], len(r['pcm']) / r['frequence'])
            propre = r['volume'] * self.vol_snd(ident)                                                          # (en-tete du fichier x snd_vol.dat : le volume de l'original, #237)
            p = self.media.Player(); p.queue(src); p.volume = self.mix.gain(cat, propre); p.play()          # (la musique tourne meme coupee ou a zero : rouvrir la categorie la fait entendre au bon endroit)
            self.bgm = p; self.bgm_propre = propre; self.bgm_cat = cat
            self.bgm_t0 = self.t_pause if self.t_pause is not None else time.time(); self.bgm_pos0 = depart
            if self.t_pause is not None: p.pause()
            self.bgm_fin = None if r['boucle'] else self.bgm_t0 + len(r['pcm']) / r['frequence'] - depart       # jingle sans boucle : heure de la reprise de la musique d'avant
            self._succes()
        except Exception as e:
            if not relance: self.bgm_perdue = ident                          # a relancer au retour du son (un jingle rate n'a plus d'objet)
            self._echec('musique %d' % ident, e)

    def position_bgm(self):
        """Position de lecture de la musique en cours (secondes dans le morceau, boucle comprise), ou None si rien ne joue."""
        r = self.dec.get('BGM%02d' % self.bgm_id) if self.bgm_id is not None else None
        if self.bgm is None or r is None or self.bgm_t0 is None: return None
        pos = self.bgm_pos0 + ((self.t_pause if self.t_pause is not None else time.time()) - self.bgm_t0)
        fr = r['frequence']; n = len(r['pcm']) / fr
        if r['boucle'] and r['fin'] > r['debut']:
            fin, deb = r['fin'] / fr, r['debut'] / fr
            if pos >= fin: pos = deb + (pos - fin) % (fin - deb)
        return min(max(pos, 0.0), max(n - 0.01, 0.0))

    def etat_bgm(self):
        """Ce qu'il faut pour reprendre la musique au meme moment (etats enregistres) : {'id', 'pos', 'reprise'} ou None."""
        pos = self.position_bgm()
        return None if pos is None else {'id': self.bgm_id, 'pos': pos, 'reprise': self.reprise}

    def restaurer_bgm(self, info, defaut=None):
        """Chargement d'un etat : la musique repart du moment enregistre (sans `info`, ancien etat : depuis le debut de `defaut`, la derniere commande du moteur)."""
        self.arreter_bgm(); self.attente_bgm.clear()
        if info is None:
            if defaut is not None: self.jouer_bgm(defaut)
            return
        self.jouer_bgm(info['id'], float(info.get('pos') or 0.0)); self.reprise = info.get('reprise')

    def arreter_bgm(self):
        self.bgm_demande = None; self.bgm_id = None
        if self.bgm is not None:
            try: self.bgm.pause(); self.bgm.delete()
            except Exception: pass
            self.bgm = None

    # anciens noms (volume de la musique / des bruitages) : conserves pour l'interface existante
    @property
    def vol_m(self): return self.mix.vol['musique']

    @property
    def vol_b(self): return self.mix.vol['effets']

    def regler_mixage(self, general=None, volumes=None, actifs=None, jeu=None):
        """Menu Echap : nouveaux volumes / interrupteurs, appliques TOUT DE SUITE aux sons en cours (musique, jingle et bruitages deja lances).
        general : 0 a 1 ; volumes, actifs : {categorie: valeur} ; jeu : {'musique': facteur, 'effets': facteur} (options « volume » du jeu)."""
        m = self.mix
        if general is not None: m.general = float(general)
        for c, v in (volumes or {}).items():
            if c in m.vol: m.vol[c] = float(v)
        for c, v in (actifs or {}).items():
            if c in m.actif: m.actif[c] = bool(v)
        for c, v in (jeu or {}).items():
            if c in m.jeu: m.jeu[c] = float(v)
        self._appliquer_volumes()

    def _appliquer_volumes(self):
        if self.bgm is not None:
            try: self.bgm.volume = self.mix.gain(self.bgm_cat, self.bgm_propre)
            except Exception as e: self._une_fois('volume de la musique', e)
        for x in self.se:
            try: x.p.volume = self.mix.gain(x.cat, x.propre, 'effets')
            except Exception as e: self._une_fois('volume des bruitages', e)

    def regler_volumes(self, musique=None, bruitages=None):
        """Compatibilite : volume de la musique et des bruitages (0 a 1)."""
        self.regler_mixage(volumes={k: v for k, v in (('musique', musique), ('effets', bruitages)) if v is not None})

    def _doit_pauser(self):
        """Les lecteurs doivent-ils etre en pause ? Oui sans focus (toujours), ou menu suspendu hors ecoute de la page Son."""
        return self.hors_focus or (self.suspendu and not self.ecoute)

    def mettre_en_pause(self, oui):
        """Menu Echap ouvert (oui) ou ferme : musique et bruitages en pause, sauf pendant l'ecoute (page Son du menu : on entend les reglages)."""
        self.suspendu = bool(oui)
        if not oui: self.ecoute = False
        self._pause_physique(self._doit_pauser())

    def perdre_focus(self, oui):
        """Fenetre sans focus (oui) ou de retour (non) : comme Sound.SystemPause de l'original, musique et bruitages en pause ; au retour, ils reprennent la ou ils s'etaient arretes (les echeances sont decalees de la duree de la pause, `_pause_physique`)."""
        self.hors_focus = bool(oui)
        self._pause_physique(self._doit_pauser())

    def ecouter(self, oui):
        """Page Son du menu Echap : les sons reprennent (la musique en cours, les bruitages d'essai) pour entendre les volumes qu'on regle ; a la sortie de la page, ils se remettent en pause."""
        self.ecoute = bool(oui)
        if self.suspendu or self.hors_focus: self._pause_physique(self._doit_pauser())

    def _pause_physique(self, oui):
        """Pause reelle des lecteurs ; a la reprise, les echeances (fin d'un jingle, d'un bruitage) sont decalees de la duree de la pause."""
        if oui == (self.t_pause is not None) or not self.ok: return
        if oui:
            self.t_pause = time.time()
            for p in [self.bgm] + [x.p for x in self.se]:
                try:
                    if p is not None: p.pause()
                except Exception: pass
        else:
            d = time.time() - self.t_pause; self.t_pause = None
            if self.bgm_t0 is not None: self.bgm_t0 += d
            if self.bgm_fin is not None: self.bgm_fin += d
            for x in self.se: x.fin += d
            for p in [self.bgm] + [x.p for x in self.se]:
                try:
                    if p is not None: p.play()
                except Exception as e: self._une_fois('reprise apres la pause', e)

    def basculer(self):
        """Touche : son active / coupe."""
        self.actif = not self.actif
        if not self.actif:
            self.arreter_bgm(); self.attente_bgm.clear()
            for x in self.se:
                try: x.p.pause(); x.p.delete()
                except Exception: pass
            self.se = []
        return self.actif

    def fermer(self):
        for pool in (self.pool, self.pool_fond):
            try: pool.shutdown(wait=False, cancel_futures=True)
            except Exception: pass
        self.arreter_bgm()


def _classe_source(media):
    class SourceBoucle(media.Source):
        """Musique avec boucle a l'echantillon pres (debut, fin) ; fin == 0 : jouee une seule fois."""
        def __init__(self, media_, audio_data, fmt, pcm, debut, fin):
            super().__init__()
            self.audio_format = fmt; self.pcm = pcm; self.debut = debut; self.fin = fin; self.pos = 0; self._audio_data = audio_data

        def get_audio_data(self, num_bytes, compensation_time=0.0):
            oc = self.audio_format.bytes_per_frame
            n = max(1, num_bytes // oc); morceaux = []; restant = n; t0 = self.pos / self.audio_format.sample_rate
            while restant > 0:
                limite = self.fin if self.fin and self.pos < self.fin else len(self.pcm)
                k = min(restant, limite - self.pos)
                if k <= 0:
                    if self.fin: self.pos = self.debut; continue
                    break
                morceaux.append(self.pcm[self.pos:self.pos + k]); self.pos += k; restant -= k
                if self.fin and self.pos >= self.fin: self.pos = self.debut
            if not morceaux: return None
            data = np.concatenate(morceaux).tobytes()
            return self._audio_data(data, len(data), t0, len(data) / oc / self.audio_format.sample_rate)

        def seek(self, timestamp):
            self.pos = int(max(0.0, timestamp) * self.audio_format.sample_rate) % max(1, len(self.pcm))
    return SourceBoucle


class _Fabrique:
    def __call__(self, media, *a):
        return _classe_source(media)(media, *a)


SourceBoucle = _Fabrique()
