// smart-portfolio-ai/Jenkinsfile
pipeline {
    agent any

    environment {
        DEPLOY_DIR = '/home/totoro/Pythonproject/smart-portfolio-ai'
        PYTHON_BIN = 'python3'
        APP_PORT = '8501'
    }

    stages {
        stage('Sync Files') {
            steps {
                sh '''
                    mkdir -p ${DEPLOY_DIR}/data
                    rsync -av --exclude='.venv' --exclude='venv' --exclude='data/users.db' --exclude='.git' ./ ${DEPLOY_DIR}/
                '''
            }
        }

        stage('Setup Virtualenv & Dependencies') {
            steps {
                sh '''
                    cd ${DEPLOY_DIR}
                    if [ ! -d ".venv" ]; then
                        ${PYTHON_BIN} -m venv .venv
                    fi
                    .venv/bin/pip install --upgrade pip
                    .venv/bin/pip install -r requirements.txt
                '''
            }
        }

        stage('Deploy & Restart') {
            steps {
                sh '''
                    cd ${DEPLOY_DIR}
                    if [ ! -f ".env" ]; then
                        touch .env
                    fi

                    # pm2 describe 실행 시 에러가 나더라도 sh 스크립트가 중단되지 않도록 || true 처리
                    if pm2 describe smart-portfolio-ai > /dev/null 2>&1; then
                        echo "Existing process found. Reloading..."
                        pm2 restart smart-portfolio-ai
                    else
                        echo "Starting new process..."
                        pm2 start .venv/bin/streamlit --name "smart-portfolio-ai" -- run app.py --server.port=${APP_PORT} --server.address=0.0.0.0
                    fi
                    
                    pm2 save
                '''
            }
        }
    }

    post {
        success {
            echo 'Deployment successfully completed!'
        }
        failure {
            echo 'Deployment failed. Check Jenkins logs.'
        }
    }
}