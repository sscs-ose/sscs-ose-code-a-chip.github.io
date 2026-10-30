// =============================================================================
// Project: ProEm - Open Source Protocol Emulator
// File: sim/t_i2c.cpp
// Type: Test, pin level (CXXRTL)
// Device under test: protocol_emulator (src/top/protocol_emulator.sv)
// Author: Paul Vincent Bezzina
// Language: C++14
// Description:
// =============================================================================

#include "bench.h"
struct Dev { unsigned addr=0x48, regs[256]={0}, ptr=0, shift=0, cur=0; int st=0, rc=0, sda_low=0, scl_hold=0, stretch=0, first=1, ack=0, rw=0; std::string log; } dev;
enum { D_IDLE, D_ADDR, D_WRITE, D_READ, D_WAIT };
int psda=1, pscl=1;
void logb(unsigned b){ char s[8]; snprintf(s,sizeof s,"%02X ",b); dev.log+=s; }
void i2c_env(){
  int sda=!t.p_data__oe__a.get<bool>() && !dev.sda_low;
  int scl=!t.p_clock__oe__a.get<bool>() && !(dev.scl_hold>0);
  if(dev.scl_hold>0) dev.scl_hold--;
  if(scl && pscl && psda && !sda){ dev.log+= (dev.st==D_IDLE)?"S ":"Sr "; dev.st=D_ADDR; dev.rc=0; dev.shift=0; dev.sda_low=0; }
  else if(scl && pscl && !psda && sda){ dev.log+="P "; dev.st=D_IDLE; dev.sda_low=0; }
  else if(scl && !pscl && dev.st!=D_IDLE){ dev.rc++;
    if(dev.rc<=8 && (dev.st==D_ADDR||dev.st==D_WRITE)) dev.shift=((dev.shift<<1)|sda)&0xFF;
    if(dev.rc==9 && dev.st==D_READ){ dev.log+= sda?"N ":"A "; dev.ack=!sda; } }
  else if(!scl && pscl && dev.st!=D_IDLE){
    if(dev.rc==8){
      if(dev.st==D_ADDR){ logb(dev.shift); dev.ack=(dev.shift>>1)==dev.addr; dev.rw=dev.shift&1; dev.log+= dev.ack?"A ":"N "; dev.sda_low=dev.ack; }
      else if(dev.st==D_WRITE){ logb(dev.shift); if(dev.first){ dev.ptr=dev.shift; dev.first=0; } else dev.regs[dev.ptr++&0xFF]=dev.shift; dev.log+="A "; dev.sda_low=1; dev.ack=1; }
      else if(dev.st==D_READ) dev.sda_low=0; }
    else if(dev.rc==9){ dev.rc=0; dev.sda_low=0; dev.shift=0; if(dev.stretch) dev.scl_hold=dev.stretch;
      if(dev.st==D_ADDR){ if(!dev.ack) dev.st=D_WAIT; else if(dev.rw){ dev.st=D_READ; dev.cur=dev.regs[dev.ptr++&0xFF]; logb(dev.cur); dev.sda_low=!((dev.cur>>7)&1); } else { dev.st=D_WRITE; dev.first=1; } }
      else if(dev.st==D_READ){ if(dev.ack){ dev.cur=dev.regs[dev.ptr++&0xFF]; logb(dev.cur); dev.sda_low=!((dev.cur>>7)&1); } else dev.st=D_WAIT; } }
    else if(dev.st==D_READ && dev.rc>=1 && dev.rc<8) dev.sda_low=!((dev.cur>>(7-dev.rc))&1); }
  psda=sda; pscl=scl; pin_in=(sda)|(scl<<1); }
bool txn(const char*name,const B&prog,const std::string&explog,V exphost,std::vector<unsigned> expst){ dev.log.clear(); clear_results(); program(prog); idle(20000); wait_return();
  bool ok=dev.log==explog && got[0]==exphost && status[0]==expst;
  ok&=report(name,ok,std::string(" bus: ")+dev.log+"|"+show(got[0])+" |"+showst(status[0])); return ok; }
int main(int argc,char**argv){ int div=argc>1?atoi(argv[1]):10; env=i2c_env; power_on(); bool ok=true;
  CH=0; program(cat({I_order(1),I_line(0,0),I_clock(GENERATE,div,1,0,1),I_out(2,1,0,0,1),I_wdog(60000),I_start(0x90,8,0,1),I_hdr(1,0,1,0,0),I_hdr(2,0x05,8,0,1),I_hdr(3,0,1,0,0),I_hdr(4,0x91,8,0,1,1,1),I_hdr(5,0,1,0,0,1),I_main(16,2,0,1)}));
  ok&=txn("RUN WRITE: register 05 <- A1 B2",cat({I_data(8,0xA1),I_data(8,0xB2),I_run(2)}),"S 90 A 05 A A1 A B2 A P ",{},{1});
  ok&=report("device registers written",dev.regs[5]==0xA1&&dev.regs[6]==0xB2);
  ok&=txn("RUN READ: Sr, 91, read 2 bytes, ACK then NACK",I_run(1),"S 90 A 05 A Sr 91 A A1 A B2 N P ",{{8,0xA1},{8,0xB2}},{1});
  dev.stretch=37; dev.regs[5]=0x3C; dev.regs[6]=0xC3;
  ok&=txn("RUN READ with the device stretching SCL",I_run(1),"S 90 A 05 A Sr 91 A 3C A C3 N P ",{{8,0x3C},{8,0xC3}},{1});
  dev.stretch=0;
  ok&=txn("no device at 0x50: address NACK, STOP",cat({I_start(0xA0,8,0,1),I_run(2)}),"S A0 N P ",{},{2});
  printf(ok?"ALL PASS\n":"FAILED\n"); return !ok; }
