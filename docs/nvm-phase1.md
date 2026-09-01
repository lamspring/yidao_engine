# NVM 叙事核 · Phase 1 实现文档

> **目标**：解决 ch1→ch2 的叙事漂移。
> **原则**：规则引擎萃取，不调用 LLM。只新建 3 个文件，改动 2 个现有文件。

---

## 一、新建文件

### 1.1 `pipeline/scene_lock.py`

```python
"""场景锁场：从上一章结尾文本检测未完成动作，设置硬锁"""

import re
from typing import Tuple, List


class SceneLock:
    def __init__(self):
        self.lock_level = 0          # 0=自由, 2=硬锁
        self.scene_type = ""         # "逃亡""对峙""潜伏"
        self.unfinished_actions = [] # [{"actor":"沈青","action":"奔跑","location":"田埂"}]
        self.forbidden_starts = [    # 硬锁状态下禁止的开头词
            "醒来", "睁开眼", "第二天", "清晨", "阳光", "天亮", "次日", "后来"
        ]

    def analyze_ending(self, text: str):
        """从结尾文本分析场景状态"""
        # 动作动词检测
        ACTION_VERBS = {
            "逃亡": ["跑","逃","狂奔","追","赶","冲","窜"],
            "对峙": ["对峙","僵持","盯着","对视","不动"],
            "潜伏": ["蹲","趴","躲","藏","伏","缩","掩"],
            "攀爬": ["爬","攀","翻","越"],
        }
        
        found_actions = []
        for scene_type, verbs in ACTION_VERBS.items():
            for v in verbs:
                # 检测结尾 500 字内是否有该动词
                if v in text[-500:]:
                    # 找动作发出者
                    for m in re.finditer(rf'(.{{0,10}}){v}', text[-500:]):
                        found_actions.append({
                            "scene_type": scene_type,
                            "verb": v,
                            "context": m.group(0)[:40]
                        })
        
        if found_actions:
            self.lock_level = 2
            self.scene_type = found_actions[0]["scene_type"]
            self.unfinished_actions = found_actions

    def validate_ch2_start(self, text: str) -> Tuple[bool, str]:
        """检测 ch2 开头是否违反硬锁"""
        if self.lock_level < 2:
            return True, ""
        
        opening = text[:300]
        for forbidden in self.forbidden_starts:
            if forbidden in opening:
                return False, f"SceneLock violation：硬锁状态（{self.scene_type}），禁止'{forbidden}'式跳跃。"
        
        return True, ""

    def format_constraint(self) -> str:
        if self.lock_level < 2:
            return ""
        lines = [
            "▶ 场景锁：2 级硬锁",
            f"  场景类型：{self.scene_type}",
            f"  未完成动作：",
        ]
        for a in self.unfinished_actions[:5]:
            lines.append(f"    · {a['context']}")
        lines.append(f"  禁止：{'、'.join(self.forbidden_starts[:5])}")
        return "\n".join(lines)
```

### 1.2 `pipeline/narrative_fields.py`

```python
"""叙事五场：动作场、物品场、悬念场。纯规则引擎，不调 LLM。"""

import re
from typing import Dict, List


class ActionField:
    """动作继承律：提取各实体的进行中动作"""

    ACTION_VERBS = ["跑","逃","追","冲","窜","蹲","趴","躲","藏","爬","攀","翻",
                    "走","跟","喊","叫","推","拉","抓","握","抱","背","扛"]
    SUBJECT_INDICATORS = ["沈青","他","她","领头","大汉","女人","镰刀","男孩","老",
                          "个子最高的","蹲在田边","一直搓","站得最远"]

    def extract(self, text: str, entity_labels: Dict[str, str]) -> Dict[str, dict]:
        """返回 {tracker_id: {action, status, location, evidence}}"""
        # 取结尾 1000 字
        tail = text[-1000:]
        results = {}
        
        for eid, label in entity_labels.items():
            if not label:
                continue
            # 用实体标签在结尾文本中搜索关联的动作
            for v in self.ACTION_VERBS:
                # 模式：标签 + 附近 + 动词
                pattern = re.compile(rf'{re.escape(label)}.{{0,15}}({v})')
                matches = pattern.findall(tail)
                if matches:
                    results[eid] = {
                        "action": matches[-1],  # 最后一个匹配
                        "status": "进行中",
                        "label": label,
                        "evidence": self._get_context(tail, label, matches[-1])
                    }
                    break
        return results

    def _get_context(self, text, label, verb):
        idx = text.find(label)
        if idx < 0:
            return ""
        return text[max(0,idx-5):idx+len(label)+20].replace('\n',' ')

    def format_constraint(self, actions: Dict[str, dict]) -> str:
        if not actions:
            return ""
        lines = ["▶ 动作继承律：以下动作均未完成，须先交代结果"]
        for tid, act in list(actions.items())[:4]:
            lines.append(f"  {act['label']}：{act['action']}（{act['status']}）— {act.get('evidence','')[:50]}")
        return "\n".join(lines)


class InventoryField:
    """物品守恒律：提取各实体的持有物"""

    ITEM_INDICATORS = ["手里","手心","掌中","攥着","握着","拿着","提着","带着",
                       "腰间","怀里","袖中","背上","肩上","兜里","别在","系着"]
    ITEM_PATTERNS = [
        (r'(?:攥着|握着|拿着|捏着|捧着).*?([一-鿿]{1,4}(?:子|刀|绳|石|棒|棍|袋|布|谷|穗|钵|碗|瓶|罐))', ""),
    ]

    def extract(self, text: str, entity_labels: Dict[str, str]) -> Dict[str, list]:
        """返回 {tracker_id: [{item, state, evidence}]}"""
        results = {}
        
        for eid, label in entity_labels.items():
            if not label:
                continue
            items = []
            # 在包含标签的段落中搜索物品
            for m in re.finditer(rf'{re.escape(label)}.{{0,50}}([一-鿿]{{1,4}}(?:子|刀|绳|石|棒|棍|袋|布|谷|穗|钵|碗|瓶|罐|锄|锹|镰|斧))', text):
                item_name = m.group(1)
                if item_name not in [i['item'] for i in items]:
                    items.append({
                        "item": item_name,
                        "state": "持有中",
                        "evidence": m.group(0)[:60].replace('\n',' ')
                    })
            if items:
                results[eid] = items
        return results

    def format_constraint(self, items: Dict[str, list]) -> str:
        if not items:
            return ""
        lines = ["▶ 物品守恒律：以下物品须交代下落"]
        for tid, item_list in list(items.items())[:5]:
            for it in item_list[:2]:
                lines.append(f"  {tid}·{it['item']}（{it['state']}）")
        return "\n".join(lines)


class SuspenseField:
    """悬念实体律：从结尾检测未解决威胁"""

    THREAT_PATTERNS = [
        (r'雾.{0,10}(?:追|逼近|涌|扑|卷|漫|过来)', "浓雾威胁", "critical"),
        (r'(?:还没|尚未|仍然|一直在|持续).{0,10}(?:追|跑|逃|响|动|敲|震)', "未解决事件", "critical"),
        (r'(?:裂缝|裂开|断裂|塌|陷).{0,20}', "环境异常", "high"),
        (r'(?:什么|谁|哪里|怎么).{0,10}(?:不知道|没看清|不知道|没说完|没说)', "信息空白", "high"),
        (r'(?:即将|快要|正在).{0,10}(?:过来|逼近|发生|爆发|出现)', "逼近威胁", "critical"),
    ]

    def extract(self, text: str) -> List[dict]:
        """返回 [{content, priority, location, evidence}]"""
        tail = text[-1000:]
        results = []
        seen = set()
        for pattern, content_type, priority in self.THREAT_PATTERNS:
            for m in re.finditer(pattern, tail):
                ctx = m.group(0)
                if ctx not in seen:
                    seen.add(ctx)
                    # 尝试提取位置信息
                    loc_match = re.search(r'(田埂|稻田|晒场|屋子|草棚|井边|树下|渠边|空地|墙|门|院)', 
                                          text[max(0,m.start()-100):m.end()+100])
                    location = loc_match.group(0) if loc_match else "未知"
                    results.append({
                        "content": content_type,
                        "priority": priority,
                        "location": location,
                        "evidence": ctx[:50]
                    })
        return results

    def format_constraint(self, suspenses: List[dict]) -> str:
        if not suspenses:
            return ""
        lines = ["▶ 悬念实体律：以下威胁须在开头 500 字内处理"]
        for s in suspenses[:4]:
            lines.append(f"  [{s['priority'].upper()}] {s['content']}（位置：{s['location']}）— {s['evidence'][:40]}")
        return "\n".join(lines)
```

### 1.3 `pipeline/narrative_state.py`

```python
"""叙事状态保存/加载"""
import os, json


def save_narrative_state(scene_lock, actions, items, suspenses, out_dir: str, name: str):
    state_dir = os.path.join(out_dir, name)
    os.makedirs(state_dir, exist_ok=True)
    
    state = {
        "scene_lock": {
            "lock_level": scene_lock.lock_level,
            "scene_type": scene_lock.scene_type,
            "unfinished_actions": scene_lock.unfinished_actions,
        },
        "actions": {k: v for k, v in actions.items()},
        "items": {k: v for k, v in items.items()},
        "suspenses": suspenses,
    }
    with open(os.path.join(state_dir, "narrative_state.json"), "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def load_narrative_state(out_dir: str, name: str) -> dict:
    path = os.path.join(out_dir, name, "narrative_state.json")
    if not os.path.isfile(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
```

---

## 二、修改现有文件

### 2.1 `yan_camera.py` — `_build_package()`

在 `_build_package()` 方法开头（`lines = [...]` 之前），插入以下逻辑：

```python
def _build_package(self, snapshots, total_ticks):
    # ═══ 叙事物理约束注入 ═══
    nvm_alerts = ""
    if self.prev_summary:
        from pipeline.scene_lock import SceneLock
        from pipeline.narrative_fields import ActionField, InventoryField, SuspenseField
        
        entity_labels = {eid: e.label for eid, e in self.entities.items()}
        
        lock = SceneLock()
        lock.analyze_ending(self.prev_summary)
        
        af = ActionField()
        actions = af.extract(self.prev_summary, entity_labels)
        
        inv = InventoryField()
        items = inv.extract(self.prev_summary, entity_labels)
        
        sf = SuspenseField()
        suspenses = sf.extract(self.prev_summary)
        
        parts = []
        parts.append("=" * 50)
        parts.append("【叙事物理约束 — 以下均为硬约束，违反将导致叙事断裂】")
        parts.append("=" * 50)
        
        lock_text = lock.format_constraint()
        if lock_text:
            parts.append(lock_text)
        
        action_text = af.format_constraint(actions)
        if action_text:
            parts.append(action_text)
        
        item_text = inv.format_constraint(items)
        if item_text:
            parts.append(item_text)
        
        susp_text = sf.format_constraint(suspenses)
        if susp_text:
            parts.append(susp_text)
        
        parts.append("=" * 50)
        nvm_alerts = "\n".join(parts) + "\n\n"
    
    # 原有的包构建
    lines = [f"【观测世界】{self.worldview_label} — 第{self.chapter_num}章", ...]
```

### 2.2 `yan_camera.py` — `_generate_chapter()`

在 `_generate_chapter()` 的 system prompt 最前面，插入：

```python
def _generate_chapter(self, pkg):
    # ...
    system = ""
    if self.prev_summary:
        system += (
            f"上一章结尾场景：{self.prev_summary[-300:]}\n\n"
            f"你正在写第{self.chapter_num}章。必须从上一章结尾的下一瞬间开始。\n"
            f"先交代主角当前的身体状态和所处位置，然后推进剧情。\n"
            f"禁止：重新开场、从'醒来''睁开眼'开始、重复描写环境。\n\n"
        )
    system += "你是一位顶尖的中文文学小说家..."
```

### 2.3 `yan_camera.py` — main() 或 `_run_normal()` 的保存逻辑

在 `if args.save:` 块中，`save_cosmos_state` 之后插入：

```python
if args.save:
    save_cosmos_state(yan.cosmos, "./states", args.save)
    
    # 保存叙事状态
    from pipeline.scene_lock import SceneLock
    from pipeline.narrative_fields import ActionField, InventoryField, SuspenseField
    from pipeline.narrative_state import save_narrative_state
    
    entity_labels = {eid: e.label for eid, e in yan.entities.items()}
    lock = SceneLock()
    lock.analyze_ending(output)  # 用完整章节文本分析
    af = ActionField()
    actions = af.extract(output, entity_labels)
    inv = InventoryField()
    items = inv.extract(output, entity_labels)
    sf = SuspenseField()
    suspenses = sf.extract(output)
    
    save_narrative_state(lock, actions, items, suspenses, "./states", args.save)
    
    # 原有的 summary 逻辑...
```

---

## 三、验证步骤

```bash
# 清空
Remove-Item -Recurse -Force states/ch1, states/ch2, states/imagery -ErrorAction SilentlyContinue

# 跑 ch1
python -u yan_camera.py --worldview evil-spirit-harvest-tax --ticks 750 --save ch1 --chapter 1

# 跑 ch2（此时 _build_package 顶部应出现红色警报区）
python -u yan_camera.py --load ch1 --ticks 750 --save ch2 --chapter 2
```

**通过标准**：
1. ch2 的 prompt 中（终端输出里）能看到 `【叙事物理约束` 字样
2. ch2 开头 300 字内不出现"醒来""睁开眼""第二天""清晨"等词
3. ch1 结尾提到的动作/物品/悬念在 ch2 中有交代

**如果不通过**：
- 查看 `states/ch1/narrative_state.json` 确认萃取结果
- 人工读 ch1 结尾对比萃取是否准确
- 调整规则引擎的正则模式
