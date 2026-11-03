// Generic Verilator harness for the PrecisionFit FIR DUT.
//
//   Usage: ./VFIR <input_vectors.txt> <output_vectors.txt> <out_width>
//
// Reads one signed decimal sample per line from the input file, drives it into
// the DUT one per cycle with in_valid=1, and writes out_data (signed decimal)
// whenever out_valid=1, in order.
//
// out_width is the signed bit-width of the output port (e.g. 14). Verilator
// maps sub-word ports to the smallest unsigned C++ type (e.g. uint16_t for 14
// bits), so we must manually sign-extend before printing to get correct
// negative values.
//
// This file is intentionally module-name agnostic: the build script compiles
// the DUT with `verilator --prefix VFIR`, so the generated class is always
// named VFIR no matter what the top module is called. That replaces the
// symlink/sed hack in the implementation guide with something that works for
// every generated config.
//
// Licensed under the Apache License, Version 2.0. See the repo LICENSE file.
#include <verilated.h>
#include "VFIR.h"

#include <cstdlib>
#include <fstream>
#include <iostream>
#include <vector>

int main(int argc, char** argv) {
    Verilated::commandArgs(argc, argv);
    if (argc < 4) {
        std::cerr << "usage: fir_tb <in_file> <out_file> <out_width>\n";
        return 1;
    }

    int out_width = std::atoi(argv[3]);
    if (out_width <= 0 || out_width > 64) {
        std::cerr << "out_width must be in 1..64, got " << out_width << "\n";
        return 1;
    }

    VFIR* dut = new VFIR;

    std::ifstream fin(argv[1]);
    std::ofstream fout(argv[2]);
    if (!fin || !fout) {
        std::cerr << "could not open input or output vector file\n";
        return 1;
    }

    std::vector<long long> inputs;
    long long v;
    while (fin >> v) inputs.push_back(v);

    // reset
    dut->clk = 0;
    dut->rst_n = 0;
    dut->in_valid = 0;
    dut->in_data = 0;
    for (int i = 0; i < 8; i++) {
        dut->clk = !dut->clk;
        dut->eval();
    }
    dut->rst_n = 1;

    // sign-extension mask: canonical (x ^ sign_bit) - sign_bit
    long long sign_bit = 1LL << (out_width - 1);
    long long data_mask = (1LL << out_width) - 1;

    size_t idx = 0;
    // run enough cycles to flush the pipeline after the last input
    size_t total_cycles = inputs.size() + 32;

    for (size_t cyc = 0; cyc < total_cycles; cyc++) {
        // negedge: apply inputs
        dut->clk = 0;
        if (idx < inputs.size()) {
            dut->in_valid = 1;
            dut->in_data = inputs[idx];
            idx++;
        } else {
            dut->in_valid = 0;
        }
        dut->eval();

        // posedge: sample the registered outputs
        dut->clk = 1;
        dut->eval();
        if (dut->out_valid) {
            long long raw = (long long)dut->out_data & data_mask;
            long long extended = (raw ^ sign_bit) - sign_bit;
            fout << extended << "\n";
        }
    }

    fout.close();
    delete dut;
    return 0;
}
