"""灵体层 · 争斗系统（M2 组件化拆分：自 spirit.py 整段搬运，行为不变）"""

from .base import *

class 争斗Mixin:
    """灵之争斗诸行。"""

    # ── 三·威胁与逃避 ────────────────────────

    def _邻居们(self, spirits: list) -> list:
        return [s for s in spirits if s is not self and s.alive
                and abs(s.y - self.y) <= 1 and abs(s.x - self.x) <= 1]

    def _身边威胁(self, spirits: list):
        """相邻、比我强、且抢过我的人。"""
        for s in self._邻居们(spirits):
            if s.strength > self.strength and self.remembers_robbery_by(s.name):
                return s
        return None

    def _逃离(self, threat, world: World, rng):
        """躲开威胁：朝远离它的方向退一步。"""
        候选 = []
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                ny, nx = self.y + dy, self.x + dx
                if world.in_bounds(ny, nx) and world.water[ny, nx] < 1.8:
                    d_new = abs(ny - threat.y) + abs(nx - threat.x)
                    候选.append((-d_new, rng.random(), ny, nx))
        if 候选:
            候选.sort()
            _, _, ny, nx = 候选[0]
            self._移动到(world, ny, nx)


    # ── 五·抢夺（含目睹）─────────────────────

    def _尝试抢夺(self, world: World, spirits: list, tick: int, report, rng) -> bool:
        if tick - self._last_rob < ROB_COOLDOWN:
            return False
        弱者 = [s for s in self._邻居们(spirits) if s.strength < self.strength * ROB_WEAKER
                and getattr(s, "_已成年", True)]   # 稚子无辜，不劫幼童
        if not 弱者 or rng.random() > self.aggr * ROB_CHANCE:
            return False
        self._last_rob = tick
        猎物 = min(弱者, key=lambda s: s.strength)
        amount = min(11.0, 3.0 + 猎物.yang * 0.18)   # 抢夺是夺食，不是索命
        转阳(world, 猎物, self, amount, 率=0.8)      # 夺来之阳沿途有耗，耗者归还炁场
        # 行囊中的食物与利器也一并易手（武器可被抢夺、遗留、传承）
        可夺 = [it for it in 猎物.bag if it.类型 in FOOD_YANG] \
            or [it for it in 猎物.bag if it.类型 in WEAPON_BONUS]
        夺得 = None
        if 可夺:
            夺得 = max(可夺, key=lambda it: ITEM_VALUE.get(it.类型, 1))
            猎物.bag.remove(夺得)
            self.bag.append(夺得)

        # 被抢者：永存记忆 + 愤怒激增 + 目标链（受辱 → 变强 → 报复）+ 心态漂移
        猎物.remember(f"{self.name} 抢了我", "被抢", self.name, 0.90, tick)
        猎物.mood["愤怒"] = 1.0
        猎物.mood["恐惧"] = min(1.0, 猎物.mood["恐惧"] + 0.3)
        猎物.pressure += 0.55
        猎物.want("变强")
        猎物.want(f"报复:{self.name}")
        猎物._漂移("caution", DRIFT_CAUTION_ROBBED, tick, report, "屡遭抢夺")
        # 抢夺者自己记一笔——他也记住了这个人
        self.remember(f"我抢过 {猎物.name}", "抢人", 猎物.name, 0.50, tick)

        world.add_mark("刻痕", self.y, self.x, TICKS_PER_DAY // 2)
        夜袭 = "夜袭：" if is_night(tick) else ""
        喝 = f" {猎物.name}：{rng.choice(_QUOTES_ROBBED)}" if rng.random() < 0.4 else ""
        物注 = f"，夺去{夺得.类型}" if 夺得 is not None else ""
        report(tick, (self.y, self.x),
               f"{夜袭}{self.name} 抢夺了 {猎物.name} 的食物{物注}（因：饥饿+好斗）{喝}",
               kind="抢夺", actor=self.name, target=猎物.name)
        self._旁观者记(world, spirits, tick, 猎物)
        猎物._死否(world, tick, report, "被抢伤重", spirits)
        return True

    def _旁观者记(self, world: World, spirits: list, tick: int, 猎物):
        """目睹：感知半径内看见抢夺者，记下不义；对受害者心生同情。"""
        for w in spirits:
            if w is self or w is 猎物 or not w.alive:
                continue
            if w._切比(w.y, w.x, self.y, self.x) > w._感知半径(tick):
                continue
            w.remember(f"目睹 {self.name} 行凶", "目睹", self.name, 0.50, tick)
            w.remember(f"见 {猎物.name} 遭人抢夺", "同情", 猎物.name, 0.40, tick)


    # ── 六·报复（凭记忆搜寻，无全局追踪）──────

    def _追击报复(self, world: World, spirits: list, tick: int, report, rng) -> bool:
        for goal in list(self.goals):
            if not goal.startswith("报复:"):
                continue
            tname = goal.split(":", 1)[1]
            target = next((s for s in spirits if s.alive and s.name == tname), None)
            ls = self._last_seen.get(tname)
            if target is None:
                # 不知其死活：久寻不遇（逾两日）方叹一句恩怨成空
                if ls is None or tick - ls[2] > 2 * TICKS_PER_DAY:
                    self.drop_goal(goal)
                    self.remember(f"{tname} 已不知踪迹，恩怨成空", "恩怨", tname, 0.60, tick)
                continue
            # 力量门槛：以最后一次亲见的力量为凭
            known_strength = ls[3] if ls else 14.0
            if self.strength < known_strength * 1.1:
                continue    # 力量未成，继续积蓄（落入锻炼分支）
            if self._感知到(target, tick):
                # 仇人就在眼前：逼近，相邻则开打
                if abs(target.y - self.y) <= 1 and abs(target.x - self.x) <= 1:
                    report(tick, (self.y, self.x),
                           f"{self.name} 寻见了 {target.name}，新仇旧恨一起算（因：受辱铭记+踏破铁鞋）",
                           kind="报复", actor=self.name, target=tname)
                    self._战斗(target, world, spirits, tick, report, rng, 报复=goal)
                else:
                    self._走向(world, target.y, target.x, rng)
                return True
            if ls is not None:
                # 只记得最后见到仇人的地方：前往该处；不在，则沿记忆搜寻
                if (self.y, self.x) == (ls[0], ls[1]):
                    self._探索(world, rng)
                else:
                    self._走向(world, ls[0], ls[1], rng)
                return True
            self._探索(world, rng)
            return True
        return False


    # ── 七·庇护：目睹好友遭劫，挺身而出 ───────

    def _尝试庇护(self, world: World, spirits: list, tick: int, report, rng) -> bool:
        if self.caution >= 0.5:
            return False    # 谨慎者多一事不如少一事
        新目睹 = [m for m in self.memories
                  if m.类别 == "目睹" and tick - m.念戳 <= WITNESS_FRESH]
        if not 新目睹:
            return False
        for m1 in 新目睹:
            robber = next((s for s in spirits if s.alive and s.name == m1.对象), None)
            if robber is None or not self._感知到(robber, tick):
                continue
            # 受害者须是我的好友
            受害好友 = any(m2.类别 == "同情" and tick - m2.念戳 <= WITNESS_FRESH
                          and self.relation(m2.对象) >= FRIEND_REL
                          for m2 in self.memories)
            if not 受害好友 or self.strength < robber.strength:
                continue
            victim = next((m2.对象 for m2 in self.memories
                           if m2.类别 == "同情" and tick - m2.念戳 <= WITNESS_FRESH
                           and self.relation(m2.对象) >= FRIEND_REL), None)
            report(tick, (self.y, self.x),
                   f"{self.name} 出手护下 {victim}，拦在 {robber.name} 面前"
                   f"{rng.choice(_QUOTES_PROTECT)}（因：目睹不义+故交遭劫）",
                   kind="庇护", actor=self.name, target=victim)
            self._战斗(robber, world, spirits, tick, report, rng, 报复=None)
            # 无论胜负，受害者都记住了这个挺身而出的人
            受护者 = next((s for s in spirits if s.alive and s.name == victim), None)
            if 受护者 is not None:
                胜 = robber.yang < self.yang  # 粗略：战后余阳高者占优
                受护者.remember(f"{self.name} 护过我", "受护", self.name,
                               0.80 if 胜 else 0.65, tick)
            return True
        return False


    # ── 临界涌现：阳极则反 ───────────────────

    def _涌现(self, world: World, spirits: list, tick: int, report, rng):
        """压力溃堤：谨慎者暴起反击，好斗者崩溃逃跑。"""
        if self.aggr > 0.6:
            # 好斗者崩溃：平日里越悍，溃时越狼狈
            self.mood["恐惧"] = 1.0
            self.pressure = 0.4
            threat = self._身边威胁(spirits)
            if threat is not None:
                self._逃离(threat, world, rng)
            report(tick, (self.y, self.x),
                   f"【涌现·阳极则反】{self.name} 压力溃堤，崩溃逃跑（因：威胁环伺，压力临界）",
                   kind="涌现", actor=self.name)
            return
        # 谨慎者暴起：不计强弱，向抢过自己的人挥拳
        仇人 = [s for s in self._邻居们(spirits) if self.remembers_robbery_by(s.name)]
        if 仇人:
            target = 仇人[0]
            report(tick, (self.y, self.x),
                   f"【涌现·阳极则反】{self.name} 忍无可忍，暴起反击 {target.name}（因：受辱积怨，压力临界）",
                   kind="涌现反击", actor=self.name, target=target.name)
            self.pressure = 0.35
            self._战斗(target, world, spirits, tick, report, rng, 报复=None)
        else:
            # 仇人不在眼前，压着怒火去最后见到他的地方找
            self.pressure = 0.6
            仇名 = next((m.对象 for m in self.memories if m.类别 == "被抢"), None)
            ls = self._last_seen.get(仇名) if 仇名 else None
            if ls is not None:
                self._走向(world, ls[0], ls[1], rng)


    # ── 战斗 ────────────────────────────────

    def _战斗(self, target, world: World, spirits: list, tick: int, report, rng, 报复):
        """力量对比定胜负，武器加算其中；败者阳大损，存活则再添受辱记忆。"""
        我武 = WEAPON_BONUS.get(self._最佳武器(), 0.0)
        彼武 = WEAPON_BONUS.get(target._最佳武器(), 0.0)
        pa = self.strength * (1.0 + 我武) * rng.uniform(0.9, 1.1)
        pd = target.strength * (1.0 + 彼武) * rng.uniform(0.9, 1.1)
        胜, 败 = (self, target) if pa >= pd else (target, self)
        败._耗阳(rng.uniform(12.0, 20.0))   # 分出高下，不必见生死；搏耗之阳就地归还
        胜._耗阳(rng.uniform(2.0, 5.0))
        败._斗伤念 = tick     # 战斗负伤之据：横死无回光（v8-P0D·D1）
        胜._斗伤念 = tick

        world.add_mark("刻痕", self.y, self.x, TICKS_PER_DAY // 2)
        report(tick, (self.y, self.x),
               f"{胜.name} 与 {败.name} 相斗，{胜.name} 胜（因：{'力量已成' if 胜 is self and 报复 else '力量悬殊'}）",
               kind="战斗", actor=胜.name, target=败.name)

        # 旁观者亦看见打斗：行凶之名，又多一人记得
        for w in spirits:
            if w is self or w is target or not w.alive:
                continue
            if w._切比(w.y, w.x, self.y, self.x) <= w._感知半径(tick):
                w.remember(f"目睹 {胜.name} 与 {败.name} 相斗", "目睹", 胜.name, 0.40, tick)

        if 败._死否(world, tick, report, "伤重不治", spirits):
            pass
        elif 报复 is not None and 胜 is self and 败.alive \
                and rng.random() < 败.affinity * 0.5 + 败.caution * 0.3:
            # 恩怨两清：被复仇者打垮之后，有人认了——债到此为止，不再冤冤相报
            败.remember(f"我与 {胜.name} 的恩怨已了", "两清", 胜.name, 0.50, tick)
            败.mood["恐惧"] = min(1.0, 败.mood["恐惧"] + 0.2)
            report(tick, (self.y, self.x),
                   f"{败.name} 认了：与 {胜.name} 的恩怨到此为止（因：打也打了+冤冤相报何时了）",
                   kind="两清", actor=败.name, target=胜.name)
        else:
            # 败者受辱：永存记忆，也可能长出他自己的目标链
            败.remember(f"{胜.name} 打垮了我", "受辱", 胜.name, 0.88, tick)
            败.pressure += 0.45
            败.mood["恐惧"] = min(1.0, 败.mood["恐惧"] + 0.4)
            败.mood["愤怒"] = min(1.0, 败.mood["愤怒"] + 0.4)
            败.want("变强")
            败.want(f"报复:{胜.name}")

        if 胜 is self and 报复 is not None:
            # 大仇得报：目标链闭合；性好斗者由此更悍
            self.remember(f"我终于报复了 {target.name}", "报仇", target.name, 0.92, tick)
            self.drop_goal(报复)
            self.mood["愤怒"] = 0.2
            self.mood["希望"] = min(1.0, self.mood["希望"] + 0.3)
            self._漂移("aggr", DRIFT_AGGR_REVENGE, tick, report, "报复得手")
            report(tick, (self.y, self.x),
                   f"{self.name} 大仇得报（因：因果闭环）",
                   kind="报仇成", actor=self.name, target=target.name)
            # 若仇人名下之屋本是夺自我手，今日一并夺回
            if any(m.类别 == "夺屋" and m.对象 == target.name for m in self.memories) \
                    and target.hut is not None:
                屋 = target.hut
                target.hut = None
                屋.主人 = self.name
                self.hut = 屋
                self._known_huts[self.name] = (屋.y, 屋.x)
                report(tick, (屋.y, 屋.x),
                       f"{self.name} 夺回了被 {target.name} 强占的茅屋（因：夺屋之恨+力量已成）",
                       kind="夺回", actor=self.name, target=target.name)
        胜._死否(world, tick, report, "伤重不治", spirits)
