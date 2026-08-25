#!/usr/bin/env python3
"""
降噪数学理论模块（noise_theory）

本模块为代码评审降噪提供确定性的、有数学理论支撑的判据，
替代经验阈值（如"长度 >= 8"）。所有函数均为纯函数：
同一输入永远产生同一输出，无随机性、无环境依赖。

理论支柱
========

1. Shannon 熵（信息论，Shannon 1948）
   ------------------------------------
   字符串 s 的字符频率分布 p_i 的熵：

       H(s) = - Σ_i p_i · log2(p_i)        [bits/char]

   H 度量"每个字符平均携带的信息量"。均匀随机抽取的字符串
   H → log2(K)（K 为字符集大小）；重复模式 H → 0。

2. Miller-Madow 偏差修正（Miller 1955）
   ------------------------------------
   有限样本下 plug-in 熵估计量系统性低估真实熵，期望偏差约为：

       E[Ĥ - H] ≈ -(K-1) / (2n)        [nats]

   修正估计量：

       Ĥ_MM = Ĥ_plug-in + (K-1) / (2n · ln2)     [bits]

   其中 K 为样本中出现的不同字符数，n 为样本长度。

3. 字符集分层假设检验（charset-stratified test）
   --------------------------------------------
   绝对熵无法区分十六进制密钥（H=4.0）与英文文本（order-0 ≈ 4.1-4.5），
   必须先按字符集分层再检验：

   - H0（自然/人工字符串）：值来自自然语言或模板，通常含空白字符，
     或属于低熵模式（重复、占位符）
   - H1（机器生成凭据）：值从凭据字符集（hex/base62/base64/符号混合）
     均匀随机抽取，H ≈ log2(K)

   判决规则（详见 is_high_entropy_secret 的 docstring）：
   - 凭据字符集字符串：H_MM >= 3.5 且总熵 n·H_MM >= 32 bits
   - 自然字符集（含空白）字符串：判定为非机器生成格式，拒绝

   已知局限（诚实声明）：
   - 字符频率熵无法识别顺序结构（"123456..." 与随机数字同分布），
     该问题等价于 Shannon 熵 < Kolmogorov 复杂度的鸿沟，业界工具
     （detect-secrets / truffleHog）同样存在；
   - 自然语言口令短语（passphrase）会被拒绝——但此类值多为示例文案。

4. 贝叶斯后验校准（概率论）
   ------------------------
   检出的"置信度"不应是拍脑袋常数，而应是校准概率：

       P(TP | E) = LR · π / (LR · π + (1 - π))

   π 为先验 P(TP)；LR 为证据 E 的似然比。多引擎一致检出时
   （给定条件独立假设）：

       LR = Π_i (sensitivity_i / false_alarm_i)

   先验采用最大熵选择 π = 0.5（Jeffreys 先验，无反馈数据时最无偏）；
   引擎灵敏度参数为文档化假设，可通过 config 覆盖，
   反馈数据积累后应由 FeedbackManager 统计 empirically 更新。

5. 期望错误发现率（Benjamini-Hochberg 风格 FDR 控制）
   -------------------------------------------------
   扫描产生 N 条检出，每条带校准后验 p_i（= P(TP|E_i)），则：

       E[FP] = Σ_i (1 - p_i)
       E[FDR] = Σ_i (1 - p_i) / N

   给定 FDR 预算 q，按后验降序保留最大前缀 k 使得
   Σ_{i<=k}(1-p_i)/k <= q，即为 BH 程序在后验意义上的对应物。

6. Z-score 离群检验（统计过程控制思想）
   ----------------------------------
   规则维度的噪音监控不应看"Top N 排名"（随机且不稳定），
   而应做统计检验：规则检出率 r_j 相对全体规则分布的标准化离群度：

       z_j = (r_j - μ_r) / σ_r

   |z_j| >= 2 判定为离群（噪音规则候选）。
"""

import math
import re
from typing import Dict, List, Optional, Sequence, Tuple

# ============================================================
# 1. 信息论：Shannon 熵 + Miller-Madow 修正
# ============================================================

def shannon_entropy_bits(value: str) -> Tuple[float, float]:
    """计算字符串的 plug-in Shannon 熵与 Miller-Madow 修正熵

    Args:
        value: 待测字符串

    Returns:
        (H_plug_in, H_miller_madow)，单位 bits/char

    数学：
        H = -Σ p_i log2 p_i
        H_MM = H + (K-1)/(2n·ln2)，K 为不同字符数，n 为长度
    """
    n = len(value)
    if n == 0:
        return (0.0, 0.0)

    freq: Dict[str, int] = {}
    for ch in value:
        freq[ch] = freq.get(ch, 0) + 1

    h = 0.0
    for count in freq.values():
        p = count / n
        h -= p * math.log2(p)

    k = len(freq)
    h_mm = h + (k - 1) / (2 * n * math.log(2))
    return (round(h, 6), round(h_mm, 6))


# ============================================================
# 2. 字符集分类
# ============================================================

# 凭据字符集（由小到大），命中最先匹配者
_HEX = re.compile(r"^[0-9a-fA-F]+$")
_BASE62 = re.compile(r"^[0-9a-zA-Z]+$")
_BASE64 = re.compile(r"^[0-9a-zA-Z+/=]+$")
_ALNUM_SYM = re.compile(r"^[0-9a-zA-Z_\-./~!@#$%^&*()+\[\]{}<>?|\\]+$")
_PLACEHOLDER = re.compile(r"\$\{|\{%|\$\{\{|<<|>>")

# 结构判据：非凭据命名空间的语法形态
# HTTP 头名：大写字母数字段以连字符连接（X-AUTH-TOKEN、CONTENT-TYPE-2）
_HTTP_HEADER_NAME = re.compile(r"[A-Z0-9]+(?:-[A-Z0-9]+)+")
# 连字符自然词：纯字母段以连字符连接（self-contained、Content-Type）；
# 真实机器凭据即使带连字符前缀（sk-…），后段也含数字/混合大小写，
# 不会落在纯字母分段形态里
_HYPHEN_NATURAL_WORD = re.compile(r"[A-Za-z]+(?:-[A-Za-z]+)+")

CREDENTIAL_CHARSETS = ("hex", "base62", "base64", "alnum_sym")


def classify_charset(value: str) -> str:
    """将字符串分类到字符集族

    Returns:
        "hex"      : 仅 [0-9a-fA-F]（K=16, log2 K = 4.0）
        "base62"   : 仅 [0-9a-zA-Z]（K=62, log2 K ≈ 5.95）
        "base64"   : base62 + [+/=]
        "alnum_sym": 字母数字 + 常见符号
        "natural"  : 含空白或上述之外的字符（自然语言/文案）
        "placeholder": 含 ${...} / {%...%} / <<...>> 模板标记
    """
    if _PLACEHOLDER.search(value):
        return "placeholder"
    if not value.strip():
        return "natural"
    if _HEX.match(value):
        return "hex"
    if _BASE62.match(value):
        return "base62"
    if _BASE64.match(value):
        return "base64"
    if _ALNUM_SYM.match(value):
        return "alnum_sym"
    return "natural"


# ============================================================
# 3. 熵门控：结构化字符串是否为高熵凭据
# ============================================================

# 判决参数（均可推导/复核，见模块 docstring 第 3 节）
MIN_LEN = 12          # 熵估计的最低样本量：n<12 时 MM 修正方差过大
MIN_PER_CHAR = 3.5    # 凭据字符集判决门限（hex 均匀=4.0，留估计余量）
MIN_TOTAL_BITS = 32.0  # 总熵门限：2^32 次方暴力破解边界，低于此为弱凭据


def is_high_entropy_secret(
    value: str,
    min_len: int = MIN_LEN,
    min_per_char: float = MIN_PER_CHAR,
    min_total_bits: float = MIN_TOTAL_BITS,
) -> Tuple[bool, Dict]:
    """判决字符串是否为"机器生成的高熵凭据"（确定性函数）

    判决逻辑（每一步均有数学依据）：
    1. placeholder      -> 拒绝（结构判决：模板注入，非硬编码）
    2. 结构判据         -> 拒绝（URL/URI 路径/HTTP 头名/连字符自然词：
                          语法结构上不属于凭据命名空间，先验 P(TP)≈0，
                          无需进入熵检验）
    3. n < min_len      -> 拒绝（统计判决：样本不足，熵估计不可靠）
    4. charset == natural -> 拒绝（假设检验：非凭据字符集，H0 无法拒绝）
    5. 凭据字符集:
       H_MM >= min_per_char       （单位熵检验：接近均匀抽取）
       且 n · H_MM >= min_total_bits （总熵检验：非弱凭据）

    Args:
        value: 字符串字面量（不含引号）

    Returns:
        (verdict, detail)：detail 含每步判决依据，可追溯
    """
    detail: Dict = {
        "value_len": len(value),
        "charset": classify_charset(value),
    }

    if detail["charset"] == "placeholder":
        detail["reason"] = "模板占位符（${}/{%%}/<<>>），非硬编码"
        return (False, detail)

    # ---- 结构判据（2026-08-24 spring-boot 端到端实测驱动）----
    # 凭据不存在于这些语法命名空间：URL、URI 路径、HTTP 头名、
    # 连字符自然词。它们可能满足熵门限（如 /oauth2/token 的
    # H_MM≈3.6），但"高熵"来自路径语义而非随机抽取——这正是
    # Shannon 熵无法区分"结构熵"与"随机熵"的已知局限，需以
    # 结构先验补足。
    if "://" in value:
        detail["reason"] = "URL 结构（含 ://），非凭据"
        return (False, detail)
    if value.startswith("/"):
        detail["reason"] = "URI 路径（以 / 开头），非凭据"
        return (False, detail)
    if _HTTP_HEADER_NAME.fullmatch(value):
        detail["reason"] = "HTTP 头名结构（大写字母数字+连字符），非凭据"
        return (False, detail)
    if _HYPHEN_NATURAL_WORD.fullmatch(value):
        detail["reason"] = "连字符自然词（纯字母分段），非凭据"
        return (False, detail)

    if len(value) < min_len:
        detail["reason"] = f"样本量不足（n={len(value)} < {min_len}），熵估计不可靠"
        return (False, detail)

    h_plugin, h_mm = shannon_entropy_bits(value)
    total_bits = len(value) * h_mm
    detail.update(
        {
            "entropy_plugin": h_plugin,
            "entropy_miller_madow": h_mm,
            "total_bits": round(total_bits, 2),
        }
    )

    if detail["charset"] == "natural":
        detail["reason"] = "自然字符集（含空白），非机器生成凭据格式"
        return (False, detail)

    if h_mm < min_per_char:
        detail["reason"] = (
            f"单位熵不足（H_MM={h_mm:.2f} < {min_per_char} bits/char，"
            f"远离均匀抽取 log2(K)）"
        )
        return (False, detail)

    if total_bits < min_total_bits:
        detail["reason"] = (
            f"总熵不足（{total_bits:.1f} < {min_total_bits} bits，"
            f"暴力破解代价 < 2^32，弱凭据低报告价值）"
        )
        return (False, detail)

    detail["reason"] = (
        f"高熵凭据（charset={detail['charset']}, H_MM={h_mm:.2f}, "
        f"总熵={total_bits:.1f} bits）"
    )
    return (True, detail)


# ============================================================
# 4. 贝叶斯后验校准
# ============================================================

# 引擎判决质量参数（文档化假设，config 可覆盖，反馈数据积累后应经验更新）
# 依据 docs/architecture.md 引擎优先级声明：AST 最精确 > Semgrep > 正则
ENGINE_PARAMS = {
    "ast": {"sensitivity": 0.90, "false_alarm": 0.05},
    "semgrep": {"sensitivity": 0.80, "false_alarm": 0.10},
    "regex": {"sensitivity": 0.60, "false_alarm": 0.20},
}

# 最大熵先验（无反馈数据时的 Jeffreys 选择）
DEFAULT_PRIOR = 0.5


def bayes_posterior(prior: float, likelihood_ratio: float) -> float:
    """贝叶斯后验：P(TP|E) = LR·π / (LR·π + (1-π))

    Args:
        prior: 先验 P(TP)，无信息时取 0.5（最大熵选择）
        likelihood_ratio: 证据似然比 P(E|TP)/P(E|FP)

    Returns:
        校准后验概率 P(TP|E)
    """
    if likelihood_ratio <= 0:
        raise ValueError("似然比必须为正")
    num = likelihood_ratio * prior
    return round(num / (num + (1.0 - prior)), 6)


def engine_agreement_posterior(
    engines: Sequence[str],
    prior: float = DEFAULT_PRIOR,
    engine_params: Optional[Dict[str, Dict[str, float]]] = None,
) -> float:
    """多引擎一致检出的贝叶斯后验

    模型（假设给定真相时引擎条件独立）：
        LR = Π_i (sensitivity_i / false_alarm_i)

    Args:
        engines: 检出同一位置的引擎列表，如 ["ast", "semgrep"]
        prior: 先验 P(TP)
        engine_params: 引擎参数覆盖

    Returns:
        P(TP | engines 都检出)
    """
    params = engine_params or ENGINE_PARAMS
    lr = 1.0
    for e in engines:
        p = params.get(e)
        if p is None:
            # 未知引擎：保守取弱证据 LR=1（不改变先验）
            continue
        lr *= p["sensitivity"] / p["false_alarm"]
    return bayes_posterior(prior, lr)


# ============================================================
# 5. FDR / 期望错误发现数
# ============================================================

def fdr_report(confidences: Sequence[float]) -> Dict:
    """扫描级期望错误发现统计

    Args:
        confidences: 每条检出的校准后验 P(TP|E_i)

    Returns:
        {"n": N, "expected_fp": Σ(1-p_i), "expected_fdr": Σ(1-p_i)/N}
    """
    n = len(confidences)
    if n == 0:
        return {"n": 0, "expected_fp": 0.0, "expected_fdr": 0.0}
    expected_fp = sum(1.0 - c for c in confidences)
    return {
        "n": n,
        "expected_fp": round(expected_fp, 2),
        "expected_fdr": round(expected_fp / n, 4),
    }


def bh_keep_count(confidences: Sequence[float], q: float = 0.10) -> int:
    """BH 风格 FDR 控制下的保留数

    按后验降序排列，保留最大前缀 k 使 Σ_{i<=k}(1-p_i)/k <= q。

    Args:
        confidences: 各检出后验
        q: FDR 预算（默认 0.10）

    Returns:
        建议保留的检出条数 k
    """
    if not confidences:
        return 0
    ordered = sorted(confidences, reverse=True)
    cumulative_fp = 0.0
    for k, p in enumerate(ordered, start=1):
        cumulative_fp += 1.0 - p
        if cumulative_fp / k > q:
            return k - 1
    return len(ordered)


# ============================================================
# 6. 规则维度 Z-score 离群检验（噪音规则监控）
# ============================================================

def rule_z_scores(rule_counts: Dict[str, int]) -> Dict[str, float]:
    """规则检出量的标准化离群度（统计过程控制思想）

    用全体规则的检出量分布作为参照，计算每条规则的 z-score：
        z_j = (x_j - μ) / σ
    |z| >= 2 视为离群（噪音规则候选）。

    注意：规则间检出量天然非同分布，此为跨截面快速筛选；
    严格的 SPC 应在反馈数据积累后按规则自身历史序列建控制图。

    Args:
        rule_counts: {rule_id: 检出数}

    Returns:
        {rule_id: z-score}
    """
    if len(rule_counts) < 3:
        return {}
    values = list(rule_counts.values())
    mean = sum(values) / len(values)
    variance = sum((v - mean) ** 2 for v in values) / len(values)
    std = math.sqrt(variance)
    if std == 0:
        return {rid: 0.0 for rid in rule_counts}
    return {rid: round((c - mean) / std, 3) for rid, c in rule_counts.items()}


def flag_noise_rules(rule_counts: Dict[str, int], threshold: float = 2.0) -> List[str]:
    """返回 z-score 超阈值的噪音规则候选（按 |z| 降序）"""
    z = rule_z_scores(rule_counts)
    flagged = [(rid, zv) for rid, zv in z.items() if abs(zv) >= threshold]
    flagged.sort(key=lambda kv: -abs(kv[1]))
    return [rid for rid, _ in flagged]
