// =============================================================================
// Project: ProEm - Open Source Protocol Emulator
// File: sim/verilator/emu_sim.h
// Type: Test bench shim: runs the CXXRTL tests on a Verilator model (for coverage)
// Device under test: protocol_emulator (src/top/protocol_emulator.sv)
// Author: Paul Vincent Bezzina
// Language: C++14
// Description:
// =============================================================================

#include "Vprotocol_emulator.h"
#include "verilated.h"
#include "verilated_cov.h"
#include <cstdlib>
#include <string>

namespace cxxrtl_design {

template<typename S> struct port {
	S *s;
	template<typename T> void set(T v) { *s = (S)v; }
	template<typename T> T get() const { return (T)*s; }
};

struct p_protocol__emulator {
	VerilatedContext *ctx;
	Vprotocol_emulator *m;
	port<CData> p_clk, p_rst__n, p_rx__serial, p_pin__in, p_tx__serial;
	port<CData> p_data__out__a, p_data__oe__a, p_pair__out__a, p_pair__oe__a, p_clock__out__a, p_clock__oe__a, p_select__out__a, p_armed__a, p_host__full__a;
	port<CData> p_data__out__b, p_data__oe__b, p_pair__out__b, p_pair__oe__b, p_clock__out__b, p_clock__oe__b, p_select__out__b, p_armed__b, p_host__full__b;
	port<CData> p_baud__locked;
	p_protocol__emulator() {
		ctx = new VerilatedContext;
		m = new Vprotocol_emulator(ctx);
		p_clk = {&m->clk}; p_rst__n = {&m->rst_n}; p_rx__serial = {&m->rx_serial}; p_pin__in = {&m->pin_in}; p_tx__serial = {&m->tx_serial};
		p_data__out__a = {&m->data_out_a}; p_data__oe__a = {&m->data_oe_a}; p_pair__out__a = {&m->pair_out_a}; p_pair__oe__a = {&m->pair_oe_a};
		p_clock__out__a = {&m->clock_out_a}; p_clock__oe__a = {&m->clock_oe_a}; p_select__out__a = {&m->select_out_a}; p_armed__a = {&m->armed_a}; p_host__full__a = {&m->host_full_a};
		p_data__out__b = {&m->data_out_b}; p_data__oe__b = {&m->data_oe_b}; p_pair__out__b = {&m->pair_out_b}; p_pair__oe__b = {&m->pair_oe_b};
		p_clock__out__b = {&m->clock_out_b}; p_clock__oe__b = {&m->clock_oe_b}; p_select__out__b = {&m->select_out_b}; p_armed__b = {&m->armed_b}; p_host__full__b = {&m->host_full_b};
		p_baud__locked = {&m->baud_locked};
		m->rst_n = 1;
		m->clk = 0;
		m->eval();
	}
	~p_protocol__emulator() {
		m->final();
		const char *f = std::getenv("PROEM_COV");
		ctx->coveragep()->write(f ? f : "coverage.dat");
	}
	void step() { m->eval(); }
};

}
