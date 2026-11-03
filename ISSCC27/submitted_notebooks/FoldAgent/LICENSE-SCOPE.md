# License scope

The project-owned materials in this package are licensed under the **Apache License 2.0** in [LICENSE](LICENSE). The author confirmed public release under the proposed license scheme on 31 October 2026. See [PUBLICATION-AUTHORIZATION.json](PUBLICATION-AUTHORIZATION.json).

| Material | Applicable terms |
|---|---|
| Notebook, English/Chinese HTML, authored figures and documentation | Apache-2.0 |
| Project RTL, specifications, interface maps and verification code under design/ | Apache-2.0 |
| Reference RTL, testbenches, stimulus, original ChipNebula measurement excerpt and its portable adaptation under reproduction/ | Apache-2.0, as authorized for these packaged materials |
| Project netlists, SDC, SPEF, DEF, placement/routing, analysis scripts and project contributions to GDS under physical/ | Apache-2.0, with the third-party components below retaining their terms |
| Project research data, reports and logs under data/, evidence/ and portability/, including the bounded historical agent configuration/intent/brief/output records under evidence/agent/ | Apache-2.0 |
| Project-authored review, rendering, validation and packaging scripts | Apache-2.0 |
| OpenROAD patches under physical/tool-patches/ | BSD-3-Clause; the directory contains its own LICENSE and NOTICE |

## Third-party materials

- SKY130 HD standard-cell geometry embedded in the GDS files retains Apache-2.0; see licenses/SKY130-HD-Apache-2.0.txt.
- physical/gds/export-technology.lyt retains its upstream ORFS/SKY130 technology provenance. The accompanying ORFS build/run-script BSD-3-Clause and SKY130 Apache-2.0 notices are retained. Its project changes are LEF-path substitutions recorded in physical/gds/inputs.json.
- Third-party license texts under licenses/ retain their existing terms. OpenSTA and Icarus are separately obtained dependencies with GPL licenses; their binaries and complete sources are obtained separately.
- licenses/ChipNebula-original-project.toml records the original platform identity and historical Proprietary field. The bounded measurement excerpt and adaptation shipped here have the Apache-2.0 release authorization recorded above; the complete external platform repository retains its existing license.

Original source and evidence files keep their bytes for hash verification. This scope document attaches the applicable project license to those files without rewriting the measured inputs. Existing copyright, attribution and modification notices remain in place. [NOTICE](NOTICE) and [THIRD-PARTY-NOTICES.md](THIRD-PARTY-NOTICES.md) provide attribution and upstream references.
