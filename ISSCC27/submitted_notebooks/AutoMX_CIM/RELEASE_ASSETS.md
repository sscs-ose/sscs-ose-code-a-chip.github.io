# Reproduction assets

Download the prepared archives from the team's
[Google Drive folder](https://drive.google.com/drive/folders/182dkLchafQBx1tNYUVZpyNpNAvFWwNjB?usp=drive_link).
Locate each file by its exact name:

| Archive | Size (bytes) | Use |
|---|---:|---|
| `AutoMX_CIM_runtime_inputs_20261030.tar.gz` | 1,454,841,643 | PDKs, pinned toolchain, hard-IP/benchmark inputs and UCI HAR data for a fresh complete run |
| `AutoMX_CIM_measurement_records_20261029.tar.gz` | 429,895,973 | Optional detailed numerical records, logs, NPZ waveforms and experiment scripts from the completed final run |

Open the folder in a browser and download the runtime archive to your
Linux reproduction host. Restore it from the local file:

```bash
python scripts/restore_runtime.py --archive /path/to/AutoMX_CIM_runtime_inputs_20261030.tar.gz
```

The measurement archive is not required to execute the notebook. It is a
selected record of the final acquisition rather than a complete backup of
all intermediate physical/simulator dump files.

The folder and both archives have public link-reader permissions
(`anyone` / `reader`), verified through Drive permission metadata on
31 October 2026. Archive names and byte counts match the table above.
The complete archives were not downloaded during this preparation check.
The `download_url` fields
in `runtime_assets.json` remain null because the delivery uses a folder
page and manual download, rather than individual direct archive URLs.
Use the local `--archive` path after downloading from Drive.

See [reproduction instructions](docs/REPRODUCIBILITY.md) for the Linux host,
native-tool and Python requirements.
