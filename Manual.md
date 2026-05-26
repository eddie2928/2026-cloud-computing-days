# QnA Diary 인프라 수동 배포 매뉴얼

Terraform을 쓸 수 없는 상황에서 AWS 콘솔(또는 AWS CLI 스크립트)로 동일한 리소스를 올리기 위한 가이드입니다. 기존 `infra/*.tf` 파일과 1:1 매핑되도록 정리했습니다.

---

## 0. 사전 정보 (변수)

`infra/variables.tf` + `terraform.tfvars` 기준 실제 값.

| 항목 | 값 |
|---|---|
| Region | `us-east-1` |
| VPC CIDR | `10.20.0.0/16` |
| Public Subnet A | `10.20.1.0/24` (`us-east-1a`) |
| Public Subnet B | `10.20.2.0/24` (`us-east-1b`) |
| EC2 Type | `t3.small` |
| RDS Class | `db.t3.micro` / PostgreSQL 16 / 20GB |
| DB Name / User | `qnadiary` / `appuser` |
| DB Password | `a-gXcJS-jCyr4XjAEPwyNZMcP8M` |
| App Password | `inha-nxt` |
| Session Secret | `B1nAH_8pNObWNGk0QmRhOK-vFFRKrOYkFg8iP6N1bg5-LglEUl_1-A` |
| Bedrock Model | `us.anthropic.claude-sonnet-4-6` |
| Git Repo / Branch | `https://github.com/55002ghals/2026-cloud-computing-days.git` / `master` |
| 공통 태그 | `Project=qna-diary` |

리소스 명명 규칙: 모두 `qna-diary-*` 접두.

---

## 1. 리소스 생성 순서 (의존 그래프)

```
Key Pair  ─┐
VPC ─ IGW ─ Subnet(2) ─ RouteTable ─ Route ─ Assoc
                │
                ├─ Security Group: ec2-sg
                └─ Security Group: rds-sg  (ec2-sg 참조)
                          │
DB Subnet Group ──────────┤
                          ├─ RDS PostgreSQL
IAM Role ─ Policy ─ Attach ─ Instance Profile
                          │
                          └─ EC2 (user_data 포함)
```

---

## 2. 콘솔 수동 절차

### 2.1 EC2 Key Pair
- EC2 → **Network & Security → Key Pairs → Create key pair**
- Name: `qna-diary-key`, Type: `RSA`, Format: `.pem`
- 다운로드된 `qna-diary-key.pem`을 안전한 위치에 저장 (SSH 접속용)
- Windows: `icacls qna-diary-key.pem /inheritance:r /grant:r "%USERNAME%:R"`

### 2.2 VPC
- VPC 콘솔 → **Your VPCs → Create VPC**
- **VPC only** 선택
- Name: `qna-diary-vpc`, IPv4 CIDR: `10.20.0.0/16`, Tenancy: default
- 생성 후 **Actions → Edit VPC settings**: `Enable DNS resolution`, `Enable DNS hostnames` 모두 체크

### 2.3 Internet Gateway
- VPC → **Internet Gateways → Create**
- Name: `qna-diary-igw` → 생성 → **Actions → Attach to VPC → qna-diary-vpc**

### 2.4 Public Subnets (2개)
- VPC → **Subnets → Create subnet** (qna-diary-vpc 선택)
- Subnet 1
  - Name: `qna-diary-public-us-east-1a`, AZ: `us-east-1a`, CIDR: `10.20.1.0/24`
- Subnet 2
  - Name: `qna-diary-public-us-east-1b`, AZ: `us-east-1b`, CIDR: `10.20.2.0/24`
- 각 서브넷 선택 → **Actions → Edit subnet settings → Enable auto-assign public IPv4 address**

### 2.5 Route Table
- VPC → **Route Tables → Create**
- Name: `qna-diary-public-rt`, VPC: `qna-diary-vpc`
- 생성 후 **Routes → Edit routes → Add route**
  - Destination: `0.0.0.0/0`, Target: Internet Gateway → `qna-diary-igw`
- **Subnet associations → Edit** → 두 public 서브넷 모두 선택

### 2.6 Security Groups
**ec2-sg** (먼저 생성)
- EC2 → **Security Groups → Create**
- Name: `qna-diary-ec2-sg`, VPC: `qna-diary-vpc`
- Inbound:
  - TCP 80, Source `0.0.0.0/0` (HTTP)
  - TCP 22, Source `0.0.0.0/0` (SSH)
- Outbound: All traffic `0.0.0.0/0` (기본값)

**rds-sg**
- Name: `qna-diary-rds-sg`, VPC: `qna-diary-vpc`
- Inbound:
  - TCP 5432, Source = **qna-diary-ec2-sg** (SG 참조)
- Outbound: All traffic `0.0.0.0/0`

### 2.7 IAM (Bedrock 접근용)
- IAM → **Policies → Create policy → JSON**

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "BedrockInvokeModel",
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel",
        "bedrock:InvokeModelWithResponseStream"
      ],
      "Resource": [
        "arn:aws:bedrock:us-east-1:*:inference-profile/us.anthropic.claude-sonnet-4-6",
        "arn:aws:bedrock:*::foundation-model/anthropic.claude-sonnet-4-6"
      ]
    },
    {
      "Sid": "BedrockListModels",
      "Effect": "Allow",
      "Action": ["bedrock:ListFoundationModels"],
      "Resource": "*"
    }
  ]
}
```
- Policy Name: `qna-diary-bedrock-access`

- IAM → **Roles → Create role**
- Trusted entity: AWS service → **EC2**
- Attach policy: `qna-diary-bedrock-access`
- Role Name: `qna-diary-ec2-bedrock-role`
- (Instance Profile은 콘솔에서 EC2 Role 만들 때 자동 생성됨. 이름이 Role 이름과 동일하게 됨 — 단, Terraform이 만든 이름은 `qna-diary-ec2-profile`. CLI로 별도 생성하려면 아래 자동화 스크립트 참고)

### 2.8 RDS
- RDS → **Subnet groups → Create**
- Name: `qna-diary-db-subnet-group`, VPC: `qna-diary-vpc`
- AZ: `us-east-1a`, `us-east-1b`, Subnets: 두 public 서브넷 모두 추가

- RDS → **Databases → Create database**
- **Standard create**
- Engine: PostgreSQL, Version: 16.x
- Templates: **Free tier** 또는 **Dev/Test**
- DB instance identifier: `qna-diary-postgres`
- Master username: `appuser`
- Master password: `a-gXcJS-jCyr4XjAEPwyNZMcP8M`
- Instance class: `db.t3.micro`
- Storage: 20 GiB gp2/gp3, Encryption: **disabled**
- Connectivity:
  - VPC: `qna-diary-vpc`
  - Subnet group: `qna-diary-db-subnet-group`
  - Public access: **No**
  - VPC SG: `qna-diary-rds-sg`
  - AZ: `us-east-1a`
- Additional configuration:
  - Initial database name: `qnadiary`
  - Backup retention: 0 (또는 기본값)
  - Deletion protection: **off**
  - Performance Insights / Enhanced monitoring: off

- 생성 후 **Endpoint** 메모 (예: `qna-diary-postgres.xxxx.us-east-1.rds.amazonaws.com`)

### 2.9 EC2 인스턴스
- EC2 → **Launch instances**
- Name: `qna-diary-app`
- AMI: **Amazon Linux 2023** (`al2023-ami-2023*-x86_64`, Standard / 8GB. ⚠ minimal 버전 금지)
- Instance type: `t3.small`
- Key pair: `qna-diary-key`
- Network:
  - VPC: `qna-diary-vpc`, Subnet: `qna-diary-public-us-east-1a`
  - Auto-assign public IP: Enable
  - Security group: 기존 선택 → `qna-diary-ec2-sg`
- Storage: 20 GiB **gp3** (root)
- Advanced details:
  - IAM instance profile: `qna-diary-ec2-bedrock-role` (또는 `qna-diary-ec2-profile`)
  - **User data**에 아래 스크립트 붙여넣기 (변수 치환 필수)

#### User Data (RDS Endpoint 알아낸 후 치환)
`<RDS_ENDPOINT>`만 실제 값으로 바꿔서 그대로 사용.

```bash
#!/bin/bash
set -euo pipefail
exec > >(tee /var/log/user-data.log | logger -t user-data -s 2>/dev/console) 2>&1

GIT_REPO_URL="https://github.com/55002ghals/2026-cloud-computing-days.git"
GIT_BRANCH="master"
DB_URL="postgresql+asyncpg://appuser:a-gXcJS-jCyr4XjAEPwyNZMcP8M@<RDS_ENDPOINT>/qnadiary"
APP_PASSWORD="inha-nxt"
SESSION_SECRET="B1nAH_8pNObWNGk0QmRhOK-vFFRKrOYkFg8iP6N1bg5-LglEUl_1-A"
BEDROCK_MODEL_ID="us.anthropic.claude-sonnet-4-6"
AWS_REGION="us-east-1"

dnf install -y python3.11 python3.11-pip nodejs20 git nginx
dnf clean all

mkdir -p /opt/app
git clone --branch "$GIT_BRANCH" "$GIT_REPO_URL" /opt/app
chown -R ec2-user:ec2-user /opt/app

cd /opt/app/backend
python3.11 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt

cd /opt/app/frontend
npm ci
npm run build
rm -rf node_modules

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

cd /opt/app/backend
DB_URL="$DB_URL" APP_PASSWORD="$APP_PASSWORD" SESSION_SECRET="$SESSION_SECRET" \
  BEDROCK_MODEL_ID="$BEDROCK_MODEL_ID" AWS_REGION="$AWS_REGION" \
  .venv/bin/alembic upgrade head

systemctl daemon-reload
systemctl enable nginx qna-api
systemctl start nginx qna-api
```

- Launch.
- 인스턴스 상태가 Running이 된 후 `Public IPv4 address` 확인.
- 부트스트랩 진행 로그: SSH 접속 후 `sudo tail -f /var/log/user-data.log`

### 2.10 동작 확인
- 5~10분 대기 (npm build 시간) → 브라우저에서 `http://<EC2_PUBLIC_IP>` 접속
- SSH: `ssh -i qna-diary-key.pem ec2-user@<EC2_PUBLIC_IP>`
- 서비스: `sudo systemctl status qna-api nginx`

---

## 3. 자동화 스크립트 (AWS CLI)

콘솔 클릭을 줄이고 싶다면 아래 스크립트 사용. PowerShell 또는 Git Bash/WSL에서 실행 가능 (AWS CLI v2 + jq 필요).

> ⚠ 이 스크립트는 idempotent하지 않습니다. 한 번 실행 후 실패 시 부분 리소스 정리 필요.

`infra-deploy.sh` 로 저장하고 실행:

```bash
#!/usr/bin/env bash
set -euo pipefail

# === Config ===
export AWS_DEFAULT_REGION=us-east-1
REGION=us-east-1
PROJECT_TAG='Key=Project,Value=qna-diary'

VPC_CIDR=10.20.0.0/16
SUBNET_A_CIDR=10.20.1.0/24
SUBNET_B_CIDR=10.20.2.0/24
AZ_A=us-east-1a
AZ_B=us-east-1b

DB_USERNAME=appuser
DB_PASSWORD='a-gXcJS-jCyr4XjAEPwyNZMcP8M'
DB_NAME=qnadiary
APP_PASSWORD='inha-nxt'
SESSION_SECRET='B1nAH_8pNObWNGk0QmRhOK-vFFRKrOYkFg8iP6N1bg5-LglEUl_1-A'
BEDROCK_MODEL_ID=us.anthropic.claude-sonnet-4-6
BASE_MODEL_ID=anthropic.claude-sonnet-4-6
GIT_REPO_URL=https://github.com/55002ghals/2026-cloud-computing-days.git
GIT_BRANCH=master

tag() { echo "ResourceType=$1,Tags=[{Key=Name,Value=$2},{Key=Project,Value=qna-diary}]"; }

echo "== Key Pair =="
aws ec2 create-key-pair --key-name qna-diary-key \
  --tag-specifications "$(tag key-pair qna-diary-key)" \
  --query KeyMaterial --output text > qna-diary-key.pem
chmod 600 qna-diary-key.pem

echo "== VPC =="
VPC_ID=$(aws ec2 create-vpc --cidr-block $VPC_CIDR \
  --tag-specifications "$(tag vpc qna-diary-vpc)" \
  --query Vpc.VpcId --output text)
aws ec2 modify-vpc-attribute --vpc-id $VPC_ID --enable-dns-support
aws ec2 modify-vpc-attribute --vpc-id $VPC_ID --enable-dns-hostnames

echo "== IGW =="
IGW_ID=$(aws ec2 create-internet-gateway \
  --tag-specifications "$(tag internet-gateway qna-diary-igw)" \
  --query InternetGateway.InternetGatewayId --output text)
aws ec2 attach-internet-gateway --vpc-id $VPC_ID --internet-gateway-id $IGW_ID

echo "== Subnets =="
SUBNET_A=$(aws ec2 create-subnet --vpc-id $VPC_ID --cidr-block $SUBNET_A_CIDR \
  --availability-zone $AZ_A \
  --tag-specifications "$(tag subnet qna-diary-public-$AZ_A)" \
  --query Subnet.SubnetId --output text)
SUBNET_B=$(aws ec2 create-subnet --vpc-id $VPC_ID --cidr-block $SUBNET_B_CIDR \
  --availability-zone $AZ_B \
  --tag-specifications "$(tag subnet qna-diary-public-$AZ_B)" \
  --query Subnet.SubnetId --output text)
aws ec2 modify-subnet-attribute --subnet-id $SUBNET_A --map-public-ip-on-launch
aws ec2 modify-subnet-attribute --subnet-id $SUBNET_B --map-public-ip-on-launch

echo "== Route Table =="
RT_ID=$(aws ec2 create-route-table --vpc-id $VPC_ID \
  --tag-specifications "$(tag route-table qna-diary-public-rt)" \
  --query RouteTable.RouteTableId --output text)
aws ec2 create-route --route-table-id $RT_ID \
  --destination-cidr-block 0.0.0.0/0 --gateway-id $IGW_ID
aws ec2 associate-route-table --route-table-id $RT_ID --subnet-id $SUBNET_A
aws ec2 associate-route-table --route-table-id $RT_ID --subnet-id $SUBNET_B

echo "== Security Groups =="
EC2_SG=$(aws ec2 create-security-group --group-name qna-diary-ec2-sg \
  --description "Security group for EC2 web server" --vpc-id $VPC_ID \
  --tag-specifications "$(tag security-group qna-diary-ec2-sg)" \
  --query GroupId --output text)
aws ec2 authorize-security-group-ingress --group-id $EC2_SG \
  --ip-permissions "IpProtocol=tcp,FromPort=80,ToPort=80,IpRanges=[{CidrIp=0.0.0.0/0,Description=HTTP}]" \
                   "IpProtocol=tcp,FromPort=22,ToPort=22,IpRanges=[{CidrIp=0.0.0.0/0,Description=SSH}]"

RDS_SG=$(aws ec2 create-security-group --group-name qna-diary-rds-sg \
  --description "Security group for RDS PostgreSQL" --vpc-id $VPC_ID \
  --tag-specifications "$(tag security-group qna-diary-rds-sg)" \
  --query GroupId --output text)
aws ec2 authorize-security-group-ingress --group-id $RDS_SG \
  --ip-permissions "IpProtocol=tcp,FromPort=5432,ToPort=5432,UserIdGroupPairs=[{GroupId=$EC2_SG,Description=PostgreSQL from EC2}]"

echo "== IAM =="
cat > /tmp/trust.json <<'EOF'
{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":"ec2.amazonaws.com"},"Action":"sts:AssumeRole"}]}
EOF
aws iam create-role --role-name qna-diary-ec2-bedrock-role \
  --assume-role-policy-document file:///tmp/trust.json \
  --tags Key=Project,Value=qna-diary >/dev/null

cat > /tmp/bedrock.json <<EOF
{
  "Version":"2012-10-17",
  "Statement":[
    {"Sid":"BedrockInvokeModel","Effect":"Allow",
     "Action":["bedrock:InvokeModel","bedrock:InvokeModelWithResponseStream"],
     "Resource":[
       "arn:aws:bedrock:${REGION}:*:inference-profile/${BEDROCK_MODEL_ID}",
       "arn:aws:bedrock:*::foundation-model/${BASE_MODEL_ID}"
     ]},
    {"Sid":"BedrockListModels","Effect":"Allow",
     "Action":["bedrock:ListFoundationModels"],"Resource":"*"}
  ]
}
EOF
POLICY_ARN=$(aws iam create-policy --policy-name qna-diary-bedrock-access \
  --policy-document file:///tmp/bedrock.json \
  --tags Key=Project,Value=qna-diary \
  --query Policy.Arn --output text)
aws iam attach-role-policy --role-name qna-diary-ec2-bedrock-role --policy-arn $POLICY_ARN
aws iam create-instance-profile --instance-profile-name qna-diary-ec2-profile \
  --tags Key=Project,Value=qna-diary >/dev/null
aws iam add-role-to-instance-profile \
  --instance-profile-name qna-diary-ec2-profile \
  --role-name qna-diary-ec2-bedrock-role

echo "== RDS Subnet Group =="
aws rds create-db-subnet-group --db-subnet-group-name qna-diary-db-subnet-group \
  --db-subnet-group-description "qna-diary" \
  --subnet-ids $SUBNET_A $SUBNET_B \
  --tags Key=Project,Value=qna-diary >/dev/null

echo "== RDS Instance (creating, ~10min) =="
aws rds create-db-instance \
  --db-instance-identifier qna-diary-postgres \
  --engine postgres --engine-version 16 \
  --db-instance-class db.t3.micro \
  --allocated-storage 20 \
  --db-name $DB_NAME \
  --master-username $DB_USERNAME \
  --master-user-password "$DB_PASSWORD" \
  --db-subnet-group-name qna-diary-db-subnet-group \
  --vpc-security-group-ids $RDS_SG \
  --no-publicly-accessible --no-multi-az \
  --no-storage-encrypted \
  --no-deletion-protection \
  --backup-retention-period 0 \
  --tags Key=Project,Value=qna-diary >/dev/null

aws rds wait db-instance-available --db-instance-identifier qna-diary-postgres
RDS_ENDPOINT=$(aws rds describe-db-instances --db-instance-identifier qna-diary-postgres \
  --query "DBInstances[0].Endpoint.Address" --output text)
echo "RDS endpoint: $RDS_ENDPOINT"

echo "== AMI lookup =="
AMI_ID=$(aws ec2 describe-images --owners amazon \
  --filters "Name=name,Values=al2023-ami-2023*-x86_64" "Name=virtualization-type,Values=hvm" \
  --query "Images | sort_by(@, &CreationDate)[-1].ImageId" --output text)
echo "AMI: $AMI_ID"

echo "== User data =="
DB_URL="postgresql+asyncpg://${DB_USERNAME}:${DB_PASSWORD}@${RDS_ENDPOINT}/${DB_NAME}"
cat > /tmp/user-data.sh <<USERDATA
#!/bin/bash
set -euo pipefail
exec > >(tee /var/log/user-data.log | logger -t user-data -s 2>/dev/console) 2>&1

dnf install -y python3.11 python3.11-pip nodejs20 git nginx
dnf clean all

mkdir -p /opt/app
git clone --branch "${GIT_BRANCH}" "${GIT_REPO_URL}" /opt/app
chown -R ec2-user:ec2-user /opt/app

cd /opt/app/backend
python3.11 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt

cd /opt/app/frontend
npm ci
npm run build
rm -rf node_modules

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
Environment=APP_PASSWORD=${APP_PASSWORD}
Environment=SESSION_SECRET=${SESSION_SECRET}
Environment=DB_URL=${DB_URL}
Environment=BEDROCK_MODEL_ID=${BEDROCK_MODEL_ID}
Environment=AWS_REGION=${REGION}

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
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
    }
    location / { try_files \$uri \$uri/ /index.html; }
}
NGINX
rm -f /etc/nginx/conf.d/default.conf

cd /opt/app/backend
DB_URL="${DB_URL}" APP_PASSWORD="${APP_PASSWORD}" SESSION_SECRET="${SESSION_SECRET}" \
  BEDROCK_MODEL_ID="${BEDROCK_MODEL_ID}" AWS_REGION="${REGION}" \
  .venv/bin/alembic upgrade head

systemctl daemon-reload
systemctl enable nginx qna-api
systemctl start nginx qna-api
USERDATA

echo "== EC2 =="
# Instance profile propagation 대기
sleep 10
INSTANCE_ID=$(aws ec2 run-instances \
  --image-id $AMI_ID \
  --instance-type t3.small \
  --key-name qna-diary-key \
  --subnet-id $SUBNET_A \
  --security-group-ids $EC2_SG \
  --iam-instance-profile Name=qna-diary-ec2-profile \
  --block-device-mappings 'DeviceName=/dev/xvda,Ebs={VolumeSize=20,VolumeType=gp3}' \
  --user-data file:///tmp/user-data.sh \
  --tag-specifications "$(tag instance qna-diary-app)" \
  --query "Instances[0].InstanceId" --output text)

aws ec2 wait instance-running --instance-ids $INSTANCE_ID
PUBLIC_IP=$(aws ec2 describe-instances --instance-ids $INSTANCE_ID \
  --query "Reservations[0].Instances[0].PublicIpAddress" --output text)

cat <<SUMMARY

============================================
배포 완료 (앱 부트스트랩에 5~10분 추가 소요)
--------------------------------------------
VPC:            $VPC_ID
EC2 instance:   $INSTANCE_ID
Public IP:      $PUBLIC_IP
App URL:        http://$PUBLIC_IP
RDS endpoint:   $RDS_ENDPOINT
SSH:            ssh -i qna-diary-key.pem ec2-user@$PUBLIC_IP
부트스트랩 로그: sudo tail -f /var/log/user-data.log
============================================
SUMMARY
```

---

## 4. 삭제 (역순)

```bash
# EC2
aws ec2 terminate-instances --instance-ids <INSTANCE_ID>
aws ec2 wait instance-terminated --instance-ids <INSTANCE_ID>

# RDS
aws rds delete-db-instance --db-instance-identifier qna-diary-postgres \
  --skip-final-snapshot --delete-automated-backups
aws rds wait db-instance-deleted --db-instance-identifier qna-diary-postgres
aws rds delete-db-subnet-group --db-subnet-group-name qna-diary-db-subnet-group

# IAM
aws iam remove-role-from-instance-profile --instance-profile-name qna-diary-ec2-profile --role-name qna-diary-ec2-bedrock-role
aws iam delete-instance-profile --instance-profile-name qna-diary-ec2-profile
aws iam detach-role-policy --role-name qna-diary-ec2-bedrock-role --policy-arn <POLICY_ARN>
aws iam delete-policy --policy-arn <POLICY_ARN>
aws iam delete-role --role-name qna-diary-ec2-bedrock-role

# Networking
aws ec2 delete-security-group --group-id <RDS_SG>
aws ec2 delete-security-group --group-id <EC2_SG>
aws ec2 disassociate-route-table --association-id <ASSOC_ID>   # 각 서브넷별
aws ec2 delete-route-table --route-table-id <RT_ID>
aws ec2 delete-subnet --subnet-id <SUBNET_A>
aws ec2 delete-subnet --subnet-id <SUBNET_B>
aws ec2 detach-internet-gateway --internet-gateway-id <IGW_ID> --vpc-id <VPC_ID>
aws ec2 delete-internet-gateway --internet-gateway-id <IGW_ID>
aws ec2 delete-vpc --vpc-id <VPC_ID>
aws ec2 delete-key-pair --key-name qna-diary-key
```

---

## 5. 트러블슈팅

| 증상 | 확인 |
|---|---|
| 80 포트 응답 없음 | `sudo tail -200 /var/log/user-data.log` — npm/alembic 실패 여부 |
| `qna-api` 죽음 | `sudo journalctl -u qna-api -n 200` |
| Bedrock 401/AccessDenied | IAM Role의 inference-profile/foundation-model ARN 확인. 또한 us-east-1에서 해당 모델 access 활성화 필요 (Bedrock 콘솔 → Model access) |
| RDS 연결 실패 | EC2 SG ↔ RDS SG 5432 규칙, RDS가 EC2와 같은 VPC, subnet group에 EC2 서브넷 포함 |
| AMI minimal 선택됨 | 8GB Standard AL2023 인지 확인 (2GB minimal은 디스크 부족) |
| user-data 재실행 필요 | `sudo cloud-init clean && sudo cloud-init init` 또는 인스턴스 재생성 |
