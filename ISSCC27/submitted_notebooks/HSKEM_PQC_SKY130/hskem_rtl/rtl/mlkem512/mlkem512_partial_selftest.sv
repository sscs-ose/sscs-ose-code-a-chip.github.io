import mlkem512_pkg::*;

module mlkem512_partial_selftest (
    input  wire       clk,
    input  wire       rst_n,
    input  wire       start,
    output reg        busy,
    output reg        done,
    output reg        pass,
    output reg [7:0]  status,
    output reg [31:0] digest
);
    wire [9:0] c10_2000;
    wire [3:0] c4_2000;
    wire [15:0] d10_615;
    wire [15:0] d4_10;

    wire [15:0] cbd2_coeff [0:7];
    wire [15:0] cbd3_coeff [0:3];

    wire [15:0] pack10_in [0:3];
    wire [15:0] pack10_out [0:3];
    wire [39:0] pack10_bytes;

    wire [15:0] pack4_in [0:1];
    wire [15:0] pack4_out [0:1];
    wire [7:0] pack4_bytes;

    wire [15:0] pack12_in [0:1];
    wire [15:0] pack12_out [0:1];
    wire [23:0] pack12_bytes;

    assign pack10_in[0] = 16'd341;
    assign pack10_in[1] = 16'd682;
    assign pack10_in[2] = 16'd17;
    assign pack10_in[3] = 16'd999;

    assign pack4_in[0] = 16'd7;
    assign pack4_in[1] = 16'd8;

    assign pack12_in[0] = 16'd1234;
    assign pack12_in[1] = 16'd2047;

    mlkem512_compress #(.D(10)) u_c10 (
        .coeff(16'd2000),
        .compressed(c10_2000)
    );

    mlkem512_compress #(.D(4)) u_c4 (
        .coeff(16'd2000),
        .compressed(c4_2000)
    );

    mlkem512_decompress #(.D(10)) u_d10 (
        .compressed(10'd615),
        .coeff(d10_615)
    );

    mlkem512_decompress #(.D(4)) u_d4 (
        .compressed(4'd10),
        .coeff(d4_10)
    );

    mlkem512_cbd2_block u_cbd2 (
        .word_le(32'h01234567),
        .coeff(cbd2_coeff)
    );

    mlkem512_cbd3_block u_cbd3 (
        .word_le(24'hABCDEF),
        .coeff(cbd3_coeff)
    );

    mlkem512_byte_pack_block #(.D(10), .COEFFS(4), .BYTES(5)) u_pack10 (
        .coeff(pack10_in),
        .bytes_le(pack10_bytes)
    );

    mlkem512_byte_unpack_block #(.D(10), .COEFFS(4), .BYTES(5)) u_unpack10 (
        .bytes_le(pack10_bytes),
        .coeff(pack10_out)
    );

    mlkem512_byte_pack_block #(.D(4), .COEFFS(2), .BYTES(1)) u_pack4 (
        .coeff(pack4_in),
        .bytes_le(pack4_bytes)
    );

    mlkem512_byte_unpack_block #(.D(4), .COEFFS(2), .BYTES(1)) u_unpack4 (
        .bytes_le(pack4_bytes),
        .coeff(pack4_out)
    );

    mlkem512_byte_pack_block #(.D(12), .COEFFS(2), .BYTES(3)) u_pack12 (
        .coeff(pack12_in),
        .bytes_le(pack12_bytes)
    );

    mlkem512_byte_unpack_block #(.D(12), .COEFFS(2), .BYTES(3)) u_unpack12 (
        .bytes_le(pack12_bytes),
        .coeff(pack12_out)
    );

    wire param_ok =
        (MLKEM_N == 256) && (MLKEM_Q == 3329) &&
        (MLKEM512_K == 2) && (MLKEM512_ETA1 == 3) &&
        (MLKEM512_ETA2 == 2) && (MLKEM512_DU == 10) &&
        (MLKEM512_DV == 4) && (MLKEM512_EK_BYTES == 800) &&
        (MLKEM512_DK_BYTES == 1632) && (MLKEM512_CT_BYTES == 768) &&
        (MLKEM_SS_BYTES == 32);

    wire compress_ok =
        (c10_2000 == 10'd615) && (d10_615 == 16'd1999) &&
        (c4_2000 == 4'd10) && (d4_10 == 16'd2081);

    wire cbd2_ok =
        (cbd2_coeff[0] == 16'd1) && (cbd2_coeff[1] == 16'd0) &&
        (cbd2_coeff[2] == 16'd0) && (cbd2_coeff[3] == 16'd3328) &&
        (cbd2_coeff[4] == 16'd2) && (cbd2_coeff[5] == 16'd1) &&
        (cbd2_coeff[6] == 16'd1) && (cbd2_coeff[7] == 16'd0);

    wire cbd3_ok =
        (cbd3_coeff[0] == 16'd1) && (cbd3_coeff[1] == 16'd1) &&
        (cbd3_coeff[2] == 16'd3327) && (cbd3_coeff[3] == 16'd3328);

    wire pack10_ok =
        (pack10_bytes == 40'hF9C11AA955) &&
        (pack10_out[0] == 16'd341) && (pack10_out[1] == 16'd682) &&
        (pack10_out[2] == 16'd17) && (pack10_out[3] == 16'd999);

    wire pack4_ok =
        (pack4_bytes == 8'h87) &&
        (pack4_out[0] == 16'd7) && (pack4_out[1] == 16'd8);

    wire pack12_ok =
        (pack12_bytes == 24'h7FF4D2) &&
        (pack12_out[0] == 16'd1234) && (pack12_out[1] == 16'd2047);

    wire [7:0] status_calc = {
        param_ok && compress_ok && cbd2_ok && cbd3_ok &&
            pack10_ok && pack4_ok && pack12_ok,
        pack12_ok,
        pack4_ok,
        pack10_ok,
        cbd3_ok,
        cbd2_ok,
        compress_ok,
        param_ok
    };

    wire [31:0] digest_calc = {
        c10_2000[7:0],
        d10_615[7:0],
        pack10_bytes[7:0],
        pack12_bytes[7:0]
    };

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            busy <= 1'b0;
            done <= 1'b0;
            pass <= 1'b0;
            status <= 8'd0;
            digest <= 32'd0;
        end else begin
            done <= 1'b0;
            if (start && !busy) begin
                busy <= 1'b1;
                pass <= (status_calc == 8'hFF);
                status <= status_calc;
                digest <= digest_calc;
            end else if (busy) begin
                busy <= 1'b0;
                done <= 1'b1;
            end
        end
    end
endmodule

