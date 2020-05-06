import os
import re
import pandas as pd
import yaml
import dagshub

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

train_df_path = "rML-train.csv"

# ----- Helper Functions -----
# A partial fit for the TfidfVectorizer courtesy @maxymoo on Stack Overflow
# https://stackoverflow.com/questions/39109743/adding-new-text-to-sklearn-tfidif-vectorizer-python/39114555#39114555
def partial_fit(self, X):
    # If this is the first iteration, use regular fit
    if not hasattr(self, "is_initialized"):
        self.fit(X)
        self.n_docs = len(X)
        self.is_initialized = True
    else:
        max_idx = max(self.vocabulary_.values())
        for a in X:
            # update vocabulary_
            if self.lowercase:
                a = str(a).lower()
            tokens = re.findall(self.token_pattern, a)
            for w in tokens:
                if w not in self.vocabulary_:
                    max_idx += 1
                    self.vocabulary_[w] = max_idx

            # update idf_
            df = (self.n_docs + self.smooth_idf) / np.exp(
                self.idf_ - 1
            ) - self.smooth_idf
            self.n_docs += 1
            df.resize(len(self.vocabulary_))
            for w in tokens:
                df[self.vocabulary_[w]] += 1
            idf = np.log((self.n_docs + self.smooth_idf) / (df + self.smooth_idf)) + 1
            self._tfidf._idf_diag = dia_matrix((idf, 0), shape=(len(idf), len(idf)))
# ----- End Helper Functions -----


class TextModel:
    def __init__(self, random_state=42):
        self.model = SGDClassifier(loss="log", random_state=random_state)
        print("Generate TFIDF features...")
        TfidfVectorizer.partial_fit = partial_fit
        self.tfidf = TfidfVectorizer(max_features=25000)
    
    def train(self):
        print("Training TextModel...")

        for i, chunk in enumerate(pd.read_csv(os.path.join(remote_wfs, train_df_path), chunksize=CHUNK_SIZE)):
            print(f"Fitting TFIDF to chunk {i+1}...")
            self.tfidf.partial_fit(chunk["title_and_body"].values.astype("U"))

        print("TFIDF feature matrix created!")

        for i, chunk in enumerate(pd.read_csv(os.path.join(remote_wfs, train_df_path), chunksize=CHUNK_SIZE)):
            print(f"Training on chunk {i+1}...")
            df_y = chunk[TARGET_LABEL]
            tfidf_X = self.tfidf.transform(chunk["title_and_body"].values.astype("U"))
            self.model.partial_fit(tfidf_X, df_y, classes=np.array([0, 1]))

    def save_model(self, logger=None):
        os.makedirs(reddit_utils.MODELS_DIR, exist_ok=True)
        joblib.dump(self.model, reddit_utils.MODEL_PATH)
        joblib.dump(self.tfidf, reddit_utils.TFIDF_PATH)
        # log params
        if logger:
            logger.log_hyperparams(prepare_log(self.tfidf.get_params(), "tfidf"))
            logger.log_hyperparams(prepare_log(self.model.get_params(), "model"))
            logger.log_hyperparams(model_class=type(self.model).__name__)


def get_remote_gs_wfs():
    print("Retreiving location of remote working file system...")
    stream = os.popen("dvc remote list --local")
    output = stream.read()
    remote_wfs_loc = output.split("\t")[1].split("\n")[0]
    return remote_wfs_loc


def load_and_train(remote_wfs, model_type=None, random_state=42):
    print("Initializing models...")
    if model_type == MODEL_TYPE_TEXT:
        model = TextModel(random_state=random_state)
    else:
        # TODO
        return

    model.train()

    print("Saving models locally...")
    with dagshub.dagshub_logger(should_log_metrics=False) as logger:
        logger.log_hyperparams(feature_type="text")
        model.save_model(logger=logger)


if __name__ == "__main__":
    remote_wfs = get_remote_gs_wfs()
    load_and_train(remote_wfs, MODEL_TYPE)
    print("Loading and training done!")
