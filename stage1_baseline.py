# -*- coding: utf-8 -*-
"""
阶段一：基线脚本测试
生成标准观测数据包，供后续 LLM 测试使用
"""

import json
import sys
import io
# Windows控制台UTF-8修复：防止Unicode字符输出时gbk编码错误
if sys.platform == "win32" and hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')


# 确保在本目录运行
from kernel import World, yang_count
from observer import WorldCamera, EntityTracker
from interpreter import XiangInterpreter
from analyst import YaoAnalyst
from event_engine import EventEngine

print("=" * 60)
print("【阶段一】基线脚本测试")
print("=" * 60)

# ───────────────────────────────────────────
# 1. 初始化世界
# ───────────────────────────────────────────
print("\n[1/5] 初始化世界 32x64...")
world = World(height=32, width=64)
cam = WorldCamera(world, y=16, x=32, scale="meso", intent="landscape")
interpreter = XiangInterpreter(cam)

# ───────────────────────────────────────────
# 2. 静默运行 500 tick
# ───────────────────────────────────────────
print("[2/5] 静默运行 500 tick...")
for i in range(500):
    world.tick()
    if (i + 1) % 100 == 0:
        print(f"  ...已完成 {i + 1} 息")

print(f"  世界当前 tick: {world.tick_count}")
print(f"  道阈值 V_thresh: {world.V_thresh:.3f}")
print(f"  道偏置 dao_bias: {world.dao_bias:+.3f}")

# 全局统计
yc = yang_count(world.gua)
yang_ratio = float(yc.mean()) / 6.0
print(f"  全局阳爻比: {yang_ratio:.2%}")

# ───────────────────────────────────────────
# 3. 标准 capture() 数据包
# ───────────────────────────────────────────
print("\n[3/5] 生成标准 capture() 数据包...")
packet = cam.capture()

# 美化输出
def pretty_json(data):
    return json.dumps(data, ensure_ascii=False, indent=2)

with open("stage1_capture_packet.json", "w", encoding="utf-8") as f:
    f.write(pretty_json(packet))
print("  已保存: stage1_capture_packet.json")

# ───────────────────────────────────────────
# 4. 极简 capture_minimal() 数据包
# ───────────────────────────────────────────
print("\n[4/5] 生成极简 capture_minimal() 数据包...")
mini = cam.capture_minimal()
with open("stage1_capture_minimal.json", "w", encoding="utf-8") as f:
    f.write(pretty_json(mini))
print("  已保存: stage1_capture_minimal.json")

# ───────────────────────────────────────────
# 5. 象法解释（Yao Descriptor）
# ───────────────────────────────────────────
print("\n[5/5] 生成象法解释描述符...")
descriptor = interpreter.interpret(packet)
with open("stage1_descriptor.json", "w", encoding="utf-8") as f:
    f.write(pretty_json(descriptor))
print("  已保存: stage1_descriptor.json")

# ───────────────────────────────────────────
# 6. 多尺度多位置观测（扩展测试）
# ───────────────────────────────────────────
print("\n[扩展] 多尺度多位置观测...")

scenarios = []

# 场景A：当前焦点（meso尺度）
scenarios.append({
    "name": "焦点观测（meso）",
    "packet": packet,
    "descriptor": descriptor,
})

# 场景B：微观单点
cam.set_scale("micro")
packet_micro = cam.capture()
descriptor_micro = interpreter.interpret(packet_micro)
scenarios.append({
    "name": "微观单点（micro）",
    "packet": packet_micro,
    "descriptor": descriptor_micro,
})

# 场景C：宏观区域
cam.set_scale("macro")
packet_macro = cam.capture()
descriptor_macro = interpreter.interpret(packet_macro)
scenarios.append({
    "name": "宏观区域（macro）",
    "packet": packet_macro,
    "descriptor": descriptor_macro,
})

# 场景D：宇观全局
cam.set_scale("cosmic")
packet_cosmic = cam.capture()
descriptor_cosmic = interpreter.interpret(packet_cosmic)
scenarios.append({
    "name": "宇观全局（cosmic）",
    "packet": packet_cosmic,
    "descriptor": descriptor_cosmic,
})

# 场景E：追踪异常点
cam.set_scale("meso")
cam.pan_to_anomaly()
packet_anomaly = cam.capture()
descriptor_anomaly = interpreter.interpret(packet_anomaly)
scenarios.append({
    "name": f"异常追踪（meso, 位置{cam.y},{cam.x}）",
    "packet": packet_anomaly,
    "descriptor": descriptor_anomaly,
})

with open("stage1_multi_scenarios.json", "w", encoding="utf-8") as f:
    f.write(pretty_json(scenarios))
print("  已保存: stage1_multi_scenarios.json")

# ───────────────────────────────────────────
# 7. 体用两轮分析（带 tracker）
# ───────────────────────────────────────────
print("\n[扩展] 体用两轮分析...")
tracker = EntityTracker(world, "test_entity", 16, 32, radius=4)
# 已经运行了500tick，tracker的hex_history已有数据
analyst = YaoAnalyst(cam)
body_usage_result = analyst.run_two_rounds(tracker, perspective="objective")

with open("stage1_body_usage.json", "w", encoding="utf-8") as f:
    f.write(pretty_json(body_usage_result))
print("  已保存: stage1_body_usage.json")

# ───────────────────────────────────────────
# 8. 事件引擎检测
# ───────────────────────────────────────────
print("\n[扩展] 事件引擎检测...")
engine = EventEngine(world, analyst)
events = engine.check_tracker_events(tracker)
global_event = engine.check_global_events([tracker])

event_dump = {
    "tracker_events": events,
    "global_event": global_event,
}
with open("stage1_events.json", "w", encoding="utf-8") as f:
    f.write(pretty_json(event_dump))
print("  已保存: stage1_events.json")
if events:
    print(f"  检测到 {len(events)} 个 tracker 事件")
for ev in events:
    print(f"    - {ev['event_type']} (tick {ev['tick']})")

# ───────────────────────────────────────────
# 9. 结构验证报告
# ───────────────────────────────────────────
print("\n" + "=" * 60)
print("【结构验证报告】")
print("=" * 60)

def check_field(data, path, expected_type=None):
    """检查数据路径是否存在且类型正确"""
    keys = path.split(".")
    curr = data
    for k in keys:
        if isinstance(curr, dict) and k in curr:
            curr = curr[k]
        else:
            return False, f"缺失: {path}"
    if expected_type and not isinstance(curr, expected_type):
        return False, f"类型错误: {path} 应为 {expected_type.__name__}"
    return True, f"OK: {path}"

checks = [
    (packet, "observer_id", str),
    (packet, "timestamp", int),
    (packet, "focus.center", list),
    (packet, "focus.radius", int),
    (packet, "scale", str),
    (packet, "intent", str),
    (packet, "data.hexagram", int),
    (packet, "data.active_lines", list),
    (packet, "data.neighbor_profile.dominant_hexagram", int),
    (packet, "data.neighbor_profile.relation_term", str),
    (packet, "data.history.recent_hexagrams", list),
    (packet, "data.history.long_term_dominant", int),
    (packet, "data.history.volatility", float),
    (packet, "persistence.is_persistent", bool),
    (packet, "_meta.global_yang_ratio", float),
    (packet, "_meta.V_thresh", float),
    (packet, "_meta.dao_bias", float),
    
    (descriptor, "primary_structure", str),
    (descriptor, "structural_tone", str),
    (descriptor, "active_line", int),
    (descriptor, "life_stage", str),
    (descriptor, "change_narrative", str),
    (descriptor, "scale", str),
    (descriptor, "context_modifier", str),
    (descriptor, "historical_trend", str),
    (descriptor, "dao_influence", str),
    (descriptor, "possible_manifestations", dict),
    (descriptor, "_meta.yang_ratio", float),
    
    (body_usage_result, "body.body_hex", int),
    (body_usage_result, "body.body_type", str),
    (body_usage_result, "body.body_confidence", float),
    (body_usage_result, "body.body_nature", str),
    (body_usage_result, "usage.current_hex", int),
    (body_usage_result, "usage.structural_tone", str),
    (body_usage_result, "relation.type", str),
    (body_usage_result, "relation.description", str),
    (body_usage_result, "narrative_thread", str),
]

all_pass = True
for data, path, typ in checks:
    ok, msg = check_field(data, path, typ)
    status = "✅" if ok else "❌"
    if not ok:
        all_pass = False
    print(f"  {status} {msg}")

print("\n" + "=" * 60)
if all_pass:
    print("【阶段一测试通过】所有结构字段验证成功")
else:
    print("【阶段一测试失败】存在字段缺失或类型错误")
print("=" * 60)
