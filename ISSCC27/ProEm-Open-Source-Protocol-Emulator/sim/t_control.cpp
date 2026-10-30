// =============================================================================
// Project: ProEm - Open Source Protocol Emulator
// File: sim/t_control.cpp
// Type: Test, pin level (CXXRTL)
// Device under test: protocol_emulator (src/top/protocol_emulator.sv)
// Author: Paul Vincent Bezzina
// Language: C++14
// Description:
// =============================================================================

#include "bench.h"
int sck=0, sd=0;
void c_env(){ pin_in=sd|(sck<<1); }
void bit(int b){ sd=b; idle(3); sck=1; idle(3); sck=0; }
void byteLSB(unsigned v){ for(int i=0;i<8;i++) bit((v>>i)&1); }
void bits(const char*s){ for(;*s;s++) bit(*s=='1'); }
bool check(const char*name,V exp,std::vector<unsigned> st){ idle(40); wait_return(); bool ok=got[0]==exp&&status[0]==st; ok=report(name,ok,show(got[0])+" |"+showst(status[0])); clear_results(); return ok; }
int main(int argc,char**argv){ if(argc>1) INS_R=atoi(argv[1]); env=c_env; power_on(); char d[48]; snprintf(d,sizeof d," (%d clocks per bit)",INS_R); bool ok=report("auto-baud locks on the 0x55 sync byte",baud_ok(),d);
  CH=0; program(cat({I_clock(SYNC,0,1,0),I_start(0xD5,8,1,0),I_hdr(1,0xFF,8,1,0),I_hdr(2,0x12,8,1,0),I_hdr(3,0x34,8,0,0),I_main(16,0),I_run(0)}));
  auto frame=[&](unsigned h2){ bits("10101010"); bits("10101011"); byteLSB(0xFF); byteLSB(h2); byteLSB(0x34); };
  frame(0x12); byteLSB(0xAB); byteLSB(0xCD);
  ok&=check("read frame, 3 headers, 3 captured",{{8,0xD5},{8,0xFF},{8,0x12},{8,0xAB},{8,0xCD}},{1});
  frame(0x13);
  ok&=check("header mismatch: captures dropped, abort status",{},{2});
  program(I_wdog(300)); frame(0x12); byteLSB(0x11); idle(600);
  ok&=check("watchdog: stalled read frame -> abort + timeout",{{8,0xD5},{8,0xFF},{8,0x12},{8,0x11}},{6});
  program(I_wdog(0)); frame(0x12); byteLSB(0x22); program(I_halt()); byteLSB(0x33);
  ok&=check("HALT mid-frame: no status, rest ignored",{{8,0xD5},{8,0xFF},{8,0x12},{8,0x22}},{});
  ok&=report("HALT disarms the chain",!t.p_armed__a.get<bool>());
  frame(0x12); byteLSB(0x44); byteLSB(0x55);
  ok&=check("disarmed chain ignores a frame",{},{});
  program(I_run(0)); frame(0x12); byteLSB(0x5A); byteLSB(0xA5);
  ok&=check("RUN re-arms",{{8,0xD5},{8,0xFF},{8,0x12},{8,0x5A},{8,0xA5}},{1});
  program(cat({I_clear(),I_clock(SYNC,0,1,0),I_start(0x2A,6,1,0),I_main(8,0),I_run(0)}));
  bits("111010101"); byteLSB(0x3C);
  ok&=check("CLEAR, then 6-bit START given as a plain number",{{6,0x2A},{8,0x3C}},{1});
  program(cat({I_order(1),I_start(0x2A,6,1,0),I_main(8,0),I_run(0)}));
  bits("000101010"); for(int i=7;i>=0;i--) bit((0x3C>>i)&1);
  ok&=check("same START, MSB first",{{6,0x2A},{8,0x3C}},{1});
  program(I_link(5)); RET_R=5;
  program(cat({I_order(0),I_start(0xD5,8,1,0),I_main(16,0),I_run(0)})); bits("10101011"); byteLSB(0x0F); byteLSB(0xF0);
  ok&=check("LINK 5: frame read back over a 5-clock link",{{8,0xD5},{8,0x0F},{8,0xF0}},{1});
  program(I_link(0)); RET_R=0;
  program(B{0xF7,0,0,0}); CH=0; program(I_hdr(7,0,8,0,0)); wait_return();
  ok&=report("BRANCH 7 and HDR 7 -> cmd_error flag",global_flags.size()>=1&&(global_flags[0]&2),showst(global_flags)); global_flags.clear();
  send_byte(0x00,0); settle(); wait_return();
  ok&=report("stop bit low -> rx_error flag",global_flags.size()==1&&global_flags[0]==1,showst(global_flags)); global_flags.clear();
  program(cat({I_clear(),I_start(0,1,0,1),I_main(64,1)})); { B p; for(int i=0;i<9;i++){ B x=I_data(8,i); p.insert(p.end(),x.begin(),x.end()); } program(p); } wait_return();
  ok&=report("9th DATA into the 8-entry host FIFO -> drop flag",global_flags.size()==1&&global_flags[0]==4&&t.p_host__full__a.get<bool>(),showst(global_flags));
  printf(ok?"ALL PASS\n":"FAILED\n"); return !ok; }
