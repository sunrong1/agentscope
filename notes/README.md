# AgentScope 学习日志

> **学习目标**：成为 Agent 应用架构师
> **学习对象**：AgentScope 2.0（sunrong1/agentscope fork）
> **方法论来源**：deepseek 提供的 3 阶段学习系统 + 自我修正

## 终极度量标准（学完应该长什么样）

- [ ] 能拆解：画出核心架构图，讲清各组件职责与通信方式
- [ ] 能扩展：独立开发自定义 Agent/Tool 并集成
- [ ] 能排错：分布式部署、消息通信、状态同步问题有排查思路
- [ ] 能评判：能说清设计优点与局限，知道何时用/不用

## 阶段路线图

| 阶段 | 周期 | 目标 | 交付物 |
|---|---|---|---|
| Phase 1 宏观认知 | W1-W2 | 顶层设计、架构图 | ✅ `notes/phase-1/architecture.md`<br/>✅ `notes/phase-1/class-diagrams.md`<br/>⏳ W1-D4 时序图 / W1-D5 分布式拓扑 |
| Phase 2 核心深潜 | W3-W8 | 5 大核心模块 | 5 份源码注解 + 5 个独立 Demo |
| Phase 3 实战构建 | W9+ | 提 PR | 至少 1 个被合并的 PR |

## 每周自检表（周五下午 30min 填写）

> 链接列必须填上产出物路径

| 周次 | 知：画类图/时序图 | 行：独立 Demo | 破：独立解的 bug | 建：提交代码/文档 | 状态 |
|---|---|---|---|---|---|
| W1 | | | | | |
| W2 | | | | | |
| W3 | | | | | |
| W4 | | | | | |
| W5 | | | | | |
| W6 | | | | | |
| W7 | | | | | |
| W8 | | | | | |

**规则**：连续 2 周"否"，启动 5-Why 分析。

## 错题本

见 `notes/debug-log.md`

## 公开承诺

> 📢 **已发布**：[仓库根 `LEARNING.md`](../LEARNING.md)
>
> 8 周成为 Agent 应用架构师。三个版本同步发布：
> - 仓库 LEARNING.md（权威版，每交付物链接）
> - 博客版（sunrong.site，同行可读）
> - 社交媒体版（X/LinkedIn/朋友圈，短版）

## 进度看板

- [x] 2026-07-18 W1-D1：clone 仓库，建学习分支
- [x] 2026-07-18 W1-D2：Phase 1 骨架图（4 层 + Agent 钩子 + MessageBus + 工具流 + App 装配）
- [x] 2026-07-18 W1-D3：Phase 1 类图（Agent/Toolkit/MiddlewareBase/MessageBus 4 大类族 + 全景类图）
- [ ] W1-D4：补时序图（agent.reply + tool call）
- [ ] W1-D5：分布式拓扑图
- [ ] W1-D6：架构评判文档（ADR 格式 3 个关键决策）
- [ ] W1-D7：周自检 + 公开承诺发布
