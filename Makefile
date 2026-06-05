SHELL := /bin/bash
PROJECT_DIR := $(shell pwd)
BACKEND_DIR  := $(PROJECT_DIR)/backend
FRONTEND_DIR := $(PROJECT_DIR)/frontend
PYTHON       := $(shell command -v python3.11 2>/dev/null || echo python3)
VENV         := $(BACKEND_DIR)/.venv
PY           := $(VENV)/bin/python
PIP          := $(VENV)/bin/pip
ALEMBIC      := $(VENV)/bin/alembic
PYTEST       := $(VENV)/bin/pytest
UVICORN      := $(VENV)/bin/uvicorn

.DEFAULT_GOAL := help

# ── 도움말 ──────────────────────────────────────────────────────────────────
.PHONY: help
help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
	  awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-18s\033[0m %s\n",$$1,$$2}'

# ── 최초 세팅 ────────────────────────────────────────────────────────────────
.PHONY: setup
setup: ## 첫 실행 전 전체 환경 세팅 (venv + npm + .env)
	@echo ">>> [1/3] 백엔드 가상환경 생성 및 패키지 설치"
	$(PYTHON) -m venv $(VENV)
	$(PIP) install -q --upgrade pip
	$(PIP) install -q -r $(BACKEND_DIR)/requirements.txt \
	                    -r $(BACKEND_DIR)/requirements-dev.txt
	@echo ">>> [2/3] 프론트엔드 패키지 설치"
	cd $(FRONTEND_DIR) && npm install --silent
	@echo ">>> [3/3] .env 파일 확인"
	@if [ ! -f $(BACKEND_DIR)/.env ]; then \
	  printf 'APP_PASSWORD=inha-nxt\nSESSION_SECRET=local-dev-secret-change-me\nDB_URL=postgresql+asyncpg://appuser:localdevpass@localhost:5432/qnadiary\nANTHROPIC_API_KEY=\nCLAUDE_MODEL=claude-sonnet-4-6\n' > $(BACKEND_DIR)/.env; \
	  echo "  .env 생성됨 → $(BACKEND_DIR)/.env (ANTHROPIC_API_KEY에 실제 키 입력 필요)"; \
	else \
	  echo "  .env 이미 존재 — 건너뜀"; \
	fi
	@echo ">>> 완료! 'make db && make migrate && make backend' 으로 서버 실행"

# ── DB ───────────────────────────────────────────────────────────────────────
.PHONY: db
db: ## PostgreSQL 도커 컨테이너 시작
	docker compose -f $(PROJECT_DIR)/docker-compose.dev.yml up -d
	@echo "DB 준비 대기 중..."
	@until docker compose -f $(PROJECT_DIR)/docker-compose.dev.yml exec -T postgres \
	  pg_isready -U appuser -d qnadiary -q 2>/dev/null; do sleep 1; done
	@echo "DB 준비 완료"

.PHONY: db-stop
db-stop: ## PostgreSQL 도커 컨테이너 중지
	docker compose -f $(PROJECT_DIR)/docker-compose.dev.yml down

.PHONY: db-reset
db-reset: ## DB 완전 초기화 (볼륨 삭제 후 재시작 + 마이그레이션)
	docker compose -f $(PROJECT_DIR)/docker-compose.dev.yml down -v
	$(MAKE) db
	$(MAKE) migrate

# ── 마이그레이션 ──────────────────────────────────────────────────────────────
.PHONY: migrate
migrate: ## Alembic 마이그레이션 최신 적용
	cd $(BACKEND_DIR) && $(ALEMBIC) upgrade head

.PHONY: migrate-status
migrate-status: ## 현재 마이그레이션 상태 확인
	cd $(BACKEND_DIR) && $(ALEMBIC) current

# ── 서버 실행 ────────────────────────────────────────────────────────────────
.PHONY: backend
backend: ## 백엔드 개발 서버 실행 (http://localhost:8000)
	cd $(BACKEND_DIR) && $(UVICORN) app.main:app --reload --port 8000

.PHONY: frontend
frontend: ## 프론트엔드 개발 서버 실행 (http://localhost:5173)
	cd $(FRONTEND_DIR) && npm run dev

# ── 테스트 ───────────────────────────────────────────────────────────────────
.PHONY: test-backend
test-backend: ## 백엔드 테스트 (Docker 필요)
	cd $(BACKEND_DIR) && $(PYTEST) -v --tb=short

.PHONY: test-frontend
test-frontend: ## 프론트엔드 테스트
	cd $(FRONTEND_DIR) && npm test -- --run

.PHONY: test
test: test-backend test-frontend ## 전체 테스트
