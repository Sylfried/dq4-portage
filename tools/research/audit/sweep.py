"""Balayage des cartes (v2, sans fenetre : Moteur Unicorn seul, voir coverage.md section 5).
   python3 sweep.py DEB FIN [IMAGES] [OUTPUT.json] [SLOT]
   Pour chaque carte (indices DEB..FIN-1 de la liste triee des .stg de l'APK de donnees) : Global::startTown(nom), IMAGES pas de moteur, puis releve :
   - exception du moteur (PC + symbole) ; apres une exception le moteur est RECREE et la sauvegarde rechargee (la v1 propageait l'echec a toutes les cartes suivantes) ;
   - paquets : compte par type, valeurs distinctes des types rares (6, 16, 17, 18, 30, 31, 33, 34...), bits de drapeaux de 13 / 15 / 10 / 11, echelles de sprites (13 bit 0x800) ;
   - sprites (id, position finale), modeles de maillage / fbx demandes, sons demandes (BGM / SE), fenetres (ports, types) ouvertes, message visible, fondu restant, drapeaux, partie.
   L'analyse (textures manquantes, PNJ hors carte...) se fait ensuite sur le JSON (analysis.py)."""
import os, sys, json, time, zipfile, struct, collections, traceback
sys.path.insert(0, '/tmp/audit')
import hl
APK = hl.APK
RARE = (1, 6, 16, 17, 18, 23, 27, 30, 31, 33, 34, 8, 9, 5, 7, 2, 3, 4)
def names():
    z = zipfile.ZipFile(APK + '/split_UnityDataAssetPack.apk')
    return sorted(n.split('/')[-1][:-4] for n in z.namelist() if n.startswith('assets/map/') and n.endswith('.stg'))
def rounded(v): return [round(float(x), 3) for x in v]
def reading(m, name_str, frames):
    r = {'carte': name_str, 'ok': False}
    t0 = time.time(); types = collections.Counter(); vals = collections.defaultdict(list); flags13 = collections.Counter(); flags15 = collections.Counter(); scales = set()
    sounds = {'bgm': set(), 'se': set()}; mods = set(); fbx = set(); sprid = {}; cams = collections.Counter()
    before = m.state.loaded_maps; first_idx = None
    try:
        m.start_town(name_str)
        for i in range(frames):
            pkt = m.step(0, 0)
            for t, a, f in pkt:
                types[t] += 1
                if t in RARE and len(vals[t]) < 8:
                    v = (list(a[:4]), rounded(f[:4]))
                    if v not in vals[t]: vals[t].append(v)
                if t == 13 and a:
                    flags13[a[0] & 0xf800] += 1
                    if a[0] & 0x800 and f: scales.add(round(float(f[0]), 4))
                elif t == 15 and a: flags15[a[0] & 0xff00] += 1
                elif t == 10 and a: cams['10:%d' % (a[0] & 0xff)] += 1
                elif t == 11 and a: cams['11:%d' % (a[0] & 0xff)] += 1
                elif t == 12 and len(a) >= 2 and a[1] >= 0: sprid[a[0]] = a[1]
                elif t == 21 and len(a) >= 2 and a[1] >= 0: mods.add(a[1])
                elif t == 31 and len(a) >= 2 and a[1] >= 0: fbx.add(a[1])
                elif t == 37 and a: sounds['bgm'].add(a[0])
                elif t == 35 and a: sounds['se'].add(a[0])
            if first_idx is None and m.state.loaded_maps > before: first_idx = i
        e = m.state
        r.update(ok=True, charge_a=first_idx, map_view=e.game_map, partie=e.part, pkts={str(k): v for k, v in sorted(types.items())},
                 vals={str(k): v for k, v in vals.items()}, f13={hex(k): v for k, v in flags13.items()}, f15={hex(k): v for k, v in flags15.items()}, echelles=sorted(scales),
                 cams=dict(cams), bgm=sorted(sounds['bgm']), se=sorted(sounds['se']), modeles=sorted(mods), fbx=sorted(fbx), fond=rounded(e.background), msg=bool(m.msg_visible),
                 fondu=[e.fade['n'], e.background_fade['n']], flags=m.flags(),
                 ports=sorted((p, f.get('type')) for p, f in m.ui.f.items() if f.get('act') and p >= 2))
        r['sprites'] = {str(k): {'id': sprid.get(k, s['id']), 'pos': None if s['pos'] is None else rounded(s['pos']), 'vis': s.get('vis', True)} for k, s in e.sprites.items()}
        r['cam'] = {'pos': None if e.cam_pos is None else rounded(e.cam_pos), 'cible': None if e.cam_target is None else rounded(e.cam_target)}
    except Exception as ex:
        r['exc'] = repr(ex)[:400]; r['tb'] = traceback.format_exc()[-300:]
        try: r['pkts'] = {str(k): v for k, v in sorted(types.items())}
        except Exception: pass
    r['t'] = round(time.time() - t0, 2)
    return r
def engine(tag, slot):
    m = hl.new(tag)
    assert m.load_save(slot)
    for _ in range(10): m.step(0, 0)
    return m
if __name__ == '__main__':
    start_idx, end = int(sys.argv[1]), int(sys.argv[2]); frames = int(sys.argv[3]) if len(sys.argv) > 3 else 60
    output = sys.argv[4] if len(sys.argv) > 4 else '/tmp/audit/balayage2_%d_%d.json' % (start_idx, end)
    slot = int(sys.argv[5]) if len(sys.argv) > 5 else 1
    NAMES = names()
    tag = 'bal2_%d' % start_idx
    m = engine(tag, slot); res = {}; t0 = time.time(); recreated = 0
    for name_str in NAMES[start_idx:end]:
        res[name_str] = reading(m, name_str, frames)
        if not res[name_str]['ok'] and 'exc' in res[name_str]:
            print('FAILED', name_str, res[name_str]['exc'][:160].replace('\n', ' | '), flush=True)
            m = engine(tag, slot); recreated += 1
    json.dump(res, open(output, 'w'))
    print('%d maps in %.1f s (%d engines recreated)' % (len(res), time.time() - t0, recreated))
