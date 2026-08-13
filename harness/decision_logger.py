"""
决策日志模块
记录 AI 评审的每个决策，包括决策理由和证据
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


class DecisionLogger:
    """决策日志记录器"""
    
    def __init__(self, storage_dir: str = "data/decisions"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.current_scan_id = None
        self.decisions = []
    
    def start_scan(self, repo: str, workflow: str, total_issues: int) -> str:
        """开始新的扫描会话"""
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        self.current_scan_id = timestamp
        self.decisions = []
        
        self.scan_metadata = {
            "scan_id": timestamp,
            "timestamp": datetime.now().isoformat(),
            "repo": repo,
            "workflow": workflow,
            "total_issues": total_issues,
        }
        
        return timestamp
    
    def log_decision(
        self,
        issue_id: str,
        rule_id: str,
        file: str,
        line: int,
        severity: str,
        original_message: str,
        ai_action: str,
        ai_confidence: float,
        ai_reasoning: str,
        ai_evidence: Optional[List[str]] = None,
    ):
        """记录一个 AI 决策"""
        decision = {
            "issue_id": issue_id,
            "rule_id": rule_id,
            "file": file,
            "line": line,
            "severity": severity,
            "original_message": original_message,
            "ai_action": ai_action,
            "ai_confidence": ai_confidence,
            "ai_reasoning": ai_reasoning,
            "ai_evidence": ai_evidence or [],
            "user_verdict": None,
            "user_comment": None,
            "verdict_at": None,
        }
        self.decisions.append(decision)
    
    def update_decision(
        self,
        issue_id: str,
        ai_action: Optional[str] = None,
        ai_confidence: Optional[float] = None,
        ai_reasoning: Optional[str] = None,
    ) -> bool:
        """
        更新指定 issue_id 的决策日志条目（P1 修复 3: review_merger 同步覆写）

        Args:
            issue_id: 问题 ID
            ai_action: 新的 ai_action
            ai_confidence: 新的 ai_confidence
            ai_reasoning: 新的 ai_reasoning

        Returns:
            True 如果成功更新，False 如果未找到
        """
        for d in self.decisions:
            if d.get("issue_id") == issue_id:
                if ai_action is not None:
                    d["ai_action"] = ai_action
                if ai_confidence is not None:
                    d["ai_confidence"] = ai_confidence
                if ai_reasoning is not None:
                    d["ai_reasoning"] = ai_reasoning
                # 记录更新时间
                d["updated_at"] = datetime.now().isoformat()
                return True
        return False

    def save(self):
        """保存决策日志到文件"""
        if not self.current_scan_id:
            raise ValueError("No scan session started. Call start_scan() first.")
        
        filename = f"{self.current_scan_id}.json"
        filepath = self.storage_dir / filename
        
        data = {
            **self.scan_metadata,
            "decisions": self.decisions,
        }
        
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        return filepath
    
    def load(self, scan_id: str) -> Dict:
        """加载指定扫描的决策日志"""
        filepath = self.storage_dir / f"{scan_id}.json"
        if not filepath.exists():
            raise FileNotFoundError(f"Decision log not found: {scan_id}")
        
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    
    def list_scans(self) -> List[str]:
        """列出所有扫描会话"""
        scans = []
        for f in self.storage_dir.glob("*.json"):
            scans.append(f.stem)
        return sorted(scans, reverse=True)
