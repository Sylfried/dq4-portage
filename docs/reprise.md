# Reprise du travail dans une nouvelle conversation

Écrit le 02/11/2026 (fin de la session des lots #40 à #45). Objectif : qu'une nouvelle conversation reparte sans perdre un seul sujet en cours. **À lire en premier**, puis à ouvrir seulement ce dont la tâche a besoin (les gros fichiers de notes pèsent ~340 Ko : ne pas les charger en entier).

## 1. Le projet en cinq lignes
- Portage PC natif 16:9 de **Dragon Quest IV** (APK Android déjà patchés en français). Le moteur d'origine `libdq4core.so` tourne **tel quel** sous Unicorn ; la couche Unity (C#) est refaite en Python dans une visionneuse pyglet (`dq4_pc/*.py`).
- Dépôt : `Sylfried/dq4-portage` (**public**, donc aucune donnée perso, aucun contenu Square Enix, aucune capture du jeu, aucun dump). Les issues de l'ancien suivi sont dans `Sylfried/dq4-pc` (27 ouvertes) ; `dq4-portage` n'en a aucune (suivi par PR).
- Utilisateur : Sylfried, francophone, « vibecoder » : il teste sur son **PC Windows**, veut des outils clé en main, des réponses **courtes et honnêtes** (toujours « établi / supposé / non vérifié »). Souvent il délègue : décider, le dire.
- État au moment de l'écriture : `main` = **71fcd53** (« Avance #45 »), puis cette PR de reprise (#46). 39 fichiers de tests verts. **Rien n'est validé sous Windows ni sur un vrai GPU** (tout a tourné sous Mesa / llvmpipe).

## 2. Règles permanentes (de Sylfried)
1. **Le jeu d'origine fait foi** : tout ce que la visionneuse remplace doit coller au mobile, sauf demande contraire. Le moteur ne se modifie pas (seulement des crochets ciblés).
2. **Un bug découvert dans une situation précise se corrige globalement** (cause racine, tous les endroits concernés).
3. **Quand le jeu impose une valeur par script (ex. Nimzo dans DQ5), elle l'emporte sur les réglages du joueur** (déjà fait pour la caméra, à généraliser).
4. Ne **jamais** toucher aux fichiers du patch FR (APK patchés, `*.mpt`, Excel, `DQ_Patch_FR.exe`) ni aux **vraies sauvegardes** (copie en lecture seule ; les tests écrivent dans `/tmp/sv_*`).
5. **Ne jamais ouvrir ni modifier** `claude/piste-3-projet-unity.md` dans le Projet claude.ai.
6. Pas de fichier non demandé. Tout nouveau réglage : valeur par défaut + bouton ↺ (`pause._choix(defaut=...)`) + clé dans `reglages.py` + migration si le défaut change.
7. Aucun contenu Square Enix dans le dépôt (`.gitignore` strict, ne jamais `git add -f`). Ne pas commiter les dumps IL2CPP.

## 3. Où est quoi
| Quoi | Où |
|---|---|
| README (usage, touches, nouveautés) | `README.md` |
| État de la visionneuse, par avance (#25 → #47), « reste à faire », « Non vérifié » | `docs/notes-visionneuse-dq4-pc.md` (section **« Avance #47 »** à la fin ; en tête de section : « À trancher par Sylfried ») |
| Faits techniques moteur / protocole / chronologies | `docs/notes-technique-portage-dq4.md` (**« Avance #47 : faits techniques »**) |
| Manière de travailler (branches, issues) | `docs/workflow.md` (périmé : dit « pas de push direct sur main + issues » ; l'usage réel est le **suivi par PR**, à corriger, cf. décision 2 du rapport) |
| Rapport « Ce qu'il reste après l'audit » (18 décisions, 15 oublis, 11 bugs, 20 non vérifiés) | `docs/audit/rapport_reste_a_faire.md` (copie du Claude Doc https://claude.ai/artifact/5q6Cs8Br27SGqahx1AkvD4) |
| Audit détaillé : registre des décisions D-xx, lacunes G-xxx, couverture fonctionnelle, issues GitHub | `docs/audit/{decisions,lacunes_connues,couverture,github_issues}.md` |
| Spécifications d'audit (interface de combat, menus, avant-partie, caméra, prologue, texte) | `docs/audit/specs/` |
| Briefs donnés aux sous-agents (modèle à réutiliser : `brief_commun45.md`) | `docs/briefs/` |
| Rapports finaux des sous-agents (lots #40-#44 : 36 ; lot #45 : 10) | `docs/archives/` |
| Scripts de la session : PR, worktrees, tests | `outils/flux_session/` (voir `LISEZMOI.md`) |
| Scripts de recherche et de mesure (111, non maintenus, chemins codés en dur) | `outils/recherche/` (voir `LISEZMOI.md`) |
| Tests | `outils/test_*.py` (39 fichiers) |

## 4. Remettre l'environnement cloud en route
1. Attacher le dépôt avec push : outil `add_repo` (`Sylfried` / `dq4-portage`, accès `push`), cloner dans `/home/claude/dq4-portage`, `register_repo_root`. Ne pas tester le dépôt avec curl : appeler directement l'outil.
2. Fichiers du jeu (à demander à Sylfried si absents, **jamais commités**) : APK patchés (`.../jeux/DQ4/patched_apks`) et une **copie en lecture seule** de ses sauvegardes (`dq4_pc/sauvegardes`). Variables utilisées : `DQ_APK`, `DQ_SAVES`, `DQ_CACHE_CARTES=/tmp/cache44`, `PYGLET_AUDIO=silent`. Le dump IL2CPP (lecture du C# du jeu) se régénère avec `outils/dump_il2cpp.bat` / `generer_ui.bat` (côté Windows) ; il sert à lire les classes Unity, pas à être publié.
3. Python : `pip install --break-system-packages numpy pillow unicorn pyglet UnityPy capstone soundfile`. Plus besoin de xvfb : `PYGLET_HEADLESS=1` (EGL).
4. **Tests** : toujours depuis la racine du dépôt, en script : `PYGLET_HEADLESS=1 python3 outils/test_X.py` (jamais `-m unittest`, certains tests importent leurs voisins via le dossier du script). `outils/flux_session/lancer_tests.sh` lance toute la suite (une ligne par fichier, `FIN` à la fin). Certains tests acceptent `--apk --saves`, d'autres non (`test_casino_bestiaire`, `test_transition_combat`). Importer pyglet sans écran exige `pyglet.options['shadow_window']=False`.
5. **Lancer la visionneuse en capture** : `cd dq4_pc && PYGLET_HEADLESS=1 PYGLET_AUDIO=silent python3 fenetre.py --apk ... --saves-lecture ... --saves-ecriture /tmp/sv_X --reglages /tmp/rg_X.json --slot 1 --cache /tmp/uicache4 --msaa 0 --largeur 1280 --hauteur 720 --sans-preparation --sans-son --shot /tmp/m_X.png --images 100000 --touches-test "" --shots-boucle "150,330"` (captures séparées par des **virgules**). `--slot 1` = journal 1, `0` = logos + titre + menu de départ.

## 5. Flux PR (déroulé de la session)
- Branche par sujet depuis `main`. Gros lot : **sous-agents en parallèle**, un worktree `wt<N>-<nom>` et une branche `agent<N>-<nom>` chacun (brief = `docs/briefs/brief_commun45.md` + mission), fusion `--no-ff` dans une branche `lot<N>`, **suite complète de tests sur l'arbre fusionné** (les conflits de `moteur.py` / `fenetre.py` / `pause.py` sont la zone à risque : relire les `__setstate__` et `Moteur.step`), puis PR.
- PR numérotée **« Avance #N : titre »** par `outils/flux_session/pr.sh "titre" corps.md` (REST `gh api`, fusion squash ; **GraphQL est bloqué** en session cloud, donc pas de `gh issue list` ; utiliser `gh api repos/.../issues`). Le script revient sur `main` et fait le `pull`.
- Pieds de commit : `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>` puis `Claude-Session: https://claude.ai/code/session_...` (celui de la session en cours). Le hook d'arrêt exige commit + push de toute branche modifiée.
- Après chaque PR : sur le PC de Sylfried, `git pull --ff-only origin main` dans `$HOME/mnt/dq4-portage` (outil `device_bash`), puis resynchroniser les deux notes dans le Projet (`project_write` avec `local_path`, chemins `claude/notes-visionneuse-dq4-pc.md` et `claude/notes-technique-portage-dq4.md`).
- Corps de PR : court, en français, sections « Retours », « Tests », « À trancher », « Non vérifié ». Message final à Sylfried : très court.

## 6. Sujets ouverts (ce qui reste)
**A. Premier reste : validation Windows / vrai GPU** (MSAA, plein écran, multi-moniteurs, performance à x3/x4/x8, souris, lanceur `.bat`, boîtes de dialogue d'import / export). Rien d'autre ne le remplace ; la suite dépend de ses retours de test.

**B. Décisions en attente de Sylfried** (recommandation = ce qui sera fait sans réponse)
- 18 points du rapport (toits, suivi par PR, piste Unity #57, manette, DQ5 / DQ6, packaging `.exe`, shaders retirés, entrées retirées de l'éditeur, pixel perfect par défaut, curseur doré, clavier du nom, retour à l'écran titre, licence d'Unicorn…) : tableau complet dans `docs/audit/rapport_reste_a_faire.md`.
- Issues : sur 27 ouvertes dans `dq4-pc`, 7 peuvent être fermées (#2 sauf `IBase`, #5, #7 sauf coffres, #10, #22, #23, #41), 2 attendent confirmation (#40, #17), #6 et #57 sont des décisions. **Aucune n'a été fermée** (à faire avec un commentaire renvoyant à la PR).
- Issues de #45 (« À trancher ») : (1) section « Défilement du texte » : sous Vitesses dans Commandes (actuel) ou dans Affichage (ce qu'il avait écrit) ; (2) recentrage des textes : option dans Pause ou suppression (commit f756c63 ; `DQ_TEXTE_ORIGINAL=1` donne le placement exact du jeu) ; (3) soins à PV pleins : afficher le message du jeu « Mais rien ne se passe. » (demande un crochet moteur sur l'indicateur d'effet) ; (4) option de caméra d'escalier « ignorer la hauteur du héros » ; (5) correction du liseré des pierres / décalques au sol (« option A », bavure de couleur des bords alpha ; code de la proposition dans `outils/recherche/decor/`) ; (6) persistance du filtre Favoris ; (7) opacité du bouton de vitesse de combat.

**C. Oublis de Claude à faire** (liste du rapport, hors poses couchées déjà traitées) : animations d'événements FEAN (paquet 6, scènes d'histoire et bingo), échelle du terrain `field_scale` (paquet 30), effets d'écran 3 / 5 / 6, PNJ de scénario qui apparaissent / disparaissent, sauvegarde rapide de l'écran Divers au clavier, bruitage 300, animations FEMV et bateaux, icône de genre 18, son (table de volumes, fondus), fond de combat estimé et roulis de caméra de combat, autres modèles 3D, CI minimale (`.github/`), scripts de recherche à ranger (**fait dans cette PR**), documentation périmée.

**D. Bugs connus ou probables** (11) : bruitage de transition perdu à accélérateur élevé, `startTown` plante sur `za3f3` et `ev01` (pointeur nul dans `FldStage::getCameraLimitL`), allocateur de 256 Mo jamais libéré (`MemoryError` possible sur longue session), murs invisibles et escalier de `dbout`, monstre endormi qui pourrait s'effacer, survol de souris, `<ERR 3080@>` dans des dialogues de PNJ du casino, vagues d'eau sur le sol des grottes, angle de caméra sauvegardé, zoom minicarte à 400 %, blocage de 0,1 à 0,5 s au chargement d'une carte. Détail et références : tableau « Bugs connus » du rapport.

**E. Non vérifié** (20 points + liste « #45 ») : voir fin de `rapport_reste_a_faire.md` et « Non vérifié (#45) » dans les notes. Tout ce qui a été vu l'a été sous Linux. **Chapitres 2 et suivants jamais joués** (toutes les sauvegardes réelles sont au chapitre 1) : c'est le plus gros trou de couverture. Services à jouer pour de vrai : auberge par le PNJ, sorts du menu, divination, bénédiction, purification, radeau, henge, sifflet, Rura, bestiaire, boutiques types 28 / 59 / 63 / 70, banque au clavier (3 150 G), combats de boss / groupes / Morph / game over, retour au titre depuis un combat ou une boutique.

**F. Extensions plus lointaines** (dépendent des décisions) : DQ5 et DQ6 (issue #19), manette (#8), packaging `.exe` (#18), piste Unity (#57, en pause).

## 7. Démarrer la nouvelle conversation
1. Ouvrir le Projet « Dragon Quest 4-5-6 Android > PC » (ce document est son doc `claude/reprise-nouvelle-conversation.md`).
2. Premier message conseillé : « Reprends le projet DQ4 PC avec la note de reprise ; voici mes retours de test Windows : … » (ou, sans retours : « liste-moi les décisions en attente puis traite les oublis du rapport »).
3. Claude doit alors : cloner le dépôt (§4), lire `docs/reprise.md`, lire seulement la section utile des notes (§3), annoncer son plan en une phrase, lancer les sous-agents pour un gros lot (brief = `docs/briefs/brief_commun45.md`), tenir une liste de tâches et finir par le message court.
4. Garder en tête que la **consommation** d'une session longue est élevée : charger peu de documents, déléguer les gros lots, ne pas relire les notes complètes.
