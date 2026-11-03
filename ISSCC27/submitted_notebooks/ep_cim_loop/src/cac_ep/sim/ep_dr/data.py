"""MNIST → 7×7 (4×4 평균) → 이진화 → ±1.  ep_dr 공용 데이터 로더.

입력 bit 1 → +1, 0 → −1 (dual-rail binary, README §1: 0 은 −1).
"""
import os
import struct
from pathlib import Path

import numpy as np

# 공유 원자료 (복사하지 않음). Olympus 에서는 EP_DR_MNIST 로 바꾼다.
MNIST_DIR = Path(os.environ.get('EP_DR_MNIST', '~/work/projects/ternary_ep/sim/data/MNIST/raw')).expanduser()
POOL = 4                        # 28×28 → 7×7
DIGITS = (0, 1, 4)              # 단계 1 결과 (README §8)
THR = 0.3                       # 이진화 문턱 (README §3 #6)


def load_pooled(split):
    """split 'train' | 't10k' → 화소 평균 (N, 49) ∈ [0, 1], 라벨 (N,)."""
    with open(MNIST_DIR / f'{split}-images-idx3-ubyte', 'rb') as f:
        struct.unpack('>IIII', f.read(16)); X = np.frombuffer(f.read(), np.uint8).reshape(-1, 28, 28)
    with open(MNIST_DIR / f'{split}-labels-idx1-ubyte', 'rb') as f:
        struct.unpack('>II', f.read(8)); y = np.frombuffer(f.read(), np.uint8).astype(np.int64)
    n = 28 // POOL
    p = X.astype(np.float64).reshape(-1, n, POOL, n, POOL).mean(axis=(2, 4)).reshape(-1, n * n) / 255.0
    return p, y


def binarize(p, thr=0.5):
    """화소 평균 > thr → +1, 아니면 −1."""
    return np.where(p > thr, 1.0, -1.0)


def subset(x, y, classes):
    """classes (오름차순) 만 남기고 라벨을 0..len−1 로."""
    keep = np.isin(y, classes)
    return x[keep], np.searchsorted(np.asarray(classes), y[keep])


def load_task(split, digits=DIGITS, thr=THR):
    """학습용: split 'train' | 't10k' → 입력 ±1 (N, 49), 라벨 0..len(digits)−1."""
    p, y = load_pooled(split)
    return subset(binarize(p, thr), y, digits)
