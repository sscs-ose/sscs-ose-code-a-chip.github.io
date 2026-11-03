"""run_step.sh 한 단계 결과 → <outdir>/<단계>.json (짧게). 쓰임: summarize.py <단계> <outdir> <top> <종료코드>"""
import json, os, re, sys
step, out, top, rc = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4])
J = dict(step=step, top=top, exit=rc, flatglob=os.environ.get('FLATGLOB', ''))
try:
    wall, rss = open(f'{out}/{step}.time').read().split()[-2:]
    J.update(wall_s=float(wall), maxrss_mb=round(int(rss) / 1024, 1))
except Exception as e:
    J['time_err'] = str(e)
if step == 'drc':
    txt = open(f'{out}/{top}.magic.sum').read().splitlines()
    rules = {}
    for l in txt[1:]:
        m = re.match(r'\s*(\d+)\s+(.*)', l)
        if m:
            k = re.search(r'\(([^)]*)\)\s*$', m.group(2)); rules[k.group(1) if k else m.group(2)] = rules.get(k.group(1) if k else m.group(2), 0) + int(m.group(1))
    J.update(total=sum(rules.values()), hvntm_1=rules.get('hvntm.1', 0), total_wo_hvntm1=sum(rules.values()) - rules.get('hvntm.1', 0), rules=rules)
elif step == 'ext':
    sp = open(f'{out}/ext/{top}.mag.spice').read().splitlines()
    log = open(f'{out}/ext.log').read()
    m = re.search(r'ANTENNA_FEEDBACK_COUNT (\d+)', log)
    J.update(subckts=sum(l.lower().startswith('.subckt') for l in sp), antenna_violations=int(m.group(1)) if m else None)
    try:
        fb = open(f'{out}/ext/antenna.fb').read()
        J['antenna_planes'] = {p: fb.count(f'plane {p}') for p in sorted(set(re.findall(r'plane (\w+)', fb)))}
    except OSError:
        pass
elif step == 'lvs':
    t = open(f'{out}/lvs/{top}.netgen.out').read()
    res = re.findall(r'^Final result: (.*)$', t, re.M)
    blocks = re.split(r'^Subcircuit summary:', t, flags=re.M)
    cells = {}
    for b in blocks[1:]:
        c = re.search(r'Circuit 1: (\S+)', b); d = re.search(r'Number of devices: (\d+)[^|]*\|Number of devices: (\d+)', b)
        n = re.search(r'Number of nets: (\d+)[^|]*\|Number of nets: (\d+)', b); v = re.search(r'^(Netlists[^\n]*|Top level cell failed[^\n]*)', b, re.M)
        if c:
            cells[c.group(1)] = dict(dev=[int(d.group(1)), int(d.group(2))] if d else None, nets=[int(n.group(1)), int(n.group(2))] if n else None, result=v.group(1) if v else '')
    bad = {k: v for k, v in cells.items() if 'do not match' in v['result'] or 'port errors' in v['result'] or (v['dev'] and v['dev'][0] != v['dev'][1]) or (v['nets'] and v['nets'][0] != v['nets'][1])}
    J.update(final=res[-1] if res else None, top_cell=cells.get(top), n_cells=len(cells), cells_not_clean=bad,
             top_pin_fail='Top level cell failed pin matching' in t)
elif step == 'read':
    J['ok'] = os.path.exists(f'{out}/read.sum')
json.dump(J, open(f'{out}/{step}.json', 'w'), indent=1)
print(json.dumps({k: v for k, v in J.items() if k not in ('rules', 'cells_not_clean')}, ensure_ascii=False))
