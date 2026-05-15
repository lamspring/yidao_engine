# -*- coding: utf-8 -*-
"""
《易道动态世界引擎》v5.0 — 世界观测器 (WorldPerceptionInterface)
AI 的"世界摄像机"。系统与外界（玩家、叙事AI）的唯一感知接口。

设计原则：
  - 世界在后台静默运行，不观测时不产生解释
  - 观测是按需的、区域性的、分层级的
  - 输出为结构化数据包，解释引擎据此生成世界现象
  - 未观测区域不存在于解释层（观测即显化）
  - LLM 可直接操作摄像头的移动、尺度、意图
"""

import numpy as np
from collections import Counter
from typing import List, Tuple, Dict, Optional
from kernel import yang_count, split_trigrams
from codex import get_gua, get_phase_meaning


# ═══════════════════════════════════════════
# 0. 八卦相荡关系查表（邻域上下文预计算）
# ═══════════════════════════════════════════

# 八卦索引: 0坤(土) 1震(木) 2坎(水) 3巽(木) 4艮(土) 5离(火) 6兑(金) 7乾(金)
_BAGUA_NAMES = ["坤", "震", "坎", "巽", "艮", "离", "兑", "乾"]
_BAGUA_WUXING = ["土", "木", "水", "木", "土", "火", "金", "金"]

# 8×8 关系词矩阵（行=焦点卦，列=邻域卦）
# 关系源于五行生克、先天通气、先天对冲
_BAGUA_RELATION_TERMS = [
    # 0 坤(土)
    ["厚土共鸣", "木克厚土", "土克深渊", "木克厚土", "厚土叠加", "火土相生", "土金相生", "天地对冲"],
    # 1 震(木)
    ["木克厚土", "雷雷相激", "水木相生", "雷风相薄", "木克厚土", "木火相生", "金克柔木", "金克柔木"],
    # 2 坎(水)
    ["土克深渊", "水木相生", "深渊回响", "水木相生", "土克深渊", "水火对冲", "金水相生", "金水相生"],
    # 3 巽(木)
    ["木克厚土", "雷风相薄", "水木相生", "风行同化", "木克厚土", "木火相生", "金克柔木", "金克柔木"],
    # 4 艮(土)
    ["厚土叠加", "木克厚土", "土克深渊", "木克厚土", "山山相峙", "火土相生", "山泽通气", "土金相生"],
    # 5 离(火)
    ["火土相生", "木火相生", "水火对冲", "木火相生", "火土相生", "炎炎相炽", "火克刚金", "火克刚金"],
    # 6 兑(金)
    ["土金相生", "金克柔木", "金水相生", "金克柔木", "山泽通气", "火克刚金", "泽泽相溢", "金金共鸣"],
    # 7 乾(金)
    ["天地对冲", "金克柔木", "金水相生", "金克柔木", "土金相生", "火克刚金", "金金共鸣", "乾乾相健"],
]


def get_relation_term(trigram_focus: int, trigram_neighbor: int) -> str:
    """
    根据焦点八卦与邻域八卦，返回相荡关系词。
    trigram: 0-7 的八卦索引
    """
    tf = int(trigram_focus) & 0b111
    tn = int(trigram_neighbor) & 0b111
    return _BAGUA_RELATION_TERMS[tf][tn]


def get_dominant_trigram(gua_region: np.ndarray) -> int:
    """
    从卦象区域中提取主导八卦（上下卦中出现最频繁者）。
    返回 0-7 的八卦索引。
    """
    if gua_region.size == 0:
        return 0
    upper, lower = split_trigrams(gua_region)
    all_tri = np.concatenate([upper.flatten(), lower.flatten()])
    vals, counts = np.unique(all_tri, return_counts=True)
    return int(vals[np.argmax(counts)])


# ═══════════════════════════════════════════
# 1. 实体持久跟踪器
# ═══════════════════════════════════════════

# 先天对卦组（乾坤、坎离、震巽、艮兑）
_OPPOSITE_PAIRS = frozenset([
    frozenset([0, 63]),    # 乾坤
    frozenset([9, 27]),    # 震巽
    frozenset([18, 45]),   # 坎离
    frozenset([36, 54]),   # 艮兑
])


def _is_opposite_pair(a: int, b: int) -> bool:
    """判断两个卦值是否构成先天对卦。"""
    return frozenset([a & 0b111111, b & 0b111111]) in _OPPOSITE_PAIRS


class EntityTracker:
    """
    对角色、国家、神祇等需要跨时刻解释的对象进行长期跟踪。
    维持历史卦序列，供解释引擎人格化输出。

    P1 新增：三态体之识别（单一体 / 交战体 / 混沌体）
    """

    # 三态阈值
    BODY_SINGLE_THRESHOLD = 0.60
    BODY_CONTESTED_THRESHOLD = 0.35

    def __init__(
        self,
        world,
        entity_id: str,
        center_y: int,
        center_x: int,
        radius: int = 3,
    ):
        self.world = world
        self.entity_id = entity_id
        self.center_y = int(center_y) % world.H
        self.center_x = int(center_x) % world.W
        self.radius = max(1, radius)
        self.hex_history: List[int] = []      # 每息记录的主卦
        self.tick_history: List[int] = []     # 对应的 tick
        self.max_history = 64
        self.is_persistent = True

        # P4 新增：事件状态机
        self.event_state = {
            "last_first_dx_tick": -9999,    # 上次初诊的世界 tick
            "last_re_dx_tick": -9999,       # 上次复诊的世界 tick
            "last_emergency_tick": -9999,   # 上次急诊的世界 tick
            "post_flip_cooldown": 0,        # 卦变后冷却计数（复诊窗口）
            "flip_recorded": False,         # 本轮是否已记录卦变
        }

        self._update()

    def _region_rect(self) -> Tuple[int, int, int, int]:
        r = self.radius - 1
        y0 = max(0, self.center_y - r)
        x0 = max(0, self.center_x - r)
        y1 = min(self.world.H, self.center_y + r + 1)
        x1 = min(self.world.W, self.center_x + r + 1)
        return y0, x0, y1, x1

    def _update(self):
        """在当前世界 tick 下采样区域主卦并记录。同一 tick 内去重。"""
        if self.tick_history and self.tick_history[-1] == self.world.tick_count:
            return
        y0, x0, y1, x1 = self._region_rect()
        region = self.world.gua[y0:y1, x0:x1]
        if region.size == 0:
            dominant = 0
        else:
            vals, counts = np.unique(region, return_counts=True)
            dominant = int(vals[np.argmax(counts)])
        self.hex_history.append(dominant)
        self.tick_history.append(self.world.tick_count)
        if len(self.hex_history) > self.max_history:
            self.hex_history.pop(0)
            self.tick_history.pop(0)

        # P4：卦变检测与复诊冷却管理
        if len(self.hex_history) >= 2:
            prev = self.hex_history[-2]
            curr = self.hex_history[-1]
            if prev != curr and not self.event_state["flip_recorded"]:
                # 检测到卦变，启动复诊窗口（5息）
                self.event_state["post_flip_cooldown"] = 5
                self.event_state["flip_recorded"] = True
                self.event_state["pre_flip_hex"] = prev
                self.event_state["post_flip_hex"] = curr
            elif prev == curr:
                self.event_state["flip_recorded"] = False
        
        # 复诊冷却递减
        if self.event_state["post_flip_cooldown"] > 0:
            self.event_state["post_flip_cooldown"] -= 1

    def update_center(self, y: int, x: int):
        """更新跟踪中心（实体移动时调用）。"""
        self.center_y = int(y) % self.world.H
        self.center_x = int(x) % self.world.W
        self._update()

    # ───────────────────────────────────────────
    # 基础属性（向后兼容）
    # ───────────────────────────────────────────

    @property
    def recent_hexagrams(self) -> List[int]:
        """最近最多 3 息的主卦序列。"""
        return self.hex_history[-3:] if self.hex_history else []

    @property
    def long_term_dominant(self) -> int:
        """历史中出现最频繁的主卦。全时段等权。"""
        if not self.hex_history:
            return 0
        c = Counter(self.hex_history)
        return c.most_common(1)[0][0]

    @property
    def volatility(self) -> float:
        """变化频率：0.0（完全静止）~ 1.0（每息都变）。"""
        if len(self.hex_history) < 2:
            return 0.0
        changes = sum(
            1 for i in range(1, len(self.hex_history))
            if self.hex_history[i] != self.hex_history[i - 1]
        )
        return changes / (len(self.hex_history) - 1)

    # ───────────────────────────────────────────
    # P1 新增：体之三态识别
    # ───────────────────────────────────────────

    @property
    def body_confidence(self) -> float:
        """体的置信度：长期主导卦的占比。0.0 ~ 1.0。"""
        if not self.hex_history:
            return 0.0
        c = Counter(self.hex_history)
        top_count = c.most_common(1)[0][1]
        return top_count / len(self.hex_history)

    @property
    def body_type(self) -> str:
        """
        三态分类：
          'single'    → 单一体（置信度 > 0.6）
          'contested' → 交战体（0.35 ~ 0.6）
          'chaotic'   → 混沌体（< 0.35）
        """
        conf = self.body_confidence
        if conf > self.BODY_SINGLE_THRESHOLD:
            return "single"
        elif conf >= self.BODY_CONTESTED_THRESHOLD:
            return "contested"
        else:
            return "chaotic"

    @property
    def contested_pair(self) -> Optional[Tuple[int, int]]:
        """
        如果是交战体，返回交战卦对（按出现频率排序）。
        优先识别先天对卦（乾坤、坎离、震巽、艮兑）。
        若非对卦，则返回出现频率最高的两个卦。
        """
        if len(self.hex_history) < 10:
            return None
        c = Counter(self.hex_history)
        top2 = c.most_common(2)
        if len(top2) < 2:
            return None
        (h1, n1), (h2, n2) = top2
        # 前两名之和必须占历史的主导地位（>50%），否则是混沌而非交战
        if (n1 + n2) / len(self.hex_history) < 0.5:
            return None
        # 若恰好是对卦，返回对卦顺序（大数在前，小数在后，固定顺序）
        if _is_opposite_pair(h1, h2):
            return (max(h1, h2), min(h1, h2))
        # 否则返回频率降序
        return (h1, h2)

    def recent_dominant(self, window: int = 12) -> int:
        """
        近期主导卦（时间衰减视角）。
        默认取最近 12 息，供社会学家/道学家视角使用。
        """
        if not self.hex_history:
            return 0
        recent = self.hex_history[-window:] if len(self.hex_history) >= window else self.hex_history
        c = Counter(recent)
        return c.most_common(1)[0][0]

    def get_body(self, perspective: str = "objective") -> dict:
        """
        获取体之描述。支持四种视角：
          'objective'     → 全时段等权，最客观的本质（默认）
          'archaeologist' → 考古学家视角，同 objective
          'sociologist'   → 社会学家视角，侧重近期主导
          'taoist'        → 道学家视角，侧重当下此刻
        """
        self._update()

        btype = self.body_type
        conf = round(self.body_confidence, 3)

        if perspective in ("objective", "archaeologist"):
            hex_val = self.long_term_dominant
        elif perspective == "sociologist":
            hex_val = self.recent_dominant(window=12)
        elif perspective == "taoist":
            hex_val = self.hex_history[-1] if self.hex_history else 0
        else:
            hex_val = self.long_term_dominant

        result = {
            "entity_id": self.entity_id,
            "perspective": perspective,
            "body_type": btype,
            "body_confidence": conf,
            "body_hex": int(hex_val),
            "long_term_dominant": int(self.long_term_dominant),
            "volatility": round(self.volatility, 3),
            "history_length": len(self.hex_history),
        }

        # 交战体补充信息
        if btype == "contested":
            pair = self.contested_pair
            if pair:
                result["contested_pair"] = (int(pair[0]), int(pair[1]))
                result["is_opposite_pair"] = _is_opposite_pair(pair[0], pair[1])
            else:
                result["contested_pair"] = None
                result["is_opposite_pair"] = False

        return result

    def get_history_state(self) -> dict:
        """供数据包直接使用的 history 字段（扩展版）。"""
        return {
            "recent_hexagrams": self.recent_hexagrams,
            "long_term_dominant": self.long_term_dominant,
            "recent_dominant": self.recent_dominant(window=12),
            "volatility": round(self.volatility, 3),
            "body_type": self.body_type,
            "body_confidence": round(self.body_confidence, 3),
        }

    def get_persistence_state(self) -> dict:
        return {
            "entity_id": self.entity_id,
            "is_persistent": self.is_persistent,
        }


# ═══════════════════════════════════════════
# 2. 经典观测器（自然语言描述层，向后兼容）
# ═══════════════════════════════════════════

class YaoObserver:
    """
    世界观测器。不持有世界状态，只持有世界引用。
    所有解释都是观测瞬间的涌现翻译。
    """

    def __init__(self, world):
        self.world = world

    # ───────────────────────────────────────────
    # 内部工具
    # ───────────────────────────────────────────

    def _region_stats(self, y0: int, x0: int, h: int, w: int) -> dict:
        """获取区域原始统计（内部用）"""
        H, W = self.world.H, self.world.W
        y0 = max(0, y0)
        x0 = max(0, x0)
        y1 = min(H, y0 + h)
        x1 = min(W, x0 + w)
        if y1 <= y0 or x1 <= x0:
            return {"error": "invalid region"}

        rgua = self.world.gua[y0:y1, x0:x1]
        rtrend = self.world.trend[y0:y1, x0:x1]
        rphase = self.world.phase[y0:y1, x0:x1]
        rpot = self.world.potential[y0:y1, x0:x1]
        rstab = self.world.stable_age[y0:y1, x0:x1]

        cells = rgua.size
        vals, counts = np.unique(rgua, return_counts=True)

        top_idx = int(np.argmax(counts))
        top_gua = get_gua(int(vals[top_idx]))
        dominance = float(counts[top_idx]) / cells

        proto_counts = Counter()
        for v, c in zip(vals, counts):
            proto_counts[get_gua(int(v))["protocol"]] += int(c)
        dominant_proto = proto_counts.most_common(1)[0][0]

        yc = yang_count(rgua)
        yang_ratio = float(np.mean(yc)) / 6.0

        return {
            "top_gua": top_gua,
            "dominance": dominance,
            "dominant_proto": dominant_proto,
            "proto_counts": proto_counts,
            "yang_ratio": yang_ratio,
            "mean_trend": float(np.mean(rtrend)),
            "mean_phase": float(np.mean(rphase)),
            "mean_potential": float(np.mean(rpot)),
            "max_potential": float(np.max(rpot)),
            "mean_stable": float(np.mean(rstab)),
            "phase_meaning": get_phase_meaning(dominant_proto, float(np.mean(rphase))),
            "cells": cells,
        }

    # ───────────────────────────────────────────
    # 核心观测接口（自然语言）
    # ───────────────────────────────────────────

    def observe_region(self, y0: int, x0: int, h: int, w: int) -> str:
        """观测指定矩形区域，返回自然语言描述。"""
        s = self._region_stats(y0, x0, h, w)
        if "error" in s:
            return "观测失败：无效区域。"

        fragments = []
        top = s["top_gua"]

        # 1. 总体氛围
        if s["dominance"] > 0.7:
            fragments.append(
                f"你观测到一片高度统一的{top['name']}卦之域（{top['protocol']}）。"
            )
        elif s["dominance"] > 0.4:
            fragments.append(
                f"你观测到一片以{top['name']}卦（{top['protocol']}）为主导的混成区域。"
            )
        else:
            fragments.append(
                f"你观测到一片诸力交织的混沌地带，{top['name']}卦（{top['protocol']}）略占上风。"
            )

        # 2. 阴阳基调
        yr = s["yang_ratio"]
        if yr < 0.25:
            fragments.append("阴气凝重，万物内藏，潜龙勿用。")
        elif yr < 0.4:
            fragments.append("阴长阳消，收敛之势已成。")
        elif yr > 0.75:
            fragments.append("阳气极盛，万物外向扩张，已近亢龙有悔之境。")
        elif yr > 0.6:
            fragments.append("阳长阴消，生发之气充盈。")
        else:
            fragments.append("阴阳平衡，冲气为和。")

        # 3. 生命阶段
        fragments.append(s["phase_meaning"] + "。")

        # 4. 能量与动态
        mt = s["mean_trend"]
        mp = s["mean_potential"]
        vt = self.world.V_thresh

        energy_parts = []
        if mp > vt * 0.85:
            energy_parts.append(f"势能已积累至{mp:.2f}，濒临临界反转（阈值{vt:.2f}）")
        elif mp > vt * 0.5:
            energy_parts.append(f"势能中等（{mp:.2f}），内在矛盾正在积累")
        else:
            energy_parts.append(f"势能尚低（{mp:.2f}），处于相对稳态")

        if abs(mt) > 0.4:
            direction = "阳化加速" if mt > 0 else "阴化沉潜"
            energy_parts.append(f"气象剧烈（{mt:+.2f}），{direction}")
        elif abs(mt) > 0.15:
            direction = "阳化" if mt > 0 else "阴化"
            energy_parts.append(f"气象活跃（{mt:+.2f}），{direction}进行中")
        else:
            energy_parts.append(f"气象平和（{mt:+.2f}），变动暂缓")

        fragments.append("；".join(energy_parts) + "。")

        # 5. 结构竞争
        pc = s["proto_counts"]
        if len(pc) >= 3:
            others = [f"{k}({v})" for k, v in pc.most_common(3)]
            fragments.append(f"域内协议竞争：{', '.join(others)}。")

        # 6. 异常标记
        if s["max_potential"] > vt:
            fragments.append("【异常】区域内存在已突破势能阈值的爆发点。")
        if s["mean_stable"] < 3 and s["mean_potential"] > vt * 0.5:
            fragments.append("【异常】近期发生过剧烈卦变，新结构尚未稳定。")

        return "".join(fragments)

    def observe_point(self, y: int, x: int) -> str:
        """观测单点，返回微观状态描述。"""
        H, W = self.world.H, self.world.W
        y, x = y % H, x % W

        gua_val = int(self.world.gua[y, x])
        info = get_gua(gua_val)
        trend = float(self.world.trend[y, x])
        phase = float(self.world.phase[y, x])
        pot = float(self.world.potential[y, x])
        stable = int(self.world.stable_age[y, x])
        vt = self.world.V_thresh

        if trend > 0.5:
            t_desc = "强烈阳化，急剧扩张"
        elif trend > 0.15:
            t_desc = "阳化中，边界外推"
        elif trend < -0.5:
            t_desc = "强烈阴化，急剧内敛"
        elif trend < -0.15:
            t_desc = "阴化中，边界溶解"
        else:
            t_desc = "气象平和，暂处稳态"

        if pot > vt:
            p_desc = f"势能已溢满（{pot:.2f}/{vt:.2f}），随时可能爆发反转"
        elif pot > vt * 0.7:
            p_desc = f"势能高涨（{pot:.2f}/{vt:.2f}），临界在即"
        elif pot > vt * 0.3:
            p_desc = f"势能积累中（{pot:.2f}/{vt:.2f}）"
        else:
            p_desc = f"势能平静（{pot:.2f}/{vt:.2f}）"

        meaning = get_phase_meaning(info["protocol"], phase)

        return (
            f"此点为{info['name']}卦（{info['protocol']}），五行属{info['wuxing']}。"
            f"{meaning}。"
            f"阴阳气象{trend:+.2f}，{t_desc}。"
            f"{p_desc}。"
            f"已持续{stable}息未变。"
        )

    def observe_trajectory(self, y: int, x: int, back_steps: int = 30) -> str:
        """回溯单点在过去 back_steps 息内的演化轨迹。"""
        H, W = self.world.H, self.world.W
        y, x = y % H, x % W
        hist = self.world.history

        if not hist:
            return "尚无历史记录。"

        available = min(back_steps, len(hist))
        trajectory = [int(h[y, x]) for h in hist[-available:]]

        events = []
        prev = trajectory[0]
        for i, val in enumerate(trajectory[1:], 1):
            if val != prev:
                tick_offset = self.world.tick_count - available + i
                old_name = get_gua(prev)["name"]
                new_name = get_gua(val)["name"]
                events.append(f"第{tick_offset}息：{old_name}→{new_name}")
                prev = val

        start = get_gua(trajectory[0])
        current = get_gua(trajectory[-1])

        if not events:
            return (
                f"过去{available}息内，此点始终为{start['name']}卦（{start['protocol']}），"
                f"未有变化，处于持续稳态。"
            )

        event_text = "；".join(events)
        return (
            f"你回溯此点过去{available}息的轨迹：起始于{start['name']}卦（{start['protocol']}）。"
            f"期间发生{len(events)}次卦变：{event_text}。"
            f"当前为{current['name']}卦（{current['protocol']}）。"
        )

    def scan_anomalies(self, pot_ratio: float = 0.8) -> List[Tuple[int, int, str]]:
        """扫描全场异常点，返回 (y, x, reason) 列表。"""
        H, W = self.world.H, self.world.W
        vt = self.world.V_thresh
        anomalies = []

        # 高势能点
        high_pot = self.world.potential > vt * pot_ratio
        if np.any(high_pot):
            ys, xs = np.where(high_pot)
            for y, x in zip(ys[:5], xs[:5]):
                pot = float(self.world.potential[y, x])
                gua = get_gua(int(self.world.gua[y, x]))
                anomalies.append((
                    int(y), int(x),
                    f"{gua['name']}卦势能{pot:.2f}（临界）"
                ))

        # 最近发生卦变的点
        if len(self.world.history) >= 2:
            last = self.world.history[-1]
            prev = self.world.history[-2]
            changed = (last != prev)
            if np.any(changed):
                ys, xs = np.where(changed)
                for y, x in zip(ys[:3], xs[:3]):
                    gua = get_gua(int(last[y, x]))
                    anomalies.append((
                        int(y), int(x),
                        f"{gua['name']}卦刚发生卦变"
                    ))

        return anomalies

    def observe_field_summary(self) -> str:
        """全局摘要，一句话概括世界当前态势。"""
        H, W = self.world.H, self.world.W
        yc = yang_count(self.world.gua)
        yang_ratio = float(np.mean(yc)) / 6.0
        mean_energy = float(np.mean(np.abs(self.world.trend)))
        vt = self.world.V_thresh

        vals = self.world.gua.flatten()
        proto_cnt = Counter(get_gua(int(v))["protocol"] for v in vals)
        top_proto, top_count = proto_cnt.most_common(1)[0]
        proto_ratio = top_count / (H * W)

        mood = []
        if yang_ratio < 0.3:
            mood.append("世界整体偏阴，收敛内敛")
        elif yang_ratio > 0.7:
            mood.append("世界整体偏阳，扩张外显")
        else:
            mood.append("世界阴阳交错")

        if mean_energy < 0.1:
            mood.append("动态沉寂")
        elif mean_energy > 0.5:
            mood.append("变革频繁")
        else:
            mood.append("动态适中")

        mood.append(f"主导协议为{top_proto}（占比{proto_ratio:.1%}）")

        return (
            f"第{self.world.tick_count}息：{'，'.join(mood)}。"
            f"道阈值V={vt:.2f}，道偏置={self.world.dao_bias:+.3f}。"
        )


# ═══════════════════════════════════════════
# 3. 世界摄像机（感知接口，LLM 可操作）
# ═══════════════════════════════════════════

class WorldCamera:
    """
    AI 的"世界摄像机" —— 系统与外界的唯一感知接口。

    LLM 操作范式：
        cam = WorldCamera(world, observer_id="narrator_01")
        cam.set_scale("meso")
        cam.set_intent("character")
        cam.move_to(20, 40)

        packet = cam.capture()          # 完整数据包
        mini   = cam.capture_minimal()  # 极简帧
        text   = cam.look()             # 自然语言描述（可选）

        cam.track_entity("hero_01", y=20, x=40, radius=3)
        packet_with_history = cam.capture()  # 自动包含跟踪实体的 history
    """

    # scale → 默认 radius 映射
    SCALE_RADIUS = {
        "micro": 1,      # 单点，微观
        "meso": 4,       # 局部，人/物尺度
        "macro": 12,     # 区域，地形/势力尺度
        "cosmic": 0,     # 全局，特殊处理
    }

    # intent → 默认 scale 建议（仅作提示，不强制）
    INTENT_DEFAULT_SCALE = {
        "character": "meso",
        "object": "meso",
        "landscape": "macro",
        "faction": "macro",
        "god": "cosmic",
        "event": "meso",
    }

    def __init__(
        self,
        world,
        observer_id: str = "world_cam_01",
        y: int = None,
        x: int = None,
        scale: str = "meso",
        intent: str = "landscape",
    ):
        self.world = world
        self.observer_id = observer_id
        self._observer = YaoObserver(world)

        # 焦点坐标（环形边界）
        self.y = (y if y is not None else world.H // 2) % world.H
        self.x = (x if x is not None else world.W // 2) % world.W

        # 观测参数
        self.scale = scale if scale in self.SCALE_RADIUS else "meso"
        self.intent = intent
        self.zoom = 1.0

        # 移动历史
        self.move_history = []
        self._record_position()

        # 实体跟踪表: entity_id -> EntityTracker
        self._trackers: Dict[str, EntityTracker] = {}
        self._active_tracker_id: Optional[str] = None

    # ───────────────────────────────────────────
    # 内部工具
    # ───────────────────────────────────────────

    def _record_position(self):
        self.move_history.append({
            "tick": self.world.tick_count,
            "y": int(self.y),
            "x": int(self.x),
            "zoom": float(self.zoom),
            "scale": self.scale,
            "intent": self.intent,
        })

    def _get_radius(self) -> int:
        """根据当前 scale 和 zoom 计算实际 radius。"""
        base = self.SCALE_RADIUS.get(self.scale, 4)
        if base == 0:  # cosmic
            return max(self.world.H, self.world.W)
        # zoom 影响 radius：zoom_in → radius 缩小，zoom_out → radius 放大
        r = max(1, int(base * self.zoom))
        return r

    def _focus_rect(self, radius: int) -> Tuple[int, int, int, int]:
        """返回焦点区域矩形 (y0, x0, y1, x1)。radius=1 为单点。"""
        r = radius - 1
        y0 = max(0, self.y - r)
        x0 = max(0, self.x - r)
        y1 = min(self.world.H, self.y + r + 1)
        x1 = min(self.world.W, self.x + r + 1)
        return y0, x0, y1, x1

    def _neighbor_rect(self, radius: int) -> Tuple[int, int, int, int]:
        """返回邻域矩形（比焦点大一圈的外围上下文）。"""
        nr = radius + 2  # 邻域半径
        r = nr - 1
        y0 = max(0, self.y - r)
        x0 = max(0, self.x - r)
        y1 = min(self.world.H, self.y + r + 1)
        x1 = min(self.world.W, self.x + r + 1)
        return y0, x0, y1, x1

    def _dominant_hexagram(self, gua_region: np.ndarray) -> int:
        """区域主导卦（众数），平局时取中心点。"""
        if gua_region.size == 0:
            return 0
        vals, counts = np.unique(gua_region, return_counts=True)
        best = int(vals[np.argmax(counts)])
        # 若主导度太低(<30%)且区域非空， fallback 到中心点
        if counts[np.argmax(counts)] / gua_region.size < 0.30 and gua_region.size > 1:
            # 确保是二维数组才取中心点
            if gua_region.ndim >= 2:
                cy, cx = gua_region.shape[0] // 2, gua_region.shape[1] // 2
                best = int(gua_region[cy, cx])
        return best

    def _detect_active_lines(self, y0: int, x0: int, y1: int, x1: int) -> List[int]:
        """
        检测焦点区域内刚发生穷极翻转的爻位。
        返回 [1-6] 列表，按翻转频繁程度排序。
        """
        if len(self.world.history) < 2:
            return []
        old = self.world.history[-2][y0:y1, x0:x1]
        new = self.world.history[-1][y0:y1, x0:x1]
        xor = old ^ new
        changed = xor.flatten()
        changed = changed[changed != 0]
        if changed.size == 0:
            return []
        counts = np.zeros(6, dtype=int)
        for i in range(6):
            counts[i] = int(np.sum((changed >> i) & 1))
        active = [i + 1 for i in range(6) if counts[i] > 0]
        active.sort(key=lambda line: counts[line - 1], reverse=True)
        return active

    def _compute_neighbor_profile(self, fy0, fx0, fy1, fx1) -> dict:
        """计算邻域上下文 profile。"""
        ny0, nx0, ny1, nx1 = self._neighbor_rect(self._get_radius())
        neighbor_gua = self.world.gua[ny0:ny1, nx0:nx1]
        if neighbor_gua.size == 0:
            return {
                "dominant_hexagram": 0,
                "relation_term": "虚空",
                "yang_ratio": 0.5,
            }

        # 排除焦点区域（若有重叠）
        # 采用切比雪夫距离 mask
        yy, xx = np.mgrid[ny0:ny1, nx0:nx1]
        dy, dx = yy - self.y, xx - self.x
        dist = np.maximum(np.abs(dy), np.abs(dx))
        focus_r = self._get_radius() - 1
        neighbor_mask = dist > focus_r

        if not np.any(neighbor_mask):
            # 边界极端情况，直接用整个区域
            neighbor_vals = neighbor_gua
        else:
            neighbor_vals = neighbor_gua[neighbor_mask]

        dom_hex = self._dominant_hexagram(neighbor_vals)
        yc = yang_count(neighbor_vals)
        yang_ratio = float(np.mean(yc)) / 6.0 if yc.size > 0 else 0.5

        # 关系词：焦点主导卦 vs 邻域主导卦
        focus_gua = self._dominant_hexagram(self.world.gua[fy0:fy1, fx0:fx1])
        focus_tri = get_dominant_trigram(np.array([[focus_gua]], dtype=np.uint8))
        neighbor_tri = get_dominant_trigram(np.array([[dom_hex]], dtype=np.uint8))

        if self.scale == "cosmic":
            relation = "浑然一局"
        else:
            relation = get_relation_term(focus_tri, neighbor_tri)

        return {
            "dominant_hexagram": dom_hex,
            "relation_term": relation,
            "yang_ratio": round(yang_ratio, 3),
        }

    def _compute_history(self, y0, x0, y1, x1) -> dict:
        """从历史快照推导焦点区域的 history 字段（无实体跟踪时）。"""
        hist = self.world.history
        if not hist:
            return {
                "recent_hexagrams": [],
                "long_term_dominant": 0,
                "volatility": 0.0,
            }

        seq = []
        for snap in hist:
            region = snap[y0:y1, x0:x1]
            if region.size == 0:
                seq.append(0)
            else:
                vals, counts = np.unique(region, return_counts=True)
                seq.append(int(vals[np.argmax(counts)]))

        recent = seq[-3:] if len(seq) >= 3 else seq
        c = Counter(seq)
        long_term = c.most_common(1)[0][0] if c else 0
        changes = sum(1 for i in range(1, len(seq)) if seq[i] != seq[i - 1])
        vol = changes / (len(seq) - 1) if len(seq) > 1 else 0.0

        return {
            "recent_hexagrams": recent,
            "long_term_dominant": long_term,
            "volatility": round(vol, 3),
        }

    def _get_persistence(self) -> dict:
        """获取当前 persistence 状态。"""
        if self._active_tracker_id and self._active_tracker_id in self._trackers:
            tracker = self._trackers[self._active_tracker_id]
            return tracker.get_persistence_state()
        return {
            "entity_id": "",
            "is_persistent": False,
        }

    def _get_history_for_packet(self, y0, x0, y1, x1) -> dict:
        """获取数据包的 history 字段（优先使用实体跟踪器）。"""
        if self._active_tracker_id and self._active_tracker_id in self._trackers:
            tracker = self._trackers[self._active_tracker_id]
            tracker._update()  # 确保最新
            return tracker.get_history_state()
        return self._compute_history(y0, x0, y1, x1)

    # ───────────────────────────────────────────
    # LLM 操作接口：移动
    # ───────────────────────────────────────────

    def move_to(self, y: int, x: int):
        """移动摄像机到绝对坐标（自动环形边界）。"""
        self.y = int(y) % self.world.H
        self.x = int(x) % self.world.W
        self._record_position()

    def pan(self, dy: int, dx: int):
        """相对平移。"""
        self.move_to(self.y + dy, self.x + dx)

    def pan_north(self, steps: int = 5):
        self.pan(-steps, 0)

    def pan_south(self, steps: int = 5):
        self.pan(steps, 0)

    def pan_west(self, steps: int = 5):
        self.pan(0, -steps)

    def pan_east(self, steps: int = 5):
        self.pan(0, steps)

    def pan_to_anomaly(self) -> str:
        """自动平移到全场最异常点。返回移动说明。"""
        anoms = self._observer.scan_anomalies(pot_ratio=0.9)
        if not anoms:
            return "全场无显著异常，摄像机保持原位。"
        y, x, reason = anoms[0]
        old_y, old_x = self.y, self.x
        self.move_to(y, x)
        return f"摄像机从({old_y},{old_x})自动追踪至({y},{x})。原因：{reason}。"

    # ───────────────────────────────────────────
    # LLM 操作接口：参数调节
    # ───────────────────────────────────────────

    def set_scale(self, scale: str):
        """
        设定观测尺度。
        micro=单点微观, meso=局部人/物, macro=区域地形/势力, cosmic=全局。
        """
        if scale not in self.SCALE_RADIUS:
            raise ValueError(f"非法 scale: {scale}，可选: {list(self.SCALE_RADIUS.keys())}")
        self.scale = scale
        self._record_position()

    def set_intent(self, intent: str):
        """
        设定观测意图，解释引擎据此将结构语气填入不同物类框架。
        例如: character | object | landscape | faction | god | event
        """
        self.intent = intent
        self._record_position()

    def suggest_scale_for_intent(self) -> str:
        """根据当前 intent 返回推荐的 scale（供 LLM 决策参考）。"""
        return self.INTENT_DEFAULT_SCALE.get(self.intent, "meso")

    # ───────────────────────────────────────────
    # 视野控制（兼容旧版 zoom）
    # ───────────────────────────────────────────

    def zoom_in(self, factor: float = 0.7):
        """缩小视野（看得更细），radius 减小。"""
        self.zoom = max(0.2, self.zoom * factor)

    def zoom_out(self, factor: float = 1.5):
        """放大视野（看得更广），radius 增大。"""
        self.zoom = min(3.0, self.zoom * factor)

    def reset_zoom(self):
        self.zoom = 1.0

    # ───────────────────────────────────────────
    # 实体跟踪接口
    # ───────────────────────────────────────────

    def track_entity(self, entity_id: str, y: int = None, x: int = None, radius: int = 3):
        """
        对指定区域建立持久跟踪。此后 capture() 会包含该实体的 history 与 persistence。
        entity_id 由上层 AI/玩家命名，如 "hero_01", "秦帝国", "深渊之眼"。
        """
        y = (y if y is not None else self.y) % self.world.H
        x = (x if x is not None else self.x) % self.world.W
        tracker = EntityTracker(self.world, entity_id, y, x, radius)
        self._trackers[entity_id] = tracker
        self._active_tracker_id = entity_id
        return f"已建立对 '{entity_id}' 的持久跟踪（中心 {y},{x}，半径 {radius}）。"

    def untrack_entity(self, entity_id: str):
        """移除指定实体的跟踪。"""
        if entity_id in self._trackers:
            del self._trackers[entity_id]
            if self._active_tracker_id == entity_id:
                self._active_tracker_id = None
            return f"已移除对 '{entity_id}' 的跟踪。"
        return f"未找到实体 '{entity_id}'。"

    def switch_tracker(self, entity_id: str):
        """切换当前活跃跟踪器（不改变焦点，只改变 persistence 输出）。"""
        if entity_id in self._trackers:
            self._active_tracker_id = entity_id
            return f"当前活跃实体已切换为 '{entity_id}'。"
        return f"未找到实体 '{entity_id}'，请先调用 track_entity() 建立跟踪。"

    def list_trackers(self) -> List[str]:
        """列出所有正在跟踪的实体 ID。"""
        return list(self._trackers.keys())

    def update_tracker_center(self, entity_id: str, y: int, x: int):
        """更新已跟踪实体的中心坐标（实体移动时调用）。"""
        if entity_id in self._trackers:
            self._trackers[entity_id].update_center(y, x)
            return f"'{entity_id}' 跟踪中心已更新至 ({y},{x})。"
        return f"未找到实体 '{entity_id}'。"

    # ───────────────────────────────────────────
    # 核心感知接口：数据包输出
    # ───────────────────────────────────────────

    def capture(self) -> dict:
        """
        采集一帧完整数据包。这是摄像头向解释引擎交付的标准感知帧。
        """
        radius = self._get_radius()
        y0, x0, y1, x1 = self._focus_rect(radius)

        focus_gua = self.world.gua[y0:y1, x0:x1]
        hexagram = self._dominant_hexagram(focus_gua)
        active_lines = self._detect_active_lines(y0, x0, y1, x1)
        neighbor_profile = self._compute_neighbor_profile(y0, x0, y1, x1)
        history = self._get_history_for_packet(y0, x0, y1, x1)
        persistence = self._get_persistence()

        # 全局 yang_ratio（道控制器调节依据）
        yc = yang_count(self.world.gua)
        global_yang_ratio = float(np.mean(yc)) / 6.0

        return {
            "observer_id": self.observer_id,
            "timestamp": self.world.tick_count,
            "focus": {
                "center": [int(self.x), int(self.y), 0],
                "radius": radius,
            },
            "scale": self.scale,
            "intent": self.intent,
            "data": {
                "hexagram": hexagram,
                "active_lines": active_lines,
                "neighbor_profile": neighbor_profile,
                "history": history,
            },
            "persistence": persistence,
            "_meta": {
                "global_yang_ratio": round(global_yang_ratio, 3),
                "V_thresh": round(self.world.V_thresh, 3),
                "dao_bias": round(self.world.dao_bias, 3),
            }
        }

    def capture_minimal(self) -> dict:
        """
        极简版帧。适合性能最低的场合，解释引擎仍能输出基本描述。
        """
        radius = self._get_radius()
        y0, x0, y1, x1 = self._focus_rect(radius)

        focus_gua = self.world.gua[y0:y1, x0:x1]
        center_hex = self._dominant_hexagram(focus_gua)

        # active_line：若有多条，只取最活跃的一条；无则为 None
        active_lines = self._detect_active_lines(y0, x0, y1, x1)
        active_line = active_lines[0] if active_lines else None

        # 邻域主导卦
        ny0, nx0, ny1, nx1 = self._neighbor_rect(radius)
        neighbor_gua = self.world.gua[ny0:ny1, nx0:nx1]
        neighbor_dominant = self._dominant_hexagram(neighbor_gua) if neighbor_gua.size > 0 else 0

        return {
            "center_hex": center_hex,
            "active_line": active_line,
            "neighbor_dominant": neighbor_dominant,
            "scale": self.scale,
            "intent": self.intent,
        }

    # ───────────────────────────────────────────
    # 兼容接口：自然语言描述（向后兼容）
    # ───────────────────────────────────────────

    def look(self) -> str:
        """观测当前视野，返回自然语言描述（旧版兼容）。"""
        radius = self._get_radius()
        y0, x0, y1, x1 = self._focus_rect(radius)
        h = y1 - y0
        w = x1 - x0
        header = (
            f"【摄像机视野】焦点({self.y},{self.x})，尺度{self.scale}，"
            f"意图{self.intent}，范围({y0}:{y1},{x0}:{x1})\n"
        )
        return header + self._observer.observe_region(y0, x0, h, w)

    def look_point(self) -> str:
        """观测焦点单点。"""
        return self._observer.observe_point(self.y, self.x)

    def look_trajectory(self, back_steps: int = 30) -> str:
        """回溯焦点历史轨迹。"""
        return self._observer.observe_trajectory(self.y, self.x, back_steps)

    def scan_nearby(self, radius: int = 10) -> List[Tuple[int, int, str]]:
        """扫描焦点周围 radius 范围内的异常点。"""
        H, W = self.world.H, self.world.W
        y0 = max(0, self.y - radius)
        y1 = min(H, self.y + radius + 1)
        x0 = max(0, self.x - radius)
        x1 = min(W, self.x + radius + 1)

        vt = self.world.V_thresh
        anomalies = []
        sub_pot = self.world.potential[y0:y1, x0:x1]
        high = sub_pot > vt * 0.85
        if np.any(high):
            ys, xs = np.where(high)
            for y, x in zip(ys[:5], xs[:5]):
                gy, gx = int(y0 + y), int(x0 + x)
                pot = float(self.world.potential[gy, gx])
                gua = get_gua(int(self.world.gua[gy, gx]))
                anomalies.append((gy, gx, f"{gua['name']}卦势能{pot:.2f}"))
        return anomalies

    def auto_track(self) -> str:
        """自动追踪：将摄像机移动到全场最异常的地点。"""
        return self.pan_to_anomaly()

    def get_position(self) -> dict:
        """获取摄像机当前状态。"""
        return {
            "y": int(self.y),
            "x": int(self.x),
            "zoom": float(self.zoom),
            "scale": self.scale,
            "intent": self.intent,
            "world_tick": self.world.tick_count,
            "move_count": len(self.move_history),
            "active_tracker": self._active_tracker_id,
            "trackers": self.list_trackers(),
        }

    def narrative_trajectory(self) -> str:
        """返回摄像机的移动轨迹叙事。"""
        if len(self.move_history) <= 1:
            return "摄像机尚未移动。"
        lines = ["摄像机移动轨迹："]
        for i, rec in enumerate(self.move_history):
            lines.append(
                f"  第{i}站：第{rec['tick']}息 → ({rec['y']},{rec['x']}) "
                f"缩放{rec['zoom']:.1f} 尺度={rec['scale']} 意图={rec['intent']}"
            )
        return "\n".join(lines)

    # ───────────────────────────────────────────
    # 供 LLM 快速决策的辅助信息
    # ───────────────────────────────────────────

    def get_context_prompt(self) -> str:
        """
        为 LLM 生成一段可直接嵌入 system prompt 的摄像机上下文说明。
        告诉 LLM 当前能看到什么、能做什么。
        """
        pos = self.get_position()
        packet = self.capture_minimal()
        gua = get_gua(packet["center_hex"])
        neighbor = get_gua(packet["neighbor_dominant"])
        lines = [
            f"【世界摄像机状态】",
            f"- 你当前位于 ({pos['y']},{pos['x']})，世界第 {pos['world_tick']} 息。",
            f"- 观测尺度: {pos['scale']}，观测意图: {pos['intent']}。",
            f"- 焦点卦象: {gua['name']}（{gua['protocol']}），五行属{gua['wuxing']}。",
            f"- 邻域主导: {neighbor['name']}（{neighbor['protocol']}）。",
            f"- 活跃跟踪: {pos['active_tracker'] or '无'}。",
            f"- 已跟踪实体: {', '.join(pos['trackers']) or '无'}。",
            f"",
            f"【你可调用的摄像机操作】",
            f"- 移动: move_to(y,x), pan(dy,dx), pan_north(steps), pan_to_anomaly()",
            f"- 参数: set_scale('micro'|'meso'|'macro'|'cosmic'), set_intent('character'|...)",
            f"- 采集: capture() → 完整数据包, capture_minimal() → 极简帧",
            f"- 跟踪: track_entity(id,y,x,radius), untrack_entity(id), switch_tracker(id)",
            f"- 描述: look() → 自然语言, look_point() → 单点微观",
            f"- 状态: get_position(), scan_nearby(radius)",
        ]
        return "\n".join(lines)
