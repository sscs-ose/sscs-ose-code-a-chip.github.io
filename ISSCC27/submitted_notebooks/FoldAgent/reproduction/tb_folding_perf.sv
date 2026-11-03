`timescale 1ns/1ps
module tb_lb;
  reg clk=0; always #50 clk=~clk;
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

  integer perf_seed,profile,stall_profile,service_cycle[0:1099],response_count[0:1099];
  integer qjob[0:9][0:3],last_due[0:9],burst_active[0:9];
  reg [9:0] ready_events[0:999999];
  reg [3:0] latency_events[0:175999];
  reg [4095:0] ready_file,latency_file;

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
    if(cycles>=1000000) $fatal(1,"GLOBAL TIMEOUT");
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
          
          response_count[qjob[p][qhead[p]]]=response_count[qjob[p][qhead[p]]]+1;
          if(response_count[qjob[p][qhead[p]]]==8*active_k/4) service_cycle[qjob[p][qhead[p]]]=cycles;
          qhead[p]=(qhead[p]+1)%4;qcount[p]=qcount[p]-1;

        end
        if(phy_req_valid[p]&&phy_req_ready[p]) begin
          if(phys_to_log[p]<0) $fatal(1,"UNSELECTED physical request lane=%d",p);
          if(qcount[p]>=4) $fatal(1,"MORE than four outstanding rows lane=%d",p);
          tile=2*phy_req_addr[p*16+:16]+phy_req_bank[p];
          if(tile!=(issued[p]%(active_k/4)) || tile>=active_k/4) $fatal(1,"ADDRESS/order lane=%d tile=%d expected=%d K=%d",p,tile,issued[p],active_k);
          packed_weight=0;
        for(integer z=0;z<4;z=z+1)
          packed_weight[z*8+:8]=w[4*tile+z][fault_swap ? (phys_to_log[p]+1)%8 : phys_to_log[p]][7:0];
          qdata[p][qtail[p]]=packed_weight;
          qerr[p][qtail[p]]=active_error && tile==0;
          
          qjob[p][qtail[p]]=issued[p]/(active_k/4);
          if(profile==1) begin
            qaddr[p][qtail[p]]=cycles+latency_events[p*17600+issued[p]];
            if(qaddr[p][qtail[p]]<=last_due[p]) qaddr[p][qtail[p]]=last_due[p]+1;
            last_due[p]=qaddr[p][qtail[p]];
          end else qaddr[p][qtail[p]]=cycles;

          qtail[p]=(qtail[p]+1)%4;qcount[p]=qcount[p]+1;issued[p]=issued[p]+1;
        end
      end
    end
  end


  always @(negedge clk) begin
    phy_rsp_valid=0;phy_rsp_error=0;phy_req_ready=0;
    out_ready=rst_n && (stall_profile==0 || cycles%11>=3);
    if(rst_n) for(integer p=0;p<10;p=p+1) begin
      phy_req_ready[p]=profile==1 ? ready_events[cycles][p] : 1;
      if(qcount[p]==0) burst_active[p]=0;
      if(qcount[p]>=4 || (qcount[p]>0 && cycles-qaddr[p][qhead[p]]>=16)) burst_active[p]=1;
      if(qcount[p]>0 && (profile==0 || (profile==1 && qaddr[p][qhead[p]]<=cycles+1) || (profile==2 && burst_active[p]))) begin
        phy_rsp_valid[p]=1;
        phy_rsp_rdata[p*32+:32]=qdata[p][qhead[p]];
        phy_rsp_error[p]=qerr[p][qhead[p]];
      end
    end
  end

  initial begin
    unloaded=1; random_state=11; count=1100;
    tmp=$value$plusargs("perf_k=%d",active_k);
    tmp=$value$plusargs("perf_map=%d",code);
    tmp=$value$plusargs("perf_profile=%d",profile);
    tmp=$value$plusargs("perf_stall=%d",stall_profile);
    if(!$value$plusargs("vectors=%s",filename)) $fatal(1,"performance vectors missing");
    if(!$value$plusargs("ready_events=%s",ready_file)) $fatal(1,"ready events missing");
    if(!$value$plusargs("latency_events=%s",latency_file)) $fatal(1,"latency events missing");
    $readmemh(ready_file,ready_events); $readmemh(latency_file,latency_events);
    fd=$fopen(filename,"r"); if(fd==0) $fatal(1,"performance vectors unreadable");
    for(j=0;j<64;j=j+1) scan=$fscanf(fd,"%d",x[j]);
    for(j=0;j<64;j=j+1) for(lane=0;lane<8;lane=lane+1) begin scan=$fscanf(fd,"%d",tmp);w[j][lane]=tmp;end
    for(j=0;j<8;j=j+1) begin scan=$fscanf(fd,"%d",tmp);for(n=0;n<count;n=n+1) expected[n][j]=tmp;end
    for(n=0;n<count;n=n+1) begin
      expected_bank[n]=n%2;expected_error[n]=0;response_count[n]=0;service_cycle[n]=-1;
    end
    for(j=0;j<10;j=j+1) begin last_due[j]=0;burst_active[j]=0;end
    reset_dut();configure(code);
    for(slot=0;slot<2;slot=slot+1) for(word=0;word<8;word=word+1) begin
      @(negedge clk);in_valid=1;in_bank=slot;in_word=word;
      for(j=0;j<8;j=j+1) in_data[j*8+:8]=x[word*8+j][7:0];
      @(posedge clk);if(!in_ready)$fatal(1,"performance input preload rejected");
    end
    @(negedge clk);in_valid=0;cmd_valid=1;cmd_k=active_k;cmd_in_bank=0;cmd_out_bank=0;
    for(n=0;n<count;n=n+1) begin
      @(posedge clk);while(!cmd_ready)@(posedge clk);
      accepted_cycle[n]=cycles;tail=tail+1;
      @(negedge clk);cmd_in_bank=(n+1)%2;cmd_out_bank=(n+1)%2;
    end
    cmd_valid=0;
    while(head<count) @(negedge clk);
    for(j=0;j<10;j=j+1) if(phys_to_log[j]>=0 && issued[j]!=count*active_k/4) $fatal(1,"performance request count");
    for(n=0;n<count;n=n+1) if(response_count[n]!=8*active_k/4) $fatal(1,"performance service byte count");
    tmp=0;for(n=100;n<count;n=n+1) if(finish_cycle[n]-accepted_cycle[n]>tmp) tmp=finish_cycle[n]-accepted_cycle[n];
    $display("FOLD_PERF_PASS jobs=1100 intervals=1000 completion_cycles=%0d supply_cycles=%0d useful_bytes=%0d max_latency=%0d",
      finish_cycle[1099]-finish_cycle[99],service_cycle[1099]-service_cycle[99],1000*8*active_k,tmp);
    $finish;
  end
endmodule
