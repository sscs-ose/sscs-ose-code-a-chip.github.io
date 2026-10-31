# Digital blocks: RTL -> GDS with open-source tools, then the same checks as for the saved (commercial) layout
#   digital_oss/run_block.sh <block>: Yosys synthesis -> OpenROAD floorplan with the saved block's outline, pins and power grid
#   -> placement -> routing (metal 1-3) -> GDS (KLayout) -> Magic DRC -> Magic extraction + Netgen LVS -> gate-level simulation (Icarus)
#   -> check that outline, pin names, pin shapes and the netlist port order are the same as the saved block (so the chip netlist and placement do not change).
# A block that passes everything replaces the saved GDS, netlist, DEF and gate-level Verilog; sections 9-12 then place, route and check the chip with it
#   (place/mk_lef.py reads pins and outline from the DEF, net/mk_top.py reads port directions from the Verilog).
import re
DOSS, DOUT = EP / 'digital_oss', WORK / 'digital_oss'
DIG = {   # block -> saved files that sections 9-12 read: GDS (LEF/placement), CDL (chip netlist), DEF (LEF pins and outline), gate-level Verilog (port directions)
    'glob_dig': dict(gds=L / 'blk_digital/out/glob_dig_lbl.gds', cdl=L / 'blk_digital/out/glob_dig.cdl',
                     deff=[L / 'blk_digital/out/glob_dig_pnr.def'], v=[L / 'blk_digital/out/glob_dig_pnr.v']),
    'data_blk': dict(gds=LT / 'place/data_blk_repin/out/data_blk_lbl.gds', cdl=L / 'blk_digital/out/data_blk.cdl',
                     deff=[LT / 'place/data_blk_repin/out/data_blk_pnr.def'],
                     v=[L / 'blk_digital/out/data_blk_pnr.v', LT / 'place/data_blk_repin/out/data_blk_pnr.v']),
    'col_blk': dict(gds=EP / 'digital/col_blk/out/col_blk/col_blk_lbl.gds', cdl=EP / 'digital/col_blk/out/col_blk/col_blk.cdl',
                    deff=[EP / 'digital/col_blk/out/col_blk/col_blk_pnr.def'], v=[EP / 'digital/col_blk/out/col_blk/col_blk_pnr.v']),
    'row_blk': dict(gds=EP / 'digital/row_blk/out/row_blk/row_blk_lbl.gds', cdl=EP / 'digital/row_blk/out/row_blk/row_blk.cdl',
                    deff=[EP / 'digital/row_blk/out/row_blk/row_blk_pnr.def'], v=[EP / 'digital/row_blk/out/row_blk/row_blk_pnr.v']),
}
def def_for_lef(src, dst):
    # Same DEF, written the way place/mk_lef.py reads it: each "- " entry at the start of the line, no "+ PORT" line
    # (OpenROAD writes "+ PORT" even for a pin with one shape; mk_lef.py takes pins with exactly one shape).
    t = re.sub(r'^\s+- ', '- ', Path(src).read_text(), flags=re.M)
    a, z = t.index('\nPINS '), t.index('END PINS')
    pins = re.split(r'(?m)^(?=- )', t[a:z])
    assert all(p.count('+ PORT') <= 1 and len(re.findall(r'\+ LAYER ', p)) <= 1 for p in pins), f'{src}: pin with more than one shape'
    Path(dst).write_text(t[:a] + re.sub(r'(?m)^\s*\+ PORT\s*\n', '', t[a:z]) + t[z:])


DIG_OSS = []
for b, D in DIG.items():
    with step(f'digital block {b} (Yosys + OpenROAD)', 'layout') as r:
        sh(f'NJ={NJ} PY={PY} bash run_block.sh {b} {DOUT}', cwd=DOSS, tail=4)
        s = json.loads((DOUT / b / 'summary.json').read_text())
        rules = ', '.join(f'{k} {v}' for k, v in (s['drc_rules'] or {}).items())
        r['note'] = (f"{s['cells']} cells incl. macros, {s['cell_area_um2']:.0f} um2; outline and pins same as saved: {s['same_as_saved']}; "
                     f"route violations {s['drt_violations']}; Magic DRC {s['drc_total']}{' (' + rules + '; same rules as the saved layout)' if rules else ''}; "
                     f"LVS: {s['lvs']}; gate sim {'PASS' if s['gate_sim'] else 'FAIL'}")
        r['ok'] = bool(s['same_as_saved'] and s['drt_violations'] == 0 and s['drc_ok'] and s['lvs_ok'] and s['gate_sim'])
        if r['ok']:     # keep the saved files once (if present), then put the open-source result in their place
            new = [(DOUT / b / f'{b}.gds', [D['gds']]), (DOUT / b / f'{b}.cdl', [D['cdl']]),
                   (DOUT / b / f'{b}.def', D['deff']), (DOUT / b / f'{b}_pnr.v', D['v'])]
            for src, dsts in new:
                for f in dsts:
                    if f.exists() and not (REF / f.name).exists():
                        shutil.copy2(f, REF / f.name)
                    f.parent.mkdir(parents=True, exist_ok=True)
                    def_for_lef(src, f) if f.suffix == '.def' else shutil.copy2(src, f)
            DIG_OSS.append(b)
print('Digital blocks from open-source RTL-to-GDS (used in the chip):', DIG_OSS)
print('Saved GDS used as is (digital blocks):', [b for b in ('row_blk', 'col_blk', 'data_blk', 'glob_dig') if b not in DIG_OSS])
with step('figure: digital block GDS (open-source)', 'layout'):
    F.gds_grid([(DOUT / b / f'{b}.gds', b, t) for b, t in (('row_blk', 'Row control + row switches'), ('col_blk', 'Column control + column switches + clamps'),
                                                          ('data_blk', 'DATA block'), ('glob_dig', 'Global control'))
                if (DOUT / b / f'{b}.gds').exists()],
               LYP, 'digital_oss', 'Digital blocks from RTL with open-source tools')
