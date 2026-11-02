"""Test de la teinte du decor (paquet 33, `cmd_map_color_rate`) et de l'echelle des sprites (paquet 13, bit 0x800) : decodage dans `Etat.appliquer`, reconnaissance des groupes « tz_ »,
interrupteur de debogage ; partie « moteur reel » facultative (--apk et --saves : la teinte arrive apres le paquet 0 a chaque chargement de carte).

    python3 outils/test_teinte_carte.py [--apk "<dossier des APK patches>" --saves "<dossier des sauvegardes>"]
Sans ecran, sans GL. Les sauvegardes ne sont ouvertes qu'en lecture (le moteur ecrit dans un dossier temporaire).
"""
import argparse, os, pickle, sys, tempfile, types, unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'dq4_pc'))
import moteur as MO
import teinte_carte as TC

ARGS = None


def pq(*paquets): return [(t, list(a), list(f)) for t, a, f in paquets]


class DecodageEtat(unittest.TestCase):
    def test_neutre_par_defaut(self):
        self.assertEqual(MO.Etat().teinte, (1.0, 1.0, 1.0))

    def test_paquet_33(self):
        e = MO.Etat(); e.appliquer(pq((33, [], [1.25, 0.65, 0.75])), lambda: 'x')
        self.assertEqual(e.teinte, (1.25, 0.65, 0.75))
        e.appliquer(pq((33, [], [0.8, 0.8, 1.1])), lambda: 'x')                       # la derniere teinte gagne (fondu de teinte : un paquet par image)
        self.assertEqual(e.teinte, (0.8, 0.8, 1.1))

    def test_paquet_33_incomplet_ignore(self):
        e = MO.Etat(); e.appliquer(pq((33, [], [1.25, 0.65])), lambda: 'x')
        self.assertEqual(e.teinte, (1.0, 1.0, 1.0))

    def test_nouvelle_carte_remet_le_neutre(self):
        e = MO.Etat(); e.appliquer(pq((33, [], [1.3, 0.7, 0.55])), lambda: 'x')
        e.appliquer(pq((0, [0], [])), lambda: 'mlb1a')
        self.assertEqual(e.teinte, (1.0, 1.0, 1.0))
        e.appliquer(pq((0, [0], []), (33, [], [1.25, 0.65, 0.75])), lambda: 'mlb1a')      # le moteur envoie la teinte APRES le paquet 0, dans la meme image
        self.assertEqual(e.teinte, (1.25, 0.65, 0.75))

    def test_chargement_de_la_carte_du_monde_remet_le_neutre(self):
        e = MO.Etat(); e.appliquer(pq((33, [], [1.3, 0.7, 0.55])), lambda: 'x')
        e.appliquer(pq((27, [1], [])), lambda: 'x')
        self.assertEqual(e.teinte, (1.0, 1.0, 1.0))

    def test_ancien_etat_enregistre(self):
        e = MO.Etat(); d = dict(e.__dict__); del d['teinte']
        e2 = MO.Etat.__new__(MO.Etat); e2.__setstate__(d)
        self.assertEqual(e2.teinte, (1.0, 1.0, 1.0))
        e3 = pickle.loads(pickle.dumps(MO.Etat()))
        self.assertEqual(e3.teinte, (1.0, 1.0, 1.0))


class GroupesTz(unittest.TestCase):
    IDS = {101, 202}

    def test_neutre(self):
        self.assertTrue(TC.teinte_neutre((1.0, 1.0, 1.0)))
        self.assertTrue(TC.teinte_neutre(None))
        self.assertFalse(TC.teinte_neutre((1.25, 0.65, 0.75)))
        self.assertFalse(TC.teinte_neutre((1.0, 1.0, 0.99)))

    def test_identifiant(self):
        self.assertTrue(TC.groupe_tz(101, self.IDS)); self.assertFalse(TC.groupe_tz(303, self.IDS))

    def test_transparent(self):
        self.assertTrue(TC.groupe_tz(('tr', 3, 202), self.IDS)); self.assertFalse(TC.groupe_tz(('tr', 3, 303), self.IDS))

    def test_palette_animee(self):
        self.assertTrue(TC.groupe_tz(('pam', 'tz_damg01', 0, 0), self.IDS)); self.assertTrue(TC.groupe_tz(('tr', 1, ('pam', 'tz_kifkyk1', 2, 0)), self.IDS))
        self.assertFalse(TC.groupe_tz(('pam', 'wtkira1', 0, 0), self.IDS)); self.assertFalse(TC.groupe_tz(('pam', 'doku00', 1, 0), self.IDS))

    def test_liste_inconnue_tout_est_teinte(self):
        self.assertFalse(TC.groupe_tz(101, None)); self.assertFalse(TC.groupe_tz(101, set()))

    def test_fichier_du_cache(self):
        import json
        d = tempfile.mkdtemp(prefix='tz_')
        self.assertIsNone(TC.lire(d))
        with open(os.path.join(d, TC.FICHIER), 'w') as fh: json.dump({'ids': [5, 7]}, fh)
        self.assertEqual(TC.lire(d), {5, 7})
        with open(os.path.join(d, TC.FICHIER), 'w') as fh: fh.write('pas du json')
        self.assertIsNone(TC.lire(d))

    def test_cles_lues_dans_le_cache_sans_toucher_au_paquet(self):
        import json
        d = tempfile.mkdtemp(prefix='tz_')
        with open(os.path.join(d, TC.FICHIER), 'w') as fh: json.dump({'ids': [9]}, fh)
        faux = types.SimpleNamespace(cache=d)                              # aucune methode : un acces au paquet de donnees leverait
        self.assertEqual(TC.Cles(faux).ids(), {9})


class EchelleSprites(unittest.TestCase):
    def _etat(self):
        e = MO.Etat(); e.appliquer(pq((12, [0, 106], []), (12, [1, 130], [])), lambda: 'x'); return e

    def test_echelle_par_defaut(self):
        e = self._etat(); self.assertEqual(e.sprites[0]['ech'], 1.0)

    def test_premiere_mise_a_jour_ignoree_puis_echelle_lue(self):
        e = self._etat()
        e.appliquer(pq((13, [0x6800, 1537], [0.062, 1.08, 0.047, -3.2])), lambda: 'x')      # 1re mise a jour (le personnage est place) : echelle de depart sans suite (0,062, puis 1,0 une image apres), ignoree ; les flottants suivants restent alignes
        s = e.sprites[0]; self.assertEqual(s['ech'], 1.0); self.assertAlmostEqual(s['pos'][0], 1.08, 4); self.assertAlmostEqual(s['pos'][2], -3.2, 4); self.assertEqual((s['pose'], s['dir']), (1, 6))
        e.appliquer(pq((13, [0x800], [1.0])), lambda: 'x'); self.assertEqual(e.sprites[0]['ech'], 1.0)
        e.appliquer(pq((13, [0x800], [0.7383])), lambda: 'x'); self.assertAlmostEqual(e.sprites[0]['ech'], 0.7383, 4); self.assertAlmostEqual(e.sprites[0]['pos'][0], 1.08, 4)
        self.assertEqual(e.sprites[1]['ech'], 1.0)

    def test_couleur_avec_echelle(self):
        e = self._etat(); e.sprites[1]['pos'] = (0.0, 0.0, 0.0)                              # deja place
        e.appliquer(pq((13, [0x1800 | 1], [0.5, 1.0, 0.5, 0.25, 0.75])), lambda: 'x')
        s = e.sprites[1]; self.assertEqual(s['ech'], 0.5); self.assertEqual(s['col'], (1.0, 0.5, 0.25, 0.75))

    def test_sprite_recree_remis_a_1(self):
        e = self._etat(); e.sprites[0]['pos'] = (0.0, 0.0, 0.0); e.appliquer(pq((13, [0x800], [0.5])), lambda: 'x'); self.assertEqual(e.sprites[0]['ech'], 0.5)
        e.appliquer(pq((12, [0, 106], [])), lambda: 'x'); self.assertEqual(e.sprites[0]['ech'], 1.0)


class MoteurReel(unittest.TestCase):
    def test_teinte_apres_chargement(self):
        apk = (ARGS.apk if ARGS else None) or os.environ.get('DQ_APK'); saves = (ARGS.saves if ARGS else None) or os.environ.get('DQ_SAVES')
        if not apk or not saves: self.skipTest('moteur reel : --apk et --saves (ou DQ_APK et DQ_SAVES)')
        m = MO.Moteur(apk, saves, tempfile.mkdtemp(prefix='sv_teinte_')); self.assertTrue(m.charger_sauvegarde(1))
        for _ in range(10): m.step(0, 0)
        for carte, attendu in (('mlb1a', (1.25, 0.65, 0.75)), ('teout1', (1.3, 0.7, 0.55)), ('dab1', (1.0, 1.0, 1.0))):
            m.demarrer_ville(carte)
            for _ in range(60): m.step(0, 0)
            self.assertEqual(m.etat.carte, carte)
            for a, b in zip(m.etat.teinte, attendu): self.assertAlmostEqual(a, b, 3, carte)


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('--apk'); ap.add_argument('--saves'); ARGS, reste = ap.parse_known_args()
    unittest.main(argv=[sys.argv[0]] + reste, verbosity=2)
