# 易道引擎 v4.0 · 完整架构设计

> **原则**：引擎必须产生累积的物理状态。LLM 只能翻译，不能发明。
> **改动范围**：kernal.py 不动。其余全改。

---

## 一、文件结构

```
yidao_engine/
├── kernel.py          [不动] 64卦数学 + 5场 + tick()
├── traces.py          [新建] 爻痕系统
├── artifacts.py       [新建] 礼器场系统
├── chronicle.py       [新建] 史官簿系统
├── zhengying.py       [新建] 征应链系统
├── mandate.py         [新建] 月令系统
├── cosmos.py          [重写] 多网格编排器，整合所有新系统
├── entity.py          [重写] 跨网格实体，感知痕迹和礼器
├── observer.py        [升级] 快照包含痕迹/礼器/史官簿/征应/月令
├── pipeline/
│   ├── config.py      [扩展] 新增各系统的配置项
│   └── llm_client.py  [不动]
├── yan_camera.py      [重写] 时间线包注入全部引擎状态
└── configs/worldviews/evil-spirit-harvest-tax.json  [扩展] 启用新系统
```

---

## 二、traces.py — 爻痕系统

### 2.1 概念

每次卦变在网格中留下一条"爻痕"。爻痕有位置、时间、强度、类型。强度随时间衰减但永不归零。LLM 读取 snapshot 时看到爻痕即看到"这个世界经历过什么"。

### 2.2 数据结构

```python
@dataclass
class YaoTrace:
    tick: int           # 发生时世界 tick
    grid_name: str      # 所属网格名（tian/ren/di）
    y: int              # 行坐标
    x: int              # 列坐标
    pre_hex: int        # 变化前卦值 (0-63)
    post_hex: int       # 变化后卦值 (0-63)
    change_type: str    # 变化类型："错卦""综卦""复卦""杂卦"或"爻变"
    trend_at: float     # 变化时 trend 值
    potential_at: float # 变化时 potential 值
    intensity: float    # 初始 1.0，每息乘 decay_rate

@dataclass  
class TraceField:
    """管理一个网格的所有爻痕"""
    grid_name: str
    H: int; W: int
    traces: List[YaoTrace]
    decay_rate: float         # 每息衰减率，默认 0.998（约 500 息后半衰）
    intensity_map: np.ndarray # H×W，每个格子的累积爻痕强度
    history: List[str]        # 史官簿文本条目（该网格）
```

### 2.3 核心方法

```python
def record_change(tick, grid_name, y, x, pre, post, trend, potential):
    """卦变发生时调用。生成 YaoTrace，累加到 intensity_map"""

def tick_decay():
    """每息调用。所有 trace.intensity *= decay_rate；更新 intensity_map"""

def get_region_traces(y0, x0, h, w, min_intensity=0.1) -> List[YaoTrace]:
    """返回区域内强度>阈值的爻痕，按强度降序"""

def get_top_traces(grid_name, n=20) -> List[YaoTrace]:
    """返回该网格强度最高的 n 条爻痕"""

def format_ledger_entry(trace: YaoTrace) -> str:
    """生成春秋笔法史官记录：
    '息{750} {grid_name}宫({y},{x})发生{change_type}，{pre_name}→{post_name}，势能{potential:.2f}'
    """
```

### 2.4 春秋笔法格式化

```python
CHANGE_NAMES = {
    "错卦": "阴阳反位",
    "综卦": "本末倒悬", 
    "复卦": "七日来复",
    "杂卦": "刚柔交错",
    "爻变": "一爻动"
}

def format_ledger(trace):
    return (
        f"息{trace.tick}，{trace.grid_name}宫({trace.y},{trace.x})"
        f"{CHANGE_NAMES.get(trace.change_type, '变')}，"
        f"{get_gua(trace.pre_hex)['name']}→{get_gua(trace.post_hex)['name']}，"
        f"势能{trace.potential_at:.2f}"
    )
```

---

## 三、artifacts.py — 礼器场系统

### 3.1 概念

网格中某区域卦象长期稳定（stable_age > 阈值），自动"结晶"出礼器。礼器占据物理空间，有类型和属性，会修改局部卦场参数。LLM 读到礼器时必须承认其存在。

### 3.2 数据结构

```python
@dataclass
class Artifact:
    artifact_id: str       # 唯一ID，如 "liqi_ren_14_32"
    grid_name: str         # 所属网格
    y: int; x: int         # 位置
    artifact_type: str     # "鼎""镜""符""节""旌""鼓""碑""璧"
    born_tick: int         # 生成时的 tick
    stable_age: int        # 已稳定存在多少息
    gua: int               # 结晶时的卦值
    protocol: str          # 卦协议
    description: str       # 自动生成的描述文本
    modifiers: dict        # 对局部世界的修改，如 {"V_thresh": +0.2, "trend_bias": +0.1}

@dataclass
class ArtifactField:
    grid_name: str
    H: int; W: int
    artifact_map: np.ndarray  # H×W，0=无，1-8=礼器类型
    artifacts: Dict[str, Artifact]
    threshold: int            # 稳定多少息后生成，默认 80
```

### 3.3 礼器类型判定规则

```python
def determine_artifact_type(protocol, trend, phase, yang_ratio):
    """根据局部场状态决定生成何种礼器"""
    if protocol in ("承载","厚德") and trend > -0.1:
        return "鼎"   # 承载稳固 → 鼎。三足容器，不可移动，物理重量锚定空间。
    elif protocol in ("显文明","光辉") and phase > 0.4:
        return "镜"   # 文明显现 → 镜（鉴）。反射真相，揭示隐藏之物。
    elif protocol in ("交换","变通") and 0.3 < phase < 0.7:
        return "符"   # 交换进行中 → 符（契约）。两半对合，约定已立。
    elif protocol in ("止界","险阻") and yang_ratio < 0.4:
        return "节"   # 阴盛止界 → 节（门槛/禁忌）。不可随意穿越，强制叙事减速。
    elif protocol in ("发动","震动") and yang_ratio > 0.6:
        return "鼓"   # 阳动 → 鼓。此区域容易再次被动员。局部 V_thresh -0.2。
    elif phase > 0.7:
        return "旌"   # 高度活跃 → 旌旗。权威在场，标示"谁在管这里"。
    elif trend < -0.5:
        return "碑"   # 衰败 → 碑（碣）。记录发生过什么，不预设行为类型。
    else:
        return "璧"   # 默认 → 璧（环形玉）。循环、天意。弱强制，仅作存在标记。
```

### 3.4 各礼器详解

| 礼器 | 触发 | 含义 | 叙事强制力 | 世界效果 |
|------|------|------|-----------|---------|
| 鼎 | 承载/厚德 + trend>-0.1 | 青铜三足容器，极重。空间的"地基"。 | 强：鼎占据物理空间，LLM不能写"空无一物" | 无 |
| 镜 | 显文明/光辉 + phase>0.4 | 铜镜。反射隐藏真相。 | 中：暗示"此处曾被审视或揭露" | 无 |
| 符 | 交换/变通 + 0.3<phase<0.7 | 虎符/契约。两半对合。 | 中：约定已立，不能否认曾有过协议 | 无 |
| 节 | 止界/险阻 + yang<0.4 | 门槛/禁入标记。不可随意穿越。 | 最强：LLM必须写"跨过门槛"，不能写"径直走入" | 局部 V_thresh +0.2 |
| 鼓 | 发动/震动 + yang>0.6 | 召集之鼓。此处发生过动员。 | 中：曾有过警报或集结 | 局部 V_thresh -0.2 |
| 旌 | phase>0.7 | 旗帜。标示权威归属。 | 中：空间的支配者留下痕迹 | 无 |
| 碑 | trend<-0.5 | 石碑。记录发生过的事。 | 中：此处有过衰落或终结 | 无 |
| 璧 | 默认兜底 | 环形玉。循环、天意。 | 弱：仅作存在标记 | 无 |

### 3.4 核心方法

```python
def evolve(tick, stable_age, gua, trend, phase, potential, yang_ratio):
    """每息调用。检查每个格子是否满足生成/维持/消亡条件"""

def generate_artifact(grid_name, y, x, tick, stable_age, gua, protocol, trend, phase, yang_ratio):
    """生成礼器，记录到 artifact_map 和 artifacts"""

def get_region_artifacts(y0, x0, h, w) -> List[Artifact]:
    """返回区域内的礼器列表"""

def apply_modifiers(world_gua, world_trend, world_potential, world_V_thresh):
    """将礼器的 modifiers 应用到世界场参数上"""

def artifact_description(artifact: Artifact) -> str:
    """生成礼器的自然语言描述：
    '鼎在(14,32)，已存续120息。青铜色，三足，腹刻饕餮纹，沉稳不动。'
    """
```

---

## 四、chronicle.py — 史官簿系统

### 4.1 概念

每次卦变自动生成一条春秋笔法记录。不是 LLM 生成的，是引擎格式化的。LLM 读到的是"官方档案"，不能否认。

### 4.2 数据结构

```python
@dataclass
class ChronicleEntry:
    tick: int
    grid_name: str
    y: int; x: int
    entry_type: str  # "卦变""礼器生成""礼器消亡""征应触发""阈值突破"
    text: str        # 春秋笔法格式化文本
    severity: int    # 重要级 1-5

@dataclass
class Chronicle:
    entries: List[ChronicleEntry]
    max_entries: int  # 最多保留条数，默认 200
```

### 4.3 核心方法

```python
def record_change(grid_name, y, x, pre, post, change_type, potential, tick):
    """记录卦变"""

def record_artifact_born(artifact, tick):
    """记录礼器生成：'息{tick}，{grid}宫({y},{x})鼎成。自{born_tick}息至今稳定{age}息。'"""

def record_artifact_died(artifact, tick):
    """记录礼器消亡"""

def record_zhengying_triggered(chain, tick):
    """记录征应触发"""

def get_recent(n=50) -> List[ChronicleEntry]:
    """返回最近 n 条"""

def get_by_grid(grid_name, n=30) -> List[ChronicleEntry]:
    """按网格筛选"""

def format_for_llm(grid_name, n=20) -> str:
    """生成 LLM prompt 注入文本"""
```

---

## 五、zhengying.py — 征应链系统

### 5.1 概念

当特定卦象组合出现时，引擎注册一条未完成的因果链："征"已经发生，"应"的条件已设定。当条件满足时强制触发。LLM 读到 pending 的征应链时必须将"这个预言还没兑现"的状态写入叙事。

### 5.2 数据结构

```python
@dataclass 
class ZhengyingChain:
    chain_id: str
    grid_name: str
    sign_tick: int          # "征"发生时 tick
    sign_y: int; sign_x: int
    sign_gua: int           # 征的卦象
    sign_description: str   # 征的描述文本
    omen_text: str          # 占辞："阴极反阳，深渊出明"
    trigger_condition: dict # 应条件，如 {"gua_contains": [52,58], "within_ticks": 100, "region_radius": 5}
    status: str             # "pending""triggered""expired"
    trigger_tick: int       # 触发时 tick（未触发=-1）
    response_description: str # 应发生后的描述

@dataclass
class ZhengyingPool:
    chains: List[ZhengyingChain]
    max_chains: int  # 池上限，默认 10
```

### 5.3 核心方法

```python
def register_sign(grid_name, y, x, gua, potential, tick):
    """当 potential > 1.3 且卦变为特定组合时，注册一条征应链"""

def check_conditions(tick, gua_field, region):
    """每息检查所有 pending 链的应条件是否满足"""

def trigger(chain, tick):
    """应条件满足：标记为 triggered，生成应描述，触发局部场扰动"""

def expire_stale(tick, max_age=500):
    """清理超时未触发的链"""

def format_pending_for_llm() -> str:
    """生成 LLM 用的'未兑现预言'文本"""
```

### 5.4 征应触发规则

```python
SIGN_TEMPLATES = [
    {
        "name": "深渊出明",
        "condition": lambda gua, pot: gua == 29 and pot > 1.3,  # 坎卦 + 高势能
        "omen": "阴极反阳，深渊将出明。",
        "trigger": {"gua_contains": [30], "within_ticks": 150},  # 离卦出现 → 应
    },
    {
        "name": "雷入山止", 
        "condition": lambda gua, pot: gua == 51 and pot > 1.2,  # 震卦 + 高势能
        "omen": "动极生静，雷入山而止。山中将有物等待。",
        "trigger": {"gua_contains": [52], "within_ticks": 100},
    },
    {
        "name": "天地交泰",
        "condition": lambda gua, pot: gua == 11 and pot > 1.0,  # 泰卦
        "omen": "天地交而万物通。上下将合。",
        "trigger": {"protocol_contains": ["交换","变通"], "within_ticks": 200},
    },
]
```

---

## 六、mandate.py — 月令系统

### 6.1 概念

根据当前全局卦象组合，引擎自动生成一个"月令"——当前时节的规则约束。月令影响卦变趋势和 LLM 叙事方向。灵感来自《礼记·月令》。

### 6.2 数据结构

```python
@dataclass
class Mandate:
    active: bool
    season: str         # "春""夏""秋""冬"
    element_main: str   # 主气五行："木""火""金""水""土"
    element_guest: str  # 客气五行
    prohibition: str    # 禁忌行为
    encouragement: str  # 鼓励行为
    natural_signs: str  # 自然征兆描述
    updated_tick: int   # 更新时的 tick
    stable_for: int     # 已稳定多少息

@dataclass
class MandateSystem:
    current: Mandate
    history: List[Mandate]
    update_interval: int  # 多少息检测一次，默认 200
```

### 6.3 核心方法

```python
def detect_season(yang_ratio_global, trend_global, phase_global, tick):
    """根据全局场检测当前月令"""

def generate_mandate(season, yang_ratio, trend, phase) -> Mandate:
    """生成月令对象"""

def format_for_llm() -> str:
    """生成 LLM prompt 注入：
    '时值仲春，震木主事。雷将发声，蛰虫咸动。禁止刑杀，宜布德施惠。'
    """

def apply_constraints(world):
    """月令修改世界参数：禁止刑杀时降低 V_thresh、提升 dao_bias"""
```

### 6.4 季节判定

```python
# 基于全局 yang_ratio 在 200 息内的平均值
if avg_yang > 0.65: season = "夏"
elif avg_yang > 0.50: season = "春"  
elif avg_yang > 0.35: season = "秋"
else: season = "冬"

# 五行主气
ELEMENT_BY_SEASON = {"春": "木", "夏": "火", "秋": "金", "冬": "水"}

# 禁忌
PROHIBITIONS = {
    "春": "禁止伐木，毋覆巢，毋杀孩虫",
    "夏": "毋起土功，毋发大众",
    "秋": "毋封诸侯，毋以妾为妻",
    "冬": "毋发盖藏，毋起大众",
}
```

---

## 七、cosmos.py — 重写

### 7.1 新结构

```python
class Cosmos:
    def __init__(self, config):
        self.worlds: Dict[str, World] = {}
        self.trace_fields: Dict[str, TraceField] = {}     # 每网格一个
        self.artifact_fields: Dict[str, ArtifactField] = {} # 每网格一个
        self.chronicle = Chronicle()
        self.zhengying_pool = ZhengyingPool()
        self.mandate_system = MandateSystem()
        self.tick_count = 0
```

### 7.2 tick() 流程

```python
def tick(self):
    # Step 1-8: 各网格独立演化（原有逻辑）
    for w in self.worlds.values():
        w.tick()
    
    # Step 9: 记录爻痕
    for gname, w in self.worlds.items():
        changed = (w.gua != w._buf_gua)  # 需要对比旧值
        if changed:
            for y, x in changed_positions:
                self.trace_fields[gname].record_change(...)
                self.chronicle.record_change(...)
    
    # Step 10: 爻痕衰减
    for tf in self.trace_fields.values():
        tf.tick_decay()
    
    # Step 11: 礼器演化
    for gname, w in self.worlds.items():
        self.artifact_fields[gname].evolve(
            self.tick_count, w.stable_age, w.gua, w.trend, w.phase, w.potential
        )
    
    # Step 12: 礼器效果应用
    for gname, af in self.artifact_fields.items():
        af.apply_modifiers(self.worlds[gname])
    
    # Step 13: 征应检查
    for gname, w in self.worlds.items():
        self.zhengying_pool.register_sign(...)   # 检测新征
        self.zhengying_pool.check_conditions(...) # 检查应
        self.zhengying_pool.expire_stale(...)    # 清理过期
    
    # Step 14: 月令更新
    if self.tick_count % self.mandate_system.update_interval == 0:
        self.mandate_system.detect_and_update(...)
    
    # Step 15: 网格间交互（原有逻辑）
    for rule in self.interactions:
        ...
    
    self.tick_count += 1
```

---

## 八、entity.py — 重写

### 8.1 新增能力

每个 Entity 现在能感知其所处位置的：
- 爻痕（附近发生过什么）
- 礼器（附近有什么物体）
- 征应链（附近有什么未兑现的预言）

### 8.2 state_vector() 扩展

```python
def state_vector(self) -> dict:
    return {
        "entity_id": ...,
        "label": ...,
        "grids": {
            "ren": {
                "hex": 42, "hex_name": "既济",
                "phase": 0.12, "potential": 0.45, "trend": 0.31,
                "recent_flips": [...],
                # 新增
                "nearby_traces": [...],       # 附近爻痕
                "nearby_artifacts": [...],     # 附近礼器
                "pending_omens": [...],        # 附近未兑现征应
                "local_chronicle": [...],      # 该区域的史官记录
            }
        }
    }
```

---

## 九、observer.py — 升级

### 9.1 capture() 扩展

```python
def capture(self) -> dict:
    packet = {
        # 原有字段
        "observer_id": ...,
        "timestamp": ...,
        "focus": ...,
        "data": ...,
        
        # 新增
        "traces": self._get_focus_traces(),
        "artifacts": self._get_focus_artifacts(),
        "chronicle_recent": self.cosmos.chronicle.get_recent(20),
        "pending_omens": self.cosmos.zhengying_pool.format_pending(),
        "mandate": self.cosmos.mandate_system.format_current(),
    }
    return packet
```

---

## 十、yan_camera.py — 重写 _build_package

### 10.1 时间线包新结构

```python
def _build_package(self, snapshots, total_ticks):
    lines = [
        f"【观测世界】{self.worldview_label} — 第{self.chapter_num}章",
        f"【时间跨度】{total_ticks} tick",
    ]
    
    # 月令（最优先，设定基调）
    if mandate_text:
        lines.append(f"\n【时令】{mandate_text}")
    
    # 史官簿·近事（不可否认的历史事实）
    if chronicle_entries:
        lines.append("\n【史官簿·近事】")
        for entry in chronicle_entries:
            lines.append(f"  {entry}")

    # 礼器场（空间中存在的实物）
    if artifacts:
        lines.append("\n【礼器场·现存器物】")
        for a in artifacts:
            lines.append(f"  {a.artifact_type}在({a.y},{a.x})，存续{a.stable_age}息。{a.description}")

    # 爻痕地图（历史事件的物理残留）
    if traces:
        lines.append("\n【爻痕地图·事件残留】")
        for t in traces:
            lines.append(f"  息{t.tick} ({t.y},{t.x}) {t.pre_name}→{t.post_name} 余势{t.intensity:.2f}")

    # 征应·未兑现（悬而未决的因果）
    if omens:
        lines.append("\n【征应·未兑现】")
        for o in omens:
            lines.append(f"  {o}")

    # 累积意象（原有）
    # ...

    # 实体状态（原有）
    # ...
```

---

## 十一、配置扩展

### 11.1 worldview JSON 新增字段

```json
{
  "grids": {...},
  "interactions": [...],
  "entities": [...],
  "narrative": {...},
  
  "traces": {
    "decay_rate": 0.998,
    "min_intensity_for_snapshot": 0.1
  },
  "artifacts": {
    "threshold_ticks": 80,
    "max_per_grid": 20
  },
  "chronicle": {
    "max_entries": 200,
    "severity_threshold": 1
  },
  "zhengying": {
    "max_pending": 10,
    "expire_ticks": 500,
    "potential_threshold": 1.3
  },
  "mandate": {
    "enabled": true,
    "update_interval": 200
  }
}
```

---

## 十二、LLM 看到的变化

### 改造前（现在的 time 线包）
```
【观测世界】丰收税局副本 — 第2章
【时间跨度】750 tick
【世界背景】丰收税局副本，良田两百亩，田税一万斤
━━━ 实体状态变化 ━━━
【快照1】tick 751
  沈青: 人界=比(势0.33), 天道=坤(势0.79)
  个子最高的那个: 人界=比(势0.36)
...
```

### 改造后（新增内容）
```
【观测世界】丰收税局副本 — 第2章
【时间跨度】750 tick

【时令】时值仲秋，金气主事。百谷既收，田税当纳。毋封土，谨盖藏。

【史官簿·近事】
  息180，人界宫(16,32)阴阳反位，坤→比，势能1.20。沈青接近税务官。
  息420，天道宫(32,32)一爻动，比→师，势能0.95。规则暗面浮现。
  息680，人界宫(14,34)本末倒悬，师→坤，势能1.45。恐惧弥漫。

【礼器场·现存器物】
  节在(16,32)，已存续350息。灰石门槛，高半尺。跨越者须停步。
  鼎在(14,34)，已存续120息。铜锈斑驳，三足陷泥。沉默见证。

【爻痕地图·事件残留】
  息180 (16,32) 坤→比 余势0.72
  息420 (32,32) 比→师 余势0.53
  息680 (14,34) 师→坤 余势0.85

【征应·未兑现】
  息500 (20,40) 征：震→艮。占辞："动极生静，雷入山而止。山中将有物等待。"
  应条件：该区域100息内出现艮+兑。当前状态：待兑现（已过180息）

【实体状态变化】
  ...
```

---

## 十三、实施顺序

1. **traces.py** — 独立模块，可单独测试
2. **chronicle.py** — 依赖 traces
3. **artifacts.py** — 独立模块，可单独测试  
4. **mandate.py** — 独立模块
5. **zhengying.py** — 依赖 artifacts
6. **cosmos.py 重写** — 整合 1-5
7. **entity.py 重写** — 依赖 cosmos
8. **observer.py 升级** — 依赖 cosmos
9. **config.py 扩展** — 加配置项
10. **worldview JSON 扩展** — 加 traces/artifacts/chronicle/zhengying/mandate 配置
11. **yan_camera.py 重写** — _build_package 注入全部新数据

---

## 附录A：块宇宙 + 光锥观察（来自 Kimi 的建议）

### 概念

引擎不应给 LLM 一个"当前切片"，而应给一个**因果光锥**：过去 300 息的痕迹 → 当前的完整状态 → 未来 100 息的趋势预测。这对应《易传·系辞》"易无思也，无为也，寂然不动，感而遂通天下之故"。

### BlockUniverse

```python
class BlockUniverse:
    H: int; W: int
    max_tick: int
    cell_history: Dict[Tuple[int,int,int], CellState]  # (y,x,tick) 稀疏存储
    
    msgua_cycle: np.ndarray       # 十二消息卦
    nayin_sequence: List[str]     # 纳音序列
    lulu_sequence: List[str]      # 律吕序列
    
    def tick(self): ...
    def extract_past(self, y, x, now, depth) -> List[CellState]: ...
    def extract_future_trend(self, y, x, now, depth) -> dict: ...
    def trace_causality(self, past_states) -> List[str]: ...
```

### ObserverCone

```python
class ObserverCone:
    def __init__(self, block, y, x, now, past_depth=300, future_depth=100):
        self.past_cells = block.extract_past(y, x, now, past_depth)
        self.present = block.cell_history.get((y, x, now))
        self.future_trend = block.extract_future_trend(y, x, now, future_depth)
        self.causal_chain = block.trace_causality(self.past_cells)
    
    def format_for_llm(self) -> str:
        """生成 LLM 用的光锥文本"""
        # 输出格式见正文第十二节
```

---

## 附录B：全局节律系统（P0）

### 十二消息卦 — 全局阴阳呼吸

```python
MSGUA_SEQUENCE = ["复","临","泰","大壮","夬","乾","姤","遁","否","观","剥","坤"]
# 每1440息走完一个完整周期
# global_yang_ratio = abs(sin(phase * pi))
# 阳长时 gamma_mod 升高, 万物躁动; 阴长时降低, 万物凝滞
```

**LLM约束**: 消息卦=泰(三阳开泰) → "天地交而万物通"
消息卦=观(四阴剥阳) → "风行地上，观民设教"

### 六十甲子纳音 — 每tick的音色

60组纳音映射: ("海中金","金",0.3), ("炉中火","火",0.8), ...
tick % 60 索引到纳音名/五行/频率。
频率调制 trend 场: 金=高频震颤, 土=低频沉稳。

**LLM约束**: "涧下水" → 不能写岩浆; "霹雳火" → 不能写冰封

### 十二律吕 — 气象场声波

黄钟(=冬至, 低频0.05) 到 应钟(=纯阴, 极低频0.03)
tick % 12 索引律吕名和频率, 调制 trend 振荡模式。

---

## 附录C：人事网络层（P1）

### 六亲 — 区域社会功能

- 生我=父母: 庇护/制度/压力
- 同我=兄弟: 竞争/合作/平辈
- 我生=子孙: 创造/消耗/未来
- 我克=妻财: 资源/欲望/交易
- 克我=官鬼: 权威/危险/疾病

### 八门 — 区域流动控制

休(0.2), 生(1.5), 伤(0.5), 杜(0.0), 景(1.0), 死(0.0), 惊(0.8), 开(2.0)

**LLM约束**: 杜门=密室/禁闭; 开门=畅通/自由

---

## 附录D：五运六气（P2）

1440tick=一年, 分五运(木火土金水, 每288tick)和六气, 区域五行与主运相克时势能翻倍。
LLM读取"少阳相火司天, 阳明燥金在泉" → 上热下燥的病理期。

## 附录E：七十二候（P2）

1440tick分72候, 每20tick一候。
"立春初候·东风解冻", "惊蛰次候·仓庚鸣" 等。
当区域卦象五行与候气共振时, 强制注入环境触发器。

## 附录F：谶纬（P3）

特定卦变组合 → 强制释放谶语:
(63,0): "亢龙有悔，天下大旱"
(0,63): "群龙无首，吉"
(18,45): "水火未济，鬼神哭"

LLM必须编织进叙事, 但不能直接解释。状态: unresolved → 等待兑现。

## 附录G：实施总路线

| 优先级 | 模块 | 说明 |
|--------|------|------|
| P0 | 块宇宙存储 + 光锥观察 | LLM从切片→因果链 |
| P0 | 爻痕 + 史官簿 | 时间锚定 |
| P0 | 礼器场 | 空间锚定 |
| P0 | 消息卦 + 纳音 + 律吕 | 全局气氛锁定 |
| P1 | 六亲 + 八门 | 人事/空间关系 |
| P1 | 征应链 + 月令 | 因果/时令 |
| P2 | 五运六气 + 七十二候 | 周期锁定 |
| P3 | 谶纬 | 神秘层 |

---

## 附录H：时间锚点修正 — LLM 不拿确定性未来

> *来自 Kimi 的建议：引擎内部保留未来推演，但给 LLM 的 prompt 只开"未竟之势"。*

### 核心切割

| 信息 | 引擎内部 | 给LLM |
|------|---------|-------|
| 未来精确卦变 | 必须保留 | **不给** |
| 势能突破预测 | 道控制器使用 | **不给** |
| 征应链pending条件 | 触发逻辑使用 | 以"未竟之势"给 |
| 谶语 | 全局氛围 | 以"低语/回声"给 |
| 礼器老化迹象 | 物理演算 | **给**（裂纹、剥落在现在就能看见） |

### "几"代替"定"

《周易·系辞》："几者，动之微，吉之先见者也。"

未来的卦变不是剧本，是无法被精确预言的"几"——需要在当下回应的、模糊的、多义的征兆。

LLM 得不到 "息850将发生艮→兑"，只得到 "势能逼近临界，空气中有什么紧绷着即将断裂"。

### 修正后的 ObserverCone

```python
class ObserverCone:
    """只给过去+现在+未竟之势。不给确定性未来数据。"""
    def __init__(self, block, y, x, now, past_depth=300):
        self.past_cells = block.extract_past(y, x, now, past_depth)
        self.present = block.cell_history.get((y, x, now))
        self.causal_chain = block.trace_causality(self.past_cells)
        # 不调用 extract_future_trend()
        self.omen = block.get_omen(y, x, now)  # 只有未竟之势
```

### 叙事对比

错误（给了未来）："李老三推开木门，他知道三天后这道门槛会变成山泽通气的渡口——LLM把未来塞进现在的人物意识，时间线崩溃。

正确（只给未竟之势）："李老三推开木门。门槛上的漆早已剥落——这道'节'立了七百五十息，像被遗忘的禁令。他莫名觉得，这屋子里的什么东西，撑不了太久了。"——来自礼器老化（现在迹象）+ 未竟之势（模糊预感）。
