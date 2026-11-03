"""Bounded, deterministic single-clock SoC wiring from frozen CSIR and locked IP."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePosixPath
import shlex
from typing import Any, Mapping

from chip_nebula.taskgraph.soc_adapter import SoCAdapterError, gpio_output_adapter


SOC_PACKAGE_TOPS = {
    "rv32i-cpu": "picorv32",
    "native-apb-bridge": "nebula_native_apb_bridge",
    "apb-gpio": "nebula_apb_gpio_regs",
    "apb-uart": "nebula_apb_uart",
    "apb-timer": "nebula_apb_timer",
}
_MEMORY_CAPABILITIES = {"program-rom", "register-ram"}
_PERIPHERAL_CAPABILITIES = {"apb-gpio", "apb-uart", "apb-timer"}


class SoCAssemblyError(ValueError):
    pass


@dataclass(frozen=True)
class SoCBuild:
    source: str
    connections: tuple[dict[str, Any], ...]


def supports_soc_package(capability: str, top_module: str) -> bool:
    """Only the pin contracts implemented below may enter this assembly profile."""
    return SOC_PACKAGE_TOPS.get(capability) == top_module


def _number(value: Any) -> int:
    if type(value) is int:
        return value
    if isinstance(value, str):
        return int(value, 0)
    raise SoCAssemblyError(f"invalid address or size: {value!r}")


def _hex32(value: int) -> str:
    return f"32'h{value:08X}"


def _hex12(value: int) -> str:
    return f"12'h{value:03X}"


def _parameters(entry: Mapping[str, Any]) -> str:
    values = entry.get("parameters", {})
    if not values:
        return ""
    if any(type(value) is not int for value in values.values()):
        raise SoCAssemblyError(f"unsupported parameter binding: {entry['instance']}")
    pairs = ", ".join(f".{name}({value})" for name, value in sorted(values.items()))
    return f" #({pairs})"


def _external_bindings(entry: Mapping[str, Any], names: tuple[str, ...]) -> dict[str, str]:
    bindings = dict(entry.get("port_bindings", {}))
    unknown = sorted(set(bindings) - set(names))
    if unknown:
        raise SoCAssemblyError(
            f"unsupported top port binding for {entry['instance']}: {', '.join(unknown)}"
        )
    return {name: str(bindings.get(name, name)) for name in names}


def render_soc(document: Mapping[str, Any], instances: tuple[dict[str, Any], ...]) -> SoCBuild:
    """Validate and render the supported CPU→ROM/RAM/APB fabric profile.

    Address windows, instance names, GPIO width, source versions and top ports
    come from the frozen document and content lock. Unsupported topology fails
    before any source file is written.
    """
    if document.get("design_kind") != "single_clock_soc":
        raise SoCAssemblyError("SoC assembly requires a single_clock_soc specification")
    try:
        adapter = gpio_output_adapter(document)
    except SoCAdapterError as exc:
        raise SoCAssemblyError(str(exc)) from exc
    if len(document.get("clocks", [])) != 1 or len(document.get("resets", [])) != 1:
        raise SoCAssemblyError("SoC assembly supports exactly one clock and reset")
    clock = str(document["clocks"][0]["name"])
    reset = str(document["resets"][0]["name"])
    by_capability: dict[str, dict[str, Any]] = {}
    by_name: dict[str, dict[str, Any]] = {}
    for entry in instances:
        name = str(entry["instance"])
        capability = str(entry.get("capability", ""))
        if name in by_name or capability in by_capability:
            raise SoCAssemblyError(f"duplicate SoC instance or capability: {name}, {capability}")
        if capability not in {*SOC_PACKAGE_TOPS, *_MEMORY_CAPABILITIES, "generated-rtl"}:
            raise SoCAssemblyError(f"unsupported SoC capability: {capability}")
        if capability in SOC_PACKAGE_TOPS and not supports_soc_package(
            capability, str(entry["top_module"]),
        ):
            raise SoCAssemblyError(f"unsupported pin contract: {name}")
        if capability in _MEMORY_CAPABILITIES and entry.get("kind") != "generated":
            raise SoCAssemblyError(f"memory {name} must use frozen generated RTL")
        by_capability[capability] = entry
        by_name[name] = entry
    required = {"rv32i-cpu", "native-apb-bridge", *_MEMORY_CAPABILITIES}
    if not required <= set(by_capability):
        raise SoCAssemblyError(
            "SoC assembly requires one CPU, native/APB bridge, ROM and register RAM"
        )
    cpu = by_capability["rv32i-cpu"]
    bridge = by_capability["native-apb-bridge"]
    rom = by_capability["program-rom"]
    ram = by_capability["register-ram"]
    peripherals = [
        entry for entry in instances if entry["capability"] in _PERIPHERAL_CAPABILITIES
    ]
    if not peripherals:
        raise SoCAssemblyError("SoC APB bridge needs at least one peripheral")
    if adapter:
        child = by_capability.get("generated-rtl")
        if (
            child is None or child.get("kind") != "generated_rtl"
            or child.get("instance") != adapter["instance"]
            or child.get("top_module") != adapter["module"]
        ):
            raise SoCAssemblyError("GPIO 适配器与锁定的生成子模块不一致")
    if cpu.get("parameters", {}).get("ENABLE_IRQ") != 0:
        raise SoCAssemblyError("current PicoRV32 assembly supports ENABLE_IRQ=0 only")
    windows: dict[str, tuple[int, int]] = {}
    for window in document.get("address_windows", []):
        name = str(window["instance"])
        base, size = _number(window["base"]), _number(window["size"])
        if name in windows or not (0 <= base < 2**32) or not (0 < size < 2**32 - base):
            raise SoCAssemblyError(f"invalid or duplicate address window: {name}")
        windows[name] = (base, size)
    addressable = [rom, ram, *peripherals]
    if set(windows) != {item["instance"] for item in addressable}:
        raise SoCAssemblyError("address windows must cover exactly the memory and APB instances")
    ordered = sorted((base, base + size, name) for name, (base, size) in windows.items())
    for left, right in zip(ordered, ordered[1:]):
        if left[1] > right[0]:
            raise SoCAssemblyError(f"overlapping address windows: {left[2]}, {right[2]}")
    for memory in (rom, ram):
        base, size = windows[memory["instance"]]
        if base != memory["base"] or size != memory["size_bytes"]:
            raise SoCAssemblyError(f"generated memory window differs from lock: {memory['instance']}")
    if windows[rom["instance"]][0] != 0:
        raise SoCAssemblyError("PicoRV32 reset vector 0 must map to the program ROM")
    apb_base = windows[peripherals[0]["instance"]][0] & ~0xFFF
    if apb_base + 4096 >= 2**32:
        raise SoCAssemblyError("APB aperture exceeds the 32-bit address space")
    for entry in peripherals:
        base, size = windows[entry["instance"]]
        if not (apb_base <= base and base + size <= apb_base + 4096):
            raise SoCAssemblyError("APB peripherals must fit one aligned 4 KiB aperture")
        if size > 4096 or base % 4 or size % 4:
            raise SoCAssemblyError(f"unsupported APB window alignment: {entry['instance']}")
    for memory in (rom, ram):
        base, size = windows[memory["instance"]]
        if base < apb_base + 4096 and apb_base < base + size:
            raise SoCAssemblyError("APB aperture overlaps a memory window")

    declared_ports = {item["name"]: item for item in document.get("ports", [])}
    expected_ports: dict[str, tuple[str, int]] = {
        clock: ("input", 1), reset: ("input", 1),
        "irq_o": ("output", len(peripherals)),
        "trap_o": ("output", 1), "bus_fault_o": ("output", 1),
    }
    external: dict[str, dict[str, str]] = {}
    if "apb-gpio" in by_capability:
        gpio = by_capability["apb-gpio"]
        width = gpio.get("parameters", {}).get("GPIO_WIDTH")
        if type(width) is not int or width not in {8, 16, 32}:
            raise SoCAssemblyError("GPIO width must be a qualified 8, 16 or 32 bits")
        if gpio.get("parameters", {}).get("ADDR_WIDTH") != 12:
            raise SoCAssemblyError("GPIO APB address width must match the 12-bit bridge")
        binding = _external_bindings(gpio, ("gpio_i", "gpio_o", "gpio_oe"))
        external[gpio["instance"]] = binding
        expected_ports.update({
            binding["gpio_i"]: ("input", width),
            binding["gpio_o"]: ("output", width),
            binding["gpio_oe"]: ("output", width),
        })
    if "apb-uart" in by_capability:
        uart = by_capability["apb-uart"]
        binding = _external_bindings(uart, ("uart_rx_i", "uart_tx_o"))
        external[uart["instance"]] = binding
        expected_ports.update({
            binding["uart_rx_i"]: ("input", 1),
            binding["uart_tx_o"]: ("output", 1),
        })
    if set(declared_ports) != set(expected_ports):
        raise SoCAssemblyError(
            "SoC top ports differ from supported clock/reset/peripheral/IRQ contract"
        )
    for name, (direction, width) in expected_ports.items():
        declaration = declared_ports[name]
        if declaration.get("direction") != direction or declaration.get("width", 1) != width:
            raise SoCAssemblyError(f"SoC top port direction or width mismatch: {name}")
    if len(expected_ports) != 5 + sum(len(value) for value in external.values()):
        raise SoCAssemblyError("multiple SoC signals bind the same top port")

    port_lines = []
    for port in document["ports"]:
        direction = port["direction"]
        width = port.get("width", 1)
        vector = "" if width == 1 else f"[{width - 1}:0] "
        port_lines.append(f"    {direction} logic {vector}{port['name']}")
    lines = [
        "// Generated from frozen CSIR and exact IP/content lock. Do not edit.",
        f"module {document['name']} (",
        ",\n".join(port_lines),
        ");",
        "    logic mem_valid, mem_instr, mem_ready;",
        "    logic [31:0] mem_addr, mem_wdata, mem_rdata;",
        "    logic [3:0] mem_wstrb;",
        "    logic rom_select, ram_select, apb_select, unmapped_select;",
        "    logic [31:0] rom_read_data, ram_read_data;",
        "    logic bridge_ready, bridge_fault;",
        "    logic [31:0] bridge_rdata;",
        "    logic [11:0] apb_addr;",
        "    logic [2:0] apb_prot;",
        "    logic apb_sel, apb_enable, apb_write;",
        "    logic [31:0] apb_wdata, apb_rdata;",
        "    logic [3:0] apb_strb;",
        "    logic apb_ready, apb_error;",
    ]
    for entry in peripherals:
        name = entry["instance"]
        lines.extend([
            f"    logic {name}_sel, {name}_ready, {name}_error, {name}_irq;",
            f"    logic [31:0] {name}_rdata;",
            f"    logic [11:0] {name}_local_addr;",
        ])
    if adapter:
        lines.append(
            f"    logic [{adapter['width'] - 1}:0] {adapter['raw_signal']};"
        )
    lines.extend([
        f"    {cpu['top_module']}{_parameters(cpu)} {cpu['instance']} (",
        f"        .clk({clock}), .resetn({reset}), .trap(trap_o),",
        "        .mem_valid(mem_valid), .mem_instr(mem_instr), .mem_ready(mem_ready),",
        "        .mem_addr(mem_addr), .mem_wdata(mem_wdata),",
        "        .mem_wstrb(mem_wstrb), .mem_rdata(mem_rdata),",
        "        .pcpi_wr(1'b0), .pcpi_rd(32'b0), .pcpi_wait(1'b0),",
        "        .pcpi_ready(1'b0), .irq(32'b0)",
        "    );",
    ])
    for memory, signal in ((rom, "rom"), (ram, "ram")):
        base, size = windows[memory["instance"]]
        lines.append(
            f"    assign {signal}_select = mem_valid && mem_addr >= {_hex32(base)} "
            f"&& mem_addr < {_hex32(base + size)};"
        )
    lines.extend([
        f"    assign apb_select = mem_valid && mem_addr >= {_hex32(apb_base)} "
        f"&& mem_addr < {_hex32(apb_base + 4096)};",
        "    assign unmapped_select = mem_valid && !rom_select && !ram_select && !apb_select;",
        "    assign mem_ready = rom_select || ram_select || unmapped_select ||",
        "                       (apb_select && bridge_ready);",
        "    assign mem_rdata = rom_select && mem_wstrb == 0 ? rom_read_data :",
        "                       ram_select && mem_wstrb == 0 ? ram_read_data :",
        "                       apb_select ? bridge_rdata : 32'b0;",
        f"    {rom['top_module']} {rom['instance']} (",
        f"        .byte_addr(mem_addr - {_hex32(windows[rom['instance']][0])}),",
        "        .read_data(rom_read_data)",
        "    );",
        f"    {ram['top_module']} {ram['instance']} (",
        f"        .clk({clock}), .resetn({reset}),",
        f"        .byte_addr(mem_addr - {_hex32(windows[ram['instance']][0])}),",
        "        .write_enable(mem_valid && ram_select && |mem_wstrb),",
        "        .write_strobes(mem_wstrb), .write_data(mem_wdata),",
        "        .read_data(ram_read_data)",
        "    );",
        f"    always_ff @(posedge {clock} or negedge {reset}) begin",
        f"        if (!{reset}) bus_fault_o <= 1'b0;",
        "        else if ((rom_select && |mem_wstrb) || unmapped_select || bridge_fault)",
        "            bus_fault_o <= 1'b1;",
        "    end",
        f"    {bridge['top_module']} {bridge['instance']} (",
        f"        .clk({clock}), .resetn({reset}),",
        "        .mem_valid(apb_select), .mem_instr(mem_instr),",
        "        .mem_ready(bridge_ready), .mem_addr(mem_addr),",
        "        .mem_wdata(mem_wdata), .mem_wstrb(mem_wstrb),",
        "        .mem_rdata(bridge_rdata), .fault_o(bridge_fault),",
        "        .PADDR(apb_addr), .PPROT(apb_prot), .PSEL(apb_sel),",
        "        .PENABLE(apb_enable), .PWRITE(apb_write),",
        "        .PWDATA(apb_wdata), .PSTRB(apb_strb),",
        "        .PREADY(apb_ready), .PRDATA(apb_rdata), .PSLVERR(apb_error)",
        "    );",
    ])
    connections: list[dict[str, Any]] = [
        {"from": cpu["instance"], "to": entry["instance"],
         "protocol": "PicoRV32-native", "base": windows[entry["instance"]][0],
         "size": windows[entry["instance"]][1]}
        for entry in (rom, ram)
    ]
    connections.append({
        "from": cpu["instance"], "to": bridge["instance"],
        "protocol": "PicoRV32-native", "base": apb_base, "size": 4096,
    })
    for entry in peripherals:
        name = entry["instance"]
        base, size = windows[name]
        offset = base - apb_base
        lines.extend([
            f"    assign {name}_sel = apb_sel && apb_addr >= {_hex12(offset)}"
            + (f" && apb_addr < {_hex12(offset + size)}" if offset + size < 4096 else "")
            + ";",
            f"    assign {name}_local_addr = apb_addr - {_hex12(offset)};",
        ])
        port_lines = [
            f".PCLK({clock})", f".PRESETn({reset})",
            f".PADDR({name}_local_addr)", ".PPROT(apb_prot)",
            f".PSEL({name}_sel)", ".PENABLE(apb_enable)",
            ".PWRITE(apb_write)", ".PWDATA(apb_wdata)",
            ".PSTRB(apb_strb)", f".PREADY({name}_ready)",
            f".PRDATA({name}_rdata)", f".PSLVERR({name}_error)",
        ]
        if entry["capability"] in {"apb-gpio", "apb-uart"}:
            port_lines.extend(
                f".{port}({adapter['raw_signal'] if adapter and entry['capability'] == 'apb-gpio' and port == 'gpio_o' else target})"
                for port, target in external[name].items()
            )
        port_lines.append(f".irq_o({name}_irq)")
        lines.extend([
            f"    {entry['top_module']}{_parameters(entry)} {name} (",
            "        " + ",\n        ".join(port_lines),
            "    );",
        ])
        connections.append({
            "from": bridge["instance"], "to": name, "protocol": "APB4",
            "base": base, "size": size, "local_offset": offset,
            "irq_bit": peripherals.index(entry),
        })
    if adapter:
        lines.extend([
            f"    {adapter['module']} {adapter['instance']} (",
            f"        .{adapter['input_port']}({adapter['raw_signal']}),",
            f"        .{adapter['output_port']}({adapter['top_output']})",
            "    );",
        ])
        connections.append({
            "from": adapter["gpio_instance"], "to": adapter["instance"],
            "protocol": "gpio-output-vector", "width": adapter["width"],
        })
    def response(field: str, fallback: str) -> str:
        return " : ".join(
            [f"{entry['instance']}_sel ? {entry['instance']}_{field}" for entry in peripherals]
            + [fallback]
        )
    lines.extend([
        "    assign apb_ready = " + response("ready", "1'b1") + ";",
        "    assign apb_rdata = " + response("rdata", "32'b0") + ";",
        "    assign apb_error = " + response("error", "apb_sel && apb_enable") + ";",
        "    assign irq_o = {" + ", ".join(
            f"{entry['instance']}_irq" for entry in reversed(peripherals)
        ) + "};",
        "endmodule",
        "",
    ])
    return SoCBuild("\n".join(lines), tuple(connections))


def render_soc_verification(
    document: Mapping[str, Any], instances: tuple[dict[str, Any], ...],
) -> str:
    """Emit commands for independent frozen checkers, never a generated checker."""
    runner = document.get("acceptance_runner")
    if runner is not None:
        path = PurePosixPath(runner) if isinstance(runner, str) else PurePosixPath(".")
        if (
            not isinstance(runner, str) or not runner
            or any(char in runner for char in "\x00\n\r\\")
            or path.is_absolute() or path.as_posix() != runner
            or any(part in {".", ".."} for part in path.parts)
            or runner not in document.get("acceptance_sources", [])
        ):
            raise SoCAssemblyError("independent SoC acceptance runner is not frozen")
        by_capability = {item["capability"]: item for item in instances}
        if not {"program-rom", "register-ram"} <= set(by_capability):
            raise SoCAssemblyError("independent SoC runner needs locked ROM and RAM")
        exports = {
            "NEBULA_SOC_MODULE": str(document["name"]),
            "NEBULA_ROM_MODULE": str(by_capability["program-rom"]["top_module"]),
            "NEBULA_RAM_MODULE": str(by_capability["register-ram"]["top_module"]),
        }
        return "\n".join([
            "#!/usr/bin/env bash", "set -euo pipefail",
            'cd "$(dirname "${BASH_SOURCE[0]}")/.."',
            *(f"export {name}={shlex.quote(value)}" for name, value in exports.items()),
            "bash -- " + shlex.quote(runner),
            "",
        ])
    required = {
        "tb/nebula_soc_tb.sv", "tb/nebula_fabric_tb.sv",
        "tb/nebula_peripheral_tb.sv", "tb/rv32i_integer_tb.sv",
        "tb/nebula_memory_tb.sv", "firmware/isa_regression.hex",
        "tb/run_cpu_isa.sh", "tb/cpu_isa/isa_tb.sv",
        "tb/cpu_isa/system/system_tb.sv", "tb/cpu_isa/cases.txt",
        "tb/cpu_isa/system/cases.txt",
    }
    missing = required - set(document.get("acceptance_sources", []))
    if missing:
        raise SoCAssemblyError(
            "frozen SoC acceptance sources are missing: " + ", ".join(sorted(missing))
        )
    by_capability = {item["capability"]: item for item in instances}
    rom = by_capability["program-rom"]["top_module"]
    ram = by_capability["register-ram"]["top_module"]
    return "\n".join([
        "#!/usr/bin/env bash",
        "set -euo pipefail",
        'cd "$(dirname "${BASH_SOURCE[0]}")/.."',
        "mkdir -p build/chip-nebula-assembly",
        "run_case() {",
        '    local top="$1" bench="$2" label="$3"',
        "    shift 3",
        '    local output="build/chip-nebula-assembly/${label}"',
        '    iverilog -g2012 -s "$top" "$@" -o "$output" -f integration/nebula.f "$bench" > "${output}.compile.log" 2>&1 || { cat "${output}.compile.log"; return 1; }',
        '    vvp -n "$output" 2>&1 | tee "${output}.simulation.log"',
        "}",
        "run_case nebula_soc_tb tb/nebula_soc_tb.sv firmware "
        f"-DNEBULA_SOC_MODULE={document['name']}",
        "run_case nebula_fabric_tb tb/nebula_fabric_tb.sv fabric "
        f"-DNEBULA_SOC_MODULE={document['name']}",
        "run_case nebula_peripheral_tb tb/nebula_peripheral_tb.sv peripheral",
        "run_case rv32i_integer_tb tb/rv32i_integer_tb.sv cpu-directed",
        "run_case nebula_memory_tb tb/nebula_memory_tb.sv memory "
        f"-DROM_MODULE={rom} -DRAM_MODULE={ram}",
        "bash tb/run_cpu_isa.sh",
        "echo SOC_ASSEMBLY_CHECKS_PASSED",
        "",
    ])
