"""Duree d'un cycle jour / nuit de la carte du monde, en secondes reelles NOMINALES : le vrai moteur est avance avec la vraie horloge de la visionneuse (battle_speed.avancer, 60 images par seconde, facteur de marche f) mais avec une horloge simulee (la charge de la machine ne compte pas)."""
import sys, struct, random, json
sys.path.insert(0,'/tmp/sp45'); sys.path.insert(0,'/home/claude/wt45-sprites/dq4_pc')
import h45; from dq4_pc.core import engine as ENGINE; from dq4_pc.battle import battle_speed as VC
def cycle(f, cycles=1.0, seed=1, tag='c'):
    m=h45.new('cyc%s'%tag); m.load_save(4)
    for i in range(700):
        m.step(0,0)
        if i>=130 and 0 in m.state.sprites: break
    c=m.core; G=c.export('_ZN6status7g_StageE'); enc=c.call(c.export('_ZN7Encount12getSingletonEv'))
    rd=lambda: struct.unpack('<i', c.mem(G+0xcc,4))[0]
    DIRS=(ENGINE.UP,ENGINE.RIGHT,ENGINE.DOWN,ENGINE.LEFT); rnd=random.Random(seed)
    BOX=(2300,2480,342,362); st=dict(d=1,sans=0,prev=tuple(m.state.sprites[0]['pos']),t=rd(),gagne=0,pas=0,marche=0)
    t_initial=st['t']
    def do_step():
        c.mem_w(enc+0x18,b'\x00')                      # (mesure) pas de rencontre : la carte du monde sans combat
        d=DIRS[st['d']]; m.step(d,d); st['pas']+=1
        pos=tuple(m.state.sprites[0]['pos']); t=rd()
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
    acc=0.0; clock=0.0; dt=1/60.0; n_shown=0; jal=[]
    while st['gagne']<3392*cycles and n_shown<60*400:
        acc,_,_=VC.advance_time(acc, dt, f, do_step, lambda: 0.0)       # horloge simulee : jamais de coupure de budget
        n_shown+=1; clock=n_shown*dt
        if (n_shown%60==0): jal.append((round(clock,2), st['gagne']))
    return dict(f=f, seconds=round(clock,2), images_moteur=st['pas'], images_en_marche=st['marche'], gagne=st['gagne'], cycles=cycles, fin_t=st['t'], t_initial=t_initial, jalons=jal[:3])
if __name__=='__main__':
    f=float(sys.argv[1]); r=cycle(f, float(sys.argv[2]) if len(sys.argv)>2 else 1.0, tag=sys.argv[1]); print(json.dumps(r), flush=True)
