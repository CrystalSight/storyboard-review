# storyboard-review

动漫分镜脚本并行审查器。接收分镜表格 JSON 后，启动 5 个子代理并行执行审查，汇总生成统一报告。

## 功能特性

- **并行执行** - 5 个审查代理同时运行，耗时降低 40-60%
- **L1 校验** - 字数限制、空单元格检查（Python 脚本）
- **L2 审查** - 省略性描述、绘图提示词、视频提示词、跨行一致性（AI 执行）
- **统一报告** - 自动生成结构化审查报告和修正反馈

## 快速开始

### 前置条件

- Python 3.9+
- 已解析的分镜表格 `parsed.json`

### 执行审查

```bash
# 1. 解析 Markdown 表格为 JSON
python scripts/parse_table.py --input response.txt --output temp/001/parsed.json

# 2. 启动 5 个并行子代理（通过 Claude Code skill）
# 主会话加载 skill 后自动执行

# 3. 汇总审查报告
python scripts/merge_reports.py --input-dir temp/001/ --output temp/001/final_review_report.txt
```

## 5 个审查代理

| 代理 | 执行方式 | 检查项 |
|------|---------|--------|
| Agent 1 (L1) | Python 脚本 | 字数限制、空单元格 |
| Agent 2 (L2) | AI 执行 | 省略性描述、空单元格 |
| Agent 3 (L2) | AI 执行 | 绘图提示词结构、角色人设 9 要素 |
| Agent 4 (L2) | AI 执行 | 视频提示词结构、动态逻辑 |
| Agent 5 (L2) | AI 执行 | 角色跨镜头一致性 |

## 输出示例

```
## L2 审查结果：FAIL

### Agent 1: L1 校验
- 字数校验：PASS
- 完整性校验：PASS - 覆盖率 92%

### Agent 3: L2 绘图提示词逐行审查
- 整体判定：FAIL
- 总镜号数：10
- 通过：7 | 失败：3

### 给生成模型的反馈
**镜号 3 - 角色人设 9 要素**：
- 问题：缺少第 6 项：下装描述
- 修正建议：补充下装描述，如'下着黑色长裤'
```

## 目录结构

```
storyboard-review/
├── SKILL.md                 # Claude Code skill 入口
├── README.md                # 本文档
├── config/
│   └── config.yaml          # 审查规则配置
├── scripts/
│   ├── parse_table.py       # Markdown 表格解析
│   ├── l1_validator.py      # L1 校验脚本
│   └── merge_reports.py     # 报告汇总脚本
├── agents/                  # 子代理执行指令
│   ├── agent1_l1.md
│   ├── agent2_l2_fast.md
│   ├── agent3_l2_drawing.md
│   ├── agent4_l2_video.md
│   └── agent5_l2_cross_row.md
└── references/              # 审查规则参考
    ├── validation_rules.md  # 审查规则详情
    └── boundary_cases.md    # 边界案例库
```

## 许可证

MIT License
