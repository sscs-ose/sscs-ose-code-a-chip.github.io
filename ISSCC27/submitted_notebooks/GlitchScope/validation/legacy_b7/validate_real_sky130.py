from __future__ import annotations
import argparse,csv,json,hashlib
from collections import Counter
from pathlib import Path
from glitchscope.liberty import parse_liberty_file, LibertyDelayProvider, bilinear
from glitchscope.model import Cell, ps_to_fs

EXPECTED_CELL_COUNT = 428
EXPECTED_COMB_ARC_COUNT = 1178
EXPECTED_SENSE_COUNTS = {
    'negative_unate': 561,
    'positive_unate': 617,
}
EXPECTED_CONDITIONAL_COMB_ARCS = 0

def find_cell(lib, exact, fallback_token):
    if exact in lib.cells:
        return exact
    xs=[n for n in lib.cells if fallback_token in n.lower()]
    if not xs:
        raise AssertionError('No real-library cell matching '+fallback_token)
    return sorted(xs)[0]

def sole_output(cell):
    outs=sorted({a.output_pin for a in cell.timing_arcs})
    if len(outs)!=1:
        raise AssertionError('Expected one timed output for '+cell.name+', got '+str(outs))
    return outs[0]

def require_cell_shape(lib, name, output_pin, related_pins, arc_count, sense_counts):
    lc=lib.cells[name]
    got_output=sole_output(lc)
    got_related=sorted({a.related_pin for a in lc.timing_arcs})
    got_arc_count=len(lc.timing_arcs)
    got_senses=dict(sorted(Counter(a.timing_sense for a in lc.timing_arcs).items()))
    exp_senses=dict(sorted(sense_counts.items()))
    if got_output != output_pin:
        raise AssertionError(f'{name}: output mismatch expected={output_pin} got={got_output}')
    if got_related != sorted(related_pins):
        raise AssertionError(f'{name}: related-pin mismatch expected={sorted(related_pins)} got={got_related}')
    if got_arc_count != arc_count:
        raise AssertionError(f'{name}: arc-count mismatch expected={arc_count} got={got_arc_count}')
    if got_senses != exp_senses:
        raise AssertionError(f'{name}: timing-sense mismatch expected={exp_senses} got={got_senses}')

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--lib',required=True)
    ap.add_argument('--out',required=True)
    a=ap.parse_args()
    out=Path(a.out)
    out.mkdir(parents=True,exist_ok=True)

    lib=parse_liberty_file(a.lib)
    sense_counts=Counter(
        arc.timing_sense for c in lib.cells.values() for arc in c.timing_arcs
    )
    senses=sorted(sense_counts)
    total_arcs=sum(len(c.timing_arcs) for c in lib.cells.values())
    conditional=sum(
        1 for c in lib.cells.values() for arc in c.timing_arcs if arc.when
    )

    # B1D1 established the exact propagation authority for the frozen
    # SKY130HD TT/25C/1.80V Liberty. non_unate is present only in raw
    # non-combinational timing blocks for this authority.
    if len(lib.cells) != EXPECTED_CELL_COUNT:
        raise AssertionError(
            f'Real SKY130 cell-count mismatch expected={EXPECTED_CELL_COUNT} got={len(lib.cells)}'
        )
    if total_arcs != EXPECTED_COMB_ARC_COUNT:
        raise AssertionError(
            f'Real SKY130 combinational-arc mismatch expected={EXPECTED_COMB_ARC_COUNT} got={total_arcs}'
        )

    got_sense_counts=dict(sorted(sense_counts.items()))
    exp_sense_counts=dict(sorted(EXPECTED_SENSE_COUNTS.items()))
    if got_sense_counts != exp_sense_counts:
        raise AssertionError(
            f'Real SKY130 propagation timing-sense authority mismatch '
            f'expected={exp_sense_counts} got={got_sense_counts}'
        )

    if conditional != EXPECTED_CONDITIONAL_COMB_ARCS:
        raise AssertionError(
            f'Real SKY130 conditional combinational-arc mismatch '
            f'expected={EXPECTED_CONDITIONAL_COMB_ARCS} got={conditional}'
        )

    names={
      'inv':find_cell(lib,'sky130_fd_sc_hd__inv_1','__inv_'),
      'buf':find_cell(lib,'sky130_fd_sc_hd__buf_1','__buf_'),
      'nand2':find_cell(lib,'sky130_fd_sc_hd__nand2_1','__nand2_'),
      'nor2':find_cell(lib,'sky130_fd_sc_hd__nor2_1','__nor2_'),
      'xor2':find_cell(lib,'sky130_fd_sc_hd__xor2_1','__xor2_'),
      'xnor2':find_cell(lib,'sky130_fd_sc_hd__xnor2_1','__xnor2_'),
    }

    require_cell_shape(lib,names['inv'],'Y',['A'],1,{'negative_unate':1})
    require_cell_shape(lib,names['buf'],'X',['A'],1,{'positive_unate':1})
    require_cell_shape(lib,names['nand2'],'Y',['A','B'],2,{'negative_unate':2})
    require_cell_shape(lib,names['nor2'],'Y',['A','B'],2,{'negative_unate':2})
    require_cell_shape(
        lib,names['xor2'],'X',['A','B'],4,
        {'negative_unate':2,'positive_unate':2}
    )
    require_cell_shape(
        lib,names['xnor2'],'Y',['A','B'],4,
        {'negative_unate':2,'positive_unate':2}
    )

    rows=[]
    for role,name in names.items():
        lc=lib.cells[name]
        outpin=sole_output(lc)
        related=sorted({x.related_pin for x in lc.timing_arcs})
        row_senses=Counter(x.timing_sense for x in lc.timing_arcs)
        rows.append([
            role,name,outpin,';'.join(related),len(lc.timing_arcs),
            ';'.join(f'{k}:{v}' for k,v in sorted(row_senses.items()))
        ])

    inv=lib.cells[names['inv']]
    outpin=sole_output(inv)
    arcs=[x for x in inv.timing_arcs if x.related_pin=='A' and not x.when]
    if len(arcs)!=1:
        raise AssertionError('Expected one unconditional INV A arc, got '+str(len(arcs)))
    arc=arcs[0]
    x=arc.cell_fall.index_1[0]
    y=arc.cell_fall.index_2[0]
    slew_fs=ps_to_fs(x*lib.time_unit_ps)
    load_ff=y*lib.capacitance_unit_ff
    cell=Cell(
        'U_INV','INV',{'A':'A'},'Y',0,0,
        library_cell=names['inv'],library_output_pin=outpin
    )
    q=LibertyDelayProvider(lib).delay(
        cell,0,input_slew_fs=slew_fs,load_ff=load_ff,
        related_pin='A',pin_values={'A':1},input_transition=(0,1)
    )
    expected=ps_to_fs(bilinear(arc.cell_fall,x,y)*lib.time_unit_ps)
    if q.delay_fs!=expected:
        raise AssertionError('Real INV provider/table mismatch')

    with (out/'representative_cells.csv').open('w',newline='') as f:
        w=csv.writer(f)
        w.writerow([
            'role','cell','output_pin','related_pins',
            'combinational_arc_count','timing_sense_counts'
        ])
        w.writerows(rows)

    summary={
      'status':'PASS',
      'source_path':str(Path(a.lib)),
      'source_sha256':hashlib.sha256(Path(a.lib).read_bytes()).hexdigest(),
      'cell_count':len(lib.cells),
      'combinational_arc_count':total_arcs,
      'conditional_combinational_arc_count':conditional,
      'timing_sense_counts':dict(sorted(sense_counts.items())),
      'timing_senses':senses,
      'representative_cells':names,
      'real_inv_probe_delay_fs':q.delay_fs,
      'real_inv_probe_slew_fs':q.output_slew_fs,
      'index_3_supported':False,
      'sequential_timing_used':False,
      'internal_power_used':False,
      'b1h1_validator_diagnosis':
          'B1D1 proved non_unate timing blocks are non-combinational in the '
          'frozen real Liberty; propagation authority is exactly '
          '561 negative_unate + 617 positive_unate',
    }
    (out/'real_sky130_b1_summary.json').write_text(
        json.dumps(summary,indent=2,sort_keys=True)
    )

    print('REAL_SKY130_CELL_COUNT='+str(len(lib.cells)))
    print('REAL_SKY130_COMBINATIONAL_ARC_COUNT='+str(total_arcs))
    print('REAL_SKY130_CONDITIONAL_COMB_ARC_COUNT='+str(conditional))
    print(
        'REAL_SKY130_TIMING_SENSE_COUNTS='+
        json.dumps(dict(sorted(sense_counts.items())),sort_keys=True)
    )
    print('REAL_SKY130_NON_UNATE_PROP_ARCS=0')
    for row in rows:
        print(
            'REAL_CELL_'+row[0].upper()+'='+row[1]+
            ' OUT='+row[2]+' PINS='+row[3]+
            ' ARCS='+str(row[4])+' SENSES='+row[5]
        )
    print('REAL_INV_PROBE_DELAY_FS='+str(q.delay_fs))
    print('B1H1_REAL_SKY130_PROPAGATION_AUTHORITY_PASS')
    print('GLITCHSCOPE_PHASE_B1_REAL_SKY130_PARSE_PASS')

if __name__=='__main__':
    main()
