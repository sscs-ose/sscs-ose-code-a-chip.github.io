"""
Generate synthesizable Verilog from a FixedPointConfig + coefficient set.

One template (`src/verilog/fir_symmetric.v.j2`) serves both precision modes:

  * uniform     -- `bit_widths=None`, every unique coefficient gets
                   `cfg.coeff_total_bits` bits
  * per-tap     -- `bit_widths=array`, one total width per unique coefficient
                   (folded pairs first, center tap last), which is what the
                   sensitivity-guided search produces

Keeping a single template (the guide's section 5.3 recommendation) means the
arithmetic, rounding and saturation behaviour cannot silently drift between
the uniform and non-uniform paths -- the only thing that changes is how many
bits each constant multiplier is given.
"""
from pathlib import Path

import numpy as np
from jinja2 import Environment, FileSystemLoader

import paths
from fixedpoint import FixedPointConfig, quantize_coeffs_per_tap

TEMPLATE_DIR = str(paths.VERILOG_DIR)
OUTPUT_DIR = paths.RTL_DIR
UNIFORM_TEMPLATE = "fir_symmetric.v.j2"
NONUNIFORM_TEMPLATE = "fir_nonuniform.v.j2"


def _hex_pattern(value: int, width: int) -> str:
    """Exact `width`-bit two's-complement hex pattern (sized literal source)."""
    mask = (1 << width) - 1
    digits = (width + 3) // 4
    return format(int(value) & mask, f"0{digits}x")


def _sign_pad_expr(src: str, src_width: int, shift: int, term_width: int) -> str:
    """
    Pad a product at the LSB by `shift` zeros (binary-point alignment) and put
    the result in a `term_width`-bit signed wire, sign-extending as needed.
    """
    sign_pad = term_width - src_width - shift
    assert sign_pad >= 0, \
        f"term_width {term_width} too small for {src} ({src_width} bits) + {shift} shift"
    parts = []
    if sign_pad == 1:
        parts.append(f"{src}[{src_width - 1}]")
    elif sign_pad > 1:
        parts.append(f"{{{sign_pad}{{{src}[{src_width - 1}]}}}}")
    parts.append(src)
    if shift > 0:
        parts.append(f"{{{shift}{{1'b0}}}}")
    return src if len(parts) == 1 else "{" + ", ".join(parts) + "}"


def _sext_expr(src: str, src_width: int, dst_width: int) -> str:
    """Explicit sign extension of a named wire from src_width to dst_width bits."""
    pad = dst_width - src_width
    assert pad >= 0, f"cannot sign-extend {src} ({src_width}) to {dst_width} bits"
    if pad == 0:
        return src
    if pad == 1:
        return "{" + f"{src}[{src_width - 1}], {src}" + "}"
    return "{" + f"{{{pad}{{{src}[{src_width - 1}]}}}}, {src}" + "}"


def build_context(h_float: np.ndarray, cfg: FixedPointConfig, config_name: str,
                  module_name: str = None, bit_widths=None) -> dict:
    """Compute every width/constant the template needs, and return the context."""
    n_taps = len(h_float)
    assert n_taps % 2 == 1, "this template assumes odd tap count for a center tap"
    assert np.allclose(h_float, h_float[::-1]), "coefficients must be symmetric"

    n_pairs = n_taps // 2
    center_index = n_pairs

    if bit_widths is None:
        bit_widths = np.full(n_pairs + 1, cfg.coeff_total_bits, dtype=int)
    bit_widths = np.asarray(bit_widths, dtype=int)
    assert len(bit_widths) == n_pairs + 1, \
        f"expected {n_pairs + 1} per-tap widths, got {len(bit_widths)}"
    frac_bits_per_tap = bit_widths - cfg.coeff_int_bits
    assert np.all(frac_bits_per_tap >= 0), "coefficient width below coeff_int_bits"
    F = int(frac_bits_per_tap.max())

    # quantize each unique coefficient with its own width
    full = quantize_coeffs_per_tap(h_float, cfg, frac_bits_per_tap)
    coeffs_unique = np.array(
        [int(full[i]) for i in range(n_pairs)] + [int(full[center_index])],
        dtype=np.int64)

    fold_width = cfg.input_total_bits + 1
    prod_widths_pairs = [fold_width + int(w) for w in bit_widths[:n_pairs]]
    prod_width_center = cfg.input_total_bits + int(bit_widths[n_pairs])

    # after binary-point alignment every term has this width (see fixedpoint.py)
    term_width = cfg.input_total_bits + 1 + cfg.coeff_int_bits + F
    term_shift_bits = [F - int(f) for f in frac_bits_per_tap]

    term_exprs = [
        _sign_pad_expr(f"prod{i}", prod_widths_pairs[i], term_shift_bits[i], term_width)
        for i in range(n_pairs)
    ]
    term_exprs.append(
        _sign_pad_expr("prod_center", prod_width_center, term_shift_bits[n_pairs], term_width))

    acc_bits = cfg.acc_total_bits_for_frac(F, n_taps)
    acc_frac_bits = cfg.input_frac_bits + F
    shift = acc_frac_bits - cfg.output_frac_bits
    if shift < 0:
        raise ValueError("output_frac_bits must be <= input_frac_bits + max coeff frac bits")

    acc_sum_expr = " + ".join(
        _sext_expr(f"term{i}", term_width, acc_bits) for i in range(len(term_exprs)))

    shifted_width = acc_bits + 1 - shift
    if shifted_width < cfg.output_total_bits:
        raise ValueError(
            f"requantized width {shifted_width} < output width {cfg.output_total_bits}; "
            "increase acc_guard_bits")

    round_const = (1 << (shift - 1)) if (cfg.rounding == "round" and shift > 0) else 0
    out_max = (1 << (cfg.output_total_bits - 1)) - 1
    out_min = -(1 << (cfg.output_total_bits - 1))

    module_name = module_name or f"fir_{config_name}"
    return dict(
        config_name=config_name,
        module_name=module_name,
        n_taps=n_taps, n_pairs=n_pairs, center_index=center_index,
        coeffs_unique=[int(c) for c in coeffs_unique],
        coeff_hex=[_hex_pattern(int(c), int(w))
                   for c, w in zip(coeffs_unique, bit_widths)],
        coeff_widths=[int(w) for w in bit_widths],
        coeff_frac_bits_max=F,
        coeff_int_bits=cfg.coeff_int_bits,
        fold_width=fold_width,
        prod_widths_pairs=prod_widths_pairs,
        prod_width_center=prod_width_center,
        term_width=term_width,
        term_shift_bits=term_shift_bits,
        term_exprs=term_exprs,
        acc_sum_expr=acc_sum_expr,
        acc_bits=acc_bits,
        acc_frac_bits=acc_frac_bits,
        shift=shift,
        shifted_width=shifted_width,
        round_const_hex=_hex_pattern(round_const, acc_bits + 1),
        out_max_hex=_hex_pattern(out_max, shifted_width),
        out_min_hex=_hex_pattern(out_min, shifted_width),
        input_total_bits=cfg.input_total_bits,
        input_int_bits=cfg.input_int_bits,
        input_frac_bits=cfg.input_frac_bits,
        output_total_bits=cfg.output_total_bits,
        output_int_bits=cfg.output_int_bits,
        output_frac_bits=cfg.output_frac_bits,
        rounding=cfg.rounding,
        saturate_output=cfg.saturate_output,
        unique_coeff_frac_bits=[int(v) for v in frac_bits_per_tap],
    )


def _render(context: dict, template_name: str, output_dir=None,
            module_name: str = None) -> str:
    module_name = module_name or context["module_name"]
    out_dir = Path(output_dir) if output_dir else OUTPUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    env = Environment(loader=FileSystemLoader(TEMPLATE_DIR),
                      trim_blocks=True, lstrip_blocks=True, keep_trailing_newline=True)
    tmpl = env.get_template(template_name)
    rtl = tmpl.render(**context)

    out_path = out_dir / f"{module_name}.v"
    out_path.write_text(rtl)
    return str(out_path)


def generate_rtl(h_float: np.ndarray, cfg: FixedPointConfig, config_name: str,
                 module_name: str = None, bit_widths=None, output_dir=None,
                 template_name: str = None) -> str:
    """
    Generate one Verilog file. `bit_widths` selects per-tap precision; when it
    is None the uniform template is used with `cfg.coeff_total_bits` per tap.
    Returns the path of the written .v file.
    """
    ctx = build_context(h_float, cfg, config_name, module_name=module_name,
                        bit_widths=bit_widths)
    if template_name is None:
        template_name = UNIFORM_TEMPLATE if bit_widths is None else NONUNIFORM_TEMPLATE
    return _render(ctx, template_name, output_dir=output_dir,
                   module_name=ctx["module_name"])


def generate_rtl_nonuniform(h_float: np.ndarray, cfg: FixedPointConfig,
                            bit_widths, config_name: str, module_name: str = None,
                            output_dir=None) -> str:
    """Sensitivity-guided (per-tap width) RTL generation."""
    return generate_rtl(h_float, cfg, config_name, module_name=module_name,
                        bit_widths=bit_widths, output_dir=output_dir,
                        template_name=NONUNIFORM_TEMPLATE)


if __name__ == "__main__":
    from reference import FILTER_A_SPEC, design_filter

    paths.ensure_dirs()
    h = design_filter(FILTER_A_SPEC)
    cfg = FixedPointConfig(
        coeff_int_bits=2, coeff_frac_bits=10,
        input_int_bits=2, input_frac_bits=14,
        acc_guard_bits=4,
        output_int_bits=2, output_frac_bits=14,
        rounding="round", saturate_output=True,
    )
    path = generate_rtl(h, cfg, config_name="baseline_conservative")
    print(f"Generated: {paths.rel(path)}")

    bits = np.array([6, 7, 8, 9, 10, 11, 12, 12, 12])
    path2 = generate_rtl_nonuniform(h, cfg, bits, config_name="nonuniform_demo")
    print(f"Generated: {paths.rel(path2)}")
