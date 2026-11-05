# Correspondance des noms du 05/11/2026 (passage à l'anglais)

Demande de Sylfried (05/11/2026) : « Revois toute l'organisation du projet pour changer la convention de nommage pour avoir tous les dossiers, les fichiers, les variables des fichiers pythons etc, bref tout en anglais » (D-239).

**Ce qui est en anglais** : les dossiers et fichiers du dépôt, et tous les identifiants du code (modules, classes, fonctions, méthodes, attributs, variables, arguments, constantes).

**Ce qui reste en français, à dessein** : les textes affichés au joueur (les clés de `tr()`), les commentaires, les docstrings et les documents ; les clés de dictionnaires et de `reglages.json`, les identifiants de pages du menu Pause, les clés des dictionnaires d'états instantanés et les noms des variables GLSL (ce sont des chaînes, pas des identifiants) ; les options de la ligne de commande (`--largeur`, `--saves-ecriture`…) ; les dossiers que le jeu crée sur ton PC (`donnees\…`), traités à part.

Les anciens états instantanés (`.dqs`) et les anciens réglages se relisent toujours : voir `OLD_ATTRIBUTES` (core/engine.py), `OLD_MODULES` et `OLD_CLASSES` (persistence/savestates.py).

La table complète ancien nom → nouveau nom des **identifiants** est dans [`rename_identifiers.tsv`](rename_identifiers.tsv).

## Dossiers

| Avant | Maintenant |
|---|---|
| `dq4_pc/combat/` | `dq4_pc/battle/` |
| `dq4_pc/fenetre/` | `dq4_pc/window/` |
| `dq4_pc/monde/` | `dq4_pc/world/` |
| `dq4_pc/noyau/` | `dq4_pc/core/` |
| `dq4_pc/persistance/` | `dq4_pc/persistence/` |
| `dq4_pc/rendu/` | `dq4_pc/render/` |
| `dq4_pc/textes_en/` | `dq4_pc/texts_en/` |
| `outils/` | `tools/` |
| `outils/flux_session/` | `tools/session_flow/` |
| `outils/recherche/` | `tools/research/` |
| `outils/recherche/chargement/` | `tools/research/loading/` |
| `outils/recherche/combat/` | `tools/research/battle/` |
| `outils/recherche/decor/` | `tools/research/scenery/` |
| `outils/recherche/moteur/` | `tools/research/engine/` |
| `outils/recherche/son/` | `tools/research/sound/` |
| `outils/recherche/texte/` | `tools/research/text/` |

## Fichiers dont le nom a changé

### `.github/ISSUE_TEMPLATE/` → `.github/ISSUE_TEMPLATE/`

| Avant | Maintenant |
|---|---|
| `recherche.md` | `research.md` |
| `tache.md` | `task.md` |
| `test_windows.md` | `windows_test.md` |

### `docs/archives/` → `docs/archives/`

| Avant | Maintenant |
|---|---|
| `rapports-agents-40-44.md` | `agent-reports-40-44.md` |
| `rapports-agents-45.md` | `agent-reports-45.md` |

### `docs/archives/briefs/` → `docs/archives/briefs/`

| Avant | Maintenant |
|---|---|
| `brief_commun.md` | `common_brief.md` |
| `brief_commun42.md` | `common_brief42.md` |
| `brief_commun43.md` | `common_brief43.md` |
| `brief_commun44.md` | `common_brief44.md` |
| `brief_commun45.md` | `common_brief45.md` |
| `brief_commun47.md` | `common_brief47.md` |

### `docs/audit/` → `docs/audit/`

| Avant | Maintenant |
|---|---|
| `plan_tests_chapitre2.md` | `chapter2_test_plan.md` |
| `couverture.md` | `coverage.md` |
| `lacunes_connues.md` | `known_gaps.md` |
| `rapport_reste_a_faire.md` | `remaining_work_report.md` |

### `docs/audit/specs/` → `docs/audit/specs/`

| Avant | Maintenant |
|---|---|
| `audit_interface_combat.md` | `battle_interface_audit.md` |
| `moteur_avant_partie.md` | `engine_pre_game.md` |
| `audit_menus_pave.md` | `numpad_menus_audit.md` |
| `texte_notes.md` | `text_notes.md` |
| `unity_avant_partie.md` | `unity_pre_game.md` |

### `docs/` → `docs/`

| Avant | Maintenant |
|---|---|
| `plan_du_code.md` | `code_plan.md` |
| `historique.md` | `history.md` |
| `licences.md` | `licenses.md` |
| `reprise.md` | `resume.md` |
| `notes-technique-portage-dq4.md` | `technical-notes-dq4-port.md` |
| `notes-visionneuse-dq4-pc.md` | `viewer-notes-dq4-pc.md` |

### `dq4_pc/combat/` → `dq4_pc/battle/`

| Avant | Maintenant |
|---|---|
| `effet_combat.py` | `battle_effect.py` |
| `historique_combat.py` | `battle_history.py` |
| `vitesse_combat.py` | `battle_speed.py` |
| `effets_plein_ecran.py` | `full_screen_effects.py` |

### `dq4_pc/fenetre/` → `dq4_pc/window/`

| Avant | Maintenant |
|---|---|
| `scene_combat.py` | `battle_scene.py` |
| `effets_capture.py` | `capture_effects.py` |
| `constantes.py` | `constants.py` |
| `champ.py` | `field.py` |
| `plein_ecran.py` | `full_screen.py` |
| `jeu.py` | `game.py` |
| `aides.py` | `helpers.py` |
| `entrees.py` | `inputs.py` |
| `clavier_souris.py` | `keyboard_mouse.py` |
| `affichage_menus.py` | `menu_display.py` |
| `ecrans.py` | `screens.py` |
| `instantanes.py` | `snapshots.py` |
| `titre.py` | `title_screen.py` |

### `dq4_pc/noyau/` → `dq4_pc/core/`

| Avant | Maintenant |
|---|---|
| `rencontres.py` | `encounters.py` |
| `moteur.py` | `engine.py` |
| `priorite_jeu.py` | `game_priority.py` |
| `historique.py` | `history.py` |
| `suivi_charge.py` | `load_tracking.py` |
| `pose_couchee.py` | `lying_pose.py` |

### `dq4_pc/` → `dq4_pc/`

| Avant | Maintenant |
|---|---|
| `langue.py` | `language.py` |
| `principal.py` | `main.py` |
| `chemins.py` | `paths.py` |
| `son.py` | `sound.py` |

### `dq4_pc/menus/` → `dq4_pc/menus/`

| Avant | Maintenant |
|---|---|
| `police_messages.py` | `message_font.py` |
| `saisie_nom.py` | `name_entry.py` |
| `avant_partie.py` | `pre_game.py` |
| `ecran_sauvegardes.py` | `saves_screen.py` |
| `ui_historique.py` | `ui_history.py` |

### `dq4_pc/monde/` → `dq4_pc/world/`

| Avant | Maintenant |
|---|---|
| `donnees.py` | `data.py` |
| `decors_plats.py` | `flat_sceneries.py` |
| `objets_carte.py` | `map_objects.py` |
| `teinte_carte.py` | `map_tint.py` |
| `contours_decor.py` | `scenery_outlines.py` |

### `dq4_pc/persistance/` → `dq4_pc/persistence/`

| Avant | Maintenant |
|---|---|
| `format_journal.py` | `logfile_format.py` |
| `sauvegardes.py` | `saves.py` |
| `etats.py` | `savestates.py` |
| `reglages.py` | `settings.py` |
| `ecriture.py` | `write_dir.py` |

### `dq4_pc/rendu/` → `dq4_pc/render/`

| Avant | Maintenant |
|---|---|
| `effets_capture.py` | `capture_effects.py` |
| `effet_lampe.py` | `lamp_effect.py` |
| `effet_riremito.py` | `riremito_effect.py` |
| `effet_tabi.py` | `tabi_effect.py` |
| `ciel_titre.py` | `title_sky.py` |

### `dq4_pc/textes_en/` → `dq4_pc/texts_en/`

| Avant | Maintenant |
|---|---|
| `fenetre.py` | `window.py` |

### `./` → `./`

| Avant | Maintenant |
|---|---|
| `lancer_dq4.bat` | `launch_dq4.bat` |

### `tests/` → `tests/`

| Avant | Maintenant |
|---|---|
| `_chemins.py` | `_paths.py` |
| `test_sauvegarde_auto.py` | `test_autosave.py` |
| `test_ballon_echelle.py` | `test_balloon_scale.py` |
| `test_ombre_ballon.py` | `test_balloon_shadow.py` |
| `test_camera_combat.py` | `test_battle_camera.py` |
| `test_historique_combat.py` | `test_battle_history.py` |
| `test_decor_combat_heure.py` | `test_battle_scenery_time_of_day.py` |
| `test_vitesse_combat.py` | `test_battle_speed.py` |
| `test_transition_combat.py` | `test_battle_transition.py` |
| `test_effets_capture.py` | `test_capture_effects.py` |
| `test_casino_bestiaire.py` | `test_casino_bestiary.py` |
| `test_coup_critique.py` | `test_critical_hit.py` |
| `test_horloge_jour.py` | `test_day_clock.py` |
| `test_nom_dialogue.py` | `test_dialogue_name.py` |
| `test_croix_et_clic.py` | `test_dpad_and_click.py` |
| `test_croix_course.py` | `test_dpad_run.py` |
| `test_rencontres.py` | `test_encounters.py` |
| `test_coffre_ennemi.py` | `test_enemy_chest.py` |
| `test_camera_moteur.py` | `test_engine_camera.py` |
| `test_entrees.py` | `test_entries.py` |
| `test_don_exp_toucher.py` | `test_exp_gift_touch.py` |
| `test_ciel_etendu.py` | `test_extended_sky.py` |
| `test_ordre_groupe_champ.py` | `test_field_group_order.py` |
| `test_fld_priorite.py` | `test_fld_priority.py` |
| `test_perte_focus.py` | `test_focus_loss.py` |
| `test_effets_plein_ecran.py` | `test_full_screen_effects.py` |
| `test_priorite_jeu.py` | `test_game_priority.py` |
| `test_fond_degrade.py` | `test_gradient_background.py` |
| `test_decalques_sol.py` | `test_ground_decals.py` |
| `test_alerte_tas.py` | `test_heap_alert.py` |
| `test_historique_acces.py` | `test_history_access.py` |
| `test_historique_cle.py` | `test_history_key.py` |
| `test_lignes_inactives.py` | `test_inactive_lines.py` |
| `test_panneau_interface.py` | `test_interface_panel.py` |
| `test_reglages_interface.py` | `test_interface_settings.py` |
| `test_description_objet.py` | `test_item_description.py` |
| `test_bruitage_clavier.py` | `test_keyboard_sfx.py` |
| `test_langue.py` | `test_language.py` |
| `test_lanceur.py` | `test_launcher.py` |
| `test_niveau_pv.py` | `test_level_hp.py` |
| `test_chargement.py` | `test_loading.py` |
| `test_pose_couchee.py` | `test_lying_pose.py` |
| `test_magie_liste.py` | `test_magic_entries.py` |
| `test_objets_carte.py` | `test_map_items.py` |
| `test_textures_carte.py` | `test_map_textures.py` |
| `test_teinte_carte.py` | `test_map_tint.py` |
| `test_cartes_pnj.py` | `test_maps_npcs.py` |
| `test_touche_menu.py` | `test_menu_key.py` |
| `test_langue_menus.py` | `test_menu_language.py` |
| `test_tabulation_menu.py` | `test_menu_tab.py` |
| `test_message_repli.py` | `test_message_fallback.py` |
| `test_police_messages.py` | `test_message_font.py` |
| `test_historique_messages.py` | `test_message_history.py` |
| `test_crochets_manques.py` | `test_missing_hooks.py` |
| `test_texture_monstre_absente.py` | `test_missing_monster_texture.py` |
| `test_espace_insecable.py` | `test_nonbreaking_space.py` |
| `test_langue_pages.py` | `test_page_language.py` |
| `test_parametres_sans_pause.py` | `test_params_without_pause.py` |
| `test_chemins.py` | `test_paths.py` |
| `test_langue_pause.py` | `test_pause_language.py` |
| `test_temps_de_jeu.py` | `test_play_time.py` |
| `test_poker_police.py` | `test_poker_font.py` |
| `test_retour_titre.py` | `test_return_to_title.py` |
| `test_decors_racine.py` | `test_root_scenery.py` |
| `test_notifications_sauvegardes.py` | `test_save_notifications.py` |
| `test_ecriture_sauvegarde.py` | `test_save_writing.py` |
| `test_import_sauvegardes.py` | `test_saves_import.py` |
| `test_sauvegardes_un_dossier.py` | `test_saves_in_one_folder.py` |
| `test_etats_correctifs.py` | `test_savestate_fixes.py` |
| `test_etats_ordre.py` | `test_savestates_order.py` |
| `test_etats_liste_blanche.py` | `test_savestates_whitelist.py` |
| `test_decor_culling.py` | `test_scenery_culling.py` |
| `test_contours_decor.py` | `test_scenery_outlines.py` |
| `test_ecrans.py` | `test_screens.py` |
| `test_sepia_decor.py` | `test_sepia_scenery.py` |
| `test_son_decodage.py` | `test_sound_decoding.py` |
| `test_son_echecs.py` | `test_sound_failures.py` |
| `test_son_mixage.py` | `test_sound_mixing.py` |
| `test_son_musique_limites.py` | `test_sound_music_limits.py` |
| `test_reglages_son_texte.py` | `test_sound_text_settings.py` |
| `test_son_volumes.py` | `test_sound_volumes.py` |
| `test_feuilles_speciales.py` | `test_special_sheets.py` |
| `test_bouton_vitesse.py` | `test_speed_button.py` |
| `test_oui_non_empile.py` | `test_stacked_yes_no.py` |
| `test_plaque_depart.py` | `test_start_menu_plate.py` |
| `test_texte_recentrage.py` | `test_text_recentering.py` |
| `test_texte_defilement.py` | `test_text_scrolling.py` |
| `test_camera_titre.py` | `test_title_camera.py` |
| `test_titre_centrage.py` | `test_title_centering.py` |
| `test_titre_logo.py` | `test_title_logo.py` |
| `test_titre_ciel.py` | `test_title_sky.py` |
| `test_camera_ville.py` | `test_town_camera.py` |
| `test_bruitage_transition.py` | `test_transition_sfx.py` |
| `test_enchainement_tours.py` | `test_turn_chaining.py` |
| `test_carte_inconnue.py` | `test_unknown_map.py` |
| `test_sprites_droits.py` | `test_upright_sprites.py` |
| `test_langue_fenetre.py` | `test_window_language.py` |
| `test_mode_fenetre.py` | `test_window_mode.py` |
| `test_sans_rappel_demarrage.py` | `test_without_startup_callback.py` |

### `outils/` → `tools/`

| Avant | Maintenant |
|---|---|
| `generer_ui.bat` | `generate_ui.bat` |
| `mesure_bascule.py` | `measure_toggle.py` |
| `simuler_rencontres.py` | `simulate_encounters.py` |

### `outils/recherche/` → `tools/research/`

| Avant | Maintenant |
|---|---|
| `LISEZMOI.md` | `README.md` |

### `outils/recherche/audit/` → `tools/research/audit/`

| Avant | Maintenant |
|---|---|
| `analyse.py` | `analysis.py` |
| `audit_reproduire.sh` | `audit_reproduce.sh` |
| `audit_valeurs.py` | `audit_values.py` |
| `probe_grille.py` | `probe_grid.py` |
| `echelles.py` | `scales.py` |
| `scan_paquets.py` | `scan_packets.py` |
| `balayage.py` | `sweep.py` |
| `balayage_tete.py` | `sweep_head.py` |

### `outils/recherche/combat/` → `tools/research/battle/`

| Avant | Maintenant |
|---|---|
| `analyse_log.py` | `analysis_log.py` |
| `exp_contour.py` | `exp_outline.py` |
| `gl_decors.py` | `gl_sceneries.py` |

### `outils/recherche/moteur/` → `tools/research/engine/`

| Avant | Maintenant |
|---|---|
| `desm.py` | `disasm_method.py` |
| `desasm_moteur.py` | `disasm_engine.py` |
| `dq4_sauvegarde.py` | `dq4_save.py` |
| `extraire_res.py` | `extract_res.py` |
| `harnais.py` | `harness.py` |
| `sonde_titre.py` | `probe_title.py` |
| `lire_journal.py` | `read_logfile.py` |
| `rend_tous.py` | `render_all.py` |
| `rend_combat.py` | `render_battle.py` |
| `rend_etat.py` | `render_state.py` |
| `rend_type.py` | `render_type.py` |
| `scan_parts_manquantes.py` | `scan_missing_parts.py` |

### `outils/recherche/chargement/` → `tools/research/loading/`

| Avant | Maintenant |
|---|---|
| `apres_viewer_h.py` | `after_viewer_h.py` |
| `analyse_suivi.py` | `analysis_tracking.py` |
| `mesure.py` | `measure.py` |

### `outils/recherche/decor/` → `tools/research/scenery/`

| Avant | Maintenant |
|---|---|
| `fond.py` | `background.py` |
| `hauteurs.py` | `heights.py` |
| `marche_fin.py` | `walk_end.py` |
| `marche_sud.py` | `walk_south.py` |

### `outils/recherche/son/` → `tools/research/sound/`

| Avant | Maintenant |
|---|---|
| `scen_combat.py` | `battle_scenario.py` |
| `fuite.py` | `flee_battle.py` |
| `inv_se.py` | `inv_sfx.py` |
| `menusons.py` | `menu_sounds.py` |
| `vrai_pyglet.py` | `real_pyglet.py` |
| `son_AB.py` | `sound_ab.py` |

### `outils/recherche/sprites/` → `tools/research/sprites/`

| Avant | Maintenant |
|---|---|
| `mesure_cycle.py` | `measure_cycle.py` |

### `outils/recherche/texte/` → `tools/research/text/`

| Avant | Maintenant |
|---|---|
| `analyse.py` | `analysis.py` |
| `rend_multi.py` | `render_multi.py` |

### `outils/recherche/ui/` → `tools/research/ui/`

| Avant | Maintenant |
|---|---|
| `render_liste.py` | `render_list.py` |

### `outils/flux_session/` → `tools/session_flow/`

| Avant | Maintenant |
|---|---|
| `LISEZMOI.md` | `README.md` |
| `moteur_slot.sh` | `engine_slot.sh` |
| `lancer_tests.sh` | `run_tests.sh` |

### `outils/ui_il2cpp/` → `tools/ui_il2cpp/`

| Avant | Maintenant |
|---|---|
| `desasm.py` | `disasm.py` |
| `generer_ui.py` | `generate_ui.py` |
| `entete.py` | `header.py` |
