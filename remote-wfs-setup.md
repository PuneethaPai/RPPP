# Simple Instructions to setup a Google Cloud Storage Remote Working File System with DVC
1. Create a virtualenv and activate it
2. `pip install dvc`, and for our case `pip install google-cloud-bigquery` as well.
3. Create a GS bucket {your-gs-bucket}.
4. Create a folder called {your-dvc-cache} & {your-remote-wfs}
5. Add {your-dvc-cache} to project as remote cache:

     `dvc remote add -d {dvc-cache-name} gs://{your-gs-bucket}/{your-dvc-cache}/`

6. Define {dvc-cache-name} as the cache within the config file:

    `dvc config cache.gs {dvc-cache-name}`

7. Add {your-remote-wfs} as a remote working file system – this is done by adding it in the local config:

    `dvc remote add --local remote-wfs gs://{your-gs-bucket}/{your-remote-wfs}/`

Success!