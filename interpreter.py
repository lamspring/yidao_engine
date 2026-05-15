# -*- coding: utf-8 -*-
"""
《易道动态世界引擎》v4.0 — 象法解释引擎 (XiangInterpreter)
解决"卦象如何成为万事万物"的问题，且绝不僵化。

核心原则：
  1. 卦象 ≠ 事物，卦象 = 关系结构 + 变化倾向
  2. 同一卦在不同尺度、邻域、历史下，显现为截然不同的实体
  3. 必须经过五层规则才生成具象，禁止 if hex==X then "水" 式硬映射
  4. 每次解释必须保留"未定域"：输出多个可能具象，由上层叙事 AI 选取
"""

from typing import Dict, List, Optional, Any
from codex import get_gua, get_trigram, get_protocol


# ═══════════════════════════════════════════
# 0. 基础语气库（八卦）
# ═══════════════════════════════════════════

_TRIGRAM_TONE = {
    0: {"name": "坤", "nature": "阴", "verb": "承载", "adj": "包容、沉静、柔顺",
        "structure": "纯阴闭合", "movement": "静藏", "open_close": "全闭"},
    1: {"name": "震", "nature": "阳", "verb": "惊醒", "adj": "突发、启动、裂变",
        "structure": "阳动于下", "movement": "突发", "open_close": "底开"},
    2: {"name": "坎", "nature": "阴", "verb": "陷溺", "adj": "隐藏、危险、深邃",
        "structure": "阳陷于中", "movement": "陷落", "open_close": "内开外合"},
    3: {"name": "巽", "nature": "阴", "verb": "渗透", "adj": "潜移、扩散、风化",
        "structure": "阴柔深入", "movement": "潜移", "open_close": "顶合底开"},
    4: {"name": "艮", "nature": "阳", "verb": "止息", "adj": "静止、边界、封印",
        "structure": "阳止于上", "movement": "静止", "open_close": "顶开底合"},
    5: {"name": "离", "nature": "阳", "verb": "照亮", "adj": "明亮、依附、文明",
        "structure": "外阳内阴", "movement": "外显", "open_close": "外开内合"},
    6: {"name": "兑", "nature": "阳", "verb": "开口", "adj": "交流、喜悦、毁折",
        "structure": "阳悦于外", "movement": "交流", "open_close": "顶开"},
    7: {"name": "乾", "nature": "阳", "verb": "开创", "adj": "刚健、纯粹、主动",
        "structure": "纯阳扩张", "movement": "刚健", "open_close": "全开"},
}


# ═══════════════════════════════════════════
# 1. 特殊卦结构语气覆盖（重要复合卦）
# ═══════════════════════════════════════════
# 格式: {卦值: "结构语气描述"}
# 未被覆盖的卦将基于上下卦动态组合
# 以下卦值已对照 codex.py 的先天二进制序逐一核验

_SPECIAL_GUA_TONE = {
    # ━━━ 乾坤消息（十二消息卦）━━━
    1:  "地雷复，一阳来复，生机初动于地下，反复其道",
    6:  "地泽临，居高临下，教思无穷，容保民无疆",
    7:  "地天泰，天地交泰，上下相通，阴阳交融而万物化生",
    15: "雷天大壮，四阳盛长，大者正也，壮勿妄动",
    55: "泽天夬，决也，刚决柔也，君子以施禄及下",
    59: "天风姤，遇也，一阴初生，柔遇刚而合",
    60: "天山遁，远遁避世，君子以远小人，不恶而严",
    56: "天地否，闭塞不通，阴阳隔绝而生机受阻",
    24: "风地观，观民设教，风行地上，瞻仰之象",
    32: "山地剥，阴盛阳消，剥落殆尽，硕果仅存",

    # ━━━ 水火既济/未济 ━━━
    21: "水火既济，事已成而守成为难，盛极将衰之局",
    42: "火水未济，事未成而希望在前，变动不居之势",

    # ━━━ 同人大有 ━━━
    61: "天火同人，志同道合，光明与同，群阳相聚",
    47: "火天大有，盛大丰有，光明普照，万物归附",

    # ━━━ 谦豫 ━━━
    4:  "地山谦，外卑内实，谦虚退让而内蕴坚贞",
    8:  "雷地豫，顺以动，悦乐预备，雷出于地",

    # ━━━ 随蛊 ━━━
    49: "泽雷随，随时而动，顺时顺势，从善如流",
    35: "山风蛊，腐败生变，积弊待振，山下有风",

    # ━━━ 噬嗑贲 ━━━
    41: "火雷噬嗑，咬合刑罚，明罚敕法，刚柔相济",
    37: "山火贲，文明以止，饰外扬中，文质彬彬",

    # ━━━ 屯蒙 ━━━
    17: "水雷屯，刚柔始交而难生，万物初生之艰",
    34: "山水蒙，山下出泉，蒙昧初开，教化之始",

    # ━━━ 需讼 ━━━
    23: "水天需，云上于天，待时而动，不犯难行",
    58: "天水讼，上刚下险，险而健讼，争讼之道",

    # ━━━ 师比 ━━━
    2:  "地水师，行险而顺，聚众伐罪，出师之象",
    16: "水地比，亲比相依，地上有水，润泽万物",

    # ━━━ 小畜履 ━━━
    31: "风天小畜，密云不雨，蓄养待时，柔得位而上下应",
    62: "天泽履，履虎尾而不咥，礼行天下，谨慎前行",

    # ━━━ 咸恒 ━━━
    52: "泽山咸，感应无心，山泽通气，男女相感",
    11: "雷风恒，雷风相薄，恒久之道，刚柔皆应",

    # ━━━ 晋明夷 ━━━
    40: "火地晋，明出地上，柔进而上行，晋升之象",
    5:  "地火明夷，明入地中，晦其明也，内文明而外柔顺",

    # ━━━ 家人睽 ━━━
    29: "风火家人，正家而天下定，内助外和，家人之道",
    46: "火泽睽，乖也，上火下泽，二女同居其志不同行",

    # ━━━ 蹇解 ━━━
    20: "水山蹇，难也，见险而止，反身修德",
    10: "雷水解，动而免乎险，雷雨作而百果草木皆甲坼",

    # ━━━ 损益 ━━━
    38: "山泽损，损下益上，损有余而补不足",
    25: "风雷益，损上益下，自上下下，民说无疆",

    # ━━━ 萃升 ━━━
    48: "泽地萃，聚也，顺以说，刚中而应，故聚也",
    26: "地风升，柔以时升，巽而顺，积小以高大",

    # ━━━ 困井 ━━━
    50: "泽水困，穷也，险以说，困而不失其所亨",
    19: "水风井，改邑不改井，井养而不穷",

    # ━━━ 革鼎 ━━━
    53: "泽火革，去故也，水火相息，二女同居其志不相得",
    43: "火风鼎，取新也，木上有火，烹饪之象",

    # ━━━ 渐归妹 ━━━
    28: "风山渐，进也，女归吉也，循序渐进",
    14: "雷泽归妹，征凶无攸利，少女从长男",

    # ━━━ 丰旅 ━━━
    13: "雷火丰，大也，明以动，故丰",
    44: "火山旅，小亨，柔得中乎外而顺乎刚",

    # ━━━ 涣节 ━━━
    26: "风水涣，离也，风行水上，涣散离散",
    22: "水泽节，亨，苦节不可贞，泽上有水，节制之象",

    # ━━━ 中孚小过 ━━━
    30: "风泽中孚，信也，柔在内而刚得中，说而巽",
    12: "雷山小过，小者过而亨也，飞鸟遗之音",

    # ━━━ 无妄大过 ━━━
    57: "天雷无妄，无妄之灾，动而健，刚自外来而为主于内",
    51: "泽风大过，栋桡也，本末弱也，刚过而中",

    # ━━━ 颐大畜 ━━━
    33: "山雷颐，养也，山下有雷，颐中有物",
    39: "山天大畜，止而健，刚上而尚贤",
}


# ═══════════════════════════════════════════
# 2. 六爻位叙事（动爻时位判断）
# ═══════════════════════════════════════════

_YAO_LINE_NARRATIVE = {
    1: {
        "stage": "萌芽初生",
        "description": "初爻动，如种子破土，气机始动，极其稚嫩而充满潜力",
        "mood": "潜藏待发",
        "risk": "根基未稳，最易夭折",
    },
    2: {
        "stage": "内部调适",
        "description": "二爻动，如幼苗扎根，内在结构正在调整与巩固",
        "mood": "稳扎稳打",
        "risk": "固守一方，难有大成",
    },
    3: {
        "stage": "越界涉险",
        "description": "三爻动，如人行至门槛，正在越界、冒险，危机与转机并存",
        "mood": "危中有机",
        "risk": "过界则凶，进退维谷",
    },
    4: {
        "stage": "外部磨合",
        "description": "四爻动，如登堂入室，正与外部结构接触、碰撞、寻求接纳",
        "mood": "交涉事繁",
        "risk": "内外不调，上下猜忌",
    },
    5: {
        "stage": "主导变革",
        "description": "五爻动，如君临天下，处于主导地位的变化，影响全局",
        "mood": "权柄在握",
        "risk": "位高势危，一失足则倾覆",
    },
    6: {
        "stage": "穷极将反",
        "description": "上爻动，如日中则昃，物极必反，即将发生根本性反转",
        "mood": "盛极而衰",
        "risk": "亢龙有悔，过刚易折",
    },
}

# 静卦（无动爻）的生命阶段描述
_STATIC_STAGE = {
    "stage": "静守持中",
    "description": "卦象静止，阴阳结构处于相对稳定期，趋势内蕴而未发",
    "mood": "潜藏待机",
    "risk": "久静则僵，缺乏变化",
}


# ═══════════════════════════════════════════
# 3. 尺度映射框架
# ═══════════════════════════════════════════

_SCALE_FRAMEWORK = {
    "micro": {
        "name": "微观",
        "entity_type": "元素、微粒、微小生物、局部势态",
        "template": "如{adj}的{element}，{movement}于微末之间",
        "examples": ["一滴水", "一粒火星", "一只飞虫", "一丝微风"],
    },
    "meso": {
        "name": "中观",
        "entity_type": "人物、情绪、小型团体、器物",
        "template": "如{adj}的{entity}，{movement}于人际之间",
        "examples": ["一个人", "一场聚会", "一件器物", "一次交易"],
    },
    "macro": {
        "name": "宏观",
        "entity_type": "文明、国家、地形、宗教、神祇",
        "template": "如{adj}的{civilization}，{movement}于历史长河",
        "examples": ["一个帝国", "一座山脉", "一种信仰", "一个时代"],
    },
    "cosmic": {
        "name": "宇观",
        "entity_type": "宇宙周期、道趋势、世界命运",
        "template": "如{adj}的{cosmos}，{movement}于造化之枢",
        "examples": ["一个纪元", "阴阳循环", "道之流转", "天地大化"],
    },
}


# ═══════════════════════════════════════════
# 4. 意图具象模板
# ═══════════════════════════════════════════

# 每种意图在不同尺度下如何具象化
# 格式: intent -> {scale -> 描述模板}
_INTENT_TEMPLATES = {
    "character": {
        "micro": "一个带有{adj}气质的小型生灵或精灵",
        "meso": "一个{adj}的人，正处于{stage}，{movement}",
        "macro": "一个{adj}的民族性格或文明人格",
        "cosmic": "一种{adj}的宇宙原型或道之化身",
    },
    "object": {
        "micro": "一粒{adj}的物质或微观结构",
        "meso": "一件{adj}的器物或建筑，{movement}",
        "macro": "一座{adj}的地形或遗迹，见证{stage}",
        "cosmic": "一种{adj}的宇宙法则具现",
    },
    "landscape": {
        "micro": "一片{adj}的微观地形",
        "meso": "一处{adj}的景致，{movement}",
        "macro": "一片{adj}的大地形胜，正处于{stage}",
        "cosmic": "一个{adj}的宇宙景观或纪元地貌",
    },
    "faction": {
        "micro": "一股{adj}的微小势力",
        "meso": "一个{adj}的小团体或家族，{movement}",
        "macro": "一个{adj}的国家或文明，正处于{stage}",
        "cosmic": "一种{adj}的宇宙阵营或天道倾向",
    },
    "god": {
        "micro": "一个{adj}的微小神性碎片",
        "meso": "一位{adj}的本土神灵或精怪",
        "macro": "一尊{adj}的大神或文明主神，{movement}",
        "cosmic": "至高{adj}的道之显化或创世本源",
    },
    "event": {
        "micro": "一场{adj}的微小变故",
        "meso": "一次{adj}的事件或遭遇，{movement}",
        "macro": "一场{adj}的历史转折，正处于{stage}",
        "cosmic": "一个{adj}的宇宙级灾变或创生",
    },
}

# 默认意图（当传入的 intent 不在上表时）
_DEFAULT_INTENT = "event"


# ═══════════════════════════════════════════
# 5. 邻域关系修饰词库
# ═══════════════════════════════════════════

_NEIGHBOR_MODIFIERS = {
    # 基于关系词生成上下文修饰
    "对冲": {
        "tone": "对立、撕裂、极化",
        "effect": "如孤岛置于逆流，内外截然相反，张力极大",
        "mood_shift": "紧张",
    },
    "交融": {
        "tone": "混合、渗透、共生",
        "effect": "如鱼入水，内外浑然一体，相得益彰",
        "mood_shift": "和谐",
    },
    "共鸣": {
        "tone": "呼应、叠加、共振",
        "effect": "如山谷回音，同气相求，力量倍增",
        "mood_shift": "激昂",
    },
    "克制": {
        "tone": "压制、侵蚀、消耗",
        "effect": "如强弩之末，外部压力持续消耗其生机",
        "mood_shift": "压抑",
    },
    "相生": {
        "tone": "滋养、助长、孕育",
        "effect": "如春雨润物，外部环境正为其提供生长之机",
        "mood_shift": "欣欣向荣",
    },
    "通气": {
        "tone": "呼应、交换、流通",
        "effect": "如呼吸相通，内外之间存在着隐秘的通道",
        "mood_shift": "通畅",
    },
    # 兜底
    "default": {
        "tone": "交织、影响",
        "effect": "与周围环境保持着某种动态平衡",
        "mood_shift": "平和",
    },
}


def _classify_relation(relation_term: str) -> str:
    """根据关系词归类到修饰类别。"""
    for key in ["对冲", "交融", "共鸣", "克制", "相生", "通气"]:
        if key in relation_term:
            return key
    return "default"


# ═══════════════════════════════════════════
# 6. 道控制器影响规则
# ═══════════════════════════════════════════

_DAO_INFLUENCE_RULES = [
    # (global_yang_ratio 阈值, 倾向, 对阳卦影响, 对阴卦影响)
    (0.75, "极阳", "过刚易折，阳极将转", "阴极求生，暗流涌动"),
    (0.60, "偏阳", "阳势正盛，宜进忌骄", "阴势受抑，隐忍待机"),
    (0.40, "中和", "阴阳平衡，冲气为和", "阴阳平衡，冲气为和"),
    (0.25, "偏阴", "阴势渐浓，收敛为宜", "阴势正盛，静藏得利"),
    (0.00, "极阴", "阳微难振，潜龙勿用", "阴极生阳，转机将萌"),
]


def _get_dao_influence(global_yang_ratio: float, hexagram_yang_ratio: float) -> str:
    """根据世界阴阳大势与卦的阴阳属性，生成道控制器影响描述。"""
    # 找到当前世界倾向
    world_tendency = None
    for threshold, tendency, yang_effect, yin_effect in _DAO_INFLUENCE_RULES:
        if global_yang_ratio >= threshold:
            world_tendency = (tendency, yang_effect, yin_effect)
            break
    if world_tendency is None:
        world_tendency = _DAO_INFLUENCE_RULES[-1]

    tendency, yang_effect, yin_effect = world_tendency
    # 判断该卦偏阳还是偏阴
    if hexagram_yang_ratio > 0.6:
        return f"【道势】世界处于{tendency}阶段，{yang_effect}"
    elif hexagram_yang_ratio < 0.4:
        return f"【道势】世界处于{tendency}阶段，{yin_effect}"
    else:
        return f"【道势】世界处于{tendency}阶段，此卦阴阳调和，不受大势偏颇"


# ═══════════════════════════════════════════
# 7. 结构语气生成器
# ═══════════════════════════════════════════

def _build_structure_tone(hexagram: int) -> Dict[str, str]:
    """
    构建卦的结构语气。优先使用特殊覆盖，否则基于上下卦动态组合。
    """
    v = int(hexagram) & 0b111111

    # 优先特殊覆盖
    if v in _SPECIAL_GUA_TONE:
        tone_text = _SPECIAL_GUA_TONE[v]
        upper_idx = (v >> 3) & 0b111
        lower_idx = v & 0b111
        yang_cnt = bin(v).count('1')
        return {
            "hexagram": v,
            "name": get_gua(v)["name"],
            "tone": tone_text,
            "yin_yang_balance": f"{yang_cnt}阳{6-yang_cnt}阴",
            "yang_ratio": yang_cnt / 6.0,
            "movement": _TRIGRAM_TONE[upper_idx]["movement"],
            "open_close": _TRIGRAM_TONE[upper_idx]["open_close"],
            "upper": _TRIGRAM_TONE[upper_idx],
            "lower": _TRIGRAM_TONE[lower_idx],
            "is_special": True,
        }

    # 动态组合
    upper_idx = (v >> 3) & 0b111
    lower_idx = v & 0b111
    upper = _TRIGRAM_TONE[upper_idx]
    lower = _TRIGRAM_TONE[lower_idx]
    yang_cnt = bin(v).count('1')

    if upper_idx == lower_idx:
        tone_text = f"纯粹{upper['adj']}之象，内外一致，{upper['verb']}之力贯穿始终"
    else:
        # 判断上下卦的阴阳关系
        if upper["nature"] == "阳" and lower["nature"] == "阴":
            relation = "外刚内柔"
        elif upper["nature"] == "阴" and lower["nature"] == "阳":
            relation = "外柔内刚"
        elif upper["nature"] == "阳" and lower["nature"] == "阳":
            relation = "表里皆刚"
        else:
            relation = "表里皆柔"
        tone_text = (
            f"{relation}，外{upper['verb']}而内{lower['verb']}，"
            f"如{upper['adj']}之表包裹着{lower['adj']}之里"
        )

    return {
        "hexagram": v,
        "name": get_gua(v)["name"],
        "tone": tone_text,
        "yin_yang_balance": f"{yang_cnt}阳{6-yang_cnt}阴",
        "yang_ratio": yang_cnt / 6.0,
        "movement": f"外{upper['movement']}而内{lower['movement']}",
        "open_close": f"外{upper['open_close']}而内{lower['open_close']}",
        "upper": upper,
        "lower": lower,
        "is_special": False,
    }


# ═══════════════════════════════════════════
# 8. 历史趋势解读
# ═══════════════════════════════════════════

def _synthesize_history(
    hexagram: int,
    recent_hexagrams: List[int],
    long_term_dominant: int,
    volatility: float,
) -> str:
    """基于历史序列生成趋势描述。"""
    current_name = get_gua(hexagram)["name"]
    dominant_name = get_gua(long_term_dominant)["name"]

    parts = []

    # 长期主导 vs 当前
    if hexagram == long_term_dominant:
        parts.append(f"此单元本质为{dominant_name}，当前仍处于其本性之中")
    else:
        current_tone = _build_structure_tone(hexagram)["tone"][:20]
        dominant_tone = _build_structure_tone(long_term_dominant)["tone"][:20]
        parts.append(
            f"此单元长期以{dominant_name}为本质（{dominant_tone}...），"
            f"当前暂显为{current_name}（{current_tone}...）"
        )

    # 变化频率
    if volatility > 0.7:
        parts.append("变化极剧，如狂飙骤雨，难以捉摸其定形")
    elif volatility > 0.4:
        parts.append("变动频繁，如流云走马，时过境迁")
    elif volatility > 0.1:
        parts.append("偶有变动，如季节更迭，大体有常")
    else:
        parts.append("久静少变，如磐石深潭，根深蒂固")

    # 近期序列趋势
    if len(recent_hexagrams) >= 2:
        if all(h == recent_hexagrams[0] for h in recent_hexagrams):
            parts.append(f"最近{len(recent_hexagrams)}息持续为{get_gua(recent_hexagrams[0])['name']}，稳态延续")
        else:
            names = [get_gua(h)["name"] for h in recent_hexagrams]
            parts.append(f"近期卦序：{'→'.join(names)}")

    return "；".join(parts)


# ═══════════════════════════════════════════
# 9. 具象生成器（possible_manifestations）
# ═══════════════════════════════════════════

def _generate_manifestations(
    structure: Dict[str, str],
    scale: str,
    active_lines: List[int],
    neighbor_profile: Dict[str, Any],
    history_narrative: str,
) -> Dict[str, str]:
    """
    为不同意图生成可能具象。每个具象都是基于规则的动态生成，非硬编码。
    """
    tone = structure["tone"]
    movement = structure["movement"]
    upper = structure["upper"]
    lower = structure["lower"]

    # 动爻影响（描述片段，不带句首标点）
    active_desc = ""
    if active_lines:
        if len(active_lines) == 1:
            line = active_lines[0]
            active_desc = f"第{line}爻动，{_YAO_LINE_NARRATIVE[line]['stage']}"
        else:
            lines_str = "、".join([f"第{l}爻" for l in active_lines])
            active_desc = f"多爻齐动（{lines_str}），结构剧烈重构"
    else:
        active_desc = "静守其位"

    # 邻域影响
    relation = neighbor_profile.get("relation_term", "")
    relation_class = _classify_relation(relation)
    modifier = _NEIGHBOR_MODIFIERS[relation_class]
    neighbor_effect = modifier["effect"]

    # 构建模板变量
    adj = upper["adj"]
    adj_inner = lower["adj"]
    stage = _YAO_LINE_NARRATIVE[active_lines[0]]["stage"] if active_lines else "静守期"

    # 生成各意图具象
    manifests = {}
    for intent, templates in _INTENT_TEMPLATES.items():
        template = templates.get(scale, templates.get("meso"))
        # 根据结构语气定制
        if intent == "character":
            desc = (
                f"一个{adj}之人，{active_desc}，"
                f"其态如{movement}，{neighbor_effect}"
            )
        elif intent == "object":
            if "外显" in movement or "照亮" in upper["verb"]:
                obj_type = "发光之物"
            elif "静止" in movement or "止息" in upper["verb"]:
                obj_type = "稳固之器"
            elif "渗透" in movement or "潜移" in upper["verb"]:
                obj_type = "流动之物"
            elif "陷落" in movement or "陷溺" in upper["verb"]:
                obj_type = "幽深之器"
            else:
                obj_type = "寻常之物"
            desc = (
                f"一件{obj_type}，其性{tone[:30]}...，"
                f"{active_desc}，{neighbor_effect}"
            )
        elif intent == "landscape":
            if upper["name"] in ["艮", "坤"]:
                terrain = "山岳大地"
            elif upper["name"] in ["坎", "兑"]:
                terrain = "水泽湖泊"
            elif upper["name"] in ["离", "乾"]:
                terrain = "天光火域"
            elif upper["name"] in ["震", "巽"]:
                terrain = "风雷林木"
            else:
                terrain = "混成之地"
            desc = (
                f"一片{terrain}，其势{tone[:30]}...，"
                f"{active_desc}，{neighbor_effect}"
            )
        elif intent == "faction":
            desc = (
                f"一股{adj}的势力，{active_desc}，"
                f"其势{movement}，{neighbor_effect}"
            )
        elif intent == "god":
            desc = (
                f"一尊{adj}的神性，{active_desc}，"
                f"{movement}于天地之间，{neighbor_effect}"
            )
        elif intent == "event":
            if active_lines:
                event_type = "变故"
            elif "突发" in movement or "惊醒" in upper["verb"]:
                event_type = "突发之事"
            elif "静止" in movement:
                event_type = "凝滞之局"
            else:
                event_type = "渐变之势"
            desc = (
                f"一场{event_type}，其因{tone[:30]}...，"
                f"{active_desc}，{neighbor_effect}"
            )
        else:
            desc = template.format(adj=adj, stage=stage, movement=movement)

        manifests[intent] = desc

    return manifests


# ═══════════════════════════════════════════
# 10. 核心解释引擎类
# ═══════════════════════════════════════════

class XiangInterpreter:
    """
    象法解释引擎。

    输入：摄像头数据包（来自 WorldCamera.capture()）
    输出：易象描述符（Yao Descriptor）

    使用方式：
        from observer import WorldCamera
        from interpreter import XiangInterpreter

        cam = WorldCamera(world)
        interpreter = XiangInterpreter()

        packet = cam.capture()
        descriptor = interpreter.interpret(packet)
        print(descriptor["change_narrative"])
        print(descriptor["possible_manifestations"]["character"])
    """

    def __init__(self, camera=None):
        """
        camera: 可选的 WorldCamera 实例。若提供，interpret() 可不传 packet 自动采集。
        """
        self.camera = camera

    def interpret(self, packet: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        执行五层解释，生成易象描述符。

        Args:
            packet: 摄像头数据包。若为 None 且 camera 已设置，则自动采集。

        Returns:
            Yao Descriptor (dict)
        """
        if packet is None:
            if self.camera is None:
                raise ValueError("未提供 packet 且未设置 camera，无法解释")
            packet = self.camera.capture()

        # 提取数据
        hexagram = packet["data"]["hexagram"]
        active_lines = packet["data"]["active_lines"]
        neighbor_profile = packet["data"]["neighbor_profile"]
        history = packet["data"]["history"]
        scale = packet.get("scale", "meso")
        intent = packet.get("intent", "event")
        global_yang = packet.get("_meta", {}).get("global_yang_ratio", 0.5)

        # ═══════════════════════════════════
        # 第一层：阴阳结构定性
        # ═══════════════════════════════════
        structure = _build_structure_tone(hexagram)
        structural_tone = structure["tone"]

        # ═══════════════════════════════════
        # 第二层：时位判断
        # ═══════════════════════════════════
        if active_lines:
            primary_line = active_lines[0]
            line_info = _YAO_LINE_NARRATIVE[primary_line]
            life_stage = line_info["stage"]
            if len(active_lines) == 1:
                change_narrative = (
                    f"{line_info['description']}。"
                    f"此卦正处于{life_stage}，"
                    f"{line_info['mood']}，需警惕{line_info['risk']}"
                )
            else:
                lines_str = "、".join([str(l) for l in active_lines])
                change_narrative = (
                    f"多爻齐动（{lines_str}），结构剧烈重构，"
                    f"如大厦将倾又逢地震，内外交困而转机暗伏"
                )
        else:
            static = _STATIC_STAGE
            life_stage = static["stage"]
            change_narrative = (
                f"{static['description']}。"
                f"此卦处于{life_stage}，{static['mood']}，"
                f"需注意{static['risk']}"
            )

        # ═══════════════════════════════════
        # 第三层：尺度映射
        # ═══════════════════════════════════
        scale_info = _SCALE_FRAMEWORK.get(scale, _SCALE_FRAMEWORK["meso"])
        scale_desc = f"{scale_info['name']}（{scale_info['entity_type']}）"

        # ═══════════════════════════════════
        # 第四层：邻域场上下文
        # ═══════════════════════════════════
        relation = neighbor_profile.get("relation_term", "")
        relation_class = _classify_relation(relation)
        modifier = _NEIGHBOR_MODIFIERS[relation_class]

        neighbor_hex = neighbor_profile.get("dominant_hexagram", 0)
        neighbor_name = get_gua(neighbor_hex)["name"]
        context_modifier = (
            f"邻域主导为{neighbor_name}卦，"
            f"与焦点卦呈'{relation}'之势。"
            f"{modifier['effect']}"
        )

        # ═══════════════════════════════════
        # 第五层：历史积累与人格化
        # ═══════════════════════════════════
        historical_trend = _synthesize_history(
            hexagram,
            history.get("recent_hexagrams", []),
            history.get("long_term_dominant", hexagram),
            history.get("volatility", 0.0),
        )

        # ═══════════════════════════════════
        # possible_manifestations
        # ═══════════════════════════════════
        manifestations = _generate_manifestations(
            structure, scale, active_lines, neighbor_profile, historical_trend
        )

        # ═══════════════════════════════════
        # 道控制器影响
        # ═══════════════════════════════════
        dao_effect = _get_dao_influence(global_yang, structure["yang_ratio"])

        # ═══════════════════════════════════
        # 组装 Yao Descriptor
        # ═══════════════════════════════════
        descriptor = {
            "primary_structure": structure["name"],
            "structural_tone": structural_tone,
            "active_line": active_lines[0] if active_lines else -1,
            "life_stage": life_stage,
            "change_narrative": change_narrative,
            "scale": scale_desc,
            "context_modifier": context_modifier,
            "historical_trend": historical_trend,
            "dao_influence": dao_effect,
            "possible_manifestations": manifestations,
            "_meta": {
                "yang_ratio": round(structure["yang_ratio"], 3),
                "yin_yang_balance": structure["yin_yang_balance"],
                "movement": structure["movement"],
                "open_close": structure["open_close"],
                "is_special_gua": structure["is_special"],
                "relation_class": relation_class,
            }
        }

        return descriptor

    def interpret_minimal(self, mini_packet: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        基于极简帧生成简化版描述符。
        适合性能受限场景，保留核心语义但弱化人格化与历史。
        """
        if mini_packet is None:
            if self.camera is None:
                raise ValueError("未提供 packet 且未设置 camera")
            mini_packet = self.camera.capture_minimal()

        hexagram = mini_packet["center_hex"]
        active_line = mini_packet.get("active_line")
        scale = mini_packet.get("scale", "meso")
        intent = mini_packet.get("intent", "event")
        neighbor_hex = mini_packet.get("neighbor_dominant", 0)

        structure = _build_structure_tone(hexagram)
        neighbor_name = get_gua(neighbor_hex)["name"]

        # 极简生命阶段
        if active_line and active_line > 0:
            stage = _YAO_LINE_NARRATIVE[active_line]["stage"]
            change = f"第{active_line}爻动，{stage}"
        else:
            stage = "静守持中"
            change = "卦象静止，阴阳结构稳定"

        # 极简具象（只生成请求的 intent + 通用 event）
        manifests = {}
        for key in [intent, "event"]:
            if key in _INTENT_TEMPLATES:
                template = _INTENT_TEMPLATES[key].get(scale, _INTENT_TEMPLATES[key]["meso"])
                manifests[key] = (
                    f"{structure['tone'][:40]}...，{change}，"
                    f"邻域为{neighbor_name}卦"
                )

        return {
            "primary_structure": structure["name"],
            "structural_tone": structure["tone"],
            "active_line": active_line if active_line else -1,
            "life_stage": stage,
            "change_narrative": change,
            "scale": _SCALE_FRAMEWORK.get(scale, _SCALE_FRAMEWORK["meso"])["name"],
            "context_modifier": f"邻域主导为{neighbor_name}卦",
            "possible_manifestations": manifests,
        }

    def narrative(self, packet: Dict[str, Any] = None, style: str = "poetic") -> str:
        """
        生成一段可直接用于叙事的自然语言描述。

        Args:
            style: "poetic"(诗意), "analytical"(分析性), "ominous"( ominous )
        """
        desc = self.interpret(packet)

        if style == "poetic":
            lines = [
                f"【{desc['primary_structure']}之象】",
                f"{desc['structural_tone']}。",
                f"{desc['change_narrative']}。",
                f"{desc['context_modifier']}。",
                f"{desc['historical_trend']}。",
                f"{desc['dao_influence']}。",
                "",
                "【可能显现】",
            ]
            for intent, manifest in desc["possible_manifestations"].items():
                lines.append(f"  · {intent}：{manifest}")
            return "\n".join(lines)

        elif style == "analytical":
            return (
                f"结构：{desc['primary_structure']}（{desc['_meta']['yin_yang_balance']}）\n"
                f"语气：{desc['structural_tone']}\n"
                f"时位：{desc['life_stage']}（active_line={desc['active_line']}）\n"
                f"变化：{desc['change_narrative']}\n"
                f"尺度：{desc['scale']}\n"
                f"邻域：{desc['context_modifier']}\n"
                f"历史：{desc['historical_trend']}\n"
                f"道势：{desc['dao_influence']}\n"
            )

        elif style == "ominous":
            return (
                f"此处显现{desc['primary_structure']}之兆。{desc['structural_tone']}，"
                f"而{desc['change_narrative']}。"
                f"{desc['context_modifier']}。"
                f"{desc['historical_trend']}。"
                f"{desc['dao_influence']}。"
                f"若以此卦拟人，则如{desc['possible_manifestations'].get('character', '未知')}。"
            )

        else:
            return self.narrative(packet, style="poetic")


# ═══════════════════════════════════════════
# 11. 快捷函数
# ═══════════════════════════════════════════

def interpret_packet(packet: Dict[str, Any]) -> Dict[str, Any]:
    """一次性解释数据包（无需实例化）。"""
    return XiangInterpreter().interpret(packet)


def interpret_camera(camera) -> Dict[str, Any]:
    """从摄像头自动采集并解释。"""
    return XiangInterpreter(camera).interpret()
