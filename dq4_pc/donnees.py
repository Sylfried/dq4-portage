"""Lecture des donnees graphiques du jeu (datapack.unity3d, dans l'APK de donnees de l'utilisateur).
Rien n'est fourni avec ce programme : tout est lu dans les fichiers du joueur puis mis en cache sur son disque."""
import os, re, math, pickle, zipfile, struct, json, time, threading, gc
import numpy as np
import fld

DATAPACK = 'assets/bin/Data/datapack.unity3d'


def _quat_mat(x, y, z, w):
    return np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                     [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                     [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]], dtype=np.float64)


def euler_mat(rx, ry, rz):
    """Quaternion.Euler d'Unity (degres) : Z, puis X, puis Y."""
    a, b, c = math.radians(rx), math.radians(ry), math.radians(rz)
    Rx = np.array([[1, 0, 0], [0, math.cos(a), -math.sin(a)], [0, math.sin(a), math.cos(a)]])
    Ry = np.array([[math.cos(b), 0, math.sin(b)], [0, 1, 0], [-math.sin(b), 0, math.cos(b)]])
    Rz = np.array([[math.cos(c), -math.sin(c), 0], [math.sin(c), math.cos(c), 0], [0, 0, 1]])
    return Ry @ Rx @ Rz


class Donnees:
    def __init__(self, apk_donnees, cache_dir, log=print):
        self.apk, self.cache, self.log = apk_donnees, cache_dir, log
        os.makedirs(cache_dir, exist_ok=True)
        self._env = None
        self._objs = None
        self._verrou = threading.RLock()          # UnityPy partage un seul lecteur de fichier : une seule extraction a la fois (preparation en arriere-plan et jeu)
        self._tex_noms = None
        self._mesh = {}
        self._go_by_name = None

    # ---- UnityPy (charge a la demande, seulement si le cache ne suffit pas)
    def env(self):
        if self._env is None:
            with self._verrou:
                if self._env is None:
                    import UnityPy
                    self.log('Lecture du paquet de donnees du jeu (une seule fois, quelques secondes)...')
                    raw = zipfile.ZipFile(self.apk).read(DATAPACK)
                    env = UnityPy.load(raw)
                    self._objs = {o.path_id: o for o in env.objects}
                    self._env = env
        return self._env

    def liberer(self):
        """Rend la memoire du paquet de donnees (plus de 800 Mo) ; il sera relu a la demande si un element manque encore."""
        with self._verrou:
            self._env = None; self._objs = None; self._go_by_name = None; self._tex_noms = None; self._mesh = {}
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

    def _texture(self, matref, tex_out):
        """-> (cle, scale, offset) ; remplit tex_out[cle] = tableau RGBA (haut en premier)"""
        try:
            m = matref.deref_parse_as_object()
            for k, v in m.m_SavedProperties.m_TexEnvs:
                if v.m_Texture.path_id:
                    key = v.m_Texture.path_id
                    if key not in tex_out:
                        t = v.m_Texture.deref_parse_as_object()
                        tex_out[key] = np.array(t.image.convert('RGBA'))
                    return key, (v.m_Scale.x, v.m_Scale.y), (v.m_Offset.x, v.m_Offset.y)
        except Exception as ex:
            self.log('  texture illisible: %s' % ex)
        return None, (1, 1), (0, 0)

    def _components(self, g):
        out = {}
        for c in g.m_Components:
            o = (c.component if hasattr(c, 'component') else c).deref(); out[o.type.name] = o
        return out

    def _map_text(self, nom):
        self.env()
        for pid, o in self._objs.items():
            if o.type.name == 'TextAsset':
                t = o.read()
                if t.m_Name == nom + '.map':
                    return t.m_Script.encode('utf-8', 'surrogateescape') if isinstance(t.m_Script, str) else bytes(t.m_Script)
        return None

    # ---- une carte
    def _enfants_images(self, cg):
        """Maillages d'image d'un modele (enfants sNN_*, FldObject.seq_build_mesh) : liste de MeshFilter, dans l'ordre ; l'image 0 est le maillage du modele lui-meme."""
        t = self._components(cg)['Transform'].read(); out = []
        for ch in t.m_Children:
            cgo = self._objs[ch.deref_parse_as_object().m_GameObject.path_id].read()
            if re.match(r's\d+_', cgo.m_Name):
                c = self._components(cgo)
                if 'MeshFilter' in c: out.append((cgo.m_Name, c['MeshFilter'].read().m_Mesh))
        return [m for _, m in sorted(out, key=lambda x: x[0])]

    def carte(self, nom, silencieux=False):
        """-> dict : 'groupes' {cle_texture: (positions Nx3, uv Nx2, couleurs Nx4)}, 'textures' {cle: RGBA}, 'objets' (FMAP), 'plages' {objet: [(cle, debut, nombre)]},
        'noms' {objet: nom du modele}, 'var' {(objet, modele): {'plages', 'images'}} : variantes de modele des animations communes (FCAN), cuites a la position d'origine de l'objet
        et placees apres les objets de la carte dans les groupes ; 'tabs' (FCAN), 'mots' (FPMV), 'seqent' / 'seqs' (FSEQ / FSQD)"""
        f = os.path.join(self.cache, 'carte3_%s.pkl' % nom)
        if os.path.exists(f):
            with open(f, 'rb') as fh: return pickle.load(fh)
        with self._verrou:
            if os.path.exists(f):                                   # produite entre-temps par la preparation en arriere-plan
                with open(f, 'rb') as fh: return pickle.load(fh)
            return self._extraire_carte(nom, f, silencieux)

    def _extraire_carte(self, nom, f, silencieux=False):
        if not silencieux: self.log('Extraction de la carte %s ...' % nom)
        gos = self._gos(); raw = self._map_text(nom)
        root = gos.get(nom + '.fld')
        if root is None or raw is None: raise KeyError('carte introuvable dans les donnees : ' + nom)
        nobj, objs = fld.map_objs(raw)
        kids = {}
        rg = self._objs[root].read(); rt = self._components(rg)['Transform'].read()
        for ch in rt.m_Children:
            cg = self._objs[ch.deref_parse_as_object().m_GameObject.path_id].read()
            m = re.match(r'(\d+)_', cg.m_Name)
            if m: kids[int(m.group(1))] = cg
        tex = {}; acc = {}; lens = {}; plages = {}; noms = {}

        def cuire(o, cg):
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
            vws = [vw]
            for mref in self._enfants_images(cg):                      # images suivantes (meme nombre de sommets que le modele)
                vi = self._mesh_data(mref)[0]
                if len(vi) == len(v): vws.append((np.c_[vi, np.ones(len(vi))] @ W.T)[:, :3].astype(np.float32))
            out = []; imgs = []
            for i, tr in enumerate(tris):
                mat = mr.m_Materials[min(i, len(mr.m_Materials) - 1)]
                key, sc, off = self._texture(mat, tex)
                idx = tr.ravel()
                a = acc.setdefault(key, ([], [], []))
                out.append((key, lens.get(key, 0), len(idx))); lens[key] = lens.get(key, 0) + len(idx)
                a[0].append(vw[idx]); a[1].append(uv[idx] * np.array(sc, np.float32) + np.array(off, np.float32)); a[2].append(col[idx])
                imgs.append(np.stack([x[idx] for x in vws]) if len(vws) > 1 else None)
            return out, imgs

        for iobj, o in enumerate(objs):
            cg = kids.get(o['mdl'])
            if cg is None: continue
            noms[iobj] = cg.m_Name
            pl, _ = cuire(o, cg)
            if pl: plages[iobj] = pl
        tabs = fld.canim(raw); var = {}
        for iobj, o in enumerate(objs):                              # variantes des animations communes (porte ouverte, jarre ou tonneau casse, coffre ouvert...)
            if not 0 <= o['canim'] < len(tabs): continue
            for m, sq, pm in tabs[o['canim']]:
                if m == o['mdl'] or (iobj, m) in var or kids.get(m) is None: continue
                pl, imgs = cuire(o, kids[m])
                if pl: var[(iobj, m)] = {'plages': pl, 'images': imgs}
        groupes = {k: tuple(np.concatenate(x).astype(np.float32) for x in a) for k, a in acc.items()}
        seqent, seqs = fld.sequences(raw)
        res = {'groupes': groupes, 'textures': {k: tex[k] for k in groupes if k in tex}, 'objets': objs, 'plages': plages, 'noms': noms,
               'var': var, 'tabs': tabs, 'mots': fld.pmv(raw), 'seqent': seqent, 'seqs': seqs}
        with open(f + '.tmp', 'wb') as fh: pickle.dump(res, fh, protocol=4)
        os.replace(f + '.tmp', f)                                   # ecriture atomique : jamais de fichier a moitie ecrit
        return res

    def _textures(self):
        """{nom: objet Texture2D} (a appeler avec le verrou)."""
        if self._tex_noms is None:
            self.env()
            self._tex_noms = {}
            for o in self._objs.values():
                if o.type.name == 'Texture2D': self._tex_noms.setdefault(o.read().m_Name, o)
        return self._tex_noms

    def texture(self, nom):
        """Texture Unity par son nom (ex. `field` : tuiles de la carte du monde), RGBA haut en bas ; mise en cache."""
        f = os.path.join(self.cache, 'tex_%s.npy' % nom)
        if os.path.exists(f): return np.load(f)
        with self._verrou:
            if os.path.exists(f): return np.load(f)
            o = self._textures().get(nom)
            if o is None: return None
            a = np.array(o.read().image.convert('RGBA')); np.save(f, a); return a

    # ---- feuille de sprites d'un personnage
    def feuille(self, ident):
        f = os.path.join(self.cache, 'sprite_h%d.npy' % ident)
        if os.path.exists(f): return np.load(f)
        with self._verrou:
            if os.path.exists(f): return np.load(f)
            tx = self._textures()
            for nom in ('h%d' % ident, 'h%03d' % ident):
                o = tx.get(nom)
                if o is not None:
                    a = np.array(o.read().image.convert('RGBA')); np.save(f, a); return a
        return None

    # ---- preparation du cache en arriere-plan
    def _fichier_prepa(self):
        return os.path.join(self.cache, 'preparation.json')

    def _elements(self, liste):
        """[(genre, nom, fichier)] : tout ce que le jeu peut avoir a extraire du paquet de donnees."""
        el = [('texture', 'field', 'tex_field.npy')]
        el += [('carte', n, 'carte3_%s.pkl' % n) for n in liste['cartes']]
        el += [('feuille', n, 'sprite_h%d.npy' % int(n)) for n in liste['feuilles']]
        el += [('texture', n, 'tex_%s.npy' % n) for n in liste['monstres']]
        return el

    def preparer(self, arret):
        """Extrait en arriere-plan, au rythme tranquille, toutes les cartes, feuilles de sprites et textures de monstres pas encore en cache : le jeu n'a plus jamais a lire
        le gros paquet de donnees en pleine partie (la premiere carte inconnue, un puits par exemple, figeait l'ecran pendant la lecture). Quand tout est pret, la memoire est
        rendue, et les lancements suivants ne touchent plus au paquet. `arret` : Event pour interrompre."""
        try:
            fp = self._fichier_prepa(); liste = None
            if os.path.exists(fp):
                try: liste = json.load(open(fp, encoding='utf-8'))
                except Exception: liste = None
            if liste is not None:
                echecs = set(liste.get('echecs', []))
                if all(os.path.exists(os.path.join(self.cache, f)) or n in echecs for _, n, f in self._elements(liste)): return       # deja tout pret
            else:
                with self._verrou:
                    go = self._gos(); tx = self._textures()
                liste = {'cartes': sorted(n[:-4] for n in go if n.endswith('.fld')),
                         'feuilles': sorted(str(int(n[1:])) for n in tx if re.fullmatch(r'h\d+', n)),
                         'monstres': sorted(n for n in tx if re.fullmatch(r'm\d{3}', n)), 'echecs': []}
            echecs = set(liste.get('echecs', []))
            t_debut = time.time(); n_faits = 0
            self.log('Preparation du cache en arriere-plan (une seule fois, environ une minute et demie ; le jeu reste jouable)...')
            for genre, n, f in self._elements(liste):
                if arret.is_set(): return
                if os.path.exists(os.path.join(self.cache, f)) or n in echecs: continue
                t = time.perf_counter()
                try:
                    if genre == 'carte': self.carte(n, True)
                    elif genre == 'feuille': self.feuille(int(n))
                    else: self.texture(n)
                except Exception as ex:
                    echecs.add(n); self.log('Preparation : %s %s ignore (%s)' % (genre, n, str(ex)[:60]))
                n_faits += 1
                time.sleep(min(0.4, 2.0 * (time.perf_counter() - t)) + 0.01)          # rythme tranquille : le jeu garde la main
            liste['echecs'] = sorted(echecs)
            with open(fp + '.tmp', 'w', encoding='utf-8') as fh: json.dump(liste, fh)
            os.replace(fp + '.tmp', fp)
            if n_faits: self.log('Preparation du cache terminee : %d elements en %.0f s.' % (n_faits, time.time() - t_debut))
            self.liberer()
        except Exception as ex:
            self.log('Preparation du cache interrompue : %s' % ex)
