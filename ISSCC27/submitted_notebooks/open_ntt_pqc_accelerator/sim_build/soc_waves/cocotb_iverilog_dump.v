module cocotb_iverilog_dump();
initial begin
    string dumpfile_path;    if ($value$plusargs("dumpfile_path=%s", dumpfile_path)) begin
        $dumpfile(dumpfile_path);
    end else begin
        $dumpfile("/home/faisal/vlsi_project/sscs-ose-code-a-chip.github.io/ISSCC27/submitted_notebooks/open_ntt_pqc_accelerator/sim_build/soc_waves/open_ntt_soc.fst");
    end
    $dumpvars(0, open_ntt_soc);
end
endmodule
