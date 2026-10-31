"""단계 1: 숫자 3개 고르기 (README §4).

0–9 에서 3개를 고르는 120가지 조합을 실제 입력(7×7 이진 ±1)으로 선형 분류기 두 개에 넣어
test 정확도 순위를 낸다. 회로 학습이 아니라 데이터 성질만 본다.
  ridge    : one-hot 최소제곱 + bias, 닫힌 해 (λ = 1e-3·N)
  centroid : 가장 가까운 클래스 평균
train 은 그 숫자들의 MNIST train 전부, test 는 t10k 전부.

사용: python select_digits.py [--thr 0.5]   →  out/select_digits_thr<thr>.csv
"""
import argparse
import csv
import itertools
from pathlib import Path

import numpy as np

from data import binarize, load_pooled, subset

ap = argparse.ArgumentParser()
ap.add_argument('--thr', type=float, default=0.5, help='이진화 문턱 (화소 평균)')
a = ap.parse_args()

ptr, ytr_all = load_pooled('train')
pte, yte_all = load_pooled('t10k')
Btr, Bte = binarize(ptr, a.thr), binarize(pte, a.thr)


def ridge(Xtr, ytr, Xte, lam=1e-3):
    A = np.hstack([Xtr, np.ones((len(Xtr), 1))])
    W = np.linalg.solve(A.T @ A + lam * len(A) * np.eye(A.shape[1]), A.T @ np.eye(3)[ytr])
    return (np.hstack([Xte, np.ones((len(Xte), 1))]) @ W).argmax(1)


def centroid(Xtr, ytr, Xte):
    M = np.stack([Xtr[ytr == k].mean(0) for k in range(3)])
    return ((Xte[:, None, :] - M[None]) ** 2).sum(-1).argmin(1)


rows = []
for cl in itertools.combinations(range(10), 3):
    Xtr, ytr = subset(Btr, ytr_all, cl)
    Xte, yte = subset(Bte, yte_all, cl)
    pr, pc = ridge(Xtr, ytr, Xte), centroid(Xtr, ytr, Xte)
    per = [(pr[yte == k] == k).mean() for k in range(3)]
    rows.append(dict(digits='-'.join(map(str, cl)), ridge_acc=(pr == yte).mean(), ridge_min_class=min(per),
                     centroid_acc=(pc == yte).mean(), n_train=len(ytr), n_test=len(yte)))

rows.sort(key=lambda r: (-r['ridge_acc'], -r['centroid_acc']))
rank_c = {r['digits']: i + 1 for i, r in enumerate(sorted(rows, key=lambda r: -r['centroid_acc']))}
out = Path(__file__).parent / 'out' / f'select_digits_thr{a.thr}.csv'
out.parent.mkdir(exist_ok=True)
with open(out, 'w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0]) + ['centroid_rank'])
    w.writeheader()
    for r in rows:
        w.writerow({**r, 'centroid_rank': rank_c[r['digits']]})

print(f'thr {a.thr}: on-pixel 비율 train {np.mean(Btr > 0):.3f}')
print(f'{"rank":>4} {"digits":>7} {"ridge":>7} {"min cls":>8} {"centroid":>9} {"c-rank":>6}')
for i, r in enumerate(rows):
    if i < 10 or r['digits'] == '0-1-2':
        print(f'{i + 1:>4} {r["digits"]:>7} {r["ridge_acc"]:7.4f} {r["ridge_min_class"]:8.4f} '
              f'{r["centroid_acc"]:9.4f} {rank_c[r["digits"]]:>6}')
print(f'saved {out}')
