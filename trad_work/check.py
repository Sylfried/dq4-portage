"""usage: check.py batch_NN.in.txt batch_NN.out.txt  -> liste des problemes (code de sortie 1 s'il y en a de bloquants)"""
import os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import trad_lib as T
def read(path):
    out = {}; kinds = {}; cur = None; buf = []
    for line in open(path, encoding='utf-8').read().split('\n'):
        if line.startswith('@@ '):
            if cur: out[cur] = '\n'.join(buf).rstrip('\n')
            p = line.split(); cur = p[1]; kinds[cur] = p[2] if len(p) > 2 else '?'; buf = []
        elif line.startswith('## FILE '):
            if cur: out[cur] = '\n'.join(buf).rstrip('\n'); cur = None; buf = []
        elif cur is not None: buf.append(line)
    if cur: out[cur] = '\n'.join(buf).rstrip('\n')
    return out, kinds
a, ka = read(sys.argv[1]); b, kb = read(sys.argv[2])
block = 0; warn = 0
for i in a:
    if i not in b: print('MANQUANT', i, repr(a[i][:60])); block += 1
for i in b:
    if i not in a: print('EN TROP', i); block += 1
FR = re.compile(r"\b(le|la|les|des|une|est|sont|pour|dans|que|qui|pas|sur|avec|sans|cette|mais|comme|puis|quand|apres|avant|elle|nous|vous|ils|aux|donc|tout|tous|toute|chaque|etait|fait|faire|peut|doit)\b|[àâçéèêëîïôûùüÿœ]")
TOK = re.compile(r"0x[0-9A-Fa-f]+|\d+(?:[.,]\d+)?|[A-Za-z]+_[A-Za-z0-9_]+|[a-z]+[A-Z][A-Za-z0-9]*|#\d+|D-\d+|`[^`]+`")
def norm(s): return re.sub(r'(\d),(\d)', r'\1.\2', s)
def strip_quotes(s): return re.sub(r'«[^»]*»|`[^`]*`|"[^"]*"', ' ', s)
for i in a:
    if i not in b: continue
    src, dst = a[i], b[i]
    if ka[i] == 't' and '\n' in dst.strip(): print('LIGNES', i, 'commentaire de fin de ligne sur plusieurs lignes :', repr(dst[:70])); block += 1
    miss = [t for t in TOK.findall(norm(src)) if t not in norm(dst)]
    if miss: print('ELEMENTS PERDUS', i, miss[:6], '|', repr(src[:50])); warn += 1
    fr = FR.findall(strip_quotes(dst))
    if len(fr) >= 2 or (fr and any(ord(c) > 127 for c in ''.join(x if isinstance(x,str) else x[0] for x in fr))):
        print('FRANCAIS ?', i, repr(dst[:80])); warn += 1
    if dst.strip() == '' : print('VIDE', i); block += 1
print('bloquants:', block, 'avertissements:', warn)
sys.exit(1 if block else 0)
