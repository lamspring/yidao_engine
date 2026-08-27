# -*- coding: utf-8 -*-
"""
yidao_core 不变量测试套件 —— "逻辑严密"不是感觉，是每次修改后可断言的东西。

运行：python yidao_core/tests/test_invariants.py

不变量：
  1. 太初自生：从无到有——炁场极化产生非均匀世界（有高地有洼地有水），且确定可复现。
  2. 分布图创世：用户给的阴阳分布图（任意尺寸）能凝聚成世界。
  3. 点化：观测者点击 (y,x)，该处诞生一点灵。
  4. 确定性：同种子两次运行，世界与众灵状态逐字节一致。
  5. 有界性：所有场有限、非负；草 ∈ [0,1]；人口有上限；记忆有容量。
  6. 水量闭环：水 + 云 + 九泉的总量长期漂移有界（不涝不涸）。
  7. 天道守道不救生：健康世界里天道沉默；炁场死寂时唯再动一念；众生灭绝不出手。
  8. 世界是活的：短程运行内有多种显著事件自然发生。
  9. 世界无史：世界对象不携带随时间无限增长的历史结构。
  10. 死寂重启：炁场被抹平后，天道以一缕涨落重启变化（且没有为死者降恩）。
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import numpy as np

from yidao_core.world import World, TICKS_PER_DAY
from yidao_core.session import Session
from yidao_core.genesis import 炁场极化, 界面点

PASS = 0


def ok(name, cond, detail=""):
    global PASS
    assert cond, f"✗ {name} {detail}"
    PASS += 1
    print(f"✓ {name} {detail}")


def 众灵指纹(session):
    return tuple((s.name, s.alive, round(s.yang, 6), s.y, s.x,
                  len(s.memories), round(s.strength, 6)) for s in session.spirits)


def 世界指纹(session):
    w = session.world
    return tuple(np.asarray(a).tobytes() for a in (w.height, w.water, w.cloud, w.grass))


# ── 1. 太初自生 ──────────────────────────────
def test_genesis():
    Q1 = 炁场极化(32, 42)
    Q2 = 炁场极化(32, 42)
    Q3 = 炁场极化(32, 7)
    assert np.array_equal(Q1, Q2), "同种子炁场必须一致"
    assert not np.array_equal(Q1, Q3), "异种子炁场必须不同"
    w = World(seed=42)
    ok("太初自生·非均匀", w.height.std() > 0.5, f"地形标准差 {w.height.std():.2f}")
    ok("太初自生·有水", float(w.water.mean()) > 0.05, f"水均 {w.water.mean():.2f}")
    ok("太初自生·有旱有涝的可能", float(w.water.max()) > 1.0,
       f"最深 {w.water.max():.1f}")
    ok("太初自生·太古草木已生", float(w.grass.mean()) > 0.05,
       f"草均 {w.grass.mean():.2f}")
    cells = 界面点(w.height, w.water)
    ok("太初自生·有交界可生灵", len(cells) > 0, f"{len(cells)} 处界面")


# ── 2. 分布图创世 ─────────────────────────────
def test_init_map():
    图 = [[0.9, 0.1, 0.1, 0.9],
          [0.1, 0.5, 0.5, 0.1],
          [0.1, 0.5, 0.5, 0.1],
          [0.9, 0.1, 0.1, 0.9]]
    w = World(seed=1, init_map=图)
    ok("分布图创世", w.height.shape == (32, 32) and w.height.std() > 0.3,
       f"4×4 → {w.height.shape}，高差 {w.height.std():.2f}")
    # 图的四角是阴聚（0.9）→ 应为高地；中央为阳散（0.5→0.1）→ 应低
    角 = float(np.mean([w.height[2, 2], w.height[2, -3], w.height[-3, 2], w.height[-3, -3]]))
    心 = float(w.height[16, 16])
    ok("分布图创世·阴阳成形", 角 > 心, f"角高 {角:.1f} > 心高 {心:.1f}")


# ── 3. 点化 ─────────────────────────────────
def test_seed_at():
    s = Session.genesis(seed=42)
    n0 = len(s.spirits)
    灵 = s.seed_at(16, 16)
    ok("点化·诞生", len(s.spirits) == n0 + 1 and 灵.alive, f"名 {灵.name}")
    ok("点化·落地非深水", s.world.water[灵.y, 灵.x] < 1.8,
       f"落于 ({灵.y},{灵.x}) 水深 {s.world.water[灵.y, 灵.x]:.2f}")


# ── 4. 确定性 ───────────────────────────────
def test_determinism():
    a = Session.genesis(seed=42)
    a.run(640)
    b = Session.genesis(seed=42)
    b.run(640)
    ok("确定性·世界逐字节一致", 世界指纹(a) == 世界指纹(b))
    ok("确定性·众灵一致", 众灵指纹(a) == 众灵指纹(b))


# ── 5/6/7/8/9. 长程健康 ───────────────────────
def test_long_run():
    log = []
    s = Session.genesis(seed=2026, on_event=lambda **kw: log.append(kw))
    水量初 = float(s.world.water.sum() + s.world.cloud.sum())
    s.run(TICKS_PER_DAY * 30)
    w = s.world

    ok("有界·数值有限", w.numbers_sane())
    ok("有界·草 ∈ [0,1]", bool((w.grass >= 0).all() and (w.grass <= 1).all()))
    ok("有界·水云九泉非负", float(w.water.min()) >= 0 and float(w.cloud.min()) >= 0
       and w._深潭 >= 0, f"九泉 {w._深潭:.0f}")
    alive = [x for x in s.spirits if x.alive]
    ok("有界·人口有上限", len(s.spirits) <= 25, f"历生 {len(s.spirits)}")
    ok("有界·记忆有容量", all(len(x.memories) <= 41 for x in s.spirits),
       f"最多 {max(len(x.memories) for x in s.spirits)} 条")
    ok("有界·众灵数值正常", all(-1e-6 <= x.yang <= 100.1 and 0 <= x.pressure <= 1.01
                                for x in s.spirits))

    水量末 = float(w.water.sum() + w.cloud.sum() + w._深潭)
    漂移 = abs(水量末 - 水量初) / max(水量初, 1e-9)
    ok("水量闭环·漂移有界", 漂移 < 0.5, f"漂移 {漂移:.1%}（初 {水量初:.0f} → 末 {水量末:.0f}）")

    kinds = {e["kind"] for e in log}
    天道 = sum(1 for e in log if e["kind"] == "天道")
    ok("天道少为", 天道 <= 3, f"30 日干预 {天道} 次")
    ok("世界是活的", len(kinds) >= 5, f"显著事件 {len(kinds)} 类")
    ok("众生未灭", len(alive) >= 1, f"存活 {len(alive)}")

    # 世界无史：世界对象里不应存在随念数线性增长的历史容器
    历史嫌疑 = []
    for 名, 值 in vars(w).items():
        if isinstance(值, list) and len(值) > 1000:
            历史嫌疑.append((名, len(值)))
    ok("世界无史", not 历史嫌疑, f"{历史嫌疑}")


# ── 10. 死寂重启（天道守道不救生）──────────────
def test_stagnation_stir():
    s = Session.genesis(seed=42)
    w = s.world
    # 抹平炁场、众生尽灭：水尽、云散、草绝、墒消，连九泉也枯了——这才是真正的"无"
    w.water[:] = 0.0
    w.cloud[:] = 0.0
    w.grass[:] = 0.0
    w.moisture[:] = 0.0
    w._深潭 = 0.0
    for x in s.spirits:
        x.alive = False
    log = []
    s.on_event = lambda **kw: log.append(kw)
    s.run(2 * TICKS_PER_DAY + 5)
    再动 = [e for e in log if e["kind"] == "天道" and "再动一念" in e["text"]]
    ok("死寂重启·天道再动一念", len(再动) >= 1, f"{len(再动)} 次")
    ok("死寂重启·炁场复有涨落", float(w.cloud.std()) > 1e-6,
       f"云差 {w.cloud.std():.4f}")
    # 同一缸里，天道没有为灭绝的众生降过雨施过肥
    救生 = [e for e in log if e["kind"] == "天道" and "再动一念" not in e["text"]]
    ok("死寂重启·不为众生降恩", not 救生, f"{[e['text'] for e in 救生]}")


if __name__ == "__main__":
    print("yidao_core 不变量测试\n" + "─" * 40)
    test_genesis()
    test_init_map()
    test_seed_at()
    test_determinism()
    test_long_run()
    test_stagnation_stir()
    print("─" * 40)
    print(f"全部通过（{PASS} 项断言）。世界的严密性已被断言，而非感觉。")
