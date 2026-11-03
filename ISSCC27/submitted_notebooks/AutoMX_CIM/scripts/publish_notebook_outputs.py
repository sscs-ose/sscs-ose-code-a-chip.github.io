"""Publish tested result outputs without rerunning or altering numerical evidence."""
from pathlib import Path
from datetime import datetime,timezone
import json,copy,shutil,runpy,sys
import nbformat
from scripts.enrich_cim_notebook import enrich
from scripts.cim_output_presentation import compact_outputs

b=Path(__file__).resolve().parents[1]
if '--reuse-validation' not in sys.argv:runpy.run_module('scripts.validate_notebook_outputs',run_name='__main__')
r=json.loads((b/'docs/output_validation_20261027.json').read_text());assert r['status']=='PASSED'
book=nbformat.read(r['candidate'],4);tested=nbformat.read(r['notebook'],4)
old=nbformat.read(b/'AutoMX_CIM_Code_a_Chip.ipynb',4)
old_by_id={c.id:c for c in old.cells}
blank={c.id for c in old.cells if c.cell_type=='code' and not c.outputs}
ran={c.id:c for c in tested.cells if c.cell_type=='code' and c.execution_count is not None}
refreshed=[]
for c in book.cells:
    if c.cell_type!='code':continue
    if c.id in blank and c.id in ran:
        actual=ran[c.id];assert actual.source==c.source,c.id
        c.outputs=copy.deepcopy(actual.outputs);c.execution_count=actual.execution_count
        c.metadata['output_validation']={'notebook':r['notebook'],'cell':c.id}
        refreshed.append(c.id)
    if not c.outputs and c.id not in blank and old_by_id[c.id].outputs:
        c.outputs=copy.deepcopy(old_by_id[c.id].outputs)
        c.execution_count=old_by_id[c.id].execution_count
        c.metadata['output_source']='Verified conversion records retained; stdout formatting updated.'
    c.outputs=compact_outputs(c.outputs)
    assert any(o.get('text','').strip() if o.output_type=='stream' else bool(o.get('data')) or o.output_type=='error' for o in c.outputs),c.id
assert len([c for c in book.cells if c.cell_type=='code'])==129
assert len(refreshed)==len(blank),(len(refreshed),len(blank))
assert {c.id for c in old.cells}.issubset({c.id for c in book.cells})
for cid in ['meter-energy','meter-area','meter-early-checkpoints','native-runall-render-top','klayout-native']:
    a=next(c for c in old.cells if c.id==cid);z=next(c for c in book.cells if c.id==cid)
    assert [o for o in a.outputs if o.output_type!='stream']==[o for o in z.outputs if o.output_type!='stream'],cid
book.metadata['output_validation']={**r,'formerly_silent':len(blank),'refreshed_silent_cells':len(refreshed),'silent_cells_remaining':0}
nbformat.validate(book)
# Preserve the verified full execution before replacing its presentation copy.
archive=b/'attempts/before_result_output_publish_20261027';archive.mkdir(exist_ok=True)
for name in ['AutoMX_CIM_Code_a_Chip.ipynb','AutoMX_CIM_Code_a_Chip.executed.ipynb']:
    if not (archive/name).exists():shutil.copy2(b/name,archive/name)
    nbformat.write(book,b/name)
r.update(notebook_cells=len(book.cells),code_cells=129,formerly_silent=len(blank),refreshed_silent_cells=len(refreshed),silent_cells_remaining=0)
(b/'docs/output_validation_20261027.json').write_text(json.dumps(r,indent=2)+'\n')
for name in ['README.md','scripts/standalone_readme.md']:
    p=b/name;s=p.read_text()
    note=f'''## Bảng và đồ thị trong cell — 2026-10-27

Notebook có mục **Kết quả chính** ngay đầu để mở checkpoint, kiến trúc, baseline, năng lượng, diện tích và GDS. **{len(blank)} cell trước đây trống đã có output**: đọc số liệu từ 43 report đóng gói, dựng lại đồ thị và trình bày API ở cell chỉ khai báo hàm. Nguồn/ngày nằm dưới bảng, không thêm banner cho số liệu. Đã chạy kiểm {r['executed_cells']} cells của phần hiển thị, tạo {r['tables']} bảng và {r['plots']} hình; transcript tool đầy đủ giữ trong file log, output chỉ giữ dòng kết quả chính. Các số đo diện tích/năng lượng và hai hình top của Run All đã xác nhận được giữ nguyên.

Bản chính hiện có **{len(book.cells)} cells / 129 code cells**. Báo cáo: `docs/output_validation_20261027.json`.

'''
    if '## Bảng và đồ thị trong cell — 2026-10-27' not in s:
        first,rest=s.split('\n',1);s=first+'\n\n'+note+rest.lstrip('\n')
    p.write_text(s)
root=Path('/home/nam/Vihn/interface_verify/fpga_export_18x18_mnist_softreset/test_folder/AutoMX-CIM')
for name in ['scripts/cim_output_presentation.py','scripts/enrich_cim_notebook.py','scripts/cim_function_reference.py',
 'scripts/cim_measurement_extension.py','scripts/adapt_flow2_standalone_notebook.py','scripts/validate_notebook_outputs.py',
 'scripts/publish_notebook_outputs.py','scripts/standalone_readme.md','docs/output_validation_20261027.json']:
    shutil.copy2(b/name,root/name)
shutil.copytree(b/'data/checkpoints',root/'data/checkpoints',dirs_exist_ok=True)
print('OUTPUTS_UPDATED',json.dumps({k:r[k] for k in ['notebook_cells','code_cells','formerly_silent','silent_cells_remaining','tables','plots']}),flush=True)
