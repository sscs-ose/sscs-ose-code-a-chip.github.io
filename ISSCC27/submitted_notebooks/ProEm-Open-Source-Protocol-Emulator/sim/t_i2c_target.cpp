// =============================================================================
// Project: ProEm - Open Source Protocol Emulator
// File: sim/t_i2c_target.cpp
// Type: Test, pin level (CXXRTL)
// Device under test: protocol_emulator (src/top/protocol_emulator.sv)
// Author: Paul Vincent Bezzina
// Language: C++14
// Description:
// =============================================================================

#include "bench.h"
int HALF=60, csda=1, cscl=1;
std::string bus;
int sda_line(){ return csda && !t.p_data__oe__a.get<bool>(); }
void t_env(){ pin_in=sda_line()|(cscl<<2); }
void half(){ idle(HALF); }
void c_start(){ csda=1; cscl=1; half(); csda=0; half(); cscl=0; half(); bus+="S "; }
void c_rstart(){ csda=1; half(); cscl=1; half(); csda=0; half(); cscl=0; half(); bus+="Sr "; }
void c_stop(){ csda=0; half(); cscl=1; half(); csda=1; half(); bus+="P "; }
int c_bit(int b){ csda=b; half(); cscl=1; idle(HALF/2); int r=sda_line(); idle(HALF-HALF/2); cscl=0; return r; }
int c_write(unsigned v){ char s[8]; snprintf(s,sizeof s,"%02X ",v); bus+=s; for(int i=7;i>=0;i--) c_bit((v>>i)&1); int ack=!c_bit(1); bus+=ack?"A ":"N "; return ack; }
unsigned c_read(int ack){ unsigned v=0; for(int i=0;i<8;i++) v=(v<<1)|c_bit(1); c_bit(!ack); char s[8]; snprintf(s,sizeof s,"%02X ",v); bus+=s; bus+=ack?"A ":"N "; return v; }
bool check(const char*name,const std::string&expbus,V exphost,std::vector<unsigned> expst){ idle(400); wait_return();
  bool ok=bus==expbus&&got[0]==exphost&&status[0]==expst;
  ok=report(name,ok,std::string(" bus: ")+bus+"|"+show(got[0])+" |"+showst(status[0])); bus.clear(); clear_results(); return ok; }
int main(int argc,char**argv){ if(argc>1) HALF=atoi(argv[1]); env=t_env; power_on(); bool ok=true;
  CH=0; program(cat({I_order(1),I_line(0,0),I_clock(SYNC,0,2,0),I_out(2,0,0,0,1),I_start(0,0,0,0,0),
    I_hdr(1,0x42,7,0,0),I_hdr(2,0,1,1,0,0,0,1),I_hdr(3,0,1,0,1),I_branch(0,GO_WRITE,GO_READ,0,2,0x01,0x01),
    I_main(64,2,1,1,0),I_run(0)}));
  { B p=cat({I_data(8,0x5A),I_data(8,0xC3)}); program(p); }
  c_start(); c_write(0x84); c_write(0x11); c_write(0x22); c_stop();
  ok&=check("controller writes 2 bytes to 0x42",
    "S 84 A 11 A 22 A P ",{{1,0},{8,0x11},{8,0x22}},{0x01});
  c_start(); c_write(0x85); c_read(1); c_read(0); c_stop();
  ok&=check("controller reads 2 bytes (branch to write; NACK entry)",
    "S 85 A 5A A C3 N P ",{{1,1},{0,0x02}},{0x41});
  c_start(); c_write(0xA0); c_stop();
  ok&=check("wrong address 0x50: no ACK, frame aborted",
    "S A0 N P ",{},{0x02});
  program(I_data(8,0x77));
  c_start(); c_write(0x84); c_write(0x07); c_rstart(); c_write(0x85); c_read(0); c_stop();
  ok&=check("write register 07, repeated START, read 1 byte",
    "S 84 A 07 A Sr 85 A 77 N P ",{{1,0},{8,0x07},{1,1},{0,0x02}},{0x01,0x41});
  printf(ok?"ALL PASS\n":"FAILED\n"); return !ok; }
