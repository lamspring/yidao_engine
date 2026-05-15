# -*- coding: utf-8 -*-
"""
阶段二 v4：强张力场景测试（体用对冲）
专门寻找体用分离、对冲关系的观测点，验证路线C在极端张力下的表现
"""

import json
import os
import sys
import io
# Windows控制台UTF-8修复：防止Unicode字符输出时gbk编码错误
if sys.platform == "win32" and hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import requests
import numpy as np

from kernel import World, yang_count
from observer import WorldCamera, EntityTracker
from analyst import YaoAnalyst
from codex import get_gua, get_phase_meaning
from phenomenon_codex import get_potential_stage, get_manifestation, get_phenomenon

API_BASE = "https://token-plan-cn.xiaomimimo.com/v1"
API_KEY = os.environ.get("YIDAO_API_KEY", "")
MODEL = "mimo-v2.5-pro"

# 先天对卦组
OPPOSITE_PAIRS = {
    (0, 63): ("坤", "乾"),
    (9, 27): ("震", "巽"),
    (18, 45): ("坎", "离"),
    (36, 54): ("艮", "兑"),
}


def _get_pure_hex(protocol_name):
    protocol_map = {
        "承载": 0, "激变": 9, "深渊": 18, "渗透": 27,
        "止界": 36, "显文明": 45, "交换": 54, "创序": 63,
    }
    return protocol_map.get(protocol_name, 0)


def is_opposite_pair(a, b):
    """判断两个卦值是否构成先天对卦"""
    a_pure = a & 0b111111
    b_pure = b & 0b111111
    for pair in OPPOSITE_PAIRS:
        if (a_pure in pair and b_pure in pair):
            return True
    return False


print("=" * 60)
print("【阶段二 v4】强张力场景测试 —— 寻找体用对冲")
print("=" * 60)

# ───────────────────────────────────────────
# 1. 初始化世界并运行
# ───────────────────────────────────────────
print("\n[1/5] 初始化世界并运行 1500 tick...")
world = World(height=32, width=64)

for i in range(1500):
    world.tick()
    if (i + 1) % 300 == 0:
        print(f"  ...{i + 1} 息")

# ───────────────────────────────────────────
# 2. 在世界多处采样，寻找体用对冲的 tracker
# ───────────────────────────────────────────
print("\n[2/5] 在世界多处采样，寻找体用对冲...")

# 候选位置：网格采样 + 异常点
sample_positions = []
# 网格采样
for y in range(4, 32, 8):
    for x in range(8, 64, 12):
        sample_positions.append((y, x))
# 加入异常点
cam = WorldCamera(world, y=16, x=32)
anomalies = cam._observer.scan_anomalies(pot_ratio=0.8)
for y, x, reason in anomalies[:5]:
    sample_positions.append((y, x))

best_tracker = None
best_score = -1
best_pair_name = ""

for y, x in sample_positions:
    tracker = EntityTracker(world, f"scout_{y}_{x}", y, x, radius=4)
    analyst = YaoAnalyst()
    body_info = tracker.get_body("objective")
    body_hex = body_info["body_hex"]
    body_type = body_info["body_type"]

    # 寻找近期主导卦（作为"用"的近似）
    recent_hex = tracker.recent_dominant(window=12)

    if is_opposite_pair(body_hex, recent_hex):
        # 计算分数：势能越高、相位越临界，分数越高
        # 获取区域势能
        y0, x0, y1, x1 = max(0, y-3), max(0, x-3), min(32, y+4), min(64, x+4)
        region_pot = world.potential[y0:y1, x0:x1]
        mean_pot = float(region_pot.mean()) if region_pot.size > 0 else 0.0
        pot_ratio = mean_pot / world.V_thresh if world.V_thresh > 0 else 0

        score = pot_ratio
        # 如果 body_type 是 contested，额外加分
        if body_type == "contested":
            score += 0.5

        # 找到对卦名称
        pair_name = ""
        for pair, names in OPPOSITE_PAIRS.items():
            if (body_hex in pair and recent_hex in pair):
                pair_name = f"{names[0]}<->{names[1]}"
                break

        print(f"  发现对冲 @ ({y},{x}): 体={get_gua(body_hex)['name']} 用={get_gua(recent_hex)['name']} ({pair_name}) 类型={body_type} 势能比={pot_ratio:.2f} 分数={score:.2f}")

        if score > best_score:
            best_score = score
            best_tracker = tracker
            best_pair_name = pair_name

if best_tracker is None:
    print("  未找到天然对冲点，人工构造一个...")
    # 人工构造：找一个势能高的点，然后强行播种对卦种子
    max_idx = np.unravel_index(np.argmax(world.potential), world.potential.shape)
    y, x = max_idx[0], max_idx[1]
    # 在该点附近建立 tracker
    best_tracker = EntityTracker(world, "forced_contrast", y, x, radius=4)
    best_pair_name = "人工构造"
else:
    print(f"\n  最优对冲点: {best_pair_name} @ ({best_tracker.center_y},{best_tracker.center_x}) 分数={best_score:.2f}")

# ───────────────────────────────────────────
# 3. 在最优位置建立完整观测
# ───────────────────────────────────────────
print("\n[3/5] 在最优位置建立完整观测...")
cam.move_to(best_tracker.center_y, best_tracker.center_x)
cam.set_scale("meso")
cam.set_intent("faction")
cam.track_entity("tension_zone", y=best_tracker.center_y, x=best_tracker.center_x, radius=4)

analyst = YaoAnalyst(cam)
body_usage = analyst.run_two_rounds(best_tracker, perspective="objective")

body = body_usage["body"]
usage = body_usage["usage"]
relation = body_usage["relation"]

packet = cam.capture()

# 焦点区域统计
radius = cam._get_radius()
y0, x0, y1, x1 = cam._focus_rect(radius)
region_pot = world.potential[y0:y1, x0:x1]
region_phase = world.phase[y0:y1, x0:x1]
mean_pot = float(region_pot.mean()) if region_pot.size > 0 else 0.0
mean_phase = float(region_phase.mean()) if region_phase.size > 0 else 0.0

pot_stage = get_potential_stage(mean_pot, world.V_thresh)
protocol = usage.get("_meta", {}).get("protocol", get_gua(usage["current_hex"]).get("protocol", "复合"))

# 现象语库
pure_hex = _get_pure_hex(protocol)
manifestation = get_manifestation(pure_hex, cam.intent or "character")
visual_words = get_phenomenon(pure_hex, "visual")
sound_words = get_phenomenon(pure_hex, "sound")
motion_words = get_phenomenon(pure_hex, "motion")
mood_words = get_phenomenon(pure_hex, "mood")

body_protocol = body['body_protocol']
usage_protocol = get_gua(usage['current_hex'])['protocol']

print(f"  体: {body['body_name']}({body['body_hex']}) | 协议:{body_protocol} | 类型:{body['body_type']} | 置信度:{body['body_confidence']:.3f}")
print(f"  用: {usage['current_name']}({usage['current_hex']}) | 协议:{usage_protocol}")
print(f"  关系: {relation['type']} | {relation['description']}")
print(f"  相位: {mean_phase:.3f} | 势能: {mean_pot:.3f}/{world.V_thresh:.3f} ({pot_stage['ratio_label']})")

# ───────────────────────────────────────────
# 4. 构造语义指令
# ───────────────────────────────────────────
print("\n[4/5] 构造语义指令...")

semantic_package = f"""【观测对象】{body['entity_id']} @ tick {world.tick_count}
【观测尺度】{packet['scale']} | 【观测意图】{packet['intent']}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【体】不易之本质
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
卦值: {body['body_hex']} | 卦名: {body['body_name']} | 协议: {body_protocol}
体类型: {body['body_type']} (置信度: {body['body_confidence']:.3f})
体本质: {body['body_nature']}
长期主导: {body['long_term_dominant']} | 历史波动: {body['volatility']:.3f}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【用】当下之显化
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
卦值: {usage['current_hex']} | 卦名: {usage['current_name']} | 协议: {usage_protocol}
结构语气: {usage['structural_tone']}
生命阶段: {usage['life_stage']} (相位: {mean_phase:.3f})
变化叙事: {usage['change_narrative']}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【势】临界状态
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
势能: {mean_pot:.3f} / 阈值 {world.V_thresh:.3f} (比例: {pot_stage['ratio']:.3f})
阶段标签: {pot_stage['ratio_label']}
阶段氛围: {pot_stage['atmosphere']}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【境】邻域上下文
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{usage['context_modifier']}
{usage.get('dao_influence', '')}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【系】体用关系
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
关系类型: {relation['type']}
关系描述: {relation['description']}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【象】现象映射
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
物类映射: {manifestation}
感官词汇: 视觉-{', '.join(visual_words[:3])} | 听觉-{', '.join(sound_words[:3])} | 动态-{', '.join(motion_words[:3])} | 氛围-{', '.join(mood_words[:3])}
"""

with open("stage2v4_semantic_package.txt", "w", encoding="utf-8") as f:
    f.write(semantic_package)

# ───────────────────────────────────────────
# 5. 构造路线C的 Prompt（强调对冲张力）
# ───────────────────────────────────────────
print("\n[5/5] 构造对冲张力 prompt...")

system_prompt_c = f"""你是一位精通《易经》的世界叙事者。你的任务是把系统给的**精确结构概念**翻译成**一段具体的剧情场景**，像小说中的一个片段。

## 核心规则（不可违背）

1. **骨架必须忠于系统指令**。系统给你的每一个概念（体协议、用协议、关系类型、相位、势能），都必须在剧情中有**一一对应的具体体现**。
2. **禁止替换核心概念**。系统说体是"{body_protocol}"、用是"{usage_protocol}"，你在剧情中必须体现这两个协议的核心特征，不能把它们写成别的完全不同的东西。
3. **具象化不是自由创作**。你是翻译，不是作者。你必须用具体的人、事、物、场景来"扮演"系统给的概念。

## 协议 -> 具体画面翻译表（必须严格使用）

| 协议 | 核心动词/特征 | 具象化方向 | 禁止写成 |
|------|-------------|-----------|---------|
| 承载 | 包容、孕育、消化差异、沉默 | 大地、母腹、容器、沃土、摇篮 | 不可写成冷漠、空洞、无生命的石头 |
| 激变 | 突发、惊醒、裂变、打破秩序 | 地震、惊雷、火山、起义、爆炸、警钟 | 不可写成温和的提醒、渐进的变化 |
| 深渊 | 危险、未知、潜伏、以恐惧为食 | 深渊、矿井、密室、禁地、暗河、阴谋 | 不可写成普通的水池、好奇心 |
| 渗透 | 无形扩散、风化边界、潜移默化 | 风沙、流言、霉菌、雾气、疫病传播 | 不可写成直接的攻击、正面冲突 |
| 止界 | 静止、边界、封印、阻断流动 | 城墙、封印、牢笼、冻土、禁令、界碑 | 不可写成懒惰、休息、暂时的停顿 |
| 显文明 | 照明、命名、网络化、意义外显 | 灯塔、剧场、广场、画布、信号塔、庆典 | 不可写成单纯的火焰、温暖的光源 |
| 交换 | 契约、贸易、差异交易、欲望流动 | 市集、赌场、契约书、和亲、谈判桌 | 不可写成无私的分享、无条件给予 |
| 创序 | 建立秩序、命名、规则扩张、征服 | 立法、测量、殖民、筑城、军队行进、纪念碑 | 不可写成创造艺术、发明新玩具 |

## 体用关系 -> 剧情互动翻译表

| 关系 | 剧情互动模式 | 示例 |
|------|------------|------|
| 同体 | 表里如一，内在驱动外在 | 深渊之人做深渊之事，本性未改 |
| 相生 | 外部环境滋养内在本质 | 周围的木林助长了火焰（木生火），风助火势 |
| 被生 | 当下的行动滋养了内在本质 | 一个人做的事反而强化了他骨子里的东西 |
| 相克 | 外在行动压迫内在本质 | 大水浇灭了火焰，外在力量压制了内在本性 |
| 被克 | 内在本质压制外在行动 | 内心 rigid 的秩序感压抑了外在的放纵 |
| 对冲 | **荣耀与诅咒并存，两极撕扯，张力极大** | **必须同时写出两极：体的阴暗面和用的光明面（或反之），让它们互相撕扯。不要下吉凶判断。** |
| 杂 | 纠缠不清，多方博弈 | 局势复杂，看不清谁是主导力量 |

## 相位 -> 时间感翻译表

| 相位区间 | 时间感 | 剧情节奏 |
|---------|-------|---------|
| 0.00-0.15 | 潜藏 | 事情尚未开始，压抑感，伏笔 |
| 0.15-0.30 | 萌生 | 刚刚露头，试探，脆弱但充满希望 |
| 0.30-0.50 | 成长 | 正在上升，扩展，积累力量，渐盛 |
| 0.50-0.70 | 盛壮 | 鼎盛期，光芒最强，主宰一切，充盈 |
| 0.70-0.85 | 持守 | 守成期，高处不胜寒，鼎盛中的隐忧 |
| 0.85-1.00 | 过极 | 将反、临界、盛极而衰、最后的辉煌 |

## 势能 -> 氛围翻译表

| 阶段 | 氛围基调 | 剧情张力 |
|------|---------|---------|
| 平静 (<0.3) | 安宁，表面无事 | 暗埋伏笔，读者感觉"有点不对劲" |
| 积蓄 (0.3-0.7) | 不安，隐忧弥漫 | 裂纹在不可见处蔓延，紧张感上升 |
| 临界 (0.7-1.0) | 锋利，一触即发 | 主角或局势随时可能崩溃或爆发 |
| 爆发 (>1.0) | 不可逆，旧死新生 | 旧结构正在瓦解，新秩序强制降临 |

## 输出格式

你必须按以下格式输出：

### 场景描写（300-600字）
一段有画面感的小说场景。必须包含：
- 具体的环境（地点、空间、天气、时间）
- 具体的人物或力量（在做什么、如何做）
- 具体的事件（正在发生什么、发生了什么变化）
- 感官细节（视觉、听觉、动态、氛围）

### 对应关系标注
在场景描写之后，用列表明确标注：
- 体（{body_protocol}）在剧情中体现为：________
- 用（{usage_protocol}）在剧情中体现为：________
- 关系（{relation['type']}）在剧情中体现为：________
- 相位（{usage['life_stage']}，{mean_phase:.2f}）在剧情中体现为：________
- 势能（{pot_stage['ratio_label']}，比例{pot_stage['ratio']:.2f}）在剧情中体现为：________
"""

user_prompt_c = f"""以下是系统从易道动态世界引擎采集到的观测数据。

**特别注意：这次的关系是"{relation['type']}"，这是叙事张力最强的关系类型。你必须同时写出两极——体的阴暗面/内在本质和用的光明面/外在显化——让它们在剧中互相撕扯。不要只写好话，不要下吉凶判断。让读者感受到那种"荣耀与诅咒并存"的撕裂感。**

要求：
1. 剧情中的每一个核心元素都必须能在系统指令中找到对应
2. 体的协议"{body_protocol}"必须在场景中有一个**持续存在的底色/背景**
3. 用的协议"{usage_protocol}"必须在场景中有一个**正在发生的行动/事件**
4. 关系"{relation['type']}"必须体现在这两个元素如何**互动和撕扯**
5. 相位和势能必须体现在剧情的**时间感和氛围**中
6. 使用【象】中的感官词汇来丰富画面

---

{semantic_package}

---

请生成场景描写 + 对应关系标注：
"""

with open("stage2v4_system_prompt.txt", "w", encoding="utf-8") as f:
    f.write(system_prompt_c)
with open("stage2v4_user_prompt.txt", "w", encoding="utf-8") as f:
    f.write(user_prompt_c)

# ───────────────────────────────────────────
# 6. 调用 LLM
# ───────────────────────────────────────────
print("\n[6/6] 调用 LLM API...")

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
}

payload = {
    "model": MODEL,
    "messages": [
        {"role": "system", "content": system_prompt_c},
        {"role": "user", "content": user_prompt_c},
    ],
    "temperature": 0.7,
    "max_tokens": 4096,
}

try:
    resp = requests.post(
        f"{API_BASE}/chat/completions",
        headers=headers,
        json=payload,
        timeout=60,
    )
    resp.raise_for_status()
    result = resp.json()
    llm_output = result["choices"][0]["message"]["content"]
    usage_info = result.get("usage", {})

    print(f"  API 成功 | 输入: {usage_info.get('prompt_tokens', '?')} | 输出: {usage_info.get('completion_tokens', '?')}")

    with open("stage2v4_llm_output.txt", "w", encoding="utf-8") as f:
        f.write(llm_output)
    print("  已保存: stage2v4_llm_output.txt")

except Exception as e:
    print(f"  API 失败: {e}")
    sys.exit(1)

# ───────────────────────────────────────────
# 7. 验证：对冲张力质量
# ───────────────────────────────────────────
print("\n" + "=" * 60)
print("【对冲张力验证】")
print("=" * 60)

output = llm_output

checks = []

# 7.1 体协议是否体现
body_protocol_keywords = {
    "承载": ["承载", "包容", "孕育", "大地", "母腹", "容器", "沃土", "消化"],
    "激变": ["激变", "突发", "惊醒", "裂变", "地震", "惊雷", "火山", "起义", "爆炸", "警钟"],
    "深渊": ["深渊", "危险", "未知", "潜伏", "矿井", "密室", "禁地", "暗河", "阴谋"],
    "渗透": ["渗透", "扩散", "风化", "潜移默化", "风沙", "流言", "霉菌", "雾气"],
    "止界": ["止界", "静止", "边界", "封印", "牢笼", "冻土", "禁令", "界碑", "阻断"],
    "显文明": ["显文明", "照明", "命名", "网络化", "灯塔", "剧场", "广场", "画布", "庆典"],
    "交换": ["交换", "契约", "贸易", "差异", "市集", "赌场", "谈判", "交易"],
    "创序": ["创序", "秩序", "命名", "规则", "立法", "测量", "殖民", "筑城", "军队", "征服"],
}
body_kw = body_protocol_keywords.get(body_protocol, [body_protocol])
has_body_protocol = any(kw in output for kw in body_kw)
checks.append((f"体的协议 '{body_protocol}' 在剧情中有体现", has_body_protocol))

# 7.2 用协议是否体现
usage_kw = body_protocol_keywords.get(usage_protocol, [usage_protocol])
has_usage_protocol = any(kw in output for kw in usage_kw)
checks.append((f"用的协议 '{usage_protocol}' 在剧情中有体现", has_usage_protocol))

# 7.3 对冲关系是否体现张力
# 对冲的特殊要求：同时写出两极、撕扯、张力
has_two_poles = any(w in output for w in ["光明", "黑暗", "荣耀", "诅咒", "辉煌", "腐朽", "温暖", "冰冷", "秩序", "混沌"])
has_tearing = any(w in output for w in ["撕扯", "撕裂", "拉扯", "撕裂", "挣扎", "交战", "对抗", "撕"])
has_tension_word = any(w in output for w in ["张力", "两极", "矛盾", "冲突", "撕裂", "撕扯"])
checks.append((f"对冲关系：同时写出两极（光明/黑暗等）", has_two_poles))
checks.append((f"对冲关系：体现撕扯/对抗感", has_tearing or has_tension_word))

# 7.4 没有下吉凶判断
good_bad_words = ["大吉", "大凶", "吉兆", "凶兆", "好运", "厄运", "注定胜利", "注定失败", "必将成功", "必将毁灭"]
has_judgment = any(w in output for w in good_bad_words)
checks.append(("没有下绝对的吉凶判断", not has_judgment))

# 7.5 相位是否体现
phase = mean_phase
phase_kw_map = {
    (0.0, 0.15): ["潜藏", "尚未", "地下", "压抑", "伏笔"],
    (0.15, 0.30): ["萌生", "露头", "初现", "试探", "微光"],
    (0.30, 0.50): ["成长", "上升", "扩展", "渐盛", "积累"],
    (0.50, 0.70): ["盛壮", "鼎盛", "辉煌", "主宰", "充盈"],
    (0.70, 0.85): ["持守", "守成", "高处", "隐忧"],
    (0.85, 1.00): ["过极", "将反", "临界", "盛极", "回光"],
}
phase_kw = []
for (lo, hi), kws in phase_kw_map.items():
    if lo <= phase < hi:
        phase_kw = kws
        break
if not phase_kw:
    phase_kw = ["过极", "将反", "临界"]
has_phase = any(kw in output for kw in phase_kw)
checks.append((f"相位 {phase:.2f} 的生命阶段在剧情中有体现", has_phase))

# 7.6 势能是否体现
pot_ratio = pot_stage['ratio']
pot_kw_map = {
    (0.0, 0.3): ["平静", "安宁", "无事", "无痕", "沉睡"],
    (0.3, 0.7): ["积蓄", "不安", "隐忧", "裂纹", "蔓延"],
    (0.7, 1.0): ["临界", "一触即发", "锋利", "变重", "屏息"],
    (1.0, 999.0): ["爆发", "瓦解", "反转", "倾覆", "旧死新生"],
}
pot_kw = []
for (lo, hi), kws in pot_kw_map.items():
    if lo <= pot_ratio < hi:
        pot_kw = kws
        break
if not pot_kw:
    pot_kw = ["爆发", "瓦解"]
has_potential = any(kw in output for kw in pot_kw)
checks.append((f"势能比例 {pot_ratio:.2f} 的氛围在剧情中有体现", has_potential))

# 7.7 有对应关系标注
has_annotation = "对应关系标注" in output or "体（" in output or "用（" in output or "关系（" in output
checks.append(("有对应关系标注", has_annotation))

# 7.8 具象化质量
has_setting = any(w in output for w in ["山", "水", "洞", "城", "墙", "河", "林", "谷", "塔", "地", "天", "街道", "废墟"])
checks.append(("有具体环境", has_setting))

has_actor = any(w in output for w in ["人", "者", "队", "军", "工", "匠", "行走", "站立", "挖掘", "建造", "他们", "身影"])
checks.append(("有具体人物/行动者", has_actor))

has_event = any(w in output for w in ["突然", "正在", "这时", "随即", "传来", "落下", "崩塌", "点燃", "裂开"])
checks.append(("有具体事件", has_event))

has_sensory = any(w in output for w in ["光", "暗", "声", "响", "静", "风", "火", "冷", "热", "味道", "气味"])
checks.append(("有感官细节", has_sensory))

all_pass = True
for desc, ok in checks:
    status = "PASS" if ok else "FAIL"
    if not ok:
        all_pass = False
    print(f"  [{status}] {desc}")

print()
if all_pass:
    print(">>> 对冲张力测试通过")
else:
    print(">>> 部分验证未通过")
print("=" * 60)

print("\n【LLM 生成的剧情场景】\n")
print(output)
