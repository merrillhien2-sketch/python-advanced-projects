"""办公自动化工具路由

提供 Excel/PDF/CSV 文件处理、批量重命名、数据报告生成等接口。

接口列表:
    - POST /excel/import       上传 Excel 文件转 JSON
    - POST /excel/export       JSON 数据转 Excel 下载
    - POST /excel/merge        合并多个 Excel 文件
    - POST /pdf/extract-text   上传 PDF 提取文本
    - POST /batch-rename       批量重命名预览
    - POST /report/generate    生成数据报告
    - POST /csv/to-json        CSV 转 JSON
    - POST /csv/from-json      JSON 转 CSV 下载
"""

import io

from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.common import ResponseBase
from app.schemas.office import (
    BatchRenameRequest,
    BatchRenameResponse,
    CsvConvertRequest,
    CsvConvertResponse,
    ExcelImportResponse,
    JsonToExcelRequest,
    PdfTextResponse,
    ReportRequest,
    ReportResponse,
)
from app.services.office_service import OfficeService

router = APIRouter()


@router.post(
    "/excel/import",
    response_model=ResponseBase[ExcelImportResponse],
    summary="上传 Excel 文件转 JSON",
)
async def excel_import(
    file: UploadFile = File(..., description="Excel 文件"),
    db: AsyncSession = Depends(get_db),
) -> ResponseBase[ExcelImportResponse]:
    """上传 Excel 文件并转为 JSON

    接受 .xlsx/.xls 文件，解析第一个工作表，
    返回表头和数据行。

    参数:
        file: 上传的 Excel 文件
        db: 异步数据库会话

    返回:
        包含 Excel 数据的响应
    """
    file_bytes = await file.read()
    result = await OfficeService.excel_to_json(file_bytes)
    return ResponseBase(data=ExcelImportResponse(**result))


@router.post(
    "/excel/export",
    summary="JSON 数据转 Excel 下载",
)
async def excel_export(
    request: JsonToExcelRequest,
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """将 JSON 数据转为 Excel 文件下载

    根据传入的 JSON 数据列表生成 Excel 文件，
    以文件流形式返回下载。

    参数:
        request: JSON 转 Excel 请求（数据列表、工作表名称）
        db: 异步数据库会话

    返回:
        Excel 文件流下载响应
    """
    file_bytes = await OfficeService.json_to_excel(
        data=request.data, sheet_name=request.sheet_name
    )

    return StreamingResponse(
        io.BytesIO(file_bytes),
        media_type=(
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        ),
        headers={
            "Content-Disposition": (
                'attachment; filename="export.xlsx"'
            )
        },
    )


@router.post(
    "/excel/merge",
    response_model=ResponseBase[dict],
    summary="合并多个 Excel 文件",
)
async def excel_merge(
    files: list[UploadFile] = File(..., description="多个 Excel 文件"),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """合并多个 Excel 文件到一个

    接受多个 Excel 文件，将所有数据行合并到一个工作表，
    以文件流形式返回下载。

    参数:
        files: 上传的多个 Excel 文件
        db: 异步数据库会话

    返回:
        合并后的 Excel 文件流下载响应
    """
    file_bytes_list = []
    for f in files:
        content = await f.read()
        file_bytes_list.append(content)

    merged_bytes = await OfficeService.merge_excel_files(file_bytes_list)

    return StreamingResponse(
        io.BytesIO(merged_bytes),
        media_type=(
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        ),
        headers={
            "Content-Disposition": (
                'attachment; filename="merged.xlsx"'
            )
        },
    )


@router.post(
    "/pdf/extract-text",
    response_model=ResponseBase[PdfTextResponse],
    summary="上传 PDF 提取文本",
)
async def pdf_extract_text(
    file: UploadFile = File(..., description="PDF 文件"),
    db: AsyncSession = Depends(get_db),
) -> ResponseBase[PdfTextResponse]:
    """上传 PDF 文件并提取文本

    接受 PDF 文件，提取全部页面的文本内容。

    参数:
        file: 上传的 PDF 文件
        db: 异步数据库会话

    返回:
        包含提取文本的响应
    """
    file_bytes = await file.read()
    result = await OfficeService.pdf_extract_text(file_bytes)
    return ResponseBase(data=PdfTextResponse(**result))


@router.post(
    "/batch-rename",
    response_model=ResponseBase[BatchRenameResponse],
    summary="批量重命名预览",
)
async def batch_rename(
    request: BatchRenameRequest,
    db: AsyncSession = Depends(get_db),
) -> ResponseBase[BatchRenameResponse]:
    """批量重命名预览

    根据正则表达式模式对文件名进行替换，返回新旧文件名映射。
    仅生成预览，不实际修改文件。

    参数:
        request: 批量重命名请求（文件名列表、模式、替换字符串）
        db: 异步数据库会话

    返回:
        包含新旧文件名映射的响应
    """
    result = await OfficeService.batch_rename(
        filenames=request.filenames,
        pattern=request.pattern,
        replacement=request.replacement,
    )
    return ResponseBase(data=BatchRenameResponse(**result))


@router.post(
    "/report/generate",
    response_model=ResponseBase[ReportResponse],
    summary="生成数据报告",
)
async def generate_report(
    request: ReportRequest,
    db: AsyncSession = Depends(get_db),
) -> ResponseBase[ReportResponse]:
    """生成数据报告

    根据数据列表生成汇总统计报告，包含记录总数、字段统计、
    数值型字段的统计信息等。

    参数:
        request: 报告生成请求（标题、数据列表）
        db: 异步数据库会话

    返回:
        包含汇总统计信息的报告响应
    """
    template_data = {"title": request.title, "data": request.data}
    result = await OfficeService.generate_report(template_data)
    return ResponseBase(data=ReportResponse(**result))


@router.post(
    "/csv/to-json",
    response_model=ResponseBase[CsvConvertResponse],
    summary="CSV 转 JSON",
)
async def csv_to_json(
    request: CsvConvertRequest,
    db: AsyncSession = Depends(get_db),
) -> ResponseBase[CsvConvertResponse]:
    """CSV 文本转 JSON

    将 CSV 文本内容转为 JSON 字典列表。

    参数:
        request: CSV 转换请求（CSV 文本内容）
        db: 异步数据库会话

    返回:
        包含 JSON 数据列表的响应
    """
    csv_bytes = request.content.encode("utf-8")
    data = await OfficeService.csv_to_json(csv_bytes)
    return ResponseBase(data=CsvConvertResponse(data=data, total=len(data)))


@router.post(
    "/csv/from-json",
    summary="JSON 转 CSV 下载",
)
async def csv_from_json(
    request: JsonToExcelRequest,
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """JSON 数据转 CSV 文件下载

    将 JSON 数据列表转为 CSV 格式，以文件流形式返回下载。

    参数:
        request: JSON 数据请求（数据列表）
        db: 异步数据库会话

    返回:
        CSV 文件流下载响应
    """
    csv_bytes = await OfficeService.json_to_csv(data=request.data)

    return StreamingResponse(
        io.BytesIO(csv_bytes),
        media_type="text/csv",
        headers={
            "Content-Disposition": (
                'attachment; filename="export.csv"'
            )
        },
    )
