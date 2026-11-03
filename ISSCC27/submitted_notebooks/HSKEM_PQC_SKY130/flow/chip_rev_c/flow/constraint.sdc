# M5 ASIC-only physical-screening constraints.  The 40 ns clock is an
# evidence-driven 25 MHz profile; it does not change the 50 MHz FPGA target
# or constitute an ASIC Fmax claim.
create_clock -name core_clk -period 40.000 [get_ports clk_i]
set_clock_uncertainty 0.200 [get_clocks core_clk]

# rst_ni now enters only the ASIC-shell async-assert/sync-deassert reset
# synchronizer.  The raw asynchronous assertion path is cut at the port; the
# synchronizer output and all downstream release timing remain visible to STA.
# SPI inputs are asynchronous and are sampled by explicit core CDC
# synchronizers, so only their input-to-first-stage paths are cut here.
set_false_path -from [get_ports rst_ni]
set_false_path -from [get_ports {spi_cs_ni spi_sck_i spi_mosi_i}]

# No pad/external-service timing model exists yet.  Use a visible 2 ns
# synchronous shell budget for the already-synchronized policy/service inputs
# and core-clocked outputs.  A3 must replace this assumption with a pad/shell
# interface budget before any sign-off claim.
set_input_delay 2.000 -clock core_clk [get_ports {
    sig_valid_i provision_enable_i platform_ready_i platform_error_i[*]
    platform_id_i[*] crypto_backend_enabled_i crypto_backend_ready_i
    crypto_backend_error_i[*]
    session_sample_busy_i session_sample_done_i session_sample_response_i[*]
    entropy_valid_i entropy_data_i[*] entropy_ready_i entropy_unhealthy_i
    entropy_health_code_i[*] entropy_raw_sample_count_i[*] entropy_word_count_i[*]
    root_puf_busy_i root_puf_done_i root_puf_response_i[*]
    root_puf_min_delta_i[*] root_puf_max_delta_i[*] root_puf_health_i[*]
    root_puf_cycles_i[*] root_puf_physical_i
}]
set_output_delay 2.000 -clock core_clk [get_ports {
    spi_miso_o spi_irq_o crypto_backend_zeroize_o enrolled_o verify_ok_o
    device_id_o[*] mlkem_done_o mlkem_pass_o
    session_sample_start_o session_sample_challenge_o[*]
    entropy_enable_o entropy_clear_health_o
    root_puf_scrub_o root_puf_start_o root_puf_bank_id_o[*]
    root_puf_private_mode_o
}]
