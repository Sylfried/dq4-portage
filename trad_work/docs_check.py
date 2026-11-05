"""usage: docs_check.py <morceau.in.md> <morceau.out.md> -> problemes (code 1 si bloquants)"""
import re, sys
a = open(sys.argv[1], encoding='utf-8').read(); b = open(sys.argv[2], encoding='utf-8').read()
block = 0; warn = 0
def count(pat, s, flags=re.M): return len(re.findall(pat, s, flags))
def heads(s): return [re.match(r'(#+) ', l).group(1) for l in s.split('\n') if re.match(r'#{1,6} ', l)] if True else []
# les titres dans les blocs de code ne comptent pas : on retire les blocs
def strip_code(s): return re.sub(r'^```.*?^```', '', s, flags=re.M | re.S)
sa, sb = strip_code(a), strip_code(b)
if heads(sa) != heads(sb): print('TITRES : niveaux ou nombre differents', len(heads(sa)), len(heads(sb))); block += 1
if count(r'^```', a) != count(r'^```', b): print('BLOCS DE CODE : nombre de lignes ``` different'); block += 1
ta = [l for l in a.split('\n') if l.startswith('|')]; tb = [l for l in b.split('\n') if l.startswith('|')]
if len(ta) != len(tb): print('TABLEAUX : lignes de tableau', len(ta), '->', len(tb)); block += 1
else:
    for x, y in zip(ta, tb):
        if x.count('|') != y.count('|') and not re.search(r'`[^`]*\|[^`]*`', x): print('TABLEAU : nombre de colonnes different :', x[:60].replace('\n', ' ')); block += 1; break
if a.count('\n') != b.count('\n') and abs(a.count('\n') - b.count('\n')) > max(5, a.count('\n') // 10):
    print('LIGNES : nombre de lignes tres different', a.count('\n'), '->', b.count('\n')); warn += 1
la = re.findall(r'\]\(([^)]+)\)', a); lb = re.findall(r'\]\(([^)]+)\)', b)
if la != lb: print('LIENS : cibles differentes', [x for x in la if x not in lb][:3]); block += 1
TOK = re.compile(r"0x[0-9A-Fa-f]+|\d+(?:[.,]\d+)?|[A-Za-z]+_[A-Za-z0-9_]+|[a-z]+[A-Z][A-Za-z0-9]*|#\d+|D-\d+|[A-Z]+-\d+|`[^`\n]+`")
def norm(s): return re.sub(r'(\d),(\d)', r'\1.\2', s)
nb = norm(b)
miss = [t for t in TOK.findall(norm(a)) if t not in nb]
if miss: print('ELEMENTS PERDUS', len(miss), miss[:12]); warn += 1
FR = re.compile(r"\b(le|la|les|des|une|est|sont|pour|dans|que|qui|pas|sur|avec|sans|cette|mais|comme|puis|quand|apres|avant|elle|nous|vous|ils|aux|donc|tout|tous|toute|chaque|etait|fait|faire|peut|doit|ou|et)\b|[àâçéèêëîïôûùüÿœ]")
cnt = 0; ex = []
for l in sb.split('\n'):
    t = re.sub(r'«[^»]*»|`[^`]*`|"[^"]*"|\([^)]*\)|\[[^\]]*\]\([^)]*\)', ' ', l)
    f = FR.findall(t)
    if len(f) >= 3: cnt += 1; ex.append(l.strip()[:70])
if cnt: print('FRANCAIS ?', cnt, 'lignes, par ex.', ex[:3]); warn += 1
print('bloquants:', block, 'avertissements:', warn); sys.exit(1 if block else 0)
