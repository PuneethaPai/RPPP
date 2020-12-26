import os
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.linear_model import SGDClassifier

import src.reddit_utils as r_utils
from src.utilities import dump_yaml


class NumCatModel:
    def __init__(self, loss, random_state=42):
        self.model = SGDClassifier(loss=loss, random_state=random_state)

    def train(self, chunksize, data_loc, target):
        print("Training NumCatModel...")

        for i, chunk in enumerate(pd.read_csv(data_loc, chunksize=chunksize)):
            print(f"Training on chunk {i+1}...")
            df_y = chunk[target]
            cols_to_train = r_utils.NUM_COL_NAMES + r_utils.CAT_COL_NAMES
            df_X = chunk[cols_to_train]
            self.model.partial_fit(df_X, df_y, classes=np.array([0, 1]))

        y_proba = np.array([])
        y_pred = np.array([])
        y = np.array([])
        print("Calculating training metrics...")
        for i, chunk in enumerate(pd.read_csv(data_loc, chunksize=chunksize)):
            df_y = chunk[target]
            cols_to_train = r_utils.NUM_COL_NAMES + r_utils.CAT_COL_NAMES
            df_X = chunk[cols_to_train]

            y_proba = np.concatenate((y_pred, self.model.predict_proba(df_X)[:, 1]))
            y_pred = np.concatenate((y_pred, self.model.predict(df_X)))
            y = np.concatenate((y, chunk[target]))

        metrics = r_utils.calculate_metrics(y_pred, y_proba, y)
        metrics_path = Path("models/metrics/")
        metrics_path.mkdir(parents=True, exist_ok=True)
        dump_yaml(metrics, metrics_path / "train.yaml")

    def save_model(self):
        os.makedirs(r_utils.MODELS_DIR, exist_ok=True)
        joblib.dump(self.model, r_utils.MODEL_PATH)
        # log params
        hyper_params = dict(
            feature_type="numerical + categorical",
            model_class=type(self.model).__name__,
            model=self.model.get_params(),
        )
        dump_yaml(hyper_params, Path("models/result.yaml"))
