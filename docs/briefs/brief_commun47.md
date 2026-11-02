# Brief commun — lot « oublis du rapport » (PR #47)

## Le projet
Portage PC 16:9 de Dragon Quest IV (APK Android patché FR). Le moteur d'origine `libdq4core.so` tourne tel quel sous Unicorn ; la couche Unity (C#) est refaite dans une visionneuse pyglet (`dq4_pc/fenetre.py`, `moteur.py`, `ui_menu.py`, `pause.py`, `son.py`, `reglages.py`, `postfx.py`, `objets_carte.py`, `fbx.py`, `entrees.py`...). Utilisateur : Sylfried, francophone, « vibecoder » (il teste sur son PC Windows, veut des outils clé en main). Réponses courtes et honnêtes : **toujours dire ce qui est établi (lu dans le code / observé), supposé, non vérifié**.

Base = `main` à **b2899f4** (PR #46, 02/11/2026) + ce brief (branche `lot47`). Lis d'abord, dans ton worktree : `docs/reprise.md` (règles et carte du dépôt), puis **seulement la section utile** de `docs/notes-visionneuse-dq4-pc.md` (surtout « Avance #44 » et « Avance #45 », à la fin) et de `docs/notes-technique-portage-dq4.md` (« Avance #45 : faits techniques »). Ne charge pas ces fichiers en entier (~340 Ko). Les références G-xxx, D-xx, PAQ-x, CAR-x, SRV-x, CAS-x renvoient à `docs/audit/{lacunes_connues,decisions,couverture}.md` (fais un `grep -n` sur la référence). Le rapport d'ensemble est `docs/audit/rapport_reste_a_faire.md`.

## Ce lot
Sylfried n'a pas donné de retours de test cette fois : on traite des **oublis** de la liste du rapport (« Oublis de Claude »). Chaque agent en traite un sous-ensemble (ta mission). Aucune capture de référence du mobile n'existe : le jeu d'origine se lit dans le **code** (dump IL2CPP, moteur).

## Environnement (cloud, 2 cœurs, 7 Go : plusieurs agents en même temps)
- **Pas de xvfb** : `PYGLET_HEADLESS=1` (EGL/Mesa). Importer pyglet sans écran exige `pyglet.options['shadow_window']=False`.
- Variables : `export PYGLET_HEADLESS=1 PYGLET_AUDIO=silent DQ_APK=/mnt/user-data/uploads/dq4-portage/jeux/DQ4/patched_apks DQ_SAVES=/mnt/user-data/uploads/dq4-portage/jeux/DQ4/saves/20261007_190735 DQ_CACHE_CARTES=/tmp/cache47_NOM` (NOM = ton nom de chantier : **un cache à toi**, pas de partage avec les autres agents).
- **Sauvegardes** : `DQ_SAVES` ci-dessus = la copie **d'origine du mobile** (lecture seule), celle que les tests attendent (emplacement 1 : Ragnar à Strattbourg, Doc, etc.). **N'utilise pas** `/mnt/user-data/uploads/dq4-portage/dq4_pc/sauvegardes` : Sylfried l'a rejouée depuis (les tests de magie et d'historique de combat y échouent). Le moteur écrit dans un dossier temporaire (`/tmp/sv_NOM`), jamais dans les sauvegardes.
- **Dump IL2CPP (lecture seule)** : `/home/claude/il2/dump.cs`, `script.json`, `stringliteral.json` (pas de `il2cpp.h`). Il sert à lire les classes Unity, jamais à être commité ni cité en entier dans le dépôt.
- **Tests** : toujours depuis la racine de ton worktree, **en script** : `python3 -W ignore outils/test_X.py` (jamais `-m unittest outils.X`). Certains acceptent `--apk --saves`, d'autres non ; avec les variables d'environnement ci-dessus, la plupart se passent d'arguments. Lance seulement les tests de ton périmètre (la suite complète prend ~7 min sur 2 cœurs partagés : je la lance sur l'arbre fusionné). Ajoute les tiens (`outils/test_<sujet>.py`).
- **Visionneuse en capture** : `cd dq4_pc && python3 fenetre.py --apk "$DQ_APK" --saves-lecture "$DQ_SAVES" --saves-ecriture /tmp/sv_NOM --reglages /tmp/rg_NOM.json --slot 1 --cache /tmp/uicache47_NOM --msaa 0 --largeur 1280 --hauteur 720 --sans-preparation --sans-son --shot /tmp/m_NOM.png --images 100000 --touches-test "" --shots-boucle "150,330"` (captures séparées par des **virgules**, fichiers `/tmp/m_NOM_b<image>.png` à lire avec l'outil Read). `--slot 1` = journal 1 (Ragnar à Strattbourg), `0` = logos + titre + menu de départ. Harnais de touches (`--touches-test "image:TOUCHE,image:@x@y,image:\$texte"`, `!x!y`, `^x^y`, `~@x@y`, `+TOUCHE`/`-TOUCHE`) : voir `fenetre.py`. Un fichier de réglages inexistant = valeurs par défaut. Débogage : `DQ_MENUDBG`, `DQ_UIDBG`, `DQ_SAVEDBG`, `DQ_PKTALL=<fichier>`, `DQ_APPEL`, `DQ_CARTE_DEPL`, `DQ_SUIVI`.
- `python3 -m pyflakes` sur les fichiers modifiés avant de committer (avertissements connus : `sel`, `racine`, `em`, `ax`, `struct`, `unicorn`, `io`, `R`, `yp`, `mh`, `soundfile`, `SourceBoucle`).
- Les chantiers durent plus longtemps que les tests : prévois des runs ciblés ; quelques centaines d'images moteur prennent plusieurs minutes.

## Règles de travail (impératives)
1. Tu travailles **uniquement dans ton worktree** (`/home/claude/wt47-NOM`, branche `agent47-NOM`). **Ne touche pas** à `/home/claude/dq4-portage` ni aux autres worktrees, ne fais **aucun** `git push`, ne change pas de branche, ne crée pas de PR. Commits sur ta branche, **un commit par point**, avec ce pied de message (deux lignes séparées, après une ligne vide) :
   `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`
   `Claude-Session: https://claude.ai/code/session_014GF7TWaZ7HKpoCu5KRp2TJ`
2. **Ne touche jamais** aux fichiers du patch FR (APK patchés, `*.mpt`, Excel, `DQ_Patch_FR.exe`) ni aux vraies sauvegardes.
3. **Aucun contenu Square Enix dans le dépôt** : pas de dump, pas de capture du jeu, pas de texte du jeu recopié en bloc, pas de fichier extrait des APK. Les captures restent dans `/tmp`. `.gitignore` strict : jamais `git add -f`.
4. **Le jeu d'origine fait foi** : ce que la visionneuse remplace doit coller au comportement mobile, sauf demande contraire de Sylfried. Le moteur ne se modifie pas (le fichier reste intact ; seulement des crochets ciblés en mémoire, déjà listés dans les notes).
5. **Un bug découvert dans une situation précise se corrige globalement** (cause racine, tous les endroits concernés).
6. **Quand le jeu impose une valeur par script, elle l'emporte sur les réglages du joueur.**
7. **Pas de fichier non demandé.** Tout nouveau réglage : valeur par défaut + bouton ↺ (`pause._choix(defaut=...)`) + clé dans `reglages.py` + migration si un défaut change (un `reglages.json` existant ne doit pas garder l'ancien défaut gelé).
8. **Pas de gros refactor** : une correction est petite, localisée, ne change pas ce qui marche (PR #43 à #45 à jour : ne défais rien).
9. Reste dans ton **périmètre de fichiers**. Zones **partagées** entre agents : `moteur.py` (`Etat.appliquer`, `__setstate__`, `Moteur.step`), `fenetre.py`, `pause.py`, `ui_menu.py`. Si tu dois y toucher, fais des **hunks courts et isolés** et signale-les dans ton rapport (les conflits de fusion sont là).
10. **Ne mets pas de documentation dans `docs/`** (sauf mission « docs ») : inclus dans ton rapport les notes à fusionner (texte prêt à coller, en français).
11. Tu n'as pas de Windows ni de vrai GPU : tout ce qui en dépend est codé défensivement (repli propre à toute erreur) et listé en « non vérifié ». Si un point est trop gros ou trop incertain, **documente-le avec une estimation au lieu de bricoler** : ne conclus jamais « fait » sans preuve (test, capture, ligne de code).
12. Avant le rapport : `git status` (arbre propre), `git log --oneline main..HEAD`.

## Format du rapport final (ton dernier message), court et en français
1. **Par point de ta mission** : fait / partiel / pas fait, avec preuve (test, capture `/tmp/...`, ligne de code), **Établi / Supposé / Non vérifié**.
2. **Commits** : liste.
3. **Notes à fusionner dans `docs/`** (texte prêt à coller).
4. **Fichiers touchés hors périmètre** et pièges pour la fusion.
5. **Ce que tu n'as pas pu vérifier.**
6. **À trancher par Sylfried** (si un point demande son avis, une phrase par question, avec ta recommandation).
