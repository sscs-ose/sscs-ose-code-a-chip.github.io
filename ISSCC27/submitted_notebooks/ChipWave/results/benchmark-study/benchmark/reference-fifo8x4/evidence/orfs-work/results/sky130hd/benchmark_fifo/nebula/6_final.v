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
 output [7:0] rd_data;
 input [7:0] wr_data;

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
 wire _043_;
 wire _044_;
 wire _045_;
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
 wire _061_;
 wire _062_;
 wire _063_;
 wire _064_;
 wire _065_;
 wire _066_;
 wire _067_;
 wire _068_;
 wire _069_;
 wire _070_;
 wire _071_;
 wire _072_;
 wire _073_;
 wire _074_;
 wire _075_;
 wire _076_;
 wire _077_;
 wire _078_;
 wire _079_;
 wire _080_;
 wire _081_;
 wire _082_;
 wire _083_;
 wire _084_;
 wire _085_;
 wire _086_;
 wire _087_;
 wire _088_;
 wire _089_;
 wire _090_;
 wire _091_;
 wire _092_;
 wire _093_;
 wire _094_;
 wire _095_;
 wire _096_;
 wire _097_;
 wire _098_;
 wire _099_;
 wire _100_;
 wire _101_;
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
 wire _121_;
 wire _123_;
 wire _124_;
 wire _125_;
 wire _127_;
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
 wire net12;
 wire net13;
 wire net14;
 wire net15;
 wire net16;
 wire net17;
 wire net18;
 wire net19;
 wire net20;
 wire net21;
 wire net1;
 wire \rptr[0] ;
 wire \rptr[1] ;
 wire net2;
 wire \storage[0][0] ;
 wire \storage[0][1] ;
 wire \storage[0][2] ;
 wire \storage[0][3] ;
 wire \storage[0][4] ;
 wire \storage[0][5] ;
 wire \storage[0][6] ;
 wire \storage[0][7] ;
 wire \storage[1][0] ;
 wire \storage[1][1] ;
 wire \storage[1][2] ;
 wire \storage[1][3] ;
 wire \storage[1][4] ;
 wire \storage[1][5] ;
 wire \storage[1][6] ;
 wire \storage[1][7] ;
 wire \storage[2][0] ;
 wire \storage[2][1] ;
 wire \storage[2][2] ;
 wire \storage[2][3] ;
 wire \storage[2][4] ;
 wire \storage[2][5] ;
 wire \storage[2][6] ;
 wire \storage[2][7] ;
 wire \storage[3][0] ;
 wire \storage[3][1] ;
 wire \storage[3][2] ;
 wire \storage[3][3] ;
 wire \storage[3][4] ;
 wire \storage[3][5] ;
 wire \storage[3][6] ;
 wire \storage[3][7] ;
 wire \used[0] ;
 wire \used[1] ;
 wire \used[2] ;
 wire \wptr[0] ;
 wire \wptr[1] ;
 wire net3;
 wire net4;
 wire net5;
 wire net6;
 wire net7;
 wire net8;
 wire net9;
 wire net10;
 wire net11;
 wire clknet_0_clk;
 wire clknet_2_0__leaf_clk;
 wire clknet_2_1__leaf_clk;
 wire clknet_2_2__leaf_clk;
 wire clknet_2_3__leaf_clk;

 sky130_fd_sc_hd__inv_6 _142_ (.A(\rptr[0] ),
    .Y(_121_));
 sky130_fd_sc_hd__inv_1 _143_ (.A(\storage[0][4] ),
    .Y(_130_));
 sky130_fd_sc_hd__inv_1 _144_ (.A(\storage[0][0] ),
    .Y(_090_));
 sky130_fd_sc_hd__nand2_1 _145_ (.A(_121_),
    .B(_090_),
    .Y(_091_));
 sky130_fd_sc_hd__inv_1 _146_ (.A(\storage[1][0] ),
    .Y(_092_));
 sky130_fd_sc_hd__nand2_1 _147_ (.A(_092_),
    .B(\rptr[0] ),
    .Y(_093_));
 sky130_fd_sc_hd__nand3_1 _148_ (.A(_091_),
    .B(_093_),
    .C(_134_),
    .Y(_094_));
 sky130_fd_sc_hd__a21oi_1 _149_ (.A1(_089_),
    .A2(_094_),
    .B1(net12),
    .Y(net14));
 sky130_fd_sc_hd__inv_1 _150_ (.A(\storage[2][3] ),
    .Y(_095_));
 sky130_fd_sc_hd__nand2_2 _151_ (.A(_121_),
    .B(_095_),
    .Y(_096_));
 sky130_fd_sc_hd__inv_1 _152_ (.A(\storage[3][3] ),
    .Y(_097_));
 sky130_fd_sc_hd__nand2_1 _153_ (.A(_097_),
    .B(\rptr[0] ),
    .Y(_098_));
 sky130_fd_sc_hd__nand2_2 _154_ (.A(_121_),
    .B(_130_),
    .Y(_131_));
 sky130_fd_sc_hd__nand3_1 _155_ (.A(_096_),
    .B(_098_),
    .C(\rptr[1] ),
    .Y(_099_));
 sky130_fd_sc_hd__inv_1 _156_ (.A(\storage[0][3] ),
    .Y(_100_));
 sky130_fd_sc_hd__nand2_1 _157_ (.A(_121_),
    .B(_100_),
    .Y(_101_));
 sky130_fd_sc_hd__inv_1 _158_ (.A(\storage[1][3] ),
    .Y(_102_));
 sky130_fd_sc_hd__nand2_1 _159_ (.A(_102_),
    .B(\rptr[0] ),
    .Y(_103_));
 sky130_fd_sc_hd__nand3_1 _160_ (.A(_101_),
    .B(_103_),
    .C(_134_),
    .Y(_104_));
 sky130_fd_sc_hd__a21oi_1 _161_ (.A1(_099_),
    .A2(_104_),
    .B1(net12),
    .Y(net17));
 sky130_fd_sc_hd__inv_1 _162_ (.A(\wptr[1] ),
    .Y(_007_));
 sky130_fd_sc_hd__nand2_1 _163_ (.A(_030_),
    .B(\rptr[0] ),
    .Y(_105_));
 sky130_fd_sc_hd__nand3_1 _164_ (.A(_137_),
    .B(_121_),
    .C(net1),
    .Y(_106_));
 sky130_fd_sc_hd__inv_1 _165_ (.A(\storage[1][4] ),
    .Y(_132_));
 sky130_fd_sc_hd__nand2_1 _166_ (.A(_105_),
    .B(_106_),
    .Y(_019_));
 sky130_fd_sc_hd__xnor2_1 _167_ (.A(_015_),
    .B(\used[0] ),
    .Y(_018_));
 sky130_fd_sc_hd__nand2_1 _168_ (.A(_015_),
    .B(\used[1] ),
    .Y(_107_));
 sky130_fd_sc_hd__o21ai_0 _169_ (.A1(_004_),
    .A2(_015_),
    .B1(_107_),
    .Y(_017_));
 sky130_fd_sc_hd__inv_1 _170_ (.A(\wptr[0] ),
    .Y(_006_));
 sky130_fd_sc_hd__nand2_1 _171_ (.A(_013_),
    .B(\wptr[0] ),
    .Y(_108_));
 sky130_fd_sc_hd__nand3_1 _172_ (.A(_027_),
    .B(net11),
    .C(_006_),
    .Y(_109_));
 sky130_fd_sc_hd__nand2_1 _173_ (.A(_108_),
    .B(_109_),
    .Y(_016_));
 sky130_fd_sc_hd__inv_1 _174_ (.A(\storage[2][2] ),
    .Y(_110_));
 sky130_fd_sc_hd__nand2_2 _175_ (.A(_110_),
    .B(_121_),
    .Y(_111_));
 sky130_fd_sc_hd__nand2_1 _176_ (.A(_132_),
    .B(\rptr[0] ),
    .Y(_133_));
 sky130_fd_sc_hd__inv_1 _177_ (.A(\storage[3][2] ),
    .Y(_112_));
 sky130_fd_sc_hd__nand2_1 _178_ (.A(_112_),
    .B(\rptr[0] ),
    .Y(_113_));
 sky130_fd_sc_hd__nand3_2 _179_ (.A(_111_),
    .B(_113_),
    .C(\rptr[1] ),
    .Y(_114_));
 sky130_fd_sc_hd__inv_1 _180_ (.A(\storage[0][2] ),
    .Y(_115_));
 sky130_fd_sc_hd__nand2_1 _181_ (.A(_121_),
    .B(_115_),
    .Y(_116_));
 sky130_fd_sc_hd__inv_1 _182_ (.A(\storage[1][2] ),
    .Y(_117_));
 sky130_fd_sc_hd__nand2_1 _183_ (.A(_117_),
    .B(\rptr[0] ),
    .Y(_118_));
 sky130_fd_sc_hd__nand3_1 _184_ (.A(_116_),
    .B(_118_),
    .C(_134_),
    .Y(_119_));
 sky130_fd_sc_hd__a21oi_2 _185_ (.A1(_114_),
    .A2(_119_),
    .B1(net12),
    .Y(net16));
 sky130_fd_sc_hd__inv_1 _186_ (.A(\rptr[1] ),
    .Y(_134_));
 sky130_fd_sc_hd__nand3_2 _187_ (.A(_131_),
    .B(_133_),
    .C(_134_),
    .Y(_135_));
 sky130_fd_sc_hd__inv_1 _188_ (.A(\used[2] ),
    .Y(_136_));
 sky130_fd_sc_hd__inv_1 _189_ (.A(\used[1] ),
    .Y(_001_));
 sky130_fd_sc_hd__inv_2 _190_ (.A(\used[0] ),
    .Y(_000_));
 sky130_fd_sc_hd__nand3_1 _191_ (.A(_136_),
    .B(_001_),
    .C(_000_),
    .Y(_137_));
 sky130_fd_sc_hd__inv_2 _193_ (.A(_137_),
    .Y(net12));
 sky130_fd_sc_hd__a21oi_2 _194_ (.A1(_129_),
    .A2(_135_),
    .B1(net12),
    .Y(net18));
 sky130_fd_sc_hd__nand3_1 _195_ (.A(_001_),
    .B(_000_),
    .C(\used[2] ),
    .Y(_027_));
 sky130_fd_sc_hd__inv_1 _196_ (.A(_027_),
    .Y(net13));
 sky130_fd_sc_hd__inv_1 _197_ (.A(_012_),
    .Y(_028_));
 sky130_fd_sc_hd__nand3_1 _198_ (.A(_027_),
    .B(net11),
    .C(net2),
    .Y(_029_));
 sky130_fd_sc_hd__nor2_1 _199_ (.A(_028_),
    .B(_029_),
    .Y(_026_));
 sky130_fd_sc_hd__nand2_1 _200_ (.A(_137_),
    .B(net1),
    .Y(_030_));
 sky130_fd_sc_hd__inv_1 _201_ (.A(_030_),
    .Y(_014_));
 sky130_fd_sc_hd__xnor2_1 _202_ (.A(\rptr[1] ),
    .B(\rptr[0] ),
    .Y(_031_));
 sky130_fd_sc_hd__inv_1 _203_ (.A(\storage[2][4] ),
    .Y(_123_));
 sky130_fd_sc_hd__nand2_1 _204_ (.A(_030_),
    .B(\rptr[1] ),
    .Y(_032_));
 sky130_fd_sc_hd__o21ai_0 _205_ (.A1(_031_),
    .A2(_030_),
    .B1(_032_),
    .Y(_022_));
 sky130_fd_sc_hd__inv_1 _206_ (.A(_003_),
    .Y(_033_));
 sky130_fd_sc_hd__nand2_1 _207_ (.A(_033_),
    .B(_005_),
    .Y(_034_));
 sky130_fd_sc_hd__inv_1 _208_ (.A(_005_),
    .Y(_002_));
 sky130_fd_sc_hd__nand2_1 _209_ (.A(_002_),
    .B(_003_),
    .Y(_035_));
 sky130_fd_sc_hd__inv_1 _210_ (.A(_015_),
    .Y(_036_));
 sky130_fd_sc_hd__nand3_1 _211_ (.A(_034_),
    .B(_035_),
    .C(_036_),
    .Y(_037_));
 sky130_fd_sc_hd__nand2_1 _212_ (.A(_037_),
    .B(\used[2] ),
    .Y(_038_));
 sky130_fd_sc_hd__nand4_1 _213_ (.A(_034_),
    .B(_035_),
    .C(_136_),
    .D(_036_),
    .Y(_039_));
 sky130_fd_sc_hd__nand2_1 _214_ (.A(_121_),
    .B(_123_),
    .Y(_124_));
 sky130_fd_sc_hd__nand2_1 _215_ (.A(_038_),
    .B(_039_),
    .Y(_021_));
 sky130_fd_sc_hd__nand2_1 _216_ (.A(_027_),
    .B(net11),
    .Y(_013_));
 sky130_fd_sc_hd__nand2_1 _217_ (.A(_013_),
    .B(\wptr[1] ),
    .Y(_040_));
 sky130_fd_sc_hd__nand3_1 _218_ (.A(_027_),
    .B(_009_),
    .C(net11),
    .Y(_041_));
 sky130_fd_sc_hd__nand2_1 _219_ (.A(_040_),
    .B(_041_),
    .Y(_020_));
 sky130_fd_sc_hd__inv_1 _220_ (.A(\storage[2][6] ),
    .Y(_042_));
 sky130_fd_sc_hd__nand2_2 _221_ (.A(_121_),
    .B(_042_),
    .Y(_043_));
 sky130_fd_sc_hd__inv_1 _222_ (.A(\storage[3][6] ),
    .Y(_044_));
 sky130_fd_sc_hd__nand2_1 _223_ (.A(_044_),
    .B(\rptr[0] ),
    .Y(_045_));
 sky130_fd_sc_hd__nand3_1 _224_ (.A(_043_),
    .B(_045_),
    .C(\rptr[1] ),
    .Y(_046_));
 sky130_fd_sc_hd__inv_1 _225_ (.A(\storage[3][4] ),
    .Y(_125_));
 sky130_fd_sc_hd__inv_1 _226_ (.A(\storage[0][6] ),
    .Y(_047_));
 sky130_fd_sc_hd__nand2_1 _227_ (.A(_121_),
    .B(_047_),
    .Y(_048_));
 sky130_fd_sc_hd__inv_1 _228_ (.A(\storage[1][6] ),
    .Y(_049_));
 sky130_fd_sc_hd__nand2_1 _229_ (.A(_049_),
    .B(\rptr[0] ),
    .Y(_050_));
 sky130_fd_sc_hd__nand3_1 _230_ (.A(_048_),
    .B(_050_),
    .C(_134_),
    .Y(_051_));
 sky130_fd_sc_hd__a21oi_1 _231_ (.A1(_046_),
    .A2(_051_),
    .B1(net12),
    .Y(net20));
 sky130_fd_sc_hd__inv_1 _232_ (.A(\storage[2][7] ),
    .Y(_052_));
 sky130_fd_sc_hd__nand2_2 _233_ (.A(_121_),
    .B(_052_),
    .Y(_053_));
 sky130_fd_sc_hd__inv_1 _234_ (.A(\storage[3][7] ),
    .Y(_054_));
 sky130_fd_sc_hd__nand2_1 _235_ (.A(_054_),
    .B(\rptr[0] ),
    .Y(_055_));
 sky130_fd_sc_hd__nand3_1 _237_ (.A(_053_),
    .B(_055_),
    .C(\rptr[1] ),
    .Y(_056_));
 sky130_fd_sc_hd__inv_1 _238_ (.A(\storage[0][7] ),
    .Y(_057_));
 sky130_fd_sc_hd__nand2_1 _239_ (.A(_121_),
    .B(_057_),
    .Y(_058_));
 sky130_fd_sc_hd__inv_1 _240_ (.A(\storage[1][7] ),
    .Y(_059_));
 sky130_fd_sc_hd__nand2_1 _241_ (.A(_059_),
    .B(\rptr[0] ),
    .Y(_060_));
 sky130_fd_sc_hd__nand3_1 _242_ (.A(_058_),
    .B(_060_),
    .C(_134_),
    .Y(_061_));
 sky130_fd_sc_hd__a21oi_1 _243_ (.A1(_056_),
    .A2(_061_),
    .B1(net12),
    .Y(net21));
 sky130_fd_sc_hd__inv_1 _244_ (.A(\storage[2][5] ),
    .Y(_062_));
 sky130_fd_sc_hd__nand2_2 _245_ (.A(_121_),
    .B(_062_),
    .Y(_063_));
 sky130_fd_sc_hd__inv_1 _246_ (.A(\storage[3][5] ),
    .Y(_064_));
 sky130_fd_sc_hd__nand2_1 _247_ (.A(_125_),
    .B(\rptr[0] ),
    .Y(_127_));
 sky130_fd_sc_hd__nand2_1 _248_ (.A(_064_),
    .B(\rptr[0] ),
    .Y(_065_));
 sky130_fd_sc_hd__nand3_1 _249_ (.A(_063_),
    .B(_065_),
    .C(\rptr[1] ),
    .Y(_066_));
 sky130_fd_sc_hd__inv_1 _250_ (.A(\storage[0][5] ),
    .Y(_067_));
 sky130_fd_sc_hd__nand2_1 _251_ (.A(_121_),
    .B(_067_),
    .Y(_068_));
 sky130_fd_sc_hd__inv_1 _252_ (.A(\storage[1][5] ),
    .Y(_069_));
 sky130_fd_sc_hd__nand2_1 _253_ (.A(_069_),
    .B(\rptr[0] ),
    .Y(_070_));
 sky130_fd_sc_hd__nand3_1 _254_ (.A(_068_),
    .B(_070_),
    .C(_134_),
    .Y(_071_));
 sky130_fd_sc_hd__a21oi_1 _255_ (.A1(_066_),
    .A2(_071_),
    .B1(net12),
    .Y(net19));
 sky130_fd_sc_hd__inv_1 _256_ (.A(_008_),
    .Y(_072_));
 sky130_fd_sc_hd__nor2_1 _257_ (.A(_072_),
    .B(_029_),
    .Y(_023_));
 sky130_fd_sc_hd__inv_1 _259_ (.A(_010_),
    .Y(_073_));
 sky130_fd_sc_hd__nor2_1 _260_ (.A(_073_),
    .B(_029_),
    .Y(_025_));
 sky130_fd_sc_hd__inv_1 _261_ (.A(_011_),
    .Y(_074_));
 sky130_fd_sc_hd__nor2_1 _262_ (.A(_074_),
    .B(_029_),
    .Y(_024_));
 sky130_fd_sc_hd__inv_1 _263_ (.A(\storage[2][1] ),
    .Y(_075_));
 sky130_fd_sc_hd__nand2_2 _264_ (.A(_121_),
    .B(_075_),
    .Y(_076_));
 sky130_fd_sc_hd__inv_1 _265_ (.A(\storage[3][1] ),
    .Y(_077_));
 sky130_fd_sc_hd__nand2_1 _266_ (.A(_077_),
    .B(\rptr[0] ),
    .Y(_078_));
 sky130_fd_sc_hd__nand3_1 _267_ (.A(_076_),
    .B(_078_),
    .C(\rptr[1] ),
    .Y(_079_));
 sky130_fd_sc_hd__inv_1 _268_ (.A(\storage[0][1] ),
    .Y(_080_));
 sky130_fd_sc_hd__nand3_1 _269_ (.A(_124_),
    .B(_127_),
    .C(\rptr[1] ),
    .Y(_129_));
 sky130_fd_sc_hd__nand2_1 _270_ (.A(_121_),
    .B(_080_),
    .Y(_081_));
 sky130_fd_sc_hd__inv_1 _271_ (.A(\storage[1][1] ),
    .Y(_082_));
 sky130_fd_sc_hd__nand2_1 _272_ (.A(_082_),
    .B(\rptr[0] ),
    .Y(_083_));
 sky130_fd_sc_hd__nand3_1 _273_ (.A(_081_),
    .B(_083_),
    .C(_134_),
    .Y(_084_));
 sky130_fd_sc_hd__a21oi_1 _274_ (.A1(_079_),
    .A2(_084_),
    .B1(net12),
    .Y(net15));
 sky130_fd_sc_hd__inv_1 _275_ (.A(\storage[2][0] ),
    .Y(_085_));
 sky130_fd_sc_hd__nand2_2 _276_ (.A(_121_),
    .B(_085_),
    .Y(_086_));
 sky130_fd_sc_hd__inv_1 _277_ (.A(\storage[3][0] ),
    .Y(_087_));
 sky130_fd_sc_hd__nand2_1 _278_ (.A(_087_),
    .B(\rptr[0] ),
    .Y(_088_));
 sky130_fd_sc_hd__nand3_1 _279_ (.A(_086_),
    .B(_088_),
    .C(\rptr[1] ),
    .Y(_089_));
 sky130_fd_sc_hd__fa_1 _280_ (.A(_000_),
    .B(_001_),
    .CIN(_002_),
    .COUT(_003_),
    .SUM(_004_));
 sky130_fd_sc_hd__ha_1 _281_ (.A(_006_),
    .B(_007_),
    .COUT(_008_),
    .SUM(_009_));
 sky130_fd_sc_hd__ha_1 _282_ (.A(_006_),
    .B(\wptr[1] ),
    .COUT(_010_),
    .SUM(_138_));
 sky130_fd_sc_hd__ha_1 _283_ (.A(\wptr[0] ),
    .B(_007_),
    .COUT(_011_),
    .SUM(_139_));
 sky130_fd_sc_hd__ha_1 _284_ (.A(\wptr[0] ),
    .B(\wptr[1] ),
    .COUT(_012_),
    .SUM(_140_));
 sky130_fd_sc_hd__ha_1 _285_ (.A(_013_),
    .B(_014_),
    .COUT(_005_),
    .SUM(_015_));
 sky130_fd_sc_hd__clkbuf_8 clkbuf_0_clk (.A(clk),
    .X(clknet_0_clk));
 sky130_fd_sc_hd__clkbuf_8 clkbuf_2_0__f_clk (.A(clknet_0_clk),
    .X(clknet_2_0__leaf_clk));
 sky130_fd_sc_hd__clkbuf_8 clkbuf_2_1__f_clk (.A(clknet_0_clk),
    .X(clknet_2_1__leaf_clk));
 sky130_fd_sc_hd__clkbuf_8 clkbuf_2_2__f_clk (.A(clknet_0_clk),
    .X(clknet_2_2__leaf_clk));
 sky130_fd_sc_hd__clkbuf_8 clkbuf_2_3__f_clk (.A(clknet_0_clk),
    .X(clknet_2_3__leaf_clk));
 sky130_fd_sc_hd__clkinv_2 clkload0 (.A(clknet_2_1__leaf_clk));
 sky130_fd_sc_hd__clkinv_2 clkload1 (.A(clknet_2_2__leaf_clk));
 sky130_fd_sc_hd__clkinv_2 clkload2 (.A(clknet_2_3__leaf_clk));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input1 (.A(rd_en),
    .X(net1));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input10 (.A(wr_data[7]),
    .X(net10));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input11 (.A(wr_en),
    .X(net11));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input2 (.A(rst_n),
    .X(net2));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input3 (.A(wr_data[0]),
    .X(net3));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input4 (.A(wr_data[1]),
    .X(net4));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input5 (.A(wr_data[2]),
    .X(net5));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input6 (.A(wr_data[3]),
    .X(net6));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input7 (.A(wr_data[4]),
    .X(net7));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input8 (.A(wr_data[5]),
    .X(net8));
 sky130_fd_sc_hd__clkdlybuf4s50_1 input9 (.A(wr_data[6]),
    .X(net9));
 sky130_fd_sc_hd__clkdlybuf4s50_1 output12 (.A(net12),
    .X(empty));
 sky130_fd_sc_hd__clkdlybuf4s50_1 output13 (.A(net13),
    .X(full));
 sky130_fd_sc_hd__clkdlybuf4s50_1 output14 (.A(net14),
    .X(rd_data[0]));
 sky130_fd_sc_hd__clkdlybuf4s50_1 output15 (.A(net15),
    .X(rd_data[1]));
 sky130_fd_sc_hd__clkdlybuf4s50_1 output16 (.A(net16),
    .X(rd_data[2]));
 sky130_fd_sc_hd__clkdlybuf4s50_1 output17 (.A(net17),
    .X(rd_data[3]));
 sky130_fd_sc_hd__clkdlybuf4s50_1 output18 (.A(net18),
    .X(rd_data[4]));
 sky130_fd_sc_hd__clkdlybuf4s50_1 output19 (.A(net19),
    .X(rd_data[5]));
 sky130_fd_sc_hd__clkdlybuf4s50_1 output20 (.A(net20),
    .X(rd_data[6]));
 sky130_fd_sc_hd__clkdlybuf4s50_1 output21 (.A(net21),
    .X(rd_data[7]));
 sky130_fd_sc_hd__dfrtp_1 \rptr[0]$_DFFE_PN0P_  (.D(_019_),
    .Q(\rptr[0] ),
    .RESET_B(net2),
    .CLK(clknet_2_3__leaf_clk));
 sky130_fd_sc_hd__dfrtp_1 \rptr[1]$_DFFE_PN0P_  (.D(_022_),
    .Q(\rptr[1] ),
    .RESET_B(net2),
    .CLK(clknet_2_3__leaf_clk));
 sky130_fd_sc_hd__edfxtp_1 \storage[0][0]$_DFFE_PP_  (.D(net3),
    .DE(_023_),
    .Q(\storage[0][0] ),
    .CLK(clknet_2_0__leaf_clk));
 sky130_fd_sc_hd__edfxtp_1 \storage[0][1]$_DFFE_PP_  (.D(net4),
    .DE(_023_),
    .Q(\storage[0][1] ),
    .CLK(clknet_2_0__leaf_clk));
 sky130_fd_sc_hd__edfxtp_1 \storage[0][2]$_DFFE_PP_  (.D(net5),
    .DE(_023_),
    .Q(\storage[0][2] ),
    .CLK(clknet_2_0__leaf_clk));
 sky130_fd_sc_hd__edfxtp_1 \storage[0][3]$_DFFE_PP_  (.D(net6),
    .DE(_023_),
    .Q(\storage[0][3] ),
    .CLK(clknet_2_0__leaf_clk));
 sky130_fd_sc_hd__edfxtp_1 \storage[0][4]$_DFFE_PP_  (.D(net7),
    .DE(_023_),
    .Q(\storage[0][4] ),
    .CLK(clknet_2_0__leaf_clk));
 sky130_fd_sc_hd__edfxtp_1 \storage[0][5]$_DFFE_PP_  (.D(net8),
    .DE(_023_),
    .Q(\storage[0][5] ),
    .CLK(clknet_2_0__leaf_clk));
 sky130_fd_sc_hd__edfxtp_1 \storage[0][6]$_DFFE_PP_  (.D(net9),
    .DE(_023_),
    .Q(\storage[0][6] ),
    .CLK(clknet_2_0__leaf_clk));
 sky130_fd_sc_hd__edfxtp_1 \storage[0][7]$_DFFE_PP_  (.D(net10),
    .DE(_023_),
    .Q(\storage[0][7] ),
    .CLK(clknet_2_0__leaf_clk));
 sky130_fd_sc_hd__edfxtp_1 \storage[1][0]$_DFFE_PP_  (.D(net3),
    .DE(_024_),
    .Q(\storage[1][0] ),
    .CLK(clknet_2_2__leaf_clk));
 sky130_fd_sc_hd__edfxtp_1 \storage[1][1]$_DFFE_PP_  (.D(net4),
    .DE(_024_),
    .Q(\storage[1][1] ),
    .CLK(clknet_2_2__leaf_clk));
 sky130_fd_sc_hd__edfxtp_1 \storage[1][2]$_DFFE_PP_  (.D(net5),
    .DE(_024_),
    .Q(\storage[1][2] ),
    .CLK(clknet_2_0__leaf_clk));
 sky130_fd_sc_hd__edfxtp_1 \storage[1][3]$_DFFE_PP_  (.D(net6),
    .DE(_024_),
    .Q(\storage[1][3] ),
    .CLK(clknet_2_2__leaf_clk));
 sky130_fd_sc_hd__edfxtp_1 \storage[1][4]$_DFFE_PP_  (.D(net7),
    .DE(_024_),
    .Q(\storage[1][4] ),
    .CLK(clknet_2_0__leaf_clk));
 sky130_fd_sc_hd__edfxtp_1 \storage[1][5]$_DFFE_PP_  (.D(net8),
    .DE(_024_),
    .Q(\storage[1][5] ),
    .CLK(clknet_2_2__leaf_clk));
 sky130_fd_sc_hd__edfxtp_1 \storage[1][6]$_DFFE_PP_  (.D(net9),
    .DE(_024_),
    .Q(\storage[1][6] ),
    .CLK(clknet_2_0__leaf_clk));
 sky130_fd_sc_hd__edfxtp_1 \storage[1][7]$_DFFE_PP_  (.D(net10),
    .DE(_024_),
    .Q(\storage[1][7] ),
    .CLK(clknet_2_0__leaf_clk));
 sky130_fd_sc_hd__edfxtp_1 \storage[2][0]$_DFFE_PP_  (.D(net3),
    .DE(_025_),
    .Q(\storage[2][0] ),
    .CLK(clknet_2_1__leaf_clk));
 sky130_fd_sc_hd__edfxtp_1 \storage[2][1]$_DFFE_PP_  (.D(net4),
    .DE(_025_),
    .Q(\storage[2][1] ),
    .CLK(clknet_2_1__leaf_clk));
 sky130_fd_sc_hd__edfxtp_1 \storage[2][2]$_DFFE_PP_  (.D(net5),
    .DE(_025_),
    .Q(\storage[2][2] ),
    .CLK(clknet_2_1__leaf_clk));
 sky130_fd_sc_hd__edfxtp_1 \storage[2][3]$_DFFE_PP_  (.D(net6),
    .DE(_025_),
    .Q(\storage[2][3] ),
    .CLK(clknet_2_1__leaf_clk));
 sky130_fd_sc_hd__edfxtp_1 \storage[2][4]$_DFFE_PP_  (.D(net7),
    .DE(_025_),
    .Q(\storage[2][4] ),
    .CLK(clknet_2_1__leaf_clk));
 sky130_fd_sc_hd__edfxtp_1 \storage[2][5]$_DFFE_PP_  (.D(net8),
    .DE(_025_),
    .Q(\storage[2][5] ),
    .CLK(clknet_2_1__leaf_clk));
 sky130_fd_sc_hd__edfxtp_1 \storage[2][6]$_DFFE_PP_  (.D(net9),
    .DE(_025_),
    .Q(\storage[2][6] ),
    .CLK(clknet_2_1__leaf_clk));
 sky130_fd_sc_hd__edfxtp_1 \storage[2][7]$_DFFE_PP_  (.D(net10),
    .DE(_025_),
    .Q(\storage[2][7] ),
    .CLK(clknet_2_1__leaf_clk));
 sky130_fd_sc_hd__edfxtp_1 \storage[3][0]$_DFFE_PP_  (.D(net3),
    .DE(_026_),
    .Q(\storage[3][0] ),
    .CLK(clknet_2_3__leaf_clk));
 sky130_fd_sc_hd__edfxtp_1 \storage[3][1]$_DFFE_PP_  (.D(net4),
    .DE(_026_),
    .Q(\storage[3][1] ),
    .CLK(clknet_2_2__leaf_clk));
 sky130_fd_sc_hd__edfxtp_1 \storage[3][2]$_DFFE_PP_  (.D(net5),
    .DE(_026_),
    .Q(\storage[3][2] ),
    .CLK(clknet_2_3__leaf_clk));
 sky130_fd_sc_hd__edfxtp_1 \storage[3][3]$_DFFE_PP_  (.D(net6),
    .DE(_026_),
    .Q(\storage[3][3] ),
    .CLK(clknet_2_3__leaf_clk));
 sky130_fd_sc_hd__edfxtp_1 \storage[3][4]$_DFFE_PP_  (.D(net7),
    .DE(_026_),
    .Q(\storage[3][4] ),
    .CLK(clknet_2_1__leaf_clk));
 sky130_fd_sc_hd__edfxtp_1 \storage[3][5]$_DFFE_PP_  (.D(net8),
    .DE(_026_),
    .Q(\storage[3][5] ),
    .CLK(clknet_2_3__leaf_clk));
 sky130_fd_sc_hd__edfxtp_1 \storage[3][6]$_DFFE_PP_  (.D(net9),
    .DE(_026_),
    .Q(\storage[3][6] ),
    .CLK(clknet_2_3__leaf_clk));
 sky130_fd_sc_hd__edfxtp_1 \storage[3][7]$_DFFE_PP_  (.D(net10),
    .DE(_026_),
    .Q(\storage[3][7] ),
    .CLK(clknet_2_3__leaf_clk));
 sky130_fd_sc_hd__dfrtp_1 \used[0]$_DFFE_PN0P_  (.D(_018_),
    .Q(\used[0] ),
    .RESET_B(net2),
    .CLK(clknet_2_2__leaf_clk));
 sky130_fd_sc_hd__dfrtp_1 \used[1]$_DFFE_PN0P_  (.D(_017_),
    .Q(\used[1] ),
    .RESET_B(net2),
    .CLK(clknet_2_2__leaf_clk));
 sky130_fd_sc_hd__dfrtp_1 \used[2]$_DFFE_PN0P_  (.D(_021_),
    .Q(\used[2] ),
    .RESET_B(net2),
    .CLK(clknet_2_3__leaf_clk));
 sky130_fd_sc_hd__dfrtp_1 \wptr[0]$_DFFE_PN0P_  (.D(_016_),
    .Q(\wptr[0] ),
    .RESET_B(net2),
    .CLK(clknet_2_2__leaf_clk));
 sky130_fd_sc_hd__dfrtp_1 \wptr[1]$_DFFE_PN0P_  (.D(_020_),
    .Q(\wptr[1] ),
    .RESET_B(net2),
    .CLK(clknet_2_2__leaf_clk));
endmodule
