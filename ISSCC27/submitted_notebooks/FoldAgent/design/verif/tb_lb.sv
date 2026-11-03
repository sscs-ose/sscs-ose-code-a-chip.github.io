`timescale 1ns/1ps
module tb_lb;
  reg clk=0; always #5 clk=~clk;
  reg rst_n=0, cfg_commit=0;
  reg [15:0] cfg_map=0; reg [9:0] cfg_bad=0;
  wire cfg_locked,cfg_error;
  reg in_valid=0,in_bank=0; reg [2:0] in_word=0; reg [63:0] in_data=0;
  wire in_ready;
  reg cmd_valid=0; reg [6:0] cmd_k=4; reg cmd_in_bank=0,cmd_out_bank=0;
  wire cmd_ready;
  wire out_valid; reg out_ready=0;
  wire [63:0] out_data; wire out_last,out_bank,out_error;
  wire [9:0] phy_req_valid,phy_req_bank;
  reg [9:0] phy_req_ready=0,phy_rsp_valid=0,phy_rsp_error=0;
  wire [159:0] phy_req_addr; reg [319:0] phy_rsp_rdata=0;
  lb_feedback dut(.*);

  integer qdata[0:9][0:3],qerr[0:9][0:3],qaddr[0:9][0:3];
  integer qhead[0:9],qtail[0:9],qcount[0:9],issued[0:9];
  integer prev_wait[0:9],prev_addr[0:9],prev_bank[0:9];
  integer phys_to_log[0:9];
  integer x[0:63],w[0:63][0:7];
  integer expected[0:9999][0:7],expected_bank[0:9999],expected_error[0:9999];
  integer tail=0,head=0,word_index=0,cycles=0,active_k=4,active_error=0;
  integer lane,word,j,slot,tile,tmp,seed=11,random_state,unloaded=0;
  integer count=1000,fd,scan,n,code,err,deadline,config_only=0;
  integer overlap=0,reset_probe=0,fault_data=0,fault_swap=0,fault_drop=0,all_returned;
  integer accepted_cycle[0:9999],finish_cycle[0:9999];
  reg force_stall=0,bank;
  reg [31:0] packed_weight;
  reg [63:0] held_data; reg held_last,held_bank,held_error,was_stalled=0;
  reg [4095:0] filename;

  function integer randbit;
    input integer mask;
    begin
      random_state = (random_state ^ (random_state << 13));
      random_state = (random_state ^ (random_state >> 17));
      random_state = (random_state ^ (random_state << 5));
      randbit=random_state & mask;
    end
  endfunction

  task reset_dut;
    begin
      @(negedge clk); rst_n=0; cfg_commit=0; in_valid=0; cmd_valid=0;
      repeat(2) @(negedge clk);
      rst_n=1; @(negedge clk);
      if(cfg_locked || out_valid) $fatal(1,"RESET status/output not cleared");
    end
  endtask

  task configure;
    input integer map;
    begin configure_bits(map,0); end
  endtask

  task configure_bits;
    input integer map;
    input integer bad;
    integer a,target,valid,used;
    begin
      cfg_map=map; cfg_bad=bad; used=0; valid=1;
      for(a=0;a<10;a=a+1) phys_to_log[a]=-1;
      for(a=0;a<8;a=a+1) begin
        target=(map>>(2*a))&3;
        if(target==3) valid=0;
        target=(target==0)?a:7+target;
        if(target<10) begin
          if((used>>target)&1) valid=0;
          if((bad>>target)&1) valid=0;
          used=used|(1<<target); phys_to_log[target]=a;
        end
      end
      cfg_commit=1; @(negedge clk); cfg_commit=0;
      if(cfg_locked!==valid[0] || cfg_error===valid[0])
        $fatal(1,"CONFIG code=%h valid=%d locked=%b error=%b",map,valid,cfg_locked,cfg_error);
    end
  endtask

  // Independent ordered four-entry DRAM response queues; no DUT internals read.
  always @(posedge clk) begin
    cycles=cycles+1;
    if(cycles>4000000) $fatal(1,"GLOBAL TIMEOUT");
    if(!rst_n) begin
      for(integer p=0;p<10;p=p+1) begin
        qhead[p]=0;qtail[p]=0;qcount[p]=0;issued[p]=0;prev_wait[p]=0;
      end
      was_stalled=0;
    end else begin
      if(was_stalled && (!out_valid || out_data!==held_data || out_last!==held_last || out_bank!==held_bank || out_error!==held_error))
        $fatal(1,"OUTPUT changed during backpressure");
      was_stalled=out_valid&&!out_ready;
      held_data=out_data;held_last=out_last;held_bank=out_bank;held_error=out_error;
      if(out_valid&&out_ready) begin
        if(head>=tail) $fatal(1,"UNEXPECTED output");
        if(out_bank!==expected_bank[head][0] || out_error!==expected_error[head][0] || out_last!==(word_index==3))
          $fatal(1,"OUTPUT metadata mismatch job=%d word=%d",head,word_index);
        if($signed(out_data[31:0])!==expected[head][2*word_index] || $signed(out_data[63:32])!==expected[head][2*word_index+1])
          $fatal(1,"NUMERIC mismatch job=%d word=%d got=%h expected=%d,%d",head,word_index,out_data,expected[head][2*word_index],expected[head][2*word_index+1]);
        if(word_index==3) begin finish_cycle[head]=cycles;head=head+1;word_index=0;end
        else word_index=word_index+1;
      end
      for(integer p=0;p<10;p=p+1) begin
        if(prev_wait[p] && (!phy_req_valid[p] || phy_req_addr[p*16+:16]!==prev_addr[p][15:0] || phy_req_bank[p]!==prev_bank[p][0]))
          $fatal(1,"REQUEST unstable lane=%d",p);
        prev_wait[p]=phy_req_valid[p]&&!phy_req_ready[p];
        prev_addr[p]=phy_req_addr[p*16+:16];prev_bank[p]=phy_req_bank[p];
        if(phy_rsp_valid[p]) begin
          if(qcount[p]<1) $fatal(1,"MODEL queue underflow");
          qhead[p]=(qhead[p]+1)%4;qcount[p]=qcount[p]-1;
        end
        if(phy_req_valid[p]&&phy_req_ready[p]) begin
          if(phys_to_log[p]<0) $fatal(1,"UNSELECTED physical request lane=%d",p);
          if(qcount[p]>=4) $fatal(1,"MORE than four outstanding rows lane=%d",p);
          tile=2*phy_req_addr[p*16+:16]+phy_req_bank[p];
          if(tile!=issued[p] || tile>=active_k/4) $fatal(1,"ADDRESS/order lane=%d tile=%d expected=%d K=%d",p,tile,issued[p],active_k);
          packed_weight=0;
        for(integer z=0;z<4;z=z+1)
          packed_weight[z*8+:8]=w[4*tile+z][fault_swap ? (phys_to_log[p]+1)%8 : phys_to_log[p]][7:0];
          qdata[p][qtail[p]]=packed_weight;
          qerr[p][qtail[p]]=active_error && tile==0;
          qaddr[p][qtail[p]]=cycles;
          qtail[p]=(qtail[p]+1)%4;qcount[p]=qcount[p]+1;issued[p]=issued[p]+1;
        end
      end
    end
  end

  always @(negedge clk) begin
    phy_rsp_valid=0;phy_rsp_error=0;phy_req_ready=0;
    out_ready=rst_n&&!force_stall&&(unloaded || randbit(3)!=0);
    if(rst_n) for(integer p=0;p<10;p=p+1) begin
      phy_req_ready[p]=unloaded || randbit(3)!=0;
      if(qcount[p]>0 && (unloaded || randbit(3)!=0) && qaddr[p][qhead[p]]<cycles) begin
        phy_rsp_valid[p]=1;
        phy_rsp_rdata[p*32+:32]=qdata[p][qhead[p]];
        phy_rsp_error[p]=qerr[p][qhead[p]];
        if(fault_data && phys_to_log[p]==0) phy_rsp_rdata[p*32+:32]=qdata[p][qhead[p]]^32'b1;
        if(fault_drop && phys_to_log[p]==0) phy_rsp_valid[p]=0;
      end
    end
  end

  initial begin
    tmp=$value$plusargs("seed=%d",seed);random_state=seed|1;
    tmp=$value$plusargs("count=%d",count);
    tmp=$value$plusargs("config_only=%d",config_only);
    tmp=$value$plusargs("unloaded=%d",unloaded);
    tmp=$value$plusargs("overlap=%d",overlap);
    tmp=$value$plusargs("reset_probe=%d",reset_probe);
    tmp=$value$plusargs("fault_data=%d",fault_data);
    tmp=$value$plusargs("fault_swap=%d",fault_swap);
    tmp=$value$plusargs("fault_drop=%d",fault_drop);
    if(config_only) begin
      slot=0;
      for(code=0;code<65536;code=code+1) begin
        reset_dut();configure(code);
        if(cfg_locked) begin
          slot=slot+1;cfg_map=16'hffff;cfg_bad=10'h3ff;cfg_commit=1;
          @(negedge clk);cfg_commit=0;
          if(!cfg_locked || cfg_error) $fatal(1,"LOCKED configuration changed");
          for(err=0;err<10;err=err+1) begin reset_dut();configure_bits(code,1<<err);end
        end
      end
      reset_dut();configure(3);configure(0);
      $display("LB_CONFIG_BAD_PASS cases=730");
      $display("LB_LOCK_PASS cases=%0d",slot);
      $display("LB_CONFIG_PASS encodings=65536");$finish;
    end
    if(!$value$plusargs("vectors=%s",filename)) $fatal(1,"vectors missing");
    fd=$fopen(filename,"r");if(fd==0) $fatal(1,"cannot open vectors");
    reset_dut();
    for(n=0;n<count;n=n+1) begin
      scan=$fscanf(fd,"%d %d %d",active_k,code,active_error);
      if(scan!=3) $fatal(1,"short vector header");
      for(j=0;j<64;j=j+1) scan=$fscanf(fd,"%d",x[j]);
      for(j=0;j<64;j=j+1) for(lane=0;lane<8;lane=lane+1) begin
        scan=$fscanf(fd,"%d",tmp);w[j][lane]=tmp;
      end
      for(j=0;j<8;j=j+1) begin scan=$fscanf(fd,"%d",tmp);expected[n][j]=tmp;end
      if(n==0 || !cfg_locked) configure(code);
      else if(cfg_map!==code[15:0]) $fatal(1,"workload changed locked mapping");
      bank=n%2;
      for(word=0;word<8;word=word+1) begin
        @(negedge clk);in_valid=1;in_bank=bank;in_word=word;
        for(j=0;j<8;j=j+1) in_data[j*8+:8]=x[word*8+j][7:0];
        deadline=cycles+500;
        @(posedge clk);while(!in_ready) begin if(cycles>deadline)$fatal(1,"input timeout");@(posedge clk);end
      end
      @(negedge clk);in_valid=0;cmd_valid=0;cmd_k=5;
      #1;if(cmd_ready) $fatal(1,"ILLEGAL K command accepted");
      cmd_k=active_k;
      if(overlap && n==1) begin
        cmd_out_bank=0;#1;if(cmd_ready) $fatal(1,"BUSY output bank command accepted");
      end
      cmd_valid=1;cmd_in_bank=bank;cmd_out_bank=bank;
      expected_bank[n]=bank;expected_error[n]=active_error;
      for(j=0;j<10;j=j+1) issued[j]=0;
      deadline=cycles+1000;
      @(posedge clk);while(!cmd_ready) begin if(cycles>deadline)$fatal(1,"command timeout");@(posedge clk);end
      accepted_cycle[n]=cycles;tail=tail+1;
      @(negedge clk);cmd_valid=0;
      // Both input banks are real: active bank rejects writes, other bank accepts.
      in_valid=1;in_bank=bank;in_word=7;in_data=64'h1234567812345678;
      #1;if(in_ready!==1'b0) $fatal(1,"ACTIVE input bank writable");
      in_bank=!bank;
      #1;if(in_ready!==1'b1) $fatal(1,"INACTIVE input bank blocked");
      @(negedge clk);in_valid=0;
      deadline=cycles+2000;
      if(reset_probe && n==0) begin
        repeat(2) @(negedge clk);
        head=tail;word_index=0;
        reset_dut();
      end else begin
        if(overlap) begin
          all_returned=0;
          while(!all_returned) begin
            if(cycles>deadline)$fatal(1,"overlap response timeout");
            @(negedge clk);all_returned=1;
            for(j=0;j<10;j=j+1) if(phys_to_log[j]>=0 && (issued[j]!=active_k/4 || qcount[j]!=0 || phy_rsp_valid[j])) all_returned=0;
          end
          if(n==0) begin force_stall=1;repeat(8) @(negedge clk);end
          else begin repeat(8) @(negedge clk);force_stall=0;end
        end
        if(!overlap || n!=0) begin
          while(head<tail) begin if(cycles>deadline)$fatal(1,"result timeout job=%d head=%d",n,head);@(negedge clk);end
        end
        for(j=0;j<10;j=j+1) if(phys_to_log[j]>=0 && issued[j]!=active_k/4) $fatal(1,"missing requests");
      end
    end
    $display("LB_TRAFFIC_PASS tasks=%0d seed=%0d cycles=%0d",head,seed,cycles);
    if(overlap) $display("LB_OVERLAP_PASS two_output_banks=1");
    if(reset_probe) $display("LB_RESET_PASS cancelled=1 completed=1");
    for(n=0;n<count;n=n+1) $display("LB_LATENCY job=%0d cycles=%0d",n,finish_cycle[n]-accepted_cycle[n]);
    $finish;
  end
endmodule
