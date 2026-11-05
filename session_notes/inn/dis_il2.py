import os, sys
os.environ['DQ_IL2'] = '/tmp/claude-0/-home-claude/45fdf246-f4ad-5078-9633-8be9ccf9e9c9/scratchpad/inn/il2'
sys.path.insert(0, '/home/claude/dq4-portage/tools/ui_il2cpp')
import disasm as d
a, b = int(sys.argv[1], 16), int(sys.argv[2], 16)
print("\n".join(d.dis(a, b)))
