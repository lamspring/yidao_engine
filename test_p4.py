# -*- coding: utf-8 -*-
"""P4 事件驱动引擎端到端测试"""

from kernel import World
from observer import WorldCamera, EntityTracker
from analyst import YaoAnalyst
from event_engine import EventEngine

print("=== P4 事件驱动引擎测试 ===")

# 1. 初始化世界
w = World(height=32, width=64)

# 2. 在世界多个位置建立 tracker
trackers = [
    EntityTracker(w, "center", 16, 32, radius=4),
    EntityTracker(w, "north", 4, 32, radius=3),
    EntityTracker(w, "south", 28, 32, radius=3),
    EntityTracker(w, "west", 16, 8, radius=3),
    EntityTracker(w, "east", 16, 56, radius=3),
]

# 3. 初始化观象者与事件引擎
cam = WorldCamera(w)
analyst = YaoAnalyst(cam)
engine = EventEngine(w, analyst)

# 4. 运行 800 息，收集事件
all_events = []

for tick in range(1, 801):
    w.tick()
    
    # 更新所有 tracker
    for t in trackers:
        t._update()
    
    # 检测 tracker 级别事件
    for t in trackers:
        events = engine.check_tracker_events(t)
        for ev in events:
            all_events.append(ev)
    
    # 检测全局会诊事件
    conf = engine.check_global_events(trackers)
    if conf:
        all_events.append(conf)

# 5. 统计与展示
print(f"\n800 息内共触发 {len(all_events)} 个事件\n")

# 按类型统计
from collections import Counter
type_counts = Counter(ev["event_type"] for ev in all_events)
print("事件类型分布:")
for etype, count in type_counts.most_common():
    print(f"  {etype}: {count} 次")

# 展示前 8 个事件的叙事
print("\n=== 事件叙事样本 ===")
for i, ev in enumerate(all_events[:8]):
    print(f"\n[{i+1}] {ev['event_type']} (第{ev['tick']}息)")
    print(f"    {ev['narrative'][:120]}...")

# 展示最后几个事件（如果有的话）
if len(all_events) > 8:
    print(f"\n... 共 {len(all_events)} 个事件，此处省略 ...")

print("\n=== P4 测试完成 ===")
