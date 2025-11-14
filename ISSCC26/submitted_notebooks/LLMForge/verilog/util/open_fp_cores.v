module bf16_fp_recip (
  input  wire [15:0] a,   // BF16 input
  output wire [15:0] z    // Reciprocal output
);

  // 1) Extract sign, exponent, fraction
  wire sign = a[15];
  wire [7:0] exp = a[14:7];
  wire [6:0] frac = a[6:0];
  wire [7:0] bias = 8'd127;

  // 2) Reconstruct normalized mantissa
  wire [7:0] mantissa_in = {1'b1, frac};  // 1.xxx

  // 3) Rough initial estimate: 1/m
  // For demonstration, use constant approximation
  // In real hardware: use LUT with 32-64 entries
  wire [7:0] recip_est = 8'd255 / mantissa_in;

  // 4) Optional: One Newton-Raphson refinement
  // y = y * (2 - x * y)
  wire [15:0] prod1 = mantissa_in * recip_est;      // x * y
  wire [8:0] two_minus_prod1 = 9'd512 - prod1[15:7]; // 2 - prod1
  wire [15:0] refined = recip_est * two_minus_prod1;

  // 5) Exponent: invert exponent w.r.t bias
  wire [7:0] exp_out = bias * 2 - exp;

  // 6) Assemble output
  assign z = {sign, exp_out, refined[15:9]};

endmodule

module fp_i2flt #(
  parameter SIG_WIDTH = 7,
  parameter EXP_WIDTH = 8,
  parameter ISIZE = 32,   // Input integer bit-width
  parameter ISIGN = 1     // 1 = signed, 0 = unsigned
)(
  input  wire [ISIZE-1:0] a,    // Integer input
  output wire [SIG_WIDTH+EXP_WIDTH:0] z  // IEEE output
);

  localparam FP_WIDTH = SIG_WIDTH + EXP_WIDTH + 1; // sign + exp + sig
  localparam EXP_BIAS = (1 << (EXP_WIDTH-1)) - 1;

  // Sign bit
  wire sign;
  wire [ISIZE-1:0] mag;

  assign sign = ISIGN ? a[ISIZE-1] : 1'b0;
  assign mag  = ISIGN ? (sign ? (~a + 1'b1) : a) : a;

  // Leading Zero Count
  integer i;
  reg [7:0] lz;
  always @(*) begin
    lz = 0;
    for (i = ISIZE-1; i >= 0; i = i - 1) begin
      if (mag[i] == 1'b1)
        lz = ISIZE - i - 1;
    end
  end

  // Normalized mantissa
  wire [ISIZE-1:0] shifted = mag << lz;

  // Mantissa: drop MSB implicit 1
  wire [SIG_WIDTH-1:0] mantissa = shifted[ISIZE-2 -: SIG_WIDTH];

  // Exponent
  wire [EXP_WIDTH-1:0] exponent = EXP_BIAS + ISIZE - lz - 1;

  assign z = {sign, exponent, mantissa};

endmodule

module fp_flt2i #(
  parameter SIG_WIDTH = 23,
  parameter EXP_WIDTH = 8,
  parameter ISIZE     = 32,
  parameter ISIGN     = 1   // 1 = signed, 0 = unsigned
)(
  input  wire [SIG_WIDTH+EXP_WIDTH:0] a,  // IEEE input
  output wire [ISIZE-1:0] z               // Integer output
);

  localparam FP_WIDTH = SIG_WIDTH + EXP_WIDTH + 1;
  localparam EXP_BIAS = (1 << (EXP_WIDTH-1)) - 1;

  wire sign;
  wire [EXP_WIDTH-1:0] exponent;
  wire [SIG_WIDTH-1:0] mantissa;

  assign sign     = a[FP_WIDTH-1];
  assign exponent = a[FP_WIDTH-2 -: EXP_WIDTH];
  assign mantissa = a[SIG_WIDTH-1:0];

  // Restore hidden bit
  wire [SIG_WIDTH:0] significand = {1'b1, mantissa};

  // Compute shift amount
  wire signed [EXP_WIDTH:0] shift = exponent - EXP_BIAS;

  // Shift significand to get integer part
  reg [ISIZE-1:0] int_value;

  always @(*) begin
    if (shift >= 0) begin
      int_value = significand << shift;
    end else begin
      int_value = significand >> (-shift);
    end

    if (ISIGN && sign) begin
      int_value = ~int_value + 1;  // 2's complement for negative
    end
  end

  assign z = int_value;

endmodule


module fp_add_DG #(
  parameter SIG_WIDTH = 7,
  parameter EXP_WIDTH = 8
)(
  input  wire [SIG_WIDTH+EXP_WIDTH:0] a,
  input  wire [SIG_WIDTH+EXP_WIDTH:0] b,
  input  wire [2:0] rnd,     // Not used in this simple version
  input  wire DG_ctrl,       // Data Gating control
  output reg  [SIG_WIDTH+EXP_WIDTH:0] z,
  output wire [7:0] status    // Optional
);

  // --- Internal FP adder: use open-source HardFloat or custom ---
  wire [SIG_WIDTH+EXP_WIDTH:0] sum_result;

  fp_add #(
    .sig_width(SIG_WIDTH),
    .exp_width(EXP_WIDTH)
  ) adder_core (
    .a(a),
    .b(b),
    .rnd(0),
    .z(sum_result),
    .status(_)
  );

  // --- Data Gating: latch output when DG_ctrl=0 ---
  always @(*) begin
    if (DG_ctrl) begin
      z = sum_result;
    end
    // else z holds previous value (in hardware, use a register!)
  end

  // --- Example: no real status flags here ---
  assign status = 8'b0;

endmodule

module fp_exp #(
  parameter SIG_WIDTH = 7,
  parameter EXP_WIDTH = 8
)(
  input  wire [SIG_WIDTH+EXP_WIDTH:0] a, // IEEE-754 input
  output wire [SIG_WIDTH+EXP_WIDTH:0] z  // IEEE-754 output
);

  // Local params
  localparam FP_WIDTH = SIG_WIDTH + EXP_WIDTH + 1;
  localparam EXP_BIAS = (1 << (EXP_WIDTH-1)) - 1; // 127 for FP32

  // --- Unpack input ---
  wire sign;
  wire [EXP_WIDTH-1:0] exp;
  wire [SIG_WIDTH-1:0] frac;
  wire [31:0] log2_e = 32'h3FB8AA3B; // log2(e) ≈ 1.4427 in IEEE-754

  assign sign = a[FP_WIDTH-1];
  assign exp  = a[FP_WIDTH-2 -: EXP_WIDTH];
  assign frac = a[SIG_WIDTH-1:0];

  // --- Convert input to log2 domain: x * log2(e) ---
  // Approx: assume input already scaled or pass-through for demo

  // --- Integer and fraction parts ---
  wire signed [EXP_WIDTH:0] k;  // integer part
  wire [5:0] f;                 // 6-bit fraction for LUT

  // For demo: map input to k and f
  assign k = exp - EXP_BIAS;  // approximate integer
  assign f = frac[22:17];     // top bits for LUT index

  // --- LUT for 2^f ---
  reg [23:0] lut_out;
  always @(*) begin
    case (f[5:4])
      2'b00: lut_out = 24'h800000; // 1.0
      2'b01: lut_out = 24'h8CCCCD; // ~1.1
      2'b10: lut_out = 24'h99999A; // ~1.2
      2'b11: lut_out = 24'hA66666; // ~1.3
    endcase
  end

  // --- Compose output ---
  wire [EXP_WIDTH-1:0] exp_out = EXP_BIAS + k;
  wire [SIG_WIDTH-1:0] frac_out = lut_out[SIG_WIDTH+1:2]; // Drop extra bits

  assign z = {1'b0, exp_out, frac_out};

endmodule

module fp_add #(
    parameter integer sig_width = 7,   // number of fraction bits
    parameter integer exp_width = 8,   // number of exponent bits
)(
    input  wire [sig_width+exp_width:0] a,  // input a
    input  wire [sig_width+exp_width:0] b,  // input b
    input  wire [2:0]                   rnd, // rounding mode (ignored)
    output reg  [sig_width+exp_width:0] z,   // result = a + b
    output reg  [7:0]                   status // status flags
);

    // Sign, exponent, mantissa extraction
    wire sign_a = a[sig_width + exp_width];
    wire sign_b = b[sig_width + exp_width];
    wire [exp_width-1:0] exp_a = a[sig_width + exp_width - 1 : sig_width];
    wire [exp_width-1:0] exp_b = b[sig_width + exp_width - 1 : sig_width];
    wire [sig_width-1:0] frac_a = a[sig_width-1:0];
    wire [sig_width-1:0] frac_b = b[sig_width-1:0];

    // Add implicit leading 1 for normalized values
    wire [sig_width:0] mant_a = (|exp_a) ? {1'b1, frac_a} : {1'b0, frac_a};
    wire [sig_width:0] mant_b = (|exp_b) ? {1'b1, frac_b} : {1'b0, frac_b};

    // Align mantissas
    wire [exp_width:0] exp_diff = (exp_a > exp_b) ? (exp_a - exp_b) : (exp_b - exp_a);
    wire [sig_width+2:0] mant_a_align = (exp_a >= exp_b) ? {mant_a, 2'b00} : ({mant_a, 2'b00} >> exp_diff);
    wire [sig_width+2:0] mant_b_align = (exp_b > exp_a) ? {mant_b, 2'b00} : ({mant_b, 2'b00} >> exp_diff);

    // Add or subtract based on sign
    reg [sig_width+2:0] mant_add;
    reg [exp_width-1:0] exp_result;
    reg sign_result;

    always @(*) begin
        if (sign_a == sign_b) begin
            mant_add = mant_a_align + mant_b_align;
            sign_result = sign_a;
        end else begin
            if ({exp_a, mant_a} >= {exp_b, mant_b}) begin
                mant_add = mant_a_align - mant_b_align;
                sign_result = sign_a;
            end else begin
                mant_add = mant_b_align - mant_a_align;
                sign_result = sign_b;
            end
        end
        exp_result = (exp_a >= exp_b) ? exp_a : exp_b;
    end

    // Normalize result
    wire [sig_width-1:0] frac_norm;
    wire [2*sig_width-1:0] frac_norms;
    wire [exp_width-1:0] exp_norm;

    wire [$clog2(sig_width+3)-1:0] shift;
    wire                          valid;
    priority_encoder #(
        .WIDTH(sig_width + 3)
    ) pe_inst (
        .in(mant_add),
        .shift(shift),
        .valid(valid)
    );

    assign frac_norms = mant_add << shift;
    assign frac_norm  = frac_norms[sig_width+2:3];
    assign exp_norm   = (exp_result > shift) ? (exp_result - shift) : 0;

    // Final packing
    always @(*) begin
        z = {sign_result, exp_norm, frac_norm};
        status = 8'b0;
        if (mant_add == 0)
            z = {1'b0, {exp_width{1'b0}}, {sig_width{1'b0}}};  // exact zero
    end

endmodule
// module fp_add #(
//   parameter SIG_WIDTH = 23,
//   parameter EXP_WIDTH = 8
// )(
//   input  wire [SIG_WIDTH+EXP_WIDTH:0] a,
//   input  wire [SIG_WIDTH+EXP_WIDTH:0] b,
//   input  wire [2:0] rnd,  // Not used in this basic version
//   output wire [SIG_WIDTH+EXP_WIDTH:0] z,
//   output wire [7:0] status  // Optional exception flags
// );

//   localparam FP_WIDTH = SIG_WIDTH + EXP_WIDTH + 1;
//   localparam EXP_BIAS = (1 << (EXP_WIDTH-1)) - 1;

//   // === Unpack ===
//   wire sign_a = a[FP_WIDTH-1];
//   wire [EXP_WIDTH-1:0] exp_a = a[FP_WIDTH-2 -: EXP_WIDTH];
//   wire [SIG_WIDTH-1:0] frac_a = a[SIG_WIDTH-1:0];

//   wire sign_b = b[FP_WIDTH-1];
//   wire [EXP_WIDTH-1:0] exp_b = b[FP_WIDTH-2 -: EXP_WIDTH];
//   wire [SIG_WIDTH-1:0] frac_b = b[SIG_WIDTH-1:0];

//   // Add implicit leading ones
//   wire [SIG_WIDTH:0] mant_a = (exp_a == 0) ? {1'b0, frac_a} : {1'b1, frac_a};
//   wire [SIG_WIDTH:0] mant_b = (exp_b == 0) ? {1'b0, frac_b} : {1'b1, frac_b};

//   // === Align exponents ===
//   wire [EXP_WIDTH-1:0] exp_diff = (exp_a > exp_b) ? (exp_a - exp_b) : (exp_b - exp_a);

//   wire [SIG_WIDTH+3:0] mant_a_shift, mant_b_shift;
//   wire [EXP_WIDTH-1:0] exp_max;

//   always @(*) begin
//   if (exp_a > exp_b) begin
//     mant_a_shift = {mant_a, 3'b000};
//     mant_b_shift = ({mant_b, 3'b000} >> exp_diff);
//     exp_max = exp_a;
//   end else begin
//     mant_b_shift = {mant_b, 3'b000};
//     mant_a_shift = ({mant_a, 3'b000} >> exp_diff);
//     exp_max = exp_b;
//   end
//   end

//   // === Add/Sub mantissas ===
//   reg [SIG_WIDTH+4:0] mant_sum;
//   reg result_sign;

//   always @(*) begin
//     if (sign_a == sign_b) begin
//       mant_sum = mant_a_shift + mant_b_shift;
//       result_sign = sign_a;
//     end else begin
//       if (mant_a_shift >= mant_b_shift) begin
//         mant_sum = mant_a_shift - mant_b_shift;
//         result_sign = sign_a;
//       end else begin
//         mant_sum = mant_b_shift - mant_a_shift;
//         result_sign = sign_b;
//       end
//     end
//   end

//   // === Normalize ===
//   reg [EXP_WIDTH-1:0] exp_out;
//   reg [SIG_WIDTH-1:0] frac_out;

//   always @(*) begin
//     reg [SIG_WIDTH+4:0] norm_mant = mant_sum;
//     reg [4:0] shift_amt = 0;

//     while (norm_mant[SIG_WIDTH+4] == 0 && exp_max > 0) begin
//       norm_mant = norm_mant << 1;
//       shift_amt = shift_amt + 1;
//     end

//     exp_out = exp_max - shift_amt;
//     frac_out = norm_mant[SIG_WIDTH+3:4];
//   end

//   assign z = {result_sign, exp_out, frac_out};

//   assign status = 8'b0; // add overflow/underflow detection if needed

// endmodule



