import pandas as pd
import gcsfs
import os
from sklearn.model_selection import train_test_split

PROJECT_NAME = "talos-project"
GCLOUD_CRED_ENV_VAR = "GOOGLE_APPLICATION_CREDENTIALS"
CHUNK_SIZE = 5000
TARGET_LABEL = "is_top_decile"


raw_df_path = "rML-raw-data.csv"
train_df_path = "rML-train.csv"
test_df_path = "rML-test.csv"


def get_remote_gs_wfs():
    print("Retreiving location of remote working file system...")
    stream = os.popen("dvc remote list --local")
    output = stream.read()
    remote_wfs_loc = output.split("\t")[1].split("\n")[0]
    return remote_wfs_loc


def load_and_process_data(remote_wfs, random_state=42):
    fs = gcsfs.GCSFileSystem(
        project=PROJECT_NAME, token=os.environ[GCLOUD_CRED_ENV_VAR]
    )
    with fs.open(os.path.join(remote_wfs, train_df_path), "a") as train_f, fs.open(
        os.path.join(remote_wfs, test_df_path), "a"
    ) as test_f:
        print("Loading data in chuncks...")
        for i, chunk in enumerate(
            pd.read_csv(os.path.join(remote_wfs, raw_df_path), chunksize=CHUNK_SIZE)
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

    df["title_and_body"] = df["title"] + " " + df["body"]

    return df


def save_data(train_chunk, train_f, test_chunk, test_f, i):
    # We want to write the headers only once
    header = True if i == 0 else False

    train_chunk.to_csv(train_f, header=header, mode="a")
    test_chunk.to_csv(test_f, header=header, mode="a")


if __name__ == "__main__":
    remote_wfs = get_remote_gs_wfs()
    load_and_process_data(remote_wfs)
    print("Loading and processing done!")
