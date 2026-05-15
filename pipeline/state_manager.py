# -*- coding: utf-8 -*-
"""状态管理器 — 支持世界的保存、加载和增量演化"""
import os
import json
import numpy as np
from typing import List, Dict, Optional, Tuple


def _ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)


def save_state(world, trackers: list, camera, out_dir: str, name: Optional[str] = None) -> str:
    """
    保存世界状态到磁盘。
    返回保存目录路径。
    """
    if name is None:
        from datetime import datetime
        name = datetime.now().strftime("%Y%m%d_%H%M%S")

    state_dir = os.path.join(out_dir, name)
    _ensure_dir(state_dir)

    # 1. 保存 numpy 数组
    np.savez(
        os.path.join(state_dir, "world.npz"),
        gua=world.gua,
        trend=world.trend,
        phase=world.phase,
        potential=world.potential,
        stable_age=world.stable_age,
    )

    # 2. 保存 world 标量参数
    world_meta = {
        "H": int(world.H),
        "W": int(world.W),
        "tick_count": int(world.tick_count),
        "V_thresh": float(world.V_thresh),
        "gamma": float(world.gamma),
        "alpha": float(world.alpha),
        "dao_bias": float(world.dao_bias),
        "dao_check_interval": int(world.dao_check_interval),
        "HISTORY_MAX": int(world.HISTORY_MAX),
        "history": [h.tolist() for h in world.history],
    }
    with open(os.path.join(state_dir, "world_meta.json"), "w", encoding="utf-8") as f:
        json.dump(world_meta, f, ensure_ascii=False, indent=2)

    # 3. 保存 trackers
    trackers_data = []
    for t in trackers:
        trackers_data.append({
            "entity_id": t.entity_id,
            "center_y": int(t.center_y),
            "center_x": int(t.center_x),
            "radius": int(t.radius),
            "hex_history": [int(h) for h in t.hex_history],
            "tick_history": [int(tk) for tk in t.tick_history],
            "max_history": int(t.max_history),
            "is_persistent": bool(t.is_persistent),
            "event_state": t.event_state,
        })
    with open(os.path.join(state_dir, "trackers.json"), "w", encoding="utf-8") as f:
        json.dump(trackers_data, f, ensure_ascii=False, indent=2)

    # 4. 保存 camera
    camera_data = {
        "observer_id": camera.observer_id,
        "y": int(camera.y),
        "x": int(camera.x),
        "scale": camera.scale,
        "intent": camera.intent,
        "zoom": float(camera.zoom),
        "move_history": camera.move_history,
        "tracker_ids": list(camera._trackers.keys()),
        "active_tracker_id": camera._active_tracker_id,
    }
    with open(os.path.join(state_dir, "camera.json"), "w", encoding="utf-8") as f:
        json.dump(camera_data, f, ensure_ascii=False, indent=2)

    print(f"[状态保存] 已保存到 {state_dir}")
    print(f"           tick={world.tick_count} | 实体数={len(trackers)}")
    return state_dir


def load_state(world, camera, out_dir: str, name: str) -> list:
    """
    从磁盘加载世界状态。
    传入已有的 world 和 camera 对象（会被修改），返回重新创建的 trackers 列表。
    """
    state_dir = os.path.join(out_dir, name)
    if not os.path.isdir(state_dir):
        raise FileNotFoundError(f"状态目录不存在: {state_dir}")

    # 1. 加载 numpy 数组
    npz = np.load(os.path.join(state_dir, "world.npz"))
    world.gua[:] = npz["gua"]
    world.trend[:] = npz["trend"]
    world.phase[:] = npz["phase"]
    world.potential[:] = npz["potential"]
    world.stable_age[:] = npz["stable_age"]

    # 2. 加载 world 标量参数
    with open(os.path.join(state_dir, "world_meta.json"), "r", encoding="utf-8") as f:
        meta = json.load(f)

    world.tick_count = meta["tick_count"]
    world.V_thresh = meta["V_thresh"]
    world.gamma = meta["gamma"]
    world.alpha = meta["alpha"]
    world.dao_bias = meta["dao_bias"]
    world.dao_check_interval = meta["dao_check_interval"]
    world.HISTORY_MAX = meta.get("HISTORY_MAX", 24)
    world.history = [np.array(h, dtype=np.uint8) for h in meta.get("history", [])]

    # 3. 重建 buffers（尺寸可能变化）
    world._buf_gua = np.zeros_like(world.gua)
    world._buf_trend = np.zeros_like(world.trend)
    world._buf_phase = np.zeros_like(world.phase)
    world._buf_potential = np.zeros_like(world.potential)

    # 4. 重建 trackers
    from observer import EntityTracker
    trackers = []
    with open(os.path.join(state_dir, "trackers.json"), "r", encoding="utf-8") as f:
        trackers_data = json.load(f)

    for td in trackers_data:
        t = EntityTracker(world, td["entity_id"], td["center_y"], td["center_x"], td["radius"])
        t.hex_history = [int(h) for h in td["hex_history"]]
        t.tick_history = [int(tk) for tk in td["tick_history"]]
        t.max_history = td.get("max_history", 64)
        t.is_persistent = td.get("is_persistent", True)
        t.event_state = td.get("event_state", {
            "last_first_dx_tick": -9999,
            "last_re_dx_tick": -9999,
            "last_emergency_tick": -9999,
            "post_flip_cooldown": 0,
            "flip_recorded": False,
        })
        trackers.append(t)

    # 5. 恢复 camera
    with open(os.path.join(state_dir, "camera.json"), "r", encoding="utf-8") as f:
        cam_data = json.load(f)

    camera.observer_id = cam_data["observer_id"]
    camera.y = cam_data["y"] % world.H
    camera.x = cam_data["x"] % world.W
    camera.scale = cam_data["scale"]
    camera.intent = cam_data["intent"]
    camera.zoom = cam_data["zoom"]
    camera.move_history = cam_data.get("move_history", [])

    # 重新绑定 trackers 到 camera
    camera._trackers = {}
    for t in trackers:
        camera._trackers[t.entity_id] = t
    camera._active_tracker_id = cam_data.get("active_tracker_id")
    if camera._active_tracker_id and camera._active_tracker_id not in camera._trackers:
        camera._active_tracker_id = None

    print(f"[状态加载] 从 {state_dir}")
    print(f"           tick={world.tick_count} | 实体数={len(trackers)} | 历史帧={len(world.history)}")
    return trackers


def list_states(out_dir: str) -> List[Tuple[str, dict]]:
    """列出所有已保存的状态，返回 [(name, meta), ...]"""
    states = []
    if not os.path.isdir(out_dir):
        return states
    for name in sorted(os.listdir(out_dir)):
        state_dir = os.path.join(out_dir, name)
        meta_path = os.path.join(state_dir, "world_meta.json")
        if os.path.isfile(meta_path):
            with open(meta_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
            states.append((name, meta))
    return states
