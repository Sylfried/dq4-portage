# Scripts de flux de la session (cloud)

- `pr.sh "titre" corps.md` : pousse la branche courante, ouvre la PR « Avance #N : titre » (N = nombre de PR + 1), la fusionne en squash par l'API REST (`gh api` ; GraphQL est bloqué en session cloud), revient sur `main` et fait `git pull`. Chemin du dépôt codé : `/home/claude/dq4-portage`.
- `lancer_tests.sh` : lance tous les `outils/test_*.py` **sans écran virtuel** (`PYGLET_HEADLESS=1`), avec `--apk` / `--saves` quand le test les accepte (sinon sans arguments) ; une ligne par fichier, `FIN` à la fin. À adapter : `DQ_APK`, `DQ_SAVES`, `DQ_CACHE_CARTES`.
- `run_wt.sh WORKTREE NOM "touches" "captures" [slot]` : visionneuse sous `xvfb-run` (verrou `/tmp/xvfb.lock`) pour une scène scriptée et des captures `/tmp/m_NOM_b<image>.png`. En headless : `PYGLET_HEADLESS=1 python3 fenetre.py ...` directement (sans verrou).
