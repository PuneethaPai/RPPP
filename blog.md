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

This enables to have an easy, maintainable, reproducible and isolated job environment setup. Also debugging environment specific issues becomes easier as we can reproduce the jobs execution env conditions anywhere.

To do so Jenkins enalbes us to define `agent`'s to be a docker container; which can be brought up from an `image` or from a customised image, defined in a [`Dockerfile`](./Dockerfile).

More on the same can be checked at [Using Docker with Pipeline](https://www.jenkins.io/doc/book/pipeline/docker/) section of their [Pipeline](https://www.jenkins.io/doc/book/pipeline/) documentation.

In next section, we will go through how we have defined our JenkinsAgent.

## Jenkins Agent:

Here we define the `agent` to be a container brought up from this [Dockerfine](./Dockerfile).

Agent Definition:

```Groovy
agent {
    dockerfile {
        args "-v ${env.WORKSPACE}:/project -w /project -v /extras:/extras -e PYTHONPATH=/project"
    }
}
```

Details:

- Repo has been mounted inside the container to `/project`.
- `-w /project` make sures that all our pipeline stage commands are executed inside our repo directory.
- We have also mounted `/extras` volume to cache any files, between multiple job runs. This will help in reducing build latency. For more info check [Sync DVC remotes](#Sync-DVC-remotes) pipeline stage.

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

!requirements.txt    # except requirements.txt file ;)
```

In next section we will be defining stages in our pipeline.

## Stages

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

We have defined all our test cases in the [test folder](./test) and using [pytest](https://docs.pytest.org/en/latest/) to run them for us.

```Groovy
stage('Run Unit Test') {
    steps {
        sh 'pytest -vvrxXs'
    }
}
```

### Run Linting Test:

For linting check, as standard practice we will use [flake8](https://flake8.pycqa.org/en/latest/) and [black](https://black.readthedocs.io/en/stable/).

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

With `dvc status -r origin` we test our connect with the remote. DVC remote informations are defined in the config, [.dvc/config](./.dvc/config) file.

### Sync DVC remotes:

Before running any further DVC stanges, we would need to fetch already versioned data and models files from DVC. This can be done with `dvc pull` command.

Everytime while we fetch DVC versioned files from `S3` or similar remote storages, it increases our network load, build latency and also service usages cost.

To optimise this we can cache already fetched files, say from previous builds. Then in consequent builds we can **only fetch the required diff**.

We will use the mounted volume `/extras` for this and refer it by dvc remote `jenkins_local`. More info [.dvc/config](./.dvc/config) file.

**While `origin` is our primary storage, we use `jenkins_local` as a secondary local storage! :exploading_head:**

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
2. Then we only fetch the required diffs, by pulling from `origin`.
3. We then sync both the remotes, by pushing the diffs back to `jenkins_local`.

### Update DVC Pipeline:

Once you have defined [`dvc pipeline`](https://dvc.org/doc/start/data-pipelines) running your expeirment is stright forward with [`dvc repro`](https://dvc.org/doc/command-reference/repro) cmd. Every run of your dvc pipeline _can potentially create_ new versions of data, models and metrics.

Hence the question is **When should you run your Experiments?**

Should we run for:

- All the commits?
- Only for changes in, `master` branch?
- Should we set up some manual trigger?
- Based on "special" commit message syntax?
- or **On Pull request?**

Let's analyze pros and cons for each of these options:

| Options                              | Pros                                                                                                                      | Cons                                                                                                                                                    |
| :----------------------------------- | :------------------------------------------------------------------------------------------------------------------------ | :------------------------------------------------------------------------------------------------------------------------------------------------------ |
| For All Commits                      | We will never miss any experiment                                                                                         | This will increase build latency. May be overkill to run for all commits/changes                                                                        |
| Only for changes in, `master` branch | Only master branch experiments are saved                                                                                  | Only master branch experiments are saved. "Bad" experiments can slip through the PR review process and gets merged to master, before we could catch it. |
| Setup a manual trigger               | We can decide when we want to run/skip experiment.                                                                        | Automation is not complete. There is room for manual errors.                                                                                            |
| "Special" Commit message syntax      | We can decide when we want to run/skip experiment.                                                                        | Automation is not complete. There is room for manual errors.                                                                                            |
| **On Pull Request**                  | We can run and compare experiment, before we approve the PR. No "Bad" experiments can now slip through PR review process. | **None**                                                                                                                                                |

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

Here `$CHANGE_BRANCH` refers to Pull request **source** branch and `$CHANGE_TARGET` refers to Pull request **target** branch.

1. `when { changeRequest() }` Makes sures to run this `stage` only when Pull Request is open/modified/updated.
2. `dvc repro -mP` runs the pipeline end-to-end and also prints the final metrices.
3. `dvc push` saves the results _(data & models)_ to remote storages.
4. `dvc metrics diff` compares the metrics in PR source vs PR target.

### Commit back Results:

Once the DVC pipeline is run, it will version the experiment results and modifies corresponding metadata in the [`dvc.lock`](./dvc.lock) file.

When we commit this [`dvc.lock`](./dvc.lock) file into git, we can say the experiment is saved successfully.

For a given git commit, looking at [`dvc.lock`](./dvc.lock) file, DVC will understand which versions of files to be loaded from the [cache](./.dvc/cache). We can checkout that perticular version by [`dvc checkout`](https://dvc.org/doc/command-reference/checkout) cmd.

Now in this stage `Commit back Results` all we have to do is check if [`dvc.lock`](./dvc.lock) file got modified?, then commit and push it to our `feature/experiment` branch.

```Groovy
stage('Commit back results') {
    when { changeRequest() }
    steps {
        dir("/extras/RPPP/repo/${env.CHANGE_BRANCH}") {
            sh '''
                git branch -a
                git status
                if ! git diff --exit-code; then                                   # 1
                    git add .
                    git status
                    git commit -m '$GIT_COMMIT_REV: Update dvc.lock and metrics'  # 2
                    git push origin HEAD:$CHANGE_BRANCH                           # 3
                else
                    echo 'Nothing to Commit!'                                     # 4
                fi
            '''
        }
    }
}
```

Explaination:

1. `git diff --exit-code` to check if there are un-committed changes.
2. `git commit -m '$GIT_COMMIT_REV: ...` to commit with reference to parent commit `$GIT_COMMIT_REV`. This helps us also understand for which user commit the experiment was run by our Jenkins Pipeline.
3. `git push origin HEAD:$CHANGE_BRANCH` to push to our experiment/feature branch saved in environment variable `$CHANGE_BRANCH`.
4. Else part to print there was nothing to commit. This means the DVC pipeline is already up to date.
