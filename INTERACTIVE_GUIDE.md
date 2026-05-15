# 易道引擎交互式推演模式使用指南

> 本文档面向使用易道引擎进行**交互式叙事推演**的用户。如果你只需要一次性生成完整叙事，请参考 `QUICKSTART.md` 的批处理模式。

---

## 目录

- [1. 什么是交互式推演模式](#1-什么是交互式推演模式)
- [2. 快速开始](#2-快速开始)
- [3. 核心概念](#3-核心概念)
  - [3.1 世界与 tick](#31-世界与-tick)
  - [3.2 摄像机系统](#32-摄像机系统)
  - [3.3 变体语库](#33-变体语库)
  - [3.4 叙事连续性](#34-叙事连续性)
- [4. 命令详解](#4-命令详解)
- [5. 完整示例工作流](#5-完整示例工作流)
- [6. 故障排除](#6-故障排除)

---

## 1. 什么是交互式推演模式

传统模式下，易道引擎一次性运行 1500 ticks，自动选出"最佳事件"，输出一段完整的五幕史诗。

**交互式推演模式**让你成为"世界导演"：

- **控制节奏**：每次推进多少 ticks 由你决定
- **实时观察**：世界每推进一次，你可以选择是否让 LLM 解释当前状态
- **调整镜头**：像导演一样移动摄像机——聚焦某个角色、锁定某种文学视角
- **不满意就重来**：对 LLM 生成的叙事不满意？一键重新生成（不改变 world 状态）
- **保存进度**：随时保存完整会话，明天回来继续

```
你：推进 150 ticks
引擎：tick=150，检测到卦变 ⚡
你：解释此幕
LLM：生成第一幕叙事...
你：聚焦到父亲，锁定科幻变体
引擎：摄像机已调整
你：再推进 200 ticks
引擎：tick=350，稳态
你：解释此幕
LLM：生成父亲特写 + 科幻视角叙事...
```

---

## 2. 快速开始

### 2.1 环境准备

```bash
# 1. 安装依赖（只需要 numpy）
pip install numpy

# 2. 设置 LLM API Key（以 DeepSeek 为例）
# Linux/macOS:
export DEEPSEEK_API_KEY="sk-xxxxxxxx"
# Windows CMD:
set DEEPSEEK_API_KEY=sk-xxxxxxxx
# Windows PowerShell:
$env:DEEPSEEK_API_KEY="sk-xxxxxxxx"
```

支持的提供商：`deepseek`、`openai`、`claude`、`kimi`、`mimo`、`local`

### 2.2 启动交互模式

```bash
# 基础启动
python main.py --interactive

# 使用特定提供商
python main.py --interactive --provider deepseek

# 加载修仙世界观
python main.py --interactive --worldview xiuxian --provider deepseek

# 无 LLM 测试模式（只保存 prompts，不调用 API）
python main.py --interactive --no-llm
```

### 2.3 第一条命令

启动后会看到：

```
============================================================
【易道引擎 v5.1 交互推演模式】
============================================================
命令: [Enter]/n 下一步 | s N 推进N | e 解释 | focus 聚焦
      variant 变体 | variants 列变体 | r 重生成 | reset 重置
      save 保存 | load 加载 | status 状态 | q 退出
============================================================

[0]>
```

输入 `s 150` 并按回车：

```
[0]> s 150
  推进 150 ticks | tick=150 | 稳态
  输入 'e' 解释此幕，或继续推进
```

输入 `e`：

```
[150]> e

[生成叙事中...]
  [PASS] 正文中无'相位'
  [PASS] 正文中无'势能'
  ...
>>> 验证通过

# 连贯叙事
## 同一片土地
黄昏时分，父亲坐在门槛上...
...

[幕 1] tick=150 | 聚焦=family | 变体=无 | 验证=PASS | 累计tokens≈4200
```

---

## 3. 核心概念

### 3.1 世界与 tick

易道引擎的世界是**确定性**的——相同的初始状态和 tick 数，总是产生相同的结果。

- **tick**：世界的时间单位。每次 `tick()` 推进一息，所有场（卦象、气象、相位、势能）同步演化
- **最小推进间隔**：50 ticks。低于此值会被拒绝，因为 LLM 难以从变化过小的 snapshot 中写出有意义的叙事
- **卦变（flip）**：当某个实体的卦象发生变化时，引擎会标记 `⚡ 检测到 N 次卦变`。这通常意味着该实体经历了重大的结构性转变

### 3.2 摄像机系统

摄像机**不是给用户看的**，而是控制 LLM "观测世界的方式"。你调整摄像机参数，LLM 根据这些参数调整叙事的焦点和风格。

| 参数 | 说明 | 示例 |
|------|------|------|
| `focus` | 观测核心 | `family`（全家）、`father`（父亲）、`激变`（追踪协议） |
| `distance` | 叙事距离 | `closeup`（特写）、`medium`（中景）、`panorama`（全景） |
| `style` | 叙事风格 | `polished`（白描文学）、`raw`（结构化叙事） |
| `variant_lock` | 文学视角锁定 | `道家`/`科幻`/`神话`/`存在主义` 或英文别名 `dao`/`scifi`/`myth`/`exist` |

**默认配置**：`focus=family`, `distance=medium`, `style=polished`, `variant_lock=无`

### 3.3 变体语库

每个协议（承载、激变、深渊...）有 4 个系统默认变体：

| 中文标签 | 英文别名 | 内容风格 |
|---------|---------|---------|
| 道家 | `dao` | 庄子、老子、天人合一 |
| 科幻 | `scifi` | 戴森球、曲率引擎、AI 自举 |
| 神话 | `myth` | 盖亚、托尔、普罗米修斯 |
| 存在主义 | `exist` / `existentialism` | 萨特、海德格尔、加缪 |

**层级**：
1. **系统默认**（renderer.PROTOCOL_LIBRARY）— 不可修改
2. **世界观级**（`configs/worldviews/*.json` 中的 `lexicon_variants`）— 随世界观加载
3. **会话级**（运行时 `add-variant` 添加）— 当前会话有效，可写回世界观文件

### 3.4 叙事连续性

每次成功的 `explain()` 会自动将叙事摘要加入历史。下次 `explain()` 时，最近 2 幕的摘要会被注入 system prompt 的"前情提要"段落，提示 LLM 保持人物一致性。

```
## 叙事连续性提示
这是连续叙事的一部分。请保持以下前情中的人物一致性:
- 幕1 (tick=150): 父亲在书房整理旧物，发现一张泛黄的照片...
- 幕2 (tick=300): 母亲察觉到异样，但选择沉默...
```

**注意**：`reroll`（重新生成）不加入历史，避免重复。

---

## 4. 命令详解

### 推进与解释

| 命令 | 说明 |
|------|------|
| `[Enter]` / `n` | 推进默认间隔（150 ticks），自动检测变化 |
| `s N` | 强制推进 N ticks（最小 50） |
| `e` / `explain` | 解释当前幕（调用 LLM 生成叙事） |
| `r` / `reroll` | 重新生成当前叙事（不改变 world 状态） |

### 摄像机控制

| 命令 | 说明 |
|------|------|
| `focus NAME` | 聚焦：family / father / mother / eldest / second / youngest / 激变 / 承载 ... |
| `variant TAG` | 锁定变体：道家 / dao / 科幻 / scifi / 神话 / myth / 存在主义 / exist / off |
| `variants [PROTOCOL]` | 列出所有可用变体。不指定协议则列出全部 |
| `camera` | 显示当前摄像机配置 |

### 变体 CRUD

| 命令 | 说明 |
|------|------|
| `add-variant PROTOCOL TAG CONTENT` | 添加会话级变体。例：`add-variant 承载 我的变体 大地沉默如谜...` |
| `rm-variant PROTOCOL TAG` | 删除会话级变体（只能删自己加的） |

### 状态管理

| 命令 | 说明 |
|------|------|
| `reset` | 重置世界（tick=0，保留配置和变体） |
| `save NAME` | 保存完整会话（world + narrative_history + camera + variants） |
| `load NAME` | 加载会话 |
| `status` | 显示当前 world 状态摘要 |
| `q` / `quit` | 退出 |

---

## 5. 完整示例工作流

### 场景：导演一部家庭史诗

```bash
$ python main.py --interactive --worldview xiuxian --provider deepseek

[0]> s 200
  推进 200 ticks | tick=200 | 稳态

[200]> e
  [生成叙事中...]
  >>> 验证通过
  [幕 1] tick=200 | 聚焦=family | 变体=无 | 验证=PASS | 累计tokens≈3800
  # 五口之家在黄昏的庭院...

[200]> focus father
  摄像机聚焦已设置为: father

[200]> variant scifi
  变体已锁定为: scifi

[200]> s 300
  推进 300 ticks | tick=500 | ⚡ 检测到 8 次卦变

[500]> e
  [生成叙事中...]
  >>> 验证通过
  [幕 2] tick=500 | 聚焦=father | 变体=scifi | 验证=PASS | 累计tokens≈8500
  # 父亲——星际生态穹顶的最后守望者...
  # （叙事自动携带了幕1中父亲的人物底色）

[500]> focus family
  摄像机聚焦已设置为: family

[500]> variant off
  变体锁定已解除

[500]> s 500
  推进 500 ticks | tick=1000 | ⚡ 检测到 15 次卦变

[1000]> e
  [生成叙事中...]
  [幕 3] tick=1000 | 聚焦=family | 变体=无 | 验证=PASS | 累计tokens≈13000

[1000]> r
  [重新生成叙事中...]
  [重新生成] tick=1000 | 累计tokens≈17500
  # （同一 world 状态的另一版叙事）

[1000]> save my_epic
  会话已保存到: ./states/my_epic

[1000]> q
  [退出] 再见
```

### 第二天继续

```bash
$ python main.py --interactive --worldview xiuxian --provider deepseek

[0]> load my_epic
  会话 'my_epic' 加载成功

[1000]> status
  tick: 1000
  摄像机: 聚焦: family | 变体: 无 | 距离: 中景 | 风格: 白描
  叙事幕数: 3
  累计 tokens: 17500

[1000]> s 500
...
```

---

## 6. 故障排除

### 6.1 推进时提示"间隔太小"

```
[提示] 间隔太小（30 ticks），建议至少 50 ticks
```

**原因**：LLM 需要足够的变化才能写出有意义的叙事。
**解决**：使用 `s 100` 或更大的数值。

### 6.2 LLM 调用返回 401 Unauthorized

```
API 失败: 401 Client Error: Authorization Required
```

**原因**：API Key 未设置或错误。
**解决**：
```bash
export DEEPSEEK_API_KEY="sk-xxxx"  # Linux/macOS
set DEEPSEEK_API_KEY=sk-xxxx        # Windows CMD
```

### 6.3 LLM 调用返回 400 Bad Request

```
API 失败: 400 Client Error: Bad Request
```

**原因**：Windows 终端中文输入产生编码乱码（surrogates）。
**解决**：使用英文别名：`variant scifi` / `variant dao` / `variant myth`。

### 6.4 叙事中没有对话 / 对话太少

**原因**：白描模式（polished）默认鼓励用动作代替对话。
**解决**：这是正常风格，不是 bug。如需更多对话，可在 `explain` 后手动给 LLM 提要求（目前暂不支持 prompt 注入自定义指令）。

### 6.5 validator 报告"部分验证未通过"

常见假阴性：
- `映射标注中有系统概念锚定` — 通常是因为 LLM 用了 `# 对应关系标注` 而非 `### 对应关系标注`。已修复，如仍出现请更新到最新版本。
- `有对话描写` — LLM 确实在正文中写了对话（如 `"睡吧。"`），这是 LLM 的自由选择。

### 6.6 如何手动调用保存的 prompts

如果 LLM 调用失败或你想换模型：

```bash
# prompts 已自动保存到 outputs/<时间戳>/
ls outputs/20260515_200420/
# timeline_package.txt  system_prompt.txt  user_prompt.txt

# 复制到任意 LLM 平台手动调用
```

---

## 附录：文件结构

```
outputs/<时间戳>/
├── timeline_package.txt   # 语义包（给 LLM 的观测数据）
├── system_prompt.txt      # System Prompt
├── user_prompt.txt        # User Prompt
└── llm_output.txt         # LLM 生成的叙事（成功时）

states/<名称>/
├── world.npz              # 世界场数据（numpy）
├── world_meta.json        # 世界标量参数
├── trackers.json          # 实体历史
├── camera.json            # 摄像机状态
└── session.json           # 叙事历史 + 摄像机配置 + 变体
```

---

**许可证**：代码 Apache-2.0 / 文档 CC BY-SA 4.0
