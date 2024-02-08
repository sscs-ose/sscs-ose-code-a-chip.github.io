module MEMS1D_BUFG_512x32_wrapper (
	CLK,
	CEN,
	RDWEN,
	AS,
	AW,
	AC,
	D,
	BW,
	Q
);
	input CLK;
	input CEN;
	input RDWEN;
	input AS;
	input [5:0] AW;
	input [1:0] AC;
	input [31:0] D;
	input [31:0] BW;
	output wire [31:0] Q;
	/*
	wire DEEPSLEEP;
	wire POWERGATE;
	buf (DEEPSLEEP, 1'b0);
	buf (POWERGATE, 1'b0);
	wire T_BIST;
	wire T_LOGIC;
	wire T_CEN;
	wire T_RDWEN;
	wire T_DEEPSLEEP;
	wire T_POWEGATE;
	buf (T_BIST, 1'b0);
	buf (T_LOGIC, 1'b0);
	buf (T_CEN, 1'b0);
	buf (T_RDWEN, 1'b0);
	buf (T_DEEPSLEEP, 1'b0);
	wire T_POWERGATE;
	buf (T_POWERGATE, 1'b0);
	wire T_AS;
	buf (T_AS, 1'b0);
	wire [5:0] T_AW;
	buf (T_AW[0], 1'b0);
	buf (T_AW[1], 1'b0);
	buf (T_AW[2], 1'b0);
	buf (T_AW[3], 1'b0);
	buf (T_AW[4], 1'b0);
	buf (T_AW[5], 1'b0);
	wire [1:0] T_AC;
	buf (T_AC[0], 1'b0);
	buf (T_AC[1], 1'b0);
	wire [31:0] T_D;
	buf (T_D[0], 1'b0);
	buf (T_D[1], 1'b0);
	buf (T_D[2], 1'b0);
	buf (T_D[3], 1'b0);
	buf (T_D[4], 1'b0);
	buf (T_D[5], 1'b0);
	buf (T_D[6], 1'b0);
	buf (T_D[7], 1'b0);
	buf (T_D[8], 1'b0);
	buf (T_D[9], 1'b0);
	buf (T_D[10], 1'b0);
	buf (T_D[11], 1'b0);
	buf (T_D[12], 1'b0);
	buf (T_D[13], 1'b0);
	buf (T_D[14], 1'b0);
	buf (T_D[15], 1'b0);
	buf (T_D[16], 1'b0);
	buf (T_D[17], 1'b0);
	buf (T_D[18], 1'b0);
	buf (T_D[19], 1'b0);
	buf (T_D[20], 1'b0);
	buf (T_D[21], 1'b0);
	buf (T_D[22], 1'b0);
	buf (T_D[23], 1'b0);
	buf (T_D[24], 1'b0);
	buf (T_D[25], 1'b0);
	buf (T_D[26], 1'b0);
	buf (T_D[27], 1'b0);
	buf (T_D[28], 1'b0);
	buf (T_D[29], 1'b0);
	buf (T_D[30], 1'b0);
	buf (T_D[31], 1'b0);
	wire [31:0] T_BW;
	buf (T_BW[0], 1'b0);
	buf (T_BW[1], 1'b0);
	buf (T_BW[2], 1'b0);
	buf (T_BW[3], 1'b0);
	buf (T_BW[4], 1'b0);
	buf (T_BW[5], 1'b0);
	buf (T_BW[6], 1'b0);
	buf (T_BW[7], 1'b0);
	buf (T_BW[8], 1'b0);
	buf (T_BW[9], 1'b0);
	buf (T_BW[10], 1'b0);
	buf (T_BW[11], 1'b0);
	buf (T_BW[12], 1'b0);
	buf (T_BW[13], 1'b0);
	buf (T_BW[14], 1'b0);
	buf (T_BW[15], 1'b0);
	buf (T_BW[16], 1'b0);
	buf (T_BW[17], 1'b0);
	buf (T_BW[18], 1'b0);
	buf (T_BW[19], 1'b0);
	buf (T_BW[20], 1'b0);
	buf (T_BW[21], 1'b0);
	buf (T_BW[22], 1'b0);
	buf (T_BW[23], 1'b0);
	buf (T_BW[24], 1'b0);
	buf (T_BW[25], 1'b0);
	buf (T_BW[26], 1'b0);
	buf (T_BW[27], 1'b0);
	buf (T_BW[28], 1'b0);
	buf (T_BW[29], 1'b0);
	buf (T_BW[30], 1'b0);
	buf (T_BW[31], 1'b0);
	wire T_WBT;
	wire T_STAB;
	buf (T_WBT, 1'b0);
	buf (T_STAB, 1'b0);
	wire [1:0] MA_SAWL;
	buf (MA_SAWL[0], 1'b1);
	buf (MA_SAWL[1], 1'b1);
	wire [1:0] MA_WL;
	buf (MA_WL[0], 1'b0);
	buf (MA_WL[1], 1'b0);
	wire [1:0] MA_WRAS;
	buf (MA_WRAS[0], 1'b0);
	buf (MA_WRAS[1], 1'b1);
	wire MA_WRASD;
	wire RBE;
	wire QRB;
	wire OBSV_CTL;
	buf (MA_WRASD, 1'b0);
	buf (RBE, 1'b0);
	wire [6:0] RBF0A;
	buf (RBF0A[0], 1'b0);
	buf (RBF0A[1], 1'b0);
	buf (RBF0A[2], 1'b0);
	buf (RBF0A[3], 1'b0);
	buf (RBF0A[4], 1'b0);
	buf (RBF0A[5], 1'b0);
	buf (RBF0A[6], 1'b0);
	*/

        wire spare_wen0_s;
	buf (spare_wen0_s, 1'b0);
	sky130_sram_1rw_32x512_32 I1(
		.clk0(CLK),
		.csb0(CEN),
		.web0(RDWEN),
		.addr0({1'b0,AS,AW,AC}),
		.din0(D),
		.dout0(Q)
	);
	/*
	MEMS1D_BUFG_512x32 I1(
		.CLK(CLK),
		.CEN(CEN),
		.RDWEN(RDWEN),
		.DEEPSLEEP(DEEPSLEEP),
		.POWERGATE(POWERGATE),
		.AS(AS),
		.AW(AW),
		.AC(AC),
		.D(D),
		.BW(BW),
		.T_BIST(T_BIST),
		.T_LOGIC(T_LOGIC),
		.T_CEN(T_CEN),
		.T_RDWEN(T_RDWEN),
		.T_DEEPSLEEP(T_DEEPSLEEP),
		.T_POWERGATE(T_POWEGATE),
		.T_AS(T_AS),
		.T_AW(T_AW),
		.T_AC(T_AC),
		.T_D(T_D),
		.T_BW(T_BW),
		.T_WBT(T_WBT),
		.T_STAB(T_STAB),
		.MA_SAWL(MA_SAWL),
		.MA_WL(MA_WL),
		.MA_WRAS(MA_WRAS),
		.MA_WRASD(MA_WRASD),
		.RBE(RBE),
		.RBF0A(RBF0A),
		.QRB(QRB),
		.Q(Q),
		.OBSV_CTL(OBSV_CTL)
	);*/
endmodule
module MEMS1D_BUFG_1024x32_wrapper (
	CLK,
	CEN,
	RDWEN,
	AS,
	AW,
	AC,
	D,
	BW,
	Q
);
	input CLK;
	input CEN;
	input RDWEN;
	input AS;
	input [6:0] AW;
	input [1:0] AC;
	input [31:0] D;
	input [31:0] BW;
	output wire [31:0] Q;
	/*
	wire DEEPSLEEP;
	wire POWERGATE;
	buf (DEEPSLEEP, 1'b0);
	buf (POWERGATE, 1'b0);
	wire T_BIST;
	wire T_LOGIC;
	wire T_CEN;
	wire T_RDWEN;
	wire T_DEEPSLEEP;
	wire T_POWEGATE;
	buf (T_BIST, 1'b0);
	buf (T_LOGIC, 1'b0);
	buf (T_CEN, 1'b0);
	buf (T_RDWEN, 1'b0);
	buf (T_DEEPSLEEP, 1'b0);
	wire T_POWERGATE;
	buf (T_POWERGATE, 1'b0);
	wire T_AS;
	buf (T_AS, 1'b0);
	wire [6:0] T_AW;
	buf (T_AW[0], 1'b0);
	buf (T_AW[1], 1'b0);
	buf (T_AW[2], 1'b0);
	buf (T_AW[3], 1'b0);
	buf (T_AW[4], 1'b0);
	buf (T_AW[5], 1'b0);
	buf (T_AW[6], 1'b0);
	wire [1:0] T_AC;
	buf (T_AC[0], 1'b0);
	buf (T_AC[1], 1'b0);
	wire [31:0] T_D;
	buf (T_D[0], 1'b0);
	buf (T_D[1], 1'b0);
	buf (T_D[2], 1'b0);
	buf (T_D[3], 1'b0);
	buf (T_D[4], 1'b0);
	buf (T_D[5], 1'b0);
	buf (T_D[6], 1'b0);
	buf (T_D[7], 1'b0);
	buf (T_D[8], 1'b0);
	buf (T_D[9], 1'b0);
	buf (T_D[10], 1'b0);
	buf (T_D[11], 1'b0);
	buf (T_D[12], 1'b0);
	buf (T_D[13], 1'b0);
	buf (T_D[14], 1'b0);
	buf (T_D[15], 1'b0);
	buf (T_D[16], 1'b0);
	buf (T_D[17], 1'b0);
	buf (T_D[18], 1'b0);
	buf (T_D[19], 1'b0);
	buf (T_D[20], 1'b0);
	buf (T_D[21], 1'b0);
	buf (T_D[22], 1'b0);
	buf (T_D[23], 1'b0);
	buf (T_D[24], 1'b0);
	buf (T_D[25], 1'b0);
	buf (T_D[26], 1'b0);
	buf (T_D[27], 1'b0);
	buf (T_D[28], 1'b0);
	buf (T_D[29], 1'b0);
	buf (T_D[30], 1'b0);
	buf (T_D[31], 1'b0);
	wire [31:0] T_BW;
	buf (T_BW[0], 1'b0);
	buf (T_BW[1], 1'b0);
	buf (T_BW[2], 1'b0);
	buf (T_BW[3], 1'b0);
	buf (T_BW[4], 1'b0);
	buf (T_BW[5], 1'b0);
	buf (T_BW[6], 1'b0);
	buf (T_BW[7], 1'b0);
	buf (T_BW[8], 1'b0);
	buf (T_BW[9], 1'b0);
	buf (T_BW[10], 1'b0);
	buf (T_BW[11], 1'b0);
	buf (T_BW[12], 1'b0);
	buf (T_BW[13], 1'b0);
	buf (T_BW[14], 1'b0);
	buf (T_BW[15], 1'b0);
	buf (T_BW[16], 1'b0);
	buf (T_BW[17], 1'b0);
	buf (T_BW[18], 1'b0);
	buf (T_BW[19], 1'b0);
	buf (T_BW[20], 1'b0);
	buf (T_BW[21], 1'b0);
	buf (T_BW[22], 1'b0);
	buf (T_BW[23], 1'b0);
	buf (T_BW[24], 1'b0);
	buf (T_BW[25], 1'b0);
	buf (T_BW[26], 1'b0);
	buf (T_BW[27], 1'b0);
	buf (T_BW[28], 1'b0);
	buf (T_BW[29], 1'b0);
	buf (T_BW[30], 1'b0);
	buf (T_BW[31], 1'b0);
	wire T_WBT;
	wire T_STAB;
	buf (T_WBT, 1'b0);
	buf (T_STAB, 1'b0);
	wire [1:0] MA_SAWL;
	buf (MA_SAWL[0], 1'b1);
	buf (MA_SAWL[1], 1'b1);
	wire [1:0] MA_WL;
	buf (MA_WL[0], 1'b0);
	buf (MA_WL[1], 1'b0);
	wire [1:0] MA_WRAS;
	buf (MA_WRAS[0], 1'b0);
	buf (MA_WRAS[1], 1'b1);
	wire MA_WRASD;
	wire RBE;
	wire QRB;
	wire OBSV_CTL;
	buf (MA_WRASD, 1'b0);
	buf (RBE, 1'b0);
	wire [6:0] RBF0A;
	buf (RBF0A[0], 1'b0);
	buf (RBF0A[1], 1'b0);
	buf (RBF0A[2], 1'b0);
	buf (RBF0A[3], 1'b0);
	buf (RBF0A[4], 1'b0);
	buf (RBF0A[5], 1'b0);
	buf (RBF0A[6], 1'b0);
        wire spare_wen0_s;
        buf (spare_wen0_s, 1'b0);*/

        sky130_sram_1rw_32x1024_32 I1(
	        .clk0(CLK),
	        .csb0(CEN),
	        .web0(RDWEN),
	        .addr0({1'b0,AS,AW,AC}),
	        .din0(D),
	        .dout0(Q)
	);
/*
	MEMS1D_BUFG_1024x32 I1(
		.CLK(CLK),
		.CEN(CEN),
		.RDWEN(RDWEN),
		.DEEPSLEEP(DEEPSLEEP),
		.POWERGATE(POWERGATE),
		.AS(AS),
		.AW(AW),
		.AC(AC),
		.D(D),
		.BW(BW),
		.T_BIST(T_BIST),
		.T_LOGIC(T_LOGIC),
		.T_CEN(T_CEN),
		.T_RDWEN(T_RDWEN),
		.T_DEEPSLEEP(T_DEEPSLEEP),
		.T_POWERGATE(T_POWEGATE),
		.T_AS(T_AS),
		.T_AW(T_AW),
		.T_AC(T_AC),
		.T_D(T_D),
		.T_BW(T_BW),
		.T_WBT(T_WBT),
		.T_STAB(T_STAB),
		.MA_SAWL(MA_SAWL),
		.MA_WL(MA_WL),
		.MA_WRAS(MA_WRAS),
		.MA_WRASD(MA_WRASD),
		.RBE(RBE),
		.RBF0A(RBF0A),
		.QRB(QRB),
		.Q(Q),
		.OBSV_CTL(OBSV_CTL)
	);*/
endmodule
module MEMS1D_BUFG_2048x32_wrapper (
	CLK,
	CEN,
	RDWEN,
	AS,
	AW,
	AC,
	D,
	BW,
	Q
);
	input CLK;
	input CEN;
	input RDWEN;
	input [1:0] AS;
	input [6:0] AW;
	input [1:0] AC;
	input [31:0] D;
	input [31:0] BW;
	output wire [31:0] Q;
	/*
	wire DEEPSLEEP;
	wire POWERGATE;
	buf (DEEPSLEEP, 1'b0);
	buf (POWERGATE, 1'b0);
	wire T_BIST;
	wire T_LOGIC;
	wire T_CEN;
	wire T_RDWEN;
	wire T_DEEPSLEEP;
	wire T_POWEGATE;
	buf (T_BIST, 1'b0);
	buf (T_LOGIC, 1'b0);
	buf (T_CEN, 1'b0);
	buf (T_RDWEN, 1'b0);
	buf (T_DEEPSLEEP, 1'b0);
	wire T_POWERGATE;
	buf (T_POWERGATE, 1'b0);
	wire [1:0] T_AS;
	buf (T_AS[0], 1'b0);
	buf (T_AS[1], 1'b0);
	wire [6:0] T_AW;
	buf (T_AW[0], 1'b0);
	buf (T_AW[1], 1'b0);
	buf (T_AW[2], 1'b0);
	buf (T_AW[3], 1'b0);
	buf (T_AW[4], 1'b0);
	buf (T_AW[5], 1'b0);
	buf (T_AW[6], 1'b0);
	wire [1:0] T_AC;
	buf (T_AC[0], 1'b0);
	buf (T_AC[1], 1'b0);
	wire [31:0] T_D;
	buf (T_D[0], 1'b0);
	buf (T_D[1], 1'b0);
	buf (T_D[2], 1'b0);
	buf (T_D[3], 1'b0);
	buf (T_D[4], 1'b0);
	buf (T_D[5], 1'b0);
	buf (T_D[6], 1'b0);
	buf (T_D[7], 1'b0);
	buf (T_D[8], 1'b0);
	buf (T_D[9], 1'b0);
	buf (T_D[10], 1'b0);
	buf (T_D[11], 1'b0);
	buf (T_D[12], 1'b0);
	buf (T_D[13], 1'b0);
	buf (T_D[14], 1'b0);
	buf (T_D[15], 1'b0);
	buf (T_D[16], 1'b0);
	buf (T_D[17], 1'b0);
	buf (T_D[18], 1'b0);
	buf (T_D[19], 1'b0);
	buf (T_D[20], 1'b0);
	buf (T_D[21], 1'b0);
	buf (T_D[22], 1'b0);
	buf (T_D[23], 1'b0);
	buf (T_D[24], 1'b0);
	buf (T_D[25], 1'b0);
	buf (T_D[26], 1'b0);
	buf (T_D[27], 1'b0);
	buf (T_D[28], 1'b0);
	buf (T_D[29], 1'b0);
	buf (T_D[30], 1'b0);
	buf (T_D[31], 1'b0);
	wire [31:0] T_BW;
	buf (T_BW[0], 1'b0);
	buf (T_BW[1], 1'b0);
	buf (T_BW[2], 1'b0);
	buf (T_BW[3], 1'b0);
	buf (T_BW[4], 1'b0);
	buf (T_BW[5], 1'b0);
	buf (T_BW[6], 1'b0);
	buf (T_BW[7], 1'b0);
	buf (T_BW[8], 1'b0);
	buf (T_BW[9], 1'b0);
	buf (T_BW[10], 1'b0);
	buf (T_BW[11], 1'b0);
	buf (T_BW[12], 1'b0);
	buf (T_BW[13], 1'b0);
	buf (T_BW[14], 1'b0);
	buf (T_BW[15], 1'b0);
	buf (T_BW[16], 1'b0);
	buf (T_BW[17], 1'b0);
	buf (T_BW[18], 1'b0);
	buf (T_BW[19], 1'b0);
	buf (T_BW[20], 1'b0);
	buf (T_BW[21], 1'b0);
	buf (T_BW[22], 1'b0);
	buf (T_BW[23], 1'b0);
	buf (T_BW[24], 1'b0);
	buf (T_BW[25], 1'b0);
	buf (T_BW[26], 1'b0);
	buf (T_BW[27], 1'b0);
	buf (T_BW[28], 1'b0);
	buf (T_BW[29], 1'b0);
	buf (T_BW[30], 1'b0);
	buf (T_BW[31], 1'b0);
	wire T_WBT;
	wire T_STAB;
	buf (T_WBT, 1'b0);
	buf (T_STAB, 1'b0);
	wire [1:0] MA_SAWL;
	buf (MA_SAWL[0], 1'b1);
	buf (MA_SAWL[1], 1'b1);
	wire [1:0] MA_WL;
	buf (MA_WL[0], 1'b0);
	buf (MA_WL[1], 1'b0);
	wire [1:0] MA_WRAS;
	buf (MA_WRAS[0], 1'b0);
	buf (MA_WRAS[1], 1'b1);
	wire MA_WRASD;
	wire RBE;
	wire QRB;
	wire OBSV_CTL;
	buf (MA_WRASD, 1'b0);
	buf (RBE, 1'b0);
	wire [6:0] RBF0A;
	buf (RBF0A[0], 1'b0);
	buf (RBF0A[1], 1'b0);
	buf (RBF0A[2], 1'b0);
	buf (RBF0A[3], 1'b0);
	buf (RBF0A[4], 1'b0);
	buf (RBF0A[5], 1'b0);
	buf (RBF0A[6], 1'b0);
	MEMS1D_BUFG_2048x32 I1(
		.CLK(CLK),
		.CEN(CEN),
		.RDWEN(RDWEN),
		.DEEPSLEEP(DEEPSLEEP),
		.POWERGATE(POWERGATE),
		.AS(AS),
		.AW(AW),
		.AC(AC),
		.D(D),
		.BW(BW),
		.T_BIST(T_BIST),
		.T_LOGIC(T_LOGIC),
		.T_CEN(T_CEN),
		.T_RDWEN(T_RDWEN),
		.T_DEEPSLEEP(T_DEEPSLEEP),
		.T_POWERGATE(T_POWEGATE),
		.T_AS(T_AS),
		.T_AW(T_AW),
		.T_AC(T_AC),
		.T_D(T_D),
		.T_BW(T_BW),
		.T_WBT(T_WBT),
		.T_STAB(T_STAB),
		.MA_SAWL(MA_SAWL),
		.MA_WL(MA_WL),
		.MA_WRAS(MA_WRAS),
		.MA_WRASD(MA_WRASD),
		.RBE(RBE),
		.RBF0A(RBF0A),
		.QRB(QRB),
		.Q(Q),
		.OBSV_CTL(OBSV_CTL)
	);*/
        wire spare_wen0_s;
        buf (spare_wen0_s, 1'b0);
        sky130_sram_1rw_32x2048_32 I1(
	      .clk0(CLK),
	      .csb0(CEN),
	      .web0(RDWEN),
	      .addr0({1'b0,AS,AW,AC}),
	      .din0(D),
	      .dout0(Q)
	);

endmodule
module MEMS1D_BUFG_4096x32_wrapper (
	CLK,
	CEN,
	RDWEN,
	AS,
	AW,
	AC,
	D,
	BW,
	Q
);
	input CLK;
	input CEN;
	input RDWEN;
	input [2:0] AS;
	input [6:0] AW;
	input [1:0] AC;
	input [31:0] D;
	input [31:0] BW;
	output wire [31:0] Q;
	/*
	wire DEEPSLEEP;
	wire POWERGATE;
	buf (DEEPSLEEP, 1'b0);
	buf (POWERGATE, 1'b0);
	wire T_BIST;
	wire T_LOGIC;
	wire T_CEN;
	wire T_RDWEN;
	wire T_DEEPSLEEP;
	wire T_POWEGATE;
	buf (T_BIST, 1'b0);
	buf (T_LOGIC, 1'b0);
	buf (T_CEN, 1'b0);
	buf (T_RDWEN, 1'b0);
	buf (T_DEEPSLEEP, 1'b0);
	wire T_POWERGATE;
	buf (T_POWERGATE, 1'b0);
	wire [2:0] T_AS;
	buf (T_AS[0], 1'b0);
	buf (T_AS[1], 1'b0);
	buf (T_AS[2], 1'b0);
	wire [6:0] T_AW;
	buf (T_AW[0], 1'b0);
	buf (T_AW[1], 1'b0);
	buf (T_AW[2], 1'b0);
	buf (T_AW[3], 1'b0);
	buf (T_AW[4], 1'b0);
	buf (T_AW[5], 1'b0);
	buf (T_AW[6], 1'b0);
	wire [1:0] T_AC;
	buf (T_AC[0], 1'b0);
	buf (T_AC[1], 1'b0);
	wire [31:0] T_D;
	buf (T_D[0], 1'b0);
	buf (T_D[1], 1'b0);
	buf (T_D[2], 1'b0);
	buf (T_D[3], 1'b0);
	buf (T_D[4], 1'b0);
	buf (T_D[5], 1'b0);
	buf (T_D[6], 1'b0);
	buf (T_D[7], 1'b0);
	buf (T_D[8], 1'b0);
	buf (T_D[9], 1'b0);
	buf (T_D[10], 1'b0);
	buf (T_D[11], 1'b0);
	buf (T_D[12], 1'b0);
	buf (T_D[13], 1'b0);
	buf (T_D[14], 1'b0);
	buf (T_D[15], 1'b0);
	buf (T_D[16], 1'b0);
	buf (T_D[17], 1'b0);
	buf (T_D[18], 1'b0);
	buf (T_D[19], 1'b0);
	buf (T_D[20], 1'b0);
	buf (T_D[21], 1'b0);
	buf (T_D[22], 1'b0);
	buf (T_D[23], 1'b0);
	buf (T_D[24], 1'b0);
	buf (T_D[25], 1'b0);
	buf (T_D[26], 1'b0);
	buf (T_D[27], 1'b0);
	buf (T_D[28], 1'b0);
	buf (T_D[29], 1'b0);
	buf (T_D[30], 1'b0);
	buf (T_D[31], 1'b0);
	wire [31:0] T_BW;
	buf (T_BW[0], 1'b0);
	buf (T_BW[1], 1'b0);
	buf (T_BW[2], 1'b0);
	buf (T_BW[3], 1'b0);
	buf (T_BW[4], 1'b0);
	buf (T_BW[5], 1'b0);
	buf (T_BW[6], 1'b0);
	buf (T_BW[7], 1'b0);
	buf (T_BW[8], 1'b0);
	buf (T_BW[9], 1'b0);
	buf (T_BW[10], 1'b0);
	buf (T_BW[11], 1'b0);
	buf (T_BW[12], 1'b0);
	buf (T_BW[13], 1'b0);
	buf (T_BW[14], 1'b0);
	buf (T_BW[15], 1'b0);
	buf (T_BW[16], 1'b0);
	buf (T_BW[17], 1'b0);
	buf (T_BW[18], 1'b0);
	buf (T_BW[19], 1'b0);
	buf (T_BW[20], 1'b0);
	buf (T_BW[21], 1'b0);
	buf (T_BW[22], 1'b0);
	buf (T_BW[23], 1'b0);
	buf (T_BW[24], 1'b0);
	buf (T_BW[25], 1'b0);
	buf (T_BW[26], 1'b0);
	buf (T_BW[27], 1'b0);
	buf (T_BW[28], 1'b0);
	buf (T_BW[29], 1'b0);
	buf (T_BW[30], 1'b0);
	buf (T_BW[31], 1'b0);
	wire T_WBT;
	wire T_STAB;
	buf (T_WBT, 1'b0);
	buf (T_STAB, 1'b0);
	wire [1:0] MA_SAWL;
	buf (MA_SAWL[0], 1'b1);
	buf (MA_SAWL[1], 1'b1);
	wire [1:0] MA_WL;
	buf (MA_WL[0], 1'b0);
	buf (MA_WL[1], 1'b0);
	wire [1:0] MA_WRAS;
	buf (MA_WRAS[0], 1'b0);
	buf (MA_WRAS[1], 1'b1);
	wire MA_WRASD;
	wire RBE;
	wire QRB;
	wire OBSV_CTL;
	buf (MA_WRASD, 1'b0);
	buf (RBE, 1'b0);
	wire [6:0] RBF0A;
	buf (RBF0A[0], 1'b0);
	buf (RBF0A[1], 1'b0);
	buf (RBF0A[2], 1'b0);
	buf (RBF0A[3], 1'b0);
	buf (RBF0A[4], 1'b0);
	buf (RBF0A[5], 1'b0);
	buf (RBF0A[6], 1'b0);
	MEMS1D_BUFG_4096x32 I1(
		.CLK(CLK),
		.CEN(CEN),
		.RDWEN(RDWEN),
		.DEEPSLEEP(DEEPSLEEP),
		.POWERGATE(POWERGATE),
		.AS(AS),
		.AW(AW),
		.AC(AC),
		.D(D),
		.BW(BW),
		.T_BIST(T_BIST),
		.T_LOGIC(T_LOGIC),
		.T_CEN(T_CEN),
		.T_RDWEN(T_RDWEN),
		.T_DEEPSLEEP(T_DEEPSLEEP),
		.T_POWERGATE(T_POWEGATE),
		.T_AS(T_AS),
		.T_AW(T_AW),
		.T_AC(T_AC),
		.T_D(T_D),
		.T_BW(T_BW),
		.T_WBT(T_WBT),
		.T_STAB(T_STAB),
		.MA_SAWL(MA_SAWL),
		.MA_WL(MA_WL),
		.MA_WRAS(MA_WRAS),
		.MA_WRASD(MA_WRASD),
		.RBE(RBE),
		.RBF0A(RBF0A),
		.QRB(QRB),
		.Q(Q),
		.OBSV_CTL(OBSV_CTL)
	);*/

        wire spare_wen0_s;
        buf (spare_wen0_s, 1'b0);
        sky130_sram_1rw_32x4096_32 I1(
  	      .clk0(CLK),
              .csb0(CEN),
	      .web0(RDWEN),
	      .addr0({1'b0,AS,AW,AC}),
	      .din0(D),
	      .dout0(Q)
	);

endmodule
module MEMROMIU_FUN_wrapper (
	CLK,
	CEN,
	AS,
	AW,
	AC,
	Q
);
	input CLK;
	input CEN;
	input AS;
	input [4:0] AW;
	input [4:0] AC;
	output wire [31:0] Q;
	wire T_BIST;
	wire T_LOGIC;
	wire T_CEN;
	wire T_SCAN;
	wire T_SI;
	buf (T_BIST, 1'b0);
	buf (T_LOGIC, 1'b0);
	buf (T_CEN, 1'b0);
	buf (T_SCAN, 1'b0);
	buf (T_SI, 1'b0);
	wire T_AS;
	buf (T_AS, 1'b0);
	wire [4:0] T_AW;
	buf (T_AW[0], 1'b0);
	buf (T_AW[1], 1'b0);
	buf (T_AW[2], 1'b0);
	buf (T_AW[3], 1'b0);
	buf (T_AW[4], 1'b0);
	wire [4:0] T_AC;
	buf (T_AC[0], 1'b0);
	buf (T_AC[1], 1'b0);
	buf (T_AC[2], 1'b0);
	buf (T_AC[3], 1'b0);
	buf (T_AC[4], 1'b0);
	wire T_WBT;
	wire T_SO;
	buf (T_WBT, 1'b0);
	buf (T_SO, 1'b0);
	wire [1:0] MA_SAWL;
	buf (MA_SAWL[0], 1'b1);
	buf (MA_SAWL[1], 1'b1);
	wire MA_WL;
	buf (MA_WL, 1'b0);
	MEMROMIU_FUN I1(
		.CLK(CLK),
		.CEN(CEN),
		.AS(AS),
		.AW(AW),
		.AC(AC),
		.T_BIST(T_BIST),
		.T_LOGIC(T_LOGIC),
		.T_CEN(T_CEN),
		.T_SCAN(T_SCAN),
		.T_SI(T_SI),
		.T_AS(T_AS),
		.T_AW(T_AW),
		.T_AC(T_AC),
		.T_WBT(T_WBT),
		.MA_SAWL(MA_SAWL),
		.MA_WL(MA_WL),
		.Q(Q),
		.T_SO(T_SO)
	);
endmodule
