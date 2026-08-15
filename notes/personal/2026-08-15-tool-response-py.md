## 2026-08-15 | `tool/_response.py` — W5-D2 第 2 段

**读了什么**：`src/agentscope/tool/_response.py` (205 行) — ToolChunk + ToolResponse + 累积逻辑

**关键发现**：**3 大设计点** — **base64 helper + 4 条累积路径 + 状态优先级**。

---

### 2 个类 + 1 个 helper

```
_merge_base64_chunks:  工具函数  /  解决 base64 padding 问题
ToolChunk:            流式 chunk  /  is_last + state
ToolResponse:         完整 response  /  状态固定 4 选 1
```

### 4 条累积路径（append_chunk）

```
同 id 累加 (text + text)    →  text += text
同 id 累加 (data + data)    →  base64 decode + concat + encode
不同类型同 id               →  raise ValueError
不同 id                     →  新增 block
```

### 状态优先级

```python
ERROR > INTERRUPTED > DENIED  /  永不降级  /  严重度单调
```

---

### Q1（_merge_base64_chunks helper）✅⚠️ 浅

**你答**："独立 base64 / 尾部 = 号 / 直接拼装解码出错"

**为什么不能直接字符串 concat**：

```
# 1 字节 "a" 编码
base64.b64encode(b"a")  →  "YQ=="  (2 padding)

# 2 字节 "ab" 编码
base64.b64encode(b"ab")  →  "YWI="  (1 padding)

# 字符串 concat
"YQ==" + "YWI="  →  "YQ==YWI="  (长度 7)

# 解码失败！
binascii.Error: Invalid base64-encoded string
 /  /  number of data characters 7
 /  /  cannot be 1 more than a multiple of 4
```

**核心原因**：
- **有效 base64 长度必须是 4 倍数**
- **每个 chunk 内部有 padding**——**拼装后长度非 4 倍数**——**decode 失败**
- **= padding 出现在 chunk 内部**——**破坏 base64 语法**

**3 步修复**：

```python
def _merge_base64_chunks(existing, incoming):
    # 1. 解码（移除 padding 拿原始字节）
    existing_bytes = base64.b64decode(existing)  # b"ab"
    incoming_bytes = base64.b64decode(incoming)  # b"cd"
    
    # 2. 字节级拼接（不涉及 base64 编码）
    merged_bytes = existing_bytes + incoming_bytes  # b"abcd"
    
    # 3. 重新编码（重新算 padding）
    return base64.b64encode(merged_bytes).decode("ascii")  # "YWJjZA=="
```

**兜底分支**（`except binascii.Error`）——**测试用 placeholder 字符串**（"hello"）——**不是合法 base64**——**不能崩**——**W4 Robustness 实战**。

---

### Q2（4 条累积路径）✅✅ 强

**你答**："流式场景 / 相同 id 累加 / 不同 id 新增 / 多场景"

**为什么需要 2 种行为**：

| 模式 | 例子 | 行为 |
|---|---|---|
| **多 chunk 同一数据** | Bash 长输出 5 段 stdout | 5 chunk **同 id** → **累加** |
| **多 chunk 不同数据** | tool 返回 text + image + code | 3 chunk **不同 id** → **新增** |
| **混合** | Bash 输出 + 最终错误码 | 同 id + 1 不同 id → 混合 |

**如果只有 1 种**：

| 单一行为 | 后果 |
|---|---|
| **全部累加** | 不知道 text/image 边界——**丢失语义** |
| **全部新增** | Bash 5 段 → 5 个 TextBlock——**浪费 token** |

**路径 3 raise 谁会触发**——**真实场景**：

| 场景 | 谁触发 |
|---|---|
| **正常使用** | 永远不触发——**LLM 输出稳定** |
| **Tool 实现 bug** | tool 先返回 text 又返回 image 同 id——**bug** |
| **MCP 协议错** | 远程 tool 格式不一致——**上游 bug** |
| **mock 数据 bug** | 测试 mock 没设计好——**测试 bug** |

**所以**：
- **不是业务正常情况**——**是 bug 检测**
- **raise 比 silent fail 好**——**W5 "raise = Stop the world"**——**让开发者立刻发现**
- **vs yield error chunk**——**raise 强制修代码**——**yield 让 agent 重试（无效）**

**架构师视角**：

> **"Type mismatch = Compile error at runtime"**
> - **同 id 不同类型 = 协议层错**——**必须 fail-fast**
> - **fail-fast 让 bug 早暴露**——**上线前就抓到**
> - **不是"防御性编程"**——**是"协议层错检测"**

---

### Q3（状态优先级）✅✅ 强

**你答**："严重程度 / 反过来会覆盖 / DENIED 覆盖 ERROR / 真实错误被吞 / 调试灾难"

**为什么 ERROR > INTERRUPTED > DENIED**：

| 状态 | 含义 | 严重度 |
|---|---|---|
| **ERROR** | 工具出 bug / 网络错 | **最严重**——**必须查** |
| **INTERRUPTED** | 用户主动中断 | **中**——**用户知道** |
| **DENIED** | 权限拒绝 | **轻**——**配置问题** |

**"降级" 的灾难演示**：

```
Chunk 1: 工具返回 ERROR（真实错误）
Chunk 2: 工具又返回 DENIED（同一个 chunk 流）

如果允许降级：
  self.state = DENIED  →  覆盖了 ERROR
  →  用户看到 "权限拒绝" → 改权限 → 没用
  →  实际是网络错 → 永远失败

实际代码（保留 ERROR）：
  if chunk.state == ERROR:
      self.state = ERROR  →  永远保留最严重
  →  用户看到 ERROR → 查网络 → 找到根因
```

**"降级" = silent failure**——**W5 Robustness ≠ Strictness 的反面**——**太宽容 = 灾难**。

**架构师视角**：

> **"State priority = Severity monotonicity"**（状态优先级 = 严重度单调性）
> - **状态只能"升级"**——**不能"降级"**
> - **"降级" = silent failure**——**W5 Robustness 的反面**——**太宽容 = 灾难**
> - **同理**：日志级别 / 告警级别 / SLA 降级——**都遵循严重度单调**

---

## 我今天 3 个最大收获

1. **base64 padding = 长度非 4 倍数**——**字符串 concat 直接崩**——**必须 decode + 字节 concat + re-encode**
2. **Type mismatch = Compile error at runtime**——**同 id 不同类型 raise**——**fail-fast 让 bug 早暴露**
3. **Severity monotonicity**——**状态只能升级不能降级**——**"降级" = silent failure**——**W5 Robustness 反面**

## W5-D2 段 2 战绩

| 数据 | 数字 |
|---|---|
| 行数 | 205 |
| 笔记 | 1（本文）|
| 答 | 3 |
| 强 | 2 |
| 浅 | 1 |
| 缺 | 0 |
| 评分 | **7.5/10** |

## W5 累计战绩

| 段 | 文件 | 行数 | 笔记 | 强 |
|---|---|---|---|---|
| W5-D1 段 1 | skill/_local_loader.py | 172 | 1 | 2 |
| W5-D1 段 2 | tool/_base.py | 451 | 1 | 3 |
| W5-D2 段 1 | tool/_toolkit.py | 683 | 1 | 3 |
| **W5-D2 段 2** | **tool/_response.py** | **205** | **1** | **2** |
| **W5 累计** | | **1511** | **4** | **10** |

## 累计 W2 + W3 + W4 + W5

| 数据 | 数字 |
|---|---|
| 行数 | **4797 + 1511 = 6308** |
| 笔记 | **33 + 4 = 37** |
| 强 | **75 + 10 = 85** |
| 胜率 | **85/112 = 76%** |

## 仍不清楚的

- `tool/_builtin/_bash.py` 真实工具实现细节
- `tool/_adapters.py` MCP 适配器完整流程
- `_merge_base64_chunks` 是否处理了"中间 chunk 损坏"场景

## 接下来

W5-D2 段 2 闭环（205 行 + 1 笔记 + 3 答 2 强 + 7.5 分）。

**W5-D2 段 3 候选**：
- `tool/_builtin/_bash.py` (789 行) —— 真实工具
- `tool/_builtin/_read.py` / `_write.py` / `_edit.py` —— 文件操作
- `tool/_adapters.py` (394 行) —— MCP 适配器

**下午 1:46**——**今天 2 段 W5**——**W5 累计 4 段 1511 行**——**进度稳定**。
