# -*- coding: utf-8 -*-
"""
史官 · 选链器（selector.py）——可讲述性报告（纯规则，零 LLM）。

选题原则：链优先，不是时间线流水账。一篇好故事 = 一条有起承转合的因果链。

本模块把 v6/fishbowl.py 的 find_* 系列迁移为消费 EventLedger 的结构化链检测：
每条链的节点 = 事件 id 序列（可考据），附可讲述性评分与世界丰富度体检。

杀手特性：可讲述性报告 = 世界丰富度体检仪表盘——
史官写不出好链不是史官的问题，是世界哪里不够丰富的信号。
"""

from dataclasses import dataclass, field

from yidao_core.world import TICKS_PER_DAY

# ── 情感极性（恩/仇/生/死）与结局闭合 ──
_恩 = {"分享", "救助", "庇护", "还债", "澄清", "两清", "同悼", "渡阳", "结为伴侣"}
_仇 = {"抢夺", "战斗", "报复", "涌现反击", "赖账", "夺屋成", "谎言戳穿", "传闻失真"}
_生 = {"诞育", "生", "点化"}
_死 = {"死亡", "寿终", "悼念"}
# 闭合结局：死亡/离去/和解/事成/得法/报复
_闭合 = {"死亡", "寿终", "还债", "澄清", "两清", "报仇成", "夺回", "迁抵",
         "建成", "取火", "制陶", "渡阳", "结为伴侣", "井成", "报复", "涌现反击"}


def day_of(tick: int) -> int:
    return tick // TICKS_PER_DAY + 1


@dataclass
class Chain:
    """一条因果链：节点 = 事件 id 序列（可考据）；节拍 = 折叠后的叙事单位。"""
    链型: str
    主体: str
    nodes: list[int]
    summary: str
    actors: list[str] = field(default_factory=list)
    beats: list = field(default_factory=list)   # [(kind, [ids...])] 节拍折叠视图
    score_detail: dict = field(default_factory=dict)
    score: float = 0.0


def _polarity(kinds: list[str]) -> float:
    span = (bool(set(kinds) & _恩) + bool(set(kinds) & _仇)
            + bool(set(kinds) & _生) + bool(set(kinds) & _死))
    return span / 4.0


def _fold(byid, nodes: list[int]) -> list:
    """节拍折叠（v6.1 §3.1）：同类连续节点折叠为一节拍。
    折叠是评分层的视图变换——事件簿与链的原始节点不动（考据仍指原始事件 id）。
    返回 [(kind, [ids...])]，如 13 条锻炼始 → 1 个"蓄势"节拍。"""
    beats = []
    for i in nodes:
        e = byid[i]
        if beats and beats[-1][0] == e["kind"]:
            beats[-1][1].append(i)
        else:
            beats.append((e["kind"], [i]))
    return beats


def _score(byid, beats: list) -> tuple[dict, float]:
    """可讲述性评分（§3.1：按节拍重算）：
    长度/转折/情感跨度/结局闭合皆以节拍为单位；
    动机可得率 = 可调出现场读数或观心快照的节拍占比（真值，S2 起）。"""
    kinds = [k for k, _ in beats]
    n = len(beats)
    # 长度：3~8 节拍为佳；过短无事（n<3 线性递减），过长难讲（n>8 渐减）
    长度 = (1.0 if 3 <= n <= 8 else n / 3.0 if n < 3
            else max(0.0, 1.0 - (n - 8) / 8.0))
    转折 = min(1.0, max(0, len(set(kinds)) - 1) / 3.0)
    跨度 = _polarity(kinds)
    闭合 = 1.0 if kinds and kinds[-1] in _闭合 else 0.3
    有 = sum(1 for _, ids in beats
             if any(byid[i].get("readings") or "minds" in byid[i] for i in ids))
    动机 = round(有 / max(1, n), 2)
    detail = {"长度": round(长度, 2), "转折": round(转折, 2), "情感跨度": round(跨度, 2),
              "结局闭合": round(闭合, 2), "动机可得率": 动机}
    total = 0.20 * 长度 + 0.25 * 转折 + 0.20 * 跨度 + 0.20 * 闭合 + 0.15 * 动机
    return detail, round(total, 3)


class ChainSelector:
    """吃事件簿（+众灵只读引用），出结构化链与可讲述性报告。"""

    def __init__(self, ledger, spirits):
        self.ledger = ledger
        self.spirits = spirits
        # 静默日常不进链不进报告（§2.3）：选链只见非静默事件；
        # 但节点 id 是全簿的序号——byid 保持全簿索引（考据之锚不失）
        self.E = [e for e in ledger.events if not e.get("quiet")]
        self.byid = {e["id"]: e for e in ledger.events}

    # ═══════════ 链检测（自 fishbowl find_* 迁移改造）═══════════

    def 仇恨链(self) -> list[Chain]:
        """被抢 → 铭记 → 锻炼 → 报复/临界反击。"""
        out = []
        seen = set()
        for r in self.E:
            if r["kind"] != "抢夺":
                continue
            v, rob, t = r["target"], r["actor"], r["tick"]
            if (v, rob) in seen:
                continue
            主 = next((s for s in self.spirits if s.name == v), None)
            if 主 is None:
                continue
            铭记 = any(m.永存 and m.类别 in ("被抢", "受辱") and m.对象 == rob
                       for m in 主.memories)
            报仇 = next((e for e in self.E
                         if e["kind"] in ("报复", "涌现反击")
                         and e["actor"] == v and e["target"] == rob and e["tick"] > t),
                        None)
            if not (铭记 and 报仇):
                continue
            seen.add((v, rob))
            nodes = [r["id"]]
            锻炼 = [e["id"] for e in self.E
                    if e["kind"] == "锻炼始" and e["actor"] == v
                    and t < e["tick"] < 报仇["tick"]]
            nodes += 锻炼
            nodes.append(报仇["id"])
            标签 = "报复" if 报仇["kind"] == "报复" else "临界反击"
            out.append(Chain("仇恨链", v, nodes,
                             f"{v}: 被抢(第{day_of(t)}日) → 铭记 → "
                             f"{标签}{rob}(第{day_of(报仇['tick'])}日)",
                             [v, rob]))
        return out

    def 恩义链(self) -> list[Chain]:
        """分享/救助 → 铭记 → 互助（回报分享/挺身相护/悼念）。"""
        out = []
        seen = set()
        for e in self.E:
            if e["kind"] not in ("分享", "救助"):
                continue
            a, b, t = e["actor"], e["target"], e["tick"]
            if (a, b) in seen:
                continue
            受恩者 = next((s for s in self.spirits if s.name == b), None)
            if 受恩者 is None:
                continue
            铭记 = any(m.对象 == a and m.类别 == "受助" for m in 受恩者.memories)
            if not 铭记:
                continue
            回报 = next((x for x in self.E
                         if x["tick"] > t and x["actor"] == b and x["target"] == a
                         and x["kind"] in ("分享", "救助", "庇护", "悼念")), None)
            if 回报 is None:
                continue
            seen.add((a, b))
            标签 = {"分享": "回报分享", "救助": "回报救助",
                    "庇护": "挺身相护", "悼念": "悼念"}[回报["kind"]]
            out.append(Chain("恩义链", b, [e["id"], 回报["id"]],
                             f"{b}: 受{a}之恩(第{day_of(t)}日) → 铭记 → "
                             f"{标签}{a}(第{day_of(回报['tick'])}日)",
                             [a, b]))
        return out

    def 建造链(self) -> list[Chain]:
        """淋雨 → 领悟/学会建造 → 采集 → 建成 → 他人模仿。"""
        out = []
        for s in self.spirits:
            淋雨 = next((e for e in self.E
                         if e["kind"] == "淋雨" and e["actor"] == s.name), None)
            得法 = next((e for e in self.E
                         if "建造" in e["text"]
                         and ((e["kind"] in ("领悟", "模仿") and e["actor"] == s.name)
                              or (e["kind"] == "传授" and e["target"] == s.name))), None)
            建成 = next((e for e in self.E
                         if e["kind"] == "建成" and e["actor"] == s.name), None)
            if not (得法 and 建成):
                continue
            法名 = {"领悟": "自悟建造", "模仿": "观察学会建造",
                    "传授": "受教建造"}[得法["kind"]]
            nodes = ([淋雨["id"]] if 淋雨 else []) + [得法["id"]]
            采集 = [e["id"] for e in self.E
                    if e["kind"] == "采集" and e["actor"] == s.name
                    and 得法["tick"] <= e["tick"] <= 建成["tick"]]
            nodes += 采集[:6]      # 采集为重复事件, 至多取六节
            nodes.append(建成["id"])
            扩散 = next((e for e in self.E
                         if e["kind"] in ("模仿", "传授") and "建造" in e["text"]
                         and e["tick"] > 建成["tick"]
                         and (e["actor"] != s.name or e["target"] == s.name)), None)
            parts = ([f"夜雨淋身(第{day_of(淋雨['tick'])}日)"]
                     if 淋雨 and 淋雨["tick"] < 得法["tick"] else []) \
                + [f"{法名}(第{day_of(得法['tick'])}日)",
                   f"茅屋建成(第{day_of(建成['tick'])}日)"]
            if 扩散 is not None:
                nodes.append(扩散["id"])
                谁 = 扩散["actor"] if 扩散["kind"] == "模仿" else 扩散["target"]
                parts.append(f"{谁}效仿(第{day_of(扩散['tick'])}日)")
            out.append(Chain("建造链", s.name, nodes,
                             f"{s.name}: " + " → ".join(parts), [s.name]))
        return out

    def 夺屋链(self) -> list[Chain]:
        """被夺屋 → 铭记 → 锻炼 → 夺回/报复。"""
        out = []
        for e in self.E:
            if e["kind"] != "夺屋成":
                continue
            v, rob, t = e["target"], e["actor"], e["tick"]
            主 = next((s for s in self.spirits if s.name == v), None)
            if 主 is None:
                continue
            铭记 = any(m.永存 and m.类别 == "夺屋" and m.对象 == rob for m in 主.memories)
            后报 = next((x for x in self.E
                         if x["kind"] in ("夺回", "报复", "涌现反击")
                         and x["actor"] == v and x["target"] == rob and x["tick"] > t),
                        None)
            if not (铭记 and 后报):
                continue
            nodes = [e["id"]]
            锻炼 = [x["id"] for x in self.E
                    if x["kind"] == "锻炼始" and x["actor"] == v
                    and t < x["tick"] < 后报["tick"]]
            nodes += 锻炼 + [后报["id"]]
            标签 = "夺回" if 后报["kind"] == "夺回" else "报复"
            out.append(Chain("夺屋链", v, nodes,
                             f"{v}: 被夺屋(第{day_of(t)}日) → 铭记 → "
                             f"{标签}{rob}(第{day_of(后报['tick'])}日)", [v, rob]))
        return out

    def _得法事件(self, name: str, skill: str):
        for e in self.E:
            if skill not in e["text"]:
                continue
            if e["kind"] in ("领悟", "模仿") and e["actor"] == name:
                return e
            if e["kind"] == "传授" and e["target"] == name:
                return e
        return None

    def 技能链(self) -> list[Chain]:
        """器物链 / 取火链 / 畜牧链：发明 → 制成/得火/驯化 → 使用 → 传播。"""
        out = []
        for s in self.spirits:
            得法 = self._得法事件(s.name, "制器")
            制成 = next((e for e in self.E
                         if e["kind"] == "制器" and e["actor"] == s.name), None)
            if 得法 and 制成:
                nodes = [得法["id"], 制成["id"]]
                parts = [f"悟得制器(第{day_of(得法['tick'])}日)",
                         f"制成器物(第{day_of(制成['tick'])}日)"]
                传播 = next((e for e in self.E
                             if e["tick"] > 制成["tick"] and "制器" in e["text"]
                             and ((e["kind"] in ("模仿", "领悟") and e["actor"] != s.name)
                                  or (e["kind"] == "传授" and e["actor"] == s.name))),
                            None)
                if 传播:
                    nodes.append(传播["id"])
                    谁 = 传播["actor"] if 传播["kind"] != "传授" else 传播["target"]
                    parts.append(f"{谁}习得(第{day_of(传播['tick'])}日)")
                out.append(Chain("器物链", s.name, nodes,
                                 f"{s.name}: " + " → ".join(parts), [s.name]))
            受冻 = next((e for e in self.E
                         if e["kind"] == "受冻" and e["actor"] == s.name), None)
            得火法 = self._得法事件(s.name, "取火")
            得火 = next((e for e in self.E
                         if e["kind"] == "取火" and e["actor"] == s.name), None)
            if 得火法 and 得火:
                nodes = ([受冻["id"]] if 受冻 else []) + [得火法["id"], 得火["id"]]
                parts = ([f"寒夜受冻(第{day_of(受冻['tick'])}日)"] if 受冻 else []) \
                    + [f"悟取火(第{day_of(得火法['tick'])}日)",
                       f"钻木得火(第{day_of(得火['tick'])}日)"]
                熟食 = next((e for e in self.E
                             if e["kind"] == "烹食初" and e["actor"] == s.name
                             and e["tick"] > 得火["tick"]), None)
                if 熟食:
                    nodes.append(熟食["id"])
                    parts.append(f"始知熟食(第{day_of(熟食['tick'])}日)")
                out.append(Chain("取火链", s.name, nodes,
                                 f"{s.name}: " + " → ".join(parts), [s.name]))
            得畜法 = self._得法事件(s.name, "畜牧")
            驯化 = next((e for e in self.E
                         if e["kind"] == "驯化" and e["actor"] == s.name), None)
            if 得畜法 and 驯化:
                nodes = [得畜法["id"], 驯化["id"]]
                parts = [f"悟畜牧(第{day_of(得畜法['tick'])}日)",
                         f"驯化入栏(第{day_of(驯化['tick'])}日)"]
                收产 = next((e for e in self.E
                             if e["kind"] in ("收蛋", "挤奶") and e["actor"] == s.name
                             and e["tick"] > 驯化["tick"]), None)
                if 收产:
                    nodes.append(收产["id"])
                    parts.append(f"{收产['kind']}(第{day_of(收产['tick'])}日)")
                out.append(Chain("畜牧链", s.name, nodes,
                                 f"{s.name}: " + " → ".join(parts), [s.name]))
        return out

    def 家族链(self) -> list[Chain]:
        """家族链：诞育事件为节点（可考据），谱系自众灵子女关系（只读）。"""
        out = []
        for s in self.spirits:
            if s.代 != 0 or not s.子女:
                continue
            nodes = [e["id"] for e in self.E
                     if e["kind"] == "诞育" and e["target"] in s.子女]
            nodes += [e["id"] for e in self.E
                      if e["kind"] in ("死亡", "寿终")
                      and e["actor"] in [s.name] + list(s.子女)]
            nodes.sort(key=lambda i: self.byid[i]["tick"])
            if not nodes:
                continue
            卒 = sum(1 for e in ((self.byid[i] for i in nodes)) if e["kind"] in ("死亡", "寿终"))
            out.append(Chain("家族链", s.name, nodes,
                             f"{s.name} 一门：诞育 {len(s.子女)} 口，亡故 {卒} 人",
                             [s.name] + list(s.子女)))
        return out

    def 债务链(self) -> list[Chain]:
        """借贷 → 还债（善）或 赖账 → 反目（恶）。"""
        out = []
        seen = set()
        for e in self.E:
            if e["kind"] != "借贷":
                continue
            a, b, t = e["actor"], e["target"], e["tick"]
            if (a, b) in seen:
                continue
            还 = next((x for x in self.E if x["kind"] == "还债"
                       and x["actor"] == b and x["target"] == a and x["tick"] > t), None)
            赖 = next((x for x in self.E if x["kind"] == "赖账"
                       and x["actor"] == b and x["target"] == a and x["tick"] > t), None)
            if 还 is not None:
                seen.add((a, b))
                out.append(Chain("债务链", b, [e["id"], 还["id"]],
                                 f"{b}: 受{a}借贷之惠(第{day_of(t)}日) → 铭记 → "
                                 f"还债两清(第{day_of(还['tick'])}日)", [a, b]))
            elif 赖 is not None:
                seen.add((a, b))
                反目 = next((x for x in self.E if x["tick"] > 赖["tick"]
                             and x["kind"] in ("抢夺", "战斗")
                             and {x["actor"], x["target"]} == {a, b}), None)
                nodes = [e["id"], 赖["id"]] + ([反目["id"]] if 反目 else [])
                尾 = f" → 反目成仇(第{day_of(反目['tick'])}日)" if 反目 else ""
                out.append(Chain("债务链", b, nodes,
                                 f"{b}: 受{a}借贷之惠(第{day_of(t)}日) → "
                                 f"赖账生怨(第{day_of(赖['tick'])}日){尾}", [a, b]))
        return out

    def _疑案结局(self, 疑者: str, 事主: str, t: int):
        """一桩疑案的结局：事主剖白（澄清），或双方交恶（谎言戳穿/抢夺/战斗/报复）。"""
        澄清 = next((x for x in self.E if x["kind"] == "澄清"
                     and x["actor"] == 事主 and x["target"] == 疑者 and x["tick"] > t),
                    None)
        if 澄清 is not None:
            return ("澄清冰释", 澄清["tick"], 澄清["id"])
        冲突 = next((x for x in self.E if x["tick"] > t
                     and x["kind"] in ("谎言戳穿", "抢夺", "战斗", "报复", "涌现反击")
                     and {x["actor"], x["target"]} == {疑者, 事主}), None)
        if 冲突 is not None:
            return ("结仇", 冲突["tick"], 冲突["id"])
        return None

    def 传闻链(self) -> list[Chain]:
        """传闻（失真）→ 听者生疑/误会 → 澄清或结仇；另收骨旁生疑的误会链。"""
        out = []
        seen = set()
        for e in self.E:
            if e["kind"] not in ("传闻", "传闻失真") or not e["extra"].get("subject"):
                continue
            teller = e["actor"]
            listener, subj, t = e["target"], e["extra"]["subject"], e["tick"]
            if (listener, subj) in seen:
                continue
            if "打死" not in e["text"] and not any(
                    k in e["text"] for k in ("抢掠", "打垮", "行过凶", "夺过",
                                              "欠债不还", "坑人", "口吐谎言", "行止不端")):
                continue
            结局 = self._疑案结局(listener, subj, t)
            if 结局 is None:
                continue
            seen.add((listener, subj))
            失真 = ", 失真" if e["kind"] == "传闻失真" else ""
            out.append(Chain("传闻链", listener, [e["id"], 结局[2]],
                             f"{listener}: 听{teller}传闻{subj}(第{day_of(t)}日{失真}) → "
                             f"疑心生暗鬼 → {结局[0]}(第{day_of(结局[1])}日)",
                             [teller, listener, subj]))
        for e in self.E:
            if e["kind"] != "误会":
                continue
            疑者, 嫌, t = e["actor"], e["target"], e["tick"]
            if (疑者,  嫌) in seen:
                continue
            结局 = self._疑案结局(疑者,  嫌, t)
            if 结局 is None:
                continue
            seen.add((疑者,  嫌))
            故 = e["extra"].get("subject") or "故人"
            out.append(Chain("误会链", 疑者,  [e["id"], 结局[2]],
                             f"{疑者}: 见{嫌}在{故}遗骨旁，疑其为凶(第{day_of(t)}日) → "
                             f"{结局[0]}(第{day_of(结局[1])}日)", [疑者,  嫌]))
        return out

    def 迁徙链(self) -> list[Chain]:
        """迁徙节：弃宅（迁徙）与落脚（迁抵）相配。"""
        out = []
        for e in self.E:
            if e["kind"] != "迁徙":
                continue
            抵 = next((x for x in self.E if x["kind"] == "迁抵"
                       and x["actor"] == e["actor"] and x["tick"] >= e["tick"]), None)
            # 因注：世界层观测性改造后, 迁徙之由存于 extra["因注"]（世界不解释自己）
            因 = e["extra"].get("因注", "")
            nodes = [e["id"]] + ([抵["id"]] if 抵 else [])
            尾 = (f" → 第{day_of(抵['tick'])}日抵{抵.get('pos')}" if 抵
                  else " → 至世界尽头仍未落脚")
            out.append(Chain("迁徙链", e["actor"], nodes,
                             f"{e['actor']}：第{day_of(e['tick'])}日自{e.get('pos')}弃宅"
                             f"{尾}（{因}）", [e["actor"]]))
        return out

    # ═══════════ 汇总：打分与报告 ═══════════

    def detect_all(self) -> list[Chain]:
        chains = (self.仇恨链() + self.恩义链() + self.建造链() + self.夺屋链()
                  + self.技能链() + self.家族链() + self.债务链()
                  + self.传闻链() + self.迁徙链())
        for c in chains:
            c.nodes.sort(key=lambda i: self.byid[i]["tick"])   # 节点以 tick 为序（考据之纲）
            c.beats = _fold(self.byid, c.nodes)                # 节拍折叠（§3.1）
            c.score_detail, c.score = _score(self.byid, c.beats)
        chains.sort(key=lambda c: -c.score)
        return chains

    def report(self, seed: int, days: int) -> tuple[str, dict]:
        """可讲述性报告（Markdown + JSON 双格式）。"""
        chains = self.detect_all()
        链中 = {i for c in chains for i in c.nodes}
        总 = len(self.E)
        孤立率 = round(1.0 - len(链中) / max(1, 总), 3)
        均长 = round(sum(len(c.nodes) for c in chains) / max(1, len(chains)), 1)
        型计 = {}
        for c in chains:
            型计[c.链型] = 型计.get(c.链型, 0) + 1

        # 世界丰富度体检：缺口分析
        缺口 = []
        体检表 = {"仇恨链": "无冲突：世界过温（抢夺机制冷）",
                  "夺屋链": "无夺屋：悍者机制冷",
                  "恩义链": "无恩义：互助机制冷",
                  "传闻链": "无传闻结链：传闻系统空转",
                  "误会链": "无误会：疑案机制冷",
                  "建造链": "无建造：学习系统未启动",
                  "器物链": "无器物：制器系统未启动",
                  "取火链": "无取火：火食系统未启动",
                  "畜牧链": "无畜牧：圈养系统未启动",
                  "债务链": "无债务：人情往来未发生",
                  "家族链": "无诞育：代际更替未发生",
                  "迁徙链": "无迁徙：灾荒驱动未发生"}
        for 型,  缺 in 体检表.items():
            if 型计.get(型,  0) == 0:
                缺口.append(缺)
        可述 = [c for c in chains if len(c.nodes) >= 3]

        md = [f"# 可讲述性报告 · 种子 {seed} · {days} 日", "",
              "## 世界丰富度体检", "",
              f"- 事件总数 {总}；链总数 {len(chains)}；孤立事件比例 {孤立率:.1%}；平均链长 {均长}",
              f"- 各链型：{('、'.join(f'{k}×{v}' for k, v in 型计.items())) or '无'}", ""]
        if not 可述:
            md += ["**世界在此种子下无可讲述之事。**", "",
                   "缺口：", ""] + [f"- {x}" for x in 缺口] + [""]
        elif 缺口:
            md += ["缺口（链型缺席，机制偏冷）：", ""] + [f"- {x}" for x in 缺口] + [""]

        md += ["## 链评分 Top", ""]
        js = {"seed": seed, "days": days,
              "stats": {"事件总数": 总,  "链总数": len(chains), "孤立事件比例": 孤立率,
                        "平均链长": 均长,  "链型计数": 型计,
                        "无可讲述之事": not 可述, "缺口": 缺口},
              "chains": []}
        for i, c in enumerate(chains[:10]):
            d = "、".join(f"{k} {v}" for k, v in c.score_detail.items())
            节拍 = " → ".join(k + (f"×{len(ids)}" if len(ids) > 1 else "")
                             for k, ids in c.beats)
            md += [f"### {i + 1}. [{c.链型}] {c.summary}", "",
                   f"评分 {c.score}（{d}）", "",
                   f"节拍：{节拍}", "",
                   f"节点：{' '.join('E' + str(n) for n in c.nodes)}", ""]
            js["chains"].append({"链型": c.链型,  "主体": c.主体,  "梗概": c.summary,
                                 "nodes": c.nodes, "actors": c.actors,
                                 "beats": [(k, ids) for k, ids in c.beats],
                                 "score": c.score, "score_detail": c.score_detail})
        return "\n".join(md), js


# 防笔误哨兵：上面若混入全角括号会在此处立现（模块导入即解析）
