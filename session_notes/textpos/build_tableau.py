import json, collections, statistics
D = json.load(open('mesures.json')); rows = D['rows']
L = json.load(open('/tmp/audit_final/interface/uicache/ui_layout.json'))
NAMES = {int(k): v.get('name', '').replace('Make_', '').replace('()', '') for k, v in L['types'].items()}
PX = 1.008
NB = '   '
import re
def norm(t):
    for c in NB: t = t.replace(c, ' ')
    return re.sub(r'\s+', ' ', t).strip()
def rewrapped(e):
    p = e['P']; vq = e.get('V_quads')
    if not p or not vq: return False
    return [norm(l) for l in re.split(r'\r?\n', p['text']) if norm(l)] != [norm(q[0]) for q in vq if norm(q[0])]
POKER_TEST = ('Abandonner', 'Doubler', 'Garder', 'Changer')

def stat(r):
    P = r['probe']['P']; V = r['probe']['V']
    o = dict(dz=0.0, dx=0.0, ts=1.0, lines=0, ov=0.0, nbsp=False, flags=[], cls='a', n=0, note='')
    if P is None or V is None:
        o['cls'] = '?'; o['note'] = 'rien dessine (sonde)'; return o
    o['dz'] = V['base0'] - P['base0']
    c = r['container']
    for e in r['real']:
        p, v = e['P'], e['V']
        if not p or not v: continue
        o['n'] += 1
        if any(ch in e['s'] for ch in NB): o['nbsp'] = True
        o['dx'] = max(o['dx'], abs(v['xl'] - p['xl']), abs(v['xr'] - p['xr']))
        o['ts'] = min(o['ts'], v['ts'])
        if rewrapped(e): o['lines'] += 1
        if c:
            k, x0, x1, z0, z1 = c
            o['ov'] = max(o['ov'], p['xr'] - x1, x0 - p['xl'])
    f = o['flags']
    if abs(o['dz']) > 0.05: f.append('R')
    if o['nbsp'] and o['dx'] > 0.5: f.append('T')
    if o['ts'] < 0.999: f.append('K')
    if o['lines']: f.append('W')
    if o['ov'] > 0.5 and r['typ'] != 20: f.append('d')      # type 20 : conteneur mal repere par le banc (faux positifs)
    # poker : aucune chaine observee, essais avec des etiquettes plausibles
    if r['typ'] == 48 and r['container'] and r['container'][0] == 'plaque' and r['container'][2] - r['container'][1] < 100 and r['id'] == 4:
        f.append('K*'); o['note'] = 'compression si le libelle depasse la plaque de 72 u (« Abandonner » x0,70 ; « Changer » x0,81 ; « Doubler » x0,85) ; chaines non observees'
    big = (o['ts'] < 0.999) or o['lines'] or ('T' in f) or abs(o['dz']) > 7 or ('K*' in f)
    o['cls'] = 'c' if big else ('b' if 'R' in f else 'a')
    return o

S = [(r, stat(r)) for r in rows]
cls = collections.Counter(o['cls'] for r, o in S)
flg = collections.Counter(f for r, o in S for f in o['flags'])
dz_list = [o['dz'] for r, o in S if 'R' in o['flags']]
by_ls = collections.defaultdict(list)
for r, o in S:
    if 'R' in o['flags']: by_ls[round(r['ls'], 3)].append(o['dz'])

WIN = {
 1: 'D-231 `_push_yes_no` : les deux plaques (côte à côte sur mobile) sont empilées, « Oui » au-dessus de « Non » (dx −135 u, dz −49 u pour la seconde) ; demande de Sylfried du 04/11 ; le texte suit sa plaque, placement relatif inchangé',
 7: '`fit_x` 214 u (CARD_COST_X_MAX) sur la ligne de coût (cellule 0/2) : compression x0,90 ; description (0/1) recoupée à 148 u (`DESCRIPTIONS`)',
 10: 'description (0/4) recoupée à 148 u',
 12: 'bandeau de chapitre : le quad « hyodai1 » (450 x 225) est reconstruit par la visionneuse ; pas de texte déplacé',
 31: 'plaques des noms de monstres : largeur recalculée par `_plate_width`, marge `PLATE_MARGIN` 7 u (les 4 cellules de nom ne sont pas liées à un paramètre)',
 38: 'description (2/3) recoupée à 56 u + compression jusqu’à x0,70 (D-234)',
 46: 'description (4/3) recoupée à 148 u (supposé : fenêtre non ouverte dans le moteur, #219)',
 48: 'étiquettes de bouton comprimées pour tenir dans la plaque, même avec la police d’origine (`BUTTON_COMPRESSION_TYPES`, SVC-03, « police réduite » : choix de Sylfried)',
 53: '`center_menu` : le groupe de boutons est centré en hauteur (dz = 200,1 u) dans un cadre noir ; bouton « Sauvegardes » à la place de « Sauv. cloud » (D-72)',
 54: '`_tab_title` : le titre suit l’onglet (code 2 : +30 u en x, −56 u en z) ; choix du portage, PR #39 ; `CENTERED_WINDOWS` : fenêtre centrée à l’écran',
 55: '`CENTERED_WINDOWS` ; saisie du nom dessinée à la main (positions non retrouvées dans le code)',
 60: 'description (4/4) recoupée à 148 u',
 61: 'description (4/4) recoupée à 148 u (supposé, #219)',
 63: 'description (0/4) recoupée à 148 u (supposé, #219)',
 66: '`_church` : fenêtre reconstruite (plaque de sortie recopiée)',
 70: 'description (0/3) recoupée à 148 u (supposé, #219)',
 80: 'licence dessinée à la main (positions non retrouvées dans le code)',
}

out = []
w = out.append
w('# Position des textes de l’interface : viewer vs jeu mobile (5 novembre 2026)')
w('')
w('Généré par `/tmp/claude-0/-home-claude/45fdf246-f4ad-5078-9633-8be9ccf9e9c9/scratchpad/textpos/build_tableau.py` à partir de `mesures.json` (même dossier). Aucun fichier du dépôt n’a été modifié.')
w('')
w('## Méthode et lecture')
w('')
w('- Banc de mesure : `Render._text` de la visionneuse (vraie police SE-GARRIR), sans écran (headless), unités d’interface (1 u ≈ 1,008 px à 720p, ≈ 1,5 px à 1080p). 465 cellules de texte liées à un paramètre (80 types `Make_*`).')
w('- **P** = mise en page exportée de l’APK pure (aucun écart de la visionneuse). **V** = réglages par défaut. **O** = `DQ_TEXTE_ORIGINAL=1` (ne retire QUE le recentrage vertical ; recoupe, compression et espaces fines restent actifs).')
w('- Écart = V − P. `Δz` : décalage vertical de la ligne de base (positif = vers le haut) ; `Δx` : plus grand décalage d’un bord (gauche ou droit) sur les chaînes réelles ; `ts` : échelle horizontale minimale (1 = pas de compression).')
w('- Chaînes : « observé » = chaînes françaises réelles de ce port (audit du moteur) ; « frère » = chaînes d’une cellule voisine du même groupe et du même numéro ; « aucune » = seulement une chaîne-sonde (`Abcdefgh`), donc position vérifiée, largeur non.')
w('- Drapeaux : **R** recentrage vertical (`text_recentering`, D-143 / D-174, PR #45) ; **T** espaces fines (`THIN_SPACES`, #161 / #162) ; **K** compression horizontale ; **W** recoupe en lignes (descriptions) ; **d** dépasse son plaque/cadre dès le mode jeu (P) : trop long en français, classe d, laissé tel quel (D-133, C-13) ; **K\\*** compression du poker (chaînes non observées).')
w('- Classes : **a** identique (écart < 0,05 u) ; **b** petit écart voulu (recentrage seul, ≤ 7 u) ; **c** écart plus grand ou à question (compression, recoupe, espaces fines, poker) ; **d** dépassement dû à la longueur du français (indépendant de l’écart V − P, signalé en plus par le drapeau).')
w('')
w('## Bilan')
w('')
w('- Cellules : **%d** a, **%d** b, **%d** c (sur %d). Drapeaux : %s.' % (cls['a'], cls['b'], cls['c'], len(S), ', '.join('%s %d' % (k, v) for k, v in sorted(flg.items()))))
w('- Recentrage vertical (R) : %d cellules ; de %.2f à %.2f u (≈ %.1f à %.1f px à 720p), médiane %.2f u. 61 cellules à interligne ≥ 1 : inchangées. Par interligne : %s.' % (len(dz_list), min(dz_list), max(dz_list), min(dz_list) * PX, max(dz_list) * PX, statistics.median(dz_list), ' ; '.join('%.3f → %.1f u (%d)' % (k, statistics.median(v), len(v)) for k, v in sorted(by_ls.items()) if len(v) >= 3)))
w('- Aucun défaut d’ancre mal lue, de ligne manquante, de `\\r\\n` perdu, de tabulation mal calculée ni de texte caché par une plaque n’a été trouvé dans le mode P (mise en page exportée).')
w('')
w('## Écarts au niveau de la fenêtre (le texte bouge avec elle)')
w('')
w('| Type | Nom | Écart |')
w('|---|---|---|')
for t in sorted(WIN):
    w('| %d | %s | %s |' % (t, NAMES.get(t, ''), WIN[t]))
w('')
w('Hors `Make_*` : fenêtre de message du terrain (`MessageWindow`, types de message 0 à 3) : `three_lines` (cadre du type 1 réduit de 188 à 126 u, PR #20), `limit_lines` (canevas de 3 lignes exactes au lieu de 3,5 : bas −240,5 → −227 u, PR #32), `full_text` (types 2 et 3 agrandis de 1/0,9 : 459 → 510 u de large, 122 → 135,6 u de haut, PR #30, D-62), position de la boîte `_dz_message` / `MSG_BOTTOM` −362 / `CB_MSG_BOTTOM` −338 (option `--msg-origine`), échelle globale `UI_ZOOM` 1,12 (toute l’interface : rapports internes inchangés).')
w('')
w('## Par type')
w('')
w('| Type | Nom | Cellules | a | b | c | d | Écart de fenêtre |')
w('|---|---|---|---|---|---|---|---|')
bytype = collections.defaultdict(list)
for r, o in S: bytype[r['typ']].append(o)
for t in sorted(NAMES):
    os_ = bytype.get(t, [])
    cc = collections.Counter(o['cls'] for o in os_)
    dd = sum(1 for o in os_ if 'd' in o['flags'])
    w('| %d | %s | %d | %d | %d | %d | %d | %s |' % (t, NAMES[t], len(os_), cc['a'], cc['b'], cc['c'], dd, 'oui (voir ci-dessus)' if t in WIN else ('sans texte lié' if not os_ else '')))
w('')
w('## Par cellule')
w('')
w('`id/no` : paramètre du jeu. `anc/al` : ancre (0 à 8) / alignement. `ls` : interligne exporté. `tab` : tabSize. `Δz` en u (px à 720p). `dép.` : dépassement du plaque/cadre en mode P (u).')
w('')
w('| Type | id/no | anc/al | ls | tab | chaînes | Δz u (px) | Δx u | ts | dép. | Drapeaux | Cl. |')
w('|---|---|---|---|---|---|---|---|---|---|---|---|')
for r, o in S:
    srcs = {'observe': 'observé', 'frere': 'frère', 'aucune': 'aucune', 'observe+pool2': 'observé+desc.', 'frere+pool2': 'frère+desc.'}[r['src']]
    w('| %d %s | %d/%d | %d/%d | %.3f | %s | %s %d | %+.2f (%+.1f) | %.1f | %.2f | %s | %s | %s |' % (r['typ'], NAMES[r['typ']], r['id'], r['no'], r['anchor'], r['align'], r['ls'], r['tab'] if r['tab'] else '', srcs, o['n'], o['dz'], o['dz'] * PX, o['dx'], o['ts'], ('%.0f' % o['ov']) if o['ov'] > 0.5 else '', ' '.join(o['flags']), o['cls']))
w('')
w('## Chiffres détaillés')
w('')
w('### Descriptions recoupées et comprimées (`DESCRIPTIONS`, 111 à 112 chaînes françaises par cellule : descriptions d’objets du moteur)')
w('')
w('| Cellule | Limite u | Chaînes | Modifiées | dont recoupées | dont comprimées | Dépassent en mode jeu | Dépassent en V | ts min |')
w('|---|---|---|---|---|---|---|---|---|')
KEYS = {(7,0,1):148,(10,0,4):148,(38,2,3):56,(46,4,3):148,(60,4,4):148,(61,4,4):148,(63,0,4):148,(70,0,3):148}
for r in rows:
    k = (r['typ'], r['id'], r['no'])
    if k not in KEYS: continue
    lim = KEYS[k]; n = ch = ovp = ovv = rw = cp = 0; mt = 1.0
    for e in r['real']:
        p, v = e['P'], e['V']
        if not p or not v: continue
        n += 1
        if v['lines'] != p['lines'] or v['ts'] < 0.999 or abs(v['xl'] - p['xl']) > 0.05 or abs(v['xr'] - p['xr']) > 0.05: ch += 1
        if p['xr'] > lim + 0.5: ovp += 1
        if v['xr'] > lim + 0.5: ovv += 1
        if rewrapped(e): rw += 1
        if v['ts'] < 0.999: cp += 1
        mt = min(mt, v['ts'])
    w('| %d/%d/%d %s | %g | %d | %d | %d | %d | %d | %d | %.2f |' % (k + (r['name'], lim, n, ch, rw, cp, ovp, ovv, mt)))
w('')
w('### Poker (type 48, plaques de 72 u des boutons 4/0 à 4/5)')
w('')
w('| Libellé | Largeur jeu | Largeur viewer | ts |')
w('|---|---|---|---|')
w('| Abandonner | 103,4 | 72,4 | 0,700 |')
w('| Changer | 71,6 | 58,0 | 0,810 |')
w('| Doubler | 68,6 | 58,0 | 0,845 |')
w('| Garder | 59,7 | 58,0 | 0,972 |')
w('')
w('La compression vise toutes les cellules du type 48, pas seulement les plaques : la cellule 2/0 (ligne d’information, alignée à droite) est comprimée de la même façon si son texte dépasse (supposé : effet de bord, non voulu).')
w('')
w('## Textes propres à la visionneuse (absents du jeu d’origine, non jugés)')
w('')
w('- Menu Échap (`dq4_pc/menus/pause.py`, textes `texts_en/pause.py`) : reprendre, états instantanés, affichage, son, commandes, retour au titre ; fenêtres noires et curseur du jeu, textes dessinés par la visionneuse.')
w('- Historique (`dq4_pc/menus/ui_history.py`) : deux onglets (Dialogues, Combats), case « Favoris seulement » ; chaque entrée dans une boîte de dialogue du jeu (cadre 452 x 126 u) avec la police SE-GARRIR.')
w('- Écran « Sauvegardes » (`dq4_pc/menus/saves_screen.py`) : exporter / importer, remplace « Sauv. cloud » ; dessiné dans le style des autres menus.')
w('- Notifications (`toast`) : « État N enregistré / chargé / vide », « Sauvegarde impossible… », erreurs ; lignes d’information F1 (en haut à droite) ; bouton « Vitesse de combat » (`hud_mobile.py`).')
w('- Saisie du nom et licence (type 80) : dessinées à la main, positions non retrouvées dans le code (mise en page inventée).')
w('- Éditeur d’interface (aperçu), `menu_display.py` : menus simples en Pillow/pyglet pour les fenêtres sans mise en page.')
w('')
w('## Non couvert ou non vérifié')
w('')
w('- Aucune chaîne réelle observée pour les types 24, 27, 28, 34, 39, 41, 42, 44 à 53 (casino), 55, 62 à 65, 67, 69 à 71, 79 : position vérifiée seulement avec la sonde `Abcdefgh`.')
w('- Ancre basse (anchor 7, 12 cellules) et `\\n` final : le modèle n’est vérifié que sur capture mobile pour les ancres haute et milieu. Une chaîne qui finit par `\\n` dans une cellule à ancre milieu ou basse (ex. 10/0/3 « Disparaît après une\\nseule utilisation.\\n ») compte une ligne vide en plus (décalage de 11,8 u si Unity l’ignore) : à vérifier sur capture.')
w('- Les cellules à ancre milieu du type 4, 5, 30, 32, 46, 60, 61, 67 ont l’ancre décalée de +18 à +26 u du centre de la plaque (zone d’icône) : cohérent d’une fenêtre à l’autre, supposé voulu par la mise en page.')
w('- Issue #138 (premier bouton d’une liste plus haut dans sa plaque) : les décalages de texte sont identiques d’une ligne à l’autre dans le banc, pas de cause côté visionneuse trouvée ; à voir sous Windows.')
open('tableau_types.md', 'w').write('\n'.join(out) + '\n')
print(len(out), 'lignes', cls, flg)
