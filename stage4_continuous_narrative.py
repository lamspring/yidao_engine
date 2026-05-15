# -*- coding: utf-8 -*-
"""
阶段四：连续观测 + 叙事连贯性测试
追踪一个实体经历完整生命周期，验证 LLM 能否生成跨时间的连贯叙事
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

    # 区域统计
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

    # 单点精确数据（焦点中心）
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


print("=" * 60)
print("【阶段四】连续观测 + 叙事连贯性测试")
print("=" * 60)

# ───────────────────────────────────────────
# 1. 初始化世界并长期运行
# ───────────────────────────────────────────
print("\n[1/6] 初始化世界并运行 3000 tick...")
world = World(height=32, width=64)
cam = WorldCamera(world, y=16, x=32, scale="meso", intent="faction")
tracker = EntityTracker(world, "watched_entity", 16, 32, radius=4)
analyst = YaoAnalyst(cam)
engine = EventEngine(world, analyst)

# 记录所有卦变事件
flip_events = []
all_snapshots = []

for i in range(3000):
    world.tick()
    tracker._update()

    # 检测卦变
    if len(tracker.hex_history) >= 2:
        prev = tracker.hex_history[-2]
        curr = tracker.hex_history[-1]
        if prev != curr:
            flip_events.append({
                "tick": world.tick_count,
                "pre_hex": prev,
                "post_hex": curr,
                "pre_name": get_gua(prev)["name"],
                "post_name": get_gua(curr)["name"],
            })

    # 每 100 tick 保存一个快照
    if (i + 1) % 100 == 0:
        snap = capture_snapshot(world, cam, tracker, analyst, f"T{i+1}")
        all_snapshots.append(snap)

    if (i + 1) % 500 == 0:
        print(f"  ...{i + 1} 息，已记录 {len(flip_events)} 次卦变")

print(f"\n运行完成：共 {len(flip_events)} 次卦变")
for ev in flip_events[:10]:
    print(f"  tick {ev['tick']}: {ev['pre_name']}({ev['pre_hex']}) -> {ev['post_name']}({ev['post_hex']})")
if len(flip_events) > 10:
    print(f"  ... 共 {len(flip_events)} 次")

# ───────────────────────────────────────────
# 2. 寻找最有故事性的连续片段
# ───────────────────────────────────────────
print("\n[2/6] 寻找最有故事性的连续片段...")

# 策略：找到一个完整的卦变周期，包含稳态→临界→卦变→新稳态
# 选择包含最多戏剧性的 5 个连续时间点

best_story = None
best_score = -1

# 遍历所有卦变，寻找前后都有足够稳态的
for idx, flip in enumerate(flip_events):
    flip_tick = flip["tick"]
    pre_snap = None
    critical_snap = None
    post_snap = None
    stable_snap = None

    for snap in all_snapshots:
        tick = snap["tick"]
        # 卦变前 50-150 tick 的稳态
        if flip_tick - 150 <= tick <= flip_tick - 50:
            if pre_snap is None or abs(tick - (flip_tick - 100)) < abs(pre_snap["tick"] - (flip_tick - 100)):
                pre_snap = snap
        # 卦变前 10-40 tick 的临界态
        if flip_tick - 40 <= tick <= flip_tick - 10:
            if critical_snap is None or snap["center_pot"] > critical_snap["center_pot"]:
                critical_snap = snap
        # 卦变后 10-40 tick 的新态初现
        if flip_tick + 10 <= tick <= flip_tick + 40:
            if post_snap is None or abs(tick - (flip_tick + 20)) < abs(post_snap["tick"] - (flip_tick + 20)):
                post_snap = snap
        # 卦变后 100-200 tick 的新稳态
        if flip_tick + 100 <= tick <= flip_tick + 200:
            if stable_snap is None or abs(tick - (flip_tick + 150)) < abs(stable_snap["tick"] - (flip_tick + 150)):
                stable_snap = snap

    if all([pre_snap, critical_snap, post_snap, stable_snap]):
        # 评分：势能差距越大、关系变化越剧烈，分数越高
        score = 0
        # 卦变前后的卦名差异
        if pre_snap["center_gua_name"] != post_snap["center_gua_name"]:
            score += 1
        # 临界态的势能
        if critical_snap:
            score += critical_snap["center_pot"] * 2
        # 关系变化
        if pre_snap["relation"]["type"] != post_snap["relation"]["type"]:
            score += 2

        if score > best_score:
            best_score = score
            best_story = {
                "flip": flip,
                "pre_snap": pre_snap,
                "critical_snap": critical_snap,
                "post_snap": post_snap,
                "stable_snap": stable_snap,
            }

if best_story is None:
    print("  未找到完整周期，使用最后几个可用快照...")
    # fallback：使用最后 4 个快照
    best_story = {
        "flip": flip_events[-1] if flip_events else {"tick": 3000, "pre_name": "?", "post_name": "?"},
        "pre_snap": all_snapshots[-4],
        "critical_snap": all_snapshots[-3],
        "post_snap": all_snapshots[-2],
        "stable_snap": all_snapshots[-1],
    }

story = best_story
flip = story["flip"]

print(f"\n选定故事片段：")
print(f"  卦变: tick {flip['tick']} | {flip['pre_name']} -> {flip['post_name']}")
print(f"  稳态前: tick {story['pre_snap']['tick']} | 体:{story['pre_snap']['body']['body_name']} | 用:{story['pre_snap']['usage']['current_name']} | 关系:{story['pre_snap']['relation']['type']}")
print(f"  临界前: tick {story['critical_snap']['tick']} | 相位:{story['critical_snap']['center_phase']:.2f} | 势能:{story['critical_snap']['center_pot']:.2f}")
print(f"  卦变后: tick {story['post_snap']['tick']} | 体:{story['post_snap']['body']['body_name']} | 用:{story['post_snap']['usage']['current_name']} | 关系:{story['post_snap']['relation']['type']}")
print(f"  新稳态: tick {story['stable_snap']['tick']} | 体:{story['stable_snap']['body']['body_name']} | 用:{story['stable_snap']['usage']['current_name']} | 关系:{story['stable_snap']['relation']['type']}")

# ───────────────────────────────────────────
# 3. 构造时间序列语义指令
# ───────────────────────────────────────────
print("\n[3/6] 构造时间序列语义指令...")


def format_snapshot(snap, label):
    return f"""【{label}】tick {snap['tick']}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
单点状态: {snap['center_gua_name']}({snap['center_gua']}) | {snap['center_protocol']} | 相位:{snap['center_phase']:.2f} | 势能:{snap['center_pot']:.2f} | 气象:{snap['center_trend']:+.2f}

体: {snap['body']['body_name']}({snap['body']['body_hex']}) | {snap['body']['body_protocol']} | 类型:{snap['body']['body_type']}
体本质: {snap['body']['body_nature'].split('。')[0]}。

用: {snap['usage']['current_name']}({snap['usage']['current_hex']}) | {get_gua(snap['usage']['current_hex'])['protocol']}
结构语气: {snap['usage']['structural_tone']}
生命阶段: {snap['usage']['life_stage']}
变化叙事: {snap['usage']['change_narrative']}

关系: {snap['relation']['type']} | {snap['relation']['description']}

势能阶段: {snap['pot_stage']['ratio_label']} (比例:{snap['pot_stage']['ratio']:.2f})
阶段氛围: {snap['pot_stage']['atmosphere']}

感官: 视觉-{', '.join(snap['sensory']['visual'])} | 听觉-{', '.join(snap['sensory']['sound'])} | 动态-{', '.join(snap['sensory']['motion'])} | 氛围-{', '.join(snap['sensory']['mood'])}
"""

timeline_package = f"""【观测对象】{tracker.entity_id}
【卦变事件】tick {flip['tick']}: {flip['pre_name']}({flip['pre_hex']}) -> {flip['post_name']}({flip['post_hex']})

以下是摄像机在卦变前后连续跟踪该实体采集到的 4 个时间切片：

{format_snapshot(story['pre_snap'], 'T-1 稳态期')}

{format_snapshot(story['critical_snap'], 'T0 临界期')}

{format_snapshot(story['post_snap'], 'T+1 卦变后')}

{format_snapshot(story['stable_snap'], 'T+2 新稳态')}
"""

with open("stage4_timeline_package.txt", "w", encoding="utf-8") as f:
    f.write(timeline_package)

# ───────────────────────────────────────────
# 4. 构造路线C的连续叙事 Prompt
# ───────────────────────────────────────────
print("\n[4/6] 构造连续叙事 prompt...")

system_prompt = """你是一位精通《易经》的世界编年史作者。你的任务是把系统在不同时间采集到的观测数据，编织成一段**有因果、有节奏、有张力的连续叙事**。

## 核心规则

1. **时间连续性**：叙事必须体现时间的流逝。不是四个孤立的画面，而是一个连续的过程：伏笔 → 酝酿 → 爆发 → 后果。
2. **因果关系**：后面的变化必须能从前面的状态中找到原因。读者读完应该觉得"前面的铺垫导致了后面的爆发"。
3. **体的不变与用的变**：体的本质（骨子里的东西）在长期内保持相对稳定，但用的显化（当下发生的事）在随时间剧烈变化。叙事要体现这种"不变的底色 vs 多变的表象"的张力。
4. **卦变的仪式感**：卦变不是普通的改变，而是"穷极则变"——旧结构在无法承受自身重量后的自我瓦解与新结构的强制降临。卦变那一刻应该有仪式感、宿命感。
5. **相位推进的节奏感**：从初爻到上爻，叙事节奏应该从"潜藏压抑"逐渐加速到"盛壮辉煌"，最后以"将反/崩解"告终。

## 叙事结构要求

你必须按以下结构输出：

### 连贯叙事（600-1000字）
一段跨越四个时间切片的连续故事。要求：
- 有明确的时间感（从T-1到T+2的流逝感）
- 有伏笔→酝酿→爆发→后果的因果链
- 体的本质作为贯穿始终的底色
- 用的显化作为随时间变化的事件层
- 卦变时刻要有仪式感/宿命感

### 时间切片对应表
在叙事之后，用表格明确标注每个时间切片在剧情中的体现：
| 时间 | 剧情中的场景 | 体协议体现 | 用协议体现 | 关系体现 | 相位/势能体现 |

### 叙事质量自检
回答以下问题：
1. 叙事中是否有"伏笔→爆发→后果"的因果链？
2. 体的本质是否在四个切片中保持了一致性？
3. 卦变时刻是否有仪式感/宿命感？
4. 是否同时写出了荣耀与诅咒/光明与黑暗的两极？
"""

user_prompt = f"""以下是系统从易道动态世界引擎连续跟踪一个实体采集到的时间序列数据。这个实体在 tick {flip['tick']} 经历了一次卦变：{flip['pre_name']} -> {flip['post_name']}。

请你把四个时间切片编织成一段**连续的、有因果的、有节奏感**的叙事，像一部短篇史诗或历史编年。

要求：
1. 不要写成四个孤立的场景描写，而要写成**一段连续的故事**
2. 读者应该能感受到时间的流逝和事件的因果
3. 体的本质作为"底色"贯穿始终，用的显化作为"事件层"随时间变化
4. 卦变时刻要有**仪式感**——不是普通的改变，而是旧结构的自我瓦解与新结构的强制降临
5. 使用【象】中的感官词汇来丰富画面

---

{timeline_package}

---

请生成连贯叙事 + 时间切片对应表 + 叙事质量自检：
"""

with open("stage4_system_prompt.txt", "w", encoding="utf-8") as f:
    f.write(system_prompt)
with open("stage4_user_prompt.txt", "w", encoding="utf-8") as f:
    f.write(user_prompt)

# ───────────────────────────────────────────
# 5. 调用 LLM
# ───────────────────────────────────────────
print("\n[5/6] 调用 LLM API...")

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
        timeout=60,
    )
    resp.raise_for_status()
    result = resp.json()
    llm_output = result["choices"][0]["message"]["content"]
    usage_info = result.get("usage", {})

    print(f"  API 成功 | 输入: {usage_info.get('prompt_tokens', '?')} | 输出: {usage_info.get('completion_tokens', '?')}")

    with open("stage4_llm_output.txt", "w", encoding="utf-8") as f:
        f.write(llm_output)
    print("  已保存: stage4_llm_output.txt")

except Exception as e:
    print(f"  API 失败: {e}")
    sys.exit(1)

# ───────────────────────────────────────────
# 6. 验证：叙事连贯性
# ───────────────────────────────────────────
print("\n" + "=" * 60)
print("【叙事连贯性验证】")
print("=" * 60)

output = llm_output

checks = []

# 6.1 时间感
has_time_flow = any(w in output for w in ["起初", "后来", "随后", "终于", "那一刻", "当", "之前", "之后", "T-1", "T0", "T+1", "T+2", "时间", "流逝"])
checks.append(("有明确的时间流逝感", has_time_flow))

# 6.2 因果链
causal_words = ["因此", "所以", "因为", "于是", "导致", "酝酿", "积累", "终于", "引爆", "崩解", "瓦解"]
has_causality = any(w in output for w in causal_words)
checks.append(("有因果逻辑链", has_causality))

# 6.3 伏笔→爆发→后果
has_setup = any(w in output for w in ["伏笔", "潜藏", "压抑", "积蓄", "酝酿", "暗流", "沉默", "潜伏"])
has_climax = any(w in output for w in ["爆发", "崩解", "瓦解", "撕裂", "裂变", "点燃", "引爆", "那一刻"])
has_aftermath = any(w in output for w in ["后果", "余波", "残骸", "废墟", "新生", "之后", "从此", "留下"])
checks.append(("有伏笔铺垫", has_setup))
checks.append(("有爆发/高潮", has_climax))
checks.append(("有后果/余波", has_aftermath))

# 6.4 体的一致性（体的本质在多个时间点中被重复提及）
body_protocol = story['pre_snap']['body']['body_protocol']
has_body_consistency = body_protocol in output
checks.append((f"体的本质 '{body_protocol}' 贯穿叙事", has_body_consistency))

# 6.5 用的变化（卦变前后用的不同被体现）
pre_usage = story['pre_snap']['usage']['current_name']
post_usage = story['post_snap']['usage']['current_name']
has_usage_change = pre_usage in output and post_usage in output
checks.append((f"用的变化 '{pre_usage}'->'{post_usage}' 被体现", has_usage_change))

# 6.6 卦变仪式感
ritual_words = ["仪式", "宿命", "必然", "不可阻挡", "强制", "降临", "那一刻", "决定性", "不可逆转", "旧死新生"]
has_ritual = any(w in output for w in ritual_words)
checks.append(("卦变时刻有仪式感/宿命感", has_ritual))

# 6.7 两极并存
polar_words = ["光明", "黑暗", "荣耀", "诅咒", "辉煌", "腐朽", "秩序", "混沌", "温暖", "冰冷"]
has_polarity = sum(1 for w in polar_words if w in output) >= 2
checks.append(("同时写出两极（光明/黑暗等）", has_polarity))

# 6.8 有对应表
has_table = "|" in output or "时间切片" in output or "对应表" in output
checks.append(("有时间切片对应表", has_table))

# 6.9 有自检
has_self_check = "自检" in output or "伏笔→爆发→后果" in output or "一致性" in output
checks.append(("有叙事质量自检", has_self_check))

# 6.10 具象化质量
has_sensory = any(w in output for w in ["光", "暗", "声", "响", "静", "风", "火", "冷", "热", "味道", "气味", "颤抖", "震动"])
checks.append(("有感官细节", has_sensory))

all_pass = True
for desc, ok in checks:
    status = "PASS" if ok else "FAIL"
    if not ok:
        all_pass = False
    print(f"  [{status}] {desc}")

print()
if all_pass:
    print(">>> 连续叙事测试通过")
else:
    print(">>> 部分验证未通过")
print("=" * 60)

print("\n【LLM 生成的连续叙事】\n")
print(output)
