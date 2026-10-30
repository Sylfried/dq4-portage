# Portage PC de DQ4 (Android) : notes techniques (état au 29/10/2026, soir)

## Architecture du jeu
- Unity 2022.3.62f3 (IL2CPP, ARM64 uniquement) + moteur C++ autonome `libdq4core.so` (2,4 Mo, 6 664 fonctions exportées avec noms conservés).
- Le moteur n'utilise que libc/libstdc++, `liblog` et 3 appels OpenGL (`glBindTexture`, `glGetError`, `glTexSubImage2D`, tous dans `TextureWriter`). Aucun appel de tracé : c'est Unity qui dessine.
- Points d'entrée (C) : `IsLoadNativeCode`, `DevInit(chemin_apk_données, chemin_sauvegarde, langue)`, `MenuPortInit(32, tampon_unity, 129, tampon_natif, 1089)`, `GameInit(input, output, output_float, str)`, `GameUpdate(pad_press, pad_toggle)`, `UnityRenderEvent`, `GetMessageCanvas`.
- `DevInit` reçoit le chemin de l'APK de données : le moteur lit lui-même le ZIP (21 ouvertures de l'APK au démarrage).

## Test de faisabilité (voie A) : RÉUSSI
- `portage_pc/test_faisabilite/` (`lancer_test.bat` + `test_core.py`, archive locale non versionnée ; `dq4_pc/emu_core.py` en est la suite) : chargeur ELF AArch64 maison + Unicorn. 61 constructeurs C++, DevInit, MenuPortInit, GameInit et des centaines de GameUpdate tournent. Validé sous Windows (Python 3.15, pc "pdc") et Linux.
- Vitesse : GameUpdate ~15 ms/image dans l'émulateur.

## Protocole moteur -> Unity (tampons de sortie)
- Deux curseurs globaux (dans la lib : entiers 0x258278, flottants 0x258280). Chaque image : flux d'entiers `[état, paquet, paquet…]` (terminé par -1) et flux de flottants parallèle. Le protocole est **différentiel** (Unity garde l'état : le moteur n'envoie que les changements).
- Découpage fiable des paquets : surveiller les écritures sur le curseur d'entiers (= validation d'un paquet) ; les flottants appartiennent au paquet « ouvert » (UnityGetPacket appelé, pas encore validé), sinon au dernier paquet validé (caméra 10 et chargement 11 : flottants écrits après la validation).
- **Le 1er entier du tampon de sortie est un mot d'état partagé** lu au début de chaque GameUpdate (stocké dans Global+0xd8). Bit0 = fondu en cours (mis par `UnitySetFade`, qui émet aussi un paquet type 9) : **Unity doit le remettre à 0 quand le fondu est fini**, sinon le moteur ne change jamais de partie/carte (cause du blocage initial). Autres bits mis par le moteur : bit2 `PlayerManager::setLock`, bit3 `UnityInitTouchFlag`, bit4 `TownCamera::setLimit`.
- `UnityGetPacket(type)` écrit le type et renvoie le curseur ; `UnitySetPacket(a,b)` ajoute 2 entiers ; `UnitySetPacket(int*)` valide ; `UnityGetFloatPacket(n)` réserve n flottants.
- **Paquets décodés :**
  - 0 = chargement d'une carte Unity : `unity_load_fld(nom, genre)` écrit le chemin de la ressource dans un tampon interne (lib+0x258290), ex. `ev/ev01/out/ev01` (titre), `m/ml/in/mlb1a` (1re ville), `m/ma/…/mak1f1`, `btl/<a>/stage/<b>` (combats) ; suivi d'un paquet 11 (flags + flottant).
  - 9 fondu ; 8 (6 flottants) ; 37/35 sons.
  - 10 caméra : entier = flags (bit0 position, bit1 cible), flottants x,y,z (Unity, y haut). FOV vertical 20° pour les villes (Camera Unity du datapack).
  - 12 `(slot, id)` : crée un sprite de personnage (id -1 = libère) ; la feuille de sprites est la texture Unity `h<id>` (ex. `h106`).
  - 13 mise à jour de sprite : entier 1 = flags | slot (slot sur 11 bits) ; bit11 → 1 flottant (échelle, 0.045 au début), bit12 → 4 flottants (couleur RGBA 0-1, alpha = fondu), bit13 → 3 flottants (position x,y,z monde = valeur/4096, z inversé), bit14 → un entier `pose | direction<<8`. 15 : bit12 → 3 flottants, bit13 → 1 flottant (÷12). 16 = fin d'animation.
  - 21 (slot, id) chargement de modèle (id -1 = libération) ; 22 maillage dynamique ; 31 ModelObject setup/cleanup ; 32 ModelObject::draw ; 28 FieldData::drawBlock ; 14, 18, 19-20 billboards/objets, 24-25 effets, 27-30 cartes/symboles, 34 effet d'écran (sémantique à établir).
- **Feuille de sprites `h<id>`** : cases de 24×32 px, 3 colonnes (pose 0-2) × 8 lignes (direction + variante), dans une texture 128×256. Les textures `m<id>` sont les monstres (combat) ; `m8901` = logo du titre.

## Démarrer le moteur sans Unity
- Singleton `Global` : pointeur à lib+0x23d438. Parties (`Global+0xc0` = actuelle, `+0xee` = id) : 3 = GameStartPart (menu de debug), 0xc = TownPart (le titre « ev01 » est une carte de ville), FieldPart, BattlePart, CasinoPart, BookPart.
- `Global::startTown(this, "nom")` + simulation du fondu (mettre à 0 le bit0 du 1er entier du tampon de sortie avant chaque `GameUpdate`) = change de carte. Nécessite au moins 1-2 `GameUpdate` avant (le curseur d'écriture doit exister).
- **Charger une sauvegarde : `profile::SaveLoad::loadbank(bank)`** (statique ; `bank` 0 = `data1.dat`, 15 360 octets ; le moteur ouvre `<chemin_sauvegarde>data1.dat`, sans « / » intermédiaire avec `/dq/save`). À appeler après quelques `GameUpdate`. Il restaure le groupe et relance la ville (`restartChurch` → `startTown`) ; la sauvegarde n°1 de l'utilisateur se trouve dans une église (carte `mak1f1`).
- `GameManager::resetParty` plante tant qu'aucune ville n'a été initialisée (`GameManager::initialize` est appelé par `TownSystem::initialize`).

## Données Unity (datapack.unity3d)
- Se lit avec UnityPy 1.25.4 : 12 267 GameObject, 10 627 Mesh, 4 619 Texture2D, 11 645 Material, 700 TextAsset (.map), 46 AnimationClip, 38 Camera.
- **Une carte = un GameObject racine `<nom>.fld`** (`mlb1a.fld`, `mak1f1.fld`, `ev01.fld`…) avec des enfants : décor principal `000_<nom>` (plusieurs sous-maillages = matériaux, textures `*.tim`), et des petits quads pour les accessoires (coffre, tonneau, pot, porte, torche…) dont les positions sont posées par le moteur. `<nom>.map` (TextAsset, en-tête « FHDR ») décrit objets et collisions.
- Lecture Mesh : `MeshHandler(m).process()` (sommets, UV0, couleurs, triangles par sous-maillage). Textures : `Texture2D.image` ; UV : v inversé.
- Lien id de modèle 3D (8900…, titre) -> objet Unity : non résolu.

## Rendu : état
- Version initiale : rasteriseur numpy maison (cloud). Remplacé par la fenêtre pyglet/OpenGL de `dq4_pc/fenetre.py` (voir `notes-visionneuse-dq4-pc.md`).
- Cadrage : vue conçue pour le portrait (ASPECT_DEF 0,5625). En 16:9 avec le même FOV vertical, une petite salle laisse des marges vides ; une ville étendue montre plus de décor sur les côtés.

## Inconnues / prochaines étapes
Suivies dans les issues du dépôt. Rappel : paquets 4, 6, 14, 15, 18, 19-20, 27-30 (FieldData / carte du monde) à décoder ; modèles 3D id -> asset (titre, boss) ; son (`libsdlib_android.so`, non étudiée) ; combats.
