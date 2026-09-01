# -*- coding: utf-8 -*-
"""
《易道引擎》v6.0 "鱼缸" — 灵体层 (spirit.py)

灵体 = 记忆 + 心情 + 心态 + 欲望 + 抉择。

第一性原理（见 docs/engine-v6-lingti.md）：
  万物由阴凝聚而成，内含一份固定的阳；阳每念逸散，阳尽则亡。
  记忆只记要义、会压缩、会遗忘，但关键的事永远不忘。
  关系 = 对他人的记忆；遗忘 = 陌路。
  因果为常，临界涌现：情绪/压力如势能积累，超过阈值即翻转——阳极则反。

v6.0.1 丰富化：
  感知有限（昼五夜二，无全图知识）；昼夜节律（夜里归栖安眠）；
  饥渴双线；社交与恩义（交谈/分享/救助/目睹/庇护）；
  心态被经历塑造（谨慎/好斗/亲和缓慢漂移）；死亡与悼念。
v6.0.2 营造与耕织：
  知识（会建造/会种植）由领悟、模仿、传授而来，一旦获得不遗忘；
  茅草屋与农田是世界层物质对象，会漏、会塌、会枯；
  夜雨淋身是建造动机的根源；对茅屋有三种社会响应：模仿、求庇、夺屋。
v6.3 人性：
  传闻（二手记忆，传播失真随链长渐长：张冠李戴、抢夺传成杀人）；
  误会（见人在遗骨遗物旁徘徊，疑其为凶——错误记忆与真目睹无异）；
  谎言（赖账者当面抵赖、好斗者装无辜；记忆分明则戳穿，淡忘则得逞）；
  声望（传闻+目睹的分布式社会记忆，久闻其名，初见不从零起）；
  同悼（一人举哀，闻者同悲——葬礼雏形，群体纽带由此而生）。
v6.4 值得被书写：
  凿井（连续口渴而悟，井水取自九泉；井会淤、会枯、可淘浚，众灵向井聚居）；
  道路（众脚往复踏出径，径上行走省力，久无人走则荒芜）；
  陶器（腐坏之痛而悟，采土就火而烧；藏粮缓腐、可储水，可交易传代）；
  衣物与饰品（受冻的第二出路：缝纫；骨饰无实用、只有社会价值）；
  贝币雏形（美贝天然稀缺：能易物、能还债、能馈赠）；
  祈雨聚与迁徙（仪式是群体的镇定剂，迷信从巧合中诞生；
  故土草枯水涸则弃家携眷，屋田栏留作无主遗迹——史记级事件）。
v6.5 DNA 与真学习（作者指示：真学习不是顿悟；环境塑造 DNA 链；生长要有过程）：
  基因组（人格位点：谨慎/悍戾/亲和/悟性/体质；技艺禀赋位点：渔猎/建造/种植/百工/火食/畜牧）
  —— 初代由环境印记主导，第 N 代 w_血脉=N/(N+1) 渐由祖辈血脉主导；
  真学习：技能获得改为经验积累过槛（_积学），掷骰顿悟全部废除；
  生长曲线 body_curve：幼弱（0.15）→ 抽条（10 日长成）→ 壮盛 → 衰老（地板 0.4）。
"""

from dataclasses import dataclass

try:
    from ..world import (World, Farm, Carrion, Fence, Fireplace, Item, Well,
                        TICKS_PER_DAY, is_night, FROST_AT, FIRE_FEED, BEASTS,
                        WELL_DIG_TICKS, PATH_AT, PATH_COST, BODY2FIELD, DRINK_KEEP,
                        ITEM_YANG, ITEM_YANG_TOOL, FIRE_YANG0, HUT_YANG0, 物形阴,
                        YIN_HUT, YIN_FIRE, YIN_FENCE)
    from ..qi import BEAST_FORM_YIN
except ImportError:  # 允许 v6/fishbowl.py 以脚本方式直跑
    from world import (World, Farm, Carrion, Fence, Fireplace, Item, Well,
                       TICKS_PER_DAY, is_night, FROST_AT, FIRE_FEED, BEASTS,
                       WELL_DIG_TICKS, PATH_AT, PATH_COST, BODY2FIELD, DRINK_KEEP,
                       ITEM_YANG, ITEM_YANG_TOOL, FIRE_YANG0, HUT_YANG0, 物形阴,
                       YIN_HUT, YIN_FIRE, YIN_FENCE)
    from qi import BEAST_FORM_YIN

# ───────────────────────────────────────────
# 0. 灵体常数（调参集中于此）
# ───────────────────────────────────────────

YANG_DECAY = 0.10       # （已废，v8-P0D）旧定额逸散——定率化后由 YANG_RATE 代之
YANG_RATE = 0.00125     # 阳·每念自然逸散率（率 × 存量；阳 80 时与旧制 0.10 持平）

# ── 回光返照（v8-P0D·D1，作者 2026-09-01 拍板）──
GLEAM_AT = 0.8          # 回光阈：阳首次跌破此值且非战斗所致 → 入回光态
GLEAM_TICKS = 12        # 回光窗（念）：窗内一切决策阈值按假象值评估
GLEAM_FAKE = 45.0       # 假象值：窗中如常人——能行走、交谈、口述、馈赠、归家
GLEAM_SAVE = 5.0        # 残阳得续之阈：渡阳拉回此值之上，回光解除
GLEAM_SAGE_KNOW = 6     # 悟道者认定：贯通六门技艺
GLEAM_SAGE_WIT = 0.75   # 且悟性过人——结构性稀有，百年难遇一人
MOVE_COST = 0.22        # 移动耗阳
TRAIN_COST = 0.30       # 锻炼耗阳
EAT_GAIN = 22.0         # 吃草补阳
EAT_GRASS_MIN = 0.4     # 草量达到此值方可入口

THIRST_DECAY = 0.12     # 水分每念自然下降
THIRST_URGENT = 30.0    # 低于此值 → 找水是第一要务
THIRST_LOW = 25.0       # 低于此值，阳的逸散加速
DRINK_MIN = 0.4         # 积水达到此值可饮

SENSE_DAY = 5           # 白昼感知半径
SENSE_NIGHT = 2         # 夜晚感知半径

HUNGER_YANG = 40.0      # 阳低于此值 → 求生觅食为第一要务
STRENGTH_CAP = 26.0     # 力量上限
TRAIN_GAIN = 0.045      # 锻炼每念力量微增
TRAIN_SAFE_YANG = 45.0  # 阳高于此值才敢锻炼

ROB_AGGR = 0.55         # 好斗度高于此值才会动抢夺之念
ROB_HUNGER = 62.0       # 阳低于此值的"饥饿"才驱动抢夺
ROB_GREEDY_YANG = 75.0  # 悍戾者的饥饿线放宽：霸凌半靠性，半靠饿
ROB_CHANCE = 0.42       # 相邻弱者当前时，好斗者每念下手概率系数
ROB_WEAKER = 0.98       # 力量低于我×此值才算"弱者"
ROB_COOLDOWN = 8        # 抢夺后需消化，同一悍匪两抢之间的最小念数

PRESSURE_MAX = 1.0      # 压力临界值：超过即涌现
PRESSURE_DECAY = 0.008  # 压力每念缓慢衰减

MEMORY_FORGET = 0.05    # 权重低于此值即遗忘
MEMORY_ETERNAL = 0.85   # 情绪强度达到此值的记忆永存
MOURN_DECAY = 0.97      # 哀伤衰减极慢：悼念记忆每日权重×此值
REGION_SIZE = 6         # "区域"记忆的空间粒度

# 社交与恩义
TALK_CHANCE = 0.10      # 相邻故人无急务时，每念搭话的基础概率
TALK_PAIR_CD = 32       # 同一对人两次交谈的最小念数
SHARE_REL = 0.5         # 关系达到此值才会分食救人
SHARE_NEED = 48.0       # 阳低于此值即算"面有饥色"，故交见之于心不忍
SHARE_SELF = 52.0       # 自身阳高于此值才有余力分食
FRIEND_REL = 0.7        # 关系达到此值方为好友（庇护/悼念的门槛）
SHARE_YANG = 15.0       # 一次分食让渡的阳
SHARE_PAIR_CD = 24      # 同一对人两次分食的最小念数
WITNESS_FRESH = 3       # 目睹记忆多少念内算"就在眼前"，可触发庇护

# 心态漂移：性格被经历塑造
DRIFT_CAUTION_ROBBED = 0.03   # 屡遭抢夺 → 谨慎缓升
DRIFT_AGGR_REVENGE = 0.06     # 报复成功 → 好斗缓升
DRIFT_AFFINITY_HELPED = 0.05  # 多次受助 → 亲和缓升
DRIFT_AFFINITY_TALK = 0.01    # 闲谈亦可增进亲和
DRIFT_REPORT = 0.10           # 单向累计漂移超过此值 → 心性显化，值得入流

# 知识、建造与种植（知识来源：领悟 / 观察模仿 / 传授）
MATERIAL_NEED = 3       # 建一座茅屋所需茅草份数
GATHER_GRASS_MIN = 0.6  # 草量达到此值方可割取茅草
BUILD_TICKS = 12        # 连续施工念数
BUILD_COST = 0.30       # 施工每念耗阳
HUT_REPAIR = 30.0       # 一份茅草修缮补阳
HUT_OWN_REPAIR_AT = 45.0  # 屋阳低于此值主人起修缮之念
PLANT_COST = 6.0        # 播种所耗之阳（一份种粮）
PLANT_MOIST = (0.3, 0.75)  # 宜耕湿度区间
HARVEST_GAIN = 30.0     # 收获补阳（产量高于野草）
FARM_MAX = 2            # 一灵同时照看的田数上限
# 真学习（v6.5）：技能不再"概率×悟性"掷骰顿悟，而是经验积累过槛——
# 试错、观察、受挫都在攒经验，顿悟只是临门一脚。
# 历史参数（掷骰时代，已废，存档备查）：INVENT_BUILD 0.15 / INVENT_FARM 0.012 /
#   LEARN_WATCH 0.02 / INVENT_TOOL 0.08 / INVENT_FIRE 0.18 / INVENT_COOK 0.30 /
#   INVENT_FISH 0.08 / INVENT_HERD 0.06 / INVENT_WELL 0.10 / INVENT_POTTERY 0.10 /
#   INVENT_SEW 0.12 / LEARN_TOUCH 0.40
LEARN_GATE = {"建造": 40.0, "种植": 45.0, "制器": 40.0, "取火": 45.0, "烹饪": 25.0,
              "渔猎": 35.0, "畜牧": 45.0, "凿井": 50.0, "制陶": 45.0, "缝纫": 40.0}
TEACH_CHANCE = 0.35     # 交谈时把知识教给故人的概率
SEIZE_AGGR = 0.65       # 好斗度高于此值的无屋者才会起夺屋之念

# ── 食物、材料与器物 ──
# 食物营养（补阳）：熟食远高于生食；生食有致病风险
FOOD_YANG = {"熟肉": 20.0, "熟鱼": 14.0, "生肉": 10.0, "生鱼": 8.0,
             "蛋": 8.0, "奶": 8.0, "谷种": 6.0, "果": 7.0}
RAW_KINDS = {"生肉", "生鱼"}
RAW_SICK = 0.15         # 生食致病概率（腹泻 → 阳损 + 坏记忆）
EAT_GRASS_GAIN = 14.0   # 野菜野草：能活，但算不上好日子

# 制器配方：类型 → 材料表。制器成功率随熟练提升
RECIPES = {"石斧": {"石": 1, "木": 1}, "石刀": {"石": 1}, "鱼竿": {"木": 1, "藤": 1},
           "耒耜": {"木": 2}, "背篓": {"藤": 2}, "石矛": {"石": 1, "木": 1, "藤": 1},
           "棍棒": {"木": 1}}
TOOL_PRIORITY = ["石斧", "石刀", "鱼竿", "石矛", "耒耜", "背篓", "棍棒"]
WEAPON_BONUS = {"金刃": 0.70, "石矛": 0.50, "棍棒": 0.30, "石斧": 0.15, "石刀": 0.10}
CRAFT_TICKS = 4         # 制一件器所需念数
CHOP_YIELD = 2          # 伐木一树所得（有石斧则 3）
SKILL_GAIN = 0.04       # 每用一次，熟练微增（再受该域禀赋 20% 加成，见 _涨熟练）

HUNT_BASE = {"鸡": 0.70, "羊": 0.45, "牛": 0.25}   # 徒手捕猎基础得手率（石矛 +0.15）
TAME_CHANCE = {"鸡": 0.50, "羊": 0.30, "牛": 0.18} # 驯化基础成功率（×畜牧熟练修正）

# 人情：交易、借贷、馈赠
TRADE_CHANCE = 0.25     # 相邻故人无急务且互有盈余时的以物易物概率
LEND_REL = 0.5          # 借贷门槛：关系达到此值方肯出手相助
GIFT_REL = 0.8          # 馈赠门槛：关系深厚且我有盈余
DEBT_DAYS = 3           # 借贷逾此日数有能力还而不还 → 赖账生怨

# 人性（v6.3）：传闻、误会、谎言、声望、同悼——一切社会现象从
# "记忆 + 感知有限 + 信息传播失真" 中涌现，无硬编码剧情。
GOSSIP_CHANCE = 0.35    # 交谈时谈论某个第三方的概率
GOSSIP_MAX_HOP = 3      # （已退位，v8-P1C）旧链长硬门——现为续传概率 + 链长 6 安全阀
GOSSIP_SURVIVE = 0.55   # 每站续传概率：传闻欲再传则掷之，不过则此链止于此口
GOSSIP_DISTORT = 0.10   # 基础失真率（每多一站翻倍：×(1+链长)）
GOSSIP_EMO = 0.55       # 二手之事情绪折扣（耳闻不如亲历）
GOSSIP_EMO_CAP = 0.42   # 寻常传闻的情绪上限（血案传闻不受此限）
GOSSIP_WEIGHT = 0.5     # 传闻入关系的权重折扣：耳闻不如眼见
MISJUDGE = 0.06         # 骨旁生疑基础概率（×(0.5+谨慎)）：见人在遗骨旁，或疑其为凶
CONFRONT_CHANCE = 0.12  # 狭路相逢、心中有疑/有债时，当面质问的每念概率
CLARIFY_CHANCE = 0.55   # 问心无愧者被质问时澄清成功的概率
DENY_INNOCENT = 0.45    # 有亏心事者被质问时装无辜的尝试率
LIE_DENY = 0.35         # 赖账者被当面问债时否认的概率系数（×(1.2-亲和)）
LIE_CLEAR_W = 0.35      # 债主记忆权重高于此值 → 谎言被戳穿；低于此值 → 谎言得逞

# 井、陶、衣、饰、贝（v6.4）：新技能的顿悟系数已随掷骰时代一并作废（见上方存档注）
POTTERY_CLAY = 2        # 烧一陶罐需土两份
SEW_TICKS_VINE = 2      # 缝一寒衣需藤两份、骨针一枚（骨）
SHELL_VALUE = 3         # 一枚美贝的名义价值（贝币雏形：能易物、能还债、能馈赠）
DIG_COST = 0.25         # 凿井施工每念耗阳

# 祈雨与迁徙（v6.4）：群体事件两件。天道永不回应祈雨——但人心会记住巧合。
DROUGHT_DAYS = 4        # 连续不见雨超过此日数，人心生旱魃之惧
PRAY_GRASS = 0.18       # 居所附近草均低于此值，是为草枯之验
PRAY_AFFINITY = 0.5     # 亲和高于此值者才会发起祈雨聚
PRAY_RANGE = 7          # 闻讯而来的半径
PRAY_COOLDOWN = 3       # 同一灵两次发起祈雨聚的最小日数
PRAY_ANSWER = 3         # 祈后三日内恰有雨 → 祈雨得应（纯巧合，迷信由此而生）
FAMINE_GRASS = 0.10     # 居所四周草均低于此值且四邻无水 → 记荒一日
FAMINE_DAYS = 3         # 连续荒三日 → 弃家迁徙
MIGRATE_NEAR = 6        # 迁徙目标至少此距离（挪窝不算迁徙）
MIGRATE_GIVEUP = 6      # 跋涉逾此日数未至 → 就地落脚（走到哪里，哪里就是家）

# 代际：生长、婚育、衰老、寿终（v6.2）
ADULT_DAY = 4.0         # 第几日成年（幼年期：跟随父母、受哺育、家传学习）
OLD_AGE_DAY = 40.0      # 第几日起衰老（阳上限渐缩，筋骨渐衰）
MATE_REL = 0.85         # 结为伴侣的双向关系门槛
MATE_CHANCE = 0.30      # 相邻两悦时结侣的每念概率
BIRTH_PAIR_CD = 5 * TICKS_PER_DAY   # 一对伴侣两次诞育的最小间隔
BIRTH_NIGHT_CHANCE = 0.05           # 夜里同檐温饱时的每念诞育概率
FERTILE_AGE = (5.0, 38.0)           # 生育窗口（日）
POP_CAP = 20            # 世界人口上限（繁衍通道；凝聚通道仍受凝聚上限约束）
CHILD_FOLLOW = 2        # 幼崽与父母保持的距离
HEIR_TELL = 6           # 成年礼上父母口述的往事条数
RELIC_DAYS = 3          # 无主遗物留存日数，而后归还于土
BAG_CAP = 14            # 行囊容量：人就一双手，背不动天下

# 物品名义价值（交易公平感的尺度）
ITEM_VALUE = {"熟肉": 4, "熟鱼": 3, "生肉": 3, "生鱼": 2, "蛋": 2, "奶": 2, "谷种": 1, "果": 1,
              "木": 2, "石": 2, "藤": 1, "骨": 1, "茅草": 1,
              "石斧": 8, "石刀": 6, "鱼竿": 7, "耒耜": 7, "背篓": 6, "石矛": 9, "棍棒": 5,
              "土": 1, "美石": 2, "矿石": 3, "金块": 8, "金刃": 14,
              "陶罐": 7, "寒衣": 8, "骨饰": 6, "美贝": SHELL_VALUE}

# 角色名池（可扩展）
NAMES = ["阿石", "禾", "石根", "葵", "麦", "岩", "泉", "桑",
         "槿", "土伯", "苇", "崖", "苔", "溪", "壤", "岚"]
# 后代名池：新生代之名
GEN_NAMES = ["苗", "芽", "穗", "荞", "荠", "蒲", "菱", "莲",
             "蕨", "杜", "梁", "棘", "柳", "榆", "桐", "梓",
             "稻", "稷", "菽", "荏", "莓", "菁", "芒", "芦"]


def 新名(spirits: list, rng) -> str:
    """为新生儿取名：避开在世者之名，枯竭则加排行。"""
    现名 = {s.name for s in spirits}
    池 = [n for n in GEN_NAMES + NAMES if n not in 现名]
    if 池:
        return rng.choice(池)
    base = rng.choice(GEN_NAMES)
    i = 2
    while f"{base}·{i}" in 现名:
        i += 1
    return f"{base}·{i}"


# ───────────────────────────────────────────
# 〇·五、DNA 链与生长（v6.5）
# ───────────────────────────────────────────

DNA_人格 = ("谨慎", "悍戾", "亲和", "悟性", "体质")
DNA_技艺 = ("渔猎", "建造", "种植", "百工", "火食", "畜牧")
# 技能 → 禀赋域：学该技时按其域的禀赋位点加速
SKILL_DOMAIN = {"建造": "建造", "凿井": "建造",
                "制器": "百工", "制陶": "百工", "缝纫": "百工",
                "取火": "火食", "烹饪": "火食",
                "种植": "种植", "渔猎": "渔猎", "畜牧": "畜牧"}


def 夹01(v: float) -> float:
    return max(0.0, min(1.0, v))


def _截断正态(rng, mu: float, sigma: float, lo: float, hi: float) -> float:
    """截断正态（v8-P2 个体差异正态化）：小因素叠加 → 钟形曲线——
    大多数平庸，天才与夭折皆稀有。稀有者才值得被书写。"""
    return max(lo, min(hi, rng.gauss(mu, sigma)))


def 转阳(world, 出, 入, 量: float, 率: float = 1.0):
    """灵与灵之间的阳转移：出者实扣，入者实受；
    路途损耗与上限溢出皆就地归还炁场——能量不生不灭（宇宙底座第一律）。"""
    扣 = min(出.yang, 量)
    出.yang -= 扣
    旧 = 入.yang
    入.yang = min(100.0, 入.yang + 扣 * 率)
    余 = 扣 - (入.yang - 旧)
    if 余 > 0.0:
        world.qi.归还(入.y, 入.x, 阳=余)


def 环境印记(world: World, y: int, x: int) -> dict:
    """出生地的环境塑造值（各位点 0..1）：环境塑造 DNA——河边生者善渔。
    采样出生点半径 4：水域率→渔猎；平均高度+石树→建造/百工；草率+湿度→种植/畜牧；
    瘠薄之地→谨慎/悍戾微倾。纯函数（世界此刻快照 → 数值），自身不含随机。"""
    r = 4
    n = 0
    水 = 高 = 草 = 湿 = 0.0
    石点 = 0
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            ny, nx = y + dy, x + dx
            if not world.in_bounds(ny, nx):
                continue
            n += 1
            水 += 1.0 if world.water[ny, nx] >= 0.4 else 0.0
            高 += float(world.height[ny, nx])
            草 += float(world.grass[ny, nx])
            湿 += float(world.moisture[ny, nx])
            if world.stone[ny, nx] >= 1.0:
                石点 += 1
    n = max(1, n)
    树 = sum(1 for t in world.trees if abs(t.y - y) <= r and abs(t.x - x) <= r)
    水域率 = 水 / n
    均高 = 高 / n / 9.0                 # 归一：地形高程 0..9
    草率 = 草 / n                        # 草 ∈ [0,1]
    湿度 = 湿 / n                        # 墒 ∈ [0,1]
    材率 = min(1.0, 石点 / n + 树 / 8.0)  # 石与树皆为营造之材
    瘠薄 = 夹01(1.0 - 草率 * 1.5 - 水域率 * 1.0)
    return {
        # 技艺禀赋位点
        "渔猎": 夹01(水域率 * 2.2),
        "建造": 夹01(0.1 + 0.9 * (0.6 * 均高 + 0.4 * 材率)),
        "百工": 夹01(0.1 + 0.9 * (0.3 * 均高 + 0.7 * 材率)),
        "种植": 夹01(0.05 + 1.0 * 草率 * (0.5 + 0.5 * 湿度)),
        "畜牧": 夹01(0.05 + 0.95 * 草率 * (0.7 + 0.3 * 湿度)),
        "火食": 夹01(0.25 + 0.45 * 材率),
        # 人格位点（对初代只是微倾的底；瘠薄之地出警惕悍戾之性）
        "谨慎": 夹01(0.5 + 0.25 * 瘠薄),
        "悍戾": 夹01(0.45 + 0.25 * 瘠薄),
        "亲和": 夹01(0.5 + 0.15 * 草率 - 0.15 * 瘠薄),
        "悟性": 0.5,
        "体质": 夹01(0.5 + 0.15 * 草率),
    }


def _成形基因组(rng, env: dict, 亲: tuple | None, 代: int) -> dict:
    """基因组成形（作者原话：DNA 从第一代的环境影响，到最后由祖辈血脉主导，
    环境影响退居）。初代（凝聚生）：人格随机为底 + 环境微倾，禀赋全由环境给；
    第 N 代新生儿：位点 = w_血脉 × 父母均值 + w_环境 × 环境印记 + 噪声（±0.08），
    w_血脉 = N/(N+1)——第 1 代五五开，第 4 代血脉占八成。"""
    if 亲 is None:
        # v8-P2 正态化：初代人格位点改截断正态（均值 0.5，σ 0.12）——
        # 悍戾保留 betavariate（需求书认作正确示范）
        dna = {
            "谨慎": 夹01(_截断正态(rng, 0.5, 0.12, 0.05, 0.95) * 0.8 + env.get("谨慎", 0.5) * 0.2
                       + _截断正态(rng, 0.0, 0.035, -0.05, 0.05)),
            "悍戾": 夹01((rng.uniform(0.55, 0.95) if rng.random() < 0.3
                        else rng.betavariate(1.3, 4.0)) * 0.8 + env.get("悍戾", 0.45) * 0.2
                       + _截断正态(rng, 0.0, 0.035, -0.05, 0.05)),
            "亲和": 夹01(_截断正态(rng, 0.5, 0.12, 0.05, 0.95) * 0.8 + env.get("亲和", 0.5) * 0.2
                       + _截断正态(rng, 0.0, 0.035, -0.05, 0.05)),
            "悟性": 夹01(_截断正态(rng, 0.5, 0.12, 0.05, 0.95) * 0.8 + env.get("悟性", 0.5) * 0.2
                       + _截断正态(rng, 0.0, 0.035, -0.05, 0.05)),
            "体质": 夹01(_截断正态(rng, 0.5, 0.12, 0.05, 0.95) * 0.8 + env.get("体质", 0.5) * 0.2
                       + _截断正态(rng, 0.0, 0.035, -0.05, 0.05)),
        }
        for k in DNA_技艺:
            dna[k] = 夹01(env.get(k, 0.3) + _截断正态(rng, 0.0, 0.035, -0.08, 0.08))
        return dna
    w_血 = 代 / (代 + 1)
    w_环 = 1.0 / (代 + 1)
    pa, pb = 亲
    return {k: 夹01(w_血 * (pa.get(k, 0.5) + pb.get(k, 0.5)) / 2
                  + w_环 * env.get(k, 0.5)
                  + _截断正态(rng, 0.0, 0.035, -0.08, 0.08))
            for k in DNA_人格 + DNA_技艺}


def body_curve(age_days: float) -> float:
    """形体曲线（幼弱→壮盛→衰老）：0-4 日幼雏（0.15+0.05×日），
    4-10 日抽条（线性涨至 1.0），10-40 日壮盛（1.0），40 日后每日 -0.02，地板 0.4。"""
    if age_days < 4.0:
        return 0.15 + 0.05 * age_days
    if age_days < 10.0:
        return 0.35 + (age_days - 4.0) * (0.65 / 6.0)
    if age_days <= 40.0:
        return 1.0
    return max(0.4, 1.0 - 0.02 * (age_days - 40.0))

# 记忆压缩时，类别 → 动词
_KIND_VERB = {"食物": "觅食", "区域": "踏勘", "抢人": "欺生", "战斗": "争斗",
              "探索": "游历", "交谈": "寒暄", "目睹": "见闻", "同情": "见闻",
              "受助": "受恩", "助人": "行善", "受护": "受恩", "淋雨": "淋雨挨冻",
              "听闻": "传闻", "听闻恨": "旧怨", "亲缘": "天伦", "传闻": "闲闻",
              "冰释": "释怨", "同悼": "同悼", "谎言": "谎言", "疑": "疑惑",
              "焦渴": "焦渴", "腐坏": "伤耗", "同祈": "同祈", "祈应": "祈应",
              "迁徙": "迁徙"}

# 关系加权：正向记忆与负向记忆的类别表（"传闻" 不入表——按其自带褒贬计）
_REL_POS = {"交谈", "受助", "助人", "受护", "同情", "悼念", "受教", "交易",
            "亲缘", "伴侣", "继承", "听闻", "家传", "两清", "同悼", "冰释",
            "同祈", "祈应"}
_REL_NEG = {"被抢", "受辱", "目睹", "被拒", "夺屋", "被亏", "赖账",
            "听闻恨", "父仇", "谎言"}

# 传闻素材：类别 → (褒贬, 谈资说法)。恶行与善行皆可口耳相传。
_GOSSIP_DEED = {"被抢": (-1, "抢掠过他人"), "受辱": (-1, "打垮过他人"),
                "目睹": (-1, "行过凶"), "夺屋": (-1, "夺过人屋檐"),
                "赖账": (-1, "欠债不还"), "被亏": (-1, "交易坑人"),
                "谎言": (-1, "口吐谎言"), "听闻恨": (-1, "行止不端"),
                "受助": (1, "有恩于人"), "受护": (1, "挺身护过人"),
                "还债": (1, "有信有义"), "同悼": (1, "重情重义"),
                "冰释": (1, "胸襟坦荡"), "听闻": (1, "名声在外"),
                "祈应": (1, "祈雨得天垂青"), "同祈": (1, "与人同祈过甘霖")}
_GOSSIP_KILL = "打死了人"   # 失真夸大：抢夺传成杀人

# 克制的短语池（状态驱动，一句以内，禁止刷屏）
_QUOTES_ROBBED = ["「欺人太甚！」", "「我记住了。」", "「还我！」"]
_QUOTES_SAVED = ["「滴水之恩。」", "「……多谢。」"]
_QUOTES_PROTECT = ["「住手！」"]


@dataclass
class Memory:
    """记忆：只记要义。{要义, 情绪强度, 念戳, 权重, 永存}
    传闻另带两笔：链长（话传了几站，失真随之渐长）与褒贬（善闻/恶闻）。"""
    要义: str
    类别: str            # 被抢 / 受辱 / 抢人 / 报仇 / 交谈 / 受助 / 目睹 / 悼念 / 传闻 ...
    对象: str | None     # 涉及的他人之名（关系=对他人的记忆），无则 None
    情绪强度: float
    念戳: int
    权重: float
    永存: bool
    次数: int = 1        # 同类永存记忆重复发生时累加（"他屡抢了我"）
    链长: int = 0        # 传闻专用：此事辗转了几张口（0 = 亲历/一手）
    褒贬: int = 0        # 传闻专用：+1 善闻 / -1 恶闻 / 0 不置褒贬
    序: int = 0          # 此灵心中第几条记忆（口述历史去重的稳定身份，不用 id()——
                       # 内存地址会被回收复用，导致结果随进程启动方式漂移）


__all__ = [
    "ADULT_DAY",
    "BAG_CAP",
    "BEASTS",
    "BEAST_FORM_YIN",
    "BIRTH_NIGHT_CHANCE",
    "BIRTH_PAIR_CD",
    "BODY2FIELD",
    "BUILD_COST",
    "BUILD_TICKS",
    "CHILD_FOLLOW",
    "CHOP_YIELD",
    "CLARIFY_CHANCE",
    "CONFRONT_CHANCE",
    "CRAFT_TICKS",
    "Carrion",
    "DEBT_DAYS",
    "DENY_INNOCENT",
    "DIG_COST",
    "DNA_人格",
    "DNA_技艺",
    "DRIFT_AFFINITY_HELPED",
    "DRIFT_AFFINITY_TALK",
    "DRIFT_AGGR_REVENGE",
    "DRIFT_CAUTION_ROBBED",
    "DRIFT_REPORT",
    "DRINK_KEEP",
    "DRINK_MIN",
    "DROUGHT_DAYS",
    "EAT_GAIN",
    "EAT_GRASS_GAIN",
    "EAT_GRASS_MIN",
    "FAMINE_DAYS",
    "FAMINE_GRASS",
    "FARM_MAX",
    "FERTILE_AGE",
    "FIRE_FEED",
    "FIRE_YANG0",
    "FOOD_YANG",
    "FRIEND_REL",
    "FROST_AT",
    "Farm",
    "Fence",
    "Fireplace",
    "GATHER_GRASS_MIN",
    "GEN_NAMES",
    "GIFT_REL",
    "GOSSIP_CHANCE",
    "GOSSIP_DISTORT",
    "GOSSIP_EMO",
    "GOSSIP_EMO_CAP",
    "GOSSIP_MAX_HOP",
    "GOSSIP_SURVIVE",
    "GOSSIP_WEIGHT",
    "HARVEST_GAIN",
    "HEIR_TELL",
    "HUNGER_YANG",
    "HUNT_BASE",
    "HUT_OWN_REPAIR_AT",
    "HUT_REPAIR",
    "HUT_YANG0",
    "ITEM_VALUE",
    "ITEM_YANG",
    "ITEM_YANG_TOOL",
    "Item",
    "LEARN_GATE",
    "LEND_REL",
    "LIE_CLEAR_W",
    "LIE_DENY",
    "MATERIAL_NEED",
    "MATE_CHANCE",
    "MATE_REL",
    "MEMORY_ETERNAL",
    "MEMORY_FORGET",
    "MIGRATE_GIVEUP",
    "MIGRATE_NEAR",
    "MISJUDGE",
    "MOURN_DECAY",
    "MOVE_COST",
    "Memory",
    "NAMES",
    "OLD_AGE_DAY",
    "PATH_AT",
    "PATH_COST",
    "PLANT_COST",
    "PLANT_MOIST",
    "POP_CAP",
    "POTTERY_CLAY",
    "PRAY_AFFINITY",
    "PRAY_ANSWER",
    "PRAY_COOLDOWN",
    "PRAY_GRASS",
    "PRAY_RANGE",
    "PRESSURE_DECAY",
    "PRESSURE_MAX",
    "RAW_KINDS",
    "RAW_SICK",
    "RECIPES",
    "REGION_SIZE",
    "RELIC_DAYS",
    "ROB_AGGR",
    "ROB_CHANCE",
    "ROB_COOLDOWN",
    "ROB_GREEDY_YANG",
    "ROB_HUNGER",
    "ROB_WEAKER",
    "SEIZE_AGGR",
    "SENSE_DAY",
    "SENSE_NIGHT",
    "SEW_TICKS_VINE",
    "SHARE_NEED",
    "SHARE_PAIR_CD",
    "SHARE_REL",
    "SHARE_SELF",
    "SHARE_YANG",
    "SHELL_VALUE",
    "SKILL_DOMAIN",
    "SKILL_GAIN",
    "STRENGTH_CAP",
    "TALK_CHANCE",
    "TALK_PAIR_CD",
    "TAME_CHANCE",
    "TEACH_CHANCE",
    "THIRST_DECAY",
    "THIRST_LOW",
    "THIRST_URGENT",
    "TICKS_PER_DAY",
    "TOOL_PRIORITY",
    "TRADE_CHANCE",
    "TRAIN_COST",
    "TRAIN_GAIN",
    "TRAIN_SAFE_YANG",
    "WEAPON_BONUS",
    "WELL_DIG_TICKS",
    "WITNESS_FRESH",
    "Well",
    "World",
    "YANG_DECAY",
    "YANG_RATE",
    "GLEAM_AT",
    "GLEAM_TICKS",
    "GLEAM_FAKE",
    "GLEAM_SAVE",
    "GLEAM_SAGE_KNOW",
    "GLEAM_SAGE_WIT",
    "YIN_FENCE",
    "YIN_FIRE",
    "YIN_HUT",
    "_GOSSIP_DEED",
    "_GOSSIP_KILL",
    "_KIND_VERB",
    "_QUOTES_PROTECT",
    "_QUOTES_ROBBED",
    "_QUOTES_SAVED",
    "_REL_NEG",
    "_REL_POS",
    "_成形基因组",
    "body_curve",
    "dataclass",
    "is_night",
    "夹01",
    "新名",
    "物形阴",
    "环境印记",
    "转阳",
]
