# -*- coding: utf-8 -*-
"""
《易道动态世界引擎》v4.0 — 涌现解释器 (YaoRenderer)
将底层阴阳场、趋势场、势能场翻译为可读的世界描述与终端可视化。

原则：
  本层只做解释，不做状态修改。
  所有输出都是卦场快照的涌现语义。
"""

import numpy as np
from collections import Counter
from codex import (
    get_gua, get_phase_meaning, PROTOCOL_COLOR_RGB, gua_to_color
)

# 亮度块字符（按阳爻比例）
BRIGHT_CHARS = " ░▒▓█"
# 趋势方向字符
TREND_CHARS = "▽▼▸▲△"  # 强阴、中阴、平、中阳、强阳


def _rgb_to_ansi256(r: int, g: int, b: int) -> int:
    """RGB 转 256 色 ANSI 码"""
    if r == g == b:
        if r < 8:
            return 16
        if r > 248:
            return 231
        return 232 + ((r - 8) // 10)
    r_idx = r // 51
    g_idx = g // 51
    b_idx = b // 51
    return 16 + 36 * r_idx + 6 * g_idx + b_idx


def _fg(text: str, rgb: tuple) -> str:
    code = _rgb_to_ansi256(*rgb)
    return f"\033[38;5;{code}m{text}\033[0m"


def _bg(text: str, rgb: tuple) -> str:
    code = _rgb_to_ansi256(*rgb)
    return f"\033[48;5;{code}m{text}\033[0m"


class YaoRenderer:
    """卦场涌现解释器"""

    def __init__(self, world):
        self.world = world
        self.prev_gua = None
        self.flips = np.zeros((world.H, world.W), dtype=np.uint8)

    def analyze_region(self, y0: int, x0: int, h: int, w: int) -> dict:
        """分析区域卦场，返回统计与涌现语义。"""
        H, W = self.world.H, self.world.W
        y1 = min(H, y0 + h)
        x1 = min(W, x0 + w)

        rgua = self.world.gua[y0:y1, x0:x1]
        rtrend = self.world.trend[y0:y1, x0:x1]
        rphase = self.world.phase[y0:y1, x0:x1]
        rpot = self.world.potential[y0:y1, x0:x1]
        rstab = self.world.stable_age[y0:y1, x0:x1]

        cells = rgua.size
        if cells == 0:
            return {"error": "empty region"}

        # 主导卦
        vals, counts = np.unique(rgua, return_counts=True)
        top_idx = int(np.argmax(counts))
        top_gua_val = int(vals[top_idx])
        top_gua = get_gua(top_gua_val)
        dominance = float(counts[top_idx]) / cells

        # 协议分布
        proto_counts = Counter()
        for v in vals:
            proto = get_gua(int(v))["protocol"]
            proto_counts[proto] += int(counts[vals == v][0])

        dominant_proto = proto_counts.most_common(1)[0][0]

        # 趋势统计
        mean_trend = float(np.mean(rtrend))
        max_trend = float(np.max(np.abs(rtrend)))

        # 相位与势能
        mean_phase = float(np.mean(rphase))
        mean_pot = float(np.mean(rpot))
        max_pot = float(np.max(rpot))

        # 阳爻比
        yc = np.unpackbits(rgua.view(np.uint8), bitorder='little')
        yc = yc.reshape(rgua.shape[0], rgua.shape[1], 8)[:, :, :6]
        yang_ratio = float(np.mean(yc))

        # 稳定度
        mean_stable = float(np.mean(rstab))

        return {
            "top_gua": top_gua,
            "dominance": dominance,
            "dominant_protocol": dominant_proto,
            "protocol_dist": dict(proto_counts),
            "yang_ratio": yang_ratio,
            "mean_trend": mean_trend,
            "max_trend": max_trend,
            "mean_phase": mean_phase,
            "mean_potential": mean_pot,
            "max_potential": max_pot,
            "mean_stable": mean_stable,
            "phase_meaning": get_phase_meaning(dominant_proto, mean_phase),
            "cells": cells,
        }

    def _trend_char(self, t: float) -> str:
        """趋势方向字符"""
        if t < -0.5:
            return "▽"
        elif t < -0.15:
            return "▼"
        elif t > 0.5:
            return "△"
        elif t > 0.15:
            return "▲"
        else:
            return "·"

    def render_terminal(self, detail: bool = True) -> str:
        """
        终端可视化渲染。
        每个格点：背景色 = 协议色，字符 = 阳爻比例/趋势/势能状态。
        """
        world = self.world
        grid = world.gua
        trend = world.trend
        pot = world.potential
        phase = world.phase
        H, W = grid.shape

        lines = []
        header_w = W + 24

        # 爻变检测
        if self.prev_gua is not None:
            self.flips = (grid != self.prev_gua).astype(np.uint8)
        self.prev_gua = grid.copy()

        # ── 顶部统计栏 ──
        lines.append("═" * header_w)

        # 全局统计
        yc = np.unpackbits(grid.view(np.uint8), bitorder='little')
        yc = yc.reshape(H, W, 8)[:, :, :6]
        global_yang = float(np.mean(yc))
        mean_trend_energy = float(np.mean(np.abs(trend)))

        # 主导协议（全局）
        all_vals, all_counts = np.unique(grid, return_counts=True)
        proto_cnt = Counter()
        for v, c in zip(all_vals, all_counts):
            proto_cnt[get_gua(int(v))["protocol"]] += int(c)
        top_proto = proto_cnt.most_common(1)[0][0] if proto_cnt else "?"

        lines.append(
            f" 易道引擎 v4.0 │ 息数:{world.tick_count:5d} │ "
            f"道阈值V:{world.V_thresh:.2f} │ 道偏置:{world.dao_bias:+.3f}"
        )
        lines.append(
            f" 阳爻比:{global_yang:.1%} │ 气象能:{mean_trend_energy:.2f} │ "
            f"主导协议:{top_proto}"
        )
        lines.append("─" * header_w)

        # ── 卦场可视化 ──
        for y in range(H):
            row = ""
            for x in range(W):
                v = int(grid[y, x])
                info = get_gua(v)
                rgb = PROTOCOL_COLOR_RGB.get(info["protocol"], (180, 160, 200))
                ratio = bin(v).count('1') / 6.0

                # 选择字符
                if self.flips[y, x]:
                    ch = "◆"  # 刚发生卦变
                elif pot[y, x] > world.V_thresh * 0.85:
                    ch = "●"  # 势能濒临爆发
                elif abs(trend[y, x]) > 0.7:
                    ch = self._trend_char(trend[y, x])  # 强气象标记
                else:
                    ch = BRIGHT_CHARS[min(int(ratio * 4), 4)]

                # 势能高时背景色微微提亮（视觉警示）
                if pot[y, x] > world.V_thresh * 0.7:
                    rgb_alert = (
                        min(255, rgb[0] + 40),
                        min(255, rgb[1] + 20),
                        min(255, rgb[2] + 20),
                    )
                    row += _bg(ch, rgb_alert)
                else:
                    row += _bg(ch, rgb)
            lines.append(row)

        # ── 底部区域解释 ──
        if detail:
            lines.append("─" * header_w)
            ay, ax = H // 4, W // 4
            info = self.analyze_region(ay, ax, H // 2, W // 2)

            if "error" not in info:
                tg = info["top_gua"]
                trend_dir = "阳化" if info["mean_trend"] > 0 else "阴化"
                pot_alert = "【濒临反转】" if info["max_potential"] > world.V_thresh else ""

                lines.append(
                    f"【中心区域】{tg['name']}({tg['protocol']}) │ "
                    f"相位:{info['mean_phase']:.2f} │ 势能:{info['mean_potential']:.2f} {pot_alert}"
                )
                lines.append(f"  六爻语义: {info['phase_meaning']}")
                lines.append(
                    f"  区域气象:{info['mean_trend']:+.2f}({trend_dir}) │ "
                    f"稳定度:{info['mean_stable']:.0f}息 │ 集中度:{info['dominance']:.1%}"
                )
                # 协议分布
                dist = info["protocol_dist"]
                dist_str = " ".join([f"{k}:{v}" for k, v in sorted(dist.items(), key=lambda x: -x[1])[:4]])
                lines.append(f"  协议分布: {dist_str}")

        lines.append("═" * header_w)
        return "\n".join(lines)

    def render_simple(self) -> str:
        """极简渲染：只返回卦场亮度字符画（无颜色）"""
        lines = []
        for y in range(self.world.H):
            row = ""
            for x in range(self.world.W):
                v = int(self.world.gua[y, x])
                ratio = bin(v).count('1') / 6.0
                row += BRIGHT_CHARS[min(int(ratio * 4), 4)]
            lines.append(row)
        return "\n".join(lines)

    def render_trend_field(self, width: int = 64) -> str:
        """气象场文本可视化（用于调试/深度观测）"""
        H, W = self.world.H, self.world.W
        lines = ["【气象场】阴化 ← → 阳化"]
        for y in range(H):
            row = ""
            for x in range(W):
                t = self.world.trend[y, x]
                if t < -0.3:
                    row += "-"
                elif t > 0.3:
                    row += "+"
                elif abs(t) < 0.05:
                    row += "."
                else:
                    row += self._trend_char(t)
            lines.append(row)
        return "\n".join(lines)

    def render_potential_field(self, width: int = 64) -> str:
        """势能场文本可视化"""
        H, W = self.world.H, self.world.W
        pot = self.world.potential
        lines = ["【势能场】.低  ░中  ▒高  ▓临界  █爆发"]
        for y in range(H):
            row = ""
            for x in range(W):
                p = pot[y, x]
                if p < 0.2:
                    row += "."
                elif p < 0.5:
                    row += "░"
                elif p < 0.8:
                    row += "▒"
                elif p < self.world.V_thresh:
                    row += "▓"
                else:
                    row += "█"
            lines.append(row)
        return "\n".join(lines)


# ═══════════════════════════════════════════════════════
# Route-C v2 象法语库 — 八协议多维感官 + 文学变体
# ═══════════════════════════════════════════════════════

PROTOCOL_LIBRARY = {
    "承载": {
        "core": "承载万物的底层结构，不抵抗、不选择，纯粹的接纳与孕育",
        "variants": {
            "道家": "大地无疆，厚德载物，不为主而为万物之宾",
            "存在主义": "列维纳斯的'面容'，他者的不可吞噬性，伦理的无限责任",
            "科幻": "戴森球内部的生态穹顶，人工重力下的稳定农业层",
            "神话": "盖亚的子宫，所有生命的共同母亲，沉默而永恒",
        },
        "visual": ["土黄", "广袤平原", "厚重云层", "缓慢移动的影子", "深沉的大地色"],
        "sound": ["低沉", "大地嗡鸣", "远处雷声", "寂静中的重量", "土壤的呼吸"],
        "touch": ["温暖", "坚实", "湿润", "沉重", "包容的厚度"],
        "smell": ["泥土", "腐殖质", "雨后", "根系", "大地的气息"],
        "taste": ["甘甜", "淀粉", "根系的涩", "土地的咸"],
        "mood": ["包容", "沉默", "耐心", "忧郁", "母性的宁静"],
        "tempo": ["极慢", "恒常", "无节奏", "永恒的呼吸"],
        "geometry": ["水平延展", "下沉", "广阔", "无边界的平面"],
    },
    "激变": {
        "core": "结构的突然断裂与重构，旧秩序的瞬间瓦解与新可能性的强制开启",
        "variants": {
            "道家": "惊蛰，春雷唤醒蛰虫，不是毁灭而是唤醒",
            "存在主义": "海德格尔的'焦虑'瞬间，日常状态的崩塌，此在的本真显现",
            "科幻": "曲率引擎的第一次点火，空间本身的褶皱与撕裂",
            "神话": "托尔的雷霆，不是惩罚而是契约的强制执行",
        },
        "visual": ["闪电", "裂纹", "碎片", "突然的强光", "分叉的路径"],
        "sound": ["轰鸣", "炸裂", "耳鸣", "之后的寂静", "结构崩塌的共鸣"],
        "touch": ["刺痛", "麻木", "电流感", "震动", "尖锐的边界"],
        "smell": ["臭氧", "燃烧的绝缘体", "金属", "电离的空气"],
        "taste": ["金属味", "尖锐", "酸", "电流的刺痛感"],
        "mood": ["惊醒", "恐惧", "狂喜", "混乱", "觉醒的颤栗"],
        "tempo": ["瞬间", "爆发", "骤停", "断裂的节拍"],
        "geometry": ["垂直", "分叉", "放射状", "碎裂的平面"],
    },
    "深渊": {
        "core": "潜伏于结构底层的未知力量，表面平静下暗涌的不可预测性",
        "variants": {
            "道家": "庄子江湖，相濡以沫不如相忘于江湖，水的流动不盈",
            "存在主义": "萨特的'虚无'，存在的无底深渊，自由的重负",
            "科幻": "深海热泉生态，不依赖阳光的生命，化学合成的奇迹",
            "神话": "北欧赫瓦格密尔泉，世界树下的原始之泉，万物的源头与归宿",
        },
        "visual": ["幽蓝", "不可见底", "缓慢下沉的颗粒", "水面下的阴影", "无光的深谷"],
        "sound": ["水滴回声", "寂静", "低频震动", "暗流", "深海的脉搏"],
        "touch": ["冰冷", "粘稠", "压力", "湿滑的触感", "无底的坠落感"],
        "smell": ["盐与铁", "陈旧", "深海", "潮湿的岩石"],
        "taste": ["涩", "金属感", "咸", "深海的苦"],
        "mood": ["未知", "潜伏", "敬畏", "恐惧", "神秘的吸引"],
        "tempo": ["极慢", "深长呼吸", "暗涌", "不可见的流动"],
        "geometry": ["垂直性", "下坠感", "无边界", "漩涡", "深渊的入口"],
    },
    "渗透": {
        "core": "无形无质却无处不在的渗透力，从缝隙中进入、传播、改变结构",
        "variants": {
            "道家": "风箱，虚而不屈，动而愈出，无形而大用",
            "存在主义": "话语的渗透，福柯的权力微观物理学，无处不在的规训",
            "科幻": "纳米云雾，肉眼不可见的智能尘埃，通过呼吸进入体内",
            "神话": "洛基的变形，不是力量的对抗而是形式的欺骗与渗透",
        },
        "visual": ["微尘", "飘动的窗帘", "水面波纹", "烟雾", "不可见的轨迹"],
        "sound": ["低语", "沙沙声", "风声", "呼吸", "无形的颤动"],
        "touch": ["轻柔", "拂过", "无实体", "凉意", "穿透的触感"],
        "smell": ["远方", "变化", "花香与腐朽混合", "渗透的气息"],
        "taste": ["清淡", "空气", "不可捕捉", "变化的余味"],
        "mood": ["狡黠", "温柔", "不安", "暧昧", "无形的掌控"],
        "tempo": ["持续", "不可预测", "间歇", "渗透的节奏"],
        "geometry": ["网状", "分叉", "渗透", "弥漫", "缝隙的舞蹈"],
    },
    "止界": {
        "core": "明确的边界与停止点，结构的固化与不可逾越的界限",
        "variants": {
            "道家": "知止不殆，止于其所，不动而制动",
            "存在主义": "加缪的'墙'，自由的边界，人必须在限制中创造意义",
            "科幻": "事件视界，黑洞的边界，信息不可逃逸的绝对界限",
            "神话": "世界之山，须弥山，天与地的连接点与分界点",
        },
        "visual": ["断崖", "高墙", "阴影", "不可逾越的线", "绝对的边界"],
        "sound": ["寂静", "回声", "岩石摩擦", "心跳", "停止的钟声"],
        "touch": ["粗糙", "冰冷", "坚硬", "阻力", "不可穿透的厚度"],
        "smell": ["岩石", "苔藓", "冻结", "时间的停滞"],
        "taste": ["苦涩", "矿物质", "干燥", "不可逾越的涩"],
        "mood": ["凝重", "敬畏", "压抑", "决心", "边界前的抉择"],
        "tempo": ["停滞", "沉重", "单点", "永恒的静止"],
        "geometry": ["垂直", "阻挡", "堆积", "顶点", "不可逾越的平面"],
    },
    "显文明": {
        "core": "依附于结构而显化的文明之光，照亮的同时也制造阴影，光明的暂时性",
        "variants": {
            "道家": "凿户牖以为室，当其无，有室之用，光明依赖于黑暗",
            "存在主义": "柏拉图洞穴中的火光，既是解放的媒介也是新的枷锁",
            "科幻": "戴森群，恒星能量的捕获与文明的光辉，依附于恒星的暂时繁荣",
            "神话": "普罗米修斯的火，偷来的光明，既是礼物也是诅咒",
        },
        "visual": ["火焰", "灯笼", "霓虹", "烛光", "阴影", "光明的边缘"],
        "sound": ["噼啪", "燃烧", "低语", "欢呼", "光明的嗡鸣"],
        "touch": ["灼热", "温暖", "刺痛", "干燥", "光的重量"],
        "smell": ["烟", "焦炭", "香", "臭氧", "燃烧的记忆"],
        "taste": ["辣", "苦", "灼烧感", "光明的苦涩"],
        "mood": ["狂热", "虚荣", "渴望", "脆弱", "依附的焦虑"],
        "tempo": ["加速", "燃烧", "骤灭", "短暂的光辉"],
        "geometry": ["向外放射", "依附", "中心发光", "边缘阴影", "脆弱的光锥"],
    },
    "交换": {
        "core": "边界的溶解与交换，两个系统的接口与交易，愉悦源于连接而非拥有",
        "variants": {
            "道家": "上善若水，水善利万物而不争，处众人之所恶，故几于道",
            "存在主义": "马丁·布伯的'我-你'关系，真正的相遇发生在我与你之间",
            "科幻": "星际贸易港，不同文明的接口，翻译器与货币兑换站",
            "神话": "密米尔之泉，奥丁用一只眼睛换取智慧，交易的神圣性",
        },
        "visual": ["水面倒影", "镜子", "交易窗口", "握手", "界面的光芒"],
        "sound": ["笑声", "水声", "硬币", "歌声", "交换的韵律"],
        "touch": ["湿润", "光滑", "清凉", "接触", "连接的触感"],
        "smell": ["酒香", "花香", "潮湿", "混合的气息"],
        "taste": ["甘甜", "果香", "回味", "交换的甜涩"],
        "mood": ["愉悦", "轻松", "诱惑", "虚幻", "连接的喜悦"],
        "tempo": ["流动", "循环", "往复", "交换的节奏"],
        "geometry": ["界面", "反射", "对称", "波浪", "连接的桥梁"],
    },
    "创序": {
        "core": "主动的秩序创造与结构建立，从混沌中强行赋予形式与规则",
        "variants": {
            "道家": "天行健，君子以自强不息，不是强制而是自然的秩序",
            "存在主义": "尼采的'权力意志'，不是统治而是自我超越，创造价值的意志",
            "科幻": "超级AI的第一次自举，从噪声中涌现的语法与逻辑结构",
            "神话": "盘古开天，从混沌中劈出秩序，自身化为天地",
        },
        "visual": ["星空", "几何图案", "蓝图", "冰晶", "秩序的网络"],
        "sound": ["号角", "钟声", "机械律动", "纯音", "秩序的共鸣"],
        "touch": ["冰冷", "精确", "锐利", "光滑", "结构的硬度"],
        "smell": ["臭氧", "金属", "纯净", "新世界的清新"],
        "taste": ["清冽", "无杂味", "结构化", "秩序的纯粹"],
        "mood": ["威严", "孤高", "决断", "纯粹", "创造者的孤独"],
        "tempo": ["加速", "脉冲", "规律", "秩序的节拍"],
        "geometry": ["向上", "放射", "对称", "层级", "秩序的金字塔"],
    },
}


def get_protocol_library(protocol: str) -> dict:
    """获取协议的完整象法语库（含文学变体）"""
    return PROTOCOL_LIBRARY.get(protocol, {
        "core": protocol,
        "variants": {},
        "visual": [], "sound": [], "touch": [],
        "smell": [], "taste": [], "mood": [], "tempo": [], "geometry": [],
    })


def get_sensory_packet(protocol: str, phase: float = 0.5) -> dict:
    """
    根据协议和相位生成感官数据包。
    phase 影响感官的'成熟度'——初爻期偏原始，上爻期偏极端。
    """
    lib = get_protocol_library(protocol)
    import random
    # 确定性选择（避免随机）：用 phase 做索引选择
    def _pick(items, idx):
        if not items:
            return ""
        return items[idx % len(items)]

    i = int(phase * 10) % 5  # phase 0~1 映射到 0~4 的索引
    return {
        "core": lib["core"],
        "variant_dao": _pick(list(lib["variants"].values()), 0) if lib["variants"] else "",
        "visual": _pick(lib["visual"], i),
        "sound": _pick(lib["sound"], i),
        "touch": _pick(lib["touch"], i),
        "smell": _pick(lib["smell"], i),
        "taste": _pick(lib["taste"], i),
        "mood": _pick(lib["mood"], i),
        "tempo": _pick(lib["tempo"], i),
        "geometry": _pick(lib["geometry"], i),
    }
