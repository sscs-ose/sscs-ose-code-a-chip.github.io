// =============================================================================
// Project: ProEm - Open Source Protocol Emulator
// File: sim/t_random_branch.cpp
// Type: Test, pin level (CXXRTL), constrained random
// Device under test: protocol_emulator (src/top/protocol_emulator.sv)
// Author: Paul Vincent Bezzina
// Language: C++14
// Description:
// =============================================================================

#include "bench.h"
int MSB=0, gap=0, sck=0, sd=0;
void r_env(){ pin_in=sd|(sck<<1); }
void bit(int b){ sd=b; idle(gap+2); sck=1; idle(gap+2); sck=0; }
void send(unsigned v,unsigned n){ for(unsigned k=0;k<n;k++) bit(MSB? (v>>(n-1-k))&1 : (v>>k)&1); }
B prog;
void add(const B&b){ prog.insert(prog.end(),b.begin(),b.end()); }
int main(int argc,char**argv){ int seed=argc>1?atoi(argv[1]):1; if(argc>2) MSB=atoi(argv[2]); int runs_n=argc>3?atoi(argv[3]):100; srand(seed); INS_R=6; env=r_env; power_on(); int bad=0;
  for(int r=0;r<runs_n;r++){ gap=rand()%4; prog.clear(); add(I_clear()); add(I_order(MSB)); add(I_clock(SYNC,0,1,0)); clear_results();
    unsigned l1=1+rand()%8, l2=1+rand()%8, l3=1+rand()%8, n=1+rand()%20;
    unsigned x2=rand()&((1u<<l2)-1), x3=rand()&((1u<<l3)-1), v1=rand()&((1u<<l1)-1);
    unsigned mask=rand()&0xFF, value=rand()&0xFF; if(rand()%2) value=(v1&mask)|(value&~mask);
    int hit=rand()%4, miss=rand()%4, base=rand()%3;
    add(I_start(0xD5,8,0,0)); add(I_hdr(1,0,l1,1,0,0,0,1)); add(I_hdr(2,x2,l2,1,0,1)); add(I_hdr(3,x3,l3,1,0,2));
    add(I_branch(0,hit,miss,0,1,mask,value)); add(I_main(n,0)); add(I_run(base)); program(prog);
    bool matched=((v1^value)&mask&((1u<<l1)-1))==0 && ((value&mask)>>l1)==0;
    int act=matched?hit:miss; int m=base; if(act==GO_READ) m=1; else if(act==GO_WRITE) m=2;
    V exp; std::vector<unsigned> est;
    for(int i=0;i<3;i++) for(int k=0;k<8;k++) bit(k%2==0);
    send(0xD5,8); send(v1,l1); exp.push_back({l1,v1});
    if(act==ABORT){ est.push_back(0x82|(matched?0x40:0)); for(int k=0;k<16;k++) bit(0); }
    else { if(m==1){ send(x2,l2); exp.push_back({l2,x2}); } if(m==2){ send(x3,l3); exp.push_back({l3,x3}); }
      std::vector<int> ch; for(unsigned i=0;i<n;i++) ch.push_back(rand()&1); for(int b:ch) bit(b);
      for(size_t i=0;i<ch.size();i+=8){ unsigned v=0,c=0; for(size_t j=i;j<ch.size()&&j<i+8;j++){ if(MSB) v=(v<<1)|ch[j]; else v|=ch[j]<<c; c++; } exp.push_back({c,v}); }
      est.push_back(0x01|(matched?0x40:0)); }
    for(int k=0;k<4;k++) bit(MSB?0:1); idle(100); wait_return();
    bool ok=got[0]==exp&&status[0]==est;
    if(!ok){ bad++; if(bad<6) printf("FAIL run %d l1=%u v1=%X mask=%02X value=%02X hit=%d miss=%d base=%d\n  exp%s |%s\n  got%s |%s\n",r,l1,v1,mask,value,hit,miss,base,show(exp).c_str(),showst(est).c_str(),show(got[0]).c_str(),showst(status[0]).c_str()); } }
  printf("seed %d %s: %d/%d branch programs passed\n",seed,MSB?"MSB":"LSB",runs_n-bad,runs_n); return bad!=0; }
