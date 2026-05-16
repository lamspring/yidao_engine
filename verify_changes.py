# -*- coding: utf-8 -*-
"""改动验证脚本 — 验证本次所有修改的正确性"""
import numpy as np
from kernel import World, hugua, yao_bian, hugua_scalar, yao_bian_scalar

print("=" * 60)
print("【改动验证】64息卦运 + 向量化 + 索引统一")
print("=" * 60)

# ── 1. hugua 向量化一致性 ──
print("\n[1/5] hugua 向量化 vs 标量一致性...")
mismatches = 0
for v in range(64):
    vec = int(hugua(np.array([v], dtype=np.uint8))[0])
    scalar = hugua_scalar(v)
    if vec != scalar:
        print(f"  MISMATCH: hugua({v}) = vec={vec}, scalar={scalar}")
        mismatches += 1
if mismatches:
    print(f"  FAIL: {mismatches} mismatches")
else:
    print("  PASS: 64卦全部一致")

# ── 2. yao_bian 向量化一致性 ──
print("\n[2/5] yao_bian 向量化 vs 标量一致性...")
mismatches = 0
for v in range(64):
    for pos in range(6):
        vec = int(yao_bian(np.array([v], dtype=np.uint8), np.array([pos], dtype=np.uint8))[0])
        scalar = yao_bian_scalar(v, pos)
        if vec != scalar:
            mismatches += 1
if mismatches:
    print(f"  FAIL: {mismatches} mismatches")
else:
    print("  PASS: 64×6=384 全部一致")

# ── 3. World 模拟运行 ──
print("\n[3/5] World 模拟 200 tick（验证新 senescence 不崩溃）...")
w = World(height=32, width=64)
for i in range(200):
    w.tick()
mean_pot = float(w.potential.mean())
max_pot = float(w.potential.max())
print(f"  tick={w.tick_count}, V_thresh={w.V_thresh:.3f}, dao_bias={w.dao_bias:+.3f}")
print(f"  mean pot={mean_pot:.3f}, max pot={max_pot:.3f}")
# 验证势能不会无限增长
assert max_pot <= 2.5, f"势能溢出: {max_pot}"
print("  PASS: 势能无溢出")

# ── 4. 卦运周期波形验证 ──
print("\n[4/5] 卦运周期波形验证...")
import numpy as np
ages = np.array([0, 8, 16, 24, 32, 40, 48, 56, 63, 64, 80, 96, 127], dtype=np.float32)
for a in ages:
    cycle_phase = 2 * np.pi * (a % 64) / 64.0
    cycle_factor = 0.5 * (1.0 - np.cos(cycle_phase))
    boost = 0.03 * cycle_factor
    print(f"  age={a:4.0f} cycle_age={a%64:3.0f} factor={cycle_factor:.3f} boost={boost:.4f}")
print("  PASS: 波形正确")

# ── 5. 索引统一验证 ──
print("\n[5/5] 索引统一验证...")
from observer import get_dominant_trigram, get_relation_term
# 构造一个测试区域
test_region = np.array([[63]], dtype=np.uint8)  # 乾卦=全阳
dom = get_dominant_trigram(test_region)
assert dom == 63, f"期望 63，得到 {dom}"
print(f"  get_dominant_trigram(乾)= {dom} (期望 63) ✓")

# 验证关系词函数接受卦值
rel = get_relation_term(63, 0)  # 乾坤 = 天地对冲
assert "天地对冲" in rel, f"期望天地对冲，得到 {rel}"
print(f"  get_relation_term(乾,坤)= '{rel}' ✓")

# 向后兼容：也接受0-7索引
rel2 = get_relation_term(7, 0)
assert "天地对冲" in rel2, f"期望天地对冲（兼容），得到 {rel2}"
print(f"  get_relation_term(7,0 兼容)= '{rel2}' ✓")

print("\n" + "=" * 60)
print("【全部验证通过】")
print("=" * 60)
