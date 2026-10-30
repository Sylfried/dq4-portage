import struct, sys
def chunks(raw):
    """FLD : suite de chunks 'TAG4' + taille(4, taille totale du chunk) ; FHDR a une taille propre."""
    out = []; p = 0
    while p + 8 <= len(raw):
        tag = raw[p:p+4]
        if not tag.isalpha(): break
        sz = struct.unpack_from('<I', raw, p + 4)[0]
        if sz < 8 or p + sz > len(raw): out.append((tag.decode(), p, len(raw) - p)); break
        out.append((tag.decode(), p, sz)); p = (p + sz + 15) & ~15
    return out
def map_objs(raw):
    cs = {t: (p, s) for t, p, s in chunks(raw)}
    p, s = cs['FMAP']
    nobj = struct.unpack_from('<I', raw, p + 8)[0]
    objs = []
    for i in range(nobj):
        o = p + 0x20 + 0x50 * i
        pos = struct.unpack_from('<3f', raw, o); oid = struct.unpack_from('<i', raw, o + 12)[0]
        rot = struct.unpack_from('<3f', raw, o + 16); mdl, com = struct.unpack_from('<hH', raw, o + 28)
        scl = struct.unpack_from('<3f', raw, o + 32); uid = struct.unpack_from('<i', raw, o + 44)[0]
        flag, prio = struct.unpack_from('<HH', raw, o + 48); rest = raw[o + 52:o + 80]
        seqobj, pmv = struct.unpack_from('<hh', raw, o + 56); canim = struct.unpack_from('<h', raw, o + 74)[0]       # FLD_MAP_OBJ : seq_obj_id, pmv_id ; canim_id (numero de la table d'animations communes de FCAN, -1 = aucune)
        objs.append(dict(i=i, pos=pos, id=oid, rot=rot, mdl=mdl, com=com, scl=scl, uid=uid, flag=flag, prio=prio, seqobj=seqobj, pmv=pmv, canim=canim, rest=rest.hex()))
    return nobj, objs
def canim(raw):
    """FCAN : tables d'animations communes. -> liste de tables ; une table = liste d'entrees (modele, seq_obj_id, pmv_id) dont l'indice + 1 est le numero d'animation
    (FldObject.SetCommonAnimation : modele a afficher, sequence de maillages (FSEQ), mouvement (FPMV))."""
    cs = {t: (p, s) for t, p, s in chunks(raw)}
    if 'FCAN' not in cs: return []
    p, s = cs['FCAN']; n = struct.unpack_from('<i', raw, p + 8)[0]; q = p + 12
    paires = [struct.unpack_from('<ii', raw, q + 8 * i) for i in range(n)]; q += 8 * n; out = []
    for nd, _ in paires:
        out.append([struct.unpack_from('<3h', raw, q + 8 * i) for i in range(nd)]); q += 8 * nd
    return out

def _entete_motion(raw, o):
    flag, nkey, rep, delai, rdelai, ksz = struct.unpack_from('<6h', raw, o); fin = struct.unpack_from('<i', raw, o + 16)[0]
    return dict(flag=flag, nkey=nkey, repeat=rep, delai=delai, rdelai=rdelai, fin=fin)

def pmv(raw):
    """FPMV : mouvements d'objets (position, rotation, echelle en cles, image = 1/60 s). -> liste de {'fin', 'repeat', 'keys': [(image, pos, rot, scl)]}"""
    cs = {t: (p, s) for t, p, s in chunks(raw)}
    if 'FPMV' not in cs: return []
    p, s = cs['FPMV']; n = struct.unpack_from('<i', raw, p + 8)[0]; out = []
    for o in struct.unpack_from('<%di' % n, raw, p + 12):
        m = _entete_motion(raw, o); keys = []
        for k in range(m['nkey']):
            v = struct.unpack_from('<i9f', raw, o + 0x20 + 40 * k); keys.append((v[0], v[1:4], v[4:7], v[7:10]))
        m['keys'] = keys; out.append(m)
    return out

def sequences(raw):
    """FSQD : sequences de maillages (cle = image 1/60 s, valeur = numero de maillage d'image) ; FSEQ : objets de sequence (obj_id, seq_id, grp_id, delai).
    -> (liste d'entrees FSEQ [(obj, seq)], liste de sequences {'fin', 'repeat', 'keys': [(image, valeur)]})"""
    cs = {t: (p, s) for t, p, s in chunks(raw)}; ent = []; seqs = []
    if 'FSEQ' in cs:
        p, s = cs['FSEQ']; n = struct.unpack_from('<i', raw, p + 8)[0]
        ent = [struct.unpack_from('<2h', raw, p + 12 + 20 * i) for i in range(n)]
    for t, p, s in chunks(raw):
        if t != 'FSQD': continue
        m = _entete_motion(raw, p + 16); m['keys'] = [struct.unpack_from('<2i', raw, p + 48 + 8 * k) for k in range(m['nkey'])]; seqs.append(m)
    return ent, seqs

if __name__ == '__main__':
    raw = open(sys.argv[1], 'rb').read()
    print([(t, hex(p), hex(s)) for t, p, s in chunks(raw)])
    n, objs = map_objs(raw); print('nobj', n)
    for o in objs: print(o)
