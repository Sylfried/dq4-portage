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
  * palettes animees (FPLP / FPAM) : la texture d'une surface (eau scintillante, marais, sol qui fait mal) change d'image en image (classe PalettesCarte).

Panneaux de decor (FldObject, drapeaux FLD_OBJ_FLAG_BILLBOARD_Y = 4 et FLD_OBJ_FLAG_BILLBOARD_XYZ = 32 : arbres, bougies, torches, tonneaux, chaises...) : un quadrilatere dont l'origine est le pied ;
il pivote autour de l'axe vertical (4) ou prend toute la rotation de la camera (32) pour rester de face. Les sommets sont cuits a l'orientation d'origine ; `orienter` les recalcule
quand la camera tourne (touches de rotation de la camera, villes et donjons)."""
import math
import numpy as np
from donnees import euler_mat

PAS = 2                      # FldObject.Update : s_seq_frame_rate_step = 2 par image


def _interp(cles, t):
    """Cles [(image, ...)] triees -> (indice avant, indice apres, fraction) a l'image t (tenue sur la derniere cle)."""
    if t >= cles[-1][0]: return len(cles) - 1, len(cles) - 1, 0.0
    for i in range(len(cles) - 1):
        f1, f2 = cles[i][0], cles[i + 1][0]
        if f1 <= t < f2: return i, i + 1, (t - f1) / float(f2 - f1)
    return 0, 0, 0.0


class ObjetsCarte:
    def __init__(self, c):
        self.objs = c['objets']; self.plages = c.get('plages', {}); self.var = c.get('var', {}); self.tabs = c.get('tabs', [])
        self.mots = c.get('mots', []); self.seqs = c.get('seqs', []); self.seqent = c.get('seqent', [])
        self.orig = c['groupes'] and {k: g[0] for k, g in c['groupes'].items()} or {}
        self.cur = {k: p.copy() for k, p in self.orig.items()}                      # positions affichees (modifiees sur place)
        self.var_de = {}                                                             # objet -> [modele, ...] des variantes
        for (i, m) in self.var: self.var_de.setdefault(i, []).append(m)
        for pl in (v['plages'] for v in self.var.values()):                        # variantes cachees tant qu'aucune animation ne les demande
            for key, d, n in pl: self.cur[key][d:d + n] = 0.0
        self.imgobj = c.get('imgobj', {})                                            # objet -> images (positions, UV, couleurs) de sa sequence de maillages, par sous-maillage
        self.uv0 = {k: g[1] for k, g in c['groupes'].items()}; self.col0 = {k: g[2] for k, g in c['groupes'].items()}
        self.cur_uv = {}; self.cur_col = {}                                          # UV et couleurs affichees : copies creees a la demande (groupes dont l'une ou l'autre change)
        self.sale_uv = set(); self.sale_col = set()
        self.etat = {}; self.sale = set(); self._inv = {}; self.auto = {}
        self.bill = {i: o['flag'] for i, o in enumerate(self.objs) if o.get('flag', 0) & 36 and self.valide(i)}     # panneaux de decor : objet -> drapeaux
        self.SENS_TANGAGE = 1.0
        self._rb = {4: np.eye(3), 32: np.eye(3)}; self.bill_ok = False                  # orientation actuelle (autour de Y / camera complete) ; faux tant que les sommets ne la suivent pas
        self._o64 = {}; self._cles = {}; self._emat = {}                              # caches : position/rotation/echelle d'origine, cles des mouvements en tableaux, matrices de rotation
        self._semer()

    def reinit(self):
        """Nouveau chargement de la meme carte : tous les objets reprennent leur etat d'origine."""
        self.etat = {}
        for k in self.cur: self.cur[k][:] = self.orig[k]
        for k in self.cur_uv: self.cur_uv[k][:] = self.uv0[k]
        for k in self.cur_col: self.cur_col[k][:] = self.col0[k]
        for pl in (v['plages'] for v in self.var.values()):
            for key, d, n in pl: self.cur[key][d:d + n] = 0.0
        self.sale = set(self.cur); self.sale_uv = set(self.cur_uv); self.sale_col = set(self.cur_col); self.bill_ok = False
        self._semer()

    def _semer(self):
        """Animations de depart : sequences de maillages et mouvements des objets qui en ont une en continu (FMAP seq_obj_id / pmv_id)."""
        self.auto = {}
        for i, o in enumerate(self.objs):
            if not self.valide(i): continue
            a = None; so = o.get('seqobj', -1)
            if 0 <= so < len(self.seqent) and i in self.imgobj:
                e = self.seqent[so]
                if 0 <= e[1] < len(self.seqs) and e[7] != 0 and self.seqs[e[1]]['keys'] and self.seqs[e[1]]['fin'] > 0:     # nombre de tours d'origine 0 : jamais lancee d'elle-meme
                    sq = self.seqs[e[1]]; a = dict(seq=sq, mot=None, delai=e[3], rdelai=e[4], rep=e[5], fin=sq['fin'])
            pm = o.get('pmv', -1)
            if 0 <= pm < len(self.mots) and self.mots[pm]['keys'] and self.mots[pm]['repeat'] != 0 and self.mots[pm]['fin'] > 0:
                mo = self.mots[pm]
                if a is None: a = dict(seq=None, mot=mo, delai=mo['delai'], rdelai=mo['rdelai'], rep=mo['repeat'], fin=mo['fin'])
                else: a['mot'] = mo
            if a is None: continue
            a['temps'] = 0; a['fini'] = False; self.auto[i] = a
            st = self._st(i); st['seq'] = a['seq']; st['mot'] = a['mot']; self._poser(i)

    def restaurer(self, etat, auto=None):
        """Remet les objets dans un etat enregistre (etats instantanes) ; `auto` absent (ancien format) : animations en continu reprises au depart."""
        self.etat = etat
        if auto is not None: self.auto = auto
        for i, a in self.auto.items():
            st = self._st(i); st['seq'] = a['seq']; st['mot'] = a['mot']
        for i in list(self.etat): self._poser(i)
        self.sale |= set(self.cur); self.sale_uv |= set(self.cur_uv); self.sale_col |= set(self.cur_col); self.bill_ok = False

    def orienter(self, lacet, base, tangage=0.0):
        """Tourne les panneaux de decor vers la camera. `lacet` : cap de la camera (radians, 0 = vers +Z, positif vers +X) ; `base` : (droite, haut, avant) de la camera ; `tangage` : inclinaison ajoutee a la camera
        (degres, 0 = vue du jeu) : les panneaux qui ne tournent qu'autour de Y (tonneaux, jarres...) se penchent d'autant, pour rester de face a la camera quand on la releve ou l'abaisse. -> True si des sommets ont change."""
        if not self.bill: return False
        c, s = math.cos(lacet), math.sin(lacet)
        ry = np.array([[c, 0.0, s], [0.0, 1.0, 0.0], [-s, 0.0, c]])                      # Quaternion.Euler(0, lacet, 0)
        if tangage:
            a = math.radians(tangage) * self.SENS_TANGAGE; ca, sa = math.cos(a), math.sin(a)
            ry = ry @ np.array([[1.0, 0.0, 0.0], [0.0, ca, -sa], [0.0, sa, ca]])         # puis penche autour de l'axe horizontal du panneau (son pied reste en place)
        rf = np.column_stack([np.asarray(b, np.float64) for b in base])                   # rotation complete de la camera (axes x, y, z de l'objet = droite, haut, avant)
        if self.bill_ok and np.allclose(ry, self._rb[4], atol=1e-5) and np.allclose(rf, self._rb[32], atol=1e-5): return False
        self._rb = {4: ry, 32: rf}; self.bill_ok = True
        for i in self.bill: self._poser(i)
        return True

    def uv(self, key): return self.cur_uv.get(key, self.uv0[key])

    def col(self, key): return self.cur_col.get(key, self.col0[key])

    def _tableau(self, tab, orig, key):
        if key not in tab: tab[key] = orig[key].copy()
        return tab[key]

    # ---- commandes du moteur
    def _st(self, i):
        o = self.objs[i]
        return self.etat.setdefault(i, {'mdl': o['mdl'], 'off': False, 'alpha': 31, 'pos': None, 'rot': None, 'mot': None, 'seq': None, 'temps': 0})

    def valide(self, i):
        return 0 <= i < len(self.objs) and (i in self.plages or i in self.var_de)

    def anim_commune(self, i, no):
        if not self.valide(i): return
        o = self.objs[i]; st = self._st(i)
        self.auto.pop(i, None); st['mot'] = st['seq'] = None; st['temps'] = 0; st['fini'] = False
        if no <= 0: st['mdl'] = o['mdl']
        else:
            tab = self.tabs[o['canim']] if 0 <= o['canim'] < len(self.tabs) else []
            if no > len(tab): return
            m, sq, pm = tab[no - 1]; st['mdl'] = m
            if 0 <= pm < len(self.mots): st['mot'] = self.mots[pm]
            if 0 <= sq < len(self.seqent) and 0 <= self.seqent[sq][1] < len(self.seqs): st['seq'] = self.seqs[self.seqent[sq][1]]
        self._poser(i)

    def duree(self, i, no):
        """Images du jeu pendant lesquelles le moteur doit attendre la fin de l'animation, ou None si l'objet n'a pas cette animation."""
        if not 0 <= i < len(self.objs): return None
        o = self.objs[i]; tab = self.tabs[o['canim']] if 0 <= o['canim'] < len(self.tabs) else []
        if not 1 <= no <= len(tab): return None
        m, sq, pm = tab[no - 1]; fin = 0
        if 0 <= pm < len(self.mots): fin = max(fin, self.mots[pm]['fin'])
        if 0 <= sq < len(self.seqent) and 0 <= self.seqent[sq][1] < len(self.seqs): fin = max(fin, self.seqs[self.seqent[sq][1]]['fin'])
        return max(1, -(-fin // PAS)) + 1

    def on_off(self, i, drapeau):
        if self.valide(i): self._st(i)['off'] = drapeau != 0; self._poser(i)

    def alpha(self, i, niveau):
        if self.valide(i): self._st(i)['alpha'] = niveau; self._poser(i)

    def position(self, i, p):
        if self.valide(i): self._st(i)['pos'] = tuple(p); self._poser(i)

    def rotation(self, i, r):
        if self.valide(i): self._st(i)['rot'] = tuple(r); self._poser(i)

    # ---- images
    def tick(self):
        """Une image du jeu : avance les mouvements et les sequences en cours. -> ensemble des groupes modifies depuis le dernier appel."""
        for i, a in self.auto.items():                      # animations en continu : delai de depart, tours, delai entre deux tours (FldObject.fld_motion_update)
            if a['fini'] or i not in self.etat: continue
            if a['delai'] >= 1: a['delai'] -= PAS; a['temps'] = 0
            else:
                a['temps'] += PAS
                if a['temps'] > a['fin']:
                    reste = a['temps'] - a['fin']
                    if a['rep'] >= 1: a['rep'] -= 1
                    if a['rep'] == 0: a['temps'] = a['fin']; a['fini'] = True
                    else: a['temps'] = reste
                    a['delai'] = a['rdelai']
            self.etat[i]['temps'] = a['temps']; self._poser(i)
        for i, st in self.etat.items():
            if i in self.auto: continue
            mv = [x for x in (st['mot'], st['seq']) if x]
            if not mv or st.get('fini'): continue
            st['temps'] += PAS
            for x in mv:                                   # FldObject.fld_motion_update : au dela de la fin, repetition (repeat = -1 : sans fin) ou tenue sur la derniere cle
                if st['temps'] > x['fin'] and x['repeat'] == -1 and x['fin'] > 0: st['temps'] -= x['fin']
            if all(st['temps'] >= x['fin'] and x['repeat'] != -1 for x in mv): st['fini'] = True
            self._poser(i)
        s = self.sale; self.sale = set(); return s

    def _origine(self, i):
        r = self._o64.get(i)
        if r is None:
            o = self.objs[i]; r = self._o64[i] = (np.array(o['pos'], np.float64), np.array(o['rot'], np.float64), np.array(o['scl'], np.float64))
        return r

    def _cles_mot(self, mot):
        """Positions, rotations et echelles des cles d'un mouvement, en tableaux (n, 3)."""
        r = self._cles.get(id(mot))
        if r is None or r[0] is not mot:                                           # (l'identite est verifiee : un numero libere pourrait etre reutilise)
            ks = mot['keys']; r = self._cles[id(mot)] = (mot,) + tuple(np.array([k[j] for k in ks], np.float64) for j in (1, 2, 3))
        return r[1:]

    def _rot(self, rot):
        k = (float(rot[0]), float(rot[1]), float(rot[2])); m = self._emat.get(k)
        if m is None:
            if len(self._emat) > 20000: self._emat.clear()
            m = self._emat[k] = euler_mat(*k)
        return m

    def _matrice(self, i):
        if i not in self._inv:
            o = self.objs[i]; S = np.diag(o['scl']).astype(np.float64)
            try: A = np.linalg.inv(euler_mat(*o['rot']) @ S)
            except np.linalg.LinAlgError: A = np.eye(3)
            self._inv[i] = A
        return self._inv[i]

    def _poser(self, i):
        o = self.objs[i]; st = self._st(i)
        base = [(None, self.plages.get(i, []), self.imgobj.get(i))]
        for m in self.var_de.get(i, []): base.append((m, self.var[(i, m)]['plages'], self.var[(i, m)]['images']))
        pos0, rot0, scl0 = self._origine(i); pos, rot, scl = pos0, rot0, scl0
        if st['pos'] is not None: pos = np.array(st['pos'], np.float64)
        if st['rot'] is not None: rot = np.array([st['rot'][0], st['rot'][1], 0.0], np.float64)
        mot = st['mot']; t = st['temps']
        if mot is not None and mot['keys']:
            a, b, f = _interp(mot['keys'], t); cp, cr, cs = self._cles_mot(mot)
            pos = pos + (cp[a] if a == b or f == 0.0 else cp[a] * (1 - f) + cp[b] * f)
            rot = rot + (cr[a] if a == b or f == 0.0 else cr[a] * (1 - f) + cr[b] * f)
            scl = scl * (cs[a] if a == b or f == 0.0 else cs[a] * (1 - f) + cs[b] * f)
        panneau = self.bill.get(i) if self.bill_ok else None
        identite = st['pos'] is None and st['rot'] is None and mot is None and panneau is None       # le modele reste a sa place d'origine
        if not identite:
            R = self._rot(rot) if panneau is None else self._rb[32 if panneau & 32 else 4] @ self._rot(rot - rot0)       # panneau : l'orientation vient de la camera (le reste du mouvement s'y ajoute)
            T = R @ (scl[:, None] * self._matrice(i))                                    # monde d'origine -> monde actuel : (v - pos0) -> T, puis + pos  (= R . diag(scl) . inv(R0 . diag(scl0)))
        for m, plages, images in base:
            vivant = (m is None and st['mdl'] == o['mdl']) or (m is not None and st['mdl'] == m)
            vivant = vivant and not st['off'] and st['alpha'] > 0
            for k, (key, d, n) in enumerate(plages):
                img = images[k] if images else None
                if not vivant: v = np.zeros((n, 3), np.float32)
                else:
                    src, uv, col = self._src_seq(key, d, n, img, st)
                    v = src if identite else ((src.astype(np.float64) - pos0) @ T.T + pos).astype(np.float32)
                    if img is not None:                                                  # UV et couleurs qui changent d'une image a l'autre de la sequence
                        if img['uv'] is not None: self._tableau(self.cur_uv, self.uv0, key)[d:d + n] = self.uv0[key][d:d + n] if uv is None else uv; self.sale_uv.add(key)
                        if img['col'] is not None: self._tableau(self.cur_col, self.col0, key)[d:d + n] = self.col0[key][d:d + n] if col is None else col; self.sale_col.add(key)
                self.cur[key][d:d + n] = v; self.sale.add(key)

    def _src_seq(self, key, d, n, img, st):
        """(sommets, UV, couleurs) d'un sous-maillage : d'origine (UV et couleurs None), ou interpoles par la sequence de maillages en cours (FldObject.seq_build_mesh : entre les images
        des deux cles autour de l'image courante ; la valeur d'une cle est le numero de l'enfant du modele)."""
        seq = st['seq']
        if seq is None or img is None or not seq['keys']: return self.orig[key][d:d + n], None, None
        a, b, f = _interp(seq['keys'], st['temps']); n_img = len(img['pos'])
        va = min(max(seq['keys'][a][1], 0), n_img - 1); vb = min(max(seq['keys'][b][1], 0), n_img - 1)
        mix = lambda x: None if x is None else (x[va] if va == vb or f == 0.0 else x[va] * (1 - f) + x[vb] * f)
        return mix(img['pos']), mix(img['uv']), mix(img['col'])


class PalettesCarte:
    """Palettes animees de la carte (FldObject.update_plp) : chaque animation (FPAM) enchaine ses cles ; la duree d'une cle est en 1/60 s, comptee par pas de 2 par image du jeu.
    Les surfaces concernees (groupes de texture 'pam', voir Donnees.carte) prennent la texture de la cle courante. Animation liee a un evenement (numero >= 1) : image 0 tant que l'evenement n'est pas en cours."""

    def __init__(self, c):
        self.defs = c.get('pamdef', {})
        self.pams = [{'frame': p['frame'], 'cle': p['cle'], 'durees': p['durees']} for p in c.get('pam', [])]

    def tick(self):
        """Une image du jeu."""
        for p in self.pams:
            d = p['durees']
            if not d: continue
            p['frame'] += PAS
            if p['frame'] - d[min(p['cle'], len(d) - 1)] >= 0:
                p['frame'] -= d[min(p['cle'], len(d) - 1)]; p['cle'] = 0 if len(d) <= p['cle'] + 1 else p['cle'] + 1

    def image(self, key, evenement=0):
        """Numero de l'image (texture) courante du groupe `key`."""
        dd = self.defs[key]
        if dd['evenement'] >= 1 and dd['evenement'] != evenement: return 0
        p = self.pams[dd['pam']]
        return min(max(p['cle'], 0), len(dd['images']) - 1)

    def etat(self): return [(p['frame'], p['cle']) for p in self.pams]

    def regler(self, etat):
        for p, (f, k) in zip(self.pams, etat): p['frame'] = f; p['cle'] = k
