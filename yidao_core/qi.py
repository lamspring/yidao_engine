# -*- coding: utf-8 -*-
"""
《易道引擎》世界底座 — 炁场层 (qi.py)

宇宙底座第一律（见 docs/engine-v6-lingti.md 附录《宇宙底座第一律》）：
  宇宙是一只封闭盒子，能量总量永恒不变；场即能量，无处不在。
  阳逸散是连续的就地归还（洒水壶：走到哪撒到哪）；
  阴的归还是一次性崩塌（倾覆：阴尽数回归环境）。
  总量守恒，唯越界可破；越界必留痕。

本模块是这条定律的最小落地（M1）：

  炁场        —— 常驻的能量场，阴与阳两库，处处皆满；归还与抽取皆就地。
  账本        —— 四笔流水：泵（日月泵经生物质入链）、草汲（炁→草，逸散即播种）、
                  越界A（水文域的越界出入）、越界B（能量域的越界出入）。
  守恒结算    —— 出流按格封顶：承诺总量超过存量则按比例压缩（水流复制的修复机制）。

守恒域（M1 划定）：
  A 域（水文）：water + cloud + 九泉。断言 ΔA = 越界A（云散排气、天道注云、汲井出口）。
  B 域（能量）：炁场 + Σ灵阳 + Σ兽阳。断言 ΔB = 泵 − 草汲 + 越界B。
  C 域（生物质与器物：草木鱼虫、物品、屋火井栏）：泵的领地，M1 暂不断言（备注后续）。
"""

import numpy as np

QI0 = 80.0              # 太初存量：创世时每格炁之初值（阴阳各半）
FORM_YIN = 30.0         # 灵的形阴：凝聚成形时自炁场抽取，坏灭时尽数归还
BEAST_FORM_YIN = {"鸡": 8.0, "羊": 15.0, "牛": 25.0}   # 走兽形阴
QI_GRASS_DRINK = 0.02   # 草每念汲炁上限：逸散即播种，场养草木


class 炁场:
    """常驻能量场：阴与阳两库，处处皆满。

    哲学：场不是容器，场就是能量本身。归还不是"存进"，是当场能量姿态的改变；
    抽取不是"取出"，是阴向之收敛凝聚。两库皆不得为负——能量只有多少，没有亏欠。
    """

    def __init__(self, size: int, 太初存量: float = QI0):
        self.yin = np.full((size, size), 太初存量 / 2.0)
        self.yang = np.full((size, size), 太初存量 / 2.0)

    # ── 归还：阳如洒水壶沿途撒，阴如倾覆一次还 ──

    def 归还(self, y: int, x: int, 阳: float = 0.0, 阴: float = 0.0):
        if 阳 > 0.0:
            self.yang[y, x] += 阳
        if 阴 > 0.0:
            self.yin[y, x] += 阴

    # ── 抽取：凝聚成形，阴向之收敛 ──

    def 抽取(self, y: int, x: int, 阳: float = 0.0, 阴: float = 0.0) -> tuple[float, float]:
        """就地先取，不足则全场均摊（阴向之收敛凝聚：远处的炁向成形之处汇聚）。
        返回 (实抽阳, 实抽阴)；场不足时短少，差额由调用方记越界账。"""
        return self._取(self.yang, y, x, 阳), self._取(self.yin, y, x, 阴)

    @staticmethod
    def _取(pool: np.ndarray, y: int, x: int, 量: float) -> float:
        if 量 <= 0.0:
            return 0.0
        本地 = float(pool[y, x])
        if 本地 >= 量:
            pool[y, x] -= 量
            return 量
        pool[y, x] = 0.0
        缺 = 量 - 本地
        总 = float(pool.sum())
        if 总 <= 1e-9:
            return 本地
        摊 = min(1.0, 缺 / 总)
        pool *= (1.0 - 摊)            # 全场每格按比例出一点，向此处收敛
        return 本地 + min(缺, 总)

    def 总量(self) -> float:
        return float(self.yin.sum() + self.yang.sum())


class 账:
    """守恒账本：流水笔笔有出处。

      泵      日月之泵经生物质直入身体之量（采食野草、兽食草虫——太阳能的入网口）
      源C     生物质与太古遗泽入万物之链之量（采集、伐木、渔获、屠宰、收蛋挤奶）
      食转    食物之结解开、其阳转入身体之量（C 域 → B 域：食其阳）
      物归    万物逸散、腐坏、塌毁、归土归还炁场之量（C 域 → B 域：还其形）
              可为负——负者，炁场补入万物之量（凿井、营建之不足，阴向之凝聚）
      草汲    炁场养草之量（逸散即播种：B 域 → 生物质）
      越界A   水文域的越界出入（正入负出：天道注云为正，云散排气为负）
      越界B   能量域的越界出入（点化/凝聚时炁不足之补差、天道修复）
      越界C   器物域的越界出入（凝聚万物而炁场全域不足之补差，殆不曾见）

    三域恒等式：
      ΔA = 越界A
      ΔB = 泵 − 草汲 + 物归 + 食转 + 越界B
      ΔC = 源C − 物归 − 食转 + 越界C
    """

    def __init__(self):
        self.泵 = 0.0
        self.源C = 0.0
        self.食转 = 0.0
        self.物归 = 0.0
        self.草汲 = 0.0
        self.越界A = 0.0
        self.越界B = 0.0
        self.越界C = 0.0

    def 归零(self):
        self.泵 = self.源C = self.食转 = self.物归 = self.草汲 = 0.0
        self.越界A = self.越界B = self.越界C = 0.0


def 封顶结算(pool: np.ndarray, flows: list) -> np.ndarray:
    """守恒结算器：出流按格封顶。

    flows: [(sy, sx, ty, tx, f)] —— 每格向邻格承诺的出流（快照式）。
    若一格的承诺总出流超过其存量，则各方向按比例压缩——承诺不得超过实有，
    这是"阴凝聚只是抽走周围的阴"的结算面表达：抽走的量绝不超过实有的量。
    返回 delta（与 pool 同形），结算后 pool + delta 处处非负且总量严格不变。
    """
    out = np.zeros_like(pool)
    for sy, sx, ty, tx, f in flows:
        out[sy, sx] += f
    scale = np.minimum(1.0, pool / np.maximum(out, 1e-12))
    delta = np.zeros_like(pool)
    for sy, sx, ty, tx, f in flows:
        f = f * scale[sy, sx]
        delta[sy, sx] -= f
        delta[ty, tx] += f
    return delta
