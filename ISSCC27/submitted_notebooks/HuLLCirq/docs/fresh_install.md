# First-ever PC setup and local GUI launch

Updated: 2026-10-29. This route does **not** require a restored NPU project, a
previous PC's `.work` directory, or a private Ollama model cache. It acquires
pinned public dependencies and opens an independent, initially empty workspace.
Use the migration guide (historical development reference; not included in this curated archive) only when intentionally restoring
an existing environment. Saved results and acceptance are never manufactured by
environment preparation.

## Prerequisites requiring the PC owner's decision

- Windows x86-64 and PowerShell 7 (`pwsh`). Use Microsoft's
  [PowerShell installation instructions](https://learn.microsoft.com/powershell/scripting/install/installing-powershell-on-windows).
- WSL2, with an initialized Ubuntu **24.04 amd64** distribution and standard
  `/mnt/<drive>` automount. The default example name is `Ubuntu`; pass
  `-Distribution Ubuntu-24.04` consistently if that is its actual registered name.
  The helper rejects WSL1, other Ubuntu releases and architectures. Microsoft's
  [WSL installation guide](https://learn.microsoft.com/windows/wsl/install)
  describes administrator installation and reboot requirements. The helper does
  not run `wsl --install`, change WSL versions, or create a Linux user for you.
  Its `/usr/bin/python3` standard library is required for Linux file-link
  inspection; preparation checks its availability before acquisition.
- FUSE2 compatibility in Ubuntu (`libfuse.so.2`). If the prerequisite check reports
  it missing, the PC owner may run `sudo apt-get update` and then
  `sudo apt-get install libfuse2t64` **inside that Ubuntu distribution**. This is
  an explicit system-level prerequisite, not an automatic action of HuLLCirq.
  See the [AppImage project's FUSE documentation](https://docs.appimage.org/user-guide/troubleshooting/fuse.html).
  Do not install the package named `fuse` or disable security controls as a substitute.
- At least 30 GiB free before first preparation, plus space for future design
  outputs. More space may be needed depending on PDK acquisition and retained
  runs. The model alone is about 4.68 GB. A practical machine should have enough
  RAM/GPU memory for the chosen context; 16 GiB system RAM and an 8 GiB-class GPU
  are useful starting points, not a performance guarantee.
- An Internet connection to the documented official sources. No account,
  credentials, paid inference API, network sharing, inbound firewall rule or
  Tailscale configuration is required.

The scripts detect missing prerequisites and stop; they never install packages
system-wide, terminate an unrelated process, or weaken a machine policy. Keep
the checkout on a local Windows drive at a reasonably short path. All dependency
files and host-specific records remain under ignored `.work`.

If preparation reports `Dependency preparation command failed:` without further
detail, a silent prerequisite `test` may have failed. To check FUSE2 explicitly
from Windows PowerShell, run:

```powershell
wsl.exe -d Ubuntu --exec /usr/bin/test -r /usr/lib/x86_64-linux-gnu/libfuse.so.2
$LASTEXITCODE
```

Exit 0 means that specific file is readable; exit 1 means it is not. This is
only a prerequisite check, not complete runtime verification. Use the same
distribution name as the setup command. If missing, follow the owner-approved
Ubuntu `libfuse2t64` installation prerequisite above, then rerun the documented
preparation. Do not create `ready.json` manually, suppress the check, remove
unrelated files or change a firewall/loopback policy. For failed dependency
commands, the helper now names the command and exit code. Retain that detail and
diagnose the prerequisite; empty stdout is not a successful check.

The Windows/WSL link-inventory defect reproduced on 2026-10-29 is corrected.
Fresh preparation validates Linux links, retains original target/content/mode
provenance, and converts only valid relative links to internal regular files
before Windows inventory. Broken, external, cyclic and directory links do not
qualify. The pinned Yosys package set includes its `yosys-abc` documentation
target. Windows long-path I/O is handled locally without changing OS policy.

Application-side PDK verification and related retained-file I/O also use
extended-length Windows reads, preserving the setup receipt and PDK pins. The
2026-10-29 current-host GUI checkpoint passed S11 Mixed placement and S12
Magic/KLayout DRC; S13 and S14 were unexecuted at that checkpoint. This
qualification covers those observed stages. S14's native path-budget guard
remains unchanged. See the external-I/O GUI ledger (historical development reference; not included in this curated archive)
for the recorded scope and subsequent results.

Earlier failed stages and metadata are retained. If a pre-workspace interrupted
setup has an incomplete old PDK manifest, preparation may create separate
complete metadata only when all native-recorded files and all old records match
exactly. It does not overwrite the old manifest or accept changed/extra files.
The verifier and launcher choose that same verified profile set automatically;
do not hand-edit any ready record, remove integrity checks, or repair links
manually. See the six-loop correction and startup record (historical development reference; not included in this curated archive).

## 1. Inspect the plan without downloading or writing

Open **PowerShell 7** in the HuLLCirq directory containing `scripts/run_workspace.py`.
The scripts locate their checkout from their own location, not the terminal's
current directory. These examples assume you are in that directory:

```powershell
pwsh -NoProfile -ExecutionPolicy Bypass -File scripts/setup_fresh_runtime.ps1 -Plan
```

`-Plan` works even before Python is present. It starts no external process and
creates no files. `-ExecutionPolicy Bypass` applies only to that child process;
it does not change the user or machine policy.

## 2. Explicitly acquire and prepare fixed dependencies

Read the license/source table below. The model is Apache-2.0; its license blob
is retained and verified with the model, not replaced by HuLLCirq's license.
Then run:

```powershell
pwsh -NoProfile -ExecutionPolicy Bypass -File scripts/setup_fresh_runtime.ps1 `
  -Prepare -Download -AcceptModelLicense
```

For a differently named, otherwise supported distribution, append
`-Distribution Ubuntu-24.04` to **every** setup/verify/launch command.

This explicit action:

1. Prepares Python 3.12.10 from its fixed official embeddable archive if missing.
2. Checks WSL release, architecture, WSL2 kernel, automount and FUSE compatibility.
3. Obtains the pinned Qwen2.5-Coder manifest and all five content-addressed blobs
   directly from the public Ollama registry. It requests no inference and starts
   no Ollama daemon. There is no dependency on a user's pre-existing model cache.
4. Prepares isolated Ollama, Icarus, Yosys/Tcl, LibreLane and SKY130A/HD dependencies.
   Native commands perform version checks, package extraction and Ciel PDK
   acquisition only; they do not compile a design or run placement, routing,
   simulation, DRC, LVS or S14.
5. Writes a checksum inventory and **new**, current-host compiler/synthesis/
   physical/DRC/LVS profiles. It does not copy an old checkpoint, old NPU design,
   old execution configuration or old accepted result into the new environment.

The isolated profiles and empty workspace use `.work/fresh/<host-binding>/`.
The binding depends on the resolved checkout path and distribution name. Moving
the checkout therefore selects a new root and requires preparation again; stale
absolute paths are not silently reused. The GUI's existing managed model API
uses the fixed shared `.work/m2/ollama-models` location. Existing matching blobs
are read and verified; conflicting files are refused rather than overwritten.

Downloads use unique `.download.<id>` files, verify complete size and SHA-256,
and only then publish the fixed final name. An interrupted download is not a
valid dependency. Repeating the same command retries missing downloads in new
temporary files and verifies completed files. Old interrupted files stay for
diagnosis. An interrupted extraction or conflicting fixed file is preserved and
reported; do not delete a whole `.work` directory or edit pins to force success.
Use a single preparer for a given checkout.

### Fixed sources, identities and license provenance

| Dependency | Fixed identity / source | Conditions |
| --- | --- | --- |
| Python | 3.12.10 Windows amd64; archive SHA-256 `4acbed6dd1c744b0376e3b1cf57ce906f9dc9e95e68824584c8099a63025a3c3`; [python.org](https://www.python.org/ftp/python/3.12.10/python-3.12.10-embed-amd64.zip) | PSF license; archive retained, no system installation |
| Ollama | 0.32.15; archive SHA-256 `a1d11d46a944f9c7521f5e9a3a5db51cd3365401da627d96c204698fc6914ff9`; [upstream release](https://github.com/ollama/ollama/releases/tag/v0.32.15) | MIT plus bundled component notices retained |
| Qwen2.5-Coder | `qwen2.5-coder:7b`, GGUF Q4_K_M; raw manifest SHA-256 `dae161e27b0e90dd1856c8bb3209201fd6736d8eb66298e75ed87571486f4364`; [official Ollama listing](https://ollama.com/library/qwen2.5-coder:7b), [Qwen model](https://huggingface.co/Qwen/Qwen2.5-Coder-7B-Instruct) | Apache-2.0; all blob hashes/sizes and license hash in [the public pin](../configs/fresh_model_qwen25_coder.json); no weights bundled with the source |
| Icarus | Noble `12.0-2build2`, archive SHA-256 `f19394cee05ad526e0eb3873bc6c17a5828f56df17fbe2db40cb66513a2d4667`; [Ubuntu package](https://packages.ubuntu.com/noble/iverilog) | GPL-2.0-or-later and packaged component notices retained; extraction only |
| Yosys / Tcl | `0.33-5build2` / `8.6.14+dfsg-1build1`; exact Ubuntu archive URLs, hashes, sizes and notices in [runtime_m2b.json](../configs/runtime_m2b.json) | Yosys ISC; Tcl/Tk terms; bundled package notices retained |
| LibreLane / SKY130A | LibreLane 3.0.16 AppImage SHA-256 `428df0d6d7ce167de6a31bc46001f1167b7fb1fbc1ed95fba278367a95883147`; Ciel revision `8afc8346a57fe1ab7934ba5a6056ea8b43078e71`; [release](https://github.com/librelane/librelane/releases/tag/3.0.16) | LibreLane Apache-2.0 plus bundled tool notices; PDK component licenses retained and complete installed-file hashes inventoried |

The registry's tested manifest-digest URL returned `MANIFEST_UNKNOWN`. The
installer requests the official `7b` tag endpoint but verifies the **original raw
manifest hash before any blob request**. A changed tag fails safely; it never
silently accepts a newer model. The tag/manifest protocol follows the
[pinned Ollama implementation](https://github.com/ollama/ollama/blob/v0.32.15/server/images.go).
Blob transfers follow only HTTPS redirects and require the pinned digest and byte
count. An unavailable upstream asset is a setup failure, not permission to change
the recorded model/tool version.

## 3. Verify without changing the environment or a circuit

```powershell
pwsh -NoProfile -ExecutionPolicy Bypass -File scripts/setup_fresh_runtime.ps1
```

The default mode only reads/hashes the prepared inventory, exact model manifest
and blobs, profile files and all PDK files. It creates no directory, changes no
file content or modification time, downloads nothing, starts no native/model process and
writes no project or verification result. It checks retained dependency integrity,
not that the whole PC or a circuit has passed EDA. Missing dependencies fail with
a preparation instruction; verification never repairs them automatically.

Preparation reports are private host data. They may contain absolute host paths;
do not publish `.work/fresh`, `.work/m2` or a copied runtime inventory verbatim.

## 4. Start an empty local workspace

```powershell
pwsh -NoProfile -ExecutionPolicy Bypass -File scripts/start_fresh_workspace.ps1
```

The launcher first performs the same read-only verification, then runs the GUI
on loopback only (default port 8772). It starts no model or circuit job. If the
port is already occupied, select an unused `-Port` explicitly or stop the exact
owned prior GUI; the launcher never kills another process. It never enables
Tailscale Serve/Funnel, LAN binding or firewall access.

Run this public procedure from an ordinary Windows PowerShell 7 terminal.
An agent's restricted AppContainer launch is a different execution condition;
the wrapper does not remove inherited isolation or grant network permissions.
Do not disable security controls or add loopback exemptions to make that agent
launch imitate the public procedure. A printed URL or listening socket alone
does not establish readiness: confirm that the normal Projects page actually
opens before starting generation or EDA. A duplicate-start error also does not
prove that the existing listener is reachable.

Public-route qualification must exercise this launcher with its verified fresh
profiles and independent workspace, not substitute a direct development launch
using an old workspace. Existing pinned downloads may be reused if verified;
call that a prepared/current-host test, not a clean-PC installation. Keep setup,
HTTP/GUI startup and circuit E2E evidence separate. On 2026-10-29, after owner
installation of FUSE2 and the source corrections above, this exact public
preparation and an independent default verification passed on the current host:
17,333 files, including the complete 8,322-file selected PDK. This exact public
launcher then started its independent empty workspace, returned HTTP 200 and
visibly displayed **Projects & components** in the embedded browser. Existing
checksum-verified downloads were reused. This qualifies current-host setup and
GUI startup, not a clean-PC/uncached installation or any circuit E2E. See the
actual correction, failures, counts and startup screenshot (historical development reference; not included in this curated archive).

1. Open the local URL printed by the launcher. Choose **New project**, name your
   own digital project and create its system. No NPU import is required.
2. In **01 Global Settings → LLM provider**, select **Local**, Chat Completions,
   model **qwen2.5-coder:7b**, with the managed local endpoint shown by the GUI
   (port 11435, `/v1`). A new project's older default model is not automatically
   relabelled. Set context 32,768, output 4,000, timeout 600 seconds, temperature
   0.2, seed 104, and provider-default thinking, then explicitly save the profile.
3. Select **Start local LLM**. **Test Connection** is an explicit metadata probe
   and saves its probe record; it is not part of read-only environment verification.
4. Enter the design and independent expected vectors, then use the normal GUI
   generation, correction, review and execution actions. See
   [generic digital projects](generic_digital_projects.md). The default policy
   remains manual; setup does not grant automatic acceptance.
5. Prepare S14 from its GUI after the exact S11/S12/S13 chain exists. Host setup
   cannot prepare source-bound S14 or Functional Map data before a design exists.

All circuit generation/repair/reverification after this setup is available from
the GUI; the setup commands do not stand in for those actions. To stop the GUI,
press Ctrl+C in its launcher terminal. Stop the owned local model from the GUI
before closing when appropriate. No network publication needs to be revoked
because this route creates none.

## Validation boundary

The 2026-10-28 implementation was checked using isolated dependency/HTTP/archive
fixtures and actual read-only plan/failure commands. Tests include empty setup,
no private cache, moved tag, corrupt/interrupted transfer, interrupted publication,
license gating, path traversal, conflicting/extra files and moved-host rejection.
The small public manifest endpoint was checked against the original pin. The
development host was **not** wiped, huge dependencies were **not** redownloaded,
and a second clean-PC native S01–S14 E2E is **not claimed**. The earlier non-NPU
GUI E2E remains its own saved evidence, not a substitute for clean-machine testing.

### Implementation and validation ledger (JST)

This setup subtask has **six software-QA iterations**, not six GUI or native
design E2E executions. No model inference, circuit EDA job, live-store mutation,
automatic adoption, system installation, network publication, push or PR was
performed by this subtask.

| Record | Time on 2026-10-28 | Intervention / observed result |
| --- | --- | --- |
| FS-I1 | First public pin write 16:58:08.4187949; setup wrapper 16:58:08.8868600; launcher 16:58:09.3855797; Python orchestrator 17:00:11.2705089 | Added a first-acquisition path, explicit license/download gating, fixed-blob acquisition, host-bound profiles and empty-workspace launcher; historical helpers kept unchanged |
| FS-I1 hardening | Final orchestrator 17:09:52.0085590; setup wrapper 17:09:52.4856815 | Added complete no-write verification, escaped-cache/reparse-point rejection, explicit Ciel acquisition boundary, PDK inventory and host/config bindings |
| FS-I2 | Tests first written 17:02:05.0881399; guide first written 17:04:31.3130511; final test source 17:10:59.7435397 | Added isolated tests, public instructions, failure interpretation and explicit unverified clean-PC boundary |
| FS-Q1 | Before the 17:02:27 checkpoint | Initial 19-test selection: failed with 30 setup/cleanup errors because this environment's default sandbox temporary directory was unwritable; not a dependency or circuit failure |
| FS-Q2 | After that checkpoint | Same 19 tests passed in 0.127 s using a checkout-local test temporary directory; no system ACL or security policy changed |
| FS-Q3 | Subsequent expanded selection | 20 tests: 19 passed, one new positive verification fixture incorrectly inventoried a staging file; the fixture was corrected, not a live environment |
| FS-Q4 | Before the 17:06:33 checkpoint | 20 tests passed in 0.343 s. Actual Python/PowerShell read-only plans succeeded; a missing-runtime verify failed safely without creating its runtime root |
| FS-Q5 | Final 17:11:02.8626394 checkpoint | 21 tests passed in 0.408 s; both PowerShell scripts parsed; targeted whitespace check passed. Fixture expected hashes/sizes are explicitly not native release qualification |
| FS-I1 final bounded-cache hardening | Orchestrator 17:23:26.7277969; public pin 17:23:26.3109460; test source 17:23:27.0964573 | Bound the public manifest to exactly 858 bytes and inventoried only the required model's five blobs/manifest, not unrelated cached models |
| FS-Q6 | 17:23:45.9715003 checkpoint | Final dedicated 21 tests passed in 0.338 s; targeted whitespace check passed. No native acquisition or circuit run added |

The public registry tag response was actually 858 bytes and matched the pinned
manifest SHA-256; the three fixed Ubuntu archive URLs returned HTTP 200 to HEAD
requests. The rejected manifest-digest request and initial sandbox DNS failure
were retained as observations, not reported as successful acquisition. No large
model weights, packages, AppImage or PDK were downloaded for this validation.
