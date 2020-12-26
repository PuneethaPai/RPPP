import os

import dagshub
import yaml

import src.reddit_utils as r_utils
from src.model_def import NumCatModel
from src.utilities import read_yaml

pre_process = read_yaml("params.yaml", "pre_process")
train = read_yaml("params.yaml", "train")

CHUNK_SIZE = pre_process["chunk_size"]
TARGET_LABEL = pre_process["target_col"]


def load_and_train(random_state=42):
    train_data_loc = os.path.join("data/processed", r_utils.TRAIN_DF_PATH)
    print("Initializing models...")
    model = NumCatModel(train["loss"], random_state=random_state)
    model.train(chunksize=CHUNK_SIZE, data_loc=train_data_loc, target=TARGET_LABEL)

    print("Saving models locally...")
    model.save_model()


if __name__ == "__main__":
    load_and_train()
    print("Loading and training done!")
