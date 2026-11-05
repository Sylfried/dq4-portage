"""Quels emetteurs du moteur ecrivent les paquets 19 / 20 (bulles) ? Balaie `mov w0, #0x13|#0x14` suivi d'un appel UnitySetPacket / UnityGetPacket."""
import sys, collections
sys.path.insert(0, '/tmp/claude-0/-home-claude/45fdf246-f4ad-5078-9633-8be9ccf9e9c9/scratchpad')
import scan as SC, plt as P
st = SC.stubs()
want = {a for a, n in st.items() if n.startswith('UnitySetPacket') or n.startswith('UnityGetPacket') or n in ('_Z14UnitySetPacketii', '_Z14UnityGetPacketii', '_Z14UnitySetPacketi', '_Z14UnityGetPacketi')}
print('stubs', {hex(a): n for a, n in st.items() if a in want})
last = {}      # derniere valeur mov w0, #imm vue (fenetre courte)
res = collections.defaultdict(list)
win = []
for ins in SC.balayer():
    if ins.mnemonic == 'mov' and ins.op_str.startswith('w0, #'):
        try: last['v'] = int(ins.op_str.split('#')[1], 0); last['at'] = ins.address
        except Exception: pass
    elif ins.mnemonic in ('bl',):
        try: t = int(ins.op_str.lstrip('#'), 16)
        except Exception: continue
        if t in want and last.get('v') in (19, 20) and ins.address - last['at'] <= 24:
            res[(last['v'], SC.fonction(ins.address)[1])].append(hex(ins.address))
        last = {}
for (v, f), a in sorted(res.items()): print(v, f, a)
