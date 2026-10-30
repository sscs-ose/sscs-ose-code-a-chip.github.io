# =============================================================================
# Project: ProEm - Open Source Protocol Emulator
# File: docs/diagram/make_diagram.py
# Type: Script: architecture diagram generator
# Author: Paul Vincent Bezzina
# Language: Python 3
# Description:
# =============================================================================
import base64
W,H=2800,1940
C=dict(bg="#F4F7F6",ink="#15201F",muted="#5A6B6A",rule="#CCD8D5",surf="#FFFFFF",
 rx="#0B7670",rxs="#E0F0EE",tx="#B4531A",txs="#F8E7DC",cf="#6A5FB0",cfs="#ECE9F7",gold="#9A7B12",golds="#F6EFD6",cd="#2F5D9A",cds="#E4ECF7")
o=[]
def A(s): o.append(s)
def esc(t): return t.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")
def rect(x,y,w,h,fill,stroke,r=8,sw=1.6,dash=None):
    d=f' stroke-dasharray="{dash}"' if dash else ''
    A(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{d}/>')
def T(x,y,t,size=15,col=None,w=400,anchor="middle",fam="body",it=False):
    f={"body":"Plex","disp":"Barlow","mono":"PlexMono"}[fam]
    st=' font-style="italic"' if it else ''
    A(f'<text x="{x}" y="{y}" font-family="{f}" font-size="{size}" font-weight="{w}" fill="{col or C["ink"]}" text-anchor="{anchor}"{st}>{esc(t)}</text>')
KIND={"plain":("surf","ink"),"rx":("rxs","rx"),"tx":("txs","tx"),"cf":("cfs","cf"),"gold":("golds","gold"),"cd":("cds","cd"),"dash":("surf","muted")}
def box(x,y,w,h,title,subs=(),kind="plain",tsize=20,ssize=13.5,dash=False,top=False):
    f,s=KIND[kind]
    rect(x,y,w,h,C[f],C[s],dash="6 5" if dash else None)
    n=len(subs); lh=ssize+4.5
    ty=(y+30) if top else (y+h/2-(n*lh)/2+6)
    T(x+w/2,ty,title,tsize,w=600,fam="disp")
    for i,s2 in enumerate(subs): T(x+w/2,ty+23+i*lh,s2,ssize,C["muted"])
def line(pts,col,sw=2.2,arrow=True,dash=None,start=False):
    d=" ".join(("M" if i==0 else "L")+f"{x},{y}" for i,(x,y) in enumerate(pts))
    m={C["rx"]:"rx",C["tx"]:"tx",C["ink"]:"ink",C["cf"]:"cf",C["gold"]:"gold",C["muted"]:"mu",C["cd"]:"cd"}[col]
    da=f' stroke-dasharray="{dash}"' if dash else ''
    ae=f' marker-end="url(#a{m})"' if arrow else ''
    asr=f' marker-start="url(#a{m})"' if start else ''
    A(f'<path d="{d}" fill="none" stroke="{col}" stroke-width="{sw}" stroke-linejoin="round"{da}{ae}{asr}/>')
def lab(x,y,t,col,anchor="start",size=13,w=500): T(x,y,t,size,col,anchor=anchor,w=w)
def labbg(x,y,t,col,size=13):
    wd=len(t)*size*0.5+4
    rect(x-wd/2,y-size,wd,size+5,C["bg"],C["bg"],r=3,sw=0)
    T(x,y,t,size,col,anchor="middle",w=500)
def font(name,path,weight,style="normal"):
    b=base64.b64encode(open(path,"rb").read()).decode()
    return f'@font-face{{font-family:"{name}";src:url(data:font/woff2;base64,{b}) format("woff2");font-weight:{weight};font-style:{style};}}'
import os
import sys
HERE=os.path.dirname(os.path.abspath(__file__))
F=os.path.join(HERE,"fonts")+"/"
css="".join([font("Plex",F+"ibm-plex-sans-latin-400-normal.woff2",400),font("Plex",F+"ibm-plex-sans-latin-500-normal.woff2",500),
 font("Plex",F+"ibm-plex-sans-latin-600-normal.woff2",600),font("Plex",F+"ibm-plex-sans-latin-400-italic.woff2",400,"italic"),
 font("PlexMono",F+"ibm-plex-mono-latin-400-normal.woff2",400),font("PlexMono",F+"ibm-plex-mono-latin-500-normal.woff2",500),
 font("Barlow",F+"barlow-semi-condensed-latin-500-normal.woff2",500),font("Barlow",F+"barlow-semi-condensed-latin-600-normal.woff2",600),
 font("Barlow",F+"barlow-semi-condensed-latin-700-normal.woff2",700)])

A(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">')
A(f'<defs><style>{css}</style>')
for n,c in [("rx",C["rx"]),("tx",C["tx"]),("ink",C["ink"]),("cf",C["cf"]),("gold",C["gold"]),("mu",C["muted"]),("cd",C["cd"])]:
    A(f'<marker id="a{n}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="{c}"/></marker>')
A('</defs>')
A(f'<rect width="{W}" height="{H}" fill="{C["bg"]}"/>')

T(60,80,"ProEm · Protocol Emulator ASIC",48,w=700,anchor="start",fam="disp")
T(W-60,72,"Paul Vincent Bezzina  |  Open Source Protocol Emulator",20,C["muted"],anchor="end",w=500)
T(60,118,"Full architecture · ISA v0.7.1 · IHP 130 nm through Tiny Tapeout (6 × 4 tiles) · 50 MHz system clock",20,C["muted"],anchor="start")

rect(300,160,2100,1300,"none",C["muted"],r=16,sw=1.6,dash="10 7")
T(322,190,"CHIP · protocol_emulator",15,C["muted"],anchor="start",w=500,fam="mono")

box(40,220,220,1220,"RP2040",["host / demo board","","sends ISA bytes","0x55 first (auto-baud)","","programs a frame:","START · HDR · MAIN","END · LINE · CLOCK","OUT · RUN","","loads write data","with DATA","","receives host entries,","frame status and","link events","","both links are UART;","PIO for a fast return"],"plain",28,14)
box(2440,220,320,1220,"Bus & pads",["pin_in[7:0] → chip","","per channel, each with","an output enable:","data · pair (D−)","clock · select","","open drain: enable","pulls the pad low","","bidirectional pads","(SDA, SCL, D+, D−)","are read back","through pin_in","","UART · SPI · I²C · PS/2","10BASE-T · USB LS · CAN"],"plain",28,14)

box(330,220,290,120,"UART receiver",["auto-baud on 0x55 (8 bit times)","8N1 → byte + valid","rx_error on a low stop bit"],"cf",20)
box(330,380,290,300,"Control unit",["ISA v0.7.1 decoder","opcode · CH · N + 0–4 operands","","registered cfg bus → chain A / B","RUN · HALT · CLEAR pulses","DATA → host FIFO · BRANCH: rules,","CRC set-up and reply pattern","LINE · CLOCK · OUT per channel","LINK divider for the return","cmd_error on bad BRANCH / HDR"],"cf",22)
box(330,1250,290,180,"Return path",["round robin: A · B · link events","2-byte messages","{10 C 0 len} + value","len 14 = CRC result","len 15 = frame status","UART TX at the LINK rate"],"gold",22)
line([(262,280),(328,280)],C["cf"]); labbg(295,270,"rx_serial",C["cf"])
line([(475,340),(475,378)],C["cf"])
line([(328,1340),(262,1340)],C["gold"]); labbg(295,1330,"tx_serial",C["gold"])

box(2170,220,200,120,"Input pipeline",["2 synchroniser flops","+ 1 register per pin","→ pins[7:0]"],"rx",20,13)
line([(2438,280),(2372,280)],C["rx"]); labbg(2405,270,"pin_in",C["rx"])
line([(2270,340),(2270,1140)],C["rx"],arrow=False,sw=2.6)

rect(650,200,1490,860,C["surf"],C["ink"],r=16,sw=2.2)
T(672,230,"CHANNEL A",16,C["ink"],anchor="start",w=600,fam="mono")
T(2120,230,"emulator_channel · 8,707 cells",14,C["muted"],anchor="end")

rect(680,250,880,515,"#FBFDFC",C["rx"],r=12,sw=2)
T(700,278,"FRAME CHAIN",15,C["rx"],anchor="start",w=600,fam="mono")
T(1540,278,"6,753 cells (CRC 846) · one bit per tick",13,C["muted"],anchor="end")
names=["START","HDR 1","HDR 2","HDR 3","HDR 4","HDR 5","HDR 6"]
subs=[["own pin","match, level","or write"]]+[["1–8 bits","compare,","capture, write"]]*6
for i,nm in enumerate(names):
    x=700+i*122
    box(x,300,106,96,nm,subs[i],"rx",18,12,dash=(i>=3))
    if i<6: line([(x+106,348),(x+120,348)],C["ink"],sw=1.8)
T(1120,414,"per block: direction W · capture · ANY (any value) · SEEK (skip to the first bit) · group GRP · SR repeated START",13,C["muted"])
rect(700,424,840,40,"#FFFFFF",C["ink"],r=6,sw=1.4)
T(1120,450,"start_router: next active block · branch_unit: 2 rules switch to read / write or abort on a received field or a read-back mismatch",14,C["ink"],w=500)
box(700,486,180,184,"END",["16-bit window","one pin, or the","D+ / D− pair:","SE0 ends,","SE1 aborts","raw pins, end_tick"],"tx",20,12.5)
box(895,486,275,184,"MAIN",["read: bits → bytes,","to a count or until END","write: host entries,","split at count and bytes","ACK slot after each byte","fixed or follows RUN mode"],"rx",22,12.5)
box(1185,486,205,184,"Frame buffer",["16 × {wire, len, value}","commit · rollback","status entry per frame","writes wait at","almost full"],"gold",20,12.5)
box(1405,486,135,184,"Watchdog",["no bit, entry","or tx_done","for N clocks","→ end frame"],"plain",18,12.5)
line([(1170,578),(1183,578)],C["gold"],sw=1.8)
line([(880,578),(893,578)],C["tx"],sw=1.8)
line([(1120,466),(1120,484)],C["ink"],sw=1.8)
box(990,680,350,78,"CRC unit + tail",["1–16 bits in wire order, input registered: check (8E / AE)","or append; byte fields, across frames · reply after good / bad"],"rx",16,12)
line([(1132,672),(1132,680)],C["rx"],sw=1.6)
line([(1340,714),(1612,714),(1612,822),(1658,822)],C["tx"],sw=2); lab(1480,706,"CRC, reply (direct)",C["tx"],"middle",size=12)

box(680,790,225,240,"Host FIFO",["8 × {length, value}","filled by DATA","feeds a write MAIN","","host_full → drop flag"],"tx",20,13)
box(925,790,390,240,"Controls & status",["RUN · RUN READ · RUN WRITE","HALT · CLEAR · ORDER · WDOG","groups pick blocks per run mode","SR → length-0 wire entry = Sr","","status entry at each frame end:","complete · abort · timeout","line error · overflow · underrun","branch matched · branch abort","CRC result entry just before it"],"cf",20,12.5)
box(1335,790,225,240,"Entry dispatcher",["reads the buffer in order","wire → encoder","host + status → return","status entry = frame mark","for STOP / end of packet"],"gold",20,13)
line([(800,788),(800,778),(960,778),(960,672)],C["tx"],sw=2); lab(808,790+0,"",C["tx"],size=12); lab(966,776,"host entries",C["tx"],size=12)
line([(1360,672),(1360,788)],C["gold"],sw=2)

rect(1640,250,480,780,"#FAFCFE",C["cd"],r=12,sw=2)
T(1660,278,"LINE CODEC",15,C["cd"],anchor="start",w=600,fam="mono")
T(2100,278,"1,597 cells · LINE · CLOCK · OUT",13,C["muted"],anchor="end")
box(1660,296,440,150,"Tick source (CLOCK)",["SYNC: an edge of a clock pin","ASYNC / RECOVER: 22-bit bit timer (12 bit/s and up),","mid-bit sample, re-centred on every edge","GENERATE: drives SCK / SCL, waits for stretching"],"cd",19,13)
box(1660,462,440,196,"Decoder (LINE)",["NRZ · NRZI · NRZI pair (J / K, SE0, SE1)","Manchester: mid-bit edges, ¾-bit blanking, boundary lock","unstuffer: drop the bit after n equal bits","decoded bit replaces PIN_A, one tick per bit","stuff error → abort (not while sending)"],"cd",19,13)
box(1660,674,440,340,"Encoder (LINE + OUT)",["1-entry holding register from the dispatcher","NRZ · NRZI (from J) · Manchester","stuff bit after n equal bits","I²C controller: START · Sr · STOP","I²C target: START / STOP detect, drive after SCL falls","end of packet: SE0 SE0 J, or 2 bits high","read-back check of the driven pad → branch","wait entry: reply gap on the receive bit grid","cancel: drop queued bits, release the line","drive: off · while sending (released for reads) · open drain · always","outputs: data · pair · clock · select"],"cd",19,12.5)
line([(2268,370),(2102,370)],C["rx"]); line([(2268,540),(2102,540)],C["rx"])
lab(2110,360,"clock pin",C["rx"],size=12); lab(2110,530,"data pins",C["rx"],size=12)
line([(1658,540),(1562,540)],C["rx"]); lab(1600,528,"bit, tick",C["rx"],"middle",size=12)
line([(1562,600),(1658,600)],C["ink"],sw=1.8); lab(1600,590,"listen",C["ink"],"middle",size=12)
line([(1658,650),(1562,650)],C["ink"],sw=1.8); lab(1600,640,"tx_done",C["ink"],"middle",size=12)
line([(1562,860),(1658,860)],C["tx"]); lab(1600,850,"wire",C["tx"],"middle",size=12)
line([(1562,905),(1658,905)],C["gold"],sw=1.8,dash="6 4"); lab(1600,895,"mark",C["gold"],"middle",size=12)
line([(2102,850),(2438,850)],C["tx"],sw=2.6); lab(2270,838,"data · pair · clock · select",C["tx"],"middle",size=13)
lab(2270,872,"+ output enables",C["tx"],"middle",size=12)

line([(620,500),(630,500),(630,1165),(648,1165)],C["cf"],dash="7 5",sw=1.8,arrow=True)
line([(630,500),(678,500)],C["cf"],dash="7 5",sw=1.8); lab(636,490,"cfg",C["cf"],size=12)
line([(620,640),(642,640),(642,900),(678,900)],C["tx"],sw=1.8); lab(648,890,"DATA",C["tx"],size=12)
line([(1447,1032),(1447,1082),(560,1082),(560,1248)],C["gold"]); lab(1100,1101,"host entries + status, channel A",C["gold"],"middle",size=12)

rect(650,1112,1490,118,C["surf"],C["ink"],r=16,sw=2.2,dash="10 6")
T(672,1142,"CHANNEL B",16,C["ink"],anchor="start",w=600,fam="mono")
T(1395,1170,"identical copy: its own host FIFO, frame chain, line codec and dispatcher",19,C["ink"])
T(1395,1200,"run both at once: SPI full duplex, UART RX + TX, USB TX looped into USB RX, Manchester TX into RX",15,C["muted"])
line([(2268,1140),(2142,1140)],C["rx"])
line([(2142,1200),(2438,1200)],C["tx"],sw=2.6); lab(2290,1190,"outputs",C["tx"],"middle",size=13)
line([(650,1210),(590,1210),(590,1248)],C["gold"])

lx,ly=330,1490
leg=[(C["cf"],"configuration","7 5"),(C["rx"],"pins, received bits",None),(C["tx"],"data to send, outputs",None),(C["gold"],"entries, status, return","6 4"),(C["ink"],"handshakes",None)]
for i,(c,t2,d) in enumerate(leg):
    x=lx+i*420
    line([(x,ly),(x+50,ly)],c,arrow=False,dash=d,sw=2.6); T(x+62,ly+5,t2,15,C["ink"],anchor="start")

T(60,1558,"Verified end to end at pin level",28,w=700,anchor="start",fam="disp")
T(430,1558,"every test sends ISA bytes to the chip, drives or models the real lines, and reads results back over the return UART",16,C["muted"],anchor="start")
cards=[("UART",["ASYNC timer · NRZ","RX from a sender 2 % off rate","TX on the other channel"],"rx"),
 ("SPI",["GENERATE SCK and chip select","full duplex on two channels","target mode on SYNC"],"rx"),
 ("I²C",["controller: S / Sr / P, stretching","target at 0x42: branch on R/W","controller ↔ target on one chip"],"cf"),
 ("PS/2",["SYNC on the falling edge","start, 8 data, parity, stop","two clock speeds"],"plain"),
 ("10BASE-T RX",["Manchester at 5 clocks / bit","jitter and random phase","CRC checked, MAC filter"],"gold"),
 ("Manchester TX",["preamble from write blocks","end-of-frame idle","looped into the other channel"],"gold"),
 ("USB low speed",["NRZI pair, stuffing, SE0 / SE1","CRC-5 / CRC-16 check and append","ACK handshake sent on chip"],"tx"),
 ("CAN",["5-bit stuffing, arbitration","CRC-15 checked or appended","ACK driven in the ACK slot"],"cd")]
for i,(nm,ls,k) in enumerate(cards):
    x=60+i*337
    box(x,1578,324,140,nm,ls,k,22,13.5)
T(60,1744,"plus 16 more standards, receive and transmit: RS-232/422/485 · MIDI · NMEA 0183 · PROFIBUS DP · Modbus RTU · DMX512 · LIN · K-Line · SDI-12 · SMBus/PMBus · MDIO · SD card · 3-wire SPI · DALI · CAN 2.0B / NMEA 2000 · RC5 infrared",15,C["ink"],anchor="start",w=500)
T(60,1768,"and 1,800 random programs, 600 random branch programs, 60 random CRCs chip to chip, SWD-style acknowledge, streaming and underrun, control tests: auto-baud, HALT, CLEAR, LINK, watchdog, error flags",15,C["muted"],anchor="start")

T(60,1806,"Where the logic cells go",28,w=700,anchor="start",fam="disp")
T(372,1806,"IHP cells per block (hierarchical synthesis, 19,145 in all) · routed layout: 25,612 cells with repair buffers and clock tree, 43 % of the core · timing met at every corner",16,C["muted"],anchor="start")
parts=[("Chain A",5907,C["rx"]),("CRC A",846,"#0E5A55"),("Codec A",1597,C["cd"]),("Host FIFO A",319,C["tx"]),("Chain B",5907,"#3E9C95"),("CRC B",846,"#2C7A74"),("Codec B",1597,"#6F8FC0"),("Host FIFO B",319,"#D98A5C"),
       ("Control unit",961,C["cf"]),("UART RX",434,"#9A90D0"),("Return path",324,C["gold"]),("Repair + clock tree",6467,"#B9C4C1")]
x0,y0,wt=60,1826,2680; total=25612/0.43
rect(x0,y0,wt,46,"#E6ECEA",C["rule"],r=6)
x=x0
for name,v,c in parts:
    w=wt*v/total
    A(f'<rect x="{x:.1f}" y="{y0}" width="{w:.1f}" height="46" fill="{c}"/>'); x+=w
T(x+18,y0+30,"free ≈ 57 % of the core area",16,C["muted"],anchor="start",w=500)
T(x0+wt-12,y0+30,"6 × 4 tiles",15,C["muted"],anchor="end",w=500)
for i,(name,v,c) in enumerate(parts):
    xx=x0+i*224; yy=y0+80
    A(f'<rect x="{xx}" y="{yy-13}" width="16" height="16" rx="3" fill="{c}"/>')
    T(xx+24,yy,f"{name} · {v:,}",14,C["ink"],anchor="start")
A('</svg>')
svg="\n".join(o)
open(os.path.join(HERE,"chip.svg"),"w").write(svg)
from playwright.sync_api import sync_playwright
with sync_playwright() as pw:
    exe=os.environ.get("CHROMIUM")
    b=pw.chromium.launch(executable_path=exe) if exe else pw.chromium.launch()
    pg=b.new_page(viewport={"width":W,"height":H},device_scale_factor=2)
    pg.set_content('<html><body style="margin:0">'+svg+'</body></html>')
    pg.evaluate("document.fonts.ready")
    pg.wait_for_timeout(800)
    pg.screenshot(path=os.path.join(HERE,"..","images","protocol_emulator_architecture.png"),clip={"x":0,"y":0,"width":W,"height":H})
    b.close()
