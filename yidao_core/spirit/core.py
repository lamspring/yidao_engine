"""灵体层 · 核心系统（M2 组件化拆分：自 spirit.py 整段搬运，行为不变）"""

from .base import *

class 核心Mixin:
    """灵之核心诸行。"""
    """灵体：有记忆、有心情、有欲望、会抉择。"""

    def __init__(self, name: str, y: int, x: int, tick: int, rng, 父母=None,
                 env: dict | None = None):
        self.name = name
        self.y, self.x = y, x
        self.诞生念 = tick
        self.alive = True
        self._世界 = None     # 世界回链（会话建立时挂上）：逸散归还炁场之用

        # 阳、水分与力量：阴凝聚时所得的一份阳
        self.yang = rng.uniform(70.0, 95.0)
        self.水分 = rng.uniform(60.0, 90.0)
        self.strength = rng.uniform(8.0, 14.0)

        # ── DNA（v6.5）：生殖系特质序列——人格位点 + 技艺禀赋位点。
        # 初生属性由 dna 决定；心态漂移改的是活值（体细胞），不回写 dna（生殖系）。
        # 初代由环境印记主导，第 N 代血脉渐主导、环境渐弱（见 _成形基因组）。
        self.dna = _成形基因组(rng, env or {},
                             None if 父母 is None else (父母[0].dna, 父母[1].dna),
                             0 if 父母 is None else max(p.代 for p in 父母) + 1)
        # 体质差异：有人耐饿，有人消化快——众灵的饥饱节律由此错开
        self.metabo = 0.8 + 0.45 * self.dna["体质"]

        # 性格特质：谨慎 / 好斗 / 亲和——初生有定数（dna），经历可改之（心态漂移）
        self.caution = self.dna["谨慎"]
        self.aggr = self.dna["悍戾"]
        self.affinity = self.dna["亲和"]
        self._drift_acc = {"caution": 0.0, "aggr": 0.0, "affinity": 0.0}

        # 心情（快变量）
        self.mood = {"恐惧": 0.15, "愤怒": 0.0, "希望": 0.4, "疲惫": 0.0}
        # 压力积累器：受辱受威胁而无出路时积攒，临界即涌现
        self.pressure = 0.0

        self.memories: list[Memory] = []
        self._mem_seq = 0                 # 记忆序号：心中的第几条往事
        # 已知情报只来自两处：亲眼所见，或故人相告。没有全图知识。
        self.known_food: dict[tuple[int, int], int] = {}   # 食物位置 → 最后知悉念
        self.known_water: dict[tuple[int, int], int] = {}  # 水源位置 → 最后知悉念
        self._last_seen: dict[str, tuple] = {}  # 他人 → (y, x, 念, 当时力量)
        self._stay: dict[tuple[int, int], int] = {}  # 格子 → 驻足念数（栖身处由此而出）
        self._mourned: set = set()              # 已悼念过的尸骨
        self._疑过: set = set()                 # 已起过疑心的尸骨/遗物（疑只起一次）
        self._talk_cd: dict[str, int] = {}
        self._share_cd: dict[str, int] = {}

        self.goals: list[str] = []      # 欲望目标链：如 ["变强", "报复:石根"]
        self.training = False           # 是否正在锻炼（用于记录"开始锻炼"）
        self._last_train_report = -TICKS_PER_DAY
        self._last_rob = -ROB_COOLDOWN
        # 日常琐事计数：不进事件流，只入观心与终局统计
        self.stats = {"进食": 0, "饮水": 0, "安眠": 0, "锻炼": 0}

        # 知识与财产：技能（会建造/种植/制器/取火/烹饪/渔猎/畜牧）一旦获得不遗忘；
        # 熟练度随使用提升；名下有屋、田、工具、牲畜、存粮、债务
        self.knowledge: set[str] = set()
        self.悟性 = self.dna["悟性"]
        # 真学习（v6.5）：技能 → 攒下的经验；过 LEARN_GATE 乃悟（见 _积学）
        self._学习: dict[str, float] = {}
        self._学始: dict[str, int] = {}      # 技能 → 初次积攒之念（积学日久之证）
        self.skills: dict[str, float] = {}   # 技能 → 熟练度 0..1
        self.bag: list[Item] = []            # 随身物品（食物/材料/工具），会腐坏
        self.hut = None                 # 自己的茅屋（世界层 Building 对象）
        self._known_huts: dict[str, tuple[int, int]] = {}   # 主人名 → 屋址（社会记忆）
        self._known_fires: dict[str, tuple[int, int]] = {}  # 主人名 → 火址
        self._工地: tuple | None = None  # (y, x, 已施工念数)
        self._求庇_day = -1             # 每夜至多求庇一次
        self._求庇_target: str | None = None  # 已起意的求庇对象（雨歇也把路走完）
        self._淋雨_day = -1             # 每夜至多记一次淋雨
        self._受冻_day = -1             # 每夜至多记一次受冻
        self._庇主: str | None = None   # 今夜收留我的人
        self._家门: tuple | None = None  # 结侣时定下的家：两口子同住一檐下
        self.debts: dict[str, list] = {}    # 我欠谁的：名 → [(物品, 念)]
        self.credits: dict[str, list] = {}  # 谁欠我的：名 → [(物品, 念)]

        # ── v6.4：井、祈雨、迁徙 ──
        self._known_wells: dict[tuple[int, int], str] = {}  # 井址 → 凿井人（社会记忆）
        self._井地: tuple | None = None    # (y, x, 已施工念数) 凿井工地
        self._渴_day = -1                  # 每日至多记一次焦渴
        self._雨见: int = tick             # 最后一次亲见落雨之念
        self._赴祈: tuple | None = None    # (y, x, 日, 发起者) 闻讯赴祈
        self._祈雨: tuple | None = None    # (发起者, 念) —— 祈后待验：三日内的雨都算"应"
        self._祀_day = -1                  # 发起祈雨聚之日（守祀一日）
        self._荒 = 0                       # 居所连续荒凉日数
        self._荒_day = -1
        self._迁: tuple | None = None      # (ty, tx, 启程念) 迁徙目标
        self._迁由 = ""                    # 迁徙之由（叙事用）

        # ── 代际（v6.2）：家世、寿数、婚育 ──
        self.代 = 0 if 父母 is None else max(p.代 for p in 父母) + 1
        self.父母 = tuple(p.name for p in 父母) if 父母 else None
        self.伴侣: str | None = None
        self.子女: list[str] = []
        self.寿数 = int(rng.uniform(46, 56) * TICKS_PER_DAY)  # 阳寿有定数，个体各异
        self.卒念: int | None = None
        self._已成年 = 父母 is None     # 凝聚而生者落地即成年；新生儿须经幼年
        self._上次诞育 = -BIRTH_PAIR_CD
        self._讲过: dict[str, set] = {}  # 口述历史：对谁讲过哪些往事（记忆 id）
        self._家传_day = -1              # 家传每日至多灌注一门

        if 父母 is not None:
            # 新生儿：阴凝聚得一点阳，弱小娇嫩；禀赋已在 dna 中承自双亲
            self.yang = 30.0
            self.水分 = 60.0
            self.strength = 3.0
            self.mood = {"恐惧": 0.05, "愤怒": 0.0, "希望": 0.6, "疲惫": 0.0}
            for p in 父母:
                self.remember(f"{p.name} 是父母", "亲缘", p.name, 0.95, tick)


    # ───────────────────────────────────────
    # 五、每念抉择（优先级自上而下；因果为常，涌现为变）
    # ───────────────────────────────────────

    def decide(self, world: World, spirits: list, tick: int, report, rng):
        if not self.alive:
            return

        # ── 岁月：生长、衰老与寿终（先于一切抉择）──
        年龄日 = (tick - self.诞生念) / TICKS_PER_DAY
        if not self._已成年 and 年龄日 >= ADULT_DAY:
            self._成年(world, spirits, tick, report)
        # 形体曲线（v6.5）：幼弱→壮盛→衰老。力量上限随形体起伏；
        # 十日内者力量自然抽条；战斗/抢夺/显示皆以此钳制后的有效值为准。
        形 = body_curve(年龄日)
        if 年龄日 < 10.0:
            self.strength = max(self.strength, 3.0 + 11.0 * 形)
        if self.strength > STRENGTH_CAP * 形:
            self.strength = STRENGTH_CAP * 形
        if 年龄日 >= OLD_AGE_DAY:
            self.strength = max(4.0, self.strength - 0.008)     # 筋骨渐衰
            cap = max(60.0, 100.0 - (年龄日 - OLD_AGE_DAY) * 2.5)  # 阳上限渐缩
            if self.yang > cap:
                world.qi.归还(self.y, self.x, 阳=self.yang - cap)   # 衰老之阳还于天地
                self.yang = cap
        if tick - self.诞生念 >= self.寿数:
            self._寿终(world, tick, report, spirits)
            return
        if not self._已成年:
            self._幼年(world, spirits, tick, report, rng)
            return

        self._心情漂移()
        # 压力衰减定率化（v8-P0C）：乘性衰减——怨恨阴燃，余怒久郁，
        # 高压闷烧（0.7-0.9）更常见，临界涌现更不可预测
        self.pressure *= (1.0 - PRESSURE_DECAY)

        # 自己的屋塌了没有：世界是物质的，屋檐不会永远等你
        if self.hut is not None and self.hut not in world.buildings:
            self.remember("我的茅屋塌了", "塌屋", None, 0.65, tick)
            self.hut = None
            self._工地 = None
        if self._家门 is not None and world.building_at(self._家门[0], self._家门[1]) is None:
            self._家门 = None   # 家门所在之屋已塌，另觅栖身

        # 故土荒否：每日一次打量居所四周——草枯水涸积够三日，便生弃家之念
        self._察荒(world, spirits, tick, report, rng)

        # 阳之逸散：夜眠减半，渴极加速，体质各异；严寒无檐无火则耗阳更速
        夜 = is_night(tick)
        if not 夜:
            self._庇主 = None           # 天亮了，借宿之约已了
            self._求庇_target = None
        有檐 = self._檐下(world)
        近火 = world.fire_near(self.y, self.x) is not None
        气温 = float(world.temp[self.y, self.x])
        在家 = (self.y, self.x) == self._栖身所()
        安枕 = 夜 and 在家 and self.yang > HUNGER_YANG and self.水分 > THIRST_URGENT
        逸散 = YANG_DECAY * self.metabo * (0.5 if 安枕 else 1.0)
        if self.水分 < THIRST_LOW:
            逸散 *= 1.5
        # 夜雨淋身：无檐之躯，冷雨耗阳；寒夜无火，冷气侵骨——有寒衣者减半
        if 夜 and world.raining_on(self.y, self.x) and not 有檐:
            逸散 += 0.10
        if 气温 < FROST_AT and not 有檐 and not 近火:
            衣 = next((it for it in self.bag if it.类型 == "寒衣"), None)
            if 衣 is not None:
                逸散 += -气温 * 0.015 * 0.45   # 寒衣裹身，冷气侵骨减半
                耗 = min(0.03, 衣.阳)
                衣.阳 -= 耗                  # 寒气磨衣：衣会旧、会敝
                world.物归(self.y, self.x, 耗)
                if 衣.阳 <= 0:
                    self.bag.remove(衣)
                    world.物归(self.y, self.x, 物形阴("寒衣"))
                    self.remember("我的寒衣敝了", "器损", None, 0.40, tick)
                    report(tick, (self.y, self.x),
                           f"{self.name} 的寒衣散成了碎藤（因：寒气磨衣，阳尽则敝）",
                           kind="衣敝", actor=self.name)
            else:
                逸散 += -气温 * 0.015
        self._耗阳(逸散)
        排 = min(self.水分, THIRST_DECAY)
        self.水分 -= 排
        world.water[self.y, self.x] += 排 * BODY2FIELD   # 汗溺之排，就地还场（水过身体，终还于土）

        # 随身物什各按其材质腐坏（寒慢热快）；陶罐藏粮，腐坏减半。
        # 腐者之量就地归还炁场（物归）；腐尽之形阴亦还——消亡之处肥其土。
        # 存粮腐坏是锥心之痛——痛一次，积一分烧土为瓮之思。
        有罐 = any(it.类型 == "陶罐" for it in self.bag)
        坏食 = []
        存 = []
        for it in self.bag:
            藏 = 0.55 if (有罐 and it.类型 in FOOD_YANG) else 1.0
            旧 = it.阳
            if it.腐一步(气温, 藏=藏):
                world.物归(self.y, self.x, 旧 + 物形阴(it.类型))
                if it.类型 in FOOD_YANG:
                    坏食.append(it.类型)
            else:
                world.物归(self.y, self.x, 旧 - it.阳)
                存.append(it)
        self.bag = 存
        if 坏食 and rng.random() < 0.5:
            self.remember(f"怀中的{坏食[0]}腐坏了，可惜之极", "腐坏", None, 0.40, tick)
            self._积学("制陶", 25.0, tick, report,
                       "痛惜腐坏之粮，忽悟可烧土为瓮以储之", "腐坏之痛")

        if self._死否(world, tick, report, "阳尽", spirits):
            return

        # 感知先行：所见即所知；若遇故人遗骨，悼念占去此念
        if self._感知(world, spirits, tick, report, rng):
            return

        # 〇、压力临界 → 涌现（优先于一切理性抉择）
        if self.pressure >= PRESSURE_MAX:
            self._涌现(world, spirits, tick, report, rng)
            return

        # 一、陌生环境 → 先观察，不冒进
        if not self._区域有记忆():
            self._观察(world, tick)
            return

        # 二、饥渴 → 求生为第一要务（好斗者饥饿时先动抢夺之念）
        if self.yang < HUNGER_YANG:
            if self.aggr > ROB_AGGR and self._尝试抢夺(world, spirits, tick, report, rng):
                return
            self._觅食(world, spirits, tick, report, rng)
            self._死否(world, tick, report, "阳尽", spirits)
            return
        if self.水分 < THIRST_URGENT:
            self._找水(world, tick, report, rng)
            return

        # 三、旁边有"比自己强且抢过自己"者：谨慎则避，积怨临界则暴起
        threat = self._身边威胁(spirits)
        if threat is not None:
            if self.caution > 0.35:
                self._逃离(threat, world, rng)
                self.pressure += 0.06
                self.mood["恐惧"] = min(1.0, self.mood["恐惧"] + 0.15)
                return
            self.pressure += 0.10   # 忍气吞声，压力暗积

        # 三·五、迁徙途中：昼行夜宿，不到新土不止
        if self._迁 is not None and self._行迁(world, tick, report, rng):
            return

        # 四、夜里无急务 → 归栖安眠；雨夜无屋者求庇，寒夜无火者取暖
        if 夜:
            if not 有檐:
                if world.raining_on(self.y, self.x):
                    self._淋雨(world, tick, report, rng)
                # 寒夜受冻：冷到骨头里，才会想出钻木取火
                if 气温 < FROST_AT and not 近火:
                    self._受冻(world, tick, report, rng)
                # 求庇既起意，雨歇也把路走完
                if world.raining_on(self.y, self.x) or self._求庇_target is not None:
                    if self._尝试求庇(world, spirits, tick, report, rng):
                        return
                # 寒夜寻火：知道何处有火，便往火边去
                if 气温 < FROST_AT and not 近火 and self._known_fires:
                    fy, fx = min(self._known_fires.values(),
                                 key=lambda p: abs(p[0] - self.y) + abs(p[1] - self.x))
                    if world.fire_near(fy, fx, 0) is not None:
                        self._走向(world, fy, fx, rng)
                        return
            home = self._栖身所()
            if (self.y, self.x) == home or 有檐:
                # 夜半私话：同檐而眠、温饱有余的伴侣或诞新丁
                if self.伴侣 is not None and 有檐:
                    p = next((s for s in spirits if s.alive and s.name == self.伴侣), None)
                    if p is not None and self._切比(self.y, self.x, p.y, p.x) <= 2 \
                            and self._诞育(world, spirits, p, tick, report, rng):
                        return
                # 寒夜在自家檐下，钻木起一灶火
                if 气温 < FROST_AT and not 近火 and "取火" in self.knowledge \
                        and self._数料("木") >= 1:
                    self._钻木(world, tick, report, rng)
                    return
                # 寒季储粮：家中余粮入仓，腐坏减半——冬藏是生存主线
                if self.hut is not None and (self.y, self.x) == (self.hut.y, self.hut.x):
                    余食 = [it for it in self.bag if it.类型 in FOOD_YANG]
                    if len(余食) >= 3:
                        for it in 余食[1:]:
                            self.bag.remove(it)
                            self.hut.仓储.append(it)
                self._安眠(world, 有檐)
            elif self._迁 is not None:
                self._安眠(world, 有檐)   # 迁徙途中，夜则就地宿营
            else:
                self._走向(world, home[0], home[1], rng)
            return

        # 五、悍戾者饥饿线放宽：霸凌不靠饿，靠性
        if self.aggr > ROB_AGGR and self.yang < ROB_GREEDY_YANG:
            if self._尝试抢夺(world, spirits, tick, report, rng):
                return

        # 五·五、雨夜将至而无屋的悍者，或起夺屋之念
        if self.hut is None and self.aggr > SEIZE_AGGR:
            if self._尝试夺屋(world, spirits, tick, report, rng):
                return

        # 六、有报复目标且力量已成 → 凭记忆搜寻仇人
        if self._追击报复(world, spirits, tick, report, rng):
            return

        # 七、目睹好友遭劫 → 挺身庇护
        if self._尝试庇护(world, spirits, tick, report, rng):
            return

        # 七·五、连旱草枯 → 祈雨聚（天道永不回应祈雨；仪式是群体的镇定剂）
        if self._祈雨聚(world, spirits, tick, report, rng):
            return

        # 八、故人相遇无急务 → 寒暄分食（恩义由此而生，知识由此而传）
        if self._社交(world, spirits, tick, report, rng):
            return

        # 八·五、男婚女嫁与生养：两情相悦且有檐可依 → 结侣；温饱有余 → 诞育
        if self._婚配(world, spirits, tick, report, rng):
            return

        # 九、知建造之法且有动机者 → 备料营造；会种植且温饱者 → 耕一畦田
        if self._营建(world, tick, report, rng):
            return
        if self._农事(world, tick, report, rng):
            return
        # 九·二、知凿井且水忧在心者 → 择低洼湿润处凿井
        if self._凿井(world, tick, report, rng):
            return

        # 九·五、百工：制器、取火、烹饪、畜牧——温饱之上的营生
        if self._百工(world, spirits, tick, report, rng):
            return

        # 十、有"变强"目标且安全 → 锻炼
        if "变强" in self.goals and threat is None and self.yang > TRAIN_SAFE_YANG:
            self._锻炼(tick, report)
            return

        # 十一、否则游荡 / 观察 / 顺手采食饮水
        self._游荡(world, tick, report, rng, spirits)
        self._死否(world, tick, report, "阳尽", spirits)


    # ───────────────────────────────────────
    # 二、记忆：铭记 / 遗忘 / 压缩
    # ───────────────────────────────────────

    def remember(self, 要义: str, 类别: str, 对象: str | None, 情绪: float, tick: int,
                 链长: int = 0, 褒贬: int = 0):
        """记下一事。情绪 ≥0.85 的记忆永存——关键的事永远不忘。
        同对象同类别的永存记忆不再另起新条，只在旧痕上加深。"""
        永存 = 情绪 >= MEMORY_ETERNAL
        if 永存 and 对象 is not None:
            旧 = next((m for m in self.memories
                       if m.永存 and m.类别 == 类别 and m.对象 == 对象), None)
            if 旧 is not None:
                旧.次数 += 1
                旧.念戳 = tick
                旧.权重 = min(1.0, 旧.权重 + 0.03)
                return
        self.memories.append(Memory(
            要义=要义, 类别=类别, 对象=对象, 情绪强度=情绪,
            念戳=tick, 权重=0.3 + 0.7 * 情绪, 永存=永存, 链长=链长, 褒贬=褒贬,
            序=self._mem_seq))
        self._mem_seq += 1

    def settle_day(self, tick: int = 0, report=None, spirits: list = ()):
        """每日结算：低情绪记忆衰减，归零即遗忘；相似低权重记忆压缩成一条要义。
        哀伤衰减极慢——故人之思，念念不忘。
        另清账目：欠债逾三日而我有能力还而不还 → 债主记一笔赖账之怨。"""
        for 债主, 账 in list(self.debts.items()):
            for 物, 借念 in list(账):
                if tick - 借念 > DEBT_DAYS * TICKS_PER_DAY and self.yang > 45.0 \
                        and report is not None:
                    # 赖账：比抢夺更隐蔽的恶——债主心里记下一笔
                    债主灵 = next((s for s in spirits if s.name == 债主), None)
                    账.remove((物, 借念))
                    if not 账:
                        del self.debts[债主]
                    if 债主灵 is not None:
                        债主灵.credits.pop(self.name, None)
                        债主灵.remember(f"{self.name} 欠账不还", "赖账", self.name, 0.55, tick)
                        report(tick, (self.y, self.x),
                               f"{债主} 记恨 {self.name} 欠账不还（因：有约在先+有能力还而不还）",
                               kind="赖账", actor=self.name, target=债主)
        留存: list[Memory] = []
        for m in self.memories:
            if m.永存:
                留存.append(m)
                continue
            m.权重 *= MOURN_DECAY if m.类别 in ("悼念", "听闻", "听闻恨") \
                else (0.80 + 0.18 * m.情绪强度)
            if m.权重 >= MEMORY_FORGET:
                留存.append(m)
        self.memories = 留存

        # 压缩：同类同对象的三条以上低权重记忆，并为一条"零碎的旧事"
        分组: dict[tuple, list[Memory]] = {}
        for m in self.memories:
            if not m.永存:
                分组.setdefault((m.类别, m.对象), []).append(m)
        for (类别, 对象), ms in 分组.items():
            if len(ms) >= 3:
                verb = _KIND_VERB.get(类别, "过往")
                最旧 = min(ms, key=lambda m: m.念戳)
                褒贬合计 = sum(m.褒贬 for m in ms)
                merged = Memory(
                    要义=f"零碎的{verb}旧事（{len(ms)}件并为一件）",
                    类别=类别, 对象=对象,
                    情绪强度=sum(m.情绪强度 for m in ms) / len(ms),
                    念戳=最旧.念戳,
                    权重=max(m.权重 for m in ms) * 0.9,
                    永存=False,
                    链长=max(m.链长 for m in ms),
                    褒贬=1 if 褒贬合计 > 0 else (-1 if 褒贬合计 < 0 else 0),
                    序=self._mem_seq)
                self._mem_seq += 1
                for m in ms:
                    self.memories.remove(m)
                self.memories.append(merged)

        # 容量兜底：心就这么大，最轻的往事先走
        if len(self.memories) > 40:
            非永存 = [m for m in self.memories if not m.永存]
            非永存.sort(key=lambda m: m.权重)
            for m in 非永存[:len(self.memories) - 40]:
                self.memories.remove(m)

    def remembers_robbery_by(self, name: str) -> bool:
        """是否记着"此人抢过我"——记得就是有关系，忘了就是陌路。"""
        return any(m.类别 in ("被抢", "受辱") and m.对象 == name for m in self.memories)

    def relation(self, name: str) -> float:
        """关系 = 对此人全部记忆的加权综合。忘光即陌路（0）。
        传闻按其自带褒贬计入，且耳闻不如眼见——权重打半折。"""
        s = 0.0
        for m in self.memories:
            if m.对象 != name:
                continue
            w = m.权重 * (1.5 if m.永存 else 1.0)
            if m.类别 == "传闻":
                s += w * m.褒贬 * GOSSIP_WEIGHT
            elif m.类别 in _REL_POS:
                s += w
            elif m.类别 in _REL_NEG:
                s -= w
        return s

    def 声望(self, name: str) -> float:
        """此人在我心中的声望：我对他的全部耳闻（传闻/听闻/目睹）之加权和。
        声望是分布式的社会记忆——每个灵心里都有一个版本，世上没有全局榜。"""
        s = 0.0
        for m in self.memories:
            if m.对象 != name:
                continue
            if m.类别 == "传闻":
                s += m.权重 * m.褒贬 * GOSSIP_WEIGHT
            elif m.类别 == "听闻":
                s += m.权重 * 0.5
            elif m.类别 == "听闻恨":
                s -= m.权重 * 0.5
            elif m.类别 == "目睹":
                s -= m.权重
        return s


    # ───────────────────────────────────────
    # 三、欲望（目标链）
    # ───────────────────────────────────────

    def want(self, goal: str):
        if goal not in self.goals:
            self.goals.append(goal)

    def drop_goal(self, goal: str):
        if goal in self.goals:
            self.goals.remove(goal)
        # 若已无人可报复，"变强"之念也随之淡去
        if goal.startswith("报复:") and not any(g.startswith("报复:") for g in self.goals):
            if "变强" in self.goals:
                self.goals.remove("变强")


    # ───────────────────────────────────────
    # 四、心态漂移：性格被经历塑造
    # ───────────────────────────────────────

    def _漂移(self, axis: str, delta: float, tick: int, report, 因: str):
        旧 = getattr(self, axis)
        setattr(self, axis, max(0.0, min(1.0, 旧 + delta)))
        self._drift_acc[axis] += delta
        if self._drift_acc[axis] >= DRIFT_REPORT:
            self._drift_acc[axis] = 0.0
            词 = {"caution": "愈发警惕", "aggr": "愈发悍戾", "affinity": "愈发亲和"}[axis]
            report(tick, (self.y, self.x),
                   f"{self.name} 变得{词}（因：{因}）",
                   kind="漂移", actor=self.name)


    # ── 基础动作与状态 ───────────────────────

    def _走向(self, world: World, ty: int, tx: int, rng):
        """朝目标贪心地走一步，避开水深处。"""
        候选 = []
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                ny, nx = self.y + dy, self.x + dx
                if world.in_bounds(ny, nx) and world.water[ny, nx] < 1.8:
                    d = abs(ny - ty) + abs(nx - tx)
                    候选.append((d, rng.random(), ny, nx))
        if 候选:
            候选.sort()
            if 候选[0][0] < abs(self.y - ty) + abs(self.x - tx):
                self._移动到(world, 候选[0][2], 候选[0][3])

    def _移动到(self, world: World, ny: int, nx: int):
        if (ny, nx) != (self.y, self.x):
            self.y, self.x = ny, nx
            world.tread[ny, nx] += 1.0    # 众脚往复，径由此而生（记录在世界里）
            耗 = MOVE_COST * (PATH_COST if world.tread[ny, nx] >= PATH_AT else 1.0)
            self._耗阳(耗)                 # 径上行走省力一半
            self.mood["疲惫"] = min(1.0, self.mood["疲惫"] + 0.01)
            self.training = False

    def _耗阳(self, amount: float):
        """阳之逸散：就地归还炁场——洒水壶，走到哪撒到哪（宇宙底座第一律）。"""
        扣 = min(self.yang, amount)
        self.yang -= 扣
        w = self._世界
        if w is not None and 扣 > 0.0:
            w.qi.归还(self.y, self.x, 阳=扣)

    def _泵阳(self, world: World, 量: float):
        """自生物质得阳（食草啖肉、田间收获）：记日月之泵——
        太阳能经草木鱼虫入链；上限溢出者不入账（溢者本未入网）。"""
        旧 = self.yang
        self.yang = min(100.0, self.yang + 量)
        world.账.泵 += self.yang - 旧

    def _得物(self, world: World, 类型: str):
        """自生物质/太古遗泽得物（采集、伐木、渔获、屠宰、收蛋挤奶）：
        记源C——物质从泵的领地进入万物之链。"""
        self.bag.append(Item(类型))
        world.源C(ITEM_YANG.get(类型, ITEM_YANG_TOOL) + 物形阴(类型))

    def _转化(self, world: World, 料单: list, 成品能: float):
        """转化结算：旧结解开、新结系上。耗料之（阳+形阴）与成品之（阳+形阴）
        的差额归还炁场（物归；不足则负，炁场补之）——斧不是被造出来的，
        是木与石的结解开、在工匠手中重新系上的。"""
        料能 = sum(it.阳 + 物形阴(it.类型) for it in 料单 if it is not None)
        world.物归(self.y, self.x, 料能 - 成品能)

    def _死否(self, world: World, tick: int, report, 因: str, spirits: list = ()) -> bool:
        """阳尽则亡：遗体成尸骨印记（带姓名，供故人悼念），保质约 2 日后化为土。
        死后有善后：遗物归亲人，无亲则遗于野；听过父母深仇的孩子从此背负。"""
        if self.alive and self.yang <= 0:
            self.yang = 0.0
            self.alive = False
            world.生灵归账(self.y, self.x, 0.0, self.水分)   # 形阴与躯中残水，尽数归还（倾覆）
            self.水分 = 0.0
            self.卒念 = tick
            world.add_mark("尸骨", self.y, self.x, 2 * TICKS_PER_DAY, 标签=self.name)
            report(tick, (self.y, self.x),
                   f"{self.name} 阳尽而亡，遗骨归于尘土（因：{因}）",
                   kind="死亡", actor=self.name)
            self._善后(world, tick, report, spirits)
            self._盖棺()
            return True
        return not self.alive

    def _盖棺(self):
        """盖棺定论：心就这么大，死者的心不再结算——入土前最轻的往事随风，留四十条。"""
        if len(self.memories) > 40:
            非永存 = sorted((m for m in self.memories if not m.永存), key=lambda m: m.权重)
            for m in 非永存[:len(self.memories) - 40]:
                self.memories.remove(m)

    def _寿终(self, world: World, tick: int, report, spirits: list):
        """寿数已尽：不是被杀，不是饿死，是阳寿自然竭尽——安然闭目。"""
        world.生灵归账(self.y, self.x, self.yang, self.水分)   # 余阳、形阴、躯中残水，尽数归还
        self.yang = 0.0
        self.水分 = 0.0
        self.alive = False
        self.卒念 = tick
        world.add_mark("尸骨", self.y, self.x, 2 * TICKS_PER_DAY, 标签=self.name)
        report(tick, (self.y, self.x),
               f"{self.name} 寿数已尽，安然闭目，遗骨归于尘土（因：阳寿自然竭尽）",
               kind="寿终", actor=self.name)
        self._善后(world, tick, report, spirits)
        self._盖棺()

    def _善后(self, world: World, tick: int, report, spirits: list):
        """身后事：随身遗物与名下财产归于最亲的人（伴侣优先，其次子女）；
        无亲则遗物留在原地，待人拾取，日久归土。父仇或由此落到孩子肩上。"""
        heir = None
        p = next((s for s in spirits if s.alive and s.name == self.伴侣), None)
        子女 = [s for s in spirits if s.alive and s.name in self.子女]
        if p is not None:
            heir = p
        elif 子女:
            heir = min(子女, key=lambda s: s.诞生念)   # 长子/长女继承
        if heir is not None:
            for it in self.bag:
                heir.bag.append(it)
            self.bag = []
            if self.hut is not None:
                self.hut.主人 = heir.name
                if heir.hut is None:
                    heir.hut = self.hut
                heir._known_huts[heir.name] = (self.hut.y, self.hut.x)
                heir._known_huts[self.name] = (self.hut.y, self.hut.x)
                self.hut = None
            for f in world.farms:
                if f.主人 == self.name:
                    f.主人 = heir.name
            for a in world.animals:
                if a.驯主 == self.name:
                    a.驯主 = heir.name
            for f in world.fences:
                if f.主人 == self.name:
                    f.主人 = heir.name
            for f in world.fires:
                if f.主人 == self.name:
                    f.主人 = heir.name
            heir.remember(f"{self.name} 留给我的念想", "继承", self.name, 0.70, tick)
            report(tick, (self.y, self.x),
                   f"{heir.name} 继承了 {self.name} 的遗物与屋檐（因：血脉相续）",
                   kind="继承", actor=heir.name, target=self.name)
        else:
            if self.bag:
                world.relics.append({"名": self.name, "y": self.y, "x": self.x,
                                     "物": self.bag[:], "念": tick})
                self.bag = []
            self.hut = None   # 屋成无主，留在世上风雨飘摇
        # 父仇子报：听过父母深仇旧事的孩子，从此把仇记在自己身上
        for s in spirits:
            if not s.alive or s.name not in self.子女:
                continue
            恨 = [m for m in s.memories if m.类别 == "听闻恨" and m.对象
                  and any(x.alive and x.name == m.对象 for x in spirits)]
            if not 恨:
                continue
            仇 = max(恨, key=lambda m: m.情绪强度)
            if 仇.情绪强度 < 0.55:
                continue
            s.remember(f"{仇.对象} 是父母的大仇，此恨不共戴天", "父仇", 仇.对象, 0.88, tick)
            s.want("变强")
            s.want(f"报复:{仇.对象}")
            report(tick, (s.y, s.x),
                   f"{s.name} 把 {仇.对象} 之仇记在了自己身上（因：父仇子报）",
                   kind="父仇", actor=s.name, target=仇.对象)

    def _心情漂移(self):
        """心情是快变量：无风波时各自回落。"""
        self.mood["愤怒"] = max(0.0, self.mood["愤怒"] - 0.005)
        self.mood["恐惧"] = max(0.0, self.mood["恐惧"] - 0.02)
        self.mood["希望"] += (0.3 - self.mood["希望"]) * 0.01
        self.mood["疲惫"] = max(0.0, self.mood["疲惫"] - 0.008)


    # ── 观心：读心界面用的只读视图 ───────────

    def 关系(self) -> list[tuple[str, float]]:
        """关系 = 对他人的记忆。记得就是有关系，忘了就是陌路。"""
        seen: dict[str, float] = {}
        for m in self.memories:
            if m.对象 and m.类别 != "区域" and m.对象 not in seen:
                seen[m.对象] = self.relation(m.对象)
        return sorted(seen.items(), key=lambda kv: -abs(kv[1]))
