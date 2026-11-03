// ============================================================================
//  tb.cpp -- shared testbench for the baseline and ExpMul FlashAttention-2
//            kernels (phase 2)
//
//  1. exp-unit accuracy (baseline PWL vs libm)
//  2. functional sweep: dtype x d x N x temperature, 3 implementations
//     (baseline / ExpMul Alg.3 / ExpMul mantissa-interp) vs a double-precision
//     FlashAttention-2 reference with the *same* loop order
//  3. per-query error detail for d=64, N=512, FP32
//  4. numerical-stability corner cases (huge scores, uniform scores, N=1, ...)
//  5. block-parallel equivalence: P=1 vs P=4 (broadcast K/V)
//
//  Build : scripts/build.ps1 / scripts/build.sh
//  Run   : tb.exe results/phase2
// ============================================================================
#include "flash_attn.hpp"

#include <algorithm>
#include <cmath>
#include <cstdarg>
#include <cstdio>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <random>
#include <string>
#include <vector>

using namespace fa;

namespace {

// ---------------------------------------------------------------------------
//  deterministic RNG (Box-Muller on top of mt19937_64, seed 20250520)
// ---------------------------------------------------------------------------
struct Rng {
  std::mt19937_64 g;
  std::uniform_real_distribution<double> u{1e-12, 1.0};
  explicit Rng(uint64_t seed) : g(seed) {}
  double next() { return u(g); }
  double normal() {
    double a = next(), b = next();
    return std::sqrt(-2.0 * std::log(a)) * std::cos(6.283185307179586 * b);
  }
};

std::string fmt(const char* f, ...) {
  char buf[512];
  va_list ap;
  va_start(ap, f);
  vsnprintf(buf, sizeof(buf), f, ap);
  va_end(ap);
  return std::string(buf);
}

// ---------------------------------------------------------------------------
//  double-precision FlashAttention-2 reference (same order as the kernels)
// ---------------------------------------------------------------------------
template <int D>
void ref_attn(const double* q, const double* K, const double* V, int N, double* o) {
  double l = 0.0, m = -1e30;
  double acc[D];
  for (int j = 0; j < D; ++j) acc[j] = 0.0;
  for (int i = 0; i < N; ++i) {
    const double* k = K + (size_t)i * D;
    const double* v = V + (size_t)i * D;
    double s = 0.0;
    for (int j = 0; j < D; ++j) s += q[j] * k[j];
    const double mn = std::max(m, s);
    const double e1 = std::exp(m - mn);
    const double e2 = std::exp(s - mn);
    l = l * e1 + e2;
    for (int j = 0; j < D; ++j) acc[j] = acc[j] * e1 + v[j] * e2;
    m = mn;
  }
  for (int j = 0; j < D; ++j) o[j] = acc[j] / l;
}

// ---------------------------------------------------------------------------
//  error metrics between a float result and the double reference
// ---------------------------------------------------------------------------
struct Metric {
  double l2_mean = 0, l2_p95 = 0, l2_max = 0;
  double el_p50 = 0, el_p95 = 0, el_max = 0;
  long long nf = 0;      // non-finite outputs
};

Metric compare(const std::vector<float>& got, const std::vector<double>& ref, int d) {
  const size_t n = got.size();
  const size_t nq = n / (size_t)d;
  std::vector<double> l2(nq);
  std::vector<double> el;
  el.reserve(n);
  Metric M;
  double sum = 0, mx = 0;
  // global rms of the reference, used to gate tiny elements
  double rms = 0;
  for (size_t i = 0; i < n; ++i) rms += ref[i] * ref[i];
  rms = std::sqrt(rms / (double)n);
  const double gate = 0.01 * rms + 1e-30;
  for (size_t q = 0; q < nq; ++q) {
    double num = 0, den = 0;
    for (int j = 0; j < d; ++j) {
      const double e = (double)got[q * d + j] - ref[q * d + j];
      if (!std::isfinite((double)got[q * d + j])) M.nf++;
      num += e * e;
      den += ref[q * d + j] * ref[q * d + j];
      if (std::fabs(ref[q * d + j]) > gate) {
        el.push_back(std::fabs(e) / std::fabs(ref[q * d + j]));
      }
    }
    l2[q] = std::sqrt(num / (den + 1e-30));
    sum += l2[q];
    mx = std::max(mx, l2[q]);
  }
  std::sort(l2.begin(), l2.end());
  std::sort(el.begin(), el.end());
  M.l2_mean = sum / (double)nq;
  M.l2_p95 = l2[(size_t)(0.95 * (l2.size() - 1))];
  M.l2_max = mx;
  if (!el.empty()) {
    M.el_p50 = el[el.size() / 2];
    M.el_p95 = el[(size_t)(0.95 * (el.size() - 1))];
    M.el_max = el.back();
  }
  return M;
}

// ---------------------------------------------------------------------------
//  data generation in T storage format
// ---------------------------------------------------------------------------
template <int D, class T>
void gen_qkv(Rng& rng, int nq, int N, double temp,
             std::vector<typename T::storage>& Q,
             std::vector<typename T::storage>& K,
             std::vector<typename T::storage>& V, std::vector<double>& Qd,
             std::vector<double>& Kd, std::vector<double>& Vd) {
  const double qs = temp / std::sqrt((double)D);
  Q.resize((size_t)nq * D);
  Qd.resize((size_t)nq * D);
  for (size_t i = 0; i < Q.size(); ++i) {
    Qd[i] = rng.normal() * qs;
    Q[i] = T::from_float((float)Qd[i]);
    Qd[i] = T::to_float(Q[i]);          // keep the reference consistent with T
  }
  K.resize((size_t)N * D);
  Kd.resize((size_t)N * D);
  V.resize((size_t)N * D);
  Vd.resize((size_t)N * D);
  for (size_t i = 0; i < K.size(); ++i) {
    Kd[i] = rng.normal();
    K[i] = T::from_float((float)Kd[i]);
    Kd[i] = T::to_float(K[i]);
    Vd[i] = rng.normal();
    V[i] = T::from_float((float)Vd[i]);
    Vd[i] = T::to_float(V[i]);
  }
}

// ---------------------------------------------------------------------------
//  host-side sequencer: the accelerator processes P queries per pass, so the
//  testbench walks over all queries in blocks of P (Fig.1/Fig.2 dataflow).
// ---------------------------------------------------------------------------
template <int P, int D, class T>
void baseline_all(const typename T::storage* Q, const typename T::storage* K,
                  const typename T::storage* V, int N, typename T::storage* O) {
  for (int q0 = 0; q0 < N; q0 += P)
    fa2_baseline<P, D, T>(Q + (size_t)q0 * D, K, V, N, O + (size_t)q0 * D);
}

template <int P, int D, class T>
void expmul_all(const typename T::storage* Q, const typename T::storage* K,
                const typename T::storage* V, int N, typename T::storage* O,
                int variant) {
  for (int q0 = 0; q0 < N; q0 += P)
    fa2_expmul<P, D, T>(Q + (size_t)q0 * D, K, V, N, O + (size_t)q0 * D, variant);
}

// ---------------------------------------------------------------------------
//  one sweep point: baseline + 2 ExpMul variants vs double reference
// ---------------------------------------------------------------------------
template <int D, class T>
void run_point(const char* tname, int N, double temp, Rng& rng, std::ofstream& ferr,
               Metric* out[3]) {
  std::vector<typename T::storage> Q, K, V;
  std::vector<double> Qd, Kd, Vd;
  gen_qkv<D, T>(rng, N, N, temp, Q, K, V, Qd, Kd, Vd);

  std::vector<double> ref((size_t)N * D);
  for (int q = 0; q < N; ++q) {
    ref_attn<D>(&Qd[(size_t)q * D], Kd.data(), Vd.data(), N, &ref[(size_t)q * D]);
  }

  const char* names[3] = {"baseline", "expmul_exp", "expmul_mi"};
  for (int v = 0; v < 3; ++v) {
    std::vector<typename T::storage> O((size_t)N * D);
    if (v == 0) {
      baseline_all<4, D, T>(Q.data(), K.data(), V.data(), N, O.data());
    } else {
      expmul_all<4, D, T>(Q.data(), K.data(), V.data(), N, O.data(), v - 1);
    }
    std::vector<float> Of(O.size());
    for (size_t i = 0; i < O.size(); ++i) Of[i] = T::to_float(O[i]);
    const Metric M = compare(Of, ref, D);
    ferr << fmt("%d,%s,%s,%d,%.2f,%.6f,%.6f,%.6f,%.6f,%.6f,%.6f,%lld\n", D, tname,
                names[v], N, temp, M.l2_mean, M.l2_p95, M.l2_max, M.el_p50, M.el_p95,
                M.el_max, M.nf);
    if (out) *out[v] = M;
    std::printf("  d=%-2d %-5s N=%-4d T=%.1f %-11s relL2 mean=%.5f p95=%.5f max=%.5f"
                "  el p95=%.4f\n", D, tname, N, temp, names[v], M.l2_mean, M.l2_p95,
                M.l2_max, M.el_p95);
  }
}

// ---------------------------------------------------------------------------
//  stability corner cases (FP32, d=64)
// ---------------------------------------------------------------------------
template <int D, class T>
void stability(const char* tname, std::ofstream& fst) {
  struct Case { const char* name; double qscale; int N; int mode; double vscale; };
  // mode 0: random, 1: all-equal scores (uniform attention), 2: one dominant key
  const Case cases[] = {
      {"random",         1.0,  64, 0, 1.0},
      {"temp4",          4.0,  64, 0, 1.0},
      {"huge_1e3",       1e3,  64, 0, 1.0},
      {"huge_1e6",       1e6,  64, 0, 1.0},
      {"uniform",        0.0,  64, 1, 1.0},
      {"single_key",     1.0,   1, 0, 1.0},
      {"dominant_key",   1.0,  64, 2, 1.0},
      {"v_large_1e30",   1.0,  64, 0, 1e30},
      {"v_tiny_1e-30",   1.0,  64, 0, 1e-30},
  };
  Rng rng(777);
  for (const auto& c : cases) {
    const int N = c.N;
    std::vector<typename T::storage> Q((size_t)D), K((size_t)N * D), V((size_t)N * D);
    std::vector<double> Qd((size_t)D), Kd((size_t)N * D), Vd((size_t)N * D);
    for (int j = 0; j < D; ++j) {
      Qd[j] = rng.normal() * c.qscale / std::sqrt((double)D);
      Q[j] = T::from_float((float)Qd[j]);
      Qd[j] = T::to_float(Q[j]);
    }
    for (int i = 0; i < N; ++i) {
      for (int j = 0; j < D; ++j) {
        double kv = (c.mode == 1) ? 0.1731 : rng.normal();
        if (c.mode == 2 && i > 0) kv *= 0.01;     // first key dominates
        Kd[(size_t)i * D + j] = kv;
        K[(size_t)i * D + j] = T::from_float((float)kv);
        Kd[(size_t)i * D + j] = T::to_float(K[(size_t)i * D + j]);
        double vv = rng.normal() * c.vscale;
        Vd[(size_t)i * D + j] = vv;
        V[(size_t)i * D + j] = T::from_float((float)vv);
        Vd[(size_t)i * D + j] = T::to_float(V[(size_t)i * D + j]);
      }
    }
    std::vector<double> ref((size_t)D);
    ref_attn<D>(Qd.data(), Kd.data(), Vd.data(), N, ref.data());

    // naive softmax without max subtraction -- shows the overflow we avoid
    int naive_bad = 0;
    for (int i = 0; i < N; ++i) {
      double s = 0;
      for (int j = 0; j < D; ++j) s += Qd[j] * Kd[(size_t)i * D + j];
      float e = (float)std::exp(s);              // FP32 exp, no max removal
      if (!std::isfinite(e)) naive_bad = 1;
    }

    std::vector<typename T::storage> O0((size_t)D), O1((size_t)D), O2((size_t)D);
    fa2_baseline<1, D, T>(Q.data(), K.data(), V.data(), N, O0.data());
    fa2_expmul<1, D, T>(Q.data(), K.data(), V.data(), N, O1.data(), 0);
    fa2_expmul<1, D, T>(Q.data(), K.data(), V.data(), N, O2.data(), 1);

    double max_abs[3] = {0, 0, 0}, rel_l2[3] = {0, 0, 0}, ref_norm = 0;
    long long nf[3] = {0, 0, 0};
    for (int j = 0; j < D; ++j) ref_norm += ref[j] * ref[j];
    ref_norm = std::sqrt(ref_norm);
    const typename T::storage* Os[3] = {O0.data(), O1.data(), O2.data()};
    for (int v = 0; v < 3; ++v) {
      double num = 0;
      for (int j = 0; j < D; ++j) {
        const double g = T::to_float(Os[v][j]);
        if (!std::isfinite(g)) nf[v]++;
        const double e = g - ref[j];
        num += e * e;
        max_abs[v] = std::max(max_abs[v], std::fabs(e));
      }
      rel_l2[v] = std::sqrt(num) / std::max(ref_norm, 1e-30);
    }

    fst << fmt("%s,%d,%d,%.3g,%.3g,%.6e,%.6e,%.6e,%.6e,%.6e,%.6e,%.6e,%d,%lld,%lld,%lld\n",
               tname, D, N, c.qscale, c.vscale, max_abs[0], max_abs[1], max_abs[2],
               rel_l2[0], rel_l2[1], rel_l2[2], ref_norm, naive_bad, nf[0], nf[1],
               nf[2]);
    std::printf("  stability %-13s N=%-3d q=%-7.3g v=%-7.3g | max|err| base=%.2e "
                "exp=%.2e mi=%.2e | relL2 base=%.2e exp=%.2e mi=%.2e | naive_ovf=%d\n",
                c.name, N, c.qscale, c.vscale, max_abs[0], max_abs[1], max_abs[2],
                rel_l2[0], rel_l2[1], rel_l2[2], naive_bad);
  }
}

}  // namespace

int main(int argc, char** argv) {
  const std::string outdir = (argc > 1) ? argv[1] : "results/phase2";
  std::filesystem::create_directories(outdir);

  std::printf("== Phase 2: FlashAttention-2 baseline vs ExpMul ==\n");

  // ------------------------------------------------------------------
  //  1. baseline exp unit accuracy (PWL, 8 segments)
  // ------------------------------------------------------------------
  {
    std::ofstream fe(outdir + "/exp_unit_error.csv");
    fe << "x,exp_exact,exp_pwl,rel_err\n";
    double mx = 0, sum = 0;
    int n = 0;
    for (int i = 0; i <= 200000; ++i) {
      float x = -15.0f + 15.0f * (float)i / 200000.0f;
      if (i == 200000) x = 0.0f;
      const double ref = std::exp((double)x);
      const double got = (double)exp_pwl<8>(x);
      const double rel = std::fabs(got - ref) / ref;
      mx = std::max(mx, rel);
      sum += rel;
      ++n;
      if ((i % 200) == 0) fe << fmt("%.7g,%.9g,%.9g,%.9g\n", x, ref, got, rel);
    }
    fe.close();
    std::printf("exp PWL(8): max rel err = %.4f%%, mean = %.4f%%\n", 100 * mx,
                100 * sum / n);
  }

  // ------------------------------------------------------------------
  //  2. sweep
  // ------------------------------------------------------------------
  std::ofstream ferr(outdir + "/errors_matrix.csv");
  ferr << "d,dtype,variant,N,temp,rel_l2_mean,rel_l2_p95,rel_l2_max,"
          "el_p50,el_p95,el_max,nonfinite\n";
  Rng rng(20250520);
  const int Ns[] = {16, 64, 128, 512};
  const double temps[] = {1.0, 2.0};
  std::printf("\n-- error sweep (rel-L2 per query vs double reference) --\n");
  for (int di = 0; di < 3; ++di) {
    for (int ti = 0; ti < 2; ++ti) {
      for (int ni = 0; ni < 4; ++ni) {
        const int N = Ns[ni];
        const double tp = temps[ti];
        if (di == 0) {
          run_point<16, FP32Policy>("fp32", N, tp, rng, ferr, nullptr);
          run_point<16, BF16Policy>("bf16", N, tp, rng, ferr, nullptr);
        } else if (di == 1) {
          run_point<32, FP32Policy>("fp32", N, tp, rng, ferr, nullptr);
          run_point<32, BF16Policy>("bf16", N, tp, rng, ferr, nullptr);
        } else {
          run_point<64, FP32Policy>("fp32", N, tp, rng, ferr, nullptr);
          run_point<64, BF16Policy>("bf16", N, tp, rng, ferr, nullptr);
        }
      }
    }
  }
  ferr.close();

  // ------------------------------------------------------------------
  //  3. per-query detail for d=64, N=512, FP32, temp=1
  // ------------------------------------------------------------------
  {
    const int D = 64, N = 512;
    Rng r2(424242);
    std::vector<FP32Policy::storage> Q, K, V;
    std::vector<double> Qd, Kd, Vd;
    gen_qkv<64, FP32Policy>(r2, N, N, 1.0, Q, K, V, Qd, Kd, Vd);
    std::vector<double> ref((size_t)N * D);
    for (int q = 0; q < N; ++q)
      ref_attn<64>(&Qd[(size_t)q * D], Kd.data(), Vd.data(), N, &ref[(size_t)q * D]);

    std::ofstream fd(outdir + "/detail_d64_N512_fp32.csv");
    fd << "query,rel_l2_baseline,rel_l2_expmul_exp,rel_l2_expmul_mi\n";
    std::vector<std::vector<float>> outs(3, std::vector<float>((size_t)N * D));
    for (int v = 0; v < 3; ++v) {
      std::vector<FP32Policy::storage> O((size_t)N * D);
      if (v == 0) baseline_all<4, 64, FP32Policy>(Q.data(), K.data(), V.data(), N, O.data());
      else expmul_all<4, 64, FP32Policy>(Q.data(), K.data(), V.data(), N, O.data(), v - 1);
      for (size_t i = 0; i < O.size(); ++i) outs[v][i] = O[i];
    }
    Metric M[3];
    for (int v = 0; v < 3; ++v) M[v] = compare(outs[v], ref, D);
    for (int q = 0; q < N; ++q) {
      double l2[3];
      for (int v = 0; v < 3; ++v) {
        double num = 0, den = 0;
        for (int j = 0; j < D; ++j) {
          const double e = (double)outs[v][(size_t)q * D + j] - ref[(size_t)q * D + j];
          num += e * e;
          den += ref[(size_t)q * D + j] * ref[(size_t)q * D + j];
        }
        l2[v] = std::sqrt(num / (den + 1e-30));
      }
      fd << fmt("%d,%.8f,%.8f,%.8f\n", q, l2[0], l2[1], l2[2]);
    }
    fd.close();
    std::printf("\ndetail d=64 N=512 fp32: relL2 mean base=%.5f exp=%.5f mi=%.5f\n",
                M[0].l2_mean, M[1].l2_mean, M[2].l2_mean);
  }

  // ------------------------------------------------------------------
  //  4. stability
  // ------------------------------------------------------------------
  std::printf("\n-- numerical stability --\n");
  std::ofstream fst(outdir + "/stability.csv");
  fst << "dtype,d,N,qscale,vscale,max_abs_base,max_abs_exp,max_abs_mi,"
         "rel_l2_base,rel_l2_exp,rel_l2_mi,ref_norm,naive_exp_overflow,"
         "nonfinite_base,nonfinite_exp,nonfinite_mi\n";
  stability<64, FP32Policy>("fp32", fst);
  stability<64, BF16Policy>("bf16", fst);
  fst.close();

  // ------------------------------------------------------------------
  //  5. block-parallel equivalence: P=1 vs P=4
  // ------------------------------------------------------------------
  {
    const int D = 64, N = 128, P = 4;
    Rng r3(999);
    std::vector<FP32Policy::storage> Q, K, V;
    std::vector<double> Qd, Kd, Vd;
    gen_qkv<64, FP32Policy>(r3, P, N, 1.0, Q, K, V, Qd, Kd, Vd);
    std::vector<FP32Policy::storage> O4((size_t)P * D), O1((size_t)P * D);
    fa2_expmul<P, 64, FP32Policy>(Q.data(), K.data(), V.data(), N, O4.data(), 1);
    for (int b = 0; b < P; ++b)
      fa2_expmul<1, 64, FP32Policy>(&Q[(size_t)b * D], K.data(), V.data(), N,
                                    &O1[(size_t)b * D], 1);
    int diff = 0;
    for (size_t i = 0; i < O4.size(); ++i) diff += (O4[i] != O1[i]);
    std::printf("\nblock-parallel P=4 vs P=1: %d differing lanes (expect 0)\n", diff);
    std::ofstream fb(outdir + "/blocking_check.csv");
    fb << "lanes,differing\n" << O4.size() << "," << diff << "\n";
    fb.close();
  }

  // ------------------------------------------------------------------
  //  6. JSON summary
  // ------------------------------------------------------------------
  {
    std::ofstream fj(outdir + "/phase2_stats.json");
    fj << "{\n";
    fj << "  \"seed\": 20250520,\n";
    fj << "  \"metric\": \"rel_l2 = per-query ||o-ref||_2 / ||ref||_2, double-precision FA2 reference\",\n";
    fj << "  \"kernels\": [\"baseline(PWL exp + FP mul)\", \"expmul_exp(Alg.3)\", \"expmul_mi(mantissa interp)\"],\n";
    fj << "  \"dtype\": [\"fp32\", \"bf16\"],\n";
    fj << "  \"d\": [16, 32, 64],\n";
    fj << "  \"N\": [16, 64, 128, 512],\n";
    fj << "  \"temperature\": [1.0, 2.0],\n";
    fj << "  \"sweep\": \"see errors_matrix.csv\",\n";
    fj << "  \"stability\": \"see stability.csv\",\n";
    fj << "  \"block_parallel\": \"P=4 vs P=1 identical (see blocking_check.csv)\"\n";
    fj << "}\n";
    fj.close();
  }

  std::printf("\nwrote %s/{errors_matrix.csv,detail_d64_N512_fp32.csv,stability.csv,"
              "exp_unit_error.csv,blocking_check.csv}\n", outdir.c_str());
  return 0;
}
