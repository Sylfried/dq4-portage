import json, subprocess, sys
# usage: ouvrir_pr.py <branche> <titre> <fichier corps>
branche, titre, fich = sys.argv[1:4]
corps = open(fich, encoding='utf-8').read()
d = {"title": titre, "head": branche, "base": "main", "body": corps}
r = subprocess.run(["gh","api","-X","POST","repos/Sylfried/dq4-portage/pulls","--input","-"], input=json.dumps(d), text=True, capture_output=True)
if r.returncode: print("ERREUR", r.stderr[:400]); sys.exit(1)
j = json.loads(r.stdout); print(j['number'], j['html_url'])
