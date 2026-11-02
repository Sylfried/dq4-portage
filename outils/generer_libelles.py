#!/usr/bin/env python3
"""Generateur reproductible des tables de dq4_pc/libelles.py (lieux) et des tableaux de frequence de outils/test_libelles.py.

Ce que l'outil CALCULE (a partir du jeu, rien n'est devine) :
  1. LIEUX. Le moteur d'origine (libdq4core.so, sous Unicorn, comme le portage) sait nommer le lieu d'une carte pour l'ecran de sauvegarde :
       profile::SaveLoad::getPlaceNameNo(int, char* nom_de_carte) -> 0x0c0000NN (0 = pas de nom) ; la regle du moteur ne regarde que les DEUX PREMIERES LETTRES du nom de carte
       (ma = Strattbourg, ha = Bastione, cb = Zamoksva...), le texte vient de TextAPI::extractText(buf, 0x0c0000NN) (banque b1007000 du patch FR, entree NN - 1).
     L'outil appelle ces deux fonctions du moteur pour chaque carte du jeu et verifie que toutes les cartes d'un meme prefixe donnent le meme numero.
     Les prefixes a 0 (chateaux ca cc ch cl cm, donjons d?, tours t?, villes mg ml mp, lieux s? et za, combats bt, evenements ev) n'ont pas de nom officiel : libelles.py leur applique
     des types generiques d'apres la 1re lettre ; les prefixes s? qui ont des maisons / une auberge (cartes s?m#f# ou s?y#f#) sont des villages.
  2. PERSONNAGES. Les scripts de cartes (assets/script/<carte>.bin, 397 fichiers) placent les personnages : chaque noeud `scriptobject` porte six entiers
     (a0, modele, direction, x, y, z) a  o + (W(o+0x14) & ~3) + (W(o+0x20) & ~3) (W = mot de 32 bits) ; tout a zero = pas de placement. `modele` est le numero de feuille de sprite
     (texture « h<modele> » du paquet de donnees ; les numeros 158-230 et 298-300 d'une table de conversion du moteur (36 triplets a 0xfda20 de libdq4core) sont des modeles 3D,
     des monstres ou un meuble). L'outil compte les placements et les cartes par modele (FREQ_SPRITES).
     Le CLASSEMENT des feuilles (homme, femme, soldat...) est fait A LA MAIN d'apres des planches-contact des feuilles h<numero> (voir _GROUPES_SPRITES de libelles.py) : il n'est pas genere.
  3. DECORS. Les noms de modeles FMAP de chaque carte (donnees.carte(nom)['noms'], sans le numero de groupe) donnent FREQ_OBJETS. Les motifs de _REGLES_OBJETS sont ecrits a la main.

Usage (depuis la racine du depot) :
    python3 outils/generer_libelles.py --apk "<dossier des APK patches>" --cache "<dossier de cache des cartes>" [--ecrire]
Sans --ecrire : affiche seulement les statistiques et ce qui serait ecrit. Avec --ecrire : remplace le bloc entre
    # === DEBUT GENERE (outils/generer_libelles.py) ===  et  # === FIN GENERE ===
dans dq4_pc/libelles.py et outils/test_libelles.py. Le moteur n'ecrit que dans un dossier temporaire ; les APK, les ressources et les sauvegardes ne sont jamais modifies.
"""
import argparse, collections, os, re, struct, sys, tempfile, textwrap, zipfile

RACINE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
sys.path.insert(0, os.path.join(RACINE, 'dq4_pc'))
DEBUT = '# === DEBUT GENERE (outils/generer_libelles.py) ==='
FIN = '# === FIN GENERE ==='
DONNEES = 'split_UnityDataAssetPack.apk'


def lire_placements(apk_donnees):
    """{carte: [(modele, direction, x, y, z)]} d'apres les scripts de cartes (placements non nuls)."""
    z = zipfile.ZipFile(apk_donnees); res = {}
    for nom in z.namelist():
        m = re.fullmatch(r'assets/script/(\w+)\.bin', nom)
        if not m: continue
        b = z.read(nom); lst = []
        for mm in re.finditer(rb'scriptobject\x00+', b):
            o = mm.start()
            hs, po, ps = (struct.unpack_from('<I', b, o + d)[0] for d in (0x14, 0x20, 0x24))
            if ps < 0x18: continue
            v = struct.unpack_from('<6i', b, o + (hs & ~3) + (po & ~3))
            if v != (0,) * 6: lst.append(v[1:])
        res[m.group(1)] = lst
    return res


def frequences_sprites(placements):
    """{modele: (placements, cartes)}."""
    n = collections.Counter(); c = collections.defaultdict(set)
    for carte, lst in placements.items():
        for v in lst: n[v[0]] += 1; c[v[0]].add(carte)
    return {k: (n[k], len(c[k])) for k in sorted(n)}


def liste_cartes(donnees):
    return sorted(n[:-4] for n in donnees._gos() if n.endswith('.fld'))


def frequences_decors(donnees, cartes):
    """{nom de modele sans numero de groupe: (occurrences, cartes)}."""
    n = collections.Counter(); c = collections.defaultdict(set)
    for carte in cartes:
        try: noms = donnees.carte(carte, True)['noms']
        except Exception as e:
            print('carte %s ignoree (%s)' % (carte, str(e)[:60])); continue
        for nom in noms.values():
            nom = re.sub(r'^\d+_', '', nom).lower(); n[nom] += 1; c[nom].add(carte)
    return {k: (n[k], len(c[k])) for k in sorted(n)}


def noms_lieux(dossier_apk, cartes):
    """({prefixe: (numero, nom)}, avertissements) : getPlaceNameNo et extractText du moteur, pour chaque carte."""
    import moteur as MO
    tmp = tempfile.mkdtemp(prefix='sv_libelles_')
    mo = MO.Moteur(dossier_apk, tmp, tmp); c = mo.core
    gpn = c.export('_ZN7profile8SaveLoad14getPlaceNameNoEiPc'); ext = c.export('_ZN7TextAPI11extractTextEPci'); buf = c.malloc(0x400)
    par = collections.defaultdict(collections.Counter)
    for nom in cartes: par[nom[:2]][c.call(gpn, 0, c.cstr(nom.encode()), label='gpn') & 0xffffffff] += 1
    res, avert = {}, []
    for p, cnt in sorted(par.items()):
        if len(cnt) > 1: avert.append('prefixe %s : numeros differents %s' % (p, dict(cnt)))
        r = cnt.most_common(1)[0][0]
        if r == 0: continue
        c.mem_w(buf, b'\0' * 0x400); c.call(ext, buf, r, label='et')
        res[p] = (r & 0xffff, c.mem(buf, 0x100).split(b'\0')[0].decode('utf-8'))
    return res, avert


def villages_s(cartes, officiels):
    """Prefixes s? sans nom officiel qui ont des maisons ou une auberge (cartes s?m#f# / s?y#f#)."""
    return sorted({n[:2] for n in cartes if n[0] == 's' and n[:2] not in officiels and re.fullmatch(r's[a-z][my]\d.*', n)})


def bloc_libelles(officiels, villages):
    ls = ['_LIEUX_OFFICIELS = {                                                                  # prefixe de carte (2 lettres) -> nom du patch FR (getPlaceNameNo + extractText du moteur)']
    ls += ["    '%s': %r,   # %d" % (p, nom, n) for p, (n, nom) in sorted(officiels.items())]
    ls += ['}', '_LIEUX_VILLAGES = %s                                                      # prefixes s? sans nom officiel mais avec maisons / auberge' % ('{%s}' % ', '.join(repr(v) for v in sorted(villages)) if villages else 'set()')]
    return '\n'.join(ls) + '\n'


def bloc_test(cartes, fsp, fob):
    def liste(nom, items):
        lignes = textwrap.wrap(' '.join(items), 150)
        return '%s = (%s\n    ).split()\n' % (nom, ('\n    ').join(repr(l + ' ') for l in lignes))
    out = '# cartes du jeu (%d)\n' % len(cartes) + liste('CARTES', cartes)
    out += '# modele de sprite : « modele:placements:cartes » (placements dans les scripts, nombre de cartes)\n'
    out += liste('_FREQ_SPRITES', ['%d:%d:%d' % (k, *v) for k, v in sorted(fsp.items())])
    out += '# modeles de decor (nom sans numero de groupe) vus au moins 2 fois : « nom:occurrences:cartes »\n'
    out += liste('_FREQ_OBJETS', ['%s:%d:%d' % (k, *v) for k, v in sorted(fob.items()) if v[0] >= 2])
    return out


def remplacer(fichier, contenu):
    t = open(fichier, encoding='utf-8').read()
    i, j = t.index(DEBUT) + len(DEBUT), t.index(FIN)
    open(fichier, 'w', encoding='utf-8').write(t[:i] + '\n' + contenu + t[j:])


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--apk', required=True, help='dossier des APK patches (base.apk, split_UnityDataAssetPack.apk, split_config.arm64_v8a.apk)')
    ap.add_argument('--cache', required=True, help='dossier de cache des cartes du portage (carte8_*.pkl) ; rempli si besoin (lent la premiere fois)')
    ap.add_argument('--ecrire', action='store_true', help='remplace les blocs generes de libelles.py et de test_libelles.py')
    a = ap.parse_args()
    from donnees import Donnees
    donnees = Donnees(os.path.join(a.apk, DONNEES), a.cache, log=lambda *x: None)
    cartes = liste_cartes(donnees)
    placements = lire_placements(os.path.join(a.apk, DONNEES)); fsp = frequences_sprites(placements)
    fob = frequences_decors(donnees, cartes)
    officiels, avert = noms_lieux(a.apk, cartes)
    villages = villages_s(cartes, officiels)
    print('%d cartes ; %d placements de personnages (%d modeles) ; %d modeles de decor ; %d prefixes nommes ; villages s? : %s' % (
        len(cartes), sum(v[0] for v in fsp.values()), len(fsp), len(fob), len(officiels), villages))
    for w in avert: print('ATTENTION', w)
    for p, (n, nom) in sorted(officiels.items(), key=lambda kv: kv[1][0]): print('  %s  %2d  %s' % (p, n, nom))
    if not a.ecrire: print('(simulation : relancer avec --ecrire pour ecrire les fichiers)'); return
    remplacer(os.path.join(RACINE, 'dq4_pc', 'libelles.py'), bloc_libelles(officiels, villages))
    remplacer(os.path.join(RACINE, 'outils', 'test_libelles.py'), bloc_test(cartes, fsp, fob))
    print('blocs ecrits')


if __name__ == '__main__':
    main()
