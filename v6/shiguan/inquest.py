# -*- coding: utf-8 -*-
"""
史官 · 调查接口（inquest.py）——侦探的调查台（§2.4）。

史官的全知以"调查"为路径，不以"被喂"为路径：
  1. 现场照片：事件的结构化现场读数（readings，事发当刻的实值）；
  2. 当事人记忆：事发当 tick 的观心快照（若有），否则终局记忆档案
     ——终局档案必带时效警告标注（终局之心非事发之心）；
  3. 旁证链：事件簿中与当事人相关的先行事件（规则筛选，不许 LLM 自由发挥）。

查不到就如实写"不可考"——真相随死者入土是史学的常态，不是缺陷。
"""

from yidao_core.world import TICKS_PER_DAY

# 旁证相关性：某类事件的先行旁证该找哪些 kind（同当事人 + 时间窗）
_旁证KIND = {
    "战斗": ("抢夺", "被抢", "受辱", "夺屋成", "赖账", "传闻", "传闻失真", "误会",
             "战斗", "报复", "锻炼始"),
    "报复": ("抢夺", "夺屋成", "传闻失真", "误会", "锻炼始", "战斗"),
    "涌现反击": ("抢夺", "夺屋成", "传闻失真", "误会", "锻炼始", "战斗"),
    "死亡": ("战斗", "抢夺", "受冻", "生食致病", "传闻失真", "误会", "回光"),
    "寿终": ("回光", "渡阳", "不渡", "诞育", "结为伴侣"),
    "渡阳": ("回光", "战斗", "受冻"),
    "夺屋成": ("淋雨", "受冻", "战斗", "抢夺"),
    "澄清": ("误会", "传闻失真", "传闻", "谎言戳穿"),
    "两清": ("战斗", "报复", "抢夺"),
    "领悟": ("淋雨", "受冻", "生食致病", "焦渴", "观察", "采集"),
}
_默认旁证 = ("战斗", "抢夺", "死亡", "寿终", "进食", "饮水", "受冻")


class Inquest:
    """按需调查：why(事件 id) → 读数 + 当事人心 + 旁证链。"""

    def __init__(self, ledger, spirits):
        self.ledger = ledger
        self.spirits = spirits      # 只读终局档案用

    def why(self, event_id: int) -> dict:
        e = self.ledger.by_id(event_id)
        # 一、现场照片
        readings = e.get("readings")
        # 二、当事人心：快照优先, 终局档案次之（带时效警告）
        mind = None
        if "minds" in e and "actor" in e["minds"]:
            mind = {"快照": e["minds"]["actor"], "时效": "事发当刻"}
        else:
            s = next((x for x in self.spirits if x.name == e["actor"]), None)
            if s is not None:
                mems = sorted(s.memories, key=lambda m: -m.权重)[:5]
                mind = {"快照": {
                            "阳": round(s.yang, 2), "代": s.代,
                            "top_memories": [{"要义": m.要义,  "类别": m.类别, 
                                              "对象": m.对象,  "权重": round(m.权重,  3)}
                                             for m in mems],
                            "pressure": round(s.pressure, 3),
                            "knowledge": sorted(s.knowledge)},
                        "时效": "终局档案——事发时或已不同（记忆会遗忘压缩）"}
        # 三、旁证链：同当事人的先行相关事件（kind 相关性表 × 时间窗 20 日）
        窗 = 20 * TICKS_PER_DAY
        相关 = set(_旁证KIND.get(e["kind"], _默认旁证))
        旁证 = [x["id"] for x in self.ledger.events
                if x["id"] != event_id
                and x["tick"] < e["tick"] and e["tick"] - x["tick"] <= 窗
                and x["kind"] in 相关
                and x["actor"] in (e["actor"], e["target"])]
        旁证.sort(key=lambda i: self.ledger.by_id(i)["tick"])
        return {"readings": readings, "actor_mind": mind, "旁证": 旁证}
