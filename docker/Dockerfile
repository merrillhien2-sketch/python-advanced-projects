# 企业级 Python 平台 Dockerfile
# 基础镜像：Python 3.11 精简版
FROM python:3.11-slim

# 设置环境变量：禁用字节码缓存、强制无缓冲输出、设置时区
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TZ=Asia/Shanghai

# 设置工作目录
WORKDIR /app

# 安装系统依赖（含 tesseract-ocr 用于 OCR，及中文语言包）
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        default-libmysqlclient-dev \
        pkg-config \
        tesseract-ocr \
        tesseract-ocr-chi-sim \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖清单并安装（单独一层便于缓存）
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目代码
COPY . .

# 创建日志目录
RUN mkdir -p logs

# 暴露服务端口
EXPOSE 8000

# 启动命令：运行 uvicorn ASGI 服务
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
