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

DATA_START = 0xcc
ADAPT = (230, 230, 230, 230, 307, 409, 512, 614, 768, 614, 512, 409, 307, 230, 230, 230)
COEF = ((256, 0), (512, -256), (0, 0), (192, 64), (240, 0), (460, -208), (392, -232))


def read_header(d):
    """-> dict (codec, canaux, frequence, echantillons, debut, fin, volume, bloc) ou None si ce n'est pas un AKB."""
    if len(d) < DATA_START or d[:4] != b'AKB ': return None
    codec, channels, freq, n, start_idx, end = struct.unpack_from('<BBHIII', d, 0x0c)
    volume = struct.unpack_from('<f', d, 0x20)[0]
    block = struct.unpack_from('<H', d, 0xc2)[0]              # bloc d'extra a 0xc0 (u16 a 0xc0 : 0, taille de bloc a 0xc2, echantillons u32 a 0xc4, debut de boucle u32 a 0xc8)
    return dict(codec=codec, canaux=channels, frequence=freq, echantillons=n, debut=start_idx, fin=end, volume=volume if 0.0 < volume <= 2.0 else 1.0, bloc=block)


def decode_msadpcm(d, channels, block):
    """MS-ADPCM par blocs (quatre bits par echantillon) -> int16 (n, canaux). Les blocs sont independants (leur en-tete donne l'etat) : on decode tous les blocs a la fois."""
    num = len(d) // block
    if num == 0: return np.zeros((0, channels), np.int16)
    b = np.frombuffer(d[:num * block], np.uint8).reshape(num, block)
    ent = 7 * channels
    pred = [b[:, c].astype(np.int64) for c in range(channels)]
    # en-tete : indices de prediction (1 octet par canal), deltas (s16), echantillon 1 (s16), echantillon 2 (s16), chacun regroupe par canal
    def s16(o): return (b[:, o].astype(np.int64) | (b[:, o + 1].astype(np.int64) << 8)).astype(np.int16).astype(np.int64)
    delta = [s16(channels + 2 * c) for c in range(channels)]
    s1 = [s16(channels + 2 * channels + 2 * c) for c in range(channels)]
    s2 = [s16(channels + 4 * channels + 2 * c) for c in range(channels)]
    k1 = np.array([k[0] for k in COEF], np.int64); k2 = np.array([k[1] for k in COEF], np.int64)
    c1 = [k1[np.minimum(pc, 6)] for pc in pred]; c2 = [k2[np.minimum(pc, 6)] for pc in pred]
    raw = b[:, ent:]
    nibs = np.empty((num, raw.shape[1] * 2), np.int64)
    nibs[:, 0::2] = raw >> 4; nibs[:, 1::2] = raw & 15
    per_channel = nibs.shape[1] // channels
    output = np.zeros((num, 2 + per_channel, channels), np.int64)
    adapt = np.array(ADAPT, np.int64)
    for c in range(channels):
        output[:, 0, c] = s2[c]; output[:, 1, c] = s1[c]
        a, z = s1[c].copy(), s2[c].copy(); dl = delta[c].copy()
        nc = nibs[:, c::channels]                       # stereo : les quartets alternent gauche (poids fort) / droite
        for i in range(per_channel):
            n = nc[:, i]; sn = n - ((n & 8) << 1)
            t = a * c1[c] + z * c2[c]; p = np.where(t < 0, -((-t) >> 8), t >> 8)         # division entiere vers zero (code de reference Microsoft)
            p = np.clip(p + sn * dl, -32768, 32767)
            z = a; a = p
            dl = np.maximum(16, (adapt[n] * dl) >> 8)
            output[:, 2 + i, c] = p
    return output.reshape(-1, channels).astype(np.int16)


def decode_akb(d):
    """Fichier AKB -> dict (pcm int16 (n, canaux), frequence, debut, fin, volume) ou None."""
    h = read_header(d)
    if h is None: return None
    if h['codec'] == 2:
        pcm = decode_msadpcm(d[DATA_START + 4:], h['canaux'], h['bloc'] or 512)
    elif h['codec'] == 5:
        import soundfile as sf
        pcm, _ = sf.read(io.BytesIO(d[DATA_START:]), dtype='int16', always_2d=True)
    else:
        return None
    n = len(pcm)
    start_idx, end = h['debut'], h['fin']
    looping = 0 < end <= n and start_idx < end
    return dict(pcm=np.ascontiguousarray(pcm), frequence=h['frequence'], debut=start_idx if looping else 0, fin=end if looping else 0, volume=h['volume'], boucle=looping)


BGM_RESTART = 0x1000        # cmd_bgm : valeur >= 0x1000 = Sound.PlayBGM(valeur - 0x1000) avec reprise : la musique en cours est memorisee et reprise (depuis le debut) quand ce morceau est fini (jingle)
BGM_STOP = 0x4000           # valeur >= 0x4000 = Sound.StopBGM (SoundManager::stopBgm envoie 0x4000 | duree, battleStop 0x4008) ; la duree est ignoree par Unity (arret immediat)
SFX_GRACE = 0.4               # secondes : un bruitage qui vient d'etre lance n'est jamais libere parce que son lecteur ne se dit pas encore « en lecture » (marche acceleree : le moteur fait plusieurs pas, donc plusieurs tick(), a la suite dans la meme image affichee, juste apres l'ordre du bruitage de porte ou de sortie de village)
SFX_LOOP_MAX = 120.0        # secondes : un bruitage en boucle dont le moteur n'enverrait jamais l'arret est coupe
# Musiques decodees d'avance (tache de fond, une a la fois, quand rien d'autre n'est a decoder) et gardees en memoire (jamais chassees par le cache) : le decodage d'une musique longue prend plus d'une seconde (BGM 23, 113 s :
# 1,15 s ici ; plus sur un PC lent), alors que le moteur arrete une musique demandee pendant un combat accelere 2,7 s apres l'avoir lancee (x3) : sans cela, la musique de la defaite (BGM 23, demandee quand tout le groupe est battu)
# n'etait decodee qu'a ce moment-la, et l'arret du moteur, arrive avant la fin du decodage, la supprimait : le groupe mourait en silence. Les jingles (BGM 6, 8, 10, 13, 35 a 50) sont courts : 0,04 s chacun.
ENGINE_FRAMES_PER_S = 30.0   # images du moteur par seconde a vitesse normale (un pas du moteur = 1/30 s)
BGM_PRELOADED = (6, 8, 10, 13) + tuple(range(35, 51)) + (30, 23)

# ---- categories de sons (menu Echap > Son). Unity ne connait que PlayBGM / PlaySE (classe Sound) : ni voix, ni canal « ME » a part. Les categories sont celles que le MOTEUR distingue par la facon de jouer un son :
# musique (PlayBGM, avec boucle) ; jingles et fanfares (PlayBGM sans boucle : BGM 6, 8, 10, 13, 35 a 50 de 2,9 a 23,2 s, ou demande avec la reprise de la musique d'avant, 0x1000 | n = SoundManager::playRestart) ;
# bruitages (PlaySE) ; sons de l'interface (bruitages 300 a 304 : 300 = bouton de menu joue par Unity et page de message jouee par ui_MsgLoop, 301 = menu EXTRA_PRESENT_EXP, 304 = ouverture d'un Oui / Non ;
# 302 et 303 : meme bloc de la banque, jamais appeles directement par le moteur, donc supposes de l'interface).
CATEGORIES = ('musique', 'jingles', 'effets', 'interface')
SFX_INTERFACE = frozenset(range(300, 305))
JINGLE_DURATION_MAX = 30.0       # secondes : un morceau sans boucle plus court que cela est un jingle ; BGM 1 (111 s) et 34 (655 s), sans boucle, sont de vraies musiques (sauf demande avec reprise)


def category_sfx(ident):
    return 'interface' if ident in SFX_INTERFACE else 'effets'


def category_bgm(restart, looping, duration):
    """'jingles' pour un morceau sans boucle demande avec reprise de la musique d'avant, ou court ; 'musique' sinon (un morceau en boucle ne revient jamais a la musique d'avant : c'est une musique)."""
    return 'jingles' if (not looping and (restart or duration <= JINGLE_DURATION_MAX)) else 'musique'


def game_option_volume(idx):
    """Option « volume » de la fenetre Parametres du jeu (OptionStatus, 0 a 4, enregistree dans la sauvegarde) -> facteur : Sound.SetVolumeBGM / SetVolumeSE font s_bgmVolume = s_seVolume = (indice + 1) x 0,2."""
    return (min(4, max(0, int(idx))) + 1) * 0.2


class Mixer:
    """Volumes (0 a 1) et interrupteurs par categorie. gain(categorie, volume propre au fichier) = volume general x volume de la categorie x volume propre x option « volume » du jeu
    (musique et jingles : celle de la musique ; bruitages et interface : celle des bruitages), 0 si la categorie est coupee. Pur calcul : aucun lecteur audio."""
    def __init__(self, general=1.0, music=1.0, jingles=1.0, effects=1.0, interface=1.0):
        self.general = float(general)
        self.vol = dict(musique=float(music), jingles=float(jingles), effets=float(effects), interface=float(interface))
        self.active = {c: True for c in CATEGORIES}
        self.game = dict(musique=1.0, effets=1.0)              # options « volume » du jeu (fenetre Parametres) : facteurs 0,2 a 1

    def gain(self, category, own=1.0):
        if not self.active.get(category, True): return 0.0
        g = self.general * self.vol.get(category, 1.0) * own * self.game['musique' if category in ('musique', 'jingles') else 'effets']
        return max(0.0, min(1.0, g))


class _SFX:
    """Un bruitage en cours : identifiant, lecteur, heure de fin, categorie, volume propre du fichier."""
    __slots__ = ('ident', 'p', 'end', 'category', 'own', 'begin')
    def __init__(self, ident, p, end, category, own, begin=None): self.ident, self.p, self.end, self.category, self.own = ident, p, end, category, own; self.begin = time.time() if begin is None else begin


class Sound:
    """Lecture : une musique a la fois (avec boucle), des bruitages en parallele. Le decodage se fait en tache de fond."""
    def __init__(self, apk, cache, log=print, music_volume=1.0, sfx_volume=1.0, active=True):
        self.apk, self.cache, self.log = apk, cache, log
        self.mix = Mixer(music=music_volume, effects=sfx_volume)
        self.active = active; self.ok = False
        self.pool = ThreadPoolExecutor(max_workers=1)
        self.background_pool = ThreadPoolExecutor(max_workers=1)                 # prechargement des musiques : un fil a part, pour qu'il ne retarde jamais un son demande par le moteur
        self.dec = collections.OrderedDict(); self.jobs = {}
        self.background = []; self.pinned = set()                              # musiques a decoder d'avance (noms), noms gardes en memoire
        self.bgm_queue = collections.deque(); self.e_req = None          # ordres de musique retenus pendant un jingle (valeur, image du moteur) ; image du moteur de l'ordre qui a lance la musique en cours
        self.bgm = None; self.bgm_id = None; self.bgm_request = None
        self.resume = None; self.bgm_end = None                           # jingle : musique a reprendre, heure de fin du jingle
        self.bgm_t0 = None; self.bgm_pos0 = 0.0; self.bgm_offset = 0.0     # heure et position (secondes) du depart de la lecture ; position demandee pour la prochaine musique (chargement d'un etat)
        self.sfx = []                                                       # [_SFX]
        self.bgm_own_volume = 1.0; self.bgm_category = 'musique'; self.t_pause = None   # volume propre a la musique en cours et sa categorie ; heure du debut de la pause (menu Echap)
        self.suspended = False; self.listening = False                         # menu Echap ouvert ; page Son du menu (les sons jouent pendant que le moteur est arrete)
        self.lock = threading.Lock(); self.zip = None; self.ogg = False
        try:
            import soundfile                                               # lecture des musiques (Ogg Vorbis) ; les bruitages n'en ont pas besoin
            self.ogg = True
        except Exception:
            self.log('Music unavailable: module "soundfile" missing (pip install soundfile). Sound effects stay active.')
        try:
            import pyglet
            from pyglet.media.codecs.base import AudioFormat, AudioData
            self.pyglet = pyglet; self.media = pyglet.media; self.AudioFormat = AudioFormat; self.AudioData = AudioData
            self.ok = True
        except Exception as e:
            self.log('Sound unavailable (%r)' % (e,))

    # ---- lecture des fichiers
    def _bytes(self, name_str):
        with self.lock:
            if self.zip is None: self.zip = zipfile.ZipFile(self.apk)
            try: return self.zip.read('assets/sound/%s.akb' % name_str)
            except KeyError: return None

    def _decode(self, name_str):
        f = os.path.join(self.cache, 'son_%s.npz' % name_str)
        try:
            if os.path.exists(f):
                z = np.load(f); return dict(pcm=z['pcm'], frequence=int(z['p'][0]), debut=int(z['p'][1]), fin=int(z['p'][2]), volume=float(z['v'][0]), boucle=bool(z['p'][3]))
        except Exception: pass
        d = self._bytes(name_str)
        if d is None: return None
        r = decode_akb(d)
        if r is not None and name_str.startswith('SE'):                        # les bruitages sont petits : cache disque (une musique longue, elle, prend plus d'une seconde : voir BGM_PRELOADED)
            try: np.savez(f, pcm=r['pcm'], p=np.array([r['frequence'], r['debut'], r['fin'], int(r['boucle'])], np.int64), v=np.array([r['volume']], np.float32))
            except Exception: pass
        return r

    def _get(self, name_str, callback, background=False):
        """Appelle rappel(donnees) : tout de suite si `name_str` est deja decode, sinon depuis tick() quand la tache de fond a fini."""
        if name_str in self.dec: self.dec.move_to_end(name_str); callback(self.dec[name_str]); return
        if name_str in self.jobs: self.jobs[name_str][1].append(callback); return
        self.jobs[name_str] = ((self.background_pool if background else self.pool).submit(self._decode_safe, name_str), [callback])

    def _decode_safe(self, name_str):
        try: return self._decode(name_str)
        except Exception as e:
            self.log('Sound: %s unreadable (%r)' % (name_str, e)); return None

    def preload(self, ids):
        """Decode en tache de fond les bruitages courants."""
        if not (self.ok and self.active): return
        for i in ids: self._get('SE%04d' % i, lambda r: None)

    def preload_music(self, ids=BGM_PRELOADED):
        """Musiques a decoder d'avance : une par image du jeu, seulement quand aucun autre decodage n'attend (la premiere musique du jeu passe donc la premiere) et une fois qu'une musique joue. Elles restent en memoire."""
        if not (self.ok and self.ogg): return                                # (meme son coupe au depart : le prechargement attend qu'une musique joue)
        for i in ids:
            name_str = 'BGM%02d' % i
            self.pinned.add(name_str)
            if name_str not in self.background: self.background.append(name_str)

    def _purge(self):
        """Cache de decodage : 80 sons (hors musiques epinglees) et 400 Mo au plus ; les plus anciennement utilises partent les premiers."""
        while True:
            free_keys = [k for k in self.dec if k not in self.pinned]
            if len(free_keys) <= 80 and sum(x['pcm'].nbytes for x in self.dec.values()) <= 400 * 2 ** 20: return
            if not free_keys: return
            del self.dec[free_keys[0]]

    # ---- appele a chaque image
    def tick(self):
        if not self.ok: return
        for name_str, (fut, callbacks) in list(self.jobs.items()):
            if not fut.done(): continue
            r = fut.result(); del self.jobs[name_str]
            if r is None: continue
            self.dec[name_str] = r; self._purge()
            for cb in callbacks: cb(r)
        if self.background and not self.jobs and self.bgm is not None:             # rien d'autre a decoder et une musique joue : on avance le prechargement d'une musique
            name_str = self.background.pop(0)
            if name_str not in self.dec: self._get(name_str, lambda r: None, background=True)
        now = time.time()
        self._release_orders(now)
        if self.resume is not None and self.bgm_end is not None and now >= self.bgm_end:       # Sound.SystemUpdate : le jingle est fini, la musique d'avant reprend
            n = self.resume; self.resume = None; self.bgm_end = None
            self.stop_bgm(); self.play_bgm(n)
        living = []
        for x in self.sfx:                                                  # un bruitage termine (ou depasse sa duree) est libere
            if now < x.end and (x.p.playing or now - x.begin < SFX_GRACE): living.append(x)
            else:
                try: x.p.delete()
                except Exception: pass
        self.sfx = living

    # ---- ordres du moteur
    def events(self, evts, engine_frame=None):
        """evts : [(type de paquet, valeur)] de l'image : 35 bruitage, 36 arret de bruitage, 37 musique. engine_frame : numero de la derniere image du moteur (30 par seconde a vitesse normale) :
        sert a ne pas couper un jingle quand le jeu tourne plus vite que la normale (voir _is_jingle_protected)."""
        if not (self.ok and self.active): return
        if os.environ.get('DQ_SON'): self.log('Sound: frame %s orders %s' % (getattr(self, 'image', '?'), evts))       # (test) journal des ordres du moteur
        for t, v in evts:
            if t == 35: self.play_sfx(v)
            elif t == 36: self.stop_sfx(v)
            elif t == 37: self._bgm_order(v, engine_frame)

    def _bgm_order(self, v, e):
        """Ordre de musique du moteur (image e) : appliques tout de suite, ou retenu tant qu'un jingle le meriterait (et derriere ceux qui attendent deja : l'ordre des ordres est garde)."""
        if self.bgm_queue or self._is_jingle_protected(e): self.bgm_queue.append((v, e))
        else: self._apply_order(v, e)

    def _apply_order(self, v, e):
        self.play_bgm(v); self.e_req = e

    def _is_jingle_protected(self, e):
        """Vrai si un jingle joue encore ET que l'ordre du moteur d'image e serait arrive apres lui a vitesse normale. Un combat accelere enchaine ses ordres (arret, reprise de la musique, ...) 2 a 3 fois plus tot : la fanfare etait coupee
        (montee de niveau, BGM 47 de 3,1 s : jouee 1,75 s a x3). L'ordre attend donc l'heure a laquelle il serait arrive a vitesse normale (image e - image de l'ordre qui a lance le jingle, a 30 par seconde) ou la fin du jingle, la premiere des deux."""
        if e is None or self.e_req is None or self.bgm is None or self.bgm_end is None or self.bgm_category != 'jingles' or self.bgm_t0 is None: return False
        if not self.mix.active.get('jingles', True): return False          # jingles coupes : rien a proteger
        return time.time() < min(self.bgm_end, self.bgm_t0 + (e - self.e_req) / ENGINE_FRAMES_PER_S)

    def _release_orders(self, now):
        """Ordres de musique retenus : appliques dans l'ordre des que le jingle n'a plus de raison de les retenir. Jingle fini et ordre suivant = un autre jingle (avec reprise) : la musique d'avant reprend d'abord, comme sans retard (Sound.SystemUpdate)."""
        if self.t_pause is not None: return
        while self.bgm_queue:
            v, e = self.bgm_queue[0]
            if self._is_jingle_protected(e): return
            if BGM_RESTART <= v < BGM_STOP and self.resume is not None and self.bgm_end is not None and now >= self.bgm_end:
                n = self.resume; self.resume = None; self.bgm_end = None; self.stop_bgm(); self.play_bgm(n)
            self.bgm_queue.popleft(); self._apply_order(v, e)

    def play_sfx(self, ident):
        if os.environ.get('DQ_SON'): self.log('Sound: frame %s sound effect %d' % (getattr(self, 'image', '?'), ident))
        name_str = 'SE%04d' % ident
        self._get(name_str, lambda r, i=ident: self._launch_sfx(i, r))

    def _launch_sfx(self, ident, r):
        try:
            fmt = self.AudioFormat(channels=r['pcm'].shape[1], sample_size=16, sample_rate=r['frequence'])
            looping = r['boucle']                                                            # bruitages en boucle (14 sur 634) : jusqu'a l'ordre d'arret du moteur (paquet 36)
            src = LoopSource(self.media, self.AudioData, fmt, r['pcm'], r['debut'] if looping else 0, r['fin'] if looping else 0)
            category = category_sfx(ident); g = self.mix.gain(category, r['volume'])
            if g <= 0.0 and not looping: return                                 # categorie coupee (ou volume a zero) : un bruitage court n'est pas joue ; un bruitage en boucle l'est a volume nul : il s'entend si on rouvre la categorie
            p = self.media.Player(); p.queue(src); p.volume = g; p.play()
            self.sfx.append(_SFX(ident, p, time.time() + (SFX_LOOP_MAX if looping else len(r['pcm']) / r['frequence'] + 0.5), category, r['volume']))
            if len(self.sfx) > 24:
                try: self.sfx[0].p.delete()
                except Exception: pass
                del self.sfx[0]
        except Exception as e:
            self.log('Sound: playback failed (%r)' % (e,)); self.ok = False

    def stop_sfx(self, ident):
        for x in list(self.sfx):
            if x.ident == ident:
                try: x.p.pause(); x.p.delete()
                except Exception: pass
        self.sfx = [x for x in self.sfx if x.ident != ident]

    def play_bgm(self, v, offset=0.0):
        if v >= BGM_STOP:                                         # cmd_bgm : >= 0x4000 = Sound.StopBGM
            self.resume = None; self.e_req = None; self.stop_bgm(); return
        if not self.ogg: return
        resume = None; restart = v >= BGM_RESTART
        if restart: v -= BGM_RESTART; resume = self.bgm_id                 # Sound.PlayBGM avec reprise : jingle, puis retour a la musique en cours
        elif v == self.bgm_id and self.bgm is not None: self.resume = None; return       # deja en cours
        else: self.resume = None
        self.stop_bgm(); self.bgm_id = v; self.bgm_request = v; self.resume = resume; self.bgm_end = None; self.bgm_offset = offset; self.e_req = None
        self._get('BGM%02d' % v, lambda r, i=v, rl=restart: self._launch_bgm(i, r, rl))

    def _launch_bgm(self, ident, r, restart=False):
        if self.bgm_request != ident: return                        # une autre musique a ete demandee entre-temps
        try:
            fmt = self.AudioFormat(channels=r['pcm'].shape[1], sample_size=16, sample_rate=r['frequence'])
            src = LoopSource(self.media, self.AudioData, fmt, r['pcm'], r['debut'], r['fin'] if r['boucle'] else 0)
            dec, self.bgm_offset = self.bgm_offset, 0.0
            if dec > 0: src.pos = min(int(dec * r['frequence']), max(0, len(r['pcm']) - 1))              # reprise au moment enregistre (etat charge)
            initial = src.pos / r['frequence']                                                                # (avant play : le lecteur lit tout de suite quelques secondes d'avance)
            category = category_bgm(restart, r['boucle'], len(r['pcm']) / r['frequence'])
            p = self.media.Player(); p.queue(src); p.volume = self.mix.gain(category, r['volume']); p.play()          # (la musique tourne meme coupee ou a zero : rouvrir la categorie la fait entendre au bon endroit)
            self.bgm = p; self.bgm_own_volume = r['volume']; self.bgm_category = category
            self.bgm_t0 = self.t_pause if self.t_pause is not None else time.time(); self.bgm_pos0 = initial
            if self.t_pause is not None: p.pause()
            self.bgm_end = None if r['boucle'] else self.bgm_t0 + len(r['pcm']) / r['frequence'] - initial       # jingle sans boucle : heure de la reprise de la musique d'avant
        except Exception as e:
            self.log('Sound: music failed (%r)' % (e,)); self.ok = False

    def position_bgm(self):
        """Position de lecture de la musique en cours (secondes dans le morceau, boucle comprise), ou None si rien ne joue."""
        r = self.dec.get('BGM%02d' % self.bgm_id) if self.bgm_id is not None else None
        if self.bgm is None or r is None or self.bgm_t0 is None: return None
        pos = self.bgm_pos0 + ((self.t_pause if self.t_pause is not None else time.time()) - self.bgm_t0)
        fr = r['frequence']; n = len(r['pcm']) / fr
        if r['boucle'] and r['fin'] > r['debut']:
            end, start_idx = r['fin'] / fr, r['debut'] / fr
            if pos >= end: pos = start_idx + (pos - end) % (end - start_idx)
        return min(max(pos, 0.0), max(n - 0.01, 0.0))

    def bgm_state(self):
        """Ce qu'il faut pour reprendre la musique au meme moment (etats enregistres) : {'id', 'pos', 'reprise'} ou None."""
        pos = self.position_bgm()
        return None if pos is None else {'id': self.bgm_id, 'pos': pos, 'reprise': self.resume}

    def restore_bgm(self, info, default=None):
        """Chargement d'un etat : la musique repart du moment enregistre (sans `info`, ancien etat : depuis le debut de `default`, la derniere commande du moteur)."""
        self.stop_bgm(); self.bgm_queue.clear()
        if info is None:
            if default is not None: self.play_bgm(default)
            return
        self.play_bgm(info['id'], float(info.get('pos') or 0.0)); self.resume = info.get('reprise')

    def stop_bgm(self):
        self.bgm_request = None; self.bgm_id = None
        if self.bgm is not None:
            try: self.bgm.pause(); self.bgm.delete()
            except Exception: pass
            self.bgm = None

    # anciens noms (volume de la musique / des bruitages) : conserves pour l'interface existante
    @property
    def vol_m(self): return self.mix.vol['musique']

    @property
    def vol_b(self): return self.mix.vol['effets']

    def set_mix(self, general=None, volumes=None, active_flags=None, game=None):
        """Menu Echap : nouveaux volumes / interrupteurs, appliques TOUT DE SUITE aux sons en cours (musique, jingle et bruitages deja lances).
        general : 0 a 1 ; volumes, actifs : {categorie: valeur} ; jeu : {'musique': facteur, 'effets': facteur} (options « volume » du jeu)."""
        m = self.mix
        if general is not None: m.general = float(general)
        for c, v in (volumes or {}).items():
            if c in m.vol: m.vol[c] = float(v)
        for c, v in (active_flags or {}).items():
            if c in m.active: m.active[c] = bool(v)
        for c, v in (game or {}).items():
            if c in m.game: m.game[c] = float(v)
        self._apply_volumes()

    def _apply_volumes(self):
        if self.bgm is not None:
            try: self.bgm.volume = self.mix.gain(self.bgm_category, self.bgm_own_volume)
            except Exception: pass
        for x in self.sfx:
            try: x.p.volume = self.mix.gain(x.category, x.own)
            except Exception: pass

    def set_volumes(self, music=None, sound_effects=None):
        """Compatibilite : volume de la musique et des bruitages (0 a 1)."""
        self.set_mix(volumes={k: v for k, v in (('musique', music), ('effets', sound_effects)) if v is not None})

    def set_paused(self, yes):
        """Menu Echap ouvert (oui) ou ferme : musique et bruitages en pause, sauf pendant l'ecoute (page Son du menu : on entend les reglages)."""
        self.suspended = bool(yes)
        if not yes: self.listening = False
        self._pause_audio_players(self.suspended and not self.listening)

    def listen(self, yes):
        """Page Son du menu Echap : les sons reprennent (la musique en cours, les bruitages d'essai) pour entendre les volumes qu'on regle ; a la sortie de la page, ils se remettent en pause."""
        self.listening = bool(yes)
        if self.suspended: self._pause_audio_players(not self.listening)

    def _pause_audio_players(self, yes):
        """Pause reelle des lecteurs ; a la reprise, les echeances (fin d'un jingle, d'un bruitage) sont decalees de la duree de la pause."""
        if yes == (self.t_pause is not None) or not self.ok: return
        if yes:
            self.t_pause = time.time()
            for p in [self.bgm] + [x.p for x in self.sfx]:
                try:
                    if p is not None: p.pause()
                except Exception: pass
        else:
            d = time.time() - self.t_pause; self.t_pause = None
            if self.bgm_t0 is not None: self.bgm_t0 += d
            if self.bgm_end is not None: self.bgm_end += d
            for x in self.sfx: x.end += d
            for p in [self.bgm] + [x.p for x in self.sfx]:
                try:
                    if p is not None: p.play()
                except Exception: pass

    def toggle(self):
        """Touche : son active / coupe."""
        self.active = not self.active
        if not self.active:
            self.stop_bgm(); self.bgm_queue.clear()
            for x in self.sfx:
                try: x.p.pause(); x.p.delete()
                except Exception: pass
            self.sfx = []
        return self.active

    def shutdown(self):
        for pool in (self.pool, self.background_pool):
            try: pool.shutdown(wait=False, cancel_futures=True)
            except Exception: pass
        self.stop_bgm()


def _source_class(media):
    class LoopSource(media.Source):
        """Musique avec boucle a l'echantillon pres (debut, fin) ; fin == 0 : jouee une seule fois."""
        def __init__(self, media_, audio_data, fmt, pcm, begin, end):
            super().__init__()
            self.audio_format = fmt; self.pcm = pcm; self.begin = begin; self.end = end; self.pos = 0; self._audio_data = audio_data

        def get_audio_data(self, num_bytes, compensation_time=0.0):
            oc = self.audio_format.bytes_per_frame
            n = max(1, num_bytes // oc); chunks = []; remaining = n; t0 = self.pos / self.audio_format.sample_rate
            while remaining > 0:
                limit = self.end if self.end and self.pos < self.end else len(self.pcm)
                k = min(remaining, limit - self.pos)
                if k <= 0:
                    if self.end: self.pos = self.begin; continue
                    break
                chunks.append(self.pcm[self.pos:self.pos + k]); self.pos += k; remaining -= k
                if self.end and self.pos >= self.end: self.pos = self.begin
            if not chunks: return None
            data = np.concatenate(chunks).tobytes()
            return self._audio_data(data, len(data), t0, len(data) / oc / self.audio_format.sample_rate)

        def seek(self, timestamp):
            self.pos = int(max(0.0, timestamp) * self.audio_format.sample_rate) % max(1, len(self.pcm))
    return LoopSource


class _Factory:
    def __call__(self, media, *a):
        global LoopSource
        return _source_class(media)(media, *a)


LoopSource = _Factory()
