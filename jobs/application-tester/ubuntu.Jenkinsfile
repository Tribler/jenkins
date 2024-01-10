pipeline {
    agent { label 'tester_ubuntu' }
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
        booleanParam(name: 'SILENT', defaultValue: true, description: 'Run in silent mode?')
        string(name: 'DURATION', defaultValue: '30', description: 'Duration of the test in minutes')
    }
    environment {
        SENTRY_URL = credentials('TEST_SENTRY_URL')
        TRIBLER_PASSWORD=credentials('TRIBLER_USER_PASSWORD')
        SKIP_VERSION_CLEANUP = 'TRUE'
        CORE_API_PORT = '8085'
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
                        python3 deploy_ubuntu.py
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
                        if [ "${params.SILENT}" = "false" ]; then
                            SILENT_ARG=
                        else
                            SILENT_ARG="-s"
                        fi

                        ls -l
                        #tree
                        cd tribler
                        export PYTHONPATH=./scripts/application_tester:./src
                        python3 ./scripts/application_tester/main.py "${params.TRIBLER_EXE_PATH}" --duration ${params.DURATION} --monitordownloads 10 --monitorresources 60 --monitoripv8 30

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
