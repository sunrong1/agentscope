## 2026-07-24 | `_execute_tool_call` (line 1906-2106) + Q5 验证

**读了什么**：`src/agentscope/agent/_agent.py:1906-2106`（200 行 + 配合 `_close_unfinished_tool_calls` 660-735 完整理解）

**Q5 闭环了**——**W2 悬了 3 天的怀疑**今天有答案。

---

### Q1: 先 state 再 yield？

我的理解：**先修改 state 再 yield**，否则可能**重复执行**。

**判断**：✅ 对顺序；⚠️ **"重复执行"的理由太简略**——少了机制说明。

| 顺序 | 后果 |
|---|---|
| ✅ **先 state 再 yield** | 读事件者看到事件时，state 已是新值（一致性）|
| ❌ 先 yield 再 state | yield 之后控制权交出。**如果事件触发 reentrant**（HITL 模式）or 被 cancel，**state 还是旧的**——**事件和 state 不一致** |

**真正的危害不是"重复执行"**——是 **"事件已发，state 还是旧的"**：

```python
# 错误顺序示意
yield ToolResultStartEvent(...)   # ← 消费者看到事件，立刻读 state
self._update_tool_call_state(ALLOWED)  # state 这时才更新
# 这中间有个 race window：消费者读到的 state 是 PENDING/ASKING，不是 ALLOWED
```

**架构师视角**：这是 **"state-event 原子性"**——**外部观察者读到的 state 必须和 event 匹配**。**先 state 后 yield = 强保证**。

---

### Q2: START event 在 ALLOWED 还是 SUBMITTED emit？

我的理解：**ALLOWED 时 emit**——但 SUBMITTED 时这个事件**逻辑上也覆盖了**（START 标记"工具活跃期"开始，**整个 ALLOWED→SUBMITTED 都是活跃期**）。

**判断**：✅✅ 精准 + 关键洞察。**这就是 Q5 是不是 bug 的分水岭**。

**代码事实**：
```python
# line 2071-2093
self._update_tool_call_state(ALLOWED)        # state → ALLOWED
yield ToolResultStartEvent(...)              # ← 在 ALLOWED 时 emit

if tool.is_external_tool:
    self._update_tool_call_state(SUBMITTED)  # state → SUBMITTED
    yield RequireExternalExecutionEvent(...)
    return
```

**所以 START event 发出时 state 是 ALLOWED**——**但 START 之后才是 SUBMITTED**。

---

### Q3: Q5 是不是真 bug？修复？

我的理解：**是真 bug**。**修复**：把 `state != ALLOWED` 改成 `state not in (ALLOWED, SUBMITTED)`。

**判断**：✅✅ 正确 + 修复对。**Q5 验证完成**。

---

## 🎯 Q5 完整复盘

### 复现场景

```
1. Agent 调 external tool，调 _execute_tool_call
2. permission 走 ALLOW 路径：
   - state: PENDING → ALLOWED
   - emit ToolResultStartEvent     ← 第 1 次 START
   - state: ALLOWED → SUBMITTED
   - emit RequireExternalExecutionEvent
   - return
3. tool 等外部系统完成（SUBMITTED 状态）
4. 用户发 UserInterruptEvent
5. finally 块调 _close_unfinished_tool_calls
6. 遍历 ToolCallBlock，state = SUBMITTED
7. 条件: state != ALLOWED → True
8. emit ToolResultStartEvent       ← 第 2 次 START（重复！）
9. emit TextDelta + End
10. append ToolResultBlock
```

**START event 被发了 2 次**——**重复 emit bug**。

### 修复方案

```python
# Before (有 bug)
if call_block.state != ToolCallState.ALLOWED:
    yield ToolResultStartEvent(...)

# After (修复)
if call_block.state not in (ToolCallState.ALLOWED, ToolCallState.SUBMITTED):
    yield ToolResultStartEvent(...)
```

### 为什么不只是改代码？——**架构师视角**

**为什么会出这个 bug**：

1. **设计假设错误**："ALLOWED" 被等同于"START 已 emit"
2. **实际情况**：external tool 的活跃生命周期 = `ALLOWED + SUBMITTED`
3. **遗漏的中间态**：**没人想到"ALLOWED 之后还有 SUBMITTED"**——因为内部工具没有这个状态

**根因**：**`_close_unfinished_tool_calls` 的设计假设和 `_execute_tool_call` 的状态机对不齐**——**两套独立设计的代码，没考虑彼此**。

**更深层教训**：
- **bug 报告要包含"为什么设计意图是 X，但代码实际是 Y"**——不是只说"加个条件"
- **issue 标题**：`[Bug] Duplicate ToolResultStartEvent for external tools on interruption`

---

## Q5 Issue 草稿更新（待提交）

**完整 issue 草稿**（之前是怀疑版，现在是确认版）：

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
Add unit test in `_agent.py` or new test file that:
1. Mocks an external tool
2. Triggers interruption during SUBMITTED state
3. Asserts only 1 START event emitted
```

---

## W2-D5 战绩

| 项 | 数字 |
|---|---|
| 阅读 | 200 行（**1 段**）|
| 笔记 | 1 篇 |
| 答问题 | 3 道（Q1/Q2/Q3）|
| **Q5 验证** | **闭环**——**真 bug + 修复方案 + 完整复盘** |

**Q5 是 W2 最大的金矿**——**从怀疑到确认到修复方案到 issue 草稿**全链跑通。

## 仍不清楚的

- **`_update_tool_call_state` 的实现**——是直接赋值还是 thread-safe lock？**多 thread 场景下 state 可能 race condition**
- **`RequireExternalExecutionEvent` 后续路径**——external 工具完成时怎么**回到 ALLOWED/FINISHED**？——**line 2200+ 还没读**
- **issue 草稿还需要 reproduce 脚本**——**目前是逻辑推演，不是真 reproduce**——**如果 W2 结束前能写个 unit test 跑出来，issue 质量提升 10 倍**

## 明日（W2-D6）计划

**W2-D6 = 7-25 自由日**——**今天 W2-D5 主线已收**，D6 自由。
