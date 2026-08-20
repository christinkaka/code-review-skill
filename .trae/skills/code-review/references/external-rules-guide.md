# 外部规则加载详细指南

## 推荐的开源规约库

| 规则库 | Stars | 语言覆盖 | 适用场景 |
|---|---|---|---|
| **Semgrep 官方规则** | 15.8k | 30+ 语言 | OWASP Top 10 全集，20000+ 规则 |
| **0xdea/semgrep-rules** | ~500 | C/C++ | 缓冲区溢出、use-after-free、整数溢出等 |
| **mindedsecurity/android-security** | 335 | Java/Kotlin | Android 移动安全，基于 OWASP MASTG |
| **dipa96/semgrep-rules** | ~30 | JavaScript | DOM XSS 深度检测 |

## 使用命令

```bash
# 列出推荐规则库
python3 scripts/rule_loader.py --list

# 从推荐库加载
python3 scripts/rule_loader.py --from recommended --repo-key semgrep-official
python3 scripts/rule_loader.py --from recommended --repo-key 0xdea-c-cpp

# 从自定义 GitHub 仓库加载
python3 scripts/rule_loader.py --from github --repo https://github.com/user/rules --subdir rules/security

# 查看已加载规则
python3 scripts/rule_loader.py --status

# 移除规则
python3 scripts/rule_loader.py --remove <rule-id>

# 按类别过滤
python3 scripts/rule_loader.py --from recommended --repo-key semgrep-official --categories security
```

## 目录结构

```
references/external/
├── semgrep-official_java-spring-csrf-disabled.yaml
├── 0xdea-c-cpp_raptor-buffer-overflow.yaml
├── .loaded_rules.json          # 已加载规则元数据
└── .temp/                       # 临时目录（克隆后自动清理）
```

## 外部规则 vs 内部规则

| 维度 | 内部规则 | 外部规则 |
|---|---|---|
| 来源 | 团队编写 | 开源仓库加载 |
| 格式 | Markdown + pattern | Semgrep YAML |
| 目录 | security/design/implementation | external/ |
| 适用 | 业务规范、架构约束 | 通用安全、行业标准 |

## 最佳实践

1. 通用安全规则直接从 Semgrep 官方库加载
2. 内部规则专注业务特定规范
3. 按需加载，不要一次加载所有规则
4. 定期重新加载获取最新规则
5. 用 `--remove` 移除不适用的规则
