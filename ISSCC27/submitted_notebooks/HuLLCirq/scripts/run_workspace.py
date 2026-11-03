#!/usr/bin/env python3
"""Start project management and multiple independent system workspaces."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from hullcirq.domain import DomainError
from hullcirq.store import strict_loads
from hullcirq.workspace import WorkspaceRegistry
from hullcirq.workspace_server import make_workspace_server


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8772)
    parser.add_argument("--workspace-dir", type=Path, default=PROJECT_ROOT / ".work" / "workspace")
    parser.add_argument("--ollama-path", type=Path,
                        help="Trusted installed Ollama executable for the GUI's local server controls; no automatic model download.")
    parser.add_argument("--legacy-data-dir", type=Path,
                        help="Copy an existing saved design/history into a read-only managed system; never modify its originals.")
    for name in ("compiler", "synthesizer", "physical", "drc", "lvs", "postlayout"):
        parser.add_argument(f"--{name}-config", type=Path)
    args = parser.parse_args()
    if not 0 <= args.port <= 65535:
        parser.error("--port must be from 0 to 65535")
    server = None
    try:
        registry = WorkspaceRegistry(args.workspace_dir)
        if args.legacy_data_dir:
            try:
                registry.register_legacy(args.legacy_data_dir, "NPU baseline", "Original NPU")
            except DomainError as error:
                if error.code != "project_in_trash":
                    raise
                print("The legacy snapshot remains in Trash. Restore it from Projects > Trash to open it again.", flush=True)
        configurations = tuple(strict_loads(path.read_text(encoding="utf-8-sig")) if path else None
                               for path in (args.compiler_config, args.synthesizer_config, args.physical_config,
                                            args.drc_config, args.lvs_config, args.postlayout_config))
        server = make_workspace_server("127.0.0.1", args.port, registry, PROJECT_ROOT, configurations,
                                       ollama_path=args.ollama_path)
        print(f"HuLLCirq projects: http://127.0.0.1:{server.server_address[1]}/", flush=True)
        print(f"Workspace directory: {registry.root}", flush=True)
        print("New / Open / Close / Backup / Restore, independent systems, and versioned graph components. No model or EDA job starts automatically.", flush=True)
        print("Start the prepared local LLM from Global Settings > Local LLM server. No separate model terminal is required.", flush=True)
        server.serve_forever(poll_interval=0.25)
    except KeyboardInterrupt:
        pass
    except (DomainError, OSError) as error:
        print(f"Cannot start workspace: {error}", file=sys.stderr)
        return 1
    finally:
        if server is not None:
            server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
