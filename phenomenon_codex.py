# -*- coding: utf-8 -*-
"""
《易道动态世界引擎》v2.0 — 现象语库 (PhenomenonCodex)

语库扩建三大模块：
  1. 物类映射库（MANIFESTATION_TEMPLATES）：八纯卦 × 六种物类
  2. 现象词汇库（PHENOMENON_LEXICON）：八卦协议 × 四维度感官描述
  3. 变化与势能叙事库（TRANSITION_NARRATIVES + POTENTIAL_STAGE_NARRATIVE）

设计原则：
  - 不是64卦硬编码，而是基于八卦协议的语义生成规则
  - 复合卦通过上下卦协议组合推导
  - 现象级描述，让卦象能被感知、被阅读、被叙事
"""

from typing import Dict, List, Tuple, Optional


# ═══════════════════════════════════════════
# 一、物类映射库（八纯卦 × 六种物类）
# ═══════════════════════════════════════════

MANIFESTATION_TEMPLATES = {
    # ━━━ 人物（character）━━━
    "character": {
        0: "养育者、沉默的守护者，包容一切却鲜言自我。如大地之母，承载众生命运而不居功。",
        9: "觉醒者、革命者，一声惊雷打破沉默。如被压迫者中的先知，以突发唤醒沉睡的众魂。",
        18: "深渊行者、炼金术士，与危险共舞。如潜入禁忌之知的求索者，以恐惧为食，以未知为氧气。",
        27: "渗透者、风媒、无形之手，改变一切却不被看见。如流言的传播者、文化的塑造者。",
        36: "守门人、隐士、法官，划定边界不许逾越。如山中的苦修者，以静止为力量，以拒绝为尊严。",
        45: "明星、艺术家、演说家，光芒四射但内心渴求依附。如燃烧自己照亮他人的火炬，美丽而中空。",
        54: "商人、外交官、艺人，以交换和悦纳为生。如市场中的调停者，用笑容缝合差异。",
        63: "立法者、开拓者，一身铁骨，不容侵犯。如建立秩序的征服者，以命名切割混沌。",
    },

    # ━━━ 植物（plant）━━━
    "plant": {
        0: "地衣、苔藓，覆盖大地，无花无果却生生不息。如最卑微的覆盖者，以沉默延续生命。",
        9: "春笋、惊雷木，破土而出，一日三尺。如被压抑后骤然爆发的生命力，带着响声生长。",
        18: "深海藻、幽兰，生于暗处，以阴湿为养。如水底的水草，不见阳光却自有呼吸。",
        27: "蒲公英、藤蔓，随风而散，无孔不入。如最轻的种子，借风之力抵达最远的地方。",
        36: "崖柏、石缝松，扎根绝壁，静止如雕塑。如拒绝肥沃的孤独者，以贫瘠为土壤。",
        45: "满树繁花，灿烂夺目，但根系很浅。如樱花，以极致的绚烂宣告短暂的轮回。",
        54: "含羞草、向日葵，开合有度，向光而笑。如敏感的回应者，以姿态交换阳光。",
        63: "参天古木，主干笔直，枝桠如剑。如森林中的王者，以高度定义空间。",
    },

    # ━━━ 建筑（architecture）━━━
    "architecture": {
        0: "大地母殿、地宫，与土地融为一体。如被大地吞噬的建筑，从土中来，归土中去。",
        9: "钟楼、瞭望塔，以惊醒为功能。如村庄中的警报者，一声钟响唤醒沉睡的方圆。",
        18: "深井、地下迷宫、水闸，以幽深为结构。如通往地下世界的入口，光在此处被吞噬。",
        27: "通风塔、廊桥，无形之风得以穿行。如建筑的呼吸系统，风过而不留痕。",
        36: "城墙、关卡、堡垒，以阻断为使命。如文明的边界线，划分内外，拒绝流动。",
        45: "灯塔、剧院、广场，为聚集与展示而生。如城市的眼睛和喉咙，发光并呼喊。",
        54: "市集、交易所、温泉浴场，以交流为功能。如人群的交汇点，差异在此相遇。",
        63: "高塔、纪念碑，象征权威与秩序。如刺破天空的箭头，宣告人类对空间的征服。",
    },

    # ━━━ 自然（nature）━━━
    "nature": {
        0: "厚土、旷野，静默承载万物。如无边的大地，不拒绝任何一粒种子，也不挽留任何一阵风。",
        9: "春雷、地震、火山喷发，突发而不可预测。如大地的喷嚏，瞬间改变地貌。",
        18: "深潭、暗河、寒潮，幽深而危险。如大地的伤口，反射着天空却不接纳阳光。",
        27: "微风、季风、沙尘暴，无形却改变地貌。如空气的手，温柔或暴烈地重塑世界。",
        36: "悬崖、冰川、冻土，静止而拒绝。如时间的疤痕，拒绝融化，拒绝生长。",
        45: "野火、霞光、极光，美丽而短暂。如天空的伤口，燃烧或绚烂，然后归于黑暗。",
        54: "湖泊、沼泽、温泉，以交换滋养万物。如大地上的镜子，映照天空也映照深渊。",
        63: "晴空万里，天行刚健。如纯粹的空间，不为任何云停留，不为任何鸟弯曲。",
    },

    # ━━━ 事件（event）━━━
    "event": {
        0: "丰收、大赦、集体迁徙、安葬。如大地的呼吸——吸入一切，呼出一切，周期循环。",
        9: "起义、政变、突发灾难、惊醒。如被压制的弹簧突然释放，秩序在瞬间崩塌。",
        18: "沉船、探险、阴谋曝光、深渊凝视。如真相浮出水面，带着危险的气息。",
        27: "流言传播、风俗改变、信息泄露。如无形之风穿过人群，改变却不被察觉。",
        36: "停战、封锁、禁令、边界划定。如运动的突然停止，一切被冻结在某一帧。",
        45: "庆典、革命性的公开演讲、大火。如光芒的集中爆发，照亮所有人的脸。",
        54: "签约、贸易协定、和亲、狂欢节。如差异的交汇，以契约驯化冲突。",
        63: "奠基仪式、法令颁布、加冕典礼。如秩序的降临，以命名切割混沌。",
    },

    # ━━━ 器物（object）━━━
    "object": {
        0: "鼎、瓮、粮仓、地契。如大地的容器，承载而不显露。",
        9: "战鼓、警钟、炸药、启动键。如惊醒的工具，一触即发。",
        18: "镜子、井、锁、毒药。如深渊的入口，映照或封闭。",
        27: "风筝、风铃、信鸽、筛子。如风的玩具，无形之力的有形载体。",
        36: "门闩、盾、墓碑、界碑。如静止的宣言，拒绝即存在。",
        45: "火炬、灯笼、画布、舞台。如光明的器具，燃烧自己照亮他物。",
        54: "钱币、酒杯、契约书、乐器。如交换的媒介，差异的等价物。",
        63: "王冠、权杖、印玺、天文仪。如秩序的符号，以物质承载权力。",
    },
}


# ═══════════════════════════════════════════
# 二、现象词汇库（八卦协议 × 四维度感官）
# ═══════════════════════════════════════════

PHENOMENON_LEXICON = {
    0: {  # 坤 ☷ 承载
        "visual": ["暗沉", "大地色", "无边无际", "厚重的阴影", "土壤的肌理"],
        "sound": ["寂静", "低沉的嗡鸣", "大地呼吸", "远方的闷响", "尘埃落地"],
        "motion": ["缓慢", "厚重", "不可动摇", "下沉", "铺展", "包容"],
        "mood": ["安宁", "压抑", "孕育", "沉重", "沉默的耐心", "母亲的疲倦"],
    },
    9: {  # 震 ☳ 激变
        "visual": ["闪电", "裂痕", "突如其来的光芒", "碎片飞散", "颤抖的地面"],
        "sound": ["惊雷", "爆裂声", "碎裂", "轰鸣", "金属扭曲"],
        "motion": ["骤发", "颤抖", "颠覆", "弹跳", "冲破", "惊醒"],
        "mood": ["惊恐", "兴奋", "觉醒", "战栗", "突如其来的清晰", "破坏的快感"],
    },
    18: {  # 坎 ☵ 深渊
        "visual": ["幽暗", "深水反光", "漩涡", "潮湿的幽光", "水下折射"],
        "sound": ["水滴", "暗流", "低吼", "回声", "溺水的沉默"],
        "motion": ["陷溺", "涡旋", "吞噬", "下沉", "渗透", "淹没"],
        "mood": ["恐惧", "诱惑", "沉郁", "幽闭", "被吸引的战栗", "深不见底的好奇"],
    },
    27: {  # 巽 ☴ 渗透
        "visual": ["微动", "气流扰动", "无形之痕", "飘散的尘埃", "弯曲的光线"],
        "sound": ["低语", "风声", "细碎", "沙沙", "远处传来的消息"],
        "motion": ["渗透", "盘旋", "无孔不入", "飘散", "迂回", "潜移默化"],
        "mood": ["不安", "好奇", "被窥视", "隐约的不祥", "看不见的陪伴", "蔓延的焦虑"],
    },
    36: {  # 艮 ☶ 止界
        "visual": ["巨石", "高墙", "阻隔", "阴影的边界", "不可逾越的轮廓"],
        "sound": ["沉闷回响", "寂静", "回声", "脚步停止", "呼吸凝滞"],
        "motion": ["静止", "凝固", "拒绝", "阻挡", "拦截", "定格"],
        "mood": ["肃穆", "压抑", "安全", "被困", "拒绝的尊严", "边界的孤独"],
    },
    45: {  # 离 ☲ 显文明
        "visual": ["火光", "绚丽", "闪耀", "刺目的红", "跳动的影"],
        "sound": ["燃烧", "欢呼", "高音", "爆裂", "鼓掌"],
        "motion": ["升腾", "扩散", "依附", "跳跃", "照亮", "衰减"],
        "mood": ["热情", "空虚", "渴望", "狂欢", "明极反晦的预感", "被看见的焦虑"],
    },
    54: {  # 兑 ☱ 交换
        "visual": ["镜面", "水光", "笑颜", "反射", "流动的光泽"],
        "sound": ["笑声", "低语", "金属碰撞", " splash", "硬币落地"],
        "motion": ["交换", "流动", "悦纳", "触碰", "传递", "交易"],
        "mood": ["喜悦", "轻浮", "诱惑", "满足", "交换后的空虚", "连接的渴望"],
    },
    63: {  # 乾 ☰ 创序
        "visual": ["刺目白光", "几何线条", "金属锋芒", "清晰的分割", "无限延伸"],
        "sound": ["轰鸣", "号角", "金石之声", "整齐的步伐", "宣告"],
        "motion": ["高速推进", "不可阻挡", "直切", "扩张", "征服", "定义"],
        "mood": ["庄严", "孤高", "决绝", "凛冽", "绝对的自信", "创造者的不安"],
    },
}


# ═══════════════════════════════════════════
# 三、变化与势能叙事库
# ═══════════════════════════════════════════

# 3.1 卦变过渡描述（核心子集：纯卦之间的经典过渡）
# 格式: (from_hex, to_hex) -> 过渡叙事
TRANSITION_NARRATIVES = {
    # 乾坤对变
    (0, 63): "大地隆起，化为刺破苍穹的高峰。沉默的承载者终于开口，以秩序的名义切割混沌。",
    (63, 0): "高塔崩塌，化为大地的一部分。秩序的残骸被大地包容，铁骨归于泥土。",

    # 坎离对变
    (18, 45): "深渊之中，一簇幽光忽然亮起。黑暗的水底燃起火焰，危险与美丽在此交汇。",
    (45, 18): "火焰燃尽，余烬沉入黑暗的水底。光明的残骸被深渊吞噬，灰烬归于暗流。",

    # 震巽对变
    (9, 27): "惊雷之后，风起于无形。爆发的碎片被气流裹挟，化为漫天的尘埃与消息。",
    (27, 9): "风卷残云，雷声在云层中酝酿。无形的渗透终于累积成爆发的临界点。",

    # 艮兑对变
    (36, 54): "山岳裂开，泉水涌出。静止的边界开始流动，拒绝化为交换。",
    (54, 36): "湖泊干涸，化为盐碱之地。流动的交换凝固成边界，泉眼被岩石封死。",

    # 经典单向过渡
    (0, 9): "沉睡的大地，被雷声惊醒。土壤裂开，新芽带着响声破土。",
    (9, 0): "惊雷过后，大地重新闭合。爆发的碎片被土壤覆盖，归于沉默。",
    (0, 45): "地下之火涌出地面，光明照亮黑暗。大地的深处原来藏着燃烧的心脏。",
    (45, 0): "火焰燃尽，光芒沉入大地。曾经绚烂的灰烬成为土壤的养分。",
    (18, 0): "深渊之水渗入大地，被土壤吸收。危险被包容，暗流化为湿润。",
    (0, 18): "大地裂开，深渊涌出。沉默的承载者暴露出内在的伤口。",
    (63, 45): "白昼燃起火光，权威化为展示。秩序的创造者在燃烧中显露面容。",
    (45, 63): "火光冲天，化为白昼。燃烧终将被更宏大的秩序所覆盖。",
    (63, 9): "秩序之中，一声惊雷炸响。铁律被裂缝穿透，完美出现裂痕。",
    (9, 63): "惊雷之后，新的秩序建立。破坏者成为立法者，混乱中诞生规则。",
    (36, 9): "沉寂已久的山岩，突然迸出第一道裂痕。静止的边界开始颤抖。",
    (9, 36): "震动撞上边界，静止与运动对抗。雷声在山谷中回荡，最终被岩石吸收。",
    (54, 45): "交换的媒介被点燃，交易化为火焰。笑声中升起烟雾，契约在燃烧。",
    (45, 54): "火光映照水面，美丽开始交换。燃烧之后的余温成为交易的筹码。",
}

# 3.2 势能积累阶段描述
POTENTIAL_STAGE_NARRATIVE = [
    {
        "range": (0.0, 0.3),
        "ratio_label": "平静",
        "description": "微澜未起，一切尚在平静中。",
        "atmosphere": "此地安静如常，仿佛什么都没有发生。风过无痕，水静无波。",
        "warning": "",
    },
    {
        "range": (0.3, 0.7),
        "ratio_label": "积蓄",
        "description": "暗流涌动，不可名状的不安正在积蓄。",
        "atmosphere": "空气中弥漫着某种难以言喻的紧张，像暴风雨前的闷热。细微的裂纹正在不可见处蔓延。",
        "warning": "敏锐的观察者已能感知到某种变化的前兆。",
    },
    {
        "range": (0.7, 1.0),
        "ratio_label": "临界",
        "description": "临界将至，连空气都变得锋利。",
        "atmosphere": "每一息都可能成为最后一息平静，结构在看不见的深处发出呻吟。万物屏息，等待第一声破裂。",
        "warning": "建议提高观测频率，准备记录突变。",
    },
    {
        "range": (1.0, 999.0),
        "ratio_label": "爆发",
        "description": "势已满盈，一触即发。",
        "atmosphere": "再无一息可等。反转、爆发、错卦——某种根本性的转变已不可避免。旧结构正在自我瓦解的边缘。",
        "warning": "突变 imminent。所有关联实体应做好应变准备。",
    },
]


# ═══════════════════════════════════════════
# 四、公共接口函数
# ═══════════════════════════════════════════

def get_manifestation(protocol_hex: int, category: str = "character") -> str:
    """
    获取指定卦值在指定物类下的映射描述。

    Args:
        protocol_hex: 纯卦值（0, 9, 18, 27, 36, 45, 54, 63）
        category: 物类，可选: character/plant/architecture/nature/event/object

    Returns:
        物类映射描述字符串
    """
    cat = MANIFESTATION_TEMPLATES.get(category, MANIFESTATION_TEMPLATES["character"])
    return cat.get(protocol_hex, "未知之物，尚未被命名。")


def get_phenomenon(protocol_hex: int, dimension: str = "visual") -> List[str]:
    """
    获取指定卦值在指定感官维度下的现象词汇列表。

    Args:
        protocol_hex: 纯卦值
        dimension: 维度，可选: visual/sound/motion/mood

    Returns:
        词汇列表
    """
    phenom = PHENOMENON_LEXICON.get(protocol_hex, {})
    return phenom.get(dimension, ["不可名状"])


def get_transition_narrative(from_hex: int, to_hex: int) -> Optional[str]:
    """
    获取卦变过渡描述。
    优先查找精确匹配，其次查找反向匹配，最后返回 None（由调用方使用通用模板）。
    """
    key = (from_hex, to_hex)
    if key in TRANSITION_NARRATIVES:
        return TRANSITION_NARRATIVES[key]
    # 尝试反向
    reverse_key = (to_hex, from_hex)
    if reverse_key in TRANSITION_NARRATIVES:
        desc = TRANSITION_NARRATIVES[reverse_key]
        # 简单反转（不完美，但可用）
        return f"逆行之变：{desc}"
    return None


def get_potential_stage(potential: float, V_thresh: float = 1.2) -> Dict:
    """
    根据势能值返回阶段描述。

    Args:
        potential: 当前势能值
        V_thresh: 阈值（默认1.2）

    Returns:
        包含 ratio_label, description, atmosphere, warning 的字典
    """
    ratio = potential / V_thresh if V_thresh > 0 else 0
    for stage in POTENTIAL_STAGE_NARRATIVE:
        lo, hi = stage["range"]
        if lo <= ratio < hi:
            return {
                "ratio": round(ratio, 3),
                "ratio_label": stage["ratio_label"],
                "description": stage["description"],
                "atmosphere": stage["atmosphere"],
                "warning": stage["warning"],
            }
    # fallback 到最后一个阶段
    last = POTENTIAL_STAGE_NARRATIVE[-1]
    return {
        "ratio": round(ratio, 3),
        "ratio_label": last["ratio_label"],
        "description": last["description"],
        "atmosphere": last["atmosphere"],
        "warning": last["warning"],
    }


def build_phenomenon_description(
    hex_val: int,
    category: str = "character",
    dimensions: List[str] = None,
) -> str:
    """
    构建综合现象描述。
    根据卦值和物类，组合现象词汇生成一段生动的场景描述。
    """
    if dimensions is None:
        dimensions = ["visual", "sound", "motion", "mood"]

    from codex import get_gua
    gua = get_gua(hex_val)
    protocol_hex = _get_pure_hex_for_protocol(gua["protocol"])

    # 获取物类映射
    manifestation = get_manifestation(protocol_hex, category)

    # 获取现象词汇
    words = {}
    for dim in dimensions:
        words[dim] = get_phenomenon(protocol_hex, dim)

    # 组合描述
    parts = [
        f"如{manifestation.split('。')[0]}。",
    ]
    if "visual" in words:
        parts.append(f"视觉上，{words['visual'][0]}、{words['visual'][1]}。")
    if "sound" in words:
        parts.append(f"声音上，{words['sound'][0]}、{words['sound'][1]}。")
    if "motion" in words:
        parts.append(f"动态上，{words['motion'][0]}、{words['motion'][1]}。")
    if "mood" in words:
        parts.append(f"氛围上，{words['mood'][0]}、{words['mood'][1]}。")

    return " ".join(parts)


def _get_pure_hex_for_protocol(protocol: str) -> int:
    """根据协议名返回对应的纯卦值。"""
    protocol_map = {
        "承载": 0,
        "激变": 9,
        "深渊": 18,
        "渗透": 27,
        "止界": 36,
        "显文明": 45,
        "交换": 54,
        "创序": 63,
    }
    return protocol_map.get(protocol, 0)


# ═══════════════════════════════════════════
# 五、测试
# ═══════════════════════════════════════════

if __name__ == "__main__":
    print("=== 物类映射库测试 ===")
    for cat in ["character", "plant", "architecture", "nature", "event", "object"]:
        desc = get_manifestation(45, cat)
        print(f"\n离({cat}): {desc[:50]}...")

    print("\n\n=== 现象词汇库测试 ===")
    for dim in ["visual", "sound", "motion", "mood"]:
        words = get_phenomenon(18, dim)
        print(f"坎({dim}): {', '.join(words[:3])}")

    print("\n\n=== 卦变过渡测试 ===")
    for pair in [(18, 45), (45, 18), (36, 9), (0, 63)]:
        desc = get_transition_narrative(*pair)
        if desc:
            print(f"{pair}: {desc[:60]}...")
        else:
            print(f"{pair}: (无专属描述，需用通用模板)")

    print("\n\n=== 势能阶段测试 ===")
    for pot in [0.1, 0.5, 0.9, 1.1, 1.5]:
        stage = get_potential_stage(pot, V_thresh=1.2)
        print(f"势能 {pot:.1f} (比例 {stage['ratio']:.2f}): {stage['ratio_label']} — {stage['description']}")

    print("\n\n=== 综合现象描述测试 ===")
    print(build_phenomenon_description(45, "character"))
    print()
    print(build_phenomenon_description(18, "nature"))

    print("\n测试完成!")
