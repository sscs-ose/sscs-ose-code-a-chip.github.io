// =============================================================================
// Project: ProEm - Open Source Protocol Emulator
// File: sim/t_crc.cpp
// Type: Test, pin level (CXXRTL)
// Device under test: protocol_emulator (src/top/protocol_emulator.sv)
// Author: Paul Vincent Bezzina
// Language: C++14
// Description:
// =============================================================================

#include "bench.h"
int scen=0;
double tclk=20.0, tbit=1000.0/1.5, now=0, se0_end=-1, first_drive=-1; std::vector<std::pair<double,int>> ev; size_t ei=0; int dp=0, dm=1, usb_ch=0;
struct Rx { int st=0, cnt=0, level=0, ones=0, se0=0; std::vector<int> bits; std::string shape; } mon;
int P=50; long T0=-1; std::vector<int> node_bits; std::vector<int> samples; int bus=1;
long edge_t=-1; int prev_bus=1; int R=16; int flip_bit=-1;
int out_released(int ch){ return ch ? !t.p_data__oe__b.get<bool>() : !t.p_data__oe__a.get<bool>(); }
void usb_monitor(){ int op=usb_ch?t.p_data__oe__b.get<bool>():t.p_data__oe__a.get<bool>(); int pp=usb_ch?t.p_pair__oe__b.get<bool>():t.p_pair__oe__a.get<bool>();
  int d=op?(usb_ch?t.p_data__out__b.get<bool>():t.p_data__out__a.get<bool>()):0; int m=pp?(usb_ch?t.p_pair__out__b.get<bool>():t.p_pair__out__a.get<bool>()):1;
  if(op && first_drive<0) first_drive=now;
  if(mon.st==0){ if(op && d){ mon.st=1; mon.cnt=16; mon.level=0; mon.ones=0; mon.bits.clear(); mon.shape.clear(); } }
  else if(mon.st==1 && --mon.cnt==0){ mon.cnt=33;
    if(!d && !m){ mon.se0++; mon.shape+="0"; }
    else if(mon.se0){ mon.shape+=(!d && m)?"J":"?"; mon.st=2; mon.cnt=40; }
    else { int bit=(d==mon.level); mon.level=d; if(mon.ones==6){ if(bit) mon.shape+="!"; mon.ones=0; } else { mon.bits.push_back(bit); mon.ones=bit?mon.ones+1:0; } } }
  else if(mon.st==2 && --mon.cnt==0){ mon.shape+=(!op && !pp)?"R":"D"; mon.st=3; } }
void env_all(){ now+=tclk;
  if(scen==0){ while(ei<ev.size() && ev[ei].first<=now){ int s=ev[ei].second; dp=(s==1||s==3); dm=(s==0||s==3); ei++; } pin_in=dp|(dm<<1); usb_monitor(); }
  else if(scen==1){ pin_in=2; usb_monitor(); }
  else if(scen==2){ int nb=1; if(T0>=0 && cycles>=T0){ long k=(cycles-T0)/P; if(k<(long)node_bits.size()) nb=node_bits[k];
      if((cycles-T0)%P==P/2 && k<(long)node_bits.size()) samples.push_back(nb && out_released(0)); }
    bus=nb && out_released(0); pin_in=bus; }
  else if(scen==3){ bus=out_released(0) && out_released(1); pin_in=bus|(bus<<3);
    if(edge_t<0 && prev_bus && !bus) edge_t=cycles; prev_bus=bus;
    if(edge_t>=0 && (cycles-edge_t)%P==P/2) samples.push_back(bus); }
  else if(scen==4){ int b=t.p_data__oe__b.get<bool>()?t.p_data__out__b.get<bool>():1;
    if(edge_t<0 && prev_bus && !b) edge_t=cycles; prev_bus=b;
    if(edge_t>=0 && flip_bit>=0){ long a=edge_t+(long)(1+flip_bit)*R; if(cycles>=a && cycles<a+R) b=!b; }
    pin_in=b<<3; } }
void encode(const std::vector<unsigned>&bytes){ ev.clear(); ei=0; double tt=now+2000; int level=0, ones=0; ev.push_back({tt,0});
  auto put=[&](int b){ if(!b) level=!level; ev.push_back({tt,level?1:0}); tt+=tbit; };
  for(unsigned by:bytes) for(int k=0;k<8;k++){ int b=(by>>k)&1; put(b); if(b){ if(++ones==6){ put(0); ones=0; } } else ones=0; }
  ev.push_back({tt,2}); tt+=2*tbit; se0_end=tt; ev.push_back({tt,0}); tt+=tbit; ev.push_back({tt+1,0});
  while(ei<ev.size()) clk(); idle(1500); }
std::vector<unsigned> bits_bytes(const std::vector<int>&b,int msb){ std::vector<unsigned> o; for(size_t i=0;i+8<=b.size();i+=8){ unsigned v=0; for(int k=0;k<8;k++) v|=b[i+k]<<(msb?7-k:k); o.push_back(v); } return o; }
std::vector<int> stuff5(const std::vector<int>&raw){ std::vector<int> o; int run=0,last=-1; for(int b:raw){ o.push_back(b); if(b==last) run++; else { run=1; last=b; } if(run==5){ int s=!b; o.push_back(s); last=s; run=1; } } return o; }
std::vector<int> unstuff5(const std::vector<int>&s,size_t count,size_t&used){ std::vector<int> o; int run=0,last=-1; size_t i=0; bool skip=false;
  while(o.size()<count && i<s.size()){ int b=s[i++]; if(skip){ skip=false; run=1; last=b; continue; } o.push_back(b); if(b==last) run++; else { run=1; last=b; } if(run==5) skip=true; }
  if(skip && i<s.size()) i++; used=i; return o; }
std::vector<int> can_raw(unsigned id,unsigned data){ std::vector<int> r; r.push_back(0); for(int i=10;i>=0;i--) r.push_back((id>>i)&1); r.push_back(0); r.push_back(0); r.push_back(0);
  for(int i=3;i>=0;i--) r.push_back((1>>i)&1); for(int i=7;i>=0;i--) r.push_back((data>>i)&1); return r; }
std::string last_entry(int c){ if(got[c].empty()) return "none"; char b[16]; snprintf(b,sizeof b,"%u:%02X",got[c].back().first,got[c].back().second); return b; }
bool result_is(int c,unsigned v){ return !got[c].empty() && got[c].back().first==14 && got[c].back().second==v; }
bool usb_rx(const char*name,const std::vector<unsigned>&data,bool corrupt){ std::vector<int> bits=byte_bits(data,0); unsigned c=crc_wire(bits,16,0x8005,1); std::vector<int> tx=crc_tx(c,16,1);
  std::vector<unsigned> crcb=bits_bytes(tx,0); std::vector<unsigned> pkt={0x80,0xC3}; for(unsigned d:data) pkt.push_back(d); if(corrupt) pkt[2]^=0x10; pkt.push_back(crcb[0]); pkt.push_back(crcb[1]);
  clear_results(); mon=Rx(); first_drive=-1; encode(pkt); wait_return();
  V exp; exp.push_back({8,0xC3}); for(size_t i=2;i<pkt.size();i++) exp.push_back({8,pkt[i]}); exp.push_back({14,corrupt?2u:3u});
  bool ok=got[0]==exp && status[0]==std::vector<unsigned>({1});
  double gap=(first_drive-se0_end)/tbit;
  if(corrupt) ok=ok && first_drive<0;
  else ok=ok && bits_bytes(mon.bits,0)==std::vector<unsigned>({0x80,0xD2}) && mon.shape=="00JR" && gap>=2.5 && gap<=7.5;
  char g[48]; snprintf(g,sizeof g," gap %.1f bits",corrupt?0.0:gap);
  return report(name,ok,show(got[0])+" |"+showst(status[0])+" reply"+showst(bits_bytes(mon.bits,0))+" "+mon.shape+(corrupt?"":g)); }
bool can_rx(const char*name,unsigned id,unsigned data,bool corrupt){ std::vector<int> raw=can_raw(id,data); unsigned c=crc_wire(raw,15,0x4599,0); std::vector<int> tx=crc_tx(c,15,0);
  if(corrupt) tx[3]^=1; for(int b:tx) raw.push_back(b); node_bits=stuff5(raw); size_t n=node_bits.size(); node_bits.push_back(1); node_bits.push_back(1); node_bits.push_back(1); for(int k=0;k<7;k++) node_bits.push_back(1);
  clear_results(); samples.clear(); T0=cycles+200; idle((long)node_bits.size()*P+600); T0=-1; wait_return();
  bool ack=samples.size()>n+2 && samples[n]==1 && samples[n+1]==(corrupt?1:0) && samples[n+2]==1;
  bool ok=result_is(0,corrupt?2:3) && status[0]==std::vector<unsigned>({1}) && ack;
  char d[64]; snprintf(d,sizeof d," stuffed %zu bits, delim/ack/delim %d%d%d",n,samples.size()>n?samples[n]:-1,samples.size()>n+1?samples[n+1]:-1,samples.size()>n+2?samples[n+2]:-1);
  return report(name,ok,std::string(" result ")+last_entry(0)+" |"+showst(status[0])+d); }
bool can_loop(const char*name,unsigned id,unsigned data){ clear_results(); samples.clear(); edge_t=-1; prev_bus=1;
  CH=1; program(cat({I_data(8,id>>3),I_data(3,id&7),I_data(7,0x01),I_data(8,data),I_run(2)})); idle(120*P); wait_return();
  size_t used=0; std::vector<int> fr=unstuff5(samples,42,used); bool crc_ok=false, ack=false;
  if(fr.size()==42){ std::vector<int> body(fr.begin(),fr.begin()+27); std::vector<int> want=crc_tx(crc_wire(body,15,0x4599,0),15,0); crc_ok=std::vector<int>(fr.begin()+27,fr.end())==want;
    ack=samples.size()>used+2 && samples[used]==1 && samples[used+1]==0 && samples[used+2]==1; }
  std::vector<int> body=can_raw(id,data); bool body_ok=fr.size()==42 && std::vector<int>(fr.begin(),fr.begin()+27)==body;
  bool ok=body_ok && crc_ok && ack && result_is(0,3) && status[0]==std::vector<unsigned>({1}) && status[1]==std::vector<unsigned>({1});
  char d[96]; snprintf(d,sizeof d," body %d crc %d ack %d, A result %s, status A%s B%s",body_ok,crc_ok,ack,last_entry(0).c_str(),showst(status[0]).c_str(),showst(status[1]).c_str());
  return report(name,ok,d); }
int main(int argc,char**argv){ int runs=argc>1?atoi(argv[1]):60; env=env_all; pin_in=2; power_on(); bool ok=true;
  scen=0; usb_ch=0; CH=0;
  program(cat({I_link(4),I_line(2,0,6,1),I_clock(RECOVER,33,0,0,0,2),I_out(1,0,1,1),I_start(0x80,8,0,0,0),I_hdr(1,0,8,1,0,0,0,1),I_main(0,0,1,0,0),I_end(2,0,0x0003,1,0,1,1),
    I_crc_a(16,7,1,0x8005),I_crc_b(1,1,0,1,0x800D),I_reply(REPLY_GOOD,16,3,0xD280),I_run(0)})); RET_R=4;
  ok&=usb_rx("USB DATA0 receive, CRC16 good: ACK handshake sent",{0x01,0x02,0xFF,0xFF,0x7E},false);
  ok&=usb_rx("USB DATA0 receive, data corrupted: CRC bad, no reply",{0x01,0x02,0xFF,0xFF,0x7E},true);
  ok&=usb_rx("USB receive again after a bad packet",{0xA5,0x5A},false);
  program(cat({I_crc_a(5,7,1,0x05),I_crc_b(1,1,0,1,0x0C),I_reply(REPLY_OFF,1,0,0)}));
  { std::vector<int> tb; unsigned addr=0x3A, endp=0x9; for(int i=0;i<7;i++) tb.push_back((addr>>i)&1); for(int i=0;i<4;i++) tb.push_back((endp>>i)&1);
    std::vector<int> tx=crc_tx(crc_wire(tb,5,0x05,1),5,1); for(int b:tx) tb.push_back(b); std::vector<unsigned> by=bits_bytes(tb,0);
    for(int bad=0;bad<2;bad++){ std::vector<unsigned> pkt={0x80,0xE1,by[0]^(bad?0x04u:0u),by[1]}; clear_results(); encode(pkt); wait_return();
      bool r=got[0]==V({{8,0xE1},{8,pkt[2]},{8,pkt[3]},{14,bad?2u:3u}}) && status[0]==std::vector<unsigned>({1});
      ok&=report(bad?"USB OUT token, address corrupted: CRC5 bad":"USB OUT token, CRC5 good",r,show(got[0])+" |"+showst(status[0])); } }
  scen=1; usb_ch=1; mon=Rx(); clear_results(); CH=1;
  program(cat({I_line(2,0,6,1),I_clock(RECOVER,33),I_out(1,0,1,1),I_start(0x80,8,0,1),I_hdr(1,0x4B,8,0,1),I_main(32,1),I_crc_a(16,7,1,0x8005),I_crc_b(1,0,1,1,0),
    I_data(8,0xFF),I_data(8,0xFF),I_data(8,0x7E),I_data(8,0x00),I_run(2)}));
  idle(4000); wait_return();
  { std::vector<unsigned> txb=bits_bytes(mon.bits,0); std::vector<unsigned> d={0xFF,0xFF,0x7E,0x00}; std::vector<unsigned> c=bits_bytes(crc_tx(crc_wire(byte_bits(d,0),16,0x8005,1),16,1),0);
    std::vector<unsigned> want={0x80,0x4B,0xFF,0xFF,0x7E,0x00,c[0],c[1]};
    ok&=report("USB DATA1 transmit with CRC16 appended",txb==want && mon.shape=="00JR" && status[1]==std::vector<unsigned>({1}),std::string(" ")+showst(txb)+" "+mon.shape+" |"+showst(status[1])); }
  program(cat({I_halt(),I_clear()})); CH=0; program(cat({I_halt(),I_clear()})); RET_R=4;
  scen=2; CH=0;
  program(cat({I_order(1),I_line(0,0,5,0,0,1),I_clock(ASYNC,P),I_out(2),I_start(0,1,0,0,0),I_main(41,0),I_crc_a(15,0,0,0x4599),I_crc_b(1,1,0,0,0),I_reply(REPLY_GOOD,2,0,0x2),I_run(0)}));
  ok&=can_rx("CAN receive with stuffing, CRC-15 good: ACK in the ACK slot",0x000,0xFF,false);
  ok&=can_rx("CAN receive, CRC corrupted: no ACK",0x000,0xFF,true);
  ok&=can_rx("CAN receive, ID 0x7FF and data 0x00",0x7FF,0x00,false);
  scen=3; CH=0;
  program(cat({I_line(0,3,5,0,0,1),I_start(0,1,0,0,3),I_main(41,0,0,0,3)}));
  CH=1; program(cat({I_order(1),I_line(0,3,5,0,0,1),I_clock(ASYNC,P),I_out(2),I_start(0,1,0,1),I_main(26,1),I_crc_a(15,0,0,0x4599),I_crc_b(1,0,1,0,0)}));
  ok&=can_loop("CAN chip-to-chip: B sends with CRC appended, A checks and ACKs",0x123,0x5A);
  ok&=can_loop("CAN chip-to-chip: heavy stuffing (ID 0x000, data 0x00)",0x000,0x00);
  program(cat({I_halt(),I_clear()})); CH=0; program(cat({I_halt(),I_clear()}));
  scen=4; srand(7); int bad=0;
  CH=0; program(cat({I_line(0,3),I_clock(ASYNC,R),I_start(0,1,0,0,3),I_run(0)}));
  CH=1; program(cat({I_line(0,3),I_clock(ASYNC,R),I_out(3,1),I_start(0,1,0,1)}));
  for(int r=0;r<runs;r++){ int W=1+rand()%16, L=1+rand()%40, init=rand()&1, inv=rand()&1, msb=rand()&1; unsigned poly=(rand()&0xFFFF)&((1u<<W)-1)|1;
    std::vector<int> bits; for(int i=0;i<L;i++) bits.push_back(rand()&1);
    std::vector<int> tx=crc_tx(crc_wire(bits,W,poly,init),W,inv); std::vector<int> all=bits; for(int b:tx) all.push_back(b);
    unsigned residue=crc_wire(all,W,poly,init)>>(16-W); bool corrupt=(r%3==2); flip_bit=corrupt?rand()%L:-1;
    int chunks=(L+7)/8; chunks+=rand()%(9-chunks); if(chunks>L) chunks=L; std::vector<int> sizes(chunks,1); int left=L-chunks;
    while(left>0){ int k=rand()%chunks; if(sizes[k]<8){ sizes[k]++; left--; } }
    B q; size_t pos=0; for(int s:sizes){ unsigned v=0; for(int i=0;i<s;i++) v|=bits[pos+i]<<(msb?s-1-i:i); pos+=s; B e=I_data(s,v); q.insert(q.end(),e.begin(),e.end()); }
    CH=0; program(cat({I_main(L+W,0,0,0,3),I_crc_a(W,7,init,poly),I_crc_b(1,1,0,inv,residue)}));
    clear_results(); edge_t=-1; prev_bus=1;
    CH=1; program(cat({I_order(msb),I_main(L,1),I_crc_a(W,7,init,poly),I_crc_b(1,0,1,inv,0),q,I_run(2)}));
    idle((long)(L+W+4)*R+200); wait_return();
    bool good=result_is(0,corrupt?2:3) && status[0]==std::vector<unsigned>({1}) && status[1]==std::vector<unsigned>({1});
    if(!good){ bad++; if(bad<6) printf("  FAIL run %d W=%d L=%d poly=%04X init=%d inv=%d msb=%d corrupt=%d(bit %d): result %s A%s B%s\n",r,W,L,poly,init,inv,msb,corrupt,flip_bit,last_entry(0).c_str(),showst(status[0]).c_str(),showst(status[1]).c_str()); } }
  flip_bit=-1;
  ok&=report("random CRC widths, polynomials, init, inversion, bit order; a third corrupted on the wire",bad==0,std::string(" ")+std::to_string(runs-bad)+"/"+std::to_string(runs));
  printf(ok?"ALL PASS\n":"FAILED\n"); return !ok; }
