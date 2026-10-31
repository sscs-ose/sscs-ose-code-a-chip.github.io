"""Author a fresh Run All session with live tool output and no visible digests."""
from pathlib import Path
import ast,json,re,shutil
import nbformat as nbf
from scripts import build_flow2_combined_inline as combined
from scripts.flow2_notebook_theory import apply_front_matter
ROOT=combined.ROOT
PKG=combined.PKG


def readable_prints(source):
    """Keep raw saved artifacts; omit provenance fields from JSON display calls."""
    lines=source.splitlines(keepends=True);edits={}
    for node in ast.walk(ast.parse(source)):
        if isinstance(node,ast.Call) and isinstance(node.func,ast.Name) and node.func.id=='print':
            for arg in [*node.args,*[v.value for v in node.keywords]]:
                for child in ast.walk(arg):
                    if isinstance(child,ast.Call) and isinstance(child.func,ast.Attribute) and isinstance(child.func.value,ast.Name) and child.func.value.id=='json' and child.func.attr=='dumps':
                        edits[(child.func.lineno,child.func.col_offset,child.func.end_col_offset)]=b'pretty'
    for (line,start,end),value in sorted(edits.items(),reverse=True):
        raw=lines[line-1].encode();lines[line-1]=(raw[:start]+value+raw[end:]).decode()
    result=''.join(lines)
    if edits:result=f'from {PKG}.presentation import pretty\n'+result
    return result


def build():
    combined.build();book=nbf.read(combined.BOOK,4)
    cells=book.cells;by_id={c.id:c for c in cells}
    config=by_id['runall-config'].source
    config=config.replace('import os,sys,json,hashlib,types','import os,sys,json,hashlib,types,time\nfrom datetime import datetime,timezone')
    config=config.replace('os.environ.get("AUTOMX_CIM_ROOT",Path.cwd())','os.environ.get("AUTOMX_CIM_ROOT",'+repr(str(ROOT))+')')
    config=config.replace('CACHE=Path(os.environ.get("AUTOMX_RUNALL_CACHE","/media/nam/EDABK/AutoMX_CIM_runall_20261023")).resolve()\nTAG=os.environ.get("AUTOMX_RUNALL_TAG","combined_inline_srv_20261023_01")',
        'SESSION_NAME="fresh_"+datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")\nCACHE=Path(os.environ.get("AUTOMX_RUNALL_CACHE",str(Path("/media/nam/EDABK/AutoMX_CIM_fresh_runs")/SESSION_NAME))).resolve()\nTAG=os.environ.get("AUTOMX_RUNALL_TAG",CACHE.name)\nWORK=CACHE/TAG\nprior_results=[p for p in WORK.rglob("*") if p.is_file()] if WORK.exists() else []\nif prior_results:raise FileExistsError("Fresh Run All needs an empty output folder. Select a new session: "+str(WORK))\nWORK.mkdir(parents=True,exist_ok=True)\n(WORK/"fresh_start.json").write_text(json.dumps({"started_epoch_s":time.time(),"pre_existing_results":len(prior_results),"reuse":False,"work":str(WORK)},indent=2)+"\\n")')
    by_id['runall-config'].source=config
    presentation=nbf.v4.new_code_cell('%%inline_module presentation\n'+combined.read('scripts/flow2_notebook_presentation.py'),id='inline-presentation')
    cells.insert(cells.index(by_id['inline-history']),presentation)
    by_id['inline-history'].source+='\n# NOTEBOOK_RUN\nhistory.REFERENCE_ONLY=True\n'
    # Include every implementation needed to generate and run the PEX pilot.
    pilot='from dataclasses import dataclass\nCORE="automx_ternary_cim_4x4_core"\nE2M1_MAGNITUDES_X2=(0,1,2,3,4,6,8,12)\n'
    pilot+=combined.nodes('automx_cim/physical/stage5.py','core_pins')
    pilot+=combined.nodes('scripts/run_core_pex_coverage.py','Case','make_deck')
    pilot+=combined.nodes('scripts/run_core_transfer_design_space.py','make_screen_deck')
    pilot+=combined.nodes('scripts/run_core_candidate_pex.py','make_pex_deck')
    pilot+=combined.read('scripts/flow2_fresh_pilot.py')
    cells.insert(cells.index(by_id['inline-history'])+1,nbf.v4.new_code_cell('%%inline_module fresh_pilot\n'+pilot,id='inline-fresh-pilot'))
    replacements={
        'story-transfer_error':'fresh_baseline=fresh_pilot.measure_pair(ROOT,WORK,200,100)',
        'story-candidate_result':'fresh_candidate=fresh_pilot.measure_pair(ROOT,WORK,800,50)',
        'story-decoder_errors':'pass  # Reference definitions only; no process is executed in this cell.',
        'story-partition_result':'fresh_pex_progress=fresh_pilot.plot_progress(WORK)',
        'story-routing_progress':'pass  # The next cell executes OpenROAD/KLayout and prints their native output.',
        'story-dependencies':'fresh_activity=fresh_pilot.fresh_activity(flow)'}
    for cid,invoke in replacements.items():
        before,_,_=by_id[cid].source.partition('# NOTEBOOK_RUN\n');by_id[cid].source=before+'# NOTEBOOK_RUN\n'+invoke+'\n'
    # Each native step executes; outputs never come from a prior session cache.
    support=by_id['inline-support'];support.source=support.source.replace('reuse=True','reuse=False')
    # Cell entrypoints explicitly print measured quantities, not receipt objects.
    calibration=by_id['runall-calibration'];calibration.source=calibration.source.replace('print(\'Measured ADC calibration:\',json.dumps(self.calibration,indent=2))',"print('Measured ADC calibration:',json.dumps({k:v for k,v in self.calibration.items() if k!='source_cases'},indent=2))")
    current=by_id['runall-partition-sources'];current.source=current.source.replace('print("Verified routed source:",support.item(source_views["odb"]))','print("Routing design input:",source_views["odb"])')
    summaries={
        'combined-intro':'# AutoMX-CIM — Fresh Run All: mô phỏng và tool chạy mới\n\nMỗi Run All mặc định tạo một thư mục output mới, bắt đầu trống và tắt reuse. Cell PEX đầu flow chạy ngspice trên cùng hai stimulus trước/sau đổi tải và PWM; phần tiếp theo đo analog/SAR/MHA, tổng hợp Yosys, xuất GDS và kiểm bằng tool native. Output hiển thị command, log tool, điện áp, số lỗi, runtime và kết quả đo.\n\nCác recipe của 127 cell cũ vẫn được giữ để tham chiếu. Lượt này không đọc lại điện áp, waveform hay log đo cũ để làm kết quả hiện tại. RTL/PDK, netlist PEX, GDS library và ODB routing được dùng làm đầu vào thiết kế. Chọn kernel env_mamba rồi Restart & Run All.',
        'combined-history':'## Phần A — recipe cũ và phép đo PEX chạy mới\n\nPhần thuyết minh cũ lưu lại quá trình phát triển. Các recipe lịch sử mặc định chỉ được nạp định nghĩa; hai cell PEX bổ sung bên dưới chạy ngspice thật vào thư mục mới.',
        'story-transfer_error-guide':'### Đo mới lỗi transfer: 200 fF / 100 ps\n\nChạy lại hai stimulus sum 11 và sum 12 trên PEX. Điện áp trong bảng được parse từ stdout ngspice của lượt chạy này.',
        'story-candidate_result-guide':'### Đo lại cùng stimulus: 800 fF / 50 ps\n\nGiữ nguyên PEX và hai stimulus, chỉ đổi tải/PWM. Kiểm gap và overlap từ log mới.',
        'story-decoder_errors-guide':'### Recipe chẩn đoán decoder cũ\n\nGiữ implementation để tra cứu; kết quả decoder của lượt mới được đo ở nhánh SAR phía sau.',
        'story-partition_result-guide':'### Kết quả PEX trước/sau của lượt mới\n\nĐồ thị đọc đúng bốn phép đo ngspice vừa chạy ở hai cell trước.',
        'story-routing_progress-guide':'### Đầu vào routing và lượt xuất GDS mới\n\nCell tiếp theo in đường dẫn ODB đầu vào rồi chạy OpenROAD và KLayout, tạo DEF/LEF/GDS cùng log mới.',
        'story-dependencies-guide':'### Các tool đã chạy trong phiên mới\n\nBảng tổng hợp return code và runtime lấy từ các process được chạy trong phiên hiện tại.',
        'combined-orchestration-appendix':'## Phần C — recipe server cũ để tham chiếu\n\nCác implementation và lời gọi cũ được giữ; Run All hiện tại không in lại log lịch sử.',
    }
    for cid,text in summaries.items():by_id[cid].source=text
    for cell in cells:
        if cell.cell_type=='markdown':
            paragraphs=cell.source.split('\n\n')
            cell.source='\n\n'.join(p for p in paragraphs if not re.search(r'(?i)sha[-_ ]?256|\\rm SHA|SHA256|kiểm SHA',p))
            cell.source=cell.source.replace('Đối chiếu hash','Đối chiếu đầu vào').replace('theo hash','theo đầu vào').replace('kiểm hash','kiểm đầu vào').replace('hash','thông tin đầu vào')
        elif cell.id!='runall-config':
            prefix,sep,body=cell.source.partition('\n')
            if prefix.startswith('%%'):cell.source=prefix+'\n'+readable_prints(body)
            else:cell.source=readable_prints(cell.source)
    apply_front_matter(book)
    book.metadata['automx']['flow']='flow2_fresh_inline_v3'
    book.metadata['automx']['native_reuse']=False
    book.metadata['automx']['source_root']=str(ROOT)
    nbf.write(book,combined.BOOK)
    record=json.loads((ROOT/'docs/flow2_fresh_session_20261023.json').read_text());session=Path(record['session'])
    record['work']=str(session/record['tag']);record['notebook']=str(session/combined.BOOK.name)
    (ROOT/'docs/flow2_fresh_session_20261023.json').write_text(json.dumps(record,indent=2)+'\n')
    shutil.copy2(combined.BOOK,record['notebook'])
    (session/'README.md').write_text('# Fresh Run All\n\nNotebook dùng env_mamba. Tất cả kết quả được tạo mới; không sao chép output/cache/log cũ. Nguồn thiết kế: '+str(ROOT)+'\n')
    print('Fresh notebook:',record['notebook'])
    return record

if __name__=='__main__':build()
