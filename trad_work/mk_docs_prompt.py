"""usage: mk_docs_prompt.py <nom> <morceau.in.md> ... -> prompt_docs_<nom>.txt"""
import sys
t = open('prompt_docs_template.txt', encoding='utf-8').read()
names = sys.argv[2:]
lst = ', '.join('`' + n + '`' for n in names)
open(f'prompt_docs_{sys.argv[1]}.txt', 'w', encoding='utf-8').write(t.replace('@@LIST@@', lst))
print(sys.argv[1], len(names))
