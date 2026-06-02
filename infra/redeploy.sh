#!/bin/bash
set -euo pipefail

# -----------------------------------------------------------------------------
# [실시간 로그 설정] 터미널 화면 출력과 동시에 /var/log/deploy.log 파일에 기록
# -----------------------------------------------------------------------------
exec &> >(stdbuf -oL -eL tee /var/log/deploy.log)

GIT_REPO_URL="https://github.com/55002ghals/2026-cloud-computing-days.git"
GIT_BRANCH="master"
DB_URL="postgresql+asyncpg://appuser:a-gXcJS-jCyr4XjAEPwyNZMcP8M@qna-diary-postgres.cby4uwwoo3ds.ap-northeast-2.rds.amazonaws.com/qnadiary"
APP_PASSWORD="inha-nxt"
SESSION_SECRET="B1nAH_8pNObWNGk0QmRhOK-vFFRKrOYkFg8iP6N1bg5-LglEUl_1-A"
BEDROCK_MODEL_ID="us.anthropic.claude-sonnet-4-6"
AWS_REGION="ap-northeast-2"

echo "==> [1/7] Installing System Packages..."
dnf install -y python3.11 python3.11-pip nodejs20 git nginx
dnf clean all

# -----------------------------------------------------------------------------
# [소스코드 동기화] /opt/app 이 이미 존재하면 clone 대신 pull 수행
# -----------------------------------------------------------------------------
echo "==> [2/7] Synchronizing Source Code..."
if [ -d "/opt/app/.git" ]; then
    echo "Info: /opt/app already exists with git repository. Fetching latest changes..."
    cd /opt/app
    git fetch origin "$GIT_BRANCH"
    git reset --hard "origin/$GIT_BRANCH"
else
    echo "Info: /opt/app does not exist. Cloning repository..."
    mkdir -p /opt/app
    git clone --branch "$GIT_BRANCH" "$GIT_REPO_URL" /opt/app
fi
chown -R ec2-user:ec2-user /opt/app

echo "==> [3/7] Setting up Python Virtual Environment..."
cd /opt/app/backend
python3.11 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt

# == Checking and Creating Database 'qnadiary' if not exists ==
echo "==> [4/7] Verifying Database Context..."
.venv/bin/python3 -u -c "
import asyncio
import asyncpg

async def init_database():
    try:
        conn = await asyncpg.connect('postgresql://appuser:a-gXcJS-jCyr4XjAEPwyNZMcP8M@qna-diary-postgres.cby4uwwoo3ds.ap-northeast-2.rds.amazonaws.com/postgres')
        exists = await conn.fetchval(\"SELECT EXISTS(SELECT 1 FROM pg_database WHERE datname = 'qnadiary')\")

        if not exists:
            await conn.execute('COMMIT')
            await conn.execute('CREATE DATABASE qnadiary')
            print(\"Success: 'qnadiary' database has been created.\", flush=True)
        else:
            print(\"Info: 'qnadiary' database already exists. Skipping creation.\", flush=True)

        await conn.close()
    except Exception as e:
        print(f\"Warning/Error during DB creation: {e}\", flush=True)

asyncio.run(init_database())
"

echo "==> [5/7] Building Frontend Assets..."
cd /opt/app/frontend
npm ci
npm run build
rm -rf node_modules

echo "==> [6/7] Configuring System Services (Nginx & Systemd)..."
cat > /etc/systemd/system/qna-api.service <<UNIT
[Unit]
Description=QnA Diary FastAPI Application
After=network.target

[Service]
User=ec2-user
WorkingDirectory=/opt/app/backend
ExecStart=/opt/app/backend/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
Restart=always
RestartSec=5
EnvironmentFile=-/etc/qna-diary/env
Environment=APP_PASSWORD=$APP_PASSWORD
Environment=SESSION_SECRET=$SESSION_SECRET
Environment=DB_URL=$DB_URL
Environment=BEDROCK_MODEL_ID=$BEDROCK_MODEL_ID
Environment=AWS_REGION=$AWS_REGION

[Install]
WantedBy=multi-user.target
UNIT

cat > /etc/nginx/conf.d/qna-diary.conf <<'NGINX'
server {
    listen 80;
    server_name _;

    root /opt/app/frontend/dist;
    index index.html;

    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    location / {
        try_files $uri $uri/ /index.html;
    }
}
NGINX

rm -f /etc/nginx/conf.d/default.conf

echo "==> [7/7] Running Database Migrations & Starting Services..."
cd /opt/app/backend
DB_URL="$DB_URL" APP_PASSWORD="$APP_PASSWORD" SESSION_SECRET="$SESSION_SECRET" \
  BEDROCK_MODEL_ID="$BEDROCK_MODEL_ID" AWS_REGION="$AWS_REGION" \
  .venv/bin/alembic upgrade head

# seed_holidays 도 app.config.Settings 를 import 하므로 알렘빅과 동일한 env 5종 필요
DB_URL="$DB_URL" APP_PASSWORD="$APP_PASSWORD" SESSION_SECRET="$SESSION_SECRET" \
  BEDROCK_MODEL_ID="$BEDROCK_MODEL_ID" AWS_REGION="$AWS_REGION" \
  .venv/bin/python -m scripts.seed_holidays

systemctl daemon-reload
systemctl enable nginx qna-api
systemctl restart nginx qna-api

echo "==> Redeploy done"
systemctl --no-pager status qna-api | head -n 20

echo "==> Tailing qna-api logs (Ctrl+C to exit)"
journalctl -u qna-api -f