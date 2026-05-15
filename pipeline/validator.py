# -*- coding: utf-8 -*-
"""输出验证器"""
import re


def validate_raw(output: str, story_data: dict) -> list[tuple[str, bool]]:
    """验证 raw 风格输出"""
    checks = []
    checks.append(("有明确时间流逝感", any(w in output for w in ["起初", "后来", "随后", "终于", "之前", "之后", "那一刻"])))
    checks.append(("有因果逻辑链", any(w in output for w in ["因此", "所以", "因为", "于是", "导致", "源于", "终于"])))
    checks.append(("有伏笔铺垫", any(w in output for w in ["伏笔", "潜藏", "压抑", "积蓄", "酝酿", "暗流", "沉默", "潜伏"])))
    checks.append(("有爆发/高潮", any(w in output for w in ["爆发", "崩解", "瓦解", "撕裂", "裂变", "点燃", "引爆", "那一刻"])))
    checks.append(("有后果/余波", any(w in output for w in ["后果", "余波", "残骸", "废墟", "新生", "之后", "从此", "留下"])))
    checks.append(("卦变有仪式感", any(w in output for w in ["宿命", "轰鸣", "自决", "强制", "降临", "产道", "不可逆转", "旧死新生"])))
    checks.append(("两极并存", sum(1 for w in ["光明", "黑暗", "荣耀", "诅咒", "辉煌", "腐朽", "温暖", "冰冷"] if w in output) >= 2))
    checks.append(("有对应表", "对应关系" in output or "|" in output))
    checks.append(("有质量自检", "自检" in output or "因果链" in output))
    checks.append(("有感官细节", any(w in output for w in ["光", "暗", "声", "响", "静", "风", "火", "冷", "热", "味道", "颤抖", "震动"])))
    return checks


def validate_polished(output: str, narrative_part: str, member_names: list[str]) -> list[tuple[str, bool]]:
    """验证 polished 风格输出（Route-C v2）"""
    checks = []
    # 正文零数据引用
    forbidden = ["相位", "势能", "交互分", "同卦共鸣", "先天对卦", "体协议", "用协议", "卦象"]
    for term in forbidden:
        checks.append((f"正文中无'{term}'", term not in narrative_part))
    checks.append(("正文中无小数数据", not bool(re.search(r"\d+\.\d+", narrative_part))))
    checks.append(("有感官细节", sum(1 for w in ["光", "暗", "声", "响", "静", "风", "火", "冷", "热", "味道", "颤抖", "震动", "笑", "泪"] if w in narrative_part) >= 3))
    checks.append(("有对话描写", "：" in narrative_part or '"' in narrative_part or '"' in narrative_part))
    checks.append(("有动作描写", any(w in narrative_part for w in ["撕", "画", "写", "走", "站", "坐", "推", "拉", "锁", "开", "放", "拿"])))
    checks.append(("至少有3个角色名出现", sum(1 for name in member_names if name in narrative_part) >= 3))
    checks.append(("有家庭/互动氛围", any(w in output for w in ["父亲", "母亲", "家", "家里", "家人", "争吵", "拥抱", "沉默", "对视"])))
    checks.append(("有对应关系标注（附录）", "对应关系" in output or "对应表" in output))
    checks.append(("有质量自检", "自检" in output or "因果链" in output))
    # Route-C v2：检查映射标注中是否有系统概念锚定
    annotation = ""
    for marker in ["### 对应关系", "### 二、对应关系", "### 附录", "### 映射标注"]:
        if marker in output:
            annotation = output.split(marker)[-1]
            break
    checks.append(("映射标注中有系统概念锚定", "系统概念" in annotation or "【" in annotation))
    checks.append(("映射标注中有LLM文学映射", "文学映射" in annotation or "LLM" in annotation))
    return checks


def print_results(checks: list[tuple[str, bool]]) -> bool:
    all_pass = True
    for desc, ok in checks:
        status = "PASS" if ok else "FAIL"
        if not ok:
            all_pass = False
        print(f"  [{status}] {desc}")
    print()
    if all_pass:
        print(">>> 验证通过")
    else:
        print(">>> 部分验证未通过")
    return all_pass
