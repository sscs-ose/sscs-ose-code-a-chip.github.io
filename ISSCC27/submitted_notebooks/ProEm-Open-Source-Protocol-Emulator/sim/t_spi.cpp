// =============================================================================
// Project: ProEm - Open Source Protocol Emulator
// File: sim/t_spi.cpp
// Type: Test, pin level (CXXRTL)
// Device under test: protocol_emulator (src/top/protocol_emulator.sv)
// Author: Paul Vincent Bezzina
// Language: C++14
// Description:
// =============================================================================

#include "bench.h"
int scenario=0;
unsigned sl_miso=0, sl_in=0; int sl_bits=0, sl_prev_sck=0, sl_prev_cs=1, sl_out=0; std::vector<unsigned> sl_words; std::deque<unsigned> sl_reply;
int m_sck=0, m_cs=1, m_mosi=0, m_miso_seen=0; unsigned m_rx=0;
void spi_env(){
  if(scenario==0){
    int sck=t.p_clock__oe__a.get<bool>()? t.p_clock__out__a.get<bool>() : 0;
    int cs=t.p_select__out__a.get<bool>();
    int mosi=t.p_data__out__a.get<bool>();
    if(sl_prev_cs && !cs){ sl_miso=sl_reply.empty()?0:sl_reply.front(); if(!sl_reply.empty()) sl_reply.pop_front(); sl_bits=0; sl_in=0; sl_out=(sl_miso>>15)&1; }
    if(!cs && sck && !sl_prev_sck){ sl_in=(sl_in<<1)|mosi; sl_bits++; if(sl_bits==16) sl_words.push_back(sl_in); }
    if(!cs && !sck && sl_prev_sck){ sl_miso<<=1; sl_out=(sl_miso>>15)&1; }
    sl_prev_sck=sck; sl_prev_cs=cs;
    pin_in=(sck<<1)|(cs<<2)|(sl_out<<3);
  } else {
    pin_in=(m_mosi)|(m_sck<<1)|(m_cs<<2);
  } }
void master_transfer(unsigned w,int half){ m_rx=0; m_cs=0; idle(half);
  for(int b=15;b>=0;b--){ m_mosi=(w>>b)&1; idle(half); m_sck=1; int miso=t.p_data__oe__a.get<bool>()? t.p_data__out__a.get<bool>() : 0; m_rx=(m_rx<<1)|miso; idle(half); m_sck=0; }
  idle(half); m_cs=1; idle(4*half); }
int main(int argc,char**argv){ int div=argc>1?atoi(argv[1]):6; env=spi_env; power_on(); bool ok=true;
  CH=0; program(cat({I_order(1),I_line(0,0),I_clock(GENERATE,div,1,0,0),I_out(3,0),I_wdog(4000),I_start(0,0,0,1),I_main(16,1)}));
  CH=1; program(cat({I_order(1),I_line(0,3),I_clock(SYNC,0,1,0),I_start(0,0,0,0,2),I_main(16,0,0,0,3),I_run(0)}));
  unsigned mosi[]={0xA55A,0x1234,0xF00F}, miso[]={0x9F41,0xC3E7,0x0180};
  for(int r=0;r<3;r++) sl_reply.push_back(miso[r]);
  CH=0; program(cat({I_data(8,mosi[0]>>8),I_data(8,mosi[0]&0xFF),I_run(0)}));
  for(int r=1;r<3;r++){ idle(40*div*2); program(cat({I_data(8,mosi[r]>>8),I_data(8,mosi[r]&0xFF)})); }
  idle(40*div*2); wait_return();
  V expb; for(int r=0;r<3;r++){ expb.push_back({8,miso[r]>>8}); expb.push_back({8,miso[r]&0xFF}); }
  char d[48]; snprintf(d,sizeof d," (SCK half period %d clocks)",div);
  ok&=report("controller: slave received MOSI words",sl_words==std::vector<unsigned>({0xA55A,0x1234,0xF00F}),std::string(" slave got")+showst(sl_words)+d);
  ok&=report("controller: chain B read MISO words",got[1]==expb,show(got[1]));
  ok&=report("controller: chain A 3 frames complete",status[0]==std::vector<unsigned>({1,1,1}),showst(status[0]));
  scenario=1; clear_results(); CH=0; program(I_clear()); CH=1; program(I_clear());
  CH=1; program(cat({I_order(1),I_line(0,0),I_clock(SYNC,0,1,0),I_start(0,0,0,0,2),I_main(16,0,0,0,0),I_run(0)}));
  CH=0; program(cat({I_order(1),I_line(0,0),I_clock(SYNC,0,1,0),I_out(3,0),I_start(0,0,0,1),I_main(16,1),I_data(8,0x5E),I_data(8,0xC4),I_run(0)}));
  master_transfer(0x6B2D,10); unsigned first=m_rx;
  CH=0; program(cat({I_data(8,0x81),I_data(8,0x7E)}));
  master_transfer(0xBEEF,10); unsigned second=m_rx; wait_return();
  ok&=report("target: chip read master's MOSI",got[1]==V({{8,0x6B},{8,0x2D},{8,0xBE},{8,0xEF}}),show(got[1]));
  char e[48]; snprintf(e,sizeof e," master got %04X %04X",first,second);
  ok&=report("target: chip answered on MISO",first==0x5EC4&&second==0x817E,e);
  printf(ok?"ALL PASS\n":"FAILED\n"); return !ok; }
