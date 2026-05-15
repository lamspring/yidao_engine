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
