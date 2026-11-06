# AI-Assisted Development Workflow (AI 辅助开发工作流)

> 本项目从骨架到 v1.4 全程在 AI 结对开发下完成。这份文档公开我们的真实工作方式——不是"让 AI 生成代码然后祈祷"，而是一套可审计的协作纪律。

## 1. 核心原则：评估驱动，而非生成驱动

AI 负责加速写代码，**人负责定义"什么叫对"**：

```
人类: 定义需求 → 定义评估标准(30问测试集+参考SQL) → Review 每一轮生成结果
AI  : 生成代码/SQL/Prompt → 执行 → 把失败原因喂回重生成
```

本项目的量化结果见 README 结果表（三路检索对比）。

## 2. 结构化上下文工程

AI 输出质量取决于输入上下文的质量。本项目实践：

- **Schema Prompt 作为契约**：表结构、关联路径、字段语义全部写进 Prompt——模型"照抄示例"是真实风险，所以示例即契约（详见 agent/nl2sql.py 的迭代记录）
- **错误反馈闭环**：护栏拒绝/占位符/数据库执行错误统一"拦截→把原因喂回→重生成"，AI 自己修复语法与字段错误
- **few-shot 优于规则声明**："之前N天必须双边界"写了规则模型照样犯，放一个错误示例立刻管用

## 3. AI 生成代码的 Review 纪律

AI 生成的代码不直接进主干：

1. **护栏先行**：模型永远只生成 SQL，执行前必过只读护栏（黑名单+多语句拦截+审计）——即使模型幻觉也不至于破坏数据
2. **测试锚定**：护栏本身 9 类 pytest 用例（含注释绕过、字符串误判）先写，AI 改护栏必须全绿
3. **逐行吃透**：进主干的每段 AI 代码，作者（人类）必须能白板讲清每一行为什么这么写

## 4. 真实踩坑记录（AI 协作的失败模式）

| 现象 | 根因 | 对策 |
|---|---|---|
| 模型输出非法 JSON | SQL 引号未转义 | 三层容错：剥代码块→宽松解析→错误回喂重生成 |
| 模型把 Prompt 示例照抄进 SQL（`:start/:end`）| 示例格式即契约 | Prompt 改为 SQL 表达式 + 注入当前日期 + 占位符拦截 |
| 模型 3 轮都直 JOIN 不存在的字段 | 自纠错修得了语法修不了路径 | 把"中间表必经路径"写进 Schema 知识 |
| 规则声明无效 | 指令遵循弱于模式匹配 | few-shot 错误示例替代规则文本 |

## 5. 工具栈

- 编码协作：Claude Code 类 CLI 工具 + 结构化上下文规范（CLAUDE.md 元数据体系）
- 模型：智谱 GLM（glm-4-flash 对话 / embedding-3 向量）
- 验证：pytest（护栏 9 用例）+ 30 问自动评估集（三路检索对比脚本 tests/compare_retrieval.py）

---

*This project was built human-AI pair programming style. The human defined what "correct" means (eval sets, guardrails); AI accelerated implementation. Every merged line is understood and defensible by the human author.*
