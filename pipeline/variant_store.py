# -*- coding: utf-8 -*-
"""变体语库仓库 — 支持三层存储与 CRUD"""
import json
import os
from typing import List, Dict, Optional


# 系统默认变体的英文别名（Windows 终端友好）
_VARIANT_ALIASES = {
    "dao": "道家",
    "scifi": "科幻",
    "sciencefiction": "科幻",
    "myth": "神话",
    "existentialism": "存在主义",
    "exist": "存在主义",
}


class VariantStore:
    """
    管理协议文学变体的三层存储：
      1. 系统默认（renderer.PROTOCOL_LIBRARY）
      2. 世界观级（worldview JSON 中的 lexicon_variants）
      3. 会话级（运行时用户增删改）
    """

    def __init__(self, worldview=None):
        self._session: Dict[str, Dict[str, str]] = {}   # protocol -> {tag: content}
        self._worldview = worldview
        self._worldview_variants: Dict[str, Dict[str, str]] = {}
        self._load_defaults()
        if worldview:
            self._load_worldview(worldview)

    @staticmethod
    def _resolve_tag(tag: str) -> str:
        """将英文别名解析为中文标签。"""
        return _VARIANT_ALIASES.get(tag.lower(), tag)

    def _load_defaults(self):
        """从 renderer.PROTOCOL_LIBRARY 加载系统默认变体。"""
        from renderer import PROTOCOL_LIBRARY
        self._defaults: Dict[str, Dict[str, str]] = {}
        for protocol, lib in PROTOCOL_LIBRARY.items():
            variants = lib.get("variants", {})
            if variants:
                self._defaults[protocol] = dict(variants)

    def _load_worldview(self, worldview):
        """从世界观配置加载 lexicon_variants。"""
        if not worldview or not worldview.protocol_map:
            return
        for protocol, entry in worldview.protocol_map.items():
            lexicons = entry.get("lexicon_variants", [])
            if lexicons:
                self._worldview_variants[protocol] = {}
                for idx, content in enumerate(lexicons):
                    tag = f"世界观_{idx + 1}"
                    self._worldview_variants[protocol][tag] = content

    # ── 查询 ──

    def list_protocols(self) -> List[str]:
        """返回所有有变体的协议名（合并三层）。"""
        keys = set(self._defaults.keys())
        keys.update(self._worldview_variants.keys())
        keys.update(self._session.keys())
        return sorted(keys)

    def list_variants(self, protocol: str) -> List[Dict]:
        """
        返回某协议的所有变体，按优先级合并三层。
        格式: [{"tag": str, "content": str, "source": "system|worldview|session"}, ...]
        """
        result = []
        seen_tags = set()

        # 会话级（最高优先级）
        for tag, content in self._session.get(protocol, {}).items():
            result.append({"tag": tag, "content": content, "source": "session"})
            seen_tags.add(tag)

        # 世界观级
        for tag, content in self._worldview_variants.get(protocol, {}).items():
            if tag not in seen_tags:
                result.append({"tag": tag, "content": content, "source": "worldview"})
                seen_tags.add(tag)

        # 系统默认
        for tag, content in self._defaults.get(protocol, {}).items():
            if tag not in seen_tags:
                result.append({"tag": tag, "content": content, "source": "system"})
                seen_tags.add(tag)

        return result

    def get_variant_content(self, protocol: str, tag: str) -> Optional[str]:
        """按优先级查找变体内容（支持英文别名）。"""
        tag = self._resolve_tag(tag)
        if protocol in self._session and tag in self._session[protocol]:
            return self._session[protocol][tag]
        if protocol in self._worldview_variants and tag in self._worldview_variants[protocol]:
            return self._worldview_variants[protocol][tag]
        if protocol in self._defaults and tag in self._defaults[protocol]:
            return self._defaults[protocol][tag]
        return None

    def has_variant(self, protocol: str, tag: str) -> bool:
        return self.get_variant_content(protocol, tag) is not None

    # ── CRUD ──

    def add_variant(self, protocol: str, tag: str, content: str) -> bool:
        """添加会话级变体。如果 tag 已存在（任意层级），返回 False。"""
        tag = self._resolve_tag(tag)
        if self.has_variant(protocol, tag):
            return False
        if protocol not in self._session:
            self._session[protocol] = {}
        self._session[protocol][tag] = content
        return True

    def remove_variant(self, protocol: str, tag: str) -> bool:
        """删除变体。只能删除会话级。"""
        tag = self._resolve_tag(tag)
        if protocol in self._session and tag in self._session[protocol]:
            del self._session[protocol][tag]
            if not self._session[protocol]:
                del self._session[protocol]
            return True
        return False

    def update_variant(self, protocol: str, tag: str, content: str) -> bool:
        """更新变体。只能更新会话级。"""
        tag = self._resolve_tag(tag)
        if protocol in self._session and tag in self._session[protocol]:
            self._session[protocol][tag] = content
            return True
        return False

    def persist(self, config_dir: str = "./configs") -> bool:
        """
        将会话级变体写回当前世界观 JSON 文件。
        返回是否成功。
        """
        if not self._worldview:
            return False
        path = os.path.join(config_dir, "worldviews", f"{self._worldview.name}.json")
        if not os.path.isfile(path):
            return False
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            for protocol, variants in self._session.items():
                if protocol not in data.get("protocol_map", {}):
                    continue
                existing = data["protocol_map"][protocol].get("lexicon_variants", [])
                # 将 session 变体追加（避免重复）
                for tag, content in variants.items():
                    if content not in existing:
                        existing.append(content)
                data["protocol_map"][protocol]["lexicon_variants"] = existing
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception:
            return False

    def format_table(self, protocol: str) -> str:
        """返回某协议变体的表格字符串，供 CLI 显示。"""
        variants = self.list_variants(protocol)
        if not variants:
            return f"  协议 '{protocol}' 暂无变体。"
        lines = [f"  ── '{protocol}' 变体列表 ──"]
        for v in variants:
            src_mark = {"session": "[会话]", "worldview": "[世界观]", "system": "[系统]"}.get(v["source"], "")
            content_preview = v["content"][:40] + "..." if len(v["content"]) > 40 else v["content"]
            lines.append(f"    {src_mark} {v['tag']}: {content_preview}")
        return "\n".join(lines)
