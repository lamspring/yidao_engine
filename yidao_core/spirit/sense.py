"""灵体层 · 感知系统（M2 组件化拆分：自 spirit.py 整段搬运，行为不变）"""

from .base import *

class 感知Mixin:
    """灵之感知诸行。"""

    # ───────────────────────────────────────
    # 一、感知：昼五夜二，所见即所知
    # ───────────────────────────────────────

    def _感知半径(self, tick: int) -> int:
        return SENSE_NIGHT if is_night(tick) else SENSE_DAY

    @staticmethod

    def _切比(y1, x1, y2, x2) -> int:
        return max(abs(y1 - y2), abs(x1 - x2))

    def _感知(self, world: World, spirits: list, tick: int, report, rng) -> bool:
        """每念扫视四周：记下眼见的食物与水源、谁在眼前、谁家屋檐与田畦、何处有故人之骨。
        返回 True 表示本念已被悼念占去。"""
        r = self._感知半径(tick)
        self._stay[(self.y, self.x)] = self._stay.get((self.y, self.x), 0) + 1
        for dy in range(-r, r + 1):
            for dx in range(-r, r + 1):
                ny, nx = self.y + dy, self.x + dx
                if not world.in_bounds(ny, nx):
                    continue
                if world.grass[ny, nx] >= EAT_GRASS_MIN:
                    self.known_food[(ny, nx)] = tick
                elif (ny, nx) in self.known_food and world.grass[ny, nx] < EAT_GRASS_MIN:
                    del self.known_food[(ny, nx)]   # 亲见枯竭，从心中抹去
                if world.water[ny, nx] >= DRINK_MIN:
                    self.known_water[(ny, nx)] = tick
        for s in spirits:
            if s is not self and s.alive \
                    and self._切比(self.y, self.x, s.y, s.x) <= r:
                self._last_seen[s.name] = (s.y, s.x, tick, s.strength)

        # 看见别人的茅屋/农田：记下"那是谁的"（所有权是社会记忆），
        # 看在眼里、记在心里——日久看明白门道，模仿由此而生（积学，不再掷骰）
        for b in world.buildings:
            if self._切比(self.y, self.x, b.y, b.x) > r:
                continue
            self._known_huts[b.主人] = (b.y, b.x)
            if "建造" not in self.knowledge and b.主人 != self.name \
                    and self._积学("建造", 2.5, tick, report,
                                   f"看明白了 {b.主人} 的茅屋，悟得建造之法", "观察模仿"):
                self.remember(f"看懂了 {b.主人} 的茅屋，悟得建造之法", "学会", b.主人, 0.60, tick)
        for f in world.farms:
            if self._切比(self.y, self.x, f.y, f.x) > r:
                continue
            if "种植" not in self.knowledge and f.主人 != self.name \
                    and self._积学("种植", 2.5, tick, report,
                                   f"看明白了 {f.主人} 的田畦，悟得种植之法", "观察模仿"):
                self.remember(f"看懂了 {f.主人} 的田畦，悟得种植之法", "学会", f.主人, 0.60, tick)
        # 火堆入眼：记下何处有火（寒夜可以投奔）
        for f in world.fires:
            if self._切比(self.y, self.x, f.y, f.x) <= r:
                self._known_fires[f.主人] = (f.y, f.x)

        # 井入眼：记下何处有井（旱时可以来汲）；看得久了，自会看出凿井的门道
        for wl in world.wells:
            if self._切比(self.y, self.x, wl.y, wl.x) > r:
                continue
            self._known_wells[(wl.y, wl.x)] = wl.主人
            if "凿井" not in self.knowledge and wl.主人 != self.name \
                    and self._积学("凿井", 2.5, tick, report,
                                   f"看明白了 {wl.主人} 的井，悟得凿井之法", "观察模仿"):
                self.remember(f"看懂了 {wl.主人} 的井，悟得凿井之法", "学会", wl.主人, 0.60, tick)

        # 亲见落雨：旱魃之惧随之刷新。祈过雨的人此刻最敏感——
        # 三日内的雨都算"得应"：纯巧合，但人心不这么记（迷信从巧合中诞生）。
        if world.raining_on(self.y, self.x):
            self._雨见 = tick
            if self._祈雨 is not None:
                发起, 祈念 = self._祈雨
                self._祈雨 = None
                if tick - 祈念 <= PRAY_ANSWER * TICKS_PER_DAY:
                    if 发起 != self.name:
                        self.remember(f"{发起} 祈雨得应，甘霖果至", "祈应", 发起, 0.75, tick)
                    else:
                        self.remember("我祈的雨竟落了下来", "祈应", None, 0.70, tick)
                    self.mood["希望"] = 1.0
                    report(tick, (self.y, self.x),
                           f"{self.name} 淋着雨，坚信 {发起} 的祈雨得了应（因：雨后之巧+人心信之）",
                           kind="祈应", actor=self.name, target=发起)

        # 悼念：好友的遗骨就在眼前，岂能不停一停；在场同识者闻哀同悲（同悼）。
        # 误会：认得死者却不知其死因，见有人在遗骨/遗物旁徘徊——疑心生暗鬼。
        for m in world.marks:
            if m.类型 != "尸骨" or not m.标签:
                continue
            key = (m.y, m.x, m.诞生念)
            if key in self._mourned:
                continue
            if self._切比(self.y, self.x, m.y, m.x) > r:
                continue
            if self.relation(m.标签) >= FRIEND_REL:
                self._mourned.add(key)
                self.remember(f"在 {m.标签} 的遗骨前伫立良久", "悼念", m.标签, 0.70, tick)
                self.mood["希望"] = max(0.0, self.mood["希望"] - 0.2)
                report(tick, (m.y, m.x),
                       f"{self.name} 在 {m.标签} 的遗骨前伫立良久（因：故人之思）",
                       kind="悼念", actor=self.name, target=m.标签)
                self._同悼(world, spirits, m, tick, report)
                return True
            if self._生疑(spirits, m.标签, m.y, m.x, key, tick, report, rng):
                return True
        for rl in world.relics:
            key = ("遗物", rl["y"], rl["x"], rl["念"])
            if self._切比(self.y, self.x, rl["y"], rl["x"]) > r:
                continue
            if self._生疑(spirits, rl["名"], rl["y"], rl["x"], key, tick, report, rng):
                return True
        return False

    def _生疑(self, spirits: list, 亡者: str, y: int, x: int, key, tick: int,
              report, rng) -> bool:
        """疑心生暗鬼：认得死者、不知其死因，见有人在遗骨/遗物旁徘徊，
        概率性误以为此人是凶手——记下一笔与真目睹无异的错误记忆。疑只起一次。"""
        if key in self._疑过:
            return False
        if not any(m.对象 == 亡者 and m.类别 != "传闻" for m in self.memories):
            return False    # 根本不识死者，无从生疑
        骨旁 = [s for s in spirits if s is not self and s.alive
                and getattr(s, "_已成年", True)
                and self._切比(s.y, s.x, y, x) <= 1
                and self._切比(self.y, self.x, s.y, s.x) <= self._感知半径(tick)
                and not any(m.对象 == s.name and m.类别 == "目睹"
                            for m in self.memories)]
        if not 骨旁:
            return False
        self._疑过.add(key)
        if rng.random() >= MISJUDGE * (0.5 + self.caution):
            return False
        嫌 = rng.choice(骨旁)
        # 错误记忆与真目睹同类别、同文字——在灵心里，误会与事实不可分辨
        self.remember(f"目睹 {嫌.name} 行凶", "目睹", 嫌.name, 0.65, tick)
        self.mood["恐惧"] = min(1.0, self.mood["恐惧"] + 0.2)
        report(tick, (y, x),
               f"{self.name} 见 {嫌.name} 徘徊在 {亡者} 的遗骨遗物旁，疑其为凶（因：疑心生暗鬼+感知有限）",
               kind="误会", actor=self.name, target=嫌.name, subject=亡者)
        return True

    def _同悼(self, world: World, spirits: list, mark, tick: int, report):
        """一人举哀，闻者同悲：在场、同识死者、尚未致哀的人同声而哀。
        共同的哀伤把生者拉近——葬礼的雏形，群体纽带由此而生。"""
        key = (mark.y, mark.x, mark.诞生念)
        同识 = []
        for s in spirits:
            if s is self or not s.alive or not getattr(s, "_已成年", True):
                continue
            if key in s._mourned:
                continue
            if self._切比(s.y, s.x, mark.y, mark.x) > s._感知半径(tick):
                continue
            if s.relation(mark.标签) < FRIEND_REL * 0.6:
                continue
            同识.append(s)
        if not 同识:
            return
        for s in 同识:
            s._mourned.add(key)
            s.remember(f"在 {mark.标签} 的遗骨前同声而哀", "悼念", mark.标签, 0.60, tick)
            s.remember(f"与 {self.name} 同悼 {mark.标签}", "同悼", self.name, 0.50, tick)
            self.remember(f"与 {s.name} 同悼 {mark.标签}", "同悼", s.name, 0.50, tick)
        名 = "、".join([self.name] + [s.name for s in 同识])
        report(tick, (mark.y, mark.x),
               f"{名} 在 {mark.标签} 的遗骨前同声而哀（因：故人之思+同气相感）",
               kind="同悼", actor=self.name, target=mark.标签)

    def _感知到(self, s, tick: int) -> bool:
        return s.alive and self._切比(self.y, self.x, s.y, s.x) <= self._感知半径(tick)

    def _观察(self, world: World, tick: int):
        """踏勘陌生之地：记下区域、压下未知恐惧（食物水源已由感知收录）。"""
        key = self._区域键()
        旧 = next((m for m in self.memories if m.类别 == "区域" and m.对象 == key), None)
        if 旧 is not None:
            旧.权重 = 0.3
            旧.念戳 = tick
        else:
            self.remember(f"踏勘过{world.terrain_name(self.y, self.x)}一带",
                          "区域", key, 0.15, tick)
        self.mood["恐惧"] = max(0.0, self.mood["恐惧"] - 0.15)
        self.mood["希望"] = min(1.0, self.mood["希望"] + 0.05)
        self._耗阳(0.05)
