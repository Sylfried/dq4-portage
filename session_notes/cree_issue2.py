import json, subprocess, sys
# usage: cree_issue2.py <titre> <fichier corps> <labels virgule> [jalon]
titre, fich, labels = sys.argv[1], sys.argv[2], [l for l in sys.argv[3].split(',') if l]
data = {"title": titre, "body": open(fich, encoding='utf-8').read(), "labels": labels}
if len(sys.argv) > 4 and sys.argv[4] != '-': data["milestone"] = int(sys.argv[4])
for i in range(4):
    r = subprocess.run(["gh", "api", "-X", "POST", "repos/Sylfried/dq4-portage/issues", "--input", "-"], input=json.dumps(data), text=True, capture_output=True)
    if not r.returncode: j = json.loads(r.stdout); print(j["number"], j["title"]); sys.exit(0)
    print("ERREUR", r.stderr[:200])
sys.exit(1)
