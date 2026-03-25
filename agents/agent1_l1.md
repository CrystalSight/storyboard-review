# Agent 1: L1 校验 - 执行指令

## 任务说明

执行**L1 校验**：字数检查 + 空单元格检查。

**注意**：L1 校验是技术层校验，使用 Python 脚本执行，不需要 AI 亲自审查。

## 输入文件

- `<filename>/parsed.json` - 分镜表格 JSON 数据（相对于当前工作目录）
- `config/config.yaml` - 配置文件（相对于技能目录）

## 输出文件

- `<filename>/agent1_l1_result.json` - L1 校验结果 JSON

## 执行命令

```bash
python <skill-dir>/scripts/l1_validator.py \
  --input <filename>/parsed.json \
  --config <skill-dir>/config/config.yaml \
  > <filename>/agent1_l1_result.json
```

## 检查项

### 1. 字数校验

检查每行原文列的字符数是否超过上限（默认 30 字）。

### 2. 空单元格检查

检查绘图提示词和视频提示词是否为空。

## 输出 JSON 格式

由 `l1_validator.py` 自动生成，格式如下：

```json
{
  "passed": true/false,
  "total_rows": N,
  "char_limit": 30,
  "failures": [
    {
      "shot_number": "镜号",
      "char_count": 字数，
      "max_allowed": 30,
      "text_preview": "原文预览",
      "issue": "问题描述"
    }
  ],
  "empty_cells": [
    {
      "shot_number": "镜号",
      "column": "列名",
      "issue": "单元格为空"
    }
  ]
}
```
