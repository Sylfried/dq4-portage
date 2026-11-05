"""Mesure avant / apres de la retenue du dessin (State.chargement) : pour chaque changement de carte, images du moteur ou la scene serait visible (au moins 2 %) alors qu'elle n'est pas en place.
usage : python3 measure.py MODE SCENARIO [args]   MODE : avant (retenue desactivee) | apres ; SCENARIO : marche SLOT DIR N | tp SLOT n1,n2,... | mort SLOT MONSTRE | etat SLOT"""
from scen import *
import copy

def configure(mode):
    ENGINE.State.fade_speed = 2.0          # reglage par defaut de la visionneuse (fondus au noir deux fois plus courts)
    if mode == 'avant': ENGINE.State.update_loading = lambda self: setattr(self, 'loading', None)          # jamais de retenue : comportement d'origine

def snapshot(m):
    e = m.state
    return dict(img=m.frames, carte=e.game_map, partie=e.part, cam=None if e.cam_pos is None else tuple(round(float(x), 2) for x in e.cam_pos),
                cib=None if e.cam_target is None else tuple(round(float(x), 2) for x in e.cam_target),
                spr={k: (None if s['pos'] is None else tuple(round(float(x), 1) for x in s['pos'])) for k, s in e.sprites.items() if s.get('vis', True)},
                fa=e.fade['a'], ba=e.background_fade['a'], fn=e.fade['n'], bn=e.background_fade['n'], retenu=e.loading is not None, champ=e.field is not None, cc=e.loaded_maps)

def analyze(traj, maps_loaded_before, tag_label, verbose=False):
    """traj : liste d'instantanes apres chaque pas. Pour chaque chargement (loaded_maps qui augmente) : etat « final » = celui 8 pas apres, ou le dernier avant l'ouverture complete du fondu."""
    res = []
    i = 0; n = len(traj)
    while i < n:
        if traj[i]['cc'] > (traj[i - 1]['cc'] if i else maps_loaded_before):
            k = i; end = traj[min(n - 1, k + 8)]
            before_cam = traj[k - 1]['cam'] if k else None
            vis_deficient = []; vis_tot = []; held = 0
            for j in range(k, min(n, k + 40)):
                s = traj[j]
                if j > k and s['cc'] > traj[k]['cc']: break
                vis = (1 - s['fa']) * (1 - s['ba'])
                camp = not (s['cam'] is None and end['cam'] is not None) and not (before_cam is not None and s['cam'] == before_cam and end['cam'] != before_cam)      # camera pas encore envoyee, ou encore celle de la carte d'avant
                sp_ok = all(s['spr'].get(c) is not None for c, p in end['spr'].items() if p is not None)
                world_ok = s['partie'] != ENGINE.PART_FIELD or s['champ']
                ready = camp and sp_ok and world_ok
                visible = vis >= 0.02 and not s['retenu']
                if s['retenu']: held += 1
                if visible: vis_tot.append(j - k)
                if visible and not ready: vis_deficient.append((j - k, round(vis, 2), 'cam' if not camp else '', 'spr' if not sp_ok else '', 'monde' if not world_ok else ''))
                if verbose: print('   +%d fa=%.2f ba=%.2f vis=%.2f held=%d ready=%d cam=%s' % (j - k, s['fa'], s['ba'], vis, s['retenu'], ready, s['cam']))
            res.append((tag_label, traj[k]['img'], traj[k - 1]['carte'] if k else None, traj[k]['carte'], len(vis_deficient), vis_deficient[:4], held, vis_tot[:1]))
            i = k + 1
        else: i += 1
    return res

def show(res):
    for lbl, img, from_, toward, node, det, held, v1 in res:
        print('%-10s frame %5d %s -> %-8s : %d visible frame(s) with scene not in place %s | frames held %d | 1st visible frame +%s' % (lbl, img, from_, toward, node, det, held, v1[0] if v1 else None))

if __name__ == '__main__':
    mode, scen = sys.argv[1], sys.argv[2]; configure(mode)
    verb = os.environ.get('V') == '1'
    if scen == 'marche':
        slot, d, N = int(sys.argv[3]), int(sys.argv[4], 0), int(sys.argv[5])
        m = new('ms_%s_%s_%s' % (mode, slot, d)); m.load_save(slot); traj = []; cc0 = m.state.loaded_maps
        for i in range(N):
            a = 0; held = 0
            if m.msg_visible and i % 12 == 0: a = 0x10
            elif not m.msg_visible and m.active_menu() is None: held = d
            m.step(held, a); traj.append(snapshot(m))
        show(analyze(traj, cc0, 'walk%d' % slot, verb))

    elif scen == 'mort':
        OFF_HP = 0x22; PLAYER_STRIDE, OFF_HAVESTATUS = 0x530, 0x58
        slot, mon, N = int(sys.argv[3]), int(sys.argv[4]), int(sys.argv[5])
        m = new('mm_%s_%s' % (mode, sys.argv[3])); m.load_save(slot); c = m.core
        for _ in range(200): m.step(0, 0)
        cc0 = m.state.loaded_maps; traj = []
        party = c.export('_ZN6status7g_PartyE'); orig = c.export('_ZN6status9PartyData15originalPlayer_E')
        members = [i for i in struct.unpack('<13I', c.mem(party + 0x304, 13 * 4)) if i]
        for i in members: c.mem_w(orig + PLAYER_STRIDE * i + OFF_HAVESTATUS + OFF_HP, struct.pack('<H', 1))
        enc = c.call(c.export('_ZN7Encount12getSingletonEv'), label='enc')
        def force(u, addr, sz, ud):
            for j in range(4):
                i, n = (mon, 3) if j == 0 else (0, 0)
                c.mem_w(enc + 0x34 + 4 * j, struct.pack('<I', i)); c.mem_w(enc + 0x44 + 4 * j, struct.pack('<I', n))
        a = c.export('_ZN10BattleRoot12setupMonsterEv'); c.uc.hook_add(unicorn.UC_HOOK_CODE, force, None, a, a); c.uc.ctl_flush_tb()
        c.call(c.export('_ZN6Global11startBattleEv'), m._global(), label='startBattle')
        rel = None; att = 0
        for i in range(N):
            p = d = 0
            if rel is not None: m.send_menu(rel, 1, -1, 0); rel = None
            port = m.active_menu()
            if port is not None and not m.msg_visible:
                att += 1
                if att % 4 == 0: m.send_menu(port, 1, -1, 0x10); rel = port
            elif m.msg_visible and (m.ui.msg.get('feed') or m.message_state()[1] in (3, 5)):
                att += 1
                if att % 4 == 0: p = d = ENGINE.A
            else: att = 0
            m.step(p, d); m.ui.damage = []; traj.append(snapshot(m))
        show(analyze(traj, cc0, 'mort', verb))
    elif scen == 'tp':
        slot = int(sys.argv[3]); names = sys.argv[4].split(',')
        m = new('mt_%s_%s' % (mode, slot)); m.load_save(slot)
        for _ in range(100): m.step(0, 0)
        for name_str in names:
            cc0 = m.state.loaded_maps; traj = []
            try: m.start_town(name_str)
            except Exception as ex: print('EXC', name_str, repr(ex)[:80]); continue
            for i in range(40): m.step(0, 0); traj.append(snapshot(m))
            show(analyze(traj, cc0, 'tp', verb))

    elif scen == 'tpmax':
        import zipfile
        APKZ = zipfile.ZipFile(APK + '/split_UnityDataAssetPack.apk')
        names = sorted(n.split('/')[-1][:-4] for n in APKZ.namelist() if n.startswith('assets/map/') and n.endswith('.stg'))
        names = [n for n in names if not n.startswith('btl') and n not in ('ev01',)]
        slot, step, dec = int(sys.argv[3]), int(sys.argv[4]), int(sys.argv[5])
        m = new('mx_%s_%s_%s' % (mode, slot, dec)); m.load_save(slot)
        for _ in range(100): m.step(0, 0)
        stats = collections.Counter(); defaults = 0; n_ok = 0; longs = []
        for name_str in names[dec::step]:
            cc0 = m.state.loaded_maps; traj = []
            try: m.start_town(name_str)
            except Exception as ex: print('EXC', name_str, repr(ex)[:80]); continue
            try:
                for i in range(40): m.step(0, 0); traj.append(snapshot(m))
            except Exception as ex: print('EXC step', name_str, repr(ex)[:80]); break
            for lbl, img, from_, toward, node, det, held, v1 in analyze(traj, cc0, 'tp'):
                stats[held] += 1; defaults += node; n_ok += 1
                if node: longs.append((toward, node, det[:1]))
        print('%s : %d loads ; frames held (histogram) %s ; visible frames with scene not in place: %d in total, over %d loads %s' % (mode, n_ok, dict(sorted(stats.items())), defaults, len(longs), longs[:5]))
    elif scen == 'monde':
        slot = int(sys.argv[3]); m = new('mw_%s_%s' % (mode, slot)); m.load_save(slot)
        for _ in range(100): m.step(0, 0)
        for lbl, f in (('champ', lambda: m.start_field()), ('ville', lambda: m.start_town(sys.argv[4]))):
            cc0 = m.state.loaded_maps; traj = []
            try: f()
            except Exception as ex: print('EXC', lbl, repr(ex)[:100]); continue
            for i in range(60): m.step(0, 0); traj.append(snapshot(m))
            show(analyze(traj, cc0, lbl, verb))
