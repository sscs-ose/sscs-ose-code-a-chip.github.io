"""UCI-HAR loading, subject-wise split, feature selection and quantization.

Everything that touches labels or statistics is fit on the TRAIN subjects only
(validation subjects are carved out of the official train subjects; the official
test subjects are never used for fitting).
"""
import hashlib
import json
import pathlib
import urllib.request
import zipfile

import numpy as np
from sklearn.feature_selection import f_classif

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
SPLITS_JSON = DATA_DIR / "splits.json"

HAR_URL = ("https://archive.ics.uci.edu/static/public/240/"
           "human+activity+recognition+using+smartphones.zip")
HAR_SHA256 = "c00b803081a5c797cd5e4b83700a9810b38d53d9d84e01917e090e1fdbc81031"
CLASSES = ["WALKING", "UPSTAIRS", "DOWNSTAIRS", "SITTING", "STANDING", "LAYING"]
N_VAL_SUBJECTS = 4
SPLIT_SEED = 2027


def download_har():
    """Download and unpack UCI-HAR (checksum-verified). Returns the dataset dir."""
    ds = RAW_DIR / "UCI HAR Dataset"
    if (ds / "train" / "X_train.txt").exists():
        return ds
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    outer = RAW_DIR / "har.zip"
    if not outer.exists():
        urllib.request.urlretrieve(HAR_URL, outer)
    digest = hashlib.sha256(outer.read_bytes()).hexdigest()
    if digest != HAR_SHA256:
        raise RuntimeError(f"UCI-HAR checksum mismatch: {digest}")
    with zipfile.ZipFile(outer) as z:
        z.extractall(RAW_DIR)
    with zipfile.ZipFile(RAW_DIR / "UCI HAR Dataset.zip") as z:
        z.extractall(RAW_DIR)
    return ds


def _load_part(ds, part):
    X = np.loadtxt(ds / part / f"X_{part}.txt", dtype=np.float32)
    y = np.loadtxt(ds / part / f"y_{part}.txt", dtype=np.int64) - 1  # 0..5
    s = np.loadtxt(ds / part / f"subject_{part}.txt", dtype=np.int64)
    return X, y, s


def make_splits():
    """Official subject split + seeded validation subjects. Written once, then frozen."""
    if SPLITS_JSON.exists():
        return json.loads(SPLITS_JSON.read_text())
    ds = download_har()
    _, _, s_tr = _load_part(ds, "train")
    _, _, s_te = _load_part(ds, "test")
    train_subj = sorted(set(s_tr.tolist()))
    rng = np.random.default_rng(SPLIT_SEED)
    val_subj = sorted(rng.choice(train_subj, N_VAL_SUBJECTS, replace=False).tolist())
    splits = {
        "dataset": "UCI-HAR (561 features)",
        "sha256": HAR_SHA256,
        "seed": SPLIT_SEED,
        "train_subjects": [s for s in train_subj if s not in val_subj],
        "val_subjects": val_subj,
        "test_subjects": sorted(set(s_te.tolist())),
        "note": "Official 21/9 subject split; val subjects drawn from the official train subjects.",
    }
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    SPLITS_JSON.write_text(json.dumps(splits, indent=2) + "\n")
    return splits


def select_features(X, y, F, corr_max=0.95):
    """Greedy ANOVA-F ranking that skips features too correlated with ones already picked."""
    score, _ = f_classif(X, y)
    order = np.argsort(-np.nan_to_num(score))
    Z = (X - X.mean(0)) / (X.std(0) + 1e-9)
    picked = []
    for i in order:
        if all(abs(float(Z[:, i] @ Z[:, j]) / len(Z)) < corr_max for j in picked):
            picked.append(int(i))
            if len(picked) == F:
                break
    return np.array(picked)


def quantize(X, lo, hi, Q):
    """Uniform Q-level quantization with train-set min/max; values outside are clipped."""
    q = np.floor((X - lo) / (hi - lo + 1e-12) * Q)
    return np.clip(q, 0, Q - 1).astype(np.int64)


def load(F=64, Q=16):
    """Return dict of quantized splits: {'train'|'val'|'test': (Xq [N,F], y [N], subj [N])}."""
    ds = download_har()
    sp = make_splits()
    Xa, ya, sa = _load_part(ds, "train")
    Xt, yt, st = _load_part(ds, "test")
    tr = np.isin(sa, sp["train_subjects"])
    va = np.isin(sa, sp["val_subjects"])
    feats = select_features(Xa[tr], ya[tr], F)
    lo, hi = Xa[tr][:, feats].min(0), Xa[tr][:, feats].max(0)
    out = {"features": feats, "F": F, "Q": Q}
    for name, X, y, s in [("train", Xa[tr], ya[tr], sa[tr]),
                          ("val", Xa[va], ya[va], sa[va]),
                          ("test", Xt, yt, st)]:
        out[name] = (quantize(X[:, feats], lo, hi, Q), y, s)
    return out


if __name__ == "__main__":
    d = load()
    print(json.dumps(make_splits(), indent=2))
    for k in ("train", "val", "test"):
        print(k, d[k][0].shape, np.bincount(d[k][1]))
