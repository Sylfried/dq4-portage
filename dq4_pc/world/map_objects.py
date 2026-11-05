"""Objets animes des cartes de ville : portes qui s'ouvrent, jarres et tonneaux qui se brisent, coffres qui s'ouvrent, objets masques ou deplaces par le moteur.

Reproduit cote Python ce que fait la couche Unity du jeu (FldObject) a partir des paquets du moteur :
  * paquet 5 (cmd_fld_common_anim) : objet | numero << 16 -> SetCommonAnimation : la table d'animations communes de l'objet (FCAN, objet.canim)
    donne, pour chaque numero, le modele a afficher (porte, jarre intacte ou cassee...), une sequence de maillages (FSEQ/FSQD : le modele se deforme
    d'une image a l'autre, ex. la jarre qui eclate) et un mouvement (FPMV : position, rotation et echelle ajoutees a celles de l'objet, ex. battant de porte) ;
    numero 0 = modele d'origine, immobile ;
  * paquet 7 (cmd_fld_on_off) : objet | drapeau << 16 -> GameObject.SetActive(drapeau == 0) ;
  * paquet 2 (cmd_fld_alpha) : objet | niveau (0..31) << 16 ; niveau 0 = invisible ;
  * paquets 3 et 4 (cmd_fld_pos, cmd_fld_rot) : nouvelle position / rotation de l'objet.
Les temps sont en soixantiemes de seconde dans les donnees ; FldObject.Update avance de 2 par image du jeu (30 images/s).

Animations jouees en continu, sans ordre du moteur (FldObject.update_seq / update_pmv / update_plp) :
  * sequence de maillages (FMAP : seq_obj_id -> entree de FSEQ) : eau qui coule, lampes qui vacillent... Le maillage est interpole d'une image a l'autre
    (sommets, UV et couleurs : FldObject.seq_build_mesh) ; l'entree donne le delai de depart, le delai entre deux tours et le nombre de tours (-1 : sans fin) ;
  * mouvement (FMAP : pmv_id -> FPMV) : objets qui tournent, balancent...
  * palettes animees (FPLP / FPAM) : la texture d'une surface (eau scintillante, marais, sol qui fait mal) change d'image en image (classe MapPalettes).

Panneaux de decor (FldObject, drapeaux FLD_OBJ_FLAG_BILLBOARD_Y = 4 et FLD_OBJ_FLAG_BILLBOARD_XYZ = 32 : arbres, bougies, torches, tonneaux, chaises...) : un quadrilatere dont l'origine est le pied ;
il pivote autour de l'axe vertical (4) ou prend toute la rotation de la camera (32) pour rester de face. Les sommets sont cuits a l'orientation d'origine ; `orient` les recalcule
quand la camera tourne (touches de rotation de la camera, villes et donjons)."""
import math
import numpy as np
from dq4_pc.world.data import euler_mat

STEP = 2                      # FldObject.Update : s_seq_frame_rate_step = 2 par image


def _interp(lookup_keys, t):
    """TzKeys [(image, ...)] triees -> (indice avant, indice apres, fraction) a l'image t (tenue sur la derniere cle)."""
    if t >= lookup_keys[-1][0]: return len(lookup_keys) - 1, len(lookup_keys) - 1, 0.0
    for i in range(len(lookup_keys) - 1):
        f1, f2 = lookup_keys[i][0], lookup_keys[i + 1][0]
        if f1 <= t < f2: return i, i + 1, (t - f1) / float(f2 - f1)
    return 0, 0, 0.0


def _clock(delay, rdelai, rep, end):
    """ExampleCounter d'une animation (un FldObject.FLD_MOTION : cur_frame, start_delay, repeat_delay, repeat_num, end_frame) : chaque mouvement (FPMV) et chaque sequence de maillages (FSQD) a SON horloge,
    avec sa duree et son nombre de tours (fld_motion_update 0xCD69DC, appele une fois par motion). Deux animations d'un meme objet (ex. le rayon de soin : sequence de 84 images, rotation de 800) ne partagent rien."""
    return {'delai': delay, 'rdelai': rdelai, 'rep': rep, 'fin': end, 'temps': 0, 'fini': False}


def _advance(h):
    """Une image du jeu pour une horloge (FldObject.fld_motion_update) : delai de depart, puis le temps avance de STEP ; au-dela de la fin : un tour de moins (rep = -1 : sans fin), retour au debut
    (reste du depassement) apres le delai entre deux tours, ou arret sur la derniere cle quand les tours sont epuises."""
    if h['fini']: return
    if h['delai'] >= 1: h['delai'] -= STEP; h['temps'] = 0
    else:
        h['temps'] += STEP
        if h['temps'] > h['fin']:
            remainder = h['temps'] - h['fin']
            if h['rep'] >= 1: h['rep'] -= 1
            if h['rep'] == 0: h['temps'] = h['fin']; h['fini'] = True
            else: h['temps'] = remainder
            h['delai'] = h['rdelai']


def _migrate_auto(a):
    """Etat enregistre par une ancienne version : une seule horloge (celle de la sequence, sinon celle du mouvement) pour les deux animations de l'objet. Les deux horloges reprennent le temps
    enregistre (celle du mouvement a son propre modulo)."""
    if 'hs' in a or 'hm' in a: return a
    h = {k: a.get(k, d) for k, d in (('delai', 0), ('rdelai', 0), ('rep', -1), ('fin', 0), ('temps', 0), ('fini', False))}
    n = {'seq': a.get('seq'), 'mot': a.get('mot'), 'hs': None, 'hm': None}
    if n['seq'] is not None: n['hs'] = dict(h)
    if n['mot'] is not None:
        if n['seq'] is None: n['hm'] = dict(h)
        else:
            eng = n['mot']; n['hm'] = _clock(eng['delai'], eng['rdelai'], eng['repeat'], eng['fin'])
            if eng['fin'] > 0: n['hm']['temps'] = h['temps'] % eng['fin']
    return n


class MapObjects:
    def __init__(self, c):
        self.objs = c['objets']; self.spans = c.get('plages', {}); self.var = c.get('var', {}); self.tabs = c.get('tabs', [])
        self.words = c.get('mots', []); self.seqs = c.get('seqs', []); self.seqent = c.get('seqent', [])
        self.orig = c['groupes'] and {k: g[0] for k, g in c['groupes'].items()} or {}
        self.cur = {k: p.copy() for k, p in self.orig.items()}                      # positions affichees (modifiees sur place)
        self.var_of = {}                                                             # objet -> [modele, ...] des variantes
        for (i, m) in self.var: self.var_of.setdefault(i, []).append(m)
        for pl in (v['plages'] for v in self.var.values()):                        # variantes cachees tant qu'aucune animation ne les demande
            for key, d, n in pl: self.cur[key][d:d + n] = 0.0
        self.imgobj = c.get('imgobj', {})                                            # objet -> images (positions, UV, couleurs) de sa sequence de maillages, par sous-maillage
        self.uv0 = {k: g[1] for k, g in c['groupes'].items()}; self.col0 = {k: g[2] for k, g in c['groupes'].items()}
        self.cur_uv = {}; self.cur_col = {}                                          # UV et couleurs affichees : copies creees a la demande (groupes dont l'une ou l'autre change)
        self.dirty_uv = set(); self.dirty_col = set()
        self.state = {}; self.dirty = set(); self._inv = {}; self.auto = {}
        self.bill = {i: o['flag'] for i, o in enumerate(self.objs) if o.get('flag', 0) & 36 and self.valid(i)}     # panneaux de decor : objet -> drapeaux
        self.PITCH_DIRECTION = 1.0
        self._rb = {4: np.eye(3), 32: np.eye(3)}; self.bill_ok = False                  # orientation actuelle (autour de Y / camera complete) ; faux tant que les sommets ne la suivent pas
        self._o64 = {}; self._keys = {}; self._emat = {}                              # caches : position/rotation/echelle d'origine, cles des mouvements en tableaux, matrices de rotation
        self._init_seed()

    def reinit(self):
        """Nouveau chargement de la meme carte : tous les objets reprennent leur etat d'origine."""
        self.state = {}
        for k in self.cur: self.cur[k][:] = self.orig[k]
        for k in self.cur_uv: self.cur_uv[k][:] = self.uv0[k]
        for k in self.cur_col: self.cur_col[k][:] = self.col0[k]
        for pl in (v['plages'] for v in self.var.values()):
            for key, d, n in pl: self.cur[key][d:d + n] = 0.0
        self.dirty = set(self.cur); self.dirty_uv = set(self.cur_uv); self.dirty_col = set(self.cur_col); self.bill_ok = False
        self._init_seed()

    def _init_seed(self):
        """Animations de depart : sequences de maillages et mouvements des objets qui en ont une en continu (FMAP seq_obj_id / pmv_id). Chacune a sa propre horloge (voir `_clock`)."""
        self.auto = {}
        for i, o in enumerate(self.objs):
            if not self.valid(i): continue
            sq = eng = hs = hm = None; so = o.get('seqobj', -1)
            if 0 <= so < len(self.seqent) and i in self.imgobj:
                e = self.seqent[so]
                if 0 <= e[1] < len(self.seqs) and e[7] != 0 and self.seqs[e[1]]['keys'] and self.seqs[e[1]]['fin'] > 0:     # nombre de tours d'origine 0 : jamais lancee d'elle-meme
                    sq = self.seqs[e[1]]; hs = _clock(e[3], e[4], e[5], sq['fin'])
            mp = o.get('pmv', -1)
            if 0 <= mp < len(self.words) and self.words[mp]['keys'] and self.words[mp]['repeat'] != 0 and self.words[mp]['fin'] > 0:
                eng = self.words[mp]; hm = _clock(eng['delai'], eng['rdelai'], eng['repeat'], eng['fin'])
            if sq is None and eng is None: continue
            self.auto[i] = dict(seq=sq, mot=eng, hs=hs, hm=hm)
            st = self._st(i); st['seq'] = sq; st['mot'] = eng; st['temps'] = st['tseq'] = st['tmot'] = 0; self._place(i)

    def restore(self, state, auto=None):
        """Remet les objets dans un etat enregistre (etats instantanes) ; `auto` absent (ancien format) : animations en continu reprises au depart."""
        self.state = state
        if auto is not None: self.auto = {i: _migrate_auto(a) for i, a in auto.items()}
        for i, a in self.auto.items():
            st = self._st(i); st['seq'] = a['seq']; st['mot'] = a['mot']
        for i in list(self.state): self._place(i)
        self.dirty |= set(self.cur); self.dirty_uv |= set(self.cur_uv); self.dirty_col |= set(self.cur_col); self.bill_ok = False

    def orient(self, yaw, base, pitch=0.0):
        """Tourne les panneaux de decor vers la camera. `yaw` : cap de la camera (radians, 0 = vers +Z, positif vers +X) ; `base` : (droite, haut, avant) de la camera ; `pitch` : inclinaison ajoutee a la camera
        (degres, 0 = vue du jeu) : les panneaux qui ne tournent qu'autour de Y (tonneaux, jarres...) se penchent d'autant, pour rester de face a la camera quand on la releve ou l'abaisse. -> True si des sommets ont change."""
        if not self.bill: return False
        c, s = math.cos(yaw), math.sin(yaw)
        ry = np.array([[c, 0.0, s], [0.0, 1.0, 0.0], [-s, 0.0, c]])                      # Quaternion.Euler(0, lacet, 0)
        if pitch:
            a = math.radians(pitch) * self.PITCH_DIRECTION; ca, sa = math.cos(a), math.sin(a)
            ry = ry @ np.array([[1.0, 0.0, 0.0], [0.0, ca, -sa], [0.0, sa, ca]])         # puis penche autour de l'axe horizontal du panneau (son pied reste en place)
        rf = np.column_stack([np.asarray(b, np.float64) for b in base])                   # rotation complete de la camera (axes x, y, z de l'objet = droite, haut, avant)
        if self.bill_ok and np.allclose(ry, self._rb[4], atol=1e-5) and np.allclose(rf, self._rb[32], atol=1e-5): return False
        self._rb = {4: ry, 32: rf}; self.bill_ok = True
        for i in self.bill: self._place(i)
        return True

    def uv(self, key): return self.cur_uv.get(key, self.uv0[key])

    def col(self, key): return self.cur_col.get(key, self.col0[key])

    def _array_copy(self, tab, orig, key):
        if key not in tab: tab[key] = orig[key].copy()
        return tab[key]

    # ---- commandes du moteur
    def _st(self, i):
        o = self.objs[i]
        return self.state.setdefault(i, {'mdl': o['mdl'], 'off': False, 'alpha': 31, 'pos': None, 'rot': None, 'mot': None, 'seq': None, 'temps': 0, 'tmot': 0, 'tseq': 0})

    def valid(self, i):
        return 0 <= i < len(self.objs) and (i in self.spans or i in self.var_of)

    def common_anim(self, i, no):
        if not self.valid(i): return
        o = self.objs[i]; st = self._st(i)
        self.auto.pop(i, None); st['mot'] = st['seq'] = None; st['temps'] = st['tmot'] = st['tseq'] = 0; st['fini'] = False
        if no <= 0: st['mdl'] = o['mdl']
        else:
            tab = self.tabs[o['canim']] if 0 <= o['canim'] < len(self.tabs) else []
            if no > len(tab): return
            m, sq, mp = tab[no - 1]; st['mdl'] = m
            if 0 <= mp < len(self.words): st['mot'] = self.words[mp]
            if 0 <= sq < len(self.seqent) and 0 <= self.seqent[sq][1] < len(self.seqs): st['seq'] = self.seqs[self.seqent[sq][1]]
        self._place(i)

    def duration(self, i, no):
        """Images du jeu pendant lesquelles le moteur doit attendre la fin de l'animation, ou None si l'objet n'a pas cette animation."""
        if not 0 <= i < len(self.objs): return None
        o = self.objs[i]; tab = self.tabs[o['canim']] if 0 <= o['canim'] < len(self.tabs) else []
        if not 1 <= no <= len(tab): return None
        m, sq, mp = tab[no - 1]; end = 0
        if 0 <= mp < len(self.words): end = max(end, self.words[mp]['fin'])
        if 0 <= sq < len(self.seqent) and 0 <= self.seqent[sq][1] < len(self.seqs): end = max(end, self.seqs[self.seqent[sq][1]]['fin'])
        return max(1, -(-end // STEP)) + 1

    def on_off(self, i, flag):
        if self.valid(i): self._st(i)['off'] = flag != 0; self._place(i)

    def alpha(self, i, level):
        if self.valid(i): self._st(i)['alpha'] = level; self._place(i)

    def position(self, i, p):
        if self.valid(i): self._st(i)['pos'] = tuple(p); self._place(i)

    def rotation(self, i, r):
        if self.valid(i): self._st(i)['rot'] = tuple(r); self._place(i)

    # ---- images
    def tick(self):
        """Une image du jeu : avance les mouvements et les sequences en cours. -> ensemble des groupes modifies depuis le dernier appel."""
        for i, a in self.auto.items():                      # animations en continu : delai de depart, tours, delai entre deux tours (FldObject.fld_motion_update), une horloge par animation
            if i not in self.state: continue
            st = self.state[i]; alive = False
            for h, lookup_key in ((a.get('hs'), 'tseq'), (a.get('hm'), 'tmot')):
                if h is None or h['fini']: continue
                _advance(h); st[lookup_key] = h['temps']; alive = True
            if alive: self._place(i)
        for i, st in self.state.items():
            if i in self.auto: continue
            if st.get('fini'): continue
            if not (st['mot'] or st['seq']): continue
            for x, lookup_key in ((st['mot'], 'tmot'), (st['seq'], 'tseq')):         # animation commune : chaque mouvement et chaque sequence compte son propre temps (FldObject.fld_motion_update : repetition, repeat = -1 : sans fin, sinon tenue sur la derniere cle)
                if not x: continue
                t = st.get(lookup_key, st['temps']) + STEP
                if t > x['fin'] and x['repeat'] == -1 and x['fin'] > 0: t -= x['fin']
                st[lookup_key] = t
            if all(st[lookup_key] >= x['fin'] and x['repeat'] != -1 for x, lookup_key in ((st['mot'], 'tmot'), (st['seq'], 'tseq')) if x): st['fini'] = True
            self._place(i)
        s = self.dirty; self.dirty = set(); return s

    def _origin(self, i):
        r = self._o64.get(i)
        if r is None:
            o = self.objs[i]; r = self._o64[i] = (np.array(o['pos'], np.float64), np.array(o['rot'], np.float64), np.array(o['scl'], np.float64))
        return r

    def _motion_keys(self, word):
        """Positions, rotations et echelles des cles d'un mouvement, en tableaux (n, 3)."""
        r = self._keys.get(id(word))
        if r is None or r[0] is not word:                                           # (l'identite est verifiee : un numero libere pourrait etre reutilise)
            ks = word['keys']; r = self._keys[id(word)] = (word,) + tuple(np.array([k[j] for k in ks], np.float64) for j in (1, 2, 3))
        return r[1:]

    def _rot(self, rot):
        k = (float(rot[0]), float(rot[1]), float(rot[2])); m = self._emat.get(k)
        if m is None:
            if len(self._emat) > 20000: self._emat.clear()
            m = self._emat[k] = euler_mat(*k)
        return m

    def _matrix(self, i):
        if i not in self._inv:
            o = self.objs[i]; S = np.diag(o['scl']).astype(np.float64)
            try: A = np.linalg.inv(euler_mat(*o['rot']) @ S)
            except np.linalg.LinAlgError: A = np.eye(3)
            self._inv[i] = A
        return self._inv[i]

    def _place(self, i):
        o = self.objs[i]; st = self._st(i)
        base = [(None, self.spans.get(i, []), self.imgobj.get(i))]
        for m in self.var_of.get(i, []): base.append((m, self.var[(i, m)]['plages'], self.var[(i, m)]['images']))
        pos0, rot0, scl0 = self._origin(i); pos, rot, scl = pos0, rot0, scl0
        if st['pos'] is not None: pos = np.array(st['pos'], np.float64)
        if st['rot'] is not None: rot = np.array([st['rot'][0], st['rot'][1], 0.0], np.float64)
        word = st['mot']; t = st.get('tmot', st['temps'])                                  # (etat d'une ancienne version : une seule horloge)
        if word is not None and word['keys']:
            a, b, f = _interp(word['keys'], t); cp, cr, cs = self._motion_keys(word)
            dp = cp[a] if a == b or f == 0.0 else cp[a] * (1 - f) + cp[b] * f
            if word['flag'] & 4: pos = pos + self._rot(rot) @ (scl * dp)                      # mouvement commun (FldObject.c_pmv_func) : le deplacement est lu dans le repere de l'objet, MultiplyPoint(TRS(position, rotateXZY(rotation), echelle)) de l'objet avant le mouvement (tiroir qui sort de SON meuble, quel que soit son cap)
            else: pos = pos + dp                                                              # mouvement ordinaire (FldObject.pmv_func) : le deplacement s'ajoute tel quel
            rot = rot + (cr[a] if a == b or f == 0.0 else cr[a] * (1 - f) + cr[b] * f)
            scl = scl * (cs[a] if a == b or f == 0.0 else cs[a] * (1 - f) + cs[b] * f)
        panel = self.bill.get(i) if self.bill_ok else None
        identity = st['pos'] is None and st['rot'] is None and word is None and panel is None       # le modele reste a sa place d'origine
        if not identity:
            R = self._rot(rot) if panel is None else self._rb[32 if panel & 32 else 4] @ self._rot(rot - rot0)       # panneau : l'orientation vient de la camera (le reste du mouvement s'y ajoute)
            T = R @ (scl[:, None] * self._matrix(i))                                    # monde d'origine -> monde actuel : (v - pos0) -> T, puis + pos  (= R . diag(scl) . inv(R0 . diag(scl0)))
        for m, spans, frames in base:
            alive = (m is None and st['mdl'] == o['mdl']) or (m is not None and st['mdl'] == m)
            alive = alive and not st['off'] and st['alpha'] > 0
            for k, (key, d, n) in enumerate(spans):
                img = frames[k] if frames else None
                if not alive: v = np.zeros((n, 3), np.float32)
                else:
                    src, uv, col = self._src_seq(key, d, n, img, st)
                    v = src if identity else ((src.astype(np.float64) - pos0) @ T.T + pos).astype(np.float32)
                    if img is not None:                                                  # UV et couleurs qui changent d'une image a l'autre de la sequence
                        if img['uv'] is not None: self._array_copy(self.cur_uv, self.uv0, key)[d:d + n] = self.uv0[key][d:d + n] if uv is None else uv; self.dirty_uv.add(key)
                        if img['col'] is not None: self._array_copy(self.cur_col, self.col0, key)[d:d + n] = self.col0[key][d:d + n] if col is None else col; self.dirty_col.add(key)
                self.cur[key][d:d + n] = v; self.dirty.add(key)

    def _src_seq(self, key, d, n, img, st):
        """(sommets, UV, couleurs) d'un sous-maillage : d'origine (UV et couleurs None), ou interpoles par la sequence de maillages en cours (FldObject.seq_build_mesh : entre les images
        des deux cles autour de l'image courante ; la valeur d'une cle est le numero de l'enfant du modele)."""
        seq = st['seq']
        if seq is None or img is None or not seq['keys']: return self.orig[key][d:d + n], None, None
        a, b, f = _interp(seq['keys'], st.get('tseq', st['temps'])); n_img = len(img['pos'])
        va = min(max(seq['keys'][a][1], 0), n_img - 1); vb = min(max(seq['keys'][b][1], 0), n_img - 1)
        mix = lambda x: None if x is None else (x[va] if va == vb or f == 0.0 else x[va] * (1 - f) + x[vb] * f)
        return mix(img['pos']), mix(img['uv']), mix(img['col'])


class MapPalettes:
    """Palettes animees de la carte (FldObject.update_plp) : chaque animation (FPAM) enchaine ses cles ; la duree d'une cle est en 1/60 s, comptee par pas de 2 par image du jeu.
    Les surfaces concernees (groupes de texture 'pam', voir Data.carte) prennent la texture de la cle courante. Animation liee a un evenement (numero >= 1) : image 0 tant que l'evenement n'est pas en cours."""

    def __init__(self, c):
        self.defs = c.get('pamdef', {})
        self.pams = [{'frame': p['frame'], 'cle': p['cle'], 'durees': p['durees']} for p in c.get('pam', [])]

    def tick(self):
        """Une image du jeu."""
        for p in self.pams:
            d = p['durees']
            if not d: continue
            p['frame'] += STEP
            if p['frame'] - d[min(p['cle'], len(d) - 1)] >= 0:
                p['frame'] -= d[min(p['cle'], len(d) - 1)]; p['cle'] = 0 if len(d) <= p['cle'] + 1 else p['cle'] + 1

    def image(self, key, event_code=0):
        """Numero de l'image (texture) courante du groupe `key`."""
        dd = self.defs[key]
        if dd['evenement'] >= 1 and dd['evenement'] != event_code: return 0
        p = self.pams[dd['pam']]
        return min(max(p['cle'], 0), len(dd['images']) - 1)

    def state(self): return [(p['frame'], p['cle']) for p in self.pams]

    def select_language(self, state):
        for p, (f, k) in zip(self.pams, state): p['frame'] = f; p['cle'] = k
