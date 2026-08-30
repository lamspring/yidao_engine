"""灵体层 · 营建系统（M2 组件化拆分：自 spirit.py 整段搬运，行为不变）"""

from .base import *

class 营建Mixin:
    """灵之营建诸行。"""

    # ── 雨夜、屋檐与求庇 ─────────────────────

    def _淋雨(self, world: World, tick: int, report, rng):
        """夜雨淋身：记下这寒夜（每日至多一记）。
        痛得够深、悟性够高者，会在冷雨中自己想出办法——初代发明由此而来。"""
        day = tick // TICKS_PER_DAY
        if self._淋雨_day == day:
            return
        self._淋雨_day = day
        self.remember("夜雨淋身，寒彻入骨", "淋雨", None, 0.55, tick)
        self.mood["希望"] = max(0.0, self.mood["希望"] - 0.1)
        self.mood["疲惫"] = min(1.0, self.mood["疲惫"] + 0.05)
        report(tick, (self.y, self.x),
               f"{self.name} 夜雨淋身（因：无屋可栖+天公不作美）",
               kind="淋雨", actor=self.name)
        # 淋一夜雨，积一分营造之思——冻得久了，自会想出屋檐
        self._积学("建造", 10.0, tick, report,
                   "在冷雨中忽悟：可结草为屋", "夜雨淋身")

    def _尝试求庇(self, world: World, spirits: list, tick: int, report, rng) -> bool:
        """雨夜无屋 → 求宿故人檐下；屋主依关系收留或拒绝。
        赶路不占额度——走到了、见了主，才算求过一次。"""
        day = tick // TICKS_PER_DAY
        if self._求庇_day == day:
            self._求庇_target = None
            return False
        # 找一座"我知道的、非敌之人的、还在的"屋——好友优先，收留与否由屋主定夺
        候选 = []
        for 主人, pos in self._known_huts.items():
            if 主人 == self.name or self.relation(主人) <= -0.3:
                continue
            b = world.building_at(pos[0], pos[1])
            if b is not None and b.主人 == 主人:
                候选.append((-self.relation(主人), abs(pos[0] - self.y) + abs(pos[1] - self.x), 主人, pos))
        if not 候选:
            self._求庇_target = None
            return False
        候选.sort()
        _, _, 主人, pos = 候选[0]
        self._求庇_target = 主人
        if self._切比(self.y, self.x, pos[0], pos[1]) > 0:
            self._走向(world, pos[0], pos[1], rng)   # 冒夜雨赶往故人檐下
            return True
        # 已到门前：主人在家吗？肯收留吗？
        self._求庇_day = day
        owner = next((s for s in spirits if s.alive and s.name == 主人), None)
        if owner is None or self._切比(owner.y, owner.x, pos[0], pos[1]) > 3:
            return False    # 吃了闭门羹：主不在，悄然退去
        if owner.relation(self.name) >= FRIEND_REL * 0.8:
            self._庇主 = 主人
            self.remember(f"{主人} 收留了我", "受助", 主人, 0.75, tick)
            owner.remember(f"我收留过 {self.name}", "助人", self.name, 0.50, tick)
            self._漂移("affinity", DRIFT_AFFINITY_HELPED, tick, report, "雨夜得人收留")
            report(tick, pos,
                   f"{主人} 收留了夜雨来投的 {self.name}（因：故交+恻隐）",
                   kind="求庇收留", actor=主人, target=self.name)
        else:
            self.remember(f"{主人} 拒我于门外", "被拒", 主人, 0.60, tick)
            self.pressure += 0.20
            self.mood["希望"] = max(0.0, self.mood["希望"] - 0.15)
            report(tick, pos,
                   f"{主人} 拒绝了夜雨来投的 {self.name}（因：情分未够）",
                   kind="求庇拒绝", actor=主人, target=self.name)
            # 寒心之人，暗自立誓：他日自建屋檐，不求于人
            self._积学("建造", 15.0, tick, report,
                       "吃了闭门羹，暗自立誓自建屋檐", "求庇被拒+寒心")
        return True


    # ── 夺屋：雨夜无屋的悍者，恃强占人屋檐 ────

    def _尝试夺屋(self, world: World, spirits: list, tick: int, report, rng) -> bool:
        r = self._感知半径(tick)
        for b in world.buildings:
            if b.主人 == self.name:
                continue
            if self._切比(self.y, self.x, b.y, b.x) > r:
                continue
            owner = next((s for s in spirits if s.alive and s.name == b.主人), None)
            if owner is None:
                continue    # 无主空屋暂不取：夺屋要的是当面压服
            ls = self._last_seen.get(b.主人)
            知其力 = ls[3] if ls else None
            if 知其力 is None or self.strength < 知其力 * 0.9:
                continue    # 不知底细或打不过，不起念
            if not self._感知到(owner, tick):
                continue    # 主人不在场，夺之无名
            if self._切比(self.y, self.x, owner.y, owner.x) > 1:
                self._走向(world, owner.y, owner.x, rng)
                return True
            report(tick, (self.y, self.x),
                   f"{self.name} 闯到 {owner.name} 的茅屋前，要占这屋檐（因：无屋+恃强）",
                   kind="夺屋", actor=self.name, target=owner.name)
            我阳 = self.yang
            self._战斗(owner, world, spirits, tick, report, rng, 报复=None)
            if self.yang >= 我阳 - 8.0:    # 我占了上风（粗略以战后余阳判）
                b.主人 = self.name
                self.hut = b
                if owner.alive:
                    owner.hut = None
                    owner.remember(f"{self.name} 夺了我的屋", "夺屋", self.name, 0.92, tick)
                    owner.pressure += 0.60
                    owner.want("变强")
                    owner.want(f"报复:{self.name}")
                    owner._漂移("caution", DRIFT_CAUTION_ROBBED, tick, report, "被人夺了屋檐")
                    self.remember(f"我夺了 {owner.name} 的屋", "抢人", owner.name, 0.55, tick)
                    report(tick, (b.y, b.x),
                           f"茅屋易主：{owner.name} 的屋檐从此归 {self.name}（因：力弱者失其居）",
                           kind="夺屋成", actor=self.name, target=owner.name)
                else:
                    # 主人已死，空屋归胜者
                    report(tick, (b.y, b.x),
                           f"茅屋易主：{owner.name} 已亡，空屋归 {self.name}（因：胜者为王）",
                           kind="夺屋成", actor=self.name, target=owner.name)
            return True
        return False


    # ── 营建与农事 ──────────────────────────

    def _建材数(self) -> int:
        """草木藤皆可为舍：茅草、藤、木都是建材。"""
        return sum(1 for it in self.bag if it.类型 in ("茅草", "藤", "木"))

    def _取建材(self) -> Item | None:
        return self._取料("茅草") or self._取料("藤") or self._取料("木")

    def _营建(self, world: World, tick: int, report, rng) -> bool:
        """建造链：知法 + 动机（淋过雨/求庇被拒/见过他人的屋）→ 备料 → 选址 → 施工。"""
        if self.hut is not None:
            # 屋漏则修：一份建材补一回阳；无料则采——修缮也要有备料
            if self.hut.阳 < HUT_OWN_REPAIR_AT:
                if self._建材数() >= 1 and (self.y, self.x) == (self.hut.y, self.hut.x):
                    料 = self._取建材()
                    旧 = self.hut.阳
                    self.hut.阳 = min(80.0, self.hut.阳 + HUT_REPAIR)
                    self._转化(world, [料], self.hut.阳 - 旧)   # 修缮：料之结系回屋上
                    report(tick, (self.y, self.x),
                           f"{self.name} 修缮了自家茅屋（因：风雨剥蚀，屋阳将亏）",
                           kind="修缮", actor=self.name)
                    return True
                if self._建材数() < 1:
                    if world.grass[self.y, self.x] >= GATHER_GRASS_MIN:
                        world.grass[self.y, self.x] -= 0.4
                        self._得物(world, "茅草")
                        self._耗阳(0.15)
                        report(tick, (self.y, self.x),
                               f"{self.name} 割取茅草（因：修缮之需）",
                               kind="采集", actor=self.name)
                        return True
                    if self._采集资源(world, tick, report, rng):
                        return True
                    if self.known_food:
                        ty, tx = min(self.known_food,
                                     key=lambda p: abs(p[0] - self.y) + abs(p[1] - self.x))
                        self._走向(world, ty, tx, rng)
                        return True
            return False
        if "建造" not in self.knowledge:
            return False
        # 动机：淋过雨、受过冻、求庇被拒、看过他人的屋、屋塌之痛、或刚刚弃家而迁
        # （建造动机源于物质痛苦——冷雨冻风皆为师）
        动机 = any(m.类别 in ("淋雨", "受冻", "被拒", "学会", "塌屋", "迁徙")
                   for m in self.memories)
        if not 动机:
            return False
        # 备料：先割脚下的丰草，再采眼见之材（藤木亦可为舍），最后走向记忆中的草场
        if self._建材数() < MATERIAL_NEED:
            if world.grass[self.y, self.x] >= GATHER_GRASS_MIN:
                world.grass[self.y, self.x] -= 0.4
                self._得物(world, "茅草")
                self._耗阳(0.15)
                report(tick, (self.y, self.x),
                       f"{self.name} 割取茅草（因：营造之需）",
                       kind="采集", actor=self.name)
                return True
            if self._采集资源(world, tick, report, rng):
                return True
            r = self._感知半径(tick)
            丰草 = [(abs(dy) + abs(dx), self.y + dy, self.x + dx)
                    for dy in range(-r, r + 1) for dx in range(-r, r + 1)
                    if world.in_bounds(self.y + dy, self.x + dx)
                    and world.grass[self.y + dy, self.x + dx] >= GATHER_GRASS_MIN]
            if 丰草:
                丰草.sort()
                self._走向(world, 丰草[0][1], 丰草[0][2], rng)
            elif self.known_food:
                ty, tx = min(self.known_food,
                             key=lambda p: abs(p[0] - self.y) + abs(p[1] - self.x))
                self._走向(world, ty, tx, rng)
            else:
                self._探索(world, rng)
            return True
        # 选址：谨慎者喜高燥，亲水者近水泽——性格决定风水
        if self._工地 is None:
            self._工地 = (*self._选址(world, rng), 0)
            report(tick, (self._工地[0], self._工地[1]),
                   f"{self.name} 在{world.terrain_name(self._工地[0], self._工地[1])}动土建屋（因：备料已足）",
                   kind="动土", actor=self.name)
        ty, tx, 进度 = self._工地
        if (self.y, self.x) != (ty, tx):
            self._走向(world, ty, tx, rng)
            return True
        self._耗阳(BUILD_COST)
        进度 += 1
        self._工地 = (ty, tx, 进度)
        if 进度 >= BUILD_TICKS:
            料单 = [self._取建材() for _ in range(MATERIAL_NEED)]
            self.hut = world.add_building(ty, tx, self.name)
            self._转化(world, 料单, HUT_YANG0 + YIN_HUT)   # 材之结解开，屋之结系上
            self._known_huts[self.name] = (ty, tx)
            self._工地 = None
            self.mood["希望"] = 1.0
            report(tick, (ty, tx),
                   f"{self.name} 的茅屋落成（因：淋过冷雨+自己动手）",
                   kind="建成", actor=self.name)
        return True

    def _选址(self, world: World, rng) -> tuple[int, int]:
        """在栖身所附近择一宅基地。谨慎者偏好高地（防风……高处风更烈，但不被水淹），
        亲水亲和者偏好近水的洼地——选址是性格写在大地上的投影。"""
        hy, hx = self._栖身所()
        喜高 = self.caution > self.affinity
        best, bs, br = (hy, hx), -1e9, 6
        for dy in range(-br, br + 1):
            for dx in range(-br, br + 1):
                ny, nx = hy + dy, hx + dx
                if not world.in_bounds(ny, nx):
                    continue
                if world.water[ny, nx] > 1.0 or world.building_at(ny, nx):
                    continue
                h = world.height[ny, nx]
                score = (h * 1.2 if 喜高 else (9.0 - h) * 0.6 + world.moisture[ny, nx] * 4.0)
                score += rng.uniform(0, 1.5) - 0.15 * (abs(dy) + abs(dx))
                # 逐井而居：近井之地水无忧——定居格局随井而变
                for (wy, wx) in self._known_wells:
                    if abs(wy - ny) + abs(wx - nx) <= 4:
                        score += 2.5
                        break
                if score > bs:
                    best, bs = (ny, nx), score
        return best

    def _井址(self, world: World, rng) -> tuple | None:
        """凿井选址：低洼湿润、非深水、无屋无井无田之地，离栖身所越近越好。
        水往低处流，九泉离低洼最近——选址是对水文的无声理解。"""
        hy, hx = self._栖身所()
        best, bs = None, -1e9
        for dy in range(-6, 7):
            for dx in range(-6, 7):
                ny, nx = hy + dy, hx + dx
                if not world.in_bounds(ny, nx):
                    continue
                if world.water[ny, nx] > 1.5 or world.building_at(ny, nx) \
                        or world.well_at(ny, nx) is not None:
                    continue
                if any(f.y == ny and f.x == nx for f in world.farms):
                    continue
                score = -world.height[ny, nx] + world.moisture[ny, nx] * 4.0 \
                    - 0.2 * (abs(dy) + abs(dx)) + rng.uniform(0, 0.5)
                if score > bs:
                    best, bs = (ny, nx), score
        return best

    def _凿井(self, world: World, tick: int, report, rng) -> bool:
        """凿井链：知法 + 水忧（焦渴记忆或久不见雨）→ 择低洼湿润处 → 施工 → 井成。
        井是世界对象：会淤、会枯、可淘浚；众灵向井聚居，定居格局由此而变。"""
        if "凿井" not in self.knowledge:
            return False
        动机 = any(m.类别 == "焦渴" for m in self.memories) \
            or tick - self._雨见 > 2 * TICKS_PER_DAY
        if not 动机:
            return False
        # 近处已有活井则不必再凿
        for (wy, wx) in self._known_wells:
            if world.well_at(wy, wx) is not None \
                    and self._切比(self.y, self.x, wy, wx) <= 6:
                return False
        for wl in world.wells:
            if self._切比(self.y, self.x, wl.y, wl.x) <= 4:
                return False
        if self._井地 is None:
            址 = self._井址(world, rng)
            if 址 is None:
                return False
            self._井地 = (址[0], 址[1], 0)
            report(tick, 址,
                   f"{self.name} 在{world.terrain_name(址[0], 址[1])}动工凿井（因：水忧在心+凿井之法）",
                   kind="凿井", actor=self.name)
        ty, tx, 进度 = self._井地
        if (self.y, self.x) != (ty, tx):
            self._走向(world, ty, tx, rng)
            return True
        self._耗阳(DIG_COST)
        进度 += 1
        self._井地 = (ty, tx, 进度)
        if 进度 >= WELL_DIG_TICKS:
            self._井地 = None
            world.wells.append(Well(ty, tx, self.name))
            # 井非阴阳凝聚之物，乃地形之变：水脉本在地底，人只是把泥土掘开——
            # 与径同类（众脚踏出来的地形之变），不入器物账；旬日劳作之阳
            # 已通过 _耗阳 归还炁场，那是汗水唯一的能量去向
            self._known_wells[(ty, tx)] = self.name
            self._涨熟练("凿井")
            self.mood["希望"] = min(1.0, self.mood["希望"] + 0.3)
            report(tick, (ty, tx),
                   f"{self.name} 凿成一口井，九泉之水自此可取（因：焦渴所迫+旬日施工）",
                   kind="井成", actor=self.name)
        return True

    def _农事(self, world: World, tick: int, report, rng) -> bool:
        """种植链：会种植且温饱 → 播种；田熟则收。"""
        if "种植" not in self.knowledge:
            return False
        我田 = [f for f in world.farms if f.主人 == self.name]
        for f in 我田:
            if not f.成熟(tick):
                continue
            if (self.y, self.x) == (f.y, f.x):
                world.farms.remove(f)
                self._泵阳(world, HARVEST_GAIN)     # 田间收获，记日月之泵
                self.mood["希望"] = min(1.0, self.mood["希望"] + 0.15)
                report(tick, (f.y, f.x),
                       f"{self.name} 收获了亲手种的庄稼（因：种瓜得瓜）",
                       kind="收获", actor=self.name)
                return True
            self._走向(world, f.y, f.x, rng)
            return True
        if len(我田) < FARM_MAX and self.yang > 55.0:
            m = world.moisture[self.y, self.x]
            if PLANT_MOIST[0] <= m <= PLANT_MOIST[1] and world.water[self.y, self.x] < 0.8 \
                    and world.building_at(self.y, self.x) is None \
                    and not any(f.y == self.y and f.x == self.x for f in world.farms):
                self._耗阳(PLANT_COST)      # 躬耕之耗，就地归还
                world.farms.append(Farm(self.y, self.x, self.name, tick))
                report(tick, (self.y, self.x),
                       f"{self.name} 在{world.terrain_name(self.y, self.x)}播下种子（因：习得种植+土润宜耕）",
                       kind="播种", actor=self.name)
                return True
        return False


    # ── 百工：制器、取火、烹饪、畜牧 ──────────

    def _有器(self, 类型: str) -> bool:
        return any(it.类型 == 类型 for it in self.bag)

    def _最佳武器(self) -> str | None:
        有 = [w for w in WEAPON_BONUS if self._有器(w)]
        return max(有, key=lambda w: WEAPON_BONUS[w]) if 有 else None

    def _数料(self, 类型: str) -> int:
        return sum(1 for it in self.bag if it.类型 == 类型)

    def _取料(self, 类型: str) -> Item | None:
        it = next((i for i in self.bag if i.类型 == 类型), None)
        if it is not None:
            self.bag.remove(it)
        return it

    def _磨损(self, 类型: str, tick: int, report):
        """工具会磨损；阳尽断裂。损者与断者之形，皆归还炁场。"""
        it = next((i for i in self.bag if i.类型 == 类型), None)
        if it is None:
            return
        耗 = min(1.5, it.阳)
        it.阳 -= 耗
        if self._世界 is not None:
            self._世界.物归(self.y, self.x, 耗)
        if it.阳 <= 0:
            self.bag.remove(it)
            if self._世界 is not None:
                self._世界.物归(self.y, self.x, 物形阴(类型))
            self.remember(f"我的{类型}用断了", "器损", None, 0.45, tick)
            report(tick, (self.y, self.x),
                   f"{self.name} 的{类型}断了（因：磨损日久，阳尽则断）",
                   kind="器断", actor=self.name)

    def _百工(self, world: World, spirits: list, tick: int, report, rng) -> bool:
        """温饱之上的营生：添柴 → 备料 → 制器 → 制陶 → 缝纫 → 烹饪 → 畜牧。"""
        # 备料：知百工而缺料，则采眼见之材（木/石/藤/土/骨）
        if self.knowledge & {"制器", "取火", "畜牧", "制陶", "缝纫"}:
            if self._备料(world, tick, report, rng):
                return True
        # 添柴：自家的火，阳亏则续一份木——火要靠养；柴之结化火之阳
        for f in world.fires:
            if f.主人 == self.name and f.阳 < 30.0 \
                    and abs(f.y - self.y) <= 2 and abs(f.x - self.x) <= 2 \
                    and self._数料("木") >= 1:
                料 = self._取料("木")
                旧 = f.阳
                f.阳 = min(80.0, f.阳 + FIRE_FEED)
                self._转化(world, [料], f.阳 - 旧)
                report(tick, (f.y, f.x),
                       f"{self.name} 给火堆添了柴（因：火阳将亏）",
                       kind="添柴", actor=self.name)
                return True
        # 制器：知法 + 缺器 + 有料
        if "制器" in self.knowledge:
            for 器 in TOOL_PRIORITY:
                if self._有器(器):
                    continue
                料 = RECIPES[器]
                if all(self._数料(k) >= v for k, v in 料.items()):
                    料单 = [self._取料(k) for k, v in 料.items() for _ in range(v)]
                    if rng.random() < 0.5 + 0.5 * self._熟练("制器"):
                        self.bag.append(Item(器))
                        self._转化(world, 料单, ITEM_YANG_TOOL + 物形阴(器))
                        self._涨熟练("制器")
                        report(tick, (self.y, self.x),
                               f"{self.name} 制成了{器}（因：制器之技+材料齐备）",
                               kind="制器", actor=self.name)
                    else:
                        self._转化(world, 料单, 0.0)     # 制器败：料之结散归炁场
                        self._耗阳(0.3)
                        report(tick, (self.y, self.x),
                               f"{self.name} 制{器}失败，费了些材料（因：手艺生疏）",
                               kind="制器败", actor=self.name)
                    return True
        # 冶炼（火克金）：知制器 + 有矿石 + 焰火旺——矿石入火，金自石出
        if "制器" in self.knowledge and self._数料("矿石") >= 1 \
                and world.火相(self.y, self.x) == "焰":
            料单 = [self._取料("矿石")]
            self.bag.append(Item("金块"))
            self._转化(world, 料单, ITEM_YANG["金块"] + 物形阴("金块"))
            self._涨熟练("制器")
            report(tick, (self.y, self.x),
                   f"{self.name} 就焰火炼出一块金块（因：火克金+矿石入火，金自石出）",
                   kind="冶炼", actor=self.name)
            return True
        # 锻打：金块与木，就焰火锻成金刃——金刃之利，远胜石器
        if "制器" in self.knowledge and not self._有器("金刃") \
                and self._数料("金块") >= 1 and self._数料("木") >= 1 \
                and world.火相(self.y, self.x) == "焰":
            料单 = [self._取料("金块"), self._取料("木")]
            self.bag.append(Item("金刃"))
            self._转化(world, 料单, ITEM_YANG_TOOL + 物形阴("金刃"))
            self._涨熟练("制器")
            report(tick, (self.y, self.x),
                   f"{self.name} 就焰火锻成一柄金刃（因：锻打之工+金木齐备）",
                   kind="锻打", actor=self.name)
            return True
        # 制陶：知法 + 有土或沙（土与沙皆可成陶）+ 旺火在旁才能烧（星火难成器）
        if "制陶" in self.knowledge and not self._有器("陶罐") \
                and self._数料("土") + self._数料("沙") >= POTTERY_CLAY:
            if world.火相(self.y, self.x) in ("火", "焰"):
                料单 = [(self._取料("土") or self._取料("沙"))
                        for _ in range(POTTERY_CLAY)]
                if rng.random() < 0.5 + 0.5 * self._熟练("制陶"):
                    self.bag.append(Item("陶罐"))
                    self._转化(world, 料单, ITEM_YANG["陶罐"] + 物形阴("陶罐"))
                    self._涨熟练("制陶")
                    report(tick, (self.y, self.x),
                           f"{self.name} 和泥成坯，就火烧成一只陶罐（因：制陶之技+火边烧制）",
                           kind="制陶", actor=self.name)
                else:
                    self._转化(world, 料单, 0.0)     # 裂坯：土之结散归炁场
                    self._耗阳(0.3)
                    report(tick, (self.y, self.x),
                           f"{self.name} 烧陶裂了坯，费了些土（因：手艺生疏）",
                           kind="制陶败", actor=self.name)
                return True
            # 无火或火弱（星火难烧陶）：自钻新火，或赴他处之旺火
            if "取火" in self.knowledge and not world.raining_on(self.y, self.x) \
                    and any(self._数料(k) >= 1 for k in ("木", "茅草", "藤")):
                return self._钻木(world, tick, report, rng)
            if self._赴火(world, tick, rng):
                return True
        # 缝纫：以藤为线、以骨为针——寒衣御寒，骨饰传情
        if "缝纫" in self.knowledge:
            if not self._有器("寒衣") and self._数料("藤") >= SEW_TICKS_VINE \
                    and self._数料("骨") >= 1:
                料单 = [self._取料("藤"), self._取料("藤"), self._取料("骨")]
                if rng.random() < 0.5 + 0.5 * self._熟练("缝纫"):
                    self.bag.append(Item("寒衣"))
                    self._转化(world, 料单, ITEM_YANG["寒衣"] + 物形阴("寒衣"))
                    self._涨熟练("缝纫")
                    report(tick, (self.y, self.x),
                           f"{self.name} 以藤为线、以骨为针，缝成一件寒衣（因：寒夜受冻+缝纫之技）",
                           kind="缝纫", actor=self.name)
                else:
                    self._转化(world, 料单, 0.0)     # 走针：藤骨之结散归炁场
                    self._耗阳(0.3)
                    report(tick, (self.y, self.x),
                           f"{self.name} 缝衣走了针，费了些藤骨（因：手艺生疏）",
                           kind="缝纫败", actor=self.name)
                return True
        # 琢饰：琢骨成饰（有美石则镶之）。缝纫者缀之，制器者亦可琢之——
        # 饰品无实用价值，只有社会价值：馈赠之重、身份之始
        if ("缝纫" in self.knowledge or "制器" in self.knowledge) \
                and not self._有器("骨饰") and self.affinity > 0.4 \
                and self._数料("骨") >= 1:
            料单 = [self._取料("骨")]
            美石 = self._取料("美石")
            镶 = 美石 is not None
            if 镶:
                料单.append(美石)
            if rng.random() < 0.5 + 0.5 * max(self._熟练("缝纫"), self._熟练("制器")):
                self.bag.append(Item("骨饰"))
                self._转化(world, 料单, ITEM_YANG["骨饰"] + 物形阴("骨饰"))
                self._涨熟练("缝纫")
                report(tick, (self.y, self.x),
                       f"{self.name} {'琢骨镶石' if 镶 else '琢骨'}，成一枚骨饰（因：爱美之心+闲工）",
                       kind="琢饰", actor=self.name)
            else:
                self._转化(world, 料单, 0.0)     # 崩角：骨石之结散归炁场
                self._耗阳(0.3)
                report(tick, (self.y, self.x),
                       f"{self.name} 琢饰崩了角，费了些骨石（因：手艺生疏）",
                       kind="缝纫败", actor=self.name)
            return True
        # 烹饪：有生食 + 近火——守着火堆掂量生食，一日积一分，忽悟可炙之而食
        生 = next((it for it in self.bag if it.类型 in RAW_KINDS), None)
        if 生 is not None \
                and (world.fire_near(self.y, self.x) is not None or self._known_fires):
            self._积学("烹饪", 4.0, tick, report,
                       "守着火堆，忽悟生食可炙", "火在侧")
        # 野炊：带着生食、会烹饪、会取火、有木却无火 → 就地生火
        if "烹饪" in self.knowledge and "取火" in self.knowledge \
                and any(it.类型 in RAW_KINDS for it in self.bag) \
                and world.fire_near(self.y, self.x) is None \
                and self._数料("木") >= 1 and not world.raining_on(self.y, self.x):
            if self._钻木(world, tick, report, rng):
                return True
        if "烹饪" in self.knowledge and self._烹制(world, tick, report, rng):
            return True
        # 畜牧：知法 → 建栏 → 驯化 → 照料收产
        if "畜牧" in self.knowledge:
            if self._畜牧事(world, tick, report, rng):
                return True
        return False

    def _备料(self, world: World, tick: int, report, rng) -> bool:
        """为百工备料：算出缺什么（木/石/藤），采眼见最近者。"""
        缺 = set()
        if "制器" in self.knowledge:
            for 器 in TOOL_PRIORITY:
                if self._有器(器):
                    continue
                for k, v in RECIPES[器].items():
                    if self._数料(k) < v:
                        缺.add(k)
                break
        if "取火" in self.knowledge and self._数料("木") < 1 \
                and world.fire_near(self.y, self.x) is None:
            缺.add("木")
        if "畜牧" in self.knowledge and self._数料("木") < 2 \
                and not any(f.主人 == self.name for f in world.fences):
            缺.add("木")
        if "制陶" in self.knowledge and not self._有器("陶罐") \
                and self._数料("土") < POTTERY_CLAY:
            缺.add("土")
        if "缝纫" in self.knowledge and not self._有器("寒衣"):
            if self._数料("藤") < SEW_TICKS_VINE:
                缺.add("藤")
            if self._数料("骨") < 1:
                缺.add("骨")
        if not 缺:
            return False
        r = self._感知半径(tick)
        候选 = []
        if "木" in 缺:
            for tree in world.trees:
                d = self._切比(self.y, self.x, tree.y, tree.x)
                if d <= r and tree.阳 >= 30:
                    候选.append((d, tree.y, tree.x, "木"))
        if "骨" in 缺:
            for c in world.carrions:
                d = self._切比(self.y, self.x, c.y, c.x)
                if d <= r and c.骨 > 0:
                    候选.append((d, c.y, c.x, "骨"))
        for dy in range(-r, r + 1):
            for dx in range(-r, r + 1):
                ny, nx = self.y + dy, self.x + dx
                if not world.in_bounds(ny, nx):
                    continue
                if "石" in 缺 and world.height[ny, nx] >= 6.5 and world.stone[ny, nx] >= 1.0:
                    候选.append((max(abs(dy), abs(dx)), ny, nx, "石"))
                if "藤" in 缺 and world.vine[ny, nx] >= 1.0:
                    候选.append((max(abs(dy), abs(dx)), ny, nx, "藤"))
                if "土" in 缺 and world.moisture[ny, nx] > 0.45 and world.water[ny, nx] < 1.5:
                    候选.append((max(abs(dy), abs(dx)), ny, nx, "土"))
        if not 候选:
            return False
        候选.sort()
        d, ty, tx, 料 = 候选[0]
        if d <= 1:
            return self._采集资源(world, tick, report, rng)
        self._走向(world, ty, tx, rng)
        return True

    def _畜牧事(self, world: World, tick: int, report, rng) -> bool:
        """圈养之道：先立栏，再驯化温顺者，而后收蛋挤奶。"""
        我栏 = next((f for f in world.fences if f.主人 == self.name), None)
        if 我栏 is None:
            # 建栏于栖身所旁：需木二
            if self._数料("木") >= 2:
                料单 = [self._取料("木"), self._取料("木")]
                hy, hx = self._栖身所()
                for dy in (0, 1, -1, 2, -2):
                    for dx in (0, 1, -1, 2, -2):
                        ny, nx = hy + dy, hx + dx
                        if world.in_bounds(ny, nx) and world.water[ny, nx] < 1.0 \
                                and world.building_at(ny, nx) is None:
                            world.fences.append(Fence(ny, nx, self.name))
                            self._转化(world, 料单, 60.0 + YIN_FENCE)   # 木之结化栏之结
                            report(tick, (ny, nx),
                                   f"{self.name} 立起一圈围栏（因：畜牧之志+木料齐备）",
                                   kind="建栏", actor=self.name)
                            return True
            return False
        我畜 = [a for a in world.animals if a.驯主 == self.name]
        # 收蛋挤奶
        for a in 我畜:
            if a.产物念 > 0:
                continue
            p = BEASTS[a.种类]
            if abs(a.y - self.y) > 1 or abs(a.x - self.x) > 1:
                continue
            if a.种类 == "鸡":
                self._得物(world, "蛋")     # 鸡之所产：泵所养之生物质入链
                a.产物念 = p["蛋期"]
                self._涨熟练("畜牧")
                report(tick, (self.y, self.x),
                       f"{self.name} 从鸡窝里拾了一枚蛋（因：畜牧之劳）",
                       kind="收蛋", actor=self.name)
                return True
            self._得物(world, "奶")         # 畜之所产：泵所养之生物质入链
            a.产物念 = p["奶期"]
            self._涨熟练("畜牧")
            report(tick, (self.y, self.x),
                   f"{self.name} 挤了一{a.种类}奶（因：畜牧之劳）",
                   kind="挤奶", actor=self.name)
            return True
        # 驯化：围栏旁看见温顺野畜，试收之
        if len(我畜) < 4:
            for a in world.animals:
                if a.驯化:
                    continue
                if abs(a.y - self.y) > 1 or abs(a.x - self.x) > 1:
                    continue
                if abs(a.y - 我栏.y) + abs(a.x - 我栏.x) > 8:
                    continue    # 太远的畜，赶不回来
                if rng.random() < TAME_CHANCE[a.种类] * (0.7 + self._熟练("畜牧")):
                    a.驯主 = self.name
                    a.栏位 = (我栏.y, 我栏.x)
                    self._涨熟练("畜牧")
                    report(tick, (self.y, self.x),
                           f"{self.name} 驯化了一只{a.种类}入栏（因：畜牧之法+耐心）",
                           kind="驯化", actor=self.name)
                    return True
        return False
