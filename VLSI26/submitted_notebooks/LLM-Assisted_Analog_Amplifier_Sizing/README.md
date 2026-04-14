# LLM-Assisted Analog Amplifier Sizing

An LLM-guided analog amplifier sizing flow using gm/ID methodology, SPICE verification, and iterative root-cause diagnosis on the SKY130 open-source PDK.

## Team Members

| Name | Affiliation | IEEE Member | SSCS Member |
|------|-------------|-------------|-------------|
| TBD  | TBD         | TBD         | TBD         |

## Tools & Versions

| Tool | Version | Purpose |
|------|---------|---------|
| ngspice | 45+ | SPICE simulation |
| SKY130 PDK | Open-source | 130nm process |
| Python | 3.11 | Agent logic, gm/ID LUT |
| Claude API | Anthropic | LLM backbone |
| FastAPI | 0.135+ | Simulation server |

## Repositories

- **AnalogAgent**: [github.com/Analog-agent/AnalogAgent](https://github.com/Analog-agent/AnalogAgent) — LLM agent + gm/ID LUT + sizing logic
- **CircuitCollector**: [github.com/Analog-agent/CircuitCollector](https://github.com/Analog-agent/CircuitCollector) — Testbench generation + ngspice simulation server

## License

Apache 2.0
