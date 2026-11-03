// =============================================================================
// Project: ProEm - Open Source Protocol Emulator
// File: sim/t_manchester.cpp
// Type: Test, pin level (CXXRTL)
// Device under test: protocol_emulator (src/top/protocol_emulator.sv)
// Author: Paul Vincent Bezzina
// Language: C++14
// Description:
// =============================================================================

#include "bench.h"
int hi_run=0, max_run=0, released=0;
void m_env(){ int oe=t.p_data__oe__a.get<bool>(); int d=oe?t.p_data__out__a.get<bool>():0; pin_in=d; if(d) hi_run++; else { if(hi_run>max_run) max_run=hi_run; hi_run=0; } if(!oe) released++; }
int main(int argc,char**argv){ int div=argc>1?atoi(argv[1]):6; int endlen=div+div/2+1; env=m_env; power_on(); bool ok=true;
  CH=1; program(cat({I_line(3,0),I_clock(RECOVER,div,0,0,0,1),I_start(0xD5,8,0,0,0),I_main(0,0,1,0,0),I_end(endlen,0,(1u<<endlen)-1),I_run(0)}));
  CH=0; program(cat({I_line(3,0),I_clock(RECOVER,div),I_out(1,0,0,1),I_start(0x55,8,0,1),I_hdr(1,0x55,8,0,1),I_hdr(2,0x55,8,0,1),I_hdr(3,0x55,8,0,1),I_hdr(4,0x55,8,0,1),I_hdr(5,0x55,8,0,1),I_hdr(6,0x55,8,0,1),I_main(64,1)}));
  unsigned body[]={0xD5,0xFF,0xFF,0x12,0x34,0x08,0x00,0xC7};
  for(int round=0;round<2;round++){ clear_results(); max_run=0; released=0;
    B p; for(unsigned b:body){ B d=I_data(8,b^(round*0x5A*(b!=0xD5))); p.insert(p.end(),d.begin(),d.end()); } B r=I_run(2); p.insert(p.end(),r.begin(),r.end()); program(p);
    idle(200*div*8); wait_return();
    V exp; for(int i=1;i<8;i++) exp.push_back({8,body[i]^(round*0x5A)});
    char d[96]; snprintf(d,sizeof d," | longest high %d clocks (TP_IDL), released %d",max_run,released>0);
    ok&=report("Manchester TX on A, received by B's decoder",got[1]==exp&&status[1]==std::vector<unsigned>({1})&&status[0]==std::vector<unsigned>({1}),show(got[1])+" |"+showst(status[1])+d);
    ok&=report("  end of frame: line high for 2 bit times, then released",max_run>=2*div&&released>0); }
  printf(ok?"ALL PASS\n":"FAILED\n"); return !ok; }
