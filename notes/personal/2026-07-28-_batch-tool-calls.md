## 2026-07-28 | `_batch_tool_calls` (line 1675-1713) — W3-D2 第 1 段

**读了什么**：`src/agentscope/agent/_agent.py:1675-1713`（38 行）

**关键发现**：**这个函数是 RLE（Run-Length Encoding）算法**——**把 LLM 的 tool call 序列压缩成 batch 序列**。

---

### Q1（2 属性）✅✅ 强

**你抓到 docstring bug**：
- docstring 说：`is_concurrency_safe` AND `is_read_only`
- 代码只用：`is_concurrency_safe`
- **`is_read_only` 完全没用**——**注释和实现对不齐**

**潜在影响**：
- 如果 `is_read_only=True` 但 `is_concurrency_safe=False`——**会被归到 sequential**——**应该可以并发但没并发**
- **这是 Q5 级 issue 候选**——**值得研究**

---

### Q2（unknown tool）✅✅ 精准

**你答**："未注册工具 A, B, C → concurrent → 执行时 None → block"

**代码 (line 1690-1692)**：
```python
# Treat unregistered or unavailable tools as concurrent tools since
# it will not generate side effects and be blocked with acting
if tool is None or tool.is_concurrency_safe:
```

**架构师视角**：
- 未知 tool = 不可执行 = 无副作用 = **safe**
- 放 concurrent **不会污染 state**（即使失败）
- **"fail-safe 假设"**——unknown = safe = concurrent

**vs "fail-secure"**：
- 严格模式应该把 unknown 当 sequential
- AgentScope 选 fail-safe——**为了不让单个 unknown 卡住整个 batch**

---

### Q3（batch 排序）✅✅ 精准

**你答**："保持原顺序，相邻同类型合并"——**RLE 算法**

| LLM 输出 | Batch 后 |
|---|---|
| [C, C, S, C, C, S, S, C] | [C(2), S(1), C(2), S(2), C(1)] |

**8 个 tool call → 5 个 batch**（减少 37%）

**为什么这样设计**：
- **LLM 输出顺序 = 推理顺序**——**有意义**（不能乱）
- **同类合并 = 减少 batch 数 = 减少 dispatch 次数**
- **保留顺序 = 尊重 LLM 决策**——**不重排**

**架构师视角**：
> **"Batching 是 RLE，不是 sort"**
> - sort 会改变 LLM 决策
> - RLE 只压缩类型
> - **这就是 "honor the LLM's order, but reduce dispatch overhead"**

---

## 我今天最大的收获（3 个）

1. **RLE 算法应用**——**batching 是数据压缩**
2. **fail-safe vs fail-secure 哲学选择**——**AgentScope 选 fail-safe**
3. **docstring 与实现对不齐**——**可能是个 issue 候选**

## W3-D2 第 1 段战绩

| 项 | 数据 |
|---|---|
| 阅读 | 38 行 |
| 笔记 | 1 篇 |
| 答问题 | 3 道（3 强）|
| 发现 | **docstring bug**（Q5 级候选）|

## 仍不清楚的

- **`_ToolCallBatch` 类定义在哪**——**type 字段是 enum 还是 str**
- **`is_read_only` 在哪里被用**——**其他函数？**
- **`_execute_sequential_tool_calls` 和 `_execute_concurrent_tool_calls` 的具体差异**
- **`is_concurrency_safe` 默认值**——**True / False / per-tool**

## 接下来

**W3-D2 第 2 段候选**：

| 段 | 内容 | 行数 |
|---|---|---|
| A | `_execute_sequential_tool_calls` | ~80 行 |
| B | `_execute_concurrent_tool_calls` | ~150 行（line 1752-1900）|
| C | 写 Q5 reproduce 脚本 | 60-90min |

**我建议 A**——**先 sequential**——**B 是 concurrent**——**两者对比学**。

**或者 C**——**Q5 闭环**——**W2 留的债**。

**你定**？
