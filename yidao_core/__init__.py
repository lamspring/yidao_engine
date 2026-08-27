# -*- coding: utf-8 -*-
"""
yidao_core —— 《易道引擎》世界底座。

四层结构：
  太初层  genesis  —— 从无到有：炁场 → 涨落 → 极化 → 凝聚（World.genesis / seed_at）
  世界层  world    —— 阴阳物质物理：天气、水文、生死、物质腐坏
  灵体层  spirit   —— 记忆 / 心情 / 欲望 / 抉择 / 繁衍（灵 = 记忆体，世界无史而人心有史）
  天道层  tiandao  —— 防崩溃兜底，无为而治，介入必留痕

约束：零第三方依赖（仅 numpy）；确定性（显式种子）；世界只存此刻，不写历史。
观测层（终端文字流、GUI、游戏引擎）在本包之外，通过 Session 接入。
"""

from .world import World, TICKS_PER_DAY, is_night
from .spirit import Spirit, NAMES, 新名
from .tiandao import Tiandao
from .session import Session

__version__ = "0.1.0"

__all__ = ["World", "Spirit", "Tiandao", "Session", "NAMES", "新名",
           "TICKS_PER_DAY", "is_night", "__version__"]
