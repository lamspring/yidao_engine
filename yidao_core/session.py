# -*- coding: utf-8 -*-
"""
《易道引擎》世界底座 — 会话层 (session.py)

Session = 一缸世界的会话：世界 + 众灵 + 天道 + 观测回调。
观测层（终端文字流 / 游戏引擎 / 任何平台）经此接入：

    from yidao_core.session import Session

    session = Session.genesis(seed=42)        # 从无到有
    session.run(640)                          # 世界自行十日
    session.seed_at(y, x)                     # 观测者点化：点击处诞生一点灵
    snap = session.snapshot()                 # 此刻的世界与众生

on_event 回调签名：
    on_event(tick, pos, text, kind, actor, target, **extra)
    extra 可携带附加线索（如传闻事件的第三方 subject），供观测层考据。
世界只存此刻；观测笔记记在观测层，不在世界层。
"""

import random

try:
    from .world import World, TICKS_PER_DAY, WORLD_SIZE
    from .spirit import Spirit, NAMES, 新名, 环境印记
    from .tiandao import Tiandao
    from .genesis import 界面点
except ImportError:  # 允许脚本方式直跑
    from world import World, TICKS_PER_DAY, WORLD_SIZE
    from spirit import Spirit, NAMES, 新名, 环境印记
    from tiandao import Tiandao
    from genesis import 界面点

INITIAL_SPIRITS = 10        # 太初众灵数（诞生于阴阳交界）
MAX_SPIRITS = 12            # 凝聚通道的世界容纳上限（繁衍通道另有 POP_CAP）
BIRTH_COVERAGE = 0.20       # 草覆盖率高于此值才算"世界丰饶"
BIRTH_CHANCE = 0.008        # 丰饶时每念"阴凝聚得阳"的低概率


class Session:
    """一缸世界的会话。"""

    def __init__(self, world: World, spirits: list, seed: int, on_event=None):
        self.world = world
        self.spirits = spirits
        self.seed = seed
        self.rng = random.Random(seed ^ 0x5EED)
        self.on_event = on_event or (lambda **kw: None)
        self.tiandao = Tiandao(world, self._emit)
        self._名池 = NAMES[:]
        self.rng.shuffle(self._名池)
        self.生灵 = True          # 灵之开关：侏罗纪缸为 False（无灵凝聚）

    # ── 创世 ────────────────────────────────

    @classmethod
    def genesis(cls, seed: int = 42, size: int = WORLD_SIZE,
                spirits: int = INITIAL_SPIRITS, init_map=None, on_event=None,
                生灵: bool = True, 兽群: str = "田园"):
        """从无到有：炁场自组织出世界，众灵诞生于阴阳交界之处。
        生灵=False 则开纯兽之缸（侏罗纪：无灵初诞，亦无自然凝聚）。"""
        world = World(seed=seed, size=size, init_map=init_map, 兽群=兽群)
        rng = random.Random(seed ^ 0x5EED)
        名池 = NAMES[:]
        rng.shuffle(名池)
        cells = 界面点(world.height, world.water)
        ss: list[Spirit] = []
        if 生灵:
            for i in range(spirits):
                if cells:
                    y, x = cells[i % len(cells)]
                else:
                    y, x = size // 2, size // 2
                # 凝聚之处的水土写入初代 DNA：河边生者善渔，高燥多材者善营造
                s = Spirit(名池[i % len(名池)], y, x, 0, rng,
                           env=环境印记(world, y, x))
                s._世界 = world
                world.生灵入账(s)     # 太初众灵亦自炁凝聚：初阳与形阴自炁场抽取
                ss.append(s)
        session = cls(world, ss, seed, on_event)
        session._名池 = 名池
        session.生灵 = 生灵
        return session

    def seed_at(self, y: int, x: int):
        """观测者点化：一点阳种落入 (y,x)，阴向之收敛凝聚，一点灵诞生。
        落深水则就最近浅处凝聚。返回新灵。"""
        y = max(0, min(self.world.size - 1, int(y)))
        x = max(0, min(self.world.size - 1, int(x)))
        if self.world.water[y, x] >= 1.8:   # 深水不聚形，就最近浅处
            best, bd = (y, x), 1e9
            for dy in range(-4, 5):
                for dx in range(-4, 5):
                    ny, nx = y + dy, x + dx
                    if self.world.in_bounds(ny, nx) and self.world.water[ny, nx] < 1.8:
                        d = abs(dy) + abs(dx)
                        if d < bd:
                            best, bd = (ny, nx), d
            y, x = best
        name = 新名(self.spirits, self.rng)
        s = Spirit(name, y, x, self.world.tick, self.rng,
                   env=环境印记(self.world, y, x))
        s._世界 = self.world
        self.world.生灵入账(s)      # 点化亦凝聚：初阳与形阴自炁场抽取，不足记越界
        self.spirits.append(s)
        self._emit(self.world.tick, (y, x),
                   f"【点化】观测者一点阳种落入，{name} 凝聚成形（因：观测者点化+阴凝聚得阳）",
                   kind="点化", actor=name)
        return s

    # ── 演化 ────────────────────────────────

    def _emit(self, tick, pos, text, kind, actor=None, target=None, **extra):
        # 世界不解释自己，世界只留证据（v6.1 §0.2/§2.5）：
        # 事件文本剥离"（因：…）"注释——注释原文存 extra["因注"]（考据线索）；
        # 叙事层只见干净的行为记录。
        if "（因：" in text:
            head, 因 = text.split("（因：", 1)
            extra.setdefault("因注", 因.rstrip("）"))
            text = head
        # 现场读数（§2.2）：事发当刻的实况，按 kind 白名单现算——观测性改造，动力学不动
        读数 = self._readings(kind, actor, target)
        if 读数:
            extra["readings"] = 读数
        self.on_event(tick=tick, pos=pos, text=text, kind=kind,
                      actor=actor, target=target, **extra)

    # 现场读数白名单：什么 kind 带什么读数（没有的机制不硬塞）
    _READINGS = {
        "死亡": ("阳", "代"), "寿终": ("阳", "代"),
        "战斗": ("阳", "pressure"), "报复": ("阳", "pressure", "铭记时长"),
        "涌现反击": ("阳", "pressure", "阈值", "铭记时长"),
        "涌现": ("阳", "pressure", "阈值"),
        "抢夺": ("阳",), "夺屋成": ("阳", "pressure"), "夺回": ("阳", "铭记时长"),
        "渡阳": ("阳",), "回光": ("阳",),
        "进食": ("阳", "水分"), "饮水": ("阳", "水分"),
        "分享": ("阳",), "救助": ("阳",), "借贷": ("阳",), "还债": ("阳",),
        "赖账": ("阳",), "领悟": ("阳",), "家传": ("阳",), "传授": ("阳",),
        "受冻": ("阳",), "淋雨": ("阳",), "诞育": ("阳",), "结为伴侣": ("阳",),
    }

    def _readings(self, kind, actor, target):
        """按白名单现算现场读数：值取当事人事发当刻的实况（当事念的灵体字段）。
        铭记时长：报复/夺回类事件，溯当事人心中的受辱记忆之龄。"""
        白 = self._READINGS.get(kind)
        if not 白 or actor is None:
            return None
        s = next((x for x in self.spirits if x.name == actor), None)
        if s is None:
            return None
        out = {}
        for k in 白:
            if k == "阳":
                out["阳"] = round(s.yang, 2)
            elif k == "水分":
                out["水分"] = round(s.水分, 2)
            elif k == "代":
                out["代"] = s.代
            elif k == "pressure":
                out["pressure"] = round(s.pressure, 3)
            elif k == "阈值":
                out["阈值"] = 1.0
            elif k == "铭记时长" and target is not None:
                辱 = [m for m in s.memories
                      if m.类别 in ("被抢", "受辱", "夺屋") and m.对象 == target]
                if 辱:
                    out["铭记时长"] = round(
                        (self.world.tick - min(m.念戳 for m in 辱))
                        / TICKS_PER_DAY, 1)
        return out or None

    def step(self):
        """推进一念：世界物理 → 众灵抉择 → 每日结算 → 天道监护 → 自然凝聚。"""
        world = self.world
        tick = world.tick
        world.step(self.spirits)

        for ev in world.drain_events():
            self._emit(tick, ev["pos"], ev["text"], ev["kind"],
                       actor=ev.get("actor"), target=ev.get("target"))

        order = [s for s in self.spirits if s.alive]
        self.rng.shuffle(order)
        for s in order:
            s.decide(world, self.spirits, tick, self._emit, self.rng)

        if tick % TICKS_PER_DAY == TICKS_PER_DAY - 1:
            for s in self.spirits:
                if s.alive:
                    s.settle_day(tick, self._emit, self.spirits)

        self.tiandao.check(tick, self.spirits)

        # 自然凝聚：世界丰饶且灵数未满时，低概率于丰饶水泽边凝聚新灵
        # （侏罗纪缸生灵=False：无灵凝聚，世界纯由兽群演绎）
        alive_n = sum(1 for s in self.spirits if s.alive)
        if self.生灵 and alive_n < MAX_SPIRITS and world.grass_coverage() > BIRTH_COVERAGE \
                and self.rng.random() < BIRTH_CHANCE:
            spots = world.rich_spots()
            if spots:
                y, x = spots[self.rng.randrange(len(spots))]
                name = self._名池[len(self.spirits) % len(self._名池)]
                if any(s.name == name for s in self.spirits):
                    name = f"{name}·{len(self.spirits)}"
                s = Spirit(name, y, x, tick, self.rng,
                           env=环境印记(world, y, x))
                s._世界 = world
                world.生灵入账(s)      # 自然凝聚：初阳与形阴自炁场抽取
                self.spirits.append(s)
                self._emit(tick, (y, x),
                           f"【生】{name} 于丰饶水泽边凝聚成形（因：阴凝聚得阳）",
                           kind="出生", actor=name)

    def run(self, ticks: int):
        for _ in range(ticks):
            self.step()

    # ── 观测（只读此刻）────────────────────

    def snapshot(self) -> dict:
        """此刻的世界与众生：覆盖式当前快照，无历史。"""
        w = self.world
        return {
            "tick": w.tick,
            "气温均": round(float(w.temp.mean()), 1),
            "草覆盖率": round(w.grass_coverage(), 3),
            "降雨场次": w.rain_episodes,
            "茅屋": len(w.buildings),
            "农田": len(w.farms),
            "走兽": len(w.animals),
            "火堆": len(w.fires),
            "众灵": [{"名": s.name, "在世": s.alive, "位置": (s.y, s.x),
                      "阳": round(s.yang, 1), "代": s.代}
                     for s in self.spirits],
        }
