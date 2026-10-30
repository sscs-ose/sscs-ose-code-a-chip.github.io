// =============================================================================
// Project: ProEm - Open Source Protocol Emulator
// File: sim/t_branch.cpp
// Type: Test, pin level (CXXRTL)
// Device under test: protocol_emulator (src/top/protocol_emulator.sv)
// Author: Paul Vincent Bezzina
// Language: C++14
// Description:
// =============================================================================

#include "bench.h"
int scenario=0;
int s_drive=1, s_pscl=0, s_rises=0; unsigned s_ack=1; unsigned long long s_data=0;
int s_bit_for(int k){ if(k>=10&&k<=12) return (s_ack>>(k-10))&1; if(s_ack==1&&k>=13&&k<=45) return (s_data>>(k-13))&1; return 1; }
int c_mine=1, c_active=0, c_lost=0, c_t=0, c_period=50; std::vector<int> c_frame, c_heard;
int chip_level(){ return !t.p_data__oe__a.get<bool>(); }
void b_env(){
  if(scenario==0){
    int scl=!t.p_clock__oe__a.get<bool>();
    int sda=chip_level() && s_drive;
    if(scl && !s_pscl) s_rises++;
    if(!scl && s_pscl) s_drive=s_bit_for(s_rises+1);
    s_pscl=scl; pin_in=sda|(scl<<1);
  } else {
    int bus=chip_level() && c_mine;
    if(!c_active && !bus && c_heard.empty()){ c_active=1; c_t=0; c_lost=0; }
    if(c_active){ int k=c_t/c_period, ph=c_t%c_period;
      if(k<(int)c_frame.size()){ if(ph==0) c_mine=c_lost?1:c_frame[k]; if(ph==c_period/2){ c_heard.push_back(bus); if(!c_lost && c_frame[k]==1 && bus==0){ c_lost=1; c_mine=1; } } }
      else { c_mine=1; c_active=0; }
      c_t++; }
    pin_in=(chip_level() && c_mine); } }
std::vector<int> can_frame(unsigned id,unsigned d){ std::vector<int> f; f.push_back(0); for(int i=10;i>=0;i--) f.push_back((id>>i)&1); for(int i=7;i>=0;i--) f.push_back((d>>i)&1); return f; }
std::string bits(const std::vector<int>&v){ std::string s; for(int b:v) s+=b?'1':'0'; return s; }
bool swd(const char*name,unsigned ack,unsigned long long data,V exphost,std::vector<unsigned> expst){ s_ack=ack; s_data=data; s_rises=0; s_drive=1; clear_results();
  program(I_run(0)); idle(3000); wait_return();
  bool ok=got[0]==exphost&&status[0]==expst&&chip_level();
  return report(name,ok,show(got[0])+" |"+showst(status[0])); }
bool can(const char*name,unsigned mine,unsigned other,bool win){ c_frame=can_frame(other,0x5A); c_heard.clear(); c_active=0; c_mine=1; clear_results();
  program(cat({I_data(8,mine>>3),I_data(3,mine&7),I_data(8,0xA5),I_run(2)})); idle(2500); wait_return();
  std::vector<int> expbus=win? can_frame(mine,0xA5) : c_frame;
  bool ok=c_heard==expbus && status[0]==std::vector<unsigned>(1,win?0x01u:0xC2u) && chip_level();
  return report(name,ok,std::string(" bus ")+bits(c_heard)+" |"+showst(status[0])); }
int main(int argc,char**argv){ env=b_env; power_on(); bool ok=true;
  scenario=0; CH=0;
  program(cat({I_order(0),I_line(0,0),I_clock(GENERATE,6,1,0,0),I_out(2,0),I_wdog(2000),
    I_start(0xA5,8,0,1),I_hdr(1,0,1,0,0,0,0,1),I_hdr(2,0,3,1,0,0,0,1),I_branch(0,GO_READ,ABORT,0,2,0x07,0x01),I_main(33,0)}));
  unsigned long long d=0x1DEADBEEFull;
  ok&=swd("SWD-style read, ACK OK: branch continues to data",1,d,{{3,1},{8,0xEF},{8,0xBE},{8,0xAD},{8,0xDE},{1,1}},{0x41});
  ok&=swd("SWD-style read, ACK WAIT: branch aborts, ACK returned",2,d,{{3,2}},{0x82});
  ok&=swd("SWD-style read, ACK FAULT: branch aborts",4,d,{{3,4}},{0x82});
  ok&=swd("ACK OK again after the aborts",1,0x012345678ull,{{3,1},{8,0x78},{8,0x56},{8,0x34},{8,0x12},{1,0}},{0x41});
  scenario=1; program(I_clear());
  program(cat({I_order(1),I_line(0,0),I_clock(ASYNC,50),I_out(2,0),I_start(0,1,0,1),I_main(19,1),I_branch(0,ABORT,KEEP,1,0,0,0)}));
  ok&=can("CAN-style arbitration: chip 0x456 loses to 0x123",0x456,0x123,false);
  ok&=can("CAN-style arbitration: chip 0x123 beats 0x456",0x123,0x456,true);
  ok&=can("lose again, then line released and reusable",0x3F0,0x3EF,false);
  printf(ok?"ALL PASS\n":"FAILED\n"); return !ok; }
