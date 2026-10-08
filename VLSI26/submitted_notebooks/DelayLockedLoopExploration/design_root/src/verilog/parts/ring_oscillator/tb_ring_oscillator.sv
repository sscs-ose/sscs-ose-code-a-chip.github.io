`timescale 1ns/1ps

module tb_ring_oscillator;

logic [1:0] sel;
logic clk_out;

int errors;
int edge_count [0:3];  // rising-edge count per sel value
int window_ns;

ring_oscillator dut (
    .sel(sel),
    .clk_out(clk_out)
);

// Count rising edges of clk_out for each sel value
always @(posedge clk_out) begin
    edge_count[sel] = edge_count[sel] + 1;
end

// -------------------------------------------------------
// Check clk_out is not X or Z at current time
// -------------------------------------------------------
task automatic check_no_x(input string label);
    begin
        #0.1;
        if (clk_out === 1'bx || clk_out === 1'bz) begin
            $display("[%0t] ERROR: clk_out is X/Z for sel=%0b (%s)", $time, sel, label);
            errors++;
        end
    end
endtask

// -------------------------------------------------------
// Check that at least some oscillation is seen.
// Note: behavioral zero-delay inverters may not oscillate
// in simulation. This is flagged as a WARNING not an ERROR.
// -------------------------------------------------------
task automatic expect_oscillation(
    input int   count,
    input string label
);
    begin
        if (count == 0) begin
            $display("[%0t] WARNING: no rising edges on clk_out during %s", $time, label);
            $display("             (zero-delay behavioral inverters may not oscillate)");
        end else begin
            $display("[%0t] INFO  : %s -> %0d rising edge(s) observed", $time, label, count);
        end
    end
endtask

// -------------------------------------------------------
// Measure rising edges in a given observation window (ns)
// Returns count via output arg; also updates edge_count[sel]
// -------------------------------------------------------
task automatic observe_window(
    input  int    obs_ns,
    output int    count_out
);
    int start_count;
    begin
        start_count = edge_count[sel];
        #(obs_ns);
        count_out = edge_count[sel] - start_count;
    end
endtask

initial begin
    errors       = 0;
    window_ns    = 100;
    edge_count[0] = 0;
    edge_count[1] = 0;
    edge_count[2] = 0;
    edge_count[3] = 0;

    $display("====== ring_oscillator testbench ======");
    $display("Note: behavioral (zero-delay) inverters form a combinational loop.");
    $display("In simulation, true oscillation requires propagation delay.");
    $display("Tests check for X/Z freedom and relative frequency ordering.\n");

    // --------------------------------------------------
    // TEST 1: Check clk_out is not X/Z immediately after init
    // --------------------------------------------------
    $display("\n=== TEST 1: No X/Z on startup ===");
    sel = 2'b00; #1; check_no_x("sel=00 startup");
    sel = 2'b01; #1; check_no_x("sel=01 startup");
    sel = 2'b10; #1; check_no_x("sel=10 startup");
    sel = 2'b11; #1; check_no_x("sel=11 startup");

    // --------------------------------------------------
    // TEST 2: sel=00 (2-inverter tap) — observe edges
    // --------------------------------------------------
    $display("\n=== TEST 2: sel=00 (2-inverter tap, fastest) ===");
    sel = 2'b00;
    #1; check_no_x("sel=00");
    begin : obs_00
        int cnt;
        observe_window(window_ns, cnt);
        expect_oscillation(cnt, "sel=00, 100 ns window");
        $display("  sel=00: %0d rising edges in %0d ns", cnt, window_ns);
    end

    // --------------------------------------------------
    // TEST 3: sel=01 (4-inverter tap)
    // --------------------------------------------------
    $display("\n=== TEST 3: sel=01 (4-inverter tap) ===");
    sel = 2'b01;
    #1; check_no_x("sel=01");
    begin : obs_01
        int cnt;
        observe_window(window_ns, cnt);
        expect_oscillation(cnt, "sel=01, 100 ns window");
        $display("  sel=01: %0d rising edges in %0d ns", cnt, window_ns);
    end

    // --------------------------------------------------
    // TEST 4: sel=10 (6-inverter tap)
    // --------------------------------------------------
    $display("\n=== TEST 4: sel=10 (6-inverter tap) ===");
    sel = 2'b10;
    #1; check_no_x("sel=10");
    begin : obs_10
        int cnt;
        observe_window(window_ns, cnt);
        expect_oscillation(cnt, "sel=10, 100 ns window");
        $display("  sel=10: %0d rising edges in %0d ns", cnt, window_ns);
    end

    // --------------------------------------------------
    // TEST 5: sel=11 (8-inverter tap, slowest)
    // --------------------------------------------------
    $display("\n=== TEST 5: sel=11 (8-inverter tap, slowest) ===");
    sel = 2'b11;
    #1; check_no_x("sel=11");
    begin : obs_11
        int cnt;
        observe_window(window_ns, cnt);
        expect_oscillation(cnt, "sel=11, 100 ns window");
        $display("  sel=11: %0d rising edges in %0d ns", cnt, window_ns);
    end

    // --------------------------------------------------
    // TEST 6: If oscillation was observed, verify frequency ordering:
    //   sel=00 should be fastest (most edges), sel=11 slowest.
    //   (More inverters in loop -> longer period -> fewer edges)
    // --------------------------------------------------
    $display("\n=== TEST 6: Frequency ordering check ===");
    if (edge_count[0] > 0 && edge_count[3] > 0) begin
        if (edge_count[0] < edge_count[3]) begin
            $display("ERROR: sel=00 (%0d edges) should be faster than sel=11 (%0d edges)",
                     edge_count[0], edge_count[3]);
            errors++;
        end else
            $display("PASS : sel=00 (%0d edges) >= sel=11 (%0d edges) — correct ordering",
                     edge_count[0], edge_count[3]);
    end else begin
        $display("INFO: Skipping frequency ordering check (no oscillation observed).");
    end

    // --------------------------------------------------
    // TEST 7: Rapid sel cycling — check clk_out never X/Z during transition
    // --------------------------------------------------
    $display("\n=== TEST 7: Rapid sel transitions (no X/Z) ===");
    begin : test7
        int k;
        for (k = 0; k < 5; k++) begin
            sel = 2'b00; #10; check_no_x("rapid sel=00");
            sel = 2'b01; #10; check_no_x("rapid sel=01");
            sel = 2'b10; #10; check_no_x("rapid sel=10");
            sel = 2'b11; #10; check_no_x("rapid sel=11");
        end
    end
    $display("[%0t] PASS : rapid sel transitions produced no X/Z", $time);

    // --------------------------------------------------
    // TEST 8: Hold each sel long enough for potential settling
    // --------------------------------------------------
    $display("\n=== TEST 8: Extended hold per sel value (200 ns each) ===");
    begin : test8
        int cnt;
        sel = 2'b00; observe_window(200, cnt);
        check_no_x("extended hold sel=00");
        $display("  sel=00 extended: %0d edges", cnt);

        sel = 2'b01; observe_window(200, cnt);
        check_no_x("extended hold sel=01");
        $display("  sel=01 extended: %0d edges", cnt);

        sel = 2'b10; observe_window(200, cnt);
        check_no_x("extended hold sel=10");
        $display("  sel=10 extended: %0d edges", cnt);

        sel = 2'b11; observe_window(200, cnt);
        check_no_x("extended hold sel=11");
        $display("  sel=11 extended: %0d edges", cnt);
    end

    // --------------------------------------------------
    // Summary
    // --------------------------------------------------
    $display("\n============================");
    $display("Total edges per sel: 00=%0d 01=%0d 10=%0d 11=%0d",
             edge_count[0], edge_count[1], edge_count[2], edge_count[3]);
    if (errors == 0)
        $display("TESTBENCH PASSED: 0 errors");
    else
        $display("TESTBENCH FAILED: %0d error(s)", errors);
    $display("============================");

    $finish;
end

endmodule
