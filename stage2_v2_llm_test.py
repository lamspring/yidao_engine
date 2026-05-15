# -*- coding: utf-8 -*-
"""
阶段二 v2：剧情具象化测试
修正问题：要求 LLM 输出具体的事件/画面/剧情，而非抽象哲学散文
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


def _get_pure_hex(protocol_name):
    protocol_map = {
        "承载": 0, "激变": 9, "深渊": 18, "渗透": 27,
        "止界": 36, "显文明": 45, "交换": 54, "创序": 63,
    }
    return protocol_map.get(protocol_name, 0)


print("=" * 60)
print("【阶段二 v2】剧情具象化测试")
print("=" * 60)

# ───────────────────────────────────────────
# 1. 初始化世界并运行
# ───────────────────────────────────────────
print("\n[1/5] 初始化世界并运行 1000 tick...")
world = World(height=32, width=64)
cam = WorldCamera(world, y=16, x=32, scale="meso", intent="landscape")

for i in range(1000):
    world.tick()
    if (i + 1) % 200 == 0:
        print(f"  ...{i + 1} 息")

# 找异常点
anomalies = cam._observer.scan_anomalies(pot_ratio=0.85)
if anomalies:
    target_y, target_x, reason = anomalies[0]
    print(f"  发现异常点: ({target_y},{target_x}) -> {reason}")
    cam.move_to(target_y, target_x)
else:
    max_idx = np.unravel_index(np.argmax(world.potential), world.potential.shape)
    cam.move_to(max_idx[0], max_idx[1])
    print(f"  选择势能最高点: ({max_idx[0]},{max_idx[1]})")

# 再跑 200 tick，让变化发生
for i in range(200):
    world.tick()

print(f"\n当前 tick: {world.tick_count}, 观测位置: ({cam.y},{cam.x})")

# ───────────────────────────────────────────
# 2. 获取完整数据
# ───────────────────────────────────────────
print("\n[2/5] 获取体用分析...")
tracker = EntityTracker(world, "test_region", cam.y, cam.x, radius=4)
cam.track_entity("test_region", y=cam.y, x=cam.x, radius=4)

analyst = YaoAnalyst(cam)
body_usage = analyst.run_two_rounds(tracker, perspective="objective")

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

print(f"  体: {body['body_name']}({body['body_hex']}) | {body['body_protocol']} | {body['body_type']}")
print(f"  用: {usage['current_name']}({usage['current_hex']}) | {get_gua(usage['current_hex'])['protocol']}")
print(f"  关系: {relation['type']}")
print(f"  相位: {mean_phase:.3f} | 势能: {mean_pot:.3f}/{world.V_thresh:.3f} ({pot_stage['ratio_label']})")

# ───────────────────────────────────────────
# 3. 构造语义指令
# ───────────────────────────────────────────
print("\n[3/5] 构造语义指令...")

semantic_package = f"""【观测对象】{body['entity_id']} @ tick {world.tick_count}
【观测尺度】{packet['scale']} | 【观测意图】{packet['intent']}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【体】不易之本质
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
卦值: {body['body_hex']} | 卦名: {body['body_name']} | 协议: {body['body_protocol']}
体类型: {body['body_type']} (置信度: {body['body_confidence']:.3f})
体本质: {body['body_nature']}
长期主导: {body['long_term_dominant']} | 历史波动: {body['volatility']:.3f}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【用】当下之显化
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
卦值: {usage['current_hex']} | 卦名: {usage['current_name']} | 协议: {get_gua(usage['current_hex'])['protocol']}
结构语气: {usage['structural_tone']}
生命阶段: {usage['life_stage']} (相位: {mean_phase:.3f})
变化叙事: {usage['change_narrative']}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【势】临界状态
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
势能: {mean_pot:.3f} / 阈值 {world.V_thresh:.3f} (比例: {pot_stage['ratio']:.3f})
阶段标签: {pot_stage['ratio_label']}
阶段氛围: {pot_stage['atmosphere']}
警告: {pot_stage['warning']}

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

with open("stage2v2_semantic_package.txt", "w", encoding="utf-8") as f:
    f.write(semantic_package)

# ───────────────────────────────────────────
# 4. 构造 v2 Prompt —— 强调剧情具象化
# ───────────────────────────────────────────
print("\n[4/5] 构造剧情具象化 prompt...")

system_prompt_v2 = """你是一位精通《易经》的世界叙事者。你的任务不是写哲学散文，而是**把卦象翻译成一个具体的场景、一段正在发生的剧情、一幅有画面感的描述**。

## 核心定位
系统给你的是世界的"骨架"（卦象、相位、势能、关系）。你的任务是给骨架赋予"血肉"——让它变成人类能**看到、听到、感受到**的具体画面。

## 输出要求
你的输出必须是**一段剧情场景描写**，像小说中的一个片段。必须包含：

1. **具体的环境** —— 不是"深渊的栖居者"，而是"一座深不见底的水下洞穴，岩壁上布满发光的苔藓"
2. **正在行动的人物/力量** —— 不是"创序之力"，而是"一支身穿铁甲的工程队正在岩壁上开凿通道"
3. **正在发生的具体事件** —— 不是"结构剧烈重构"，而是"洞穴深处突然传来塌方声，碎石滚落，但工程队没有撤退"
4. **感官细节** —— 视觉（光线、颜色、形状）、听觉（声音、回声、沉默）、动态（运动、震颤、静止）、氛围（温度、气味、情绪）

## 结构语法（必须遵循，但藏在画面背后）

### 相位 -> 生命阶段
- 0.00-0.15 初爻潜藏：事情刚萌芽，尚未破土，压抑感
- 0.15-0.30 二爻萌生：露头、试探、微光初现
- 0.30-0.50 三爻成长：上升、扩展、渐盛、积累
- 0.50-0.70 四爻盛壮：鼎盛、辉煌、主宰、充盈
- 0.70-0.85 五爻持守：守成、高处不胜寒、鼎盛中的隐忧
- 0.85-1.00 上爻过极：将反、临界、盛极而衰、最后的辉煌

### 势能比例 -> 临界感
- <0.3 平静：安宁，暗埋伏笔，表面无事
- 0.3-0.7 积蓄：不安，隐忧弥漫，裂纹在不可见处蔓延
- 0.7-1.0 临界：锋利，一触即发，空气变重
- >1.0 爆发：不可逆，旧死新生，旧结构正在瓦解

### 体用关系 -> 叙事张力
- 同体：本色未改，表里如一
- 相生：顺势而为，如鱼得水，外部滋养内部
- 被生：滋养外显，由内而发，内在驱动外在
- 相克：逆势而为，内外交战，外在压迫内在
- 被克：压抑外显，内紧外松，内在压制外在
- 对冲：表里截然，张力极大，荣耀与诅咒并存
- 杂：纠缠不清，有待观察

## 叙事原则
1. **画面优先**：读者读完你的文字，脑海中应该有一幅清晰的画面
2. **体用分离**：先说"这个地方骨子里是什么"（长期本质），再说"此刻正在发生什么"（当下事件）
3. **张力优先**：不要只写好话。对冲要写出两极撕扯，相克要写出内外交战
4. **相位铁律**：>0.85 必写"将反"，<0.15 必写"潜藏"
5. **势能铁律**：>1.0 必写"已变"，0.7-1.0 必写"临界"
6. **禁止硬编码**：不要"坎就是水"，用系统给的精确概念（如"深渊栖居者"）
7. **禁止抽象堆砌**：不要连续使用"本质""显化""张力"等元概念，用具体的人事物替代
"""

user_prompt_v2 = f"""以下是系统从易道动态世界引擎采集到的观测数据。请你把它翻译成**一段具体的剧情场景**，像小说中的一个片段。

要求：
1. 输出是一段完整的场景描写，有画面感，有人物/力量在行动，有具体事件在发生
2. 使用【象】现象映射中的物类映射和感官词汇来具象化
3. 体用关系必须体现在剧情中：体的本质是这个地方的"底色"，用的显化是"当下正在上演的事件"
4. 相位的生命阶段要体现在事件的时间感上（刚萌芽？鼎盛？将反？）
5. 势能的临界感要体现在氛围上（平静下的暗流？一触即发的紧张？）
6. 不要罗列数据，不要解释概念，直接写场景
7. 结尾用一句话暗示未来走向

---

{semantic_package}

---

请生成场景描写（300-600字）：
"""

with open("stage2v2_system_prompt.txt", "w", encoding="utf-8") as f:
    f.write(system_prompt_v2)
with open("stage2v2_user_prompt.txt", "w", encoding="utf-8") as f:
    f.write(user_prompt_v2)

# ───────────────────────────────────────────
# 5. 调用 LLM
# ───────────────────────────────────────────
print("\n[5/5] 调用 LLM API...")

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
}

payload = {
    "model": MODEL,
    "messages": [
        {"role": "system", "content": system_prompt_v2},
        {"role": "user", "content": user_prompt_v2},
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

    with open("stage2v2_llm_output.txt", "w", encoding="utf-8") as f:
        f.write(llm_output)
    print("  已保存: stage2v2_llm_output.txt")

except Exception as e:
    print(f"  API 失败: {e}")
    sys.exit(1)

# ───────────────────────────────────────────
# 6. 验证：剧情具象化质量
# ───────────────────────────────────────────
print("\n" + "=" * 60)
print("【剧情具象化验证】")
print("=" * 60)

output = llm_output

# 剧情具象化检查
checks = []

# 是否有具体环境描写（地点、空间）
has_setting = any(w in output for w in [
    "山", "水", "洞", "城", "墙", "河", "林", "谷", "原", "海", "岛", "塔", "庙",
    "地面", "天空", "岩壁", "街道", "森林", "洞穴", "废墟", "宫殿", "边境"
])
checks.append(("有具体环境/地点描写", has_setting))

# 是否有具体人物/行动者在行动
has_actor = any(w in output for w in [
    "人", "者", "士", "队", "军", "民", "师", "徒", "客", "兵", "工", "匠",
    "行走", "站立", "奔跑", "挖掘", "建造", "燃烧", "呼喊", "沉默", "等待",
    "他们", "众人", "一人", "那人", "队伍", "身影"
])
checks.append(("有具体人物/行动者在行动", has_actor))

# 是否有具体事件（正在发生什么）
has_event = any(w in output for w in [
    "突然", "正在", "忽然", "与此同时", "此刻", "这时", "随即", "紧接着",
    "传来", "落下", "升起", "崩塌", "点燃", "裂开", "涌入", "退去",
    "仪式", "战斗", "建造", "迁徙", "发现", "交易", "会谈", "封锁"
])
checks.append(("有具体事件在发生", has_event))

# 是否有感官细节
has_sensory = any(w in output for w in [
    "光", "暗", "亮", "黑", "红", "白", "金", "蓝", "绿",
    "声", "音", "响", "静", "嗡", "鸣", "吼", "滴",
    "风", "雨", "雪", "雾", "尘", "烟", "火", "水",
    "冷", "热", "寒", "暖", "湿", "干", "腥", "香"
])
checks.append(("有感官细节（视觉/听觉/触觉/嗅觉）", has_sensory))

# 是否仍然提及体的本质概念（保留结构翻译）
body_nature_core = body['body_nature'].split("。")[0]
has_body = any(kw in output for kw in body_nature_core.split("。")[0].split("，")[:3])
checks.append(("保留了体的本质概念", has_body or body['body_protocol'] in output))

# 是否提及用的事件
has_usage = usage['current_name'] in output or get_gua(usage['current_hex'])['protocol'] in output
checks.append(("保留了用的显化概念", has_usage))

# 是否有张力/冲突/转折
has_conflict = any(w in output for w in ["但", "然而", "却", "而", "尽管", "虽然", "相反"])
checks.append(("有叙事张力/转折", has_conflict))

# 结尾是否有未来暗示
has_foreshadow = any(w in output[-100:] for w in ["未来", "终将", "或将", "不久之后", "明日", "下一刻", " soon"])
checks.append(("结尾有未来走向暗示", has_foreshadow))

# 抽象概念堆砌检查（负面指标）
abstract_words = ["本质", "显化", "张力", "结构", "态势", "场域", "维度", "范式"]
abstract_count = sum(output.count(w) for w in abstract_words)
checks.append((f"抽象元概念密度低（当前 {abstract_count} 个）", abstract_count <= 5))

all_pass = True
for desc, ok in checks:
    status = "PASS" if ok else "FAIL"
    if not ok:
        all_pass = False
    print(f"  [{status}] {desc}")

print()
if all_pass:
    print(">>> 剧情具象化测试通过")
else:
    print(">>> 部分验证项未通过，需改进")
print("=" * 60)

print("\n【LLM 生成的剧情场景】\n")
print(output)
