import dagshub
import os
import pandas as pd
import yaml

import numpy as np
import joblib

import reddit_utils

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


def load_transform_and_eval(remote_wfs, random_state=42):
    print("loading transformer and model...")
    model = joblib.load(reddit_utils.MODEL_PATH)

    y_proba = np.array([])
    y_pred = np.array([])
    y = np.array([])
    print("Loading test data and testing model...")
    for i, chunk in enumerate(
        pd.read_csv(os.path.join(remote_wfs, reddit_utils.TEST_DF_PATH), chunksize=CHUNK_SIZE)
    ):
        print(f"Testing on chunk {i+1}...")
        df_X = chunk[COLS_FOR_EVAL]
        y_proba = np.concatenate((y_pred, model.predict_proba(df_X)[:, 1]))
        y_pred = np.concatenate((y_pred, model.predict(df_X)))
        y = np.concatenate((y, chunk[TARGET_LABEL]))

    print("Calculating metrics")
    metrics = reddit_utils.calculate_metrics(y_pred, y_proba, y)

    print("Logging metrics...")
    with dagshub.dagshub_logger(should_log_hparams=False, metrics_path='test_metrics.csv') as logger:
        logger.log_metrics(reddit_utils.prepare_log(metrics, "test"))


if __name__ == "__main__":
    remote_wfs = reddit_utils.get_remote_gs_wfs()
    load_transform_and_eval(remote_wfs)
    print("Model evaluation done!")
