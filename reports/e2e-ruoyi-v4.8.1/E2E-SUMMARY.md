# 端到端代码审核演示总结

**目标**: RuoYi v4.8.0 → v4.8.1 版本升级差异审核  
**时间**: 2026-08-26  
**模式**: 3 票投票（Self-Consistency）

---

## 执行流程

| 步骤 | 耗时 | 结果 |
|------|------|------|
| Step 0 环境准备 | — | Python 3.10.20 + Semgrep 1.171.0 + RuoYi 克隆（27M） |
| Step 1 策略识别 | — | 案例确认：RuoYi v4.8.0→v4.8.1（59 文件/Java 33 个） |
| Step 1.5 策略确认 | — | 用户确认：default Profile + 3 票投票模式 |
| Step 2 确定性扫描 | 4.5s | AST 31 + Semgrep 20 → 去重后 45 条（35 CRITICAL） |
| Step 3 AI 增强 | — | 3 个子 Agent 并行评审（qwen 契约） |
| Step 4 合并报告 | — | 多数票聚合：45 → 4 条 |

---

## 三票一致性

| 指标 | 结果 |
|------|------|
| 三票完全一致 | **44/45 条（97.8%）** |
| 分歧项 | 1 条（`err-java-empty-catch` @ ExcelUtil:1417） |
| 每票 TP/FP 结构 | vote1: 4/41, vote2: 3/42, vote3: 4/41 |

**分歧项裁决**: `ExcelUtil:1417` 空 catch 块（vote1/vote3 判 TP、vote2 判 FP）→ 多数票保留（2/3 TP）

---

## 最终保留问题（4 条）

### 1. [INFO] `naming-java-boolean-vague` — ServletUtils.java:166
**投票**: TP 3/3 | **置信度**: 0.8  
**问题**: `boolean flag = false;` 语义模糊，应重命名为 `isMobile`  
**证据**: `checkAgentIsMobile` 方法内局部变量，全方法仅 3 处引用，重命名零风险

### 2. [INFO] `naming-java-constant-case` — ExcelUtil.java:112
**投票**: TP 3/3 | **置信度**: 0.85  
**问题**: `public static final int sheetSize = 65536;` 违反 UPPER_SNAKE_CASE  
**证据**: 同文件 SEPARATOR/FORMULA_REGEX_STR 均已合规，全仓仅 ExcelUtil 内部 3 处引用

### 3. [WARNING] `err-java-empty-catch` — ExcelUtil.java:1417
**投票**: TP 2/3 | **置信度**: 0.8  
**问题**: `catch (NumberFormatException e) {}` 完全为空，统计列静默丢值无排查线索  
**证据**: 源码 1417-1420 行 catch 块无注释、无日志，合计统计静默偏差

### 4. [WARNING] `err-java-empty-catch` — LogAspect.java:209
**投票**: TP 3/3 | **置信度**: 0.8  
**问题**: `catch (Exception e) {}` 完全静默吞掉审计参数序列化失败  
**证据**: 源码 209-212 行 catch 块为空，sys_oper_log 审计数据可无声缺失

---

## 滤除问题（41 条）

| 类别 | 数量 | 滤除原因 |
|------|------|----------|
| `sqli-mybatis-dollar` @ pom.xml | 31 | Maven 属性插值（`${spring-boot.version}` 等），构建期静态替换，非 MyBatis Mapper |
| `sqli-mybatis-dollar` @ SysUserMapper.xml | 3 | `${params.dataScope}` 数据权限片段，`@DataScope` 注解后端拼接（已加固） |
| `serialVersionUID` 命名 | 3 | Java 序列化规范法定魔法字段名 |
| `xss-js-innerhtml` @ fileinput.js | 1 | 第三方库 IE 检测常量（`isIE(9)/isIE(10)` 字面量调用） |
| `api-java-rest-naming` @ SysMenuController | 1 | 实际为 `@PostMapping`（规则针对 GET），前端硬编码 URL |
| `null-java-method-chain` @ LogAspect | 1 | `joinPoint.getTarget()` 在 Spring AOP 方法切点恒非空 |
| `err-java-empty-catch` @ KickoutSessionFilter | 1 | catch 内有注释"面对异常，我们选择忽略"，预期会话失效 |

---

## 关键发现

1. **扫描器文件类型识别缺陷**: 31 条 `sqli-mybatis-dollar` 打在 pom.xml 上，规则未区分 Maven 属性插值与 MyBatis `${}` SQL 拼接
2. **RuoYi 已加固形态识别**: `${params.dataScope}` 经 `@DataScope` + `clearDataScope()` 后端拼接，子 Agent 正确识别为已加固
3. **投票机制价值**: 97.8% 一致率证明低温评审稳定性；1 条分歧项被多数票正确保留（ExcelUtil:1417 空 catch 确实无注释）

---

## 产出文件

- `report.json`: 4 条最终问题（JSON 格式）
- `report.md`: Markdown 报告（待更新）
- `subagent-review-task.md`: 任务文件（含投票委派说明）
- `ai-review-result-vote{1,2,3}.json`: 三票原始裁决（留档可审计）

---

**端到端演示完成** ✅
