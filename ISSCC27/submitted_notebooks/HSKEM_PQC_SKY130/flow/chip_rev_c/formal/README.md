# Bounded formal checks of the session service

`hsm_session_props.sv` states six properties on the ports of `hsm_shell`, in the chip's configuration: the internal ML-KEM key channel is on and the HMAC sits outside the shell, so that its busy, done and digest signals are free inputs and every property holds for any HMAC timing and any digest. Inputs are free in every cycle, apart from one reset at the start, one compact command in flight at a time, and legacy and compact commands never in the same cycle.

| | Property |
|:---|:---|
| P1 | No bit of K reaches the host: two copies that differ only in K give identical responses |
| P2 | A sealed frame's counter is exactly the previous one plus one, starting at 1 |
| P3 | An accepted frame carries the epoch of the current binding and a counter above the last accepted |
| P4 | After the rejection limit no frame is accepted until the next binding or zeroization |
| P5 | A binding is refused as a replay only if an earlier successful command used that counter or a later one |
| P6 | A binding succeeds only with a nonce ready, returns that nonce as its epoch and consumes it |

`run_formal.sh` needs SymbiYosys and Bitwuzla (OSS CAD Suite) and the chip's RTL root from `../rtl/make_root.sh`:

```
flow/chip_rev_c/rtl/make_root.sh /tmp/hskem2c
flow/chip_rev_c/formal/run_formal.sh /tmp/hskem2c/root /tmp/hskem_formal results/fullchip/rev_c/session_formal.json
```

The checks are bounded to 48 cycles from reset, and the model lowers the rejection limit from 16 to 2 so that the lock lies within the bound. The cover task shows that a binding, a sealed frame, a received frame and the lock are reached. The unbounded attempt does not close: k-induction to depth 12 passes its base case and fails its induction step, so these are bounded checks, not proofs.
