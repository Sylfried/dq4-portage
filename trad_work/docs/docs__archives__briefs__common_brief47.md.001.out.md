# Common brief — "report oversights" batch (PR #47)

## The project
16:9 PC port of Dragon Quest IV (French-patched Android APK). The original engine `libdq4core.so` runs unmodified under Unicorn; the Unity layer (C#) is rebuilt in a pyglet viewer (`dq4_pc/window.py`, `engine.py`, `ui_menu.py`, `pause.py`, `sound.py`, `settings.py`, `postfx.py`, `map_objects.py`, `fbx.py`, `inputs.py`...). User: Sylfried, French-speaking, "vibecoder" (he tests on his Windows PC, wants turnkey tools). Short, honest answers: **always say what is established (read in the code / observed), assumed, not verified**.

Base = `main` at **b2899f4** (PR #46, 2026-11-02) + this brief (branch `lot47`). Read first, in your worktree: `docs/resume.md` (rules and repository map), then **only the useful section** of `docs/viewer-notes-dq4-pc.md` (especially "Avance #44" and "Avance #45", at the end) and of `docs/technical-notes-dq4-port.md` ("Avance #45: technical facts"). Do not load these files in full (~340 KB). The references G-xxx, D-xx, PAQ-x, CAR-x, SRV-x, CAS-x point to `docs/audit/{known_gaps,decisions,coverage}.md` (run a `grep -n` on the reference). The overall report is `docs/audit/remaining_work_report.md`.

## This batch
Sylfried sent (Monday 22:29) a list of feedback items (he checked some points on his mobile): **this batch, "22:29 feedback", is handled first**; the batch of the audit report oversights is paused (branch `agent47-docs`, not merged). Each agent handles a subset (your mission, with his exact words). Sylfried's screenshots (read them with the Read tool) in `/tmp/specs47/`: `ecran1_pause_cases_rouges.png` (Pause menu: "Écran du plein écran" and "Résolution" lines with red text under the value), `ecran2_titre_decentre.png` (PC title screen: logo and scenery that seem shifted to the left), `ecran3_combat_commandes_bouton_vitesse.png` (battle: commands frame, speed button under the frame on the left, "retour" button on the right). No mobile screenshot exists: the original game is read in the **code** (IL2CPP dump, engine). When an instruction is ambiguous: choose the simplest interpretation and **say which one** in your report.

**Engine slots**: 2 cores and 7 GB for about ten agents. Any execution that loads the real engine (tests with `DQ_APK`, viewer, `window.py`) is launched **via** `tools/session_flow/engine_slot.sh` (at most 2 at the same time; it waits for its turn): `/home/claude/wt47-NOM/tools/session_flow/engine_slot.sh python3 -W ignore tools/test_X.py`. Purely unit-level tests (without the engine) do not need it. Keep each execution short and targeted.

## Environment (cloud, 2 cores, 7 GB: several agents at the same time)
- **No xvfb**: `PYGLET_HEADLESS=1` (EGL/Mesa). Importing pyglet without a screen requires `pyglet.options['shadow_window']=False`.
- Variables: `export PYGLET_HEADLESS=1 PYGLET_AUDIO=silent DQ_APK=/mnt/user-data/uploads/dq4-portage/jeux/DQ4/patched_apks DQ_SAVES=/mnt/user-data/uploads/dq4-portage/jeux/DQ4/saves/20261007_190735 DQ_CACHE_CARTES=/tmp/cache47_NOM` (NOM = your task name: **a cache of your own**, not shared with the other agents).
- **Saves**: `DQ_SAVES` above = the **original mobile copy** (read-only), the one the tests expect (slot 1: Ragnar at Strattbourg, Doc, etc.). **Do not use** `/mnt/user-data/uploads/dq4-portage/dq4_pc/sauvegardes`: Sylfried has replayed it since (the magic and battle history tests fail there). The engine writes to a temporary folder (`/tmp/sv_NOM`), never to the saves.
- **IL2CPP dump (read-only)**: `/home/claude/il2/dump.cs`, `script.json`, `stringliteral.json` (no `il2cpp.h`). It is used to read the Unity classes, never to be committed nor quoted in full in the repository.
- **Tests**: always from the root of your worktree, **as a script**: `python3 -W ignore tools/test_X.py` (never `-m unittest tools.X`). Some accept `--apk --saves`, others do not; with the environment variables above, most need no arguments. Run only the tests of your scope (the full suite takes ~7 min on 2 shared cores: I run it on the merged tree). Add your own (`tools/test_<sujet>.py`).
- **Viewer in capture mode**: `cd dq4_pc && python3 window.py --apk "$DQ_APK" --saves-lecture "$DQ_SAVES" --saves-ecriture /tmp/sv_NOM --reglages /tmp/rg_NOM.json --slot 1 --cache /tmp/uicache47_NOM --msaa 0 --largeur 1280 --hauteur 720 --sans-preparation --sans-son --shot /tmp/m_NOM.png --images 100000 --touches-test "" --shots-boucle "150,330"` (screenshots separated by **commas**, files `/tmp/m_NOM_b<image>.png` to read with the Read tool). `--slot 1` = adventure log 1 (Ragnar at Strattbourg), `0` = logos + title + start menu. Key harness (`--touches-test "image:TOUCHE,image:@x@y,image:\$texte"`, `!x!y`, `^x^y`, `~@x@y`, `+TOUCHE`/`-TOUCHE`): see `window.py`. A nonexistent settings file = default values. Debugging: `DQ_MENUDBG`, `DQ_UIDBG`, `DQ_SAVEDBG`, `DQ_PKTALL=<fichier>`, `DQ_APPEL`, `DQ_CARTE_DEPL`, `DQ_SUIVI`.
- `python3 -m pyflakes` on the modified files before committing (known warnings: `selected`, `root`, `em`, `ax`, `struct`, `unicorn`, `io`, `R`, `yp`, `mh`, `soundfile`, `LoopSource`).
- The tasks take longer than the tests: plan targeted runs; a few hundred engine frames take several minutes.

## Working rules (mandatory)
1. You work **only in your worktree** (`/home/claude/wt47-NOM`, branch `agent47-NOM`). **Do not touch** `/home/claude/dq4-portage` nor the other worktrees, make **no** `git push`, do not switch branches, do not create a PR. Commits on your branch, **one commit per point**, with this message footer (two separate lines, after a blank line):
   `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`
   `Claude-Session: https://claude.ai/code/session_014GF7TWaZ7HKpoCu5KRp2TJ`
2. **Never touch** the French patch files (patched APKs, `*.mpt`, Excel, `DQ_Patch_FR.exe`) nor the real saves.
3. **No Square Enix content in the repository**: no dump, no game screenshot, no game text copied in bulk, no file extracted from the APKs. Screenshots stay in `/tmp`. Strict `.gitignore`: never `git add -f`.
4. **The original game is the reference**: what the viewer replaces must match the mobile behavior, unless Sylfried requests otherwise. The engine is not modified (the file stays intact; only targeted in-memory hooks, already listed in the notes).
5. **A bug discovered in a specific situation is fixed globally** (root cause, all the places concerned).
6. **When the game imposes a value by script, it takes precedence over the player's settings.**
7. **No unrequested file.** Any new setting: default value + ↺ button (`pause._choice(default=...)`) + key in `settings.py` + migration if a default changes (an existing `settings.json` must not keep the old default frozen).
8. **No big refactor**: a fix is small, localized, does not change what works (PRs #43 to #45 are up to date: do not undo anything).
9. Stay within your **file scope**. **Shared** zones among agents: `engine.py` (`State.apply`, `__setstate__`, `Engine.step`), `window.py`, `pause.py`, `ui_menu.py`. If you must touch them, make **short, isolated hunks** and flag them in your report (the merge conflicts are there).
10. **Do not put documentation in `docs/`** (except for a "docs" mission): include in your report the notes to merge (ready-to-paste text, in French).
11. You have no Windows and no real GPU: anything that depends on them is coded defensively (clean fallback on any error) and listed as "not verified". If a point is too big or too uncertain, **document it with an estimate instead of improvising**: never conclude "done" without proof (test, screenshot, line of code).
12. Before the report: `git status` (clean tree), `git log --oneline main..HEAD`.

## Final report format (your last message), short and in French
1. **Per point of your mission**: done / partial / not done, with proof (test, screenshot `/tmp/...`, line of code), **Established / Assumed / Not verified**.
2. **Commits**: list.
3. **Notes to merge into `docs/`** (ready-to-paste text).
4. **Files touched outside your scope** and merge pitfalls.
5. **What you could not verify.**
6. **To be decided by Sylfried** (if a point needs his opinion, one sentence per question, with your recommendation).
