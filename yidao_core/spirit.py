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
    from .world import (World, Farm, Carrion, Fence, Fireplace, Item, Well,
                        TICKS_PER_DAY, is_night, FROST_AT, FIRE_FEED, BEASTS,
                        WELL_DIG_TICKS, PATH_AT, PATH_COST)
except ImportError:  # 允许 v6/fishbowl.py 以脚本方式直跑
    from world import (World, Farm, Carrion, Fence, Fireplace, Item, Well,
                       TICKS_PER_DAY, is_night, FROST_AT, FIRE_FEED, BEASTS,
                       WELL_DIG_TICKS, PATH_AT, PATH_COST)

# ───────────────────────────────────────────
# 0. 灵体常数（调参集中于此）
# ───────────────────────────────────────────

YANG_DECAY = 0.10       # 阳·每念自然逸散
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
             "蛋": 8.0, "奶": 8.0, "谷种": 6.0}
RAW_KINDS = {"生肉", "生鱼"}
RAW_SICK = 0.15         # 生食致病概率（腹泻 → 阳损 + 坏记忆）
EAT_GRASS_GAIN = 14.0   # 野菜野草：能活，但算不上好日子

# 制器配方：类型 → 材料表。制器成功率随熟练提升
RECIPES = {"石斧": {"石": 1, "木": 1}, "石刀": {"石": 1}, "鱼竿": {"木": 1, "藤": 1},
           "耒耜": {"木": 2}, "背篓": {"藤": 2}, "石矛": {"石": 1, "木": 1, "藤": 1},
           "棍棒": {"木": 1}}
TOOL_PRIORITY = ["石斧", "石刀", "鱼竿", "石矛", "耒耜", "背篓", "棍棒"]
WEAPON_BONUS = {"石矛": 0.50, "棍棒": 0.30, "石斧": 0.15, "石刀": 0.10}
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
GOSSIP_MAX_HOP = 3      # 话传三站而止：传闻链长上限
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
ITEM_VALUE = {"熟肉": 4, "熟鱼": 3, "生肉": 3, "生鱼": 2, "蛋": 2, "奶": 2, "谷种": 1,
              "木": 2, "石": 2, "藤": 1, "骨": 1, "茅草": 1,
              "石斧": 8, "石刀": 6, "鱼竿": 7, "耒耜": 7, "背篓": 6, "石矛": 9, "棍棒": 5,
              "土": 1, "美石": 2, "陶罐": 7, "寒衣": 8, "骨饰": 6, "美贝": SHELL_VALUE}

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
        dna = {
            "谨慎": 夹01(rng.uniform(0.2, 0.95) * 0.8 + env.get("谨慎", 0.5) * 0.2
                       + rng.uniform(-0.05, 0.05)),
            "悍戾": 夹01((rng.uniform(0.55, 0.95) if rng.random() < 0.3
                        else rng.betavariate(1.3, 4.0)) * 0.8 + env.get("悍戾", 0.45) * 0.2
                       + rng.uniform(-0.05, 0.05)),
            "亲和": 夹01(rng.uniform(0.3, 0.7) * 0.8 + env.get("亲和", 0.5) * 0.2
                       + rng.uniform(-0.05, 0.05)),
            "悟性": 夹01(rng.uniform(0.2, 0.9) * 0.8 + env.get("悟性", 0.5) * 0.2
                       + rng.uniform(-0.05, 0.05)),
            "体质": 夹01(rng.random() * 0.8 + env.get("体质", 0.5) * 0.2
                       + rng.uniform(-0.05, 0.05)),
        }
        for k in DNA_技艺:
            dna[k] = 夹01(env.get(k, 0.3) + rng.uniform(-0.08, 0.08))
        return dna
    w_血 = 代 / (代 + 1)
    w_环 = 1.0 / (代 + 1)
    pa, pb = 亲
    return {k: 夹01(w_血 * (pa.get(k, 0.5) + pb.get(k, 0.5)) / 2
                  + w_环 * env.get(k, 0.5)
                  + rng.uniform(-0.08, 0.08))
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


class Spirit:
    """灵体：有记忆、有心情、有欲望、会抉择。"""

    def __init__(self, name: str, y: int, x: int, tick: int, rng, 父母=None,
                 env: dict | None = None):
        self.name = name
        self.y, self.x = y, x
        self.诞生念 = tick
        self.alive = True

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
    # 一、感知：昼五夜二，所见即所知
    # ───────────────────────────────────────

    def _感知半径(self, tick: int) -> int:
        return SENSE_NIGHT if is_night(tick) else SENSE_DAY

    @staticmethod
    def _切比(y1, x1, y2, x2) -> int:
        return max(abs(y1 - y2), abs(x1 - x2))

    def _感知(self, world: World, spirits: list, tick: int, report, rng) -> bool:
        """每念扫视四周：记下眼见的食物与水源、谁在眼前、谁家屋檐与田畦、何处有故人之骨。
        返回 True 表示本念已被悼念占去。"""
        r = self._感知半径(tick)
        self._stay[(self.y, self.x)] = self._stay.get((self.y, self.x), 0) + 1
        for dy in range(-r, r + 1):
            for dx in range(-r, r + 1):
                ny, nx = self.y + dy, self.x + dx
                if not world.in_bounds(ny, nx):
                    continue
                if world.grass[ny, nx] >= EAT_GRASS_MIN:
                    self.known_food[(ny, nx)] = tick
                elif (ny, nx) in self.known_food and world.grass[ny, nx] < EAT_GRASS_MIN:
                    del self.known_food[(ny, nx)]   # 亲见枯竭，从心中抹去
                if world.water[ny, nx] >= DRINK_MIN:
                    self.known_water[(ny, nx)] = tick
        for s in spirits:
            if s is not self and s.alive \
                    and self._切比(self.y, self.x, s.y, s.x) <= r:
                self._last_seen[s.name] = (s.y, s.x, tick, s.strength)

        # 看见别人的茅屋/农田：记下"那是谁的"（所有权是社会记忆），
        # 看在眼里、记在心里——日久看明白门道，模仿由此而生（积学，不再掷骰）
        for b in world.buildings:
            if self._切比(self.y, self.x, b.y, b.x) > r:
                continue
            self._known_huts[b.主人] = (b.y, b.x)
            if "建造" not in self.knowledge and b.主人 != self.name \
                    and self._积学("建造", 2.5, tick, report,
                                   f"看明白了 {b.主人} 的茅屋，悟得建造之法", "观察模仿"):
                self.remember(f"看懂了 {b.主人} 的茅屋，悟得建造之法", "学会", b.主人, 0.60, tick)
        for f in world.farms:
            if self._切比(self.y, self.x, f.y, f.x) > r:
                continue
            if "种植" not in self.knowledge and f.主人 != self.name \
                    and self._积学("种植", 2.5, tick, report,
                                   f"看明白了 {f.主人} 的田畦，悟得种植之法", "观察模仿"):
                self.remember(f"看懂了 {f.主人} 的田畦，悟得种植之法", "学会", f.主人, 0.60, tick)
        # 火堆入眼：记下何处有火（寒夜可以投奔）
        for f in world.fires:
            if self._切比(self.y, self.x, f.y, f.x) <= r:
                self._known_fires[f.主人] = (f.y, f.x)

        # 井入眼：记下何处有井（旱时可以来汲）；看得久了，自会看出凿井的门道
        for wl in world.wells:
            if self._切比(self.y, self.x, wl.y, wl.x) > r:
                continue
            self._known_wells[(wl.y, wl.x)] = wl.主人
            if "凿井" not in self.knowledge and wl.主人 != self.name \
                    and self._积学("凿井", 2.5, tick, report,
                                   f"看明白了 {wl.主人} 的井，悟得凿井之法", "观察模仿"):
                self.remember(f"看懂了 {wl.主人} 的井，悟得凿井之法", "学会", wl.主人, 0.60, tick)

        # 亲见落雨：旱魃之惧随之刷新。祈过雨的人此刻最敏感——
        # 三日内的雨都算"得应"：纯巧合，但人心不这么记（迷信从巧合中诞生）。
        if world.raining_on(self.y, self.x):
            self._雨见 = tick
            if self._祈雨 is not None:
                发起, 祈念 = self._祈雨
                self._祈雨 = None
                if tick - 祈念 <= PRAY_ANSWER * TICKS_PER_DAY:
                    if 发起 != self.name:
                        self.remember(f"{发起} 祈雨得应，甘霖果至", "祈应", 发起, 0.75, tick)
                    else:
                        self.remember("我祈的雨竟落了下来", "祈应", None, 0.70, tick)
                    self.mood["希望"] = 1.0
                    report(tick, (self.y, self.x),
                           f"{self.name} 淋着雨，坚信 {发起} 的祈雨得了应（因：雨后之巧+人心信之）",
                           kind="祈应", actor=self.name, target=发起)

        # 悼念：好友的遗骨就在眼前，岂能不停一停；在场同识者闻哀同悲（同悼）。
        # 误会：认得死者却不知其死因，见有人在遗骨/遗物旁徘徊——疑心生暗鬼。
        for m in world.marks:
            if m.类型 != "尸骨" or not m.标签:
                continue
            key = (m.y, m.x, m.诞生念)
            if key in self._mourned:
                continue
            if self._切比(self.y, self.x, m.y, m.x) > r:
                continue
            if self.relation(m.标签) >= FRIEND_REL:
                self._mourned.add(key)
                self.remember(f"在 {m.标签} 的遗骨前伫立良久", "悼念", m.标签, 0.70, tick)
                self.mood["希望"] = max(0.0, self.mood["希望"] - 0.2)
                report(tick, (m.y, m.x),
                       f"{self.name} 在 {m.标签} 的遗骨前伫立良久（因：故人之思）",
                       kind="悼念", actor=self.name, target=m.标签)
                self._同悼(world, spirits, m, tick, report)
                return True
            if self._生疑(spirits, m.标签, m.y, m.x, key, tick, report, rng):
                return True
        for rl in world.relics:
            key = ("遗物", rl["y"], rl["x"], rl["念"])
            if self._切比(self.y, self.x, rl["y"], rl["x"]) > r:
                continue
            if self._生疑(spirits, rl["名"], rl["y"], rl["x"], key, tick, report, rng):
                return True
        return False

    def _生疑(self, spirits: list, 亡者: str, y: int, x: int, key, tick: int,
              report, rng) -> bool:
        """疑心生暗鬼：认得死者、不知其死因，见有人在遗骨/遗物旁徘徊，
        概率性误以为此人是凶手——记下一笔与真目睹无异的错误记忆。疑只起一次。"""
        if key in self._疑过:
            return False
        if not any(m.对象 == 亡者 and m.类别 != "传闻" for m in self.memories):
            return False    # 根本不识死者，无从生疑
        骨旁 = [s for s in spirits if s is not self and s.alive
                and getattr(s, "_已成年", True)
                and self._切比(s.y, s.x, y, x) <= 1
                and self._切比(self.y, self.x, s.y, s.x) <= self._感知半径(tick)
                and not any(m.对象 == s.name and m.类别 == "目睹"
                            for m in self.memories)]
        if not 骨旁:
            return False
        self._疑过.add(key)
        if rng.random() >= MISJUDGE * (0.5 + self.caution):
            return False
        嫌 = rng.choice(骨旁)
        # 错误记忆与真目睹同类别、同文字——在灵心里，误会与事实不可分辨
        self.remember(f"目睹 {嫌.name} 行凶", "目睹", 嫌.name, 0.65, tick)
        self.mood["恐惧"] = min(1.0, self.mood["恐惧"] + 0.2)
        report(tick, (y, x),
               f"{self.name} 见 {嫌.name} 徘徊在 {亡者} 的遗骨遗物旁，疑其为凶（因：疑心生暗鬼+感知有限）",
               kind="误会", actor=self.name, target=嫌.name, subject=亡者)
        return True

    def _同悼(self, world: World, spirits: list, mark, tick: int, report):
        """一人举哀，闻者同悲：在场、同识死者、尚未致哀的人同声而哀。
        共同的哀伤把生者拉近——葬礼的雏形，群体纽带由此而生。"""
        key = (mark.y, mark.x, mark.诞生念)
        同识 = []
        for s in spirits:
            if s is self or not s.alive or not getattr(s, "_已成年", True):
                continue
            if key in s._mourned:
                continue
            if self._切比(s.y, s.x, mark.y, mark.x) > s._感知半径(tick):
                continue
            if s.relation(mark.标签) < FRIEND_REL * 0.6:
                continue
            同识.append(s)
        if not 同识:
            return
        for s in 同识:
            s._mourned.add(key)
            s.remember(f"在 {mark.标签} 的遗骨前同声而哀", "悼念", mark.标签, 0.60, tick)
            s.remember(f"与 {self.name} 同悼 {mark.标签}", "同悼", self.name, 0.50, tick)
            self.remember(f"与 {s.name} 同悼 {mark.标签}", "同悼", s.name, 0.50, tick)
        名 = "、".join([self.name] + [s.name for s in 同识])
        report(tick, (mark.y, mark.x),
               f"{名} 在 {mark.标签} 的遗骨前同声而哀（因：故人之思+同气相感）",
               kind="同悼", actor=self.name, target=mark.标签)

    def _感知到(self, s, tick: int) -> bool:
        return s.alive and self._切比(self.y, self.x, s.y, s.x) <= self._感知半径(tick)

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
                self.yang = cap
        if tick - self.诞生念 >= self.寿数:
            self._寿终(world, tick, report, spirits)
            return
        if not self._已成年:
            self._幼年(world, spirits, tick, report, rng)
            return

        self._心情漂移()
        self.pressure = max(0.0, self.pressure - PRESSURE_DECAY)

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
                衣.阳 -= 0.03                # 寒气磨衣：衣会旧、会敝
                if 衣.阳 <= 0:
                    self.bag.remove(衣)
                    self.remember("我的寒衣敝了", "器损", None, 0.40, tick)
                    report(tick, (self.y, self.x),
                           f"{self.name} 的寒衣散成了碎藤（因：寒气磨衣，阳尽则敝）",
                           kind="衣敝", actor=self.name)
            else:
                逸散 += -气温 * 0.015
        self._耗阳(逸散)
        self.水分 = max(0.0, self.水分 - THIRST_DECAY)

        # 随身物什各按其材质腐坏（寒慢热快）；陶罐藏粮，腐坏减半。
        # 存粮腐坏是锥心之痛——痛一次，积一分烧土为瓮之思。
        有罐 = any(it.类型 == "陶罐" for it in self.bag)
        坏食 = []
        存 = []
        for it in self.bag:
            藏 = 0.55 if (有罐 and it.类型 in FOOD_YANG) else 1.0
            if it.腐一步(气温, 藏=藏):
                if it.类型 in FOOD_YANG:
                    坏食.append(it.类型)
            else:
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

    # ── 一·观察 ─────────────────────────────

    def _区域键(self) -> str:
        return f"{self.y // REGION_SIZE},{self.x // REGION_SIZE}"

    def _区域有记忆(self) -> bool:
        key = self._区域键()
        return any(m.类别 == "区域" and m.对象 == key and m.权重 >= MEMORY_FORGET
                   for m in self.memories)

    def _观察(self, world: World, tick: int):
        """踏勘陌生之地：记下区域、压下未知恐惧（食物水源已由感知收录）。"""
        key = self._区域键()
        旧 = next((m for m in self.memories if m.类别 == "区域" and m.对象 == key), None)
        if 旧 is not None:
            旧.权重 = 0.3
            旧.念戳 = tick
        else:
            self.remember(f"踏勘过{world.terrain_name(self.y, self.x)}一带",
                          "区域", key, 0.15, tick)
        self.mood["恐惧"] = max(0.0, self.mood["恐惧"] - 0.15)
        self.mood["希望"] = min(1.0, self.mood["希望"] + 0.05)
        self._耗阳(0.05)

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
                    b.yang -= 8.0
                    self.yang = min(100.0, self.yang + 8.0)
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
        """吃下一份食物。熟食养人；生食有病患之险。"""
        self.bag.remove(it)
        self.yang = min(100.0, self.yang + FOOD_YANG[it.类型])
        self.stats["进食"] += 1
        # 吃过一口熟食，便想学这手艺——吃一口积一分
        if it.类型 in ("熟肉", "熟鱼"):
            self._积学("烹饪", 12.0, tick, report,
                       "吃了熟食，一心想学这手艺", "熟食之美")
        if it.类型 in RAW_KINDS and rng.random() < RAW_SICK:
            self.yang -= 5.0
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
            self.yang = min(100.0, self.yang + EAT_GRASS_GAIN)
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
                        self.bag.append(Item("生鱼"))
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
                肉, 骨 = {"鸡": (2, 1), "羊": (4, 2), "牛": (6, 3)}[a.种类]
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
            罐.盛水 = 0.0
            self.水分 = 100.0
            self.stats["饮水"] += 1
            report(tick, (self.y, self.x),
                   f"{self.name} 饮尽陶罐中所储之水（因：口渴+储水备旱）",
                   kind="饮水", actor=self.name)
            return
        if world.water[self.y, self.x] >= DRINK_MIN:
            self._饮水(world, tick, report, rng)
            self._灌罐(report, tick)
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

    def _灌罐(self, report, tick):
        """饮于水泽时，顺手把空陶罐灌满。"""
        罐 = next((it for it in self.bag if it.类型 == "陶罐" and it.盛水 <= 0), None)
        if 罐 is not None:
            罐.盛水 = 60.0
            report(tick, (self.y, self.x),
                   f"{self.name} 把陶罐灌满了水（因：储水备旱）",
                   kind="灌水", actor=self.name)

    def _汲井(self, world: World, tick: int, report, rng) -> bool:
        """在井边汲水。井水取自九泉；井淤则淘之，井枯则徒叹。"""
        well = world.well_at(self.y, self.x)
        if well is None:
            self._known_wells.pop((self.y, self.x), None)
            return False
        st = world.汲井(well)
        if st == "活":
            self.水分 = 100.0
            self.stats["饮水"] += 1
            self._灌罐(report, tick)
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
        self.水分 = 100.0
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
        猎物.yang -= amount
        self.yang = min(100.0, self.yang + amount * 0.8)
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

    # ── 祈雨聚（v6.4）：天道永不回应，仪式是群体的镇定剂 ──

    def _祈雨聚(self, world: World, spirits: list, tick: int, report, rng) -> bool:
        """连旱草枯之际，亲和高者发起祈雨聚；邻近灵闻讯而来，围聚一处，费率一日。
        天道永不回应祈雨——但参与者恐惧下降、关系上升、互记"同祈"；
        若三日内恰有雨至（纯巧合），参与者记"祈雨得应"，发起者声望由此而起。
        迷信从巧合中诞生，这是真实人性。"""
        day = tick // TICKS_PER_DAY
        # 赴祈：闻讯而来，到场则同祈
        if self._赴祈 is not None:
            y, x, d, 发起 = self._赴祈
            if d != day or is_night(tick):
                self._赴祈 = None
                return False
            if self._切比(self.y, self.x, y, x) <= 1:
                self._赴祈 = None
                self._祈雨 = (发起, tick)
                主 = next((s for s in spirits if s.alive and s.name == 发起), None)
                if 主 is not None:
                    self.remember(f"与 {发起} 同祈甘霖", "同祈", 发起, 0.50, tick)
                    主.remember(f"{self.name} 来与我同祈", "同祈", self.name, 0.45, tick)
                self.mood["恐惧"] = max(0.0, self.mood["恐惧"] - 0.25)
                self.mood["希望"] = min(1.0, self.mood["希望"] + 0.10)
                report(tick, (self.y, self.x),
                       f"{self.name} 赶来与 {发起} 同祈甘霖（因：闻讯而至+同忧则同祈）",
                       kind="赴祈", actor=self.name, target=发起)
                # 祈雨不应，不如凿井：同忧之际，有人低头看向了大地
                self._积学("凿井", 12.0, tick, report,
                           "祈雨之余忽悟：雨不应人，低洼之下或有九泉，可凿井取之", "祈雨不应")
                return True
            self._走向(world, y, x, rng)
            return True
        # 发起者守祀一日：围聚之处，不远离
        if self._祀_day == day:
            self.mood["疲惫"] = max(0.0, self.mood["疲惫"] - 0.05)
            return True
        # 发起条件：白昼、连旱、草枯、亲和高、温饱有余
        if is_night(tick) or self.affinity < PRAY_AFFINITY:
            return False
        if tick - self._雨见 < DROUGHT_DAYS * TICKS_PER_DAY:
            return False
        if day - self._祀_day < PRAY_COOLDOWN:
            return False
        if self.yang < 50.0 or self.水分 < 40.0:
            return False
        r = 3
        草 = [world.grass[self.y + dy, self.x + dx]
              for dy in range(-r, r + 1) for dx in range(-r, r + 1)
              if world.in_bounds(self.y + dy, self.x + dx)]
        if not 草 or sum(草) / len(草) > PRAY_GRASS:
            return False
        if rng.random() > 0.5:
            return False
        # 发起！邻近灵闻讯而来
        self._祀_day = day
        旱日 = (tick - self._雨见) // TICKS_PER_DAY
        闻讯 = [s for s in spirits if s is not self and s.alive
                and getattr(s, "_已成年", True)
                and self._切比(s.y, s.x, self.y, self.x) <= PRAY_RANGE
                and s.relation(self.name) > -0.3
                and s.yang > 40.0 and s.水分 > 35.0 and s._迁 is None]
        for s in 闻讯:
            s._赴祈 = (self.y, self.x, day, self.name)
        self._祈雨 = (self.name, tick)
        self.mood["恐惧"] = max(0.0, self.mood["恐惧"] - 0.15)
        report(tick, (self.y, self.x),
               f"{self.name} 于{world.terrain_name(self.y, self.x)}之上发起祈雨聚，"
               f"{len(闻讯)} 灵闻讯而来（因：连旱{旱日}日+草枯苗焦）",
               kind="祈雨聚", actor=self.name)
        # 祈雨不应，不如凿井：发起者在仰天之余，也可能低头看向大地
        self._积学("凿井", 12.0, tick, report,
                   "祈雨之余忽悟：雨不应人，低洼之下或有九泉，可凿井取之", "祈雨不应")
        return True

    # ── 逃荒与迁徙（v6.4）：故土资源崩溃 → 弃家携眷，迁往丰饶 ──

    def _察荒(self, world: World, spirits: list, tick: int, report, rng):
        """每日一次打量故土：居所四周草枯水涸积够三日，便生弃家迁徙之念。"""
        day = tick // TICKS_PER_DAY
        if self._荒_day == day or is_night(tick) or self._迁 is not None:
            return
        self._荒_day = day
        hy, hx = self._栖身所()
        if self._切比(self.y, self.x, hy, hx) > 6:
            return
        r = 4
        草, 水 = [], False
        for dy in range(-r, r + 1):
            for dx in range(-r, r + 1):
                ny, nx = hy + dy, hx + dx
                if world.in_bounds(ny, nx):
                    草.append(world.grass[ny, nx])
                    if world.water[ny, nx] >= DRINK_MIN:
                        水 = True
        # 井也是水：近处有井，故土不算涸——凿井真能安住人心
        if not 水:
            for (wy, wx) in self._known_wells:
                if world.well_at(wy, wx) is not None \
                        and self._切比(hy, hx, wy, wx) <= r:
                    水 = True
                    break
        if 草 and sum(草) / len(草) < FAMINE_GRASS and not 水:
            self._荒 += 1
        else:
            self._荒 = 0
        if self._荒 >= FAMINE_DAYS and self.yang > 45.0:
            self._起迁(world, spirits, tick, report, rng)

    def _起迁(self, world: World, spirits: list, tick: int, report, rng):
        """弃家携眷，迁往丰饶处（记忆中最新的远处食点；无则望一个方向闯出去）。
        不动产尽弃：屋田栏火留作无主遗迹——门楣之名犹在，物是人非。"""
        远处 = [(t, p) for p, t in self.known_food.items()
                if self._切比(self.y, self.x, p[0], p[1]) >= MIGRATE_NEAR]
        if 远处:
            远处.sort()
            ty, tx = 远处[-1][1]
        else:
            向 = [(0, 1), (0, -1), (1, 0), (-1, 0), (1, 1), (1, -1), (-1, 1), (-1, -1)]
            d = 向[rng.randrange(8)]
            ty = int(max(0, min(world.size - 1, self.y + d[0] * 14)))
            tx = int(max(0, min(world.size - 1, self.x + d[1] * 14)))
        self._迁 = (ty, tx, tick)
        self._迁由 = "故土草枯水涸"
        self._荒 = 0
        故居 = (self.y, self.x)
        self._弃产(world)
        # 携眷：伴侣同行，稚子自会跟着父母
        眷 = next((s for s in spirits if s.alive and s.name == self.伴侣), None)
        if 眷 is not None and 眷._迁 is None:
            眷._迁 = (ty, tx, tick)
            眷._迁由 = f"随 {self.name} 举家而迁"
            眷._荒 = 0
            眷._弃产(world)
            眷.remember(f"随 {self.name} 弃家而迁", "迁徙", self.name, 0.60, tick)
        携 = f"携 {眷.name} " if 眷 is not None else ""
        self.remember("弃家而迁，故土难留", "迁徙", None, 0.65, tick)
        report(tick, 故居,
               f"{self.name} {携}弃宅而去，踏上迁徙之路（因：{self._迁由}）",
               kind="迁徙", actor=self.name, target=眷.name if 眷 else None)

    def _弃产(self, world: World):
        """丢弃不动产：屋留原地风雨飘摇，田栏火改称"荒"，牲畜野化。"""
        self.hut = None       # 屋成无主遗迹，门楣之名犹在
        self._家门 = None
        self._工地 = None
        self._井地 = None
        for f in world.farms:
            if f.主人 == self.name:
                f.主人 = "荒"
        for f in world.fences:
            if f.主人 == self.name:
                f.主人 = "荒"
        for f in world.fires:
            if f.主人 == self.name:
                f.主人 = "荒"
        for a in world.animals:
            if a.驯主 == self.name:
                a.驯主 = None
                a.栏位 = None

    def _行迁(self, world: World, tick: int, report, rng) -> bool:
        """迁徙途中：昼行夜宿，不到新土不止；抵达或跋涉太久则落脚。"""
        ty, tx, 起 = self._迁
        到 = self._切比(self.y, self.x, ty, tx) <= 2
        疲 = tick - 起 > MIGRATE_GIVEUP * TICKS_PER_DAY
        if 到 or 疲:
            self._迁 = None
            self._stay = {}     # 落脚新土，栖身所重新长出来
            self._荒 = -2       # 初到之地休养生息两日，再打量故土荒否
            self.mood["希望"] = min(1.0, self.mood["希望"] + 0.2)
            注 = "寻得新土" if 到 else "跋涉力竭，就地落脚"
            report(tick, (self.y, self.x),
                   f"{self.name} 迁抵{world.terrain_name(self.y, self.x)}，于此重建家园"
                   f"（因：{self._迁由}+{注}）",
                   kind="迁抵", actor=self.name)
            return False        # 落脚的这一念，余下时光照常过
        self._走向(world, ty, tx, rng)
        return True

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
                self.yang -= SHARE_YANG
                b.yang = min(100.0, b.yang + SHARE_YANG)
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
                    self.yang -= 10.0
                    b.yang = min(100.0, b.yang + 10.0)
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
        失真率随传播链长度上升。话传三站而止。"""
        if rng.random() > GOSSIP_CHANCE:
            return
        # 挑一桩关于第三方的旧事作谈资（不与 b 重复人尽皆知之事）
        素材 = [m for m in self.memories
                if m.对象 not in (None, self.name, b.name)
                and m.权重 >= 0.2 and m.链长 < GOSSIP_MAX_HOP
                and (m.类别 in _GOSSIP_DEED or (m.类别 == "传闻" and m.褒贬 != 0))
                and not any(x.类别 == "传闻" and x.对象 == m.对象 for x in b.memories)]
        if not 素材:
            return
        src = 素材[rng.randrange(len(素材))]
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

    # ── 人情三事：借贷、还债、馈赠、交易 ──────

    def _摸器悟法(self, it, tick: int, report, rng):
        """摸到他人所制之器而积其法：陶罐启制陶，衣饰启缝纫——模仿不止于看，也在于摸。"""
        if it.类型 == "陶罐":
            self._积学("制陶", 12.0, tick, report,
                       "摩挲陶罐良久，悟得其烧制之法", "观察模仿+触物生情")
        elif it.类型 in ("寒衣", "骨饰"):
            self._积学("缝纫", 12.0, tick, report,
                       f"细看{it.类型}的针脚，悟得缝纫之法", "观察模仿+触物生情")

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
                self.yang -= 10.0
                b.yang = min(100.0, b.yang + 10.0)
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
                self.yang -= 10.0
                b.yang = min(100.0, b.yang + 10.0)
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

    # ── 婚育：结侣与诞育（v6.2）──────────────

    def _婚配(self, world: World, spirits: list, tick: int, report, rng) -> bool:
        """男婚女嫁：相邻、两情相悦、有檐可依、温饱 → 结为伴侣。（生养是夜半私事，见 decide 夜分支）"""
        if self.伴侣 is not None:
            p = next((s for s in spirits if s.alive and s.name == self.伴侣), None)
            if p is None:
                self.伴侣 = None   # 鳏寡之人，可再续弦
            else:
                return False
        for b in self._邻居们(spirits):
            if not b._已成年 or b.伴侣 is not None:
                continue
            if self.relation(b.name) < MATE_REL or b.relation(self.name) < MATE_REL:
                continue
            if self.yang < 55.0 or b.yang < 55.0:
                continue
            if self.hut is None and b.hut is None:
                continue    # 无片瓦者，何以家为
            if rng.random() > MATE_CHANCE:
                continue
            self.伴侣 = b.name
            b.伴侣 = self.name
            # 定下共同的家门：两口子同住一檐下
            家屋 = self.hut or b.hut
            self._家门 = b._家门 = (家屋.y, 家屋.x)
            # 交换家门所在：从此配偶的屋檐也是家
            if self.hut is not None:
                b._known_huts[self.name] = (self.hut.y, self.hut.x)
            if b.hut is not None:
                self._known_huts[b.name] = (b.hut.y, b.hut.x)
            self.remember(f"与 {b.name} 结为伴侣", "伴侣", b.name, 0.95, tick)
            b.remember(f"与 {self.name} 结为伴侣", "伴侣", self.name, 0.95, tick)
            report(tick, (self.y, self.x),
                   f"{self.name} 与 {b.name} 结为伴侣（因：两情相悦+有檐可依）",
                   kind="结侣", actor=self.name, target=b.name)
            return True
        return False

    def _诞育(self, world: World, spirits: list, partner, tick: int, report, rng) -> bool:
        """生养：夜里同檐、温饱有余、生育窗口内、间隔既过 → 阴凝聚得一点阳，新生儿诞生。"""
        if tick - self._上次诞育 < BIRTH_PAIR_CD:
            return False
        年龄日 = (tick - self.诞生念) / TICKS_PER_DAY
        if not (FERTILE_AGE[0] <= 年龄日 <= FERTILE_AGE[1]):
            return False
        if not is_night(tick):
            return False
        if sum(1 for s in spirits if s.alive) >= POP_CAP:
            return False
        屋 = self.hut or partner.hut
        if 屋 is None:
            return False
        if self._切比(self.y, self.x, 屋.y, 屋.x) > 2:
            return False
        if self.yang < 50.0 or partner.yang < 50.0:
            return False
        if rng.random() > BIRTH_NIGHT_CHANCE:
            return False
        self._上次诞育 = tick
        partner._上次诞育 = tick
        name = 新名(spirits, rng)
        # 出生地环境写入婴儿 DNA：生在谁家檐下，就染上哪方水土
        child = Spirit(name, 屋.y, 屋.x, tick, rng, 父母=(self, partner),
                       env=环境印记(world, 屋.y, 屋.x))
        spirits.append(child)
        self.子女.append(name)
        partner.子女.append(name)
        self.remember(f"我与 {partner.name} 得子 {name}", "伴侣", partner.name, 0.95, tick)
        partner.remember(f"我与 {self.name} 得子 {name}", "伴侣", self.name, 0.95, tick)
        report(tick, (屋.y, 屋.x),
               f"【诞】{self.name} 与 {partner.name} 得子 {name}（因：温饱有余+伉俪情深）",
               kind="诞育", actor=self.name, target=name)
        return True

    # ── 九·锻炼 ─────────────────────────────

    def _锻炼(self, tick: int, report):
        # "开始锻炼"每日至多报一次——日日苦练是心志，不是新闻
        if not self.training and tick - self._last_train_report >= TICKS_PER_DAY:
            self._last_train_report = tick
            report(tick, (self.y, self.x),
                   f"{self.name} 开始锻炼（因：受辱铭记，欲求变强）",
                   kind="锻炼始", actor=self.name)
        self.training = True
        self.stats["锻炼"] += 1
        gain = TRAIN_GAIN * (1.0 - 0.5 * self.mood["疲惫"])
        self.strength = min(STRENGTH_CAP, self.strength + gain)
        self.mood["疲惫"] = min(1.0, self.mood["疲惫"] + 0.02)
        self._耗阳(TRAIN_COST)

    # ── 十·游荡与安眠 ────────────────────────

    def _栖身所(self) -> tuple[int, int]:
        """栖身处：结侣之家优先；有屋则屋为家；否则是记忆中最常停留的格子。"""
        if self._家门 is not None:
            return self._家门
        if self.hut is not None:
            return (self.hut.y, self.hut.x)
        if self.伴侣 is not None and self.伴侣 in self._known_huts:
            return self._known_huts[self.伴侣]
        if not self._stay:
            return (self.y, self.x)
        return max(self._stay.items(), key=lambda kv: kv[1])[0]

    def _檐下(self, world: World) -> bool:
        """此刻头顶是否有屋檐：自己的屋、配偶的屋，或今夜收留我之人的屋。"""
        b = world.building_at(self.y, self.x)
        if b is None:
            return False
        return b.主人 == self.name or b.主人 == self._庇主 or b.主人 == self.伴侣

    def _安眠(self, world: World, 有檐: bool):
        """归栖而眠：檐下安眠，疲惫大解；露宿则雨打风吹，歇不踏实。"""
        self.stats["安眠"] += 1
        self.mood["疲惫"] = max(0.0, self.mood["疲惫"] - (0.08 if 有檐 else 0.05))
        self.mood["希望"] = min(1.0, self.mood["希望"] + 0.02)
        self.training = False

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
                self.bag.append(Item("生肉"))
            for _ in range(c.骨 if 刀 else (1 if c.骨 and self._数料("骨") < 2
                                            and ({"缝纫", "制器"} & self.knowledge) else 0)):
                self.bag.append(Item("骨"))
            world.carrions.remove(c)
            report(tick, (self.y, self.x),
                   f"{self.name} 肢解了{c.名}的尸骸，得肉{肉}（因：{'石刀之利' if 刀 else '徒手可及'}）",
                   kind="屠宰", actor=self.name)
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
                self.bag.append(Item("木"))
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
        # 采石（高地）：石中偶有美者——美石是饰品的料
        if world.height[self.y, self.x] >= 6.5 and world.stone[self.y, self.x] >= 1.0:
            world.stone[self.y, self.x] -= 1.0
            if rng.random() < 0.15 and self._数料("美石") < 2:
                self.bag.append(Item("美石"))
                report(tick, (self.y, self.x),
                       f"{self.name} 采得一枚美石（因：高地有石+石中美者）",
                       kind="采石", actor=self.name)
            else:
                self.bag.append(Item("石"))
                report(tick, (self.y, self.x),
                       f"{self.name} 采得一块石头（因：高地有石）",
                       kind="采石", actor=self.name)
            self._积学("制器", 10.0, tick, report,
                       "采石时忽有所悟：木石可成器，是为制器", "劳作日久")
            return True
        # 采藤（水泽边）
        if world.vine[self.y, self.x] >= 1.0:
            world.vine[self.y, self.x] -= 1.0
            self.bag.append(Item("藤"))
            report(tick, (self.y, self.x),
                   f"{self.name} 采得一把藤蔓（因：泽畔有藤）",
                   kind="采藤", actor=self.name)
            return True
        # 掘土（泽畔河泥，制陶之料）
        if "制陶" in self.knowledge and self._数料("土") < POTTERY_CLAY \
                and world.moisture[self.y, self.x] > 0.45 and world.water[self.y, self.x] < 1.5:
            self.bag.append(Item("土"))
            report(tick, (self.y, self.x),
                   f"{self.name} 掘取河泥得土（因：制陶之需）",
                   kind="采土", actor=self.name)
            return True
        # 采贝：水泽边俯拾，低概率得美贝——天然稀缺，贝币之雏形
        if world.moisture[self.y, self.x] > 0.45 and world.water[self.y, self.x] < 1.5 \
                and self._数料("美贝") < 4 and rng.random() < 0.010:
            self.bag.append(Item("美贝"))
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
                    self._取建材()
                    self.hut.阳 = min(80.0, self.hut.阳 + HUT_REPAIR)
                    report(tick, (self.y, self.x),
                           f"{self.name} 修缮了自家茅屋（因：风雨剥蚀，屋阳将亏）",
                           kind="修缮", actor=self.name)
                    return True
                if self._建材数() < 1:
                    if world.grass[self.y, self.x] >= GATHER_GRASS_MIN:
                        world.grass[self.y, self.x] -= 0.4
                        self.bag.append(Item("茅草"))
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
                self.bag.append(Item("茅草"))
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
            for _ in range(MATERIAL_NEED):
                self._取建材()
            self.hut = world.add_building(ty, tx, self.name)
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
                self.yang = min(100.0, self.yang + HARVEST_GAIN)
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
                self.yang -= PLANT_COST
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

    def _涨熟练(self, 技能: str):
        # 禀赋加成：该域 DNA 禀赋给熟练增速 20% 加成
        禀赋 = self.dna.get(SKILL_DOMAIN.get(技能, ""), 0.5)
        self.skills[技能] = min(1.0, self.skills.get(技能, 0.0)
                                + SKILL_GAIN * (1.0 + 0.2 * 禀赋))

    def _熟练(self, 技能: str) -> float:
        return self.skills.get(技能, 0.0)

    def _积学(self, 技能: str, 量: float, tick: int, report, 文: str, 因: str) -> bool:
        """真学习（v6.5）：经验积累取代掷骰顿悟。试错、观察、受挫都在攒经验，
        顿悟只是临门一脚。已会者不再积；增速受悟性与该域 DNA 禀赋修饰；
        经验过 LEARN_GATE 则豁然贯通（领悟事件注明积学几日）。返回是否贯通。"""
        if 技能 in self.knowledge:
            return False
        if 技能 not in self._学始:
            self._学始[技能] = tick
        禀赋 = self.dna.get(SKILL_DOMAIN.get(技能, ""), 0.5)
        self._学习[技能] = self._学习.get(技能, 0.0) \
            + 量 * (0.6 + 0.5 * self.悟性) * (0.55 + 0.9 * 禀赋)
        if self._学习[技能] < LEARN_GATE[技能]:
            return False
        self.knowledge.add(技能)
        历时 = max(1, round((tick - self._学始.pop(技能)) / TICKS_PER_DAY))
        self._学习.pop(技能, None)
        report(tick, (self.y, self.x),
               f"{self.name} {文}（因：{因}·积学{历时}日乃悟）",
               kind="领悟", actor=self.name)
        return True

    def _磨损(self, 类型: str, tick: int, report):
        """工具会磨损；阳尽断裂。"""
        it = next((i for i in self.bag if i.类型 == 类型), None)
        if it is None:
            return
        it.阳 -= 1.5
        if it.阳 <= 0:
            self.bag.remove(it)
            self.remember(f"我的{类型}用断了", "器损", None, 0.45, tick)
            report(tick, (self.y, self.x),
                   f"{self.name} 的{类型}断了（因：磨损日久，阳尽则断）",
                   kind="器断", actor=self.name)

    def _受冻(self, world: World, tick: int, report, rng):
        """寒夜彻骨：记下一笔。冻一夜，积一分——有人想出钻木取火，有人想着添衣。"""
        day = tick // TICKS_PER_DAY
        if self._受冻_day == day:
            return
        self._受冻_day = day
        self.remember("寒夜彻骨，几冻毙", "受冻", None, 0.55, tick)
        report(tick, (self.y, self.x),
               f"{self.name} 寒夜受冻（因：天地转阴+无火无檐）",
               kind="受冻", actor=self.name)
        self._积学("取火", 12.0, tick, report,
                   "在寒夜里想出钻木取火", "受冻已久")
        # 寒夜受冻的第二条出路：有人取火，有人添衣
        self._积学("缝纫", 8.0, tick, report,
                   "冻得搓手顿足，忽想以藤为线、以骨为针，缀衣以御寒", "受冻已久")
        # 冻怕了的人也想有四面墙：受冻同启建造之思
        self._积学("建造", 6.0, tick, report,
                   "冻得缩成一团，忽想有个挡风之屋", "受冻已久")

    def _钻木(self, world: World, tick: int, report, rng) -> bool:
        """钻木取火：需干柴一份（木最佳，茅草藤叶亦可引火），概率成功（悟性+熟练），得火一堆。"""
        柴 = self._取料("木") or self._取料("茅草") or self._取料("藤")
        if 柴 is None:
            return False
        if rng.random() < 0.35 + 0.5 * self.悟性 + 0.3 * self._熟练("取火"):
            self._涨熟练("取火")
            屋内 = self.hut is not None and (self.y, self.x) == (self.hut.y, self.hut.x)
            world.fires.append(Fireplace(self.y, self.x, self.name, 屋内=屋内))
            self._known_fires[self.name] = (self.y, self.x)
            self.mood["希望"] = min(1.0, self.mood["希望"] + 0.3)
            report(tick, (self.y, self.x),
                   f"{self.name} 钻木得火，{'屋内起灶' if 屋内 else '野地生烟'}（因：寒夜所迫+取火之技）",
                   kind="取火", actor=self.name)
            # 得火即炙：怀中若揣着生食又懂烹饪，新火第一灶
            if "烹饪" in self.knowledge:
                self._烹制(world, tick, report, rng)
        else:
            self._耗阳(0.4)
            report(tick, (self.y, self.x),
                   f"{self.name} 钻木良久，未得火（因：手生）",
                   kind="取火败", actor=self.name)
        return True

    def _赴火(self, world: World, tick: int, rng) -> bool:
        """向火而去：先找看得见的炊烟（感知半径内），再找记忆中的火。"""
        r = self._感知半径(tick)
        见火 = [fi for fi in world.fires
                if self._切比(self.y, self.x, fi.y, fi.x) <= r]
        if 见火:
            f0 = min(见火, key=lambda fi: self._切比(self.y, self.x, fi.y, fi.x))
            self._走向(world, f0.y, f0.x, rng)
            return True
        # 记忆中的火若已熄，忘掉这处；否则前往
        死火 = [k for k, p in self._known_fires.items()
                if world.fire_near(p[0], p[1], 0) is None]
        for k in 死火:
            del self._known_fires[k]
        if self._known_fires:
            fy, fx = min(self._known_fires.values(),
                         key=lambda p: abs(p[0] - self.y) + abs(p[1] - self.x))
            self._走向(world, fy, fx, rng)
            return True
        return False

    def _烹制(self, world: World, tick: int, report, rng) -> bool:
        """携生食赴火而炙：熟食之利，值得多走几步。看见炊烟即知火处。"""
        生 = next((it for it in self.bag if it.类型 in RAW_KINDS), None)
        if 生 is None:
            return False
        f = world.fire_near(self.y, self.x)
        if f is None:
            if self._赴火(world, tick, rng):
                return True
            # 无火可觅而会取火：有干柴就地点一堆
            if "取火" in self.knowledge and not world.raining_on(self.y, self.x):
                if any(self._数料(k) >= 1 for k in ("木", "茅草", "藤")):
                    return self._钻木(world, tick, report, rng)
            return False
        # 火在身旁：炙之
        self.bag.remove(生)
        熟 = "熟肉" if 生.类型 == "生肉" else "熟鱼"
        self.bag.append(Item(熟))
        self._涨熟练("烹饪")
        self.mood["希望"] = min(1.0, self.mood["希望"] + 0.1)
        初次 = self.stats.get("烹食", 0) == 0
        self.stats["烹食"] = self.stats.get("烹食", 0) + 1
        report(tick, (self.y, self.x),
               f"{self.name} 以火炙{生.类型[1:]}为熟食（因：烹饪之技+火堆在侧）",
               kind="烹食初" if 初次 else "烹食", actor=self.name)
        return True

    def _百工(self, world: World, spirits: list, tick: int, report, rng) -> bool:
        """温饱之上的营生：添柴 → 备料 → 制器 → 制陶 → 缝纫 → 烹饪 → 畜牧。"""
        # 备料：知百工而缺料，则采眼见之材（木/石/藤/土/骨）
        if self.knowledge & {"制器", "取火", "畜牧", "制陶", "缝纫"}:
            if self._备料(world, tick, report, rng):
                return True
        # 添柴：自家的火，阳亏则续一份木——火要靠养
        for f in world.fires:
            if f.主人 == self.name and f.阳 < 30.0 \
                    and abs(f.y - self.y) <= 2 and abs(f.x - self.x) <= 2 \
                    and self._数料("木") >= 1:
                self._取料("木")
                f.阳 = min(80.0, f.阳 + FIRE_FEED)
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
                    for k, v in 料.items():
                        for _ in range(v):
                            self._取料(k)
                    if rng.random() < 0.5 + 0.5 * self._熟练("制器"):
                        self.bag.append(Item(器))
                        self._涨熟练("制器")
                        report(tick, (self.y, self.x),
                               f"{self.name} 制成了{器}（因：制器之技+材料齐备）",
                               kind="制器", actor=self.name)
                    else:
                        self._耗阳(0.3)
                        report(tick, (self.y, self.x),
                               f"{self.name} 制{器}失败，费了些材料（因：手艺生疏）",
                               kind="制器败", actor=self.name)
                    return True
        # 制陶：知法 + 有土 + 窑/火堆旁才能烧
        if "制陶" in self.knowledge and not self._有器("陶罐") \
                and self._数料("土") >= POTTERY_CLAY:
            if world.fire_near(self.y, self.x) is None:
                if self._赴火(world, tick, rng):
                    return True
            else:
                for _ in range(POTTERY_CLAY):
                    self._取料("土")
                if rng.random() < 0.5 + 0.5 * self._熟练("制陶"):
                    self.bag.append(Item("陶罐"))
                    self._涨熟练("制陶")
                    report(tick, (self.y, self.x),
                           f"{self.name} 和泥成坯，就火烧成一只陶罐（因：制陶之技+火边烧制）",
                           kind="制陶", actor=self.name)
                else:
                    self._耗阳(0.3)
                    report(tick, (self.y, self.x),
                           f"{self.name} 烧陶裂了坯，费了些土（因：手艺生疏）",
                           kind="制陶败", actor=self.name)
                return True
        # 缝纫：以藤为线、以骨为针——寒衣御寒，骨饰传情
        if "缝纫" in self.knowledge:
            if not self._有器("寒衣") and self._数料("藤") >= SEW_TICKS_VINE \
                    and self._数料("骨") >= 1:
                self._取料("藤")
                self._取料("藤")
                self._取料("骨")
                if rng.random() < 0.5 + 0.5 * self._熟练("缝纫"):
                    self.bag.append(Item("寒衣"))
                    self._涨熟练("缝纫")
                    report(tick, (self.y, self.x),
                           f"{self.name} 以藤为线、以骨为针，缝成一件寒衣（因：寒夜受冻+缝纫之技）",
                           kind="缝纫", actor=self.name)
                else:
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
            self._取料("骨")
            镶 = self._取料("美石") is not None
            if rng.random() < 0.5 + 0.5 * max(self._熟练("缝纫"), self._熟练("制器")):
                self.bag.append(Item("骨饰"))
                self._涨熟练("缝纫")
                report(tick, (self.y, self.x),
                       f"{self.name} {'琢骨镶石' if 镶 else '琢骨'}，成一枚骨饰（因：爱美之心+闲工）",
                       kind="琢饰", actor=self.name)
            else:
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
                self._取料("木")
                self._取料("木")
                hy, hx = self._栖身所()
                for dy in (0, 1, -1, 2, -2):
                    for dx in (0, 1, -1, 2, -2):
                        ny, nx = hy + dy, hx + dx
                        if world.in_bounds(ny, nx) and world.water[ny, nx] < 1.0 \
                                and world.building_at(ny, nx) is None:
                            world.fences.append(Fence(ny, nx, self.name))
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
                self.bag.append(Item("蛋"))
                a.产物念 = p["蛋期"]
                self._涨熟练("畜牧")
                report(tick, (self.y, self.x),
                       f"{self.name} 从鸡窝里拾了一枚蛋（因：畜牧之劳）",
                       kind="收蛋", actor=self.name)
                return True
            self.bag.append(Item("奶"))
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
        败.yang -= rng.uniform(12.0, 20.0)   # 分出高下，不必见生死
        胜.yang -= rng.uniform(2.0, 5.0)

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
        self.yang -= amount

    def _死否(self, world: World, tick: int, report, 因: str, spirits: list = ()) -> bool:
        """阳尽则亡：遗体成尸骨印记（带姓名，供故人悼念），保质约 2 日后化为土。
        死后有善后：遗物归亲人，无亲则遗于野；听过父母深仇的孩子从此背负。"""
        if self.alive and self.yang <= 0:
            self.yang = 0.0
            self.alive = False
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
        self.yang = 0.0
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

    # ── 幼年：跟随父母，受哺育，耳濡目染 ──────

    def _幼年(self, world: World, spirits: list, tick: int, report, rng):
        """幼崽不事生产、不争斗：跟着父母，饿了受哺，看着学着长大。"""
        self._心情漂移()
        self._耗阳(YANG_DECAY * self.metabo * 0.6)   # 孩童耗阳少些
        self.水分 = max(0.0, self.水分 - THIRST_DECAY)
        if self._死否(world, tick, report, "阳尽", spirits):
            return
        if self._感知(world, spirits, tick, report, rng):
            return
        亲 = [s for s in spirits if s.alive and s.name in (self.父母 or ())]
        if not 亲:
            # 无亲可依的孤雏，只得早当起家
            self._已成年 = True
            report(tick, (self.y, self.x),
                   f"{self.name} 无亲可依，提前长大成人（因：孤儿早当家）",
                   kind="成年", actor=self.name)
            return
        亲.sort(key=lambda p: self._切比(self.y, self.x, p.y, p.x))
        p = 亲[0]
        d = self._切比(self.y, self.x, p.y, p.x)
        # 饿了：父母在旁则受哺
        if self.yang < 60.0 and d <= 1 and p.yang > 40.0:
            p.yang -= 12.0
            self.yang = min(100.0, self.yang + 12.0)
            self.stats["进食"] += 1
            self.remember(f"{p.name} 哺育我", "亲缘", p.name, 0.85, tick)
            return
        if self.水分 < 40.0 and world.water[self.y, self.x] >= DRINK_MIN:
            self._饮水(world, tick, report, rng)
            return
        if d > CHILD_FOLLOW:
            self._走向(world, p.y, p.x, rng)
            return
        # 家传：父母在身边劳作，孩子看着学着——每日灌注一门（门槛的三成半），
        # 最强的知识通道也非一蹴而就：手把手几日，方能自得
        day = tick // TICKS_PER_DAY
        if self._家传_day != day and d <= 1:
            for kn in ("烹饪", "渔猎", "制器", "取火", "建造", "种植", "畜牧",
                       "凿井", "制陶", "缝纫"):
                if kn in p.knowledge and kn not in self.knowledge:
                    self._家传_day = day
                    self.remember(f"{p.name} 手把手教我{kn}之法", "受教", p.name, 0.70, tick)
                    p.remember(f"我把{kn}之法传给了 {self.name}", "家传", self.name, 0.55, tick)
                    report(tick, (self.y, self.x),
                           f"{p.name} 把{kn}之法手把手传给了 {self.name}（因：家传）",
                           kind="家传", actor=p.name, target=self.name)
                    self._积学(kn, LEARN_GATE[kn] * 0.35, tick, report,
                               f"承 {p.name} 家传，于{kn}之法日久自得", "家传目染")
                    break

    def _成年(self, world: World, spirits: list, tick: int, report):
        """成年礼：从此独自面对世界。父母把心中最重的往事讲给他听——口述历史。"""
        self._已成年 = True
        report(tick, (self.y, self.x),
               f"{self.name} 成年了，开始独自面对这个世界（因：岁月生长）",
               kind="成年", actor=self.name)
        for s in spirits:
            if not s.alive or s.name not in (self.父母 or ()):
                continue
            往事 = [m for m in sorted(s.memories, key=lambda m: (m.永存, m.权重),
                                      reverse=True)
                    if m.类别 not in ("区域", "亲缘")][:HEIR_TELL]
            for m in 往事:
                情绪 = m.情绪强度 * 0.7
                恨 = m.类别 in _REL_NEG
                self.remember(f"听{s.name}讲起：{m.要义}",
                              "听闻恨" if 恨 else "听闻", m.对象, 情绪, tick)

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
