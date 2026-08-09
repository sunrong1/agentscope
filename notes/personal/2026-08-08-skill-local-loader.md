## 2026-08-08 | `skill/_local_loader.py` — W5-D1 第 1 段

**读了什么**：`src/agentscope/skill/_local_loader.py` (172 行)

**关键发现**：**本地 Skill 加载器——5 大设计点的实战**。

---

### LocalSkillLoader 5 大设计点

```
1. SKILL.md = frontmatter (YAML) + body (markdown)
2. Cache: key=skill_root, invalidates by mtime
3. Concurrent: asyncio.gather(*tasks) — N 个 SKILL.md 并发读
4. Error isolation: 3 道防线 (try/except + return_exceptions + 二次过滤)
5. scan_subdir: 单层 vs 递归
```

### SKILL.md 格式

```yaml
---
name: my_skill
description: ...
---
这里是 markdown 格式的 skill 内容
```

---

### Q1（mtime vs hash 缓存）✅✅ 强

**你答**（升级版）："hash 慢 + 复杂 + skill 文件较小 + 误判影响不大 + 本地 mtime 轻量"

**架构师视角**：

> **"Speed > Perfect accuracy"**（速度 > 完美准确）
> - mtime 误判 invalidate = 重新读 = 浪费 1 次 I/O（KB 级几毫秒）
> - mtime 误判 valid = 用旧内容 = BUG 风险（FS 精度不够时）
> - hash 万无一失 = 每次都读全文 + 算 hash = 慢 100x
> - **AgentScope 选 mtime**——**因为 SKILL.md 是小文件**——**误判 invalidate 成本极低**

**判断标准**：

| 场景 | mtime | hash |
|---|---|---|
| 小文件 + 本地 FS | ✅ | 杀鸡用牛刀 |
| 大文件（GB）| ✅ | ✅ 值得 |
| 跨机器 / NFS | ⚠️ | ✅ |
| 关键数据 | ❌ | ✅ |
| **AgentScope Skill** | ✅ | ❌ 太重 |

**mtime 3 个真实问题**：
1. `touch` 改 mtime 不改内容
2. FAT32 等 FS 只有 2s 精度
3. NFS clock skew

---

### Q2（asyncio.gather 并发）✅✅ 强

**你答**（升级版）："并发 + skill 多 + IO 慢 + 错误隔离 + 不相互影响"

**关键设计**：

```python
# 第 1 层：asyncio.to_thread(os.walk) — 不阻塞 event loop
skill_dirs = await asyncio.to_thread(_find_skill_dirs)

# 第 2 层：asyncio.gather(*tasks, return_exceptions=True) — 并发 + 隔离
results = await asyncio.gather(*tasks, return_exceptions=True)
```

**vs 顺序加载**：

| 维度 | 顺序 | 并发 |
|---|---|---|
| 总时间 | N × I/O | max(I/O) |
| 错误隔离 | 1 错全错 | **return_exceptions 防** |
| 资源占用 | 1 个 | N 个 |
| 顺序保证 | 严格 | 不保证 |

**架构师视角**：

> **"Concurrency = parallelism + error isolation"**（并发 = 并行 + 错误隔离）
> - **顺序加载** = 1 步错 → 后面全错
> - **并发加载 + return_exceptions** = 1 步错 → 其它继续
> - **`return_exceptions=True`** = **关键**——**没有它 = 并发不如顺序**

**asyncio.to_thread 的意义**：
- `os.walk` 是同步的——阻塞 event loop
- 1000 个子目录 = 1000ms 阻塞 = 其他请求全卡
- to_thread 放到线程池——event loop 不阻塞

---

### Q3（错误隔离 3 道防线）✅⚠️ 浅

**你答**："优雅降级 + 提升体验"

**"优雅降级" vs "快速失败"——根本是 2 个相反的设计哲学**：

| 维度 | 优雅降级（AgentScope）| 快速失败（Fail-Fast）|
|---|---|---|
| 异常处理 | catch + log + default | let it crash |
| 可用性 | 高——1 错不影响其他 | 低——1 错拖垮全系统 |
| debug | 高——错误被吞，要查 log | 低——异常直接抛 |
| 适用 | 通用框架 / 公共组件 | 业务关键 / 单元测试 |

**3 道防线**：

```python
# 防线 1：单 skill try/except
try:
    ...
except Exception as e:
    logger.warning(...)
    return None  # ← 不抛

# 防线 2：gather return_exceptions=True
results = await asyncio.gather(*tasks, return_exceptions=True)
# 异常 → result

# 防线 3：list_skills 二次过滤
for i, result in enumerate(results):
    if isinstance(result, Exception):
        logger.warning(...)
    elif result is not None:
        skills.append(result)
```

**为什么 Skill loader 选优雅降级**：

| 理由 | 说明 |
|---|---|
| **1 个 skill 错 ≠ 整个 framework 错** | 不应因某用户的 SKILL.md 写错就全崩 |
| **用户写错是常态** | SKILL.md 用户编辑——会写错——必须容错 |
| **启动期 fail-fast 太重** | skill loader 在启动期调——失败 = app 起不来 |
| **observability 优先** | log warning + continue = 监控可见 + 系统可用 |

**架构师视角**：

> **"Robustness ≠ Strictness"**（健壮 ≠ 严格）
> - **优雅降级** = **系统健壮**——**1 个组件失败不影响整体**
> - **快速失败** = **代码严格**——**任何错误立即可见**
> - **框架代码选优雅降级**——**业务代码选快速失败**
> - **AgentScope 是 framework**——**必须优雅降级**——**否则 1 个用户写错 = 整个 app 崩**

---

## 我今天 3 个最大收获

1. **Speed > Perfect accuracy**（小文件 + 本地 FS → mtime 完美——hash 杀鸡用牛刀）
2. **Concurrency = parallelism + error isolation**（`return_exceptions=True` 是关键）
3. **Robustness ≠ Strictness**（框架选容错，业务选严格——3 道防线保证可用性）

## W5-D1 段 1 战绩

| 数据 | 数字 |
|---|---|
| 行数 | 172 |
| 笔记 | 1（本文）|
| 答 | 3 |
| 强 | 2 |
| 浅 | 1 |
| 缺 | 0 |
| 评分 | **7.5/10** |

## 累计 W2 + W3 + W4 + W5

| 数据 | 数字 |
|---|---|
| 行数 | **4565 + 172 = 4737** |
| 笔记 | **31 + 1 = 32** |
| 强 | **70 + 2 = 72** |
| 胜率 | **72/99 = 73%** |

## 仍不清楚的

- `SkillLoaderBase`（skill/_base.py，29 行）的抽象方法
- `Skill` 数据类的字段（`skill/__init__.py` 导出）
- 其他 skill loader（远程？MCP？）

## 接下来

W5-D1 段 1 闭环（172 行 + 1 笔记 + 3 答）。

W5 计划 = 工具与插件 + tracing。

**W5-D1 段 2 候选**：
- `tool/_base.py` (451 行) — ToolBase 抽象类
- `skill/_base.py` (29 行) — 太小，跳过
- `tool/__init__.py` (1151 字节) — 太小，跳过

**我建议 `tool/_base.py` (451 行)**——**和 W4 ChatModelBase 平行**——**对照读**。

**18:15**——**今天 W5 起步**——**晚 9 点收工**——**还有 1 段空间**。
