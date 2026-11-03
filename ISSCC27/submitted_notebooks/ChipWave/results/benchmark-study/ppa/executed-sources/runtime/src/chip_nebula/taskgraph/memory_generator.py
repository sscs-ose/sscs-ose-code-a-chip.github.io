"""Deterministic, versioned ROM/RAM RTL from a frozen single-clock CSIR."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path, PurePosixPath
from typing import Any, Mapping


class MemoryGenerationError(ValueError):
    pass


def _sha256(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def _digest(value: Any) -> str:
    return _sha256(json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
    ).encode("utf-8"))


class MemoryGenerator:
    """Generate only the supported 32-bit ROM and reset-cleared register RAM."""

    def __init__(self, project_root: Path) -> None:
        self.root = project_root.resolve()

    def _source(self, relative: str) -> bytes:
        path = PurePosixPath(relative)
        if (
            not relative or path.is_absolute() or path.as_posix() != relative
            or any(part in {".", ".."} for part in path.parts)
        ):
            raise MemoryGenerationError(f"ROM 镜像路径无效：{relative}")
        source = self.root / relative
        try:
            if source.resolve(strict=True) != source or not source.is_file():
                raise MemoryGenerationError(f"ROM 镜像必须是工程内普通文件：{relative}")
            return source.read_bytes()
        except OSError as exc:
            raise MemoryGenerationError(f"ROM 镜像不可读取：{relative}") from exc

    @staticmethod
    def _image_words(raw: bytes, capacity: int, relative: str) -> list[int]:
        try:
            lines = raw.decode("utf-8").splitlines()
        except UnicodeError as exc:
            raise MemoryGenerationError(f"ROM 镜像不是 UTF-8 文本：{relative}") from exc
        words: list[int] = []
        for line_number, line in enumerate(lines, 1):
            token = line.split("//", 1)[0].split("#", 1)[0].strip()
            if not token:
                continue
            if not re.fullmatch(r"[0-9a-fA-F]{1,8}", token):
                raise MemoryGenerationError(
                    f"ROM 镜像第 {line_number} 行不是单个 32 位十六进制字：{relative}"
                )
            words.append(int(token, 16))
            if len(words) > capacity:
                raise MemoryGenerationError(f"ROM 镜像超过 {capacity} 个字：{relative}")
        return words + [0] * (capacity - len(words))

    def render(self, spec: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, bytes]]:
        if not spec.get("valid") or not spec.get("frozen") or spec.get("integrity") is False:
            raise MemoryGenerationError("存储器生成需要有效且未被修改的冻结规格")
        document = spec.get("document", {})
        if document.get("design_kind") != "single_clock_soc":
            raise MemoryGenerationError("首期仅支持单时钟 SoC 的存储器生成")
        memories = document.get("memories", [])
        if not isinstance(memories, list) or not memories:
            raise MemoryGenerationError("冻结规格没有存储器定义")
        windows = {
            item["instance"]: item for item in document.get("address_windows", [])
            if isinstance(item, dict) and isinstance(item.get("instance"), str)
        }
        expected_hashes = document.get("acceptance_sources_hashes", {})
        inputs: list[dict[str, Any]] = []
        images: dict[str, bytes] = {}
        for memory in memories:
            instance = memory["instance"]
            kind = memory["kind"]
            size = memory["size_bytes"]
            if (
                not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", instance)
                or kind not in {"rom", "register_ram"}
                or type(size) is not int or not 4 <= size <= 65_536 or size % 4
                or memory.get("data_width") != 32
                or instance not in windows
                or int(str(windows[instance]["size"]), 0) != size
            ):
                raise MemoryGenerationError(f"存储器契约不受支持：{instance}")
            entry = {
                "instance": instance, "kind": kind, "size_bytes": size,
                "base": int(str(windows[instance]["base"]), 0),
            }
            if kind == "rom":
                relative = str(memory["image"])
                raw = self._source(relative)
                source_sha = _sha256(raw)
                if expected_hashes.get(relative) != source_sha:
                    raise MemoryGenerationError(
                        f"ROM 镜像未绑定冻结验收摘要或内容已变化：{relative}"
                    )
                words = self._image_words(raw, size // 4, relative)
                images[instance] = ("\n".join(f"{word:08x}" for word in words) + "\n").encode()
                entry.update({"source_image": relative, "source_sha256": source_sha})
            inputs.append(entry)
        inputs.sort(key=lambda item: item["instance"])
        # Verilator 4.x cannot elaborate the nonblocking array-reset loop
        # once register RAM grows beyond the reference 256 B configuration.
        # Keep the v1 bytes immutable; v2 uses a blocking reset assignment for
        # larger register arrays and receives a distinct content identity.
        generator_version = 2 if any(
            item["kind"] == "register_ram" and item["size_bytes"] > 256
            for item in inputs
        ) else 1
        identity = {
            "generator_version": generator_version,
            "spec_digest": str(spec["spec_digest"]),
            "acceptance_sources_digest": str(spec.get("acceptance_sources_digest", "")),
            "memories": inputs,
        }
        version = _digest(identity).removeprefix("sha256:")[:16]
        directory = f"generated/memory/{version}"
        files: dict[str, bytes] = {}
        modules: list[dict[str, Any]] = []
        for entry in inputs:
            instance = entry["instance"]
            module = f"chip_nebula_{instance}_{version}"
            relative = f"{directory}/{module}.sv"
            image = f"{directory}/{instance}.hex" if entry["kind"] == "rom" else ""
            if image:
                files[image] = images[instance]
                rtl = self._rom_rtl(module, entry["size_bytes"], images[instance])
            else:
                rtl = self._ram_rtl(
                    module, entry["size_bytes"], reset_blocking=generator_version >= 2,
                )
            files[relative] = rtl.encode("utf-8")
            modules.append({
                **entry, "module": module, "rtl": relative,
                "image": image, "image_sha256": _sha256(images[instance]) if image else "",
            })
        filelist = f"{directory}/memory.f"
        files[filelist] = ("\n".join(item["rtl"] for item in modules) + "\n").encode()
        hashes = {name: _sha256(data) for name, data in sorted(files.items())}
        record = {
            "schema_version": 1, **identity, "modules": modules,
            "filelist": filelist, "file_hashes": hashes,
        }
        record["generation_digest"] = _digest(record)
        manifest = f"{directory}/manifest.json"
        record["generated_files"] = sorted([*files, manifest])
        files[manifest] = (json.dumps(record, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()
        return record, files

    def materialize(self, spec: Mapping[str, Any]) -> dict[str, Any]:
        record, files = self.render(spec)
        try:
            for relative, data in files.items():
                target = self.root / relative
                if any(parent.is_symlink() for parent in (target, *target.parents) if parent != self.root):
                    raise MemoryGenerationError(f"生成目标不能经过符号链接：{relative}")
                if target.exists() and target.read_bytes() != data:
                    raise MemoryGenerationError(f"版本化存储器产物已被修改，拒绝覆盖：{relative}")
            for relative, data in files.items():
                target = self.root / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                if not target.exists():
                    target.write_bytes(data)
        except OSError as exc:
            raise MemoryGenerationError(f"版本化存储器产物不可写入：{exc}") from exc
        return record

    def current(self, spec: Mapping[str, Any]) -> dict[str, Any] | None:
        """Return the exact current bundle only when every generated byte matches."""
        try:
            record, files = self.render(spec)
        except MemoryGenerationError:
            return None
        try:
            if any(
                not (self.root / relative).is_file()
                or (self.root / relative).is_symlink()
                or (self.root / relative).read_bytes() != data
                for relative, data in files.items()
            ):
                return None
        except OSError:
            return None
        return {**record, "verification_status": "not_run"}

    def verify(self, record: Mapping[str, Any]) -> list[str]:
        violations: list[str] = []
        body = {
            key: value for key, value in record.items()
            if key not in {"generation_digest", "generated_files"}
        }
        if record.get("generation_digest") != _digest(body):
            violations.append("generation_digest")
        manifest = next(
            (name for name in record.get("generated_files", []) if name.endswith("/manifest.json")),
            "",
        )
        expected_manifest = (
            json.dumps(record, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
        ).encode()
        if not manifest or not (self.root / manifest).is_file() or (
            self.root / manifest
        ).read_bytes() != expected_manifest:
            violations.append(manifest or "manifest.json")
        for relative, expected in record.get("file_hashes", {}).items():
            source = self.root / relative
            if not source.is_file() or source.is_symlink() or _sha256(source.read_bytes()) != expected:
                violations.append(relative)
        return violations

    @staticmethod
    def _rom_rtl(module: str, size: int, image: bytes) -> str:
        words = image.decode("ascii").splitlines()
        init = "\n".join(
            f"        words[{index}] = 32'h{value};" for index, value in enumerate(words)
        )
        return (
            "// Generated from frozen CSIR and content-checked ROM image.\n"
            f"module {module} (\n"
            "    input  wire [31:0] byte_addr,\n"
            "    output wire [31:0] read_data\n"
            ");\n"
            f"    reg [31:0] words [0:{size // 4 - 1}];\n"
            "    initial begin\n"
            f"{init}\n"
            "    end\n"
            f"    assign read_data = (byte_addr < 32'd{size} && byte_addr[1:0] == 2'b00)\n"
            "        ? words[byte_addr >> 2] : 32'b0;\n"
            "endmodule\n"
        )

    @staticmethod
    def _ram_rtl(module: str, size: int, *, reset_blocking: bool = False) -> str:
        reset_assignment = "=" if reset_blocking else "<="
        return (
            "// Generated from frozen CSIR: asynchronous reset, byte-write register RAM.\n"
            f"module {module} (\n"
            "    input  wire clk,\n"
            "    input  wire resetn,\n"
            "    input  wire [31:0] byte_addr,\n"
            "    input  wire write_enable,\n"
            "    input  wire [3:0] write_strobes,\n"
            "    input  wire [31:0] write_data,\n"
            "    output wire [31:0] read_data\n"
            ");\n"
            f"    reg [31:0] words [0:{size // 4 - 1}];\n"
            f"    assign read_data = (byte_addr < 32'd{size} && byte_addr[1:0] == 2'b00)\n"
            "        ? words[byte_addr >> 2] : 32'b0;\n"
            "    integer word_index;\n"
            "    integer byte_index;\n"
            "    always @(posedge clk or negedge resetn) begin\n"
            "        if (!resetn) begin\n"
            f"            for (word_index = 0; word_index < {size // 4}; word_index = word_index + 1)\n"
            f"                words[word_index] {reset_assignment} 32'b0;\n"
            "        end else if (write_enable && byte_addr < "
            f"32'd{size} && byte_addr[1:0] == 2'b00) begin\n"
            "            for (byte_index = 0; byte_index < 4; byte_index = byte_index + 1)\n"
            "                if (write_strobes[byte_index])\n"
            "                    words[byte_addr >> 2][byte_index * 8 +: 8] <=\n"
            "                        write_data[byte_index * 8 +: 8];\n"
            "        end\n"
            "    end\n"
            "endmodule\n"
        )
