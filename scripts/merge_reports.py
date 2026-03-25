"""
merge_reports.py - 合并 5 个并行子代理的审查结果，生成统一审查报告

用法:
  python scripts/merge_reports.py --input-dir temp/001/ --output temp/001/final_review_report.txt

说明:
  本脚本读取 5 个 agent 的输出 JSON 文件，生成统一的审查报告。
  前 5 部分内容直接拼接，"给生成模型的反馈"部分从各 agent 的 findings 中提取并汇总。
"""
import argparse
import json
import os
import sys


def load_json_file(path: str) -> dict:
    """加载 JSON 文件，如果不存在则返回 None"""
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def format_l1_result(result: dict) -> str:
    """格式化 L1 校验结果"""
    if result is None:
        return "### Agent 1: L1 校验\n[未执行]\n"

    lines = ["### Agent 1: L1 校验"]

    # 字数校验
    char_passed = len(result.get("failures", [])) == 0
    lines.append(f"- 字数校验：{'PASS' if char_passed else 'FAIL'}")
    if result.get("failures"):
        # 显示所有字数超限问题
        for f in result["failures"]:
            lines.append(f"  - 镜号{f['shot_number']}: {f['issue']}")

    # 完整性校验
    if "integrity_check" in result:
        integrity = result["integrity_check"]
        lines.append(f"- 完整性校验：{'PASS' if integrity['passed'] else 'FAIL'} - 覆盖率 {integrity['match_rate']*100:.1f}%")

    # 空单元格
    if result.get("empty_cells"):
        lines.append(f"- 空单元格：{len(result['empty_cells'])} 个")

    return "\n".join(lines) + "\n"


def format_l2_result(result: dict, agent_name: str) -> str:
    """格式化 L2 审查结果（统一格式）"""
    if result is None:
        return f"### {agent_name}\n[未执行]\n"

    lines = [f"### {agent_name}"]
    lines.append(f"- 整体判定：{'PASS' if result.get('passed', True) else 'FAIL'}")

    # 如果有总数信息
    if "total_shots" in result:
        lines.append(f"- 总镜号数：{result['total_shots']}")
    if "passed_shots" in result:
        lines.append(f"- 通过：{result['passed_shots']}")
    if "failed_shots" in result:
        lines.append(f"- 失败：{result['failed_shots']}")

    # 如果有 findings，显示所有失败的详情
    findings = result.get("findings", [])
    if findings:
        lines.append("")
        lines.append("#### 问题详情")
        for f in findings:  # 显示所有问题，不再限制数量
            lines.append(f"\n**镜号 {f.get('shot_number', 'N/A')}**")
            lines.append(f"- 问题类型：{f.get('type', '未知')}")
            lines.append(f"- 问题描述：{f.get('issue', '')}")
            if f.get('original'):
                lines.append(f"- 原文：`{f['original']}`")
            if f.get('suggestion'):
                lines.append(f"- 修正建议：{f['suggestion']}")

    return "\n".join(lines) + "\n"


def format_cross_row_result(result: dict) -> str:
    """格式化 L2 跨行一致性检查结果"""
    if result is None:
        return "### Agent 5: L2 跨行一致性检查\n[未执行]\n"

    lines = ["### Agent 5: L2 跨行一致性检查"]
    lines.append(f"- 整体判定：{'PASS' if result.get('passed', True) else 'FAIL'}")
    lines.append(f"- 检查角色数：{result.get('total_characters', 0)}")

    findings = result.get("findings", [])
    if findings:
        lines.append("")
        lines.append("#### 不一致详情")
        for f in findings:
            char = f.get('character', '未知角色')
            attr = f.get('attribute', '未知属性')
            first = f.get('first_appearance', {})
            conflict = f.get('conflict_appearance', {})
            lines.append(f"- **{char}** 的 {attr}: "
                        f"镜号{first.get('shot_number', '?')}=\"{first.get('value', '')}\" vs "
                        f"镜号{conflict.get('shot_number', '?')}=\"{conflict.get('value', '')}\"")

    return "\n".join(lines) + "\n"


def classify_priority(item: dict) -> int:
    """
    根据问题类型返回优先级（数字越小优先级越高）

    优先级分类：
    1. 阻塞性问题 - 空单元格、省略性描述，导致无法生成
    2. 结构问题 - 缺少必要层次、字数超限、完整性不足
    3. 细节问题 - 人设要素缺失、动态逻辑问题、跨镜不一致
    """
    problem_type = item.get("type", "")

    # 优先级 1: 阻塞性问题
    if "空单元格" in problem_type or "省略性描述" in problem_type:
        return 1

    # 优先级 2: 结构问题
    if any(kw in problem_type for kw in ["字数超限", "完整性不足", "结构完整性", "缺少"]):
        return 2

    # 优先级 3: 细节问题
    return 3


def sort_key(item: dict):
    """
    排序键：先按优先级排序，优先级相同则按镜号排序
    """
    priority = classify_priority(item)
    shot = item.get("shot", "999")

    # 尝试将镜号转换为数字以便正确排序
    try:
        shot_num = int(shot)
    except (ValueError, TypeError):
        # 非数字镜号（如"整体"或"3/8"）排在后面
        shot_num = 9999

    return (priority, shot_num)


def generate_feedback(all_results: dict) -> str:
    """
    从各 agent 的 findings 中提取问题，按优先级排序后生成完整的"给生成模型的反馈"部分。

    优化点：
    - 移除硬编码的数量限制，显示所有问题
    - 按优先级分组：阻塞性问题 > 结构问题 > 细节问题
    - 每组内按镜号排序
    - 添加分组统计信息
    """
    lines = ["---", "", "### 给生成模型的反馈", ""]

    # 收集所有失败项
    feedback_items = []

    # Agent 1: L1 失败 - 收集所有问题，不再限制数量
    l1 = all_results.get("l1")
    if l1 and not l1.get("passed"):
        for f in l1.get("failures", []):
            feedback_items.append({
                "shot": str(f["shot_number"]),
                "type": "L1 字数超限",
                "issue": f["issue"],
                "original": f.get("text_preview", ""),
                "suggestion": "请控制原文每行在字数限制内",
                "example": ""
            })
        if l1.get("integrity_check") and not l1["integrity_check"]["passed"]:
            feedback_items.append({
                "shot": "整体",
                "type": "L1 完整性不足",
                "issue": f"覆盖率仅 {l1['integrity_check']['match_rate']*100:.1f}%",
                "original": "",
                "suggestion": "请确保原文内容完整覆盖剧本",
                "example": ""
            })
        for e in l1.get("empty_cells", []):
            feedback_items.append({
                "shot": str(e["shot_number"]),
                "type": f"L1 空单元格 ({e.get('column', '')})",
                "issue": e.get("issue", "单元格为空"),
                "original": "",
                "suggestion": "请补充完整内容",
                "example": ""
            })

    # Agent 2: L2 快速筛选失败 - 收集所有问题
    l2_fast = all_results.get("l2_fast")
    if l2_fast and not l2_fast.get("passed"):
        for f in l2_fast.get("findings", []):
            feedback_items.append({
                "shot": str(f.get("shot_number", "N/A")),
                "type": f.get("type", "L2 快速筛选"),
                "issue": f.get("issue", ""),
                "original": f.get("original", ""),
                "suggestion": f.get("suggestion", ""),
                "example": f.get("example", "")
            })

    # Agent 3: L2 绘图提示词失败 - 收集所有问题
    l2_drawing = all_results.get("l2_drawing")
    if l2_drawing:
        for f in l2_drawing.get("findings", []):
            feedback_items.append({
                "shot": str(f.get("shot_number", "N/A")),
                "type": f.get("issue_type", "绘图提示词问题"),
                "issue": f.get("issue", ""),
                "original": f.get("original", ""),
                "suggestion": f.get("suggestion", ""),
                "example": f.get("example", "")
            })

    # Agent 4: L2 视频提示词失败 - 收集所有问题
    l2_video = all_results.get("l2_video")
    if l2_video:
        for f in l2_video.get("findings", []):
            feedback_items.append({
                "shot": str(f.get("shot_number", "N/A")),
                "type": f.get("issue_type", "视频提示词问题"),
                "issue": f.get("issue", ""),
                "original": f.get("original", ""),
                "suggestion": f.get("suggestion", ""),
                "example": f.get("example", "")
            })

    # Agent 5: L2 跨行一致性失败 - 收集所有问题
    l2_cross = all_results.get("l2_cross_row")
    if l2_cross:
        for f in l2_cross.get("findings", []):
            feedback_items.append({
                "shot": f"{f.get('first_appearance', {}).get('shot_number', '?')}/{f.get('conflict_appearance', {}).get('shot_number', '?')}",
                "type": "角色跨镜不一致",
                "issue": f"{f.get('character', '')}的{f.get('attribute', '')}不一致",
                "original": "",
                "suggestion": f.get("suggestion", ""),
                "example": f.get("example", "")
            })

    if not feedback_items:
        lines.append("所有审查项均通过，无需修正。")
        return "\n".join(lines)

    # 按优先级和镜号排序
    feedback_items.sort(key=sort_key)

    # 统计各优先级问题数量
    priority_counts = {1: 0, 2: 0, 3: 0}
    for item in feedback_items:
        priority = classify_priority(item)
        priority_counts[priority] += 1

    # 生成反馈文本
    lines.append("你的上一次输出未能通过 L2 审查，请根据以下反馈修正：")
    lines.append("")
    lines.append(f"**问题总数：{len(feedback_items)} 条**")

    # 添加优先级统计
    if priority_counts[1] > 0:
        lines.append(f"- 阻塞性问题：{priority_counts[1]} 条（需优先修正）")
    if priority_counts[2] > 0:
        lines.append(f"- 结构问题：{priority_counts[2]} 条")
    if priority_counts[3] > 0:
        lines.append(f"- 细节问题：{priority_counts[3]} 条")
    lines.append("")

    # 按优先级分组输出
    current_priority = None
    priority_names = {
        1: "【优先级 1 - 阻塞性问题】",
        2: "【优先级 2 - 结构问题】",
        3: "【优先级 3 - 细节问题】"
    }

    for item in feedback_items:
        priority = classify_priority(item)

        # 当优先级变化时，添加分组标题
        if priority != current_priority:
            current_priority = priority
            lines.append(f"\n{priority_names[priority]}")
            lines.append("")

        lines.append(f"**镜号 {item['shot']} - {item['type']}**：")
        lines.append(f"- 问题：{item['issue']}")
        if item.get('original'):
            lines.append(f"- 原文：`{item['original']}`")
        if item.get('suggestion'):
            lines.append(f"- 修正建议：{item['suggestion']}")
        lines.append("")

    lines.append("\n请重新生成完整表格，确保所有镜头都通过审查。")

    return "\n".join(lines)


def merge_reports(input_dir: str) -> str:
    """合并所有子代理结果，生成最终报告"""
    # 加载所有结果
    all_results = {
        "l1": load_json_file(os.path.join(input_dir, "agent1_l1_result.json")),
        "l2_fast": load_json_file(os.path.join(input_dir, "agent2_l2_fast.json")),
        "l2_drawing": load_json_file(os.path.join(input_dir, "agent3_l2_drawing.json")),
        "l2_video": load_json_file(os.path.join(input_dir, "agent4_l2_video.json")),
        "l2_cross_row": load_json_file(os.path.join(input_dir, "agent5_l2_cross_row.json"))
    }

    # 计算整体判定
    overall_passed = all(
        r is None or r.get("passed", True)
        for r in all_results.values()
    )

    # 生成报告
    report_lines = [
        f"## L2 审查结果：{'PASS' if overall_passed else 'FAIL'}",
        "",
        format_l1_result(all_results["l1"]),
        format_l2_result(all_results["l2_fast"], "Agent 2: L2 快速筛选"),
        format_l2_result(all_results["l2_drawing"], "Agent 3: L2 绘图提示词逐行审查"),
        format_l2_result(all_results["l2_video"], "Agent 4: L2 视频提示词逐行审查"),
        format_cross_row_result(all_results["l2_cross_row"]),
        "",
        "### 审查总结",
    ]

    # 统计信息
    total_shots = 0
    passed_shots = 0
    if all_results["l2_drawing"]:
        total_shots = all_results["l2_drawing"].get("total_shots", 0)
        passed_shots = all_results["l2_drawing"].get("passed_shots", 0)
    elif all_results["l2_video"]:
        total_shots = all_results["l2_video"].get("total_shots", 0)
        passed_shots = all_results["l2_video"].get("passed_shots", 0)

    report_lines.append(f"- 总镜号数：{total_shots}")
    report_lines.append(f"- 通过镜号：{passed_shots}")
    report_lines.append(f"- 失败镜号：{total_shots - passed_shots}")
    report_lines.append("")

    # 添加反馈部分
    report_lines.append(generate_feedback(all_results))

    return "\n".join(report_lines)


def main():
    parser = argparse.ArgumentParser(description="合并审查报告")
    parser.add_argument("--input-dir", required=True, help="子代理输出文件所在目录")
    parser.add_argument("--output", required=True, help="最终报告输出文件路径")

    args = parser.parse_args()

    report = merge_reports(args.input_dir)

    with open(args.output, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"审查报告已生成：{args.output}")


if __name__ == "__main__":
    main()
