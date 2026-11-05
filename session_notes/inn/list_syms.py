import os, sys, shutil, tempfile
sys.path.insert(0, '/home/claude/dq4-portage')
from dq4_pc.core import engine as ENGINE
APK = os.environ['DQ_APK']; SAVES = os.environ['DQ_SAVES']
f = tempfile.mkdtemp(prefix='sv_inn_')
m = ENGINE.Engine(APK, SAVES, f)
import re
names = [n for n in m.core.elf.exports if re.search(r'Sound|Bgm|BGM|Jingle|Music|isPlay|IsPlay|Playing|Se[A-Z]|Fanfare', n)]
for n in sorted(names): print(n)
shutil.rmtree(f, ignore_errors=True)
