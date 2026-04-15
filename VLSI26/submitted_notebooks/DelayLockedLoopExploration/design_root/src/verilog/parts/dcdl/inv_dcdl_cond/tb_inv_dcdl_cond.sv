`timescale 1ns/1ps

module tb_inv_dcdl_cond;

logic A;
logic [1:0] Q;
logic Y;

inv_dcdl_cond dut (
    .A(A),
    .Q(Q),
    .Y(Y)
);

initial begin
    $display("Starting inverter DCDL cond test");
    A = 0;
    Q = 2'b00;

    #17 Q = 2'b01;
    #23 Q = 2'b10;
    #19 Q = 2'b11;
    #29 Q = 2'b00;
    #31 Q = 2'b01;
    #13 Q = 2'b10;
    #27 Q = 2'b11;

    #40 $finish;
end

always #5 A = ~A;

always #7 begin
    $display("t=%0t A=%b Q=%b tap0=%b tap1=%b tap2=%b tap3=%b Y=%b",
        $time, A, Q, dut.tap0, dut.tap1, dut.tap2, dut.tap3, Y);
end

endmodule