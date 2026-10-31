`timescale 1ns/1ps
module npu_smoke_tb;
 logic clk=0,rst_n=0,req_valid=0,rsp_ready=1,kill=0;
 logic req_ready,rsp_valid;
 logic [31:0] req_a=0,req_b=0,rsp_data;
 logic [31:0] av[0:63],bv[0:63],ev[0:63];
 integer k;
 nebula_npu_dot4 dut(.*);
 always #5 clk=~clk;
 task automatic tick; @(posedge clk); #1; endtask
 task automatic offer(input logic[31:0] a,b);
   @(negedge clk);req_a=a;req_b=b;req_valid=1;
   for(integer n=0;n<20 && !req_ready;n++) tick();
   if(!req_ready) $fatal(1,"NPU request timeout");
   tick();req_valid=0;
   if(rsp_valid) $fatal(1,"NPU response too early at acceptance");
 endtask
 task automatic check_case(input integer i);
   @(negedge clk);rsp_ready=(i%7!=0);
   offer(av[i],bv[i]);
   tick();if(rsp_valid) $fatal(1,"NPU response early at n+1 case=%0d",i);
   tick();
   if(!rsp_valid || rsp_data!==ev[i]) $fatal(1,"NPU result/latency case=%0d valid=%b got=%h expected=%h",i,rsp_valid,rsp_data,ev[i]);
   if(!rsp_ready) begin
     repeat(3) begin tick();if(!rsp_valid || rsp_data!==ev[i]) $fatal(1,"NPU unstable backpressured response");end
     @(negedge clk);rsp_ready=1;
   end
   tick();if(rsp_valid) $fatal(1,"NPU duplicate response");
 endtask
 initial begin
    av[0]=32'h00000000; bv[0]=32'h00000000; ev[0]=32'h00000000;
    av[1]=32'h80808080; bv[1]=32'h80808080; ev[1]=32'h00010000;
    av[2]=32'h80808080; bv[2]=32'h7f7f7f7f; ev[2]=32'hffff0200;
    av[3]=32'h7f7f7f7f; bv[3]=32'h7f7f7f7f; ev[3]=32'h0000fc04;
    av[4]=32'h04030201; bv[4]=32'h01020304; ev[4]=32'h00000014;
    av[5]=32'h7f0100ff; bv[5]=32'hff00807f; ev[5]=32'hffffff02;
    av[6]=32'h143b1b54; bv[6]=32'h8db80ed9; ev[6]=32'hffffdb1a;
    av[7]=32'h015644ff; bv[7]=32'h9fc64d22; ev[7]=32'h00000075;
    av[8]=32'hebcde4c7; bv[8]=32'h1ea3bf29; ev[8]=32'h00000e0c;
    av[9]=32'hc872a951; bv[9]=32'h5d892c51; ev[9]=32'hffffc157;
    av[10]=32'h99359a3e; bv[10]=32'h4f823f74; ev[10]=32'hffffc91f;
    av[11]=32'hffedbbfa; bv[11]=32'ha0089d38; ev[11]=32'h00001927;
    av[12]=32'h00c2e20d; bv[12]=32'hd723321d; ev[12]=32'hfffff323;
    av[13]=32'h2b0bb02a; bv[13]=32'h89329984; ev[13]=32'hfffffa01;
    av[14]=32'h9b720b6f; bv[14]=32'ha6041ee5; ev[14]=32'h00001adf;
    av[15]=32'h4ec68a78; bv[15]=32'he4dd4878; ev[15]=32'h00001676;
    av[16]=32'hecb8cd00; bv[16]=32'h21211c99; ev[16]=32'hffffee90;
    av[17]=32'haf56d299; bv[17]=32'h754e001f; ev[17]=32'hffffe8b6;
    av[18]=32'hf3fbaba6; bv[18]=32'h9917d307; ev[18]=32'h00001143;
    av[19]=32'hf1794979; bv[19]=32'h6ba76350; ev[19]=32'h000011b5;
    av[20]=32'h2277f5ef; bv[20]=32'h588e3ae0; ev[20]=32'hffffd654;
    av[21]=32'hf6d6289b; bv[21]=32'hecd83c20; ev[21]=32'h00000418;
    av[22]=32'h65365e1b; bv[22]=32'he285b6af; ev[22]=32'hffffb681;
    av[23]=32'h646d66db; bv[23]=32'h866773c6; ev[23]=32'h00003267;
    av[24]=32'h84de0616; bv[24]=32'hec282c6f; ev[24]=32'h00000ef2;
    av[25]=32'h87b2089a; bv[25]=32'h1a71b98e; ev[25]=32'hfffffc7c;
    av[26]=32'h698db2e8; bv[26]=32'hbe4c8ff1; ev[26]=32'hffffe6a0;
    av[27]=32'he09e9d5b; bv[27]=32'h31360906; ev[27]=32'hffffe3db;
    av[28]=32'h2d834f55; bv[28]=32'h261191a9; ev[28]=32'hffffbf3d;
    av[29]=32'hc12bbc24; bv[29]=32'h62117dfc; ev[29]=32'hffffc8f9;
    av[30]=32'ha5ff02bf; bv[30]=32'h77e61e57; ev[30]=32'hffffbff2;
    av[31]=32'hcdedc13b; bv[31]=32'h605faa16; ev[31]=32'h0000000f;
    av[32]=32'hd4c9ce46; bv[32]=32'h50107c22; ev[32]=32'hffffdfe4;
    av[33]=32'hcdd6f8a1; bv[33]=32'h62245af8; ev[33]=32'hffffe6ba;
    av[34]=32'h7dfc13c1; bv[34]=32'h833ee100; ev[34]=32'hffffbfb2;
    av[35]=32'ha77c2bbe; bv[35]=32'hfc41ac5c; ev[35]=32'hfffffb0c;
    av[36]=32'ha517a4d7; bv[36]=32'h246c2d13; ev[36]=32'hffffe9b1;
    av[37]=32'h1d08cccc; bv[37]=32'h5fc92644; ev[37]=32'hfffff383;
    av[38]=32'heef903b5; bv[38]=32'h405f3ded; ev[38]=32'hffffff2f;
    av[39]=32'h4f1da80a; bv[39]=32'h928621e8; ev[39]=32'hffffc3f4;
    av[40]=32'h4e7b349e; bv[40]=32'h661a0458; ev[40]=32'h00000ab2;
    av[41]=32'he0ed54d3; bv[41]=32'hf5e439ea; ev[41]=32'h00001a06;
    av[42]=32'he569a442; bv[42]=32'h6277c035; ev[42]=32'h00004b23;
    av[43]=32'h5ff8c3ac; bv[43]=32'h414df449; ev[43]=32'h0000009f;
    av[44]=32'h27fa2b78; bv[44]=32'h7cd8ed45; ev[44]=32'h000030fb;
    av[45]=32'h50b27285; bv[45]=32'h7edeb276; ev[45]=32'hffffd64e;
    av[46]=32'hc271078f; bv[46]=32'hcb03d0e5; ev[46]=32'h000018c4;
    av[47]=32'h6115bf92; bv[47]=32'h0517ac9b; ev[47]=32'h00004482;
    av[48]=32'h9106411f; bv[48]=32'h9ca4118f; ev[48]=32'h00001fd6;
    av[49]=32'h7633160c; bv[49]=32'h3e96b7ec; ev[49]=32'h00000040;
    av[50]=32'h2864753e; bv[50]=32'h84f03b7c; ev[50]=32'h00001f5f;
    av[51]=32'h43cc32ba; bv[51]=32'h4894a8ba; ev[51]=32'h00002abc;
    av[52]=32'he4c96cb8; bv[52]=32'h89099862; ev[52]=32'hffffc3a5;
    av[53]=32'h73c7b1b6; bv[53]=32'h1b191ef0; ev[53]=32'h000001ee;
    av[54]=32'had5f8829; bv[54]=32'hb56c8144; ev[54]=32'h000086d1;
    av[55]=32'h9d6b2527; bv[55]=32'h186faf79; ev[55]=32'h00002bd7;
    av[56]=32'h24a4cebe; bv[56]=32'h17e6ce93; ev[56]=32'h00003272;
    av[57]=32'h43b7ab56; bv[57]=32'h53517a9c; ev[57]=32'hffffb486;
    av[58]=32'hc24ffa06; bv[58]=32'h22f629f1; ev[58]=32'hfffff35e;
    av[59]=32'hb2ec2171; bv[59]=32'h61ea6fe8; ev[59]=32'hffffe7e1;
    av[60]=32'h9a5f3b5f; bv[60]=32'h82ffbee5; ev[60]=32'h0000189a;
    av[61]=32'h39059a04; bv[61]=32'h8797455b; ev[61]=32'hffffc8f0;
    av[62]=32'hd824258c; bv[62]=32'h08fa2237; ev[62]=32'hffffe9e6;
    av[63]=32'hc1b86462; bv[63]=32'hce68c68c; ev[63]=32'hffffabfe;
   repeat(3)tick();@(negedge clk);rst_n=1;tick();
   for(k=0;k<64;k++)check_case(k);
   offer(av[4],bv[4]);
   @(negedge clk);kill=1;
   tick();if(rsp_valid)$fatal(1,"kill leaked response");
   @(negedge clk);kill=0;
   repeat(5)begin tick();if(rsp_valid)$fatal(1,"late killed response");end
   check_case(4);
   offer(av[5],bv[5]);
   @(negedge clk);rst_n=0;
   repeat(2)begin tick();if(rsp_valid)$fatal(1,"reset leaked response");end
   @(negedge clk);rst_n=1;tick();check_case(5);
   $display("NPU_SMOKE_PASS vectors=64 backpressure=covered kill=covered reset=covered");$finish;
 end
 initial begin #100000;$fatal(1,"NPU smoke timeout");end
endmodule
