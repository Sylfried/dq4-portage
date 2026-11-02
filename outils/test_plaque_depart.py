"""Test de la logique pure de la plaque « Sauvegarde automatique » du menu de depart (type 53), sans fenetre ni moteur :

  1. etats d'un bouton (MenuParts.BUTTON_STATE_*) : normal et enfonce reagissent, invisible / grise / inverse ne reagissent pas (IButton : le test de contact est coupe) ;
  2. disponibilite de la sauvegarde auto : le code 0 du moteur (1 = data5.dat valide, 0 = absent) l'emporte ; sans code, l'etiquette envoyee par le moteur tranche ;
  3. `Fenetre.plaque_auto` : plaque TOUJOURS visible avec son etiquette ; sans sauvegarde auto elle est grisee (etat 3) et sort des zones tactiles (`boutons` : ni clic, ni survol, ni validation au clavier) ;
     des que la sauvegarde auto existe : etat normal, etiquette du moteur, zone tactile ; les autres plaques (Continuer...) ne sont pas touchees ; l'ancien comportement (plaque cachee) reste disponible (DQ_AUTO_CACHEE).

    python3 outils/test_plaque_depart.py        (Linux sans ecran : pyglet en mode « headless »)
"""
import os, sys, types, unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'dq4_pc'))
import pyglet
if sys.platform.startswith('linux') and not os.environ.get('DISPLAY'): pyglet.options['headless'] = True; pyglet.options['shadow_window'] = False
import ui_menu as UM


def type_depart():
    """Mise en page minimale du menu de depart : deux plaques (Continuer = bouton 0, Sauvegarde automatique = bouton 4), chacune avec son etiquette."""
    carre = {'vtx': [[-100.0, 10.0], [100.0, 10.0], [100.0, -10.0], [-100.0, -10.0]], 'uv': [[0, 0], [1, 0], [1, 1], [0, 1]], 'sub': {'0': [0, 1, 2, 0, 2, 3]}}
    def plaque(nid, bouton, z): return {'id': nid, 'par': 1, 'pos': [0.0, 4.0, z], 'act': True, 'mats': [{'sheet': 1, 'part': 7, 'color': [1, 1, 1, 1], 'shader': 'parts', 'offset': None}], 'mesh': carre, 'parts': {'buttonId': bouton, 'gamepad': 16}}
    def texte(nid, par): return {'id': nid, 'par': par, 'pos': [0.0, 8.0, -8.0], 'act': True, 'text': {'font': 'font', 'characterSize': 10.0, 'text': None}, 'mats': []}
    return {'name': 'Make_StartMenuSecond()', 'err': None,
            'nodes': [{'id': 1, 'par': None, 'pos': [0.0, 0.0, 0.0], 'act': True, 'mats': []}, plaque(10, 4, 60.0), texte(11, 10), plaque(20, 0, 0.0), texte(21, 20)],
            'parts': [{'node': 10, 'ib': [{'k': 'button'}, {'k': 'text', 'go': 11, 'variant': 0}]}, {'node': 20, 'ib': [{'k': 'button'}, {'k': 'text', 'go': 21, 'variant': 0}]}],
            'params': [{'id': 4, 'no': 0, 'parts': 0, 'base': 0}, {'id': 4, 'no': 1, 'parts': 0, 'base': 1}, {'id': 0, 'no': 0, 'parts': 1, 'base': 0}, {'id': 0, 'no': 1, 'parts': 1, 'base': 1}],
            'codes': [], 'builds': []}


def fenetre():
    ml = types.SimpleNamespace(types={'53': type_depart()}, infos=[], cadres=[], hdr={'lang': {'hiro': 1.0}}, pousse=(0.0, 0.0))
    return UM.Fenetre(ml, 53)


def texte(fe, nid): return fe.N[nid]['text']['text']
def zones(fe): return sorted(b[0] for b in fe.boutons())


class TestEtats(unittest.TestCase):
    def test_etat_actif(self):
        self.assertTrue(UM.etat_actif(UM.ETAT_NORMAL)); self.assertTrue(UM.etat_actif(UM.ETAT_ENFONCE))
        for e in (UM.ETAT_INVISIBLE, UM.ETAT_GRISE, UM.ETAT_INVERSE): self.assertFalse(UM.etat_actif(e), e)
        self.assertEqual((UM.ETAT_NORMAL, UM.ETAT_ENFONCE, UM.ETAT_INVISIBLE, UM.ETAT_GRISE, UM.ETAT_INVERSE), (0, 1, 2, 3, 4))      # MenuParts.BUTTON_STATE_*

    def test_disponibilite(self):
        self.assertTrue(UM.plaque_auto_disponible(1, '')); self.assertFalse(UM.plaque_auto_disponible(0, 'Sauvegarde automatique'))      # le code 0 l'emporte
        self.assertTrue(UM.plaque_auto_disponible(None, 'Sauvegarde automatique')); self.assertFalse(UM.plaque_auto_disponible(None, '')); self.assertFalse(UM.plaque_auto_disponible(None, '  ')); self.assertFalse(UM.plaque_auto_disponible(None, None))


class TestPlaqueAuto(unittest.TestCase):
    def setUp(self): os.environ.pop('DQ_AUTO_CACHEE', None)

    def test_sans_sauvegarde_auto_grisee_et_inactive(self):
        fe = fenetre(); fe.code(0, 0)                                                                   # le moteur : pas de data5.dat, pas d'etiquette (4, 1)
        for _ in range(3): fe.plaque_auto()                                                              # idempotent : appelee a chaque image
        pl = fe.N[10]
        self.assertTrue(pl['act']); self.assertEqual(texte(fe, 11), UM.LIBELLE_AUTO)                      # visible, avec son etiquette
        self.assertEqual(pl['etat'], UM.ETAT_GRISE)                                                      # grisee
        self.assertNotIn(4, zones(fe)); self.assertIn(0, zones(fe))                                       # inactive : plus de zone tactile ; Continuer, lui, reste actif

    def test_avec_sauvegarde_auto_normale(self):
        fe = fenetre(); fe.param_str(4, 1, 'Sauvegarde automatique'); fe.code(0, 1); fe.plaque_auto()
        self.assertEqual(fe.N[10]['etat'], UM.ETAT_NORMAL); self.assertTrue(fe.N[10]['act']); self.assertIn(4, zones(fe))

    def test_etiquette_du_moteur_conservee(self):
        fe = fenetre(); fe.param_str(4, 1, 'Reprendre le dernier point'); fe.code(0, 1); fe.plaque_auto()
        self.assertEqual(texte(fe, 11), 'Reprendre le dernier point')                                  # on ne remplace jamais l'etiquette envoyee par le moteur

    def test_la_sauvegarde_apparait_ensuite(self):
        fe = fenetre(); fe.code(0, 0); fe.plaque_auto(); self.assertEqual(fe.N[10]['etat'], UM.ETAT_GRISE)
        fe.param_str(4, 1, 'Sauvegarde automatique (nouvelle)'); fe.code(0, 1); fe.plaque_auto()           # data5.dat apparait : le moteur renvoie code et etiquette
        self.assertEqual(fe.N[10]['etat'], UM.ETAT_NORMAL); self.assertIn(4, zones(fe)); self.assertEqual(texte(fe, 11), 'Sauvegarde automatique (nouvelle)'); self.assertFalse(fe.auto_grise)

    def test_puis_disparait(self):
        fe = fenetre(); fe.param_str(4, 1, 'Sauvegarde automatique'); fe.code(0, 1); fe.plaque_auto(); fe.code(0, 0); fe.plaque_auto()
        self.assertEqual(fe.N[10]['etat'], UM.ETAT_GRISE); self.assertNotIn(4, zones(fe)); self.assertTrue(texte(fe, 11))

    def test_sans_code_l_etiquette_tranche(self):
        fe = fenetre(); fe.plaque_auto(); fe.plaque_auto()                                                # ni code ni etiquette : grisee (et notre etiquette de remplacement ne la « valide » pas a l'image suivante)
        self.assertEqual(fe.N[10]['etat'], UM.ETAT_GRISE); self.assertNotIn(4, zones(fe))
        fe.param_str(4, 1, 'Reprise automatique'); fe.plaque_auto()                                       # etiquette du moteur (differente de la notre) sans code : disponible
        self.assertEqual(fe.N[10]['etat'], UM.ETAT_NORMAL); self.assertIn(4, zones(fe))

    def test_autres_plaques_intactes(self):
        fe = fenetre(); fe.param_str(0, 1, 'Continuer votre aventure'); fe.param_int(0, 0, UM.ETAT_GRISE); fe.code(0, 0); fe.plaque_auto()
        self.assertEqual(fe.N[20]['etat'], UM.ETAT_GRISE); self.assertEqual(texte(fe, 21), 'Continuer votre aventure'); self.assertNotIn(0, zones(fe))      # une plaque grisee par le moteur (aucune banque) : meme regle

    def test_etat_envoye_par_le_moteur(self):
        fe = fenetre(); fe.param_int(0, 0, UM.ETAT_NORMAL); self.assertIn(0, zones(fe))
        for etat, attendu in ((UM.ETAT_ENFONCE, True), (UM.ETAT_INVISIBLE, False), (UM.ETAT_GRISE, False), (UM.ETAT_INVERSE, False), (UM.ETAT_NORMAL, True)):
            fe.param_int(0, 0, etat); self.assertEqual(0 in zones(fe), attendu, etat)

    def test_comportement_d_origine_sur_demande(self):
        os.environ['DQ_AUTO_CACHEE'] = '1'
        try:
            fe = fenetre(); fe.code(0, 0); fe.plaque_auto()
            self.assertFalse(fe.N[10]['act']); self.assertNotIn(4, zones(fe))                              # le jeu d'origine cache la plaque
        finally: os.environ.pop('DQ_AUTO_CACHEE', None)


if __name__ == '__main__':
    unittest.main()
