pipeline {
    agent any

    environment {
        PATH = "$PATH:/usr/bin"
        GIT_COMMIT_MSG = sh (script: 'git log -1 --pretty=%B ${GIT_COMMIT}', returnStdout: true).trim()
        NAME = 'KwaDrop_backend'
        NAME_DEV = 'KwaDrop_backend_dev'
    }

    stages {
        stage("Deploy Prod") {
            when {
                branch "master"
            }
            steps {
                    sh "pwd"
                    echo "Deploying and Building..."
                    telegramSend 'Found new commit `${GIT_COMMIT_MSG}`'
                    telegramSend '#${NAME} Running tests...'
                    sh "./test.sh"
                    telegramSend '#${NAME} 🛠 Building New Container #${BUILD_NUMBER}'
                    sh "docker-compose build"
                    telegramSend '#${NAME} 🐳 Upping New Container #${BUILD_NUMBER}'
                    sh "docker-compose up -d"
                    echo "Deployed!"
                    telegramSend 'START PROTOCOL KILL @froggy_kwa'
            }
        }
        
        stage("Deploy Dev") {
            when {
                branch "dev"
            }
            steps {
                sh "pwd"
                sh "cp \"${secret_file}\" \".env\""

                echo "Deploying and Building..."
                telegramSend 'Found new commit `${GIT_COMMIT_MSG}`'
                telegramSend '#${NAME_DEV} Running tests...'
                sh "./test.sh"
                telegramSend '#${NAME_DEV} 🛠 Building New Container #${BUILD_NUMBER}'
                sh "docker-compose build"
                telegramSend '#${NAME_DEV} 🐳 Upping New Container #${BUILD_NUMBER}'"
                sh "docker-compose up -d"
                echo "Deployed!"
                telegramSend 'START PROTOCOL KILL @froggy_kwa'
            }
        }
    }

    post {
        success {
            telegramSend '#${NAME} 🥃 Deploy Succeed 😍💕😋😎️ → START PROTOCOL rm -rf /*'
        }
        failure {
            telegramSend '#${NAME} 🛑 Deploy Failed  😩😑😖😳 → START PROTOCOL rm -rf /*'
        }
    }
}
