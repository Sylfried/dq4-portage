# Journal agent45-texte (TX) - mesures a 14 h 40 (reprise apres coupure)
Worktree /home/claude/wt45-texte (branche agent45-texte, aucun commit encore). Scripts de mesure : /tmp/claude-0/-home-claude/17145693-c62f-5af6-a741-2d4f94a36edf/scratchpad/tx/

## Etabli (code lu / mesure sur ecran4 mobile 810x483)
- Le jeu utilise des TextMesh Unity (pas UI Text) : ancre 0-8, alignement, characterSize, lineSpacing exportes dans ui_layout.json (type 33 = Make_BattleTarget : onglets ancre 4 ls 0.801 cs 9.945 z -146 ; textes des boutons de cible ancre 3 (MiddleLeft) ls 0.441 cs 9.945, nœud z -198 = centre du bouton (-218) + biais dy 20).
- Police SE-GARRIR : 20 px, interligne 23.525, ascent 18.887 ; 1 px police = characterSize*0.1 unite (ui_menu.py:981-990, _texte).
- Echelle du mobile : 1.688 px/unite (cadre : 754.5 px entre les traits blancs = 447 unites ; hauteur 260 px = 154 unites ; boutons 174 unites = ~289 px visibles).
- Mobile, bouton de cible 1 (y 118 a 200, centre 159.2) : « Rat volant » ligne de base y=182 = 13.5 unites SOUS le centre. Formule actuelle de la visionneuse (bloc centre sur zp, pas = 23.525*u*ls, base = haut - ascent) : 13.4 unites -> OK pour UNE ligne.
- Mobile, « Scarapince / ×2 » : lignes de base y=165 et y=200, pas = 35 px = 20.7 unites = 2.0 x le pas nominal (10.3 unites avec ls 0.441). Formule actuelle : 173 et 191 -> FAUX de 8 px (1re ligne) et 9 px (2e).
- Ajustement : pas reel P = 20.7, ascent effectif A = 24.1 (au lieu de 18.9) ; A - P/2 = 13.75 (1 ligne) et A - P = 3.4 (2 lignes) recoupent les deux mesures.
## A verifier
- Le double pas vient-il d'une chaine « \r\n » (Unity compterait 2 sauts de ligne) ou d'un lineSpacing change par le jeu a la pose du texte ? (journal paquets /tmp/pk_tx.txt, DQ_PKTALL)
- Memes ecarts pour les onglets (ancre 4) et les plaques de monstres (type 31, ancre 3, ls 0.481), fenetres d'etat (type 29).

## MAJ 15 h (apres lecture du journal de paquets et mesure PC vs mobile) - ETABLI
- Le moteur envoie « Nom\n\n\t×2 » (2 sauts de ligne + tabulation) : 3 lignes, pas 2. Avec ce bloc de 3 lignes (pas = 23.525*u*ls) la formule de la visionneuse donne 1re base -3.3 / 3e base -23.9 unites sous le centre du bouton ; mobile : -3.4 / -24.2. Une ligne : formule -13.4, mobile -13.5. => la formule de placement (bloc centre sur zp = z - dy, base = haut - ascent) REPRODUIT le mobile.
- Capture PC ecran3 et mobile ecran4 ont la MEME echelle (1.688 px/unite : traits du cadre a 754.5 px). Texte « Ragnar » de l'onglet : profil de lignes identique pixel a pixel (27 25 30 24 20 18...), base a 8 px au-dessus du trait du corps de fenetre des 2 cotes, bord gauche a 30.5 px du trait du cadre des 2 cotes. => aucun ecart de placement visionneuse / jeu d'origine sur ce texte.
- Plaque PC « Scarapince ×2 » : bases a 46 et 82 px sous le bord interieur haut ; bouton mobile (meme chaine) : 47 et 82. Meme structure.
- Cause du « texte trop bas » (present AUSSI sur mobile) : Unity pose la base a `ascent` (18.887 px police) sous le haut de la ligne quel que soit lineSpacing ; les lineSpacing du jeu (0.441 cibles, 0.481 plaques, 0.801 onglets/boutons, 0.873...) raccourcissent la boite de ligne (reglages calcules pour la police japonaise) => l'encre descend de (1 - ls) * 23.525 * u / 2 sous le centre de sa boite : 6.5 unites (11 px a 1.688) pour « Rat volant » / plaques, 2.3 pour onglets et boutons.
- Correction proposee (ecart volontaire par rapport au jeu d'origine, a la demande de Sylfried) : remonter le texte de (1 - ls) * interligne * u / 2 pour ls < 1 (un seul endroit : Rendu._texte). DQ_TEXTE_ORIGINAL=1 rend le placement exact du jeu.

## MAJ 15 h 40 - rendus hors ecran (pyglet headless, sans xvfb) a l'echelle des captures (1.688 px/unite)
- Scripts : scratchpad/tx/rend_multi.py (HL=1) ; mesures : analysis.py ; sorties : scratchpad/tx/out1/*.png (t33 cible, t32 commandes, t29 etat, t31 plaques, g<type> = 31 types generiques), feuilles feuille_combat.png / feuille_29_31.png / feuille_gA.png / feuille_gB.png.
- Type 33 rendu par la visionneuse (mode original) vs capture mobile : onglet, « Rat volant », « Scarapince / x2 » a +-1 px (decalage global de 1 px du rendu, calage CX/CY) => la visionneuse = le jeu.
- Mode recentre : « Rat volant » ligne de base a 13.0 px sous le centre du bouton, encre 147-171 (centre 159, bouton 117-199, centre 158) ; « Scarapince / x2 » encre 130-188 (marges 13 / 11 px) ; onglet remonte de 4 px ; en-tete « Doc » de la plaque d'etat : centre de l'encre a 5 px sous le centre de la bande (original) -> 1 px (recentre) ; PV / PM / Nv. inchanges (ls > 1).
- Commits (branche agent45-texte) : ab76eb9 (isolement du placement + test mobile), f756c63 (recentrage). Tests : tools/test_texte_recentrage.py (8) ; test_plaque_depart (12), test_panneau_interface (10), test_reglages_interface (15) OK.
- En attente (verrou xvfb occupe) : captures reelles en combat avant / apres (/tmp/c_txav_126.png avec DQ_TEXTE_ORIGINAL=1, /tmp/c_txap_126.png).
- Captures reelles combat avant / apres OK : /tmp/tx45/c_avant_126.png, c_apres_126.png, combat_reel_avant_apres.png (nom Ragnar -2 px, plaque -5 px, onglet -2/-4 px, Attaquer -2 px a 1280x720).
