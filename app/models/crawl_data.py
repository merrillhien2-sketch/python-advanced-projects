"""爬虫数据模型

定义爬虫抓取数据表结构，存储页面标题、正文、作者、标签及情感得分等信息。
"""

from sqlalchemy import Column, Float, String, Text

from app.models.base import BaseModel


class CrawlData(BaseModel):
    """爬虫抓取数据表模型

    字段说明:
        - source_url: 数据来源的 URL 地址
        - title: 页面标题
        - content: 页面正文内容
        - author: 作者信息，可为空
        - tags: 标签列表（逗号分隔字符串），可为空
        - sentiment_score: 情感分析得分（-1 到 1），可为空
        - status: 数据状态，默认 "active"
    """

    __tablename__ = "crawl_data"

    source_url = Column(Text, nullable=False, comment="来源URL")
    title = Column(String(500), nullable=False, comment="标题")
    content = Column(Text, nullable=False, comment="正文内容")
    author = Column(String(100), nullable=True, comment="作者")
    tags = Column(String(500), nullable=True, comment="标签")
    sentiment_score = Column(Float, nullable=True, comment="情感得分")
    status = Column(String(20), default="active", nullable=False, comment="状态")
