// ============================================================================
//  fp32_funcs.vh -- synthesizable binary32 multiply / add as Verilog functions
//  (included inside modules; the modules fp32_mul.v / fp32_add.v are thin
//   wrappers so the same code is used everywhere)
// ============================================================================
function [31:0] fmul32(input [31:0] a, input [31:0] b);
  reg [7:0] ea, eb;
  reg [22:0] fa, fb, man, man_f;
  reg [23:0] ma, mb, man_r;
  reg [47:0] p;
  reg hi, gd, st, rup, ovf, zero, inf;
  reg signed [9:0] ex, ex_f;
  begin
    ea = a[30:23]; eb = b[30:23];
    fa = a[22:0];  fb = b[22:0];
    ma = (ea == 8'd0) ? 24'd0 : {1'b1, fa};
    mb = (eb == 8'd0) ? 24'd0 : {1'b1, fb};
    p  = ma * mb;
    hi = p[47];
    man = hi ? p[46:24] : p[45:23];
    gd  = hi ? p[23] : p[22];
    st  = hi ? (|p[22:0]) : (|p[21:0]);
    ex  = $signed({2'b00, ea}) + $signed({2'b00, eb}) - 10'sd127
          + (hi ? 10'sd1 : 10'sd0);
    rup = gd & (st | man[0]);
    man_r = {1'b0, man} + {23'd0, rup};
    ovf = man_r[23];
    man_f = ovf ? man_r[23:1] : man_r[22:0];
    ex_f = ex + (ovf ? 10'sd1 : 10'sd0);
    zero = (ea == 8'd0) | (eb == 8'd0) | (ex_f <= 0);
    inf  = (ex_f >= 255);
    fmul32 = zero ? 32'h0000_0000 :
             inf  ? {a[31] ^ b[31], 8'hFF, 23'h0} :
                    {a[31] ^ b[31], ex_f[7:0], man_f};
  end
endfunction

function [31:0] fadd32(input [31:0] a, input [31:0] b);
  reg [7:0] ea, eb, e_big, e_sml, d;
  reg [22:0] fa, fb, f_big, f_sml, man, man_f;
  reg [23:0] m_big, m_sml, man_r;
  reg [32:0] m_big_a, m_sml_ext, m_sml_sh, mask33, m_sml_a;
  reg [32:0] sum_raw, sum_c, sum_n;
  reg [31:0] r;
  reg [5:0] lz;
  reg found, carry, gd, stk, rup, ovf, zero, inf, sgn, a_zero, b_zero;
  reg signed [9:0] ex;
  integer i;
  begin
    ea = a[30:23]; eb = b[30:23];
    fa = a[22:0];  fb = b[22:0];
    a_zero = (ea == 8'd0);
    b_zero = (eb == 8'd0);

    if (a_zero)      fadd32 = b;
    else if (b_zero) fadd32 = a;
    else begin
      // order by magnitude
      if ((ea > eb) || (ea == eb && fa >= fb)) begin
        e_big = ea; e_sml = eb; f_big = fa; f_sml = fb;
        sgn = a[31];
      end else begin
        e_big = eb; e_sml = ea; f_big = fb; f_sml = fa;
        sgn = b[31];
      end
      m_big = {1'b1, f_big};
      m_sml = {1'b1, f_sml};
      d = e_big - e_sml;

      m_big_a   = {2'b00, m_big, 7'b0000000};
      m_sml_ext = {2'b00, m_sml, 7'b0000000};
      if (d >= 8'd33) begin
        m_sml_sh = 33'd0;
        mask33   = {33{1'b1}};
      end else begin
        m_sml_sh = m_sml_ext >> d;
        mask33   = (33'd1 << d) - 33'd1;
      end
      m_sml_a = m_sml_sh | {{32{1'b0}}, ((|(m_sml_ext & mask33)) | (d >= 8'd33))};

      if (a[31] == b[31]) sum_raw = m_big_a + m_sml_a;
      else                sum_raw = m_big_a - m_sml_a;

      carry = sum_raw[31];
      if (carry) sum_c = (sum_raw >> 1) | {{32{1'b0}}, sum_raw[0]};
      else       sum_c = sum_raw;

      lz = 6'd0; found = 1'b0;
      for (i = 30; i >= 0; i = i - 1)
        if (sum_c[i] == 1'b1 && !found) begin
          lz = 30 - i;
          found = 1'b1;
        end

      sum_n = (sum_c == 33'd0) ? 33'd0 : (sum_c << lz);
      man   = sum_n[29:7];
      gd    = sum_n[6];
      stk   = |sum_n[5:0];
      rup   = gd & (stk | man[0]);
      man_r = {1'b0, man} + {23'd0, rup};
      ovf   = man_r[23];
      man_f = ovf ? man_r[23:1] : man_r[22:0];

      ex = $signed({2'b00, e_big}) + (carry ? 10'sd1 : 10'sd0)
           - $signed({4'b0000, lz}) + (ovf ? 10'sd1 : 10'sd0);
      zero = (sum_c == 33'd0) || (ex <= 0);
      inf  = (ex >= 255);
      r = zero ? 32'h0 : inf ? {sgn, 8'hFF, 23'h0} : {sgn, ex[7:0], man_f};
      fadd32 = r;
    end
  end
endfunction
