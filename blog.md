# CML with Jenkins in DagsHub

## Topics to Cover:

- Jenkins Local Setup
- Standard Jenkins pipeline for CI
- Steps to incorporate DVC pipeline with CI Pipeline
- Enhanced PR review process with Jenkins + Dagshub integration
- Using Jenkins for your remote training

## Problems to be addressed by CML:

- Collaboration in DS mainly needs experiment comparison, over other checks like
  - Code changes check
  - Tests, linting
  - Build passing
- Most often we may not be able to execute experiments in our local machine, because
  - Reourse contraints: CPU. GPU, Memory, Network
  - Time contraint _(few models may need days of training)_
  - Also we would like to automate the process to reduce errors

## Background

- DVC is a great tool to have in our arsenal to deine
  - Version Data, models
  - Define DS end-to-end pipeline
  - Track experiments
  - Compare experiments
- Jenkins is an open source generic CI/CD pipeline

## Solution

- Running tests and linting
- Check if dvc.lock file is upto date
- Check if all the artifacts are pused to dvc shared remote
- Execute experiment on behalf of the user
- Automation of remote training

---

# TLDR

- Data Science projects are unique in its own ways, but still can adapt lot of learning from Software Delivery Projects and Practices.
- MLops is under the umberlla of Devops, addresses rituals to take models running in DS laptops to production.
- DS pull request from DagsHub and CML from DVC addresses few neuanses of applying standard CI/CD practices to ML projects.
- This blog talks about extending same idea to implement the same using Jenkins and DVC pipelines.

# By the end of this you would be able to:

- Standardize integration standard and be able to do it continuosly.
- Setup Jenkins pipeline for your project.
- Learn a simple and elegant way of managing experiment, i.e features in DS projects.

# Prerequisite:

- Setup a running Jenkins Sever, which executes your CI pipeline. You can follow instructions in [JenkinsDockerSetup](https://dagshub.com/puneethp/JenkinsDockerSetup) to do so.
- Setup end to end Machine Learning Pipeline with DVC to make you experiments reproducible and version you data/models.

# Standard Jenkins pipeline for CI

The reference project has been developed in Python, but the same concepts should be applicable to other technology ML projects.
Once you have a running Jenkins Sever and defined End-to-End experimentation ML pipeline we can integrate it with Jenkins CI/CD pipeline.

## Job setup:

It is a good practice to define jobs, to be run inside a Docker Container.

This enables to have an easy, maintainable, reproducible and standard setup for jobs. Also debugging environment specific issues becomes easier as we can reproduce the jobs execution env conditions in our local.

Jenkins enalbes us to define `agent`s to be a docker container, which can be brought up from an `docker image` or from a customised image defined in a `Dockerfile`. More on the same can be checked at [Using Docker with Pipeline](https://www.jenkins.io/doc/book/pipeline/docker/) section of their [Pipeline](https://www.jenkins.io/doc/book/pipeline/) documentation.

### Jenkins Agent:

- Here we define the `agent` to be a container brought up from this [Dockerfine](./Dockerfile).
- Repo will be mounted to `/project` path inside the container.
- We have also mounted `/extras` volume to cache any files, between multiple job runs.

Agent Definition:

```Groovy
agent {
    dockerfile {
        args "-v ${env.WORKSPACE}:/project -w /project -v /extras:/extras -e PYTHONPATH=/project"
    }
}
```

Agent [Dockerfile](./Dockerfile):

Here we define base image, install the required software and library dependencies.

```Dockerfile
FROM python:3.8                      # Base image for our job
RUN pip install --upgrade pip && \
    pip install -U setuptools==49.6.0
RUN apt-get update && \
    apt-get install unzip groff -y
RUN curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip" && \
    unzip awscliv2.zip && \
    ./aws/install                    # Installing aws-cli to use S3 as remote storage
COPY requirements.txt ./

RUN pip install -r requirements.txt  # Installing project dependenices
```

[.dockerignore](./.dockerignore)

```.dockerignore
*                    # Ignores everything

!requirements.txt    # except requirements.txt file
```

## Stages

As we have defined our `agent`, now we can define stages in our pipeline.

Here are few stages that we define in our Jeninks pipeline:

- Run Unit tests
- Run Linting tests
- DVC specific stages
  - Setup DVC remote connection
  - Sync DVC remotes
  - On Pull Request
    - Execute DVC experiment/pipeline end-to-end
    - Compare the results
    - Commit back the experiment to the experiment/feature branch

### Run Unit Tests:

We have defined our test cases in [test folder](./test) and using [pytest](https://docs.pytest.org/en/latest/) to run them for us.

```Groovy
stage('Run Unit Test') {
    steps {
        sh 'pytest -vvrxXs'
    }
}
```

### Run Linting Test:

For linting check as standard practice we use [flake8](https://flake8.pycqa.org/en/latest/) and [black](https://black.readthedocs.io/en/stable/).

```Groovy
stage('Run Linting') {
    steps {
        sh '''
            flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
            flake8 . --count --max-complexity=10 --max-line-length=127 --statistics
            black . --check --diff
        '''
    }
}
```

## DVC Stanges:

### Setup DVC remote connection:

Once you have setup [credentials](https://www.jenkins.io/doc/book/using/using-credentials/) in Jenkins, we can use it in a stage as follows. With `dvc status -r origin` we test our connect with the remote. DVC remote informations are define in file [.dvc/config](./.dvc/config) file.

```Groovy
stage('Setup DVC Creds') {
    steps {
        withCredentials(
            [
                usernamePassword(
                    credentialsId: 'PASSWORD',
                    passwordVariable: 'PASSWORD',
                    usernameVariable: 'USER_NAME'),
            ]
        ) {
            sh '''
                dvc remote modify origin --local auth basic
                dvc remote modify origin --local user $USER_NAME
                dvc remote modify origin --local password $PASSWORD
                dvc status -r origin
            '''
        }
    }
}
```

### Sync DVC remotes:

Before running any further DVC stanges, we would need to fetch the data and models versioned by DVC. This can be done with `dvc pull` command. But fetching files from `S3` or similar remote storages, it increases our network load, build latency and also service usages cost.

To optimise this we can cache already fetched files, say from previous builds and **only fetch the diff** required for the current build.

We will use the mounted volume `/extras` for this and refer it by dvc remote `jenkins_local`.

1. First we fetch cached files from `jenkins_local`.
2. Then we fetch diff by pulling from `origin`.
3. We then sync both the remotes, by pushing the diffs back to `jenkins_local`.

```Groovy
stage('Sync DVC Remotes') {
    steps {
        sh '''
            dvc status
            dvc status -r jenkins_local
            dvc status -r origin
            dvc pull -r jenkins_local || echo 'Some files are missing in local cache!'  # 1
            dvc pull -r origin                                                          # 2
            dvc push -r jenkins_local                                                   # 3
        '''
    }
}
```
