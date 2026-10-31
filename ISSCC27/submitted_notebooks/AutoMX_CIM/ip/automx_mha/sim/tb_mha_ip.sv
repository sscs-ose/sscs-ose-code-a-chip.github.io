`timescale 1ns/1ps
module tb_mha_ip;
    reg clk_i=0,rst_ni=0;always #5 clk_i=~clk_i;
    reg cfg_valid_i=0;wire cfg_ready_o;
    reg [1:0] cfg_stage_i=0,cfg_row_i=0;reg [3:0] cfg_wpos_i=0,cfg_wneg_i=0;
    reg req_valid_i=0;wire req_ready_o;reg [39:0] req_act_x2_i=0;
    wire rsp_valid_o;reg rsp_ready_i=0;wire rsp_row_o;wire [47:0] rsp_result_x2_o;wire busy_o,fault_o;
    reg core_available_i=1,core_fault_i=0;
    wire core_cfg_valid_o;wire core_cfg_ready_i;
    wire [1:0] core_cfg_row_o;wire [3:0] core_cfg_wpos_o,core_cfg_wneg_o;
    wire core_eval_valid_o;wire core_eval_ready_i;wire [19:0] core_act_x2_o;
    reg core_result_valid_i=0;wire core_result_ready_o;reg [47:0] core_result_x2_i=0;
    reg core_result_calibrated_i=1;
    automx_mha_ip #(.CORE_TIMEOUT_CYCLES(80)) dut(.*);
    reg [15:0] lfsr=16'h721b;
    reg [3:0] backend_pos[0:3],backend_neg[0:3];
    integer countdown=0,projection_count=0,backend_count=0;
    reg freeze_backend=0;
    assign core_cfg_ready_i=!freeze_backend && lfsr[0];
    assign core_eval_ready_i=!freeze_backend && countdown==0 && !core_result_valid_i && lfsr[1];
    integer r,c,s;
    always @(posedge clk_i) begin
        if(!rst_ni) begin
            lfsr<=16'h721b;countdown<=0;core_result_valid_i<=0;projection_count<=0;
        end else begin
            lfsr<={lfsr[14:0],lfsr[15]^lfsr[13]^lfsr[12]^lfsr[10]};
            if(core_cfg_valid_o && core_cfg_ready_i) begin
                backend_pos[core_cfg_row_o]<=core_cfg_wpos_o;backend_neg[core_cfg_row_o]<=core_cfg_wneg_o;
            end
            if(core_eval_valid_o && core_eval_ready_i) begin
                for(c=0;c<4;c=c+1) begin
                    s=0;
                    for(r=0;r<4;r=r+1) begin
                        if(backend_pos[r][c])s=s+$signed(core_act_x2_o[5*r+:5]);
                        if(backend_neg[r][c])s=s-$signed(core_act_x2_o[5*r+:5]);
                    end
                    core_result_x2_i[12*c+:12]<=12'(s);
                end
                countdown<=2+{29'd0,lfsr[4:2]};projection_count<=projection_count+1;
            end else if(countdown>0) begin
                countdown<=countdown-1;
                if(countdown==1) core_result_valid_i<=1;
            end
            if(core_result_valid_i && core_result_ready_o)core_result_valid_i<=0;
        end
    end
    reg [39:0] activations[0:255];reg [127:0] weights[0:255];
    reg [95:0] expected_outputs[0:255];reg [127:0] expected_probabilities[0:255];
    reg [39:0] expected_context[0:255];reg [47:0] held;
    reg [95:0] trace_q,trace_k,trace_v;
    integer cases,index,j,stage,row,output_index,initial_count;
    string folder;
    task reset;
        begin
            @(negedge clk_i);rst_ni=0;cfg_valid_i=0;req_valid_i=0;rsp_ready_i=0;
            freeze_backend=0;core_fault_i=0;core_result_calibrated_i=1;
            repeat(3)@(negedge clk_i);rst_ni=1;repeat(2)@(negedge clk_i);
        end
    endtask
    task configure(input integer vector_index);
        begin
            for(stage=0;stage<4;stage=stage+1)for(row=0;row<4;row=row+1)begin
                @(negedge clk_i);cfg_stage_i=2'(stage);cfg_row_i=2'(row);
                cfg_wpos_i=weights[vector_index][8*(stage*4+row)+:4];
                cfg_wneg_i=weights[vector_index][8*(stage*4+row)+4+:4];cfg_valid_i=1;
                do @(posedge clk_i);while(!cfg_ready_o);
                @(negedge clk_i);cfg_valid_i=0;
            end
        end
    endtask
    task request(input [39:0] acts);
        begin
            @(negedge clk_i);req_act_x2_i=acts;req_valid_i=1;
            do @(posedge clk_i);while(!req_ready_o);
            @(negedge clk_i);req_valid_i=0;
        end
    endtask
    initial begin
        if(!$value$plusargs("DATA=%s",folder))$fatal(1,"DATA directory required");
        if(!$value$plusargs("CASES=%d",cases))$fatal(1,"CASES required");
        $readmemh({folder,"/activations.memh"},activations,0,cases-1);
        $readmemh({folder,"/weights.memh"},weights,0,cases-1);
        $readmemh({folder,"/outputs.memh"},expected_outputs,0,cases-1);
        $readmemh({folder,"/probabilities.memh"},expected_probabilities,0,cases-1);
        $readmemh({folder,"/context.memh"},expected_context,0,cases-1);
        reset();
        if(req_ready_o)$fatal(1,"incomplete weights accepted");
        cfg_valid_i=1;cfg_wpos_i=1;cfg_wneg_i=1;#1;
        if(cfg_ready_o)$fatal(1,"overlapping ternary masks accepted");
        @(negedge clk_i);cfg_valid_i=0;
        for(index=0;index<cases;index=index+1)begin
            configure(index);initial_count=projection_count;request(activations[index]);
            for(output_index=0;output_index<2;output_index=output_index+1)begin
                wait(rsp_valid_o || fault_o);@(negedge clk_i);
                if(fault_o)$fatal(1,"unexpected MHA fault case %0d",index);
                if(rsp_row_o!=1'(output_index) || rsp_result_x2_o!==expected_outputs[index][48*output_index+:48])
                    $fatal(1,"MHA output case=%0d row=%0d got=%h expected=%h",index,output_index,rsp_result_x2_o,expected_outputs[index][48*output_index+:48]);
                held=rsp_result_x2_o;
                repeat(4)begin @(negedge clk_i);if(!rsp_valid_o || rsp_result_x2_o!==held || req_ready_o)$fatal(1,"output backpressure");end
                rsp_ready_i=1;@(negedge clk_i);rsp_ready_i=0;
            end
            if(projection_count-initial_count!=8)$fatal(1,"projection sequence count");
            for(j=0;j<8;j=j+1)begin
                if(dut.probabilities[j]!==expected_probabilities[index][16*j+:16])$fatal(1,"softmax mismatch %0d %0d",index,j);
                if(j%2==0 && {1'b0,dut.probabilities[j]}+{1'b0,dut.probabilities[j+1]}!=17'd32768)$fatal(1,"probability normalization");
            end
            if({dut.context_acts[1],dut.context_acts[0]}!==expected_context[index])$fatal(1,"MXFP4 context quantization");
            if(index==0)begin
                for(j=0;j<8;j=j+1)begin
                    trace_q[12*j+:12]=dut.q_mem[j];trace_k[12*j+:12]=dut.k_mem[j];trace_v[12*j+:12]=dut.v_mem[j];
                end
                $display("MHA_RTL_CANONICAL q=%024h k=%024h v=%024h context=%010h output=%024h",trace_q,trace_k,trace_v,{dut.context_acts[1],dut.context_acts[0]},{dut.output_rows[1],dut.output_rows[0]});
            end
        end
        $display("MHA_IP_BIT_EXACT_PASS cases=%0d vector_projections=%0d output_values=%0d",cases,cases*8,cases*8);
        $display("MHA_IP_READY_VALID_RANDOM_STALLS_AND_OUTPUT_BACKPRESSURE_PASS");
        reset();configure(0);request(activations[0]);repeat(3)@(negedge clk_i);reset();
        if(busy_o || rsp_valid_o || fault_o || req_ready_o)$fatal(1,"reset/abort");
        $display("MHA_IP_RESET_ABORT_PASS");
        configure(0);core_available_i=0;#1;if(req_ready_o)$fatal(1,"uncalibrated backend admitted");
        core_available_i=1;req_act_x2_i=activations[0];req_act_x2_i[4:0]=5'd5;request(req_act_x2_i);
        wait(fault_o);if(rsp_valid_o)$fatal(1,"invalid activation produced output");
        $display("MHA_IP_INVALID_ACTIVATION_PASS");
        reset();configure(0);request(activations[0]);freeze_backend=1;
        wait(fault_o);if(rsp_valid_o)$fatal(1,"timeout produced output");
        $display("MHA_IP_BACKEND_TIMEOUT_PASS");
        reset();configure(0);request(activations[0]);core_result_calibrated_i=0;
        wait(fault_o);if(rsp_valid_o)$fatal(1,"uncalibrated response produced output");
        $display("MHA_IP_UNCALIBRATED_RESULT_PASS");
        reset();configure(0);request(activations[0]);core_fault_i=1;
        wait(fault_o);if(rsp_valid_o)$fatal(1,"backend fault produced output");
        $display("MHA_IP_BACKEND_FAULT_PASS");
        $finish;
    end
    initial begin #10000000;$fatal(1,"watchdog");end
endmodule
