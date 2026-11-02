"""Harnais sans fenetre : demarre le moteur (Moteur de dq4_pc), charge une sauvegarde et journalise TOUS les messages de menu moteur -> interface.
Usage (depuis un script) : from harnais import *; mo = demarrer(slot=4); ... mo.step(...)
Les messages (port, [shorts]) de chaque image sont gardes dans JOURNAL = [(image, partie, port, args)]."""
import os, sys, struct
sys.path.insert(0, os.environ.get('DQ4_SRC', '/home/claude/wt-audit/dq4_pc'))
import moteur as MO
APK = '/mnt/user-data/uploads/DQ Patch/jeux/DQ4/patched_apks'
SAVES = '/mnt/user-data/uploads/Downloads/DQ Patch/jeux/DQ4/saves/20261007_190735'
JOURNAL = []

def demarrer(slot=4, ecriture='/tmp/r3_sv'):
    os.makedirs(ecriture, exist_ok=True)
    mo = MO.Moteur(APK, SAVES, ecriture)
    orig = mo.ui.appliquer
    def appliquer(liste, orig=orig):
        for port, a in liste: JOURNAL.append((mo.images, mo.etat.partie, port, list(a)))
        return orig(liste)
    mo.ui.appliquer = appliquer
    for _ in range(3): mo.step(0, 0)
    if slot: mo.charger_sauvegarde(slot)
    return mo

def avancer(mo, n, tenu=0, decl=None):
    for _ in range(n): mo.step(tenu, decl)
