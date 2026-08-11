# ============================================================
# 企业级 Python 平台 Makefile
# 常用开发与部署命令
# 使用方式：make <target>
# ============================================================

# 使用 bash 以支持 ANSI-C 引号（db-init 目标使用）
SHELL := /bin/bash

# Python 解释器
PYTHON := python3
# Docker Compose 文件与 env 文件
COMPOSE := docker compose --env-file .env -f docker/docker-compose.yml

.PHONY: install run test lint docker-up docker-down celery-worker celery-beat db-init

## 安装项目依赖
install:
	$(PYTHON) -m pip install -r requirements.txt

## 本地运行开发服务器（热重载）
run:
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

## 运行测试用例
test:
	pytest -v

## 代码静态检查（pyflakes + mypy，未安装则跳过）
lint:
	@command -v pyflakes >/dev/null 2>&1 && pyflakes app/ || echo "pyflakes 未安装，已跳过"
	@command -v mypy >/dev/null 2>&1 && mypy app/ || echo "mypy 未安装，已跳过"

## 构建并启动全部 Docker 服务
docker-up:
	$(COMPOSE) up -d --build

## 停止并移除全部 Docker 服务
docker-down:
	$(COMPOSE) down

## 启动 Celery Worker（本地）
celery-worker:
	celery -A app.tasks.celery_app:celery_app worker --loglevel=info

## 启动 Celery Beat 定时任务调度（本地）
celery-beat:
	celery -A app.tasks.celery_app:celery_app beat --loglevel=info

## 初始化数据库（根据模型创建表）
db-init:
	$(PYTHON) -c $'import asyncio\nfrom app.core.database import Base, engine\n\nasync def init():\n    async with engine.begin() as conn:\n        await conn.run_sync(Base.metadata.create_all)\n\nasyncio.run(init())'
	@echo "数据库表初始化完成"
