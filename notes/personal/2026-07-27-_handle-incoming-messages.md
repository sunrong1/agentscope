## 2026-07-27 | `_handle_incoming_messages` (line 1635-1662) — W3-D1 第 4 段

**读了什么**：`src/agentscope/agent/_agent.py:1635-1662`（28 行）

**关键发现**：**这个 28 行小函数定义了 agent 输入协议的"外部边界"**。

---

### Q1（3 验证规则）✅✅ 精准

| 规则 | 条件 | 原因 |
|---|---|---|
| 1 | 不是 `Msg` 实例 | 类型必须正确 |
| 2 | `role == "system"` | system 是系统配置，不是对话消息 |
| 3 | 包含 `tool_call` / `tool_result` / `thinking` block | 内部生成的，不应外部传入 |

**你的关键洞察**：
- "system role 是系统配置，不应该是对话消息"——**这是数据契约的本质**
- "tool 和思考是内部生成的，不应该是外部传入"——**内部状态不能外部污染**

**架构师视角**：
> **"外部输入 vs 内部状态"——边界清晰**
> - 外部只能传 user/assistant 角色的"对话内容"
> - 内部状态（tool/thinking/system）由 agent 自己产生
> - **这是 inviolable 的边界**——**违反就 raise ValueError**

---

### Q2（deepcopy 必要性）✅✅ 精准

**你答**："防止调用方修改，影响到 context。最小惊讶原则。"

**真正原理**：
- Python 列表 `append` 是**引用传递**——**不复制对象**
- `state.context.append(msg)` 后——**context 里和外部的 msg 是同一个对象**
- 任何一边修改都会影响另一边——**aliasing bug**

```python
# Without deepcopy
state.context.append(msg)
msg.content.append(evil_block)  # 外部修改 → context 也变了！

# With deepcopy
copied = deepcopy(msg)
state.context.append(copied)
msg.content.append(evil_block)  # 外部修改 → context 不变 ✓
```

**Python 原则**：
- **最小惊讶原则**（Principle of Least Astonishment）——**你改它，应该只改它**
- **数据隔离**（Data Isolation）——**输入数据与内部状态分离**

**架构师视角**：
> **"deepcopy 不是性能优化——是数据隔离"**

---

### Q3（vs `_handle_incoming_event`）✅✅ 强

**你答**："event 是控制信号，msg 是对话内容。单一职责原则。"

**完美表述**：

| 函数 | 处理 | 性质 |
|---|---|---|
| `_handle_incoming_messages` | `Msg` / `list[Msg]` | **Content**（用户说什么）|
| `_handle_incoming_event` | `UserConfirmResultEvent` / `ExternalExecutionResultEvent` | **Signal**（HITL 进度通知）|

**为什么分离**：
- **Msg 的处理是"内容"逻辑**——**append 到 context**——**纯数据**
- **Event 的处理是"控制"逻辑**——**改 state / 触发 tool**——**有副作用**
- **混在一起 → 复杂 → 难测试**——**分离 → 清晰 → 可维护**

**架构师视角**：
> **"Msg = content, Event = signal"**——**这是 agent 输入协议的 2 大分类**
> - W2 学的 6 种 input（4 种 sync + 2 种 async）现在完整了：
>   - `Msg` / `list[Msg]` = content（new conversation）
>   - `UserConfirmResultEvent` / `ExternalExecutionResultEvent` = signal（HITL continuation）
>   - `UserInterruptEvent` = signal（force stop）
>   - `None` = poll（check status）

---

## 我今天最大的收获（3 个）

1. **3 验证规则的本质**——**外部输入 vs 内部状态**——**边界清晰**
2. **deepcopy 不是性能优化**——**是数据隔离**——**防止 aliasing**
3. **Msg vs Event = content vs signal**——**这是 agent 输入协议的 2 大分类**

## W3-D1 全战绩（4 段）

| 段 | 行数 | 笔记 |
|---|---|---|
| `_inject_runtime_state` | 240 | 1 |
| `_check_incoming_event` | 90 | （含在 _handle 笔记）|
| `_handle_incoming_event` | 102 | 1 |
| `_handle_incoming_messages` | 28 | 1（本文）|
| **W3-D1 合计** | **460** | **3** |

## 仍不清楚的

- **`state.context.append(msg)` 是不是真的 append**——**还是用 `_save_to_context`**——**两条路径的区别**
- **其他 input type**（`Msg` 之外的）的边界检查在哪
- **`Msg` 是不是 base class**——**`ToolMsg` / `ToolResponseMsg` / `AssistantMsg` 是子类**

## 接下来

W3-D1 完成 4 段（460 行 + 3 笔记）——**W3-D2 候选**：
- `_batch_tool_calls` (~50 行)
- `_execute_sequential_tool_calls` (~80 行)
- Q5 reproduce 脚本
