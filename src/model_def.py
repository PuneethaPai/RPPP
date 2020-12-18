import joblib
import numpy as np

import os
import pandas as pd
from sklearn.linear_model import SGDClassifier
import reddit_utils


class NumCatModel:
    def __init__(self, random_state=42):
        self.model = SGDClassifier(loss="log", random_state=random_state)

    def train(self, chunksize, data_loc, target, logger=None):
        print("Training NumCatModel...")

        for i, chunk in enumerate(pd.read_csv(data_loc, chunksize=chunksize)):
            print(f"Training on chunk {i+1}...")
            df_y = chunk[target]
            cols_to_train = reddit_utils.NUM_COL_NAMES + reddit_utils.CAT_COL_NAMES
            df_X = chunk[cols_to_train]
            self.model.partial_fit(df_X, df_y, classes=np.array([0, 1]))

        if logger:
            y_proba = np.array([])
            y_pred = np.array([])
            y = np.array([])
            print("Calculating training metrics...")
            for i, chunk in enumerate(pd.read_csv(data_loc, chunksize=chunksize)):
                df_y = chunk[target]
                cols_to_train = reddit_utils.NUM_COL_NAMES + reddit_utils.CAT_COL_NAMES
                df_X = chunk[cols_to_train]

                y_proba = np.concatenate((y_pred, self.model.predict_proba(df_X)[:, 1]))
                y_pred = np.concatenate((y_pred, self.model.predict(df_X)))
                y = np.concatenate((y, chunk[target]))

            metrics = reddit_utils.calculate_metrics(y_pred, y_proba, y)
            logger.log_metrics(reddit_utils.prepare_log(metrics, "train"))

    def save_model(self, logger=None):
        os.makedirs(reddit_utils.MODELS_DIR, exist_ok=True)
        joblib.dump(self.model, reddit_utils.MODEL_PATH)
        # log params
        if logger:
            logger.log_hyperparams(feature_type="numerical + categorical")
            logger.log_hyperparams(model_class=type(self.model).__name__)
            logger.log_hyperparams(
                reddit_utils.prepare_log(self.model.get_params(), "model")
            )
