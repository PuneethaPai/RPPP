/* groovylint-disable CompileStatic, DuplicateMapLiteral, DuplicateStringLiteral, LineLength, NestedBlockDepth */
pipeline {
    agent any
    environment {
        GIT_COMMIT_REV = sh(returnStdout: true, script: 'git rev-parse --short HEAD').trim()
        JENKINS_USER_NAME = 'JenkinsRPPP'
        JENKINS_EMAIL = 'jenkins@rpp.com'
    // GIT_COMMIT_MASTER = sh(returnStdout: true, script: 'git rev-parse --short master').trim()
    }
    stages {
        stage('Run inside Docker Image') {
            agent {
                dockerfile {
                    args "-v ${env.WORKSPACE}:/project -w /project -v /extras:/extras -e PYTHONPATH=/project"
                }
            }
            stages {
                stage('Run Unit Test') {
                    steps {
                        sh 'pytest -vvrxXs'
                    }
                }
                stage('Run Linting') {
                    steps {
                        sh '''
                            flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
                            flake8 . --count --max-complexity=10 --max-line-length=127 --statistics
                            black . --check --diff
                        '''
                    }
                }
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
                stage('Sync DVC Remotes') {
                    steps {
                        sh '''
                            dvc status
                            dvc status -r jenkins_local
                            dvc status -r origin
                            dvc pull -r jenkins_local || echo 'Some files are missing in local cache!'
                            dvc pull -r origin
                            dvc push -r jenkins_local
                        '''
                    }
                }
                stage('Update DVC Pipeline') {
                    when { changeRequest() }
                    steps {
                        sh '''
                            date >> a.txt
                            dvc repro --dry -mP
                            dvc repro -mP
                            git branch -a
                            cat dvc.lock
                            dvc push -r jenkins_local
                            dvc push -r origin
                            # rm -r /extras/RPPP/repo/$CHANGE_BRANCH || echo 'All clean'
                            # mkdir -p /extras/RPPP/repo/$CHANGE_BRANCH
                            # cp -Rf . /extras/RPPP/repo/$CHANGE_BRANCH
                        '''
                        sh 'dvc metrics diff --show-md --precision 2 $CHANGE_TARGET'
                    }
                }
                stage('Commit back results') {
                    when { changeRequest() }
                    steps {
                        withCredentials(
                            [
                                usernamePassword(
                                    credentialsId: 'GIT_PAT',
                                    passwordVariable: 'GIT_PAT',
                                    usernameVariable: 'GIT_USER_NAME'),
                            ]
                        ) {
                            sh '''
                                env
                                git branch -a
                                git status
                                if ! git diff --exit-code; then
                                    git add .
                                    git status
                                    git config --local user.email $JENKINS_EMAIL
                                    git config --local user.name $JENKINS_USER_NAME
                                    git commit -m '$GIT_COMMIT_REV: Update dvc.lock and metrics'
                                    git push https://$GIT_USER_NAME:$GIT_PAT@github.com/PuneethaPai/RPPP HEAD:$CHANGE_BRANCH
                                    cat ~/.git-credentials || echo 'Nothing Saved/cached'
                                else
                                    echo 'Nothing to Commit!'
                                fi
                            '''
                        }
                    }
                }
            }
        }
    }
}
