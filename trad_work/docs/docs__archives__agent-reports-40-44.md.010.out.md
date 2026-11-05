## Agent a013cab3ae1bf6983 — 2026-11-02 03:13

REPORT "libelles" (PR #43), branch agent-libelles, worktree /home/claude/wt-libelles

DELIVERED (1 commit 4ec25d6, clean tree, pyflakes without alerts, 13 tests OK in 0.1 s, import 0.0x s without numpy/unicorn/pyglet)
- dq4_pc/libelles.py: libelle_source(modele), libelle_lieu(carte) + confiance_source() / confiance_lieu() ("certain/suppose"; "officiel/derive/generique").
- tools/generer_libelles.py: regenerates the "lieux" block of libelles.py and the frequency tables of test_libelles.py (`--apk <dossier APK> --cache <cache cartes> [--ecrire]`; without --ecrire = simulation). ~13 s.
- tools/test_libelles.py: without xvfb, without engine, without APK (embedded data); prints the coverage with -v.
Nothing else touched (neither wt-histo, nor dq4-portage, nor docs/). APK, resources, FR patch and saves read-only.

WHAT THE ENGINE PROVIDES (verified by loading 4 saves under Unicorn, `Engine(APK, saves, tmp)`)
- Character: `State.sprites[slot]['id']` = integer = sprite sheet h<id> (world map: +4096, already handled). libelle_source accepts the integer, 'h019', '19', or directly the dict State.sprites[i]. Example read at Bastione (caf1): 36 -> "Un roi", 17/15 -> "Un soldat", 18 -> "Un chevalier", 5 -> "Un vieil homme".
- Scenery: FMAP model name, data.game_map(name)['noms'][object] ("012_tubo01"); libelle_source accepts it with or without group number and "(Clone)".
- Place: State.game_map ("caf1", "mak1f1"). VERIFIED PITFALL: on the world map (State.part == 0xe) State.game_map keeps the name of the LAST TOWN ("maout" with part 14). libelle_lieu(etat) accepts the State object and returns "Monde" if part == 0xe; otherwise pass 'monde'.
- Slot 0 = playable party leader (id 106 on two saves of chapter 1, 100 in ev01): label "Un aventurier"; its name must come from the message, not from here.

COVERAGE (test figures)
- Characters: 3590 placements in the scripts, 174 models. Named: 158 models = 3509 placements (97.7%), of which certain 950 (26.5%), assumed 2559. Deliberately unnamed: 16 3D models (158, 161, 162, 164, 166, 167, 169, 170, 192, 196, 197, 210-213, 215) = 81 placements (215 alone accounts for 37).
- Scenery: 1939 model names, 16955 occurrences (seen ≥ 2 times); 36 labels cover 4868 occurrences (the rest = flowers, grass, lights, walls, pillars, scenery without a message). All the requested objects to examine are covered: jar, barrel, chest, shelf, chest of drawers, drawer, crate, well, bed, sign, stove, fireplace, bag, book, grave, statue, throne, armor, door, chair, table, etc.
- Places: 670 maps of the game (.fld): official name from the FR patch 248, derived 31 ("Château de X", "Château de Bastione"), generic 192, no place 199 (including 140 battle maps bt, 9 ev, 1 fk, 23 za, 25 s?).

PLACE RULE (a single one, documented): the engine names a place from the first 2 letters of the map (SaveLoad::getPlaceNameNo + TextAPI::extractText, entry NN-1 of b1007000); the whole interior of a place (houses, inn, church, well, floors) returns the place name ("Strattbourg", never "Maison, Strattbourg"). Prefix c?: "Château de X" except names that are already "Palais…". Without an official name: c -> "Château", d -> "Grotte", t -> "Tour", m -> "Ville", s? with houses/inn (sb, se, sj) -> "Village"; bt, ev, fk, za, other s? -> None.

ESTABLISHED
- Format of the script placements, conversion table of the engine (types 2/3/4), official name per prefix (read in the engine, all prefixes consistent), FR text of each name, sprite ids on 4 saves, "State.game_map stale on the world map".
- Sheets viewed with Read: the 155 h sheets used; 183 = balloon and 193 = boats confirmed on the world map (ids 4279 / 4289).
ASSUMED
- The whole visual classification marked 'S' (occupation, age, sex from the image alone); the object names deduced from romaji (tubo, taru, hondana, tansu, kb...): 3D models not rendered on screen; "Château de X" for cb cd cf cg ci ck; "Château de Bastione" for ca (the engine has no name for 'ca'; supported by save 2 and by the script of caf1 which refers to haout = Bastione).
NOT VERIFIED
- Types 3 (165, 199-204, 221-230, 298, 300 -> "Un monstre") and 4 (299 -> "Un meuble"): deduced from the engine's table, not seen in game; how histo will obtain the identity of a monster/3D model (they do not appear in State.sprites) is not resolved. No test with a window.

QUESTIONABLE CASES TO HAVE REVIEWED
- Sprite 9 (195 placements, 43 in inns): "Un homme"; maybe the innkeeper. 11, 65, 220 "Un homme costaud".
- 15/16/17 "Un soldat", 18 and 152 "Un chevalier" (blurry boundary). 19, 144 "Un guerrier".
- 34 "Un noble", 37 "Un jeune noble", 35 and 38 "Une dame" (38 stands next to the king 36: probably the queen), 79 and 82 "Un roi".
- 148, 149 "Un ange" (ck = Zénithia); 68, 75, 153, 155 "Un magicien"; 21 "Un prêtre" (read in the churches); 66 "Un marin" (map mndoc).
- 131 and 52 "Un chien" (maybe a wolf); 45, 46, 47 "Un chat"; 138, 141 "Un félin".
- 69, 70, 71, 72 (village mq, teal bonnets): "Un homme / Une femme / Un garçon" without race.
- 216, 217 (heroine with green hair, ev08) "Une jeune femme".
- Places: dp = 29 maps of an 8-level dungeon that the engine names "Chapelle du Coteau" (kept, engine rule); cc, ch, cl, cm remain "Château" (name not known to the engine); all d* "Grotte" (may be a tunnel, a mine); mg, ml, mp "Ville"; za (3 towers of 9 floors) and most s?: None, out of caution.
- The 16 3D models of type 2 remain unnamed (215 is placed 37 times in 27 maps): check on screen if a label is wanted.

NOTES FOR THE DOC (to merge, nothing written in docs/)
- Sprite sheets h<id>: 3 columns x 4 rows of 24x32 (row 0 back, 1 profile, 2 front, 3 profile); 128x256 = 8 rows for the 10 playable characters (100, 103...127 in steps of 3); h193 = boats 512x512.
- Character placements: `scriptobject`; six int32 (a0, model, direction, x, y, z) at o + (W(o+0x14)&~3) + (W(o+0x20)&~3); conversion table at 0xfda20 (36 triplets key, target, type: 2 = 3D model 310-325, 3 = monster 0-18, 4 = furniture).
- getPlaceNameNo: first 2 letters of the map name; 0x0c0000NN; text = entry NN-1 of b1007000 (n = 52 still gives "ソロタウン", untranslated, no prefix uses it).
- State.game_map remains the last town when State.part == 0xe.

MERGE PITFALLS
- 3 new files, no conflict expected. The blocks between "# === DEBUT GENERE" and "# === FIN GENERE" are written by the generator: do not edit them by hand.
- The generator fills the map cache given by --cache (I used /tmp/uicache4: about a hundred carte8_*.pkl added, harmless). The game has 670 maps (.fld), not 523: 523 was the content of the cache at that time.
- On the histo side: ev* (events) and bt* return None -> keep the last known place; do not pass State.game_map alone on the world map; prefer the name read in the message to "Un aventurier" for the playable characters.
- Nothing to remember about the user.

---

## Agent a85fdfd2cea49649d — 2026-11-02 03:15

REPORT "coffres" agent (Screen 3), worktree /home/claude/wt-coffres, branch agent-coffres, base 08f5785. Clean tree, 2 commits.

## Verdict
Root cause found, fixed globally and verified by before/after screenshots on all the orientations encountered. A rotation defect of the map objects, not a problem of « tourner le coffre vers le joueur » (EN: "turning the chest toward the player"). The chest keeps its own heading (the map's) and its lid pivots around ITS rear hinge.

## Findings
1. **Root cause: wrong order of rotations in `data.euler_mat`.**
   - Disassembly of `FldObject.rotateXZY` (0xCD47F0): q = (AngleAxis(ry, up) * AngleAxis(-rz, forward)) * AngleAxis(-rx, right).
   - Axes read: static `Vector3` at offsets 0x18, 0x48 and 0x3C (confirmed in the dump).
   - Quaternion product reread instruction by instruction: q2*q3 then (q2*q3)*q1, so X first (object frame), then Z, then the heading Y last. Matrix = Ry·Rz·Rx.
   - The previous code (#21) did Rx·Ry·Rz, so the lid tilt (key FPMV rx = -60) happened around the world's X axis, not the chest's. The #21 note "order X, Y, Z" was wrong.
   - Consequence: only a chest with heading 0 opened properly. Heading ±90: lid sideways. Heading 180: lid toward the front, inside the chest. Heading -27: lid crooked, outer face toward the player.
2. **Second defect, same family: `c_pmv_func` ignored.**
   - The common movements (flag & 4) read their displacement in the object's frame: position = MultiplyPoint(TRS(pos, rotateXZY(rot), scl)) of the object (0xCD96D8). `update_pmv_one` (0xCD6824) chooses CPMV (4) when flag & 4, otherwise PMV (1).
   - The viewer added the displacement as is (world). The drawers (`hikidashi1b`, key posZ) with heading ≠ 0 came out sideways.
3. **Representation of the chests (read in the data).**
   - A chest = 2 map objects: `tbox01` (body, no animation) and `tbox02` (lid, origin = high rear hinge, FCAN table).
   - Animation 1 = closed, 2 = opening (X rotation from 0 to -60 in 10 units, 5 game frames), 3 = held open, 4 = closing.
   - No separate 3D model, no 4 or 8 orientations: a single Y heading per object.
   - Of the 194 chests, 184 have heading 0. The other 10: `ham1f1` (90), `hcy1b1` (90 x3), `mdi1f1` (-27), `sjout` (rz = -7), `ss5b1b` (-90 x2), `tcf1` (180), `tcf3` (180).
   - Billboard flag = 0: the chests never turn toward the camera. Only barrels and jars (flag 4) do.
4. **No Unity chest logic in the dump.**
   - No TreasureBox or TownChara class for this; everything goes through `FldObject`.
   - Engine: `TownFurnitureObject::openObject` only sends `SetCommonAnimation(object, 2)` (closing = 4) via packet 5. No rotation toward the player.
   - Packet 4 (`cmd_fld_rot`) is only emitted by `FldStage::setRotObjectUid`, with no direct caller in the .so (hence possibly by an event script), and by `CasinoPoker::initialize`.
5. **Common animations of the whole game** (scan of the 523 maps):
   - Chests: X rotation only.
   - Drawers: posZ only.
   - Doors (door01-06, wdoor01-06) and wardrobe leaves (tansu*): Y rotation only, hence unchanged.
   - Jars and barrels: billboards, out of scope.
   - Only chests and drawers were affected (10 chests, about 9 drawers with heading ≠ 0: chf2, dpb4b/5b, mkm1f1, mmout, sey1f1, shb1, za2f8, za3f2).
6. **Intended side effect: the initial pose of tilted objects (rx or rz ≠ 0 with ry ≠ 0) also changes.**
   - About 280 objects, 71 types: cliffs `dlkm1a`, tufts `kb0x`, `tate01b`, `ken01b`, `tenkuzyo2e` (the title island), etc.
   - Hint that the new order is the one the designers intended: the pairs `dlkm1a` (40, 6, 0) / (-40, 186, 0) lean in the same world direction with Ry·Rx, and in opposite directions with the old order.

## Fixes (files and functions)
- `dq4_pc/data.py`:
  - `euler_mat` returns `Ry @ Rz @ Rx` (docstring rewritten).
  - Cache `carte8_` becomes `carte9_` in 3 places: `Data.game_map`, `_elements`, and `_purge_old` (purges `carte[0-8]_`). The vertices of tilted objects are baked with `euler_mat`: the cache must be rebuilt.
- `dq4_pc/map_objects.py`: in `MapObjects._place`, a movement with `flag & 4` adds its displacement in the object's frame (`pos += _rot(rot) @ (scl * dp)`); the other movements (flag 0 or 1) unchanged.
- `dq4_pc/window.py`: only the predecessor's line is kept, `DQ_CARTE_SANS_SPR=1`.
  - It is a test hook in the `DQ_CARTE_TEST` block of the frame method (~line 2801). It empties `e.sprites` so that the hero does not hide the object.
  - No function of the off-limits scope touched (`_town_panel`, `_edge_correction`, `_shift_depth`, title, window modes, mouse).
- `tools/test_map_items.py` (new, predecessor's work completed): 15 tests, about 5 s, without xvfb. Looks for the maps in `DQ_CACHE_CARTES` (default `/tmp/uicache_coffres`) and skips the "real objects" tests if the cache is missing.
  - 11 pure-logic tests: `euler_mat` against an independent quaternion reference, X tilt in the object's frame, lid at all headings, drawer and scale, engine order pos/rot then anim, unchanged door.
  - 4 tests on the REAL objects: the 194 chests (rigid rotation around the hinge, no roll along the chest's X axis, free edge that rises and moves back, reclosing identical to the start), drawers (displacement = R(heading) · key), doors.
  - Verified that the chests test fails with the old `euler_mat`.
- Commits (brief footer present): ac4cb9b (fix + cache carte9) and f58ce7b (tests of the real objects).
- pyflakes: only the warning `struct` unused in `data.py`, already known.

## Before/after screenshots (absolute paths, before = top or 1st row, after = below)
Columns: frames 9, 12, 14, 16, 22, 40.
- `/tmp/coffres_captures/mdi1f1_avant_haut_apres_bas.png`: chest with heading -27, default camera. **This is very probably the scene of the user's screenshot.**
- `/tmp/coffres_captures/ss5b1b_cap-90_avant_haut_apres_bas.png`: heading -90.
- `/tmp/coffres_captures/hcy1b1_cap90_et_tcf1_cap180_avant_apres.png`
- `/tmp/coffres_captures/mdi1f1_cap-27_et_ham1f1_cap90_avant_apres.png`
- `/tmp/coffres_captures/tiroirs_sey1f1_cap90_chf2_cap-90_avant_apres.png`: drawers, which used to come out sideways and now come out toward the front of the furniture.
- `/tmp/coffres_captures/caf1_cap0_temoin_camera_0_35_-35.png`: control with heading 0 (unchanged) and the camera rotated.
- `/tmp/coffres_captures/titre_ile_avant_gauche_apres_droite.png`; full frame: `/tmp/coffres_captures/titre_avant_700.png` and `/tmp/coffres_captures/titre_apres_700.png`.
- Tools (not committed): `/tmp/cof/chest_shot.sh`, `/tmp/cof/batch2.sh`, `/tmp/cof/batch3.sh`, `/tmp/cof/sheet.py`. "Before" base: copy `/tmp/coffres_avant`. Full `carte9` cache of my trials: `/tmp/uicache_coffres` (523 maps; does not touch `/tmp/uicache4`).

## Established / Assumed / Not verified
**Established** (read in the code or observed):
- Order `rotateXZY` and axes (disassembly + dump).
- `pmv_func` and `c_pmv_func`: sum of the Euler angles then `rotateXZY`, multiplicative scale, `c_pmv_func` displacement in the object's frame.
- CPMV choice by `flag & 4`.
- The engine only sends animations 2 (open) and 4 (close) for the chests.
- The 194 chests, the drawers and the doors of all maps pass the tests.
- Screenshots under xvfb (Mesa): the lids open toward the back of the chest at all headings, the drawers come out toward the front.

**Assumed:**
- That the user's screenshot comes from `mdi1f1` (shop with a "bag" crest, floor, white pillar; the only chest with heading -27; the "before" rendering with the default camera has the lid with its outer face toward the player). Identification by resemblance, not by a save.
- That « orientés vers le joueur » (EN: "oriented toward the player") means the chests with heading ≠ 0.
- That the original does not turn the chest toward the camera: flag 0, no rotation sent. If we want it to do so when the camera turns, that would be an unfaithful addition.

**Not verified:**
- No comparison with a phone screenshot (none available).
- No game played with a real chest opening (animation launched by `DQ_ANIM_TEST`, same `common_anim` path as packet 5).
- Windows GPU rendering.
- Who calls `setRotObjectUid` by script (an event could turn an object).
- Direction (2 versus 4) of the doors: chosen by the engine (not read), the viewer plays the number received.

## Merge pitfalls / to flag
1. **Title (`ev01`)**: the castle island (`tenkuzyo2e`, rot (-43, 39, -18)) changes its tilt. The "top" of the island goes from (-0.24 ; 0.56 ; 0.79) to (0.25 ; 0.70 ; 0.67): before, castle leaning to the left; after, castle nearly vertical, island tilted the other way. Consistent with the original code, but the "titre" agent must know before re-aligning "dragon and castle" on the mobile.
2. **Cache**: the name `carte9_` must remain the largest among agents. If another agent also changes the prefix, take the max and keep the purge `carte[0-N]_`. At the first launch, the 523 maps are prepared again (background preparation: 0.1 to 0.3 s per map in test).
3. `window.py`: a single line added (test), conflict very unlikely.
4. `tools/test_map_items.py` is new; the existing tests do not depend on `euler_mat`.

## Doc notes to merge (viewer-notes + technical-notes)
**Chests, drawers: rotation of map objects (#43).**
- Chests with heading ≠ 0 opening sideways or toward the front, drawers coming out sideways (Screen 3 of 2026-11-02).
- Cause: `data.euler_mat` composed Rx·Ry·Rz whereas `FldObject.rotateXZY` (0xCD47F0) does (AngleAxis(ry, up) * AngleAxis(-rz, forward)) * AngleAxis(-rx, right): X first in the object's frame, Z, then Y (the heading) last = Ry·Rz·Rx. The "X, Y, Z" order of #21 was a misreading.
- The common movements (FPMV, flag & 4) are read by `c_pmv_func` (0xCD96D8) in the object's frame; `update_pmv_one` (0xCD6824) chooses CPMV (4) when flag & 4, otherwise PMV (1).
- A chest = `tbox01` (body) + `tbox02` (lid, origin = high rear hinge). Animation 2 = opening (rx 0 to -60), 3 = held, 4 = closing. The engine only sends `SetCommonAnimation` 2 or 4 (`TownFurnitureObject::openObject / closeObject`), never a rotation toward the player.
- Chest headings: 184 out of 194 at 0; the others in `ham1f1`, `hcy1b1`, `mdi1f1`, `sjout`, `ss5b1b`, `tcf1`, `tcf3`.
- Common animations of the game: chests rx, drawers posZ, doors and wardrobes ry (unchanged).
- Cache `carte9_`.
- Side effect: about 280 tilted objects change orientation, including the title island.
- Test: `tools/test_map_items.py`.
- Still not verified: see above.

Memory (information useful for later, source = this session): the user tests his screenshots on real maps of the game (the "Screen 3" screenshot very probably corresponds to `mdi1f1`, heading -27).

---
