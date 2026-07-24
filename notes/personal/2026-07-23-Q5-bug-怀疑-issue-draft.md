# Q5 Bug 怀疑 → 确认 - Issue Draft

## 状态：✅ **已验证（2026-07-24 W2-D5）**

- 提出时间：2026-07-23（W2-D4 13:38 左右）
- 验证时间：2026-07-24（W2-D5 09:30 左右）
- 验证文件：`notes/personal/2026-07-24-_execute-tool-call-Q5验证.md`
- 结论：**是真 bug，重复 emit ToolResultStartEvent**
- 修复方案：`if call_block.state not in (ToolCallState.ALLOWED, ToolCallState.SUBMITTED):`

---

## 复现步骤（验证后）

1. 配置 `is_external_tool=True` 的工具
2. 调用 `agent.reply()` 触发该 external tool
3. 工具进入 SUBMITTED 状态（等待外部完成）
4. 用户发 `UserInterruptEvent`
5. `_close_unfinished_tool_calls` 被调用
6. 条件 `state != ALLOWED` 为 True（SUBMITTED ≠ ALLOWED）
7. 重复 emit `ToolResultStartEvent` ← **bug**

## 代码位置

- Bug 在：`src/agentscope/agent/_agent.py:705`
- 源头在：`src/agentscope/agent/_agent.py:2070-2090`（`_execute_tool_call` Case 4）

---

## 问题（已确认）

`_close_unfinished_tool_calls` 里：
```python
if call_block.state != ToolCallState.ALLOWED:
    await self._close_single_tool_call(...)
```

这里只跳过 ALLOWED 状态，**但漏掉了 SUBMITTED 状态**。**SUBMITTED 状态时 START event 已经在 _execute_tool_call 里 emit 过了**（在状态转为 SUBMITTED 之前）。**如果 SUBMITTED 状态进入 _close_unfinished_tool_calls，会重复 emit START event。**

## 理由（已确认）

- ALLOWED = 调 _execute_tool_call Case 3/4 路径
- Case 3（internal tool）：state PENDING → ALLOWED → emit START → 执行 → FINISHED
- Case 4（external tool）：state PENDING → ALLOWED → **emit START** → state ALLOWED → SUBMITTED → emit RequireExternalExecutionEvent

**Case 4 路径中，emit START 是在 ALLOWED 状态时**。**但 yield 之后 state 立刻被改为 SUBMITTED**。所以**该 START event 逻辑上同时覆盖了 ALLOWED 和 SUBMITTED 两个状态**。

## 验证结果

读 `_execute_tool_call` line 1906-2106 验证：

```python
# line 2071-2093
self._update_tool_call_state(ALLOWED)        # state → ALLOWED
yield ToolResultStartEvent(...)              # ← START emit 在 ALLOWED 状态

if tool.is_external_tool:
    self._update_tool_call_state(SUBMITTED)  # state → SUBMITTED
    yield RequireExternalExecutionEvent(...)
    return
```

**确认**：START event 在 ALLOWED 时 emit，但 event 语义覆盖 ALLOWED + SUBMITTED 两个状态。

## 修复

```python
# Before
if call_block.state != ToolCallState.ALLOWED:
    yield ToolResultStartEvent(...)

# After
if call_block.state not in (ToolCallState.ALLOWED, ToolCallState.SUBMITTED):
    yield ToolResultStartEvent(...)
```

---

## Issue 草稿（验证版，W2 末可提交）

```markdown
## Bug: Duplicate ToolResultStartEvent for external tools on interruption

### Environment
- AgentScope version: latest
- Affected file: `src/agentscope/agent/_agent.py`

### Description
When an external tool call is interrupted (e.g. user sends UserInterruptEvent 
while tool is in SUBMITTED state), `_close_unfinished_tool_calls` emits a 
second `ToolResultStartEvent` because its state check only excludes ALLOWED, 
not SUBMITTED.

### Steps to reproduce
1. Configure a tool with `is_external_tool=True`
2. Call `agent.reply()` to invoke this external tool
3. While tool is in SUBMITTED state (waiting for external completion), 
   interrupt with `UserInterruptEvent`
4. Observe: 2 `ToolResultStartEvent` events emitted (1 from 
   `_execute_tool_call`, 1 from `_close_unfinished_tool_calls`)

### Expected
Only 1 `ToolResultStartEvent` per tool call.

### Actual
2 `ToolResultStartEvent` for the same tool_call_id.

### Root cause
`_execute_tool_call` emits START while state == ALLOWED, then transitions to 
SUBMITTED for external tools. But `_close_unfinished_tool_calls` only checks 
for ALLOWED, treating SUBMITTED as "START not yet emitted".

### Proposed fix
```python
# _close_unfinished_tool_calls line 705
- if call_block.state != ToolCallState.ALLOWED:
+ if call_block.state not in (ToolCallState.ALLOWED, ToolCallState.SUBMITTED):
    yield ToolResultStartEvent(...)
```

### Suggested test
Add unit test that:
1. Mocks an external tool
2. Triggers interruption during SUBMITTED state
3. Asserts only 1 START event emitted
```
