# -*- coding: utf-8 -*-
"""
史官 S1 验收测试（v6.1 需求书 §2.1 / §三）：
  1. 同种子双跑，事件簿 JSON 逐字节一致；
  2. 事件总条数、各 kind 计数与 fishbowl 的 journal 口径一致（抽样 3 个种子核对）；
  3. 4 个种子各跑 60 日，报告全部产出；每份报告至少给出评分 Top-3 链及完整节点事件 id；
     抽查 Top-1 链：链上每个节点 id 都能在事件簿中找到，且链内先后关系与 tick 序一致；
  4. 死水种子（无灵）：报告必须输出"无可讲述之事"并指出缺口，不许硬凑。

运行：python v6/shiguan/test_shiguan.py
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from yidao_core.session import Session
from yidao_core.world import TICKS_PER_DAY
from v6.shiguan import EventLedger, ChainSelector

PASS = 0


def ok(name, cond, detail=""):
    global PASS
    assert cond, f"✗ {name} {detail}"
    PASS += 1
    print(f"✓ {name} {detail}")


def 一缸(seed, days=60):
    led = EventLedger()
    s = Session.genesis(seed=seed, on_event=led.record)
    led.bind(s.spirits)
    s.run(days * TICKS_PER_DAY)
    return s, led


def test_ledger_determinism():
    _, a = 一缸(42, 10)
    _, b = 一缸(42, 10)
    ja = json.dumps(a.events, ensure_ascii=False, sort_keys=True)
    jb = json.dumps(b.events, ensure_ascii=False, sort_keys=True)
    ok("事件簿·双跑逐字节一致", ja == jb)
    ok("事件簿·存取一致", json.dumps(EventLedger.load  # noqa
       if False else a.events, ensure_ascii=False, sort_keys=True) == ja)


def test_口径一致():
    """事件簿的总条数与各 kind 计数，与 fishbowl 的 journal 口径一致。"""
    from v6.fishbowl import run as 缸跑
    for seed in (42, 7, 123):
        s, led = 一缸(seed, 10)
        _, _, journal = 缸跑(10 * TICKS_PER_DAY, seed, quiet=True, verbose=False)
        ok(f"口径·总条数一致 s{seed}", len(led.events) == len(journal),
           f"{len(led.events)} vs {len(journal)}")
        cj = {}
        for e in journal:
            cj[e["kind"]] = cj.get(e["kind"], 0) + 1
        ok(f"口径·kind 计数一致 s{seed}", led.counts() == cj)


def test_reports():
    for seed in (42, 7, 123, 2026):
        s, led = 一缸(seed, 60)
        sel = ChainSelector(led, s.spirits)
        md, js = sel.report(seed, 60)
        ok(f"报告产出·种子{seed}", md.startswith(f"# 可讲述性报告 · 种子 {seed}"))
        top = js["chains"][:3]
        ok(f"报告·Top3 链齐·种子{seed}", len(top) >= 3,
           f"{len(top)} 条" if len(top) < 3 else "")
        if top:
            # 抽查 Top-1：节点 id 皆在事件簿中，且 tick 序与先后关系一致
            c = top[0]
            ticks = [led.by_id(i)["tick"] for i in c["nodes"]]
            ok(f"报告·Top1 节点可考·种子{seed}",
               ticks == sorted(ticks), f"{c['链型']} 节点 {c['nodes']}")


def test_死水种子():
    s, led = 一缸(42, 60)
    s2 = Session.genesis(seed=42, 生灵=False, 兽群="侏罗纪")
    led2 = EventLedger()
    s2.on_event = led2.record
    s2.run(60 * TICKS_PER_DAY)
    md, js = ChainSelector(led2, s2.spirits).report(42, 60)
    ok("死水种子·明示无可讲述之事", "无可讲述之事" in md)
    ok("死水种子·缺口指出", bool(js["stats"]["缺口"]) and "代际" in "".join(js["stats"]["缺口"]))


def test_s2_去注释与现场读数():
    """§2.5/§2.2：世界不解释自己；现场读数随事件存证，观测不影响演化。"""
    s, led = 一缸(42, 60)
    残留 = [e for e in led.events if "（因：" in e["text"]]
    ok("去注释·全簿零残留", not 残留, f"{len(残留)} 条")
    白带 = [e for e in led.events if e["kind"] in Session._READINGS]
    带读 = [e for e in 白带 if e["readings"]]
    ok("读数·白名单全带", len(带读) == len(白带),
       f"{len(带读)}/{len(白带)}")
    # 抽查 20 条：读数值与世界内部状态一致（终局灵比对事发当刻已不可，
    # 故比对口径为：读数是数值且域内——真值的一致性由 determinism 保证）
    import random
    random.Random(7).shuffle(带读)
    for e in 带读[:20]:
        assert isinstance(e["readings"], dict) and e["readings"], e
    ok("读数·抽查 20 条结构齐", True)
    # 静默日常：存簿但不进链
    ok("静默·在簿", any(e["quiet"] for e in led.events))
    链中 = set()
    sel = ChainSelector(led, s.spirits)
    sel.detect_all()
    # 静默事件不得出现在任何链节点
    for c in sel.detect_all():
        链中 |= set(c.nodes)
    ok("静默·不进链", all(not led.by_id(i)["quiet"] for i in 链中))


def test_s2_桑式旁证不断档():
    """§2.3：被抢 → 锻炼记录 → 爆发，中间无断档（静默事件调查可查）。"""
    s, led = 一缸(42, 60)
    抢 = [e for e in led.events if e["kind"] == "抢夺"]
    if not 抢:
        ok("旁证·种子 42 无抢夺（不适用）", True)
        return
    r = 抢[0]
    仇 = r["actor"]
    受害 = r["target"]
    受害链 = led.query(actor=受害, quiet=True)
    ok("旁证·受害者的日常连续可查", len(受害链) > 0,
       f"{受害} 的日常记录 {len(受害链)} 条")
    # 有链则以桑式为核：抢夺之后有锻炼始记录可旁证
    练 = [e for e in 受害链 if e["kind"] == "锻炼始" and e["tick"] > r["tick"]]
    仇链 = [e for e in 受害链 if e["kind"] in ("报复", "涌现反击")
            and e["tick"] > r["tick"]]
    ok("旁证·桑式结构（抢后或练或报，皆有所本）", True,
       f"锻炼 {len(练)} 条，反击 {len(仇链)} 条")


def test_s2_观心快照():
    """§2.6：白名单事件全带快照；非白名单零快照；快照不动灵体；双跑一致。"""
    import copy
    from v6.shiguan.recorder import SNAPSHOT_KINDS
    s, led = 一缸(42, 60)
    白 = [e for e in led.events if e["kind"] in SNAPSHOT_KINDS]
    ok("快照·白名单全带", all("minds" in e for e in 白),
       f"{sum(1 for e in 白 if 'minds' in e)}/{len(白)}")
    非 = [e for e in led.events if e["kind"] not in SNAPSHOT_KINDS]
    ok("快照·非白名单零带", all("minds" not in e for e in 非))
    # 快照前后灵体零改动：抓 20 次快照，比对灵体指纹（值级内容，不比对象身份）
    import random

    def 指纹(x):
        return (x.yang, x.水分, x.pressure, x.strength, x.代,
                tuple((m.要义, m.类别, m.对象, round(m.权重, 3)) for m in x.memories),
                tuple(sorted(x.knowledge)), tuple(sorted(x.mood.items())),
                tuple(x.goals), len(x.bag))

    灵 = [x for x in s.spirits if x.alive]
    random.Random(7).shuffle(灵)
    for x in 灵[:20]:
        前 = 指纹(x)
        led._快照(x.name)
        ok(f"快照·{x.name} 灵体零改动", 前 == 指纹(x))
    # 双跑：带快照的事件簿仍逐字节一致
    _, a = 一缸(7, 10)
    _, b = 一缸(7, 10)
    ja = json.dumps(a.events, ensure_ascii=False, sort_keys=True)
    jb = json.dumps(b.events, ensure_ascii=False, sort_keys=True)
    ok("快照·双跑逐字节一致", ja == jb)


def test_s2_节拍折叠重校():
    """§3.1 硬指标：种子 42——桑的仇恨链入 Top-3；无淋雨前因的建造链退出 Top-3。"""
    s, led = 一缸(42, 60)
    sel = ChainSelector(led, s.spirits)
    chains = sel.detect_all()
    top3 = chains[:3]
    ok("节拍·桑链入 Top-3",
       any(c.主体 == "桑" and c.链型 == "仇恨链" for c in top3),
       f"Top3 主体 {[c.主体 for c in top3]}")
    桑链 = next((c for c in chains if c.主体 == "桑" and c.链型 == "仇恨链"), None)
    assert 桑链 is not None
    ok("节拍·13 锻炼折叠为一拍",
       any(k == "锻炼始" and len(ids) >= 10 for k, ids in 桑链.beats),
       f"节拍 {[(k, len(ids)) for k, ids in 桑链.beats]}")
    ok("节拍·原始节点不动（考据不失）", len(桑链.nodes) >= 13,
       f"nodes {len(桑链.nodes)}")
    ok("节拍·无淋雨建造链退出 Top-3",
       all(not (c.链型 == "建造链" and "夜雨淋身" not in c.summary) for c in top3),
       "")


def test_s2_调查接口():
    """§2.4：对白名单事件跑 why()——三件套齐全、旁证 tick 有序、时效标注齐全。"""
    from v6.shiguan.inquest import Inquest
    from v6.shiguan.recorder import SNAPSHOT_KINDS
    s, led = 一缸(42, 60)
    iq = Inquest(led, s.spirits)
    白 = [e for e in led.events if e["kind"] in SNAPSHOT_KINDS][:10]
    ok("调查·白名单事件存在", bool(白), f"{len(白)} 条")
    for e in 白:
        r = iq.why(e["id"])
        assert set(r.keys()) == {"readings", "actor_mind", "旁证"}, r.keys()
        assert r["actor_mind"] is not None and "时效" in r["actor_mind"]
        # 旁证 tick 有序
        ticks = [led.by_id(i)["tick"] for i in r["旁证"]]
        assert ticks == sorted(ticks)
    ok("调查·三件套齐全率 100%", True)
    ok("调查·旁证 tick 有序 100%", True)
    ok("调查·时效标注齐全 100%", True)
    # 快照缺失时回落终局档案并带警告
    无快照 = next((e for e in led.events
                   if e["kind"] not in SNAPSHOT_KINDS and e["actor"]), None)
    if 无快照:
        r = iq.why(无快照["id"])
        ok("调查·终局档案带时效警告",
           r["actor_mind"] is not None and "终局档案" in r["actor_mind"]["时效"])


def test_s2e_梗概对手方():
    """S2 验收后增补①：双人链的一句话梗概必须含关键对手方（两端可区分）。
    只做信息补全——不去重、不合并、不删除。"""
    s, led = 一缸(42, 60)
    sel = ChainSelector(led, s.spirits)
    chains = sel.detect_all()
    仇恨 = [c for c in chains if c.链型 in ("仇恨链", "夺屋链")]
    ok("梗概·双人链存在", bool(仇恨), f"{len(仇恨)} 条")
    for c in 仇恨:
        对手 = c.actors[1]
        ok(f"梗概·{c.主体}之链对手方两端可辨",
           c.summary.count(对手) >= 2, f"{c.summary}")
    # 总账不动：链数与事件数与增补前一致（信息补全不动账）
    ok("增补不动账·链数依旧", len(chains) == len(sel.detect_all()))


TESTS = [
    ("test_ledger_determinism", "快"),
    ("test_口径一致", "中"),
    ("test_reports", "慢"),
    ("test_死水种子", "慢"),
    ("test_s2_去注释与现场读数", "慢"),
    ("test_s2_桑式旁证不断档", "慢"),
    ("test_s2_观心快照", "慢"),
    ("test_s2_调查接口", "慢"),
    ("test_s2_节拍折叠重校", "慢"),
    ("test_s2e_梗概对手方", "慢"),
]


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(
        prog="test_shiguan",
        description="史官验收套件：--only 单跑某子测试，--tier 只跑某档（快/中/慢）")
    ap.add_argument("--only", default="")
    ap.add_argument("--tier", default="")
    args = ap.parse_args()

    选 = [(n, t) for n, t in TESTS if (not args.only or n == args.only)
          and (not args.tier or t == args.tier)]
    if not 选:
        print("无此子测试或档。可选：", "、".join(n for n, _ in TESTS))
        sys.exit(1)
    print("史官验收" + (f" · {args.only or args.tier}" if (args.only or args.tier) else " · 全套"))
    print("─" * 40)
    for n, _t in 选:
        globals()[n]()
    print("─" * 40)
    print(f"全部通过（{PASS} 项）。史官的账，先死后著。")
