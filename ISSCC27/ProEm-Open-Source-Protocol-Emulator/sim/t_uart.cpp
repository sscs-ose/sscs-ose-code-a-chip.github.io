// =============================================================================
// Project: ProEm - Open Source Protocol Emulator
// File: sim/t_uart.cpp
// Type: Test, pin level (CXXRTL)
// Device under test: protocol_emulator (src/top/protocol_emulator.sv)
// Author: Paul Vincent Bezzina
// Language: C++14
// Description:
// =============================================================================

#include "bench.h"
double txr=40.8; std::deque<int> txbits; double txclock=0; int txlevel=1;
int rxs=0, rxc=0, rxi=0; unsigned rxb=0; std::vector<unsigned> heard; int R=40;
void uart_env(){ if(!txbits.empty()){ txclock+=1; if(txclock>=txr){ txclock-=txr; txlevel=txbits.front(); txbits.pop_front(); } } else txlevel=1;
  pin_in=(pin_in&~1u)|txlevel;
  int lv=t.p_data__oe__b.get<bool>()? t.p_data__out__b.get<bool>() : 1;
  if(rxs==0){ if(!lv){ rxs=1; rxc=R/2; } }
  else if(--rxc==0){ if(rxs==1){ if(lv) rxs=0; else { rxs=2; rxi=0; rxb=0; rxc=R; } }
    else if(rxs==2){ rxb|=(unsigned)lv<<rxi; rxi++; rxc=R; if(rxi==8) rxs=3; }
    else { if(lv) heard.push_back(rxb); rxs=0; } } }
void uart_send(unsigned b){ txbits.push_back(0); for(int i=0;i<8;i++) txbits.push_back((b>>i)&1); txbits.push_back(1); }
int main(int argc,char**argv){ if(argc>1) INS_R=atoi(argv[1]); if(argc>2) txr=atof(argv[2]); env=uart_env; power_on(); bool ok=report("auto-baud locked",baud_ok());
  CH=0; program(cat({I_line(0,0),I_clock(ASYNC,R),I_start(0x00,1,0,0,0),I_main(9,0,0,0,0),I_run(0)}));
  CH=1; program(cat({I_line(0,0),I_clock(ASYNC,R),I_out(3,1),I_start(0x00,1,0,1),I_main(9,1),I_data(8,0x48),I_data(1,1),I_data(8,0x69),I_data(1,1),I_data(8,0x21),I_data(1,1),I_run(0)}));
  unsigned msg[]={0x55,0xA3,0x00,0xFF,0x7E};
  for(unsigned b:msg) uart_send(b);
  for(int i=0;i<3000 && !txbits.empty();i++) idle(100);
  idle(2000); wait_return();
  V expa; std::vector<unsigned> sta; for(unsigned b:msg){ expa.push_back({8,b}); expa.push_back({1,1}); sta.push_back(0x01); }
  char d[64]; snprintf(d,sizeof d," (sender at %.1f clocks/bit)",txr);
  ok&=report("UART RX on chain A: 5 bytes + stop bits",got[0]==expa&&status[0]==sta,show(got[0])+" |"+showst(status[0])+d);
  ok&=report("UART TX on chain B: \"Hi!\" on the line",heard==std::vector<unsigned>({0x48,0x69,0x21}),std::string(" heard ")+showst(heard));
  ok&=report("chain B: 3 frames complete",status[1]==std::vector<unsigned>({1,1,1}),showst(status[1]));
  printf(ok?"ALL PASS\n":"FAILED\n"); return !ok; }
