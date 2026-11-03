"""Expose the real five-macro floorplan and source-driven hardening in the notebook."""
from pathlib import Path
import nbformat as nbf


def extend(root=None):
    b=Path(root).resolve() if root else Path(__file__).resolve().parents[1]
    p=b/'AutoMX_CIM_Code_a_Chip.ipynb';book=nbf.read(p,4)
    book.cells=[c for c in book.cells if not c.id.startswith('block-floorplan-')]
    catalog=next(c for c in book.cells if c.id=='native-runall-render-macros')
    catalog.source=catalog.source.replace('len(sources)!=3','len(sources)<3').replace('need the three real wrapper input GDS files','need at least CIM, conditioner and ADC input GDS files')
    catalog.source=catalog.source.replace("('03_adc_reference','SAR ADC with its native reference circuitry','adc_top')]):","('03_adc_reference','SAR ADC with its native reference circuitry','adc_top'),\n        ('08_mha','MHA: QK transpose, softmax, context and projection control','automx_mha_ip'),\n        ('09_readout','Readout, SAR sequencing and calibration','automx_cim_readout_seq')]):")
    catalog.source=catalog.source.replace('catalog.catalog(ROOT,design/"config.json")[:3]','catalog.catalog(ROOT,design/"config.json")[:5]')
    runtime=next(c for c in book.cells if c.id=='standalone-runtime')
    runtime.source='%%standalone_runtime\n'+(b/'scripts/standalone_runtime.py').read_text()+"\nprint('Runtime: harden MHA/readout → five-macro top → hierarchical RC/STA',flush=True)\n"
    guide=nbf.v4.new_markdown_cell('''**Thực hiện:** `native` gọi bản OpenLane/OpenROAD cố định. `build_block` tổng hợp và place-and-route riêng từng module; `finish_block` xuất abstract LEF, trích SPEF và kiểm nguồn/timing nội bộ. `write_interface_lib` khai báo chân và clock cho placement/CTS ở cấp cha; thư viện này không có timing arc. `harden` kiểm source RTL, kích thước, clock và phiên bản tool trước khi nhận các view IP đã đóng; nếu source thay đổi hoặc thiếu view, hàm chạy hardening lại các khối cần thiết. Các macro số là source IP của flow, tương tự CIM và ADC. `prepare_pnr` nối năm bộ GDS/LEF, đặt vị trí cố định và nối power grid. `hierarchical_timing` đọc netlist gate và SPEF của cả cấp cha, MHA và readout để đo timing thực, thay cho việc đặc trưng từng macro quá lâu.

**Đầu vào → đầu ra:** RTL MHA/readout → hard macro GDS/LEF/SPEF → floorplan năm khối → place-and-route dây giữa các khối → LVS, nguồn và STA phân cấp. CTS là Clock Tree Synthesis; STA là Static Timing Analysis; SPEF là Standard Parasitic Exchange Format; LEF là Layout Exchange Format.''',id='block-floorplan-runtime-guide')
    i=book.cells.index(runtime);book.cells.insert(i,guide)
    theory=nbf.v4.new_markdown_cell('''<a id="results-block-floorplan"></a>

## Floorplan gồm năm hard macro

**Thực hiện:** Giữ logic MHA và readout trong hai macro vật lý riêng. Parent top chỉ chứa logic phân quyền và dây giữa các macro; các cell bên trong khối được tổng hợp và đi dây từ RTL trước khi ghép. Ba macro CIM/acquisition, conditioner/mux và SAR ADC giữ vị trí.

| Khối | Kích thước dự kiến / µm | Gốc (x,y) / µm |
|---|---|---|
| CIM + acquisition | Theo LEF | (50,50) |
| Conditioner + mux | Theo LEF | (1100,50) |
| SAR ADC | Theo LEF | (3100,50) |
| Readout / calibration | 1250 × 750 | (800,450) |
| MHA RTL | 650 × 400 | (2250,800) |

**Đầu vào → đầu ra:** hai module RTL đã kiểm thử → hai hình chữ nhật có chân biên riêng → top GDS năm macro. Hình floorplan ở cuối lấy tọa độ từ DEF và kích thước từ LEF thực tế, không thay đổi polygon hay ẩn dây trong GDS.''',id='block-floorplan-theory')
    i=next(i for i,c in enumerate(book.cells) if c.id=='mha-ip-architecture');book.cells.insert(i,theory)
    area=next(c for c in book.cells if c.id=='meter-area')
    a=area.source.index("for meter_file,meter_name in [('core'") if "for meter_file,meter_name" in area.source else area.source.index("_block_names=")
    z=area.source.index('meter_areas +=',a)
    new='''_block_names={'automx_cim_core_acquisition_proto':'Core + acquisition','automx_cim_condition_mux_proto':'Conditioner + mux','adc_top':'SAR ADC','automx_mha_ip':'MHA hard macro','automx_cim_readout_seq':'Readout/calibration hard macro'}
for _lef_path in portable.PNR['config']['EXTRA_LEFS']:
    _lef_text=Path(_lef_path).read_text();_master=re.search(r'MACRO\\s+(\\S+)',_lef_text)[1]
    meter_w,meter_h=map(float,re.search(r'SIZE\\s+([\\d.]+)\\s+BY\\s+([\\d.]+)',_lef_text).groups())
    meter_areas.append({'block':_block_names.get(_master,_master),'area_um2':meter_w*meter_h,'source':str(_lef_path),'kind':'macro footprint'})
'''
    area.source=area.source[:a]+new+area.source[z:]
    area.source=area.source.replace('Placed wrapper/controller + CTS/buffers','Top glue + CTS/buffers')
    area.source=area.source.replace("sum(r['area_um2'] for r in meter_areas[:3])","sum(r['area_um2'] for r in meter_areas if r['kind']=='macro footprint')")
    code='''from pathlib import Path
import re,json
from IPython.display import SVG,Markdown,display
_w=portable.WORK
_def=(_w/'streamout/automx_cim_mixed_signal_proto.def').read_text()
_u=int(re.search(r'UNITS DISTANCE MICRONS (\\d+)',_def)[1])
_section=_def.split('COMPONENTS ',1)[1].split('END COMPONENTS')[0]
_sizes={}
for _p in portable.PNR['config']['EXTRA_LEFS']:
    _s=Path(_p).read_text();_m=re.search(r'MACRO\\s+(\\S+)',_s)[1]
    _sizes[_m]=list(map(float,re.search(r'SIZE\\s+([\\d.]+)\\s+BY\\s+([\\d.]+)',_s).groups()))
_names={'core_i':'CIM + acquisition','condition_i':'Conditioner + MUX','adc_i':'SAR ADC','seq_i':'Readout / calibration','mha_i':'MHA RTL'}
_colors={'core_i':'#3e8c72','condition_i':'#b7953e','adc_i':'#3979a8','seq_i':'#8270a4','mha_i':'#b45560'}
_rows=[]
for _name,_master,_x,_y,_orient in re.findall(r'-\\s+(\\S+)\\s+(\\S+).*?\\+\\s+(?:FIXED|PLACED)\\s*\\(\\s*(\\d+)\\s+(\\d+)\\s*\\)\\s+(\\S+)',_section,re.S):
    if _name in _names:
        _width,_height=_sizes[_master];_rows.append(dict(instance=_name,master=_master,x=float(_x)/_u,y=float(_y)/_u,width=_width,height=_height,orientation=_orient))
assert {r['instance'] for r in _rows}==set(_names)
for i,a in enumerate(_rows):
    for z in _rows[i+1:]:assert a['x']+a['width']<=z['x'] or z['x']+z['width']<=a['x'] or a['y']+a['height']<=z['y'] or z['y']+z['height']<=a['y']
_svg=['<svg xmlns="http://www.w3.org/2000/svg" viewBox="-30 -65 3660 1500" width="1200"><rect x="0" y="0" width="3600" height="1400" fill="white" stroke="#333" stroke-width="4"/><text x="20" y="-20" font-size="32" font-family="sans-serif">Physical floorplan — actual DEF / LEF coordinates (µm)</text>']
for r in _rows:
    x=r['x'];y=1400-r['y']-r['height'];w=r['width'];h=r['height'];cx=x+w/2;cy=y+h/2;col=_colors[r['instance']]
    _svg.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{col}" fill-opacity="0.12" stroke="{col}" stroke-width="5"/>')
    _svg.append(f'<text x="{cx}" y="{cy-15}" text-anchor="middle" font-family="sans-serif" font-size="30" fill="#222">{_names[r["instance"]]}</text>')
    _svg.append(f'<text x="{cx}" y="{cy+30}" text-anchor="middle" font-family="sans-serif" font-size="22" fill="#444">{w:g} × {h:g} | ({x:g}, {r["y"]:g})</text>')
_svg.append('</svg>');_svg=''.join(_svg)
_path=_w/'render_top/block_floorplan.svg';_path.write_text(_svg)
(_w/'block_floorplan.json').write_text(json.dumps({'status':'PASS','die_um':[3600,1400],'blocks':_rows,'source':'actual routed DEF and hard-macro LEFs'},indent=2)+'\\n')
display(SVG(_svg))
display(Markdown('| Block | x,y / µm | Width × height / µm |\\n|---|---|---|\\n'+'\\n'.join(f"| {_names[r['instance']]} | {r['x']:g}, {r['y']:g} | {r['width']:g} × {r['height']:g} |" for r in _rows)))
print('FLOORPLAN_FIVE_FIXED_MACROS_PASS no overlaps',flush=True)
'''
    i=next(i for i,c in enumerate(book.cells) if c.id=='native-runall-render-top')+1
    book.cells[i:i]=[nbf.v4.new_markdown_cell('''**Thực hiện:** Đọc instance cố định từ DEF và SIZE từ năm LEF, kiểm đủ năm khối và không chồng lấn rồi dựng SVG floorplan có tên khối. Hình này là sơ đồ vị trí từ database thực; hình KLayout phía trên vẫn là render GDS với cùng cấu hình lớp/màu.

**Đầu vào → đầu ra:** routed DEF + macro LEF → bảng tọa độ/kích thước, `block_floorplan.json` và `render_top/block_floorplan.svg`.''',id='block-floorplan-render-guide'),nbf.v4.new_code_cell(code,id='block-floorplan-render')]
    for c in book.cells:
        if c.cell_type=='markdown' and 'Kết quả chính' in c.source and 'results-checkpoint' in c.source:
            if '#results-block-floorplan' not in c.source:c.source+='\n\n[Floorplan năm khối vật lý](#results-block-floorplan)\n'
            break
    if book.metadata.get('presentation_language')=='en':
        from scripts.notebook_english import translate_book
        translate_book(book,b)
    nbf.write(book,p)
    print('FIVE_MACRO_NOTEBOOK',len(book.cells),sum(c.cell_type=='code' for c in book.cells))

if __name__=='__main__':extend()
