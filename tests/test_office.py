"""办公自动化服务测试。

测试 CSV/JSON 互转、批量重命名预览、数据报告生成功能。
这些服务方法为纯数据处理，不依赖数据库。
"""

import pytest

from app.services.office_service import OfficeService


@pytest.mark.asyncio
async def test_csv_to_json():
    """测试 CSV 转 JSON。

    将 CSV 文本转为 JSON 字典列表，验证行数和字段值。
    """
    csv_content = b"name,age,city\nAlice,30,Beijing\nBob,25,Shanghai\n"
    result = await OfficeService.csv_to_json(csv_content)

    assert isinstance(result, list), "结果应为列表"
    assert len(result) == 2, f"应解析出 2 行数据，实际 {len(result)}"
    assert result[0]["name"] == "Alice", "第一行 name 应为 Alice"
    assert result[0]["age"] == "30", "第一行 age 应为 30"
    assert result[1]["city"] == "Shanghai", "第二行 city 应为 Shanghai"


@pytest.mark.asyncio
async def test_json_to_csv():
    """测试 JSON 转 CSV。

    将字典列表转为 CSV 字节内容，验证包含正确的表头和数据行。
    """
    data = [
        {"name": "Alice", "age": 30, "city": "Beijing"},
        {"name": "Bob", "age": 25, "city": "Shanghai"},
    ]
    result = await OfficeService.json_to_csv(data)

    assert isinstance(result, bytes), "结果应为字节内容"
    csv_text = result.decode("utf-8")
    lines = csv_text.strip().split("\n")
    assert len(lines) == 3, f"CSV 应包含 1 行表头 + 2 行数据 = 3 行，实际 {len(lines)}"
    assert "name" in lines[0], "表头应包含 name"
    assert "Alice" in lines[1], "第一行数据应包含 Alice"
    assert "Bob" in lines[2], "第二行数据应包含 Bob"


@pytest.mark.asyncio
async def test_batch_rename():
    """测试批量重命名预览。

    根据正则模式替换文件名，验证新旧文件名映射正确。
    """
    filenames = ["report_2023.pdf", "data_2023.xlsx", "notes_2023.txt"]
    pattern = r"2023"
    replacement = "2024"

    result = await OfficeService.batch_rename(filenames, pattern, replacement)

    assert result["total"] == 3, f"应返回 3 个映射，实际 {result['total']}"
    mappings = result["mappings"]
    assert mappings[0]["old_name"] == "report_2023.pdf"
    assert mappings[0]["new_name"] == "report_2024.pdf"
    assert mappings[1]["new_name"] == "data_2024.xlsx"
    assert mappings[2]["new_name"] == "notes_2024.txt"


@pytest.mark.asyncio
async def test_generate_report():
    """测试数据报告生成。

    根据数据列表生成汇总统计报告，验证标题、记录数和字段统计。
    """
    template_data = {
        "title": "销售数据报告",
        "data": [
            {"product": "A", "price": 100, "quantity": 10},
            {"product": "B", "price": 200, "quantity": 5},
            {"product": "C", "price": 150, "quantity": 8},
        ],
    }

    result = await OfficeService.generate_report(template_data)

    assert result["title"] == "销售数据报告", "报告标题应一致"
    assert result["summary"]["total_records"] == 3, "总记录数应为 3"
    assert result["summary"]["total_fields"] == 3, "字段数应为 3"
    assert "generated_at" in result, "应包含生成时间"
    # 验证数值字段统计
    assert "price" in result["summary"]["field_stats"], "应包含 price 字段统计"
    assert result["summary"]["field_stats"]["price"]["sum"] == 450, "price 总和应为 450"
    assert result["summary"]["field_stats"]["price"]["max"] == 200, "price 最大值应为 200"
    assert result["summary"]["field_stats"]["price"]["min"] == 100, "price 最小值应为 100"
