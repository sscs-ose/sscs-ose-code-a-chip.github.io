#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""使用 LUTQuantConv2d 手写构建 ResNet-20，并从 QAT 权重复制尺度继续推理评估。"""

import os
import time
from dataclasses import dataclass

import torch
import torch.nn as nn
from torch.utils.data import DataLoader, Subset
from torchvision import datasets, transforms

from resnet20_lut import ResNet20LUTCfg, build_lut_resnet20, resolve_lut_table


@dataclass
class Cfg(ResNet20LUTCfg):
    test_subset: int | None = None
    lut_table_path: str | None = '/home/junyi/projects/Quant/code/lut/truth_table_0.5.csv'
    qat_ckpt: str = '/home/junyi/projects/Quant/runs_qat/resnet20/resnet20_cifar100_qat_int8_lut_0.5_ft.pt'
    # lut_table_path: str | None = None


def get_test_loader(cfg: Cfg) -> DataLoader:
    mean = [0.5071, 0.4865, 0.4409]
    std = [0.2673, 0.2564, 0.2762]
    test_tf = transforms.Compose([
        transforms.ToTensor(),
        transforms.Normalize(mean, std),
    ])
    test_set = datasets.CIFAR100(cfg.data_root, train=False, download=True, transform=test_tf)
    if cfg.test_subset is not None and cfg.test_subset < len(test_set):
        indices = torch.arange(cfg.test_subset)
        test_set = Subset(test_set, indices)
    return DataLoader(test_set, batch_size=cfg.batch_sz, shuffle=False,
                      num_workers=cfg.num_workers, pin_memory=True)




@torch.no_grad()
def evaluate(model: nn.Module, loader: DataLoader, device: str) -> tuple[float, float, float]:
    model.eval()
    total = 0
    correct = 0
    total_loss = 0.0
    criterion = nn.CrossEntropyLoss()

    if device.startswith('cuda'):
        torch.cuda.synchronize()
    t0 = time.time()
    total_batches = len(loader)
    for step, (x, y) in enumerate(loader, 1):
        x = x.to(device)
        y = y.to(device)
        logits = model(x)
        loss = criterion(logits, y)
        total_loss += loss.item() * x.size(0)
        pred = logits.argmax(dim=1)
        correct += (pred == y).sum().item()
        total += x.size(0)
        if step % max(1, total_batches // 10) == 0 or step == total_batches:
            print(f'[Eval] processed {step}/{total_batches} batches...')
    if device.startswith('cuda'):
        torch.cuda.synchronize()
    elapsed = time.time() - t0
    avg_loss = total_loss / max(total, 1)
    acc = correct / max(total, 1)
    return avg_loss, acc, elapsed


def main():
    cfg = Cfg()
    device = cfg.device
    torch.backends.cudnn.benchmark = True

    if cfg.lut_table_path is not None:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        resolve_lut_table(cfg, base_dir)
        print(f'[Info] Loaded LUT truth table: {cfg.lut_table_path}')

    print('[Info] Building LUT ResNet-20 and loading QAT checkpoint...')
    print(f'[Info] Using checkpoint at: {cfg.qat_ckpt}')
    model = build_lut_resnet20(cfg).to(device)

    print('[Info] Preparing CIFAR-100 test set...')
    test_loader = get_test_loader(cfg)

    print('[Info] Starting evaluation...')
    loss, acc, elapsed = evaluate(model, test_loader, device)
    samples = len(test_loader.dataset)
    print(f'[Result] test_loss={loss:.4f}, test_acc={acc*100:.2f}%, time={elapsed:.2f}s, throughput={samples/elapsed:.1f} samples/s')


if __name__ == '__main__':
    main()
