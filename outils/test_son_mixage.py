"""Test du mixage du son (categories, volumes, interrupteurs) sans fenetre ni carte son : les lecteurs de pyglet sont remplaces par de faux lecteurs qui gardent leur volume.

    python3 outils/test_son_mixage.py
"""
import os, sys, unittest
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'dq4_pc'))
sys.modules['pyglet'] = None                                             # (pas de pyglet : ni fenetre ni pilote audio ; Son le prend pour « son indisponible » et on lui donne de faux lecteurs)
import son as SON


class FauxLecteur:
    def __init__(self): self.volume = 1.0; self.playing = False; self.supprime = False
    def queue(self, src): pass
    def play(self): self.playing = True
    def pause(self): self.playing = False
    def delete(self): self.supprime = True; self.playing = False


class FauxSource:
    def __init__(self, *a): self.pos = 0


class FauxMedia:
    Player = FauxLecteur
    Source = object


def donnees(secondes, boucle, volume=1.0, frequence=1000):
    n = int(secondes * frequence)
    return dict(pcm=np.zeros((n, 1), np.int16), frequence=frequence, debut=0 if not boucle else n // 4, fin=0 if not boucle else n, volume=volume, boucle=boucle)


def nouveau_son():
    s = SON.Son('inexistant.apk', '/tmp', log=lambda *a: None)
    s.ok = True; s.ogg = True; s.media = FauxMedia; s.AudioFormat = lambda **kw: kw; s.AudioData = None
    SON.SourceBoucle = FauxSource
    for i in (300, 316, 400, 500): s.dec['SE%04d' % i] = donnees(1.0, False, volume=0.5)
    s.dec['SE0500'] = donnees(2.0, True, volume=1.0)                      # bruitage en boucle
    s.dec['BGM02'] = donnees(60.0, True, volume=0.8)                       # musique (boucle)
    s.dec['BGM08'] = donnees(5.0, False, volume=1.0)                       # jingle (court, sans boucle)
    s.dec['BGM01'] = donnees(111.0, False, volume=1.0)                     # morceau long sans boucle : de la musique
    return s


class Categories(unittest.TestCase):
    def test_se(self):
        for i in range(300, 305): self.assertEqual(SON.categorie_se(i), 'interface')
        for i in (299, 305, 316, 501, 1129): self.assertEqual(SON.categorie_se(i), 'effets')

    def test_bgm(self):
        self.assertEqual(SON.categorie_bgm(False, True, 60.0), 'musique')               # en boucle
        self.assertEqual(SON.categorie_bgm(False, False, 5.0), 'jingles')               # court sans boucle
        self.assertEqual(SON.categorie_bgm(True, False, 5.0), 'jingles')                # demande avec reprise de la musique d'avant
        self.assertEqual(SON.categorie_bgm(False, False, 111.0), 'musique')             # long sans boucle
        self.assertEqual(SON.categorie_bgm(True, True, 5.0), 'musique')                 # en boucle : on ne revient jamais a la musique d'avant

    def test_option_du_jeu(self):
        self.assertEqual([round(SON.volume_option_jeu(i), 2) for i in range(5)], [0.2, 0.4, 0.6, 0.8, 1.0])
        self.assertEqual(SON.volume_option_jeu(9), 1.0); self.assertEqual(SON.volume_option_jeu(-3), 0.2)


class Gain(unittest.TestCase):
    def test_defaut(self):
        m = SON.Mixage()
        for c in SON.CATEGORIES: self.assertEqual(m.gain(c), 1.0)

    def test_produit(self):
        m = SON.Mixage(general=0.5, musique=0.8, jingles=0.6, effets=0.4, interface=0.2)
        self.assertAlmostEqual(m.gain('musique'), 0.4); self.assertAlmostEqual(m.gain('jingles'), 0.3)
        self.assertAlmostEqual(m.gain('effets'), 0.2); self.assertAlmostEqual(m.gain('interface'), 0.1)
        self.assertAlmostEqual(m.gain('musique', 0.5), 0.2)                                 # volume propre au fichier
        m.jeu['musique'] = 0.6; m.jeu['effets'] = 0.2                                      # options « volume » du jeu : musique + jingles / bruitages + interface
        self.assertAlmostEqual(m.gain('musique'), 0.24); self.assertAlmostEqual(m.gain('jingles'), 0.18)
        self.assertAlmostEqual(m.gain('effets'), 0.04); self.assertAlmostEqual(m.gain('interface'), 0.02)

    def test_interrupteur_et_bornes(self):
        m = SON.Mixage(); m.actif['effets'] = False
        self.assertEqual(m.gain('effets'), 0.0); self.assertEqual(m.gain('interface'), 1.0)
        m.general = 3.0; self.assertEqual(m.gain('musique'), 1.0)                          # jamais plus de 1
        m.general = -1.0; self.assertEqual(m.gain('musique'), 0.0)


class Lecture(unittest.TestCase):
    def test_volumes_appliques_tout_de_suite(self):
        s = nouveau_son()
        s.jouer_bgm(2); s.jouer_se(300); s.jouer_se(316)
        self.assertEqual(s.bgm_cat, 'musique'); self.assertAlmostEqual(s.bgm.volume, 0.8)
        v = {x.ident: x for x in s.se}
        self.assertEqual(v[300].cat, 'interface'); self.assertEqual(v[316].cat, 'effets')
        self.assertAlmostEqual(v[300].p.volume, 0.5); self.assertAlmostEqual(v[316].p.volume, 0.5)
        s.regler_mixage(general=0.5, volumes={'musique': 0.5, 'effets': 0.2, 'interface': 1.0})
        self.assertAlmostEqual(s.bgm.volume, 0.5 * 0.5 * 0.8)                              # la musique en cours change
        self.assertAlmostEqual(v[316].p.volume, 0.5 * 0.2 * 0.5)                           # les bruitages en cours aussi
        self.assertAlmostEqual(v[300].p.volume, 0.5 * 1.0 * 0.5)

    def test_interrupteurs(self):
        s = nouveau_son()
        s.jouer_bgm(2); s.jouer_se(316)
        s.regler_mixage(actifs={'musique': False, 'effets': False})
        self.assertEqual(s.bgm.volume, 0.0); self.assertEqual(s.se[0].p.volume, 0.0)
        s.jouer_se(316); s.jouer_se(316)
        self.assertEqual(len(s.se), 1, 'un bruitage court n\'est pas joue quand sa categorie est coupee')
        s.jouer_se(300); self.assertEqual(len(s.se), 2, 'les sons de l\'interface restent actifs')
        s.regler_mixage(actifs={'musique': True, 'effets': True})
        self.assertAlmostEqual(s.bgm.volume, 0.8); self.assertAlmostEqual(s.se[0].p.volume, 0.5)

    def test_boucle_coupee_puis_rouverte(self):
        s = nouveau_son(); s.regler_mixage(actifs={'effets': False})
        s.jouer_se(500)
        self.assertEqual(len(s.se), 1, 'un bruitage en boucle est lance meme coupe (volume nul)')
        self.assertEqual(s.se[0].p.volume, 0.0)
        s.regler_mixage(actifs={'effets': True}); self.assertAlmostEqual(s.se[0].p.volume, 1.0)

    def test_jingle_et_reprise(self):
        s = nouveau_son()
        s.jouer_bgm(2); musique = s.bgm
        s.jouer_bgm(SON.BGM_RELANCE + 8)
        self.assertEqual(s.bgm_cat, 'jingles'); self.assertEqual(s.reprise, 2)
        s.regler_mixage(volumes={'jingles': 0.25, 'musique': 0.5}); self.assertAlmostEqual(s.bgm.volume, 0.25)
        s.regler_mixage(actifs={'jingles': False}); self.assertEqual(s.bgm.volume, 0.0)
        self.assertIsNot(s.bgm, musique)
        s.regler_mixage(actifs={'jingles': True})
        s.jouer_bgm(1)                                                                       # long morceau sans boucle : de la musique
        self.assertEqual(s.bgm_cat, 'musique'); self.assertAlmostEqual(s.bgm.volume, 0.5)

    def test_ecoute_pendant_la_pause(self):
        s = nouveau_son(); s.jouer_bgm(2); s.jouer_se(316)
        lecteurs = [s.bgm] + [x.p for x in s.se]
        s.mettre_en_pause(True); self.assertTrue(all(not p.playing for p in lecteurs))
        s.ecouter(True); self.assertTrue(all(p.playing for p in lecteurs), 'page Son : les sons reprennent')
        s.regler_mixage(volumes={'musique': 0.5}); self.assertAlmostEqual(s.bgm.volume, 0.4)
        s.ecouter(False); self.assertTrue(all(not p.playing for p in lecteurs), 'on quitte la page : de nouveau en pause')
        s.mettre_en_pause(False); self.assertTrue(all(p.playing for p in lecteurs))
        s.mettre_en_pause(True); s.ecouter(True); s.mettre_en_pause(False)
        self.assertFalse(s.ecoute); self.assertTrue(all(p.playing for p in lecteurs))

    def test_anciens_noms(self):
        s = nouveau_son(); s.regler_volumes(0.3, 0.6)
        self.assertAlmostEqual(s.vol_m, 0.3); self.assertAlmostEqual(s.vol_b, 0.6)
        self.assertAlmostEqual(s.mix.vol['musique'], 0.3); self.assertAlmostEqual(s.mix.vol['effets'], 0.6)


if __name__ == '__main__':
    unittest.main(verbosity=2)
