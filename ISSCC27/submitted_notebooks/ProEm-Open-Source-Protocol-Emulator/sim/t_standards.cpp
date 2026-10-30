// =============================================================================
// Project: ProEm - Open Source Protocol Emulator
// File: sim/t_standards.cpp
// Type: Test, pin level (CXXRTL)
// Device under test: protocol_emulator (src/top/protocol_emulator.sv)
// Author: Paul Vincent Bezzina
// Language: C++14
// Description:
// =============================================================================

#include "bench.h"
#include <cstring>
#include <algorithm>

struct Wave { std::deque<std::pair<int,long>> seg; int level=1, idle=1; long left=0;
  void add(int lv,long n){ if(n>0) seg.push_back({lv,n}); }
  int step(){ if(left==0){ if(seg.empty()){ level=idle; return level; } level=seg.front().first; left=seg.front().second; seg.pop_front(); } left--; return level; }
  bool busy() const { return left>0||!seg.empty(); } };
Wave m0, m1;
std::vector<uint8_t> tr, tr2;
std::function<void()> scen=[](){};
void env_std(){ scen(); }
int oA(){ return t.p_data__oe__a.get<bool>()? t.p_data__out__a.get<bool>() : 1; }
int oB(){ return t.p_data__oe__b.get<bool>()? t.p_data__out__b.get<bool>() : 1; }
int cA(){ return t.p_clock__oe__a.get<bool>()? t.p_clock__out__a.get<bool>() : 1; }
int cB(){ return t.p_clock__oe__b.get<bool>()? t.p_clock__out__b.get<bool>() : 1; }
typedef std::vector<std::pair<unsigned,unsigned>> E;
typedef std::vector<unsigned> U;

int par(unsigned v,int n){ int p=0; for(int i=0;i<n;i++) p^=(v>>i)&1; return p; }
void uwave(Wave&w,unsigned v,long d,int nb,int parity,int stops,int inv=0){
  w.add(0^inv,d); for(int i=0;i<nb;i++) w.add(((v>>i)&1)^inv,d); if(parity) w.add(par(v,nb)^inv,d); w.add(1^inv,d*stops); }
struct UF { unsigned v; int ok; };
std::vector<UF> udecode(const std::vector<uint8_t>&x,long d,int nb,int parity,int stops,int inv=0,size_t from=1){
  std::vector<UF> o; auto at=[&](size_t k){ return k<x.size()? (x[k]^inv) : 1; }; size_t i=std::max<size_t>(from,1);
  while(i<x.size()){ if(at(i-1)==1 && at(i)==0){ size_t s=i; if(at(s+d/2)!=0){ i++; continue; }
      unsigned v=0; for(int b=0;b<nb;b++) v|=(unsigned)at(s+d*(b+1)+d/2)<<b; int ok=1;
      if(parity) ok&=at(s+d*(nb+1)+d/2)==par(v,nb);
      for(int k=0;k<stops;k++) ok&=at(s+d*(nb+1+(parity?1:0)+k)+d/2)==1;
      o.push_back({v,ok}); i=s+d*(nb+(parity?1:0)+stops)+d/2; } else i++; }
  return o; }
U values(const std::vector<UF>&f){ U o; for(auto&x:f) o.push_back(x.v); return o; }
bool all_ok(const std::vector<UF>&f){ for(auto&x:f) if(!x.ok) return false; return true; }

B urx(long d,int mbits,int pin,int inv=0){ return cat({I_line(0,pin,0,0,inv),I_clock(ASYNC,(unsigned)d),I_start(0,1,0,0,pin),I_main(mbits,0,0,0,pin),I_run(0)}); }
B utx(long d,int mbits,int pin,int drive,int inv=0,int cshigh=0){ return cat({I_line(0,pin,0,0,inv),I_clock(ASYNC,(unsigned)d),I_out(drive,1,0,0,0,cshigh),I_start(0,1,0,1),I_main(mbits,1,0,0,pin)}); }
E uentries(const U&b,int nb,int parity,int stops){ E e; for(unsigned v:b){ e.push_back({(unsigned)nb,v}); unsigned tail=0; int pos=0;
    if(parity) tail|=(unsigned)par(v,nb)<<pos++; for(int s=0;s<stops;s++) tail|=1u<<pos++; e.push_back({(unsigned)pos,tail}); } return e; }
V uexpect(const U&b,int nb,int parity,int stops){ V o; for(unsigned v:b){ std::vector<int> bits; for(int i=0;i<nb;i++) bits.push_back((v>>i)&1);
    if(parity) bits.push_back(par(v,nb)); for(int s=0;s<stops;s++) bits.push_back(1);
    for(size_t i=0;i<bits.size();i+=8){ unsigned n=std::min<size_t>(8,bits.size()-i), x=0; for(unsigned k=0;k<n;k++) x|=(unsigned)bits[i+k]<<k; o.push_back({n,x}); } } return o; }
bool host_full(int ch){ return ch? t.p_host__full__b.get<bool>() : t.p_host__full__a.get<bool>(); }
void feed(int ch,const E&e,size_t from=0){ int sv=CH; CH=ch;
  for(size_t i=from;i<e.size();i++){ while(!serial.empty()) clk(); idle(8); while(host_full(ch)) clk(); send(I_data(e[i].first,e[i].second)); }
  while(!serial.empty()) clk(); CH=sv; }
void tx_run(int ch,const E&e,int mode){ size_t n=std::min<size_t>(8,e.size()); int sv=CH; CH=ch; B b;
  for(size_t i=0;i<n;i++){ B x=I_data(e[i].first,e[i].second); b.insert(b.end(),x.begin(),x.end()); }
  B r=I_run(mode); b.insert(b.end(),r.begin(),r.end()); send(b); CH=sv; feed(ch,e,n); }
void reset_both(){ int sv=CH; CH=0; scen=[](){ pin_in=0xFF; }; program(I_clear()); CH=1; program(I_clear()); CH=sv; clear_results(); tr.clear(); tr2.clear(); m0=Wave(); m1=Wave();  }
std::string hexs(const U&v){ std::string s; char b[8]; for(unsigned x:v){ snprintf(b,sizeof b," %02X",x); s+=b; } return s; }
std::string ascii(const U&v){ std::string s=" \""; for(unsigned x:v){ if(x=='\r') s+="\\r"; else if(x=='\n') s+="\\n"; else s+=(char)x; } return s+"\""; }
U str_bytes(const char*s){ U o; for(;*s;s++) o.push_back((unsigned char)*s); return o; }
void wait_status(int ch,size_t n,long limit=20000000){ for(long i=0;i<limit && status[ch].size()<n;i++) clk(); idle(200); wait_return(); }
void run_model(Wave&w,long tail){ while(w.busy()) clk(); idle(tail); wait_return(); }

bool uart_std(const char*name,long D,int nb,int parity,int stops,const U&rx,const U&txm,int drive,int inv,bool text){
  bool ok=true; char n1[96], n2[96];
  reset_both(); CH=0; program(urx(D,nb+(parity?1:0)+stops,0,inv));
  for(unsigned b:rx) uwave(m0,b,D,nb,parity,stops,inv);
  m0.idle=1^inv;
  scen=[&]{ pin_in=0xF6|m0.step(); };
  run_model(m0,D*4);
  snprintf(n1,sizeof n1,"%s receive",name);
  ok&=report(n1,got[0]==uexpect(rx,nb,parity,stops) && status[0]==U(rx.size(),1),text? ascii(rx).substr(0,40)+"... "+std::to_string(status[0].size())+" frames" : show(got[0])+" |"+showst(status[0]));
  reset_both(); CH=1; program(utx(D,nb+(parity?1:0)+stops,3,drive,inv));
  scen=[&]{ int b=oB(); if(!t.p_data__oe__b.get<bool>()) b=1^inv; tr.push_back(b); pin_in=0xF7|(b<<3); };
  tx_run(1,uentries(txm,nb,parity,stops),0);
  wait_status(1,txm.size()); idle(D*16);
  auto f=udecode(tr,D,nb,parity,stops,inv);
  snprintf(n2,sizeof n2,"%s transmit",name);
  ok&=report(n2,values(f)==txm && all_ok(f) && status[1]==U(txm.size(),1),text? ascii(values(f)).substr(0,40)+"..." : std::string(" line")+hexs(values(f)));
  return ok; }

unsigned crc16_modbus(const U&b){ unsigned c=0xFFFF; for(unsigned x:b){ c^=x; for(int i=0;i<8;i++) c=(c&1)?((c>>1)^0xA001):(c>>1); } return c; }
unsigned nmea_sum(const char*s){ unsigned c=0; for(const char*p=s+1;*p && *p!='*';p++) c^=(unsigned char)*p; return c; }

bool t_rs485(){ const long D=434; bool ok=true;
  U rx={0x01,0x10,0xA5,0x5A,0xFF,0x00}, txm={0x02,0x47,0x6F,0x03};
  reset_both(); CH=0; program(urx(D,9,0));
  for(unsigned b:rx) uwave(m0,b,D,8,0,1);
  scen=[&]{ pin_in=0xF6|m0.step(); }; run_model(m0,D*4);
  ok&=report("RS-232/422/485 receive, 115200 8N1",got[0]==uexpect(rx,8,0,1)&&status[0]==U(rx.size(),1),show(got[0]));
  reset_both(); CH=1; program(utx(D,9,3,1,0,1));
  std::vector<uint8_t> de, oe;
  scen=[&]{ int b=oB(); tr.push_back(b); de.push_back(t.p_select__out__b.get<bool>()); oe.push_back(t.p_data__oe__b.get<bool>()); pin_in=0xF7|(b<<3); };
  tx_run(1,uentries(txm,8,0,1),0); wait_status(1,txm.size()); idle(D*16);
  auto f=udecode(tr,D,8,0,1); bool cover=true; long driven=0, enabled=0;
  for(size_t k=0;k<oe.size();k++){ if(oe[k]){ driven++; if(!de[k]) cover=false; } if(de[k]) enabled++; }
  bool released=!oe.back() && !de.back();
  char d[96]; snprintf(d,sizeof d," line%s, DE covers %ld driven clocks (%ld enabled)",hexs(values(f)).c_str(),driven,enabled);
  ok&=report("RS-485 transmit, DE on the select output",values(f)==txm&&all_ok(f)&&cover&&released&&status[1]==U(txm.size(),1),d);
  return ok; }

bool t_midi(){ return uart_std("MIDI 31250 8N1 (Note On / Note Off)",1600,8,0,1,{0x90,0x3C,0x64},{0x80,0x3C,0x00},3,0,false); }

bool t_nmea0183(){ const char*body="$GPGLL,4916.45,N,12311.12,W,225444,A*"; char s[96]; snprintf(s,sizeof s,"%s%02X\r\n",body,nmea_sum(body));
  const char*body2="$PPROE,1,TEST*"; char s2[64]; snprintf(s2,sizeof s2,"%s%02X\r\n",body2,nmea_sum(body2));
  return uart_std("NMEA 0183 4800 8N1",10417,8,0,1,str_bytes(s),str_bytes(s2),3,0,true); }

bool t_profibus(){ U req={0x10,0x02,0x01,0x49}; req.push_back((0x02+0x01+0x49)&0xFF); req.push_back(0x16);
  U rsp={0x10,0x01,0x02,0x00}; rsp.push_back((0x01+0x02+0x00)&0xFF); rsp.push_back(0x16);
  return uart_std("PROFIBUS DP 500 kbit/s 8E1 (SD1)",100,8,1,1,req,rsp,1,0,false); }

bool t_modbus(){ U req={0x01,0x03,0x00,0x00,0x00,0x02}; unsigned c=crc16_modbus(req); req.push_back(c&0xFF); req.push_back(c>>8);
  U rsp={0x01,0x03,0x04,0x00,0x0A,0x00,0x0B}; c=crc16_modbus(rsp); rsp.push_back(c&0xFF); rsp.push_back(c>>8);
  bool ok=uart_std("Modbus RTU 19200 8E1",2604,8,1,1,req,rsp,1,0,false);
  ok&=report("Modbus RTU: request CRC is C4 0B",req[6]==0xC4&&req[7]==0x0B,hexs(req));
  const long D=2604;
  for(int bad=0;bad<2;bad++){ reset_both(); CH=0;
    program(cat({I_line(0,0),I_clock(ASYNC,D),I_start(0,1,0,0,0),I_hdr(1,0,8,1,0,0,0,1),I_hdr(2,0,1,1,0,0,0,1),I_main(1,0,0,0,0),
      I_crc_a(16,1,1,0x8005),I_crc_b(1,1,0,0,0,1,1),I_run(0)}));
    U m=req; if(bad) m[3]^=0x01; for(unsigned b:m) uwave(m0,b,D,8,1,1);
    scen=[&]{ pin_in=0xFE|m0.step(); }; run_model(m0,D*4);
    unsigned last=0; U data; for(auto&x:got[0]){ if(x.first==14) last=x.second; if(x.first==8) data.push_back(x.second); }
    char d[80]; snprintf(d,sizeof d," bytes%s, CRC result after the last byte %02X",hexs(data).c_str(),last);
    ok&=report(bad?"Modbus RTU receive, one bit flipped: on-chip CRC reports bad":"Modbus RTU receive with the CRC checked on chip (byte fields, spans frames)",data==m&&last==(bad?2u:3u)&&status[0]==U(m.size(),1),d); }
  return ok; }


long low_run(const std::vector<uint8_t>&x,size_t from,int level,size_t*end){ size_t i=from; while(i<x.size() && x[i]!=level) i++; size_t s=i; while(i<x.size() && x[i]==level) i++; if(end) *end=i; return (long)(i-s); }
size_t first_fall(const std::vector<uint8_t>&x,size_t from=1){ for(size_t i=std::max<size_t>(from,1);i<x.size();i++) if(x[i-1]==1 && x[i]==0) return i; return x.size(); }

bool t_dmx(){ const long D=200; bool ok=true; U slots={0x00,0xFF,0x80,0x01,0x7E};
  reset_both(); CH=1;
  program(cat({I_line(0,3),I_clock(ASYNC,D),I_out(3,1),I_start(0,1,0,1),I_hdr(1,0x00,8,0,1),I_hdr(2,0x00,8,0,1),I_hdr(3,0xC0,8,0,1),I_main(11*slots.size(),1,0,0,3)}));
  E e; e.push_back({1,0}); for(size_t i=0;i<slots.size();i++){ e.push_back({8,slots[i]}); if(i+1<slots.size()) e.push_back({3,3}); else e.push_back({2,3}); }
  scen=[&]{ int b=oB(); tr.push_back(b); pin_in=0xF7|(b<<3); };
  tx_run(1,e,2); wait_status(1,1); idle(D*16);
  size_t s=first_fall(tr), e1, e2; long brk=low_run(tr,s,0,&e1), mab=low_run(tr,e1,1,&e2);
  auto f=udecode(tr,D,8,0,2,0,e2);
  char d[96]; snprintf(d,sizeof d," break %.0f us, MAB %.0f us, slots%s",brk/50.0,mab/50.0,hexs(values(f)).c_str());
  ok&=report("DMX512 transmit: break, mark after break, start code + 4 slots",brk>=88*50&&mab>=8*50&&values(f)==slots&&all_ok(f)&&status[1]==U({1}),d);
  reset_both(); CH=0;
  program(cat({I_line(0,0),I_clock(ASYNC,D),I_start(0,1,0,0,0),I_hdr(1,0,8,1,0,0,0,1),I_hdr(2,1,1,0,0),I_main(1,0,0,0,0),I_end(1,0,0x0001),I_run(0)}));
  U pk1={0x00,0x11,0x22,0x33}, pk2={0x00,0xA0,0x0B};
  for(int p=0;p<2;p++){ m0.add(1,D*5); m0.add(0,p?7000:5000); m0.add(1,p?400:600); for(unsigned b:(p?pk2:pk1)){ uwave(m0,b,D,8,0,2); m0.add(1,p?0:D); } }
  scen=[&]{ pin_in=0xFE|m0.step(); }; run_model(m0,D*20);
  V exp; U st; for(int p=0;p<2;p++){ st.push_back(0x02); for(unsigned b:(p?pk2:pk1)){ exp.push_back({8,b}); exp.push_back({1,1}); st.push_back(0x01); } }
  ok&=report("DMX512 receive: break seen as a framing abort, then slots, twice",got[0]==exp&&status[0]==st,show(got[0])+" |"+showst(status[0]));
  return ok; }

unsigned lin_pid(unsigned id){ id&=0x3F; unsigned p0=((id>>0)^(id>>1)^(id>>2)^(id>>4))&1, p1=(~((id>>1)^(id>>3)^(id>>4)^(id>>5)))&1; return id|(p0<<6)|(p1<<7); }
unsigned lin_sum(const U&b){ unsigned s=0; for(unsigned x:b){ s+=x; if(s>255) s-=255; } return (~s)&0xFF; }

bool t_lin(){ const long D=2604; bool ok=true; unsigned pid=lin_pid(0x10); U data={0x34,0x12}; U cs_in={pid,0x34,0x12}; unsigned chk=lin_sum(cs_in);
  reset_both(); CH=0;
  program(cat({I_line(0,0),I_clock(ASYNC,D),I_out(2,1),I_start(0,1,0,1),I_hdr(1,0,8,0,1),I_hdr(2,0,4,0,1),I_hdr(3,0x1,2,0,1),I_main(49,1)}));
  E e={{8,0x55},{2,1},{8,pid},{2,1},{8,data[0]},{2,1},{8,data[1]},{2,1},{8,chk},{1,1}};
  scen=[&]{ int bus=oA(); tr.push_back(bus); pin_in=0xFE|bus; };
  tx_run(0,e,2); wait_status(0,1); idle(D*16);
  size_t s=first_fall(tr), e1, e2; long brk=low_run(tr,s,0,&e1); long del=low_run(tr,e1,1,&e2);
  auto f=udecode(tr,D,8,0,1,0,e2); U v=values(f);
  bool good=v.size()==5&&v[0]==0x55&&v[1]==pid&&v[2]==0x34&&v[3]==0x12&&lin_sum({v[1],v[2],v[3]})==v[4];
  char d[96]; snprintf(d,sizeof d," break %.1f bits, delimiter %.1f, frame%s",brk/(double)D,del/(double)D,hexs(v).c_str());
  ok&=report("LIN master: break, sync, PID 0x10, 2 bytes, enhanced checksum",good&&brk>=13*D&&del>=D&&all_ok(f)&&status[0]==U({1}),d);
  reset_both(); CH=0;
  program(cat({I_line(0,0),I_clock(ASYNC,D),I_out(2,1),I_start(0x55,8,0,0,0),I_hdr(1,0x1,2,0,0),I_hdr(2,1,1,0,0),I_hdr(3,0,1,0,0,0,0,0,1),I_hdr(4,pid,8,0,0),I_hdr(5,1,1,0,0),I_main(31,1),
    I_data(2,1),I_data(8,data[0]),I_data(2,1),I_data(8,data[1]),I_data(2,1),I_data(8,chk),I_data(1,1),I_run(0)}));
  size_t mark=0; long hdr_end=0;
  auto header=[&](unsigned p,int dl,int gap){ m0.add(1,D*3); m0.add(0,D*13); m0.add(1,D*dl); uwave(m0,0x55,D,8,0,1); m0.add(1,D*gap); uwave(m0,p,D,8,0,1); };
  scen=[&]{ int bus=m0.step() && oA(); tr.push_back(bus); pin_in=0xFE|bus; };
  header(lin_pid(0x21),1,0); header(pid,2,3);
  while(m0.busy()) clk(); hdr_end=(long)tr.size(); idle(D*40); wait_return();
  mark=(size_t)hdr_end; auto r=udecode(tr,D,8,0,1,0,mark); U rv=values(r);
  long space=(long)first_fall(tr,mark)-hdr_end;
  char d2[96]; snprintf(d2,sizeof d2," response%s after %.1f bits | status%s",hexs(rv).c_str(),space/(double)D,showst(status[0]).c_str());
  ok&=report("LIN slave: ignores 0x21, answers 0x10 (2-bit delimiter, 3-bit gap)",rv==U({data[0],data[1],chk})&&all_ok(r)&&status[0]==U({0x02,0x01}),d2);
  return ok; }

unsigned sum8(const U&b){ unsigned s=0; for(unsigned x:b) s+=x; return s&0xFF; }

bool t_kline(){ const long D=4808, W=62500; bool ok=true;
  U req={0x81,0xEE,0xF0,0x81}; req.push_back(sum8(req)); U rsp={0x80,0xF0,0xEE,0x03,0xC1,0xEA,0x8F}; rsp.push_back(sum8(rsp));
  reset_both();
  CH=0; program(cat({I_line(0,0),I_clock(ASYNC,W),I_out(2,1),I_start(0,1,0,1),I_hdr(1,0,8,0,1),I_hdr(2,0,8,0,1),I_hdr(3,0,3,0,1),
    I_hdr(4,0xFF,8,0,1),I_hdr(5,0xFF,8,0,1),I_hdr(6,0x07,3,0,1),I_main(1,1),I_branch(0,KEEP,KEEP,1,0,0,0)}));
  CH=1; program(cat({I_line(0,0),I_clock(ASYNC,D),I_out(2,1),I_start(0,1,0,1),I_main(9,1)}));
  E e=uentries(req,8,0,1); CH=1; { B b; for(size_t i=0;i<8;i++){ B y=I_data(e[i].first,e[i].second); b.insert(b.end(),y.begin(),y.end()); } program(b); }
  long t_req_end=-1; int phase=0;
  scen=[&]{ int bus=oA() && oB() && m0.step(); tr.push_back(bus); pin_in=0xFE|bus; };
  CH=0; program(cat({I_data(1,1),I_run(2)}));
  for(long i=0;i<5000000 && status[0].empty();i++) clk();
  CH=1; send(I_run(0)); feed(1,e,8);
  for(long i=0;i<5000000 && status[1].size()<req.size();i++) clk();
  idle(D*12); t_req_end=(long)tr.size();
  CH=0; program(cat({I_clear(),I_line(0,0),I_clock(ASYNC,D),I_start(0,1,0,0,0),I_main(9,0),I_run(0)}));
  m0.add(1,25*50000-(long)(tr.size()-t_req_end)); for(unsigned b:rsp) uwave(m0,b,D,8,0,1);
  run_model(m0,D*12); (void)phase;
  size_t s=first_fall(tr), e1; long low=low_run(tr,s,0,&e1); size_t req0=first_fall(tr,e1);
  auto f=udecode(tr,D,8,0,1,0,e1); U v=values(f); U vreq(v.begin(),v.begin()+std::min<size_t>(5,v.size()));
  char d[120]; snprintf(d,sizeof d," low %.2f ms, request at %.2f ms:%s",low/50000.0,(req0-s)/50000.0,hexs(vreq).c_str());
  ok&=report("K-Line tester: fast init 25 ms low, request at 50 ms",std::abs(low-25*50000)<=50000&&std::abs((long)(req0-s)-50*50000)<=50000&&vreq==req&&!status[0].empty()&&status[0][0]==1,d);
  V exp=uexpect(rsp,8,0,1);
  ok&=report("K-Line: ECU positive response received after P2",got[0]==exp&&status[0].size()==1+rsp.size(),show(got[0]));
  return ok; }

bool t_sdi12(){ const long D=41667; bool ok=true; U cmd=str_bytes("0M!"), rsp=str_bytes("00011\r\n");
  reset_both(); int sensor_drive=0;
  CH=1; program(cat({I_line(0,0,0,0,1),I_clock(ASYNC,D),I_out(1,1),I_start(0,1,0,1),I_hdr(1,0,8,0,1),I_hdr(2,0,6,0,1),I_hdr(3,0xFF,8,0,1),I_hdr(4,0x3,2,0,1),
    I_main(30,1),I_branch(0,KEEP,KEEP,1,0,0,0)}));
  CH=0; program(cat({I_line(0,0,0,0,1),I_clock(ASYNC,D),I_start(0,1,0,0,0),I_main(9,0)}));
  m0.idle=0;
  scen=[&]{ int m=m0.step(); int bus=t.p_data__oe__b.get<bool>()? (int)t.p_data__out__b.get<bool>() : (sensor_drive? m : 0); tr.push_back(bus); pin_in=0xFE|bus; };
  E e; for(unsigned c:cmd){ e.push_back({8,(c<<1)&0xFF}); e.push_back({2,(unsigned)(par(c,7)|2)}); }
  tx_run(1,e,2); wait_status(1,1);
  CH=0; program(I_run(0));
  size_t cmd_end=tr.size(); m0.add(0,10*50000); for(unsigned c:rsp) uwave(m0,c,D,7,1,1,1); sensor_drive=1;
  run_model(m0,D*12);
  std::vector<uint8_t> lg(tr.size()); for(size_t k=0;k<tr.size();k++) lg[k]=tr[k]^1;
  size_t s=first_fall(lg), e1, e2; long brk=low_run(lg,s,0,&e1), mk=low_run(lg,e1,1,&e2);
  std::vector<uint8_t> head(tr.begin(),tr.begin()+cmd_end); auto f=udecode(head,D,7,1,1,1,e2);
  char d[120]; snprintf(d,sizeof d," break %.1f ms, marking %.2f ms, command%s",brk/50000.0,mk/50000.0,ascii(values(f)).c_str());
  ok&=report("SDI-12 recorder: break, marking, \"0M!\" at 1200 7E1, inverted",brk>=12*50000&&mk>=8.33*50000&&values(f)==cmd&&all_ok(f)&&status[1]==U({1}),d);
  V exp; for(unsigned c:rsp){ exp.push_back({8,c|(unsigned)(par(c,7)<<7)}); exp.push_back({1,1}); }
  U got7; for(auto&x:got[0]) if(x.first==8) got7.push_back(x.second&0x7F);
  ok&=report("SDI-12: sensor response \"00011\\r\\n\" received, parity in bit 7",got[0]==exp&&status[0]==U(rsp.size(),1),ascii(got7));
  return ok; }

unsigned crc8_bytes(const U&b,unsigned poly){ unsigned c=0; for(unsigned x:b){ c^=x; for(int i=0;i<8;i++) c=(c&0x80)?(((c<<1)^poly)&0xFF):((c<<1)&0xFF); } return c; }
unsigned crc7_bits(const std::vector<int>&bits){ unsigned c=0; for(int b:bits){ int fb=((c>>6)&1)^b; c=(c<<1)&0x7F; if(fb) c^=0x09; } return c; }

struct Dev { unsigned addr=0x40, regs[256]={0}, ptr=0, shift=0, cur=0; int st=0, rc=0, sda_low=0, first=1, ack=0, rw=0; std::string log; U bytes; } dev;
enum { D_IDLE, D_ADDR, D_WRITE, D_READ, D_WAIT };
int psda=1, pscl=1;
void logb(unsigned b){ char x[8]; snprintf(x,sizeof x,"%02X ",b); dev.log+=x; dev.bytes.push_back(b); }
void smbus_env(){
  int sda=!t.p_data__oe__a.get<bool>() && !dev.sda_low;
  int scl=!t.p_clock__oe__a.get<bool>();
  if(scl && pscl && psda && !sda){ dev.log+=(dev.st==D_IDLE)?"S ":"Sr "; dev.st=D_ADDR; dev.rc=0; dev.shift=0; dev.sda_low=0; }
  else if(scl && pscl && !psda && sda){ dev.log+="P "; dev.st=D_IDLE; dev.sda_low=0; }
  else if(scl && !pscl && dev.st!=D_IDLE){ dev.rc++;
    if(dev.rc<=8 && (dev.st==D_ADDR||dev.st==D_WRITE)) dev.shift=((dev.shift<<1)|sda)&0xFF;
    if(dev.rc==9 && dev.st==D_READ){ dev.log+=sda?"N ":"A "; dev.ack=!sda; } }
  else if(!scl && pscl && dev.st!=D_IDLE){
    if(dev.rc==8){
      if(dev.st==D_ADDR){ logb(dev.shift); dev.ack=(dev.shift>>1)==dev.addr; dev.rw=dev.shift&1; dev.log+=dev.ack?"A ":"N "; dev.sda_low=dev.ack; }
      else if(dev.st==D_WRITE){ logb(dev.shift); if(dev.first){ dev.ptr=dev.shift; dev.first=0; } else dev.regs[dev.ptr++&0xFF]=dev.shift; dev.log+="A "; dev.sda_low=1; dev.ack=1; }
      else if(dev.st==D_READ) dev.sda_low=0; }
    else if(dev.rc==9){ dev.rc=0; dev.sda_low=0; dev.shift=0;
      if(dev.st==D_ADDR){ if(!dev.ack) dev.st=D_WAIT; else if(dev.rw){ dev.st=D_READ; dev.cur=dev.regs[dev.ptr++&0xFF]; logb(dev.cur); dev.sda_low=!((dev.cur>>7)&1); } else { dev.st=D_WRITE; dev.first=1; } }
      else if(dev.st==D_READ){ if(dev.ack){ dev.cur=dev.regs[dev.ptr++&0xFF]; logb(dev.cur); dev.sda_low=!((dev.cur>>7)&1); } else dev.st=D_WAIT; } }
    else if(dev.st==D_READ && dev.rc>=1 && dev.rc<8) dev.sda_low=!((dev.cur>>(7-dev.rc))&1); }
  psda=sda; pscl=scl; pin_in=0xFA|sda|(scl<<2); }

bool t_smbus(){ bool ok=true; reset_both(); dev=Dev(); scen=smbus_env;
  CH=0; program(cat({I_order(1),I_line(0,0),I_clock(GENERATE,250,2,0,1),I_out(2,1,0,0,1),I_wdog(60000),I_start(0x80,8,0,1),I_hdr(1,0,1,0,0),I_hdr(2,0x21,8,0,1),I_hdr(3,0,1,0,0),
    I_hdr(4,0x81,8,0,1,1,1),I_hdr(5,0,1,0,0,1),I_main(24,2,0,1)}));
  unsigned pec=crc8_bytes({0x80,0x21,0x34,0x12},0x07);
  dev.log.clear(); dev.bytes.clear(); program(cat({I_data(8,0x34),I_data(8,0x12),I_data(8,pec),I_run(2)})); idle(120000); wait_return();
  bool wpec=dev.bytes.size()==5 && crc8_bytes(U(dev.bytes.begin(),dev.bytes.end()-1),0x07)==dev.bytes.back();
  ok&=report("SMBus Write Word with PEC, 100 kHz",wpec&&dev.regs[0x21]==0x34&&dev.regs[0x22]==0x12&&status[0]==U({1}),std::string(" bus: ")+dev.log);
  unsigned rpec=crc8_bytes({0x80,0x21,0x81,0xCD,0xAB},0x07); dev.regs[0x21]=0xCD; dev.regs[0x22]=0xAB; dev.regs[0x23]=rpec;
  clear_results(); dev.log.clear(); dev.bytes.clear(); program(I_run(1)); idle(150000); wait_return();
  U r; for(auto&x:got[0]) r.push_back(x.second);
  bool rok=r.size()==3 && crc8_bytes({0x80,0x21,0x81,r[0],r[1]},0x07)==r[2];
  ok&=report("SMBus Read Word with PEC: data and PEC checked by the host",rok&&r[0]==0xCD&&r[1]==0xAB&&status[0]==U({1}),std::string(" bus: ")+dev.log+"|"+show(got[0]));
  program(cat({I_crc_a(8,0,0,0x07),I_crc_b(1,1,0,0,0,1)}));
  for(int bad=0;bad<2;bad++){ dev.regs[0x23]=rpec^(bad?0x10:0); clear_results(); dev.log.clear(); program(I_run(1)); idle(150000); wait_return();
    ok&=report(bad?"SMBus Read Word, corrupted PEC: on-chip check reports bad":"SMBus Read Word: PEC checked on chip (byte fields only)",got[0]==V({{8,0xCD},{8,0xAB},{8,rpec^(bad?0x10u:0u)},{14,bad?2u:3u}})&&status[0]==U({1}),show(got[0])); }
  return ok; }

struct Phy { unsigned regs[32]={0}; unsigned addr=1; int ones=0, idx=-1, out=1, rd=0, pend=-1, pv=1, delay=0, fight=0; unsigned frame=0; int pmdc=0; } phy;
void mdio_env(){ int mdc=cA(); int mdio=oA() && phy.out; if(t.p_data__oe__a.get<bool>() && phy.rd==1 && phy.idx>=15) phy.fight++;
  if(phy.pend>0 && --phy.pend==0) phy.out=phy.pv;
  if(mdc && !phy.pmdc){
    if(phy.idx<0){ if(mdio) phy.ones++; else { if(phy.ones>=32){ phy.idx=0; phy.frame=0; } phy.ones=0; } }
    if(phy.idx>=0){ int i=phy.idx; if(i<14) phy.frame=(phy.frame<<1)|mdio;
      if(i==13){ unsigned op=(phy.frame>>10)&3, pa=(phy.frame>>5)&31; phy.rd=(pa!=phy.addr)?0:(op==2?1:(op==1?-1:0)); }
      if(i>=16 && phy.rd==-1) phy.frame=(phy.frame<<1)|mdio;
      if(i==31){ if(phy.rd==-1) phy.regs[(phy.frame>>16)&31]=phy.frame&0xFFFF; phy.idx=-1; phy.ones=0; phy.rd=0; phy.pv=1; phy.pend=phy.delay; if(!phy.delay) phy.out=1; }
      else { phy.idx++; int nx=phy.idx; if(phy.rd==1 && nx>=15){ phy.pv=(nx==15)?0:(int)((phy.regs[phy.frame&31]>>(31-nx))&1); phy.pend=phy.delay; if(!phy.delay) phy.out=phy.pv; } } } }
  phy.pmdc=mdc; pin_in=0xFA|mdio|(mdc<<2); }

bool t_mdio(){ bool ok=true; reset_both(); phy=Phy(); phy.regs[2]=0x0022; phy.regs[3]=0x1622; scen=mdio_env;
  auto h4=[](int op,unsigned pa){ return (unsigned)((0x1<<6)|(op<<4)|((pa>>1)&0xF)); };
  unsigned pa=1, reg=4;
  CH=0; program(cat({I_order(1),I_line(0,0),I_clock(GENERATE,10,2,0,0),I_out(1,1),I_wdog(5000),I_start(0xFF,8,0,1),I_hdr(1,0xFF,8,0,1),I_hdr(2,0xFF,8,0,1),I_hdr(3,0xFF,8,0,1),
    I_hdr(4,h4(1,pa),8,0,1),I_hdr(5,((pa&1)<<7)|(reg<<2)|0x2,8,0,1),I_main(16,1),I_data(8,0x01),I_data(8,0xE1),I_run(2)}));
  idle(3000); wait_return();
  char d[64]; snprintf(d,sizeof d," PHY 1 reg 4 = %04X",phy.regs[4]);
  ok&=report("MDIO clause 22 write: preamble, ST, OP, PHYAD, REGAD, TA, data",phy.regs[4]==0x01E1&&status[0]==U({1}),d);
  auto rd=[&](unsigned a,unsigned r){ clear_results(); CH=0; program(cat({I_hdr(4,h4(2,a),8,0,1),I_hdr(5,((a&1)<<5)|r,6,0,1),I_hdr(6,0x2,2,0,0),I_main(16,0),I_run(1)})); idle(3000); wait_return(); };
  rd(1,4); V g1=got[0]; U s1=status[0];
  rd(1,2); V g2=got[0]; U s2=status[0];
  char f[48]; snprintf(f,sizeof f," | overlap %d clocks",phy.fight);
  ok&=report("MDIO read: PHY switching 0 ns after MDC, push-pull MDC",g1==V({{8,0x01},{8,0xE1}})&&g2==V({{8,0x00},{8,0x22}})&&s1==U({1})&&s2==U({1})&&phy.fight==0,show(g1)+" |"+show(g2)+f);
  rd(5,2);
  ok&=report("MDIO read from an absent PHY: no TA, frame aborts",got[0].empty()&&status[0]==U({2}),showst(status[0]));
  return ok; }

struct Card { int pcs=1, psck=0, cnt=-1, miso=1, started=0; std::vector<int> bits; U resp, seen; int rbit=-1; } card;
void sd_env(){ int sck=cB(); int cs=t.p_select__out__b.get<bool>(); int mosi=oA();
  if(card.pcs && !cs){ card.cnt=-1; card.bits.clear(); card.started=0; card.rbit=-1; card.miso=1; }
  if(!cs && sck && !card.psck){
    if(!card.started && mosi==0){ card.started=1; card.cnt=0; }
    if(card.started){ if(card.cnt<48) card.bits.push_back(mosi);
      if(card.cnt==47){ std::vector<int> body(card.bits.begin(),card.bits.begin()+40); unsigned c=0; for(int i=0;i<7;i++) c=(c<<1)|card.bits[40+i];
        U by; for(int i=0;i<6;i++){ unsigned v=0; for(int k=0;k<8;k++) v=(v<<1)|card.bits[i*8+k]; by.push_back(v); } card.seen=by;
        int bad=(crc7_bits(body)!=c)||card.bits[47]!=1||card.bits[0]!=0||card.bits[1]!=1; unsigned cmd=by[0]&0x3F;
        card.resp={(unsigned)(0x01|(bad?0x08:0))}; if(cmd==8 && !bad){ card.resp.push_back(0); card.resp.push_back(0); card.resp.push_back(by[3]&0x0F); card.resp.push_back(by[4]); } }
      card.cnt++; } }
  if(!cs && !sck && card.psck && card.started){ int nx=card.cnt-56; card.miso=(nx>=0 && nx<(int)card.resp.size()*8)? (card.resp[nx/8]>>(7-nx%8))&1 : 1; }
  if(cs) card.miso=1;
  card.pcs=cs; card.psck=sck; pin_in=0x9E|mosi|(sck<<5)|(card.miso<<6); }

bool t_sdcard(){ bool ok=true; reset_both(); card=Card(); scen=sd_env;
  CH=1; program(cat({I_order(1),I_line(0,6),I_clock(GENERATE,63,5,0,0),I_out(3,0),I_wdog(20000),I_start(0,0,0,1),I_main(96,0,0,0,6)}));
  CH=0; program(cat({I_order(1),I_line(0,0),I_clock(SYNC,0,5,0),I_out(3,1),I_start(0,0,0,1),I_main(40,1),I_crc_a(7,7,0,0x09),I_crc_b(1,0,1,0,0),I_reply(REPLY_ALWAYS,16,0,0xFFFF)}));
  auto cmd=[&](const U&c,const char*name,const U&want_seen,const U&want_resp){ clear_results(); card=Card();
    CH=0; program(cat({I_data(8,c[0]),I_data(8,c[1]),I_data(8,c[2]),I_data(8,c[3]),I_data(8,c[4]),I_run(2)})); CH=1; program(I_run(1));
    idle(96*130+2000); wait_return();
    U all; for(auto&x:got[1]) all.push_back(x.second); size_t k=0; while(k<all.size() && all[k]==0xFF) k++;
    U r(all.begin()+std::min(k,all.size()),all.begin()+std::min(k+want_resp.size(),all.size()));
    return report(name,card.seen==want_seen&&r==want_resp&&status[0]==U({1})&&status[1]==U({1}),std::string(" card saw")+hexs(card.seen)+", reply"+hexs(r)); };
  ok&=cmd({0x40,0,0,0,0},"SD card CMD0, CRC-7 appended by the chip, R1 = 01",{0x40,0,0,0,0,0x95},{0x01});
  ok&=cmd({0x48,0,0,0x01,0xAA},"SD card CMD8, CRC-7 87, R7 echoes 1AA",{0x48,0,0,0x01,0xAA,0x87},{0x01,0x00,0x00,0x01,0xAA});
  return ok; }

struct Spi3 { unsigned regs[128]={0}; int pcs=1, psck=0, n=0, out=1, rd=0, drv=0, fight=0; unsigned addr=0, sh=0; } s3;
void spi3_env(){ int sck=cA(); int cs=t.p_select__out__a.get<bool>(); int chip=t.p_data__oe__a.get<bool>(); if(chip && s3.drv) s3.fight++; int sdio=chip? (int)t.p_data__out__a.get<bool>() : (s3.drv? s3.out : 1);
  if(s3.pcs && !cs){ s3.n=0; s3.sh=0; s3.out=1; s3.rd=0; }
  if(!cs && sck && !s3.psck){ s3.sh=((s3.sh<<1)|sdio)&0xFF; s3.n++;
    if(s3.n==8){ s3.rd=(s3.sh>>7)&1; s3.addr=s3.sh&0x7F; }
    else if(s3.n>8 && (s3.n%8)==0 && !s3.rd){ s3.regs[s3.addr++&0x7F]=s3.sh; } }
  if(!cs && !sck && s3.psck && s3.rd && s3.n>=8){ int k=s3.n-8; unsigned v=s3.regs[(s3.addr+k/8)&0x7F]; s3.out=(v>>(7-k%8))&1; s3.drv=1; }
  if(cs){ s3.out=1; s3.drv=0; }
  s3.pcs=cs; s3.psck=sck; pin_in=0xFA|sdio|(sck<<2); }

bool t_spi3(){ bool ok=true; reset_both(); s3=Spi3(); scen=spi3_env; unsigned reg=0x34;
  CH=0; program(cat({I_order(1),I_line(0,0),I_clock(GENERATE,25,2,0,0),I_out(1,1),I_wdog(5000),I_start(0,0,0,1),I_hdr(1,reg&0x7F,8,0,1,2),I_hdr(2,reg|0x80,8,0,1,1),I_main(16,2)}));
  program(cat({I_data(8,0x5A),I_data(8,0xC3),I_run(2)})); idle(2000); wait_return();
  char d[64]; snprintf(d,sizeof d," device regs 34,35 = %02X %02X",s3.regs[0x34],s3.regs[0x35]);
  ok&=report("3-wire SPI write: address byte, 2 data bytes on one SDIO line",s3.regs[0x34]==0x5A&&s3.regs[0x35]==0xC3&&status[0]==U({1}),d);
  s3.regs[0x34]=0x9E; s3.regs[0x35]=0x07; clear_results(); program(I_run(1)); idle(2000); wait_return();
  char f[48]; snprintf(f,sizeof f," | both driving: %d clocks",s3.fight);
  ok&=report("3-wire SPI read: push-pull, chip releases SDIO for the read",got[0]==V({{8,0x9E},{8,0x07}})&&status[0]==U({1})&&s3.fight==0,show(got[0])+f);
  return ok; }

bool t_dali(){ const long T=41666; bool ok=true; reset_both();
  CH=1; program(cat({I_order(1),I_line(3,3),I_clock(ASYNC,(unsigned)T),I_out(2,1),I_start(1,1,0,1),I_main(16,1)}));
  scen=[&]{ int bus=oB(); tr.push_back(bus); pin_in=0xF7|(bus<<3); };
  tx_run(1,{{8,0x03},{8,0x90}},2); wait_status(1,1); idle(T*20);
  size_t s=first_fall(tr); unsigned v=0; bool okb=true; int nb=0;
  for(int k=0;k<17;k++){ size_t a=s+k*T+T/4, b=s+k*T+3*T/4; if(b>=tr.size()){ okb=false; break; } int lo=tr[a], hi=tr[b]; if(lo==hi) okb=false; v=(v<<1)|(unsigned)(hi&&!lo); nb++; }
  bool stop=true; long late=0; for(size_t k=s+17*T;k<s+19*T && k<tr.size();k++) if(!tr[k]){ late++; if(k>s+17*T+T/8) stop=false; }
  char d[96]; snprintf(d,sizeof d," start %u, address %02X, command %02X, released %ld clocks after the last bit",(v>>16)&1,(v>>8)&0xFF,v&0xFF,late);
  ok&=report("DALI forward frame: Manchester 1200 bit/s, start + 16 bits MSB first",okb&&nb==17&&v==0x10390&&stop&&status[1]==U({1}),d);
  reset_both(); CH=0; program(cat({I_order(1),I_line(3,0,0,0,0,0,1),I_clock(ASYNC,(unsigned)T),I_start(1,1,0,0,0),I_main(8,0),I_run(0)}));
  unsigned back=0xA5; m0.add(1,T*10); auto mb=[&](int b){ m0.add(b?0:1,T/2); m0.add(b?1:0,T/2); }; mb(1); for(int i=7;i>=0;i--) mb((back>>i)&1); m0.add(1,T*3);
  scen=[&]{ pin_in=0xFE|m0.step(); }; run_model(m0,T);
  ok&=report("DALI backward frame: Manchester decoder, first edge = bit boundary",got[0]==V({{8,back}})&&status[0]==U({1}),show(got[0]));
  m0=Wave(); clear_results(); m0.add(1,T*30); mb(1); for(int i=7;i>=0;i--) mb((0x3C>>i)&1); m0.add(1,T*3); run_model(m0,T);
  ok&=report("DALI: a second backward frame after idle",got[0]==V({{8,0x3C}})&&status[0]==U({1}),show(got[0]));
  return ok; }

std::vector<int> stuff5(const std::vector<int>&raw){ std::vector<int> o; int run=0,last=-1; for(int b:raw){ o.push_back(b); if(b==last) run++; else { run=1; last=b; } if(run==5){ int x=!b; o.push_back(x); last=x; run=1; } } return o; }
std::vector<int> unstuff5(const std::vector<int>&s,size_t count,size_t&used){ std::vector<int> o; int run=0,last=-1; size_t i=0; bool skip=false;
  while(o.size()<count && i<s.size()){ int b=s[i++]; if(skip){ skip=false; run=1; last=b; continue; } o.push_back(b); if(b==last) run++; else { run=1; last=b; } if(run==5) skip=true; }
  if(skip && i<s.size()) i++; used=i; return o; }
std::vector<int> can_ext(unsigned id,const U&data){ std::vector<int> r; r.push_back(0); for(int i=28;i>=18;i--) r.push_back((id>>i)&1); r.push_back(1); r.push_back(1);
  for(int i=17;i>=0;i--) r.push_back((id>>i)&1); r.push_back(0); r.push_back(0); r.push_back(0); for(int i=3;i>=0;i--) r.push_back((data.size()>>i)&1);
  for(unsigned d:data) for(int i=7;i>=0;i--) r.push_back((d>>i)&1); return r; }
V msb_chunks(const std::vector<int>&b,size_t from,size_t n){ V o; for(size_t i=from;i<from+n;i+=8){ unsigned k=std::min<size_t>(8,from+n-i), v=0; for(unsigned j=0;j<k;j++) v=(v<<1)|(unsigned)b[i+j]; o.push_back({k,v}); } return o; }

bool t_can_ext(){ const long P=200; bool ok=true; unsigned id=(2u<<26)|(127250u<<8)|0x23; U data={0x01,0x34,0x12,0xFF,0x7F,0xFF,0x7F,0xFD};
  std::vector<int> raw=can_ext(id,data); size_t nb=raw.size()-1; unsigned crc=crc_wire(raw,15,0x4599,0); std::vector<int> crcb=crc_tx(crc,15,0);
  B rxprog=cat({I_order(1),I_line(0,0,5,0,0,1),I_clock(ASYNC,P),I_out(2),I_start(0,1,0,0,0),I_main(nb+15,0),I_crc_a(15,0,0,0x4599),I_crc_b(1,1,0,0,0),I_reply(REPLY_GOOD,2,0,0x2),I_run(0)});
  for(int bad=0;bad<2;bad++){ reset_both(); CH=0; program(rxprog);
    std::vector<int> full=raw; for(int b:crcb) full.push_back(b); if(bad) full[full.size()-3]^=1; std::vector<int> st=stuff5(full); size_t n=st.size();
    for(int i=0;i<3;i++) m0.add(1,P); for(int b:st) m0.add(b,P); for(int i=0;i<10;i++) m0.add(1,P);
    std::vector<int> smp; long t0=-1;
    scen=[&]{ int nd=m0.step(); int bus=nd && oA(); if(t0<0 && !nd) t0=(long)cycles; if(t0>=0 && ((long)cycles-t0)%P==P/2) smp.push_back(bus); pin_in=0xFE|bus; };
    run_model(m0,P*4);
    bool ack=smp.size()>n+2 && smp[n]==1 && smp[n+1]==(bad?1:0) && smp[n+2]==1;
    V exp=msb_chunks(full,1,nb+15); exp.push_back({14,bad?2u:3u});
    char d[96]; snprintf(d,sizeof d," %zu stuffed bits, result %s, delim/ack/delim %d%d%d",n,show(V(got[0].end()-std::min<size_t>(1,got[0].size()),got[0].end())).c_str(),smp.size()>n?smp[n]:-1,smp.size()>n+1?smp[n+1]:-1,smp.size()>n+2?smp[n+2]:-1);
    ok&=report(bad?"CAN 2.0B extended: corrupted CRC, no ACK":"CAN 2.0B / NMEA 2000 receive: PGN 127250, CRC-15, ACK",got[0]==exp&&ack&&status[0]==U({1}),d); }
  reset_both(); CH=0; program(rxprog);
  CH=1; program(cat({I_order(1),I_line(0,3,5,0,0,1),I_clock(ASYNC,P),I_out(2),I_start(0,1,0,1),I_main(nb,1),I_crc_a(15,0,0,0x4599),I_crc_b(1,0,1,0,0)}));
  E e; for(size_t i=1;i<raw.size();i+=8){ unsigned k=std::min<size_t>(8,raw.size()-i), v=0; for(unsigned j=0;j<k;j++) v=(v<<1)|(unsigned)raw[i+j]; e.push_back({k,v}); }
  std::vector<int> smp; long t0=-1;
  scen=[&]{ int bus=oA() && oB(); if(t0<0 && !bus) t0=(long)cycles; if(t0>=0 && ((long)cycles-t0)%P==P/2) smp.push_back(bus); pin_in=0xF6|bus|(bus<<3); };
  tx_run(1,e,2); wait_status(1,1); wait_status(0,1); idle(P*20);
  size_t used=0; std::vector<int> fr=unstuff5(smp,nb+1+15,used);
  bool body=fr.size()==nb+16 && std::vector<int>(fr.begin(),fr.begin()+nb+1)==raw, cok=body && std::vector<int>(fr.begin()+nb+1,fr.end())==crcb;
  bool ack=smp.size()>used+2 && smp[used]==1 && smp[used+1]==0 && smp[used+2]==1;
  char d[96]; snprintf(d,sizeof d," body %d crc %d ack %d, A result %s, status A%s B%s",body,cok,ack,got[0].empty()?"-":show(V(got[0].end()-1,got[0].end())).c_str(),showst(status[0]).c_str(),showst(status[1]).c_str());
  ok&=report("CAN 2.0B extended chip to chip: B sends with CRC, A checks and ACKs",body&&cok&&ack&&!got[0].empty()&&got[0].back()==std::make_pair(14u,3u)&&status[0]==U({1})&&status[1]==U({1}),d);
  return ok; }

bool t_rc5(){ const long T=88900; bool ok=true; unsigned addr=5, cmd=0x35, tog=1;
  std::vector<int> bits={1,1,(int)tog}; for(int i=4;i>=0;i--) bits.push_back((addr>>i)&1); for(int i=5;i>=0;i--) bits.push_back((cmd>>i)&1);
  reset_both(); CH=0; program(cat({I_order(1),I_line(3,0,0,0,1),I_clock(RECOVER,(unsigned)T),I_start(0x3,2,0,0,0),I_main(12,0),I_run(0)}));
  m0.add(1,T*4); for(int b:bits){ m0.add(b,T/2); m0.add(!b,T/2); } m0.add(1,T*4);
  scen=[&]{ pin_in=0xFE|m0.step(); }; run_model(m0,T);
  unsigned v1=0,v2=0; for(int i=2;i<10;i++) v1=(v1<<1)|(unsigned)bits[i]; for(int i=10;i<14;i++) v2=(v2<<1)|(unsigned)bits[i];
  ok&=report("RC5 infrared receive: 1.778 ms bits (DIV 88900, above 16 bits)",got[0]==V({{8,v1},{4,v2}})&&status[0]==U({1}),show(got[0]));
  reset_both(); CH=1; program(cat({I_order(1),I_line(3,3),I_clock(ASYNC,(unsigned)T),I_out(3,0),I_start(0x3,2,0,1),I_main(12,1)}));
  scen=[&]{ int b=oB(); tr.push_back(b); pin_in=0xF7|(b<<3); };
  tx_run(1,{{8,v1},{4,v2}},2); wait_status(1,1); idle(T*16);
  size_t rise=0; for(size_t k=1;k<tr.size();k++) if(!tr[k-1] && tr[k]){ rise=k; break; }
  size_t s0=rise-T/2; std::vector<int> got_bits; bool clean=true;
  for(int k=0;k<14;k++){ size_t a=s0+k*T+T/4, b=s0+k*T+3*T/4; if(b>=tr.size()){ clean=false; break; } if(tr[a]==tr[b]) clean=false; got_bits.push_back(tr[b]); }
  char d[64]; snprintf(d,sizeof d," 14 bits %s, toggle %d, address %u, command %02X",clean?"clean":"BAD",got_bits.size()>2?got_bits[2]:-1,addr,cmd);
  ok&=report("RC5 transmit: carrier-enable envelope for an IR LED driver",clean&&got_bits==bits&&status[1]==U({1}),d);
  return ok; }

bool t_kline5(){ const long S=40, W=2500000/S, D=4808; bool ok=true;
  reset_both();
  unsigned blk[5]={0xF0,0x0F,0xF0,0x0F,0xF0};
  CH=0; program(cat({I_line(0,0),I_clock(ASYNC,(unsigned)W),I_out(2,1),I_start(blk[0],8,0,1),I_hdr(1,blk[1],8,0,1),I_hdr(2,blk[2],8,0,1),I_hdr(3,blk[3],8,0,1),I_hdr(4,blk[4],8,0,1),
    I_main(1,1),I_branch(0,KEEP,KEEP,1,0,0,0)}));
  CH=1; program(cat({I_line(0,0),I_clock(ASYNC,D),I_out(2,1),I_start(0,1,0,1),I_main(9,1)}));
  scen=[&]{ int bus=oA() && oB() && m0.step(); tr.push_back(bus); pin_in=0xFE|bus; };
  CH=0; program(cat({I_data(1,1),I_run(2)}));
  for(long i=0;i<20000000 && status[0].empty();i++) clk();
  size_t init_end=tr.size();
  CH=0; program(cat({I_clear(),I_line(0,0),I_clock(ASYNC,D),I_start(0,1,0,0,0),I_main(9,0),I_run(0)}));
  m0.add(1,(long)(100*50000/S)); uwave(m0,0x55,D,8,0,1); m0.add(1,D*2); uwave(m0,0x08,D,8,0,1); m0.add(1,D*2); uwave(m0,0x08,D,8,0,1);
  while(m0.busy()) clk(); idle(D*12);
  CH=1; program(cat({I_data(8,0xF7),I_data(1,1),I_run(0)})); wait_status(1,1); idle(D*12);
  m0.add(1,30*50000/S); uwave(m0,0xCC,D,8,0,1); run_model(m0,D*12);
  size_t s0=first_fall(tr); std::vector<uint8_t> init(tr.begin(),tr.begin()+init_end); auto f=udecode(init,4*W,8,0,1,0,1);
  long bitlen=low_run(tr,s0,0,nullptr);
  U rx; for(auto&x:got[0]) if(x.first==8) rx.push_back(x.second);
  char d[96]; snprintf(d,sizeof d," address byte%s, start bit %.1f ms (scaled 1/%ld)",hexs(values(f)).c_str(),bitlen/50000.0,S);
  ok&=report("K-Line 5-baud init: address 33 sent at 5 bit/s (4 samples per bit)",values(f)==U({0x33})&&all_ok(f)&&std::labs(bitlen-4*W)<=W/100,d);
  ok&=report("K-Line 5-baud: sync 55, key bytes 08 08, tester F7, ECU CC",rx==U({0x55,0x08,0x08,0xF7,0xCC}),hexs(rx));
  return ok; }

typedef bool(*TestFn)();
struct T { const char*key; TestFn fn; };
std::vector<T> tests={{"rs485",t_rs485},{"midi",t_midi},{"nmea0183",t_nmea0183},{"profibus",t_profibus},{"modbus",t_modbus},{"dmx",t_dmx},{"lin",t_lin},{"kline",t_kline},{"kline5",t_kline5},{"sdi12",t_sdi12},{"smbus",t_smbus},{"mdio",t_mdio},{"sdcard",t_sdcard},{"spi3",t_spi3},{"dali",t_dali},{"can_ext",t_can_ext},{"rc5",t_rc5}};

int main(int argc,char**argv){ env=env_std; pin_in=0xFF; power_on(); program(I_link(4)); RET_R=4; bool ok=true;
  for(auto&x:tests){ if(argc>1 && strcmp(argv[1],x.key)) continue; printf("== %s\n",x.key); ok&=x.fn(); }
  printf(ok?"ALL PASS\n":"FAILED\n"); return !ok; }
