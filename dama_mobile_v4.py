"""
DAMA MODE — Mobile Edition v4
Brazilian Draughts | Kivy + Full v4 Ultimate Engine

Same engine as desktop v4:
  PVS + LMR + Null Move + IID + Futility + Delta + Counter + Repetition

HOW TO RUN ON LAPTOP (test first):
  pip install kivy[base]
  python dama_mobile_v4.py

HOW TO BUILD APK:
  Rename this file to main.py
  Use the build.yml provided
"""

import random, time, threading
from collections import defaultdict
from kivy.app import App
from kivy.uix.widget import Widget
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.popup import Popup
from kivy.graphics import Color, Ellipse, Rectangle, Line
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.metrics import dp

# ═══════════════════════════════════════════════════════════
#  V4 BITBOARD ENGINE  (full strength — identical to desktop)
# ═══════════════════════════════════════════════════════════
sq_map = []
rc_sq  = {}
for _r in range(8):
    for _c in range(8):
        if (_r+_c)%2 == 1:
            rc_sq[(_r,_c)] = len(sq_map)
            sq_map.append((_r,_c))

DIRS = [(-1,-1),(-1,1),(1,-1),(1,1)]
step_t=[[-1]*4 for _ in range(32)]
jover =[[-1]*4 for _ in range(32)]
jland =[[-1]*4 for _ in range(32)]
krays =[[] for _ in range(32)]
NEIGHBORS=[0]*32

for _i,(_r,_c) in enumerate(sq_map):
    _rays=[]
    for _d,(_dr,_dc) in enumerate(DIRS):
        _nr,_nc=_r+_dr,_c+_dc
        if 0<=_nr<8 and 0<=_nc<8:
            step_t[_i][_d]=rc_sq[(_nr,_nc)]
            _lr,_lc=_r+2*_dr,_c+2*_dc
            if 0<=_lr<8 and 0<=_lc<8:
                jover[_i][_d]=rc_sq[(_nr,_nc)]
                jland[_i][_d]=rc_sq[(_lr,_lc)]
        _ray=[]
        _nr2,_nc2=_r+_dr,_c+_dc
        while 0<=_nr2<8 and 0<=_nc2<8:
            _ray.append(rc_sq[(_nr2,_nc2)])
            _nr2+=_dr; _nc2+=_dc
        _rays.append(_ray)
    krays[_i]=_rays
    m=0
    for _dr,_dc in DIRS:
        _nr,_nc=_r+_dr,_c+_dc
        if 0<=_nr<8 and 0<=_nc<8:
            _s=rc_sq.get((_nr,_nc),-1)
            if _s>=0: m|=(1<<_s)
    NEIGHBORS[_i]=m

LPROMO=sum(1<<i for i,(r,c) in enumerate(sq_map) if r==0)
DPROMO=sum(1<<i for i,(r,c) in enumerate(sq_map) if r==7)
CENTER=sum(1<<i for i,(r,c) in enumerate(sq_map) if 2<=r<=5 and 2<=c<=5)
INNER =sum(1<<i for i,(r,c) in enumerate(sq_map) if 3<=r<=4 and 3<=c<=4)
EDGE  =sum(1<<i for i,(r,c) in enumerate(sq_map) if c in(0,7))
BACK_L=sum(1<<i for i,(r,c) in enumerate(sq_map) if r==7)
BACK_D=sum(1<<i for i,(r,c) in enumerate(sq_map) if r==0)

POS_L=[0]*32; POS_D=[0]*32; POS_K=[0]*32; POS_KE=[0]*32
for i,(r,c) in enumerate(sq_map):
    e=-6 if c in(0,7) else(-2 if c in(1,6) else 0)
    cen=8 if 2<=r<=5 and 2<=c<=5 else 0
    inn=4 if 3<=r<=4 and 3<=c<=4 else 0
    POS_L[i]=(7-r)*5+cen+inn+e+(4 if r==6 else 0)+(2 if r==5 else 0)
    POS_D[i]=r*5+cen+inn+e+(4 if r==1 else 0)+(2 if r==2 else 0)
    POS_K[i]=(14 if 3<=r<=4 and 3<=c<=4 else 10 if 2<=r<=5 and 2<=c<=5
              else 5 if 1<=r<=6 and 1<=c<=6 else 0)+e
    POS_KE[i]=(18 if 3<=r<=4 and 3<=c<=4 else 14 if 2<=r<=5 and 2<=c<=5
               else 7 if 1<=r<=6 else 0)+e

random.seed(0xDA2A2025)
ZOB=[[random.getrandbits(64) for _ in range(4)] for _ in range(32)]
ZOB_TURN=random.getrandbits(64)

def zob(lp,dp,lk,dk,turn):
    h=0
    b=lp
    while b: sq=(b&-b).bit_length()-1; h^=ZOB[sq][0]; b&=b-1
    b=dp
    while b: sq=(b&-b).bit_length()-1; h^=ZOB[sq][1]; b&=b-1
    b=lk
    while b: sq=(b&-b).bit_length()-1; h^=ZOB[sq][2]; b&=b-1
    b=dk
    while b: sq=(b&-b).bit_length()-1; h^=ZOB[sq][3]; b&=b-1
    if turn==1: h^=ZOB_TURN
    return h

def pc(x): return bin(x).count('1')

def init_st():
    lp=sum(1<<rc_sq[(r,c)] for r in range(5,8) for c in range(8) if (r+c)%2==1)
    dp=sum(1<<rc_sq[(r,c)] for r in range(3)   for c in range(8) if (r+c)%2==1)
    return lp,dp,0,0

def count_p(st): lp,dp,lk,dk=st; return pc(lp)+pc(lk),pc(dp)+pc(dk)

def gen_chains(lp,dp,lk,dk,turn,sq,excl):
    opp=(dp|dk) if turn==0 else (lp|lk)
    ownk=lk if turn==0 else dk
    occ=lp|dp|lk|dk; king=bool(ownk>>sq&1); res=[]
    if king:
        for ray in krays[sq]:
            found=-1
            for rsq in ray:
                if excl>>rsq&1: break
                if opp>>rsq&1:
                    if found>=0: break
                    found=rsq
                elif occ>>rsq&1: break
                else:
                    if found>=0:
                        ne=excl|(1<<found)
                        sub=gen_chains(lp,dp,lk,dk,turn,rsq,ne)
                        if sub:
                            for fs,cm,st2 in sub: res.append((fs,cm|(1<<found),[(sq,rsq,found)]+st2))
                        else: res.append((rsq,1<<found,[(sq,rsq,found)]))
                        break
    else:
        for d in range(4):
            ov=jover[sq][d]; la=jland[sq][d]
            if ov<0 or la<0: continue
            if excl>>ov&1 or not(opp>>ov&1) or occ>>la&1: continue
            ne=excl|(1<<ov)
            sub=gen_chains(lp,dp,lk,dk,turn,la,ne)
            if sub:
                for fs,cm,st2 in sub: res.append((fs,cm|(1<<ov),[(sq,la,ov)]+st2))
            else: res.append((la,1<<ov,[(sq,la,ov)]))
    return res

def all_max_chains(lp,dp,lk,dk,turn):
    own=(lp|lk) if turn==0 else (dp|dk)
    best=[]; mx=0; b=own
    while b:
        sq=(b&-b).bit_length()-1
        for ch in gen_chains(lp,dp,lk,dk,turn,sq,0):
            n=len(ch[2])
            if n>mx: mx=n; best=[ch]
            elif n==mx: best.append(ch)
        b&=b-1
    return best

def apply_cap(lp,dp,lk,dk,turn,ch):
    fs,cap,steps=ch; fr=steps[0][0]
    was_k=(lk>>fr&1) if turn==0 else (dk>>fr&1)
    if turn==0: lp&=~(1<<fr); lk&=~(1<<fr)
    else:       dp&=~(1<<fr); dk&=~(1<<fr)
    lp&=~cap; dp&=~cap; lk&=~cap; dk&=~cap
    if turn==0:
        if was_k or(LPROMO>>fs&1): lk|=(1<<fs)
        else: lp|=(1<<fs)
    else:
        if was_k or(DPROMO>>fs&1): dk|=(1<<fs)
        else: dp|=(1<<fs)
    return lp,dp,lk,dk

def apply_mv(lp,dp,lk,dk,turn,fr,to):
    if turn==0:
        if lk>>fr&1: lk=(lk&~(1<<fr))|(1<<to)
        else:
            lp=(lp&~(1<<fr))|(1<<to)
            if LPROMO>>to&1: lp&=~(1<<to); lk|=(1<<to)
    else:
        if dk>>fr&1: dk=(dk&~(1<<fr))|(1<<to)
        else:
            dp=(dp&~(1<<fr))|(1<<to)
            if DPROMO>>to&1: dp&=~(1<<to); dk|=(1<<to)
    return lp,dp,lk,dk

def gen_simple(lp,dp,lk,dk,turn):
    own=(lp|lk) if turn==0 else (dp|dk)
    ownk=lk if turn==0 else dk
    occ=lp|dp|lk|dk; fwd=[0,1] if turn==0 else [2,3]
    mvs=[]; b=own
    while b:
        sq=(b&-b).bit_length()-1
        if ownk>>sq&1:
            for ray in krays[sq]:
                for rsq in ray:
                    if occ>>rsq&1: break
                    mvs.append((sq,rsq))
        else:
            for d in fwd:
                t=step_t[sq][d]
                if t>=0 and not(occ>>t&1): mvs.append((sq,t))
        b&=b-1
    return mvs

def legal(lp,dp,lk,dk,turn):
    ch=all_max_chains(lp,dp,lk,dk,turn)
    if ch: return True,ch
    return False,[(fr,to) for fr,to in gen_simple(lp,dp,lk,dk,turn)]

def evaluate(lp,dp,lk,dk):
    lc=pc(lp); dc=pc(dp); lkc=pc(lk); dkc=pc(dk)
    tl=lc+lkc; td=dc+dkc
    if tl==0: return 100000
    if td==0: return -100000
    total=tl+td; endgame=total<=8; deep_end=total<=4
    diff=(dc*100+dkc*330)-(lc*100+lkc*330)
    if diff>0: diff+=min(diff//4,60)
    elif diff<0: diff-=min(-diff//4,60)
    s=diff
    kt=POS_KE if endgame else POS_K
    b=lp
    while b: sq=(b&-b).bit_length()-1; s-=POS_L[sq]; b&=b-1
    b=dp
    while b: sq=(b&-b).bit_length()-1; s+=POS_D[sq]; b&=b-1
    b=lk
    while b: sq=(b&-b).bit_length()-1; s-=kt[sq]; b&=b-1
    b=dk
    while b: sq=(b&-b).bit_length()-1; s+=kt[sq]; b&=b-1
    _,lm=legal(lp,dp,lk,dk,0); _,dm=legal(lp,dp,lk,dk,1)
    s+=(len(dm)-len(lm))*7
    if len(lm)==0: s+=800
    if len(dm)==0: s-=800
    s+=pc(dp&BACK_D)*8-pc(lp&BACK_L)*8
    s-=pc(lk&EDGE)*10; s+=pc(dk&EDGE)*10
    s-=pc(lp&EDGE)*3;  s+=pc(dp&EDGE)*3
    b=dp
    while b:
        sq=(b&-b).bit_length()-1; s+=pc(NEIGHBORS[sq]&(dp|dk))*3; b&=b-1
    b=lp
    while b:
        sq=(b&-b).bit_length()-1; s-=pc(NEIGHBORS[sq]&(lp|lk))*3; b&=b-1
    b=dp
    while b:
        sq=(b&-b).bit_length()-1; r2,_=sq_map[sq]
        if r2>=6: s+=25
        elif r2>=5: s+=14
        elif r2>=4: s+=6
        b&=b-1
    b=lp
    while b:
        sq=(b&-b).bit_length()-1; r2,_=sq_map[sq]
        if r2<=1: s-=25
        elif r2<=2: s-=14
        elif r2<=3: s-=6
        b&=b-1
    if endgame:
        s+=(pc(dk&CENTER)-pc(lk&CENTER))*12
        s+=(pc(dk&INNER)-pc(lk&INNER))*8
        if tl==1 and lkc==1 and td>=2:
            b=lk; sq=(b&-b).bit_length()-1; r2,c2=sq_map[sq]
            s+=(min(r2,7-r2)+min(c2,7-c2))*18
        if td==1 and dkc==1 and tl>=2:
            b=dk; sq=(b&-b).bit_length()-1; r2,c2=sq_map[sq]
            s-=(min(r2,7-r2)+min(c2,7-c2))*18
    if dkc>=1 and dc>=1 and lkc==0: s+=50
    if lkc>=1 and lc>=1 and dkc==0: s-=50
    return s

_TT={}; _TT_SZ=1<<21
_EX,_LO,_UP=0,1,2
_hist=defaultdict(int); _killers=[[None,None] for _ in range(64)]
_counters={}; _rep=defaultdict(int); _stop_ai=False

def _lmr(depth,idx,is_cap):
    if is_cap or depth<3 or idx<2: return 0
    if idx<5: return 1
    if idx<10: return 2
    return min(3,depth//3)

def _ttg(h,depth,alpha,beta):
    e=_TT.get(h%_TT_SZ)
    if not e or e[0]!=h: return None,None
    _,ed,es,ef,em=e
    if ed>=depth:
        if ef==_EX: return es,em
        if ef==_LO and es>=beta: return es,em
        if ef==_UP and es<=alpha: return es,em
    return None,em

def _ttp(h,d,s,f,mv):
    idx=h%_TT_SZ; e=_TT.get(idx)
    if not e or e[0]!=h or e[1]<=d: _TT[idx]=(h,d,s,f,mv)

def _qsc(lp,dp,lk,dk,turn,alpha,beta,qd):
    if _stop_ai: return 0
    sp=evaluate(lp,dp,lk,dk)
    if turn==1:
        if sp>=beta: return beta
        if sp+400<alpha: return alpha
        alpha=max(alpha,sp)
    else:
        if sp<=alpha: return alpha
        if sp-400>beta: return beta
        beta=min(beta,sp)
    if qd==0: return sp
    chs=all_max_chains(lp,dp,lk,dk,turn)
    if not chs: return sp
    chs.sort(key=lambda ch:len(ch[2])*500+pc(ch[1])*100,reverse=True)
    for ch in chs:
        if _stop_ai: return 0
        nlp,ndp,nlk,ndk=apply_cap(lp,dp,lk,dk,turn,ch)
        s2=_qsc(nlp,ndp,nlk,ndk,1-turn,alpha,beta,qd-1)
        if turn==1:
            if s2>=beta: return beta
            alpha=max(alpha,s2)
        else:
            if s2<=alpha: return alpha
            beta=min(beta,s2)
    return alpha if turn==1 else beta

def _srch(lp,dp,lk,dk,turn,depth,alpha,beta,null_ok=True,ply=0,pmv=None):
    global _stop_ai,_hist,_killers,_counters,_rep
    if _stop_ai: return 0,None
    h=zob(lp,dp,lk,dk,turn); _rep[h]+=1
    if _rep[h]>=3: _rep[h]-=1; return 0,None
    tt_s,tt_mv=_ttg(h,depth,alpha,beta)
    if tt_s is not None: _rep[h]-=1; return tt_s,tt_mv
    is_cap,mvs=legal(lp,dp,lk,dk,turn)
    if not mvs: _rep[h]-=1; return(-99000+ply if turn==1 else 99000-ply),None
    if depth==0:
        _rep[h]-=1
        if is_cap: return _qsc(lp,dp,lk,dk,turn,alpha,beta,8),None
        return evaluate(lp,dp,lk,dk),None
    lc2,dc2=count_p((lp,dp,lk,dk)); total=lc2+dc2
    NR=3 if depth>=6 else 2
    if null_ok and not is_cap and depth>=NR+1 and total>6:
        ns,_=_srch(lp,dp,lk,dk,1-turn,depth-NR-1,-beta,-beta+1,null_ok=False,ply=ply+1)
        if(turn==1 and ns>=beta)or(turn==0 and ns<=alpha): _rep[h]-=1; return(beta if turn==1 else alpha),None
    if tt_mv is None and depth>=5 and not is_cap:
        _srch(lp,dp,lk,dk,turn,depth-3,alpha,beta,null_ok=False,ply=ply)
        _,tt_mv=_ttg(h,1,alpha,beta)
    FM=[0,120,240,360]
    if depth<=3 and not is_cap and total>4:
        st2=evaluate(lp,dp,lk,dk)
        if turn==1 and st2+FM[depth]<=alpha: _rep[h]-=1; return alpha,None
        if turn==0 and st2-FM[depth]>=beta:  _rep[h]-=1; return beta,None
    d2=min(depth,63)
    if is_cap: mvs=sorted(mvs,key=lambda ch:len(ch[2])*3000+pc(ch[1])*200,reverse=True)
    else:
        def sc(m):
            s2=_hist[m]*2
            if m==tt_mv: return 200000
            if _killers[d2][0]==m: s2+=1800
            if _killers[d2][1]==m: s2+=1600
            if pmv and _counters.get(pmv)==m: s2+=1400
            return s2+POS_K[m[1]]*4
        mvs=sorted(mvs,key=sc,reverse=True)
    best_mv=mvs[0]; oa=alpha; raised=False
    if turn==1:
        best=-999999
        for idx,mv in enumerate(mvs):
            if _stop_ai: break
            if is_cap: nlp,ndp,nlk,ndk=apply_cap(lp,dp,lk,dk,turn,mv); mk=None; np2=None
            else: fr,to=mv; nlp,ndp,nlk,ndk=apply_mv(lp,dp,lk,dk,turn,fr,to); mk=mv; np2=mv
            red=_lmr(depth,idx,is_cap)
            if idx==0 or not raised: s2,_=_srch(nlp,ndp,nlk,ndk,0,depth-1,alpha,beta,ply=ply+1,pmv=np2)
            else:
                s2,_=_srch(nlp,ndp,nlk,ndk,0,max(0,depth-1-red),-alpha-1,-alpha,ply=ply+1,pmv=np2); s2=-s2
                if s2>alpha:
                    if red>0: s2,_=_srch(nlp,ndp,nlk,ndk,0,depth-1,-alpha-1,-alpha,ply=ply+1,pmv=np2); s2=-s2
                    if s2>alpha and s2<beta: s2,_=_srch(nlp,ndp,nlk,ndk,0,depth-1,alpha,beta,ply=ply+1,pmv=np2)
            if s2>best: best=s2; best_mv=mv
            if s2>alpha: alpha=s2; raised=True
            if beta<=alpha:
                if mk:
                    if _killers[d2][0]!=mk: _killers[d2][1]=_killers[d2][0]; _killers[d2][0]=mk
                    if pmv: _counters[pmv]=mk
                    _hist[mk]+=depth*depth
                break
        fl=_EX if oa<best<beta else(_LO if best>=beta else _UP)
        _ttp(h,depth,best,fl,best_mv); _rep[h]-=1; return best,best_mv
    else:
        best=999999
        for idx,mv in enumerate(mvs):
            if _stop_ai: break
            if is_cap: nlp,ndp,nlk,ndk=apply_cap(lp,dp,lk,dk,turn,mv); mk=None; np2=None
            else: fr,to=mv; nlp,ndp,nlk,ndk=apply_mv(lp,dp,lk,dk,turn,fr,to); mk=mv; np2=mv
            red=_lmr(depth,idx,is_cap)
            if idx==0 or not raised: s2,_=_srch(nlp,ndp,nlk,ndk,1,depth-1,alpha,beta,ply=ply+1,pmv=np2)
            else:
                s2,_=_srch(nlp,ndp,nlk,ndk,1,max(0,depth-1-red),beta,beta+1,ply=ply+1,pmv=np2)
                if s2<beta:
                    if red>0: s2,_=_srch(nlp,ndp,nlk,ndk,1,depth-1,beta,beta+1,ply=ply+1,pmv=np2)
                    if s2<beta and s2>alpha: s2,_=_srch(nlp,ndp,nlk,ndk,1,depth-1,alpha,beta,ply=ply+1,pmv=np2)
            if s2<best: best=s2; best_mv=mv
            if s2<beta: beta=s2; raised=True
            if beta<=alpha:
                if mk:
                    if _killers[d2][0]!=mk: _killers[d2][1]=_killers[d2][0]; _killers[d2][0]=mk
                    if pmv: _counters[pmv]=mk
                    _hist[mk]+=depth*depth
                break
        fl=_EX if oa<best<beta else(_LO if best>=beta else _UP)
        _ttp(h,depth,best,fl,best_mv); _rep[h]-=1; return best,best_mv

def get_ai_move(st,turn,tl=4.0):
    global _stop_ai,_TT,_hist,_killers,_counters,_rep
    lp,dp,lk,dk=st; _stop_ai=False; _TT={}
    _hist=defaultdict(int); _killers=[[None,None] for _ in range(64)]
    _counters={}; _rep=defaultdict(int)
    start=time.time(); best_mv=None; best_d=0; prev=0
    _,mvs=legal(lp,dp,lk,dk,turn)
    if not mvs: return None,0
    AW=30
    for depth in range(2,50):
        if time.time()-start>tl*0.88: break
        alpha,beta=(-999999,999999) if depth<5 else(prev-AW,prev+AW)
        fc=0
        while True:
            try:
                s2,mv=_srch(lp,dp,lk,dk,turn,depth,alpha,beta)
                if _stop_ai: break
                if s2<=alpha: AW=min(AW*2,400); alpha=max(alpha-AW,-999999); fc+=1
                elif s2>=beta: AW=min(AW*2,400); beta=min(beta+AW,999999); fc+=1
                else:
                    AW=max(AW//2,20); prev=s2
                    if mv is not None: best_mv=mv; best_d=depth
                    break
            except: break
            if fc>6 or(alpha<=-999999 and beta>=999999): break
        if abs(prev)>90000: break
    return best_mv or mvs[0], best_d

# ═══════════════════════════════════════════════════════════
#  COLORS
# ═══════════════════════════════════════════════════════════
def hx(s):
    s=s.lstrip('#')
    return tuple(int(s[i:i+2],16)/255 for i in (0,2,4))+(1,)

GOLD=hx('C9A84C'); GOLD_L=hx('E8CA70')
C_DARK=hx('371806'); C_LITE=hx('BE9450')
C_SEL=hx('6E5200'); C_VALID=hx('124C12')
C_CAP=hx('640A0A'); C_LM=hx('0A3252')
TEXT=hx('E4DCC2'); MUTED=hx('605040')
PL_C=hx('D7B484'); PL2_C=hx('FFF8E4')
PD_C=hx('301404'); PD2_C=hx('4A2808')
BG_C=(0.04,0.04,0.04,1)

# ═══════════════════════════════════════════════════════════
#  BOARD WIDGET
# ═══════════════════════════════════════════════════════════
class BoardWidget(Widget):
    def __init__(self,gs,**kw):
        super().__init__(**kw)
        self.gs=gs
        self.bind(size=lambda *a:self.redraw(), pos=lambda *a:self.redraw())

    def cell_size(self): return min(self.width,self.height)/8

    def origin(self):
        c=self.cell_size()
        return self.x+(self.width-c*8)/2, self.y+(self.height-c*8)/2

    def redraw(self):
        self.canvas.clear()
        g=self.gs; cell=self.cell_size()
        if cell<1: return
        ox,oy=self.origin()
        lp,dp,lk,dk=g.st; occ=lp|dp|lk|dk
        himap={(h[0],h[1]):h[2] for h in g.hcap+g.hmv}
        with self.canvas:
            Color(*GOLD)
            Line(rectangle=(ox-dp(2),oy-dp(2),cell*8+dp(4),cell*8+dp(4)),width=dp(2))
            for r in range(8):
                for c in range(8):
                    x=ox+c*cell; y=oy+(7-r)*cell
                    if (r+c)%2==0:
                        Color(*C_LITE); Rectangle(pos=(x,y),size=(cell,cell)); continue
                    sq=rc_sq.get((r,c),-1)
                    issel=sq>=0 and g.sel==sq
                    ishi=(r,c) in himap; iscap=himap.get((r,c),False)
                    islm=sq in g.lmv if sq>=0 else False
                    if issel: Color(*C_SEL)
                    elif iscap: Color(*C_CAP)
                    elif ishi: Color(*C_VALID)
                    elif islm: Color(*C_LM)
                    else: Color(*C_DARK)
                    Rectangle(pos=(x,y),size=(cell,cell))
                    if g.hints and ishi and sq>=0 and not(occ>>sq&1):
                        cx2=x+cell/2; cy2=y+cell/2; r2=cell*0.18
                        if iscap: Color(0.85,0.2,0.2,0.85); Line(circle=(cx2,cy2,r2),width=dp(2))
                        else: Color(0.25,0.65,0.25,0.85); Ellipse(pos=(cx2-r2,cy2-r2),size=(r2*2,r2*2))
            ht=g.pc
            if g.turn==ht and not g.thinking and not g.dead:
                amc=all_max_chains(lp,dp,lk,dk,ht)
                can_sqs=set(ch[2][0][0] for ch in amc) if amc else set(fr for fr,to in gen_simple(lp,dp,lk,dk,ht))
            else: can_sqs=set()
            for i,(r,c) in enumerate(sq_map):
                p=0
                if lk>>i&1: p=3
                elif lp>>i&1: p=1
                elif dk>>i&1: p=4
                elif dp>>i&1: p=2
                if not p: continue
                x=ox+c*cell; y=oy+(7-r)*cell
                cx2=x+cell/2; cy2=y+cell/2; rad=cell*0.40; islt=p in(1,3)
                if g.hints and i in can_sqs and g.sel is None:
                    Color(*GOLD_L[:3],0.75); Line(circle=(cx2,cy2,rad+dp(3)),width=dp(2))
                if g.sel==i: Color(*GOLD); Line(circle=(cx2,cy2,rad+dp(4)),width=dp(3))
                Color(0,0,0,0.45); Ellipse(pos=(cx2-rad+dp(2),cy2-rad-dp(2)),size=(rad*2,rad*2))
                if islt:
                    Color(*PL_C); Ellipse(pos=(cx2-rad,cy2-rad),size=(rad*2,rad*2))
                    Color(*PL2_C[:3],0.75); r2=rad*0.45
                    Ellipse(pos=(cx2-rad*0.5,cy2),size=(r2*2,r2*2))
                    Color(*hx('A07040')[:3],0.55); Line(circle=(cx2,cy2,rad),width=dp(1.5))
                else:
                    Color(*PD_C); Ellipse(pos=(cx2-rad,cy2-rad),size=(rad*2,rad*2))
                    Color(*PD2_C[:3],0.65); r2=rad*0.35
                    Ellipse(pos=(cx2-rad*0.45,cy2-rad*0.1),size=(r2*2,r2*2))
                    Color(*hx('1A0800')[:3],0.5); Line(circle=(cx2,cy2,rad),width=dp(1.5))
                if p in(3,4):
                    Color(*GOLD_L); cr=rad*0.22; Ellipse(pos=(cx2-cr,cy2-cr),size=(cr*2,cr*2))

    def on_touch_down(self,touch):
        if not self.collide_point(*touch.pos): return False
        cell=self.cell_size()
        if cell<1: return False
        ox,oy=self.origin()
        c=int((touch.x-ox)//cell); r=7-int((touch.y-oy)//cell)
        if 0<=r<8 and 0<=c<8 and (r+c)%2==1: self.gs.handle_tap(r,c)
        return True

# ═══════════════════════════════════════════════════════════
#  GAME STATE
# ═══════════════════════════════════════════════════════════
class GameState:
    def __init__(self,on_update):
        self.on_update=on_update
        self.st=init_st(); self.turn=0; self.pc=0
        self.sel=None; self.hcap=[]; self.hmv=[]; self.lmv=[]
        self.dead=False; self.winner=None
        self.thinking=False; self.ai_res=None; self.aid=0
        self.csq=None; self.csteps=[]; self.copts=[]
        self.log=[]; self.snaps=[]; self.hints=True

    def _reset_engine(self):
        global _TT,_hist,_killers,_counters,_rep
        _TT={}; _hist=defaultdict(int)
        _killers=[[None,None] for _ in range(64)]
        _counters={}; _rep=defaultdict(int)

    def reset(self):
        self._reset_engine()
        self.st=init_st(); self.turn=0
        self.sel=None; self.hcap=[]; self.hmv=[]; self.lmv=[]
        self.dead=False; self.winner=None; self.thinking=False; self.ai_res=None
        self.csq=None; self.csteps=[]; self.copts=[]
        self.log=[]; self.snaps=[]; self.aid=0
        if self.turn!=self.pc: self._sai()

    def handle_tap(self,r,c):
        if self.thinking or self.dead or self.turn!=self.pc: return
        sq=rc_sq[(r,c)]; lp,dp,lk,dk=self.st
        if self.csq is not None:
            nexts=[ch for ch in self.copts if len(ch[2])>len(self.csteps) and ch[2][len(self.csteps)][1]==sq]
            if nexts:
                step=nexts[0][2][len(self.csteps)]; fr2,to2,ov2=step
                lp,dp,lk,dk=apply_cap(lp,dp,lk,dk,self.turn,(to2,1<<ov2,[step]))
                self.st=(lp,dp,lk,dk); self.csteps.append(step)
                self.lmv.append(fr2); self.lmv.append(to2)
                cont=[ch for ch in nexts if len(ch[2])>len(self.csteps)]
                if cont:
                    self.csq=to2; self.copts=nexts; self.sel=to2
                    dsts=set(ch[2][len(self.csteps)][1] for ch in cont)
                    self.hcap=[(sq_map[d2][0],sq_map[d2][1],True) for d2 in dsts]; self.hmv=[]
                else: self._log(self.csteps,False); self._eoh()
            self.on_update(); return
        if self.sel is not None:
            hc=next((h for h in self.hcap if h[0]==r and h[1]==c),None)
            hm=next((h for h in self.hmv  if h[0]==r and h[1]==c),None)
            if hc:
                chs=all_max_chains(lp,dp,lk,dk,self.turn)
                match=[ch for ch in chs if ch[2][0][0]==self.sel and ch[2][0][1]==sq]
                if not match: self.sel=None; self.hcap=[]; self.hmv=[]; self.on_update(); return
                step=match[0][2][0]; fr2,to2,ov2=step; self.snaps.append(self.st)
                lp,dp,lk,dk=apply_cap(lp,dp,lk,dk,self.turn,(to2,1<<ov2,[step]))
                self.st=(lp,dp,lk,dk); self.csteps=[step]; self.lmv=[fr2,to2]
                cont=[ch for ch in match if len(ch[2])>1]
                if cont:
                    self.csq=to2; self.copts=match; self.sel=to2
                    dsts=set(ch[2][1][1] for ch in cont)
                    self.hcap=[(sq_map[d2][0],sq_map[d2][1],True) for d2 in dsts]; self.hmv=[]
                else: self._log(self.csteps,False); self._eoh()
                self.on_update(); return
            if hm:
                fr2=self.sel; self.snaps.append(self.st)
                lp,dp,lk,dk=apply_mv(lp,dp,lk,dk,self.turn,fr2,sq)
                self.st=(lp,dp,lk,dk); self.lmv=[fr2,sq]
                self._log([(fr2,sq,None)],False); self._eoh(); self.on_update(); return
            self.sel=None; self.hcap=[]; self.hmv=[]
        p=0
        if lk>>sq&1: p=3
        elif lp>>sq&1: p=1
        elif dk>>sq&1: p=4
        elif dp>>sq&1: p=2
        if not p: self.on_update(); return
        own=(p in(1,3)) if self.pc==0 else (p in(2,4))
        if not own: self.on_update(); return
        chs=all_max_chains(lp,dp,lk,dk,self.turn)
        if chs:
            pc2=[ch for ch in chs if ch[2][0][0]==sq]
            if not pc2: self.on_update(); return
            self.sel=sq; dsts=set(ch[2][0][1] for ch in pc2)
            self.hcap=[(sq_map[d2][0],sq_map[d2][1],True) for d2 in dsts]; self.hmv=[]
        else:
            sm=[m for m in gen_simple(lp,dp,lk,dk,self.turn) if m[0]==sq]
            if not sm: self.on_update(); return
            self.sel=sq; self.hmv=[(sq_map[t][0],sq_map[t][1],False) for _,t in sm]; self.hcap=[]
        self.on_update()

    def _eoh(self):
        self.sel=None; self.hcap=[]; self.hmv=[]
        self.csq=None; self.csteps=[]; self.copts=[]
        lc,dc=count_p(self.st)
        if not lc: self._go(1); return
        if not dc: self._go(0); return
        self.turn=1-self.turn
        _,mvs=legal(*self.st,self.turn)
        if not mvs: self._go(1-self.turn); return
        self.on_update()
        if self.turn!=self.pc: self._sai()

    def _sai(self):
        self.thinking=True; snap=self.st; t2=self.turn
        def w():
            lc2,dc2=count_p(snap); tot=lc2+dc2
            tl=1.5 if tot>18 else(3.0 if tot>10 else 5.0)
            self.ai_res=get_ai_move(snap,t2,tl)
        threading.Thread(target=w,daemon=True).start()

    def apply_ai(self):
        res=self.ai_res; self.ai_res=None; self.thinking=False
        if res is None: self._go(self.pc); return
        mv,d=res; self.aid=d; self.snaps.append(self.st)
        lp,dp,lk,dk=self.st
        is_ch=isinstance(mv,tuple) and len(mv)==3 and isinstance(mv[2],list)
        if is_ch:
            fs,cap,steps=mv; self.lmv=[s2[0] for s2 in steps]+[fs]
            lp,dp,lk,dk=apply_cap(lp,dp,lk,dk,self.turn,mv)
            self.st=(lp,dp,lk,dk); self._log(steps,True,chain=True)
        else:
            fr,to=mv; self.lmv=[fr,to]
            lp,dp,lk,dk=apply_mv(lp,dp,lk,dk,self.turn,fr,to)
            self.st=(lp,dp,lk,dk); self._log([(fr,to,None)],True)
        lc,dc=count_p(self.st)
        if not lc: self._go(1); return
        if not dc: self._go(0); return
        self.turn=1-self.turn
        _,mvs=legal(*self.st,self.turn)
        if not mvs: self._go(1-self.turn); return
        if self.turn!=self.pc: self._sai()

    def _go(self,w): self.dead=True; self.winner=w; self.thinking=False

    def _log(self,steps,ai,chain=False):
        n2=len(self.log)+1
        try:
            if chain:
                frm=f"{chr(97+sq_map[steps[0][0]][1])}{8-sq_map[steps[0][0]][0]}"
                to=f"{chr(97+sq_map[steps[-1][1]][1])}{8-sq_map[steps[-1][1]][0]}"
                txt=f"{frm}x{to}(x{len(steps)})"
            else:
                fr,to=steps[0][0],steps[0][1]
                frm=f"{chr(97+sq_map[fr][1])}{8-sq_map[fr][0]}"
                tom=f"{chr(97+sq_map[to][1])}{8-sq_map[to][0]}"
                caps=sum(1 for s2 in steps if len(s2)>2 and s2[2] is not None)
                txt=f"{frm}x{tom}(x{caps})" if caps else f"{frm}-{tom}"
        except: txt="move"
        self.log.append((n2,txt,ai))

    def undo(self):
        if not self.snaps or self.thinking: return
        self.st=self.snaps.pop()
        self.sel=None; self.hcap=[]; self.hmv=[]
        self.csq=None; self.csteps=[]; self.copts=[]; self.lmv=[]
        self.dead=False; self.thinking=False; self.turn=self.pc
        if self.log: self.log.pop()
        if self.log: self.log.pop()
        self.on_update()

# ═══════════════════════════════════════════════════════════
#  KIVY APP
# ═══════════════════════════════════════════════════════════
class DamaMobileApp(App):
    def build(self):
        Window.clearcolor=BG_C; self.title='DAMA MODE v4'
        self.root_widget=FloatLayout()
        self.gs=GameState(on_update=self._safe_refresh)
        self._tick_ev=None; self._go_shown=False
        self._show_menu()
        return self.root_widget

    def _safe_refresh(self):
        Clock.schedule_once(lambda dt:self._do_refresh(),0)

    def _do_refresh(self):
        if hasattr(self,'board_widget') and self.board_widget:
            self.board_widget.redraw()
        self._upd_labels()
        if self.gs.dead and not self._go_shown:
            self._go_shown=True
            Clock.schedule_once(lambda dt:self._show_go(),0.15)

    def _upd_labels(self):
        if not hasattr(self,'lbl_status'): return
        g=self.gs; lc,dc=count_p(g.st)
        pn="YOU" if g.pc==0 else "AI"; an="AI" if g.pc==0 else "YOU"
        if hasattr(self,'lbl_lc'): self.lbl_lc.text=f"{pn if g.pc==0 else an}  {lc}"
        if hasattr(self,'lbl_dc'): self.lbl_dc.text=f"{dc}  {an if g.pc==0 else pn}"
        if hasattr(self,'lbl_dep') and g.aid>0: self.lbl_dep.text=f"d:{g.aid}"
        if g.thinking:
            self.lbl_status.text='AI THINKING...'; self.lbl_status.color=(*GOLD[:3],1)
        elif g.turn==g.pc and not g.dead:
            lp2,dp2,lk2,dk2=g.st; ac=all_max_chains(lp2,dp2,lk2,dk2,g.pc)
            if ac: self.lbl_status.text='CAPTURE REQUIRED!'; self.lbl_status.color=(0.9,0.3,0.3,1)
            else:  self.lbl_status.text='YOUR TURN';         self.lbl_status.color=(*TEXT[:3],1)
        else: self.lbl_status.text='AI MOVING...'; self.lbl_status.color=(*MUTED[:3],1)

    def _show_menu(self):
        self.root_widget.clear_widgets()
        if self._tick_ev: self._tick_ev.cancel(); self._tick_ev=None
        if hasattr(self,'board_widget'): self.board_widget=None
        outer=BoxLayout(orientation='vertical',padding=dp(24),spacing=dp(14),
                        size_hint=(0.88,0.84),pos_hint={'center_x':.5,'center_y':.5})
        outer.add_widget(Label(text='DAMA MODE v4',font_size=dp(34),bold=True,
                               color=GOLD,size_hint_y=None,height=dp(50)))
        outer.add_widget(Label(text='Ultimate Grandmaster Engine',font_size=dp(13),
                               color=MUTED,size_hint_y=None,height=dp(26)))
        outer.add_widget(Label(text='Select your colour',font_size=dp(15),color=TEXT,
                               size_hint_y=None,height=dp(30)))
        self._mc=0
        row=BoxLayout(orientation='horizontal',spacing=dp(14),size_hint_y=None,height=dp(72))
        self._bl=Button(text='LIGHT',bold=True,font_size=dp(15),
                        background_color=(0.18,0.13,0.03,1),color=GOLD)
        self._bd=Button(text='DARK', bold=True,font_size=dp(15),
                        background_color=(0.10,0.10,0.10,1),color=(*MUTED[:3],1))
        self._bl.bind(on_press=lambda x:self._pick(0))
        self._bd.bind(on_press=lambda x:self._pick(1))
        row.add_widget(self._bl); row.add_widget(self._bd); outer.add_widget(row)
        sb=Button(text='ENTER THE BOARD',bold=True,font_size=dp(17),
                  background_color=(0.50,0.33,0.10,1),color=(0,0,0,1),
                  size_hint_y=None,height=dp(62))
        sb.bind(on_press=self._start); outer.add_widget(sb)
        outer.add_widget(Label(
            text='v4: PVS+LMR+Null+IID+Futility+Delta+Counter+Repetition\nDepth 15+ | Same strength as desktop version',
            font_size=dp(11),color=MUTED,halign='center',size_hint_y=None,height=dp(50)))
        self.root_widget.add_widget(outer)

    def _pick(self,c):
        self._mc=c
        if c==0:
            self._bl.background_color=(0.18,0.13,0.03,1); self._bl.color=GOLD
            self._bd.background_color=(0.10,0.10,0.10,1); self._bd.color=(*MUTED[:3],1)
        else:
            self._bd.background_color=(0.18,0.13,0.03,1); self._bd.color=GOLD
            self._bl.background_color=(0.10,0.10,0.10,1); self._bl.color=(*MUTED[:3],1)

    def _start(self,*a):
        self.gs.pc=self._mc; self._go_shown=False
        self._build_ui()
        self.gs.reset()
        self._do_refresh()

    def _build_ui(self):
        self.root_widget.clear_widgets()
        main=BoxLayout(orientation='vertical',spacing=dp(4),padding=dp(4))
        hdr=BoxLayout(orientation='horizontal',size_hint_y=None,height=dp(44))
        hdr.add_widget(Label(text='DAMA MODE v4',font_size=dp(17),bold=True,color=GOLD))
        self.lbl_status=Label(text='YOUR TURN',font_size=dp(13),color=TEXT)
        hdr.add_widget(self.lbl_status); main.add_widget(hdr)
        sc=BoxLayout(orientation='horizontal',size_hint_y=None,height=dp(34))
        self.lbl_lc=Label(text='YOU  12',font_size=dp(13),bold=True,color=PL_C)
        self.lbl_dep=Label(text='',font_size=dp(10),color=MUTED)
        self.lbl_dc=Label(text='12  AI',font_size=dp(13),bold=True,color=PD2_C)
        sc.add_widget(self.lbl_lc); sc.add_widget(self.lbl_dep); sc.add_widget(self.lbl_dc)
        main.add_widget(sc)
        self.board_widget=BoardWidget(self.gs,size_hint=(1,1))
        main.add_widget(self.board_widget)
        btns=BoxLayout(orientation='horizontal',size_hint_y=None,height=dp(50),spacing=dp(5))
        for txt,fn in [('UNDO',self._undo),('NEW',self._new),('HINTS',self._hints),('RESIGN',self._resign),('MENU',self._menu)]:
            b=Button(text=txt,font_size=dp(11),bold=True,
                     background_color=(0.10,0.10,0.10,1),color=(*MUTED[:3],1))
            b.bind(on_press=fn); btns.add_widget(b)
        main.add_widget(btns); self.root_widget.add_widget(main)
        if self._tick_ev: self._tick_ev.cancel()
        self._tick_ev=Clock.schedule_interval(self._tick,1/30)

    def _tick(self,dt):
        if self.gs.thinking and self.gs.ai_res is not None:
            self.gs.apply_ai(); self._do_refresh()

    def _undo   (self,*a): self.gs.undo()
    def _hints  (self,*a): self.gs.hints=not self.gs.hints; self._do_refresh()
    def _resign (self,*a): self.gs._go(1-self.gs.pc); self._do_refresh()
    def _new    (self,*a): self._go_shown=False; self.gs.reset(); self._do_refresh()
    def _menu   (self,*a):
        global _stop_ai; _stop_ai=True
        if self._tick_ev: self._tick_ev.cancel(); self._tick_ev=None
        self.board_widget=None; self._show_menu()

    def _show_go(self):
        g=self.gs; won=g.winner==g.pc; lc,dc=count_p(g.st)
        title="VICTORY!" if won else "DEFEATED"
        msg="Outstanding — you beat the Ultimate AI!" if won else "The Ultimate AI prevails!"
        stats=f"Light:{lc}  Dark:{dc}  Moves:{len(g.log)}  Depth:{g.aid}"
        content=BoxLayout(orientation='vertical',padding=dp(18),spacing=dp(10))
        tc=(0.2,0.82,0.42,1) if won else(0.85,0.22,0.22,1)
        content.add_widget(Label(text=title,font_size=dp(28),bold=True,color=tc,size_hint_y=None,height=dp(46)))
        content.add_widget(Label(text=msg,font_size=dp(13),color=TEXT,halign='center'))
        content.add_widget(Label(text=stats,font_size=dp(11),color=MUTED,halign='center'))
        brow=BoxLayout(orientation='horizontal',spacing=dp(10),size_hint_y=None,height=dp(50))
        b_rm=Button(text='REMATCH',bold=True,background_color=(0.50,0.33,0.10,1),color=(0,0,0,1))
        b_mn=Button(text='MENU',bold=True,background_color=(0.12,0.12,0.12,1),color=(*MUTED[:3],1))
        brow.add_widget(b_rm); brow.add_widget(b_mn); content.add_widget(brow)
        popup=Popup(title='',content=content,size_hint=(0.86,0.54),
                    background_color=(0.06,0.06,0.06,0.97),separator_height=0)
        b_rm.bind(on_press=lambda x:(popup.dismiss(),self._new()))
        b_mn.bind(on_press=lambda x:(popup.dismiss(),self._menu()))
        popup.open()

if __name__=='__main__':
    print("DAMA MODE v4 Mobile — pip install kivy && python dama_mobile_v4.py")
    DamaMobileApp().run()
