"""灵体层 · 婚育系统（M2 组件化拆分：自 spirit.py 整段搬运，行为不变）"""

from .base import *

Spirit = None  # 诞育自指，包组装后注入真身

class 婚育Mixin:
    """灵之婚育诸行。"""

    # ── 婚育：结侣与诞育（v6.2）──────────────

    def _婚配(self, world: World, spirits: list, tick: int, report, rng) -> bool:
        """男婚女嫁：相邻、两情相悦、有檐可依、温饱 → 结为伴侣。（生养是夜半私事，见 decide 夜分支）"""
        if self.伴侣 is not None:
            p = next((s for s in spirits if s.alive and s.name == self.伴侣), None)
            if p is None:
                self.伴侣 = None   # 鳏寡之人，可再续弦
            else:
                return False
        for b in self._邻居们(spirits):
            if not b._已成年 or b.伴侣 is not None:
                continue
            if self.relation(b.name) < MATE_REL or b.relation(self.name) < MATE_REL:
                continue
            if self.yang < 55.0 or b.yang < 55.0:
                continue
            if self.hut is None and b.hut is None:
                continue    # 无片瓦者，何以家为
            if rng.random() > MATE_CHANCE:
                continue
            self.伴侣 = b.name
            b.伴侣 = self.name
            # 定下共同的家门：两口子同住一檐下
            家屋 = self.hut or b.hut
            self._家门 = b._家门 = (家屋.y, 家屋.x)
            # 交换家门所在：从此配偶的屋檐也是家
            if self.hut is not None:
                b._known_huts[self.name] = (self.hut.y, self.hut.x)
            if b.hut is not None:
                self._known_huts[b.name] = (b.hut.y, b.hut.x)
            self.remember(f"与 {b.name} 结为伴侣", "伴侣", b.name, 0.95, tick)
            b.remember(f"与 {self.name} 结为伴侣", "伴侣", self.name, 0.95, tick)
            report(tick, (self.y, self.x),
                   f"{self.name} 与 {b.name} 结为伴侣（因：两情相悦+有檐可依）",
                   kind="结侣", actor=self.name, target=b.name)
            return True
        return False

    def _诞育(self, world: World, spirits: list, partner, tick: int, report, rng) -> bool:
        """生养：夜里同檐、温饱有余、生育窗口内、间隔既过 → 阴凝聚得一点阳，新生儿诞生。"""
        if tick - self._上次诞育 < BIRTH_PAIR_CD:
            return False
        年龄日 = (tick - self.诞生念) / TICKS_PER_DAY
        if not (FERTILE_AGE[0] <= 年龄日 <= FERTILE_AGE[1]):
            return False
        if not is_night(tick):
            return False
        if sum(1 for s in spirits if s.alive) >= POP_CAP:
            return False
        屋 = self.hut or partner.hut
        if 屋 is None:
            return False
        if self._切比(self.y, self.x, 屋.y, 屋.x) > 2:
            return False
        if self.yang < 50.0 or partner.yang < 50.0:
            return False
        if rng.random() > BIRTH_NIGHT_CHANCE:
            return False
        self._上次诞育 = tick
        partner._上次诞育 = tick
        name = 新名(spirits, rng)
        # 出生地环境写入婴儿 DNA：生在谁家檐下，就染上哪方水土
        child = Spirit(name, 屋.y, 屋.x, tick, rng, 父母=(self, partner),
                       env=环境印记(world, 屋.y, 屋.x))
        child._世界 = world
        world.生灵入账(child)      # 阴凝聚得一点阳：新生之初阳与形阴自炁场抽取
        spirits.append(child)
        self.子女.append(name)
        partner.子女.append(name)
        self.remember(f"我与 {partner.name} 得子 {name}", "伴侣", partner.name, 0.95, tick)
        partner.remember(f"我与 {self.name} 得子 {name}", "伴侣", self.name, 0.95, tick)
        report(tick, (屋.y, 屋.x),
               f"【诞】{self.name} 与 {partner.name} 得子 {name}（因：温饱有余+伉俪情深）",
               kind="诞育", actor=self.name, target=name)
        return True


    # ── 幼年：跟随父母，受哺育，耳濡目染 ──────

    def _幼年(self, world: World, spirits: list, tick: int, report, rng):
        """幼崽不事生产、不争斗：跟着父母，饿了受哺，看着学着长大。"""
        self._心情漂移()
        self._耗阳(self.yang * YANG_RATE * self.metabo * 0.6)   # 孩童耗阳少些（定率化）
        排 = min(self.水分, THIRST_DECAY)
        self.水分 -= 排
        world.water[self.y, self.x] += 排 * BODY2FIELD   # 汗溺之排，就地还场（水过身体，终还于土）
        if self._死否(world, tick, report, "阳尽", spirits):
            return
        if self._感知(world, spirits, tick, report, rng):
            return
        亲 = [s for s in spirits if s.alive and s.name in (self.父母 or ())]
        if not 亲:
            # 无亲可依的孤雏，只得早当起家
            self._已成年 = True
            report(tick, (self.y, self.x),
                   f"{self.name} 无亲可依，提前长大成人（因：孤儿早当家）",
                   kind="成年", actor=self.name)
            return
        亲.sort(key=lambda p: self._切比(self.y, self.x, p.y, p.x))
        p = 亲[0]
        d = self._切比(self.y, self.x, p.y, p.x)
        # 饿了：父母在旁则受哺
        if self.yang < 60.0 and d <= 1 and p.yang > 40.0:
            转阳(world, p, self, 12.0)       # 哺育：父母之阳转移于子
            self.stats["进食"] += 1
            self.remember(f"{p.name} 哺育我", "亲缘", p.name, 0.85, tick)
            return
        if self.水分 < 40.0 and world.water[self.y, self.x] >= DRINK_MIN:
            self._饮水(world, tick, report, rng)
            return
        if d > CHILD_FOLLOW:
            self._走向(world, p.y, p.x, rng)
            return
        # 家传：父母在身边劳作，孩子看着学着——每日灌注一门（门槛的三成半），
        # 最强的知识通道也非一蹴而就：手把手几日，方能自得
        day = tick // TICKS_PER_DAY
        if self._家传_day != day and d <= 1:
            for kn in ("烹饪", "渔猎", "制器", "取火", "建造", "种植", "畜牧",
                       "凿井", "制陶", "缝纫"):
                if kn in p.knowledge and kn not in self.knowledge:
                    self._家传_day = day
                    self.remember(f"{p.name} 手把手教我{kn}之法", "受教", p.name, 0.70, tick)
                    p.remember(f"我把{kn}之法传给了 {self.name}", "家传", self.name, 0.55, tick)
                    report(tick, (self.y, self.x),
                           f"{p.name} 把{kn}之法手把手传给了 {self.name}（因：家传）",
                           kind="家传", actor=p.name, target=self.name)
                    self._积学(kn, LEARN_GATE[kn] * 0.35, tick, report,
                               f"承 {p.name} 家传，于{kn}之法日久自得", "家传目染")
                    break

    def _成年(self, world: World, spirits: list, tick: int, report):
        """成年礼：从此独自面对世界。父母把心中最重的往事讲给他听——口述历史。"""
        self._已成年 = True
        report(tick, (self.y, self.x),
               f"{self.name} 成年了，开始独自面对这个世界（因：岁月生长）",
               kind="成年", actor=self.name)
        for s in spirits:
            if not s.alive or s.name not in (self.父母 or ()):
                continue
            往事 = [m for m in sorted(s.memories, key=lambda m: (m.永存, m.权重),
                                      reverse=True)
                    if m.类别 not in ("区域", "亲缘")][:HEIR_TELL]
            for m in 往事:
                情绪 = m.情绪强度 * 0.7
                恨 = m.类别 in _REL_NEG
                self.remember(f"听{s.name}讲起：{m.要义}",
                              "听闻恨" if 恨 else "听闻", m.对象, 情绪, tick)
