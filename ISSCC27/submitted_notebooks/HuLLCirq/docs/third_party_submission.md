# Third-party sources and distribution scope

HuLLCirq's original software and explanatory submission materials use the
[Apache License 2.0](../LICENSE). This does not replace the individual terms of
external tools, models or PDKs, and is not a trademark-clearance statement.

| Dependency or reference | Recorded version/source | Submission treatment |
| --- | --- | --- |
| Python | 3.12.10 Windows embeddable; [official distribution](https://www.python.org/downloads/release/python-31210/) | Runtime acquired separately; Python Software Foundation terms remain upstream |
| Ollama | 0.32.15; [upstream release](https://github.com/ollama/ollama/releases/tag/v0.32.15) | Runtime and components acquired separately; their notices remain in that distribution |
| Qwen2.5-Coder | 7B Instruct / Ollama `qwen2.5-coder:7b`; [model source](https://huggingface.co/Qwen/Qwen2.5-Coder-7B-Instruct) | Weights excluded; pinned acquisition and license acceptance are in the first-use setup |
| Icarus Verilog | 12.0 for generic synthesis-netlist verification; separately pinned later simulator where the frozen native profile requires it | Executables acquired separately; per-run version records control the actual evidence |
| Yosys and ABC | Generic Yosys 0.33 and the separately pinned LibreLane toolchain | Executables acquired separately; do not identify all historical runs with one version |
| LibreLane | [3.0.16](https://github.com/librelane/librelane/tree/3.0.16) | AppImage/tool distributions excluded; reused Apache-2.0 notice retained in [the license copy](licenses/librelane-3.0.16.txt) |
| SKY130A / SKY130 HD | Ciel revision `8afc8346a57fe1ab7934ba5a6056ea8b43078e71`; [SkyWater sources](https://github.com/google/skywater-pdk) | PDK installation and rule-deck sources excluded; acquisition manifest and frozen profile identify original inputs |
| OpenROAD, OpenSTA, Magic, KLayout, Netgen | The source-bound native version/profile records in each case | Acquired through the pinned native environment; individual upstream notices apply |
| Pillow | Used by optional image-rendering helpers | Not required for the standard-library GUI server or notebook evidence checks |

The reused LibreLane timing template and extraction integration are identified
in the retained source and profile metadata. Upstream copyright headers remain
in reused scripts. Derived layout/netlist/report files retain their declared
origin and are not represented as original LLM output or new upstream libraries.

Related work: [Chip-Chat](https://arxiv.org/abs/2305.13243) and
[TinyTPU](https://github.com/deaneeth/tiny-tpu) informed the project context;
their implementations were not copied as the demonstrated circuit. The notebook
and generation histories distinguish `development_assistant`, `local_llm`,
ordinary-program transformations and user-authorized adoption.

The supplied AI-generated logo, concept artwork and derived icon are not
distributed in this curated submission. Their original provenance and bytes
remain in the private preservation set. No ownership, open-license grant or
third-party non-infringement claim is made for those excluded images.
