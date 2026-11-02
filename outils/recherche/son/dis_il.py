import os, sys
os.environ['DQ_IL2'] = '/home/claude/il2'
sys.path.insert(0, '/home/claude/dq4-portage/outils/ui_il2cpp')
import desasm as d
a, b = int(sys.argv[1], 16), int(sys.argv[2], 16)
print("\n".join(d.dis(a, b)))
