"""En-tete de la mise en page : planches d'icones (PartsInfo), couleurs de texte, parametres de langue, decalage « appuye » des boutons.
Usage : python entete.py sortie.json"""
import json, struct, sys
import scene as S, runall2 as R, menusys as M
T = S.T
# Color.cyan / Color.green : proprietes natives d'Unity (absentes de l'emulation) -> valeurs standard d'Unity
GENERATION = 3      # numero de version de la mise en page : 2 = langue reglee (GetLangages) ; 3 = argument des Make_* = rang dans le groupe de types (type 22 : bouton Mode) ; lancer_dq4.bat refait un fichier de generation plus ancienne
COULEURS_UNITY = {5: [0.0, 1.0, 1.0, 1.0], 6: [0.0, 1.0, 0.0, 1.0]}


def entete():
    st = R.statics(T, 'MenuParts')
    infos = []
    for i in T.infos:
        W = i['W']; ps = i['ps']
        infos.append(dict(tex=i['texNo'], sx=i['sx'], sy=i['sy'], ps=ps, dps=i['dps'], W=W, uvsize=ps / W, startV=i['sy'] / W, widthNum=W // ps, startNo=i['sx'] // ps))
    cl = T.u(st + 0x70, 8); n = T.u(cl + 0x18, 8)
    colors = [list(struct.unpack('<4f', bytes(T.uc.mem_read(cl + 0x20 + 16 * k, 16)))) for k in range(n)]
    for k, c in enumerate(colors):
        ok = all(0.0 <= x <= 1.0 and (x == 0.0 or x > 1e-6) for x in c) and c[3] == 1.0
        if not ok and k in COULEURS_UNITY: colors[k] = COULEURS_UNITY[k]
    sz, line, dy, hiro, nameb = struct.unpack('<5f', bytes(T.uc.mem_read(st + 8, 20)))
    k = M.klass_of(T, 'MenuParts.IButton'); T.run(0xd04310)
    pu = struct.unpack('<2f', bytes(T.uc.mem_read(T.u(k + 0xb8, 8), 8)))
    return dict(info=infos, colors=colors, lang=dict(size=sz, line=line, dy=dy, hiro=hiro, nameBase=nameb), pushed=list(pu), W=450, nTypes=len(R.tbl), gen=GENERATION)


if __name__ == '__main__':
    json.dump(entete(), open(sys.argv[1], 'w'))
