import sys; sys.path.insert(0,'/tmp/claude-0/-home-claude/45fdf246-f4ad-5078-9633-8be9ccf9e9c9/scratchpad/textpos')
from tp_lib import *
ty = 31
for s in ('Rat volant', 'Glacyclone\n\n\t×2', 'Scarapince\n\n\t×10', 'Scarapince\n\n\t×3'):
    outs = {}
    for mode in 'PVO':
        m = MODES[mode]; r = apply_mode(m)
        w = UM.Window(ml, ty)
        nb, nt = w._plate_nodes(0)
        w.plate(0, s, [0]*6, 1)
        node = w.N[nt]
        res = measure_node(w, node, r)
        nc = w.N[nb]
        xs = [nc['pos'][0] + v[0] for v in nc['vtx']]; zs = [nc['pos'][2] + v[1] for v in nc['vtx']]
        outs[mode] = (res['lines'], round(res['xl'],1), round(res['xr'],1), round(res['base0'],2), round(res['ts'],3), (round(min(xs),1), round(max(xs),1), round(min(zs),1), round(max(zs),1)), node['text']['anchor'], node['text']['alignment'], round(node['text']['lineSpacing'],3), node['text']['characterSize'], node['text'].get('tabSize'))
    print(repr(s)); 
    for k,v in outs.items(): print('  ', k, v)
