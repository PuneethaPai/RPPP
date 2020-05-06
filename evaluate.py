import dagshub
import os
import pandas as pd
import yaml

import re
import numpy as np
import joblib
from scipy.sparse.dia import dia_matrix
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import SGDClassifier

from reddit_utils import calculate_metrics, prepare_log
import reddit_utils

with open(r"./general_params.yml") as f:
    params = yaml.safe_load(f)

with open(r"./training_params.yml") as f:
    training_params = yaml.safe_load(f)

CHUNK_SIZE = params["chunk_size"]
TARGET_LABEL = params["target_col"]
MODEL_TYPE_TEXT = "model_text"
MODEL_TYPE_NUM_CAT = "model_num_cat"
MODEL_TYPE_OTHER = ""
MODEL_TYPE = (
    MODEL_TYPE_TEXT
    if training_params["use_text_cols"]
    else MODEL_TYPE_NUM_CAT
    if training_params["use_number_category_cols"]
    else MODEL_TYPE_OTHER
)


TEST_DF_PATH = "rML-test.csv"


def get_remote_gs_wfs():
    print("Retreiving location of remote working file system...")
    stream = os.popen("dvc remote list --local")
    output = stream.read()
    remote_wfs_loc = output.split("\t")[1].split("\n")[0]
    return remote_wfs_loc


def load_transform_and_eval(remote_wfs, model_type=None, random_state=42):
    print("loading transformer and model...")
    if model_type == MODEL_TYPE_TEXT:
        model = joblib.load(os.path.join(reddit_utils.LOCAL_PATH, reddit_utils.MODEL_PATH))
        tfidf = joblib.load(os.path.join(reddit_utils.LOCAL_PATH, reddit_utils.TFIDF_PATH))
    else:
        # TODO
        return

    y_proba = np.array([])
    y_pred = np.array([])
    y = np.array([])
    print("Loading test data and testing model...")
    for i, chunk in enumerate(
        pd.read_csv(os.path.join(remote_wfs, TEST_DF_PATH), chunksize=CHUNK_SIZE)
    ):
        print(f"Testing on chunk {i+1}...")
        test_tfidf = tfidf.transform(chunk["title_and_body"].values.astype("U"))
        y_proba = np.concatenate((y_pred, model.predict_proba(test_tfidf)[:, 1]))
        y_pred = np.concatenate((y_pred, model.predict(test_tfidf)))
        y = np.concatenate((y, chunk[TARGET_LABEL]))

    print("Calculating metrics")
    print(np.unique(y_proba), np.unique(y_pred), np.unique(y))
    metrics = calculate_metrics(y_pred, y_proba, y)

    print("Logging metrics...")
    with dagshub.dagshub_logger(should_log_hparams=False) as logger:
        logger.log_metrics(prepare_log(metrics, "test"))


if __name__ == "__main__":
    remote_wfs = get_remote_gs_wfs()
    load_transform_and_eval(remote_wfs, MODEL_TYPE)
    print("Model evaluation done!")
