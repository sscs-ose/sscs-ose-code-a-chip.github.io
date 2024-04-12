import itertools
import numpy as np
import matplotlib.pyplot as plt 


SMALL_SIZE = 12
MEDIUM_SIZE = 16
BIGGER_SIZE = 20

plt.rc('font', size=SMALL_SIZE)          # controls default text sizes
plt.rc('axes', titlesize=SMALL_SIZE)     # fontsize of the axes title
plt.rc('axes', labelsize=MEDIUM_SIZE)    # fontsize of the x and y labels
plt.rc('axes', linewidth=1.5)              # linewidth of the axes
plt.rc('xtick', labelsize=SMALL_SIZE)    # fontsize of the tick labels
plt.rc('ytick', labelsize=SMALL_SIZE)    # fontsize of the tick labels
plt.rc('legend', fontsize=SMALL_SIZE)    # legend fontsize
plt.rc('figure', titlesize=BIGGER_SIZE)  # fontsize of the figure title

# Comment if using Colab
plt.rcParams["font.family"] = "Arial"

def plot_confusion_matrix(
    cm, 
    classes,
    normalize=False,
    title='Confusion matrix',
    cmap=plt.cm.Blues
):
    """  

    """
    print('Visualizing...')
    if normalize: 
        count = cm.sum(axis=1)[:, np.newaxis]
        nonzero_count = np.where(count!=0, count, count+1)
        cm = cm.astype('float') / nonzero_count
        print("Normalized confusion matrix\n")
    else:
        print('Confusion matrix, without normalization\n')
    
    plt.figure(figsize=(8,8))
    plt.imshow(cm, interpolation='nearest', cmap=cmap)
    plt.title(title, fontsize = 20, weight='bold')
    cbar = plt.colorbar(fraction=0.046)
    cbar.ax.tick_params(labelsize=16)   
    tick_marks = np.arange(len(classes))
    plt.xticks(tick_marks, classes.values(), rotation=45, fontsize = 14, weight='bold')
    plt.yticks(tick_marks, classes.values(), fontsize = 14, weight='bold')
    
    fmt = '.2f' if normalize else 'd'
    thresh = cm.max() / 2.
    for i, j in itertools.product(range(cm.shape[0]), range(cm.shape[1])):
        plt.text(j, i, format(cm[i, j], fmt),
                 horizontalalignment="center",
                 color="white" if cm[i, j] > thresh else "black",
                 fontsize = 14)

    plt.tight_layout()
    plt.ylabel('True Class', fontsize = 16, labelpad=-18, weight='bold')
    plt.xlabel('Predicted Class', fontsize = 16, labelpad=-10, weight='bold')


def plot_twinx_fig(
    loss, 
    acc, 
    validation=True
):
    """ 

    """
    fig, ax1 = plt.subplots(figsize=(7, 5))
    ax1_color = "tab:blue"
    ax1.set_ylabel('Loss', color=ax1_color)
    ax1.tick_params(axis='y', labelcolor=ax1_color)
    ax1.plot(loss[0::2], color=ax1_color, label="train_loss")
    if validation == True:
        ax1.plot(loss[1::2], '--', color=ax1_color, label="validation_loss")
    
    ax2 = ax1.twinx()

    ax2_color = "tab:red"
    ax2.set_ylabel('Accuracy', color=ax2_color)
    ax2.tick_params(axis='y', labelcolor=ax2_color)
    ax2.plot(acc[0::2], color=ax2_color, label="train_acc")
    if validation == True:
        ax2.plot(acc[1::2], '--', color=ax2_color, label="validation_acc")

    ax2.set_title("Loss and Accuracy", fontsize = 20)
    fig.tight_layout()
    fig.legend(loc = 5, bbox_to_anchor=(0.85, 0.55), prop={'size':14})
    plt.show()


def plot_snr(
    snr_dict,
):
    """

    """
    plt.figure(figsize=(7, 5))
    if "clean" in snr_dict:
        plt.axhline(y=snr_dict["clean"], color='r', linestyle='--', label="clean")
        snr_dict.pop("clean")
    plt.plot(snr_dict.keys(), snr_dict.values(), 'o-', label="noisy")
    plt.xticks(list(snr_dict.keys()))
    plt.xlabel("SNR")
    plt.ylabel("Accuracy")
    plt.title("Accuracy vs SNR", fontsize = 20)
    plt.legend(loc="lower right")
    plt.grid(linestyle='--')
    plt.show()