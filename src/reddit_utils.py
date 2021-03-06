import os

from sklearn.metrics import (
    roc_auc_score,
    average_precision_score,
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
)

# ----- Cloud Details -----
PROJECT_NAME = "talos-project"
BIGQUERY_PROJECT = "project-talos"
GCLOUD_CRED_ENV_VAR = "GOOGLE_APPLICATION_CREDENTIALS"

# ----- Constants -----
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
TEXT_COL_NAME = ["title_and_body"]

# ----- Paths -----


MODELS_DIR = "./models"
TFIDF_PATH = MODELS_DIR + "/tfidf.pkl"
MODEL_PATH = MODELS_DIR + "/model.pkl"
RAW_DF_PATH = "rML-raw-data.csv"
TRAIN_DF_PATH = "rML-train.csv"
TEST_DF_PATH = "rML-test.csv"

# ----- Functions -----


def calculate_metrics(y_pred, y_proba, y):
    return {
        "roc_auc": float(roc_auc_score(y, y_proba)),
        "average_precision": float(average_precision_score(y, y_proba)),
        "accuracy": float(accuracy_score(y, y_pred)),
        "precision": float(precision_score(y, y_pred)),
        "recall": float(recall_score(y, y_pred)),
        "f1": float(f1_score(y, y_pred)),
    }


def get_remote_gs_wfs():
    print("Retreiving location of remote working file system...")
    stream = os.popen("dvc remote list --local")
    output = stream.read()
    remote_wfs_loc = output.split("\t")[1].split("\n")[0]
    return remote_wfs_loc


# Prepare a dictionary of either hyperparams or metrics for logging.
def prepare_log(d, prefix=""):
    if prefix:
        prefix = f"{prefix}__"

    # Ensure all logged values are suitable for logging - complex objects aren't supported.
    def sanitize(value):
        return (
            value
            if value is None or type(value) in [str, int, float, bool]
            else str(value)
        )

    return {f"{prefix}{k}": sanitize(v) for k, v in d.items()}
