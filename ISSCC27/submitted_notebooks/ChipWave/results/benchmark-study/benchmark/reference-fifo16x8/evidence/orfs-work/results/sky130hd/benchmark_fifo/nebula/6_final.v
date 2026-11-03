module benchmark_fifo (clk,
    empty,
    full,
    rd_en,
    rst_n,
    wr_en,
    rd_data,
    wr_data);
 input clk;
 output empty;
 output full;
 input rd_en;
 input rst_n;
 input wr_en;
 output [15:0] rd_data;
 input [15:0] wr_data;

 wire _000_;
 wire _001_;
 wire _002_;
 wire _003_;
 wire _004_;
 wire _005_;
 wire _006_;
 wire _007_;
 wire _008_;
 wire _009_;
 wire _010_;
 wire _011_;
 wire _012_;
 wire _013_;
 wire _014_;
 wire _015_;
 wire _016_;
 wire _017_;
 wire _018_;
 wire _019_;
 wire _020_;
 wire _021_;
 wire _022_;
 wire _023_;
 wire _024_;
 wire _025_;
 wire _026_;
 wire _027_;
 wire _028_;
 wire _029_;
 wire _030_;
 wire _031_;
 wire _032_;
 wire _033_;
 wire _034_;
 wire _035_;
 wire _036_;
 wire _037_;
 wire _038_;
 wire _039_;
 wire _040_;
 wire _041_;
 wire _042_;
 wire _044_;
 wire _046_;
 wire _047_;
 wire _048_;
 wire _049_;
 wire _050_;
 wire _051_;
 wire _052_;
 wire _053_;
 wire _054_;
 wire _055_;
 wire _056_;
 wire _057_;
 wire _058_;
 wire _059_;
 wire _060_;
 wire _063_;
 wire _064_;
 wire _065_;
 wire _068_;
 wire _070_;
 wire _072_;
 wire _074_;
 wire _075_;
 wire _076_;
 wire _078_;
 wire _080_;
 wire _081_;
 wire _082_;
 wire _084_;
 wire _085_;
 wire _086_;
 wire _088_;
 wire _090_;
 wire _092_;
 wire _093_;
 wire _094_;
 wire _096_;
 wire _098_;
 wire _100_;
 wire _102_;
 wire _103_;
 wire _104_;
 wire _105_;
 wire _106_;
 wire _107_;
 wire _108_;
 wire _109_;
 wire _110_;
 wire _111_;
 wire _112_;
 wire _113_;
 wire _114_;
 wire _115_;
 wire _116_;
 wire _117_;
 wire _118_;
 wire _119_;
 wire _120_;
 wire _121_;
 wire _122_;
 wire _123_;
 wire _124_;
 wire _125_;
 wire _126_;
 wire _127_;
 wire _128_;
 wire _129_;
 wire _130_;
 wire _131_;
 wire _132_;
 wire _133_;
 wire _134_;
 wire _135_;
 wire _136_;
 wire _137_;
 wire _138_;
 wire _139_;
 wire _140_;
 wire _141_;
 wire _142_;
 wire _143_;
 wire _145_;
 wire _146_;
 wire _147_;
 wire _149_;
 wire _150_;
 wire _151_;
 wire _152_;
 wire _153_;
 wire _154_;
 wire _155_;
 wire _156_;
 wire _157_;
 wire _158_;
 wire _159_;
 wire _160_;
 wire _161_;
 wire _162_;
 wire _163_;
 wire _164_;
 wire _166_;
 wire _167_;
 wire _168_;
 wire _169_;
 wire _171_;
 wire _172_;
 wire _173_;
 wire _174_;
 wire _175_;
 wire _176_;
 wire _177_;
 wire _178_;
 wire _179_;
 wire _180_;
 wire _181_;
 wire _182_;
 wire _183_;
 wire _184_;
 wire _185_;
 wire _186_;
 wire _187_;
 wire _188_;
 wire _190_;
 wire _191_;
 wire _192_;
 wire _193_;
 wire _194_;
 wire _196_;
 wire _197_;
 wire _198_;
 wire _199_;
 wire _200_;
 wire _201_;
 wire _203_;
 wire _204_;
 wire _205_;
 wire _206_;
 wire _207_;
 wire _208_;
 wire _209_;
 wire _210_;
 wire _211_;
 wire _212_;
 wire _213_;
 wire _214_;
 wire _215_;
 wire _216_;
 wire _217_;
 wire _218_;
 wire _219_;
 wire _220_;
 wire _221_;
 wire _222_;
 wire _223_;
 wire _224_;
 wire _225_;
 wire _226_;
 wire _227_;
 wire _228_;
 wire _229_;
 wire _230_;
 wire _231_;
 wire _232_;
 wire _233_;
 wire _234_;
 wire _235_;
 wire _236_;
 wire _237_;
 wire _238_;
 wire _239_;
 wire _240_;
 wire _241_;
 wire _242_;
 wire _243_;
 wire _244_;
 wire _245_;
 wire _246_;
 wire _247_;
 wire _248_;
 wire _249_;
 wire _250_;
 wire _251_;
 wire _252_;
 wire _253_;
 wire _254_;
 wire _255_;
 wire _256_;
 wire _257_;
 wire _258_;
 wire _259_;
 wire _260_;
 wire _261_;
 wire _262_;
 wire _263_;
 wire _264_;
 wire _265_;
 wire _266_;
 wire _267_;
 wire _268_;
 wire _269_;
 wire _270_;
 wire _271_;
 wire _272_;
 wire _273_;
 wire _274_;
 wire _275_;
 wire _276_;
 wire _277_;
 wire _278_;
 wire _279_;
 wire _280_;
 wire _281_;
 wire _282_;
 wire _283_;
 wire _284_;
 wire _285_;
 wire _286_;
 wire _287_;
 wire _288_;
 wire _289_;
 wire _290_;
 wire _291_;
 wire _292_;
 wire _293_;
 wire _294_;
 wire _295_;
 wire _296_;
 wire _297_;
 wire _298_;
 wire _299_;
 wire _300_;
 wire _301_;
 wire _302_;
 wire _303_;
 wire _304_;
 wire _305_;
 wire _306_;
 wire _307_;
 wire _308_;
 wire _309_;
 wire _310_;
 wire _311_;
 wire _312_;
 wire _313_;
 wire _314_;
 wire _315_;
 wire _316_;
 wire _317_;
 wire _318_;
 wire _319_;
 wire _320_;
 wire _321_;
 wire _322_;
 wire _323_;
 wire _324_;
 wire _325_;
 wire _326_;
 wire _327_;
 wire _328_;
 wire _329_;
 wire _330_;
 wire _331_;
 wire _332_;
 wire _333_;
 wire _334_;
 wire _335_;
 wire _336_;
 wire _337_;
 wire _338_;
 wire _339_;
 wire _340_;
 wire _341_;
 wire _342_;
 wire _343_;
 wire _344_;
 wire _345_;
 wire _346_;
 wire _347_;
 wire _348_;
 wire _349_;
 wire _350_;
 wire _351_;
 wire _352_;
 wire _353_;
 wire _354_;
 wire _355_;
 wire _356_;
 wire _357_;
 wire _358_;
 wire _359_;
 wire _360_;
 wire _361_;
 wire _362_;
 wire _363_;
 wire _364_;
 wire _365_;
 wire _366_;
 wire _367_;
 wire _368_;
 wire _369_;
 wire _370_;
 wire _371_;
 wire _372_;
 wire _373_;
 wire _374_;
 wire _375_;
 wire _376_;
 wire _377_;
 wire _378_;
 wire _379_;
 wire _380_;
 wire _381_;
 wire _382_;
 wire _383_;
 wire _384_;
 wire _385_;
 wire _386_;
 wire _387_;
 wire _388_;
 wire _389_;
 wire _390_;
 wire _391_;
 wire _392_;
 wire _393_;
 wire _394_;
 wire _395_;
 wire _396_;
 wire _397_;
 wire _398_;
 wire _399_;
 wire _400_;
 wire _401_;
 wire _402_;
 wire _403_;
 wire _404_;
 wire _405_;
 wire _406_;
 wire _407_;
 wire _408_;
 wire _409_;
 wire _410_;
 wire _411_;
 wire _412_;
 wire _413_;
 wire _414_;
 wire _415_;
 wire _416_;
 wire _417_;
 wire _418_;
 wire _419_;
 wire _420_;
 wire _421_;
 wire _422_;
 wire _423_;
 wire _424_;
 wire _425_;
 wire _426_;
 wire _427_;
 wire _428_;
 wire _429_;
 wire _430_;
 wire _431_;
 wire _432_;
 wire _433_;
 wire _434_;
 wire _435_;
 wire _436_;
 wire _437_;
 wire _438_;
 wire _439_;
 wire _440_;
 wire _441_;
 wire _442_;
 wire _443_;
 wire _444_;
 wire _445_;
 wire _446_;
 wire _447_;
 wire _448_;
 wire _449_;
 wire _450_;
 wire _451_;
 wire _452_;
 wire _453_;
 wire _454_;
 wire _455_;
 wire _456_;
 wire _457_;
 wire _458_;
 wire _459_;
 wire _460_;
 wire _461_;
 wire _462_;
 wire _463_;
 wire _464_;
 wire _465_;
 wire _466_;
 wire _467_;
 wire _468_;
 wire _469_;
 wire _470_;
 wire _471_;
 wire _472_;
 wire _473_;
 wire _474_;
 wire _475_;
 wire _476_;
 wire _477_;
 wire _478_;
 wire _479_;
 wire _480_;
 wire _481_;
 wire net20;
 wire net21;
 wire net22;
 wire net23;
 wire net24;
 wire net25;
 wire net26;
 wire net27;
 wire net28;
 wire net29;
 wire net30;
 wire net31;
 wire net32;
 wire net33;
 wire net34;
 wire net35;
 wire net36;
 wire net37;
 wire net1;
 wire \rptr[0] ;
 wire \rptr[1] ;
 wire \rptr[2] ;
 wire net2;
 wire \storage[0][0] ;
 wire \storage[0][10] ;
 wire \storage[0][11] ;
 wire \storage[0][12] ;
 wire \storage[0][13] ;
 wire \storage[0][14] ;
 wire \storage[0][15] ;
 wire \storage[0][1] ;
 wire \storage[0][2] ;
 wire \storage[0][3] ;
 wire \storage[0][4] ;
 wire \storage[0][5] ;
 wire \storage[0][6] ;
 wire \storage[0][7] ;
 wire \storage[0][8] ;
 wire \storage[0][9] ;
 wire \storage[1][0] ;
 wire \storage[1][10] ;
 wire \storage[1][11] ;
 wire \storage[1][12] ;
 wire \storage[1][13] ;
 wire \storage[1][14] ;
 wire \storage[1][15] ;
 wire \storage[1][1] ;
 wire \storage[1][2] ;
 wire \storage[1][3] ;
 wire \storage[1][4] ;
 wire \storage[1][5] ;
 wire \storage[1][6] ;
 wire \storage[1][7] ;
 wire \storage[1][8] ;
 wire \storage[1][9] ;
 wire \storage[2][0] ;
 wire \storage[2][10] ;
 wire \storage[2][11] ;
 wire \storage[2][12] ;
 wire \storage[2][13] ;
 wire \storage[2][14] ;
 wire \storage[2][15] ;
 wire \storage[2][1] ;
 wire \storage[2][2] ;
 wire \storage[2][3] ;
 wire \storage[2][4] ;
 wire \storage[2][5] ;
 wire \storage[2][6] ;
 wire \storage[2][7] ;
 wire \storage[2][8] ;
 wire \storage[2][9] ;
 wire \storage[3][0] ;
 wire \storage[3][10] ;
 wire \storage[3][11] ;
 wire \storage[3][12] ;
 wire \storage[3][13] ;
 wire \storage[3][14] ;
 wire \storage[3][15] ;
 wire \storage[3][1] ;
 wire \storage[3][2] ;
 wire \storage[3][3] ;
 wire \storage[3][4] ;
 wire \storage[3][5] ;
 wire \storage[3][6] ;
 wire \storage[3][7] ;
 wire \storage[3][8] ;
 wire \storage[3][9] ;
 wire \storage[4][0] ;
 wire \storage[4][10] ;
 wire \storage[4][11] ;
 wire \storage[4][12] ;
 wire \storage[4][13] ;
 wire \storage[4][14] ;
 wire \storage[4][15] ;
 wire \storage[4][1] ;
 wire \storage[4][2] ;
 wire \storage[4][3] ;
 wire \storage[4][4] ;
 wire \storage[4][5] ;
 wire \storage[4][6] ;
 wire \storage[4][7] ;
 wire \storage[4][8] ;
 wire \storage[4][9] ;
 wire \storage[5][0] ;
 wire \storage[5][10] ;
 wire \storage[5][11] ;
 wire \storage[5][12] ;
 wire \storage[5][13] ;
 wire \storage[5][14] ;
 wire \storage[5][15] ;
 wire \storage[5][1] ;
 wire \storage[5][2] ;
 wire \storage[5][3] ;
 wire \storage[5][4] ;
 wire \storage[5][5] ;
 wire \storage[5][6] ;
 wire \storage[5][7] ;
 wire \storage[5][8] ;
 wire \storage[5][9] ;
 wire \storage[6][0] ;
 wire \storage[6][10] ;
 wire \storage[6][11] ;
 wire \storage[6][12] ;
 wire \storage[6][13] ;
 wire \storage[6][14] ;
 wire \storage[6][15] ;
 wire \storage[6][1] ;
 wire \storage[6][2] ;
 wire \storage[6][3] ;
 wire \storage[6][4] ;
 wire \storage[6][5] ;
 wire \storage[6][6] ;
 wire \storage[6][7] ;
 wire \storage[6][8] ;
 wire \storage[6][9] ;
 wire \storage[7][0] ;
 wire \storage[7][10] ;
 wire \storage[7][11] ;
 wire \storage[7][12] ;
 wire \storage[7][13] ;
 wire \storage[7][14] ;
 wire \storage[7][15] ;
 wire \storage[7][1] ;
 wire \storage[7][2] ;
 wire \storage[7][3] ;
 wire \storage[7][4] ;
 wire \storage[7][5] ;
 wire \storage[7][6] ;
 wire \storage[7][7] ;
 wire \storage[7][8] ;
 wire \storage[7][9] ;
 wire \used[0] ;
 wire \used[1] ;
 wire \used[2] ;
 wire \used[3] ;
 wire \wptr[0] ;
 wire \wptr[1] ;
 wire \wptr[2] ;
 wire net3;
 wire net4;
 wire net5;
 wire net6;
 wire net7;
 wire net8;
 wire net9;
 wire net10;
 wire net11;
 wire net12;
 wire net13;
 wire net14;
 wire net15;
 wire net16;
 wire net17;
 wire net18;
 wire net19;
 wire clknet_0_clk;
 wire net50;
 wire net51;
 wire net52;
 wire net53;
 wire net54;
 wire net55;
 wire net56;
 wire net57;
 wire net58;
 wire net59;
 wire net60;
 wire net61;
 wire clknet_4_0_0_clk;
 wire clknet_4_1_0_clk;
 wire clknet_4_2_0_clk;
 wire clknet_4_3_0_clk;
 wire clknet_4_4_0_clk;
 wire clknet_4_5_0_clk;
 wire clknet_4_6_0_clk;
 wire clknet_4_7_0_clk;
 wire clknet_4_8_0_clk;
 wire clknet_4_9_0_clk;
 wire clknet_4_10_0_clk;
 wire clknet_4_11_0_clk;
 wire clknet_4_12_0_clk;
 wire clknet_4_13_0_clk;
 wire clknet_4_14_0_clk;
 wire clknet_4_15_0_clk;

 sky130_fd_sc_hd__nor2_2 _482_ (.A(\used[0] ),
    .B(\used[1] ),
    .Y(_035_));
 sky130_fd_sc_hd__inv_1 _483_ (.A(\used[2] ),
    .Y(_036_));
 sky130_fd_sc_hd__nand2_2 _484_ (.A(_041_),
    .B(net1),
    .Y(_042_));
 sky130_fd_sc_hd__o21ai_0 _485_ (.A1(_016_),
    .A2(_111_),
    .B1(_112_),
    .Y(_019_));
 sky130_fd_sc_hd__nand2_1 _486_ (.A(_014_),
    .B(\wptr[0] ),
    .Y(_113_));
 sky130_fd_sc_hd__nand2_1 _487_ (.A(_039_),
    .B(_113_),
    .Y(_018_));
 sky130_fd_sc_hd__nor2_1 _488_ (.A(_007_),
    .B(_014_),
    .Y(_114_));
 sky130_fd_sc_hd__a21oi_1 _489_ (.A1(_104_),
    .A2(_014_),
    .B1(_114_),
    .Y(_017_));
 sky130_fd_sc_hd__inv_1 _490_ (.A(\used[1] ),
    .Y(_001_));
 sky130_fd_sc_hd__inv_1 _491_ (.A(\storage[0][0] ),
    .Y(_115_));
 sky130_fd_sc_hd__nand2_1 _492_ (.A(_060_),
    .B(_115_),
    .Y(_116_));
 sky130_fd_sc_hd__inv_1 _493_ (.A(\storage[1][0] ),
    .Y(_117_));
 sky130_fd_sc_hd__nand2_1 _494_ (.A(_117_),
    .B(\rptr[0] ),
    .Y(_118_));
 sky130_fd_sc_hd__inv_2 _495_ (.A(_042_),
    .Y(_015_));
 sky130_fd_sc_hd__nand3_1 _496_ (.A(_116_),
    .B(_118_),
    .C(_070_),
    .Y(_119_));
 sky130_fd_sc_hd__inv_1 _497_ (.A(\storage[2][0] ),
    .Y(_120_));
 sky130_fd_sc_hd__nand2_1 _498_ (.A(_060_),
    .B(_120_),
    .Y(_121_));
 sky130_fd_sc_hd__inv_1 _499_ (.A(\storage[3][0] ),
    .Y(_122_));
 sky130_fd_sc_hd__nand2_1 _500_ (.A(_122_),
    .B(\rptr[0] ),
    .Y(_123_));
 sky130_fd_sc_hd__nand3_1 _501_ (.A(_121_),
    .B(_123_),
    .C(net60),
    .Y(_124_));
 sky130_fd_sc_hd__nand2_1 _502_ (.A(_119_),
    .B(_124_),
    .Y(_125_));
 sky130_fd_sc_hd__nor2_1 _503_ (.A(\rptr[2] ),
    .B(_125_),
    .Y(_126_));
 sky130_fd_sc_hd__inv_1 _504_ (.A(\storage[4][0] ),
    .Y(_127_));
 sky130_fd_sc_hd__nand2_1 _505_ (.A(_060_),
    .B(_127_),
    .Y(_128_));
 sky130_fd_sc_hd__inv_1 _507_ (.A(\storage[5][0] ),
    .Y(_129_));
 sky130_fd_sc_hd__nand2_1 _508_ (.A(_129_),
    .B(\rptr[0] ),
    .Y(_130_));
 sky130_fd_sc_hd__nand3_1 _509_ (.A(_128_),
    .B(_130_),
    .C(_070_),
    .Y(_131_));
 sky130_fd_sc_hd__inv_1 _510_ (.A(\storage[6][0] ),
    .Y(_132_));
 sky130_fd_sc_hd__nand2_1 _511_ (.A(_060_),
    .B(_132_),
    .Y(_133_));
 sky130_fd_sc_hd__inv_1 _512_ (.A(\storage[7][0] ),
    .Y(_134_));
 sky130_fd_sc_hd__nand2_1 _513_ (.A(_134_),
    .B(\rptr[0] ),
    .Y(_135_));
 sky130_fd_sc_hd__nand3_1 _514_ (.A(_133_),
    .B(_135_),
    .C(net60),
    .Y(_136_));
 sky130_fd_sc_hd__nand3_1 _515_ (.A(_131_),
    .B(_136_),
    .C(\rptr[2] ),
    .Y(_137_));
 sky130_fd_sc_hd__nand2_1 _516_ (.A(_137_),
    .B(_041_),
    .Y(_138_));
 sky130_fd_sc_hd__xnor2_1 _517_ (.A(\rptr[2] ),
    .B(_008_),
    .Y(_044_));
 sky130_fd_sc_hd__nor2_1 _518_ (.A(_126_),
    .B(_138_),
    .Y(net22));
 sky130_fd_sc_hd__inv_1 _519_ (.A(\storage[0][1] ),
    .Y(_139_));
 sky130_fd_sc_hd__nand2_1 _520_ (.A(_060_),
    .B(_139_),
    .Y(_140_));
 sky130_fd_sc_hd__inv_1 _521_ (.A(\storage[1][1] ),
    .Y(_141_));
 sky130_fd_sc_hd__nand2_1 _522_ (.A(_141_),
    .B(\rptr[0] ),
    .Y(_142_));
 sky130_fd_sc_hd__nand3_1 _523_ (.A(_140_),
    .B(_142_),
    .C(_070_),
    .Y(_143_));
 sky130_fd_sc_hd__inv_1 _525_ (.A(\storage[2][1] ),
    .Y(_145_));
 sky130_fd_sc_hd__nand2_1 _526_ (.A(_060_),
    .B(_145_),
    .Y(_146_));
 sky130_fd_sc_hd__inv_1 _527_ (.A(\storage[3][1] ),
    .Y(_147_));
 sky130_fd_sc_hd__nand2_1 _530_ (.A(_147_),
    .B(\rptr[0] ),
    .Y(_149_));
 sky130_fd_sc_hd__nand3_1 _531_ (.A(_146_),
    .B(_149_),
    .C(net60),
    .Y(_150_));
 sky130_fd_sc_hd__nand2_1 _532_ (.A(_143_),
    .B(_150_),
    .Y(_151_));
 sky130_fd_sc_hd__nor2_1 _533_ (.A(\rptr[2] ),
    .B(_151_),
    .Y(_152_));
 sky130_fd_sc_hd__inv_1 _534_ (.A(\storage[4][1] ),
    .Y(_153_));
 sky130_fd_sc_hd__nand2_1 _535_ (.A(_060_),
    .B(_153_),
    .Y(_154_));
 sky130_fd_sc_hd__inv_1 _536_ (.A(\storage[5][1] ),
    .Y(_155_));
 sky130_fd_sc_hd__nand2_1 _537_ (.A(_155_),
    .B(\rptr[0] ),
    .Y(_156_));
 sky130_fd_sc_hd__nand3_1 _538_ (.A(_154_),
    .B(_156_),
    .C(_070_),
    .Y(_157_));
 sky130_fd_sc_hd__nand2_1 _539_ (.A(_042_),
    .B(\rptr[2] ),
    .Y(_046_));
 sky130_fd_sc_hd__inv_1 _540_ (.A(\storage[6][1] ),
    .Y(_158_));
 sky130_fd_sc_hd__nand2_1 _541_ (.A(_060_),
    .B(_158_),
    .Y(_159_));
 sky130_fd_sc_hd__inv_1 _542_ (.A(\storage[7][1] ),
    .Y(_160_));
 sky130_fd_sc_hd__nand2_1 _543_ (.A(_160_),
    .B(\rptr[0] ),
    .Y(_161_));
 sky130_fd_sc_hd__nand3_1 _544_ (.A(_159_),
    .B(_161_),
    .C(net60),
    .Y(_162_));
 sky130_fd_sc_hd__nand3_1 _545_ (.A(_157_),
    .B(_162_),
    .C(\rptr[2] ),
    .Y(_163_));
 sky130_fd_sc_hd__nand2_1 _546_ (.A(_163_),
    .B(_041_),
    .Y(_164_));
 sky130_fd_sc_hd__nor2_1 _547_ (.A(_152_),
    .B(_164_),
    .Y(net29));
 sky130_fd_sc_hd__inv_1 _549_ (.A(\storage[0][2] ),
    .Y(_166_));
 sky130_fd_sc_hd__o21ai_0 _550_ (.A1(_044_),
    .A2(_042_),
    .B1(_046_),
    .Y(_026_));
 sky130_fd_sc_hd__nand2_1 _551_ (.A(_060_),
    .B(_166_),
    .Y(_167_));
 sky130_fd_sc_hd__inv_1 _552_ (.A(\storage[1][2] ),
    .Y(_168_));
 sky130_fd_sc_hd__nand2_1 _553_ (.A(_168_),
    .B(\rptr[0] ),
    .Y(_169_));
 sky130_fd_sc_hd__nand3_1 _555_ (.A(_167_),
    .B(_169_),
    .C(_070_),
    .Y(_171_));
 sky130_fd_sc_hd__inv_1 _556_ (.A(\storage[2][2] ),
    .Y(_172_));
 sky130_fd_sc_hd__nand2_1 _557_ (.A(_060_),
    .B(_172_),
    .Y(_173_));
 sky130_fd_sc_hd__inv_1 _558_ (.A(\storage[3][2] ),
    .Y(_174_));
 sky130_fd_sc_hd__nand2_1 _559_ (.A(_174_),
    .B(\rptr[0] ),
    .Y(_175_));
 sky130_fd_sc_hd__nand3_1 _560_ (.A(_173_),
    .B(_175_),
    .C(net60),
    .Y(_176_));
 sky130_fd_sc_hd__a21oi_1 _561_ (.A1(_013_),
    .A2(_010_),
    .B1(_012_),
    .Y(_047_));
 sky130_fd_sc_hd__nand2_1 _562_ (.A(_171_),
    .B(_176_),
    .Y(_177_));
 sky130_fd_sc_hd__nor2_1 _563_ (.A(\rptr[2] ),
    .B(_177_),
    .Y(_178_));
 sky130_fd_sc_hd__inv_1 _564_ (.A(\storage[4][2] ),
    .Y(_179_));
 sky130_fd_sc_hd__nand2_1 _565_ (.A(_060_),
    .B(_179_),
    .Y(_180_));
 sky130_fd_sc_hd__inv_1 _566_ (.A(\storage[5][2] ),
    .Y(_181_));
 sky130_fd_sc_hd__nand2_1 _567_ (.A(_181_),
    .B(\rptr[0] ),
    .Y(_182_));
 sky130_fd_sc_hd__nand3_1 _568_ (.A(_180_),
    .B(_182_),
    .C(_070_),
    .Y(_183_));
 sky130_fd_sc_hd__inv_1 _569_ (.A(\storage[6][2] ),
    .Y(_184_));
 sky130_fd_sc_hd__nand2_1 _570_ (.A(_060_),
    .B(_184_),
    .Y(_185_));
 sky130_fd_sc_hd__inv_1 _571_ (.A(\storage[7][2] ),
    .Y(_186_));
 sky130_fd_sc_hd__nand3_1 _572_ (.A(_013_),
    .B(_011_),
    .C(\used[0] ),
    .Y(_048_));
 sky130_fd_sc_hd__nand2_1 _573_ (.A(_186_),
    .B(\rptr[0] ),
    .Y(_187_));
 sky130_fd_sc_hd__nand3_1 _574_ (.A(_185_),
    .B(_187_),
    .C(net60),
    .Y(_188_));
 sky130_fd_sc_hd__nand3_1 _576_ (.A(_183_),
    .B(_188_),
    .C(\rptr[2] ),
    .Y(_190_));
 sky130_fd_sc_hd__nand2_1 _577_ (.A(_190_),
    .B(_041_),
    .Y(_191_));
 sky130_fd_sc_hd__nor2_1 _578_ (.A(_178_),
    .B(_191_),
    .Y(net30));
 sky130_fd_sc_hd__inv_1 _579_ (.A(\storage[0][3] ),
    .Y(_192_));
 sky130_fd_sc_hd__nand2_1 _580_ (.A(_060_),
    .B(_192_),
    .Y(_193_));
 sky130_fd_sc_hd__inv_1 _581_ (.A(\storage[1][3] ),
    .Y(_194_));
 sky130_fd_sc_hd__nand2_1 _583_ (.A(_047_),
    .B(_048_),
    .Y(_049_));
 sky130_fd_sc_hd__nand2_1 _584_ (.A(_194_),
    .B(\rptr[0] ),
    .Y(_196_));
 sky130_fd_sc_hd__nand3_1 _585_ (.A(_193_),
    .B(_196_),
    .C(_070_),
    .Y(_197_));
 sky130_fd_sc_hd__inv_1 _586_ (.A(\storage[2][3] ),
    .Y(_198_));
 sky130_fd_sc_hd__nand2_1 _587_ (.A(_060_),
    .B(_198_),
    .Y(_199_));
 sky130_fd_sc_hd__inv_1 _588_ (.A(\storage[3][3] ),
    .Y(_200_));
 sky130_fd_sc_hd__nand2_1 _589_ (.A(_200_),
    .B(\rptr[0] ),
    .Y(_201_));
 sky130_fd_sc_hd__nand3_1 _591_ (.A(_199_),
    .B(_201_),
    .C(net60),
    .Y(_203_));
 sky130_fd_sc_hd__nand2_1 _592_ (.A(_197_),
    .B(_203_),
    .Y(_204_));
 sky130_fd_sc_hd__nor2_1 _593_ (.A(\rptr[2] ),
    .B(_204_),
    .Y(_205_));
 sky130_fd_sc_hd__nand3_2 _594_ (.A(_035_),
    .B(\used[3] ),
    .C(_036_),
    .Y(_037_));
 sky130_fd_sc_hd__inv_1 _595_ (.A(_005_),
    .Y(_002_));
 sky130_fd_sc_hd__inv_1 _596_ (.A(\storage[4][3] ),
    .Y(_206_));
 sky130_fd_sc_hd__nand2_1 _597_ (.A(_060_),
    .B(_206_),
    .Y(_207_));
 sky130_fd_sc_hd__inv_1 _598_ (.A(\storage[5][3] ),
    .Y(_208_));
 sky130_fd_sc_hd__nand2_1 _599_ (.A(_208_),
    .B(\rptr[0] ),
    .Y(_209_));
 sky130_fd_sc_hd__nand3_1 _600_ (.A(_207_),
    .B(_209_),
    .C(_070_),
    .Y(_210_));
 sky130_fd_sc_hd__inv_1 _601_ (.A(\storage[6][3] ),
    .Y(_211_));
 sky130_fd_sc_hd__nand2_1 _602_ (.A(_060_),
    .B(_211_),
    .Y(_212_));
 sky130_fd_sc_hd__inv_1 _603_ (.A(\storage[7][3] ),
    .Y(_213_));
 sky130_fd_sc_hd__nand2_1 _604_ (.A(_213_),
    .B(\rptr[0] ),
    .Y(_214_));
 sky130_fd_sc_hd__nand3_1 _605_ (.A(_212_),
    .B(_214_),
    .C(net60),
    .Y(_215_));
 sky130_fd_sc_hd__nand2_1 _606_ (.A(_040_),
    .B(_002_),
    .Y(_050_));
 sky130_fd_sc_hd__nand3_1 _607_ (.A(_210_),
    .B(_215_),
    .C(\rptr[2] ),
    .Y(_216_));
 sky130_fd_sc_hd__nand2_1 _608_ (.A(_216_),
    .B(_041_),
    .Y(_217_));
 sky130_fd_sc_hd__nor2_1 _609_ (.A(_205_),
    .B(_217_),
    .Y(net31));
 sky130_fd_sc_hd__inv_1 _610_ (.A(\storage[0][4] ),
    .Y(_218_));
 sky130_fd_sc_hd__nand2_1 _611_ (.A(_060_),
    .B(_218_),
    .Y(_219_));
 sky130_fd_sc_hd__inv_1 _612_ (.A(\storage[1][4] ),
    .Y(_220_));
 sky130_fd_sc_hd__nand2_1 _613_ (.A(_220_),
    .B(\rptr[0] ),
    .Y(_221_));
 sky130_fd_sc_hd__nand3_1 _614_ (.A(_219_),
    .B(_221_),
    .C(_070_),
    .Y(_222_));
 sky130_fd_sc_hd__inv_1 _615_ (.A(\storage[2][4] ),
    .Y(_223_));
 sky130_fd_sc_hd__nand2_1 _616_ (.A(_060_),
    .B(_223_),
    .Y(_224_));
 sky130_fd_sc_hd__nand2_1 _617_ (.A(\used[3] ),
    .B(_005_),
    .Y(_051_));
 sky130_fd_sc_hd__inv_1 _618_ (.A(\storage[3][4] ),
    .Y(_225_));
 sky130_fd_sc_hd__nand2_1 _619_ (.A(_225_),
    .B(\rptr[0] ),
    .Y(_226_));
 sky130_fd_sc_hd__nand3_1 _620_ (.A(_224_),
    .B(_226_),
    .C(net60),
    .Y(_227_));
 sky130_fd_sc_hd__nand2_1 _621_ (.A(_222_),
    .B(_227_),
    .Y(_228_));
 sky130_fd_sc_hd__nor2_1 _622_ (.A(\rptr[2] ),
    .B(_228_),
    .Y(_229_));
 sky130_fd_sc_hd__inv_1 _623_ (.A(\storage[4][4] ),
    .Y(_230_));
 sky130_fd_sc_hd__nand2_1 _624_ (.A(_060_),
    .B(_230_),
    .Y(_231_));
 sky130_fd_sc_hd__inv_1 _625_ (.A(\storage[5][4] ),
    .Y(_232_));
 sky130_fd_sc_hd__nand2_1 _626_ (.A(_232_),
    .B(\rptr[0] ),
    .Y(_233_));
 sky130_fd_sc_hd__nand3_1 _627_ (.A(_231_),
    .B(_233_),
    .C(_070_),
    .Y(_234_));
 sky130_fd_sc_hd__nand2_1 _628_ (.A(_050_),
    .B(_051_),
    .Y(_052_));
 sky130_fd_sc_hd__inv_1 _629_ (.A(\storage[6][4] ),
    .Y(_235_));
 sky130_fd_sc_hd__nand2_1 _630_ (.A(_060_),
    .B(_235_),
    .Y(_236_));
 sky130_fd_sc_hd__inv_1 _631_ (.A(\storage[7][4] ),
    .Y(_237_));
 sky130_fd_sc_hd__nand2_1 _632_ (.A(_237_),
    .B(\rptr[0] ),
    .Y(_238_));
 sky130_fd_sc_hd__nand3_1 _633_ (.A(_236_),
    .B(_238_),
    .C(net60),
    .Y(_239_));
 sky130_fd_sc_hd__nand3_1 _634_ (.A(_234_),
    .B(_239_),
    .C(\rptr[2] ),
    .Y(_240_));
 sky130_fd_sc_hd__nand2_1 _635_ (.A(_240_),
    .B(_041_),
    .Y(_241_));
 sky130_fd_sc_hd__nor2_1 _636_ (.A(_229_),
    .B(_241_),
    .Y(net32));
 sky130_fd_sc_hd__inv_1 _637_ (.A(\storage[0][5] ),
    .Y(_242_));
 sky130_fd_sc_hd__nand2_1 _638_ (.A(net58),
    .B(_242_),
    .Y(_243_));
 sky130_fd_sc_hd__inv_1 _639_ (.A(_052_),
    .Y(_053_));
 sky130_fd_sc_hd__inv_1 _640_ (.A(\storage[1][5] ),
    .Y(_244_));
 sky130_fd_sc_hd__nand2_1 _641_ (.A(_244_),
    .B(net61),
    .Y(_245_));
 sky130_fd_sc_hd__nand3_1 _642_ (.A(_243_),
    .B(_245_),
    .C(_070_),
    .Y(_246_));
 sky130_fd_sc_hd__inv_1 _643_ (.A(\storage[2][5] ),
    .Y(_247_));
 sky130_fd_sc_hd__nand2_1 _644_ (.A(net58),
    .B(_247_),
    .Y(_248_));
 sky130_fd_sc_hd__inv_1 _645_ (.A(\storage[3][5] ),
    .Y(_249_));
 sky130_fd_sc_hd__nand2_1 _646_ (.A(_249_),
    .B(net61),
    .Y(_250_));
 sky130_fd_sc_hd__nand3_1 _647_ (.A(_248_),
    .B(_250_),
    .C(net60),
    .Y(_251_));
 sky130_fd_sc_hd__nand2_1 _648_ (.A(_246_),
    .B(_251_),
    .Y(_252_));
 sky130_fd_sc_hd__nor2_1 _649_ (.A(net59),
    .B(_252_),
    .Y(_253_));
 sky130_fd_sc_hd__nand2_1 _650_ (.A(_049_),
    .B(_053_),
    .Y(_054_));
 sky130_fd_sc_hd__inv_1 _651_ (.A(\storage[4][5] ),
    .Y(_254_));
 sky130_fd_sc_hd__nand2_1 _652_ (.A(net58),
    .B(_254_),
    .Y(_255_));
 sky130_fd_sc_hd__inv_1 _653_ (.A(\storage[5][5] ),
    .Y(_256_));
 sky130_fd_sc_hd__nand2_1 _654_ (.A(_256_),
    .B(net61),
    .Y(_257_));
 sky130_fd_sc_hd__nand3_1 _655_ (.A(_255_),
    .B(_257_),
    .C(_070_),
    .Y(_258_));
 sky130_fd_sc_hd__inv_1 _656_ (.A(\storage[6][5] ),
    .Y(_259_));
 sky130_fd_sc_hd__nand2_1 _657_ (.A(net58),
    .B(_259_),
    .Y(_260_));
 sky130_fd_sc_hd__inv_1 _658_ (.A(\storage[7][5] ),
    .Y(_261_));
 sky130_fd_sc_hd__nand2_1 _659_ (.A(_261_),
    .B(net61),
    .Y(_262_));
 sky130_fd_sc_hd__nand3_1 _660_ (.A(_260_),
    .B(_262_),
    .C(net60),
    .Y(_263_));
 sky130_fd_sc_hd__nand3_1 _661_ (.A(_052_),
    .B(_047_),
    .C(_048_),
    .Y(_055_));
 sky130_fd_sc_hd__nand3_1 _662_ (.A(_258_),
    .B(_263_),
    .C(net59),
    .Y(_264_));
 sky130_fd_sc_hd__nand2_1 _663_ (.A(_264_),
    .B(_041_),
    .Y(_265_));
 sky130_fd_sc_hd__nor2_1 _664_ (.A(_253_),
    .B(_265_),
    .Y(net33));
 sky130_fd_sc_hd__inv_1 _665_ (.A(\storage[0][6] ),
    .Y(_266_));
 sky130_fd_sc_hd__nand2_1 _666_ (.A(net58),
    .B(_266_),
    .Y(_267_));
 sky130_fd_sc_hd__inv_1 _667_ (.A(\storage[1][6] ),
    .Y(_268_));
 sky130_fd_sc_hd__nand2_1 _668_ (.A(_268_),
    .B(net61),
    .Y(_269_));
 sky130_fd_sc_hd__nand3_1 _669_ (.A(_267_),
    .B(_269_),
    .C(_070_),
    .Y(_270_));
 sky130_fd_sc_hd__inv_1 _670_ (.A(\storage[2][6] ),
    .Y(_271_));
 sky130_fd_sc_hd__nand2_1 _671_ (.A(net58),
    .B(_271_),
    .Y(_272_));
 sky130_fd_sc_hd__nand3b_1 _672_ (.A_N(_016_),
    .B(_054_),
    .C(_055_),
    .Y(_056_));
 sky130_fd_sc_hd__inv_1 _673_ (.A(\storage[3][6] ),
    .Y(_273_));
 sky130_fd_sc_hd__nand2_1 _674_ (.A(_273_),
    .B(net61),
    .Y(_274_));
 sky130_fd_sc_hd__nand3_1 _675_ (.A(_272_),
    .B(_274_),
    .C(net60),
    .Y(_275_));
 sky130_fd_sc_hd__nand2_1 _676_ (.A(_270_),
    .B(_275_),
    .Y(_276_));
 sky130_fd_sc_hd__nor2_1 _677_ (.A(net59),
    .B(_276_),
    .Y(_277_));
 sky130_fd_sc_hd__inv_1 _678_ (.A(\storage[4][6] ),
    .Y(_278_));
 sky130_fd_sc_hd__nand2_1 _679_ (.A(net58),
    .B(_278_),
    .Y(_279_));
 sky130_fd_sc_hd__inv_1 _680_ (.A(\storage[5][6] ),
    .Y(_280_));
 sky130_fd_sc_hd__nand2_1 _681_ (.A(_280_),
    .B(net61),
    .Y(_281_));
 sky130_fd_sc_hd__nand3_1 _682_ (.A(_279_),
    .B(_281_),
    .C(_070_),
    .Y(_282_));
 sky130_fd_sc_hd__nand2_1 _683_ (.A(\used[3] ),
    .B(_016_),
    .Y(_057_));
 sky130_fd_sc_hd__inv_1 _684_ (.A(\storage[6][6] ),
    .Y(_283_));
 sky130_fd_sc_hd__nand2_1 _685_ (.A(_283_),
    .B(net58),
    .Y(_284_));
 sky130_fd_sc_hd__inv_1 _686_ (.A(\storage[7][6] ),
    .Y(_285_));
 sky130_fd_sc_hd__nand2_1 _687_ (.A(_285_),
    .B(net61),
    .Y(_286_));
 sky130_fd_sc_hd__nand3_1 _688_ (.A(_284_),
    .B(_286_),
    .C(net60),
    .Y(_287_));
 sky130_fd_sc_hd__nand3_1 _689_ (.A(_282_),
    .B(_287_),
    .C(net59),
    .Y(_288_));
 sky130_fd_sc_hd__nand2_1 _690_ (.A(_288_),
    .B(_041_),
    .Y(_289_));
 sky130_fd_sc_hd__nor2_1 _691_ (.A(_277_),
    .B(_289_),
    .Y(net34));
 sky130_fd_sc_hd__inv_1 _692_ (.A(\storage[0][7] ),
    .Y(_290_));
 sky130_fd_sc_hd__nand2_1 _693_ (.A(net58),
    .B(_290_),
    .Y(_291_));
 sky130_fd_sc_hd__nand2_1 _694_ (.A(_056_),
    .B(_057_),
    .Y(_025_));
 sky130_fd_sc_hd__inv_1 _695_ (.A(\storage[1][7] ),
    .Y(_292_));
 sky130_fd_sc_hd__nand2_1 _696_ (.A(_292_),
    .B(net61),
    .Y(_293_));
 sky130_fd_sc_hd__nand3_1 _697_ (.A(_291_),
    .B(_293_),
    .C(_070_),
    .Y(_294_));
 sky130_fd_sc_hd__inv_1 _698_ (.A(\storage[2][7] ),
    .Y(_295_));
 sky130_fd_sc_hd__nand2_1 _699_ (.A(net58),
    .B(_295_),
    .Y(_296_));
 sky130_fd_sc_hd__inv_1 _700_ (.A(\storage[3][7] ),
    .Y(_297_));
 sky130_fd_sc_hd__nand2_1 _701_ (.A(_297_),
    .B(net61),
    .Y(_298_));
 sky130_fd_sc_hd__nand3_1 _702_ (.A(_296_),
    .B(_298_),
    .C(net60),
    .Y(_299_));
 sky130_fd_sc_hd__nand2_1 _703_ (.A(_294_),
    .B(_299_),
    .Y(_300_));
 sky130_fd_sc_hd__nor2_1 _704_ (.A(net59),
    .B(_300_),
    .Y(_301_));
 sky130_fd_sc_hd__inv_1 _705_ (.A(_037_),
    .Y(net21));
 sky130_fd_sc_hd__xnor2_1 _706_ (.A(\wptr[2] ),
    .B(_006_),
    .Y(_058_));
 sky130_fd_sc_hd__inv_1 _707_ (.A(\storage[4][7] ),
    .Y(_302_));
 sky130_fd_sc_hd__nand2_1 _708_ (.A(net58),
    .B(_302_),
    .Y(_303_));
 sky130_fd_sc_hd__inv_1 _709_ (.A(\storage[5][7] ),
    .Y(_304_));
 sky130_fd_sc_hd__nand2_1 _710_ (.A(_304_),
    .B(net61),
    .Y(_305_));
 sky130_fd_sc_hd__nand3_1 _711_ (.A(_303_),
    .B(_305_),
    .C(_070_),
    .Y(_306_));
 sky130_fd_sc_hd__inv_1 _712_ (.A(\storage[6][7] ),
    .Y(_307_));
 sky130_fd_sc_hd__nand2_1 _713_ (.A(net58),
    .B(_307_),
    .Y(_308_));
 sky130_fd_sc_hd__inv_1 _714_ (.A(\storage[7][7] ),
    .Y(_309_));
 sky130_fd_sc_hd__nand2_1 _715_ (.A(_309_),
    .B(net61),
    .Y(_310_));
 sky130_fd_sc_hd__nand3_1 _716_ (.A(_308_),
    .B(_310_),
    .C(net60),
    .Y(_311_));
 sky130_fd_sc_hd__nand2_1 _717_ (.A(_014_),
    .B(\wptr[2] ),
    .Y(_059_));
 sky130_fd_sc_hd__nand3_1 _718_ (.A(_306_),
    .B(_311_),
    .C(net59),
    .Y(_312_));
 sky130_fd_sc_hd__nand2_1 _719_ (.A(_312_),
    .B(_041_),
    .Y(_313_));
 sky130_fd_sc_hd__nor2_1 _720_ (.A(_301_),
    .B(_313_),
    .Y(net35));
 sky130_fd_sc_hd__inv_1 _721_ (.A(\storage[0][8] ),
    .Y(_314_));
 sky130_fd_sc_hd__nand2_1 _722_ (.A(net58),
    .B(_314_),
    .Y(_315_));
 sky130_fd_sc_hd__inv_1 _723_ (.A(\storage[1][8] ),
    .Y(_316_));
 sky130_fd_sc_hd__nand2_1 _724_ (.A(_316_),
    .B(net61),
    .Y(_317_));
 sky130_fd_sc_hd__nand3_1 _725_ (.A(_315_),
    .B(_317_),
    .C(_070_),
    .Y(_318_));
 sky130_fd_sc_hd__inv_1 _726_ (.A(\storage[2][8] ),
    .Y(_319_));
 sky130_fd_sc_hd__nand2_1 _727_ (.A(net58),
    .B(_319_),
    .Y(_320_));
 sky130_fd_sc_hd__o21ai_0 _728_ (.A1(_058_),
    .A2(_014_),
    .B1(_059_),
    .Y(_024_));
 sky130_fd_sc_hd__inv_1 _729_ (.A(\storage[3][8] ),
    .Y(_321_));
 sky130_fd_sc_hd__nand2_1 _730_ (.A(_321_),
    .B(net61),
    .Y(_322_));
 sky130_fd_sc_hd__nand3_1 _731_ (.A(_320_),
    .B(_322_),
    .C(net60),
    .Y(_323_));
 sky130_fd_sc_hd__nand2_1 _732_ (.A(_318_),
    .B(_323_),
    .Y(_324_));
 sky130_fd_sc_hd__nor2_1 _733_ (.A(net59),
    .B(_324_),
    .Y(_325_));
 sky130_fd_sc_hd__inv_1 _734_ (.A(\storage[4][8] ),
    .Y(_326_));
 sky130_fd_sc_hd__nand2_1 _735_ (.A(net58),
    .B(_326_),
    .Y(_327_));
 sky130_fd_sc_hd__inv_1 _736_ (.A(\storage[5][8] ),
    .Y(_328_));
 sky130_fd_sc_hd__nand2_1 _737_ (.A(_328_),
    .B(net61),
    .Y(_329_));
 sky130_fd_sc_hd__nand3_1 _738_ (.A(_327_),
    .B(_329_),
    .C(_070_),
    .Y(_330_));
 sky130_fd_sc_hd__inv_2 _739_ (.A(\rptr[0] ),
    .Y(_060_));
 sky130_fd_sc_hd__inv_1 _740_ (.A(\storage[6][8] ),
    .Y(_331_));
 sky130_fd_sc_hd__nand2_1 _741_ (.A(net58),
    .B(_331_),
    .Y(_332_));
 sky130_fd_sc_hd__inv_1 _742_ (.A(\storage[7][8] ),
    .Y(_333_));
 sky130_fd_sc_hd__nand2_1 _743_ (.A(_333_),
    .B(net61),
    .Y(_334_));
 sky130_fd_sc_hd__nand3_1 _744_ (.A(_332_),
    .B(_334_),
    .C(net60),
    .Y(_335_));
 sky130_fd_sc_hd__nand3_1 _745_ (.A(_330_),
    .B(_335_),
    .C(net59),
    .Y(_336_));
 sky130_fd_sc_hd__nand2_1 _746_ (.A(_336_),
    .B(_041_),
    .Y(_337_));
 sky130_fd_sc_hd__nor2_1 _747_ (.A(_325_),
    .B(_337_),
    .Y(net36));
 sky130_fd_sc_hd__inv_1 _748_ (.A(\storage[0][9] ),
    .Y(_338_));
 sky130_fd_sc_hd__nand2_1 _749_ (.A(net58),
    .B(_338_),
    .Y(_339_));
 sky130_fd_sc_hd__inv_1 _751_ (.A(\storage[1][9] ),
    .Y(_340_));
 sky130_fd_sc_hd__nand2_1 _752_ (.A(_340_),
    .B(net61),
    .Y(_341_));
 sky130_fd_sc_hd__nand3_1 _753_ (.A(_339_),
    .B(_341_),
    .C(_070_),
    .Y(_342_));
 sky130_fd_sc_hd__inv_1 _754_ (.A(\storage[2][9] ),
    .Y(_343_));
 sky130_fd_sc_hd__nand2_1 _755_ (.A(net58),
    .B(_343_),
    .Y(_344_));
 sky130_fd_sc_hd__inv_1 _756_ (.A(\storage[3][9] ),
    .Y(_345_));
 sky130_fd_sc_hd__nand2_1 _757_ (.A(_345_),
    .B(net61),
    .Y(_346_));
 sky130_fd_sc_hd__nand3_1 _758_ (.A(_344_),
    .B(_346_),
    .C(net60),
    .Y(_347_));
 sky130_fd_sc_hd__nand2_1 _759_ (.A(_342_),
    .B(_347_),
    .Y(_348_));
 sky130_fd_sc_hd__nor2_1 _760_ (.A(net59),
    .B(_348_),
    .Y(_349_));
 sky130_fd_sc_hd__inv_1 _762_ (.A(\storage[4][9] ),
    .Y(_350_));
 sky130_fd_sc_hd__nand2_1 _763_ (.A(net58),
    .B(_350_),
    .Y(_351_));
 sky130_fd_sc_hd__inv_1 _764_ (.A(\storage[5][9] ),
    .Y(_352_));
 sky130_fd_sc_hd__nand2_1 _765_ (.A(_352_),
    .B(net61),
    .Y(_353_));
 sky130_fd_sc_hd__nand3_1 _766_ (.A(_351_),
    .B(_353_),
    .C(_070_),
    .Y(_354_));
 sky130_fd_sc_hd__inv_1 _767_ (.A(\storage[6][9] ),
    .Y(_355_));
 sky130_fd_sc_hd__nand2_1 _768_ (.A(net58),
    .B(_355_),
    .Y(_356_));
 sky130_fd_sc_hd__inv_1 _769_ (.A(\storage[7][9] ),
    .Y(_357_));
 sky130_fd_sc_hd__nand2_1 _770_ (.A(_357_),
    .B(net61),
    .Y(_358_));
 sky130_fd_sc_hd__nand3_1 _771_ (.A(_356_),
    .B(_358_),
    .C(net60),
    .Y(_359_));
 sky130_fd_sc_hd__inv_1 _772_ (.A(\storage[0][15] ),
    .Y(_063_));
 sky130_fd_sc_hd__nand3_1 _773_ (.A(_354_),
    .B(_359_),
    .C(net59),
    .Y(_360_));
 sky130_fd_sc_hd__nand2_1 _774_ (.A(_360_),
    .B(_041_),
    .Y(_361_));
 sky130_fd_sc_hd__nor2_1 _775_ (.A(_349_),
    .B(_361_),
    .Y(net37));
 sky130_fd_sc_hd__inv_1 _776_ (.A(\storage[0][10] ),
    .Y(_362_));
 sky130_fd_sc_hd__nand2_1 _777_ (.A(net58),
    .B(_362_),
    .Y(_363_));
 sky130_fd_sc_hd__inv_1 _778_ (.A(\storage[1][10] ),
    .Y(_364_));
 sky130_fd_sc_hd__nand2_1 _779_ (.A(_364_),
    .B(net61),
    .Y(_365_));
 sky130_fd_sc_hd__nand3_1 _780_ (.A(_363_),
    .B(_365_),
    .C(_070_),
    .Y(_366_));
 sky130_fd_sc_hd__inv_1 _781_ (.A(\storage[2][10] ),
    .Y(_367_));
 sky130_fd_sc_hd__nand2_1 _782_ (.A(net58),
    .B(_367_),
    .Y(_368_));
 sky130_fd_sc_hd__nand2_1 _783_ (.A(_060_),
    .B(_063_),
    .Y(_064_));
 sky130_fd_sc_hd__inv_1 _784_ (.A(\storage[3][10] ),
    .Y(_369_));
 sky130_fd_sc_hd__nand2_1 _785_ (.A(_369_),
    .B(net61),
    .Y(_370_));
 sky130_fd_sc_hd__nand3_1 _786_ (.A(_368_),
    .B(_370_),
    .C(net60),
    .Y(_371_));
 sky130_fd_sc_hd__nand2_1 _787_ (.A(_366_),
    .B(_371_),
    .Y(_372_));
 sky130_fd_sc_hd__nor2_1 _788_ (.A(net59),
    .B(_372_),
    .Y(_373_));
 sky130_fd_sc_hd__inv_1 _789_ (.A(\storage[4][10] ),
    .Y(_374_));
 sky130_fd_sc_hd__nand2_1 _790_ (.A(net58),
    .B(_374_),
    .Y(_375_));
 sky130_fd_sc_hd__inv_1 _791_ (.A(\storage[5][10] ),
    .Y(_376_));
 sky130_fd_sc_hd__nand2_1 _792_ (.A(_376_),
    .B(net61),
    .Y(_377_));
 sky130_fd_sc_hd__nand3_1 _793_ (.A(_375_),
    .B(_377_),
    .C(_070_),
    .Y(_378_));
 sky130_fd_sc_hd__inv_1 _794_ (.A(\storage[1][15] ),
    .Y(_065_));
 sky130_fd_sc_hd__inv_1 _795_ (.A(\storage[6][10] ),
    .Y(_379_));
 sky130_fd_sc_hd__nand2_1 _796_ (.A(net58),
    .B(_379_),
    .Y(_380_));
 sky130_fd_sc_hd__inv_1 _797_ (.A(\storage[7][10] ),
    .Y(_381_));
 sky130_fd_sc_hd__nand2_1 _798_ (.A(_381_),
    .B(net61),
    .Y(_382_));
 sky130_fd_sc_hd__nand3_1 _799_ (.A(_380_),
    .B(_382_),
    .C(net60),
    .Y(_383_));
 sky130_fd_sc_hd__nand3_1 _800_ (.A(_378_),
    .B(_383_),
    .C(net59),
    .Y(_384_));
 sky130_fd_sc_hd__nand2_1 _801_ (.A(_384_),
    .B(_041_),
    .Y(_385_));
 sky130_fd_sc_hd__nor2_1 _802_ (.A(_373_),
    .B(_385_),
    .Y(net23));
 sky130_fd_sc_hd__inv_1 _803_ (.A(\storage[0][11] ),
    .Y(_386_));
 sky130_fd_sc_hd__nand2_1 _804_ (.A(net58),
    .B(_386_),
    .Y(_387_));
 sky130_fd_sc_hd__inv_1 _806_ (.A(\storage[1][11] ),
    .Y(_388_));
 sky130_fd_sc_hd__nand2_1 _807_ (.A(_388_),
    .B(net61),
    .Y(_389_));
 sky130_fd_sc_hd__nand3_1 _808_ (.A(_387_),
    .B(_389_),
    .C(_070_),
    .Y(_390_));
 sky130_fd_sc_hd__inv_1 _809_ (.A(\storage[2][11] ),
    .Y(_391_));
 sky130_fd_sc_hd__nand2_1 _810_ (.A(net58),
    .B(_391_),
    .Y(_392_));
 sky130_fd_sc_hd__inv_1 _811_ (.A(\storage[3][11] ),
    .Y(_393_));
 sky130_fd_sc_hd__nand2_1 _812_ (.A(_393_),
    .B(net61),
    .Y(_394_));
 sky130_fd_sc_hd__nand3_1 _813_ (.A(_392_),
    .B(_394_),
    .C(net60),
    .Y(_395_));
 sky130_fd_sc_hd__nand2_1 _814_ (.A(_390_),
    .B(_395_),
    .Y(_396_));
 sky130_fd_sc_hd__nor2_1 _815_ (.A(net59),
    .B(_396_),
    .Y(_397_));
 sky130_fd_sc_hd__nand3_1 _816_ (.A(\wptr[2] ),
    .B(net2),
    .C(\wptr[1] ),
    .Y(_038_));
 sky130_fd_sc_hd__inv_1 _818_ (.A(\storage[4][11] ),
    .Y(_398_));
 sky130_fd_sc_hd__nand2_1 _819_ (.A(net58),
    .B(_398_),
    .Y(_399_));
 sky130_fd_sc_hd__inv_1 _820_ (.A(\storage[5][11] ),
    .Y(_400_));
 sky130_fd_sc_hd__nand2_1 _821_ (.A(_400_),
    .B(net61),
    .Y(_401_));
 sky130_fd_sc_hd__nand3_1 _822_ (.A(_399_),
    .B(_401_),
    .C(_070_),
    .Y(_402_));
 sky130_fd_sc_hd__inv_1 _823_ (.A(\storage[6][11] ),
    .Y(_403_));
 sky130_fd_sc_hd__nand2_1 _824_ (.A(net58),
    .B(_403_),
    .Y(_404_));
 sky130_fd_sc_hd__inv_1 _825_ (.A(\storage[7][11] ),
    .Y(_405_));
 sky130_fd_sc_hd__nand2_1 _826_ (.A(_405_),
    .B(net61),
    .Y(_406_));
 sky130_fd_sc_hd__nand3_1 _827_ (.A(_404_),
    .B(_406_),
    .C(net60),
    .Y(_407_));
 sky130_fd_sc_hd__nand2_1 _828_ (.A(_065_),
    .B(\rptr[0] ),
    .Y(_068_));
 sky130_fd_sc_hd__nand3_1 _829_ (.A(_402_),
    .B(_407_),
    .C(net59),
    .Y(_408_));
 sky130_fd_sc_hd__nand2_1 _830_ (.A(_408_),
    .B(_041_),
    .Y(_409_));
 sky130_fd_sc_hd__nor2_1 _831_ (.A(_397_),
    .B(_409_),
    .Y(net24));
 sky130_fd_sc_hd__inv_1 _832_ (.A(\storage[0][12] ),
    .Y(_410_));
 sky130_fd_sc_hd__nand2_1 _833_ (.A(net58),
    .B(_410_),
    .Y(_411_));
 sky130_fd_sc_hd__inv_1 _834_ (.A(\storage[1][12] ),
    .Y(_412_));
 sky130_fd_sc_hd__nand2_1 _835_ (.A(_412_),
    .B(net61),
    .Y(_413_));
 sky130_fd_sc_hd__nand3_1 _836_ (.A(_411_),
    .B(_413_),
    .C(_070_),
    .Y(_414_));
 sky130_fd_sc_hd__inv_1 _837_ (.A(\storage[2][12] ),
    .Y(_415_));
 sky130_fd_sc_hd__nand2_1 _838_ (.A(net58),
    .B(_415_),
    .Y(_416_));
 sky130_fd_sc_hd__inv_1 _840_ (.A(\storage[3][12] ),
    .Y(_417_));
 sky130_fd_sc_hd__nand2_1 _841_ (.A(_417_),
    .B(net61),
    .Y(_418_));
 sky130_fd_sc_hd__nand3_1 _842_ (.A(_416_),
    .B(_418_),
    .C(net60),
    .Y(_419_));
 sky130_fd_sc_hd__nand2_1 _843_ (.A(_414_),
    .B(_419_),
    .Y(_420_));
 sky130_fd_sc_hd__nor2_1 _844_ (.A(net59),
    .B(_420_),
    .Y(_421_));
 sky130_fd_sc_hd__inv_1 _845_ (.A(\storage[4][12] ),
    .Y(_422_));
 sky130_fd_sc_hd__nand2_1 _846_ (.A(net58),
    .B(_422_),
    .Y(_423_));
 sky130_fd_sc_hd__inv_1 _847_ (.A(\storage[5][12] ),
    .Y(_424_));
 sky130_fd_sc_hd__nand2_1 _848_ (.A(_424_),
    .B(net61),
    .Y(_425_));
 sky130_fd_sc_hd__nand3_1 _849_ (.A(_423_),
    .B(_425_),
    .C(_070_),
    .Y(_426_));
 sky130_fd_sc_hd__inv_2 _850_ (.A(\rptr[1] ),
    .Y(_070_));
 sky130_fd_sc_hd__inv_1 _851_ (.A(\storage[6][12] ),
    .Y(_427_));
 sky130_fd_sc_hd__nand2_1 _852_ (.A(net58),
    .B(_427_),
    .Y(_428_));
 sky130_fd_sc_hd__inv_1 _853_ (.A(\storage[7][12] ),
    .Y(_429_));
 sky130_fd_sc_hd__nand2_1 _854_ (.A(_429_),
    .B(net61),
    .Y(_430_));
 sky130_fd_sc_hd__nand3_1 _855_ (.A(_428_),
    .B(_430_),
    .C(net60),
    .Y(_431_));
 sky130_fd_sc_hd__nand3_1 _856_ (.A(_426_),
    .B(_431_),
    .C(net59),
    .Y(_432_));
 sky130_fd_sc_hd__nand2_1 _857_ (.A(_432_),
    .B(_041_),
    .Y(_433_));
 sky130_fd_sc_hd__nor2_1 _858_ (.A(_421_),
    .B(_433_),
    .Y(net25));
 sky130_fd_sc_hd__inv_1 _859_ (.A(\storage[0][13] ),
    .Y(_434_));
 sky130_fd_sc_hd__nand2_1 _860_ (.A(net58),
    .B(_434_),
    .Y(_435_));
 sky130_fd_sc_hd__inv_1 _862_ (.A(\storage[1][13] ),
    .Y(_436_));
 sky130_fd_sc_hd__nand2_1 _863_ (.A(_436_),
    .B(net61),
    .Y(_437_));
 sky130_fd_sc_hd__nand3_1 _864_ (.A(_435_),
    .B(_437_),
    .C(_070_),
    .Y(_438_));
 sky130_fd_sc_hd__inv_1 _865_ (.A(\storage[2][13] ),
    .Y(_439_));
 sky130_fd_sc_hd__nand2_1 _866_ (.A(net58),
    .B(_439_),
    .Y(_440_));
 sky130_fd_sc_hd__inv_1 _867_ (.A(\storage[3][13] ),
    .Y(_441_));
 sky130_fd_sc_hd__nand2_1 _868_ (.A(_441_),
    .B(net61),
    .Y(_442_));
 sky130_fd_sc_hd__nand3_1 _869_ (.A(_440_),
    .B(_442_),
    .C(net60),
    .Y(_443_));
 sky130_fd_sc_hd__nand2_1 _870_ (.A(_438_),
    .B(_443_),
    .Y(_444_));
 sky130_fd_sc_hd__nor2_1 _871_ (.A(net59),
    .B(_444_),
    .Y(_445_));
 sky130_fd_sc_hd__nand3_1 _872_ (.A(_064_),
    .B(_068_),
    .C(_070_),
    .Y(_072_));
 sky130_fd_sc_hd__inv_1 _873_ (.A(\storage[4][13] ),
    .Y(_446_));
 sky130_fd_sc_hd__nand2_1 _874_ (.A(net58),
    .B(_446_),
    .Y(_447_));
 sky130_fd_sc_hd__inv_1 _875_ (.A(\storage[5][13] ),
    .Y(_448_));
 sky130_fd_sc_hd__nand2_1 _876_ (.A(_448_),
    .B(net61),
    .Y(_449_));
 sky130_fd_sc_hd__nand3_1 _877_ (.A(_447_),
    .B(_449_),
    .C(_070_),
    .Y(_450_));
 sky130_fd_sc_hd__inv_1 _878_ (.A(\storage[6][13] ),
    .Y(_451_));
 sky130_fd_sc_hd__nand2_1 _879_ (.A(net58),
    .B(_451_),
    .Y(_452_));
 sky130_fd_sc_hd__inv_1 _880_ (.A(\storage[7][13] ),
    .Y(_453_));
 sky130_fd_sc_hd__nand2_1 _881_ (.A(_453_),
    .B(net61),
    .Y(_454_));
 sky130_fd_sc_hd__nand3_1 _882_ (.A(_452_),
    .B(_454_),
    .C(net60),
    .Y(_455_));
 sky130_fd_sc_hd__nand3_1 _884_ (.A(_450_),
    .B(_455_),
    .C(net59),
    .Y(_456_));
 sky130_fd_sc_hd__nand2_1 _885_ (.A(_456_),
    .B(_041_),
    .Y(_457_));
 sky130_fd_sc_hd__nor2_1 _886_ (.A(_445_),
    .B(_457_),
    .Y(net26));
 sky130_fd_sc_hd__inv_1 _887_ (.A(\storage[0][14] ),
    .Y(_458_));
 sky130_fd_sc_hd__nand2_1 _888_ (.A(net58),
    .B(_458_),
    .Y(_459_));
 sky130_fd_sc_hd__inv_1 _889_ (.A(\storage[1][14] ),
    .Y(_460_));
 sky130_fd_sc_hd__nand2_1 _890_ (.A(_460_),
    .B(net61),
    .Y(_461_));
 sky130_fd_sc_hd__nand3_1 _891_ (.A(_459_),
    .B(_461_),
    .C(_070_),
    .Y(_462_));
 sky130_fd_sc_hd__inv_1 _892_ (.A(\storage[2][14] ),
    .Y(_463_));
 sky130_fd_sc_hd__nand2_1 _893_ (.A(net58),
    .B(_463_),
    .Y(_464_));
 sky130_fd_sc_hd__inv_1 _894_ (.A(\storage[2][15] ),
    .Y(_074_));
 sky130_fd_sc_hd__inv_1 _895_ (.A(\storage[3][14] ),
    .Y(_465_));
 sky130_fd_sc_hd__nand2_1 _896_ (.A(_465_),
    .B(net61),
    .Y(_466_));
 sky130_fd_sc_hd__nand3_1 _897_ (.A(_464_),
    .B(_466_),
    .C(net60),
    .Y(_467_));
 sky130_fd_sc_hd__nand2_1 _898_ (.A(_462_),
    .B(_467_),
    .Y(_468_));
 sky130_fd_sc_hd__nor2_1 _899_ (.A(net59),
    .B(_468_),
    .Y(_469_));
 sky130_fd_sc_hd__inv_1 _900_ (.A(\storage[4][14] ),
    .Y(_470_));
 sky130_fd_sc_hd__nand2_1 _901_ (.A(net58),
    .B(_470_),
    .Y(_471_));
 sky130_fd_sc_hd__inv_1 _902_ (.A(\storage[5][14] ),
    .Y(_472_));
 sky130_fd_sc_hd__nand2_1 _903_ (.A(_472_),
    .B(net61),
    .Y(_473_));
 sky130_fd_sc_hd__nand3_1 _904_ (.A(_471_),
    .B(_473_),
    .C(_070_),
    .Y(_474_));
 sky130_fd_sc_hd__nand2_1 _905_ (.A(_060_),
    .B(_074_),
    .Y(_075_));
 sky130_fd_sc_hd__inv_1 _906_ (.A(\storage[6][14] ),
    .Y(_475_));
 sky130_fd_sc_hd__nand2_1 _907_ (.A(net58),
    .B(_475_),
    .Y(_476_));
 sky130_fd_sc_hd__inv_1 _908_ (.A(\storage[7][14] ),
    .Y(_477_));
 sky130_fd_sc_hd__nand2_1 _909_ (.A(_477_),
    .B(net61),
    .Y(_478_));
 sky130_fd_sc_hd__nand3_1 _910_ (.A(_476_),
    .B(_478_),
    .C(net60),
    .Y(_479_));
 sky130_fd_sc_hd__nand3_1 _911_ (.A(_474_),
    .B(_479_),
    .C(net59),
    .Y(_480_));
 sky130_fd_sc_hd__nand2_1 _912_ (.A(_480_),
    .B(_041_),
    .Y(_481_));
 sky130_fd_sc_hd__nor2_1 _913_ (.A(_469_),
    .B(_481_),
    .Y(net27));
 sky130_fd_sc_hd__inv_1 _914_ (.A(\storage[3][15] ),
    .Y(_076_));
 sky130_fd_sc_hd__nand2_2 _915_ (.A(_037_),
    .B(net19),
    .Y(_014_));
 sky130_fd_sc_hd__nand2_1 _917_ (.A(_076_),
    .B(\rptr[0] ),
    .Y(_078_));
 sky130_fd_sc_hd__nand3_1 _919_ (.A(_075_),
    .B(_078_),
    .C(net60),
    .Y(_080_));
 sky130_fd_sc_hd__nand2_1 _920_ (.A(_072_),
    .B(_080_),
    .Y(_081_));
 sky130_fd_sc_hd__nor2_1 _921_ (.A(\rptr[2] ),
    .B(_081_),
    .Y(_082_));
 sky130_fd_sc_hd__inv_1 _923_ (.A(\storage[4][15] ),
    .Y(_084_));
 sky130_fd_sc_hd__nand2_1 _924_ (.A(_060_),
    .B(_084_),
    .Y(_085_));
 sky130_fd_sc_hd__inv_1 _925_ (.A(\storage[5][15] ),
    .Y(_086_));
 sky130_fd_sc_hd__or2_4 _926_ (.A(\wptr[0] ),
    .B(_014_),
    .X(_039_));
 sky130_fd_sc_hd__nand2_1 _928_ (.A(_086_),
    .B(\rptr[0] ),
    .Y(_088_));
 sky130_fd_sc_hd__nand3_1 _930_ (.A(_085_),
    .B(_088_),
    .C(_070_),
    .Y(_090_));
 sky130_fd_sc_hd__inv_1 _932_ (.A(\storage[6][15] ),
    .Y(_092_));
 sky130_fd_sc_hd__nand2_1 _933_ (.A(_060_),
    .B(_092_),
    .Y(_093_));
 sky130_fd_sc_hd__inv_1 _934_ (.A(\storage[7][15] ),
    .Y(_094_));
 sky130_fd_sc_hd__nand2_1 _936_ (.A(_094_),
    .B(\rptr[0] ),
    .Y(_096_));
 sky130_fd_sc_hd__nor2_1 _937_ (.A(_038_),
    .B(_039_),
    .Y(_033_));
 sky130_fd_sc_hd__nand3_1 _939_ (.A(_093_),
    .B(_096_),
    .C(net60),
    .Y(_098_));
 sky130_fd_sc_hd__nand3_1 _941_ (.A(_090_),
    .B(_098_),
    .C(\rptr[2] ),
    .Y(_100_));
 sky130_fd_sc_hd__nand2_1 _943_ (.A(_100_),
    .B(_041_),
    .Y(_102_));
 sky130_fd_sc_hd__nor2_1 _944_ (.A(_082_),
    .B(_102_),
    .Y(net28));
 sky130_fd_sc_hd__inv_1 _945_ (.A(_041_),
    .Y(net20));
 sky130_fd_sc_hd__inv_1 _946_ (.A(\wptr[2] ),
    .Y(_103_));
 sky130_fd_sc_hd__inv_1 _947_ (.A(\wptr[1] ),
    .Y(_104_));
 sky130_fd_sc_hd__inv_1 _948_ (.A(\used[3] ),
    .Y(_040_));
 sky130_fd_sc_hd__nand3_1 _949_ (.A(_103_),
    .B(_104_),
    .C(net2),
    .Y(_105_));
 sky130_fd_sc_hd__nor2_1 _950_ (.A(_105_),
    .B(_039_),
    .Y(_027_));
 sky130_fd_sc_hd__nand3_1 _951_ (.A(_104_),
    .B(\wptr[2] ),
    .C(net2),
    .Y(_106_));
 sky130_fd_sc_hd__nor2_1 _952_ (.A(_106_),
    .B(_039_),
    .Y(_031_));
 sky130_fd_sc_hd__nand3_1 _953_ (.A(_037_),
    .B(net19),
    .C(\wptr[0] ),
    .Y(_107_));
 sky130_fd_sc_hd__nor2_1 _954_ (.A(_105_),
    .B(_107_),
    .Y(_028_));
 sky130_fd_sc_hd__nand3_1 _955_ (.A(_103_),
    .B(net2),
    .C(\wptr[1] ),
    .Y(_108_));
 sky130_fd_sc_hd__nor2_1 _956_ (.A(_108_),
    .B(_039_),
    .Y(_029_));
 sky130_fd_sc_hd__nor2_1 _957_ (.A(_108_),
    .B(_107_),
    .Y(_030_));
 sky130_fd_sc_hd__nor2_1 _958_ (.A(_106_),
    .B(_107_),
    .Y(_032_));
 sky130_fd_sc_hd__nand3_2 _959_ (.A(_035_),
    .B(_040_),
    .C(_036_),
    .Y(_041_));
 sky130_fd_sc_hd__nor2_1 _960_ (.A(_038_),
    .B(_107_),
    .Y(_034_));
 sky130_fd_sc_hd__xor2_1 _961_ (.A(_060_),
    .B(_042_),
    .X(_023_));
 sky130_fd_sc_hd__nand2_1 _962_ (.A(_015_),
    .B(_009_),
    .Y(_109_));
 sky130_fd_sc_hd__o21ai_1 _963_ (.A1(_070_),
    .A2(_015_),
    .B1(_109_),
    .Y(_022_));
 sky130_fd_sc_hd__inv_1 _964_ (.A(\used[0] ),
    .Y(_000_));
 sky130_fd_sc_hd__xnor2_1 _965_ (.A(_016_),
    .B(\used[0] ),
    .Y(_021_));
 sky130_fd_sc_hd__nand2_1 _966_ (.A(_016_),
    .B(\used[1] ),
    .Y(_110_));
 sky130_fd_sc_hd__o21ai_0 _967_ (.A1(_016_),
    .A2(_004_),
    .B1(_110_),
    .Y(_020_));
 sky130_fd_sc_hd__xor2_1 _968_ (.A(_013_),
    .B(_003_),
    .X(_111_));
 sky130_fd_sc_hd__nand2_1 _969_ (.A(_016_),
    .B(\used[2] ),
    .Y(_112_));
 sky130_fd_sc_hd__fa_1 _970_ (.A(_000_),
    .B(_001_),
    .CIN(_002_),
    .COUT(_003_),
    .SUM(_004_));
 sky130_fd_sc_hd__ha_1 _971_ (.A(\wptr[0] ),
    .B(\wptr[1] ),
    .COUT(_006_),
    .SUM(_007_));
 sky130_fd_sc_hd__ha_1 _972_ (.A(\rptr[0] ),
    .B(net60),
    .COUT(_008_),
    .SUM(_009_));
 sky130_fd_sc_hd__ha_1 _973_ (.A(\used[1] ),
    .B(_005_),
    .COUT(_010_),
    .SUM(_011_));
 sky130_fd_sc_hd__ha_1 _974_ (.A(\used[2] ),
    .B(_005_),
    .COUT(_012_),
    .SUM(_013_));
 sky130_fd_sc_hd__ha_1 _975_ (.A(_014_),
    .B(_015_),
    .COUT(_005_),
    .SUM(_016_));
 sky130_fd_sc_hd__clkbuf_16 clkbuf_0_clk (.A(clk),
    .X(clknet_0_clk));
 sky130_fd_sc_hd__clkbuf_16 clkbuf_4_0_0_clk (.A(clknet_0_clk),
    .X(clknet_4_0_0_clk));
 sky130_fd_sc_hd__clkbuf_16 clkbuf_4_10_0_clk (.A(clknet_0_clk),
    .X(clknet_4_10_0_clk));
 sky130_fd_sc_hd__clkbuf_16 clkbuf_4_11_0_clk (.A(clknet_0_clk),
    .X(clknet_4_11_0_clk));
 sky130_fd_sc_hd__clkbuf_16 clkbuf_4_12_0_clk (.A(clknet_0_clk),
    .X(clknet_4_12_0_clk));
 sky130_fd_sc_hd__clkbuf_16 clkbuf_4_13_0_clk (.A(clknet_0_clk),
    .X(clknet_4_13_0_clk));
 sky130_fd_sc_hd__clkbuf_16 clkbuf_4_14_0_clk (.A(clknet_0_clk),
    .X(clknet_4_14_0_clk));
 sky130_fd_sc_hd__clkbuf_16 clkbuf_4_15_0_clk (.A(clknet_0_clk),
    .X(clknet_4_15_0_clk));
 sky130_fd_sc_hd__clkbuf_16 clkbuf_4_1_0_clk (.A(clknet_0_clk),
    .X(clknet_4_1_0_clk));
 sky130_fd_sc_hd__clkbuf_16 clkbuf_4_2_0_clk (.A(clknet_0_clk),
    .X(clknet_4_2_0_clk));
 sky130_fd_sc_hd__clkbuf_16 clkbuf_4_3_0_clk (.A(clknet_0_clk),
    .X(clknet_4_3_0_clk));
 sky130_fd_sc_hd__clkbuf_16 clkbuf_4_4_0_clk (.A(clknet_0_clk),
    .X(clknet_4_4_0_clk));
 sky130_fd_sc_hd__clkbuf_16 clkbuf_4_5_0_clk (.A(clknet_0_clk),
    .X(clknet_4_5_0_clk));
 sky130_fd_sc_hd__clkbuf_16 clkbuf_4_6_0_clk (.A(clknet_0_clk),
    .X(clknet_4_6_0_clk));
 sky130_fd_sc_hd__clkbuf_16 clkbuf_4_7_0_clk (.A(clknet_0_clk),
    .X(clknet_4_7_0_clk));
 sky130_fd_sc_hd__clkbuf_16 clkbuf_4_8_0_clk (.A(clknet_0_clk),
    .X(clknet_4_8_0_clk));
 sky130_fd_sc_hd__clkbuf_16 clkbuf_4_9_0_clk (.A(clknet_0_clk),
    .X(clknet_4_9_0_clk));
 sky130_fd_sc_hd__bufinv_16 clkload0 (.A(clknet_4_0_0_clk));
 sky130_fd_sc_hd__clkinv_2 clkload1 (.A(clknet_4_1_0_clk));
 sky130_fd_sc_hd__clkbuf_1 clkload10 (.A(clknet_4_12_0_clk));
 sky130_fd_sc_hd__bufinv_16 clkload11 (.A(clknet_4_13_0_clk));
 sky130_fd_sc_hd__bufinv_16 clkload12 (.A(clknet_4_14_0_clk));
 sky130_fd_sc_hd__clkinv_1 clkload13 (.A(clknet_4_15_0_clk));
 sky130_fd_sc_hd__clkinv_4 clkload2 (.A(clknet_4_2_0_clk));
 sky130_fd_sc_hd__clkinv_4 clkload3 (.A(clknet_4_3_0_clk));
 sky130_fd_sc_hd__clkinv_2 clkload4 (.A(clknet_4_4_0_clk));
 sky130_fd_sc_hd__bufinv_16 clkload5 (.A(clknet_4_5_0_clk));
 sky130_fd_sc_hd__clkinvlp_4 clkload6 (.A(clknet_4_6_0_clk));
 sky130_fd_sc_hd__clkinvlp_4 clkload7 (.A(clknet_4_7_0_clk));
 sky130_fd_sc_hd__bufinv_16 clkload8 (.A(clknet_4_10_0_clk));
 sky130_fd_sc_hd__clkinv_2 clkload9 (.A(clknet_4_11_0_clk));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input1 (.A(rd_en),
    .X(net1));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input10 (.A(wr_data[1]),
    .X(net10));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input11 (.A(wr_data[2]),
    .X(net11));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input12 (.A(wr_data[3]),
    .X(net12));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input13 (.A(wr_data[4]),
    .X(net13));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input14 (.A(wr_data[5]),
    .X(net14));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input15 (.A(wr_data[6]),
    .X(net15));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input16 (.A(wr_data[7]),
    .X(net16));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input17 (.A(wr_data[8]),
    .X(net17));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input18 (.A(wr_data[9]),
    .X(net18));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input19 (.A(wr_en),
    .X(net19));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input2 (.A(rst_n),
    .X(net2));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input3 (.A(wr_data[0]),
    .X(net3));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input4 (.A(wr_data[10]),
    .X(net4));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input5 (.A(wr_data[11]),
    .X(net5));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input6 (.A(wr_data[12]),
    .X(net6));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input7 (.A(wr_data[13]),
    .X(net7));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input8 (.A(wr_data[14]),
    .X(net8));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input9 (.A(wr_data[15]),
    .X(net9));
 sky130_fd_sc_hd__clkdlybuf4s50_1 output20 (.A(net20),
    .X(empty));
 sky130_fd_sc_hd__clkdlybuf4s50_1 output21 (.A(net21),
    .X(full));
 sky130_fd_sc_hd__clkdlybuf4s50_1 output22 (.A(net22),
    .X(rd_data[0]));
 sky130_fd_sc_hd__clkdlybuf4s50_1 output23 (.A(net23),
    .X(rd_data[10]));
 sky130_fd_sc_hd__clkdlybuf4s50_1 output24 (.A(net24),
    .X(rd_data[11]));
 sky130_fd_sc_hd__clkdlybuf4s50_1 output25 (.A(net25),
    .X(rd_data[12]));
 sky130_fd_sc_hd__clkdlybuf4s50_1 output26 (.A(net26),
    .X(rd_data[13]));
 sky130_fd_sc_hd__clkdlybuf4s50_1 output27 (.A(net27),
    .X(rd_data[14]));
 sky130_fd_sc_hd__clkdlybuf4s50_1 output28 (.A(net28),
    .X(rd_data[15]));
 sky130_fd_sc_hd__clkdlybuf4s50_1 output29 (.A(net29),
    .X(rd_data[1]));
 sky130_fd_sc_hd__clkdlybuf4s50_1 output30 (.A(net30),
    .X(rd_data[2]));
 sky130_fd_sc_hd__clkdlybuf4s50_1 output31 (.A(net31),
    .X(rd_data[3]));
 sky130_fd_sc_hd__clkdlybuf4s50_1 output32 (.A(net32),
    .X(rd_data[4]));
 sky130_fd_sc_hd__clkdlybuf4s50_1 output33 (.A(net33),
    .X(rd_data[5]));
 sky130_fd_sc_hd__clkdlybuf4s50_1 output34 (.A(net34),
    .X(rd_data[6]));
 sky130_fd_sc_hd__clkdlybuf4s50_1 output35 (.A(net35),
    .X(rd_data[7]));
 sky130_fd_sc_hd__clkdlybuf4s50_1 output36 (.A(net36),
    .X(rd_data[8]));
 sky130_fd_sc_hd__clkdlybuf4s50_1 output37 (.A(net37),
    .X(rd_data[9]));
 sky130_fd_sc_hd__buf_4 place50 (.A(_029_),
    .X(net50));
 sky130_fd_sc_hd__buf_4 place51 (.A(_031_),
    .X(net51));
 sky130_fd_sc_hd__buf_4 place52 (.A(_027_),
    .X(net52));
 sky130_fd_sc_hd__buf_4 place53 (.A(_033_),
    .X(net53));
 sky130_fd_sc_hd__buf_4 place54 (.A(_034_),
    .X(net54));
 sky130_fd_sc_hd__buf_4 place55 (.A(_032_),
    .X(net55));
 sky130_fd_sc_hd__buf_4 place56 (.A(_030_),
    .X(net56));
 sky130_fd_sc_hd__buf_4 place57 (.A(_028_),
    .X(net57));
 sky130_fd_sc_hd__buf_4 place58 (.A(_060_),
    .X(net58));
 sky130_fd_sc_hd__buf_4 place59 (.A(\rptr[2] ),
    .X(net59));
 sky130_fd_sc_hd__buf_4 place60 (.A(\rptr[1] ),
    .X(net60));
 sky130_fd_sc_hd__buf_4 place61 (.A(\rptr[0] ),
    .X(net61));
 sky130_fd_sc_hd__dfrtp_1 \rptr[0]$_DFFE_PN0P_  (.D(_023_),
    .Q(\rptr[0] ),
    .RESET_B(net2),
    .CLK(clknet_4_6_0_clk));
 sky130_fd_sc_hd__dfrtp_1 \rptr[1]$_DFFE_PN0P_  (.D(_022_),
    .Q(\rptr[1] ),
    .RESET_B(net2),
    .CLK(clknet_4_6_0_clk));
 sky130_fd_sc_hd__dfrtp_1 \rptr[2]$_DFFE_PN0P_  (.D(_026_),
    .Q(\rptr[2] ),
    .RESET_B(net2),
    .CLK(clknet_4_6_0_clk));
 sky130_fd_sc_hd__edfxtp_1 \storage[0][0]$_DFFE_PP_  (.D(net3),
    .DE(_027_),
    .Q(\storage[0][0] ),
    .CLK(clknet_4_5_0_clk));
 sky130_fd_sc_hd__edfxtp_1 \storage[0][10]$_DFFE_PP_  (.D(net4),
    .DE(net52),
    .Q(\storage[0][10] ),
    .CLK(clknet_4_10_0_clk));
 sky130_fd_sc_hd__edfxtp_1 \storage[0][11]$_DFFE_PP_  (.D(net5),
    .DE(net52),
    .Q(\storage[0][11] ),
    .CLK(clknet_4_8_0_clk));
 sky130_fd_sc_hd__edfxtp_1 \storage[0][12]$_DFFE_PP_  (.D(net6),
    .DE(net52),
    .Q(\storage[0][12] ),
    .CLK(clknet_4_2_0_clk));
 sky130_fd_sc_hd__edfxtp_1 \storage[0][13]$_DFFE_PP_  (.D(net7),
    .DE(net52),
    .Q(\storage[0][13] ),
    .CLK(clknet_4_3_0_clk));
 sky130_fd_sc_hd__edfxtp_1 \storage[0][14]$_DFFE_PP_  (.D(net8),
    .DE(net52),
    .Q(\storage[0][14] ),
    .CLK(clknet_4_0_0_clk));
 sky130_fd_sc_hd__edfxtp_1 \storage[0][15]$_DFFE_PP_  (.D(net9),
    .DE(_027_),
    .Q(\storage[0][15] ),
    .CLK(clknet_4_4_0_clk));
 sky130_fd_sc_hd__edfxtp_1 \storage[0][1]$_DFFE_PP_  (.D(net10),
    .DE(net52),
    .Q(\storage[0][1] ),
    .CLK(clknet_4_6_0_clk));
 sky130_fd_sc_hd__edfxtp_1 \storage[0][2]$_DFFE_PP_  (.D(net11),
    .DE(net52),
    .Q(\storage[0][2] ),
    .CLK(clknet_4_12_0_clk));
 sky130_fd_sc_hd__edfxtp_1 \storage[0][3]$_DFFE_PP_  (.D(net12),
    .DE(net52),
    .Q(\storage[0][3] ),
    .CLK(clknet_4_12_0_clk));
 sky130_fd_sc_hd__edfxtp_1 \storage[0][4]$_DFFE_PP_  (.D(net13),
    .DE(net52),
    .Q(\storage[0][4] ),
    .CLK(clknet_4_12_0_clk));
 sky130_fd_sc_hd__edfxtp_1 \storage[0][5]$_DFFE_PP_  (.D(net14),
    .DE(net52),
    .Q(\storage[0][5] ),
    .CLK(clknet_4_14_0_clk));
 sky130_fd_sc_hd__edfxtp_1 \storage[0][6]$_DFFE_PP_  (.D(net15),
    .DE(net52),
    .Q(\storage[0][6] ),
    .CLK(clknet_4_14_0_clk));
 sky130_fd_sc_hd__edfxtp_1 \storage[0][7]$_DFFE_PP_  (.D(net16),
    .DE(net52),
    .Q(\storage[0][7] ),
    .CLK(clknet_4_9_0_clk));
 sky130_fd_sc_hd__edfxtp_1 \storage[0][8]$_DFFE_PP_  (.D(net17),
    .DE(net52),
    .Q(\storage[0][8] ),
    .CLK(clknet_4_11_0_clk));
 sky130_fd_sc_hd__edfxtp_1 \storage[0][9]$_DFFE_PP_  (.D(net18),
    .DE(net52),
    .Q(\storage[0][9] ),
    .CLK(clknet_4_8_0_clk));
 sky130_fd_sc_hd__edfxtp_1 \storage[1][0]$_DFFE_PP_  (.D(net3),
    .DE(net57),
    .Q(\storage[1][0] ),
    .CLK(clknet_4_5_0_clk));
 sky130_fd_sc_hd__edfxtp_1 \storage[1][10]$_DFFE_PP_  (.D(net4),
    .DE(net57),
    .Q(\storage[1][10] ),
    .CLK(clknet_4_10_0_clk));
 sky130_fd_sc_hd__edfxtp_1 \storage[1][11]$_DFFE_PP_  (.D(net5),
    .DE(net57),
    .Q(\storage[1][11] ),
    .CLK(clknet_4_8_0_clk));
 sky130_fd_sc_hd__edfxtp_1 \storage[1][12]$_DFFE_PP_  (.D(net6),
    .DE(net57),
    .Q(\storage[1][12] ),
    .CLK(clknet_4_2_0_clk));
 sky130_fd_sc_hd__edfxtp_1 \storage[1][13]$_DFFE_PP_  (.D(net7),
    .DE(net57),
    .Q(\storage[1][13] ),
    .CLK(clknet_4_3_0_clk));
 sky130_fd_sc_hd__edfxtp_1 \storage[1][14]$_DFFE_PP_  (.D(net8),
    .DE(net57),
    .Q(\storage[1][14] ),
    .CLK(clknet_4_0_0_clk));
 sky130_fd_sc_hd__edfxtp_1 \storage[1][15]$_DFFE_PP_  (.D(net9),
    .DE(net57),
    .Q(\storage[1][15] ),
    .CLK(clknet_4_4_0_clk));
 sky130_fd_sc_hd__edfxtp_1 \storage[1][1]$_DFFE_PP_  (.D(net10),
    .DE(net57),
    .Q(\storage[1][1] ),
    .CLK(clknet_4_7_0_clk));
 sky130_fd_sc_hd__edfxtp_1 \storage[1][2]$_DFFE_PP_  (.D(net11),
    .DE(net57),
    .Q(\storage[1][2] ),
    .CLK(clknet_4_6_0_clk));
 sky130_fd_sc_hd__edfxtp_1 \storage[1][3]$_DFFE_PP_  (.D(net12),
    .DE(net57),
    .Q(\storage[1][3] ),
    .CLK(clknet_4_12_0_clk));
 sky130_fd_sc_hd__edfxtp_1 \storage[1][4]$_DFFE_PP_  (.D(net13),
    .DE(net57),
    .Q(\storage[1][4] ),
    .CLK(clknet_4_13_0_clk));
 sky130_fd_sc_hd__edfxtp_1 \storage[1][5]$_DFFE_PP_  (.D(net14),
    .DE(net57),
    .Q(\storage[1][5] ),
    .CLK(clknet_4_15_0_clk));
 sky130_fd_sc_hd__edfxtp_1 \storage[1][6]$_DFFE_PP_  (.D(net15),
    .DE(net57),
    .Q(\storage[1][6] ),
    .CLK(clknet_4_11_0_clk));
 sky130_fd_sc_hd__edfxtp_1 \storage[1][7]$_DFFE_PP_  (.D(net16),
    .DE(net57),
    .Q(\storage[1][7] ),
    .CLK(clknet_4_9_0_clk));
 sky130_fd_sc_hd__edfxtp_1 \storage[1][8]$_DFFE_PP_  (.D(net17),
    .DE(net57),
    .Q(\storage[1][8] ),
    .CLK(clknet_4_11_0_clk));
 sky130_fd_sc_hd__edfxtp_1 \storage[1][9]$_DFFE_PP_  (.D(net18),
    .DE(net57),
    .Q(\storage[1][9] ),
    .CLK(clknet_4_8_0_clk));
 sky130_fd_sc_hd__edfxtp_1 \storage[2][0]$_DFFE_PP_  (.D(net3),
    .DE(_029_),
    .Q(\storage[2][0] ),
    .CLK(clknet_4_5_0_clk));
 sky130_fd_sc_hd__edfxtp_1 \storage[2][10]$_DFFE_PP_  (.D(net4),
    .DE(net50),
    .Q(\storage[2][10] ),
    .CLK(clknet_4_10_0_clk));
 sky130_fd_sc_hd__edfxtp_1 \storage[2][11]$_DFFE_PP_  (.D(net5),
    .DE(net50),
    .Q(\storage[2][11] ),
    .CLK(clknet_4_8_0_clk));
 sky130_fd_sc_hd__edfxtp_1 \storage[2][12]$_DFFE_PP_  (.D(net6),
    .DE(net50),
    .Q(\storage[2][12] ),
    .CLK(clknet_4_2_0_clk));
 sky130_fd_sc_hd__edfxtp_1 \storage[2][13]$_DFFE_PP_  (.D(net7),
    .DE(net50),
    .Q(\storage[2][13] ),
    .CLK(clknet_4_3_0_clk));
 sky130_fd_sc_hd__edfxtp_1 \storage[2][14]$_DFFE_PP_  (.D(net8),
    .DE(net50),
    .Q(\storage[2][14] ),
    .CLK(clknet_4_0_0_clk));
 sky130_fd_sc_hd__edfxtp_1 \storage[2][15]$_DFFE_PP_  (.D(net9),
    .DE(_029_),
    .Q(\storage[2][15] ),
    .CLK(clknet_4_4_0_clk));
 sky130_fd_sc_hd__edfxtp_1 \storage[2][1]$_DFFE_PP_  (.D(net10),
    .DE(net50),
    .Q(\storage[2][1] ),
    .CLK(clknet_4_6_0_clk));
 sky130_fd_sc_hd__edfxtp_1 \storage[2][2]$_DFFE_PP_  (.D(net11),
    .DE(net50),
    .Q(\storage[2][2] ),
    .CLK(clknet_4_12_0_clk));
 sky130_fd_sc_hd__edfxtp_1 \storage[2][3]$_DFFE_PP_  (.D(net12),
    .DE(net50),
    .Q(\storage[2][3] ),
    .CLK(clknet_4_12_0_clk));
 sky130_fd_sc_hd__edfxtp_1 \storage[2][4]$_DFFE_PP_  (.D(net13),
    .DE(net50),
    .Q(\storage[2][4] ),
    .CLK(clknet_4_15_0_clk));
 sky130_fd_sc_hd__edfxtp_1 \storage[2][5]$_DFFE_PP_  (.D(net14),
    .DE(net50),
    .Q(\storage[2][5] ),
    .CLK(clknet_4_15_0_clk));
 sky130_fd_sc_hd__edfxtp_1 \storage[2][6]$_DFFE_PP_  (.D(net15),
    .DE(net50),
    .Q(\storage[2][6] ),
    .CLK(clknet_4_11_0_clk));
 sky130_fd_sc_hd__edfxtp_1 \storage[2][7]$_DFFE_PP_  (.D(net16),
    .DE(net50),
    .Q(\storage[2][7] ),
    .CLK(clknet_4_12_0_clk));
 sky130_fd_sc_hd__edfxtp_1 \storage[2][8]$_DFFE_PP_  (.D(net17),
    .DE(net50),
    .Q(\storage[2][8] ),
    .CLK(clknet_4_11_0_clk));
 sky130_fd_sc_hd__edfxtp_1 \storage[2][9]$_DFFE_PP_  (.D(net18),
    .DE(net50),
    .Q(\storage[2][9] ),
    .CLK(clknet_4_8_0_clk));
 sky130_fd_sc_hd__edfxtp_1 \storage[3][0]$_DFFE_PP_  (.D(net3),
    .DE(net56),
    .Q(\storage[3][0] ),
    .CLK(clknet_4_5_0_clk));
 sky130_fd_sc_hd__edfxtp_1 \storage[3][10]$_DFFE_PP_  (.D(net4),
    .DE(net56),
    .Q(\storage[3][10] ),
    .CLK(clknet_4_10_0_clk));
 sky130_fd_sc_hd__edfxtp_1 \storage[3][11]$_DFFE_PP_  (.D(net5),
    .DE(net56),
    .Q(\storage[3][11] ),
    .CLK(clknet_4_8_0_clk));
 sky130_fd_sc_hd__edfxtp_1 \storage[3][12]$_DFFE_PP_  (.D(net6),
    .DE(net56),
    .Q(\storage[3][12] ),
    .CLK(clknet_4_2_0_clk));
 sky130_fd_sc_hd__edfxtp_1 \storage[3][13]$_DFFE_PP_  (.D(net7),
    .DE(net56),
    .Q(\storage[3][13] ),
    .CLK(clknet_4_1_0_clk));
 sky130_fd_sc_hd__edfxtp_1 \storage[3][14]$_DFFE_PP_  (.D(net8),
    .DE(net56),
    .Q(\storage[3][14] ),
    .CLK(clknet_4_0_0_clk));
 sky130_fd_sc_hd__edfxtp_1 \storage[3][15]$_DFFE_PP_  (.D(net9),
    .DE(net56),
    .Q(\storage[3][15] ),
    .CLK(clknet_4_4_0_clk));
 sky130_fd_sc_hd__edfxtp_1 \storage[3][1]$_DFFE_PP_  (.D(net10),
    .DE(net56),
    .Q(\storage[3][1] ),
    .CLK(clknet_4_7_0_clk));
 sky130_fd_sc_hd__edfxtp_1 \storage[3][2]$_DFFE_PP_  (.D(net11),
    .DE(net56),
    .Q(\storage[3][2] ),
    .CLK(clknet_4_12_0_clk));
 sky130_fd_sc_hd__edfxtp_1 \storage[3][3]$_DFFE_PP_  (.D(net12),
    .DE(net56),
    .Q(\storage[3][3] ),
    .CLK(clknet_4_12_0_clk));
 sky130_fd_sc_hd__edfxtp_1 \storage[3][4]$_DFFE_PP_  (.D(net13),
    .DE(net56),
    .Q(\storage[3][4] ),
    .CLK(clknet_4_13_0_clk));
 sky130_fd_sc_hd__edfxtp_1 \storage[3][5]$_DFFE_PP_  (.D(net14),
    .DE(net56),
    .Q(\storage[3][5] ),
    .CLK(clknet_4_15_0_clk));
 sky130_fd_sc_hd__edfxtp_1 \storage[3][6]$_DFFE_PP_  (.D(net15),
    .DE(net56),
    .Q(\storage[3][6] ),
    .CLK(clknet_4_11_0_clk));
 sky130_fd_sc_hd__edfxtp_1 \storage[3][7]$_DFFE_PP_  (.D(net16),
    .DE(net56),
    .Q(\storage[3][7] ),
    .CLK(clknet_4_9_0_clk));
 sky130_fd_sc_hd__edfxtp_1 \storage[3][8]$_DFFE_PP_  (.D(net17),
    .DE(net56),
    .Q(\storage[3][8] ),
    .CLK(clknet_4_11_0_clk));
 sky130_fd_sc_hd__edfxtp_1 \storage[3][9]$_DFFE_PP_  (.D(net18),
    .DE(net56),
    .Q(\storage[3][9] ),
    .CLK(clknet_4_8_0_clk));
 sky130_fd_sc_hd__edfxtp_1 \storage[4][0]$_DFFE_PP_  (.D(net3),
    .DE(_031_),
    .Q(\storage[4][0] ),
    .CLK(clknet_4_5_0_clk));
 sky130_fd_sc_hd__edfxtp_1 \storage[4][10]$_DFFE_PP_  (.D(net4),
    .DE(net51),
    .Q(\storage[4][10] ),
    .CLK(clknet_4_10_0_clk));
 sky130_fd_sc_hd__edfxtp_1 \storage[4][11]$_DFFE_PP_  (.D(net5),
    .DE(net51),
    .Q(\storage[4][11] ),
    .CLK(clknet_4_8_0_clk));
 sky130_fd_sc_hd__edfxtp_1 \storage[4][12]$_DFFE_PP_  (.D(net6),
    .DE(net51),
    .Q(\storage[4][12] ),
    .CLK(clknet_4_3_0_clk));
 sky130_fd_sc_hd__edfxtp_1 \storage[4][13]$_DFFE_PP_  (.D(net7),
    .DE(net51),
    .Q(\storage[4][13] ),
    .CLK(clknet_4_1_0_clk));
 sky130_fd_sc_hd__edfxtp_1 \storage[4][14]$_DFFE_PP_  (.D(net8),
    .DE(net51),
    .Q(\storage[4][14] ),
    .CLK(clknet_4_2_0_clk));
 sky130_fd_sc_hd__edfxtp_1 \storage[4][15]$_DFFE_PP_  (.D(net9),
    .DE(_031_),
    .Q(\storage[4][15] ),
    .CLK(clknet_4_4_0_clk));
 sky130_fd_sc_hd__edfxtp_1 \storage[4][1]$_DFFE_PP_  (.D(net10),
    .DE(_031_),
    .Q(\storage[4][1] ),
    .CLK(clknet_4_7_0_clk));
 sky130_fd_sc_hd__edfxtp_1 \storage[4][2]$_DFFE_PP_  (.D(net11),
    .DE(net51),
    .Q(\storage[4][2] ),
    .CLK(clknet_4_6_0_clk));
 sky130_fd_sc_hd__edfxtp_1 \storage[4][3]$_DFFE_PP_  (.D(net12),
    .DE(_031_),
    .Q(\storage[4][3] ),
    .CLK(clknet_4_13_0_clk));
 sky130_fd_sc_hd__edfxtp_1 \storage[4][4]$_DFFE_PP_  (.D(net13),
    .DE(net51),
    .Q(\storage[4][4] ),
    .CLK(clknet_4_15_0_clk));
 sky130_fd_sc_hd__edfxtp_1 \storage[4][5]$_DFFE_PP_  (.D(net14),
    .DE(net51),
    .Q(\storage[4][5] ),
    .CLK(clknet_4_14_0_clk));
 sky130_fd_sc_hd__edfxtp_1 \storage[4][6]$_DFFE_PP_  (.D(net15),
    .DE(net51),
    .Q(\storage[4][6] ),
    .CLK(clknet_4_14_0_clk));
 sky130_fd_sc_hd__edfxtp_1 \storage[4][7]$_DFFE_PP_  (.D(net16),
    .DE(net51),
    .Q(\storage[4][7] ),
    .CLK(clknet_4_9_0_clk));
 sky130_fd_sc_hd__edfxtp_1 \storage[4][8]$_DFFE_PP_  (.D(net17),
    .DE(net51),
    .Q(\storage[4][8] ),
    .CLK(clknet_4_11_0_clk));
 sky130_fd_sc_hd__edfxtp_1 \storage[4][9]$_DFFE_PP_  (.D(net18),
    .DE(net51),
    .Q(\storage[4][9] ),
    .CLK(clknet_4_8_0_clk));
 sky130_fd_sc_hd__edfxtp_1 \storage[5][0]$_DFFE_PP_  (.D(net3),
    .DE(net55),
    .Q(\storage[5][0] ),
    .CLK(clknet_4_5_0_clk));
 sky130_fd_sc_hd__edfxtp_1 \storage[5][10]$_DFFE_PP_  (.D(net4),
    .DE(net55),
    .Q(\storage[5][10] ),
    .CLK(clknet_4_10_0_clk));
 sky130_fd_sc_hd__edfxtp_1 \storage[5][11]$_DFFE_PP_  (.D(net5),
    .DE(net55),
    .Q(\storage[5][11] ),
    .CLK(clknet_4_9_0_clk));
 sky130_fd_sc_hd__edfxtp_1 \storage[5][12]$_DFFE_PP_  (.D(net6),
    .DE(net55),
    .Q(\storage[5][12] ),
    .CLK(clknet_4_3_0_clk));
 sky130_fd_sc_hd__edfxtp_1 \storage[5][13]$_DFFE_PP_  (.D(net7),
    .DE(net55),
    .Q(\storage[5][13] ),
    .CLK(clknet_4_1_0_clk));
 sky130_fd_sc_hd__edfxtp_1 \storage[5][14]$_DFFE_PP_  (.D(net8),
    .DE(net55),
    .Q(\storage[5][14] ),
    .CLK(clknet_4_1_0_clk));
 sky130_fd_sc_hd__edfxtp_1 \storage[5][15]$_DFFE_PP_  (.D(net9),
    .DE(net55),
    .Q(\storage[5][15] ),
    .CLK(clknet_4_4_0_clk));
 sky130_fd_sc_hd__edfxtp_1 \storage[5][1]$_DFFE_PP_  (.D(net10),
    .DE(net55),
    .Q(\storage[5][1] ),
    .CLK(clknet_4_7_0_clk));
 sky130_fd_sc_hd__edfxtp_1 \storage[5][2]$_DFFE_PP_  (.D(net11),
    .DE(net55),
    .Q(\storage[5][2] ),
    .CLK(clknet_4_12_0_clk));
 sky130_fd_sc_hd__edfxtp_1 \storage[5][3]$_DFFE_PP_  (.D(net12),
    .DE(net55),
    .Q(\storage[5][3] ),
    .CLK(clknet_4_13_0_clk));
 sky130_fd_sc_hd__edfxtp_1 \storage[5][4]$_DFFE_PP_  (.D(net13),
    .DE(net55),
    .Q(\storage[5][4] ),
    .CLK(clknet_4_15_0_clk));
 sky130_fd_sc_hd__edfxtp_1 \storage[5][5]$_DFFE_PP_  (.D(net14),
    .DE(net55),
    .Q(\storage[5][5] ),
    .CLK(clknet_4_15_0_clk));
 sky130_fd_sc_hd__edfxtp_1 \storage[5][6]$_DFFE_PP_  (.D(net15),
    .DE(net55),
    .Q(\storage[5][6] ),
    .CLK(clknet_4_14_0_clk));
 sky130_fd_sc_hd__edfxtp_1 \storage[5][7]$_DFFE_PP_  (.D(net16),
    .DE(net55),
    .Q(\storage[5][7] ),
    .CLK(clknet_4_9_0_clk));
 sky130_fd_sc_hd__edfxtp_1 \storage[5][8]$_DFFE_PP_  (.D(net17),
    .DE(net55),
    .Q(\storage[5][8] ),
    .CLK(clknet_4_11_0_clk));
 sky130_fd_sc_hd__edfxtp_1 \storage[5][9]$_DFFE_PP_  (.D(net18),
    .DE(net55),
    .Q(\storage[5][9] ),
    .CLK(clknet_4_8_0_clk));
 sky130_fd_sc_hd__edfxtp_1 \storage[6][0]$_DFFE_PP_  (.D(net3),
    .DE(_033_),
    .Q(\storage[6][0] ),
    .CLK(clknet_4_5_0_clk));
 sky130_fd_sc_hd__edfxtp_1 \storage[6][10]$_DFFE_PP_  (.D(net4),
    .DE(net53),
    .Q(\storage[6][10] ),
    .CLK(clknet_4_10_0_clk));
 sky130_fd_sc_hd__edfxtp_1 \storage[6][11]$_DFFE_PP_  (.D(net5),
    .DE(net53),
    .Q(\storage[6][11] ),
    .CLK(clknet_4_9_0_clk));
 sky130_fd_sc_hd__edfxtp_1 \storage[6][12]$_DFFE_PP_  (.D(net6),
    .DE(net53),
    .Q(\storage[6][12] ),
    .CLK(clknet_4_2_0_clk));
 sky130_fd_sc_hd__edfxtp_1 \storage[6][13]$_DFFE_PP_  (.D(net7),
    .DE(net53),
    .Q(\storage[6][13] ),
    .CLK(clknet_4_1_0_clk));
 sky130_fd_sc_hd__edfxtp_1 \storage[6][14]$_DFFE_PP_  (.D(net8),
    .DE(net53),
    .Q(\storage[6][14] ),
    .CLK(clknet_4_0_0_clk));
 sky130_fd_sc_hd__edfxtp_1 \storage[6][15]$_DFFE_PP_  (.D(net9),
    .DE(_033_),
    .Q(\storage[6][15] ),
    .CLK(clknet_4_7_0_clk));
 sky130_fd_sc_hd__edfxtp_1 \storage[6][1]$_DFFE_PP_  (.D(net10),
    .DE(_033_),
    .Q(\storage[6][1] ),
    .CLK(clknet_4_7_0_clk));
 sky130_fd_sc_hd__edfxtp_1 \storage[6][2]$_DFFE_PP_  (.D(net11),
    .DE(_033_),
    .Q(\storage[6][2] ),
    .CLK(clknet_4_13_0_clk));
 sky130_fd_sc_hd__edfxtp_1 \storage[6][3]$_DFFE_PP_  (.D(net12),
    .DE(_033_),
    .Q(\storage[6][3] ),
    .CLK(clknet_4_13_0_clk));
 sky130_fd_sc_hd__edfxtp_1 \storage[6][4]$_DFFE_PP_  (.D(net13),
    .DE(_033_),
    .Q(\storage[6][4] ),
    .CLK(clknet_4_15_0_clk));
 sky130_fd_sc_hd__edfxtp_1 \storage[6][5]$_DFFE_PP_  (.D(net14),
    .DE(net53),
    .Q(\storage[6][5] ),
    .CLK(clknet_4_14_0_clk));
 sky130_fd_sc_hd__edfxtp_1 \storage[6][6]$_DFFE_PP_  (.D(net15),
    .DE(net53),
    .Q(\storage[6][6] ),
    .CLK(clknet_4_14_0_clk));
 sky130_fd_sc_hd__edfxtp_1 \storage[6][7]$_DFFE_PP_  (.D(net16),
    .DE(net53),
    .Q(\storage[6][7] ),
    .CLK(clknet_4_12_0_clk));
 sky130_fd_sc_hd__edfxtp_1 \storage[6][8]$_DFFE_PP_  (.D(net17),
    .DE(net53),
    .Q(\storage[6][8] ),
    .CLK(clknet_4_9_0_clk));
 sky130_fd_sc_hd__edfxtp_1 \storage[6][9]$_DFFE_PP_  (.D(net18),
    .DE(net53),
    .Q(\storage[6][9] ),
    .CLK(clknet_4_9_0_clk));
 sky130_fd_sc_hd__edfxtp_1 \storage[7][0]$_DFFE_PP_  (.D(net3),
    .DE(net54),
    .Q(\storage[7][0] ),
    .CLK(clknet_4_5_0_clk));
 sky130_fd_sc_hd__edfxtp_1 \storage[7][10]$_DFFE_PP_  (.D(net4),
    .DE(net54),
    .Q(\storage[7][10] ),
    .CLK(clknet_4_10_0_clk));
 sky130_fd_sc_hd__edfxtp_1 \storage[7][11]$_DFFE_PP_  (.D(net5),
    .DE(net54),
    .Q(\storage[7][11] ),
    .CLK(clknet_4_9_0_clk));
 sky130_fd_sc_hd__edfxtp_1 \storage[7][12]$_DFFE_PP_  (.D(net6),
    .DE(net54),
    .Q(\storage[7][12] ),
    .CLK(clknet_4_3_0_clk));
 sky130_fd_sc_hd__edfxtp_1 \storage[7][13]$_DFFE_PP_  (.D(net7),
    .DE(net54),
    .Q(\storage[7][13] ),
    .CLK(clknet_4_1_0_clk));
 sky130_fd_sc_hd__edfxtp_1 \storage[7][14]$_DFFE_PP_  (.D(net8),
    .DE(net54),
    .Q(\storage[7][14] ),
    .CLK(clknet_4_0_0_clk));
 sky130_fd_sc_hd__edfxtp_1 \storage[7][15]$_DFFE_PP_  (.D(net9),
    .DE(net54),
    .Q(\storage[7][15] ),
    .CLK(clknet_4_4_0_clk));
 sky130_fd_sc_hd__edfxtp_1 \storage[7][1]$_DFFE_PP_  (.D(net10),
    .DE(net54),
    .Q(\storage[7][1] ),
    .CLK(clknet_4_7_0_clk));
 sky130_fd_sc_hd__edfxtp_1 \storage[7][2]$_DFFE_PP_  (.D(net11),
    .DE(net54),
    .Q(\storage[7][2] ),
    .CLK(clknet_4_13_0_clk));
 sky130_fd_sc_hd__edfxtp_1 \storage[7][3]$_DFFE_PP_  (.D(net12),
    .DE(net54),
    .Q(\storage[7][3] ),
    .CLK(clknet_4_13_0_clk));
 sky130_fd_sc_hd__edfxtp_1 \storage[7][4]$_DFFE_PP_  (.D(net13),
    .DE(net54),
    .Q(\storage[7][4] ),
    .CLK(clknet_4_15_0_clk));
 sky130_fd_sc_hd__edfxtp_1 \storage[7][5]$_DFFE_PP_  (.D(net14),
    .DE(net54),
    .Q(\storage[7][5] ),
    .CLK(clknet_4_15_0_clk));
 sky130_fd_sc_hd__edfxtp_1 \storage[7][6]$_DFFE_PP_  (.D(net15),
    .DE(net54),
    .Q(\storage[7][6] ),
    .CLK(clknet_4_14_0_clk));
 sky130_fd_sc_hd__edfxtp_1 \storage[7][7]$_DFFE_PP_  (.D(net16),
    .DE(net54),
    .Q(\storage[7][7] ),
    .CLK(clknet_4_9_0_clk));
 sky130_fd_sc_hd__edfxtp_1 \storage[7][8]$_DFFE_PP_  (.D(net17),
    .DE(net54),
    .Q(\storage[7][8] ),
    .CLK(clknet_4_9_0_clk));
 sky130_fd_sc_hd__edfxtp_1 \storage[7][9]$_DFFE_PP_  (.D(net18),
    .DE(net54),
    .Q(\storage[7][9] ),
    .CLK(clknet_4_8_0_clk));
 sky130_fd_sc_hd__dfrtp_1 \used[0]$_DFFE_PN0P_  (.D(_021_),
    .Q(\used[0] ),
    .RESET_B(net2),
    .CLK(clknet_4_0_0_clk));
 sky130_fd_sc_hd__dfrtp_1 \used[1]$_DFFE_PN0P_  (.D(_020_),
    .Q(\used[1] ),
    .RESET_B(net2),
    .CLK(clknet_4_0_0_clk));
 sky130_fd_sc_hd__dfrtp_1 \used[2]$_DFFE_PN0P_  (.D(_019_),
    .Q(\used[2] ),
    .RESET_B(net2),
    .CLK(clknet_4_1_0_clk));
 sky130_fd_sc_hd__dfrtp_1 \used[3]$_DFFE_PN0P_  (.D(_025_),
    .Q(\used[3] ),
    .RESET_B(net2),
    .CLK(clknet_4_1_0_clk));
 sky130_fd_sc_hd__dfrtp_1 \wptr[0]$_DFFE_PN0P_  (.D(_018_),
    .Q(\wptr[0] ),
    .RESET_B(net2),
    .CLK(clknet_4_4_0_clk));
 sky130_fd_sc_hd__dfrtp_1 \wptr[1]$_DFFE_PN0P_  (.D(_017_),
    .Q(\wptr[1] ),
    .RESET_B(net2),
    .CLK(clknet_4_4_0_clk));
 sky130_fd_sc_hd__dfrtp_1 \wptr[2]$_DFFE_PN0P_  (.D(_024_),
    .Q(\wptr[2] ),
    .RESET_B(net2),
    .CLK(clknet_4_1_0_clk));
endmodule
