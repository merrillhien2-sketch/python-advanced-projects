# Enterprise Python Platform

企业级 Python 异步 Web 平台，基于 FastAPI + SQLAlchemy + Celery 构建，提供用户认证、短链服务、AI 异步任务、定时爬虫等功能。

## 项目简介

本项目是一个企业级 Python 异步 Web 应用平台，采用现代化的技术栈和最佳实践，旨在为中小型企业提供一套完整、可靠、可扩展的后端服务框架。项目涵盖用户认证与授权、短链服务、AI 异步任务处理、定时爬虫、系统健康监控等核心功能模块。

## 功能特性

- **用户认证与授权**：基于 JWT 的用户注册、登录、权限管理
- **短链服务**：URL 短链生成与解析，支持过期时间和 Redis 缓存
- **AI 异步任务**：OCR 文字识别、情感分析（单条/批量），基于 Celery 异步执行
- **定时任务调度**：过期短链清理、定时网页爬取、系统健康检查
- **数据缓存**：基于 Redis 的高速缓存层
- **异步架构**：全链路异步 I/O，高并发处理能力
- **统一异常处理**：规范化的错误响应格式
- **API 文档**：自动生成 Swagger UI 和 ReDoc 交互式文档
- **完善的测试**：单元测试覆盖核心功能，使用 SQLite 内存数据库和 Mock Redis
- **安全加密**：基于 Fernet 的数据加解密工具
- **部署友好**：支持 Docker 一键部署和手动部署

## 技术栈

| 分类 | 技术 | 版本 |
|------|------|------|
| Web 框架 | FastAPI | 0.100+ |
| ASGI 服务器 | Uvicorn / Gunicorn | - |
| ORM | SQLAlchemy | 2.0+ (async) |
| 数据库 | MySQL | 8.0 |
| 数据库驱动 | aiomysql | - |
| 缓存 | Redis | 7.0 |
| 异步任务队列 | Celery | 5.3+ |
| HTTP 客户端 | httpx | - |
| 数据验证 | Pydantic | 2.0+ |
| 认证 | python-jose (JWT) | - |
| 密码哈希 | passlib (bcrypt) | - |
| 加密 | cryptography (Fernet) | - |
| 测试框架 | pytest + pytest-asyncio | - |
| Python | Python | 3.11+ |

## 项目结构

```
python-enterprise-platform/
├── app/                          # 应用主目录
│   ├── __init__.py               # 版本号定义
│   ├── main.py                   # FastAPI 应用入口
│   ├── celery_app.py             # Celery 应用（根级，示例任务）
│   ├── api/                      # API 路由
│   │   ├── __init__.py
│   │   └── v1/                   # v1 版本路由
│   │       ├── __init__.py
│   │       ├── router.py         # 路由聚合
│   │       ├── auth.py           # 认证路由 (/api/v1/auth)
│   │       ├── shortlink.py      # 短链路由 (/api/v1/shortlink)
│   │       ├── ai.py             # AI 服务路由 (/api/v1/ai)
│   │       ├── crawler.py        # 爬虫路由 (/api/v1/crawler)
│   │       ├── chat.py           # 聊天路由 (/api/v1/chat)
│   │       └── tasks.py          # 任务路由 (/api/v1/tasks)
│   ├── core/                     # 核心配置
│   │   ├── __init__.py
│   │   ├── config.py             # 应用配置 (settings)
│   │   ├── database.py           # 数据库配置 (Base, engine, get_db)
│   │   ├── redis_client.py       # Redis 客户端 (redis_client, get_redis)
│   │   ├── exceptions.py         # 自定义异常 (AppException, NotFoundException 等)
│   │   ├── security.py           # 安全工具 (JWT, 密码哈希, get_current_user)
│   │   ├── logging_config.py     # 日志配置
│   │   └── rate_limit.py         # 接口限流
│   ├── models/                   # 数据模型
│   │   ├── __init__.py           # 导出 User, ShortLink, TaskRecord, CrawlData
│   │   ├── base.py               # 基础模型 (BaseModel, TimestampMixin)
│   │   ├── user.py               # 用户模型
│   │   ├── shortlink.py          # 短链模型
│   │   ├── task.py               # 任务记录模型
│   │   └── crawl_data.py         # 爬取数据模型
│   ├── schemas/                  # Pydantic 数据模式
│   │   ├── __init__.py
│   │   ├── common.py             # 通用响应模式 (ResponseBase, PaginatedResponse)
│   │   ├── user.py               # 用户相关模式 (UserCreate, UserLogin, TokenResponse)
│   │   ├── shortlink.py          # 短链相关模式
│   │   ├── ai.py                 # AI 相关模式
│   │   └── task.py               # 任务相关模式
│   ├── services/                 # 业务逻辑层
│   │   ├── __init__.py
│   │   ├── shortlink_service.py  # 短链服务
│   │   ├── ai_service.py         # AI 服务 (情感分析, OCR, 目标检测, 推荐)
│   │   ├── crawler_service.py    # 爬虫服务
│   │   └── recommendation_service.py  # 推荐服务
│   ├── tasks/                    # Celery 异步任务
│   │   ├── __init__.py
│   │   ├── celery_app.py         # Celery 应用配置 (含 Beat 定时调度)
│   │   ├── scheduled_tasks.py    # 定时任务 (清理短链/爬取/健康检查)
│   │   └── ai_tasks.py           # AI 异步任务 (OCR/情感分析/批量分析)
│   └── utils/                    # 工具包
│       ├── __init__.py
│       ├── helpers.py            # 通用工具函数 (UUID/短码/时间/脱敏/分块等)
│       └── crypto.py             # 加密工具 (AES 加解密/Fernet)
├── tests/                        # 单元测试
│   ├── __init__.py
│   ├── conftest.py               # pytest 配置和 fixtures (MockRedis, SQLite 内存库)
│   ├── test_health.py            # 健康检查测试
│   ├── test_shortlink.py         # 短链服务测试
│   ├── test_ai.py                # AI 服务测试
│   └── test_auth.py              # 认证测试
├── docs/                         # 文档
│   ├── local_setup.md            # 本地启动教程
│   └── deployment.md             # 服务器部署教程
├── scripts/                      # 脚本
│   └── init_db.py                # 数据库初始化脚本 (建表+创建管理员)
├── docker/                       # Docker 部署
│   ├── Dockerfile                # Docker 镜像配置
│   ├── docker-compose.yml        # Docker Compose 编排
│   └── nginx.conf                # Nginx 配置
├── .env-example                  # 环境变量示例
├── .gitignore
├── Makefile                      # Make 命令
├── pytest.ini                    # pytest 配置 (asyncio_mode=auto)
├── requirements.txt              # Python 依赖
└── README.md                     # 项目说明文档
```

## 快速开始

### 1. 环境准备

确保已安装 Python 3.11+、MySQL 8.0、Redis 7.0。

### 2. 克隆项目

```bash
git clone https://github.com/your-org/python-enterprise-platform.git
cd python-enterprise-platform
```

### 3. 创建虚拟环境并安装依赖

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 4. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 文件，填入你的本地配置
```

### 5. 初始化数据库

```bash
# 创建 MySQL 数据库
mysql -u root -p -e "CREATE DATABASE enterprise_platform CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"

# 创建表和默认管理员
python scripts/init_db.py
```

### 6. 启动服务

```bash
# 启动 FastAPI 应用
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 启动 Celery Worker（新终端）
celery -A app.tasks.celery_app worker --loglevel=info

# 启动 Celery Beat（新终端）
celery -A app.tasks.celery_app beat --loglevel=info
```

### 7. 访问 API 文档

打开浏览器访问 http://localhost:8000/docs

> 详细的本地启动教程请参阅 [docs/local_setup.md](docs/local_setup.md)

## 环境变量说明

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `APP_NAME` | 应用名称 | Enterprise Platform |
| `DEBUG` | 调试模式 | True |
| `LOG_LEVEL` | 日志级别 | INFO |
| `DATABASE_URL` | 数据库连接地址 | mysql+aiomysql://root:password@localhost:3306/enterprise_platform |
| `REDIS_URL` | Redis 连接地址 | redis://localhost:6379/0 |
| `CELERY_BROKER_URL` | Celery 消息代理地址 | redis://localhost:6379/1 |
| `CELERY_RESULT_BACKEND` | Celery 结果后端地址 | redis://localhost:6379/2 |
| `CELERY_TIMEZONE` | Celery 时区 | Asia/Shanghai |
| `SECRET_KEY` | 应用密钥（用于 JWT 和加密） | 必须修改 |
| `ALGORITHM` | JWT 签名算法 | HS256 |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Token 过期时间（分钟） | 1440 |
| `ADMIN_USERNAME` | 默认管理员用户名 | admin |
| `ADMIN_PASSWORD` | 默认管理员密码 | admin123456 |
| `ADMIN_EMAIL` | 默认管理员邮箱 | admin@example.com |
| `CRAWL_URLS` | 定时爬取的 URL 列表 | [] |

## API 接口概览

### 健康检查

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/health` | 系统健康检查 |

### 认证

| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| POST | `/api/v1/auth/register` | 用户注册 | 否 |
| POST | `/api/v1/auth/login` | 用户登录 | 否 |
| GET | `/api/v1/auth/me` | 获取当前用户信息 | 是 |

### 短链服务

| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| POST | `/api/v1/shortlink/` | 创建短链 | 是 |
| GET | `/api/v1/shortlink/{code}` | 短链跳转（302 重定向） | 否 |
| GET | `/api/v1/shortlink/` | 分页查询短链列表 | 否 |

### AI 服务

| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| POST | `/api/v1/ai/sentiment` | 情感分析 | 是 |
| POST | `/api/v1/ai/ocr` | OCR 文字识别 | 是 |
| POST | `/api/v1/ai/batch-sentiment` | 批量情感分析 | 是 |

### 异步任务

| 任务名称 | 说明 | 执行频率 |
|----------|------|----------|
| `clean_expired_shortlinks` | 清理过期短链 | 每小时 |
| `scheduled_crawl` | 定时网页爬取 | 每 30 分钟 |
| `health_check` | 系统健康检查 | 每 5 分钟 |
| `async_ocr_task` | 异步 OCR 识别 | 按需调用 |
| `async_sentiment_task` | 异步情感分析 | 按需调用 |
| `batch_sentiment_task` | 批量情感分析 | 按需调用 |

## 部署说明

### Docker 部署（推荐）

```bash
# 构建并启动所有服务
docker compose up -d

# 初始化数据库
docker compose exec app python scripts/init_db.py

# 查看服务状态
docker compose ps
```

### 手动部署

```bash
# 使用 Gunicorn 启动
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000

# 使用 systemd 管理进程
sudo systemctl start enterprise-app
sudo systemctl start enterprise-celery-worker
sudo systemctl start enterprise-celery-beat
```

> 详细的部署教程请参阅 [docs/deployment.md](docs/deployment.md)

## 测试说明

### 运行测试

```bash
# 运行所有测试
pytest

# 运行特定测试模块
pytest tests/test_health.py -v
pytest tests/test_auth.py -v
pytest tests/test_shortlink.py -v
pytest tests/test_ai.py -v

# 生成覆盖率报告
pytest --cov=app --cov-report=term-missing --cov-report=html
```

### 测试特点

- 使用 **pytest + pytest-asyncio** 框架，`asyncio_mode = auto`
- 使用 **SQLite 内存数据库**，无需连接真实 MySQL
- 使用 **Mock Redis**，无需连接真实 Redis
- 所有测试可独立运行，不依赖外部服务
- 测试覆盖健康检查、认证、短链、AI 服务等核心模块

### 测试文件说明

| 文件 | 说明 | 测试用例数 |
|------|------|-----------|
| `tests/conftest.py` | 测试配置和 fixtures | - |
| `tests/test_health.py` | 健康检查接口测试 | 2 |
| `tests/test_shortlink.py` | 短链服务测试 | 3 |
| `tests/test_ai.py` | AI 服务测试 | 4 |
| `tests/test_auth.py` | 认证服务测试 | 4 |

## 开发指南

### 代码结构规范

项目采用分层架构：

```
API 路由 (app/api/) → 业务服务 (app/services/) → 数据模型 (app/models/)
                                                      ↓
                                              数据库 (app/core/database.py)
```

- **API 路由层**：负责接收 HTTP 请求、参数验证、调用服务层、返回响应
- **业务服务层**：封装核心业务逻辑，可被 API 和 Celery 任务复用
- **数据模型层**：定义数据库表结构和 ORM 映射
- **异步任务层**：Celery 任务，处理耗时操作（AI 推理、爬虫等）
- **工具层**：通用工具函数和加密工具

### 添加新功能

1. 在 `app/models/` 中定义数据模型
2. 在 `app/schemas/` 中定义请求/响应模式
3. 在 `app/services/` 中实现业务逻辑
4. 在 `app/api/` 中添加 API 路由
5. 在 `tests/` 中编写单元测试
6. 运行测试验证：`pytest -v`

### 添加 Celery 异步任务

1. 在 `app/tasks/` 中创建任务文件
2. 使用 `@celery_app.task(name="app.tasks.xxx.task_name")` 装饰器定义任务
3. 如需定时执行，在 `app/tasks/celery_app.py` 的 `beat_schedule` 中添加调度配置
4. 编写完善的异常处理和日志记录

### 代码风格

- 遵循 PEP 8 规范
- 使用类型注解（Type Hints）
- 所有公共函数和类添加文档字符串
- 注释使用中文

### 提交规范

使用 Conventional Commits 规范：

```
<type>(<scope>): <subject>

<body>

<footer>
```

类型说明：
- `feat`: 新功能
- `fix`: 修复 Bug
- `docs`: 文档更新
- `style`: 代码格式调整
- `refactor`: 代码重构
- `test`: 测试相关
- `chore`: 构建/工具相关

## 开源协议

本项目基于 [MIT License](LICENSE) 开源协议。

```
MIT License

Copyright (c) 2024 Enterprise Platform

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```
