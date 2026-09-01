# -*- coding: utf-8 -*-
"""
《易道引擎》v6.0 "鱼缸" — 灵体世界最小可行原型

三层架构（详见 docs/engine-v6-lingti.md）：
  世界层  world.py    只有此刻，不存历史；水往低处流，草木依水土生。
  灵体层  spirit.py   记忆（压缩/遗忘/永存）· 心情 · 欲望 · 抉择。
  天道    tiandao.py  无为而治，只在崩溃边缘做最小干预。
  观测层  fishbowl.py 终端文字流；LLM 不在演化回路中。

运行：python -m v6.fishbowl --ticks 640 --seed 42
"""

from .world import World, TICKS_PER_DAY
from .spirit import Spirit
from .tiandao import Tiandao

__version__ = "6.0.0-fishbowl"
__all__ = ["World", "Spirit", "Tiandao", "TICKS_PER_DAY"]
