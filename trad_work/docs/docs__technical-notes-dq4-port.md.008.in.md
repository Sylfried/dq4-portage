### Écritures qui jouent le rôle d'Unity (le moteur les attend d'Unity)
| Réf | Site | Rôle | Fichier:ligne |
|---|---|---|---|
| U1 | bit 0 du premier mot du tampon de sortie (`outp[0]`, `Global.Flag`) | « un fondu est en cours » (`Fade.FadePlane.CheckFade`), levé et baissé à chaque image selon les deux plans de fondu | `engine.py:747` |
| U2 | bit 1 du même mot | « effet d'écran en cours » (`Capture.ScreenEffect`) pendant la cascade de début de combat ; la fenêtre le borne (`ATTENTE_CHARGE_MAX`) | `engine.py:717` (appelé en `722` et `730`) |
| U3 | bit 0 de l'octet `table[idx × 32 + 0x14]` d'un objet de carte (`table` = `[FLDObject + 8]`) | rappel « animation finie » (porte, coffre, jarre) après une durée lue dans les données, sinon `DUREE_ANIM` | `engine.py:914` |
| U4 | file de messages interface → moteur (`buf1`) ; remise à zéro de la file moteur → interface (`buf2`) | ce que fait `MenuPort.Send` : touches et clics de menu, saisie du nom ; seules les actions du joueur y passent | `engine.py:881` (envoi), `845` (remise à zéro) |
| U5 | tampon de paramètres du canevas de message, puis appel direct de `SDrawCTRL::CanvasSetup` | Unity crée ce canevas par un message de port (512 x 512) | `engine.py:654-655` |

### Autres écritures
| Réf | Site | Rôle | Fichier:ligne |
|---|---|---|---|
| E1 | `etats.appliquer` : image de la bibliothèque, tas, données, TLS | chargement d'un état instantané demandé par le joueur (la version du fichier est vérifiée) ; suivi de `reappliquer_correctifs` (S1 à S4) | `savestates.py:46-50` ; `engine.py:603-609` |
| F1 | `CoreJeu.h_fopen` / `h_fclose` | les fichiers `dataN.dat` ouverts en écriture par le moteur sont redirigés vers le dossier d'écriture (`--saves-ecriture`) ; les originaux ne sont ouverts qu'en lecture (Établi par la lecture du code ; non vérifié par somme de contrôle) ; depuis #199 l'écriture passe par `CoreJeu.ecrire_atomique` (`.tmp` + `os.replace`, deux essais) et une erreur d'E/S n'arrête plus le moteur (`echecs_ecriture`, signalée par la fenêtre) | `noyau/moteur.py` (`CoreJeu`) |

### Appels de fonctions du moteur (pas d'écriture directe)
- **A1** retour à l'écran titre (`Moteur.retour_titre`, menu Pause > « Revenir à l'écran titre » après confirmation) : `profile::SaveLoad::killbank(4, 0)` (efface la banque 4, la sauvegarde automatique ; les fichiers que le moteur écrit vont dans le dossier d'écriture, F1), `PlayerManager::setLock(1)`, `Global::startTitle()` : ce que fait le bouton d'origine des Paramètres du jeu. `engine.py:664-671`.
- **A2** chargement d'un journal (`SaveLoad::loadbank`) et relecture du catalogue après un import (`getCatalogView`, `getCatalogRecent`, `getCatalogStatus`) : `engine.py:918`, `923`, `933`.
- **A3** initialisation (`DevInit`, `MenuPortInit`, `GameInit`, `engine.py:436-441`), `GameUpdate` à chaque image avec le masque de touches (`engine.py:756`) ; essais seulement : `Global::startField` et `startTown` (`engine.py:662`, `675`), `BattleMenu_setHoppingNumbers` sous `DQ_CALLHOP` (`engine.py:753`).

### Crochets en lecture seule
| Réf | Site | Ce qu'il lit | Fichier:ligne |
|---|---|---|---|
| R1 | `MenuPort::SetVisible` | si la fenêtre de message est affichée | `engine.py:459` |
| R2 | `FieldData::drawBlock` | l'objet qui porte la carte du monde | `engine.py:465` |
| R3 | `FLDObject::SetCommonAnimation` | l'objet animé en cours | `engine.py:468` |
| R4 | `OptionStatus::setBattleSpeed` | un changement de la vitesse des messages fait dans les Paramètres d'origine (rappel à la visionneuse) | `engine.py:505` |
| R5 | `TownMenu_OPERATION_ROOT::menuUpdate` `0x16ef28` | le bouton choisi (7 = « Paramètres ») : lève `demande_pause` | `engine.py:643-644` |
| R6 | `TextBuffer::cat` | chaque page de message, pour l'historique des dialogues | `history.py:306` |
| R7 | cinq fonctions de combat : `PartyStatus::startBattle`, `BattleActorManager2::execMonsterDeath`, `BattleExecDefeatMonster::initialize`, `BattleExecEscape::setup`, `Global::endBattle` | ennemis vaincus, or, expérience, pour l'historique des combats | `battle_history.py:36-37`, `157` |
| R8 | `UC_HOOK_MEM_WRITE` sur les curseurs d'écriture `0x258278` et `0x258280` et crochet sur `UnityGetPacket` | découpe les paquets moteur → Unity | `pktlog.py:11-14` |
| R9 | les quatre crochets d'entrée / sortie des commandes de fondu de script (S9) | un drapeau Python | `engine.py:566` |

Les crochets d'historique (R6, R7) sont entourés de `try` (`Capteur._cat`, `CapteurCombat._crochet`) : une erreur ne doit pas arrêter le moteur. Les variables d'environnement `DQ_*` de débogage ne modifient pas le moteur, sauf `DQ_CALLHOP` (essai, A3).
