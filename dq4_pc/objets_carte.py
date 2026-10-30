"""Objets animes des cartes de ville : portes qui s'ouvrent, jarres et tonneaux qui se brisent, coffres qui s'ouvrent, objets masques ou deplaces par le moteur.

Reproduit cote Python ce que fait la couche Unity du jeu (FldObject) a partir des paquets du moteur :
  * paquet 5 (cmd_fld_common_anim) : objet | numero << 16 -> SetCommonAnimation : la table d'animations communes de l'objet (FCAN, objet.canim)
    donne, pour chaque numero, le modele a afficher (porte, jarre intacte ou cassee...), une sequence de maillages (FSEQ/FSQD : le modele se deforme
    d'une image a l'autre, ex. la jarre qui eclate) et un mouvement (FPMV : position, rotation et echelle ajoutees a celles de l'objet, ex. battant de porte) ;
    numero 0 = modele d'origine, immobile ;
  * paquet 7 (cmd_fld_on_off) : objet | drapeau << 16 -> GameObject.SetActive(drapeau == 0) ;
  * paquet 2 (cmd_fld_alpha) : objet | niveau (0..31) << 16 ; niveau 0 = invisible ;
  * paquets 3 et 4 (cmd_fld_pos, cmd_fld_rot) : nouvelle position / rotation de l'objet.
Les temps sont en soixantiemes de seconde dans les donnees ; FldObject.Update avance de 2 par image du jeu (30 images/s)."""
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
        self.etat = {}; self.sale = set(); self._inv = {}

    def reinit(self):
        """Nouveau chargement de la meme carte : tous les objets reprennent leur etat d'origine."""
        self.etat = {}
        for k in self.cur: self.cur[k][:] = self.orig[k]
        for pl in (v['plages'] for v in self.var.values()):
            for key, d, n in pl: self.cur[key][d:d + n] = 0.0
        self.sale = set(self.cur)

    # ---- commandes du moteur
    def _st(self, i):
        o = self.objs[i]
        return self.etat.setdefault(i, {'mdl': o['mdl'], 'off': False, 'alpha': 31, 'pos': None, 'rot': None, 'mot': None, 'seq': None, 'temps': 0})

    def valide(self, i):
        return 0 <= i < len(self.objs) and (i in self.plages or i in self.var_de)

    def anim_commune(self, i, no):
        if not self.valide(i): return
        o = self.objs[i]; st = self._st(i)
        st['mot'] = st['seq'] = None; st['temps'] = 0; st['fini'] = False
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
        for i, st in self.etat.items():
            mv = [x for x in (st['mot'], st['seq']) if x]
            if not mv or st.get('fini'): continue
            st['temps'] += PAS
            for x in mv:                                   # FldObject.fld_motion_update : au dela de la fin, repetition (repeat = -1 : sans fin) ou tenue sur la derniere cle
                if st['temps'] > x['fin'] and x['repeat'] == -1 and x['fin'] > 0: st['temps'] -= x['fin']
            if all(st['temps'] >= x['fin'] and x['repeat'] != -1 for x in mv): st['fini'] = True
            self._poser(i)
        s = self.sale; self.sale = set(); return s

    def _matrice(self, i):
        if i not in self._inv:
            o = self.objs[i]; S = np.diag(o['scl']).astype(np.float64)
            try: A = np.linalg.inv(euler_mat(*o['rot']) @ S)
            except np.linalg.LinAlgError: A = np.eye(3)
            self._inv[i] = A
        return self._inv[i]

    def _poser(self, i):
        o = self.objs[i]; st = self._st(i)
        base = [(None, self.plages.get(i, []), None)]
        for m in self.var_de.get(i, []): base.append((m, self.var[(i, m)]['plages'], self.var[(i, m)]['images']))
        pos = np.array(o['pos'], np.float64); rot = np.array(o['rot'], np.float64); scl = np.array(o['scl'], np.float64)
        if st['pos'] is not None: pos = np.array(st['pos'], np.float64)
        if st['rot'] is not None: rot = np.array([st['rot'][0], st['rot'][1], 0.0], np.float64)
        mot = st['mot']; t = st['temps']
        if mot is not None and mot['keys']:
            a, b, f = _interp(mot['keys'], t); ka, kb = mot['keys'][a], mot['keys'][b]
            lerp = lambda u, v: np.array(u, np.float64) * (1 - f) + np.array(v, np.float64) * f
            pos = pos + lerp(ka[1], kb[1]); rot = rot + lerp(ka[2], kb[2]); scl = scl * lerp(ka[3], kb[3])
        pos0 = np.array(o['pos'], np.float64); A = self._matrice(i)
        B = euler_mat(*rot) @ np.diag(scl)
        T = B @ A                                          # monde d'origine -> monde actuel : (v - pos0) -> T, puis + pos
        identite = st['mdl'] == o['mdl'] and st['pos'] is None and st['rot'] is None and mot is None and st['seq'] is None
        cache = {}
        for m, plages, images in base:
            vivant = (m is None and st['mdl'] == o['mdl']) or (m is not None and st['mdl'] == m)
            vivant = vivant and not st['off'] and st['alpha'] > 0
            for k, (key, d, n) in enumerate(plages):
                if not vivant: v = np.zeros((n, 3), np.float32)
                else:
                    src = self.orig[key][d:d + n] if m is None else self._src_var(i, m, key, d, n, k, images, st)
                    v = src if identite and m is None else ((src.astype(np.float64) - pos0) @ T.T + pos).astype(np.float32)
                self.cur[key][d:d + n] = v; self.sale.add(key)

    def _src_var(self, i, m, key, d, n, k, images, st):
        """Sommets d'une variante de modele : d'origine, ou deformes par la sequence de maillages en cours (image courante entre deux cles)."""
        seq = st['seq']; img = images[k] if images else None
        if seq is None or img is None or not seq['keys']: return self.orig[key][d:d + n]
        a, b, f = _interp(seq['keys'], st['temps'])
        va = min(max(seq['keys'][a][1], 0), len(img) - 1); vb = min(max(seq['keys'][b][1], 0), len(img) - 1)
        return img[va] * (1 - f) + img[vb] * f
