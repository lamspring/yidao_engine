# -*- coding: utf-8 -*-
"""
世界观语库生成工具 —— 为世界观中的每个协议生成文学语库变体

用法:
    python tools/generate_worldview_lexicon.py --worldview xiuxian --variants 5
    python tools/generate_worldview_lexicon.py --worldview cthulhu --provider openai --variants 3 --dry-run
"""

import sys
import os
import json
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pipeline.config import LLMConfig
from pipeline.llm_client import LLMClient
from renderer import PROTOCOL_LIBRARY


SYSTEM_PROMPT = """你是一位象法文学家，专为特定世界观生成感官文学描写。

规则：
1. 每次为同一个概念生成多段不同的描写，段与段之间要有明显差异
2. 只写感官（视觉、听觉、触觉、气味、情绪、节奏），禁止系统术语
3. 描写必须让系统概念通过纯文学手段可被感知
4. 世界观是"调色板"，不是唯一滤镜——同一概念可以有不同的文学面貌
5. 追求多样性：有的段偏视觉，有的偏听觉，有的偏情绪，有的偏节奏
6. 每段 40-80 字

输出格式：只输出纯文学描写段落，用 --- 分隔，不要任何说明文字。"""


def build_user_prompt(protocol, core_def, worldview_name, mapped_name, mapped_desc, variants_count):
    return f"""请为以下概念生成 {variants_count} 段不同的感官文学描写：

系统概念：{protocol}（{core_def}）
世界观名称：{worldview_name}
世界观映射：{mapped_name} — {mapped_desc}

要求：
- {variants_count} 段不同风格的描写
- 每段 40-80 字
- 只包含感官和情绪，禁止系统术语
- 贴合世界观但不堆砌词汇
- 段与段之间差异明显

请直接输出 {variants_count} 段，用 --- 分隔："""


def parse_variants(text: str, expected_count: int) -> list[str]:
    """解析 LLM 输出，提取变体段落"""
    # 尝试用 --- 分隔
    parts = [p.strip() for p in text.split("---") if p.strip()]
    if len(parts) >= expected_count:
        return parts[:expected_count]
    # 尝试用空行分隔
    parts = [p.strip() for p in text.split("\n\n") if p.strip() and len(p.strip()) >= 20]
    if len(parts) >= expected_count:
        return parts[:expected_count]
    # 尝试用换行分隔（每段一行）
    parts = [p.strip() for p in text.split("\n") if p.strip() and len(p.strip()) >= 20]
    return parts[:expected_count] if len(parts) >= expected_count else parts


def generate_for_protocol(protocol, entry, worldview, llm_client, variants_count):
    """为单个协议生成语库变体"""
    core_def = PROTOCOL_LIBRARY.get(protocol, {}).get("core", protocol)
    mapped_name = entry.get("name", protocol)
    mapped_desc = entry.get("description", "")
    worldview_name = worldview.get("name", "通用世界观")

    user_prompt = build_user_prompt(
        protocol, core_def, worldview_name, mapped_name, mapped_desc, variants_count
    )

    print(f"  生成 {protocol}（{mapped_name}）...")
    try:
        output, usage = llm_client.call(SYSTEM_PROMPT, user_prompt)
        variants = parse_variants(output, variants_count)
        print(f"    ✓ 生成 {len(variants)} 段 | 输入:{usage.get('prompt_tokens','?')} 输出:{usage.get('completion_tokens','?')}")
        return variants
    except Exception as e:
        print(f"    ✗ 失败: {e}")
        return []


def main():
    p = argparse.ArgumentParser(description="为世界观生成文学语库变体")
    p.add_argument("--worldview", required=True, help="世界观配置名")
    p.add_argument("--provider", default="deepseek", help="LLM提供商")
    p.add_argument("--variants", type=int, default=5, help="每个协议生成几个变体")
    p.add_argument("--config-dir", default="./configs", help="配置文件目录")
    p.add_argument("--dry-run", action="store_true", help="只打印，不写入文件")
    args = p.parse_args()

    # 加载世界观
    worldview_path = os.path.join(args.config_dir, "worldviews", f"{args.worldview}.json")
    if not os.path.exists(worldview_path):
        print(f"[错误] 世界观不存在: {worldview_path}")
        sys.exit(1)

    with open(worldview_path, "r", encoding="utf-8") as f:
        worldview = json.load(f)

    protocols = worldview.get("protocol_map", {})
    if not protocols:
        print("[错误] 世界观中没有 protocol_map")
        sys.exit(1)

    print(f"[配置] 世界观: {worldview.get('name', args.worldview)}")
    print(f"[配置] 提供商: {args.provider} | 每个协议生成: {args.variants} 段")
    print(f"[配置] 共 {len(protocols)} 个协议")
    print()

    # 初始化 LLM 客户端
    if not args.dry_run:
        try:
            llm_cfg = LLMConfig.from_provider(args.provider, args.config_dir)
            llm_client = LLMClient(llm_cfg)
            print(f"[LLM] 已连接: {llm_cfg.model}")
        except Exception as e:
            print(f"[错误] LLM 连接失败: {e}")
            print("[提示] 你可以：")
            print("  1. 设置环境变量后重试")
            print("  2. 使用 --dry-run 查看生成提示（不调用 LLM）")
            sys.exit(1)
    else:
        llm_client = None
        print("[DRY-RUN] 不调用 LLM，只展示生成提示")

    print()
    print("=" * 60)

    # 为每个协议生成
    for protocol, entry in protocols.items():
        if args.dry_run:
            # 只打印 prompt
            core_def = PROTOCOL_LIBRARY.get(protocol, {}).get("core", protocol)
            mapped_name = entry.get("name", protocol)
            mapped_desc = entry.get("description", "")
            worldview_name = worldview.get("name", args.worldview)
            prompt = build_user_prompt(protocol, core_def, worldview_name, mapped_name, mapped_desc, args.variants)
            print(f"\n【{protocol} / {mapped_name}】")
            print(prompt)
            print("-" * 40)
        else:
            # 调用 LLM 生成
            variants = generate_for_protocol(protocol, entry, worldview, llm_client, args.variants)
            if variants:
                entry["lexicon_variants"] = variants
                print(f"    示例: {variants[0][:40]}...")

    if args.dry_run:
        print("\n[DRY-RUN 完成] 使用 --dry-run 查看生成提示，去掉 --dry-run 实际生成")
        return

    # 保存
    print()
    print("=" * 60)
    if args.dry_run:
        return

    with open(worldview_path, "w", encoding="utf-8") as f:
        json.dump(worldview, f, ensure_ascii=False, indent=2)

    print(f"[完成] 已保存到: {worldview_path}")
    print(f"[提示] 建议人工审核生成的语库变体，确保质量后再使用")


if __name__ == "__main__":
    main()
