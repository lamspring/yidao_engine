# -*- coding: utf-8 -*-
"""世界模拟运行器"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from kernel import World
from observer import WorldCamera, EntityTracker
from analyst import YaoAnalyst
from event_engine import EventEngine
from codex import get_gua
from phenomenon_codex import get_potential_stage, get_manifestation, get_phenomenon
from .config import WorldConfig, EntityConfig


def _get_pure_hex(protocol_name):
    protocol_map = {"承载":0, "激变":9, "深渊":18, "渗透":27, "止界":36, "显文明":45, "交换":54, "创序":63}
    return protocol_map.get(protocol_name, 0)


def capture_compact(world, cam, tracker, analyst, tick_label):
    """精简快照"""
    cam.move_to(tracker.center_y, tracker.center_x)
    body_usage = analyst.run_two_rounds(tracker, perspective="objective")
    cy, cx = tracker.center_y, tracker.center_x
    center_gua = int(world.gua[cy, cx])
    center_phase = float(world.phase[cy, cx])
    center_pot = float(world.potential[cy, cx])
    body = body_usage["body"]
    usage = body_usage["usage"]
    relation = body_usage["relation"]
    pot_stage = get_potential_stage(center_pot, world.V_thresh)
    protocol = usage.get("_meta", {}).get("protocol", get_gua(usage["current_hex"]).get("protocol", "复合"))
    pure_hex = _get_pure_hex(protocol)
    return {
        "tick_label": tick_label, "tick": world.tick_count,
        "center_gua": center_gua, "center_gua_name": get_gua(center_gua)["name"],
        "center_protocol": get_gua(center_gua)["protocol"],
        "center_phase": round(center_phase, 2), "center_pot": round(center_pot, 2),
        "body_name": body["body_name"], "body_protocol": body["body_protocol"],
        "body_nature": body["body_nature"].split("。")[0] + "。",
        "usage_name": usage["current_name"], "usage_hex": usage["current_hex"],
        "structural_tone": usage["structural_tone"],
        "life_stage": usage["life_stage"],
        "relation_type": relation["type"], "relation_desc": relation["description"],
        "pot_label": pot_stage["ratio_label"], "pot_atmosphere": pot_stage["atmosphere"],
        "manifestation": get_manifestation(pure_hex, cam.intent or "character"),
        "sensory": {
            "visual": get_phenomenon(pure_hex, "visual")[:3],
            "sound": get_phenomenon(pure_hex, "sound")[:3],
            "motion": get_phenomenon(pure_hex, "motion")[:3],
            "mood": get_phenomenon(pure_hex, "mood")[:3],
        },
    }


class WorldRunner:
    def __init__(self, world_cfg: WorldConfig, entities_cfg: list[EntityConfig]):
        self.world = World(height=world_cfg.height, width=world_cfg.width)
        self.cam = WorldCamera(self.world, y=14, x=30, scale=world_cfg.camera_scale, intent=world_cfg.camera_intent)
        self.analyst = YaoAnalyst(self.cam)
        self.engine = EventEngine(self.world, self.analyst)
        self.trackers = []
        self.flip_events = []
        self.all_snapshots = []
        self.ticks = world_cfg.ticks
        self.interval = world_cfg.snapshot_interval

        for ec in entities_cfg:
            t = EntityTracker(self.world, ec.name, ec.y, ec.x, radius=ec.radius)
            self.trackers.append(t)
            self.flip_events.append([])
            self.all_snapshots.append([])

    def run(self, progress_callback=None):
        for i in range(self.ticks):
            self.world.tick()
            for idx, t in enumerate(self.trackers):
                t._update()
                if len(t.hex_history) >= 2:
                    prev, curr = t.hex_history[-2], t.hex_history[-1]
                    if prev != curr:
                        self.flip_events[idx].append({
                            "tick": self.world.tick_count,
                            "pre_hex": prev, "post_hex": curr,
                            "pre_name": get_gua(prev)["name"], "post_name": get_gua(curr)["name"],
                        })
            if (i + 1) % self.interval == 0:
                for idx, t in enumerate(self.trackers):
                    self.all_snapshots[idx].append(capture_compact(
                        self.world, self.cam, t, self.analyst,
                        f"{t.entity_id}_T{i+1}"
                    ))
            if progress_callback and (i + 1) % 500 == 0:
                total_flips = sum(len(f) for f in self.flip_events)
                progress_callback(i + 1, total_flips)
        return self
