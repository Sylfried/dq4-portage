# Scripts de recherche et de mesure (archives de session)

Scripts écrits pendant la session du 31/10 au 02/11/2026 (audit, enquêtes sur le moteur, mesures des agents). **Non maintenus** : chemins `/tmp/...` et `/home/claude/...` codés en dur (cloud de session), worktrees `wt45-*` disparus ; ils supposent le dump IL2CPP (`outils/dump_il2cpp.bat`) et les APK de l'utilisateur. À copier et adapter, pas à lancer tels quels.

- `audit/` : balayage des 529 cartes par le moteur seul (`balayage.py`, `hl.py`), graphe d'appels, audit de la saisie tactile (`audit_*`).
- `moteur/` : désassemblage et sondes du moteur (`desasm_moteur.py`, `dasm_core.py`), lecture de journaux, rendus hors écran de fenêtres (`rend_*.py`), harnais.
- `chargement/`, `sprites/`, `combat/`, `texte/`, `camera/`, `decor/`, `ui/`, `son/` : harnais de mesure des agents du lot #45.
- Les scripts de travail de la session (tests, PR) sont dans `outils/flux_session/`.
