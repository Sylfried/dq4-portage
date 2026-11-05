"""Un seul dossier de sauvegardes (D-232 ; demande de Sylfried du 04/11/2026 à 23 h 55 : « tu ne pourrais juste pas stocker tous les fichiers directement dans le dossier "sauvegardes" ou un seul sous-dossier pour coller
à la logique des états ? Comme ça si je veux transférer toutes les sauvegardes du mobile sur le patch je n'ai pas besoin de faire de gymnastique mentale à deviner quel fichier mettre dans quel dossier »), sans fenêtre ni moteur :

  1. disposition : `donnees\\sauvegardes` reçoit data1.dat à data5.dat, data9.dat ET `etats\\` (comme le .zip d'export) ; `portage` n'est plus qu'un autre nom de ce dossier ;
  2. reprise des anciens `sauvegardes\\portage` et `sauvegardes\\mobile\\<date>` au démarrage : les journaux sont COPIÉS dans `sauvegardes\\` (le portage d'abord, puis la copie du téléphone la plus récente, sans rien écraser : ce que le jeu lisait
     avant, fichier par fichier), puis les deux anciens dossiers sont DÉPLACÉS tels quels dans `avant_rangement_<date>\\` ; rien n'est supprimé, une seconde reprise ne fait rien ;
  3. cas réel de Sylfried : fichiers du portage plus anciens que ceux du téléphone, `manifest.json` dans la copie du téléphone, vieux `dq4_pc\\sauvegardes` encore là (ne doit pas passer devant les fichiers d'aujourd'hui) ;
  4. sécurité : un journal déjà posé dans `sauvegardes\\` n'est pas écrasé, une erreur de déplacement laisse tout en place (le jeu lit déjà `sauvegardes\\`), DQ4_JEUX (copie du téléphone ailleurs) n'est pas touché ;
  5. le moteur lit ce dossier (`fichiers_effectifs`), l'export le met à plat et l'import y écrit.

    python3 tests/test_sauvegardes_un_dossier.py
"""
import os, shutil, sys, tempfile, unittest, zipfile
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from dq4_pc import langue as _LANGUE; _LANGUE.regler('fr')          # (D-238 : ces tests attendent les textes francais, quelle que soit la langue de l'ordinateur)
from dq4_pc import chemins as CH
from dq4_pc.persistance import sauvegardes as S

NOMS = CH.NOMS_JOURNAUX


def ecrire(chemin, contenu=b'x'):
    os.makedirs(os.path.dirname(chemin), exist_ok=True)
    with open(chemin, 'wb') as f: f.write(contenu)
    return chemin


def contenu(*p):
    with open(os.path.join(*p), 'rb') as f: return f.read()


def tous_les_fichiers(racine):
    return sorted(os.path.relpath(os.path.join(r, f), racine) for r, _, fs in os.walk(racine) for f in fs)


class Disposition(unittest.TestCase):
    def test_un_seul_dossier(self):
        d = CH.Dossiers('/projet', env={})
        self.assertEqual(d.portage, d.sauvegardes); self.assertEqual(d.etats, os.path.join(d.sauvegardes, 'etats'))
        self.assertEqual(d.dossier_etats(d.portage), os.path.join(d.sauvegardes, 'etats')); self.assertEqual(d.dossier_copies(d.portage), d.sauvegardes)

    def test_noms_des_fichiers_du_jeu(self):
        self.assertEqual(NOMS, ('data1.dat', 'data2.dat', 'data3.dat', 'data4.dat', 'data5.dat', 'data9.dat')); self.assertEqual(S.NOMS, NOMS)

    def test_aucun_code_ne_range_encore_dans_portage(self):
        """Le dossier `portage` n'existe plus que comme ancien nom (chemins.py : repris puis range) ; aucun autre module ne le construit."""
        racine = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'dq4_pc')
        for dossier, _d, fichiers in os.walk(racine):
            for f in fichiers:
                if f.endswith('.py') and f != 'chemins.py':
                    with open(os.path.join(dossier, f), encoding='utf-8') as fh: src = fh.read()
                    self.assertNotIn("'portage'", src, f); self.assertNotIn('sauvegardes\\\\portage', src, f)


class Reprise(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.mkdtemp(prefix='un_dossier_'); self.d = CH.Dossiers(self.t, env={}); self.sv = self.d.sauvegardes

    def tearDown(self): shutil.rmtree(self.t, ignore_errors=True)

    def migrer(self, d=None): return CH.migrer(d or self.d, log=lambda *a: None)

    def cas_de_sylfried(self):
        """Ce que son PC contenait au 04/11/2026 : portage (data1, data5, data9 d'aujourd'hui ; data2 à data4 plus anciens), copie du téléphone plus récente pour data2 à data4, plus un manifeste, et un vieux dq4_pc\\sauvegardes."""
        for nom in ('data1.dat', 'data5.dat', 'data9.dat'): ecrire(os.path.join(self.d.ancien_portage, nom), b'portage_' + nom.encode())
        for nom in ('data2.dat', 'data3.dat', 'data4.dat'): ecrire(os.path.join(self.d.ancien_portage, nom), b'portage_vieux_' + nom.encode())
        tel = os.path.join(self.d.mobile, '20261103_222423')
        for nom in NOMS: ecrire(os.path.join(tel, nom), b'tel_' + nom.encode())
        ecrire(os.path.join(tel, 'manifest.json'), b'{"device": "SM S938B"}'); ecrire(os.path.join(self.d.mobile, '20261007_190735', 'data1.dat'), b'tel_ancien')
        ecrire(os.path.join(self.sv, 'avant_import_20261101_192625', 'data2.dat'), b'AV'); ecrire(os.path.join(self.d.etats, 'etat_01.dqs'), b'E1')
        ecrire(os.path.join(self.t, 'dq4_pc', 'sauvegardes', 'data1.dat'), b'tres_vieux'); ecrire(os.path.join(self.t, 'dq4_pc', 'sauvegardes', 'data3.dat'), b'tres_vieux3')

    def test_les_journaux_sont_remontes_dans_sauvegardes(self):
        self.cas_de_sylfried(); fait = self.migrer()
        self.assertTrue(any('anciens dossiers ranges' in ph for ph in fait), fait)
        for nom in ('data1.dat', 'data5.dat', 'data9.dat'): self.assertEqual(contenu(self.sv, nom), b'portage_' + nom.encode(), nom)                  # le portage (ce que le jeu ecrivait) passe devant
        for nom in ('data2.dat', 'data3.dat', 'data4.dat'): self.assertEqual(contenu(self.sv, nom), b'portage_vieux_' + nom.encode(), nom)            # ... meme plus ancien : comme avant (aucun choix a la date)
        self.assertEqual(sorted(f for f in os.listdir(self.sv) if f.endswith('.dat')), sorted(NOMS))

    def test_la_copie_du_telephone_complete_ce_qui_manque(self):
        ecrire(os.path.join(self.d.ancien_portage, 'data1.dat'), b'portage1')
        for nom in NOMS: ecrire(os.path.join(self.d.mobile, '20261103_222423', nom), b'tel_' + nom.encode())
        ecrire(os.path.join(self.d.mobile, '20261007_190735', 'data3.dat'), b'tel_ancien3'); ecrire(os.path.join(self.d.mobile, '20261007_190735', 'data1.dat'), b'tel_ancien1')
        self.migrer()
        self.assertEqual(contenu(self.sv, 'data1.dat'), b'portage1'); self.assertEqual(contenu(self.sv, 'data3.dat'), b'tel_data3.dat')                     # la copie la plus recente, pas une plus ancienne

    def test_les_anciens_dossiers_sont_ranges_tels_quels_rien_n_est_perdu(self):
        self.cas_de_sylfried(); avant = set(tous_les_fichiers(self.sv)); self.migrer()
        rangement = [x for x in os.listdir(self.sv) if x.startswith('avant_rangement_')]; self.assertEqual(len(rangement), 1)
        for sous in ('portage', 'mobile'): self.assertFalse(os.path.exists(os.path.join(self.sv, sous)), sous)                                      # plus de portage\ ni de mobile\
        r = os.path.join(self.sv, rangement[0])
        self.assertEqual(contenu(r, 'portage', 'data2.dat'), b'portage_vieux_data2.dat'); self.assertEqual(contenu(r, 'mobile', '20261103_222423', 'manifest.json'), b'{"device": "SM S938B"}')
        self.assertEqual(contenu(r, 'mobile', '20261007_190735', 'data1.dat'), b'tel_ancien')
        apres = set(tous_les_fichiers(self.sv))
        for f in avant:                                                                                                                                # chaque fichier d'avant est la OU on l'a range, avec le meme contenu
            if f.startswith(('portage' + os.sep, 'mobile' + os.sep)): self.assertIn(os.path.join(rangement[0], f), apres, f)
            else: self.assertIn(f, apres, f)
        self.assertEqual(contenu(self.sv, 'etats', 'etat_01.dqs'), b'E1'); self.assertEqual(contenu(self.sv, 'avant_import_20261101_192625', 'data2.dat'), b'AV')    # etats et copies d'import : a leur place

    def test_une_seconde_reprise_ne_fait_rien(self):
        self.cas_de_sylfried(); self.migrer(); avant = tous_les_fichiers(self.t)
        self.assertEqual(self.migrer(), []); self.assertEqual(tous_les_fichiers(self.t), avant)

    def test_le_vieux_dossier_dq4_pc_ne_passe_pas_devant_les_fichiers_d_aujourd_hui(self):
        """Il reste chez lui un `dq4_pc\\sauvegardes` d'avant le premier rangement (copie, pas deplacement) : ses vieux data1 et data3 ne doivent pas remplacer ceux du portage."""
        self.cas_de_sylfried(); self.migrer()
        self.assertEqual(contenu(self.sv, 'data1.dat'), b'portage_data1.dat'); self.assertEqual(contenu(self.sv, 'data3.dat'), b'portage_vieux_data3.dat')
        self.assertEqual(contenu(self.t, 'dq4_pc', 'sauvegardes', 'data1.dat'), b'tres_vieux')                                                      # (et il n'est pas touche)

    def test_un_journal_deja_pose_dans_sauvegardes_n_est_pas_ecrase(self):
        """Il a deja copie les data du telephone dans `sauvegardes\\` : ils gagnent ; ceux de l'ancien portage ne sont pas perdus (ranges)."""
        ecrire(os.path.join(self.sv, 'data1.dat'), b'copie_du_telephone'); ecrire(os.path.join(self.d.ancien_portage, 'data1.dat'), b'ancien_portage'); ecrire(os.path.join(self.d.ancien_portage, 'data2.dat'), b'portage2')
        self.migrer()
        self.assertEqual(contenu(self.sv, 'data1.dat'), b'copie_du_telephone'); self.assertEqual(contenu(self.sv, 'data2.dat'), b'portage2')
        r = os.path.join(self.sv, [x for x in os.listdir(self.sv) if x.startswith('avant_rangement_')][0]); self.assertEqual(contenu(r, 'portage', 'data1.dat'), b'ancien_portage')

    def test_rien_a_ranger(self):
        ecrire(os.path.join(self.sv, 'data1.dat'), b'a'); self.assertEqual(self.migrer(), []); self.assertEqual(tous_les_fichiers(self.sv), ['data1.dat'])

    def test_un_dossier_vide_est_range_sans_rien_copier(self):
        os.makedirs(self.d.ancien_portage); self.migrer()
        self.assertFalse(os.path.exists(self.d.ancien_portage)); self.assertEqual(sorted(f for f in os.listdir(self.sv) if f.endswith('.dat')), [])

    def test_une_erreur_de_deplacement_laisse_tout_en_place(self):
        self.cas_de_sylfried()
        vrai = os.replace

        def refuse_les_dossiers(src, dst):                                    # Windows : un dossier dont un fichier est ouvert ne se deplace pas ; les copies de fichiers (tmp -> destination) passent
            if os.path.isdir(src): raise PermissionError('fichier ouvert')
            return vrai(src, dst)
        with mock.patch('dq4_pc.chemins.os.replace', side_effect=refuse_les_dossiers):
            fait = self.migrer()
        self.assertTrue(any('NON ranges' in ph and 'fichier ouvert' in ph for ph in fait), fait)
        self.assertTrue(os.path.isdir(self.d.ancien_portage) and os.path.isdir(self.d.mobile))                                                            # rien n'a bouge
        self.assertEqual(contenu(self.sv, 'data1.dat'), b'portage_data1.dat')                                                                           # (le jeu lit deja sauvegardes : copie faite avant le deplacement)
        fait = self.migrer()                                                                                                                           # puis la reprise suivante termine
        self.assertTrue(any('anciens dossiers ranges' in ph for ph in fait), fait); self.assertFalse(os.path.exists(self.d.ancien_portage))

    def test_un_fichier_qui_ne_peut_pas_etre_pose_arrete_le_rangement(self):
        """Un dossier nomme `data1.dat` occupe la place : le journal du portage n'a pas pu etre copie, donc l'ancien dossier ne bouge pas."""
        ecrire(os.path.join(self.d.ancien_portage, 'data1.dat'), b'portage1'); os.makedirs(os.path.join(self.sv, 'data1.dat'))
        fait = self.migrer()
        self.assertTrue(any('NON ranges' in ph and 'data1.dat' in ph for ph in fait), fait); self.assertTrue(os.path.isfile(os.path.join(self.d.ancien_portage, 'data1.dat')))

    def test_dq4_jeux_la_copie_du_telephone_n_est_pas_touchee(self):
        jeux = os.path.join(self.t, 'ailleurs', 'DQ4'); d = CH.Dossiers(self.t, env={'DQ4_JEUX': jeux})
        for nom in NOMS: ecrire(os.path.join(jeux, 'saves', '20261007_190735', nom), b'tel_' + nom.encode())
        ecrire(os.path.join(d.sauvegardes, 'portage', 'data1.dat'), b'p')
        self.assertEqual(CH.migrer(d, log=lambda *a: None), [])
        self.assertTrue(os.path.isfile(os.path.join(jeux, 'saves', '20261007_190735', 'data1.dat'))); self.assertTrue(os.path.isfile(os.path.join(d.sauvegardes, 'portage', 'data1.dat')))
        self.assertTrue(d.sauvegarde_mobile_recente().endswith('20261007_190735'))                                                                      # (le jeu la lit toujours en second)


class AvecLeMoteurEtLesZips(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.mkdtemp(prefix='un_dossier_zip_'); self.d = CH.Dossiers(self.t, env={}); self.avant = CH.DOSSIERS; CH.DOSSIERS = self.d

    def tearDown(self): CH.DOSSIERS = self.avant; shutil.rmtree(self.t, ignore_errors=True)

    def test_copier_les_fichiers_du_telephone_suffit(self):
        """Le geste voulu : les data1.dat... du telephone dans `sauvegardes\\`, rien d'autre ; le moteur les lit (dossier d'ecriture d'abord) et l'export les range a plat avec les etats."""
        for nom in NOMS: ecrire(os.path.join(self.d.sauvegardes, nom), b'tel_' + nom.encode())
        ecrire(os.path.join(self.d.etats, 'etat_01.dqs'), b'e' * 2000)
        self.assertEqual(sorted(S.fichiers_effectifs(self.d.portage, None)), sorted(NOMS))
        sortie = os.path.join(self.t, 'sortie.zip'); self.assertEqual(S.exporter(self.d.portage, None, sortie), (6, 1))
        with zipfile.ZipFile(sortie) as z: self.assertEqual(sorted(z.namelist()), sorted(NOMS + ('etats/etat_01.dqs',)))

    def test_le_contenu_du_dossier_est_celui_du_zip(self):
        """Ce que l'export met dans le .zip est ce que le dossier contient (a part les copies de securite) : le dossier se copie d'un PC a l'autre comme le .zip se decompresse."""
        for nom in NOMS: ecrire(os.path.join(self.d.sauvegardes, nom), b'j' + nom.encode())
        ecrire(os.path.join(self.d.etats, 'etat_02.dqs'), b'e' * 2000); ecrire(os.path.join(self.d.sauvegardes, 'avant_import_20261101_101010', 'data1.dat'), b'AV')
        sortie = os.path.join(self.t, 'sortie.zip'); S.exporter(self.d.portage, None, sortie)
        with zipfile.ZipFile(sortie) as z: dans_le_zip = sorted(z.namelist())
        dossier = sorted(f.replace(os.sep, '/') for f in tous_les_fichiers(self.d.sauvegardes) if not f.startswith('avant_'))
        self.assertEqual(dans_le_zip, dossier)


if __name__ == '__main__':
    unittest.main(verbosity=1)
