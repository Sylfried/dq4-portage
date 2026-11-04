"""Duree d'un cycle jour / nuit de la carte du monde, en secondes reelles NOMINALES : le vrai moteur est avance avec la vraie horloge de la visionneuse (vitesse_combat.avancer, 60 images par seconde, facteur de marche f) mais avec une horloge simulee (la charge de la machine ne compte pas)."""
import sys, struct, random, json
sys.path.insert(0,'/tmp/sp45'); sys.path.insert(0,'/home/claude/wt45-sprites/dq4_pc')
import h45; from dq4_pc.noyau import moteur as MO; from dq4_pc.combat import vitesse_combat as VC
def cycle(f, cycles=1.0, graine=1, tag='c'):
    m=h45.nouveau('cyc%s'%tag); m.charger_sauvegarde(4)
    for i in range(700):
        m.step(0,0)
        if i>=130 and 0 in m.etat.sprites: break
    c=m.core; G=c.export('_ZN6status7g_StageE'); enc=c.call(c.export('_ZN7Encount12getSingletonEv'))
    rd=lambda: struct.unpack('<i', c.mem(G+0xcc,4))[0]
    DIRS=(MO.HAUT,MO.DROITE,MO.BAS,MO.GAUCHE); rnd=random.Random(graine)
    BOX=(2300,2480,342,362); st=dict(d=1,sans=0,prev=tuple(m.etat.sprites[0]['pos']),t=rd(),gagne=0,pas=0,marche=0)
    t_depart=st['t']
    def faire_pas():
        c.mem_w(enc+0x18,b'\x00')                      # (mesure) pas de rencontre : la carte du monde sans combat
        d=DIRS[st['d']]; m.step(d,d); st['pas']+=1
        pos=tuple(m.etat.sprites[0]['pos']); t=rd()
        st['gagne']+= (t-st['t'])%3392; 
        if t!=st['t']: st['marche']+=1
        st['t']=t
        if pos==st['prev']:
            st['sans']+=1
            if st['sans']>=3: st['d']=rnd.randrange(4); st['sans']=0
        else: st['sans']=0
        st['prev']=pos
        x,y=pos[0],pos[1]
        if not (BOX[0]<x<BOX[2-0+0-0] if False else (BOX[0]<x<BOX[1] and BOX[2]<y<BOX[3])):
            cx,cy=(BOX[0]+BOX[1])/2,(BOX[2]+BOX[3])/2
            st['d'] = (1 if x<cx else 3) if abs(x-cx)/(BOX[1]-BOX[0]) > abs(y-cy)/(BOX[3]-BOX[2]) else (2 if y<cy else 0)
        return True
    acc=0.0; temps=0.0; dt=1/60.0; n_aff=0; jal=[]
    while st['gagne']<3392*cycles and n_aff<60*400:
        acc,_,_=VC.avancer(acc, dt, f, faire_pas, lambda: 0.0)       # horloge simulee : jamais de coupure de budget
        n_aff+=1; temps=n_aff*dt
        if (n_aff%60==0): jal.append((round(temps,2), st['gagne']))
    return dict(f=f, secondes=round(temps,2), images_moteur=st['pas'], images_en_marche=st['marche'], gagne=st['gagne'], cycles=cycles, fin_t=st['t'], t_depart=t_depart, jalons=jal[:3])
if __name__=='__main__':
    f=float(sys.argv[1]); r=cycle(f, float(sys.argv[2]) if len(sys.argv)>2 else 1.0, tag=sys.argv[1]); print(json.dumps(r), flush=True)
