import torch

from torch.nn.utils.rnn import pad_sequence
from torch.utils.data import DataLoader, sampler


def padding_sequence(batch):
    """ Make all tensor in a batch the same length by padding with zeros
    Args:   
        batch: tuple of tensors
    Returns:
        Padded tensors and tensor of lengths
    """
    batch = [item.t() for item in batch]
    batch = pad_sequence(batch, batch_first=True, padding_value=0.)
    return batch.permute(0, 2, 1)


def custom_collate(batch):
    """
    
    """
    tensors, targets = [], []

    for audio, label in batch:
        tensors += [audio]
        targets += [label]

    tensors = padding_sequence(tensors)
    targets = torch.stack(targets)

    return tensors, targets


def genSampler(subDataset):
    y = torch.stack([subDataset[i][1] for i in range(len(subDataset))])
    class_sample_count = torch.unique(y, return_counts=True)[1]
    # print("Class Sample Count:", class_sample_count)
    weight = 1. / class_sample_count
    # print("Class Weight:", weight)
    samples_weight = weight[y]

    balance_sampler = sampler.WeightedRandomSampler(
        samples_weight, len(samples_weight)
    )
    return balance_sampler, weight


def genDataLoader(
    dataset,
    batch_size,
    collate_fn=custom_collate,
    sampler="balanced",
    num_workers=0,
    pin_memory=False,
):
    print("\nGetting Data... \n")
    trainDataset = dataset["train"]
    validDataset = dataset["val"]
    testDataset = dataset["test"]

    print("Batch Size:", batch_size)
    print(
        "\nTrain Len =", len(trainDataset), 
        ", Validation Len =", len(validDataset), 
        ", Test Len =", len(testDataset)
    )

    # Create train dataloader
    if sampler == "balanced":
        print("\nBalanced sampler is used for trainloader.")
        train_sampler,_ = genSampler(trainDataset)
        trainloader = DataLoader(
            trainDataset,
            batch_size=batch_size,
            shuffle=False,
            sampler=train_sampler,
            collate_fn=collate_fn,
            num_workers=num_workers,
            drop_last=True,
            pin_memory=pin_memory,
        )
    else:
        print("\nBalanced sampler is not used for trainloader.")
        trainloader = DataLoader(
            trainDataset,
            batch_size=batch_size,
            shuffle=True,
            collate_fn=collate_fn,
            num_workers=num_workers,
            drop_last=True,
            pin_memory=pin_memory,
        )

    # Create validation and test dataloaders
    print("Shuffle is False for validloader.")
    validloader = DataLoader(
        validDataset,
        batch_size=batch_size,
        shuffle=False,
        collate_fn=collate_fn,
        num_workers=num_workers,
        drop_last=True,
        pin_memory=pin_memory,
    )

    print("Shuffle is False for testloader.")
    testloader = DataLoader(
        testDataset,
        batch_size=batch_size,
        shuffle=False,
        collate_fn=collate_fn,
        num_workers=num_workers,
        drop_last=True,
        pin_memory=pin_memory,
    )

    print("")
    print(
        "Train Size Batched =", len(trainloader),
        ", Validation Size Batched =", len(validloader),
        ", Test Size Batched =", len(testloader),
    )
    
    return {"train": trainloader, "val": validloader, "test": testloader}
