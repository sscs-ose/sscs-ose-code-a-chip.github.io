module top(
    input logic clk,
    input logic nRST,
    input logic [7:0] readA,
    input logic [7:0] readB,
    output logic [7:0] write
);

    logic [4:0] PERead;
    logic [4:0] PEStart;
    logic [2:0] filtRead;

    logic [2:0] PENewOuput;

    topLevelControl U1(
        .clk(clk),
        .nRST(nRST),
        .readA(readA),
        .readB(readB),
        .PERead(PERead),
        .PEStart(PEStart),
        .filtRead(filtRead)
    );

    //PE Group 0
    //PE 0,0
    logic [9:0] psum_o00;

    PE U2(
        .clk_i(clk), 
        .rstn_i(nRST),
        .psum_i({{3{readA[7]}}, readA[6:0]}),
        .filter_i(readB), 
        .ifmap_i(readA), 
        .read_new_filter_val(filtRead[0]),
        .read_new_ifmap_val(PERead[0]),
        .start_conv(PEStart[0]),
        .psum_o(psum_o00), 
        .psum_valid_o()
    );

    //PE Group 1
    //PE 1,0

    logic [9:0] psum_o10;

    PE U3(
        .clk_i(clk), 
        .rstn_i(nRST),
        .psum_i(psum_o00),
        .filter_i(readB), 
        .ifmap_i(readA), 
        .read_new_filter_val(filtRead[1]),
        .read_new_ifmap_val(PERead[1]),
        .start_conv(PEStart[1]),
        .psum_o(psum_o10), 
        .psum_valid_o()
    );

    //PE 0,1
    logic [9:0] psum_o01;

    PE U4(
        .clk_i(clk), 
        .rstn_i(nRST),
        .psum_i({{3{readB[7]}}, readB[6:0]}),
        .filter_i(readB), 
        .ifmap_i(readA), 
        .read_new_filter_val(filtRead[0]),
        .read_new_ifmap_val(PERead[1]),
        .start_conv(PEStart[1]),
        .psum_o(psum_o01), 
        .psum_valid_o()
    );

    //PE Group 2
    //PE 2,0
    logic [9:0] psum_o20;

    PE U5(
        .clk_i(clk), 
        .rstn_i(nRST),
        .psum_i(psum_o10),
        .filter_i(readB), 
        .ifmap_i(readA), 
        .read_new_filter_val(filtRead[2]),
        .read_new_ifmap_val(PERead[2]),
        .start_conv(PEStart[2]),
        .psum_o(psum_o20), 
        .psum_valid_o(PENewOuput[2])
    );

    //PE 1,1
    logic [9:0] psum_o11;

    PE U6(
        .clk_i(clk), 
        .rstn_i(nRST),
        .psum_i(psum_o01),
        .filter_i(readB), 
        .ifmap_i(readA), 
        .read_new_filter_val(filtRead[1]),
        .read_new_ifmap_val(PERead[2]),
        .start_conv(PEStart[2]),
        .psum_o(psum_o11), 
        .psum_valid_o()
    );

    //PE 0,2
    logic [9:0] psum_o02;

    PE U7(
        .clk_i(clk), 
        .rstn_i(nRST),
        .psum_i({{3{readB[7]}}, readB[6:0]}),
        .filter_i(readB), 
        .ifmap_i(readA), 
        .read_new_filter_val(filtRead[0]),
        .read_new_ifmap_val(PERead[2]),
        .start_conv(PEStart[2]),
        .psum_o(psum_o02), 
        .psum_valid_o()
    );

    //PE Group 3
    //PE 2,1
    logic [9:0] psum_o21;

    PE U8(
        .clk_i(clk), 
        .rstn_i(nRST),
        .psum_i(psum_o11),
        .filter_i(readB), 
        .ifmap_i(readA), 
        .read_new_filter_val(filtRead[2]),
        .read_new_ifmap_val(PERead[3]),
        .start_conv(PEStart[3]),
        .psum_o(psum_o21), 
        .psum_valid_o(PENewOuput[1])
    );

    //PE 1,2
    logic [9:0] psum_o12;

    PE U9(
        .clk_i(clk), 
        .rstn_i(nRST),
        .psum_i(psum_o02),
        .filter_i(readB), 
        .ifmap_i(readA), 
        .read_new_filter_val(filtRead[1]),
        .read_new_ifmap_val(PERead[3]),
        .start_conv(PEStart[3]),
        .psum_o(psum_o12), 
        .psum_valid_o()
    );

    //PE Group 4
    //PE 2,2
    logic [9:0] psum_o22;

    PE U10(
        .clk_i(clk), 
        .rstn_i(nRST),
        .psum_i(psum_o12),
        .filter_i(readB), 
        .ifmap_i(readB), 
        .read_new_filter_val(filtRead[2]),
        .read_new_ifmap_val(PERead[4]),
        .start_conv(PEStart[4]),
        .psum_o(psum_o22), 
        .psum_valid_o(PENewOuput[0])
    );

    logic[9:0] writeIntermediate;
    logic overflowPos;
    logic overflowNeg;

    always_comb begin //select which PE is routed to output
        casez({PENewOuput})
            3'b1??: begin
                writeIntermediate = psum_o20;
            end
            3'b01?: begin
                writeIntermediate = psum_o21;
            end
            3'b001: begin
                writeIntermediate = psum_o22;
            end
            default: begin
                writeIntermediate = '0;
            end
        endcase

        write = {writeIntermediate[9], writeIntermediate[6:0]}; //cap output to +/-127 by detecting overflows and writing max value to output in case of overflow
        
        overflowPos = !writeIntermediate[9] & (writeIntermediate[8] | writeIntermediate[7]);
        overflowNeg = writeIntermediate[9] & (!writeIntermediate[8] | !writeIntermediate[7]);

        if(overflowPos) begin
            write[6:0] = '1;
        end
        if(overflowNeg) begin
            write[6:0] = '0;
        end
    end

endmodule