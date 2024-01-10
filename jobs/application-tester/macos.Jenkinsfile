pipeline {
    agent { label 'tester_macos' }
    parameters {
        string(
            name: 'ARTIFACT_JOB',
            defaultValue: 'https://jenkins.tribler.org/job/Tribler/job/Build/job/Build-All/',
            description: 'Upstream job that builds the artifacts'
        )
        string(
            name: 'DEPLOYMENT_SCRIPTS_REPO',
            defaultValue: 'https://github.com/tribler/jenkins',
            description: 'Github repository with deployment scripts'
        )
        string(
            name: 'DEPLOYMENT_SCRIPTS_REPO_BRANCH',
            defaultValue: 'master',
            description: 'Branch to checkout on Github repository with deployment scripts'
        )
        string(name: 'GIT_REPOSITORY', defaultValue: 'https://github.com/tribler/tribler.git', description: 'Git Repository')
        string(name: 'GIT_BRANCH', defaultValue: 'main', description: 'Git branch')
        string(name: 'TRIBLER_EXE_PATH', defaultValue: '/usr/share/tribler/tribler', description: 'Tribler executable path')
        string(name: 'DURATION', defaultValue: '30', description: 'Duration of the test in minutes')
    }
    environment {
        SENTRY_URL = credentials('TEST_SENTRY_URL')
        TRIBLER_PASSWORD=credentials('TRIBLER_USER_PASSWORD')
        SKIP_VERSION_CLEANUP = 'TRUE'
        CORE_API_PORT = '8085'
        LC_ALL = 'en_US.UTF-8'
        LANG = 'en_US.UTF-8'
        LANGUAGE = 'en_US.UTF-8'
    }
    stages {
        stage('Install binaries') {
            environment {
                JENKINS_JOB_URL = "${params.ARTIFACT_JOB}"
            }
            steps {
                cleanWs()
                checkout scm: [
                    $class: 'GitSCM',
                    branches: [[name: params.DEPLOYMENT_SCRIPTS_REPO_BRANCH]],
                    clean: true,
                    userRemoteConfigs: [[url: params.DEPLOYMENT_SCRIPTS_REPO]],
                    extensions: [[$class: 'RelativeTargetDirectory', relativeTargetDir: 'deployment_scripts']]
                ]
                script {
                    sh '''
                        #!/bin/bash
                        cd deployment_scripts
                        python3 -m virtualenv venv
                        . venv/bin/activate
                        pip3 install requests sentry_sdk pydantic==1.10.11 file-read-backwards==3.0.0 psutil==5.9.5 colorlog==6.7.0
                        python3 deploy_mac.py
                        deactivate

                        cp -rf $WORKSPACE/Tribler.app $HOME
                    '''
                }
            }
        }
        stage('Run application tester') {
            steps {
                cleanWs()
                checkout scm: [
                    $class: 'GitSCM',
                    branches: [[name: params.GIT_BRANCH]],
                    clean: true,
                    userRemoteConfigs: [[url: params.GIT_REPOSITORY]],
                    extensions: [[$class: 'RelativeTargetDirectory', relativeTargetDir: 'tribler']]
                ]
                script {
                    sh """
                        #!/bin/bash
                        cd tribler
                        python3 -m virtualenv venv
                        . venv/bin/activate

                        pip3 install requests sentry_sdk pydantic==1.10.11 file-read-backwards==3.0.0 psutil==5.9.5 colorlog==6.7.0 configobj aiohttp

                        export PYTHONPATH=./scripts/application_tester:./src
                        python3 ./scripts/application_tester/main.py "${HOME}/Tribler.app/Contents/MacOS/tribler" --duration ${params.DURATION}

                        deactivate

                        Rscript ./scripts/application_tester/scripts/downloads.r
                        Rscript ./scripts/application_tester/scripts/resources.r
                        Rscript ./scripts/application_tester/scripts/ipv8_stats.r
                        Rscript ./scripts/application_tester/scripts/circuits.r
                        Rscript ./scripts/application_tester/scripts/requests.r
                    """
                }
            }
            post {
                success {
                    archiveArtifacts artifacts: 'tribler/output/**', fingerprint: true, allowEmptyArchive: true
                }
            }
        }
    }

}
