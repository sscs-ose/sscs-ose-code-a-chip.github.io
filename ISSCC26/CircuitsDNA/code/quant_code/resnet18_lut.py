#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Shared building blocks for CIFAR ResNet-18 using LUTQuantConv2d and LUTQuantLinear."""

from __future__ import annotations

import csv
import os
from dataclasses import dataclass, field

import torch
import torch.nn as nn
import torch.nn.functional as F

from sym_quant import QuantConv2d
from lut_quant_conv import LUTQuantConv2d
from lut_quant_linear import LUTQuantLinear


@dataclass
class ResNet18LUTCfg:
    data_root: str = '/home/junyi/projects/datasets'
    device: str = 'cuda' if torch.cuda.is_available() else 'cpu'
    batch_sz: int = 128
    num_workers: int = 4
    num_classes: int = 100
    qat_ckpt: str = '/home/junyi/projects/Quant/runs_qat/resnet18/resnet18_cifar100_qat_int8.pt'
    nbits_w: int = 8
    nbits_a: int = 8
    per_channel: bool = False
    quantize_input: bool = True
    quantize_output: bool = False
    lut_mini_batch: int = 0
    lut_mini_channels: int = 0
    lut_table_path: str | None = None
    lut_table: torch.Tensor | None = field(default=None, repr=False)
    test_subset: int | None = None


def load_lut_table_csv(path: str) -> torch.Tensor:
    if not os.path.isfile(path):
        raise FileNotFoundError(f'LUT CSV file not found: {path}')
    table = torch.zeros(256, 256, dtype=torch.int16)
    with open(path, 'r', newline='') as fp:
        reader = csv.DictReader(fp)
        if reader.fieldnames is None or not {'A', 'B', 'OUT'} <= set(reader.fieldnames):
            raise ValueError('LUT CSV missing required columns: expected A,B,OUT')
        count = 0
        for row in reader:
            a = int(row['A'])
            b = int(row['B'])
            out = int(row['OUT'])
            if not (-128 <= a <= 127 and -128 <= b <= 127):
                raise ValueError(f'LUT key out of int8 range: A={a}, B={b}')
            table[a + 128, b + 128] = out
            count += 1
    if count != 256 * 256:
        raise ValueError(f'LUT CSV row count mismatch: expected 65536 rows, got {count}')
    return table


def resolve_lut_table(cfg: ResNet18LUTCfg, base_dir: str | None = None) -> None:
    if cfg.lut_table_path is None:
        cfg.lut_table = None
        return
    lut_path = cfg.lut_table_path
    if not os.path.isabs(lut_path):
        base = base_dir if base_dir is not None else os.getcwd()
        lut_path = os.path.join(base, lut_path)
    cfg.lut_table = load_lut_table_csv(lut_path)
    cfg.lut_table_path = lut_path


def qconv3x3_lut(ic: int, oc: int, stride: int, cfg: ResNet18LUTCfg, *, bias: bool = False) -> QuantConv2d:
    mode = 'per_channel' if cfg.per_channel else 'per_tensor'
    return LUTQuantConv2d(
        ic,
        oc,
        kernel_size=3,
        stride=stride,
        padding=1,
        bias=bias,
        nbits_weight=cfg.nbits_w,
        nbits_act=cfg.nbits_a,
        weight_scale_mode=mode,
        quantize_input=cfg.quantize_input,
        quantize_output=cfg.quantize_output,
        mini_batch_size=cfg.lut_mini_batch,
        mini_channels=cfg.lut_mini_channels,
        lut_table=cfg.lut_table,
    )


class QBasicBlockLUT(nn.Module):
    expansion = 1

    def __init__(self, in_planes: int, planes: int, stride: int, cfg: ResNet18LUTCfg):
        super().__init__()
        self.conv1 = qconv3x3_lut(in_planes, planes, stride, cfg, bias=False)
        self.bn1 = nn.BatchNorm2d(planes)
        self.conv2 = qconv3x3_lut(planes, planes, 1, cfg, bias=False)
        self.bn2 = nn.BatchNorm2d(planes)
        self.down = None
        if stride != 1 or in_planes != planes:
            self.down = nn.Sequential(
                nn.Conv2d(in_planes, planes, kernel_size=1, stride=stride, bias=False),
                nn.BatchNorm2d(planes),
            )

    def forward(self, x: torch.Tensor, *, collect: bool = False) -> torch.Tensor:
        out = F.relu(self.bn1(self.conv1(x, collect=collect)), inplace=True)
        out = self.bn2(self.conv2(out, collect=collect))
        residual = x if self.down is None else self.down(x)
        return F.relu(out + residual, inplace=True)


class QResNet18CIFARLUT(nn.Module):
    def __init__(self, num_classes: int, cfg: ResNet18LUTCfg):
        super().__init__()
        self.cfg = cfg
        self.conv1 = qconv3x3_lut(3, 64, 1, cfg, bias=False)
        self.bn1 = nn.BatchNorm2d(64)
        self.layer1 = self._make_layer(64, 64, 2, 1, cfg)
        self.layer2 = self._make_layer(64, 128, 2, 2, cfg)
        self.layer3 = self._make_layer(128, 256, 2, 2, cfg)
        self.layer4 = self._make_layer(256, 512, 2, 2, cfg)
        self.pool = nn.AdaptiveAvgPool2d(1)
        self.fc = LUTQuantLinear(
            512,
            num_classes,
            bias=True,
            nbits_weight=cfg.nbits_w,
            nbits_act=cfg.nbits_a,
            quantize_input=cfg.quantize_input,
            quantize_output=cfg.quantize_output,
            lut_table=cfg.lut_table,
        )

    def _make_layer(self, in_planes: int, planes: int, blocks: int, stride: int, cfg: ResNet18LUTCfg):
        layers = [QBasicBlockLUT(in_planes, planes, stride, cfg)]
        for _ in range(1, blocks):
            layers.append(QBasicBlockLUT(planes, planes, 1, cfg))
        return nn.ModuleList(layers)

    def forward(self, x: torch.Tensor, *, collect: bool = False) -> torch.Tensor:
        out = F.relu(self.bn1(self.conv1(x, collect=collect)), inplace=True)
        for blk in self.layer1:
            out = blk(out, collect=collect)
        for blk in self.layer2:
            out = blk(out, collect=collect)
        for blk in self.layer3:
            out = blk(out, collect=collect)
        for blk in self.layer4:
            out = blk(out, collect=collect)
        out = self.pool(out).view(out.size(0), -1)
        return self.fc(out, collect=collect)


def load_qat_state(cfg: ResNet18LUTCfg) -> dict:
    if not cfg.qat_ckpt or not os.path.isfile(cfg.qat_ckpt):
        raise FileNotFoundError(f'QAT checkpoint not found: {cfg.qat_ckpt}')
    return torch.load(cfg.qat_ckpt, map_location='cpu')


def build_lut_resnet18(cfg: ResNet18LUTCfg) -> QResNet18CIFARLUT:
    model = QResNet18CIFARLUT(num_classes=cfg.num_classes, cfg=cfg)
    state = load_qat_state(cfg)
    missing, unexpected = model.load_state_dict(state, strict=False)
    if missing or unexpected:
        print(f'[load_state] missing={missing} unexpected={unexpected}')
    return model


__all__ = [
    'ResNet18LUTCfg',
    'load_lut_table_csv',
    'resolve_lut_table',
    'QResNet18CIFARLUT',
    'build_lut_resnet18',
    'load_qat_state',
]
