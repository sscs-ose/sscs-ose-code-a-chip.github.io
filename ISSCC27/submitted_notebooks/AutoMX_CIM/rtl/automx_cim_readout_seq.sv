// Slow physical prototype. SAR completion comes exclusively from the ADC.
// The technology delay line requires post-layout pulse-width measurement;
// its taps are NOT assumed to be calibrated 50 ps units.
`timescale 1ns/1ps
`default_nettype none
module automx_cim_readout_seq #(
    parameter integer BOOT_CYCLES = 8192,
    parameter integer SETTLE_CYCLES = 16,
    parameter integer ADC_TIMEOUT_CYCLES = 4096,
    parameter integer VCM_HALF_PERIOD = 763,
    parameter integer BINARY_DECODE = 1,
    parameter integer CAL_CLOCK_GATING = 1
) (
    input wire clk_i, rst_ni,
    input wire cfg_valid_i, output wire cfg_ready_o,
    input wire [1:0] cfg_row_i,
    input wire [3:0] cfg_wpos_i, cfg_wneg_i,
    input wire cal_valid_i, output wire cal_ready_o,
    input wire [8:0] cal_address_i, input wire [11:0] cal_threshold_i,
    output wire calibrated_o,
    input wire eval_valid_i, output wire eval_ready_o,
    input wire signed [19:0] act_x2_i, input wire raw_mode_i,
    output wire result_valid_o, input wire result_ready_i,
    output reg signed [47:0] result_acc_o,
    output reg [95:0] raw_codes_o,
    output reg result_calibrated_o, output wire fault_o,
    output reg [15:0] weight_pos_o, weight_neg_o,
    output reg [3:0] wlp_o, wln_o,
    output wire pre_b_o, track_o, output reg [3:0] select_o,
    output wire adc_rst_no, adc_start_o, output reg clk_vcm_o,
    input wire adc_eoc_i, input wire [15:0] adc_word_i
);
    localparam [4:0] BOOT=0, IDLE=1, PRE=2, RELEASE=3, PULSE=4,
        HOLD=5, DEAD=6, SETTLE=7, EOC_LOW=8, START=9, WAIT_EOC=10,
        WORD_SETTLE=11, CAPTURE=12, DECODE=13, ADVANCE=14, RESULT=15, FAULT=16,
        CAL_PREV=17, CAL_NEXT=18;
    reg [4:0] state;
    reg [15:0] timer;
    reg [15:0] vcm_count;
    reg phase_b;
    reg [1:0] column;
    reg signed [19:0] acts;
    reg raw_mode;
    reg launch;
    (* async_reg = "true" *) reg eoc_meta, eoc_sync;
    reg [303:0] threshold_valid;
    reg calibration_error;
    reg [11:0] thresholds [0:303];
    // Threshold contents have no reset in the original interface. Only the
    // accepted calibration write may clock this 3,648-bit storage bank.
    wire calibration_write = rst_ni && state==IDLE && cal_valid_i && cal_ready_o;
    wire threshold_clock;
    generate if(CAL_CLOCK_GATING) begin: storage_gating
        automx_calibration_clock_gate gate_i(.clk_i(clk_i),.enable_i(calibration_write),.clk_o(threshold_clock));
    end else begin: storage_ungated
        assign threshold_clock=clk_i;
    end endgenerate
    always @(posedge threshold_clock) begin
        if(calibration_write) thresholds[cal_address_i]<=cal_threshold_i;
    end
    reg [11:0] captured_code;
    reg [5:0] decode_index, decode_bin;
    reg [5:0] decode_low, decode_high;
    wire [8:0] threshold_address = (phase_b ? 9'd152 : 9'd0)+{7'd0,column}*9'd38+{3'd0,decode_index};
    reg [8:0] calibration_address;
    reg [11:0] calibration_value;
    // Share one physical LUT read mux between decoding and the two neighbor
    // checks. Calibration handshakes take three clocks instead of one.
    wire [8:0] threshold_read_address = state==CAL_PREV ? calibration_address-9'd1 :
        state==CAL_NEXT ? calibration_address+9'd1 : threshold_address;
    wire [11:0] threshold_read_data = thresholds[threshold_read_address];
    reg signed [5:0] partial_a [0:3];
    wire [12:0] tap;
    assign tap[0] = launch;
    genvar k;
    generate for (k=1; k<=12; k=k+1) begin: delay_taps
        (* keep = 1, dont_touch = 1 *) sky130_fd_sc_hd__buf_1 delay_i (.A(tap[k-1]), .X(tap[k]));
    end endgenerate
    assign calibrated_o = (&threshold_valid) && !calibration_error && state!=CAL_PREV && state!=CAL_NEXT;
    assign cfg_ready_o = state==IDLE && !eval_valid_i && !(|(cfg_wpos_i & cfg_wneg_i));
    assign cal_ready_o = state==IDLE && !eval_valid_i && cal_address_i < 9'd304;
    assign eval_ready_o = state==IDLE && !cfg_valid_i && !cal_valid_i &&
                          (raw_mode_i || calibrated_o) && valid_acts(act_x2_i);
    assign result_valid_o = state==RESULT;
    assign fault_o = state==FAULT;
    assign pre_b_o = !(state==BOOT || state==IDLE || state==PRE || state==CAL_PREV || state==CAL_NEXT);
    assign track_o = state==PRE || state==RELEASE || state==PULSE;
    assign adc_rst_no = !(state==BOOT || state==IDLE || state==PRE || state==RELEASE ||
                         state==PULSE || state==HOLD || state==DEAD || state==SETTLE || state==FAULT ||
                         state==CAL_PREV || state==CAL_NEXT);
    assign adc_start_o = state==START;

    function automatic [4:0] magnitude(input signed [4:0] x);
        magnitude = x[4] ? (~x+5'd1) : x;
    endfunction
    function automatic valid_acts(input signed [19:0] x);
        integer r;
        reg [4:0] m;
        begin
            valid_acts=1;
            for(r=0;r<4;r=r+1) begin
                m=magnitude(x[5*r+:5]);
                case(m)
                    0,1,2,3,4,6,8,12: ;
                    default: valid_acts=0;
                endcase
            end
        end
    endfunction
    // The reachable two-row integer alphabet is fixed; thresholds are
    // programmed only from measurements of this complete readout path.
    // Explicit unsigned index avoids the int' cast unsupported by the
    // Verilog frontend shipped with OpenLane 30ee138.
    function automatic signed [5:0] level(input [5:0] i);
        begin
            case(i)
              0:level=-24;1:level=-20;2:level=-18;3:level=-16;4:level=-15;
              5:level=-14;6:level=-13;7:level=-12;8:level=-11;9:level=-10;
              10:level=-9;11:level=-8;12:level=-7;13:level=-6;14:level=-5;
              15:level=-4;16:level=-3;17:level=-2;18:level=-1;19:level=0;
              20:level=1;21:level=2;22:level=3;23:level=4;24:level=5;
              25:level=6;26:level=7;27:level=8;28:level=9;29:level=10;
              30:level=11;31:level=12;32:level=13;33:level=14;34:level=15;
              35:level=16;36:level=18;37:level=20;38:level=24;
              default:level=0;
            endcase
        end
    endfunction
    integer row;
    reg [4:0] mag;
    always @* begin
        wlp_o=0; wln_o=0; select_o=0;
        for(row=0;row<4;row=row+1) begin
            mag=magnitude(acts[5*row+:5]);
            if(state==PULSE && (row>=2)==phase_b && mag>0 && mag<=12) begin
                if(acts[5*row+4]) wln_o[row]=launch && !tap[mag[3:0]];
                else wlp_o[row]=launch && !tap[mag[3:0]];
            end
        end
        if(state>=SETTLE && state<=CAPTURE) select_o=4'b0001<<column;
    end
    integer i;
    reg signed [5:0] decoded;
    reg signed [11:0] sum;
    reg [5:0] next_bin;
    reg [5:0] next_low, next_high;
    reg decode_done;
    always @(posedge clk_i or negedge rst_ni) begin
        if(!rst_ni) begin
            state<=BOOT; timer<=0; vcm_count<=0; clk_vcm_o<=0;
            phase_b<=0; column<=0; acts<=0; raw_mode<=0; launch<=0;
            weight_pos_o<=0; weight_neg_o<=0; threshold_valid<=0;calibration_error<=0;
            calibration_address<=0;calibration_value<=0;
            captured_code<=0;decode_index<=0;decode_bin<=0;
            decode_low<=0;decode_high<=38;
            result_acc_o<=0; raw_codes_o<=0; result_calibrated_o<=0;
            eoc_meta<=0; eoc_sync<=0;
            for(i=0;i<4;i=i+1) partial_a[i]<=0;
        end else begin
            eoc_meta<=adc_eoc_i; eoc_sync<=eoc_meta;
            if(vcm_count==VCM_HALF_PERIOD-1) begin vcm_count<=0; clk_vcm_o<=!clk_vcm_o; end
            else vcm_count<=vcm_count+1;
            timer<=timer+1;
            case(state)
                BOOT: if(timer>=BOOT_CYCLES-1) begin state<=IDLE; timer<=0; end
                IDLE: begin
                    timer<=0; launch<=0;
                    if(cfg_valid_i && cfg_ready_o) begin
                        weight_pos_o[4*cfg_row_i+:4]<=cfg_wpos_i;
                        weight_neg_o[4*cfg_row_i+:4]<=cfg_wneg_i;
                    end
                    if(cal_valid_i && cal_ready_o) begin
                        threshold_valid[cal_address_i]<=1;
                        calibration_address<=cal_address_i;calibration_value<=cal_threshold_i;
                        state<=CAL_PREV;
                    end
                    if(eval_valid_i && eval_ready_o) begin
                        acts<=act_x2_i; raw_mode<=raw_mode_i; phase_b<=0; column<=0;
                        result_calibrated_o<=0; result_acc_o<=0; raw_codes_o<=0;
                        state<=PRE;
                    end
                end
                CAL_PREV: begin
                    if(calibration_address%38!=0 && threshold_valid[threshold_read_address] &&
                       calibration_value<=threshold_read_data) calibration_error<=1;
                    state<=CAL_NEXT;
                end
                CAL_NEXT: begin
                    if(calibration_address%38!=37 && threshold_valid[threshold_read_address] &&
                       calibration_value>=threshold_read_data) calibration_error<=1;
                    state<=IDLE;timer<=0;
                end
                PRE: if(timer>=1) begin state<=RELEASE; timer<=0; end
                RELEASE: begin state<=PULSE; timer<=0; launch<=1; end
                PULSE: begin launch<=0; state<=HOLD; timer<=0; end
                HOLD: begin state<=DEAD; timer<=0; end
                DEAD: begin state<=SETTLE; timer<=0; end
                SETTLE: if(timer>=SETTLE_CYCLES-1) begin state<=EOC_LOW; timer<=0; end
                EOC_LOW: begin
                    if(!eoc_sync) begin state<=START; timer<=0; end
                    else if(timer>=ADC_TIMEOUT_CYCLES-1) state<=FAULT;
                end
                START: begin state<=WAIT_EOC; timer<=0; end
                WAIT_EOC: begin
                    if(eoc_sync) begin state<=WORD_SETTLE; timer<=0; end
                    else if(timer>=ADC_TIMEOUT_CYCLES-1) state<=FAULT;
                end
                WORD_SETTLE: if(timer>=2) begin state<=CAPTURE; timer<=0; end
                CAPTURE: begin
                    if(adc_word_i[3:0]!=0) state<=FAULT;
                    else begin
                        raw_codes_o[(phase_b ? 48 : 0)+12*column+:12]<=adc_word_i[15:4];
                        captured_code<=adc_word_i[15:4];
                        decode_index<=BINARY_DECODE ? 6'd19 : 6'd0;decode_bin<=0;
                        decode_low<=0;decode_high<=38;
                        state<=raw_mode ? ADVANCE : DECODE;timer<=0;
                    end
                end
                // Upper bound: count thresholds <= code. Strictly increasing
                // calibration is checked above. The half-open [low, high)
                // search uses the same single LUT read, at most six clocks.
                // BINARY_DECODE=0 retains the measured 38-clock baseline.
                DECODE: begin
                    if(BINARY_DECODE) begin
                        next_low=decode_low;next_high=decode_high;
                        if(captured_code>=threshold_read_data) next_low=decode_index+6'd1;
                        else next_high=decode_index;
                        next_bin=next_low;
                        decode_done=next_low==next_high;
                    end else begin
                        next_bin=decode_bin+(captured_code>=threshold_read_data ? 6'd1 : 6'd0);
                        decode_done=decode_index==37;
                    end
                    if(decode_done) begin
                        decoded=level(next_bin);
                        if(!phase_b) partial_a[column]<=decoded;
                        else begin
                            sum={{6{partial_a[column][5]}},partial_a[column]}+{{6{decoded[5]}},decoded};
                            result_acc_o[12*column+:12]<=sum;
                        end
                        state<=ADVANCE;timer<=0;
                    end else if(BINARY_DECODE) begin
                        decode_low<=next_low;decode_high<=next_high;
                        decode_index<=({1'b0,next_low}+{1'b0,next_high})>>1;
                    end else begin decode_index<=decode_index+1;decode_bin<=next_bin;end
                end
                ADVANCE: begin
                    timer<=0;
                    if(column!=3) begin column<=column+1; state<=DEAD; end
                    else if(!phase_b) begin phase_b<=1; column<=0; state<=PRE; end
                    else begin state<=RESULT; result_calibrated_o<=!raw_mode && calibrated_o; end
                end
                RESULT: if(result_ready_i) begin state<=IDLE; timer<=0; end
                FAULT: ;
                default: state<=FAULT;
            endcase
        end
    end
endmodule
// Portable latch model for RTL; the physical flow maps the characterized ICG.
module automx_calibration_clock_gate(input wire clk_i,enable_i,output wire clk_o);
`ifdef SYNTHESIS
    (* keep=1 *) sky130_fd_sc_hd__dlclkp_1 icg_i(.CLK(clk_i),.GATE(enable_i),.GCLK(clk_o));
`else
    reg enable_latched;
    always @* if(!clk_i) enable_latched=enable_i;
    assign clk_o=clk_i && enable_latched;
`endif
endmodule
`default_nettype wire
