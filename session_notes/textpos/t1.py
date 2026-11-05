import sys; sys.path.insert(0,'/tmp/claude-0/-home-claude/45fdf246-f4ad-5078-9633-8be9ccf9e9c9/scratchpad/textpos')
from tp_lib import *
print(text_cells(35)[:14])
for mode in 'PVO':
    r = measure(35, 0, 1, 'Coût en PM:\t  2', mode)   # (id 0, no 1)
    print(mode, {k: (round(v,2) if isinstance(v,float) else v) for k,v in r.items() if k!='quads'})
