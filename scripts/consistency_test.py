#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
安评检查助手 - 一致性测试工具

用于验证报告输出的一致性，确保多次生成相同输入时，报告结构、
措辞、风险等级保持高度一致（≥95%相似度）。
"""

import json
import hashlib
from typing import Dict, List, Any
from datetime import datetime
from difflib import SequenceMatcher


class ConsistencyTester:
    """一致性测试器"""
    
    def __init__(self):
        self.test_cases = [
            "安全设备台账不符，缺少位置和接入日期，没有制定备份及恢复策略",
            "机房温湿度控制不当，空调运转异常，未开展网络安全应急演练",
            "配电箱未上锁，临时线缆敷设混乱，员工未佩戴安全帽"
        ]
    
    def calculate_similarity(self, str1: str, str2: str) -> float:
        """
        计算两个字符串的相似度
        
        Args:
            str1: 字符串1
            str2: 字符串2
            
        Returns:
            相似度（0-1之间的小数）
        """
        return SequenceMatcher(None, str1, str2).ratio()
    
    def calculate_report_hash(self, report: Dict[str, Any]) -> str:
        """
        计算报告的哈希值（用于一致性检测）
        
        Args:
            report: 报告字典
            
        Returns:
            MD5哈希值
        """
        # 将报告转换为标准化的JSON字符串（排序key，确保ASCII）
        report_str = json.dumps(
            report, 
            sort_keys=True, 
            ensure_ascii=False,
            indent=2
        )
        return hashlib.md5(report_str.encode('utf-8')).hexdigest()
    
    def analyze_structure(self, report: Dict[str, Any]) -> Dict[str, Any]:
        """
        分析报告结构
        
        Args:
            report: 报告字典
            
        Returns:
            结构信息字典
        """
        return {
            "has_basic_info": "基本信息" in str(report),
            "has_summary": "评价结果概览" in str(report),
            "has_problems": "问题详情" in str(report),
            "has_statistics": "扣分统计" in str(report),
            "has_rectification": "整改建议汇总" in str(report),
            "has_conclusion": "评价结论" in str(report),
            "problem_count": len(report.get("problems", [])),
            "module_count": len(report.get("modules", []))
        }
    
    def compare_reports(self, report1: Dict[str, Any], report2: Dict[str, Any]) -> Dict[str, Any]:
        """
        对比两份报告的差异
        
        Args:
            report1: 报告1
            report2: 报告2
            
        Returns:
            差异信息字典
        """
        differences = {
            "structure_diff": [],
            "content_diff": [],
            "score_diff": [],
            "risk_level_diff": [],
            "phrasing_diff": []
        }
        
        # 对比结构
        struct1 = self.analyze_structure(report1)
        struct2 = self.analyze_structure(report2)
        
        for key in struct1:
            if struct1[key] != struct2[key]:
                differences["structure_diff"].append(
                    f"{key}不一致: {struct1[key]} vs {struct2[key]}"
                )
        
        # 对比问题详情
        problems1 = report1.get("problems", [])
        problems2 = report2.get("problems", [])
        
        if len(problems1) != len(problems2):
            differences["structure_diff"].append(
                f"问题数量不一致: {len(problems1)} vs {len(problems2)}"
            )
        
        for i, (p1, p2) in enumerate(zip(problems1, problems2)):
            seq = i + 1
            # 对比扣分理由
            if p1.get("deduction_reason") != p2.get("deduction_reason"):
                differences["content_diff"].append(
                    f"问题{seq}扣分理由不一致"
                )
                differences["phrasing_diff"].append(
                    f"问题{seq}: '{p1.get('deduction_reason')}' vs '{p2.get('deduction_reason')}'"
                )
            
            # 对比风险等级
            if p1.get("risk_level") != p2.get("risk_level"):
                differences["risk_level_diff"].append(
                    f"问题{seq}风险等级不一致: {p1.get('risk_level')} vs {p2.get('risk_level')}"
                )
            
            # 对比扣分值
            if p1.get("deduction") != p2.get("deduction"):
                differences["score_diff"].append(
                    f"问题{seq}扣分值不一致: {p1.get('deduction')} vs {p2.get('deduction')}"
                )
            
            # 对比整改建议
            if p1.get("rectification") != p2.get("rectification"):
                differences["content_diff"].append(
                    f"问题{seq}整改建议不一致"
                )
                differences["phrasing_diff"].append(
                    f"问题{seq}整改: '{p1.get('rectification')}' vs '{p2.get('rectification')}'"
                )
        
        # 对比总体得分
        if report1.get("total_score") != report2.get("total_score"):
            differences["score_diff"].append(
                f"总体得分不一致: {report1.get('total_score')} vs {report2.get('total_score')}"
            )
        
        # 对比评价结论
        if report1.get("conclusion") != report2.get("conclusion"):
            differences["content_diff"].append(
                f"评价结论不一致: '{report1.get('conclusion')}' vs '{report2.get('conclusion')}'"
            )
        
        return differences
    
    def test_consistency(self, generate_report_func, test_iterations: int = 10) -> Dict[str, Any]:
        """
        执行一致性测试
        
        Args:
            generate_report_func: 报告生成函数
            test_iterations: 测试迭代次数
            
        Returns:
            测试结果字典
        """
        print(f"{'='*60}")
        print(f"开始一致性测试（迭代次数：{test_iterations}）")
        print(f"{'='*60}\n")
        
        results = {
            "test_cases": [],
            "overall_similarity": 0.0,
            "hash_consistency": False,
            "passed": False
        }
        
        for idx, test_case in enumerate(self.test_cases, 1):
            print(f"{'='*60}")
            print(f"测试用例 {idx}: {test_case}")
            print(f"{'='*60}\n")
            
            # 生成多次报告
            reports = []
            hash_values = []
            
            for i in range(test_iterations):
                try:
                    report = generate_report_func(test_case)
                    reports.append(report)
                    
                    # 计算哈希值
                    report_hash = self.calculate_report_hash(report)
                    hash_values.append(report_hash)
                    
                    print(f"  迭代 {i+1}: 哈希值 = {report_hash[:16]}...")
                
                except Exception as e:
                    print(f"  迭代 {i+1}: 生成失败 - {str(e)}")
                    continue
            
            # 分析哈希一致性
            unique_hashes = list(set(hash_values))
            hash_consistency_rate = (test_iterations - len(unique_hashes) + 1) / test_iterations
            
            print(f"\n  哈希值一致性分析：")
            print(f"    - 唯一哈希数量: {len(unique_hashes)}")
            print(f"    - 一致性比例: {hash_consistency_rate*100:.1f}%")
            
            if len(unique_hashes) == 1:
                print(f"    ✓ 报告完全一致")
                hash_status = "完全一致"
            elif len(unique_hashes) <= 2:
                print(f"    ⚠ 报告基本一致（{len(unique_hashes)}种变体）")
                hash_status = "基本一致"
            else:
                print(f"    ✗ 报告差异较大（{len(unique_hashes)}种变体）")
                hash_status = "差异较大"
            
            # 对比报告差异
            if len(reports) >= 2:
                differences = self.compare_reports(reports[0], reports[-1])
                
                print(f"\n  差异分析：")
                if differences["structure_diff"]:
                    print(f"    结构差异 ({len(differences['structure_diff'])}):")
                    for diff in differences["structure_diff"]:
                        print(f"      - {diff}")
                else:
                    print(f"    ✓ 结构一致")
                
                if differences["content_diff"]:
                    print(f"    内容差异 ({len(differences['content_diff'])}):")
                    for diff in differences["content_diff"]:
                        print(f"      - {diff}")
                else:
                    print(f"    ✓ 内容一致")
                
                if differences["risk_level_diff"]:
                    print(f"    风险等级差异 ({len(differences['risk_level_diff'])}):")
                    for diff in differences["risk_level_diff"]:
                        print(f"      - {diff}")
                else:
                    print(f"    ✓ 风险等级一致")
                
                if differences["score_diff"]:
                    print(f"    扣分差异 ({len(differences['score_diff'])}):")
                    for diff in differences["score_diff"]:
                        print(f"      - {diff}")
                else:
                    print(f"    ✓ 扣分一致")
            
            # 计算相似度
            if len(reports) >= 2:
                report_str1 = json.dumps(reports[0], sort_keys=True, ensure_ascii=False)
                report_str2 = json.dumps(reports[-1], sort_keys=True, ensure_ascii=False)
                similarity = self.calculate_similarity(report_str1, report_str2)
                
                print(f"\n  报告相似度: {similarity*100:.1f}%")
                
                if similarity >= 0.95:
                    print(f"    ✓ 相似度达标（≥95%）")
                    similarity_status = "优秀"
                elif similarity >= 0.90:
                    print(f"    ⚠ 相似度良好（≥90%）")
                    similarity_status = "良好"
                elif similarity >= 0.85:
                    print(f"    ⚠ 相似度一般（≥85%）")
                    similarity_status = "一般"
                else:
                    print(f"    ✗ 相似度不达标（<85%）")
                    similarity_status = "不达标"
            else:
                similarity = 0.0
                similarity_status = "无法计算"
            
            # 记录结果
            case_result = {
                "test_case": test_case,
                "hash_status": hash_status,
                "unique_hashes": len(unique_hashes),
                "similarity": similarity,
                "similarity_status": similarity_status,
                "differences": differences if len(reports) >= 2 else {}
            }
            results["test_cases"].append(case_result)
            
            print(f"\n{'='*60}\n")
        
        # 计算总体相似度
        if results["test_cases"]:
            total_similarity = sum(c["similarity"] for c in results["test_cases"])
            results["overall_similarity"] = total_similarity / len(results["test_cases"])
        
        # 判断是否通过
        results["passed"] = (
            all(c["hash_status"] in ["完全一致", "基本一致"] for c in results["test_cases"]) and
            results["overall_similarity"] >= 0.95
        )
        
        # 输出总结
        print(f"{'='*60}")
        print(f"测试总结")
        print(f"{'='*60}")
        print(f"  总体相似度: {results['overall_similarity']*100:.1f}%")
        print(f"  测试状态: {'✓ 通过' if results['passed'] else '✗ 未通过'}")
        print(f"{'='*60}\n")
        
        return results
    
    def generate_test_report(self, test_results: Dict[str, Any], output_file: str = None) -> str:
        """
        生成测试报告
        
        Args:
            test_results: 测试结果
            output_file: 输出文件路径（可选）
            
        Returns:
            报告内容
        """
        report_lines = [
            "# 智能细则匹配与评价报告生成器 - 一致性测试报告",
            "",
            f"**测试时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"**总体相似度**: {test_results['overall_similarity']*100:.1f}%",
            f"**测试状态**: {'通过 ✓' if test_results['passed'] else '未通过 ✗'}",
            "",
            "---",
            "",
            "## 测试详情"
        ]
        
        for idx, case in enumerate(test_results["test_cases"], 1):
            report_lines.extend([
                f"",
                f"### 测试用例 {idx}",
                f"",
                f"**问题描述**: {case['test_case']}",
                f"",
                f"- 哈希一致性: {case['hash_status']}",
                f"- 唯一哈希数: {case['unique_hashes']}",
                f"- 相似度: {case['similarity']*100:.1f}% ({case['similarity_status']})",
                f""
            ])
            
            if case.get("differences"):
                diffs = case["differences"]
                if any(diffs.values()):
                    report_lines.extend([
                        "**差异详情**:",
                        ""
                    ])
                    
                    if diffs["structure_diff"]:
                        report_lines.append("- 结构差异:")
                        for diff in diffs["structure_diff"]:
                            report_lines.append(f"  - {diff}")
                    
                    if diffs["content_diff"]:
                        report_lines.append("- 内容差异:")
                        for diff in diffs["content_diff"]:
                            report_lines.append(f"  - {diff}")
                    
                    if diffs["risk_level_diff"]:
                        report_lines.append("- 风险等级差异:")
                        for diff in diffs["risk_level_diff"]:
                            report_lines.append(f"  - {diff}")
                    
                    if diffs["score_diff"]:
                        report_lines.append("- 扣分差异:")
                        for diff in diffs["score_diff"]:
                            report_lines.append(f"  - {diff}")
                    
                    report_lines.append("")
        
        report_content = "\n".join(report_lines)
        
        # 保存到文件
        if output_file:
            try:
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(report_content)
                print(f"测试报告已保存到: {output_file}")
            except Exception as e:
                print(f"保存测试报告失败: {str(e)}")
        
        return report_content


def main():
    """主函数 - 演示如何使用一致性测试工具"""
    
    print("智能细则匹配与评价报告生成器 - 一致性测试工具\n")
    
    # 创建测试器实例
    tester = ConsistencyTester()
    
    # 模拟报告生成函数（实际使用时替换为真实的报告生成函数）
    def mock_generate_report(problem_desc: str) -> Dict[str, Any]:
        """
        模拟报告生成函数
        
        实际使用时，请替换为调用你的skill生成报告的函数
        """
        import random
        
        # 模拟一些随机性（用于测试一致性）
        random.seed(42)  # 使用固定种子确保"模拟"的一致性
        
        return {
            "problems": [
                {
                    "description": problem_desc,
                    "deduction_reason": "根据细则条款要求，应按规定执行，但实际情况不符合要求，扣除5分。",
                    "deduction": 5,
                    "risk_level": "高",
                    "rectification": "[立即整改] 具体措施，确保问题得到彻底解决，并建立长效机制防止复发。"
                }
            ],
            "total_score": 595,
            "conclusion": "本次评价总体表现优秀，大部分安全管理措施落实到位，网络安全防护体系较为完善，建议继续保持并持续改进。"
        }
    
    # 执行一致性测试
    test_results = tester.test_consistency(
        generate_report_func=mock_generate_report,
        test_iterations=10
    )
    
    # 生成测试报告
    report_file = f"reports/一致性测试报告_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    tester.generate_test_report(test_results, output_file=report_file)
    
    print("\n测试完成！")


if __name__ == "__main__":
    main()
