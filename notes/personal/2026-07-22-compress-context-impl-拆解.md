## 2026-07-22 | Agent 类 `_compress_context_impl` 拆解（line 392-501）

**读了什么**：`src/agentscope/agent/_agent.py:392-501`

**读了多久**：约 3 小时（含早餐/思考）

---

### Q1: 4 段消息拼接的设计意图

我的理解：
- 分段让语义更清晰
- 系统 / 要压缩 / 动态指令 / 用户任务

**判断**：⚠️ 结构对，语义浅。`AssistantMsg` 不是分类标签，是**消息来源身份**——"agent 之前说过的补充指令"。

### Q2: reserve_ratio 降级策略

我的理解：
- 优先按用户需求，保留更多上下文
- FallBack 模式

**判断**：⚠️ 方向对，名字不准。**Graceful Degradation（优雅降级）**——"3 级降级"模式（理想 → 激进 → 暴力），不是 fallback（替代方案）。

### Q3: trigger_ratio vs reserve_ratio

我的理解：
- trigger = 0.8（开始压缩）
- reserve = 0.1（保留）
- trigger > reserve

**判断**：❌ **根本性误解**。trigger 和 reserve 是**2 个独立概念**：
- trigger = "**什么时候**触发"（邮箱满到 80%）
- reserve = "**留多少**空间"（压缩任务自己用 10%）
- 不一定要 trigger > reserve！

### Q4（自加）: `**` 字典解包

**判断**：✅✅ 完全对。`cfg.summary_template.format(**res.content)` = 字典展开成关键字参数。LLM 结构化输出 → 自动解析成 dict → 模板填字段。

---

### 我今天最大的收获

1. **触发比率 vs 预留比率是独立的**——以前以为"一个东西的两面"，错
2. **AssistantMsg 是消息来源身份**——不是分类标签
3. **Graceful Degradation vs Fallback 的区别**——前者是按需降级保证可用，后者是找替代方案

### 我之前没意识到的盲点

读 W1 那 4 份 learning-map 时，我**没仔细看 trigger_ratio 和 reserve_ratio 的语义**——所以今天 Q3 答错。**这就是"看 AI 整理的图 vs 自己读代码"的区别**——AI 的图掩盖了细节。

### 明天要看

- `_agent.py:500-619`（`_compress_context_impl` 下半段：structured output + apply change + offload）
- 或者跳到 `_reply` 入口（line 620）
