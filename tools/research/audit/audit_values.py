#!/usr/bin/env python3
"""audit_values.py : recalcule les valeurs derivees citees dans /tmp/specs/audit_menus_pave.md a partir des constantes brutes lues dans libil2cpp.so / libdq4core.so
(origine de chaque constante en commentaire : RVA de la methode ou nom du champ). Aucune dependance : python3 audit_values.py

Reperes : interface d'origine = 450 unites de large (eIndent.CalcScreenPosition : x de -225 a 225), portrait de reference 450 x 800 (le portage convertit par H / 800)."""
import math

print('== D-pad (TouchPad) ==')
TBL = (1.225, 1.0, 0.775)                 # c_PadScaleTBL (FieldRVA, hash 60DE99C6...) : index = g_pad_size (0 Grande, 1 Moyenne, 2 Petite)
QUAD = 256.0                              # anneau : quad +-128 sur la zone (256..512, 256..512) de la texture Button (maillage de la scene level1, objet MPad)
BASE = 0.63                               # c_PadBaseScaleXY : echelle locale de MPad (SetPadPos 0xD22E60 : localScale = 0,63 x tbl)
PORT_DIAM, PORT_SCALE = 165.0, (1.25, 1.0, 0.75)
for i, name_str in enumerate(('Grande', 'Moyenne', 'Petite')):
    sc = TBL[i]; d = QUAD * BASE * sc
    print('  %-8s original diameter %.2f (radius %.2f) ; port %.2f ; gap %+.1f %%' % (name_str, d, d / 2, PORT_DIAM * PORT_SCALE[i], (PORT_DIAM * PORT_SCALE[i] / d - 1) * 100))
R = QUAD * BASE / 2                       # rayon de l'anneau pour sc = 1 : 80,64
print('  ring radius (sc = 1) = %.2f' % R)
print('  dead zone s_MoveThreshold = 10 -> %.4f of the radius (port 0.15)' % (10 / R))
print('  max travel of the ball s_moveNakaLimit = 36.5 -> %.4f of the radius (port 0.5)' % (36.5 / R))
print('  start threshold MoveBeginLimit = 16 -> %.4f of the radius ; AnyThreshold = 8 -> %.4f ; MoveRingLimit = 56 -> %.4f of the radius' % (16 / R, 8 / R, 56 / R))
print('  detection collider: radius 95 x sc -> %.4f of the ring radius' % (95 / R))
print('  dots: center at 104 (local, quad +-128) -> %.5f of the diameter (port 85/256 = %.5f)' % (104 / 256, 85 / 256))
print('  sector(angle) = ((int((deg + 180) / 22.5) + 1) >> 1) & 7 ; c_padDirTable = (4, 6, 2, 10, 8, 9, 1, 5) (left, left+down, down, down+right, right, right+up, up, up+left)')

print('\n== D-pad position (SetPadPos 0xD22E60) ==')
for pos in range(4):
    for i, name_str in enumerate(('Grande', 'Moyenne', 'Petite')):
        sc = TBL[i]
        base = {0: -120.0, 1: 0.0, 2: 120.0, 3: 0.0}[pos]
        if pos % 2 == 0: base += (1 if pos >= 2 else -1) * 80.0 * (1 - sc)
        z = 134.5 - 80.0 * (1 - sc)                                   # depuis le bas de l'ecran (ancre 7 = CenterBottom) + NotchFix.TouchPadAdjustmentValue (0 sur PC)
        print('  pos %d (%s) %-8s center x = %+7.2f from the middle, z = %6.2f from the bottom' % (pos, ('gauche', 'centre-gauche', 'droite', 'centre-droite')[pos], name_str, base, z))
print('  engine default: g_pad_pos = 1, g_pad_size = 1 (MaterielMenu_LOAD::makeDiary 0x194a50) -> D-pad at the bottom middle, x = 0')

print('\n== HUD buttons (TouchPad.CreateMenuButton 0xD2377C): plate = (w + 32) x (h + 32), icon = 48 x iconSize ==')
for name_str, key, ico, sz, isz, zdep in (('Map', 0x1000, 3, 1.0, 1.2, None), ('Command', 0x800, 4, 1.0, 1.2, 278.0), ('Talk', 0x400, 15, 0.775, 1.0, 188.0), ('PadPos', 0, 17, 0.55, 1.0, 104.5)):
    w, h = 40 * sz, 32 * sz
    print('  %-8s key %#06x icon %2d : area %5.1f x %5.1f, plate %5.1f x %5.1f, icon %5.1f' % (name_str, key, ico, w, h, w + 32, h + 32, 48 * isz))
print('  (port: square plate H/18 x 1.6 = %.1f px at H = 800)' % (800 / 18 * 1.6))
print('  center x: +-44 (Map, Command), +-39.5 (Talk), +-35 (PadPos) from the edge ; Map: z = -12 from the top ; Command 278, Talk 188, PadPos 104.5 from the bottom')

print('\n== Map window (type 25, MenuPortItemTable.Make_CityMap 0xCF0684 / ICityMap 0xD081D8) ==')
K = 450.0 / 256.0                         # 1,7578125 : unites par pixel du plan de 256 x 192
S = 0.99                                  # localScale du plan et du voile
H2 = 400.0                                # demi-hauteur du portrait de reference
x0, ztop = -225.0 + 2.0, H2 - 2.0         # Build(indent 0, ecran 0, x = 2, y = 12, z = -2 - NotchFix.AdjustmentValue) ; AdjustmentValue = 0 sur PC
print('  plane: top-left corner (%.1f, %.1f), size %.2f x %.3f, x from %.1f to %.1f, z from %.3f to %.1f ; port: x from -225 to 225, z from 62.5 to 400' % (x0, ztop, 450 * S, 337.5 * S, x0, x0 + 450 * S, ztop - 337.5 * S, ztop))
print('  frame (CreateWindow0 430 x 319.5 + border 12): x from -227 to 227, z from 402 to 58.5')
print('  marker (code 1/2): x = %.3f + %.6f x px, z = %.1f - %.6f x py (bottom-left corner of the 24 x 24 icon)' % (x0, S * K, ztop, S * K))
for px, py in ((0, 0), (128, 96), (256, 192)):
    ox, oz = x0 + S * K * px, ztop - S * K * py
    gx, gz = -225 + K * px, 400 - K * py
    print('     px=%3d py=%3d : original (%.2f, %.2f), port (%.2f, %.2f), gap (%+.2f, %+.2f)' % (px, py, ox, oz, gx, gz, gx - ox, gz - oz))
print('  discovered places (code 3, BlinkMapSymbol): 4 x 4 square with top-left corner (-227 + lo x K, 402 - hi x K) -> center (-225 + lo x K, 400 - hi x K): the port is exact ; alpha: triangle 1 -> 0 -> 1 over 4 s (m_blinkRate 0.5), color (1, 0, 0, 1)')
print('  code 4 (special place): icon no. 3 of sheet 5 (MenuTexture y = 288, 16 px cells: red cross), quad 21.6 = 18 x 1.2, depth 13, position (-227 + lo x K, 402 - hi x K), bottom-left corner anchor (assumed: bInBounds = true like the feather): missing from the port')
print('  veil (code 5): quad 450 x 337.5 scale 0.99, depth 12.5, texture 256 x 192 RGBA filled in 10 x 10 blocks from (48, 16) (bit = 1: block copied from dsdq4wmap01m), Point filter')

print('\n== Map button (types 22 / 23, Make_MapButton 0xCF0414) ==')
print('  CreateMenuPortItem (0xCE4294) calls the delegate with type - IndexOf(makeFuncList, delegate): type 22 -> 0 (window 54 x 112: back + mode), type 23 -> 1 (window 54 x 47: back)')
print('  window: bottom-right corner anchor (8), position (2, 0, -2 + NotchFix.AdjustmentValue) ; back: plate 64 x 55.5, center (187.5, -366), icon 11 x 1.3, key 0x400 ; mode: plate 64 x 55.5, center (187.5, -300), icon 2 x 1.2, key 2')
print('  mode button icon (sheet 3): 2 in town (TownImageMap::checkData), 20 large world map (FieldImageMap::open), 19 small world map (FieldImageMap::execute)')

print('\n== Quantity digits (ItemNumCTRL.Changer 0xD08060) ==')
def case12(no):                           # PartsInfo 12 : startNo 6, widthNum 16, ps 32, depart y = 192 (texture Button 512 x 512) ; uv_icon() du portage
    n = no + 6
    return ((n % 16) * 32, 192 + (n // 16) * 32)
for v in (0, 1, 2, 9, 10, 57, 99, 100, 123):
    t, u = (v // 10) % 10, v % 10
    if v < 2: ic = (1, 1)
    else: ic = ((t * 16) if t != 0 else 1, u * 16)
    print('  value %3d -> icon tens %3d %s, units %3d %s' % (v, ic[0], case12(ic[0]), ic[1], case12(ic[1])))
print('  (Changer(v): v < 2 -> two empty cells (icon 1 = (224, 192)) ; otherwise tens = (v / 10) % 10 -> icon 16 x d, or 1 (empty) if 0 ; units = 16 x (v % 10) ; digit d = column x = 192, y = 192 + 32 d)')
print('  Sub_ItemButton (0xCEE1D4): digits of sheet 12, bottom-left corner anchor (indent 6) of the line, tens at (0, 6), units at (10, 6), size 0.6 -> quad of 28.8 units (dps 48 x 0.6)')
