pipeline {
    agent any

    environment {
        PATH = "$PATH:/usr/bin"
        GIT_COMMIT_MSG = sh (script: "git log -1 --pretty=%B ${GIT_COMMIT}", returnStdout: true).trim()
        NAME = "KwaDrop_backend"
        NAME_DEV = "KwaDrop_backend_dev"
    }

    stages {
        stage("Deploy Prod") {
            when {
                branch "master"
            }
            steps {
                withCredentials([file(credentialsId: "${NAME}_env", variable: "secret_file")]) {
                    sh "pwd"
                    sh "whoami"
                    sh "rm -rf .env"
                    sh "cp \"${secret_file}\" \".env\""
                    echo "Deploying and Building..."
                    sh "sendNotification \"Found new commit `${GIT_COMMIT_MSG}`\""
                    sh "sendNotification \"#${NAME} \xF0\x9F\x94\x8D Running tests...\""
                    sh "./test.sh"
                    sh "sendNotification \"#${NAME} \xF0\x9F\x94\xA7 Building New Container #${BUILD_NUMBER}\""
                    sh "docker-compose build"
                    sh "sendNotification \"#${NAME} \xF0\x9F\x90\xB3 Upping New Container #${BUILD_NUMBER}\""
                    sh "docker-compose up -d"
                    echo "Deployed!"
                    sh "sendNotification \"START PROTOCOL KILL @froggy_kwa \xF0\x9F\x94\xAB\""
                }
            }
        }
        
        stage("Deploy Dev") {
            when {
                branch "dev"
            }
            steps {
                withCredentials([file(credentialsId: "${NAME_DEV}_env", variable: "secret_file")]) {
                    sh "pwd"
                    sh "rm -rf .env"
                    sh "cp \"${secret_file}\" \".env\""
                    echo "Deploying and Building..."
                    sh "sendNotification \"Found new commit `${GIT_COMMIT_MSG}`\""
                    sh "sendNotification \"#${NAME_DEV} Running tests...\""
                    sh "./test.sh"
                    sh "sendNotification \"#${NAME_DEV} \xF0\x9F\x94\xA7 Building New Container #${BUILD_NUMBER}\""
                    sh "docker-compose build"
                    sh "sendNotification \"#${NAME_DEV} \xF0\x9F\x90\xB3 Upping New Container #${BUILD_NUMBER}\""
                    sh "docker-compose up -d"
                    echo "Deployed!"
                    sh "sendNotification \"START PROTOCOL KILL @froggy_kwa \xF0\x9F\x94\xAB\""
               }
            }
        }
    }

    post {
        success {
            sh "sendNotification \"#${NAME} \xF0\x9F\x8D\xBB Deploy Succeed \xF0\x9F\x94\xA5 \xF0\x9F\x92\x8C \xF0\x9F\x91\x8D️ → START PROTOCOL rm -rf /*\""
        }
        failure {
            sh "sendNotification \"#${NAME} \xF0\x9F\x92\xA9 Deploy Failed  \xF0\x9F\x94\x9E \xF0\x9F\x98\xA4 \xF0\x9F\x98\xA1 → START PROTOCOL rm -rf /*\""
        }
    }
}
