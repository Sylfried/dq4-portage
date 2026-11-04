"""Teinte du decor (paquet 33, `cmd_map_color_rate`) : quels groupes de decor la recoivent.

Cote Unity (lu dans libil2cpp, RVA 0xD14E44 `NativeManager.cmd_map_color_rate`, 0xCD79F4 `FldObject.update_material_color`, 0xCD811C `FldObject.save_org_color`) :
  - le paquet donne trois flottants r, g, b : `FldObject.m_color` = (r, g, b, 1) (carte du monde : `Field.SetColor` = couleur du materiau des tuiles et de chaque symbole) ;
  - `FldObject.Update` appelle `update_material_color` a chaque image : pour chaque materiau de chaque Renderer de la carte, `Material.color` = `_OrgColor` x `m_color`, SAUF si le materiau n'a
    pas de texture principale ou si le NOM de cette texture contient « tz_ » (lampes, bougies, torches, vagues, sols qui font mal : `tz_akari1`, `tz_rousoku1`, `tz_nami`, `tz_damg01`...) : ceux-la
    gardent `_OrgColor` seul (la teinte du jour / du soir ne les touche pas : ils restent allumes) ;
  - `_OrgColor` n'est PAS la couleur `_Color` de l'asset : `FldObject.save_org_color` (RVA 0xCD811C, appele a la fin de `init_fld`) relit `Material.color` puis ecrit `_OrgColor` = (1, 1, 1, alpha d'origine) pour chaque
    materiau de chaque Renderer (s0 a s2 reecrits a 1,0 dans le desassemblage). Donc `Material.color` = (m_color.rgb, alpha) a chaque image : la couleur RGB `_Color` stockee dans l'asset n'est jamais utilisee en jeu
    (point precise par le coordinateur ; la correction du cache des cartes, `donnees.py`, est faite sur une autre branche : ce module et le uniforme `teinte` supposent un cache SANS cette couleur d'asset) ;
  - les shaders du decor (`Custom/fld_normal`, `fld_atest`, `fld_trans` : texture x couleur de sommet x `_Color`) ; la carte du monde (`Custom/Field` : texture x `_Color`).
Les personnages (`Chara`), les ombres, les bulles et l'interface ne sont pas touches.

Ce module ne contient que ce qui sert a reconnaitre les groupes « tz_ » : le cache des cartes ne garde pas le nom des textures, seulement leur identifiant (path_id) ; la liste des identifiants dont le
nom contient « tz_ » est lue dans le paquet de donnees UNE fois (une demi-seconde apres le chargement du paquet, qui prend lui-meme quelques secondes) et gardee dans `tz_cles.json` du cache.
"""
import json, os, struct, threading

FICHIER = 'tz_cles.json'
MARQUE = 'tz_'                              # FldObject.update_material_color : Texture.name.IndexOf("tz_") != -1 -> pas de teinte


def teinte_neutre(t):
    """Vrai si la teinte ne change rien (1, 1, 1) : rien a faire, le dessin reste identique au pixel pres."""
    return t is None or (abs(t[0] - 1.0) < 1e-6 and abs(t[1] - 1.0) < 1e-6 and abs(t[2] - 1.0) < 1e-6)


def groupe_tz(cle, ids_tz, noms_pam=None):
    """Vrai si le groupe de decor `cle` (cle du cache des cartes : identifiant de texture, ('tr', priorite, cle) pour un materiau transparent, ('pam', nom, animation, evenement) pour une palette animee)
    est une texture « tz_ » donc non teintee. `ids_tz` : ensemble des identifiants de textures « tz_ » (None = inconnu : tout est teinte)."""
    if isinstance(cle, tuple) and len(cle) == 3 and cle[0] == 'tr': cle = cle[2]
    if isinstance(cle, tuple) and len(cle) >= 2 and cle[0] == 'pam': return MARQUE in str(cle[1])        # palette animee : textures « <nom>.NNN » (FldObject.set_palette_data)
    return bool(ids_tz) and cle in ids_tz


def lire(cache):
    """Ensemble des identifiants « tz_ » enregistre dans le cache, None s'il n'y est pas (encore) ou s'il est illisible."""
    try:
        with open(os.path.join(cache, FICHIER), encoding='utf-8') as fh: d = json.load(fh)
        return set(int(x) for x in d['ids'])
    except Exception:
        return None


def calculer(donnees):
    """Lit le paquet de donnees (sous le verrou de `donnees`), releve les textures dont le nom contient « tz_ », ecrit le fichier du cache et renvoie l'ensemble. Leve une exception en cas d'echec."""
    with donnees._verrou:
        charge_ici = donnees._env is None
        try:
            donnees.env()
            def nom(o):
                try: return o.peek_name() or ''                  # lecture du seul nom (UnityPy recent)
                except Exception: return o.read().m_Name         # sinon lecture complete de l'objet
            ids = sorted(o.path_id for o in donnees._objs.values() if o.type.name == 'Texture2D' and MARQUE in nom(o))
        finally:
            if charge_ici: donnees.liberer()                  # on rend les 800 Mo si c'est nous qui avons lu le paquet
    f = os.path.join(donnees.cache, FICHIER)
    with open(f + '.tmp', 'w', encoding='utf-8') as fh: json.dump({'ids': ids, 'marque': MARQUE}, fh)
    os.replace(f + '.tmp', f)
    return set(ids)


class Cles:
    """Ensemble des identifiants « tz_ », lu dans le cache ou calcule en tache de fond ; `ids()` renvoie None tant qu'il n'est pas pret (le decor est alors entierement teinte : les lampes se
    rallument des que la liste arrive, quelques secondes, une seule fois)."""
    def __init__(self, donnees, log=print):
        self.donnees = donnees; self.log = log; self._ids = None; self._essai = False; self._fil = None

    def ids(self):
        if self._ids is not None: return self._ids
        if not self._essai:
            self._essai = True
            self._ids = lire(self.donnees.cache)
            if self._ids is None:
                def travail():
                    try: self._ids = calculer(self.donnees)
                    except Exception as ex:
                        self.log('Teinte des cartes : textures « tz_ » illisibles (%s) : toute la carte sera teintee' % str(ex)[:80]); self._ids = set()
                self._fil = threading.Thread(target=travail, daemon=True, name='teinte-tz'); self._fil.start()
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
FICHIER_FONDS = 'fonds_decor.json'
PREFIXE_FONDS = 'btl'                      # decors de combat (btl_*, btlc*, btld*, btls*, btlt*, btlm*, btly*)


def fond_fetc(raw):
    """Couleur de fond (r, g, b) en flottants 0 a 1 du bloc FETC d'un fichier .map de decor (FLD_MAP_ETC.bg_color : octets 8 a 10 du bloc, apres 'FETC' et sa taille), ou None s'il n'y a pas de bloc."""
    from dq4_pc.monde import fld
    for tag, p, s in fld.chunks(raw):
        if tag == 'FETC' and s >= 12 and p + 11 <= len(raw):
            r, g, b = struct.unpack_from('<3B', raw, p + 8)
            return (r / 255.0, g / 255.0, b / 255.0)
    return None


def lire_fonds(cache):
    """{nom du decor: (r, g, b)} enregistre dans le cache, None s'il n'y est pas (encore) ou s'il est illisible."""
    try:
        with open(os.path.join(cache, FICHIER_FONDS), encoding='utf-8') as fh: d = json.load(fh)
        return {k: tuple(float(x) for x in v) for k, v in d['fonds'].items()}
    except Exception:
        return None


def calculer_fonds(donnees):
    """Lit le paquet de donnees (sous le verrou de `donnees`), releve le FETC de chaque decor de combat, ecrit le fichier du cache et renvoie le dictionnaire. Leve une exception en cas d'echec."""
    fonds = {}
    with donnees._verrou:
        charge_ici = donnees._env is None
        try:
            donnees.env()
            for o in donnees._objs.values():
                if o.type.name != 'TextAsset': continue
                try: nom = o.peek_name() or ''
                except Exception: nom = o.read().m_Name
                if not (nom.startswith(PREFIXE_FONDS) and nom.endswith('.map')): continue
                t = o.read(); raw = t.m_Script.encode('utf-8', 'surrogateescape') if isinstance(t.m_Script, str) else bytes(t.m_Script)
                c = fond_fetc(raw)
                if c is not None: fonds[nom[:-4]] = c
        finally:
            if charge_ici: donnees.liberer()
    f = os.path.join(donnees.cache, FICHIER_FONDS)
    with open(f + '.tmp', 'w', encoding='utf-8') as fh: json.dump({'fonds': fonds, 'prefixe': PREFIXE_FONDS}, fh)
    os.replace(f + '.tmp', f)
    return fonds


class Fonds:
    """Couleurs de fond des decors de combat, lues dans le cache ou calculees en tache de fond (une fois, quelques secondes) ; `couleur(nom)` renvoie None tant que la liste n'est pas prete ou si le decor n'y est
    pas : l'appelant garde alors son estimation (Jeu._fond_combat)."""
    def __init__(self, donnees, log=print):
        self.donnees = donnees; self.log = log; self._fonds = None; self._essai = False; self._fil = None

    def couleur(self, nom):
        if self._fonds is None and not self._essai:
            self._essai = True
            self._fonds = lire_fonds(self.donnees.cache)
            if self._fonds is None:
                def travail():
                    try: self._fonds = calculer_fonds(self.donnees)
                    except Exception as ex:
                        self.log('Fonds des decors de combat illisibles (%s) : fond estime' % str(ex)[:80]); self._fonds = {}
                self._fil = threading.Thread(target=travail, daemon=True, name='fonds-decor'); self._fil.start()
        return (self._fonds or {}).get(nom)
