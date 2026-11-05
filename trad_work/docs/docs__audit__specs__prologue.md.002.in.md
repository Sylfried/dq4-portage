## 10. Établi / Supposé / Inconnu

**Établi** : la chronologie des paquets (§2) ; les deux plans de fondu, leurs shaders, leur file, leurs règles `Command` / `Update` / `IsEnd` (§3.1) ; la texture et la composition du bandeau ; `isEnd` de l'attente de touche = `decl != 0` ; la cause de la boîte violette et la disparition vérifiée sur cinq transitions ; la reconstitution visuelle du prologue (bandeau sur noir, éclats, salle).

**Supposé** : la caméra porteuse des plans (donc « fond = devant la scène, derrière l'interface ») ; la hauteur 225 du bandeau ; le garde-fou « noir > 6 s » inutile pour le plan de fond (le moteur le rouvre lui-même : vérifié pour la licence, le combat et le prologue, pas pour les autres flux) ; l'astuce « statut masqué » valable aussi quand le noir vient du plan de fond (comportement existant conservé).

**Inconnu / non vérifié** : tailles et places exactes des éclats par rapport au jeu réel ; paquet 33 ; paquet 13 `[2048]` pendant le travelling (valeur 0,748 → 1,0, probablement un taux de couleur du héros) ; `SetFadePriority` ; le deuxième texte du bandeau ; durée de l'extraction de `hyodai1` sous Windows ; comportement avec `vitesse_fondu` ≠ 2 (la durée d'affichage du bandeau en dépend car le moteur attend la fin des fondus).

---

## 11. Fichiers et captures

Captures (`/tmp/specs/img/`) : `prologue_carte_chapitre.png`, `prologue_sequence_titre.png`, `prologue_sequence_epee_piece.png`, `prologue_sequence_complete_camera_centree.png`, `prologue_attente_touche.png`, `prologue_boite_violette_avant_apres.png`, `prologue_boite_violette_avant_detail.png`, `prologue_transition_sexe.png`, `prologue_suppression_confirmation.png`, `prologue_suppression_oui.png`, `prologue_suppression_retour_menu.png`, `prologue_licence_retour.png`, `prologue_combat_avant_apres.png`, `prologue_tex_hyodai1.png`.

Lanceurs : `/tmp/run_t_prologue.sh` (scénario), `/tmp/run_c_prologue.sh` (combat), `/tmp/run_t_base.sh` (copie de `d381c1d` dans `/tmp/base_d381`), `/tmp/sheet.py` (planches). Réglages de test : `/tmp/rg_nc.json` (caméra non centrée), `/tmp/rg_v1.json` (vitesse des transitions 1).
