import os
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import yaml

import reddit_utils
from utilities import dump_yaml

with open(r"./general_params.yml") as f:
    params = yaml.safe_load(f)

with open(r"./model_params.yml") as f:
    model_params = yaml.safe_load(f)

CHUNK_SIZE = params["chunk_size"]
TARGET_LABEL = params["target_col"]
COLS_FOR_EVAL = []

if model_params["use_text_cols"]:
    COLS_FOR_EVAL += reddit_utils.TEXT_COL_NAME

if model_params["use_number_category_cols"]:
    COLS_FOR_EVAL += reddit_utils.NUM_COL_NAMES + reddit_utils.CAT_COL_NAMES


def load_transform_and_eval():
    print("loading transformer and model...")
    model = joblib.load(reddit_utils.MODEL_PATH)

    y_proba = np.array([])
    y_pred = np.array([])
    y = np.array([])
    print("Loading test data and testing model...")
    for i, chunk in enumerate(
        pd.read_csv(
            os.path.join("data/processed", reddit_utils.TEST_DF_PATH),
            chunksize=CHUNK_SIZE,
        )
    ):
        print(f"Testing on chunk {i+1}...")
        df_X = chunk[COLS_FOR_EVAL]
        y_proba = np.concatenate((y_pred, model.predict_proba(df_X)[:, 1]))
        y_pred = np.concatenate((y_pred, model.predict(df_X)))
        y = np.concatenate((y, chunk[TARGET_LABEL]))

    print("Calculating metrics")
    metrics = reddit_utils.calculate_metrics(y_pred, y_proba, y)

    print("Logging metrics...")
    metrics_path = Path("models/metrics/test.yaml")
    dump_yaml(reddit_utils.prepare_log(metrics), metrics_path)


if __name__ == "__main__":
    load_transform_and_eval()
    print("Model evaluation done!")
