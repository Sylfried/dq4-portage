"""usage: find_french.py <depot> [--ids] : liste les commentaires / docstrings qui contiennent encore du francais (textes ajoutes apres l'extraction des lots).
Ecrit `batch_new.in.txt` (format des lots) dans le dossier courant pour les traduire avec le meme prompt que les autres lots."""
import os, re, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import trad_lib as T
FR = re.compile(r"\b(le|la|les|des|une|est|sont|pour|dans|que|qui|pas|sur|avec|sans|cette|mais|comme|puis|quand|apres|avant|elle|nous|vous|ils|aux|donc|tout|tous|toute|chaque|etait|fait|faire|peut|doit|ou|et|du|au|ne|se|ce|ses|son|sa|aussi|ici|plus)\b|[àâçéèêëîïôûùüÿœ]")
repo = sys.argv[1]; groups = []; n = 0
for f in subprocess.check_output(['git', 'ls-files', '*.py'], cwd=repo, text=True).split():
    src = open(os.path.join(repo, f), encoding='utf-8', newline='').read(); its = []
    for it in T.comment_items(src) + T.docstring_items(src):
        t = re.sub(r'`[^`]*`|"[^"]*"|\'[^\']*\'', ' ', it['text'])
        if len(FR.findall(t.lower())) >= 3 and len(re.findall(r'\b(the|of|is|are|and|to|in|for|with)\b', t.lower())) < 2:
            k = 'd' if it['kind'] == 'd' else ('c' if it['full'] else 't'); its.append((it['id'], k, it['text'])); n += 1
    if its: groups.append((f, its))
T.write_batch('batch_new.in.txt', groups)
print(n, 'textes encore en francais dans', len(groups), 'fichiers -> batch_new.in.txt')
