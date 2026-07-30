## 2026-07-30 | `_into_queue` + `_split_context_for_compression` — W3-D4 第 1 段

**读了什么**：
- `_into_queue` line 1897-1917 (22 行)
- `_split_context_for_compression` line 2372-2466 (95 行)

**关键发现**：**context compression 是 W2-D3 学的 schema 驱动的"具体实现"**——**多层粒度 + 事务原子性**。

---

### Q1（3 层 split 策略）✅✅ 强

**你答**："逐层细化，粗到细"

**技术名**：**"Hierarchical Refinement"** 或 **"Coarse-to-fine"**

| 粒度 | 适用场景 | 精度 |
|---|---|---|
| **msg 级** | 一条 msg 整个超出 | 粗 |
| **block 级** | msg 内部分 block 超出 | 中 |
| **tool pair 级** | 防止破坏原子性 | 细 |

**只用 msg 级**——**结果**：
- 假设 msg M 有 3 个 block（call → result → 总结）
- msg 级判断 M 应该保留
- 但 block 级：call 在前，result 在后，token 多——**call 必须 compress**——**msg 级做不到**

**架构师视角**：
> **"Multi-level granularity = precision"**——**不抽象的代价是粒度不够**
> - Q1 昨天学"Duplication > Wrong Abstraction"
> - 今天学"多层级 > 单层级"
> - 两者都"具体 > 抽象"——**哲学一致**

---

### Q2（tool pair 不变式）⚠️ 浅

**你答**："切了让模型疑惑"

**真正 bug**：

```python
# Compress 后 reserved 部分：
[ToolResultBlock(tool_call_id="tc_001", output="用户余额 100 元")]
# ToolCallBlock 已经在 compress 部分
# LLM 看到这条 msg：
"Tool result: 用户余额 100 元"
# LLM 没看到 "Tool call: query_balance"
# 两种 bug：
#   1. 困惑 → 幻觉（"我没调用过这 tool 啊"）
#   2. 假设是 system message → 误解语义
```

**核心 bug**：**破坏 "cause → effect" 链**——**LLM 看到 effect 不知道 cause**——**推理错乱**。

**架构师视角**：
> **"Tool call/result 是 distributed transaction 的"**
> - call = request
> - result = response
> - **事务原子**——不能 request 在一边，response 在另一边
> - **context compression 破坏事务原子 = corrupted state**

---

### Q3（convergent 算法）⚠️ 浅

**你答**："block 依赖复杂"

**为什么必须"反复"**——**举例**：

```
初始 boundary（block 12）：
  Reserved: [..., ToolResult(tc_001), ToolCall(tc_002), TextBlock("ok")]
  Compressed: [ToolCall(tc_001), TextBlock("...")]

检查：ToolResult(tc_001) 没有对应 ToolCall(tc_001) → 不变式破坏
动作：把 ToolResult(tc_001) 移到 compressed

新 boundary（block 8）：
  Reserved: [..., ToolCall(tc_002), TextBlock("ok")]
  Compressed: [ToolCall(tc_001), TextBlock("..."), ToolResult(tc_001)]

又检查：ToolCall(tc_002) 没有对应 ToolResult(tc_002) → 又破坏！
动作：把 ToolCall(tc_002) 移到 compressed

新 boundary（block 5）：
  Reserved: [..., TextBlock("ok")]
  Compressed: [ToolCall(tc_001), TextBlock("..."), ToolResult(tc_001), ToolCall(tc_002)]

检查：TextBlock("ok") 不在 tool pair 检查 → 通过
退出
```

**为什么必须终止**——**数学证明**：
- 每次循环**只把 block 从 reserved 移到 compressed**——**单调减少**
- reserved 是**有限的**
- 必然在某次循环后 reserved = [] 或没有 orphan
- **Convergent = monotone + finite** = **必然终止**

**架构师视角**：
> **"Convergent algorithm = monotone + finite"**
> - monotone 方向：reserved 越来越小
> - 有限集合：blocks 有限
> - **terminated = guaranteed**

---

## 我今天最大的收获（3 个）

1. **Hierarchical Refinement**——**多层级粒度 = precision**
2. **Tool pair = distributed transaction**——**事务原子性不能破坏**
3. **Convergent algorithm = monotone + finite**——**终止性可证**

## W3-D4 第 1 段战绩

| 项 | 数据 |
|---|---|
| 阅读 | 117 行（_into_queue 22 + _split 95）|
| 笔记 | 1 篇 |
| 答问题 | 3 道（1 强 + 2 浅）|
| 概念 | 多层粒度 + 事务原子 + 收敛算法 |

## W3 收尾进度

| 已完成 | 待完成 |
|---|---|
| ✅ _handle_error_tool_call | _split_tool_result_for_compression |
| ✅ _acting | _clear_unreserved_read_cache |
| ✅ _into_queue | _get_system_prompt |
| ✅ _split_context_for_compression | _prepare_model_input |
| | _call_model |

**完成 4/9 段**——**还剩 5 段约 250 行**。

## 仍不清楚的

- **`_split_tool_result_for_compression`** 跟 `_split_context_for_compression` 的关系
- **`is_state_injected` 的实际工具**——**state-injected 怎么 inject state**
- **token count 是 LLM 算还是本地算**——**`count_tokens` 怎么实现**
- **`SystemMsg` vs `UserMsg` 在压缩中的作用**——**system 永远不压缩？**

## 接下来

W3-D4 第 1 段完成（117 行 + 1 笔记）——**W3 收尾进度 4/9**。

**W3-D4 段 2 候选**：
1. `_split_tool_result_for_compression`（~150 行）——大段
2. `_prepare_model_input` + `_call_model`（~80 行）——model 适配
3. 切 W4 消息模块

**我建议 1**——**completion 路径完整**——**为 W3 收尾**。

**但今天 22:00**——**已经 13.5h 工作**——**应该收工**——**明天读段 2**。

**你定？**
