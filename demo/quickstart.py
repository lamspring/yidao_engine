# -*- coding: utf-8 -*-
"""
易道引擎 · 5 分钟快速上手 Demo

用法:
  python demo/quickstart.py              # 纯本地：显示世界数据的自然语言解释
  python demo/quickstart.py --llm         # 调用 LLM 生成文学叙事（需设 API key）
  python demo/quickstart.py --llm --worldview xiuxian  # 修仙世界观叙事
"""

import sys, os

# 确保能找到项目模块
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from kernel import World
from observer import WorldCamera, EntityTracker
from analyst import YaoAnalyst
from codex import get_gua
from phenomenon_codex import get_potential_stage, get_manifestation, get_phenomenon

print("=" * 60)
print(" 易道引擎 Demo — 世界在运转，观测即显化")
print("=" * 60)

# ── 1. 创建世界，运行 300 tick ──
print("\n[1/3] 世界诞生中...")
w = World(height=32, width=64)
cam = WorldCamera(w, y=16, x=32, scale="meso", intent="character")
tracker = EntityTracker(w, "demo_entity", 16, 32, radius=4)
analyst = YaoAnalyst(cam)

for i in range(300):
    w.tick()
    tracker._update()
    if (i + 1) % 100 == 0:
        print(f"  ...{i+1} 息")

print(f"  当前: 第 {w.tick_count} 息 | 道阈值 V={w.V_thresh:.2f}")

# ── 2. 找到最值得观测的位置 ──
print("\n[2/3] 摄像机寻找焦点...")
max_idx = w.potential.argmax()
fy, fx = max_idx // w.W, max_idx % w.W
cam.move_to(fy, fx)
body_usage = analyst.run_two_rounds(tracker, perspective="objective")

body = body_usage["body"]
usage = body_usage["usage"]
relation = body_usage["relation"]

# 势能阶段
center_pot = float(w.potential[fy, fx])
pot_stage = get_potential_stage(center_pot, w.V_thresh)

# 感官数据
protocol = usage.get("_meta", {}).get("protocol",
            get_gua(usage["current_hex"]).get("protocol", "复合"))
pure_map = {"承载":0, "激变":9, "深渊":18, "渗透":27, "止界":36, "显文明":45, "交换":54, "创序":63}
pure_hex = pure_map.get(protocol, 0)

# ── 3. 输出观测报告 ──
print("\n[3/3] 观测报告：\n")
print("=" * 60)
print(f"  时间: 第 {w.tick_count} 息")
print(f"  位置: ({fy}, {fx})")
print()
print(f"  ▎体（骨子里的本质）")
print(f"    卦: {body['body_name']}({body['body_hex']})")
print(f"    协议: {body['body_protocol']}")
print(f"    类型: {body['body_type']} (置信度 {body['body_confidence']:.2f})")
print(f"    本质: {body['body_nature'][:80]}...")
print()
print(f"  ▎用（此刻的显现）")
print(f"    卦: {usage['current_name']}({usage['current_hex']})")
print(f"    阶段: {usage['life_stage']}")
print(f"    语气: {usage['structural_tone'][:80]}...")
print()
print(f"  ▎关系: {relation['type']} — {relation['description']}")
print(f"  ▎势能: {center_pot:.2f} / {w.V_thresh:.2f} ({pot_stage['ratio_label']})")
print(f"      {pot_stage['atmosphere']}")
print()
print(f"  ▎感官:")
print(f"    视: {', '.join(get_phenomenon(pure_hex, 'visual')[:3])}")
print(f"    听: {', '.join(get_phenomenon(pure_hex, 'sound')[:3])}")
print(f"    动: {', '.join(get_phenomenon(pure_hex, 'motion')[:3])}")
print(f"    情: {', '.join(get_phenomenon(pure_hex, 'mood')[:3])}")
print()
print(f"  ▎物类映射（{cam.intent}）:")
print(f"    {get_manifestation(pure_hex, cam.intent)[:100]}...")
print("=" * 60)

# ── 可选：LLM 文学叙事 ──
if "--llm" in sys.argv:
    print("\n[LLM] 调用语言模型生成文学叙事...")
    worldview_name = None
    for i, arg in enumerate(sys.argv):
        if arg == "--worldview" and i + 1 < len(sys.argv):
            worldview_name = sys.argv[i + 1]

    worldview = None
    worldview_inject = ""
    if worldview_name:
        import json
        config_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "configs")
        wv_path = os.path.join(config_dir, "worldviews", f"{worldview_name}.json")
        if os.path.isfile(wv_path):
            with open(wv_path, "r", encoding="utf-8") as f:
                worldview = json.load(f)
            worldview_inject = f"\n世界观：{worldview['name']} — {worldview['description']}\n"
            for proto, entry in worldview.get("protocol_map", {}).items():
                worldview_inject += f"  {proto} -> {entry['name']}: {entry['description']}\n"

    system_prompt = f"""你是一位世界观测者。你把底层结构数据翻译成一段生动的文学叙事。
规则：
1. 正文中禁止出现卦名、数字、系统术语
2. 用动作、环境、感官细节代替抽象概念
3. 200字以内，最后以一个具体画面收尾
{worldview_inject}"""

    user_prompt = f"""观测到以下世界状态：

实体"{tracker.entity_id}"的本质：{body['body_nature'][:150]}
此刻它显化为{usage['current_name']}卦，处于{usage['life_stage']}。
{usage['structural_tone'][:120]}
体用关系：{relation['description']}。
势能处于{pot_stage['ratio_label']}阶段。{pot_stage['atmosphere']}
感官描述：视觉-{', '.join(get_phenomenon(pure_hex, 'visual')[:3])}
听觉-{', '.join(get_phenomenon(pure_hex, 'sound')[:3])}
氛围-{', '.join(get_phenomenon(pure_hex, 'mood')[:3])}

请写一段文学叙事："""

    # 尝试调用 LLM
    api_base = os.environ.get("YIDAO_API_BASE", "https://token-plan-cn.xiaomimimo.com/v1")
    api_key = os.environ.get("MIMO_API_KEY", os.environ.get("YIDAO_API_KEY", ""))
    model = "mimo-v2.5-pro"

    if not api_key:
        api_key = os.environ.get("DEEPSEEK_API_KEY", "")
        api_base = "https://api.deepseek.com"
        model = "deepseek-chat"

    if not api_key:
        api_key = os.environ.get("OPENAI_API_KEY", "")
        api_base = "https://api.openai.com"
        model = "gpt-4o"

    if api_key:
        import requests
        try:
            resp = requests.post(
                f"{api_base}/chat/completions",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={"model": model, "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ], "temperature": 0.75, "max_tokens": 800},
                timeout=60,
            )
            if resp.ok:
                text = resp.json()["choices"][0]["message"]["content"]
                print("\n" + "-" * 60)
                print(text)
                print("-" * 60)
            else:
                print(f"  LLM 调用失败: {resp.status_code}")
        except Exception as e:
            print(f"  LLM 调用异常: {e}")
    else:
        print("  未检测到 API Key。请设置 MIMO_API_KEY / DEEPSEEK_API_KEY / OPENAI_API_KEY 之一。")
        print("  或者在无 LLM 模式下，上面的观测报告已经是完整的世界描述了。")

print(f"\n{'=' * 60}")
print(" Demo 结束。这个世界还在继续运转——每次运行，你都会看到不同的状态。")
print(f"{'=' * 60}")
