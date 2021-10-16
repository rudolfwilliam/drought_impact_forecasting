from torch import nn
import torch.optim as optim
from torch.optim.lr_scheduler import LambdaLR
import pytorch_lightning as pl
from drought_impact_forecasting.losses import kl_weight, base_line_total_loss
from .model_parts.SAVP_model.base_model import Encoder, Discriminator_GAN, Discriminator_VAE
from .model_parts.Conv_LSTM import Conv_LSTM
 
class LSTM_model(pl.LightningModule):
    def __init__(self, cfg):
        """
        Base prediction model. It is an adaptation of SAVP (Stochastic Adversarial Video Prediction) by Alex Lee presented in https://arxiv.org/pdf/1804.01523.pdf

        Parameters:
            cfg (dict) -- model configuration parameters
        """
        super().__init__()
        self.cfg = cfg
        self.num_epochs = self.cfg["training"]["epochs"]

        #self.Discriminator_GAN = Discriminator_GAN(self.cfg)
        channels = 7
        n_cells = 10
        self.model = Conv_LSTM(input_dim = channels, 
                              hidden_dim = [3]*n_cells, 
                              kernel_size = (3,3), 
                              num_layers = n_cells,
                              batch_first=False, 
                              bias=True, 
                              return_all_layers=False)

    # For now just use the GAN
    def forward(self, x):
        return self.model(x)

    def configure_optimizers(self):
        if self.cfg["training"]["optimizer"] == "adam":
            optimizer = optim.Adam(self.parameters(), lr=self.cfg["training"]["start_learn_rate"])
            
            # Decay learning rate according for last (epochs - decay_point) iterations
            lambda_all = lambda epoch: self.cfg["training"]["start_learn_rate"] \
                          if epoch <= self.cfg["model"]["decay_point"] \
                          else ((self.cfg["training"]["epochs"]-epoch) / (30-self.cfg["model"]["decay_point"])
                                * self.cfg["training"]["start_learn_rate"])

            scheduler = LambdaLR(optimizer, lambda_all)
        else:
            raise ValueError("You have specified an invalid optimizer.")

        # Pls check this works correctly with pytorch lightning
        return [optimizer], [scheduler]

    def training_step(self, batch, batch_idx):
        highres_dynamic_context, highres_static, meso_dynamic, meso_static, highres_dynamic_target = batch
        print(highres_dynamic_context.shape)
        # Only satellite images as input
        y_preds, _ = self(highres_dynamic_context)
        print("Target shape: {}".format(highres_dynamic_target.shape))
        print("Predicted shape: {}".format(type(y_preds[0])))
        loss_total = base_line_total_loss(y_preds, highres_dynamic_target, self.current_epoch,
                self.cfg["loss"]["lambda1"], self.cfg["loss"]["lambda_KL_factor"],
                self.cfg["model"]["anneal_start"], self.cfg["model"]["anneal_end"])

        return loss_total

    """def validation_step(self):
        pass"""