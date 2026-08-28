// smart-portfolio-ai/Jenkinsfile
pipeline {
    agent any

    environment {
        DEPLOY_DIR = '/home/totoro/Pythonproject/smart-portfolio-ai'
        PYTHON_BIN = 'python3'
        APP_PORT = '8501'
        PATH = "/usr/local/bin:/usr/bin:/bin:${env.PATH}"
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

        stage('Deploy & Start with PM2') {
            steps {
                sh '''
                    cd ${DEPLOY_DIR}
                    if [ ! -f ".env" ]; then
                        touch .env
                    fi

                    # PM2에 해당 서비스가 등록되어 있는지 확인
                    if pm2 describe smart-portfolio-ai >/dev/null 2>&1; then
                        echo "Existing process found. Restarting..."
                        pm2 restart smart-portfolio-ai
                    else
                        echo "Starting new PM2 process..."
                        pm2 start .venv/bin/streamlit \
                          --name "smart-portfolio-ai" \
                          -- run app.py --server.port=${APP_PORT} --server.address=0.0.0.0
                    fi

                    # 현재 PM2 프로세스 상태 저장 (부팅 시 자동 재시작 유지용)
                    pm2 save
                '''
            }
        }
    }

    post {
        success {
            echo 'Deployment successfully completed and PM2 process is running!'
        }
        failure {
            echo 'Deployment failed. Check Jenkins logs.'
        }
    }
}