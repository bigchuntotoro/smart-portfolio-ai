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

                    # 에러 상태인 기존 프로세스가 있다면 삭제 후 재등록
                    if pm2 describe smart-portfolio-ai >/dev/null 2>&1; then
                        echo "Cleaning up existing process..."
                        pm2 delete smart-portfolio-ai
                    fi

                    echo "Starting Streamlit app with Python interpreter..."
                    pm2 start .venv/bin/streamlit \
                      --name "smart-portfolio-ai" \
                      --interpreter .venv/bin/python3 \
                      -- run app.py --server.port=${APP_PORT} --server.address=0.0.0.0

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