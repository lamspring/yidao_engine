# -*- coding: utf-8 -*-
"""v6 兼容壳：灵体层已迁入 yidao_core.spirit，此处仅为向后兼容的转口。"""
import os as _os
import sys as _sys

_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))

from yidao_core.spirit import *  # noqa: F401,F403
from yidao_core.spirit import Spirit, Memory, NAMES, GEN_NAMES, 新名  # noqa: F401
