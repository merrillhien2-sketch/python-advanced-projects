# 本地启动教程

本教程将指导你在本地环境中搭建和运行企业级 Python 平台项目。

## 环境要求

在开始之前，请确保你的开发环境满足以下要求：

| 组件 | 最低版本 | 推荐版本 | 说明 |
|------|---------|---------|------|
| Python | 3.11 | 3.11+ | 项目使用 Python 3.11+ 特性 |
| MySQL | 8.0 | 8.0 | 主数据库 |
| Redis | 6.0 | 7.0 | 缓存和消息队列 |
| Git | 2.20 | 最新版 | 版本控制 |

### 验证环境

```bash
# 检查 Python 版本
python3 --version
# 预期输出: Python 3.11.x 或更高

# 检查 MySQL 版本
mysql --version
# 预期输出: mysql Ver 8.0.x

# 检查 Redis 版本
redis-server --version
# 预期输出: Redis server v=7.0.x

# 检查 Git 版本
git --version
```

## 1. 克隆项目

```bash
git clone https://github.com/your-org/python-enterprise-platform.git
cd python-enterprise-platform
```

## 2. 创建虚拟环境

使用 `venv` 创建虚拟环境（推荐）：

```bash
# 创建虚拟环境
python3 -m venv venv

# 激活虚拟环境
# Linux / macOS:
source venv/bin/activate
# Windows (PowerShell):
# venv\Scripts\Activate.ps1
# Windows (CMD):
# venv\Scripts\activate.bat

# 验证虚拟环境已激活
which python
# 预期输出: /path/to/project/venv/bin/python
```

或者使用 `conda` 创建虚拟环境：

```bash
conda create -n enterprise-platform python=3.11
conda activate enterprise-platform
```

## 3. 安装依赖

```bash
# 升级 pip
pip install --upgrade pip

# 安装项目依赖
pip install -r requirements.txt

# 如果有开发依赖（可选）
pip install -r requirements-dev.txt
```

### 主要依赖说明

| 依赖 | 用途 |
|------|------|
| fastapi | Web 框架 |
| uvicorn | ASGI 服务器 |
| sqlalchemy | ORM 框架 |
| aiomysql | MySQL 异步驱动 |
| redis | Redis 客户端 |
| celery | 异步任务队列 |
| httpx | HTTP 客户端 |
| python-jose | JWT 令牌 |
| passlib | 密码哈希 |
| cryptography | 加密工具 |
| pydantic | 数据验证 |

## 4. 配置 .env 文件

在项目根目录创建 `.env` 文件：

```bash
cp .env.example .env
```

编辑 `.env` 文件，填入你的本地配置：

```env
# ==================== 应用配置 ====================
APP_NAME=Enterprise Platform
APP_VERSION=1.0.0
DEBUG=True
LOG_LEVEL=INFO

# ==================== 数据库配置 ====================
DATABASE_URL=mysql+aiomysql://root:your_password@localhost:3306/enterprise_platform

# ==================== Redis 配置 ====================
REDIS_URL=redis://localhost:6379/0

# ==================== Celery 配置 ====================
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2
CELERY_TIMEZONE=Asia/Shanghai

# ==================== 安全配置 ====================
SECRET_KEY=your-super-secret-key-change-this-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# ==================== 管理员配置 ====================
ADMIN_USERNAME=admin
ADMIN_PASSWORD=admin123456
ADMIN_EMAIL=admin@example.com

# ==================== 爬虫配置 ====================
CRAWL_URLS=[]
```

> **重要提示**：请务必修改 `SECRET_KEY` 和管理员密码，不要在生产环境中使用默认值。

## 5. 初始化数据库

### 5.1 创建 MySQL 数据库

登录 MySQL 并创建数据库：

```bash
mysql -u root -p
```

```sql
CREATE DATABASE enterprise_platform CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'enterprise'@'localhost' IDENTIFIED BY 'your_password';
GRANT ALL PRIVILEGES ON enterprise_platform.* TO 'enterprise'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

### 5.2 运行数据库初始化脚本

```bash
# 创建所有数据库表并创建默认管理员用户
python scripts/init_db.py
```

预期输出：

```
========================================
  企业级 Python 平台 - 数据库初始化
========================================
正在创建数据库表...
数据库表创建成功！
正在创建默认管理员用户...
默认管理员用户创建成功！
  用户名: admin
  邮箱: admin@example.com
========================================
  数据库初始化完成！
========================================
```

## 6. 启动 Redis

确保 Redis 服务已启动：

```bash
# 启动 Redis 服务（前台运行）
redis-server

# 或以后台服务方式启动（Linux）
sudo systemctl start redis

# 验证 Redis 是否正常运行
redis-cli ping
# 预期输出: PONG
```

## 7. 启动应用服务

### 7.1 启动 FastAPI 应用

```bash
# 开发模式（支持热重载）
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 生产模式
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

应用启动后，可以访问：

- API 服务: http://localhost:8000
- API 文档 (Swagger UI): http://localhost:8000/docs
- API 文档 (ReDoc): http://localhost:8000/redoc
- 健康检查: http://localhost:8000/health

### 7.2 启动 Celery Worker

打开新的终端窗口，激活虚拟环境后执行：

```bash
celery -A app.tasks.celery_app worker --loglevel=info
```

### 7.3 启动 Celery Beat（定时任务调度）

再打开一个新的终端窗口：

```bash
celery -A app.tasks.celery_app beat --loglevel=info
```

> **提示**：Worker 和 Beat 可以合并启动（仅限开发环境）：
> ```bash
> celery -A app.tasks.celery_app worker --beat --loglevel=info
> ```

## 8. 运行测试

### 8.1 运行所有测试

```bash
pytest
```

### 8.2 运行特定测试文件

```bash
# 运行健康检查测试
pytest tests/test_health.py -v

# 运行短链服务测试
pytest tests/test_shortlink.py -v

# 运行 AI 服务测试
pytest tests/test_ai.py -v

# 运行认证测试
pytest tests/test_auth.py -v
```

### 8.3 生成测试覆盖率报告

```bash
# 安装覆盖率工具（如果尚未安装）
pip install pytest-cov

# 运行测试并生成覆盖率报告
pytest --cov=app --cov-report=term-missing --cov-report=html

# 查看 HTML 覆盖率报告
# 在浏览器中打开 htmlcov/index.html
```

### 8.4 测试说明

- 测试使用 SQLite 内存数据库，**不需要**连接真实的 MySQL
- 测试使用 Mock Redis，**不需要**连接真实的 Redis
- 测试使用 pytest + pytest-asyncio，支持异步测试
- 所有测试均可独立运行，不依赖外部服务

## 9. 访问 API 文档

应用启动后，在浏览器中打开：

### Swagger UI
```
http://localhost:8000/docs
```

Swagger UI 提供交互式 API 文档，你可以直接在浏览器中测试 API。

### ReDoc
```
http://localhost:8000/redoc
```

ReDoc 提供更美观的 API 文档展示。

### 主要 API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /health | 健康检查 |
| POST | /api/auth/register | 用户注册 |
| POST | /api/auth/login | 用户登录 |
| GET | /api/auth/me | 获取当前用户信息 |
| POST | /api/shortlinks | 创建短链 |
| GET | /api/shortlinks/{short_code} | 解析短链 |

## 10. 常见问题

### Q: 启动时报 `ModuleNotFoundError`

确保已激活虚拟环境并安装了所有依赖：

```bash
source venv/bin/activate
pip install -r requirements.txt
```

### Q: 数据库连接失败

1. 确认 MySQL 服务已启动：`sudo systemctl status mysql`
2. 确认 `.env` 中的 `DATABASE_URL` 配置正确
3. 确认数据库已创建：`mysql -u root -p -e "SHOW DATABASES;"`

### Q: Redis 连接失败

1. 确认 Redis 服务已启动：`redis-cli ping`
2. 确认 `.env` 中的 `REDIS_URL` 配置正确

### Q: Celery Worker 无法连接 Broker

1. 确认 Redis 服务已启动
2. 确认 `.env` 中的 `CELERY_BROKER_URL` 配置正确
3. 尝试指定 Redis 数据库编号：`redis://localhost:6379/1`

### Q: 测试失败

1. 确认已安装测试依赖：`pip install pytest pytest-asyncio httpx aiosqlite`
2. 确认 `pytest.ini` 配置文件存在且 `asyncio_mode = auto`
3. 尝试清除缓存后重新运行：`pytest --cache-clear`

## 11. 开发工具推荐

| 工具 | 用途 |
|------|------|
| VS Code | 代码编辑器（推荐安装 Python 扩展） |
| DBeaver | 数据库管理工具 |
| Postman / Insomnia | API 测试工具 |
| RedisInsight | Redis 可视化管理工具 |
| Flower | Celery 任务监控工具 |
