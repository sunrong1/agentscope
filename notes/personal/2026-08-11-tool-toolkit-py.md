## 2026-08-11 | `tool/_toolkit.py` Toolkit — W5-D2 第 1 段

**读了什么**：`src/agentscope/tool/_toolkit.py` (683 行) — Toolkit 核心调度器

**关键发现**：**3 大设计点** — **Tool Groups + 4 类型 result + 3 层 error handling**。

---

### Toolkit = 3-in-1 容器

```
Python tools  +  MCP clients  +  Skills  /  统一管理
```

### Tool Groups（核心新概念）

```
"basic" 组永远激活  /  自定义组 agent 可激活/反激活
通过 ResetTools meta tool 切换
```

### 4 种 result 类型（call_tool dispatcher）

```python
if isinstance(res, ToolChunk):       # 单 chunk
elif isinstance(res, AsyncGenerator): # async 流
elif isinstance(res, Generator):      # sync 流
else: raise DeveloperOrientedException(...)  # 代码 bug
```

### 3 层 error handling

```python
except mcp.shared.exceptions.McpError:  # MCP 错
    yield error chunk
except Exception:
    if isinstance(e, DeveloperOrientedException):
        raise  # 冒泡
    yield error chunk
except asyncio.CancelledError:
    yield INTERRUPTED chunk
finally:
    yield tool_response  # 契约保证
```

---

### Q1（Tool Groups + meta tool）✅✅ 强

**你答**："meta tool 切换 / basic 永远激活（安全）/ 调用所有 tool 成本高+风险"

**架构师视角**：

> **"Tool groups = plugin system for agents"**（tool group = agent 的插件系统）
> - **VS Code 装扩展**——**装上 = 在 group 里**——**不用 = 不在 group 里**
> - **agent 像 IDE**——**自己决定装什么扩展**

**3 层"basic 永远激活"原因**：
1. **安全** — 防止 agent "忘记切换" 核心 tool
2. **可用性** — 即使 agent 出错，basic 永远在
3. **简单** — 用户配 "我想用 X" — **X 默认在 basic**

**"调用所有 tool"3 类成本**：
- **Token 成本**（100 tools × 200 tokens = 20K tokens）
- **LLM 选择成本**（100 tools 选错概率↑）
- **执行风险**（100 tools 含 `rm -rf` = 1 错致命）

---

### Q2（4 种 result 类型）✅✅ 强

**你答**："3 类型 = 不同实现 / raise = 代码 bug 必须修 / yield = 运行错误 Agent 处理"

**"3 类型 = 接住一切"**：

| 类型 | 例子 | 行为 |
|---|---|---|
| `ToolChunk` | `read_file()` 一次返回完整结果 | 简单同步 |
| `AsyncGenerator` | `Bash` 实时流式输出 | 长任务实时反馈 |
| `Generator` | 同步函数但 yield | 同步环境兼容 |
| `else` | 返回 str / int / None | **代码 bug**——**raise** |

**raise vs yield 架构关键**：

| 错误类型 | 谁负责 | 处理方式 |
|---|---|---|
| **代码 bug** | 开发者 | **raise**——必须修 |
| **MCP 网络错** | 用户环境 | yield chunk |
| **工具执行错** | 工具 / 数据 | yield chunk |
| **取消** | 用户 | yield INTERRUPTED |

> **"raise = Stop the world / yield = Recovery path"**
> - **raise** = 系统级错误 = 框架不能继续 = 必须冒泡
> - **yield** = 业务级错误 = agent 可以继续 = 降级处理
> - **混用 = 灾难** — bug 变 silent failure（yield 吞了）— 或业务错冒泡（raise 杀服务）

---

### Q3（3 层 error handling）✅✅ 强

**你答**：
- "McpError = 特有错误，格式特殊，单独处理"
- "DeveloperOrientedException = 代码 bug，冒泡给开发者"
- "CancelledError = 用户主动取消，不是错误，是中断信号"
- "finally = 保证 tool_response 一定发出，让调用方知道工具执行完了"

**升级**：

> **"3 层 = 错误的 3 个责任方"**
> - **McpError** = 第三方（外部协议）——降级为 chunk
> - **Exception（非 Dev）** = 工具实现方 ——降级为 chunk
> - **DeveloperOrientedException** = 框架使用者（开发者）——raise 冒泡
> - **CancelledError** = 用户 ——尊重意图 ——标记 INTERRUPTED

**责任方不同 = 处理不同**——3 层不是过度设计——是精确表达"谁的错"。

---

## 我今天 3 个最大收获

1. **Tool groups = plugin system** — agent 像 IDE 装扩展
2. **raise = Stop the world / yield = Recovery path** — 错误处理按责任方分
3. **finally = 契约保证** — 调用方永远收到响应

## W5-D2 段 1 战绩

| 数据 | 数字 |
|---|---|
| 行数 | 683 |
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
| W5-D1 段 2 | tool/_base.py | 451 | 1 | 3 |
| **W5-D2 段 1** | **tool/_toolkit.py** | **683** | **1** | **3** |
| **W5 累计** | | **1306** | **3** | **8** |

## 累计 W2 + W3 + W4 + W5

| 数据 | 数字 |
|---|---|
| 行数 | **4797 + 1306 = 6103** |
| 笔记 | **33 + 3 = 36** |
| 强 | **75 + 8 = 83** |
| 胜率 | **83/109 = 76%** |

## 仍不清楚的

- `ToolGroup` 内部实现（`tool/_tool_group.py`，70 行）—— group 怎么管理 skill + tool + mcp
- `tool/_builtin/` 内置工具（bash, read, write, edit, grep, glob）—— 怎么实现
- `ToolChunk` / `ToolResponse` 完整定义（`tool/_response.py`）
- `tool/_toolkit.py` 的 `_get_available_tools` 完整实现——MCP 错误隔离细节
- `tool/_adapters.py` MCP 适配器细节

## 接下来

W5-D2 段 1 闭环（683 行 + 1 笔记 + 3 强 + 9.0 分）。

**W5-D2 段 2 候选**：
- `tool/_builtin/_bash.py` (789 行) —— 真实工具实现
- `tool/_builtin/_read.py` / `_write.py` / `_edit.py` —— 文件操作
- `tool/_response.py` (205 行) —— ToolChunk 定义
- `tool/_tool_group.py` (70 行) —— ToolGroup 实现
- `tool/_adapters.py` (394 行) —— MCP 适配器

**晚 9:44**——**今天 W5 段 1 完美**——**建议收工**——**周末休息**。
