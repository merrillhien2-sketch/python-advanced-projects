# 服务器部署教程

本教程详细说明如何将企业级 Python 平台部署到生产服务器，包括 Docker 部署、手动部署、Nginx 反向代理、SSL 配置、日志管理、进程管理、数据库备份、监控和安全加固。

---

## 目录

1. [Docker 部署（推荐）](#1-docker-部署推荐)
2. [手动部署](#2-手动部署)
3. [Nginx 反向代理配置](#3-nginx-反向代理配置)
4. [SSL/HTTPS 配置](#4-sslhttps-配置)
5. [日志管理](#5-日志管理)
6. [进程管理（systemd / supervisor）](#6-进程管理systemd--supervisor)
7. [数据库备份](#7-数据库备份)
8. [监控建议](#8-监控建议)
9. [安全加固建议](#9-安全加固建议)

---

## 1. Docker 部署（推荐）

Docker 部署是最简单、最一致的部署方式，推荐在生产环境中使用。

### 1.1 前置条件

- Docker 24.0+
- Docker Compose 2.20+

```bash
# 验证 Docker 安装
docker --version
docker compose version
```

### 1.2 项目文件结构

确保项目根目录下有以下文件：

```
python-enterprise-platform/
├── docker-compose.yml
├── Dockerfile
├── .env
├── nginx/
│   └── nginx.conf
└── ...
```

### 1.3 Dockerfile 示例

```dockerfile
FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件并安装
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目代码
COPY . .

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 1.4 docker-compose.yml 示例

```yaml
version: "3.8"

services:
  # FastAPI 应用
  app:
    build: .
    container_name: enterprise-app
    restart: always
    ports:
      - "8000:8000"
    env_file:
      - .env
    depends_on:
      - mysql
      - redis
    volumes:
      - ./logs:/app/logs
    networks:
      - enterprise-network

  # Celery Worker
  celery-worker:
    build: .
    container_name: enterprise-celery-worker
    restart: always
    command: celery -A app.tasks.celery_app worker --loglevel=info
    env_file:
      - .env
    depends_on:
      - redis
    volumes:
      - ./logs:/app/logs
    networks:
      - enterprise-network

  # Celery Beat
  celery-beat:
    build: .
    container_name: enterprise-celery-beat
    restart: always
    command: celery -A app.tasks.celery_app beat --loglevel=info
    env_file:
      - .env
    depends_on:
      - redis
    networks:
      - enterprise-network

  # MySQL 数据库
  mysql:
    image: mysql:8.0
    container_name: enterprise-mysql
    restart: always
    environment:
      MYSQL_ROOT_PASSWORD: ${MYSQL_ROOT_PASSWORD:-rootpassword}
      MYSQL_DATABASE: enterprise_platform
      MYSQL_USER: ${MYSQL_USER:-enterprise}
      MYSQL_PASSWORD: ${MYSQL_PASSWORD:-enterprisepassword}
    ports:
      - "3306:3306"
    volumes:
      - mysql-data:/var/lib/mysql
      - ./mysql/init:/docker-entrypoint-initdb.d
    command: --character-set-server=utf8mb4 --collation-server=utf8mb4_unicode_ci
    networks:
      - enterprise-network

  # Redis 缓存
  redis:
    image: redis:7-alpine
    container_name: enterprise-redis
    restart: always
    ports:
      - "6379:6379"
    volumes:
      - redis-data:/data
    command: redis-server --appendonly yes --maxmemory 512mb --maxmemory-policy allkeys-lru
    networks:
      - enterprise-network

  # Nginx 反向代理
  nginx:
    image: nginx:alpine
    container_name: enterprise-nginx
    restart: always
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./nginx/ssl:/etc/nginx/ssl:ro
    depends_on:
      - app
    networks:
      - enterprise-network

volumes:
  mysql-data:
  redis-data:

networks:
  enterprise-network:
    driver: bridge
```

### 1.5 启动 Docker 部署

```bash
# 构建并启动所有服务
docker compose up -d

# 查看服务状态
docker compose ps

# 查看应用日志
docker compose logs -f app

# 初始化数据库（首次部署）
docker compose exec app python scripts/init_db.py

# 停止所有服务
docker compose down

# 停止并删除数据卷（谨慎操作！会删除所有数据）
# docker compose down -v
```

### 1.6 更新部署

```bash
# 拉取最新代码
git pull origin main

# 重新构建并启动
docker compose up -d --build

# 执行数据库迁移（如果有）
docker compose exec app python scripts/init_db.py
```

---

## 2. 手动部署

如果不使用 Docker，可以手动部署到服务器。

### 2.1 服务器环境准备

```bash
# 安装 Python 3.11
sudo apt update
sudo apt install -y python3.11 python3.11-venv python3.11-dev

# 安装 MySQL 8.0
sudo apt install -y mysql-server

# 安装 Redis
sudo apt install -y redis-server

# 安装 Nginx
sudo apt install -y nginx

# 启动服务
sudo systemctl start mysql
sudo systemctl start redis-server
sudo systemctl start nginx
```

### 2.2 部署应用

```bash
# 创建应用目录
sudo mkdir -p /opt/enterprise-platform
sudo chown $USER:$USER /opt/enterprise-platform

# 克隆代码
cd /opt/enterprise-platform
git clone https://github.com/your-org/python-enterprise-platform.git .

# 创建虚拟环境
python3.11 -m venv venv
source venv/bin/activate

# 安装依赖
pip install --upgrade pip
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env 文件，填入生产环境配置
nano .env

# 初始化数据库
python scripts/init_db.py
```

### 2.3 使用 Gunicorn + Uvicorn 启动

```bash
# 安装 Gunicorn
pip install gunicorn

# 启动应用（4 个 worker 进程）
gunicorn app.main:app \
    -w 4 \
    -k uvicorn.workers.UvicornWorker \
    -b 0.0.0.0:8000 \
    --timeout 120 \
    --access-logfile /opt/enterprise-platform/logs/access.log \
    --error-logfile /opt/enterprise-platform/logs/error.log
```

---

## 3. Nginx 反向代理配置

### 3.1 Nginx 配置文件

创建 `/etc/nginx/sites-available/enterprise-platform`：

```nginx
# HTTP -> HTTPS 重定向
server {
    listen 80;
    server_name your-domain.com www.your-domain.com;
    
    # Let's Encrypt 证书验证
    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }
    
    # 重定向到 HTTPS
    location / {
        return 301 https://$server_name$request_uri;
    }
}

# HTTPS 主服务
server {
    listen 443 ssl http2;
    server_name your-domain.com www.your-domain.com;

    # SSL 证书配置
    ssl_certificate /etc/nginx/ssl/fullchain.pem;
    ssl_certificate_key /etc/nginx/ssl/privkey.pem;

    # SSL 安全配置
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;

    # 安全头
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";

    # 日志
    access_log /var/log/nginx/enterprise-access.log;
    error_log /var/log/nginx/enterprise-error.log;

    # 文件上传大小限制
    client_max_body_size 50M;

    # API 反向代理
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket 支持
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        
        # 超时设置
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # 静态文件（如果有）
    location /static/ {
        alias /opt/enterprise-platform/static/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # 健康检查（不记日志）
    location /health {
        proxy_pass http://127.0.0.1:8000;
        access_log off;
    }
}
```

### 3.2 启用配置

```bash
# 创建符号链接启用站点
sudo ln -s /etc/nginx/sites-available/enterprise-platform /etc/nginx/sites-enabled/

# 测试 Nginx 配置
sudo nginx -t

# 重新加载 Nginx
sudo systemctl reload nginx
```

---

## 4. SSL/HTTPS 配置

### 4.1 使用 Let's Encrypt 获取免费 SSL 证书

```bash
# 安装 Certbot
sudo apt install -y certbot python3-certbot-nginx

# 获取 SSL 证书（自动修改 Nginx 配置）
sudo certbot --nginx -d your-domain.com -d www.your-domain.com

# 或仅获取证书（手动配置 Nginx）
sudo certbot certonly --nginx -d your-domain.com -d www.your-domain.com
```

### 4.2 自动续期

Let's Encrypt 证书有效期为 90 天，Certbot 会自动设置续期任务：

```bash
# 测试自动续期
sudo certbot renew --dry-run

# 查看续期任务
sudo systemctl list-timers | grep certbot
```

### 4.3 手动生成自签名证书（仅用于测试）

```bash
# 创建 SSL 证书目录
sudo mkdir -p /etc/nginx/ssl

# 生成自签名证书
sudo openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout /etc/nginx/ssl/privkey.pem \
    -out /etc/nginx/ssl/fullchain.pem \
    -subj "/C=CN/ST=Beijing/L=Beijing/O=Enterprise/CN=your-domain.com"

# 设置权限
sudo chmod 600 /etc/nginx/ssl/privkey.pem
```

> **警告**：自签名证书仅用于测试环境，生产环境请使用 Let's Encrypt 或商业 SSL 证书。

---

## 5. 日志管理

### 5.1 应用日志配置

在 `.env` 中配置日志级别：

```env
LOG_LEVEL=INFO
```

### 5.2 日志文件位置

```
/opt/enterprise-platform/logs/
├── app.log          # 应用日志
├── access.log       # HTTP 访问日志
├── error.log        # 错误日志
├── celery-worker.log # Celery Worker 日志
└── celery-beat.log   # Celery Beat 日志
```

### 5.3 使用 logrotate 自动轮转日志

创建 `/etc/logrotate.d/enterprise-platform`：

```
/opt/enterprise-platform/logs/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    create 0644 www-data www-data
    postrotate
        # 通知应用重新打开日志文件
        if [ -f /opt/enterprise-platform/logs/app.pid ]; then
            kill -USR1 $(cat /opt/enterprise-platform/logs/app.pid)
        fi
    endpostrotate
}
```

```bash
# 测试 logrotate 配置
sudo logrotate -d /etc/logrotate.d/enterprise-platform

# 手动执行日志轮转
sudo logrotate -f /etc/logrotate.d/enterprise-platform
```

### 5.4 查看日志

```bash
# 实时查看应用日志
tail -f /opt/enterprise-platform/logs/app.log

# 查看错误日志
grep "ERROR" /opt/enterprise-platform/logs/error.log

# 查看 Nginx 访问日志
tail -f /var/log/nginx/enterprise-access.log

# 查看 Nginx 错误日志
tail -f /var/log/nginx/enterprise-error.log

# 查看 Celery 日志
tail -f /opt/enterprise-platform/logs/celery-worker.log
```

---

## 6. 进程管理（systemd / supervisor）

### 6.1 使用 systemd（推荐）

#### 6.1.1 FastAPI 应用服务

创建 `/etc/systemd/system/enterprise-app.service`：

```ini
[Unit]
Description=Enterprise Platform FastAPI Application
After=network.target mysql.service redis-server.service

[Service]
Type=exec
User=www-data
Group=www-data
WorkingDirectory=/opt/enterprise-platform
EnvironmentFile=/opt/enterprise-platform/.env
ExecStart=/opt/enterprise-platform/venv/bin/gunicorn app.main:app \
    -w 4 \
    -k uvicorn.workers.UvicornWorker \
    -b 127.0.0.1:8000 \
    --timeout 120
Restart=always
RestartSec=5
StandardOutput=append:/opt/enterprise-platform/logs/app.log
StandardError=append:/opt/enterprise-platform/logs/error.log

[Install]
WantedBy=multi-user.target
```

#### 6.1.2 Celery Worker 服务

创建 `/etc/systemd/system/enterprise-celery-worker.service`：

```ini
[Unit]
Description=Enterprise Platform Celery Worker
After=network.target redis-server.service

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=/opt/enterprise-platform
EnvironmentFile=/opt/enterprise-platform/.env
ExecStart=/opt/enterprise-platform/venv/bin/celery -A app.tasks.celery_app worker --loglevel=info
Restart=always
RestartSec=10
StandardOutput=append:/opt/enterprise-platform/logs/celery-worker.log
StandardError=append:/opt/enterprise-platform/logs/celery-worker.log

[Install]
WantedBy=multi-user.target
```

#### 6.1.3 Celery Beat 服务

创建 `/etc/systemd/system/enterprise-celery-beat.service`：

```ini
[Unit]
Description=Enterprise Platform Celery Beat Scheduler
After=network.target redis-server.service

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=/opt/enterprise-platform
EnvironmentFile=/opt/enterprise-platform/.env
ExecStart=/opt/enterprise-platform/venv/bin/celery -A app.tasks.celery_app beat --loglevel=info
Restart=always
RestartSec=10
StandardOutput=append:/opt/enterprise-platform/logs/celery-beat.log
StandardError=append:/opt/enterprise-platform/logs/celery-beat.log

[Install]
WantedBy=multi-user.target
```

#### 6.1.4 管理服务

```bash
# 重新加载 systemd 配置
sudo systemctl daemon-reload

# 启动所有服务
sudo systemctl start enterprise-app
sudo systemctl start enterprise-celery-worker
sudo systemctl start enterprise-celery-beat

# 设置开机自启
sudo systemctl enable enterprise-app
sudo systemctl enable enterprise-celery-worker
sudo systemctl enable enterprise-celery-beat

# 查看服务状态
sudo systemctl status enterprise-app
sudo systemctl status enterprise-celery-worker
sudo systemctl status enterprise-celery-beat

# 重启服务
sudo systemctl restart enterprise-app
sudo systemctl restart enterprise-celery-worker
sudo systemctl restart enterprise-celery-beat

# 停止服务
sudo systemctl stop enterprise-app
sudo systemctl stop enterprise-celery-worker
sudo systemctl stop enterprise-celery-beat
```

### 6.2 使用 Supervisor（替代方案）

安装 Supervisor：

```bash
sudo apt install -y supervisor
```

创建 `/etc/supervisor/conf.d/enterprise-platform.conf`：

```ini
[program:enterprise-app]
command=/opt/enterprise-platform/venv/bin/gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker -b 127.0.0.1:8000 --timeout 120
directory=/opt/enterprise-platform
user=www-data
autostart=true
autorestart=true
stdout_logfile=/opt/enterprise-platform/logs/app.log
stderr_logfile=/opt/enterprise-platform/logs/error.log
environment=ENVIRONMENT="production"

[program:enterprise-celery-worker]
command=/opt/enterprise-platform/venv/bin/celery -A app.tasks.celery_app worker --loglevel=info
directory=/opt/enterprise-platform
user=www-data
autostart=true
autorestart=true
stdout_logfile=/opt/enterprise-platform/logs/celery-worker.log
stderr_logfile=/opt/enterprise-platform/logs/celery-worker.log

[program:enterprise-celery-beat]
command=/opt/enterprise-platform/venv/bin/celery -A app.tasks.celery_app beat --loglevel=info
directory=/opt/enterprise-platform
user=www-data
autostart=true
autorestart=true
stdout_logfile=/opt/enterprise-platform/logs/celery-beat.log
stderr_logfile=/opt/enterprise-platform/logs/celery-beat.log
```

```bash
# 重新加载 Supervisor 配置
sudo supervisorctl reread
sudo supervisorctl update

# 查看服务状态
sudo supervisorctl status

# 重启服务
sudo supervisorctl restart enterprise-app
```

---

## 7. 数据库备份

### 7.1 手动备份

```bash
# 创建备份目录
sudo mkdir -p /opt/backups/mysql

# 手动备份 MySQL 数据库
mysqldump -u root -p enterprise_platform | gzip > /opt/backups/mysql/enterprise_platform_$(date +%Y%m%d_%H%M%S).sql.gz

# 查看备份文件
ls -lh /opt/backups/mysql/
```

### 7.2 自动备份脚本

创建 `/opt/scripts/backup_mysql.sh`：

```bash
#!/bin/bash

# MySQL 备份脚本

# 配置
MYSQL_USER="root"
MYSQL_PASSWORD="your_password"
DATABASE_NAME="enterprise_platform"
BACKUP_DIR="/opt/backups/mysql"
RETENTION_DAYS=30

# 创建备份目录
mkdir -p "$BACKUP_DIR"

# 生成备份文件名
BACKUP_FILE="$BACKUP_DIR/${DATABASE_NAME}_$(date +%Y%m%d_%H%M%S).sql.gz"

# 执行备份
mysqldump -u "$MYSQL_USER" -p"$MYSQL_PASSWORD" "$DATABASE_NAME" | gzip > "$BACKUP_FILE"

# 检查备份是否成功
if [ $? -eq 0 ]; then
    echo "[$(date)] 备份成功: $BACKUP_FILE"
else
    echo "[$(date)] 备份失败！" >&2
    exit 1
fi

# 删除超过保留期的旧备份
find "$BACKUP_DIR" -name "${DATABASE_NAME}_*.sql.gz" -mtime +$RETENTION_DAYS -delete
echo "[$(date)] 已清理超过 ${RETENTION_DAYS} 天的旧备份"
```

```bash
# 设置脚本执行权限
sudo chmod +x /opt/scripts/backup_mysql.sh

# 测试备份脚本
sudo /opt/scripts/backup_mysql.sh
```

### 7.3 设置定时备份

```bash
# 编辑 crontab
sudo crontab -e

# 每天凌晨 2 点自动备份
0 2 * * * /opt/scripts/backup_mysql.sh >> /opt/backups/backup.log 2>&1
```

### 7.4 恢复数据库

```bash
# 解压并恢复数据库
gunzip < /opt/backups/mysql/enterprise_platform_20240115_020000.sql.gz | mysql -u root -p enterprise_platform
```

### 7.5 Redis 备份

```bash
# 手动触发 Redis 持久化
redis-cli BGSAVE

# 复制 RDB 文件
cp /var/lib/redis/dump.rdb /opt/backups/redis/dump_$(date +%Y%m%d).rdb
```

---

## 8. 监控建议

### 8.1 应用健康检查

```bash
# 使用 curl 检查健康状态
curl -s http://localhost:8000/health | jq .

# 编写健康检查脚本
cat > /opt/scripts/health_check.sh << 'EOF'
#!/bin/bash
RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health)
if [ "$RESPONSE" = "200" ]; then
    echo "[$(date)] 应用健康: OK"
else
    echo "[$(date)] 应用异常: HTTP $RESPONSE" >&2
    # 发送告警通知
    # sudo systemctl restart enterprise-app
fi
EOF
chmod +x /opt/scripts/health_check.sh
```

### 8.2 使用 Flower 监控 Celery

```bash
# 安装 Flower
pip install flower

# 启动 Flower
celery -A app.tasks.celery_app flower --port=5555

# 或在后台运行
nohup celery -A app.tasks.celery_app flower --port=5555 > /opt/enterprise-platform/logs/flower.log 2>&1 &
```

访问 Flower 控制台：http://localhost:5555

### 8.3 系统资源监控

```bash
# 安装 htop 查看系统资源
sudo apt install -y htop
htop

# 查看磁盘使用情况
df -h

# 查看内存使用情况
free -h

# 查看 MySQL 进程
mysql -u root -p -e "SHOW PROCESSLIST;"

# 查看 Redis 信息
redis-cli INFO memory
redis-cli INFO stats
```

### 8.4 推荐监控工具

| 工具 | 用途 | 说明 |
|------|------|------|
| Prometheus | 指标采集 | 搭配 Grafana 使用 |
| Grafana | 可视化面板 | 展示监控数据 |
| Flower | Celery 监控 | 监控异步任务 |
| Sentry | 错误追踪 | 自动捕获应用异常 |
| Uptime Robot | 服务可用性 | 外部监控服务状态 |

---

## 9. 安全加固建议

### 9.1 服务器安全

```bash
# 更新系统
sudo apt update && sudo apt upgrade -y

# 配置防火墙（UFW）
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp        # SSH
sudo ufw allow 80/tcp        # HTTP
sudo ufw allow 443/tcp       # HTTPS
sudo ufw enable

# 禁用 root SSH 登录
sudo sed -i 's/PermitRootLogin yes/PermitRootLogin no/' /etc/ssh/sshd_config
sudo systemctl restart sshd

# 安装 fail2ban 防止暴力破解
sudo apt install -y fail2ban
sudo systemctl enable fail2ban
sudo systemctl start fail2ban
```

### 9.2 应用安全

1. **修改默认密钥**：
   ```env
   # 生产环境必须修改
   SECRET_KEY=使用-python3 -c "import secrets; print(secrets.token_urlsafe(32))"-生成
   ```

2. **关闭调试模式**：
   ```env
   DEBUG=False
   ```

3. **修改默认管理员密码**：首次登录后立即修改管理员密码。

4. **数据库安全**：
   ```sql
   -- 删除匿名用户
   DELETE FROM mysql.user WHERE User='';
   -- 限制 root 只能本地登录
   UPDATE mysql.user SET Host='localhost' WHERE User='root';
   FLUSH PRIVILEGES;
   ```

5. **Redis 安全**：
   ```bash
   # 设置 Redis 密码
   sudo sed -i 's/# requirepass foobared/requirepass your_redis_password/' /etc/redis/redis.conf
   
   # 禁止危险命令
   echo "rename-command FLUSHALL ''" >> /etc/redis/redis.conf
   echo "rename-command CONFIG ''" >> /etc/redis/redis.conf
   
   sudo systemctl restart redis-server
   ```

### 9.3 网络安全

1. **使用 HTTPS**：所有流量通过 HTTPS 加密传输。
2. **配置 CORS**：限制跨域请求来源。
3. **API 限流**：使用 Redis 实现接口限流，防止 DDoS 攻击。
4. **定期更新依赖**：
   ```bash
   # 检查依赖安全漏洞
   pip install safety
   safety check
   
   # 更新依赖
   pip install --upgrade -r requirements.txt
   ```

### 9.4 文件权限

```bash
# 设置项目目录权限
sudo chown -R www-data:www-data /opt/enterprise-platform
sudo chmod -R 750 /opt/enterprise-platform

# 设置 .env 文件权限（仅所有者可读写）
sudo chmod 600 /opt/enterprise-platform/.env

# 设置日志目录权限
sudo chmod -R 750 /opt/enterprise-platform/logs
```

---

## 部署检查清单

在部署完成后，请逐项确认：

- [ ] `.env` 文件已配置正确的生产环境参数
- [ ] `SECRET_KEY` 已修改为随机字符串
- [ ] `DEBUG=False` 已设置
- [ ] 数据库已初始化（`python scripts/init_db.py`）
- [ ] 默认管理员密码已修改
- [ ] SSL 证书已配置
- [ ] Nginx 反向代理已配置并测试通过
- [ ] 防火墙已启用并配置正确
- [ ] systemd/supervisor 服务已设置开机自启
- [ ] 日志轮转已配置
- [ ] 数据库自动备份已设置
- [ ] 健康检查脚本已部署
- [ ] 所有服务状态正常
