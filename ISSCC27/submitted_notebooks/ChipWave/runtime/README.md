# ChipWave case runtime

This local component distribution contains the CLI, TaskGraph, Codex adapter,
IP library and physical-flow dependencies used in the accompanying experiment.
The exact source scope and hashes are in `used-components.json`. It contains
137 selected source/resource files from the recorded `mvp_test` revision.
Exact upstream revisions and released-file hashes remain in the manifest.

The project owner requested publication of the components used in this case
so that others can reproduce and reuse the work. This selected distribution
is covered by the submission's Apache-2.0 license. The upstream private
repository's global Proprietary designation and license files are unchanged.
The submission does not claim that the entire upstream platform is public.

Install with `python -m pip install ./runtime`. Use `chipwave new`,
`chipwave run`, and `chipwave taskgraph` with the supplied project-local
roles and recipes. The browser frontend is outside this case distribution.
A model account is needed for new RTL generation and AI PPA decisions;
saved-design functional checks, offline workflow lessons and deterministic
physical replay require no model account or network model calls.

The standard-flow extension includes the used CSIR compiler and PREPARE/review/freeze path, the specification-to-gds recipe, its roles and required authoring/physical-closure skills. The added compiler/resource files retain the frozen upstream bytes. The explicit recovery-control patch is identified with its upstream and released hashes in used-components.json; it permits a recorded operator decision to restart review from current inputs while retaining old WIP and its session.

The project-creation compatibility patch supports older Git installations. Both
patches have upstream/released hashes and explanations in `used-components.json`.

The benchmark-workflow extension increases the real physical-tool version-query
timeout from 10 to 60 seconds for rootless container startup on shared hosts.
It still queries and matches the actual pinned versions; engineering gates,
tool binaries and physical candidate timeouts are unchanged. The original and
released source hashes are recorded in `used-components.json`.

The public project is named **ChipWave**. The historical upstream project name
is ChipNebula. The Python import namespace `chip_nebula`, `.chip_nebula`
project data and the `chip-nebula` command alias remain compatible with the
frozen experiments. The public command is `chipwave`; its display-only CLI
patch is recorded in `used-components.json`. Original evidence and licensing
identities have not been rewritten.
