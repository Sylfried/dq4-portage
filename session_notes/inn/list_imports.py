import os, sys, shutil, tempfile, re
sys.path.insert(0, '/home/claude/dq4-portage')
from dq4_pc.core import engine as ENGINE
m = ENGINE.Engine(os.environ['DQ_APK'], os.environ['DQ_SAVES'], tempfile.mkdtemp(prefix='sv_inn_'))
c = m.core
print(len(c.stub_names), 'stubs')
for n in c.stub_names:
    if re.search(r'Unity|Sound|Bgm|Play|Music|Audio|Fade', n): print(n)
print('--- exports Unity*')
for n in sorted(c.elf.exports):
    if n.startswith('_Z') and re.search(r'Unity', n): print(n)
