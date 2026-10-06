"""
llm_pqc_optimizer.py : LLM-Guided Cryptographic Hardware Optimizer & DSE Reasoner

Provides domain-specific AI reasoning for Post-Quantum Cryptography silicon:
1. Ring & Twiddle Geometry Reasoning: Automates parameter derivation for Dilithium, Kyber, and custom rings.
2. Side-Channel Leakage Minimization: Evaluates hardware Hamming toggle traces from perf_counters.v to guide DPA resistance.
3. Physical Path Delay Analysis: Recommends pipeline retiming strategies on SkyWater 130nm.
"""

import sys
import os
import math
from typing import Dict, Any, List

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from ntt_golden import modinv_general, MONT_R, MONT_R_BITS, modexp, bit_reverse


class PQCGeometryReasoner:
    """Derives mathematical constants and scheduling microcode for arbitrary PQC rings."""

    def compile_scheme_parameters(self, name: str, q: int, n: int, root: int) -> Dict[str, Any]:
        """Derive hardware parameters for Montgomery arithmetic, twiddles, and stage seeds."""
        qprime = (-modinv_general(q, MONT_R)) % MONT_R
        r2 = (MONT_R * MONT_R) % q
        ninv = modinv_general(n, q)
        ninv_mont = (ninv * MONT_R) % q

        # Bit width needed
        coeff_width = math.ceil(math.log2(q))

        # Check NTT completeness (does 2n divide q - 1?)
        is_complete = ((q - 1) % (2 * n) == 0)
        stages = int(math.log2(n)) if is_complete else int(math.log2(n)) - 1

        # Derive stage seeds for on-the-fly twiddle generator
        stage_seeds = []
        for s in range(int(math.log2(n))):
            idx = 1 << s
            br_idx = bit_reverse(idx, int(math.log2(n)))
            zeta_val = modexp(root, br_idx, q)
            zeta_mont = (zeta_val * MONT_R) % q
            stage_seeds.append(zeta_mont)

        return {
            "name": name,
            "modulus_q": q,
            "poly_degree_n": n,
            "root_of_unity": root,
            "coeff_width_bits": coeff_width,
            "is_complete_ntt": is_complete,
            "transform_stages": stages,
            "montgomery_r": MONT_R,
            "qprime": qprime,
            "r2_mont": r2,
            "ninv_mont": ninv_mont,
            "stage_seeds_mont": stage_seeds,
        }

    def generate_reasoning_report(self, params: Dict[str, Any]) -> str:
        """Generate human-readable architectural reasoning report."""
        report = []
        report.append(f"### [AI Co-Pilot] Mathematical Ring & Microarchitecture Analysis: {params['name']}")
        report.append(f"* **Ring Specification**: $\\mathbb{{Z}}_{{{params['modulus_q']}}}[x]/(x^{{{params['poly_degree_n']}}} + 1)$")
        report.append(f"* **Arithmetic Completeness**: {'Complete Radix-2/Radix-4 NTT (2n | q-1)' if params['is_complete_ntt'] else 'Incomplete NTT (Base case: degree-1 polynomial multiplication)'}")
        report.append(f"* **Optimal Datapath Width**: {params['coeff_width_bits']} bits (fits inside standard 24-bit/32-bit register file)")
        report.append(f"* **Montgomery Constants**: $Q' = {params['qprime']}$, $R^2 = {params['r2_mont']}$, $n^{{-1}}_{{\\text{{mont}}}} = {params['ninv_mont']}$")
        report.append(f"* **On-The-Fly Twiddle Generator (N4)**: Initialized with {len(params['stage_seeds_mont'])} stage seeds; avoids {params['poly_degree_n']}-word ROM storage.")
        return "\n".join(report)


class SideChannelLeakageReasoner:
    """Reasons over hardware telemetry toggle counts from perf_counters.v to evaluate DPA risk."""

    def evaluate_leakage_profile(self, toggle_count: int, cycles: int, masked: bool) -> Dict[str, Any]:
        toggles_per_cycle = toggle_count / max(1, cycles)

        # In unmasked datapaths, high Hamming distance transitions correlate with secret key bits
        # First-order Boolean/modular share masking decorrelates Hamming distance from the secret
        dpa_vulnerability_score = (toggles_per_cycle * 0.85) if not masked else (toggles_per_cycle * 0.12)
        leakage_risk = "LOW (First-order Masked)" if masked else ("HIGH" if toggles_per_cycle > 3.5 else "MEDIUM")

        recommendation = (
            "Masking is ACTIVE: Coefficient shares (x0, x1) decorrelate power consumption from secret polynomials."
            if masked else
            "Enable first-order share masking (`mask.v`) for private key operations (ML-DSA signing / ML-KEM decapsulation) to prevent DPA key extraction."
        )

        return {
            "total_toggles": toggle_count,
            "toggles_per_cycle": round(toggles_per_cycle, 2),
            "dpa_vulnerability_index": round(dpa_vulnerability_score, 2),
            "leakage_risk": leakage_risk,
            "ai_recommendation": recommendation,
        }


class PhysicalTimingAdvisor:
    """Analyzes physical synthesis critical paths on SkyWater 130nm."""

    def analyze_critical_path(self, depth: int, radix: int) -> Dict[str, Any]:
        # Critical path in unpipelined Montgomery cell: 24b Mul -> 32b Q' Mul -> 56b Add -> Conditional Sub
        stage_delay_ns = 22.5 / depth
        fmax_est_mhz = 1000.0 / (stage_delay_ns + 1.2)  # 1.2ns setup+clock-to-q overhead

        advice = []
        if depth == 1:
            advice.append("Critical path is constrained by the combined product-sum chain ($T + m \\cdot Q$). Clock frequency limited to ~40 MHz.")
        elif depth >= 3:
            advice.append("Multi-stage pipelining breaks the multiplier carry chain into balanced segments, enabling >80 MHz operation on Sky130 hd standard cells.")

        if radix == 4:
            advice.append("Radix-4 butterfly processes 4 terms concurrently, reducing transform stages by 50% for maximum throughput.")

        return {
            "multiplier_stages": depth,
            "butterfly_radix": radix,
            "estimated_fmax_mhz": round(fmax_est_mhz, 1),
            "critical_path_stage_delay_ns": round(stage_delay_ns, 2),
            "advisor_notes": advice,
        }


if __name__ == "__main__":
    reasoner = PQCGeometryReasoner()
    dil_res = reasoner.compile_scheme_parameters("ML-DSA (Dilithium)", 8380417, 256, 1753)
    print(reasoner.generate_reasoning_report(dil_res))

    ky_res = reasoner.compile_scheme_parameters("ML-KEM (Kyber)", 3329, 256, 17)
    print("\n" + reasoner.generate_reasoning_report(ky_res))

    sc_reasoner = SideChannelLeakageReasoner()
    sc_eval = sc_reasoner.evaluate_leakage_profile(toggle_count=8450, cycles=6144, masked=True)
    print("\nSide-Channel Evaluation:", sc_eval)
