# Complete portable-entry validation

This directory records one execution from a fresh v3 ZIP extraction, a new standard-library Python environment and a minimal child-process environment. The host and recorded installed Icarus/OpenSTA binaries were reused. The source files and STA scripts tested here are identical to their v4 counterparts.

- [result.json](result.json): overall result, exact comparison status and isolation scope.
- [environment.json](environment.json): tested ZIP identity and executable hashes.
- [runtime-environment.json](runtime-environment.json): Python, operating system and architecture.
- paired/reference/ and paired/two-tier/: each design's 162 simulation logs, command receipts and performance report.
- [comparison.json](comparison.json): paired measurement comparison; the reproduction entry also checked all counters against both historical reports.
- joint/: the three analysis logs, complete electrical reports, scalar results and coverage comparison.
- [public-library-check.json](public-library-check.json): fixed public Liberty download and its matching hash.
- [manifest.json](manifest.json): hashes of these execution records.

The performance comparison includes scenario identity, supply/completion cycles, useful bytes, maximum latency, RTL identity and checker/workload digests. Each simulation first checks arithmetic/protocol behavior and ends with FOLD_PERF_PASS. Full electrical reports match the historical reports byte for byte; all 556 unannotated drivers are listed unloaded drivers.

To run the packaged entries, follow ../reproduction/README.md and ../physical/README.md. Fixed public sources and build commands are in ../DEPENDENCIES.md. execute.py preserves the orchestration used for this audit and its original workspace paths.
