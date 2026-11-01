# Portable project evidence

Projects can be transferred through the English GUI without copying an entire
workspace or installing software from an archive. This is an **archival evidence
package**, not an executable clone of the original host.

## Export and reopen using only the GUI

1. Wait for active model and EDA work to finish. Open **Projects**.
2. On the source project, select **Download evidence package**. Read the privacy
   notice and type `PRIVATE` to confirm the explicit download.
3. On the destination installation, select **Projects → Restore evidence package**
   and choose the saved `.hullcirq-evidence.json` file. Confirm a new project name.
   If a browser cannot access a file picker, **Paste evidence JSON** accepts the
   complete original package text through an explicit **Check and restore
   evidence** button. Do not reformat it through JavaScript number conversion.
4. Restore assigns fresh project/system IDs and opens a read-only saved system.
   No model, EDA process, tool configuration, policy or automatic adoption starts.
5. In Projects, select **Inspect evidence package**. The service checks every
   attached object's byte count and SHA-256 before listing it. Download raw files,
   inspect the manifest, or select **Open archived Functional Map** for the saved
   interactive map, including role visibility and zoom controls.
6. To continue designing, explicitly **Duplicate** a restored system. This creates
   an editable design with no transferred runs, reviews or adoption policy. Install
   and configure trusted local tools separately, then perform new checks.

Foreign absolute paths inside historical JSON remain byte-for-byte provenance.
They are not rewritten to look like native results, followed to execute commands,
or imported as active host profiles. The separate archive manifest maps retained
bytes to bounded local objects. The regular stage view shows recorded history;
the Projects evidence inspector is the relocation-safe route to archived files
and Functional Maps.

## Contents and boundaries

- Fixed system JSON stores preserve specifications, original expectations,
  snapshots, prompts, RTL proposals, failures, corrections, execution and review
  history as exact raw bytes. Pinned logical component data is retained.
- External EDA files are copied only from explicitly recorded, raw-hash-bound
  artifact manifests below the application's managed result area. Unrelated
  workspace files and directories are never swept into the package.
- Available registered Functional Maps include their verified source and view
  manifests and hash-bound files. Different saved layout/map versions remain
  separate. Import does not regenerate the map or change the physical design.
- Missing original historical files/maps are listed under `unavailable`. A
  package with such entries is not a complete replay archive; the GUI makes the
  missing count visible. A mismatched file hash stops export instead of silently
  substituting another result.
- PDK distributions, tools, executable host configurations, model weights,
  credentials files and model caches are not installation payloads. Use
  [Fresh installation](fresh_install.md) to prepare a destination runtime.

Raw saved history can contain original private host paths, proprietary designs
and prompts. **This is a private transfer format, not a redacted publication
format.** Review its contents before sharing. Public documentation must not copy
real host paths, accounts, addresses, tokens or private capabilities from it.

## Limits and archive safety

The GUI package limit is 120 MiB compressed/encoded, below the 128 MiB upload
limit. Decoding is bounded to 2 GiB total, 512 MiB per file and 50,000 files.
Traversal, absolute archive destinations, Windows device names, alternate data
streams, case-fold collisions, linked/reparse paths, conflicting file/directory
paths, trailing gzip streams and declared-size decompression bombs are rejected.
Every raw byte count/hash is checked. SHA-256 provides integrity, not sender
authentication or proof that a historical circuit result was scientifically
valid. Imported HTML/JavaScript is never executed. The interactive map extracts
only the inert embedded map JSON and presents it using the installed trusted
viewer template, with `<` escaped, network/forms/external resources disabled and
no same-origin privileges. Raw historical HTML remains downloadable unchanged.

## Optional command-line equivalent

Run the isolated Python from the HuLLCirq directory. Replace placeholders with
your local workspace, project ID and a new output filename; never paste secrets.

```powershell
& $Python scripts/portable_project.py export --workspace '<workspace-folder>' --project-id '<project-id>' --package '<new-package-file>'
& $Python scripts/portable_project.py verify --package '<package-file>'
& $Python scripts/portable_project.py restore --workspace '<destination-workspace>' --package '<package-file>' --name 'Restored evidence'
& $Python scripts/portable_project.py inspect --workspace '<destination-workspace>' --project-id '<new-project-id>'
```

`verify` reads and checks the package without creating a workspace or executing
anything. `export` refuses to overwrite an existing output. Neither a successful
archive check nor a restored Accepted label qualifies tools/PDK or execution on
the destination host.
