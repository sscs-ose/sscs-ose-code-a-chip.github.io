#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# network resnet18

import os, json, math
import torch
import torch.nn as nn
import torch.nn.functional as F
from torchvision import datasets, transforms
from torch.utils.data import DataLoader
from torch.optim.lr_scheduler import CosineAnnealingLR

class Cfg:
    data_root = '/home/junyiluo/projects/Quant/data'
    device = 'cuda' if torch.cuda.is_available() else 'cpu'

    # data & train
    batch_sz = 128
    num_workers = 4
    num_classes = 100
    epochs = 200
    lr = 1e-3
    eta_min = 1e-4     

    # io
    out_dir = './runs_fp32'
    ckpt = 'resnet18_cifar100_fp32.pt'
    hist = 'history_fp32.json'



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



# FP32 ResNet-18 (CIFAR版)
def conv3x3(ic, oc, s=1, bias=False):
    return nn.Conv2d(ic, oc, kernel_size=3, stride=s, padding=1, bias=bias)

class BasicBlock(nn.Module):
    expansion = 1
    def __init__(self, in_planes, planes, stride=1):
        super().__init__()
        self.conv1 = conv3x3(in_planes, planes, stride, bias=False)
        self.bn1   = nn.BatchNorm2d(planes)
        self.conv2 = conv3x3(planes, planes, 1, bias=False)
        self.bn2   = nn.BatchNorm2d(planes)
        self.down  = None
        if stride != 1 or in_planes != planes:
            self.down = nn.Sequential(
                nn.Conv2d(in_planes, planes, kernel_size=1, stride=stride, bias=False),
                nn.BatchNorm2d(planes)
            )

    def forward(self, x):
        out = F.relu(self.bn1(self.conv1(x)), inplace=True)
        out = self.bn2(self.conv2(out))
        residual = x if self.down is None else self.down(x)
        out = F.relu(out + residual, inplace=True)
        return out

class ResNet18CIFAR(nn.Module):
    def __init__(self, num_classes=100):
        super().__init__()
        self.conv1 = conv3x3(3, 64, 1, bias=False)  # CIFAR用3x3/stride1
        self.bn1 = nn.BatchNorm2d(64)
        self.layer1 = self._make_layer(64,  64, 2, 1)
        self.layer2 = self._make_layer(64, 128, 2, 2)
        self.layer3 = self._make_layer(128,256, 2, 2)
        self.layer4 = self._make_layer(256,512, 2, 2)
        self.pool = nn.AdaptiveAvgPool2d(1)
        self.fc = nn.Linear(512, num_classes)

    def _make_layer(self, in_planes, planes, blocks, stride):
        layers = [BasicBlock(in_planes, planes, stride)]
        for _ in range(1, blocks):
            layers.append(BasicBlock(planes, planes, 1))
        return nn.ModuleList(layers)

    def forward(self, x):
        out = F.relu(self.bn1(self.conv1(x)), inplace=True)
        for blk in self.layer1: out = blk(out)
        for blk in self.layer2: out = blk(out)
        for blk in self.layer3: out = blk(out)
        for blk in self.layer4: out = blk(out)
        out = self.pool(out).view(out.size(0), -1)
        return self.fc(out)


# Train / Eval
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
    return loss_sum/tot, cor/tot

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
    return loss_sum/tot, cor/tot


# Main
def main():
    cfg = Cfg()
    os.makedirs(cfg.out_dir, exist_ok=True)
    train_loader, test_loader = get_loaders_cifar100(cfg)
    model = ResNet18CIFAR(num_classes=cfg.num_classes).to(cfg.device)

    # opt = torch.optim.Adam(model.parameters(), lr=cfg.lr)
    opt = torch.optim.SGD(
        model.parameters(), lr=0.1, momentum=0.9, weight_decay=5e-4, nesterov=True
    )
    # scheduler = CosineAnnealingLR(opt, T_max=cfg.epochs, eta_min=cfg.eta_min)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=cfg.epochs, eta_min=cfg.eta_min)

    history = {"train_loss": [], "train_acc": [], "test_loss": [], "test_acc": []}
    for ep in range(1, cfg.epochs + 1):
        tr_loss, tr_acc = train_one_epoch(model, train_loader, opt, cfg.device)
        te_loss, te_acc = evaluate(model, test_loader, cfg.device)

        history["train_loss"].append(tr_loss); history["train_acc"].append(tr_acc)
        history["test_loss"].append(te_loss);  history["test_acc"].append(te_acc)

        cur_lr = opt.param_groups[0]['lr']
        print(f'[FP32 {ep:03d}] lr {cur_lr:.2e} | train {tr_loss:.4f}/{tr_acc*100:.2f}% | '
              f'test {te_loss:.4f}/{te_acc*100:.2f}%')

        scheduler.step()

    torch.save(model.state_dict(), os.path.join(cfg.out_dir, cfg.ckpt))
    with open(os.path.join(cfg.out_dir, cfg.hist), 'w') as f:
        json.dump(history, f)

    te_loss, te_acc = evaluate(model, test_loader, cfg.device)
    print(f'FP32 final: loss {te_loss:.4f}, acc {te_acc*100:.2f}%')

if __name__ == '__main__':
    main()
