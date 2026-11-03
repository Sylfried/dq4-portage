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
        for i in (299, 305, 316, 408, 501, 1129): self.assertEqual(SON.categorie_se(i), 'effets')
        self.assertEqual(SON.categorie_se(409), 'jingles', 'fanfare de victoire')

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

    def test_bruitage_tout_juste_lance_jamais_libere_par_les_pas_suivants(self):
        """Marche acceleree : le moteur fait plusieurs pas (donc plusieurs tick()) a la suite dans la meme image affichee, juste apres l'ordre du bruitage de porte ou de sortie de village ; un lecteur qui ne se
        dit pas encore « en lecture » ne doit pas faire perdre le bruitage. Passe le delai de grace, un lecteur arrete est libere comme avant."""
        s = nouveau_son(); s.jouer_se(316); x = s.se[0]
        x.p.playing = False                                                  # (le lecteur ne s'annonce pas encore)
        for _ in range(8): s.tick()                                          # huit pas a la suite
        self.assertEqual(len(s.se), 1); self.assertFalse(x.p.supprime)
        x.debut -= SON.SE_GRACE + 0.01; s.tick()                             # delai de grace passe : lecteur arrete = bruitage libere
        self.assertEqual(s.se, []); self.assertTrue(x.p.supprime)

    def test_bruitage_en_lecture_garde_jusqu_a_sa_fin(self):
        s = nouveau_son(); s.jouer_se(316); x = s.se[0]
        x.debut -= 10.0; s.tick(); self.assertEqual(len(s.se), 1)             # en lecture : garde
        x.fin = 0.0; s.tick(); self.assertEqual(s.se, [])                    # duree depassee : libere

    def test_bruitages_de_transition_joues_en_entier(self):
        """Porte (309) puis transition de carte (305, demande par le moteur entre le debut du fondu et le chargement : voir test_bruitage_transition) : le chargement de la carte bloque la boucle jusqu'a 0,5 s et le moteur
        fait plusieurs pas a la suite (marche acceleree) ; les deux bruitages restent joues, a leur volume, jusqu'a la fin de leur duree d'origine, puis sont liberes."""
        s = nouveau_son(); s.dec['SE0309'] = donnees(1.5, False, volume=0.4); s.dec['SE0305'] = donnees(1.0, False, volume=0.5)
        s.evenements([(35, 309)]); [s.tick() for _ in range(6)]
        s.evenements([(35, 305)]); [s.tick() for _ in range(6)]
        self.assertEqual([x.ident for x in s.se], [309, 305]); self.assertEqual([x.cat for x in s.se], ['effets', 'effets'])
        self.assertEqual([round(x.p.volume, 3) for x in s.se], [0.4, 0.5])
        for x in s.se: x.debut -= 0.5; x.fin -= 0.5                          # le chargement de la carte a bloque la boucle 0,5 s
        s.tick()
        self.assertEqual([x.ident for x in s.se], [309, 305]); self.assertFalse(any(x.p.supprime for x in s.se))
        for x in s.se: x.debut -= 0.9; x.fin -= 0.9                          # 1,4 s ecoulees : le 305 (1,0 s + 0,5 s de marge) est encore la, le 309 (1,5 s) aussi
        s.tick(); self.assertEqual([x.ident for x in s.se], [309, 305])
        for x in s.se: x.fin = 0.0                                           # duree depassee : liberes
        s.tick(); self.assertEqual(s.se, [])

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

    def test_fanfare_de_victoire_est_un_jingle(self):
        """SE 409 (victoire) : volume et interrupteur de « Jingles et fanfares », mais l'option « bruitages » du jeu (pas celle de la musique)."""
        s = nouveau_son(); s.dec['SE0409'] = donnees(2.9, False, volume=0.6)
        s.regler_mixage(volumes={'jingles': 0.5, 'effets': 0.1}, jeu={'musique': 1.0, 'effets': 0.4})
        s.jouer_se(409); x = s.se[-1]
        self.assertEqual(x.cat, 'jingles'); self.assertAlmostEqual(x.p.volume, 0.5 * 0.6 * 0.4)
        s.regler_mixage(jeu={'musique': 0.2, 'effets': 1.0}); self.assertAlmostEqual(x.p.volume, 0.5 * 0.6, msg='regle tout de suite, avec l\'option des bruitages')
        s.regler_mixage(actifs={'jingles': False}); self.assertEqual(x.p.volume, 0.0)
        n = len(s.se); s.jouer_se(409); self.assertEqual(len(s.se), n, 'jingles coupes : la fanfare n\'est pas jouee')
        s.regler_mixage(actifs={'jingles': True, 'effets': False}); s.jouer_se(409); self.assertEqual(len(s.se), n + 1, 'bruitages coupes : la fanfare, elle, joue')

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


def attendre(s):
    """Laisse finir les decodages de fond, puis tick() (le decodage tourne dans un fil)."""
    for nom, (fut, rap) in list(s.jobs.items()): fut.result()
    s.tick()


class Precharge(unittest.TestCase):
    """SN : les musiques que le moteur demande puis arrete aussitot en combat (BGM 23 : defaite du groupe ; jingles) sont decodees d'avance et gardees en memoire."""

    def son(self):
        s = nouveau_son(); s.decodes = []
        def decode(nom): s.decodes.append(nom); return donnees(113.0 if nom == 'BGM23' else 4.0, nom == 'BGM03')       # (BGM 3 : la musique du moment, avec boucle)
        s._decode = decode
        return s

    def test_rien_avant_la_premiere_musique(self):
        s = self.son(); s.precharger_musiques((23, 47))
        for _ in range(3): attendre(s)
        self.assertEqual(s.decodes, [], 'tant qu\'aucune musique ne joue, rien n\'est decode d\'avance')
        s.jouer_bgm(3); attendre(s)                                                 # la musique du jeu passe la premiere
        self.assertEqual(s.decodes[0], 'BGM03'); self.assertIsNotNone(s.bgm)

    def test_une_musique_a_la_fois_puis_toutes_en_memoire(self):
        s = self.son(); s.jouer_bgm(3); attendre(s); s.precharger_musiques((47, 23, 9))
        attendre(s); self.assertEqual(len(s.jobs), 1, 'une seule musique a la fois')
        for _ in range(5): attendre(s)
        self.assertEqual(s.decodes, ['BGM03', 'BGM47', 'BGM23', 'BGM09'], 'dans l\'ordre demande')
        for nom in ('BGM47', 'BGM23', 'BGM09'): self.assertIn(nom, s.dec)

    def test_pas_devant_un_decodage_demande(self):
        s = self.son(); s.jouer_bgm(3); attendre(s); s.precharger_musiques((23,))
        s.jouer_bgm(5)                                                              # decodage demande par le moteur : le prechargement attend
        s.tick(); self.assertEqual(list(s.jobs), ['BGM05'], 'le prechargement ne passe pas devant un son demande')
        for _ in range(4): attendre(s)
        self.assertIn('BGM23', s.dec)

    def test_epingles_jamais_chassees(self):
        s = self.son(); s.jouer_bgm(3); attendre(s); s.precharger_musiques((23,))
        for _ in range(3): attendre(s)
        self.assertIn('BGM23', s.dec)
        for i in range(200): s.dec['SE%04d' % (1000 + i)] = donnees(0.1, False)
        s._purger()
        self.assertIn('BGM23', s.dec, 'une musique epinglee reste')
        self.assertLessEqual(len([k for k in s.dec if k not in s.epingles]), 80, 'le reste suit la regle des 80 sons')

    def test_defaite_demandee_puis_arretee_est_jouee(self):
        """Le moteur demande BGM 23 (tout le groupe est battu) : la musique part tout de suite, sans attendre un decodage que l'arret du moteur annulerait."""
        s = self.son(); s.jouer_bgm(3); attendre(s); s.precharger_musiques((23,))
        for _ in range(3): attendre(s)
        s.jouer_bgm(SON.BGM_ARRET); self.assertIsNone(s.bgm)
        s.jouer_bgm(23); self.assertIsNotNone(s.bgm, 'jouee dans l\'image meme de l\'ordre'); self.assertEqual(s.bgm_id, 23)
        self.assertEqual(s.jobs, {})

    def test_sans_prechargement_l_arret_annule_le_decodage(self):
        """Ce que le prechargement evite : musique non decodee, ordre puis arret avant la fin du decodage -> rien ne joue."""
        s = self.son(); s.jouer_bgm(23); s.jouer_bgm(SON.BGM_ARRET); attendre(s)
        self.assertIsNone(s.bgm)

    def test_desactive(self):
        s = self.son(); s.ok = False; s.precharger_musiques((23,)); self.assertEqual(s.fond, [])


class ProtectionJingle(unittest.TestCase):
    """SN : un jeu accelere (combat x2, x3) enchaine les ordres de musique du moteur plus vite : la fanfare etait coupee (montee de niveau, BGM 47 de 3,1 s : 1,75 s a x3). Un ordre qui serait arrive apres le jingle
    a vitesse normale attend l'heure ou il serait arrive (image du moteur, 30 par seconde) ou la fin du jingle ; sans image du moteur, rien ne change. Horloge simulee ; jingle = BGM 8 (5 s), musique = BGM 2 (boucle)."""

    def setUp(self):
        import types
        self.h = 1000.0; self.ancien = SON.time
        SON.time = types.SimpleNamespace(time=lambda: self.h)
        self.s = nouveau_son()

    def tearDown(self): SON.time = self.ancien

    def ordre(self, v, e, dt=0.0):
        self.h += dt; self.s.evenements([(37, v)], image_moteur=e); self.s.tick()

    def avance(self, dt): self.h += dt; self.s.tick()

    def lancer_jingle(self, v=8, e=100, relance=False):
        s = self.s; self.ordre(2, 0); self.assertEqual(s.bgm_id, 2)
        self.ordre(v | (SON.BGM_RELANCE if relance else 0), e); self.assertEqual(s.bgm_cat, 'jingles'); self.t0 = self.h

    def test_vitesse_normale_rien_ne_change(self):
        s = self.s; self.lancer_jingle()
        self.ordre(SON.BGM_ARRET, 160, dt=2.0)                                      # image 160 = 2 s apres l'image 100 : l'heure qu'il est
        self.assertIsNone(s.bgm); self.assertEqual(len(s.attente_bgm), 0)

    def test_x3_arret_retenu_jusqu_a_l_heure_normale(self):
        s = self.s; self.lancer_jingle()
        self.ordre(SON.BGM_ARRET, 160, dt=0.7)                                      # a x3 : l'ordre de l'image 160 arrive a 0,7 s au lieu de 2 s
        self.assertEqual(s.bgm_id, 8); self.assertIsNotNone(s.bgm); self.assertEqual(len(s.attente_bgm), 1)
        self.avance(1.2); self.assertIsNotNone(s.bgm, '1,9 s : pas encore')
        self.avance(0.15); self.assertIsNone(s.bgm, '2,05 s : l\'ordre part a l\'heure normale'); self.assertEqual(len(s.attente_bgm), 0)

    def test_ordre_apres_la_fin_du_jingle_part_a_la_fin_du_jingle(self):
        s = self.s; self.lancer_jingle()
        self.ordre(SON.BGM_ARRET, 400, dt=1.0); self.ordre(2, 430, dt=0.1)               # images 400 et 430 : 10 s et 11 s apres (le jingle dure 5 s)
        self.assertEqual(len(s.attente_bgm), 2)
        self.avance(3.8); self.assertEqual(len(s.attente_bgm), 2, '4,9 s : le jingle joue encore')
        self.avance(0.2)
        self.assertEqual(len(s.attente_bgm), 0); self.assertEqual(s.bgm_id, 2, 'les ordres partent dans l\'ordre : arret puis musique 2'); self.assertEqual(s.bgm_cat, 'musique')

    def test_bruitages_jamais_retenus(self):
        s = self.s; self.lancer_jingle()
        self.ordre(SON.BGM_ARRET, 300, dt=0.5); s.evenements([(35, 316)], image_moteur=301)
        self.assertEqual([x.ident for x in s.se], [316])

    def test_sans_image_du_moteur_ou_sans_jingle_ou_jingles_coupes(self):
        s = self.s; self.lancer_jingle()
        s.evenements([(37, SON.BGM_ARRET)]); self.assertIsNone(s.bgm, 'sans image du moteur : tout de suite')
        self.ordre(2, 0); self.ordre(5, 10, dt=0.1); self.assertEqual(len(s.attente_bgm), 0, 'une musique avec boucle n\'est pas un jingle')
        s.regler_mixage(actifs={'jingles': False}); self.ordre(8, 100); self.ordre(SON.BGM_ARRET, 500, dt=0.1)
        self.assertIsNone(s.bgm, 'jingles coupes : rien a proteger')

    def test_jingle_avec_reprise_puis_jingle_suivant(self):
        s = self.s; self.lancer_jingle(relance=True); self.assertEqual(s.reprise, 2)
        self.ordre(SON.BGM_RELANCE + 8, 400, dt=1.0)                                  # 2e fanfare, apres la fin de la 1re a vitesse normale
        self.assertEqual(len(s.attente_bgm), 1); self.assertEqual(s.bgm_id, 8)
        self.avance(4.1)
        self.assertEqual(len(s.attente_bgm), 0); self.assertEqual(s.bgm_id, 8); self.assertEqual(s.reprise, 2, 'la musique d\'avant a repris, puis le 2e jingle l\'a gardee a reprendre (pas le 1er jingle)')

    def test_pause_ne_libere_rien(self):
        s = self.s; self.lancer_jingle()
        self.ordre(SON.BGM_ARRET, 160, dt=0.5)
        s.mettre_en_pause(True); self.avance(100.0); self.assertEqual(len(s.attente_bgm), 1)
        s.mettre_en_pause(False); self.assertEqual(len(s.attente_bgm), 1, 'la pause decale les echeances')
        self.avance(1.0); self.assertEqual(len(s.attente_bgm), 1); self.avance(0.6); self.assertEqual(len(s.attente_bgm), 0)

    def test_chargement_d_un_etat_vide_la_file(self):
        s = self.s; self.lancer_jingle(); self.ordre(SON.BGM_ARRET, 300, dt=0.2); self.assertEqual(len(s.attente_bgm), 1)
        s.restaurer_bgm({'id': 2, 'pos': 0.0, 'reprise': None}); self.assertEqual(len(s.attente_bgm), 0); self.assertEqual(s.bgm_id, 2)


if __name__ == '__main__':
    unittest.main(verbosity=2)
