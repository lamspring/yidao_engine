# -*- coding: utf-8 -*-
"""
《易道引擎》世界底座 — 太初层 (genesis.py)

从无到有：道生一，一生二，二生三，三生万物。

  无（道）  = 未分化的均匀炁场——空不是没有，是未分化的能量。
  第一动    = 种子涨落。绝对均匀的确定性场永远不会自己变，变化需要差别；
              种子就是这个宇宙的奇点，是第一念动。同一个种子，同一个宇宙。
  一生二    = 极化。涨落被非线性放大，炁分化为两种运动倾向：
              阴（收敛、凝聚、沉）与阳（发散、活跃、浮）。
  二生三    = 冲气。阴阳交界处梯度最大，变化最剧烈——界面是诞生之地。
  三生万物  = 凝聚。阴向中心收敛成形，锁住一份阳：地形、太古之水、
              以及诞生于交界的第一批灵。

两条创世路径：
  World.genesis(seed)            无人打扰的自生：从炁场自组织出第一张世界参数图
  World(seed, init_map=分布图)   从你给的阴阳分布图开始（任意尺寸，自动缩放）
  session.seed_at(y, x)          观测者点化：注入一点阳种，阴凝聚成形（见 session.py）
"""

import numpy as np

# 太初常数
QI_NOISE = 0.02      # 种子涨落幅度：第一动微不可见，却决定宇宙
DIFFUSE = 0.25       # 炁扩散率：能量向邻域均流
POLARIZE = 0.03      # 极化率：强者愈强的非线性放大
POLAR_STEPS = 48     # 极化迭代次数（太少不分化，太久则板结）
WATER_LEVEL = 0.62   # 太古之水的水位线：归一化高度低于此则积水


def 炁场极化(size: int, seed: int, steps: int = POLAR_STEPS) -> np.ndarray:
    """道生一，一生二：均匀炁场 + 种子涨落，经扩散与非线性放大，分化为阴阳场。
    返回归一化之前的炁场 Q：高处为阴聚成形之所，低处为阳散虚空之地。"""
    rng = np.random.default_rng(seed ^ 0x4F1B)   # 太初有自己的随机流，不扰世界线
    Q = np.ones((size, size)) + rng.normal(0.0, QI_NOISE, (size, size))
    for _ in range(steps):
        blur = (np.roll(Q, 1, 0) + np.roll(Q, -1, 0)
                + np.roll(Q, 1, 1) + np.roll(Q, -1, 1)) / 4.0
        Q = Q + (blur - Q) * DIFFUSE                       # 扩散：炁向邻域均流
        Q = Q * (1.0 + POLARIZE * np.tanh((Q - Q.mean()) * 3.0))  # 极化：强者愈强
    return Q


def 凝聚成形(Q: np.ndarray, rng: np.random.Generator):
    """二生三，三生万物：阴阳场凝聚为地形与太古之水。
    返回 (height, water, cloud)。"""
    q = (Q - Q.min()) / max(Q.max() - Q.min(), 1e-9)
    q = q ** 1.4                            # 拉开落差：洼者愈凹，高者愈凸
    height = q * 9.0
    # 太古之水：阳散低处即为泽，处处尚存一点水气。无此则无蒸发、无云、无雨
    water = np.clip((WATER_LEVEL - q) * 3.0, 0.0, None) + rng.uniform(0.05, 0.2, Q.shape)
    cloud = 0.4 + rng.random(Q.shape) * 0.5
    return height, water, cloud


def 从分布图(init_map, size: int):
    """以用户所给的阴阳分布图为炁场，凝聚成形。任意尺寸的图自动块状缩放。"""
    M = np.asarray(init_map, dtype=np.float64)
    if M.ndim != 2 or 0 in M.shape:
        raise ValueError("init_map 须为二维阴阳分布图")
    fy = int(np.ceil(size / M.shape[0]))
    fx = int(np.ceil(size / M.shape[1]))
    Q = np.kron(M, np.ones((fy, fx)))[:size, :size]
    rng = np.random.default_rng(int(Q.sum() * 1000) ^ 0x77AA)
    return 凝聚成形(Q, rng)


def 界面点(height: np.ndarray, water: np.ndarray, limit: int = 64) -> list:
    """万物生于交界：梯度最大、非深水、且六格内有水可饮的格子，按梯度降序。"""
    gy = np.roll(height, -1, 0) - height
    gx = np.roll(height, -1, 1) - height
    grad = np.hypot(gy, gx)
    grad[water >= 1.8] = 0.0    # 深水不聚形
    # 逐水而居：六格内无活水之处，灵不生于斯
    邻水 = np.zeros_like(grad, dtype=bool)
    有水 = water >= 0.4
    for dy in range(-6, 7):
        for dx in range(-6, 7):
            邻水 |= np.roll(np.roll(有水, dy, 0), dx, 1)
    grad[~邻水] = 0.0
    n = height.shape[0]
    cells = [(float(grad[y, x]), y, x) for y in range(n) for x in range(n)]
    cells.sort(reverse=True)
    return [(y, x) for g, y, x in cells if g > 1e-6][:limit]
