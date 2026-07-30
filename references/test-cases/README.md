# 测试案例规约

本目录包含各规约的测试案例，用于验证规则是否正确生效。

## 目录结构

```
test-cases/
├── README.md                    # 本文件
├── security/                    # 安全规约测试案例
│   ├── xxe-test.md             # XXE 测试案例
│   ├── xss-test.md             # XSS 测试案例
│   ├── authorization-test.md   # 越权访问测试案例
│   ├── path-traversal-test.md  # 目录穿越测试案例
│   ├── privilege-escalation-test.md  # 提权测试案例
│   ├── signature-bypass-test.md      # 签名绕过测试案例
│   ├── sql-injection-test.md         # SQL 注入测试案例
│   └── ssrf-test.md                  # SSRF 测试案例
├── design/                      # 设计规约测试案例
│   ├── architecture-test.md    # 架构合规测试案例
│   ├── api-design-test.md      # API 设计测试案例
│   └── database-test.md        # 数据库规范测试案例
└── implementation/              # 实现规约测试案例
    ├── naming-test.md          # 命名规范测试案例
    ├── error-handling-test.md  # 异常处理测试案例
    ├── concurrency-test.md     # 并发安全测试案例
    └── null-safety-test.md     # 空指针防护测试案例
```

## 测试案例格式

每个测试案例文件包含：

```markdown
# XXE 测试案例

## 违规代码样本

```java
// 应该命中 xxe-java-document-builder 规则
DocumentBuilderFactory factory = DocumentBuilderFactory.newInstance();
DocumentBuilder builder = factory.newDocumentBuilder();
Document doc = builder.parse(inputStream);
```

**预期命中规则**: `xxe-java-document-builder`

## 正确代码样本

```java
// 不应该命中任何规则
DocumentBuilderFactory factory = DocumentBuilderFactory.newInstance();
factory.setFeature("http://apache.org/xml/features/disallow-doctype-decl", true);
DocumentBuilder builder = factory.newDocumentBuilder();
Document doc = builder.parse(inputStream);
```

**预期命中规则**: 无
```

## 运行测试

使用测试脚本验证规则：

```bash
python scripts/test_rules.py --test-dir references/test-cases/
```

测试脚本会：
1. 扫描测试案例目录中的所有 `.md` 文件
2. 提取违规代码样本和正确代码样本
3. 运行规则引擎检查
4. 对比实际命中规则与预期命中规则
5. 输出测试报告
