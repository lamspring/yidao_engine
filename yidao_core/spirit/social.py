"""灵体层 · 社交系统（M2 组件化拆分：自 spirit.py 整段搬运，行为不变）"""

from .base import *

class 社交Mixin:
    """灵之社交诸行。"""

    # ── 八·社交与恩义 ────────────────────────

    def _社交(self, world: World, spirits: list, tick: int, report, rng) -> bool:
        邻居 = self._邻居们(spirits)

        # 分享/救助（含送食）：故交面有饥色，我阳尚足——在身旁则分食，在远处则送去
        for b in spirits:
            if b is self or not b.alive:
                continue
            if self.relation(b.name) >= SHARE_REL and b.yang < SHARE_NEED \
                    and self.yang > SHARE_SELF \
                    and tick - self._share_cd.get(b.name, -SHARE_PAIR_CD) >= SHARE_PAIR_CD \
                    and self._感知到(b, tick):
                if b not in 邻居:
                    self._走向(world, b.y, b.x, rng)     # 送食于途
                    return True
                self._share_cd[b.name] = tick
                转阳(world, self, b, SHARE_YANG)     # 分食于途：灵与灵之间的转移
                濒死 = b.yang < 20.0
                b.remember(f"{self.name} 救过我" if 濒死 else f"{self.name} 分过我食物",
                           "受助", self.name, 0.90 if 濒死 else 0.60, tick)
                b._漂移("affinity", DRIFT_AFFINITY_HELPED, tick, report, "多次受人恩惠")
                self.remember(f"我帮过 {b.name}", "助人", b.name, 0.50, tick)
                谢 = f" {b.name}：{rng.choice(_QUOTES_SAVED)}" if rng.random() < 0.5 else ""
                kind = "救助" if 濒死 else "分享"
                因 = "故交+其阳将竭" if 濒死 else "故交+其阳不足"
                report(tick, (self.y, self.x),
                       f"{self.name} 分食物给 {b.name}（因：{因}）{谢}",
                       kind=kind, actor=self.name, target=b.name)
                return True
            # 情分未厚而其人困乏：不白给，可以借——借贷由此而生
            if 0.2 <= self.relation(b.name) < SHARE_REL and b.yang < 38.0 \
                    and self.yang > 55.0 and b.name not in self.credits \
                    and self._感知到(b, tick) and b in 邻居:
                余食 = next((it for it in self.bag if it.类型 in FOOD_YANG), None)
                if 余食 is not None:
                    self.bag.remove(余食)
                    b.bag.append(余食)
                    借物 = 余食.类型
                else:
                    转阳(world, self, b, 10.0)       # 赊一口阳气，言明后还
                    借物 = "口粮"
                self.credits.setdefault(b.name, []).append((借物, tick))
                b.debts.setdefault(self.name, []).append((借物, tick))
                self.remember(f"我借给 {b.name} 一份{借物}", "助人", b.name, 0.50, tick)
                b.remember(f"{self.name} 借给我一份{借物}", "受助", self.name, 0.65, tick)
                report(tick, (self.y, self.x),
                       f"{self.name} 借给 {b.name} 一份{借物}，言明后还（因：相熟+其困乏）",
                       kind="借贷", actor=self.name, target=b.name)
                return True

        if not 邻居:
            return False

        # 狭路相逢：心中有疑（目睹/恶闻）或有债未清，纵然话不投机，也要当面问个明白
        for b in 邻居:
            if not getattr(b, "_已成年", True):
                continue
            if self.relation(b.name) > -0.3 and b.relation(self.name) > -0.3:
                continue    # 尚能寒暄者，对质留到交谈桌上了结
            if tick - self._talk_cd.get(b.name, -TALK_PAIR_CD) < TALK_PAIR_CD:
                continue
            if rng.random() > CONFRONT_CHANCE:
                continue
            self._talk_cd[b.name] = tick
            b._talk_cd[self.name] = tick
            if self._对质(b, tick, report, rng):
                return True

        # 相遇交谈：非敌、双方无紧急需求 → 交换一处食物情报
        for b in 邻居:
            if self.relation(b.name) <= -0.3 or b.relation(self.name) <= -0.3:
                continue    # 仇人相见，无寒暄
            if b.yang <= HUNGER_YANG or b.水分 <= THIRST_URGENT:
                continue    # 对方有急务，不扰
            if tick - self._talk_cd.get(b.name, -TALK_PAIR_CD) < TALK_PAIR_CD:
                continue
            # 熟人见面话多：已有的情分让搭话更自然
            情分 = max(0.0, min(self.relation(b.name), 2.0))
            if rng.random() > TALK_CHANCE * (0.5 + self.affinity) * (1.0 + 情分):
                continue
            self._talk_cd[b.name] = tick
            b._talk_cd[self.name] = tick
            # 久闻其名：初见陌生人，关系不从 0 起——传闻早已先入为主；
            # 佩骨饰者引人注目，身份由此而生（礼物经济的另一面）
            名望 = self.声望(b.name)
            if any(it.类型 == "骨饰" for it in b.bag):
                名望 += 0.15
            if abs(名望) >= 0.2 and not any(
                    m.对象 == b.name and m.类别 not in ("传闻", "听闻", "听闻恨")
                    for m in self.memories):
                report(tick, (self.y, self.x),
                       f"{self.name} 初见 {b.name}，{'早闻其善' if 名望 > 0 else '早闻其恶'}（因：传闻先入为主）",
                       kind="闻名", actor=self.name, target=b.name)
            # 互通有无：各把一处对方不知道的食物点告诉对方
            我告 = [p for p in self.known_food if p not in b.known_food]
            彼告 = [p for p in b.known_food if p not in self.known_food]
            if 我告:
                b.known_food[rng.choice(我告)] = tick
            if 彼告:
                self.known_food[rng.choice(彼告)] = tick
            # 屋檐也是谈资：把"谁家在何处盖了屋"告诉对方
            我知 = [(n, p) for n, p in self._known_huts.items() if n not in b._known_huts]
            彼知 = [(n, p) for n, p in b._known_huts.items() if n not in self._known_huts]
            if 我知 and rng.random() < 0.5:
                n, p = rng.choice(我知)
                b._known_huts[n] = p
            if 彼知 and rng.random() < 0.5:
                n, p = rng.choice(彼知)
                self._known_huts[n] = p
            # 井址也是谈资：何处有井，旱时可知——井的位置随口耳相传而播
            我知井 = [p for p in self._known_wells if p not in b._known_wells]
            彼知井 = [p for p in b._known_wells if p not in self._known_wells]
            if 我知井 and rng.random() < 0.5:
                p = rng.choice(我知井)
                b._known_wells[p] = self._known_wells[p]
            if 彼知井 and rng.random() < 0.5:
                p = rng.choice(彼知井)
                self._known_wells[p] = b._known_wells[p]
            self.remember(f"与 {b.name} 交谈", "交谈", b.name, rng.uniform(0.3, 0.5), tick)
            b.remember(f"与 {self.name} 交谈", "交谈", self.name, rng.uniform(0.3, 0.5), tick)
            self._漂移("affinity", DRIFT_AFFINITY_TALK, tick, report, "常与人为善")
            b._漂移("affinity", DRIFT_AFFINITY_TALK, tick, report, "常与人为善")
            report(tick, (self.y, self.x),
                   f"{self.name} 与 {b.name} 交换了食物消息（因：相遇+无急务）",
                   kind="交谈", actor=self.name, target=b.name)
            # 当面对质：债主问债、被疑者自白——谎言与澄清皆出于此
            if self._对质(b, tick, report, rng):
                return True
            # 闲言碎语：谈论不在场的第三者——传闻由此而起，失真随之而生
            self._传闲话(spirits, b, tick, report, rng)
            # 传授：情分够厚，便把法子教给故人——但教一次未必会，
            # 灌注的是经验（门槛的六成），余下的路还要他自己走
            for kn in ("建造", "种植", "制器", "取火", "烹饪", "渔猎", "畜牧",
                       "凿井", "制陶", "缝纫"):
                if kn in self.knowledge and kn not in b.knowledge \
                        and self.relation(b.name) > 0.3 and rng.random() < TEACH_CHANCE:
                    b.remember(f"{self.name} 教过我{kn}之法", "受教", self.name, 0.60, tick)
                    self.remember(f"我教过 {b.name} {kn}之法", "助人", b.name, 0.45, tick)
                    report(tick, (self.y, self.x),
                           f"{self.name} 把{kn}之法教给了 {b.name}（因：交谈投契+倾囊相授）",
                           kind="传授", actor=self.name, target=b.name)
                    b._积学(kn, LEARN_GATE[kn] * 0.6, tick, report,
                            f"得 {self.name} 点拨，于{kn}之法豁然贯通", "倾囊相授+自己历练")
                    break
            # 口述历史：亲缘夜话——把心中最重的往事讲给孩子，历史由此跨代
            if b.name in (self.子女 or []):
                讲过 = self._讲过.setdefault(b.name, set())
                往事 = [m for m in sorted(self.memories,
                                          key=lambda m: (m.永存, m.权重), reverse=True)
                        if m.序 not in 讲过 and m.类别 not in ("区域", "亲缘", "听闻", "听闻恨", "传闻")]
                if 往事:
                    m = 往事[0]
                    讲过.add(m.序)
                    b.remember(f"听{self.name}讲起：{m.要义}",
                               "听闻恨" if m.类别 in _REL_NEG else "听闻",
                               m.对象, m.情绪强度 * 0.7, tick)
                    report(tick, (self.y, self.x),
                           f"{self.name} 给 {b.name} 讲起往事：{m.要义}（因：口述历史）",
                           kind="口述", actor=self.name, target=b.name)
            # 人情三事：借贷、还债、馈赠、交易
            if self._人情往来(world, b, tick, report, rng):
                return True
            return True
        return False


    # ── 对质：当面问个明白——谎言与澄清皆出于此 ──

    def _对质(self, b, tick: int, report, rng) -> bool:
        """当面质问 b：问债（赖账者或抵赖）与问疑（被误会者自白、有亏心者装无辜）。
        返回 True 表示本次相逢以对质收场（发生了戳穿/得逞/澄清）。"""
        # 一、问债：他欠我的，当面问起。赖账者低概率否认——
        # 债主记忆分明则当场戳穿，记忆已淡则账目随风而散。
        账 = self.credits.get(b.name)
        if 账:
            借念 = min(念 for _, 念 in 账)
            赖过 = any(m.类别 == "谎言" and m.对象 == b.name and m.念戳 >= 借念
                       for m in self.memories)
            if not 赖过 and b.affinity < 0.6 \
                    and rng.random() < LIE_DENY * (1.2 - b.affinity):
                证 = [m for m in self.memories if m.类别 == "助人" and m.对象 == b.name]
                证 = max(证, key=lambda m: m.权重) if 证 else None
                if 证 is not None and 证.权重 >= LIE_CLEAR_W:
                    # 戳穿：记忆如山，岂容抵赖
                    self.remember(f"{b.name} 当面抵赖欠债", "谎言", b.name, 0.78, tick)
                    self.mood["愤怒"] = min(1.0, self.mood["愤怒"] + 0.4)
                    b.remember(f"{self.name} 当众戳穿了我的抵赖", "受辱", self.name, 0.60, tick)
                    b.pressure += 0.35
                    report(tick, (self.y, self.x),
                           f"{b.name} 抵赖：「我何时欠过你？」{self.name} 记得分明，当场戳穿（因：谎言+记忆如山）",
                           kind="谎言戳穿", actor=self.name, target=b.name)
                else:
                    # 得逞：债主自己已淡忘，谎言随风，账目勾销
                    self.credits.pop(b.name, None)
                    b.debts.pop(self.name, None)
                    self.remember(f"莫非我记错了，{b.name} 并不欠我", "疑", b.name, 0.30, tick)
                    report(tick, (self.y, self.x),
                           f"{b.name} 抵赖：「我何时欠过你？」{self.name} 记忆已淡，账目就此勾销（因：谎言+淡忘）",
                           kind="谎言得逞", actor=b.name, target=self.name)
                return True
            return False    # 认了账或未被逼问，还债之事走人情往来
        # 二、问疑：我心里记着"目睹他行凶"或关于他的恶闻，当面质问。
        # 他若问心无愧则澄清；若有亏心事则只能装无辜——亲见者难骗，耳闻者易哄。
        疑 = [m for m in self.memories if m.对象 == b.name
              and (m.类别 == "目睹" or (m.类别 == "传闻" and m.褒贬 < 0))]
        if not 疑:
            return False
        已了 = [m for m in self.memories if m.对象 == b.name and m.类别 in ("冰释", "谎言")]
        if 已了 and max(m.念戳 for m in 已了) >= max(m.念戳 for m in 疑):
            return False    # 这桩疑案已问过，不必再翻
        亏心 = any(m.类别 in ("抢人", "夺屋") for m in b.memories)
        if not 亏心:
            # 澄清：事实胜于流言。前嫌尽释，反成深交。
            if rng.random() < CLARIFY_CHANCE:
                for m in 疑:
                    self.memories.remove(m)
                self.remember(f"{b.name} 与我剖白心迹，前嫌尽释", "冰释", b.name, 0.60, tick)
                b.remember(f"{self.name} 信了我的剖白", "冰释", self.name, 0.50, tick)
                report(tick, (self.y, self.x),
                       f"{b.name} 向 {self.name} 剖白心迹，误会冰释（因：当面质问+问心无愧）",
                       kind="澄清", actor=b.name, target=self.name)
                return True
            return False
        # 装无辜：赌咒发誓未曾作恶
        if rng.random() >= DENY_INNOCENT:
            return False
        亲眼 = any(m.类别 == "目睹" for m in 疑)
        if rng.random() < (0.18 if 亲眼 else 0.65):
            for m in 疑:
                self.memories.remove(m)
            self.remember(f"{b.name} 赌咒发誓是清白的，我姑且信了", "冰释", b.name, 0.35, tick)
            report(tick, (self.y, self.x),
                   f"{b.name} 赌咒发誓未曾行凶，{self.name} 将信将疑，姑且信了（因：花言巧语+口说无凭）",
                   kind="谎言得逞", actor=b.name, target=self.name)
        else:
            self.remember(f"{b.name} 矢口否认罪行", "谎言", b.name, 0.80, tick)
            self.mood["愤怒"] = min(1.0, self.mood["愤怒"] + 0.4)
            b.pressure += 0.3
            b.remember(f"{self.name} 当众咬定我的罪行", "受辱", self.name, 0.55, tick)
            report(tick, (self.y, self.x),
                   f"{b.name} 矢口否认，{self.name} 记忆如山，岂能有假（因：谎言+记忆犹在）",
                   kind="谎言戳穿", actor=self.name, target=b.name)
        return True


    # ── 传闻：谈论不在场的第三者，失真随链长而生 ──

    def _传闲话(self, spirits: list, b, tick: int, report, rng):
        """交谈时概率性谈论第三方：把一条关于他人的记忆说给 b 听。
        b 获得二手记忆（类别"传闻"）。传播会失真：张冠李戴、抢夺传成杀人；
        失真率随传播链长度上升。
        v8-P1C：链长硬停退位——改每站续传概率（0.55），欲再传则掷之，
        不过则此链止于此口；链长 ≤ 6 为安全阀（留痕）。大多数传闻一两站而止，
        偶有五站远来的血案传闻——远方来的消息自带稀有性与戏剧性。"""
        if rng.random() > GOSSIP_CHANCE:
            return
        # 挑一桩关于第三方的旧事作谈资（不与 b 重复人尽皆知之事）
        素材 = [m for m in self.memories
                if m.对象 not in (None, self.name, b.name)
                and m.权重 >= 0.2
                and (m.类别 in _GOSSIP_DEED or (m.类别 == "传闻" and m.褒贬 != 0))
                and not any(x.类别 == "传闻" and x.对象 == m.对象 for x in b.memories)]
        if not 素材:
            return
        src = 素材[rng.randrange(len(素材))]
        # 每站续传概率：传闻欲再传，掷之
        if src.类别 == "传闻" and rng.random() > GOSSIP_SURVIVE:
            return
        if src.链长 >= 6:
            # 安全阀留痕：链长触及上限（续传失控——设计上罕见）
            report(tick, (self.y, self.x),
                   "【越界·安全阀】传闻链长触及上限（因：续传失控，硬顶接管）",
                   kind="安全阀", actor=self.name)
            return
        对象 = src.对象
        if src.类别 == "传闻":
            褒贬, 谈资 = src.褒贬, ("行止不端" if src.褒贬 < 0 else "名声在外")
        else:
            褒贬, 谈资 = _GOSSIP_DEED[src.类别]
        情绪 = min(GOSSIP_EMO_CAP, src.情绪强度 * GOSSIP_EMO)
        # 失真：每多传一站，走样一分
        失真 = False
        if rng.random() < GOSSIP_DISTORT * (1 + src.链长):
            失真 = True
            换角 = rng.random() < 0.5
            if 换角:
                # 张冠李戴：把事安到另一个熟人头上（活着的优先，死者死无对证）
                在世 = sorted({s.name for s in spirits if s.alive}
                            & {m.对象 for m in self.memories
                               if m.对象 and m.类别 != "区域"}
                            - {对象, b.name, self.name})
                备选 = 在世 or sorted({m.对象 for m in self.memories
                                     if m.对象 and m.类别 != "区域"}
                                    - {对象, b.name, self.name})
                if 备选:
                    对象 = 备选[rng.randrange(len(备选))]
                elif 褒贬 < 0:
                    谈资, 情绪 = _GOSSIP_KILL, min(0.8, src.情绪强度 * GOSSIP_EMO * 1.3)
                else:
                    失真 = False
            elif 褒贬 < 0:
                # 夸大其词：抢夺传成杀人
                谈资, 情绪 = _GOSSIP_KILL, min(0.8, src.情绪强度 * GOSSIP_EMO * 1.3)
            else:
                失真 = False
        # 闻者自辨：与事主交情深厚者，不信恶言；已听过此人之事者，不再重复
        if any(x.类别 == "传闻" and x.对象 == 对象 for x in b.memories):
            return
        if 褒贬 < 0 and b.relation(对象) > 0.7 and rng.random() < 0.5:
            return
        b.remember(f"听{self.name}说起：{对象}{谈资}", "传闻", 对象, 情绪, tick,
                   链长=src.链长 + 1, 褒贬=褒贬)
        因 = "口耳相传+以讹传讹" if 失真 else "闲谈+口耳相传"
        report(tick, (self.y, self.x),
               f"{self.name} 对 {b.name} 说：听闻 {对象}{谈资}（因：{因}）",
               kind="传闻失真" if 失真 else "传闻",
               actor=self.name, target=b.name, subject=对象)

    def _人情往来(self, world: World, b, tick: int, report, rng) -> bool:
        rel = self.relation(b.name)
        # 还债：我欠他的，手上有余则当面奉还——恩怨两清，关系更进；无食则以贝抵之
        if b.name in self.debts and self.debts[b.name]:
            物, _ = self.debts[b.name][0]
            贝注 = ""
            还物 = next((it for it in self.bag if it.类型 in FOOD_YANG), None)
            if 还物 is not None:
                self.bag.remove(还物)
                b.bag.append(还物)
            elif 物 == "口粮" and self.yang > 60.0:
                转阳(world, self, b, 10.0)       # 以阳气相赊相还：灵与灵之间的转移
                还物 = None
            else:
                # 贝可还债：照债物的名义价值折算美贝
                n = max(1, (ITEM_VALUE.get(物, 2) + SHELL_VALUE - 1) // SHELL_VALUE)
                if self._数料("美贝") >= n:
                    for _ in range(n):
                        b.bag.append(self._取料("美贝"))
                    还物 = None
                    贝注 = f"，以美贝{n}枚抵之"
                else:
                    还物 = False    # 囊中羞涩，还不上
            if 还物 is not False:
                self.debts[b.name].pop(0)
                if not self.debts[b.name]:
                    del self.debts[b.name]
                if b.credits.get(self.name):
                    b.credits[self.name].pop(0)
                    if not b.credits[self.name]:
                        del b.credits[self.name]
                self.remember(f"我还了 {b.name} 的债", "还债", b.name, 0.55, tick)
                b.remember(f"{self.name} 还了欠我的", "受助", self.name, 0.65, tick)
                report(tick, (self.y, self.x),
                       f"{self.name} 还了 {b.name} 的{物}{贝注}（因：受人之恩，终要还报）",
                       kind="还债", actor=self.name, target=b.name)
                return True
        # 借贷：故交困乏，手上有余则借出一份；无实物则赊一口阳气，言明后还
        if rel >= LEND_REL and b.yang < 35.0 and self.yang > 55.0 \
                and b.name not in self.credits:
            余食 = next((it for it in self.bag if it.类型 in FOOD_YANG), None)
            if 余食 is not None:
                self.bag.remove(余食)
                b.bag.append(余食)
                借物 = 余食.类型
            else:
                转阳(world, self, b, 10.0)       # 以阳气相赊相还：灵与灵之间的转移
                借物 = "口粮"
            self.credits.setdefault(b.name, []).append((借物, tick))
            b.debts.setdefault(self.name, []).append((借物, tick))
            self.remember(f"我借给 {b.name} 一份{借物}", "助人", b.name, 0.50, tick)
            b.remember(f"{self.name} 借给我一份{借物}", "受助", self.name, 0.65, tick)
            report(tick, (self.y, self.x),
                   f"{self.name} 借给 {b.name} 一份{借物}，言明后还（因：故交困乏）",
                   kind="借贷", actor=self.name, target=b.name)
            return True
        # 馈赠：情厚且余裕，不图报地给一份。珍物表情意，重于果腹之食——
        # 饰品馈赠的关系涨幅最大（礼物经济与身份的开端）
        if rel >= GIFT_REL and rng.random() < 0.2:
            it, 情 = None, None
            if self._数料("骨饰") >= 1:
                it, 情 = self._取料("骨饰"), (0.60, 0.85, "珍物表情意")
            elif self._数料("寒衣") >= 2:
                it, 情 = self._取料("寒衣"), (0.55, 0.80, "寒衣赠暖")
            elif self._数料("陶罐") >= 2:
                it, 情 = self._取料("陶罐"), (0.50, 0.65, "陶器之赠")
            elif self._数料("美贝") >= 3:
                it, 情 = self._取料("美贝"), (0.50, 0.70, "以贝为赠")
            else:
                余食 = [x for x in self.bag if x.类型 in FOOD_YANG]
                if len(余食) >= 2:
                    it, 情 = 余食[0], (0.45, 0.60, "情厚有余")
                    self.bag.remove(it)
            if it is not None:
                b.bag.append(it)
                self.remember(f"我赠了 {b.name} 一份{it.类型}", "助人", b.name, 情[0], tick)
                b.remember(f"{self.name} 赠我一份{it.类型}", "受助", self.name, 情[1], tick)
                report(tick, (self.y, self.x),
                       f"{self.name} 赠了 {b.name} 一份{it.类型}（因：{情[2]}）",
                       kind="馈赠", actor=self.name, target=b.name)
                b._摸器悟法(it, tick, report, rng)
                return True
        # 交易：互有盈余而各有所缺，以物易物；公平与否，影响关系。
        # 无互补物资时，以贝结算——我出贝、你出货（贝币雏形：能易物）。
        if rng.random() < TRADE_CHANCE:
            我余 = [it for it in self.bag if it.类型 in ITEM_VALUE]
            彼余 = [it for it in b.bag if it.类型 in ITEM_VALUE]
            我出 = next((it for it in 我余
                         if sum(1 for x in 我余 if x.类型 == it.类型) >= 2
                         and all(x.类型 != it.类型 for x in 彼余)), None)
            彼出 = next((it for it in 彼余
                         if all(x.类型 != it.类型 for x in 我余)), None)
            if 我出 is not None and 彼出 is not None:
                self.bag.remove(我出)
                b.bag.remove(彼出)
                self.bag.append(彼出)
                b.bag.append(我出)
                我值, 彼值 = ITEM_VALUE[我出.类型], ITEM_VALUE[彼出.类型]
                self.remember(f"与 {b.name} 交易，以{我出.类型}易{彼出.类型}", "交易", b.name, 0.40, tick)
                b.remember(f"与 {self.name} 交易，以{彼出.类型}易{我出.类型}", "交易", self.name, 0.40, tick)
                注 = "各取所需"
                if 我值 > 彼值 * 1.5:
                    b.remember(f"{self.name} 占了我便宜", "被亏", self.name, 0.45, tick)
                    注 = "他占了些便宜"
                elif 彼值 > 我值 * 1.5:
                    self.remember(f"{b.name} 占了我便宜", "被亏", b.name, 0.45, tick)
                    注 = "我占了些便宜"
                report(tick, (self.y, self.x),
                       f"{self.name} 以{我出.类型}易 {b.name} 的{彼出.类型}（因：互有盈余+{注}）",
                       kind="交易", actor=self.name, target=b.name)
                self._摸器悟法(彼出, tick, report, rng)
                b._摸器悟法(我出, tick, report, rng)
                return True
            # 贝币结算：我无互补之物而彼有货 → 我出贝；反之彼出贝
            if 我出 is None and 彼出 is not None and 彼出.类型 != "美贝":
                n = max(1, (ITEM_VALUE[彼出.类型] + SHELL_VALUE - 1) // SHELL_VALUE)
                if self._数料("美贝") >= n:
                    for _ in range(n):
                        b.bag.append(self._取料("美贝"))
                    b.bag.remove(彼出)
                    self.bag.append(彼出)
                    self.remember(f"以美贝{n}枚买 {b.name} 的{彼出.类型}", "交易", b.name, 0.45, tick)
                    b.remember(f"{self.name} 以美贝{n}枚买我的{彼出.类型}", "交易", self.name, 0.45, tick)
                    report(tick, (self.y, self.x),
                           f"{self.name} 以美贝{n}枚易 {b.name} 的{彼出.类型}（因：无互补之物+以贝为媒）",
                           kind="贝易", actor=self.name, target=b.name)
                    self._摸器悟法(彼出, tick, report, rng)
                    return True
            elif 彼出 is None and 我出 is not None and 我出.类型 != "美贝":
                n = max(1, (ITEM_VALUE[我出.类型] + SHELL_VALUE - 1) // SHELL_VALUE)
                if b._数料("美贝") >= n:
                    for _ in range(n):
                        self.bag.append(b._取料("美贝"))
                    self.bag.remove(我出)
                    b.bag.append(我出)
                    self.remember(f"{b.name} 以美贝{n}枚买我的{我出.类型}", "交易", b.name, 0.45, tick)
                    b.remember(f"以美贝{n}枚买 {self.name} 的{我出.类型}", "交易", self.name, 0.45, tick)
                    report(tick, (self.y, self.x),
                           f"{b.name} 以美贝{n}枚易 {self.name} 的{我出.类型}（因：无互补之物+以贝为媒）",
                           kind="贝易", actor=b.name, target=self.name)
                    b._摸器悟法(我出, tick, report, rng)
                    return True
        return False
