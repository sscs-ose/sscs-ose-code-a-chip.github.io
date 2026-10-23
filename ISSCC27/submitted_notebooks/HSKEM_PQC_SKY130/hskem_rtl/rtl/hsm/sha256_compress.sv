module sha256_compress #(
    // ASIC timing candidate: retain the 16-word recurrence window instead of
    // a variable-index 64-word schedule.  The default preserves the qualified
    // FPGA implementation until the candidate passes synthesis and board gates.
    parameter SLIDING_SCHEDULE = 1'b0
) (
    input  wire         clk,
    input  wire         rst_n,
    input  wire         scrub,
    input  wire         start,
    input  wire [255:0] state_in,
    input  wire [511:0] block_in,
    output reg          busy,
    output reg          done,
    output reg  [255:0] state_out
);
    reg [31:0] w [0:63];
    reg [31:0] init_h [0:7];
    reg [31:0] a, b, c, d, e, f, g, h;
    reg [5:0] round;
    integer i;

    reg [31:0] wt;
    reg [31:0] t1;
    reg [31:0] t2;
    reg [31:0] next_a;
    reg [31:0] next_e;
    reg [31:0] schedule_next;

    function automatic [31:0] rotr;
        input [31:0] x;
        input integer n;
        begin rotr = (x >> n) | (x << (32-n)); end
    endfunction

    function automatic [31:0] small_sigma0;
        input [31:0] x;
        begin small_sigma0 = rotr(x,7) ^ rotr(x,18) ^ (x >> 3); end
    endfunction

    function automatic [31:0] small_sigma1;
        input [31:0] x;
        begin small_sigma1 = rotr(x,17) ^ rotr(x,19) ^ (x >> 10); end
    endfunction

    function automatic [31:0] big_sigma0;
        input [31:0] x;
        begin big_sigma0 = rotr(x,2) ^ rotr(x,13) ^ rotr(x,22); end
    endfunction

    function automatic [31:0] big_sigma1;
        input [31:0] x;
        begin big_sigma1 = rotr(x,6) ^ rotr(x,11) ^ rotr(x,25); end
    endfunction

    function automatic [31:0] choose;
        input [31:0] x, y, z;
        begin choose = (x & y) ^ (~x & z); end
    endfunction

    function automatic [31:0] majority;
        input [31:0] x, y, z;
        begin majority = (x & y) ^ (x & z) ^ (y & z); end
    endfunction

    function automatic [31:0] round_k;
        input [5:0] idx;
        begin
            case (idx)
                6'd0: round_k=32'h428a2f98;  6'd1: round_k=32'h71374491;
                6'd2: round_k=32'hb5c0fbcf;  6'd3: round_k=32'he9b5dba5;
                6'd4: round_k=32'h3956c25b;  6'd5: round_k=32'h59f111f1;
                6'd6: round_k=32'h923f82a4;  6'd7: round_k=32'hab1c5ed5;
                6'd8: round_k=32'hd807aa98;  6'd9: round_k=32'h12835b01;
                6'd10:round_k=32'h243185be; 6'd11:round_k=32'h550c7dc3;
                6'd12:round_k=32'h72be5d74; 6'd13:round_k=32'h80deb1fe;
                6'd14:round_k=32'h9bdc06a7; 6'd15:round_k=32'hc19bf174;
                6'd16:round_k=32'he49b69c1; 6'd17:round_k=32'hefbe4786;
                6'd18:round_k=32'h0fc19dc6; 6'd19:round_k=32'h240ca1cc;
                6'd20:round_k=32'h2de92c6f; 6'd21:round_k=32'h4a7484aa;
                6'd22:round_k=32'h5cb0a9dc; 6'd23:round_k=32'h76f988da;
                6'd24:round_k=32'h983e5152; 6'd25:round_k=32'ha831c66d;
                6'd26:round_k=32'hb00327c8; 6'd27:round_k=32'hbf597fc7;
                6'd28:round_k=32'hc6e00bf3; 6'd29:round_k=32'hd5a79147;
                6'd30:round_k=32'h06ca6351; 6'd31:round_k=32'h14292967;
                6'd32:round_k=32'h27b70a85; 6'd33:round_k=32'h2e1b2138;
                6'd34:round_k=32'h4d2c6dfc; 6'd35:round_k=32'h53380d13;
                6'd36:round_k=32'h650a7354; 6'd37:round_k=32'h766a0abb;
                6'd38:round_k=32'h81c2c92e; 6'd39:round_k=32'h92722c85;
                6'd40:round_k=32'ha2bfe8a1; 6'd41:round_k=32'ha81a664b;
                6'd42:round_k=32'hc24b8b70; 6'd43:round_k=32'hc76c51a3;
                6'd44:round_k=32'hd192e819; 6'd45:round_k=32'hd6990624;
                6'd46:round_k=32'hf40e3585; 6'd47:round_k=32'h106aa070;
                6'd48:round_k=32'h19a4c116; 6'd49:round_k=32'h1e376c08;
                6'd50:round_k=32'h2748774c; 6'd51:round_k=32'h34b0bcb5;
                6'd52:round_k=32'h391c0cb3; 6'd53:round_k=32'h4ed8aa4a;
                6'd54:round_k=32'h5b9cca4f; 6'd55:round_k=32'h682e6ff3;
                6'd56:round_k=32'h748f82ee; 6'd57:round_k=32'h78a5636f;
                6'd58:round_k=32'h84c87814; 6'd59:round_k=32'h8cc70208;
                6'd60:round_k=32'h90befffa; 6'd61:round_k=32'ha4506ceb;
                6'd62:round_k=32'hbef9a3f7; default:round_k=32'hc67178f2;
            endcase
        end
    endfunction

    always @* begin
        if (SLIDING_SCHEDULE) begin
            // At round t, w[0:15] holds W[t:t+15].  Fixed taps avoid the
            // 64-to-1 variable-index mux present in the legacy schedule.
            wt = w[0];
            schedule_next = small_sigma1(w[14]) + w[9] +
                            small_sigma0(w[1]) + w[0];
        end else begin
            if (round < 16)
                wt = w[round];
            else
                wt = small_sigma1(w[round-2]) + w[round-7] +
                     small_sigma0(w[round-15]) + w[round-16];
            schedule_next = 32'd0;
        end
        t1 = h + big_sigma1(e) + choose(e,f,g) + round_k(round) + wt;
        t2 = big_sigma0(a) + majority(a,b,c);
        next_a = t1 + t2;
        next_e = d + t1;
    end

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            busy      <= 1'b0;
            done      <= 1'b0;
            state_out <= 256'd0;
            round     <= 6'd0;
            a <= 0; b <= 0; c <= 0; d <= 0;
            e <= 0; f <= 0; g <= 0; h <= 0;
            for (i=0; i<64; i=i+1) w[i] <= 32'd0;
            for (i=0; i<8; i=i+1) init_h[i] <= 32'd0;
        end else if (scrub) begin
            busy      <= 1'b0;
            done      <= 1'b0;
            state_out <= 256'd0;
            round     <= 6'd0;
            a <= 0; b <= 0; c <= 0; d <= 0;
            e <= 0; f <= 0; g <= 0; h <= 0;
            for (i=0; i<64; i=i+1) w[i] <= 32'd0;
            for (i=0; i<8; i=i+1) init_h[i] <= 32'd0;
        end else begin
            done <= 1'b0;
            if (start && !busy) begin
                for (i=0; i<16; i=i+1)
                    w[i] <= block_in[511-i*32 -: 32];
                for (i=16; i<64; i=i+1)
                    w[i] <= 32'd0;
                for (i=0; i<8; i=i+1)
                    init_h[i] <= state_in[255-i*32 -: 32];
                a <= state_in[255:224]; b <= state_in[223:192];
                c <= state_in[191:160]; d <= state_in[159:128];
                e <= state_in[127:96];  f <= state_in[95:64];
                g <= state_in[63:32];   h <= state_in[31:0];
                round <= 6'd0;
                busy  <= 1'b1;
            end else if (busy) begin
                if (SLIDING_SCHEDULE) begin
                    for (i=0; i<15; i=i+1)
                        w[i] <= w[i+1];
                    w[15] <= schedule_next;
                end else if (round >= 16) begin
                    w[round] <= wt;
                end
                a <= next_a;
                b <= a;
                c <= b;
                d <= c;
                e <= next_e;
                f <= e;
                g <= f;
                h <= g;
                if (round == 6'd63) begin
                    state_out <= {init_h[0]+next_a, init_h[1]+a,
                                  init_h[2]+b, init_h[3]+c,
                                  init_h[4]+next_e, init_h[5]+e,
                                  init_h[6]+f, init_h[7]+g};
                    busy <= 1'b0;
                    done <= 1'b1;
                end else begin
                    round <= round + 6'd1;
                end
            end
        end
    end
endmodule
