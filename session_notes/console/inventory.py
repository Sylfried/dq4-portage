"""Inventory of strings flowing to console sinks (AST). usage: inventory.py ROOT > out.tsv"""
import ast, os, re, sys, json

ROOT = sys.argv[1]
ACC = re.compile('[àâäçéèêëîïôöùûüÿœÀÂÇÉÈÊËÎÏÔÙÛÜŒ«»…]')
FW = {'le','la','les','des','du','une','un','et','ou','pour','dans','sur','avec','sans','est','pas','ces','aux','vos','votre','tes','tous','toutes','quand','comme','mais','donc','sont','chaque','sinon','aucun','aucune','par','defaut','fichier','erreur','chargement','impossible','dossier','jeu','image','images','carte','combat','lance','lancez','mets','manque','introuvable','trouve','trouvee','absent','absente','dossiers','fichiers','non','oui','ni','ce','cette','qui','que','au','en','se','sa','son','ses','leur','ete','etat','sauvegarde','fenetre','ecran','moteur','texte','taille','lecture','donnees','resultat','resultats','premier','deuxieme','touche','touches','nombre','pas','tout','tous','mesure','cherche','cherche','avant','apres','vers','depuis','aussi','seulement','fait','faire','arret','fin','debut','temps','duree','ecart','valeur','valeurs','ligne','lignes','octets','capture','captures','decor','monstre','monstres','sprite','texture','textures','son','musique','bruitage'}
SINKS = {'print','log','note','_wait','warn','warning','exit','SystemExit','error','info','debug','critical','write','say','_log','verbose','out','emit','echo'}

def has_fr(s):
    if ACC.search(s): return True
    ws = re.findall(r"[a-zA-Z]+", s.lower())
    return any(w in FW for w in ws)

class V(ast.NodeVisitor):
    def __init__(self, path, src):
        self.path = path; self.rows = []; self.src = src
        self.doc_ids = set()
    def mark_docs(self, tree):
        for n in ast.walk(tree):
            if isinstance(n, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                b = n.body
                if b and isinstance(b[0], ast.Expr) and isinstance(b[0].value, ast.Constant) and isinstance(b[0].value.value, str):
                    self.doc_ids.add(id(b[0].value))

def fname(f):
    if isinstance(f, ast.Name): return f.id
    if isinstance(f, ast.Attribute): return f.attr
    return None

def consts(node):
    """all str Constant nodes inside node"""
    out = []
    for n in ast.walk(node):
        if isinstance(n, ast.Constant) and isinstance(n.value, str): out.append(n)
    return out

def main():
    allrows = []
    for d, _, fs in os.walk(ROOT):
        if '/.git' in d or '__pycache__' in d: continue
        for f in sorted(fs):
            if not f.endswith('.py'): continue
            p = os.path.join(d, f); rel = os.path.relpath(p, ROOT)
            if rel.startswith('tests/') or '/texts_en/' in rel or rel.endswith('language.py'): continue
            src = open(p, encoding='utf-8').read()
            try: tree = ast.parse(src)
            except SyntaxError as e: print('SYNTAX', rel, e, file=sys.stderr); continue
            v = V(p, src); v.mark_docs(tree)
            parents = {id(c): n for n in ast.walk(tree) for c in ast.iter_child_nodes(n)}
            seen = set()
            assigns = {}
            for node in ast.walk(tree):
                if isinstance(node, ast.Assign):
                    for t in node.targets:
                        if isinstance(t, ast.Name): assigns.setdefault(t.id, []).append(node.value)
                elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.value is not None:
                    assigns.setdefault(node.target.id, []).append(node.value)
            def role(n, call):
                x = n
                while id(x) in parents and parents[id(x)] is not call:
                    pnode = parents[id(x)]
                    if isinstance(pnode, (ast.JoinedStr, ast.IfExp, ast.Starred, ast.Tuple, ast.List)): pass
                    elif isinstance(pnode, ast.BinOp) and isinstance(pnode.op, (ast.Mod, ast.Add)): pass
                    elif isinstance(pnode, ast.Call) and (fname(pnode.func) in ('tr', 'N_')): pass
                    elif isinstance(pnode, ast.Call) and fname(pnode.func) == 'format' and isinstance(pnode.func, ast.Attribute) and pnode.func.value is x: pass
                    else: return 'other'
                    x = pnode
                return 'text'
            def add(kind, n, call):
                key = (n.lineno, n.col_offset)
                if key in seen or id(n) in v.doc_ids: return
                seen.add(key)
                allrows.append((rel, n.lineno, n.col_offset, kind + '/' + role(n, call), n.value))
            # parents for scope lookups
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    nm = fname(node.func)
                    if nm in SINKS:
                        # write only on stderr/stdout
                        for a in list(node.args):
                            for c in consts(a): add('sink:' + nm, c, node)
                            # variable flow: names used in the argument -> string assignments in the same scope chain
                            for nn in ast.walk(a):
                                if isinstance(nn, ast.Name) and not isinstance(nn.ctx, ast.Store):
                                    for asg in assigns.get(nn.id, ()):
                                        for c in consts(asg): add('flow:' + nm + ':' + nn.id, c, node)
                        for k in node.keywords:
                            if k.arg in ('file','flush','end','sep'): continue
                            for c in consts(k.value): add('sink:' + nm, c, node)
                    elif nm in ('add_argument', 'ArgumentParser', 'add_parser', 'add_argument_group', 'add_subparsers', 'add_mutually_exclusive_group'):
                        for k in node.keywords:
                            if k.arg in ('help','description','epilog','usage','metavar','title'):
                                for c in consts(k.value): add('argparse:' + k.arg, c, node)
                        for a in node.args[1:] if nm == 'add_argument' else []:
                            pass
                elif isinstance(node, ast.Raise) and node.exc is not None and isinstance(node.exc, ast.Call):
                    for a in node.exc.args:
                        for c in consts(a): add('raise:' + (fname(node.exc.func) or '?'), c, node)
                elif isinstance(node, ast.Assert) and node.msg is not None:
                    for c in consts(node.msg): add('assert', c, node)
    for r in allrows: print('\t'.join([r[0], str(r[1]), str(r[2]), r[3], json.dumps(r[4], ensure_ascii=False)]))

main()
