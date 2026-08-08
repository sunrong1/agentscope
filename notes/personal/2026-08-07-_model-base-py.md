## 2026-08-07 | `model/_base.py` ChatModelBase — W4-D5 第 2 段

**读了什么**：`src/agentscope/model/_base.py` (646 行)

**关键发现**：**Model 层抽象核心——9 个 LLM provider 的母类**。

---

### ChatModelBase 结构

```
字段 (7): credential / model / stream / max_retries / retry_delay / context_size
内类: Parameters (BaseModel 子类定义自己的参数)
方法 (9):
  - _get_retryable_exceptions()  → ()
  - list_models()                → 读 YAML
  - __call__()                   → retry loop + 流式包装
  - _call_api()                  → @abstractmethod
  - _validate_tool_choice()      → 校验
  - count_tokens()               → 估算
  - generate_structured_output() → structured
  - _call_api_with_structured_output() → 假 tool 实现
```

### Structured Output 假 tool 实现

```python
# 1. 造假 tool
tools=[{
    "type": "function",
    "function": {
        "name": "generate_structured_output",
        "description": "Call this function to generate structured output...",
        "parameters": input_schema,
    }
}]

# 2. 强制 LLM 调
tool_choice = ToolChoice(mode="generate_structured_output")

# 3. 注入提示
instruction = "<system-reminder>Now you MUST call the tool..."

# 4. Parse 调用的 input
if isinstance(_, ToolCallBlock) and _.name == func_name:
    structured_output = _json_loads_with_repair(_.input, input_schema)
```

---

### Q1（Template Method Pattern）✅✅ 强

**你答**："模板方法模式 / 功能复用 / 轻量扩展"

**架构师视角**：

> **"Template Method = Inversion of Control for extension"**（模板方法 = 扩展版控制反转）
> - 不是子类调父类——是父类调子类——Hollywood Principle
> - 9 个 provider 行为统一——修 1 处 = 9 处受益

**vs "让子类实现 5 个方法"**：

| 方案 | 代码量 | 接入成本 | 修 bug 成本 |
|---|---|---|---|
| 5 方法 × 9 | 45 处 | 5× | 9 处 |
| 1 方法 × 9 | 9 处 | 1× | 1 处 |

---

### Q2（Structured Output 假 tool）✅✅ 强

**你答**："统一接口 / 模型能力不同 / 不能等"

**架构师视角**：

> **"Abstract the capability, not the implementation"**（抽象能力，不抽象实现）
> - 能力 = "返回结构化 JSON"——所有 provider 都能做
> - 实现 = "API 原生支持"——只有部分 provider 有
> - 抽象能力 = 9 个 provider 都"支持" structured output

**vs "等所有 provider 都支持原生"**：
- 等所有原生 = 永远等不到
- 假 tool = 现在 9 个全部能用

**W3 data flow 实战**：
- 不靠 API——靠数据流
- 把 structured output 伪装成 tool call
- 数据是同一个（JSON）——载体换了

---

### Q3（Retry 逻辑 2 份 DRY）✅✅ 强

**你答**："不违反 / 抽象会引入更多参数分支 / 收益小 / 难维护"

**为什么不抽**：

```python
# 抽了之后需要什么？
async def _retry(
    call_fn,         # 调什么
    on_cancelled,    # CancelledError 怎么处理（仅 __call__ 处理！）
    on_unretryable,  # 怎么判断重试 vs 立即抛
    return_type,     # 返回什么
):
    ...
```

**3 个 callback + 1 个 type**——**难追**。

**vs W3-D3 (Duplication > Wrong Abstraction) 实战**：

| W3 案例 | W4 案例 |
|---|---|
| 3 个 middleware 函数不抽 | 2 个 retry loop 不抽 |
| 形态相同 + 行为不同 | 形态相似 + 返回类型不同 |
| 抽了会丢 type safety | 抽了会引入 callback 复杂度 |

**同一个原则——不同应用——W3-W4 一脉相承**。

---

## 我今天 3 个最大收获

1. **Template Method = 扩展版控制反转**（Hollywood Principle：父类调子类）
2. **Abstract the capability, not the implementation**（假 tool = 优雅降级）
3. **Code is read more than written**（不抽的 retry loop 易读，W3 原则实战）

## W4-D5 段 2 战绩

| 数据 | 数字 |
|---|---|
| 行数 | 646 |
| 笔记 | 1（本文）|
| 答 | 3 |
| 强 | 3 |
| 浅 | 0 |
| 缺 | 0 |
| 评分 | **9.0/10** |

## 累计 W2 + W3 + W4

| 数据 | 数字 |
|---|---|
| 行数 | **4150 + 646 = 4796** |
| 笔记 | **30 + 1 = 31** |
| 强 | **67 + 3 = 70** |
| 胜率 | **70/96 = 73%** |

## 仍不清楚的

- `_StreamAccumulator`（line 16 新 import）—— 之前不在 base 里
- `list_models` 的 YAML 文件**长什么样**—— 需要看具体 provider 的 `_models/` 目录
- 9 个 provider 的 `_call_api` 实现差异
- `parameters` 的 Pydantic 模型怎么注入到 LLM API

## 接下来

W4-D5 段 2 闭环（646 行 + 1 笔记 + 3 强）——**W4 收官完美**。

W5 (8-10) 计划：工具与插件模块（`tool/` + `tracing/`)。
