## 2026-08-09 | `tool/_base.py` ToolBase — W5-D1 第 2 段

**读了什么**：`src/agentscope/tool/_base.py` (451 行)

**关键发现**：**Tool 抽象核心——3 个核心类 + 5 大设计点**。

---

### 3 个核心类

```
ParamsBase:           Pydantic BaseModel + 去掉 title 字段（轻量版 JSON schema）
ToolMiddlewareBase:   1 个抽象方法 on_tool_call（onion 模型）
ToolBase:             11 字段 + 5 方法（核心抽象）
```

### ToolBase 11 字段（5 boolean 标志！）

```python
name / description / input_schema
is_concurrency_safe / is_read_only / is_external_tool / is_state_injected / is_mcp
mcp_name
dangerous_files / dangerous_directories  # class-level
```

### 关键设计：call() vs __call__()

```python
async def call(self, **kwargs) -> ToolChunk | AsyncGenerator:
    """Subclass override point"""
    if not self.is_external_tool:
        raise NotImplementedError(...)
    raise RuntimeError(...)

async def __call__(self, **kwargs):
    """Template method - applies middleware chain"""
    if not self._middlewares:
        return await self.call(**kwargs)
    # 递归 onion chain
    return execute_chain(0, **kwargs)
```

### Onion 中间件链

```python
mw[0] → mw[1] → tool.call() → mw[1] post → mw[0] post
```

---

### Q1（5 boolean 标志 vs 5 子类）✅✅ 强

**你答**："boolean 简洁 / 组合爆炸 / 管理困难"

**架构师视角**：

> **"Boolean flags = aspect-oriented composition"**（boolean 标志 = 面向方面组合）
> - **5 个 bool 不是 5 种类型**——**是 5 个 aspect（方面）**
> - **Type 思维**：这个 tool 是什么**类**？
> - **Aspect 思维**：这个 tool 有什么**能力/特征**？
> - **AgentScope 选 aspect 思维**——**因为 5 个维度互不互斥**——**可以任意组合**

**vs 5 子类**：

| 维度 | 5 boolean | 5 单继承 | 5 多继承 mixin |
|---|---|---|---|
| 组合数 | 2^5 = 32 | 5 | 31 |
| 灵活性 | 最高 | 最低 | 高 |
| 复杂度 | 低 | 中 | 高（菱形）|
| 新增维度 | + 1 bool（0 改）| + 1 抽象类 | + 1 mixin |

**判断标准**：
- 维度互斥 → 用继承
- 维度可组合 → 用 boolean

---

### Q2（call() vs __call__() 两层抽象）✅✅ 强

**你答**："分两层 / 防子类忘 / 行为一致"

**架构师视角**：

> **"Template Method = Compiler-enforced invariant"**（模板方法 = 编译期不变量）
> - **不用"提醒"子类"记得加 middleware"**——**结构上强制**
> - **不用"code review 检查"**——**基类已经做了**
> - **Type system + base class = 强制一致性**——**bug 不会发生**

**方案 A 的风险**（只用 __call__）：
1. 忘了 super().__call__() → middleware 链断
2. 忘了 apply_middleware() → 权限失效——**安全风险**
3. 新人写 tool 默默出错

**vs W4 ChatModelBase 同源**：

| W4 ChatModelBase | W5 ToolBase |
|---|---|
| `_call_api()` 子类实现 | `call()` 子类实现 |
| `__call__()` retry + 流式包装 | `__call__()` middleware 包装 |
| Invariant: 每次调 LLM 都 retry | Invariant: 每次调 tool 都过 middleware |

---

### Q3（onion middleware 递归 vs 循环）✅✅ 强

**你答**："作者觉得递归简洁 / 我觉得循环清晰"

**架构师视角**：

> **"Recursion + continuation = future-proof"**（递归 + 续体 = 面向未来）
> - **今天中间件简单**——**但 framework 不知道未来用户怎么用**
> - **递归写法的"next_handler 是闭包"**支持任意复杂逻辑
> - **循环写法的"pre × N + post × N"**锁死了结构

**递归 vs 循环的灵活性**：

| 中间件能做的事 | 递归 | 循环 |
|---|---|---|
| 调 next_handler 继续 | ✅ | ✅ |
| 不调（拦截跳过 tool）| ✅ | ❌ |
| 调多次（重试）| ✅ | ❌ |
| 修改 kwargs | ✅ | ⚠️ |
| 调完 next_handler 后 yield 自己的结果 | ✅ | ⚠️ |

**"洋葱"对调用方透明**：

| 调用方视角 | 体验 |
|---|---|
| `tool(arg)` 一行 | 不知道有 middleware |
| 中间件从哪来 | 调用方传 `middlewares=[...]` |
| 中间件加在哪 | 内部 `execute_chain` 透明 |
| 错误从哪冒 | 任意层——**调用方不用关心** |

---

## 我今天 3 个最大收获

1. **Boolean flags = Aspect-oriented composition**（5 bool 互不互斥——Type vs Aspect 思维）
2. **Template Method = Invariant Protection**（防忘——结构强制 vs 提醒）
3. **Recursion + continuation = future-proof**（洋葱透明——框架选灵活）

## W5-D1 段 2 战绩

| 数据 | 数字 |
|---|---|
| 行数 | 451 |
| 笔记 | 1（本文）|
| 答 | 3 |
| 强 | 3 |
| 浅 | 0 |
| 缺 | 0 |
| 评分 | **9.0/10** |

## W5 累计战绩

| 段 | 文件 | 行数 | 笔记 | 强 |
|---|---|---|---|---|
| W5-D1 段 1 | skill/_local_loader.py | 172 | 1 | 2 |
| **W5-D1 段 2** | **tool/_base.py** | **451** | **1** | **3** |
| **W5 累计** | | **623** | **2** | **5** |

## 累计 W2 + W3 + W4 + W5

| 数据 | 数字 |
|---|---|
| 行数 | **4797** |
| 笔记 | **33** |
| 强 | **75** |
| 胜率 | **74%** |

## 仍不清楚的

- `ToolChunk`（tool/_response.py）—— 流式 / 非流式 chunk 长什么样
- `ToolMiddlewareBase` 的具体实现（tracing / permission / 等）
- `_FunctionTool` 怎么把普通函数包成 tool
- `Toolkit`（tool/_toolkit.py，683 行）—— 怎么注册 + 调度 tool

## 接下来

W5-D1 段 2 闭环（451 行 + 1 笔记 + 3 强 + 9.0 分）。

**W5-D2 候选**：
- `tool/_toolkit.py` (683 行) — Toolkit 核心调度器
- `tool/_response.py` (205 行) — ToolChunk 定义
- `tool/_types.py` (200+ 行) — Tool 相关类型

**接下来我会用"更引导"的方式问问题**——**加 📍 行号 + 💡 观察提示**——**先观察后分析后评价**。
