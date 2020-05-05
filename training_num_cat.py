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
from sklearn.metrics import (
    roc_auc_score,
    average_precision_score,
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
)

with open(r"./general_params.yml") as f:
    params = yaml.safe_load(f)

with open(r"./training_params.yml") as f:
    training_params = yaml.safe_load(f)

NUM_COL_NAMES = ["title_len", "body_len", "hour", "minute", "dayofweek", "dayofyear"]
CAT_COL_NAMES = [
    "has_thumbnail",
    "flair_Clickbait",
    "flair_Discussion",
    "flair_Inaccurate",
    "flair_Misleading",
    "flair_News",
    "flair_None",
    "flair_Project",
    "flair_Research",
    "flair_Shameless Self Promo",
]
CHUNK_SIZE = params["chunk_size"]
TARGET_LABEL = params["target_col"]
TRAIN_TFIDF = training_params["use_text_cols"]
TRAIN_NUM_CAT = training_params["use_number_category_cols"]

local_path = "."
train_df_path = "rML-train.csv"
tfidf_path = "models/tfidf.pkl"
clf_tfidf_path = "models/tfidf.pkl"
clf_num_cat_path = "models/tfidf.pkl"


# ----- Helper Functions -----
# A partial fit for the TfidfVectorizer courtesy @maxymoo on Stack Overflow
# https://stackoverflow.com/questions/39109743/adding-new-text-to-sklearn-tfidif-vectorizer-python/39114555#39114555
def partial_fit(self, X):
    # If this is the first iteration, use regular fit
    if not hasattr(self, 'is_initialized'):
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
            idf = (
                np.log((self.n_docs + self.smooth_idf) / (df + self.smooth_idf)) + 1
            )
            self._tfidf._idf_diag = dia_matrix((idf, 0), shape=(len(idf), len(idf)))


# ----- End Helper Functions -----


def get_remote_gs_wfs():
    print("Retreiving location of remote working file system...")
    stream = os.popen("dvc remote list --local")
    output = stream.read()
    remote_wfs_loc = output.split("\t")[1].split("\n")[0]
    return remote_wfs_loc


def load_and_train(remote_wfs, random_state=42):
    print("Initializing models...")
    if TRAIN_TFIDF:
        clf_tfidf = SGDClassifier(loss="log", random_state=random_state)
        print("Generate TFIDF features...")
        TfidfVectorizer.partial_fit = partial_fit
        tfidf = TfidfVectorizer(max_features=25000)
        for i, chunk in enumerate(
            pd.read_csv(os.path.join(remote_wfs, train_df_path), chunksize=CHUNK_SIZE)
        ):
            print(f"Training on chunk {i+1}...")
            tfidf.partial_fit(chunk["title_and_body"])

        print("TFIDF feature matrix created!")

    if TRAIN_NUM_CAT:
        num_cat_cols = NUM_COL_NAMES + CAT_COL_NAMES
        clf_num_cat = SGDClassifier(loss="log", random_state=random_state)

    print("Training model...")
    for i, chunk in enumerate(
        pd.read_csv(os.path.join(remote_wfs, train_df_path), chunksize=CHUNK_SIZE)
    ):
        print(f"Training on chunk {i+1}...")
        df_y = chunk[TARGET_LABEL]
        if TRAIN_TFIDF:
            tfidf_X = tfidf.transform(chunk["title_and_body"])
            clf_tfidf.partial_fit(tfidf_X, df_y, classes=np.array([0,1]))

        if TRAIN_NUM_CAT:
            num_cat_X = chunk[num_cat_cols]
            clf_num_cat.partial_fit(num_cat_X, df_y, classes=np.array([0,1]))

        print("Saving models locally...")
        save_data(tfidf, clf_tfidf, clf_num_cat)


def save_data(tfidf=None, clf_tfidf=None, clf_num_cat=None):
    if TRAIN_TFIDF:
        joblib.dump(tfidf, os.path.join(local_path, tfidf_path))
        joblib.dump(clf_tfidf, os.path.join(local_path, clf_tfidf_path))
    if TRAIN_NUM_CAT:
        joblib.dump(clf_num_cat, os.path.join(local_path, clf_num_cat_path))


if __name__ == "__main__":
    remote_wfs = get_remote_gs_wfs()
    load_and_train(remote_wfs)
    print("Loading and training done!")
