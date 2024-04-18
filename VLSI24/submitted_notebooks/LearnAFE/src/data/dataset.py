import torch
import random
import torchaudio
import torch.nn.functional as F

from tabulate import tabulate
from os.path import join, normpath
from torchaudio.datasets import SPEECHCOMMANDS
from torch.utils.data import Dataset, ConcatDataset


def label2idx(word, dict):
    """ Get key from dict
    Args:
        word: label
        dict: dictionary
    Returns:
        key: index of the label
    """
    for key, value in dict.items(): 
         if word == value: 
            return torch.tensor(key) 
    return ValueError(f"Label '{word}' not found in CLASSES.")


def idx2label(index, dict):
    """ Get label from dict
    Args:
        index: index of the label
        dict: dictionary
    Returns:
        word: label
    """
    if index in dict:
        return dict[index]
    else:
        raise ValueError(f"Index '{index}' not found in CLASSES.")


def load_list(filename, root_path):
    """

    """
    filepath = join(root_path, filename)
    with open(filepath) as fileobj:
        return [normpath(join(root_path, line.strip())) for line in fileobj]


def clip_noise(noise_list, noise_samples, clip_len):
    """

    """
    noises = []
    for i in range(len(noise_list)):
        noise, _ = torchaudio.load(noise_list[i]) 
        noise_len = noise.shape[1]

        for j in range(noise_samples):
            offset = random.randint(0, noise_len - clip_len)
            noises.append(noise[:, offset : offset + clip_len])

    return noises


class NoiseDataset(Dataset):
    """

    """
    def __init__(
        self,
        root_path,
        classes,
        noise_samples,
        clip_len,
    ):
        noise_list = load_list("noise_list.txt", root_path)
        self.noise_set = clip_noise(noise_list, noise_samples, clip_len) 
        self.classes = classes

    def __len__(self):
        return len(self.noise_set)

    def __getitem__(self, index):
        data = self.noise_set[index]
        label = "silence"
        return data, label2idx(label, self.classes)


class CommandSubset(SPEECHCOMMANDS):
    """

    """
    def __init__(self, subset: str = None, root_path: str = None):
        super().__init__("./", download=True)

        if root_path != self._path: 
            raise ValueError("root_path is not correct!")

        if subset == "validation":
            self._walker = load_list("validation_list.txt", self._path)
        elif subset == "testing":
            self._walker = load_list("testing_list.txt", self._path)
        elif subset == "training":
            excludes = load_list("validation_list.txt", self._path) + load_list("testing_list.txt", self._path)
            excludes = set(excludes)
            self._walker = [w for w in self._walker if w not in excludes]


class CommandDataset(Dataset):
    """

    """
    def __init__(
        self,
        subset,
        root_path,
        keywords,
        classes,
        pad_len,
    ):
        assert subset in ["training", "testing", "validation"], "INVALID SUBSET NAME"
        self.sub_set = CommandSubset(subset, root_path) 
        self.keywords = keywords
        self.classes = classes
        self.pad_len = (pad_len, pad_len)

    def __len__(self):
        return len(self.sub_set)

    def __getitem__(self, index):
        data = self.sub_set[index][0]
        pad_data = F.pad(data, self.pad_len, mode="constant", value=0)
        if self.sub_set[index][2] not in self.keywords:
            label = "unknown"
        else:
            label = self.sub_set[index][2]
        return pad_data, label2idx(label, self.classes)


def genDatasets(
    root_path,
    keywords,
    classes, 
    command_len,
    pad_len,
    silence_samples=600,
    silence_split=0.1,
    verbose=False,
):
    """

    """
    command_train = CommandDataset(
        subset="training", 
        root_path=root_path,
        keywords=keywords,
        classes=classes,
        pad_len=pad_len,
    )
    command_val = CommandDataset(
        subset="validation",
        root_path=root_path,
        keywords=keywords,
        classes=classes,
        pad_len=0,
    )
    command_test = CommandDataset(
        subset="testing",
        root_path=root_path,
        keywords=keywords,
        classes=classes,
        pad_len=0,
    )

    # create silence dataset
    val_test_len = int(silence_samples*silence_split)
    train_len = silence_samples - val_test_len*2    

    silence_train = NoiseDataset(
        root_path=root_path,
        classes=classes,
        noise_samples=train_len,
        clip_len=command_len + pad_len*2,
    )
    silence_val = NoiseDataset(
        root_path=root_path,
        classes=classes,
        noise_samples=val_test_len,
        clip_len=command_len,
    )
    silence_test = NoiseDataset(
        root_path=root_path,
        classes=classes,
        noise_samples=val_test_len,
        clip_len=command_len,
    )

    if verbose == True:
        table = [
            ["", "train", "val", "test"],
            ["command", len(command_train), len(command_val), len(command_test)],
            ["silence", len(silence_train), len(silence_val), len(silence_test)],
        ]
        print(tabulate(table, headers="firstrow", tablefmt="github"))
    
    return {
        "train": ConcatDataset([command_train, silence_train]), 
        "val": ConcatDataset([command_val, silence_val]), 
        "test": ConcatDataset([command_test, silence_test])
    }
