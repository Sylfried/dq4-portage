"""Libelles descriptifs pour l'historique des messages : « Une femme », « Un soldat », « Une jarre » (qui parle) et « Château de Bastione », « Grotte » (où).

Module de donnees pur : deux tables compactes et deux fonctions, aucune dependance lourde, import instantane. Rien n'est lu dans les APK au lancement.
Tout ce qui est suppose (et non lu dans le moteur) est marque : voir confiance_source() et confiance_lieu(), et outils/generer_libelles.py pour la methode.

libelle_source(modele) -> str | None
    Libelle court AVEC article indefini (« Un vieil homme », « Une jarre »...) du personnage ou de l'objet identifie par `modele` ; None si inconnu.
    Formes d'identifiant acceptees (equivalentes) :
      - un entier : numero de feuille de sprite du moteur = Etat.sprites[emplacement]['id'] (paquet 12). Sur la carte du monde le moteur ajoute 4096 : retire ici ;
      - une chaine « h019 » (nom de la texture de la feuille dans le paquet de donnees) ou « 19 » ;
      - une chaine de decor : nom du modele FMAP de l'objet, avec ou sans son numero de groupe (« 012_tubo01 », « tubo01 », « Taru01(Clone) ») = Etat.carte-> donnees.carte(nom)['noms'][objet] ;
      - un dict (ou tout objet a cle 'id') portant l'une de ces formes : une entree de Etat.sprites convient telle quelle.
libelle_lieu(carte) -> str | None
    Nom court du lieu, utilisable seul apres « · » : nom officiel du patch FR quand le moteur en connait un, sinon un type generique (« Grotte », « Tour »).
    Identifiants acceptes : nom de carte du moteur (Etat.carte : « caf1 », « maout », « mak1f1 ») avec ou sans chemin / extension (« carte8_caf1.pkl »), « monde » (carte du monde),
    ou un objet Etat (attributs .carte et .partie ; partie 0xe = carte du monde : Etat.carte garde alors le NOM DE LA DERNIERE VILLE, il ne faut pas s'y fier).
    Regle unique : TOUTES les cartes d'un meme lieu (exterieur, maisons, auberge, eglise, puits, etages) rendent le nom du lieu ; pas de « Maison, Strattbourg ».
"""
import re

# --------------------------------------------------------------------------------------------------------------------------------------------
# Personnages : feuilles de sprite (Etat.sprites[i]['id']) ; (libelle, confiance, numeros). Confiance : 'C' = certaine (lu dans le moteur ou sans ambiguite visuelle), 'S' = supposee
# (classement visuel de la feuille, prudent : « Un homme » quand le metier n'est pas lisible).
# --------------------------------------------------------------------------------------------------------------------------------------
_GROUPES_SPRITES = (
    ('Un homme', 'C', (2,)),
    ('Un homme', 'S', (9, 10, 12, 13, 14, 23, 28, 30, 32, 33, 39, 57, 58, 67, 69, 71, 73, 76, 78, 132, 134, 142)),
    ('Un homme costaud', 'S', (11, 65, 220)),
    ('Un jeune homme', 'S', (0, 62, 77)),
    ('Un vieil homme', 'C', (5, 55, 61)),
    ('Un vieil homme', 'S', (146, 195)),
    ('Un garçon', 'C', (7,)),
    ('Un garçon', 'S', (72, 140)),
    ('Une petite fille', 'C', (8,)),
    ('Une jeune femme', 'C', (1,)),
    ('Une jeune femme', 'S', (63, 216, 217, 219)),
    ('Une femme', 'C', (4,)),
    ('Une femme', 'S', (24, 31, 42, 56, 59, 64, 70, 74, 133, 139, 145)),
    ('Une vieille femme', 'C', (3, 60)),
    ('Une vieille femme', 'S', (6,)),
    ('Une dame', 'S', (35, 38)),
    ('Une servante', 'S', (29,)),
    ('Une danseuse', 'S', (26, 121, 124, 126)),
    ('Une bunny girl', 'C', (27, 85)),
    ('Une elfe', 'C', (43, 135, 143)),
    ('Un soldat', 'S', (15, 16, 17, 150)),
    ('Un chevalier', 'S', (18, 152)),
    ('Un guerrier', 'S', (19, 144)),
    ('Une guerrière', 'S', (20,)),
    ('Un roi', 'C', (36,)),
    ('Un roi', 'S', (79, 82)),
    ('Un noble', 'S', (34,)),
    ('Un jeune noble', 'S', (37,)),
    ('Un prêtre', 'S', (21,)),
    ('Une religieuse', 'S', (22, 25)),
    ('Un magicien', 'S', (68, 75, 153, 155)),
    ('Une magicienne', 'S', (40,)),
    ('Un marin', 'S', (66,)),
    ('Un ange', 'S', (148, 149)),
    ('Un personnage encapuchonné', 'S', (41, 147)),
    ('Un aventurier', 'S', (100, 103, 106, 109, 112, 115, 118, 127)),            # personnages jouables : emplacement 0 = chef de groupe (106 sur deux sauvegardes du chapitre 1 ; 100 sur ev01). Leur nom vient du message, pas d'ici
    # animaux
    ('Un chien', 'C', (44,)),
    ('Un chien', 'S', (52, 131)),
    ('Un chat', 'S', (45, 46, 47)),
    ('Un cheval', 'C', (48, 49, 136)),
    ('Une vache', 'C', (50,)),
    ('Une vache', 'S', (51,)),
    ('Un cochon', 'C', (54,)),
    ('Un coq', 'S', (80,)),
    ('Un lapin', 'C', (173,)),
    ('Une grenouille', 'C', (174,)),
    ('Un félin', 'S', (138, 141)),
    ('Un lion', 'S', (157,)),
    ('Un petit animal', 'S', (53,)),
    # monstres : 130 / 180 = « gluant » (monstre 0 du patch FR) ; 165, 199-204, 221-230, 298, 300 : le moteur les remplace par un monstre (table de conversion, type 3)
    ('Un gluant', 'C', (130, 180)),
    ('Un squelette', 'S', (81, 182)),
    ('Un monstre', 'C', (165, 199, 200, 201, 202, 203, 204, 221, 222, 223, 224, 225, 226, 227, 228, 229, 230, 298, 300)),
    ('Un monstre', 'S', (154, 156, 159, 160, 163, 171, 172, 175, 176, 177, 178, 179, 181, 184, 185, 186, 187, 188, 189, 191)),
    # objets et vehicules places comme des sprites
    ('Une flamme', 'C', (151, 190)),
    ('Un œuf', 'C', (168,)),
    ('Un cercueil', 'C', (83,)),
    ('Un ballon', 'C', (183,)),                                                      # carte du monde (observe : id 4096 + 183)
    ('Une charrette', 'S', (137,)),
    ('Un bateau', 'C', (193,)),                                                      # carte du monde (observe : id 4096 + 193)
    ('Un meuble', 'S', (299,)),                                                      # remplace par un meuble par le moteur (table de conversion, type 4)
)
# Non nommes volontairement (None) : 158, 161, 162, 164, 166, 167, 169, 170, 192, 196, 197, 210-213, 215 = modeles 3D (table de conversion, type 2), nature non identifiee.

# --------------------------------------------------------------------------------------------------------------------------------------
# Decors et objets a examiner : noms de modeles FMAP (sans le numero de groupe), motifs ordonnes (le premier qui correspond gagne).
# Le nom vient du japonais en romaji (tubo = jarre, taru = tonneau, tbox = coffre au tresor, hondana = etagere a livres, tansu = commode, hikidashi = tiroir, kibako = caisse, ido = puits...)
# ou de l'anglais abrege (bed, door, book, slot) ; confiance 'S' partout sauf ce qui est un mot anglais courant (non verifie a l'ecran : les modeles 3D n'ont pas ete rendus).
# --------------------------------------------------------------------------------------------------------------------------------------
_REGLES_OBJETS = (
    (r'(?:big)?tubo\d+\w*', 'Une jarre', 'S'),
    (r'taru\w*', 'Un tonneau', 'S'),
    (r'tbox\d+', 'Un coffre', 'C'),
    (r'(?:hondana|bkdana|sakadana)\d*', 'Une étagère', 'S'),
    (r'tansu\d+[lr]?', 'Une commode', 'S'),
    (r'hikidashi\d*[a-z]?', 'Un tiroir', 'S'),
    (r'kibako\d*', 'Une caisse', 'S'),
    (r'(?:dpb\d+)?ido\d*', 'Un puits', 'S'),
    (r'w?bed\d*[a-z]?', 'Un lit', 'C'),
    (r'kamado\d*[a-z]?', 'Un fourneau', 'S'),
    (r'danro\d*', 'Une cheminée', 'S'),
    (r'(?:okikb|trskb|msgkb|dhkb|kb)\d*', 'Un panneau', 'S'),
    (r'hukuro\d*', 'Un sac', 'S'),
    (r'bin\d+', 'Une bouteille', 'S'),
    (r'book\d+', 'Un livre', 'C'),
    (r'haka\d+', 'Une tombe', 'S'),
    (r'\w*zou\d+', 'Une statue', 'S'),
    (r'gyokuza\d+', 'Un trône', 'S'),
    (r'kyodai\d+', 'Une coiffeuse', 'S'),
    (r'yoroi\d+', 'Une armure', 'S'),
    (r'yasai\d+', 'Des légumes', 'S'),
    (r'planter\d+', 'Un pot de fleurs', 'S'),
    (r'hachiue\d+(?:ns)?', 'Une plante en pot', 'S'),
    (r'slot\d+', 'Une machine à sous', 'C'),
    (r'ybbell\d+', 'Une cloche', 'S'),
    (r'araiba\d+', 'Un évier', 'S'),
    (r'oke\d+', 'Un seau', 'S'),
    (r'syokudai\d+', 'Un chandelier', 'S'),
    (r'taima\d+[a-z]?\d*', 'Une torche', 'S'),
    (r'tetugo\d+', 'Des barreaux', 'S'),
    (r'(?:esta|en|big)?isu\d*[a-z]?', 'Une chaise', 'C'),
    (r'(?:en|big)?tbl\d+', 'Une table', 'C'),
    (r'chdesk\d+', 'Un bureau', 'C'),
    (r'ikada\d+', 'Un radeau', 'S'),
    (r'kobune\d+', 'Une barque', 'S'),
    (r'w?door\d+', 'Une porte', 'C'),
)
_REGLES_OBJETS = tuple((re.compile(r'(?:%s)' % p), lib, c) for p, lib, c in _REGLES_OBJETS)

# === DEBUT GENERE (outils/generer_libelles.py) ===
_LIEUX_OFFICIELS = {                                                                  # prefixe de carte (2 lettres) -> nom du patch FR (getPlaceNameNo + extractText du moteur)
    'cb': 'Zamoksva',   # 27
    'cd': 'Ballimore',   # 18
    'ce': 'Palais de Lord Lionel',   # 24
    'cf': 'Casabranca',   # 16
    'cg': 'Parthénia',   # 23
    'ci': 'Fémiscyra',   # 34
    'cj': 'Palais du démon',   # 37
    'ck': 'Zénithia',   # 40
    'dp': 'Chapelle du Coteau',   # 42
    'ha': 'Bastione',   # 32
    'hc': 'Chandor',   # 17
    'hh': 'Canalot',   # 31
    'ma': 'Strattbourg',   # 33
    'mb': 'Zalenagrad',   # 50
    'mc': 'Taborov',   # 28
    'md': 'Vrenor',   # 5
    'me': 'Bazar du désert',   # 29
    'mf': 'Lakanaba',   # 8
    'mh': 'Teafortwo',   # 26
    'mi': 'Deadend',   # 12
    'mj': 'Port Lionel',   # 25
    'mk': 'Alpion',   # 38
    'mm': 'Bourg-les-Bains',   # 19
    'mn': 'Port-Carène',   # 20
    'mo': 'Ringys',   # 22
    'mq': 'Rosecolline',   # 35
    'mr': 'Estuaria',   # 36
    'ms': 'Azimut',   # 39
    'sh': 'Domaine de Minimus',   # 21
    'sm': 'Havre céleste',   # 41
    'ss': 'Chez Hoffman',   # 51
}
_LIEUX_VILLAGES = {'sb', 'se', 'sj'}                                                      # prefixes s? sans nom officiel mais avec maisons / auberge
# === FIN GENERE ===

_LIEUX_EXCEPTIONS = {'ca': 'Château de Bastione'}                                    # caf1 : le moteur n'a pas de nom pour 'ca' ; c'est le château de Bastione (sauvegarde de l'utilisateur, script de caf1 -> haout = Bastione)
_LIEUX_GENERIQUES = {'c': 'Château', 'd': 'Grotte', 't': 'Tour', 'm': 'Ville'}       # premiere lettre des noms de cartes sans nom officiel (convention des noms du jeu : c chateau, d donjon, t tour, m ville)

_MONDE = ('monde', 'world', 'worldmap', 'champ', 'field')
_PARTIE_CHAMP = 0xe                                                                  # Etat.partie : carte du monde (moteur.PARTIE_CHAMP)
_SPRITES = {}
for _lib, _conf, _ids in _GROUPES_SPRITES:
    for _i in _ids:
        assert _i not in _SPRITES, _i
        _SPRITES[_i] = (_lib, _conf)
del _lib, _conf, _ids, _i


def _de(nom):
    """« de Bastione » / « d'Azimut » (voyelle ou h muet)."""
    return ("d'" if nom[:1].lower() in 'aeiouyhéèêâîôû' else 'de ') + nom


def _entier(x):
    try:
        if isinstance(x, bool): return None
        i = int(x)
        return i if i == x else None
    except (TypeError, ValueError, OverflowError):
        return None


def _decoder(modele):
    """('sprite', entier) | ('objet', nom normalise) | None."""
    if modele is None: return None
    if not isinstance(modele, str):
        i = _entier(modele)
        if i is None:
            try: sous = modele['id']
            except Exception: sous = getattr(modele, 'id', None)
            return None if sous is None or sous is modele else _decoder(sous)
        return ('sprite', i - 4096 if i >= 4096 else i) if i >= 0 else None
    s = modele.strip().lower().split('/')[-1]
    if s.endswith('(clone)'): s = s[:-7].strip()
    m = re.fullmatch(r'h?(\d{1,4})', s)
    if m: return _decoder(int(m.group(1)))
    s = re.sub(r'\.(?:prefab|fbx|pkl|bin)$', '', s)
    s = re.sub(r'^\d+_', '', s)
    return ('objet', s) if s else None


def libelle_source(modele):
    """Voir l'en-tete du module. None si `modele` est inconnu ou d'une forme non reconnue."""
    d = _decoder(modele)
    if d is None: return None
    if d[0] == 'sprite':
        v = _SPRITES.get(d[1])
        return v[0] if v else None
    for rx, lib, _ in _REGLES_OBJETS:
        if rx.fullmatch(d[1]): return lib
    return None


def confiance_source(modele):
    """'certain' | 'suppose' | None (modele inconnu)."""
    d = _decoder(modele)
    if d is None: return None
    if d[0] == 'sprite': v = _SPRITES.get(d[1]); c = v[1] if v else None
    else: c = next((c for rx, _, c in _REGLES_OBJETS if rx.fullmatch(d[1])), None)
    return {'C': 'certain', 'S': 'suppose'}.get(c)


def _nom_carte(carte):
    """Nom de carte du moteur en minuscules, 'monde' pour la carte du monde, None si inutilisable."""
    if carte is None: return None
    if not isinstance(carte, str):
        if getattr(carte, 'partie', None) == _PARTIE_CHAMP: return 'monde'
        carte = getattr(carte, 'carte', None)
        if not isinstance(carte, str): return None
    s = carte.strip().lower().split('/')[-1]
    s = re.sub(r'\.(?:pkl|bin|fld|prefab|unity3d)$', '', s)
    s = re.sub(r'^carte\d+_', '', s)
    if s in _MONDE: return 'monde'
    return s if re.fullmatch(r'[a-z][a-z0-9_]+', s) else None


def _lieu(carte):
    """(libelle, origine) ; origine : 'officiel' (nom du patch FR lu par le moteur), 'derive' (nom officiel + « Château de », exception, ou « Monde »), 'generique' (type de lieu), None."""
    nom = _nom_carte(carte)
    if nom is None: return None, None
    if nom == 'monde': return 'Monde', 'derive'
    p = nom[:2]
    off = _LIEUX_OFFICIELS.get(p)
    if off:
        if p[0] == 'c' and not off.startswith(('Palais', 'Château')): return 'Château ' + _de(off), 'derive'
        return off, 'officiel'
    if p in _LIEUX_EXCEPTIONS: return _LIEUX_EXCEPTIONS[p], 'derive'
    if p in _LIEUX_VILLAGES: return 'Village', 'generique'
    g = _LIEUX_GENERIQUES.get(p[0])
    return (g, 'generique') if g else (None, None)


def libelle_lieu(carte):
    """Voir l'en-tete du module. None si la carte est inconnue ou n'est pas un lieu (combat, evenement)."""
    return _lieu(carte)[0]


def confiance_lieu(carte):
    """'officiel' | 'derive' | 'generique' | None."""
    return _lieu(carte)[1]
