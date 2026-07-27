## 2026-07-27 | `_handle_incoming_event` (line 1533-1634) — W3-D1 第 3 段

**读了什么**：`src/agentscope/agent/_agent.py:1533-1634`（102 行）

**关键发现**：**HITL 的实际执行点**——**W2-D4 学的 reentrant protocol 概念在这里落地**。

---

### Q1（流程）⚠️ 浅

**你答了主流程**（ALLOWED/DENIED/ExternalExecutionResultEvent）——**漏了 3 个细节**：

1. **name/input 改写**（line 1580-1581）
2. **`_engine.add_rule(rule)`**（line 1584）
3. **early return**（line 1547-1548）

**完整流程**：
```
UserConfirmResultEvent:
  confirmed_tool_calls = {id: confirmation}
  遍历 last_msg 的 tool_call
    找到匹配的 tool_call
      confirmed: state → ALLOWED + name 改写 + input 改写 + add_rule
      denied: _handle_error_tool_call (yield deny event)
    pop id

ExternalExecutionResultEvent:
  遍历 execution_results
    _convert_tool_chunk_to_event → yield chunk events
    yield ToolResultEndEvent
```

---

### Q2（HITL 设计）⚠️ 浅

**你答**："HITL 设计，人始终是最终决策者"

**更深的设计**：
- 传统 HITL = **binary confirm**（"是/否"批准这个 tool call）
- AgentScope HITL = **modification allowed**（"可以改参数，甚至可以换工具"）
- **`tool_call.name = confirmation.tool_call.name`**——**用户可以换工具**
- **`tool_call.input = confirmation.tool_call.input`**——**用户可以改参数**

**架构师视角**：
> **"Confirmation ≠ approval, confirmation = collaboration"**
> - LLM 推荐"用 curl 拉 URL A"——用户**批准但改成用 wget**——**这比 binary confirm 灵活 10 倍**
> - **HITL 2.0**——**不是 ask permission，是 collaborate**

---

### Q3（rules）✅✅ 强

**你做对了**——**自己去找 `ConfirmResult` 类 verify**——**这是真学习**：

```python
class ConfirmResult:
    confirmed: bool
    tool_call: ToolCallBlock  # ← 可以 modify
    rules: list[PermissionRule] | None  # ← 可以 register
```

**add_rule 的效果**：
- 用户 approve "CreateTask" 时选"以后所有 CreateTask 都自动 approve"
- rule 进 `_engine`——**后续同类型 tool call 自动 ALLOWED**——**不用再 confirm**
- **这是 "teach agent your preferences" 模式**——**HITL 的高级形态**

---

### Q4（早期 return）✅✅ 强

**你答对**：
- `event is None` = 用户传 None = 轮询/新消息
- `context 为空` = 从未调用 reply = 初始状态
- **两者都"无需处理"——直接 return**——**"check + early return" 模式**

---

## 我今天最大的收获（4 个）

1. **`_handle_incoming_event` 只处理 2 种 event**（UserConfirmResultEvent + ExternalExecutionResultEvent）——**UserInterruptEvent 在别处**
2. **HITL 2.0 = modification allowed**——**不是 binary confirm**
3. **rules 模式**——**一次确认注册规则**——**后续自动通过**——**teach agent preferences**
4. **early return 是 fail-fast 的轻量版**——**无效输入直接 return**——**比 raise 更轻量**

## W3-D1 战绩（3 段）

| 段 | 行数 | 笔记 |
|---|---|---|
| `_inject_runtime_state` | 240 | 1 |
| `_check_incoming_event` | 90 | （含在本笔记）|
| `_handle_incoming_event` | 102 | 1 |
| **W3-D1 合计** | **432** | **2** |

## 仍不清楚的

- **`_convert_tool_chunk_to_event` 实现**——chunk → event 转换机制
- **`_engine.add_rule` 内部**——permission engine 怎么 evaluate 规则
- **`_handle_error_tool_call` 实现**——line 1590 调用，没读
- **rule 的优先级**——多个 rule 冲突怎么处理

## 接下来

W3-D1 已完成 3 段（_inject + _check + _handle）——**W3-D1 目标超额**。

**明天 W3-D2 候选**：
- `_handle_incoming_messages` (~30 行，line 1635-1662)
- `_batch_tool_calls` + `_execute_sequential_tool_calls` (~240 行, line 1663-1905)
- Q5 reproduce 脚本起步
