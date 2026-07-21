## 2026-07-21 | Agent 类 4 个公开方法（line 195-275）

**读了什么**：`src/agentscope/agent/_agent.py:195-275`

**读了多久**：约 40 分钟

---

### Q1: 为什么 `reply_stream` + `reply` 两个方法？

我的理解：
- 两个都是公共 API
- `stream` 流式输出（实时显示）
- `reply` 一次性返回最终消息

`if not isinstance(chunk, Msg)` 的含义：如果不是 msg 类型。

**判断**：⚠️ 方向对，差细节。**`reply_stream` 故意不 yield 最终 Msg**——只 yield events（tool call / text delta 等）。最终 Msg 必须调 `reply()` 拿。

设计意图（我猜）：events 和 Msg 是两类东西，**不该混在同一条流**。

### Q2: 多个 Msg / 0 个 Msg？

我的理解：
- 多个 Msg → 只保留最后一个
- 0 个 Msg → `RuntimeError`
- 合理：最终是 assistant 消息，中间是 tool call 消息

**判断**：✅✅ 强洞察。**从 import 里的 `ToolCallBlock` / `ToolResultBlock` 推出** "中间过程是工具消息"。

### Q3: 1 行 wrapper 的架构名？

我的理解：**Facade 模式（门面）**。隐藏内部实现，保持外部接口简洁。

**判断**：✅ 对。但更精确：`observe` 是 Facade 的极简形态（纯 1 行委托）。标准 Facade 通常会做更多加工。

### Q4: Facade vs Adapter 区别？

我的理解：
- **Facade**：隐藏内部复杂，**对外提供简单接口**（多合一）
- **Adapter**：接口不兼容，**做格式/协议转换**（变接口）

**判断**：✅✅ 教科书答案。区分得很准。

---

### 我今天最大的收获

1. **Facade vs Adapter 的实操区分**——"简化" vs "兼容"两字说清
2. **设计意图要追问 "为什么这么写"**——`reply_stream` 主动过滤 Msg 不是 bug，是**有意的**
3. **从 imports 反推行为**——看到 `ToolCallBlock` 就该想到"reply 流里会有这些中间事件"

### 我之前没想到的

- 我以为 `reply_stream` 会 yield 所有东西（events + Msg），**没想过它会主动过滤**。这是我没读代码时**想象不到**的设计细节。

### 明天要看

`_agent.py:275-320`：`compress_context` 方法（带 middleware 链）
