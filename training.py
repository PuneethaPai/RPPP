import os

import yaml
import dagshub

from model_def import NumCatModel
import reddit_utils

with open(r"./general_params.yml") as f:
    params = yaml.safe_load(f)

CHUNK_SIZE = params["chunk_size"]
TARGET_LABEL = params["target_col"]

def load_and_train(remote_wfs, random_state=42):
    train_data_loc = os.path.join(remote_wfs, reddit_utils.TRAIN_DF_PATH)
    print("Initializing models...")
    model = NumCatModel(random_state=random_state)
    model.train(
        chunksize=CHUNK_SIZE, data_loc=train_data_loc, target=TARGET_LABEL,
    )

    print("Saving models locally...")
    with dagshub.dagshub_logger(should_log_metrics=False) as logger:
        model.save_model(logger=logger)


if __name__ == "__main__":
    remote_wfs = reddit_utils.get_remote_gs_wfs()
    load_and_train(remote_wfs)
    print("Loading and training done!")
