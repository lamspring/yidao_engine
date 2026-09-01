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
  6. 守恒（宇宙底座第一律）：水文 Δ = 越界账A；能量 Δ = 泵 − 草汲 + 越界账B。
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
    return tuple(np.asarray(a).tobytes()
                 for a in (w.height, w.water, w.cloud, w.grass, w.qi.yin, w.qi.yang))


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
    水量初 = s.world.水总量A(s.spirits)
    能量初 = s.world.能量总量B(s.spirits)
    万物初 = s.world.万物总量C(s.spirits)
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
                                for x in s.spirits if x.alive))   # 死者心已盖棺，不在此约
    ok("有界·炁场非负", float(w.qi.yin.min()) >= 0 and float(w.qi.yang.min()) >= 0,
       f"炁 {w.qi.总量():.0f}")

    # 一物一处：任何物品不得同时处于两个容器（分身有术曾是储粮循环的真 bug）
    物位 = {}
    for x in s.spirits:
        for it in x.bag:
            物位.setdefault(id(it), []).append(x.name + ".bag")
    for b in w.buildings:
        for it in b.仓储:
            物位.setdefault(id(it), []).append(b.主人 + ".仓储")
    for r in w.relics:
        for it in r["物"]:
            物位.setdefault(id(it), []).append("遗物@" + r["名"])
    分身 = {k: v for k, v in 物位.items() if len(v) > 1}
    ok("一物一处·无分身", not 分身, f"{分身}")

    # 宇宙底座第一律：总量守恒，唯越界可破，越界必留痕
    # A 域（水文：场水+云+九泉+体水+罐水）：Δ 必须严格等于越界账（云散排气/天道注云）
    水量末 = w.水总量A(s.spirits)
    差A = abs(水量末 - 水量初 - w.账.越界A)
    ok("守恒·水文严格守恒±越界账", 差A < 1e-6 * max(水量初, 1.0),
       f"Δ {水量末 - 水量初:+.1f} = 越界账 {w.账.越界A:+.1f}（差 {差A:.2e}）")
    # B 域（能量）：Δ(炁+灵阳+灵形阴+兽阳+兽形阴) = 泵 − 草汲 + 物归 + 食转 + 越界账
    能量末 = w.能量总量B(s.spirits)
    应 = w.账.泵 - w.账.草汲 + w.账.物归 + w.账.食转 + w.账.越界B
    差B = abs(能量末 - 能量初 - 应)
    ok("守恒·能量严格守恒±泵与越界账", 差B < 1e-6 * max(能量初, 1.0),
       f"Δ {能量末 - 能量初:+.1f} = 泵 {w.账.泵:.1f} − 草汲 {w.账.草汲:.1f} "
       f"+ 物归 {w.账.物归:.1f} + 食转 {w.账.食转:.1f} + 越界 {w.账.越界B:+.1f}（差 {差B:.2e}）")
    # C 域（器物）：Δ(物品+屋火井栏) = 源C − 物归 − 食转 + 越界C
    万物末 = w.万物总量C(s.spirits)
    应C = w.账.源C - w.账.物归 - w.账.食转 + w.账.越界C
    差C = abs(万物末 - 万物初 - 应C)
    ok("守恒·器物严格守恒±源与归", 差C < 1e-6 * max(万物初, 1.0),
       f"Δ {万物末 - 万物初:+.1f} = 源C {w.账.源C:.1f} − 物归 {w.账.物归:.1f} "
       f"− 食转 {w.账.食转:.1f} + 越界 {w.账.越界C:+.1f}（差 {差C:.2e}）")

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


# ── 8.5 侏罗纪缸（纯兽世界：食物链活着，守恒不破）─────────
def test_jurassic():
    import collections
    ev = []
    s = Session.genesis(seed=123, 生灵=False, 兽群="侏罗纪",
                        on_event=lambda **kw: ev.append(kw))
    ok("侏罗纪·无灵开缸", len(s.spirits) == 0 and len(s.world.animals) > 0,
       f"兽 {len(s.world.animals)}")
    w = s.world
    A0 = w.水总量A(s.spirits)
    B0 = w.能量总量B(s.spirits)
    C0 = w.万物总量C(s.spirits)
    s.run(TICKS_PER_DAY * 30)
    # 食物链活着：猎杀真实发生
    猎 = sum(1 for e in ev if e["kind"] == "猎杀")
    ok("侏罗纪·猎杀真实发生", 猎 > 0, f"猎杀 {猎} 起")
    # 守恒：无灵之缸，三域恒等式纹丝不动
    dA = abs(w.水总量A(s.spirits) - A0 - w.账.越界A)
    dB = abs(w.能量总量B(s.spirits) - B0
             - (w.账.泵 - w.账.草汲 + w.账.物归 + w.账.食转 + w.账.越界B))
    dC = abs(w.万物总量C(s.spirits) - C0
             - (w.账.源C - w.账.物归 - w.账.食转 + w.账.越界C))
    ok("侏罗纪·水文守恒", dA < 1e-6 * max(A0, 1.0), f"差 {dA:.2e}")
    ok("侏罗纪·能量守恒", dB < 1e-6 * max(B0, 1.0), f"差 {dB:.2e}")
    ok("侏罗纪·器物守恒", dC < 1e-6 * max(C0, 1.0), f"差 {dC:.2e}")
    # 种群兴衰有序：有新生，亦有存续
    ok("侏罗纪·种群有继", len(w.animals) > 0,
       f"30 日存 {dict(collections.Counter(a.种类 for a in w.animals))}")


# ── 8.6 定率化单元探针（v8-P0：e 式衰减的签名）────────────
def test_rate_decay():
    from yidao_core.world import Item
    # 腐坏指数签名：率 × 存量（等效旧寿校准：平均寿命与旧制定额齐平）；
    # 阳永不负值；余烬判尽（指数永不归零，< 0.5 视为腐尽）
    a = Item("生鱼")          # 阳 30；校准率 0.09×ln(60)/30 ≈ 0.0123（气温 15 时系数 1.0）
    初 = a.阳
    步 = 0
    while not a.腐一步(15.0) and 步 < 100000:
        步 += 1
        assert a.阳 > 0.0, "定率衰减下阳永不负值"
    ok("定率·余烬判尽", 0.0 < a.阳 < 0.5, f"{步} 念后余 {a.阳:.3f}")
    ok("定率·平均寿命与旧制齐平", 300 < 步 < 400,
       f"生鱼 {步} 念腐尽（旧制定额 333 念；e 式衰减形变而寿不变）")
    # 半衰期签名：ln2/0.0123 ≈ 56 念后存量约半
    b = Item("生鱼")
    for _ in range(56):
        b.腐一步(15.0)
    ok("定率·半衰期签名", abs(b.阳 / 初 - 0.5) < 0.03, f"56 念后余 {b.阳 / 初:.3f}")


# ── 8.7 v8-P0 长程验收（60 日：制陶动机链不断、涌现仍发）──────
def test_v8_p0():
    ev = []
    s = Session.genesis(seed=2026, on_event=lambda **kw: ev.append(kw))
    s.run(TICKS_PER_DAY * 60)
    制陶 = sum(1 for e in ev if e["kind"] == "领悟" and "陶" in e["text"]) \
        + sum(1 for e in ev if e["kind"] == "制陶")
    ok("定率·制陶动机链不断", 制陶 >= 1, f"制陶相关 {制陶} 起")
    涌现 = sum(1 for e in ev if e["kind"] in ("涌现", "涌现反击"))
    ok("定率·涌现仍发生", 涌现 >= 1, f"涌现 {涌现} 起")
    # v8-P0B：塌屋/火熄仍发（危房与余烬的世代仍在）；
    # 井废 60 日内本就不发生（石工寿以百日计，旧制亦然）——断言放宽，理由已注于 commit
    塌 = sum(1 for e in ev if e["kind"] == "塌屋")
    熄 = sum(1 for e in ev if e["kind"] == "火熄")
    ok("定率·塌屋仍发生", 塌 >= 1, f"塌屋 {塌} 起")
    ok("定率·火熄仍发生", 熄 >= 1, f"火熄 {熄} 起")


# ── 9.5 五行相律（土与水）─────────────────────
def test_phases():
    w = World(seed=42)
    w.trees.clear()     # 相律自证：先清场，树木只按测试之意而立
    # 土相：被水侵蚀则湿为泥；水分大于泥则溃为沙；水少则干；水特别少则硬碎亦成沙
    w.water[:] = 0.0
    w.moisture[:] = 0.05
    ok("相律·极干为沙", w.土相(5, 5) == "沙")
    w.moisture[:] = 0.15
    ok("相律·水少为干", w.土相(5, 5) == "干")
    w.moisture[:] = 0.45
    ok("相律·适中为土", w.土相(5, 5) == "土")
    w.moisture[:] = 0.80
    ok("相律·水蚀为泥", w.土相(5, 5) == "泥")
    w.water[:] = 2.0
    ok("相律·水过溃沙", w.土相(5, 5) == "沙")
    # 水相：多则为流为海，少则为滴为气
    w.cloud[:] = 0.0
    w.water[:] = 0.3
    ok("相律·水少为滴", w.水相(5, 5) == "滴")
    w.water[:] = 1.0
    ok("相律·积水为流", w.水相(5, 5) == "流")
    w.water[:] = 2.5
    ok("相律·水巨为海", w.水相(5, 5) == "海")
    w.water[:] = 0.0
    w.cloud[:] = 0.8
    ok("相律·水蒸气为气", w.水相(5, 5) == "气")
    # 火相：星（将熄）/ 火 / 焰（旺）——烧制之事，需旺火方成
    from yidao_core.world import Fireplace
    w.fires.clear()
    ok("相律·无火为无", w.火相(5, 5) == "无")
    w.fires.append(Fireplace(5, 5, "测试", 阳=10.0))
    ok("相律·将熄为星", w.火相(5, 5) == "星")
    w.fires[0].阳 = 30.0
    ok("相律·常火为火", w.火相(5, 5) == "火")
    w.fires[0].阳 = 60.0
    ok("相律·旺火为焰", w.火相(5, 5) == "焰")
    # 木固土：近树之土，根柢盘结，纵极干亦不易溃为沙
    from yidao_core.world import Tree
    w.water[:] = 0.0
    w.moisture[:] = 0.05
    ok("相律·无树极干为沙", w.土相(5, 5) == "沙")
    w.trees.append(Tree(5, 5))
    ok("相律·木固土", w.土相(5, 5) == "干")
    # 果树结实：暖季渐熟（开缸即暖季之末，季相为正）
    t2 = Tree(8, 8, 50.0, 果树=True)
    w.trees.append(t2)
    for _ in range(400):
        w._物理步(预热=True)
    ok("相律·果树结实", t2.果数 > 0, f"果数 {t2.果数}")


# ── 9.6 组件独立（M2b：灵是一束可拆可立的组件）──────────
def test_components():
    from yidao_core.spirit import (Body, Genome, Mind, Desire, Knowledge,
                                   Property, Relations, Remembrance, Intel, Itinerary)
    for cls in (Body, Genome, Mind, Desire, Knowledge,
                Property, Relations, Remembrance, Intel, Itinerary):
        c = cls()      # 组件可独立实例化——脱离灵而立
        assert c is not None
    ok("组件·十组件独立可立", True)
    # 路由桥不吞字段：灵之扁平读写与组件读写是同一处
    s = Session.genesis(seed=42)
    x = s.spirits[0]
    x.yang = 55.0
    ok("组件·路由桥读写同一", x.身.yang == 55.0 and x.yang == x.身.yang,
       f"身.yang {x.身.yang}")
    x.心.mood["希望"] = 0.9
    ok("组件·心情路由同一", x.mood["希望"] == 0.9)


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
    test_rate_decay()
    test_v8_p0()
    test_phases()
    test_components()
    test_jurassic()
    test_stagnation_stir()
    print("─" * 40)
    print(f"全部通过（{PASS} 项断言）。世界的严密性已被断言，而非感觉。")
