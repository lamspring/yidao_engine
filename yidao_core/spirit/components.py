# -*- coding: utf-8 -*-
"""
灵体层 · 组件（components.py）

灵 = 一束纯数据组件。这是 v7-M2b 深水区：状态从平铺在 self 上，
迁入十个各司其职的组件——组件可独立实例化、独立测试、独立序列化。
（此底座日后要作虚拟现实的算法引擎，灵之构造必须拆得开、立得住。）

  身 Body         形体的活力账：阳、水分、力量、代谢、寿数
  谱 Genome       生殖系特质序列（DNA）与悟性
  心 Mind         心情（快变量）与心态（慢变量：dna 底 + 漂移活值）
  欲 Desire       欲望目标链与锻炼之志
  学 Knowledge    会什么（知识）、多熟（熟练）、学到哪（经验池）
  产 Property     随身行囊、名下屋、债务、在建工程
  缘 Relations    家世亲缘：代、父母、伴侣、子女、家门、庇主
  忆 Remembrance  心中的往事：记忆、序号、口述、悼念、交谈节拍、日常统计
  闻 Intel        情报与社会记忆：已知食物/水源、最后相见、屋火井之址
  程 Itinerary    历法与征程的运行态：每日标记、迁徙、祈雨、成年与诞育节拍

组件字段名沿用灵之旧扁平名（yang、mood、memories……），故 96 个方法体
一行未改：读写经 Spirit 的路由（见 __init__.py）落入组件。路由是兼容桥，
组件才是真身；日后各系统可渐次直谈组件，桥到时再拆。
"""

from dataclasses import dataclass, field


@dataclass
class Body:
    """身：形体的活力账。"""
    alive: bool = True
    诞生念: int = 0
    卒念: int | None = None
    寿数: int = 0
    yang: float = 0.0
    水分: float = 0.0
    strength: float = 0.0
    metabo: float = 1.0


@dataclass
class Genome:
    """谱：生殖系特质序列（DNA，初生即定）与悟性（dna 之定影）。"""
    dna: dict = field(default_factory=dict)
    悟性: float = 0.5


@dataclass
class Mind:
    """心：心情（恐惧/愤怒/希望/疲惫，随环境实时波动）与
    心态（谨慎/好斗/亲和，由记忆长期塑造——漂移改活值，不回写 dna）。"""
    mood: dict = field(default_factory=dict)
    pressure: float = 0.0
    caution: float = 0.5
    aggr: float = 0.5
    affinity: float = 0.5
    _drift_acc: dict = field(default_factory=dict)


@dataclass
class Desire:
    """欲：从阳存量长出的目标链（求生、变强、报复……）与锻炼之志。"""
    goals: list = field(default_factory=list)
    training: bool = False
    _last_train_report: int = 0


@dataclass
class Knowledge:
    """学：会什么、多熟、学到哪。"""
    knowledge: set = field(default_factory=set)
    skills: dict = field(default_factory=dict)
    _学习: dict = field(default_factory=dict)
    _学始: dict = field(default_factory=dict)


@dataclass
class Property:
    """产：随身行囊、名下屋、债务、在建工程。"""
    bag: list = field(default_factory=list)
    hut: object = None
    debts: dict = field(default_factory=dict)
    credits: dict = field(default_factory=dict)
    _工地: tuple | None = None
    _井地: tuple | None = None


@dataclass
class Relations:
    """缘：家世与亲缘。"""
    代: int = 0
    父母: tuple | None = None
    伴侣: str | None = None
    子女: list = field(default_factory=list)
    _家门: tuple | None = None
    _庇主: str | None = None


@dataclass
class Remembrance:
    """忆：心中的往事（会压缩、会遗忘、会永存）、口述历史、悼念、日常统计。"""
    memories: list = field(default_factory=list)
    _mem_seq: int = 0
    _讲过: dict = field(default_factory=dict)
    _疑过: set = field(default_factory=set)
    _mourned: set = field(default_factory=set)
    _talk_cd: dict = field(default_factory=dict)
    _share_cd: dict = field(default_factory=dict)
    stats: dict = field(default_factory=dict)


@dataclass
class Intel:
    """闻：情报只来自两处——亲眼所见，或故人相告。没有全图知识。"""
    known_food: dict = field(default_factory=dict)
    known_water: dict = field(default_factory=dict)
    _last_seen: dict = field(default_factory=dict)
    _stay: dict = field(default_factory=dict)
    _known_huts: dict = field(default_factory=dict)
    _known_fires: dict = field(default_factory=dict)
    _known_wells: dict = field(default_factory=dict)
    _雨见: int = 0
    _last_rob: int = 0


@dataclass
class Itinerary:
    """程：历法与征程的运行态。"""
    _淋雨_day: int = -1
    _受冻_day: int = -1
    _求庇_day: int = -1
    _求庇_target: str | None = None
    _渴_day: int = -1
    _祀_day: int = -1
    _荒: int = 0
    _荒_day: int = -1
    _迁: tuple | None = None
    _迁由: str = ""
    _祈雨: tuple | None = None
    _赴祈: tuple | None = None
    _家传_day: int = -1
    _已成年: bool = False
    _上次诞育: int = 0
    # ── 回光返照（v8-P0D·D1）──
    _回光: int | None = None      # 回光起始念（None=不在回光中）
    _回光过: bool = False         # 一生仅此一次
    _斗伤念: int = -999           # 最近战斗负伤之念（横死无回光之据）


# 路由表：扁平名 → 组件持有名。Spirit 的 __getattr__/__setattr__ 依此把
# 旧的扁平读写（self.yang …）桥进组件（self.身.yang …）——方法体一行未改。
组件字段 = {
    "身": Body, "谱": Genome, "心": Mind, "欲": Desire, "学": Knowledge,
    "产": Property, "缘": Relations, "忆": Remembrance, "闻": Intel, "程": Itinerary,
}

ROUTE: dict[str, str] = {}
for _c, _cls in 组件字段.items():
    for _f in _cls.__dataclass_fields__:
        ROUTE[_f] = _c
