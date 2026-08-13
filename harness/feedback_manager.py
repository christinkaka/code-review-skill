"""
反馈管理模块
管理用户对 AI 评审结果的反馈
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


class FeedbackManager:
    """反馈管理器"""
    
    def __init__(self, storage_file: str = "data/feedbacks.json", workspace_storage_file: str = None):
        """
        初始化反馈管理器

        Args:
            storage_file: 全局存储路径（跨扫描复用）
            workspace_storage_file: workspace 存储路径（本次扫描备份）
        """
        self.storage_file = Path(storage_file)
        self.storage_file.parent.mkdir(parents=True, exist_ok=True)
        self.workspace_storage_file = Path(workspace_storage_file) if workspace_storage_file else None
        if self.workspace_storage_file:
            self.workspace_storage_file.parent.mkdir(parents=True, exist_ok=True)
        self.feedbacks = self._load()

    def sync_to_workspace(self):
        """将全局反馈同步到 workspace 备份"""
        if self.workspace_storage_file and self.workspace_storage_file != self.storage_file:
            if self.storage_file.exists():
                self.workspace_storage_file.write_text(
                    self.storage_file.read_text(encoding="utf-8"),
                    encoding="utf-8"
                )
    
    def _load(self) -> List[Dict]:
        """加载反馈数据"""
        if self.storage_file.exists():
            with open(self.storage_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("feedbacks", [])
        return []
    
    def _save(self):
        """保存反馈数据（同时写全局 + workspace）"""
        # 写全局路径
        with open(self.storage_file, "w", encoding="utf-8") as f:
            json.dump({"feedbacks": self.feedbacks}, f, indent=2, ensure_ascii=False)
        # 写 workspace 路径（如果不同）
        if self.workspace_storage_file and self.workspace_storage_file != self.storage_file:
            with open(self.workspace_storage_file, "w", encoding="utf-8") as f:
                json.dump({"feedbacks": self.feedbacks}, f, indent=2, ensure_ascii=False)
    
    def add_feedback(
        self,
        issue_id: str,
        scan_id: str,
        verdict: str,
        comment: Optional[str] = None,
    ) -> Dict:
        """
        添加用户反馈
        
        Args:
            issue_id: 问题 ID
            scan_id: 扫描会话 ID
            verdict: 裁定结果 (confirmed/false_positive/uncertain)
            comment: 用户评论
        
        Returns:
            创建的反馈记录
        """
        feedback = {
            "issue_id": issue_id,
            "scan_id": scan_id,
            "verdict": verdict,
            "comment": comment,
            "timestamp": datetime.now().isoformat(),
        }
        self.feedbacks.append(feedback)
        self._save()
        return feedback
    
    def get_feedbacks_for_scan(self, scan_id: str) -> List[Dict]:
        """获取指定扫描的所有反馈"""
        return [f for f in self.feedbacks if f["scan_id"] == scan_id]
    
    def get_feedbacks_for_issue(self, issue_id: str) -> List[Dict]:
        """获取指定问题的所有反馈"""
        return [f for f in self.feedbacks if f["issue_id"] == issue_id]
    
    def get_all_feedbacks(self) -> List[Dict]:
        """获取所有反馈"""
        return self.feedbacks
    
    def get_feedback_summary(self) -> Dict:
        """获取反馈统计摘要"""
        total = len(self.feedbacks)
        if total == 0:
            return {
                "total": 0,
                "confirmed": 0,
                "false_positive": 0,
                "uncertain": 0,
            }
        
        confirmed = sum(1 for f in self.feedbacks if f["verdict"] == "confirmed")
        false_positive = sum(1 for f in self.feedbacks if f["verdict"] == "false_positive")
        uncertain = sum(1 for f in self.feedbacks if f["verdict"] == "uncertain")
        
        return {
            "total": total,
            "confirmed": confirmed,
            "false_positive": false_positive,
            "uncertain": uncertain,
        }
