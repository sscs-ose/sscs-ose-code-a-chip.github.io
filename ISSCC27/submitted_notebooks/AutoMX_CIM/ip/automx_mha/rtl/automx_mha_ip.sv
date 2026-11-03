// Copyright 2026 EDABK Laboratory.
// Two-token, four-channel, two-head MHA. All arithmetic is synthesizable.
// Projection backend: the existing four-column CIM/SAR readout handshake.
`default_nettype none
module automx_mha_ip #(
    parameter integer CORE_TIMEOUT_CYCLES = 1048576
) (
    input wire clk_i, rst_ni,
    input wire cfg_valid_i, output wire cfg_ready_o,
    input wire [1:0] cfg_stage_i, cfg_row_i,
    input wire [3:0] cfg_wpos_i, cfg_wneg_i,
    input wire req_valid_i, output wire req_ready_o,
    input wire [39:0] req_act_x2_i,
    output wire rsp_valid_o, input wire rsp_ready_i,
    output wire rsp_row_o, output wire [47:0] rsp_result_x2_o,
    output wire busy_o, fault_o,
    input wire core_available_i, core_fault_i,
    output wire core_cfg_valid_o, input wire core_cfg_ready_i,
    output wire [1:0] core_cfg_row_o,
    output wire [3:0] core_cfg_wpos_o, core_cfg_wneg_o,
    output wire core_eval_valid_o, input wire core_eval_ready_i,
    output wire [19:0] core_act_x2_o,
    input wire core_result_valid_i, output wire core_result_ready_o,
    input wire [47:0] core_result_x2_i,
    input wire core_result_calibrated_i
);
    localparam [3:0] IDLE=0, CONFIGURE=1, ISSUE=2, COLLECT=3,
        SCORE=4, SM_LO=5, SM_HI=6, SM_INTERPOLATE=7, NEXT_PAIR=8,
        CONTEXT=9, OUTPUT_ROWS=10, ERROR_STATE=11;
    reg [3:0] state;
    reg [3:0] wpos [0:15], wneg [0:15];
    reg [15:0] weights_loaded;
    reg [19:0] input_acts [0:1], context_acts [0:1];
    reg signed [11:0] q_mem [0:7], k_mem [0:7], v_mem [0:7];
    reg [15:0] probabilities [0:7]; // unsigned Q0.15, including 1 = 32768
    reg [47:0] output_rows [0:1];
    reg [1:0] projection, config_row;
    reg token, head, query_row, key_row, lane, output_row;
    reg signed [39:0] accumulator;
    reg signed [31:0] first_score;
    reg sm_negative;
    reg [5:0] sm_index;
    reg [6:0] sm_fraction;
    reg [15:0] sm_low, sm_high;
    reg [31:0] watchdog;

    function automatic valid_activation(input [39:0] packed_acts);
        integer i; reg signed [4:0] value; reg [4:0] magnitude;
        begin
            valid_activation=1'b1;
            for(i=0;i<8;i=i+1) begin
                value=$signed(packed_acts[5*i+:5]);
                magnitude=value[4] ? -value : value;
                case(magnitude)
                    0,1,2,3,4,6,8,12: ;
                    default: valid_activation=1'b0;
                endcase
            end
        end
    endfunction

    // Nearest MXFP4 E2M1 magnitude; exact ties choose the smaller magnitude,
    // matching the notebook's ordered argmin. Input is X2 times Q0.15.
    function automatic signed [4:0] quantize_context(input signed [39:0] value);
        reg [39:0] magnitude; reg signed [4:0] code;
        begin
            magnitude=value[39] ? -value : value;
            if(magnitude<=40'd16384) code=0;
            else if(magnitude<=40'd49152) code=1;
            else if(magnitude<=40'd81920) code=2;
            else if(magnitude<=40'd114688) code=3;
            else if(magnitude<=40'd163840) code=4;
            else if(magnitude<=40'd229376) code=6;
            else if(magnitude<=40'd327680) code=8;
            else code=12;
            quantize_context=value[39] ? -code : code;
        end
    endfunction

    // sigmoid(i/8), Q0.15. The second probability is the exact complement.
    // Linear interpolation uses the same multiplier as QK^T and A@V.
    function automatic [15:0] sigmoid_lut(input [6:0] index);
        begin
            case(index)
                7'd0: sigmoid_lut=16'd16384;
                7'd1: sigmoid_lut=16'd17407;
                7'd2: sigmoid_lut=16'd18421;
                7'd3: sigmoid_lut=16'd19420;
                7'd4: sigmoid_lut=16'd20397;
                7'd5: sigmoid_lut=16'd21344;
                7'd6: sigmoid_lut=16'd22255;
                7'd7: sigmoid_lut=16'd23127;
                7'd8: sigmoid_lut=16'd23955;
                7'd9: sigmoid_lut=16'd24737;
                7'd10: sigmoid_lut=16'd25471;
                7'd11: sigmoid_lut=16'd26155;
                7'd12: sigmoid_lut=16'd26790;
                7'd13: sigmoid_lut=16'd27377;
                7'd14: sigmoid_lut=16'd27917;
                7'd15: sigmoid_lut=16'd28411;
                7'd16: sigmoid_lut=16'd28862;
                7'd17: sigmoid_lut=16'd29272;
                7'd18: sigmoid_lut=16'd29644;
                7'd19: sigmoid_lut=16'd29979;
                7'd20: sigmoid_lut=16'd30282;
                7'd21: sigmoid_lut=16'd30555;
                7'd22: sigmoid_lut=16'd30799;
                7'd23: sigmoid_lut=16'd31018;
                7'd24: sigmoid_lut=16'd31214;
                7'd25: sigmoid_lut=16'd31389;
                7'd26: sigmoid_lut=16'd31545;
                7'd27: sigmoid_lut=16'd31684;
                7'd28: sigmoid_lut=16'd31807;
                7'd29: sigmoid_lut=16'd31917;
                7'd30: sigmoid_lut=16'd32015;
                7'd31: sigmoid_lut=16'd32102;
                7'd32: sigmoid_lut=16'd32179;
                7'd33: sigmoid_lut=16'd32247;
                7'd34: sigmoid_lut=16'd32307;
                7'd35: sigmoid_lut=16'd32361;
                7'd36: sigmoid_lut=16'd32408;
                7'd37: sigmoid_lut=16'd32450;
                7'd38: sigmoid_lut=16'd32487;
                7'd39: sigmoid_lut=16'd32520;
                7'd40: sigmoid_lut=16'd32549;
                7'd41: sigmoid_lut=16'd32574;
                7'd42: sigmoid_lut=16'd32597;
                7'd43: sigmoid_lut=16'd32617;
                7'd44: sigmoid_lut=16'd32635;
                7'd45: sigmoid_lut=16'd32650;
                7'd46: sigmoid_lut=16'd32664;
                7'd47: sigmoid_lut=16'd32676;
                7'd48: sigmoid_lut=16'd32687;
                7'd49: sigmoid_lut=16'd32696;
                7'd50: sigmoid_lut=16'd32705;
                7'd51: sigmoid_lut=16'd32712;
                7'd52: sigmoid_lut=16'd32719;
                7'd53: sigmoid_lut=16'd32725;
                7'd54: sigmoid_lut=16'd32730;
                7'd55: sigmoid_lut=16'd32734;
                7'd56: sigmoid_lut=16'd32738;
                7'd57: sigmoid_lut=16'd32742;
                7'd58: sigmoid_lut=16'd32745;
                7'd59: sigmoid_lut=16'd32747;
                7'd60: sigmoid_lut=16'd32750;
                7'd61: sigmoid_lut=16'd32752;
                7'd62: sigmoid_lut=16'd32754;
                7'd63: sigmoid_lut=16'd32756;
                7'd64: sigmoid_lut=16'd32757;
                default: sigmoid_lut=16'd32768;
            endcase
        end
    endfunction

    assign cfg_ready_o=rst_ni && state==IDLE && !req_valid_i && !(|(cfg_wpos_i&cfg_wneg_i));
    assign req_ready_o=rst_ni && state==IDLE && (&weights_loaded) && core_available_i && !cfg_valid_i && !core_fault_i;
    assign rsp_valid_o=state==OUTPUT_ROWS;
    assign rsp_row_o=output_row;
    assign rsp_result_x2_o=output_rows[output_row];
    assign busy_o=state!=IDLE;
    assign fault_o=state==ERROR_STATE;
    assign core_cfg_valid_o=state==CONFIGURE;
    assign core_cfg_row_o=config_row;
    assign core_cfg_wpos_o=wpos[{projection,config_row}];
    assign core_cfg_wneg_o=wneg[{projection,config_row}];
    assign core_eval_valid_o=state==ISSUE;
    assign core_act_x2_o=(state==ISSUE || state==COLLECT) ? (projection==2'd3 ? context_acts[token] : input_acts[token]) : 20'd0;
    assign core_result_ready_o=state==COLLECT;

    // A single signed 18x18 multiplier is shared across all attention math.
    reg signed [17:0] multiply_a, multiply_b;
    wire signed [35:0] product=multiply_a*multiply_b;
    wire signed [39:0] mac_sum=accumulator+{{4{product[35]}},product};
    wire [2:0] q_address={query_row,head,lane};
    wire [2:0] kv_address={key_row,head,lane};
    wire [2:0] probability_address={head,query_row,key_row};
    wire signed [39:0] score_difference={{8{first_score[31]}},first_score}-mac_sum;
    wire [39:0] difference_magnitude=score_difference[39] ? -score_difference : score_difference;
    // Stored Q/K values are twice their real value. 181/1024 approximates
    // 1/(4*sqrt(2)); sigmoid input therefore has ten fractional bits.
    wire [21:0] scaled_difference=difference_magnitude[12:0]*9'd181;
    wire [15:0] interpolated_probability=sm_low+((product+36'sd64)>>>7);
    wire [15:0] first_probability=sm_negative ? 16'd32768-interpolated_probability : interpolated_probability;
    always @* begin
        multiply_a=0; multiply_b=0;
        case(state)
            SCORE: begin
                multiply_a={{6{q_mem[q_address][11]}},q_mem[q_address]};
                multiply_b={{6{k_mem[kv_address][11]}},k_mem[kv_address]};
            end
            SM_INTERPOLATE: begin
                multiply_a=$signed({2'b0,sm_high})-$signed({2'b0,sm_low});
                multiply_b=$signed({11'b0,sm_fraction});
            end
            CONTEXT: begin
                multiply_a={{6{v_mem[kv_address][11]}},v_mem[kv_address]};
                multiply_b=$signed({2'b0,probabilities[probability_address]});
            end
            default: ;
        endcase
    end

    integer i;
    // Data buffers have no asynchronous reset: loaded flags and FSM sequencing
    // guarantee complete writes before use. Only control/valid state resets.
    // This avoids a 1500-sink global reset on the SKY130 prototype.
    always @(posedge clk_i) begin
        case(state)
            IDLE: begin
                if(cfg_valid_i && cfg_ready_o) begin
                    wpos[{cfg_stage_i,cfg_row_i}]<=cfg_wpos_i;
                    wneg[{cfg_stage_i,cfg_row_i}]<=cfg_wneg_i;
                end
                if(req_valid_i && req_ready_o && valid_activation(req_act_x2_i)) begin
                    input_acts[0]<=req_act_x2_i[19:0];input_acts[1]<=req_act_x2_i[39:20];
                    context_acts[0]<=0;context_acts[1]<=0;
                end
            end
            COLLECT: if(core_result_valid_i && core_result_calibrated_i) begin
                for(i=0;i<4;i=i+1) begin
                    case(projection)
                        0:q_mem[4*token+i]<=core_result_x2_i[12*i+:12];
                        1:k_mem[4*token+i]<=core_result_x2_i[12*i+:12];
                        2:v_mem[4*token+i]<=core_result_x2_i[12*i+:12];
                        3:output_rows[token][12*i+:12]<=core_result_x2_i[12*i+:12];
                    endcase
                end
                if(token && projection==2)accumulator<=0;
            end
            SCORE: begin
                if(!lane)accumulator<=mac_sum;
                else begin
                    accumulator<=0;
                    if(!key_row)first_score<=mac_sum[31:0];
                    else if(difference_magnitude>=40'd46) begin
                        probabilities[{head,query_row,1'b0}]<=score_difference[39] ? 16'd0 : 16'd32768;
                        probabilities[{head,query_row,1'b1}]<=score_difference[39] ? 16'd32768 : 16'd0;
                    end else begin
                        sm_negative<=score_difference[39];sm_index<=scaled_difference[12:7];sm_fraction<=scaled_difference[6:0];
                    end
                end
            end
            SM_LO: sm_low<=sigmoid_lut({1'b0,sm_index});
            SM_HI: sm_high<=sigmoid_lut({1'b0,sm_index}+7'd1);
            SM_INTERPOLATE: begin
                probabilities[{head,query_row,1'b0}]<=first_probability;
                probabilities[{head,query_row,1'b1}]<=16'd32768-first_probability;
            end
            NEXT_PAIR: accumulator<=0;
            CONTEXT: begin
                if(!key_row)accumulator<=mac_sum;
                else begin
                    context_acts[query_row][5*{head,lane}+:5]<=quantize_context(mac_sum);
                    accumulator<=0;
                end
            end
            default: ;
        endcase
    end

    always @(posedge clk_i or negedge rst_ni) begin
        if(!rst_ni) begin
            state<=IDLE;weights_loaded<=0;projection<=0;config_row<=0;token<=0;
            head<=0;query_row<=0;key_row<=0;lane<=0;output_row<=0;watchdog<=0;
        end else begin
            if(state==CONFIGURE || state==ISSUE || state==COLLECT)watchdog<=watchdog+1;
            else watchdog<=0;
            case(state)
                IDLE: begin
                    if(cfg_valid_i && cfg_ready_o)weights_loaded[{cfg_stage_i,cfg_row_i}]<=1'b1;
                    if(req_valid_i && req_ready_o) begin
                        if(!valid_activation(req_act_x2_i))state<=ERROR_STATE;
                        else begin projection<=0;config_row<=0;token<=0;state<=CONFIGURE;watchdog<=0;end
                    end
                end
                CONFIGURE: if(core_cfg_ready_i) begin
                    watchdog<=0;
                    if(config_row==3)begin config_row<=0;state<=ISSUE;end
                    else config_row<=config_row+1'b1;
                end
                ISSUE: if(core_eval_ready_i)begin watchdog<=0;state<=COLLECT;end
                COLLECT: if(core_result_valid_i) begin
                    watchdog<=0;
                    if(!core_result_calibrated_i)state<=ERROR_STATE;
                    else if(!token)begin token<=1;state<=ISSUE;end
                    else if(projection<2)begin projection<=projection+1'b1;config_row<=0;token<=0;state<=CONFIGURE;end
                    else if(projection==2)begin head<=0;query_row<=0;key_row<=0;lane<=0;state<=SCORE;end
                    else begin output_row<=0;state<=OUTPUT_ROWS;end
                end
                SCORE: begin
                    if(!lane)lane<=1;
                    else begin
                        lane<=0;
                        if(!key_row)key_row<=1;
                        else if(difference_magnitude>=40'd46)state<=NEXT_PAIR;
                        else state<=SM_LO;
                    end
                end
                SM_LO: state<=SM_HI;
                SM_HI: state<=SM_INTERPOLATE;
                SM_INTERPOLATE: state<=NEXT_PAIR;
                NEXT_PAIR: begin
                    key_row<=0;lane<=0;
                    if(!query_row)begin query_row<=1;state<=SCORE;end
                    else if(!head)begin head<=1;query_row<=0;state<=SCORE;end
                    else begin head<=0;query_row<=0;state<=CONTEXT;end
                end
                CONTEXT: begin
                    if(!key_row)key_row<=1;
                    else begin
                        key_row<=0;
                        if(!lane)lane<=1;
                        else if(!head)begin lane<=0;head<=1;end
                        else if(!query_row)begin lane<=0;head<=0;query_row<=1;end
                        else begin projection<=3;config_row<=0;token<=0;state<=CONFIGURE;end
                    end
                end
                OUTPUT_ROWS: if(rsp_ready_i)begin
                    if(!output_row)output_row<=1;
                    else state<=IDLE;
                end
                ERROR_STATE: ;
                default: state<=ERROR_STATE;
            endcase
            if(state!=IDLE && state!=ERROR_STATE && core_fault_i)state<=ERROR_STATE;
            if((state==CONFIGURE || state==ISSUE || state==COLLECT) && watchdog>=CORE_TIMEOUT_CYCLES-1)state<=ERROR_STATE;
        end
    end
endmodule
`default_nettype wire
