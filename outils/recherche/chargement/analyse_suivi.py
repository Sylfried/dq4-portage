"""Lit un journal DQ_SUIVI : pour chaque chargement de carte, les images dessinees juste apres (genre, image du moteur, fondu) et les sauts d'images du moteur entre deux images affichees."""
import re, sys
lignes = [l.rstrip() for l in open(sys.argv[1], encoding='utf-8', errors='replace') if l.startswith('SUIVI')]
def champs(l): return dict(re.findall(r"(\w+)=('[^']*'|\S+)", l))
dess = []
for l in lignes:
    m = re.match(r'SUIVI \+([\d.]+)s (.*)', l)
    t, rest = float(m.group(1)), m.group(2)
    if rest.startswith('dessin'):
        g = re.search(r"genre=(.*?) partie=", rest).group(1); f = champs(rest.replace(g, g.replace(' ', '_')))
        fa = f['fondu'].split('/'); dess.append(dict(t=t, n=int(f['n']), img=int(f['img']), genre=g, carte=f['carte'], cam=f['camera'], pers=f['personnages'], fa=float(fa[0]), ms=float(f['ms']), ret=f['retenu']))
    elif rest.startswith('carte chargee'): dess.append(dict(t=t, charge=rest))
prec = None
for d in dess:
    if 'charge' in d: print('--', d['charge'], '(+%.2fs)' % d['t']); prec = None; continue
    saut = '' if prec is None else ('saut moteur +%d' % (d['img'] - prec['img']) if d['img'] - prec['img'] > 1 else '')
    print('  n=%-3d img=%-4d %-30s fondu=%.2f pers=%-5s cam=%-22s %6.0f ms %s' % (d['n'], d['img'], d['genre'], d['fa'], d['pers'], d['cam'], d['ms'], saut)); prec = d
