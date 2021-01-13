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

- Data Science projects are unique in its own ways, but still can adapt lot of learning from Software Delivery Principles and Projects.
- MLops is comes under the umberlla of Devops. It addresses, the rituals to take models running in DS laptops to production.
- Versioning your data and models is the first step to achieve reproducible results and [DVC](https://dvc.org/) has done a great job on it.
- Adding to it, [DS Pull Request](https://dagshub.com/docs/collaborating_on_dagshub/data_science_pull_requests/) from [DagsHub](https://dagshub.com/) and [CML](https://cml.dev/) from DVC addresses few neuanses of applying standard CI/CD practices to ML projects.
- This blog talks about extending ideas of CML to implement using Jenkins and DVC pipelines.
- If it's one thing, you want to get from this blog; that would be the [Jenkinsfile](./Jenkinsfile) file.

# By the end of this you would be able to:

- Setup Jenkins pipeline for your project.
- Define end-to-end ML pipeline with DVC.
- Standardize continuous integration practices in the team.
- Learn a simple and elegant way of managing experiment, i.e features in DS projects.

# Prerequisite:

- Setup a running Jenkins Sever, which executes your CI pipeline. You can follow instructions in [JenkinsDockerSetup](https://dagshub.com/puneethp/JenkinsDockerSetup) to do so.
- Setup end-to-end Machine Learning Pipeline with DVC to make you experiments reproducible and version you data/models. Learn more about [dvc pipeline](https://dvc.org/doc/start/data-pipelines).

# Standard Jenkins pipeline for CI

The reference project has been developed in Python, but the same concepts should be applicable to other technology ML projects.

The core of this blog revolves around the [Jenkinsfile](./Jenkinsfile). Stick till the end, to know the details of all moving parts. :smile:

# Jenkins Pipeline:

It is a good practice to define jobs, to run inside a Docker Container.

This enables to have an easy, maintainable, reproducible and isolated job environment setup. Also debugging environment specific issues becomes easier as we can reproduce the jobs execution env anywhere.

To do so Jenkins enalbes us to define `agent`s to be a docker container, which can be brought up from an `image` or from a customised image, defined in a [`Dockerfile`](./Dockerfile).

More on the same can be checked at [Using Docker with Pipeline](https://www.jenkins.io/doc/book/pipeline/docker/) section of their [Pipeline](https://www.jenkins.io/doc/book/pipeline/) documentation.

## Jenkins Agent:

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

Here we define the job container's base image; install the required software and library dependencies.

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

To help us define docker context when building the container image.

```.dockerignore
*                    # Ignores everything

!requirements.txt    # except requirements.txt file
```

## Stages

As we have defined our `agent`, now we can define stages in our pipeline.

Here are few stages that we will be defining in our Jeninks Pipeline:

- Run Unit tests
- Run Linting tests
- DVC specific stages
  - Setup DVC remote connection
  - Sync DVC remotes
  - On Pull Request
    - Execute end-to-end DVC experiment/pipeline
    - Compare the results
    - Commit back the results to the experiment/feature branch

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

Once you have setup [credentials](https://www.jenkins.io/doc/book/using/using-credentials/) in Jenkins, we can use it in a stage as follows.

With `dvc status -r origin` we test our connect with the remote. DVC remote informations are defined in the config, [.dvc/config](./.dvc/config) file.

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

Before running any further DVC stanges, we would need to fetch the data and models already versioned by DVC. This can be done with `dvc pull` command.

Everytime while we fetch files from `S3` or similar remote storages, it increases our network load, build latency and also service usages cost.

To optimise this we can cache already fetched files, say from previous builds and **only fetch the diff** required for the consequent builds.

We will use the mounted volume `/extras` for this and refer it by dvc remote `jenkins_local`. More info [.dvc/config](./.dvc/config) file.

**While `origin` is our primary storage, we use `jenkins_local` as a secondary local storage!**

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

Explaination:

1. First we fetch cached files from `jenkins_local`.
2. Then we only fetch diffs, by pulling from `origin`.
3. We then sync both the remotes, by pushing the diffs back to `jenkins_local`.

### Update DVC Pipeline:

Once you have defined [`dvc pipeline`](https://dvc.org/doc/start/data-pipelines) running your expeirment is stright forward with [`dvc repro`](https://dvc.org/doc/command-reference/repro) cmd.

But the question is **When should you run your Experiments?**

Should we run for:

- All the commits?
- Only for changes in, `master` branch?
- Should we set up some manual trigger?
- Based on commit message syntax?
- or **On Pull request?**

Let's analyze pros and cons for each of these options:

| Option                               | Pros                                                         | Cons                                                                                                                  |
| :----------------------------------- | :----------------------------------------------------------- | :-------------------------------------------------------------------------------------------------------------------- |
| For All Commits                      | - We will never miss any experiment                          | - Will increase build latency - May not be needed to be run for all commits/changes                                   |
| Only for changes in, `master` branch | Only master branch experiments are saved                     | - Only master branch experiments are saved - "Bad" experiments or PR gets merged to master, before we could catch it. |
| Setup a manual trigger               | We can decide when we want to run/skip experiment.           | - Automation is not complete. - There is room for manual errors.                                                      |
| "Special" Commit message syntax      | We can decide when we want to run/skip experiment.           | - Automation is not complete. - There is room for manual errors.                                                      |
| **On Pull Request**                  | We can run and compare experiment, before we approve the PR. | **None**                                                                                                              |

```Groovy
stage('Update DVC Pipeline') {
    when { changeRequest() }                                            //# 1
    steps {
        sh '''
            dvc repro --dry -mP
            dvc repro -mP                                                 # 2
            git branch -a
            cat dvc.lock
            dvc push -r jenkins_local                                     # 3
            dvc push -r origin                                            # 3
            rm -r /extras/RPPP/repo/$CHANGE_BRANCH || echo 'All clean'
            mkdir -p /extras/RPPP/repo/$CHANGE_BRANCH
            cp -Rf . /extras/RPPP/repo/$CHANGE_BRANCH
        '''
        sh 'dvc metrics diff --show-md --precision 2 $CHANGE_TARGET'    //# 4
    }
}
```

Explaination:

`$CHANGE_BRANCH` refers to Pull request **source** and `$CHANGE_TARGET` refers to Pull request **target**

1. `when { changeRequest() }` Makes sures to run this `stage` only when Pull Request is open.
2. `dvc repro -mP` runs the pipeline end-to-end and prints the metrics at the end.
3. `dvc push` saves the results _(data & models)_ to remote storages.
4. `dvc metrics diff` compares the metrics in PR source vs PR target.
