import torch
import torch.nn as nn
import torch.nn.functional as F


class DSCNN(nn.Module):
    def __init__(
        self,
        num_classes,
        in_channel=1,
    ):
        super(DSCNN, self).__init__()

        self.conv1 = nn.Conv2d(in_channel, 64, kernel_size=(3, 3))
        self.bn1 = nn.BatchNorm2d(64)
        self.layer1 = self._make_layer(64)
        self.layer2 = self._make_layer(64)
        self.layer3 = self._make_layer(64)
        self.layer4 = self._make_layer(64)
        self.bn2 = nn.BatchNorm2d(64)
        self.avgpool = nn.AdaptiveAvgPool2d((1, 1))
        self.fc = nn.Linear(64, num_classes)
        self.bn3 = nn.BatchNorm1d(num_classes)
        self.softmax = nn.LogSoftmax(dim=1)

    def _make_layer(self, channels):
        block = nn.Sequential(
            nn.Conv2d(channels, channels, kernel_size=3, groups=channels),
            nn.BatchNorm2d(channels),
            nn.ReLU(),
            nn.Conv2d(channels, channels, kernel_size=1),
            nn.BatchNorm2d(channels),
            nn.ReLU(),
        )
        return block
    
    def forward(self, x):
        x = F.relu(self.bn1(self.conv1(x)))
        x = self.layer1(x)
        x = self.layer2(x)
        x = self.layer3(x)
        x = self.layer4(x)
        x = self.bn2(self.avgpool(x))
        x = torch.flatten(x, 1)
        x = self.bn3(self.fc(x))
        x = self.softmax(x)
        return x