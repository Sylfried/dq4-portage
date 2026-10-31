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


def decoder_akb(d):
    """Fichier AKB -> dict (pcm int16 (n, canaux), frequence, debut, fin, volume) ou None."""
    h = lire_entete(d)
    if h is None: return None
    if h['codec'] == 2:
        pcm = decoder_msadpcm(d[DEBUT_DONNEES + 4:], h['canaux'], h['bloc'] or 512)
    elif h['codec'] == 5:
        import soundfile as sf
        pcm, _ = sf.read(io.BytesIO(d[DEBUT_DONNEES:]), dtype='int16', always_2d=True)
    else:
        return None
    n = len(pcm)
    deb, fin = h['debut'], h['fin']
    boucle = 0 < fin <= n and deb < fin
    return dict(pcm=np.ascontiguousarray(pcm), frequence=h['frequence'], debut=deb if boucle else 0, fin=fin if boucle else 0, volume=h['volume'], boucle=boucle)


BGM_RELANCE = 0x1000        # cmd_bgm : valeur >= 0x1000 = Sound.PlayBGM(valeur - 0x1000) avec reprise : la musique en cours est memorisee et reprise (depuis le debut) quand ce morceau est fini (jingle)
BGM_ARRET = 0x4000           # valeur >= 0x4000 = Sound.StopBGM (SoundManager::stopBgm envoie 0x4000 | duree, battleStop 0x4008) ; la duree est ignoree par Unity (arret immediat)
SE_BOUCLE_MAX = 120.0        # secondes : un bruitage en boucle dont le moteur n'enverrait jamais l'arret est coupe


class Son:
    """Lecture : une musique a la fois (avec boucle), des bruitages en parallele. Le decodage se fait en tache de fond."""
    def __init__(self, apk, cache, log=print, volume_musique=1.0, volume_bruitages=1.0, actif=True):
        self.apk, self.cache, self.log = apk, cache, log
        self.vol_m, self.vol_b = volume_musique, volume_bruitages
        self.actif = actif; self.ok = False
        self.pool = ThreadPoolExecutor(max_workers=1)
        self.dec = collections.OrderedDict(); self.jobs = {}
        self.bgm = None; self.bgm_id = None; self.bgm_demande = None
        self.reprise = None; self.bgm_fin = None                           # jingle : musique a reprendre, heure de fin du jingle
        self.se = []                                                       # [(id, Player)]
        self.bgm_propre = 1.0; self.t_pause = None                          # volume propre a la musique en cours ; heure du debut de la pause (menu Echap)
        self.verrou = threading.Lock(); self.zip = None; self.ogg = False
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
                z = np.load(f); return dict(pcm=z['pcm'], frequence=int(z['p'][0]), debut=int(z['p'][1]), fin=int(z['p'][2]), volume=float(z['v'][0]), boucle=bool(z['p'][3]))
        except Exception: pass
        d = self._octets(nom)
        if d is None: return None
        r = decoder_akb(d)
        if r is not None and nom.startswith('SE'):                        # les bruitages sont petits : cache disque (les musiques se decodent en une fraction de seconde)
            try: np.savez(f, pcm=r['pcm'], p=np.array([r['frequence'], r['debut'], r['fin'], int(r['boucle'])], np.int64), v=np.array([r['volume']], np.float32))
            except Exception: pass
        return r

    def _obtenir(self, nom, rappel):
        """Appelle rappel(donnees) : tout de suite si `nom` est deja decode, sinon depuis tick() quand la tache de fond a fini."""
        if nom in self.dec: self.dec.move_to_end(nom); rappel(self.dec[nom]); return
        if nom in self.jobs: self.jobs[nom][1].append(rappel); return
        self.jobs[nom] = (self.pool.submit(self._decode_sur, nom), [rappel])

    def _decode_sur(self, nom):
        try: return self._decode(nom)
        except Exception as e:
            self.log('Son : %s illisible (%r)' % (nom, e)); return None

    def precharger(self, ids):
        """Decode en tache de fond les bruitages courants."""
        if not (self.ok and self.actif): return
        for i in ids: self._obtenir('SE%04d' % i, lambda r: None)

    # ---- appele a chaque image
    def tick(self):
        if not self.ok: return
        for nom, (fut, rappels) in list(self.jobs.items()):
            if not fut.done(): continue
            r = fut.result(); del self.jobs[nom]
            if r is None: continue
            self.dec[nom] = r
            while len(self.dec) > 80 or sum(x['pcm'].nbytes for x in self.dec.values()) > 400 * 2 ** 20: self.dec.popitem(last=False)
            for cb in rappels: cb(r)
        maintenant = time.time()
        if self.reprise is not None and self.bgm_fin is not None and maintenant >= self.bgm_fin:       # Sound.SystemUpdate : le jingle est fini, la musique d'avant reprend
            n = self.reprise; self.reprise = None; self.bgm_fin = None
            self.arreter_bgm(); self.jouer_bgm(n)
        vivants = []
        for i, p, fin in self.se:                                          # un bruitage termine (ou depasse sa duree) est libere
            if maintenant < fin and p.playing: vivants.append((i, p, fin))
            else:
                try: p.delete()
                except Exception: pass
        self.se = vivants

    # ---- ordres du moteur
    def evenements(self, evts):
        """evts : [(type de paquet, valeur)] de l'image : 35 bruitage, 36 arret de bruitage, 37 musique."""
        if not (self.ok and self.actif): return
        if os.environ.get('DQ_SON'): self.log('Son : image %s ordres %s' % (getattr(self, 'image', '?'), evts))       # (test) journal des ordres du moteur
        for t, v in evts:
            if t == 35: self.jouer_se(v)
            elif t == 36: self.arreter_se(v)
            elif t == 37: self.jouer_bgm(v)

    def jouer_se(self, ident):
        if os.environ.get('DQ_SON'): self.log('Son : image %s bruitage %d' % (getattr(self, 'image', '?'), ident))
        nom = 'SE%04d' % ident
        self._obtenir(nom, lambda r, i=ident: self._lancer_se(i, r))

    def _lancer_se(self, ident, r):
        try:
            fmt = self.AudioFormat(channels=r['pcm'].shape[1], sample_size=16, sample_rate=r['frequence'])
            boucle = r['boucle']                                                            # bruitages en boucle (14 sur 634) : jusqu'a l'ordre d'arret du moteur (paquet 36)
            src = SourceBoucle(self.media, self.AudioData, fmt, r['pcm'], r['debut'] if boucle else 0, r['fin'] if boucle else 0)
            p = self.media.Player(); p.queue(src); p.volume = max(0.0, min(1.0, self.vol_b * r['volume'])); p.play()
            self.se.append((ident, p, time.time() + (SE_BOUCLE_MAX if boucle else len(r['pcm']) / r['frequence'] + 0.5)))
            if len(self.se) > 24:
                try: self.se[0][1].delete()
                except Exception: pass
                del self.se[0]
        except Exception as e:
            self.log('Son : lecture impossible (%r)' % (e,)); self.ok = False

    def arreter_se(self, ident):
        for i, p, _ in list(self.se):
            if i == ident:
                try: p.pause(); p.delete()
                except Exception: pass
        self.se = [x for x in self.se if x[0] != ident]

    def jouer_bgm(self, v):
        if v >= BGM_ARRET:                                         # cmd_bgm : >= 0x4000 = Sound.StopBGM
            self.reprise = None; self.arreter_bgm(); return
        if not self.ogg: return
        reprise = None
        if v >= BGM_RELANCE: v -= BGM_RELANCE; reprise = self.bgm_id        # Sound.PlayBGM avec reprise : jingle, puis retour a la musique en cours
        elif v == self.bgm_id and self.bgm is not None: self.reprise = None; return       # deja en cours
        else: self.reprise = None
        self.arreter_bgm(); self.bgm_id = v; self.bgm_demande = v; self.reprise = reprise; self.bgm_fin = None
        self._obtenir('BGM%02d' % v, lambda r, i=v: self._lancer_bgm(i, r))

    def _lancer_bgm(self, ident, r):
        if self.bgm_demande != ident: return                        # une autre musique a ete demandee entre-temps
        try:
            fmt = self.AudioFormat(channels=r['pcm'].shape[1], sample_size=16, sample_rate=r['frequence'])
            src = SourceBoucle(self.media, self.AudioData, fmt, r['pcm'], r['debut'], r['fin'] if r['boucle'] else 0)
            p = self.media.Player(); p.queue(src); p.volume = max(0.0, min(1.0, self.vol_m * r['volume'])); p.play()
            self.bgm = p; self.bgm_propre = r['volume']
            if self.t_pause is not None: p.pause()
            self.bgm_fin = None if r['boucle'] else time.time() + len(r['pcm']) / r['frequence']       # jingle sans boucle : heure de la reprise de la musique d'avant
        except Exception as e:
            self.log('Son : musique impossible (%r)' % (e,)); self.ok = False

    def arreter_bgm(self):
        self.bgm_demande = None; self.bgm_id = None
        if self.bgm is not None:
            try: self.bgm.pause(); self.bgm.delete()
            except Exception: pass
            self.bgm = None

    def regler_volumes(self, musique=None, bruitages=None):
        """Menu Echap : nouveaux volumes (0 a 1) ; la musique en cours change tout de suite, les bruitages a partir du suivant."""
        if musique is not None:
            self.vol_m = float(musique)
            if self.bgm is not None:
                try: self.bgm.volume = max(0.0, min(1.0, self.vol_m * self.bgm_propre))
                except Exception: pass
        if bruitages is not None: self.vol_b = float(bruitages)

    def mettre_en_pause(self, oui):
        """Menu Echap ouvert : musique et bruitages en pause ; a la reprise, les echeances (fin d'un jingle, d'un bruitage) sont decalees de la duree de la pause."""
        if oui == (self.t_pause is not None) or not self.ok: return
        if oui:
            self.t_pause = time.time()
            for p in [self.bgm] + [x[1] for x in self.se]:
                try:
                    if p is not None: p.pause()
                except Exception: pass
        else:
            d = time.time() - self.t_pause; self.t_pause = None
            if self.bgm_fin is not None: self.bgm_fin += d
            self.se = [(i, p, fin + d) for i, p, fin in self.se]
            for p in [self.bgm] + [x[1] for x in self.se]:
                try:
                    if p is not None: p.play()
                except Exception: pass

    def basculer(self):
        """Touche : son active / coupe."""
        self.actif = not self.actif
        if not self.actif:
            self.arreter_bgm()
            for _, p, _ in self.se:
                try: p.pause(); p.delete()
                except Exception: pass
            self.se = []
        return self.actif

    def fermer(self):
        try: self.pool.shutdown(wait=False, cancel_futures=True)
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
        global SourceBoucle
        return _classe_source(media)(media, *a)


SourceBoucle = _Fabrique()
