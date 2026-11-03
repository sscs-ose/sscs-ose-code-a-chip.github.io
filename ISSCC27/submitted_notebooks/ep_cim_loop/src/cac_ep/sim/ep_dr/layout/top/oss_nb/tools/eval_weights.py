"""저장된 가중치 (export_weights.py 꼴 npz) 또는 학습 체크포인트 (train.py 의 ckpt.npz) 의 test 정확도를 Python solver 로 잰다.
쓰임: python3 eval_weights.py <ep_dr 폴더> npz <weights.npz> [키 …]          → 키마다 test (3,097 장) 정확도, 저장된 값과 차
      python3 eval_weights.py <ep_dr 폴더> ckpt <out/runs/<tag>>            → 그 실행의 L_best 를 학습 배치 (LAY) 로
결과 json 한 줄 (마지막 줄)."""
import json
import os
import sys
import time
from pathlib import Path

EP = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(EP))
import numpy as np            # noqa: E402
import torch                  # noqa: E402
from circuit import G_WIN, W1, W2, init_G   # noqa: E402
from data import load_task    # noqa: E402
from train import LAY, evaluate, layout_of  # noqa: E402

Xte, yte = load_task('t10k')
out = {}
t0 = time.time()
if sys.argv[2] == 'npz':
    W = np.load(sys.argv[3])
    lay = layout_of(W)
    info = {i['key']: i for i in json.loads(str(W['info']))}
    keys = sys.argv[4:] or list(info)
    m = torch.as_tensor((lay.kind == W1) | (lay.kind == W2))
    for k in keys:
        c = info[k]['config']
        G = torch.as_tensor(W[f'{k}/G_best'])[None]
        acc, st = evaluate(lay, G, Xte, yte, c['a'], c['r_on'], m, c['v_b'], c['r_ser'], not c['no_out_clamp'])
        out[k] = dict(test=round(float(acc[0]), 6), saved=round(info[k]['test_at_best'], 6),
                      diff=round(float(acc[0]) - info[k]['test_at_best'], 6), p_neuron_uW=round(float(st['p_neuron_uW'][0]), 2))
        print(f"{k}: test {float(acc[0]) * 100:.2f} % (stored {info[k]['test_at_best'] * 100:.2f} %), {time.time() - t0:.1f} s", flush=True)
else:
    run = Path(sys.argv[3])
    c = json.loads((run / 'config.json').read_text())
    ck = np.load(run / 'ckpt.npz')
    m = (LAY.kind == W1) | (LAY.kind == W2)
    base = init_G(LAY, np.random.default_rng(0), '2023', c['g_bz'])[0]
    for j, (n, s) in enumerate(ck['runs']):
        dg = (G_WIN[1] - G_WIN[0]) / (2 ** int(n) - 1)
        G = torch.as_tensor(np.where(m, G_WIN[0] + ck['L_best'][j] * dg, base))[None]
        acc, _ = evaluate(LAY, G, Xte, yte, c['a'], c['r_on'], torch.as_tensor(m), c['v_b'], c['r_ser'], not c['no_out_clamp'])
        out[f'{n}b_s{s}'] = dict(test=round(float(acc[0]), 6), test_at_best_logged=round(float(ck['test_at_best'][j]), 6))
        print(f"{n}b/s{s}: test {float(acc[0]) * 100:.2f} % (training log {float(ck['test_at_best'][j]) * 100:.2f} %)", flush=True)
if sys.argv[2] == 'npz' and os.environ.get('EVAL_PRED'):     # 그림용: 첫 키의 예측 (혼동 행렬)
    from circuit import row_drive
    from data import DIGITS
    from solver import solve
    k = keys[0]; c = info[k]['config']
    G = torch.as_tensor(W[f'{k}/G_best'])[None]
    pred = []
    with torch.no_grad():
        for i0 in range(0, len(Xte), 1024):
            u = torch.as_tensor(row_drive(lay, Xte[i0:i0 + 1024], c['a']))
            _, vy, _ = solve(lay, G.expand(len(u), -1, -1), u, r_on=c['r_on'], v_b=c['v_b'], r_ser=c['r_ser'], out_diode=not c['no_out_clamp'])
            pred.append((vy[:, 0::2] - vy[:, 1::2]).argmax(1).numpy())
    pred = np.concatenate(pred)
    np.savez(os.environ['EVAL_PRED'], pred=pred, y=yte, digits=np.array(DIGITS), key=k)
    out['pred_acc_check'] = round(float((pred == yte).mean()), 6)
out['sec'] = round(time.time() - t0, 1)
print(json.dumps(out))
