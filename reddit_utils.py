from sklearn.metrics import (
    roc_auc_score,
    average_precision_score,
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
)

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

# ----- Paths -----
MODELS_DIR = "./models"
TFIDF_PATH = MODELS_DIR + "/tfidf.pkl"
MODEL_PATH = MODELS_DIR + "/model.pkl"

# ----- Functions -----
def calculate_metrics(y_pred, y_proba, y):
    return {
        'roc_auc': roc_auc_score(y, y_proba),
        'average_precision': average_precision_score(y, y_proba),
        'accuracy': accuracy_score(y, y_pred),
        'precision': precision_score(y, y_pred),
        'recall': recall_score(y, y_pred),
        'f1': f1_score(y, y_pred),
    }

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