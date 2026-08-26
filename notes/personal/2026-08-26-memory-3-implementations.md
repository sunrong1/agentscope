## 2026-08-26 | 3 个记忆实现整体对比 — W6-D1 段 2

**读了什么**：
- `src/agentscope/middleware/_longterm_memory/_mem0/_middleware.py` (741 行)
- `src/agentscope/middleware/_longterm_memory/_reme/_middleware.py` (552 行)
- `src/agentscope/middleware/_longterm_memory/_agentic_memory/_middleware.py` (953 行)
- + 各 _tools.py + _utils.py + adapter

**关键发现**：**3 种哲学 = 3 种"自动化等级"**——**Middleware 模式让"记忆策略"可插拔**。

---

### 段 2 整体架构

```
src/agentscope/middleware/_longterm_memory/
│
├─ __init__.py
│
├─ _mem0/ (1180 行)                    ← HERO 在用
│   ├─ _middleware.py (741)            — Mem0 集成
│   ├─ _tools.py (270)                 — search_memory + add_memory
│   ├─ _agentscope_adapter.py (439)    — Msg ↔ Mem0 格式
│   └─ _utils.py (76)
│
├─ _reme/ (1042 行)
│   ├─ _middleware.py (552)            — 嵌入式 ReMe app
│   ├─ _tools.py (182)                 — memory_search（无 add）
│   ├─ _config.py (376)
│   └─ _utils.py (104)
│
└─ _agentic_memory/ (953 行)
    └─ _middleware.py (953)            — 文件系统 + Read/Write
```

---

### 4 维度全景对比

#### 维度 1：**Hook 实现矩阵**

| Hook | _mem0 | _reme | _agentic_memory |
|---|---|---|---|
| `on_reply` | ✅ 自动 search + 写回 | ✅ **后台 search + 自动写回** | ✅ 轻量（不主动搜索）|
| `on_reasoning` | ❌ | ✅ **并发检索等待** | ✅ **异步 hint** 主题文件 |
| `on_system_prompt` | ✅ 注入检索说明 | ✅ 注入检索说明 | ✅ **注入 MEMORY.md 索引** |
| `list_tools` | ✅ 2 个 tool | ✅ 1 个 tool | ❌ 用现有 Read/Write |

#### 维度 2：**数据流**

```
_mem0: 用户消息 → on_reply(前:search 同步) → 注入 context → 推理 → 写回
_reme: 用户消息 → on_reply(后台:launch search) → 并发 on_reasoning 等待 → 注入 → 写回
_agentic_memory: 启动 → on_system_prompt(注入索引) → agent 用 Read 读 → Write 写
```

#### 维度 3：**Tool 接口**

| 实现 | 暴露 Tool | Tool 数量 | Tool 行为 |
|---|---|---|---|
| **_mem0** | `search_memory` + `add_memory` | 2 | 显式（agent 主动调）|
| **_reme** | `memory_search` | 1 | 显式 search（write 自动）|
| **_agentic_memory** | **0**（用 Read/Write）| 0 | 完全自主 |

**核心 insight**：**Tool 数量 = 框架"自动化"程度的反向指标**

#### 维度 4：**持久化**

| 实现 | 存储 | 跨 session | 跨实例 | 运维成本 |
|---|---|---|---|---|
| **_mem0** | 外部服务（pgvector/Qdrant）| ✅ user_id | ✅ SaaS | ⚠️ **高** |
| **_reme** | 进程内 ReMe app | ✅ session_id | ❌ 单进程 | 🟡 中 |
| **_agentic_memory** | 本地 .md 文件 | ✅ workspace | ⚠️ 文件共享 | ✅ **零** |

---

### 核心 insight 1：**Middleware 模式 = "可插拔记忆策略"**

```
用户代码：
agent = Agent(
    ...,
    middleware=[
        Mem0Middleware(...),       # 选 1
        # ReMeMiddleware(...),     # 或
        # AgenticMemoryMiddleware(...),  # 或
    ]
)
```

**3 个实现可互换**——**这正是"开闭原则"的体现**——**对扩展开放，对修改封闭**。

---

### 核心 insight 2：**3 种 Hook 组合 = 3 种"记忆调度"**

| Hook 组合 | 调度模式 | 性能 | 实时性 |
|---|---|---|---|
| **on_reply** only | 同步 | ⚠️ 阻塞 | 🟢 高 |
| **on_reply + on_reasoning** | 并发 | ✅ 0 latency | 🟡 best-effort |
| **on_system_prompt + on_reasoning** | 懒加载 | ✅ 极快 | 🟡 异步 hint |

**为什么 _reme + _agentic_memory 都用 on_reasoning？**
- 因为它们**避免前向 latency**——**检索放后台**——**框架级并发优化**

---

### 核心 insight 3：**3 种"记忆写回"哲学**

| 写回触发 | 实现 | 优势 | 风险 |
|---|---|---|---|
| **agent 主动** | _mem0 `add_memory` | 精确（agent 知道什么值得记）| ⚠️ agent 可能忘 |
| **LLM 自动提取** | _reme `auto_memory` | 智能（LLM 决定）| ⚠️ LLM 成本 |
| **agent 文件操作** | _agentic_memory `Write` | 透明（agent 看到 .md）| ⚠️ 写作成本 |

---

### 选型决策树

```
你的项目需要什么？
│
├─ 跨实例 + 多用户 + 企业级
│   └─ ✅ _mem0（HERO 选的就是这个）
│
├─ 单机 + 自动整理 + 零运维
│   └─ ✅ _reme
│
├─ 隐私优先 + 完全可控 + 零依赖
│   └─ ✅ _agentic_memory
│
└─ 性能优先（避免前向 latency）
    └─ ✅ _reme 或 _agentic_memory（on_reasoning 并发）
```

---

### HERO 实战 ↔ 框架实现对应

| H1 2026 绩效说 | 框架实际做了什么 |
|---|---|
| "引入 Mem0 方案" | _mem0/ 整个模块（1180 行）|
| "记忆系统" | _mem0 维护 `user_id` + `agent_id` 双 key |
| "测试场景落地" | `_middleware.py:on_reply` hook 自动写 |

**HERO 选 `_mem0` 是 3 个实现里"自动化等级最低"但"跨服务能力最强"**——**符合企业生产需求**。

---

### 段 2 收尾心法

> **"3 种哲学 = 3 种自动化等级（半自动 / 全自动 / 全手动）"**
> **"Tool 数量 = 框架自动化程度的反向指标"**
> **"on_reasoning 是性能优化的关键 Hook"**

---

### 跨 W 连接（段 2 涉及的 3 大方法论）

| W6 段 2 设计 | 对应之前的方法论 |
|---|---|
| **Middleware 模式 = 策略可插拔** | W4 飞跃 #3 Field Grouping（同源）|
| **on_reasoning 并发** | W5 三大方法论 Concurrency = parallelism + isolation |
| **写回哲学（agent/系统/文件）**| W5 三大方法论 Speed > Perfect Accuracy |

---

## 📊 W6-D1 整体收获

| 项 | 状态 |
|---|---|
| **段 1** | ✅ state/_state.py 整体架构（4 Context + Container + Compat）|
| **段 2** | ✅ 3 个 memory 实现整体对比（Middleware 模式）|
| **总行数** | ~1100 行（state 372 + 3 个 middleware 各 100-200 头 + adapter）|
| **核心 insight** | 6 个（3 个/段）|
| **跨 W 引用** | 3 大方法论 + 8 大飞跃 + ToolCallState 状态优先级 |
