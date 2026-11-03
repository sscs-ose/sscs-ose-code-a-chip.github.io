`timescale 1ns/1ps
// Functional ADC response fixture. Transistor evidence is supplied separately
// by the native CIM/SAR experiment; this test checks the actual RTL hierarchy.
module sky130_fd_sc_hd__buf_1(input wire A,output wire X);assign #0.05 X=A;endmodule
module tb_mha_mixed_top;
    reg clk_i=0,rst_ni=0;always #5 clk_i=~clk_i;
    reg cfg_valid_i=0;wire cfg_ready_o;reg [1:0] cfg_row_i=0;
    reg [3:0] cfg_wpos_i=0,cfg_wneg_i=0;
    reg cal_valid_i=0;wire cal_ready_o;reg [8:0] cal_address_i=0;reg [11:0] cal_threshold_i=0;
    wire calibrated_o;
    reg eval_valid_i=0;wire eval_ready_o;reg signed [19:0] act_x2_i=0;reg raw_mode_i=0;
    wire result_valid_o;reg result_ready_i=0;wire signed [47:0] result_acc_o;
    wire [95:0] raw_codes_o;wire result_calibrated_o,fault_o,BIAS_MON;
    reg mha_mode_i=1,mha_cfg_valid_i=0;wire mha_cfg_ready_o;
    reg [1:0] mha_cfg_stage_i=0,mha_cfg_row_i=0;
    reg [3:0] mha_cfg_wpos_i=0,mha_cfg_wneg_i=0;
    reg mha_req_valid_i=0;wire mha_req_ready_o;reg [39:0] mha_req_act_x2_i=0;
    wire mha_rsp_valid_o;reg mha_rsp_ready_i=0;wire mha_rsp_row_o;
    wire [47:0] mha_rsp_result_x2_o;wire mha_busy_o,mha_fault_o;
    wire VPWR=1'b1,VGND=1'b0;
    automx_cim_mixed_signal_proto dut(.*);
    defparam dut.seq_i.BOOT_CYCLES=2;
    defparam dut.seq_i.SETTLE_CYCLES=2;
    defparam dut.seq_i.ADC_TIMEOUT_CYCLES=24;
    defparam dut.seq_i.VCM_HALF_PERIOD=2;
    reg adc_eoc=0;reg [15:0] adc_word=0;integer adc_timer=0,conversions=0,vectors=0;
    integer r,sum,bin,col,phase,j;integer levels[0:38];
    initial begin
        levels[0]=-24;levels[1]=-20;levels[2]=-18;
        for(j=3;j<=35;j=j+1) levels[j]=j-19;
        levels[36]=18;levels[37]=20;levels[38]=24;
        force dut.adc_i.conversion_finished_osr_out=adc_eoc;
        force dut.adc_i.result_out=adc_word;
    end
    always @(posedge clk_i) begin
        if(!rst_ni || !dut.adc_rst_n)begin adc_timer<=0;adc_eoc<=0;end
        else if(dut.adc_start)begin
            sum=0;col=dut.seq_i.column;phase=dut.seq_i.phase_b;
            for(r=2*phase;r<2*phase+2;r=r+1)begin
                if(dut.wp[4*r+col])sum=sum+$signed(dut.seq_i.acts[5*r+:5]);
                if(dut.wn[4*r+col])sum=sum-$signed(dut.seq_i.acts[5*r+:5]);
            end
            bin=-1;
            for(r=0;r<39;r=r+1)if(levels[r]==sum)bin=r;
            if(bin<0)$fatal(1,"unreachable two-row sum %0d",sum);
            adc_word<=16'((50+80*bin)<<4);adc_timer<=3;conversions<=conversions+1;
        end else if(adc_timer>0)begin
            adc_timer<=adc_timer-1;
            if(adc_timer==1)adc_eoc<=1;
        end
        if(rst_ni && dut.seq_eval_valid && dut.seq_eval_ready)vectors<=vectors+1;
        if(rst_ni && mha_busy_o && (cfg_ready_o || cal_ready_o || eval_ready_o || result_valid_o))$fatal(1,"MHA ownership leaked to host");
        if(rst_ni && (fault_o || mha_fault_o))$fatal(1,"unexpected integrated fault");
    end
    reg [39:0] activation[0:0];reg [127:0] weights[0:0];reg [95:0] expected[0:0];
    string folder;integer i,stage,row;reg [47:0] held;integer start_conversion;
    initial begin
        if(!$value$plusargs("DATA=%s",folder))$fatal(1,"DATA required");
        $readmemh({folder,"/canonical_activations.memh"},activation,0,0);
        $readmemh({folder,"/canonical_weights.memh"},weights,0,0);
        $readmemh({folder,"/canonical_outputs.memh"},expected,0,0);
        repeat(3)@(negedge clk_i);rst_ni=1;repeat(4)@(negedge clk_i);
        if(mha_req_ready_o)$fatal(1,"MHA accepted before calibration/weights");
        for(i=0;i<304;i=i+1)begin
            while(!cal_ready_o)@(negedge clk_i);
            cal_valid_i=1;cal_address_i=9'(i);cal_threshold_i=12'(100+80*(i%38));
            @(negedge clk_i);cal_valid_i=0;
        end
        while(!cal_ready_o)@(negedge clk_i);
        if(!calibrated_o)$fatal(1,"decoder calibration incomplete");
        for(stage=0;stage<4;stage=stage+1)for(row=0;row<4;row=row+1)begin
            mha_cfg_valid_i=1;mha_cfg_stage_i=2'(stage);mha_cfg_row_i=2'(row);
            mha_cfg_wpos_i=weights[0][8*(stage*4+row)+:4];
            mha_cfg_wneg_i=weights[0][8*(stage*4+row)+4+:4];
            do @(posedge clk_i);while(!mha_cfg_ready_o);
            @(negedge clk_i);mha_cfg_valid_i=0;
        end
        mha_req_act_x2_i=activation[0];mha_req_valid_i=1;
        do @(posedge clk_i);while(!mha_req_ready_o);
        @(negedge clk_i);mha_req_valid_i=0;
        // Changing mode mid-frame must preserve ownership until both rows exit.
        mha_mode_i=0;cfg_valid_i=1;cal_valid_i=1;eval_valid_i=1;
        for(row=0;row<2;row=row+1)begin
            wait(mha_rsp_valid_o);@(negedge clk_i);
            if(mha_rsp_row_o!=1'(row) || mha_rsp_result_x2_o!==expected[0][48*row+:48])$fatal(1,"integrated MHA result row %0d",row);
            held=mha_rsp_result_x2_o;
            repeat(5)begin @(negedge clk_i);if(!mha_rsp_valid_o || mha_rsp_result_x2_o!==held)$fatal(1,"MHA response instability");end
            if(row==1)begin cfg_valid_i=0;cal_valid_i=0;eval_valid_i=0;end
            mha_rsp_ready_i=1;@(negedge clk_i);mha_rsp_ready_i=0;
        end
        if(conversions!=64 || vectors!=8)$fatal(1,"integration counts ADC=%0d vectors=%0d",conversions,vectors);
        $display("MHA_CIM_SAR_RTL_TOP_PASS vectors=%0d adc_conversions=%0d output_values=8",vectors,conversions);
        $display("MHA_OWNER_LOCK_CALIBRATION_AND_BACKPRESSURE_PASS");
        // The original direct readout interface still evaluates a matrix.
        for(i=0;i<4;i=i+1)begin
            while(!cfg_ready_o)@(negedge clk_i);
            cfg_row_i=2'(i);cfg_wpos_i=4'b0001<<i;cfg_wneg_i=0;cfg_valid_i=1;
            @(negedge clk_i);cfg_valid_i=0;
        end
        while(!eval_ready_o)@(negedge clk_i);
        act_x2_i=activation[0][19:0];eval_valid_i=1;@(negedge clk_i);eval_valid_i=0;
        wait(result_valid_o);@(negedge clk_i);
        for(i=0;i<4;i=i+1)if($signed(result_acc_o[12*i+:12])!=$signed(activation[0][5*i+:5]))$fatal(1,"direct mode regression");
        if(!result_calibrated_o)$fatal(1,"direct result not calibrated");
        $display("MHA_TOP_DIRECT_CIM_SAR_MODE_PASS");
        $finish;
    end
    initial begin #2000000;$fatal(1,"integrated watchdog");end
endmodule
