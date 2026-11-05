# Scripts de recherche et de mesure (archives de session)

Scripts écrits pendant la session du 31/10 au 02/11/2026 (audit, enquêtes sur le moteur, mesures des agents). **Non maintenus** : chemins `/tmp/...` et `/home/claude/...` codés en dur (cloud de session), worktrees `wt45-*` disparus ; ils supposent le dump IL2CPP (`tools/dump_il2cpp.bat`) et les APK de l'utilisateur. À copier et adapter, pas à lancer tels quels.

- `audit/` : balayage des 529 cartes par le moteur seul (`sweep.py`, `hl.py`), graphe d'appels, audit de la saisie tactile (`audit_*`).
- `engine/` : désassemblage et sondes du moteur (`disasm_engine.py`, `dasm_core.py`), lecture de journaux, rendus hors écran de fenêtres (`render_*.py`), harnais.
- `loading/`, `sprites/`, `battle/`, `text/`, `camera/`, `scenery/`, `ui/`, `sound/` : harnais de mesure des agents du lot #45.
- Les scripts de travail de la session (tests, PR) sont dans `tools/session_flow/`.
