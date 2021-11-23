from logging import Logger
import sys
import os
import numpy as np
import random
from shutil import copy2
import pickle

#from pytorch_lightning.accelerators import accelerato
#from pytorch_lightning.callbacks.early_stopping import EarlyStopping

sys.path.append(os.getcwd())

import torch
import matplotlib.pyplot as plt
from torch.utils.data import DataLoader
import pytorch_lightning as pl
from pytorch_lightning import Trainer
from pytorch_lightning.loggers import WandbLogger

from config.config import command_line_parser
from drought_impact_forecasting.models.LSTM_model import LSTM_model
from drought_impact_forecasting.models.Transformer_model import Transformer_model
from drought_impact_forecasting.models.Baseline_model import Last_model
from Data.data_preparation import prepare_data
from callbacks import Prediction_Callback
from callbacks import WandbTrain_callback

import wandb
from datetime import datetime

def main():

    #TODO: Make this modular so that it works both for LSTM and Transformer

    timestamp = datetime.now().strftime("%d_%m_%Y_%H_%M_%S") # timestamp unique to this training instance
    print("Timestamp of the instance: " + timestamp)

    args, cfg = command_line_parser(mode='train')
    print(args)
    
    #os.mkdir(os.getcwd() + "/model_instances/model_" + timestamp)
    #copy2(os.getcwd() + "/config/" + args.model_name + ".json", os.getcwd() + "/model_instances/model_" + timestamp + "/" + args.model_name + ".json")

    if not cfg["training"]["offline"]:
        wandb.login()
    
    wandb.init()

    # Store the model to wandb
    copy2(os.getcwd() + "/config/" + args.model_name + ".json", os.path.join(wandb.run.dir, "configs.json"))
    #GPU handling
    device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    # print("GPU count: {0}".format(gpu_count))

    wandb_logger = WandbLogger(project='DS_Lab', config=cfg, group=args.model_name, job_type='train', offline=True)
    
    random.seed(cfg["training"]["seed"])
    pl.seed_everything(cfg["training"]["seed"], workers=True)

    training_data, val_1_data, val_2_data = prepare_data(cfg["data"]["mesoscale_cut"],
                                                         cfg["data"]["train_dir"],
                                                         device = device,
                                                         training_samples=cfg["training"]["training_samples"],
                                                         val_1_samples=cfg["training"]["val_1_samples"],
                                                         val_2_samples=cfg["training"]["val_2_samples"])
    
    train_dataloader = DataLoader(training_data, 
                                  num_workers=cfg["training"]["num_workers"],
                                  batch_size=cfg["training"]["train_batch_size"],
                                  shuffle=True, 
                                  drop_last=False)

    val_1_dataloader = DataLoader(val_1_data, 
                                  num_workers=cfg["training"]["num_workers"],
                                  batch_size=cfg["training"]["val_1_batch_size"], 
                                  drop_last=False)

    val_2_dataloader = DataLoader(val_2_data, 
                                  num_workers=cfg["training"]["num_workers"],
                                  batch_size=cfg["training"]["val_2_batch_size"], 
                                  drop_last=False)
    with open(os.path.join(wandb.run.dir, "train_data_paths.pkl"), "wb") as fp:
        pickle.dump(training_data.paths, fp)
    with open(os.path.join(wandb.run.dir, "val_1_data_paths.pkl"), "wb") as fp:
        pickle.dump(val_1_data.paths, fp)
    with open(os.path.join(wandb.run.dir, "val_2_data_paths.pkl"), "wb") as fp:
        pickle.dump(val_2_data.paths, fp)
    # Load model Callbacks
    callbacks = Prediction_Callback(cfg["data"]["mesoscale_cut"], 
                                    cfg["data"]["train_dir"],
                                    cfg["data"]["test_dir"], 
                                    training_data,
                                    cfg["training"]["print_predictions"],
                                    timestamp)
    wd_callbacks = WandbTrain_callback()
    # setup Trainer
    trainer = Trainer(max_epochs=cfg["training"]["epochs"], 
                      logger=wandb_logger,
                      log_every_n_steps = min(cfg["training"]["log_steps"],
                                            cfg["training"]["training_samples"] / cfg["training"]["train_batch_size"]),
                      devices = cfg["training"]["devices"],
                      accelerator=cfg["training"]["accelerator"],
                      callbacks=[wd_callbacks])

    # setup Model
    if args.model_name == "LSTM_model":
        model = LSTM_model(cfg, timestamp)
    elif args.model_name == "Transformer_model":
        model = Transformer_model(cfg, timestamp)
    else:
        raise ValueError("The specified model name is invalid.")

    model_last = Last_model()
    # Run training
    trainer.fit(model, train_dataloader, val_1_dataloader)
    # Run validation
    trainer.test(model, val_2_dataloader)

    if not cfg["training"]["offline"]:
        wandb.finish()

if __name__ == "__main__":
    main()
