import gcsfs
import os
import pandas as pd
from sklearn.model_selection import train_test_split
import yaml

import reddit_utils

with open(r"./general_params.yml") as f:
    params = yaml.safe_load(f)

CHUNK_SIZE = params["chunk_size"]
TARGET_LABEL = params["target_col"]

UNIQUE_FLAIRS = [
    "Discussion",
    "Project",
    "Research",
    "None",
    "News",
    "Shameless Self Promo",
    "Inaccurate",
    "Misleading",
    "Clickbait",
]

def load_and_process_data(remote_wfs, random_state=42):
    fs = gcsfs.GCSFileSystem(
        project=reddit_utils.PROJECT_NAME, token=os.environ[reddit_utils.GCLOUD_CRED_ENV_VAR]
    )
    with fs.open(os.path.join(remote_wfs, reddit_utils.TRAIN_DF_PATH), "a") as train_f, fs.open(
        os.path.join(remote_wfs, reddit_utils.TEST_DF_PATH), "a"
    ) as test_f:
        print("Loading data in chuncks...")
        for i, chunk in enumerate(
            pd.read_csv(os.path.join(remote_wfs, reddit_utils.RAW_DF_PATH), chunksize=CHUNK_SIZE)
        ):
            print(f"Processing chunk {i+1}...")
            processed_data = process(chunk)
            print("Splitting into train and test data...")
            train_chunk, test_chunk = train_test_split(
                processed_data,
                random_state=random_state,
                stratify=processed_data[TARGET_LABEL],
            )
            print("Saving to cloud...")
            save_data(train_chunk, train_f, test_chunk, test_f, i)


def process(chunk):
    df = chunk.copy()
    df = df.drop(columns=["id", "author"])
    df = df.rename(columns={"selftext": "body", "link_flair_text": "flair"})

    df["title_len"] = df.title.str.len()
    df["body_len"] = df.body.str.len()
    df["has_thumbnail"] = [
        0 if (x == "self" or x == "default") else 1 for x in df["thumbnail"]
    ]

    df = df.fillna({"body": "", "flair": "None", "body_len": 0})
    df["flair"] = ["Discussion" if (x == "Discusssion") else x for x in df["flair"]]

    df = pd.concat([df, pd.get_dummies(df["flair"], prefix="flair")], axis=1).drop(
        ["flair"], axis=1
    )

    for flair in UNIQUE_FLAIRS:
        flair_with_prefix = "flair_" + flair
        if flair_with_prefix not in df.columns:
            df[flair_with_prefix] = 0

    df = df[df["title"] != "[deleted by user]"]
    df = df[df["body"] != "[deleted]"]
    df = df[df["body"] != "[removed]"]

    df["title_and_body"] = (df["title"] + " " + df["body"]).astype(str)

    return df


def save_data(train_chunk, train_f, test_chunk, test_f, i):
    # TODO: Saving is kinda slow now. Try to improve performance
    # We want to write the headers only once
    header = True if i == 0 else False
    train_chunk.to_csv(train_f, header=header, mode="a")
    test_chunk.to_csv(test_f, header=header, mode="a")


if __name__ == "__main__":
    remote_wfs = reddit_utils.get_remote_gs_wfs()
    load_and_process_data(remote_wfs)
    print("Loading and processing done!")
