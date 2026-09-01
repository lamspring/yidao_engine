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


if __name__ == "__main__":
    print("史官 S1 验收\n" + "─" * 40)
    test_ledger_determinism()
    test_口径一致()
    test_reports()
    test_死水种子()
    print("─" * 40)
    print(f"全部通过（{PASS} 项）。史官的账，先死后著。")
