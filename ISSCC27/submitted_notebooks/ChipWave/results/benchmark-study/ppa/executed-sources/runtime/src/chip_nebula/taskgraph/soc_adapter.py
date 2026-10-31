"""Checked insertion contract for a generated GPIO output adapter in a SoC.

The adapter transforms one public GPIO vector after the reviewed APB GPIO IP.
Its behavior comes from frozen CSIR; this module only fixes the connection
point and refuses unknown topology. Functional correctness remains the job of
an independently frozen integration checker.
"""

from __future__ import annotations

import re
from typing import Any, Mapping


_IDENTIFIER = re.compile(r"[A-Za-z_][A-Za-z0-9_$]*\Z")


class SoCAdapterError(ValueError):
    pass


def gpio_output_adapter(document: Mapping[str, Any]) -> dict[str, Any] | None:
    """Validate and describe the optional single-cycle GPIO output insertion."""
    if document.get("design_kind") != "single_clock_soc":
        return None
    instances = document.get("instances", [])
    if not isinstance(instances, list):
        raise SoCAdapterError("SoC instances must be a list")
    children = [
        item for item in instances if isinstance(item, Mapping)
        and item.get("capability") == "generated-rtl"
    ]
    if not children:
        return None
    if len(children) != 1:
        raise SoCAdapterError("首期 SoC 只支持一个生成型 GPIO 输出适配器")
    child = children[0]
    gpio = [
        item for item in instances if isinstance(item, Mapping)
        and item.get("capability") == "apb-gpio"
    ]
    if len(gpio) != 1:
        raise SoCAdapterError("GPIO 输出适配器需要唯一的已审核 APB GPIO 实例")
    owner = gpio[0]
    gpio_name = owner.get("name")
    parameters = owner.get("parameters", {})
    width = parameters.get("GPIO_WIDTH") if isinstance(parameters, Mapping) else None
    if (
        not isinstance(gpio_name, str) or not _IDENTIFIER.fullmatch(gpio_name)
        or type(width) is not int or width not in {8, 16, 32}
    ):
        raise SoCAdapterError("GPIO 输出适配器缺少受支持的 GPIO 实例与位宽")
    owner_bindings = owner.get("port_bindings", {})
    if not isinstance(owner_bindings, Mapping):
        raise SoCAdapterError("GPIO 顶层端口绑定无效")
    top_output = owner_bindings.get("gpio_o", "gpio_o")
    if not isinstance(top_output, str) or not _IDENTIFIER.fullmatch(top_output):
        raise SoCAdapterError("GPIO 顶层输出端口无效")
    top_ports = [
        port for port in document.get("ports", []) if isinstance(port, Mapping)
        and port.get("name") == top_output
    ]
    if len(top_ports) != 1 or top_ports[0].get("direction") != "output" or top_ports[0].get("width") != width:
        raise SoCAdapterError("适配后的 GPIO 顶层输出端口方向或位宽不匹配")
    if (
        child.get("integration_role") != "gpio-output-adapter"
        or child.get("addressable") is not False
        or child.get("package") or child.get("version")
        or child.get("parameters", {}) != {}
        or child.get("interface_ids")
    ):
        raise SoCAdapterError("生成型 GPIO 适配器必须是无地址、无 IP 包的精确连接实例")
    generated = child.get("generated_module")
    if not isinstance(generated, Mapping):
        raise SoCAdapterError("GPIO 适配器缺少生成模块契约")
    module = generated.get("name")
    if not isinstance(module, str) or not _IDENTIFIER.fullmatch(module) or module == document.get("name"):
        raise SoCAdapterError("GPIO 适配器模块名无效或与 SoC 顶层冲突")
    if generated.get("latency_cycles") != 0:
        raise SoCAdapterError("GPIO 输出适配器必须声明零周期组合转换")
    behavior = generated.get("behavior")
    if not isinstance(behavior, str) or not behavior.strip():
        raise SoCAdapterError("GPIO 适配器缺少可审查的行为说明")
    ids = generated.get("requirement_ids")
    confirmed = {
        item.get("id") for item in document.get("requirements", [])
        if isinstance(item, Mapping) and item.get("status") == "confirmed"
    }
    if (
        not isinstance(ids, list) or not ids
        or len(ids) != len(set(ids))
        or any(not isinstance(item, str) or item not in confirmed for item in ids)
    ):
        raise SoCAdapterError("GPIO 适配器必须关联已确认的功能需求")
    ports = generated.get("ports")
    if not isinstance(ports, list) or len(ports) != 2:
        raise SoCAdapterError("GPIO 适配器必须声明一个输入和一个输出")
    by_direction: dict[str, str] = {}
    for port in ports:
        if not isinstance(port, Mapping):
            raise SoCAdapterError("GPIO 适配器端口必须是对象")
        direction, name = port.get("direction"), port.get("name")
        if (
            direction not in {"input", "output"} or direction in by_direction
            or not isinstance(name, str) or not _IDENTIFIER.fullmatch(name)
            or type(port.get("width")) is not int or port["width"] != width
        ):
            raise SoCAdapterError("GPIO 适配器端口方向、名称或位宽无效")
        by_direction[direction] = name
    if set(by_direction) != {"input", "output"} or len(set(by_direction.values())) != 2:
        raise SoCAdapterError("GPIO 适配器需要不同名的输入与输出端口")
    bindings = child.get("port_bindings")
    if not isinstance(bindings, Mapping) or bindings != {
        by_direction["input"]: f"{gpio_name}.gpio_o",
        by_direction["output"]: top_output,
    }:
        raise SoCAdapterError("GPIO 适配器必须显式连接 APB GPIO 输出与顶层输出")
    raw_signal = f"{gpio_name}_raw_out"
    if any(
        isinstance(port, Mapping) and port.get("name") == raw_signal
        for port in document.get("ports", [])
    ):
        raise SoCAdapterError("GPIO 适配器内部信号与顶层端口重名")
    return {
        "instance": child["name"], "module": module,
        "gpio_instance": gpio_name, "width": width,
        "input_port": by_direction["input"], "output_port": by_direction["output"],
        "top_output": top_output, "raw_signal": raw_signal,
    }
