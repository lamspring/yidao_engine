# -*- coding: utf-8 -*-
"""语义包构造器 — 支持世界观绑定"""
from codex import get_gua
from renderer import get_sensory_packet, get_protocol_library


def _translate(text: str, worldview) -> str:
    """如果有世界观配置，翻译系统术语"""
    if worldview is None:
        return text
    # 翻译协议名
    for protocol, entry in worldview.protocol_map.items():
        text = text.replace(protocol, entry.get("name", protocol))
    return text


def format_member_compact(snap, member_name, worldview=None):
    body_p = _translate(snap['body_protocol'], worldview)
    usage_p = _translate(get_gua(snap['usage_hex'])['protocol'], worldview)
    rel = _translate(snap['relation_type'], worldview)
    return (
        f"  [{member_name}] {snap['center_gua_name']}({snap['center_gua']}) | "
        f"体:{body_p} | 用:{snap['usage_name']}({usage_p}) | "
        f"关系:{rel} | 相:{snap['center_phase']:.2f} | "
        f"势:{snap['center_pot']:.2f}({snap['pot_label']}) | 生阶:{snap['life_stage']}"
    )


def format_member_detailed(snap, member_name, worldview=None):
    body_p = _translate(snap['body_protocol'], worldview)
    usage_p = _translate(get_gua(snap['usage_hex'])['protocol'], worldview)
    rel = _translate(snap['relation_type'], worldview)
    rel_desc = snap['relation_desc']
    if worldview:
        for rt, rt_desc in worldview.relation_templates.items():
            rel_desc = rel_desc.replace(rt, rt_desc)
    # 世界观感官覆盖
    sensory = snap['sensory']
    if worldview and snap['body_protocol'] in worldview.protocol_map:
        w_sensory = worldview.protocol_map[snap['body_protocol']].get('sensory', {})
        if w_sensory.get('visual'): sensory['visual'] = w_sensory['visual'][:3]
        if w_sensory.get('sound'): sensory['sound'] = w_sensory['sound'][:3]
        if w_sensory.get('mood'): sensory['mood'] = w_sensory['mood'][:3]

    # Route-C v2：注入系统象法语库（8维度 + 文学变体）
    lib = get_protocol_library(snap['body_protocol'])

    # 用户自定义语库变体（优先级高于系统默认）
    user_variants = []
    if worldview and snap['body_protocol'] in worldview.protocol_map:
        user_variants = worldview.protocol_map[snap['body_protocol']].get('lexicon_variants', [])

    lit_variants = lib.get('variants', {})
    variant_lines = []

    if user_variants:
        # 用户自定义变体：根据 phase 确定性选择
        idx = int(snap['center_phase'] * 100) % len(user_variants)
        selected = user_variants[idx]
        variant_lines.append(f"    [用户自定义] {selected}")
        for i, v in enumerate(user_variants):
            marker = " ← 当前选中" if i == idx else ""
            variant_lines.append(f"    [{i}] {v[:60]}{'...' if len(v) > 60 else ''}{marker}")
    else:
        for k, v in lit_variants.items():
            variant_lines.append(f"    [{k}] {v}")

    lit_block = "\n".join(variant_lines) if variant_lines else "    （无预设变体）"

    # 根据 phase 选择确定性感官词
    phase_idx = int(snap['center_phase'] * 10) % 5
    def _pick(items, idx):
        if not items:
            return "—"
        return items[idx % len(items)]

    return f"""【{member_name}】tick {snap['tick']}
单点: {snap['center_gua_name']}({snap['center_gua']}) | {snap['center_protocol']} | 相位:{snap['center_phase']:.2f} | 势能:{snap['center_pot']:.2f}
体: {snap['body_name']}({snap['body_hex']}) | {body_p} | 本质: {snap['body_nature']}
用: {snap['usage_name']}({snap['usage_hex']}) | {usage_p}
结构语气: {snap['structural_tone']} | 生命阶段: {snap['life_stage']}
关系: {rel} | {rel_desc}
势能: {snap['pot_label']} ({snap['pot_atmosphere']})
感官: 视-{', '.join(sensory['visual'])} | 听-{', '.join(sensory['sound'])} | 动-{', '.join(sensory['motion'])} | 情-{', '.join(sensory['mood'])}
象法语库（8维）: 视-{_pick(lib['visual'], phase_idx)} | 听-{_pick(lib['sound'], phase_idx)} | 触-{_pick(lib['touch'], phase_idx)} | 嗅-{_pick(lib['smell'], phase_idx)} | 味-{_pick(lib['taste'], phase_idx)} | 情-{_pick(lib['mood'], phase_idx)} |  tempo-{_pick(lib['tempo'], phase_idx)} | 形-{_pick(lib['geometry'], phase_idx)}
文学变体:
{lit_block}
"""


def build_single_package(flip_event, story, tracker_name, worldview=None):
    timeline = f"""【观测对象】{_translate(tracker_name, worldview)}
【卦变事件】tick {flip_event['tick']}: {flip_event['pre_name']}({flip_event['pre_hex']}) -> {flip_event['post_name']}({flip_event['post_hex']})

以下是卦变前后连续跟踪采集到的 4 个时间切片：

【T-1 稳态期】tick {story['pre_snap']['tick']}
{format_member_detailed(story['pre_snap'], tracker_name, worldview)}

【T0 临界期】tick {story['critical_snap']['tick']}
{format_member_detailed(story['critical_snap'], tracker_name, worldview)}

【T+1 卦变后】tick {story['post_snap']['tick']}
{format_member_detailed(story['post_snap'], tracker_name, worldview)}

【T+2 新稳态】tick {story['stable_snap']['tick']}
{format_member_detailed(story['stable_snap'], tracker_name, worldview)}
"""
    if worldview:
        timeline += f"\n【世界观】{worldview.name} — {worldview.description}\n"
    return timeline


def build_family_package(family_event, member_configs, family_slices, worldview=None):
    member_names = [m.name for m in member_configs]
    cross_tick = family_event["tick"]
    lines = [
        f"【观测对象】{worldview.name if worldview else '五口之家'}家庭史诗",
        f"【世界观】{worldview.description if worldview else '通用易道世界'}",
        f"【家庭成员】",
    ]
    for i, mc in enumerate(member_configs):
        desc = mc.description
        if worldview and mc.name in worldview.character_archetypes:
            desc = worldview.character_archetypes[mc.name]
        lines.append(f"  {i}. {mc.name} — {desc}")
    lines.append(f"\n【家庭事件】tick {cross_tick} | 故事性评分 {family_event['score']:.1f} | {family_event['flip_count']} 位成员经历卦变\n")

    OPPOSITE_PAIRS = {(0, 63), (9, 54), (18, 45), (27, 36)}
    for label, target, members in family_slices:
        lines.append(f"═══ {label} (tick≈{target}) ═══")
        for idx, snap in enumerate(members):
            lines.append(format_member_compact(snap, member_names[idx], worldview))
        # 交互分析
        opposites = []
        sames = []
        for i in range(len(members)):
            for j in range(i + 1, len(members)):
                a, b = members[i]["center_gua"], members[j]["center_gua"]
                if (a, b) in OPPOSITE_PAIRS or (b, a) in OPPOSITE_PAIRS:
                    opposites.append(f"{member_names[i]}-{member_names[j]}")
                if a == b:
                    sames.append(f"{member_names[i]}-{member_names[j]}")
        if opposites:
            lines.append(f"  [先天对卦] {', '.join(opposites)}")
        if sames:
            lines.append(f"  [同卦共鸣] {', '.join(sames)}")
        max_pot = max(m["center_pot"] for m in members)
        min_pot = min(m["center_pot"] for m in members)
        lines.append(f"  [势能极差] {min_pot:.2f} ~ {max_pot:.2f}\n")

    # 附录：体本质 + 世界观映射
    lines.append("\n【附录：各成员体的本质描述】\n")
    t0_members = family_slices[2][2]
    for idx, snap in enumerate(t0_members):
        lines.append(f"{member_names[idx]}: {snap['body_nature']}")
        if worldview:
            w_name = worldview.translate_protocol(snap['body_protocol'], 'name')
            w_desc = worldview.translate_protocol(snap['body_protocol'], 'description')
            lines.append(f"  → 世界观映射: {w_name} ({w_desc})")

    # 世界观仪式模板
    if worldview and worldview.flip_ritual:
        lines.append(f"\n【卦变仪式模板】{worldview.flip_ritual.get('template', '')}")

    return "\n".join(lines)
