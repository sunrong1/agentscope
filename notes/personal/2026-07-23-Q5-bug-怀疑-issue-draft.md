## 2026-07-23 | Q5 bug 怀疑 + Issue 草稿（待 W2 末决定）

### 起源

W2-D4 读 `_close_unfinished_tool_calls`（line 620-732）时，发现一个**可能 bug**：

> `_close_unfinished_tool_calls` 里 `if call_block.state != ToolCallState.ALLOWED` 这个检查**只排除 ALLOWED 状态**，但**没排除 SUBMITTED 状态**。
> 状态机是 `ASKING → ALLOWED → SUBMITTED → FINISHED`——
> ALLOWED 时 START event 已 emit，**SUBMITTED 时也是（早就在 ALLOWED 时发了）**。
> 所以 SUBMITTED 状态下会被**重复 emit START event**。

### 验证状态

| 检查项 | 状态 |
|---|---|
| ToolCallState 真实枚举 | ✅ 已确认（PENDING, ASKING, ALLOWED, SUBMITTED, FINISHED）|
| ALLOWED 之前是 ASKING | ✅ 已确认（from `_execute_tool_call` line 1996+）|
| ALLOWED → SUBMITTED 状态转换存在 | ✅ 已确认（line 2093 附近）|
| `ToolResultStartEvent` 是在 ALLOWED 时 emit | ⚠️ **未完全验证**（需要读 `_execute_tool_call` 完整流程）|
| **真 reproduce** | ❌ **未做**（没跑过实际场景）|

**结论**：**怀疑成立的可能性大**，但**未 reproduce 过的 issue 会被 maintainer 关闭**。

---

## Issue 草稿（待 W2 末 reproduce 后再发）

### Title
`[BUG] _close_unfinished_tool_calls: duplicate ToolResultStartEvent for SUBMITTED state`

### Labels
`bug`, `agent`, `core`, `needs-reproduction`

### Body

```markdown
[BUG]

## Background / Description

While studying `src/agentscope/agent/_agent.py`, I noticed a potential 
bug in `_close_unfinished_tool_calls()` (line 670). This method is called 
in the `finally` block of `_reply_impl()` when a reply is interrupted 
(`ReplyFinishedReason.INTERRUPTED`), to close any "orphan" tool calls 
that don't have a corresponding tool result.

The issue is in this check at **line 705**:

```python
# An ALLOWED call was already running, so its START was already
# emitted — skip it here (checked before flipping to FINISHED).
if call_block.state != ToolCallState.ALLOWED:
    yield ToolResultStartEvent(
        reply_id=self.state.reply_id,
        tool_call_id=last_msg.content[index].id,
        tool_call_name=last_msg.content[index].name,
    )
```

The comment says: "An **ALLOWED** call was already running, so its 
START was already emitted".

However, the `ToolCallState` enum has 5 states (from 
`src/agentscope/message/_block.py`):

```python
class ToolCallState(StrEnum):
    PENDING = "pending"
    ASKING = "asking"
    ALLOWED = "allowed"
    SUBMITTED = "submitted"
    FINISHED = "finished"
```

The state machine progression is: 
`ASKING → ALLOWED → SUBMITTED → FINISHED`. 
Once a tool call reaches `ALLOWED`, the `ToolResultStartEvent` is 
emitted (when entering ALLOWED). When it later transitions to 
`SUBMITTED`, **the tool is still executing** — the START event was 
emitted long before.

The current check `if call_block.state != ToolCallState.ALLOWED` only 
excludes the `ALLOWED` state. This means when a tool call is in 
`SUBMITTED` state (actively executing) and gets interrupted, this code 
will **re-emit a duplicate `ToolResultStartEvent`** for a tool whose 
execution has already started.

## Expected Behavior

When a tool call is interrupted, the cleanup should:
1. Emit `ToolResultStartEvent` only for states where execution has 
   **not** yet started (i.e., `PENDING`, `ASKING`)
2. Skip `ToolResultStartEvent` for states where it was already emitted 
   (i.e., `ALLOWED`, `SUBMITTED`)
3. Emit `ToolResultTextDeltaEvent` and `ToolResultEndEvent` for all 
   states (to close the lifecycle)
4. Set final state to `FINISHED`

## Actual Behavior (Suspected)

For a tool call in `SUBMITTED` state at interruption:
- A duplicate `ToolResultStartEvent` is emitted (already emitted when 
  state entered ALLOWED)
- This may cause downstream consumers (UI / SSE clients / tracers) to 
  see a **start → end** sequence without a corresponding 
  **start → submitted → finished** lifecycle, breaking the state 
  machine contract.

## Steps to Reproduce

> ⚠️ **I have not yet reproduced this in a running session** — the 
> analysis is based on code reading. The reproduction steps are my 
> best guess and need verification.

1. Set up an Agent with a tool that takes time to execute 
   (e.g., a Bash tool calling `sleep 5`)
2. Trigger the tool via `agent.reply(...)` or `agent.reply_stream(...)`
3. Wait for the tool call to reach `SUBMITTED` state (e.g., poll 
   `state.context[-1].content` while it's executing)
4. **Interrupt** the reply (e.g., `asyncio.cancel()` or send a 
   `UserInterruptEvent`)
5. The `finally` block calls `_close_unfinished_tool_calls()`
6. Observe: Two `ToolResultStartEvent`s are emitted for the same 
   `tool_call_id`

## Environment

- AgentScope version: 2.0.4.post1 (commit `30ca3ef`)
- Python: 3.11+
- Affected file: `src/agentscope/agent/_agent.py`
- Affected lines: ~705-710 (the `if call_block.state != 
  ToolCallState.ALLOWED` check)

## Proposed Fix

```python
# Before
if call_block.state != ToolCallState.ALLOWED:
    yield ToolResultStartEvent(...)

# After (Option A: explicit set)
if call_block.state not in (
    ToolCallState.ALLOWED,
    ToolCallState.SUBMITTED,
):
    yield ToolResultStartEvent(...)

# After (Option B: explicit positive states)
if call_block.state in (
    ToolCallState.PENDING,
    ToolCallState.ASKING,
):
    yield ToolResultStartEvent(...)
```

Both options exclude `ALLOWED` AND `SUBMITTED`, since both have 
already had their `ToolResultStartEvent` emitted.

## Additional Notes

- The fix is **forward-compatible** — it doesn't break any existing 
  behavior, only adds a stricter check
- A regression test would be needed: interrupt a reply during 
  `SUBMITTED` state and assert that `ToolResultStartEvent` is emitted 
  **exactly once** per `tool_call_id`
- This bug does **not** cause data loss, but may cause UI/state 
  inconsistencies in downstream consumers

## How I Found This

I'm currently studying AgentScope's source code via a public learning 
journal (blog post series). During a code review of 
`_close_unfinished_tool_calls`, I noticed the state check only 
excluded `ALLOWED` but not `SUBMITTED`. Cross-referencing with the 
`ToolCallState` enum definition revealed the gap.
```

---

## 后续行动（到 W2 末）

1. **完成 W2 学习**（读完 `_agent.py` 至少 50%）
2. **写 reproduce 脚本**（基于 issue "Steps to Reproduce"）
3. **真跑过** → 确认是 bug 还是我误判
4. **写测试**（如果 reproduce 成功）→ 提 PR
5. **如果发现不是 bug**（我读错了）→ 在这里记下"我误判了"，**重要**——这是反例最有教育意义

## 反思

**这是 W2 第一次"产出"类型的学习**——之前都是"读懂"（学），这次是"找问题"（用）。
**真正的工程师学习 = 学 + 用 + 怀疑 + 验证**。

如果 W2 末能 reproduce + 提 PR，**这将是 8 周公开承诺的最大亮点**——**比"读完 1 个核心类"更有说服力**。
