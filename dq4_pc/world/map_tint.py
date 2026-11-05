"""Teinte du decor (paquet 33, `cmd_map_color_rate`) : quels groupes de decor la recoivent.

Cote Unity (lu dans libil2cpp, RVA 0xD14E44 `NativeManager.cmd_map_color_rate`, 0xCD79F4 `FldObject.update_material_color`, 0xCD811C `FldObject.save_org_color`) :
  - le paquet donne trois flottants r, g, b : `FldObject.m_color` = (r, g, b, 1) (carte du monde : `Field.SetColor` = couleur du materiau des tuiles et de chaque symbole) ;
  - `FldObject.Update` appelle `update_material_color` a chaque image : pour chaque materiau de chaque Renderer de la carte, `Material.color` = `_OrgColor` x `m_color`, SAUF si le materiau n'a
    pas de texture principale ou si le NOM de cette texture contient « tz_ » (lampes, bougies, torches, vagues, sols qui font mal : `tz_akari1`, `tz_rousoku1`, `tz_nami`, `tz_damg01`...) : ceux-la
    gardent `_OrgColor` seul (la teinte du jour / du soir ne les touche pas : ils restent allumes) ;
  - `_OrgColor` n'est PAS la couleur `_Color` de l'asset : `FldObject.save_org_color` (RVA 0xCD811C, appele a la fin de `init_fld`) relit `Material.color` puis ecrit `_OrgColor` = (1, 1, 1, alpha d'origine) pour chaque
    materiau de chaque Renderer (s0 a s2 reecrits a 1,0 dans le desassemblage). Donc `Material.color` = (m_color.rgb, alpha) a chaque image : la couleur RGB `_Color` stockee dans l'asset n'est jamais utilisee en jeu
    (point precise par le coordinateur ; la correction du cache des cartes, `data.py`, est faite sur une autre branche : ce module et le uniforme `tint` supposent un cache NO_DEFAULT cette couleur d'asset) ;
  - les shaders du decor (`Custom/fld_normal`, `fld_atest`, `fld_trans` : texture x couleur de sommet x `_Color`) ; la carte du monde (`Custom/Field` : texture x `_Color`).
Les personnages (`Chara`), les ombres, les bulles et l'interface ne sont pas touches.

Ce module ne contient que ce qui sert a reconnaitre les groupes « tz_ » : le cache des cartes ne garde pas le nom des textures, seulement leur identifiant (path_id) ; la liste des identifiants dont le
nom contient « tz_ » est lue dans le paquet de donnees UNE fois (une demi-seconde apres le chargement du paquet, qui prend lui-meme quelques secondes) et gardee dans `tz_cles.json` du cache.
"""
import json, os, struct, threading
from dq4_pc.language import tr

FILE = 'tz_cles.json'
MARK = 'tz_'                              # FldObject.update_material_color : Texture.name.IndexOf("tz_") != -1 -> pas de teinte


def neutral_tint(t):
    """Vrai si la teinte ne change rien (1, 1, 1) : rien a faire, le dessin reste identique au pixel pres."""
    return t is None or (abs(t[0] - 1.0) < 1e-6 and abs(t[1] - 1.0) < 1e-6 and abs(t[2] - 1.0) < 1e-6)


def group_tz(lookup_key, ids_tz, names_pam=None):
    """Vrai si le groupe de decor `lookup_key` (cle du cache des cartes : identifiant de texture, ('tr', priorite, cle) pour un materiau transparent, ('pam', nom, animation, evenement) pour une palette animee)
    est une texture « tz_ » donc non teintee. `ids_tz` : ensemble des identifiants de textures « tz_ » (None = inconnu : tout est teinte)."""
    if isinstance(lookup_key, tuple) and len(lookup_key) == 3 and lookup_key[0] == 'tr': lookup_key = lookup_key[2]
    if isinstance(lookup_key, tuple) and len(lookup_key) >= 2 and lookup_key[0] == 'pam': return MARK in str(lookup_key[1])        # palette animee : textures « <nom>.NNN » (FldObject.set_palette_data)
    return bool(ids_tz) and lookup_key in ids_tz


def read(cache):
    """Ensemble des identifiants « tz_ » enregistre dans le cache, None s'il n'y est pas (encore) ou s'il est illisible."""
    try:
        with open(os.path.join(cache, FILE), encoding='utf-8') as fh: d = json.load(fh)
        return set(int(x) for x in d['ids'])
    except Exception:
        return None


def compute(data):
    """Lit le paquet de donnees (sous le verrou de `data`), releve les textures dont le nom contient « tz_ », ecrit le fichier du cache et renvoie l'ensemble. Leve une exception en cas d'echec."""
    with data._lock:
        loaded_here = data._env is None
        try:
            data.env()
            def name_str(o):
                try: return o.peek_name() or ''                  # lecture du seul nom (UnityPy recent)
                except Exception: return o.read().m_Name         # sinon lecture complete de l'objet
            ids = sorted(o.path_id for o in data._objs.values() if o.type.name == 'Texture2D' and MARK in name_str(o))
        finally:
            if loaded_here: data.free_up()                  # on rend les 800 Mo si c'est nous qui avons lu le paquet
    f = os.path.join(data.cache, FILE)
    with open(f + '.tmp', 'w', encoding='utf-8') as fh: json.dump({'ids': ids, 'marque': MARK}, fh)
    os.replace(f + '.tmp', f)
    return set(ids)


class TzKeys:
    """Ensemble des identifiants « tz_ », lu dans le cache ou calcule en tache de fond ; `ids()` renvoie None tant qu'il n'est pas pret (le decor est alors entierement teinte : les lampes se
    rallument des que la liste arrive, quelques secondes, une seule fois)."""
    def __init__(self, data, log=print):
        self.data = data; self.log = log; self._ids = None; self._trial = False; self._fil = None

    def ids(self):
        if self._ids is not None: return self._ids
        if not self._trial:
            self._trial = True
            self._ids = read(self.data.cache)
            if self._ids is None:
                def worker():
                    try: self._ids = compute(self.data)
                    except Exception as ex:
                        self.log('Map tint: "tz_" textures unreadable (%s): the whole map will be tinted' % str(ex)[:80]); self._ids = set()
                self._fil = threading.Thread(target=worker, daemon=True, name='teinte-tz'); self._fil.start()
        return self._ids


# ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
# Couleur de fond des decors de combat (bloc FETC du fichier .map du decor)
#
# Cote Unity (lu dans libil2cpp) : `FldObject.init_fld` lit le bloc FETC (FLD_MAP_ETC) ; son premier champ `bg_color` est lu par `ChunkFile.readColor` (RVA 0xCCEC20 : 4 octets r, g, b, a divises par 255) ;
# `NativeManager.cmd_fld_load` (RVA 0xD11D64), en dernier, appelle `BackColor.SetColor(bg_color, 0)` (RVA 0xCC4364 : meme couleur en haut et en bas, tout de suite). Le moteur n'envoie AUCUNE couleur de fond
# en combat (pas de paquet 8) : le fond d'un combat est donc la `bg_color` du decor charge, variante par variante (`_d`, `_e`, `_n`, `_dk`) : c'est elle qui donne l'orange du coucher de soleil autour du sol.
# (Les villes, elles, recoivent ensuite un paquet 8 : `cmd_back_color` RVA 0xD14F44, alpha 1.) L'alpha du FETC vaut 0 dans les 140 decors : sans effet, le shader `BackColor` du paquet de donnees n'a
# pas de fusion (Blend One Zero, ZTest Always, ZWrite Off) : il ecrit la couleur de sommet telle quelle.
# ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
BACKGROUNDS_FILE = 'fonds_decor.json'
BACKGROUND_PREFIX = 'btl'                      # decors de combat (btl_*, btlc*, btld*, btls*, btlt*, btlm*, btly*)


def fetc_background(raw):
    """Couleur de fond (r, g, b) en flottants 0 a 1 du bloc FETC d'un fichier .map de decor (FLD_MAP_ETC.bg_color : octets 8 a 10 du bloc, apres 'FETC' et sa taille), ou None s'il n'y a pas de bloc."""
    from dq4_pc.world import fld
    for tag, p, s in fld.chunks(raw):
        if tag == 'FETC' and s >= 12 and p + 11 <= len(raw):
            r, g, b = struct.unpack_from('<3B', raw, p + 8)
            return (r / 255.0, g / 255.0, b / 255.0)
    return None


def read_backgrounds(cache):
    """{nom du decor: (r, g, b)} enregistre dans le cache, None s'il n'y est pas (encore) ou s'il est illisible."""
    try:
        with open(os.path.join(cache, BACKGROUNDS_FILE), encoding='utf-8') as fh: d = json.load(fh)
        return {k: tuple(float(x) for x in v) for k, v in d['fonds'].items()}
    except Exception:
        return None


def compute_backgrounds(data):
    """Lit le paquet de donnees (sous le verrou de `data`), releve le FETC de chaque decor de combat, ecrit le fichier du cache et renvoie le dictionnaire. Leve une exception en cas d'echec."""
    backgrounds = {}
    with data._lock:
        loaded_here = data._env is None
        try:
            data.env()
            for o in data._objs.values():
                if o.type.name != 'TextAsset': continue
                try: name_str = o.peek_name() or ''
                except Exception: name_str = o.read().m_Name
                if not (name_str.startswith(BACKGROUND_PREFIX) and name_str.endswith('.map')): continue
                t = o.read(); raw = t.m_Script.encode('utf-8', 'surrogateescape') if isinstance(t.m_Script, str) else bytes(t.m_Script)
                c = fetc_background(raw)
                if c is not None: backgrounds[name_str[:-4]] = c
        finally:
            if loaded_here: data.free_up()
    f = os.path.join(data.cache, BACKGROUNDS_FILE)
    with open(f + '.tmp', 'w', encoding='utf-8') as fh: json.dump({'fonds': backgrounds, 'prefixe': BACKGROUND_PREFIX}, fh)
    os.replace(f + '.tmp', f)
    return backgrounds


class Backgrounds:
    """Couleurs de fond des decors de combat, lues dans le cache ou calculees en tache de fond (une fois, quelques secondes) ; `color(name_str)` renvoie None tant que la liste n'est pas prete ou si le decor n'y est
    pas : l'appelant garde alors son estimation (Game._battle_background)."""
    def __init__(self, data, log=print):
        self.data = data; self.log = log; self._backgrounds = None; self._trial = False; self._fil = None

    def color(self, name_str):
        if self._backgrounds is None and not self._trial:
            self._trial = True
            self._backgrounds = read_backgrounds(self.data.cache)
            if self._backgrounds is None:
                def worker():
                    try: self._backgrounds = compute_backgrounds(self.data)
                    except Exception as ex:
                        self.log('Battle scenery backgrounds unreadable (%s): background estimated' % str(ex)[:80]); self._backgrounds = {}
                self._fil = threading.Thread(target=worker, daemon=True, name='fonds-decor'); self._fil.start()
        return (self._backgrounds or {}).get(name_str)
