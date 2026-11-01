"""Modeles 3D animes d'Unity (FbxObject : NativeManager.cmd_fbx_load = paquet 31, cmd_fbx = paquet 32).
Le moteur charge un modele « fbx/c<numero> » (prefab Resources : maillage skinne + composant Animation de style « legacy »), le place (position / rotation / echelle du monde), le colore
(Material.color de tous ses materiaux), lance ses animations (« Take 001 »...) et le montre ou le cache. Ici : les donnees extraites une fois du paquet de donnees (`Donnees.modele_fbx`),
l'evaluation des courbes d'animation (interpolation d'Hermite d'AnimationCurve), la pose des os, le skinnage (chaque sommet suit son os) et un lecteur qui reproduit Animation.Play / PlayQueued / CrossFade.
Tout est en coordonnees du monde d'Unity (main gauche), comme le reste de la visionneuse."""
import math
import numpy as np

FPS_MOTEUR = 30.0            # le moteur compte en images de 1/30 s ; l'animation d'Unity avance en secondes (la duree de « Take 001 » du dragon, 21,98 s, vaut les 659 images que le moteur attend avant « Take 002 »)
FONDU_ANIM = 0.3             # FbxObject.m_blend_time : duree du fondu enchaine (Animation.CrossFade) quand l'animation precedente est une boucle
LOOP = 2                     # WrapMode.Loop


def quat_mat(q):
    """Matrices de rotation (n, 3, 3) de quaternions (n, 4) x y z w (formule d'Unity)."""
    q = np.atleast_2d(np.asarray(q, float)); n = np.linalg.norm(q, axis=1, keepdims=True); q = q / np.where(n > 0, n, 1.0)
    x, y, z, w = q[:, 0], q[:, 1], q[:, 2], q[:, 3]
    R = np.empty((len(q), 3, 3))
    R[:, 0, 0] = 1 - 2 * (y * y + z * z); R[:, 0, 1] = 2 * (x * y - z * w); R[:, 0, 2] = 2 * (x * z + y * w)
    R[:, 1, 0] = 2 * (x * y + z * w); R[:, 1, 1] = 1 - 2 * (x * x + z * z); R[:, 1, 2] = 2 * (y * z - x * w)
    R[:, 2, 0] = 2 * (x * z - y * w); R[:, 2, 1] = 2 * (y * z + x * w); R[:, 2, 2] = 1 - 2 * (x * x + y * y)
    return R


def rot_euler(ex, ey, ez):
    """Quaternion.Euler (degres) : rotation de z, puis de x, puis de y (main gauche), comme `fenetre.rot_unity`."""
    cx, sx, cy, sy, cz, sz = (math.cos(math.radians(ex)), math.sin(math.radians(ex)), math.cos(math.radians(ey)), math.sin(math.radians(ey)), math.cos(math.radians(ez)), math.sin(math.radians(ez)))
    Rx = np.array([[1, 0, 0], [0, cx, -sx], [0, sx, cx]]); Ry = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]]); Rz = np.array([[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]])
    return Ry @ Rx @ Rz


def matrice_objet(pos, euler, echelle):
    """Transform.position / rotation (Quaternion.Euler) / localScale d'un objet sans parent -> matrice 4x4 objet -> monde."""
    M = np.eye(4); M[:3, :3] = rot_euler(*euler) @ np.diag(echelle); M[:3, 3] = pos
    return M


class Courbe:
    """AnimationCurve (cles : temps, valeur, pente d'entree, pente de sortie) : interpolation cubique d'Hermite ; une pente infinie = marche d'escalier."""
    def __init__(self, t, v, ent, sor):
        self.t = np.asarray(t, float); self.v = np.asarray(v, float); self.ent = np.asarray(ent, float); self.sor = np.asarray(sor, float)

    def valeur(self, x):
        t = self.t
        if len(t) == 1 or x <= t[0]: return self.v[0]
        if x >= t[-1]: return self.v[-1]
        i = int(np.searchsorted(t, x, side='right')) - 1
        dt = t[i + 1] - t[i]
        if dt <= 0: return self.v[i + 1]
        s = (x - t[i]) / dt
        m0, m1 = self.sor[i], self.ent[i + 1]
        if not (np.all(np.isfinite(m0)) and np.all(np.isfinite(m1))): return self.v[i]
        s2 = s * s; s3 = s2 * s
        return (2 * s3 - 3 * s2 + 1) * self.v[i] + (s3 - 2 * s2 + s) * dt * m0 + (-2 * s3 + 3 * s2) * self.v[i + 1] + (s3 - s2) * dt * m1


class ModeleFbx:
    """Un modele (donnees de `Donnees.modele_fbx`) : hierarchie d'os, maillage skinne, texture, animations."""
    def __init__(self, d):
        self.d = d
        self.parent = list(d['parent']); self.n_t = len(self.parent)
        self.p0 = np.asarray(d['pos'], float); self.q0 = np.asarray(d['rot'], float); self.s0 = np.asarray(d['scl'], float)
        self.noms = d['noms']
        self.v = np.asarray(d['v'], np.float32); self.uv = np.asarray(d['uv'], np.float32)
        self.bi = np.asarray(d['bi'], np.int64).reshape(len(self.v), -1); self.bw = np.asarray(d['bw'], np.float32).reshape(len(self.v), -1)
        self.bind = np.asarray(d['bind'], float); self.os = np.asarray(d['bones'], np.int64)
        self.tri = np.asarray(d['tri'], np.int64).reshape(-1, 3)
        self.tex = d['tex']
        self.vh = np.c_[self.v.astype(float), np.ones(len(self.v))]
        self.clips = {}
        for nom, c in d['clips'].items():
            self.clips[nom] = {'dur': float(c['dur']), 'wrap': int(c['wrap']), 'courbes': [(i, genre, Courbe(t, v, ent, sor)) for i, genre, t, v, ent, sor in c['courbes']]}

    # ---- pose
    def locales(self, poses):
        """Pose locale de chaque transformation : repos, remplace par les courbes des animations. `poses` = [(nom du clip, temps en secondes, poids)] (poids cumules = 1 : fondu enchaine)."""
        p = self.p0.copy(); q = self.q0.copy(); s = self.s0.copy()
        poses = [x for x in poses if x[0] in self.clips]
        if not poses: return p, q, s
        wtot = sum(w for _, _, w in poses) or 1.0
        repos = {'pos': self.p0, 'rot': self.q0, 'scl': self.s0}; cibles = {'pos': p, 'rot': q, 'scl': s}
        vals = []                                                      # une table {(os, genre): valeur} par clip
        for nom, t, w in poses: vals.append({(i, genre): cb.valeur(t) for i, genre, cb in self.clips[nom]['courbes']})
        for cle in set().union(*[v.keys() for v in vals]):
            i, genre = cle
            cibles[genre][i] = sum(w * v.get(cle, repos[genre][i]) for (_, _, w), v in zip(poses, vals)) / wtot
        return p, q, s

    def sommets(self, M_obj, poses):
        """Positions monde (n, 3) des sommets du maillage skinne ; M_obj = matrice monde de la racine du modele (position, rotation, echelle donnees par le moteur)."""
        p, q, s = self.locales(poses)
        R = quat_mat(q)
        W = np.empty((self.n_t, 4, 4))
        for i in range(self.n_t):
            L = np.eye(4); L[:3, :3] = R[i] * s[i][None, :]; L[:3, 3] = p[i]
            W[i] = (M_obj @ L) if self.parent[i] < 0 else (W[self.parent[i]] @ L)
        BM = W[self.os] @ self.bind                                    # matrice de skinnage de chaque os : os dans le monde x pose de liaison
        out = np.zeros((len(self.v), 3))
        for k in range(self.bi.shape[1]):
            w = self.bw[:, k]
            if not np.any(w): continue
            out += w[:, None] * np.einsum('nij,nj->ni', BM[self.bi[:, k]], self.vh)[:, :3]
        return out.astype(np.float32)


class LecteurAnim:
    """Animation d'un objet (UnityEngine.Animation, ce que fait FbxObject.PlayAnimation) pilotee par les images du moteur :
    * pas d'animation lancee : modele a sa pose de repos ;
    * Play (force, ou rien ne joue) : le clip repart du debut ; sinon, si l'animation en cours est une boucle (m_mode = Loop) : CrossFade (fondu de 0,3 s) ; sinon PlayQueued (le clip attend la fin du courant) ;
    * temps du clip : Once / Default / ClampForever = bloque sur la derniere image, Loop = modulo la duree."""
    def __init__(self, clips):
        self.clips = clips                       # {nom: {'dur', 'wrap'}}
        self.cur = None                          # [nom, image de depart (flottante)]
        self.file = []                           # clips en attente (PlayQueued)
        self.fondu = None                        # (ancien clip [nom, depart], image de debut du fondu)
        self.mode = 0                            # wrapMode du dernier clip lance (FbxObject.m_mode)

    @staticmethod
    def nom(seq): return 'Take %03d' % (seq + 1)

    def _fini(self, c, image):
        cl = self.clips.get(c[0])
        return cl is not None and cl['wrap'] != LOOP and (image - c[1]) / FPS_MOTEUR >= cl['dur']

    def jouer(self, seq, force, image):
        nom = self.nom(seq)
        if nom not in self.clips: return
        self.maj(image)
        joue = self.cur is not None and not self._fini(self.cur, image)
        if force or not joue:
            self.cur = [nom, float(image)]; self.file = []; self.fondu = None
        elif self.mode == LOOP:
            self.fondu = (list(self.cur), float(image)); self.cur = [nom, float(image)]; self.file = []
        else:
            self.file.append(nom)
        self.mode = self.clips[nom]['wrap']

    def maj(self, image):
        """Passe aux clips en attente quand le courant est fini (le suivant part exactement a la fin du precedent)."""
        while self.cur is not None and self.file and self._fini(self.cur, image):
            fin = self.cur[1] + self.clips[self.cur[0]]['dur'] * FPS_MOTEUR
            self.cur = [self.file.pop(0), fin]
        if self.fondu is not None and (image - self.fondu[1]) / FPS_MOTEUR >= FONDU_ANIM: self.fondu = None

    def poses(self, image):
        """[(clip, temps en secondes, poids)] a l'image (flottante) du moteur."""
        self.maj(image)
        if self.cur is None: return []
        def temps(c):
            cl = self.clips[c[0]]; t = max(0.0, (image - c[1]) / FPS_MOTEUR)
            if cl['wrap'] == LOOP and cl['dur'] > 0: t %= cl['dur']
            return min(t, cl['dur'])
        if self.fondu is not None and self.fondu[0][0] in self.clips:
            w = min(1.0, max(0.0, (image - self.fondu[1]) / FPS_MOTEUR / FONDU_ANIM))
            return [(self.fondu[0][0], temps(self.fondu[0]), 1.0 - w), (self.cur[0], temps(self.cur), w)]
        return [(self.cur[0], temps(self.cur), 1.0)]
