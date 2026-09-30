"""Run the official NIST ACVP ML-KEM-512 keyGen vectors through the complete HSKEM RTL.

The co-processor accepts a deterministic key-generation seed over SPI (opcode 0x14 with
d || z || k, the test path of the full-system testbench). This script feeds it the d and z
of every ACVP keyGen test case, with k = 2 as FIPS 203 prescribes for ML-KEM-512, and
compares, byte for byte, what the RTL leaves in its key memories with the expected
outputs of NIST:
  * ekPKE = ByteEncode12(t_hat) || rho   (the 800-byte encapsulation key)
  * dkPKE = ByteEncode12(s_hat)          (the first 768 bytes of the decapsulation key)
  * z                                    (the implicit-rejection secret, bytes 1600..1631 of dk)
The remaining 32 bytes of dk are H(ek), a hash of the already compared ek.

The testbench is not modified: a copy of sim/tb/tb_trustedge_spi.sv is made in a
temporary folder, and an ACVP loop, guarded by `ifdef CAC_ACVP_KEYGEN, is inserted after the
testbench's own K-PKE self-test. The copy reads the private key memories through
hierarchical references, exactly as the existing testbench oracles do; nothing leaves the
simulated chip through a new port.
A negative control repeats case 0 with k = 3, which must not reproduce the NIST key.
usage: python3 scripts/acvp_rtl_keygen.py [fpga|asic] [number of test cases, default all 25]
SPDX-License-Identifier: Apache-2.0
"""
from __future__ import annotations

import json
import os
import pathlib
import re
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
CFG = sys.argv[1] if len(sys.argv) > 1 else "fpga"
VEC = json.loads((ROOT / "golden/acvp/mlkem512_keygen.json").read_text())
N = int(sys.argv[2]) if len(sys.argv) > 2 else len(VEC)
OUT = ROOT / "results/acvp_rtl"

DECL = """
`ifdef CAC_ACVP_KEYGEN
`ifdef TRUSTEDGE_ASIC_SRAM
`define CAC_DKPKE_PAIR(_idx) dut.u_mlkem512_kpke_partial.u_matrix_mac.u_dkpke_pair_sram.u_model.mem[_idx]
`else
`define CAC_DKPKE_PAIR(_idx) dut.u_mlkem512_kpke_partial.u_matrix_mac.dkpke_pair_ram[_idx]
`endif
`define CAC_RHO(_idx) dut.u_mlkem512_kpke_partial.u_matrix_mac.rho_ram[_idx]
    reg [255:0] acvp_d [0:__N__-1];
    reg [255:0] acvp_z [0:__N__-1];
    reg [7:0]   acvp_ek [0:__N__*800-1];
    reg [7:0]   acvp_dkpke [0:__N__*768-1];
    integer acvp_t, acvp_b, acvp_idx, acvp_ek_bad, acvp_dk_bad, acvp_rho_bad, acvp_z_bad, acvp_pass;
    reg [23:0] acvp_word;
`endif
"""

LOOP = """
`ifdef CAC_ACVP_KEYGEN
        // NIST ACVP keyGen: d || z || k with k = 2 (FIPS 203, ML-KEM-512), byte-exact comparison
        $readmemh("acvp_d.hex", acvp_d);
        $readmemh("acvp_z.hex", acvp_z);
        $readmemh("acvp_ek.hex", acvp_ek);
        $readmemh("acvp_dkpke.hex", acvp_dkpke);
        acvp_pass = 0;
        for (acvp_t = 0; acvp_t < __N__; acvp_t = acvp_t + 1) begin
            spi_xfer_mlkem_runtime_seed(16'd65, acvp_d[acvp_t], acvp_z[acvp_t], 8'h02,
                mlkem_runtime_response_valid, mlkem_stage_ok, mlkem_stage_status,
                mlkem_stage_digest_a, mlkem_stage_digest_b, mlkem_stage_cycles);
            acvp_ek_bad = 0; acvp_dk_bad = 0; acvp_rho_bad = 0; acvp_z_bad = 0;
            for (acvp_b = 0; acvp_b < 768; acvp_b = acvp_b + 1) begin
                acvp_idx = (acvp_b / 384) * 128 + (acvp_b % 384) / 3;
                acvp_word = `TB_SPI_EKPKE_PAIR(acvp_idx);
                if (acvp_word[(acvp_b % 3)*8 +: 8] !== acvp_ek[acvp_t*800 + acvp_b]) acvp_ek_bad = acvp_ek_bad + 1;
                acvp_word = `CAC_DKPKE_PAIR(acvp_idx);
                if (acvp_word[(acvp_b % 3)*8 +: 8] !== acvp_dkpke[acvp_t*768 + acvp_b]) acvp_dk_bad = acvp_dk_bad + 1;
            end
            for (acvp_b = 0; acvp_b < 32; acvp_b = acvp_b + 1) begin
                if (`CAC_RHO(acvp_b) !== acvp_ek[acvp_t*800 + 768 + acvp_b]) acvp_rho_bad = acvp_rho_bad + 1;
                if (dut.mlkem512_runtime_z[acvp_b*8 +: 8] !== acvp_z[acvp_t][acvp_b*8 +: 8]) acvp_z_bad = acvp_z_bad + 1;
            end
            if (mlkem_runtime_response_valid && mlkem_stage_ok && mlkem_stage_status === 8'hFF &&
                acvp_ek_bad == 0 && acvp_dk_bad == 0 && acvp_rho_bad == 0 && acvp_z_bad == 0)
                acvp_pass = acvp_pass + 1;
            $display("ACVP_KEYGEN case=%0d ok=%b status=%02h ekpke_t_bytes_diff=%0d rho_bytes_diff=%0d dkpke_bytes_diff=%0d z_bytes_diff=%0d cycles=%0d",
                     acvp_t, mlkem_stage_ok, mlkem_stage_status, acvp_ek_bad, acvp_rho_bad, acvp_dk_bad, acvp_z_bad,
                     mlkem_stage_cycles);
        end
        $display("ACVP_KEYGEN_RESULT pass=%0d of %0d", acvp_pass, __N__);
        // negative control: case 0 again with k = 3 instead of 2 must not reproduce the NIST key
        spi_xfer_mlkem_runtime_seed(16'd65, acvp_d[0], acvp_z[0], 8'h03,
            mlkem_runtime_response_valid, mlkem_stage_ok, mlkem_stage_status,
            mlkem_stage_digest_a, mlkem_stage_digest_b, mlkem_stage_cycles);
        acvp_ek_bad = 0;
        for (acvp_b = 0; acvp_b < 768; acvp_b = acvp_b + 1) begin
            acvp_word = `TB_SPI_EKPKE_PAIR((acvp_b / 384) * 128 + (acvp_b % 384) / 3);
            if (acvp_word[(acvp_b % 3)*8 +: 8] !== acvp_ek[acvp_b]) acvp_ek_bad = acvp_ek_bad + 1;
        end
        $display("ACVP_KEYGEN_CONTROL k=3 ekpke_t_bytes_diff=%0d", acvp_ek_bad);
        $finish;
`endif
"""


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    x = bytes.fromhex
    with tempfile.TemporaryDirectory() as tmp:
        tmp = pathlib.Path(tmp)
        vec = VEC[:N]
        (tmp / "acvp_d.hex").write_text("".join(f"{int.from_bytes(x(t['d']), 'little'):064x}\n" for t in vec))
        (tmp / "acvp_z.hex").write_text("".join(f"{int.from_bytes(x(t['z']), 'little'):064x}\n" for t in vec))
        (tmp / "acvp_ek.hex").write_text("".join(f"{b:02x}\n" for t in vec for b in x(t["ek"])))
        (tmp / "acvp_dkpke.hex").write_text("".join(f"{b:02x}\n" for t in vec for b in x(t["dk"])[:768]))
        # consistency of the ACVP data with the layout compared above: dk = dkPKE || ek || H(ek) || z
        for t in vec:
            dk, ek = x(t["dk"]), x(t["ek"])
            assert dk[768:1568] == ek and dk[1600:1632] == x(t["z"]), t["tcId"]
        tb_src = (ROOT / "hskem_rtl/sim/tb/tb_trustedge_spi.sv").read_text()
        anchor_decl, anchor_loop = "    initial begin", "        // Test 1e1/1e2"
        assert tb_src.count(anchor_decl) == 1 and tb_src.count(anchor_loop) == 1
        tb = tb_src.replace(anchor_decl, DECL.replace("__N__", str(N)) + anchor_decl)
        tb = tb.replace(anchor_loop, LOOP.replace("__N__", str(N)) + anchor_loop)
        (tmp / "tb_acvp_keygen.sv").write_text(tb)
        env = dict(os.environ, CAC_TB=str(tmp / "tb_acvp_keygen.sv"), CAC_EXTRA_DEFS="-DCAC_ACVP_KEYGEN",
                   CAC_SIM_TAG="_acvp_keygen", CAC_RUN_DIR=str(tmp))
        subprocess.run(["bash", str(ROOT / "scripts/run_system_sim.sh"), CFG], env=env, check=True)
        log = (ROOT / f"results/system_sim/tb_trustedge_spi_{CFG}_acvp_keygen.log")
        text = log.read_text()
    cases = [dict((k, int(v, 16) if k == "status" else int(v)) for k, v in re.findall(r"(\w+)=(\w+)", line)
                  if k != "ok") for line in text.splitlines() if line.startswith("ACVP_KEYGEN case=")]
    res = re.search(r"ACVP_KEYGEN_RESULT pass=(\d+) of (\d+)", text)
    ctrl = re.search(r"ACVP_KEYGEN_CONTROL k=3 ekpke_t_bytes_diff=(\d+)", text)
    assert ctrl and int(ctrl[1]) > 0, "negative control reproduced the NIST key: the comparison is not effective"
    summary = {"source": "golden/acvp/mlkem512_keygen.json (NIST ACVP-Server, ML-KEM-512 keyGen)",
               "config": CFG, "seed_k": 2, "cases": len(cases),
               "passed": int(res[1]) if res else 0,
               "negative_control": {"seed_k": 3, "ekpke_t_bytes_diff_vs_case_0": int(ctrl[1])},
               "details": cases}
    (OUT / f"keygen_{CFG}.json").write_text(json.dumps(summary, indent=2) + "\n")
    log.replace(OUT / f"keygen_{CFG}.log")
    print(f"ACVP keyGen through the {CFG} RTL: {summary['passed']} of {N} test cases byte-exact")


if __name__ == "__main__":
    main()
