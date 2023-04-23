module M88_top (
	a,
	w,
	p,
	mode_8b,
	mode_4b,
	mode_2b
);
	input [7:0] a;
	input [7:0] w;
	input mode_8b;
	input mode_4b;
	input mode_2b;
	output wire [15:0] p;
	wire sout81;
	wire sout82;
	wire sout83;
	wire sout84;
	wire sout85;
	wire sout86;
	wire sout87;
	wire cout81;
	wire cout82;
	wire cout83;
	wire cout84;
	wire cout85;
	wire cout86;
	wire cout87;
	wire cout88;
	reg sin21;
	reg sin31;
	reg sin41;
	reg sin51;
	reg sin61;
	reg sin71;
	reg sin81;
	always @(*)
		case (1'b1)
			mode_8b: begin
				sin21 = 1'b1;
				sin31 = 1'b0;
				sin41 = 1'b0;
				sin51 = 1'b0;
				sin61 = 1'b0;
				sin71 = 1'b0;
				sin81 = 1'b0;
			end
			mode_4b: begin
				sin21 = 1'b0;
				sin31 = 1'b1;
				sin41 = 1'b0;
				sin51 = 1'b0;
				sin61 = 1'b1;
				sin71 = 1'b0;
				sin81 = 1'b0;
			end
			mode_2b: begin
				sin21 = 1'b0;
				sin31 = 1'b0;
				sin41 = 1'b1;
				sin51 = 1'b1;
				sin61 = 1'b0;
				sin71 = 1'b0;
				sin81 = 1'b0;
			end
		endcase
	M_88_0 M_88_0(
		.xr1(a[0]),
		.xr2(a[1]),
		.xr3(a[2]),
		.xr4(a[3]),
		.xr5(a[4]),
		.xr6(a[5]),
		.xr7(a[6]),
		.xr8(a[7]),
		.yc1(w[7]),
		.yc2(w[6]),
		.yc3(w[5]),
		.yc4(w[4]),
		.yc5(w[3]),
		.yc6(w[2]),
		.yc7(w[1]),
		.yc8(w[0]),
		.sin11(1'b0),
		.sin12(1'b0),
		.sin13(1'b0),
		.sin14(1'b0),
		.sin15(1'b0),
		.sin16(1'b0),
		.sin17(1'b0),
		.sin18(1'b0),
		.sin21(sin21),
		.sin31(sin31),
		.sin41(sin41),
		.sin51(sin51),
		.sin61(sin61),
		.sin71(sin71),
		.sin81(sin81),
		.cin11(1'b0),
		.cin12(1'b0),
		.cin13(1'b0),
		.cin14(1'b0),
		.cin15(1'b0),
		.cin16(1'b0),
		.cin17(1'b0),
		.cin18(1'b0),
		.mode_2b(mode_2b),
		.mode_4b(mode_4b),
		.mode_8b(mode_8b),
		.sout18(p[0]),
		.sout28(p[1]),
		.sout38(p[2]),
		.sout48(p[3]),
		.sout58(p[4]),
		.sout68(p[5]),
		.sout78(p[6]),
		.sout88(p[7]),
		.sout81(sout81),
		.sout82(sout82),
		.sout83(sout83),
		.sout84(sout84),
		.sout85(sout85),
		.sout86(sout86),
		.sout87(sout87),
		.cout81(cout81),
		.cout82(cout82),
		.cout83(cout83),
		.cout84(cout84),
		.cout85(cout85),
		.cout86(cout86),
		.cout87(cout87),
		.cout88(cout88)
	);
	M88_downAdder M88_downAdder(
		.s({sout81, sout82, sout83, sout84, sout85, sout86, sout87}),
		.c({cout81, cout82, cout83, cout84, cout85, cout86, cout87, cout88}),
		.mode_8b(mode_8b),
		.p_high(p[15:8])
	);
endmodule
module M_88_0 (
	xr1,
	xr2,
	xr3,
	xr4,
	xr5,
	xr6,
	xr7,
	xr8,
	yc1,
	yc2,
	yc3,
	yc4,
	yc5,
	yc6,
	yc7,
	yc8,
	sin11,
	sin12,
	sin13,
	sin14,
	sin15,
	sin16,
	sin17,
	sin18,
	sin21,
	sin31,
	sin41,
	sin51,
	sin61,
	sin71,
	sin81,
	cin11,
	cin12,
	cin13,
	cin14,
	cin15,
	cin16,
	cin17,
	cin18,
	sout18,
	sout28,
	sout38,
	sout48,
	sout58,
	sout68,
	sout78,
	sout88,
	sout81,
	sout82,
	sout83,
	sout84,
	sout85,
	sout86,
	sout87,
	cout81,
	cout82,
	cout83,
	cout84,
	cout85,
	cout86,
	cout87,
	cout88,
	mode_2b,
	mode_4b,
	mode_8b
);
	input xr1;
	input xr2;
	input xr3;
	input xr4;
	input xr5;
	input xr6;
	input xr7;
	input xr8;
	input yc1;
	input yc2;
	input yc3;
	input yc4;
	input yc5;
	input yc6;
	input yc7;
	input yc8;
	input sin11;
	input sin12;
	input sin13;
	input sin14;
	input sin15;
	input sin16;
	input sin17;
	input sin18;
	input sin21;
	input sin31;
	input sin41;
	input sin51;
	input sin61;
	input sin71;
	input sin81;
	input cin11;
	input cin12;
	input cin13;
	input cin14;
	input cin15;
	input cin16;
	input cin17;
	input cin18;
	input mode_2b;
	input mode_4b;
	input mode_8b;
	output wire sout18;
	output wire sout28;
	output wire sout38;
	output wire sout48;
	output wire sout58;
	output wire sout68;
	output wire sout78;
	output wire sout88;
	output wire sout81;
	output wire sout82;
	output wire sout83;
	output wire sout84;
	output wire sout85;
	output wire sout86;
	output wire sout87;
	output wire cout81;
	output wire cout82;
	output wire cout83;
	output wire cout84;
	output wire cout85;
	output wire cout86;
	output wire cout87;
	output wire cout88;
	wire c41_51;
	wire c42_52;
	wire c43_53;
	wire c44_54;
	wire c45_55;
	wire c46_56;
	wire c47_57;
	wire c48_58;
	wire s41_52;
	wire s42_53;
	wire s43_54;
	wire s44_55;
	wire s45_56;
	wire s46_57;
	wire s47_58;
	wire s14_25;
	wire s24_35;
	wire s34_45;
	wire s54_65;
	wire s64_75;
	wire s74_85;
	M_44_0 M_44_0(
		.xr1(xr1),
		.xr2(xr2),
		.xr3(xr3),
		.xr4(xr4),
		.yc1(yc1),
		.yc2(yc2),
		.yc3(yc3),
		.yc4(yc4),
		.sin11(sin11),
		.sin12(sin12),
		.sin13(sin13),
		.sin14(sin14),
		.sin21(sin21),
		.sin31(sin31),
		.sin41(sin41),
		.cin11(cin11),
		.cin12(cin12),
		.cin13(cin13),
		.cin14(cin14),
		.mode_2b(mode_2b),
		.mode_4b(mode_4b),
		.mode_8b(mode_8b),
		.sout14(s14_25),
		.sout24(s24_35),
		.sout34(s34_45),
		.sout44(s44_55),
		.sout41(s41_52),
		.sout42(s42_53),
		.sout43(s43_54),
		.cout41(c41_51),
		.cout42(c42_52),
		.cout43(c43_53),
		.cout44(c44_54)
	);
	M_44_4 M_44_4(
		.xr1(xr5),
		.xr2(xr6),
		.xr3(xr7),
		.xr4(xr8),
		.yc1(yc1),
		.yc2(yc2),
		.yc3(yc3),
		.yc4(yc4),
		.sin11(sin51),
		.sin12(s41_52),
		.sin13(s42_53),
		.sin14(s43_54),
		.sin21(sin61),
		.sin31(sin71),
		.sin41(sin81),
		.cin11(c41_51),
		.cin12(c42_52),
		.cin13(c43_53),
		.cin14(c44_54),
		.mode_2b(mode_2b),
		.mode_4b(mode_4b),
		.mode_8b(mode_8b),
		.sout14(s54_65),
		.sout24(s64_75),
		.sout34(s74_85),
		.sout44(sout84),
		.sout41(sout81),
		.sout42(sout82),
		.sout43(sout83),
		.cout41(cout81),
		.cout42(cout82),
		.cout43(cout83),
		.cout44(cout84)
	);
	M_44_32 M_44_32(
		.xr1(xr1),
		.xr2(xr2),
		.xr3(xr3),
		.xr4(xr4),
		.yc1(yc5),
		.yc2(yc6),
		.yc3(yc7),
		.yc4(yc8),
		.sin11(sin15),
		.sin12(sin16),
		.sin13(sin17),
		.sin14(sin18),
		.sin21(s14_25),
		.sin31(s24_35),
		.sin41(s34_45),
		.cin11(cin15),
		.cin12(cin16),
		.cin13(cin17),
		.cin14(cin18),
		.mode_2b(mode_2b),
		.mode_4b(mode_4b),
		.mode_8b(mode_8b),
		.sout14(sout18),
		.sout24(sout28),
		.sout34(sout38),
		.sout44(sout48),
		.sout41(s45_56),
		.sout42(s46_57),
		.sout43(s47_58),
		.cout41(c45_55),
		.cout42(c46_56),
		.cout43(c47_57),
		.cout44(c48_58)
	);
	M_44_36 M_44_36(
		.xr1(xr5),
		.xr2(xr6),
		.xr3(xr7),
		.xr4(xr8),
		.yc1(yc5),
		.yc2(yc6),
		.yc3(yc7),
		.yc4(yc8),
		.sin11(s44_55),
		.sin12(s45_56),
		.sin13(s46_57),
		.sin14(s47_58),
		.sin21(s54_65),
		.sin31(s64_75),
		.sin41(s74_85),
		.cin11(c45_55),
		.cin12(c46_56),
		.cin13(c47_57),
		.cin14(c48_58),
		.mode_2b(mode_2b),
		.mode_4b(mode_4b),
		.mode_8b(mode_8b),
		.sout14(sout58),
		.sout24(sout68),
		.sout34(sout78),
		.sout44(sout88),
		.sout41(sout85),
		.sout42(sout86),
		.sout43(sout87),
		.cout41(cout85),
		.cout42(cout86),
		.cout43(cout87),
		.cout44(cout88)
	);
endmodule
module M88_downAdder (
	s,
	c,
	mode_8b,
	p_high
);
	input [6:0] s;
	input [7:0] c;
	input mode_8b;
	output wire [7:0] p_high;
	assign p_high = (mode_8b ? {1'b1, s} + c : {1'b0, s} + c);
endmodule
module M_22_0 (
	xr1,
	xr2,
	yc1,
	yc2,
	sin11,
	sin12,
	sin21,
	cin11,
	cin12,
	sout21,
	sout22,
	sout12,
	cout21,
	cout22,
	mode_2b,
	mode_4b,
	mode_8b
);
	input xr1;
	input xr2;
	input yc1;
	input yc2;
	input sin11;
	input sin12;
	input sin21;
	input cin11;
	input cin12;
	input mode_2b;
	input mode_4b;
	input mode_8b;
	output wire sout21;
	output wire sout22;
	output wire sout12;
	output wire cout21;
	output wire cout22;
	wire c11_21;
	wire c12_22;
	wire s11_22;
	M_adderUnit M11(
		.a(xr1),
		.b(yc1),
		.sin(sin11),
		.cin(cin11),
		.enable(1'b1),
		.not_sel(1'b1),
		.sout(s11_22),
		.cout(c11_21)
	);
	M_adderUnit M12(
		.a(xr1),
		.b(yc2),
		.sin(sin12),
		.cin(cin12),
		.enable(1'b1),
		.not_sel(1'b0),
		.sout(sout12),
		.cout(c12_22)
	);
	M_adderUnit M21(
		.a(xr2),
		.b(yc1),
		.sin(sin21),
		.cin(c11_21),
		.enable(1'b1),
		.not_sel(~mode_2b),
		.sout(sout21),
		.cout(cout21)
	);
	M_adderUnit M22(
		.a(xr2),
		.b(yc2),
		.sin(s11_22),
		.cin(c12_22),
		.enable(1'b1),
		.not_sel(mode_2b),
		.sout(sout22),
		.cout(cout22)
	);
endmodule
module M_22_16 (
	xr1,
	xr2,
	yc1,
	yc2,
	sin11,
	sin12,
	sin21,
	cin11,
	cin12,
	sout21,
	sout22,
	sout12,
	cout21,
	cout22,
	mode_2b,
	mode_4b,
	mode_8b
);
	input xr1;
	input xr2;
	input yc1;
	input yc2;
	input sin11;
	input sin12;
	input sin21;
	input cin11;
	input cin12;
	input mode_2b;
	input mode_4b;
	input mode_8b;
	output wire sout21;
	output wire sout22;
	output wire sout12;
	output wire cout21;
	output wire cout22;
	wire c11_21;
	wire c12_22;
	wire s11_22;
	M_adderUnit M11(
		.a(xr1),
		.b(yc1),
		.sin(sin11),
		.cin(cin11),
		.enable(~mode_2b),
		.not_sel(1'b0),
		.sout(s11_22),
		.cout(c11_21)
	);
	M_adderUnit M12(
		.a(xr1),
		.b(yc2),
		.sin(sin12),
		.cin(cin12),
		.enable(~mode_2b),
		.not_sel(1'b0),
		.sout(sout12),
		.cout(c12_22)
	);
	M_adderUnit M21(
		.a(xr2),
		.b(yc1),
		.sin(sin21),
		.cin(c11_21),
		.enable(~mode_2b),
		.not_sel(1'b0),
		.sout(sout21),
		.cout(cout21)
	);
	M_adderUnit M22(
		.a(xr2),
		.b(yc2),
		.sin(s11_22),
		.cin(c12_22),
		.enable(~mode_2b),
		.not_sel(1'b0),
		.sout(sout22),
		.cout(cout22)
	);
endmodule
module M_22_18 (
	xr1,
	xr2,
	yc1,
	yc2,
	sin11,
	sin12,
	sin21,
	cin11,
	cin12,
	sout21,
	sout22,
	sout12,
	cout21,
	cout22,
	mode_2b,
	mode_4b,
	mode_8b
);
	input xr1;
	input xr2;
	input yc1;
	input yc2;
	input sin11;
	input sin12;
	input sin21;
	input cin11;
	input cin12;
	input mode_2b;
	input mode_4b;
	input mode_8b;
	output wire sout21;
	output wire sout22;
	output wire sout12;
	output wire cout21;
	output wire cout22;
	wire c11_21;
	wire c12_22;
	wire s11_22;
	M_adderUnit M11(
		.a(xr1),
		.b(yc1),
		.sin(sin11),
		.cin(cin11),
		.enable(1'b1),
		.not_sel(mode_2b),
		.sout(s11_22),
		.cout(c11_21)
	);
	M_adderUnit M12(
		.a(xr1),
		.b(yc2),
		.sin(sin12),
		.cin(cin12),
		.enable(1'b1),
		.not_sel(1'b0),
		.sout(sout12),
		.cout(c12_22)
	);
	M_adderUnit M21(
		.a(xr2),
		.b(yc1),
		.sin(sin21),
		.cin(c11_21),
		.enable(1'b1),
		.not_sel(mode_4b),
		.sout(sout21),
		.cout(cout21)
	);
	M_adderUnit M22(
		.a(xr2),
		.b(yc2),
		.sin(s11_22),
		.cin(c12_22),
		.enable(1'b1),
		.not_sel(~mode_8b),
		.sout(sout22),
		.cout(cout22)
	);
endmodule
module M_22_22 (
	xr1,
	xr2,
	yc1,
	yc2,
	sin11,
	sin12,
	sin21,
	cin11,
	cin12,
	sout21,
	sout22,
	sout12,
	cout21,
	cout22,
	mode_2b,
	mode_4b,
	mode_8b
);
	input xr1;
	input xr2;
	input yc1;
	input yc2;
	input sin11;
	input sin12;
	input sin21;
	input cin11;
	input cin12;
	input mode_2b;
	input mode_4b;
	input mode_8b;
	output wire sout21;
	output wire sout22;
	output wire sout12;
	output wire cout21;
	output wire cout22;
	wire c11_21;
	wire c12_22;
	wire s11_22;
	M_adderUnit M11(
		.a(xr1),
		.b(yc1),
		.sin(sin11),
		.cin(cin11),
		.enable(mode_8b),
		.not_sel(1'b0),
		.sout(s11_22),
		.cout(c11_21)
	);
	M_adderUnit M12(
		.a(xr1),
		.b(yc2),
		.sin(sin12),
		.cin(cin12),
		.enable(mode_8b),
		.not_sel(1'b0),
		.sout(sout12),
		.cout(c12_22)
	);
	M_adderUnit M21(
		.a(xr2),
		.b(yc1),
		.sin(sin21),
		.cin(c11_21),
		.enable(mode_8b),
		.not_sel(1'b1),
		.sout(sout21),
		.cout(cout21)
	);
	M_adderUnit M22(
		.a(xr2),
		.b(yc2),
		.sin(s11_22),
		.cin(c12_22),
		.enable(mode_8b),
		.not_sel(1'b1),
		.sout(sout22),
		.cout(cout22)
	);
endmodule
module M_22_2 (
	xr1,
	xr2,
	yc1,
	yc2,
	sin11,
	sin12,
	sin21,
	cin11,
	cin12,
	sout21,
	sout22,
	sout12,
	cout21,
	cout22,
	mode_2b,
	mode_4b,
	mode_8b
);
	input xr1;
	input xr2;
	input yc1;
	input yc2;
	input sin11;
	input sin12;
	input sin21;
	input cin11;
	input cin12;
	input mode_2b;
	input mode_4b;
	input mode_8b;
	output wire sout21;
	output wire sout22;
	output wire sout12;
	output wire cout21;
	output wire cout22;
	wire c11_21;
	wire c12_22;
	wire s11_22;
	M_adderUnit M11(
		.a(xr1),
		.b(yc1),
		.sin(sin11),
		.cin(cin11),
		.enable(~mode_2b),
		.not_sel(1'b1),
		.sout(s11_22),
		.cout(c11_21)
	);
	M_adderUnit M12(
		.a(xr1),
		.b(yc2),
		.sin(sin12),
		.cin(cin12),
		.enable(~mode_2b),
		.not_sel(1'b0),
		.sout(sout12),
		.cout(c12_22)
	);
	M_adderUnit M21(
		.a(xr2),
		.b(yc1),
		.sin(sin21),
		.cin(c11_21),
		.enable(~mode_2b),
		.not_sel(mode_8b),
		.sout(sout21),
		.cout(cout21)
	);
	M_adderUnit M22(
		.a(xr2),
		.b(yc2),
		.sin(s11_22),
		.cin(c12_22),
		.enable(~mode_2b),
		.not_sel(mode_4b),
		.sout(sout22),
		.cout(cout22)
	);
endmodule
module M_22_32 (
	xr1,
	xr2,
	yc1,
	yc2,
	sin11,
	sin12,
	sin21,
	cin11,
	cin12,
	sout21,
	sout22,
	sout12,
	cout21,
	cout22,
	mode_2b,
	mode_4b,
	mode_8b
);
	input xr1;
	input xr2;
	input yc1;
	input yc2;
	input sin11;
	input sin12;
	input sin21;
	input cin11;
	input cin12;
	input mode_2b;
	input mode_4b;
	input mode_8b;
	output wire sout21;
	output wire sout22;
	output wire sout12;
	output wire cout21;
	output wire cout22;
	wire c11_21;
	wire c12_22;
	wire s11_22;
	M_adderUnit M11(
		.a(xr1),
		.b(yc1),
		.sin(sin11),
		.cin(cin11),
		.enable(mode_8b),
		.not_sel(1'b0),
		.sout(s11_22),
		.cout(c11_21)
	);
	M_adderUnit M12(
		.a(xr1),
		.b(yc2),
		.sin(sin12),
		.cin(cin12),
		.enable(mode_8b),
		.not_sel(1'b0),
		.sout(sout12),
		.cout(c12_22)
	);
	M_adderUnit M21(
		.a(xr2),
		.b(yc1),
		.sin(sin21),
		.cin(c11_21),
		.enable(mode_8b),
		.not_sel(1'b0),
		.sout(sout21),
		.cout(cout21)
	);
	M_adderUnit M22(
		.a(xr2),
		.b(yc2),
		.sin(s11_22),
		.cin(c12_22),
		.enable(mode_8b),
		.not_sel(1'b0),
		.sout(sout22),
		.cout(cout22)
	);
endmodule
module M_22_36 (
	xr1,
	xr2,
	yc1,
	yc2,
	sin11,
	sin12,
	sin21,
	cin11,
	cin12,
	sout21,
	sout22,
	sout12,
	cout21,
	cout22,
	mode_2b,
	mode_4b,
	mode_8b
);
	input xr1;
	input xr2;
	input yc1;
	input yc2;
	input sin11;
	input sin12;
	input sin21;
	input cin11;
	input cin12;
	input mode_2b;
	input mode_4b;
	input mode_8b;
	output wire sout21;
	output wire sout22;
	output wire sout12;
	output wire cout21;
	output wire cout22;
	wire c11_21;
	wire c12_22;
	wire s11_22;
	M_adderUnit M11(
		.a(xr1),
		.b(yc1),
		.sin(sin11),
		.cin(cin11),
		.enable(1'b1),
		.not_sel(~mode_8b),
		.sout(s11_22),
		.cout(c11_21)
	);
	M_adderUnit M12(
		.a(xr1),
		.b(yc2),
		.sin(sin12),
		.cin(cin12),
		.enable(1'b1),
		.not_sel(1'b0),
		.sout(sout12),
		.cout(c12_22)
	);
	M_adderUnit M21(
		.a(xr2),
		.b(yc1),
		.sin(sin21),
		.cin(c11_21),
		.enable(1'b1),
		.not_sel(mode_4b),
		.sout(sout21),
		.cout(cout21)
	);
	M_adderUnit M22(
		.a(xr2),
		.b(yc2),
		.sin(s11_22),
		.cin(c12_22),
		.enable(1'b1),
		.not_sel(mode_2b),
		.sout(sout22),
		.cout(cout22)
	);
endmodule
module M_22_38 (
	xr1,
	xr2,
	yc1,
	yc2,
	sin11,
	sin12,
	sin21,
	cin11,
	cin12,
	sout21,
	sout22,
	sout12,
	cout21,
	cout22,
	mode_2b,
	mode_4b,
	mode_8b
);
	input xr1;
	input xr2;
	input yc1;
	input yc2;
	input sin11;
	input sin12;
	input sin21;
	input cin11;
	input cin12;
	input mode_2b;
	input mode_4b;
	input mode_8b;
	output wire sout21;
	output wire sout22;
	output wire sout12;
	output wire cout21;
	output wire cout22;
	wire c11_21;
	wire c12_22;
	wire s11_22;
	M_adderUnit M11(
		.a(xr1),
		.b(yc1),
		.sin(sin11),
		.cin(cin11),
		.enable(~mode_2b),
		.not_sel(mode_4b),
		.sout(s11_22),
		.cout(c11_21)
	);
	M_adderUnit M12(
		.a(xr1),
		.b(yc2),
		.sin(sin12),
		.cin(cin12),
		.enable(~mode_2b),
		.not_sel(1'b0),
		.sout(sout12),
		.cout(c12_22)
	);
	M_adderUnit M21(
		.a(xr2),
		.b(yc1),
		.sin(sin21),
		.cin(c11_21),
		.enable(~mode_2b),
		.not_sel(mode_8b),
		.sout(sout21),
		.cout(cout21)
	);
	M_adderUnit M22(
		.a(xr2),
		.b(yc2),
		.sin(s11_22),
		.cin(c12_22),
		.enable(~mode_2b),
		.not_sel(~mode_2b),
		.sout(sout22),
		.cout(cout22)
	);
endmodule
module M_22_4 (
	xr1,
	xr2,
	yc1,
	yc2,
	sin11,
	sin12,
	sin21,
	cin11,
	cin12,
	sout21,
	sout22,
	sout12,
	cout21,
	cout22,
	mode_2b,
	mode_4b,
	mode_8b
);
	input xr1;
	input xr2;
	input yc1;
	input yc2;
	input sin11;
	input sin12;
	input sin21;
	input cin11;
	input cin12;
	input mode_2b;
	input mode_4b;
	input mode_8b;
	output wire sout21;
	output wire sout22;
	output wire sout12;
	output wire cout21;
	output wire cout22;
	wire c11_21;
	wire c12_22;
	wire s11_22;
	M_adderUnit M11(
		.a(xr1),
		.b(yc1),
		.sin(sin11),
		.cin(cin11),
		.enable(mode_8b),
		.not_sel(1'b1),
		.sout(s11_22),
		.cout(c11_21)
	);
	M_adderUnit M12(
		.a(xr1),
		.b(yc2),
		.sin(sin12),
		.cin(cin12),
		.enable(mode_8b),
		.not_sel(1'b0),
		.sout(sout12),
		.cout(c12_22)
	);
	M_adderUnit M21(
		.a(xr2),
		.b(yc1),
		.sin(sin21),
		.cin(c11_21),
		.enable(mode_8b),
		.not_sel(1'b1),
		.sout(sout21),
		.cout(cout21)
	);
	M_adderUnit M22(
		.a(xr2),
		.b(yc2),
		.sin(s11_22),
		.cin(c12_22),
		.enable(mode_8b),
		.not_sel(1'b0),
		.sout(sout22),
		.cout(cout22)
	);
endmodule
module M_22_54 (
	xr1,
	xr2,
	yc1,
	yc2,
	sin11,
	sin12,
	sin21,
	cin11,
	cin12,
	sout21,
	sout22,
	sout12,
	cout21,
	cout22,
	mode_2b,
	mode_4b,
	mode_8b
);
	input xr1;
	input xr2;
	input yc1;
	input yc2;
	input sin11;
	input sin12;
	input sin21;
	input cin11;
	input cin12;
	input mode_2b;
	input mode_4b;
	input mode_8b;
	output wire sout21;
	output wire sout22;
	output wire sout12;
	output wire cout21;
	output wire cout22;
	wire c11_21;
	wire c12_22;
	wire s11_22;
	M_adderUnit M11(
		.a(xr1),
		.b(yc1),
		.sin(sin11),
		.cin(cin11),
		.enable(1'b1),
		.not_sel(mode_2b),
		.sout(s11_22),
		.cout(c11_21)
	);
	M_adderUnit M12(
		.a(xr1),
		.b(yc2),
		.sin(sin12),
		.cin(cin12),
		.enable(1'b1),
		.not_sel(1'b0),
		.sout(sout12),
		.cout(c12_22)
	);
	M_adderUnit M21(
		.a(xr2),
		.b(yc1),
		.sin(sin21),
		.cin(c11_21),
		.enable(1'b1),
		.not_sel(~mode_2b),
		.sout(sout21),
		.cout(cout21)
	);
	M_adderUnit M22(
		.a(xr2),
		.b(yc2),
		.sin(s11_22),
		.cin(c12_22),
		.enable(1'b1),
		.not_sel(1'b1),
		.sout(sout22),
		.cout(cout22)
	);
endmodule
module M_22_6 (
	xr1,
	xr2,
	yc1,
	yc2,
	sin11,
	sin12,
	sin21,
	cin11,
	cin12,
	sout21,
	sout22,
	sout12,
	cout21,
	cout22,
	mode_2b,
	mode_4b,
	mode_8b
);
	input xr1;
	input xr2;
	input yc1;
	input yc2;
	input sin11;
	input sin12;
	input sin21;
	input cin11;
	input cin12;
	input mode_2b;
	input mode_4b;
	input mode_8b;
	output wire sout21;
	output wire sout22;
	output wire sout12;
	output wire cout21;
	output wire cout22;
	wire c11_21;
	wire c12_22;
	wire s11_22;
	M_adderUnit M11(
		.a(xr1),
		.b(yc1),
		.sin(sin11),
		.cin(cin11),
		.enable(mode_8b),
		.not_sel(1'b1),
		.sout(s11_22),
		.cout(c11_21)
	);
	M_adderUnit M12(
		.a(xr1),
		.b(yc2),
		.sin(sin12),
		.cin(cin12),
		.enable(mode_8b),
		.not_sel(1'b0),
		.sout(sout12),
		.cout(c12_22)
	);
	M_adderUnit M21(
		.a(xr2),
		.b(yc1),
		.sin(sin21),
		.cin(c11_21),
		.enable(mode_8b),
		.not_sel(1'b0),
		.sout(sout21),
		.cout(cout21)
	);
	M_adderUnit M22(
		.a(xr2),
		.b(yc2),
		.sin(s11_22),
		.cin(c12_22),
		.enable(mode_8b),
		.not_sel(1'b1),
		.sout(sout22),
		.cout(cout22)
	);
endmodule
module M_44_0 (
	xr1,
	xr2,
	xr3,
	xr4,
	yc1,
	yc2,
	yc3,
	yc4,
	sin11,
	sin12,
	sin13,
	sin14,
	sin21,
	sin31,
	sin41,
	cin11,
	cin12,
	cin13,
	cin14,
	sout14,
	sout24,
	sout34,
	sout44,
	sout41,
	sout42,
	sout43,
	cout41,
	cout42,
	cout43,
	cout44,
	mode_2b,
	mode_4b,
	mode_8b
);
	input xr1;
	input xr2;
	input xr3;
	input xr4;
	input yc1;
	input yc2;
	input yc3;
	input yc4;
	input sin11;
	input sin12;
	input sin13;
	input sin14;
	input sin21;
	input sin31;
	input sin41;
	input cin11;
	input cin12;
	input cin13;
	input cin14;
	input mode_2b;
	input mode_4b;
	input mode_8b;
	output wire sout14;
	output wire sout24;
	output wire sout34;
	output wire sout44;
	output wire sout41;
	output wire sout42;
	output wire sout43;
	output wire cout41;
	output wire cout42;
	output wire cout43;
	output wire cout44;
	wire c21_31;
	wire c22_32;
	wire c23_33;
	wire c24_34;
	wire s21_32;
	wire s22_33;
	wire s23_34;
	wire s12_23;
	wire s32_43;
	M_22_0 M_22_0(
		.xr1(xr1),
		.xr2(xr2),
		.yc1(yc1),
		.yc2(yc2),
		.sin11(sin11),
		.sin12(sin12),
		.sin21(sin21),
		.cin11(cin11),
		.cin12(cin12),
		.mode_2b(mode_2b),
		.mode_4b(mode_4b),
		.mode_8b(mode_8b),
		.sout21(s21_32),
		.sout22(s22_33),
		.sout12(s12_23),
		.cout21(c21_31),
		.cout22(c22_32)
	);
	M_22_2 M_22_2(
		.xr1(xr3),
		.xr2(xr4),
		.yc1(yc1),
		.yc2(yc2),
		.sin11(sin31),
		.sin12(s21_32),
		.sin21(sin41),
		.cin11(c21_31),
		.cin12(c22_32),
		.mode_2b(mode_2b),
		.mode_4b(mode_4b),
		.mode_8b(mode_8b),
		.sout21(sout41),
		.sout22(sout42),
		.sout12(s32_43),
		.cout21(cout41),
		.cout22(cout42)
	);
	M_22_16 M_22_16(
		.xr1(xr1),
		.xr2(xr2),
		.yc1(yc3),
		.yc2(yc4),
		.sin11(sin13),
		.sin12(sin14),
		.sin21(s12_23),
		.cin11(cin13),
		.cin12(cin14),
		.mode_2b(mode_2b),
		.mode_4b(mode_4b),
		.mode_8b(mode_8b),
		.sout21(s23_34),
		.sout22(sout24),
		.sout12(sout14),
		.cout21(c23_33),
		.cout22(c24_34)
	);
	M_22_18 M_22_18(
		.xr1(xr3),
		.xr2(xr4),
		.yc1(yc3),
		.yc2(yc4),
		.sin11(s22_33),
		.sin12(s23_34),
		.sin21(s32_43),
		.cin11(c23_33),
		.cin12(c24_34),
		.mode_2b(mode_2b),
		.mode_4b(mode_4b),
		.mode_8b(mode_8b),
		.sout21(sout43),
		.sout22(sout44),
		.sout12(sout34),
		.cout21(cout43),
		.cout22(cout44)
	);
endmodule
module M_44_32 (
	xr1,
	xr2,
	xr3,
	xr4,
	yc1,
	yc2,
	yc3,
	yc4,
	sin11,
	sin12,
	sin13,
	sin14,
	sin21,
	sin31,
	sin41,
	cin11,
	cin12,
	cin13,
	cin14,
	sout14,
	sout24,
	sout34,
	sout44,
	sout41,
	sout42,
	sout43,
	cout41,
	cout42,
	cout43,
	cout44,
	mode_2b,
	mode_4b,
	mode_8b
);
	input xr1;
	input xr2;
	input xr3;
	input xr4;
	input yc1;
	input yc2;
	input yc3;
	input yc4;
	input sin11;
	input sin12;
	input sin13;
	input sin14;
	input sin21;
	input sin31;
	input sin41;
	input cin11;
	input cin12;
	input cin13;
	input cin14;
	input mode_2b;
	input mode_4b;
	input mode_8b;
	output wire sout14;
	output wire sout24;
	output wire sout34;
	output wire sout44;
	output wire sout41;
	output wire sout42;
	output wire sout43;
	output wire cout41;
	output wire cout42;
	output wire cout43;
	output wire cout44;
	wire c21_31;
	wire c22_32;
	wire c23_33;
	wire c24_34;
	wire s21_32;
	wire s22_33;
	wire s23_34;
	wire s12_23;
	wire s32_43;
	M_22_32 M_22_32(
		.xr1(xr1),
		.xr2(xr2),
		.yc1(yc1),
		.yc2(yc2),
		.sin11(sin11),
		.sin12(sin12),
		.sin21(sin21),
		.cin11(cin11),
		.cin12(cin12),
		.mode_2b(mode_2b),
		.mode_4b(mode_4b),
		.mode_8b(mode_8b),
		.sout21(s21_32),
		.sout22(s22_33),
		.sout12(s12_23),
		.cout21(c21_31),
		.cout22(c22_32)
	);
	M_22_32 M_22_34(
		.xr1(xr3),
		.xr2(xr4),
		.yc1(yc1),
		.yc2(yc2),
		.sin11(sin31),
		.sin12(s21_32),
		.sin21(sin41),
		.cin11(c21_31),
		.cin12(c22_32),
		.mode_2b(mode_2b),
		.mode_4b(mode_4b),
		.mode_8b(mode_8b),
		.sout21(sout41),
		.sout22(sout42),
		.sout12(s32_43),
		.cout21(cout41),
		.cout22(cout42)
	);
	M_22_32 M_22_48(
		.xr1(xr1),
		.xr2(xr2),
		.yc1(yc3),
		.yc2(yc4),
		.sin11(sin13),
		.sin12(sin14),
		.sin21(s12_23),
		.cin11(cin13),
		.cin12(cin14),
		.mode_2b(mode_2b),
		.mode_4b(mode_4b),
		.mode_8b(mode_8b),
		.sout21(s23_34),
		.sout22(sout24),
		.sout12(sout14),
		.cout21(c23_33),
		.cout22(c24_34)
	);
	M_22_32 M_22_50(
		.xr1(xr3),
		.xr2(xr4),
		.yc1(yc3),
		.yc2(yc4),
		.sin11(s22_33),
		.sin12(s23_34),
		.sin21(s32_43),
		.cin11(c23_33),
		.cin12(c24_34),
		.mode_2b(mode_2b),
		.mode_4b(mode_4b),
		.mode_8b(mode_8b),
		.sout21(sout43),
		.sout22(sout44),
		.sout12(sout34),
		.cout21(cout43),
		.cout22(cout44)
	);
endmodule
module M_44_36 (
	xr1,
	xr2,
	xr3,
	xr4,
	yc1,
	yc2,
	yc3,
	yc4,
	sin11,
	sin12,
	sin13,
	sin14,
	sin21,
	sin31,
	sin41,
	cin11,
	cin12,
	cin13,
	cin14,
	sout14,
	sout24,
	sout34,
	sout44,
	sout41,
	sout42,
	sout43,
	cout41,
	cout42,
	cout43,
	cout44,
	mode_2b,
	mode_4b,
	mode_8b
);
	input xr1;
	input xr2;
	input xr3;
	input xr4;
	input yc1;
	input yc2;
	input yc3;
	input yc4;
	input sin11;
	input sin12;
	input sin13;
	input sin14;
	input sin21;
	input sin31;
	input sin41;
	input cin11;
	input cin12;
	input cin13;
	input cin14;
	input mode_2b;
	input mode_4b;
	input mode_8b;
	output wire sout14;
	output wire sout24;
	output wire sout34;
	output wire sout44;
	output wire sout41;
	output wire sout42;
	output wire sout43;
	output wire cout41;
	output wire cout42;
	output wire cout43;
	output wire cout44;
	wire c21_31;
	wire c22_32;
	wire c23_33;
	wire c24_34;
	wire s21_32;
	wire s22_33;
	wire s23_34;
	wire s12_23;
	wire s32_43;
	M_22_36 M_22_36(
		.xr1(xr1),
		.xr2(xr2),
		.yc1(yc1),
		.yc2(yc2),
		.sin11(sin11),
		.sin12(sin12),
		.sin21(sin21),
		.cin11(cin11),
		.cin12(cin12),
		.mode_2b(mode_2b),
		.mode_4b(mode_4b),
		.mode_8b(mode_8b),
		.sout21(s21_32),
		.sout22(s22_33),
		.sout12(s12_23),
		.cout21(c21_31),
		.cout22(c22_32)
	);
	M_22_38 M_22_38(
		.xr1(xr3),
		.xr2(xr4),
		.yc1(yc1),
		.yc2(yc2),
		.sin11(sin31),
		.sin12(s21_32),
		.sin21(sin41),
		.cin11(c21_31),
		.cin12(c22_32),
		.mode_2b(mode_2b),
		.mode_4b(mode_4b),
		.mode_8b(mode_8b),
		.sout21(sout41),
		.sout22(sout42),
		.sout12(s32_43),
		.cout21(cout41),
		.cout22(cout42)
	);
	M_22_16 M_22_52(
		.xr1(xr1),
		.xr2(xr2),
		.yc1(yc3),
		.yc2(yc4),
		.sin11(sin13),
		.sin12(sin14),
		.sin21(s12_23),
		.cin11(cin13),
		.cin12(cin14),
		.mode_2b(mode_2b),
		.mode_4b(mode_4b),
		.mode_8b(mode_8b),
		.sout21(s23_34),
		.sout22(sout24),
		.sout12(sout14),
		.cout21(c23_33),
		.cout22(c24_34)
	);
	M_22_54 M_22_54(
		.xr1(xr3),
		.xr2(xr4),
		.yc1(yc3),
		.yc2(yc4),
		.sin11(s22_33),
		.sin12(s23_34),
		.sin21(s32_43),
		.cin11(c23_33),
		.cin12(c24_34),
		.mode_2b(mode_2b),
		.mode_4b(mode_4b),
		.mode_8b(mode_8b),
		.sout21(sout43),
		.sout22(sout44),
		.sout12(sout34),
		.cout21(cout43),
		.cout22(cout44)
	);
endmodule
module M_44_4 (
	xr1,
	xr2,
	xr3,
	xr4,
	yc1,
	yc2,
	yc3,
	yc4,
	sin11,
	sin12,
	sin13,
	sin14,
	sin21,
	sin31,
	sin41,
	cin11,
	cin12,
	cin13,
	cin14,
	sout14,
	sout24,
	sout34,
	sout44,
	sout41,
	sout42,
	sout43,
	cout41,
	cout42,
	cout43,
	cout44,
	mode_2b,
	mode_4b,
	mode_8b
);
	input xr1;
	input xr2;
	input xr3;
	input xr4;
	input yc1;
	input yc2;
	input yc3;
	input yc4;
	input sin11;
	input sin12;
	input sin13;
	input sin14;
	input sin21;
	input sin31;
	input sin41;
	input cin11;
	input cin12;
	input cin13;
	input cin14;
	input mode_2b;
	input mode_4b;
	input mode_8b;
	output wire sout14;
	output wire sout24;
	output wire sout34;
	output wire sout44;
	output wire sout41;
	output wire sout42;
	output wire sout43;
	output wire cout41;
	output wire cout42;
	output wire cout43;
	output wire cout44;
	wire c21_31;
	wire c22_32;
	wire c23_33;
	wire c24_34;
	wire s21_32;
	wire s22_33;
	wire s23_34;
	wire s12_23;
	wire s32_43;
	M_22_4 M_22_4(
		.xr1(xr1),
		.xr2(xr2),
		.yc1(yc1),
		.yc2(yc2),
		.sin11(sin11),
		.sin12(sin12),
		.sin21(sin21),
		.cin11(cin11),
		.cin12(cin12),
		.mode_2b(mode_2b),
		.mode_4b(mode_4b),
		.mode_8b(mode_8b),
		.sout21(s21_32),
		.sout22(s22_33),
		.sout12(s12_23),
		.cout21(c21_31),
		.cout22(c22_32)
	);
	M_22_6 M_22_6(
		.xr1(xr3),
		.xr2(xr4),
		.yc1(yc1),
		.yc2(yc2),
		.sin11(sin31),
		.sin12(s21_32),
		.sin21(sin41),
		.cin11(c21_31),
		.cin12(c22_32),
		.mode_2b(mode_2b),
		.mode_4b(mode_4b),
		.mode_8b(mode_8b),
		.sout21(sout41),
		.sout22(sout42),
		.sout12(s32_43),
		.cout21(cout41),
		.cout22(cout42)
	);
	M_22_32 M_22_20(
		.xr1(xr1),
		.xr2(xr2),
		.yc1(yc3),
		.yc2(yc4),
		.sin11(sin13),
		.sin12(sin14),
		.sin21(s12_23),
		.cin11(cin13),
		.cin12(cin14),
		.mode_2b(mode_2b),
		.mode_4b(mode_4b),
		.mode_8b(mode_8b),
		.sout21(s23_34),
		.sout22(sout24),
		.sout12(sout14),
		.cout21(c23_33),
		.cout22(c24_34)
	);
	M_22_22 M_22_22(
		.xr1(xr3),
		.xr2(xr4),
		.yc1(yc3),
		.yc2(yc4),
		.sin11(s22_33),
		.sin12(s23_34),
		.sin21(s32_43),
		.cin11(c23_33),
		.cin12(c24_34),
		.mode_2b(mode_2b),
		.mode_4b(mode_4b),
		.mode_8b(mode_8b),
		.sout21(sout43),
		.sout22(sout44),
		.sout12(sout34),
		.cout21(cout43),
		.cout22(cout44)
	);
endmodule
module M_adderUnit (
	a,
	b,
	sin,
	cin,
	enable,
	not_sel,
	sout,
	cout
);
	input a;
	input b;
	input sin;
	input cin;
	input enable;
	input not_sel;
	output wire sout;
	output wire cout;
	reg ab;
	always @(*)
		if (enable)
			ab = (not_sel ? ~(a & b) : a & b);
		else
			ab = 1'b0;
	assign {cout, sout} = (sin + cin) + ab;
endmodule
