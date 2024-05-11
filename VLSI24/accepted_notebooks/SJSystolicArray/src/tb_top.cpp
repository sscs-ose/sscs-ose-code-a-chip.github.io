#include <stdlib.h>
#include <iostream>
#include <fstream>
#include <iomanip>
#include <sstream>
#include <vector>
#include <verilated.h>
#include <verilated_vcd_c.h>
#include "Vtop.h"

VerilatedVcdC*      trace = NULL;       // Waveform Generation
static Vtop*        top;                // DUT
vluint64_t          sim_time = 0;       // Simultation time
const int           TESTCASE_SIZE = 3;  // Test cases per line

// Function to evaluate the DUT and dump waveforms
void eval_and_dump_wave() {

	top->eval();                // Evaluate the DUT
	trace->dump(sim_time++);    // Dump waveforms to VCD file and increment simulation time
}

// Function to execute a single clock cycle
void single_cycle() {

    top->clk = 0;               // Set clock low
    eval_and_dump_wave();       // Evaluate and dump waveforms
    top->clk = 1;               // Set clock high
    eval_and_dump_wave();       // Evaluate and dump waveforms
}

// Function to reset the DUT
void reset(int n) {

    top->nRST = 0;              // Assert reset
    while(n-->0)                // Loop for specified number of cycles
        single_cycle();
    top->nRST = 1;              // Deassert reset
}

// Function to initialize simulation
void sim_init() {

	trace       = new VerilatedVcdC; 
	top         = new Vtop;
	top->trace(trace,0);        // Enable tracing and set start time
	trace->open("dump.vcd");    // Open VCD file for writing waveform

    top->readA = 0;             // Initialize readA signal
    top->readB = 0;             // Initialize readB signal
    reset(2);                   // Reset the DUT for 2 cycles
}

// Function to finalize simulation and clean up
int sim_exit() {

	eval_and_dump_wave();
	top->final();               // Finalize DUT
	trace->close();             // Close VCD file
	delete top;                 // Delete DUT instance

    return EXIT_SUCCESS;
}

// Function to read in test case to a vector
void readNumbers(const std::string& filename, std::vector<int>& numbers) {
    
    // Open test case file
    std::ifstream file(filename);
    if (!file.is_open()) {
        std::cerr << "Failed to open file: " << filename << std::endl;
        return;
    }

    // Read test case file line by line, extract tokens separated by ','
    std::string line;
    while (std::getline(file, line)) {
        std::istringstream iss(line);
        std::string token;
        while (std::getline(iss, token, ',')) {
            numbers.push_back(std::stoi(token));
        }
    }

    // Close test case file
    file.close();
}

// Test main
int main(int argc, char** argv) {
    
    // Initialize test
    Verilated::commandArgs(argc, argv);
    Verilated::traceEverOn(true);
    sim_init();

    // Read in test cases
    std::vector<int> test_cases;
    readNumbers("/content/convInput.txt", test_cases);
    int cycle = ceil(test_cases.size() / TESTCASE_SIZE);

    std::ofstream dumpfile;
    //dumpfile.open("resultdump.txt");

    // Loop through test cases
    for (int i = 0; i < cycle; i++) {
        uint8_t a = test_cases[i * TESTCASE_SIZE]     & 0xFF;
        uint8_t b = test_cases[i * TESTCASE_SIZE + 1] & 0xFF;
        uint8_t w = test_cases[i * TESTCASE_SIZE + 2] & 0xFF;
        
        // Assign signals
        top->readA = a;
        top->readB = b;

        std::cout << "0,0," << +top->write << std::endl;

        single_cycle();
    }

    //dumpfile.close();

    return sim_exit();
}
