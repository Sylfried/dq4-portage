"""Ecrit couverture.md a partir des JSON (voir gen_tables.py, an_vis.py)."""
import json, os, re, struct, collections, datetime
D = '/tmp/claude-0/-home-claude/45fdf246-f4ad-5078-9633-8be9ccf9e9c9/scratchpad/anim/'
R = D + 'out/'
tb = json.load(open(R + 'tables.json'))
sw = json.load(open(R + 'sweep_all.json'))
items = {int(k): v for k, v in json.load(open(R + 'item_names.json')).items()}
iu = json.load(open(R + 'items_use.json'))
rows = json.load(open(R + 'actions_raw.json'))['rows']
names = {int(k): v for k, v in json.load(open(R + 'action_names.json')).items()}
vis = {}
for f in ('vis_a.json', 'vis_i.json'):
    if os.path.exists(R + f): vis.update({int(k): v for k, v in json.load(open(R + f)).items()})
PID = {1: 'Héros', 2: 'Héroïne', 3: 'Ragnar', 4: 'Alina', 5: 'Kiryl', 6: 'Borya', 7: 'Torneko', 8: 'Mina', 9: 'Maya', 25: 'Psaro'}
COMMON = {400, 401, 402, 403, 404, 712}
NOMESH = {411, 413}      # modele charge (paquet 21) mais jamais de maillage (paquet 22) : verifie par scripts/t12.py (out/t12_all.json)
FD = json.load(open(R + 'forced_d.json'))
def eff_of(a): return struct.unpack('<H', bytes.fromhex(rows[a])[0x26:0x28])[0]
def res(k):
    v = sw.get(str(k))
    if v is None: return None
    mods = sorted(int(m) for m in v['models'] if m != '-1'); fb = sorted({x[1][1] for x in v['fbx'] if x[1][1] >= 0})
    se = sorted({s for _, s in v['se']} - COMMON - {0}); return dict(mod=mods, fbx=fb, tint=v['tint'][1], se=se, col=v['n_col'])
def ressources(k):
    r = res(k)
    if r is None: return '—'
    if k in NOMESH: return 'modèle m%d chargé, aucun maillage envoyé ; SE %s' % (5000 + k, ','.join(map(str, r['se'])) or 'générique seul')
    p = []
    if r['mod']: p.append('maillage ' + '/'.join('m%d' % m for m in r['mod']))
    if r['fbx']: p.append('fbx ' + '/'.join('c%d' % f for f in r['fbx']))
    if r['tint']: p.append('teinte plein écran (%d paquets 33)' % r['tint'])
    if r['col']: p.append('couleur plein écran (%d paquets 25)' % r['col'])
    p.append('SE ' + ','.join(map(str, r['se'])) if r['se'] else 'SE générique seul')
    return ' ; '.join(p)
def rendu(k):
    r = res(k)
    if k in NOMESH: return 'rien à dessiner : le moteur n\'envoie aucun maillage (relevé en réel sur 200 images), donc rien non plus dans le jeu'
    if k == 0: return 'rien à dessiner (le jeu ne demande aucun effet)'
    if r is None: return 'inconnu'
    vv = vis.get(k)
    cap = ''
    if vv and vv['seen']: cap = ' ; capture réelle : maillage vu sur %d des %d images prises, remplissage max %.0f %%' % (vv['seen'], vv['shots'], 100 * vv['fill'])
    if r['fbx'] and r['mod']: return '**partiel** : maillage dessiné, fbx non dessiné' + cap
    if r['fbx']: return '**ABSENT** : fbx seul, jamais dessiné' + (' (seule la teinte plein écran est jouée)' if r['tint'] else ' (rien d\'affiché, seulement le son)') + cap
    if r['mod']: return 'OK : maillage dessiné' + cap
    return 'rien (teinte / son)'
L = []
w = L.append
w('# Couverture des animations de combat des alliés (05/11/2026)\n')
w('Sources : moteur natif réel sous Unicorn (`libdq4core.so`, sauvegarde du chapitre 1), visionneuse réelle sous Xvfb, tables du moteur, fichiers de textes du patch. Aucune modification du dépôt. Détail des méthodes en fin de fichier.\n')
w('Légende des états : **OK** = tout ce que le moteur envoie est dessiné ; **partiel** = une partie seulement ; **ABSENT** = rien de visuel ; **rien à dessiner** = le moteur ne demande aucun effet (identique au jeu).\n')
w('## 1. Sorts et techniques des alliés (actions apprises, table des niveaux du moteur)\n')
w('Lanceurs : numéros de joueur du moteur (1 Héros, 2 Héroïne, 3 Ragnar, 4 Alina, 5 Kiryl, 6 Borya, 7 Torneko, 8 Mina, 9 Maya, 25 Psaro ; noms lus dans `b1001000.mpt`). « Effet » = identifiant demandé à `BattleEffectManager::setupEffect` (confirmé en combat réel pour chaque action : colonne vérifiée = oui).\n')
w('| Action | Nom (patch FR) | Lanceurs | Effet | Ressources envoyées au viewer | Rendu viewer | Vérifié en combat réel |')
w('|---|---|---|---|---|---|---|')
for o in tb:
    a = o['action']
    if 196 <= a <= 216: continue
    if a in (71, 231, 232, 233, 234, 235) or a in (111, 112, 115, 116, 256, 33): continue
    eff = o['eff_real'] if o['eff_real'] not in (None, 303) else 0
    if a == 47: eff = 34
    if a == 48: eff = 0
    nm = o['name'] or '(sans nom)'
    ln = ', '.join(PID.get(p, str(p)) for p in o['pids']) or '—'
    ver = 'oui' if o['forced'] else 'non'
    if eff == 0:
        se = [s for s in o['se_forced'] if s not in (306, 412)]
        w('| %d | %s | %s | aucun | SE %s | rien à dessiner (aucun effet demandé ; message + son) | %s |' % (a, nm, ln, ','.join(map(str, se)) or 'aucun', ver))
    else:
        w('| %d | %s | %s | %d | %s | %s | %s |' % (a, nm, ln, eff, ressources(eff), rendu(eff), ver))
w('')
w('Sorts de terrain (196-216 : Téléportation, Évac\', Coup d\'œil, Passage sûr, Protection sacrée, Tic-tac, Mappille, Détectrésor, Fouille, Discreto, Sifflet, soins du menu Magie) : aucun effet de combat (effet 0, pas de paquet), non utilisables au combat.\n')
w('## 2. Attaques d\'arme, critiques, esquives\n')
w('| Cas | Action | Effet | Ressources | Rendu viewer |')
w('|---|---|---|---|---|')
w('| Attaque normale | 71 (« Attaquer ») | 300 + numéro de l\'arme équipée (Ragnar, épée de cuivre n° 3 : effet 303 relevé en réel) ; mains nues : 343 / 345 d\'après le désassemblage de `getWeaponEffectID` (non rejoué) | maillage m5301…m5345 (45 effets, tous présents) ; SE 410-454 selon l\'arme | OK (maillages dessinés : audit du 05/11 et capture réelle de l\'effet 303) |')
w('| Variantes d\'attaque | 231, 233, 234, 235 | 300 + arme (même message « attaque ! ») | idem | OK |')
w('| Coup critique | 232 | arme + **344** demandés à la même image (« Coup critique ! ») | maillage m5344 ; SE 407 | OK (maillage m5344 dessiné) ; son 0 pour l\'effet 344 lui-même |')
w('| Esquive / « raté » | — | aucun effet demandé (messages seulement) | — | rien à dessiner |')
w('')
w('## 3. Objets à effet utilisables en combat (20 objets du joueur ; chacun est joué dans le vrai moteur par l\'action d\'objet du numéro indiqué : out/forced_d.json)\n')
w('| Objet (n°) | Action | Effet | Ressources | Rendu viewer |')
w('|---|---|---|---|---|')
for i in sorted(int(k) for k, v in iu.items() if v['isBattleUse'] & 0xff and int(k) < 174):
    a = iu[str(i)]['getBattleUseAction']; e = eff_of(a) if a < len(rows) else 0
    nm = items.get(i, '?')
    if e:
        rs = ressources(e)
        if e in NOMESH: rs = 'modèle m%d chargé, aucun maillage envoyé ; SE %s' % (5000 + e, ','.join(map(str, sorted({x for _, x in FD.get(str(a), {}).get('se', [])} - COMMON - {0, 412, 306}))) or 'aucun')
        w('| %s (%d) | %d | %d | %s | %s |' % (nm, i, a, e, rs, rendu(e)))
    else:
        se = sorted({x for _, x in FD.get(str(a), {}).get('se', [])} - COMMON - {0, 412, 306})
        w('| %s (%d) | %d | aucun | SE %s | rien à dessiner (aucun effet demandé ; message + son) |' % (nm, i, a, ','.join(map(str, se)) or 'aucun'))
w('')
w('Numéros d\'objet 207 (action 1) et 216 (action 257, « exhale … ») : sans nom dans les textes des objets du joueur (la table de noms s\'arrête à 173), donc des données internes, non offertes au joueur ; leurs effets (Flamme, aucun) sont couverts ailleurs. Les objets sans effet de combat (herbes, potions…) passent par les actions de soin : message + son 501, aucun effet.')
w('')
open(D + 'couverture_part1.md', 'w').write('\n'.join(L))
print(len(L))
