"""Etats instantanes (savestates) : tout ce qui fait vivre le jeu, a un instant entre deux images.

Le moteur d'origine tourne dans l'emulateur (emu_core) : son etat = memoire (tas, donnees, pages modifiees de la bibliotheque) + quelques
compteurs du chargeur. A cela s'ajoute ce que la visionneuse a decode des paquets (Etat : camera, sprites, fondus...) et la memoire des fenetres de menu
(Interface). Un etat pese quelques centaines de Ko compresse ; la pile n'est pas gardee (elle est vide entre deux appels du moteur).

Fichier : b'DQ4ETAT1' | taille + JSON des infos | taille + PNG de la miniature | pickle compresse (zlib).
Les etats ne contiennent AUCUN fichier du jeu : ils ne servent qu'avec l'APK qui les a produits (meme version de la bibliotheque)."""
import hashlib, io, json, os, pickle, struct, time, zlib

from dq4_pc.language import tr

# Anciens noms de modules (avant le rangement du 04/11/2026 : tout etait a plat dans dq4_pc) -> noms actuels : les etats enregistres avant cette date
# gardent le nom de module `moteur` (ou autre) dans leur pickle ; on les relit sans les changer.
OLD_MODULES = {
    'emu_core': 'dq4_pc.core.emu_core', 'moteur': 'dq4_pc.core.engine', 'pktlog': 'dq4_pc.core.pktlog', 'rencontres': 'dq4_pc.core.encounters',
    'priorite_jeu': 'dq4_pc.core.game_priority', 'suivi_charge': 'dq4_pc.core.load_tracking', 'pose_couchee': 'dq4_pc.core.lying_pose', 'historique': 'dq4_pc.core.history',
    'effet_combat': 'dq4_pc.battle.battle_effect', 'vitesse_combat': 'dq4_pc.battle.battle_speed', 'historique_combat': 'dq4_pc.battle.battle_history',
    'donnees': 'dq4_pc.world.data', 'fld': 'dq4_pc.world.fld', 'fbx': 'dq4_pc.world.fbx', 'hd': 'dq4_pc.world.hd', 'objets_carte': 'dq4_pc.world.map_objects',
    'decors_plats': 'dq4_pc.world.flat_sceneries', 'contours_decor': 'dq4_pc.world.scenery_outlines', 'teinte_carte': 'dq4_pc.world.map_tint',
    'postfx': 'dq4_pc.render.postfx', 'ciel_titre': 'dq4_pc.render.title_sky',
    'ui_menu': 'dq4_pc.menus.ui_menu', 'pause': 'dq4_pc.menus.pause', 'ui_historique': 'dq4_pc.menus.ui_history', 'hud_mobile': 'dq4_pc.menus.hud_mobile',
    'ecran_sauvegardes': 'dq4_pc.menus.saves_screen', 'avant_partie': 'dq4_pc.menus.pre_game', 'saisie_nom': 'dq4_pc.menus.name_entry',
    'reglages': 'dq4_pc.persistence.settings', 'sauvegardes': 'dq4_pc.persistence.saves', 'etats': 'dq4_pc.persistence.savestates',
    'entrees': 'dq4_pc.window.inputs', 'ecrans': 'dq4_pc.window.screens', 'son': 'dq4_pc.sound',
    'dq4_pc.noyau.moteur': 'dq4_pc.core.engine',       # etats enregistres entre le rangement du 04/11/2026 et le passage a l'anglais du 05/11/2026
}
# Anciens noms de classes (meme date) : `Etat` est devenue `State`.
OLD_CLASSES = {'Etat': 'State'}


# Liste blanche des classes lisibles dans un etat (#241, audit ENG-05) : un `.dqs` recu d'une autre personne ne doit pas pouvoir executer de code au chargement. Un pickle peut appeler n'importe quelle fonction
# d'un module importable (os.system, eval...) ; on n'accepte que les types de donnees qu'ecrit `snapshot` / `write` : les deux classes du portage (`State`, `Interface`), les conteneurs de base,
# les tableaux numpy (les deux espaces de noms, `numpy.core` avant numpy 2 et `numpy._core` depuis) et trois conteneurs de `collections`. Releve fait sur de vrais etats (monde, ville, combat) : rien d'autre.
ALLOWED_CLASSES = {
    'dq4_pc.core.engine': {'State', 'Interface'},
    'builtins': {'bool', 'bytearray', 'bytes', 'complex', 'dict', 'float', 'frozenset', 'int', 'list', 'range', 'set', 'slice', 'str', 'tuple'},
    'collections': {'OrderedDict', 'defaultdict', 'deque'},
    'numpy': {'dtype', 'ndarray'},
    'numpy.core.multiarray': {'_reconstruct', 'scalar'}, 'numpy._core.multiarray': {'_reconstruct', 'scalar'},
    'numpy.core.numeric': {'_frombuffer'}, 'numpy._core.numeric': {'_frombuffer'},
}


class _Unpickler(pickle.Unpickler):
    def find_class(self, module, name):
        module = OLD_MODULES.get(module, module)
        name = OLD_CLASSES.get(name, name) if module == 'dq4_pc.core.engine' else name
        if name not in ALLOWED_CLASSES.get(module, ()):
            raise pickle.UnpicklingError(tr("fichier d'état refusé : il demande « %s.%s », ce qu'un état du portage ne contient pas (fichier venu d'ailleurs ou abîmé ; il n'a pas été exécuté)") % (module, name))
        return super().find_class(module, name)


def _load(raw):
    """pickle.loads qui reconnait aussi les anciens noms de modules et refuse toute classe hors de ALLOWED_CLASSES (rien n'est execute : un fichier piege est rejete avant)."""
    return _Unpickler(io.BytesIO(raw)).load()

MAGIC = b'DQ4ETAT1'
VERSION = 1
PAGE = 4096


def lib_fingerprint(core):
    """Empreinte de la bibliotheque du moteur (image apres relocation) : un etat n'a de sens qu'avec la bibliotheque qui l'a produit (#206)."""
    return hashlib.sha256(bytes(core.elf.img)).hexdigest()[:16]


def _modified_pages(core):
    """Pages de la bibliotheque (donnees, patchs) differentes de l'image apres relocation : [(numero, octets)]."""
    cur = core.mem(core.LIB_BASE, core.elf.size); ini = bytes(core.elf.img)
    n = (len(cur) + PAGE - 1) // PAGE
    return [(i, cur[i * PAGE:(i + 1) * PAGE]) for i in range(n) if cur[i * PAGE:(i + 1) * PAGE] != ini[i * PAGE:(i + 1) * PAGE]]


def snapshot(m, viewer=None):
    """Etat du moteur `m` (Moteur) -> dictionnaire serialisable. A appeler entre deux images. `viewer` : objet serialisable de plus (etat des objets animes de la carte...) rendu par appliquer."""
    c = m.core
    ui = m.ui; obs, ui.obs = ui.obs, None
    try:
        python = pickle.dumps({'etat': m.state, 'ui': ui, 'images': m.frames, 'anims': list(m.anims), 'msg_visible': m.msg_visible, 'fielddata': m.fielddata,
                               'fldobj': m.fldobj, 'grille': m._grid, 'grille_img': m._grid_frame, 'msgs_ui': m.msgs_ui}, protocol=pickle.HIGHEST_PROTOCOL)
    finally:
        ui.obs = obs
    return {
        'version': VERSION, 'lib_sha': lib_fingerprint(c),
        'heap': c.mem(c.HEAP_BASE, c.heap_ptr - c.HEAP_BASE), 'heap_ptr': c.heap_ptr,
        'data': c.mem(c.DATA_BASE, c.DATA_SIZE), 'tls': c.mem(c.TLS_BASE, c.TLS_SIZE), 'data_ptr': c.data_ptr,
        'lib': _modified_pages(c), 'next_file': c.next_file,
        'fichiers': {h: {k: v for k, v in f.items() if k in ('name', 'pos', 'w', 'persist')} for h, f in c.files.items()},
        'python': python, 'viewer': pickle.dumps(viewer, protocol=pickle.HIGHEST_PROTOCOL),
    }


def apply(m, d):
    """Remet le moteur `m` dans l'etat `d` -> objet `viewer` donne a instantane. Les ressources liees a la fenetre (fenetres de menu d'origine, textures) sont a reconstruire par l'appelant (voir Game.load_state)."""
    if d.get('version') != VERSION: raise ValueError(tr('etat d\'une autre version (%s)') % d.get('version'))
    c = m.core; uc = c.uc
    if d.get('lib_sha') and d['lib_sha'] != lib_fingerprint(c): raise ValueError(tr('etat enregistre avec une autre version de la bibliotheque du moteur (APK different) : il ne peut pas etre charge'))       # (les etats d'avant #206 n'ont pas d'empreinte : acceptes)
    p = _load(d['python']); viewer = _load(d['viewer']) if d.get('viewer') else None            # TOUT est lu avant d'ecrire quoi que ce soit dans le moteur : un fichier abime laisse le jeu intact (#206)
    uc.mem_write(c.LIB_BASE, bytes(c.elf.img))
    for i, b in d['lib']: uc.mem_write(c.LIB_BASE + i * PAGE, b)
    if c.heap_ptr > d['heap_ptr']: uc.mem_write(c.HEAP_BASE + (d['heap_ptr'] - c.HEAP_BASE), bytes(c.heap_ptr - d['heap_ptr']))
    uc.mem_write(c.HEAP_BASE, d['heap']); c.heap_ptr = d['heap_ptr']
    uc.mem_write(c.DATA_BASE, d['data']); uc.mem_write(c.TLS_BASE, d['tls']); c.data_ptr = d['data_ptr']; c.next_file = d['next_file']
    c.files = {}
    for h, f in d['fichiers'].items():             # fichiers ouverts : on n'en garde la trace que si le moteur en avait ouvert (non vu entre deux images jusqu'ici)
        m.log('etat : fichier ouvert non restaure (%s)' % (f.get('name'),))
    old = m.ui.obs
    m.state = p['etat']; m.ui = p['ui']; m.ui.obs = old
    if not hasattr(m.ui, 'damage'): m.ui.damage = []              # etat enregistre par une version plus ancienne (avant les nombres de degats)
    m.frames = p['images']; m.anims = p['anims']; m.msg_visible = p['msg_visible']; m.fielddata = p['fielddata']; m.fldobj = p['fldobj']
    m._grid = p['grille']; m._grid_frame = p['grille_img']; m.msgs_ui = p['msgs_ui']
    m.reapply_fixes()                                    # vitesses de heros d'origine (un etat enregistre par une ancienne version pendant une course les contient majorees), bouton « Paramètres » -> menu Pause (un etat enregistre
                                                                  # avant ce detournement a remis l'instruction d'origine), fenetre des lieux elargie et « Sauv. cloud » retiree (idem : l'image d'origine est rechargee ci-dessus)
    m.pk.begin()
    return viewer


def write(path, d, info, thumbnail_png=b''):
    """Enregistre l'etat `d` dans `path` (ecriture atomique)."""
    info = dict(info, date=time.strftime('%Y-%m-%d %H:%M:%S'), version=VERSION)
    ent = json.dumps(info).encode('utf-8')
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    tmp = path + '.tmp'
    with open(tmp, 'wb') as f:
        f.write(MAGIC); f.write(struct.pack('<I', len(ent))); f.write(ent); f.write(struct.pack('<I', len(thumbnail_png))); f.write(thumbnail_png)
        f.write(zlib.compress(pickle.dumps(d, protocol=pickle.HIGHEST_PROTOCOL), 3))
    os.replace(tmp, path)


def info(path):
    """-> (infos, miniature PNG) d'un fichier d'etat, sans lire l'etat lui-meme ; None si le fichier n'existe pas ou n'est pas valide."""
    try:
        with open(path, 'rb') as f:
            if f.read(len(MAGIC)) != MAGIC: return None
            n, = struct.unpack('<I', f.read(4)); ent = json.loads(f.read(n).decode('utf-8'))
            k, = struct.unpack('<I', f.read(4)); png = f.read(k)
        return ent, png
    except Exception:
        return None


def read(path):
    """-> dictionnaire d'etat (a passer a appliquer)."""
    with open(path, 'rb') as f:
        if f.read(len(MAGIC)) != MAGIC: raise ValueError(tr('ce n\'est pas un etat du portage'))
        n, = struct.unpack('<I', f.read(4)); f.read(n)
        k, = struct.unpack('<I', f.read(4)); f.read(k)
        return _load(zlib.decompress(f.read()))
