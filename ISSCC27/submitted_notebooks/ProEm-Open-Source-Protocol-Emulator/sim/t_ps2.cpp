// =============================================================================
// Project: ProEm - Open Source Protocol Emulator
// File: sim/t_ps2.cpp
// Type: Test, pin level (CXXRTL)
// Device under test: protocol_emulator (src/top/protocol_emulator.sv)
// Author: Paul Vincent Bezzina
// Language: C++14
// Description:
// =============================================================================

#include "bench.h"
int kclk=1, kdat=1;
void ps2_env(){ pin_in=(kclk<<4)|(kdat<<5); }
int parity(unsigned b){ int p=1; for(int i=0;i<8;i++) p^=(b>>i)&1; return p; }
void key(unsigned b,int half){ int bits[11]; bits[0]=0; for(int i=0;i<8;i++) bits[1+i]=(b>>i)&1; bits[9]=parity(b); bits[10]=1;
  for(int i=0;i<11;i++){ kdat=bits[i]; idle(half/2); kclk=0; idle(half); kclk=1; idle(half/2); } kdat=1; idle(4*half); }
int main(int argc,char**argv){ int half=argc>1?atoi(argv[1]):40; env=ps2_env; power_on(); bool ok=true;
  CH=1; program(cat({I_line(0,5),I_clock(SYNC,0,4,1),I_start(0,1,0,0,5),I_main(10,0,0,0,5),I_run(0)}));
  unsigned keys[]={0x1C,0xF0,0x1C,0x5A};
  for(unsigned k:keys) key(k,half);
  wait_return();
  V exp; std::vector<unsigned> st; for(unsigned k:keys){ exp.push_back({8,k}); exp.push_back({2,(unsigned)(parity(k)|2)}); st.push_back(1); }
  ok&=report("PS/2 device to host: A, release A, Enter",got[1]==exp&&status[1]==st,show(got[1])+" |"+showst(status[1]));
  printf(ok?"ALL PASS\n":"FAILED\n"); return !ok; }
