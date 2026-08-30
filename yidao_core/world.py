# -*- coding: utf-8 -*-
"""
《易道引擎》v6.0 "鱼缸" — 世界层 (world.py)

第一性原理（见 docs/engine-v6-lingti.md）：
  世界是世界，角色是角色。世界只遵循自身物质特性做固定变化。
  世界没有过去，没有未来，只有此时此刻——本模块不保存任何历史数组，
  一切场与对象皆为覆盖式的当前快照。

  万物由阴凝聚得一份阳而成形，阳逸散速率因材质而异，阳尽则坏灭降级、归还于土。
  底层逻辑永远是"能量影响形体的好坏"：
    日月运行（昼夜、寒暑）是世界的阴阳总源——白昼阳盛、夜晚阴盛、阴雨之日以阴为主；
    气温自阴阳推导，气温再影响蒸发、草木、作物、兽群、乃至灵的阳之逸散与食物腐坏。
  天气不是写死的日程：蒸发成云、风推云移、云厚积处概率成雨。
  茅草屋、农田、树木、火堆、走兽、尸骸——都是遵守同一阴阳物质模型的世界对象。
"""

from dataclasses import dataclass, field
import math
import numpy as np

try:
    from .qi import 炁场, 账, 封顶结算, FORM_YIN, BEAST_FORM_YIN, QI_GRASS_DRINK
except ImportError:  # 允许脚本方式直跑
    from qi import 炁场, 账, 封顶结算, FORM_YIN, BEAST_FORM_YIN, QI_GRASS_DRINK

# ───────────────────────────────────────────
# 0. 时间、格局与日月（阴阳总源）
# ───────────────────────────────────────────

TICKS_PER_DAY = 64      # 64 念 = 一日（世界的能量循环周期）
WORLD_SIZE = 32         # 32×32 鱼缸
SEASON_DAYS = 32        # 寒暑循环：约 32 日一个轮回（暖季 16 + 寒季 16）
DAYLEN_WARM = 46        # 暖季日照念数（昼长夜短）
DAYLEN_COLD = 36        # 寒季日照念数（昼短夜长）
SEASON_OFFSET = 12      # 开缸即暖季之末：寒季很快到来，生存压力才看得见


def cycle_day(tick: int) -> int:
    """今日在寒暑循环中的位置（0..SEASON_DAYS-1）。"""
    return (tick // TICKS_PER_DAY + SEASON_OFFSET) % SEASON_DAYS


def season_factor(tick: int) -> float:
    """季节系数：+1 仲夏（暖季正中），-1 仲冬（寒季正中）。"""
    return math.cos(2 * math.pi * (cycle_day(tick) - SEASON_DAYS // 4) / SEASON_DAYS)


def day_length(tick: int) -> int:
    """今日昼长：暖季长昼，寒季短昼。"""
    return DAYLEN_WARM if season_factor(tick) >= 0 else DAYLEN_COLD


def is_night(tick: int) -> bool:
    """昼夜的划分来自能量循环与季节，而非外加的开关。"""
    return tick % TICKS_PER_DAY >= day_length(tick)


def sunlight(tick: int) -> float:
    """日照强度 0~1：日出于旦，日昃于暮，夜里为零。"""
    if is_night(tick):
        return 0.0
    return math.sin(math.pi * (tick % TICKS_PER_DAY) / day_length(tick))


# ── 天气：风与云从能量场涌现 ──
EVAPORATE = 0.035       # 水每念蒸发基率（风加速之，寒缓之）
CLOUD_RAIN_AT = 1.0     # 云量超过此值方有雨意
RAIN_RATE = 0.80        # 成雨时每念降水量（暴雨倾盆，一场把云打薄）
SEEP = 0.0025           # 渗漏：水每念渗入土的基率（土燥则速，土润则缓）
SPRING_PRESSURE = 0.002 # 涌泉：每念涌出九泉存量的比例（潭愈满，泉愈涌，闭环之回流）
SPRING_TOTAL = 0.5      # （已废）旧涌泉每念总量上限——v7 起改为与九泉之压相称
CLOUD_DECAY = 0.9999    # 云气每念自然散逸（极慢——唯一的漏水口，防的是永涝）
WIND_WALK = 0.05        # 风向随机游走步长（弧度/念）
WIND_SPEED_WALK = 0.03  # 风力起伏步长
WIND_MAX = 0.8          # 风力上限（格/念）

# 湿度：由近期水量平滑得出（升快降慢）
MOIST_UP = 0.10
MOIST_DOWN = 0.008

# 草：湿度适中处生长，有上限；水淹与干旱皆伤草；寒季生长慢
GRASS_GROW = 0.03
GRASS_SUIT_CENTER = 0.50    # 最适湿度
GRASS_SUIT_WIDTH = 0.50     # 适生湿度带宽
GRASS_FLOOD = 2.5           # 水深超过此值草被淹死（深泽无草，浅滩无碍）
GRASS_DRY = 0.08            # 湿度低于此值草枯萎

# ── 建筑与农田 ──
HUT_YANG0 = 80.0        # 茅屋落成时的阳存量
HUT_LEAK_AT = 45.0      # 阳低于此值则漏雨（屋内休息打折）
HUT_RUIN_AT = 20.0      # 阳低于此值则残破（将塌）
HUT_DECAY = 0.030       # 茅屋每念阳逸散（草材质，速于木石）
HUT_RAIN_DMG = 0.055    # 雨淋损伤
HUT_WIND_DMG = 0.075    # 风损系数（×风力×高地加成）
HUT_FLOOD_DMG = 0.07    # 积水浸泡系数
HUT_MARK_TTL = 2 * TICKS_PER_DAY  # 屋骸印记保质期

FARM_MATURE = 96        # 农田成熟所需生长进度（约一日半，寒暖而异其速）
FARM_WITHER_DRY = 0.12  # 湿度低于此值，田开始枯萎
FARM_WITHER_MAX = 48    # 连续枯萎念数尽则田毁
FARM_FLOOD = 1.5        # 水深超过此值，田被淹坏
FARM_PEST = 1.2         # 虫密度超过此值，农田遭虫灾

# ── 生态：鱼、虫、树、石、藤 ──
FISH_CAP = 2.0          # 鱼群密度上限
FISH_GROW = 0.010       # 鱼群繁育基率（水温适宜则快）
INSECT_CAP = 2.0        # 虫密度上限
INSECT_GROW = 0.012     # 虫繁育基率（暖则速，霜则灭）
TREE_MAX = 60           # 树木总数上限
TREE_GROW = 0.015       # 树每念阳生长
TREE_SPREAD = 0.002     # 每念新树苗萌发概率（逐格）
STONE_CAP = 3.0         # 高地石料上限
STONE_REGEN = 0.0008    # 石料极缓慢再生（风化成砾）
VINE_CAP = 2.0          # 水泽边藤蔓上限
VINE_GROW = 0.010       # 藤蔓生长率

# ── 走兽：阴阳同构，凝聚得阳而生，阳尽而死 ──
ANIMAL_MAX = 45
# 兽种表已迁入兽层（beast.py）：食性、体型、群性、勇怯皆入表；
# 灵之世代畜牧所需（蛋期/奶期）亦在其中。此处转口，向后兼容。
from . import beast as _beast_mod
BEASTS = _beast_mod.BEASTS
BREED_CHANCE = _beast_mod.BREED_CHANCE
FLEE_RADIUS = _beast_mod.FLEE_RADIUS
CARRION_YANG = 25.0     # 尸骸初始阳（腐坏尽则归土）
CARRION_DECAY = 0.8     # 尸骸每念腐坏

# ── 火堆 ──
FIRE_YANG0 = 60.0       # 火堆初生之阳
FIRE_DECAY = 0.06       # 火每念燃损（须添柴）
FIRE_RAIN_DMG = 0.4     # 露天火遇雨急熄；屋内灶火无恙
FIRE_WARM_RADIUS = 2    # 火之暖煦所及
FIRE_FEED = 25.0        # 添一份木柴所续之阳
# 火相（五行相律）：星（将熄）/ 火 / 焰（旺）——烧制之事，需旺火方成
FIRE_EMBER = 20.0       # 阳低于此值，火相为"星"
FIRE_BLAZE = 45.0       # 阳高于此值，火相为"焰"
FIRE_ASH_GRASS = 0.25   # 火生土：火熄成灰，灰肥其土，草即荣之量

# ── 井与径（v6.4）：井是凿入九泉的水眼，径是众脚踏出来的路 ──
WELL_YANG0 = 70.0       # 井落成时的阳存量（石土之质，缓于茅屋）
WELL_DECAY = 0.012      # 井壁每念阳逸散
WELL_RAIN_SILT = 0.05   # 雨携泥淤井
WELL_SILT_AT = 25.0     # 井阳低于此值则淤塞，汲不得水，须淘浚
WELL_DRY_DEEP = 6.0     # 九泉存量低于此值，井水暂枯（打不出水）
WELL_DIG_TICKS = 16     # 凿井连续施工念数
WELL_MARK_TTL = 3 * TICKS_PER_DAY  # 井骸印记保质期

# 体水汇率：身体之水 1 点 = 场水 0.004（水过身体，只是转移，总量不变）
# 饮于泽、汲于井、灌于罐、汗溺之排、亡故之还——皆按此率在域内结算
BODY2FIELD = 0.004
DRINK_KEEP = 0.2        # 饮留水皮：饮水至多汲至场水余此值（泽不为一人而涸）

PATH_AT = 26.0          # 同一格被踩踏次数过此成"径"
PATH_DECAY = 0.012      # 径每念荒芜（久无人走则消失）
PATH_COST = 0.5         # 径上移动耗阳折半

# ── 物品：有阳存量、会腐坏，腐速因材质而异（鱼鲜最快，骨石最慢）──
ITEM_DECAY = {"生鱼": 0.09, "生肉": 0.06, "奶": 0.08, "蛋": 0.04, "果": 0.05,
              "熟肉": 0.02, "熟鱼": 0.02, "谷种": 0.005,
              "茅草": 0.010, "藤": 0.010, "木": 0.003, "石": 0.001, "骨": 0.0008,
              "石斧": 0.001, "石刀": 0.001, "鱼竿": 0.001, "耒耜": 0.001,
              "背篓": 0.001, "石矛": 0.001, "棍棒": 0.001,
              "土": 0.002, "沙": 0.001, "矿石": 0.001, "金块": 0.0008, "金刃": 0.0008,
              "陶罐": 0.001, "寒衣": 0.004,
              "骨饰": 0.0008, "美石": 0.001, "美贝": 0.0005}
ITEM_YANG = {"生鱼": 30.0, "生肉": 40.0, "奶": 25.0, "蛋": 35.0, "果": 22.0,
             "熟肉": 40.0, "熟鱼": 35.0, "谷种": 50.0,
             "茅草": 40.0, "藤": 40.0, "木": 60.0, "石": 80.0, "骨": 70.0,
             "土": 40.0, "沙": 35.0, "矿石": 70.0, "金块": 85.0,
             "陶罐": 60.0, "寒衣": 50.0,
             "骨饰": 70.0, "美石": 80.0, "美贝": 80.0}
ITEM_YANG_TOOL = 50.0   # 工具/武器初生之阳；使用中磨损，阳尽断裂
TOOL_WEAR = 1.5         # 工具每用一次磨损之阳

# ── 万物之形阴（C 域器物账）：生时自场抽取、灭时尽数归还 ──
# 物品之形阴 = 初生阳 × 0.4（形阳相随，规则免表）；建筑器物各有定数
YIN_HUT = 60.0          # 茅屋形阴（阳0=80）
YIN_FIRE = 30.0         # 火堆形阴（阳0=60）
YIN_FENCE = 40.0        # 围栏形阴（阳0=60）
# 井无形阴：井非阴阳凝聚之物，乃地形之变（如径），不在器物账内


def 物形阴(类型: str) -> float:
    """物品之形阴：初生阳的四成（形阳相随）。"""
    return ITEM_YANG.get(类型, ITEM_YANG_TOOL) * 0.4

# 物候事件的气温阈值
FROST_AT = 0.0          # 霜冻线
HEAT_AT = 30.0          # 酷暑线


@dataclass(eq=False)
class Item:
    """物品：一份阴凝聚的阳。草藤易腐，木石耐久，骨最不坏。
    陶罐另带一笔"盛水"——罐可储水，水尽则空。
    eq=False：物是实体不是数值——比较与移除皆按"是不是这同一个"（identity），
    杜绝两件数值相同的物被误认为同一个（储粮循环曾因此一物两处、分身有术）。"""
    类型: str
    阳: float = 0.0
    盛水: float = 0.0

    def __post_init__(self):
        if self.阳 <= 0:
            self.阳 = ITEM_YANG.get(self.类型, ITEM_YANG_TOOL)

    def 腐一步(self, 气温: float, 屋内: bool = False, 藏: float = 1.0) -> bool:
        """每念腐坏一步；寒季腐慢，屋内储粮更慢，陶罐藏粮亦缓。返回 True 表示已腐尽。"""
        rate = ITEM_DECAY.get(self.类型, 0.001)
        rate *= float(np.clip(0.5 + 气温 / 30.0, 0.3, 1.8))
        if 屋内:
            rate *= 0.5
        rate *= 藏
        self.阳 -= rate
        return self.阳 <= 0


@dataclass
class Mark:
    """印记：角色行为在世界留下的物理痕迹，有保质期，随时间衰减消失。"""
    类型: str          # 刻痕 / 尸骨 / 屋骸
    y: int
    x: int
    诞生念: int
    保质期: int        # 以念计
    标签: str | None = None   # 痕迹所系之名（如尸骨属于谁）；世界不解释它，只携带它

    def 尚存(self, tick: int) -> bool:
        return tick - self.诞生念 < self.保质期


@dataclass
class Building:
    """茅草屋：阴凝聚得阳的物质结构。阳缓慢逸散，风雨积水皆损之，阳尽则塌。"""
    y: int
    x: int
    主人: str          # 门楣上的名——所有权的社会记忆存在众灵心里，这里只是物理标签
    阳: float = HUT_YANG0
    仓储: list = field(default_factory=list)   # 屋内储物（腐坏减半）

    @property
    def 状态(self) -> str:
        if self.阳 > HUT_LEAK_AT:
            return "完好"
        if self.阳 > HUT_RUIN_AT:
            return "漏雨"
        return "残破"


@dataclass
class Farm:
    """农田：人垦的一畦。随气温生长，会枯，会被水淹坏，虫盛则遭灾。"""
    y: int
    x: int
    主人: str
    播种念: int
    进度: float = 0.0
    枯萎: float = 0.0

    def 成熟(self, tick: int) -> bool:
        return self.进度 >= FARM_MATURE


@dataclass
class Tree:
    """树木：缓慢生长的世界对象。可伐取木；阳尽而枯。
    五行相律（木）：木固土——近树之土，根柢盘结，不易溃为沙；
    果树暖季结实，可采食；寒季落尽，还于土。"""
    y: int
    x: int
    阳: float = 10.0
    果树: bool = False
    果数: int = 0


@dataclass
class Carrion:
    """尸骸：兽死之躯，鲜肉与骨材料，腐坏尽则归还于土。"""
    y: int
    x: int
    肉: int
    骨: int
    阳: float = CARRION_YANG
    名: str = ""        # 生前种类


@dataclass
class Animal:
    """走兽：轻量个体。吃草/饮水/受惊逃/繁殖/衰老死亡——与灵同一个阴阳模型。
    亦有体水（水过兽身，总量不变）；野性本能循环见兽层（beast.py）。"""
    种类: str
    y: int
    x: int
    阳: float
    年龄: int = 0
    驯主: str | None = None
    栏位: tuple | None = None     # 圈养锚点
    产物念: int = 0               # 距下次下蛋/可挤奶的剩余念数
    水分: float = 80.0            # 体水：渴则饮，汗溺还场

    @property
    def 驯化(self) -> bool:
        return self.驯主 is not None


@dataclass
class Fireplace:
    """火堆：木柴之阳的缓慢释放。需添柴维续；露天遇大雨则熄，屋内灶火安全。"""
    y: int
    x: int
    主人: str
    阳: float = FIRE_YANG0
    屋内: bool = False


@dataclass
class Fence:
    """围栏：圈养之所。草木质，缓腐。"""
    y: int
    x: int
    主人: str
    阳: float = 60.0


@dataclass
class Well:
    """井：凿入九泉的水眼——地形之变，非阴阳凝聚之物。
    水脉本在地底，人只是把泥土掘开获得一个取水的入口（与径同类）。
    其"阳"实为井壁的通畅度（如径之踩踏数，是地形的状态，不在能量账内）：
    雨携泥入、用久则淤（通畅 <25 汲不得水，知法者可淘浚复之）；
    九泉涸则井暂枯；通畅尽则塌淤成坑，留井骸印记。"""
    y: int
    x: int
    主人: str
    阳: float = WELL_YANG0

    @property
    def 状态(self) -> str:
        if self.阳 <= 0:
            return "废"
        if self.阳 < WELL_SILT_AT:
            return "淤"
        return "活"


class World:
    """鱼缸世界：只有此刻，不存历史。"""

    def __init__(self, seed: int, size: int = WORLD_SIZE, init_map=None,
                 兽群: str = "田园"):
        """创世两条路：不给分布图，则从炁场自生（道生一）；给分布图，则以图为炁。
        兽群：田园（鸡羊牛，灵之世代的畜牧对象）/ 侏罗纪（角龙梁龙迅猛龙）。"""
        self.size = size
        self.tick = 0
        self._rng = np.random.default_rng(seed)

        if init_map is None:
            from .genesis import 炁场极化, 凝聚成形
            Q = 炁场极化(size, seed)
            self.height, self.water, self.cloud = 凝聚成形(Q, self._rng)
        else:
            from .genesis import 从分布图
            self.height, self.water, self.cloud = 从分布图(init_map, size)

        # 当前快照诸场（无历史）：水、云、湿度、草、气温、阳氛
        # 创世纪土壤含墒（由太古之水推导）；墒情合适处，太古草木已先生
        self.moisture = np.clip(self.water / 1.5, 0.0, 1.0) * 0.8
        宜草 = np.clip(1.0 - np.abs(self.moisture - GRASS_SUIT_CENTER) / GRASS_SUIT_WIDTH,
                       0.0, 1.0)
        self.grass = 宜草 * 0.5 * (self.water < GRASS_FLOOD)
        self.temp = np.full((size, size), 15.0)     # 气温场（每念重算）
        self.yang_qi = np.zeros((size, size))       # 阳氛场：白昼阳盛、阴雨阴盛
        self.fish = np.zeros((size, size))          # 鱼群密度（水域）
        self.insects = np.zeros((size, size))       # 虫密度（草丛）
        self.stone = np.zeros((size, size))         # 石料（高地）
        self.vine = np.zeros((size, size))          # 藤蔓（水泽边）
        self.stone[self.height >= 6.5] = self._rng.uniform(1, 3, int((self.height >= 6.5).sum()))
        self.marks: list[Mark] = []
        self.relics: list[dict] = []   # 无主遗物：{名, y, x, 物, 念}，日久归还于土
        self.buildings: list[Building] = []
        self.farms: list[Farm] = []
        self.trees: list[Tree] = []
        self.carrions: list[Carrion] = []
        self.animals: list[Animal] = []
        self.fires: list[Fireplace] = []
        self.fences: list[Fence] = []
        self.wells: list[Well] = []
        # 径：众脚踏出来的路。记录在世界里——每有一灵踏上一格，tread 加一；
        # 久无人走则荒芜消失。是当前快照场，不是历史。
        self.tread = np.zeros((size, size))
        self._tread_was = np.zeros((size, size))   # 上一念的踩踏场（径成跳变检测用）

        # 风：有方向有强度，随机起伏（区域气压差的简化涌现）
        self.wind_angle = float(self._rng.uniform(0, 2 * np.pi))
        self.wind_speed = float(self._rng.uniform(0.05, 0.3))
        self._cloud_ox = 0.0              # 云团亚格位移积累
        self._cloud_oy = 0.0
        self._深潭 = 0.0                   # 九泉：渗入土中之水的归处（闭环守恒的一库）

        # 炁场与守恒账（宇宙底座第一律，见 qi.py）：常驻能量场，处处皆满；
        # 逸散就地归还、凝聚就地抽取；四笔流水，笔笔有出处。
        self.qi = 炁场(size)
        self.账 = 账()

        # 天气状态（供灵体层查询：此刻我头顶在下雨吗）
        self.rain_mask = np.zeros((size, size), dtype=bool)
        self.rain_episodes = 0            # 成雨场次（无雨→有雨的跳变计数）
        self._was_raining = False
        self._rain_end = -64              # 上一场雨离场的念
        self.collapsed_huts = 0           # 累计塌屋数
        self._pheno_done: set = set()     # 本寒暑已报过的物候节点

        # 世界层事件（塌屋、田枯、兽死、物候等），由观测层逐念取走——世界自己不记
        self._events: list[dict] = []

        # 创世树与兽群：阴凝聚得阳，散于水草之间
        # 五行相律（木）：树木有品类——约三成为果树，暖季结实可采食
        for _ in range(14):
            y, x = int(self._rng.integers(0, size)), int(self._rng.integers(0, size))
            if self.moisture is not None:
                self.trees.append(Tree(y, x, float(self._rng.uniform(20, 90)),
                                       果树=bool(self._rng.random() < 0.3)))
        群 = {"田园": {"鸡": 6, "羊": 4, "牛": 3},
              "侏罗纪": {"角龙": 6, "梁龙": 2, "迅猛龙": 4, "始祖鸟": 5}}[兽群]
        for 种类, 数 in 群.items():
            for _ in range(数):
                y, x = int(self._rng.integers(0, size)), int(self._rng.integers(0, size))
                # 创世兽群亦自炁凝聚：初阳形阴体水皆有所出（兽生落地即壮年）
                _beast_mod.兽生(self, 种类, y, x, self._rng)

        # 预流：让世界先静转两日，风云水草各归其位
        for _ in range(TICKS_PER_DAY * 2):
            self._物理步(预热=True)
        self.tick = 0
        self.marks = []
        self.rain_episodes = 0
        self._events = []
        self._pheno_done = set()
        self.账.归零()      # 预流期间的流水不入账——账本与念时同起点

    # ───────────────────────────────────────
    # 一、物理推进（世界自行运转，不问角色）
    # ───────────────────────────────────────

    def step(self, spirits: list | None = None):
        """推进一念：日月阴阳、风云雨、水流、湿度、草、生态、建筑农田、印记衰减。"""
        self._物理步(预热=False)
        if spirits is not None:
            self._生态步(spirits)
        self.tick += 1

    def _物理步(self, 预热: bool):
        n = self.size
        t = self.tick

        # 日月阴阳：阳氛 = 日照 × 季节 ± 云雨风修正——白昼阳盛，阴雨阴盛
        日 = sunlight(t)
        季 = season_factor(t)
        base_temp = 15.0 + 13.0 * 季
        云蔽 = np.clip(self.cloud / 2.0, 0.0, 1.0)
        self.yang_qi = 日 * max(0.2, 季 + 1.0) * (1.0 - 云蔽 * 0.7) - self.rain_mask * 0.4
        self.temp = (base_temp + 8.0 * 日 * (1.0 - 云蔽 * 0.6)
                     - (4.0 if is_night(t) else 0.0)
                     - self.rain_mask * 6.0 - self.wind_speed * 2.0
                     - self.height * 0.3)
        温均 = float(self.temp.mean())

        # 风：方向与强度皆随机起伏（简化涌现）
        self.wind_angle = float(self.wind_angle + self._rng.normal(0, WIND_WALK)) % (2 * np.pi)
        self.wind_speed = float(np.clip(
            self.wind_speed + self._rng.normal(0, WIND_SPEED_WALK), 0.0, WIND_MAX))

        # 蒸发：水化为云；风燥则旺，天寒则缓。蒸一升水，成一分云，守恒。
        温蒸 = float(np.clip(0.4 + 温均 / 25.0, 0.3, 1.6))
        ev = np.minimum(self.water, EVAPORATE * (0.6 + self.wind_speed) * 温蒸)
        self.water -= ev
        self.cloud += ev

        # 云随风移（亚格积累 + 整数滚移），兼有扩散与散逸
        self._cloud_oy += np.cos(self.wind_angle) * self.wind_speed
        self._cloud_ox += np.sin(self.wind_angle) * self.wind_speed
        shy, shx = int(self._cloud_oy), int(self._cloud_ox)
        if shy or shx:
            self.cloud = np.roll(self.cloud, (shy, shx), (0, 1))
            self._cloud_oy -= shy
            self._cloud_ox -= shx
        blur = (np.roll(self.cloud, 1, 0) + np.roll(self.cloud, -1, 0)
                + np.roll(self.cloud, 1, 1) + np.roll(self.cloud, -1, 1)) / 4.0
        # 扩散宜弱：云须能在水泽上空积出局部厚云，雨才有地方性
        # 云气散逸：按宇宙底座第一律记越界出账（散于宇宙之外的唯一排气口，防的是永涝）
        混 = self.cloud * 0.98 + blur * 0.02
        散 = 混 * (1.0 - CLOUD_DECAY)
        self.cloud = 混 - 散
        self.账.越界A -= float(散.sum())

        # 雨：云厚积处概率性成雨——概率随超阈云量平方增长，
        # 薄云难雨、厚云倾盆，雨因此成"场"，而非日日均匀的毛毛雨
        过阈 = np.clip(self.cloud - CLOUD_RAIN_AT, 0.0, None)
        prob = np.clip(过阈 ** 2 * 2.0, 0.0, 0.7)
        self.rain_mask = self._rng.random((n, n)) < prob
        雨量 = np.minimum(self.cloud * 0.45, RAIN_RATE) * self.rain_mask
        self.water += 雨量
        self.cloud -= 雨量        # 水量守恒：雨即云之化身，一两不多一两不少
        np.clip(self.cloud, 0.0, None, out=self.cloud)
        # 一场"雨"的判据：成雨面积越过 2% 为一场；场与场之间须隔 16 念晴隙
        raining_now = bool((self.rain_mask.mean() > 0.02))
        if raining_now and not self._was_raining:
            if t - self._rain_end > 16:
                self.rain_episodes += 1
            self._was_raining = True
        elif not raining_now and self._was_raining:
            self._was_raining = False
            self._rain_end = t

        # 水往低处流：每念向更低的邻居让出一部分（八邻，快照式结算）。
        # 守恒结算（封顶结算）：承诺的总出流不得超过该格实有——
        # 多方向承诺超出的部分按比例压缩，能量不生不灭（修水流复制之漏）。
        level = self.height + self.water
        flows = []
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if dy == 0 and dx == 0:
                    continue
                sy = slice(0, n - dy) if dy > 0 else slice(-dy, n)
                ty = slice(dy, n) if dy > 0 else slice(0, n + dy)
                sx = slice(0, n - dx) if dx > 0 else slice(-dx, n)
                tx = slice(dx, n) if dx > 0 else slice(0, n + dx)
                diff = level[sy, sx] - level[ty, tx]
                f = np.clip((diff - 0.02) * 0.16, 0.0, None)
                f = np.minimum(f, self.water[sy, sx] * 0.2)
                flows.append((sy, sx, ty, tx, f))
        self.water = np.maximum(self.water + 封顶结算(self.water, flows), 0.0)

        # 渗漏与九泉：水渗入土，归于九泉（阴）；九泉满则低洼处涌泉，涸则止。
        # 水 → 云 → 雨 → 水 → 土 → 九泉 → 泉 —— 闭环守恒，世界因此不涝不涸
        渗 = np.minimum(self.water, SEEP * np.clip(1.2 - self.moisture, 0.2, 1.2))
        self.water -= 渗
        self._深潭 += float(渗.sum())
        if self._深潭 > 0.0:
            # 泉生于谷畔，不注深潭：涌向低而尚干的土地，不成则在潭中蛰伏。
            # 涌泉之量与九泉之压相称（潭愈满，泉愈涌），且不得漫过洼地之容——
            # 渗漏是慢管、涌泉是压管，地表既不涸亦不涝，闭环才真的转得动。
            低洼 = (self.height <= np.percentile(self.height, 15)) & (self.water < 1.0)
            泉数 = int(低洼.sum())
            if 泉数:
                可容 = float(np.sum(1.0 - self.water[低洼]))
                涌 = min(self._深潭, self._深潭 * SPRING_PRESSURE, 可容)
                if 涌 > 0.0:
                    self.water[低洼] += 涌 / 泉数
                    self._深潭 -= 涌

        # 湿度：近期水量的平滑记忆（世界唯一的"记性"，亦只是场的惯性）
        inst = np.clip(self.water / 1.5, 0.0, 1.0)
        rate = np.where(inst > self.moisture, MOIST_UP, MOIST_DOWN)
        self.moisture += (inst - self.moisture) * rate
        np.clip(self.moisture, 0.0, 1.0, out=self.moisture)

        # 草：湿度适中则生，暖季速寒季缓，水淹则溺，干旱则枯。
        # 五行相律（土）：泥最荣，土次之，干瘠薄，沙难生——相态系数修其生长
        温生 = float(np.clip(温均 / 18.0, 0.2, 1.3))
        suit = np.clip(1.0 - np.abs(self.moisture - GRASS_SUIT_CENTER) / GRASS_SUIT_WIDTH, 0.0, 1.0)
        沙 = (self.water >= 1.5) | (self.moisture < 0.08)     # 土相为沙：极干硬碎或水蚀过甚
        相系 = np.where(沙, 0.2, 1.0)
        self.grass += GRASS_GROW * 温生 * suit * 相系 * (1.0 - self.grass)
        # 草汲炁（逸散即播种）：场中之阳养草木——众生沿途归还之能量，经场转手喂给后来者
        汲 = np.minimum(self.qi.yang, QI_GRASS_DRINK) * 温生 * suit * 相系 * (1.0 - self.grass)
        self.qi.yang -= 汲
        self.grass += 汲 * 0.5
        self.账.草汲 += float(汲.sum())
        self.grass[self.water > GRASS_FLOOD] -= 0.05
        self.grass[(self.water >= 1.5) & (self.water <= GRASS_FLOOD)] -= 0.02   # 水蚀成沙，草亦难立
        self.grass[self.moisture < GRASS_DRY] -= 0.008
        np.clip(self.grass, 0.0, 1.0, out=self.grass)

        # 鱼：水域之中，水温宜则繁，严寒酷暑则减
        水域 = self.water > 0.8
        鱼率 = FISH_GROW * float(np.clip(1.0 - abs(温均 - 18.0) / 20.0, 0.0, 1.0))
        self.fish[水域] += 鱼率 * (1.0 - self.fish[水域] / FISH_CAP)
        self.fish[~水域] = 0.0
        np.clip(self.fish, 0.0, FISH_CAP, out=self.fish)

        # 虫：草丛之中，暖则孳生，霜则死灭
        草丛 = self.grass > 0.2
        虫率 = INSECT_GROW * float(np.clip(温均 / 20.0, 0.0, 1.2))
        self.insects[草丛] += 虫率 * (1.0 - self.insects[草丛] / INSECT_CAP)
        self.insects[~草丛] = 0.0
        if 温均 < FROST_AT:
            self.insects *= 0.95
        np.clip(self.insects, 0.0, INSECT_CAP, out=self.insects)

        # 树：缓慢生长，缓慢繁衍；果树暖季结实、寒季落尽（还于土，生物质循环）
        for tree in list(self.trees):
            tree.阳 = min(100.0, tree.阳 + TREE_GROW)
            if 温均 < FROST_AT - 5.0:
                tree.阳 -= 0.05     # 严寒伤木
                if tree.阳 <= 0:
                    self.trees.remove(tree)
            # 果树结实：暖季渐熟（两念一果，至多三枚），寒季落尽
            if tree.果树:
                if 季 > 0.0 and tree.阳 > 40.0 and self._rng.random() < 0.02:
                    tree.果数 = min(3, tree.果数 + 1)
                elif 季 < -0.3:
                    tree.果数 = 0
        if len(self.trees) < TREE_MAX and self._rng.random() < TREE_SPREAD * n * n:
            湿区 = (self.moisture > 0.3) & (self.water < 1.0)
            ys, xs = np.nonzero(湿区)
            if len(ys):
                i = int(self._rng.integers(0, len(ys)))
                self.trees.append(Tree(int(ys[i]), int(xs[i]),
                                       果树=bool(self._rng.random() < 0.3)))

        # 石：高地风化成砾，极缓慢再生；藤：水泽边蔓延
        高地 = self.height >= 6.5
        self.stone[高地] = np.minimum(self.stone[高地] + STONE_REGEN, STONE_CAP)
        泽畔 = (self.moisture > 0.45) & (self.water < 1.5)
        self.vine[泽畔] = np.minimum(self.vine[泽畔] + VINE_GROW * 温生, VINE_CAP)
        self.vine[~泽畔] = np.maximum(self.vine[~泽畔] - 0.005, 0.0)

        if 预热:
            return

        # 物候节点：寒暑交替、初霜、酷暑——天地自有节律
        self._物候(t, 季, 温均)

        # 建筑：阳之逸散 + 风雨积水之损——逸散与剥蚀皆就地归还炁场（物归）；
        # 阳尽则塌，形阴与仓储之余尽数归还，化为屋骸
        for b in list(self.buildings):
            损 = HUT_DECAY
            if self.rain_mask[b.y, b.x]:
                损 += HUT_RAIN_DMG * (1.5 if b.阳 < HUT_LEAK_AT else 1.0)
            损 += self.wind_speed * HUT_WIND_DMG * (1.0 + self.height[b.y, b.x] / 9.0 * 1.5)
            if self.water[b.y, b.x] > 0.8:
                损 += (self.water[b.y, b.x] - 0.8) * HUT_FLOOD_DMG
            if self.temp[b.y, b.x] < FROST_AT:
                损 += 0.01     # 冻裂
            耗 = min(损, b.阳)
            b.阳 -= 耗
            self.物归(b.y, b.x, 耗)
            # 屋内仓储：腐坏减半（仓储的意义）；腐者之量亦归还炁场
            气温b = float(self.temp[b.y, b.x])
            存仓 = []
            for it in b.仓储:
                旧 = it.阳
                if it.腐一步(气温b, 屋内=True):
                    self.物归(b.y, b.x, 旧 + 物形阴(it.类型))
                else:
                    self.物归(b.y, b.x, 旧 - it.阳)
                    存仓.append(it)
            b.仓储 = 存仓
            if b.阳 <= 0:
                self.buildings.remove(b)
                self.物归(b.y, b.x, YIN_HUT
                          + sum(it.阳 + 物形阴(it.类型) for it in b.仓储))
                self.collapsed_huts += 1
                self.add_mark("屋骸", b.y, b.x, HUT_MARK_TTL, 标签=b.主人)
                self._events.append({
                    "kind": "塌屋", "pos": (b.y, b.x), "actor": b.主人,
                    "text": f"{b.主人} 的茅屋塌了（因：风雨剥蚀，阳尽则坏）"})

        # 农田：随气温生长；枯于旱，毁于淹，损于虫
        for f in list(self.farms):
            if self.moisture[f.y, f.x] < FARM_WITHER_DRY:
                f.枯萎 += 1.0
            elif self.water[f.y, f.x] > FARM_FLOOD:
                f.枯萎 += 2.0
            else:
                f.枯萎 = max(0.0, f.枯萎 - 0.5)
                f.进度 += float(np.clip(self.temp[f.y, f.x] / 18.0, 0.2, 1.3))
            if self.insects[f.y, f.x] > FARM_PEST:
                f.枯萎 += 0.5   # 虫灾啮苗
            if f.枯萎 >= FARM_WITHER_MAX:
                self.farms.remove(f)
                self._events.append({
                    "kind": "田枯", "pos": (f.y, f.x), "actor": f.主人,
                    "text": f"{f.主人} 的农田毁了（因：水土失调）"})

        # 火堆：燃柴续阳，燃损归还炁场；露天遇雨则熄，形阴亦还
        for f in list(self.fires):
            耗 = min(FIRE_DECAY, f.阳)
            f.阳 -= 耗
            self.物归(f.y, f.x, 耗)
            if not f.屋内 and self.rain_mask[f.y, f.x]:
                耗 = min(FIRE_RAIN_DMG, f.阳)
                f.阳 -= 耗
                self.物归(f.y, f.x, 耗)
            if f.阳 <= 0:
                self.fires.remove(f)
                self.物归(f.y, f.x, YIN_FIRE)
                # 火生土：火熄成灰，灰肥其土——烧尽之结，恰是草木之粮
                self.grass[f.y, f.x] = min(1.0, self.grass[f.y, f.x] + FIRE_ASH_GRASS)
                self._events.append({
                    "kind": "火熄", "pos": (f.y, f.x), "actor": f.主人,
                    "text": f"{f.主人} 的火堆熄了（因：薪尽而火传难继）"})

        # 尸骸腐坏，尽则归土（尸为泵所养之生物质，不入器物账）；围栏缓腐，腐者归还
        for c in list(self.carrions):
            c.阳 -= CARRION_DECAY * float(np.clip(0.5 + self.temp[c.y, c.x] / 30.0, 0.3, 1.8))
            if c.阳 <= 0:
                self.carrions.remove(c)
        for fe in list(self.fences):
            耗 = min(0.01, fe.阳)
            fe.阳 -= 耗
            self.物归(fe.y, fe.x, 耗)
            if fe.阳 <= 0:
                self.fences.remove(fe)
                self.物归(fe.y, fe.x, YIN_FENCE)

        # 井：井壁渐淤（雨携泥入、用久则淤）——井为地形之变，非器物，
        # 其"阳"是通畅度（地形之状态，如径之踩踏数），不在能量账内。
        # 五行相律（土）：沙地凿井易塌——沙无结构性，井壁通畅三倍速溃
        for wl in list(self.wells):
            沙蚀 = 3.0 if self.土相(wl.y, wl.x) == "沙" else 1.0
            wl.阳 -= WELL_DECAY * 沙蚀
            if self.rain_mask[wl.y, wl.x]:
                wl.阳 -= WELL_RAIN_SILT
            if wl.阳 <= 0:
                self.wells.remove(wl)
                self.add_mark("井骸", wl.y, wl.x, WELL_MARK_TTL, 标签=wl.主人)
                self._events.append({
                    "kind": "井废", "pos": (wl.y, wl.x), "actor": wl.主人,
                    "text": f"{wl.主人} 凿的井塌淤成坑（因：年久失淘，阳尽则废）"})

        # 径：久无人走则荒芜；踩踏过阈则成径——村落间的路自己长出来
        np.subtract(self.tread, PATH_DECAY, out=self.tread)
        np.maximum(self.tread, 0.0, out=self.tread)
        新径 = (self.tread >= PATH_AT) & (self._tread_was < PATH_AT)
        if 新径.any():
            ys, xs = np.nonzero(新径)
            for y, x in zip(ys.tolist(), xs.tolist()):
                self._events.append({
                    "kind": "径成", "pos": (y, x), "actor": None,
                    "text": f"此处众脚往复，踏出了一条径（因：踩踏日久+世上本无路）"})
        self._tread_was[:] = self.tread

        # 印记随时间衰减消失——世界不可能永久一成不变
        self.marks = [m for m in self.marks if m.尚存(t)]
        # 无主遗物亦如此：日久归土——物之余阳与形阴，尽数归还炁场
        存遗 = []
        for r in self.relics:
            if t - r["念"] < 3 * TICKS_PER_DAY:
                存遗.append(r)
            else:
                for it in r["物"]:
                    self.物归(r["y"], r["x"], it.阳 + 物形阴(it.类型))
        self.relics = 存遗

    def _物候(self, tick: int, 季: float, 温均: float):
        """寒暑节点入流：寒潮、酷暑、初霜——每一寒暑只报一次。"""
        轮 = tick // (TICKS_PER_DAY * SEASON_DAYS)
        cd = cycle_day(tick)
        if cd == SEASON_DAYS // 2 and ("寒潮", 轮) not in self._pheno_done:
            self._pheno_done.add(("寒潮", 轮))
            self._events.append({"kind": "物候", "pos": None, "actor": None,
                                 "text": "【物候】寒潮来袭，天地转阴（因：寒暑循环，阴长阳消）"})
        if cd == 0 and ("回暖", 轮) not in self._pheno_done:
            self._pheno_done.add(("回暖", 轮))
            self._events.append({"kind": "物候", "pos": None, "actor": None,
                                 "text": "【物候】春回大地，阳气始生（因：寒暑循环，阴极阳生）"})
        if cd == SEASON_DAYS // 4 and ("酷暑", 轮) not in self._pheno_done:
            self._pheno_done.add(("酷暑", 轮))
            self._events.append({"kind": "物候", "pos": None, "actor": None,
                                 "text": "【物候】酷暑正盛，阳极之至（因：日长夜短，阳盛至极）"})
        if 温均 < FROST_AT and ("初霜", 轮) not in self._pheno_done:
            self._pheno_done.add(("初霜", 轮))
            self._events.append({"kind": "物候", "pos": None, "actor": None,
                                 "text": "【物候】入冬第一场霜，草木凋、虫声绝（因：气温跌破霜冻线）"})

    # ───────────────────────────────────────
    # 二、生态步：走兽的生死（轻量个体，同一阴阳模型）
    # ───────────────────────────────────────

    def _生态步(self, spirits: list):
        """圈养者守旧制（栏畔牲畜）；野性者入兽层本能循环（见 beast.py）。"""
        rng = self._rng
        for a in list(self.animals):
            if a not in self.animals:
                continue
            p = BEASTS[a.种类]
            # 圈养者：守在栏畔，不肯走远
            if a.驯化 and a.栏位 is not None:
                扣 = min(a.阳, p["逸散"])
                a.阳 -= 扣
                self.qi.归还(a.y, a.x, 阳=扣)
                a.年龄 += 1
                a.产物念 = max(0, a.产物念 - 1)
                if a.阳 <= 0 or a.年龄 > p["寿日"] * TICKS_PER_DAY * rng.uniform(0.9, 1.1):
                    _beast_mod.兽亡(self, a)
                    self._events.append({
                        "kind": "畜死", "pos": (a.y, a.x), "actor": a.驯主,
                        "text": f"{a.驯主} 的{a.种类}病死了（因：饲养不周，阳尽则亡）"})
                    continue
                py, px = a.栏位
                if abs(a.y - py) + abs(a.x - px) > 4:
                    a.y += int(np.sign(py - a.y))
                    a.x += int(np.sign(px - a.x))
                elif rng.random() < 0.3:
                    a.y = int(np.clip(a.y + rng.integers(-1, 2), 0, self.size - 1))
                    a.x = int(np.clip(a.x + rng.integers(-1, 2), 0, self.size - 1))
                # 圈养久饥则野化逃逸
                if a.阳 < p["阳"] * 0.25 and rng.random() < 0.02:
                    a.驯主 = None
                    a.栏位 = None
                self._兽食(a, p)
                continue
            # 野性：兽层本能循环（饥则食、渴则饮、敌至则逃或斗）
            _beast_mod.兽行(self, a, spirits, rng)
        _beast_mod.繁衍(self, rng)

    def _兽食(self, a: Animal, p: dict):
        """兽食其食：鸡啄虫，羊牛啮草。鸡所过处，虫灾自减。
        食入之阳来自生物质——记日月之泵（太阳能经草木鱼虫入链）。"""
        旧 = a.阳
        if p["食"] == "虫":
            if self.insects[a.y, a.x] > 0.3:
                self.insects[a.y, a.x] -= 0.3
                a.阳 = min(p["阳"], a.阳 + 6.0)
        else:
            if self.grass[a.y, a.x] > 0.25:
                self.grass[a.y, a.x] -= 0.2
                a.阳 = min(p["阳"], a.阳 + 5.0)
        self.账.泵 += a.阳 - 旧

    # ───────────────────────────────────────
    # 三、天道用的最小干预接口（只修世界层）
    # ───────────────────────────────────────

    def gather_clouds(self):
        """聚云致雨：引九泉之水汽上腾为云——天道不造新水，只搬旧水。"""
        引 = min(self._深潭, 80.0)
        self._深潭 -= 引
        self.cloud += 引 / (self.size * self.size)

    def fertility_pulse(self):
        """肥力脉冲：湿度尚可之处，草一次性返青。"""
        mask = self.moisture > 0.22
        self.grass[mask] = np.maximum(self.grass[mask], 0.55)

    # ───────────────────────────────────────
    # 四、查询接口（只读此刻）
    # ───────────────────────────────────────

    def drain_events(self) -> list[dict]:
        """观测层每念取走世界事件；世界自取自忘。"""
        ev, self._events = self._events, []
        return ev

    def raining_on(self, y: int, x: int) -> bool:
        return bool(self.rain_mask[y, x])

    def building_at(self, y: int, x: int) -> Building | None:
        for b in self.buildings:
            if b.y == y and b.x == x:
                return b
        return None

    def fire_near(self, y: int, x: int, r: int = FIRE_WARM_RADIUS) -> Fireplace | None:
        for f in self.fires:
            if abs(f.y - y) <= r and abs(f.x - x) <= r:
                return f
        return None

    def well_at(self, y: int, x: int) -> Well | None:
        for w in self.wells:
            if w.y == y and w.x == x:
                return w
        return None

    def 汲井(self, well: Well, 需: float = 0.0) -> str:
        """从井里打水。井水取自九泉：身体所需之水自九泉转入身体（域内转移）。
        返回 "活"（得饮）/ "淤"（淤塞须淘）/ "枯"（九泉暂涸）。"""
        if well.状态 == "淤":
            return "淤"
        if self._深潭 < WELL_DRY_DEEP:
            return "枯"
        取 = min(需, self._深潭 - WELL_DRY_DEEP + 0.001)
        self._深潭 -= max(0.0, 取)      # 九泉之水入灵之口——域内转移，不入越界账
        well.阳 -= 0.3      # 汲用亦损井
        return "活"

    # ── 守恒接口（宇宙底座第一律的入账/归账/总量）──

    def 生灵入账(self, s):
        """凝聚成形：新灵之初阳与形阴自炁场抽取（阴向之收敛），不足则记越界；
        初生之躯所含之水，自当地场水（不足则九泉）转入身体——水过身体，总量不变。"""
        实阳, 实阴 = self.qi.抽取(s.y, s.x, 阳=s.yang, 阴=FORM_YIN)
        self.账.越界B += (s.yang - 实阳) + (FORM_YIN - 实阴)
        需 = s.水分 * BODY2FIELD
        取 = min(需, float(self.water[s.y, s.x]))
        self.water[s.y, s.x] -= 取
        欠 = 需 - 取
        if 欠 > 0.0:
            引 = min(self._深潭, 欠)
            self._深潭 -= 引
            欠 -= 引
        if 欠 > 0.0:
            self.账.越界A += 欠      # 四野滴水全无，唯越界补之（殆不曾见）

    def 生灵归账(self, y: int, x: int, 阳余: float, 水分余: float = 0.0):
        """坏灭倾覆：余阳与形阴尽数归还炁场；躯中残水就地还场——
        形成、存在、消亡、回归，四步两清。"""
        self.qi.归还(y, x, 阳=max(0.0, 阳余), 阴=FORM_YIN)
        if 水分余 > 0.0:
            self.water[y, x] += 水分余 * BODY2FIELD

    def 能量总量B(self, spirits: list) -> float:
        """B 域（能量）总量：炁场 + Σ(灵阳+灵形阴) + Σ(兽阳+兽形阴)。
        形阴是生灵之形的阴量：生时自炁抽取、死时尽数归还，故生者在账。
        C 域（生物质与器物）暂不入账。"""
        return (self.qi.总量()
                + sum(s.yang + (FORM_YIN if s.alive else 0.0) for s in spirits)
                + sum(a.阳 + BEAST_FORM_YIN.get(a.种类, 10.0) for a in self.animals))

    def 物归(self, y: int, x: int, 量: float):
        """万物与炁场之间的归还与支取（C↔B）：逸散、腐坏、塌毁、归土之量，就地归还；
        量为负则是炁场补入万物（凝聚、营建之不足，阴向之收敛），账亦照记。"""
        if 量 >= 0.0:
            self.qi.归还(y, x, 阳=量)
            self.账.物归 += 量
        else:
            实阳, _ = self.qi.抽取(y, x, 阳=-量)
            self.账.物归 -= 实阳
            self.账.越界C += (-量) - 实阳      # 全场炁不足之补差（殆不曾见）

    def 源C(self, 量: float):
        """生物质与太古遗泽入万物之链（采集、伐木、渔获、屠宰、收蛋挤奶）。"""
        self.账.源C += 量

    def 万物总量C(self, spirits: list) -> float:
        """C 域（器物）总量：Σ(物品阳+形阴) + Σ(屋火栏阳+形阴)。
        生物质（草木鱼虫石藤树尸）与太古遗泽是泵的领地，不入此账；
        井为地形之变（如径），亦非器物，不在此账。"""
        物能 = 0.0
        for s in spirits:
            物能 += sum(it.阳 + 物形阴(it.类型) for it in s.bag)
        for b in self.buildings:
            物能 += b.阳 + YIN_HUT + sum(it.阳 + 物形阴(it.类型) for it in b.仓储)
        物能 += sum(f.阳 + YIN_FIRE for f in self.fires)
        物能 += sum(f.阳 + YIN_FENCE for f in self.fences)
        for r in self.relics:
            物能 += sum(it.阳 + 物形阴(it.类型) for it in r["物"])
        return 物能

    def 水总量A(self, spirits: list) -> float:
        """A 域（水文）总量：场水 + 云 + 九泉 + Σ活灵体水 + Σ兽体水 + Σ罐中盛水。
        身体里的水、罐里的水，都只是"转移了地方"的水——从未离开宇宙。"""
        体水 = sum(s.水分 for s in spirits if s.alive) \
            + sum(a.水分 for a in self.animals)
        罐水 = 0.0
        for s in spirits:
            罐水 += sum(it.盛水 for it in s.bag)
        for b in self.buildings:
            罐水 += sum(it.盛水 for it in b.仓储)
        for r in self.relics:
            罐水 += sum(it.盛水 for it in r["物"])
        return (float(self.water.sum() + self.cloud.sum() + self._深潭)
                + (体水 + 罐水) * BODY2FIELD)

    def add_building(self, y: int, x: int, 主人: str) -> Building:
        b = Building(y, x, 主人)
        self.buildings.append(b)
        return b

    def in_bounds(self, y: int, x: int) -> bool:
        return 0 <= y < self.size and 0 <= x < self.size

    def terrain_name(self, y: int, x: int) -> str:
        if self.water[y, x] > 1.0:
            return "水泽"
        h = self.height[y, x]
        if h >= 6.5:
            return "高地"
        if h <= 2.5:
            return "洼地"
        return "坡地"

    # ── 五行相律（土与水）：零新场，相态皆由既有场按律推导 ──
    # 土：被水侵蚀则湿、湿甚为泥；水分大于泥则溃为沙；水少则干；水特别少则硬碎亦成沙
    # 水：多则为流为海；少则为滴、为气（云者，水之蒸气也）

    def 土相(self, y: int, x: int) -> str:
        """土之相态：沙（极干硬碎或水蚀过甚）→ 干 → 土 → 泥。
        五行相律（木克土/木固土）：近树之土，根柢盘结——纵水蚀极干，亦不易溃为沙。"""
        m = float(self.moisture[y, x])
        水蚀 = self.water[y, x] >= 1.5
        极干 = m < 0.08
        if 水蚀 or 极干:
            # 木固土：两步之内有树盘根，则沙化难成，犹可为干
            for t in self.trees:
                if abs(t.y - y) <= 2 and abs(t.x - x) <= 2:
                    return "干"
            return "沙"
        if m < 0.25:
            return "干"
        if m < 0.65:
            return "土"
        return "泥"

    def 水相(self, y: int, x: int) -> str:
        """水之相态：气（云者水之蒸气）→ 滴 → 流 → 海。"""
        w = float(self.water[y, x])
        if w >= 1.8:
            return "海"      # 水多，体积变大，则为水流，再大是大海
        if w >= 0.6:
            return "流"
        if w >= 0.15:
            return "滴"
        if self.cloud[y, x] >= 0.6:
            return "气"      # 水少则或为水滴，或为水蒸气，或为空气中的水份
        return "无"

    def 火相(self, y: int, x: int) -> str:
        """火之相态：无（无火）→ 星（将熄）→ 火 → 焰（旺）。
        相由暖煦所及之内最强的一堆火定（火者，木之阳之缓释也）。"""
        best = 0.0
        for f in self.fires:
            if abs(f.y - y) <= FIRE_WARM_RADIUS and abs(f.x - x) <= FIRE_WARM_RADIUS:
                best = max(best, f.阳)
        if best <= 0.0:
            return "无"
        if best < FIRE_EMBER:
            return "星"      # 星火：将熄未熄，暖有余而炙不足
        if best <= FIRE_BLAZE:
            return "火"
        return "焰"          # 焰：旺火，可烧陶熔金

    def grass_coverage(self) -> float:
        """草覆盖率（有草之格占比），供出生与天道判定。"""
        return float((self.grass > 0.3).mean())

    def add_mark(self, 类型: str, y: int, x: int, 保质期: int, 标签: str | None = None):
        self.marks.append(Mark(类型, y, x, self.tick, 保质期, 标签))

    def rich_spots(self) -> list[tuple[int, int]]:
        """丰饶水泽边：湿润、有草、未没顶——阴凝聚得阳之处。"""
        mask = (self.moisture > 0.40) & (self.grass > 0.45) & (self.water < 1.2)
        ys, xs = np.nonzero(mask)
        return list(zip(ys.tolist(), xs.tolist()))

    def lowest_neighbor(self, y: int, x: int) -> tuple[int, int]:
        """八邻中地势（含水深）最低的一格，水之道也。"""
        best, bv = (y, x), self.height[y, x] + self.water[y, x]
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                ny, nx = y + dy, x + dx
                if self.in_bounds(ny, nx):
                    v = self.height[ny, nx] + self.water[ny, nx]
                    if v < bv:
                        best, bv = (ny, nx), v
        return best

    def numbers_sane(self) -> bool:
        """数值健康检查：全场不得出现 NaN/Inf。"""
        return (np.isfinite(self.water).all() and np.isfinite(self.grass).all()
                and np.isfinite(self.moisture).all() and np.isfinite(self.height).all()
                and np.isfinite(self.cloud).all() and np.isfinite(self.temp).all()
                and np.isfinite(self.qi.yin).all() and np.isfinite(self.qi.yang).all())

    def heal_numbers(self):
        """数值异常时的最小修复（抚平，不改趋势）。"""
        np.nan_to_num(self.water, copy=False, nan=0.0, posinf=3.0, neginf=0.0)
        np.nan_to_num(self.grass, copy=False, nan=0.0, posinf=1.0, neginf=0.0)
        np.nan_to_num(self.moisture, copy=False, nan=0.0, posinf=1.0, neginf=0.0)
        np.nan_to_num(self.cloud, copy=False, nan=0.0, posinf=5.0, neginf=0.0)
        np.nan_to_num(self.temp, copy=False, nan=10.0, posinf=50.0, neginf=-30.0)
        np.nan_to_num(self.qi.yin, copy=False, nan=40.0, posinf=1e6, neginf=0.0)
        np.nan_to_num(self.qi.yang, copy=False, nan=40.0, posinf=1e6, neginf=0.0)
