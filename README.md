# Python 高级实战项目集合

> 企业级可部署上线的 Python 项目集合，涵盖 AI/机器学习、大数据、异步高并发后端、爬虫、数据分析、舆情监控、自动化办公、接口测试等方向。

## 项目简介

本项目是一个**企业级 Python 实战项目集合**，基于 FastAPI + SQLAlchemy + Celery + Redis + Docker 构建，采用完整分层架构。包含 **12 个功能模块**，覆盖 AI 算法、数据分析、爬虫、短链服务、WebSocket 实时通信、异步任务、舆情监控、代理IP池、办公自动化、接口测试、电商价格监控等主流技术方向，适合求职展示、学习参考和商业化接单。

## 功能模块总览

| 模块 | 路由前缀 | 核心能力 | 求职方向 |
|------|----------|----------|----------|
| 用户认证 | `/api/v1/auth` | JWT 注册/登录/鉴权, bcrypt 密码哈希 | Python 后端 |
| AI 服务 | `/api/v1/ai` | OCR 文字识别, 情感分析, 目标检测, 协同过滤推荐 | AI/NLP |
| 爬虫服务 | `/api/v1/crawler` | 异步抓取, 批量爬取, UA 轮换, 并发控制 | 爬虫工程师 |
| 短链服务 | `/api/v1/shortlink` | base62 编码, Redis 缓存, 点击统计, 过期管理 | Python 后端 |
| WebSocket 聊天 | `/api/v1/chat` | 多用户聊天室, 连接池管理, 广播消息 | Python 后端 |
| 异步任务 | `/api/v1/tasks` | Celery 任务队列, 状态追踪, 定时调度 | Python 后端 |
| **数据分析** | `/api/v1/data-analysis` | 电商订单分析, 仪表盘统计, 用户画像, 营收趋势 | 数据分析师 |
| **舆情监控** | `/api/v1/sentiment` | 评论监控任务, 自动情感分析, 舆情汇总统计 | AI/NLP |
| **代理IP池** | `/api/v1/proxy-pool` | 代理管理, 健康检查, 批量导入, 智能轮换 | 爬虫工程师 |
| **办公工具** | `/api/v1/office` | Excel/CSV 互转, PDF 提取, 批量重命名, 报告生成 | 自动化 |
| **接口测试** | `/api/v1/api-test` | 测试套件/用例管理, HTTP 执行, 结果比对 | 测试工程师 |
| **价格监控** | `/api/v1/price-monitor` | 商品管理, 价格历史, 降价告警, 统计分析 | 爬虫/数据 |

## 技术栈

| 分类 | 技术 | 说明 |
|------|------|------|
| Web 框架 | FastAPI 0.111 | 异步 ASGI 框架, 自动 API 文档 |
| ORM | SQLAlchemy 2.0 | 异步引擎, DeclarativeBase |
| 数据库 | MySQL 8.0 / SQLite | 生产用 MySQL, 测试用 SQLite 内存 |
| 缓存 | Redis 7 | 短链缓存, 限流, 会话 |
| 任务队列 | Celery 5.4 | 异步任务 + Beat 定时调度 |
| 认证 | python-jose (JWT) + bcrypt | 令牌签发与密码哈希 |
| HTTP 客户端 | httpx | 异步请求, 爬虫, 接口测试 |
| HTML 解析 | BeautifulSoup4 + lxml | 爬虫页面解析 |
| OCR | pytesseract + Pillow | 图片文字识别 |
| Excel | openpyxl | Excel 读写 |
| PDF | pdfplumber | PDF 文本提取 |
| 测试 | pytest + pytest-asyncio | 异步测试, 41 个用例 |
| 部署 | Docker + Nginx | docker-compose 6 服务编排 |
| Python | 3.11+ | 现代类型注解 |

## 项目结构

```
python-enterprise-platform/
├── app/
│   ├── main.py                       # FastAPI 应用入口
│   ├── core/                         # 核心基础设施
│   │   ├── config.py                 # 配置管理 (pydantic-settings)
│   │   ├── database.py               # 异步数据库 (SQLAlchemy 2.0)
│   │   ├── redis_client.py           # Redis 连接
│   │   ├── security.py               # JWT + bcrypt 安全工具
│   │   ├── exceptions.py             # 全局异常处理
│   │   ├── rate_limit.py             # Redis 滑动窗口限流
│   │   └── logging_config.py         # 日志系统 (RotatingFileHandler)
│   ├── models/                       # 数据模型 (14 个表)
│   │   ├── user.py / shortlink.py / task.py / crawl_data.py
│   │   ├── data_analysis.py          # 订单记录 + 用户画像
│   │   ├── sentiment_monitor.py      # 监控任务 + 舆情记录
│   │   ├── proxy_pool.py             # 代理IP
│   │   ├── api_test.py               # 测试套件 + 用例 + 运行记录
│   │   └── price_monitor.py          # 商品 + 价格历史 + 告警
│   ├── schemas/                      # Pydantic 数据校验
│   ├── services/                     # 业务服务层 (10 个服务)
│   │   ├── ai_service.py             # OCR/情感/检测/推荐
│   │   ├── crawler_service.py        # 异步爬虫
│   │   ├── shortlink_service.py      # 短链服务
│   │   ├── data_analysis_service.py  # 数据分析
│   │   ├── sentiment_monitor_service.py  # 舆情监控
│   │   ├── proxy_pool_service.py     # 代理IP池
│   │   ├── office_service.py         # 办公自动化
│   │   ├── api_test_service.py       # 接口测试
│   │   └── price_monitor_service.py  # 价格监控
│   ├── api/v1/                       # API 路由 (12 个模块)
│   │   ├── router.py                 # 路由聚合
│   │   ├── auth.py / ai.py / crawler.py / shortlink.py / chat.py / tasks.py
│   │   ├── data_analysis.py          # 数据分析路由
│   │   ├── sentiment_monitor.py      # 舆情监控路由
│   │   ├── proxy_pool.py             # 代理IP池路由
│   │   ├── office.py                 # 办公工具路由
│   │   ├── api_test.py               # 接口测试路由
│   │   └── price_monitor.py          # 价格监控路由
│   ├── tasks/                        # Celery 异步任务
│   │   ├── celery_app.py             # Celery 配置 + Beat 调度
│   │   ├── scheduled_tasks.py        # 定时任务 (清理/爬取/健康检查)
│   │   └── ai_tasks.py               # AI 异步任务
│   └── utils/                        # 工具包
│       ├── helpers.py                # 通用工具 (UUID/短码/脱敏/分块)
│       └── crypto.py                 # Fernet 加解密
├── tests/                            # 单元测试 (41 个用例)
├── docker/                           # Docker 部署
├── docs/                             # 部署文档
├── scripts/                          # 初始化脚本
├── .env-example                      # 环境变量模板
├── requirements.txt                  # 依赖清单
├── Makefile                          # 常用命令
├── pytest.ini                        # pytest 配置
├── SELF_CHECK_REPORT.md              # 三层自查报告
└── README.md
```

## 快速开始

### 1. 环境准备

Python 3.11+, MySQL 8.0, Redis 7.0

### 2. 克隆项目

```bash
git clone https://github.com/merrillhien2-sketch/python-advanced-projects.git
cd python-advanced-projects
```

### 3. 安装依赖

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 4. 配置环境变量

```bash
cp .env-example .env
# 编辑 .env, 填入你的配置
```

### 5. 初始化数据库

```bash
python scripts/init_db.py
```

### 6. 启动服务

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
celery -A app.tasks.celery_app worker --loglevel=info
celery -A app.tasks.celery_app beat --loglevel=info
```

### 7. 访问 API 文档

http://localhost:8000/docs

## API 接口概览

### 基础模块

| 模块 | 路径 | 主要接口 |
|------|------|----------|
| 认证 | `/api/v1/auth` | 注册, 登录, 获取用户信息 |
| AI | `/api/v1/ai` | OCR, 情感分析, 目标检测, 推荐 |
| 爬虫 | `/api/v1/crawler` | 单页/批量抓取, 数据查询 |
| 短链 | `/api/v1/shortlink` | 创建, 跳转, 列表 |
| 聊天 | `/api/v1/chat` | WebSocket 聊天, 在线统计 |
| 任务 | `/api/v1/tasks` | 创建, 查询, 列表 |

### 新增模块

| 模块 | 路径 | 主要接口 |
|------|------|----------|
| 数据分析 | `/api/v1/data-analysis` | 订单创建/批量导入, 仪表盘, 营收趋势, 用户画像 |
| 舆情监控 | `/api/v1/sentiment` | 监控任务, 舆情记录, 情感分析, 汇总统计 |
| 代理IP池 | `/api/v1/proxy-pool` | 添加/批量导入, 随机获取, 健康检查, 统计 |
| 办公工具 | `/api/v1/office` | Excel/CSV互转, PDF提取, 批量重命名, 报告 |
| 接口测试 | `/api/v1/api-test` | 套件/用例管理, 执行, 历史 |
| 价格监控 | `/api/v1/price-monitor` | 商品管理, 价格记录, 告警, 统计 |

## 测试说明

```bash
# 运行全部测试
pytest

# 运行特定模块
pytest tests/test_data_analysis.py -v
pytest tests/test_proxy_pool.py -v
```

| 测试文件 | 用例数 | 覆盖模块 |
|----------|--------|----------|
| test_health.py | 2 | 健康检查 |
| test_auth.py | 4 | 用户认证 |
| test_shortlink.py | 3 | 短链服务 |
| test_ai.py | 4 | AI 服务 |
| test_data_analysis.py | 5 | 数据分析 |
| test_sentiment_monitor.py | 6 | 舆情监控 |
| test_proxy_pool.py | 6 | 代理IP池 |
| test_office.py | 4 | 办公工具 |
| test_api_test.py | 3 | 接口测试 |
| test_price_monitor.py | 4 | 价格监控 |
| **合计** | **41** | **全部通过** |

## 部署

### Docker 部署

```bash
docker compose -f docker/docker-compose.yml --env-file .env up -d
docker compose exec app python scripts/init_db.py
```

### 手动部署

```bash
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000
```

详见 [docs/deployment.md](docs/deployment.md)

## 开源协议

MIT License
