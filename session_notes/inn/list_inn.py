import os, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from h import *
m = ENGINE.Engine(APK, SAVES, tempfile.mkdtemp(prefix='sv_inn_'))
for n in sorted(m.core.elf.exports):
    if 'INN' in n or 'Inn' in n or 'inn' in n.lower() and 'Materiel' in n: print(n)
