"""Test du coffre au tresor lache par un ennemi a la fin d'un combat (« Le londuleux laisse tomber un coffre au tresor ! », « Ragnar l'ouvre. », « Il contient ... », « Ragnar met ... dans le sac. »).

Question posee (retours de 22 h 29) : le jeu d'origine joue-t-il un bruitage d'ouverture de coffre pendant ces messages ? Reponse etablie en lisant le moteur et en le faisant tourner :
  - la suite est la tache BattleExecItem (4 sous-taches BattleExecVictory30 a 32, messages 801876 et suivants) : elles ne font que poser un message (TextAPI::setMACRO0, BattleMessage::setMessage,
    BattleAutoFeed::setMessageSend) et donner l'objet (PartyStatus::giveItem) ; aucune ne passe par SoundManager / Sound::sePlayDirect ;
  - Unity n'appelle Sound.PlaySE directement que dans InputName.Update, MenuPortItem.Update et TouchPad.internalUpdate (boutons : bruitage 300) ;
  - dans le moteur reel, avec un butin force, les seuls paquets de son de toute la suite sont le bruitage 300 (« bip ») du debut de chacun des 4 messages, joue par ui_MsgLoop.
Ce test garde cette observation : si un jour le moteur demandait un autre son pendant ces messages, `Etat.sons` le contiendrait et la visionneuse (Son.evenements) le jouerait ; le test echouerait pour qu'on le sache.

Le butin est force dans un moteur jetable : MonsterParty::getDropItem / getDropItemMonster (champs +0x3eac et +0x3eb0 de MonsterParty, ecrits par checkDropItem au tirage de fin de combat) renvoient un objet
et un monstre imposes (la meme methode que test_historique_combat force la composition d'un groupe).

    DQ_APK=<dossier des APK patches> DQ_SAVES=<dossier des sauvegardes> python3 outils/test_coffre_ennemi.py        (une minute environ)
Sans DQ_APK et DQ_SAVES, le test du moteur reel est saute.
"""
import os, struct, sys, tempfile, unittest

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ICI, '..'))
APK, SAVES = os.environ.get('DQ_APK'), os.environ.get('DQ_SAVES')
OBJET_FORCE, MONSTRE_FORCE = 1, 3          # bâton de cyprès ; londuleux (le monstre du combat)
SE_BIP = 300                                # bruitage joue par ui_MsgLoop au debut de chaque message quand le joueur vient de reprendre la main
ETAPES = ('laisse tomber un coffre au trésor', "l'ouvre", 'Il contient', 'dans le sac')


@unittest.skipUnless(APK and SAVES, 'moteur reel : DQ_APK=<dossier des APK patches> DQ_SAVES=<dossier des sauvegardes>')
class CoffreLacheParUnEnnemi(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import unicorn; from dq4_pc.noyau import moteur as MO; from dq4_pc.persistance import etats as ET
        cls.MO, cls.ET = MO, ET
        cls.mo = MO.Moteur(APK, SAVES, tempfile.mkdtemp(prefix='sv_coffre_')); c = cls.c = cls.mo.core
        cls.mo.charger_sauvegarde(1)
        for _ in range(200): cls.mo.step(0, 0)
        enc = c.call(c.export('_ZN7Encount12getSingletonEv'), label='enc')
        def groupe(u, adr, sz, ud):                                                      # rencontre imposee : un londuleux
            for j in range(4):
                i, n = (MONSTRE_FORCE, 1) if j == 0 else (0, 0)
                c.mem_w(enc + 0x34 + 4 * j, struct.pack('<I', i)); c.mem_w(enc + 0x44 + 4 * j, struct.pack('<I', n))
        a = c.export('_ZN10BattleRoot12setupMonsterEv'); c.uc.hook_add(unicorn.UC_HOOK_CODE, groupe, None, a, a)
        cls.butin = True
        def butin(u, adr, sz, ud):                                                       # tirage de fin de combat : un coffre contenant OBJET_FORCE (ou aucun)
            x0 = u.reg_read(c.XREG[0])
            c.mem_w(x0 + 0x3eac, struct.pack('<I', OBJET_FORCE if cls.butin else 0)); c.mem_w(x0 + 0x3eb0, struct.pack('<I', MONSTRE_FORCE if cls.butin else 0))
        for n in ('_ZN6status12MonsterParty11getDropItemEv', '_ZN6status12MonsterParty18getDropItemMonsterEv'):
            a = c.export(n); c.uc.hook_add(unicorn.UC_HOOK_CODE, butin, None, a, a)
        c.uc.ctl_flush_tb()
        cls.depart = ET.instantane(cls.mo)

    def jouer(self, butin):
        """Combat force joué jusqu'a son terme (A partout). -> (textes [(image, texte)], sons [(image, type, valeur)]) ; sons = Etat.sons, ce que la visionneuse transmet a Son.evenements."""
        MO, mo, c = self.MO, self.mo, self.c
        type(self).butin = butin
        self.ET.appliquer(mo, self.depart)
        textes, sons = [], []
        def pas(p=0, d=0):
            mo.etat.sons = []; mo.step(p, d); mo.ui.degats = []
            sons.extend((mo.images, t, v) for t, v in mo.etat.sons)
            for r in mo.capteur.vider(): textes.append((mo.images, r['texte'].replace('\xa0', ' ').replace('\n', ' / ').strip(' /')))
        for _ in range(3): pas()
        textes.clear(); sons.clear()
        c.call(c.export('_ZN6Global11startBattleEv'), mo._global(), label='startBattle')
        n = 0
        while mo.etat.partie != MO.PARTIE_COMBAT and n < 1500: pas(); n += 1
        self.assertEqual(mo.etat.partie, MO.PARTIE_COMBAT)
        st = {'rel': None, 'att': 0}
        for i in range(6000):
            p = d = 0
            if st['rel'] is not None: mo.envoyer_menu(st['rel'], 1, -1, 0); st['rel'] = None
            port = mo.menu_actif()
            if port is not None and not mo.msg_visible:
                st['att'] += 1
                if st['att'] % 4 == 0: mo.envoyer_menu(port, 1, -1, 0x10); st['rel'] = port
            elif mo.msg_visible and (mo.ui.msg.get('feed') or mo.etat_message()[1] in (3, 5)):
                st['att'] += 1
                if st['att'] % 4 == 0: p = d = MO.A
            else: st['att'] = 0
            prec = mo.etat.partie; pas(p, d)
            if mo.etat.partie != MO.PARTIE_COMBAT and prec == MO.PARTIE_COMBAT: return textes, sons
        self.fail('le combat ne se termine pas')

    @staticmethod
    def image_de(textes, morceau):
        return next((im for im, t in textes if morceau in t), None)

    def test_suite_des_messages_et_seul_bruitage_300(self):
        textes, sons = self.jouer(True)
        images = [self.image_de(textes, e) for e in ETAPES]
        self.assertTrue(all(im is not None for im in images), 'les 4 messages du coffre sont affiches : %r' % (images,))
        self.assertEqual(images, sorted(images), 'dans l\'ordre : coffre lache, ouverture, contenu, objet range dans le sac')
        # fenetre : du debut du 1er message (le bip precede le texte d'une image) a celui du dernier (+ 3 images)
        fenetre = [(im, t, v) for im, t, v in sons if images[0] - 3 <= im <= images[-1] + 3]
        self.assertEqual([v for _, t, v in fenetre if t == 35], [SE_BIP] * 4, 'un seul bruitage par message, le bip 300 : le moteur ne demande aucun bruitage d\'ouverture de coffre')
        self.assertEqual([t for _, t, v in fenetre if t != 35], [], 'ni arret de bruitage ni musique pendant la suite du coffre')

    def test_sans_coffre_pas_de_message(self):
        textes, sons = self.jouer(False)
        self.assertIsNone(self.image_de(textes, ETAPES[0]), 'sans butin force (objet 0), aucun coffre')
        self.assertTrue(any('pièces d\'or' in t for _, t in textes), 'le combat est bien gagne')


if __name__ == '__main__':
    unittest.main(verbosity=2)
