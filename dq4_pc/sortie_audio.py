"""Choix du peripherique de sortie audio (#112, D-207) : la logique, sans fenetre ni son reel, pour la tester avec de faux pilotes (outils/test_sortie_audio.py).
Lu dans pyglet 2.1 (Windows 8 et plus, pilote XAudio2, celui que pyglet prend en premier) : `pyglet.media.devices.get_audio_device_manager().get_output_devices()` liste les sorties actives (`id`, `name`) et
`pyglet.media.get_audio_driver().set_device(device)` recree le moteur audio sur cette sortie, puis chaque lecteur en cours se remet en lecture (`Player.on_driver_reset`). Sans `set_device` (autre pilote, audio coupe pour
les tests) la ligne du menu est inactive. Le choix est enregistre dans `reglages.json` (`sortie_audio` : None = Automatique, sinon {id, nom}) ; une sortie qui n'est plus branchee est gardee dans les reglages et le son
reste sur la sortie par defaut de Windows en attendant. **Jamais vu sous Windows** : tout est entoure de try / except (une erreur laisse le son comme il etait)."""
import time, types

AUTO = 'auto'                 # valeur de la liste : suivre la sortie par defaut de Windows (le pilote la suit tout seul quand elle change)
ABSENT_SUFFIXE = ' (non branchée)'
DELAI_LISTE = 1.5             # la liste des sorties est gardee 1,5 s (le menu refait ses lignes a chaque image)


def _pilote():
    """Le pilote audio de pyglet s'il sait changer de sortie, sinon None (jamais d'erreur)."""
    try:
        import pyglet.media as media
        p = media.get_audio_driver()
        return p if callable(getattr(p, 'set_device', None)) else None
    except Exception: return None


def _gestionnaire():
    """Le gestionnaire de peripheriques audio de pyglet (Windows), sinon None."""
    try:
        from pyglet.media.devices import get_audio_device_manager
        return get_audio_device_manager()
    except Exception: return None


def choix_valide(v):
    """Reglage `sortie_audio` lu dans reglages.json : None ou {id, nom} (textes non vides) ; tout le reste -> None (Automatique)."""
    if isinstance(v, dict) and isinstance(v.get('id'), str) and v['id'] and isinstance(v.get('nom'), str):
        return {'id': v['id'], 'nom': v['nom']}
    return None


class Sorties:
    """Les sorties audio detectees et la sortie en service. `pilote` et `gestionnaire` s'injectent pour les tests ; None = ceux de pyglet (cherches a chaque appel : jamais d'erreur au lancement)."""
    def __init__(self, pilote=None, gestionnaire=None, horloge=time.monotonic):
        self._pilote_force = pilote; self._gest_force = gestionnaire; self._horloge = horloge
        self._liste = []; self._t_liste = None; self.en_service = AUTO

    def _p(self): return self._pilote_force if self._pilote_force is not None else _pilote()
    def _g(self): return self._gest_force if self._gest_force is not None else _gestionnaire()

    def disponible(self):
        """Le pilote sait-il changer de sortie et le systeme en liste-t-il ? (sinon la ligne du menu est inactive)"""
        return self._p() is not None and self._g() is not None

    def lister(self, frais=False):
        """[(id, nom)] des sorties actives, dans l'ordre du systeme ; [] sans pilote ou en cas d'erreur."""
        t = self._horloge()
        if not frais and self._t_liste is not None and t - self._t_liste < DELAI_LISTE: return list(self._liste)
        liste = []
        try:
            g = self._g()
            if g is not None and self._p() is not None:
                for d in g.get_output_devices():
                    ident = str(d.id); nom = str(getattr(d, 'name', '') or getattr(d, 'description', '') or ident).strip()
                    if ident and not any(i == ident for i, _ in liste): liste.append((ident, nom))
        except Exception: liste = []
        self._liste = liste; self._t_liste = t
        return list(liste)

    def valeur(self, choix):
        """Valeur de la liste pour le reglage `choix` (None ou {id, nom}) : AUTO, ou l'id de la sortie choisie (branchee ou non)."""
        return AUTO if choix is None else choix['id']

    def valeurs(self, choix):
        """Valeurs proposees par la ligne du menu : Automatique, les sorties detectees, puis (a la fin) la sortie enregistree quand elle n'est plus branchee."""
        liste = self.lister(); v = [AUTO] + [i for i, _ in liste]
        if choix is not None and choix['id'] not in v: v.append(choix['id'])
        return v

    def nom(self, valeur, choix):
        """Libelle d'une valeur de la liste."""
        if valeur == AUTO: return 'Automatique'
        for i, n in self.lister():
            if i == valeur: return n
        if choix is not None and choix['id'] == valeur: return choix['nom'] + ABSENT_SUFFIXE
        return str(valeur)

    def modifiable(self, choix):
        """La ligne a-t-elle un choix a offrir ? Oui quand le pilote sait changer et qu'une sortie au moins est detectee (ou que la sortie enregistree n'est plus la : on peut la remplacer)."""
        return self.disponible() and (bool(self.lister()) or choix is not None)

    def _poser(self, ident):
        """Recree le moteur audio sur la sortie `ident` (None : la sortie par defaut, qui suit celle de Windows). Les lecteurs en cours reprennent (pyglet)."""
        p = self._p()
        if ident is None: p.set_device(types.SimpleNamespace(id=None))
        else:
            d = next((d for d in self._g().get_output_devices() if str(d.id) == ident), None)
            if d is None: raise LookupError(ident)
            p.set_device(d)
        self.en_service = AUTO if ident is None else ident

    def appliquer(self, valeur):
        """Choix du joueur dans le menu : -> (reussi, choix a enregistrer). Automatique : sortie par defaut. Une sortie qui a disparu depuis la liste : rien ne change (reussi = False)."""
        if valeur == AUTO:
            if self.en_service == AUTO: return True, None
            try: self._poser(None)
            except Exception as ex:
                print('Sortie audio (automatique) impossible : %r' % (ex,), flush=True); return False, None
            return True, None
        nom = next((n for i, n in self.lister(True) if i == valeur), None)
        if nom is None: return False, None
        if self.en_service == valeur: return True, {'id': valeur, 'nom': nom}
        try: self._poser(valeur)
        except Exception as ex:
            print('Sortie audio « %s » impossible : %r' % (nom, ex), flush=True); return False, None
        return True, {'id': valeur, 'nom': nom}

    def appliquer_enregistree(self, choix):
        """Au lancement : remet la sortie enregistree si elle est branchee ; sinon le son reste sur la sortie par defaut (le choix est garde). -> True si une sortie a ete posee."""
        if choix is None or not self.disponible(): return False
        if not any(i == choix['id'] for i, _ in self.lister(True)):
            print('Sortie audio « %s » non branchée : sortie par défaut de Windows' % choix['nom'], flush=True); return False
        return self.appliquer(choix['id'])[0]
