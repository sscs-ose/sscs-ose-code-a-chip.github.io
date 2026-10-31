
`timescale 1ns/1ps
module tb_vga;
  reg clk=0,rst_n=0;
  wire [9:0] h_count,v_count;
  wire hsync,vsync,video_active,frame_tick;
  integer i,ex_h,ex_v,n_active=0,n_hlow=0,n_vlow=0,n_tick=0;
  vga_timing dut(.clk(clk),.rst_n(rst_n),.h_count(h_count),.v_count(v_count),
   .hsync(hsync),.vsync(vsync),.video_active(video_active),.frame_tick(frame_tick));
  always #5 clk=~clk;
  initial begin
    repeat (3) @(negedge clk);
    rst_n=1;
    for(i=0;i<420000;i=i+1) begin
      ex_h=i%800;ex_v=i/800;
      #1;
      if(h_count !== ex_h || v_count !== ex_v)
        $fatal(1,"Counters: cycle=%0d got (%0d,%0d) expected (%0d,%0d)",i,h_count,v_count,ex_h,ex_v);
      if(hsync !== !((ex_h>=656)&&(ex_h<752))) $fatal(1,"HSYNC at %0d",i);
      if(vsync !== !((ex_v>=490)&&(ex_v<492))) $fatal(1,"VSYNC at %0d",i);
      if(video_active !== ((ex_h<640)&&(ex_v<480))) $fatal(1,"Active at %0d",i);
      if(frame_tick !== ((ex_h==799)&&(ex_v==524))) $fatal(1,"Tick at %0d",i);
      if(video_active) n_active=n_active+1;
      if(!hsync) n_hlow=n_hlow+1;
      if(!vsync) n_vlow=n_vlow+1;
      if(frame_tick) n_tick=n_tick+1;
      @(posedge clk); #1;
    end
    if(n_active!=307200 || n_hlow!=50400 || n_vlow!=1600 || n_tick!=1)
       $fatal(1,"Wrong counts active=%0d Hlow=%0d Vlow=%0d ticks=%0d",n_active,n_hlow,n_vlow,n_tick);
    if(h_count!==0 || v_count!==0) $fatal(1,"Frame wrap failed");
    $display("RTL_PASS: VGA 420000 pixels, active=%0d, Hlow=%0d, Vlow=%0d, ticks=%0d",n_active,n_hlow,n_vlow,n_tick);
    $finish;
  end
endmodule
