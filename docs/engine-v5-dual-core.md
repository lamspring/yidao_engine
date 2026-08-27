# 易道双核引擎 v5.0 · 架构设计

> **核心转变**：从"物理引擎 + LLM翻译"升级为"双核引擎"。
> **物理核（YVM）** 管世界怎么变。
> **叙事核（NVM）** 管故事怎么接。
> 叙事核寄生在物理核之上，用物理规律约束叙事连续性。LLM 不是"自由创作者"，是"被叙事物理定律束缚的观测者"。

---

## 〇、为什么 v4.0 还不够

v4.0 给了 LLM 丰富的引擎数据：爻痕、礼器、史官簿、六亲、八门、纳音、律吕、征应、谶纬。

但这些全是**物理数据**——"息 450 坎→离 at (14,32)"。LLM 知道物理世界发生了什么，但不知道**上一章的叙事把这件事写成了什么**。是"沈青触碰石碑指尖发麻"，还是"地下涌出热气蒸腾"？

**引擎状态 ≠ 叙事状态。** 物理数据永远无法替代文学记忆。

v5.0 的答案：增加一个**叙事核（NVM）**，它和物理核一样拥有真实的数值场，有惯性、有阻尼、有强制性。LLM 的输出必须通过叙事核的物理验证，验证失败则打回重写。

---

## 一、新架构全景

```
┌─────────────────────────────────────────────┐
│  Layer 5: PromptForge 闸门层                  │
│  - 构建：物理快照 + 叙事快照 + 债务宣言         │
│  - 验证：场景锁/情绪/债务/DNA 四重校验          │
│  - 重写：违规时注入违规清单，打回 LLM           │
├─────────────────────────────────────────────┤
│  Layer 4: LLM 观测层（只读，强约束）            │
├─────────────────────────────────────────────┤
│  Layer 3: 叙事核 NVM                          │
│  - SceneLock    场景锁场                      │
│  - EmotionField 情绪场                        │
│  - DebtField    债务场                        │
│  - CharacterDNA 人物DNA场                     │
│  - ProphecyQueue 谶语队列                     │
├─────────────────────────────────────────────┤
│  Layer 2: 物理核 YVM（v4.0 已实现）            │
│  - 卦场 / 爻痕 / 礼器 / 史官簿 / 征应链        │
│  - 六亲 / 八门 / 五运六气 / 七十二候 / 谶纬    │
├─────────────────────────────────────────────┤
│  Layer 1: 块宇宙存储 BlockUniverse             │
│  - 四维数组 (x, y, tick, 场量)                │
│  - 叙事事件链 NarrativeEventChain             │
└─────────────────────────────────────────────┘
```

---

## 二、叙事核 NVM 的五大硬状态

这些不是 prompt 里的"建议"，是引擎内部**真实的数值场**。LLM 必须通过接口读取，且**不得违背**。

### 2.1 场景锁场 SceneLock

**概念**：叙事场景是物理实体。有锁级、有类型、有退出条件。只有物理状态满足退出条件才能切换场景。

**数据结构**：

```python
@dataclass
class SceneLock:
    lock_level: int = 0          # 0=自由, 1=软锁(建议), 2=硬锁(强制)
    current_scene_id: str = ""   # 场景指纹（哈希）
    scene_type: str = ""         # "逃亡""对峙""潜伏""探索""仪式""日常""室内""野外"
    exit_conditions: List[str]   # 每条是一个物理条件，如"找到掩体""威胁离开""门被打开"
    forbidden_transitions: List[str]  # 禁止的场景跳转，如"直接醒来""瞬移到另一地点"
    spatial_anchor: Tuple[int,int,int]  # (grid_name, y, x) 场景的空间坐标绑定
    locked_at_tick: int = 0      # 锁定时 tick
    min_duration: int = 50       # 最短持续 tick（硬锁期间必须在此场景至少待这么多 tick）
```

**核心方法**：

```python
def set_lock(self, level, scene_type, spatial_anchor, exit_conditions, forbidden):
    """设置锁。通常在章节结尾检测到未完成动作时触发。"""

def check_exit_conditions(self, world_snapshot, entity_positions) -> bool:
    """检查物理状态是否满足退出条件。满足则降级或解锁。"""

def validate_transition(self, proposed_text: str) -> Tuple[bool, str]:
    """校验 LLM 输出是否违反场景锁。
    检测关键词："第二天""醒来""睁开眼""已经""后来""之后"
    在硬锁状态下，出现这些词直接返回 False。
    """

def detect_scene_from_text(self, chapter_text: str) -> dict:
    """从上一章结尾文本中检测：当前场景类型、未完成动作、空间锚点。
    用于自动设置下一章的场景锁。
    """
```

**第一章结尾自动锁定逻辑**：

```python
# 检测 ch1 结尾文本
ending_analysis = SceneLock.detect_scene_from_text(ch1_ending)

# 如果检测到"奔跑""逃亡""追""跑"等词
if ending_analysis.get("action_unfinished"):
    SceneLock.set_lock(
        level=2,  # 硬锁
        scene_type=ending_analysis["scene_type"],  # 如 "野外逃亡"
        spatial_anchor=ending_analysis["location"],
        exit_conditions=["找到掩体", "进入安全区域", "威胁离开"],
        forbidden_transitions=["室内场景", "第二天", "醒来", "平静描述"]
    )
```

**LLM 约束注入**：

```
【场景物理定律 — 必须遵守】
当前锁级：2（硬锁）
场景类型：野外逃亡
锁定时间：已持续 xxx tick
退出条件（以下任一满足方可切换场景）：
  1. 找到掩体且威胁暂时远离
  2. 进入可关闭的建筑物
禁止操作（出现即违规）：
  1. "第二天清晨""醒来""睁开眼"等时间跳跃
  2. 场景突然切换到室内且没有任何"进入"的物理动作描述
  3. 情绪突然平静，没有任何过渡
```

---

### 2.2 情绪场 EmotionField

**概念**：每个角色的情绪是物理量，有惯性和阻尼。不是标签，是可微分的场。LLM 不能一夜之间让恐慌归零。

**数据结构**：

```python
@dataclass
class EmotionState:
    fear: float = 0.0       # 恐慌 0.0~1.0
    anger: float = 0.0      # 愤怒
    hope: float = 0.0       # 希望
    fatigue: float = 0.0    # 疲惫
    confusion: float = 0.0  # 困惑
    resolve: float = 0.0    # 决绝

@dataclass
class EmotionField:
    emotions: Dict[str, EmotionState]  # tracker_id -> 情绪向量
    inertia: float = 0.85             # 惯性系数（越高越难突变）
    damping: float = 0.05             # 自然衰减（每息）
    delta_threshold: float = 0.3      # 单章情绪变化超过此值触发 violation
    history: Dict[str, List[Tuple[int, EmotionState]]]  # 追踪器情绪历史
```

**核心方法**：

```python
def tick(self, world_snapshot):
    """每物理 tick，情绪按物理规律演化。
    恐慌 = 旧恐慌 × 惯性 + 威胁等级 × 0.1 - 自然衰减
    决不能发生 0.92 → 0.1 的断崖式下降。
    """

def apply_narrative_event(self, tracker_id, event_type, intensity):
    """LLM 输出的叙事事件会改变情绪值。
    如 '发现安全屋' → 恐慌 -0.2, 希望 +0.3
    如 '同伴死亡' → 恐慌 +0.4, 愤怒 +0.5
    """

def validate_emotion_transition(self, tracker_id, new_text: str) -> Tuple[bool, str]:
    """验证 LLM 输出的情绪变化是否物理合理。
    如果恐慌从 0.92 降到 0.1 且文本中没有任何触发事件 → violation。
    """

def get_constraint_text(self) -> str:
    """生成 LLM 约束文本"""
```

**LLM 约束注入**：

```
【情绪物理定律 — 必须遵守】
上一章结尾情绪场：
  沈青: 恐慌=0.92, 疲惫=0.45, 困惑=0.78
  领头人: 恐慌=0.88, 决绝=0.60

本章情绪约束：
1. 恐慌值不得低于 0.6（硬约束）
2. 任何情绪的单章变化不得超过 0.3（软约束）
3. 情绪变化必须有对应的物理触发事件（如"找到掩体"→恐慌可降 0.2）
4. 禁止情绪断崖：不能从极度恐慌直接切换到平静叙述
```

---

### 2.3 债务场 DebtField

**概念**：每个未解决的悬念在空间中占据一个"债务泡"。债务不会自动消失，只会越积越深。LLM 读到债务时必须处理。

**数据结构**：

```python
@dataclass
class DebtBubble:
    debt_id: str
    tick_created: int
    type: str               # "suspense""action""object""prophecy""relationship"
    content: str            # 债务描述，如"浓雾中有东西即将追上"
    priority: str           # "critical""high""medium"
    spatial_anchor: Tuple[int,int,int]  # (grid, y, x) 债务发生的空间坐标
    status: str = "pending"  # "pending""resolving""resolved"
    pressure: float = 1.0   # 债务压力值，随时间累积（不衰减，反而增长）
    pressure_growth: float = 0.02  # 每 tick 压力增长
    holder_tracker: str = ""  # 关联的人物 tracker_id
    resolved_by: str = ""    # 解决方式

@dataclass
class DebtField:
    debts: List[DebtBubble]
    
    def tick(self):
        """每 tick，所有 pending 债务的压力值递增。不解决的债务越来越重。"""
        for debt in self.debts:
            if debt.status == "pending":
                debt.pressure += debt.pressure_growth
    
    def add(self, debt: DebtBubble):
        """注入新债务"""
    
    def mark_resolved(self, debt_id: str):
        """标记已解决"""
    
    def get_active_debts(self, min_pressure: float = 0.5) -> List[DebtBubble]:
        """获取所有活跃债务，按压力排序"""
    
    def get_critical_alerts(self) -> List[str]:
        """获取红色警报级别的债务，用于 prompt 顶部注入"""
```

**债务自动提取逻辑**（从 LLM 输出中检测未解决悬念）：

```python
class DebtExtractor:
    """规则引擎：从 ch1 的叙事文本中自动提取叙事债务"""
    
    DEBT_PATTERNS = [
        # (关键词, 债务类型, 优先级)
        (["逃跑","奔跑","逃亡","狂奔"], "action", "critical"),
        (["浓雾","雾里有","雾中","雾里"], "suspense", "critical"),
        (["拿着","握着","带着","攥着"], "object", "high"),
        (["他/她还没","尚未","不知道","没说"], "information", "high"),
        (["裂缝","裂开","断裂"], "environment", "medium"),
    ]
    
    def extract(self, chapter_text: str, spatial_context: dict) -> List[DebtBubble]:
        """扫描文本，匹配模式，生成债务泡"""
```

**LLM 约束注入**：

```
【债务警报 — 必须处理】
以下叙事债务已持续 pending，压力持续累积：
1. [CRITICAL 压力=1.85] 浓雾追逐
   空间锚：人界(18,30)
   产生于：息 680，第一章结尾
   要求：本章必须在开头 500 字内处理此威胁
2. [HIGH 压力=1.20] 热谷子
   持有者：沈青
   产生于：息 700，第一章
   要求：必须交代用途或去向
3. [MEDIUM 压力=0.80] 男孩之死的后果
   空间锚：人界(16,32)
   要求：其他角色应有所反应

未解决的债务会在后续章节持续增压。解决后压力归零。
```

---

### 2.4 人物 DNA 场 CharacterDNA

**概念**：每个实体的叙事基因组。从第一章 LLM 输出中自动提取并锁定。后续章节 LLM 不得变异。

**数据结构**：

```python
@dataclass
class CharacterDNA:
    tracker_id: str
    # 已确立的叙事事实（锁定）
    name: str = ""              # 第一章确立的中文名
    age_range: str = ""         # 年龄段
    physical_marks: List[str]   # 身体特征（如"后颈有细线""手腕系草绳"）
    voice_pattern: str = ""     # 语言模式（"寡言""反问式""低声""粗哑"）
    gesture_habits: List[str]   # 习惯动作（如"搓衣角""蹲着""用拇指敲"）
    essence: str = ""           # 叙事本质（如"承载之质""决断之核"）
    core_wound: str = ""        # 核心创伤事件
    role_in_group: str = ""     # 在群体中的角色（"领头""质疑者""沉默者"）
    
    # 关系网络（锁定）
    relationships: Dict[str, str]  # tracker_id → 六亲关系（"兄弟""官鬼"等）
    
    # 认知边界（锁定，LLM 不得越界）
    known_facts: List[str]      # 该角色知道的事实
    unknown_facts: List[str]    # 该角色不知道的事实（LLM 不能让他说出来）
    
    # 物品持有（锁定）
    inventory: List[str]        # 持有的物品，必须有好物理存在
    
    # 禁止行为（基于 DNA 推导）
    forbidden_actions: List[str]  # 如"领头人不能喋喋不休""沈青不能预知税局来历"
```

**核心方法**：

```python
@classmethod
def extract_from_text(cls, tracker_id: str, chapter_text: str, entity_labels: dict) -> "CharacterDNA":
    """从第一章 LLM 输出中自动提取 DNA。
    规则引擎 + 小型 LLM 调用。
    提取：名字、身体特征、语言模式、习惯动作、持有的物品。
    """

def validate_output(self, text: str) -> Tuple[bool, List[str]]:
    """验证 LLM 输出是否违反 DNA。
    检查：名字是否一致、语言模式是否匹配、认知边界是否被突破、
    物品是否凭空消失、禁止行为是否出现。
    返回 (通过, 违规列表)。
    """

def merge_new_info(self, text: str):
    """如果 LLM 在本章引入了新的可验证事实，更新 DNA（锁定）。"""
```

**LLM 约束注入**：

```
【人物DNA登记簿 — 必须遵守】
1. 沈青 (shenqing)
   名字：沈青（已锁定，禁止更名）
   身体特征：手指缝有青黑色线（已锁定）
   持有物：热谷子（第1章获取，必须一直持有或交代去向）
   已知事实：税局会抽取生命力、稻田在雾气中、男孩已死
   未知事实：税官的真实身份、雾中有什么、田地为何会动
   禁止行为：▶ 不能说出他未知的事实；▶ 不能突然变勇敢

2. 领头人 (e2)
   名字：第1章未命名（特征：个子最高、穿灰布短褐）
   语言模式：寡言、命令式、声音粗哑（已锁定）
   身体特征：小臂全是泥点子（已锁定）
   禁止行为：▶ 不能喋喋不休；▶ 不能突然消失

3. 蹲在田边的年轻女人 (e3)
   ...
```

---

### 2.5 谶语队列 ProphecyQueue

**概念**：来自征应链和谶纬系统的未来义务。LLM 必须在当前叙事中埋下预兆，在物理条件满足时兑现。

**数据结构**：

```python
@dataclass
class Prophecy:
    prophecy_id: str
    omen_text: str            # 必须在当前叙事中埋下的预兆文本
    trigger_condition: dict   # 引擎物理条件，如 {"gua_contains":[52,58]}
    fulfillment_window: Tuple[int,int]  # (min_tick, max_tick) 必须在此区间兑现
    status: str = "pending"   # "pending""seeded""fulfilled""expired"
    seeded_text: str = ""     # LLM 在第X章埋下的预兆文本
    
@dataclass
class ProphecyQueue:
    prophecies: List[Prophecy]
    
    def get_pending(self) -> List[Prophecy]:
        """获取需要在本章埋下预兆的谶语"""
    
    def check_fulfillment(self, world_state) -> List[Prophecy]:
        """检查哪些谶语的物理条件已满足，需要在本章兑现"""
    
    def expire_unfulfilled(self, current_tick):
        """标记超时未兑现的谶语为 expired（会产生叙事惩罚）"""
```

**LLM 约束注入**：

```
【谶语·必须埋下的预兆】
以下谶语需要在当前叙事中自然埋入：
1. "亢龙有悔，天下大旱"
   状态：待埋种
   要求：在本章的环境描写中出现干裂、缺水、燥热等意象
   兑现条件：未来 200 息内该区域出现乾→坤卦变时自动兑现

【谶语·等待兑现】
1. "阴极反阳，深渊出明"
   状态：已埋种（第1章："雾气深处有微光一闪"）
   等待物理触发条件：该区域出现坎→离卦变
```

---

## 三、PromptForge — 三层闸门

### 3.1 第一层：债务注入（写之前）

```python
def build_chapter_prompt(world_snapshot, narrative_vm, observer_cone, chapter_num):
    prompt_parts = []
    
    # ── 红色警报区（最先注入，最重要的约束）──
    prompt_parts.append("=" * 60)
    prompt_parts.append("【叙事物理定律 — 以下所有条款均为硬约束，违反直接打回重写】")
    prompt_parts.append("=" * 60)
    
    # 场景锁
    lock = narrative_vm.scene_lock
    if lock.lock_level >= 1:
        prompt_parts.append(f"\n## 场景锁（{'硬锁' if lock.lock_level==2 else '软锁'}）")
        prompt_parts.append(f"当前场景：{lock.scene_type}")
        prompt_parts.append(f"禁止操作：{', '.join(lock.forbidden_transitions)}")
    
    # 债务警报
    critical_debts = narrative_vm.debt_field.get_critical_alerts()
    if critical_debts:
        prompt_parts.append("\n## 债务警报（本章必须处理）")
        for d in critical_debts:
            prompt_parts.append(f"  [{d['priority']}] {d['content']}")
    
    # 情绪场
    prompt_parts.append("\n## 情绪物理定律")
    prompt_parts.append(narrative_vm.emotion_field.get_constraint_text())
    
    # ── 人物 DNA ──
    prompt_parts.append("\n## 人物DNA登记簿")
    for dna in narrative_vm.dna_registry.values():
        prompt_parts.append(f"\n### {dna.name or dna.tracker_id}")
        if dna.voice_pattern:
            prompt_parts.append(f"语言模式：{dna.voice_pattern}")
        if dna.inventory:
            prompt_parts.append(f"持有物：{', '.join(dna.inventory)}")
        if dna.forbidden_actions:
            prompt_parts.append(f"禁止：{'; '.join(dna.forbidden_actions)}")
    
    # ── 物理快照（引擎数据）──
    prompt_parts.append("\n" + "=" * 60)
    prompt_parts.append(observer_cone.format_for_llm())
    
    # ── 写作指令 ──
    prompt_parts.append("\n" + "=" * 60)
    prompt_parts.append("【写作指令】")
    prompt_parts.append(f"请续写第{chapter_num}章。必须严格遵守以上所有叙事物理定律。")
    prompt_parts.append("违反任何一项，本章将被打回重写。")
    
    return "\n".join(prompt_parts)
```

### 3.2 第二层：输出验证（写之后）

```python
class NarrativeValidator:
    def __init__(self, narrative_vm):
        self.nvm = narrative_vm
    
    def validate(self, llm_output: str) -> Tuple[bool, List[dict]]:
        violations = []
        
        # Check 1: 场景锁
        valid, msg = self.nvm.scene_lock.validate_transition(llm_output)
        if not valid:
            violations.append({"layer": "SceneLock", "msg": msg, "severity": "critical"})
        
        # Check 2: 情绪场
        for tid, dna in self.nvm.dna_registry.items():
            valid, msg = self.nvm.emotion_field.validate_emotion_transition(tid, llm_output)
            if not valid:
                violations.append({"layer": "EmotionField", "tracker": tid, "msg": msg})
        
        # Check 3: 债务场
        active_debts = self.nvm.debt_field.get_active_debts(min_pressure=0.8)
        for debt in active_debts:
            if not self._is_debt_addressed(llm_output, debt):
                violations.append({"layer": "DebtField", "debt_id": debt.debt_id, 
                                   "msg": f"关键债务未处理：{debt.content}", "severity": "warning"})
        
        # Check 4: 人物DNA
        for tid, dna in self.nvm.dna_registry.items():
            valid, dna_violations = dna.validate_output(llm_output)
            if not valid:
                for v in dna_violations:
                    violations.append({"layer": "CharacterDNA", "tracker": tid, "msg": v})
        
        # Check 5: 禁止句式（旧质量检查）
        forbidden_patterns = self._check_forbidden_patterns(llm_output)
        violations.extend(forbidden_patterns)
        
        return len([v for v in violations if v.get("severity") == "critical"]) == 0, violations
```

### 3.3 第三层：迭代重写（验证失败时）

```python
def generate_with_validation(llm_client, prompt, narrative_vm, max_retries=3):
    for attempt in range(max_retries):
        output, _ = llm_client.call(system_prompt, prompt)
        
        passed, violations = narrative_vm.validator.validate(output)
        
        if passed:
            # 更新叙事核状态
            narrative_vm.after_llm_output(output)
            return output
        
        # 构建修正提示
        correction = "【叙事物理校验失败 — 请重写】\n"
        correction += f"你的输出违反了以下叙事物理定律：\n"
        for i, v in enumerate(violations, 1):
            correction += f"{i}. [{v['layer']}] {v['msg']}\n"
        correction += f"\n请重写。这是第{attempt+1}次尝试，还剩{max_retries-attempt-1}次机会。\n"
        
        # 追加到 prompt
        prompt = prompt + "\n\n" + correction
    
    # 所有重试耗尽
    raise NarrativeViolationError(f"叙事验证失败 {max_retries} 次：{violations}")
```

---

## 四、块宇宙叙事扩展

```python
class NarrativeBlock:
    """四维块中的每个 (x,y,tick) 存储物理+叙事双重状态"""
    physical_state: dict     # 五场数据
    narrative_state: dict    # 叙事核在此时的状态
    events: List[str]        # 在此发生的叙事事件（LLM 输出的摘要）
    debts_created: List[str] # 在此产生的债务 ID
    debts_resolved: List[str]

class BlockUniverse:
    narrative_blocks: Dict[Tuple[int,int,int], NarrativeBlock]
    
    def extract_causal_narrative(self, observer_pos, now, past_depth=300):
        """提取的不是物理数据，而是叙事因果链"""
        chain = []
        for tick in range(now - past_depth, now):
            block = self.get_block(observer_pos, tick)
            if block:
                chain.append({
                    'tick': tick,
                    'events': block.events,
                    'debt_delta': len(block.debts_created) - len(block.debts_resolved),
                    'physical_change': self._detect_physical_change(tick-1, tick),
                })
        return chain
```

---

## 五、实施路线图

### Phase 1：核心约束（解决第二章漂移）

| 文件 | 内容 |
|------|------|
| `pipeline/narrative_vm.py` | 新建。实现 SceneLock + EmotionField + DebtField + CharacterDNA + NarrativeValidator |
| `pipeline/narrative_state.py` | 新建。实现 BlockUniverse 的叙事扩展 + NarrativeBlock 存储 |
| `yan_camera.py` | 重写 `_build_package`：prompt 顶部注入红色警报区。增加 `_validate_and_retry` 循环 |
| `pipeline/config.py` | 扩展。新增 NVM 配置节 |

**预期效果**：场景锁=2级硬锁后，LLM 写"醒来"直接打回重写。债务清单强制 LLM 处理未解决的悬念。

### Phase 2：DNA自动化

| 文件 | 内容 |
|------|------|
| `pipeline/dna_extractor.py` | 新建。从 ch1 LLM 输出中自动提取 CharacterDNA |
| `pipeline/debt_extractor.py` | 新建。从 ch1 叙事中自动检测悬念和债务 |
| `state_manager.py` | 升级。保存/恢复叙事核状态（DNA、债务、情绪、场景锁） |

**预期效果**：人物性格、语言模式、持有物跨章锁定，LLM 不能凭空改名或改变性格。

### Phase 3：闭环迭代

| 文件 | 内容 |
|------|------|
| `pipeline/narrative_validator.py` | 升级。增加情绪断崖检测、DNA 校验、债务偿还检查 |
| `yan_camera.py` | 升级。实现完整的三层闸门：债务注入 → 输出验证 → 迭代重写 |

**预期效果**：违规输出不再保存，自动触发重写。最多 3 次重试。

---

## 六、总结：为什么这次能解决

| 旧问题 | 旧方案（调 prompt） | 新方案（叙事核） |
|--------|-------------------|----------------|
| 第二章"醒来" | 提醒 LLM 别写 | **SceneLock=2级硬锁**，写"醒来" → 验证器打回 |
| 人物突然多/少 | 提醒 LLM 记得 | **CharacterDNA** 锁定。违规输出拒收 |
| 情绪断崖 | 提醒保持情绪 | **EmotionField** 物理演化，|Δ恐慌|>0.3 触发 violation |
| 悬念丢失 | 前情提要 | **DebtField** 债务泡空间锚定，不解决持续增压 |
| 空间漂移 | 提醒场景一致 | **SceneLock** 绑定空间，转换需物理动作验证 |
| 物品消失 | 提醒物品 | **DNA.inventory** 物理持有，不交代=债务未清 |

**核心哲学**：
> 旧引擎："LLM 是聪明的，提醒它就会记得。"  
> 新引擎："LLM 是不可信的，必须用叙事物理定律强制约束它。"

第一章结尾是逃亡峰值 → 第二章必须是逃亡余波。这不是建议，是叙事核的物理定律。


---

## 附录一：叙事五场 — 从 LLM 输出中萃取的硬事实

> 节律三律管"怎么写"，叙事五场管"写什么"。两者缺一不可。

### 萃取原则：起居注

不录形容，不录比喻，不录心理推测。只录可验证的物理事实：某时某地某人做某事，持有某物，知道/不知道某事。

### 五场对照表

| 物理场 | 叙事场 | 古典对应 | 功能 |
|--------|--------|---------|------|
| gua | **ActionField** | 起居注 | 谁在做什么，动作完成度，是否中断 |
| trend | **KnowledgeField** | 谱牒 | 谁知道什么，信息边界，禁止超认知 |
| phase | **InventoryField** | 方志 | 物品在哪里、什么状态、是否交接 |
| potential | **RelationField** | 谱牒 | 人物关系势能，信任值，权力分配 |
| stable_age | **SuspenseField** | 方志·灾异 | 未竟事件的时空坐标，债务优先级 |

### ActionField

```python
@dataclass
class ActionState:
    tracker_id: str
    action: str          # 谓词："奔跑""对峙""蹲伏""攀爬"
    status: str          # "进行中""已中断""已完成"
    trigger: str         # 触发原因
    location: str        # 空间位置
    since_tick: int      # 开始时间

class ActionField:
    states: Dict[str, ActionState]
    
    def extract_from_text(self, text: str, tick: int):
        """规则引擎萃取:
        - 检测主语+动词: "沈青跟在他身后跑" → 沈青·奔跑·进行中
        - 检测动词+方位: "领头人蹲下" → 领头人·蹲伏·进行中
        """
    
    def validate(self, llm_output: str) -> List[dict]:
        """验证律: 上一章'进行中'的动作，本章前500字必须交代结果"""
        for state in self.states.values():
            if state.status == "进行中":
                if not self._is_resolved_in_text(llm_output, state):
                    return [{"pass": False, 
                             "msg": f"{state.tracker_id}的'{state.action}'进行中但未交代结果"}]
        return []
```

### KnowledgeField

```python
@dataclass
class KnowledgeState:
    tracker_id: str
    knows: List[str]        # 已确认知道的事实
    does_not_know: List[str] # 明确不知道的事实（禁止说出来）
    suspects: List[str]      # 怀疑但未确认

class KnowledgeField:
    states: Dict[str, KnowledgeState]
    
    def validate(self, llm_output: str) -> List[dict]:
        """验证律: 人物不能说出 does_not_know 中的内容"""
        violations = []
        for tid, ks in self.states.items():
            for forbidden in ks.does_not_know:
                if self._detect_mention(llm_output, tid, forbidden):
                    violations.append({
                        "pass": False,
                        "msg": f"{tid}说出了超出认知的事实'{forbidden}'"
                    })
        return violations
```

### InventoryField

```python
@dataclass
class ItemState:
    item: str
    holder: str
    state: str           # "攥在手心""系于手腕""别在腰后"
    source: str          # 来源："税官稻田""枯草搓成"
    tick_acquired: int
    temperature: str = ""  # 可感知的物理属性

class InventoryField:
    items: Dict[str, List[ItemState]]
    
    def validate(self, llm_output: str) -> List[dict]:
        """验证律: 物品不会凭空消失，状态改变须有物理过程"""
        violations = []
        for holder, items in self.items.items():
            for item in items:
                if not self._is_mentioned(llm_output, item.item):
                    violations.append({
                        "pass": False,
                        "msg": f"{holder}持有'{item.item}'未交代下落"
                    })
        return violations
```

### RelationField

```python
@dataclass
class RelationState:
    pair: Tuple[str, str]
    type: str            # "临时同盟""被猎捕""主从"
    trust: float         # 0.0~1.0
    power: str           # "X主导""平等"

class RelationField:
    relations: Dict[Tuple[str,str], RelationState]
    
    def validate(self, llm_output: str) -> List[dict]:
        """验证律: 关系改变须有事件驱动，信任值变化须有物理原因"""
        pass
```

### SuspenseField

```python
@dataclass
class SuspenseEvent:
    event_id: str
    type: str            # "物理威胁""权力真空""空间异常""物品异常"
    location: str        # 空间锚点
    status: str          # "逼近中""暂停征收""未解释"
    priority: str        # "critical""high""medium"
    since_tick: int

class SuspenseField:
    events: List[SuspenseEvent]
    
    def validate(self, llm_output: str) -> List[dict]:
        """验证律: critical 级事件须在开头处理，禁止引入新主线替代"""
        violations = []
        for ev in self.events:
            if ev.priority == "critical":
                if not self._is_addressed_in_opening(llm_output, ev.event_id):
                    violations.append({
                        "pass": False,
                        "msg": f"CRITICAL事件'{ev.event_id}'未在开头处理"
                    })
        return violations
```

### 萃取器：规则引擎，不用 LLM

```python
class QiJuZhuExtractor:
    """起居注萃取器。纯规则引擎，零 LLM 调用。"""
    
    ACTION_PATTERNS = [
        (r'(沈青|他).*?(跑|奔跑|狂奔|逃|追|趴|蹲|站)', 'action'),
        (r'(领头人|大汉).*?(喊|叫|跑|停|蹲|拉)', 'action'),
    ]
    
    INVENTORY_PATTERNS = [
        (r'(手里|手心|掌中|攥着|握着|拿着).*?(谷子|草绳|镰刀)', 'inventory'),
    ]
    
    KNOWLEDGE_PATTERNS = [
        (r'(沈青|他).*?(知道|明白|意识到|发现).*?(税局|雾|田|谷子)', 'knowledge'),
    ]
    
    SUSPENSE_PATTERNS = [
        (r'(还没|尚未|不知道|没看清|没说完)', 'suspense'),
        (r'(即将|快要|正在).*?(追|逼近|过来|靠近)', 'suspense'),
    ]
    
    def extract_all(self, text: str, tick: int) -> dict:
        """一次性萃取所有五场硬事实"""
        return {
            'action': self._extract_action(text, tick),
            'inventory': self._extract_inventory(text, tick),
            'knowledge': self._extract_knowledge(text, tick),
            'relation': self._extract_relation(text, tick),
            'suspense': self._extract_suspense(text, tick),
        }
```

---

## 附录二：完整 Prompt 形态（第二章示例）

```
【叙事物理定律 — 硬约束，违规打回重写】
═══════════════════════════════════

▶ 场景锁：硬锁=2级，场景=野外逃亡
  禁止："第二天""醒来""睁开眼""已经"
  退出条件：找到掩体 / 进入封闭空间 / 威胁暂时远离

▶ 动作继承律：以下动作均为"进行中"，本章前500字须先交代结果
  沈青：奔跑（触发：领头人喊'快走'，位置：田埂东段）→ 跑成功？被追上？停下？
  领头人：奔跑（位置：沈青前方）
  年轻女人：奔跑
  镰刀男：奔跑

▶ 物品守恒律：以下物品须交代下落或状态变化
  沈青·热谷子（攥在手心，温热）→ 掉落？握紧？发烫？异变？
  领头人·草绳（系于手腕）
  镰刀男·镰刀（别腰后，刀背暗红）

▶ 认知边界律：以下事实禁止人物说出
  沈青不能知道："税局是活的""税局是城市""雾中物真身""谷子为何温热"

▶ 悬念实体律：以下CRITICAL事件须在开头处理
  [CRITICAL] 浓雾追兵（逼近中，位置：田埂东段雾墙）

═══════════════════════════════════

【物理快照·光锥】息750→1500
  ...
【叙事五场·继承态】
  ...（以上五场数据以结构化格式注入）
【节律三律】
  六爻律：上爻期，须收束或反转
  五行流：木旺→须生火或条件克土
  卦变锁：单爻变，禁止时间跳跃
【象曰】明夷，利艰贞。
【写作指令】请续写第2章。违反以上任何一条将被验证器打回。
```

---

## 附录三：验证失败 → 重写示例

```
【叙事物理校验失败 — 第 1 次重试】
你的输出违反了以下定律：

1. [ActionField] 沈青的"奔跑"进行中但未交代结果。检测到"冻醒"暗示时间跳跃。
   → 请先写奔跑如何结束：摔倒？被拦住？找到掩体？然后才能写"停下"或"醒来"。

2. [InventoryField] 沈青持有"热谷子"（状态：攥在手心），第二章未提及。
   → 请在奔跑/停下过程中明确谷子去向：落地/握紧/发烫。

3. [SuspenseField] CRITICAL事件"浓雾追兵"未在开头处理。检测到引入新场景替换了旧悬念。
   → 请在前500字内提及逼近的雾墙或追兵的声音/迹象。

请重写。剩余 2 次机会。
```


---

## 附录I：句法场 SyntaxField

> 不是"怎么写"的自由选择，是上一章句法指纹的继承。句式有惯性，否定句有密度上限。

### 数据结构

```python
class SyntaxField:
    def __init__(self):
        self.fingerprint = {
            "avg_sentence_len": 0,           # 平均句长（字）
            "negation_ratio": 0.0,           # 否定句占比
            "contrast_density": {},           # "不是...是..."密度
            "sensory_verb_top5": [],          # 主导感官动词
        }
        self.inheritance_rate = 0.7          # 继承系数

    def extract_from_chapter(self, text: str):
        """提取句法指纹"""
        sentences = split_sentences(text)
        self.fingerprint["avg_sentence_len"] = mean(len(s) for s in sentences)
        contrast = len(re.findall(r"不是.*?是", text))
        self.fingerprint["contrast_density"]["不是_是"] = contrast / len(sentences)
        self.fingerprint["negation_ratio"] = count_negation(text) / len(sentences)
        self.fingerprint["sensory_verb_top5"] = extract_top_verbs(text, 5)

class SyntaxValidator:
    RULES = {
        "contrast_inertia": {
            "check": lambda old, new: new["不是_是"] <= old.get("不是_是", 0.02) * 1.5,
            "msg": "'不是...是...'密度超标。删除否定铺垫，反常事物直接呈现。",
            "fix": "误：'不是红薯，是骨头' → 正：'他手里攥着骨头，黑乎乎的，挂着碎肉。'"
        },
        "sentence_len_inertia": {
            "check": lambda old, new: abs(new["avg_len"] - old["avg_len"]) <= 8,
            "msg": "句长突变。保持上一章的呼吸节奏。",
        },
        "sensory_coherence": {
            "check": lambda old, new: len(set(new["top5"]) & set(old["top5"])) >= 2,
            "msg": "感官漂移。保持主导感官连续性。",
        },
    }
```

### LLM 约束注入格式

```
【句法继承律】
上一章句法指纹：平均句长23字，'不是...是...'密度2%，主导感官=触觉
本章约束：
1. "不是……是……"每千字≤2处。反常直接呈现，不加否定铺垫。
2. 句长偏差≤±8字。
3. 触觉优先，禁止突然全转视觉。
```

---

## 附录J：风格势能场 StylePotential

> 恐怖有梯度，意象有亲缘。style 不是开关，是连续谱。

### 恐怖梯度谱

```python
STYLE_GRADIENT = {
    "anomaly":   0.20,   # 悬疑：异常发现（影子偏了、骨头有痕）
    "dread":     0.40,   # 不安：威胁逼近（地底声、无脸人）
    "horror":    0.60,   # 恐惧：边界突破（人/物从井出、被追踪）
    "terror":    0.80,   # 恐怖：身体侵犯（皮肤被侵入、五官消失）
    "abjection": 1.00,   # 崩解：现实瓦解（'你也是假的'、身体崩裂）
}

class StylePotential:
    def __init__(self):
        self.current_level = 0.15
        self.inertia = 0.72        # 风格惯性（同 YVM alpha）
        self.max_delta = 0.15      # 每章最大跃升
    
    def compute_allowed_level(self, target_phase: float) -> float:
        target = phase_to_style(target_phase)
        raw = self.inertia * self.current_level + (1 - self.inertia) * target
        return min(raw, self.current_level + self.max_delta)
```

### 意象亲缘锁

```python
class ImageGenealogy:
    MAX_DISTANCE = 2  # 新意象与已有谱系的最大亲缘距离

    @staticmethod
    def validate(new_image: str, existing_nodes: dict) -> int:
        """返回最短亲缘距离。>2 则违规。"""
        # 距离1: 直接衍生（骨头→骨粉）
        # 距离2: 间接关联（骨头→齿痕→牙）
        # 距离3+: 跳跃（影子→嘴里长牙）→ 违规
```

### LLM 约束注入格式

```
【风格渐变律】
上一章浓度：0.35（dread早期）。本章上限：0.50（horror早期）。
禁止：身体崩解、元叙事崩解（'你也是假的'）、面部崩裂。
允许：他人诡异行为、环境恶化、认知动摇、威胁逼近。

【意象亲缘律】
已激活谱系：骨头/齿痕/影子/井/磨盘/刻痕/无脸人/地底声/空白脸
新意象亲缘距离 ≤2。'嘴里长牙'距离=3 → 禁止。先写'牙'作为物体出现，再衍生。
```

---

## 附录K：实施指令 — SyntaxField + StylePotential

### 新建文件

`pipeline/syntax_field.py`
- SyntaxField 类（extract_from_chapter + format_constraint）
- SyntaxValidator 类（validate 方法，检查 contrast_inertia / sentence_len_inertia / sensory_coherence）

`pipeline/style_potential.py`
- StylePotential 类（compute_allowed_level + validate_body_horror）
- ImageGenealogy 类（validate 方法，计算亲缘距离）

### 修改文件

`yan_camera.py` 的 `_build_package()` — 在 NVM 约束注入中增加：
- SyntaxField 的句法约束块
- StylePotential 的风格约束块
- ImageGenealogy 的意象亲缘约束块

### 验证

清空状态，重跑 ch1→ch3。ch3 不应出现 body horror（嘴里长牙、脸裂到耳根、皮肤脱落）。
