#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# network resnet18

import os, json
import torch
import torch.nn as nn
import torch.nn.functional as F
from torchvision import datasets, transforms
from torch.utils.data import DataLoader
from torch.optim.lr_scheduler import CosineAnnealingLR
from sym_quant import QuantConv2d, QuantLinear


# -----------------------------
# Config
# -----------------------------
class Cfg:
    data_root = '/home/junyi/projects/datasets'
    device = 'cuda' if torch.cuda.is_available() else 'cpu'

    # data & train
    batch_sz = 128
    num_workers = 4
    num_classes = 100

    warmup_epochs = 2
    calib_steps   = 20
    epochs_qat    = 200
    # optimizer (SGD)
    lr_qat     = 0.1
    momentum   = 0.9
    weight_decay = 5e-4
    nesterov   = True

    # scheduler (Cosine)
    eta_min    = 1e-4

    # Optional secondary calibration
    recalib       = False
    recalib_ratio = 0.7

    # Quantization parameters
    nbits_w = 8
    nbits_a = 8
    per_channel = False
    quantize_input  = True
    quantize_output = False

    # init
    fp32_ckpt = '/home/junyi/projects/Quant/runs_fp32/resnet18_cifar100_fp32.pt'

    # io
    out_dir = '/home/junyi/projects/Quant/runs_qat/resnet18'
    ckpt = 'resnet18_cifar100_qat_int8.pt'
    hist = 'history_qat_resnet18.json'


# -----------------------------
# Data: CIFAR-100
# -----------------------------
def get_loaders_cifar100(cfg: Cfg):
    mean = [0.5071, 0.4865, 0.4409]
    std  = [0.2673, 0.2564, 0.2762]

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

    train_set = datasets.CIFAR100(cfg.data_root, train=True,  download=True, transform=train_tf)
    test_set  = datasets.CIFAR100(cfg.data_root, train=False, download=True, transform=test_tf)
    train_loader = DataLoader(train_set, batch_size=cfg.batch_sz, shuffle=True,
                              num_workers=cfg.num_workers, pin_memory=True)
    test_loader  = DataLoader(test_set,  batch_size=cfg.batch_sz, shuffle=False,
                              num_workers=cfg.num_workers, pin_memory=True)
    return train_loader, test_loader


# -----------------------------
# Quant ResNet-18 (CIFAR variant)
# Only the main convs are quantized; the downsample 1x1 stays in float (can be replaced if needed)
# -----------------------------
def qconv3x3(ic, oc, s=1, cfg: Cfg=None, bias=False):
    return QuantConv2d(
        ic, oc, 3, stride=s, padding=1, bias=bias,
        nbits_weight=cfg.nbits_w, nbits_act=cfg.nbits_a,
        weight_scale_mode=('per_channel' if cfg.per_channel else 'per_tensor'),
        quantize_input=cfg.quantize_input, quantize_output=cfg.quantize_output
    )


def qlinear(in_features, out_features, cfg: Cfg=None, bias=True):
    return QuantLinear(
        in_features, out_features, bias=bias,
        nbits_weight=cfg.nbits_w, nbits_act=cfg.nbits_a,
        quantize_input=cfg.quantize_input, quantize_output=cfg.quantize_output,
        approx_w='round', approx_a='round'
    )


class QBasicBlock(nn.Module):
    expansion = 1

    def __init__(self, in_planes, planes, stride=1, cfg: Cfg=None):
        super().__init__()
        self.conv1 = qconv3x3(in_planes, planes, stride, cfg, bias=False)
        self.bn1   = nn.BatchNorm2d(planes)
        self.conv2 = qconv3x3(planes, planes, 1, cfg, bias=False)
        self.bn2   = nn.BatchNorm2d(planes)
        self.down  = None
        if stride != 1 or in_planes != planes:
            self.down = nn.Sequential(
                nn.Conv2d(in_planes, planes, kernel_size=1, stride=stride, bias=False),
                nn.BatchNorm2d(planes)
            )

    def forward(self, x, *, collect=False):
        out = F.relu(self.bn1(self.conv1(x, collect=collect)), inplace=True)
        out = self.bn2(self.conv2(out, collect=collect))
        residual = x if self.down is None else self.down(x)
        return F.relu(out + residual, inplace=True)


class QResNet18CIFAR(nn.Module):
    def __init__(self, num_classes=100, cfg: Cfg=None):
        super().__init__()
        self.cfg = cfg
        self.conv1 = qconv3x3(3, 64, 1, cfg, bias=False)
        self.bn1 = nn.BatchNorm2d(64)
        # self.maxpool = nn.MaxPool2d(kernel_size=3, stride=2, padding=1)  # EncodingNet reference; keep high-res stride-1 flow
        self.layer1 = self._make_layer(64, 64, 2, 1, cfg)
        self.layer2 = self._make_layer(64, 128, 2, 2, cfg)
        self.layer3 = self._make_layer(128,256, 2, 2, cfg)
        self.layer4 = self._make_layer(256,512, 2, 2, cfg)
        self.pool = nn.AdaptiveAvgPool2d(1)
        self.fc = qlinear(512, num_classes, cfg)

    def _make_layer(self, in_planes, planes, blocks, stride, cfg):
        layers = [QBasicBlock(in_planes, planes, stride, cfg)]
        for _ in range(1, blocks):
            layers.append(QBasicBlock(planes, planes, 1, cfg))
        return nn.ModuleList(layers)

    def forward(self, x, *, collect=False):
        out = F.relu(self.bn1(self.conv1(x, collect=collect)), inplace=True)
    # out = self.maxpool(out)  # CIFAR keeps 32x32 resolution; skip early downsampling
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


# -----------------------------
# Helpers: train / eval / calib / switches
# -----------------------------
def train_one_epoch(model, loader, opt, device):
    model.train()
    tot, cor, loss_sum = 0, 0, 0.0
    for x, y in loader:
        x, y = x.to(device), y.to(device)
        opt.zero_grad()
        logits = model(x)
        loss = F.cross_entropy(logits, y)
        loss.backward()
        opt.step()
        loss_sum += loss.item() * x.size(0)
        cor += (logits.argmax(1) == y).sum().item()
        tot += x.size(0)
    return loss_sum / tot, cor / tot


@torch.no_grad()
def evaluate(model, loader, device):
    model.eval()
    tot, cor, loss_sum = 0, 0, 0.0
    for x, y in loader:
        x, y = x.to(device), y.to(device)
        logits = model(x)
        loss = F.cross_entropy(logits, y)
        loss_sum += loss.item() * x.size(0)
        cor += (logits.argmax(1) == y).sum().item()
        tot += x.size(0)
    return loss_sum / tot, cor / tot


def set_activation_quant_enabled(model, in_enabled: bool, out_enabled: bool):
    for m in model.modules():
        if hasattr(m, 'quantize_input'):
            m.quantize_input = bool(in_enabled)
        if hasattr(m, 'quantize_output'):
            m.quantize_output = bool(out_enabled)


@torch.no_grad()
def calibrate_activations(model, loader, device, max_steps: int):
    model.eval()
    steps = 0
    for x, _ in loader:
        x = x.to(device)
        _ = model(x, collect=True)
        steps += 1
        if steps >= max_steps:
            break
    for m in model.modules():
        if hasattr(m, 'act_update'):
            m.act_update()
        if hasattr(m, 'reset_collector'):
            m.reset_collector()


@torch.no_grad()
def calibrate_weights(model: nn.Module):
    """
    This function runs a one-shot calibration for weights/biases, writing MSE-optimal scales into each QuantConv2d so that subsequent forwards quantize with fixed scales (no per-forward re-search).
    """
    num_layers = 0
    for m in model.modules():
        if hasattr(m, 'Wupdate') and callable(getattr(m, 'Wupdate')):
            m.Wupdate()
            num_layers += 1
        elif hasattr(m, 'Qupdate') and callable(getattr(m, 'Qupdate')):
            try:
                m.Qupdate('weight')
                num_layers += 1
            except TypeError:
                pass
    print(f'[Calib-W] calibrated {num_layers} quant conv layer(s).')


# -----------------------------
# Main
# -----------------------------
def main():
    cfg = Cfg()
    os.makedirs(cfg.out_dir, exist_ok=True)
    train_loader, test_loader = get_loaders_cifar100(cfg)
    model = QResNet18CIFAR(num_classes=cfg.num_classes, cfg=cfg).to(cfg.device)

    if cfg.fp32_ckpt and os.path.isfile(cfg.fp32_ckpt):
        sd = torch.load(cfg.fp32_ckpt, map_location='cpu')
        missing, unexpected = model.load_state_dict(sd, strict=False)
        print(f'load_state: missing={len(missing)} unexpected={len(unexpected)}')

    optimizer = torch.optim.SGD(
        model.parameters(),
        lr=cfg.lr_qat, momentum=cfg.momentum,
        weight_decay=cfg.weight_decay, nesterov=cfg.nesterov
    )

    total_epochs = cfg.warmup_epochs + cfg.epochs_qat
    scheduler = CosineAnnealingLR(optimizer, T_max=total_epochs, eta_min=cfg.eta_min)

    history = {"train_loss": [], "train_acc": [], "test_loss": [], "test_acc": []}

    set_activation_quant_enabled(model, in_enabled=False, out_enabled=False)
    print(f'[Warm-up] epochs={cfg.warmup_epochs}')
    for ep in range(1, cfg.warmup_epochs + 1):
        tr_loss, tr_acc = train_one_epoch(model, train_loader, optimizer, cfg.device)
        te_loss, te_acc = evaluate(model, test_loader, cfg.device)
        cur_lr = optimizer.param_groups[0]['lr']
        print(f'[W{ep:02d}] lr {cur_lr:.2e} | train {tr_loss:.4f}/{tr_acc*100:.2f}% | test {te_loss:.4f}/{te_acc*100:.2f}%')
        scheduler.step()

    calibrate_weights(model)

    set_activation_quant_enabled(model, in_enabled=cfg.quantize_input, out_enabled=cfg.quantize_output)
    print(f'[Calib-1] collecting {cfg.calib_steps} mini-batches...')
    calibrate_activations(model, train_loader, cfg.device, cfg.calib_steps)

    total_qat = cfg.epochs_qat
    re_ep = int(total_qat * cfg.recalib_ratio) if cfg.recalib else -1

    for ep in range(1, total_qat + 1):
        tr_loss, tr_acc = train_one_epoch(model, train_loader, optimizer, cfg.device)
        te_loss, te_acc = evaluate(model, test_loader, cfg.device)
        history["train_loss"].append(tr_loss)
        history["train_acc"].append(tr_acc)
        history["test_loss"].append(te_loss)
        history["test_acc"].append(te_acc)
        cur_lr = optimizer.param_groups[0]['lr']
        print(f'[QAT {ep:03d}] lr {cur_lr:.2e} | train {tr_loss:.4f}/{tr_acc*100:.2f}% | test {te_loss:.4f}/{te_acc*100:.2f}%')
        scheduler.step()

        if cfg.recalib and ep == re_ep:
            print(f'[Calib-2 @ QAT {ep}] collecting {cfg.calib_steps} mini-batches...')
            calibrate_activations(model, train_loader, cfg.device, cfg.calib_steps)

    torch.save(model.state_dict(), os.path.join(cfg.out_dir, cfg.ckpt))
    with open(os.path.join(cfg.out_dir, cfg.hist), 'w') as f:
        json.dump(history, f)

    te_loss, te_acc = evaluate(model, test_loader, cfg.device)
    print(f'INT8 final: loss {te_loss:.4f}, acc {te_acc*100:.2f}%')


if __name__ == '__main__':
    main()
