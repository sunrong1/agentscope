## 2026-07-22 | `_compress_context_impl` 下半段（line 501-619）

**读了什么**：`src/agentscope/agent/_agent.py:501-619`

**读了多久**：约 1 小时

---

### Q1: compression_tool_schema 是假工具？

我的理解：
- 不同 LLM 输出 JSON 能力有差异，**用 function calling 更可靠**
- OpenAI 叫 Function Calling，Anthropic 叫 Tool Use
- AgentScope 用 OpenAI 风格

**判断**：✅✅ 强洞察。**Function calling > JSON 提示词** 是关键设计选择。

### Q2: 降级 2 的"丢最早消息"算法

我的理解：
- 尽量保留重要信息
- 10% 是给压缩后响应的空间

**判断**：⚠️ 方向对，**"逐步丢"是贪心优化**——`for i in range(1, N+1)` 试图找**最小 i** 让 token 满足约束。**最小 i = 最大保留**。
10% = `1 - trigger_ratio <= 0.9` = trigger 至多 0.9，至少留 10% 给 prompt。

### Q3: asyncio.shield 在保护什么？

我的理解：
- 防止 state 半更新（summary 改了但 context 没改）

**判断**：✅✅✅ 精准。**原子性保证**——apply 任务要么完整完成，要么不开始。

### Q4（自加）: 保留的 10% 怎么用？

我的理解：
- 是 LLM 响应消息的空间
- 模型不知道 10%，是 server 侧约束

**判断**：✅ 对。**预留给 response，不告诉模型**——是预估，不是 prompt 指令。

---

### 我今天最大的收获

1. **Function calling 是结构化输出的工业标准**——比 "请输出 JSON" 提示词**可靠 10 倍**
2. **"逐步丢" = 最小损失搜索**——贪心算法，**保留尽可能多的历史**
3. **asyncio.shield 是异步原子性操作**——apply 阶段不能被中断

### 跟之前的关联

- `compression_tool_schema` 用了 `cfg.summary_schema`——这个 schema 是 Pydantic 定义的（**我们在 imports 里见过 `SummarySchema` 继承 `BaseModel`**）
- 整个流程是：**Pydantic schema → JSON schema → function calling → LLM 严格输出 → Pydantic 解析**

**这是一个完整的"schema-driven"管道**。设计优雅。

### 明天要看

`_agent.py:620-...`（`_reply` 公开方法——ReAct 主循环入口）
