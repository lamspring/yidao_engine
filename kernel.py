# -*- coding: utf-8 -*-
"""
《易道动态世界引擎》v4.0 — 核心引擎 (YDWEVirtualMachine)
严格基于：
  - 周易六爻生命周期（初爻→上爻→反转）
  - 先天八卦二进制编码（阴=0, 阳=1, 初爻=LSB）
  - 道德经"反者道之动"（长期稳定积累反向势能）
  - 五行生克交感场论（替代XOR的真正卦交变）

架构公理：
  世界 = 阴阳流动形成的暂时稳定结构
  爻  = 趋势（非静态状态，而是变化方向）
  八卦 = 八种行为协议（非元素属性）
  六爻 = 任何局部结构的强制生命周期
"""

import numpy as np
from typing import Tuple

# ───────────────────────────────────────────
# 0. 先天常量：八卦协议与五行交感
# ───────────────────────────────────────────

# 八卦索引: 0坤 1震 2坎 3巽 4艮 5离 6兑 7乾
TRIGRAM_NAMES = ["坤", "震", "坎", "巽", "艮", "离", "兑", "乾"]

# 八卦本征阴阳驱动力（气象方向与强度）
# 正 = 阳化（扩张/分化/显化/加速），负 = 阴化（融合/内敛/沉淀/减速）
TRIGRAM_DRIVE = np.array([
    -0.80,  # 坤 ☷ 承载融合（强烈阴化）
    +0.60,  # 震 ☳ 爆发惊醒（阳化裂变）
    -0.50,  # 坎 ☵ 深渊内敛（阴化陷落）
    -0.20,  # 巽 ☴ 渗透扩散（阴化风化）
    +0.00,  # 艮 ☶ 止界封印（阻断气象流动，静止）
    +0.50,  # 离 ☲ 显文明化（阳化外显）
    +0.30,  # 兑 ☱ 交换契约（阳化差异制造）
    +0.80,  # 乾 ☰ 创序扩张（强烈阳化）
], dtype=np.float32)

# ───────────────────────────────────────────
# 五行共振矩阵（8×8）
# ───────────────────────────────────────────
# 八卦五行归属：坤艮=土，震巽=木，坎=水，离=火，兑乾=金
RESONANCE = np.zeros((8, 8), dtype=np.float32)

# 同卦共振
for i in range(8):
    RESONANCE[i, i] = 0.50

# 先天通气 — 对宫互补（雷风相薄，山泽通气）
RESONANCE[1, 3] = RESONANCE[3, 1] = 0.55  # 震↔巽
RESONANCE[4, 6] = RESONANCE[6, 4] = 0.55  # 艮↔兑

# 天地定位、水火不相射 — 先天极性对冲
RESONANCE[0, 7] = RESONANCE[7, 0] = -0.80  # 乾↔坤
RESONANCE[2, 5] = RESONANCE[5, 2] = -0.80  # 坎↔离

# 五行相生（被生者受益，生者略泄）
SHENG = [
    (1, 5), (3, 5),   # 木(震/巽) → 火(离)
    (5, 0), (5, 4),   # 火(离) → 土(坤/艮)
    (0, 6), (0, 7), (4, 6), (4, 7),  # 土(坤/艮) → 金(兑/乾)
    (6, 2), (7, 2),   # 金(兑/乾) → 水(坎)
    (2, 1), (2, 3),   # 水(坎) → 木(震/巽)
]
for a, b in SHENG:  # a 生 b
    if RESONANCE[a, b] == 0:
        RESONANCE[a, b] = 0.10   # 生者泄气
    if RESONANCE[b, a] == 0:
        RESONANCE[b, a] = 0.25   # 被生者受益

# 五行相克（被克者强负，克者自损）
KE = [
    (1, 0), (1, 4), (3, 0), (3, 4),  # 木(震/巽) 克 土(坤/艮)
    (0, 2), (4, 2),                  # 土(坤/艮) 克 水(坎)
    (2, 5),                           # 水(坎) 克 火(离)
    (5, 6), (5, 7),                  # 火(离) 克 金(兑/乾)
    (6, 1), (6, 3), (7, 1), (7, 3),  # 金(兑/乾) 克 木(震/巽)
]
for a, b in KE:  # a 克 b
    if RESONANCE[b, a] == 0:
        RESONANCE[b, a] = -0.40   # b 被克，强烈受损
    if RESONANCE[a, b] == 0:
        RESONANCE[a, b] = -0.10   # a 克人，自身消耗


# ───────────────────────────────────────────
# 1. 卦变函数（四种基本变换指令）
# ───────────────────────────────────────────

def cuo_gua(S):
    """错卦：六爻全变（最剧烈的反向/全面否定）"""
    return np.bitwise_xor(S, 0b111111)

def zong_gua(S):
    """综卦：上下颠倒（结构翻转/视角换位）"""
    lower = np.bitwise_and(S, 0b111)
    upper = np.right_shift(S, 3)
    return np.bitwise_or(np.left_shift(lower, 3), upper)

def hugua_scalar(S: int) -> int:
    """互卦：取2345爻（内部矛盾显性化）"""
    y0 = (S >> 1) & 1
    y1 = (S >> 2) & 1
    y2 = (S >> 3) & 1
    y3 = (S >> 2) & 1
    y4 = (S >> 3) & 1
    y5 = (S >> 4) & 1
    return y0 | (y1 << 1) | (y2 << 2) | (y3 << 3) | (y4 << 4) | (y5 << 5)

def yao_bian_scalar(S: int, pos: int) -> int:
    """单爻变：变动指定爻位（0=初爻, ..., 5=上爻）"""
    return S ^ (1 << pos)

def split_trigrams(S: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """向量化分离六爻卦的上下卦"""
    lower = np.bitwise_and(S, 0b111)
    upper = np.right_shift(S, 3)
    return upper, lower

# 阳爻数查表（256字节，极快）
_YANG_LUT = np.array([bin(i).count('1') for i in range(256)], dtype=np.uint8)

def yang_count(S: np.ndarray) -> np.ndarray:
    """向量化统计阳爻数（0~6）"""
    return _YANG_LUT[S.astype(np.uint8)]


# ───────────────────────────────────────────
# 2. 世界核心类
# ───────────────────────────────────────────

class World:
    """
    易道动态世界引擎核心。

    场构成：
      gua         : 卦象场 (H, W) uint8，值域 0-63
      trend       : 气象场 (Qi Flow Field) (H, W) float32，-1~+1
                    负 = 阴化（融合/内敛/沉淀），正 = 阳化（扩张/分化/显化）
                    不是被动算出的"趋势指标"，而是真实流动、有惯性的"气"
      phase       : 六爻生命周期场 (H, W) float32，0~1
                    0.0=初爻萌芽 → 0.17=二爻稳定 → 0.33=三爻过界
                    → 0.50=四爻碰撞 → 0.67=五爻主导 → 0.83=上爻极化 → 1.0=反转
      potential   : 反向势能场 (H, W) float32，>=0
                    长期稳定区域积累的"即将反转"势能
      stable_age  : 连续稳定计数 (H, W) uint16
                    记录该位置卦象未变的息数

    演化总公式：
      气象流动 → 局部稳定 → 八卦协议激活 → 六爻推进 → 势能积累 → 穷极则变 → 新结构
    """

    def __init__(self, height: int = 32, width: int = 64):
        self.H = height
        self.W = width

        # 核心五场
        self.gua = np.zeros((height, width), dtype=np.uint8)
        self.trend = np.zeros((height, width), dtype=np.float32)
        self.phase = np.zeros((height, width), dtype=np.float32)
        self.potential = np.zeros((height, width), dtype=np.float32)
        self.stable_age = np.zeros((height, width), dtype=np.uint16)

        # 下一帧缓冲（避免原地修改）
        self._buf_gua = np.zeros_like(self.gua)
        self._buf_trend = np.zeros_like(self.trend)
        self._buf_phase = np.zeros_like(self.phase)
        self._buf_potential = np.zeros_like(self.potential)

        # 时序
        self.tick_count = 0
        self.history = []          # 最近若干帧卦场快照（供涌现解释）
        self.HISTORY_MAX = 24

        # 道控制器参数
        self.V_thresh = 1.2        # 势能释放阈值（动态调节），含观察保护期设计
        self.gamma = 0.018         # 六爻生命周期推进速度
        self.alpha = 0.72          # 趋势惯性系数（越高越难突变）
        self.dao_bias = 0.0        # 全局阴阳调谐偏置（损有余补不足）
        self.dao_check_interval = 10

        # 确定性初始化
        self._init_field()

    def _init_field(self):
        """
        确定性初始化：禁止随机数。
        无极(全坤) → 太极(中心乾种) → 两仪(乾坤对立) → 四象(坎离震艮分形)
        """
        H, W = self.H, self.W
        self.gua.fill(0)          # 全坤 = 无极
        self.trend.fill(0.0)
        self.phase.fill(0.0)
        self.potential.fill(0.0)
        self.stable_age.fill(0)

        cy, cx = H // 2, W // 2

        # 太极：中心乾（纯阳种子）— 道生一
        self._set_seed(cy, cx, 63)
        # 两仪：乾之对位坤已存在（全坤场）— 一生二

        # 四象：四隅播种四种极性 — 二生四
        qy, qx = H // 4, W // 4
        self._set_seed(qy, qx, 18)            # 坎（水，阴中之阳）
        self._set_seed(qy, cx + qx, 45)       # 离（火，阳中之阴）
        self._set_seed(cy + qy, qx, 9)        # 震（雷，阳动）
        self._set_seed(cy + qy, cx + qx, 36)  # 艮（山，止界）

        # 八卦：八边缘中点播种八纯卦 — 四生八
        self._set_seed(0, cx, 27)       # 巽（风，顶部渗透）
        self._set_seed(H - 1, cx, 54)   # 兑（泽，底部交换）
        self._set_seed(cy, 0, 0)        # 坤（左边界）
        self._set_seed(cy, W - 1, 63)   # 乾（右边界）

        # 初始趋势场：从种子向外扩散的微弱波纹
        yy, xx = np.mgrid[0:H, 0:W]
        dy, dx = yy - cy, xx - cx
        dist = np.sqrt(dy * dy + dx * dx) + 1.0
        # 更强的空间异质性：不同象限有不同初始相位
        self.trend = (
            0.08 * np.sin(dy / 2.5) * np.cos(dx / 3.5) /
            (dist * 0.06 + 1)
            + 0.04 * np.sin((dx + dy) / 4.0)
        )
        self.trend = np.clip(self.trend, -0.35, 0.35)

        self._record_history()

    def _set_seed(self, y: int, x: int, gua_val: int):
        """确定性播种：重置该位置的卦与生命周期"""
        y, x = y % self.H, x % self.W
        self.gua[y, x] = int(gua_val) & 0b111111
        self.phase[y, x] = 0.0
        self.potential[y, x] = 0.0
        self.stable_age[y, x] = 0

    def set_seed(self, y: int, x: int, gua_val: int):
        """外部接口：播种"""
        self._set_seed(y, x, gua_val)

    def _record_history(self):
        self.history.append(self.gua.copy())
        if len(self.history) > self.HISTORY_MAX:
            self.history.pop(0)

    # ───────────────────────────────────────────
    # 核心演算：一息之内
    # ───────────────────────────────────────────

    def _compute_neighbor_resonance(self) -> np.ndarray:
        """
        外感：3×3 邻域五行交感共振。
        替代旧版 XOR，实现真正的卦交变。
        """
        H, W = self.H, self.W
        upper, lower = split_trigrams(self.gua)
        effect = np.zeros((H, W), dtype=np.float32)

        # 邻域权重（中心弱，四周强，体现"外感"而非"自闭"）
        shifts = [
            (-1, -1, 0.06), (-1, 0, 0.14), (-1, 1, 0.06),
            ( 0, -1, 0.14), ( 0, 0, 0.20), ( 0, 1, 0.14),
            ( 1, -1, 0.06), ( 1, 0, 0.14), ( 1, 1, 0.06),
        ]

        for dy, dx, w in shifts:
            # 环形边界
            ny_u = np.roll(np.roll(upper, dy, axis=0), dx, axis=1)
            ny_l = np.roll(np.roll(lower, dy, axis=0), dx, axis=1)
            # 查共振矩阵（向量化）
            res_u = RESONANCE[upper, ny_u]
            res_l = RESONANCE[lower, ny_l]
            effect += w * (res_u + res_l) * 0.5

        return effect

    def _compute_protocol_drive(self) -> np.ndarray:
        """
        内化：八卦协议本征驱动力。
        每个格点根据其上下卦产生阴阳气象倾向。
        """
        upper, lower = split_trigrams(self.gua)
        drive = (TRIGRAM_DRIVE[upper] + TRIGRAM_DRIVE[lower]) * 0.5

        # 阴阳比例调制：纯卦驱动力最强，均衡卦衰减（冲气为和）
        yc = yang_count(self.gua)
        modulation = 1.0 - 0.30 * np.abs(yc.astype(np.float32) - 3.0) / 3.0
        modulation = np.clip(modulation, 0.45, 1.0)

        return drive * modulation

    def _accumulate_potential(self, new_trend: np.ndarray) -> np.ndarray:
        """
        反向势能积累（含观察保护期与老年加速）。

        四阶段韵律：
          婴儿期（stable_age < 10）：保护极强，几乎不积累
          成长期（10~40）：S 曲线平滑过渡
          成熟期（40~80）：正常积累
          老年期（> 80）：额外加速，确保老而不死必有一爆
        """
        # 1. 基础积累：气象越平静，积累越快
        base = 0.030 * np.exp(-2.8 * np.abs(new_trend))

        # 2. 观察保护期：S 曲线调制（sigmoid，中心 25 息）
        age = self.stable_age.astype(np.float32)
        protection = 1.0 / (1.0 + np.exp(-0.15 * (age - 25)))

        # 3. 老年加速：stable_age > 80 时额外加速
        senescence = 0.025 * (age > 80).astype(np.float32)

        pot = self.potential + base * protection + senescence
        return np.clip(pot, 0.0, 2.5)

    def _resolve_transformations(self, new_trend: np.ndarray, new_phase: np.ndarray, new_potential: np.ndarray):
        """
        穷极则变 + 上爻反转。
        """
        gua_out = self.gua.copy()
        trend_out = new_trend.copy()
        phase_out = new_phase.copy()
        pot_out = new_potential.copy()
        stable_out = self.stable_age.copy()

        # 条件1: 上爻反转（phase >= 1.0，生命周期终结，必须全面反向）
        rebirth = new_phase >= 1.0
        if np.any(rebirth):
            gua_out[rebirth] = cuo_gua(self.gua[rebirth])
            phase_out[rebirth] = 0.0
            pot_out[rebirth] = 0.0
            trend_out[rebirth] = -new_trend[rebirth] * 0.25
            stable_out[rebirth] = 0

        # 条件2: 势能释放（potential > V_thresh，结构内在矛盾爆发）
        flip = (~rebirth) & (new_potential > self.V_thresh)
        if np.any(flip):
            idx_y, idx_x = np.where(flip)
            for y, x in zip(idx_y, idx_x):
                S = int(gua_out[y, x])
                ph = float(phase_out[y, x])

                if ph < 0.30:
                    # 初爻/二爻：内部矛盾显性化 → 互卦
                    gua_out[y, x] = hugua_scalar(S)
                elif ph < 0.60:
                    # 三爻/四爻：结构翻转 → 综卦
                    gua_out[y, x] = zong_gua(np.array([S], dtype=np.uint8))[0]
                else:
                    # 五爻/上爻前夕：当前主导爻位发生变动
                    pos = min(5, int(ph * 6))
                    gua_out[y, x] = yao_bian_scalar(S, pos)

                pot_out[y, x] = 0.0
                # 释放势能会强化当前气象方向（突变加速）
                t = float(trend_out[y, x])
                trend_out[y, x] = np.clip(t + np.sign(t) * 0.30, -1.0, 1.0)
                stable_out[y, x] = 0

        return gua_out, trend_out, phase_out, pot_out, stable_out

    def _dao_adjust(self):
        """
        道控制器：无为而治。
        只调节全局环境参数 V_thresh 与 dao_bias，不直接改写格点。
        """
        mean_energy = float(np.mean(np.abs(self.trend)))
        yc = yang_count(self.gua)
        yang_ratio = float(np.mean(yc)) / 6.0

        # 僵化：系统过于平静，降低阈值惊醒
        if mean_energy < 0.10:
            self.V_thresh = max(0.80, self.V_thresh * 0.88)
            # 在最死寂且势能最高的点给予"道生震"的扰动
            dead = np.abs(self.trend) < 0.02
            if np.any(dead):
                dy, dx = np.where(dead)
                pots = self.potential[dead]
                if pots.size > 0:
                    pick = int(np.argmax(pots))
                    self.trend[dy[pick], dx[pick]] = 0.5
                    self.potential[dy[pick], dx[pick]] = 0.0

        # 过热：系统过于混沌，提高阈值让结构有机会暂时稳定
        elif mean_energy > 0.55:
            self.V_thresh = min(2.0, self.V_thresh * 1.12)

        # 损有余而补不足：阳盛抑阳，阴盛扶阳
        if yang_ratio > 0.72:
            self.dao_bias = -0.025
        elif yang_ratio < 0.28:
            self.dao_bias = +0.025
        else:
            self.dao_bias *= 0.85
            if abs(self.dao_bias) < 0.002:
                self.dao_bias = 0.0

    def tick(self):
        """世界推进一息。核心演算循环。"""
        # Step 1: 外感（邻居五行交感）
        neighbor_res = self._compute_neighbor_resonance()

        # Step 2: 内化（八卦协议本征驱动）
        protocol_drive = self._compute_protocol_drive()

        # Step 3: 气象演化（冲气流动，阴阳交感）
        # trend = 惯性*旧气象 + 扩散*外感 + 协议*内化 + 道偏置
        new_trend = (
            self.alpha * self.trend +
            (1.0 - self.alpha) * neighbor_res +
            0.14 * protocol_drive +
            self.dao_bias
        )
        new_trend = np.clip(new_trend, -1.0, 1.0)

        # Step 4: 六爻生命周期推进
        # |trend|（气象强度）越大推进越快；potential 越高推进越快
        # 反转后冷却期：stable_age < 10 时推进减半（给新结构稳定时间）
        cooldown = np.clip(1.0 - 0.4 * (self.stable_age < 10).astype(np.float32), 0.6, 1.0)
        new_phase = self.phase + self.gamma * np.abs(new_trend) * (1.0 + 0.20 * self.potential) * cooldown

        # Step 5: 反向势能积累
        new_potential = self._accumulate_potential(new_trend)

        # Step 6: 穷极则变（卦变解析）
        gua_out, trend_out, phase_out, pot_out, stable_out = \
            self._resolve_transformations(new_trend, new_phase, new_potential)

        # Step 7: 稳定计数更新
        changed = (gua_out != self.gua)
        stable_out = np.where(changed, np.uint16(0), stable_out + np.uint16(1))

        # 写回
        self.gua = gua_out
        self.trend = trend_out
        self.phase = np.clip(phase_out, 0.0, 2.0)  # 允许略微超过1.0，在下一轮处理
        self.potential = pot_out
        self.stable_age = stable_out

        self.tick_count += 1
        self._record_history()

        # Step 8: 道控制器（周期性）
        if self.tick_count % self.dao_check_interval == 0:
            self._dao_adjust()

    # ───────────────────────────────────────────
    # 观测接口（供上层AI纯读取，禁止写入）
    # ───────────────────────────────────────────

    def get_snapshot(self) -> dict:
        """获取当前世界完整快照"""
        return {
            "gua": self.gua.copy(),
            "trend": self.trend.copy(),
            "phase": self.phase.copy(),
            "potential": self.potential.copy(),
            "stable_age": self.stable_age.copy(),
            "tick": self.tick_count,
            "V_thresh": self.V_thresh,
            "dao_bias": self.dao_bias,
            "history": [h.copy() for h in self.history[-12:]],
        }

    def get_region_stats(self, y0: int, x0: int, h: int, w: int) -> dict:
        """获取局部区域的统计特征"""
        y0 = max(0, y0)
        x0 = max(0, x0)
        y1 = min(self.H, y0 + h)
        x1 = min(self.W, x0 + w)
        if y1 <= y0 or x1 <= x0:
            return {"error": "invalid region"}
        region_gua = self.gua[y0:y1, x0:x1]
        region_trend = self.trend[y0:y1, x0:x1]
        region_phase = self.phase[y0:y1, x0:x1]
        region_pot = self.potential[y0:y1, x0:x1]

        return {
            "size": int((y1 - y0) * (x1 - x0)),
            "mean_trend": float(np.mean(region_trend)),
            "mean_phase": float(np.mean(region_phase)),
            "mean_potential": float(np.mean(region_pot)),
            "yang_ratio": float(np.mean(yang_count(region_gua))) / 6.0,
            "dominant_gua": int(np.bincount(region_gua.flatten()).argmax()),
        }
