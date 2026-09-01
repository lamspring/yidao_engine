# -*- coding: utf-8 -*-
"""
史官 · 记录仪（recorder.py）——事件簿。

世界只存此刻；史官的事件簿是"世界之外、观测层自负盈亏"的史。
第一性原理：原样存录，不做任何加工。text 一字不改，extra 原样保留。
加工是下游的事。

用法：
    ledger = EventLedger()
    session = Session.genesis(seed=42, on_event=ledger.record)
    session.run(...)
"""

import json

from yidao_core.world import TICKS_PER_DAY


# 静默日常白名单（§2.3）：存簿但默认不进报告、不进链、不进评分，仅调查接口可调。
# 锻炼始不在其列：它是"立志"的抉择事件，是仇恨链的蓄势节拍——非日常琐事。
QUIET_KINDS = {"进食", "饮水", "生食致病", "受冻", "淋雨"}


class EventLedger:
    """事件簿：结构化地记下世界发来的每一条事件。"""

    def __init__(self):
        self.events: list[dict] = []

    def record(self, tick, pos, text, kind, actor=None, target=None,
               readings=None, **extra):
        """on_event 回调：原样存录。id 即序号（世界确定性 → 序号即唯一锚）。
        readings：现场读数（§2.2），无则 None；quiet：静默日常（§2.3）。"""
        self.events.append({
            "id": len(self.events),
            "tick": tick,
            "day": tick // TICKS_PER_DAY + 1,
            "pos": list(pos) if pos is not None else None,
            "kind": kind,
            "actor": actor,
            "target": target,
            "text": text,
            "readings": readings,
            "quiet": kind in QUIET_KINDS,
            "extra": dict(extra),
        })

    # ── 查询（供选链器）──────────────────────
    def query(self, kind=None, actor=None, target=None, t0=None, t1=None,
              quiet=False) -> list:
        """按 kind / actor / target / 时间窗 [t0, t1) 过滤，保持原序。
        静默日常默认不见（quiet=True 才见）——调查接口的门。"""
        out = self.events if quiet else [e for e in self.events if not e["quiet"]]
        if kind is not None:
            ks = {kind} if isinstance(kind, str) else set(kind)
            out = [e for e in out if e["kind"] in ks]
        if actor is not None:
            out = [e for e in out if e["actor"] == actor]
        if target is not None:
            out = [e for e in out if e["target"] == target]
        if t0 is not None:
            out = [e for e in out if e["tick"] >= t0]
        if t1 is not None:
            out = [e for e in out if e["tick"] < t1]
        return out

    def by_id(self, event_id: int) -> dict:
        return self.events[event_id]

    def counts(self) -> dict:
        """各 kind 计数（口径核对用）。"""
        out = {}
        for e in self.events:
            out[e["kind"]] = out.get(e["kind"], 0) + 1
        return out

    # ── 序列化：同种子双跑逐字节一致 ──────────
    def save(self, path: str):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.events, f, ensure_ascii=False, sort_keys=True,
                      indent=1)

    @classmethod
    def load(cls, path: str) -> "EventLedger":
        led = cls()
        with open(path, encoding="utf-8") as f:
            led.events = json.load(f)
        return led
