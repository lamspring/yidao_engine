# -*- coding: utf-8 -*-
"""
阶段六：五口之家家庭史诗测试
同时追踪五个实体（家庭成员），寻找家庭级共振事件，验证 LLM 能否生成多角色家族叙事
"""

import json
import os
import sys
import io
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
    protocol_map = {"承载":0, "激变":9, "深渊":18, "渗透":27, "止界":36, "显文明":45, "交换":54, "创序":63}
    return protocol_map.get(protocol_name, 0)


def capture_compact(world, cam, tracker, analyst, tick_label):
    """精简版快照：只保留叙事必需字段，控制token量"""
    cam.move_to(tracker.center_y, tracker.center_x)
    body_usage = analyst.run_two_rounds(tracker, perspective="objective")
    cy, cx = tracker.center_y, tracker.center_x
    center_gua = int(world.gua[cy, cx])
    center_phase = float(world.phase[cy, cx])
    center_pot = float(world.potential[cy, cx])
    body = body_usage["body"]
    usage = body_usage["usage"]
    relation = body_usage["relation"]
    pot_stage = get_potential_stage(center_pot, world.V_thresh)
    return {
        "tick_label": tick_label, "tick": world.tick_count,
        "center_gua": center_gua, "center_gua_name": get_gua(center_gua)["name"],
        "center_protocol": get_gua(center_gua)["protocol"],
        "center_phase": round(center_phase, 2), "center_pot": round(center_pot, 2),
        "body_name": body["body_name"], "body_protocol": body["body_protocol"],
        "body_nature": body["body_nature"].split("。")[0] + "。",
        "usage_name": usage["current_name"], "usage_hex": usage["current_hex"],
        "structural_tone": usage["structural_tone"],
        "life_stage": usage["life_stage"],
        "relation_type": relation["type"], "relation_desc": relation["description"],
        "pot_label": pot_stage["ratio_label"], "pot_atmosphere": pot_stage["atmosphere"],
    }


def family_interaction_score(snapshots):
    """计算家庭整体交互故事性评分"""
    n = len(snapshots)
    score = 0
    # 1. 先天对卦对数
    opp_pairs = {(0,63),(9,54),(18,45),(27,36)}
    opposite_count = 0
    same_count = 0
    pot_spread = 0
    for i in range(n):
        for j in range(i+1, n):
            a, b = snapshots[i]["center_gua"], snapshots[j]["center_gua"]
            if (a,b) in opp_pairs or (b,a) in opp_pairs:
                opposite_count += 1
            if a == b:
                same_count += 1
            pot_spread = max(pot_spread, abs(snapshots[i]["center_pot"] - snapshots[j]["center_pot"]))
    score += opposite_count * 4
    score += same_count * 2
    score += pot_spread * 3
    # 2. 关系多样性
    rels = set(s["relation_type"] for s in snapshots)
    score += len(rels) * 2
    # 3. 势能极端值
    max_pot = max(s["center_pot"] for s in snapshots)
    min_pot = min(s["center_pot"] for s in snapshots)
    score += max_pot * 2
    if max_pot > 1.5 and min_pot < 0.3:
        score += 3  # 极端分化
    return round(score, 1)


def detect_family_events(flip_events_list, all_snaps_list, tick_window=50):
    """检测家庭级事件"""
    events = []
    # 遍历所有可能的tick
    for t in range(tick_window, 3000 - tick_window, tick_window // 2):
        # 收集该tick附近所有实体的快照
        nearby_snaps = []
        for idx, snaps in enumerate(all_snaps_list):
            best = None
            for s in snaps:
                if abs(s["tick"] - t) <= tick_window:
                    if best is None or abs(s["tick"] - t) < abs(best["tick"] - t):
                        best = s
            if best:
                best["member_idx"] = idx
                nearby_snaps.append(best)

        if len(nearby_snaps) < 3:
            continue

        score = family_interaction_score(nearby_snaps)

        # 统计卦变
        flip_count = 0
        for idx, flips in enumerate(flip_events_list):
            for f in flips:
                if abs(f["tick"] - t) <= tick_window:
                    flip_count += 1
                    break

        if flip_count >= 2:
            score += flip_count * 3

        events.append({"tick": t, "score": score, "snaps": nearby_snaps, "flip_count": flip_count})

    events.sort(key=lambda x: x["score"], reverse=True)
    return events


print("=" * 60)
print("【阶段六】五口之家家庭史诗测试")
print("=" * 60)

# ───────────────────────────────────────────
# 1. 初始化世界 + 五口之家
# ───────────────────────────────────────────
print("\n[1/6] 初始化世界，放置五口之家，运行 3000 tick...")
world = World(height=32, width=64)
cam = WorldCamera(world, y=14, x=30, scale="meso", intent="character")
analyst = YaoAnalyst(cam)
engine = EventEngine(world, analyst)

# 五口之家：父亲、母亲、长子、次子、幼女
# 放置在一个 8×10 的家庭区域内，间距2-3格
members = [
    ("father",    12, 28, "父亲 — 家族的根基与秩序"),
    ("mother",    12, 32, "母亲 — 家族的渗透与滋养"),
    ("eldest",    14, 26, "长子 — 家族的锋芒与开拓"),
    ("second",    14, 34, "次子 — 家族的变动与探索"),
    ("youngest",  16, 30, "幼女 — 家族的生机与变数"),
]

trackers = []
flip_events_list = []
all_snaps_list = []

for name, y, x, desc in members:
    t = EntityTracker(world, name, y, x, radius=3)
    trackers.append(t)
    flip_events_list.append([])
    all_snaps_list.append([])

for i in range(1500):
    world.tick()
    for idx, t in enumerate(trackers):
        t._update()
        if len(t.hex_history) >= 2:
            prev, curr = t.hex_history[-2], t.hex_history[-1]
            if prev != curr:
                flip_events_list[idx].append({
                    "tick": world.tick_count, "pre_hex": prev, "post_hex": curr,
                    "pre_name": get_gua(prev)["name"], "post_name": get_gua(curr)["name"],
                })

    if (i + 1) % 150 == 0:
        for idx, t in enumerate(trackers):
            all_snaps_list[idx].append(capture_compact(world, cam, t, analyst, f"{t.entity_id}_T{i+1}"))

    if (i + 1) % 500 == 0:
        total_flips = sum(len(f) for f in flip_events_list)
        print(f"  ...{i+1} 息 | 家庭总卦变 {total_flips} 次")

total_flips = sum(len(f) for f in flip_events_list)
print(f"\n运行完成：五口之家总卦变 {total_flips} 次")
for idx, (name, _, _, desc) in enumerate(members):
    print(f"  {name}: {len(flip_events_list[idx])} 次卦变")

# ───────────────────────────────────────────
# 2. 检测家庭级事件
# ───────────────────────────────────────────
print("\n[2/6] 检测家庭级共振事件...")

family_events = detect_family_events(flip_events_list, all_snaps_list, tick_window=75)

if not family_events:
    print("  未检测到显著家庭事件，使用最后时刻...")
    best_event = {
        "tick": 3000,
        "score": 0,
        "snaps": [all_snaps_list[i][-1] for i in range(5)],
        "flip_count": 0,
    }
else:
    best_event = family_events[0]

print(f"\n选定家庭事件：tick {best_event['tick']} | 故事性评分: {best_event['score']:.1f} | 涉及卦变: {best_event['flip_count']} 人")
for s in best_event["snaps"]:
    print(f"  {s['tick_label']}: {s['center_gua_name']} | 体:{s['body_protocol']} | 用:{s['usage_name']} | 势:{s['center_pot']:.2f} | 关系:{s['relation_type']}")

# ───────────────────────────────────────────
# 3. 提取 5 个时间切片（围绕家庭事件）
# ───────────────────────────────────────────
print("\n[3/6] 提取家庭时间切片...")

event_tick = best_event["tick"]

def find_member_nearest(snapshots, target_tick, label):
    best = min(snapshots, key=lambda s: abs(s["tick"] - target_tick))
    best["slice_label"] = label
    return best

# 5个切片：家庭史诗的完整弧线
slice_configs = [
    ("T-2 日常稳态", event_tick - 300),
    ("T-1 暗流涌动", event_tick - 200),
    ("T0  家庭事件", event_tick),
    ("T+1 余波震荡", event_tick + 200),
    ("T+2 新秩序",   event_tick + 300),
]

family_slices = []
for label, target in slice_configs:
    member_snaps = []
    for idx in range(5):
        s = find_member_nearest(all_snaps_list[idx], target, label)
        member_snaps.append(s)
    score = family_interaction_score(member_snaps)
    family_slices.append({"label": label, "target_tick": target, "members": member_snaps, "score": score})
    rels = ", ".join(sorted(set(m["relation_type"] for m in member_snaps)))
    pots = "/".join(f"{m['center_pot']:.1f}" for m in member_snaps)
    print(f"  {label}: 交互分={score:.1f} | 关系={rels} | 势能=[{pots}]")

# ───────────────────────────────────────────
# 4. 构造家庭语义包（精简版，控制token）
# ───────────────────────────────────────────
print("\n[4/6] 构造家庭语义包...")

member_names = [m[0] for m in members]
member_descs = [m[3] for m in members]


def format_member_compact(snap, member_idx):
    name = member_names[member_idx]
    return f"  [{name}] {snap['center_gua_name']}({snap['center_gua']}) | 体:{snap['body_protocol']} | 用:{snap['usage_name']} | 关系:{snap['relation_type']} | 相:{snap['center_phase']:.2f} | 势:{snap['center_pot']:.2f}({snap['pot_label']}) | 生阶:{snap['life_stage']}"


timeline_package = f"""【观测对象】五口之家家庭史诗
【家庭成员】
  0. father    — 父亲，家族的根基与秩序
  1. mother    — 母亲，家族的渗透与滋养
  2. eldest    — 长子，家族的锋芒与开拓
  3. second    — 次子，家族的变动与探索
  4. youngest  — 幼女，家族的生机与变数

【家庭事件】tick {event_tick} | 故事性评分 {best_event['score']:.1f} | {best_event['flip_count']} 位成员经历卦变

以下是家庭在事件前后连续采集到的 5 个时间切片：

"""

for fs in family_slices:
    timeline_package += f"\n═══ {fs['label']} (tick≈{fs['target_tick']}) | 家庭交互分:{fs['score']:.1f} ═══\n"
    for idx, snap in enumerate(fs["members"]):
        timeline_package += format_member_compact(snap, idx) + "\n"
    # 添加家庭级交互分析
    opp_pairs = {(0,63),(9,54),(18,45),(27,36)}
    opposites = []
    sames = []
    for i in range(5):
        for j in range(i+1, 5):
            a, b = fs["members"][i]["center_gua"], fs["members"][j]["center_gua"]
            if (a,b) in opp_pairs or (b,a) in opp_pairs:
                opposites.append(f"{member_names[i]}-{member_names[j]}")
            if a == b:
                sames.append(f"{member_names[i]}-{member_names[j]}")
    if opposites:
        timeline_package += f"  [先天对卦] {', '.join(opposites)}\n"
    if sames:
        timeline_package += f"  [同卦共鸣] {', '.join(sames)}\n"
    max_pot = max(m["center_pot"] for m in fs["members"])
    min_pot = min(m["center_pot"] for m in fs["members"])
    timeline_package += f"  [势能极差] {min_pot:.2f} ~ {max_pot:.2f} (差={max_pot-min_pot:.2f})\n"

with open("stage6_timeline_package.txt", "w", encoding="utf-8") as f:
    f.write(timeline_package)

# 附录：每个成员的体本质详细描述（供LLM参考）
appendix = "\n【附录：各成员体的本质描述】\n\n"
for idx in range(5):
    # 取T0时刻的体描述作为代表
    t0_snap = family_slices[2]["members"][idx]
    appendix += f"{member_names[idx]}: {t0_snap['body_nature']}\n"

with open("stage6_appendix.txt", "w", encoding="utf-8") as f:
    f.write(appendix)

# ───────────────────────────────────────────
# 5. 构造家庭史诗 Prompt
# ───────────────────────────────────────────
print("\n[5/6] 构造家庭史诗 prompt...")

system_prompt = """你是一位精通《易经》的家族史诗作者。你的任务是把系统同时跟踪五个家庭成员采集到的观测数据，编织成一段**有家族史诗感的多角色连续叙事**。

## 核心规则（Route-C 协议扩展版）

1. **五主角结构**：这不是独角戏，也不是双主角。这是五个灵魂在同一屋檐下的共生史。每个家庭成员都有自己的"体"（骨子里的性格底色）和"用"（当下的行为模式），同时他们之间还有复杂的互动网络。

2. **家庭作为有机体**：五个成员不是孤立的个体，而是一个"家庭有机体"的五个器官。当父亲卦变时，母亲会感知到；当长子锋芒毕露时，幼女会退缩。写出这种"牵一发而动全身"的家庭共振感。

3. **角色差异化**：五个角色必须有截然不同的"性格"，由各自的体协议决定：
   - 父亲：根基、秩序、承载
   - 母亲：渗透、滋养、交换
   - 长子：锋芒、开拓、刚健
   - 次子：变动、探索、好奇
   - 幼女：生机、变数、柔软

4. **家庭事件的张力来源**：
   - 先天对卦对：如父亲与长子形成对冲，意味着代际冲突
   - 同卦共鸣：如母亲与幼女同卦，意味着母女同心
   - 势能差：如某人势能1.9（即将爆发），某人势能0.1（平静），写出家庭内部的能量落差

5. **史诗弧线**：五个时间切片构成完整的家庭史诗：
   - T-2 日常稳态：五口人各自的日常，暗流已伏
   - T-1 暗流涌动：个别成员的变化开始影响家庭氛围
   - T0  家庭事件：核心冲突/变故爆发，牵一发而动全身
   - T+1 余波震荡：每个人都在事件中受伤或成长
   - T+2 新秩序：家庭重构了新的平衡，但已不再是原来的样子

6. **卦变仪式感**：任何成员的卦变都不是"换个心情"，而是内在结构的自我瓦解与重建。要有仪式感。

7. **强制映射标注**：叙事之后必须写"### 对应关系标注"，列出每个家庭成员的关键系统概念对应到叙事中的哪个元素。

## 叙事结构要求

### 连贯叙事（1200-1800字）
一段跨越五个时间切片的家庭史诗。要求：
- 五个角色都有鲜明的性格，且性格由"体"决定
- 家庭内部有真实的互动（对话、冲突、扶持、误解）
- 不要写成五个独立的个人传记，要写成"一个家庭的命运"
- 使用时间流逝感（季节、年份、时辰等）
- T0 事件是高潮，前后有明确的因果铺垫与余波

### 家庭对应关系标注
用表格明确标注：
| 时间 | 成员 | 体协议体现 | 用协议体现 | 家庭角色体现 | 相位/势能体现 |

### 叙事质量自检
1. 五个角色是否有各自独立的性格弧线？
2. 家庭事件是否体现了"牵一发而动全身"的共振感？
3. T0 事件是否有足够的张力与仪式感？
4. 是否同时写出了家庭的温暖与撕裂两极？
5. 新秩序（T+2）与旧秩序（T-2）是否有本质的不同？
"""

flip_detail = ""
if best_event["flip_count"] > 0:
    flip_detail = f"本次家庭事件中，共有 {best_event['flip_count']} 位成员经历了卦变。"

user_prompt = f"""以下是系统从易道动态世界引擎同时跟踪一个五口之家采集到的时间序列数据。

{flip_detail}
请你把五个时间切片编织成一段**家族史诗**——不是五个人的个人传记，而是一个家庭作为有机体的命运变迁。

要求：
1. 给每个家庭成员起一个有质感的中文名字（如父亲叫"沉岩"、母亲叫"润音"等），名字要符合其体的本质
2. 写出家庭内部的真实互动：冲突、扶持、误解、默契
3. 某个成员的变化必须影响到其他成员（牵一发而动全身）
4. T0 是家庭的核心变故/冲突/转折，要有仪式感
5. T+2 的新秩序必须与 T-2 的旧秩序有本质不同
6. 使用感官词汇丰富画面

---

{timeline_package}

---

{appendix}

---

请生成连贯叙事 + 家庭对应关系标注 + 叙事质量自检：
"""

with open("stage6_system_prompt.txt", "w", encoding="utf-8") as f:
    f.write(system_prompt)
with open("stage6_user_prompt.txt", "w", encoding="utf-8") as f:
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
    "temperature": 0.75,
    "max_tokens": 5000,
}

try:
    resp = requests.post(
        f"{API_BASE}/chat/completions",
        headers=headers,
        json=payload,
        timeout=180,
    )
    resp.raise_for_status()
    result = resp.json()
    llm_output = result["choices"][0]["message"]["content"]
    usage_info = result.get("usage", {})

    print(f"  API 成功 | 输入: {usage_info.get('prompt_tokens', '?')} | 输出: {usage_info.get('completion_tokens', '?')}")

    with open("stage6_llm_output.txt", "w", encoding="utf-8") as f:
        f.write(llm_output)
    print("  已保存: stage6_llm_output.txt")

except Exception as e:
    print(f"  API 失败: {e}")
    sys.exit(1)

# ───────────────────────────────────────────
# 7. 验证：家庭史诗质量
# ───────────────────────────────────────────
print("\n" + "=" * 60)
print("【家庭史诗叙事验证】")
print("=" * 60)

output = llm_output
checks = []

# 7.1 五个角色都在
for idx, name in enumerate(member_names):
    present = name in output or member_descs[idx].split(" — ")[0] in output
    checks.append((f"成员 '{name}' 在叙事中出现", present))

# 7.2 有家庭互动
family_words = ["父亲", "母亲", "长子", "次子", "幼女", "家", "家里", "家人", "父母", "兄弟", "兄妹", "姐妹", "争吵", "拥抱", "沉默", "对视", "默契"]
has_family = any(w in output for w in family_words)
checks.append(("有家庭互动氛围", has_family))

# 7.3 因果链
causal = ["因此", "所以", "因为", "于是", "导致", "源于", "终于"]
has_causal = any(w in output for w in causal)
checks.append(("有因果逻辑链", has_causal))

# 7.4 时间流逝
time_w = ["起初", "后来", "随后", "终于", "之前", "之后", "当", "那一刻", "年", "春", "秋", "冬", "夏"]
has_time = any(w in output for w in time_w)
checks.append(("有时间流逝感", has_time))

# 7.5 体的一致性
for idx in range(5):
    bp = family_slices[2]["members"][idx]["body_protocol"]
    checks.append((f"{member_names[idx]} 的体 '{bp}' 有体现", bp in output))

# 7.6 用的变化
for idx in range(5):
    un = family_slices[0]["members"][idx]["usage_name"]
    checks.append((f"{member_names[idx]} 的用 '{un}' 有体现", un in output))

# 7.7 卦变仪式感
ritual = ["宿命", "轰鸣", "自决", "强制", "降临", "产道", "不可逆转", "崩塌", "瓦解", "撕裂"]
has_ritual = any(w in output for w in ritual)
checks.append(("卦变/事件有仪式感", has_ritual))

# 7.8 两极
polar = ["温暖", "冰冷", "光明", "黑暗", "荣耀", "诅咒", "爱", "恨", "凝聚", "分裂"]
has_polar = sum(1 for w in polar if w in output) >= 2
checks.append(("两极并存", has_polar))

# 7.9 对应表
has_table = "对应关系" in output or "对应表" in output
checks.append(("有对应关系标注", has_table))

# 7.10 自检
has_check = "自检" in output or "因果链" in output or "一致性" in output
checks.append(("有质量自检", has_check))

# 7.11 感官
sensory = ["光", "暗", "声", "响", "静", "风", "火", "冷", "热", "味道", "颤抖", "震动", "笑", "泪"]
has_sensory = sum(1 for w in sensory if w in output) >= 3
checks.append(("有感官细节", has_sensory))

# 7.12 牵一发而动全身
resonance = ["影响", "波及", "牵连", "共鸣", "震荡", "感染", "传递", "蔓延", "整个家"]
has_resonance = any(w in output for w in resonance)
checks.append(("有家庭共振感（牵一发而动全身）", has_resonance))

all_pass = True
for desc, ok in checks:
    status = "PASS" if ok else "FAIL"
    if not ok:
        all_pass = False
    print(f"  [{status}] {desc}")

print()
if all_pass:
    print(">>> 家庭史诗叙事测试通过")
else:
    print(">>> 部分验证未通过")
print("=" * 60)

print("\n【LLM 生成的家庭史诗】\n")
print(output[:2000])
print("\n... [截断，完整内容见 stage6_llm_output.txt]")
