"""시험용: 노트북 사본에 nb_cell_sec8.py 를 8 장 블록 생성 셀 바로 뒤에, nb_cell_sec10.py 를 10 장 배선 셀 바로 앞에 넣는다 (정본 build_nb.py 는 메인 세션이 고침).
쓰임: python3 test_insert_cell.py <in.ipynb> <cell8.py> <out.ipynb> [cell10.py]"""
import json
import sys
nb = json.load(open(sys.argv[1]))
src = open(sys.argv[2]).read()
k = next(i for i, c in enumerate(nb['cells']) if c['cell_type'] == 'code' and 'for name, cwd, cmd, outs in BLK:' in ''.join(c['source']))
cell = dict(cell_type='code', execution_count=None, metadata={}, outputs=[], source=src.splitlines(keepends=True))
if 'id' in nb['cells'][k]:
    cell['id'] = 'digoss01'
nb['cells'].insert(k + 1, cell)
if len(sys.argv) > 4:
    k2 = next(i for i, c in enumerate(nb['cells']) if c['cell_type'] == 'code' and "RO = LT / 'route_oss'" in ''.join(c['source']))
    c2 = dict(cell_type='code', execution_count=None, metadata={}, outputs=[], source=open(sys.argv[4]).read().splitlines(keepends=True))
    if 'id' in nb['cells'][k2]:
        c2['id'] = 'digoss02'
    nb['cells'].insert(k2, c2)
    print('inserted before cell', k2)
json.dump(nb, open(sys.argv[3], 'w'), indent=1, ensure_ascii=False)
print('inserted after cell', k)
