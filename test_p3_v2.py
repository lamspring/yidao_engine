# -*- coding: utf-8 -*-
"""P3 语库扩展精度验证——聚焦复合卦体描述"""

from kernel import World
from observer import WorldCamera, EntityTracker
from analyst import YaoAnalyst
from body_nature import get_body_nature
from codex import get_gua

print("=== P3 语库扩展精度验证 ===")

w = World(height=32, width=64)

# 在世界多个位置埋设 tracker，跑 1000 息
positions = [
    (8, 16), (8, 48), (24, 16), (24, 48),
    (16, 8), (16, 32), (16, 56), (4, 32),
]
trackers = []
for idx, (y, x) in enumerate(positions):
    t = EntityTracker(w, f"region_{idx}", y, x, radius=3)
    trackers.append(t)

for _ in range(1000):
    w.tick()
    for t in trackers:
        t._update()

# 初始化观象者
cam = WorldCamera(w)
analyst = YaoAnalyst(cam)

# 筛选出 interesting 的样本：single+复合卦 / contested / chaotic
print("\n=== 复合卦体描述精度展示 ===\n")

interesting = []
for t in trackers:
    body_info = t.get_body("objective")
    hex_val = body_info["body_hex"]
    btype = body_info["body_type"]
    
    # 只展示：复合卦单一体、交战体、混沌体
    is_pure = hex_val in [0, 9, 18, 27, 36, 45, 54, 63]
    if btype == "single" and is_pure:
        continue  # 跳过纯卦单一体，那些已经验证过了
    
    interesting.append((t, body_info))

if not interesting:
    print("本轮未生成 contested/chaotic 或复合卦单一体。")
    print("展示所有样本中的体类型分布：")
    from collections import Counter
    type_dist = Counter(t.body_type for t in trackers)
    hex_dist = Counter(t.get_body("objective")["body_hex"] for t in trackers)
    print(f"  体类型: {dict(type_dist)}")
    print(f"  体卦象: {dict(hex_dist)}")
    
    # 强制展示一个复合卦的 body_nature 对比
    print("\n=== 强制对比：既济(21) 的体描述 ===")
    print(f"扩展后: {get_body_nature(21)[:80]}...")
    print(f"扩展前(fallback): 光明的显化者...")
    
else:
    for t, body_info in interesting:
        hex_val = body_info["body_hex"]
        btype = body_info["body_type"]
        gua = get_gua(hex_val)
        
        # 用 analyst 跑两轮
        cam.move_to(t.center_y, t.center_x)
        result = analyst.run_two_rounds(t, perspective="objective")
        
        print(f"--- {t.entity_id} ({t.center_y},{t.center_x}) ---")
        print(f"  体类型: {btype}")
        print(f"  体卦象: {gua['name']}({hex_val})")
        print(f"  置信度: {body_info['body_confidence']:.3f}")
        print(f"  变化率: {body_info['volatility']:.3f}")
        
        if btype == "contested":
            pair = body_info.get("contested_pair")
            if pair:
                from observer import _is_opposite_pair
                print(f"  交战对: {pair}, 对卦={_is_opposite_pair(pair[0], pair[1])}")
        
        print(f"\n  体之本质:")
        nature = result["body"]["body_nature"]
        print(f"  {nature[:120]}...")
        
        print(f"\n  narrative_thread:")
        for line in result["narrative_thread"].split("\n")[:3]:
            print(f"  {line}")
        print()

# 统计全局
print("=== 全局体类型分布 ===")
from collections import Counter
type_dist = Counter(t.body_type for t in trackers)
print(f"  {dict(type_dist)}")

print("\n=== 高频体卦象统计 ===")
hex_counts = Counter(t.get_body("objective")["body_hex"] for t in trackers)
for hex_val, count in hex_counts.most_common():
    gua = get_gua(hex_val)
    is_covered = hex_val in [0, 9, 18, 27, 36, 45, 54, 63,
                             21, 42, 7, 56, 61, 47, 52, 11,
                             49, 35, 6, 24, 41, 37, 38, 25]
    status = "✅ 专属" if is_covered else "⚪ fallback"
    print(f"  {gua['name']:3s}({hex_val:2d}): {count}次  {status}")

print("\n验证完成!")
