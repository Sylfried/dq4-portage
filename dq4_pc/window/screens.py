"""Moniteurs du plein ecran : la logique pure (sans fenetre ni OpenGL), pour la tester avec de faux ecrans (tools/test_screens.py).
Le plein ecran se fait toujours sur le moniteur ou se trouve la fenetre (aucun choix du joueur : retire le 03/11/2026 sur sa demande ; le reglage `ecran_plein` de #52 n'existe plus) :
- lister : les moniteurs detectes par pyglet (`display.get_screens()`) -> descriptions (indice, position, dimensions, nom, principal) ;
- screen_of : le moniteur qui contient le centre d'un rectangle (la fenetre) ;
- cible : le moniteur du plein ecran (celui de la fenetre, sinon le principal)."""


def _name_of(ec):
    """Nom du moniteur quand pyglet le donne (Windows : nom d'usage du moniteur, X11 : nom de la sortie) ; '' sinon (jamais d'erreur)."""
    for attempt in (lambda: ec.get_monitor_name(), lambda: ec.name):
        try:
            n = attempt()
            if isinstance(n, str) and n.strip(): return n.strip()
        except Exception: pass
    return ''


def listing(screens):
    """Liste des ecrans de pyglet (dans l'ordre de `get_screens()`) -> [dict(indice, x, y, largeur, hauteur, nom, principal)] ; exactement un principal (celui que le systeme annonce, a defaut celui en (0, 0), a defaut le premier).
    Un ecran illisible est ignore ; `screens` illisible -> []."""
    output = []
    try: entries = list(screens)
    except Exception: return []
    for src, ec in enumerate(entries):
        try: d = dict(x=int(ec.x), y=int(ec.y), largeur=int(ec.width), hauteur=int(ec.height), nom=_name_of(ec), principal=False)
        except Exception: continue
        try: d['annonce'] = bool(ec.is_primary)
        except Exception: d['annonce'] = None
        d['source'] = src          # (position dans la liste de pyglet : retrouve l'objet Screen meme si un ecran illisible a ete ignore)
        output.append(d)
    if not output: return []
    p = next((d for d in output if d['annonce']), None) or next((d for d in output if d['x'] == 0 and d['y'] == 0), None) or output[0]
    p['principal'] = True
    for i, d in enumerate(output): d['indice'] = i; d.pop('annonce', None)
    return output


def screen_of(rect, entries):
    """Indice de l'ecran qui contient le centre du rectangle (x, y, largeur, hauteur) de la fenetre, a defaut celui qu'elle recouvre le plus ; None si elle n'en touche aucun (ou rectangle illisible)."""
    try: x, y, w, h = [float(v) for v in rect]
    except (TypeError, ValueError): return None
    cx, cy = x + w / 2.0, y + h / 2.0
    for d in entries:
        if d['x'] <= cx < d['x'] + d['largeur'] and d['y'] <= cy < d['y'] + d['hauteur']: return d['indice']
    best, area = None, 0.0
    for d in entries:
        ax, ay = min(x + w, d['x'] + d['largeur']) - max(x, d['x']), min(y + h, d['y'] + d['hauteur']) - max(y, d['y'])
        if ax > 0 and ay > 0 and ax * ay > area: best, area = d['indice'], ax * ay
    return best


def main(entries):
    """Indice de l'ecran principal (0 si la liste est vide : jamais d'erreur)."""
    return next((d['indice'] for d in entries if d['principal']), 0)


def target(entries, window=None):
    """Indice (dans `entries`) du moniteur du plein ecran : celui ou se trouve la fenetre (`window` : son indice, None si inconnu), a defaut le principal. Liste vide -> None."""
    if not entries: return None
    return window if isinstance(window, int) and not isinstance(window, bool) and 0 <= window < len(entries) else main(entries)
