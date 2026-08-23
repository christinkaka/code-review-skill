#!/usr/bin/env python3
"""
Profile 完整性测试
确保 default profile 包含所有安全规约
"""

import glob
import sys
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

REFERENCES_DIR = Path(__file__).parent.parent / "references"


class TestDefaultProfileCompleteness:
    """验证 default profile 包含所有安全规约"""

    def _load_profile(self):
        profile_path = REFERENCES_DIR / "profiles" / "default.yaml"
        with open(profile_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    def _get_spec_paths(self, profile):
        return [s["path"] for s in profile.get("specs", [])]

    def test_deserialization_included(self):
        """default profile 必须包含 deserialization 规约"""
        profile = self._load_profile()
        paths = self._get_spec_paths(profile)
        assert "security/deserialization.md" in paths, (
            "default.yaml 缺少 security/deserialization.md"
        )

    def test_log_injection_included(self):
        """default profile 必须包含 log-injection 规约"""
        profile = self._load_profile()
        paths = self._get_spec_paths(profile)
        assert "security/log-injection.md" in paths, (
            "default.yaml 缺少 security/log-injection.md"
        )

    def test_all_security_rules_have_md(self):
        """security 目录下所有 .md 文件都应在 default profile 中"""
        profile = self._load_profile()
        paths = set(self._get_spec_paths(profile))
        security_dir = REFERENCES_DIR / "security"
        md_files = sorted(glob.glob(str(security_dir / "*.md")))
        for md_file in md_files:
            rel_path = f"security/{Path(md_file).name}"
            assert rel_path in paths, (
                f"default.yaml 缺少 {rel_path}"
            )

    def test_all_security_rules_have_yaml(self):
        """security 目录下所有规则都应有对应的 .yaml 文件"""
        security_dir = REFERENCES_DIR / "security"
        md_files = {Path(f).stem for f in glob.glob(str(security_dir / "*.md"))}
        yaml_files = {Path(f).stem for f in glob.glob(str(security_dir / "*.yaml"))}
        missing_yaml = md_files - yaml_files
        assert not missing_yaml, (
            f"以下规则缺少 .yaml 文件: {missing_yaml}"
        )
