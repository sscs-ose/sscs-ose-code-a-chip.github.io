# LLM-Assisted Analog Amplifier Sizing

An LLM-guided analog amplifier sizing flow using gm/ID methodology, ngspice SPICE simulation, and iterative root-cause diagnosis on the SKY130 open-source PDK.

## Team Members

| Name | Affiliation | Email | IEEE Member | SSCS Member |
|------|-------------|-------|-------------|-------------|
| Jiyuan Duan    | Rice University              | jd200@rice.edu          | Yes | Yes |
| Shikai Wang    | George Washington University | shikai.wang@gwu.edu     | No  | No  |
| Gerald Topalli | Rice University              | gerald.topalli@rice.edu | Yes | Yes |
| Houbo He       | Rice University              | houbo.he@rice.edu       | Yes | Yes |
| Lei Xia        | Rice University              | lx27@rice.edu           | Yes | Yes |
| Weidong Cao    | George Washington University | weidong.cao@gwu.edu     | Yes | Yes |
| Taiyun Chi     | Rice University              | tc57@rice.edu           | Yes | Yes |

## Tools & Versions

| Tool | Version | Purpose |
|------|---------|---------|
| ngspice | 46 | SPICE simulation |
| SKY130 PDK | Open-source | 130nm process (bundled in repo) |
| Python | 3.11 | Agent logic, gm/ID LUT queries |
| Claude Code | Latest | LLM-driven interactive design agent (VS Code extension) |
| FastAPI | 0.118+ | CircuitCollector simulation server |
| Conda/Miniforge | Latest | Environment management |

## Repository

All source code, example netlists, SKY130 gm/ID LUT data, and the full skill stack are in a single public repo:

- **Main repo**: [github.com/jiyuanduan001-oss/LLM-Assisted-Analog-Amplifier-Sizing](https://github.com/jiyuanduan001-oss/LLM-Assisted-Analog-Amplifier-Sizing)
  - `AnalogAgent/` — LLM agent, gm/ID LUT, `.claude/skills/` stack, example netlists, spec-form template
  - `CircuitCollector/` — FastAPI testbench-generation + ngspice simulation server

The notebook walks through cloning this repo, installing ngspice, setting up two conda environments, starting the simulation server, and driving the interactive sizing flow from Claude Code inside VS Code.

## References

- B. Murmann, "gm/ID-Based Design Methodology" (Stanford)
- SkyWater SKY130 Open-Source PDK: https://github.com/google/skywater-pdk
- ngspice Open-Source SPICE Simulator: https://ngspice.sourceforge.io/
- Claude Code: https://claude.ai/claude-code

## License

Apache 2.0
