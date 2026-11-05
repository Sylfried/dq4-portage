# Dragon Quest IV (Android) : caméra pilotée par le jeu, et « bip » à l'ouverture d'un message

Notes de recherche côté moteur (`libdq4core.so`, ARM64, sous Unicorn) et côté visionneuse (`dq4_pc/fenetre.py`), branche `camera-bip`
(worktree `/home/claude/wt-camera-bip`, issue de `main` d381c1d). Même style que `/tmp/specs/moteur_avant_partie.md`.

Conventions :
- adresses = vaddr de la lib ; à l'exécution on ajoute `LIB_BASE = 0x10000000` ;
- « **Établi** » = vérifié par une trace, une capture ou un désassemblage sans ambiguïté ;
  « **Supposé** » = déduit, non vérifié ; « **Inconnu** » = pas de donnée ;
- les choix qui sont les miens (pas ceux de l'original) sont marqués **[choix]**.

---

## 1. Résumé

1. **Caméra** (texte d'origine, branche `camera-bip` ; **mis à jour le 03/11/2026 : l'option a été supprimée en #47**, le centrage est toujours actif tant que le joueur a la caméra, voir §2.4) : l'option « Centrer la caméra sur le joueur » de la visionneuse (`reg['camera_centree']`) ne valait plus que lorsque le joueur
   avait la caméra. Le critère fiable est le **verrou de la `TownCamera` du moteur** (`+0x3e`), pas le drapeau « joueur verrouillé » (`Global.Flag` bit 0x4)
   ni la distance cible/héros (ancien critère : 60 unités, inopérant dans le prologue où la cible n'est qu'à 23 unités du héros).
2. **Bip** : le « bip » à l'ouverture d'un message est le **bruitage 300, commandé par le moteur** (paquet 35). C'est normal, c'est le même
   bruitage que celui du passage à la page suivante. Il est joué **une seule fois**, avec le bon fichier (`SE0300`) ; la visionneuse n'ajoute rien.
   Aucune modification n'a été nécessaire.

---

## 2. Caméra

### 2.1 L'objet `TownCamera` (moteur)

Objet statique, symbole exporté `_ZN10TownCamera11m_singletonE` (lu par `Moteur.camera_jeu()`, `dq4_pc/moteur.py`). Champs utilisés (**établi** par désassemblage de
`TownCamera::execute`, `setCameraLock`, `setMoveTo`, `setTargetPlayer`, `setMoveTragetChara`, `__cmd_camera_move_to_player::isEnd`, et par lecture mémoire en jeu) :

| offset | taille | rôle |
|---|---|---|
| `+0x34` | i32 | limite de rotation gauche (négative = rotation interdite dans ce lieu) — déjà lu par `camera_ville()` |
| `+0x38` | i32 | limite de rotation droite — idem |
| `+0x3e` | u8 | **verrou de la caméra** : 0 = la caméra suit le joueur (`setTarget(g_cmnPartyInfo)` dans `execute`) ; 1 = menée par le jeu |
| `+0x40` | u8 | verrou de point de vue (rotation) |
| `+0x43` | u8 | déplacement en cours (`setMoveTo`) |
| `+0x48` | i32 | mode de cible : 0 aucun, 1 à 4 déplacements, **5 = vise un personnage**, 6 = vise le joueur |

Le verrou est **posé** par : `setCameraLock(true)` (appelé par `cmd_map_event_camera::initialize`, `TownFallAction`, `TownActionRura`, `TownActionRuraFailed`,
`TownPlayerAction::setup`), `setMoveTo`, `setTargetPlayer(true)`, `setMoveTragetChara` ; il est **levé** par `__cmd_camera_move_to_player::isEnd` et `setCameraLock(false)`.
(Établi pour la liste des appelants ; **supposé** que tous ces chemins sont atteints en jeu : seuls les événements de script, le prologue et les marches libres ont été observés.)

### 2.2 Pourquoi pas `Global.Flag` bit 0x4

`cmn::PlayerManager::setLock(bool)` (0x1c63e4) tient un compteur `locked_` : verrouiller incrémente et pose `Flag |= 4` ; déverrouiller décrémente
et, à zéro, efface le bit 0x4 de `Flag` et arme `ui_MsgBeginTalkSE` (voir §3). Le bit 0x4 est donc posé **pendant tout message** (le héros est figé)
alors que la caméra ne fait que suivre le héros (verrou `TownCamera` = 0). Le prendre comme critère aurait supprimé le centrage à chaque dialogue de PNJ,
de jarre, de coffre. **Rejeté** (établi : trace `Flag = 0x1c/0x1d` en prologue avec verrou 1, `Flag = 0x1c` avec verrou 0 pendant les messages).

### 2.3 Trace du prologue (slot 2, carte `mlb1a`, nouvelle partie)

Relevée avec `DQ_CAMV=6` (affichage de l'état toutes les 6 images ; `_camv` dans `window.py`) et avec la sonde sans fenêtre `sonde_prologue4.py` :

- `ev01` (images 0-11) : verrou 0, pas de héros.
- `mlb1a`, image 12 → ~368 : `camera_jeu() = (1, 5, 0, 0)` : verrou 1, mode 5 (cible = un personnage), `Flag` 0x1c / 0x1d.
  Héros (1.1, 0.0, -3.2), cible caméra (0.0, 0.0, 20.0), position caméra (0.0, 28.9, -7.0) : cible à **23,2 unités** du héros.
  L'ancien critère (`CAM_CENTRE_MAX = 60`) centrait donc la caméra sur le héros et on voyait la salle au lieu de l'écran noir « Prologue » de l'original.
- Ensuite : `(0, 0, 0, 0)` ; le joueur a la caméra (dans la visionneuse, libération vers les images 369-371 de la boucle ; dans la sonde sans fenêtre, entre les images moteur 404 et 567, selon la cadence des appuis de touche).
- Pendant les messages, les jarres/tonneaux/coups de bâton : `(0, 0, 0, 0)` (sonde : images 942 à 1739) : le verrou **reste à 0**, le centrage reste actif. **Établi.**

### 2.4 Ce que fait la visionneuse maintenant (`_camera_ville`, `tick`)

> **État au 03/11/2026 (#47, #48)** : l'option `camera_centree` n'existe plus (clé abandonnée, `settings.py:99-100`). Le centrage est actif dès que `not libre and not mini and not cam_jeu and not titre` (`window.py:1171-1172`) ; le reste de cette section décrit le principe, qui est inchangé (verrou `TownCamera`, bornes 16/9, transition sans saut). Les puces qui parlent de « l'option » valent comme « le centrage ».

- `self.cam_jeu` = verrou `TownCamera` lu à chaque pas moteur (`camera_ville()[2]`, déjà lu pour `cam_bloquee`).
- Centrage actif seulement si `option and not cam_libre and not cam_jeu`. Hors centrage, le jeu applique sa caméra telle quelle, **avec les bornes
  16/9 de la visionneuse** (`bornes_x`, qui sont un choix de la visionneuse : le moteur cadre pour un écran portrait) — c'est exactement le comportement
  de l'option désactivée. **[choix]** : les bornes 16/9 restent appliquées pendant les scènes.
- Les scènes `cam_libre` (paquet 11, bit 7) gardent l'ancien comportement (inchangé).
- Transition sans saut **[choix]** : la correction de centrage `cam_dec` garde son lissage d'origine (`1 - exp(-14 dt)`), et le « poids » `cam_poids`
  (même constante) fait entrer/sortir progressivement les bornes 16/9. Si la cible de la caméra du jeu **saute** (changement de carte,
  coupure de plan : écart > 1,5 unité par pas, le même seuil que `_interpoler`, désormais `CAM_SAUT_VILLE`) la correction suit aussitôt (pas de glissement après la coupure).
- `CAM_CENTRE_MAX` (60) est conservé comme garde-fou (position du héros périmée), plus comme critère.
- Carte du monde (`_camera_champ`) : la caméra est déjà centrée sur le héros par le moteur (`e.champ['cam']`), aucune option en jeu. Inchangée.

### 2.5 Vérifications (captures xvfb, `--touches-test`, `CACHE=/tmp/uicache4`)

| vérification | résultat |
|---|---|
| prologue, images ≤ 368 (verrou 1) : option activée comparée à option désactivée | **identiques au pixel** (écran noir « Prologue » de l'original) |
| prologue, après libération du verrou | caméra centrée sur le héros ; identique à l'ancien code option activée |
| exploration libre (église → porte → `maout`), 5 captures (225, 235, 300, 420, 470) | **identiques au pixel** avant/après modification (caméra centrée, porte, changement de carte) |
| message de PNJ à l'église (3 captures, 230/260/330) | **identiques au pixel** avant/après modification |
| décalage artificiel de la cible (variable `DQ_DECTEST`, retirée) simulant le bornage du moteur près d'un bord | corrigé par le centrage quand verrou = 0 ; conservé quand option désactivée |
| `python3 -m pyflakes window.py engine.py` | un seul avertissement, ancien : `sel` inutilisé (≈ ligne 1700) |

### 2.6 Non vérifié / inconnu

- Une caméra de scène **visible** (verrou 1, cible de plan réellement visible) avec le héros près d'un bord de carte bornée : aucune scène de ce type
  n'a pu être jouée (le prologue est un écran noir ; en `maout` le moteur ne borne pas la cible : héros − cible = 0).
- Acquisition du verrou avec un déplacement **lent** (non coupé) : le raccord n'a été vérifié que pour des coupures et par simulation.
- Chutes (`TownFallAction`), sort de retour (`TownActionRura*`) : appelants identifiés, non joués.
- Prologue : les captures à l'écran ne passent pas l'attente de touche (`cmd_key_wait_type_b`) avec A seul : voir §4.

---

## 3. Le « bip » à l'ouverture d'un message

### 3.1 Réponse

Normal et voulu par le moteur. C'est le bruitage **SE 300** (paquet 35, fichier `SE0300`) :

- joué **au début d'un message** si le joueur vient de reprendre la main (sinon rien au début) ;
- joué **à chaque passage à la page suivante** (c'est « le même bip » que remarque le joueur).

### 3.2 Mécanisme (établi : désassemblage + sonde avec crochets mémoire et piles d'appel)

- Octet `ui_MsgBeginTalkSE` à `lib+0x252388` (GOT `0x23d800`). **Armé** (écrit à 1) par `cmn::PlayerManager::setLock(false)+0x5c` (0x1c6440) quand le compteur
  de verrous retombe à 0, c'est-à-dire quand le joueur est libéré (appelants vus : `cmd_player_lock`, `TownFurnitureManager::execute+0x44`).
  **Consommé** (écrit à 0) par `ui_MsgLoop()+0x1b8` (fonction à 0x157044), qui joue alors SE 300 : appel terminal à 0x157224.
- Passage de page : `ui_MsgLoop` appelle aussi le bruitage 300 à 0x157114 (`bl`, +0xd0) à chaque avancée.
- Conséquence : le **premier** message après une libération du joueur fait « bip » à l'ouverture ; les messages suivants d'un même événement
  (joueur toujours verrouillé) n'en font pas à l'ouverture mais en font au passage de page.
- Trace jarre à message (sonde, slot 2, prologue, jarre en (-2.5, -6.0)) :

  | image | événement |
  |---|---|
  | 1634 | paquet 35, SE **319** (jarre qui se brise ; **320** pour un tonneau, `TownFurnitureObject::openObject`) |
  | 1641 | paquet 35, SE **326** (icône « Riseup » de l'objet obtenu, `TownRiseupIcon::execute`) |
  | 1665 | ouverture de la fenêtre de message (`ui_MsgSetup` ← `TownFurnitureObject::addMessage` ← `TownWindowSystem::openCommonMessage`) |
  | 1669 | `ui_MsgLoop+0x1b8` efface `ui_MsgBeginTalkSE` |
  | 1670 | paquet 35, SE **300** ← c'est le « bip » |
  | 1713 | fin du message |
  | 1715 | `PlayerManager::setLock(false)` (via `TownFurnitureManager::execute`) réarme l'octet |

  Les jarres/tonneaux sans objet n'ont pas de message : seulement 319 / 320, pas de bip.
- Autres bruitages de l'interface vus : SE **304** à l'ouverture d'un Oui/Non (`CommonMenu_YESNO::menuSetup`, image 583 de la sonde) ; **305** vu à l'image 879 (cause non analysée).
  Un message de PNJ donne SE 300 à l'ouverture puis 300 à chaque page (images 621, 669, 693).
- Côté Unity (désassemblage IL2CPP) : `cmd_se_play` (0xD150A8) → `Sound.PlaySE` (0xD15128) → `SoundControl.Play("SE"+no, s_seVolume, no)`, sans condition.
  Unity ne joue lui-même le 300 que pour les boutons de menu (`MenuPortItem.Update`, `TouchPad.internalUpdate`, `InputName.Update`).
- Côté visionneuse : `sound.py` `jouer_se(ident)` → fichier `SE%04d`, volume `vol_b * r['volume']` ; les seuls `jouer_se(SE_BOUTON)` de `window.py` accompagnent des
  clics / validations de menu et de boutons d'écran (miroir de `MenuPortItem.Update`), jamais l'ouverture d'un message. **Pas de double lecture** (un seul paquet 35 → un seul `jouer_se`),
  bon fichier, aucune modification du code.
- Piège d'analyse : un crochet Unicorn posé sur une plage de 2 instructions se déclenche deux fois par appel ; ce n'est pas un double bruitage réel.

### 3.3 Supposé / inconnu

- **Supposé** : le volume réel du bruitage dans le jeu d'origine est `s_seVolume × volume du fichier` ; la visionneuse applique `vol_b × volume du fichier`
  (`vol_b` = volume de bruitages des réglages du portage). Non comparé au jeu Android.
- **Inconnu** : comportement du bip avec « Vitesse du texte » ou messages automatiques (non essayés).

---

## 4. Observations annexes (non corrigées, hors périmètre)

1. **Touches clavier des boutons d'écran** : Entrée (Commandes), Espace (Discussion), M (Carte) n'émettent pas le SE 300 alors qu'un clic souris sur le même bouton
   le joue (Unity : `TouchPad.internalUpdate`). Écart de fidélité mineur.
2. **Attente de touche du prologue** (`cmd_key_wait_type_b`, drapeau 0x4 posé, aucun message) : sur le terrain, Espace est converti en `BTN_PAROLE` (0x100) et A / B sont
   retirés de la manette (`p &= ~(MO.A | MO.B)`), donc le moteur ne reçoit jamais A brut ; Entrée devient `BTN_MENU`. Les captures automatisées n'ont pas pu passer ce point
   sans artifice (retiré). Zone d'un autre agent (écrans titre / prologue) : à signaler, non touchée.

---

## 5. Fichiers

- `dq4_pc/fenetre.py` : critère `cam_jeu`, `cam_poids`, `cam_saut`, `_coupure_camera`, `_camv`, constante `CAM_SAUT_VILLE`.
- `dq4_pc/moteur.py` : `Moteur.camera_jeu()` (lecture de la `TownCamera`).
- Sondes (scratchpad de session) : `sonde_prologue.py` à `sonde_prologue4.py`, `sonde_pnj.py`, `sonde_bord.py` ; lanceur `/tmp/run_t_camera-bip.sh`.
