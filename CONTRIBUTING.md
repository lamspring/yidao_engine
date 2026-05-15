# 贡献指南

感谢你对易道引擎的兴趣！本项目欢迎以下形式的贡献：

- **世界观配置** (`configs/worldviews/*.json`)
- **象法语库变体** (`lexicon_variants`)
- **Bug 修复**
- **文档改进**

---

## 快速开始

### 1. Fork & Clone

```bash
git clone https://github.com/YOUR_NAME/yidao_engine.git
cd yidao_engine
```

### 2. 安装依赖

```bash
pip install numpy
```

### 3. 运行测试

```bash
# 零配置测试（不调用 LLM）
python main.py --no-llm --worldview xiuxian
```

---

## 贡献世界观配置

### 文件位置

所有世界观配置放在 `configs/worldviews/` 目录下，文件名为 `{世界观名}.json`。

### 最小可运行示例

```json
{
  "name": "你的世界观名称",
  "description": "一句话描述这个世界观的核心设定",
  "protocol_map": {
    "承载": {
      "name": "映射名",
      "description": "该协议在此世界观中的具体含义",
      "sensory": {
        "visual": ["视觉元素1", "视觉元素2"],
        "sound": ["听觉元素1", "听觉元素2"],
        "mood": ["情绪元素1", "情绪元素2"]
      }
    }
  },
  "relation_templates": {
    "同体": "关系描述",
    "相生": "关系描述"
  },
  "character_archetypes": {
    "father": "角色原型描述",
    "mother": "角色原型描述",
    "eldest": "角色原型描述",
    "second": "角色原型描述",
    "youngest": "角色原型描述"
  }
}
```

### 必填字段

| 字段 | 说明 | 必填 |
|------|------|------|
| `name` | 世界观名称 | ✅ |
| `description` | 世界观描述 | ✅ |
| `protocol_map` | 8 协议映射 | ✅ |
| `protocol_map[].name` | 协议在此世界观中的名称 | ✅ |
| `protocol_map[].description` | 协议在此世界观中的描述 | ✅ |
| `protocol_map[].sensory` | 感官描述 | ✅ |
| `protocol_map[].sensory.visual` | 视觉元素（至少 1 个） | ✅ |
| `protocol_map[].sensory.sound` | 听觉元素（至少 1 个） | ✅ |
| `protocol_map[].sensory.mood` | 情绪元素（至少 1 个） | ✅ |
| `relation_templates` | 体用关系模板 | 可选 |
| `character_archetypes` | 角色原型 | 可选 |
| `flip_ritual` | 卦变仪式模板 | 可选 |
| `protocol_map[].lexicon_variants` | 文学语库变体 | 可选 |

### 协议覆盖要求

**强烈建议**覆盖全部 8 个协议：
- `承载`（坤）— 大地、承载、孕育
- `激变`（震）— 雷霆、突变、觉醒
- `深渊`（坎）— 深渊、潜伏、未知
- `渗透`（巽）— 渗透、传播、无形
- `止界`（艮）— 边界、停止、固化
- `显文明`（离）— 光明、文明、依附
- `交换`（兑）— 交换、愉悦、连接
- `创序`（乾）— 创造、秩序、主动

如果某个协议在你的世界观中确实不存在，请在 PR 描述中说明原因。

---

## 贡献象法语库变体 (`lexicon_variants`)

`lexicon_variants` 是世界观配置中的可选字段，为每个协议提供多段文学化的感官描写，供 LLM 在叙事时复用。

### 生成方式

**推荐**：使用官方工具自动生成：

```bash
python tools/generate_worldview_lexicon.py \
  --worldview 你的世界观名 \
  --provider deepseek \
  --variants 5
```

生成后**必须人工审核**，删除不贴切的段落，保留高质量的。

**手动编写**：直接编辑 JSON 文件，在 `protocol_map[协议]` 下添加 `lexicon_variants` 数组。

### 质量标准

每一段变体必须满足：

1. **长度**：40-80 字
2. **内容**：纯感官描写（视觉、听觉、触觉、嗅觉、味觉、情绪、节奏）
3. **禁止**：系统术语（卦名、协议名、相位、势能、数字数据等）
4. **锚定**：必须让系统概念通过纯文学手段可被感知
5. **多样性**：同一协议的多个变体之间要有明显差异

### ✅ 合格示例

```json
"lexicon_variants": [
  "黑雾深处，骨灯的火苗一动不动，像是某种东西在黑暗中屏住了呼吸",
  "血月倒影在水面破碎成千万片，每一片里都藏着一张未曾睁开的脸",
  "锁链拖动的声音从四面八方传来，却找不到来源——仿佛整个空间本身就是囚笼"
]
```

### ❌ 不合格示例

```json
"lexicon_variants": [
  "深渊协议处于高相位状态，势能积累中",  // 包含系统术语
  "这是一个很深的地方",  // 过于笼统，没有感官细节
  "黑雾深处，骨灯的火苗一动不动，像是某种东西在黑暗中屏住了呼吸"  // 与上一段完全相同（重复）
]
```

---

## 提交前自检

在提交 PR 之前，请运行以下检查：

### 1. JSON 格式验证

```bash
python -m json.tool configs/worldviews/你的世界观.json > /dev/null
```

无输出说明格式正确。

### 2. 功能测试

```bash
# 测试是否能正确加载
python main.py --no-llm --worldview 你的世界观 --ticks 100
```

### 3. 语库变体检查（如有）

```bash
python -c "
import json
d = json.load(open('configs/worldviews/你的世界观.json'))
for p, e in d.get('protocol_map', {}).items():
    vs = e.get('lexicon_variants', [])
    for i, v in enumerate(vs):
        assert 20 <= len(v) <= 200, f'{p}[{i}] 长度异常: {len(v)}'
        forbidden = ['卦', '相位', '势能', '协议', '趋势', '爻']
        for term in forbidden:
            assert term not in v, f'{p}[{i}] 包含禁用词: {term}'
print('检查通过')
"
```

---

## Pull Request 流程

1. **Fork** 本仓库
2. **创建分支**：`git checkout -b worldview/你的世界观名`
3. **添加/修改文件**：`configs/worldviews/你的世界观.json`
4. **提交**：`git commit -m "[worldview] 添加 XXX 世界观"`
5. **Push**：`git push origin worldview/你的世界观名`
6. **创建 PR**：使用 PR 模板填写相关信息

### PR 审核标准

**⚠️ 重要：所有 PR 必须经过维护者 (@lamspring) 的人工审核后方可合并。CI 自动检查仅作为辅助，不构成通过许可。**

维护者会人工检查：
- JSON 格式是否合法
- 必填字段是否完整
- `lexicon_variants` 是否符合质量标准（文学性、感官丰富度、无系统术语）
- 世界观设定是否与《易经》卦象结构兼容（不强制 1:1，但不能根本冲突）
- 内容是否涉及敏感、违法或垃圾信息

即使 CI 检查全部通过，也不代表 PR 会被自动合并。请耐心等待维护者审核。

---

## 审核与合并政策

- **所有贡献必须经过人工审核**，无自动合并
- 维护者保留拒绝任何 PR 的权利，无需说明理由
- 被拒绝的常见原因：质量不达标、与项目理念冲突、包含不当内容

## 许可证

- **世界观配置**（`configs/worldviews/*.json`）：CC BY 4.0
  - 提交即表示你同意在此许可证下发布你的贡献
  - 保留署名权，允许他人自由改编和商业使用

---

## 联系方式

如有疑问，欢迎：
- 创建 Issue 讨论
- 发送邮件至 lamspring@yeah.net
