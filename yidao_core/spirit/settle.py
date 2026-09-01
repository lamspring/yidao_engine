"""灵体层 · 安身系统（M2 组件化拆分：自 spirit.py 整段搬运，行为不变）"""

from .base import *

class 安身Mixin:
    """灵之安身诸行。"""
    def _受冻(self, world: World, tick: int, report, rng):
        """寒夜彻骨：记下一笔。冻一夜，积一分——有人想出钻木取火，有人想着添衣。"""
        day = tick // TICKS_PER_DAY
        if self._受冻_day == day:
            return
        self._受冻_day = day
        self.remember("寒夜彻骨，几冻毙", "受冻", None, 0.55, tick)
        report(tick, (self.y, self.x),
               f"{self.name} 寒夜受冻（因：天地转阴+无火无檐）",
               kind="受冻", actor=self.name)
        self._积学("取火", 12.0, tick, report,
                   "在寒夜里想出钻木取火", "受冻已久")
        # 寒夜受冻的第二条出路：有人取火，有人添衣
        self._积学("缝纫", 8.0, tick, report,
                   "冻得搓手顿足，忽想以藤为线、以骨为针，缀衣以御寒", "受冻已久")
        # 冻怕了的人也想有四面墙：受冻同启建造之思
        self._积学("建造", 6.0, tick, report,
                   "冻得缩成一团，忽想有个挡风之屋", "受冻已久")

    def _钻木(self, world: World, tick: int, report, rng) -> bool:
        """钻木取火：需干柴一份（木最佳，茅草藤叶亦可引火），概率成功（悟性+熟练），得火一堆。"""
        柴 = self._取料("木") or self._取料("茅草") or self._取料("藤")
        if 柴 is None:
            return False
        if rng.random() < 0.35 + 0.5 * self.悟性 + 0.3 * self._熟练("取火"):
            self._涨熟练("取火")
            屋内 = self.hut is not None and (self.y, self.x) == (self.hut.y, self.hut.x)
            world.fires.append(Fireplace(self.y, self.x, self.name, 屋内=屋内))
            self._转化(world, [柴], FIRE_YANG0 + YIN_FIRE)   # 柴之结化火之结
            self._known_fires[self.name] = (self.y, self.x)
            self.mood["希望"] = min(1.0, self.mood["希望"] + 0.3)
            report(tick, (self.y, self.x),
                   f"{self.name} 钻木得火，{'屋内起灶' if 屋内 else '野地生烟'}（因：寒夜所迫+取火之技）",
                   kind="取火", actor=self.name)
            # 得火即炙：怀中若揣着生食又懂烹饪，新火第一灶
            if "烹饪" in self.knowledge:
                self._烹制(world, tick, report, rng)
        else:
            self._转化(world, [柴], 0.0)     # 未得火：柴之结散归炁场
            self._耗阳(0.4)
            report(tick, (self.y, self.x),
                   f"{self.name} 钻木良久，未得火（因：手生）",
                   kind="取火败", actor=self.name)
        return True

    def _赴火(self, world: World, tick: int, rng) -> bool:
        """向火而去：先找看得见的炊烟（感知半径内），再找记忆中的火。"""
        r = self._感知半径(tick)
        见火 = [fi for fi in world.fires
                if self._切比(self.y, self.x, fi.y, fi.x) <= r]
        if 见火:
            f0 = min(见火, key=lambda fi: self._切比(self.y, self.x, fi.y, fi.x))
            self._走向(world, f0.y, f0.x, rng)
            return True
        # 记忆中的火若已熄，忘掉这处；否则前往
        死火 = [k for k, p in self._known_fires.items()
                if world.fire_near(p[0], p[1], 0) is None]
        for k in 死火:
            del self._known_fires[k]
        if self._known_fires:
            fy, fx = min(self._known_fires.values(),
                         key=lambda p: abs(p[0] - self.y) + abs(p[1] - self.x))
            self._走向(world, fy, fx, rng)
            return True
        return False

    def _烹制(self, world: World, tick: int, report, rng) -> bool:
        """携生食赴火而炙：熟食之利，值得多走几步。看见炊烟即知火处。"""
        生 = next((it for it in self.bag if it.类型 in RAW_KINDS), None)
        if 生 is None:
            return False
        f = world.fire_near(self.y, self.x)
        if f is None:
            if self._赴火(world, tick, rng):
                return True
            # 无火可觅而会取火：有干柴就地点一堆
            if "取火" in self.knowledge and not world.raining_on(self.y, self.x):
                if any(self._数料(k) >= 1 for k in ("木", "茅草", "藤")):
                    return self._钻木(world, tick, report, rng)
            return False
        # 火在身旁：炙之
        self.bag.remove(生)
        熟 = "熟肉" if 生.类型 == "生肉" else "熟鱼"
        self.bag.append(Item(熟))
        self._转化(world, [生], ITEM_YANG[熟] + 物形阴(熟))   # 火炙：生之结化熟之结
        self._涨熟练("烹饪")
        self.mood["希望"] = min(1.0, self.mood["希望"] + 0.1)
        初次 = self.stats.get("烹食", 0) == 0
        self.stats["烹食"] = self.stats.get("烹食", 0) + 1
        report(tick, (self.y, self.x),
               f"{self.name} 以火炙{生.类型[1:]}为熟食（因：烹饪之技+火堆在侧）",
               kind="烹食初" if 初次 else "烹食", actor=self.name)
        return True


    # ── 九·锻炼 ─────────────────────────────

    def _锻炼(self, tick: int, report):
        # "开始锻炼"每日至多报一次——日日苦练是心志，不是新闻
        if not self.training and tick - self._last_train_report >= TICKS_PER_DAY:
            self._last_train_report = tick
            report(tick, (self.y, self.x),
                   f"{self.name} 开始锻炼（因：受辱铭记，欲求变强）",
                   kind="锻炼始", actor=self.name)
        self.training = True
        self.stats["锻炼"] += 1
        gain = TRAIN_GAIN * (1.0 - 0.5 * self.mood["疲惫"])
        self.strength = min(STRENGTH_CAP, self.strength + gain)
        self.mood["疲惫"] = min(1.0, self.mood["疲惫"] + 0.02)
        self._耗阳(TRAIN_COST)


    # ── 十·游荡与安眠 ────────────────────────

    def _栖身所(self) -> tuple[int, int]:
        """栖身处：结侣之家优先；有屋则屋为家；否则是记忆中最常停留的格子。"""
        if self._家门 is not None:
            return self._家门
        if self.hut is not None:
            return (self.hut.y, self.hut.x)
        if self.伴侣 is not None and self.伴侣 in self._known_huts:
            return self._known_huts[self.伴侣]
        if not self._stay:
            return (self.y, self.x)
        return max(self._stay.items(), key=lambda kv: kv[1])[0]

    def _檐下(self, world: World) -> bool:
        """此刻头顶是否有屋檐：自己的屋、配偶的屋，或今夜收留我之人的屋。"""
        b = world.building_at(self.y, self.x)
        if b is None:
            return False
        return b.主人 == self.name or b.主人 == self._庇主 or b.主人 == self.伴侣

    def _安眠(self, world: World, 有檐: bool):
        """归栖而眠：檐下安眠，疲惫大解；露宿则雨打风吹，歇不踏实。"""
        self.stats["安眠"] += 1
        self.mood["疲惫"] = max(0.0, self.mood["疲惫"] - (0.08 if 有檐 else 0.05))
        self.mood["希望"] = min(1.0, self.mood["希望"] + 0.02)
        self.training = False


    # ── 祈雨聚（v6.4）：天道永不回应，仪式是群体的镇定剂 ──

    def _祈雨聚(self, world: World, spirits: list, tick: int, report, rng) -> bool:
        """连旱草枯之际，亲和高者发起祈雨聚；邻近灵闻讯而来，围聚一处，费率一日。
        天道永不回应祈雨——但参与者恐惧下降、关系上升、互记"同祈"；
        若三日内恰有雨至（纯巧合），参与者记"祈雨得应"，发起者声望由此而起。
        迷信从巧合中诞生，这是真实人性。"""
        day = tick // TICKS_PER_DAY
        # 赴祈：闻讯而来，到场则同祈
        if self._赴祈 is not None:
            y, x, d, 发起 = self._赴祈
            if d != day or is_night(tick):
                self._赴祈 = None
                return False
            if self._切比(self.y, self.x, y, x) <= 1:
                self._赴祈 = None
                self._祈雨 = (发起, tick)
                主 = next((s for s in spirits if s.alive and s.name == 发起), None)
                if 主 is not None:
                    self.remember(f"与 {发起} 同祈甘霖", "同祈", 发起, 0.50, tick)
                    主.remember(f"{self.name} 来与我同祈", "同祈", self.name, 0.45, tick)
                self.mood["恐惧"] = max(0.0, self.mood["恐惧"] - 0.25)
                self.mood["希望"] = min(1.0, self.mood["希望"] + 0.10)
                report(tick, (self.y, self.x),
                       f"{self.name} 赶来与 {发起} 同祈甘霖（因：闻讯而至+同忧则同祈）",
                       kind="赴祈", actor=self.name, target=发起)
                # 祈雨不应，不如凿井：同忧之际，有人低头看向了大地
                self._积学("凿井", 12.0, tick, report,
                           "祈雨之余忽悟：雨不应人，低洼之下或有九泉，可凿井取之", "祈雨不应")
                return True
            self._走向(world, y, x, rng)
            return True
        # 发起者守祀一日：围聚之处，不远离
        if self._祀_day == day:
            self.mood["疲惫"] = max(0.0, self.mood["疲惫"] - 0.05)
            return True
        # 发起条件：白昼、连旱、草枯、亲和高、温饱有余
        if is_night(tick) or self.affinity < PRAY_AFFINITY:
            return False
        if tick - self._雨见 < DROUGHT_DAYS * TICKS_PER_DAY:
            return False
        if day - self._祀_day < PRAY_COOLDOWN:
            return False
        if self.yang < 50.0 or self.水分 < 40.0:
            return False
        r = 3
        草 = [world.grass[self.y + dy, self.x + dx]
              for dy in range(-r, r + 1) for dx in range(-r, r + 1)
              if world.in_bounds(self.y + dy, self.x + dx)]
        if not 草 or sum(草) / len(草) > PRAY_GRASS:
            return False
        if rng.random() > 0.5:
            return False
        # 发起！邻近灵闻讯而来
        self._祀_day = day
        旱日 = (tick - self._雨见) // TICKS_PER_DAY
        闻讯 = [s for s in spirits if s is not self and s.alive
                and getattr(s, "_已成年", True)
                and self._切比(s.y, s.x, self.y, self.x) <= PRAY_RANGE
                and s.relation(self.name) > -0.3
                and s.yang > 40.0 and s.水分 > 35.0 and s._迁 is None]
        for s in 闻讯:
            s._赴祈 = (self.y, self.x, day, self.name)
        self._祈雨 = (self.name, tick)
        self.mood["恐惧"] = max(0.0, self.mood["恐惧"] - 0.15)
        report(tick, (self.y, self.x),
               f"{self.name} 于{world.terrain_name(self.y, self.x)}之上发起祈雨聚，"
               f"{len(闻讯)} 灵闻讯而来（因：连旱{旱日}日+草枯苗焦）",
               kind="祈雨聚", actor=self.name)
        # 祈雨不应，不如凿井：发起者在仰天之余，也可能低头看向大地
        self._积学("凿井", 12.0, tick, report,
                   "祈雨之余忽悟：雨不应人，低洼之下或有九泉，可凿井取之", "祈雨不应")
        return True
