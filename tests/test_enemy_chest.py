"""Test du coffre au tresor lache par un ennemi a la fin d'un combat (« Le londuleux laisse tomber un coffre au tresor ! », « Ragnar l'ouvre. », « Il contient ... », « Ragnar met ... dans le sac. »).

Question posee (retours de 22 h 29) : le jeu d'origine joue-t-il un bruitage d'ouverture de coffre pendant ces messages ? Reponse etablie en lisant le moteur et en le faisant tourner :
  - la suite est la tache BattleExecItem (4 sous-taches BattleExecVictory30 a 32, messages 801876 et suivants) : elles ne font que poser un message (TextAPI::setMACRO0, BattleMessage::setMessage,
    BattleAutoFeed::setMessageSend) et donner l'objet (PartyStatus::giveItem) ; aucune ne passe par SoundManager / Sound::sePlayDirect ;
  - Unity n'appelle Sound.PlaySE directement que dans InputName.Update, MenuPortItem.Update et TouchPad.internalUpdate (boutons : bruitage 300) ;
  - dans le moteur reel, avec un butin force, les seuls paquets de son de toute la suite sont le bruitage 300 (« bip ») du debut de chacun des 4 messages, joue par ui_MsgLoop.
Ce test garde cette observation : si un jour le moteur demandait un autre son pendant ces messages, `State.sounds` le contiendrait et la visionneuse (Sound.evenements) le jouerait ; le test echouerait pour qu'on le sache.

Le butin est force dans un moteur jetable : MonsterParty::getDropItem / getDropItemMonster (champs +0x3eac et +0x3eb0 de MonsterParty, ecrits par checkDropItem au tirage de fin de combat) renvoient un objet
et un monstre imposes (la meme methode que test_battle_history force la composition d'un groupe).

    DQ_APK=<dossier des APK patches> DQ_SAVES=<dossier des sauvegardes> python3 tools/test_enemy_chest.py        (une minute environ)
Sans DQ_APK et DQ_SAVES, le test du moteur reel est saute.
"""
import os, struct, sys, tempfile, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..'))
APK, SAVES = os.environ.get('DQ_APK'), os.environ.get('DQ_SAVES')
FORCED_ITEM, FORCED_MONSTER = 1, 3          # bâton de cyprès ; londuleux (le monstre du combat)
SFX_BEEP = 300                                # bruitage joue par ui_MsgLoop au debut de chaque message quand le joueur vient de reprendre la main
STAGES = ('laisse tomber un coffre au trésor', "l'ouvre", 'Il contient', 'dans le sac')


@unittest.skipUnless(APK and SAVES, 'moteur reel : DQ_APK=<dossier des APK patches> DQ_SAVES=<dossier des sauvegardes>')
class ChestDroppedByEnemy(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import unicorn; from dq4_pc.core import engine as ENGINE; from dq4_pc.persistence import savestates as SS
        cls.ENGINE, cls.SS = ENGINE, SS
        cls.eng = ENGINE.Engine(APK, SAVES, tempfile.mkdtemp(prefix='sv_coffre_')); c = cls.c = cls.eng.core
        cls.eng.load_save(1)
        for _ in range(200): cls.eng.step(0, 0)
        enc = c.call(c.export('_ZN7Encount12getSingletonEv'), label='enc')
        def group(u, addr, sz, ud):                                                      # rencontre imposee : un londuleux
            for j in range(4):
                i, n = (FORCED_MONSTER, 1) if j == 0 else (0, 0)
                c.mem_w(enc + 0x34 + 4 * j, struct.pack('<I', i)); c.mem_w(enc + 0x44 + 4 * j, struct.pack('<I', n))
        a = c.export('_ZN10BattleRoot12setupMonsterEv'); c.uc.hook_add(unicorn.UC_HOOK_CODE, group, None, a, a)
        cls.loot = True
        def loot(u, addr, sz, ud):                                                       # tirage de fin de combat : un coffre contenant FORCED_ITEM (ou aucun)
            x0 = u.reg_read(c.XREG[0])
            c.mem_w(x0 + 0x3eac, struct.pack('<I', FORCED_ITEM if cls.loot else 0)); c.mem_w(x0 + 0x3eb0, struct.pack('<I', FORCED_MONSTER if cls.loot else 0))
        for n in ('_ZN6status12MonsterParty11getDropItemEv', '_ZN6status12MonsterParty18getDropItemMonsterEv'):
            a = c.export(n); c.uc.hook_add(unicorn.UC_HOOK_CODE, loot, None, a, a)
        c.uc.ctl_flush_tb()
        cls.initial = SS.snapshot(cls.eng)

    def play(self, loot):
        """Combat force joué jusqu'a son terme (A partout). -> (textes [(image, texte)], sons [(image, type, valeur)]) ; sons = State.sons, ce que la visionneuse transmet a Sound.evenements."""
        ENGINE, eng, c = self.ENGINE, self.eng, self.c
        type(self).loot = loot
        self.SS.apply(eng, self.initial)
        texts, sounds = [], []
        def step(p=0, d=0):
            eng.state.sounds = []; eng.step(p, d); eng.ui.damage = []
            sounds.extend((eng.frames, t, v) for t, v in eng.state.sounds)
            for r in eng.sensor.drain(): texts.append((eng.frames, r['texte'].replace('\xa0', ' ').replace('\n', ' / ').strip(' /')))
        for _ in range(3): step()
        texts.clear(); sounds.clear()
        c.call(c.export('_ZN6Global11startBattleEv'), eng._global(), label='startBattle')
        n = 0
        while eng.state.part != ENGINE.PART_BATTLE and n < 1500: step(); n += 1
        self.assertEqual(eng.state.part, ENGINE.PART_BATTLE)
        st = {'rel': None, 'att': 0}
        for i in range(6000):
            p = d = 0
            if st['rel'] is not None: eng.send_menu(st['rel'], 1, -1, 0); st['rel'] = None
            port = eng.active_menu()
            if port is not None and not eng.msg_visible:
                st['att'] += 1
                if st['att'] % 4 == 0: eng.send_menu(port, 1, -1, 0x10); st['rel'] = port
            elif eng.msg_visible and (eng.ui.msg.get('feed') or eng.message_state()[1] in (3, 5)):
                st['att'] += 1
                if st['att'] % 4 == 0: p = d = ENGINE.A
            else: st['att'] = 0
            prev = eng.state.part; step(p, d)
            if eng.state.part != ENGINE.PART_BATTLE and prev == ENGINE.PART_BATTLE: return texts, sounds
        self.fail('le combat ne se termine pas')

    @staticmethod
    def frame_of(texts, chunk):
        return next((im for im, t in texts if chunk in t), None)

    def test_message_sequence_and_only_sfx_300(self):
        texts, sounds = self.play(True)
        frames = [self.frame_of(texts, e) for e in STAGES]
        self.assertTrue(all(im is not None for im in frames), 'les 4 messages du coffre sont affiches : %r' % (frames,))
        self.assertEqual(frames, sorted(frames), 'dans l\'ordre : coffre lache, ouverture, contenu, objet range dans le sac')
        # fenetre : du debut du 1er message (le bip precede le texte d'une image) a celui du dernier (+ 3 images)
        window = [(im, t, v) for im, t, v in sounds if frames[0] - 3 <= im <= frames[-1] + 3]
        self.assertEqual([v for _, t, v in window if t == 35], [SFX_BEEP] * 4, 'un seul bruitage par message, le bip 300 : le moteur ne demande aucun bruitage d\'ouverture de coffre')
        self.assertEqual([t for _, t, v in window if t != 35], [], 'ni arret de bruitage ni musique pendant la suite du coffre')

    def test_without_chest_no_message(self):
        texts, sounds = self.play(False)
        self.assertIsNone(self.frame_of(texts, STAGES[0]), 'sans butin force (objet 0), aucun coffre')
        self.assertTrue(any('pièces d\'or' in t for _, t in texts), 'le combat est bien gagne')


if __name__ == '__main__':
    unittest.main(verbosity=2)
