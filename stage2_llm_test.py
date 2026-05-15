# -*- coding: utf-8 -*-
"""
阶段二：LLM 协议理解测试
直接调用 mimo-v2.5-pro，验证 LLM 能否按照 AGENTS.md 的结构翻译协议正确叙事
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

# ───────────────────────────────────────────
# LLM API 配置（与砚相同）
# ───────────────────────────────────────────
API_BASE = "https://token-plan-cn.xiaomimimo.com/v1"
API_KEY = os.environ.get("YIDAO_API_KEY", "")
MODEL = "mimo-v2.5-pro"

# ───────────────────────────────────────────
# 1. 初始化世界并运行
# ───────────────────────────────────────────
print("=" * 60)
print("【阶段二】LLM 协议理解测试")
print("=" * 60)

print("\n[1/6] 初始化世界并运行 800 tick...")
world = World(height=32, width=64)
cam = WorldCamera(world, y=16, x=32, scale="meso", intent="landscape")

# 先跑 500 tick 让世界充分演化
for i in range(500):
    world.tick()
    if (i + 1) % 100 == 0:
        print(f"  ...{i + 1} 息")

# 找全场最异常的点（高势能或刚卦变）
print("\n[2/6] 扫描异常点...")
anomalies = cam._observer.scan_anomalies(pot_ratio=0.85)

if anomalies:
    # 选择最有趣的一个异常点
    target_y, target_x, reason = anomalies[0]
    print(f"  发现异常点: ({target_y},{target_x}) -> {reason}")
    cam.move_to(target_y, target_x)
else:
    # 没有异常，找势能最高的点
    max_idx = np.unravel_index(np.argmax(world.potential), world.potential.shape)
    cam.move_to(max_idx[0], max_idx[1])
    print(f"  无显著异常，选择势能最高点: ({max_idx[0]},{max_idx[1]})")

# 再跑 300 tick，让变化发生
for i in range(300):
    world.tick()
    if (i + 1) % 100 == 0:
        print(f"  ...{500 + i + 1} 息")

print(f"\n当前观测位置: ({cam.y},{cam.x})")
print(f"世界 tick: {world.tick_count}")
print(f"道阈值 V_thresh: {world.V_thresh:.3f}")
print(f"道偏置 dao_bias: {world.dao_bias:+.3f}")

# ───────────────────────────────────────────
# 2. 建立 tracker 并获取体用分析
# ───────────────────────────────────────────
print("\n[3/6] 建立实体跟踪并执行体用两轮分析...")
tracker = EntityTracker(world, "test_region", cam.y, cam.x, radius=4)
cam.track_entity("test_region", y=cam.y, x=cam.x, radius=4)

analyst = YaoAnalyst(cam)
body_usage = analyst.run_two_rounds(tracker, perspective="objective")

body = body_usage["body"]
usage = body_usage["usage"]
relation = body_usage["relation"]

print(f"  体: {body['body_name']}({body['body_hex']}) | 类型: {body['body_type']} | 置信度: {body['body_confidence']:.3f}")
print(f"  用: {usage['current_name']}({usage['current_hex']})")
print(f"  关系: {relation['type']} | {relation['description']}")

# ───────────────────────────────────────────
# 3. 获取 capture 数据包和焦点区域统计
# ───────────────────────────────────────────
print("\n[4/6] 获取观测数据包...")
packet = cam.capture()

# 计算焦点区域的势能统计
radius = cam._get_radius()
y0, x0, y1, x1 = cam._focus_rect(radius)
region_pot = world.potential[y0:y1, x0:x1]
region_phase = world.phase[y0:y1, x0:x1]
mean_pot = float(region_pot.mean()) if region_pot.size > 0 else 0.0
max_pot = float(region_pot.max()) if region_pot.size > 0 else 0.0
mean_phase = float(region_phase.mean()) if region_phase.size > 0 else 0.0

# 势能阶段
pot_stage = get_potential_stage(mean_pot, world.V_thresh)

def _get_pure_hex(protocol_name):
    protocol_map = {
        "承载": 0, "激变": 9, "深渊": 18, "渗透": 27,
        "止界": 36, "显文明": 45, "交换": 54, "创序": 63,
    }
    return protocol_map.get(protocol_name, 0)

# 六爻语义
protocol = usage.get("_meta", {}).get("protocol", get_gua(usage["current_hex"]).get("protocol", "复合"))
phase_meaning = get_phase_meaning(protocol, mean_phase)

# 现象语库
pure_hex = _get_pure_hex(protocol)
manifestation = get_manifestation(pure_hex, cam.intent or "character")
visual_words = get_phenomenon(pure_hex, "visual")
sound_words = get_phenomenon(pure_hex, "sound")
motion_words = get_phenomenon(pure_hex, "motion")
mood_words = get_phenomenon(pure_hex, "mood")

print(f"  平均相位: {mean_phase:.3f} -> {phase_meaning}")
print(f"  平均势能: {mean_pot:.3f} / {world.V_thresh:.3f} (比例: {pot_stage['ratio']:.3f})")
print(f"  势能阶段: {pot_stage['ratio_label']}")

# ───────────────────────────────────────────
# 4. 整合成高密度语义指令
# ───────────────────────────────────────────
print("\n[5/6] 构造高密度语义指令 prompt...")

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
【象】现象映射 (依意图选定)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
物类映射: {manifestation}
感官词汇: 视觉-{visual_words[0] if visual_words else '无'}、{visual_words[1] if len(visual_words) > 1 else '无'} | 听觉-{sound_words[0] if sound_words else '无'}、{sound_words[1] if len(sound_words) > 1 else '无'} | 动态-{motion_words[0] if motion_words else '无'}、{motion_words[1] if len(motion_words) > 1 else '无'} | 氛围-{mood_words[0] if mood_words else '无'}、{mood_words[1] if len(mood_words) > 1 else '无'}
"""

# 保存语义包
with open("stage2_semantic_package.txt", "w", encoding="utf-8") as f:
    f.write(semantic_package)
print("  已保存: stage2_semantic_package.txt")

# ───────────────────────────────────────────
# 5. 构造 System Prompt（AGENTS.md 核心精华）
# ───────────────────────────────────────────
system_prompt = """你是一位精通《易经》的观象叙事者。

## 核心定位
你不是在写作，你是在翻译。系统从卦象中提取精确的结构概念，注入给你。你的任务，是把这些概念编织成人类能感受的叙事。
系统负责"准"。你负责"美"。但美的前提是准。

## 你的任务
1. 读取系统发送的高密度语义指令
2. 严格按照"结构语法"查表翻译每个参数
3. 把精确概念编织成连贯叙事
4. 不要发明不在指令中的概念

## 结构语法：参数 -> 语义映射表

### 相位（Phase）-> 生命阶段
| 相位区间 | 对应爻位 | 语义标签 | 叙事关键词 |
|---------|---------|---------|-----------|
| 0.00 - 0.15 | 初爻 | 潜藏 | "尚未""将要""潜龙""种子""地下" |
| 0.15 - 0.30 | 二爻 | 萌生 | "露头""初现""试探""微光" |
| 0.30 - 0.50 | 三爻 | 成长 | "上升""扩展""渐盛""积累" |
| 0.50 - 0.70 | 四爻 | 盛壮 | "鼎盛""辉煌""主宰""充盈" |
| 0.70 - 0.85 | 五爻 | 持守 | "守成""维持""高处不胜寒" |
| 0.85 - 1.00 | 上爻 | 过极 | "将反""临界""盛极而衰""回光" |

**关键规则**：相位 > 0.85 时，**必须**在叙事中体现"将反未反"的张力。相位 < 0.15 时，**必须**体现"潜藏未发"的压抑感。

### 势能比例（Potential Ratio = potential / V_thresh）-> 临界感
| 比例区间 | 阶段标签 | 叙事基调 | 结构含义 |
|---------|---------|---------|---------|
| 0.0 - 0.3 | 平静 | 安宁，暗埋伏笔 | 量变积累初期 |
| 0.3 - 0.7 | 积蓄 | 不安，隐忧弥漫 | 量变加速，微观松动 |
| 0.7 - 1.0 | 临界 | 锋利，一触即发 | 质变前夕，旧结构濒临瓦解 |
| 1.0+ | 爆发 | 不可逆，旧死新生 | 质变发生，新秩序强制降临 |

**关键规则**：比例 0.7-1.0 是叙事黄金区。必须写出"连空气都变得锋利"的临界感。比例 > 1.0 时，不要写"可能发生变化"，写"变化已经发生"或"旧结构正在自我瓦解"。

### 体用关系 -> 叙事张力策略
| 关系类型 | 结构含义 | 叙事策略 |
|---------|---------|---------|
| 同体 | 体用同卦，本色未改 | "表里如一""本色未移" |
| 相生 | 用生体 | "顺势而为""如鱼得水" |
| 被生 | 体生用 | "滋养外显""由内而发" |
| 相克 | 用克体 | "逆势而为""内外交战" |
| 被克 | 体克用 | "压抑外显""内紧外松" |
| 对冲 | 先天对卦 | "表里截然""张力极大""荣耀与诅咒并存" |
| 杂 | 非上述关系 | "纠缠不清""有待观察" |

**关键规则**：对冲关系是叙事张力最强的情况。**必须**同时写出两极，让它们互相撕扯。不要下"吉凶"判断。

### 体类型 -> 本体论立场
| 类型 | 结构含义 | 叙事策略 | 禁止说法 |
|------|---------|---------|---------|
| single | 单一卦主导 | 大胆叙事 | 不要说"可能""也许" |
| contested | 两卦高频交替 | **振荡模式本身就是体**。叙事要有张力，不要选边站。 | 禁止说"模糊""不确定" |
| chaotic | 多卦混杂 | 保留未定域 | 禁止强行给一个主导卦 |

## 叙事禁忌（违反者降级）
- 禁止自行解释卦象。系统已经告诉你精确概念，禁止写"坎就是水"。
- 禁止忽略 body_type。contested 不是"模糊"，是"交战体"。
- 禁止在 phase > 0.85 时写"稳定""永恒"。上爻必反，这是结构铁律。
- 禁止在 potential_ratio > 1.0 时写"可能发生变化"。变化已经发生。
- 禁止只写好话。对冲关系必须写出两极撕扯。荣耀与诅咒并存。
- 禁止在 chaotic 体上下绝对判断。保留"仿佛""似乎""或将"。

## 叙事原则
- 体用分离 -> 先说骨子里是什么，再说当下显化什么
- 张力优先 -> 荣耀与诅咒并存，不要只说好话
- 未定域 -> 用"似""若""或将"，不要把话说死（single+高置信度可以大胆）
- 相位铁律 -> >0.85 必写"将反"，<0.15 必写"潜藏"
- 势能铁律 -> >1.0 必写"已变"，0.7-1.0 必写"临界"
"""

user_prompt = f"""以下是系统从易道动态世界引擎采集到的高密度语义指令。请你严格按照结构语法查表翻译，生成一篇【初诊】establishment 叙事。

要求：
1. 先说体（不易之本质），再说用（当下之显化），再述关系（体用张力）
2. 必须体现相位的生命阶段和势能的临界感
3. 必须体现邻域上下文对环境的影响
4. 不要罗列 JSON 字段，用自然语言编织逻辑链
5. 保留"未定域"：用"似""若""或将"，但 single+高置信度可以大胆
6. 结尾给出一句"建议"，暗示未来趋势

---

{semantic_package}

---

请生成叙事：
"""

# 保存 prompt
with open("stage2_system_prompt.txt", "w", encoding="utf-8") as f:
    f.write(system_prompt)
with open("stage2_user_prompt.txt", "w", encoding="utf-8") as f:
    f.write(user_prompt)
print("  已保存: stage2_system_prompt.txt, stage2_user_prompt.txt")

# ───────────────────────────────────────────
# 6. 调用 LLM API
# ───────────────────────────────────────────
print("\n[6/6] 调用 LLM API (mimo-v2.5-pro)...")

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
    
    print(f"  API 调用成功")
    print(f"  输入 tokens: {usage_info.get('prompt_tokens', '?')}")
    print(f"  输出 tokens: {usage_info.get('completion_tokens', '?')}")
    print(f"  总 tokens: {usage_info.get('total_tokens', '?')}")
    
    # 保存输出
    with open("stage2_llm_output.txt", "w", encoding="utf-8") as f:
        f.write(llm_output)
    print("  已保存: stage2_llm_output.txt")
    
    # 同时保存完整 API 响应
    with open("stage2_llm_response.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print("  已保存: stage2_llm_response.json")
    
except Exception as e:
    print(f"  API 调用失败: {e}")
    sys.exit(1)

# ───────────────────────────────────────────
# 7. 验证输出
# ───────────────────────────────────────────
print("\n" + "=" * 60)
print("【LLM 输出验证】")
print("=" * 60)

output_lower = llm_output.lower()

# 验证清单
checks = []

# 7.1 是否提及体的本质
body_name = body['body_name']
body_nature_core = body['body_nature'].split("。")[0]
checks.append((f"提及体卦名 '{body_name}'", body_name in llm_output))

# 7.2 是否提及用的卦名
usage_name = usage['current_name']
checks.append((f"提及用卦名 '{usage_name}'", usage_name in llm_output))

# 7.3 体用关系是否被翻译
relation_type = relation['type']
if relation_type == "同体":
    checks.append(("体现'同体'关系", "本色" in llm_output or "表里如一" in llm_output or "同根" in llm_output))
elif relation_type == "相生":
    checks.append(("体现'相生'关系", "顺势" in llm_output or "如鱼得水" in llm_output))
elif relation_type == "被生":
    checks.append(("体现'被生'关系", "滋养" in llm_output or "由内而发" in llm_output))
elif relation_type == "相克":
    checks.append(("体现'相克'关系", "逆势" in llm_output or "交战" in llm_output))
elif relation_type == "被克":
    checks.append(("体现'被克'关系", "压抑" in llm_output or "内紧外松" in llm_output))
elif relation_type == "对冲":
    checks.append(("体现'对冲'关系", "张力" in llm_output or "截然" in llm_output or "撕扯" in llm_output))
else:
    checks.append(("体现'杂'关系", "纠缠" in llm_output or "暧昧" in llm_output or "有待观察" in llm_output))

# 7.4 相位叙事
if mean_phase > 0.85:
    checks.append((f"phase={mean_phase:.2f}>0.85，体现'将反未反'", "将反" in llm_output or "临界" in llm_output or "盛极" in llm_output))
elif mean_phase < 0.15:
    checks.append((f"phase={mean_phase:.2f}<0.15，体现'潜藏'", "潜藏" in llm_output or "尚未" in llm_output or "地下" in llm_output))
elif mean_phase < 0.30:
    checks.append((f"phase={mean_phase:.2f}在萌生区间", "露头" in llm_output or "初现" in llm_output or "微光" in llm_output))
elif mean_phase < 0.50:
    checks.append((f"phase={mean_phase:.2f}在成长区间", "上升" in llm_output or "扩展" in llm_output or "渐盛" in llm_output))
elif mean_phase < 0.70:
    checks.append((f"phase={mean_phase:.2f}在盛壮区间", "鼎盛" in llm_output or "辉煌" in llm_output or "充盈" in llm_output))
elif mean_phase < 0.85:
    checks.append((f"phase={mean_phase:.2f}在持守区间", "守成" in llm_output or "高处" in llm_output or "隐忧" in llm_output))

# 7.5 势能叙事
pot_ratio = pot_stage['ratio']
if pot_ratio > 1.0:
    checks.append((f"potential_ratio={pot_ratio:.2f}>1.0，体现'已变'", "已变" in llm_output or "旧结构" in llm_output or "瓦解" in llm_output or "反转" in llm_output))
elif pot_ratio > 0.7:
    checks.append((f"potential_ratio={pot_ratio:.2f}在临界区间", "临界" in llm_output or "一触即发" in llm_output or "锋利" in llm_output or "空气" in llm_output))
elif pot_ratio > 0.3:
    checks.append((f"potential_ratio={pot_ratio:.2f}在积蓄区间", "积蓄" in llm_output or "暗流" in llm_output or "不安" in llm_output or "隐忧" in llm_output))
else:
    checks.append((f"potential_ratio={pot_ratio:.2f}在平静区间", "平静" in llm_output or "安宁" in llm_output or "稳态" in llm_output))

# 7.6 禁止项：没有自行解释卦象
# 检查是否写了"坎就是水""离就是火"这类硬编码
gua_hardcodes = ["坎就是水", "离就是火", "乾就是天", "坤就是地", "震就是雷", "巽就是风", "艮就是山", "兑就是泽"]
found_hardcode = any(hc in llm_output for hc in gua_hardcodes)
checks.append(("没有硬编码卦象解释（如'坎就是水'）", not found_hardcode))

# 7.7 张力优先：不只做吉祥话
# 简单检查：如果叙事中出现"但是""然而""却"等转折词，说明有张力
has_tension = any(w in llm_output for w in ["但是", "然而", "却", "张力", "撕扯", "危机", "诅咒"])
checks.append(("体现叙事张力（有转折或矛盾感）", has_tension))

# 7.8 是否有建议
has_advice = "建议" in llm_output or "未来" in llm_output or "趋势" in llm_output or "观测" in llm_output
checks.append(("结尾有建议或趋势暗示", has_advice))

# 打印验证结果
all_pass = True
for desc, ok in checks:
    status = "PASS" if ok else "FAIL"
    if not ok:
        all_pass = False
    print(f"  [{status}] {desc}")

print()
if all_pass:
    print(">>> 阶段二测试通过：LLM 叙事符合结构翻译协议")
else:
    print(">>> 阶段二测试警告：部分验证项未通过，请检查叙事质量")
print("=" * 60)

# 打印 LLM 输出
print("\n【LLM 生成的叙事】\n")
print(llm_output)
