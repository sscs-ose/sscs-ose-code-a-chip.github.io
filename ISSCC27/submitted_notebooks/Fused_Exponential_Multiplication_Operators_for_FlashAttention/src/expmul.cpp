// ============================================================================
//  expmul.cpp -- Phase 1 test driver for the ExpMul operator
//
//  1. Error of ExpMul(x,V) against the exact float/double value e^x * V
//  2. Structure of the logarithmic quantisation (L vs -x*log2(e), weight ratio)
//  3. Edge cases: x = 0, clipping, exponent underflow, inf/NaN, denormals
//  4. Invariants that the RTL relies on (sign, |Out| <= |V|, monotonicity)
//  5. Dumps bit-exact vectors for the Python model and the RTL testbench
//
//  Build:  see scripts/build.ps1  (MSVC)  /  scripts/build.sh (g++)
//  Run  :  expmul.exe <out_dir>
// ============================================================================
#include "expmul.hpp"

#include <algorithm>
#include <cmath>
#include <cstdarg>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <random>
#include <string>
#include <vector>

using namespace fa;

namespace {

struct Stats {
  long long n = 0;
  double sum_rel = 0.0, sum_rel2 = 0.0, max_abs_rel = 0.0;
  double sum_log2_ratio = 0.0, sum_log2_ratio2 = 0.0;
  long long exact_bits = 0;      // Out bits == float(exp(x)*v) bits
  long long underflow = 0;       // exponent underflow -> 0
  long long saturated = 0;       // L == 0 (weight == 1)
  long long l_err0 = 0;          // L == round(-x*log2e) exactly
  long long within1 = 0, within5 = 0, within10 = 0, within20 = 0;
  double sum_ldelta = 0.0;
  std::vector<double> rel;       // for percentiles
};

inline double pct(std::vector<double>& v, double p) {
  if (v.empty()) return 0.0;
  size_t k = (size_t)(p * (double)(v.size() - 1));
  return v[k];
}

std::string fmt(const char* f, ...) {
  char buf[512];
  va_list ap;
  va_start(ap, f);
  vsnprintf(buf, sizeof(buf), f, ap);
  va_end(ap);
  return std::string(buf);
}

// random FP32 value with a wide dynamic range (sign, exponent, mantissa)
inline float rand_fp32(std::mt19937_64& rng, int lo_exp, int hi_exp) {
  std::uniform_int_distribution<int> sign(0, 1);
  std::uniform_int_distribution<int> ex(lo_exp, hi_exp);
  std::uniform_int_distribution<uint32_t> mant(0, FP32_MANT_MSK);
  uint32_t e = (uint32_t)ex(rng);
  uint32_t b = ((uint32_t)sign(rng) << 31) | (e << 23) | mant(rng);
  return u2f(b);
}

}  // namespace

int main(int argc, char** argv) {
  const std::string outdir = (argc > 1) ? argv[1] : "results/phase1";
  std::filesystem::create_directories(outdir);

  std::mt19937_64 rng(20250520ULL);
  const long long N = 2000000;

  std::uniform_real_distribution<double> u01(0.0, 1.0);

  // ---- x mixture: emphasise the region where attention weights actually live
  auto sample_x = [&](void) -> double {
    double u = u01(rng);
    if (u < 0.45) return -4.0 * u01(rng);            // [-4,0]   dominant weights
    if (u < 0.75) return -10.0 * u01(rng);           // [-10,0]
    return -15.0 * u01(rng);                          // [-15,0]
  };

  // =========================================================================
  //  1. random error characterisation
  // =========================================================================
  std::vector<float> xs;
  xs.reserve((size_t)N);
  std::vector<float> vs;
  vs.reserve((size_t)N);

  Stats st[3];
  for (int m = 0; m < 3; ++m) st[m].rel.reserve((size_t)N);

  std::ofstream fpair(outdir + "/expmul_pairs.csv");
  fpair << "x,v_bits,out_bits_nearest,L_nearest,out_bits_ceil,L_ceil,"
           "out_bits_mi,ref_double,rel_nearest,rel_ceil,rel_mi\n";

  long long nz = 0;
  for (long long i = 0; i < N; ++i) {
    float x = (float)sample_x();
    float v = rand_fp32(rng, 60, 190);   // |v| in ~[1e-20, 1e19]
    xs.push_back(x);
    vs.push_back(v);

    const int Ln = log2exp(x, LOG2EXP_NEAREST);
    const int Lc = log2exp(x, LOG2EXP_CEIL);
    const float yn = expmul_fp32(x, v, LOG2EXP_NEAREST);
    const float yc = expmul_fp32(x, v, LOG2EXP_CEIL);
    const float ym = expmul_mi_fp32(x, v);

    const double t = std::exp((double)x) * (double)v;   // exact reference
    const double ideal = -(double)x * 1.4426950408889634;
    const float ys[3] = {yn, yc, ym};
    const int   Ls[3] = {Ln, Lc, Ln};

    for (int m = 0; m < 3; ++m) {
      Stats& S = st[m];
      const float y = ys[m];
      const int L = Ls[m];
      S.n++;
      if (std::fabs(t) > 1e-300) {
        double r = ((double)y - t) / std::fabs(t);
        S.sum_rel += r;
        S.sum_rel2 += r * r;
        S.max_abs_rel = std::max(S.max_abs_rel, std::fabs(r));
        S.rel.push_back(std::fabs(r));
        if (std::fabs(r) <= 0.01) S.within1++;
        if (std::fabs(r) <= 0.05) S.within5++;
        if (std::fabs(r) <= 0.10) S.within10++;
        if (std::fabs(r) <= 0.20) S.within20++;
        double lr = std::log2(std::fabs(y / t));
        S.sum_log2_ratio += lr;
        S.sum_log2_ratio2 += lr * lr;
      }
      if (f2u(y) == f2u((float)(std::exp(x) * v))) S.exact_bits++;
      if (y == 0.0f && v != 0.0f) S.underflow++;
      if (L == 0) S.saturated++;
      double dl = (double)L - std::round(ideal);
      S.sum_ldelta += std::fabs(dl);
      if (std::round(ideal) == (double)L) S.l_err0++;
    }

    if (i < 100000) {
      fpair << fmt("%.9g", x) << "," << fmt("%08x", f2u(v)) << ","
            << fmt("%08x", f2u(yn)) << "," << Ln << ","
            << fmt("%08x", f2u(yc)) << "," << Lc << ","
            << fmt("%08x", f2u(ym)) << ","
            << fmt("%.17g", t) << ","
            << fmt("%.10g", (std::fabs(t) > 1e-300 ? ((double)yn - t) / std::fabs(t) : 0.0)) << ","
            << fmt("%.10g", (std::fabs(t) > 1e-300 ? ((double)yc - t) / std::fabs(t) : 0.0)) << ","
            << fmt("%.10g", (std::fabs(t) > 1e-300 ? ((double)ym - t) / std::fabs(t) : 0.0))
            << "\n";
    }
    if (t != 0.0) nz++;
  }
  fpair.close();

  // =========================================================================
  //  2. fine sweep of x (v = 1) -- weight vs exp(x)
  // =========================================================================
  std::ofstream fsw(outdir + "/expmul_sweep.csv");
  fsw << "x,x_hat,L_nearest,L_ceil,w_nearest,w_ceil,exp_x,ratio_nearest,ratio_ceil\n";
  const int NSW = 60001;
  int prevL = -1;
  bool monotone = true;
  for (int i = 0; i < NSW; ++i) {
    float x = -15.0f + 15.0f * (float)i / (float)(NSW - 1);
    if (i == 0) x = -15.0f;
    q6_10 q = to_q6_10(x);
    int Ln = log2exp_q(q, LOG2EXP_NEAREST);
    int Lc = log2exp_q(q, LOG2EXP_CEIL);
    if (i > 0 && Ln > prevL) monotone = false;   // x grows -> L must not grow
    prevL = Ln;
    float ex = std::exp(x);
    fsw << fmt("%.9g", x) << "," << (int)q.raw << "," << Ln << "," << Lc << ","
        << fmt("%.9g", weight_from_L(Ln)) << "," << fmt("%.9g", weight_from_L(Lc)) << ","
        << fmt("%.9g", ex) << ","
        << fmt("%.9g", (double)weight_from_L(Ln) / (double)ex) << ","
        << fmt("%.9g", (double)weight_from_L(Lc) / (double)ex) << "\n";
  }
  fsw.close();

  // =========================================================================
  //  3. edge cases
  // =========================================================================
  std::ofstream fedge(outdir + "/expmul_edge_cases.csv");
  fedge << "case,x,v_bits,v,out_bits_nearest,out,L_nearest,note\n";
  struct EdgeCase { const char* name; float x; float v; const char* note; };
  std::vector<EdgeCase> edges = {
      {"x_zero",            0.0f,            1.0f,        "identity: Out must equal V"},
      {"x_negzero",        -0.0f,            1.0f,        "identity"},
      {"x_tiny_neg",       -1e-9f,           1.0f,        "L=0 -> identity"},
      {"x_clip_min",      -15.0f,            1.0f,        "clip boundary"},
      {"x_below_clip",    -20.0f,            1.0f,        "clipped to -15"},
      {"x_positive",        3.0f,            1.0f,        "clipped to 0 (illegal input)"},
      {"x_nan",          NAN,                1.0f,        "must not produce NaN"},
      {"x_zero_v_zero",     0.0f,            0.0f,        "zero in -> zero out"},
      {"x_zero_v_negzero",  0.0f,           -0.0f,        "zero in -> +0 out"},
      {"v_neg",            -1.0f,           -2.5f,        "sign preserved"},
      {"v_flt_min",        -1.0f, 1.17549435e-38f,        "min normal, L=1 -> normal"},
      {"v_max",           -15.0f, 3.40282347e+38f,        "max normal, L=22"},
      {"v_subnormal",       0.0f, 1e-40f,                 "subnormal input -> 0"},
      {"v_inf",             0.0f, INFINITY,               "inf passthrough"},
  };
  // explicit subnormal-underflow case
  edges.push_back({"v_subnormal_underflow", -5.0f, 1e-40f, "input subnormal -> 0"});
  for (auto& e : edges) {
    int L = log2exp(e.x, LOG2EXP_NEAREST);
    float y = expmul_fp32(e.x, e.v, LOG2EXP_NEAREST);
    fedge << e.name << "," << fmt("%.9g", e.x) << "," << fmt("%08x", f2u(e.v)) << ","
          << fmt("%.9g", e.v) << "," << fmt("%08x", f2u(y)) << "," << fmt("%.9g", y)
          << "," << L << "," << e.note << "\n";
  }
  fedge.close();

  // =========================================================================
  //  4. per-range error table
  // =========================================================================
  const double edges_x[8] = {15.0, 10.0, 7.0, 4.0, 2.0, 1.0, 0.5, 0.0};
  std::ofstream fbucket(outdir + "/expmul_error_by_range.csv");
  fbucket << "range_lo,range_hi,pairs,mean_rel,rms_rel,max_rel,mean_abs_dL\n";
  std::printf("\n%-16s %9s %10s %10s %10s %10s\n", "|x| range", "pairs",
              "mean e", "rms e", "max|e|", "E|dL|");
  for (int b = 0; b < 7; ++b) {
    double lo = edges_x[b + 1], hi = edges_x[b];
    long long n = 0, bad = 0;
    double s = 0, s2 = 0, mx = 0, dl = 0;
    for (size_t i = 0; i < xs.size(); ++i) {
      double ax = -(double)xs[i];                    // |x|, x <= 0
      if (ax < lo || ax >= hi) continue;
      double t = std::exp((double)xs[i]) * (double)vs[i];
      if (std::fabs(t) < 1e-300) { bad++; continue; }
      double y = (double)expmul_fp32(xs[i], vs[i]);
      double r = (y - t) / std::fabs(t);
      n++; s += r; s2 += r * r; mx = std::max(mx, std::fabs(r));
      dl += std::fabs((double)log2exp(xs[i]) - std::round(-(double)xs[i] * 1.4426950408889634));
    }
    double mean = n ? s / n : 0, rms = n ? std::sqrt(s2 / n) : 0;
    std::printf("%5.1f .. %5.1f   %9lld %+10.4f %10.4f %10.4f %10.3f\n",
                lo, hi, n, mean, rms, mx, n ? dl / n : 0.0);
    if (n) {
      fbucket << fmt("%.1f", lo) << "," << fmt("%.1f", hi) << "," << n << ","
              << fmt("%.6f", mean) << "," << fmt("%.6f", rms) << ","
              << fmt("%.6f", mx) << "," << fmt("%.4f", dl / n) << "\n";
    }
  }
  fbucket.close();

  // =========================================================================
  //  5. summary + JSON
  // =========================================================================
  std::string json = "{\n  \"seed\": 20250520,\n  \"pairs\": " + std::to_string(N) + ",\n";
  const char* names[3] = {"exp_only_near", "exp_only_ceil", "mantissa_int"};
  std::printf("\n== ExpMul(x,V) vs exact e^x*V ==\n");
  std::printf("%-14s %8s %9s %9s %9s %9s %9s %9s\n", "variant", "n",
              "mean", "rms", "p50", "p90", "p99", "max");
  for (int m = 0; m < 3; ++m) {
    Stats& S = st[m];
    std::sort(S.rel.begin(), S.rel.end());
    double mean = S.sum_rel / S.n;
    double rms = std::sqrt(S.sum_rel2 / S.n);
    double p50 = pct(S.rel, 0.50), p90 = pct(S.rel, 0.90), p99 = pct(S.rel, 0.99);
    std::printf("%-14s %8lld %+9.4f %9.4f %9.4f %9.4f %9.4f %9.4f\n",
                names[m], S.n, mean, rms, p50, p90, p99, S.max_abs_rel);
    json += std::string("  \"") + names[m] + "\": {\n";
    json += "    \"mean_rel\": " + fmt("%.8f", mean) + ",\n";
    json += "    \"rms_rel\": " + fmt("%.8f", rms) + ",\n";
    json += "    \"p50_abs_rel\": " + fmt("%.8f", p50) + ",\n";
    json += "    \"p90_abs_rel\": " + fmt("%.8f", p90) + ",\n";
    json += "    \"p99_abs_rel\": " + fmt("%.8f", p99) + ",\n";
    json += "    \"max_abs_rel\": " + fmt("%.8f", S.max_abs_rel) + ",\n";
    json += "    \"mean_log2_ratio\": " + fmt("%.8f", S.sum_log2_ratio / S.n) + ",\n";
    json += "    \"std_log2_ratio\": " + fmt("%.8f", std::sqrt(std::max(0.0, S.sum_log2_ratio2 / S.n - std::pow(S.sum_log2_ratio / S.n, 2)))) + ",\n";
    json += "    \"frac_L_eq_round\": " + fmt("%.8f", (double)S.l_err0 / S.n) + ",\n";
    json += "    \"mean_abs_dL\": " + fmt("%.8f", S.sum_ldelta / S.n) + ",\n";
    json += "    \"frac_weight_one\": " + fmt("%.8f", (double)S.saturated / S.n) + ",\n";
    json += "    \"frac_underflow_to_zero\": " + fmt("%.8f", (double)S.underflow / S.n) + ",\n";
    json += "    \"frac_within_1pct\": " + fmt("%.8f", (double)S.within1 / S.n) + ",\n";
    json += "    \"frac_within_5pct\": " + fmt("%.8f", (double)S.within5 / S.n) + ",\n";
    json += "    \"frac_within_10pct\": " + fmt("%.8f", (double)S.within10 / S.n) + ",\n";
    json += "    \"frac_within_20pct\": " + fmt("%.8f", (double)S.within20 / S.n) + ",\n";
    json += "    \"frac_bitwise_eq_float_ref\": " + fmt("%.8f", (double)S.exact_bits / S.n) + "\n";
    json += std::string("  }") + ",\n";
  }
  json += "  \"monotonic_in_x\": " + std::string(monotone ? "true" : "false") + ",\n";
  json += "  \"sweep_points\": " + std::to_string(NSW) + "\n}\n";
  std::ofstream fj(outdir + "/expmul_stats.json");
  fj << json;
  fj.close();

  std::printf("\nmonotone L(x) over [-15,0]: %s\n", monotone ? "yes" : "NO");
  std::printf("wrote %s/{expmul_pairs.csv,expmul_sweep.csv,expmul_edge_cases.csv,"
              "expmul_error_by_range.csv,expmul_stats.json}\n", outdir.c_str());

  // invariants
  bool ok = true;
  float probes[] = {1.0f, -1.0f, 12345.0f, 1e-30f, 3.4e38f, 0.0f};
  for (float v : probes) {
    if (f2u(expmul_fp32(0.0f, v)) != f2u(v) && v != 0.0f) ok = false;
    float y = expmul_fp32(-3.7f, v);
    if (std::fabs(y) > std::fabs(v)) ok = false;
  }
  std::printf("invariants (identity at x=0, |Out|<=|V|): %s\n", ok ? "PASS" : "FAIL");
  return ok ? 0 : 2;
}
