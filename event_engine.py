# -*- coding: utf-8 -*-
"""
《易道动态世界引擎》v2.0 — 事件驱动引擎 (EventEngine)

P4 核心：让解释层学会在恰当的时机开口说话。

四大事件：
  初诊(FirstDx)  : 首次聚焦 / 长期未观测后的重新诊断
  复诊(ReDx)     : 卦变发生后 3-5 息内的局部更新
  急诊(Emergency): 势能濒临临界（V > 0.9 * V_thresh）
  会诊(Conference): 多区域共振卦变（天下大势）
"""

import numpy as np
from typing import List, Dict, Optional, Tuple
from collections import Counter


# ═══════════════════════════════════════════
# 事件类型常量
# ═══════════════════════════════════════════

EVENT_FIRST_DX = "初诊"
EVENT_RE_DX = "复诊"
EVENT_EMERGENCY = "急诊"
EVENT_CONFERENCE = "会诊"


# ═══════════════════════════════════════════
# 事件引擎核心类
# ═══════════════════════════════════════════

class EventEngine:
    """
    事件驱动引擎。

    使用方式：
        engine = EventEngine(world, analyst)
        
        # 每息或按需检测
        for tracker in trackers:
            events = engine.check_tracker_events(tracker)
            for ev in events:
                print(ev["narrative"])
        
        global_event = engine.check_global_events(trackers)
        if global_event:
            print(global_event["narrative"])
    """

    # 冷却期配置（息数）
    COOLDOWN_FIRST_DX = 300      # 初诊冷却
    COOLDOWN_RE_DX = 10          # 复诊冷却
    COOLDOWN_EMERGENCY = 20      # 急诊冷却
    COOLDOWN_CONFERENCE = 50     # 会诊冷却（全局）

    # 触发阈值
    EMERGENCY_POT_RATIO = 0.90   # 急诊势能比例
    CONFERENCE_MIN_COUNT = 3     # 会诊最小参与实体数
    CONFERENCE_TIME_WINDOW = 10  # 会诊时间窗口（息）

    def __init__(self, world, analyst):
        self.world = world
        self.analyst = analyst
        self.conference_cooldown = 0  # 全局会诊冷却计数
        self.last_conference_tick = -9999

    # ───────────────────────────────────────────
    # 单个 tracker 的事件检测
    # ───────────────────────────────────────────

    def check_tracker_events(self, tracker) -> List[Dict]:
        """
        检测指定 tracker 上的所有触发事件。
        返回事件列表（可能为空，可能包含 1-3 个事件）。
        """
        events = []
        tick = self.world.tick_count
        es = tracker.event_state

        # 1. 初诊检测
        if tick - es["last_first_dx_tick"] > self.COOLDOWN_FIRST_DX:
            events.append(self._build_first_dx(tracker))
            es["last_first_dx_tick"] = tick

        # 2. 复诊检测：卦变后 3-5 息窗口内
        cooldown = es["post_flip_cooldown"]
        if 3 <= cooldown <= 5 and tick - es["last_re_dx_tick"] > self.COOLDOWN_RE_DX:
            events.append(self._build_re_dx(tracker))
            es["last_re_dx_tick"] = tick

        # 3. 急诊检测：区域内势能临界
        if tick - es["last_emergency_tick"] > self.COOLDOWN_EMERGENCY:
            if self._is_emergency(tracker):
                events.append(self._build_emergency(tracker))
                es["last_emergency_tick"] = tick

        return events

    # ───────────────────────────────────────────
    # 全局事件检测：会诊
    # ───────────────────────────────────────────

    def check_global_events(self, trackers: List) -> Optional[Dict]:
        """
        检测全局会诊事件。
        返回会诊事件或 None。
        """
        tick = self.world.tick_count
        if tick - self.last_conference_tick <= self.COOLDOWN_CONFERENCE:
            return None

        # 收集最近发生卦变的 tracker
        recent_flippers = []
        for t in trackers:
            if len(t.hex_history) < 2:
                continue
            # 检查最近 CONFERENCE_TIME_WINDOW 息内是否有卦变
            # 由于 hex_history 只保留 64 帧，检查最近几帧即可
            changed = False
            hist = t.hex_history
            for i in range(max(1, len(hist) - self.CONFERENCE_TIME_WINDOW), len(hist)):
                if hist[i] != hist[i - 1]:
                    changed = True
                    break
            if changed:
                recent_flippers.append(t)

        if len(recent_flippers) < self.CONFERENCE_MIN_COUNT:
            return None

        # 检查共振：卦变方向或目标卦的一致性
        resonance = self._check_resonance(recent_flippers)
        if not resonance:
            return None

        self.last_conference_tick = tick
        return self._build_conference(recent_flippers, resonance)

    # ───────────────────────────────────────────
    # 触发条件判断
    # ───────────────────────────────────────────

    def _is_emergency(self, tracker) -> bool:
        """判断 tracker 区域内是否存在急诊条件。"""
        y0, x0, y1, x1 = tracker._region_rect()
        if y1 <= y0 or x1 <= x0:
            return False
        region_pot = self.world.potential[y0:y1, x0:x1]
        if region_pot.size == 0:
            return False
        threshold = self.world.V_thresh * self.EMERGENCY_POT_RATIO
        return bool(np.any(region_pot > threshold))

    def _check_resonance(self, trackers: List) -> Optional[Dict]:
        """
        检查多个 tracker 的卦变是否呈现共振一致性。
        
        共振判定：
          - 目标卦一致性：多个 tracker 卦变后趋向同一卦或同一协议
          - 方向一致性：多个 tracker 同时向阳/向阴转化
        
        返回共振信息字典，若无共振返回 None。
        """
        if len(trackers) < self.CONFERENCE_MIN_COUNT:
            return None

        # 收集最近的变化信息
        post_hexes = []
        pre_hexes = []
        for t in trackers:
            if len(t.hex_history) < 2:
                continue
            post_hexes.append(t.hex_history[-1])
            pre_hexes.append(t.hex_history[-2])

        if len(post_hexes) < self.CONFERENCE_MIN_COUNT:
            return None

        # 1. 目标卦一致性：统计变化后的卦
        post_counter = Counter(post_hexes)
        top_post, top_post_count = post_counter.most_common(1)[0]
        
        # 2. 协议一致性
        from codex import get_gua
        post_protocols = [get_gua(h)["protocol"] for h in post_hexes]
        proto_counter = Counter(post_protocols)
        top_proto, top_proto_count = proto_counter.most_common(1)[0]

        # 3. 方向一致性：阳爻数变化
        from kernel import yang_count
        pre_yang = [int(yang_count(np.array([h], dtype=np.uint8))[0]) for h in pre_hexes]
        post_yang = [int(yang_count(np.array([h], dtype=np.uint8))[0]) for h in post_hexes]
        yang_changes = [post_yang[i] - pre_yang[i] for i in range(len(pre_yang))]
        upward = sum(1 for c in yang_changes if c > 0)  # 阳化
        downward = sum(1 for c in yang_changes if c < 0)  # 阴化

        # 判定标准：满足以下任一即视为共振
        resonance_type = None
        resonance_desc = ""
        
        if top_post_count >= len(trackers) * 0.5:
            # 半数以上变向同一卦
            gua = get_gua(top_post)
            resonance_type = "目标汇聚"
            resonance_desc = f"多个实体同时向 {gua['name']} 卦({gua['protocol']})汇聚"
        elif top_proto_count >= len(trackers) * 0.6:
            # 六成以上变向同一协议
            resonance_type = "协议共鸣"
            resonance_desc = f"多个实体同时显化为'{top_proto}'协议"
        elif upward >= len(trackers) * 0.6:
            resonance_type = "阳化共振"
            resonance_desc = "多个实体同时向阳转化，生发之气充盈"
        elif downward >= len(trackers) * 0.6:
            resonance_type = "阴化共振"
            resonance_desc = "多个实体同时向阴转化，收敛之势已成"
        else:
            return None

        return {
            "type": resonance_type,
            "description": resonance_desc,
            "participants": len(trackers),
            "dominant_post_hex": top_post,
            "dominant_protocol": top_proto,
        }

    # ───────────────────────────────────────────
    # 事件构建
    # ───────────────────────────────────────────

    def _build_first_dx(self, tracker) -> Dict:
        """构建初诊事件。"""
        result = self.analyst.run_two_rounds(tracker, perspective="objective")
        return {
            "event_type": EVENT_FIRST_DX,
            "entity_id": tracker.entity_id,
            "tick": self.world.tick_count,
            "narrative": (
                f"【初诊】{tracker.entity_id} 首次被观测。"
                f"其体为 {result['body']['body_name']}({result['body']['body_type']})，"
                f"当下显化为 {result['usage']['current_name']}。"
                f"{result['relation']['description']}。"
            ),
            "detail": result,
        }

    def _build_re_dx(self, tracker) -> Dict:
        """构建复诊事件。"""
        es = tracker.event_state
        pre_hex = es.get("pre_flip_hex", 0)
        post_hex = es.get("post_flip_hex", 0)
        
        from codex import get_gua
        pre_name = get_gua(pre_hex)["name"]
        post_name = get_gua(post_hex)["name"]
        
        # 获取当前用象
        result = self.analyst.run_two_rounds(tracker, perspective="objective")
        
        return {
            "event_type": EVENT_RE_DX,
            "entity_id": tracker.entity_id,
            "tick": self.world.tick_count,
            "narrative": (
                f"【复诊】{tracker.entity_id} 刚发生卦变：{pre_name} → {post_name}。"
                f"{result['usage']['change_narrative']}"
            ),
            "detail": {
                "pre_hex": pre_hex,
                "post_hex": post_hex,
                "pre_name": pre_name,
                "post_name": post_name,
                "usage": result["usage"],
            },
        }

    def _build_emergency(self, tracker) -> Dict:
        """构建急诊事件。"""
        y0, x0, y1, x1 = tracker._region_rect()
        region_pot = self.world.potential[y0:y1, x0:x1]
        max_pot = float(np.max(region_pot))
        vt = self.world.V_thresh
        
        # 找到最高势能点的卦象
        max_idx = np.unravel_index(np.argmax(region_pot), region_pot.shape)
        max_y, max_x = y0 + max_idx[0], x0 + max_idx[1]
        max_gua = int(self.world.gua[max_y, max_x])
        from codex import get_gua as get_gua_info
        gua_info = get_gua_info(max_gua)
        
        result = self.analyst.run_two_rounds(tracker, perspective="objective")
        
        return {
            "event_type": EVENT_EMERGENCY,
            "entity_id": tracker.entity_id,
            "tick": self.world.tick_count,
            "narrative": (
                f"【急诊】{tracker.entity_id} 势能临界！"
                f"最大势能 {max_pot:.2f} / 阈值 {vt:.2f}。"
                f"临界点为 {gua_info['name']} 卦({gua_info['protocol']})。"
                f"{result['relation']['description']}。"
                f"势已积蓄至爆发边缘。"
            ),
            "detail": {
                "max_potential": max_pot,
                "V_thresh": vt,
                "critical_gua": gua_info["name"],
                "critical_protocol": gua_info["protocol"],
                "momentum": result.get("momentum", {}),
            },
        }

    def _build_conference(self, trackers: List, resonance: Dict) -> Dict:
        """构建会诊事件。"""
        participants = [t.entity_id for t in trackers]
        return {
            "event_type": EVENT_CONFERENCE,
            "tick": self.world.tick_count,
            "narrative": (
                f"【会诊·天下大势】第 {self.world.tick_count} 息，"
                f"{len(trackers)} 个实体同时发生卦变，呈现 {resonance['type']}。"
                f"{resonance['description']}。"
                f"此乃大规模结构性变动的征兆，非局部扰动可比。"
            ),
            "detail": {
                "resonance_type": resonance["type"],
                "resonance_desc": resonance["description"],
                "participants": participants,
                "dominant_post_hex": resonance["dominant_post_hex"],
                "dominant_protocol": resonance["dominant_protocol"],
            },
        }
