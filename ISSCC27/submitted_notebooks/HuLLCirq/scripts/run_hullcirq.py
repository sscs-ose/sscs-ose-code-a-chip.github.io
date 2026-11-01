#!/usr/bin/env python3
"""Start the English GUI, persistent input history and scoped node-generation API."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from hullcirq.domain import DomainError
from hullcirq.server import make_server
from hullcirq.store import ProjectStore
from hullcirq.store import strict_loads


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8766, help="Loopback HTTP port (default: 8766).")
    parser.add_argument("--data-dir", type=Path, default=PROJECT_ROOT / ".work" / "projects" / "default",
                        help="Local state directory; its state.json holds all revisions and review history.")
    parser.add_argument("--fixture", type=Path, help="Design JSON used only when the state directory is new.")
    parser.add_argument("--compiler-config", type=Path, help="Trusted native/WSL Icarus configuration JSON; no syntax pass is inferred when absent.")
    parser.add_argument("--synthesizer-config", type=Path, help="Trusted native/WSL Yosys configuration JSON for generic synthesis without a PDK.")
    parser.add_argument("--physical-config", type=Path, help="Trusted pinned LibreLane/SKY130 execution profile for S11 routed layout.")
    parser.add_argument("--drc-config", type=Path, help="Trusted pinned DRC profile for the exact adopted S11 GDS; no layout rerun.")
    parser.add_argument("--lvs-config", type=Path, help="Trusted pinned extraction/LVS profile for the exact adopted S12 and S11 circuit; no layout rerun.")
    parser.add_argument("--postlayout-config", type=Path, help="Trusted versioned dynamic post-layout profile for the exact adopted S11/S12/S13 chain and original GUI job.")
    args = parser.parse_args()
    if not 0 <= args.port <= 65535:
        parser.error("--port must be from 0 to 65535")
    try:
        store = ProjectStore(args.data_dir, args.fixture)
        compiler = strict_loads(args.compiler_config.read_text(encoding="utf-8-sig")) if args.compiler_config else None
        synthesizer = strict_loads(args.synthesizer_config.read_text(encoding="utf-8-sig")) if args.synthesizer_config else None
        physical = strict_loads(args.physical_config.read_text(encoding="utf-8-sig")) if args.physical_config else None
        drc = strict_loads(args.drc_config.read_text(encoding="utf-8-sig")) if args.drc_config else None
        lvs = strict_loads(args.lvs_config.read_text(encoding="utf-8-sig")) if args.lvs_config else None
        postlayout = strict_loads(args.postlayout_config.read_text(encoding="utf-8-sig")) if args.postlayout_config else None
        server = make_server("127.0.0.1", args.port, store, PROJECT_ROOT, compiler, synthesizer, physical, drc, lvs, postlayout)
    except (DomainError, OSError) as error:
        print(f"Cannot start HuLLCirq: {error}", file=sys.stderr)
        return 1
    print(f"HuLLCirq S01–S14: http://127.0.0.1:{server.server_address[1]}/", flush=True)
    print(f"Local project history: {store.state_path}", flush=True)
    scope = (postlayout or {}).get("execution_scope", "not_configured")
    print("Input checks, scoped RTL generation, node/global functional verification, routed layout, DRC, LVS and post-layout APIs available. S11–S14 require explicit profiles. S14 method: " + scope + ". Inspect its verification scope and results in the GUI. Ctrl+C stops the server.", flush=True)
    try:
        server.serve_forever(poll_interval=0.25)
    except KeyboardInterrupt:
        pass
    finally:
        server.postlayout_workflow.close()
        server.lvs_workflow.close()
        server.drc_workflow.close()
        server.physical_workflow.close()
        server.global_workflow.close()
        server.global_generation.close()
        server.workflow.close()
        server.generation.close()
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
