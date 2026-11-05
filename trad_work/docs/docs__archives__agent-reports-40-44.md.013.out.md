## Agent acb3a91d1ee1b129b — 2026-11-02 04:41

REPORT "titre2" (branch agent-titre2, worktree /home/claude/wt-titre2, base 08f5785). Clean tree. Tests: test_title_sky (22), test_start_menu_plate (12), test_title_camera (3), test_town_camera, panel/settings/sound: OK. pyflakes: only the known warnings (ax, sel, struct).

COMMITS (8): 585538a (data.py + map_objects.py taken from ac4cb9b, euler_mat Ry.Rz.Rx, carte9 cache); 9d15a85 (title 1:1: face direction, zoom, removal of the hacks, DQ_FBXLOG); 1903c66 (title_sky.py + tests); 49f5ffe (sky in window.py); fdd6b10 (auto plate + buttons/is_state_active); 4784e98 (title camera test); 5c17b72 (sky setting + gray text); 599d54c (engine.py: default FBX rotation).

A. DRAGON, "2 orientations"
Established: the dragon is placed ONCE by the engine (frame 2: pos (-2.16 ; 7.0 ; 0.55), yaw 349.45°, seen from behind, it looks toward +z, away from the camera). Its trajectory comes from the FBX clips: Take 001 (21.98 s) then Take 002 looping (2.18 s) at frame 662; it enters from the top ~420-480, dives ~540-620, lands above the logo 660-800 flapping its wings. Log: /tmp/t2_fbxlog.txt (DQ_FBXLOG=1).
Cause of the "2 orientations": culling. Unity's Cull Back = front faces clockwise on screen, whereas GL expects counterclockwise. The far inner faces showed through the near faces that were removed: we saw a "face" while the body was seen from behind. Fixed: glFrontFace(GL_CW) in _paint_fbx (DQ_FBX_CULL 0/1/2 to compare).
The euler_mat fix (ac4cb9b) does NOT explain it: it changes the tilt of the castle island (map objects, FldObject.rotateXZY), not the dragon (FbxObject.SetRotation = Quaternion.Euler).
Assumed: direction of the dragon's heading (no filmed mobile reference).

B. MOBILE 1:1
Established: the central 9:16 area is the phone rendering. Gaps removed: (1) zoom bug on ev01 (the hidden hero sprite triggered the zoom formula: scene enlarged ×1.185, logo wider than the area); excluded for ev01, and the same bug would exist on any map with a hidden hero sprite; (2) hacks TITRE_HAUT, TITRE_DRAGON_HAUT, _decalage_credits (+ _credits_cache, DQ_CREDITS_ORIGINE) removed: the credits are placed by the engine.
Measurement: 1281×720 window (columns 438..842) against 405×720, vignette at 0 (/tmp/rg_t2n.json): pixel-identical (mean 0.0004; ≤107 pixels out of 291,600 differ, text edges). 405×720 against 720×1280 downscaled: mean difference 0.6 to 1.3 (resampling). Captures: /tmp/m_t2n1_b{300,540,720,900}.png (1281), /tmp/m_t2n2_* (405), /tmp/m_t2n3_* (720×1280).
Pitfall: with the default vignette (0.3, user setting) the edges of the area are about 20% darker in a narrow window than in 16/9 (first diff misleading, compared with /tmp/t2_cmp900.png). It is not a scene difference.
Not touched: "Touchez l'écran" (UI layer, ui_k scale: 0.89 in a portrait/405 window against 1.0 in 16/9, i.e. y = 0.79 against 0.82 of the height; UI policy outside my scope).

C. LOGO / CREDITS
Established: logo centered (residual = asymmetries in the engine data); credits centered within ±1.5 px, left as the engine places them.

D. SKY
Established: new pure module /home/claude/wt-titre2/dq4_pc/title_sky.py. Outside the portrait area, bands of the same geometry as the sky rows (y, z, identical colors) take over the texture with a variable horizontal stretch (0.52 to 1.48, mean 1) and a 3% vertical slide that is zero at the row seams. Continuous join at the edge, scrolling followed. The area remains the original sky: area pixel-identical between band mode and copy mode (difference 0.0; /tmp/m_t2g1_b900 against /tmp/m_t2h1_b900). Fallback: any error gives the original sky alone; DQ_CIEL_COPIES=1 gives the old behavior; DQ_CIEL_PARAMS=a1,a2,glisse,longueur for tests.
Before / after (frame 900): 16:9 /tmp/m_t2h1_b900.png against /tmp/m_t2g1_b900.png; 21:9 (1920×820) /tmp/m_t2h2_b900.png against /tmp/m_t2g2_b900.png; very wide (1920×400) /tmp/m_t2h3_b900.png against /tmp/m_t2g3_b900.png; 16:9 sequence /tmp/m_t2g1_b{300,540,720,900}.png; mobile reference /tmp/m_t2z3_b900.png; rejected variants /tmp/m_t2v1_b900.png and m_t2v3_b900.png. Honest opinion: the regular carpet of identical copies is broken (variable widths and heights), but the same cloud shapes remain recognizable. This is the limit of "intact area + a single texture".

E. START MENU
Established: plate "Sauvegarde automatique" (cell 4, data5) always visible with its label. Without data5: state 3 (grayed), gray text, no touch area (no click, no hover, no keyboard validation). With data5: normal and active, engine label kept.
Audit of the original (disassembly): code 0 = availability of data5; the engine sends the label (4,1) only if data5 is valid; the original HIDES plate 4 without data5. Cells 0/1/3 (type 53) are grayed by the engine when unavailable; the type 54 lists have no states. The engine does not block the validation of a grayed cell, it is Unity that cuts the contact test for states 2/3/4 (BUTTON_STATE_*); the viewer now does the same.
Choice: grayed rather than hidden (« je te laisse choisir » (EN: "I'll let you choose")). DQ_AUTO_CACHEE=1 restores the original (hidden).
Behavior changed: plate 4 (new visibility); gray text of grayed plates; grayed "Continuer"/"Reprendre"/"Supprimer" are no longer clickable.
Verified with two sets of saves (copies in /tmp, data5 removed from the copy): without /tmp/m_t2p1_b380.png; with /tmp/m_t2p2_b380.png. Real click on the grayed plate: nothing happens (/tmp/t2c1_sheet.png), Enter validates "Continuer".
Not verified: rendering of the original gray shader and gray of the text on mobile (gray text = viewer choice, Assumed); fallback label (FR string from the patch assumed).

NOT VERIFIED (global): Windows; windows wider than 4.8:1; real 720×1280 window by the user (tested under xvfb only); dragon heading against a mobile capture.

DOC NOTES TO MERGE (not written in docs/):
- Culling: Cull Back = clockwise on screen, hence glFrontFace(CW).
- Hero zoom to exclude when sprite 0 is hidden (ev01, and any similar map).
- Dragon: placed once, trajectory = FBX clips Take 001 then Take 002 at frame 662.
- Table of button states 0 normal, 1 pressed, 2 invisible, 3 gray, 4 inverted; hit-test cut for 2/3/4.
- The engine hides plate 4 via code 0; the engine does not block clicks on grayed cells.
- Sky method and constants; environment variables DQ_CIEL_COPIES, DQ_CIEL_PARAMS, DQ_AUTO_CACHEE, DQ_SANS_CREDITS, DQ_FBXLOG, DQ_FBX_CULL.
- The vignette (user setting) makes the edges of the portrait area differ from the mobile; to be turned off to compare 1:1.

MERGE PITFALLS:
- window.py, touched areas (by function): import of title_sky (after `import fbx`); removal of the constants TITRE_HAUT and TITRE_DRAGON_HAUT (~l.112); Game.__init__ line ext_map/ext_sky/_M_town/_town_aspect (l.181); _town_camera (condition `map_name != 'ev01'` on the hero zoom, yoff without TITRE_HAUT); _battle_meshes (removal of _decalage_credits and _credits_cache, DQ_SANS_CREDITS kept); _load_map (ev01: call to _title_sky); new methods _title_sky and _paint_sky (before _calc_hd_scenery); _paint_scenery step 0 (call _paint_sky); _paint_fbx (glFrontFace CW, mvp translation removed); _draw_menus (type 53: center_menu then auto_plate); town rendering (`self._M_town = M; self._town_aspect = aspect` before _paint_scenery(True)).
- ui_menu.py: buttons() now ignores states 2/3/4 in ALL windows; additions auto_plate, gray_texts, is_state_active, vals_code, auto_grayed.
- engine.py: default rotation of packet 31 = (0,0,0); DQ_FBXLOG in packet 32.
- data.py and map_objects.py come from ac4cb9b: probable conflict or duplicate when merging the coffres branch (take a single version; cache renamed carte9, old cache invalidated).
- New tests: tools/test_title_sky.py, test_start_menu_plate.py, test_title_camera.py.

Reusable capture scripts: /tmp/t2_final.sh, /tmp/t2_zone2.sh, /tmp/run_t2.sh (SAVES=...), /tmp/t2_diff.py; test saves /tmp/sv_t2_sans, /tmp/sv_t2_avec.

---

## Agent a3150b360db4a6624 — 2026-11-02 10:22

REPORT HCB (battle history: capture of the results), branch `agent44-histocombat` (worktree /home/claude/wt44-histocombat, base 6580393). Clean tree. 3 commits: 41b0792, 7ca0446, 17729a8 (2-line footer). Files touched: ONLY the 2 NEW `dq4_pc/battle_history.py` (283 l.) and `tools/test_battle_history.py` (552 l.). No line modified in window.py / engine.py / history.py / ui_history.py / pause.py. pyflakes clean. No push.

== API provided ==
`class BattleSensor`: `__init__(engine)` (hooks READ-only, nothing written into the engine memory; cleanly deactivates itself `active=False` if the engine is not the one studied), `do_update(engine) -> list[dict]` (once per frame after `eng.step`, never raises), and `BattleSensor.for_(eng)` (single sensor per engine, created on the 1st request, hooks installed only once).
dict = `{'t': g_Game+4 (1/60 s) at the end of the battle, 'ennemis': [{'nom','total','vaincus'}, ...] (1 entry per species, order of appearance, displayed French name), 'or': int, 'xp': int, 'issue': 'victoire'|'fuite'|'defaite'}`.
Reusable pure part: `Tracking`, `build_battle`, `plate_name`, `group_names`, constant `OUTCOMES`.
xp = value PER MEMBER read from the message ("Chaque membre de l'équipe reçoit N points d'expérience", after possible doubling); gold = team total ("L'équipe reçoit M pièces d'or"). gold/xp = 0 for escape and defeat (the engine pays nothing: verified). Missing data = 0 / name 'Monstre'.

== THE integration line (at the lead's choice, in window.py right after line 2611 `self.history.do_update(eng, ...)`, or in the lead's History.do_update) ==
`for combat in HC.BattleSensor.for_(eng).do_update(eng): <lead's consumer>(combat)`   (with `import battle_history as HC`). Nothing to create elsewhere.

== Established (measured on the real Unicorn engine, save 1, forced battles) ==
- Victory: dict identical to the game text ("reçoit N points d'expérience", "N pièces d'or") AND to memory (group gold before/after; experience of each member before/after). Mutation test: an xp falsified by +1 makes the test fail.
- Several species (2 and 4, order of appearance verified), several members (Ragnar gains, guest Doc gains none although the message says "chaque membre"), gold/xp doubling (BaseAction::doubleFlag_: the dict gives the number from the message).
- Successful escape after failed attempts (BattleExecEscape::setup draws on EVERY attempt, not only on success) and escape after a death: outcome 'fuite', gold/xp 0, partial defeated counts correct.
- Defeat / game over reached (monster no. 150 ×3): outcome 'defaite', gold/xp 0.
- Two battles in a row: 2 distinct dicts, t increasing.
- Battle interrupted by a loaded savestate (in town, or mid-battle): nothing false, no crash, next battle properly reported. Sensor created in the middle of a battle or after other battles (blocks already translated, ctl_flush_tb): correct.
- Names: sweep of the numbers 0..187: for all ordinary monsters the dict name = name from the game's appearance message (engine plates type 31, one plate = one group).
- Cost of do_update: outside battle 0.3 to 3 µs/frame (against 0.7 to 1.5 ms per engine step), in battle ~46 µs on average.
- Tests: 57 tests OK (~60 s with engine). Pure: computation (Tracking, names, build_battle) + glue on a FAKE engine (state break, skipped frames, abandonment after 20 frames outside battle, swallowed errors, event safeguard). Optional real engine: `DQ_APK="/mnt/user-data/uploads/DQ Patch/jeux/DQ4/patched_apks" DQ_SAVES=/mnt/user-data/uploads/dq4-portage/dq4_pc/sauvegardes python3 tools/test_battle_history.py` (writes to a temporary folder, skipped if the variables are missing). Without xvfb.

== Assumed ==
- The plate names are reliable up to the 1st death (beyond that the matches are no longer certain: name 'Monstre' for a species that arrived later, e.g. a summoned reinforcement).
- A hyphen at the end of a plate line is rejoined without a space: "Scara-somniaque", "Typhon-phonphon", "Pterrori-dactyle" (consistent with the message). Ambiguous case: "Psaro l'Exter-minateur" (word break or real hyphen? the engine does not say).
- Outcome 'fuite' deduced (no victory routine nor defeat flag, battle ended): the case of a monster that flees alone = same outcome.

== Not verified ==
- Scenario battles / scripted bosses (BattleScriptManager): boss names read (Pruslas, Rashaverak, Aamon, Barbatos, Lord Lionel, Dickenz...) but not compared with an appearance message (the game emits none); scripted victory/defeat not played.
- Monsters that flee on their own, real Windows/GPU (engine-only test).
- Saves other than 1 (party of 2 members).

== Known limits (by design) ==
- A battle whose start was not seen (state loaded mid-battle, sensor created mid-battle) is NEVER reported (better nothing than something false).
- A slot emptied then refilled by the same monster in the same frame would be undercounted.
- Abandonment of a battle without endBattle (return to the title): tracking dropped after 20 frames outside battle.

== Merge pitfalls ==
- Do NOT put `do_update` in a loop that would call it several times per engine frame: call it exactly once per `eng.step` (the frame delta is compared: gap >8 or state replaced = break, tracking abandoned).
- `Engine.state` is replaced by savestates.apply: the sensor detects it, but keep the lead's consumer independent of the state object.
- The dicts come out at the frame where endBattle runs; 't' is the game clock (same base as history.Sensor.time_and_key).
- The raw text of the battle messages contains ";" and "$" (patch break marks): do not confuse them with monster names, which are already cleaned here.

== Notes to merge into docs/ (at your discretion) ==
- Hooks (symbols): start `_ZN6status11PartyStatus11startBattleEv`; death `_ZN19BattleActorManager216execMonsterDeathEi` (x1 = index among the OCCUPIED slots); victory `_ZN23BattleExecDefeatMonster10initializeEv`; escape (attempt) `_ZN16BattleExecEscape5setupEv`; end `_ZN6Global9endBattleEb` (bit0 = annihilation, + flag g_BattleResult+0x509).
- Memory: g_Party+0x2e0 group gold, +0x2f8 battle experience (per member), +0x2fc battle gold (team); g_Monster 12 slots at +8, step 0x538, +0x4f8 monster no. (0xffffffff = empty), +0x4fc group no.; a member's experience = originalPlayer_+0x530*k+0x60 (0xffffffff = gains none).
- Monster plates: Engine.ui window type 31, `dispo` = number of groups, plate j = j-th group (sorted group index); they only arrive when the target choice opens (not at the start of the battle); text "Nom\n\n\t×3" or "Début \n\nsuite" for a split name.
- Forcing an encounter in a test: hook on `BattleRoot::setupMonster`, write into Encount (`Encount::getSingleton`) the numbers at +0x34+4j and the counts at +0x44+4j; launch with `Global::startBattle(eng._global())`.

== Memorable facts (source: this mission, measurements on the engine) ==
No new user preference. Project facts: the engine pays neither gold nor xp for an escape; BattleExecEscape::setup draws on every escape attempt.

---

## Agent aba2eb4af16a27785 — 2026-11-02 10:24

REPORT PAQ (agent 44, ignored engine packets) — full version, measurements of the last GL batch included. Worktree /home/claude/wt44-paquets, branch agent44-paquets, base ab22007. 2 commits, clean tree: a598be1 (PAQ-1, packet 33) and c8681df (PAQ-2, packet 13). Two-line trailer on both. Nothing pushed.

1. TABLE OF FINDINGS
| ID | what | evidence | status | class | fixed? | effort |
| PAQ-1 | Packet 33 (scenery tint) ignored | `cmd_map_color_rate` RVA 0xD14E44 → `FldObject.m_color` (town/battle) or `Field.SetColor` (world); `update_material_color` RVA 0xCD79F4: Material.color = _OrgColor × m_color except for a material without a main texture or whose texture name contains "tz_"; fld_* shaders decoded (LZ4 blob, GLES3) = texture × vertex color × _Color, saturated on write; sprites/shadows/UI not touched | Established | oversight | yes, a598be1 | — |
| PAQ-1b | _OrgColor = (1,1,1,alpha), not the asset's _Color | `FldObject.save_org_color` RVA 0xCD811C re-disassembled (s0 to s2 = 1.0 then SetColor("_OrgColor")); coordinator's clarification confirmed | Established | cache bug (data.py) | no: the coordinator does it (audit2-histo branch, cache carte9 → carte10). My `teinte` uniform remains valid (white = neutral); comments corrected in a598be1 | — |
| PAQ-2 | Packet 13 bit 0x800 (sprite scale) discarded | `cmd_chara` RVA 0xD12EA8: Chara.SetScale → localScale = 1.8 × s on the panel; sweep of 529 maps / 1062 characters | Established | oversight | yes, c8681df | — |
| PAQ-2b | Values 0.025 to 0.08 ("0.045 / 0.059" in the audit) = starting value of the 1st update (placement), followed by 1.0 in one frame | sweep13 | Established | — | ignored in the code | — |
| PAQ-2c | Audit hypothesis "sprites wrongly sized in mlb1a" | mlb1a: 0.7383 from engine frame 23 to 438 during the opening BLACK SCREEN, then 0.74 → 1.0 in 10 frames; in GL the hero is visible when it is already 1.0: captures with / without scale identical (1 px of noise). ev07 (0.9519): 1514 px changed (0.2%), sprite 5% smaller | Established (refuted for mlb1a) | — | — | — |
| PAQ-3 | Packets 16/17: lying-down poses (sleepers) not replayed | mlm2f1: packet 16 = 0xc000508 / 0x509 (characters 8 and 9, sleep bit); capture /tmp/m_paqD_mlm2f1_b300.png: the man in the bed is displayed sitting/standing; mlb1a: sleep set at frame 20 then removed at 21 (no effect); taf1: 17 [1040, 1863] (no obvious sleeper, /tmp/m_paqD_taf1_b300.png) | Established (visible gap); mechanism Assumed | oversight | no | 1 to 2 days: CharaSleep shader, `_sleepMatrix`, `CalcLieBillboard` (0xCCD1A8), `SetSleepDir` (0xCCC5A0), `lieSetPosition` (0xCCCED4), `SetSleepNear`; check on mlm2f1 |
| PAQ-4 | Packet 18 (`changePose`) | 0 maps out of 529 | Established (never emitted at load) | oversight with no observable effect | no | — |
| PAQ-5 | Packet 6 (`fld_event_anim`) | `cmd_fld_event_anim` RVA 0xD1298C: ≥ 0x1000 → `FldObject.SetCameraNo(v & 0x3fff)`; otherwise `SetEventAnimation(v)` (0xCD637C); 0/529 at load, triggered by scripts | Established (dispatch); FEAN format Not verified | oversight | no | ~1 day (FEAN data, replay); check on a scripted scene |
| PAQ-6 | Packet 30 (`field_scale`) | `cmd_field_scale` RVA 0xD12794: int ≥ 0 → `Field.SetFloatingObject`; float → `Field.SetScale` (0xCD353C): orthographicSize = base × s + `FloatingObject.SetScale` on each floating object; emitters: balloon (`balloonExec`, `downBalloon`, `rideBalloon`, `setScriptBalloon`) | Established (zoom formula); scale base and world camera Not verified | oversight | no | 0.5 day; a save in the balloon is needed (none) |
| PAQ-7 | Packet 34, effects 3/5/6 | `cmd_screen_effect` RVA 0xD15024 → `Capture.ScreenEffect` RVA 0xCC6474: (v & 0xf) 3 → `Tabi` (bit 7 as parameter), 5 → `DarkLamp` (bit 7), 6 → `Riremito`, otherwise `BattleEffect` (only 4 is replayed); coroutines | Established (dispatch); formulas Not verified | oversight | no | ~1 day per effect |
| PAQ-8 | Packet 1 (`fld_color`) | `cmd_fld_color` RVA 0xD12C98 → `FldObject.calculateExecSepia`; no emitter, 0/529 | Established (target); unused Assumed | decision | no | — |
| PAQ-9 | Packet 27 (`field_load`) | bypassed: world read from the engine memory (`_read_world`); my branch only resets the tint to neutral | Established | decision | partial | — |

2. FIXES (one commit per packet)
- a598be1 PAQ-1: `State.tint` (engine.py: reset to neutral at packet 0 and packet 27, branch for 33); new `dq4_pc/map_tint.py` (recognition of the "tz_" groups: list of path_ids read ONCE from the data pack, ~3 s + ~800 MB, in a thread, kept in `tz_cles.json` of the cache; fallback: everything is tinted); window.py: `teinte` uniform in the fragment (clamp(rgb × teinte)), tint per group in `_paint_scenery`, and in `_paint_field` (tiles + world symbols; sprites not). Switch `DQ_SANS_TEINTE=1`. Neutral tint = path unchanged.
  Measurements: dab1 (neutral) base / new / off = 0 pixel difference; mlb1a (real tint 1.25/0.65/0.75 emitted by the engine): 15.3% of the pixels changed, purple rendering (/tmp/m_paqA0_mlb1a_b420.png before, /tmp/m_paqA1_mlb1a_b420.png after); `DQ_SANS_TEINTE=1` on mlb1a = old code (0 px at frame 200, 1 px of noise at 420); teout1 with the engine values forced (1.3/0.7/0.55): 97.8% of the pixels, mean RGB 86.9/108.9/114.7 → 110.4/76.8/63.8, orange rendering (/tmp/m_paqB_teout1_base_b420.png → /tmp/m_paqG_teout1_f_b420.png); mlout1 forced (1.25/0.65/0.75): 97.5%, 65.6/100.8/57.4 → 80.2/66.6/44.0 (/tmp/m_paqG_mlout1_off_b420.png → _f_); world map slot 4, forced tint (0.8/0.8/1.1): 99.6%, 67.0/105.7/135.0 → 53.9/84.9/148.0 (/tmp/m_paqG_monde_off_b200.png → _f_). The translucent message window is darkened by transparency, not tinted. The world map sprites were not inspected on the image.
- c8681df PAQ-2: field `ech` (1.0 by default); `t == 13`: if bit 0x800 and position already set, `ech = fl[0]` (the 1st value, the placement one, is ignored); window.py, `cam3d` branch: panel × k (bounded 0 to 8), feet fixed, depth offsets scaled by k; shadows not scaled (Assumed); `DQ_SANS_ECHELLE=1`. Test: `tools/test_map_tint.py` (18 tests OK, 1 skipped without APK). Verification: dab1 (scale 1.0) identical to within 1 px (noise also present between two passes of the same code); mlb1a identical on the visible frames; ev07 1514 px.
- Files touched: dq4_pc/engine.py, dq4_pc/window.py, dq4_pc/map_tint.py (new), tools/test_map_tint.py (new). data.py, map_objects.py, `_menu_input` not touched.

3. NOTES TO MERGE INTO docs/ (ready text)
- technical-notes (replace the line ~233 "Not reproduced: packet 33 …"): "Packet 33 (`cmd_map_color_rate`): three floats → `FldObject.m_color` (town/battle) or `Field.SetColor` (world). `FldObject.update_material_color` (RVA 0xCD79F4), every frame: Material.color = `_OrgColor` × m_color, except for a material without a main texture or whose texture has 'tz_' in its name (lamps, candles, waves…: not tinted). `_OrgColor` = (1,1,1, alpha of `_Color`) (`save_org_color`, 0xCD811C): the asset's RGB `_Color` color is never used in game. fld_* shaders: texture × vertex color × `_Color`, saturated on write (tint > 1 possible). Sprites, shadows, bubbles, interface: not tinted. Viewer: `teinte` uniform (window.py), 'tz_' groups by `map_tint.py` (`tz_cles.json`), `DQ_SANS_TEINTE=1` to compare. The value depends on the engine's time zone and persists from one map to the next: cold from our saves only mlb1a (1.25/0.65/0.75) emits one; loaded after it, mlout1, mmout, mlout2 receive the same and teout1 (1.3/0.7/0.55) (probe pk33c); caf1/ev02: 0.804/0.807/1.102, in slow fade."
- viewer-notes (lines ~72/83/141): "Packet 13 bit 0x800 = Chara.SetScale (localScale = 1.8 × s, panel only), applied (`DQ_SANS_ECHELLE=1` to turn it off). Only mlb1a (0.7383 during the opening black screen, then 0.74 → 1.0) and ev07 (0.9519) have a value ≠ 1 after placement. Lying-down poses (packets 16/17): still NOT replayed, visible on mlm2f1 (bed sleeper displayed sitting). FEAN / packet 6 and effects 3/5/6 of packet 34: dispatch read (`SetEventAnimation` / `SetCameraNo`; `Capture.Tabi` / `DarkLamp` / `Riremito`), content not replayed. Packet 30: `Field.SetScale` = orthographicSize × s + FloatingObject.SetScale, not replayed."
- Test pitfall: a `DQ_VILLE` launch of a single map does not reproduce the audit tints (sequential sweep, inherited time zone). Load mlb1a first (chain `gl_chaine.py`) or force `TEINTE`.

4. NOT VERIFIED / GOOD TO KNOW
- Windows, real GPU, computation of `tz_cles.json` on the user's PC (~3 s + ~800 MB once; thread; without it everything is tinted).
- BATTLE scenery tint and world tint emitted by the engine (day/night, swamp): not captured for real. World map tested only with forced tint.
- Saturation order: my shader does clamp(tex × vertex × tint), identical to the original once the cache is cleaned of the asset color (coordinator's work, data.py). As long as the carte9 cache keeps the asset `_Color`, materials with _Color ≠ white (night scenery in battle) remain wrong with or without tint. No conflict expected with audit2-histo.
- "3 maps" measurement: mlb1a with real tint; teout1 and mlout1 with the engine values forced (launcher `.../scratchpad/gl_teinte.py` + `run_gl_teinte.sh`). Attempt at a chain mlb1a → mlout1: the real tint is indeed emitted (TEINTE log) but the screen stays black (opening event of mlb1a in progress): unusable image.
- Merge pitfalls: window.py (`cam3d` branch of the sprites, FRAG shader, `_paint_scenery`, `_paint_field`) and engine.py (`State.apply`, branches 13/33/27); the "casino" agent touches parts 0xf/0x10 and `_menu_input`.
- The session scratchpad is SHARED with other agents (my p2.py was overwritten there): my tools are in /tmp/claude-0/-home-claude/17145693-c62f-5af6-a741-2d4f94a36edf/scratchpad/paq44/ (gl_ech.py, gl_chaine.py, pk33.py, pk33c.py, pech.py, batch*.sh).
- Useful captures: /tmp/m_paqA0_mlb1a_b420.png, /tmp/m_paqA1_mlb1a_b420.png, /tmp/m_paqB_dab1_{base,new,off}_b{300,420}.png, /tmp/m_paqB_teout1_base_b420.png, /tmp/m_paqG_teout1_f_b420.png, /tmp/m_paqG_mlout1_{f,off}_b420.png, /tmp/m_paqG_monde_{f,off}_b200.png, /tmp/m_paqG_mlb1a_off_b420.png, /tmp/m_paqC_ev07_{ech,sans}_b420.png, /tmp/m_paqC_mlb1a_{ech,sans}_b420.png, /tmp/m_paqE_mlb1a_{ech,sans}_b{340,380,400,430}.png, /tmp/m_paqD_mlm2f1_b300.png, /tmp/m_paqD_taf1_b300.png.

To remember for the main session: (1) the session scratchpad is shared between sub-agents, use one sub-folder per agent; (2) `pkill -f` on a script name present in the shell's command line kills that shell; (3) the packet 33 tint depends on the engine's time zone state and persists from one map to the next.

---
