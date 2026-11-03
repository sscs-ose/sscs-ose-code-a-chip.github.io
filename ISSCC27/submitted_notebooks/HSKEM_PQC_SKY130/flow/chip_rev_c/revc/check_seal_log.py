"""Recompute every tag of a SEAL_LOG line with Python's hmac module: HMAC-SHA-256 keyed with K over the 28-byte
message "TrustSF2" || epoch || counter || payload, truncated to 16 bytes.   usage: check_seal_log.py <log>"""
import hashlib, hmac, re, sys
n = bad = 0
for m in re.finditer(r"SEAL_LOG K=(\w+) E=(\w+) C=(\w+) P=(\w+) T=(\w+)", open(sys.argv[1]).read()):
    k, e, c, p, t = (bytes.fromhex(x) for x in m.groups())
    n += 1
    if hmac.new(k, b"TrustSF2" + e + c + p, hashlib.sha256).digest()[:16] != t:
        bad += 1
print(f"SEAL_TAGS {n} checked, {bad} wrong")
sys.exit(1 if bad or n == 0 else 0)
