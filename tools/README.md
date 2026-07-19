# 复习系统 (review.py)

基于 **SM-2 算法** 的自适应复习系统，纯 Python，零外部依赖。

## 核心特性

- ✅ **真自适应**：每次复习打分（0-3），间隔由 SM-2 算法动态计算
- ✅ **鲁棒追踪**：显式 `review` 命令，不用文件 mtime（防 typo 误判）
- ✅ **Leech 检测**：连续失败 3 次自动标记为 🩹 leech
- ✅ **毕业机制**：连续成功 3 次 + EF ≥ 2.5 自动标记为 🎓 mastered
- ✅ **可观测**：`stats` 命令看全局统计
- ✅ **零依赖**：纯标准库
- ✅ **可迁移**：改 `DATA_FILE` 就能切到其他项目

## 快速开始

```bash
# 1. 添加 Phase 1 的 5 份文档
python tools/review.py add --id agentscope-arch --title "AgentScope 架构全景" \
    --file notes/phase-1/architecture.md --difficulty 2

python tools/review.py add --id agentscope-classes --title "AgentScope 核心类图" \
    --file notes/phase-1/class-diagrams.md --difficulty 2

python tools/review.py add --id agentscope-seq --title "AgentScope 时序图" \
    --file notes/phase-1/sequence-diagrams.md --difficulty 2

python tools/review.py add --id agentscope-dist --title "AgentScope 分布式拓扑" \
    --file notes/phase-1/distributed-topology.md --difficulty 3

python tools/review.py add --id agentscope-commit --title "公开承诺" \
    --file LEARNING.md --difficulty 1

# 2. 每日 check
python tools/review.py due          # 今日应复习

# 3. 复习（交互式打分）
python tools/review.py review agentscope-arch

# 4. 统计
python tools/review.py stats
```

## 打分标准

| 分数 | 含义 | SM-2 quality |
|---|---|---|
| 0 | 完全忘了 / 答错 | 1 |
| 1 | 吃力才想起来 | 3 |
| 2 | 想了一会儿 | 4 |
| 3 | 秒答 | 5 |

## 间隔算法（SM-2 简化版）

- 成功 (1-3)：
  - 第 1 次成功 → 1 天后
  - 第 2 次成功 → 6 天后
  - 第 3 次成功+ → 上次间隔 × 当前 EF
- 失败 (0)：间隔重置为 1 天，`reps` 归零
- EF 调整：每次复习后都更新，最低不低于 1.3
- Leech：连续失败 ≥ 3 次标记为 🩹
- Mastered：连续成功 ≥ 3 次 且 EF ≥ 2.5 标记为 🎓

## 文件

```
tools/
├── review.py           # 主脚本
├── review_data.json    # 数据（git 跟踪，跨设备同步）
└── README.md           # 本文件
```

## 数据格式

```json
{
  "items": {
    "<id>": {
      "id": "...",
      "title": "...",
      "file": "...",
      "ef": 2.5,            // 当前 easiness factor
      "interval": 7,        // 当前间隔（天）
      "reps": 2,            // 连续成功次数
      "fail_streak": 0,     // 连续失败次数
      "is_leech": false,
      "is_mastered": false,
      "total_reviews": 5,
      "total_failures": 1,
      "next_due": "2026-07-26",
      "last_review": "2026-07-19 10:30:00",
      "history": [
        {"date": "...", "score": 2, "ef": 2.5, "interval": 7, "next_due": "..."}
      ]
    }
  },
  "meta": {"version": 1, "created": "2026-07-19"}
}
```

## 进阶用法

### 每天自动检查（cron）

```bash
# 每天早上 9 点提醒（macOS/Linux）
0 9 * * * cd /path/to/agentscope && python tools/review.py due
```

### 批量 review（脚本模式）

```bash
# 给所有到期项打 3 分（强制"秒答"，慎用）
python tools/review.py due | grep "^\s*\[" | awk '{print $2}' | tr -d '[]' | \
    xargs -I {} python tools/review.py review {} --score 3
```

## 待办（P2 之后做）

- [ ] Anki 卡片导出
- [ ] 多卡片 per 条目（用 cloze）
- [ ] Web UI
- [ ] 主题/tags 分类
- [ ] 难度自动调整（基于连续表现）
- [ ] 导出复习报告（HTML/PDF）
