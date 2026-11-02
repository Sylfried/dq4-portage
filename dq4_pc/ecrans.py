"""Choix du moniteur du plein ecran : la logique pure (sans fenetre ni OpenGL), pour la tester avec de faux ecrans (outils/test_ecrans.py).
- lister : les moniteurs detectes par pyglet (`display.get_screens()`) -> descriptions (indice, position, dimensions, nom, principal) ;
- libelle : « Écran 2 (2560x1440), DELL U2720Q » (principal marque) ;
- memoriser / retrouver : le reglage `ecran_plein` du joueur (None = automatique) et sa retrouvaille au lancement suivant, meme si les moniteurs ont change d'ordre ou de resolution ;
- cible : l'ecran a utiliser pour le plein ecran (le choix, sinon celui de la fenetre, sinon le principal), et l'etat du choix pour la page Affichage."""

AUTO = 'auto'                 # valeur de la liste « Écran du plein écran » : l'ecran ou se trouve la fenetre
ABSENT = 'absent'             # valeur de la liste quand l'ecran enregistre n'est plus branche : le choix est garde dans les reglages, l'ecran de la fenetre sert en attendant


def _entier(v, defaut=0):
    try: return int(v)
    except (TypeError, ValueError, OverflowError): return defaut


def _nom_de(ec):
    """Nom du moniteur quand pyglet le donne (Windows : nom d'usage du moniteur, X11 : nom de la sortie) ; '' sinon (jamais d'erreur)."""
    for essai in (lambda: ec.get_monitor_name(), lambda: ec.name):
        try:
            n = essai()
            if isinstance(n, str) and n.strip(): return n.strip()
        except Exception: pass
    return ''


def lister(ecrans):
    """Liste des ecrans de pyglet (dans l'ordre de `get_screens()`) -> [dict(indice, x, y, largeur, hauteur, nom, principal)] ; exactement un principal (celui que le systeme annonce, a defaut celui en (0, 0), a defaut le premier).
    Un ecran illisible est ignore ; `ecrans` illisible -> []."""
    sortie = []
    try: liste = list(ecrans)
    except Exception: return []
    for src, ec in enumerate(liste):
        try: d = dict(x=int(ec.x), y=int(ec.y), largeur=int(ec.width), hauteur=int(ec.height), nom=_nom_de(ec), principal=False)
        except Exception: continue
        try: d['annonce'] = bool(ec.is_primary)
        except Exception: d['annonce'] = None
        d['source'] = src          # (position dans la liste de pyglet : retrouve l'objet Screen meme si un ecran illisible a ete ignore)
        sortie.append(d)
    if not sortie: return []
    p = next((d for d in sortie if d['annonce']), None) or next((d for d in sortie if d['x'] == 0 and d['y'] == 0), None) or sortie[0]
    p['principal'] = True
    for i, d in enumerate(sortie): d['indice'] = i; d.pop('annonce', None)
    return sortie


def libelle(d):
    """« Écran 1 (1920x1080), principal » ; le nom du moniteur est ajoute quand on le connait : « Écran 2 (2560x1440), DELL U2720Q »."""
    s = 'Écran %d (%dx%d)' % (d['indice'] + 1, d['largeur'], d['hauteur'])
    if d.get('principal'): s += ', principal'
    if d.get('nom'): s += ', ' + d['nom']
    return s


def memoriser(d):
    """Ce que le reglage `ecran_plein` enregistre d'un ecran : indice, position, dimensions et nom (sans le nom ni les dimensions l'indice seul ne suffirait pas a le retrouver apres un changement de branchement)."""
    return dict(indice=int(d['indice']), x=int(d['x']), y=int(d['y']), largeur=int(d['largeur']), hauteur=int(d['hauteur']), nom=str(d.get('nom') or ''))


def valide(v):
    """Valeur lue (reglages.json, ligne de commande) -> description memorisee propre, ou None (automatique) pour tout ce qui n'en est pas une (absent, texte, nombres absurdes, dimensions nulles)."""
    if not isinstance(v, dict): return None
    try:
        d = dict(indice=_entier(v.get('indice'), -1), x=_entier(v.get('x')), y=_entier(v.get('y')), largeur=_entier(v.get('largeur')), hauteur=_entier(v.get('hauteur')), nom=str(v.get('nom') or '').strip())
    except Exception: return None
    if d['indice'] < 0 or d['largeur'] <= 0 or d['hauteur'] <= 0 or d['indice'] > 64: return None
    return d


def retrouver(choix, liste):
    """Indice, dans `liste` (de `lister`), de l'ecran enregistre `choix` ; None s'il n'est plus la (ou s'il n'y a pas de choix).
    Dans l'ordre : le meme nom de moniteur (si un seul : lui, meme si sa resolution a change ; si plusieurs : celui de la meme position et des memes dimensions, sinon du meme indice, sinon des memes dimensions) ;
    sans nom : la meme position avec les memes dimensions, puis le meme indice avec les memes dimensions, puis le seul ecran de ces dimensions. Une resolution changee sur un moniteur sans nom connu : plus retrouve (l'ecran de la fenetre sert)."""
    c = valide(choix)
    if c is None or not liste: return None
    mm = lambda d: (d['largeur'], d['hauteur']) == (c['largeur'], c['hauteur'])
    memes_noms = [d for d in liste if c['nom'] and d['nom'] == c['nom']]
    if len(memes_noms) == 1: return memes_noms[0]['indice']
    cands = memes_noms or list(liste)
    for test in (lambda d: (d['x'], d['y']) == (c['x'], c['y']) and mm(d), lambda d: d['indice'] == c['indice'] and mm(d)):          # (la place sur le bureau, reglee par le joueur, change moins que l'ordre de l'enumeration)
        t = [d for d in cands if test(d)]
        if t: return t[0]['indice']
    t = [d for d in cands if mm(d)]
    if len(t) == 1 or (memes_noms and t): return t[0]['indice']
    return None


def ecran_de(rect, liste):
    """Indice de l'ecran qui contient le centre du rectangle (x, y, largeur, hauteur) de la fenetre, a defaut celui qu'elle recouvre le plus ; None si elle n'en touche aucun (ou rectangle illisible)."""
    try: x, y, w, h = [float(v) for v in rect]
    except (TypeError, ValueError): return None
    cx, cy = x + w / 2.0, y + h / 2.0
    for d in liste:
        if d['x'] <= cx < d['x'] + d['largeur'] and d['y'] <= cy < d['y'] + d['hauteur']: return d['indice']
    meilleur, aire = None, 0.0
    for d in liste:
        ax, ay = min(x + w, d['x'] + d['largeur']) - max(x, d['x']), min(y + h, d['y'] + d['hauteur']) - max(y, d['y'])
        if ax > 0 and ay > 0 and ax * ay > aire: meilleur, aire = d['indice'], ax * ay
    return meilleur


def principal(liste):
    """Indice de l'ecran principal (0 si la liste est vide : jamais d'erreur)."""
    return next((d['indice'] for d in liste if d['principal']), 0)


def cible(choix, liste, fenetre=None):
    """L'ecran du plein ecran -> (indice dans `liste`, etat). `fenetre` : indice de l'ecran ou se trouve la fenetre (None : inconnu). Etats : 'auto' (aucun choix : l'ecran de la fenetre, a defaut le principal),
    'choisi' (l'ecran enregistre est la), 'absent' (un ecran est enregistre mais n'est plus branche : l'ecran de la fenetre, a defaut le principal ; le choix reste dans les reglages). Liste vide -> (None, etat)."""
    if not liste: return None, (AUTO if valide(choix) is None else ABSENT)
    repli = fenetre if isinstance(fenetre, int) and 0 <= fenetre < len(liste) else principal(liste)
    if valide(choix) is None: return repli, AUTO
    i = retrouver(choix, liste)
    return (i, 'choisi') if i is not None else (repli, ABSENT)


def valeurs_liste(choix, liste):
    """Valeurs de la liste deroulante de la page Affichage : AUTO, les indices des ecrans detectes, puis ABSENT quand l'ecran enregistre n'est plus la (sa ligne dit lequel)."""
    v = [AUTO] + [d['indice'] for d in liste]
    if valide(choix) is not None and retrouver(choix, liste) is None: v.append(ABSENT)
    return v


def valeur_choisie(choix, liste):
    """Valeur de la liste qui correspond au reglage : AUTO, l'indice de l'ecran retrouve, ou ABSENT."""
    if valide(choix) is None: return AUTO
    i = retrouver(choix, liste)
    return ABSENT if i is None else i


def nom_valeur(v, choix, liste):
    """Libelle d'une valeur de la liste : « Automatique (écran de la fenêtre) », « Écran 2 (2560x1440) », ou « Écran 3 (absent) » (l'ecran enregistre, qui n'est plus branche)."""
    if v == AUTO: return 'Automatique (écran de la fenêtre)'
    if v == ABSENT:
        c = valide(choix)
        return 'Écran %d (absent)' % (c['indice'] + 1) if c else 'Écran absent'
    d = next((d for d in liste if d['indice'] == v), None)
    return libelle(d) if d else 'Écran %s' % (v,)
