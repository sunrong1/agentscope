# AgentScope 2.0 分布式部署拓扑

> **配套**：`architecture.md`（架构全景） + `class-diagrams.md`（类族） + `sequence-diagrams.md`（时序）— 本文件是它们的"多副本投影"
> **代码基线**：`sunrong1/agentscope` @ `30ca3ef`
> **产出日期**：2026-07-18
> **状态**：Phase 1 - Task 4 完成

单进程模式（`InMemoryMessageBus` + `LocalWorkspace`）很好理解，但生产环境必须**多副本**。本文件梳理 AgentScope 在分布式模式下的拓扑、并发保证、故障恢复。

---

## 1. 生产拓扑总览

```mermaid
graph TB
    subgraph CLIENT["客户端"]
        WEB[Web UI]
        APP[Mobile App]
        API[第三方 API 调用方]
    end

    subgraph LB["负载均衡层"]
        LB1[Nginx / ALB<br/>HTTPS 终止 + WS Upgrade]
    end

    subgraph APILayer["API 副本层 (Stateless)"]
        API1[API Replica 1<br/>uvicorn :8000]
        API2[API Replica 2<br/>uvicorn :8000]
        API3[API Replica N<br/>uvicorn :8000]
    end

    subgraph SharedInfra["共享基础设施"]
        REDIS[(Redis<br/>MessageBus + Storage<br/>+ Session Lock)]
        S3[(S3 / OSS<br/>Blob Store)]
    end

    subgraph WorkerLayer["后台 Worker 层"]
        IDX1[Index Worker 1<br/>RAG 索引]
        IDX2[Index Worker 2]
        SCHED[Scheduler Manager<br/>调度任务]
    end

    subgraph SandboxLayer["Workspace 沙箱层 (按需创建)"]
        WS1[Docker Container<br/>session-abc]
        WS2[K8s Pod<br/>session-def]
        WS3[E2B Cloud Sandbox<br/>session-ghi]
        WS4[Daytona Workspace<br/>session-jkl]
    end

    WEB & APP & API --> LB1
    LB1 --> API1 & API2 & API3
    API1 & API2 & API3 <--> REDIS
    API1 & API2 & API3 --> S3
    IDX1 & IDX2 <--> REDIS
    IDX1 & IDX2 --> S3
    SCHED <--> REDIS
    API1 -.启动沙箱.-> WS1
    API2 -.启动沙箱.-> WS2
    API3 -.启动沙箱.-> WS3 & WS4

    classDef client fill:#e3f2fd,stroke:#1976d2
    classDef api fill:#fff3e0,stroke:#f57c00
    classDef infra fill:#f3e5f5,stroke:#7b1fa2
    classDef worker fill:#e8f5e9,stroke:#388e3c
    classDef sandbox fill:#fce4ec,stroke:#c2185b
    class WEB,APP,API client
    class LB1,API1,API2,API3 api
    class REDIS,S3 infra
    class IDX1,IDX2,SCHED worker
    class WS1,WS2,WS3,WS4 sandbox
```

**关键设计决策**：

- **API 副本是 Stateless**——所有状态在 Redis，所以副本数可任意扩缩（水平扩展）
- **Workspace 沙箱不共享**——每个 session 的沙箱在用哪个副本就建在哪（生命周期跟着 session）
- **Worker 是可独立扩展的层**——和 API 解耦，扩缩容不影响主链路
- **Redis 是"单一数据源"**——Storage + MessageBus + Session Lock + 任务队列都在这里

---

## 2. 单个 API 副本的进程内结构

```mermaid
graph TB
    subgraph Proc["一个 API 进程 (uvicorn worker)"]
        FastAPI[FastAPI App<br/>create_app]

        subgraph Dispatchers["Dispatchers (后台协程)"]
            WD[WakeupDispatcher<br/>订阅 wakeup_signal]
            CD[CancelDispatcher<br/>订阅 task_cancel_channel]
            CRR[ChatRunRegistry<br/>本进程 in-flight chat 任务]
        end

        subgraph Services["Service 层"]
            CS[ChatService]
            SS[SessionService]
            KBS[KnowledgeBaseService]
            RAS[ResourceAccessService]
        end

        subgraph Managers["Manager 层"]
            BTM[BackgroundTaskManager]
            SCH[SchedulerManager]
            SW[IndexSweeper]
        end

        subgraph Optional["可选 (enable_index_worker=True)"]
            IW[IndexWorker]
            ITC[IndexTaskConsumer]
        end

        Perm[PermissionEngine]

        FastAPI --> CS
        FastAPI --> SS
        FastAPI --> KBS
        FastAPI --> RAS
        CS --> Perm
        CS --> BTM
        CS --> CRR
        WD --> CS
        CD --> CRR
        SCH -.定时唤醒.-> WD
        KBS --> SW
        KBS -.enable_index_worker=True.-> ITC
    end

    classDef service fill:#e3f2fd
    classDef manager fill:#fff3e0
    classDef dispatcher fill:#f3e5f5
    classDef optional fill:#fff9c4
    class CS,SS,KBS,RAS service
    class BTM,SCH,SW,Perm manager
    class WD,CD,CRR dispatcher
    class IW,ITC optional
```

**关键观察**：

- **Dispatchers 是后台长跑协程**——它们订阅 message_bus 的 channel，被触发后调用 service 层
- **`ChatRunRegistry` 是 per-process**（不是共享）—— 它的作用是"本进程内哪些 chat 任务在跑"
- **IndexWorker 可内嵌可外置**（`enable_index_worker=True/False`）—— 内嵌时省部署，外置时扩缩容灵活
- **`PermissionEngine` 实例 per request**（不是全局）—— 每个请求独立做权限决策

源码锚点：
- 进程初始化：`src/agentscope/app/_lifespan.py`
- `WakeupDispatcher`：`src/agentscope/app/_manager/_wakeup_dispatcher.py:61`
- `CancelDispatcher`：`src/agentscope/app/_manager/_cancel_dispatcher.py:28`
- `ChatRunRegistry`：`src/agentscope/app/_manager/_chat_run_registry.py:23`
- `BackgroundTaskManager`：`src/agentscope/app/_manager/_background_task_manager.py:216`

---

## 3. 分布式 Session 互斥（时序 + 副本视图）

```mermaid
sequenceDiagram
    autonumber
    actor U as User
    participant LB
    participant API1 as API Replica 1
    participant API2 as API Replica 2
    participant R as Redis
    participant WS as Workspace Sandbox

    U->>LB: POST /chat (sid=S1)
    LB->>API1: 路由到副本 1
    API1->>R: acquire_lock(session_lock(S1), ttl=600s)
    R-->>API1: ✓ 拿到锁，TTL 心跳启动
    API1->>WS: 启动 Workspace 沙箱 (or 复用)
    WS-->>API1: 沙箱 ready
    API1->>U: SSE 开始推流 (event1, event2, ...)

    par 同时用户又发了一条
        U->>LB: POST /chat (sid=S1)
        LB->>API2: 路由到副本 2
        API2->>R: acquire_lock(session_lock(S1))
        R-->>API2: ⏳ 阻塞（心跳续期）
    end

    API1->>U: 推完所有 event
    API1->>R: release_lock(session_lock(S1))

    R-->>API2: ✓ 拿到锁
    API2->>WS: 复用/启动 Workspace
    API2->>U: SSE 推流 (event1, event2, ...)
    API2->>R: release_lock
```

**关键观察**：

- **Session 锁保证**：`同一 session 在同一时刻只有 1 个副本在执行 reply`——避免状态冲突
- **TTL=600s + 心跳**——API1 的 long-running reply 不会因 TTL 过期而丢锁
- **API1 crash 也不会死锁**——600s 后 API2 自动接管
- **Workspace 沙箱跟 session 走**——A 副本建的沙箱，B 副本接手后通过序列化状态能继续

源码锚点：
- `acquire_lock` 实现：`src/agentscope/app/message_bus/_redis_message_bus.py`（具体行需查）
- Lock 原语定义：`src/agentscope/app/message_bus/_base.py:386`

---

## 4. 跨副本事件传播（Wakeup / Cancel）

```mermaid
graph LR
    subgraph "API Replica 1"
        CS1[ChatService]
        WD1[WakeupDispatcher]
        CD1[CancelDispatcher]
    end

    subgraph "API Replica 2"
        CS2[ChatService]
        WD2[WakeupDispatcher]
        CD2[CancelDispatcher]
    end

    subgraph "API Replica 3"
        CS3[ChatService]
        WD3[WakeupDispatcher]
        CD3[CancelDispatcher]
    end

    R[(Redis Pub/Sub)]

    CS1 -- "publish(wakeup_signal)" --> R
    CS2 -- "publish(task_cancel, tid)" --> R
    R -- "wakeup_signal" --> WD1 & WD2 & WD3
    R -- "task_cancel" --> CD1 & CD2 & CD3

    WD1 -.如果本进程负责该 session.-> CS1[触发 reply]
    WD2 -.本进程不负责.-> X[忽略]
    WD3 -.本进程不负责.-> X

    CD2 -.匹配 task_id.-> CS2[取消该 chat task]
```

**关键观察**：

- **每个 API 副本都订阅了 wakeup_signal 和 task_cancel**——Redis Pub/Sub 广播给所有订阅者
- **每个 Dispatcher 收到事件后自决**——只处理本进程负责的（通过 `ChatRunRegistry` 查任务归属）
- **不负责的事件被丢弃**——所以"广播一次，每个副本决定要不要处理"是 O(N) 副本数，不是 O(N) 任务数
- **Wakeup 信号是 fire-and-forget**——**只通知当前在线的副本**，离线时丢消息（不持久化），所以**重要的任务通过 inbox queue 投递**

源码锚点：
- `WakeupDispatcher`：`src/agentscope/app/_manager/_wakeup_dispatcher.py`
- `CancelDispatcher`：`src/agentscope/app/_manager/_cancel_dispatcher.py`
- 关键 channel：`MessageBusKeys.wakeup_signal()`、`MessageBusKeys.task_cancel_channel()`

---

## 5. Workspace 沙箱的多后端选型

```mermaid
graph TB
    subgraph Abstract["WorkspaceBase (抽象)"]
        AB[list_mcps / list_skills / list_tools<br/>offload_context / offload_tool_result]
    end

    subgraph Local["Local - 单机开发"]
        LW[LocalWorkspace<br/>文件系统 workdir]
    end

    subgraph Container["Container - 单机生产"]
        DW[DockerWorkspace<br/>docker run]
    end

    subgraph Orch["K8s - 中大规模生产"]
        KW[K8sWorkspace<br/>Pod lifecycle]
    end

    subgraph Cloud["Cloud Sandbox - 隔离执行"]
        E2B[E2BWorkspace<br/>云端 firecracker microVM]
        DAY[DaytonaWorkspace<br/>云端 sandbox]
        OSW[OpenSandboxWorkspace<br/>阿里云沙箱]
    end

    subgraph Edge["Edge / Remote"]
        MCP[MCP Gateway<br/>跨网络协议]
    end

    AB --> LW
    AB --> DW
    AB --> KW
    AB --> E2B
    AB --> DAY
    AB --> OSW
    AB --> MCP

    classDef local fill:#e8f5e9
    classDef prod fill:#fff3e0
    classDef cloud fill:#fce4ec
    class LW local
    class DW,KW prod
    class E2B,DAY,OSW,MCP cloud
```

**选型矩阵**（架构师视角）：

| 后端 | 启动速度 | 隔离强度 | 成本 | 适用场景 |
|---|---|---|---|---|
| Local | 0（直接用） | ❌ 无 | $0 | 本地开发、单测 |
| Docker | 1-3s | 中（OS 级别） | 低 | 中小生产、单租户 |
| K8s | 5-15s | 中高 | 中 | 大生产、混合部署 |
| E2B | 2-5s | 高（microVM） | 中 | 多租户 SaaS |
| Daytona | 1-3s | 高 | 中 | 开发环境 |
| OpenSandbox | 2-5s | 高 | 低 | 国内云原生场景 |
| MCP Gateway | 即时 | 协议级 | 低 | 跨网络/跨语言集成 |

**关键设计观察**：

- **统一抽象层**——切换后端不改业务代码（`WorkspaceBase` 是接口）
- **Offload 机制跨后端通用**——`offload_context` 把压缩后的上下文存到 workspace 的 `sessions/` 目录
- **沙箱内运行的工具**通过 MCP 协议与 Agent 通信——沙箱是"另一台机器"，不是同进程

源码锚点：
- `WorkspaceBase`：`src/agentscope/workspace/_base.py`
- `LocalWorkspace`：`src/agentscope/workspace/_local_workspace.py`
- `DockerWorkspace`：`src/agentscope/workspace/_docker/_docker_workspace.py`

---

## 6. IndexWorker 的两种部署模式

```mermaid
graph TB
    subgraph ModeA["模式 A: 内嵌 IndexWorker (小规模)"]
        direction TB
        A1[API 进程内]
        A2[IndexWorker 实例]
        A3[IndexTaskConsumer]
        A4[共享进程的 MessageBus]
        A1 --> A2
        A1 --> A3
        A2 --> A4
    end

    subgraph ModeB["模式 B: 独立 IndexWorker (中大规模)"]
        direction TB
        B1[API 进程 1]
        B2[API 进程 2]
        B3[独立 IndexWorker 进程 1]
        B4[独立 IndexWorker 进程 2]
        B5[共享 Redis MessageBus]
        B1 --> B5
        B2 --> B5
        B3 --> B5
        B4 --> B5
    end

    classDef embedded fill:#e8f5e9
    classDef separate fill:#fff3e0
    class A1,A2,A3,A4 embedded
    class B1,B2,B3,B4,B5 separate
```

**模式 A（enable_index_worker=True）**：
- 适合：流量小（< 100 docs/day），不想多部署一个组件
- 缺点：API 进程要承担索引工作，CPU/IO 会影响 API 响应

**模式 B（独立进程）**：
- 适合：流量大、独立扩缩容
- 启动命令：`python -m agentscope.app.rag.index_worker`
- 优点：API 进程纯净，索引独立调优

**Sweeper 始终在 API 进程**（在 `_lifespan.py:135-145`）—— 因为它是"上传后立即触发索引"的兜底机制

源码锚点：
- 内嵌逻辑：`src/agentscope/app/_lifespan.py:128-148`
- IndexWorker：`src/agentscope/app/rag/index_worker/`

---

## 7. 数据流向（持久化 + 实时 + 离线）

```mermaid
graph LR
    subgraph RealTime["实时层 (Redis)"]
        IE[Session Events<br/>Stream]
        IQ[Session Inbox<br/>Queue]
        SL[Session Lock<br/>Key]
        WQ[Wakeup Queue<br/>Stream]
        BG[BG Tasks<br/>Hash]
    end

    subgraph Persistent["持久化层 (Redis Storage / DB)"]
        CR[Credentials]
        AR[Agents]
        SR[Sessions<br/>metadata]
        MS[Messages<br/>分页]
        ST[Schedules]
    end

    subgraph Blob["大对象层 (S3 / OSS)"]
        BS[Blobs<br/>文件、图片]
        KBI[Knowledge Base<br/>索引产物]
    end

    Sandbox[Workspace<br/>sessions/ dir]
    RAGIdx[Index Worker<br/>memory/]

    ChatService --> IE
    ChatService --> IQ
    ChatService --> SL
    Scheduler --> WQ
    BackgroundTask --> BG
    ChatService --> SR
    ChatService --> MS
    ChatService --> CR
    ChatService --> AR
    ChatService --> BS
    ChatService -.offload.-> Sandbox
    KBS --> RAGIdx
    RAGIdx --> KBI
```

**存储分层**：

| 数据 | 存哪 | 生命周期 | 备份需求 |
|---|---|---|---|
| Session Events | Redis Stream | session 结束 trim | 中（重放需要） |
| Session Inbox | Redis Queue | TTL | 低（可丢） |
| Session Lock | Redis Key | TTL=600s | 不需要 |
| Credentials | Redis (Storage) | 永久 | **高** |
| Agents 配置 | Redis (Storage) | 永久 | **高** |
| Session metadata | Redis (Storage) | 永久 | **高** |
| Messages | Redis (Storage) | 永久 | **高** |
| Blobs | S3/OSS | 永久 | **极高** |
| KB 索引 | 本地文件 + S3 | 永久 | 中 |
| 沙箱 sessions/ | Workspace 内 | session 期间 | 低（可重算） |

**架构师视角**：

- **热数据 vs 冷数据分层**——Redis 存热数据，Blobs 走对象存储，**不要什么都塞 Redis**（成本和性能都不划算）
- **Session 状态分两半**—— 元数据持久化（用户能看到），事件流 Redis（用户看不到）—— 这种"用户态 vs 系统态"分离是 SaaS 标配

源码锚点：
- `StorageBase`：`src/agentscope/app/storage/_base.py:26`
- `RedisStorage`：`src/agentscope/app/storage/_redis_storage.py:47`

---

## 8. 故障恢复矩阵

| 故障 | 影响 | 恢复机制 | 备注 |
|---|---|---|---|
| **API 副本宕机** | 该副本的 in-flight chat 中断 | (1) session 锁 TTL 过期 → 其他副本接管<br/>(2) WakeupDispatcher 在其他副本重新触发 | Redis 是 SPOF 之外的依赖 |
| **Redis 重启** | Session 锁、inbox、events 全清 | (1) 持久化配置（RDB+AOF）<br/>(2) 客户端重连 | 必须开 AOF |
| **Redis 网络分区** | 副本之间看不到彼此 | (1) 副本独立工作（最差情况重复执行）<br/>(2) 业务层做幂等 | 需要 Saga 模式 |
| **Workspace 沙箱崩溃** | 该 session 上下文丢失 | 从 Storage 重新加载 session metadata | 沙箱状态非持久化 |
| **IndexWorker 宕机** | 索引任务积压 | Sweeper 在 API 进程兜底重试 | Mode B 的核心价值 |
| **S3 不可用** | Blob 上传/下载失败 | (1) 业务重试<br/>(2) 降级为本地存储 | 多区域复制 |

**架构师视角**：

- **Redis 是 SPOF**——生产必须主从 + Sentinel/Cluster
- **API 副本无状态**——所以可以"挂了就重启"，不丢用户数据
- **沙箱是 ephemeral**——重要状态必须 offload 到 Storage，不要依赖沙箱持久化
- **IndexWorker 故障 = 索引延迟**——不影响主链路，**这是好设计**

---

## 9. 容量规划参考

| 指标 | 单副本 (8C16G) 估计 | 多副本 (3 副本) |
|---|---|---|
| 并发 chat | ~50 | ~150 |
| QPS (非流式) | ~200 | ~600 |
| SSE 并发连接 | ~500 | ~1500 |
| Redis 内存（10000 session） | ~1 GB | ~1 GB（共享） |
| Index 吞吐 | ~50 docs/min | 独立扩展无上限 |

**扩缩容策略**：

- **API 副本**：HPA 基于 CPU/连接数
- **Redis**：垂直扩展到 32G 后考虑 Cluster
- **IndexWorker**：基于队列长度
- **Workspace 后端**：按需扩（K8s HPA / E2B 自动）

---

## 10. 自我验证（按 deepseek 标准）

- [x] **能拆解**：10 张图 + 9 章节覆盖分布式全貌
- [x] **能扩展路径已识别**：每种故障都有恢复方案
- [x] **能排错起点**：故障恢复矩阵直接对照
- [x] **能评判**：选型矩阵给出 trade-off

✅ Phase 1 - Task 4 完成。**Phase 1 全部交付物已闭环**。

---

## 11. Phase 1 完整交付物清单

| # | 文件 | 内容 |
|---|---|---|
| 1 | `LEARNING.md` | 公开承诺 |
| 2 | `notes/phase-1/architecture.md` | 架构全景（6 图） |
| 3 | `notes/phase-1/class-diagrams.md` | 类族关系（5 图） |
| 4 | `notes/phase-1/sequence-diagrams.md` | 时序图（6 图） |
| 5 | `notes/phase-1/distributed-topology.md` | 分布式拓扑（10 图）|
| 6 | `notes/phase-1/public-commit-drafts.md` | 多平台文案 |
| 7 | `notes/README.md` | 学习日志主页 |
| 8 | `notes/debug-log.md` | 错题本 |
| 9 | blog post (sunrong.site) | W1 学习总结已发布 |

**接下来进 Phase 2**：W3 开始啃 `_agent.py` 2911 行源码。

---

## 12. 下一步

- **W1-D6**：ADR 架构评判（3 个关键决策的 trade-off 文档）
- **W2 周末**：周自检，填表，看 4 个维度的"知/行/破/建"
- **Phase 2-W3**：精读 `_agent.py` 2911 行，写源码注解 + 独立 Demo
