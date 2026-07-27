## 2026-07-27 | `_inject_runtime_state` (line 1009-1249) — W3-D1 第 1 段

**读了什么**：`src/agentscope/agent/_agent.py:1009-1249`（240 行）

**关键发现**：**这函数是 agent "自我感知" 的实现**——**通过 HintBlock 注入到 context 让 agent 知道"时间/任务/context 状态"**。

---

### Q1（3 维度清单）✅✅ 精准

| 维度 | 触发条件 | 注入内容 |
|---|---|---|
| **时间** | 首次 / 上次注入超 `time_interval` 小时 | `<current-time>...</current-time>` + `<timezone>...</timezone>` |
| **任务** | 有 pending/in_progress + context 不 aware | `<tasks>You have N in-progress tasks...</tasks>` |
| **上下文** | iter=0 + token 接近压缩阈值 | `<context-length>...</context-length>` |

**3 维度互相独立**——**各自独立判断、独立触发**。

---

### Q2（设计哲学）⚠️ 浅

**你答**："充分利用缓存，节约费用"

**真正机制**：
- LLM 的 **prompt cache 按前缀匹配**工作（OpenAI/Anthropic 都这样）
- **system prompt 改了 = 前缀变了 = 整个 cache 失效 = 重新计费**
- **HintBlock 放在 context messages（不是 system prompt）= 前缀不变 = cache 命中 = 省 50%+ 成本**

**架构师视角**：
> **"频繁变的信息 ≠ system prompt"**
> - 变的信息放 context（每次 reply 都更新）
> - 稳定的信息放 system prompt（缓存命中）
> - **这是 prompt engineering 的核心原则**

---

### Q3（aware_of_tasks）⚠️ 浅

**你答**："从后往前扫描，提升效率"

**真正答的是遍历方向，不是变量本身**。

**`aware_of_tasks` 是什么**——**boolean 标志，追踪 agent 是否已知道任务**：

```python
aware_of_tasks = not has_uncompleted_tasks  # 默认 True

for msg in reversed(self.state.context):  # 从后往前扫
    for block in reversed(msg.content):
        if (isinstance(block, ToolCallBlock) and 
            block.name in task_tool_names):
            aware_of_tasks = True  # 找到 task 工具调用 → agent 知道
        elif (isinstance(block, HintBlock) and "<tasks>" in text):
            aware_of_tasks = True  # 之前注入过 → agent 知道
```

**为什么需要**：
- **如果不检测** → 每次 iter 都 inject 同样的任务列表
- 任务列表 injection **只在 agent 不知道时才必要**
- **重复 inject 浪费 context tokens** + **重复给 LLM 看**

**`break` 条件**（line 1085-1095）：**两个条件（last_time + aware）都满足就提前退出**——**避免扫整个 context**。

---

### Q4（emit_hint_event）✅✅ 精准

**你答**："写入 hintblock 无条件，event 可选，默认 TRUE"

**完全正确**——**我验证过 _config.py line 273：`emit_hint_event: bool = Field(default=True)`**

**设计哲学**：
- **HintBlock 写入 context = 框架契约**（必须）
- **HintBlockEvent yield = 应用层可观测**（可选）
- **默认 emit = 上层能看到**——**debug / UI 都能用**

---

### 补充：block.name 是什么

**`block.name` = 被调用的工具名（string）**。

**实际值**（task 工具）：
- `"CreateTask"`
- `"TaskList"`
- `"UpdateTask"`
- `"DeleteTask"`

**`_inject_runtime_state` line 1105**：
```python
elif (isinstance(block, ToolCallBlock) 
      and block.name in self.injection_config.task_tool_names):
    aware_of_tasks = True
```

**逻辑**：context 里出现过 task 工具调用 → agent 已经知道任务 → 不需要再 inject 任务提示。

---

## 我今天最大的收获（4 个）

1. **3 维度独立触发**——**time / tasks / context length**——**互不依赖**
2. **HintBlock vs system prompt**——**核心是 prompt cache 命中**——**省钱关键**
3. **aware_of_tasks 优化**——**避免重复 inject**——**节省 context tokens**
4. **emit_hint_event 默认 TRUE**——**HintBlock 持久化是默认行为**

## W3-D1 第 1 段战绩

| 项 | 数据 |
|---|---|
| 阅读 | 240 行 |
| 笔记 | 1 篇（本文）|
| 答问题 | 4 道（1 精准 + 1 精准 + 2 浅）|
| 概念飞跃 | **prompt cache + HintBlock 关系**（省钱关键）|

## 仍不清楚的

- **`_prepare_model_input` 怎么算 token**——**line 1212 用了它**——**没读**
- **`injection_config.task_tool_names` 默认值是什么**——**影响 aware_of_tasks 逻辑**
- **`_resolve_timezone` 怎么实现**——**时区解析**
- **HintBlock 在 context 里**和**system prompt 一样吗**——**对 LLM 来说"地位"相等？**

## 接下来

**W3-D1 还有 3 段待读**：
1. `_check_incoming_event` (~90 行)
2. `_handle_incoming_event` (~100 行)
3. `_handle_incoming_messages` (~30 行)

**W3-D1 目标**：读完所有 4 段 + Q5 reproduce 脚本起步。
