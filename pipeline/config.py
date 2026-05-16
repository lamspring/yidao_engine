# -*- coding: utf-8 -*-
"""配置管理 — 支持从JSON配置文件加载LLM提供商和世界观"""
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
import json
import os


@dataclass
class EntityConfig:
    name: str
    y: int
    x: int
    radius: int = 3
    description: str = ""


@dataclass
class WorldConfig:
    height: int = 32
    width: int = 64
    ticks: int = 1500
    snapshot_interval: int = 150
    camera_scale: str = "meso"
    camera_intent: str = "character"


@dataclass
class LLMConfig:
    base_url: str = ""
    api_key: str = ""
    model: str = ""
    temperature: float = 0.75
    max_tokens: int = 5000
    timeout: int = 180
    max_retries: int = 2

    @classmethod
    def from_provider(cls, provider_name: str, config_dir: str = "./configs", api_key: str | None = None) -> "LLMConfig":
        """从配置文件加载LLM提供商配置。api_key 可传入以覆盖环境变量。"""
        providers_path = os.path.join(config_dir, "llm_providers.json")
        if not os.path.exists(providers_path):
            raise FileNotFoundError(f"LLM提供商配置文件不存在: {providers_path}")
        with open(providers_path, "r", encoding="utf-8") as f:
            providers = json.load(f)
        if provider_name not in providers:
            available = ", ".join(providers.keys())
            raise ValueError(f"未知LLM提供商 '{provider_name}'。可用: {available}")
        p = providers[provider_name]
        # 优先使用传入的 api_key，其次从环境变量读取（支持多个候选，逗号分隔）
        resolved_key = api_key or ""
        if not resolved_key:
            env_var_str = p.get("api_key_env", "")
            env_vars = [ev.strip() for ev in env_var_str.split(",") if ev.strip()]
            for ev in env_vars:
                if ev in os.environ:
                    resolved_key = os.environ[ev]
                    break
        if not resolved_key and provider_name != "local":
            env_hint = p.get("api_key_env", "对应的环境变量")
            raise ValueError(
                f"提供商 '{provider_name}' 需要设置环境变量 {env_hint}，但当前为空。"
                f"请执行：export {env_hint}=your_key_here (Linux/Mac) 或 set {env_hint}=your_key_here (Windows)"
            )
        return cls(
            base_url=p["base_url"],
            api_key=resolved_key,
            model=p.get("default_model", ""),
            temperature=p.get("temperature", 0.75),
            max_tokens=p.get("max_tokens", 5000),
            timeout=p.get("timeout", 180),
            max_retries=p.get("max_retries", 2),
        )


@dataclass
class WorldViewConfig:
    """世界观绑定层配置"""
    name: str = ""
    description: str = ""
    protocol_map: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    relation_templates: Dict[str, str] = field(default_factory=dict)
    flip_ritual: Dict[str, Any] = field(default_factory=dict)
    character_archetypes: Dict[str, str] = field(default_factory=dict)
    era_labels: Dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_file(cls, worldview_name: str, config_dir: str = "./configs") -> "WorldViewConfig":
        """从配置文件加载世界观"""
        path = os.path.join(config_dir, "worldviews", f"{worldview_name}.json")
        if not os.path.exists(path):
            # 尝试自动发现可用世界观
            worldviews_dir = os.path.join(config_dir, "worldviews")
            available = []
            if os.path.isdir(worldviews_dir):
                available = [f.replace(".json", "") for f in os.listdir(worldviews_dir) if f.endswith(".json")]
            avail_str = ", ".join(available) if available else "无"
            raise FileNotFoundError(f"世界观配置不存在: {path}。可用: {avail_str}")
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls(
            name=data.get("name", worldview_name),
            description=data.get("description", ""),
            protocol_map=data.get("protocol_map", {}),
            relation_templates=data.get("relation_templates", {}),
            flip_ritual=data.get("flip_ritual", {}),
            character_archetypes=data.get("character_archetypes", {}),
            era_labels=data.get("era_labels", {}),
        )

    def translate_protocol(self, protocol: str, key: str = "name") -> str:
        """将系统协议翻译为世界观的专有名词"""
        if protocol in self.protocol_map:
            entry = self.protocol_map[protocol]
            if key == "name":
                return entry.get("name", protocol)
            if key == "description":
                return entry.get("description", protocol)
            if key == "sensory":
                return entry.get("sensory", {})
        return protocol

    def translate_relation(self, relation_type: str) -> str:
        """翻译体用关系为世界观的描述"""
        return self.relation_templates.get(relation_type, relation_type)


@dataclass
class PipelineConfig:
    mode: str = "family"
    style: str = "polished"
    world: WorldConfig = field(default_factory=WorldConfig)
    entities: List[EntityConfig] = field(default_factory=list)
    llm: LLMConfig = field(default_factory=LLMConfig)
    worldview: Optional[WorldViewConfig] = None
    output_dir: str = "./outputs"
    run_name: Optional[str] = None

    @classmethod
    def default_family(cls) -> "PipelineConfig":
        return cls(
            mode="family",
            style="polished",
            world=WorldConfig(ticks=1500, snapshot_interval=150),
            entities=[
                EntityConfig("father",    12, 28, 3, "父亲 — 家族的根基与秩序"),
                EntityConfig("mother",    12, 32, 3, "母亲 — 家族的渗透与滋养"),
                EntityConfig("eldest",    14, 26, 3, "长子 — 家族的锋芒与开拓"),
                EntityConfig("second",    14, 34, 3, "次子 — 家族的变动与探索"),
                EntityConfig("youngest",  16, 30, 3, "幼女 — 家族的生机与变数"),
            ],
        )

    @classmethod
    def default_dual(cls) -> "PipelineConfig":
        return cls(
            mode="dual",
            style="polished",
            world=WorldConfig(ticks=1500, snapshot_interval=150),
            entities=[
                EntityConfig("entity_north", 10, 20, 4, "北方偏西的实体"),
                EntityConfig("entity_south", 22, 44, 4, "南方偏东的实体"),
            ],
        )

    @classmethod
    def default_single(cls) -> "PipelineConfig":
        return cls(
            mode="single",
            style="polished",
            world=WorldConfig(ticks=1500, snapshot_interval=100),
            entities=[
                EntityConfig("watched_entity", 16, 32, 4, "被观测的核心实体"),
            ],
        )
