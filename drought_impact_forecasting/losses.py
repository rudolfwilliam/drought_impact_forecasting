import torch
from torch import nn
from torch.nn import functional as F
from tqdm import tqdm

def get_loss_from_name(loss_name):
    if loss_name == "l2":
        return L2_cube_loss()
    elif loss_name == "l2_discounted":
        return L2_disc_cube_loss()

class L2_cube_loss(nn.Module):
    def __init__(self):
        super().__init__()
    def forward(self, outputs, labels):
        mask = 1 - labels[:,0:1]
        masked_outputs = outputs * mask
        masked_labels = labels * mask
        l2_loss = nn.MSELoss()
        return l2_loss(masked_outputs, masked_labels)

class L2_disc_cube_loss(nn.Module):
    def __init__(self):
        super().__init__()
    def forward(self, outputs, labels):
        return 1

# Linearly anneal the LK loss weight for certain epochs
def kl_weight(epoch, finalWeight, annealStart, annealEnd):
    if epoch <= annealStart:
        return 0
    elif epoch > annealEnd:
        return finalWeight
    else:
        return finalWeight * (epoch - annealStart)/(annealEnd - annealStart)

# Add up (and weight) the different loss components
def base_line_total_loss(y_preds, batch_y, epoch, lambda1, lambda_kl_factor, annealStart, annealEnd):
    l1_criterion = nn.L1Loss() 
    kl_criterion = nn.KLDivLoss()
    GAN_criterion = nn.CrossEntropyLoss()
    VAE_GAN_Criterion = nn.CrossEntropyLoss()

    lambda_kl_final = lambda1 * lambda_kl_factor
    curlambda_kl = kl_weight(epoch, lambda_kl_final, annealStart, annealEnd)

    L1 = l1_criterion(y_preds, batch_y).mul(lambda1)
    L_KL = kl_criterion(y_preds, batch_y).mul(curlambda_kl)
    L_GAN = GAN_criterion(y_preds, batch_y)
    # Later on these will have to come from the 2nd discriminator
    # I suggest we start by making it work with just the GAN discriminator for now
    L_VAE_GAN = VAE_GAN_Criterion(y_preds, batch_y)

    # TODO: Add variants (GAN only, VAE only)
    loss_total = L1.add(L_KL).add(L_GAN).add(L_VAE_GAN)
    return loss_total

def cloud_mask_loss(y_preds, y_truth, cloud_mask):
    l2_loss = nn.MSELoss()

    mask = torch.repeat_interleave(1-cloud_mask, 4, axis=1)
    # Mask which data is cloudy and shouldn't be used for averaging
    masked_y_pred = torch.mul(y_preds, mask)
    masked_y_truth = torch.mul(y_truth, mask)
    return l2_loss(masked_y_pred,masked_y_truth)
