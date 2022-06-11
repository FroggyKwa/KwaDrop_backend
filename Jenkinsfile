pipeline {
    agent any

    environment {
        PATH = "$PATH:/usr/bin"
        GIT_COMMIT_MSG = sh (script: "git log -1 --pretty=%B ${GIT_COMMIT}", returnStdout: true).trim()
        NAME_DEV = "KwaDrop_backend"
        NAME_DEV = "KwaDrop_backend_dev"
    }

    stages {
        stage("Deploy Prod") {
            when {
                branch "master"
            }
            steps {
                withCredentials([file(credentialsId: "${NAME_DEV}_env", variable: "secret_file")]) {
                    sh "pwd"
                    sh "whoami"
                    sh "rm -rf .env"
                    sh "cp \"${secret_file}\" \".env\""
                    echo "Deploying and Building..."
                    sh "sendNotification \"Found new commit `${GIT_COMMIT_MSG}`\""
                    sh "sendNotification \"#${NAME_DEV} Running tests...\""
                    sh "./test.sh"
                    sh "sendNotification \"#${NAME_DEV} 🛠 Building New Container #${BUILD_NUMBER}\""
                    sh "docker-compose build"
                    sh "sendNotification \"#${NAME_DEV} 🐳 Upping New Container #${BUILD_NUMBER}\""
                    sh "docker-compose up -d"
                    echo "Deployed!"
                    sh "sendNotification \"START PROTOCOL KILL @froggy_kwa\""
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
                    sh "sendNotification \"#${NAME_DEV} 🛠 Building New Container #${BUILD_NUMBER}\""
                    sh "docker-compose build"
                    sh "sendNotification \"#${NAME_DEV} 🐳 Upping New Container #${BUILD_NUMBER}\""
                    sh "docker-compose up -d"
                    echo "Deployed!"
                    sh "sendNotification \"START PROTOCOL KILL @froggy_kwa\""
               }
            }
        }
    }

    post {
        success {
            sh "sendNotification \"#${NAME} 🥃 Deploy Succeed 😍💕😋😎️ → START PROTOCOL rm -rf /*\""
        }
        failure {
            sh "sendNotification \"#${NAME} 🛑 Deploy Failed  😩😑😖😳 → START PROTOCOL rm -rf /*\""
        }
    }
}
