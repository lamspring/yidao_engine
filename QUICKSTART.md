# 易道引擎快速上手

> 基于《易经》卦象的确定性世界模拟器 + LLM 叙事生成管道

---

## 一句话介绍

易道引擎（YVM）用 64 卦的数学结构驱动世界演化，然后让 LLM 作为"观象者"把结构数据翻译成人类可读的叙事。它不是让 AI "编故事"，而是给 AI 一个**真实运行的世界**去观察和描述。

---

## 环境要求

- Python 3.10+
- 依赖：`numpy`（唯一必需依赖）
- LLM API 访问（可选，可用 `--no-llm` 仅运行模拟）

```bash
pip install numpy
```

---

## 目录结构

```
yidao_engine/
├── main.py                   # 统一入口（推荐）
├── pipeline/                 # 工作流管道
│   ├── config.py             # 配置管理
│   ├── world_runner.py       # 世界模拟
│   ├── detector.py           # 事件检测
│   ├── semantic.py           # 语义包构造
│   ├── llm_client.py         # LLM API 客户端
│   ├── prompts.py            # Prompt 模板（raw / polished）
│   └── validator.py          # 输出验证
├── configs/                  # 配置文件
│   ├── llm_providers.json    # LLM 提供商配置
│   └── worldviews/           # 世界观配置
│       ├── xiuxian.json      # 修仙世界观示例
│       └── cthulhu.json      # 克苏鲁世界观示例
├── outputs/                  # 输出目录（按时间戳自动创建）
│   └── 20260515_161335/
│       ├── timeline_package.txt   # 语义数据包
│       ├── system_prompt.txt      # 系统提示
│       ├── user_prompt.txt        # 用户提示
│       ├── llm_output.txt         # LLM 生成的叙事
│       └── meta.json              # 运行元数据
├── stage1~6_*.py             # 独立测试脚本（保留用于调试）
└── AGENTS.md                 # LLM 结构翻译协议（v5.0 + Route-C）
```

---

## 快速开始

### 1. 最简运行（五口之家 + 白描风格）

```bash
python main.py
```

默认参数：
- 模式：`family`（五口之家）
- 风格：`polished`（白描，正文无系统数据）
- tick：1500
- LLM：`mimo-v2.5-pro`
- 世界观：通用（无绑定）

### 2. 切换世界观

```bash
# 修仙门派史诗
python main.py --worldview xiuxian

# 克苏鲁疯狂叙事
python main.py --worldview cthulhu
```

### 3. 切换 LLM 提供商

```bash
# OpenAI
python main.py --provider openai

# DeepSeek
python main.py --provider deepseek

# Claude
python main.py --provider claude

# 本地模型（Ollama）
python main.py --provider local
```

**API Key 设置**：在 `configs/llm_providers.json` 中查看对应的环境变量名，然后：

```bash
# Linux/macOS
export OPENAI_API_KEY="sk-..."

# Windows
set OPENAI_API_KEY=sk-...
```

### 4. 切换叙事风格

```bash
# polished：白描手法，正文零数据引用（推荐用于阅读）
python main.py --style polished

# raw：保留系统数据引用（推荐用于验证/调试）
python main.py --style raw
```

### 5. 离线模式（不调用 LLM）

```bash
python main.py --no-llm
```

只运行世界模拟并生成语义包，保存到 `outputs/{时间戳}/timeline_package.txt`。等网络恢复后可手动调用 LLM。

### 6. 切换运行模式

```bash
# 单实体连续叙事
python main.py --mode single

# 双实体交叉互动叙事
python main.py --mode dual

# 五口之家家庭史诗（默认）
python main.py --mode family
```

### 7. 完整参数示例

```bash
python main.py \
  --mode family \
  --style polished \
  --worldview xiuxian \
  --provider deepseek \
  --ticks 1500 \
  --interval 150 \
  --output ./my_stories
```

---

## 输出文件说明

每次运行会在 `outputs/{时间戳}/` 下生成：

| 文件 | 内容 |
|------|------|
| `timeline_package.txt` | 系统语义数据包（体/用/势/关系/感官） |
| `system_prompt.txt` | 发给 LLM 的系统提示 |
| `user_prompt.txt` | 发给 LLM 的用户提示（含语义包） |
| `llm_output.txt` | LLM 生成的叙事正文 |
| `meta.json` | 运行元数据（模式/风格/世界观/模型等） |

---

## 自定义世界观

在 `configs/worldviews/` 下新建 JSON 文件即可。

**最小示例** (`configs/worldviews/赛博朋克.json`)：

```json
{
  "name": "夜之城2088",
  "description": "赛博朋克废土世界观",
  "protocol_map": {
    "承载": {
      "name": "荒坂塔",
      "description": " corporate 秩序与压迫",
      "sensory": {
        "visual": ["霓虹", "玻璃幕墙", "监控眼"],
        "sound": ["机械嗡鸣", "电梯升降", "广播"],
        "mood": ["压抑", "秩序", "冷漠"]
      }
    },
    "显文明": {
      "name": "夜之城霓虹",
      "description": "光怪陆离的赛博显化"
    }
  },
  "character_archetypes": {
    "father": "公司特工 — 维护体系运转的齿轮",
    "mother": "街头黑客 — 在数据流中滋养反抗者",
    "eldest": "独狼雇佣兵 — 在刀口舔血的锋芒",
    "second": "义体医生 — 探索人体与机械的边界",
    "youngest": "AI 觉醒者 — 数字世界的新生变数"
  }
}
```

运行：
```bash
python main.py --worldview 赛博朋克
```

完整字段参考现有示例：`xiuxian.json`、`cthulhu.json`。

---

## 自定义 LLM 提供商

在 `configs/llm_providers.json` 中添加新条目：

```json
{
  "my_api": {
    "name": "My Custom API",
    "base_url": "https://api.example.com/v1",
    "api_key_env": "MY_API_KEY",
    "default_model": "gpt-4",
    "temperature": 0.7,
    "max_tokens": 4000,
    "timeout": 120,
    "max_retries": 2
  }
}
```

运行：
```bash
export MY_API_KEY="sk-..."
python main.py --provider my_api
```

---

## 已有测试脚本

`stage1~6_*.py` 是开发过程中保留的独立测试脚本，用于验证各阶段功能：

| 脚本 | 用途 |
|------|------|
| `stage1_baseline.py` | 基线数据生成 |
| `stage2v3_llm_test.py` | Route-C 协议验证（同体场景） |
| `stage2v4_tension_test.py` | 强张力对冲场景测试 |
| `stage4_continuous_narrative.py` | 连续观测 + 叙事连贯性 |
| `stage5_multi_entity.py` | 双实体交叉互动 |
| `stage6_family_epic.py` | 五口之家家庭史诗 |
| `stage6_v2_polished.py` | 白描精修版（独立API调用） |

日常使用推荐 `main.py`，测试脚本仅用于调试或研究。

---

## 核心协议

- **Route-C**：骨架（系统精确概念）+ 血肉（LLM 具象化）+ 强制映射标注
- **分层架构**：Layer 1（卦象内核）→ Layer 2（结构感知层）→ Layer 3（LLM 叙事层）
- **关键约束**：LLM 禁止自我解释卦象、禁止绝对吉凶判断、禁止丢弃系统概念

详见 `AGENTS.md`（第 20 章：叙事生成协议 Route-C）。

---

## 状态管理（长期记忆 + 增量演化）

易道引擎支持世界状态的保存与恢复，让同一个世界可以跨会话持续运行。

### 保存状态

```bash
# 运行结束后自动保存
python main.py --save my_world

# 指定状态保存目录
python main.py --save my_world --state-dir ./my_states
```

状态包含：
- 世界五场（gua/trend/phase/potential/stable_age）
- 时序与道控制器参数
- 所有实体的历史轨迹
- 摄像机位置与跟踪状态

### 加载状态继续运行

```bash
# 加载之前保存的世界，继续运行 500 tick
python main.py --load my_world --ticks 500 --save my_world_v2

# 不加 --save 则只加载运行，不保存（用于观察）
python main.py --load my_world --ticks 500 --no-llm
```

### 列出所有状态

```bash
python main.py --list-states

# 输出示例：
#   test_world:    tick=500  | H=32x64
#   test_world_v2: tick=1000 | H=32x64
```

### 状态目录结构

```
states/
  my_world/
    world.npz          # numpy 数组（gua/trend/phase/potential/stable_age）
    world_meta.json    # 标量参数（tick_count/道控制器/历史帧）
    trackers.json      # 实体追踪器历史
    camera.json        # 摄像机状态
```

### 典型工作流

```bash
# 1. 创建新世界，运行 1500 tick，保存为 alpha
python main.py --mode family --ticks 1500 --save alpha

# 2. 第二天加载 alpha，继续运行 500 tick，观察变化，保存为 alpha_v2
python main.py --load alpha --ticks 500 --save alpha_v2

# 3. 加载 alpha_v2，调用 LLM 生成叙事（这次不继续运行，只叙事）
python main.py --load alpha_v2 --ticks 0
```

---

## 故障排查

| 问题 | 解决 |
|------|------|
| API 调用失败 / DNS 错误 | 检查网络，或改用 `--no-llm` 离线模式 |
| `UnicodeEncodeError` | 已自动修复（UTF-8 stdout 重定向） |
| 世界观配置找不到 | 确认文件在 `configs/worldviews/` 下且为 `.json` |
| LLM Key 未设置 | 检查对应的环境变量是否导出 |
| 加载状态失败 | 确认状态名正确，使用 `--list-states` 查看可用状态 |

---

> *"你不是在写作。你是在翻译。系统负责'准'。你负责'美'。"*
>
> —— AGENTS.md
