#!/usr/bin/env python3
"""数据库初始化脚本。

功能：
1. 创建所有数据库表
2. 创建默认管理员用户
3. 打印初始化结果

可独立运行：
    python scripts/init_db.py

环境变量通过 app.core.config.settings 读取。
"""

import asyncio
import sys
import os
import logging

# 将项目根目录添加到 Python 路径，确保可以导入 app 模块
# 脚本可能从项目根目录或 scripts/ 目录运行，需要兼容两种情况
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from sqlalchemy import select  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.core.database import Base, engine, AsyncSessionLocal  # noqa: E402

# 导入所有模型，确保它们被注册到 Base.metadata
from app.models import User, ShortLink, TaskRecord, CrawlData  # noqa: E402, F401

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


async def create_tables() -> None:
    """创建所有数据库表。

    使用 SQLAlchemy 的 Base.metadata.create_all 方法，
    根据模型定义在数据库中创建所有表。
    """
    logger.info("正在创建数据库表...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("数据库表创建成功！")


async def create_default_admin() -> dict:
    """创建默认管理员用户。

    从配置中读取管理员用户名、密码和邮箱，
    如果用户不存在则创建。

    Returns:
        包含管理员用户信息的字典，如果用户已存在则返回提示信息
    """
    # 从配置中获取管理员信息
    admin_username = getattr(settings, "ADMIN_USERNAME", "admin")
    admin_password = getattr(settings, "ADMIN_PASSWORD", "admin123456")
    admin_email = getattr(settings, "ADMIN_EMAIL", "admin@example.com")

    logger.info("正在创建默认管理员用户...")

    async with AsyncSessionLocal() as db:
        # 检查管理员用户是否已存在
        stmt = select(User).where(User.username == admin_username)
        result = await db.execute(stmt)
        existing_user = result.scalars().first()

        if existing_user is not None:
            logger.info("管理员用户已存在，跳过创建: %s", admin_username)
            return {
                "created": False,
                "username": admin_username,
                "email": admin_email,
                "message": "管理员用户已存在",
            }

        # 使用 app.core.security 中的密码哈希函数
        try:
            from app.core.security import hash_password

            hashed_password = hash_password(admin_password)
        except ImportError:
            # 如果 security 模块不可用，使用 bcrypt 直接哈希
            import bcrypt

            hashed_password = bcrypt.hashpw(
                admin_password.encode("utf-8"), bcrypt.gensalt()
            ).decode("utf-8")

        # 创建管理员用户（User 模型使用 role 字段表示角色，非 is_admin）
        admin_user = User(
            username=admin_username,
            email=admin_email,
            hashed_password=hashed_password,
            is_active=True,
            role="admin",
        )
        db.add(admin_user)
        await db.commit()

        logger.info("默认管理员用户创建成功！")
        logger.info("  用户名: %s", admin_username)
        logger.info("  邮箱: %s", admin_email)

        return {
            "created": True,
            "username": admin_username,
            "email": admin_email,
            "message": "管理员用户创建成功",
        }


async def main() -> None:
    """主函数：执行数据库初始化流程。"""
    print("=" * 50)
    print("  企业级 Python 平台 - 数据库初始化")
    print("=" * 50)

    try:
        # 步骤 1：创建数据库表
        await create_tables()

        # 步骤 2：创建默认管理员用户
        admin_info = await create_default_admin()

        # 打印初始化结果
        print()
        print("-" * 50)
        print("初始化结果汇总：")
        print(f"  数据库表: 创建成功")
        print(f"  管理员用户: {admin_info['message']}")
        if admin_info.get("created"):
            print(f"    用户名: {admin_info['username']}")
            print(f"    邮箱: {admin_info['email']}")
            print(f"    密码: (请查看 .env 中的 ADMIN_PASSWORD)")
            print()
            print("  ⚠ 安全提示: 请在首次登录后立即修改管理员密码！")
        print("-" * 50)
        print()
        print("=" * 50)
        print("  数据库初始化完成！")
        print("=" * 50)

    except Exception as e:
        logger.error("数据库初始化失败: %s", e, exc_info=True)
        print()
        print("=" * 50)
        print("  数据库初始化失败！")
        print(f"  错误: {e}")
        print("=" * 50)
        sys.exit(1)


if __name__ == "__main__":
    # 运行异步主函数
    asyncio.run(main())
