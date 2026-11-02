"""Test (sans fenetre) des pages du menu Pause : racine, Son (une ligne par son : nom, volume, muet, par defaut), Commandes (vitesses x1 a x4, section « Defilement du texte »), Triches (ex-« Jeu »).

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
    def noms_fenetres(self): return {'BattleRoot': [1], 'BattleAction': [2], 'RootMenu': [3], 'Status': [4]}
    def __init__(self):
        self.reg = RG.Reglages(os.path.join(tempfile.mkdtemp(prefix='pause_test_'), 'reglages.json'))
        self.son = FauxSon(); self.args = types.SimpleNamespace(cache='/inexistant'); self.width, self.height = 1280, 720; self.souris = None
        self.appels = []; self.fondu = None
    def regler_son(self, oui): self.son.actif = bool(oui)
    def appliquer_mixage(self): self.appels.append('mixage')
    def apercu_son(self, cat): self.appels.append(('apercu', cat))
    def regler_fondu(self, v): self.fondu = v
    def appliquer_texte(self): self.appels.append('texte')
    def appliquer_jeu(self): self.appels.append('jeu')
    def regler_vitesse_combat(self, v): self.reg['vitesse_combat'] = RG.cran_combat(v); self.appels.append(('combat', RG.code_defilement(v)))
    def pause_jeu(self, oui): pass


def menu(ecran):
    J = FauxJeu(); p = PA.Pause(J); p.ouvert = True; p.pile = [ecran]
    return J, p


def par_libelle(p, lib):
    return next(e for e in p._entrees() if e['l'] == lib)


class Intertitres(unittest.TestCase):
    """Liste deroulante « Interface à modifier » : les intertitres de groupe (« Écran tactile », « Dialogues »...) sont discrets, jamais en or (l'or est celui de la valeur courante)."""
    def test_intertitres_ni_or_ni_aussi_grands_que_les_valeurs(self):
        t, c = PA.style_intertitre(20.0)
        self.assertLess(t, 20.0 * 0.9); self.assertNotEqual(c, PA.OR); self.assertNotEqual(c[:3], PA.BLANC[:3])               # plus petit, ni or ni blanc
        lum = lambda x: 0.3 * x[0] + 0.59 * x[1] + 0.11 * x[2]
        self.assertLess(lum(c), lum(PA.BLANC) * 0.7); self.assertLess(c[2], c[0])                                              # terne (moins lumineux que le blanc) mais encore un gris dore (pas un gris neutre)
        self.assertLess(c[0] - c[2], 60); self.assertLess(lum(c), lum(PA.OR) - 40)                                             # (et nettement moins vif que l'or de la valeur courante)
        self.assertEqual(PA.OR, (255, 235, 4, 255))                                                                            # l'or reste celui de la valeur courante

    def test_le_code_de_la_liste_utilise_le_style_des_intertitres(self):
        src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'dq4_pc', 'pause.py'), encoding='utf-8').read()
        i = src.index('if self._entete(vals[j]):'); bloc = src[i:i + 700]
        self.assertIn('style_intertitre(fs)', bloc); self.assertNotIn(', OR)', bloc)                                           # l'intertitre n'est plus dessine en or


class Racine(unittest.TestCase):
    def test_entrees(self):
        _, p = menu('racine'); libs = [e['l'] for e in p._entrees()]
        for ancien in ('Vitesse de défilement du texte', 'Texte et défilement'): self.assertNotIn(ancien, libs)             # plus de page du texte : ses deux options sont dans Commandes
        self.assertEqual(libs, ['Reprendre', 'Historique', 'États', 'Affichage', 'Son', 'Commandes', 'Triches', "Revenir à l'écran titre"])
        self.assertNotIn('Jeu', libs); self.assertEqual(libs.index('Triches'), libs.index('Commandes') + 1)                # « Triches » (ex-« Jeu ») : juste sous « Commandes »
        self.assertFalse(hasattr(p, '_e_texte'))


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


class SectionDefilement(unittest.TestCase):
    """Commandes > « Défilement du texte » : « Vitesse du texte » et « Vitesse de combat » (ex-page « Vitesse de défilement du texte » du menu racine), nouvelle section juste sous « Vitesses »."""

    @staticmethod
    def lignes(p): return p._entrees()

    def test_section_sous_les_vitesses(self):
        _, p = menu('commandes'); e = self.lignes(p); ls = [(x['t'], x['l']) for x in e]
        i = ls.index(('sep', 'Défilement du texte'))
        self.assertEqual(ls[i + 1:i + 3], [('choix', 'Vitesse du texte'), ('choix', 'Vitesse de combat')]); self.assertEqual(e[i + 3]['t'], 'sep')          # deux options, puis la section suivante
        self.assertEqual(ls[i + 3], ('sep', 'Actions du jeu'))
        k = ls.index(('sep', 'Vitesses')); self.assertLess(k, i)
        self.assertEqual([t for t, _ in ls[k + 1:i]].count('sep'), 0, 'aucune section entre « Vitesses » et « Défilement du texte » : elle est juste dessous')
        self.assertEqual(ls[i - 1], ('touche', 'Changer la vitesse en combat'))                                                                          # (derniere ligne des vitesses)
        self.assertEqual([l for t, l in ls if t == 'sep'], ['Déplacement', 'Caméra', 'Caméra à la souris', 'Molette', 'Ctrl + molette', 'Clic molette + déplacement', 'Clic molette', 'Ctrl + clic molette', 'Vitesses', 'Défilement du texte', 'Actions du jeu', 'Autres'])

    def test_plus_de_page_texte(self):
        _, p = menu('racine'); self.assertNotIn('texte', [e['l'] for e in p._entrees()])
        with open(PA.__file__, encoding='utf-8') as f: src = f.read()
        self.assertNotIn("_aller('texte')", src); self.assertNotIn("titres['texte']", src)

    def test_noms(self):
        _, p = menu('commandes')
        vt = par_libelle(p, 'Vitesse du texte')
        self.assertEqual([p._nom_valeur('Vitesse du texte', v) for v in vt['vals']], ['Très lent', 'Lent', 'Assez lent', 'Normal', 'Rapide', 'Très rapide', 'Instantané'])
        cb = par_libelle(p, 'Vitesse de combat')
        self.assertEqual([p._nom_valeur('Vitesse de combat', v) for v in cb['vals']], ['Manuel', 'Normal', 'Rapide', 'Très rapide'])
        self.assertEqual(cb['vals'], [0.0, 1.0, 2.0, 3.0])

    def test_vitesse_du_texte(self):
        J, p = menu('commandes'); vt = par_libelle(p, 'Vitesse du texte')
        self.assertEqual((vt['get'](), vt['v']()), (4.0, 'Normal')); self.assertTrue(vt['est_defaut']())
        vt['set'](16.0); self.assertEqual(J.reg['vitesse_texte'], 16.0); self.assertEqual(J.appels[-1], 'texte'); self.assertFalse(vt['est_defaut']())        # la fenetre est prevenue
        vt['defaut'](); self.assertEqual(J.reg['vitesse_texte'], 4.0); self.assertEqual(J.appels[-1], 'texte'); self.assertTrue(vt['est_defaut']())
        self.assertTrue(vt.get('aide'))

    def test_choix_change_la_vitesse_et_le_defilement(self):
        """« Vitesse de combat » : le menu previent la fenetre (qui impose aussi le defilement : 4 en Manuel, 2 sinon) ; la liste boucle ; ↺ remet Normal (au clavier : la ligne est choisie dans la page Commandes)."""
        J, p = menu('commandes'); cb = par_libelle(p, 'Vitesse de combat')
        self.assertEqual((cb['get'](), cb['v']()), (1.0, 'Normal')); self.assertTrue(cb['est_defaut']())
        p.sel['commandes'] = [x['l'] for x in p._entrees()].index('Vitesse de combat'); p.touche(K.RIGHT); self.assertEqual(J.reg['vitesse_combat'], 2.0)
        p.touche(K.RIGHT); self.assertEqual(J.reg['vitesse_combat'], 3.0)
        p.touche(K.RIGHT); self.assertEqual(J.reg['vitesse_combat'], 0.0)                                       # (la liste boucle) Très rapide -> Manuel
        self.assertEqual(J.appels[-1], ('combat', 4)); self.assertFalse(cb['est_defaut']())
        cb['defaut'](); self.assertEqual(J.reg['vitesse_combat'], 1.0); self.assertEqual(J.appels[-1], ('combat', 0)); self.assertTrue(cb['est_defaut']())      # ↺ : Normal
        self.assertTrue(cb.get('aide')); self.assertNotIn('x2', cb['aide'])

    def test_pas_d_ancien_reglage(self):
        _, p = menu('commandes'); ls = [x.get('l') for x in p._entrees()]
        for ancien in ('Défilement automatique', 'Vitesse de défilement', 'Messages en combat', 'Rétablir le réglage du jeu'): self.assertNotIn(ancien, ls)


class PageTriches(unittest.TestCase):
    LIB = 'PV et PM restaurés au niveau supérieur'

    def test_option_desactivee_par_defaut_avec_retablissement(self):
        """Page « Triches » (ex-« Jeu ») : un interrupteur Oui / Non, Non par defaut (comme le jeu), qui previent la fenetre ; ↺ le remet sur Non."""
        J, p = menu('triches'); x = par_libelle(p, self.LIB)
        self.assertEqual(x['vals'], [True, False]); self.assertFalse(J.reg['soin_niveau']); self.assertTrue(x['est_defaut']())
        x['set'](True); self.assertTrue(J.reg['soin_niveau']); self.assertEqual(J.appels[-1], 'jeu'); self.assertFalse(x['est_defaut']())
        x['defaut'](); self.assertFalse(J.reg['soin_niveau']); self.assertEqual(J.appels[-1], 'jeu'); self.assertTrue(x['est_defaut']())
        self.assertTrue(x.get('aide'))

    def test_une_ligne_et_entree_de_la_racine(self):
        J, p = menu('triches'); self.assertEqual([e['l'] for e in p._entrees()], [self.LIB])
        p.pile = ['racine']; e = next(e for e in p._entrees() if e['l'] == 'Triches'); e['ok'](); self.assertEqual(p.ecran, 'triches')
        self.assertFalse(hasattr(p, '_e_jeu')); self.assertNotIn('Jeu', [e['l'] for e in p._entrees()])
        with open(PA.__file__, encoding='utf-8') as f: src = f.read()
        self.assertIn("titres['triches'] = 'Triches'", src); self.assertNotIn("_aller('jeu')", src)                                          # titre de la page : « Triches »

    def test_reglage_enregistre(self):
        J = FauxJeu(); J.reg['soin_niveau'] = True; J.reg.enregistrer()
        self.assertTrue(RG.Reglages(J.reg.chemin)['soin_niveau'])
        J.reg.v['soin_niveau'] = 'oui'; J.reg.enregistrer(); self.assertFalse(RG.Reglages(J.reg.chemin)['soin_niveau'])        # valeur invalide : retour au defaut (Non)


class PageCommandes(unittest.TestCase):
    LIBS = ('Vitesse de marche', 'Vitesse de caméra', 'Vitesse de transition')

    def test_vitesses_en_options(self):
        J, p = menu('commandes')
        for lib in self.LIBS:
            x = par_libelle(p, lib); self.assertEqual(x['t'], 'choix'); self.assertEqual(x['vals'], [1.0, 2.0, 3.0, 4.0])
            self.assertEqual([p._nom_valeur(lib, v) for v in x['vals']], ['x1', 'x2', 'x3', 'x4'])
        x = par_libelle(p, "Multiplicateur de l'accélérateur"); self.assertEqual(x['t'], 'curs'); self.assertAlmostEqual(x['v'] and J.reg['vitesse_accel'], 1.5)    # l'accelerateur garde son curseur
        self.assertNotIn("Vitesse de l'accélérateur", [e.get('l') for e in p._entrees()])                                                                                       # (ancien libelle : renomme)

    def test_touche_de_vitesse_de_combat(self):
        """Commandes > Vitesses : pas de reglage de vitesse de combat (il est dans la section « Défilement du texte », juste dessous), seulement la touche « Changer la vitesse en combat », juste sous le multiplicateur de l'accelerateur."""
        J, p = menu('commandes'); e = p._entrees(); ls = [x['l'] for x in e]
        i = ls.index("Multiplicateur de l'accélérateur"); self.assertEqual(ls[i - 1], "Touche d'accélérateur")
        self.assertEqual(ls[i + 1], 'Changer la vitesse en combat'); self.assertEqual(e[i + 2]['t'], 'sep'); self.assertEqual(ls[i + 2], 'Défilement du texte')      # (puis la section suivante)
        self.assertEqual(ls.count('Vitesse de combat'), 1)                                                         # (un seul reglage : dans la section Défilement du texte, pas dans Vitesses)
        for ancien in ('Vitesse des combats', 'Touche de vitesse des combats'): self.assertNotIn(ancien, ls)
        t = par_libelle(p, 'Changer la vitesse en combat'); self.assertEqual((t['t'], t['act']), ('touche', 'vit_combat')); self.assertEqual(t['v'], ['V', '—'])
        self.assertIn('Manuel', t['aide']); self.assertNotIn('x2', t['aide'])

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


class ListeInterface(unittest.TestCase):
    """Liste « Interface à modifier » : bouton de vitesse de combat dans son propre element du groupe « Combat », avec ses propres reglages."""
    def test_groupes(self):
        J, p = menu('interface'); v = p.cibles()
        ecran = v[v.index('#Écran tactile') + 1:v.index('#Dialogues')]; self.assertEqual(ecran, ['boutons'])                  # « Boutons et croix de l'écran » reste seul dans son groupe
        i = v.index('#Combat'); self.assertEqual(v[i + 1], 'bouton_vitesse')                                                   # le bouton de vitesse : premier element du groupe « Combat »
        self.assertEqual(v[i + 1:i + 4], ['bouton_vitesse', 'BattleRoot', 'BattleAction'])
        self.assertEqual(p.nom_cible('bouton_vitesse'), 'Combat : bouton de vitesse'); self.assertEqual(p.nom_cible('boutons'), "Boutons et croix de l'écran")
        self.assertEqual(sum(1 for x in v if x == 'bouton_vitesse'), 1)

    def test_page_du_bouton_de_vitesse(self):
        J, p = menu('interface'); p.cible = RG.CIBLE_VITESSE; libs = [e['l'] for e in p._entrees()]
        self.assertIn('Taille du bouton', libs); self.assertIn('Replacer sous la boîte de combat', libs); self.assertIn("Afficher cette interface à l'écran", libs)
        for autre in ('Taille des boutons', 'Afficher la croix', 'Taille de la croix', 'Position horizontale'): self.assertNotIn(autre, libs)
        p.cible = RG.CIBLE_ECRAN; libs = [e['l'] for e in p._entrees()]
        self.assertIn('Taille des boutons', libs); self.assertIn('Afficher la croix', libs); self.assertNotIn('Taille du bouton', libs)

    def test_reglages_propres_au_bouton(self):
        J, p = menu('interface'); R = J.reg; p.cible = RG.CIBLE_VITESSE
        p._poser_visible(RG.CIBLE_VITESSE, False); self.assertEqual((R['bouton_vitesse'], R['boutons']), (False, True)); self.assertFalse(p._visible(RG.CIBLE_VITESSE)); self.assertTrue(p._visible(RG.CIBLE_ECRAN))
        p._poser_visible(RG.CIBLE_ECRAN, False); p._poser_visible(RG.CIBLE_VITESSE, True); self.assertEqual((R['bouton_vitesse'], R['boutons']), (True, False))
        e = par_libelle(p, 'Taille du bouton'); e['plus'](); e['plus'](); self.assertAlmostEqual(R['bouton_vitesse_taille'], 1.2); self.assertEqual(R['boutons_taille'], 1.0); e['defaut'](); self.assertEqual(R['bouton_vitesse_taille'], 1.0)
        R['bouton_vitesse_pos'] = [3.0, 4.0]; par_libelle(p, 'Replacer sous la boîte de combat')['ok'](); self.assertEqual(R['bouton_vitesse_pos'], [])
        R['bouton_vitesse_pos'] = [3.0, 4.0]; R['boutons_pos'] = {'carte': [1, 1]}; par_libelle(p, 'Rétablir cette interface')['ok']()
        self.assertEqual((R['bouton_vitesse_pos'], R['bouton_vitesse_taille'], R['bouton_vitesse'], R['boutons_pos']), ([], 1.0, True, {'carte': [1, 1]}))      # la remise ne touche que le bouton

    def test_editeur_montre_le_bon_element(self):
        import hud_mobile as HM
        self.assertEqual(HM.noms_ed(RG.CIBLE_ECRAN), ('carte', 'menu', 'discussion', HM.CROIX)); self.assertEqual(HM.noms_ed(RG.CIBLE_VITESSE), (HM.COMBAT,)); self.assertEqual(HM.noms_ed('msg'), ())
        self.assertNotIn(HM.COMBAT, HM.noms_ed(RG.CIBLE_ECRAN))                                                               # plus dans « Boutons et croix de l'écran »


if __name__ == '__main__':
    unittest.main(verbosity=2)
