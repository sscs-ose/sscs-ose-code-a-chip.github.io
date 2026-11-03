// =============================================================================
// Project: ProEm - Open Source Protocol Emulator
// File: sim/t_modes.cpp
// Type: Test, pin level (CXXRTL)
// Device under test: protocol_emulator (src/top/protocol_emulator.sv)
// Author: Paul Vincent Bezzina
// Language: C++14
// Description:
// =============================================================================

#include "bench.h"

typedef std::vector<unsigned> U;
U U1(){ return U({1}); }
std::string hexs(const U&v){ std::string s; char b[8]; for(unsigned x:v){ snprintf(b,sizeof b," %02X",x); s+=b; } return s; }

struct Dev { int cpol=0, cpha=0, psck=0, pcs=1, bits=0, oidx=0, out=0; unsigned in=0, word=0; std::vector<unsigned> got; std::deque<unsigned> reply; } dv;
int sck_now(){ return t.p_clock__oe__a.get<bool>()? (int)t.p_clock__out__a.get<bool>() : dv.cpol; }
void dev_env(){
  int sck=sck_now(); int cs=t.p_select__out__a.get<bool>(); int mosi=t.p_data__oe__a.get<bool>()? (int)t.p_data__out__a.get<bool>() : 1;
  if(dv.pcs && !cs){ dv.word=dv.reply.empty()?0:dv.reply.front(); if(!dv.reply.empty()) dv.reply.pop_front(); dv.bits=0; dv.in=0; dv.oidx=0; if(!dv.cpha){ dv.out=(dv.word>>15)&1; dv.oidx=1; } }
  if(!cs && sck!=dv.psck){ int leading=(dv.psck==dv.cpol); int sample=leading!=dv.cpha;
    if(sample){ dv.in=((dv.in<<1)|mosi)&0xFFFF; if(++dv.bits==16) dv.got.push_back(dv.in); }
    else if(dv.oidx<16){ dv.out=(dv.word>>(15-dv.oidx))&1; dv.oidx++; } }
  dv.psck=sck; dv.pcs=cs;
  pin_in=0xF0|mosi|(sck<<1)|(cs<<2)|(dv.out<<3); }

bool spi_mode(int mode,int div){ bool ok=true; int cpol=mode>>1, cpha=mode&1, edge=(cpol==cpha)?0:1;
  CH=0; program(I_clear()); CH=1; program(I_clear()); clear_results(); dv=Dev(); dv.cpol=cpol; dv.cpha=cpha; dv.psck=cpol;
  dv.reply={0x9F41,0xC3E7};
  CH=1; program(cat({I_order(1),I_line(0,3),I_clock(SYNC,0,1,edge),I_start(0,0,0,0,2),I_main(16,0,0,0,3),I_run(0)}));
  CH=0; program(cat({I_order(1),I_line(0,0),I_clock(GENERATE,(unsigned)div,1,edge,cpol),I_out(3,0),I_wdog(4000),I_start(0,0,0,1),I_main(16,1),
    I_data(8,0xA5),I_data(8,0x5A),I_run(0)}));
  idle(40*div*2); wait_return();
  char n1[96], d1[96];
  snprintf(n1,sizeof n1,"SPI mode %d controller write: device samples MOSI (no hold margin)",mode);
  snprintf(d1,sizeof d1," device got%s, chain B read%s",showst(dv.got).c_str(),show(got[1]).c_str());
  ok&=report(n1,dv.got==std::vector<unsigned>({0xA55A})&&got[1]==V({{8,0x9F},{8,0x41}})&&status[0]==U1(),d1);
  clear_results(); dv.got.clear();
  CH=0; program(cat({I_main(16,0,0,0,3),I_run(0)}));
  idle(40*div*2); wait_return();
  char n2[96];
  snprintf(n2,sizeof n2,"SPI mode %d controller read: chip samples MISO",mode);
  ok&=report(n2,got[0]==V({{8,0xC3},{8,0xE7}})&&status[0]==U1(),show(got[0]));
  return ok; }

bool branch_rules(){ bool ok=true; const long D=40;
  CH=1; program(I_clear()); CH=0; program(I_clear()); clear_results();
  CH=0; program(cat({I_line(0,0),I_clock(ASYNC,(unsigned)D),I_start(0,1,0,0,0),I_hdr(1,0,8,1,0,0,0,1),I_main(1,0,0,0,0),
    I_branch(0,ABORT,KEEP,0,1,0xFF,0x11),I_branch(1,ABORT,KEEP,0,1,0xFF,0x22),I_run(0)}));
  std::deque<int> wave; auto byte=[&](unsigned v){ for(int k=0;k<D*3;k++) wave.push_back(1); for(int k=0;k<D;k++) wave.push_back(0);
    for(int b=0;b<8;b++) for(int k=0;k<D;k++) wave.push_back((v>>b)&1); for(int k=0;k<D*3;k++) wave.push_back(1); };
  byte(0x33); byte(0x11); byte(0x22); byte(0x44);
  env=[&]{ int lv=1; if(!wave.empty()){ lv=wave.front(); wave.pop_front(); } pin_in=0xFE|lv; };
  while(!wave.empty()) clk(); idle(D*8); wait_return(); env=dev_env;
  U bytes; for(auto&x:got[0]) if(x.first==8) bytes.push_back(x.second);
  ok&=report("BRANCH rules 0 and 1: each aborts (0xC2) on its own value",status[0]==U({0x01,0xC2,0xC2,0x01})&&bytes==U({0x33,0x11,0x22,0x44}),hexs(bytes)+" |"+showst(status[0]));
  program(B{op(0x0)}); program(B{op(0x0)}); wait_return();
  ok&=report("NOP is accepted without a command error",global_flags.empty(),showst(global_flags));
  return ok; }

int main(int argc,char**argv){ int div=argc>1?atoi(argv[1]):6; env=dev_env; pin_in=0xFF; power_on(); program(I_link(4)); RET_R=4; bool ok=true;
  for(int m=0;m<4;m++) ok&=spi_mode(m,div);
  ok&=branch_rules();
  printf(ok?"ALL PASS\n":"FAILED\n"); return !ok; }
