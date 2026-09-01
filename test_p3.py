# -*- coding: utf-8 -*-
"""P3 体用两轮流水线端到端测试"""

from kernel import World
from observer import WorldCamera, EntityTracker
from analyst import YaoAnalyst

print("=== P3 体用两轮流水线端到端测试 ===")

# 1. 初始化世界
w = World(height=32, width=64)

# 2. 在世界中心建立 tracker 并跑 500 息
tracker = EntityTracker(w, "civilization_01", 16, 32, radius=4)
for _ in range(500):
    w.tick()
    tracker._update()

# 3. 建立摄像机
cam = WorldCamera(w, y=16, x=32)
cam.track_entity("civilization_01", y=16, x=32, radius=4)

# 4. 初始化观象者
analyst = YaoAnalyst(cam)

# 5. 执行两轮分析
result = analyst.run_two_rounds(tracker, perspective="objective")

print("\n=== 观体（第一轮）===")
body = result["body"]
print(f"实体: {body['entity_id']}")
print(f"体类型: {body['body_type']}")
print(f"体置信度: {body['body_confidence']}")
print(f"体卦象: {body['body_name']}({body['body_hex']})")
print(f"协议: {body['body_protocol']}")
print(f"历史长度: {body['history_length']}")
print(f"变化率: {body['volatility']}")
print(f"\n体之本质:")
print(body["body_nature"][:120] + "...")

print("\n=== 观用（第二轮）===")
usage = result["usage"]
print(f"当前卦象: {usage['current_name']}({usage['current_hex']})")
print(f"结构语气: {usage['structural_tone'][:80]}...")
print(f"生命阶段: {usage['life_stage']}")
print(f"变化叙事: {usage['change_narrative'][:80]}...")

print("\n=== 体用关系 ===")
rel = result["relation"]
print(f"关系类型: {rel['type']}")
print(f"关系描述: {rel['description']}")

print("\n=== 体用对照叙事（narrative_thread）===")
print(result["narrative_thread"])

# 6. 测试四种视角
print("\n=== 四种视角对比 ===")
for perspective in ["objective", "archaeologist", "sociologist", "taoist"]:
    r = analyst.run_two_rounds(tracker, perspective=perspective)
    b = r["body"]
    print(f"{perspective:15s}: 体={b['body_name']}({b['body_type']}), 用={r['usage']['current_name']}, 关系={r['relation']['type']}")

print("\nP3 测试通过!")
