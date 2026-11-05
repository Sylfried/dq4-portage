## 6. Fichiers de sauvegarde et API (c)

### 6.1 Fichiers

| Fichier | Taille | Contenu |
|---|---|---|
| `data1.dat` à `data3.dat` | 0x3c00 (15 360) | banques 0-2 : trois journaux manuels |
| `data4.dat` | 15 360 | banque 3 : suspension (Reprendre) |
| `data5.dat` | 15 360 | banque 4 : sauvegarde auto |
| `data9.dat` | 512 | premier dword = banque la plus récente (`catalogRecent`) ; « DWEN » → 0 |

Sans fichier, le moteur crée `data1..5.dat` et `data9.dat` (« DWEN ») à la construction du catalogue : le dossier doit être inscriptible.

### 6.2 Chiffrement (`Cryption::Filter`, 0x152de8, conserve la taille)

- graine = CRC32 bit à bit de la chaîne `"vb76Eg43"` (polynôme 0x7a7b58c6, init 0xffffffff, inversion finale) ;
- état = xorshift32 (`<<13`, `>>17`, `<<5`) ; chaque octet est XORé avec l'octet de poids faible de l'état.

### 6.3 Disposition en clair d'une banque

| Offset | Contenu |
|---|---|
| +0 | u32 `0x65747261` (« arte ») |
| +4 | u32 `0x0bf697de` |
| +8 | u32 somme de contrôle : somme des octets des 0x3660 premiers octets, champ mis à zéro |
| +0xc | étage / banque (`g_Stage[0x2b0]`) |
| +0xd | SAVETYPE |
| +0xe, +0xf | `g_pad_pos`, `g_pad_size` |
| +0x10 | nom de carte (chaîne) |
| +0x30 | chapitre |
| +0x24c | identifiants de 14 personnages |
| +0x25c | durée de jeu (u32, 1/60 s) |
| +0x497 | nom du héros (0x20, UTF-8) |
| +0x4b7 | sexe (0 homme, 1 femme) |
| +0x109d | table de niveaux (pas 0xc8, 14 entrées) |
| 0x3660 – 0x3c00 | rempli de 0xff |

Banque vide : premier dword `DWEN` (0x4e455744, `killbank(n,true)`) ; supprimée : `DLED` (0x44454c44, `killbank(n,false)`, ramenée à `DWEN` au prochain `getCatalogView`).
Le moteur n'a aucune fonction de copie ; la synchronisation cloud est dans le menu Network.

SAVETYPE : 1/2 = sauvegarde manuelle (variantes du menu SAVE) ; 3 = suspension (`savebank(3,3)` depuis `TownMenu_OPERATION_ROOT`) ou sauvegarde auto (`AutoSave` 0x164aa8 → `savebank(4,3)`) ; 4 = nouveau jeu.

Vérifications sur l'échantillon de Sylfried : data1 = « Solo », type 1, carte mak1f1, 239 246 images ; data2 = « Sofia », type 4, mlb1a, sexe 1 ; data3 = DWEN ; data4/5 = « Solo », type 3, carte « field » ; data9 = banque 0.

### 6.4 API moteur (adresses)

| Fonction | Adresse | Remarque |
|---|---|---|
| `getCatalogView` | 0x19a9ec | 5 × 0x60 octets à 0x259b94 |
| `getCatalogStatus` | 0x19af88 | masque de bits |
| `getCatalogRecent` | 0x19b050 | banque la plus récente |
| `getSaveBank(bool)` / `setSaveBank(int)` | 0x19aed8 / 0x19b344 | |
| `memoryload(u32, void*, u32)` | 0x19ac74 | fichier absent → zéros + `DWEN`, renvoie 1 |
| `memorysave` | 0x19b2ac | |
| `killbank(int, bool)` | 0x19ae24 | bool = vide (`DWEN`) ou supprimée (`DLED`) |
| `loadbank(int)` | 0x19b060 | banque numérotée à partir de 0 |
| `savebank(int, SAVETYPE)` / `savebankAsync` | 0x19b2c8 / 0x19b3a0 | |
| `getPlaceNameNo` / `getPlaceNameByChapter` | 0x19ace8 / 0x19adfc | |
| `setCatalogMacro` | 0x19b4e8 | |
| `Profile::collectDATA` / `deliverDATA` | 0x19b824 / 0x19c284 | |
| `calcCheckSum` / `isValidData` | 0x19b78c / 0x19b800 | |
| `Backup_Exist` / `GetSize` / `Write` / `Read` | 0x152bd0 / 0x152cc4 / 0x152d28 / 0x152e58 | `Read` renvoie 0 en cas de succès |

Pour l'hôte : les appels de fichier du moteur (`fopen`/`fclose` sur `data%d.dat`) sont déjà ponts dans `dq4_pc/moteur.py` (`CoreJeu.h_fopen/h_fclose`) ; `charger_sauvegarde(numero)` = `loadbank(numero-1)`.

---

## 7. Ce que la visionneuse gère déjà (e)

Établi par captures réelles (`/tmp/specs/img/viewer_*.png`) :

| Fonction | État | Capture |
|---|---|---|
| Phase 1 du titre (sans logo ni Tap to start) | partiel | `viewer_titre_phase1.png` |
| Menu racine (type 53) et bouton Portail (74) avec la disposition d'origine | oui | `viewer_menu_titre.png` |
| Liste des banques (type 54), couleurs, « Inutilisé », bouton Retour | oui | `viewer_liste_continuer.png` |
| Continuer → chargement de mak1f1 avec message | oui | `viewer_continuer_charge_mak1f1.png` |
| Supprimer : message de confirmation + fenêtre Oui/Non | oui | `viewer_supprimer_confirmation.png` |
| Créer → saisie du nom | **rien n'est affiché** | `viewer_nouveau_nom_rien_affiche.png` |
| Licence | **écran noir, bloqué** | `viewer_licence_ecran_noir.png` |

---

## 8. Lacunes de `dq4_pc/fenetre.py` (liste concrète)

Par ordre d'importance pour le joueur :

1. **Saisie du nom et du sexe (type 55)** : aucun rendu, aucun clavier. À faire : afficher un champ + clavier (ou saisie clavier physique) ; sur validation, envoyer `[2, n]` puis les octets UTF-8 empaquetés par deux (petit-boutiste, 30 octets au plus) ; attendre le choix du sexe (fenêtre 15 : « Choisir le sexe », nom, Masculin / Féminin) et répondre `[1, 0|1, 0x10]`. Gérer B (retour). Afficher le message 833011 si le nom est refusé, 833015 pendant la création.
2. **Écran Licence (type 80)** : l'écran reste noir après `fadeOutBlack`. À faire : rendre la fenêtre 80 (texte de licence) et renvoyer un A ou un B pour revenir (états LOAD 0xf → 0x10 → 0 ; l'entrée qui termine l'état 0xf est supposée, non vérifiée).
3. **Logos et Tap to start** : dessiner les maillages du paquet 22 (emplacement 2 → 12 sommets, emplacement 0 → 16 sommets, opacité par quad 184 → 255, textures m8900 / m8901 / m8905), la texture locale `taptostart`, `Retro4_copyright`. Le ciel d'ev01 montre des bords noirs mobiles.
4. **Messages du port 0 ignorés** : `[0,999]` (Quitter : fermer l'application), `[0,6]` (Portail : ouvrir le portail), `[0,4,v]` (volume SE), `[0,5,v]` (volume BGM), `[0,7,w,w]` (taille du nom du héros, hors JA), `[0,8,pos,size]` (position/taille de la manette).
5. **Menu cloud (valeur 8, types 75-79)** : non géré ; poser `g_isAmazon = 1` pour retirer la cellule ou ignorer la valeur.
6. **Cellules grisées** (`SetItemParam(cellule,0,3)`) : rendu non vérifié dans la visionneuse.
7. **Clic souris au titre** : non vérifié ; un clic doit produire un octet pad 0x10 en 2e argument de `GameUpdate`.
8. **Prologue d'un nouveau journal** (titre de chapitre type 12, attente de touche, message + Oui/Non) : non vérifié dans la visionneuse.
9. **Raccourci `--slot N`** : charge directement (`loadbank`) et contourne le titre ; à garder pour le test, mais ne passe par aucun écran de départ.
10. **Rafraîchissement de la liste après suppression** : le moteur ne rafraîchit pas les textes, ce qui est le comportement d'origine ; ne pas chercher à le corriger.

---

## 9. Établi / supposé et inconnues

| Sujet | Statut |
|---|---|
| Séquence des deux appuis A, durées des fondus | **établi** (sonde) |
| Fenêtres, ports, types, libellés du titre | **établi** |
| Valeurs de cellule 0/1/2/3/4/8/11 et leur effet | **établi** (sonde pour 0-4 ; 8 et 11 par désassemblage et sonde de Licence) |
| Machine à états LOAD | **établi** (désassemblage + sonde) |
| Format, taille, chiffrement, somme de contrôle des banques | **établi** (échantillons réels déchiffrés, somme de contrôle concordante) |
| Protocole du nom (`[2,n]` + octets empaquetés) | **établi** côté moteur |
| Code exact de message que Unity utilise pour le nom | **supposé** (tout code ≠ 1, 3 convient) |
| Façon dont `TitleTouch` de Unity convertit le clic en appui A | **supposé** |
| Différence sémantique entre SAVETYPE 1 et 2 | inconnu |
| Effets de `g_isAmazon` au-delà de la cellule cloud | inconnu |
| Sens des entiers sans libellé des fenêtres ; disposition exacte du maillage du paquet 22 | inconnu |
| Minuterie de la boucle d'attraction (`TownOpeningManager`) | lecture de code seule |
| Suite du prologue après le Oui/Non | non explorée |
| Clavier `InputName` d'Unity (disposition, longueur maximale, boutons Katakana/Hiragana pour JA) | inconnu |

---

## 10. Reproduction

Sonde (aucune écriture dans le dépôt ; sauvegardes dans un dossier temporaire) :

```
python3 /tmp/specs/sonde_titre.py                       # toutes les branches, sauvegardes d'exemple de Sylfried
python3 /tmp/specs/sonde_titre.py --branche titre menu continuer
python3 /tmp/specs/sonde_titre.py --branche nouveau supprimer --lecture -    # premier lancement (aucune sauvegarde)
python3 /tmp/specs/sonde_titre.py --lecture /chemin/saves --apk /chemin/patched_apks
```

Branches : `titre menu continuer reprendre auto nouveau supprimer licence quitter toutes`.
Défauts : APK `/mnt/user-data/uploads/DQ Patch/jeux/DQ4/patched_apks` ; sauvegardes `/mnt/user-data/uploads/Downloads/DQ Patch/jeux/DQ4/saves/20261007_190735`.
Sorties vérifiées : `/tmp/r2_work/sonde_a.out`, `/tmp/r2_work/sonde_b.out`.

Analyse d'une sauvegarde :

```
python3 /tmp/specs/dq4_sauvegarde.py data1.dat [--dump]
```

Visionneuse sans écran (une exécution xvfb à la fois) :

```
/tmp/r2_work/runv.sh ETIQUETTE "touches" "captures" [delai]
```

Syntaxe des touches de test : `N:NOM`, `+NOM` / `-NOM`, `@x@y` (clic en pixels depuis le coin haut gauche).

Captures : `/tmp/specs/img/` (`viewer_*.png`, `tex_taptostart*.png`, `tex_Retro4_copyright*.png`, `tex_m8900.png`, `tex_m8901.png`, `tex_m8905.png`).
