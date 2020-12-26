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
