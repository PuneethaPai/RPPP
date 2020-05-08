import os
import re

import yaml
import dagshub

from model_def import NumCatModel

with open(r"./general_params.yml") as f:
    params = yaml.safe_load(f)

CHUNK_SIZE = params["chunk_size"]
TARGET_LABEL = params["target_col"]

train_df_path = "rML-train.csv"

def get_remote_gs_wfs():
    print("Retreiving location of remote working file system...")
    stream = os.popen("dvc remote list --local")
    output = stream.read()
    remote_wfs_loc = output.split("\t")[1].split("\n")[0]
    return remote_wfs_loc


def load_and_train(remote_wfs, random_state=42):
    train_data_loc = os.path.join(remote_wfs, train_df_path)
    print("Initializing models...")
    model = NumCatModel(random_state=random_state)
    model.train(chunksize=CHUNK_SIZE, data_loc=train_data_loc, target=TARGET_LABEL,)

    print("Saving models locally...")
    with dagshub.dagshub_logger(should_log_metrics=False) as logger:
        model.save_model(logger=logger)


if __name__ == "__main__":
    remote_wfs = get_remote_gs_wfs()
    load_and_train(remote_wfs)
    print("Loading and training done!")
