#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""在近似 LUT 乘法器下对 QAT ResNet-20 进行微调，以恢复精度。"""

import json
import os
import time
from dataclasses import dataclass

import torch
import torch.nn.functional as F
from torch.utils.data import DataLoader
from torchvision import datasets, transforms

from resnet20_lut import (
    QResNet20CIFARLUT,
    ResNet20LUTCfg,
    build_lut_resnet20,
    resolve_lut_table,
)


@dataclass
class Cfg(ResNet20LUTCfg):
    qat_ckpt: str = '/home/junyi/projects/Quant/runs_qat/resnet20/resnet20_cifar100_qat_int8.pt' # QAT weight path
    epochs: int = 20
    lr: float = 5e-4
    weight_decay: float = 1e-4
    momentum: float = 0.9
    nesterov: bool = True
    log_interval: int = 100
    eta_min: float = 1e-5
    output_dir: str = '/home/junyi/projects/Quant/runs_qat/resnet20'
    save_path: str | None = None
    resume_path: str | None = None
    history_path: str | None = None
    lut_table_path: str | None = '/home/junyi/projects/Quant/code/lut/truth_table_0.5.csv'  # approx LUT path


def get_loaders(cfg: Cfg) -> tuple[DataLoader, DataLoader]:
    mean = [0.5071, 0.4865, 0.4409]
    std = [0.2673, 0.2564, 0.2762]
    train_tf = transforms.Compose([
        transforms.RandomCrop(32, padding=4),
        transforms.RandomHorizontalFlip(),
        transforms.ToTensor(),
        transforms.Normalize(mean, std),
    ])
    test_tf = transforms.Compose([
        transforms.ToTensor(),
        transforms.Normalize(mean, std),
    ])
    train_set = datasets.CIFAR100(cfg.data_root, train=True, download=True, transform=train_tf)
    test_set = datasets.CIFAR100(cfg.data_root, train=False, download=True, transform=test_tf)
    train_loader = DataLoader(train_set, batch_size=cfg.batch_sz, shuffle=True,
                              num_workers=cfg.num_workers, pin_memory=True)
    test_loader = DataLoader(test_set, batch_size=cfg.batch_sz, shuffle=False,
                             num_workers=cfg.num_workers, pin_memory=True)
    return train_loader, test_loader


def infer_lut_tag(lut_path: str | None) -> str:
    if not lut_path:
        return 'exact'
    stem = os.path.splitext(os.path.basename(lut_path))[0]
    # 取最后一个下划线段，如 truth_table_0.5 -> 0.5
    candidate = stem.split('_')[-1] if '_' in stem else stem
    candidate = candidate.strip()
    return candidate or 'custom'


def train_one_epoch(model: QResNet20CIFARLUT, loader: DataLoader, optimizer: torch.optim.Optimizer,
                    device: str, log_interval: int) -> tuple[float, float]:
    model.train()
    total = 0
    correct = 0
    loss_sum = 0.0
    for step, (x, y) in enumerate(loader, 1):
        x = x.to(device)
        y = y.to(device)
        optimizer.zero_grad(set_to_none=True)
        logits = model(x)
        loss = F.cross_entropy(logits, y)
        loss.backward()
        optimizer.step()
        loss_sum += loss.item() * x.size(0)
        correct += (logits.argmax(dim=1) == y).sum().item()
        total += x.size(0)
        if step % max(1, log_interval) == 0:
            print(f'[Train] step={step:04d} loss={loss.item():.4f} acc={(correct/total)*100:.2f}%')
    return loss_sum / max(total, 1), correct / max(total, 1)


@torch.no_grad()
def evaluate(model: QResNet20CIFARLUT, loader: DataLoader, device: str) -> tuple[float, float]:
    model.eval()
    total = 0
    correct = 0
    loss_sum = 0.0
    for x, y in loader:
        x = x.to(device)
        y = y.to(device)
        logits = model(x)
        loss = F.cross_entropy(logits, y)
        loss_sum += loss.item() * x.size(0)
        correct += (logits.argmax(dim=1) == y).sum().item()
        total += x.size(0)
    return loss_sum / max(total, 1), correct / max(total, 1)


def build_model(cfg: Cfg) -> QResNet20CIFARLUT:
    model: QResNet20CIFARLUT
    if cfg.qat_ckpt and os.path.isfile(cfg.qat_ckpt):
        model = build_lut_resnet20(cfg)
    elif cfg.resume_path:
        print('[Warn] Initial QAT checkpoint not found, falling back to resume only.')
        model = QResNet20CIFARLUT(num_classes=cfg.num_classes, cfg=cfg)
    else:
        raise FileNotFoundError('Missing initial QAT weights; set cfg.qat_ckpt or provide resume_path')
    if cfg.resume_path and os.path.isfile(cfg.resume_path):
        print(f'[Info] Resume from {cfg.resume_path}')
        state = torch.load(cfg.resume_path, map_location='cpu')
        model.load_state_dict(state, strict=False)
    return model


def main() -> None:
    cfg = Cfg()
    device = cfg.device
    torch.backends.cudnn.benchmark = True

    if cfg.lut_table_path is not None:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        resolve_lut_table(cfg, base_dir)
        print(f'[Info] Loaded LUT table: {cfg.lut_table_path}')

    lut_tag = infer_lut_tag(cfg.lut_table_path)
    if cfg.save_path is None:
        cfg.save_path = os.path.join(cfg.output_dir, f'resnet20_cifar100_qat_int8_lut_{lut_tag}_ft.pt')
    if cfg.history_path is None:
        cfg.history_path = os.path.join(cfg.output_dir, f'history_ft_resnet20_lut_{lut_tag}.json')
    train_loader, test_loader = get_loaders(cfg)
    model = build_model(cfg).to(device)

    optimizer = torch.optim.SGD(
        model.parameters(), lr=cfg.lr, momentum=cfg.momentum,
        weight_decay=cfg.weight_decay, nesterov=cfg.nesterov,
    )
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
        optimizer, T_max=cfg.epochs, eta_min=cfg.eta_min
    )

    best_acc = 0.0
    history: dict[str, list[float]] = {
        'train_loss': [],
        'train_acc': [],
        'test_loss': [],
        'test_acc': [],
    }

    for epoch in range(1, cfg.epochs + 1):
        t0 = time.time()
        train_loss, train_acc = train_one_epoch(model, train_loader, optimizer, device, cfg.log_interval)
        test_loss, test_acc = evaluate(model, test_loader, device)
        scheduler.step()
        elapsed = time.time() - t0
        history['train_loss'].append(train_loss)
        history['train_acc'].append(train_acc)
        history['test_loss'].append(test_loss)
        history['test_acc'].append(test_acc)
        print(f"[Epoch {epoch:03d}] {elapsed:.1f}s | train {train_loss:.4f}/{train_acc*100:.2f}% | "
              f"test {test_loss:.4f}/{test_acc*100:.2f}% | lr={optimizer.param_groups[0]['lr']:.2e}")

        if test_acc > best_acc:
            best_acc = test_acc
            os.makedirs(os.path.dirname(cfg.save_path), exist_ok=True)
            torch.save(model.state_dict(), cfg.save_path)
        print(f'[Info] Saved new best model -> {cfg.save_path} (acc={best_acc*100:.2f}%)')

    print(f'[Done] Best test accuracy: {best_acc*100:.2f}%')

    os.makedirs(os.path.dirname(cfg.history_path), exist_ok=True)
    with open(cfg.history_path, 'w') as f:
        json.dump(history, f)
    print(f'[Info] Training history saved to {cfg.history_path}')


if __name__ == '__main__':
    main()
