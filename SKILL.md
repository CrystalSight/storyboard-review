---
name: storyboard-review
description: >
  动漫分镜脚本的并行审查器。接收分镜表格 JSON 后，启动 5 个子代理并行执行：
  L1 校验（脚本执行）、L2 快速筛选（AI 执行）、L2 绘图提示词逐行审查（AI 执行）、
  L2 视频提示词逐行审查（AI 执行）、L2 跨行一致性检查（AI 执行）。
  汇总所有结果生成统一审查报告，并在末尾输出"给生成模型的反馈"。
  Use when 需要审查分镜脚本质量、执行 L1/L2 校验、并行加速审查流程。
---

# 分镜脚本并行审查器

## Important

**重要约束**：
- L1 校验使用 Python 脚本执行（技术层校验）
- **L2 审查必须由 AI 亲自执行**，严格禁止编写 Python 脚本来执行审查逻辑
- 5 个子代理使用 subagent 工具并行启动
- **汇总报告必须使用 `merge_reports.py` 脚本生成，禁止模型手动汇总**

---

## 核心执行流程

### 步骤 1：准备输入文件

确保已有以下文件（路径相对于**用户当前工作目录**）：

- `<filename>/parsed.json` - 已解析的分镜表格 JSON

如果没有 `parsed.json`，先运行：
```bash
python <skill-dir>/scripts/parse_table.py \
  --input response.txt \
  --output <filename>/parsed.json
```

---

### 步骤 2：启动 5 个并行子代理

**重要**：你必须使用 subagent 工具同时启动 5 个审查子代理。每个子代理**必须先从阅读详细指令文件开始**。

#### subagent 1 (L1 校验) - Python 脚本执行

```markdown
【必须先读】请完整阅读详细指令文件：<skill-dir>/agents/agent1_l1.md

任务信息：
- 输入文件：<filename>/parsed.json
- 配置文件：<skill-dir>/config/config.yaml
- 输出文件：<filename>/agent1_l1_result.json
- 执行方式：运行 Python 脚本

执行命令：
python <skill-dir>/scripts/l1_validator.py --input <filename>/parsed.json --config <skill-dir>/config/config.yaml > <filename>/agent1_l1_result.json
```

---

#### subagent 2 (L2 快速筛选) - AI 亲自执行

```markdown
【必须先读】请完整阅读详细指令文件：<skill-dir>/agents/agent2_l2_fast.md

任务信息：
- 输入文件：<filename>/parsed.json
- 输出文件：<filename>/agent2_l2_fast.json
- 执行方式：AI 亲自执行（禁止使用脚本）

审查任务：省略性描述扫描 + 空单元格检查

核心原则：必须对每一个镜头执行完整审查，禁止抽样、禁止跳过
```

---

#### subagent 3 (L2 绘图提示词审查) - AI 亲自执行

```markdown
【必须先读】请完整阅读详细指令文件：<skill-dir>/agents/agent3_l2_drawing.md

任务信息：
- 输入文件：<filename>/parsed.json
- 参考文件：<skill-dir>/references/validation_rules.md, <skill-dir>/references/boundary_cases.md
- 输出文件：<filename>/agent3_l2_drawing.json
- 执行方式：AI 亲自执行（禁止使用脚本）

审查任务：
- 步骤 1：判断主体类型（有角色→路径 A / 无角色→路径 B / 非人物主体→路径 C）
- 步骤 2：执行对应路径的完整审查流程

核心原则：必须对每一个镜头执行完整审查，禁止抽样、禁止跳过
```

---

#### subagent 4 (L2 视频提示词审查) - AI 亲自执行

```markdown
【必须先读】请完整阅读详细指令文件：<skill-dir>/agents/agent4_l2_video.md

任务信息：
- 输入文件：<filename>/parsed.json
- 参考文件：<skill-dir>/references/validation_rules.md
- 输出文件：<filename>/agent4_l2_video.json
- 执行方式：AI 亲自执行（禁止使用脚本）

审查任务：结构完整性 4 层检查 + 动态逻辑合理性检查

核心原则：必须对每一个镜头执行完整审查，禁止抽样、禁止跳过
```

---

#### subagent 5 (L2 跨行一致性检查) - AI 亲自执行

```markdown
【必须先读】请完整阅读详细指令文件：<skill-dir>/agents/agent5_l2_cross_row.md

任务信息：
- 输入文件：<filename>/parsed.json
- 输出文件：<filename>/agent5_l2_cross_row.json
- 执行方式：AI 亲自执行（禁止使用脚本）

审查任务：角色人设提取 + 跨镜对比一致性

核心原则：必须对每一个镜头执行完整审查，禁止抽样、禁止跳过
```

---

### 步骤 3：汇总审查报告（必须使用脚本）

**重要约束**：
- **必须使用 `merge_reports.py` 脚本生成最终报告**
- **禁止模型手动汇总或自己编写汇总逻辑**
- **禁止修改报告格式** - 脚本会自动生成标准格式

所有子代理完成后，运行汇总脚本：

```bash
python <skill-dir>/scripts/merge_reports.py \
  --input-dir <filename>/ \
  --output <filename>/final_review_report.txt
```

**脚本自动处理**：
1. 读取 5 个 agent 的输出 JSON 文件
2. 生成统一的审查报告格式
3. 从各 agent 的 findings 中提取问题并汇总
4. 按优先级排序生成"给生成模型的反馈"部分

**故障排查**：
- 如某个 agent 输出文件缺失，重新运行对应的子代理
- 检查文件路径是否正确

---

## 子代理任务索引

| 子代理 | 详细指令文件 | 执行方式 | 主要检查项 |
|--------|-------------|---------|-----------|
| Agent 1 (L1 校验) | `agents/agent1_l1.md` | Python 脚本 | 字数检查 + 空单元格检查 |
| Agent 2 (L2 快速筛选) | `agents/agent2_l2_fast.md` | AI 亲自执行 | 省略性描述 + 空单元格 |
| Agent 3 (L2 绘图审查) | `agents/agent3_l2_drawing.md` | AI 亲自执行 | 路径判断 + 结构完整性 |
| Agent 4 (L2 视频审查) | `agents/agent4_l2_video.md` | AI 亲自执行 | 结构 4 层 + 动态逻辑 |
| Agent 5 (L2 跨行检查) | `agents/agent5_l2_cross_row.md` | AI 亲自执行 | 角色跨镜一致性 |

**注意**：详细审查规则、判定标准、示例输出请参阅对应的 `agents/agentX_XXX.md` 文件。

---

## 配置说明

### config/config.yaml

```yaml
l1_rules:
  max_original_text_chars: 30  # 原文列字数上限
```

---

## 路径约定

- `<skill-dir>`: 技能目录的绝对路径
- `<filename>`: 相对于用户当前工作目录的路径
- 技能资源：`scripts/`, `references/`, `config/`, `agents/` 均在技能目录下

---

## 输出文件

| 文件 | 说明 |
|------|------|
| `<filename>/agent1_l1_result.json` | L1 校验结果 |
| `<filename>/agent2_l2_fast.json` | L2 快速筛选结果 |
| `<filename>/agent3_l2_drawing.json` | L2 绘图提示词审查结果 |
| `<filename>/agent4_l2_video.json` | L2 视频提示词审查结果 |
| `<filename>/agent5_l2_cross_row.json` | L2 跨行一致性检查结果 |
| `<filename>/final_review_report.txt` | 最终汇总审查报告 |
| `<filename>/feedback_for_model.txt` | 给生成模型的反馈（单独文件） |

---

## 故障排查

### 某个子代理卡住

检查对应输出文件是否生成：
```bash
ls -la <filename>/agent*_*.json
```

如某个文件缺失，重新运行对应的子代理。

### 审查结果与实际不符

检查 `parsed.json` 是否正确解析。可重新运行 `parse_table.py`。

### 汇总报告格式异常

确保使用了 `merge_reports.py` 脚本，而非手动汇总。
