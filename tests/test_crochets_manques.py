"""#217 (audit ENG-08) : les reglages / crochets que le moteur d'un AUTRE apk ne laisse pas installer ne sont plus silencieux : `Moteur.crochets_manques` (ligne de console + liste sans doublon), puis la fenetre
les note dans `erreurs_fenetre.log` et affiche un message (Jeu._signaler_crochets_manques). Sans moteur : faux moteur (memoire simulee). Avec l'APK du jeu (DQ_APK, DQ_SAVES) : le moteur d'origine n'en manque aucun.
    PYGLET_HEADLESS=1 python3 tests/test_crochets_manques.py"""
import os, shutil, struct, sys, tempfile, types, unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from dq4_pc.noyau import moteur as MO
APK = os.environ.get('DQ_APK', '/mnt/user-data/uploads/dq4-portage/jeux/DQ4/patched_apks')
SAVES = os.environ.get('DQ_SAVES', '/mnt/user-data/uploads/dq4-portage/jeux/DQ4/saves/20261007_190735')

BASE = 0x10000                                                     # adresse de la fonction simulee
ORIGINE = (0x11000120 | (0xc0 << 10), 0x11000120 | (0x1c0 << 10), 0x11000120 | (0x314 << 10))       # add w0, w9, #imm des trois constantes de drawSymbol (masque 0xffc003e0 = 0x11000120)


def faux_moteur(mots=ORIGINE, cmp_param=0x71001d1f):
    """Moteur sans emulateur : la memoire est un dictionnaire d'octets ; export() renvoie BASE ; LIB_BASE = 0 (cmp du bouton Parametres a CMP_PARAMETRES)."""
    mem = bytearray(0x200000)
    for dec, w in zip((0x44, 0x48, 0x4c), mots): mem[BASE + dec:BASE + dec + 4] = struct.pack('<I', w)
    mem[MO.Moteur.CMP_PARAMETRES:MO.Moteur.CMP_PARAMETRES + 4] = struct.pack('<I', cmp_param)
    def ecrire(a, d): mem[a:a + len(d)] = d
    core = types.SimpleNamespace(LIB_BASE=0, export=lambda n: BASE, mem=lambda a, n: bytes(mem[a:a + n]), mem_w=ecrire)
    m = MO.Moteur.__new__(MO.Moteur); m.core = core; m.crochets_manques = []; m.mem = mem
    return m


def mot(m, a): return struct.unpack('<I', bytes(m.mem[a:a + 4]))[0]


class SansMoteur(unittest.TestCase):
    def test_manque_sans_doublon(self):
        m = faux_moteur(); m._manque('a'); m._manque('b'); m._manque('a')
        self.assertEqual(m.crochets_manques, ['a', 'b'])

    def test_fenetre_des_lieux_normale(self):
        m = faux_moteur(); m._elargir_symboles()
        self.assertEqual(m.crochets_manques, [])
        for dec in (0x44, 0x48, 0x4c): self.assertEqual((mot(m, BASE + dec) >> 10) & 0xfff, 1600)
        m._elargir_symboles(); self.assertEqual(m.crochets_manques, [])               # deja elargie (apres le chargement d'un etat) : ni erreur ni message

    def test_fenetre_des_lieux_autre_version(self):
        autre = (ORIGINE[0], ORIGINE[1], 0x11000120 | (0x555 << 10))
        m = faux_moteur(autre); m._elargir_symboles()
        self.assertEqual(len(m.crochets_manques), 1); self.assertIn('fenetre des lieux', m.crochets_manques[0])
        self.assertEqual(mot(m, BASE + 0x44), ORIGINE[0])                             # rien n'a ete touche
        m._elargir_symboles(); self.assertEqual(len(m.crochets_manques), 1)           # pas de doublon

    def test_bouton_parametres(self):
        m = faux_moteur(); m.patcher_parametres()
        self.assertEqual(m.crochets_manques, []); self.assertEqual(mot(m, MO.Moteur.CMP_PARAMETRES), 0x713ffd1f)
        m.patcher_parametres(); self.assertEqual(m.crochets_manques, [])               # deja patche
        m = faux_moteur(cmp_param=0xd503201f); m.patcher_parametres()                  # autre version : nop au lieu de la comparaison
        self.assertEqual(len(m.crochets_manques), 1); self.assertIn('Paramètres', m.crochets_manques[0])
        self.assertEqual(mot(m, MO.Moteur.CMP_PARAMETRES), 0xd503201f)

    def test_installateurs_signalent_leur_echec(self):
        """Un moteur dont les fonctions sont introuvables : chaque installateur le dit au lieu de se taire."""
        def introuvable(n): raise KeyError(n)
        for nom in ('_crochets_texte', '_crochets_fondu', '_crochets_niveau', '_crochets_rencontres', '_crochets_horloge_jour', '_crochets_temps_de_jeu', '_crochets_magie', '_detourner_parametres', '_elargir_symboles'):
            m = faux_moteur(); m.core.export = introuvable
            getattr(m, nom)()
            self.assertTrue(m.crochets_manques, nom + ' : echec silencieux')


class Fenetre(unittest.TestCase):
    def setUp(self):
        try: from dq4_pc.fenetre import jeu as F
        except Exception as ex: raise unittest.SkipTest('fenetre non importable ici (%r)' % (ex,))
        self.F = F; d = tempfile.mkdtemp(); self.addCleanup(shutil.rmtree, d, True)
        self.journal = os.environ['DQ_JOURNAL_FENETRE'] = os.path.join(d, 'journaux', 'erreurs_fenetre.log')
        self.addCleanup(os.environ.pop, 'DQ_JOURNAL_FENETRE', None)

    def lire(self):
        with open(self.journal, encoding='utf-8') as f: return f.read()

    def test_signalement_une_fois_puis_les_nouveaux(self):
        j = types.SimpleNamespace(_crochets_signales=0)                                  # (sans `toast` : depuis #267 aucun message a l'ecran, seulement le journal)
        mo = types.SimpleNamespace(crochets_manques=['vitesse du texte non installee', 'rencontres : CountDown::exec inattendu'])
        self.F.Jeu._signaler_crochets_manques(j, mo)
        self.assertEqual(j._crochets_signales, 2)
        txt = self.lire()
        self.assertIn('vitesse du texte', txt); self.assertIn('CountDown', txt); self.assertEqual(txt.count('\n'), 2)
        mo.crochets_manques.append('sorts sans effet : menu Magie inattendu')            # trouve apres le chargement d'un etat
        self.F.Jeu._signaler_crochets_manques(j, mo)
        self.assertEqual(j._crochets_signales, 3)
        txt = self.lire(); self.assertEqual(txt.count('\n'), 3); self.assertIn('menu Magie', txt)


@unittest.skipUnless(os.path.exists(os.path.join(APK, 'split_UnityDataAssetPack.apk')) and os.path.isdir(SAVES), "pas d'APK du jeu")
class MoteurReel(unittest.TestCase):
    def test_le_moteur_d_origine_n_en_manque_aucun(self):
        mo = MO.Moteur(APK, SAVES, tempfile.mkdtemp(prefix='sv_crochets_'))
        self.assertEqual(mo.crochets_manques, [])
        self.assertTrue(mo.capteur.actif); self.assertTrue(mo.capteur_combat.actif)
        mo.reappliquer_correctifs(); self.assertEqual(mo.crochets_manques, [])           # chargement d'un etat : toujours rien


if __name__ == '__main__': unittest.main(verbosity=1)
