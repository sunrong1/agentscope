## 2026-07-23 | 完整 ReAct 循环(line 732-991)

**读了什么**:`src/agentscope/agent/_agent.py:732-991`(259 行 完整 ReAct)

**读了多久**:约 3.5 小时(含思考)

---

### Q1: 6 种 input 类型的真实意图

我的理解:
- 6 种 input 对应 ReAct 循环的**不同节点**
- HITL 体现在 UserConfirmResultEvent + UserInterruptEvent
- `is_awaiting` 检查 UserConfirmResultEvent + awaiting_external_executions

**判断**:✅✅ 精准。**6 种 input 不是过度设计--是"长流程可恢复"的关键**:
- 同步:Msg / list[Msg](从头开始)
- 异步:3 种 Event(从中断点继续)
- 轮询:None(继续上次)

### Q2: compress_context() 在 reasoning 之前

我的理解:推理输入的 token 更少,防止 token 爆掉。

**判断**:✅✅ 对。**"先压缩再思考"是"思考"的前提**--不压缩,**根本没有空间思考**。

### Q3: `_check_next_action` 的 action 值

我的理解:3 种 -- exit / acting / reasoning。

**判断**:✅✅ 精准。**action = 状态机下一节点**:
- exit → 推理完了,输出 Msg,return
- acting → 上一轮有 tool call 待执行
- reasoning → 上一轮是推理,现在再推一次

### Q1(新): 3 个 break flag

我的理解:
- 2 个 flag 不是过度设计--**2 种不同场景**
- `hitl` = 工具要外部确认
- `interruption` = 工具执行被中止
- UserInterruptEvent 开头已处理,**不算第 3 个**

**判断**:✅✅ 强。`break_execution_for_hitl` + `break_execution_for_interruption` = **2 种"主动停"** vs 被动"流完"。

### Q2（新）: HITL 流程的“半个 reply”

我的理解：
- 是正常退出（**暂时**）
- 下次 input 4 种可能：Confirm / Cancel / 中断 / 外部完成

**判断**：✅✅ 精准。**HITL = "reentrant 协议"**——reply 看起来结束了，**state 留着等下次的 Event 唤醒**。

---

## 🔥 深度补充：reentrant protocol 是什么

**重读 W2-D4 后，我对该问题的理解有更新——这是一个大概念，需要单独理解：**

### 普通函数 vs reentrant 函数

```python
def 普通注册(name, email):
    验证邮箱 → 保存 → return
    # 不可暂停
```

```python
async def 可重入注册(name, email, payment):
    验证邮箱
    if 需要确认:
        await 用户确认()      # ← 暂停
        await 外部支付()      # ← 再暂停
    保存 → return
    # 可以暂停多次，每次被外部事件“唤醒”后继续
```

### 3 个关键属性

| 属性 | 多步表单例子 | AgentScope HITL |
|---|---|---|
| **State 持久化** | 你填过的选项都记得 | `state.context` 留着 |
| **Resume point 明确** | “下一步”按钮 | 下次 input 必须是 Event 类型 |
| **Caller 可观测** | “等待中…”状态 | "Waiting for tool calls to be confirmed" message |

### 为什么 distributed system 必须 reentrant

- **同步**调用会锁住 worker 线程
- 1000 个用户 × 锁 1 小时 = 1000 个 worker 永远挂起
- **reentrant = 释放线程 + state 持久化 + 外部事件唤醒** = 唯一可 scale 的方式

### AgentScope 的 HITL = reentrant protocol 实现

那 4 种 input 其实是“**恢复凭证**”：
- `UserConfirmResultEvent` = “我批准/拒绝”
- `ExternalExecutionResultEvent` = “外部工具结果”
- `UserInterruptEvent` = “我不要了，强制结束”
- `Msg / list[Msg]` = “我要加新指令”

**4 种 = 4 种“如何恢复”**——不是“用户输入”，是 **reply 恢复凭证**。

### 一次完整的 HITL 对话

```
轮 1: agent.reply("给张三转 1000")
       → Agent 思考，调 tool 发现需确认
       → reply 发 "Waiting for tool calls to be confirmed..."
       （reply 结束，但 state 留着）

【你下班回家】

轮 2: 第二天 agent.reply(UserConfirmResultEvent(approved=True))
       → Agent 从上次 state 继续
       → 调转账成功
       → reply 发 "转账成功"（这次真结束）
```

**轮 1 和轮 2 是同一次"业务"**——只是被暂停了。**2 次 `agent.reply()` = reentrant**。

### 与之前笔记的关联

- W2-D2 学的 "Middleware 链" = 内部插拔机制
- W2-D3 学的 "schema-driven 管道" = 序列化机制
- **W2-D4 学的 "reentrant protocol" = 长流程架构**——是这 3 者的“上位概念”

### 怎么继续加深

- 搜 “reentrant service” / “long-running operation”
- 看 **Google Cloud Operations API LRO 模式**——他们的设计是 reentrant
- 读数据库 “savepoint” 概念——事务内的可重入点

---

### Q3/Q4: 还没答,**我帮你补**

#### Q3: `interruption_raise_cancelled_error` 配置

**默认 False** = 吞掉 CancelledError,转成 `ReplyEndEvent(INTERRUPTED)`
**True** = 重新 raise,让 CancelledError 继续传播

**为什么是配置项**:
- **False(默认)**:上层调用方(FastAPI / WebSocket)拿到的是正常的 EndEvent → **前端正常关闭连接**
- **True**:测试场景需要让 CancelledError **穿透**到测试 framework,验证取消行为

**架构师视角**:这是 **"异常吞噬 vs 异常传播" 的策略选择**--**默认安全**(不传播避免上层被意外打断),**可选严格**(用于测试)。

#### Q4: finally 只对 INTERRUPTED 调 cleanup

```python
if end_event.finished_reason == INTERRUPTED:
    async for _ in self._close_unfinished_tool_calls():
        yield _  # ← 清理
    yield AssistantMsg(content=interruption_message)
yield end_event
```

**3 种结束状态**:

| 状态 | 有未完成 tool call? | 清理? |
|---|---|---|
| COMPLETED | ❌(推理自然结束)| 不需要 |
| EXCEED_MAX_ITERS | ✅(可能)| **不清理** |
| INTERRUPTED | ✅(肯定)| **清理** |

**为什么 EXCEED_MAX_ITERS 不清理**:
- **设计哲学**:"natural stopping"--**state 留着**,**用户可以手动 resume**
- INTERRUPTED 是 "**用户/系统强行停**"--**必须清理残留**

**架构师视角**:
- COMPLETED = 完美退出(无副作用)
- EXCEED_MAX_ITERS = 自然限制(可恢复)
- INTERRUPTED = 强制中断(必须善后)

**3 种 = 3 种"责任归属"**--很优雅。

---

### 我今天最大的收获(5 个)

1. **6 种 input 类型 = 异步协议设计**--不是过度设计
2. **HITL = reentrant**--reply 可暂停可恢复
3. **action 三态 = 状态机节点**(exit / acting / reasoning)
4. **3 种结束状态 = 3 种责任归属**(自然/限制/中断)
5. **interruption_raise_cancelled_error = 异常吞噬 vs 传播**

### W2-D4 战绩

| 段 | 行数 | 笔记 |
|---|---|---|
| _reply 入口 + 中断 | 112 | 1 篇 |
| Q5 bug 怀疑 issue 草稿 | 0 (存 issue 文本) | 1 篇 |
| 完整 ReAct 循环 | 259 | 1 篇 |
| **今日合计** | **371 行** | **3 篇** |

**W2-D4 = W2 史上最猛的一天**。3 段共 371 行 + 1 个真 bug 怀疑 + 完整 ReAct 循环看懂。
