pipeline {
    agent { label 'tester_win64' }
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
        string(name: 'TRIBLER_EXE_PATH', defaultValue: 'C:\\Program Files\\Tribler\\tribler.exe', description: 'Tribler executable path')
        string(name: 'DURATION', defaultValue: '30', description: 'Duration of the test in minutes')
    }
    environment {
        SENTRY_URL = credentials('TEST_SENTRY_URL')
        SKIP_VERSION_CLEANUP = 'TRUE'
        CORE_API_PORT = '8085'
        LC_ALL = 'en_US.UTF-8'
        LANG = 'en_US.UTF-8'
        LANGUAGE = 'en_US.UTF-8'
        DURATION = "${params.DURATION}"
        TRIBLER_EXE_PATH = "${params.TRIBLER_EXE_PATH}"
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
                    bat '''
                        cd deployment_scripts

                        REM Creating a virtual environment
                        python -m venv venv
                    '''

                    bat '''
                        cd deployment_scripts
                        dir

                        REM Activating virtual environment
                        call venv\\Scripts\\activate.bat
                        pip3 install -r requirements.txt

                        REM Killing a specific task
                        taskkill /im tribler.exe /f
                        timeout /t 5

                        REM Checking if a file exists and running it
                        if exist "C:\\Program Files\\Tribler\\Uninstall.exe" (
                            "C:\\Program Files\\Tribler\\Uninstall.exe" /S
                        )

                        REM Running the Python deployment script
                        python deploy_windows.py

                        REM Deactivating the virtual environment
                        call venv\\Scripts\\deactivate.bat
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
                    bat '''
                        cd tribler

                        REM Creating a virtual environment
                        python -m venv venv
                    '''

                    withCredentials([string(credentialsId: 'TRIBLER_USER_PASSWORD', variable: 'TRIBLER_PASSWORD')]) {
                        bat """
                            REM Check the SILENT parameter
                            if "%params.SILENT%"=="false" (
                                set SILENT_ARG=
                            ) else (
                                set SILENT_ARG=-s
                            )

                            REM List directory contents
                            dir

                            REM Move to the tribler directory
                            cd tribler

                            REM Activating virtual environment
                            call venv\\Scripts\\activate.bat
                            pip3 install sentry_sdk pydantic==1.10.11 file-read-backwards==3.0.0 psutil==5.9.5 colorlog==6.7.0
                            pip3 install -r requirements.txt

                            REM Set the PYTHONPATH environment variable
                            set PYTHONPATH=%PYTHONPATH%;./scripts/application_tester;./src

                            REM Run the Python script
                            echo python ./scripts/application_tester/main.py "%TRIBLER_EXE_PATH%" --duration %DURATION%
                            python ./scripts/application_tester/main.py "%TRIBLER_EXE_PATH%" --duration %DURATION%

                            REM Deactivating the virtual environment
                            call venv\\Scripts\\deactivate.bat

                            REM Run R scripts
                            Rscript ./scripts/application_tester/scripts/downloads.r
                            Rscript ./scripts/application_tester/scripts/resources.r
                            Rscript ./scripts/application_tester/scripts/ipv8_stats.r
                            Rscript ./scripts/application_tester/scripts/circuits.r
                            Rscript ./scripts/application_tester/scripts/requests.r
                        """
                    }
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
