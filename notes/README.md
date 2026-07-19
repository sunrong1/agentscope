# 学习日志

> **学习目标**：成为 Agent 应用架构师
> **学习对象**：AgentScope 2.0（sunrong1/agentscope fork）
> **当前状态**：W1 重新开始（详见 [`personal/2026-07-19-重置与真学习.md`](personal/2026-07-19-重置与真学习.md)）

## 目录结构

```
notes/
├── README.md                # 本文件
├── debug-log.md             # 错题本（跨切面）
│
├── personal/                # ⭐ 真学习笔记（过程，仅自己）
│   ├── README.md
│   └── YYYY-MM-DD-<主题>.md
│
├── learning-map/            # 🗺️ 学习地图（目标，未经验证）
│   ├── architecture.md      # ⚠️ 2026-07-18 AI 协作产出，未读代码
│   ├── class-diagrams.md    # ⚠️ 同上
│   ├── sequence-diagrams.md # ⚠️ 同上
│   ├── distributed-topology.md # ⚠️ 同上
│   └── public-commit-drafts.md # ⚠️ 同上
│
└── tools/                   # 工具
    ├── review.py            # SM-2 复习系统
    └── review_data.json
```

## 工作流

```
读代码 → 写 personal/ 笔记（过程）→ 积累够了 → 重写 learning-map/（产出）
```

**关键规则**：
- `personal/` 是真实学习过程，可以乱、可以错、可以"我没懂"
- `learning-map/` 是目标地图，但**每篇都有"⚠️ 未经验证"标记**
- **禁止**从 learning-map 倒推 personal 笔记（那是编造）

## 终极度量（学完应该长什么样）

- [ ] 能拆解：画出核心架构图，**自己读的代码**
- [ ] 能扩展：独立开发自定义 Agent/Tool，**基于真实理解**
- [ ] 能排错：分布式部署问题有排查思路，**不是复述别人的话**
- [ ] 能评判：能说清设计优点与局限，**有独立观点**

## 8 周计划（2026-07-18 → 2026-09-12）

| 阶段 | 周期 | 目标 | 真实交付物 |
|---|---|---|---|
| Phase 1 读懂 1 个核心类 | W1-2 | Agent 主体类精读 | `personal/` 里 10+ 篇笔记 |
| Phase 2 读懂 5 大模块 | W3-7 | Middleware/Bus/Storage/Workspace/Tool | 25+ 篇 personal 笔记 + 1 个 Demo |
| Phase 3 实战 | W8+ | 提 PR | 至少 1 个被合并的 PR |

**调整说明**：之前 Phase 1 是"画架构图"，现在改为"读懂 1 个核心类"——更扎实、更可验证。

## 进度看板

- [x] 2026-07-19：诚实 reset，建立 personal/ 流程
- [ ] 2026-07-19 起：每天 30-60 行精读 + personal 笔记
- [ ] W2 周末：第一次周自检（用 review 系统对 personal 笔记打分）

## 周自检表（周五下午 30min 填写）

> 自检维度改为"学习动作"而非"产出"——避免"伪学习"

| 周 | 读：精读行数 | 写：personal 笔记数 | 破：解决一个问题 | 建：跑通 1 个 demo |
|---|---|---|---|---|
| W1 | _ | 1 (重置说明) | 0 | 0 |
| W2 | | | | |
| W3 | | | | |
| W4 | | | | |
| W5 | | | | |
| W6 | | | | |
| W7 | | | | |
| W8 | | | | |

**规则**：连续两周读 < 100 行，启动 5-Why 分析。
