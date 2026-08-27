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
SPRING_TOTAL = 0.5      # 九泉每念涌泉的总量上限（分摊于最低洼一成之地）
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
# 种类 → (初生阳, 阳上限, 每念逸散, 寿命念数, 食谱)
BEASTS = {
    "鸡": dict(阳=40.0, 逸散=0.045, 寿命=8 * TICKS_PER_DAY, 食="虫", 蛋期=48),
    "羊": dict(阳=80.0, 逸散=0.05, 寿命=16 * TICKS_PER_DAY, 食="草", 奶期=64),
    "牛": dict(阳=120.0, 逸散=0.06, 寿命=24 * TICKS_PER_DAY, 食="草", 奶期=64),
}
BREED_CHANCE = 0.012    # 温饱成对的野兽每念繁殖概率
FLEE_RADIUS = 2         # 野兽见生人而逃的半径
CARRION_YANG = 25.0     # 尸骸初始阳（腐坏尽则归土）
CARRION_DECAY = 0.8     # 尸骸每念腐坏

# ── 火堆 ──
FIRE_YANG0 = 60.0       # 火堆初生之阳
FIRE_DECAY = 0.06       # 火每念燃损（须添柴）
FIRE_RAIN_DMG = 0.4     # 露天火遇雨急熄；屋内灶火无恙
FIRE_WARM_RADIUS = 2    # 火之暖煦所及
FIRE_FEED = 25.0        # 添一份木柴所续之阳

# ── 井与径（v6.4）：井是凿入九泉的水眼，径是众脚踏出来的路 ──
WELL_YANG0 = 70.0       # 井落成时的阳存量（石土之质，缓于茅屋）
WELL_DECAY = 0.012      # 井壁每念阳逸散
WELL_RAIN_SILT = 0.05   # 雨携泥淤井
WELL_DRAW = 0.35        # 每汲一次，九泉微量扣减（与世界水文闭环挂钩）
WELL_SILT_AT = 25.0     # 井阳低于此值则淤塞，汲不得水，须淘浚
WELL_DRY_DEEP = 6.0     # 九泉存量低于此值，井水暂枯（打不出水）
WELL_DIG_TICKS = 16     # 凿井连续施工念数
WELL_MARK_TTL = 3 * TICKS_PER_DAY  # 井骸印记保质期

PATH_AT = 26.0          # 同一格被踩踏次数过此成"径"
PATH_DECAY = 0.012      # 径每念荒芜（久无人走则消失）
PATH_COST = 0.5         # 径上移动耗阳折半

# ── 物品：有阳存量、会腐坏，腐速因材质而异（鱼鲜最快，骨石最慢）──
ITEM_DECAY = {"生鱼": 0.09, "生肉": 0.06, "奶": 0.08, "蛋": 0.04,
              "熟肉": 0.02, "熟鱼": 0.02, "谷种": 0.005,
              "茅草": 0.010, "藤": 0.010, "木": 0.003, "石": 0.001, "骨": 0.0008,
              "石斧": 0.001, "石刀": 0.001, "鱼竿": 0.001, "耒耜": 0.001,
              "背篓": 0.001, "石矛": 0.001, "棍棒": 0.001,
              "土": 0.002, "陶罐": 0.001, "寒衣": 0.004,
              "骨饰": 0.0008, "美石": 0.001, "美贝": 0.0005}
ITEM_YANG = {"生鱼": 30.0, "生肉": 40.0, "奶": 25.0, "蛋": 35.0,
             "熟肉": 40.0, "熟鱼": 35.0, "谷种": 50.0,
             "茅草": 40.0, "藤": 40.0, "木": 60.0, "石": 80.0, "骨": 70.0,
             "土": 40.0, "陶罐": 60.0, "寒衣": 50.0,
             "骨饰": 70.0, "美石": 80.0, "美贝": 80.0}
ITEM_YANG_TOOL = 50.0   # 工具/武器初生之阳；使用中磨损，阳尽断裂
TOOL_WEAR = 1.5         # 工具每用一次磨损之阳

# 物候事件的气温阈值
FROST_AT = 0.0          # 霜冻线
HEAT_AT = 30.0          # 酷暑线


@dataclass
class Item:
    """物品：一份阴凝聚的阳。草藤易腐，木石耐久，骨最不坏。
    陶罐另带一笔"盛水"——罐可储水，水尽则空。"""
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
    """树木：缓慢生长的世界对象。可伐取木；阳尽而枯。"""
    y: int
    x: int
    阳: float = 10.0


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
    """走兽：轻量个体。吃草/饮水/受惊逃/繁殖/衰老死亡——与灵同一个阴阳模型。"""
    种类: str
    y: int
    x: int
    阳: float
    年龄: int = 0
    驯主: str | None = None
    栏位: tuple | None = None     # 圈养锚点
    产物念: int = 0               # 距下次下蛋/可挤奶的剩余念数

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
    """井：凿入九泉的水眼。井水取自九泉（每汲微量扣减）；
    会淤塞（雨携泥入、用久则淤）、会枯（九泉涸则暂枯）、阳尽则废成井骸。"""
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

    def __init__(self, seed: int, size: int = WORLD_SIZE, init_map=None):
        """创世两条路：不给分布图，则从炁场自生（道生一）；给分布图，则以图为炁。"""
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
        for _ in range(14):
            y, x = int(self._rng.integers(0, size)), int(self._rng.integers(0, size))
            if self.moisture is not None:
                self.trees.append(Tree(y, x, float(self._rng.uniform(20, 90))))
        for 种类, 数 in (("鸡", 6), ("羊", 4), ("牛", 3)):
            for _ in range(数):
                y, x = int(self._rng.integers(0, size)), int(self._rng.integers(0, size))
                p = BEASTS[种类]
                self.animals.append(Animal(种类, y, x, p["阳"], 产物念=int(self._rng.integers(0, 64))))

        # 预流：让世界先静转两日，风云水草各归其位
        for _ in range(TICKS_PER_DAY * 2):
            self._物理步(预热=True)
        self.tick = 0
        self.marks = []
        self.rain_episodes = 0
        self._events = []
        self._pheno_done = set()

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
        self.cloud = (self.cloud * 0.98 + blur * 0.02) * CLOUD_DECAY

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

        # 水往低处流：每念向更低的邻居让出一部分（八邻，快照式结算）
        level = self.height + self.water
        delta = np.zeros_like(self.water)
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
                delta[sy, sx] -= f
                delta[ty, tx] += f
        self.water = np.maximum(self.water + delta, 0.0)

        # 渗漏与九泉：水渗入土，归于九泉（阴）；九泉满则低洼处涌泉，涸则止。
        # 水 → 云 → 雨 → 水 → 土 → 九泉 → 泉 —— 闭环守恒，世界因此不涝不涸
        渗 = np.minimum(self.water, SEEP * np.clip(1.2 - self.moisture, 0.2, 1.2))
        self.water -= 渗
        self._深潭 += float(渗.sum())
        if self._深潭 > 0.0:
            # 泉生于谷畔，不注深潭：涌向低而尚干的土地，不成则在潭中蛰伏
            低洼 = (self.height <= np.percentile(self.height, 15)) & (self.water < 1.0)
            泉数 = int(低洼.sum())
            if 泉数:
                涌 = min(self._深潭, SPRING_TOTAL)
                self.water[低洼] += 涌 / 泉数
                self._深潭 -= 涌

        # 湿度：近期水量的平滑记忆（世界唯一的"记性"，亦只是场的惯性）
        inst = np.clip(self.water / 1.5, 0.0, 1.0)
        rate = np.where(inst > self.moisture, MOIST_UP, MOIST_DOWN)
        self.moisture += (inst - self.moisture) * rate
        np.clip(self.moisture, 0.0, 1.0, out=self.moisture)

        # 草：湿度适中则生，暖季速寒季缓，水淹则溺，干旱则枯
        温生 = float(np.clip(温均 / 18.0, 0.2, 1.3))
        suit = np.clip(1.0 - np.abs(self.moisture - GRASS_SUIT_CENTER) / GRASS_SUIT_WIDTH, 0.0, 1.0)
        self.grass += GRASS_GROW * 温生 * suit * (1.0 - self.grass)
        self.grass[self.water > GRASS_FLOOD] -= 0.05
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

        # 树：缓慢生长，缓慢繁衍
        for tree in list(self.trees):
            tree.阳 = min(100.0, tree.阳 + TREE_GROW)
            if 温均 < FROST_AT - 5.0:
                tree.阳 -= 0.05     # 严寒伤木
                if tree.阳 <= 0:
                    self.trees.remove(tree)
        if len(self.trees) < TREE_MAX and self._rng.random() < TREE_SPREAD * n * n:
            湿区 = (self.moisture > 0.3) & (self.water < 1.0)
            ys, xs = np.nonzero(湿区)
            if len(ys):
                i = int(self._rng.integers(0, len(ys)))
                self.trees.append(Tree(int(ys[i]), int(xs[i])))

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

        # 建筑：阳之逸散 + 风雨积水之损；阳尽则塌，化为屋骸
        for b in list(self.buildings):
            损 = HUT_DECAY
            if self.rain_mask[b.y, b.x]:
                损 += HUT_RAIN_DMG * (1.5 if b.阳 < HUT_LEAK_AT else 1.0)
            损 += self.wind_speed * HUT_WIND_DMG * (1.0 + self.height[b.y, b.x] / 9.0 * 1.5)
            if self.water[b.y, b.x] > 0.8:
                损 += (self.water[b.y, b.x] - 0.8) * HUT_FLOOD_DMG
            if self.temp[b.y, b.x] < FROST_AT:
                损 += 0.01     # 冻裂
            b.阳 -= 损
            # 屋内仓储：腐坏减半（仓储的意义）
            b.仓储 = [it for it in b.仓储
                      if not it.腐一步(float(self.temp[b.y, b.x]), 屋内=True)]
            if b.阳 <= 0:
                self.buildings.remove(b)
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

        # 火堆：燃柴续阳，露天遇雨则熄
        for f in list(self.fires):
            f.阳 -= FIRE_DECAY
            if not f.屋内 and self.rain_mask[f.y, f.x]:
                f.阳 -= FIRE_RAIN_DMG
            if f.阳 <= 0:
                self.fires.remove(f)
                self._events.append({
                    "kind": "火熄", "pos": (f.y, f.x), "actor": f.主人,
                    "text": f"{f.主人} 的火堆熄了（因：薪尽而火传难继）"})

        # 尸骸腐坏，尽则归土；围栏缓腐
        for c in list(self.carrions):
            c.阳 -= CARRION_DECAY * float(np.clip(0.5 + self.temp[c.y, c.x] / 30.0, 0.3, 1.8))
            if c.阳 <= 0:
                self.carrions.remove(c)
        for fe in list(self.fences):
            fe.阳 -= 0.01
            if fe.阳 <= 0:
                self.fences.remove(fe)

        # 井：井壁阳逸散，雨携泥淤；阳尽则废，留井骸印记
        for wl in list(self.wells):
            wl.阳 -= WELL_DECAY
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
        # 无主遗物亦如此：日久归土
        self.relics = [r for r in self.relics
                       if t - r["念"] < 3 * TICKS_PER_DAY]

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
        rng = self._rng
        for a in list(self.animals):
            p = BEASTS[a.种类]
            a.阳 -= p["逸散"]
            a.年龄 += 1
            a.产物念 = max(0, a.产物念 - 1)

            # 衰老病死：阳尽则亡，尸骸归土
            if a.阳 <= 0 or a.年龄 > p["寿命"] * rng.uniform(0.9, 1.1):
                self.animals.remove(a)
                肉, 骨 = {"鸡": (2, 1), "羊": (4, 2), "牛": (6, 3)}[a.种类]
                self.carrions.append(Carrion(a.y, a.x, 肉, 骨, 名=a.种类))
                if a.驯主:
                    self._events.append({
                        "kind": "畜死", "pos": (a.y, a.x), "actor": a.驯主,
                        "text": f"{a.驯主} 的{a.种类}病死了（因：饲养不周，阳尽则亡）"})
                continue

            # 圈养者：守在栏畔，不肯走远
            if a.驯化 and a.栏位 is not None:
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

            # 野者避人：生的灵靠近则逃（火堆亦惊兽）
            威胁 = None
            for s in spirits:
                if s.alive and abs(s.y - a.y) <= FLEE_RADIUS and abs(s.x - a.x) <= FLEE_RADIUS:
                    威胁 = s
                    break
            if 威胁 is None:
                for f in self.fires:
                    if abs(f.y - a.y) <= FLEE_RADIUS and abs(f.x - a.x) <= FLEE_RADIUS:
                        威胁 = f
                        break
            if 威胁 is not None:
                # 兽受惊而逃——但贪食的兽有时尚且驻足，猎人因此追得上
                if rng.random() < 0.6:
                    a.y = int(np.clip(a.y + np.sign(a.y - 威胁.y), 0, self.size - 1))
                    a.x = int(np.clip(a.x + np.sign(a.x - 威胁.x), 0, self.size - 1))
                self._兽食(a, p)
                continue

            # 寻食：鸡逐虫，羊牛逐草
            食场 = self.insects if p["食"] == "虫" else self.grass
            阈 = 0.3 if p["食"] == "虫" else 0.25
            best, bv = None, 食场[a.y, a.x]
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    ny, nx = a.y + dy, a.x + dx
                    if self.in_bounds(ny, nx) and 食场[ny, nx] > bv:
                        best, bv = (ny, nx), 食场[ny, nx]
            if best is not None:
                a.y, a.x = best
            elif rng.random() < 0.4:
                a.y = int(np.clip(a.y + rng.integers(-1, 2), 0, self.size - 1))
                a.x = int(np.clip(a.x + rng.integers(-1, 2), 0, self.size - 1))
            self._兽食(a, p)

        # 繁殖：温饱且成对
        if len(self.animals) < ANIMAL_MAX:
            for i in range(len(self.animals)):
                for j in range(i + 1, len(self.animals)):
                    x, y = self.animals[i], self.animals[j]
                    if x.种类 != y.种类:
                        continue
                    if abs(x.y - y.y) + abs(x.x - y.x) > 2:
                        continue
                    p = BEASTS[x.种类]
                    if x.阳 < p["阳"] * 0.6 or y.阳 < p["阳"] * 0.6:
                        continue
                    if rng.random() < BREED_CHANCE:
                        self.animals.append(Animal(x.种类, x.y, x.x, p["阳"] * 0.5))
                        break

    def _兽食(self, a: Animal, p: dict):
        """兽食其食：鸡啄虫，羊牛啮草。鸡所过处，虫灾自减。"""
        if p["食"] == "虫":
            if self.insects[a.y, a.x] > 0.3:
                self.insects[a.y, a.x] -= 0.3
                a.阳 = min(p["阳"], a.阳 + 6.0)
        else:
            if self.grass[a.y, a.x] > 0.25:
                self.grass[a.y, a.x] -= 0.2
                a.阳 = min(p["阳"], a.阳 + 5.0)

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

    def 汲井(self, well: Well) -> str:
        """从井里打一水。井水取自九泉：每汲一次，九泉微量扣减。
        返回 "活"（得饮）/ "淤"（淤塞须淘）/ "枯"（九泉暂涸）。"""
        if well.状态 == "淤":
            return "淤"
        if self._深潭 < WELL_DRY_DEEP:
            return "枯"
        self._深潭 -= WELL_DRAW
        well.阳 -= 0.3      # 汲用亦损井
        return "活"

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
                and np.isfinite(self.cloud).all() and np.isfinite(self.temp).all())

    def heal_numbers(self):
        """数值异常时的最小修复（抚平，不改趋势）。"""
        np.nan_to_num(self.water, copy=False, nan=0.0, posinf=3.0, neginf=0.0)
        np.nan_to_num(self.grass, copy=False, nan=0.0, posinf=1.0, neginf=0.0)
        np.nan_to_num(self.moisture, copy=False, nan=0.0, posinf=1.0, neginf=0.0)
        np.nan_to_num(self.cloud, copy=False, nan=0.0, posinf=5.0, neginf=0.0)
        np.nan_to_num(self.temp, copy=False, nan=10.0, posinf=50.0, neginf=-30.0)
