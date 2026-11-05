"""Lecture des donnees graphiques du jeu (datapack.unity3d, dans l'APK de donnees de l'utilisateur).
Rien n'est fourni avec ce programme : tout est lu dans les fichiers du joueur puis mis en cache sur son disque."""
import os, re, math, pickle, zipfile, json, time, threading, gc
import numpy as np
from dq4_pc import language as LG
from dq4_pc.world import fld

DATAPACK = 'assets/bin/Data/datapack.unity3d'
WHITE_TEX = 'blanche'                 # cle de la texture blanche 4 x 4 des materiaux sans texture (voir Data._texture)


def _quat_mat(x, y, z, w):
    return np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                     [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                     [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]], dtype=np.float64)


def euler_mat(rx, ry, rz):
    """Rotation d'un objet de carte (degres) comme FldObject.rotateXZY (0xCD47F0, lue au desassemblage) : q = (AngleAxis(ry, haut) * AngleAxis(-rz, avant)) * AngleAxis(-rx, droite) -- les axes sont les
    Vector3.up / forward / right statiques (decalages 0x18 / 0x48 / 0x3C), les angles X et Z sont inverses, et le produit de quaternions applique X en premier (dans le repere de l'objet), puis Z, puis le cap Y en
    dernier (dans le repere du monde) : matrice Ry . Rz . Rx. (Ce n'est pas Quaternion.Euler d'Unity, Z-X-Y, et ce n'est pas non plus l'ordre X, Y, Z note par erreur en #21.) Utilisee par init_fld (rotation de depart),
    SetCommonAnimation, pmv_func et c_pmv_func (mouvements) : le couvercle d'un coffre, cle X = -60, se releve autour de SA charniere quel que soit le cap du coffre (un coffre de cap 90, -90 ou 180 s'ouvrait de cote
    ou vers l'avant quand le cap etait applique avant la bascule)."""
    a, b, c = math.radians(-rx), math.radians(ry), math.radians(-rz)
    Rx = np.array([[1, 0, 0], [0, math.cos(a), -math.sin(a)], [0, math.sin(a), math.cos(a)]])
    Ry = np.array([[math.cos(b), 0, math.sin(b)], [0, 1, 0], [-math.sin(b), 0, math.cos(b)]])
    Rz = np.array([[math.cos(c), -math.sin(c), 0], [math.sin(c), math.cos(c), 0], [0, 0, 1]])
    return Ry @ Rz @ Rx


def fallback_sceneries(name_str):
    """Decors voisins d'un decor de combat absent des donnees. Le moteur choisit la lettre finale selon l'heure du monde (`StageStatus::getBtlMapName` : _d jour, _e soir, _n nuit ET aube : la zone 1 -- 3264 a 127 --
    reprend `_n`, il n'existe aucun decor d'aube) ; `param_map_battle.dat` liste les decors de chaque lieu, mais `btlcc1` n'a que _d et _e : sans `_n` rien ne s'afficherait. Monde sombre sans zone horaire :
    la table du moteur demande `_dk` (btl_pl_dk, btl_se_dk, btl_sd_dk, btl_mt_dk, btl_po_dk, btl_wd_dk), mais le paquet de donnees n'a que pl, po, wd (et tc1) en `_dk` : se, sd, mt prennent la nuit
    (supposition : la table les demande, aucune ressource ne les porte). Dans l'ordre : la variante la plus proche en luminosite, les autres, puis le nom sans lettre. Un nom qui ne finit pas par
    _d, _e, _n ou _dk : aucune."""
    m = re.match(r'^(.*)_(dk|d|e|n)$', name_str or '')
    if not m: return []
    base, c = m.groups()
    order = {'n': ['e', 'd'], 'e': ['d', 'n'], 'd': ['e', 'n'], 'dk': ['n', 'd', 'e']}[c]
    return ['%s_%s' % (base, x) for x in order] + [base]


class Data:
    def __init__(self, apk_data, cache_dir, log=print):
        self.apk, self.cache, self.log = apk_data, cache_dir, log
        os.makedirs(cache_dir, exist_ok=True)
        self._env = None
        self._objs = None
        self._lock = threading.RLock()          # UnityPy partage un seul lecteur de fichier : une seule extraction a la fois (preparation en arriere-plan et jeu)
        self._tex_names = None
        self._mesh = {}
        self._go_by_name = None

    # ---- UnityPy (charge a la demande, seulement si le cache ne suffit pas)
    def env(self):
        if self._env is None:
            with self._lock:
                if self._env is None:
                    import UnityPy
                    self.log(LG.tr('Lecture du paquet de donnees du jeu (une seule fois, quelques secondes)...'))
                    raw = zipfile.ZipFile(self.apk).read(DATAPACK)
                    env = UnityPy.load(raw)
                    self._objs = {o.path_id: o for o in env.objects}
                    self._env = env
        return self._env

    def free_up(self):
        """Rend la memoire du paquet de donnees (plus de 800 Mo) ; il sera relu a la demande si un element manque encore."""
        with self._lock:
            self._env = None; self._objs = None; self._go_by_name = None; self._tex_names = None; self._mesh = {}
        gc.collect()

    def _gos(self):
        if self._go_by_name is None:
            self.env()
            self._go_by_name = {}
            for pid, o in self._objs.items():
                if o.type.name == 'GameObject':
                    self._go_by_name.setdefault(o.read().m_Name, pid)
        return self._go_by_name

    def _mesh_data(self, ref):
        from UnityPy.helpers.MeshHelper import MeshHandler
        if ref.path_id not in self._mesh:
            m = ref.deref_parse_as_object(); h = MeshHandler(m); h.process()
            v = np.array(h.m_Vertices, np.float32).reshape(-1, 3)
            uv = np.array(h.m_UV0, np.float32).reshape(len(v), -1)[:, :2] if h.m_UV0 is not None else np.zeros((len(v), 2), np.float32)
            col = np.array(h.m_Colors, np.float32).reshape(len(v), -1) if h.m_Colors is not None else np.ones((len(v), 4), np.float32)
            if col.shape[1] == 3: col = np.c_[col, np.full(len(col), 255.0, np.float32)]
            if col.size and col.max() > 1.0: col = col / 255.0
            tris = [np.array(t, np.int64).reshape(-1, 3) for t in h.get_triangles()]
            self._mesh[ref.path_id] = (v, uv, col, tris)
        return self._mesh[ref.path_id]

    def _texture(self, matref, tex_out, name_out=None, fmt_out=None):
        """-> (cle, scale, offset, couleur _Color du materiau, genre) ; remplit tex_out[cle] = tableau RGBA (haut en premier) et name_out[cle] = nom de la texture.
        genre = shader choisi par FldObject.set_shader (CD5414) : 'trans' (Custom/fld_trans : fusion SrcAlpha / OneMinusSrcAlpha, ZWrite off) si le nom de la texture ne contient pas '.tim'
        ou si _Color.a != 1 ; sinon 'atest' (fld_atest) si la texture est en RGBA32 (format 4), 'normal' (fld_normal) autrement."""
        try:
            m = matref.deref_parse_as_object()
            col = (1.0, 1.0, 1.0, 1.0)
            for k, c in m.m_SavedProperties.m_Colors:
                if k == '_Color': col = (c.r, c.g, c.b, c.a)
            for k, v in m.m_SavedProperties.m_TexEnvs:
                if v.m_Texture.path_id:
                    key = v.m_Texture.path_id
                    if key not in tex_out or (fmt_out is not None and key not in fmt_out):
                        t = v.m_Texture.deref_parse_as_object()
                        tex_out[key] = np.array(t.image.convert('RGBA'))
                        if name_out is not None: name_out[key] = t.m_Name
                        if fmt_out is not None: fmt_out[key] = int(t.m_TextureFormat)
                    name_str = (name_out or {}).get(key, '.tim'); fmt = (fmt_out or {}).get(key, 3)
                    kind = 'trans' if ('.tim' not in name_str or col[3] != 1.0) else ('atest' if fmt == 4 else 'normal')
                    return key, (v.m_Scale.x, v.m_Scale.y), (v.m_Offset.x, v.m_Offset.y), col, kind
        except Exception as ex:
            self.log(LG.tr('  texture illisible: %s') % ex)
            return None, (1, 1), (0, 0), (1.0, 1.0, 1.0, 1.0), 'normal'
        # materiau NO_DEFAULT texture (aucune texture dans ses TexEnvs : 21 cartes de lieux, 10 decors de combat) : Unity echantillonne la texture blanche par defaut, la surface est donc dessinee en couleur de sommet x _Color
        # (sol sombre, eau...). Avant, la surface etait absente de la visionneuse (groupe sans texture ignore au dessin).
        tex_out[WHITE_TEX] = np.full((4, 4, 4), 255, np.uint8)
        return WHITE_TEX, (1.0, 1.0), (0.0, 0.0), col, 'trans' if col[3] != 1.0 else 'normal'

    def _components(self, g):
        out = {}
        for c in g.m_Components:
            o = (c.component if hasattr(c, 'component') else c).deref(); out[o.type.name] = o
        return out

    def _map_text(self, name_str):
        self.env()
        for pid, o in self._objs.items():
            if o.type.name == 'TextAsset':
                t = o.read()
                if t.m_Name == name_str + '.map':
                    return t.m_Script.encode('utf-8', 'surrogateescape') if isinstance(t.m_Script, str) else bytes(t.m_Script)
        return None

    # ---- une carte
    def _frame_children(self, cg):
        """Maillages d'image d'un modele (enfants sNN_*, FldObject.seq_build_mesh) : liste de MeshFilter, dans l'ordre ; l'image 0 est le maillage du modele lui-meme."""
        t = self._components(cg)['Transform'].read(); out = []
        for ch in t.m_Children:
            cgo = self._objs[ch.deref_parse_as_object().m_GameObject.path_id].read()
            if re.match(r's\d+_', cgo.m_Name):
                c = self._components(cgo)
                if 'MeshFilter' in c: out.append((cgo.m_Name, c['MeshFilter'].read().m_Mesh))
        return [m for _, m in sorted(out, key=lambda x: x[0])]

    def game_map(self, name_str, silent=False):
        """-> dict : 'groupes' {cle_texture: (positions Nx3, uv Nx2, couleurs Nx4)}, 'textures' {cle: RGBA}, 'objets' (FMAP), 'plages' {objet: [(cle, debut, nombre)]},
        'noms' {objet: nom du modele}, 'var' {(objet, modele): {'plages', 'images'}} : variantes de modele des animations communes (FCAN), cuites a la position d'origine de l'objet
        et placees apres les objets de la carte dans les groupes ; 'tabs' (FCAN), 'mots' (FPMV), 'seqent' / 'seqs' (FSEQ / FSQD),
        'imgobj' {objet: images par sous-maillage} (sequences de maillages jouees en continu), 'pam' (FPAM : animations de palette) et 'pamdef' {cle de groupe: {'nom', 'pam', 'evenement', 'images': [RGBA]}} : surfaces dont la texture change d'image en image (eau, marais, sols qui font mal...), groupes a part"""
        f = os.path.join(self.cache, 'carte11_%s.pkl' % name_str)
        if os.path.exists(f):
            with open(f, 'rb') as fh: return pickle.load(fh)
        with self._lock:
            if os.path.exists(f):                                   # produite entre-temps par la preparation en arriere-plan
                with open(f, 'rb') as fh: return pickle.load(fh)
            return self._extract_map(name_str, f, silent)

    @staticmethod
    def _frames(ip, iuv, icol, idx, sc, off, mc=(1.0, 1.0, 1.0, 1.0)):
        """Images d'un sous-maillage : {'pos': (images, n, 3), 'uv': (images, n, 2) ou None, 'col': (images, n, 4) ou None} ; UV et couleurs seulement si elles changent d'une image a l'autre (eau qui coule, lampe qui vacille)."""
        im = {'pos': np.stack([x[idx] for x in ip]), 'uv': None, 'col': None}
        u = np.stack([x[idx] * np.array(sc, np.float32) + np.array(off, np.float32) for x in iuv]).astype(np.float32)
        if np.abs(u - u[0]).max() > 1e-6: im['uv'] = u
        c = np.stack([x[idx] for x in icol]).astype(np.float32) * np.array(mc, np.float32)
        if np.abs(c - c[0]).max() > 1e-6: im['col'] = c
        return im

    def _pam_group(self, q, pam, tex, pamdef):
        """Cle du groupe de texture d'une palette animee (une par nom, animation et evenement) ; ses images sont les textures 'pam/<nom>.NNN' (FldObject.init_fld). None si elles manquent."""
        key = ('pam', q['nom'], q['pam'], q['event'])
        if key not in pamdef:
            tx = self._textures(); imgs = []
            for k in range(len(pam['durees'])):
                o = tx.get('%s.%03d' % (q['nom'], k))
                if o is None: break
                imgs.append(np.array(o.read().image.convert('RGBA')))
            if len(imgs) < len(pam['durees']) or not imgs:
                self.log(LG.tr('  palette animee %s : %d textures sur %d, ignoree') % (q['nom'], len(imgs), len(pam['durees']))); pamdef[key] = None
            else:
                pamdef[key] = {'nom': q['nom'], 'pam': q['pam'], 'evenement': q['event'], 'images': imgs}; tex[key] = imgs[0]
        return key if pamdef[key] else None

    def _extract_map(self, name_str, f, silent=False):
        if not silent: self.log(LG.tr('Extraction de la carte %s ...') % name_str)
        gos = self._gos(); raw = self._map_text(name_str)
        root = gos.get(name_str + '.fld')
        if root is None or raw is None: raise KeyError('carte introuvable dans les donnees : ' + name_str)
        nobj, objs = fld.map_objs(raw)
        kids = {}
        rg = self._objs[root].read(); rt = self._components(rg)['Transform'].read()
        for ch in rt.m_Children:
            cg = self._objs[ch.deref_parse_as_object().m_GameObject.path_id].read()
            m = re.match(r'(\d+)_', cg.m_Name)
            if m: kids[int(m.group(1))] = cg
        if not kids and {'MeshFilter', 'MeshRenderer'} <= set(self._components(rg)): kids[0] = rg          # decor d'un seul maillage porte par la RACINE (18 decors de combat : btl_mt_*, btl_po_*, btl_sd_*, btldc1, btldh1, btldp8_*, btlta2, btltd1_*) : l'objet 0 de la carte est la racine elle-meme
        for o in objs:                                               # ChunkFile.readPosition (CCEB58) lit x, y, z puis NEGUE y (fneg) : la position d'un objet de la carte est (x, -y, z) ; sans cela les arbres et la ruine des reliefs
            o['pos'] = (o['pos'][0], -o['pos'][1], o['pos'][2])      # s'enfoncent (y du fichier = -hauteur du relief) ; c'est aussi la raison du « +1 » des coffres (fichier -0,5 -> monde +0,5)
        tex = {}; acc = {}; lens = {}; spans = {}; names = {}; tnom = {}; tfmt = {}
        pams = fld.pam(raw); plp_obj = {}; pamdef = {}
        for q in fld.plp(raw):                                       # FldObject.set_palette_data : textures de l'objet dont le nom contient celui de la palette
            if 0 <= q['pam'] < len(pams) and 0 <= q['obj'] < len(objs): plp_obj.setdefault(q['obj'], []).append(q)

        def bake(o, cg):
            """Geometrie d'un modele a la position d'origine de l'objet -> ([(cle, debut, nombre)], images ou None) ; ajoutee aux groupes."""
            comps = self._components(cg)
            if 'MeshFilter' not in comps or 'MeshRenderer' not in comps: return [], None
            t = comps['Transform'].read(); p, q, s = t.m_LocalPosition, t.m_LocalRotation, t.m_LocalScale
            L = np.eye(4); L[:3, :3] = _quat_mat(q.x, q.y, q.z, q.w) @ np.diag([s.x, s.y, s.z]); L[:3, 3] = (p.x, p.y, p.z)
            M = np.eye(4); M[:3, :3] = euler_mat(*o['rot']) @ np.diag(o['scl']); M[:3, 3] = o['pos']
            W = M @ L
            mr = comps['MeshRenderer'].read()
            v, uv, col, tris = self._mesh_data(comps['MeshFilter'].read().m_Mesh)
            vw = (np.c_[v, np.ones(len(v))] @ W.T)[:, :3].astype(np.float32)
            ip, iuv, icol = [], [], []
            for mref in self._frame_children(cg):                      # images de la sequence (FldObject.seq_build_mesh : Transform.GetChild(valeur de la cle)), meme nombre de sommets que le modele
                vi, uvi, ci, _ = self._mesh_data(mref)
                if len(vi) == len(v): ip.append((np.c_[vi, np.ones(len(vi))] @ W.T)[:, :3].astype(np.float32)); iuv.append(uvi); icol.append(ci)
            out = []; imgs = []
            for i, tr in enumerate(tris):
                mat = mr.m_Materials[min(i, len(mr.m_Materials) - 1)]
                key, sc, off, mc, kind = self._texture(mat, tex, tnom, tfmt)
                for q in plp_obj.get(o['i'], ()):
                    if q['nom'] in tnom.get(key, '').rsplit('.', 1)[0]:
                        key = self._pam_group(q, pams[q['pam']], tex, pamdef) or key; break
                # FldObject.save_org_color (init_fld, RVA 0xCD811C) : _OrgColor = (1, 1, 1, alpha de _Color) ; FldObject.update_material_color (a chaque image, 0xCD79F4) : Material.color = _OrgColor x FldObject.m_color
                # (teinte du paquet 33, blanc par defaut). La couleur RGB de _Color enregistree dans l'asset n'est donc JAMAIS utilisee en jeu (elle rendait noirs les cedres, sous-bois et arbres du decor de
                # nuit des combats : _Color = 0, 0, 0) ; seul son alpha compte. Shader fld_*.vert : couleur du sommet x _Color.
                mcol = np.array((1.0, 1.0, 1.0, mc[3]), np.float32)
                if kind == 'trans' and key is not None:               # materiau transparent : groupe a part, trace apres le decor opaque dans la file 3000 + priorite (FldObject.set_priority)
                    gk = ('tr', o['prio'], key)
                    if gk not in tex and key in tex: tex[gk] = tex[key]
                    if key in pamdef and pamdef[key]: pamdef[gk] = pamdef[key]
                    key = gk
                idx = tr.ravel()
                a = acc.setdefault(key, ([], [], []))
                out.append((key, lens.get(key, 0), len(idx))); lens[key] = lens.get(key, 0) + len(idx)
                a[0].append(vw[idx]); a[1].append(uv[idx] * np.array(sc, np.float32) + np.array(off, np.float32)); a[2].append(col[idx] * mcol)
                imgs.append(self._frames(ip, iuv, icol, idx, sc, off, mcol) if ip else None)
            return out, imgs

        seqent, seqs = fld.sequences(raw); imgobj = {}
        for iobj, o in enumerate(objs):
            cg = kids.get(o['mdl'])
            if cg is None: continue
            names[iobj] = cg.m_Name
            pl, imgs = bake(o, cg)
            if pl: spans[iobj] = pl
            if pl and imgs and any(imgs) and 0 <= o['seqobj'] < len(seqent) and 0 <= seqent[o['seqobj']][1] < len(seqs): imgobj[iobj] = imgs      # sequence jouee en continu (eau, lampes...)
        tabs = fld.canim(raw); var = {}
        for iobj, o in enumerate(objs):                              # variantes des animations communes (porte ouverte, jarre ou tonneau casse, coffre ouvert...)
            if not 0 <= o['canim'] < len(tabs): continue
            for m, sq, mp in tabs[o['canim']]:
                if m == o['mdl'] or (iobj, m) in var or kids.get(m) is None: continue
                pl, imgs = bake(o, kids[m])
                if pl: var[(iobj, m)] = {'plages': pl, 'images': imgs}
        groups = {k: tuple(np.concatenate(x).astype(np.float32) for x in a) for k, a in acc.items()}
        res = {'groupes': groups, 'textures': {k: tex[k] for k in groups if k in tex}, 'objets': objs, 'plages': spans, 'noms': names,
               'var': var, 'tabs': tabs, 'mots': fld.pmv(raw), 'seqent': seqent, 'seqs': seqs, 'imgobj': imgobj, 'pam': pams, 'pamdef': {k: v for k, v in pamdef.items() if k in groups}}
        with open(f + '.tmp', 'wb') as fh: pickle.dump(res, fh, protocol=4)
        os.replace(f + '.tmp', f)                                   # ecriture atomique : jamais de fichier a moitie ecrit
        return res

    def _textures(self):
        """{nom: objet Texture2D} (a appeler avec le verrou)."""
        if self._tex_names is None:
            self.env()
            self._tex_names = {}
            for o in self._objs.values():
                if o.type.name == 'Texture2D': self._tex_names.setdefault(o.read().m_Name, o)
        return self._tex_names

    def texture(self, name_str):
        """Texture Unity par son nom (ex. `field` : tuiles de la carte du monde), RGBA haut en bas ; mise en cache."""
        f = os.path.join(self.cache, 'tex_%s.npy' % name_str)
        if os.path.exists(f): return np.load(f)
        with self._lock:
            if os.path.exists(f): return np.load(f)
            o = self._textures().get(name_str)
            if o is None: return None
            a = np.array(o.read().image.convert('RGBA')); np.save(f, a); return a

    # ---- grand plan du monde (fenetre « Carte » de la carte du monde : MenuPortItemTable.Make_WorldLargeMap / LoadLargeWorldMap)
    def world_plan(self):
        """{'base': image 1024 x 1024 RVB (haut en premier), 'pieces': [(bit, x, y, image h x l x 3)]} : le fond `dsdq4lmap0_1024` et les pieces `P<bit>_<x>_<y>_<width_px>` (MAP_DIFF : posees sur le fond quand
        le bit du drapeau envoye par le moteur est leve ; x et y comptes depuis le coin haut gauche). Ce sont des TextAsset a donnees brutes (3 octets par pixel). Mis en cache dans world_plan.npz."""
        f = os.path.join(self.cache, 'plan_monde.npz')
        def read(z):
            pieces = [(int(k[1:].split('_')[0]), int(k.split('_')[1]), int(k.split('_')[2]), z[k]) for k in sorted(z.files) if k != 'base']
            return {'base': z['base'], 'pieces': pieces}
        if os.path.exists(f):
            with np.load(f) as z: return read(z)
        with self._lock:
            if os.path.exists(f):
                with np.load(f) as z: return read(z)
            self.env(); out = {}
            for o in self._objs.values():
                if o.type.name != 'TextAsset': continue
                t = o.read(); nm = t.m_Name
                if nm == 'dsdq4lmap0_1024' or re.fullmatch(r'P\d_\d+_\d+_\d+', nm):
                    s = t.m_Script; out[nm] = bytes(s) if isinstance(s, (bytes, bytearray)) else s.encode('utf-8', 'surrogateescape')
            if 'dsdq4lmap0_1024' not in out: return None
            arrs = {'base': np.frombuffer(out.pop('dsdq4lmap0_1024'), np.uint8).reshape(1024, 1024, 3)}
            for nm, b in out.items():
                w = int(nm.split('_')[3]); arrs[nm] = np.frombuffer(b, np.uint8).reshape(-1, w, 3)
            tmp = f + '.tmp.npz'; np.savez(tmp, **arrs); os.replace(tmp, f)
            with np.load(f) as z: return read(z)

    # ---- voile de la carte du monde (fenetre « Carte », ICityMap : code 5)
    def world_veil(self):
        """Image 192 x 256 x 4 (RGBA) du TextAsset `dsdq4wmap01m` : silhouette grisee des terres que la fenetre de carte pose sur les blocs de 10 x 10 pixels (a partir de x = 48, y = 16) non encore explores. Mise en cache."""
        f = os.path.join(self.cache, 'voile_monde.npy')
        if os.path.exists(f): return np.load(f)
        with self._lock:
            if os.path.exists(f): return np.load(f)
            self.env()
            for o in self._objs.values():
                if o.type.name != 'TextAsset': continue
                t = o.read()
                if t.m_Name != 'dsdq4wmap01m': continue
                s = t.m_Script; b = bytes(s) if isinstance(s, (bytes, bytearray)) else s.encode('utf-8', 'surrogateescape')
                if len(b) != 192 * 256 * 4: return None
                a = np.frombuffer(b, np.uint8).reshape(192, 256, 4).copy(); np.save(f, a); return a
        return None

    # ---- modele 3D anime (FbxObject : Resources « fbx/c<numero> », paquets 31 et 32 du moteur)
    def fbx_model(self, no):
        """Modele « fbx/c%04d » : hierarchie d'os, maillage skinne (un os par sommet, ou jusqu'a 4 avec poids), texture, clips d'animation (courbes de position / rotation / echelle de chaque os) -> dict
        (voir fbx.FbxModel) ; mis en cache sur le disque. L'exception de l'extraction (shader ou composant non gere) est propagee : l'appelant ignore alors le modele."""
        f = os.path.join(self.cache, 'fbx1_c%04d.pkl' % no)
        if os.path.exists(f):
            with open(f, 'rb') as fh: return pickle.load(fh)
        with self._lock:
            if os.path.exists(f):
                with open(f, 'rb') as fh: return pickle.load(fh)
            return self._extract_fbx(no, f)

    def _extract_fbx(self, no, f):
        from UnityPy.helpers.MeshHelper import MeshHandler
        pid = self._gos().get('c%04d' % no)
        if pid is None: raise KeyError('modele fbx introuvable dans les donnees : c%04d' % no)
        names, parent, pos, rot, scl, paths, t_idx, rendered = [], [], [], [], [], [], {}, []

        def visit(g, parent_idx, path):
            comps = self._components(g); to = comps['Transform']; t = to.read(); i = len(names)
            names.append(g.m_Name); parent.append(parent_idx); paths.append(path); t_idx[to.path_id] = i
            p, q, s = t.m_LocalPosition, t.m_LocalRotation, t.m_LocalScale
            pos.append((p.x, p.y, p.z)); rot.append((q.x, q.y, q.z, q.w)); scl.append((s.x, s.y, s.z))
            if 'SkinnedMeshRenderer' in comps: rendered.append(comps['SkinnedMeshRenderer'].read())
            elif 'MeshRenderer' in comps: raise ValueError('maillage non skinne non gere (%s)' % g.m_Name)
            for ch in t.m_Children:
                cg = self._objs[ch.deref_parse_as_object().m_GameObject.path_id].read()
                visit(cg, i, (path + '/' if path else '') + cg.m_Name)
        root = self._objs[pid].read(); comps = self._components(root)
        visit(root, -1, '')
        if len(rendered) != 1: raise ValueError('%d maillages skinnes (un seul est gere)' % len(rendered))
        smr = rendered[0]
        # materiaux : meme texture et shader « Custom/ImdChara » (couleur du sommet x _Color, fusion alpha, ZWrite on, Cull Back)
        tex = {}; tnom = {}; tfmt = {}; lookup_keys = set()
        for mref in smr.m_Materials:
            mat = mref.deref_parse_as_object(); sh = mat.m_Shader.deref_parse_as_object().m_ParsedForm.m_Name
            if sh != 'Custom/ImdChara': raise ValueError('shader non gere : %s' % sh)
            lookup_keys.add(self._texture(mref, tex, tnom, tfmt)[0])
        if len(lookup_keys) != 1 or None in lookup_keys or WHITE_TEX in lookup_keys: raise ValueError('textures : %s' % lookup_keys)          # (modele 3D sans texture : refuse comme avant, la texture blanche ne sert qu'au decor des cartes)
        mesh = smr.m_Mesh.deref_parse_as_object(); h = MeshHandler(mesh); h.process()
        v = np.array(h.m_Vertices, np.float32).reshape(-1, 3); n = len(v)
        uv = np.array(h.m_UV0, np.float32).reshape(n, -1)[:, :2]
        bi = np.array(h.m_BoneIndices, np.int64).reshape(n, -1) if h.m_BoneIndices is not None else np.zeros((n, 1), np.int64)
        bw = np.array(h.m_BoneWeights, np.float32).reshape(n, -1) if h.m_BoneWeights is not None else np.ones((n, 1), np.float32)       # un seul os par sommet : poids 1 (maillage « rigide », cas du dragon)
        tri_indices = np.concatenate([np.array(t, np.int64).reshape(-1, 3) for t in h.get_triangles()])
        bind = np.array([[[getattr(b, 'e%d%d' % (r, c)) for c in range(4)] for r in range(4)] for b in mesh.m_BindPose], float)
        bones = [t_idx[b.path_id] for b in smr.m_Bones]
        if len(bones) != len(bind): raise ValueError('os (%d) et poses de liaison (%d) differents' % (len(bones), len(bind)))
        clips = {}
        for cref in comps['Animation'].read().m_Animations:
            c = cref.deref_parse_as_object()
            if getattr(c, 'm_Compressed', False): raise ValueError('animation comprimee non geree (%s)' % c.m_Name)
            cb = []
            for kind, entries in (('pos', c.m_PositionCurves), ('rot', c.m_RotationCurves), ('scl', c.m_ScaleCurves)):
                for q in entries:
                    if q.path not in paths: continue
                    ks = q.curve.m_Curve; dim = 4 if kind == 'rot' else 3
                    def vec(x): return ([x.x, x.y, x.z] + ([x.w] if dim == 4 else [])) if hasattr(x, 'x') else [float(x)]
                    cb.append((paths.index(q.path), kind, [k.time for k in ks], [vec(k.value) for k in ks], [vec(k.inSlope) for k in ks], [vec(k.outSlope) for k in ks]))
            clips[c.m_Name] = {'dur': max([k[2][-1] for k in cb] or [0.0]), 'wrap': int(c.m_WrapMode), 'courbes': cb}
        res = {'noms': names, 'parent': parent, 'pos': pos, 'rot': rot, 'scl': scl, 'v': v, 'uv': uv, 'bi': bi, 'bw': bw, 'tri': tri_indices, 'bind': bind, 'bones': bones,
               'tex': tex[next(iter(lookup_keys))], 'clips': clips, 'shader': 'Custom/ImdChara'}
        with open(f + '.tmp', 'wb') as fh: pickle.dump(res, fh, protocol=4)
        os.replace(f + '.tmp', f)
        return res

    # ---- feuille de sprites d'un personnage
    def sheet(self, ident):
        f = os.path.join(self.cache, 'sprite_h%d.npy' % ident)
        if os.path.exists(f): return np.load(f)
        with self._lock:
            if os.path.exists(f): return np.load(f)
            tx = self._textures()
            for name_str in ('h%d' % ident, 'h%03d' % ident):
                o = tx.get(name_str)
                if o is not None:
                    a = np.array(o.read().image.convert('RGBA')); np.save(f, a); return a
        return None

    # ---- preparation du cache en arriere-plan
    def _prep_file(self):
        return os.path.join(self.cache, 'preparation.json')

    def _elements(self, entries):
        """[(genre, nom, fichier)] : tout ce que le jeu peut avoir a extraire du paquet de donnees."""
        el = [('texture', 'field', 'tex_field.npy')]
        el += [('carte', n, 'carte11_%s.pkl' % n) for n in entries['cartes']]
        el += [('feuille', n, 'sprite_h%d.npy' % int(n)) for n in entries['feuilles']]
        el += [('texture', n, 'tex_%s.npy' % n) for n in entries['monstres'] + entries.get('plans', []) + entries.get('effets', [])]
        el.append(('plan_monde', 'plan_monde', 'plan_monde.npz'))
        el.append(('fbx', '1018', 'fbx1_c1018.pkl'))                          # le dragon de l'ecran-titre (FbxObject c1018) ; les autres modeles 3D, s'il y en a, se lisent a la demande
        return el

    def _purge_old(self):
        """Supprime les cartes d'une ancienne version du cache (carte2_ a carte10_ : carte10_ : surfaces transparentes triees par une moitie des drapeaux et non par leur priorite, #203 ; sans les animations de palette et de sequence, coffres enfonces, couvercle a l'envers ou ouvert de cote : rotations des objets dans le mauvais ordre ; carte9_ : surfaces sans texture et decors portes par la racine absents), devenues inutiles."""
        try:
            for f in os.listdir(self.cache):
                if re.fullmatch(r'carte(?:[0-9]|10)_.+\.pkl', f): os.remove(os.path.join(self.cache, f))
        except OSError as ex:
            self.log(LG.tr('Anciennes cartes du cache non supprimees : %s') % ex)

    def prepare(self, stop):
        """Extrait en arriere-plan, au rythme tranquille, toutes les cartes, feuilles de sprites et textures de monstres pas encore en cache : le jeu n'a plus jamais a lire
        le gros paquet de donnees en pleine partie (la premiere carte inconnue, un puits par exemple, figeait l'ecran pendant la lecture). Quand tout est pret, la memoire est
        rendue, et les lancements suivants ne touchent plus au paquet. `stop` : Event pour interrompre."""
        try:
            fp = self._prep_file(); entries = None
            if os.path.exists(fp):
                try: entries = json.load(open(fp, encoding='utf-8'))
                except Exception: entries = None
                if entries is not None and ('plans' not in entries or 'effets' not in entries): entries = None            # ancienne liste (sans les plans de la fenetre de carte, ou sans les textures d'effets) : refaite
            if entries is not None:
                failures = set(entries.get('echecs', []))
                if all(os.path.exists(os.path.join(self.cache, f)) or n in failures for _, n, f in self._elements(entries)): self._purge_old(); return       # deja tout pret
            else:
                with self._lock:
                    go = self._gos(); tx = self._textures()
                entries = {'cartes': sorted(n[:-4] for n in go if n.endswith('.fld')),
                         'feuilles': sorted(str(int(n[1:])) for n in tx if re.fullmatch(r'h\d+', n)),
                         'monstres': sorted(n for n in tx if re.fullmatch(r'm\d{3}', n)), 'effets': sorted(n for n in tx if re.fullmatch(r'm\d{4}', n)), 'plans': sorted(n for n in tx if re.fullmatch(r'[a-z]{2}_map\d|dsdq4wmap\d+', n)), 'echecs': []}
            failures = set(entries.get('echecs', []))
            t_start = time.time(); n_done = 0
            self.log(LG.tr('Preparation du cache en arriere-plan (une seule fois, environ une minute et demie ; le jeu reste jouable)...'))
            for kind, n, f in self._elements(entries):
                if stop.is_set(): return
                if os.path.exists(os.path.join(self.cache, f)) or n in failures: continue
                t = time.perf_counter()
                try:
                    if kind == 'carte': self.game_map(n, True)
                    elif kind == 'feuille': self.sheet(int(n))
                    elif kind == 'plan_monde': self.world_plan()
                    elif kind == 'fbx': self.fbx_model(int(n))
                    else: self.texture(n)
                except Exception as ex:
                    failures.add(n); self.log(LG.tr('Preparation : %s %s ignore (%s)') % (kind, n, str(ex)[:60]))
                n_done += 1
                time.sleep(min(0.25, 1.0 * (time.perf_counter() - t)) + 0.01)          # rythme tranquille
            entries['echecs'] = sorted(failures)
            with open(fp + '.tmp', 'w', encoding='utf-8') as fh: json.dump(entries, fh)
            os.replace(fp + '.tmp', fp)
            if n_done: self.log(LG.tr('Preparation du cache terminee : %d elements en %.0f s.') % (n_done, time.time() - t_start))
            self._purge_old()
            self.free_up()
        except Exception as ex:
            self.log(LG.tr('Preparation du cache interrompue : %s') % ex)


if __name__ == '__main__':
    # Preparation du cache dans un processus a part (lance par la visionneuse, priorite basse) : dans un thread du jeu, les extractions (Python pur) lui prenaient le
    # verrou de l'interpreteur et saccadaient l'ecran. Fin du processus : quand l'entree standard se ferme (la visionneuse s'est arretee).
    import sys
    LG.select_language(os.environ.get('DQ4_LANGUE') or 'systeme')          # (D-238 : la langue de l'outil, donnee par le jeu qui lance ce processus ; seul, la langue de l'ordinateur)
    stop = threading.Event()
    threading.Thread(target=lambda: (sys.stdin.buffer.read(), stop.set()), daemon=True).start()
    Data(sys.argv[1], sys.argv[2], log=lambda *a: print(*a, flush=True)).prepare(stop)
