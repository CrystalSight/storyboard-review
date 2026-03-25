"""
l1_validator.py - L1 规则层校验（字数检查 + 空单元格检查）
用法:
  python scripts/l1_validator.py --input parsed.json --config config/config.yaml
  python scripts/l1_validator.py --help

输入：parse_table.py 产出的 JSON 文件
输出：JSON 格式的校验结果
"""
import argparse
import json
import sys
import yaml


def validate(parsed_path: str, max_chars: int = 30) -> dict:
    """
    校验每一行原文列的字符数是否在限制范围内
    并检查绘图提示词和视频提示词是否为空
    """
    with open(parsed_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    rows = data.get("rows", [])
    failures = []
    empty_cells = []

    for row in rows:
        shot = row["shot_number"]
        text = row["original_text"]
        char_count = len(text)

        if char_count == 0:
            empty_cells.append({
                "shot_number": shot,
                "issue": "原文列为空"
            })
        elif char_count > max_chars:
            failures.append({
                "shot_number": shot,
                "char_count": char_count,
                "max_allowed": max_chars,
                "text_preview": text[:50] + ("..." if len(text) > 50 else ""),
                "issue": f"原文共 {char_count} 字，超过上限 {max_chars} 字"
            })

    # 检查绘图提示词和视频提示词是否为空
    for row in rows:
        shot = row["shot_number"]
        if not row["drawing_prompt"].strip():
            empty_cells.append({"shot_number": shot, "issue": "绘图提示词为空"})
        if not row["video_prompt"].strip():
            empty_cells.append({"shot_number": shot, "issue": "视频提示词为空"})

    passed = len(failures) == 0 and len(empty_cells) == 0

    result = {
        "passed": passed,
        "total_rows": len(rows),
        "char_limit": max_chars,
        "failures": failures,
        "empty_cells": empty_cells,
    }

    return result


def main():
    parser = argparse.ArgumentParser(description="L1 字数校验")
    parser.add_argument("--input", required=True, help="parsed.json 文件路径")
    parser.add_argument("--config", required=True, help="config.yaml 配置文件路径")

    args = parser.parse_args()

    # 从配置文件读取 max_chars
    try:
        with open(args.config, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        max_chars = config["l1_rules"]["max_original_text_chars"]
    except FileNotFoundError:
        print(f"错误：配置文件不存在 - {args.config}", file=sys.stderr)
        sys.exit(1)
    except KeyError as e:
        print(f"错误：配置文件中缺少必需的字段 - {e}", file=sys.stderr)
        sys.exit(1)

    result = validate(args.input, max_chars)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
