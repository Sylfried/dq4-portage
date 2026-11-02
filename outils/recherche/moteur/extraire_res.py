"""Extrait de base.apk MenuTexture / Button / Font et de datapack (frameData) -> /tmp/r3_res (comme ui_menu.preparer_ressources)."""
import sys, os
sys.path.insert(0, '/home/claude/dq4-portage/dq4_pc')
APK = '/mnt/user-data/uploads/DQ Patch/jeux/DQ4/patched_apks'
out = sys.argv[1] if len(sys.argv) > 1 else '/tmp/r3_res'
import ui_menu
print(ui_menu.preparer_ressources(APK, out))
