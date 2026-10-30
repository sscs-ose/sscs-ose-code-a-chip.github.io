// =============================================================================
// Project: ProEm - Open Source Protocol Emulator
// File: sim/t_random.cpp
// Type: Test, pin level (CXXRTL)
// Device under test: protocol_emulator (src/top/protocol_emulator.sv)
// Author: Paul Vincent Bezzina
// Language: C++14
// Description:
// =============================================================================

#include "bench.h"
int MSB=0, gap=0, sck=0, sd=0, psck=0; std::vector<int> sent;
void r_env(){ int c=t.p_clock__oe__a.get<bool>()? t.p_clock__out__a.get<bool>() : 0; if(c && !psck) sent.push_back(t.p_data__out__a.get<bool>()); psck=c; pin_in=sd|(sck<<1); }
void bit(int b){ sd=b; idle(gap+2); sck=1; idle(gap+2); sck=0; }
unsigned rev(unsigned v,unsigned n){ unsigned o=0; for(unsigned i=0;i<n;i++) if((v>>i)&1) o|=1u<<(n-1-i); return o; }
B prog;
void add(const B&b){ prog.insert(prog.end(),b.begin(),b.end()); }
int main(int argc,char**argv){ int seed=argc>1?atoi(argv[1]):1; if(argc>2) MSB=atoi(argv[2]); int runs_n=argc>3?atoi(argv[3]):150; srand(seed); INS_R=6; env=r_env; power_on(); int bad=0,runs=0;
  for(int r=0;r<runs_n;r++){ gap=rand()%5; bool write=r%2; prog.clear(); add(I_clear()); add(I_order(MSB)); clear_results(); sent.clear();
    int nh=rand()%7; int N=1+rand()%24; V exp; std::vector<unsigned> est; std::vector<int> esent;
    if(write){ add(I_clock(GENERATE,2,1,0,0)); add(I_out(3,0)); add(I_wdog(200));
      unsigned sl=1+rand()%8, sv=rand()&((1u<<sl)-1); add(I_start(sv,sl,0,1));
      V hdr; hdr.push_back({sl,sv});
      for(int h=1;h<=nh;h++){ unsigned l=1+rand()%8, v=rand()&0xFF; add(I_hdr(h,v,l,0,1)); hdr.push_back({l,v&((1u<<l)-1)}); }
      add(I_main(N,1));
      int E=1+rand()%8; V ent; for(int i=0;i<E;i++){ unsigned l=1+rand()%8; ent.push_back({l,rand()&((1u<<l)-1)}); }
      for(auto&e:ent) add(I_data(e.first,e.second)); add(I_run(0)); program(prog); idle(400+100*E*(nh+2)); wait_return();
      size_t i=0; unsigned cl=0,cv=0; bool carry=false;
      while(carry||i<ent.size()){ for(auto&h:hdr) exp.push_back({h.first, MSB? rev(h.second,h.first) : h.second}); int rem=N; bool full=false;
        while(carry||i<ent.size()){ unsigned l=carry?cl:ent[i].first, v=carry?cv:ent[i].second; if(!carry) i++; carry=false;
          unsigned tk=(int)l>rem? rem : l; unsigned part= MSB? (v>>(l-tk))&((1u<<tk)-1) : v&((1u<<tk)-1); exp.push_back({tk, MSB? rev(part,tk) : part}); rem-=tk; if(l>tk){ carry=true; cl=l-tk; cv= MSB? v&((1u<<(l-tk))-1) : v>>tk; }
          if(rem==0){ full=true; break; } }
        est.push_back(full?1:5); }
      for(auto&e:exp) for(unsigned k=0;k<e.first;k++) esent.push_back((e.second>>k)&1);
      exp.clear();
    } else { add(I_clock(SYNC,0,1,0));
      int sc=rand()%2; add(I_start(0xD5,8,sc,0));
      std::vector<std::pair<unsigned,unsigned>> hv; std::vector<int> hc;
      for(int h=1;h<=nh;h++){ unsigned l=1+rand()%8, v=rand()&((1u<<l)-1); int c=rand()%2; add(I_hdr(h,v,l,c,0)); hv.push_back({l,v}); hc.push_back(c); }
      add(I_main(N,0)); add(I_run(0)); program(prog);
      int F=1+rand()%3;
      for(int f=0;f<F;f++){ size_t mark=exp.size();
        for(int i=0;i<3;i++) for(int k=0;k<8;k++) bit(k%2==0);
        for(int k=0;k<8;k++) bit(MSB? (0xD5>>(7-k))&1 : (0xD5>>k)&1);
        if(sc) exp.push_back({8,0xD5});
        bool mism=nh>0&&rand()%3==0; int mh=mism?rand()%nh:-1; bool ab=false;
        for(int h=0;h<nh&&!ab;h++){ unsigned v=hv[h].second; if(h==mh) v^=1; for(unsigned k=0;k<hv[h].first;k++) bit(MSB? (v>>(hv[h].first-1-k))&1 : (v>>k)&1);
          if(h==mh){ ab=true; est.push_back(2); } else if(hc[h]) exp.push_back(hv[h]); }
        if(ab){ exp.resize(mark); for(int k=0;k<16;k++) bit(0); }
        else { std::vector<int> ch; for(int i=0;i<N;i++) ch.push_back(rand()&1); for(int b:ch) bit(b);
          for(size_t i=0;i<ch.size();i+=8){ unsigned v=0,n=0; for(size_t j=i;j<ch.size()&&j<i+8;j++){ if(MSB) v=(v<<1)|ch[j]; else v|=ch[j]<<n; n++; } exp.push_back({n,v}); } est.push_back(1); }
        for(int k=0;k<4;k++) bit(MSB?0:1); idle(10); }
      idle(100); wait_return();
    }
    runs++; bool ok=got[0]==exp&&status[0]==est&&sent==esent;
    if(!ok){ bad++; if(bad<6){ printf("FAIL run %d %s gap=%d nh=%d N=%d\n  exp%s |%s wire %zu bits\n  got%s |%s wire %zu bits\n",r,write?"write":"read",gap,nh,N,show(exp).c_str(),showst(est).c_str(),esent.size(),show(got[0]).c_str(),showst(status[0]).c_str(),sent.size()); } } }
  printf("seed %d %s: %d/%d programs passed\n",seed,MSB?"MSB":"LSB",runs-bad,runs); return bad!=0; }
