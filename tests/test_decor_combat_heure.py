"""Decor de combat selon l'heure du monde (retour de Sylfried, 14 h 08 : « le crepuscule ou le leve de soleil dans le decor du combat »).

Moteur reel (Unicorn) : `StageStatus + 0xcc` = heure du monde (0 a 3391, elle avance en marchant), `+ 0xc8` = zone horaire que `WorldLocation::setCurrentTimeZone` en tire :
    0 a 127 : zone 1 ; 128 a 1983 : zone 2 (jour) ; 1984 a 2239 : zone 3 (soir) ; 2240 a 3263 : zone 4 (nuit) ; 3264 a 3391 : zone 1.
`StageStatus::getBtlMapName` (0x1a4580) remplace la derniere lettre du decor par l'octet `zone` de l'octet-table « d n d e n » : zones 1 et 4 -> `_n`, zone 2 -> `_d`, zone 3 -> `_e`.
Il n'existe donc PAS de decor d'aube : le debut et la fin de nuit (zone 1) reprennent le decor de nuit. Le soir (`_e`) existe, est demande par le moteur et chaque decor de la carte du monde en a un.
Le moteur n'envoie en combat ni teinte (paquet 33) ni couleur de fond (paquet 8) : la couleur du jour, du soir et de la nuit est dans les assets (couleurs de sommet + textures `_d`, `_e`, `_n`).
Le FOND du combat est la `bg_color` du bloc FETC du decor charge (`cmd_fld_load` -> `BackColor.SetColor`, lu dans libil2cpp) : orange / rouge au soir, bleu sombre la nuit (teinte_carte.fond_fetc, Fonds).

    DQ_APK=<dossier des APK patches> DQ_SAVES=<dossier des sauvegardes> python3 outils/test_decor_combat_heure.py        (DQ_CACHE=<cache des cartes> : verifie aussi les assets)"""
import os, sys, struct, tempfile, unittest, pickle, json

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from dq4_pc.noyau import moteur as MO
from dq4_pc.monde import donnees as DO
from dq4_pc.monde import teinte_carte as TC

APK, SAVES, CACHE = os.environ.get('DQ_APK'), os.environ.get('DQ_SAVES'), os.environ.get('DQ_CACHE')
ADRESSE_STAGE = 0x23d430          # GOT : StageStatus (g_StageStatus)
CAS = [(64, 1, 'n'), (1000, 2, 'd'), (1984, 3, 'e'), (2239, 3, 'e'), (2240, 4, 'n'), (3300, 1, 'n')]      # (heure du monde, zone attendue, lettre du decor)
DECORS_MONDE = ['btl_pl', 'btl_se', 'btl_sd', 'btl_mt', 'btl_po', 'btl_wd']


class Secours(unittest.TestCase):
    def test_variante_absente_remplacee_par_la_plus_proche(self):
        self.assertEqual(DO.decors_de_secours('btlcc1_n'), ['btlcc1_e', 'btlcc1_d', 'btlcc1'])         # btlcc1 n'a que _d et _e dans les donnees
        self.assertEqual(DO.decors_de_secours('btl_pl_e'), ['btl_pl_d', 'btl_pl_n', 'btl_pl'])
        self.assertEqual(DO.decors_de_secours('btl_pl_d'), ['btl_pl_e', 'btl_pl_n', 'btl_pl'])
        self.assertEqual(DO.decors_de_secours('btl_se_dk'), ['btl_se_n', 'btl_se_d', 'btl_se_e', 'btl_se'])      # monde sombre : le moteur demande btl_se_dk, absent des donnees (seuls pl, po, wd et tc1 l'ont)
        for nom in ('btlcb2', 'ev01', '', None): self.assertEqual(DO.decors_de_secours(nom), [], nom)


class FondFETC(unittest.TestCase):
    @staticmethod
    def map_de(r, g, b, a=0):
        """Fichier .map minimal : un bloc FETC (40 octets) dont les 4 premiers octets utiles sont r, g, b, a."""
        return b'FETC' + struct.pack('<I', 0x28) + bytes([r, g, b, a]) + bytes(28)

    def test_la_couleur_est_lue_dans_le_bloc_fetc(self):
        self.assertEqual(TC.fond_fetc(self.map_de(192, 52, 0)), (192 / 255.0, 52 / 255.0, 0.0))        # btl_mt_e : le rouge orange du coucher de soleil
        self.assertEqual(TC.fond_fetc(self.map_de(0, 0, 0)), (0.0, 0.0, 0.0))

    def test_l_alpha_du_fetc_est_ignore(self):
        self.assertEqual(TC.fond_fetc(self.map_de(10, 20, 30, 0)), TC.fond_fetc(self.map_de(10, 20, 30, 255)))        # alpha 0 dans les 140 decors, shader BackColor sans fusion

    def test_pas_de_bloc_fetc_pas_de_couleur(self):
        self.assertIsNone(TC.fond_fetc(b'FHDR' + struct.pack('<I', 0x98) + bytes(0x90)))
        self.assertIsNone(TC.fond_fetc(b''))

    def test_cache_illisible_ou_absent_donne_none(self):
        d = tempfile.mkdtemp(prefix='fonds_')
        self.assertIsNone(TC.lire_fonds(d))
        with open(os.path.join(d, TC.FICHIER_FONDS), 'w') as fh: fh.write('pas du json')
        self.assertIsNone(TC.lire_fonds(d))
        with open(os.path.join(d, TC.FICHIER_FONDS), 'w') as fh: json.dump({'fonds': {'btl_pl_e': [0.5, 0.25, 0.0]}}, fh)
        self.assertEqual(TC.lire_fonds(d), {'btl_pl_e': (0.5, 0.25, 0.0)})

    def test_fonds_sert_le_cache_puis_laisse_l_estimation_si_absent(self):
        d = tempfile.mkdtemp(prefix='fonds_')
        with open(os.path.join(d, TC.FICHIER_FONDS), 'w') as fh: json.dump({'fonds': {'btl_pl_e': [0.5, 0.25, 0.0]}}, fh)
        class Faux: cache = d
        f = TC.Fonds(Faux())
        self.assertEqual(f.couleur('btl_pl_e'), (0.5, 0.25, 0.0))
        self.assertIsNone(f.couleur('btl_inconnu_d'))


@unittest.skipUnless(APK and SAVES, 'moteur reel : DQ_APK=<dossier des APK patches> DQ_SAVES=<dossier des sauvegardes>')
class MoteurReel(unittest.TestCase):
    @staticmethod
    def rencontre(heure):
        """-> (zone lue, nom du decor, teintes et fonds recus au debut du combat) pour une rencontre sur la carte du monde a cette heure du monde (slot 4)."""
        mo = MO.Moteur(APK, SAVES, tempfile.mkdtemp(prefix='sv_heure_'))
        for _ in range(3): mo.step(0, 0)
        mo.charger_sauvegarde(4)
        for i in range(100): mo.step(0, 0x10 if i % 10 == 0 else 0)
        if mo.etat.partie != MO.PARTIE_CHAMP:
            mo.demarrer_champ()
            for i in range(120): mo.step(0, 0)
        c = mo.core
        g = struct.unpack('<Q', bytes(c.mem(mo.L + ADRESSE_STAGE, 8)))[0]
        c.mem_w(g + 0xcc, struct.pack('<i', heure))
        c.call(mo.E('_ZN3cmn13WorldLocation18setCurrentTimeZoneEv'), c.call(mo.E('_ZN3cmn13WorldLocation12getSingletonEv'), label='wl'), label='zone')
        zone = struct.unpack('<I', bytes(c.mem(g + 0xc8, 4)))[0]
        c.call(mo.E('_ZN7Encount12forceEncountEv'), c.call(mo.E('_ZN7Encount12getSingletonEv'), label='enc'), label='force')
        recus = []; n0 = None
        for i in range(1500):
            pq = mo.step([0x4, 0x8][(i // 20) % 2], 0)
            if n0 is not None: recus += [(t, list(f[:3])) for t, a, f in pq if t in (8, 33)]
            if mo.etat.partie == MO.PARTIE_COMBAT and n0 is None: n0 = mo.images
            if n0 is not None and mo.images - n0 > 40: break
        return zone, mo.etat.carte, recus

    def test_le_moteur_choisit_jour_soir_ou_nuit_selon_l_heure_du_monde(self):
        for heure, zone_att, lettre in CAS:
            zone, carte, recus = self.rencontre(heure)
            self.assertEqual(zone, zone_att, 'heure %d' % heure)
            self.assertEqual(carte, 'btl_pl_' + lettre, 'heure %d : zone %d' % (heure, zone))
            self.assertEqual(recus, [], 'heure %d : le moteur ne teinte pas le decor de combat et n envoie pas de fond' % heure)


@unittest.skipUnless(APK, 'ressources reelles : DQ_APK=<dossier des APK patches>')
class FondsReels(unittest.TestCase):
    """Les 140 decors de combat du paquet de donnees (lecture du paquet : plusieurs secondes, ~1 Go : a lancer via moteur_slot.sh)."""
    @classmethod
    def setUpClass(cls):
        cls.donnees = DO.Donnees(os.path.join(APK, 'split_UnityDataAssetPack.apk'), tempfile.mkdtemp(prefix='fonds_reels_'), log=lambda *a: None)
        cls.fonds = TC.calculer_fonds(cls.donnees)

    def test_les_140_decors_ont_un_fond(self):
        self.assertEqual(len(self.fonds), 140)
        self.assertEqual(TC.lire_fonds(self.donnees.cache), self.fonds)                         # et le cache est relu tel quel

    def test_le_fond_du_soir_est_plus_chaud_et_celui_de_la_nuit_plus_sombre(self):
        def chaud(c): return c[0] - c[2]
        for base in ('btl_pl', 'btl_se', 'btl_sd', 'btl_mt', 'btl_wd'):
            j, e, n = (self.fonds['%s_%s' % (base, x)] for x in 'den')
            self.assertGreater(chaud(e), chaud(j) + 0.15, base + ' : le fond du soir est plus chaud (orange) que celui du jour')
            self.assertLess(sum(n), sum(j), base + ' : le fond de la nuit est plus sombre que celui du jour')

    def test_valeurs_connues(self):
        r = lambda nom: tuple(round(255 * x) for x in self.fonds[nom])
        self.assertEqual(r('btl_pl_d'), (77, 186, 88)); self.assertEqual(r('btl_mt_e'), (192, 52, 0)); self.assertEqual(r('btl_se_n'), (8, 38, 107)); self.assertEqual(r('btl_sd_e'), (255, 115, 33))


@unittest.skipUnless(CACHE and os.path.isdir(CACHE), 'assets : DQ_CACHE=<cache des cartes>')
class Assets(unittest.TestCase):
    @staticmethod
    def decor(nom):
        with open(os.path.join(CACHE, 'carte10_%s.pkl' % nom), 'rb') as fh: return pickle.load(fh)

    def test_chaque_decor_de_la_carte_du_monde_a_ses_trois_variantes(self):
        for base in DECORS_MONDE:
            for lettre in 'den': self.assertTrue(os.path.exists(os.path.join(CACHE, 'carte10_%s_%s.pkl' % (base, lettre))), '%s_%s' % (base, lettre))

    def test_le_soir_est_plus_rouge_et_la_nuit_plus_sombre_et_plus_bleue_que_le_jour(self):
        def moyenne(nom):
            c = self.decor(nom); r = [g[2][:, :3].mean(0) for g in c['groupes'].values()]
            return sum(r) / len(r)                                      # couleur de sommet moyenne : la teinte du moment est cuite dans l'asset
        for base in DECORS_MONDE:
            j, s, n = moyenne(base + '_d'), moyenne(base + '_e'), moyenne(base + '_n')
            self.assertGreater(j.mean(), s.mean(), base + ' : le soir est plus sombre que le jour')
            self.assertGreater(s.mean(), n.mean(), base + ' : la nuit est plus sombre que le soir')
            self.assertGreater(s[0] - s[2], j[0] - j[2] + 0.1, base + ' : le soir est plus rouge (rouge - bleu)')
            self.assertGreater(j[0] - j[2], n[0] - n[2] + 0.05, base + ' : la nuit est plus bleue (rouge - bleu)')


if __name__ == '__main__': unittest.main()
