"""Graphe d'appels de libdq4core.so (bl / b directs, PLT resolus) -> /tmp/audit/cg.pkl : {nom_appele: {nom_appelant, ...}}.
Usage : python3 callgraph.py build | python3 callgraph.py up NOM [profondeur]   (appelants, recursifs, par sous-chaine de nom)"""
import sys, pickle, os, collections, bisect
sys.path.insert(0, '/tmp/specs')
CG = '/tmp/audit/cg.pkl'
def build():
    import disasm_engine as D
    from capstone import CS_ARCH_ARM64, CS_MODE_ARM, Cs
    from capstone.arm64 import ARM64_OP_IMM
    md = D.md; md.skipdata = True
    lo, hi = min(D.syms), 0x233960
    code = D.rd(lo, hi - lo)
    starts = sorted(D.syms)
    nm = lambda a: D.syms[starts[bisect.bisect_right(starts, a) - 1]]
    cg = collections.defaultdict(set); cache = {}
    for ins in md.disasm(code, lo):
        if ins.mnemonic in ('bl', 'b') and ins.operands[0].type == ARM64_OP_IMM:
            t = ins.operands[0].imm
            if t in D.syms: callee = D.syms[t]
            else:
                if t not in cache: cache[t] = D.plt_target(t)
                callee = cache[t]
                if not callee: continue
            caller = nm(ins.address)
            if caller != callee: cg[callee].add(caller)
    pickle.dump(dict(cg), open(CG, 'wb'))
    print('graph:', len(cg), 'called')
def up(sub, prof=2):
    cg = pickle.load(open(CG, 'rb'))
    targets = [k for k in cg if sub in k]
    for c in targets[:6]:
        print(c)
        level_nodes = [c]; seen = {c}
        for d in range(prof):
            nxt = []
            for x in level_nodes:
                for y in sorted(cg.get(x, ())):
                    if y in seen: continue
                    seen.add(y); nxt.append(y); print('  ' * (d + 1) + '<- ' + y)
            level_nodes = nxt
if __name__ == '__main__':
    if sys.argv[1] == 'build': build()
    else: up(sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 2)
