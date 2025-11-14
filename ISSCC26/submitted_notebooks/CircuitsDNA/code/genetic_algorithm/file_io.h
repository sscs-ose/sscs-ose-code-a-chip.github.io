#pragma once
#include <string>

#include "gate.h"   
#include "utils.h"  
#include "main.h"

struct ErrorStats;

bool load_verilog(const std::string& path, Circuit& out);

void dump_netlist(const Circuit& c, const std::string& fn = "netlist_16.txt");

void log_progress_txt(int gen, double best_fit,
                      const Circuit& best, const ErrorStats& es,
                      const std::string& logfile);
