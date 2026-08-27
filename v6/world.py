# -*- coding: utf-8 -*-
"""v6 兼容壳：世界层已迁入 yidao_core.world，此处仅为向后兼容的转口。"""
import os as _os
import sys as _sys

_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))

from yidao_core.world import *  # noqa: F401,F403
from yidao_core.world import (World, Mark, Building, Farm, Tree, Carrion,  # noqa: F401
                              Animal, Fireplace, Fence, Item,
                              TICKS_PER_DAY, is_night, season_factor, day_length,
                              cycle_day, sunlight, FROST_AT, HEAT_AT, FIRE_FEED,
                              BEASTS)
