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
                        sh 'flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics'
                        sh 'flake8 . --count --max-complexity=10 --max-line-length=127 --statistics'
                        sh 'black . --check --diff'
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
                                dvc pull -r origin
                            '''
                        }
                    }
                }
                stage('Sync DVC Remotes') {
                    steps {
                        sh 'dvc status'
                        sh 'dvc status -r jenkins_local'
                        sh 'dvc status -r origin'
                        script {
                            try {
                                sh 'dvc pull -r jenkins_local'
                            } catch (error) {
                                echo error.message
                            }
                        }
                        echo currentBuild.result
                        sh 'dvc pull -r origin'
                        sh 'dvc push -r jenkins_local'
                    }
                }
                stage('Update DVC Pipeline') {
                    when { changeRequest() }
                    steps {
                        sh 'dvc repro --dry -mP'
                        sh 'dvc repro -mP'
                        sh 'git branch -a'
                        sh "dvc metrics diff --show-md --precision 2 ${env.CHANGE_TARGET}"
                        sh 'cat dvc.lock'
                        sh 'dvc push -r jenkins_local'
                        sh 'dvc push -r origin'
                        sh "rm -r /client_wip/repo/${env.CHANGE_BRANCH} || echo 'All clean'"
                        sh "mkdir -p /client_wip/repo/${env.CHANGE_BRANCH}"
                        sh "cp -Rf . /client_wip/repo/${env.CHANGE_BRANCH}"
                    }
                }
            }
        }
        stage('Commit back results') {
            when { changeRequest() }
            steps {
                dir("/extras/RPPP/repo/${env.CHANGE_BRANCH}") {
                    sh 'git branch -a'
                    sh 'git status'
                    sh 'git add .'
                    sh 'git status'
                    sh "git commit -m '${env.GIT_COMMIT_REV}: Update dvc.lock and metrics' || echo 'Nothing to Commit'"
                    sh "git push origin HEAD:${env.CHANGE_BRANCH}"
                }
            }
        }
    }
}
