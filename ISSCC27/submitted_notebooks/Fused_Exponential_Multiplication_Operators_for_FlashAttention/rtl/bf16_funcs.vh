// ============================================================================
//  bf16_funcs.vh -- bfloat16 (1-8-7) multiply / add as Verilog functions
//  Round-to-nearest-even, flush-to-zero. Included inside modules.
// ============================================================================
function [15:0] fmul16(input [15:0] a, input [15:0] b);
  reg [7:0] ea, eb, ma, mb;
  reg [15:0] p;
  reg [6:0] man, man_f;
  reg [7:0] man_r;
  reg hi, gd, st, rup, ovf, zero, inf;
  reg signed [9:0] ex, ex_f;
  begin
    ea = a[14:7]; eb = b[14:7];
    ma = (ea == 8'd0) ? 8'd0 : {1'b1, a[6:0]};
    mb = (eb == 8'd0) ? 8'd0 : {1'b1, b[6:0]};
    p  = ma * mb;                       // [1,4)
    hi = p[15];
    man = hi ? p[14:8] : p[13:7];
    gd  = hi ? p[7]    : p[6];
    st  = hi ? (|p[6:0]) : (|p[5:0]);
    ex  = $signed({2'b00, ea}) + $signed({2'b00, eb}) - 10'sd127 + (hi ? 10'sd1 : 10'sd0);
    rup = gd & (st | man[0]);
    man_r = {1'b0, man} + {7'd0, rup};
    ovf = man_r[7];
    man_f = ovf ? man_r[7:1] : man_r[6:0];
    ex_f = ex + (ovf ? 10'sd1 : 10'sd0);
    zero = (ea == 8'd0) | (eb == 8'd0) | (ex_f <= 0);
    inf  = (ex_f >= 255);
    fmul16 = zero ? 16'h0000 :
             inf  ? {a[15] ^ b[15], 8'hFF, 7'h0} :
                    {a[15] ^ b[15], ex_f[7:0], man_f};
  end
endfunction

function [15:0] fadd16(input [15:0] a, input [15:0] b);
  reg [7:0] ea, eb, e_big, e_sml, d;
  reg [6:0] fa, fb, f_big, f_sml, man, man_f;
  reg [7:0] m_big, m_sml, man_r;
  reg [17:0] m_big_a, m_sml_ext, m_sml_sh, mask18, m_sml_a, sum_raw, sum_c, sum_n;
  reg [15:0] r;
  reg [4:0] lz;
  reg found, carry, gd, stk, rup, ovf, zero, inf, sgn, a_zero, b_zero;
  reg signed [9:0] ex;
  integer i;
  begin
    ea = a[14:7]; eb = b[14:7];
    fa = a[6:0];  fb = b[6:0];
    a_zero = (ea == 8'd0);
    b_zero = (eb == 8'd0);
    if (a_zero)      fadd16 = b;
    else if (b_zero) fadd16 = a;
    else begin
      if ((ea > eb) || (ea == eb && fa >= fb)) begin
        e_big = ea; e_sml = eb; f_big = fa; f_sml = fb; sgn = a[15];
      end else begin
        e_big = eb; e_sml = ea; f_big = fb; f_sml = fa; sgn = b[15];
      end
      m_big = {1'b1, f_big};
      m_sml = {1'b1, f_sml};
      d = e_big - e_sml;
      m_big_a   = {3'b000, m_big, 7'b0000000};
      m_sml_ext = {3'b000, m_sml, 7'b0000000};
      if (d >= 8'd18) begin
        m_sml_sh = 18'd0;
        mask18   = {18{1'b1}};
      end else begin
        m_sml_sh = m_sml_ext >> d;
        mask18   = (18'd1 << d) - 18'd1;
      end
      m_sml_a = m_sml_sh | {{17{1'b0}}, ((|(m_sml_ext & mask18)) | (d >= 8'd18))};
      if (a[15] == b[15]) sum_raw = m_big_a + m_sml_a;
      else                sum_raw = m_big_a - m_sml_a;
      carry = sum_raw[15];
      if (carry) sum_c = (sum_raw >> 1) | {{17{1'b0}}, sum_raw[0]};
      else       sum_c = sum_raw;
      lz = 5'd0; found = 1'b0;
      for (i = 14; i >= 0; i = i - 1)
        if (sum_c[i] == 1'b1 && !found) begin
          lz = 14 - i;
          found = 1'b1;
        end
      sum_n = (sum_c == 18'd0) ? 18'd0 : (sum_c << lz);
      man   = sum_n[13:7];
      gd    = sum_n[6];
      stk   = |sum_n[5:0];
      rup   = gd & (stk | man[0]);
      man_r = {1'b0, man} + {7'd0, rup};
      ovf   = man_r[7];
      man_f = ovf ? man_r[7:1] : man_r[6:0];
      ex = $signed({2'b00, e_big}) + (carry ? 10'sd1 : 10'sd0)
           - $signed({5'b00000, lz}) + (ovf ? 10'sd1 : 10'sd0);
      zero = (sum_c == 18'd0) || (ex <= 0);
      inf  = (ex >= 255);
      r = zero ? 16'h0 : inf ? {sgn, 8'hFF, 7'h0} : {sgn, ex[7:0], man_f};
      fadd16 = r;
    end
  end
endfunction
