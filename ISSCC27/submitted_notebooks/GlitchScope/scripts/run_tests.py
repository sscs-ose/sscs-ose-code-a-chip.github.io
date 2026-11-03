"""Minimal dependency-free test runner (pytest also works if installed)."""
import importlib, sys, pathlib, os
root = pathlib.Path(__file__).resolve().parents[1]
os.chdir(root); sys.path[:0] = [str(root), str(root / "tests")]
ok = fail = 0
for f in sorted((root / "tests").glob("test_*.py")):
    m = importlib.import_module(f.stem)
    for n in sorted(x for x in dir(m) if x.startswith("test_")):
        try:
            getattr(m, n)(); ok += 1
        except Exception as e:
            fail += 1; print("FAIL", f.stem, n, type(e).__name__, str(e)[:300])
print(f"TESTS pass={ok} fail={fail}")
sys.exit(1 if fail else 0)
