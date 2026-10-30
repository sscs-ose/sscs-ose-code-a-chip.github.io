// =============================================================================
// Project: ProEm - Open Source Protocol Emulator
// File: sim/t_usb.cpp
// Type: Test, pin level (CXXRTL)
// Device under test: protocol_emulator (src/top/protocol_emulator.sv)
// Author: Paul Vincent Bezzina
// Language: C++14
// Description:
// =============================================================================

#include "bench.h"
int scenario=0; double tclk=20.0, tbit=1000.0/1.5, now=0; std::vector<std::pair<double,int>> ev; size_t ei=0; int dp=0, dm=1;
struct Rx { int st=0, cnt=0, level=0, ones=0, se0=0; std::vector<int> bits; std::string shape; } mon;
void usb_env(){ now+=tclk;
  if(scenario==0){ while(ei<ev.size() && ev[ei].first<=now){ int s=ev[ei].second; dp=(s==1||s==3); dm=(s==0||s==3); ei++; } pin_in=dp|(dm<<1); }
  else { int op=t.p_data__oe__b.get<bool>(), pp=t.p_pair__oe__b.get<bool>(); int d=op?t.p_data__out__b.get<bool>():0; int m=pp?t.p_pair__out__b.get<bool>():1;
    if(scenario==2) pin_in=d|(m<<1);
    if(mon.st==0){ if(op && d){ mon.st=1; mon.cnt=16; mon.level=0; mon.ones=0; mon.bits.clear(); mon.shape.clear(); } }
    else if(mon.st==1 && --mon.cnt==0){ mon.cnt=33;
      if(!d && !m){ mon.se0++; mon.shape+="0"; }
      else if(mon.se0){ mon.shape+= (!d && m)?"J":"?"; mon.st=2; mon.cnt=40; }
      else { int bit=(d==mon.level); mon.level=d; if(mon.ones==6){ if(bit) mon.shape+="!"; mon.ones=0; } else { mon.bits.push_back(bit); mon.ones= bit? mon.ones+1 : 0; } } }
    else if(mon.st==2 && --mon.cnt==0){ mon.shape+= (!op && !pp)?"R":"D"; mon.st=3; } } }
void encode(const std::vector<unsigned>&bytes,int se1_at=-1,int nostuff=0){ ev.clear(); ei=0; double t=now+2000; int level=0, ones=0, nb=0; ev.push_back({t,0});
  auto put=[&](int b){ if(!b) level=!level; ev.push_back({t,level?1:0}); t+=tbit; };
  for(unsigned by:bytes) for(int k=0;k<8;k++){ int b=(by>>k)&1; if(nb++==se1_at){ ev.push_back({t,3}); t+=tbit; }
    put(b); if(b){ if(++ones==6 && !nostuff){ put(0); ones=0; } } else ones=0; }
  ev.push_back({t,2}); t+=2*tbit; ev.push_back({t,0}); t+=tbit; ev.push_back({t+1,0});
  while(ei<ev.size()) clk(); idle(300); }
std::vector<unsigned> tobytes(const std::vector<int>&b){ std::vector<unsigned> o; for(size_t i=0;i+8<=b.size();i+=8){ unsigned v=0; for(int k=0;k<8;k++) v|=b[i+k]<<k; o.push_back(v); } return o; }
int main(){ env=usb_env; pin_in=2; power_on(); bool ok=true;
  CH=0; program(cat({I_link(4),I_line(2,0,6,1),I_clock(RECOVER,33,0,0,0,2),I_start(0x80,8,0,0,0),I_main(0,0,1,0,0),I_end(2,0,0x0003,1,0,1,1),I_run(0)})); RET_R=4;
  clear_results(); encode({0x80,0xC3,0xFF,0xFF,0x01,0x80,0x3E,0xA5}); wait_return();
  ok&=report("RX: DATA0 with stuffed bits, ends on SE0",got[0]==V({{8,0xC3},{8,0xFF},{8,0xFF},{8,0x01},{8,0x80},{8,0x3E},{8,0xA5}})&&status[0]==std::vector<unsigned>({1}),show(got[0])+" |"+showst(status[0]));
  clear_results(); encode({0x80,0x4B,0x12,0x34},28); wait_return();
  ok&=report("RX: SE1 mid-packet -> abort + line_error",status[0]==std::vector<unsigned>({0x0A}),show(got[0])+" |"+showst(status[0]));
  clear_results(); encode({0x80,0xD2,0xFF,0x7F},-1,1); wait_return();
  ok&=report("RX: seven 1s (missing stuff bit) -> abort + line_error",status[0]==std::vector<unsigned>({0x0A}),show(got[0])+" |"+showst(status[0]));
  clear_results(); encode({0x80,0x69,0x5A}); wait_return();
  ok&=report("RX: next packet received normally",got[0]==V({{8,0x69},{8,0x5A}})&&status[0]==std::vector<unsigned>({1}),show(got[0])+" |"+showst(status[0]));
  scenario=1; clear_results();
  CH=1; program(cat({I_line(2,0,6,1),I_clock(RECOVER,33),I_out(1,0,1,1),I_start(0x80,8,0,1),I_hdr(1,0x4B,8,0,1),I_main(32,1),I_data(8,0xFF),I_data(8,0xFF),I_data(8,0x7E),I_data(8,0x00),I_run(2)}));
  idle(3000);
  std::vector<unsigned> txb=tobytes(mon.bits);
  ok&=report("TX: SYNC, PID, data with stuffing, decoded by model",txb==std::vector<unsigned>({0x80,0x4B,0xFF,0xFF,0x7E,0x00}),std::string(" ")+showst(txb));
  ok&=report("TX: end of packet = SE0 SE0 J, then released",mon.shape=="00JR",std::string(" ")+mon.shape);
  scenario=2; mon=Rx(); clear_results();
  CH=1; program(cat({I_data(8,0x11),I_data(8,0x22),I_data(8,0xFC),I_data(8,0x3F),I_run(2)}));
  idle(3000); wait_return();
  ok&=report("loopback: chain B USB TX into chain A USB RX",got[0]==V({{8,0x4B},{8,0x11},{8,0x22},{8,0xFC},{8,0x3F}})&&status[0]==std::vector<unsigned>({1}),show(got[0])+" |"+showst(status[0]));
  printf(ok?"ALL PASS\n":"FAILED\n"); return !ok; }
