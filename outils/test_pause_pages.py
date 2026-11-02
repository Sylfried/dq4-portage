"""Test (sans fenetre) des pages du menu Pause : racine, Son (une ligne par son : nom, volume, muet, par defaut), Vitesse de defilement du texte, Commandes (vitesses x1 a x4).

    python3 outils/test_pause_pages.py

Le menu est pilote avec un faux « jeu » (reglages reels, son et fenetre simules) : les memes fonctions que celles du menu, clavier compris (Pause.touche).
"""
import os, sys, tempfile, types, unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'dq4_pc'))
import pyglet
pyglet.options['shadow_window'] = False                     # (pas d'affichage necessaire : on ne dessine rien)
import reglages as RG
import pause as PA

K = pyglet.window.key
LIBELLES_SON = ['Général', 'Musique', 'Jingles et fanfares', 'Bruitages', 'Interface']
CLES_SON = {'Musique': ('musique_active', 'volume_musique'), 'Jingles et fanfares': ('jingles_actifs', 'volume_jingles'), 'Bruitages': ('bruitages_actifs', 'volume_bruitages'),
            'Interface': ('interface_active', 'volume_interface'), 'Général': ('son', 'volume_general')}


class FauxSon:
    actif = True; ecoute = False


class FauxJeu:
    """Ce que le menu Pause demande a la fenetre."""
    def __init__(self):
        self.reg = RG.Reglages(os.path.join(tempfile.mkdtemp(prefix='pause_test_'), 'reglages.json'))
        self.son = FauxSon(); self.args = types.SimpleNamespace(cache='/inexistant'); self.width, self.height = 1280, 720; self.souris = None
        self.appels = []; self.fondu = None; self.code_defilement = 2
    def regler_son(self, oui): self.son.actif = bool(oui)
    def appliquer_mixage(self): self.appels.append('mixage')
    def apercu_son(self, cat): self.appels.append(('apercu', cat))
    def regler_fondu(self, v): self.fondu = v
    def appliquer_texte(self): self.appels.append('texte')
    def defilement_actuel(self): return self.reg['defilement_combat'] if self.reg['defilement_force'] else RG.cran_defilement(self.code_defilement)
    def regler_defilement(self, code): self.reg['defilement_combat'] = RG.cran_defilement(code); self.reg['defilement_force'] = True
    def retablir_defilement(self): self.reg['defilement_force'] = False
    def pause_jeu(self, oui): pass


def menu(ecran):
    J = FauxJeu(); p = PA.Pause(J); p.ouvert = True; p.pile = [ecran]
    return J, p


def par_libelle(p, lib):
    return next(e for e in p._entrees() if e['l'] == lib)


class Racine(unittest.TestCase):
    def test_entree_renommee(self):
        _, p = menu('racine'); libs = [e['l'] for e in p._entrees()]
        self.assertIn('Vitesse de défilement du texte', libs); self.assertNotIn('Texte et défilement', libs)
        self.assertEqual(libs, ['Reprendre', 'États', 'Affichage', 'Son', 'Vitesse de défilement du texte', 'Commandes', "Revenir à l'écran titre"])


class PageSon(unittest.TestCase):
    def test_une_ligne_par_son(self):
        _, p = menu('son'); e = p._entrees()
        self.assertEqual([x['l'] for x in e], LIBELLES_SON)
        self.assertNotIn('sep', [x['t'] for x in e], 'plus de sections')
        for x in e:                                                                    # chaque ligne : une barre de volume (curseur), un bouton muet, un bouton « par defaut »
            self.assertEqual(x['t'], 'curs'); self.assertTrue(all(k in x for k in ('fixe', 'actif', 'ok', 'defaut', 'est_defaut')), x['l'])

    def test_muet_coupe_et_remet_le_bon_interrupteur(self):
        J, p = menu('son')
        for lib in LIBELLES_SON:
            cle_actif, cle_vol = CLES_SON[lib]; x = par_libelle(p, lib)
            lire = (lambda: J.son.actif) if lib == 'Général' else (lambda c=cle_actif: J.reg[c])
            self.assertTrue(lire() and x['actif']())
            x['ok'](); self.assertFalse(lire(), lib); self.assertFalse(par_libelle(p, lib)['actif']())
            if lib == 'Général': self.assertIs(J.reg['son'], False)
            others = [l for l in LIBELLES_SON if l != lib]
            self.assertTrue(all(par_libelle(p, o)['actif']() for o in others), 'une ligne ne coupe que son propre son')
            self.assertEqual(J.reg[cle_vol], 1.0, 'couper ne change pas le volume')
            x['ok'](); self.assertTrue(lire(), lib)

    def test_par_defaut_remet_volume_et_son(self):
        J, p = menu('son')
        for lib in LIBELLES_SON:
            cle_actif, cle_vol = CLES_SON[lib]; x = par_libelle(p, lib)
            self.assertTrue(x['est_defaut']())
            x['fixe'](0.3); x['ok']()
            self.assertFalse(x['est_defaut']()); self.assertAlmostEqual(J.reg[cle_vol], 0.3, 2)
            x['defaut'](); self.assertAlmostEqual(J.reg[cle_vol], RG.DEFAUT[cle_vol], 3); self.assertTrue(x['actif']()); self.assertTrue(x['est_defaut']())
            x['fixe'](0.3); self.assertFalse(x['est_defaut'](), 'un volume different suffit')
            x['defaut']()
        J2, p2 = menu('son'); x = par_libelle(p2, 'Musique'); x['ok'](); self.assertFalse(x['est_defaut'](), 'coupe : pas par defaut'); x['defaut'](); self.assertTrue(J2.reg['musique_active'])

    def test_clavier(self):
        J, p = menu('son')
        p.touche(K.DOWN); self.assertEqual(p.sel['son'], 1)                            # Musique
        p.touche(K.LEFT); self.assertAlmostEqual(J.reg['volume_musique'], 0.95, 2)
        p.touche(K.LEFT); p.touche(K.RIGHT); self.assertAlmostEqual(J.reg['volume_musique'], 0.95, 2)
        p.touche(K.RETURN); self.assertFalse(J.reg['musique_active'])                  # Entree : muet
        self.assertIsNone(p.saisie, 'Entree ne lance pas la saisie du volume sur cette page')
        p.touche(K.RETURN); self.assertTrue(J.reg['musique_active'])
        p.touche(K.SPACE); self.assertFalse(J.reg['musique_active']); p.touche(K.SPACE)
        p.touche(K.DELETE); self.assertAlmostEqual(J.reg['volume_musique'], 1.0, 3)    # Suppr : par defaut
        p.touche(K.LEFT); p.touche(K.LEFT); p.touche(K.RETURN); p.touche(K.HOME)       # Debut : aussi
        self.assertAlmostEqual(J.reg['volume_musique'], 1.0, 3); self.assertTrue(J.reg['musique_active'])
        p.touche(K.UP); p.touche(K.UP); self.assertEqual(p.sel['son'], 4)              # bouclage : en haut de la liste on arrive en bas
        p.touche(K.DOWN); self.assertEqual(p.sel['son'], 0)

    def test_clic_valeur_permet_de_taper(self):
        J, p = menu('son'); x = par_libelle(p, 'Bruitages')
        x['saisie'](40); self.assertAlmostEqual(J.reg['volume_bruitages'], 0.4, 3)

    def test_volume_fait_entendre_un_essai_et_le_retour_du_son_aussi(self):
        J, p = menu('son'); x = par_libelle(p, 'Bruitages')
        J.appels.clear(); x['moins'](); self.assertIn(('apercu', 'effets'), J.appels)
        x['ok'](); J.appels.clear(); x['ok'](); self.assertIn(('apercu', 'effets'), J.appels, 'le son revient : on l\'entend'); self.assertIn('mixage', J.appels)


class PageTexte(unittest.TestCase):
    def test_lignes(self):
        _, p = menu('texte'); e = p._entrees()
        self.assertEqual([x['l'] for x in e][:2], ['Vitesse du texte', 'Messages en combat'])
        self.assertNotIn('sep', [x['t'] for x in e], 'plus de sections')
        self.assertNotIn('Défilement automatique', [x['l'] for x in e]); self.assertNotIn('Vitesse de défilement', [x['l'] for x in e])

    def test_noms(self):
        _, p = menu('texte')
        vt = par_libelle(p, 'Vitesse du texte')
        self.assertEqual([p._nom_valeur('Vitesse du texte', v) for v in vt['vals']], ['Très lent', 'Lent', 'Assez lent', 'Normal', 'Rapide', 'Très rapide', 'Instantané'])
        cb = par_libelle(p, 'Messages en combat')
        self.assertEqual([p._nom_valeur('Messages en combat', v) for v in cb['vals']], ['Rapide', 'Moyen', 'Lent', 'Manuel'])
        self.assertEqual(cb['vals'], [0, 2, 3, 4])                                     # OptionStatus.battleSpeed : attente de 12 / 32 / 42 images, 4 = a la main

    def test_choix_impose_la_valeur_puis_rien_tant_qu_on_ne_touche_pas(self):
        J, p = menu('texte'); J.code_defilement = 3
        cb = par_libelle(p, 'Messages en combat')
        self.assertEqual(cb['get'](), 3); self.assertIs(J.reg['defilement_force'], False)       # affiche la valeur de la sauvegarde sans rien imposer
        J.code_defilement = 1; self.assertEqual(par_libelle(p, 'Messages en combat')['get'](), 2)   # cran 1 (22 images) : affiche comme Moyen
        self.assertIs(J.reg['defilement_force'], False)
        p.sel['texte'] = 1; p.touche(K.RIGHT)                                          # Moyen -> Lent
        self.assertEqual((J.reg['defilement_combat'], J.reg['defilement_force']), (3, True))
        p.touche(K.RIGHT); self.assertEqual(J.reg['defilement_combat'], 4)             # Lent -> Manuel
        p.touche(K.RIGHT); self.assertEqual(J.reg['defilement_combat'], 0)             # (la liste boucle) Manuel -> Rapide
        par_libelle(p, 'Rétablir le réglage du jeu')['ok'](); self.assertIs(J.reg['defilement_force'], False)


class PageCommandes(unittest.TestCase):
    LIBS = ('Vitesse de marche', 'Vitesse de caméra', 'Vitesse de transition')

    def test_vitesses_en_options(self):
        J, p = menu('commandes')
        for lib in self.LIBS:
            x = par_libelle(p, lib); self.assertEqual(x['t'], 'choix'); self.assertEqual(x['vals'], [1.0, 2.0, 3.0, 4.0])
            self.assertEqual([p._nom_valeur(lib, v) for v in x['vals']], ['x1', 'x2', 'x3', 'x4'])
        x = par_libelle(p, "Multiplicateur de l'accélérateur"); self.assertEqual(x['t'], 'curs'); self.assertAlmostEqual(x['v'] and J.reg['vitesse_accel'], 1.5)    # l'accelerateur garde son curseur
        self.assertNotIn("Vitesse de l'accélérateur", [e.get('l') for e in p._entrees()])                                                                                       # (ancien libelle : renomme)

    def test_vitesse_des_combats(self):
        """Ligne « Vitesse des combats » : juste sous les lignes de l'accelerateur (touche, multiplicateur), meme forme que les choix x1 a x4, libelles Normal / Rapide / Tres rapide, defaut Normal ; sa touche suit."""
        J, p = menu('commandes'); e = p._entrees(); ls = [x['l'] for x in e]
        i = ls.index("Multiplicateur de l'accélérateur"); self.assertEqual(ls[i - 1], "Touche d'accélérateur")
        self.assertEqual(ls[i + 1], 'Vitesse des combats'); self.assertEqual(ls[i + 2], 'Touche de vitesse des combats'); self.assertEqual(e[i + 3]['t'], 'sep')       # (puis la section suivante)
        x = par_libelle(p, 'Vitesse des combats'); self.assertEqual(x['t'], 'choix'); self.assertTrue(x['liste']); self.assertEqual(x['vals'], [1.0, 2.0, 3.0])
        self.assertEqual([p._nom_valeur('Vitesse des combats', v) for v in x['vals']], ['Normal', 'Rapide', 'Très rapide'])
        self.assertEqual(x['v'](), 'Normal'); self.assertEqual(J.reg['vitesse_combat'], 1.0)
        x['plus'](); self.assertEqual((J.reg['vitesse_combat'], x['v']()), (2.0, 'Rapide'))
        x['plus'](); self.assertEqual((J.reg['vitesse_combat'], x['v']()), (3.0, 'Très rapide'))
        x['plus'](); self.assertEqual((J.reg['vitesse_combat'], x['v']()), (1.0, 'Normal'))                  # la liste boucle
        x['moins'](); self.assertEqual(J.reg['vitesse_combat'], 3.0)
        self.assertTrue(x.get('aide')); self.assertNotIn('x2', x['aide'])
        t = par_libelle(p, 'Touche de vitesse des combats'); self.assertEqual((t['t'], t['act']), ('touche', 'vit_combat')); self.assertEqual(t['v'], ['V', '—'])

    def test_changement_de_valeur(self):
        J, p = menu('commandes')
        for lib, cle in zip(self.LIBS, RG.VITESSES_X_CLES):
            x = par_libelle(p, lib)
            for v in (4.0, 3.0, 2.0, 1.0): x['set'](v); self.assertEqual(J.reg[cle], v); self.assertEqual(x['v'](), 'x%d' % v)
        x = par_libelle(p, 'Vitesse de transition'); x['set'](3.0); self.assertEqual(J.fondu, 3.0)               # le moteur est prevenu

    def test_aides(self):
        _, p = menu('commandes')
        for lib in self.LIBS: self.assertTrue(par_libelle(p, lib).get('aide'), lib)


class Survol(unittest.TestCase):
    """Plus d'encadre jaune : sous le pointeur (mode souris), une zone s'assombrit ; au clavier, rien n'est survole."""
    def test_pointeur(self):
        _, p = menu('racine'); z = (10, 10, 50, 30)
        p.mode_souris = False; p.pos_souris = (20, 20); self.assertFalse(p._pointeur_dans(z)); self.assertFalse(p._sur(z))
        p.mode_souris = True; self.assertTrue(p._pointeur_dans(z)); self.assertTrue(p._sur(z))
        p.pos_souris = (60, 20); self.assertFalse(p._sur(z))                                # le pointeur sort : la zone se rallume
        p.pos_souris = (20, 20); p.popup = {'titre': 'x', 'sel': 1}; self.assertFalse(p._sur(z)); self.assertTrue(p._pointeur_dans(z))        # sous une fenetre modale : le survol lui appartient
        self.assertFalse(p._pointeur_dans(None))
        p.popup = None; p.pos_souris = (20, 20); self.assertTrue(p._sur(z)); p.sortie(); self.assertFalse(p._sur(z), 'le pointeur a quitte la fenetre : plus rien n\'est survole')

    def test_plus_de_cadre_jaune_dans_le_code_de_la_page(self):
        with open(PA.__file__, encoding='utf-8') as f: src = f.read()
        self.assertNotIn('JAUNE if sel', src); self.assertNotIn(', JAUNE)', src.replace('color=JAUNE)', ''))


if __name__ == '__main__':
    unittest.main(verbosity=2)
