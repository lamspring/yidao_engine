# -*- coding: utf-8 -*-
"""
交互式推演引擎 — 支持逐步推进、实时解释、变体锁定、叙事连续性
"""
import sys
import os
from typing import List, Dict, Optional
from dataclasses import dataclass, field

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pipeline.config import PipelineConfig
from pipeline.world_runner import WorldRunner, capture_compact
from pipeline.llm_client import LLMClient
from pipeline.camera_config import CameraConfig
from pipeline.variant_store import VariantStore
from pipeline import prompts
from pipeline import validator
from pipeline import state_manager
from codex import get_gua


@dataclass
class NarrativeEntry:
    """单幕叙事历史记录"""
    tick: int
    focus: str
    variant_lock: Optional[str]
    summary: str          # 用户或自动生成的摘要（50-100字）
    output_path: str      # 完整输出文件路径


class InteractiveRunner:
    """
    交互式推演引擎。

    核心循环:
      step() -> 推进 ticks -> 捕获 snapshot -> 等待用户 explain()
      explain() -> 构建语义包 -> 调用 LLM -> 验证 -> 保存 -> 更新历史
      reroll() -> 用同样语义包重新调用 LLM
      reset() -> 重置世界，保留配置
    """

    MIN_STEP_TICKS = 50   # 最小推进间隔，低于此值警告

    def __init__(self, cfg: PipelineConfig, output_dir: str = "./outputs"):
        self.cfg = cfg
        self.output_dir = output_dir
        self.runner = WorldRunner(cfg.world, cfg.entities)
        self.llm_client = LLMClient(cfg.llm)
        self.variant_store = VariantStore(cfg.worldview)
        self.camera = CameraConfig(
            focus="family",
            variant_lock=None,
            distance="medium",
            style=cfg.style,
        )
        self.narrative_history: List[NarrativeEntry] = []
        self.last_explain_tick = -1
        self.current_snapshots: List[dict] = []
        self._last_pkg: Optional[str] = None
        self._last_system: Optional[str] = None
        self._last_user: Optional[str] = None
        self._last_output: Optional[str] = None
        self._flip_in_last_step = False
        self._total_tokens_used = 0

    # ── 核心推进 ──

    def step(self, ticks: int) -> dict:
        """
        推进世界 ticks 次，捕获当前 snapshot，检测变化。
        返回状态字典。
        """
        if ticks < self.MIN_STEP_TICKS:
            return {
                "error": True,
                "message": f"间隔太小（{ticks} ticks），建议至少 {self.MIN_STEP_TICKS} ticks，"
                           f"否则 LLM 难以获得有效信息写出叙事。",
            }

        start_tick = self.runner.world.tick_count
        self._flip_in_last_step = False
        new_flips = []

        for i in range(ticks):
            self.runner.world.tick()
            for idx, t in enumerate(self.runner.trackers):
                t._update()
                if len(t.hex_history) >= 2:
                    prev, curr = t.hex_history[-2], t.hex_history[-1]
                    if prev != curr:
                        flip = {
                            "tick": self.runner.world.tick_count,
                            "pre_hex": prev, "post_hex": curr,
                            "pre_name": get_gua(prev)["name"],
                            "post_name": get_gua(curr)["name"],
                            "tracker": t.entity_id,
                        }
                        self.runner.flip_events[idx].append(flip)
                        new_flips.append(flip)
                        self._flip_in_last_step = True

        # 捕获当前 snapshot
        self.current_snapshots = []
        for idx, t in enumerate(self.runner.trackers):
            snap = capture_compact(
                self.runner.world, self.runner.cam, t, self.runner.analyst,
                f"{t.entity_id}_T{self.runner.world.tick_count}"
            )
            self.current_snapshots.append(snap)

        end_tick = self.runner.world.tick_count

        return {
            "error": False,
            "start_tick": start_tick,
            "end_tick": end_tick,
            "ticks_advanced": ticks,
            "flip_detected": self._flip_in_last_step,
            "new_flips": new_flips,
            "tracker_count": len(self.runner.trackers),
        }

    # ── 解释 / 叙事生成 ──

    def explain(self) -> str:
        """
        根据当前 snapshot 和 camera_config 生成叙事。
        返回 LLM 输出文本。
        """
        if not self.current_snapshots:
            return "[错误] 当前无 snapshot，请先执行 step() 推进世界。"

        # 1. 构建语义包
        pkg = self._build_snapshot_package()
        self._last_pkg = pkg

        # 2. 构建 prompts
        system, user = self._build_prompts(pkg)
        self._last_system = system
        self._last_user = user

        # 3. 调用 LLM（或 no-llm 模式）
        if self.cfg.llm.api_key or self.cfg.llm.base_url == "":
            # local 模式允许空 key
            pass
        if not self.cfg.llm.api_key and self.cfg.llm.base_url != "":
            return self._save_no_llm(pkg, system, user)

        try:
            output, usage = self.llm_client.call(system, user)
            self._last_output = output
            self._total_tokens_used += usage.get("prompt_tokens", 0) + usage.get("completion_tokens", 0)
        except Exception as e:
            return self._save_no_llm(pkg, system, user, error=str(e))

        # 4. 验证
        names = [e.name for e in self.cfg.entities]
        names.extend(["父亲", "母亲", "长子", "次子", "幼女", "儿子", "女儿", "姐姐", "哥哥", "弟弟", "妹妹"])
        if self.cfg.worldview and self.cfg.worldview.character_archetypes:
            for desc in self.cfg.worldview.character_archetypes.values():
                if " / " in desc:
                    names.append(desc.split(" / ")[0].strip())
                if " — " in desc:
                    names.append(desc.split(" — ")[0].strip())

        if self.camera.style == "polished":
            narrative = output
            for marker in ["### 对应关系", "### 二、对应关系", "### 附录", "### 映射标注", "### 叙事质量自检", "### 三、叙事质量自检"]:
                if marker in output:
                    narrative = output.split(marker)[0]
                    break
            checks = validator.validate_polished(output, narrative, names)
        else:
            checks = validator.validate_raw(output, {})
        all_pass = validator.print_results(checks)

        # 5. 保存输出
        out_path = self._save_outputs(pkg, system, user, output)

        # 6. 更新叙事历史（自动摘要：取输出前 100 字）
        summary = output[:100].replace("\n", " ") + "..."
        self.narrative_history.append(NarrativeEntry(
            tick=self.runner.world.tick_count,
            focus=self.camera.focus,
            variant_lock=self.camera.variant_lock,
            summary=summary,
            output_path=out_path,
        ))
        self.last_explain_tick = self.runner.world.tick_count

        # 7. 返回带元信息的输出
        meta = f"\n\n[幕 {len(self.narrative_history)}] tick={self.runner.world.tick_count} | " \
               f"聚焦={self.camera.focus} | 变体={self.camera.variant_lock or '无'} | " \
               f"验证={'PASS' if all_pass else '部分未通过'} | 累计tokens≈{self._total_tokens_used}"
        return output + meta

    def reroll(self) -> str:
        """重新生成当前叙事（不改变世界状态）。"""
        if self._last_pkg is None:
            return "[错误] 尚无叙事可重新生成，请先执行 explain()。"

        # 微调 temperature 增加变化
        original_temp = self.cfg.llm.temperature
        self.cfg.llm.temperature = min(original_temp + 0.1, 1.0)

        try:
            output, usage = self.llm_client.call(self._last_system, self._last_user)
            self._last_output = output
            self._total_tokens_used += usage.get("prompt_tokens", 0) + usage.get("completion_tokens", 0)
        except Exception as e:
            self.cfg.llm.temperature = original_temp
            return f"[错误] LLM 调用失败: {e}"
        finally:
            self.cfg.llm.temperature = original_temp

        # 保存但不加入 narrative_history
        out_path = self._save_outputs(self._last_pkg, self._last_system, self._last_user, output, suffix="_reroll")
        meta = f"\n\n[重新生成] tick={self.runner.world.tick_count} | 累计tokens≈{self._total_tokens_used}"
        return output + meta

    # ── 语义包构建 ──

    def _build_snapshot_package(self) -> str:
        """构建单帧语义包（交互模式核心）。"""
        snapshots = self.current_snapshots
        focus = self.camera.focus
        worldview = self.cfg.worldview

        # 根据 focus 过滤
        if focus != "family":
            # 检查是否是 entity_name
            entity_names = [e.name for e in self.cfg.entities]
            if focus in entity_names:
                idx = entity_names.index(focus)
                snapshots = [snapshots[idx]]
            else:
                # 检查是否是 protocol_name
                filtered = [s for s in snapshots if s["center_protocol"] == focus or s["body_protocol"] == focus]
                if filtered:
                    snapshots = filtered

        # 头部信息
        lines = [
            f"【观测对象】{worldview.name if worldview else '易道世界'} — tick {self.runner.world.tick_count}",
            f"【摄像机配置】{self.camera.status_line()}",
        ]
        if self._flip_in_last_step:
            lines.append("【变化提示】本次推进中检测到卦变事件")
        lines.append("")

        # 成员详细描述
        member_names = [e.name for e in self.cfg.entities]
        for idx, snap in enumerate(snapshots):
            name = member_names[idx] if idx < len(member_names) else snap.get("tick_label", "未知")
            lines.append(self._format_member_for_interactive(snap, name))
            lines.append("")

        # 交互分析（如果多个成员）
        if len(snapshots) >= 2:
            lines.append("【成员间交互】")
            from pipeline.detector import compute_interaction
            for i in range(len(snapshots)):
                for j in range(i + 1, len(snapshots)):
                    inter = compute_interaction(snapshots[i], snapshots[j])
                    name_i = member_names[i] if i < len(member_names) else f"成员{i}"
                    name_j = member_names[j] if j < len(member_names) else f"成员{j}"
                    lines.append(f"  {name_i} ↔ {name_j}: 交互分={inter['score']} | "
                                 f"对卦={'是' if inter['is_opposite'] else '否'} | "
                                 f"同卦={'是' if inter['is_same'] else '否'} | "
                                 f"势能差={inter['pot_diff']}")
            lines.append("")

        # 前情提要（最近 2 幕）
        if self.narrative_history:
            lines.append("【前情提要】（最近叙事摘要）")
            for entry in self.narrative_history[-2:]:
                lines.append(f"  幕{self.narrative_history.index(entry) + 1} tick={entry.tick}: {entry.summary}")
            lines.append("")

        # 世界观注入
        if worldview:
            lines.append(f"【世界观】{worldview.name} — {worldview.description}")
            lines.append("")

        return "\n".join(lines)

    def _format_member_for_interactive(self, snap, member_name) -> str:
        """格式化单个成员的详细描述（支持 variant_lock 覆盖）。"""
        from pipeline.semantic import _translate
        from renderer import get_protocol_library

        worldview = self.cfg.worldview
        body_p = _translate(snap['body_protocol'], worldview)
        usage_p = _translate(get_gua(snap['usage_hex'])['protocol'], worldview)
        rel = _translate(snap['relation_type'], worldview)
        rel_desc = snap['relation_desc']
        if worldview:
            for rt, rt_desc in worldview.relation_templates.items():
                rel_desc = rel_desc.replace(rt, rt_desc)

        # 感官（世界观覆盖）
        sensory = snap['sensory'].copy()
        if worldview and snap['body_protocol'] in worldview.protocol_map:
            w_sensory = worldview.protocol_map[snap['body_protocol']].get('sensory', {})
            if w_sensory.get('visual'): sensory['visual'] = w_sensory['visual'][:3]
            if w_sensory.get('sound'): sensory['sound'] = w_sensory['sound'][:3]
            if w_sensory.get('mood'): sensory['mood'] = w_sensory['mood'][:3]

        # 象法语库
        lib = get_protocol_library(snap['body_protocol'])
        phase_idx = int(snap['center_phase'] * 10) % 5
        def _pick(items, idx):
            return items[idx % len(items)] if items else "—"

        # 变体锁定覆盖
        variant_lines = []
        if self.camera.variant_lock:
            content = self.variant_store.get_variant_content(snap['body_protocol'], self.camera.variant_lock)
            if content:
                variant_lines.append(f"    [锁定变体: {self.camera.variant_lock}] {content}")
            else:
                variant_lines.append(f"    [锁定变体: {self.camera.variant_lock}] 该协议下无此变体，使用默认")
        else:
            # 列出所有可用变体（供 LLM 参考）
            variants = self.variant_store.list_variants(snap['body_protocol'])
            for v in variants[:4]:  # 最多显示 4 个
                variant_lines.append(f"    [{v['source']}] {v['tag']}: {v['content'][:50]}...")

        lit_block = "\n".join(variant_lines) if variant_lines else "    （无变体）"

        return f"""【{member_name}】
卦: {snap['center_gua_name']}({snap['center_gua']}) | 协议: {snap['center_protocol']} | 相位: {snap['center_phase']:.2f} | 势能: {snap['center_pot']:.2f}
体: {snap['body_name']} | {body_p} | 本质: {snap['body_nature']}
用: {snap['usage_name']}({snap['usage_hex']}) | {usage_p}
结构语气: {snap['structural_tone']} | 生命阶段: {snap['life_stage']}
关系: {rel} | {rel_desc}
势能阶段: {snap['pot_label']} ({snap['pot_atmosphere']})
感官: 视-{', '.join(sensory['visual'])} | 听-{', '.join(sensory['sound'])} | 动-{', '.join(sensory.get('motion', []))} | 情-{', '.join(sensory.get('mood', []))}
象法语库: 视-{_pick(lib['visual'], phase_idx)} | 听-{_pick(lib['sound'], phase_idx)} | 触-{_pick(lib['touch'], phase_idx)} | 嗅-{_pick(lib['smell'], phase_idx)} | 味-{_pick(lib['taste'], phase_idx)} | 情-{_pick(lib['mood'], phase_idx)} |  tempo-{_pick(lib['tempo'], phase_idx)} | 形-{_pick(lib['geometry'], phase_idx)}
文学变体:
{lit_block}
"""

    # ── Prompt 构建 ──

    def _build_prompts(self, pkg: str) -> tuple[str, str]:
        """构建 system_prompt 和 user_prompt（含叙事上下文 + 摄像机指令）。"""
        tmpl = prompts.get_prompt(self.camera.style, self.cfg.mode, self.cfg.worldview)
        system = tmpl["system"]
        user_tmpl = tmpl["user"]

        # 注入叙事上下文
        context_block = ""
        if self.narrative_history:
            context_block = "\n## 叙事连续性提示\n这是连续叙事的一部分。请保持以下前情中的人物一致性:\n"
            for entry in self.narrative_history[-2:]:
                context_block += f"- 幕{self.narrative_history.index(entry) + 1} (tick={entry.tick}): {entry.summary}\n"

        # 注入摄像机指令
        camera_block = "\n## 摄像机指令\n"
        if self.camera.distance == "closeup":
            camera_block += "请使用特写镜头描写：聚焦细节、微表情、局部动作、质感。\n"
        elif self.camera.distance == "panorama":
            camera_block += "请使用全景视角描写：整体氛围、环境、群体动态、空间关系。\n"
        else:
            camera_block += "请使用中景描写：人物与环境的关系、互动场景。\n"

        if self.camera.variant_lock:
            camera_block += f"文学视角锁定：请优先使用 '{self.camera.variant_lock}' 视角的语库进行描写。\n"

        if self.camera.focus != "family":
            camera_block += f"当前聚焦：{self.camera.focus}。请以该对象为核心展开叙事。\n"

        # 组装 system prompt
        system = system + context_block + camera_block

        # 组装 user prompt（复用现有模板，但替换 timeline_package）
        # 对于交互模式，我们需要一个简化版的 user prompt
        user = f"""以下是系统当前采集到的观测数据。

{pkg}

请根据以上观测数据，生成一段{'纯粹的白描式文学叙事' if self.camera.style == 'polished' else '有因果有节奏的连续叙事'}。
要求：
1. 这是连续叙事的一部分，请参考前情提要保持人物一致性
2. 正文中禁止出现任何系统术语和小数数据（ polished 模式下）
3. 结尾必须是一个具体的画面或动作
4. 必须包含对应关系标注附录
"""
        return system, user

    # ── 输出保存 ──

    def _save_outputs(self, pkg: str, system: str, user: str, output: str, suffix: str = "") -> str:
        from datetime import datetime
        run_name = datetime.now().strftime("%Y%m%d_%H%M%S") + suffix
        out_dir = os.path.join(self.output_dir, run_name)
        os.makedirs(out_dir, exist_ok=True)

        files = {
            "timeline_package.txt": pkg,
            "system_prompt.txt": system,
            "user_prompt.txt": user,
            "llm_output.txt": output,
        }
        for fname, content in files.items():
            with open(os.path.join(out_dir, fname), "w", encoding="utf-8", errors="replace") as f:
                f.write(content)

        return out_dir

    def _save_no_llm(self, pkg: str, system: str, user: str, error: str = "") -> str:
        out_dir = self._save_outputs(pkg, system, user, f"[LLM 未调用]\n{error}")
        msg = f"\n[LLM 未调用] {'API Key 未设置或调用失败' if not error else error}"
        msg += f"\n语义包 + Prompts 已保存到: {out_dir}/"
        msg += "\n提示: 你可以复制 system_prompt.txt 和 user_prompt.txt 到任意 LLM 平台手动调用"
        return msg

    # ── 状态管理 ──

    def reset(self):
        """重置世界（保留配置、摄像机、变体）。"""
        self.runner = WorldRunner(self.cfg.world, self.cfg.entities)
        self.narrative_history.clear()
        self.last_explain_tick = -1
        self.current_snapshots.clear()
        self._last_pkg = None
        self._last_system = None
        self._last_user = None
        self._last_output = None
        self._flip_in_last_step = False
        self._total_tokens_used = 0

    def status(self) -> str:
        """返回当前世界状态摘要。"""
        lines = [
            f"tick: {self.runner.world.tick_count}",
            f"摄像机: {self.camera.status_line()}",
            f"叙事幕数: {len(self.narrative_history)}",
            f"累计 tokens: {self._total_tokens_used}",
            "",
            "【实体状态】",
        ]
        for idx, t in enumerate(self.runner.trackers):
            snap = self.current_snapshots[idx] if idx < len(self.current_snapshots) else None
            if snap:
                lines.append(f"  {t.entity_id}: {snap['center_gua_name']} | {snap['body_protocol']} | "
                             f"势={snap['center_pot']:.2f} | 相={snap['center_phase']:.2f}")
            else:
                lines.append(f"  {t.entity_id}: 尚无 snapshot")
        return "\n".join(lines)

    def save_session(self, name: str, state_dir: str = "./states") -> str:
        """保存完整会话状态（世界 + 叙事历史 + 摄像机 + 变体）。"""
        # 保存世界状态
        state_manager.save_state(self.runner.world, self.runner.trackers, self.runner.cam, state_dir, name)
        # 保存会话级数据
        session_path = os.path.join(state_dir, name, "session.json")
        session_data = {
            "narrative_history": [
                {"tick": e.tick, "focus": e.focus, "variant_lock": e.variant_lock,
                 "summary": e.summary, "output_path": e.output_path}
                for e in self.narrative_history
            ],
            "camera_config": self.camera.to_dict(),
            "session_variants": self.variant_store._session,
            "last_explain_tick": self.last_explain_tick,
            "total_tokens_used": self._total_tokens_used,
        }
        with open(session_path, "w", encoding="utf-8") as f:
            import json
            json.dump(session_data, f, ensure_ascii=False, indent=2)
        return os.path.join(state_dir, name)

    def load_session(self, name: str, state_dir: str = "./states") -> bool:
        """加载完整会话状态。"""
        session_path = os.path.join(state_dir, name, "session.json")
        if not os.path.isfile(session_path):
            return False
        with open(session_path, "r", encoding="utf-8") as f:
            import json
            session_data = json.load(f)

        # 加载世界状态
        self.runner.trackers = state_manager.load_state(self.runner.world, self.runner.cam, state_dir, name)
        self.runner.flip_events = [[] for _ in self.runner.trackers]
        self.runner.all_snapshots = [[] for _ in self.runner.trackers]

        # 恢复会话数据
        self.narrative_history = [
            NarrativeEntry(e["tick"], e["focus"], e.get("variant_lock"), e["summary"], e["output_path"])
            for e in session_data.get("narrative_history", [])
        ]
        self.camera = CameraConfig.from_dict(session_data.get("camera_config", {}))
        self.variant_store._session = session_data.get("session_variants", {})
        self.last_explain_tick = session_data.get("last_explain_tick", -1)
        self._total_tokens_used = session_data.get("total_tokens_used", 0)
        return True
