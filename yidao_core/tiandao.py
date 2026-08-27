# -*- coding: utf-8 -*-
"""
《易道引擎》世界底座 — 天道层 (tiandao.py)

天道协议 v2（作者亲定，见 docs/engine-v6-lingti.md §五之修订）：

  天道守的是"道"，不是"众生"。

  世界可以毁灭，众生可以灭绝——只要炁场没有归于"古井无波"的死寂均匀，
  就基本不需要天道出手。灭绝不是系统的失败，是变化的一部分；
  只要能量场还在运动，毁灭了的世界自会有下一次凝聚。

  天道唯二介入：
    1. 数值异常（NaN / Inf / 越界）——法则将紊，抚平即走；
    2. 炁场死寂——能量场趋近无差别之"无"，则再动一念，如太初之第一动。

  天道不读心改心：绝不修改角色的记忆与欲望；灵体层只抚平数值病态。
  每次介入留痕：【天道】…（因：…）
"""

try:
    from .world import World, TICKS_PER_DAY
except ImportError:  # 允许脚本方式直跑
    from world import World, TICKS_PER_DAY

# 死寂判据
STAGNANT_EPS = 0.05                 # 场活跃度低于此值视为趋寂
STAGNANT_TICKS = 2 * TICKS_PER_DAY  # 且须持续两整日（确认不是暂歇）


class Tiandao:
    """天道：守道不救生。变化的维修工，众生的旁观者。"""

    def __init__(self, world: World, report):
        self.world = world
        self.report = report
        self._still = 0     # 炁场趋寂的连续念数

    def 活跃度(self) -> float:
        """炁场的活跃程度：场之差即变化之源。水云草诸场皆平，即是死寂。
        风不计入：无云无水，空风流转不生物事，算不上变化。"""
        w = self.world
        return float(w.water.std() + w.cloud.std() + w.grass.std() + w.moisture.std())

    def check(self, tick: int, spirits: list):
        """每念监测。绝大部分时候，天道沉默。"""
        w = self.world

        # 一、数值异常：法则将紊，抚平即走（世界层与灵体层皆在监护之内）
        sane = w.numbers_sane()
        for s in spirits:
            vals = [s.yang, s.水分, s.strength, s.pressure, *s.mood.values()]
            if any(v != v or abs(v) == float("inf") for v in vals):
                sane = False
                s.yang = 0.0      # 数值病入膏肓者，阳尽而终（不治其心，只了其形）
        if not sane:
            w.heal_numbers()
            self.report(tick, None,
                        "【天道】抚平数值异常（因：NaN/Inf 现世，法则将紊）",
                        kind="天道")
            return

        # 二、炁场死寂：唯一的"救世"——但救的不是世，是变化本身
        if self.活跃度() < STAGNANT_EPS:
            self._still += 1
        else:
            self._still = 0
        if self._still >= STAGNANT_TICKS:
            self._still = 0
            self.stir()
            self.report(tick, None,
                        "【天道】炁场将归死寂，道再动一念（因：能量趋于无差别，变化将熄）",
                        kind="天道")

        # 此外无事。草尽、屋塌、族灭、灵绝——皆不出手。
        # 众生自有生死，世界自有代谢。道在，一切自会再来。

    def stir(self):
        """再动一念：向炁场注入一缕涨落（用世界自身的随机流，确定性不破）。
        此乃越界注入——宇宙总量唯越界可破，越界必留痕：记越界账。"""
        w = self.world
        n = w.size
        注 = w._rng.uniform(0.0, 0.3, (n, n))
        w.cloud += 注
        w.账.越界A += float(注.sum())
        w.wind_speed = float(w._rng.uniform(0.1, 0.4))
