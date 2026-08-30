# -*- coding: utf-8 -*-
"""灵体层包（M2/M2b 组件化）：对外接口与旧 spirit.py 完全一致。

灵 = 一束组件（身/谱/心/欲/学/产/缘/忆/闻/程，见 components.py）。
96 个方法体一行未改：扁平读写经 ROUTE 路由桥入组件（兼容桥，行为不变）。
诞育自指：kinship._诞育 方法体原文引用 Spirit，包组装后注入真身。
"""

from .base import *
from .components import (Body, Genome, Mind, Desire, Knowledge, Property,
                         Relations, Remembrance, Intel, Itinerary,
                         组件字段, ROUTE)

from .sense import 感知Mixin
from .subsist import 生计Mixin
from .learning import 学习Mixin
from .social import 社交Mixin
from .conflict import 争斗Mixin
from .build import 营建Mixin
from .kinship import 婚育Mixin
from .migrate import 徙居Mixin
from .settle import 安身Mixin
from .core import 核心Mixin


class Spirit(感知Mixin, 生计Mixin, 学习Mixin, 社交Mixin, 争斗Mixin,
             营建Mixin, 婚育Mixin, 徙居Mixin, 安身Mixin, 核心Mixin):
    """灵：记忆体。世界无史而人心有史。"""

    def __init__(self, *args, **kwargs):
        # 先建组件（灵是一束组件），再走原初构造——字段经路由写入组件
        for c, cls in 组件字段.items():
            object.__setattr__(self, c, cls())
        super().__init__(*args, **kwargs)

    # ── 兼容桥：扁平名读写 → 组件（路由表见 components.py）──
    def __getattr__(self, k):
        c = ROUTE.get(k)
        if c is None:
            raise AttributeError(k)
        return getattr(object.__getattribute__(self, c), k)

    def __setattr__(self, k, v):
        c = ROUTE.get(k)
        if c is None:
            object.__setattr__(self, k, v)
        else:
            setattr(object.__getattribute__(self, c), k, v)


# 诞育自指：注入真身（kinship._诞育 方法体原文引用 Spirit）
from . import kinship as _kinship
_kinship.Spirit = Spirit
