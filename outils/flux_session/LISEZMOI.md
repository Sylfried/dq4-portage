# Scripts de flux de la session (cloud)

- `pr.sh "titre" corps.md` : pousse la branche courante, ouvre la PR « Avance #N : titre » (N = plus grand numéro d'issue ou de PR existant + 1 : issues et PR partagent la même numérotation), la fusionne en squash par l'API REST (`gh api` ; GraphQL est bloqué en session cloud), revient sur `main` et fait `git pull`. Chemin du dépôt codé : `/home/claude/dq4-portage`.
- `lancer_tests.sh` : lance tous les `outils/test_*.py` **sans écran virtuel** (`PYGLET_HEADLESS=1`), avec `--apk` / `--saves` quand le test les accepte (sinon sans arguments) ; une ligne par fichier, `FIN` à la fin. À adapter : `DQ_APK`, `DQ_SAVES`, `DQ_CACHE_CARTES`.
- `run_wt.sh WORKTREE NOM "touches" "captures" [slot]` : visionneuse sous `xvfb-run` (verrou `/tmp/xvfb.lock`) pour une scène scriptée et des captures `/tmp/m_NOM_b<image>.png`. En headless : `PYGLET_HEADLESS=1 python3 fenetre.py ...` directement (sans verrou).
- `moteur_slot.sh commande [args...]` : au plus 2 exécutions du vrai moteur / de la visionneuse en même temps (créneaux `flock` sur `/tmp/moteur_slot_{1,2}.lock`) ; la commande attend son tour. Utile quand plusieurs sous-agents tournent sur 2 cœurs et 7 Go.
