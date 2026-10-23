"""Byte-exact check of ML-KEM-512 encapsulation and decapsulation on the RTL of the signed-off chip (HSKEM-2 revision B).

For each case t a copy of the full-system testbench runs, over SPI:
  1. deterministic key generation with (d_t, z_t) of the NIST ACVP ML-KEM-512 keyGen vector t (opcode 0x14, k = 2),
  2. FIPS 203 encapsulation with the message m_t of the NIST ACVP encapsulation vector t (opcode 0x16, 32 bytes),
  3. decapsulation of the ciphertext just produced (opcode 0x18),
  4. decapsulation again after the decoded v coefficient 512 was moved by q/2 (the testbench's own rejection test),
and prints the 768-byte ciphertext and the 256-bit shared-key register after steps 2-4. This script compares them, byte for
byte, with golden/mlkem_full.py (which itself reproduces all 25/25/10 ACVP keyGen/encaps/decaps vectors):
  c == Encaps(ek_t, m_t).c, K_enc == Encaps(ek_t, m_t).K, K_dec == K_enc, K_rej == J(z_t || c).
Run by scripts/acvp_rtl_encdec.sh.
usage: python3 acvp_rtl_encdec.py prepare <dir> [N] | patch <tb_trustedge_spi.sv> <N> | check <dir> <sim log> <out.json> [N]
SPDX-License-Identifier: Apache-2.0
"""
import json, pathlib, re, sys
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'golden'))
import mlkem_full as M  # noqa: E402

A = ROOT / 'golden/acvp'
KG = json.loads((A / 'mlkem512_keygen.json').read_text())
ED = json.loads((A / 'mlkem512_encapdecap.json').read_text())['encapsulation']


def expected(n):
    out = []
    for t in range(n):
        d, z, m = bytes.fromhex(KG[t]['d']), bytes.fromhex(KG[t]['z']), bytes.fromhex(ED[t]['m'])
        ek, dk = M.keygen_internal(d, z)
        assert ek == bytes.fromhex(KG[t]['ek'])
        K, c = M.encaps_internal(ek, m)
        out.append(dict(d=d, z=z, m=m, c=c, K=K, J=M.J(z + c)))
    return out


def le(b):
    return f"{int.from_bytes(b, 'little'):064x}\n"


def prepare(folder, n):
    folder = pathlib.Path(folder); folder.mkdir(parents=True, exist_ok=True)
    ex = expected(n)
    (folder / 'encdec_d.hex').write_text(''.join(le(e['d']) for e in ex))
    (folder / 'encdec_z.hex').write_text(''.join(le(e['z']) for e in ex))
    (folder / 'encdec_m.hex').write_text(''.join(le(e['m']) for e in ex))
    print('prepared', n, 'cases')


def check(folder, log, out, n):
    ex = expected(n)
    text = pathlib.Path(log).read_text(errors='ignore')
    rows = {}
    for m in re.finditer(r'^ENCDEC (\w+) t=(\d+) ok=(\w) status=(\w+) (?:c=([0-9a-fx]+) )?k=([0-9a-fx]+)', text, re.M):
        rows[(m[1], int(m[2]))] = dict(ok=m[3], status=m[4], c=m[5], k=m[6])
    res, npass = [], 0
    for t, e in enumerate(ex):
        r_enc, r_dec, r_rej = rows.get(('enc', t)), rows.get(('dec', t)), rows.get(('rej', t))
        if not (r_enc and r_dec and r_rej):
            res.append(dict(case=t, missing=True)); continue
        c_rtl = bytes.fromhex(r_enc['c'])                    # printed byte 0 first
        def kb(h):                                            # register bit [8b+7:8b] = byte b
            return int(h, 16).to_bytes(32, 'little') if 'x' not in h else None
        k_enc, k_dec, k_rej = kb(r_enc['k']), kb(r_dec['k']), kb(r_rej['k'])
        ok = dict(c=c_rtl == e['c'], K_enc=k_enc == e['K'], K_dec=k_dec == e['K'], K_rej=k_rej == e['J'],
                  c_bytes_diff=sum(a != b for a, b in zip(c_rtl, e['c'])) + abs(len(c_rtl) - 768))
        good = ok['c'] and ok['K_enc'] and ok['K_dec'] and ok['K_rej']
        npass += good
        res.append(dict(case=t, **ok))
    summary = dict(source='NIST ACVP ML-KEM-512 keyGen (d, z) and encapsulation (m) vectors; expected outputs from '
                          'golden/mlkem_full.py (ACVP 25/25/10)', design='HSKEM-2 revision B RTL (flow/chip_rev_b/rtl/make_root.sh)',
                   cases=len(ex), passed=npass, details=res)
    out = pathlib.Path(out)
    out.write_text(json.dumps(summary, indent=2) + '\n')
    print(f'ACVP encapsulation/decapsulation on the revision B RTL: {npass} of {len(ex)} cases byte-exact '
          f'(c, K, decapsulated K, implicit-rejection J)')
    for r in res:
        if not all(r.get(k) for k in ('c', 'K_enc', 'K_dec', 'K_rej')): print(' ', r)


DECL = r'''
`ifdef CAC_ACVP_ENCDEC
`ifdef TRUSTEDGE_ASIC_SRAM
`define ED_CT(_i) dut.u_mlkem512_encaps_partial.u_codec.u_ciphertext_sram.u_model.mem[_i]
`else
`define ED_CT(_i) dut.u_mlkem512_encaps_partial.u_codec.ciphertext_ram[_i]
`endif
    reg [255:0] encdec_d [0:__N__-1];
    reg [255:0] encdec_z [0:__N__-1];
    reg [255:0] encdec_m [0:__N__-1];
    integer ed_t, ed_b;
    reg [11:0] ed_saved;
`endif
'''
LOOP = r'''
`ifdef CAC_ACVP_ENCDEC
        $readmemh("encdec_d.hex", encdec_d);
        $readmemh("encdec_z.hex", encdec_z);
        $readmemh("encdec_m.hex", encdec_m);
        for (ed_t = 0; ed_t < __N__; ed_t = ed_t + 1) begin
            spi_xfer_mlkem_runtime_seed(16'd65, encdec_d[ed_t], encdec_z[ed_t], 8'h02,
                mlkem_runtime_response_valid, mlkem_stage_ok, mlkem_stage_status,
                mlkem_stage_digest_a, mlkem_stage_digest_b, mlkem_stage_cycles);
            spi_xfer_mlkem_runtime_encrypt(16'd32, encdec_m[ed_t], 256'd0,
                mlkem_runtime_response_valid, mlkem_stage_ok, mlkem_stage_status,
                mlkem_stage_digest_a, mlkem_stage_digest_b, mlkem_stage_cycles);
            $write("ENCDEC enc t=%0d ok=%b status=%02h c=", ed_t, mlkem_stage_ok, mlkem_stage_status);
            for (ed_b = 0; ed_b < 768; ed_b = ed_b + 1) $write("%02h", `ED_CT(ed_b));
            $display(" k=%064h cycles=%0d", dut.u_mlkem512_decaps_partial.selected_shared_secret, mlkem_stage_cycles);
            spi_xfer_mlkem_stage(8'h18, 8'h19, mlkem_stage_ok, mlkem_stage_status,
                mlkem_stage_digest_a, mlkem_stage_digest_b, mlkem_stage_cycles);
            $display("ENCDEC dec t=%0d ok=%b status=%02h k=%064h cycles=%0d", ed_t, mlkem_stage_ok, mlkem_stage_status,
                dut.u_mlkem512_decaps_partial.selected_shared_secret, mlkem_stage_cycles);
            ed_saved = `TB_SPI_DECODED_COEFF(512);
            `TB_SPI_DECODED_COEFF(512) = ({1'b0, ed_saved} + 13'd1665 >= 13'd3329) ? ed_saved + 12'd1665 - 12'd3329 : ed_saved + 12'd1665;
            spi_xfer_mlkem_stage(8'h18, 8'h19, mlkem_stage_ok, mlkem_stage_status,
                mlkem_stage_digest_a, mlkem_stage_digest_b, mlkem_stage_cycles);
            $display("ENCDEC rej t=%0d ok=%b status=%02h k=%064h cycles=%0d", ed_t, mlkem_stage_ok, mlkem_stage_status,
                dut.u_mlkem512_decaps_partial.selected_shared_secret, mlkem_stage_cycles);
            `TB_SPI_DECODED_COEFF(512) = ed_saved;
        end
        $display("ENCDEC_DONE cases=%0d", __N__);
        $finish;
`endif
'''


def patch_tb(p, n):
    """Insert the case loop into a copy of tb_trustedge_spi.sv (compiled with -DCAC_ACVP_ENCDEC)."""
    s = open(p).read()
    decl = DECL.replace('__N__', n)
    loop = LOOP.replace('__N__', n)
    a, b = '    initial begin', '        // Test 1e1/1e2'
    assert s.count(a) == 1 and s.count(b) == 1
    open(p, 'w').write(s.replace(a, decl + a).replace(b, loop + b))


if __name__ == '__main__':
    if sys.argv[1] == 'prepare':
        prepare(sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 25)
    elif sys.argv[1] == 'patch':
        patch_tb(sys.argv[2], sys.argv[3])
    else:
        check(sys.argv[2], sys.argv[3], sys.argv[4], int(sys.argv[5]) if len(sys.argv) > 5 else 25)
