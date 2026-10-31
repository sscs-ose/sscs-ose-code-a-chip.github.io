"""묶음 안 텍스트 파일의 절대 경로 (원래 작업 컴퓨터·Olympus) 를 받은 사람의 묶음 경로로 바꾼다. 묶음 사본만 고친다.
쓰임: python3 fix_paths.py <repo 폴더> [PDK_ROOT]   (PDK_ROOT 기본 = ~/pdk/volare)
바꾸는 것 (긴 것부터):
  /home/grads/s/seokjindaveoh/work/rram_see_spice/models → <repo>/cac_ep/sim/ep_demo/char/models (SkyWater 5 V 모형)
  /home/grads/s/seokjindaveoh/work/ep_dr                 → <repo>/cac_ep/sim/ep_dr
  /home/grads/s/seokjindaveoh/work/ep_demo               → <repo>/cac_ep/sim/ep_demo
  /home/grads/s/seokjindaveoh/work/sern_hog              → <repo>/sern_hog_classab_opamp/sim
  /home/dave/work/projects/isscc_cac                     → <repo>/cac_ep
  /home/dave/work/projects                               → <repo>
  /home/dave/pdk/volare                                  → PDK_ROOT
  '/home/grads/s/seokjindaveoh/work' (뿌리만)            → <repo>/oly_work (연결 폴더)
"""
import sys
from pathlib import Path

repo = Path(sys.argv[1]).resolve()
pdk = Path(sys.argv[2] if len(sys.argv) > 2 else Path.home() / 'pdk' / 'volare').expanduser()
OLY = '/home/grads/s/seokjindaveoh/work'
MAP = [(f'{OLY}/rram_see_spice/models', f'{repo}/cac_ep/sim/ep_demo/char/models'),
       (f'{OLY}/ep_dr', f'{repo}/cac_ep/sim/ep_dr'),
       (f'{OLY}/ep_demo', f'{repo}/cac_ep/sim/ep_demo'),
       (f'{OLY}/sern_hog', f'{repo}/sern_hog_classab_opamp/sim'),
       ('/home/dave/work/projects/isscc_cac', f'{repo}/cac_ep'),     # original project folder → package folder cac_ep
       ('/home/dave/work/projects', str(repo)),
       ('/home/dave/pdk/volare', str(pdk)),
       (f"'{OLY}'", f"'{repo}/oly_work'")]        # OLY = '…/work' 처럼 뿌리만 쓴 곳 → 아래 연결 폴더
# 뿌리만 쓴 곳 (f'{OLY}/ep_demo/…') 을 위한 연결 폴더: oly_work/{ep_dr,ep_demo,sern_hog,rram_see_spice/models}
ow = repo / 'oly_work'
for name, tgt in (('ep_dr', 'cac_ep/sim/ep_dr'), ('ep_demo', 'cac_ep/sim/ep_demo'), ('sern_hog', 'sern_hog_classab_opamp/sim'),
                  ('rram_see_spice/models', 'cac_ep/sim/ep_demo/char/models')):
    l = ow / name
    l.parent.mkdir(parents=True, exist_ok=True)
    if not l.is_symlink():
        l.symlink_to(repo / tgt)
EXT = {'.py', '.tcl', '.sh', '.sbatch', '.sp', '.spice', '.lib', '.json', '.cir', '.txt', '.magicrc', '.va', '.md', '.cfg', '',
       '.cdl', '.v', '.lef', '.tlef', '.def', '.map', '.sdc', '.tsv', '.yaml', '.mk'}
n_files = n_rep = 0
for f in repo.rglob('*'):
    if 'oly_work' in f.parts or not f.is_file() or f.is_symlink() or f.suffix not in EXT or f.stat().st_size > 20_000_000:
        continue
    try:
        s = f.read_text()
    except (UnicodeDecodeError, PermissionError):
        continue
    t = s
    for a, b in MAP:
        t = t.replace(a, b)
    if t != s:
        n_files += 1
        n_rep += sum(s.count(a) for a, _ in MAP)
        f.write_text(t)
print(f'fix_paths: {n_files} files, {n_rep} replacements (repo = {repo}, PDK_ROOT = {pdk})')
