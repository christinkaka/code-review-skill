# 代码评审报告

**生成时间**: 2026-08-26T14:35:23.043060
**扫描耗时**: 2.59s

## 扫描信息

| 项目 | 值 |
|------|-----|
| 仓库 | `/private/tmp/test-e2e-repo` |
| 基线分支 | `main` |
| 目标分支 | `feature-vuln` |
| 规约 Profile | `default` |

## 变更统计

- 变更文件数: **1**
- 新增行数: **27**
- 删除行数: **0**

## 调用图分析

- 调用图节点: **5**
- 调用边: **12**
- 受影响方法: **3**

## 问题摘要

| 严重等级 | 数量 |
|----------|------|
| CRITICAL | 1 |
| HIGH | 0 |
| MEDIUM | 1 |
| LOW | 0 |
| **总计** | **2** |

### 按类别分布

| 类别 | 数量 |
|------|------|
| security | 1 |
| unknown | 1 |

## 详细问题列表

### 1. 🔴 [sqli-taint]

- **文件**: `VulnController.java`
- **行号**: 10
- **严重等级**: ERROR
- **类别**: security
- **描述**: 用户可控数据（HTTP 请求参数/头）经赋值、字符串拼接传播后流入 SQL 执行 API 或 SQL 构造 API。基于 Semgrep taint 模式做过程内数据流追踪，PreparedStatement 参数绑定（setString 等）作为净化器切断污点传播。
- **代码片段**:
  ```
  requires login
  ```
- **安全标准**: CWE-89 A03:2021

### 2. ⚪ [redirect-pattern-2]

- **文件**: `VulnController.java`
- **行号**: 15
- **严重等级**: HIGH
- **类别**: unknown
- **描述**: 用户可控 URL 参数未经白名单校验直接流入 `sendRedirect`，导致钓鱼攻击或凭证泄露。
- **代码片段**:
  ```
  requires login
  ```
- **安全标准**: CWE-601 A01:2021

---
*报告由代码评审工具自动生成 | 2026-08-26 14:35:23*