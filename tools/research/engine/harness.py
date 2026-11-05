"""Harnais sans fenetre : demarre le moteur (Moteur de dq4_pc), charge une sauvegarde et journalise TOUS les messages de menu moteur -> interface.
Usage (depuis un script) : from harnais import *; mo = demarrer(slot=4); ... mo.step(...)
Les messages (port, [shorts]) de chaque image sont gardes dans LOG = [(image, partie, port, args)]."""
import os, sys, struct
sys.path.insert(0, os.environ.get('DQ4_SRC', '/home/claude/wt-audit/dq4_pc'))
from dq4_pc.core import engine as ENGINE
APK = '/mnt/user-data/uploads/DQ Patch/jeux/DQ4/patched_apks'
SAVES = '/mnt/user-data/uploads/Downloads/DQ Patch/jeux/DQ4/saves/20261007_190735'
LOG = []

def start_engine(slot=4, write_dir='/tmp/r3_sv'):
    os.makedirs(write_dir, exist_ok=True)
    eng = ENGINE.Engine(APK, SAVES, write_dir)
    orig = eng.ui.apply
    def apply(entries, orig=orig):
        for port, a in entries: LOG.append((eng.frames, eng.state.part, port, list(a)))
        return orig(entries)
    eng.ui.apply = apply
    for _ in range(3): eng.step(0, 0)
    if slot: eng.load_save(slot)
    return eng

def advance_time(eng, n, held=0, decl=None):
    for _ in range(n): eng.step(held, decl)
