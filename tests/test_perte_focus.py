"""#235 (audit UNI-02 et SND-07, sondage du 04/11/2026 : « pause a chaque perte de focus ») : quand la fenetre perd le focus (Alt + Tab, clic ailleurs, minimisation), le jeu s'arrete et la musique et les bruitages se
mettent en pause (Sound.SystemPause de l'original) ; au retour, le son repart la ou il s'etait arrete et le jeu reprend sans rattrapage.
- Son : `Son.perdre_focus` (faux lecteurs, sans fenetre ni carte son), y compris pendant l'ecoute de la page Son du menu et menu suspendu.
- Jeu : `Jeu.on_deactivate` / `on_activate` / `_boucle` sur un faux Jeu (ignore si pyglet n'est pas importable : les tests Jeu ne tournent pas en CI).
    python3 tests/test_perte_focus.py"""
import os, sys, time, types, unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import numpy as np


class FauxLecteur:
    def __init__(self): self.playing = True; self.volume = 1.0
    def play(self): self.playing = True
    def pause(self): self.playing = False
    def delete(self): self.playing = False


def nouveau_son():
    """Un Son sans pyglet (modules `pyglet` masque) avec de faux lecteurs : une musique et un bruitage en cours."""
    saved = sys.modules.get('pyglet', 0); sys.modules['pyglet'] = None
    try:
        from dq4_pc import son as SON
        s = SON.Son('inexistant.apk', '/tmp', log=lambda *a: None, journal=lambda *a: None, alerte=lambda *a: None)
    finally:
        if saved == 0: sys.modules.pop('pyglet', None)
        else: sys.modules['pyglet'] = saved
    s.ok = True
    s.bgm = FauxLecteur(); s.bgm_fin = time.time() + 30.0; s.bgm_t0 = time.time()
    s.se = [types.SimpleNamespace(p=FauxLecteur(), fin=time.time() + 5.0, cat='effets', propre=1.0)]
    return s


class SonSansFocus(unittest.TestCase):
    def test_perte_et_retour_du_focus(self):
        s = nouveau_son(); fin = s.bgm_fin
        s.perdre_focus(True)
        self.assertFalse(s.bgm.playing); self.assertFalse(s.se[0].p.playing); self.assertIsNotNone(s.t_pause)
        time.sleep(0.05)
        s.perdre_focus(False)
        self.assertTrue(s.bgm.playing); self.assertTrue(s.se[0].p.playing); self.assertIsNone(s.t_pause)
        self.assertGreater(s.bgm_fin, fin)                                        # (l'echeance de la musique est decalee de la duree de la pause)

    def test_idempotent(self):
        s = nouveau_son(); s.perdre_focus(True); t = s.t_pause; s.perdre_focus(True); self.assertEqual(s.t_pause, t)
        s.perdre_focus(False); s.perdre_focus(False); self.assertTrue(s.bgm.playing)

    def test_pendant_l_ecoute_de_la_page_son(self):
        """La page Son du menu fait jouer les sons menu suspendu (`ecoute`) ; sans focus, rien ne joue quand meme, et le retour du focus rend la main a la page."""
        s = nouveau_son(); s.mettre_en_pause(True); s.ecouter(True)
        self.assertTrue(s.bgm.playing)                                            # (ecoute : on entend les reglages)
        s.perdre_focus(True); self.assertFalse(s.bgm.playing)
        s.ecouter(True); self.assertFalse(s.bgm.playing)                          # (la page redemande l'ecoute : toujours muet)
        s.perdre_focus(False); self.assertTrue(s.bgm.playing)                     # (retour : l'ecoute de la page reprend)

    def test_menu_suspendu_reste_en_pause_au_retour(self):
        s = nouveau_son(); s.mettre_en_pause(True); self.assertFalse(s.bgm.playing)
        s.perdre_focus(True); s.perdre_focus(False)
        self.assertFalse(s.bgm.playing)                                           # (le menu suspend encore le jeu : pas de reprise)
        s.mettre_en_pause(False); self.assertTrue(s.bgm.playing)

    def test_menu_ferme_pendant_la_perte_de_focus(self):
        s = nouveau_son(); s.mettre_en_pause(True); s.perdre_focus(True)
        s.mettre_en_pause(False); self.assertFalse(s.bgm.playing)                 # (toujours sans focus)
        s.perdre_focus(False); self.assertTrue(s.bgm.playing)


class JeuSansFocus(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try: from dq4_pc.fenetre import jeu as fenetre; cls.FE = fenetre
        except Exception as ex: raise unittest.SkipTest('fenetre non importable ici (%r)' % (ex,))

    def faux_jeu(self):
        appels = []
        son = types.SimpleNamespace(hors_focus=False)
        def perdre(oui): son.hors_focus = bool(oui); appels.append(bool(oui))
        son.perdre_focus = perdre
        hud = types.SimpleNamespace(croix_on=True, appui='carte', croix_lacher=lambda: setattr(hud, 'croix_on', False))
        molette = types.SimpleNamespace(en_cours=True, annuler=lambda: setattr(molette, 'en_cours', False))
        j = types.SimpleNamespace(_pret=True, _focus_perdu=False, son=son, hud=hud, molette=molette, appui=('p', 1, 2), survol=[1], acc=0.7, t_boucle=1.0, alpha=0.4, n_boucle=0,
                                  args=types.SimpleNamespace(touches_test=False, shots_boucle=False, options_test=False), hd_jobs={}, pad_prec=9, act_prec={'x': 1}, rep={'a': 1}, souris=(3, 4),
                                  garde_souris=types.SimpleNamespace(clavier=lambda pos: appels.append(('garde', pos))), pad=lambda: 0, _tenue=lambda a: False, camera_oubliee=0)
        j._camera_oublier = lambda: setattr(j, 'camera_oubliee', j.camera_oubliee + 1)
        j.appels = appels
        return j

    def test_perte_du_focus(self):
        j = self.faux_jeu(); self.FE.Jeu.on_deactivate(j)
        self.assertTrue(j._focus_perdu); self.assertEqual(j.appels, [True])
        self.assertFalse(j.molette.en_cours); self.assertFalse(j.hud.croix_on); self.assertIsNone(j.hud.appui); self.assertIsNone(j.appui); self.assertIsNone(j.survol)      # (boutons de souris tenus : relaches)
        self.assertEqual(j.camera_oubliee, 1)                                      # (rotation de la camera demandee a la souris : abandonnee)

    def test_boucle_gelee_sans_focus(self):
        j = self.faux_jeu(); self.FE.Jeu.on_deactivate(j)
        j.acc = 0.7; j.alpha = 0.4; j.t_boucle = 1.0; j.n_boucle = 0
        self.FE.Jeu._boucle(j, 0.016)                                              # (retourne avant tout pas du moteur : un faux Jeu n'a pas de moteur)
        self.assertEqual((j.acc, j.alpha, j.t_boucle), (0.0, 1.0, None)); self.assertEqual(j.n_boucle, 1)

    def test_le_son_est_mis_en_pause_par_la_boucle_si_l_evenement_est_arrive_avant_le_chargement(self):
        j = self.faux_jeu(); j._pret = False; self.FE.Jeu.on_deactivate(j)
        self.assertTrue(j._focus_perdu); self.assertEqual(j.appels, [])           # (rien n'existe encore : pas d'appel)
        j._pret = True; self.FE.Jeu._boucle(j, 0.016); self.assertEqual(j.appels, [True])

    def test_retour_du_focus(self):
        j = self.faux_jeu(); self.FE.Jeu.on_deactivate(j); j.acc = 0.3; j.t_boucle = 5.0; j.rep = {'a': 1}
        self.FE.Jeu.on_activate(j)
        self.assertFalse(j._focus_perdu); self.assertEqual(j.appels[-2:], [False, ('garde', (3, 4))]); self.assertEqual((j.acc, j.t_boucle), (0.0, None)); self.assertEqual(j.rep, {})
        self.assertEqual(j.pad_prec, 0)                                            # (les touches tenues au retour ne sont pas un nouvel appui)

    def test_retour_avant_le_chargement(self):
        j = self.faux_jeu(); j._pret = False; j._focus_perdu = True; self.FE.Jeu.on_activate(j)
        self.assertFalse(j._focus_perdu); self.assertEqual(j.appels, [])


if __name__ == '__main__':
    unittest.main(verbosity=2)
