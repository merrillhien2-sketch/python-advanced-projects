"""办公自动化相关 Schema

定义 Excel/PDF/CSV 文件转换、批量重命名、数据报告生成等
办公自动化场景下的请求与响应数据模型。
"""

from typing import Any, Optional

from pydantic import BaseModel, Field


class ExcelImportResponse(BaseModel):
    """Excel 导入响应

    属性:
        sheet_name: 工作表名称
        headers: 表头列表
        rows: 数据行列表（每行为字典）
        total_rows: 数据总行数
    """

    sheet_name: str = Field(..., description="工作表名称")
    headers: list[str] = Field(default_factory=list, description="表头列表")
    rows: list[dict] = Field(default_factory=list, description="数据行列表")
    total_rows: int = Field(0, description="数据总行数")


class JsonToExcelRequest(BaseModel):
    """JSON 转 Excel 请求

    属性:
        data: JSON 数据列表，每个元素为一行数据
        sheet_name: 工作表名称，默认 Sheet1
    """

    data: list[dict] = Field(..., description="JSON 数据列表")
    sheet_name: str = Field(default="Sheet1", description="工作表名称")


class PdfTextResponse(BaseModel):
    """PDF 文本提取响应

    属性:
        pages: 总页数
        text: 全部页面合并后的文本
        page_texts: 按页拆分的文本列表
    """

    pages: int = Field(0, description="总页数")
    text: str = Field(default="", description="全部页面合并文本")
    page_texts: list[str] = Field(default_factory=list, description="按页拆分的文本列表")


class BatchRenameRequest(BaseModel):
    """批量重命名请求

    属性:
        filenames: 原始文件名列表
        pattern: 待替换的模式（支持正则表达式）
        replacement: 替换后的字符串
    """

    filenames: list[str] = Field(..., description="原始文件名列表")
    pattern: str = Field(..., description="待替换的模式")
    replacement: str = Field(default="", description="替换后的字符串")


class BatchRenameResponse(BaseModel):
    """批量重命名响应

    属性:
        mappings: 新旧文件名映射列表
        total: 映射总数
    """

    mappings: list[dict[str, str]] = Field(default_factory=list, description="新旧文件名映射列表")
    total: int = Field(0, description="映射总数")


class ReportRequest(BaseModel):
    """数据报告生成请求

    属性:
        title: 报告标题
        data: 报告数据列表，每个元素为字典
    """

    title: str = Field(..., description="报告标题")
    data: list[dict] = Field(default_factory=list, description="报告数据列表")


class ReportResponse(BaseModel):
    """数据报告生成响应

    属性:
        title: 报告标题
        summary: 汇总统计信息
        generated_at: 报告生成时间（ISO 格式字符串）
    """

    title: str = Field(..., description="报告标题")
    summary: dict[str, Any] = Field(default_factory=dict, description="汇总统计信息")
    generated_at: str = Field(..., description="报告生成时间")


class CsvConvertRequest(BaseModel):
    """CSV 转换请求

    属性:
        content: CSV 文本内容
    """

    content: str = Field(..., description="CSV 文本内容")


class CsvConvertResponse(BaseModel):
    """CSV 转 JSON 响应

    属性:
        data: 转换后的 JSON 数据列表
        total: 数据总行数
    """

    data: list[dict] = Field(default_factory=list, description="转换后的 JSON 数据列表")
    total: int = Field(0, description="数据总行数")
