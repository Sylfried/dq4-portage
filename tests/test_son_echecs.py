"""#221 (audit SND-10 et SND-12) : un echec de lecture ne coupe plus le son jusqu'a la fermeture du jeu : ECHECS_MAX echecs de suite le coupent un moment, nouvel essai tout seul (delais croissants), la musique
demandee pendant la coupure est relancee au retour, tout est note dans le journal ; les erreurs avalees (volumes, reprise apres pause) sont notees une fois. Sans fenetre ni carte son (faux lecteurs).
    python3 tests/test_son_echecs.py"""
import os, sys, time, unittest
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from dq4_pc import langue as _LANGUE; _LANGUE.regler('fr')          # (D-238 : ces tests attendent les textes francais, quelle que soit la langue de l'ordinateur)
sys.modules['pyglet'] = None                                             # pas de pyglet : Son le prend pour « son indisponible », on lui donne de faux lecteurs
from dq4_pc import son as SON


class Panne:
    en_panne = False                                                     # vrai : tout nouveau lecteur refuse de jouer (peripherique retire)
    volume_refuse = False


class FauxLecteur:
    def __init__(self): self.playing = False; self._volume = 1.0
    @property
    def volume(self): return self._volume
    @volume.setter
    def volume(self, v):
        if Panne.volume_refuse: raise OSError('volume refuse')
        self._volume = v
    def queue(self, src): pass
    def play(self):
        if Panne.en_panne: raise OSError('peripherique retire')
        self.playing = True
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
    Panne.en_panne = False; Panne.volume_refuse = False
    journal, alertes = [], []
    s = SON.Son('inexistant.apk', '/tmp', log=lambda *a: None, journal=journal.append, alerte=alertes.append)
    s.ok = True; s.ogg = True; s.media = FauxMedia; s.AudioFormat = lambda **kw: kw; s.AudioData = None
    SON.SourceBoucle = FauxSource
    for i in (300, 316, 400): s.dec['SE%04d' % i] = donnees(1.0, False)
    s.dec['BGM02'] = donnees(60.0, True); s.dec['BGM05'] = donnees(60.0, True)
    return s, journal, alertes


class Echecs(unittest.TestCase):
    def test_fonctionnement_normal_sans_trace(self):
        s, j, a = nouveau_son()
        s.jouer_se(300); s.jouer_bgm(2); s.jouer_se(316)
        self.assertTrue(s.ok); self.assertEqual((s.echecs, s.pannes, j, a), (0, 0, [], []))

    def test_un_echec_ou_deux_ne_coupent_pas(self):
        s, j, a = nouveau_son(); Panne.en_panne = True
        s.jouer_se(300); s.jouer_se(316)
        self.assertTrue(s.ok); self.assertEqual(s.echecs, 2); self.assertEqual(len(j), 2); self.assertEqual(a, [])
        Panne.en_panne = False; s.jouer_se(400)                                     # un son qui part remet le compteur a zero
        self.assertEqual(s.echecs, 0); self.assertTrue(s.ok); self.assertEqual(a, [])

    def test_trois_echecs_de_suite_coupent_puis_nouvel_essai(self):
        s, j, a = nouveau_son(); Panne.en_panne = True
        for i in (300, 316, 400): s.jouer_se(i)
        self.assertFalse(s.ok); self.assertIsNotNone(s.reessai); self.assertEqual(len(a), 1); self.assertIn('interrompu', a[0])
        self.assertTrue(any('interrompu' in l for l in j)); self.assertAlmostEqual(s.reessai - time.time(), SON.DELAIS_REESSAI[0], delta=0.5)
        s.tick(); self.assertFalse(s.ok)                                            # trop tot : rien
        s.reessai = time.time() - 1; s.tick()                                       # delai ecoule : le son est rouvert
        self.assertTrue(s.ok); self.assertIsNone(s.reessai); self.assertEqual(s.echecs, SON.ECHECS_MAX - 1)
        s.jouer_se(300)                                                             # toujours en panne : un seul echec recoupe, delai plus long
        self.assertFalse(s.ok); self.assertAlmostEqual(s.reessai - time.time(), SON.DELAIS_REESSAI[1], delta=0.5)
        s.reessai = time.time() - 1; s.tick(); Panne.en_panne = False              # la sortie est revenue
        s.jouer_se(300)
        self.assertTrue(s.ok); self.assertEqual(s.echecs, 0); self.assertEqual(len(a), 3); self.assertIn('rétabli', a[-1]); self.assertTrue(any('retabli' in l for l in j))
        s.jouer_se(316); self.assertEqual(len(a), 3)                                # le retour n'est annonce qu'une fois

    def test_delais_croissants_puis_constants(self):
        s, j, a = nouveau_son(); Panne.en_panne = True; vus = []
        for _ in range(6):
            for i in (300, 316, 400): s.jouer_se(i)
            vus.append(round(s.reessai - time.time())); s.reessai = time.time() - 1; s.tick()
        self.assertEqual(vus[:3], [2, 10, 30]); self.assertTrue(all(v == 30 for v in vus[2:]), vus)

    def test_musique_demandee_pendant_la_coupure_relancee_au_retour(self):
        s, j, a = nouveau_son(); Panne.en_panne = True
        for i in (300, 316, 400): s.jouer_se(i)
        self.assertFalse(s.ok)
        s.evenements([(37, 2)]); s.evenements([(35, 300)])                          # le moteur demande la musique 2 : retenue (le bruitage est perdu)
        self.assertEqual(s.bgm_perdue, 2); self.assertIsNone(s.bgm)
        Panne.en_panne = False; s.reessai = time.time() - 1; s.tick()
        self.assertTrue(s.ok); self.assertIsNotNone(s.bgm); self.assertEqual(s.bgm_id, 2); self.assertIsNone(s.bgm_perdue)
        self.assertEqual(s.echecs, 0)                                               # la musique est partie : retabli

    def test_arret_pendant_la_coupure_supprime_la_musique_a_relancer(self):
        s, j, a = nouveau_son(); Panne.en_panne = True
        for i in (300, 316, 400): s.jouer_se(i)
        s.evenements([(37, 2)]); s.evenements([(37, SON.BGM_ARRET)])
        self.assertIsNone(s.bgm_perdue)
        s.evenements([(37, 5), (37, SON.BGM_RELANCE + 8)]); self.assertEqual(s.bgm_perdue, 5)       # un jingle a reprise ne remplace pas la musique de fond

    def test_musique_ratee_est_gardee_pour_le_retour(self):
        s, j, a = nouveau_son(); Panne.en_panne = True
        s.jouer_bgm(2)
        self.assertEqual(s.bgm_perdue, 2); self.assertEqual(s.echecs, 1)
        s.jouer_bgm(SON.BGM_RELANCE + 5)                                           # un jingle rate n'est pas a relancer
        self.assertEqual(s.bgm_perdue, 2)

    def test_son_coupe_ne_tente_rien(self):
        s, j, a = nouveau_son(); Panne.en_panne = True
        for i in (300, 316, 400): s.jouer_se(i)
        n = len(j); s.jouer_se(300); s.jouer_se(316); s.jouer_bgm(5)                 # appels directs (clic de menu...) pendant la coupure : ni essai ni echec ni ligne de journal
        self.assertEqual((len(j), s.pannes, s.echecs), (n, 1, 3)); self.assertEqual(s.bgm_perdue, 5)

    def test_son_absent_des_le_depart_ne_reessaie_pas(self):
        s, j, a = nouveau_son(); s.ok = False                                       # pas de pilote audio (import de pyglet impossible) : ni coupure ni nouvel essai
        s.tick(); self.assertFalse(s.ok); self.assertIsNone(s.reessai)


class ErreursAvalees(unittest.TestCase):
    def test_volume_refuse_note_une_fois(self):
        s, j, a = nouveau_son(); s.jouer_bgm(2); s.jouer_se(300)
        Panne.volume_refuse = True
        s.regler_mixage(general=0.5); s.regler_mixage(general=0.4)
        lignes = [l for l in j if 'volume' in l]
        self.assertEqual(len(lignes), 2, lignes)                                    # une fois pour la musique, une fois pour les bruitages, pas a chaque reglage
        self.assertTrue(s.ok)

    def test_reprise_apres_pause_refusee_notee_une_fois(self):
        s, j, a = nouveau_son(); s.jouer_bgm(2)
        s.mettre_en_pause(True); Panne.en_panne = True
        s.mettre_en_pause(False); s.mettre_en_pause(True); s.mettre_en_pause(False)
        self.assertEqual(len([l for l in j if 'reprise' in l]), 1)

    def test_journal_plafonne(self):
        s, j, a = nouveau_son()
        for k in range(100): s._noter('essai %d' % k)
        self.assertEqual(len(j), SON.NOTES_MAX)

    def test_journal_ou_alerte_defaillants_ne_cassent_rien(self):
        s, j, a = nouveau_son()
        def casse(t): raise RuntimeError('disque plein')
        s.journal = casse; s.alerte = casse; Panne.en_panne = True
        for i in (300, 316, 400): s.jouer_se(i)
        self.assertFalse(s.ok)


if __name__ == '__main__': unittest.main(verbosity=1)
