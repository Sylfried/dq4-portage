## 14. Plan de réécriture concret (ordre conseillé)
1. **Écran de logos** (section 2) avant la création du moteur : 2 images (sqex, arte), alpha linéaire 1 s / 3 s / 1 s, clic = saut. ~40 lignes pyglet ; aucune dépendance moteur.
2. **Machine `TapToStart`** (8.4) branchée sur le type de port 73 + message `[12,0,0]` ; entrée clic/Entrée -> pad A. Vérifier le fond noir (paquet 8) et les fondus (paquet 9 : bit 12 sortie, bit 14 variante).
3. **Menu du titre** (type 53) via l'export `ui_layout.json` déjà géré ; envoyer des **messages de port `[1, idBouton, 16]`** (id 0, 1, 2, 3, 8, 11) et non le pad ; **masquer le bouton id 8 (Sauv. cloud)**.
4. **Type 54** (emplacements) : message `[1, n, 16]` sur le port 14.
5. **Type 55** (nom) : section 12.6 ; **envoyer `[2,len]` + octets dans la même image**.
6. **Licence** (type 80) : fenêtre de texte défilante + bouton Privacy Policy + retour `15: 1,-1,32` (section 11) ; fondu `[20510]` -> `[16414]` déjà géré par le paquet 9.
7. Dialogue de sortie (section 4) : Échap -> confirmation.
8. Tout le reste (Google, OBB, Portail, NetConnection) : ne rien faire.

---------------------------------------------------------------------------------------------------

## 15. Inconnues (non établi, à ne pas inventer)
* Route exacte toucher -> pad (`TouchPad`) ; l'effet du **1er** appui A (rôle de la première phase du titre).
* Qui met `ApplicationQuit.s_quitStatus = 1` (Retour Android supposé).
* Valeurs inutilisées `c_skipBias`, `c_bias`.
* `InputName` : origine de la grille, boutons de fonction, `SetMode`, confirmation finale après le nom.
* Fenêtre `Make_License` (positions/tailles réelles), détails de `LicenseNobu`.
* `NetConnection` : réponses des coroutines et conditions d'ouverture côté moteur.
* Rendu 3D du titre (id 8900/8901/8905 -> objets, shader, signification des paquets BGM 16384/16392).
* Cadence réelle d'Unity (30 Hz supposé).
* Numérotation du pivot `MeshMaker.Build` (4 = centre déduit).
* Rôle exact du bit 14 du paquet 9 (fondu qui laisse l'UI visible : supposé).

---------------------------------------------------------------------------------------------------

## 16. Scripts et fichiers (reproductibles)
* `/tmp/specs/scripts/` : `da.py`, `da2.py`, `fn.py` (désassemble par nom, `LIST=1`), `xref.py` (appelants), `dr.py RVA [FIN]`, `ref_slot.py`, `consts_flt.py FICHIER [DEB [FIN]]` (constantes flottantes + appels d'un dump), `shaders.py`, `shaders2.py`, `boot_scene.py` (level0 + sharedassets0, décodage du MonoBehaviour Boot), `inputname_sets.py` (cctor InputName sous Unicorn, **sans `-I`**), `metastr.py`, `show_ui.py LOG [DEPUIS]` (décodage des traces, masque `[5,0]`/`[6,0]`), `trace_titre.py`, `trace_titre2.py` (`SCRIPT_MSG='image:port:a,b,c;…'`, `SCRIPT_PAD='image:masque,…'` ; plusieurs messages à la même image sont envoyés dans l'ordre). Dumps `_*.txt` (Boot, MainLoop, BackColor, TapToStart, InputName, Net, Make_*).
* Environnement des outils du dépôt : `DQ_IL2=/home/claude/il2` et `DQ_META=/tmp/specs/work/base_extract/assets/bin/Data/Managed/Metadata/global-metadata.dat` (sans `DQ_META`, `runall2.make()` échoue : `FileNotFoundError global-metadata.dat`).
* Traces : `/tmp/specs/work/t2_e.log` (ouverture + titre), `t2_g/h/i/j.log` (nouvelle partie, nom), `t2_k.log` (essai id 6 : sans effet), `t2_l11.log` (Licence), `t2_l8.log` (Sauv. cloud), `t2_m.log` (Licence + retour), `trace_titre_1000.log` (1000 images sans entrée).
* Table type -> Make : `/tmp/specs/work/type_to_make.txt`. Jeux de caractères : `/tmp/specs/work/inputname_sets.json`. Mise en page de référence : un `ui_layout.json` généré (ex. `/tmp/uicache/ui_layout.json`, types 53, 54, 55).
* Images : `/tmp/specs/img/` (préfixes `boot_*`, `title_*`, `dssatex_*`, `tex_*` : les miens ; les autres appartiennent à d'autres agents).
