"""灵体层 · 生计系统（M2 组件化拆分：自 spirit.py 整段搬运，行为不变）"""

from .base import *

class 生计Mixin:
    """灵之生计诸行。"""

    # ── 一·观察 ─────────────────────────────

    def _区域键(self) -> str:
        return f"{self.y // REGION_SIZE},{self.x // REGION_SIZE}"

    def _区域有记忆(self) -> bool:
        key = self._区域键()
        return any(m.类别 == "区域" and m.对象 == key and m.权重 >= MEMORY_FORGET
                   for m in self.memories)


    # ── 二·觅食与饮水 ────────────────────────

    def _觅食(self, world: World, spirits: list, tick: int, report, rng):
        """求生进食优先级：随身食物 > 家中仓储 > 求助借贷 > 渔猎 > 草籽。"""
        食 = self._袋中食()
        if 食 is None and self.hut is not None \
                and any(it.类型 in FOOD_YANG for it in self.hut.仓储):
            # 家有存粮：在家则取，在外则归——寒季储粮是生存主线
            if (self.y, self.x) == (self.hut.y, self.hut.x):
                it = next(it for it in self.hut.仓储 if it.类型 in FOOD_YANG)
                self.hut.仓储.remove(it)
                self.bag.append(it)
                食 = self._袋中食()
            else:
                self._走向(world, self.hut.y, self.hut.x, rng)
                return
        if 食 is not None:
            # 知烹饪而带生食：忍一口饿也要炙熟——无火则生火，无木则采木
            if 食.类型 in RAW_KINDS and "烹饪" in self.knowledge and self.yang > 25.0:
                if world.fire_near(self.y, self.x) is None and not self._known_fires \
                        and "取火" in self.knowledge:
                    if self._数料("木") >= 1:
                        if not world.raining_on(self.y, self.x):
                            self._钻木(world, tick, report, rng)
                    else:
                        r = self._感知半径(tick)
                        树 = [(self._切比(self.y, self.x, t0.y, t0.x), t0.y, t0.x)
                              for t0 in world.trees
                              if self._切比(self.y, self.x, t0.y, t0.x) <= r and t0.阳 >= 30]
                        if 树:
                            树.sort()
                            self._走向(world, 树[0][1], 树[0][2], rng)
                            return
                if self._烹制(world, tick, report, rng):
                    食 = self._袋中食()   # 熟食出炉，拣最好的吃
                    if 食 is None:
                        return
            # 取火成功时的"得火即炙"可能已把生食变成了熟食——入口前必须重检行囊
            食 = self._袋中食()
            if 食 is None:
                return
            self._吃(world, 食, tick, report, rng)
            return
        # 困极则开口：向身旁相熟且有盈余者求助（对方借出，我记债）
        if self.yang < 32.0:
            for b in self._邻居们(spirits):
                if self.relation(b.name) < 0.15 or b.relation(self.name) < 0.15:
                    continue
                if b.yang < 48.0 or b.name in self.debts:
                    continue
                余食 = next((it for it in b.bag if it.类型 in FOOD_YANG), None)
                if 余食 is not None:
                    b.bag.remove(余食)
                    self.bag.append(余食)
                    借物 = 余食.类型
                else:
                    转阳(world, b, self, 8.0)      # 赊一口阳气：灵与灵之间的转移
                    借物 = "口粮"
                b.credits.setdefault(self.name, []).append((借物, tick))
                self.debts.setdefault(b.name, []).append((借物, tick))
                b.remember(f"我借给 {self.name} 一份{借物}", "助人", self.name, 0.50, tick)
                self.remember(f"{b.name} 借给我一份{借物}", "受助", b.name, 0.65, tick)
                report(tick, (self.y, self.x),
                       f"{self.name} 向 {b.name} 开口求助，借得{借物}（因：饥困+相熟）",
                       kind="借贷", actor=b.name, target=self.name)
                return
        # 渔猎：近水有鱼则渔，近旁有兽则猎
        if self._渔猎(world, tick, report, rng):
            return
        if self._狩猎(world, tick, report, rng):
            return
        if self.known_food:
            ty, tx = min(self.known_food,
                         key=lambda p: abs(p[0] - self.y) + abs(p[1] - self.x))
            if (ty, tx) == (self.y, self.x):
                self._进食(world, tick, report, rng)
            else:
                self._走向(world, ty, tx, rng)
        else:
            self._探索(world, rng)

    def _袋中食(self) -> Item | None:
        """从行囊里拣出此刻最该吃的一口：熟食优先，生食次之。"""
        可食 = [it for it in self.bag if it.类型 in FOOD_YANG]
        if not 可食:
            return None
        可食.sort(key=lambda it: -FOOD_YANG[it.类型])
        return 可食[0]

    def _吃(self, world: World, it: Item, tick: int, report, rng):
        """吃下一份食物：食物之结解开——其阳转入我身（食转，C→B），
        其形阴与我身纳不尽之余归还炁场（物归）。腐食不养人：腐了多少，养分就少多少。
        熟食养人；生食有病患之险。"""
        self.bag.remove(it)
        受 = min(100.0 - self.yang, it.阳)
        self.yang += 受
        world.账.食转 += 受
        world.物归(self.y, self.x, (it.阳 - 受) + 物形阴(it.类型))
        self.stats["进食"] += 1
        # 吃过一口熟食，便想学这手艺——吃一口积一分
        if it.类型 in ("熟肉", "熟鱼"):
            self._积学("烹饪", 12.0, tick, report,
                       "吃了熟食，一心想学这手艺", "熟食之美")
        if it.类型 in RAW_KINDS and rng.random() < RAW_SICK:
            self._耗阳(5.0)     # 病耗亦逸散，就地归还
            self.remember("吃了生冷，腹中绞痛", "病患", None, 0.55, tick)
            report(tick, (self.y, self.x),
                   f"{self.name} 吃了生{it.类型[1:]}，腹中绞痛（因：生食不洁）",
                   kind="生食致病", actor=self.name)
            # 痛定思痛：有人由此想出烹饪
            self._积学("烹饪", 25.0, tick, report,
                       "痛定思痛，想出烹饪之法，以火熟食", "生食致病")

    def _进食(self, world: World, tick: int, report, rng):
        if world.grass[self.y, self.x] >= EAT_GRASS_MIN:
            world.grass[self.y, self.x] = 0.0
            self._泵阳(world, EAT_GRASS_GAIN)     # 采食草木，记日月之泵
            self.mood["希望"] = min(1.0, self.mood["希望"] + 0.1)
            self.mood["疲惫"] = max(0.0, self.mood["疲惫"] - 0.1)
            self.stats["进食"] += 1
            report(tick, (self.y, self.x),
                   f"{self.name} 采食于{world.terrain_name(self.y, self.x)}（因：饥饿）",
                   kind="进食", actor=self.name)
            # 俯身采食，屡见枯而复荣——采一次，积一分稼穑之思
            self._积学("种植", 2.5, tick, report,
                       "俯身采食，忽悟草木可由人种", "观察枯荣")


    # ── 渔猎 ────────────────────────────────

    def _渔猎(self, world: World, tick: int, report, rng) -> bool:
        """近水有鱼则渔。徒手浅水低效，有鱼竿高效。"""
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                ny, nx = self.y + dy, self.x + dx
                if not world.in_bounds(ny, nx):
                    continue
                if world.fish[ny, nx] > 0.4:
                    # 饥时见鱼游——见一回，积一分渔猎之思；日久自成其法
                    if "渔猎" not in self.knowledge:
                        if not self._积学("渔猎", 8.0, tick, report,
                                          "见鱼游于浅水，悟得渔猎之法", "饥饿所迫+久观鱼游"):
                            continue
                    有竿 = self._有器("鱼竿")
                    得手率 = 0.55 * (1.5 if 有竿 else 1.0)
                    if rng.random() < 得手率:
                        world.fish[ny, nx] -= 0.8
                        self._得物(world, "生鱼")      # 渔获：鱼自水域入链，记源C
                        self._涨熟练("渔猎")
                        if 有竿:
                            self._磨损("鱼竿", tick, report)
                        report(tick, (self.y, self.x),
                               f"{self.name} 渔得一尾（因：{'渔竿之利' if 有竿 else '徒手浅水'}）",
                               kind="渔获", actor=self.name)
                    else:
                        self._耗阳(0.2)
                    return True
        return False

    def _狩猎(self, world: World, tick: int, report, rng) -> bool:
        """近旁有兽则猎。鸡易擒，牛难搏；利器助之。"""
        if "渔猎" not in self.knowledge:
            return False
        for a in world.animals:
            if a.驯化:
                continue    # 有主之畜不猎
            d = max(abs(a.y - self.y), abs(a.x - self.x))
            if d > 2:
                continue
            加成 = WEAPON_BONUS.get(self._最佳武器(), 0.0)
            得手 = HUNT_BASE[a.种类] + 加成
            if d == 2:
                得手 *= 0.5    # 隔一步扑猎，胜算减半
            if rng.random() < 得手:
                world.animals.remove(a)
                # 猎杀亦坏灭：余阳与形阴就地归还（倾覆），肉骨归猎手
                world.qi.归还(a.y, a.x, 阳=max(0.0, a.阳),
                              阴=BEAST_FORM_YIN.get(a.种类, 10.0))
                if a.水分 > 0.0:
                    world.water[a.y, a.x] += a.水分 * BODY2FIELD
                肉, 骨 = {"鸡": (2, 1), "羊": (4, 2), "牛": (6, 3)}.get(a.种类, (2, 1))
                world.carrions.append(Carrion(a.y, a.x, 肉, 骨, 名=a.种类))
                self._涨熟练("渔猎")
                if self._最佳武器():
                    self._磨损(self._最佳武器(), tick, report)
                report(tick, (self.y, self.x),
                       f"{self.name} 猎获一头{a.种类}（因：渔猎之技{'+利器' if 加成 else ''}）",
                       kind="狩猎", actor=self.name)
                return True
            # 失手则兽惊而逃
            a.y = int(min(max(a.y + (1 if a.y >= self.y else -1) * 2, 0), world.size - 1))
            a.x = int(min(max(a.x + (1 if a.x >= self.x else -1) * 2, 0), world.size - 1))
            self._耗阳(0.3)
            return True
        return False

    def _找水(self, world: World, tick: int, report, rng):
        # 怀中陶罐有水，先饮罐中——储水以备旱，罐的价值正在于此
        罐 = next((it for it in self.bag if it.类型 == "陶罐" and it.盛水 > 0), None)
        if 罐 is not None:
            取 = min(罐.盛水, 100.0 - self.水分)     # 罐之水入我之躯：罐与身同为水之器
            self.水分 += 取
            罐.盛水 -= 取
            self.stats["饮水"] += 1
            report(tick, (self.y, self.x),
                   f"{self.name} 饮陶罐中所储之水（因：口渴+储水备旱）",
                   kind="饮水", actor=self.name)
            return
        if world.water[self.y, self.x] >= DRINK_MIN:
            self._饮水(world, tick, report, rng)
            self._灌罐(world, report, tick)
            return
        # 立在记忆中的水点上却见了底：亲见枯竭，从心中抹去
        if (self.y, self.x) in self.known_water:
            del self.known_water[(self.y, self.x)]
        # 井与水泽，择近者往
        候选 = []
        for (wy, wx), 凿主 in self._known_wells.items():
            if world.well_at(wy, wx) is not None:
                候选.append((abs(wy - self.y) + abs(wx - self.x), wy, wx, "井"))
        for (wy, wx) in self.known_water:
            候选.append((abs(wy - self.y) + abs(wx - self.x), wy, wx, "泽"))
        if 候选:
            候选.sort()
            d, ty, tx, 类 = 候选[0]
            if d == 0 and 类 == "井":
                if self._汲井(world, tick, report, rng):
                    return
            else:
                self._走向(world, ty, tx, rng)
                return
        # 四野无水：焦渴难耐。渴一日，积一分——低洼之下，九泉之上，或可凿井
        day = tick // TICKS_PER_DAY
        if self._渴_day != day:
            self._渴_day = day
            self.remember("口渴难耐，四野无水", "焦渴", None, 0.35, tick)
            self._积学("凿井", 10.0, tick, report,
                       "望着干渴的大地忽悟：低洼之下或有九泉，可凿井取之", "焦渴难耐")
        self._探索(world, rng)

    def _灌罐(self, world: World, report, tick):
        """饮于水泽时，顺手把空陶罐灌满——罐之水亦自场来，按率结算。"""
        罐 = next((it for it in self.bag if it.类型 == "陶罐" and it.盛水 <= 0), None)
        if 罐 is not None:
            取 = min(60.0 * BODY2FIELD,
                     max(0.0, float(world.water[self.y, self.x]) - DRINK_KEEP))
            world.water[self.y, self.x] -= 取
            罐.盛水 = 取 / BODY2FIELD
            if 罐.盛水 > 0:
                report(tick, (self.y, self.x),
                       f"{self.name} 把陶罐灌满了水（因：储水备旱）",
                       kind="灌水", actor=self.name)

    def _汲井(self, world: World, tick: int, report, rng) -> bool:
        """在井边汲水。井水取自九泉；井淤则淘之，井枯则徒叹。"""
        well = world.well_at(self.y, self.x)
        if well is None:
            self._known_wells.pop((self.y, self.x), None)
            return False
        st = world.汲井(well, 需=(100.0 - self.水分) * BODY2FIELD)
        if st == "活":
            self.水分 = 100.0
            self.stats["饮水"] += 1
            self._灌罐(world, report, tick)
            report(tick, (self.y, self.x),
                   f"{self.name} 汲井水而饮（因：口渴+井水取自九泉）",
                   kind="汲水", actor=self.name)
            return True
        if st == "淤" and "凿井" in self.knowledge:
            # 淘浚：俯身清淤，井复其活
            well.阳 = min(60.0, well.阳 + 35.0)
            self._耗阳(0.5)
            self._涨熟练("凿井")
            report(tick, (self.y, self.x),
                   f"{self.name} 淘浚了这口淤井，浊去清来（因：井淤难汲+凿井之技）",
                   kind="淘浚", actor=self.name)
            return True
        # 枯：九泉暂涸，井也打不出水来
        self.remember("井水枯了，九泉暂涸", "焦渴", None, 0.30, tick)
        self._known_wells.pop((self.y, self.x), None)
        return False

    def _饮水(self, world: World, tick: int, report, rng=None):
        """饮于泽：场之水入我之躯——只是转移，不是消失（水过身体，总量不变）。"""
        需 = (100.0 - self.水分) * BODY2FIELD
        取 = min(需, max(0.0, float(world.water[self.y, self.x]) - DRINK_KEEP))
        world.water[self.y, self.x] -= 取
        self.水分 += 取 / BODY2FIELD
        self.stats["饮水"] += 1
        report(tick, (self.y, self.x),
               f"{self.name} 饮于水泽（因：口渴）",
               kind="饮水", actor=self.name)
        # 储水之需：俯身饮水时常想——若能把水带走就好了。烧土为罐之思，由此日积
        if rng is not None:
            self._积学("制陶", 8.0, tick, report,
                       "俯身饮水，忽想若能把水带走该多好——可烧土为罐", "储水之需")

    def _探索(self, world: World, rng):
        """走向最陌生的方向：无已知食物/水源时的求生探索。"""
        候选 = []
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if dy == 0 and dx == 0:
                    continue
                ny, nx = self.y + dy, self.x + dx
                if world.in_bounds(ny, nx) and world.water[ny, nx] < 1.8:
                    key = f"{ny // REGION_SIZE},{nx // REGION_SIZE}"
                    熟 = any(m.类别 == "区域" and m.对象 == key for m in self.memories)
                    候选.append((0 if not 熟 else 1, rng.random(), ny, nx))
        if 候选:
            候选.sort()
            _, _, ny, nx = 候选[0]
            self._移动到(world, ny, nx)

    def _游荡(self, world: World, tick: int, report, rng, spirits: list = ()):
        self.training = False
        # 路过浅水且口渴，顺手饮之
        if world.water[self.y, self.x] >= DRINK_MIN and self.水分 < 70:
            self._饮水(world, tick, report, rng)
            return
        # 见可用之材则采：遗物、尸骸取肉取骨，树可伐木，高地采石，泽畔采藤
        if self._采集资源(world, tick, report, rng):
            return
        # 亲而聚之：附近有相悦之人而自己无所事事，便走过去作伴——佳偶由此而成
        if spirits and rng.random() < 0.25:
            相悦 = [s for s in spirits if s is not self and s.alive
                    and s._已成年 and self._感知到(s, tick)
                    and self.relation(s.name) >= 0.8 and s.relation(self.name) >= 0.5
                    and self._切比(self.y, self.x, s.y, s.x) > 1]
            if 相悦:
                b = min(相悦, key=lambda s: self._切比(self.y, self.x, s.y, s.x))
                self._走向(world, b.y, b.x, rng)
                return
        r = rng.random()
        if r < 0.30:
            # 歇脚：疲惫稍复，希望稍长
            self.mood["疲惫"] = max(0.0, self.mood["疲惫"] - 0.05)
            self.mood["希望"] = min(1.0, self.mood["希望"] + 0.02)
        elif r < 0.45 and world.grass[self.y, self.x] >= 0.5 and self.yang < 65:
            self._进食(world, tick, report, rng)   # 顺手采食，不为求生为口福
        else:
            步 = [(self.y + dy, self.x + dx)
                  for dy in (-1, 0, 1) for dx in (-1, 0, 1)
                  if (dy or dx) and world.in_bounds(self.y + dy, self.x + dx)
                  and world.water[self.y + dy, self.x + dx] < 1.8]
            if 步:
                ny, nx = 步[rng.randrange(len(步))]
                self._移动到(world, ny, nx)

    def _采集资源(self, world: World, tick: int, report, rng) -> bool:
        """采集眼前之材：遗物、尸骸、树木、石料、藤蔓。采石伐木之时，悟性高者悟出制器。
        行囊有容量：满则不再拾取。"""
        if len(self.bag) >= BAG_CAP:
            return False
        # 无主遗物：物是人非，拾而得之；若识其主，心头一沉
        for r in list(world.relics):
            if abs(r["y"] - self.y) > 1 or abs(r["x"] - self.x) > 1:
                continue
            for it in r["物"]:
                self.bag.append(it)
            world.relics.remove(r)
            识主 = any(m.对象 == r["名"] for m in self.memories)
            if 识主:
                self.remember(f"拾得故人 {r['名']} 的遗物", "悼念", r["名"], 0.50, tick)
            report(tick, (self.y, self.x),
                   f"{self.name} 拾得了 {r['名']} 的遗物（因：{'物是人非' if 识主 else '无主之物'}）",
                   kind="拾遗", actor=self.name, target=r["名"])
            return True
        # 尸骸取肉取骨（有石刀则全收；徒手拆骨一根——骨要那么多做甚，够做针饰即可）
        for c in list(world.carrions):
            if abs(c.y - self.y) > 1 or abs(c.x - self.x) > 1:
                continue
            刀 = self._有器("石刀")
            肉 = c.肉 if 刀 else max(1, c.肉 - 1)
            for _ in range(肉):
                self._得物(world, "生肉")       # 尸为泵所养之生物质，肢解入链记源C
            for _ in range(c.骨 if 刀 else (1 if c.骨 and self._数料("骨") < 2
                                            and ({"缝纫", "制器"} & self.knowledge) else 0)):
                self._得物(world, "骨")
            world.carrions.remove(c)
            report(tick, (self.y, self.x),
                   f"{self.name} 肢解了{c.名}的尸骸，得肉{肉}（因：{'石刀之利' if 刀 else '徒手可及'}）",
                   kind="屠宰", actor=self.name)
            return True
        # 采果：果树暖季结实，近者可采——木之实，泵所养之生物质入链
        for t in world.trees:
            if not t.果树 or t.果数 <= 0:
                continue
            if abs(t.y - self.y) > 1 or abs(t.x - self.x) > 1:
                continue
            t.果数 -= 1
            self._得物(world, "果")
            report(tick, (self.y, self.x),
                   f"{self.name} 从果树上采了一枚果（因：暖季结实+伸手可及）",
                   kind="采果", actor=self.name)
            return True
        # 伐木
        for tree in world.trees:
            if abs(tree.y - self.y) > 1 or abs(tree.x - self.x) > 1:
                continue
            if tree.阳 < 30:
                continue
            斧 = self._有器("石斧")
            tree.阳 -= 40 if 斧 else 55
            for _ in range(CHOP_YIELD + (1 if 斧 else 0)):
                self._得物(world, "木")         # 伐木得薪：木自生物质入链，记源C
            if 斧:
                self._磨损("石斧", tick, report)
            if tree.阳 <= 0:
                world.trees.remove(tree)
            report(tick, (self.y, self.x),
                   f"{self.name} 伐木得薪（因：{'石斧之利' if 斧 else '徒手攀折'}）",
                   kind="伐木", actor=self.name)
            self._积学("制器", 10.0, tick, report,
                       "伐木时忽有所悟：木石可成器，是为制器", "劳作日久")
            return True
        # 采石（高地）：石中偶有含金的矿石与美者——金出石中，美石是饰品的料
        if world.height[self.y, self.x] >= 6.5 and world.stone[self.y, self.x] >= 1.0:
            world.stone[self.y, self.x] -= 1.0
            r石 = rng.random()
            if r石 < 0.12 and self._数料("矿石") < 3:
                self._得物(world, "矿石")
                report(tick, (self.y, self.x),
                       f"{self.name} 采得一块矿石（因：高地有石+石中含金）",
                       kind="采石", actor=self.name)
            elif r石 < 0.27 and self._数料("美石") < 2:
                self._得物(world, "美石")
                report(tick, (self.y, self.x),
                       f"{self.name} 采得一枚美石（因：高地有石+石中美者）",
                       kind="采石", actor=self.name)
            else:
                self._得物(world, "石")
                report(tick, (self.y, self.x),
                       f"{self.name} 采得一块石头（因：高地有石）",
                       kind="采石", actor=self.name)
            self._积学("制器", 10.0, tick, report,
                       "采石时忽有所悟：木石可成器，是为制器", "劳作日久")
            return True
        # 采藤（水泽边）
        if world.vine[self.y, self.x] >= 1.0:
            world.vine[self.y, self.x] -= 1.0
            self._得物(world, "藤")
            report(tick, (self.y, self.x),
                   f"{self.name} 采得一把藤蔓（因：泽畔有藤）",
                   kind="采藤", actor=self.name)
            return True
        # 掘土（泽畔河泥，制陶之料）：掘得何物，取决于土相——泥与土得土，沙处得沙
        if "制陶" in self.knowledge and self._数料("土") + self._数料("沙") < POTTERY_CLAY \
                and world.moisture[self.y, self.x] > 0.45 and world.water[self.y, self.x] < 1.5:
            相 = world.土相(self.y, self.x)
            self._得物(world, "沙" if 相 == "沙" else "土")
            report(tick, (self.y, self.x),
                   f"{self.name} 掘取河泥得{'沙' if 相 == '沙' else '土'}（因：制陶之需+其地为{相}）",
                   kind="采土", actor=self.name)
            return True
        # 采贝：水泽边俯拾，低概率得美贝——天然稀缺，贝币之雏形
        if world.moisture[self.y, self.x] > 0.45 and world.water[self.y, self.x] < 1.5 \
                and self._数料("美贝") < 4 and rng.random() < 0.010:
            self._得物(world, "美贝")
            report(tick, (self.y, self.x),
                   f"{self.name} 拾得一枚美贝（因：水泽俯拾+天然稀缺）",
                   kind="得贝", actor=self.name)
            return True
        # 见他人栏中畜、近温顺野畜而心有所动——近观一回，积一分圈养之思
        if "畜牧" not in self.knowledge:
            for a in world.animals:
                if abs(a.y - self.y) > 2 or abs(a.x - self.x) > 2:
                    continue
                驯见 = a.驯化 and a.驯主 != self.name
                亲畜 = a.种类 == "鸡"
                if 驯见 or 亲畜:
                    if self._积学("畜牧", 7.0, tick, report,
                                  f"见{'人圈养' + a.种类 if 驯见 else '鸡雏驯顺'}，悟得畜牧之法",
                                  "近观温顺禽兽+日久心动"):
                        return True
                    break   # 每念只就最近一头禽兽心有所动
        return False
