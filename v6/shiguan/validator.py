# -*- coding: utf-8 -*-
"""
史官 · 校验器（validator.py）——考据完备与虚构扫描（§五，全部纯规则）。

两级校验：
1. 锚定完备性：正文每个自然段至少 1 个 [E{id}] 锚点；锚点 id 在该链节点集合内；
   考据表行数 = 正文段落数；考据表"事件原文"与事件簿 text 逐字一致。
2. 虚构扫描：人名白名单 ⊆ 链上 actor/target（代称须可解析回白名单）；
   禁词扫描（恰好/恰巧/冥冥中/命运的安排）；动机核查（动机句式的锚点事件
   调查所得中须有对应证据）。

教训在案（§4.4）：只做考据校验，不做创作指导。
"""
import re

_锚 = re.compile(r"\[E(\d+)\]")
_禁词 = ("恰好", "恰巧", "冥冥中", "命运的安排", "殊不知")
_动机句式 = ("因为", "为了", "他想", "他恨", "他要", "他想起了", "他记得")


class Validator:
    """吃一条链与一篇成篇，出违规清单（空 = 过）。"""

    def __init__(self, ledger, chain, inquest):
        self.ledger = ledger
        self.chain = chain
        self.inquest = inquest

    def validate(self, text: str) -> list[str]:
        v: list[str] = []
        v += self._锚定(text)
        v += self._虚构(text)
        return v

    # ── 一级：锚定完备性 ─────────────────────
    def _锚定(self, text: str) -> list[str]:
        v = []
        if "## 考据表" not in text:
            return ["无考据表：成篇缺考据表段"]
        正文, _, 表 = text.partition("## 考据表")
        段落 = [p for p in 正文.split("\n\n")
                if p.strip() and not p.strip().startswith(("#", "---", "|"))]
        锚集 = set(self.chain.nodes)
        表行 = [ln for ln in 表.splitlines() if ln.strip().startswith("|")
                and "锚定事件" not in ln and "---" not in ln]
        for i, p in enumerate(段落):
            锚 = _锚.findall(p)
            if not 锚:
                v.append(f"§{i + 1} 无锚点")
                continue
            for a in 锚:
                if int(a) not in 锚集:
                    v.append(f"§{i + 1} 锚点 E{a} 不在该链节点集合内")
        if len(表行) != len(段落):
            v.append(f"考据表行数（{len(表行)}）≠ 正文段落数（{len(段落)}）")
        # 事件回指：考据表原文与事件簿逐字一致
        for ln in 表行:
            cells = [c.strip() for c in ln.strip().strip("|").split("|")]
            if len(cells) < 4:
                v.append(f"考据表行格式不完整：{ln[:40]}")
                continue
            m = re.fullmatch(r"E(\d+)", cells[1])
            if not m:
                v.append(f"考据表锚点格式错：{cells[1]}")
                continue
            eid = int(m.group(1))
            原文 = cells[3].strip('"').strip()
            if eid >= len(self.ledger.events):
                v.append(f"考据表 E{eid} 超出事件簿")
                continue
            if 原文 != self.ledger.by_id(eid)["text"]:
                v.append(f"考据表 E{eid} 原文与事件簿不逐字一致")
        return v

    # ── 二级：虚构扫描 ──────────────────────
    def _虚构(self, text: str) -> list[str]:
        v = []
        正文 = text.partition("## 考据表")[0]
        # 人名白名单：链上 actor/target + 可解析代称（X之子 → X 在簿）
        白 = set(self.chain.actors)
        for m in re.finditer(r"([\u4e00-\u9fff]{1,4})之子", 正文):
            if m.group(1) in 白:
                白.add(m.group(0))
        众名 = {x.name for x in self.inquest.spirits}
        for name in 众名:
            if name in 白:
                continue
            # 该名以独立成分出现（非代称、非子串）才算越界
            for m in re.finditer(re.escape(name), 正文):
                后 = 正文[m.end():m.end() + 2]
                if 后.startswith("之子"):
                    continue
                v.append(f"人名越界：{name} 不在该链白名单")
                break
        for w in _禁词:
            if w in 正文:
                v.append(f"禁词出现（人工复核）：{w}")
        # 动机核查：动机句式的锚点事件，调查所得中须有证据（读数/快照/旁证）
        for p in [p for p in 正文.split("\n\n") if p.strip()]:
            if not any(k in p for k in _动机句式):
                continue
            for a in _锚.findall(p):
                r = self.inquest.why(int(a))
                有据 = bool(r["readings"]) or r["actor_mind"] is not None \
                    or bool(r["旁证"])
                if not 有据:
                    v.append(f"动机句无据：锚点 E{a} 的调查所得为空")
        return v
