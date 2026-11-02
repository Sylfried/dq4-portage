"""Tests objectifs (sans fenetre, sans moteur, sans APK) de dq4_pc/libelles.py : libelles des personnages / objets (libelle_source) et des lieux (libelle_lieu).

Les tableaux de frequence (cartes du jeu, placements de personnages par modele, modeles de decor) sont ceux du jeu, ecrits ici par outils/generer_libelles.py : le test les rejoue
sans rien relire dans les APK. Il imprime la couverture (a lire avec `-v`) et echoue si un modele frequent n'a pas de libelle, si un libelle n'a pas la forme « article + minuscules »,
si deux motifs de decor se contredisent ou si l'import n'est pas instantane.

Usage (depuis la racine du depot) :  python3 outils/test_libelles.py [-v]
"""
import collections, os, re, subprocess, sys, unittest

RACINE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
sys.path.insert(0, os.path.join(RACINE, 'dq4_pc'))
import libelles as L

# === DEBUT GENERE (outils/generer_libelles.py) ===
# cartes du jeu (670)
CARTES = ('btl_mt_d btl_mt_e btl_mt_n btl_pl_d btl_pl_dk btl_pl_e btl_pl_n btl_po_d btl_po_dk btl_po_e btl_po_n btl_sd_d btl_sd_e btl_sd_n btl_se_d btl_se_e '
    'btl_se_n btl_wd_d btl_wd_dk btl_wd_e btl_wd_n btlcb1_d btlcb1_e btlcb1_n btlcb2 btlcb2_d btlcb2_e btlcb2_n btlcc1_d btlcc1_e btlcc2 btlce1 btlcj1_d '
    'btlcj1_e btlcj1_n btlcj2_d btlcj2_e btlcj2_n btlcj3_d btlcj3_e btlcj3_n btlcj4_d btlcj4_e btlcj4_n btlcj5_d btlcj5_e btlcj5_n btlcl1 btlcl2 btlcm1 '
    'btlcm2 btlcm3 btlda1 btldb1 btldc1 btldc2 btldd1 btlde1 btldg1 btldh1 btldi1 btldj1 btldk1 btldl1 btldl2 btldm1 btldn1 btldo1 btldougu_d btldougu_e '
    'btldougu_n btldp1 btldp2 btldp3 btldp4 btldp5_d btldp5_e btldp5_n btldp6 btldp7 btldp8_d btldp8_e btldp8_n btldp9_d btldp9_e btldp9_n btldpou1 '
    'btldpou2 btldpou3 btldpou4 btldpou5 btldpou6 btldpou7 btldpou8 btldpou9 btlmc1 btlmc1_d btlmc1_e btlmc1_n btlmc2_d btlmc2_e btlmc2_n btlmq1_d btlmq1_e '
    'btlmq1_n btlsj1_d btlsj1_e btlsj1_n btlsl1 btlsn1 btlso1 btlsp1 btlsq1 btlsr1 btlta1_d btlta1_e btlta1_n btlta2 btltb1_d btltb1_e btltb1_n btltc1_d '
    'btltc1_dk btltc1_e btltc1_n btltc2_d btltc2_e btltc2_n btltd1_d btltd1_e btltd1_n btltd2_d btltd2_e btltd2_n btlte1_d btlte1_e btlte1_n btlyado_d '
    'btlyado_e btlyado_n caf1 caf2a caf2b cbf1 cbf2 cbf3 cbout ccb1a ccb1b ccb1c ccb1d cccf1a cccf1b cccf2 cccido ccf1a ccf1b ccf2 ccf3 ccout cda1f1 cdf1 '
    'cdido cdout cdp1b1 cdw1f1 cdy1f1 ceb1 cef1a cef1b cef1c cef2 ceout cep1b1 cff1 cff2 cfy1f2 cgf1 cgout1 chf1a chf1b chf2 chf3 chout cib1a cib1b cif1 '
    'cif2 ciido ciout cip1b1 cjb1a cjb1b cjb1c cjb1d cjb2 cjf1a cjf1d cjf2a cjf2b cjf2c cjout ckf1 ckf2 ckf3f5 ckf4 ckout clf1a clf1b clf2a clf3a clf3b '
    'clf3c clf4a clf4b clf4c clf5a clf5b clout cmf1a cmf1b cmf1c cmf3a cmf3b cmout dab1 dbb1a dbb1b dbb2a dbb2b dbb2c dbb3 dbm1b1 dbm1b2 dbout dcb1 dcb2 '
    'dcb3 ddb1a ddb1b ddb2 ddb3 ddb4 ddb5a ddb5b deb1 deb2a deb3a deb4 dfb1a dfb1b dgb1 dgb2 dgb3 dgb4 dgb5 dhb1 dhb2a dhb2b dhb2c dhb2d dhf1 dib1 dib2 '
    'dib3a dib3b djb1 djb2 djb3 dkb1 dkf1a dkf1c dlb1a dlb2 dlb3 dlb4 dlb5 dmb1 dmb1n1 dmb2 dmb3 dmf1 dmout dnb1a dnb1b dnb1b2 dnb1c dnb2 dnb2b3 dnb3 '
    'dnb3b4 dnb4 dnb5 dnb6 dob1 dob2 dob3a dob3b dob4 dpb1a dpb1b dpb2a dpb2b dpb2c dpb3 dpb4a dpb4b dpb4ido dpb5a dpb5b dpb5c dpb5ido dpb6a dpb6b dpb6c '
    'dpb6d dpb6e dpb7a dpb7b dpb7c dpb7d dpb7e dpb7f dpb8a dpb8b dpb8c dpb8d dpout ev01 ev02 ev03 ev04 ev05 ev06 ev07 ev08 ev09 fk01 haa1f1 haa1f2 haido '
    'hak1f1 ham1f1 ham1f2 ham2f1 haout hay1f1 hcido hck1f1 hcm1f1 hcm1f2 hcm2f1 hcm2f2 hcm3f1 hcm3f2 hcout hcy1b1 hcy1f1 hcy1f2 hhido hhk1f1 hhm1f1 hhm2f1 '
    'hhout hhy1f1 mai1f1 mai1f2 maido mak1f1 mam1f1 mam2f1 maout map1b1 may1f1 may1f2 mbk1f1 mbk1f2 mbm1f1 mbout mbw1f1 mbw1f2 mby1f1 mby1f2 mcido mck1f1 '
    'mcm1f1 mcm2f1 mcm3f1 mcout1 mcout2 mcy1f1 mdi1f1 mdm1f1 mdm2f1 mdm3f1 mdout mdy1f1 mdy1f2 mem1f1 meout mey1f1 mfa1f1 mfa1f2 mfk1f1 mfm1f1 mfm2f1 mfout '
    'mfw1b1 mfw1f1 mfy1f1 mgm1f1 mgm2f1 mgm3f1 mgout1 mgout2 mgout3 mhg1b1 mhg1f1 mhg1n1 mhido1 mhido2 mhk1f1 mhm1f1 mhm1f2 mhm2f1 mhm3f1 mhm3f2 mhout '
    'mhy1f1 mhy1f2 miido mim1f1 mim2f1 mim3b1 mim3f1 miout miy1f1 mjf1b1 mjf1f1 mjf1n1 mjk1f1 mjm1f1 mjout mjp1b1 mjp1f1 mjy1f1 mjy1f2 mkk1f1 mkm1f1 mkm2f1 '
    'mkm3f1 mkout mky1f1 mlb1a mlb1b mlido mlm1f1 mlm2f1 mlout1 mlout2 mly1f1 mmk1f1 mmm1f1 mmout mmw1f1 mmy1f1 mmy1f2 mmy2f1 mndoc mnf1b1 mnf1n1 mnf2b1 '
    'mnf2n1 mnk1f1 mnm1f1 mnm2f1 mnout mny1f1 mny1f2 moido mom1f1 mom2f1 moout moy1f1 moy1f2 mpido mpm1f1 mpm2f1 mpout1 mpout2 mpy1f1 mqb1 mqido mqm1f1 '
    'mqout mqtf1a mqtf1b mqtf2 mqtf3 mqy1f1 mrb1 mrm1f1 mrm2f1 mrout mrw1f1 mry1f1 msa1f1 msi1f1 msm1f1 msm2f1 msout msy1f1 saf1 sbm1f1 sbout sby1f1 scf1 '
    'sdf1 sdout seido seout sey1f1 sff1 sgf1 shb1 shf1 shf2 shout sif1 sjm1f1 sjm2f1 sjout sjzb1 sjzf1 sjzf2 sjzf3a sjzf3b sjzf4 sjzf5 sjzf6 skb1a skb2a '
    'skb3 skf1a slf1 slf2 slf3 slout smf1 snb1 snb2 snf1 sob1 sof1 spf1 sqf1 sqf2 sqf3 sqf4 srout ss0out ss1m1f1 ss1out ss2m1f1 ss2m2f1 ss2out ss2y1f1 '
    'ss3a1f1 ss3k1f1 ss3m1f1 ss3m2f1 ss3out ss3y1f1 ss4a1f1 ss4b1 ss4b2 ss4b3 ss4hf1 ss4hf2 ss4k1f1 ss4m1f1 ss4m2f1 ss4out ss4y1f1 ss5b1a ss5b1b ss5b2 '
    'ss5b3 ss5f1a ss5f1b ss5f2a ss5f2b ss5f2c ss5f2d ss5f2e ss5f3 ss5f4 ss5f5 ss5ido ss5out sshm1f1 sshout tab1a tab1b taf1 taf2a taf2b taf3 tatop tbb1 '
    'tbf1a tbf1b tbf2 tbf3 tbf4 tbf5 tcf1 tcf2 tcf3 tcf4 tcf5 tdf1 tdf2 tdf3 tdf4 tdf5 tdout tef1 tef10 tef11 tef12 tef2 tef3a tef3b tef4a tef4b tef5 tef6 '
    'tef7 tef8 tef9 teout1 teout2 teout3 teout4 teout5 teout6 za1f1 za1f3 za1f4 za1f5 za1f6 za1f7 za1f8 za1f9 za2f1 za2f2 za2f4 za2f5 za2f6 za2f7 za2f8 '
    'za2f9 za3f1 za3f2 za3f3 za3f5 za3f6 za3f7 zaout '
    ).split()
# modele de sprite : « modele:placements:cartes » (placements dans les scripts, nombre de cartes)
_FREQ_SPRITES = ('0:200:63 1:105:42 2:54:17 3:167:44 4:40:19 5:121:37 6:5:2 7:115:47 8:20:10 9:195:67 10:80:33 11:144:45 12:57:15 13:18:5 14:3:2 15:216:36 16:6:2 '
    '17:112:24 18:98:32 19:18:9 20:36:11 21:75:29 22:69:27 23:23:8 24:16:4 25:3:1 26:78:18 27:49:12 28:34:9 29:38:9 30:40:13 31:58:23 32:6:3 33:50:13 '
    '34:46:16 35:27:13 36:47:18 37:12:6 38:14:4 39:19:9 40:3:1 41:2:2 42:1:1 43:25:4 44:42:17 45:12:5 46:22:6 47:32:9 48:17:4 49:2:2 50:13:2 53:4:1 54:5:1 '
    '55:4:3 56:7:3 57:35:10 58:11:5 59:7:4 60:3:1 61:11:7 62:3:2 63:9:6 64:7:7 65:9:3 66:8:8 67:33:13 68:9:7 69:10:4 70:7:2 71:30:12 72:4:2 73:3:2 74:5:4 '
    '76:3:3 77:15:9 78:10:3 79:3:2 80:5:1 81:11:4 82:3:1 83:13:3 85:1:1 100:11:9 103:11:9 106:10:8 109:15:9 112:16:11 115:17:11 118:7:7 121:14:13 124:14:12 '
    '127:16:11 130:1:1 131:5:3 132:5:3 133:19:8 134:5:3 135:11:5 136:2:1 137:2:1 138:5:1 139:14:5 140:10:4 141:3:2 142:5:1 143:5:4 144:1:1 145:8:7 146:2:1 '
    '147:2:1 148:11:4 149:17:8 150:9:2 151:17:5 152:9:6 153:6:4 154:7:3 155:1:1 156:1:1 157:7:4 158:2:1 159:24:10 160:6:3 161:2:2 162:1:1 164:1:1 165:8:2 '
    '166:1:1 167:1:1 168:5:1 169:14:1 170:14:1 171:4:3 172:48:21 173:1:1 174:7:7 175:13:4 176:4:4 177:1:1 178:2:1 179:2:1 180:17:7 181:2:1 182:7:5 183:4:1 '
    '184:1:1 185:10:6 186:2:1 187:1:1 188:2:2 189:15:5 190:3:3 191:1:1 192:1:1 195:1:1 196:2:1 197:1:1 199:4:2 200:2:1 201:1:1 202:1:1 203:3:3 204:4:1 '
    '210:1:1 211:1:1 212:1:1 213:1:1 215:37:27 216:1:1 217:1:1 221:1:1 298:2:1 299:3:2 300:1:1 '
    ).split()
# modeles de decor (nom sans numero de groupe) vus au moins 2 fois : « nom:occurrences:cartes »
_FREQ_OBJETS = ('akari1a:59:35 akari2a:887:257 akari3a:21:8 araiba1:58:57 bath1:3:3 bed1:197:103 bed2:37:14 bed2b:8:6 bigkdup1:20:20 bigtbl1:5:4 bigtubo01:2:2 '
    'bin01:18:8 bin02:12:7 bin03:8:5 bin04:14:6 bird1a:16:2 bird1b:16:2 bkdana1:30:20 bkhsr01a:11:6 bkhsr01b:8:5 book01:36:34 book02:3:3 btlmc1:4:4 '
    'btlsj2_e:2:1 btlsj2_n:2:1 btltdha3:2:1 btltdha3e:2:1 btltdha3n:2:1 catou1:6:1 cb2set:4:4 cb2tenj:4:4 cb2wt1a:4:4 cbhkr1:4:4 cbhkr1a:4:4 cbhkr2:4:4 '
    'cbhkr2a:4:4 cbotp01:9:2 cbtou1:2:1 cbtou2:2:1 ccctsr2:2:1 cchkr1:3:3 cchkr1a:3:3 cchkr1b:3:3 cchkr2:3:3 ccikzr4:2:1 cdentyu1b:3:1 cdentyu4:2:1 '
    'cdentyu5:6:1 cdhata1:10:4 cdhata2:2:1 cdienty1:2:1 cetou1:3:1 cetou3:4:1 cgoutfl:2:2 cgouthtk1:3:2 cgoutndk2:3:1 chdesk1:26:26 chhsr01:25:2 '
    'chhsr03:10:2 cigaito1:4:1 cikzr1:23:3 citou1:4:1 cj04a:3:3 cj2hkr:3:3 cj4hsr1:3:3 cj4hsr2:3:3 cj4wall:3:3 cjhkr1:3:3 cjhkr2a:9:6 cjhsr01:12:1 '
    'cjinhsr01:53:12 cjinhsrdrk01:23:5 ckenke1:3:3 ckf3f5hsr1:9:1 ckf3f5hsr2:8:1 ckf4hsr1:2:1 ckokgr1:5:1 ckokumo2:2:2 ckokumo2b:2:2 ckokumo3:2:2 '
    'ckotpkz1:15:2 cksykd1:4:1 clf3aev1:2:2 clf3cev1:2:2 clhsr:14:3 clingas1:5:3 cmf1bgas1:6:4 cmoutgs1:4:1 daiza1:2:2 danro1:8:8 danro2:8:8 dchkr1a:2:1 '
    'ddb2dr1:3:1 ddb2dr2:4:1 ddb5bsw1a:4:1 ddb5bsw1b:4:1 ddiwa1:14:3 deb1tk1a:2:2 deb2atk1a:2:2 deb2awt2a:2:2 deb2hsi:2:1 dekm1a:3:1 detksb1:13:3 dgel:8:4 '
    'dghkr1:2:1 dgzou1:13:5 dhdr:6:2 dhkb:14:2 dihkr1:21:5 dikor1:72:4 dikr1a:86:3 direiki5a:4:2 direiki6a:4:1 direiki7a:3:2 dish01:6:5 dkfire1:3:3 '
    'dkiwa1:97:3 dkoku:5:1 dlb1afl1:2:2 dlb1aw1a:2:2 dlb1aw2a:2:2 dlb4tk2c:7:3 dlb4tk2e:5:1 dlb5st2a:2:2 dlb5tk1a:2:2 dlb5w1a:2:2 dliwa1:31:4 dliwa2:40:3 '
    'dlkm1a:141:4 doku:5:1 doku00:69:14 doku01:68:14 dokuro01:18:3 door01:304:151 door02:10:8 door03:15:11 door04:39:20 door05:14:6 door06:21:5 dp5jmn:3:3 '
    'dp5yo1:3:3 dp5yo2:3:3 dp9iwa:3:3 dp9jmna:3:3 dp9kb1:3:3 dpb2biwa:2:2 dpb3fl1:8:1 dpb3km1:8:3 dpb4aie1:2:2 dpb4akg1:2:2 dpb4atuti1:2:2 dpb4b:2:2 '
    'dpb4bkg1:2:2 dpb4ido2:2:2 dpb4idowt1a:2:2 dpb6biwa1:48:2 dpogk1:2:2 dpojmn1:9:9 dpou1en:9:9 dpoyo1:3:3 dpoyo1a:2:2 dpoyo2:5:5 dr:2:1 dre:2:1 drn:2:1 '
    'e01:26:26 e02:6:6 e03:3:2 e6enke1:3:3 eho1:2:1 entbl1:66:44 eoku:5:1 estaisu1:2:2 gs1:3:3 gykset1:20:18 gykset1b:4:4 gyokuza1:31:19 gyokuza1b:4:4 '
    'gyokuza1e:2:1 gyokuza2:12:12 hachiue1:59:26 hachiue1ns:2:1 hachiue2:82:36 hachiue2ns:9:2 hachiue3:2:2 hacwl1c2:4:2 hacwl1d3:4:2 hacwl1e:4:2 '
    'hacwl1f:7:4 hacwl6:2:2 haka01:30:8 haka02:27:9 hammock:4:2 hana1:595:56 hana2:303:48 hana3:424:41 hana4:113:35 hana5:63:10 haoa1b:2:2 haoisi2b:2:2 '
    'haom1b12:2:2 haom2:2:2 haop1:2:2 haoutsb1c:2:2 haowtkr1:2:2 haoya1c:2:2 hashi:4:2 hasu2:4:2 hata1:38:13 hata2:38:6 hccyb1:2:2 hcky1c:2:2 hcokgr2d:2:1 '
    'hcokyn1:2:1 hcy1b1non:2:2 hhoutent:2:1 hikidashi1:49:32 hikidashi1b:49:32 hinomi1:65:29 hkr1:3:3 hkr1a:3:2 hkr2a:11:4 hmsasae:4:2 hondana1:99:51 '
    'hosikusa1:14:5 hsr:3:2 hsr01:333:53 hsr01ns:14:1 hsr2:4:3 hsrdrk01:18:5 hukuro1:29:22 ido:26:25 ido1:20:20 ido2:9:9 ido3:9:9 idokage1:10:9 '
    'idowt1:18:18 ikada1:16:14 isihsr01:62:6 isu1:199:23 isu2:398:118 isu2b:7:7 isu2c:4:2 isu3:7:4 iwa01:9:4 iwa2:3:1 kage:2:2 kage1:2:2 kage2:2:2 '
    'kage3:2:2 kage4:2:2 kakuzai1:2:2 kakuzai2:2:1 kamado1:49:47 kamado1b:2:2 kamado1c:4:4 kamado2:3:3 kb01:28:23 kb02:39:30 kb03:21:19 kb04:68:49 '
    'kb05:11:9 kdup1:238:184 kdup2:12:9 ken01:16:11 ken01b:41:15 kenjazou1:10:4 kibako01:101:31 kifk01a:4:4 kifkkr1:6:3 kifkkr2:9:3 kifkkr3:12:3 '
    'kifkkr4:9:3 kifkyk1:4:4 kikyu1:2:2 kira1a:5:3 kkd1:7:6 klkusa1:5:1 kobune01:2:1 kobune02:2:2 kougu01:8:8 ksm02a:8:4 ksr1:11:7 kumo1a:10:1 kwd01:8:3 '
    'kwd01ns:60:3 kyodai1:9:6 kyokai2f:4:4 lgyok1:3:3 lion:3:2 majinzou1:43:15 majinzou2:17:5 maki1:43:22 makura1:6:3 mamon1:2:1 maokgr1:3:1 maopshop1:4:3 '
    'mayuge1:7:4 mayuge2:4:4 mckusa01:5:3 mcout2hsr1:2:1 mfkyki1c:4:4 mgkusa01:33:13 mgmzou1:56:25 mgmzou2:17:9 mhoutfl:2:2 mhowtkr1:3:2 mhroten:2:1 '
    'mhsydi1:6:1 mihtk01:2:1 mihtk02:4:1 mikui:25:1 mim1out:2:2 mjopshop:2:1 mkoutgs1a:2:1 mldoku:2:2 mlfire1a:22:1 mlkmr1a:11:1 mlmkhn1:22:2 mlokg1:9:3 '
    'mlokgr1b:2:1 mlokgr2:4:2 mlom1d:2:2 mlom2b:2:2 mlout2b:2:2 mlowd1:9:1 mlowd2:2:1 mloy1b:2:2 mlsn2:2:2 mlyane:2:2 mmkadan:3:3 mmky1c:3:3 mmky1ckg:3:3 '
    'mmm1out:3:3 mmm1outkg:3:3 mmoiwa1:3:3 mmoutdai:3:3 mmoutrd:3:3 mmoutsb:3:3 mmoutsn:3:3 mmoutwt:3:3 mmw1:3:3 mmw1out:3:3 mmw1outkg:3:3 mmwtkr1:3:3 '
    'mmy1out:3:3 mmy2out:3:3 mmy2outkg:3:3 mnf1b1:2:2 mnf1n1:2:2 mnhkr1:3:1 mnopshop1:2:1 mnopshop2:2:1 mnouthsr:3:1 moopshop1:4:2 mpm1out:2:2 mpm2out:2:2 '
    'mpopshop1:2:2 mpoutfl:2:2 mpouthksk:2:2 mpoutiwa01:2:2 mpoutiwa02:2:2 mpoutiwa03:2:2 mpoutrd:2:2 mpoutsb:2:2 mpoutsbk01:2:1 mpoutsk1:2:2 mpoutsn1:2:2 '
    'mpy1out:2:2 mqkui:13:1 mqkusa01:2:2 mqoutkg:2:1 mroutkg:4:1 msaout:2:1 msgkb01:10:8 mshsr:10:1 msmout:2:1 msoutdai:2:1 msoutdai2:2:1 msoutkg1:5:1 '
    'mznfoot1:2:2 mznfoot2:2:2 nho1:2:1 noku:5:1 null1:18:8 nullido:2:2 oke01:11:6 okikb01:6:6 okikb02:12:12 okikb03:14:14 okikb04:5:5 omkekm2:2:2 '
    'ono01:12:7 ono01b:12:7 otama1:55:52 pdka0a:19:1 pdka1a:3:1 planter1:30:7 planter2:14:4 pond:13:7 pondwt:13:7 rope:8:4 rousoku1a:63:34 sakadana1:18:7 '
    'sekui:11:1 sfnm1a:3:3 sfune_l:3:3 sha01:6:3 ship_m:2:2 sibakusa1:1166:73 sigemi1:19:3 sigemi1ns:40:4 sjctl02:2:1 sjin1out:2:2 sjin2out:2:2 '
    'sjnakasu:2:2 sjoutfl3:2:2 sjoutsn:2:2 sjoutsn2:2:2 sjoutsn3:2:2 sjow2:2:2 sjsk:2:2 sjsk2:2:2 skev1:3:3 slhnk1a:102:6 slot4:17:2 snb1iwa1:16:4 '
    'snhkr2a:2:1 sohkr2a:4:1 sphkr2a:2:1 sqf4enke1:3:3 sqf4enke2:3:3 sqhkr1:2:1 sqhkr2a:6:1 srenke4a:2:2 srenke5a:5:3 sriwa2:5:2 sriwa3:6:2 ss1oike1:2:2 '
    'ss4a1f1:2:2 ss4m1f1:4:4 ss4m2f1:3:3 ss4m2f1sn:2:2 ss4ohtk1:4:4 ss4oie1:4:4 ss4oie2:3:3 ss4oie3:3:3 ss4oie4:2:2 ss4oike1:3:3 ss4ojyu1:2:2 ss4okgr1:4:3 '
    'ss4oop1:4:4 ss4owtkr1:5:5 ss4y1f1:3:3 ss4y1f1isi:2:2 ss5okgr1:5:1 ss5otou1:2:1 syokudai1:26:10 syokudai2:2:1 syorui1:2:2 taima1a:27:9 taima1a2:2:1 '
    'taima2a:47:13 tansu1:77:54 tansu1l:77:54 tansu1r:77:54 tansu2:26:10 tansu2l:26:10 tansu2r:26:10 taru01:232:68 tate01:7:7 tate01b:16:16 tbdaiza1:10:9 '
    'tbl1:147:109 tbox01:195:108 tbox02:195:108 tbtb1:11:10 tc2:3:3 tchkr1a:4:4 tchkr2a:4:4 tcsora2_dk:3:3 tctimt:3:3 tdkm1:16:4 teelv1a:8:6 tehsrkg1:6:1 '
    'teihsr1d:131:13 teihsr1e:164:7 teihsr1e4:18:5 teihsr1eg:14:7 teihsr3:8:3 teihsr4:38:5 teihsr4b:44:8 tekm1:52:3 teohsr1b:7:3 teohsr1b3:12:3 '
    'teohsr1b3b:6:2 teohsr1c:4:2 teohsr1c2:2:1 teohsr1c3:6:2 teohsr1c4:3:1 teohsr1c5:3:2 teohsr2b:45:4 teohsr2d:48:4 teohsr2e:27:3 teohsr2f:31:3 '
    'teohsr3c2:17:5 teohsr3c3:8:4 teohsr3c4:4:4 teohsr3c5:4:4 teohsr3c6:4:1 teohsr3c7:4:1 tetugo01:102:26 tizu01:3:3 towel1:8:5 trskb02:2:2 trskb03:4:4 '
    'trskb04:22:19 trskb05:3:3 ts1:7:2 tubo01:221:74 tumini01:8:2 turuhasi01:6:6 tuti01:40:6 wbed01:2:2 wd01:44:4 wd01b:298:35 wd01bns:353:25 wd01ns:191:7 '
    'wd02:355:34 wd02b:49:6 wd02bns:146:7 wd02ns:449:19 wd03ns:62:2 wdne01:1109:53 wdne02:906:59 wdoor01:84:34 wdoor02:8:4 wdoor03:16:7 wdoor04:208:83 '
    'wdoor04e:2:1 wdoor05:32:15 wdoor06:24:12 yamikusa1:5:1 yamikusa2:4:2 yasai01:80:8 yasi01:2:1 ybbell01:22:22 ymaka1a:2:1 yoroi01:15:15 yoroi02:77:27 '
    'za1f2:2:2 zakgr1:2:1 '
    ).split()
# === FIN GENERE ===

FREQ_SPRITES = {int(a): (int(b), int(c)) for a, b, c in (x.split(':') for x in _FREQ_SPRITES)}
FREQ_OBJETS = {n: (int(b), int(c)) for n, b, c in (x.rsplit(':', 2) for x in _FREQ_OBJETS)}
MODELES_3D = (158, 161, 162, 164, 166, 167, 169, 170, 192, 196, 197, 210, 211, 212, 213, 215)            # table de conversion du moteur, type 2 : volontairement sans libelle
FORME = re.compile(r"(?:Un|Une|Des) [a-zàâäçéèêëîïôöûùüœ'’-]+(?: [a-zàâäçéèêëîïôöûùüœ'’-]+)*")


class Etat:                                                                          # forme minimale d'un Etat du moteur
    def __init__(self, carte, partie): self.carte, self.partie = carte, partie


class TestSource(unittest.TestCase):
    def test_exemples_sprites(self):
        att = {0: 'Un jeune homme', 1: 'Une jeune femme', 2: 'Un homme', 3: 'Une vieille femme', 4: 'Une femme', 5: 'Un vieil homme', 7: 'Un garçon', 8: 'Une petite fille',
               15: 'Un soldat', 21: 'Un prêtre', 22: 'Une religieuse', 36: 'Un roi', 43: 'Une elfe', 44: 'Un chien', 45: 'Un chat', 48: 'Un cheval', 50: 'Une vache', 83: 'Un cercueil',
               130: 'Un gluant', 165: 'Un monstre', 180: 'Un gluant'}
        for k, v in att.items(): self.assertEqual(L.libelle_source(k), v, k)

    def test_formes_d_identifiant(self):
        ref = L.libelle_source(19); self.assertEqual(ref, 'Un guerrier')
        for m in ('h019', 'H019', '19', ' h19 ', 4096 + 19, 19.0, {'id': 19, 'pos': (0, 0, 0)}, {'id': 4096 + 19}):
            self.assertEqual(L.libelle_source(m), ref, repr(m))
        class Num:                                                                   # entier de type numpy
            def __int__(self): return 19
            def __eq__(self, o): return o == 19
            __hash__ = None
        self.assertEqual(L.libelle_source(Num()), ref)
        for m in (None, '', 'inconnu', 99999, -3, 12.5, True, False, object(), [], {}, 'h', 'h99999'):
            self.assertIsNone(L.libelle_source(m), repr(m))

    def test_exemples_objets(self):
        att = {'tubo01': 'Une jarre', '012_tubo01': 'Une jarre', 'Taru01(Clone)': 'Un tonneau', 'taruwr01a': 'Un tonneau', '007_tbox01': 'Un coffre', 'tbox02': 'Un coffre',
               'hondana1': 'Une étagère', 'bkdana1': 'Une étagère', 'tansu1l': 'Une commode', 'tansu2': 'Une commode', 'hikidashi1b': 'Un tiroir', 'kibako01': 'Une caisse',
               'ido': 'Un puits', 'ido3': 'Un puits', 'dpb4ido2': 'Un puits', 'kb04': 'Un panneau', 'okikb03': 'Un panneau', 'bed1': 'Un lit', 'wbed01b': 'Un lit', 'door01': 'Une porte',
               'wdoor04': 'Une porte', 'kamado1': 'Un fourneau', 'book01': 'Un livre', 'majinzou1': 'Une statue', 'gyokuza1': 'Un trône', 'isu2': 'Une chaise', 'tbl1': 'Une table'}
        for k, v in att.items(): self.assertEqual(L.libelle_source(k), v, k)
        for k in ('hana1', 'sibakusa1', 'akari2a', 'wdne1', 'idowt1', 'idokage1', 'hsr01', 'teihsr1e', 'slotou1', 'plall01_d', 'zzz', 'tubo'):
            self.assertIsNone(L.libelle_source(k), k)

    def test_forme_des_libelles(self):
        tous = {l for l, _, _ in L._GROUPES_SPRITES} | {l for _, l, _ in L._REGLES_OBJETS}
        for l in tous:
            self.assertRegex(l, FORME); self.assertEqual(l, l.strip()); self.assertNotIn('  ', l)
        for _, _, c in L._REGLES_OBJETS: self.assertIn(c, 'CS')
        for _, c, _ in L._GROUPES_SPRITES: self.assertIn(c, 'CS')

    def test_pas_de_doublon_incoherent(self):
        vus = {}
        for lib, c, ids in L._GROUPES_SPRITES:
            for i in ids: self.assertNotIn(i, vus, 'sprite %d dans deux groupes (%s, %s)' % (i, vus.get(i), lib)); vus[i] = lib
        self.assertFalse(set(vus) & set(MODELES_3D), 'les modeles 3D (type 2) ne portent pas de libelle')
        for nom in FREQ_OBJETS:                                                      # un nom de decor ne correspond qu'a UN motif (ou a aucun)
            res = {lib for rx, lib, _ in L._REGLES_OBJETS if rx.fullmatch(nom)}
            self.assertLessEqual(len(res), 1, '%s : %s' % (nom, res))
        art = {'Un': 'm', 'Une': 'f', 'Des': 'p'}
        for l in set(vus.values()): self.assertIn(l.split()[0], art)

    def test_modeles_frequents(self):
        sans = [(n, k) for k, (n, _) in sorted(FREQ_SPRITES.items(), key=lambda kv: -kv[1][0]) if k not in MODELES_3D and L.libelle_source(k) is None]
        self.assertEqual(sans, [], 'modeles de personnages sans libelle (placements, modele)')
        for k in MODELES_3D: self.assertIsNone(L.libelle_source(k), k)
        top = sorted(FREQ_SPRITES, key=lambda k: -FREQ_SPRITES[k][0])[:40]
        for k in top:
            if k not in MODELES_3D: self.assertIsNotNone(L.libelle_source(k), k)

    def test_confiance(self):
        self.assertEqual(L.confiance_source(1), 'certain'); self.assertEqual(L.confiance_source(0), 'suppose')
        self.assertEqual(L.confiance_source('tbox01'), 'certain'); self.assertEqual(L.confiance_source('tubo01'), 'suppose')
        self.assertIsNone(L.confiance_source(99999)); self.assertIsNone(L.confiance_source(None))


class TestLieu(unittest.TestCase):
    def test_exemples(self):
        att = {'caf1': 'Château de Bastione', 'caf2a': 'Château de Bastione', 'haout': 'Bastione', 'maout': 'Strattbourg', 'mak1f1': 'Strattbourg', 'mam1f1': 'Strattbourg', 'maido': 'Strattbourg',
               'may1f1': 'Strattbourg', 'cbf1': 'Château de Zamoksva', 'cef1a': 'Palais de Lord Lionel', 'cjf2a': 'Palais du démon', 'ckout': 'Château de Zénithia', 'smf1': 'Havre céleste',
               'dpb1a': 'Chapelle du Coteau', 'dbb1a': 'Grotte', 'tef1': 'Tour', 'tatop': 'Tour', 'cccf2': 'Château', 'mgout1': 'Ville', 'sbout': 'Village', 'ss1out': 'Chez Hoffman',
               'monde': 'Monde', 'Monde': 'Monde', 'field': 'Monde', 'carte8_caf1.pkl': 'Château de Bastione', 'map/maout': 'Strattbourg', 'MAOUT': 'Strattbourg'}
        for k, v in att.items(): self.assertEqual(L.libelle_lieu(k), v, k)
        self.assertEqual(L.libelle_lieu(Etat('maout', 12)), 'Strattbourg')
        self.assertEqual(L.libelle_lieu(Etat('maout', 0xe)), 'Monde', 'sur la carte du monde Etat.carte garde la derniere ville')
        self.assertEqual(L.libelle_lieu(Etat(None, 12)), None)
        self.assertEqual(L._de('Azimut'), "d'Azimut"); self.assertEqual(L._de('Bastione'), 'de Bastione')

    def test_sans_lieu(self):
        for k in ('btl_pl_d', 'ev01', 'fk01', 'za1f1', 'zaout', 'sdf1', 'saf1', 'zz99', '', None, 123, 'a', '??', object()):
            self.assertIsNone(L.libelle_lieu(k), repr(k))

    def test_formes(self):
        for c in CARTES:
            lib = L.libelle_lieu(c)
            if lib is None: continue
            self.assertTrue(lib[:1].isupper() and not lib.endswith(' ') and ' · ' not in lib, (c, lib))
            self.assertEqual(L.libelle_lieu(c), L.libelle_lieu(c.upper()))

    def test_regle_unique_par_lieu(self):
        par = collections.defaultdict(set)
        for c in CARTES: par[c[:2]].add(L.libelle_lieu(c))
        for p, s in par.items(): self.assertEqual(len(s), 1, '%s : %s' % (p, s))
        for c in ('mak1f1', 'mam1f1', 'maido', 'may1f1', 'mai1f1', 'map1b1', 'maout'): self.assertEqual(L.libelle_lieu(c), 'Strattbourg')


class TestImport(unittest.TestCase):
    def test_import_instantane_et_leger(self):
        code = ("import sys, time; sys.path.insert(0, %r); t = time.perf_counter(); import libelles; d = time.perf_counter() - t; "
                "lourds = [m for m in ('numpy', 'unicorn', 'pyglet', 'PIL', 'UnityPy') if m in sys.modules]; print(d, lourds)") % os.path.join(RACINE, 'dq4_pc')
        d, lourds = subprocess.run([sys.executable, '-c', code], capture_output=True, text=True, check=True).stdout.split(' ', 1)
        self.assertLess(float(d), 0.1, 'import en %s s' % d); self.assertEqual(lourds.strip(), '[]')


class TestCouverture(unittest.TestCase):
    def test_couverture(self):
        tot = sum(n for n, _ in FREQ_SPRITES.values()); ok = {'C': 0, 'S': 0}; sans = collections.Counter(); par_lib = collections.Counter()
        for k, (n, _) in FREQ_SPRITES.items():
            v = L._SPRITES.get(k)
            if v: ok[v[1]] += n; par_lib[v[0]] += n
            else: sans[k] = n
        nom = sum(ok.values())
        print('\nPERSONNAGES : %d placements, %d modeles ; nommes %d (%.1f %%) dont certains %d, supposes %d ; modeles 3D / non nommes : %d placements (%s)' % (
            tot, len(FREQ_SPRITES), nom, 100.0 * nom / tot, ok['C'], ok['S'], sum(sans.values()), ' '.join('%d:%d' % kv for kv in sorted(sans.items()))))
        print('  libelles les plus frequents : ' + ', '.join('%s %d' % kv for kv in par_lib.most_common(8)))
        self.assertGreaterEqual(nom / tot, 0.97)
        toto = sum(n for n, _ in FREQ_OBJETS.values()); par = collections.Counter(); nonn = collections.Counter()
        for k, (n, _) in FREQ_OBJETS.items():
            lib = L.libelle_source(k)
            if lib: par[lib] += n
            else: nonn[re.sub(r'\d+[a-z]?\d*$', '', k)] += n
        print('DECORS : %d occurrences (modeles vus au moins 2 fois), %d reconnues en %d libelles : %s' % (toto, sum(par.values()), len(par), ', '.join('%s %d' % kv for kv in par.most_common(14))))
        print('  non nommes les plus frequents (decor sans message : fleurs, herbe, lumieres, murs, portes...) : ' + ' '.join('%s:%d' % kv for kv in nonn.most_common(18)))
        for lib in ('Une jarre', 'Un tonneau', 'Un coffre', 'Une étagère', 'Un panneau', 'Un lit'): self.assertGreater(par[lib], 0, lib)
        cl = collections.Counter(L._lieu(c)[1] for c in CARTES); par_c = collections.defaultdict(list)
        for c in CARTES: par_c[L._lieu(c)[1]].append(c[:2])
        print('LIEUX : %d cartes ; nom officiel %d, derive (Château de X ou exception) %d, generique %d, sans lieu %d' % (len(CARTES), cl['officiel'], cl['derive'], cl['generique'], cl[None]))
        print('  prefixes sans lieu : ' + ' '.join(sorted(set(par_c[None]))))
        print('  prefixes generiques : ' + ' '.join(sorted(set(par_c['generique']))))
        self.assertEqual({c[:2] for c in CARTES if c[0] in 'cdtm' and L.libelle_lieu(c) is None}, set())


if __name__ == '__main__':
    unittest.main()
