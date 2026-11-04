"""Test de la capture des resultats de combat (dq4_pc/historique_combat.py) : ennemis vaincus, or, experience.

Trois niveaux :
- calcul pur (Suivi, noms des plaques, fabriquer_combat) : aucun moteur ;
- colle (CapteurCombat) sur un FAUX moteur (memoire et emulateur simules : les crochets sont declenches a la main) : debut / morts / victoire / fin, ruptures, abandons, erreurs ;
- moteur REEL facultatif : DQ_APK=<dossier des APK patches> DQ_SAVES=<dossier des sauvegardes> (la sauvegarde 1 : Ragnar et Doc dans une ville). Les combats sont forces dans un moteur jetable (la composition de
  la rencontre est ecrite dans Encount quand BattleRoot::setupMonster va la lire ; Global::startBattle lance le combat) ; chaque dict est compare au TEXTE du jeu (« reçoit N points d'expérience »,
  « N pièces d'or ») et aux compteurs du groupe dans la memoire (or avant / apres, experience de chaque membre avant / apres).

    python3 outils/test_historique_combat.py
    DQ_APK=... DQ_SAVES=... python3 outils/test_historique_combat.py        (une minute environ)
"""
import os, re, struct, sys, tempfile, unittest

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ICI, '..'))
from dq4_pc.combat import historique_combat as HC


# ---------------------------------------------------------------------------------------------------------------------------------- calcul pur
class Plaques(unittest.TestCase):
    def test_nom_de_plaque(self):
        self.assertEqual(HC.nom_de_plaque('Rat volant'), 'Rat volant')
        self.assertEqual(HC.nom_de_plaque('Gluant\n\n\t×3'), 'Gluant')
        self.assertEqual(HC.nom_de_plaque('  Chauve-sourat \r\n'), 'Chauve-sourat')
        for v in ('', '\n\t', None, 3, b'x'): self.assertIsNone(HC.nom_de_plaque(v), repr(v))

    def test_nom_sur_deux_lignes(self):
        """Les noms longs sont coupes sur deux lignes par le jeu (« ; » et « $ » des textes) : le nom complet est rendu, le nombre de monstres (ligne commencant par une tabulation) retire."""
        for brut, nom in (('Armure \n\nerrante', 'Armure errante'), ('Gluant de \n\nmercure\n\n\t×2', 'Gluant de mercure'), ('Scara-\n\nsomniaque', 'Scara-somniaque'),
                          ('Typhon-\n\nphonphon\n\n\t×3', 'Typhon-phonphon'), ("Rejeton de \n\nl'enfer", "Rejeton de l'enfer"), ('Gluant\n\n×3', 'Gluant'), ('Gluant\n\n\t×3\n\n', 'Gluant')):
            self.assertEqual(HC.nom_de_plaque(brut), nom, repr(brut))

    def test_noms_dans_l_ordre_des_groupes(self):
        groupes = [(0, 3), (0, 3), (1, 20), (2, 0), (2, 0), (2, 0), (3, 5)]
        self.assertEqual(HC.noms_des_groupes(groupes, ['Londuleux\n\n\t×2', 'Rat volant', 'Gluant\n\n\t×3', 'Chauve-sourat']), {3: 'Londuleux', 20: 'Rat volant', 0: 'Gluant', 5: 'Chauve-sourat'})
        self.assertEqual(HC.noms_des_groupes([(1, 7), (4, 9)], ['A', 'B']), {7: 'A', 9: 'B'})                       # (les numeros de groupe ne sont pas forcement 0, 1, 2...)

    def test_pas_de_correspondance_pas_de_nom(self):
        self.assertEqual(HC.noms_des_groupes([(0, 3), (1, 20)], ['Londuleux']), {})                                  # moins de plaques que de groupes
        self.assertEqual(HC.noms_des_groupes([(0, 3)], ['Londuleux', 'Rat volant']), {})                              # plus de plaques que de groupes
        self.assertEqual(HC.noms_des_groupes([(0, 3), (1, 20)], ['Londuleux', None]), {})                             # une plaque sans nom
        self.assertEqual(HC.noms_des_groupes([], []), {})


class SuiviPur(unittest.TestCase):
    def test_un_monstre_par_emplacement_occupe(self):
        s = HC.Suivi(); s.voir([(0, 3), (1, 3), (2, 20)]); s.voir([(0, 3), (1, 3), (2, 20)])
        self.assertEqual([m['num'] for m in s.monstres], [3, 3, 20])                                                  # revu a chaque image : pas recompte
        self.assertEqual(s.nombre_presents(), 3)

    def test_ordre_d_apparition_et_regroupement(self):
        s = HC.Suivi(); s.nommer({3: 'Londuleux', 20: 'Rat volant'}); s.voir([(0, 20), (1, 3), (2, 20)]); s.mort(1, 3); s.mort(0, 20)
        self.assertEqual(s.ennemis(), [{'nom': 'Rat volant', 'total': 2, 'vaincus': 1, 'fuis': 0, 'disparus': 0}, {'nom': 'Londuleux', 'total': 1, 'vaincus': 1, 'fuis': 0, 'disparus': 0}])

    def test_emplacement_libere_puis_reoccupe_est_un_renfort(self):
        s = HC.Suivi(); s.nommer({0: 'Gluant', 9: 'Roi des gluants'}); s.voir([(0, 0), (1, 0)]); s.mort(0, 0)
        s.voir([(0, 0), (1, 0)])                                                                                      # le monstre vaincu reste dans son emplacement jusqu'au nettoyage
        s.voir([(1, 0)])                                                                                              # nettoye
        s.voir([(0, 9), (1, 0)])                                                                                      # un renfort arrive dans l'emplacement libre
        self.assertEqual(s.ennemis(), [{'nom': 'Gluant', 'total': 2, 'vaincus': 1, 'fuis': 0, 'disparus': 0}, {'nom': 'Roi des gluants', 'total': 1, 'vaincus': 0, 'fuis': 0, 'disparus': 0}])

    def test_changement_de_numero_dans_un_emplacement(self):
        s = HC.Suivi(); s.voir([(0, 0)]); s.voir([(0, 5)])                                                            # transformation / remplacement entre deux releves : nouveau monstre
        self.assertEqual([m['num'] for m in s.monstres], [0, 5])

    def test_mort_d_un_monstre_jamais_vu(self):
        s = HC.Suivi(); s.mort(4, 7)
        self.assertEqual(s.ennemis(), [{'nom': HC.NOM_INCONNU, 'total': 1, 'vaincus': 1, 'fuis': 0, 'disparus': 0}]); self.assertEqual(s.morts, 1)

    def test_plusieurs_morts_a_la_meme_image(self):
        s = HC.Suivi(); s.voir([(0, 0), (1, 0), (2, 0)]); s.mort(0, 0); s.mort(1, 0); s.mort(2, 0)
        self.assertEqual(s.ennemis(), [{'nom': HC.NOM_INCONNU, 'total': 3, 'vaincus': 3, 'fuis': 0, 'disparus': 0}]); self.assertEqual(s.issue(), 'victoire')

    def test_noms_inconnus_numeros_distincts(self):
        s = HC.Suivi(); s.voir([(0, 1), (1, 2)])
        self.assertEqual([e['nom'] for e in s.ennemis()], [HC.NOM_INCONNU, HC.NOM_INCONNU])                          # deux especes sans nom : deux entrees, jamais fondues
        s.nommer({1: 'A', 2: 'A'}); self.assertEqual(s.ennemis(), [{'nom': 'A', 'total': 2, 'vaincus': 0, 'fuis': 0, 'disparus': 0}])           # meme nom = meme espece pour le joueur

    def test_un_nom_deja_connu_n_est_pas_change(self):
        s = HC.Suivi(); s.nommer({1: 'Gluant'}); s.nommer({1: 'Autre'}); self.assertEqual(s.noms[1], 'Gluant')

    def test_compteurs_plus_grand_releve(self):
        s = HC.Suivi(); s.compteurs(3, 7); s.compteurs(6, 13); s.compteurs(0, 0); s.compteurs(5, 10)
        self.assertEqual((s.xp, s.or_), (6, 13))

    def test_issues(self):
        s = HC.Suivi(); s.voir([(0, 1), (1, 1)]); s.mort(0, 1)
        self.assertEqual(s.issue(), 'fuite')                                                                          # un monstre vaincu sur deux, pas de routine de victoire : parti
        s.tentatives_fuite = 3; self.assertEqual(s.issue(), 'fuite')
        self.assertEqual(s.issue(defaite=True), 'defaite')
        s.victoire = True; self.assertEqual(s.issue(defaite=True), 'victoire')                                         # la routine de victoire l'emporte sur un drapeau de defaite resté d'un combat precedent
        s2 = HC.Suivi(); s2.voir([(0, 1)]); s2.mort(0, 1); self.assertEqual(s2.issue(), 'victoire')                    # tous vaincus, meme sans la routine
        self.assertEqual(HC.Suivi().issue(), 'fuite')                                                                  # rien vu, rien vaincu : le groupe est parti

    def test_or_et_experience_seulement_pour_une_victoire(self):
        for defaite, gagne in ((False, True), (True, False)):
            s = HC.Suivi(); s.voir([(0, 1), (1, 1)]); s.mort(0, 1); s.compteurs(5, 9)
            if gagne: s.mort(1, 1)
            d = HC.fabriquer_combat(s, 1234, defaite=defaite)
            self.assertEqual((d['or'], d['xp']), (9, 5) if gagne else (0, 0)); self.assertEqual(d['issue'], 'victoire' if gagne else 'defaite')
        s = HC.Suivi(); s.voir([(0, 1), (1, 1)]); s.mort(0, 1); s.compteurs(5, 9); d = HC.fabriquer_combat(s, 1)
        self.assertEqual((d['issue'], d['or'], d['xp']), ('fuite', 0, 0))                                              # fuite apres une mort : ni or ni experience (le moteur ne les verse pas)

    def test_forme_du_dict(self):
        s = HC.Suivi(); s.nommer({0: 'Gluant'}); s.voir([(0, 0)]); s.mort(0, 0); s.compteurs(2, 3)
        d = HC.fabriquer_combat(s, 12345)
        self.assertEqual(d, {'t': 12345, 'ennemis': [{'nom': 'Gluant', 'total': 1, 'vaincus': 1, 'fuis': 0, 'disparus': 0}], 'or': 3, 'xp': 2, 'issue': 'victoire', 'objets': []})
        self.assertEqual(sorted(d), ['ennemis', 'issue', 'objets', 'or', 't', 'xp']); self.assertIn(d['issue'], HC.ISSUES)
        for e in d['ennemis']: self.assertEqual(sorted(e), ['disparus', 'fuis', 'nom', 'total', 'vaincus'])
        self.assertTrue(all(type(v) is int for v in (d['t'], d['or'], d['xp'])))

    def test_monstres_enfuis_et_disparus(self):
        """#141 : chaque monstre a UN sort (vaincu, enfui ou disparu) ; ce qui n'a aucun sort est encore la a la fin."""
        s = HC.Suivi(); s.nommer({0: 'Gluant', 5: 'Golem'}); s.voir([(0, 0), (1, 0), (2, 0), (3, 5)]); s.mort(0, 0); s.enfui(1, 0); s.disparu(2, 0)
        self.assertEqual(s.ennemis(), [{'nom': 'Gluant', 'total': 3, 'vaincus': 1, 'fuis': 1, 'disparus': 1}, {'nom': 'Golem', 'total': 1, 'vaincus': 0, 'fuis': 0, 'disparus': 0}])
        self.assertEqual(s.morts, 1)                                                                                  # (seuls les morts comptent comme « morts » : ni une fuite ni une disparition)

    def test_un_monstre_enfui_n_est_pas_une_victoire(self):
        s = HC.Suivi(); s.voir([(0, 0), (1, 0)]); s.mort(0, 0); s.enfui(1, 0)
        self.assertEqual(s.issue(), 'victoire')                                                                       # (plus aucun monstre : tous vaincus ou partis, au moins un vaincu)
        s = HC.Suivi(); s.voir([(0, 0), (1, 0)]); s.mort(0, 0)
        self.assertEqual(s.issue(), 'fuite')                                                                          # un monstre reste : le groupe est parti
        s.victoire = True; self.assertEqual(s.issue(), 'victoire')                                                    # (la routine de victoire du jeu a le dernier mot)

    def test_sort_d_un_monstre_jamais_vu_ou_deja_decide(self):
        s = HC.Suivi(); s.enfui(4, 7); s.disparu(5, 7)
        self.assertEqual(s.ennemis(), [{'nom': HC.NOM_INCONNU, 'total': 2, 'vaincus': 0, 'fuis': 1, 'disparus': 1}])
        s = HC.Suivi(); s.voir([(0, 3)]); s.enfui(0, 3); s.enfui(0, 3)                                               # meme emplacement, sort deja note : un autre monstre
        self.assertEqual(s.ennemis(), [{'nom': HC.NOM_INCONNU, 'total': 2, 'vaincus': 0, 'fuis': 2, 'disparus': 0}])

    def test_objets_gagnes(self):
        s = HC.Suivi(); s.nommer({0: 'Gluant'}); s.voir([(0, 0)]); s.mort(0, 0); s.compteurs(2, 3)
        s.objet(12, 'herbe médicinale'); s.objet(40, 'pierre de vie')
        d = HC.fabriquer_combat(s, 1)
        self.assertEqual(d['objets'], [{'nom': 'herbe médicinale'}, {'nom': 'pierre de vie'}])
        s2 = HC.Suivi(); s2.voir([(0, 0), (1, 0)]); s2.mort(0, 0); s2.objet(12, 'x')
        self.assertEqual(HC.fabriquer_combat(s2, 1)['objets'], [])                                                    # pas de victoire : pas d'objets rapportes


# ---------------------------------------------------------------------------------------------------------------------------------- colle sur un faux moteur
LIB = 0x10000000
A_PARTY, A_MONSTER, A_GAME, A_RESULT = 0x1000, 0x2000, 0x1f000, 0x1e000
NOMS_FONCTIONS = {'_ZN6status15BasePartyStatus12getBattleExpEv': 0x30000, '_ZN6status15BasePartyStatus13getBattleGoldEv': 0x30010, '_ZN6status13MonsterStatus8isEnableEv': 0x30020,
                  '_ZN6status11PartyStatus11startBattleEv': 0x30100, '_ZN19BattleActorManager216execMonsterDeathEi': 0x30110, '_ZN23BattleExecDefeatMonster10initializeEv': 0x30120,
                  '_ZN16BattleExecEscape5setupEv': 0x30130, '_ZN6Global9endBattleEb': 0x30140,
                  HC.SYM_CONTROLE_MORTS: 0x30200, HC.SYM_OBJET_GAGNE: 0x30300, HC.SYM_NOM_OBJET: 0x30400}
A_TACHE = 0x31000                                                                                                    # la tache BattleExecVictory32 : le numero de l'objet a +0xc
INTERNES = {evt: (NOMS_FONCTIONS[nom] + off, mot) for evt, nom, off, mot in HC.CROCHETS_INTERNES}                  # evenement -> (adresse du crochet, instruction attendue)
NOMS_OBJETS = {12: 'herbe ;médicinale', 40: 'pierre de vie', 7: '<ERR 0x04000000.7>'}                                # ce que TextAPI::extractText repond
NOMS_MONSTRES = {0: 'gluant', 3: 'londuleux', 34: 'armure ;errante', 74: 'scara$somniaque', 5: 'chauve-sourat'}


def ldr_w(decalage, rt=0): return 0xb9400000 | ((decalage // 4) << 10) | rt                                        # ldr wRt, [x0, #decalage]


class FauxUC:
    def __init__(self): self.crochets = {}; self.regs = {}
    def hook_add(self, typ, cb, ud, debut, fin): self.crochets.setdefault(debut, []).append(cb)
    def reg_read(self, r): return self.regs.get(r, 0)
    def ctl_flush_tb(self): pass


class FauxCore:
    XREG = list(range(100, 131))
    def __init__(self, mauvaise_version=False, mot_interne_faux=None):
        self.ram = bytearray(0x40000); self.uc = FauxUC(); self.lectures = 0; self.appels = []
        for nom, a in NOMS_FONCTIONS.items(): self.ram[a:a + 4] = struct.pack('<I', 0xd65f03c0)
        for evt, (a, mot) in INTERNES.items(): self.ram[a:a + 4] = struct.pack('<I', mot ^ 1 if evt == mot_interne_faux else mot)
        off = {'_ZN6status15BasePartyStatus12getBattleExpEv': HC.OFF_XP, '_ZN6status15BasePartyStatus13getBattleGoldEv': HC.OFF_OR, '_ZN6status13MonsterStatus8isEnableEv': HC.OFF_NUMERO}
        for nom, o in off.items(): self.ram[NOMS_FONCTIONS[nom]:NOMS_FONCTIONS[nom] + 4] = struct.pack('<I', ldr_w(o + (4 if mauvaise_version else 0)))
        self.symboles = dict(NOMS_FONCTIONS); self.symboles.update({'_ZN6status7g_PartyE': A_PARTY, '_ZN6status9g_MonsterE': A_MONSTER, '_ZN6status6g_GameE': A_GAME, '_ZN6status14g_BattleResultE': A_RESULT})
        for e in range(HC.NB_EMPLACEMENTS): self.vider(e)
    def export(self, nom): return self.symboles.get(nom)
    def mem(self, a, n): self.lectures += 1; return bytes(self.ram[a:a + n])
    def ecrire(self, a, fmt, *v): self.ram[a:a + struct.calcsize(fmt)] = struct.pack(fmt, *v)
    def poser(self, e, num, groupe=0): self.ecrire(A_MONSTER + HC.DEBUT_MONSTRES + e * HC.PAS_MONSTRE + HC.OFF_NUMERO, '<2I', num, groupe)
    def vider(self, e): self.poser(e, 0xffffffff, 0)
    def declencher(self, nom, *args):
        for i, v in enumerate(args): self.uc.regs[self.XREG[i + 1]] = v
        for cb in self.uc.crochets[DECLENCHEURS[nom]]: cb(self.uc, 0, 4, None)
    def declencher_interne(self, evt, **regs):
        """Crochet au milieu d'une fonction du moteur : regs = {'x20': valeur, 'x0': valeur}."""
        for r, v in regs.items(): self.uc.regs[self.XREG[int(r[1:])]] = v
        for cb in self.uc.crochets[INTERNES[evt][0]]: cb(self.uc, 0, 4, None)
    def enfui(self, i): self.declencher_interne('monstre_enfui', x20=i)
    def disparu(self, i): self.declencher_interne('monstre_disparu', x20=i)
    def objet(self, numero, rangement=0):
        """rangement : ce que giveItem a renvoye (indice du membre, ou -1 : dans le sac)."""
        self.ecrire(A_TACHE + HC.OFF_OBJET_TACHE, '<I', numero); self.declencher_interne('objet', x20=A_TACHE, x0=rangement & 0xffffffff)
    # -- l'appel d'une fonction du moteur (HC.CapteurCombat._nom_objet : TextAPI::extractText)
    def malloc(self, n): return 0x3f000
    def mem_w(self, a, b): self.ram[a:a + len(b)] = b
    def read_cstr(self, a, limit=1 << 20):
        fin = self.ram.index(0, a); return bytes(self.ram[a:fin])
    def call(self, f, *args, label=''):
        self.appels.append((f, args)); buf, arg = args; num = arg & 0xffffff; assert f == NOMS_FONCTIONS[HC.SYM_NOM_OBJET]
        if arg & 0xf000000 == HC.GENRE_MONSTRE: nom = NOMS_MONSTRES.get(num, '<ERR 0x06000000.%d>' % num)
        else: assert arg & 0xf000000 == HC.GENRE_OBJET; nom = NOMS_OBJETS.get(num, '<ERR 0x04000000.%d>' % num)
        self.mem_w(buf, nom.encode('utf-8') + b'\0'); return buf


DECLENCHEURS = {'debut': 0x30100, 'mort': 0x30110, 'victoire': 0x30120, 'fuite': 0x30130, 'fin': 0x30140}


class FauxEtat:
    def __init__(self): self.partie = 0xc


class FauxUI:
    def __init__(self): self.f = {}


class FauxMoteur:
    def __init__(self, mauvaise_version=False, mot_interne_faux=None):
        self.core = FauxCore(mauvaise_version, mot_interne_faux); self.etat = FauxEtat(); self.images = 100; self.ui = FauxUI()
    def pas(self, capteur, n=1):
        sorties = []
        for _ in range(n): self.images += 1; sorties.extend(capteur.maj(self))
        return sorties
    def plaques(self, noms, port=15, dispo=None):
        """Comme Interface.appliquer : de nouveaux dicts a chaque rafraichissement."""
        self.ui.f[port] = {'type': 31, 'dispo': len(noms) if dispo is None else dispo, 'plaq': {i: {'code': 2, 'nom': n, 'prm': [0, 0]} for i, n in enumerate(noms)}}


def combat_simple(m, c, noms=('Rat volant', 'Londuleux'), nums=(20, 3)):
    """Debut, deux monstres, plaques, deux morts, victoire, fin ; -> les dicts rendus."""
    m.etat.partie = HC.PARTIE_COMBAT; m.core.declencher('debut'); m.core.poser(0, nums[0], 0); m.core.poser(1, nums[1], 1)
    sorties = m.pas(c, 3); m.plaques(list(noms)); sorties += m.pas(c, 3)
    m.core.declencher('mort', 0); m.core.declencher('mort', 1)
    m.core.ecrire(A_PARTY + HC.OFF_XP, '<2I', 6, 13); sorties += m.pas(c, 2)
    m.core.declencher('victoire'); m.core.ecrire(A_PARTY + HC.OFF_XP, '<2I', 6, 13); sorties += m.pas(c, 2)
    m.core.ecrire(A_PARTY + HC.OFF_XP, '<2I', 0, 0); m.core.ecrire(A_GAME + 4, '<I', 5555)
    m.core.declencher('fin', 0); sorties += m.pas(c, 1)
    return sorties


class Colle(unittest.TestCase):
    def setUp(self): self.m = FauxMoteur(); self.c = HC.CapteurCombat(self.m)

    def test_crochets_installes(self):
        self.assertTrue(self.c.actif)
        self.assertEqual(sorted(self.m.core.uc.crochets), sorted([NOMS_FONCTIONS[n] for _e, n in HC.CROCHETS] + [a for a, _m in INTERNES.values()]))

    def test_crochet_interne_inattendu_seul_cet_evenement_est_perdu(self):
        """Une instruction differente a l'endroit du crochet (autre moteur) : pas de crochet au hasard ; le reste de la capture fonctionne."""
        m = FauxMoteur(mot_interne_faux='monstre_enfui'); c = HC.CapteurCombat(m)
        self.assertTrue(c.actif); self.assertNotIn(INTERNES['monstre_enfui'][0], m.core.uc.crochets); self.assertIn(INTERNES['monstre_disparu'][0], m.core.uc.crochets)
        self.assertEqual(len(combat_simple(m, c)), 1)

    def scenario_complet(self, objets=((12, 0), (40, -1)), enfui=1, disparu=2, victoire=True):
        """3 Gluants et 1 Golem : le 1er Gluant meurt, un autre s'enfuit, le dernier disparait, le Golem meurt ; puis victoire (or 13, experience 6), les objets, la fin."""
        m, c = self.m, self.c; m.etat.partie = HC.PARTIE_COMBAT; m.core.declencher('debut')
        for e, (num, grp) in enumerate(((0, 0), (0, 0), (0, 0), (5, 1))): m.core.poser(e, num, grp)
        sorties = m.pas(c, 3); m.plaques(['Gluant\n\n\t×3', 'Golem']); sorties += m.pas(c, 3)
        m.core.declencher('mort', 0); sorties += m.pas(c, 1)
        if enfui is not None: m.core.enfui(enfui)
        if disparu is not None: m.core.disparu(disparu)
        sorties += m.pas(c, 1); m.core.declencher('mort', 3); m.core.ecrire(A_PARTY + HC.OFF_XP, '<2I', 6, 13); sorties += m.pas(c, 2)
        if victoire: m.core.declencher('victoire')
        for numero, rangement in objets: m.core.objet(numero, rangement)
        sorties += m.pas(c, 2); m.core.ecrire(A_PARTY + HC.OFF_XP, '<2I', 0, 0); m.core.ecrire(A_GAME + 4, '<I', 7777)
        m.core.declencher('fin', 0); return sorties + m.pas(c, 1)

    def test_monstres_enfuis_disparus_et_objets(self):
        """#141 : qui est mort, enfui ou disparu (par espece), l'or et l'experience, les objets (le nom est demande au moteur, le « ; » est retire ; qu'ils aillent a un membre ou dans le sac)."""
        sorties = self.scenario_complet(); self.assertEqual(len(sorties), 1); d = sorties[0]
        self.assertEqual(d['ennemis'], [{'nom': 'Gluant', 'total': 3, 'vaincus': 1, 'fuis': 1, 'disparus': 1}, {'nom': 'Golem', 'total': 1, 'vaincus': 1, 'fuis': 0, 'disparus': 0}])
        self.assertEqual((d['issue'], d['or'], d['xp'], d['t']), ('victoire', 13, 6, 7777))
        self.assertEqual(d['objets'], [{'nom': 'herbe médicinale'}, {'nom': 'pierre de vie'}])

    def test_nom_d_objet_demande_une_seule_fois_et_nom_de_secours(self):
        self.scenario_complet(objets=((12, 0), (12, 1), (7, -1), (99, 0)))
        self.assertEqual(len(self.m.core.appels), 3)                                                                   # 12, 7 et 99 : un appel par objet different (le nom est garde)

    def test_objets_et_noms_de_secours_dans_le_dict(self):
        d = self.scenario_complet(objets=((7, 0), (99, -1)))[0]
        self.assertEqual([o['nom'] for o in d['objets']], ['Objet n°7', 'Objet n°99'])                                 # (« <ERR ... > » n'est jamais montre)

    def test_victoire_sans_objet(self):
        d = self.scenario_complet(objets=(), victoire=True)[0]; self.assertEqual(d['objets'], [])

    def test_nom_demande_au_moteur_sans_plaque(self):
        """Attaque surprise (pas de plaque) : le nom vient du moteur par le numero du monstre, avec une majuscule ; sans reponse du moteur : « Monstre »."""
        m, c = self.m, self.c; m.etat.partie = HC.PARTIE_COMBAT; m.core.declencher('debut')
        for e, num in enumerate((3, 34, 74, 99, 3)): m.core.poser(e, num, e)
        m.pas(c, 4)
        for e in range(5): m.core.declencher('mort', e)
        m.core.declencher('victoire'); m.core.declencher('fin', 0); d, = m.pas(c, 1)
        self.assertEqual([(e['nom'], e['total']) for e in d['ennemis']], [('Londuleux', 2), ('Armure errante', 1), ('Scara-somniaque', 1), (HC.NOM_INCONNU, 1)])
        self.assertEqual(len(m.core.appels), 4)                                                                       # (un appel par numero de monstre different)

    def test_les_plaques_l_emportent_sur_le_nom_du_moteur(self):
        m, c = self.m, self.c; combat_simple(m, c); self.assertEqual(m.core.appels, [])                              # les deux noms viennent des plaques : le moteur n'est pas interroge

    def test_groupe_en_fuite_les_monstres_restants_sont_comptes(self):
        """Le groupe s'enfuit : le monstre qui s'etait enfui est note, ceux qui restent n'ont aucun sort."""
        m, c = self.m, self.c; m.etat.partie = HC.PARTIE_COMBAT; m.core.declencher('debut'); m.core.poser(0, 3, 0); m.core.poser(1, 3, 0); m.core.poser(2, 3, 0)
        m.pas(c, 3); m.plaques(['Golem\n\n\t×3']); m.pas(c, 3); m.core.enfui(0); m.pas(c, 1); m.core.declencher('fuite'); m.core.declencher('fin', 0)
        d, = m.pas(c, 1)
        self.assertEqual((d['issue'], d['objets'], d['or'], d['xp']), ('fuite', [], 0, 0))
        self.assertEqual(d['ennemis'], [{'nom': 'Golem', 'total': 3, 'vaincus': 0, 'fuis': 1, 'disparus': 0}])

    def test_pour_un_seul_capteur_par_moteur(self):
        """CapteurCombat.pour(mo) : l'unique ligne d'integration ; les crochets ne sont installes qu'une fois."""
        m = FauxMoteur(); a = HC.CapteurCombat.pour(m); b = HC.CapteurCombat.pour(m)
        self.assertIs(a, b); self.assertTrue(a.actif)
        self.assertTrue(all(len(v) == 1 for v in m.core.uc.crochets.values()))
        for _ in range(3): self.assertEqual(HC.CapteurCombat.pour(m).maj(m), [])
        self.assertIsNot(HC.CapteurCombat.pour(FauxMoteur()), a)

    def test_pour_moteur_qui_refuse_un_attribut(self):
        class Ferme(FauxMoteur):
            def __setattr__(self, nom, valeur):
                if nom == '_capteur_combat': raise AttributeError(nom)
                object.__setattr__(self, nom, valeur)
        m = Ferme(); a = HC.CapteurCombat.pour(m); self.assertIs(HC.CapteurCombat.pour(m), a)
        self.assertTrue(all(len(v) == 1 for v in m.core.uc.crochets.values()))

    def test_moteur_inattendu_capture_desactivee(self):
        m = FauxMoteur(mauvaise_version=True); c = HC.CapteurCombat(m)
        self.assertFalse(c.actif); self.assertEqual(m.core.uc.crochets, {}); self.assertEqual(m.pas(c, 3), [])

    def test_crochet_manquant_capture_desactivee(self):
        m = FauxMoteur(); del m.core.symboles['_ZN6Global9endBattleEb']; c = HC.CapteurCombat(m)
        self.assertFalse(c.actif); self.assertEqual(m.core.uc.crochets, {})                                          # (aucun crochet a moitie installe)

    def test_victoire_complete(self):
        sorties = combat_simple(self.m, self.c)
        self.assertEqual(sorties, [{'t': 5555, 'ennemis': [{'nom': 'Rat volant', 'total': 1, 'vaincus': 1, 'fuis': 0, 'disparus': 0}, {'nom': 'Londuleux', 'total': 1, 'vaincus': 1, 'fuis': 0, 'disparus': 0}], 'or': 13, 'xp': 6, 'issue': 'victoire', 'objets': []}])
        self.assertIsNone(self.c.suivi)

    def test_deux_combats_d_affilee(self):
        a = combat_simple(self.m, self.c); self.m.etat.partie = 0xc; self.m.core.vider(0); self.m.core.vider(1); self.m.pas(self.c, 5)
        b = combat_simple(self.m, self.c, ('Gluant', 'Chauve-sourat'), (0, 5))
        self.assertEqual([[e['nom'] for e in d['ennemis']] for d in a + b], [['Rat volant', 'Londuleux'], ['Gluant', 'Chauve-sourat']])

    def test_mort_indice_parmi_les_monstres_presents(self):
        """execMonsterDeath(i) : i compte les emplacements OCCUPES (getMonsterStatus), pas les emplacements."""
        m, c = self.m, self.c; m.etat.partie = HC.PARTIE_COMBAT; m.core.declencher('debut'); m.core.poser(2, 3, 0); m.core.poser(5, 20, 1); m.core.poser(9, 20, 1); m.pas(c, 2)
        m.core.declencher('mort', 1); m.pas(c)                                                                         # le 2e monstre present = l'emplacement 5
        self.assertEqual([(mo['num'], mo['vaincu']) for mo in c.suivi.monstres], [(3, False), (20, True), (20, False)])

    def test_plaques_du_combat_precedent_ignorees(self):
        m, c = self.m, self.c; m.plaques(['Vieux', 'Nom']); m.etat.partie = HC.PARTIE_COMBAT; m.core.declencher('debut'); m.core.poser(0, 20, 0); m.core.poser(1, 3, 1); m.pas(c, 5)
        self.assertEqual(c.suivi.noms, {})                                                                             # plaques d'avant le debut : jamais lues
        m.plaques(['Rat volant', 'Londuleux']); m.pas(c); self.assertEqual(c.suivi.noms, {20: 'Rat volant', 3: 'Londuleux'})

    def test_plaques_en_retard(self):
        m, c = self.m, self.c; m.etat.partie = HC.PARTIE_COMBAT; m.core.declencher('debut'); m.core.poser(0, 20, 0); m.pas(c, 5); self.assertEqual(c.suivi.noms, {})
        m.plaques(['Rat volant']); m.pas(c); self.assertEqual(c.suivi.noms, {20: 'Rat volant'})

    def test_pas_de_plaque_nom_generique(self):
        m, c = self.m, self.c; m.etat.partie = HC.PARTIE_COMBAT; m.core.declencher('debut'); m.core.poser(0, 20, 0); m.pas(c, 3); m.core.declencher('mort', 0)
        m.core.declencher('victoire'); m.core.declencher('fin', 0); d, = m.pas(c)
        self.assertEqual(d['ennemis'], [{'nom': HC.NOM_INCONNU, 'total': 1, 'vaincus': 1, 'fuis': 0, 'disparus': 0}])

    def test_plaques_apres_une_mort_ignorees(self):
        m, c = self.m, self.c; m.etat.partie = HC.PARTIE_COMBAT; m.core.declencher('debut'); m.core.poser(0, 20, 0); m.core.poser(1, 3, 1); m.pas(c, 3); m.core.declencher('mort', 0); m.pas(c)
        m.plaques(['Londuleux']); m.pas(c, 3); self.assertEqual(c.suivi.noms, {})                                      # un groupe a disparu : les correspondances ne sont plus sures

    def test_defaite(self):
        m, c = self.m, self.c; m.etat.partie = HC.PARTIE_COMBAT; m.core.declencher('debut'); m.core.poser(0, 20, 0); m.pas(c, 3); m.core.ecrire(A_PARTY + HC.OFF_XP, '<2I', 3, 7); m.pas(c)
        m.core.declencher('fin', 1); d, = m.pas(c)
        self.assertEqual((d['issue'], d['or'], d['xp']), ('defaite', 0, 0)); self.assertEqual(d['ennemis'], [{'nom': HC.NOM_INCONNU, 'total': 1, 'vaincus': 0, 'fuis': 0, 'disparus': 0}])

    def test_defaite_signalee_par_le_drapeau_du_resultat(self):
        m, c = self.m, self.c; m.etat.partie = HC.PARTIE_COMBAT; m.core.declencher('debut'); m.core.poser(0, 20, 0); m.pas(c, 3)
        m.core.ram[A_RESULT + HC.OFF_DEFAITE] = 1; m.core.declencher('fin', 0); d, = m.pas(c)                              # defaite d'un combat de scenario : endBattle(faux) mais drapeau « perdu »
        self.assertEqual(d['issue'], 'defaite')

    def test_fuite(self):
        m, c = self.m, self.c; m.etat.partie = HC.PARTIE_COMBAT; m.core.declencher('debut'); m.core.poser(0, 20, 0); m.core.poser(1, 20, 0); m.pas(c, 3)
        m.core.declencher('mort', 0); m.core.ecrire(A_PARTY + HC.OFF_XP, '<2I', 3, 7); m.pas(c, 2); m.core.declencher('fuite'); m.pas(c); m.core.declencher('fuite'); m.core.declencher('fin', 0); d, = m.pas(c)
        self.assertEqual((d['issue'], d['or'], d['xp']), ('fuite', 0, 0)); self.assertEqual(d['ennemis'], [{'nom': HC.NOM_INCONNU, 'total': 2, 'vaincus': 1, 'fuis': 0, 'disparus': 0}])

    def test_renfort_en_cours_de_combat(self):
        m, c = self.m, self.c; m.etat.partie = HC.PARTIE_COMBAT; m.core.declencher('debut'); m.core.poser(0, 20, 0); m.pas(c, 3); m.core.poser(1, 20, 0); m.pas(c, 2)
        self.assertEqual([mo['num'] for mo in c.suivi.monstres], [20, 20])

    def test_hors_combat_rien_a_faire(self):
        m, c = self.m, self.c; m.pas(c, 5); n = m.core.lectures
        self.assertEqual(m.pas(c, 1000), []); self.assertEqual(m.core.lectures, n)                                    # aucune lecture de memoire hors combat

    def test_fin_sans_debut_ignoree(self):
        m, c = self.m, self.c; m.etat.partie = HC.PARTIE_COMBAT; m.core.poser(0, 20, 0); m.pas(c, 3)
        m.core.declencher('mort', 0); m.core.declencher('victoire'); m.core.declencher('fin', 0); self.assertEqual(m.pas(c, 2), [])                  # capteur cree en plein combat : rien de faux

    def test_etat_instantane_charge_en_combat(self):
        m, c = self.m, self.c; m.etat.partie = HC.PARTIE_COMBAT; m.core.declencher('debut'); m.core.poser(0, 20, 0); m.pas(c, 3); self.assertIsNotNone(c.suivi)
        m.etat = FauxEtat(); m.etat.partie = HC.PARTIE_COMBAT; m.images -= 40                                          # Moteur.etat est remplace par etats.appliquer, images revient en arriere
        m.pas(c); self.assertIsNone(c.suivi)
        m.core.declencher('mort', 0); m.core.declencher('victoire'); m.core.declencher('fin', 0); self.assertEqual(m.pas(c, 2), [])

    def test_images_sautees(self):
        m, c = self.m, self.c; m.etat.partie = HC.PARTIE_COMBAT; m.core.declencher('debut'); m.core.poser(0, 20, 0); m.pas(c, 3)
        m.images += 500; m.pas(c); self.assertIsNone(c.suivi)                                                          # l'etat charge pouvait avoir le meme objet Etat : l'ecart d'images le trahit

    def test_images_en_arriere_memes_objets(self):
        m, c = self.m, self.c; m.etat.partie = HC.PARTIE_COMBAT; m.core.declencher('debut'); m.core.poser(0, 20, 0); m.pas(c, 3)
        m.images -= 100; m.pas(c); self.assertIsNone(c.suivi)

    def test_un_nouveau_debut_remplace_le_suivi(self):
        m, c = self.m, self.c; m.etat.partie = HC.PARTIE_COMBAT; m.core.declencher('debut'); m.core.poser(0, 20, 0); m.pas(c, 3)
        m.core.vider(0); m.core.declencher('debut'); m.core.poser(0, 3, 0); m.pas(c, 2); self.assertEqual([mo['num'] for mo in c.suivi.monstres], [3])        # (le premier n'a pas fini : jamais rapporte)

    def test_sortie_du_combat_sans_fin_abandon(self):
        m, c = self.m, self.c; m.etat.partie = HC.PARTIE_COMBAT; m.core.declencher('debut'); m.core.poser(0, 20, 0); m.pas(c, 3)
        m.etat.partie = 0xc; m.pas(c, HC.MAX_IMAGES_SANS_COMBAT - 1); self.assertIsNotNone(c.suivi)
        m.pas(c, 3); self.assertIsNone(c.suivi)                                                                        # retour au titre, sauvegarde chargee... : on ne garde pas un faux combat

    def test_erreur_jamais_propagee(self):
        class Faux: pass
        self.assertEqual(self.c.maj(Faux()), []); self.assertIsNotNone(self.c.erreur)
        self.assertEqual(self.c.maj(self.m), [])                                                                       # le capteur continue de servir
        m, c = self.m, self.c; self.assertEqual(combat_simple(m, c)[0]['issue'], 'victoire')

    def test_crochet_qui_echoue_ne_leve_rien(self):
        self.m.core.mem = lambda a, n: (_ for _ in ()).throw(RuntimeError('lecture impossible'))
        self.m.core.declencher('mort', 0); self.m.core.declencher('fin', 0); self.m.core.declencher('debut')                # (les crochets avalent l'erreur : l'emulateur ne s'arrete jamais)

    def test_garde_fou_evenements(self):
        for _ in range(1000): self.m.core.declencher('victoire')
        self.assertLessEqual(len(self.c.evenements), 200)


# ---------------------------------------------------------------------------------------------------------------------------------- moteur reel (facultatif)
APK, SAVES = os.environ.get('DQ_APK'), os.environ.get('DQ_SAVES')
RE_XP = re.compile(r"reçoit (\d+) points? d'expérience")
RE_OR = re.compile(r"reçoit (\d+) pièces? d'or")


@unittest.skipUnless(APK and SAVES, 'moteur reel : DQ_APK=<dossier des APK patches> DQ_SAVES=<dossier des sauvegardes>')
class MoteurReel(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import unicorn; from dq4_pc.noyau import moteur as MO; from dq4_pc.persistance import etats as ET
        cls.MO, cls.ET, cls.unicorn = MO, ET, unicorn
        cls.mo = MO.Moteur(APK, SAVES, tempfile.mkdtemp(prefix='sv_hcb_')); c = cls.c = cls.mo.core
        cls.mo.charger_sauvegarde(1)
        for _ in range(200): cls.mo.step(0, 0)
        cls.cap = HC.CapteurCombat(cls.mo)
        assert cls.cap.actif
        cls.groupes = [(3, 1)]; cls.enc = c.call(c.export('_ZN7Encount12getSingletonEv'), label='enc')
        def forcer(u, adr, sz, ud):                                                       # composition de la rencontre : 4 groupes au plus, (numero de monstre, nombre) a Encount + 0x34 / 0x44
            for j in range(4):
                i, n = cls.groupes[j] if j < len(cls.groupes) else (0, 0)
                c.mem_w(cls.enc + 0x34 + 4 * j, struct.pack('<I', i)); c.mem_w(cls.enc + 0x44 + 4 * j, struct.pack('<I', n))
        a = c.export('_ZN10BattleRoot12setupMonsterEv'); c.uc.hook_add(unicorn.UC_HOOK_CODE, forcer, None, a, a)
        c.uc.ctl_flush_tb()
        cls.party = c.export('_ZN6status7g_PartyE'); cls.orig = c.export('_ZN6status9PartyData15originalPlayer_E'); cls.double = c.export('_ZN6status10BaseAction11doubleFlag_E')
        cls.depart = ET.instantane(cls.mo)

    def setUp(self):
        self.ET.appliquer(self.mo, self.depart)
        self.combats, self.msgs = [], []
        for _ in range(3): self.pas()
        self.combats.clear(); self.msgs.clear()

    # -- outils
    def or_groupe(self): return struct.unpack('<I', self.c.mem(self.party + 0x2e0, 4))[0]

    def xp_membres(self):
        """Experience de chaque membre du groupe (HaveStatus +8 de HaveStatusInfo + 0x48 ; -1 = pas d'experience, ex. un invite)."""
        idx = [i for i in struct.unpack('<13I', self.c.mem(self.party + 0x304, 13 * 4)) if i]
        return {i: struct.unpack('<I', self.c.mem(self.orig + 0x530 * i + 0x60, 4))[0] for i in idx}

    def pas(self, p=0, d=0):
        self.mo.step(p, d); self.mo.ui.degats = []
        self.combats.extend(self.cap.maj(self.mo))
        for r in self.mo.capteur.vider(): self.msgs.append(r['texte'].replace('\xa0', ' ').replace('\n', ' / ').strip(' /'))

    def lancer(self, groupes):
        MO = self.MO; type(self).groupes = groupes
        self.c.call(self.c.export('_ZN6Global11startBattleEv'), self.mo._global(), label='startBattle')
        n = 0
        while self.mo.etat.partie != MO.PARTIE_COMBAT and n < 1500: self.pas(); n += 1
        self.assertEqual(self.mo.etat.partie, MO.PARTIE_COMBAT)

    def jouer(self, actions=('combattre',), maxi=6000, apres=None):
        """Joue le combat comme le fait test_vitesse_combat (A sur le menu, avance des messages) ; `actions` : une par menu de tete, 'combattre' ou 'fuir' (bouton 3 du menu de type 30)."""
        MO, mo = self.MO, self.mo; st = {'rel': None, 'att': 0, 'k': 0}
        for i in range(maxi):
            p = d = 0
            if st['rel'] is not None: mo.envoyer_menu(st['rel'], 1, -1, 0); st['rel'] = None
            port = mo.menu_actif(); f = mo.ui.f.get(port) if port is not None else None
            if port is not None and not mo.msg_visible:
                st['att'] += 1
                if st['att'] % 4 == 0:
                    if f['type'] == 30:
                        act = actions[min(st['k'], len(actions) - 1)]; st['k'] += 1
                        mo.envoyer_menu(port, 1, 3, 0x10) if act == 'fuir' else mo.envoyer_menu(port, 1, -1, 0x10)
                    else: mo.envoyer_menu(port, 1, -1, 0x10)
                    st['rel'] = port
            elif mo.msg_visible and (mo.ui.msg.get('feed') or mo.etat_message()[1] in (3, 5)):
                st['att'] += 1
                if st['att'] % 4 == 0: p = d = MO.A
            else: st['att'] = 0
            prec = mo.etat.partie; self.pas(p, d)
            if apres: apres(i)
            if mo.etat.partie != MO.PARTIE_COMBAT and prec == MO.PARTIE_COMBAT: return i
        self.fail('le combat ne se termine pas')

    def nombres(self, regex):
        return [int(x) for m in self.msgs for x in regex.findall(m)]

    def verifier_victoire(self, combat, or0, xp0):
        """Le dict, le texte du jeu et la memoire disent la meme chose."""
        self.assertEqual(combat['issue'], 'victoire')
        self.assertEqual(self.nombres(RE_XP), [combat['xp']], 'experience du message')
        self.assertEqual(self.nombres(RE_OR), [combat['or']], 'or du message')
        self.assertEqual(self.or_groupe() - or0, combat['or'], 'or du groupe (avant / apres)')
        apres = self.xp_membres(); gains = {i: apres[i] - xp0[i] for i in apres if xp0[i] != 0xffffffff}
        self.assertTrue(gains and all(g == combat['xp'] for g in gains.values()), 'experience de chaque membre %r' % (gains,))
        for e in combat['ennemis']: self.assertEqual(e['vaincus'] + e['fuis'] + e['disparus'], e['total'])           # (un monstre peut s'enfuir : « Le gluant s'enfuit ! » -- compte comme tel, comme le message du jeu)
        self.assertEqual(sum(e['fuis'] for e in combat['ennemis']), sum(1 for m in self.msgs if "s'enfuit" in m), 'fuites des monstres : le message du jeu et le dict')
        texte = ' | '.join(self.msgs).lower()
        for e in combat['ennemis']: self.assertIn(e['nom'].lower(), texte, 'le nom doit etre celui que le jeu ecrit')

    # -- scenarios
    def test_victoire_deux_especes(self):
        or0, xp0 = self.or_groupe(), self.xp_membres()
        self.lancer([(3, 2), (0, 1)]); self.jouer()
        self.assertEqual(len(self.combats), 1); c = self.combats[0]
        self.assertEqual([(e['nom'], e['total']) for e in c['ennemis']], [('Londuleux', 2), ('Gluant', 1)])
        self.assertGreater(c['or'], 0); self.assertGreater(c['xp'], 0); self.verifier_victoire(c, or0, xp0)
        self.assertGreaterEqual(c['t'], 0)

    def test_quatre_especes_ordre_d_apparition(self):
        or0, xp0 = self.or_groupe(), self.xp_membres()
        self.lancer([(3, 2), (20, 1), (0, 3), (5, 1)]); self.jouer()
        c, = self.combats
        self.assertEqual([(e['nom'], e['total']) for e in c['ennemis']], [('Londuleux', 2), ('Rat volant', 1), ('Gluant', 3), ('Chauve-sourat', 1)])
        self.verifier_victoire(c, or0, xp0)

    def test_message_de_victoire_par_personnage(self):
        """Le groupe a plusieurs membres : « Chaque membre de l'équipe reçoit N points d'expérience » (N = la valeur par membre, la meme pour tous) et « L'équipe reçoit M pièces d'or » (M = le total)."""
        self.lancer([(20, 3)]); self.jouer(); c, = self.combats
        self.assertTrue(any('Chaque membre' in m for m in self.msgs) or len(self.xp_membres()) < 2)
        self.assertEqual(self.nombres(RE_XP), [c['xp']]); self.assertEqual(self.nombres(RE_OR), [c['or']])

    def test_experience_doublee(self):
        """Le jeu double l'or et l'experience (BaseAction::doubleFlag_) au moment de les verser : le dict donne le nombre du message, pas celui des monstres."""
        cible = self.c.export('_ZN23BattleExecDefeatMonster10initializeEv')
        h = self.c.uc.hook_add(self.unicorn.UC_HOOK_CODE, lambda u, a, s, d: self.c.mem_w(self.double, b'\x01'), None, cible, cible); self.c.uc.ctl_flush_tb()
        try:
            or0, xp0 = self.or_groupe(), self.xp_membres()
            self.lancer([(20, 2)]); self.jouer(); c, = self.combats
        finally:
            self.c.uc.hook_del(h); self.c.mem_w(self.double, b'\x00')
        self.assertEqual((c['xp'], c['or']), (12, 28)); self.verifier_victoire(c, or0, xp0)                       # 2 rats volants : 3 d'experience et 7 d'or chacun, doubles

    def test_fuite_apres_une_mort(self):
        or0, xp0 = self.or_groupe(), self.xp_membres()
        self.lancer([(3, 2), (0, 3)]); self.jouer(actions=('combattre', 'fuir'))
        c, = self.combats
        self.assertEqual((c['issue'], c['or'], c['xp']), ('fuite', 0, 0))
        self.assertEqual([(e['nom'], e['total'], e['vaincus']) for e in c['ennemis']], [('Londuleux', 2, 1), ('Gluant', 3, 0)])
        self.assertEqual(self.or_groupe(), or0); self.assertEqual(self.xp_membres(), xp0)                       # le moteur ne verse rien pour une fuite
        self.assertTrue(any("s'enfuit" in m for m in self.msgs))

    def test_fuite_reussie_apres_des_echecs(self):
        """« Mais l'ennemi bloque le passage ! » : BattleExecEscape::setup tourne a chaque tentative ; seule la derniere termine le combat."""
        self.lancer([(3, 2), (20, 2)]); self.jouer(actions=('fuir',), maxi=8000)
        c, = self.combats
        self.assertEqual((c['issue'], c['or'], c['xp']), ('fuite', 0, 0)); self.assertEqual([e['vaincus'] for e in c['ennemis']], [0, 0])

    def test_defaite(self):
        or0 = self.or_groupe()
        self.lancer([(150, 3)]); self.jouer(maxi=9000)
        c, = self.combats
        self.assertEqual((c['issue'], c['or'], c['xp']), ('defaite', 0, 0))
        self.assertEqual([(e['total'], e['vaincus']) for e in c['ennemis']], [(3, 0)]); self.assertTrue(c['ennemis'][0]['nom'])
        self.assertLessEqual(self.or_groupe(), or0)                                                              # (le jeu retire la moitie de l'or a un groupe anéanti)

    def test_deux_combats_d_affilee(self):
        self.lancer([(20, 1)]); self.jouer(); self.lancer([(3, 1), (0, 1)]); self.jouer()
        self.assertEqual([[e['nom'] for e in c['ennemis']] for c in self.combats], [['Rat volant'], ['Londuleux', 'Gluant']])
        self.assertLess(self.combats[0]['t'], self.combats[1]['t']); self.assertTrue(all(c['issue'] == 'victoire' for c in self.combats))

    def test_interrompu_par_un_etat_charge_en_ville(self):
        """Etat pris en ville, charge en plein combat : rien de faux, pas de plantage, et le combat suivant est bien rapporte."""
        ET = self.ET; ville = ET.instantane(self.mo)
        self.lancer([(3, 2), (0, 1)])
        for _ in range(500): self.pas()
        self.assertIsNotNone(self.cap.suivi)
        ET.appliquer(self.mo, ville)
        for _ in range(200): self.pas()
        self.assertIsNone(self.cap.suivi); self.assertEqual(self.combats, [])
        self.lancer([(20, 1)]); self.jouer(); self.assertEqual([[e['nom'] for e in c['ennemis']] for c in self.combats], [['Rat volant']])

    def test_interrompu_par_un_etat_de_milieu_de_combat(self):
        """Etat pris en plein combat : le combat joue jusqu'au bout est rapporte ; l'etat recharge puis termine ne l'est pas (on n'a pas vu le debut de ce combat-la)."""
        ET = self.ET; self.lancer([(3, 2), (0, 2)])
        for _ in range(480): self.pas()
        milieu = ET.instantane(self.mo); self.jouer(); self.assertEqual(len(self.combats), 1); self.combats.clear()
        ET.appliquer(self.mo, milieu); self.pas(); self.assertEqual(self.mo.etat.partie, self.MO.PARTIE_COMBAT)
        self.jouer(); self.assertEqual(self.combats, [])

    def test_capteur_cree_en_plein_combat(self):
        self.lancer([(20, 2)])
        for _ in range(300): self.pas()
        tardif = HC.CapteurCombat(self.mo); sorties = []
        for _ in range(4000):
            self.pas(*self._touches()); sorties.extend(tardif.maj(self.mo))
            if self.mo.etat.partie != self.MO.PARTIE_COMBAT: break
        self.assertEqual(sorties, [])

    def _touches(self):
        mo = self.mo
        if mo.msg_visible and (mo.ui.msg.get('feed') or mo.etat_message()[1] in (3, 5)): return self.MO.A, self.MO.A
        port = mo.menu_actif()
        if port is not None and not mo.msg_visible: mo.envoyer_menu(port, 1, -1, 0x10)
        return 0, 0

    def test_capteur_cree_apres_des_combats(self):
        """Un capteur installe quand le moteur a deja execute le code de combat (blocs traduits par l'emulateur) fonctionne aussi."""
        self.lancer([(20, 1)]); self.jouer(); self.combats.clear()
        tardif = HC.CapteurCombat(self.mo); sorties = []
        self.lancer([(3, 1)])
        orig = self.pas
        def pas(p=0, d=0): orig(p, d); sorties.extend(tardif.maj(self.mo))
        self.pas = pas
        try: self.jouer()
        finally: del self.pas
        self.assertEqual([[e['nom'] for e in c['ennemis']] for c in sorties], [['Londuleux']]); self.assertEqual(sorties[0]['xp'], self.combats[0]['xp'])

    def noms_apres_les_plaques(self, ids):
        """Lance un combat contre `ids` (un de chaque) et joue jusqu'a ce que le capteur ait lu les plaques (ouverture du choix de la cible) ; -> ({numero: nom}, messages d'apparition)."""
        class Fini(Exception): pass
        def apres(_i):
            if self.cap.suivi is not None and all(i in self.cap.suivi.noms for i in ids): raise Fini()
        self.lancer([(i, 1) for i in ids])
        try: self.jouer(maxi=2000, apres=apres)
        except Fini: pass
        return dict(self.cap.suivi.noms), [m for m in self.msgs if 'apparaît' in m]

    def test_noms_complets_des_monstres_a_nom_long(self):
        """Le nom du dict est celui que le jeu ecrit dans son message d'apparition (sans les marques de coupure « ; » et « $ »), meme quand la plaque le coupe sur deux lignes."""
        noms, apparitions = self.noms_apres_les_plaques([0, 34, 74, 82])
        self.assertEqual(noms, {0: 'Gluant', 34: 'Armure errante', 74: 'Scara-somniaque', 82: 'Gluant de mercure'})
        texte = ' | '.join(apparitions).lower().replace(';', '').replace('$', '-')
        for n in noms.values(): self.assertIn(n.lower(), texte)

    def test_noms_des_plaques_ordre_des_groupes(self):
        """Quatre especes distinctes, dans un ordre qui n'est ni celui des numeros ni l'alphabetique : chaque numero de monstre recoit SON nom (verifie par le message d'apparition)."""
        noms, apparitions = self.noms_apres_les_plaques([20, 3, 5, 0])
        self.assertEqual(noms, {20: 'Rat volant', 3: 'Londuleux', 5: 'Chauve-sourat', 0: 'Gluant'})
        self.assertEqual([m.lower() for m in apparitions], ['un rat volant apparaît !', 'un londuleux apparaît !', 'un chauve-sourat apparaît !', 'un gluant apparaît !'])

    # -- #141 : monstres enfuis / disparus, objets gagnes
    def forcer_sort(self, emplacement, sort):
        """Fait partir un monstre comme le fait le jeu : etat « mort » (setDeath) et drapeau de fuite (bit 4 de HaveStatusInfo + 0x424) ou de disparition (bit 5) ; checkDeathMonster le compte alors a l'image suivante."""
        c = self.c; hsi = c.export('_ZN6status9g_MonsterE') + HC.DEBUT_MONSTRES + emplacement * HC.PAS_MONSTRE + 0x10
        c.call(c.export('_ZN6status14HaveStatusInfo13setEscapeFlagEb' if sort == 'fui' else '_ZN6status14HaveStatusInfo16setDisappearFlagEb'), hsi, 1, label='drapeau')
        c.call(c.export('_ZN6status14HaveStatusInfo8setDeathEv'), hsi, label='setDeath')

    def test_monstre_enfui_et_monstre_disparu(self):
        """Un monstre enfui et un monstre disparu (forces dans la memoire du jeu) sont notes par espece ; les autres sont vaincus par le groupe ; l'issue est une victoire."""
        etat = {'fait': False}
        def cb(i):
            if i == 30 and not etat['fait']: etat['fait'] = True; self.forcer_sort(1, 'fui'); self.forcer_sort(2, 'disparu')
        self.lancer([(3, 4)]); self.jouer(apres=cb, maxi=9000)
        self.assertTrue(etat['fait']); c, = self.combats
        e, = c['ennemis']; self.assertEqual((e['nom'], e['total'], e['fuis'], e['disparus']), ('Londuleux', 4, 1, 1)); self.assertEqual(e['vaincus'], 2)
        self.assertEqual(c['issue'], 'victoire'); self.assertGreater(c['xp'], 0)

    def test_objet_gagne_a_la_fin_du_combat(self):
        """Un objet donne par le jeu en fin de combat (« Le londuleux laisse tomber un coffre au trésor ! ... Il contient un arc de chasseur ! » ; le butin est ecrit dans le groupe de monstres comme le jeu le fait a la mort du monstre, BattleExecItem le donne) : son nom est celui du message du jeu."""
        c = self.c; mp = c.export('_ZN6status9g_MonsterE'); etat = {'fait': False}
        def cb(i):                                                                                     # (le jeu ecrit le butin du monstre quand il meurt : on pose le notre juste apres, avant la victoire)
            if not etat['fait'] and any('vaincu' in m for m in self.msgs):
                etat['fait'] = True; c.call(c.export('_ZN6status12MonsterParty11setDropItemEi'), mp, 12, label='drop'); c.call(c.export('_ZN6status12MonsterParty18setDropItemMonsterEi'), mp, 3, label='drop monstre')
        self.lancer([(3, 1)]); self.jouer(apres=cb, maxi=9000)
        self.assertTrue(etat['fait']); d, = self.combats; self.assertEqual(d['issue'], 'victoire')
        self.assertEqual(len(d['objets']), 1, self.msgs); o = d['objets'][0]
        self.assertTrue(o['nom'] and not o['nom'].startswith('Objet n'), o)
        texte = ' | '.join(self.msgs).lower().replace(';', ''); self.assertIn(o['nom'].lower(), texte, 'le nom doit etre celui que le jeu ecrit')

    def test_cout_hors_combat(self):
        import time
        t0 = time.perf_counter(); n = 600
        for _ in range(n): self.mo.step(0, 0)
        t1 = time.perf_counter()
        for _ in range(n): self.mo.images += 1; self.cap.maj(self.mo)
        t2 = time.perf_counter()
        pas_us, maj_us = (t1 - t0) / n * 1e6, (t2 - t1) / n * 1e6
        print('\n  hors combat : maj %.1f us par image (un pas du moteur : %.0f us)' % (maj_us, pas_us))
        self.assertLess(maj_us, 200.0); self.assertLess(maj_us, pas_us * 0.1)


if __name__ == '__main__':
    unittest.main(verbosity=2)
