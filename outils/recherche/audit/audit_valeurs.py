#!/usr/bin/env python3
"""audit_valeurs.py : recalcule les valeurs derivees citees dans /tmp/specs/audit_menus_pave.md a partir des constantes brutes lues dans libil2cpp.so / libdq4core.so
(origine de chaque constante en commentaire : RVA de la methode ou nom du champ). Aucune dependance : python3 audit_valeurs.py

Reperes : interface d'origine = 450 unites de large (eIndent.CalcScreenPosition : x de -225 a 225), portrait de reference 450 x 800 (le portage convertit par H / 800)."""
import math

print('== Croix (TouchPad) ==')
TBL = (1.225, 1.0, 0.775)                 # c_PadScaleTBL (FieldRVA, hash 60DE99C6...) : index = g_pad_size (0 Grande, 1 Moyenne, 2 Petite)
QUAD = 256.0                              # anneau : quad +-128 sur la zone (256..512, 256..512) de la texture Button (maillage de la scene level1, objet MPad)
BASE = 0.63                               # c_PadBaseScaleXY : echelle locale de MPad (SetPadPos 0xD22E60 : localScale = 0,63 x tbl)
PORT_DIAM, PORT_ECH = 165.0, (1.25, 1.0, 0.75)
for i, nom in enumerate(('Grande', 'Moyenne', 'Petite')):
    sc = TBL[i]; d = QUAD * BASE * sc
    print('  %-8s diametre d\'origine %.2f (rayon %.2f) ; portage %.2f ; ecart %+.1f %%' % (nom, d, d / 2, PORT_DIAM * PORT_ECH[i], (PORT_DIAM * PORT_ECH[i] / d - 1) * 100))
R = QUAD * BASE / 2                       # rayon de l'anneau pour sc = 1 : 80,64
print('  rayon anneau (sc = 1) = %.2f' % R)
print('  zone morte s_MoveThreshold = 10 -> %.4f du rayon (portage 0,15)' % (10 / R))
print('  course max de la boule s_moveNakaLimit = 36,5 -> %.4f du rayon (portage 0,5)' % (36.5 / R))
print('  seuil de depart MoveBeginLimit = 16 -> %.4f du rayon ; AnyThreshold = 8 -> %.4f ; MoveRingLimit = 56 -> %.4f du rayon' % (16 / R, 8 / R, 56 / R))
print('  collider de detection : rayon 95 x sc -> %.4f du rayon de l\'anneau' % (95 / R))
print('  pastilles : centre a 104 (local, quad +-128) -> %.5f du diametre (portage 85/256 = %.5f)' % (104 / 256, 85 / 256))
print('  sector(angle) = ((int((deg + 180) / 22.5) + 1) >> 1) & 7 ; c_padDirTable = (4, 6, 2, 10, 8, 9, 1, 5) (gauche, gauche+bas, bas, bas+droite, droite, droite+haut, haut, haut+gauche)')

print('\n== Position de la croix (SetPadPos 0xD22E60) ==')
for pos in range(4):
    for i, nom in enumerate(('Grande', 'Moyenne', 'Petite')):
        sc = TBL[i]
        base = {0: -120.0, 1: 0.0, 2: 120.0, 3: 0.0}[pos]
        if pos % 2 == 0: base += (1 if pos >= 2 else -1) * 80.0 * (1 - sc)
        z = 134.5 - 80.0 * (1 - sc)                                   # depuis le bas de l'ecran (ancre 7 = CenterBottom) + NotchFix.TouchPadAdjustmentValue (0 sur PC)
        print('  pos %d (%s) %-8s centre x = %+7.2f depuis le milieu, z = %6.2f depuis le bas' % (pos, ('gauche', 'centre-gauche', 'droite', 'centre-droite')[pos], nom, base, z))
print('  defaut du moteur : g_pad_pos = 1, g_pad_size = 1 (MaterielMenu_LOAD::makeDiary 0x194a50) -> croix au milieu en bas, x = 0')

print('\n== Boutons du HUD (TouchPad.CreateMenuButton 0xD2377C) : plaque = (w + 32) x (h + 32), icone = 48 x iconSize ==')
for nom, key, ico, sz, isz, zdep in (('Map', 0x1000, 3, 1.0, 1.2, None), ('Command', 0x800, 4, 1.0, 1.2, 278.0), ('Talk', 0x400, 15, 0.775, 1.0, 188.0), ('PadPos', 0, 17, 0.55, 1.0, 104.5)):
    w, h = 40 * sz, 32 * sz
    print('  %-8s touche %#06x icone %2d : zone %5.1f x %5.1f, plaque %5.1f x %5.1f, icone %5.1f' % (nom, key, ico, w, h, w + 32, h + 32, 48 * isz))
print('  (portage : plaque carree H/18 x 1,6 = %.1f px a H = 800)' % (800 / 18 * 1.6))
print('  x du centre : +-44 (Map, Command), +-39,5 (Talk), +-35 (PadPos) depuis le bord ; Map : z = -12 depuis le haut ; Command 278, Talk 188, PadPos 104,5 depuis le bas')

print('\n== Fenetre de carte (type 25, MenuPortItemTable.Make_CityMap 0xCF0684 / ICityMap 0xD081D8) ==')
K = 450.0 / 256.0                         # 1,7578125 : unites par pixel du plan de 256 x 192
S = 0.99                                  # localScale du plan et du voile
H2 = 400.0                                # demi-hauteur du portrait de reference
x0, ztop = -225.0 + 2.0, H2 - 2.0         # Build(indent 0, ecran 0, x = 2, y = 12, z = -2 - NotchFix.AdjustmentValue) ; AdjustmentValue = 0 sur PC
print('  plan : coin haut-gauche (%.1f, %.1f), taille %.2f x %.3f, x de %.1f a %.1f, z de %.3f a %.1f ; portage : x de -225 a 225, z de 62,5 a 400' % (x0, ztop, 450 * S, 337.5 * S, x0, x0 + 450 * S, ztop - 337.5 * S, ztop))
print('  cadre (CreateWindow0 430 x 319,5 + bordure 12) : x de -227 a 227, z de 402 a 58,5')
print('  marqueur (code 1/2) : x = %.3f + %.6f x px, z = %.1f - %.6f x py (coin bas-gauche de l\'icone 24 x 24)' % (x0, S * K, ztop, S * K))
for px, py in ((0, 0), (128, 96), (256, 192)):
    ox, oz = x0 + S * K * px, ztop - S * K * py
    gx, gz = -225 + K * px, 400 - K * py
    print('     px=%3d py=%3d : origine (%.2f, %.2f), portage (%.2f, %.2f), ecart (%+.2f, %+.2f)' % (px, py, ox, oz, gx, gz, gx - ox, gz - oz))
print('  lieux decouverts (code 3, BlinkMapSymbol) : carre 4 x 4 de coin haut-gauche (-227 + lo x K, 402 - hi x K) -> centre (-225 + lo x K, 400 - hi x K) : le portage est exact ; alpha : triangle 1 -> 0 -> 1 en 4 s (m_blinkRate 0,5), couleur (1, 0, 0, 1)')
print('  code 4 (lieu special) : icone n. 3 de la feuille 5 (MenuTexture y = 288, cases de 16 px : croix rouge), quad 21,6 = 18 x 1,2, profondeur 13, position (-227 + lo x K, 402 - hi x K), ancrage coin bas-gauche (suppose : bInBounds = true comme la plume) : absent du portage')
print('  voile (code 5) : quad 450 x 337,5 echelle 0,99, profondeur 12,5, texture 256 x 192 RGBA remplie par blocs de 10 x 10 depuis (48, 16) (bit = 1 : bloc copie de dsdq4wmap01m), filtre Point')

print('\n== Bouton de la carte (types 22 / 23, Make_MapButton 0xCF0414) ==')
print('  CreateMenuPortItem (0xCE4294) appelle le delegue avec type - IndexOf(makeFuncList, delegue) : type 22 -> 0 (fenetre 54 x 112 : retour + mode), type 23 -> 1 (fenetre 54 x 47 : retour)')
print('  fenetre : ancre coin bas-droit (8), position (2, 0, -2 + NotchFix.AdjustmentValue) ; retour : plaque 64 x 55,5, centre (187,5, -366), icone 11 x 1,3, touche 0x400 ; mode : plaque 64 x 55,5, centre (187,5, -300), icone 2 x 1,2, touche 2')
print('  icone du bouton mode (feuille 3) : 2 en ville (TownImageMap::checkData), 20 carte du monde grande (FieldImageMap::open), 19 carte du monde petite (FieldImageMap::execute)')

print('\n== Chiffres de quantite (ItemNumCTRL.Changer 0xD08060) ==')
def case12(no):                           # PartsInfo 12 : startNo 6, widthNum 16, ps 32, depart y = 192 (texture Button 512 x 512) ; uv_icone() du portage
    n = no + 6
    return ((n % 16) * 32, 192 + (n // 16) * 32)
for v in (0, 1, 2, 9, 10, 57, 99, 100, 123):
    t, u = (v // 10) % 10, v % 10
    if v < 2: ic = (1, 1)
    else: ic = ((t * 16) if t != 0 else 1, u * 16)
    print('  valeur %3d -> icone dizaines %3d %s, unites %3d %s' % (v, ic[0], case12(ic[0]), ic[1], case12(ic[1])))
print('  (Changer(v) : v < 2 -> deux cases vides (icone 1 = (224, 192)) ; sinon dizaines = (v / 10) % 10 -> icone 16 x d, ou 1 (vide) si 0 ; unites = 16 x (v % 10) ; chiffre d = colonne x = 192, y = 192 + 32 d)')
print('  Sub_ItemButton (0xCEE1D4) : chiffres de la feuille 12, ancre coin bas-gauche (indent 6) de la ligne, dizaines en (0, 6), unites en (10, 6), taille 0,6 -> quad de 28,8 unites (dps 48 x 0,6)')
