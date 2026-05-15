# -*- coding: utf-8 -*-
"""
阶段五：多实体交叉观测 + 互动叙事测试
同时追踪两个实体，寻找它们轨迹的交叉时刻，验证 LLM 能否生成有互动的双主角叙事
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
from event_engine import EventEngine
from codex import get_gua, get_phase_meaning
from phenomenon_codex import get_potential_stage, get_manifestation, get_phenomenon

API_BASE = "https://token-plan-cn.xiaomimimo.com/v1"
API_KEY = os.environ.get("YIDAO_API_KEY", "")
MODEL = "mimo-v2.5-pro"


def _get_pure_hex(protocol_name):
    protocol_map = {
        "承载": 0, "激变": 9, "深渊": 18, "渗透": 27,
        "止界": 36, "显文明": 45, "交换": 54, "创序": 63,
    }
    return protocol_map.get(protocol_name, 0)


def capture_snapshot(world, cam, tracker, analyst, tick_label):
    """在某一 tick 采集完整观测数据"""
    cam.move_to(tracker.center_y, tracker.center_x)
    packet = cam.capture()
    body_usage = analyst.run_two_rounds(tracker, perspective="objective")

    radius = cam._get_radius()
    y0, x0, y1, x1 = cam._focus_rect(radius)
    region_pot = world.potential[y0:y1, x0:x1]
    region_phase = world.phase[y0:y1, x0:x1]
    mean_pot = float(region_pot.mean()) if region_pot.size > 0 else 0.0
    mean_phase = float(region_phase.mean()) if region_phase.size > 0 else 0.0
    pot_stage = get_potential_stage(mean_pot, world.V_thresh)

    body = body_usage["body"]
    usage = body_usage["usage"]
    relation = body_usage["relation"]

    cy, cx = tracker.center_y, tracker.center_x
    center_gua = int(world.gua[cy, cx])
    center_trend = float(world.trend[cy, cx])
    center_phase = float(world.phase[cy, cx])
    center_pot = float(world.potential[cy, cx])

    protocol = usage.get("_meta", {}).get("protocol", get_gua(usage["current_hex"]).get("protocol", "复合"))
    pure_hex = _get_pure_hex(protocol)
    manifestation = get_manifestation(pure_hex, cam.intent or "character")
    visual_words = get_phenomenon(pure_hex, "visual")
    sound_words = get_phenomenon(pure_hex, "sound")
    motion_words = get_phenomenon(pure_hex, "motion")
    mood_words = get_phenomenon(pure_hex, "mood")

    return {
        "tick_label": tick_label,
        "tick": world.tick_count,
        "center_gua": center_gua,
        "center_gua_name": get_gua(center_gua)["name"],
        "center_protocol": get_gua(center_gua)["protocol"],
        "center_trend": round(center_trend, 3),
        "center_phase": round(center_phase, 3),
        "center_pot": round(center_pot, 3),
        "body": body,
        "usage": usage,
        "relation": relation,
        "mean_pot": round(mean_pot, 3),
        "mean_phase": round(mean_phase, 3),
        "pot_stage": pot_stage,
        "manifestation": manifestation,
        "sensory": {
            "visual": visual_words[:3],
            "sound": sound_words[:3],
            "motion": motion_words[:3],
            "mood": mood_words[:3],
        },
    }


def compute_interaction(a_snap, b_snap):
    """计算两个实体在某一时刻的交互关系"""
    a_hex = a_snap["center_gua"]
    b_hex = b_snap["center_gua"]
    opp_pairs = [(0,63),(9,54),(18,45),(27,36)]
    is_opposite = (a_hex, b_hex) in opp_pairs or (b_hex, a_hex) in opp_pairs
    is_same = a_hex == b_hex
    pot_diff = abs(a_snap["center_pot"] - b_snap["center_pot"])
    phase_diff = abs(a_snap["center_phase"] - b_snap["center_phase"])
    a_rel = a_snap["relation"]["type"]
    b_rel = b_snap["relation"]["type"]

    score = 0
    if is_opposite: score += 5
    if is_same: score += 2
    score += pot_diff * 2
    score += phase_diff * 2
    if a_rel != b_rel: score += 1

    return {
        "score": score,
        "is_opposite": is_opposite,
        "is_same": is_same,
        "pot_diff": round(pot_diff, 3),
        "phase_diff": round(phase_diff, 3),
        "a_relation": a_rel,
        "b_relation": b_rel,
    }


print("=" * 60)
print("【阶段五】多实体交叉观测 + 互动叙事测试")
print("=" * 60)

# ───────────────────────────────────────────
# 1. 初始化世界并长期运行（追踪两个实体）
# ───────────────────────────────────────────
print("\n[1/6] 初始化世界，追踪两个实体，运行 3000 tick...")
world = World(height=32, width=64)
cam = WorldCamera(world, y=16, x=32, scale="meso", intent="faction")
analyst = YaoAnalyst(cam)
engine = EventEngine(world, analyst)

tracker_a = EntityTracker(world, "entity_north", 10, 20, radius=4)
tracker_b = EntityTracker(world, "entity_south", 22, 44, radius=4)

flip_events_a = []
flip_events_b = []
all_snapshots_a = []
all_snapshots_b = []

for i in range(3000):
    world.tick()
    tracker_a._update()
    tracker_b._update()

    if len(tracker_a.hex_history) >= 2:
        prev, curr = tracker_a.hex_history[-2], tracker_a.hex_history[-1]
        if prev != curr:
            flip_events_a.append({
                "tick": world.tick_count, "pre_hex": prev, "post_hex": curr,
                "pre_name": get_gua(prev)["name"], "post_name": get_gua(curr)["name"],
            })
    if len(tracker_b.hex_history) >= 2:
        prev, curr = tracker_b.hex_history[-2], tracker_b.hex_history[-1]
        if prev != curr:
            flip_events_b.append({
                "tick": world.tick_count, "pre_hex": prev, "post_hex": curr,
                "pre_name": get_gua(prev)["name"], "post_name": get_gua(curr)["name"],
            })

    if (i + 1) % 100 == 0:
        all_snapshots_a.append(capture_snapshot(world, cam, tracker_a, analyst, f"A_T{i+1}"))
        all_snapshots_b.append(capture_snapshot(world, cam, tracker_b, analyst, f"B_T{i+1}"))

    if (i + 1) % 500 == 0:
        print(f"  ...{i+1} 息 | A卦变{len(flip_events_a)}次 | B卦变{len(flip_events_b)}次")

print(f"\n运行完成：A 卦变 {len(flip_events_a)} 次，B 卦变 {len(flip_events_b)} 次")

# ───────────────────────────────────────────
# 2. 寻找两个实体轨迹的"交叉时刻"
# ───────────────────────────────────────────
print("\n[2/6] 寻找两个实体轨迹的交叉时刻...")

best_cross = None
best_score = -1

for ev_a in flip_events_a:
    tick = ev_a["tick"]
    b_snap = None
    for sb in all_snapshots_b:
        if abs(sb["tick"] - tick) <= 50:
            b_snap = sb
            break
    a_snap = None
    for sa in all_snapshots_a:
        if abs(sa["tick"] - tick) <= 50:
            a_snap = sa
            break
    if a_snap is None or b_snap is None:
        continue

    inter = compute_interaction(a_snap, b_snap)
    for ev_b in flip_events_b:
        if abs(ev_b["tick"] - tick) <= 50:
            inter["b_also_flipped"] = True
            inter["score"] += 3
            break
    else:
        inter["b_also_flipped"] = False

    if inter["score"] > best_score:
        best_score = inter["score"]
        best_cross = {
            "tick": tick, "a_flip": ev_a,
            "a_snap": a_snap, "b_snap": b_snap,
            "interaction": inter,
        }

for ev_b in flip_events_b:
    tick = ev_b["tick"]
    a_snap = None
    for sa in all_snapshots_a:
        if abs(sa["tick"] - tick) <= 50:
            a_snap = sa
            break
    b_snap = None
    for sb in all_snapshots_b:
        if abs(sb["tick"] - tick) <= 50:
            b_snap = sb
            break
    if a_snap is None or b_snap is None:
        continue

    inter = compute_interaction(a_snap, b_snap)
    for ev_a in flip_events_a:
        if abs(ev_a["tick"] - tick) <= 50:
            inter["a_also_flipped"] = True
            inter["score"] += 3
            break
    else:
        inter["a_also_flipped"] = False

    if inter["score"] > best_score:
        best_score = inter["score"]
        best_cross = {
            "tick": tick, "b_flip": ev_b,
            "a_snap": a_snap, "b_snap": b_snap,
            "interaction": inter,
        }

if best_cross is None:
    print("  未找到显著的交叉时刻，使用最后时刻...")
    best_cross = {
        "tick": 3000,
        "a_snap": all_snapshots_a[-1], "b_snap": all_snapshots_b[-1],
        "interaction": compute_interaction(all_snapshots_a[-1], all_snapshots_b[-1]),
    }

print(f"\n选定交叉时刻：tick {best_cross['tick']}")
print(f"  A: {best_cross['a_snap']['center_gua_name']} | 体:{best_cross['a_snap']['body']['body_protocol']} | 用:{best_cross['a_snap']['usage']['current_name']} | 势:{best_cross['a_snap']['center_pot']:.2f}")
print(f"  B: {best_cross['b_snap']['center_gua_name']} | 体:{best_cross['b_snap']['body']['body_protocol']} | 用:{best_cross['b_snap']['usage']['current_name']} | 势:{best_cross['b_snap']['center_pot']:.2f}")
print(f"  交互评分: {best_cross['interaction']['score']:.1f} | 先天对卦: {best_cross['interaction']['is_opposite']} | 势能差: {best_cross['interaction']['pot_diff']:.2f}")

# ───────────────────────────────────────────
# 3. 围绕交叉时刻提取 4 个时间切片
# ───────────────────────────────────────────
print("\n[3/6] 提取双实体时间切片...")

cross_tick = best_cross["tick"]

def find_nearest(snapshots, target_tick, label_prefix):
    best = min(snapshots, key=lambda s: abs(s["tick"] - target_tick))
    best["tick_label"] = f"{label_prefix}_T{best['tick']}"
    return best

pre2_a = find_nearest(all_snapshots_a, cross_tick - 400, "A")
pre2_b = find_nearest(all_snapshots_b, cross_tick - 400, "B")
pre1_a = find_nearest(all_snapshots_a, cross_tick - 150, "A")
pre1_b = find_nearest(all_snapshots_b, cross_tick - 150, "B")
t0_a = best_cross["a_snap"]
t0_b = best_cross["b_snap"]
t0_a["tick_label"] = "A_T0"
t0_b["tick_label"] = "B_T0"
post_a = find_nearest(all_snapshots_a, cross_tick + 200, "A")
post_b = find_nearest(all_snapshots_b, cross_tick + 200, "B")

slices = [
    ("T-2 各自稳态", pre2_a, pre2_b),
    ("T-1 临近感知", pre1_a, pre1_b),
    ("T0 交叉时刻", t0_a, t0_b),
    ("T+1 新态互动", post_a, post_b),
]

for label, sa, sb in slices:
    inter = compute_interaction(sa, sb)
    print(f"  {label}: A={sa['center_gua_name']}(势{sa['center_pot']:.2f}) | B={sb['center_gua_name']}(势{sb['center_pot']:.2f}) | 交互分={inter['score']:.1f}")

# ───────────────────────────────────────────
# 4. 构造双实体语义包
# ───────────────────────────────────────────
print("\n[4/6] 构造双实体语义包...")


def format_entity_snapshot(snap, entity_label):
    return f"""【{entity_label}】tick {snap['tick']}
单点: {snap['center_gua_name']}({snap['center_gua']}) | {snap['center_protocol']} | 相位:{snap['center_phase']:.2f} | 势能:{snap['center_pot']:.2f}
体: {snap['body']['body_name']}({snap['body']['body_hex']}) | {snap['body']['body_protocol']} | 本质: {snap['body']['body_nature'].split('。')[0]}。
用: {snap['usage']['current_name']}({snap['usage']['current_hex']}) | {get_gua(snap['usage']['current_hex'])['protocol']}
结构语气: {snap['usage']['structural_tone']} | 生命阶段: {snap['usage']['life_stage']}
关系: {snap['relation']['type']} | {snap['relation']['description']}
势能: {snap['pot_stage']['ratio_label']} ({snap['pot_stage']['atmosphere']})
感官: 视-{', '.join(snap['sensory']['visual'])} | 听-{', '.join(snap['sensory']['sound'])} | 动-{', '.join(snap['sensory']['motion'])} | 情-{', '.join(snap['sensory']['mood'])}
"""


timeline_package = f"""【观测对象】双实体交叉观测
【实体A】{tracker_a.entity_id} — 北方偏西的实体
【实体B】{tracker_b.entity_id} — 南方偏东的实体
【交叉时刻】tick {cross_tick}

以下是两个实体在交叉前后连续采集到的 4 个时间切片：

═══════════════════════════════════════════════════
{format_entity_snapshot(pre2_a, '实体A · T-2 各自稳态')}
{format_entity_snapshot(pre2_b, '实体B · T-2 各自稳态')}
═══════════════════════════════════════════════════
{format_entity_snapshot(pre1_a, '实体A · T-1 临近感知')}
{format_entity_snapshot(pre1_b, '实体B · T-1 临近感知')}
═══════════════════════════════════════════════════
{format_entity_snapshot(t0_a, '实体A · T0 交叉时刻')}
{format_entity_snapshot(t0_b, '实体B · T0 交叉时刻')}
【交互分析】此时两实体关系: {"先天对卦（极致张力）" if best_cross['interaction']['is_opposite'] else ("同卦（共鸣）" if best_cross['interaction']['is_same'] else "异卦")} | 势能差: {best_cross['interaction']['pot_diff']:.2f} | 相位差: {best_cross['interaction']['phase_diff']:.2f}
═══════════════════════════════════════════════════
{format_entity_snapshot(post_a, '实体A · T+1 新态互动')}
{format_entity_snapshot(post_b, '实体B · T+1 新态互动')}
═══════════════════════════════════════════════════
"""

with open("stage5_timeline_package.txt", "w", encoding="utf-8") as f:
    f.write(timeline_package)

# ───────────────────────────────────────────
# 5. 构造双实体互动叙事 Prompt
# ───────────────────────────────────────────
print("\n[5/6] 构造双实体互动叙事 prompt...")

system_prompt = """你是一位精通《易经》的世界编年史作者。你的任务是把系统同时跟踪两个实体采集到的观测数据，编织成一段**有互动的双主角连续叙事**。

## 核心规则（Route-C 协议）

1. **双主角结构**：这不是一个实体的独角戏，而是两个实体（A 和 B）的互动史。每个实体都有自己的体（本质）和用（当下显化），同时两者之间还有"关系"。
2. **体的个体性与互动性**：每个实体有自己的"体"作为不变底色，但它们的"用"会在相遇时相互影响。叙事要写出"两个独立灵魂的碰撞"。
3. **交互关系优先**：当两个实体处于同一时刻时，它们之间的卦象关系（先天对卦/同卦/异卦）是叙事的核心张力来源。先天对卦意味着极致的吸引与排斥并存；同卦意味着共鸣与叠加；异卦意味着差异与互补。
4. **时间连续性与因果链**：四个时间切片不是孤立的，而是：各自生长 → 开始感知 → 碰撞/交叉 → 各自改变的完整弧线。
5. **卦变仪式感**：如果某个实体在 T0 发生了卦变，那一刻必须有仪式感——旧结构的自我瓦解与新结构的强制降临。
6. **强制映射标注**：叙事之后必须写"### 对应关系标注"，列出每个系统概念（每个实体的体/用/势/系）对应到叙事中的哪个元素。

## 叙事结构要求

你必须按以下结构输出：

### 连贯叙事（800-1200字）
一段跨越四个时间切片的双主角连续故事。要求：
- 实体A 和 实体B 都有明确的"性格"（由体的本质决定）
- 两个实体之间要有真实的互动（不是各自独白）
- T-2：各自在自己的轨道上运行，但隐约感觉到远方的存在
- T-1：开始感知到彼此的影响，气氛微妙变化
- T0：交叉/碰撞/相遇的核心时刻，张力最大
- T+1：交叉后的余波，两个实体都被改变了

### 双实体对应关系标注
用表格或列表明确标注：
| 时间 | 实体 | 体协议体现 | 用协议体现 | 关系体现 | 相位/势能体现 |

### 叙事质量自检
1. 叙事中是否有"各自生长 → 感知 → 碰撞 → 改变"的因果链？
2. 两个实体是否有真实的互动（而非各自独白）？
3. 交叉时刻（T0）是否有足够的张力/仪式感？
4. 两个实体的体的本质是否各自保持了一致性？
5. 是否同时写出了两极（吸引/排斥、光明/黑暗、融合/分裂）？
"""

flip_info = ""
if "a_flip" in best_cross:
    flip_info = f"实体A 在 tick {cross_tick} 经历了卦变: {best_cross['a_flip']['pre_name']} -> {best_cross['a_flip']['post_name']}"
elif "b_flip" in best_cross:
    flip_info = f"实体B 在 tick {cross_tick} 经历了卦变: {best_cross['b_flip']['pre_name']} -> {best_cross['b_flip']['post_name']}"

user_prompt = f"""以下是系统从易道动态世界引擎同时跟踪两个实体采集到的时间序列数据。

{flip_info}
两个实体之间的交互特征：{"先天对卦——极致的张力与吸引" if best_cross['interaction']['is_opposite'] else ("同卦——共鸣与叠加" if best_cross['interaction']['is_same'] else "异卦——差异与互补")}，势能差 {best_cross['interaction']['pot_diff']:.2f}，相位差 {best_cross['interaction']['phase_diff']:.2f}。

请你把四个时间切片编织成一段**双主角的、有互动的、有因果的**连续叙事，像一部关于两个灵魂相遇的短篇史诗。

要求：
1. 不要写成两个独立的独角戏，要写出它们之间的真实互动
2. 读者应该能感受到"如果A不存在，B的故事会完全不同"
3. 每个实体都有自己的"体的本质"作为不变底色
4. 交叉时刻要有仪式感
5. 使用感官词汇丰富画面

---

{timeline_package}

---

请生成连贯叙事 + 双实体对应关系标注 + 叙事质量自检：
"""

with open("stage5_system_prompt.txt", "w", encoding="utf-8") as f:
    f.write(system_prompt)
with open("stage5_user_prompt.txt", "w", encoding="utf-8") as f:
    f.write(user_prompt)

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
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ],
    "temperature": 0.7,
    "max_tokens": 4096,
}

try:
    resp = requests.post(
        f"{API_BASE}/chat/completions",
        headers=headers,
        json=payload,
        timeout=120,
    )
    resp.raise_for_status()
    result = resp.json()
    llm_output = result["choices"][0]["message"]["content"]
    usage_info = result.get("usage", {})

    print(f"  API 成功 | 输入: {usage_info.get('prompt_tokens', '?')} | 输出: {usage_info.get('completion_tokens', '?')}")

    with open("stage5_llm_output.txt", "w", encoding="utf-8") as f:
        f.write(llm_output)
    print("  已保存: stage5_llm_output.txt")

except Exception as e:
    print(f"  API 失败: {e}")
    sys.exit(1)

# ───────────────────────────────────────────
# 7. 验证：双实体互动叙事质量
# ───────────────────────────────────────────
print("\n" + "=" * 60)
print("【双实体互动叙事验证】")
print("=" * 60)

output = llm_output
checks = []

has_both = (tracker_a.entity_id in output or "实体A" in output or "北方" in output)
has_both = has_both and (tracker_b.entity_id in output or "实体B" in output or "南方" in output)
checks.append(("两个实体都在叙事中出现", has_both))

interaction_words = ["碰撞", "相遇", "对抗", "共鸣", "影响", "改变", "交织", "纠缠", "彼此", "对方", "它"]
has_interaction = any(w in output for w in interaction_words)
checks.append(("有真实互动（非独白）", has_interaction))

causal = ["因此", "所以", "因为", "于是", "导致", "源于", "终于"]
has_causal = any(w in output for w in causal)
checks.append(("有因果逻辑链", has_causal))

time_words = ["起初", "后来", "随后", "终于", "之前", "之后", "当", "那一刻"]
has_time = any(w in output for w in time_words)
checks.append(("有时间流逝感", has_time))

a_body = pre2_a["body"]["body_protocol"]
b_body = pre2_b["body"]["body_protocol"]
checks.append((f"实体A的体 '{a_body}' 贯穿", a_body in output))
checks.append((f"实体B的体 '{b_body}' 贯穿", b_body in output))

a_usage_pre = pre2_a["usage"]["current_name"]
a_usage_post = post_a["usage"]["current_name"]
b_usage_pre = pre2_b["usage"]["current_name"]
b_usage_post = post_b["usage"]["current_name"]
has_usage = (a_usage_pre in output or a_usage_post in output) and (b_usage_pre in output or b_usage_post in output)
checks.append(("两个实体的用都有体现", has_usage))

ritual = ["宿命", "轰鸣", "自决", "强制", "降临", "产道", "不可逆转", "旧死新生"]
has_ritual = any(w in output for w in ritual)
checks.append(("卦变有仪式感", has_ritual))

polar = ["光明", "黑暗", "荣耀", "诅咒", "辉煌", "腐朽", "温暖", "冰冷"]
has_polar = sum(1 for w in polar if w in output) >= 2
checks.append(("两极并存", has_polar))

has_table = "对应关系" in output or "对应表" in output or "|" in output
checks.append(("有对应关系标注", has_table))

has_check = "自检" in output or "因果链" in output or "一致性" in output
checks.append(("有质量自检", has_check))

sensory = ["光", "暗", "声", "响", "静", "风", "火", "冷", "热", "味道", "颤抖", "震动"]
has_sensory = any(w in output for w in sensory)
checks.append(("有感官细节", has_sensory))

tension = ["张力", "极致", "巅峰", "临界", "碰撞", "爆发", "撕裂", "裂变"]
has_tension = any(w in output for w in tension)
checks.append(("交叉时刻有张力描写", has_tension))

all_pass = True
for desc, ok in checks:
    status = "PASS" if ok else "FAIL"
    if not ok:
        all_pass = False
    print(f"  [{status}] {desc}")

print()
if all_pass:
    print(">>> 双实体互动叙事测试通过")
else:
    print(">>> 部分验证未通过")
print("=" * 60)

print("\n【LLM 生成的双实体互动叙事】\n")
print(output[:1500])
print("\n... [截断，完整内容见 stage5_llm_output.txt]")
