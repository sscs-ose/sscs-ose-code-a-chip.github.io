# Submission, evidence inspection and reproduction

This is the curated HuLLCirq submission snapshot dated 2026-10-31. Start with
[the notebook](../HuLLCirq.ipynb) and [the evidence index](../submission/evidence_index.json).
The [team metadata](../submission/team.json) identifies the author and representative.

## Inspect the retained result without installing EDA

1. Extract the archive. The project belongs under
   `ISSCC27/submitted_notebooks/HuLLCirq/`, as specified by the current
   [official README](https://github.com/sscs-ose/sscs-ose-code-a-chip.github.io/blob/main/README.md).
   The separate upstream How to Apply page still mentions ISSCC26; the current
   ISSCC27 README controls the destination for this submission.
2. Open `HuLLCirq.ipynb` in Jupyter, or read its rendered Markdown and saved outputs.
   Its three standard-library Python cells inspect saved evidence only.
3. With Python 3.12 in the project directory, run
   `python scripts/verify_submission.py`. This checks every packaged file against
   `submission/package_manifest.json`. It does not start a model, server or EDA tool.
4. Follow the index to each circuit's original specification, independent expected
   values, adopted stage records, RTL, netlists, layout, waveforms and reports.
   Histories marked as privacy-redacted derivatives are for inspection; their
   source SHA and derivative SHA are distinct.

The main example is the eleven-node, four-PE explicit 2x2 NPU, with original K=3,
ReLU disabled and four expected outputs `[-44, 56, 59, 9]`. Its final layout has
33,681 placed-cell footprints. Counter, FIFO-to-XOR and four shared signed
saturating lanes are independent generic-design examples. Each result belongs
to its own frozen source and independent verification plan.

## Open a design in the English GUI

Follow [first-use setup](fresh_install.md) to acquire the pinned tools into an
independent `.work` directory. Windows x86-64, PowerShell 7 and WSL2 Ubuntu 24.04
amd64 are required by that route. Installing WSL/FUSE prerequisites may require
the PC owner; preparation does not silently perform administrator installation.
An independent clean-PC installation remains unverified.

Open PowerShell in the extracted HuLLCirq directory. Run the documented `-Plan`,
explicit `-Prepare -Download -AcceptModelLicense`, verification and launch steps
in that guide. The scripts derive their checkout from their own location. Do not
paste an example placeholder as an actual project directory. Do not bind the app
to a LAN or change firewall/Tailscale settings for local use.

For a packaged input example, use **Projects -> Restore backup** and select the
case's `input-only.hullcirq-project.json`. Restore creates a read-only source;
use **Duplicate** to obtain an editable design. These samples deliberately
contain no executed runs, reviews or adoption policy. Restore and Duplicate
were checked in isolated software workspaces, not claimed as an additional
GUI/native circuit flow. The separate retained result files document the
historical successful run; imported inputs do not inherit that success.

For a deterministic replay of the exact adopted P1 RTL and saved S10 generic
netlist, use the separate [saved-RTL replay procedure](saved_rtl_replay.md).
Its original testbench checks all 42 output samples in 14 cycles without a
model request or a new synthesis/physical-design run. This route has been
actually executed on the prepared Windows/WSL host during submission refinement.

For new GUI work, follow the [generic digital-project guide](generic_digital_projects.md)
through S01-S14. Explicit preview, generation, execution and review actions
produce new records; the input-only restoration route does not replay adopted RTL.
The [waveform and files guide](waveforms_and_files.md)
explains S06/S10/S14 signals and artifact inspection. The private portable
evidence format is described in [portable projects](portable_projects.md); it
must not be confused with the public redacted inspection histories here.

## Three different meanings of reproduction

| Operation | What it establishes |
| --- | --- |
| Manifest and notebook inspection | Integrity and readability of the submitted, saved evidence; no new circuit execution |
| Replaying adopted RTL with the pinned tools and original independent plan | A new verification result; this requires a separately prepared local runtime and fresh source-bound records |
| Regenerating RTL from the recorded model instructions | A new stochastic proposal which must be verified again; byte-identical answers are not promised |

The initial collection pass performed the first operation and isolated
input-backup restoration checks. A later refinement also compiled and simulated
the saved P1 RTL and saved S10 generic netlist with their unmodified independent
testbench. Both checked 42 outputs with zero mismatch/missing observations.
There was no model regeneration, resynthesis, placement/routing, DRC, LVS or STA
rerun during that refinement. The new replay result does not replace old records.
Installed tool distributions, PDKs, model weights and private host configurations
are excluded; use their documented official acquisition sources and hashes.
See [third-party notices](third_party_submission.md).

## Qualified scope and limitations

S14 is `post_route_functional_plus_sta`: routed-netlist functional simulation
plus extracted nine-corner STA. It is not dynamic SDF simulation, formal
equivalence or foundry signoff. The NPU's retained non-overlap LVS feedback is
separate from the later warning-free Counter correction. Expected values,
50 ns constraints and failed histories were not relaxed or replaced.

The latest closure has 113 GUI scenarios, including 48 extension scenarios,
and one additional complete P1 flow. At I19/Q6 the software suite recorded
3,077 executed tests, zero failures/errors and 36 skip records. I20 subsequently
passed a separate 56-test selection and actual GUI reloads; there was no new
full-suite run after I20. The complete historical fixture tree is retained
privately, so the curated archive does not claim to reproduce that full suite
through `unittest discover` without its omitted research fixtures.

Independent clean-PC setup, actual human usability, maximum native-circuit
scale and condition-dependent repeated electrical-only generic-v2 correction
remain unqualified in actual operation. Analog, CDC, arbitrary PDKs, dynamic
SDF and formal equivalence are unsupported by these results.

## Privacy, originals and submission boundary

Original specifications, expected values, original and failed histories, prior
documents and raw evidence remain unchanged in the private preservation set.
Public histories/logs are explicitly labelled derivatives: private host paths
and identifiers have been removed, and their hashes must not be substituted
for the source hashes of the original run. These derivatives are not importable
original evidence packages and do not fabricate adopted results.

Public inspection covers text, decompressed history objects and retained binary
metadata. Standard loopback constants in executable source are generic runtime
specifications, not this PC's address. Real machine/network addresses, hostnames,
personal filesystem paths and credentials are excluded. The author's name and
affiliation are explicitly authorized public metadata.

AI-generated branding images are excluded because their reuse conditions were
not approved for general redistribution. The source images remain privately
preserved. The submission copy uses text branding; no determination of exclusive
copyright in those images is asserted. The circuit/layout screenshots are
actual retained evidence and are separate from concept artwork.

The notebook's author information is confirmed. The submitter should inspect the
finished notebook and selected claims, then decide whether to submit. No public
fork push, official pull request or external publication was performed during
preparation.
