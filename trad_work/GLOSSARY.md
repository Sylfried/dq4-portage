# Glossary French -> English (use these terms everywhere, so all translators agree)

Project: native PC (16:9) port of the Android game Dragon Quest IV. "viewer" = the Python/pyglet program (`dq4_pc`) that draws the game; "engine" = the original native game code (`libdq4core.so`) it runs unmodified under Unicorn.

| French | English |
|---|---|
| moteur | engine (the original native game code) |
| visionneuse | viewer |
| jeu d'origine, jeu, jeu mobile | original game / the game (the Android/mobile game) |
| mobile (le mobile) | mobile (the mobile game) |
| portage, port | port |
| outil (l'outil) | the tool |
| fenetre (du jeu) | window ; fenetre de menu/message = menu / message window ; "fenetre du jeu" = game window |
| ecran | screen ; plein ecran = full screen ; ecran-titre = title screen |
| menu Echap | Esc menu ; menu Pause = Pause menu |
| bouton | button ; plaque = plate (the button/panel background) ; cadre = frame (box outline) ; bordure/bord = border/edge |
| boite (de message) | box (message box) ; ballon = balloon |
| texte, message, dialogue | text, message, dialogue |
| ligne | line ; saut de ligne = line break |
| police | font ; glyphe = glyph |
| carte | map ; carte du monde = world map ; terrain = field (the walkable area of a town/dungeon/world) ; ville = town ; donjon = dungeon ; tour = tower |
| combat | battle ; monstre = monster ; formation = formation ; decor (de combat) = backdrop/scenery |
| heros, personnage, PNJ | hero, character, NPC |
| joueur | player |
| sauvegarde | save ; etat instantane = savestate ; fichier de sauvegarde = save file |
| chargement | loading ; charger = load |
| pas (du moteur) | step (one engine step = one fixed 30 Hz update) |
| image (affichee) | frame (when about time or display) ; image (picture) when about a picture/texture |
| paquet | packet (engine event packet) |
| crochet | hook |
| creneau | slot |
| camera ; cap | camera ; heading |
| cible (camera) | target |
| rotation, cran | rotation, notch |
| fondu | fade ; fondu au noir = fade to black |
| effet | effect ; bruitage = sound effect (SE) ; musique = music (BGM) ; jingle = jingle |
| sprite, feuille de sprites, rangee (de sprite) | sprite, sprite sheet, sprite row |
| texture, maillage, sommets, modele | texture, mesh, vertices, model |
| rendu | rendering ; dessin, dessiner = drawing, draw |
| hors ecran | off-screen |
| anticrenelage | antialiasing |
| souris, clic, molette, pointeur, curseur | mouse, click, wheel, pointer, cursor |
| clavier, touche, appui | keyboard, key, press |
| manette | gamepad ; croix directionnelle = D-pad |
| reglage(s) | setting(s) |
| defaut (par defaut) | default |
| liste, page, onglet | list, page, tab |
| valeur, nombre, numero | value, number, number |
| dossier, fichier, chemin | folder, file, path |
| cache (nom) | cache ; cache (participle of cacher) = hidden |
| journal | log |
| audit, relecteur | audit, reviewer |
| issue (GitHub) | issue ; "Avance #N" (PR title prefix) = PR #N |
| a valider sur Windows | to be validated on Windows |
| non verifie / suppose / etabli | not verified / assumed / established |
| vitesse | speed ; acceleration = acceleration |
| rien | nothing / no change (by context) |
| tampon | buffer |
| Echap | Esc |

Conventions
- American spelling (color, center, behavior).
- Keep the names of characters and places as written in the French patch (Alina, Kiryl, Borya, Ragnar, Torneko...), and keep texts shown in the game (spell names, labels, quoted strings) in French exactly as written, e.g. "Premiers secours", "Coût en PM".
- French decimal comma becomes a decimal point (2,8125 -> 2.8125). Thousands: 1 620 -> 1,620.
- Typographic quotes « » around program/game strings become straight double quotes; the French text inside stays.
- Keep ALL identifiers, file names, paths, numbers, hex values, `backticked` code, issue numbers (#123) and decision numbers (D-123) exactly. If a comment mentions an old French identifier that was renamed (see docs/rename_identifiers.tsv in the repository: columns old<TAB>new), write the new name.

Pilot feedback (added after the first batch)
- The rename table contains the row `SANS -> NO_DEFAULT` (an artifact of the token-based rename). When the French word "sans" appears in ordinary prose or in a comment ("sans fenetre", "sans logos"), translate it as "without" / "no", NOT as NO_DEFAULT. Only keep `NO_DEFAULT` when the text is clearly about that constant.
- `window_errors.log` (and other file names) stay exactly as written.
- "journaux" / "journal de sauvegarde" (adventure logs in the game) = adventure logs / save slots; "journal" (program output) = log.
- "mailles" = mesh cells; "maillage" = mesh.
- "bavardage" (party chat) = party chat.
- Names of menu pages / labels shown in the game stay in French inside straight quotes ("Premiers secours", "Coût en PM", "Changer la vitesse en combat").
- Quotes of the player's own words in code comments are translated into English; the French original is not kept.
- Dates are ISO (2026-11-05). Days/months written in words become English.
- "mode memorise" = remembered mode (the mode saved in the settings); "memorise" in general = remembered / saved.
- Keep the length and line structure of each comment (same number of lines when possible) so the code stays readable.
- PV / PM in prose = HP / MP ("MF max" = max MP). Game labels shown on screen stay French in quotes.
- "groupe" = party (hero group) / group (monster group). "case" = cell. "morceau" = chunk. "rangee" = row. "emplacement" = slot. "garde-fou" = safeguard. "voile" = veil. "file" (queue) = queue. "releve" = reading.
- "liste des journaux" = adventure log list (save slots).
- Dict keys and string values that are still French in the current code (e.g. 'ennemis', 'nom', 'vaincus') stay in French inside backticks/quotes.
- Backticked pseudo-code stays as is, but prose around it is translated.
- UI terms: "ligne" of a menu = line; "pastille" (of the D-pad) = pill; "infobulle" = tooltip; "intertitre" = group subheading; "liste deroulante" = drop-down list; "curseur" = cursor (golden selection cursor), slider (numeric setting), thumb (scrollbar); "aimantation" = snapping; "accelerateur" = accelerator; "consigne" = hint.
- `texte()` in the rename table may not be the real method name: when a comment names a method, prefer the name that exists in the code (e.g. `text_entered` in name_entry.py).
- More terms: "case" = checkbox (tick box) / slot (key slot) / entry (menu entry) / cell (grid cell); "modele" = template (sentence template) / model (3D model); "croix" = D-pad; "fiche d'un sort" = spell info panel; key names "Carte" = Map, "Annuler" = Cancel, "Oui / Non" = Yes / No (when describing a key); tab names "Dialogues", "Combats" stay in French inside quotes.
- If a comment names a function/attribute that no longer exists in the code, leave the name as is (do not invent one).
- More terms: "marche acceleree" = accelerated walking; "combat accelere" = accelerated battle; "remanence" = afterimage; "etirure" = stretch; "glissement" (sky) = slide; "raccord" = join; "couture" = seam; "curseurs" (setting rows) = sliders; "coupure" (sound) = cutoff; "reprise" = resume (music) / migration (folders, `migrate`); "rangement" = tidy-up; "banque" (data*.dat) = bank; "maille" = mesh cell.
- Section titles of `texts_en/pause.py` such as "---- Affichage" are labels of the file: translate the part after the dashes only if it is a comment, keep game labels in French.
- `SetBlur(actual)` is a corrupted `SetBlur(vrai)` (rename artifact): write `SetBlur(true)`.
- "paquet de donnees" (datapack.unity3d) = data pack; "decoupe" (alpha-tested texture) = cut-out; "decor" = scenery; "fondu enchaine" = cross-fade; "Compteur" in prose = Counter (the rename table row `Compteur -> ExampleCounter` is a rename artifact, ignore it).
