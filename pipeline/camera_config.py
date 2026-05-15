# -*- coding: utf-8 -*-
"""摄像机配置 — 用户控制 LLM 的观测焦点"""
from dataclasses import dataclass, field
from typing import Optional, List


@dataclass
class CameraConfig:
    """
    摄像机配置。

    摄像机不是给用户直接阅读的，而是控制 LLM 观测世界的"镜头"。
    用户通过调整这些参数，间接控制 LLM 生成叙事的内容和风格。
    """
    focus: str = "family"               # "family" | entity_name | protocol_name
    variant_lock: Optional[str] = None  # None | "道家" | "科幻" | "神话" | "存在主义" | 自定义tag
    distance: str = "medium"            # "closeup" | "medium" | "panorama"
    style: str = "polished"             # "raw" | "polished"
    sensory_dims: List[str] = field(default_factory=list)  # 空=全部，如 ["visual","sound"]

    def status_line(self) -> str:
        """返回一行人类可读的状态摘要。"""
        focus_display = self.focus
        variant_display = self.variant_lock if self.variant_lock else "未锁定"
        distance_map = {"closeup": "特写", "medium": "中景", "panorama": "全景"}
        distance_display = distance_map.get(self.distance, self.distance)
        style_display = "白描" if self.style == "polished" else "结构化"
        return f"聚焦: {focus_display} | 变体: {variant_display} | 距离: {distance_display} | 风格: {style_display}"

    def to_dict(self) -> dict:
        return {
            "focus": self.focus,
            "variant_lock": self.variant_lock,
            "distance": self.distance,
            "style": self.style,
            "sensory_dims": self.sensory_dims,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "CameraConfig":
        return cls(
            focus=d.get("focus", "family"),
            variant_lock=d.get("variant_lock"),
            distance=d.get("distance", "medium"),
            style=d.get("style", "polished"),
            sensory_dims=d.get("sensory_dims", []),
        )
