# -*- coding: utf-8 -*-
"""
《易道引擎》v6.0 "鱼缸" — 模拟循环 + 观测层文字流 (fishbowl.py)

用法：
  python -m v6.fishbowl --ticks 640 --seed 42
  python v6/fishbowl.py --ticks 640 --seed 42 --inspect 阿石
  python -m v6.fishbowl --quiet            # 只输出终局摘要
  python -m v6.fishbowl --verbose          # 全开：连吃喝拉撒也入流

事件分级：
  显著事件（抢夺/战斗/报复/涌现/交谈/分享/庇护/悼念/生/死/心态漂移/天道/
  误会/澄清/谎言戳穿/同悼）进默认流；
  日常琐事（进食/饮水/安眠/传闻/传闻失真/谎言得逞/闻名）不进流、只计数，--verbose 时可见。
  夜晚默认安静，但夜袭、临终、涌现等特殊事件照常入流。

本层是"观测笔记"，写在世界之外；世界本身不存任何历史。
"""

import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import argparse
import os

# 双模式入口：python -m v6.fishbowl（包）与 python v6/fishbowl.py（脚本）皆可
if __package__:
    from .world import World, TICKS_PER_DAY, PATH_AT
    from yidao_core.session import Session
    from yidao_core.spirit import DNA_技艺, LEARN_GATE
else:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from world import World, TICKS_PER_DAY, PATH_AT
    from yidao_core.session import Session
    from yidao_core.spirit import DNA_技艺, LEARN_GATE

# 事件分级：显著事件进默认流；琐事只在 --verbose 下现身
NOTABLE_KINDS = {"抢夺", "战斗", "报复", "涌现", "涌现反击", "报仇成",
                 "交谈", "分享", "救助", "庇护", "悼念", "漂移",
                 "出生", "死亡", "天道", "锻炼始",
                 "领悟", "模仿", "传授", "动土", "建成", "播种",
                 "求庇收留", "求庇拒绝", "夺屋", "夺屋成", "夺回", "塌屋",
                 "物候", "取火", "制器", "狩猎", "驯化", "建栏", "烹食初",
                 "交易", "借贷", "还债", "赖账", "馈赠", "畜死", "生食致病",
                 "结侣", "诞育", "成年", "寿终", "家传", "继承", "拾遗",
                 "口述", "父仇", "两清",
                 "误会", "澄清", "谎言戳穿", "同悼",
                 "凿井", "井成", "制陶", "缝纫", "琢饰", "贝易",
                 "祈雨聚", "祈应", "迁徙", "迁抵"}
TRIVIA_KINDS = {"进食", "饮水", "淋雨", "采集", "收获", "田枯", "受冻",
                "伐木", "采石", "采藤", "屠宰", "收蛋", "挤奶", "添柴",
                "烹食", "取火败", "制器败", "器断", "火熄", "渔获",
                "传闻", "传闻失真", "谎言得逞", "闻名",
                "汲水", "灌水", "采土", "得贝", "制陶败", "缝纫败", "衣敝",
                "淘浚", "井废", "径成", "赴祈"}


def fmt_time(tick: int) -> str:
    """能量循环计数 → 第X日·第Y念。"""
    return f"第{tick // TICKS_PER_DAY + 1}日·第{tick % TICKS_PER_DAY + 1}念"


def day_of(tick: int) -> int:
    return tick // TICKS_PER_DAY + 1


def run(ticks: int, seed: int, quiet: bool, verbose: bool):
    """跑一缸世界。返回 (世界, 众灵, 观测日志)。
    世界算法在 yidao_core 底座里；本函数只是接上线、按下开关。"""
    journal: list[dict] = []        # 观测笔记：在观测层，不在世界层
    session = None                  # 先占位，report 闭包晚绑定

    def report(tick, pos, text, kind, actor=None, target=None, subject=None,
               **_extra):     # 考据线索（因注/读数等）随 extra 而来，鱼缸不录
        journal.append({"tick": tick, "kind": kind, "actor": actor, "pos": pos,
                        "target": target, "subject": subject, "text": text})
        if quiet:
            return
        if kind in NOTABLE_KINDS or (verbose and kind in TRIVIA_KINDS):
            if pos is None:
                print(f"[{fmt_time(tick)}] {text}")
            else:
                y, x = pos
                print(f"[{fmt_time(tick)}] {session.world.terrain_name(y, x)}({y},{x}) {text}")

    # 开天辟地：炁场自生世界，众灵诞生于阴阳交界
    session = Session.genesis(seed=seed, on_event=report)
    session.run(ticks)
    return session.world, session.spirits, journal


def find_chains(spirits: list, journal: list) -> list[str]:
    """仇恨链：被抢 → 铭记 → 锻炼 → 报复/临界反击。"""
    chains = []
    seen = set()
    for r in journal:
        if r["kind"] != "抢夺":
            continue
        v, rob, t = r["target"], r["actor"], r["tick"]
        if (v, rob) in seen:
            continue
        主 = next((s for s in spirits if s.name == v), None)
        if 主 is None:
            continue
        铭记 = any(m.永存 and m.类别 in ("被抢", "受辱") and m.对象 == rob
                   for m in 主.memories)
        报仇 = next((e for e in journal
                     if e["kind"] in ("报复", "涌现反击")
                     and e["actor"] == v and e["target"] == rob and e["tick"] > t),
                    None)
        if not (铭记 and 报仇):
            continue
        seen.add((v, rob))
        parts = [f"被抢(第{day_of(t)}日)", "铭记"]
        锻炼 = [e["tick"] for e in journal
                if e["kind"] == "锻炼始" and e["actor"] == v and t < e["tick"] < 报仇["tick"]]
        if 锻炼:
            parts.append(f"锻炼(第{day_of(min(锻炼))}-{day_of(max(锻炼))}日)")
        标签 = "报复" if 报仇["kind"] == "报复" else "临界反击"
        parts.append(f"{标签}{rob}(第{day_of(报仇['tick'])}日)")
        chains.append(f"{v}: " + " → ".join(parts))
    return chains


def find_grace_chains(spirits: list, journal: list) -> list[str]:
    """恩义链：分享/救助 → 铭记 → 互助（回报分享/挺身相护/悼念）。"""
    chains = []
    seen = set()
    for e in journal:
        if e["kind"] not in ("分享", "救助"):
            continue
        a, b, t = e["actor"], e["target"], e["tick"]
        if (a, b) in seen:
            continue
        受恩者 = next((s for s in spirits if s.name == b), None)
        if 受恩者 is None:
            continue
        铭记 = any(m.对象 == a and m.类别 == "受助" for m in 受恩者.memories)
        if not 铭记:
            continue
        回报 = next((x for x in journal
                     if x["tick"] > t and x["actor"] == b and x["target"] == a
                     and x["kind"] in ("分享", "救助", "庇护", "悼念")), None)
        if 回报 is None:
            continue
        seen.add((a, b))
        标签 = {"分享": "回报分享", "救助": "回报救助",
                "庇护": "挺身相护", "悼念": "悼念"}[回报["kind"]]
        chains.append(f"{b}: 受{a}之恩(第{day_of(t)}日) → 铭记 → "
                      f"{标签}{a}(第{day_of(回报['tick'])}日)")
    return chains


def find_build_chains(spirits: list, journal: list) -> list[str]:
    """建造链：淋雨 → 领悟/学会建造 → 采集 → 建成 → 他人模仿。"""
    chains = []
    for s in spirits:
        淋雨 = next((e for e in journal
                     if e["kind"] == "淋雨" and e["actor"] == s.name), None)
        # 得法：领悟/模仿的 actor 是自己；传授的受教者才是自己（target）
        得法 = next((e for e in journal
                     if "建造" in e["text"]
                     and ((e["kind"] in ("领悟", "模仿") and e["actor"] == s.name)
                          or (e["kind"] == "传授" and e["target"] == s.name))), None)
        建成 = next((e for e in journal
                     if e["kind"] == "建成" and e["actor"] == s.name), None)
        if not (得法 and 建成):
            continue
        法名 = {"领悟": "自悟建造", "模仿": "观察学会建造", "传授": "受教建造"}[得法["kind"]]
        parts = []
        if 淋雨:
            parts.append(f"夜雨淋身(第{day_of(淋雨['tick'])}日)")
        parts.append(f"{法名}(第{day_of(得法['tick'])}日)")
        采集 = [e["tick"] for e in journal
                if e["kind"] == "采集" and e["actor"] == s.name
                and 得法["tick"] <= e["tick"] <= 建成["tick"]]
        if 采集:
            parts.append(f"采集施工(第{day_of(min(采集))}-{day_of(max(采集))}日)")
        parts.append(f"茅屋建成(第{day_of(建成['tick'])}日)")
        # 知识扩散：他人见此屋而模仿，或此灵把法子传了出去
        扩散 = next((e for e in journal
                     if e["kind"] in ("模仿", "传授") and "建造" in e["text"]
                     and e["tick"] > 建成["tick"]
                     and (e["actor"] != s.name or e["target"] == s.name)), None)
        if 扩散 is not None:
            谁 = 扩散["actor"] if 扩散["kind"] == "模仿" else 扩散["target"]
            parts.append(f"{谁}效仿(第{day_of(扩散['tick'])}日)")
        chains.append(f"{s.name}: " + " → ".join(parts))
    return chains


def find_seize_chains(spirits: list, journal: list) -> list[str]:
    """夺屋链：被夺屋 → 铭记 → 锻炼 → 夺回/报复。"""
    chains = []
    for e in journal:
        if e["kind"] != "夺屋成":
            continue
        v, rob, t = e["target"], e["actor"], e["tick"]
        主 = next((s for s in spirits if s.name == v), None)
        if 主 is None:
            continue
        铭记 = any(m.永存 and m.类别 == "夺屋" and m.对象 == rob for m in 主.memories)
        后报 = next((x for x in journal
                     if x["kind"] in ("夺回", "报复", "涌现反击")
                     and x["actor"] == v and x["target"] == rob and x["tick"] > t), None)
        if not (铭记 and 后报):
            continue
        parts = [f"被夺屋(第{day_of(t)}日)", "铭记"]
        锻炼 = [x["tick"] for x in journal
                if x["kind"] == "锻炼始" and x["actor"] == v and t < x["tick"] < 后报["tick"]]
        if 锻炼:
            parts.append(f"锻炼(第{day_of(min(锻炼))}-{day_of(max(锻炼))}日)")
        标签 = "夺回" if 后报["kind"] == "夺回" else "报复"
        parts.append(f"{标签}{rob}(第{day_of(后报['tick'])}日)")
        chains.append(f"{v}: " + " → ".join(parts))
    return chains


def _得法事件(journal: list, name: str, skill: str):
    """某灵习得某技能的第一桩事件（领悟/模仿为己，传授为受教）。"""
    for e in journal:
        if skill not in e["text"]:
            continue
        if e["kind"] in ("领悟", "模仿") and e["actor"] == name:
            return e
        if e["kind"] == "传授" and e["target"] == name:
            return e
    return None


def find_skill_chains(spirits: list, journal: list) -> dict:
    """器物链 / 取火链 / 畜牧链：发明 → 制成/得火/驯化 → 使用 → 传播。"""
    out = {"器物链": [], "取火链": [], "畜牧链": []}
    for s in spirits:
        # 器物链
        得法 = _得法事件(journal, s.name, "制器")
        制成 = next((e for e in journal
                     if e["kind"] == "制器" and e["actor"] == s.name), None)
        if 得法 and 制成:
            parts = [f"悟得制器(第{day_of(得法['tick'])}日)",
                     f"制成器物(第{day_of(制成['tick'])}日)"]
            传播 = next((e for e in journal
                         if e["tick"] > 制成["tick"] and "制器" in e["text"]
                         and ((e["kind"] in ("模仿", "领悟") and e["actor"] != s.name)
                              or (e["kind"] == "传授" and e["actor"] == s.name))), None)
            if 传播:
                谁 = 传播["actor"] if 传播["kind"] != "传授" else 传播["target"]
                parts.append(f"{谁}习得(第{day_of(传播['tick'])}日)")
            out["器物链"].append(f"{s.name}: " + " → ".join(parts))
        # 取火链
        受冻 = next((e for e in journal
                     if e["kind"] == "受冻" and e["actor"] == s.name), None)
        得火法 = _得法事件(journal, s.name, "取火")
        得火 = next((e for e in journal
                     if e["kind"] == "取火" and e["actor"] == s.name), None)
        if 得火法 and 得火:
            parts = []
            if 受冻:
                parts.append(f"寒夜受冻(第{day_of(受冻['tick'])}日)")
            parts.append(f"悟取火(第{day_of(得火法['tick'])}日)")
            parts.append(f"钻木得火(第{day_of(得火['tick'])}日)")
            熟食 = next((e for e in journal
                         if e["kind"] == "烹食初" and e["actor"] == s.name
                         and e["tick"] > 得火["tick"]), None)
            if 熟食:
                parts.append(f"始知熟食(第{day_of(熟食['tick'])}日)")
            out["取火链"].append(f"{s.name}: " + " → ".join(parts))
        # 畜牧链
        得畜法 = _得法事件(journal, s.name, "畜牧")
        驯化 = next((e for e in journal
                     if e["kind"] == "驯化" and e["actor"] == s.name), None)
        if 得畜法 and 驯化:
            parts = [f"悟畜牧(第{day_of(得畜法['tick'])}日)",
                     f"驯化入栏(第{day_of(驯化['tick'])}日)"]
            收产 = next((e for e in journal
                         if e["kind"] in ("收蛋", "挤奶") and e["actor"] == s.name
                         and e["tick"] > 驯化["tick"]), None)
            if 收产:
                parts.append(f"{收产['kind']}(第{day_of(收产['tick'])}日)")
            out["畜牧链"].append(f"{s.name}: " + " → ".join(parts))
    return out


def find_family_trees(spirits: list) -> list[str]:
    """家族链：从初代（代 0）出发，沿子女关系画出可考谱系。"""
    byname = {s.name: s for s in spirits}
    lines: list[str] = []

    def 行(s, depth: int) -> str:
        生 = day_of(s.诞生念)
        卒 = "在世" if s.alive else (f"第{day_of(s.卒念)}日卒" if s.卒念 is not None else "已亡")
        return "    " + "  " * depth + f"{s.name}（第{生}日生，{卒}）"

    def rec(s, depth: int, seen: set):
        if s.name in seen:
            return
        seen.add(s.name)
        lines.append(行(s, depth))
        for cname in s.子女:
            c = byname.get(cname)
            if c is not None:
                rec(c, depth + 1, seen)

    for s in spirits:
        if s.代 == 0 and s.子女:
            rec(s, 0, set())
    return lines


def find_debt_chains(spirits: list, journal: list) -> list[str]:
    """债务链：借贷 → 还债（善）或 赖账 → 反目（恶）。"""
    chains = []
    seen = set()
    for e in journal:
        if e["kind"] != "借贷":
            continue
        a, b, t = e["actor"], e["target"], e["tick"]
        if (a, b) in seen:
            continue
        还 = next((x for x in journal if x["kind"] == "还债"
                   and x["actor"] == b and x["target"] == a and x["tick"] > t), None)
        赖 = next((x for x in journal if x["kind"] == "赖账"
                   and x["actor"] == b and x["target"] == a and x["tick"] > t), None)
        if 还 is not None:
            seen.add((a, b))
            chains.append(f"{b}: 受{a}借贷之惠(第{day_of(t)}日) → 铭记 → 还债两清(第{day_of(还['tick'])}日)")
        elif 赖 is not None:
            seen.add((a, b))
            反目 = next((x for x in journal if x["tick"] > 赖["tick"]
                         and x["kind"] in ("抢夺", "战斗")
                         and {x["actor"], x["target"]} == {a, b}), None)
            尾 = f" → 反目成仇(第{day_of(反目['tick'])}日)" if 反目 else ""
            chains.append(f"{b}: 受{a}借贷之惠(第{day_of(t)}日) → 赖账生怨(第{day_of(赖['tick'])}日){尾}")
    return chains


def _疑案结局(journal: list, 疑者: str, 事主: str, t: int):
    """一桩疑案的结局：事主剖白（澄清），或双方交恶（谎言戳穿/抢夺/战斗/报复）。"""
    澄清 = next((x for x in journal if x["kind"] == "澄清"
                 and x["actor"] == 事主 and x["target"] == 疑者 and x["tick"] > t), None)
    if 澄清 is not None:
        return ("澄清冰释", 澄清["tick"])
    冲突 = next((x for x in journal if x["tick"] > t
                 and x["kind"] in ("谎言戳穿", "抢夺", "战斗", "报复", "涌现反击")
                 and {x["actor"], x["target"]} == {疑者, 事主}), None)
    if 冲突 is not None:
        return ("结仇", 冲突["tick"])
    return None


def find_gossip_chains(spirits: list, journal: list) -> list[str]:
    """传闻链：传闻（失真）→ 听者生疑/误会 → 澄清或结仇。
    另收骨旁生疑的误会链：误会 → 澄清或结仇。"""
    chains = []
    seen = set()
    # 传闻链：听者因传闻对事主生疑，而后或澄清或结仇
    for e in journal:
        if e["kind"] not in ("传闻", "传闻失真") or not e.get("subject"):
            continue
        teller, listener, subj, t = e["actor"], e["target"], e["subject"], e["tick"]
        if (listener, subj) in seen:
            continue
        # 只有恶闻才生疑：看日志后文里这桩传闻是否走向澄清/结仇
        if "打死" not in e["text"] and not any(
                k in e["text"] for k in ("抢掠", "打垮", "行过凶", "夺过", "欠债不还",
                                          "坑人", "口吐谎言", "行止不端")):
            continue
        结局 = _疑案结局(journal, listener, subj, t)
        if 结局 is None:
            continue
        seen.add((listener, subj))
        失真 = "，失真" if e["kind"] == "传闻失真" else ""
        chains.append(f"{listener}: 听{teller}传闻{subj}(第{day_of(t)}日{失真}) → 疑心生暗鬼 → "
                      f"{结局[0]}(第{day_of(结局[1])}日)")
    # 误会链：骨旁生疑，而后或澄清或结仇
    for e in journal:
        if e["kind"] != "误会":
            continue
        疑者, 嫌, t = e["actor"], e["target"], e["tick"]
        if (疑者, 嫌) in seen:
            continue
        结局 = _疑案结局(journal, 疑者, 嫌, t)
        if 结局 is None:
            continue
        seen.add((疑者, 嫌))
        chains.append(f"{疑者}: 见{嫌}在{e.get('subject') or '故人'}遗骨旁，疑其为凶"
                      f"(第{day_of(t)}日) → {结局[0]}(第{day_of(结局[1])}日)")
    return chains


def find_migration_chains(spirits: list, journal: list) -> list[str]:
    """迁徙节：谁何时从何地迁往何地、因何——弃宅（迁徙）与落脚（迁抵）相配。"""
    lines = []
    for e in journal:
        if e["kind"] != "迁徙":
            continue
        抵 = next((x for x in journal if x["kind"] == "迁抵"
                   and x["actor"] == e["actor"] and x["tick"] >= e["tick"]), None)
        因 = e["text"].split("（因：", 1)[1].rstrip("）") if "（因：" in e["text"] else ""
        起 = f"第{day_of(e['tick'])}日自{e.get('pos')}弃宅"
        if 抵 is not None:
            lines.append(f"{e['actor']}：{起} → 第{day_of(抵['tick'])}日抵{抵.get('pos')}（{因}）")
        else:
            lines.append(f"{e['actor']}：{起} → 至世界尽头仍未落脚（{因}）")
    return lines


def print_summary(world: World, spirits: list, journal: list, ticks: int):
    """终局摘要：存活数、众灵心中前 5 条记忆、检出的完整因果链。"""
    alive = [s for s in spirits if s.alive]
    kinds = {e["kind"] for e in journal if e["kind"] in NOTABLE_KINDS}
    print("\n══════════ 终局摘要 ══════════")
    print(f"历时 {ticks} 念（{ticks // TICKS_PER_DAY} 日），"
          f"存活 {len(alive)} / 历生 {len(spirits)} 灵，"
          f"草覆盖率 {world.grass_coverage():.0%}，尚存印记 {len(world.marks)} 处，"
          f"显著事件 {len(kinds)} 类")
    print(f"世界物候：降雨 {world.rain_episodes} 场，"
          f"现存茅屋 {len(world.buildings)} 座（塌 {world.collapsed_huts}），"
          f"农田 {len(world.farms)} 畦，走兽 {len(world.animals)} 头，"
          f"火堆 {len(world.fires)} 处，气温 {world.temp.mean():.1f}°")

    print("\n【众灵之心】历史只在角色心中——世界自身一无所记")
    for s in alive:
        top = sorted(s.memories, key=lambda m: (m.永存, m.权重), reverse=True)[:5]
        print(f"· {s.name}（阳 {s.yang:.0f}，水 {s.水分:.0f}，力量 {s.strength:.1f}，"
              f"谨慎 {s.caution:.2f}，好斗 {s.aggr:.2f}，亲和 {s.affinity:.2f}｜"
              f"食{s.stats['进食']} 饮{s.stats['饮水']} 眠{s.stats['安眠']}）")
        for m in top:
            标 = "[永存]" if m.永存 else "      "
            次 = f"（{m.次数}次）" if m.次数 > 1 else ""
            print(f"    {标} {m.要义}{次}（情绪 {m.情绪强度:.2f}，权重 {m.权重:.2f}，第{day_of(m.念戳)}日）")
        if not top:
            print("    （心中空空如也）")

    print("\n【仇恨链】")
    chains = find_chains(spirits, journal)
    if chains:
        for c in chains:
            print(f"  {c}")
    else:
        print("  （本季未结成完整仇恨链）")

    print("\n【恩义链】")
    grace = find_grace_chains(spirits, journal)
    if grace:
        for c in grace:
            print(f"  {c}")
    else:
        print("  （本季未结成完整恩义链）")

    print("\n【建造链】")
    built = find_build_chains(spirits, journal)
    if built:
        for c in built:
            print(f"  {c}")
    else:
        print("  （本季未有茅屋落成）")

    print("\n【夺屋链】")
    seized = find_seize_chains(spirits, journal)
    if seized:
        for c in seized:
            print(f"  {c}")
    else:
        print("  （本季无人夺屋，或夺而未报）")

    skill_chains = find_skill_chains(spirits, journal)
    for 题 in ("器物链", "取火链", "畜牧链"):
        print(f"\n【{题}】")
        if skill_chains[题]:
            for c in skill_chains[题]:
                print(f"  {c}")
        else:
            print("  （本季未结成）")

    print("\n【债务链】")
    debts = find_debt_chains(spirits, journal)
    if debts:
        for c in debts:
            print(f"  {c}")
    else:
        print("  （本季无借贷往来）")

    print("\n【传闻链】")
    gossips = find_gossip_chains(spirits, journal)
    if gossips:
        for c in gossips:
            print(f"  {c}")
    else:
        print("  （本季传闻未结成可考的疑案）")
    传闻数 = sum(1 for e in journal if e["kind"] == "传闻")
    失真数 = sum(1 for e in journal if e["kind"] == "传闻失真")
    谎言数 = sum(1 for e in journal if e["kind"] in ("谎言戳穿", "谎言得逞"))
    print(f"  （传闻 {传闻数} 起，其中失真 {失真数} 起；谎言 {谎言数} 起；"
          f"同悼 {sum(1 for e in journal if e['kind'] == '同悼')} 场）")

    # v6.4：迁徙与井·径·陶·贝的物候
    print("\n【迁徙】")
    migrations = find_migration_chains(spirits, journal)
    if migrations:
        for c in migrations:
            print(f"  {c}")
    else:
        print("  （本季无人弃家，故土尚能养人）")

    print("\n【井·径·陶·贝·祈雨】")
    径段 = int((world.tread >= PATH_AT).sum())
    计数 = {k: sum(1 for e in journal if e["kind"] == k) for k in
            ("井成", "井废", "淘浚", "汲水", "径成", "制陶", "得贝", "贝易",
             "祈雨聚", "赴祈", "祈应")}
    print(f"  井：凿成 {计数['井成']} 口（现存 {len(world.wells)}，废 {计数['井废']}），"
          f"淘浚 {计数['淘浚']} 次，汲水 {计数['汲水']} 次")
    print(f"  径：踏成 {计数['径成']} 段（尚存 {径段} 段）——村落间的路自己长出来")
    print(f"  陶：烧成 {计数['制陶']} 只；贝：拾得 {计数['得贝']} 枚，"
          f"贝币结算 {计数['贝易']} 笔")
    print(f"  祈雨：聚 {计数['祈雨聚']} 场，赴祈 {计数['赴祈']} 人次，"
          f"得应 {计数['祈应']} 起（天道永不回应，得应皆巧合）")

    # 家族与口述历史：历史只在人心中跨代流动
    听闻 = sum(1 for s in alive for m in s.memories if m.类别 in ("听闻", "听闻恨"))
    trees = find_family_trees(spirits)
    # v6.5：代际纵深——平均代数与最年长家族深度（历生众灵计，1 起）
    代际注 = ""
    if spirits:
        平均代 = sum(s.代 for s in spirits) / len(spirits) + 1
        最深代 = max(s.代 for s in spirits) + 1
        代际注 = f"｜代际纵深：平均第 {平均代:.1f} 代，最年长家族深至第 {最深代} 代"
    if trees:
        print(f"\n【家族链】跨代存活的听闻记忆 {听闻} 条——历史通过人心延续{代际注}")
        for line in trees:
            print(line)
    elif 听闻 or 代际注:
        print(f"\n【家族链】跨代存活的听闻记忆 {听闻} 条{代际注}")


def inspect(spirits: list, name: str, world=None):
    """观心：翻开某灵此刻的心——全部记忆要义、目标、心情、关系、知识与财产。"""
    s = next((x for x in spirits if x.name == name), None)
    if s is None:
        print(f"查无此灵：{name}。众灵之名：{', '.join(x.name for x in spirits)}")
        return
    print(f"\n【观心·{s.name}】{'在世' if s.alive else '已亡'}")
    print(f"  阳 {s.yang:.1f}｜水分 {s.水分:.1f}｜力量 {s.strength:.2f}｜压力 {s.pressure:.2f}")
    print(f"  性格：谨慎 {s.caution:.2f}，好斗 {s.aggr:.2f}，亲和 {s.affinity:.2f}，悟性 {s.悟性:.2f}")
    # v6.5：DNA 禀赋（技艺位点前三位）与学习中（经验过门槛一成的技能）
    禀赋 = sorted(((k, s.dna[k]) for k in DNA_技艺), key=lambda kv: -kv[1])[:3]
    print(f"  DNA禀赋（前三）：" + "、".join(f"{k} {v:.2f}" for k, v in 禀赋))
    学习中 = sorted(((k, v / LEARN_GATE[k]) for k, v in s._学习.items()
                    if v > 0.10 * LEARN_GATE[k]), key=lambda kv: -kv[1])
    if 学习中:
        print(f"  学习中：" + "、".join(f"{k} {p:.0%}" for k, p in 学习中))
    年龄 = f"{(world.tick - s.诞生念) / TICKS_PER_DAY:.1f}" if world is not None else "?"
    家 = []
    if s.父母:
        家.append("父母:" + "、".join(s.父母))
    if s.伴侣:
        家.append(f"伴侣:{s.伴侣}")
    if s.子女:
        家.append("子女:" + "、".join(s.子女))
    print(f"  代际：第{s.代 + 1}代｜年龄 {年龄} 日｜寿数 {s.寿数 // TICKS_PER_DAY} 日"
          f"｜家庭：{'，'.join(家) if 家 else '（无亲无故）'}")
    print(f"  心情：" + "，".join(f"{k} {v:.2f}" for k, v in s.mood.items()))
    print(f"  栖身所：{s._栖身所()}｜日常：食{s.stats['进食']} 饮{s.stats['饮水']} "
          f"眠{s.stats['安眠']} 炼{s.stats['锻炼']}")
    print(f"  知识：{'、'.join(sorted(s.knowledge)) if s.knowledge else '（无）'}")
    if s.skills:
        print(f"  熟练：" + "、".join(f"{k} {v:.2f}" for k, v in sorted(s.skills.items())))
    财产 = []
    if s.hut is not None:
        财产.append(f"茅屋({s.hut.y},{s.hut.x})·{s.hut.状态}·阳{s.hut.阳:.0f}·储粮{len(s.hut.仓储)}")
    if world is not None:
        for f in world.farms:
            if f.主人 == s.name:
                财产.append(f"农田({f.y},{f.x})·{'可收' if f.成熟(world.tick) else '生长中'}")
        畜 = [a for a in world.animals if a.驯主 == s.name]
        if 畜:
            财产.append("牲畜:" + "、".join(f"{a.种类}" for a in 畜))
    if s.bag:
        from collections import Counter
        囊 = Counter(it.类型 for it in s.bag)
        财产.append("行囊[" + "、".join(f"{k}×{v}" for k, v in 囊.items()) + "]")
    print(f"  财产：{'、'.join(财产) if 财产 else '（无片瓦）'}")
    债务 = []
    for 名, 账 in s.debts.items():
        债务.append(f"欠{名}×{len(账)}")
    for 名, 账 in s.credits.items():
        债务.append(f"{名}欠我×{len(账)}")
    print(f"  债务：{'、'.join(债务) if 债务 else '（无）'}")
    print(f"  目标：{'、'.join(s.goals) if s.goals else '（无）'}")
    rel = s.关系()
    print(f"  关系：{'、'.join(f'{n}({v:+.2f})' for n, v in rel) if rel else '（举目皆陌路）'}")
    print(f"  记忆（{len(s.memories)} 条，按权重）：")
    for m in sorted(s.memories, key=lambda m: (m.永存, m.权重), reverse=True):
        标 = "[永存]" if m.永存 else "      "
        次 = f"（{m.次数}次）" if m.次数 > 1 else ""
        print(f"    {标} {m.要义}{次}（情绪 {m.情绪强度:.2f}，权重 {m.权重:.2f}，第{day_of(m.念戳)}日）")


def main():
    ap = argparse.ArgumentParser(description="易道引擎 v6.0 鱼缸：灵体世界最小原型")
    ap.add_argument("--ticks", type=int, default=640, help="模拟念数（默认 640 = 10 日）")
    ap.add_argument("--seed", type=int, default=42, help="显式随机种子（可复现）")
    ap.add_argument("--inspect", type=str, default=None, help="终局观心：打印该角色全部记忆/目标/心情")
    ap.add_argument("--quiet", action="store_true", help="只输出终局摘要")
    ap.add_argument("--verbose", action="store_true", help="全开：日常琐事（进食/饮水）也入流")
    args = ap.parse_args()

    if not args.quiet:
        print(f"《易道引擎》v6.0 鱼缸 ｜ 种子 {args.seed} ｜ {args.ticks} 念")
        print("世界无史，人心有史。观察开始。\n")

    world, spirits, journal = run(args.ticks, args.seed, args.quiet, args.verbose)
    print_summary(world, spirits, journal, args.ticks)
    if args.inspect:
        inspect(spirits, args.inspect, world)


if __name__ == "__main__":
    main()
