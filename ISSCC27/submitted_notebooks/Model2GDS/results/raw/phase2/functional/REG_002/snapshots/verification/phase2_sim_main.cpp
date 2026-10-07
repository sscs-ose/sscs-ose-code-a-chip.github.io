// Phase 2 independent boundary driver. Inputs never include expected C or cycles.
#include "Vphase2_sim_top.h"
#include "verilated.h"

#include <algorithm>
#include <cstdint>
#include <fstream>
#include <functional>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

#ifndef ARRAY_SIZE
#error "Compile with -DARRAY_SIZE=2, 4 or 8 to match the generated wrapper"
#endif

namespace {
constexpr int S = ARRAY_SIZE;
static_assert(S == 2 || S == 4 || S == 8, "Unsupported Phase 2 array size");
constexpr int CELLS = S * S;
constexpr uint64_t FULL_MASK = ~uint64_t{0} >> (64 - CELLS);

std::string quote(const std::string& text) {
    std::ostringstream out;
    out << '"';
    for (unsigned char c : text) {
        if (c == '"') out << "\\\"";
        else if (c == '\\') out << "\\\\";
        else if (c == '\n') out << "\\n";
        else if (c == '\r') out << "\\r";
        else if (c == '\t') out << "\\t";
        else if (c < 32) {
            const char* digits = "0123456789abcdef";
            out << "\\u00" << digits[c >> 4] << digits[c & 15];
        } else out << c;
    }
    return out.str() + '"';
}

int64_t signed32(uint32_t value) {
    return value <= 0x7fffffffU ? static_cast<int64_t>(value)
                              : static_cast<int64_t>(value) - (int64_t{1} << 32);
}

struct Test {
    std::string name;
    bool passed = false;
    uint64_t checks = 0;
    std::string details;
    void require(bool condition, const std::string& message) {
        ++checks;
        if (!condition) throw std::runtime_error(message);
    }
    void equal(int64_t actual, int64_t expected, const std::string& message) {
        require(actual == expected, message + ": expected " + std::to_string(expected)
                                   + ", observed " + std::to_string(actual));
    }
};

class Sim {
public:
    Vphase2_sim_top dut;
    uint64_t edges = 0;
    Sim() {
        dut.clk = 0; dut.rst = 1; dut.clear = 0; dut.tile_mask = 0;
        idle(); dut.eval();
    }
    ~Sim() { dut.final(); }
    void tick() {
        dut.clk = 0; dut.eval();
        dut.clk = 1; dut.eval(); ++edges;
        dut.clk = 0; dut.eval();
        if (Verilated::gotFinish()) throw std::runtime_error("Unexpected RTL finish");
    }
    void idle() {
        dut.a_boundary = 0; dut.b_boundary = 0;
        dut.a_valid = 0; dut.b_valid = 0; dut.a_last = 0; dut.b_last = 0;
    }
    void reset() {
        idle(); dut.rst = 1; dut.clear = 0; dut.tile_mask = 0;
        tick(); dut.rst = 0;
    }
    void begin(uint64_t mask) {
        idle(); dut.tile_mask = mask; dut.clear = 1;
        tick(); dut.clear = 0;
    }
    void a(int lane, int value, bool last = false) {
        dut.a_boundary |= static_cast<uint64_t>(static_cast<uint8_t>(value)) << (8 * lane);
        dut.a_valid |= 1U << lane;
        if (last) dut.a_last |= 1U << lane;
    }
    void b(int lane, int value, bool last = false) {
        dut.b_boundary |= static_cast<uint64_t>(static_cast<uint8_t>(value)) << (8 * lane);
        dut.b_valid |= 1U << lane;
        if (last) dut.b_last |= 1U << lane;
    }
    int64_t accumulator(int row, int col) const {
        return signed32(dut.accumulators[row * S + col]);
    }
    void all_zero(Test& test, const std::string& label) const {
        for (int row = 0; row < S; ++row) for (int col = 0; col < S; ++col)
            test.equal(accumulator(row, col), 0, label + " accumulator");
        test.require(dut.result_valid == 0, label + " result flags");
        test.equal(dut.tile_done, 0, label + " tile_done");
    }
};

std::vector<Test> directed_tests(Sim& sim) {
    std::vector<Test> tests;
    auto run = [&](const std::string& name, const std::function<void(Test&)>& body) {
        Test test; test.name = name;
        try {
            body(test); test.passed = true; test.details = "All directed assertions passed";
        } catch (const std::exception& error) {
            test.details = error.what();
            std::cerr << "PHASE2_DIRECTED_FAIL " << name << ": " << error.what() << '\n';
        }
        tests.push_back(test);
    };

    run("array_synchronous_reset_priority", [&](Test& test) {
        sim.reset(); sim.begin(FULL_MASK);
        sim.a(0, -7, true); sim.b(0, 9, true); sim.tick();
        sim.dut.rst = 1; sim.dut.clear = 1; sim.dut.tile_mask = FULL_MASK;
        sim.dut.eval();
        test.equal(sim.accumulator(0, 0), -63, "reset waits for rising edge");
        sim.tick(); sim.all_zero(test, "reset overrides clear and valid pair");
        test.require(sim.dut.active_mask == 0, "reset clears active mask");
        sim.dut.rst = 0; sim.dut.clear = 0; sim.idle();
        for (int edge = 0; edge < 2 * S; ++edge) sim.tick();
        sim.all_zero(test, "reset flushes every registered forwarding path");
    });

    run("array_registered_wavefront_bubble", [&](Test& test) {
        sim.reset(); sim.begin(FULL_MASK); sim.all_zero(test, "clear");
        // Test fixture: k=0 starts at data edge 0; k=1 starts at edge 2.
        // The deliberately empty base edge 1 inserts one aligned global bubble.
        for (int t = 0; t <= 2 * S; ++t) {
            sim.idle();
            for (int lane = 0; lane < S; ++lane) {
                if (t == lane) { sim.a(lane, lane + 1); sim.b(lane, lane + 2); }
                if (t == lane + 2) { sim.a(lane, -(lane + 2), true); sim.b(lane, lane + 3, true); }
            }
            sim.tick();
            uint64_t expected_flags = 0;
            for (int row = 0; row < S; ++row) for (int col = 0; col < S; ++col) {
                int64_t expected = 0;
                if (t >= row + col) expected += (row + 1) * (col + 2);
                if (t >= row + col + 2) {
                    expected -= (row + 2) * (col + 3);
                    expected_flags |= uint64_t{1} << (row * S + col);
                }
                test.equal(sim.accumulator(row, col), expected,
                           "bubble wavefront t=" + std::to_string(t) + " PE="
                           + std::to_string(row) + "," + std::to_string(col));
            }
            test.require(sim.dut.result_valid == expected_flags, "registered final-token flags");
            test.equal(sim.dut.tile_done, t == 2 * S, "full array finishes on final MAC edge");
        }
        sim.idle(); sim.tick();
        test.require(sim.dut.result_valid == FULL_MASK, "all results remain sticky");
        test.equal(sim.dut.tile_done, 1, "done remains sticky until clear");
    });

    run("array_masked_completion_clear", [&](Test& test) {
        sim.reset(); sim.begin(1);
        sim.dut.tile_mask = FULL_MASK;
        sim.a(0, -128, true); sim.b(0, 127, true); sim.tick();
        test.equal(sim.accumulator(0, 0), -16256, "signed 1x1 result");
        test.equal(sim.dut.tile_done, 1, "inactive PEs cannot delay 1x1 tile");
        test.require(sim.dut.active_mask == 1, "active mask changes only on clear");
        sim.begin(FULL_MASK); sim.all_zero(test, "clear every physical PE");
        test.require(sim.dut.active_mask == FULL_MASK, "clear latches new mask");
        sim.idle();
        for (int edge = 0; edge < 2 * S; ++edge) sim.tick();
        sim.all_zero(test, "clear flushed all old tokens");
        sim.begin(0); sim.a(0, 1, true); sim.b(0, 1, true); sim.tick();
        test.equal(sim.dut.tile_done, 0, "zero mask is gated");
    });

    run("array_last_requires_both", [&](Test& test) {
        sim.reset(); sim.begin(1);
        sim.a(0, 3, true); sim.b(0, 4); sim.tick();
        test.equal(sim.accumulator(0, 0), 12, "A-only last accumulates");
        test.equal(sim.dut.tile_done, 0, "A-only last does not finish");
        sim.idle(); sim.a(0, 2); sim.b(0, -3, true); sim.tick();
        test.equal(sim.accumulator(0, 0), 6, "B-only last accumulates");
        test.equal(sim.dut.tile_done, 0, "B-only last does not finish");
        sim.idle(); sim.a(0, -7, true); sim.dut.b_last = 1; sim.tick();
        test.equal(sim.accumulator(0, 0), 6, "unpaired valid does not accumulate");
        test.equal(sim.dut.tile_done, 0, "unpaired valid does not finish");
        sim.idle(); sim.a(0, 1, true); sim.b(0, 1, true); sim.tick();
        test.equal(sim.accumulator(0, 0), 7, "final product included");
        test.equal(sim.dut.tile_done, 1, "both final tokens finish");
    });
    return tests;
}

void save_tests(const std::string& path, const std::vector<Test>& tests) {
    std::ofstream out(path, std::ios::out | std::ios::trunc);
    if (!out) throw std::runtime_error("Cannot create directed test output");
    out << "{\n  \"schema_version\":1,\n  \"array_size\":" << S << ",\n  \"tests\":[\n";
    for (size_t index = 0; index < tests.size(); ++index) {
        if (index) out << ",\n";
        const auto& test = tests[index];
        out << "    {\"name\":" << quote(test.name) << ",\"passed\":"
            << (test.passed ? "true" : "false") << ",\"checks\":" << test.checks
            << ",\"details\":" << quote(test.details) << '}';
    }
    out << "\n  ]\n}\n";
    if (!out) throw std::runtime_error("Cannot write directed test output");
}

struct Case {
    std::string id;
    int m = 0, n = 0, k = 0;
    std::vector<int> a, b;
};

Case read_case(std::istream& input) {
    Case item; std::string marker;
    if (!(input >> marker >> item.id >> item.m >> item.n >> item.k) || marker != "CASE")
        throw std::runtime_error("Malformed CASE header");
    if (item.m <= 0 || item.n <= 0 || item.k <= 0)
        throw std::runtime_error("CASE " + item.id + " requires positive dimensions");
    auto values = [&](size_t count, std::vector<int>& target) {
        target.resize(count);
        for (auto& value : target)
            if (!(input >> value) || value < -128 || value > 127)
                throw std::runtime_error("CASE " + item.id + " invalid/missing INT8 operand");
    };
    values(static_cast<size_t>(item.m) * item.k, item.a);
    values(static_cast<size_t>(item.k) * item.n, item.b);
    return item;
}

std::string run_case(Sim& sim, const Case& item) {
    sim.reset(); // Outside workload count. Each tile's clear is counted below.
    std::vector<int64_t> result(static_cast<size_t>(item.m) * item.n);
    std::ostringstream tiles; bool first_tile = true;
    uint64_t total_cycles = 0;
    for (int row = 0; row < item.m; row += S) for (int col = 0; col < item.n; col += S) {
        const int rows = std::min(S, item.m - row), cols = std::min(S, item.n - col);
        uint64_t mask = 0;
        for (int i = 0; i < rows; ++i) for (int j = 0; j < cols; ++j)
            mask |= uint64_t{1} << (i * S + j);
        const uint64_t before_clear = sim.edges;
        sim.begin(mask);
        if (sim.dut.tile_done) throw std::runtime_error("tile_done asserted on clear edge");
        bool finished = false;
        // Timeout never supplies a successful completion or predicted cycle value.
        const int64_t timeout = static_cast<int64_t>(item.k) + 4096;
        for (int64_t t = 0; t < timeout; ++t) {
            sim.idle();
            for (int i = 0; i < rows; ++i) {
                const int64_t k = t - i;
                if (k >= 0 && k < item.k)
                    sim.a(i, item.a[static_cast<size_t>(row + i) * item.k + k], k + 1 == item.k);
            }
            for (int j = 0; j < cols; ++j) {
                const int64_t k = t - j;
                if (k >= 0 && k < item.k)
                    sim.b(j, item.b[static_cast<size_t>(k) * item.n + col + j], k + 1 == item.k);
            }
            sim.tick();
            if (sim.dut.tile_done) { finished = true; break; }
        }
        if (!finished) throw std::runtime_error("RTL completion timeout at tile "
                                                + std::to_string(row) + "," + std::to_string(col));
        const uint64_t cycles = sim.edges - before_clear;
        total_cycles += cycles;
        for (int i = 0; i < rows; ++i) for (int j = 0; j < cols; ++j)
            result[static_cast<size_t>(row + i) * item.n + col + j] = sim.accumulator(i, j);
        if (!first_tile) tiles << ',';
        first_tile = false;
        tiles << "{\"row\":" << row << ",\"col\":" << col << ",\"rows\":" << rows
              << ",\"cols\":" << cols << ",\"cycles\":" << cycles << '}';
    }
    std::ostringstream out;
    out << "{\"case_id\":" << quote(item.id) << ",\"M\":" << item.m
        << ",\"N\":" << item.n << ",\"K\":" << item.k << ",\"array_size\":" << S
        << ",\"cycles\":" << total_cycles << ",\"C\":[";
    for (int row = 0; row < item.m; ++row) {
        if (row) out << ',';
        out << '[';
        for (int col = 0; col < item.n; ++col) {
            if (col) out << ',';
            out << result[static_cast<size_t>(row) * item.n + col];
        }
        out << ']';
    }
    return out.str() + "],\"tiles\":[" + tiles.str() + "]}";
}
} // namespace

int main(int argc, char** argv) {
    Verilated::commandArgs(argc, argv);
    if (argc != 4) {
        std::cerr << "Usage: phase2_sim vectors.txt rtl_results.jsonl array_tests.json\n";
        return 2;
    }
    try {
        Sim sim;
        const auto tests = directed_tests(sim);
        save_tests(argv[3], tests);
        const size_t test_passed = std::count_if(tests.begin(), tests.end(), [](const Test& t) { return t.passed; });
        bool passed = test_passed == tests.size();
        std::cout << "PHASE2_DIRECTED_TESTS " << test_passed << '/' << tests.size() << '\n';
        std::ifstream input(argv[1]);
        std::ofstream output(argv[2], std::ios::out | std::ios::trunc);
        if (!input || !output) throw std::runtime_error("Cannot open vector/result file");
        size_t count = 0, completed = 0;
        if (!(input >> count)) throw std::runtime_error("Missing case count");
        for (size_t index = 0; index < count; ++index) {
            const auto item = read_case(input);
            try { output << run_case(sim, item) << '\n'; ++completed; }
            catch (const std::exception& error) {
                passed = false;
                std::cerr << "PHASE2_RTL_CASE_FAIL " << item.id << ": " << error.what() << '\n';
                output << "{\"case_id\":" << quote(item.id) << ",\"error\":" << quote(error.what()) << "}\n";
            }
            output.flush();
            if (!output) throw std::runtime_error("Writing RTL results failed");
        }
        std::string extra;
        if (input >> extra) throw std::runtime_error("Unexpected trailing vector input");
        std::cout << "PHASE2_RTL_CASES_COMPLETED " << completed << '/' << count << '\n';
        std::cout << (passed ? "PHASE2_RTL_DRIVER_PASS" : "PHASE2_RTL_DRIVER_FAIL") << '\n';
        return passed ? 0 : 1;
    } catch (const std::exception& error) {
        std::cerr << "PHASE2_RTL_DRIVER_FAIL: " << error.what() << '\n';
        return 1;
    }
}
