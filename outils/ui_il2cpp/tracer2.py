"""Traceur v2 : exécute réellement le code de construction des menus (Make_*, MenuParts, MeshMaker...) et
remplace l'API Unity par un modèle minimal (GameObject, Transform, Mesh, Material, TextMesh, List<T>)."""
import re, struct, math, json
from unicorn import *
from unicorn.arm64_const import *
import tracer as t
from tracer import *
import desasm as d, reloc as rl

def norm(nm):
    nm = nm.replace('$$', '.')
    for p in ('UnityEngine.', 'System.Collections.Generic.'):
        if nm.startswith(p): nm = nm[len(p):]
    return nm

class Tr2(t.Tr):
    REAL = re.compile(r'^(MenuMessage\.SetCanvasMesh|MenuPortItemTable\.Sub_|eIndent\.|NotchFix\.|UIFix\.|MenuParts\.|MeshMaker\.|MenuPortItemTable\.(MonsterNamePlate|MonsterMarkList|BattleBar|ICityMap)\.)')
    NOREAL = re.compile(r'^(MenuParts\.(<>c|FuncIsHit|IBase\.(IntChanger|StringChanger)|IButton\.<>c))')
    def __init__(self):
        super().__init__()
        self.U = {}
        self.listcls = {}
        self.sheet_mat = {}
        self.deleg = {}
        self.tab = []
        self.plist = []
        self.fixups = {k: (lambda X, F, f=f: f(self, X, F)) for k, f in Tr2.FIXUPS.items()}

    def is_real(self, nm):
        if not self.REAL.match(nm) or self.NOREAL.match(nm): return False
        if 'ctor' in nm and not nm.startswith(('MenuParts.', 'MeshMaker.', 'MenuPortItemTable.Monster', 'MenuPortItemTable.BattleBar')): return False
        return True
    def collect(self, fn, seen):
        if fn in seen: return
        seen.add(fn)
        end = fend(fn)
        for ins in d.md.disasm(d.rd(fn, end - fn), fn):
            if ins.mnemonic in ('bl', 'b') and ins.operands[0].type == 2:
                t_ = ins.operands[0].imm
                if fn <= t_ < end or t_ in self.patched: continue
                nm = self.fname(t_)
                if 0xc10000 <= t_ <= 0xc11000:
                    self.intercept(t_, lambda a: None); continue
                if self.native_for(nm, t_) is None and self.is_real(nm):
                    self.observe(t_, nm); self.collect(t_, seen)
                else: self.intercept(t_, self.stub_for(t_))

    # ----------------------------------------------------------------- noms
    def fname(self, addr):
        sg = SIG.get(addr)
        if sg: return sg['cls'] + '.' + sg['name']
        return norm(d.names.get(addr, 'sub_%x' % addr))

    def stub_for(self, addr):
        nm = self.fname(addr)
        nat = self.native_for(nm, addr)
        if nat: return nat
        return super().stub_for(addr)

    # ----------------------------------------------------------------- helpers registres
    def setf(self, *vals):
        for i in range(4):
            v = vals[i] if i < len(vals) else 0.0
            self.uc.reg_write(UC_ARM64_REG_S0 + i, struct.unpack('<I', struct.pack('<f', v))[0])
    def ret(self, v):
        self.uc.reg_write(UC_ARM64_REG_X0, v & 0xffffffffffffffff)
    def newU(self, kind, klassname=None, **kw):
        k = self.klass_for_type(klassname) if klassname else 0
        o = self.new_obj(k or 0, fill=False)
        self.U[o] = dict(kind=kind, id=self.obj[o], **kw)
        return o
    def ev(self, name, **kw): self.event('call', name=name, **kw)

    # ----------------------------------------------------------------- List<T> en mémoire réelle (_items +0x10, _size +0x18)
    def elem_info(self, tname):
        if tname in ('UnityEngine.Vector3', 'Vector3'): return 12, 'v3'
        if tname in ('UnityEngine.Vector2', 'Vector2'): return 8, 'v2'
        if tname in ('int', 'uint', 'float'): return 4, 'i32'
        if tname in ('short', 'ushort'): return 2, 'i16'
        return 8, 'ptr'
    def list_init(self, lst, esize, cap=4):
        arr = self.alloc(0x20 + esize * cap + 16); self.w(arr + 0x18, cap, 8)
        self.w(lst + 0x10, arr); self.w(lst + 0x18, 0, 4); self.w(lst + 0x1c, 0, 4)
        return arr
    def list_add_raw(self, lst, esize, raw):
        arr = self.u(lst + 0x10, 8); n = self.u(lst + 0x18, 4)
        cap = self.u(arr + 0x18, 8) if arr else 0
        if not arr or n >= cap:
            ncap = max(4, cap * 2); na = self.alloc(0x20 + esize * ncap + 16); self.w(na + 0x18, ncap, 8)
            if arr and n: self.uc.mem_write(na + 0x20, bytes(self.uc.mem_read(arr + 0x20, esize * n)))
            arr = na; self.w(lst + 0x10, arr)
        self.uc.mem_write(arr + 0x20 + esize * n, raw); self.w(lst + 0x18, n + 1, 4)
    def src_items(self, src, esize):
        """Éléments d'une source IEnumerable : tableau (X[] : longueur +0x18, données +0x20) ou List<T>."""
        if not src: return []
        nm = self.kname.get(self.u(src, 8), '')
        if '[]' in nm:
            n = self.u(src + 0x18, 8)
            return [bytes(self.uc.mem_read(src + 0x20 + esize * i, esize)) for i in range(n)]
        return self.list_items(src, esize) if self.u(src + 0x10, 8) else []
    def list_items(self, lst, esize):
        arr = self.u(lst + 0x10, 8); n = self.u(lst + 0x18, 4)
        return [bytes(self.uc.mem_read(arr + 0x20 + esize * i, esize)) for i in range(n)] if arr else []

    def list_native(self, nm):
        m = re.match(r'^List<(.+)>\.(\.?ctor|Add|AddWithResize|AddRange|InsertRange|Clear|get_Count|get_Item|set_Item|ToArray|Insert|RemoveAt|Remove|Contains|IndexOf)$', nm)
        if not m: return None
        tname, op = m.group(1), m.group(2).lstrip('.')
        esize, ek = self.elem_info(tname)
        def h(a):
            X, F = self.regs(); this = X[0]
            if op == 'ctor':
                cap = X[1] if (len(X) > 1 and 0 < X[1] < 4096 and X[1] not in self.obj) else 4
                self.list_init(this, esize, max(4, cap))
            elif op in ('Add', 'AddWithResize'):
                if ek == 'v3': raw = struct.pack('<3f', *F[:3])
                elif ek == 'v2': raw = struct.pack('<2f', *F[:2])
                elif ek == 'i32': raw = struct.pack('<I', X[1] & 0xffffffff)
                elif ek == 'i16': raw = struct.pack('<H', X[1] & 0xffff)
                else: raw = struct.pack('<Q', X[1])
                if not self.u(this + 0x10, 8): self.list_init(this, esize)
                self.list_add_raw(this, esize, raw)
            elif op == 'AddRange':
                if not self.u(this + 0x10, 8): self.list_init(this, esize)
                for r in self.src_items(X[1], esize): self.list_add_raw(this, esize, r)
            elif op == 'InsertRange':
                if not self.u(this + 0x10, 8): self.list_init(this, esize)
                items = self.list_items(this, esize); i = X[1] & 0xffffffff
                items[i:i] = self.src_items(X[2], esize)
                self.w(this + 0x18, 0, 4)
                for r in items: self.list_add_raw(this, esize, r)
            elif op == 'Clear':
                self.w(this + 0x18, 0, 4)
            elif op == 'get_Count': self.ret(self.u(this + 0x18, 4))
            elif op == 'get_Item':
                arr = self.u(this + 0x10, 8); i = X[1] & 0xffffffff
                if i >= self.u(this + 0x18, 4): raise Abort('List index')
                raw = bytes(self.uc.mem_read(arr + 0x20 + esize * i, esize))
                if ek == 'v3': self.setf(*struct.unpack('<3f', raw))
                elif ek == 'v2': self.setf(*struct.unpack('<2f', raw))
                elif ek == 'i32': self.ret(struct.unpack('<I', raw)[0])
                elif ek == 'i16': self.ret(struct.unpack('<H', raw)[0])
                else: self.ret(struct.unpack('<Q', raw)[0])
            elif op == 'set_Item':
                arr = self.u(this + 0x10, 8); i = X[1] & 0xffffffff
                if ek == 'v3': raw = struct.pack('<3f', *F[:3])
                elif ek == 'v2': raw = struct.pack('<2f', *F[:2])
                elif ek == 'i32': raw = struct.pack('<I', X[2] & 0xffffffff)
                else: raw = struct.pack('<Q', X[2])
                self.uc.mem_write(arr + 0x20 + esize * i, raw)
            elif op == 'ToArray':
                items = self.list_items(this, esize)
                ak = self.alloc(0x20)   # classe factice du tableau
                o = self.alloc(0x20 + esize * len(items) + 16); self.w(o, ak); self.w(o + 0x18, len(items), 8)
                self.uc.mem_write(o + 0x20, b''.join(items)); self.obj[o] = len(self.obj) + 1
                self.ret(o)
            elif op in ('Insert', 'RemoveAt', 'Remove', 'Contains', 'IndexOf'):
                items = self.list_items(this, esize)
                if op == 'Insert':
                    i = X[1] & 0xffffffff; raw = struct.pack('<Q', X[2])[:esize]; items.insert(i, raw)
                elif op == 'RemoveAt': items.pop(X[1] & 0xffffffff)
                elif op in ('Remove', 'Contains', 'IndexOf'):
                    raw = struct.pack('<Q', X[1])[:esize]
                    if op == 'Remove':
                        if raw in items: items.remove(raw); self.ret(1)
                        else: self.ret(0)
                    elif op == 'Contains': self.ret(1 if raw in items else 0)
                    else: self.ret(items.index(raw) if raw in items else 0xffffffff)
                if op in ('Insert', 'RemoveAt', 'Remove'):
                    self.w(this + 0x18, 0, 4)
                    for r in items: self.list_add_raw(this, esize, r)
        return h

    # ----------------------------------------------------------------- Unity-lite
    def tr_of(self, o):
        u = self.U.get(o)
        if not u: return 0
        if u['kind'] == 'Transform': return o
        go = o if u['kind'] == 'GameObject' else u.get('go')
        g = self.U.get(go)
        if not g: return 0
        if not g.get('tr'):
            tr = self.newU('Transform', 'UnityEngine.Transform', go=go, lpos=[0., 0., 0.], lscale=[1., 1., 1.], lrot=[0., 0., 0., 1.], parent=0)
            g['tr'] = tr; g['comps'].append(tr)
        return g['tr']
    def world(self, tr):
        u = self.U[tr]; p = u['parent']
        if not p: return list(u['lpos'])
        pw = self.world(p); ps = self.pscale(p)
        return [pw[i] + u['lpos'][i] * ps[i] for i in range(3)]
    def pscale(self, tr):
        u = self.U[tr]; s = list(u['lscale'])
        if u['parent']:
            ps = self.pscale(u['parent']); s = [s[i] * ps[i] for i in range(3)]
        return s
    def set_world(self, tr, w):
        u = self.U[tr]; p = u['parent']
        if not p: u['lpos'] = list(w)
        else:
            pw = self.world(p); ps = self.pscale(p)
            u['lpos'] = [(w[i] - pw[i]) / (ps[i] or 1.) for i in range(3)]

    def native_for(self, nm, addr):
        ln = self.list_native(nm)
        if ln: return ln
        H = {}
        def reg(*names):
            def deco(f):
                for n in names: H[n] = f
                return f
            return deco
        T = self
        @reg('GameObject.ctor')
        def _(X, F):
            T.U[X[0]] = dict(kind='GameObject', id=T.obj.get(X[0]), comps=[], name='', tr=0, active=True)
            T.tr_of(X[0])
        for dn in ('MenuPortItem.FUNC_SetCode', 'MenuParts.IBase.IntChanger', 'MenuParts.IBase.StringChanger', 'MenuParts.FuncIsHit', 'MenuPortItemTable.Make_FUNC'):
            def mkd(dn=dn):
                def f(X, F):             # constructeur de délégué : on mémorise (cible, méthode) ; les lambdas seront exécutées à la demande
                    mn = T.kname.get(X[2], '') if len(X) > 2 else ''
                    T.deleg[X[0]] = (X[1], mn)
                return f
            H[dn + '.ctor'] = mkd()
        @reg('RuntimeHelpers.InitializeArray')
        def _(X, F):       # tableau statique initialisé depuis les métadonnées (champ <PrivateImplementationDetails>.HASH)
            import meta
            fn = T.kname.get(X[1], '')
            m_ = re.match(r'^Field\$<PrivateImplementationDetails>\.(\w+)$', fn)
            if not m_: return
            raw = meta.field_default(m_.group(1))
            if raw is None: return
            n = T.u(X[0] + 0x18, 8); kn = T.kname.get(T.u(X[0], 8), '')
            es = 4
            if 'Byte' in kn or 'byte' in kn: es = 1
            elif 'Int16' in kn or 'short' in kn: es = 2
            elif 'Vector3' in kn: es = 12
            elif 'Vector2' in kn: es = 8
            elif 'Color' in kn or 'Vector4' in kn or 'Quaternion' in kn: es = 16
            T.uc.mem_write(X[0] + 0x20, raw[:n * es])
        # tables de liaison de MenuPortItem (journal structuré pour l'export)
        def _tab(kind, **kw): T.tab.append(dict(kind=kind, **kw))
        if addr == 0xd056a4: H[nm] = lambda X, F: (_tab('addparts', parts=X[1]), T.ret(len(T.plist) - 1 if T.plist.append(X[1]) is None else 0))[1]
        if addr == 0xd05a30: H[nm] = lambda X, F: _tab('param', id=X[1] & 0xffff, no=X[2] & 0xffff, partsNo=X[3] & 0xffffffff, baseNo=X[4] & 0xffffffff)
        if addr == 0xd05b04: H[nm] = lambda X, F: _tab('param_ibase', id=X[1] & 0xffff, no=X[2] & 0xffff, ibase=X[3])
        if addr == 0xd05b74: H[nm] = lambda X, F: _tab('param_textcolor', id=X[1] & 0xffff, no=X[2] & 0xffff, parts=X[3])
        if addr == 0xd057d4: H[nm] = lambda X, F: _tab('code_parts', id=X[1] & 0xffff, partsNo=X[2] & 0xffff)
        if addr == 0xd05948: H[nm] = lambda X, F: _tab('code_func', id=X[1] & 0xffff, func=X[2])
        @reg('sub_bf37a8')
        def _(X, F):        # initialisation du rgctx d'une méthode générique : on y met AddComponent<MenuParts>()
            if T.kname.get(X[0], '').startswith('Method$') and 'Create' in T.kname.get(X[0], ''):
                _fix_generic_menuparts(T, X, F)
        @reg('GameObject.CreatePrimitive')
        def _(X, F):
            o = T.newU('GameObject', 'UnityEngine.GameObject', comps=[], name='prim', tr=0, active=True); T.tr_of(o)
            for kd in ('MeshFilter', 'MeshRenderer', 'MeshCollider'):
                T.U[o]['comps'].append(T.newU(kd, 'UnityEngine.' + kd, go=o))
            T.ret(o)
        @reg('GameObject.Find')
        def _(X, F):
            o = T.newU('GameObject', 'UnityEngine.GameObject', comps=[], name='found', tr=0, active=True); T.tr_of(o); T.ret(o)
        @reg('GameObject.get_transform', 'Component.get_transform')
        def _(X, F): T.ret(T.tr_of(X[0]))
        @reg('Component.get_gameObject')
        def _(X, F):
            u = T.U.get(X[0]); T.ret(u['go'] if u and u['kind'] != 'GameObject' else X[0])
        @reg('GameObject.AddComponent<object>', 'GameObject.AddComponent')
        def _(X, F):
            go, kl = X[0], X[1]
            cn = T.kname.get(kl, '?').replace('_TypeInfo', '')
            m_ = re.search(r'AddComponent<(.+)>\(\)$', cn)
            if m_:                      # jeton Method$...AddComponent<T>() -> classe T
                kk = T.klass_for_type(m_.group(1))
                if kk: kl = kk
                cn = m_.group(1)
                if cn == 'T':                # Create<T> (T = MenuParts ou sous-classe) : on prend MenuParts
                    cn = 'MenuParts'; kl = T.klass_for_type('MenuParts') or kl
            cn = cn.replace('_var', '')
            c = T.new_obj(kl, fill=True)
            if cn == 'MenuParts':       # champs initialises par MenuParts..ctor (0xd031d0)
                T.list_init(c + 0, 8) if False else None
                for off in (0x38, 0x58):
                    lo = T.alloc(0x30); T.w(lo, T.klass_for_type('MenuParts') or kl); T.obj[lo] = len(T.obj) + 1
                    T.list_init(lo, 8); T.w(c + off, lo)
            T.U[c] = dict(kind=cn.split('.')[-1], id=T.obj[c], go=go)
            T.U[go]['comps'].append(c)
            if cn.endswith('TextMesh') and not any(T.U[x]['kind'] == 'MeshRenderer' for x in T.U[go]['comps']):
                r = T.newU('MeshRenderer', 'UnityEngine.MeshRenderer', go=go); T.U[go]['comps'].append(r)
            if cn.endswith('Transform'): T.U[c]['kind'] = 'Transform'
            T.ret(c)
        @reg('GameObject.GetComponent<object>', 'GameObject.GetComponent', 'Component.GetComponent<object>')
        def _(X, F):
            go = X[0] if T.U.get(X[0], {}).get('kind') == 'GameObject' else T.U.get(X[0], {}).get('go')
            kl = X[1]; cn = T.kname.get(kl, '?').replace('_TypeInfo', '').replace('_var', '')
            m_ = re.search(r'GetComponent<(.+)>\(\)$', cn)
            if m_: cn = m_.group(1)
            SUB = {'Renderer': ('MeshRenderer',), 'Collider': ('BoxCollider', 'MeshCollider'), 'Component': None}
            want = cn.split('.')[-1]
            for c in T.U.get(go, {}).get('comps', []):
                kd = T.U[c]['kind']
                if kd == want or kd == cn or (want in SUB and (SUB[want] is None or kd in SUB[want])): T.ret(c); return
            T.ret(0)
        @reg('Object.set_name')
        def _(X, F):
            u = T.U.get(X[0])
            if u: u['name'] = T.strs.get(X[1]) or rl.S.get(X[1]) or X[1]
        @reg('Object.op_Inequality')
        def _(X, F): T.ret(1 if X[0] != X[1] else 0)
        @reg('Object.op_Equality')
        def _(X, F): T.ret(1 if X[0] == X[1] else 0)
        @reg('Object.Destroy', 'Object.DontDestroyOnLoad')
        def _(X, F): pass
        # Transform
        @reg('Transform.get_position')
        def _(X, F): T.setf(*T.world(X[0]))
        @reg('Transform.set_position')
        def _(X, F): T.set_world(X[0], F[:3])
        @reg('Transform.set_localPosition')
        def _(X, F): T.U[X[0]]['lpos'] = list(F[:3])
        @reg('Transform.get_localPosition')
        def _(X, F): T.setf(*T.U[X[0]]['lpos'])
        @reg('Transform.set_localScale')
        def _(X, F): T.U[X[0]]['lscale'] = list(F[:3])
        @reg('Transform.get_localScale')
        def _(X, F): T.setf(*T.U[X[0]]['lscale'])
        @reg('Transform.set_localRotation', 'Transform.set_rotation')
        def _(X, F): T.U[X[0]]['lrot'] = list(F[:4])
        @reg('Transform.set_parent')
        def _(X, F):
            tr, p = X[0], X[1]; w = T.world(tr)
            T.U[tr]['parent'] = p if p else 0
            T.set_world(tr, w)
        @reg('Transform.get_parent')
        def _(X, F): T.ret(T.U[X[0]]['parent'])
        @reg('Transform.Translate')
        def _(X, F):
            w = T.world(X[0]); T.set_world(X[0], [w[0] + F[0], w[1] + F[1], w[2] + F[2]])
        # Mesh
        @reg('MeshFilter.get_mesh', 'MeshFilter.get_sharedMesh')
        def _(X, F):
            u = T.U[X[0]]
            if not u.get('mesh'): u['mesh'] = T.newU('Mesh', 'UnityEngine.Mesh', vtx=[], uv=[], tris={}, sub=1)
            T.ret(u['mesh'])
        @reg('MeshFilter.set_mesh')
        def _(X, F): T.U[X[0]]['mesh'] = X[1]
        def readarr(a, n, fmt_):
            sz = struct.calcsize(fmt_); cnt = T.u(a + 0x18, 8)
            return [struct.unpack_from(fmt_, bytes(T.uc.mem_read(a + 0x20 + sz * i, sz))) for i in range(cnt)]
        @reg('Mesh.set_vertices')
        def _(X, F): T.U[X[0]]['vtx'] = [tuple(round(x, 5) for x in v) for v in readarr(X[1], 0, '<3f')]
        @reg('Mesh.set_uv')
        def _(X, F): T.U[X[0]]['uv'] = [tuple(round(x, 5) for x in v) for v in readarr(X[1], 0, '<2f')]
        @reg('Mesh.set_subMeshCount')
        def _(X, F): T.U[X[0]]['sub'] = X[1] & 0xffffffff
        @reg('Mesh.SetTriangles')
        def _(X, F): T.U[X[0]]['tris'][X[2] & 0xffffffff] = [v[0] for v in readarr(X[1], 0, '<i')]
        @reg('Mesh.set_triangles')
        def _(X, F): T.U[X[0]]['tris'][0] = [v[0] for v in readarr(X[1], 0, '<i')]
        @reg('Mesh.get_bounds')
        def _(X, F):         # Bounds (centre, demi-dimensions) rendus par x8 : boite des sommets du maillage
            v = T.U[X[0]].get('vtx') or [(0.0, 0.0, 0.0)]
            mn = [min(p[i] for p in v) for i in range(3)]; mx = [max(p[i] for p in v) for i in range(3)]
            T.uc.mem_write(T.uc.reg_read(UC_ARM64_REG_X8), struct.pack('<6f', *[(a + b) / 2 for a, b in zip(mn, mx)], *[(b - a) / 2 for a, b in zip(mn, mx)]))
        @reg('Screen.get_width')
        def _(X, F): T.ret(1080)
        @reg('Screen.get_height')
        def _(X, F): T.ret(1920)
        @reg('Mesh.RecalculateBounds', 'Mesh.RecalculateNormals', 'Mesh.Clear', 'Mesh.set_colors', 'Mesh.set_normals')
        def _(X, F): pass
        # Renderer / Material
        @reg('Renderer.set_material', 'Renderer.set_sharedMaterial')
        def _(X, F): T.U[X[0]]['mat'] = [X[1]]
        @reg('Renderer.set_materials', 'Renderer.set_sharedMaterials')
        def _(X, F):
            a = X[1]; n = T.u(a + 0x18, 8); T.U[X[0]]['mat'] = [T.u(a + 0x20 + 8 * i, 8) for i in range(n)]
        @reg('Renderer.get_material', 'Renderer.get_sharedMaterial')
        def _(X, F): T.ret((T.U[X[0]].get('mat') or [0])[0])
        @reg('Renderer.set_enabled')
        def _(X, F): T.U[X[0]]['enabled'] = bool(X[1] & 1)
        @reg('Material.ctor')
        def _(X, F):
            src = T.U.get(X[1])
            if src and src['kind'] == 'Material': T.U[X[0]] = dict(src, id=T.obj.get(X[0]), clone_of=X[1])
            else: T.U[X[0]] = dict(kind='Material', id=T.obj.get(X[0]), shader=T.fmt(X[1]), color=None, tex=None)
        @reg('Material.set_color')
        def _(X, F): T.U[X[0]]['color'] = [round(x, 4) for x in F[:4]]
        @reg('Material.set_mainTexture')
        def _(X, F): T.U[X[0]]['tex'] = X[1]
        @reg('Material.get_mainTexture')
        def _(X, F): T.ret(T.U[X[0]].get('tex') or 0)
        @reg('Material.SetTextureOffset')
        def _(X, F): T.U[X[0]]['offset'] = [round(F[0], 5), round(F[1], 5)]
        @reg('Material.SetTextureScale')
        def _(X, F): T.U[X[0]]['tscale'] = [round(F[0], 5), round(F[1], 5)]
        @reg('Material.set_shader')
        def _(X, F):
            sh = T.U.get(X[1]); T.U[X[0]]['shader'] = sh.get('name') if sh else X[1]
        @reg('Material.get_shader')
        def _(X, F):
            sh = T.U[X[0]].get('shader')
            o = T.newU('Shader', 'UnityEngine.Shader', name=sh); T.ret(o)
        @reg('Shader.Find')
        def _(X, F):
            o = T.newU('Shader', 'UnityEngine.Shader', name=T.strs.get(X[0]) or rl.S.get(X[0]) or T.fmt(X[0])); T.ret(o)
        @reg('Resources.Load')
        def _(X, F):
            lr = T.uc.reg_read(UC_ARM64_REG_X30); k = 0
            try:                                  # classe visée par le cast qui suit l'appel : adrp+ldr du jeton, puis cmp
                ins = list(d.md.disasm(d.rd(lr, 48), lr)); pg = {}
                for i_ in ins:
                    if i_.mnemonic == 'adrp': pg[i_.reg_name(i_.operands[0].reg)] = i_.operands[1].imm
                    elif i_.mnemonic == 'ldr' and i_.operands[1].type == 3 and i_.reg_name(i_.operands[1].mem.base) in pg:
                        slot = pg[i_.reg_name(i_.operands[1].mem.base)] + i_.operands[1].mem.disp
                        tok = rl.R.get(slot)
                        if tok and rl.M.get(tok, '').endswith('_TypeInfo'):
                            k = T.klass.get(tok) or T.new_klass(tok); T.w(tok, k); break
            except Exception: pass
            o = T.new_obj(k, fill=False); T.obj[o] = T.obj.get(o) or len(T.obj) + 1
            T.U[o] = dict(kind='Resource', id=T.obj[o], path=T.strs.get(X[0]) or rl.S.get(X[0]) or T.fmt(X[0]), tex=None); T.ret(o)
        # TextMesh
        for prop in ('text', 'fontSize', 'characterSize', 'anchor', 'alignment', 'lineSpacing', 'tabSize', 'richText', 'fontStyle', 'offsetZ', 'font'):
            def mk(prop):
                def f(X, F):
                    u = T.U[X[0]]
                    if prop in ('characterSize', 'lineSpacing', 'tabSize', 'offsetZ'): u[prop] = round(F[0], 4)
                    elif prop == 'text': u[prop] = T.read_cs(X[1])
                    elif prop == 'font': u[prop] = 'font'
                    else: u[prop] = X[1] & 0xffffffff
                return f
            H['TextMesh.set_' + prop] = mk(prop)
        @reg('TextMesh.set_color')
        def _(X, F): T.U[X[0]]['color'] = [round(x, 4) for x in F[:4]]
        @reg('Camera.get_main')
        def _(X, F):
            o = T.newU('Camera', 'UnityEngine.Camera'); T.ret(o)
        @reg('Camera.get_aspect')
        def _(X, F): T.setf(T.aspect)
        @reg('Screen.get_width')
        def _(X, F): T.ret(int(T.screen[0]))
        @reg('Screen.get_height')
        def _(X, F): T.ret(int(T.screen[1]))
        for _cn, _cv in dict(white=(1, 1, 1, 1), black=(0, 0, 0, 1), red=(1, 0, 0, 1), green=(0, 1, 0, 1), blue=(0, 0, 1, 1), yellow=(1, 0.92156863, 0.015686275, 1),
                             cyan=(0, 1, 1, 1), magenta=(1, 0, 1, 1), gray=(0.5, 0.5, 0.5, 1), grey=(0.5, 0.5, 0.5, 1), clear=(0, 0, 0, 0)).items():
            def _mkc(_cv=_cv):
                def f(X, F): T.setf(*_cv)
                return f
            H['Color.get_' + _cn] = _mkc()
        @reg('GameObject.SetActive')
        def _(X, F):
            u = T.U.get(X[0])
            if u: u['active'] = bool(X[1] & 1)
        @reg('GameObject.get_activeSelf', 'GameObject.get_activeInHierarchy')
        def _(X, F):
            u = T.U.get(X[0]); T.ret(1 if (u and u.get('active', True)) else 0)
        @reg('Screen.get_safeArea')
        def _(X, F): T.setf(0.0, 0.0, float(T.screen[0]), float(T.screen[1]))     # pas d'encoche : zone sûre = écran entier
        @reg('Texture.get_width', 'Texture.get_height')
        def _(X, F): T.ret(1024)
        @reg('Debug.LogError', 'Debug.Log')
        def _(X, F): pass
        f = H.get(nm)
        if not f: return None
        def h(a, f=f, nm=nm):
            X, F = T.regs()
            f(X, F)
            T.ev(nm, args=[T.fmt(x) for x in X[:4]] if nm in LOGNAMES else None, floats=None, ret=None, lr=T.uc.reg_read(UC_ARM64_REG_X30)) if nm in LOGNAMES else None
        return h

    def read_cs(self, p):
        """Chaîne .NET (UTF-16 après l'en-tête de 0x14 octets) ou littéral connu."""
        if p in self.strs: return self.strs[p]
        if p in rl.S: return rl.S[p]
        try:
            n = self.u(p + 0x10, 4)
            if 0 <= n < 512: return bytes(self.uc.mem_read(p + 0x14, 2 * n)).decode('utf-16-le', 'replace')
        except Exception: pass
        return None

    aspect = 0.5625
    screen = (450, 800)

LOGNAMES = set()

def _fix_generic_menuparts(self, X, F):
    """Create<object> / CreateBuildFrameParts<object> : le MethodInfo (x2 ou x7) pointe (+0x38) vers un bloc rgctx dont l'entrée 0
    est le MethodInfo de GameObject.AddComponent<T>() ; on y met celui de AddComponent<MenuParts>()."""
    nm = 'Method$UnityEngine.GameObject.AddComponent<MenuParts>()'
    tok = [t_ for t_, n_ in rl.M.items() if n_ == nm]
    if not tok: return
    k = self.klass.get(tok[0]) or self.new_klass(tok[0]); self.w(tok[0], k)
    for mi in X[1:8]:
        if 0x1c00000 < mi < 0x2000000 or self.kname.get(mi, '').startswith('Method$'):
            blk = self.alloc(0x40); self.w(blk, k); self.w(blk + 8, k)
            self.w(mi + 0x38, blk)

Tr2.FIXUPS = {}
