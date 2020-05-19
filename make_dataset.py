from google.cloud import bigquery
import reddit_utils


def make_dataset(remote_wfs):
    client = bigquery.Client()
    temp_dataset_name = "reddit_dataset"
    temp_table_name = "posts"

    # Create Temporary BigQuery Dataset
    dataset_id = "{}.{}".format(reddit_utils.BIGQUERY_PROJECT, temp_dataset_name)
    dataset = bigquery.Dataset(dataset_id)
    dataset.location = "US"
    dataset = client.create_dataset(dataset)
    print("Created dataset {}.{}".format(client.project, dataset.dataset_id))

    # Set table_id to the ID of the destination table.

    temp_table_id = "{}.{}.{}".format(
        reddit_utils.BIGQUERY_PROJECT, temp_dataset_name, temp_table_name
    )

    job_config = bigquery.QueryJobConfig(destination=temp_table_id)

    sql = """
        SELECT id, title, selftext, link_flair_text, is_self AS self_post, thumbnail, author,
          CAST(FORMAT_TIMESTAMP('%H', TIMESTAMP_SECONDS(created_utc), 'America/New_York') AS INT64) AS hour,
          CAST(FORMAT_TIMESTAMP('%M', TIMESTAMP_SECONDS(created_utc), 'America/New_York') AS INT64) AS minute,
          CAST(FORMAT_TIMESTAMP('%w', TIMESTAMP_SECONDS(created_utc), 'America/New_York') AS INT64) AS dayofweek,
          CAST(FORMAT_TIMESTAMP('%j', TIMESTAMP_SECONDS(created_utc), 'America/New_York') AS INT64) AS dayofyear,
          gilded, score,
          IF(PERCENT_RANK() OVER (ORDER BY score ASC) >= 0.50, 1, 0) as is_top_median,
          IF(PERCENT_RANK() OVER (ORDER BY score ASC) >= 0.90, 1, 0) as is_top_decile,
          IF(PERCENT_RANK() OVER (ORDER BY score ASC) >= 0.99, 1, 0) as is_top_percent,
          FROM `fh-bigquery.reddit_posts.*`
          WHERE (_TABLE_SUFFIX BETWEEN '2018_08' AND '2019_08')
          AND subreddit = 'MachineLearning'
    """

    # Start the query, passing in the extra configuration.
    query_job = client.query(sql, job_config=job_config)  # Make an API request.
    query_job.result()  # Wait for the job to complete.
    print("Query results loaded to the temporary table {}".format(temp_table_name))

    # Export temporary dataset to GCS
    destination_uri = "{}/{}".format(remote_wfs, reddit_utils.RAW_DF_PATH)
    dataset_ref = bigquery.DatasetReference(
        reddit_utils.BIGQUERY_PROJECT, temp_dataset_name
    )
    table_ref = dataset_ref.table(temp_table_name)
    extract_job = client.extract_table(
        table_ref,
        destination_uri,
        # Location must match that of the source table.
        location="US",
    )  # API request
    extract_job.result()  # Waits for job to complete.

    print(
        "Exported {}:{}.{} to {}".format(
            reddit_utils.BIGQUERY_PROJECT,
            temp_dataset_name,
            temp_table_name,
            destination_uri,
        )
    )

    # Remove temp BigQuery table
    client.delete_dataset(
        dataset_id, delete_contents=True, not_found_ok=True
    )  # Make an API request.
    print("Deleted dataset '{}'.".format(dataset_id))


if __name__ == "__main__":
    remote_wfs = reddit_utils.get_remote_gs_wfs()
    make_dataset(remote_wfs)
    print("Created raw data file in remote working file system!")
