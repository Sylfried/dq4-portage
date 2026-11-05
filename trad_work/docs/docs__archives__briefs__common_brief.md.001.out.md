# Common brief — agents of the "20:46 feedback" batch (PR #41)

## The project
16:9 PC port of Dragon Quest IV (French-patched Android APK). The original engine `libdq4core.so` runs unmodified under Unicorn; the Unity C# layer is rebuilt in a pyglet viewer (`dq4_pc/window.py`, `engine.py`, `ui_menu.py`, `pause.py`, `sound.py`, `settings.py`...). User: Sylfried, French-speaking, "vibecoder" (he wants turnkey tools, he tests on his Windows PC). Answers must be short and honest: **always say what is established (read in the code / observed), assumed, not verified**.

Read first: `docs/viewer-notes-dq4-pc.md`, `docs/technical-notes-dq4-port.md` (in your worktree), and if needed `/tmp/specs/unity_avant_partie.md` (specification of the Unity layer, UI conventions: portrait 450 x 800, XZ plane...). IL2CPP dump: `/home/claude/il2/dump.cs` (+ `script.json`, `libil2cpp.so`, tools `/home/claude/il2/*.py` and `/tmp/specs/scripts`, `/tmp/specs/*.py`) — **read-only**.

## Working rules (mandatory)
1. You work **only in your worktree** (given in your mission), on its branch `agent-xxx`. **Do not touch** `/home/claude/dq4-portage` (it is the main repository), make **no** `git push`, do not switch branches, do not create a PR. Commits on your branch, with this message footer:
   `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>` then `Claude-Session: https://claude.ai/code/session_014GF7TUJhoy5Df7FLvSTYtw` (two separate lines).
2. **Never touch** the French patch files (patched APKs, `*.mpt`...) nor the user's saves (`/mnt/user-data/uploads/dq4-portage/dq4_pc/sauvegardes` = copy of HIS real files, **read-only**; tests write to `/tmp/sv_NOM`).
3. Only one xvfb at a time on the machine (2 cores, several agents): **always** run tests via `/tmp/run_wt.sh` (lock `flock /tmp/xvfb.lock` included, other jobs wait). Usage:
   `/tmp/run_wt.sh /home/claude/wt-XXX NOM "image:TOUCHE,image:@x@y,image:\$texte" "images à capturer" [slot] [args window.py...]`
   → screenshots `/tmp/m_NOM_b<image>.png`, log `/tmp/out_NOM.txt`. Click: `image:@x@y` (pixels from the top-left of a 1280 x 720 window). Keys = pyglet names (`RETURN`, `ESCAPE`, `LEFT`...). Test settings: `/tmp/rg.json` (make your own copy if you modify them: `RG=/tmp/rg_NOM.json /tmp/run_wt.sh ...`). Interface cache: `CACHE=/tmp/uicache4` (default). Read the screenshots with the Read tool (images). Debugging: environment variables `DQ_MENUDBG`, `DQ_UIDBG`, `DQ_SAVEDBG`, `DQ_PKTALL=<fichier>`. A few hundred engine frames take several minutes: plan targeted runs, no useless runs. Slot `0` = "Continuer" of the first adventure log.
4. The original engine is not modified. What the viewer replaces (Unity layer) must **match the original mobile behavior** ("the original game is the reference") unless the user says otherwise.
5. Stay within your file scope (given in your mission) to limit merge conflicts; if you must touch other files, change the minimum (a few lines) and report it in your report. `python3 -m pyflakes` on the modified files before committing (the existing warnings `selected`, `root`, `em`, `ax` are known).
6. Do not put any documentation in `docs/` yourself: **include in your final report** the notes to add (I merge them).
7. Final report (short, in French): what is done (per point), commits, **Established / Assumed / Not verified**, files touched, useful screenshots (absolute paths `/tmp/...`), merge pitfalls.

## The user's feedback (Sunday 20:46 message, useful excerpts)
See your mission. The user's screenshots are not available: rely on his words.
