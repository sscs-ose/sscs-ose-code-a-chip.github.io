"""Deterministic IP materialization and SystemVerilog assembly generation."""

from __future__ import annotations

import hashlib
import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from chip_nebula.taskgraph.ip_library import IPLibrary, IPLibraryError, supports_generic_named_port
from chip_nebula.taskgraph.memory_generator import MemoryGenerator
from chip_nebula.taskgraph.generated_submodule import (
    GeneratedSubmoduleError, source_record, submodule_contract,
)
from chip_nebula.taskgraph.soc_assembly import (
    SoCAssemblyError, render_soc, render_soc_verification,
    supports_soc_package,
)


class AssemblyError(ValueError):
    pass


@dataclass(frozen=True)
class AssemblyPlan:
    spec_digest: str
    lock_digest: str
    top_module: str
    instances: tuple[dict[str, Any], ...]
    connections: tuple[dict[str, Any], ...]
    generated_files: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "spec_digest": self.spec_digest,
            "lock_digest": self.lock_digest,
            "top_module": self.top_module,
            "instances": list(self.instances),
            "connections": list(self.connections),
            "generated_files": list(self.generated_files),
        }


class AssemblyService:
    def __init__(self, project_root: Path, library: IPLibrary) -> None:
        self.root = project_root.resolve()
        self.library = library
        self.integration_root = self.root / "integration"
        self.vendor_root = self.root / "ip" / "vendor"

    def verify_acceptance_contract(self, compiled_spec: Mapping[str, Any]) -> dict[str, Any]:
        """Bind a project-owned SoC checker to exactly the specification it covers."""
        document = compiled_spec.get("document", {})
        if document.get("design_kind") != "single_clock_soc":
            return {}
        relative = "tb/acceptance-contract.json"
        if relative not in document.get("acceptance_sources", []):
            raise AssemblyError("SoC 验收契约未列入冻结验收输入")
        path = self.root / relative
        if path.is_symlink() or not path.is_file():
            raise AssemblyError("SoC 验收契约缺失或不是工程内普通文件")
        try:
            contract = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise AssemblyError("SoC 验收契约不可读取或格式错误") from exc
        expected_checks = sorted(
            str(item["id"]) for item in compiled_spec.get("acceptance_plan", {}).get("checks", [])
        )
        if (
            not isinstance(contract, dict)
            or contract.get("schema_version") != 1
            or contract.get("spec_digest") != compiled_spec.get("spec_digest")
            or contract.get("check_ids") != expected_checks
            or contract.get("runner") != document.get("acceptance_runner")
        ):
            raise AssemblyError("独立 SoC checker 未审核当前规格版本；需更新验收并重新冻结")
        return contract

    def plan(self, compiled_spec: Mapping[str, Any], lock: Mapping[str, Any]) -> AssemblyPlan:
        if not compiled_spec.get("frozen") or not compiled_spec.get("valid"):
            raise AssemblyError("assembly requires a valid frozen specification")
        if lock.get("spec_digest") != compiled_spec.get("spec_digest"):
            raise AssemblyError("IP lock was resolved for a different specification")
        document = compiled_spec["document"]
        soc_mode = document.get("design_kind") == "single_clock_soc"
        generic_mode = document.get("design_kind") == "generic_module"
        by_name = {item["name"]: item for item in document.get("instances", [])}
        generated_instances = {
            item["name"] for item in document.get("instances", [])
            if item.get("capability") in {"program-rom", "register-ram"}
            and not item.get("package")
        }
        locked_generated = lock.get("generated_modules", [])
        locked_memory = [
            item for item in locked_generated if item.get("kind") == "generated"
        ]
        locked_children = [
            item for item in locked_generated if item.get("kind") == "generated_rtl"
        ]
        if len(locked_memory) + len(locked_children) != len(locked_generated):
            raise AssemblyError("IP lock contains an unsupported generated module kind")
        if generated_instances or locked_memory:
            current = MemoryGenerator(self.root).current(compiled_spec)
            expected = {
                item["instance"]: item for item in current["modules"]
            } if current else {}
            if (
                len(locked_memory) != len(generated_instances)
                or {item.get("instance") for item in locked_memory} != generated_instances
            ):
                raise AssemblyError("IP lock does not cover exactly the generated memory instances")
            for entry in locked_memory:
                item = expected.get(entry["instance"])
                if item is None or entry.get("generation_digest") != current["generation_digest"]:
                    raise AssemblyError("locked generated memory RTL is missing or changed")
                files = [item["rtl"]] + ([item["image"]] if item["image"] else [])
                source = by_name[entry["instance"]]
                if (
                    entry.get("kind") != "generated"
                    or entry.get("capability") != source.get("capability")
                    or entry.get("generator_version") != current["generator_version"]
                    or entry.get("base") != item["base"]
                    or entry.get("size_bytes") != item["size_bytes"]
                    or entry.get("top_module") != item["module"]
                    or entry.get("files") != files
                    or entry.get("file_hashes") != {
                        path: current["file_hashes"][path] for path in files
                    }
                ):
                    raise AssemblyError("locked generated memory RTL differs from frozen specification")
        specified_children = {
            item["name"] for item in document.get("instances", [])
            if isinstance(item, dict) and item.get("capability") == "generated-rtl"
        } if generic_mode or soc_mode else set()
        if (
            len(locked_children) != len(specified_children)
            or {item.get("instance") for item in locked_children} != specified_children
        ):
            raise AssemblyError("IP lock does not cover exactly the specified generated RTL children")
        for entry in locked_children:
            name = str(entry["instance"])
            try:
                contract = submodule_contract(compiled_spec, name)
                record = source_record(self.root, compiled_spec, name)
            except GeneratedSubmoduleError as exc:
                raise AssemblyError(str(exc)) from exc
            if (
                entry.get("top_module") != contract["module"]
                or entry.get("top_module") == document.get("name")
                or entry.get("capability") != "generated-rtl"
                or entry.get("spec_digest") != contract["spec_digest"]
                or entry.get("contract_digest") != record["contract_digest"]
                or entry.get("generation_digest") != record["generation_digest"]
                or entry.get("ports") != contract["ports"]
                or entry.get("parameters") != {}
                or entry.get("files") != record["files"]
                or entry.get("file_hashes") != record["file_hashes"]
            ):
                raise AssemblyError("locked generated child differs from frozen specification")
        instances: list[dict[str, Any]] = []
        for entry in lock.get("packages", []):
            if entry.get("kind") == "dependency" or not entry.get("instance"):
                continue
            source = by_name.get(entry.get("instance"))
            if source is None:
                raise AssemblyError(f"lock contains unknown instance {entry.get('instance')}")
            package = self.library.package_for_lock(entry)
            capability = str(source.get("capability", ""))
            if soc_mode:
                if not supports_soc_package(capability, str(entry["top_module"])):
                    raise AssemblyError(
                        f"package {package.key} has no supported SoC pin contract"
                    )
                instances.append({
                    **dict(entry), "capability": capability,
                    "port_bindings": dict(source.get("port_bindings", {})),
                    "vendor_dir": _vendor_directory(entry),
                })
            elif generic_mode:
                if not supports_generic_named_port(package.manifest):
                    raise AssemblyError(
                        f"package {package.key} has no complete generic named-port contract"
                    )
                if str(entry["top_module"]) == str(document["name"]):
                    raise AssemblyError("generic top module collides with a locked IP module")
                instances.append({
                    **dict(entry), "capability": capability,
                    "port_bindings": dict(source.get("port_bindings", {})),
                    "vendor_dir": _vendor_directory(entry),
                })
            else:
                generator = package.manifest.get("generator", {})
                if generator.get("kind") != "apb-gpio-wrapper-v1":
                    raise AssemblyError(
                        f"package {package.key} has no supported deterministic generator"
                    )
                instances.append({
                    **dict(entry),
                    "base": _window_base(document, str(entry["instance"])),
                    "window_size": _window_size(document, str(entry["instance"])),
                    "port_bindings": dict(source.get("port_bindings", {})),
                    "vendor_dir": _vendor_directory(entry),
                })
        if generic_mode or soc_mode:
            for entry in locked_children:
                source = by_name[entry["instance"]]
                instances.append({
                    **dict(entry),
                    "port_bindings": dict(source.get("port_bindings", {})),
                })
        if soc_mode:
            for entry in locked_memory:
                if entry["instance"] not in by_name:
                    raise AssemblyError(f"lock contains unknown instance {entry['instance']}")
                instances.append(dict(entry))
        if not instances:
            raise AssemblyError("assembly has no resolved IP instances")
        if {item["instance"] for item in instances} != set(by_name):
            raise AssemblyError("IP lock does not cover exactly the specified instances")
        if soc_mode:
            checker_root = self.root / "tb" / "cpu_isa"
            if not checker_root.is_dir():
                raise AssemblyError("frozen SoC CPU ISA acceptance directory is missing")
            checker_files = {
                path.relative_to(self.root).as_posix()
                for path in checker_root.rglob("*") if path.is_file()
            }
            frozen_sources = set(document.get("acceptance_sources", []))
            omitted = checker_files - frozen_sources
            if omitted:
                raise AssemblyError(
                    "CPU ISA acceptance input is not frozen: " + ", ".join(sorted(omitted))
                )
            try:
                connections = render_soc(document, tuple(instances)).connections
                render_soc_verification(document, tuple(instances))
            except SoCAssemblyError as exc:
                raise AssemblyError(str(exc)) from exc
        else:
            _validate_port_bindings(document, instances, generic=generic_mode)
            connections = (
                tuple(
                    {"instance": instance["instance"], "port": port,
                     "top_port": target}
                    for instance in instances
                    for port, target in sorted(instance["port_bindings"].items())
                ) if generic_mode else tuple(document.get("connections", []))
            )
        return AssemblyPlan(
            spec_digest=str(compiled_spec["spec_digest"]),
            lock_digest=str(lock["lock_digest"]),
            top_module=str(document["name"]),
            instances=tuple(instances),
            connections=connections,
            generated_files=(
                "integration/nebula_assembly.sv",
                "integration/nebula.f",
                "integration/nebula-assembly.json",
                *(("integration/nebula-verify.sh",) if soc_mode else ()),
            ),
        )

    def materialize(
        self, compiled_spec: Mapping[str, Any], lock: Mapping[str, Any]
    ) -> dict[str, Any]:
        plan = self.plan(compiled_spec, lock)
        document = compiled_spec["document"]
        if document.get("design_kind") == "single_clock_soc":
            try:
                top_text = render_soc(document, plan.instances).source
                verify_text = render_soc_verification(document, plan.instances)
            except SoCAssemblyError as exc:
                raise AssemblyError(str(exc)) from exc
        elif document.get("design_kind") == "generic_module":
            top_text = _generate_generic_top(document, plan)
            verify_text = ""
        else:
            top_text = _generate_apb_top(document, plan)
            verify_text = ""
        filelist_text = _render_filelist(lock)
        intended = {
            "integration/nebula_assembly.sv": top_text,
            "integration/nebula.f": filelist_text,
            **({"integration/nebula-verify.sh": verify_text} if verify_text else {}),
        }
        self._check_existing_assembly(intended)
        vendor_copies: list[tuple[Path, Path]] = []
        for entry in lock["packages"]:
            package = self.library.package_for_lock(entry)
            destination = self.root / _vendor_directory(entry)
            for file in package.manifest["files"]:
                relative = Path(file["path"])
                source = package.root / relative
                target = destination / relative
                if not target.parent.resolve().is_relative_to(self.root):
                    raise AssemblyError(f"vendor path escapes project: {target}")
                if target.is_symlink() or (target.exists() and not target.is_file()):
                    raise AssemblyError(f"vendor source is not a regular file: {target.relative_to(self.root)}")
                if target.exists() and _file_digest(target) != _file_digest(source):
                    raise AssemblyError(f"vendor source was modified: {target.relative_to(self.root)}")
                if not target.exists():
                    vendor_copies.append((source, target))
        for source, target in vendor_copies:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
        self.integration_root.mkdir(parents=True, exist_ok=True)
        for relative, content in intended.items():
            (self.root / relative).write_text(content, encoding="utf-8")
        record = plan.to_dict()
        record["assembly_digest"] = _digest({
            **record,
            "top_sha256": _file_digest(self.integration_root / "nebula_assembly.sv"),
            "filelist_sha256": _file_digest(self.integration_root / "nebula.f"),
            "verification_sha256": (
                _file_digest(self.integration_root / "nebula-verify.sh")
                if verify_text else ""
            ),
        })
        (self.integration_root / "nebula-assembly.json").write_text(
            json.dumps(record, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return record

    def _check_existing_assembly(self, intended: Mapping[str, str]) -> None:
        """Never replace user edits to generated integration files or their record."""
        if self.integration_root.is_symlink() or not self.integration_root.resolve().is_relative_to(self.root):
            raise AssemblyError("integration directory is linked outside the project")
        record_path = self.integration_root / "nebula-assembly.json"
        if record_path.is_symlink():
            raise AssemblyError("assembly record is a symbolic link")
        if record_path.exists():
            try:
                record = json.loads(record_path.read_text(encoding="utf-8"))
                keys = (
                    "schema_version", "spec_digest", "lock_digest", "top_module",
                    "instances", "connections", "generated_files",
                )
                old = {key: record[key] for key in keys}
                old_files = set(old["generated_files"])
                required = {
                    "integration/nebula_assembly.sv", "integration/nebula.f",
                    "integration/nebula-assembly.json",
                }
                allowed = required | {"integration/nebula-verify.sh"}
                if not required <= old_files or not old_files <= allowed:
                    raise ValueError("invalid generated file list")
                paths = {name: self.root / name for name in old_files}
                if any(path.is_symlink() or not path.is_file() for path in paths.values()):
                    raise ValueError("generated output is missing or linked")
                digest = _digest({
                    **old,
                    "top_sha256": _file_digest(paths["integration/nebula_assembly.sv"]),
                    "filelist_sha256": _file_digest(paths["integration/nebula.f"]),
                    "verification_sha256": (
                        _file_digest(paths["integration/nebula-verify.sh"])
                        if "integration/nebula-verify.sh" in paths else ""
                    ),
                })
            except (OSError, UnicodeError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
                raise AssemblyError("existing assembly record or output is invalid; source was not overwritten") from exc
            if digest != record.get("assembly_digest"):
                raise AssemblyError("assembled source was modified; source was not overwritten")
            for relative, content in intended.items():
                if relative in old_files:
                    continue
                path = self.root / relative
                if path.is_symlink() or (path.exists() and (
                    not path.is_file() or path.read_text(encoding="utf-8") != content
                )):
                    raise AssemblyError(f"existing integration file would be overwritten: {relative}")
        else:
            for relative, content in intended.items():
                path = self.root / relative
                if path.is_symlink() or (path.exists() and (
                    not path.is_file() or path.read_text(encoding="utf-8") != content
                )):
                    raise AssemblyError(f"existing integration file would be overwritten: {relative}")

    def verify_current(
        self, compiled_spec: Mapping[str, Any], lock: Mapping[str, Any],
    ) -> dict[str, Any]:
        """Reject any drift in the assembled top, filelist, script or inputs."""
        plan = self.plan(compiled_spec, lock)
        record_path = self.integration_root / "nebula-assembly.json"
        try:
            record = json.loads(record_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise AssemblyError("assembly record is missing or invalid") from exc
        if not isinstance(record, dict):
            raise AssemblyError("assembly record is missing or invalid")
        for key, expected in plan.to_dict().items():
            if record.get(key) != expected:
                raise AssemblyError(f"assembly record differs from current lock: {key}")
        top = self.integration_root / "nebula_assembly.sv"
        filelist = self.integration_root / "nebula.f"
        script = self.integration_root / "nebula-verify.sh"
        required = [top, filelist]
        if compiled_spec["document"].get("design_kind") == "single_clock_soc":
            required.append(script)
        if any(path.is_symlink() or not path.is_file() for path in required):
            raise AssemblyError("assembly output is missing or linked outside the project")
        document = compiled_spec["document"]
        try:
            expected_top = (
                render_soc(document, plan.instances).source
                if document.get("design_kind") == "single_clock_soc"
                else _generate_generic_top(document, plan)
                if document.get("design_kind") == "generic_module"
                else _generate_apb_top(document, plan)
            )
            expected_script = (
                render_soc_verification(document, plan.instances)
                if document.get("design_kind") == "single_clock_soc" else ""
            )
        except SoCAssemblyError as exc:
            raise AssemblyError(str(exc)) from exc
        if (
            top.read_text(encoding="utf-8") != expected_top
            or filelist.read_text(encoding="utf-8") != _render_filelist(lock)
            or (expected_script and script.read_text(encoding="utf-8") != expected_script)
        ):
            raise AssemblyError("assembled source or verification script has changed")
        digest = _digest({
            **plan.to_dict(),
            "top_sha256": _file_digest(top),
            "filelist_sha256": _file_digest(filelist),
            "verification_sha256": _file_digest(script) if expected_script else "",
        })
        if record.get("assembly_digest") != digest:
            raise AssemblyError("assembly digest does not match current outputs")
        changed = self.verify_vendor_integrity(lock)
        if changed:
            raise AssemblyError("locked source changed or is missing: " + ", ".join(changed[:5]))
        return record

    def verify_vendor_integrity(self, lock: Mapping[str, Any]) -> list[str]:
        violations: list[str] = []
        for entry in lock.get("packages", []):
            try:
                package = self.library.package_for_lock(entry)
            except IPLibraryError as exc:
                violations.append(str(exc))
                continue
            destination = self.root / _vendor_directory(entry)
            for item in package.manifest["files"]:
                expected = package.root / item["path"]
                actual = destination / item["path"]
                if not actual.is_file() or _file_digest(actual) != _file_digest(expected):
                    violations.append(str(actual.relative_to(self.root)))
        for entry in lock.get("generated_modules", []):
            for relative, digest in entry.get("file_hashes", {}).items():
                path = Path(relative)
                actual = self.root / path
                if (
                    path.is_absolute() or ".." in path.parts
                    or actual.is_symlink() or not actual.is_file()
                    or not actual.resolve().is_relative_to(self.root)
                    or "sha256:" + _file_digest(actual) != digest
                ):
                    violations.append(relative)
        return violations


def _render_filelist(lock: Mapping[str, Any]) -> str:
    filelist: list[str] = []
    for entry in lock["packages"]:
        vendor = Path(_vendor_directory(entry))
        file_types = entry.get("file_types", {})
        filelist.extend(
            f"+incdir+{(vendor / include_dir).as_posix()}"
            for include_dir in entry.get("include_dirs", [])
        )
        filelist.extend(f"+define+{define}" for define in entry.get("defines", []))
        for file in entry["files"]:
            kind = file_types.get(file, "")
            if kind in {"systemVerilogSource", "verilogSource"} or (
                not file_types and not file.startswith("tb/")
            ):
                filelist.append((vendor / file).as_posix())
    for entry in lock.get("generated_modules", []):
        filelist.extend(
            relative for relative in entry["files"] if relative.endswith(".sv")
        )
    filelist.append("integration/nebula_assembly.sv")
    return "\n".join(dict.fromkeys(filelist)) + "\n"


def _generate_generic_top(document: Mapping[str, Any], plan: AssemblyPlan) -> str:
    """Render a plain-pin wrapper with no inferred protocol or hidden logic."""
    ports = []
    for item in document.get("ports", []):
        width = item.get("width", 1)
        vector = "" if width == 1 else f"[{width}-1:0] "
        ports.append(f"{item['direction']} wire {vector}{item['name']}")
    lines = ["// Generated from frozen CSIR and an immutable IP lock. Do not edit."]
    parameters = document.get("parameters", [])
    if parameters:
        lines.extend([
            f"module {plan.top_module} #(",
            "    " + ",\n    ".join(
                f"parameter int {item['name']} = {item['default']}" for item in parameters
            ),
            ") (",
        ])
    else:
        lines.append(f"module {plan.top_module} (")
    lines.extend(["    " + ",\n    ".join(ports), ");"])
    for signal in document.get("internal_signals", []):
        width = signal.get("width", 1)
        vector = "" if width == 1 else f"[{width}-1:0] "
        lines.append(f"    wire {vector}{signal['name']};")
    for instance in plan.instances:
        values = instance.get("parameters", {})
        if values:
            lines.extend([
                f"    {instance['top_module']} #(",
                "        " + ",\n        ".join(
                    f".{name}({value['bind'] if isinstance(value, dict) else value})"
                    for name, value in sorted(values.items())
                ),
                f"    ) {instance['instance']} (",
            ])
        else:
            lines.append(f"    {instance['top_module']} {instance['instance']} (")
        lines.extend([
            "        " + ",\n        ".join(
                f".{port}({target})"
                for port, target in sorted(instance["port_bindings"].items())
            ),
            "    );",
        ])
    lines.extend(["endmodule", ""])
    return "\n".join(lines)


def _generate_apb_top(document: Mapping[str, Any], plan: AssemblyPlan) -> str:
    interface = next(
        (item for item in document.get("interfaces", []) if item.get("protocol") == "APB4"),
        None,
    )
    if interface is None:
        raise AssemblyError("APB assembly requires an APB4 interface")
    aw = int(interface["address_width"])
    dw = int(interface["data_width"])
    parameter = next(item for item in document.get("parameters", []) if item.get("name") == "GPIO_WIDTH")
    ports = [
        "input  logic PCLK",
        "input  logic PRESETn",
        f"input  logic [{aw - 1}:0] PADDR",
        "input  logic [2:0] PPROT",
        "input  logic PSEL",
        "input  logic PENABLE",
        "input  logic PWRITE",
        f"input  logic [{dw - 1}:0] PWDATA",
        f"input  logic [{dw // 8 - 1}:0] PSTRB",
        "output logic PREADY",
        f"output logic [{dw - 1}:0] PRDATA",
        "output logic PSLVERR",
    ]
    declared_ports = {item["name"]: item for item in document.get("ports", [])}
    for name, item in declared_ports.items():
        width = item.get("width", 1)
        vector = "" if width == 1 else f"[{width}-1:0] "
        ports.append(f"{item['direction']} logic {vector}{name}")
    lines = [
        "// Generated by Chip Nebula from a frozen CSIR and IP lock. Do not edit.",
        f"module {plan.top_module} #(",
        f"    parameter int GPIO_WIDTH = {parameter['default']}",
        ") (",
        "    " + ",\n    ".join(ports),
        ");",
        "    logic unused_pprot;",
        "    assign unused_pprot = ^PPROT;",
    ]
    response_terms: list[tuple[str, str, str]] = []
    multiple = len(plan.instances) > 1
    for index, instance in enumerate(plan.instances):
        suffix = f"_{index}"
        base = int(instance["base"])
        size = int(instance["window_size"])
        bindings = instance["port_bindings"]
        default_prefix = f"gpio{index}" if multiple else "gpio"
        gpio_i = bindings.get("gpio_i", f"{default_prefix}_i")
        gpio_o = bindings.get("gpio_o", f"{default_prefix}_o")
        gpio_oe = bindings.get("gpio_oe", f"{default_prefix}_oe")
        irq_o = bindings.get("irq_o", f"irq{index}_o" if multiple else "irq_o")
        for signal in (gpio_i, gpio_o, gpio_oe, irq_o):
            if signal not in declared_ports:
                raise AssemblyError(
                    f"instance {instance['instance']} binds undeclared top port {signal}"
                )
        parameter_bindings = []
        for parameter_name, value in instance.get("parameters", {}).items():
            expression = (
                str(value.get("bind"))
                if isinstance(value, dict) and value.get("bind")
                else str(value)
            )
            parameter_bindings.append(f"        .{parameter_name}({expression})")
        parameter_block = [f"    {instance['top_module']} #("]
        parameter_block.extend(
            f"{line}{',' if offset < len(parameter_bindings) - 1 else ''}"
            for offset, line in enumerate(parameter_bindings)
        )
        parameter_block.append(f"    ) {instance['instance']} (")
        lines.extend([
            f"    logic psel{suffix};",
            f"    logic pready{suffix};",
            f"    logic [{dw - 1}:0] prdata{suffix};",
            f"    logic pslverr{suffix};",
            f"    assign psel{suffix} = PSEL && (PADDR >= {aw}'h{base:X}) && (PADDR < {aw}'h{base + size:X});",
            *parameter_block,
            "        .PCLK(PCLK), .PRESETn(PRESETn),",
            f"        .PADDR(PADDR - {aw}'h{base:X}), .PPROT(PPROT),",
            f"        .PSEL(psel{suffix}), .PENABLE(PENABLE), .PWRITE(PWRITE),",
            "        .PWDATA(PWDATA), .PSTRB(PSTRB),",
            f"        .PREADY(pready{suffix}), .PRDATA(prdata{suffix}), .PSLVERR(pslverr{suffix}),",
            f"        .gpio_i({gpio_i}), .gpio_o({gpio_o}), .gpio_oe({gpio_oe}), .irq_o({irq_o})",
            "    );",
        ])
        response_terms.append((f"psel{suffix}", f"pready{suffix}", f"prdata{suffix}"))
    lines.extend([
        # Icarus 11 can enter a zero-time scheduling loop when several nested
        # generated wrappers use always_comb response muxes.  This block is
        # purely combinational; always @* has the same RTL meaning and avoids
        # that simulator bug for the two-instance reuse acceptance case.
        "    always @* begin",
        "        PREADY  = 1'b1;",
        "        PRDATA  = '0;",
        "        PSLVERR = PSEL;",
    ])
    for index, (select, ready, data) in enumerate(response_terms):
        keyword = "if" if index == 0 else "else if"
        lines.extend([
            f"        {keyword} ({select}) begin",
            f"            PREADY = {ready};",
            f"            PRDATA = {data};",
            f"            PSLVERR = pslverr_{index};",
            "        end",
        ])
    lines.extend(["    end", "endmodule", ""])
    return "\n".join(lines)


def _validate_port_bindings(
    document: Mapping[str, Any], instances: list[dict[str, Any]],
    *, generic: bool = False,
) -> None:
    top_ports = {
        str(item.get("name")): item
        for item in document.get("ports", []) if isinstance(item, dict)
    }
    internal = {
        str(item.get("name")): item
        for item in document.get("internal_signals", []) if isinstance(item, dict)
    } if generic else {}
    drivers: dict[str, str] = {}
    consumers: set[str] = set()
    multiple = len(instances) > 1
    for index, instance in enumerate(instances):
        declared = {
            str(item.get("name")): item
            for item in instance.get("ports", []) if isinstance(item, dict)
        }
        bindings = dict(instance.get("port_bindings", {}))
        unknown = sorted(set(bindings) - set(declared))
        if unknown:
            raise AssemblyError(
                f"instance {instance['instance']} has unknown port bindings: "
                + ", ".join(unknown)
            )
        if generic and set(bindings) != set(declared):
            missing = sorted(set(declared) - set(bindings))
            raise AssemblyError(
                f"instance {instance['instance']} has unbound ports: {', '.join(missing)}"
            )
        default_prefix = f"gpio{index}" if multiple else "gpio"
        defaults = {} if generic else {
            "gpio_i": f"{default_prefix}_i",
            "gpio_o": f"{default_prefix}_o",
            "gpio_oe": f"{default_prefix}_oe",
            "irq_o": f"irq{index}_o" if multiple else "irq_o",
        }
        for port_name, contract in declared.items():
            target = bindings.get(port_name, defaults.get(port_name, ""))
            if not isinstance(target, str) or target not in top_ports and target not in internal:
                raise AssemblyError(
                    f"instance {instance['instance']} port {port_name} is unconnected "
                    "or binds an undeclared top port/internal signal"
                )
            direction = contract.get("direction")
            if target in internal:
                if direction not in {"input", "output"}:
                    raise AssemblyError(
                        f"internal signal {target} does not support inout: "
                        f"{instance['instance']}.{port_name}"
                    )
                endpoint = internal[target]
            else:
                endpoint = top_ports[target]
                compatible = {
                    "input": {"input", "inout"},
                    "output": {"output", "inout"},
                    "inout": {"inout"},
                }
                if endpoint.get("direction") not in compatible.get(direction, set()):
                    raise AssemblyError(
                        f"direction mismatch for {instance['instance']}.{port_name} -> {target}"
                    )
            expected_width = _instance_port_width(contract.get("width", 1), instance)
            actual_width = endpoint.get("width", 1)
            if expected_width != actual_width:
                raise AssemblyError(
                    f"width mismatch for {instance['instance']}.{port_name}: "
                    f"{expected_width} != {actual_width}"
                )
            if direction in {"output", "inout"}:
                previous = drivers.get(target)
                if previous:
                    label = "internal signal" if target in internal else "top port"
                    raise AssemblyError(
                        f"{label} {target} has multiple drivers: {previous}, "
                        f"{instance['instance']}.{port_name}"
                    )
                drivers[target] = f"{instance['instance']}.{port_name}"
            elif target in internal:
                consumers.add(target)
    if generic:
        for name in internal:
            if name not in drivers:
                raise AssemblyError(f"internal signal {name} has no driver")
            if name not in consumers:
                raise AssemblyError(f"internal signal {name} has no receiver")
        used = {
            target for instance in instances
            for target in instance["port_bindings"].values()
        }
        unbound = sorted(set(top_ports) - used)
        if unbound:
            raise AssemblyError("generic top ports are unbound: " + ", ".join(unbound))


def _instance_port_width(value: Any, instance: Mapping[str, Any]) -> Any:
    if not isinstance(value, str):
        return value
    parameter = instance.get("parameters", {}).get(value)
    if isinstance(parameter, dict) and parameter.get("bind"):
        return str(parameter["bind"])
    return parameter


def _window(document: Mapping[str, Any], instance: str) -> Mapping[str, Any]:
    matches = [item for item in document.get("address_windows", []) if item.get("instance") == instance]
    if len(matches) != 1:
        raise AssemblyError(f"instance {instance} requires exactly one address window")
    return matches[0]


def _window_base(document: Mapping[str, Any], instance: str) -> int:
    return int(_window(document, instance)["base"])


def _window_size(document: Mapping[str, Any], instance: str) -> int:
    return int(_window(document, instance)["size"])


def _vendor_directory(entry: Mapping[str, Any]) -> str:
    package = str(entry["package_id"]).replace(":", "_")
    digest = str(entry["content_digest"]).removeprefix("sha256:")[:12]
    return f"ip/vendor/{package}_{entry['version']}_{digest}"


def _file_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _digest(value: Any) -> str:
    return "sha256:" + hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
