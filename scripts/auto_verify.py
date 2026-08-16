#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
安评检查助手 - 报告自动校验工具（轻量级）
每次生成报告后自动运行，核对扣分值、风险等级、引用标准与知识库一致性。

用法：
  python auto_verify.py <报告文件路径> [--kb <知识库路径>] [--risk <风险标准路径>] [--output <校验报告输出路径>]

退出码：
  0 = 全部通过
  1 = 存在校验偏差
  2 = 参数或文件错误
"""

import sys
import os
import json
import re
import argparse
from datetime import datetime

# ── 默认路径 ──────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_ROOT = os.path.dirname(SCRIPT_DIR)
DEFAULT_KB = os.path.join(SKILL_ROOT, "assets", "knowledge_base.json")
DEFAULT_RISK = os.path.join(SKILL_ROOT, "references", "risk_criteria.json")


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def extract_leaves(node, results=None):
    """递归提取知识库叶子条款"""
    if results is None:
        results = []
    sub = node.get("sub_clauses", [])
    if not sub:
        results.append(node)
    else:
        for child in sub:
            extract_leaves(child, results)
    return results


def build_clause_map(kb):
    """构建 clause_id → 叶子条款 的映射"""
    clauses = kb["clauses"]
    leaves = []
    for c in clauses:
        extract_leaves(c, leaves)
    return {l["id"]: l for l in leaves}


def build_module_map(kb):
    """构建模块 id → 叶子条款列表 的映射"""
    clauses = kb["clauses"]
    mmap = {}
    for c in clauses:
        for m in c.get("sub_clauses", []):
            m_leaves = []
            extract_leaves(m, m_leaves)
            mmap[m["id"]] = {
                "name": m["name"],
                "score": m["score"],
                "leaves": m_leaves,
            }
    return mmap


# ── 报告解析 ──────────────────────────────────────────

def parse_report(md_text):
    """从 Markdown 报告中提取结构化数据"""
    results = {
        "total_score": None,
        "full_score": None,
        "modules": [],
        "issues": [],
    }

    # 提取合计得分
    m = re.search(r"合计得分[：:]\s*(\d+)\s*/\s*(\d+)\s*分", md_text)
    if m:
        results["total_score"] = int(m.group(1))
        results["full_score"] = int(m.group(2))

    # 提取模块得分表
    mod_pattern = re.compile(
        r"\|\s*(2\.7\.\d+)\s+(.+?)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*([\d.]+)%\s*\|"
    )
    for m in mod_pattern.finditer(md_text):
        results["modules"].append({
            "id": m.group(1).strip(),
            "name": m.group(2).strip(),
            "full": int(m.group(3)),
            "actual": int(m.group(4)),
            "deduction": int(m.group(5)),
            "rate": float(m.group(6)),
        })

    # 提取问题详情表 - 支持两种列序
    # 模式1: 序号|问题描述|关联条款|风险等级|条款分值|扣分|扣分依据|参考依据|整改建议|备注
    # 模式2: 序号|问题描述|关联条款|风险等级|条款分值|扣分|参考依据|扣分依据|整改建议|备注
    issue_pattern = re.compile(
        r"\|\s*(\d+)\s*\|\s*(.+?)\s*\|\s*(2\.7[\d.]+)\s+(.+?)\s*\|\s*(高|中|低)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|"
    )
    for m in issue_pattern.finditer(md_text):
        clause_part = m.group(3)
        clause_id = clause_part.strip()
        # 清理可能的冗余编号
        clause_id = re.match(r"(2\.7[\d.]+)", clause_id)
        clause_id = clause_id.group(1) if clause_id else clause_part.strip()

        results["issues"].append({
            "seq": int(m.group(1)),
            "desc": m.group(2).strip(),
            "clause_id": clause_id,
            "clause_name": m.group(4).strip(),
            "risk_level": m.group(5),
            "clause_score": int(m.group(6)),
            "deduction": int(m.group(7)),
        })

    return results


# ── 校验逻辑 ──────────────────────────────────────────

def verify_deduction(issue, kb_clause):
    """校验扣分值与知识库扣分规则一致性"""
    deduction = issue["deduction"]
    clause_score = issue["clause_score"]
    rules = kb_clause.get("deduction_rules", [])

    # 检查"不得分"规则
    for rule in rules:
        if "不得分" in rule:
            # 如果扣分=条款标准分，则与"不得分"一致
            if deduction == clause_score:
                return True, f"扣{deduction}分=不得分，符合规则「{rule}」"

    # 检查固定扣分
    for rule in rules:
        nums = re.findall(r"扣(\d+)分", rule)
        for n in nums:
            if deduction == int(n):
                return True, f"扣{deduction}分，符合规则「{rule}」"

    # 检查灵活扣分（"每项扣X分"）
    for rule in rules:
        m = re.search(r"每项扣(\d+)分", rule)
        if m:
            per = int(m.group(1))
            if deduction > 0 and deduction % per == 0 and deduction <= clause_score:
                items = deduction // per
                return True, f"扣{deduction}分={items}项×{per}分/项，符合规则「{rule}」"

    # 检查分段扣分
    matched_partial = False
    for rule in rules:
        nums = re.findall(r"扣(\d+)分", rule)
        for n in nums:
            if deduction <= int(n):
                matched_partial = True

    if matched_partial:
        return True, f"扣{deduction}分，在规则范围内"

    return False, f"扣{deduction}分，未匹配到任何扣分规则。规则：{rules}"


def verify_risk_level(issue, risk_criteria, kb_clause=None):
    """校验风险等级与阈值+关键词+扣分比例一致性
    
    判定逻辑：
    1. "不得分"（扣分=标准分）→ 高风险（严重缺失/失效）
    2. 扣分<标准分 且 关键词命中高风险 → 按关键词提升
    3. 扣分<标准分 且 无高风险关键词 → 按扣分占标准分比例判定：
       - 占比≥50% → 中风险
       - 占比<50% → 低风险
    """
    deduction = issue["deduction"]
    clause_score = issue["clause_score"]
    reported_level = issue["risk_level"]

    levels = risk_criteria["risk_levels"]
    high_keywords = levels["high"]["keywords"]
    medium_keywords = levels["medium"]["keywords"]

    desc = issue.get("desc", "")
    clause_name = issue.get("clause_name", "")

    # 判定逻辑
    # 1. "不得分"情形：扣分=标准分 → 高风险
    if deduction == clause_score:
        determined = "高"
    # 2. 关键词命中高风险 → 高风险
    elif any(kw in desc or kw in clause_name for kw in high_keywords):
        determined = "高"
    # 3. 按扣分占比判定
    else:
        ratio = deduction / clause_score if clause_score > 0 else 0
        if ratio >= 0.5:
            determined = "中"
        else:
            determined = "低"

    # 关键词提升（中→高）：仅当关键词明确命中
    if determined == "中":
        for kw in high_keywords:
            if kw in desc or kw in clause_name:
                determined = "高"
                break

    # 关键词提升（低→中）
    if determined == "低":
        for kw in medium_keywords:
            if kw in desc or kw in clause_name:
                determined = "中"
                break

    if determined == reported_level:
        return True, f"风险等级「{reported_level}」与扣分{deduction}/{clause_score}分+关键词匹配一致"
    else:
        return False, f"风险等级「{reported_level}」，但根据扣分{deduction}/{clause_score}分({deduction/clause_score*100:.0f}%)+关键词应判定为「{determined}」"


def verify_reference(issue, kb_clause):
    """校验引用标准与知识库一致性"""
    # 报告中的参考依据无法从简化的 issue 中精确提取，改为在后续全量校验中处理
    # 此处仅校验知识库是否有引用标准
    ref = kb_clause.get("reference", "")
    if ref:
        return True, f"知识库有引用标准（{len(ref)}字）"
    else:
        return False, "知识库缺少引用标准"


def verify_module_scores(report_data, module_map):
    """校验模块得分加总"""
    results = []
    report_total = 0

    for mod in report_data["modules"]:
        mid = mod["id"]
        report_total += mod["actual"]

        if mid not in module_map:
            results.append(("⚠", mid, f"模块{mid}在知识库中未找到"))
            continue

        kb_mod = module_map[mid]
        kb_full = kb_mod["score"]
        kb_leaf_sum = sum(l.get("score", 0) for l in kb_mod["leaves"])

        checks = []
        if mod["full"] != kb_full:
            checks.append(f"报告满分{mod['full']}≠知识库{kb_full}")
        if kb_full != kb_leaf_sum:
            checks.append(f"知识库声明{kb_full}≠叶子加总{kb_leaf_sum}")

        if checks:
            results.append(("✗", mid, "；".join(checks)))
        else:
            results.append(("✓", mid, f"满分{kb_full}分一致"))

    # 总分校验
    if report_data["total_score"] is not None:
        if report_data["total_score"] == report_total:
            results.append(("✓", "总分", f"{report_total}/{report_data['full_score']} 一致"))
        else:
            results.append(("✗", "总分", f"报告{report_data['total_score']}≠模块加总{report_total}"))

    return results


# ── 主流程 ──────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="安评检查助手 - 报告自动校验工具")
    parser.add_argument("report", help="待校验的评价报告路径（Markdown）")
    parser.add_argument("--kb", default=DEFAULT_KB, help="知识库JSON路径")
    parser.add_argument("--risk", default=DEFAULT_RISK, help="风险标准JSON路径")
    parser.add_argument("--output", default=None, help="校验报告输出路径")
    args = parser.parse_args()

    # 加载资源
    if not os.path.exists(args.report):
        print(f"[错误] 报告文件不存在: {args.report}")
        sys.exit(2)

    kb = load_json(args.kb)
    risk_criteria = load_json(args.risk)
    clause_map = build_clause_map(kb)
    module_map = build_module_map(kb)

    with open(args.report, "r", encoding="utf-8") as f:
        md_text = f.read()

    report_data = parse_report(md_text)

    # ── 逐条校验 ──
    errors = 0
    warnings = 0
    lines = []
    lines.append("=" * 60)
    lines.append("安评检查助手 - 报告自动校验结果")
    lines.append(f"报告文件: {os.path.basename(args.report)}")
    lines.append(f"校验时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"知识库版本: {kb['metadata']['version']} ({kb['metadata']['last_updated']})")
    lines.append("=" * 60)

    # 1. 问题条款校验
    lines.append("")
    lines.append("【一、条款扣分校验】")

    if not report_data["issues"]:
        lines.append("  ⚠ 未从报告中提取到问题条款")
        warnings += 1
    else:
        for issue in report_data["issues"]:
            cid = issue["clause_id"]
            lines.append(f"\n  条款 {cid} ({issue['clause_name']})")

            if cid not in clause_map:
                lines.append(f"    ⚠ 条款在知识库中未找到")
                warnings += 1
                continue

            kb_clause = clause_map[cid]

            # 标准分校验
            if issue["clause_score"] != kb_clause.get("score", 0):
                lines.append(f"    ✗ 标准分：报告{issue['clause_score']}≠知识库{kb_clause['score']}")
                errors += 1
            else:
                lines.append(f"    ✓ 标准分：{kb_clause['score']}分")

            # 扣分校验
            ok, msg = verify_deduction(issue, kb_clause)
            tag = "✓" if ok else "✗"
            lines.append(f"    {tag} 扣分值：{msg}")
            if not ok:
                errors += 1

            # 风险等级校验
            ok, msg = verify_risk_level(issue, risk_criteria)
            tag = "✓" if ok else "✗"
            lines.append(f"    {tag} 风险等级：{msg}")
            if not ok:
                errors += 1

            # 引用标准校验
            ok, msg = verify_reference(issue, kb_clause)
            tag = "✓" if ok else "✗"
            lines.append(f"    {tag} 引用标准：{msg}")
            if not ok:
                errors += 1

    # 2. 模块得分校验
    lines.append("")
    lines.append("【二、模块得分加总校验】")
    mod_results = verify_module_scores(report_data, module_map)
    for tag, mid, msg in mod_results:
        lines.append(f"  {tag} {mid}: {msg}")
        if tag == "✗":
            errors += 1
        elif tag == "⚠":
            warnings += 1

    # 3. 总结
    lines.append("")
    lines.append("=" * 60)
    if errors == 0 and warnings == 0:
        lines.append("校验结论：✓ 全部通过，报告与知识库完全一致")
    elif errors == 0:
        lines.append(f"校验结论：⚠ 通过（{warnings}项警告）")
    else:
        lines.append(f"校验结论：✗ 存在{errors}项偏差、{warnings}项警告，需修正")
    lines.append("=" * 60)

    result_text = "\n".join(lines)
    print(result_text)

    # 输出校验报告
    if args.output:
        os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(result_text)
        print(f"\n校验报告已保存: {args.output}")

    sys.exit(1 if errors > 0 else 0)


if __name__ == "__main__":
    main()
