"""Enchainement des animations d'un tour en vitesse automatique (retour de Sylfried, 14 h 12) : « quand je donne un coup, le montant des degats doit apparaitre plus vite ».

Moteur reel (images du moteur, 30 par seconde) : un coup d'attaque sur la carte du monde (slot 4, rencontre forcee). `Vitesse de combat` impose OptionStatus.battleSpeed (g_Option + 5) : 0 / 1 / 2 / 3 = attente de
12 / 22 / 32 / 42 images entre deux messages ; Normal / Rapide / Tres rapide imposent 0 (reglages.CODE_DEFILEMENT_AUTO), l'ancien Normal imposait 2. Mesure : animation du coup (modele 5303) -> nombre de degats ;
la duree de l'animation elle-meme ne change pas.

    DQ_APK=<dossier des APK patches> DQ_SAVES=<dossier des sauvegardes> python3 outils/test_enchainement_tours.py"""
import os, sys, tempfile, unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from dq4_pc.noyau import moteur as MO
from dq4_pc.persistance import reglages as RG

APK, SAVES = os.environ.get('DQ_APK'), os.environ.get('DQ_SAVES')


class Reglage(unittest.TestCase):
    def test_vitesses_automatiques_imposent_l_attente_la_plus_courte(self):
        self.assertEqual([RG.code_defilement(v) for v in RG.VITESSES_COMBAT], [4, 0, 0, 0])      # Manuel : a la main (inchange) ; Normal, Rapide, Tres rapide : 12 images


@unittest.skipUnless(APK and SAVES, 'moteur reel : DQ_APK=<dossier des APK patches> DQ_SAVES=<dossier des sauvegardes>')
class MoteurReel(unittest.TestCase):
    @staticmethod
    def coup(code):
        """-> (image de la commande validee, image du modele d'effet, image de son retrait, image du nombre de degats) du premier coup d'un combat."""
        mo = MO.Moteur(APK, SAVES, tempfile.mkdtemp(prefix='sv_tours_'))
        for _ in range(3): mo.step(0, 0)
        mo.charger_sauvegarde(4)
        for i in range(100): mo.step(0, 0x10 if i % 10 == 0 else 0)
        if mo.etat.partie != MO.PARTIE_CHAMP:
            mo.demarrer_champ()
            for i in range(120): mo.step(0, 0)
        c = mo.core; mo.imposer_defilement(code)
        c.call(mo.E('_ZN7Encount12forceEncountEv'), c.call(mo.E('_ZN7Encount12getSingletonEv'), label='enc'), label='force')
        for i in range(900):
            mo.step([0x4, 0x8][(i // 20) % 2], 0)
            if mo.etat.partie == MO.PARTIE_COMBAT: break
        r = dict(menu=None, effet=None, fin=None, nombre=None); vu = False; rel = None; att = 0
        for i in range(1500):
            if rel is not None: mo.envoyer_menu(rel, 1, -1, 0); rel = None
            port = mo.menu_actif()
            if port is not None and not mo.msg_visible:
                vu = True; att += 1
                if att % 4 == 0: mo.envoyer_menu(port, 1, -1, 0x10); rel = port
            elif vu and r['menu'] is None: r['menu'] = mo.images
            pq = mo.step(0, 0)
            if r['menu'] is None and vu and port is None and not mo.msg_visible: r['menu'] = mo.images
            for t, a, f in pq:
                if t == 21 and len(a) >= 2 and a[1] == 5303 and r['effet'] is None: r['effet'] = mo.images
                if t == 21 and len(a) >= 2 and a[1] == -1 and a[0] == 2 and r['effet'] is not None and r['fin'] is None: r['fin'] = mo.images
            if mo.ui.degats and r['nombre'] is None: r['nombre'] = mo.images
            mo.ui.degats = []
            if r['nombre'] is not None: break
        return r

    def test_le_nombre_de_degats_arrive_plus_vite_et_l_animation_ne_change_pas(self):
        avant, apres = self.coup(2), self.coup(0)
        for r in (avant, apres): self.assertTrue(all(v is not None for v in r.values()), r)
        self.assertEqual(avant['fin'] - avant['effet'], apres['fin'] - apres['effet'])                         # l'animation du coup garde sa duree du jeu
        self.assertGreaterEqual(avant['nombre'] - avant['effet'], 22)                                          # (ancien Normal : 23 images, 0,77 s)
        self.assertLessEqual(apres['nombre'] - apres['effet'], 14)                                             # maintenant 13 images (0,43 s) : tout de suite apres la fin de l'animation
        self.assertLess(apres['nombre'], avant['nombre'])


if __name__ == '__main__':
    unittest.main()
