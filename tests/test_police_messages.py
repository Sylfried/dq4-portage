"""Test de la police des messages du jeu (dq4_pc/menus/police_messages.py) : celle que le moteur utilise pour dessiner les dialogues (et que l'historique reprend, #269).

    python3 tests/test_police_messages.py                                      (regles, avec une police synthetique : sans pyglet ni moteur)
    DQ_APK=<dossier des APK patches> DQ_SAVES=<dossier des sauvegardes> python3 tests/test_police_messages.py     (en plus : la vraie police, comparee au vrai moteur)

Sans moteur : lecture des glyphes (octets repetes / octets tels quels / fin), avance de la position d'ecriture (largeur du glyphe, glyphe a drapeau pose un pixel a gauche et avance de deux pixels de moins, espace du moteur et pas
de la police, tabulation, « ; » et « $ » non dessines, code absent -> glyphe du « @ »), pixels d'une ligne, coupure des lignes (`CTextAutoReturn::AutoReturn` : points de coupure, tiret, saut de ligne, mot plus long que la ligne),
extraction de la police dans le cache.
Avec le moteur reel (facultatif, ignore sinon) : les pixels de `SDrawCTRL::PutChar` dans le canevas du moteur sont ceux de `PoliceMessages.pixels` pour une phrase francaise, les lettres russes du patch (я, и) et les glyphes
a drapeau ; les lignes de `PoliceMessages.couper` sont celles d'`AutoReturn` sur des messages du jeu. Aucun caractere n'est ecrit « en dur » : tout vient du fichier de police (DQ5 et DQ6 : meme format).
"""
import os, struct, sys, tempfile, unittest, zipfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import _chemins          # (aide des tests : retrouver le code source dans les sous-dossiers de dq4_pc)
import numpy as np
from dq4_pc.menus.police_messages import PoliceMessages, extraire_police_messages, TAILLE_TABLE, DEBUT_TABLE, DEBUT_DONNEES, CODE_DEFAUT

H = 24


def codage(bitmap):
    """Donnees d'un glyphe (hauteur x largeur octets, a plat) en 'repete' (1xxxxxxx + octet) quand un octet se repete, sinon 'tels quels' (0xxxxxxx + octets), puis 0."""
    b = bytes(bitmap); out = bytearray(); i = 0
    while i < len(b):
        k = 1
        while i + k < len(b) and b[i + k] == b[i] and k < 127: k += 1
        if k >= 3: out += bytes([0x80 | k, b[i]]); i += k
        else:
            j = i + 1
            while j < len(b) and j - i < 127 and not (j + 2 < len(b) and b[j] == b[j + 1] == b[j + 2]): j += 1
            out += bytes([j - i]) + b[i:j]; i = j
    return bytes(out) + b'\0'


def police_synthetique(glyphes):
    """Fichier TNOF minimal : glyphes = {code: (largeur, drapeau, octet)} ; le glyphe est une colonne de rampe 1..255 (octet = valeur de base) pour reconnaitre chaque cellule."""
    table = np.zeros(TAILLE_TABLE, '<u4'); data = bytearray()
    for code, (w, drapeau, val) in glyphes.items():
        bm = bytes(((val + 7 * (r % 5) + 11 * (c % 3)) % 250) + 1 for r in range(H) for c in range(w))
        table[code] = ((w | (0x80 if drapeau else 0)) << 24) | len(data)
        data += codage(bm)
    head = bytearray(28); head[:4] = b'TNOF'; struct.pack_into('<H', head, 24, H)
    return bytes(head) + table.tobytes() + bytes(data)


GLYPHES = {ord('A'): (7, 0, 10), ord('B'): (9, 0, 40), ord('@'): (11, 0, 70), ord('V'): (10, 1, 100), ord('t'): (6, 1, 130), ord('-'): (4, 0, 160),
           ord(' '): (5, 0, 190), ord('я'): (8, 0, 220), ord('é'): (8, 0, 20), ord(','): (3, 0, 50), ord('x'): (6, 0, 80), ord('$'): (9, 0, 90), ord(';'): (9, 0, 95)}


def synth(**kw): return PoliceMessages(donnees=police_synthetique(GLYPHES), **kw)


class TestGlyphes(unittest.TestCase):
    def test_lecture_rle(self):
        p = synth()
        for code, (w, drapeau, val) in GLYPHES.items():
            d, largeur, bm = p.glyphe(code)
            self.assertEqual((d, largeur, bm.shape), (drapeau, w, (H, w)), chr(code))
            attendu = [((val + 7 * (r % 5) + 11 * (c % 3)) % 250) + 1 for r in range(H) for c in range(w)]
            self.assertEqual(list(bm.reshape(-1)), attendu, chr(code))

    def test_entete_et_signature(self):
        with self.assertRaises(ValueError): PoliceMessages(donnees=b'XXXX' + bytes(DEBUT_DONNEES))
        self.assertEqual(synth().hauteur, H)
        self.assertEqual(DEBUT_DONNEES, 28 + 4 * 65536)

    def test_code_absent_prend_l_arobase(self):
        p = synth()
        self.assertIn(ord('A'), p); self.assertNotIn(ord('z'), p); self.assertNotIn(0x4e2d, p)
        self.assertEqual(p.glyphe(ord('z'))[1], 11); self.assertTrue((p.glyphe(0x4e2d)[2] == p.glyphe(CODE_DEFAUT)[2]).all())
        self.assertEqual(p.largeur('zz'), 22)

    def test_aucun_caractere_en_dur(self):
        """Un caractere ajoute a la police (DQ5, DQ6 : autres lettres) s'affiche, sans rien changer dans le code."""
        g = dict(GLYPHES); g[0x0416] = (13, 0, 33)                       # « Ж »
        p = PoliceMessages(donnees=police_synthetique(g))
        self.assertEqual(p.largeur('Ж'), 13); self.assertEqual(p.largeur('ЖЖ'), 26)
        self.assertEqual(synth().largeur('Ж'), 11)                       # absent : le « @ »


class TestPlacement(unittest.TestCase):
    def test_avance_largeur_du_glyphe(self):
        p = synth(); self.assertEqual(p.largeur('AB'), 16); self.assertEqual(p.largeur('я'), 8); self.assertEqual(p.largeur(''), 0)

    def test_espace_du_moteur_pas_celui_de_la_police(self):
        p = synth(espace=6); self.assertEqual(p.glyphe(32)[1], 5); self.assertEqual(p.largeur('A A'), 7 + 6 + 7)
        self.assertEqual(synth(espace=4).largeur('A A'), 7 + 4 + 7)

    def test_tabulation_et_espace_large(self):
        p = synth(tabulation=15, espace_large=6); self.assertEqual(p.largeur('A\tA'), 7 + 15 + 7); self.assertEqual(p.largeur('A　A'), 7 + 6 + 7)

    def test_glyphe_a_drapeau(self):
        """Pose 1 pixel a gauche, avance de 2 de moins (crenage)."""
        p = synth(); cel, fin = p.plan('AV')
        self.assertEqual([x for x, _ in cel], [0, 7 - 1]); self.assertEqual(fin, 7 + 10 - 2); self.assertEqual(p.largeur('t'), 4)

    def test_retours_a_la_ligne_ne_font_rien(self):
        self.assertEqual(synth().largeur('A\nB\rA'), 7 + 9 + 7)

    def test_dollar_et_point_virgule(self):
        p = synth(langue=1); self.assertEqual(p.largeur('A$A'), 14); self.assertEqual(p.largeur('A;A'), 14)         # ni l'un ni l'autre n'est dessine (anglais)
        self.assertEqual(synth(langue=2).largeur('A;A'), 7 + 6 + 7)                                                   # « ; » est une espace pour la langue 2

    def test_ecart_entre_lettres(self):
        self.assertEqual(synth(ecart=1).largeur('AB'), 18)

    def test_pixels_une_ligne(self):
        """Le glyphe a drapeau remplace le dernier pixel du glyphe precedent (pas de melange), comme dans le canevas du moteur."""
        p = synth(); a = p.pixels('AV'); P = p.PAD; A = p.glyphe(ord('A'))[2]; V = p.glyphe(ord('V'))[2]
        self.assertEqual(a.shape, (H, 2 * P + 16))
        self.assertTrue((a[:, P:P + 6] == A[:, :6]).all()); self.assertTrue((a[:, P + 6:P + 16] == V).all())
        self.assertEqual(p.pixels('').shape, (H, 2 * P))


class TestCoupure(unittest.TestCase):
    def test_une_ligne_courte(self):
        self.assertEqual(synth().couper('AB AB'), ['AB AB'])

    def test_coupe_apres_la_derniere_espace(self):
        """« AAA AAA » fait 7 x 6 + 6 = 48 ; avec la 2e espace 54 ; la limite 60 est atteinte dans le 3e mot : retour apres la 2e espace."""
        self.assertEqual(synth().couper('AAA AAA AAA', limite=60), ['AAA AAA ', 'AAA'])
        self.assertEqual(synth().couper('AAA AAA AAA', limite=40), ['AAA ', 'AAA ', 'AAA'])

    def test_mot_plus_long_que_la_ligne(self):
        """Sans point de coupure le caractere qui depasse reste sur la ligne ; la coupure laisse une ligne vide a la fin quand le texte s'arrete juste apres (comme le moteur)."""
        self.assertEqual(synth().couper('AAAAAA', limite=20), ['AAA', 'AAA', ''])
        self.assertEqual(synth().couper('AAAAAAA', limite=20), ['AAA', 'AAA', 'A'])

    def test_saut_de_ligne_du_texte(self):
        self.assertEqual(synth().couper('AB\nAB'), ['AB', 'AB']); self.assertEqual(synth().couper('AB\r\nAB'), ['AB', 'AB'])
        self.assertEqual(synth().couper('AAA AAA AAA\nAAA', limite=60), ['AAA AAA ', 'AAA', 'AAA'])

    def test_saut_apres_une_coupure_automatique_avale(self):
        self.assertEqual(synth().couper('AAAAAAAAAAAA\nB', limite=7 * 12), ['AAAAAAAAAAAA', 'B'])         # la coupure tombe pile a la fin de la ligne : le saut qui suit est avale

    def test_tiret_point_de_coupure(self):
        p = synth()
        self.assertEqual(p.couper('AAA-AAA-AAA', limite=65), ['AAA-AAA-', 'AAA'])                       # coupure apres un tiret
        self.assertEqual(p.couper('AAA-AAA', limite=30), ['AAA-', 'AAA'])
        self.assertEqual(p.couper('AAA--AAA', limite=30), ['AAA--A', 'AA'])                             # « -- » n'est pas un point de coupure (anglais)

    def test_largeur_pour_la_coupure(self):
        p = synth(); self.assertEqual(p.largeur_coupure(';'), 0); self.assertEqual(p.largeur_coupure('$'), 9); self.assertEqual(p.largeur_coupure(' '), 6)
        self.assertEqual(p.largeur_coupure('V'), 8); self.assertEqual(synth(langue=2).largeur_coupure(';'), 6)

    def test_limite_par_defaut(self):
        self.assertEqual(PoliceMessages.LIMITE, 410)


class TestExtraction(unittest.TestCase):
    def test_extraire(self):
        with tempfile.TemporaryDirectory() as d:
            apk = os.path.join(d, 'apks'); os.makedirs(apk); cache = os.path.join(d, 'cache'); donnees = police_synthetique(GLYPHES)
            with zipfile.ZipFile(os.path.join(apk, 'split_UnityDataAssetPack.apk'), 'w') as z: z.writestr('assets/English.font', donnees)
            journal = []
            self.assertTrue(extraire_police_messages(apk, cache, journal.append))
            with open(os.path.join(cache, 'ui_messages.font'), 'rb') as f: self.assertEqual(f.read(), donnees)
            self.assertTrue(extraire_police_messages(os.path.join(d, 'absent'), cache, journal.append)); self.assertEqual(journal, [])        # deja la : rien a relire
            self.assertEqual(PoliceMessages(os.path.join(cache, 'ui_messages.font')).largeur('AB'), 16)

    def test_absente_ou_illisible(self):
        with tempfile.TemporaryDirectory() as d:
            journal = []; self.assertFalse(extraire_police_messages(os.path.join(d, 'rien'), os.path.join(d, 'c1'), journal.append)); self.assertEqual(len(journal), 1)
            apk = os.path.join(d, 'apks'); os.makedirs(apk)
            with zipfile.ZipFile(os.path.join(apk, 'split_UnityDataAssetPack.apk'), 'w') as z: z.writestr('assets/English.font', b'PAS UNE POLICE')
            self.assertFalse(extraire_police_messages(apk, os.path.join(d, 'c2'), journal.append)); self.assertFalse(os.path.exists(os.path.join(d, 'c2', 'ui_messages.font')))


# ---------------------------------------------------------------- vraie police et vrai moteur (facultatif)
APK, SAVES = os.environ.get('DQ_APK'), os.environ.get('DQ_SAVES')


@unittest.skipUnless(APK and SAVES, 'moteur reel : DQ_APK=<dossier des APK patches> DQ_SAVES=<dossier des sauvegardes>')
class TestVraiMoteur(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from dq4_pc.noyau import moteur as MO
        cls.tmp = tempfile.mkdtemp()
        assert extraire_police_messages(APK, cls.tmp, print), 'police introuvable dans le paquet de donnees'
        cls.pm = PoliceMessages(os.path.join(cls.tmp, 'ui_messages.font'))
        cls.mo = MO.Moteur(APK, SAVES, tempfile.mkdtemp(dir=cls.tmp)); cls.mo.charger_sauvegarde(1)
        for i in range(80):                                             # quelques images : le moteur pose ses parametres de texte quand un dialogue s'ouvre
            cls.mo.step(0, 0x10 if i % 9 == 5 else 0)
            cv = cls.mo.lire_canevas()
            if i > 30 and cv is not None and cv.max() > 100: break
        c = cls.mo.core; cls.c = c; cls.obj = cls.mo.obj_msg
        c.mem_w(cls.obj + 0x38, struct.pack('<3H', 6, 6, 15))           # espace, espace large, tabulation (valeurs du jeu)

    def test_la_police_a_les_lettres_du_patch(self):
        for ch in 'Je suis Ragnar éèêàçÉ,.!?' + 'яиЯ':
            self.assertIn(ord(ch), self.pm, ch)
        self.assertEqual(self.pm.hauteur, 24)

    def _moteur(self, texte, x=6, y=0):
        c, obj, mo = self.c, self.obj, self.mo
        tampon = struct.unpack('<Q', c.mem(obj + 0x10, 8))[0]
        c.mem_w(tampon, bytes(512 * 512))                               # canevas vide : chaque test part de zero
        c.mem_w(obj + 0x46, struct.pack('<H', x)); c.mem_w(obj + 0x48, struct.pack('<H', y))
        put = c.export('_ZN9SDrawCTRL7PutCharEt')
        for ch in texte: c.call(put, obj, ord(ch), label='putchar')
        cv = mo.lire_canevas(); fin = struct.unpack('<H', c.mem(obj + 0x46, 2))[0]
        return cv[y:y + 24].copy(), fin - x

    def _comparer(self, texte):
        x = 6; vu, avance = self._moteur(texte, x)
        a = self.pm.pixels(texte)                                       # la position d'ecriture est a la colonne PAD
        attendu = np.zeros_like(vu); w = min(a.shape[1], vu.shape[1] - (x - self.pm.PAD)); attendu[:, x - self.pm.PAD:x - self.pm.PAD + w] = a[:, :w]
        self.assertEqual(avance, self.pm.largeur(texte), texte)
        self.assertTrue((vu == attendu).all(), 'pixels differents pour %r : %d' % (texte, int((vu != attendu).sum())))

    def test_pixels_comme_le_moteur(self):
        for t in ('Quelle joie de vous revoir, Ragnar !', "J'espère que vous vous êtes bien reposé.", 'Pourquoи cеtte guеяяе, mon fиls ?', 'яиЯ', 'VWtvwy Vive la Yougoslavie', 'a;b c$d', 'Où ça ? Là-bas… »',
                  '\xa0Ça va ?\t.'):
            with self.subTest(t): self._comparer(t)

    def test_tous_les_glyphes_comme_le_moteur(self):
        """Chaque glyphe de la police (tous les codes que la table connait), par paquets : les pixels et l'avance sont ceux du moteur."""
        codes = [k for k in range(TAILLE_TABLE) if k in self.pm and k not in (0x09, 0x0a, 0x0d, 0x20, 0x24, 0x3b, 0x3000, 0x1b)]
        pas = 24
        for i in range(0, len(codes), pas):
            t = ''.join(chr(k) for k in codes[i:i + pas])
            if self.pm.largeur(t) > 500: continue
            with self.subTest(i=i): self._comparer(t)

    def _lignes_moteur(self, seg):
        """Lignes d'un texte telles que `CTextAutoReturn::AutoReturn` du moteur les coupe (lignes vides et espaces de fin ignorees : comme `couper_comme_le_jeu`)."""
        c = self.c
        if not hasattr(self, '_ar'):
            type(self)._ar = (c.export('_ZN15CTextAutoReturn10AutoReturnEPtPKh'), c.malloc(0x80), c.malloc(0x8000), c.malloc(0x4000)); c.mem_w(self._ar[1], bytes(0x80))
        ar, obj, sortie, entree = self._ar
        c.mem_w(entree, seg.encode('utf-8') + b'\0'); c.mem_w(sortie, bytes(0x400)); c.call(ar, obj, sortie, entree, label='AutoReturn')
        mots = struct.unpack('<2048H', c.mem(sortie, 0x1000)); fin = mots.index(0) if 0 in mots else len(mots)
        return [x.rstrip(' ') for x in ''.join(chr(u) for u in mots[:fin]).replace('\u328a', '').replace('\r', '').split('\n') if x]

    def _lignes_miennes(self, seg): return [x.rstrip(' ') for x in self.pm.couper(seg) if x]

    def test_coupure_comme_auto_return(self):
        """Des messages du jeu (un sur ~7 de chaque fichier, par page) : les lignes sont celles du moteur."""
        import re
        mo = self.mo
        z = zipfile.ZipFile(os.path.join(APK, 'split_UnityDataAssetPack.apk'))
        fichiers = sorted(int(re.search(r'b(\d{7})\.mpt', n).group(1)) for n in z.namelist() if re.search(r'assets/msg/en/b\d{7}\.mpt$', n))
        echantillon = []
        for f in fichiers:
            for r in range(0, 1000, 7):
                t = mo.capteur.modele(f + r)
                if t is not None: echantillon.append((f + r, t))
        self.assertGreater(len(echantillon), 200)
        verifies = 0
        for mid, t in echantillon[:: max(1, len(echantillon) // 400)]:
            for seg in t.split('\u3221'):
                seg = seg.rstrip('\n')
                if not seg.strip(): continue
                self.assertEqual(self._lignes_miennes(seg), self._lignes_moteur(seg), 'message %d : %r' % (mid, seg[:80]))
                verifies += 1
        self.assertGreater(verifies, 200)

    def test_coupure_symboles_comme_auto_return(self):
        """« $ » (largeur comptee pour la coupure, pas dessine), « ; » (largeur nulle), tirets, espaces larges, lettres russes, mot trop long : textes construits pour que la coupure tombe pres de ces caracteres."""
        base = ["Ragnar$ obtient ;l'herbe ;médicinale et un bâton de ;cyprès.", 'Pourquoи cеtte guеяяе ? Mon fиls, яeviens-moi vivaиt, sиnon je serai très triste !', 'Va-t-en, petit-fils-du-roi-qui-pars-là-bas--vite !',
                'A\u3000B C\u3000D E\u3000F G\u3000H I\u3000J K\u3000L M\u3000N O\u3000P Q\u3000R S\u3000T', 'x' * 120 + ' fin', 'Tsar$$ Stepan$ ;;; ' * 8]
        verifies = 0
        for t in base:
            for k in range(0, 24):
                seg = ('éé ' * (k % 6)) + t
                with self.subTest(seg=seg[:50]): self.assertEqual(self._lignes_miennes(seg), self._lignes_moteur(seg))
                verifies += 1
        self.assertGreater(verifies, 100)


if __name__ == '__main__':
    unittest.main(verbosity=2)
