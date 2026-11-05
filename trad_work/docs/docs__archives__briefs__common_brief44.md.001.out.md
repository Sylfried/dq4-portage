# Common brief — agents of part 2 of the « giga complet » (EN: "giga complete") audit (PR #44)

## The project
16:9 PC port of Dragon Quest IV (French-patched Android APK). The original engine `libdq4core.so` runs unmodified under Unicorn; the Unity C# layer is rebuilt in a pyglet viewer (`dq4_pc/window.py`, `engine.py`, `ui_menu.py`, `pause.py`, `sound.py`, `settings.py`, `postfx.py`, `flat_sceneries.py`, `fbx.py`...). User: Sylfried, French-speaking, "vibecoder" (he wants turnkey tools, he tests on his Windows PC). Short, honest answers: **always say what is established (read in the code / observed), assumed, not verified**.

Read first: `docs/viewer-notes-dq4-pc.md` (especially the end: "Feedback of 23:24 … (#42)", "Feedback of 20:46 … (#41)"), `docs/technical-notes-dq4-port.md` (in your worktree), `docs/workflow.md`, and if needed `/tmp/specs/unity_avant_partie.md`, `/tmp/specs/prologue.md`, `/tmp/specs/camera_bip.md`, `/tmp/specs/moteur_avant_partie.md` (if present). IL2CPP dump: `/home/claude/il2/dump.cs` (+ `script.json`, `libil2cpp.so`, tools `/home/claude/il2/*.py` and `/tmp/specs/*.py`) — **read-only**.


Base = `main` at **ab22007** (PR #43 merged, 2026-11-02). Read first `docs/viewer-notes-dq4-pc.md` (especially the "Feedback of 02:12 … (#43)" section at the end) and `docs/technical-notes-dq4-port.md` in your worktree.

## The context of this mission
Sylfried asked (Monday 02:12) for a **« giga complet » (EN: "giga complete") audit** of what remains: « issues GitHub, fonctionnalités jamais discutées (casino, églises, banque…), menus, interrupteurs, variables, placement des PNJ, scripts » (EN: "GitHub issues, features never discussed (casino, churches, bank…), menus, switches, variables, NPC placement, scripts"), with a **final report** that classifies each gap or discrepancy into three categories: **(a) Sylfried's decision** (he asked for it or approved it), **(b) Claude's oversight** (should have been done or checked), **(c) bug**. Part 1 (read-only) done: `/tmp/audit/couverture.md` (**read §1, §3, §4, §6**), `/tmp/audit/lacunes_connues.md` (G-xxx), `/tmp/audit/decisions.md` (D-xx), `/tmp/audit/github_issues.md`. The tools and screenshots of part 1 are in `/tmp/audit/` (probes `probe_*.py`, `hl.py`, `sweep.py`, `gl_casino.py`, logs `gl_out_*.txt`). Part 2 = **your mission**: investigate further **and fix what is simple and safe** (the fixes will be merged into PR #44); what is big or uncertain is only documented with an estimate.

## Final report format (SubagentHandback), short and in French
1. **Findings**: table `ID (ton préfixe + n°) | quoi | preuve | Établi / Supposé / Non vérifié | classe (décision / oubli / bug) | corrigé ? (commit) | sinon : effort estimé`.
2. **Fixes**: list per commit.
3. **Notes to merge into `docs/`** (ready-to-paste text).
4. **What you could not verify** (Windows, real GPU, unreachable chapter, etc.).
Never conclude "present" or "absent" without proof (screenshot, trace, line of code). If you cannot reach a feature in the test engine (no save at the right chapter), say so and propose the shortest path to test it.

## Working rules (mandatory)
1. You work **only in your worktree** (given in your mission), on its branch `agent-xxx`. **Do not touch** `/home/claude/dq4-portage` (main repository), make **no** `git push`, do not switch branches, do not create a PR. Commits on your branch, with this message footer (two separate lines):
   `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`
   `Claude-Session: https://claude.ai/code/session_014GF7TUJhoy5Df7FLvSTYtw`
2. **Never touch** the French patch files (patched APKs, `*.mpt`...) nor the user's saves (`/mnt/user-data/uploads/dq4-portage/dq4_pc/sauvegardes` = copy of HIS real files, **read-only**; tests write to `/tmp/sv_NOM`).
3. Only one xvfb at a time on the machine (2 cores, several agents): **always** run tests via `/tmp/run_wt.sh` (lock `flock /tmp/xvfb.lock` included, other jobs wait). Usage:
   `/tmp/run_wt.sh /home/claude/wt-XXX NOM "image:TOUCHE,image:@x@y,image:\$texte" "image1,image2,..." [slot] [args window.py...]`
   → screenshots `/tmp/m_NOM_b<image>.png` (the frame list is separated by **commas**), log `/tmp/out_NOM.txt`. Click: `image:@x@y` (pixels from the top-left of a 1280 x 720 window). Keys = pyglet names (`RETURN`, `ESCAPE`, `LEFT`...). Extended harness: `!x!y` (press), `^x^y` (drag), `~@x@y` (move), `+TOUCHE` / `-TOUCHE` (held key). Test settings: `RG=/tmp/rg_NOM.json` (**make your own copy**: start from `/tmp/rg_i42.json` = clean default settings; **do not use** `/tmp/rg.json`, polluted by an `angle_camera`). Interface cache: `CACHE=/tmp/uicache4` (default; if you change the resource extraction, take your own cache). Read the screenshots with the Read tool (images). Debugging: environment variables `DQ_MENUDBG`, `DQ_UIDBG`, `DQ_SAVEDBG`, `DQ_PKTALL=<fichier>`, `DQ_APPEL`, `DQ_CARTE_DEPL`... A few hundred engine frames take several minutes: plan targeted runs. Slots: `0` = logos + title + start menu; `1` = adventure log 1 (Ragnar at Strattbourg, `mak1f1`); `2` = adventure log 2 (beginning, prologue / Sofiâ at Bastione depending on the save folder).
4. The original engine is not modified. What the viewer replaces (Unity layer) must **match the original mobile behavior** ("the original game is the reference") unless the user says otherwise.
5. Stay within your file scope (given in your mission) to limit merge conflicts; if you must touch other files, change the minimum (a few lines) and flag it in your report. `python3 -m pyflakes` on the modified files before committing (the existing warnings `selected`, `root`, `em`, `ax`, `struct`, `unicorn`, `io`, `R`, `yp`, `mh`, `soundfile`, `LoopSource` are known). Existing unit tests in `tools/test_*.py`: run those that touch your scope (`xvfb-run -a -s "-screen 0 800x600x24" python3 tools/<test>.py`, or via the lock: `flock /tmp/xvfb.lock xvfb-run ...`) and add your own.
6. ** Generalization**: the user confirmed that a bug described from a specific situation must be fixed **globally**, not only for the described case. Look for the root cause and all the places concerned.
7. Do not put any documentation in `docs/` yourself: **include in your final report** the notes to add (I merge them).
8. Final report (short, in French) **delivered with the SubagentHandback tool**: what is done (per point), commits, **Established / Assumed / Not verified**, files touched, useful screenshots (absolute paths `/tmp/...`), merge pitfalls. Do not leave your working tree dirty.
9. You have no Windows: what you cannot test (real GPU, real full screen, physical mouse...) must be coded defensively (clean fallback on any error) and listed as "not verified".


## Useful technical context (learned in previous batches)
- MenuPort engine↔Unity protocol: `[N,1,cat,type]` opens, `[N,2]` closes, `[N,3,vis]`; Unity→engine return `Engine.send_menu(port, buttonId, pad)` (A=16, B=32, ◀8 ▶4, ▲2, ▼1). Start menu = type 53; shops 57–63; casino 44–48; arena 49–51, 68, 71; church 66–67; bank 57/64/65 (see `/tmp/audit/couverture.md` §2).
- Engine parts known to the viewer: 3 (town), 0xc (town), 0xd (battle), 0xe (world map); **0xf (casino) and 0x10 (bestiary) are missing** (`engine.py:8-11`); drawing guard for dynamic meshes at `window.py` (`e.part == ENGINE.PART_TOWN`).
- Engine alone without a window: `/tmp/audit/hl.py`, `Engine` (Unicorn); saves in `/mnt/user-data/uploads/dq4-portage/dq4_pc/sauvegardes` (read-only; copy to `/tmp/sv_NOM` to write).
- Camera: `Game._camera_menee`, `cam_jeu`, `angle_camera`; sprites: `Game._town_panel`; `State.apply` (`engine.py` ~97-196) decodes the packets; `State.sprites[8 + placement]`.
- Interface editor / Pause: `pause.py`, `settings.py`; game priority: `game_priority.py`; battle speed: `battle_speed.py`; history: `history.py`, `ui_history.py`, `libelles.py`; inputs: `inputs.py`.
- Existing tests: `tools/test_*.py` (unit, some under xvfb). Run those that touch your scope, add your own.

## Additional rules for part 2
- **No big refactor**: a fix must be small, localized, and must not change what works (the 16 points of PR #43 are up to date: do not undo them).
- Each fix has its own separate **commit** and a test or a before / after screenshot.
- The dynamic meshes, parts 0xf / 0x10, `_menu_input` and `State.apply` are **shared** zones among the agents of this part: change the strict minimum, flag everything you touch outside your scope.
