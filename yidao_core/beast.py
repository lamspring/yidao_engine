# -*- coding: utf-8 -*-
"""
《易道引擎》世界底座 — 兽层 (beast.py)

侏罗纪缸：行为简单不复杂的动物——饥则食，渴则饮，敌至则逃或斗，
温饱则繁衍，夜则伏，幼则从弱长成。兽不学、不建、不传话，只有本能。

兽与灵共用同一阴阳物质模型（同一守恒账）：
  逸散就地归还（洒水壶）；死亡倾覆（余阳形阴残水尽数归还）；
  出生凝聚（自炁场抽取初阳形阴、自场水取体水）；食入记日月之泵。

本层一切生死代谢皆经 world 的守恒接口。world 常量一律函数内迟绑定引用，
避循环引用（world 在模块级 import 本层，本层不在模块级 import world）。
"""

from .qi import BEAST_FORM_YIN

# 体型之序：虫 < 小 < 中 < 大 < 巨
体型序 = {"虫": 0, "小": 1, "中": 2, "大": 3, "巨": 4}

# 兽种表：食性、体型、群性、勇怯皆入表。寿日以"日"计（用处乘 TICKS_PER_DAY）。
# 蛋期/奶期为田园畜禽之产（畜牧用），单位念。
#   鸡羊牛：田园畜禽（灵之世代的畜牧对象）
#   角龙：植食大型群居，遇敌逃多斗少（被围亦斗）  梁龙：植食巨型游荡，成年几无天敌
#   迅猛龙：肉食小型群猎，猎体型不逾己者（成群可猎大一阶）
BEASTS = {
    "鸡":   dict(食="虫", 体型="小", 群=False, 勇=0.10, 阳=40.0, 逸散=0.045,
                 寿日=8, 蛋期=48),
    "羊":   dict(食="草", 体型="中", 群=True, 勇=0.15, 阳=80.0, 逸散=0.05,
                 寿日=16, 奶期=64),
    "牛":   dict(食="草", 体型="大", 群=True, 勇=0.30, 阳=120.0, 逸散=0.06,
                 寿日=24, 奶期=64),
    "角龙": dict(食="草", 体型="大", 群=True, 勇=0.35, 阳=130.0, 逸散=0.045,
                 寿日=45),
    "梁龙": dict(食="草", 体型="巨", 群=False, 勇=0.50, 阳=200.0, 逸散=0.06,
                 寿日=60),
    "迅猛龙": dict(食="肉", 体型="小", 群=True, 勇=0.80, 阳=55.0, 逸散=0.06,
                   寿日=30),
    "始祖鸟": dict(食="虫", 体型="小", 群=False, 勇=0.05, 阳=45.0, 逸散=0.04,
                   寿日=25),
}

BREED_CHANCE = 0.025    # 温饱成对的野兽每念繁殖概率（繁衍生息要跑赢天敌与寿数）
FLEE_RADIUS = 2         # 兽见天敌而逃的半径
SENSE_BEAST = 4         # 兽的感知半径（找水找食找敌）
BEAST_THIRST = 0.12     # 兽之水分每念下降（与灵同率）
DRINK_MIN_BEAST = 0.4   # 积水达到此值兽可饮

_TPD = None


def _tpd() -> int:
    """TICKS_PER_DAY 的迟绑定（避循环引用，缓存一次）。"""
    global _TPD
    if _TPD is None:
        from .world import TICKS_PER_DAY as _T
        _TPD = _T
    return _TPD


def 体曲(年龄念: int, 寿念: int) -> float:
    """兽之形体曲线：幼弱（0.5）→ 成年（1.0）→ 老渐衰。
    幼体期短（寿之 8%）——幼龙在父母的领地里抽条，不在荒野里觅食。"""
    成体念 = max(1, int(寿念 * 0.08))
    if 年龄念 < 成体念:
        return 0.5 + 0.5 * 年龄念 / 成体念
    if 年龄念 > 寿念 * 0.8:
        return max(0.6, 1.0 - 0.2 * (年龄念 - 寿念 * 0.8) / max(1, 寿念 * 0.2))
    return 1.0


def 兽生(world, 种类: str, y: int, x: int, rng, 幼体: bool = False):
    """阴凝聚得一点阳：新兽之初阳与形阴自炁场抽取，体水自场水（不足则九泉）转入。
    创世之兽落地即成年（太初无幼体）；繁衍之兽方为幼体，逐日抽条。"""
    from .world import Animal, BODY2FIELD
    p = BEASTS[种类]
    阳初 = p["阳"] * (0.5 if 幼体 else 1.0)
    形阴 = BEAST_FORM_YIN.get(种类, 10.0)
    实阳, 实阴 = world.qi.抽取(y, x, 阳=阳初, 阴=形阴)
    world.账.越界B += (阳初 - 实阳) + (形阴 - 实阴)
    a = Animal(种类, y, x, 阳初)
    a.年龄 = 0 if 幼体 else int(p["寿日"] * _tpd() * 0.3)   # 创世兽自壮年起
    if not 幼体:
        a.产物念 = int(rng.integers(0, 64))     # 创世畜禽的产物节律各异
    # 体水自场转入（水过身体，总量不变）
    需 = a.水分 * BODY2FIELD
    取 = min(需, float(world.water[y, x]))
    world.water[y, x] -= 取
    欠 = 需 - 取
    if 欠 > 0.0:
        引 = min(world._深潭, 欠)
        world._深潭 -= 引
        欠 -= 引
    if 欠 > 0.0:
        world.账.越界A += 欠      # 四野滴水全无，唯越界补之（殆不曾见）
    world.animals.append(a)
    return a


def 兽亡(world, a):
    """倾覆：余阳与形阴归还炁场，躯中残水还场，遗体成尸骸（生物质）。"""
    from .world import Carrion, BODY2FIELD
    if a in world.animals:
        world.animals.remove(a)
    world.qi.归还(a.y, a.x, 阳=max(0.0, a.阳), 阴=BEAST_FORM_YIN.get(a.种类, 10.0))
    if a.水分 > 0.0:
        world.water[a.y, a.x] += a.水分 * BODY2FIELD
    肉骨 = {"鸡": (2, 1), "羊": (4, 2), "牛": (6, 3),
            "角龙": (7, 3), "梁龙": (10, 4), "迅猛龙": (2, 1)}
    肉, 骨 = 肉骨.get(a.种类, (2, 1))
    world.carrions.append(Carrion(a.y, a.x, 肉, 骨, 名=a.种类))


def _近(world, y, x, r):
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            ny, nx = y + dy, x + dx
            if world.in_bounds(ny, nx):
                yield ny, nx


def _移(world, a, ty, tx, 疾走=False):
    """向目标挪一步（疾走两步）。不上深水。"""
    for _ in range(2 if 疾走 else 1):
        dy = (ty > a.y) - (ty < a.y)
        dx = (tx > a.x) - (tx < a.x)
        ny, nx = a.y + dy, a.x + dx
        if world.in_bounds(ny, nx) and world.water[ny, nx] < 1.8:
            a.y, a.x = ny, nx


def 兽行(world, a, spirits, rng):
    """野性本能循环（每念一决，优先级自上而下）：

      逸散与渴耗 → 死生判定 → 天敌至则逃或斗（灵与火亦令兽惊，只逃不斗）
      → 饥则食（猎/噬/草虫） → 渴则寻水 → 夜伏 → 温饱则群聚游荡。
    灵不在兽的食谱上。
    """
    from .world import is_night, BODY2FIELD, DRINK_KEEP, TICKS_PER_DAY
    p = BEASTS[a.种类]
    寿念 = p["寿日"] * TICKS_PER_DAY
    夜 = is_night(world.tick)

    # 逸散与渴耗：阳之逸散就地归还（夜伏减半）；水分渐失，汗溺还场
    逸 = p["逸散"] * (0.5 if 夜 else 1.0)
    if a.水分 < 25.0:
        逸 *= 1.5                    # 渴极加速（与灵同律）
    扣 = min(a.阳, 逸)
    a.阳 -= 扣
    world.qi.归还(a.y, a.x, 阳=扣)
    排 = min(a.水分, BEAST_THIRST)
    a.水分 -= 排
    world.water[a.y, a.x] += 排 * BODY2FIELD

    # 死生：阳尽、寿终
    if a.阳 <= 0 or a.年龄 > 寿念 * rng.uniform(0.9, 1.1):
        兽亡(world, a)
        return
    a.年龄 += 1
    a.产物念 = max(0, a.产物念 - 1)
    曲 = 体曲(a.年龄, 寿念)

    # 天敌至：逃（常态）或斗（勇而群、勇而大者敢斗）
    敌 = None
    for b in world.animals:
        if b is a:
            continue
        bp = BEASTS[b.种类]
        if bp["食"] == "肉" and 体型序[bp["体型"]] >= 体型序[p["体型"]] \
                and abs(b.y - a.y) <= FLEE_RADIUS and abs(b.x - a.x) <= FLEE_RADIUS:
            敌 = b
            break
    # 灵与火亦令兽惊（兽眼无人智，但知活物逼近则避）——见灵与火只逃不斗
    惊 = None
    if p["食"] != "肉":
        for s in spirits:
            if s.alive and abs(s.y - a.y) <= FLEE_RADIUS and abs(s.x - a.x) <= FLEE_RADIUS:
                惊 = s
                break
        if 惊 is None:
            for f in world.fires:
                if abs(f.y - a.y) <= FLEE_RADIUS and abs(f.x - a.x) <= FLEE_RADIUS:
                    惊 = f
                    break
    if 惊 is not None and 敌 is None:
        # 兽受惊而逃——但贪食的兽有时尚且驻足，猎人因此追得上
        if rng.random() < 0.6:
            _移(world, a, a.y + (a.y - 惊.y), a.x + (a.x - 惊.x), 疾走=True)
    elif 敌 is not None and p["食"] != "肉":
        群 = sum(1 for b in world.animals if b.种类 == a.种类 and b is not a
                 and abs(b.y - a.y) <= 2 and abs(b.x - a.x) <= 2)
        if rng.random() < p["勇"] * (0.4 + 0.2 * 群) * 曲:
            我力 = p["阳"] * 曲
            敌力 = BEASTS[敌.种类]["阳"] * 体曲(敌.年龄, BEASTS[敌.种类]["寿日"] * _tpd())
            if 我力 >= 敌力 * rng.uniform(0.8, 1.3):
                耗 = min(敌.阳, rng.uniform(8, 18))
                敌.阳 -= 耗
                world.qi.归还(敌.y, 敌.x, 阳=耗)
                if 敌.阳 <= 0:
                    兽亡(world, 敌)
                    world._events.append({"kind": "兽斗", "pos": (a.y, a.x),
                                          "actor": a.种类, "target": 敌.种类,
                                          "text": f"一头{a.种类}斗杀了来袭的{敌.种类}"
                                                  "（因：勇而起，群而起）"})
            else:
                耗 = min(a.阳, rng.uniform(8, 18))
                a.阳 -= 耗
                world.qi.归还(a.y, a.x, 阳=耗)
                _移(world, a, a.y + (a.y - 敌.y), a.x + (a.x - 敌.x), 疾走=True)
        else:
            _移(world, a, a.y + (a.y - 敌.y), a.x + (a.x - 敌.x), 疾走=True)
        return

    # 饥则食
    if a.阳 < p["阳"] * 0.55:
        if p["食"] == "肉":
            if _猎(world, a, p, rng, 曲):
                return
        else:
            _食素(world, a, p, rng, 曲)
            return

    # 渴则饮：寻近处活水
    if a.水分 < 40.0:
        if world.water[a.y, a.x] >= DRINK_MIN_BEAST:
            需 = (100.0 - a.水分) * BODY2FIELD
            取 = min(需, max(0.0, float(world.water[a.y, a.x]) - DRINK_KEEP))
            world.water[a.y, a.x] -= 取
            a.水分 += 取 / BODY2FIELD
            return
        水点 = [(y, x) for y, x in _近(world, a.y, a.x, SENSE_BEAST)
                if world.water[y, x] >= DRINK_MIN_BEAST]
        if 水点:
            ty, tx = min(水点, key=lambda q: abs(q[0] - a.y) + abs(q[1] - a.x))
            _移(world, a, ty, tx)
            return

    # 夜伏：夜里不动，养阳
    if 夜:
        return

    # 温饱则群聚、游荡；非群居者亦有求偶之驱（否则独居者永无后会）。
    # 求偶之目及远（旷野寻侣，半径三倍于感知）；群聚之目及近。
    同近 = [b for b in world.animals if b.种类 == a.种类 and b is not a
            and abs(b.y - a.y) <= SENSE_BEAST and abs(b.x - a.x) <= SENSE_BEAST]
    if p["群"] and 同近:
        近 = min(同近, key=lambda b: abs(b.y - a.y) + abs(b.x - a.x))
        if abs(近.y - a.y) + abs(近.x - a.x) > 2:
            _移(world, a, 近.y, 近.x)
            return
    elif rng.random() < 0.25:
        同远 = [b for b in world.animals if b.种类 == a.种类 and b is not a
                and abs(b.y - a.y) <= SENSE_BEAST * 3 and abs(b.x - a.x) <= SENSE_BEAST * 3]
        if 同远:
            远 = min(同远, key=lambda b: abs(b.y - a.y) + abs(b.x - a.x))
            if abs(远.y - a.y) + abs(远.x - a.x) > 2:
                _移(world, a, 远.y, 远.x)
                return
    if rng.random() < 0.35:
        _移(world, a, a.y + int(rng.integers(-1, 2)), a.x + int(rng.integers(-1, 2)))


def _食素(world, a, p, rng, 曲):
    """植食/杂食：就草虫而食（食入记日月之泵）；此处无食，向更丰处挪。"""
    旧 = a.阳
    if p["食"] == "虫":
        if world.insects[a.y, a.x] > 0.3:
            world.insects[a.y, a.x] -= 0.3
            a.阳 = min(p["阳"], a.阳 + 6.0 * 曲)
    else:
        if world.grass[a.y, a.x] > 0.25:
            world.grass[a.y, a.x] -= 0.2
            a.阳 = min(p["阳"], a.阳 + 5.0 * 曲)
    world.账.泵 += a.阳 - 旧
    if a.阳 > 旧:
        return
    场 = world.insects if p["食"] == "虫" else world.grass
    佳, 佳值 = None, 场[a.y, a.x]
    for y, x in _近(world, a.y, a.x, 1):
        if 场[y, x] > 佳值:
            佳, 佳值 = (y, x), 场[y, x]
    if 佳 is not None:
        a.y, a.x = 佳
    else:
        点 = [(y, x) for y, x in _近(world, a.y, a.x, SENSE_BEAST)
              if 场[y, x] > 场[a.y, a.x]]
        if 点:
            ty, tx = min(点, key=lambda q: abs(q[0] - a.y) + abs(q[1] - a.x))
            _移(world, a, ty, tx)


def _猎(world, a, p, rng, 曲) -> bool:
    """肉食：先噬尸（腐肉亦食），再猎活物——猎体型不逾己者，成群可猎大一阶。"""
    for c in list(world.carrions):
        if abs(c.y - a.y) <= 1 and abs(c.x - a.x) <= 1 and c.肉 > 0:
            c.肉 -= 1
            旧 = a.阳
            a.阳 = min(p["阳"], a.阳 + 12.0)
            world.账.泵 += a.阳 - 旧
            return True
    群 = sum(1 for b in world.animals if b.种类 == a.种类 and b is not a
             and abs(b.y - a.y) <= 3 and abs(b.x - a.x) <= 3)

    def 猎序(b):
        s = 体型序[BEASTS[b.种类]["体型"]]
        if 体曲(b.年龄, BEASTS[b.种类]["寿日"] * _tpd()) < 1.0:
            s -= 1        # 幼体弱小，体型降一阶视之（幼龙最易遭毒手）
        return s

    可猎 = [b for b in world.animals if b is not a and BEASTS[b.种类]["食"] != "肉"
            and abs(b.y - a.y) <= SENSE_BEAST and abs(b.x - a.x) <= SENSE_BEAST
            and 猎序(b) <= 体型序[p["体型"]] + (1 if 群 >= 2 else 0)]
    if not 可猎:
        return False
    猎 = min(可猎, key=lambda b: abs(b.y - a.y) + abs(b.x - a.x))
    if abs(猎.y - a.y) + abs(猎.x - a.x) <= 1:
        猎曲 = 体曲(猎.年龄, BEASTS[猎.种类]["寿日"] * _tpd())
        得手 = 0.35 + 0.3 * (曲 - 猎曲) + 0.1 * min(群, 3)   # 捕猎多失手：猎非易也
        if rng.random() < 得手:
            兽亡(world, 猎)
            world._events.append({"kind": "猎杀", "pos": (a.y, a.x),
                                  "actor": a.种类, "target": 猎.种类,
                                  "text": f"一头{a.种类}猎杀了{猎.种类}"
                                          f"{'幼体' if 猎曲 < 1.0 else ''}"
                                          "（因：饥饿驱动+弱肉强食）"})
        else:
            _移(world, 猎, 猎.y + (猎.y - a.y), 猎.x + (猎.x - a.x), 疾走=True)
        return True
    _移(world, a, 猎.y, 猎.x, 疾走=True)
    return True


def 繁衍(world, rng):
    """温饱且成对则繁殖：新生儿自炁凝聚（幼体，生而弱小，逐日抽条）。"""
    from .world import ANIMAL_MAX
    if len(world.animals) >= ANIMAL_MAX:
        return
    for i in range(len(world.animals)):
        for j in range(i + 1, len(world.animals)):
            x, y = world.animals[i], world.animals[j]
            if x.种类 != y.种类:
                continue
            if abs(x.y - y.y) + abs(x.x - y.x) > 2:
                continue
            p = BEASTS[x.种类]
            if x.阳 < p["阳"] * 0.6 or y.阳 < p["阳"] * 0.6:
                continue
            # 唯成年者可育（幼体不繁）
            if 体曲(x.年龄, p["寿日"] * _tpd()) < 1.0 \
                    or 体曲(y.年龄, p["寿日"] * _tpd()) < 1.0:
                continue
            if rng.random() < BREED_CHANCE:
                兽生(world, x.种类, x.y, x.x, rng, 幼体=True)
                return
