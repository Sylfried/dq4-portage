"""Etats instantanes (savestates) : tout ce qui fait vivre le jeu, a un instant entre deux images.

Le moteur d'origine tourne dans l'emulateur (emu_core) : son etat = memoire (tas, donnees, pages modifiees de la bibliotheque) + quelques
compteurs du chargeur. A cela s'ajoute ce que la visionneuse a decode des paquets (Etat : camera, sprites, fondus...) et la memoire des fenetres de menu
(Interface). Un etat pese quelques centaines de Ko compresse ; la pile n'est pas gardee (elle est vide entre deux appels du moteur).

Fichier : b'DQ4ETAT1' | taille + JSON des infos | taille + PNG de la miniature | pickle compresse (zlib).
Les etats ne contiennent AUCUN fichier du jeu : ils ne servent qu'avec l'APK qui les a produits (meme version de la bibliotheque)."""
import io, json, os, pickle, struct, time, zlib

MAGIE = b'DQ4ETAT1'
VERSION = 1
PAGE = 4096


def _pages_modifiees(core):
    """Pages de la bibliotheque (donnees, patchs) differentes de l'image apres relocation : [(numero, octets)]."""
    cur = core.mem(core.LIB_BASE, core.elf.size); ini = bytes(core.elf.img)
    n = (len(cur) + PAGE - 1) // PAGE
    return [(i, cur[i * PAGE:(i + 1) * PAGE]) for i in range(n) if cur[i * PAGE:(i + 1) * PAGE] != ini[i * PAGE:(i + 1) * PAGE]]


def instantane(m, viewer=None):
    """Etat du moteur `m` (Moteur) -> dictionnaire serialisable. A appeler entre deux images. `viewer` : objet serialisable de plus (etat des objets animes de la carte...) rendu par appliquer."""
    c = m.core
    ui = m.ui; obs, ui.obs = ui.obs, None
    try:
        python = pickle.dumps({'etat': m.etat, 'ui': ui, 'images': m.images, 'anims': list(m.anims), 'msg_visible': m.msg_visible, 'fielddata': m.fielddata,
                               'fldobj': m.fldobj, 'grille': m._grille, 'grille_img': m._grille_img, 'msgs_ui': m.msgs_ui}, protocol=pickle.HIGHEST_PROTOCOL)
    finally:
        ui.obs = obs
    return {
        'version': VERSION,
        'heap': c.mem(c.HEAP_BASE, c.heap_ptr - c.HEAP_BASE), 'heap_ptr': c.heap_ptr,
        'data': c.mem(c.DATA_BASE, c.DATA_SIZE), 'tls': c.mem(c.TLS_BASE, c.TLS_SIZE), 'data_ptr': c.data_ptr,
        'lib': _pages_modifiees(c), 'next_file': c.next_file,
        'fichiers': {h: {k: v for k, v in f.items() if k in ('name', 'pos', 'w', 'persist')} for h, f in c.files.items()},
        'python': python, 'viewer': pickle.dumps(viewer, protocol=pickle.HIGHEST_PROTOCOL),
    }


def appliquer(m, d):
    """Remet le moteur `m` dans l'etat `d` -> objet `viewer` donne a instantane. Les ressources liees a la fenetre (fenetres de menu d'origine, textures) sont a reconstruire par l'appelant (voir Jeu.charger_etat)."""
    if d.get('version') != VERSION: raise ValueError('etat d\'une autre version (%s)' % d.get('version'))
    c = m.core; uc = c.uc
    uc.mem_write(c.LIB_BASE, bytes(c.elf.img))
    for i, b in d['lib']: uc.mem_write(c.LIB_BASE + i * PAGE, b)
    if c.heap_ptr > d['heap_ptr']: uc.mem_write(c.HEAP_BASE + (d['heap_ptr'] - c.HEAP_BASE), bytes(c.heap_ptr - d['heap_ptr']))
    uc.mem_write(c.HEAP_BASE, d['heap']); c.heap_ptr = d['heap_ptr']
    uc.mem_write(c.DATA_BASE, d['data']); uc.mem_write(c.TLS_BASE, d['tls']); c.data_ptr = d['data_ptr']; c.next_file = d['next_file']
    c.files = {}
    for h, f in d['fichiers'].items():             # fichiers ouverts : on n'en garde la trace que si le moteur en avait ouvert (non vu entre deux images jusqu'ici)
        m.log('etat : fichier ouvert non restaure (%s)' % (f.get('name'),))
    p = pickle.loads(d['python'])
    old = m.ui.obs
    m.etat = p['etat']; m.ui = p['ui']; m.ui.obs = old
    m.images = p['images']; m.anims = p['anims']; m.msg_visible = p['msg_visible']; m.fielddata = p['fielddata']; m.fldobj = p['fldobj']
    m._grille = p['grille']; m._grille_img = p['grille_img']; m.msgs_ui = p['msgs_ui']
    m.pk.begin()
    return pickle.loads(d['viewer']) if d.get('viewer') else None


def ecrire(chemin, d, infos, miniature_png=b''):
    """Enregistre l'etat `d` dans `chemin` (ecriture atomique)."""
    infos = dict(infos, date=time.strftime('%Y-%m-%d %H:%M:%S'), version=VERSION)
    ent = json.dumps(infos).encode('utf-8')
    os.makedirs(os.path.dirname(os.path.abspath(chemin)), exist_ok=True)
    tmp = chemin + '.tmp'
    with open(tmp, 'wb') as f:
        f.write(MAGIE); f.write(struct.pack('<I', len(ent))); f.write(ent); f.write(struct.pack('<I', len(miniature_png))); f.write(miniature_png)
        f.write(zlib.compress(pickle.dumps(d, protocol=pickle.HIGHEST_PROTOCOL), 3))
    os.replace(tmp, chemin)


def infos(chemin):
    """-> (infos, miniature PNG) d'un fichier d'etat, sans lire l'etat lui-meme ; None si le fichier n'existe pas ou n'est pas valide."""
    try:
        with open(chemin, 'rb') as f:
            if f.read(len(MAGIE)) != MAGIE: return None
            n, = struct.unpack('<I', f.read(4)); ent = json.loads(f.read(n).decode('utf-8'))
            k, = struct.unpack('<I', f.read(4)); png = f.read(k)
        return ent, png
    except Exception:
        return None


def lire(chemin):
    """-> dictionnaire d'etat (a passer a appliquer)."""
    with open(chemin, 'rb') as f:
        if f.read(len(MAGIE)) != MAGIE: raise ValueError('ce n\'est pas un etat du portage')
        n, = struct.unpack('<I', f.read(4)); f.read(n)
        k, = struct.unpack('<I', f.read(4)); f.read(k)
        return pickle.loads(zlib.decompress(f.read()))
