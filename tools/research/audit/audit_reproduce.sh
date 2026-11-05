#!/bin/bash
# audit_reproduce.sh : regenere les listages d'assembleur cites dans /tmp/specs/audit_menus_pave.md (sortie dans /tmp/r4_repro/).
# Prerequis : /home/claude/il2 (dump.cs, libil2cpp.so decompose), /tmp/libdq4core.so, capstone, UnityPy. Aucun fichier du depot n'est modifie.
# Usage : bash audit_reproduce.sh
set -e
S=/tmp/specs/scripts
O=/tmp/r4_repro; mkdir -p "$O"
export DQ_IL2=/home/claude/il2
dis() { python3 -I "$S/audit_dis.py" "$1" "$2" > "$O/$3.txt"; echo "$3 : $1 .. $2"; }

# --- TouchPad (classe UnityEngine / dump.cs ligne ~265000 : champs et constantes)
dis 0xD22DE4 0xD22E60 SetPosPadSize
dis 0xD22E60 0xD22FF0 SetPadPos
dis 0xD227A4 0xD22920 SetPadBlink
dis 0xD2359C 0xD2377C SetVisibleColMove
dis 0xD2377C 0xD23938 CreateMenuButton
dis 0xD23254 0xD23358 IconVisible
dis 0xD23C2C 0xD241B4 MoveCheck
dis 0xD241B4 0xD2538C internalUpdate
dis 0xD2538C 0xD25A00 FixedUpdate
# --- Fenetre de carte (type 25), compteur de quantite (type 9), bouton de carte (types 22/23)
dis 0xCF0684 0xCF0800 Make_CityMap
dis 0xD081D8 0xD082C4 ICityMap_ctor
dis 0xD09504 0xD09900 ICityMap_codes_4_5
dis 0xD0E0D0 0xD0E900 BlinkMapSymbol
dis 0xD08444 0xD08700 MAP_DIFF_CheckSet
dis 0xD08128 0xD081D8 ItemNumCTRL_ctor
dis 0xD08060 0xD08128 ItemNumCTRL_Changer
dis 0xCEE1D4 0xCEE900 Sub_ItemButton
dis 0xCF0414 0xCF0684 Make_MapButton
dis 0xCE4C94 0xCE4F00 Sub_BackButton
dis 0xCE4294 0xCE4400 CreateMenuPortItem
dis 0xCF71BC 0xCF7280 Make_PortalButton
dis 0xD0F408 0xD0F700 PortalButton_Setup

# --- Maillages de la croix (scene level1, objets MPad / Dirs / DirNormal / DirLight / CurNomal / CurLight / CurBS)
python3 -I "$S/audit_pad_meshes.py" > "$O/pad_meshes.txt" 2>&1 || true
# --- Appels du moteur vers les fenetres (setItemParam / setItemCode)
(cd "$S" && python3 audit_scan_itemparam.py > "$O/scan_itemparam.txt" 2>&1) || true
# --- Valeurs derivees
python3 -I "$S/audit_valeurs.py" > "$O/valeurs.txt"
echo "termine : $O"
