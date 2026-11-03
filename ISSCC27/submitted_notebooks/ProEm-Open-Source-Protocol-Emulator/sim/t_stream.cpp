// =============================================================================
// Project: ProEm - Open Source Protocol Emulator
// File: sim/t_stream.cpp
// Type: Test, pin level (CXXRTL)
// Device under test: protocol_emulator (src/top/protocol_emulator.sv)
// Author: Paul Vincent Bezzina
// Language: C++14
// Description:
// =============================================================================

#include "bench.h"
int R=64, rxs=0, rxc=0, rxi=0; unsigned rxb=0; std::vector<unsigned> heard;
int psck=0; unsigned shreg=0; int nbits=0; std::vector<unsigned> spi_got;
int mode=0;
void s_env(){
  if(mode==0){ int lv=t.p_data__oe__a.get<bool>()? t.p_data__out__a.get<bool>() : 1;
    if(rxs==0){ if(!lv){ rxs=1; rxc=R/2; } }
    else if(--rxc==0){ if(rxs==1){ if(lv) rxs=0; else { rxs=2; rxi=0; rxb=0; rxc=R; } }
      else if(rxs==2){ rxb|=(unsigned)lv<<rxi; rxi++; rxc=R; if(rxi==8) rxs=3; }
      else { if(lv) heard.push_back(rxb); rxs=0; } } }
  else { int sck=t.p_clock__oe__a.get<bool>()? t.p_clock__out__a.get<bool>() : 0;
    if(sck && !psck){ shreg=(shreg<<1)|t.p_data__out__a.get<bool>(); if(++nbits==8){ spi_got.push_back(shreg&0xFF); nbits=0; } }
    psck=sck; pin_in=sck<<1; } }
int main(int argc,char**argv){ INS_R=7; env=s_env; power_on(); bool ok=true;
  CH=0; mode=0;
  program(cat({I_order(0),I_line(0,0),I_clock(ASYNC,16),I_out(3,1),I_start(0,1,0,1),I_main(32,1),I_data(8,0x55),I_run(2)}));
  idle(2000); wait_return();
  ok&=report("underrun: 8 of 32 bits loaded, frame aborts",status[0]==std::vector<unsigned>({0x22})&&t.p_data__out__a.get<bool>(),showst(status[0]));
  clear_results(); heard.clear();
  program(I_clear()); R=64;
  unsigned msg[12]={0x48,0x65,0x6C,0x6C,0x6F,0x2C,0x20,0x50,0x72,0x6F,0x45,0x6D};
  B q; auto add=[&](const B&b){ q.insert(q.end(),b.begin(),b.end()); };
  for(int i=0;i<12;i++){ add(I_data(8,msg[i])); add(I_data(1,1)); if(i<11) add(I_data(1,0)); }
  program(cat({I_order(0),I_line(0,0),I_clock(ASYNC,R),I_out(3,1),I_start(0,1,0,1),I_main(8+11*10+1,1)}));
  B first(q.begin(),q.begin()+6), rest(q.begin()+6,q.end());
  program(cat({first,I_run(2)})); program(rest); idle(3000); wait_return();
  ok&=report("UART stream: 12 bytes fed while the frame runs (FIFO holds 8)",heard==std::vector<unsigned>(msg,msg+12)&&status[0]==std::vector<unsigned>({0x01}),std::string(" heard")+showst(heard)+" |"+showst(status[0]));
  clear_results(); mode=1; program(I_clear());
  program(cat({I_order(1),I_line(0,0),I_clock(GENERATE,4,1,0,0),I_out(3,0),I_start(0,0,0,1),I_main(160,1)}));
  B s; std::vector<unsigned> sent; for(int i=0;i<20;i++){ unsigned v=(i*37+11)&0xFF; sent.push_back(v); B x=I_data(8,v); s.insert(s.end(),x.begin(),x.end()); }
  B s1(s.begin(),s.begin()+4), s2(s.begin()+4,s.end());
  program(cat({s1,I_run(2)})); program(s2); idle(2000); wait_return();
  ok&=report("SPI stream: 20 bytes, clock pauses while waiting for data",spi_got==sent&&status[0]==std::vector<unsigned>({0x01}),std::string(" got")+showst(spi_got)+" |"+showst(status[0]));
  printf(ok?"ALL PASS\n":"FAILED\n"); return !ok; }
