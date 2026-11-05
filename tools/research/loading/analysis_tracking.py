"""Lit un journal DQ_SUIVI : pour chaque chargement de carte, les images dessinees juste apres (genre, image du moteur, fondu) et les sauts d'images du moteur entre deux images affichees."""
import re, sys
lines = [l.rstrip() for l in open(sys.argv[1], encoding='utf-8', errors='replace') if l.startswith('TRACE')]
def fields(l): return dict(re.findall(r"(\w+)=('[^']*'|\S+)", l))
dess = []
for l in lines:
    m = re.match(r'TRACE \+([\d.]+)s (.*)', l)
    t, rest = float(m.group(1)), m.group(2)
    if rest.startswith('draw'):
        g = re.search(r"kind=(.*?) part=", rest).group(1); f = fields(rest.replace(g, g.replace(' ', '_')))
        fa = f['fade'].split('/'); dess.append(dict(t=t, n=int(f['n']), img=int(f['img']), genre=g, carte=f['game_map'], cam=f['camera'], pers=f['characters'], fa=float(fa[0]), ms=float(f['ms']), ret=f['retained']))
    elif rest.startswith('map loaded'): dess.append(dict(t=t, charge=rest))
prev = None
for d in dess:
    if 'charge' in d: print('--', d['charge'], '(+%.2fs)' % d['t']); prev = None; continue
    jump = '' if prev is None else ('engine jump +%d' % (d['img'] - prev['img']) if d['img'] - prev['img'] > 1 else '')
    print('  n=%-3d frame=%-4d %-30s fade=%.2f chars=%-5s cam=%-22s %6.0f ms %s' % (d['n'], d['img'], d['genre'], d['fa'], d['pers'], d['cam'], d['ms'], jump)); prev = d
