"""PROTOTYPE de l'outil de balayage des cartes (sans fenetre, Moteur seul) :
   python3 balayage_tete.py DEB FIN [IMAGES] [SORTIE.json]   -> pour chaque carte (indices DEB..FIN-1 de la liste triee des .stg) : demarrer_ville(nom), IMAGES pas de moteur,
   releve : exception du moteur, paquets vus (comptes par type), parties, sprites (id, position), cartes chargees, messages / menus ouverts, drapeaux, temps."""
import os, sys, json, time, zipfile, struct, collections, traceback
sys.path.insert(0, '/tmp/audit')
import hl
APK = hl.APK
z = zipfile.ZipFile(APK + '/split_UnityDataAssetPack.apk')
NOMS = sorted(n.split('/')[-1][:-4] for n in z.namelist() if n.startswith('assets/map/') and n.endswith('.stg'))
def balayer(m, nom, images):
    r = {'carte': nom, 'ok': False}
    t0 = time.time(); types = collections.Counter(); avant = m.etat.cartes_chargees
    try:
        m.demarrer_ville(nom)
        prem = None
        for i in range(images):
            pq = m.step(0, 0)
            for t, a, f in pq: types[t] += 1
            if prem is None and m.etat.cartes_chargees > avant: prem = i
        e = m.etat
        r.update(ok=True, charge_a=prem, carte_vue=e.carte, partie=e.partie, sprites=len(e.sprites), pkts=dict(types), fond=e.fond,
                 ports=sorted((p, f.get('type')) for p, f in m.ui.f.items() if f.get('act') and p >= 12), msg=bool(m.msg_visible), flags=m.drapeaux())
        hero = e.sprites.get(0)
        r['hero'] = None if not hero or hero['pos'] is None else [round(float(x), 2) for x in hero['pos']]
    except Exception as ex:
        r['exc'] = repr(ex)[:300]; r['tb'] = traceback.format_exc()[-600:]
    r['t'] = round(time.time() - t0, 2)
    return r
if __name__ == '__main__':
    deb, fin = int(sys.argv[1]), int(sys.argv[2]); images = int(sys.argv[3]) if len(sys.argv) > 3 else 60
    sortie = sys.argv[4] if len(sys.argv) > 4 else '/tmp/audit/balayage_%d_%d.json' % (deb, fin)
    m = hl.nouveau('bal%d' % deb); assert m.charger_sauvegarde(1)
    for _ in range(10): m.step(0, 0)
    res = {}; t0 = time.time()
    for nom in NOMS[deb:fin]:
        res[nom] = balayer(m, nom, images)
        if not res[nom]['ok']: print('ECHEC', nom, res[nom].get('exc'), flush=True)
    json.dump(res, open(sortie, 'w'))
    print('%d cartes en %.1fs' % (len(res), time.time() - t0))
