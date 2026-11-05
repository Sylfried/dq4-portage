# Final reports of the agents of batches #40 to #44

Raw reports delivered by the sub-agents of the session of 2026-10-31 to 2026-11-02 (investigations, audits, fixes); the useful notes are already merged into `docs/notes-*.md`. The `/tmp/...` paths cited no longer exist.

---

## Agent a7fa4380330259e25 — 2026-10-31 16:16

REPORT: shadows (A) and cave water (B). Nothing was modified in the repository (`git status` clean; `git apply --check` OK for both patches). Everything is in the working folder S = /tmp/claude-0/-home-claude/17145693-c62f-5af6-a741-2d4f94a36edf/scratchpad/enq_deco

== COMMON CAUSE of B and the scenery shadows (verified) ==
The viewer ignores the `_Color` of the map materials and draws all the "opaque" scenery (`data.py::_texture()` does not read `_Color`; `window.py::_paint_scenery` uses cutoff 0.5, depth write, LESS). The original game chooses the shader at runtime in `FldObject.set_shader` (RVA 0xCD5414):
- texture name without ".tim", OR `_Color.a != 1` -> `Custom/fld_trans` (Blend SrcAlpha/OneMinusSrcAlpha, ZWrite off, ZTest LEqual, queue 3000 + `prio` via `FldObject.set_priority` 0xCD7DA8);
- otherwise RGBA32 texture -> `fld_atest` (rejects only alpha == 0); otherwise `fld_normal`.
In all the `fld_*`: final color = texture x (vertex color x `_Color`).

== B. Cave water ==
Cause: the water models (objects `<carte>wt..`, texture `mawater1.tim` RGB24, medium cyan (54,205,203), alpha 255) have `_Color` = (1,1,1,0.2). The viewer drew them at alpha 1: solid cyan, hence the « électrifié » (EN: "electrified") effect. The `wtkira` palettes (FPLP) exist only in the 37 outdoor and town maps, not in the caves: this is not a lead. No additive blend.
Fix: patch `S/out/correctif_decor.patch` (data.py + window.py, applies as is to the repository).
- `_texture()` also returns `_Color` and the "kind" (trans / atest / normal); `bake` multiplies `_Color` into the vertex colors (and into `_frames`);
- the "trans" materials have their own group `('tr', prio, key)`;
- `_paint_scenery` draws the opaque groups first, then the `('tr', ...)` ones sorted by prio, with read-only depth, LEQUAL and cutoff 0;
- the cache goes from `carte5_` to `carte6_` (2 places in data.py; the old caches are ignored, so the first extraction is slower).
Proof (cave `dgb1`, center of the basin, RGB): (38,141,140) -> (29,87,93), brightness 0.55 -> 0.37. The gas, the waterfalls and the mist (`.tm2` textures) also become soft. The output of the clean patch is identical pixel for pixel to my experiment (max diff 0).
Before (left) | after (right) screenshots, in S/out/: pair_dgb1.png (the lightest), cmp_dgb1_pool.png (close-up), pair_dlb4.png, pair_deb2a.png, pair_dob1.png, pair_dnb2.png, pair_djb1.png. Raw: dgb1_av_b80.png / dgb1_ap_b80.png.

== A1. Scenery shadows (« trop brutes » (EN: "too harsh") and « pas tout a des ombres » (EN: "not everything has shadows")) ==
The scenery shadows are separate geometry, at y = 0 (stuck to the ground): `idokage1` (well), `maokage1`, `maoutsk1`, `*kg*`. Two cases, a single cause (the same as B):
- soft shadows in `.tm2` with low alpha (`kage1c` {0,14,28,42,86}, `kage1a` max 126, `hcokage1` / `ceokage1` max 96, `tekg1` max 126): the cutoff 0.5 rejects them all -> wells, buildings and others without shadow (51 maps out of 670 affected);
- shadows in `.tim` with binary alpha (`nk_sk1kg`, `y_sk2bkg`) with `_Color.a = 0.4` ignored -> 100% black, hence « brutes » (EN: "harsh").
The patch for B fixes both. Before/after: S/out/pair_maout_well.png (well) and pair_maout.png. The "LESS instead of LEQUAL" lead was tested and ruled out (dq4_t1: no extra shadow).

== A2. Character shadow (hero and NPCs): prototype done, town only ==
Why absent: the viewer does not draw them. The engine does not command them in town: packet 15 (`chara_shadow`) is never sent there (verified in the maout logs), so the default `Chara` shadow applies to all of them. On the world map it only sends `[522]` / `[523]` (hides the shadows of slots 10 and 11). `engine.py::State.apply` does not handle packet 15.
Original rendering (decoded from `Chara.SystemInit` and `SetShadowPosition` 0xCCCF38):
- mesh `s_shadowMesh`: square ±1 in XZ at Y = 0.00625, UV (0,0)(1,0)(1,1)(0,1); scale `s_shadowDefScale` = (0.347; 10; 0.206) -> ellipse of 0.694 x 0.412, 0.0625 above the plane;
- texture `CharaTex/common` (32x32, black, alpha 96/255 = 0.376 inside the ellipse, 0 outside, binary, point filter, clamp). Extraction: `Data.texture('common')`; preview S/out/tex_common.png;
- shader `Custom/CharaShadow`: tex x `_Color`, Blend SrcAlpha/OneMinusSrcAlpha, ZWrite off, ZTest LEqual, Cull Back, queue 2999 (before the sprite);
- position = position of the Chara + rotation of the panel x (0; 0; 0.25), i.e. `p - f_*0.25` on the viewer side: same point on screen, but shifted toward the camera, hence in front of the ground; orientation = camera yaw only, flat;
- final alpha = 0.376 x `SetShadowAlpha` (1 by default) x sprite alpha if < 1 (`SetColorWithShadow`); `SetVisible` also hides the shadow except `m_bSeparateShadow`; shadow object inactive if `no` is 193 or 194.
Prototype: patch `S/out/correctif_ombre_chara.patch` (to be applied AFTER correctif_decor.patch; window.py only, new method `_draw_character_shadows`, constants `SHADOW_HALF_SIZE` / `SHADOW_HEIGHT` / `SHADOW_OFFSET`). The two patches combined give exactly `S/prop/fenetre.py` and `S/prop/donnees.py`, the files I tested.
Proof: church `mak1f1`, S/out/pair_ombre_chara_eglise.png (before | after): sharp dark ellipse under the cardinal's feet; luminance ratio measured on the shadow pixels: min 0.620, expected 1 - 0.376 = 0.624. The outline is sharp (binary texture, point filter), as in the original, contrary to what one might think.

== UNCERTAINTIES ==
- Character shadow: positioning verified on a single screenshot (church). The exact vertical offset (0.0625 + vertical component of the 0.25 setback) is not compared with a screenshot of the mobile game.
- To add: do not draw the shadow if the sheet id is 193 or 194 (not verified that `no` = sheet id; h194 does not exist in the textures, h193 does); handle packet 15 for the world map.
- World map (top view) not handled: shadow at X rotation 36°, scale `shadowDefScale` x 28.8, `m_chara` at 51.84; `SetFieldShadowPosition` is only partly decoded.
- Sorting of transparents: at equal `prio`, Unity sorts the renderers from farthest to nearest; not implemented. The triangles of `s_shadowMesh` are not decoded (quad of 2 triangles assumed).
- The 5 RGBA32 `.tim` textures with partial alpha (`cfsk01`, `isneon`, `PDKA01_A`, `cm1mon2`, `kd02a`) should follow `fld_atest` (reject at alpha 0 only); I leave the cutoff 0.5 (minimal difference).
- The thin strip of translucent water on the ground next to some basins (water mesh larger than the basin, water at y = 0.1) is probably identical in the original; not confirmed. Gamma / sRGB not examined.
- `.tim` shadows at 0.4 verified only in maout. The tinted `_Color` (33 materials, mostly `btl_*` scenery) are now applied by the same patch: not verified in battle.
- Screenshots cannot be compared frame by frame between two runs where real time is involved (moving NPCs): for the church pair, the before was rendered with the shadows computed but not drawn.

== TO REMEMBER (from my investigation of the game's data and code; nothing said by the user) ==
- `FldObject.set_shader` (0xCD5414) chooses the shader of the map materials at runtime; `_Color` is multiplied into the vertex colors.
- Character shadow constants: see A2.
- The repository advanced during the investigation (damage, menus): my working copy `S/dq4_pc` is an older version; the patches above are rebased on the current repository (`S/dq4_orig` = repository at the time of verification).
- Trap: run the disassembler `/home/claude/il2/disasm.py` from /home/claude/il2 (it opens `libil2cpp.so` by relative path); my `S/dis_r.py` is its version with resolved strings.

Files: S/out/correctif_decor.patch, S/out/correctif_ombre_chara.patch, S/prop/ (tested patched versions), S/out/*.png (screenshots above).

---

## Agent adb969ea65cc6b771 — 2026-10-31 16:48

REPORT (read-only: repository /home/claude/dq4-portage not modified, `git status` empty, HEAD 63f2cc1 = main with #18/#19). Everything is in SCR = /tmp/claude-0/-home-claude/17145693-c62f-5af6-a741-2d4f94a36edf/scratchpad/enq_cb/ . Complete patch ready to apply (not applied): SCR/propositions.patch (syntax verified).

Method: instrumented copy of the code, one complete battle of 687 engine steps (slot 5, 2 Glacyclones, attacks/effects, damage, death, end), capture of EVERY step (images f = draw D1, g = draw D2, because the engine runs at 30 Hz and the display at 60 Hz = 2 draws per step) + meta.jsonl (packets, positions, draw order).

=== 1) "Vibration" when the enemies appear and 2) animation flicker: A SINGLE cause, verified ===
Cause: monster vertex buffer sent to the GPU one turn late.
- pyglet: `vl.position[:] = ...` only marks the buffer "dirty". The GPU upload happens in `buffer.commit()`, called by `Game._paint` (window.py l.396-408) only when the domain changes (`dom is not self._linked_domain`).
- `_draw_scene` (l.1659) sets `_linked_domain = None`, then `_paint_scenery()` (l.1668) binds and commits the single domain (all the vertex_lists without an explicit batch share the same one). Then `_battle_meshes(e)` (l.1669, called in the loop header) REWRITES the monster/effect vertices: the domain being already bound, there is no commit anymore: the monsters are drawn with the data of the previous frame (the commit only goes through at the next draw, via `_linked_domain = None`).
Proof (measurements):
- From the 1st step of the battle: at step 3 the monsters are ABSENT in D1 (mask 0 px) and present in D2.
- During the entry camera (steps 4-33, 1280x720, runs k1 vs k2): D1/D2 gap of the monsters' top edge average 3.7 px, max 11; left edge average 3.2 px, max 7; area average 4.5%, max 10.5%; 52 direction reversals out of 60 displayed frames with the current code, 0 with the fix. During this dolly the monsters move by 0.33 to 0.05 unit per step: the one-step lag alternates with a 0 lag at 60 Hz = back-and-forth vibration.
- Whole battle at HEAD (all_n1 vs all_n2, 640x360): D1 ≠ D2 on 415/687 steps (60%, up to 19,070 px of difference) with the current code, 0/687 with the fix (D1 == D2 exactly). Same result on the old copy (m1/m2). The effect meshes (slot 2, ~10 steps) and those of the monsters change at EVERY step, hence the flicker of attacks, spells, and the animation of the attacking enemy.
- Image: SCR/cs_m1_130.png (current: the lightning and the jumping monster alternate between two poses) vs SCR/cs_m2_130.png (fixed: monotonic movement). Figures: SCR/d1d2.json, SCR/d1d2_n.json; scripts SCR/d1d2.py, SCR/d1d2b.py.
Precise fix: window.py, `_draw_scene`, `elif is_battle:` branch; replace line 1669 `for tex, tw, th, vl, shader, hd in self._battle_meshes(e):` with:
```
monster_meshes = self._battle_meshes(e)      # rewrites the vertices ("dirty" buffers)
self._linked_domain = None                  # forces rebind + commit() at the 1st draw
for tex, tw, th, vl, shader, hd in monster_meshes:
```
(Equivalent variant: call `_battle_meshes(e)` before `self._linked_domain = None` of l.1659, like the sprites just above.) Verified: with this fix, no hole or residual flicker over the 687 steps (no A-B-A pattern, no packet 22 gap for slots 0/1; the remaining surface jumps are data-driven animations).
Uncertainties: (a) the visible effect depends on the display rate: at exactly 30 Hz the lag is constant (no vibration), at 144 Hz 1 draw out of ~5 is stale; (b) a single battle studied (2 Glacyclones): not tested with 3-4 groups or other spells; (c) the "2 draws per step" capture simulates 60 Hz; I did not measure on a real screen. Distinct latent risk, not visible here: the draw order of monsters of the same queue (2150) flips because of differences of 1e-3..1e-5 on the depth of the AABB center (l.762-763, `out.sort(key=lambda o: o[0])`, flips at steps 3, 5, 8, 14, 20, 24...); overlap of the 2 Glacyclones measured at 0 px over 109 steps, hence invisible here; if an overlap appears, proposed stable key: (queue, -depth rounded to 1e-3, slot).

=== 3) Battle message box too tall ===
Cause: height defined on the viewer side by the geometry of the window type in cache/ui_layout.json['message']['types'] (frameData 192/193/194), chosen by the engine message `[0,n]` (port 1, MenuMessage). The start of the battle sends TYPE 1 (frame 193: 188 units tall, canvas 164 lines = 4 lines of 34) whereas the field (type 0) = 126 units, canvas 100.5 = 3 lines; type 2 = 122 at scale 0.9; type 0 at the end of the battle = 126. The bottom is set by `_dz_message` (window.py l.1073-1081) on `CB_MSG_BOTTOM = -338` (l.62), independently of the height.
Measurements in pixels at 1280x720 (SCR/boite.py, white edge of the frame; SCR/boite_comparaison.png shows the 5 cases): field 116 px (bottom 43 px from the edge); current battle type 1 160 px (SCR/out_bx0/c_45.png); type 2 100 px (SCR/out_bx0/c_150.png); end type 0 104 px (SCR/out_bx0/c_560.png); all the battles: bottom 60 px from the edge. So only type 1 (battle opening messages, steps 7 to 62 of the studied battle) is too tall; types 2 and 0 already hold 3 lines.
Fix: bring the type 1 frame down to the height of type 0 (126 units; canvas 164 -> 102 lines = exactly 3 lines of 34), keeping the bottom edge unchanged so the distance to the edge (60 px) is identical. Code: ui_menu.py, new function `three_lines(t1, t0)` (before `class PageLayout`) + call in `PageLayout.__init__` right after l.50:
`if self.message: self.message['types'][1] = three_lines(self.message['types'][1], self.message['types'][0])`
(the function lowers by dz = 188 - 126 = 62 the vertices of the frame above the middle and the top of the canvas quad, and sets V of the canvas bottom to 102/512 = 0.1992; complete code in SCR/propositions.patch). Measured result: corrected type 1 104 px tall (SCR/out_bx1/c_45.png), bottom still at 659 px = 60 px from the edge, text unchanged at the top of the box. Types 0/2 and the field do not change.
Uncertainties: (a) I could not test an opening message of 4 monster groups (4 lines): the 4th line would be cropped; possible variant: keep the original frame when the engine writes more than 3 lines (the canvas "lignes" list, already read in the debug log), or limit the fix to the opening; (b) I do not know whether type 1 is used for other messages than the opening (not observed in this battle); (c) interpretation of « trop haute » (EN: "too tall") = type 1 (160 px, the only case > the field); if the user also targets types 2/0, they are at 100/104 px, lower than the field (116 px), so there is nothing to fix on the height side.

Proof files: SCR/propositions.patch, SCR/boite_comparaison.png, SCR/out_fld/s1_150.png (field box), SCR/out_bx0/c_45.png, c_150.png, c_560.png (current), SCR/out_bx1/c_45.png (fixed), SCR/cs_m1_130.png vs SCR/cs_m2_130.png (vibration), SCR/all_n1/ vs SCR/all_n2/ (f%04d.png = D1, g%04d.png = D2, meta.jsonl), SCR/d1d2.json, SCR/d1d2_n.json. Instrumented working copy: SCR/dq4_new/ (HEAD + instrumentation + fixes under the environment variables DQ_COMMIT, DQ_FIX3L).

---

## Agent a75f06474763b3fa8 — 2026-11-01 16:42

REPORT: pre-game engine (DQ4), repository not modified.

Deliverables
- /tmp/specs/moteur_avant_partie.md: complete specification (startup, menu, saves, new game, gaps, established/assumed).
- /tmp/specs/sonde_titre.py: reproducible probe (branches title, continue, resume, auto, new, delete, license, quit).
- /tmp/specs/dq4_sauvegarde.py: data*.dat analyzer.
- /tmp/specs/img/: viewer_*.png, tex_taptostart*, tex_Retro4_copyright*, tex_m8900/8901/8905.

Established conclusions
1. Title: two A presses, via the byte 0x10 as 2nd argument of GameUpdate (a MenuPort message is not enough). Between the two, a 30-frame fade, and a press during the fade-in is ignored. The 2nd press launches startGame, then part 3 and MaterielMenu_LOAD.
2. Root menu (port 13, type 53): values to send back `[1,v,0x10]`: 0 Continue, 1 Resume, 2 Create, 3 Delete, 4 Auto, 8 Cloud, 11 License. These are not the displayed line numbers. B sends `[0,999]` (Quit).
3. Saves: data1..5.dat are 15,360 bytes, data9.dat 512 bytes. The encryption is an xorshift32 XOR seeded by the CRC32 of "vb76Eg43". The layout and the checksum are decoded.
4. New game: name entered through a keyboard local to Unity, protocol `[2,len]` then packed UTF-8 bytes. Gender via `[1,0|1,A]`. makeDiary (0x194a50) writes the map mlb1a, saves as type 4 and calls startFirstTown. The game starts on mlb1a ("Prologue", message 200005, Yes/No), not on ev01 or mak1f1.
5. Deletion: killbank writes the DLED header. The text of the list is not refreshed before it is reopened.

Gaps in window.py, by priority
1. Name and gender entry (type 55): nothing is displayed.
2. License screen (type 80): blocking black screen.
3. Title logos (packet 22) and Tap to start.
4. Port 0 messages ignored: [0,999], [0,6], volumes [0,4/5], [0,7], [0,8].
5. Cloud (value 8, types 75-79).
6. Not verified: grayed cells, mouse click on the title, prologue of a new game.

Unknowns (assumed)
- The message code that Unity actually uses for the name. Code 2 is accepted, any code other than 1 and 3 will do.
- The conversion of a click into an A press by TitleTouch.
- The InputName keyboard (layout, maximum length, Katakana/Hiragana).
- The difference between SAVETYPE 1 and 2, and the effects of g_isAmazon beyond the cloud.
- The prologue after the Yes/No, and the input that ends the License screen.

To remember (source: this investigation, disassembly and probe)
- Encryption and format of the saves (see point 3).
- Name protocol and root cell values.
- The new game starts on mlb1a.
- The project notes wrongly say that type 73 is "unused": it is the Tap to start local to Unity.

Traps: TextAPI::getMessage hangs under emulation (use extractText or msg_find). The save folder must be writable.

---
