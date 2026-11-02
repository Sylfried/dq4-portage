"""Reconstruit, a partir de l'etat final du worktree, une suite de commits : bug s, P1 eglise, P2 secousse/curseur, P3 icones d'etat, P4 marques, P5 type 54.
Chaque etape = etat final moins les morceaux des etapes suivantes. Usage : python3 build_commits.py [--dry]"""
import subprocess, sys, os, re
WT = '/home/claude/wt-audit'; UIP = WT + '/dq4_pc/ui_menu.py'; FEP = WT + '/dq4_pc/fenetre.py'
FIN_UI = open(UIP, encoding='utf-8').read(); FIN_FE = open(FEP, encoding='utf-8').read()
HEAD_UI = subprocess.run(['git', '-C', WT, 'show', 'HEAD:dq4_pc/ui_menu.py'], capture_output=True, text=True).stdout
HEAD_FE = subprocess.run(['git', '-C', WT, 'show', 'HEAD:dq4_pc/fenetre.py'], capture_output=True, text=True).stdout
def bloc(txt, deb, fin):
    i = txt.index(deb); j = txt.index(fin, i + 1); return txt[i:j]
def ligne(txt, debut):
    i = txt.index(debut); j = txt.index('\n', i) + 1; return txt[i:j]
def lignes(txt, debut, n):
    i = txt.index(debut); j = i
    for _ in range(n): j = txt.index('\n', j) + 1
    return txt[i:j]
# morceaux : (feature, fichier, texte final, texte de base)
M = []
def add(f, fic, final, base=''):
    assert (FIN_UI if fic == 'ui' else FIN_FE).count(final) == 1, (f, final[:80]); M.append((f, fic, final, base))
# --- bug s
add(0, 'ui', "            if cu.get('cls', '').endswith('ICityMap'): return                                       # fenetre de carte (type 25) : le nom de la texture du plan (Menu/map) est pose par la visionneuse (nom_carte)\n",
    ligne(HEAD_UI, "            if cu.get('cls', '').endswith('ICityMap')"))
# --- P1 eglise
add(1, 'ui', lignes(FIN_UI, "        self.parts = list(self.t['parts'])", 3), "        self.parts = self.t['parts']\n")
add(1, 'ui', ligne(FIN_UI, "        if self.eglise: self.txt_eglise"))
add(1, 'ui', ligne(FIN_UI, "        if self.eglise and i == 0:"))
add(1, 'ui', bloc(FIN_UI, "    # ---- eglise (type 66", "    # ---- combat : plaques des membres"))
# --- P2 combat 29
add(2, 'ui', ligne(FIN_UI, "        self.statut = nom.startswith"))
add(2, 'ui', ligne(FIN_UI, "        elif self.statut: self._statut"))
add(2, 'ui', bloc(FIN_UI, "    # ---- combat : plaques des membres", "    # ---- icones d'etat"))
add(2, 'ui', bloc(FIN_UI, "    def tick(self):\n        \"\"\"Une image du jeu : animations", "\n\nRESSOURCES"))
add(2, 'fe', ligne(FIN_FE, "        if self.ui_g: self.ui_g.tick()"))
# --- P3 icones d'etat
add(3, 'ui', ligne(FIN_UI, "            if cu.get('cls', '').endswith('StatusIconChanger')"))
add(3, 'ui', bloc(FIN_UI, "    # ---- icones d'etat", "    # ---- combat : marques de groupe"))
# --- P4 marques
add(4, 'ui', lignes(FIN_UI, "        self.noms = nom.startswith", 3))
add(4, 'ui', ligne(FIN_UI, "        elif self.noms and i == 4"))
add(4, 'ui', bloc(FIN_UI, "    # ---- combat : marques de groupe", "    # ---- menu de depart"))
add(4, 'ui', bloc(FIN_UI, "        self._reset_marques(); marques = self._marques(); k = 0", "\n    def boutons("))
for ancien, nouveau in (("if nd['vtx'] and nd['mats'] and not nd.get('marque') and self.visible(nd['id']) for v in nd['vtx']]\n        return min(zs) if zs else 0.0", "if nd['vtx'] and nd['mats'] and self.visible(nd['id']) for v in nd['vtx']]\n        return min(zs) if zs else 0.0"),
                        ("if nd['vtx'] and nd['mats'] and not nd.get('marque') and self.visible(nd['id']) for v in nd['vtx']]\n        return (min(zs), max(zs)) if zs else None", "if nd['vtx'] and nd['mats'] and self.visible(nd['id']) for v in nd['vtx']]\n        return (min(zs), max(zs)) if zs else None"),
                        ("            if nd['vtx'] and nd['mats'] and not nd.get('marque') and self.visible(nd['id']):\n                xs =", "            if nd['vtx'] and nd['mats'] and self.visible(nd['id']):\n                xs =")):
    add(4, 'ui', ancien, nouveau)
add(4, 'ui', ligne(FIN_UI, "    proj = None "), ligne(HEAD_UI, "    proj = None "))
add(4, 'fe', "    def _ui_x_monstres(self, masque, liste=False):\n", "    def _ui_x_monstres(self, masque):\n")
add(4, 'fe', ligne(FIN_FE, "        \"\"\"Abscisses (unites d'interface, colonne portrait"), ligne(HEAD_FE, "        \"\"\"Abscisses (unites d'interface, colonne portrait"))
add(4, 'fe', "        if liste: return xs\n")
# --- P5 type 54
add(5, 'ui', ligne(FIN_UI, "        self.debut = nom.startswith"))
add(5, 'ui', ligne(FIN_UI, "        elif self.debut and i == 3"))
add(5, 'ui', bloc(FIN_UI, "    # ---- menu de depart", "    def selection(self, bouton):"))
ORIG = [m for m in __import__('re').findall(r'^    def (\w+)\(', HEAD_UI, __import__('re').M)]
def etat(stage):
    ui, fe = FIN_UI, FIN_FE
    for f, fic, final, base in M:
        if f > stage:
            if fic == 'ui': ui = ui.replace(final, base, 1)
            else: fe = fe.replace(final, base, 1)
    return ui, fe
MSG = {0: ("Fenêtre de carte : param_int n'affecte plus une variable inexistante (NameError)", "La branche ICityMap de Fenetre.param_int affectait `s`, qui n'existe pas dans cette méthode : NameError dès qu'un\nparamètre entier de la fenêtre de carte (type 25) arrivait. Le nom du plan est posé par la visionneuse (nom_carte,\nfenetre.py) : la branche se contente donc de rendre la main."),
       1: ("Église (type 66) : les cinq (ou quatre) boutons sont construits dans la fenêtre", "L'exporteur de mise en page ne voit que le titre et le bouton « Rien » : le jeu fait les boutons dans le code de\nMake_ChurchRoot (Sub_ShopButton). Fenetre les refait au code 0 du moteur (0 : cinq boutons, sinon quatre) d'après la\ntable relevée dans le code Unity : plaque à neuf découpes copiée de « Rien » (largeur 177,1 ou 110 + bordures),\nnuméro de bouton = rang, manette 16, texte centré ; les textes (id, 0) y sont rebranchés (même s'ils arrivent avant\nle code). Aucune régénération de ui_layout.json : les nœuds sont retrouvés par structure, sans identifiant codé en dur.\nTesté avec le moteur (sauvegarde 1, église mak1f1) : chaque bouton, au clic comme au clavier, envoie son numéro et le prêtre répond en conséquence."),
       2: ("Combat : secousse des plaques de membres, rouge de la barre, clignotement de la flèche", "Type 29 (Make_BattleUpStatus) : le code 8 lance ShakeFrame (8 images, table s_shakeTable) sur la plaque entière (cadre,\ntextes, barre, visage), un pas par image du jeu (30 Hz : Gestionnaire.tick, appelé après chaque pas du moteur) ; à la fin,\nRedApply de la barre PV. La flèche du membre qui agit (code 5) alterne les icônes 2 et 3 toutes les 0,7 s en temps réel\n(BattleUpCursor.c_waitTime) et repart de l'icône 2 à chaque déplacement (ForceUpdate, appelé par le code 5 d'après le\ndésassemblage de b__0). Elle n'était jamais affichée : l'exporteur ne voit pas le SetActive(true) du code >= 0, elle est\nmaintenant montrée par ce code."),
       3: ("Icônes d'état : StatusIconChanger (mort, poison, sort scellé, couleur)", "Valeur = icône | (couleur << 16) : première icône de la feuille 13 = v & 3 (croix = mort, tête de mort = poison), seconde =\nœil si le bit 2 est levé, couleur de la palette de l'en-tête sur la matière de la feuille 13 (jaune = à l'article de la mort,\nrouge = mort). Types 4, 5, 20, 21, 46, 60, 61, 67 ; le rang de la partie (deux icônes de la feuille 13) donne l'id.\nVérifié avec le moteur : un membre mort et un empoisonné dans la liste de la Résurrection."),
       4: ("Combat : marques de groupe sous les monstres (MonsterMarkList)", "Au choix de cible (plaque de code 2), une marque de la couleur du groupe (icône id + 5 de la feuille 6) par monstre du\nmasque, à l'abscisse du monstre projetée par la caméra de combat, z = -64 ; remises à zéro par le code 4. Les marques ne\ncomptent pas dans l'étendue de la fenêtre (elles ne doivent pas changer l'échelle de l'interface). _ui_x_monstres(masque, liste)\nrend la liste des abscisses."),
       5: ("Menu de départ (type 54) : cadre du titre selon le code et nombre de boutons", "Code 3 : IFrame.Change(0xDB + code) (219, 220, 221) ; code 2 : un seul bouton, plus bas (z = -266,25 avec ses textes), les\ndeux autres cachés. Le bouton retour reste où il est.")}
FOOT = "\n\nCo-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>\nClaude-Session: https://claude.ai/code/session_014GF7TUJhoy5Df7FLvSTYtw\n"
if '--dry' in sys.argv:
    for st in range(6):
        ui, fe = etat(st); open('/tmp/etat_ui_%d.py' % st, 'w', encoding='utf-8').write(ui); open('/tmp/etat_fe_%d.py' % st, 'w', encoding='utf-8').write(fe)
        for nom, t in (('ui', ui), ('fe', fe)):
            try: compile(t, nom, 'exec')
            except SyntaxError as e: print('ERREUR stage', st, nom, e)
    ui, fe = etat(5); assert ui == FIN_UI and fe == FIN_FE
    for st in range(6):
        u, _ = etat(st); manque = [m for m in ORIG if '    def %s(' % m not in u]
        assert not manque, (st, manque)
    print('dry ok'); sys.exit()
for st in range(6):
    ui, fe = etat(st); open(UIP, 'w', encoding='utf-8').write(ui); open(FEP, 'w', encoding='utf-8').write(fe)
    subprocess.run(['python3', '-m', 'py_compile', UIP, FEP], check=True)
    subprocess.run(['git', '-C', WT, 'add', 'dq4_pc/ui_menu.py', 'dq4_pc/fenetre.py'], check=True)
    t, c = MSG[st]; subprocess.run(['git', '-C', WT, 'commit', '-m', t + '\n\n' + c + FOOT], check=True)
assert open(UIP, encoding='utf-8').read() == FIN_UI and open(FEP, encoding='utf-8').read() == FIN_FE
print('commits ok')
