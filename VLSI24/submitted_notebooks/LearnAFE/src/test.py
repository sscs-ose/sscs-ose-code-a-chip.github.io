import torch

from sklearn.metrics import balanced_accuracy_score, classification_report


def test_model(
    device, 
    dataloader, 
    trained_model,  
    feature_transform, 
    verbose=False,
):
    """ Post Evaluation Metric Platfrom. Feed in the trained model

    """
    truth = []
    preds = []
    trained_model.eval()
    for data, label in dataloader:
        data, label = data.to(device), label.to(device)
        data = feature_transform(data)
        outputs = trained_model(data)
        _, predicted = torch.max(outputs, 1)
        preds.append(predicted.cpu().numpy().tolist())
        truth.append(label.cpu().numpy().tolist())

    preds_flat = [item for sublist in preds for item in sublist]
    truth_flat = [item for sublist in truth for item in sublist]
    accuracy = balanced_accuracy_score(truth_flat, preds_flat)

    if verbose == True:
        print("\nEvaluating....")
        print("Accuracy:", accuracy)
        print(classification_report(truth_flat, preds_flat))

    return accuracy, truth_flat, preds_flat