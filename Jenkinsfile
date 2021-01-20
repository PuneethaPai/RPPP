/* groovylint-disable CompileStatic, DuplicateMapLiteral, DuplicateStringLiteral, LineLength, NestedBlockDepth */
pipeline {
    agent any
    environment {
        GIT_COMMIT_REV = sh(returnStdout: true, script: 'git rev-parse --short HEAD').trim()
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
                            dvc repro --dry -mP
                            dvc repro -mP
                            git branch -a
                            cat dvc.lock
                            dvc push -r jenkins_local
                            dvc push -r origin
                            rm -r /extras/RPPP/repo/$CHANGE_BRANCH || echo 'All clean'
                            mkdir -p /extras/RPPP/repo/$CHANGE_BRANCH
                            cp -Rf . /extras/RPPP/repo/$CHANGE_BRANCH
                        '''
                        sh 'dvc metrics diff --show-md --precision 2 $CHANGE_TARGET'
                    }
                }
            }
        }
        stage('Commit back results') {
            when { changeRequest() }
            steps {
                dir("/extras/RPPP/repo/${env.CHANGE_BRANCH}") {
                    sh '''
                        git branch -a
                        git status
                        if ! git diff --exit-code dvc.lock; then
                            git add .
                            git status
                            git commit -m '$GIT_COMMIT_REV: Update dvc.lock and metrics'
                            git push origin HEAD:$CHANGE_BRANCH
                        else
                            echo 'Nothing to Commit!'
                        fi
                    '''
                }
            }
        }
    }
}
