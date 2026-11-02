"""Mesure avant / apres de la retenue du dessin (Etat.chargement) : pour chaque changement de carte, images du moteur ou la scene serait visible (au moins 2 %) alors qu'elle n'est pas en place.
usage : python3 mesure.py MODE SCENARIO [args]   MODE : avant (retenue desactivee) | apres ; SCENARIO : marche SLOT DIR N | tp SLOT n1,n2,... | mort SLOT MONSTRE | etat SLOT"""
from scen import *
import copy

def configurer(mode):
    MO.Etat.vitesse_fondu = 2.0          # reglage par defaut de la visionneuse (fondus au noir deux fois plus courts)
    if mode == 'avant': MO.Etat.maj_chargement = lambda self: setattr(self, 'chargement', None)          # jamais de retenue : comportement d'origine

def instantane(m):
    e = m.etat
    return dict(img=m.images, carte=e.carte, partie=e.partie, cam=None if e.cam_pos is None else tuple(round(float(x), 2) for x in e.cam_pos),
                cib=None if e.cam_cible is None else tuple(round(float(x), 2) for x in e.cam_cible),
                spr={k: (None if s['pos'] is None else tuple(round(float(x), 1) for x in s['pos'])) for k, s in e.sprites.items() if s.get('vis', True)},
                fa=e.fondu['a'], ba=e.fondu_fond['a'], fn=e.fondu['n'], bn=e.fondu_fond['n'], retenu=e.chargement is not None, champ=e.champ is not None, cc=e.cartes_chargees)

def analyser(traj, cc_avant, etiquette, verbeux=False):
    """traj : liste d'instantanes apres chaque pas. Pour chaque chargement (cartes_chargees qui augmente) : etat « final » = celui 8 pas apres, ou le dernier avant l'ouverture complete du fondu."""
    res = []
    i = 0; n = len(traj)
    while i < n:
        if traj[i]['cc'] > (traj[i - 1]['cc'] if i else cc_avant):
            k = i; fin = traj[min(n - 1, k + 8)]
            avant_cam = traj[k - 1]['cam'] if k else None
            vis_def = []; vis_tot = []; tenu = 0
            for j in range(k, min(n, k + 40)):
                s = traj[j]
                if j > k and s['cc'] > traj[k]['cc']: break
                vis = (1 - s['fa']) * (1 - s['ba'])
                camp = not (s['cam'] is None and fin['cam'] is not None) and not (avant_cam is not None and s['cam'] == avant_cam and fin['cam'] != avant_cam)      # camera pas encore envoyee, ou encore celle de la carte d'avant
                sp_ok = all(s['spr'].get(c) is not None for c, p in fin['spr'].items() if p is not None)
                monde_ok = s['partie'] != MO.PARTIE_CHAMP or s['champ']
                pret = camp and sp_ok and monde_ok
                visible = vis >= 0.02 and not s['retenu']
                if s['retenu']: tenu += 1
                if visible: vis_tot.append(j - k)
                if visible and not pret: vis_def.append((j - k, round(vis, 2), 'cam' if not camp else '', 'spr' if not sp_ok else '', 'monde' if not monde_ok else ''))
                if verbeux: print('   +%d fa=%.2f ba=%.2f vis=%.2f retenu=%d pret=%d cam=%s' % (j - k, s['fa'], s['ba'], vis, s['retenu'], pret, s['cam']))
            res.append((etiquette, traj[k]['img'], traj[k - 1]['carte'] if k else None, traj[k]['carte'], len(vis_def), vis_def[:4], tenu, vis_tot[:1]))
            i = k + 1
        else: i += 1
    return res

def afficher(res):
    for etiq, img, de, vers, nd, det, tenu, v1 in res:
        print('%-10s img %5d %s -> %-8s : %d image(s) visible(s) avec scene pas en place %s | images retenues %d | 1re image visible +%s' % (etiq, img, de, vers, nd, det, tenu, v1[0] if v1 else None))

if __name__ == '__main__':
    mode, scen = sys.argv[1], sys.argv[2]; configurer(mode)
    verb = os.environ.get('V') == '1'
    if scen == 'marche':
        slot, d, N = int(sys.argv[3]), int(sys.argv[4], 0), int(sys.argv[5])
        m = nouveau('ms_%s_%s_%s' % (mode, slot, d)); m.charger_sauvegarde(slot); traj = []; cc0 = m.etat.cartes_chargees
        for i in range(N):
            a = 0; tenu = 0
            if m.msg_visible and i % 12 == 0: a = 0x10
            elif not m.msg_visible and m.menu_actif() is None: tenu = d
            m.step(tenu, a); traj.append(instantane(m))
        afficher(analyser(traj, cc0, 'marche%d' % slot, verb))

    elif scen == 'mort':
        OFF_HP = 0x22; PAS_JOUEUR, OFF_HAVESTATUS = 0x530, 0x58
        slot, mon, N = int(sys.argv[3]), int(sys.argv[4]), int(sys.argv[5])
        m = nouveau('mm_%s_%s' % (mode, sys.argv[3])); m.charger_sauvegarde(slot); c = m.core
        for _ in range(200): m.step(0, 0)
        cc0 = m.etat.cartes_chargees; traj = []
        party = c.export('_ZN6status7g_PartyE'); orig = c.export('_ZN6status9PartyData15originalPlayer_E')
        membres = [i for i in struct.unpack('<13I', c.mem(party + 0x304, 13 * 4)) if i]
        for i in membres: c.mem_w(orig + PAS_JOUEUR * i + OFF_HAVESTATUS + OFF_HP, struct.pack('<H', 1))
        enc = c.call(c.export('_ZN7Encount12getSingletonEv'), label='enc')
        def forcer(u, adr, sz, ud):
            for j in range(4):
                i, n = (mon, 3) if j == 0 else (0, 0)
                c.mem_w(enc + 0x34 + 4 * j, struct.pack('<I', i)); c.mem_w(enc + 0x44 + 4 * j, struct.pack('<I', n))
        a = c.export('_ZN10BattleRoot12setupMonsterEv'); c.uc.hook_add(unicorn.UC_HOOK_CODE, forcer, None, a, a); c.uc.ctl_flush_tb()
        c.call(c.export('_ZN6Global11startBattleEv'), m._global(), label='startBattle')
        rel = None; att = 0
        for i in range(N):
            p = d = 0
            if rel is not None: m.envoyer_menu(rel, 1, -1, 0); rel = None
            port = m.menu_actif()
            if port is not None and not m.msg_visible:
                att += 1
                if att % 4 == 0: m.envoyer_menu(port, 1, -1, 0x10); rel = port
            elif m.msg_visible and (m.ui.msg.get('feed') or m.etat_message()[1] in (3, 5)):
                att += 1
                if att % 4 == 0: p = d = MO.A
            else: att = 0
            m.step(p, d); m.ui.degats = []; traj.append(instantane(m))
        afficher(analyser(traj, cc0, 'mort', verb))
    elif scen == 'tp':
        slot = int(sys.argv[3]); noms = sys.argv[4].split(',')
        m = nouveau('mt_%s_%s' % (mode, slot)); m.charger_sauvegarde(slot)
        for _ in range(100): m.step(0, 0)
        for nom in noms:
            cc0 = m.etat.cartes_chargees; traj = []
            try: m.demarrer_ville(nom)
            except Exception as ex: print('EXC', nom, repr(ex)[:80]); continue
            for i in range(40): m.step(0, 0); traj.append(instantane(m))
            afficher(analyser(traj, cc0, 'tp', verb))

    elif scen == 'tpmax':
        import zipfile
        APKZ = zipfile.ZipFile(APK + '/split_UnityDataAssetPack.apk')
        noms = sorted(n.split('/')[-1][:-4] for n in APKZ.namelist() if n.startswith('assets/map/') and n.endswith('.stg'))
        noms = [n for n in noms if not n.startswith('btl') and n not in ('ev01',)]
        slot, pas, dec = int(sys.argv[3]), int(sys.argv[4]), int(sys.argv[5])
        m = nouveau('mx_%s_%s_%s' % (mode, slot, dec)); m.charger_sauvegarde(slot)
        for _ in range(100): m.step(0, 0)
        stats = collections.Counter(); defauts = 0; n_ok = 0; longs = []
        for nom in noms[dec::pas]:
            cc0 = m.etat.cartes_chargees; traj = []
            try: m.demarrer_ville(nom)
            except Exception as ex: print('EXC', nom, repr(ex)[:80]); continue
            try:
                for i in range(40): m.step(0, 0); traj.append(instantane(m))
            except Exception as ex: print('EXC pas', nom, repr(ex)[:80]); break
            for etiq, img, de, vers, nd, det, tenu, v1 in analyser(traj, cc0, 'tp'):
                stats[tenu] += 1; defauts += nd; n_ok += 1
                if nd: longs.append((vers, nd, det[:1]))
        print('%s : %d chargements ; images retenues (histogramme) %s ; images visibles avec scene pas en place : %d au total, sur %d chargements %s' % (mode, n_ok, dict(sorted(stats.items())), defauts, len(longs), longs[:5]))
    elif scen == 'monde':
        slot = int(sys.argv[3]); m = nouveau('mw_%s_%s' % (mode, slot)); m.charger_sauvegarde(slot)
        for _ in range(100): m.step(0, 0)
        for etiq, f in (('champ', lambda: m.demarrer_champ()), ('ville', lambda: m.demarrer_ville(sys.argv[4]))):
            cc0 = m.etat.cartes_chargees; traj = []
            try: f()
            except Exception as ex: print('EXC', etiq, repr(ex)[:100]); continue
            for i in range(60): m.step(0, 0); traj.append(instantane(m))
            afficher(analyser(traj, cc0, etiq, verb))
