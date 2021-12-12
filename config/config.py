import argparse
import os
import json

def check_model_exists(name):
    if name not in ["LSTM_model", "Transformer_model", 'Conv_model','Peephole_LSTM_model', 'NDVI_Peephole_LSTM_model']:
        raise ValueError("The specified model name is invalid.")

def command_line_parser(mode = "train"):
    """"
    Returns:
        args       -- command line arguments
        cfg (dict) -- configurations from a config file depending on the --model_name argument
    """
    parser = argparse.ArgumentParser(
        add_help=True,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument('--model_name', type=str, default='LSTM_model', choices=['LSTM_model','Peephole_LSTM_model','NDVI_Peephole_LSTM_model', 'Transformer_model', 'Conv_model'], help='frame prediction architecture')

    if mode == 'train':
        parser.add_argument('--batch_size', type=int, default=None, help='batch size')
        parser.add_argument('--bm', type=str, default=None, help='big memory or small') # y = ture, n = false
        parser.add_argument('--nl', type=int, default=None, help='number of layers')
        parser.add_argument('--ft', type=int, default=None, help='future steps for training')
        parser.add_argument('--lr', type=float, default=None, help='learining rate')
        parser.add_argument('--bs', type=str, default=None, choices=['mean_cube', 'last_frame'], help='baseline function')
        args = parser.parse_args()
        check_model_exists(args.model_name)
        cfg = json.load(open(os.getcwd() + "/config/" + args.model_name + ".json", 'r'))
        if args.batch_size is not None:
            cfg["training"]["train_batch_size"] = args.batch_size
            cfg["training"]["val_1_batch_size"] = args.batch_size
            cfg["training"]["val_2_batch_size"] = args.batch_size
            cfg["training"]["test_batch_size"] = args.batch_size        
        if args.bm is not None:
            if args.bm == "y" or args.bm == "Y" or args.bm == "T" or args.bm == "t":
                cfg["model"]["big_mem"] = True
            elif args.bm == "n" or args.bm == "N" or args.bm == "f" or args.bm == "F":
                cfg["model"]["big_mem"] = False
        if args.nl is not None:
            cfg["model"]["n_layers"] = args.nl
        if args.ft is not None:
            cfg["model"]["future_training"] = args.ft
        if args.lr is not None:
            cfg["training"]["start_learn_rate"] = args.lr
        if args.bs is not None:
            cfg["model"]["baseline"] = args.bs

    
    if mode == 'validate':
        parser.add_argument('--ts', type=str, help='timestamp of the model to validate: deprecated')
        parser.add_argument('--rn', type=str, help='wandb run name to validate')
        parser.add_argument('--me', type=int, default=-1, help='model epoch to test/validate')
        args = parser.parse_args()
        check_model_exists(args.model_name)
        try:
            dir_path = find_dir_path(args.rn)
            cfg = json.load(open(os.path.join(dir_path, "files",  args.model_name + ".json"), 'r'))
            cfg['path_dir'] = dir_path
        except:
            raise ValueError("The timestamp doesn't exist.")
            
    return args, cfg

def find_dir_path(wandb_name):
    dir_path = os.path.join(os.getcwd(), "wandb")

    runs = []
    for path, subdirs, files in os.walk(dir_path):
        for dir_ in subdirs:
            # Ignore any licence, progress, etc. files
            if os.path.isfile(os.path.join(dir_path,dir_, "files", "run_name.txt")):
                with open(os.path.join(dir_path,dir_, "files",  "run_name.txt"),'r') as f:
                    if (f.read() == wandb_name):
                        return os.path.join(dir_path,dir_)
    raise ValueError("The name doesn't exist.")


def read_config(path):
    cfg = json.load(open(path, 'r'))
    return cfg