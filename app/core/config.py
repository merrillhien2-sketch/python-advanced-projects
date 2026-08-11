"""应用配置管理模块。

基于 pydantic-settings 从环境变量与 .env 文件加载全局配置，
所有模块统一通过 settings 单例读取配置，禁止硬编码。
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """全局配置类。

    所有配置项均可通过环境变量或 .env 文件覆盖，
    字段名大小写敏感。
    """

    # ---------- 应用配置 ----------
    APP_NAME: str = "Python Enterprise Platform"
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # ---------- 数据库配置 ----------
    DATABASE_URL: str = "mysql+aiomysql://root:password@localhost:3306/enterprise_db"
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_RECYCLE: int = 3600

    # ---------- Redis 配置 ----------
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_KEY_PREFIX: str = "enterprise:"

    # ---------- 安全配置 ----------
    SECRET_KEY: str = "change-me-in-production-use-openssl-rand-hex-32"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24

    # ---------- Celery 配置 ----------
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"
    CELERY_TIMEZONE: str = "Asia/Shanghai"

    # ---------- 限流配置 ----------
    RATE_LIMIT_PER_MINUTE: int = 60
    RATE_LIMIT_ENABLED: bool = True

    # ---------- CORS 配置 ----------
    CORS_ORIGINS: str = "*"

    # ---------- 日志配置 ----------
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "logs/app.log"
    LOG_MAX_BYTES: int = 10 * 1024 * 1024
    LOG_BACKUP_COUNT: int = 5

    # ---------- 管理员配置（初始化脚本使用） ----------
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = "admin123456"
    ADMIN_EMAIL: str = "admin@example.com"

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore",
    )


# 全局配置单例
settings = Settings()
