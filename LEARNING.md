# 公开承诺：8 周成为 Agent 应用架构师

> **立 flag 的人**：Dave Sun (sunrong1) · 华为上海
> **承诺日期**：2026-07-18
> **承诺周期**：2026-07-18 → 2026-09-12（Phase 1 + Phase 2 共 8 周）
> **学习对象**：[AgentScope 2.0](https://github.com/sunrong1/agentscope) · v2.0.4
> **学习记录**：[`learning-journal` 分支](https://github.com/sunrong1/agentscope/tree/learning-journal)
> **信条**：心外无理，至诚无息。
>
> ## ⚠️ 2026-07-19 重要更新：重置
> **W1 期间 4 份长文档（架构图/类图/时序图/分布式）均由 AI 协助产出，作者未亲自读代码**。
> 详情见 [`notes/personal/2026-07-19-重置与真学习.md`](notes/personal/2026-07-19-重置与真学习.md)。
>
> **W1 重新开始**：之前的产出降级为"学习地图"（标 ⚠️ 未经验证），新建 `notes/personal/` 写真学习笔记。
> 公开承诺 8 周目标不变（Sep 12），但**度量标准改为"读懂代码"而非"产出文档"**。

---

## 📈 真实学习进度（截至 2026-07-21 W2-D2 收尾）

| 周 | 日期 | 行数 | 笔记数 | 状态 |
|---|---|---|---|---|
| W1 | 7-19 | 95 | 1 | 重置 + 起步 |
| W2-D1 | 7-20 | 100 | 1 | ⬜ ⬜ ⬜ ⬜ ⬜ ⬜ ⬜ |
| W2-D2 | 7-21 | 145 | 3 | ⬜ ⬜ ⬜ ⬜ ⬜ ⬜ ⬜ |
| W2-D3 | 7-22 | 230 | 2 | ⬜ ⬜ ⬜ ⬜ ⬜ ⬜ ⬜ |
| W2-D4 | 7-23 | 371 | 4 | ⬜ ⬜ ⬜ ⬜ ⬜ ⬜ ⬜ |
| W2-D5 | 7-24 | 352 | 3 | Q5 闭环 + 推理核心 + 收尾 |
| W2-D6 | 7-25 | 0 | 1 | W2 周自检（提前到周六）|
| W2-D7 | 7-26 | 240 | 0 | 提前读 W3-D1（_inject_runtime_state）|
| **W2 累计** | | **1438** | **14** | **W2 目标 750 行 / 5 笔记** |
| W3-D1 | 7-27 | 460 | 3 | _inject + _check + _handle + _handle_messages 四段 |
| W3-D2 | 7-28 | 219 | 2 | _batch + sequential + concurrent 三段 |
| W3-D3 | 7-29 | 158 | 2 | _handle_error + _acting 收尾 |
| W3-D4 | 7-30 | 117 | 1 | _into_queue + _split_context 收尾 |
| W3-D5 | 7-31 | 349 | 4 | _split_tool_result + model 适配 + _clear_unreserved + W3 收尾反思 |
| **累计 W2 + W3** | | **2732** | **23** | **W2 目标 750 行 / 5 笔记** |

**当前 W2 + W3-D1 累计**：行数 1870 / 笔记 15 = 249% / 300% W2 目标

### W4-W5 累计摘要

| 阶段 | 累计 | 关键 |
|---|---|---|
| W4 5 days (8-3~8-7) | 2064 行 / 5 笔记 / 13 强 / 87% 胜率 | 8 大架构飞跃 |
| W5 4 段 4 笔记 | 1511 行 / 11 强 / 9.0+ avg | 3 大方法论 |
| **累计 W2+W3+W4+W5** | **6103 行 / 36 笔记 / 83 强** | **胜率 76%** |

### W6 进度（8-21 开始）

| 日期 | 段 | 行数 | 笔记 | 关键 | 状态 |
|---|---|---|---|---|---|
| 8-24 | W6-D1 段 1 | 372 | 1 | state/_state.py 整体架构 | ✅ |
| 8-26 | W6-D1 段 2 | ~3700 (3 整文件) | 1 | 3 个 memory 实现对比 | ✅ |
| 8-21~8-26 | **W6 累计** | **~4070** | **2** | **整体架构模式** | **进行中** |

> ⚠️ **学习模式切换**：W2-W5 是"逐行 + Q&A"——W6 切到"整体架构 + 跨段对比"模式。

## 🔥 W6 重大发现：Middleware 模式 = 可插拔策略

**位置**：`src/agentscope/middleware/_longterm_memory/`

**3 个实现 = 3 种"自动化等级"**：
- `_mem0` = 半自动（agent 主动 add）
- `_reme` = 全自动（LLM 提取）
- `_agentic_memory` = 全手动（agent 自己写 .md）

**HERO 选 `_mem0`**：1180 行 + user_id/agent_id 双 key 维护 + on_reply hook 自动写回

## 🔥 W2 重大发现：Q5 真 bug 闭环

**位置**：`src/agentscope/agent/_agent.py:705`

**问题**：`_close_unfinished_tool_calls` 重复 emit `ToolResultStartEvent` 给 SUBMITTED 状态的 external tool

**修复**：`if call_block.state not in (ToolCallState.ALLOWED, ToolCallState.SUBMITTED):`

**Issue 草稿已写完**——待 W2 末写 reproduce 脚本后提交。

---

## 🎯 我要在 8 周后变成什么样

不是"会用 AgentScope"，而是 **Agent 应用架构师**。4 个可验证的能力：

- [ ] **能拆解**：能画出 AgentScope 2.0 的核心架构图，讲清各组件职责与通信方式
- [ ] **能扩展**：能独立开发一个自定义 Agent 或 Tool 并集成进框架
- [ ] **能排错**：遇到分布式部署、消息通信、状态同步等问题，有清晰的排查思路
- [ ] **能评判**：能说出 AgentScope 设计的优点和局限，知道什么场景适合、什么场景不适合

---

## 📅 8 周计划

### Phase 1：宏观认知（第 1-2 周，2026-07-18 → 2026-08-01）

> 目标：理解框架的"顶层设计"，不陷入细节。

| 周 | 交付物 | 链接 | 状态 |
|---|---|---|---|
| W1-D1 | clone 仓库 + 建学习分支 | [commit](https://github.com/sunrong1/agentscope/commit/40d9bb6) | ✅ |
| W1-D2 | 架构全景图（4 层 + 6 大原语） | [architecture.md](notes/phase-1/architecture.md) | ✅ |
| W1-D3 | 核心类图（4 大类族） | [class-diagrams.md](notes/phase-1/class-diagrams.md) | ✅ |
| W1-D4 | 核心时序图 | `notes/phase-1/sequence-diagrams.md` | ⏳ |
| W1-D5 | 分布式部署拓扑 | `notes/phase-1/distributed-topology.md` | ⏳ |
| W1-D6 | 架构评判（ADR 格式） | `notes/phase-1/adr/` | ⏳ |
| W1-D7 | **公开承诺**（本文件） | `LEARNING.md` | ✅ |
| W2 | 补完 Phase 1 全部 + 周自检 | `notes/README.md` 自检表 | ⏳ |

### Phase 2：核心深潜（第 3-8 周，2026-08-01 → 2026-09-12）

> 目标：逐个攻克 5 大核心模块，每模块产出一个独立 Demo + 源码注解。

| 周 | 模块 | 交付物 |
|---|---|---|
| W3 | **Agent 基类与生命周期** | `_agent.py` 2911 行精读 + Demo |
| W4 | **消息与通信机制** | Msg 类型 + 序列化 + Demo |
| W5 | **工具与插件系统** | 自定义 Tool + MCP 集成 Demo |
| W6 | **记忆与上下文管理** | LongTermMemory Middleware 三选一接入 |
| W7 | **分布式部署** | RedisMessageBus + Session 锁 Demo |
| W8 | **RAG / 沙箱 / Tracing**（任选一深入） | 完整 Demo |

### Phase 3：实战构建（第 9 周及以后）

> 目标：脱离教程，解决一个自己的实际问题。
> **终极检验**：在 AgentScope 上游仓库 [agentscope-ai/agentscope](https://github.com/agentscope-ai/agentscope) 提交至少 1 个被合并的 PR。

---

## 📊 每周自检表

> 每周五下午 30 分钟填写。连续两周出现"否"，启动 5-Why 分析。

| 维度 | 度量 | 标准 |
|---|---|---|
| **知** | 画类图/时序图 | 能不参考资料画出来 |
| **行** | 独立 Demo | 脱离公司环境、可独立运行 |
| **破** | 独立解的 bug | 记录在 [`notes/debug-log.md`](notes/debug-log.md) |
| **建** | 提交代码/文档 | 公开可访问 |

完整自检表见 [`notes/README.md`](notes/README.md)。

---

## 🛡️ 君子之约（做不到怎么办）

- **Phase 1 完不成**：公开撤销承诺，并请一位朋友监督我重置
- **Phase 2 拖延超过 1 周**：在个人博客公开复盘
- **8 周结束 4 个能力未达**：自掏腰包请关注我的朋友喝咖啡，**并把本仓库设为 archived**

这个承诺对我自己生效。**立 flag 的意义，不在 flag 立得多漂亮，在于有人看见、你不能悄悄撤掉。**

---

## 📈 当前进度（实时更新）

| 阶段 | 进度 | 完成日期 |
|---|---|---|
| Phase 1 | 🟩 60% (3/5) | 进行中 |
| Phase 2 | ⬜ 0% | - |
| Phase 3 | ⬜ 0% | - |

更新规则：每完成一个交付物，commit 到 `learning-journal` 分支，并更新本表。

---

## 🔗 资源

- **学习仓库**：[github.com/sunrong1/agentscope](https://github.com/sunrong1/agentscope) · 分支 `learning-journal`
- **官方文档**：[docs.agentscope.io](https://docs.agentscope.io/)
- **官方仓库**：[github.com/agentscope-ai/agentscope](https://github.com/agentscope-ai/agentscope)
- **方法论来源**：deepseek 提供的"3 阶段 + 周自检"学习系统

---

> **写在最后**
>
> 看到这里的朋友，谢谢你点开。**如果你也想一起学 AgentScope，欢迎在 issue 里留言**——我会在 Phase 3 把联合作者的 PR 一起提上去。
>
> 8 周后见。
>
> —— Dave, 2026-07-18
