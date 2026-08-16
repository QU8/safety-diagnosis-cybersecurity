#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
安评检查助手 - 差异检测工具

用于快速对比两份报告的差异，识别结构、内容、风险等级、
扣分值等方面的不一致之处。
"""

import json
from typing import Dict, List, Any, Tuple
from difflib import unified_diff


class DiffDetector:
    """差异检测器"""
    
    def __init__(self):
        self.diff_types = [
            "structure_diff",      # 结构差异
            "content_diff",        # 内容差异
            "score_diff",          # 扣分差异
            "risk_level_diff",     # 风险等级差异
            "phrasing_diff",       # 措辞差异
            "module_diff"          # 模块差异
        ]
    
    def compare_reports(self, report1: Dict[str, Any], report2: Dict[str, Any], verbose: bool = True) -> Dict[str, Any]:
        """
        对比两份报告的差异
        
        Args:
            report1: 报告1（原始报告）
            report2: 报告2（对比报告）
            verbose: 是否输出详细信息
            
        Returns:
            差异信息字典
        """
        differences = {diff_type: [] for diff_type in self.diff_types}
        
        # 1. 对比总体结构
        self._compare_structure(report1, report2, differences)
        
        # 2. 对比模块信息
        self._compare_modules(report1, report2, differences)
        
        # 3. 对比问题详情
        self._compare_problems(report1, report2, differences)
        
        # 4. 对比扣分统计
        self._compare_statistics(report1, report2, differences)
        
        # 5. 对比评价结论
        self._compare_conclusion(report1, report2, differences)
        
        # 输出结果
        if verbose:
            self._print_differences(differences)
        
        return differences
    
    def _compare_structure(self, report1: Dict[str, Any], report2: Dict[str, Any], differences: Dict[str, List]):
        """对比报告结构"""
        
        # 检查关键字段是否存在
        key_fields = ["basic_info", "summary", "problems", "statistics", "rectification", "conclusion"]
        
        for field in key_fields:
            exists1 = field in report1
            exists2 = field in report2
            
            if exists1 != exists2:
                differences["structure_diff"].append(
                    f"字段'{field}'存在性不一致: report1={exists1}, report2={exists2}"
                )
    
    def _compare_modules(self, report1: Dict[str, Any], report2: Dict[str, Any], differences: Dict[str, List]):
        """对比模块信息"""
        
        modules1 = report1.get("modules", [])
        modules2 = report2.get("modules", [])
        
        # 对比模块数量
        if len(modules1) != len(modules2):
            differences["module_diff"].append(
                f"模块数量不一致: {len(modules1)} vs {len(modules2)}"
            )
        
        # 对比每个模块的得分
        module_names1 = {m["name"]: m for m in modules1}
        module_names2 = {m["name"]: m for m in modules2}
        
        all_modules = set(module_names1.keys()) | set(module_names2.keys())
        
        for module_name in sorted(all_modules):
            mod1 = module_names1.get(module_name, {})
            mod2 = module_names2.get(module_name, {})
            
            # 对比满分
            if mod1.get("score") != mod2.get("score"):
                differences["score_diff"].append(
                    f"模块'{module_name}'满分不一致: {mod1.get('score')} vs {mod2.get('score')}"
                )
            
            # 对比实得分
            if mod1.get("actual_score") != mod2.get("actual_score"):
                differences["score_diff"].append(
                    f"模块'{module_name}'实得分不一致: {mod1.get('actual_score')} vs {mod2.get('actual_score')}"
                )
            
            # 对比扣分
            if mod1.get("deduction") != mod2.get("deduction"):
                differences["score_diff"].append(
                    f"模块'{module_name}'扣分不一致: {mod1.get('deduction')} vs {mod2.get('deduction')}"
                )
    
    def _compare_problems(self, report1: Dict[str, Any], report2: Dict[str, Any], differences: Dict[str, List]):
        """对比问题详情"""
        
        problems1 = report1.get("problems", [])
        problems2 = report2.get("problems", [])
        
        # 对比问题数量
        if len(problems1) != len(problems2):
            differences["structure_diff"].append(
                f"问题数量不一致: {len(problems1)} vs {len(problems2)}"
            )
        
        # 逐个对比问题
        max_len = max(len(problems1), len(problems2))
        
        for i in range(max_len):
            seq = i + 1
            p1 = problems1[i] if i < len(problems1) else {}
            p2 = problems2[i] if i < len(problems2) else {}
            
            # 对比问题描述
            if p1.get("description") != p2.get("description"):
                differences["content_diff"].append(
                    f"问题{seq}描述不一致: '{p1.get('description')}' vs '{p2.get('description')}'"
                )
            
            # 对比关联条款
            if p1.get("clause_id") != p2.get("clause_id"):
                differences["content_diff"].append(
                    f"问题{seq}关联条款不一致: {p1.get('clause_id')} vs {p2.get('clause_id')}"
                )
            
            # 对比扣分值
            if p1.get("deduction") != p2.get("deduction"):
                differences["score_diff"].append(
                    f"问题{seq}扣分值不一致: {p1.get('deduction')} vs {p2.get('deduction')}"
                )
            
            # 对比风险等级
            if p1.get("risk_level") != p2.get("risk_level"):
                differences["risk_level_diff"].append(
                    f"问题{seq}风险等级不一致: {p1.get('risk_level')} vs {p2.get('risk_level')}"
                )
            
            # 对比扣分理由
            if p1.get("deduction_reason") != p2.get("deduction_reason"):
                differences["phrasing_diff"].append(
                    f"问题{seq}扣分理由不一致"
                )
                # 如果详细输出，显示具体差异
                if p1.get("deduction_reason") and p2.get("deduction_reason"):
                    diff_text = self._get_text_diff(
                        p1.get("deduction_reason"),
                        p2.get("deduction_reason"),
                        prefix1="问题{}理由1".format(seq),
                        prefix2="问题{}理由2".format(seq)
                    )
                    differences["phrasing_diff"].append(diff_text)
            
            # 对比整改建议
            if p1.get("rectification") != p2.get("rectification"):
                differences["phrasing_diff"].append(
                    f"问题{seq}整改建议不一致"
                )
                if p1.get("rectification") and p2.get("rectification"):
                    diff_text = self._get_text_diff(
                        p1.get("rectification"),
                        p2.get("rectification"),
                        prefix1="问题{}整改1".format(seq),
                        prefix2="问题{}整改2".format(seq)
                    )
                    differences["phrasing_diff"].append(diff_text)
            
            # 对比依据原文
            if p1.get("reference") != p2.get("reference"):
                differences["content_diff"].append(
                    f"问题{seq}依据原文不一致"
                )
    
    def _compare_statistics(self, report1: Dict[str, Any], report2: Dict[str, Any], differences: Dict[str, List]):
        """对比扣分统计"""
        
        stats1 = report1.get("statistics", {})
        stats2 = report2.get("statistics", {})
        
        # 对比各风险等级的数量和扣分
        risk_levels = ["high", "medium", "low"]
        
        for risk_level in risk_levels:
            # 对比问题数量
            count1 = stats1.get(f"{risk_level}_count", 0)
            count2 = stats2.get(f"{risk_level}_count", 0)
            
            if count1 != count2:
                differences["risk_level_diff"].append(
                    f"{risk_level}风险问题数量不一致: {count1} vs {count2}"
                )
            
            # 对比扣分合计
            score1 = stats1.get(f"{risk_level}_score", 0)
            score2 = stats2.get(f"{risk_level}_score", 0)
            
            if score1 != score2:
                differences["score_diff"].append(
                    f"{risk_level}风险扣分合计不一致: {score1} vs {score2}"
                )
        
        # 对比总计
        total_count1 = stats1.get("total_count", 0)
        total_count2 = stats2.get("total_count", 0)
        
        if total_count1 != total_count2:
            differences["risk_level_diff"].append(
                f"总问题数量不一致: {total_count1} vs {total_count2}"
            )
        
        total_deduction1 = stats1.get("total_deduction", 0)
        total_deduction2 = stats2.get("total_deduction", 0)
        
        if total_deduction1 != total_deduction2:
            differences["score_diff"].append(
                f"总扣分不一致: {total_deduction1} vs {total_deduction2}"
            )
    
    def _compare_conclusion(self, report1: Dict[str, Any], report2: Dict[str, Any], differences: Dict[str, List]):
        """对比评价结论"""
        
        conclusion1 = report1.get("conclusion", "")
        conclusion2 = report2.get("conclusion", "")
        
        if conclusion1 != conclusion2:
            differences["content_diff"].append(
                f"评价结论不一致: '{conclusion1}' vs '{conclusion2}'"
            )
            
            # 显示文本差异
            diff_text = self._get_text_diff(
                conclusion1,
                conclusion2,
                prefix1="结论1",
                prefix2="结论2"
            )
            differences["phrasing_diff"].append(diff_text)
        
        # 对比总体得分
        total_score1 = report1.get("total_score", 0)
        total_score2 = report2.get("total_score", 0)
        
        if total_score1 != total_score2:
            differences["score_diff"].append(
                f"总体得分不一致: {total_score1} vs {total_score2}"
            )
    
    def _get_text_diff(self, text1: str, text2: str, prefix1: str = "text1", prefix2: str = "text2") -> str:
        """
        获取文本差异
        
        Args:
            text1: 文本1
            text2: 文本2
            prefix1: 文本1前缀
            prefix2: 文本2前缀
            
        Returns:
            差异文本
        """
        diff_lines = list(unified_diff(
            text1.splitlines(keepends=True),
            text2.splitlines(keepends=True),
            fromfile=prefix1,
            tofile=prefix2,
            lineterm=""
        ))
        
        return "\n".join(diff_lines)
    
    def _print_differences(self, differences: Dict[str, List]):
        """打印差异信息"""
        
        print("\n" + "="*60)
        print("差异检测报告")
        print("="*60 + "\n")
        
        has_differences = False
        
        for diff_type, diff_list in differences.items():
            if diff_list:
                has_differences = True
                
                type_names = {
                    "structure_diff": "结构差异",
                    "content_diff": "内容差异",
                    "score_diff": "扣分差异",
                    "risk_level_diff": "风险等级差异",
                    "phrasing_diff": "措辞差异",
                    "module_diff": "模块差异"
                }
                
                print(f"【{type_names.get(diff_type, diff_type)}】({len(diff_list)}项)")
                print("-" * 60)
                
                for idx, diff in enumerate(diff_list, 1):
                    print(f"{idx}. {diff}")
                
                print()
        
        if not has_differences:
            print("✓ 未检测到任何差异，两份报告完全一致！\n")
        else:
            print("⚠ 检测到差异，请仔细查看上述内容。\n")
    
    def compare_markdown_files(self, file1: str, file2: str) -> Dict[str, Any]:
        """
        对比两个Markdown报告文件
        
        Args:
            file1: 报告文件1路径
            file2: 报告文件2路径
            
        Returns:
            差异信息字典
        """
        try:
            # 读取文件
            with open(file1, 'r', encoding='utf-8') as f:
                content1 = f.read()
            
            with open(file2, 'r', encoding='utf-8') as f:
                content2 = f.read()
            
            # 转换为报告字典（简化处理，实际可能需要解析Markdown）
            report1 = {
                "content": content1,
                "line_count": len(content1.splitlines()),
                "char_count": len(content1)
            }
            
            report2 = {
                "content": content2,
                "line_count": len(content2.splitlines()),
                "char_count": len(content2)
            }
            
            differences = {
                "structure_diff": [],
                "content_diff": [],
                "score_diff": [],
                "risk_level_diff": [],
                "phrasing_diff": [],
                "module_diff": []
            }
            
            # 对比行数
            if report1["line_count"] != report2["line_count"]:
                differences["structure_diff"].append(
                    f"文件行数不一致: {report1['line_count']} vs {report2['line_count']}"
                )
            
            # 对比字符数
            if report1["char_count"] != report2["char_count"]:
                differences["content_diff"].append(
                    f"文件字符数不一致: {report1['char_count']} vs {report2['char_count']}"
                )
            
            # 显示文本差异
            diff_text = self._get_text_diff(
                content1,
                content2,
                prefix1=file1,
                prefix2=file2
            )
            
            if diff_text:
                differences["content_diff"].append("文本内容差异：\n" + diff_text)
            
            # 输出结果
            self._print_differences(differences)
            
            return differences
        
        except Exception as e:
            print(f"对比文件失败: {str(e)}")
            return {}


def main():
    """主函数 - 演示如何使用差异检测工具"""
    
    print("智能细则匹配与评价报告生成器 - 差异检测工具\n")
    
    # 创建检测器实例
    detector = DiffDetector()
    
    # 模拟两份报告
    report1 = {
        "modules": [
            {"name": "公共规范", "score": 130, "actual_score": 120, "deduction": 10},
            {"name": "机房安全", "score": 100, "actual_score": 95, "deduction": 5}
        ],
        "problems": [
            {
                "description": "安全设备台账不符，缺少位置和接入日期",
                "clause_id": "2.7.4.1.1",
                "deduction": 5,
                "risk_level": "高",
                "deduction_reason": "根据细则条款要求，安全设备台账应包含责任部门、重要程度、所处位置、品牌型号、接入日期等信息，但实际情况部分信息缺失，扣除5分。",
                "rectification": "[立即整改] 完善安全设备台账信息，确保位置、接入日期等信息完整准确，并建立长效机制防止复发。"
            }
        ],
        "statistics": {
            "high_count": 1,
            "high_score": 5,
            "medium_count": 0,
            "medium_score": 0,
            "low_count": 0,
            "low_score": 0,
            "total_count": 1,
            "total_deduction": 5
        },
        "total_score": 595,
        "conclusion": "本次评价总体表现优秀，大部分安全管理措施落实到位，网络安全防护体系较为完善，建议继续保持并持续改进。"
    }
    
    report2 = {
        "modules": [
            {"name": "公共规范", "score": 130, "actual_score": 120, "deduction": 10},
            {"name": "机房安全", "score": 100, "actual_score": 95, "deduction": 5}
        ],
        "problems": [
            {
                "description": "安全设备台账不符，缺少位置和接入日期",
                "clause_id": "2.7.4.1.1",
                "deduction": 5,
                "risk_level": "高",
                "deduction_reason": "根据细则条款要求，安全设备台账应包含责任部门、重要程度、所处位置、品牌型号、接入日期等信息，但实际情况部分信息缺失，扣除5分。",
                "rectification": "[立即整改] 完善安全设备台账信息，确保位置、接入日期等信息完整准确，并建立长效机制防止复发。"
            }
        ],
        "statistics": {
            "high_count": 1,
            "high_score": 5,
            "medium_count": 0,
            "medium_score": 0,
            "low_count": 0,
            "low_score": 0,
            "total_count": 1,
            "total_deduction": 5
        },
        "total_score": 595,
        "conclusion": "本次评价总体表现优秀，大部分安全管理措施落实到位，网络安全防护体系较为完善，建议继续保持并持续改进。"
    }
    
    # 执行对比
    differences = detector.compare_reports(report1, report2)
    
    print("\n检测完成！")


if __name__ == "__main__":
    main()
