// =============================================================================
// Project: ProEm - Open Source Protocol Emulator
// File: sim/t_ethernet.cpp
// Type: Test, pin level (CXXRTL)
// Device under test: protocol_emulator (src/top/protocol_emulator.sv)
// Author: Paul Vincent Bezzina
// Language: C++14
// Description:
// =============================================================================

#include "bench.h"
double tclk=20.0; std::vector<std::pair<double,int>> edges; size_t ei=0; int line=0; double now=0;
void eth_env(){ now+=tclk; while(ei<edges.size() && edges[ei].first<=now){ line=edges[ei].second; ei++; } pin_in=(pin_in&~1u)|line; }
uint32_t crc32(const std::vector<uint8_t>&d){ uint32_t c=0xFFFFFFFF; for(uint8_t b:d){ c^=b; for(int k=0;k<8;k++) c=(c>>1)^(0xEDB88320&(-(c&1))); } return ~c; }
double jit(){ return ((rand()%7)-3)*1.0; }
void send_frame(const std::vector<uint8_t>&wire){ edges.clear(); ei=0; double t0=now+200+(rand()%1000)*tclk/1000.0;
  for(size_t i=0;i<wire.size();i++) for(int k=0;k<8;k++){ int b=(wire[i]>>k)&1; double s=t0+(i*8+k)*100.0; edges.push_back({s+jit(),!b}); edges.push_back({s+50+jit(),b}); }
  double end=t0+wire.size()*800.0; edges.push_back({end,1}); edges.push_back({end+250,0});
  while(ei<edges.size()) clk(); idle(200); }
int main(int argc,char**argv){ int mhz=argc>1?atoi(argv[1]):50; tclk=1000.0/mhz; int div=(int)(100.0/tclk+0.5); int endlen= mhz<=40?7:(mhz<=50?8:10);
  srand(mhz); env=eth_env; power_on(); bool ok=true;
  CH=0; program(cat({I_link(4),I_line(3,0),I_clock(RECOVER,div,0,0,0,1),I_start(0xD5,8,0,0,0),I_hdr(1,0xFF,8,1,0),I_hdr(2,0xFF,8,1,0),I_hdr(3,0xFF,8,1,0),I_hdr(4,0xFF,8,1,0),I_hdr(5,0xFF,8,1,0),I_hdr(6,0xFF,8,1,0),I_main(0,0,1,0,0),I_end(endlen,0,(1u<<endlen)-1),I_run(0)}));
  RET_R=4;
  int good=0, sent_b=0, other=0, rejected=0;
  for(int f=0;f<24;f++){ bool bc=rand()%4!=0; std::vector<uint8_t> fr; for(int i=0;i<6;i++) fr.push_back(bc?0xFF:(i==0?0x02:rand()&0xFF));
    for(int i=0;i<6;i++) fr.push_back(rand()&0xFF); fr.push_back(0x08); fr.push_back(0x06); int pl=2+rand()%6; for(int i=0;i<pl;i++) fr.push_back(rand()&0xFF);
    uint32_t c=crc32(fr); for(int i=0;i<4;i++) fr.push_back((c>>(8*i))&0xFF);
    std::vector<uint8_t> w(7,0x55); w.push_back(0xD5); w.insert(w.end(),fr.begin(),fr.end());
    clear_results(); send_frame(w); wait_return();
    if(bc){ sent_b++; std::vector<uint8_t> rx; bool shape=true; for(auto&e:got[0]){ if(e.first!=8) shape=false; rx.push_back(e.second); }
      bool fine=shape && rx==fr && status[0]==std::vector<unsigned>({1}) && crc32(std::vector<uint8_t>(rx.begin(),rx.end()-4))==c; if(fine) good++;
      else if(sent_b-good<4) printf("    frame %d: %zu entries (want %zu) status%s\n",f,got[0].size(),fr.size(),showst(status[0]).c_str()); }
    else { other++; if(got[0].empty() && status[0]==std::vector<unsigned>({2})) rejected++; } }
  char d[128]; snprintf(d,sizeof d," %d MHz, %d clocks/bit: %d/%d broadcast intact (CRC checked), %d/%d others rejected",mhz,div,good,sent_b,rejected,other);
  ok&=report("10BASE-T receive, Manchester decoded on chip",good==sent_b&&rejected==other,d);
  std::vector<uint8_t> big(6,0xFF); for(int i=0;i<58;i++) big.push_back(i); std::vector<uint8_t> w(7,0x55); w.push_back(0xD5); w.insert(w.end(),big.begin(),big.end());
  clear_results(); send_frame(w); wait_return();
  printf("    big frame: %zu entries returned of %zu\n",got[0].size(),big.size());
  ok&=report("64-byte frame: return link too slow, overflow reported",status[0].size()==1&&(status[0][0]&0x10)&&(status[0][0]&1),std::string(" status")+showst(status[0]));
  printf(ok?"ALL PASS\n":"FAILED\n"); return !ok; }
