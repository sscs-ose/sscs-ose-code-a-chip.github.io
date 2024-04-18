import time
import torch
import numpy as np
import src.utils.visualizing as vs

from sklearn.metrics import balanced_accuracy_score


def calc_correct(output, Y):
    """Calculate the number of correct predictions."""
    pred = output.argmax(dim=-1)
    correct = pred.squeeze().eq(Y).sum().item()
    return correct


def train_model(
    device,
    dataloader,
    model,
    criterion,
    optimizer,
    scheduler,
    feature_transform,
    l1_reg=0.0,
    hdw_reg_i=0.0,
    hdw_reg_c=0.0,
    n_epochs=10,
    print_every=1,
    verbose=True,
    plot_results=True,
    strategy=["accuracy"],
):
    """ """
    best_dict = {}
    best_result = {}
    for item in strategy:
        best_result[item] = 0

    # Define the transforms and criterion
    train_transform = feature_transform["train"]
    val_transform = feature_transform["val"]
    train_criterion = criterion["train"]
    val_criterion = criterion["val"]

    print("\nTraining for {} epochs...".format(n_epochs))
    losses = []
    accs = []
    start = time.time()
    for epoch in range(n_epochs):
        if verbose == True and epoch % print_every == 0:
            print("\n\nEpoch {}/{}:".format(epoch + 1, n_epochs))

        ## TRAINING ##
        model.train()  # set model to training mode
        running_loss = 0.0
        correct = 0
        total = len(dataloader["train"].dataset)

        for batch_idx, (data, label) in enumerate(dataloader["train"]):
            data = data.to(device)
            label = label.to(device)

            # transform + forward + backward + optimize
            feature = train_transform(data)
            output = model(feature)

            # loss function w/o L1 regularization
            loss = train_criterion(output, label)
            if hdw_reg_c != 0 or hdw_reg_i != 0:
                hdw_para = torch.tensor(
                    [x.abs().sum() for x in model.bpf.parameters()]
                ).to(device)
                hdw_reg = torch.tensor([hdw_reg_i, hdw_reg_c]).to(device)
                hdw_norm = sum(torch.mul(hdw_reg, hdw_para))
                loss += hdw_norm
            if l1_reg != 0:
                l1_norm = sum(p.abs().sum() for p in model.backbone.parameters())
                loss += l1_reg * l1_norm

            optimizer.zero_grad()  # zero the parameter (weight) gradients
            loss.backward()  # backward pass
            optimizer.step()  # update the weights

            # record statistics
            running_loss += loss.item()
            correct += calc_correct(output, label)

        if verbose == True and epoch % print_every == 0:
            print(
                "Train loss: {:.4f} | acc: {:.4f}| ".format(
                    running_loss,
                    correct / total,
                ),
                end=" ",
            )
        losses.append(running_loss / (batch_idx + 1))
        accs.append(correct / total)

        ## VALIDATION ##
        model.eval()  # set model to evaluate mode
        val_loss = 0.0

        with torch.no_grad():
            truth = []
            preds = []
            for batch_idx, (data, label) in enumerate(dataloader["val"]):
                data = data.to(device)
                label = label.to(device)

                feature = val_transform(data)
                output = model(feature)

                loss = val_criterion(output, label)
                val_loss += loss.item()

                pred = output.argmax(dim=-1)
                preds.append(pred.cpu().numpy().tolist())
                truth.append(label.cpu().numpy().tolist())

            preds_flat = [item for sublist in preds for item in sublist]
            truth_flat = [item for sublist in truth for item in sublist]
            val_acc = balanced_accuracy_score(truth_flat, preds_flat)

            # update the scheduler
            if scheduler != None:
                scheduler.step(val_loss)

            if verbose == True and epoch % print_every == 0:
                print(
                    "Val loss: {:.4f} | acc: {:.4f}|".format(
                        val_loss,
                        val_acc,
                    ),
                    end=" ",
                )
            losses.append(val_loss / (batch_idx + 1))
            accs.append(val_acc)

        ## SAVE BEST MODEL
        val_results = {
            "accuracy": accs[-1],
            "loss": 1.0 / losses[-1],
        }

        for item in strategy:
            if val_results[item] > best_result[item]:
                best_result[item] = val_results[item]
                best_dict[item] = {
                    "epoch": epoch + 1,
                    "model_state_dict": model.state_dict(),
                    "optimizer_state_dict": optimizer.state_dict(),
                } | val_results

    if verbose == True:
        print("\nFinished Training  | Time:{}".format(time.time() - start))

    if plot_results == True:
        vs.plot_twinx_fig(losses, accs)

    return best_dict
