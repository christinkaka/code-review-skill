# 测试代码库验证说明

## 概述

本测试代码库用于验证代码评审工具的实际有效性。包含 Java、Python、TypeScript 三种语言的已知安全漏洞样本和对应的安全代码样本。

- **漏洞文件（Vulnerable）**：包含真实的安全漏洞，应该被评审工具检出
- **安全文件（Safe）**：使用正确的安全实践，理想情况下不应被检出

> **重要说明**：扫描器（Semgrep + Tree-sitter）基于**模式匹配**，无法理解完整业务语义。
> 即使是 `Safe.java` 这种设计为"安全"的示例，仍可能被规则引擎命中（标记为可疑）。
> 这是**正常的**——这些命中需要交给**子 Agent AI 二次评审**来识别是否为误报。
> 
> 因此：
> - **扫描器命中数 ≠ 真实漏洞数**
> - 真实漏洞数 = 命中数 - AI 评审判定的误报数
> - 这个"两阶段评审"是本 Skill 的核心设计

**使用方法**：
1. 跑全库扫描：`python scripts/scan.py --repo test-validation --full-scan --workflow comprehensive`
2. 委派子 Agent 读取 `report/subagent-review-task.md` 做 AI 评审
3. 对比 `report.json` 中 `is_false_positive=true` 的数量与 `known-issues.json` 中的已知问题数

## 目录结构

```
test-validation/
├── known-issues.json              # 已知问题清单（验证基准）
├── README.md                      # 本文件
├── java/                          # Java 测试代码
│   ├── xxe/
│   │   ├── Vulnerable.java        # XXE 漏洞（2 处）
│   │   └── Safe.java              # 安全代码
│   ├── xss/
│   │   ├── Vulnerable.java        # XSS 漏洞（2 处）
│   │   └── Safe.java              # 安全代码
│   ├── sqli/
│   │   ├── Vulnerable.java        # SQL 注入漏洞（2 处）
│   │   └── Safe.java              # 安全代码
│   └── path-traversal/
│       ├── Vulnerable.java        # 路径穿越漏洞（2 处）
│       └── Safe.java              # 安全代码
├── python/                        # Python 测试代码
│   ├── xxe/
│   │   ├── vulnerable.py          # XXE 漏洞（3 处）
│   │   └── safe.py                # 安全代码
│   ├── command-injection/
│   │   ├── vulnerable.py          # 命令注入漏洞（4 处）
│   │   └── safe.py                # 安全代码
│   └── path-traversal/
│       ├── vulnerable.py          # 路径穿越漏洞（3 处）
│       └── safe.py                # 安全代码
└── typescript/                    # TypeScript 测试代码
    ├── xss/
    │   ├── vulnerable.ts          # XSS 漏洞（4 处）
    │   └── safe.ts                # 安全代码
    └── ssrf/
        ├── vulnerable.ts          # SSRF 漏洞（4 处）
        └── safe.ts                # 安全代码
```

## 已知问题统计

| 语言       | 漏洞类型         | 漏洞文件数 | 漏洞点数 | 安全文件数 |
|------------|------------------|-----------|---------|-----------|
| Java       | XXE              | 1         | 2       | 1         |
| Java       | XSS              | 1         | 2       | 1         |
| Java       | SQL Injection    | 1         | 2       | 1         |
| Java       | Path Traversal   | 1         | 2       | 1         |
| Python     | XXE              | 1         | 3       | 1         |
| Python     | Command Injection| 1         | 4       | 1         |
| Python     | Path Traversal   | 1         | 3       | 1         |
| TypeScript | XSS              | 1         | 4       | 1         |
| TypeScript | SSRF             | 1         | 4       | 1         |
| **合计**   | **6 类漏洞**     | **9**     | **26**  | **9**     |

## 漏洞详情

### Java 漏洞

#### XXE（XML External Entity）注入
- **文件**：`java/xxe/Vulnerable.java`
- **漏洞位置**：第 22 行、第 29 行
- **规则 ID**：`xxe-java-document-builder`
- **描述**：`DocumentBuilderFactory.newInstance()` 创建后未调用 `setFeature()` 禁用外部实体，攻击者可通过恶意 XML 读取服务器文件或发起 SSRF
- **安全做法**：设置 `disallow-doctype-decl`、`external-general-entities`、`external-parameter-entities` 等特性

#### XSS（Cross-Site Scripting）
- **文件**：`java/xss/Vulnerable.java`
- **漏洞位置**：第 30 行、第 44 行
- **规则 ID**：`xss-java-servlet-output`
- **描述**：Servlet 将 `request.getParameter()` 获取的用户输入直接拼接到 HTML 响应中，未进行 HTML 编码
- **安全做法**：对用户输入进行 HTML 实体编码后再输出

#### SQL 注入
- **文件**：`java/sqli/Vulnerable.java`
- **漏洞位置**：第 33 行、第 45 行
- **规则 ID**：`sqli-java-statement-concat`
- **描述**：使用 `Statement` 拼接用户输入构造 SQL 语句，攻击者可注入任意 SQL
- **安全做法**：使用 `PreparedStatement` 参数化查询

#### 路径穿越
- **文件**：`java/path-traversal/Vulnerable.java`
- **漏洞位置**：第 27 行、第 36 行
- **规则 ID**：`path-traversal-java-file`、`path-traversal-java-weak-filter`
- **描述**：直接使用用户输入构造文件路径，或使用不完整的过滤（仅替换 `../`）
- **安全做法**：使用 `getCanonicalPath()` 规范化路径后验证前缀

### Python 漏洞

#### XXE（XML External Entity）注入
- **文件**：`python/xxe/vulnerable.py`
- **漏洞位置**：第 20 行、第 28 行、第 35 行
- **规则 ID**：`xxe-python-lxml-parser`、`xxe-python-lxml-parse`、`xxe-python-lxml-resolve-entities`
- **描述**：lxml 的 `XMLParser()` 默认配置未禁用外部实体，或显式设置 `resolve_entities=True`
- **安全做法**：设置 `resolve_entities=False`、`no_network=True`，或使用 `defusedxml` 库

#### 命令注入
- **文件**：`python/command-injection/vulnerable.py`
- **漏洞位置**：第 19 行、第 27 行、第 35 行、第 43 行
- **规则 ID**：`priv-python-subprocess-shell-true`、`priv-python-os-system`、`priv-python-popen-shell-true`、`priv-python-check-output-shell-true`
- **描述**：`subprocess.run()`/`Popen()`/`check_output()` 使用 `shell=True` 且拼接用户输入，或 `os.system()` 直接执行用户输入
- **安全做法**：使用列表形式传递参数（`shell=False`），或使用 `shlex.quote()` 转义

#### 路径穿越
- **文件**：`python/path-traversal/vulnerable.py`
- **漏洞位置**：第 22 行、第 30 行、第 39 行
- **规则 ID**：`path-traversal-python-os-path-join`、`path-traversal-python-weak-filter`
- **描述**：`os.path.join()` 使用用户输入构造路径，或使用不完整的过滤
- **安全做法**：使用 `os.path.realpath()` 或 `pathlib.Path.resolve()` 验证路径

### TypeScript 漏洞

#### XSS（Cross-Site Scripting）
- **文件**：`typescript/xss/vulnerable.ts`
- **漏洞位置**：第 21 行、第 30 行、第 40 行、第 50 行
- **规则 ID**：`xss-ts-innerhtml`、`xss-ts-document-write`、`xss-ts-outerhtml`、`xss-ts-dangerously-set-innerhtml`
- **描述**：`innerHTML`/`outerHTML`/`document.write()`/`dangerouslySetInnerHTML` 直接赋值用户输入
- **安全做法**：使用 `textContent` 替代，或使用 DOMPurify 消毒

#### SSRF（Server-Side Request Forgery）
- **文件**：`typescript/ssrf/vulnerable.ts`
- **漏洞位置**：第 22 行、第 31 行、第 44 行、第 59 行
- **规则 ID**：`ssrf-ts-fetch-user-input`、`ssrf-ts-http-get-user-input`、`ssrf-ts-fetch-weak-filter`
- **描述**：`fetch()`/`http.get()` 直接使用用户输入的 URL，或使用不完整的过滤
- **安全做法**：使用域名白名单 + DNS 解析校验 + 协议限制

## 验证目标

验证代码评审工具的实际有效性，核心指标包括：

| 指标     | 公式                           | 目标值   |
|----------|-------------------------------|---------|
| 检出率   | 正确检出的已知问题 / 总已知问题 | >= 80%  |
| 误报率   | 检出的非问题 / 总检出数         | <= 10%  |
| 漏报率   | 未检出的已知问题 / 总已知问题   | <= 20%  |
| 安全文件误报 | 安全文件被检出数 / 安全文件总数 | 0       |

## 验证步骤

### 步骤 1：运行扫描工具

```bash
python scripts/scan.py \
  --repo test-validation/ \
  --base main \
  --target main \
  --output test-validation/report/
```

### 步骤 2：对比结果

1. 读取 `known-issues.json`（已知问题清单，作为验证基准）
2. 读取扫描工具输出的 `report.json`（实际检出结果）
3. 逐条对比：
   - 按 `file` + `line` + `rule_id` 匹配
   - 标记每个已知问题为"已检出"或"未检出"
   - 标记每个检出结果为"正确"或"误报"

### 步骤 3：计算指标

```
检出率 = 已检出的已知问题数 / 总已知问题数（26）
误报率 = 误报数 / 总检出数
漏报率 = 未检出的已知问题数 / 总已知问题数（26）
安全文件误报 = 安全文件中被检出的问题数（应为 0）
```

### 步骤 4：生成验证报告

报告应包含以下内容：

1. **汇总指标**：检出率、误报率、漏报率
2. **按语言统计**：Java/Python/TypeScript 各自的检出率
3. **按漏洞类型统计**：XXE/XSS/SQLi/路径穿越/命令注入/SSRF 各自的检出率
4. **检出详情**：列出每个已知问题的检出状态
5. **漏报分析**：列出未检出的已知问题，分析原因
6. **误报分析**：列出误报的检出结果，分析原因
7. **安全文件检查**：确认安全文件未被误报

## 验证脚本示例

```python
import json

def validate(report_path, known_issues_path):
    """验证代码评审工具的检出效果"""

    with open(known_issues_path) as f:
        known = json.load(f)

    with open(report_path) as f:
        report = json.load(f)

    # 构建检出结果的索引
    detected = set()
    for issue in report.get("issues", []):
        key = (issue["file"], issue["line"], issue["rule_id"])
        detected.add(key)

    # 统计
    total = 0
    found = 0
    missed = []

    for lang in ["java", "python", "typescript"]:
        for issue in known.get(lang, []):
            total += 1
            key = (issue["file"], issue["line"], issue["rule_id"])
            if key in detected:
                found += 1
            else:
                missed.append(issue)

    # 检查安全文件误报
    safe_files = {s["file"] for s in known.get("safe_files", [])}
    false_positives = [
        issue for issue in report.get("issues", [])
        if issue["file"] in safe_files
    ]

    # 输出结果
    print(f"总已知问题数：{total}")
    print(f"已检出：{found}")
    print(f"未检出（漏报）：{total - found}")
    print(f"检出率：{found / total * 100:.1f}%")
    print(f"漏报率：{(total - found) / total * 100:.1f}%")
    print(f"安全文件误报数：{len(false_positives)}")

    if missed:
        print("\n漏报详情：")
        for m in missed:
            print(f"  - {m['file']}:{m['line']} [{m['rule_id']}] {m['description']}")

    if false_positives:
        print("\n误报详情：")
        for fp in false_positives:
            print(f"  - {fp['file']}:{fp['line']} [{fp['rule_id']}]")

if __name__ == "__main__":
    validate("test-validation/report/report.json", "test-validation/known-issues.json")
```

## 设计原则

1. **真实性**：每个漏洞都是真实存在的安全问题，不是臆想的
2. **可编译/可运行**：代码在语法上是正确的，可以正常编译或运行
3. **对照性**：每个漏洞文件都有对应的安全文件，形成对照
4. **完整性**：已知问题清单覆盖了所有漏洞点，作为验证基准
5. **渐进性**：部分文件包含"不完整过滤"的漏洞（弱过滤），测试工具是否能识别不完整的修复
