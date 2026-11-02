"""Balayage des cartes (v2, sans fenetre : Moteur Unicorn seul, voir couverture.md section 5).
   python3 balayage.py DEB FIN [IMAGES] [SORTIE.json] [SLOT]
   Pour chaque carte (indices DEB..FIN-1 de la liste triee des .stg de l'APK de donnees) : Global::startTown(nom), IMAGES pas de moteur, puis releve :
   - exception du moteur (PC + symbole) ; apres une exception le moteur est RECREE et la sauvegarde rechargee (la v1 propageait l'echec a toutes les cartes suivantes) ;
   - paquets : compte par type, valeurs distinctes des types rares (6, 16, 17, 18, 30, 31, 33, 34...), bits de drapeaux de 13 / 15 / 10 / 11, echelles de sprites (13 bit 0x800) ;
   - sprites (id, position finale), modeles de maillage / fbx demandes, sons demandes (BGM / SE), fenetres (ports, types) ouvertes, message visible, fondu restant, drapeaux, partie.
   L'analyse (textures manquantes, PNJ hors carte...) se fait ensuite sur le JSON (analyse.py)."""
import os, sys, json, time, zipfile, struct, collections, traceback
sys.path.insert(0, '/tmp/audit')
import hl
APK = hl.APK
RARES = (1, 6, 16, 17, 18, 23, 27, 30, 31, 33, 34, 8, 9, 5, 7, 2, 3, 4)
def noms():
    z = zipfile.ZipFile(APK + '/split_UnityDataAssetPack.apk')
    return sorted(n.split('/')[-1][:-4] for n in z.namelist() if n.startswith('assets/map/') and n.endswith('.stg'))
def arrondi(v): return [round(float(x), 3) for x in v]
def releve(m, nom, images):
    r = {'carte': nom, 'ok': False}
    t0 = time.time(); types = collections.Counter(); vals = collections.defaultdict(list); flags13 = collections.Counter(); flags15 = collections.Counter(); echelles = set()
    sons = {'bgm': set(), 'se': set()}; mods = set(); fbx = set(); sprid = {}; cams = collections.Counter()
    avant = m.etat.cartes_chargees; prem = None
    try:
        m.demarrer_ville(nom)
        for i in range(images):
            pq = m.step(0, 0)
            for t, a, f in pq:
                types[t] += 1
                if t in RARES and len(vals[t]) < 8:
                    v = (list(a[:4]), arrondi(f[:4]))
                    if v not in vals[t]: vals[t].append(v)
                if t == 13 and a:
                    flags13[a[0] & 0xf800] += 1
                    if a[0] & 0x800 and f: echelles.add(round(float(f[0]), 4))
                elif t == 15 and a: flags15[a[0] & 0xff00] += 1
                elif t == 10 and a: cams['10:%d' % (a[0] & 0xff)] += 1
                elif t == 11 and a: cams['11:%d' % (a[0] & 0xff)] += 1
                elif t == 12 and len(a) >= 2 and a[1] >= 0: sprid[a[0]] = a[1]
                elif t == 21 and len(a) >= 2 and a[1] >= 0: mods.add(a[1])
                elif t == 31 and len(a) >= 2 and a[1] >= 0: fbx.add(a[1])
                elif t == 37 and a: sons['bgm'].add(a[0])
                elif t == 35 and a: sons['se'].add(a[0])
            if prem is None and m.etat.cartes_chargees > avant: prem = i
        e = m.etat
        r.update(ok=True, charge_a=prem, carte_vue=e.carte, partie=e.partie, pkts={str(k): v for k, v in sorted(types.items())},
                 vals={str(k): v for k, v in vals.items()}, f13={hex(k): v for k, v in flags13.items()}, f15={hex(k): v for k, v in flags15.items()}, echelles=sorted(echelles),
                 cams=dict(cams), bgm=sorted(sons['bgm']), se=sorted(sons['se']), modeles=sorted(mods), fbx=sorted(fbx), fond=arrondi(e.fond), msg=bool(m.msg_visible),
                 fondu=[e.fondu['n'], e.fondu_fond['n']], drapeaux=m.drapeaux(),
                 ports=sorted((p, f.get('type')) for p, f in m.ui.f.items() if f.get('act') and p >= 2))
        r['sprites'] = {str(k): {'id': sprid.get(k, s['id']), 'pos': None if s['pos'] is None else arrondi(s['pos']), 'vis': s.get('vis', True)} for k, s in e.sprites.items()}
        r['cam'] = {'pos': None if e.cam_pos is None else arrondi(e.cam_pos), 'cible': None if e.cam_cible is None else arrondi(e.cam_cible)}
    except Exception as ex:
        r['exc'] = repr(ex)[:400]; r['tb'] = traceback.format_exc()[-300:]
        try: r['pkts'] = {str(k): v for k, v in sorted(types.items())}
        except Exception: pass
    r['t'] = round(time.time() - t0, 2)
    return r
def moteur(tag, slot):
    m = hl.nouveau(tag)
    assert m.charger_sauvegarde(slot)
    for _ in range(10): m.step(0, 0)
    return m
if __name__ == '__main__':
    deb, fin = int(sys.argv[1]), int(sys.argv[2]); images = int(sys.argv[3]) if len(sys.argv) > 3 else 60
    sortie = sys.argv[4] if len(sys.argv) > 4 else '/tmp/audit/balayage2_%d_%d.json' % (deb, fin)
    slot = int(sys.argv[5]) if len(sys.argv) > 5 else 1
    NOMS = noms()
    tag = 'bal2_%d' % deb
    m = moteur(tag, slot); res = {}; t0 = time.time(); recrees = 0
    for nom in NOMS[deb:fin]:
        res[nom] = releve(m, nom, images)
        if not res[nom]['ok'] and 'exc' in res[nom]:
            print('ECHEC', nom, res[nom]['exc'][:160].replace('\n', ' | '), flush=True)
            m = moteur(tag, slot); recrees += 1
    json.dump(res, open(sortie, 'w'))
    print('%d cartes en %.1f s (%d moteurs recrees)' % (len(res), time.time() - t0, recrees))
