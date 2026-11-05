import re, sys
FW = set('le la les des du une un et ou pour dans sur avec sans est pas ces aux vos votre tes tous toutes quand comme mais donc sont chaque sinon aucun aucune par defaut fichier fichiers erreur chargement impossible dossier jeu image images carte combat lance mets manque introuvable trouve absent non oui ni ce cette qui que au se sa son ses leur etat sauvegarde sauvegardes fenetre ecran moteur texte taille lecture donnees resultat premier touche touches nombre tout mesure avant apres vers depuis aussi seulement fait faire arret fin debut temps duree ecart valeur valeurs ligne lignes octets capture decor monstre monstres musique bruitage partie heros fondu echec echecs rencontres attente ecrit cherche trouvee lu lus cible cibles appel appels nouveau ancien dossiers installe lis relance pret prete lancer echoue copie copies reglages reglage plein son journal erreurs chemin ouvrir ouvre fermer ferme enregistre enregistrer charge charger menu menus police polices'.split())
ACC = re.compile('[àâäçéèêëîïôöùûüÿœÀÂÇÉÈÊËÎÏÔÙÛÜŒ«»…°]')
EXC = set(sys.argv[2:]) | {'menu', 'menus', 'son', 'image', 'images', 'combat', 'partie', 'note', 'police'}
bad = []
for n, l in enumerate(open(sys.argv[1], encoding='utf-8', errors='replace'), 1):
    l2 = re.sub(r'(?:[A-Za-z]:)?[\\/][^\s\'")]+', ' ', l); l2 = re.sub(r'--[\w-]+|\{[^}]*\}|\[[^\]]*\]', ' ', l2)
    ws = [w for w in re.findall(r"[a-zA-Z']+", l2.lower().replace("'", ' ')) if w in FW and w not in EXC]
    if ACC.search(l2) or ws: bad.append((n, ws, l.rstrip()[:150]))
for b in bad: print(b)
print('French-looking lines:', len(bad))
