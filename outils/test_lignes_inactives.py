"""Test des lignes inactives du menu Pause (page Affichage : « Résolution » en plein écran, « Écran du plein écran » avec un seul écran ; page États : emplacements vides) et du libellé « Modifications ».

    python3 outils/test_lignes_inactives.py

Une ligne qui ne peut pas être modifiée dans l'état courant (`off`) est grisée en entier (libellé, valeur, flèche, bouton ↺, case), jamais choisie (le curseur doré et le clavier la sautent), jamais survolée (aucun
surlignage), jamais cliquée ni validée ; plus aucun texte rouge de note sous les valeurs. Le test couvre tous les types de lignes de toutes les pages : il marque chaque ligne, une à une, comme inactive (PauseMarquee)
et vérifie qu'aucune action ne l'atteint (clavier, clic, survol, molette, glisser, saisie, liste déroulante). Le menu est piloté avec un faux « jeu » ; le dessin se fait dans une fenêtre pyglet cachée (EGL sans écran) :
le survol est vérifié sur les pixels (la ligne inactive ne change pas quand le pointeur la survole, une ligne active si).
"""
import copy, os, sys, types, unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'dq4_pc'))
import pyglet
if sys.platform.startswith('linux') and not os.environ.get('DISPLAY'): pyglet.options['headless'] = True; pyglet.options['shadow_window'] = False
import numpy as np
import reglages as RG
import pause as PA
import sortie_audio as SA

K = pyglet.window.key
GAUCHE = 1
PAGES = ('racine', 'affichage', 'son', 'commandes', 'modifications', 'etats', 'quitter', 'interface')
PAGES_DESSINEES = tuple(p for p in PAGES if p != 'interface')          # (la page Interface dessine l'apercu du jeu : le faux jeu n'en a pas)
CACHE = os.environ.get('DQ_UICACHE', '/inexistant')                    # (facultatif : cache d'interface du jeu pour la police et les icones ; sans lui, polices du systeme et plaque de repli)


class FauxJeu:
    """Ce que le menu Pause demande à la fenêtre ; `plein` et `ecrans` peuvent changer à tout moment (les lignes se recalculent à chaque image)."""
    mode = 4; zoom = 1.0

    def __init__(self, plein=False, ecrans=1):
        self.reg = RG.Reglages(None); self.plein = plein; self.ecrans = ecrans; self.res = (1280, 720); self.appels = []; self.etiq = {}
        self.width, self.height = 1280, 720; self.args = types.SimpleNamespace(cache=CACHE); self.souris = None
        self.post = types.SimpleNamespace(max_msaa=None); self.son = types.SimpleNamespace(actif=True, ecoute=False, ecouter=lambda b: None, tick=lambda: None)
        self.sorties = SA.Sorties(types.SimpleNamespace(set_device=lambda d: self.appels.append(('sortie', d.id))), types.SimpleNamespace(get_output_devices=lambda: [types.SimpleNamespace(id='a', name='Haut-parleurs'), types.SimpleNamespace(id='b', name='Casque')]))

    est_plein = property(lambda self: self.plein)
    def regler_plein_ecran(self, v): self.plein = bool(v); self.appels.append(('plein', bool(v)))
    def resolutions(self): return [(1280, 720), (1920, 1080), (2560, 1440)]
    def resolution_courante(self): return self.res
    def regler_resolution(self, v): self.res = tuple(v); self.appels.append(('res', tuple(v)))
    def valeurs_ecran(self): return ['auto'] + list(range(self.ecrans))
    def valeur_ecran(self): return 'auto'
    def nom_ecran(self, v): return 'Automatique (écran de la fenêtre)' if v == 'auto' else 'Écran %d' % (v + 1)
    def ecran_modifiable(self): return self.ecrans > 1
    def regler_ecran_plein(self, v): self.appels.append(('ecran', v))
    def regler_mode(self, v): self.appels.append(('mode', v))
    def regler_distance(self, v): self.appels.append(('distance', v))
    def valeurs_sortie(self): return self.sorties.valeurs(self.reg['sortie_audio'])
    def valeur_sortie(self): return self.sorties.valeur(self.reg['sortie_audio'])
    def nom_sortie(self, v): return self.sorties.nom(v, self.reg['sortie_audio'])
    def sortie_modifiable(self): return self.sorties.modifiable(self.reg['sortie_audio'])
    def regler_sortie(self, v):
        ok, choix = self.sorties.appliquer(v)
        if ok: self.reg['sortie_audio'] = choix
    def regler_son(self, oui): self.appels.append(('son', oui))
    def appliquer_mixage(self): self.appels.append('mixage')
    def apercu_son(self, cat): self.appels.append(('apercu', cat))
    def regler_fondu(self, v): self.appels.append(('fondu', v))
    def appliquer_texte(self): self.appels.append('texte')
    def appliquer_jeu(self): self.appels.append('jeu')
    def regler_vitesse_combat(self, v): self.appels.append(('combat', v))
    def noms_fenetres(self): return {}
    def infos_etat(self, n): return None
    def pause_jeu(self, oui): pass
    def quitter(self): self.appels.append('quitter')
    def retour_titre(self): self.appels.append('titre')

    def _etiq(self, texte, taille, couleur=(255, 255, 255, 255), polices=()):
        k = (texte, round(taille, 1), couleur, polices)
        if k not in self.etiq: self.etiq[k] = pyglet.text.Label(texte, font_size=taille, color=couleur, anchor_x='left', anchor_y='baseline')
        return self.etiq[k]


class PauseMarquee(PA.Pause):
    """Menu Pause dont certaines lignes (libellés de `inactives`, sur toutes les pages) sont marquées inactives : permet d'éprouver chaque type de ligne."""
    inactives = ()

    def _entrees(self):
        e = super()._entrees()
        for x in e:
            if x['t'] != 'sep' and x.get('l') in self.inactives: x['off'] = True
        return e


def menu(page, plein=False, ecrans=1, classe=PA.Pause, **attrs):
    J = FauxJeu(plein, ecrans); p = classe(J); p.ouvert = True; p.pile = [page]
    for k, v in attrs.items(): setattr(p, k, v)
    return J, p


def etat(J, p):
    """Tout ce qu'une action sur une ligne pourrait changer."""
    return repr((copy.deepcopy(J.reg.v), list(J.appels), list(p.pile), p.capture, p.saisie, p.deroule, p.popup, p.glisse, J.plein, J.res, p.action_etat))


def libelles(e): return [x.get('l') for x in e]


_fen = []
def fenetre():
    """Fenêtre pyglet cachée (une seule pour tout le test) ; None si le contexte graphique manque ici."""
    if not _fen:
        try:
            import pyglet.window
            _fen.append(pyglet.window.Window(width=1280, height=720, visible=False))
        except Exception as ex: _fen.append(ex)
    if isinstance(_fen[0], Exception): raise unittest.SkipTest('pas de contexte graphique ici (%r)' % (_fen[0],))
    return _fen[0]


def rendre(p):
    """Dessine le menu puis rend l'image (tableau RGBA, origine en bas à gauche)."""
    w = fenetre(); w.switch_to(); w.clear(); p.dessiner()
    im = pyglet.image.get_buffer_manager().get_color_buffer().get_image_data()
    return np.frombuffer(im.get_data('RGBA', im.width * 4), np.uint8).reshape(im.height, im.width, 4).copy()


def rogner(img, z, marge=2): return img[int(z[1]) + marge:int(z[3]) - marge, int(z[0]) + marge:int(z[2]) - marge]


def zone_de(p, idx):
    """Zone (x0, y0, x1, y1) de la ligne idx à la dernière image : (zone, active ?)."""
    for z in p.zones:
        if z[4] == idx: return z[:4], True
    for z in p.zones_off:
        if z[4] == idx: return z[:4], False
    return None, None


class PageAffichage(unittest.TestCase):
    """Les deux cas de la capture de Sylfried : « Écran du plein écran » (un seul écran) et « Résolution » (plein écran)."""
    def lignes(self, plein, ecrans):
        J, p = menu('affichage', plein, ecrans); e = p._entrees(); return J, p, e, {x['l']: i for i, x in enumerate(e)}

    def test_etats_des_lignes(self):
        for plein in (False, True):
            for ecrans in (1, 2):
                J, p, e, n = self.lignes(plein, ecrans)
                self.assertEqual(p._inactif(e[n['Résolution']]), plein, (plein, ecrans)); self.assertEqual(p._inactif(e[n['Écran du plein écran']]), ecrans == 1, (plein, ecrans))
                self.assertFalse(p._inactif(e[n['Plein écran']])); self.assertFalse(p._inactif(e[n['Netteté']])); self.assertFalse(p._inactif(e[n['Interface']]))

    def test_plus_aucun_texte_rouge_de_note(self):
        for plein in (False, True):
            J, p, e, n = self.lignes(plein, 1)
            for x in e: self.assertNotIn('note', x, x.get('l'))
        with open(PA.__file__, encoding='utf-8') as f: src = f.read()
        self.assertNotIn("en['note']", src); self.assertNotIn('note=', src); self.assertNotIn('dec = ', src)                    # (plus de paramètre `note`, plus de place réservée sous la valeur ; restent en rouge : le message d'erreur du pied du cadre et « Masquée » de l'éditeur, qui ne sont pas des notes sous les valeurs)
        for texte in ('Un seul écran détecté', 'Sans effet en plein écran'): self.assertNotIn("'%s" % texte, src)

    def test_navigation_saute_les_lignes_inactives(self):
        J, p, e, n = self.lignes(False, 1); p.sel['affichage'] = n['Plein écran']                  # fenêtre, un seul écran : « Écran du plein écran » est sautée
        p.touche(K.DOWN); self.assertEqual(p.sel['affichage'], n['Résolution'])
        p.touche(K.UP); self.assertEqual(p.sel['affichage'], n['Plein écran'])
        J, p, e, n = self.lignes(True, 1); p.sel['affichage'] = n['Plein écran']                    # plein écran, un seul écran : les deux le sont
        p.touche(K.DOWN); self.assertEqual(p.sel['affichage'], n['Netteté'])
        p.touche(K.UP); self.assertEqual(p.sel['affichage'], n['Plein écran'])
        p.touche(K.UP); self.assertEqual(p.sel['affichage'], n['Interface'])                        # (le tour de la liste reprend par la fin)
        p.touche(K.DOWN); self.assertEqual(p.sel['affichage'], n['Plein écran'])
        J, p, e, n = self.lignes(False, 2); p.sel['affichage'] = n['Plein écran']                  # deux écrans : rien n'est sauté
        p.touche(K.DOWN); self.assertEqual(p.sel['affichage'], n['Écran du plein écran']); p.touche(K.DOWN); self.assertEqual(p.sel['affichage'], n['Résolution'])

    def test_molette_saute_les_lignes_inactives(self):
        J, p, e, n = self.lignes(True, 1); p.sel['affichage'] = n['Plein écran']
        p.molette(1); self.assertEqual(p.sel['affichage'], n['Netteté'])                            # (molette vers le haut = ligne suivante)

    def test_clavier_sans_effet_sur_une_ligne_inactive(self):
        for plein, ecrans, lib in ((True, 2, 'Résolution'), (False, 1, 'Écran du plein écran'), (True, 1, 'Résolution'), (True, 1, 'Écran du plein écran')):
            J, p, e, n = self.lignes(plein, ecrans); p.sel['affichage'] = n[lib]; avant = etat(J, p)
            for t in (K.RETURN, K.SPACE, K.LEFT, K.RIGHT, K.DELETE, K.HOME): p.touche(t); p.sel['affichage'] = n[lib]
            self.assertEqual(etat(J, p), avant, (plein, ecrans, lib)); self.assertIsNone(p._courante())

    def test_ligne_active_toujours_reglable(self):
        J, p, e, n = self.lignes(False, 1); p.sel['affichage'] = n['Résolution']; p.touche(K.RIGHT)          # fenêtre : la résolution se règle
        self.assertEqual(J.appels, [('res', (1920, 1080))])
        J, p, e, n = self.lignes(False, 2); p.sel['affichage'] = n['Écran du plein écran']; p.touche(K.RIGHT)
        self.assertEqual(J.appels, [('ecran', 0)])

    def test_etat_recalcule_a_chaque_image(self):
        """Une ligne grisée parce qu'une autre valeur la rend sans effet redevient active dès que cette valeur change (et inversement)."""
        J, p = menu('affichage', False, 2); n = {x['l']: i for i, x in enumerate(p._entrees())}
        self.assertFalse(p._inactif(p._entrees()[n['Résolution']]))
        p.sel['affichage'] = n['Plein écran']; p.touche(K.RETURN)                                          # Entrée sur l'interrupteur : plein écran
        self.assertTrue(J.plein); self.assertTrue(p._inactif(p._entrees()[n['Résolution']]))              # ... « Résolution » est grisée tout de suite
        p.touche(K.RETURN); self.assertFalse(J.plein); self.assertFalse(p._inactif(p._entrees()[n['Résolution']]))      # ... et se rallume au retour en fenêtre
        J.ecrans = 1; self.assertTrue(p._inactif(p._entrees()[n['Écran du plein écran']]))               # un écran débranché : la ligne se grise
        J.ecrans = 2; self.assertFalse(p._inactif(p._entrees()[n['Écran du plein écran']]))              # ... et se rallume au branchement

    def test_la_selection_quitte_la_ligne_devenue_inactive(self):
        J, p = menu('affichage', False, 2); n = {x['l']: i for i, x in enumerate(p._entrees())}; fenetre()
        p.sel['affichage'] = n['Résolution']; rendre(p); self.assertEqual(p.sel['affichage'], n['Résolution'])
        J.plein = True; rendre(p); self.assertEqual(p.sel['affichage'], n['Netteté'])                      # F11 pendant que « Résolution » est choisie : le curseur passe à la ligne active suivante
        J.plein = False; J.ecrans = 1; p.sel['affichage'] = n['Écran du plein écran']; rendre(p); self.assertEqual(p.sel['affichage'], n['Résolution'])

    def test_clic_survol_et_infobulle(self):
        J, p = menu('affichage', True, 1); n = {x['l']: i for i, x in enumerate(p._entrees())}; fenetre(); rendre(p)
        for lib in ('Résolution', 'Écran du plein écran'):
            z, actif = zone_de(p, n[lib]); self.assertFalse(actif, lib)
            for f in (0.05, 0.3, 0.5, 0.7, 0.95):                                                          # (libellé, valeur, flèche, bouton ↺ : n'importe où dans la case)
                x, y = z[0] + f * (z[2] - z[0]), (z[1] + z[3]) / 2; avant = etat(J, p); sel = p.sel['affichage']
                p.survol(x, y); self.assertTrue(p.mode_souris); self.assertEqual(p.sel['affichage'], sel, 'survol')
                p.clic(x, y, GAUCHE); self.assertEqual(etat(J, p), avant, 'clic'); self.assertEqual(p.sel['affichage'], sel)
                p.relache(x, y, GAUCHE)
            self.assertTrue(p._aide_ligne(p._entrees()[n[lib]]), lib)                                      # (elle garde son aide : elle dit pourquoi)
        self.assertNotIn('Entrée', p._aide_ligne(p._entrees()[n['Résolution']]))                           # (mais plus de consigne « Entrée ou clic : ouvrir la liste »)
        self.assertIn('Grisé quand un seul écran', p._aide_ligne(p._entrees()[n['Écran du plein écran']]))
        z, actif = zone_de(p, n['Netteté']); self.assertTrue(actif)                                      # une ligne active, elle, répond
        p.survol((z[0] + z[2]) / 2, (z[1] + z[3]) / 2); self.assertEqual(p.sel['affichage'], n['Netteté'])

    def test_pixels_aucun_surlignage_au_survol(self):
        """La ligne inactive est identique avec ou sans pointeur dessus ; une ligne active change (contrôle du test)."""
        J, p = menu('affichage', True, 1); n = {x['l']: i for i, x in enumerate(p._entrees())}; fenetre(); loin = (5.0, 5.0)
        p.mode_souris = True; p.pos_souris = loin; rendre(p); fond = rendre(p)
        for lib, change in (('Résolution', False), ('Écran du plein écran', False), ('Netteté', True), ('Luminosité', True)):
            z, actif = zone_de(p, n[lib]); self.assertEqual(actif, change, lib)
            p.pos_souris = ((z[0] + z[2]) / 2, (z[1] + z[3]) / 2); p.tt = None; dessus = rendre(p); p.pos_souris = loin; p.tt = None
            egal = np.array_equal(rogner(fond, z), rogner(dessus, z))
            self.assertEqual(egal, not change, '%s : %s' % (lib, 'identique' if egal else 'différente'))
        p.pos_souris = loin

    def test_case_entiere_grisee(self):
        """La plaque d'une ligne inactive est plus sombre que celle d'une ligne active, et son texte est gris (pas blanc)."""
        J, p = menu('affichage', True, 1); n = {x['l']: i for i, x in enumerate(p._entrees())}; fenetre(); p.mode_souris = False; img = rendre(p)
        zr, _ = zone_de(p, n['Résolution']); zn, _ = zone_de(p, n['Netteté'])
        def lum(z): c = rogner(img, z, 6).astype(float); return c[..., :3].mean(), c[..., :3].max()
        (m_r, max_r), (m_n, max_n) = lum(zr), lum(zn)
        self.assertLess(m_r, m_n); self.assertLess(max_r, 200); self.assertGreater(max_n, 240)             # (grisée : pas de blanc franc ; active : texte blanc)


class TousLesTypes(unittest.TestCase):
    """Chaque ligne de chaque page, marquée inactive à son tour : aucune action ne l'atteint, le curseur l'évite, elle n'a pas de zone de clic."""
    def lignes_de(self, page):
        J, p = menu(page); return [x for x in p._entrees() if x['t'] != 'sep']

    def test_aucune_action_n_atteint_une_ligne_inactive(self):
        vus = set()
        for page in PAGES:
            for ligne in self.lignes_de(page):
                lib = ligne['l']; J, p = menu(page, classe=PauseMarquee, inactives=(lib,)); e = p._entrees(); idx = libelles(e).index(lib); vus.add(ligne['t'])
                self.assertTrue(p._inactif(e[idx]), (page, lib)); self.assertFalse(p._actif(e[idx]))
                p.sel[page] = idx; avant = etat(J, p)
                for t in (K.RETURN, K.SPACE, K.LEFT, K.RIGHT, K.DELETE, K.HOME):
                    p.sel[page] = idx; p.touche(t); self.assertEqual(etat(J, p), avant, (page, lib, t)); self.assertIsNone(p._courante())
                self.assertIsNone(p._courante(), (page, lib))
                p.sel[page] = idx; p.saisie = None
                for sens in (K.DOWN, K.UP) if any(p._actif(x) for x in e) else ():                          # navigation : jamais sur la ligne inactive (si une autre ligne est active)
                    p.sel[page] = idx
                    for _ in range(len(e) + 2):
                        p.touche(sens); self.assertNotEqual(p.sel[page], idx, (page, lib, sens))
        self.assertGreaterEqual(vus, {'act', 'choix', 'curs', 'touche', 'slot'})                            # (tous les types de lignes ont été éprouvés)

    def test_dessin_clic_survol_de_chaque_ligne_inactive(self):
        fenetre(); vus = set()
        for page in PAGES_DESSINEES:
            for ligne in self.lignes_de(page):
                lib = ligne['l']; J, p = menu(page, classe=PauseMarquee, inactives=(lib,)); e = p._entrees(); idx = libelles(e).index(lib); vus.add(ligne['t'])
                p.sel[page] = idx; rendre(p)
                if any(p._actif(x) for x in e): self.assertNotEqual(p.sel[page], idx, (page, lib, 'le curseur quitte la ligne inactive'))          # (page d'une seule ligne : le curseur n'a nulle part ou aller)
                z, actif = zone_de(p, idx)
                if z is None: continue                                                                      # (ligne hors de la vue d'une liste qui défile : rien à cliquer)
                self.assertFalse(actif, (page, lib)); self.assertNotIn(idx, p.barres); self.assertNotIn(idx, p.zones_val); self.assertNotIn(idx, p.zones_def); self.assertNotIn(idx, p.zones_mute)
                self.assertFalse([k for k in p.zones_eff if k[0] == idx])
                for f in (0.05, 0.25, 0.5, 0.75, 0.95):
                    x, y = z[0] + f * (z[2] - z[0]), (z[1] + z[3]) / 2; avant = etat(J, p); sel = p.sel[page]
                    p.survol(x, y); self.assertEqual(p.sel[page], sel, (page, lib, 'survol')); p.clic(x, y, GAUCHE); self.assertEqual(etat(J, p), avant, (page, lib, f, 'clic'))
                    self.assertEqual(p.sel[page], sel); p.relache(x, y, GAUCHE); p.glisser(x, y); self.assertEqual(etat(J, p), avant, (page, lib, 'glisser'))
                    rendre(p)
        self.assertGreaterEqual(vus, {'act', 'choix', 'curs', 'touche', 'slot'})

    def test_page_sans_aucune_ligne_active(self):
        """Toutes les lignes inactives : ni erreur ni action ; la sélection ne bouge pas, le curseur n'est pas dessiné."""
        fenetre()
        for page in PAGES_DESSINEES:
            J, p = menu(page); libs = tuple(x['l'] for x in p._entrees() if x['t'] != 'sep')
            J, p = menu(page, classe=PauseMarquee, inactives=libs); p.sel[page] = 2 if page == 'quitter' else 0; sel = p.sel[page]; avant = etat(J, p)
            rendre(p); self.assertEqual(p.sel[page], sel, page)
            for t in (K.DOWN, K.UP, K.LEFT, K.RIGHT, K.RETURN, K.SPACE, K.DELETE, K.HOME, K.PAGEDOWN): p.touche(t)
            p.molette(1); p.molette(-1); self.assertEqual(p.sel[page], sel, page)
            for z in p.zones_off:
                x, y = (z[0] + z[2]) / 2, (z[1] + z[3]) / 2; p.survol(x, y); p.clic(x, y, GAUCHE); p.relache(x, y, GAUCHE); p.glisser(x, y)
            self.assertEqual(p.sel[page], sel, page); rendre(p); self.assertIsNone(p._courante())
            self.assertEqual(etat(J, p), avant, page)

    def test_une_ligne_active_reste_utilisable(self):
        """Marquer les autres lignes ne gêne pas celle qui reste (contrôle du test)."""
        fenetre(); J, p = menu('quitter', classe=PauseMarquee, inactives=('Oui',)); p.sel['quitter'] = 2; rendre(p)
        p.touche(K.UP); self.assertEqual(p.sel['quitter'], 2)                                               # « Oui » est inactive : le curseur reste sur « Non »
        z, actif = zone_de(p, 1); self.assertFalse(actif)
        p.clic((z[0] + z[2]) / 2, (z[1] + z[3]) / 2, GAUCHE); self.assertNotIn('quitter', J.appels); self.assertEqual(p.pile, ['quitter'])          # clic sur « Oui » inactive : l'application ne se ferme pas
        z, actif = zone_de(p, 2); self.assertTrue(actif); p.clic((z[0] + z[2]) / 2, (z[1] + z[3]) / 2, GAUCHE); self.assertFalse(p.ouvert)          # clic sur « Non » (active) : le menu se ferme


class ChangementsPendantUneAction(unittest.TestCase):
    """Une ligne qui devient inactive pendant qu'on la tient (curseur glissé, valeur tapée, liste ouverte) est lâchée sans rien changer."""
    def test_curseur_glisse_valeur_tapee_liste_ouverte(self):
        fenetre(); J, p = menu('affichage', classe=PauseMarquee); n = {x['l']: i for i, x in enumerate(p._entrees())}; rendre(p)
        z, _ = zone_de(p, n['Netteté']); bx0, bx1 = p.barres[n['Netteté']]
        p.clic(bx0 + 0.8 * (bx1 - bx0), (z[1] + z[3]) / 2, GAUCHE); self.assertEqual(p.glisse, n['Netteté']); self.assertAlmostEqual(J.reg['nettete'], 0.8, 1)       # (active : le clic règle le curseur)
        p.inactives = ('Netteté',); p.glisser(bx0 + 0.2 * (bx1 - bx0), (z[1] + z[3]) / 2); self.assertIsNone(p.glisse); self.assertAlmostEqual(J.reg['nettete'], 0.8, 1)   # (devenue inactive en la tenant : lâchée)
        p.inactives = (); p.saisie = [n['Netteté'], '5']; p.inactives = ('Netteté',); rendre(p); self.assertIsNone(p.saisie)
        p.inactives = (); p.sel['affichage'] = n['Shader']; p.touche(K.RETURN); self.assertIsNotNone(p.deroule)                                  # liste ouverte sur « Shader »
        p.inactives = ('Shader',); rendre(p); self.assertIsNone(p.deroule)


class LibelleModifications(unittest.TestCase):
    def test_libelle_partout(self):
        J, p = menu('racine'); libs = libelles(p._entrees())
        self.assertIn('Modifications', libs); self.assertNotIn('Triches', libs); self.assertEqual(libs.index('Modifications'), libs.index('Commandes') + 1)
        e = next(x for x in p._entrees() if x['l'] == 'Modifications'); e['ok'](); self.assertEqual(p.ecran, 'modifications'); self.assertEqual([x['l'] for x in p._entrees()], ['PV et PM restaurés au niveau supérieur'])
        base = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
        for fich in ('dq4_pc/pause.py', 'dq4_pc/fenetre.py', 'dq4_pc/reglages.py', 'README.md') + tuple('outils/' + f for f in sorted(os.listdir(os.path.join(base, 'outils'))) if f.endswith('.py') and f != os.path.basename(__file__)):
            with open(os.path.join(base, fich), encoding='utf-8') as f: self.assertNotIn('triche', f.read().lower(), fich)


if __name__ == '__main__':
    unittest.main(verbosity=1)
