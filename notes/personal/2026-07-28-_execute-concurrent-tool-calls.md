## 2026-07-28 | `_execute_concurrent_tool_calls` (line 1765-1895) — W3-D2 第 3 段

**读了什么**：`src/agentscope/agent/_agent.py:1765-1895`（131 行）

**关键发现**：**这是 AgentScope 异步架构的核心**——**用 data flow（events）替代 control flow（exceptions）**。

---

### Q1（sentinel pattern）✅✅ 精准

**你答**："独一无二，哨兵模式"

**为什么必须独一无二**：
- Worker 可能 yield **任何**对象
- 如果 sentinel = `True` / `None` / `"end"`——**worker 真的产出这个值**——**循环错误结束**
- `object()` 创建的对象**类型是 `<class 'object'>`**——**Worker 不可能产出这种类型**——**100% 安全**

**架构师视角**：
- **`object()` 是 Python 的"魔法 token"**——**类似 None/True/False 但是"私有"**
- 任何人都能产 None，但**没人能产 `object()` 实例**（除非显式创建）
- **这是 "namespace isolation"**——**类型系统保护 sentinel**

---

### Q2（ExceptionGroup）⚠️ 浅

**你答**："并行不互相影响"

**更深的设计哲学**——**"fail-comprehensive" vs "fail-fast"**：

| 策略 | 行为 | 优点 | 缺点 |
|---|---|---|---|
| **fail-fast** | 遇到第一个 raise 立即停止 | 快速失败 | **只看到 1 个问题**——**其他 5 个被掩盖** |
| **fail-comprehensive** | 等所有完成 + `ExceptionGroup` | **看到所有问题** | 慢一点 |

**AgentScope 选 fail-comprehensive**——**为什么**：
- **多 tool 并行**——**1 个失败不应该让其他 4 个白跑**
- **`ExceptionGroup` 一次性报所有**——**debugging 友好**
- **vs 一次次 raise**——**一次次 raise 让人崩溃**

---

### Q3（uncancel + data flow）✅✅ 强

**你抓到了核心**："用 events 代替 exceptions"

| 模式 | 描述 | 适用 |
|---|---|---|
| **Control flow** (exceptions) | 异常是"控制信号" | 同步、阻塞场景 |
| **Data flow** (events) | 事件是"数据信号" | 异步、流式场景 |

**为什么 AgentScope 选 data flow**：
- **异步 generator**——**events 是 yield 出来的"值"**——**不是 raise 出来的"信号"**
- **调用方不需要 try/except**——**只管 iterate**——**更简单**
- **同一个 generator 既传正常 events 又传 INTERRUPTED events**——**统一处理**

**架构师视角**：
> **"Modern async framework 都用 data flow 替代 control flow"**
> - asyncio CancelledError 是过渡方案
> - AgentScope **进一步用 events 替代**——**callers 更简单**
> - **这就是 "uniform event-based async pattern"**

---

## 我今天最大的收获（3 个）

1. **sentinel = `object()`**——**类型系统保护 namespace**
2. **fail-comprehensive > fail-fast**——**ExceptionGroup 友好 debugging**
3. **data flow > control flow**——**events 替代 exceptions**——**W3-D2 最大概念**

## W3-D2 全战绩（3 段）

| 段 | 行数 | 笔记 |
|---|---|---|
| `_batch_tool_calls` | 38 | 1 |
| `_execute_sequential_tool_calls` | 50 | （含）|
| `_execute_concurrent_tool_calls` | 131 | 1 |
| **W3-D2 合计** | **219** | **2** |

## 仍不清楚的

- **`_into_queue` 实现**（line 1897+）——**怎么把 tool call 包装成 queue producer**
- **`kept_rules` 怎么用**——**HITL de-duplication 完整流程**
- **`asyncio.current_task().uncancel()` 内部机制**——**Python 3.9+ 才有的 API**
- **gather cancel 后的内部 cleanup**——**Python 异步运行时怎么清理**

## 接下来

W3-D2 完成 3 段（219 行 + 2 笔记）——**W3-D3 候选**：

| 段 | 内容 | 行数 |
|---|---|---|
| A | `_into_queue` (line 1897+) | ~10 行 |
| B | `_execute_tool_call` (line 1906+, 完整 W2-D5 看过的，再读一次) | ~290 行 |
| C | Q5 reproduce 脚本 | 1-2h |
| D | 切换到 W4 模块（消息与通信） | 全新模块 |

**我建议 D**——**W3 agent 基类完成**——**W4 切到新模块**——**新鲜感**——**更高吸收率**。

**或者 C**——**W2 留的债**——**issue 增强**。

**你定？**
