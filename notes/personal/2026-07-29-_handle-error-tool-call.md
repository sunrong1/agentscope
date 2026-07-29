## 2026-07-29 | `_handle_error_tool_call` (line 2297-2366) — W3-D3 第 1 段

**读了什么**：`src/agentscope/agent/_agent.py:2297-2366`（75 行）

**关键发现**：**"error is also a result"**——**uniform type pattern**——**让 error 走 streaming protocol 同一管道**。

---

### Bonus（何时调用）✅✅ 强

**调用点**：
- `_execute_tool_call` line 1968: tool not found / input invalid / permission DENY
- `_handle_incoming_event` line 1590: 用户 confirm = false

**两种 error 场景都用同一函数**——**本身就是 uniform type pattern**。

---

### Q1（synthetic ToolChunk）✅✅ 强

**你答**："统一接口 / 归一化 / error 也是 result"

**技术名**：**"Uniform Type Pattern"** 或 **"Type Normalization"**

**为什么不让 error 走单独路径**——**反面假设**：
- 假设有 `handle_error_tool_call` 和 `handle_normal_tool_call` 两个函数
- 调用方需要：`if error: handle_error() else: handle_normal()`——**麻烦**
- **新加 error 类型**（TIMEOUT）——**要改所有 consumer**——**扩展性差**
- **event 类型不统一**——**下游处理两套**

**统一后**：
- 所有 result（成功/失败/拒绝）yield 同一组 events
- 消费方只处理 1 套——**简单**
- 扩展新 type——**只改 state 参数**——**不改 protocol**

**架构师视角**：
> **"Uniform interface > Specific interface"**
> - HTTP status code（200/404/500）= uniform
> - AgentScope 把 success/error 归一化成"tool result lifecycle"

---

### Q2（5 步顺序）⚠️ 浅

**你答**："如果调换会出现状态机逻辑处理异常"

**具体调换会破坏什么**：

| 调换 | 破坏什么 |
|---|---|
| End event 在 save_to_context **之前** | consumer 看到 End event → 但 context 没更新 → **再读 context 看不到结果** |
| Update state 在 End event **之前** | consumer 收到 EndEvent 时 → state 已经是 FINISHED → **但 EndEvent 携带 state 应该还是 ALLOWED**——**不一致** |

**架构师视角**——**State-Event Atomicity**：
> **"每个 event 出现时，state 必须是确定的"**
> - 收到 StartEvent → state 应该是 ALLOWED
> - 收到 EndEvent → state 还是 ALLOWED
> - **不能"state 提前"或"state 滞后"**

**这跟 reentrant protocol 一脉相承**——**state-event 一致性**。

---

### Q3（state update 最后）⚠️ 浅

**你答**："状态机一致性 / 先 state 变更 event 处理不了"

**更深的设计**：
- **EndEvent 携带 `state` 字段**——`ToolResultEndEvent(state=ERROR/DENIED)`
- 消费方收到 EndEvent 时**信任这个 state**——**不查内部**
- **如果 state 已更新到 FINISHED**——**EndEvent 的 state 字段就矛盾**

**架构师视角**：
> **"State 字段在 events 里 = 协议契约"**
> - 消费方**只信 event 里的 state**——**不查内部**
> - 内部 state 可以更新——**但要等 event 发完之后**
> - **"先 protocol, 后 internal state"** = **protocol-first design**

---

## 我今天最大的收获（3 个）

1. **error is also a result**——**uniform type pattern**——**和 HTTP status code 思路一致**
2. **state-event atomicity**——**每个 event 出现时 state 必须确定**——**W2 学的"先 state 再 yield"反着来**
3. **protocol-first design**——**先发 event 完，再更新内部 state**——**契约驱动**

## W3-D3 第 1 段战绩

| 项 | 数据 |
|---|---|
| 阅读 | 75 行 |
| 笔记 | 1 篇 |
| 答问题 | 3 + 1 bonus |
| 概念 | uniform type + state-event atomicity + protocol-first |

## 仍不清楚的

- **`_into_queue` 完整 22 行**（line 1897-1917）——W3-D1 提过没读
- **`_acting` middleware hook**（line 2200-2295）——**W2 提过，没读**
- **`_split_context_for_compression`**（line 2370+）——W2-D3 提过——**复杂**
- **`_call_model` + `_prepare_model_input`**（line 2700+）——**model 适配层**

## 接下来

W3-D3 第 1 段完成（75 行 + 1 笔记）——**W3 收尾进度 1/3**。

**W3-D3 第 2 段候选**：
- `_acting` (~80 行) - middleware hook
- `_into_queue` (~22 行) - 太小不合适
- 切 W4 消息模块

**我建议读 `_acting`**——**W3 收尾最有价值的段**——**理解 middleware 怎么 hook 进 tool execution**。
