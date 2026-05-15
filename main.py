# -*- coding: utf-8 -*-
"""
易道引擎统一工作流入口
用法:
  # 全新运行 + 保存状态
  python main.py --mode family --save my_world

  # 加载已有世界继续运行
  python main.py --load my_world --ticks 500 --save my_world_v2

  # 列出所有保存的状态
  python main.py --list-states

  # 修仙世界观 + DeepSeek + 保存
  python main.py --worldview xiuxian --provider deepseek --save xiuxian_world
"""

import sys
import io
import os
import argparse
import json
from datetime import datetime

if sys.platform == "win32" and hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pipeline.config import PipelineConfig, LLMConfig, WorldViewConfig
from pipeline.world_runner import WorldRunner
from pipeline import detector
from pipeline import semantic
from pipeline import prompts
from pipeline.llm_client import LLMClient
from pipeline import validator
from pipeline import state_manager


def parse_args():
    p = argparse.ArgumentParser(description="易道引擎统一工作流")
    # 运行模式
    p.add_argument("--mode", choices=["single", "dual", "family"], default="family", help="运行模式")
    p.add_argument("--style", choices=["raw", "polished"], default="polished", help="叙事风格")
    p.add_argument("--ticks", type=int, default=1500, help="本次运行新增 tick 数（增量模式）或总 tick 数（全新模式）")
    p.add_argument("--interval", type=int, default=150, help="快照采样间隔")
    # LLM & 世界观
    p.add_argument("--provider", default="deepseek", help="LLM提供商 (deepseek/openai/claude/mimo/local)")
    p.add_argument("--worldview", default=None, help="世界观配置名")
    p.add_argument("--config-dir", default="./configs", help="配置文件目录")
    p.add_argument("--no-llm", action="store_true", help="只运行模拟，不调用LLM")
    # 状态管理
    p.add_argument("--save", default=None, help="运行结束后保存状态到此名称")
    p.add_argument("--load", default=None, help="加载此前保存的状态继续运行")
    p.add_argument("--state-dir", default="./states", help="状态保存目录")
    p.add_argument("--list-states", action="store_true", help="列出所有已保存的状态")
    # 输出
    p.add_argument("--output", default="./outputs", help="叙事输出目录")
    return p.parse_args()


def setup_config(args) -> PipelineConfig:
    if args.mode == "single":
        cfg = PipelineConfig.default_single()
    elif args.mode == "dual":
        cfg = PipelineConfig.default_dual()
    else:
        cfg = PipelineConfig.default_family()

    cfg.style = args.style
    cfg.world.ticks = args.ticks
    cfg.world.snapshot_interval = args.interval
    cfg.output_dir = args.output
    cfg.run_name = datetime.now().strftime("%Y%m%d_%H%M%S")

    # 加载LLM配置
    try:
        try:
            cfg.llm = LLMConfig.from_provider(args.provider, args.config_dir)
        except ValueError as e:
            print(f"[错误] {e}")
            print("[提示] 你可以：")
            print("  1. 设置对应的环境变量（如 DEEPSEEK_API_KEY）后重试")
            print("  2. 换用其他 provider：--provider openai / --provider claude / --provider local")
            print("  3. 跳过 LLM 调用，只运行模拟：--no-llm")
            import sys
            sys.exit(1)
        print(f"[配置] LLM提供商: {args.provider} | 模型: {cfg.llm.model}")
    except Exception as e:
        print(f"[警告] 加载LLM配置失败: {e}，使用默认配置")
        cfg.llm = LLMConfig()

    # 加载世界观配置
    if args.worldview:
        try:
            cfg.worldview = WorldViewConfig.from_file(args.worldview, args.config_dir)
            print(f"[配置] 世界观: {cfg.worldview.name} | {cfg.worldview.description}")
        except Exception as e:
            print(f"[警告] 加载世界观配置失败: {e}，使用通用世界观")
            cfg.worldview = None

    return cfg


def run_simulation(runner, cfg: PipelineConfig, is_resuming: bool = False):
    print("=" * 60)
    start_tick = runner.world.tick_count
    target_tick = start_tick + cfg.world.ticks
    print(f"【易道引擎】模式={cfg.mode} 风格={cfg.style}")
    if is_resuming:
        print(f"           增量运行: tick {start_tick} -> {target_tick} (+{cfg.world.ticks})")
    else:
        print(f"           全新运行: tick 0 -> {target_tick}")
    if cfg.worldview:
        print(f"           世界观={cfg.worldview.name} 提供商={cfg.llm.model}")
    print("=" * 60)

    print(f"\n[1/5] 运行模拟 {'(续)' if is_resuming else ''}...")
    for i in range(cfg.world.ticks):
        runner.world.tick()
        for idx, t in enumerate(runner.trackers):
            t._update()
            if len(t.hex_history) >= 2:
                prev, curr = t.hex_history[-2], t.hex_history[-1]
                if prev != curr:
                    runner.flip_events[idx].append({
                        "tick": runner.world.tick_count,
                        "pre_hex": prev, "post_hex": curr,
                        "pre_name": __import__('codex').get_gua(prev)["name"],
                        "post_name": __import__('codex').get_gua(curr)["name"],
                    })
        if (i + 1) % runner.interval == 0:
            for idx, t in enumerate(runner.trackers):
                runner.all_snapshots[idx].append(
                    __import__('pipeline.world_runner', fromlist=['capture_compact']).capture_compact(
                        runner.world, runner.cam, t, runner.analyst, f"{t.entity_id}_T{runner.world.tick_count}"
                    )
                )
        if (i + 1) % 500 == 0:
            total_flips = sum(len(f) for f in runner.flip_events)
            print(f"  ...{runner.world.tick_count} 息 | 总卦变 {total_flips} 次")

    total_flips = sum(len(f) for f in runner.flip_events)
    print(f"  模拟完成 | 当前 tick={runner.world.tick_count} | 总卦变={total_flips}")
    return runner


def detect_event(runner, cfg: PipelineConfig):
    print("\n[2/5] 检测事件...")
    if cfg.mode == "single":
        event = detector.detect_flip_event(runner.flip_events[0], runner.all_snapshots[0])
        print(f"  选定卦变: tick {event['tick']} | {event['pre_name']} -> {event['post_name']}")
        return event
    elif cfg.mode == "dual":
        event = detector.detect_cross_event(runner.flip_events, runner.all_snapshots)
        print(f"  选定交叉: tick {event['tick']} | 评分={event['score']:.1f} | 卦变={event['flip_count']}人")
        return event
    else:
        event = detector.detect_family_event(runner.flip_events, runner.all_snapshots)
        print(f"  选定家庭事件: tick {event['tick']} | 评分={event['score']:.1f} | 卦变={event['flip_count']}人")
        return event


def build_slices(runner, event, cfg: PipelineConfig):
    print("\n[3/5] 提取时间切片...")
    cross_tick = event["tick"]

    def _nearest(snapshots, target):
        return min(snapshots, key=lambda s: abs(s["tick"] - target))

    if cfg.mode == "single":
        pkg = semantic.build_single_package(event, event, cfg.entities[0].name, cfg.worldview)
        return pkg

    elif cfg.mode == "dual":
        slice_configs = [
            ("T-2 各自稳态", cross_tick - 400),
            ("T-1 临近感知", cross_tick - 150),
            ("T0 交叉时刻", cross_tick),
            ("T+1 新态互动", cross_tick + 200),
        ]
        family_slices = []
        for label, target in slice_configs:
            members = [_nearest(runner.all_snapshots[i], target) for i in range(2)]
            family_slices.append((label, target, members))
        pkg = semantic.build_family_package(event, cfg.entities, family_slices, cfg.worldview)
        return pkg

    else:
        slice_configs = [
            ("T-2 日常稳态", cross_tick - 300),
            ("T-1 暗流涌动", cross_tick - 150),
            ("T0  家庭事件", cross_tick),
            ("T+1 余波震荡", cross_tick + 150),
            ("T+2 新秩序",   cross_tick + 300),
        ]
        family_slices = []
        for label, target in slice_configs:
            members = [_nearest(runner.all_snapshots[i], target) for i in range(len(cfg.entities))]
            family_slices.append((label, target, members))
        pkg = semantic.build_family_package(event, cfg.entities, family_slices, cfg.worldview)
        return pkg


def call_llm(pkg: str, event, cfg: PipelineConfig):
    print("\n[4/5] 调用 LLM...")
    tmpl = prompts.get_prompt(cfg.style, cfg.mode, cfg.worldview)
    system = tmpl["system"]

    if cfg.mode == "single":
        user = tmpl["user"].format(
            tick=event["tick"], pre_name=event["pre_name"], post_name=event["post_name"],
            timeline_package=pkg
        )
    elif cfg.mode == "dual":
        flip_info = f"tick {event['tick']} 发生交叉事件。"
        inter = event["snaps"][0]["center_gua_name"] + " vs " + event["snaps"][1]["center_gua_name"]
        user = tmpl["user"].format(
            flip_info=flip_info, interaction_desc=inter, timeline_package=pkg
        )
    else:
        flip_detail = f"本次家庭事件中，共有 {event['flip_count']} 位成员经历了卦变。" if event.get("flip_count", 0) > 0 else ""
        appendix_lines = []
        if "snaps" in event:
            for i in range(len(cfg.entities)):
                snap = event["snaps"][i]
                appendix_lines.append(f"{cfg.entities[i].name}: {snap['body_nature']}")
                if cfg.worldview:
                    w_name = cfg.worldview.translate_protocol(snap['body_protocol'], 'name')
                    appendix_lines.append(f"  -> 世界观映射: {w_name}")
        appendix = "\n".join(appendix_lines)
        user = tmpl["user"].format(flip_detail=flip_detail, timeline_package=pkg, appendix=appendix)

    client = LLMClient(cfg.llm)
    output, usage = client.call(system, user)
    print(f"  API 成功 | 输入:{usage.get('prompt_tokens','?')} | 输出:{usage.get('completion_tokens','?')}")
    return output, system, user


def validate(output: str, cfg: PipelineConfig):
    print("\n[5/5] 验证输出...")
    names = [e.name for e in cfg.entities]
    if cfg.style == "polished":
        narrative = output.split("### 对应关系")[0] if "### 对应关系" in output else output
        checks = validator.validate_polished(output, narrative, names)
    else:
        checks = validator.validate_raw(output, {})
    return validator.print_results(checks)


def save_outputs(cfg: PipelineConfig, pkg: str, system: str, user: str, output: str):
    out_dir = os.path.join(cfg.output_dir, cfg.run_name)
    _ensure_dir(out_dir)

    files = {
        "timeline_package.txt": pkg,
        "system_prompt.txt": system,
        "user_prompt.txt": user,
        "llm_output.txt": output,
    }
    for fname, content in files.items():
        with open(os.path.join(out_dir, fname), "w", encoding="utf-8") as f:
            f.write(content)

    meta = {
        "run_name": cfg.run_name,
        "mode": cfg.mode,
        "style": cfg.style,
        "ticks": cfg.world.ticks,
        "entity_count": len(cfg.entities),
        "provider": cfg.llm.model,
        "worldview": cfg.worldview.name if cfg.worldview else None,
    }
    with open(os.path.join(out_dir, "meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    print(f"\n  叙事输出已保存到: {out_dir}")
    return out_dir


def _ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)


def main():
    args = parse_args()

    # 列出状态
    if args.list_states:
        states = state_manager.list_states(args.state_dir)
        print("=" * 60)
        print("【已保存的世界状态】")
        print("=" * 60)
        if not states:
            print("  无")
        for name, meta in states:
            print(f"  {name}: tick={meta.get('tick_count', '?')} | H={meta.get('H')}x{meta.get('W')}")
        return

    cfg = setup_config(args)
    is_resuming = args.load is not None

    # 初始化或加载世界
    if is_resuming:
        print(f"\n[加载] 从状态 '{args.load}' 恢复...")
        runner = WorldRunner(cfg.world, cfg.entities)
        runner.trackers = state_manager.load_state(runner.world, runner.cam, args.state_dir, args.load)
        # 重建 flip_events 和 all_snapshots 结构
        runner.flip_events = [[] for _ in runner.trackers]
        runner.all_snapshots = [[] for _ in runner.trackers]
    else:
        runner = WorldRunner(cfg.world, cfg.entities)

    # 1. 模拟
    runner = run_simulation(runner, cfg, is_resuming)

    # 2. 检测
    event = detect_event(runner, cfg)

    # 3. 切片 + 语义包
    pkg = build_slices(runner, event, cfg)

    # 保存世界状态（如果指定了 --save）
    if args.save:
        state_manager.save_state(runner.world, runner.trackers, runner.cam, args.state_dir, args.save)

    if args.no_llm:
        print("\n[跳过LLM] --no-llm 模式")
        out_dir = os.path.join(cfg.output_dir, cfg.run_name)
        _ensure_dir(out_dir)
        with open(os.path.join(out_dir, "timeline_package.txt"), "w", encoding="utf-8") as f:
            f.write(pkg)
        print(f"  语义包已保存到: {out_dir}/timeline_package.txt")
        return

    # 4. LLM
    try:
        output, system, user = call_llm(pkg, event, cfg)
    except Exception as e:
        print(f"  LLM 调用失败: {e}")
        print("  保存语义包到本地，等网络恢复后可手动调用...")
        out_dir = os.path.join(cfg.output_dir, cfg.run_name)
        _ensure_dir(out_dir)
        with open(os.path.join(out_dir, "timeline_package.txt"), "w", encoding="utf-8") as f:
            f.write(pkg)
        print(f"  语义包已保存到: {out_dir}/timeline_package.txt")
        return

    # 5. 验证
    validate(output, cfg)

    # 6. 保存叙事
    out_dir = save_outputs(cfg, pkg, system, user, output)

    # 7. 预览
    print("\n" + "=" * 60)
    print("【LLM 输出预览】")
    print("=" * 60)
    preview_len = 2000 if cfg.style == "polished" else 1500
    print(output[:preview_len])
    print("\n... [完整内容见 llm_output.txt]")


if __name__ == "__main__":
    main()
