# -*- coding: utf-8 -*-
"""事件检测器"""
from codex import get_gua

OPPOSITE_PAIRS = {(0, 63), (9, 54), (18, 45), (27, 36)}


def compute_interaction(a_snap, b_snap):
    a_hex = a_snap["center_gua"]
    b_hex = b_snap["center_gua"]
    is_opp = (a_hex, b_hex) in OPPOSITE_PAIRS or (b_hex, a_hex) in OPPOSITE_PAIRS
    is_same = a_hex == b_hex
    pot_diff = abs(a_snap["center_pot"] - b_snap["center_pot"])
    phase_diff = abs(a_snap["center_phase"] - b_snap["center_phase"])
    score = 0
    if is_opp:
        score += 5
    if is_same:
        score += 2
    score += pot_diff * 2
    score += phase_diff * 2
    if a_snap["relation_type"] != b_snap["relation_type"]:
        score += 1
    return {
        "score": round(score, 1),
        "is_opposite": is_opp,
        "is_same": is_same,
        "pot_diff": round(pot_diff, 2),
        "phase_diff": round(phase_diff, 2),
    }


def family_interaction_score(snapshots):
    n = len(snapshots)
    score = 0
    opp_count = 0
    same_count = 0
    pot_spread = 0
    for i in range(n):
        for j in range(i + 1, n):
            a, b = snapshots[i]["center_gua"], snapshots[j]["center_gua"]
            if (a, b) in OPPOSITE_PAIRS or (b, a) in OPPOSITE_PAIRS:
                opp_count += 1
            if a == b:
                same_count += 1
            pot_spread = max(pot_spread, abs(snapshots[i]["center_pot"] - snapshots[j]["center_pot"]))
    score += opp_count * 4 + same_count * 2 + pot_spread * 3
    rels = set(s["relation_type"] for s in snapshots)
    score += len(rels) * 2
    max_pot = max(s["center_pot"] for s in snapshots)
    min_pot = min(s["center_pot"] for s in snapshots)
    score += max_pot * 2
    if max_pot > 1.5 and min_pot < 0.3:
        score += 3
    return round(score, 1)


def detect_cross_event(flip_events_list, all_snaps_list, tick_window=60):
    best_cross = None
    best_score = -1
    all_flips = []
    for idx, flips in enumerate(flip_events_list):
        for f in flips:
            all_flips.append((f["tick"], idx, f))
    for tick, flip_idx, flip in all_flips:
        member_snaps = []
        for idx, snaps in enumerate(all_snaps_list):
            best = None
            for s in snaps:
                if abs(s["tick"] - tick) <= tick_window:
                    if best is None or abs(s["tick"] - tick) < abs(best["tick"] - tick):
                        best = s
            if best:
                best["member_idx"] = idx
                member_snaps.append(best)
        if len(member_snaps) < 2:
            continue
        inter_score = family_interaction_score(member_snaps)
        flip_count = sum(
            1 for idx2, flips2 in enumerate(flip_events_list)
            if any(abs(f2["tick"] - tick) <= tick_window for f2 in flips2)
        )
        inter_score += flip_count * 3
        if inter_score > best_score:
            best_score = inter_score
            best_cross = {
                "tick": tick,
                "flip": flip,
                "flip_idx": flip_idx,
                "snaps": member_snaps,
                "score": inter_score,
                "flip_count": flip_count,
            }
    if best_cross is None:
        n = len(all_snaps_list)
        best_cross = {
            "tick": 1500,
            "score": 0,
            "snaps": [all_snaps_list[i][-1] for i in range(n)],
            "flip_count": 0,
        }
    return best_cross


def detect_family_event(flip_events_list, all_snaps_list, tick_window=75):
    events = []
    for t in range(tick_window, 1500 - tick_window, tick_window // 2):
        nearby_snaps = []
        for idx, snaps in enumerate(all_snaps_list):
            best = None
            for s in snaps:
                if abs(s["tick"] - t) <= tick_window:
                    if best is None or abs(s["tick"] - t) < abs(best["tick"] - t):
                        best = s
            if best:
                best["member_idx"] = idx
                nearby_snaps.append(best)
        if len(nearby_snaps) < 3:
            continue
        score = family_interaction_score(nearby_snaps)
        flip_count = sum(
            1 for idx, flips in enumerate(flip_events_list)
            if any(abs(f["tick"] - t) <= tick_window for f in flips)
        )
        score += flip_count * 3
        events.append({"tick": t, "score": score, "snaps": nearby_snaps, "flip_count": flip_count})
    events.sort(key=lambda x: x["score"], reverse=True)
    if events:
        return events[0]
    n = len(all_snaps_list)
    return {
        "tick": 1500,
        "score": 0,
        "snaps": [all_snaps_list[i][-1] for i in range(n)],
        "flip_count": 0,
    }


def detect_flip_event(flip_events, all_snaps):
    if not flip_events:
        return {
            "tick": 1500,
            "pre_name": "?",
            "post_name": "?",
            "pre_snap": all_snaps[-4] if len(all_snaps) >= 4 else all_snaps[0],
            "critical_snap": all_snaps[-3] if len(all_snaps) >= 3 else all_snaps[0],
            "post_snap": all_snaps[-2] if len(all_snaps) >= 2 else all_snaps[0],
            "stable_snap": all_snaps[-1],
        }
    best_story = None
    best_score = -1
    for flip in flip_events:
        flip_tick = flip["tick"]
        pre = critical = post = stable = None
        for snap in all_snaps:
            tick = snap["tick"]
            if flip_tick - 150 <= tick <= flip_tick - 50:
                if pre is None or abs(tick - (flip_tick - 100)) < abs(pre["tick"] - (flip_tick - 100)):
                    pre = snap
            if flip_tick - 40 <= tick <= flip_tick - 10:
                if critical is None or snap["center_pot"] > critical["center_pot"]:
                    critical = snap
            if flip_tick + 10 <= tick <= flip_tick + 40:
                if post is None or abs(tick - (flip_tick + 20)) < abs(post["tick"] - (flip_tick + 20)):
                    post = snap
            if flip_tick + 100 <= tick <= flip_tick + 200:
                if stable is None or abs(tick - (flip_tick + 150)) < abs(stable["tick"] - (flip_tick + 150)):
                    stable = snap
        if all([pre, critical, post, stable]):
            score = 0
            if pre["center_gua_name"] != post["center_gua_name"]:
                score += 1
            if critical:
                score += critical["center_pot"] * 2
            if pre["relation_type"] != post["relation_type"]:
                score += 2
            if score > best_score:
                best_score = score
                best_story = {
                    "flip": flip,
                    "pre_snap": pre,
                    "critical_snap": critical,
                    "post_snap": post,
                    "stable_snap": stable,
                }
    if best_story is None:
        return {
            "tick": flip_events[-1]["tick"] if flip_events else 1500,
            "pre_name": flip_events[-1]["pre_name"] if flip_events else "?",
            "post_name": flip_events[-1]["post_name"] if flip_events else "?",
            "pre_snap": all_snaps[-4],
            "critical_snap": all_snaps[-3],
            "post_snap": all_snaps[-2],
            "stable_snap": all_snaps[-1],
        }
    best_story["tick"] = best_story["flip"]["tick"]
    best_story["pre_name"] = best_story["flip"]["pre_name"]
    best_story["post_name"] = best_story["flip"]["post_name"]
    return best_story
