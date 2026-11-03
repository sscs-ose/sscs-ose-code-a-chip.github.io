# Phase 0 — Environment record (HashPareto)

Captured: 2026-10-09 (UTC) on the development machine.
This file is the authoritative, reproducibility-relevant inventory for Phase 0.
It is deliberately detailed: the Code-a-Chip submission notebook must be able to
justify and recreate its toolchain.

## 1. Host

| Item | Value |
|---|---|
| OS | Windows 11 Pro (build 26100) |
| Shell | PowerShell 5.1 |
| CPU | 8 logical processors |
| Physical RAM | 7.81 GiB (≈ 8 GB) |
| Free space on `C:` | ≈ 31 GB |
| Git (Windows) | 2.55.0.windows.5 |
| Python (Windows) | 3.14.7 |

> **Resource caveat.** The host has only ~8 GB RAM. WSL2 sees 5.8 GiB of it
> (raised from the 3.7 GiB default via `.wslconfig`, §2/§7). Large, fully
> unrolled SHA-256 variants (tens of thousands of instances) may still be slow
> or OOM during placement/routing. Mitigations are listed in §6. Free disk
> (~31 GB on `C:`; the WSL virtual disk grows on `C:`) is sufficient but must be
> monitored.

## 2. WSL2 / Linux

| Item | Value |
|---|---|
| Distro | Ubuntu 26.04.1 LTS (default, WSL version 2) |
| Kernel | 6.18.40.1-microsoft-standard-WSL2 |
| CPUs visible | 8 |
| Memory visible | 5.8 GiB total (limit `memory=6GB`) |
| Linux home | `/home/userchimbuchi` |
| `.wslconfig` | `C:\Users\USER\.wslconfig` with `[wsl2] memory=6GB swap=8GB processors=8` (applied 2026-10-09) |

## 3. RTL-to-GDS toolchain — LibreLane devshell AppImage

The flow is **not** installed with Docker. It is provided by a self-contained
AppImage that starts a Nix devshell with all EDA tools on `PATH`.

| Item | Value |
|---|---|
| AppImage | `~/librelane-devshell-x86_64.AppImage` |
| Bytes | 1398053408 (1.30 GiB) |
| SHA-256 | `428df0d6d7ce167de6a31bc46001f1167b7fb1fbc1ed95fba278367a95883147` |
| LibreLane | **v3.0.16** (Apache-2.0; adapted from OpenLane 2.0) |
| `librelane` path | `/nix/store/qnkq5r0v5zpifw744hdd6r4f4izr13mc-devshell-dir/bin/librelane` |
| Yosys | 0.62 (git 7326bb7d, clang++ 21.1.2) |
| OpenROAD | git `dcf36133a369abc8f3c5e5738cd4d82e4903c0e0` |
| Magic | 8.3.623 |
| Netgen | 1.5.316 |
| KLayout | 0.30.7 |
| Verilator / cocotb | bundled in devshell; cocotb 2.1.0 in venv |

### How to invoke it non-interactively

The AppImage opens an interactive `[nix-shell: ...]` prompt reading from stdin.
Feeding it commands over a pty works reliably:

```bash
printf '%s\nexit\n' 'librelane --version' | script -qec ~/librelane-devshell-x86_64.AppImage /dev/null
```

A convenience wrapper is committed at `tools/run_librelane.sh`:

```bash
tools/run_librelane.sh 'librelane --version'
```

Notes:
- The devshell emits ANSI control sequences; strip with
  `sed -E 's/\x1b\[[0-9;?]*[a-zA-Z]//g'` when parsing stdout.
- Passing the AppImage a command directly
  (`AppImage bash -lc '...'`) does **not** put `librelane` on `PATH`; the pty
  approach above is required.

## 4. Process Design Kit (SKY130)

| Item | Value |
|---|---|
| PDK manager | CIEL (`~/.ciel`) |
| PDK root | `~/.ciel/ciel/sky130/versions/8afc8346a57fe1ab7934ba5a6056ea8b43078e71` |
| Variants | `sky130A`, `sky130B` |
| PDK on-disk size | ≈ 2.2 GB |

## 5. Python / notebook environment

A virtualenv exists at `~/venv` (Python 3.14.4) with the notebook stack already
installed:

| Package | Version |
|---|---|
| jupyterlab | 4.6.4 |
| numpy | 2.5.3 |
| pandas | 3.0.6 |
| matplotlib | 3.11.2 |
| cocotb | 2.1.0 |
| PyYAML | 6.0.3 |
| jupyter_client / core / server | 8.10.0 / 5.9.1 / 2.21.1 |

## 6. Proof the flow works end-to-end

A complete SKY130 hardening of a UART (`DESIGN_NAME: top`, 20 ns clock) already
ran to completion on this machine:

```
~/project/uart_first/runs/RUN_2026-10-06_18-01-26/
```

It traversed all 76 LibreLane steps, including synthesis, floorplan, placement,
CTS, routing, RC extraction, STA, Magic/KLayout streamout, XOR, Magic/KLayout
DRC, SPICE extraction, and Netgen LVS, and produced:

- `final/gds/top.gds`
- `final/lef/top.lef`
- `final/metrics.json` (area ≈ 8720.86 µm², 1449 instances; power/timing per corner)

This demonstrates that synthesis-through-GDS, DRC, and LVS all pass on this host.
The remaining Phase 0 gap is only the SHA-256 design itself (Phase 1/2).

## 7. Known risks and mitigations

| Risk | Mitigation |
|---|---|
| 3.7 GiB WSL RAM may OOM large unrolled variants | **DONE — applied.** `%UserProfile%\.wslconfig` sets `memory=6GB, swap=8GB, processors=8`; verified `free` shows 5.8 GiB after `wsl --shutdown`. If even this is insufficient, cap the largest variant at `UNROLL=16` pipelined rather than full 64-unroll. |
| `C:` free space (~31 GB) shared with the growing WSL VHD | Keep only `final/` artifacts + metrics per run; delete intermediate `runs/*` step dirs after each capture. |
| `/mnt/c` (DrvFs) is slow/risky for EDA I/O | Keep the canonical repo on `C:`, but run flows from a WSL-native scratch dir (e.g. `~/hashpareto_run`), copying RTL in and `final/` + metrics out. |
| Devshell ANSI noise obscures logs | Parse LibreLane's own log files and `metrics.json` rather than stdout. |

## 8. Phase 0 exit checklist

- [x] WSL2 distro present and running (Ubuntu 26.04)
- [x] LibreLane devshell AppImage present, versioned, hashed
- [x] SKY130A/B PDK installed via CIEL
- [x] Notebook Python venv present (jupyterlab, numpy, pandas, matplotlib, cocotb)
- [x] End-to-end SKY130 flow proven on this host (UART run)
- [x] Non-interactive invocation wrapper committed (`tools/run_librelane.sh`)
- [x] Repo skeleton, `LICENSE` (Apache-2.0), `NOTICE`, reference RTL vendored
- [x] `.wslconfig` memory bump applied and verified (5.8 GiB visible)
- [x] Git repository initialized; Phase 0 committed (commit `1272ae9`)
- [x] NIST SHA-256 vectors added under `data/vectors/` (hashlib-verified)
