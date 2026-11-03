"""학습 결과를 한 파일로 정리 (README §11). 체크포인트·config 를 읽기만 하고 다시 학습하지 않는다.

각 실행(run)마다: 초기 준위 L_init (seed 로 다시 만듦, train.py levels_init 과 같은 식), 최고점 L_best, 마지막 L_final,
그에 해당하는 컨덕턴스 G [S] (고정 칸 G_bz·HRS 포함), 셀 종류 kind, 행·열 역할, 정확도, 최고점 위치.
사용: python export_weights.py --tags tanh5_seed0 tanh5_seed1 tanh5_seed2 --out out/weights/tanh5_5bit.npz
      python export_weights.py --nostab --tags nobz5_seed0 nobz5_seed1 nobz5_seed2 --out out/weights/nostab_5bit.npz
--nostab (10/25, README §12): G_bz 0 으로 학습한 실행 (학습 배치는 LAY, stabilizer 칸 = 0 S) 의 학습 셀만
stabilizer 행·열이 없는 LAY_NS 로 옮긴다. 출력 행이 한 칸 올라가고, 옛 stabilizer 열 자리는 남는 열 (HRS, Vcm) 이 된다.
"""
import argparse
import csv
import hashlib
import json
from pathlib import Path

import numpy as np

from circuit import G_WIN, W1, W2, init_G
from train import LAY, LAY_NS, levels_init

ap = argparse.ArgumentParser()
ap.add_argument('--tags', nargs='+', default=['tanh5_seed0', 'tanh5_seed1', 'tanh5_seed2'])
ap.add_argument('--out', default='out/weights/tanh5_5bit.npz')
ap.add_argument('--nostab', action='store_true', help='G_bz 0 실행을 stabilizer 없는 배치 (LAY_NS) 로 옮김')
a = ap.parse_args()
here = Path(__file__).parent
T = LAY_NS if a.nostab else LAY                                   # 내보낼 배치
m = (T.kind == W1) | (T.kind == W2)


def to_T(L):
    """학습 배치 (LAY) 준위 → 내보낼 배치 T. 학습 셀 (W1·W2) 만 옮긴다."""
    if T is LAY:
        return L
    out = np.zeros((T.rows, T.cols), L.dtype)
    out[np.ix_(np.r_[T.r_x, T.r_b], T.c_h)] = L[np.ix_(np.r_[LAY.r_x, LAY.r_b], LAY.c_h)]
    out[np.ix_(T.r_y, T.c_h)] = L[np.ix_(LAY.r_y, LAY.c_h)]
    return out


D = {}
info = []
for tag in a.tags:
    d = here / 'out' / 'runs' / tag
    c = json.loads((d / 'config.json').read_text())
    z = np.load(d / 'ckpt.npz')
    rows = list(csv.DictReader(open(d / 'log.csv')))
    assert not a.nostab or c['g_bz'] == 0, f"{tag}: --nostab 은 G_bz 0 실행만 (g_bz {c['g_bz']})"
    base = init_G(T, np.random.default_rng(0), '2023', c['g_bz'])[0]            # 고정 칸 (train.py 와 같음)
    for j, (n, s) in enumerate(z['runs'].tolist()):
        lmax = 2 ** n - 1
        G_of = lambda L: np.where(m, G_WIN[0] + L * (G_WIN[1] - G_WIN[0]) / lmax, base)
        Li = to_T(levels_init(LAY, s, lmax))                                    # 학습 때 초기값 (LAY) → T
        ev = c['eval_set'] + '_acc'
        r = [x for x in rows if x['run'] == str(j) and x['epoch'] not in ('best', 'final') and x.get(ev)]
        b = max(r, key=lambda x: float(x[ev]))                                     # 처음 나온 최고 (train.py 와 같은 > 비교)
        fin = [x for x in rows if x['run'] == str(j) and x['epoch'] == 'final']
        k = f'{n}b_s{s}'
        Lb, Lf = to_T(z['L_best'][j]), to_T(z['L_final'][j])
        for nm, L in (('L_init', Li), ('L_best', Lb), ('L_final', Lf)):
            D[f'{k}/{nm}'] = L.astype(np.int16)
            D[f'{k}/G_{nm[2:]}'] = G_of(L.astype(float))
        info.append(dict(key=k, tag=tag, bits=n, seed=s, best_val=float(z['best_eval_acc'][j]),
                         test_at_best=float(z['test_at_best'][j]), test_final=float(fin[0]['test_acc']) if fin else None,
                         best_epoch=int(b['epoch']), best_step=int(b['step']), last_step=int(r[-1]['step']),
                         init_frac_lmax=float((Li[m] == lmax).mean()),
                         same_as_init_best=float((Lb[m] == Li[m]).mean()),
                         ckpt_sha256=hashlib.sha256((d / 'ckpt.npz').read_bytes()).hexdigest(), config=c))
D['kind'] = T.kind.astype(np.int8)
D['stab'] = np.array(int(T.stab))                                                  # train.layout_of 가 읽음
D['roles'] = np.array(json.dumps(dict(r_x=T.r_x.tolist(), r_b=T.r_b.tolist(), r_s=None if T.r_s is None else int(T.r_s),
                                      r_y=T.r_y.tolist(), c_h=T.c_h.tolist(), c_s=None if T.c_s is None else int(T.c_s),
                                      c_spare=T.c_spare.tolist())))
D['info'] = np.array(json.dumps(info))
out = here / a.out
out.parent.mkdir(parents=True, exist_ok=True)
np.savez_compressed(out, **D)
keys = [i['key'] for i in info]
for i in info:
    print(f"{i['key']}: init {100*i['init_frac_lmax']:.1f} % 맨 위, 최고 val {i['best_val']:.4f} (epoch {i['best_epoch']}, "
          f"표본 {i['best_step']}), test 최고점 {i['test_at_best']:.4f} / 마지막 {i['test_final']:.4f}, "
          f"최고점 = 초기 준위 {100*i['same_as_init_best']:.1f} %")
for p, q in [(keys[x], keys[y]) for x in range(len(keys)) for y in range(x + 1, len(keys))]:
    for nm in ('L_init', 'L_best', 'L_final'):
        print(f"  {p} 대 {q} {nm} 같은 셀 {100*(D[f'{p}/{nm}'][m] == D[f'{q}/{nm}'][m]).mean():.1f} %")
print(out, f'{out.stat().st_size/1e3:.0f} kB')
