import hashlib
import json
from pathlib import Path
import pya

out=Path(__file__).resolve().parent
root=out.parents[1]
def inventory(path):
    layout=pya.Layout()
    layout.read(str(path))
    result={}
    for cell in layout.each_cell():
        rows=[]
        for li in layout.layer_indices():
            info=layout.get_info(li)
            rows.extend(f'{info.layer}/{info.datatype}:{s.to_s()}' for s in cell.shapes(li).each())
        rows.extend(f'instance:{layout.cell(i.cell_index).name}:{i.cplx_trans}:{i.a}:{i.b}:{i.na}:{i.nb}' for i in cell.each_inst())
        result[cell.name]=hashlib.sha256('\n'.join(sorted(rows)).encode()).hexdigest()
    return layout.dbu,result

first,old=inventory(root/'build/pnr/results/6_final.gds')
second,new=inventory(out/'nebula_cpu_npu_top.gds')
mismatches=sorted(k for k in old.keys()|new.keys() if old.get(k)!=new.get(k))
report=dict(status='passed' if first==second and not mismatches else 'failed',dbu_um=second,
            algorithm='Per-cell sorted layer/datatype/shape and child-name/placement inventory SHA256; stream timestamps ignored.',
            cells_compared=len(new),mismatched_cells=mismatches,cell_sha256=new,
            upstream_gds='build/pnr/results/6_final.gds',exported_gds='build/gds/nebula_cpu_npu_top.gds')
(out/'geometry_comparison.json').write_text(json.dumps(report,indent=2)+'\n')
assert report['status']=='passed',mismatches
print('SAME_SNAPSHOT_GDS_GEOMETRY_PASS',len(new))
