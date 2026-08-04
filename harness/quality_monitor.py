"""
质量监控模块
统计 AI 评审的质量指标
"""

import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List

from .decision_logger import DecisionLogger
from .feedback_manager import FeedbackManager


class QualityMonitor:
    """质量监控器"""
    
    def __init__(
        self,
        decision_logger: DecisionLogger,
        feedback_manager: FeedbackManager,
        cache_file: str = "data/stats_cache.json",
    ):
        self.decision_logger = decision_logger
        self.feedback_manager = feedback_manager
        self.cache_file = Path(cache_file)
        self.cache_file.parent.mkdir(parents=True, exist_ok=True)
    
    def calculate_accuracy(self, scan_id: str = None) -> Dict:
        """
        计算 AI 评审准确率
        
        Args:
            scan_id: 指定扫描会话 ID，如果为 None 则计算所有扫描
        
        Returns:
            准确率统计信息
        """
        if scan_id:
            # 计算指定扫描的准确率
            decisions_data = self.decision_logger.load(scan_id)
            decisions = decisions_data.get("decisions", [])
            feedbacks = self.feedback_manager.get_feedbacks_for_scan(scan_id)
        else:
            # 计算所有扫描的准确率
            decisions = []
            for sid in self.decision_logger.list_scans():
                data = self.decision_logger.load(sid)
                decisions.extend(data.get("decisions", []))
            feedbacks = self.feedback_manager.get_all_feedbacks()
        
        # 统计有反馈的决策
        feedback_map = {f["issue_id"]: f for f in feedbacks}
        
        total_with_feedback = 0
        correct_count = 0
        incorrect_count = 0
        
        for decision in decisions:
            issue_id = decision["issue_id"]
            if issue_id in feedback_map:
                total_with_feedback += 1
                feedback = feedback_map[issue_id]
                
                # AI 判断为 keep，用户确认 → 正确
                # AI 判断为 filter，用户确认为 false_positive → 正确
                if decision["ai_action"] == "keep" and feedback["verdict"] == "confirmed":
                    correct_count += 1
                elif decision["ai_action"] == "filter_false_positive" and feedback["verdict"] == "false_positive":
                    correct_count += 1
                else:
                    incorrect_count += 1
        
        accuracy = correct_count / total_with_feedback if total_with_feedback > 0 else 0.0
        
        return {
            "total_decisions": len(decisions),
            "total_feedbacks": len(feedbacks),
            "total_with_feedback": total_with_feedback,
            "correct": correct_count,
            "incorrect": incorrect_count,
            "accuracy": accuracy,
        }
    
    def calculate_accuracy_by_rule(self) -> Dict[str, Dict]:
        """按规则计算准确率"""
        rule_stats = defaultdict(lambda: {"total": 0, "correct": 0, "incorrect": 0})
        
        for scan_id in self.decision_logger.list_scans():
            decisions_data = self.decision_logger.load(scan_id)
            decisions = decisions_data.get("decisions", [])
            feedbacks = self.feedback_manager.get_feedbacks_for_scan(scan_id)
            
            feedback_map = {f["issue_id"]: f for f in feedbacks}
            
            for decision in decisions:
                issue_id = decision["issue_id"]
                rule_id = decision["rule_id"]
                
                if issue_id in feedback_map:
                    rule_stats[rule_id]["total"] += 1
                    feedback = feedback_map[issue_id]
                    
                    if decision["ai_action"] == "keep" and feedback["verdict"] == "confirmed":
                        rule_stats[rule_id]["correct"] += 1
                    elif decision["ai_action"] == "filter_false_positive" and feedback["verdict"] == "false_positive":
                        rule_stats[rule_id]["correct"] += 1
                    else:
                        rule_stats[rule_id]["incorrect"] += 1
        
        # 计算每个规则的准确率
        result = {}
        for rule_id, stats in rule_stats.items():
            accuracy = stats["correct"] / stats["total"] if stats["total"] > 0 else 0.0
            result[rule_id] = {
                "total": stats["total"],
                "correct": stats["correct"],
                "incorrect": stats["incorrect"],
                "accuracy": accuracy,
            }
        
        return result
    
    def generate_report(self) -> str:
        """生成质量报告"""
        overall = self.calculate_accuracy()
        by_rule = self.calculate_accuracy_by_rule()
        
        report = []
        report.append("=" * 60)
        report.append("AI 评审质量统计报告")
        report.append("=" * 60)
        report.append("")
        
        report.append("总体统计:")
        report.append(f"  总决策数: {overall['total_decisions']}")
        report.append(f"  总反馈数: {overall['total_feedbacks']}")
        report.append(f"  有反馈的决策: {overall['total_with_feedback']}")
        report.append(f"  正确判断: {overall['correct']}")
        report.append(f"  错误判断: {overall['incorrect']}")
        report.append(f"  准确率: {overall['accuracy']:.1%}")
        report.append("")
        
        if by_rule:
            report.append("按规则统计:")
            for rule_id, stats in sorted(by_rule.items(), key=lambda x: x[1]["accuracy"]):
                report.append(f"  {rule_id}:")
                report.append(f"    准确率: {stats['accuracy']:.1%} ({stats['correct']}/{stats['total']})")
        
        return "\n".join(report)
    
    def save_cache(self):
        """保存统计缓存"""
        cache_data = {
            "generated_at": datetime.now().isoformat(),
            "overall": self.calculate_accuracy(),
            "by_rule": self.calculate_accuracy_by_rule(),
        }
        
        with open(self.cache_file, "w", encoding="utf-8") as f:
            json.dump(cache_data, f, indent=2, ensure_ascii=False)
