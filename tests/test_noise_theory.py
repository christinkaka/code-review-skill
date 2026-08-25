#!/usr/bin/env python3
"""
noise_theory 数学理论验证测试

每个判据都有对应的数值断言：
1. Shannon 熵 + Miller-Madow 修正的公式正确性
2. 字符集分层假设检验
3. 贝叶斯后验公式
4. FDR / BH 保留数
5. Z-score 离群检验
6. 确定性（同输入同输出，无随机性）
"""

import math
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from noise_theory import (
    bayes_posterior,
    bh_keep_count,
    classify_charset,
    engine_agreement_posterior,
    fdr_report,
    flag_noise_rules,
    is_high_entropy_secret,
    rule_z_scores,
    shannon_entropy_bits,
)


# ===================================================================
# 1. Shannon 熵 + Miller-Madow 修正
# ===================================================================

class TestShannonEntropy:
    def test_all_same_chars_zero_entropy(self):
        """全同字符: p=1, H = -1·log2(1) = 0"""
        h, _ = shannon_entropy_bits("aaaa")
        assert h == pytest.approx(0.0)

    def test_two_equal_chars_one_bit(self):
        """'ab': p=0.5, H = 1 bit"""
        h, _ = shannon_entropy_bits("ab")
        assert h == pytest.approx(1.0)

    def test_four_distinct_chars_two_bits(self):
        """'abcd': 均匀分布 4 字符, H = log2(4) = 2 bits"""
        h, _ = shannon_entropy_bits("abcd")
        assert h == pytest.approx(2.0)

    def test_hex_alphabet_four_bits(self):
        """'0123456789abcdef': 均匀 16 字符, H = log2(16) = 4 bits"""
        h, _ = shannon_entropy_bits("0123456789abcdef")
        assert h == pytest.approx(4.0)

    def test_miller_madow_correction_formula(self):
        """Ĥ_MM = Ĥ + (K-1)/(2n·ln2) 数值验证: 'aabb' (K=2,n=4,H=1)"""
        h, h_mm = shannon_entropy_bits("aabb")
        assert h == pytest.approx(1.0)
        expected_mm = 1.0 + (2 - 1) / (2 * 4 * math.log(2))
        assert h_mm == pytest.approx(expected_mm)

    def test_miller_madow_is_upward_correction(self):
        """修正量恒非负（plug-in 低估真实熵）"""
        _, h_mm = shannon_entropy_bits("hello world foo")
        h2, _ = shannon_entropy_bits("hello world foo")
        assert h_mm >= h2

    def test_empty_string(self):
        h, h_mm = shannon_entropy_bits("")
        assert (h, h_mm) == (0.0, 0.0)


# ===================================================================
# 2. 字符集分类
# ===================================================================

class TestClassifyCharset:
    @pytest.mark.parametrize("value,expected", [
        ("deadbeef1234", "hex"),
        ("DeadBEEF99", "hex"),
        ("aB3kZ9mQ2v", "base62"),
        ("aB3+kZ9/mQ=", "base64"),
        ("sk-abc_123.XYZ", "alnum_sym"),
        ("welcome message", "natural"),      # 含空格
        (" привет мир ", "natural"),          # 非 ASCII
    ])
    def test_classification(self, value, expected):
        assert classify_charset(value) == expected

    def test_placeholder(self):
        assert classify_charset("${DB_PASSWORD}") == "placeholder"
        assert classify_charset("{{secret.value}}") != "placeholder"  # {{}}不在模板表


# ===================================================================
# 3. 熵门控（确定性假设检验）
# ===================================================================

class TestEntropyGate:
    def test_real_api_key_accepted(self):
        """真凭据: 高熵 base62/符号混合"""
        ok, detail = is_high_entropy_secret("sk-9f2kQz7mXv4bN8pL3wR6")
        assert ok, detail["reason"]
        assert detail["charset"] in ("alnum_sym", "base62")

    def test_hex_key_accepted(self):
        ok, detail = is_high_entropy_secret("4f7a2b91c8e3d5f6a0b7c9d2")
        assert ok, detail["reason"]

    def test_placeholder_rejected(self):
        ok, detail = is_high_entropy_secret("${DB_PASSWORD_PLACEHOLDER}")
        assert not ok
        assert "模板占位符" in detail["reason"]

    def test_short_value_rejected(self):
        """样本量不足，熵估计不可靠"""
        ok, detail = is_high_entropy_secret("aB3$kZ9#")
        assert not ok
        assert "样本量不足" in detail["reason"]

    def test_natural_text_rejected(self):
        """自然语言文案（含空格）非机器生成凭据"""
        ok, detail = is_high_entropy_secret("welcome to our application")
        assert not ok
        assert "自然字符集" in detail["reason"]

    def test_low_entropy_rejected(self):
        """重复模式: H=0"""
        ok, detail = is_high_entropy_secret("aaaaaaaaaaaaaaaa")
        assert not ok
        assert "单位熵不足" in detail["reason"]

    def test_weak_secret_rejected_by_total_bits(self):
        """参数覆盖验证总熵门限可独立生效"""
        ok, detail = is_high_entropy_secret("aB3kZ9mQ2vXw", min_total_bits=100)
        assert not ok
        assert "总熵不足" in detail["reason"]

    def test_deterministic(self):
        """核心性质: 同输入永远同输出（用户要求的不随机、稳定）"""
        value = "7f3kQz9mXv4bN8pL3wR6"
        r1 = is_high_entropy_secret(value)
        r2 = is_high_entropy_secret(value)
        assert r1 == r2

    # ----------------------------------------------------------
    # 结构判据（2026-08-24 spring-boot 端到端实测驱动的补充）
    # ----------------------------------------------------------

    def test_uri_path_rejected(self):
        """URI 路径（/oauth2/token）非凭据，结构判据拒绝"""
        ok, detail = is_high_entropy_secret("/oauth2/token")
        assert not ok
        assert "URI" in detail["reason"] or "路径" in detail["reason"]

    def test_url_rejected(self):
        """URL（含 ://）非凭据"""
        ok, detail = is_high_entropy_secret("https://api.example.com/v2")
        assert not ok
        assert "URL" in detail["reason"] or "URI" in detail["reason"]

    def test_http_header_name_rejected(self):
        """HTTP 头名（X-AUTH-TOKEN，大写+连字符）非凭据"""
        ok, detail = is_high_entropy_secret("X-AUTH-TOKEN")
        assert not ok
        assert "头" in detail["reason"] or "header" in detail["reason"].lower()

    def test_hyphenated_natural_words_rejected(self):
        """连字符自然词（self-contained）非凭据"""
        ok, detail = is_high_entropy_secret("self-contained")
        assert not ok
        assert "自然" in detail["reason"] or "词" in detail["reason"]

    def test_real_secret_still_accepted_with_structure_checks(self):
        """结构判据不误伤真凭据（含数字/混合大小写）"""
        for secret in (
            "sk-9f2kQz7mXv4bN8pL3wR6",   # 混合大小写+数字+符号
            "4f7a2b91c8e3d5f6a0b7c9d2",   # hex 含数字
            "AKIA5K2M9XQ3PL7R8T9WZ",       # 全大写含数字（无连字符）
        ):
            ok, detail = is_high_entropy_secret(secret)
            assert ok, f"{secret} 不应被结构判据误拒: {detail['reason']}"

    def test_decision_trace_complete(self):
        """每条判决都有可追溯依据"""
        _, detail = is_high_entropy_secret("sk-9f2kQz7mXv4bN8pL3wR6")
        for key in ("value_len", "charset", "entropy_miller_madow", "total_bits", "reason"):
            assert key in detail


# ===================================================================
# 4. 贝叶斯后验
# ===================================================================

class TestBayesPosterior:
    def test_formula(self):
        """P = LR·π/(LR·π+(1-π)): π=0.5, LR=64 -> 32/32.5"""
        assert bayes_posterior(0.5, 64) == pytest.approx(32 / 32.5, abs=1e-6)

    def test_lr_one_returns_prior(self):
        """无信息证据 LR=1: 后验等于先验"""
        assert bayes_posterior(0.3, 1.0) == pytest.approx(0.3)

    def test_prior_zero_and_one(self):
        assert bayes_posterior(0.0, 100) == 0.0
        assert bayes_posterior(1.0, 100) == 1.0

    def test_monotonic_in_lr(self):
        assert bayes_posterior(0.5, 10) < bayes_posterior(0.5, 100)

    def test_invalid_lr_raises(self):
        with pytest.raises(ValueError):
            bayes_posterior(0.5, 0)


class TestEngineAgreementPosterior:
    """LR = Π(s_i/f_i)，默认参数 ast(0.9/0.05)=18, semgrep(0.8/0.1)=8, regex(0.6/0.2)=3"""

    def test_ast_alone(self):
        assert engine_agreement_posterior(["ast"]) == pytest.approx(18 / 19, abs=1e-6)

    def test_semgrep_alone(self):
        assert engine_agreement_posterior(["semgrep"]) == pytest.approx(8 / 9, abs=1e-6)

    def test_ast_semgrep_agreement(self):
        lr = 18 * 8
        assert engine_agreement_posterior(["ast", "semgrep"]) == pytest.approx(
            lr / (lr + 1), abs=1e-6
        )

    def test_three_engines(self):
        lr = 18 * 8 * 3
        assert engine_agreement_posterior(["ast", "semgrep", "regex"]) == pytest.approx(
            lr / (lr + 1), abs=1e-6
        )

    def test_unknown_engine_no_evidence(self):
        """未知引擎 LR 贡献为 1，后验回到先验"""
        assert engine_agreement_posterior(["mystery"]) == pytest.approx(0.5)

    def test_custom_params(self):
        params = {"x": {"sensitivity": 0.9, "false_alarm": 0.1}}
        assert engine_agreement_posterior(["x"], engine_params=params) == pytest.approx(9 / 10)

    def test_more_engines_higher_posterior(self):
        one = engine_agreement_posterior(["semgrep"])
        two = engine_agreement_posterior(["ast", "semgrep"])
        assert two > one


# ===================================================================
# 5. FDR / BH 保留数
# ===================================================================

class TestFDRReport:
    def test_empty(self):
        assert fdr_report([]) == {"n": 0, "expected_fp": 0.0, "expected_fdr": 0.0}

    def test_perfect_confidence(self):
        r = fdr_report([1.0, 1.0])
        assert r["expected_fp"] == 0.0
        assert r["expected_fdr"] == 0.0

    def test_mixed(self):
        """E[FP] = Σ(1-p) = 0.1+0.2 = 0.3, E[FDR] = 0.3/2"""
        r = fdr_report([0.9, 0.8])
        assert r["expected_fp"] == pytest.approx(0.3)
        assert r["expected_fdr"] == pytest.approx(0.15)


class TestBHKeepCount:
    def test_all_high_confidence_kept(self):
        assert bh_keep_count([0.99, 0.99, 0.99], q=0.1) == 3

    def test_low_confidence_truncated(self):
        """[0.99, 0.98, 0.5], q=0.1: k=2 时 Σ(1-p)/k=0.03/2=0.015<=0.1;
        k=3 时 0.53/3>0.1 -> 保留 2"""
        assert bh_keep_count([0.5, 0.99, 0.98], q=0.1) == 2

    def test_empty(self):
        assert bh_keep_count([]) == 0


# ===================================================================
# 6. Z-score 离群检验
# ===================================================================

class TestRuleZScores:
    def test_outlier_detected(self):
        counts = {f"rule_{i}": 10 + i for i in range(10)}
        counts["noisy_rule"] = 500
        flagged = flag_noise_rules(counts, threshold=2.0)
        assert "noisy_rule" in flagged
        assert flagged[0] == "noisy_rule"

    def test_no_outlier_when_uniform(self):
        counts = {f"rule_{i}": 10 for i in range(10)}
        assert flag_noise_rules(counts) == []

    def test_insufficient_rules(self):
        assert rule_z_scores({"a": 1, "b": 2}) == {}

    def test_z_score_value(self):
        """z = (x-μ)/σ 数值验证"""
        counts = {"a": 0, "b": 0, "c": 0, "d": 4}
        z = rule_z_scores(counts)
        # μ=1, σ=sqrt(3), z_d = 3/sqrt(3)=sqrt(3)
        assert z["d"] == pytest.approx(math.sqrt(3), abs=1e-3)


# ===================================================================
# 7. 集成：RuleEngine 使用理论判据
# ===================================================================

class TestRuleEngineIntegration:
    def test_merge_confidence_is_bayesian_not_constant(self):
        """多引擎合并的 confidence 是贝叶斯后验（≈0.993），不再是常数 1.0"""
        from rule_engine import RuleEngine

        eng = RuleEngine.__new__(RuleEngine)
        semgrep_i = {"rule_id": "x", "file": "a.java", "line": 1, "message": "s"}
        ast_i = {"rule_id": "x", "file": "a.java", "line": 1, "message": "a"}
        merged = eng._merge_multi_engine(
            [("semgrep", [semgrep_i]), ("ast", [ast_i])]
        )
        assert merged[0]["confidence"] == pytest.approx(144 / 145, abs=1e-6)
        assert merged[0]["confidence"] < 1.0

    def test_single_engine_gets_calibrated_confidence(self):
        """单引擎检出也有校准后验（semgrep 单独 ≈ 0.889）"""
        from rule_engine import RuleEngine

        eng = RuleEngine.__new__(RuleEngine)
        merged = eng._merge_multi_engine(
            [("semgrep", [{"rule_id": "x", "file": "a", "line": 1}])]
        )
        assert merged[0]["confidence"] == pytest.approx(8 / 9, abs=1e-6)

    def test_entropy_gate_rejects_low_entropy_hardcoded(self):
        """熵门控在 RuleEngine 内生效: 低熵硬编码被拒"""
        from rule_engine import RuleEngine

        eng = RuleEngine.__new__(RuleEngine)
        issues = [
            {
                "rule_id": "crypto-hardcoded-key-java",
                "file": "a.java",
                "line": 1,
                "code_snippet": 'String dbPassword = "aaaaaaaaaaaaaaaa";',
            },
            {
                "rule_id": "crypto-hardcoded-key-java",
                "file": "a.java",
                "line": 2,
                "code_snippet": 'String dbPassword = "sk-9f2kQz7mXv4bN8pL";',
            },
            {
                "rule_id": "xss-java-other",
                "file": "a.java",
                "line": 3,
                "code_snippet": "irrelevant",
            },
        ]
        kept = eng._apply_entropy_gate(issues)
        kept_lines = [i["line"] for i in kept]
        assert 1 not in kept_lines          # 低熵被拒
        assert 2 in kept_lines              # 高熵保留
        assert 3 in kept_lines              # 非 hardcoded 规则不受门控影响
