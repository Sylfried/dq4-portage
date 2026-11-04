"""#229 (audit SND-05 et SND-06) : deux cas limites de la musique, comme dans le jeu d'origine (Sound.StopBGM / PlayBGM de SoundControl).
- Un arret de la musique PENDANT un jingle lance avec reprise (0x1000 | n) ne remet pas l'etat du jingle a zero dans Unity : la musique d'avant repart (depuis le debut). Sans jingle en cours, l'arret arrete.
- Un morceau sans boucle arrive a sa fin n'est plus « en cours » : le redemander le relance. Un morceau en train de jouer (en boucle ou non) redemande n'est pas relance (le moteur ne le redemande pas).
Sans fenetre ni carte son (faux lecteurs).
    python3 tests/test_son_musique_limites.py"""
import os, sys, time, unittest
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
sys.modules['pyglet'] = None                                             # pas de pyglet : Son le prend pour « son indisponible », on lui donne de faux lecteurs
from dq4_pc import son as SON


class FauxLecteur:
    def __init__(self): self.playing = False; self.volume = 1.0
    def queue(self, src): pass
    def play(self): self.playing = True
    def pause(self): self.playing = False
    def delete(self): self.playing = False


class FauxMedia:
    Player = FauxLecteur


class FauxSource:
    def __init__(self, *a): self.pos = 0


def donnees(secondes, boucle):
    n = int(secondes * 1000)
    return dict(pcm=np.zeros((n, 1), np.int16), frequence=1000, debut=n // 4 if boucle else 0, fin=n if boucle else 0, volume=1.0, boucle=boucle)


def nouveau_son():
    s = SON.Son('inexistant.apk', '/tmp', log=lambda *a: None, journal=lambda *a: None, alerte=lambda *a: None)
    s.ok = True; s.ogg = True; s.media = FauxMedia; s.AudioFormat = lambda **kw: kw; s.AudioData = None
    SON.SourceBoucle = FauxSource
    s.dec['BGM02'] = donnees(60.0, True)                    # musique en boucle
    s.dec['BGM01'] = donnees(5.0, False)                    # musique sans boucle (comme BGM 1 et 34)
    s.dec['BGM48'] = donnees(3.0, False)                    # jingle (coffre)
    return s


RELANCE = SON.BGM_RELANCE; ARRET = SON.BGM_ARRET


class ArretPendantUnJingle(unittest.TestCase):
    def test_arret_pendant_un_jingle_a_reprise_la_musique_d_avant_repart(self):
        s = nouveau_son(); s.jouer_bgm(2); s.jouer_bgm(RELANCE | 48)
        self.assertEqual(s.bgm_id, 48); self.assertEqual(s.reprise, 2)
        p = s.bgm; s.jouer_bgm(ARRET | 4)
        self.assertEqual(s.bgm_id, 2); self.assertIsNotNone(s.bgm); self.assertIsNot(s.bgm, p); self.assertIsNone(s.reprise); self.assertIsNone(s.bgm_fin)      # (la musique d'avant, en boucle, depuis le debut)

    def test_arret_sans_jingle_arrete(self):
        s = nouveau_son(); s.jouer_bgm(2); s.jouer_bgm(ARRET | 4)
        self.assertIsNone(s.bgm_id); self.assertIsNone(s.bgm); self.assertIsNone(s.reprise)

    def test_arret_apres_la_fin_du_jingle_arrete_la_musique_reprise(self):
        s = nouveau_son(); s.jouer_bgm(2); s.jouer_bgm(RELANCE | 48)
        s.bgm_fin = time.time() - 1.0; s.tick()                                    # fin du jingle : la musique d'avant reprend toute seule
        self.assertEqual(s.bgm_id, 2); self.assertIsNone(s.reprise)
        s.jouer_bgm(ARRET | 4); self.assertIsNone(s.bgm_id); self.assertIsNone(s.bgm)

    def test_jingle_sans_musique_d_avant_puis_arret_reste_muet(self):
        s = nouveau_son(); s.jouer_bgm(RELANCE | 48); self.assertIsNone(s.reprise)
        s.jouer_bgm(ARRET | 4); self.assertIsNone(s.bgm_id); self.assertIsNone(s.bgm)

    def test_deux_arrets_de_suite(self):
        s = nouveau_son(); s.jouer_bgm(2); s.jouer_bgm(RELANCE | 48); s.jouer_bgm(ARRET | 4); s.jouer_bgm(ARRET | 4)          # (le premier relance la musique, le second l'arrete)
        self.assertIsNone(s.bgm_id); self.assertIsNone(s.bgm)

    def test_un_nouvel_ordre_apres_l_arret(self):
        s = nouveau_son(); s.jouer_bgm(2); s.jouer_bgm(RELANCE | 48); s.jouer_bgm(ARRET | 4); s.jouer_bgm(1)
        self.assertEqual(s.bgm_id, 1); self.assertIsNone(s.reprise)


class MemeMusiqueRedemandee(unittest.TestCase):
    def test_en_cours_en_boucle_n_est_pas_relancee(self):
        s = nouveau_son(); s.jouer_bgm(2); p = s.bgm; s.jouer_bgm(2); self.assertIs(s.bgm, p)

    def test_sans_boucle_en_cours_n_est_pas_relancee(self):
        s = nouveau_son(); s.jouer_bgm(1); p = s.bgm; s.jouer_bgm(1); self.assertIs(s.bgm, p)

    def test_sans_boucle_arrivee_a_sa_fin_est_relancee(self):
        s = nouveau_son(); s.jouer_bgm(1); p = s.bgm; s.bgm_fin = time.time() - 1.0
        s.jouer_bgm(1); self.assertIsNot(s.bgm, p); self.assertEqual(s.bgm_id, 1); self.assertGreater(s.bgm_fin, time.time() + 3.0)

    def test_en_pause_le_morceau_n_est_pas_fini(self):
        s = nouveau_son(); s.jouer_bgm(1); p = s.bgm; s.bgm_fin = time.time() - 1.0; s.t_pause = time.time()
        s.jouer_bgm(1); self.assertIs(s.bgm, p)

    def test_une_autre_musique_remplace_toujours(self):
        s = nouveau_son(); s.jouer_bgm(2); p = s.bgm; s.jouer_bgm(1); self.assertEqual(s.bgm_id, 1); self.assertIsNot(s.bgm, p)


if __name__ == '__main__':
    unittest.main(verbosity=1)
