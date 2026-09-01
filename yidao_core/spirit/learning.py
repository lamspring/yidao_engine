"""灵体层 · 学习系统（M2 组件化拆分：自 spirit.py 整段搬运，行为不变）"""

from .base import *

class 学习Mixin:
    """灵之学习诸行。"""
    def _涨熟练(self, 技能: str):
        # 禀赋加成：该域 DNA 禀赋给熟练增速 20% 加成
        禀赋 = self.dna.get(SKILL_DOMAIN.get(技能, ""), 0.5)
        self.skills[技能] = min(1.0, self.skills.get(技能, 0.0)
                                + SKILL_GAIN * (1.0 + 0.2 * 禀赋))

    def _熟练(self, 技能: str) -> float:
        return self.skills.get(技能, 0.0)

    def _积学(self, 技能: str, 量: float, tick: int, report, 文: str, 因: str) -> bool:
        """真学习（v6.5）：经验积累取代掷骰顿悟。试错、观察、受挫都在攒经验，
        顿悟只是临门一脚。已会者不再积；增速受悟性与该域 DNA 禀赋修饰；
        经验过 LEARN_GATE 则豁然贯通（领悟事件注明积学几日）。返回是否贯通。"""
        if 技能 in self.knowledge:
            return False
        if 技能 not in self._学始:
            self._学始[技能] = tick
        禀赋 = self.dna.get(SKILL_DOMAIN.get(技能, ""), 0.5)
        self._学习[技能] = self._学习.get(技能, 0.0) \
            + 量 * (0.6 + 0.5 * self.悟性) * (0.55 + 0.9 * 禀赋)
        if self._学习[技能] < LEARN_GATE[技能]:
            return False
        self.knowledge.add(技能)
        历时 = max(1, round((tick - self._学始.pop(技能)) / TICKS_PER_DAY))
        self._学习.pop(技能, None)
        report(tick, (self.y, self.x),
               f"{self.name} {文}（因：{因}·积学{历时}日乃悟）",
               kind="领悟", actor=self.name)
        return True


    # ── 人情三事：借贷、还债、馈赠、交易 ──────

    def _摸器悟法(self, it, tick: int, report, rng):
        """摸到他人所制之器而积其法：陶罐启制陶，衣饰启缝纫——模仿不止于看，也在于摸。"""
        if it.类型 == "陶罐":
            self._积学("制陶", 12.0, tick, report,
                       "摩挲陶罐良久，悟得其烧制之法", "观察模仿+触物生情")
        elif it.类型 in ("寒衣", "骨饰"):
            self._积学("缝纫", 12.0, tick, report,
                       f"细看{it.类型}的针脚，悟得缝纫之法", "观察模仿+触物生情")
