import os

import yaml
import dagshub

from model_def import NumCatModel
import reddit_utils

with open(r"./general_params.yml") as f:
    params = yaml.safe_load(f)

CHUNK_SIZE = params["chunk_size"]
TARGET_LABEL = params["target_col"]


def load_and_train(random_state=42):
    with dagshub.dagshub_logger(metrics_path="training_metrics.csv") as logger:
        train_data_loc = os.path.join("processed", reddit_utils.TRAIN_DF_PATH)
        print("Initializing models...")
        model = NumCatModel(random_state=random_state)
        model.train(
            chunksize=CHUNK_SIZE,
            data_loc=train_data_loc,
            target=TARGET_LABEL,
            logger=logger,
        )

        print("Saving models locally...")
        model.save_model(logger=logger)


if __name__ == "__main__":
    load_and_train()
    print("Loading and training done!")
