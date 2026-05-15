# -*- coding: utf-8 -*-
"""
《易道动态世界引擎》v2.0 — 观象者 (YaoAnalyst)

"体-用-变-势"四轮解释流水线。
P3 实现前两轮：观体 + 观用。

设计原则：
  1. 不是简单的顺序执行，而是层层深入、带有反馈的认知过程
  2. 观体锁定不易之本质，观用感知当下之气象
  3. 两轮之间生成体用对照叙事（narrative_thread 初版）
"""

from typing import Dict, Optional, Tuple
from interpreter import XiangInterpreter
from body_nature import get_body_nature, get_contested_nature, get_chaotic_nature
from codex import get_gua, get_wuxing


# ═══════════════════════════════════════════
# 体用关系判定表（基于五行与先天结构）
# ═══════════════════════════════════════════

# 纯卦值 → 五行
_TRIGRAM_WUXING = {
    0: "土", 9: "木", 18: "水", 27: "木",
    36: "土", 45: "火", 54: "金", 63: "金",
}

# 五行生克关系描述
_WUXING_RELATION_DESC = {
    ("木", "火"): "木生火，生发之势",
    ("火", "土"): "火生土，炽盛之后归于承载",
    ("土", "金"): "土生金，沉淀之中凝结秩序",
    ("金", "水"): "金生水，刚极之处涌出幽深",
    ("水", "木"): "水生木，幽暗之下萌发新生",
    ("木", "土"): "木克土，生发之力破土而出",
    ("土", "水"): "土克水，承载之堤阻断幽深",
    ("水", "火"): "水克火，幽深浇灭炽盛",
    ("火", "金"): "火克金，炽盛熔解秩序",
    ("金", "木"): "金克木，秩序之刃斩斫生发",
}


def _get_pure_trigram(hex_val: int) -> int:
    """从任意卦值提取其主导纯卦（上卦优先）。"""
    upper = (hex_val >> 3) & 0b111
    pure_map = [0, 9, 18, 27, 36, 45, 54, 63]
    return pure_map[upper]


def _classify_body_usage_relation(body_hex: int, usage_hex: int) -> Tuple[str, str]:
    """
    判定体用之间的关系。
    返回: (relation_type, relation_desc)
    """
    b_pure = _get_pure_trigram(body_hex)
    u_pure = _get_pure_trigram(usage_hex)
    
    if b_pure == u_pure:
        return ("同体", "体用同根，本色未改")
    
    # 检查是否为先天对卦
    opposite = frozenset([b_pure, u_pure])
    if opposite in {frozenset([0, 63]), frozenset([9, 27]), frozenset([18, 45]), frozenset([36, 54])}:
        return ("对冲", "体用对冲，表里截然相反，张力极大")
    
    bw = _TRIGRAM_WUXING.get(b_pure, "?")
    uw = _TRIGRAM_WUXING.get(u_pure, "?")
    
    # 相生
    if (bw, uw) in _WUXING_RELATION_DESC:
        return ("相生", _WUXING_RELATION_DESC[(bw, uw)])
    if (uw, bw) in _WUXING_RELATION_DESC:
        return ("被生", f"{uw}生{bw}，当下之势滋养其本质")
    
    # 相克
    if (bw, uw) in _WUXING_RELATION_DESC:
        return ("相克", _WUXING_RELATION_DESC[(bw, uw)])
    if (uw, bw) in _WUXING_RELATION_DESC:
        return ("被克", f"{uw}克{bw}，当下之势压制其本质")
    
    return ("杂", "体用交织，关系暧昧不明")


# ═══════════════════════════════════════════
# 观象者核心类
# ═══════════════════════════════════════════

class YaoAnalyst:
    """
    "体-用-变-势"四轮解释流水线。

    P3 实现：
      - observe_body(): 观体，锁定不易之本质
      - observe_usage(): 观用，感知当下之气象
      - run_two_rounds(): 执行两轮，输出体用对照
    """

    def __init__(self, camera=None):
        self.camera = camera
        self.interpreter = XiangInterpreter(camera)

    # ───────────────────────────────────────────
    # 第一轮：观体 —— 锁定不易之本质
    # ───────────────────────────────────────────

    def observe_body(self, tracker, perspective: str = "objective") -> Dict:
        """
        观体：从 EntityTracker 中提取体的本质描述。

        Args:
            tracker: EntityTracker 实例
            perspective: 视角参数（objective / archaeologist / sociologist / taoist）

        Returns:
            body 描述字典
        """
        # 确保 tracker 数据最新
        tracker._update()
        
        body_info = tracker.get_body(perspective)
        btype = body_info["body_type"]
        hex_val = body_info["body_hex"]
        
        # 根据三态选择语库
        if btype == "single":
            nature = get_body_nature(hex_val)
        elif btype == "contested":
            pair = body_info.get("contested_pair")
            if pair and body_info.get("is_opposite_pair"):
                nature = get_contested_nature(pair)
            elif pair:
                nature = get_contested_nature(pair)
            else:
                nature = get_chaotic_nature()
        else:  # chaotic
            nature = get_chaotic_nature()
        
        gua_info = get_gua(hex_val)
        
        return {
            "entity_id": body_info["entity_id"],
            "perspective": perspective,
            "body_hex": hex_val,
            "body_name": gua_info["name"],
            "body_protocol": gua_info["protocol"],
            "body_type": btype,
            "body_confidence": body_info["body_confidence"],
            "body_nature": nature,
            "long_term_dominant": body_info["long_term_dominant"],
            "volatility": body_info["volatility"],
            "history_length": body_info["history_length"],
        }

    # ───────────────────────────────────────────
    # 第二轮：观用 —— 感知当下之气象
    # ───────────────────────────────────────────

    def observe_usage(self, packet: Dict = None) -> Dict:
        """
        观用：解释当前帧的显化状态。

        Args:
            packet: WorldCamera.capture() 输出的数据包。若为 None 且 camera 已设置，自动采集。

        Returns:
            usage 描述字典
        """
        if packet is None:
            if self.camera is None:
                raise ValueError("未提供 packet 且未设置 camera")
            packet = self.camera.capture()
        
        desc = self.interpreter.interpret(packet)
        
        return {
            "current_hex": packet["data"]["hexagram"],
            "current_name": desc["primary_structure"],
            "structural_tone": desc["structural_tone"],
            "life_stage": desc["life_stage"],
            "change_narrative": desc["change_narrative"],
            "context_modifier": desc["context_modifier"],
            "dao_influence": desc["dao_influence"],
            "possible_manifestations": desc.get("possible_manifestations", {}),
            "scale": desc.get("scale", ""),
            "_meta": desc.get("_meta", {}),
        }

    # ───────────────────────────────────────────
    # 两轮流水线：体用对照
    # ───────────────────────────────────────────

    def run_two_rounds(self, tracker, packet: Dict = None, perspective: str = "objective") -> Dict:
        """
        执行观体 + 观用两轮流水线，输出体用对照。

        Returns:
            包含 body、usage、体用关系、narrative_thread 的完整字典
        """
        body = self.observe_body(tracker, perspective)
        usage = self.observe_usage(packet)
        
        # 体用关系判定
        relation_type, relation_desc = _classify_body_usage_relation(
            body["body_hex"], usage["current_hex"]
        )
        
        # 生成体用对照叙事（P3 初版，P5 将升级为三步微型推理）
        narrative = self._weave_body_usage(body, usage, relation_type, relation_desc)
        
        return {
            "round": "体用两轮",
            "perspective": perspective,
            "timestamp": tracker.world.tick_count if tracker.world else 0,
            "body": body,
            "usage": usage,
            "relation": {
                "type": relation_type,
                "description": relation_desc,
            },
            "narrative_thread": narrative,
        }

    def _weave_body_usage(self, body: Dict, usage: Dict, rel_type: str, rel_desc: str) -> str:
        """
        体用对照叙事编织（P3 初版）。
        
        生成逻辑：
          1. 以体为锚（"骨子里是X——..."）
          2. 以用为显（"当下它显化为Y，..."）
          3. 以关系为张力（"但/而/然而..."）
        """
        body_name = body["body_name"]
        usage_name = usage["current_name"]
        nature = body["body_nature"]
        tone = usage["structural_tone"]
        stage = usage["life_stage"]
        
        # 截断 nature，取第一句作为核心定义
        nature_core = nature.split("。")[0] if "。" in nature else nature
        
        # 截断 tone，取前40字
        tone_short = tone[:40] + "..." if len(tone) > 40 else tone
        
        # 根据关系类型选择连接词
        if rel_type == "同体":
            connector = "此刻它正处于"
        elif rel_type == "对冲":
            connector = "然而此刻它却披着"
        elif rel_type == "相生":
            connector = "如今它正顺其本性，显化为"
        elif rel_type == "被生":
            connector = "当下它被裹挟入"
        elif rel_type == "相克":
            connector = "但如今它正被"
        elif rel_type == "被克":
            connector = "当下它却困于"
        else:
            connector = "此刻它暂时显化为"
        
        # 组装叙事
        lines = [
            f"【{body_name}之体】{nature_core}。",
            f"【{usage_name}之用】{connector}{usage_name}之象。{tone_short}。",
            f"【体用关系】{rel_desc}。",
            f"【生命阶段】{stage}。",
        ]
        
        return "\n".join(lines)


# ═══════════════════════════════════════════
# 快捷函数
# ═══════════════════════════════════════════

def analyze_body_usage(tracker, packet: Dict = None, perspective: str = "objective") -> Dict:
    """一次性执行体用两轮分析。"""
    analyst = YaoAnalyst()
    return analyst.run_two_rounds(tracker, packet, perspective)
