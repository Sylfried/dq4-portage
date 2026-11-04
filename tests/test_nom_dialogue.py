"""Nom de l'interlocuteur dans la boite de dialogue du jeu (MenuMessage, commande 4 du port 1), sans fenetre ni moteur :

  1. protocole : `[4, 0]` = pas de nom ; `[4, 1]` annonce le nom, que le PAQUET SUIVANT du port porte (un entier par caractere) ; le nom est efface quand la fenetre se cache (SetVisible(false)) ;
     les autres commandes (type, curseur, defilement) continuent de marcher, et ni elles ni les autres ports ne sont pris pour le nom ;
  2. `FenetreMessage.regler(typ, y, feed, qui)` : le nom n'est montre que sur la fenetre du terrain (type 0) ; le cadre devient frameData 191 (onglet) et un texte « qui » apparait (m_who : ancre haut-centre,
     taille 10, position locale (-104,5 ; 4 ; dy - 104)) ; sans nom, ou en combat (types 1 a 3), le rendu reste EXACTEMENT celui d'avant (cadre 192, aucun noeud « qui ») ;
  3. les cotes qui posent la fenetre (etendue, bas) ne changent pas avec l'onglet (le Oui/Non et l'echelle gardent leur place) ;
  4. (si le cache d'interface existe : DQ_CACHE_UI, sinon /tmp/uicache4) les VRAIS cadres : 191 = 192 + onglet de 246 x 32 qui depasse vers le haut.

    python3 outils/test_nom_dialogue.py        (Linux sans ecran : pyglet en mode « headless »)
"""
import os, sys, types, unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import pyglet
if sys.platform.startswith('linux') and not os.environ.get('DISPLAY'): pyglet.options['headless'] = True; pyglet.options['shadow_window'] = False
from dq4_pc.menus import ui_menu as UM
from dq4_pc.noyau import moteur as MO

CACHE = os.environ.get('DQ_CACHE_UI', '/tmp/uicache4')


def chars(s): return [ord(c) for c in s]


def faux_cadre(z_haut):
    """Cadre minimal : un rectangle de 452 x 126 (x -223..229, z -251..-125) ; avec onglet : + un rectangle x -223..23, z -125..z_haut."""
    vt = [[-223.0, -251.0], [229.0, -251.0], [229.0, -125.0], [-223.0, -125.0]]; tri = [0, 1, 2, 0, 2, 3]
    if z_haut > -125.0: vt += [[-223.0, -125.0], [23.0, -125.0], [23.0, z_haut], [-223.0, z_haut]]; tri += [4, 5, 6, 4, 6, 7]
    return dict(vtx=vt, uv=[[0.0, 0.0]] * len(vt), tri=tri)


def faux_ml(avec_cadres=True):
    base = faux_cadre(-125.0)
    t0 = dict(win=[0.0, 10.0, 86.0], canvas=dict(vtx=[[-217.0, 4.0, -140.0], [217.0, 4.0, -140.0], [217.0, 4.0, -240.5], [-217.0, 4.0, -240.5]], uv=[[0, 0], [1, 0], [1, 1], [0, 1]], tris=[0, 1, 2, 0, 2, 3]),
              feed_local=[0.0, 8.0, -235.0], frame_mesh=dict(vtx=base['vtx'], uv=base['uv'], tris=base['tri']))
    t1 = dict(t0, win=[-225.0, 10.0, -362.0])
    msg = dict(types=[t0, t1, dict(t1), dict(t1)], feed=dict(vtx=[[0.0, 0.0], [1.0, 0.0], [1.0, 1.0]], uv=[[0, 0]] * 3, tris=[0, 1, 2], mats=[{'sheet': 0, 'part': 1}]), frame_mats=[{'sheet': 0, 'part': 4}])
    cadres = [None] * 191 + [faux_cadre(-93.0), base] if avec_cadres else []
    return types.SimpleNamespace(message=msg, cadres=cadres, hdr={'lang': {'dy': 20.0, 'hiro': 1.0}})


class TestProtocole(unittest.TestCase):
    def ui(self): return MO.Interface()

    def test_sans_nom(self):
        ui = self.ui(); ui.appliquer([(1, [4, 0])]); self.assertEqual((ui.msg['qui'], ui.msg['qui_att']), ('', False))

    def test_nom_dans_le_paquet_suivant(self):
        ui = self.ui(); ui.appliquer([(1, [4, 1]), (1, chars('Roi Bastien') + [0, 0])])
        self.assertEqual((ui.msg['qui'], ui.msg['qui_att']), ('Roi Bastien', False))

    def test_nom_dans_deux_images_differentes(self):
        ui = self.ui(); ui.appliquer([(1, [4, 1])]); self.assertTrue(ui.msg['qui_att']); ui.appliquer([(1, chars('Angus'))]); self.assertEqual(ui.msg['qui'], 'Angus')

    def test_le_nom_n_est_pas_pris_pour_une_commande(self):
        """Le paquet du nom commence par un caractere (ici 1 = « curseur », 2 = « type »...) : il ne doit etre lu que comme du texte."""
        ui = self.ui(); ui.msg['type'] = 0; ui.appliquer([(1, [4, 1]), (1, [1, 1, 2, 3])])
        self.assertEqual((ui.msg['type'], ui.msg['feed'], ui.msg['qui']), (0, False, '\x01\x01\x02\x03'))
        ui.appliquer([(1, [1, 1])]); self.assertTrue(ui.msg['feed'])                  # le paquet d'apres est de nouveau une commande

    def test_nom_suivant_remplace_le_precedent(self):
        ui = self.ui(); ui.appliquer([(1, [4, 1]), (1, chars('Roi Bastien')), (1, [4, 1]), (1, chars('Angus'))]); self.assertEqual(ui.msg['qui'], 'Angus')

    def test_pas_de_nom_efface_le_precedent(self):
        ui = self.ui(); ui.appliquer([(1, [4, 1]), (1, chars('Angus')), (1, [4, 0])]); self.assertEqual(ui.msg['qui'], '')

    def test_autres_commandes_inchangees(self):
        ui = self.ui(); ui.appliquer([(1, [0, 2]), (1, [1, 1]), (1, [3, 40])])
        self.assertEqual((ui.msg['type'], ui.msg['feed'], ui.msg['y'], ui.msg['qui']), (2, True, 40, ''))

    def test_les_autres_ports_ne_donnent_pas_de_nom(self):
        ui = self.ui(); ui.appliquer([(14, [4, 1]), (14, chars('Angus'))]); self.assertEqual((ui.msg['qui'], ui.msg['qui_att']), ('', False))


class TestFenetre(unittest.TestCase):
    def fen(self, **kw): return UM.FenetreMessage(faux_ml(**kw))

    def test_sans_nom_comme_avant(self):
        f = self.fen(); f.regler(0, 0, False, '')
        self.assertEqual(sorted(f.N), ['cadre', 'canevas', 'curseur'])
        self.assertEqual(len(f.N['cadre']['vtx']), 4); self.assertFalse(f.avec_nom)

    def test_avec_nom_onglet_et_texte(self):
        f = self.fen(); f.regler(0, 0, False, 'Roi Bastien')
        self.assertEqual(len(f.N['cadre']['vtx']), 8); self.assertTrue(f.avec_nom)
        q = f.N['qui']; self.assertEqual(q['text']['text'], 'Roi Bastien')
        self.assertEqual((q['text']['anchor'], q['text']['alignment'], q['text']['characterSize']), (1, 1, 10.0))
        self.assertEqual(q['pos'], [-104.5, 14.0, 86.0 - 104.0 + 20.0])

    def test_seulement_la_fenetre_du_terrain(self):
        for typ in (1, 2, 3, 4):
            f = self.fen(); f.regler(typ, 0, False, 'Angus'); self.assertNotIn('qui', f.N, typ); self.assertFalse(f.avec_nom); self.assertEqual(f.qui, '')

    def test_nom_qui_vient_et_s_en_va(self):
        f = self.fen(); f.regler(0, 0, False, ''); f.regler(0, 0, False, 'Angus'); self.assertIn('qui', f.N); f.regler(0, 0, False, ''); self.assertNotIn('qui', f.N); self.assertEqual(len(f.N['cadre']['vtx']), 4)

    def test_changer_de_nom_sans_reconstruire(self):
        f = self.fen(); f.regler(0, 0, False, 'Angus'); n = f.N; f.regler(0, 0, False, 'Roi Bastien'); self.assertIs(f.N, n); self.assertEqual(f.N['qui']['text']['text'], 'Roi Bastien')

    def test_cotes_inchangees(self):
        a = self.fen(); a.regler(0, 0, False, ''); b = self.fen(); b.regler(0, 0, False, 'Angus')
        self.assertEqual((a.etendue(), a.bas()), (b.etendue(), b.bas())); self.assertEqual(a.etendue(), (86.0 - 251.0, 86.0 - 125.0))
        self.assertEqual(a.etendue_x(), b.etendue_x())

    def test_defilement_et_curseur_gardes_avec_le_nom(self):
        f = self.fen(); f.regler(0, 100, True, 'Angus'); self.assertTrue(f.N['curseur']['act']); self.assertAlmostEqual(f.N['canevas']['uv'][0][1], 100 / 512.0)
        f.regler(0, 100, False, ''); self.assertFalse(f.N['curseur']['act']); self.assertAlmostEqual(f.N['canevas']['uv'][0][1], 100 / 512.0)

    def test_sans_cadre_191_pas_de_nom(self):
        f = self.fen(avec_cadres=False); f.regler(0, 0, False, 'Angus'); self.assertNotIn('qui', f.N); self.assertEqual(len(f.N['cadre']['vtx']), 4)

    def test_le_nom_est_dessine_comme_un_texte_de_menu(self):
        """Rendu._items doit trouver le texte (un maillage sans sommets + un texte) et ne rien dessiner d'autre pour ce noeud."""
        f = self.fen(); f.regler(0, 0, False, 'Angus'); items = UM.Rendu._items(types.SimpleNamespace(), f)
        self.assertEqual(sorted(g for _, _, g, _ in items), ['m', 'm', 't'])            # cadre + canevas + texte (le curseur de fin de page est cache)
        self.assertEqual([x[1]['text']['text'] for _, _, g, x in items if g == 't'], ['Angus'])

    def test_apercu_de_l_editeur_sans_nom(self):
        f = self.fen(); self.assertEqual(f.qui, ''); self.assertNotIn('qui', f.N)


class TestVraisCadres(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        l, c = os.path.join(CACHE, 'ui_layout.json'), os.path.join(CACHE, 'ui_frameData.bin')
        if not (os.path.exists(l) and os.path.exists(c)): raise unittest.SkipTest('cache d\'interface absent : ' + CACHE)
        cls.ml = UM.MiseEnPage(l, c)

    def test_191_est_192_plus_un_onglet(self):
        a, b = self.ml.cadres[191], self.ml.cadres[192]
        za, zb = [v[1] for v in a['vtx']], [v[1] for v in b['vtx']]
        self.assertEqual((min(za), max(za)), (-251.0, -93.0)); self.assertEqual((min(zb), max(zb)), (-251.0, -125.0))
        xs = [v[0] for v in a['vtx'] if v[1] > -125.0]; self.assertEqual((min(xs), max(xs)), (-223.0, 23.0))             # onglet : 246 de large, 32 de haut
        self.assertEqual((min(v[0] for v in a['vtx']), max(v[0] for v in a['vtx'])), (min(v[0] for v in b['vtx']), max(v[0] for v in b['vtx'])))      # meme largeur de cadre

    def test_le_cadre_du_terrain_de_la_mise_en_page_est_192(self):
        t0 = self.ml.message['types'][0]['frame_mesh']; b = self.ml.cadres[192]
        self.assertEqual(sorted(map(tuple, t0['vtx'])), sorted(tuple(v) for v in b['vtx']))

    def test_regler_avec_les_vrais_cadres(self):
        f = UM.FenetreMessage(self.ml); f.regler(0, 0, False, ''); e0 = f.etendue(); f.regler(0, 0, False, 'Roi Bastien')
        self.assertEqual(len(f.N['cadre']['vtx']), len(self.ml.cadres[191]['vtx'])); self.assertEqual(f.etendue(), e0)
        z = [f.N['cadre']['pos'][2] + v[1] for v in f.N['cadre']['vtx']]; self.assertEqual(max(z) - e0[1], 32.0)          # l'onglet depasse de 32 au-dessus du cadre


if __name__ == '__main__':
    unittest.main(verbosity=1)
