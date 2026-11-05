"""PROTOTYPE de l'outil de balayage des cartes (sans fenetre, Moteur seul) :
   python3 sweep_head.py DEB FIN [IMAGES] [OUTPUT.json]   -> pour chaque carte (indices DEB..FIN-1 de la liste triee des .stg) : start_town(nom), IMAGES pas de moteur,
   releve : exception du moteur, paquets vus (comptes par type), parties, sprites (id, position), cartes chargees, messages / menus ouverts, drapeaux, temps."""
import os, sys, json, time, zipfile, struct, collections, traceback
sys.path.insert(0, '/tmp/audit')
import hl
APK = hl.APK
z = zipfile.ZipFile(APK + '/split_UnityDataAssetPack.apk')
NAMES = sorted(n.split('/')[-1][:-4] for n in z.namelist() if n.startswith('assets/map/') and n.endswith('.stg'))
def run_sweep(m, name_str, frames):
    r = {'carte': name_str, 'ok': False}
    t0 = time.time(); types = collections.Counter(); before = m.state.loaded_maps
    try:
        m.start_town(name_str)
        first_idx = None
        for i in range(frames):
            pkt = m.step(0, 0)
            for t, a, f in pkt: types[t] += 1
            if first_idx is None and m.state.loaded_maps > before: first_idx = i
        e = m.state
        r.update(ok=True, charge_a=first_idx, map_view=e.game_map, partie=e.part, sprites=len(e.sprites), pkts=dict(types), fond=e.background,
                 ports=sorted((p, f.get('type')) for p, f in m.ui.f.items() if f.get('act') and p >= 12), msg=bool(m.msg_visible), flags=m.flags())
        hero = e.sprites.get(0)
        r['hero'] = None if not hero or hero['pos'] is None else [round(float(x), 2) for x in hero['pos']]
    except Exception as ex:
        r['exc'] = repr(ex)[:300]; r['tb'] = traceback.format_exc()[-600:]
    r['t'] = round(time.time() - t0, 2)
    return r
if __name__ == '__main__':
    start_idx, end = int(sys.argv[1]), int(sys.argv[2]); frames = int(sys.argv[3]) if len(sys.argv) > 3 else 60
    output = sys.argv[4] if len(sys.argv) > 4 else '/tmp/audit/balayage_%d_%d.json' % (start_idx, end)
    m = hl.new('bal%d' % start_idx); assert m.load_save(1)
    for _ in range(10): m.step(0, 0)
    res = {}; t0 = time.time()
    for name_str in NAMES[start_idx:end]:
        res[name_str] = run_sweep(m, name_str, frames)
        if not res[name_str]['ok']: print('ECHEC', name_str, res[name_str].get('exc'), flush=True)
    json.dump(res, open(output, 'w'))
    print('%d cartes en %.1fs' % (len(res), time.time() - t0))
