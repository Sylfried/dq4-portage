"""Test des remises a zero de l'editeur d'interface (menu Echap > Affichage > Interface) : « Retablir cette interface » et « Retablir toutes les interfaces ».

    python3 outils/test_reglages_interface.py

Verifie : (1) que toute cle de reglage est classee (interface ou non) : une cle ajoutee a DEFAUT sans classement fait echouer le test ;
(2) « Retablir cette interface » ne remet que l'interface choisie (boutons et croix de l'ecran, ou une fenetre du jeu / les dialogues) ;
(3) « Retablir toutes les interfaces » remet toutes les interfaces et les options de l'editeur a DEFAUT, sans toucher aux autres reglages (son, affichage, touches...) ;
(4) les memes actions, appelees par la page Interface (Pause), changent aussi l'etat de session de l'editeur (place du panneau).
"""
import copy, os, sys, tempfile, types, unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'dq4_pc'))
import reglages as RG

# cles de DEFAUT qui ne touchent PAS l'editeur d'interface (affichage, son, texte, touches, camera, vitesses...) ; « infos » = lignes d'information F1, « taille_degats » = valeur fixe (plus un reglage)
HORS_INTERFACE = {'mode_sprites', 'distance_camera', 'camera_centree', 'lissage', 'plein_ecran', 'msaa', 'echelle_rendu', 'nettete', 'luminosite', 'infos', 'son', 'volume_musique', 'volume_bruitages',
                  'volume_general', 'volume_jingles', 'volume_interface', 'musique_active', 'jingles_actifs', 'bruitages_actifs', 'interface_active', 'vitesse_texte', 'defilement_force',
                  'defilement_combat', 'resolution', 'angle_camera', 'vignette', 'vitesse_marche', 'vitesse_camera', 'vitesse_fondu', 'vitesse_accel', 'taille_degats',
                  'touches_v', 'touches'}

# valeurs differentes de DEFAUT pour chaque reglage d'interface
AUTRES = {'boutons': False, 'croix': False, 'croix_taille': 1.7, 'boutons_taille': 1.4, 'boutons_pos': {'carte': [10, 5], 'menu': [3, 2.5], 'discussion': [0, 9], 'croix': [20, 9]},
          'grille_edition': False, 'boutons_aimant': False,
          'interface_fenetres': {'RootMenu': [1.3, 0.1, -0.2], 'Status': [0.7, -0.05, 0.3], 'msg': [1.5, 0.0, 0.1], 'YesNo': [0.8, 0.2, 0.0]},
          'interface_masquees': ['RootMenu', 'Status', 'msg', 'MapButton']}


def reglages_modifies():
    """Reglages de test : toutes les cles d'interface et quelques autres a des valeurs non par defaut."""
    r = RG.Reglages(None)
    for k, x in AUTRES.items(): r[k] = copy.deepcopy(x)
    r['vignette'] = 0.8; r['msaa'] = 8; r['volume_musique'] = 0.2; r['distance_camera'] = 150; r['touches']['carte'] = ['K', None]; r['camera_centree'] = False
    return r


def interface(r):
    return {k: copy.deepcopy(r[k]) for k in RG.CLES_INTERFACE}


def autres(r):
    return {k: copy.deepcopy(r[k]) for k in HORS_INTERFACE}


class RemiseAZero(unittest.TestCase):
    def test_classement_complet(self):
        classees = set(RG.CLES_INTERFACE) | HORS_INTERFACE
        self.assertEqual(set(RG.DEFAUT) - classees, set(), "cle de reglage non classee (interface ou non) : l'ajouter a reglages.CLES_* ou a HORS_INTERFACE de ce test")
        self.assertEqual(classees - set(RG.DEFAUT), set(), 'cle classee mais absente de DEFAUT')
        self.assertEqual(set(RG.CLES_INTERFACE) & HORS_INTERFACE, set())
        self.assertEqual(len(RG.CLES_INTERFACE), len(set(RG.CLES_INTERFACE)))
        self.assertEqual(set(RG.CLES_ECRAN + RG.CLES_FENETRES + RG.CLES_EDITEUR), set(RG.CLES_INTERFACE))

    def test_valeurs_de_test_non_par_defaut(self):
        self.assertEqual(set(AUTRES), set(RG.CLES_INTERFACE))
        for k, x in AUTRES.items(): self.assertNotEqual(x, RG.DEFAUT[k], k)

    def test_ecran_seul(self):
        r = reglages_modifies(); av = interface(r); ap = autres(r)
        r.remettre_interface(RG.CIBLE_ECRAN)
        for k in RG.CLES_ECRAN: self.assertEqual(r[k], RG.DEFAUT[k], k)               # boutons et croix : tout revient (affichage, tailles, positions)
        for k in RG.CLES_FENETRES + RG.CLES_EDITEUR: self.assertEqual(r[k], av[k], k)           # fenetres et options de l'editeur : intactes
        self.assertEqual(autres(r), ap)

    def test_fenetre_seule(self):
        r = reglages_modifies(); av = interface(r); ap = autres(r)
        r.remettre_interface('RootMenu')
        self.assertNotIn('RootMenu', r['interface_fenetres']); self.assertNotIn('RootMenu', r['interface_masquees'])          # taille, position et affichage d'origine
        self.assertEqual(r['interface_fenetres'], {k: x for k, x in av['interface_fenetres'].items() if k != 'RootMenu'})      # les autres fenetres gardent leur reglage
        self.assertEqual(r['interface_masquees'], [n for n in av['interface_masquees'] if n != 'RootMenu'])                   # ... et leur masquage
        for k in RG.CLES_ECRAN + RG.CLES_EDITEUR: self.assertEqual(r[k], av[k], k)
        self.assertEqual(autres(r), ap)

    def test_dialogues_et_oui_non_independants(self):
        r = reglages_modifies()
        r.remettre_interface('msg')
        self.assertNotIn('msg', r['interface_fenetres']); self.assertNotIn('msg', r['interface_masquees'])
        self.assertIn('YesNo', r['interface_fenetres'])                                           # Oui / Non est une interface a part
        r.remettre_interface('YesNo')
        self.assertNotIn('YesNo', r['interface_fenetres'])

    def test_fenetre_sans_reglage(self):
        r = reglages_modifies(); av = interface(r)
        r.remettre_interface('Money')                                                              # rien a remettre : rien ne change, pas d'erreur
        self.assertEqual(interface(r), av)

    def test_fenetre_masquee_seulement(self):
        r = RG.Reglages(None); r['interface_masquees'] = ['Status']; r.remettre_interface('Status')
        self.assertEqual(r['interface_masquees'], [])

    def test_tout(self):
        r = reglages_modifies(); ap = autres(r)
        r.remettre_interfaces()
        for k in RG.CLES_INTERFACE: self.assertEqual(r[k], RG.DEFAUT[k], k)                       # interfaces et options de l'editeur (grille, aimantation) : tout est revenu
        self.assertEqual(autres(r), ap)                                                           # les autres reglages ne bougent pas

    def test_pas_de_partage_avec_defaut(self):
        r = RG.Reglages(None); r.remettre_interfaces()
        r['interface_fenetres']['X'] = [2.0, 0.0, 0.0]; r['interface_masquees'].append('X'); r['boutons_pos']['carte'] = [1, 1]
        self.assertEqual((RG.DEFAUT['interface_fenetres'], RG.DEFAUT['interface_masquees'], RG.DEFAUT['boutons_pos']), ({}, [], {}))       # DEFAUT n'est jamais modifie par une remise a zero
        r2 = RG.Reglages(None); r2.remettre_interface('X'); r2.remettre_interface(RG.CIBLE_ECRAN)
        self.assertEqual((RG.DEFAUT['interface_fenetres'], RG.DEFAUT['interface_masquees'], RG.DEFAUT['boutons_pos']), ({}, [], {}))

    def test_enregistrement(self):
        f = os.path.join(tempfile.mkdtemp(prefix='rg_test_'), 'reglages.json')
        r = RG.Reglages(f)
        for k, x in AUTRES.items(): r[k] = copy.deepcopy(x)
        r.remettre_interface('Status'); r.remettre_interface(RG.CIBLE_ECRAN); r.enregistrer()
        r2 = RG.Reglages(f)
        self.assertEqual(r2['boutons'], True); self.assertEqual(r2['boutons_pos'], {}); self.assertNotIn('Status', r2['interface_fenetres']); self.assertIn('RootMenu', r2['interface_fenetres'])
        r2.remettre_interfaces(); r2.enregistrer()
        for k in RG.CLES_INTERFACE: self.assertEqual(RG.Reglages(f)[k], RG.DEFAUT[k], k)

    def test_elements_masques_de_l_apercu(self):
        """Apercu de l'editeur : chaque element masque (toute l'interface, ou la croix seule) est marque, les autres non ; la croix reste selectionnable (son rectangle est toujours donne)."""
        try:
            import pause as PA
            import hud_mobile as HM
        except Exception as ex:
            self.skipTest('pause.py non importable ici (%r)' % (ex,))
        r = RG.Reglages(None)
        hud = types.SimpleNamespace(rect=lambda n: (10.0 * len(n), 20.0, 60.0, 50.0))
        P = PA.Pause(types.SimpleNamespace(reg=r, hud=hud)); P.cible = RG.CIBLE_ECRAN
        masque = lambda: {n: (e[4], e[5]) for n, e in zip(HM.NOMS_ED, P._elements_apercu())}
        self.assertEqual(masque(), {'carte': (False, True), 'menu': (False, True), 'discussion': (False, True), 'croix': (False, False)})      # tout affiche : rien de marque
        r['croix'] = False                                                                       # « Afficher la croix » = Non : la croix seule est marquee (feminin), les boutons non
        self.assertEqual(masque(), {'carte': (False, True), 'menu': (False, True), 'discussion': (False, True), 'croix': (True, False)})
        r['boutons'] = False; r['croix'] = True                                                  # interface entiere masquee : boutons (masculin) et croix (feminin)
        self.assertEqual(masque(), {'carte': (True, True), 'menu': (True, True), 'discussion': (True, True), 'croix': (True, False)})
        self.assertEqual(len(P._rects_montres()), 4)                                              # (le panneau de l'editeur et la selection ne dependent pas de l'affichage)
        r['boutons'] = True; P.cible = 'RootMenu'; P.rect_apercu = (5.0, 6.0, 7.0, 8.0)
        self.assertEqual(P._elements_apercu(), [(5.0, 6.0, 7.0, 8.0, False, False)])
        r['interface_masquees'] = ['RootMenu']
        self.assertEqual(P._elements_apercu(), [(5.0, 6.0, 7.0, 8.0, True, False)])              # fenetre masquee : marquee (feminin) ; seule celle-la
        P.cible = 'Status'; self.assertEqual(P._elements_apercu(), [(5.0, 6.0, 7.0, 8.0, False, False)])
        P.cible = 'msg'; P.rect_apercu = None; self.assertEqual(P._elements_apercu(), [])

    def test_page_interface(self):
        """Les entrees « Retablir » de la page Interface appellent ces remises a zero (jeu factice : `reg` et la liste des fenetres) ; la place du panneau (session) est remise a l'origine par « toutes »."""
        try:
            import pause as PA
        except Exception as ex:
            self.skipTest('pause.py non importable ici (%r)' % (ex,))
        r = reglages_modifies(); P = PA.Pause(types.SimpleNamespace(reg=r, noms_fenetres=lambda: {'RootMenu': [1], 'Status': [2], 'Money': [3]}))
        P.cible = 'RootMenu'; P.pan_pos = (500.0, 400.0)
        ent = {x['l']: x for x in P._e_interface() if x['t'] == 'act'}
        self.assertEqual(list(ent)[-3:], ['Rétablir cette interface', 'Rétablir toutes les interfaces', 'Terminer'])
        ent['Rétablir cette interface']['ok']()
        self.assertNotIn('RootMenu', r['interface_fenetres']); self.assertIn('Status', r['interface_fenetres']); self.assertEqual(r['croix_taille'], AUTRES['croix_taille'])
        self.assertEqual(P.pan_pos, (500.0, 400.0))                                               # la place du panneau est une option globale de l'editeur
        P.cible = RG.CIBLE_ECRAN
        ent = {x['l']: x for x in P._e_interface() if x['t'] == 'act'}
        ent['Rétablir cette interface']['ok']()
        self.assertEqual([r[k] for k in RG.CLES_ECRAN], [RG.DEFAUT[k] for k in RG.CLES_ECRAN]); self.assertIn('Status', r['interface_fenetres'])
        ent['Rétablir toutes les interfaces']['ok']()
        for k in RG.CLES_INTERFACE: self.assertEqual(r[k], RG.DEFAUT[k], k)
        self.assertIsNone(P.pan_pos)


if __name__ == '__main__':
    unittest.main(verbosity=2)
