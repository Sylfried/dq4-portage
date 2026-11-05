"""Textes anglais : ecrans et fenetres de l'outil autres que les pages Parametres (D-238, voir language.py) : ecran Sauvegardes (+ messages de la logique des fichiers et boites de dialogue), historique (libelles, aide, textes composes autour
des textes du jeu), saisie du nom, licence, noms des elements de l'editeur d'interface, textes d'essai des dialogues, notifications, infos F1 et messages de la console de ces modules.
Les textes du jeu (dialogues, noms, menus d'origine) ne sont jamais traduits. Ponctuation anglaise : pas d'espace avant « : »."""
EN = {
    # ---- ecran « Sauvegardes » (menu de depart)
    'Sauvegardes': 'Saves',
    'Exporter': 'Export',
    'Importer': 'Import',
    'Exporter : enregistre tes journaux (data1 à data5, data9) et tes états instantanés dans un fichier .zip.': 'Export: saves your adventure logs (data1 to data5, data9) and your save states into a .zip file.',
    'Importer : lit un .zip de ce genre, ou des fichiers data1.dat, data2.dat… (par exemple copiés depuis un téléphone Android).': 'Import: reads a .zip like that, or data1.dat, data2.dat… files (for example copied from an Android phone).',
    "Les fichiers remplacés sont d'abord copiés dans le dossier « before_import_… » de tes sauvegardes.": 'Replaced files are first copied to the "before_import_…" folder in your saves folder.',
    '%d fichier de sauvegarde': '%d save file',
    '%d fichiers de sauvegarde': '%d save files',
    '%d état instantané': '%d save state',
    '%d états instantanés': '%d save states',
    'Exporter les sauvegardes': 'Export saves',
    'Importer des sauvegardes': 'Import saves',
    "Choisis où enregistrer le fichier dans la fenêtre qui vient de s'ouvrir…": 'Choose where to save the file in the window that just opened…',
    "Choisis le .zip ou les fichiers de sauvegarde dans la fenêtre qui vient de s'ouvrir…": 'Choose the .zip or the save files in the window that just opened…',
    'Exporté : %s et %s.': 'Exported: %s and %s.',
    'Importé : %s et %s.': 'Imported: %s and %s.',
    'Pour mettre à jour les boutons grisés du menu de départ, relance le jeu.': 'To update the grayed-out buttons of the start menu, restart the game.',
    'Impossible : %s': 'Failed: %s',
    'Export annulé.': 'Export canceled.',
    'Import annulé.': 'Import canceled.',
    'Anciens fichiers copiés dans : %s': 'Previous files copied to: %s',
    'Ignorés : %s': 'Skipped: %s',
    'Pas de boîte de dialogue disponible : dépose tes fichiers (.zip, data1.dat…) dans': 'No file dialog available: put your files (.zip, data1.dat…) in',
    'puis clique de nouveau sur Importer.': 'then click Import again.',
    'Sauvegardes importées': 'Saves imported',

    # ---- logique des fichiers de sauvegarde (persistance\sauvegardes.py, logfile_format.py) : messages d'erreur montres par l'ecran Sauvegardes, boites de dialogue de fichiers
    'Aucune sauvegarde a exporter (ni journal, ni etat instantane).': 'Nothing to export (no adventure log, no save state).',
    'Aucun fichier de sauvegarde reconnu (%s).': 'No save file recognized (%s).',
    "Aucun fichier n'a pu etre ecrit (%s).": 'No file could be written (%s).',
    'data1.dat a data5.dat, data9.dat ou savestates/state_NN.dqs attendus': 'expected data1.dat to data5.dat, data9.dat or savestates/state_NN.dqs',
    '%s : ecriture impossible (%s) ; le fichier actuel est inchange': '%s: could not be written (%s); the current file is unchanged',
    '%s : taille %d au lieu de %d (%s)': '%s: size %d instead of %d (%s)',
    '%s : %s (%s)': '%s: %s (%s)',
    '%s : fichier trop petit (%s)': '%s: file too small (%s)',
    "%s : ce n'est pas un .zip valide": '%s: not a valid .zip file',
    "ce n'est pas un journal du jeu (en-tete inconnu)": 'not a game adventure log (unknown header)',
    'fichier abime (somme de controle incorrecte)': 'damaged file (checksum mismatch)',
    'Archive zip': 'Zip archive',
    'Sauvegardes (zip, data*.dat, state_*.dqs)': 'Saves (zip, data*.dat, state_*.dqs)',
    'Tous les fichiers': 'All files',

    # ---- fenetre Historique (dialogues et combats)
    'Combats': 'Battles',
    'Favoris seulement': 'Favorites only',
    "Aucun dialogue pour l'instant.": 'No dialogue yet.',
    "Aucun combat pour l'instant.": 'No battle yet.',
    'Aucun dialogue en favori : décoche « Favoris seulement », choisis un dialogue et appuie sur Entrée (ou clique son étoile) pour le garder.': 'No favorite dialogue: uncheck "Favorites only", choose a dialogue and press Enter (or click its star) to keep it.',
    'Aucun combat en favori : décoche « Favoris seulement », choisis un combat et appuie sur Entrée (ou clique son étoile) pour le garder.': 'No favorite battle: uncheck "Favorites only", choose a battle and press Enter (or click its star) to keep it.',
    'Haut / Bas : message précédent / suivant': 'Up / Down: previous / next message',
    'Molette : défiler': 'Mouse wheel: scroll',
    'Gauche / Droite : onglet': 'Left / Right: tab',
    'Entrée : favori ★': 'Enter: favorite ★',
    'F : favoris seulement': 'F: favorites only',
    '%s : suite': '%s: next',
    'Échap : fermer': 'Esc: close',
    # textes que l'outil compose autour de ceux du jeu (entete et lignes d'un combat, favori dont le message manque)
    'Victoire': 'Victory',
    'Fuite': 'Escaped',
    'Défaite': 'Defeat',
    '%s : %s': '%s: %s',
    '%d vaincu': '%d defeated',
    '%d vaincus': '%d defeated',
    '%d enfui': '%d fled',
    '%d enfuis': '%d fled',
    '%d disparu': '%d vanished',
    '%d disparus': '%d vanished',
    '%d resté': '%d remained',
    '%d restés': '%d remained',
    '%s : enfui': '%s: fled',
    '%s : disparu': '%s: vanished',
    '%s : resté': '%s: remained',
    'Ennemis inconnus': 'Unknown enemies',
    'Or : %d\u00a0\u00a0\u00a0\u00a0\u00a0Expérience : %d': 'Gold: %d\u00a0\u00a0\u00a0\u00a0\u00a0Experience: %d',
    'Objets : %s': 'Items: %s',
    '(Message introuvable dans les fichiers du jeu : %s)': '(Message not found in the game files: %s)',
    'Monstre': 'Monster',
    'Objet n°%d': 'Item #%d',
    # messages de la console

    # ---- saisie du nom, licence
    'Saisir un nom': 'Enter a name',
    'Clavier : taper le nom': 'Keyboard: type the name',
    'Entrée : valider · Échap : retour': 'Enter: confirm · Esc: back',
    'Licence': 'License',

    # ---- noms des elements dans l'editeur d'interface (boutons de l'ecran)
    'Discussion': 'Talk',
    'Croix': 'D-pad',

    # ---- textes d'essai des dialogues (editeur d'interface), une ligne par entree
    "Aperçu d'un message.": 'Message preview.',
    'Ceci est un texte de test.': 'This is a test text.',
    'Il sert à régler la taille et': 'It is used to adjust the size and',
    'la position des dialogues.': 'position of the dialogue boxes.',
    "Aperçu d'un message": 'Message preview',
    'sur deux lignes.': 'on two lines.',
    'Voici un exemple de dialogue.': 'Here is an example dialogue.',
    'Déplace et redimensionne cette': 'Move and resize this',
    'fenêtre comme tu le souhaites.': 'window as you like.',
    "Texte d'essai : les messages du jeu": 'Test text: the game messages',
    "s'afficheront ici, à cette taille.": 'will be displayed here, at this size.',

    # ---- infos F1
    '%.0f images/s | moteur %.1f pas/s (%.1f ms) | pire image %.0f ms | dessin Python %.1f ms': '%.0f frames/s | engine %.1f steps/s (%.1f ms) | worst frame %.0f ms | Python drawing %.1f ms',



}
