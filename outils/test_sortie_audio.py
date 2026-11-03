"""Test (sans son ni fenetre) du choix du peripherique de sortie audio (#112, D-207) : sortie_audio.py avec de faux pilotes, le reglage `sortie_audio` de reglages.json et la ligne « Périphérique de sortie »
de la page Son du menu Echap.

    python3 outils/test_sortie_audio.py

Pas de vrai pilote XAudio2 ici (Linux) : le changement de sortie reel n'a jamais ete essaye ; la liste et le changement de pyglet 2.1 sont lus dans son code (voir l'en-tete de sortie_audio.py).
"""
import os, sys, tempfile, types, unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'dq4_pc'))
import pyglet
pyglet.options['shadow_window'] = False
pyglet.options['audio'] = ('silent',)
import reglages as RG
import sortie_audio as SA


class FauxPeriph:
    def __init__(self, ident, nom): self.id = ident; self.name = nom


class FauxPilote:
    def __init__(self, erreur=None): self.appels = []; self.erreur = erreur
    def set_device(self, d):
        if self.erreur: raise self.erreur
        self.appels.append(d.id)


class FauxGestionnaire:
    def __init__(self, periph): self.periph = list(periph); self.lectures = 0
    def get_output_devices(self): self.lectures += 1; return list(self.periph)


HP, CASQUE, TV = FauxPeriph('{0.0.0.00000000}.{aaa}', 'Haut-parleurs (Realtek)'), FauxPeriph('{0.0.0.00000000}.{bbb}', 'Casque (USB)'), FauxPeriph('{0.0.0.00000000}.{ccc}', 'TV (HDMI)')


def sorties(periph=(HP, CASQUE), erreur=None):
    t = [0.0]
    s = SA.Sorties(FauxPilote(erreur), FauxGestionnaire(periph), horloge=lambda: t[0]); s.t = t
    return s


class Choix(unittest.TestCase):
    def test_choix_valide(self):
        self.assertIsNone(SA.choix_valide(None))
        self.assertEqual(SA.choix_valide({'id': 'a', 'nom': 'B', 'autre': 1}), {'id': 'a', 'nom': 'B'})
        for mauvais in ('x', 3, [], {}, {'id': '', 'nom': 'B'}, {'id': 'a'}, {'id': 3, 'nom': 'B'}, {'id': 'a', 'nom': None}): self.assertIsNone(SA.choix_valide(mauvais), repr(mauvais))

    def test_reglage_enregistre_et_relu(self):
        chemin = os.path.join(tempfile.mkdtemp(prefix='sortie_test_'), 'reglages.json')
        R = RG.Reglages(chemin); self.assertIsNone(R['sortie_audio'], 'Automatique par defaut')
        R['sortie_audio'] = {'id': HP.id, 'nom': HP.name}; R.enregistrer()
        self.assertEqual(RG.Reglages(chemin)['sortie_audio'], {'id': HP.id, 'nom': HP.name})
        R['sortie_audio'] = 'n importe quoi'; R.enregistrer(); self.assertIsNone(RG.Reglages(chemin)['sortie_audio'], 'un reglage illisible redevient Automatique')


class Liste(unittest.TestCase):
    def test_liste_et_noms(self):
        s = sorties(); self.assertTrue(s.disponible())
        self.assertEqual(s.lister(), [(HP.id, HP.name), (CASQUE.id, CASQUE.name)])
        self.assertEqual(s.valeurs(None), [SA.AUTO, HP.id, CASQUE.id])
        self.assertEqual(s.nom(SA.AUTO, None), 'Automatique'); self.assertEqual(s.nom(CASQUE.id, None), CASQUE.name)
        self.assertEqual(s.valeur(None), SA.AUTO); self.assertEqual(s.valeur({'id': CASQUE.id, 'nom': CASQUE.name}), CASQUE.id)

    def test_liste_gardee_un_instant(self):
        s = sorties(); s.lister(); s.lister(); self.assertEqual(s._g().lectures, 1)
        s.t[0] = SA.DELAI_LISTE + 0.1; s.lister(); self.assertEqual(s._g().lectures, 2, 'relue apres le delai')
        s.lister(True); self.assertEqual(s._g().lectures, 3, 'relue de force')

    def test_sortie_enregistree_non_branchee(self):
        s = sorties(); choix = {'id': TV.id, 'nom': TV.name}
        self.assertEqual(s.valeurs(choix), [SA.AUTO, HP.id, CASQUE.id, TV.id], 'gardee a la fin')
        self.assertEqual(s.nom(TV.id, choix), TV.name + SA.ABSENT_SUFFIXE)
        self.assertTrue(s.modifiable(choix))

    def test_sans_pilote_ou_sans_sortie(self):
        s = SA.Sorties()                                                         # (pilote de pyglet : « silent », sans set_device)
        self.assertFalse(s.disponible()); self.assertEqual(s.lister(), []); self.assertFalse(s.modifiable(None)); self.assertEqual(s.valeurs(None), [SA.AUTO])
        self.assertFalse(sorties(periph=()).modifiable(None), 'aucune sortie detectee : ligne inactive')

    def test_erreur_du_gestionnaire(self):
        s = sorties(); s._gest_force.get_output_devices = lambda: (_ for _ in ()).throw(OSError('COM'))
        self.assertEqual(s.lister(), [])


class Changement(unittest.TestCase):
    def test_choisir_une_sortie_puis_automatique(self):
        s = sorties(); p = s._p()
        self.assertEqual(s.appliquer(SA.AUTO), (True, None)); self.assertEqual(p.appels, [], 'deja Automatique : rien a faire')
        self.assertEqual(s.appliquer(CASQUE.id), (True, {'id': CASQUE.id, 'nom': CASQUE.name})); self.assertEqual(p.appels, [CASQUE.id])
        self.assertEqual(s.appliquer(CASQUE.id)[0], True); self.assertEqual(p.appels, [CASQUE.id], 'meme sortie : pas de second changement')
        self.assertEqual(s.appliquer(SA.AUTO), (True, None)); self.assertEqual(p.appels, [CASQUE.id, None], 'retour a la sortie par defaut (id None)')

    def test_sortie_disparue(self):
        s = sorties(); s.lister()
        s._gest_force.periph = [HP]
        self.assertEqual(s.appliquer(CASQUE.id), (False, None)); self.assertEqual(s._p().appels, [])

    def test_erreur_du_pilote(self):
        s = sorties(erreur=OSError('XAudio2'))
        self.assertEqual(s.appliquer(HP.id), (False, None)); self.assertEqual(s.en_service, SA.AUTO, 'la sortie en service ne change pas')

    def test_au_lancement(self):
        s = sorties(); self.assertFalse(s.appliquer_enregistree(None)); self.assertEqual(s._p().appels, [])
        self.assertTrue(s.appliquer_enregistree({'id': CASQUE.id, 'nom': CASQUE.name})); self.assertEqual(s._p().appels, [CASQUE.id])
        s2 = sorties(); self.assertFalse(s2.appliquer_enregistree({'id': TV.id, 'nom': TV.name})); self.assertEqual(s2._p().appels, [], 'non branchee : la sortie par defaut de Windows reste')
        self.assertFalse(SA.Sorties().appliquer_enregistree({'id': HP.id, 'nom': HP.name}), 'sans pilote capable : rien')


if __name__ == '__main__':
    unittest.main(verbosity=1)
