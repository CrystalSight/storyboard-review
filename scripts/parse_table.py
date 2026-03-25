"""
parse_table.py - 解析 AI 返回的 Markdown 表格
用法:
  python scripts/parse_table.py --input response.txt --output parsed.json
  python scripts/parse_table.py --help
"""
import argparse
import json
import re
import sys


def extract_table_from_markdown(text: str) -> list[dict]:
    """从 markdown 文本中提取表格行，返回结构化数据列表。
    
    每条记录包含: shot_number, original_text, drawing_prompt, video_prompt
    """
    lines = text.strip().split("\n")

    # 定位表格区域：查找包含 | 镜号 | 的表头行
    header_idx = -1
    for i, line in enumerate(lines):
        if re.search(r"\|\s*镜号\s*\|", line):
            header_idx = i
            break

    if header_idx == -1:
        return []

    # 跳过分隔行（---）
    data_start = header_idx + 2

    rows = []
    for i in range(data_start, len(lines)):
        line = lines[i].strip()
        if not line.startswith("|"):
            break

        cells = [c.strip() for c in line.split("|")]
        # split("|") 会在首尾产生空字符串
        cells = [c for c in cells if c != "" or cells.index(c) not in (0, len(cells)-1)]
        cells = [c for c in cells if c]

        if len(cells) >= 4:
            rows.append({
                "shot_number": cells[0],
                "original_text": cells[1],
                "drawing_prompt": cells[2],
                "video_prompt": cells[3],
            })

    return rows


def main():
    parser = argparse.ArgumentParser(description="解析 Markdown 表格")
    parser.add_argument("--input", required=True, help="AI 响应文本文件路径")
    parser.add_argument("--output", default=None, help="输出 JSON 文件路径")

    args = parser.parse_args()

    with open(args.input, "r", encoding="utf-8") as f:
        text = f.read()

    rows = extract_table_from_markdown(text)

    result = {
        "total_rows": len(rows),
        "rows": rows,
    }

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(json.dumps({"status": "success", "total_rows": len(rows), "output_file": args.output}, ensure_ascii=False))
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
