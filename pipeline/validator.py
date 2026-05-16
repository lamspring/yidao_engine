# -*- coding: utf-8 -*-
"""输出验证器"""
import re

# 匹配附录标题：# / ## / ### + 对应关系/附录/映射标注/质量自检/叙事质量自检
_APPENDIX_RE = re.compile(r"^(#{1,3})\s*(对应关系|附录|映射标注|质量自检|叙事质量自检)", re.MULTILINE)


def _extract_narrative(output: str) -> str:
    """从完整输出中提取正文部分（附录之前）。"""
    match = _APPENDIX_RE.search(output)
    if match:
        return output[:match.start()]
    return output


def _extract_annotation(output: str) -> str:
    """从完整输出中提取附录部分。"""
    match = _APPENDIX_RE.search(output)
    if match:
        return output[match.start():]
    return ""


def validate_raw(output: str, story_data: dict) -> list[tuple[str, bool]]:
    """验证 raw 风格输出（阈值收紧：单关键词→多关键词最低命中数）"""
    checks = []
    narrative = _extract_narrative(output)
    # 叙事弧线：各项至少命中 2 个关键词才算通过
    time_words = ["起初", "后来", "随后", "终于", "之前", "之后", "那一刻"]
    checks.append(("有明确时间流逝感（≥2词）", sum(1 for w in time_words if w in narrative) >= 2))
    cause_words = ["因此", "所以", "因为", "于是", "导致", "源于", "终于"]
    checks.append(("有因果逻辑链（≥2词）", sum(1 for w in cause_words if w in narrative) >= 2))
    foreshadow_words = ["伏笔", "潜藏", "压抑", "积蓄", "酝酿", "暗流", "沉默", "潜伏"]
    checks.append(("有伏笔铺垫（≥2词）", sum(1 for w in foreshadow_words if w in narrative) >= 2))
    climax_words = ["爆发", "崩解", "瓦解", "撕裂", "裂变", "点燃", "引爆", "那一刻"]
    checks.append(("有爆发/高潮（≥2词）", sum(1 for w in climax_words if w in narrative) >= 2))
    aftermath_words = ["后果", "余波", "残骸", "废墟", "新生", "之后", "从此", "留下"]
    checks.append(("有后果/余波（≥2词）", sum(1 for w in aftermath_words if w in narrative) >= 2))
    ritual_words = ["宿命", "轰鸣", "自决", "强制", "降临", "产道", "不可逆转", "旧死新生"]
    checks.append(("卦变有仪式感（≥2词）", sum(1 for w in ritual_words if w in narrative) >= 2))
    checks.append(("两极并存（≥2词）", sum(1 for w in ["光明", "黑暗", "荣耀", "诅咒", "辉煌", "腐朽", "温暖", "冰冷"] if w in narrative) >= 2))
    checks.append(("有对应表", "对应关系" in output or "|" in output))
    checks.append(("有质量自检", "自检" in output or "因果链" in output))
    sense_words = ["光", "暗", "声", "响", "静", "风", "火", "冷", "热", "味道", "颤抖", "震动"]
    checks.append(("有感官细节（≥3词）", sum(1 for w in sense_words if w in narrative) >= 3))
    return checks


def validate_polished(output: str, narrative_part: str, member_names: list[str]) -> list[tuple[str, bool]]:
    """验证 polished 风格输出（Route-C v2）"""
    checks = []
    # 正文零数据引用（narrative_part 已由调用方传入，但这里再保险一次）
    narrative = _extract_narrative(output)
    forbidden = ["相位", "势能", "交互分", "同卦共鸣", "先天对卦", "体协议", "用协议", "卦象"]
    for term in forbidden:
        checks.append((f"正文中无'{term}'", term not in narrative))
    checks.append(("正文中无小数数据", not bool(re.search(r"\d+\.\d+", narrative))))
    checks.append(("有感官细节", sum(1 for w in ["光", "暗", "声", "响", "静", "风", "火", "冷", "热", "味道", "颤抖", "震动", "笑", "泪"] if w in narrative) >= 3))
    # 对话检查：排除附录区域后，正文内是否有 "XX说" 或引号对话
    has_dialogue = bool(re.search(r'[。\s]"[^"]{3,50}"[。，\s]', narrative)) or \
                   bool(re.search(r'[。\s][""""][^""""]{3,50}[""""][。，\s]', narrative))
    checks.append(("有对话描写", has_dialogue))
    checks.append(("有动作描写（≥3种）", sum(1 for w in ["撕", "画", "写", "走", "站", "坐", "推", "拉", "锁", "开", "放", "拿", "端", "放", "递", "握"] if w in narrative) >= 3))
    checks.append(("至少有3个角色名出现", sum(1 for name in member_names if name in narrative) >= 3))
    checks.append(("有家庭/互动氛围", any(w in output for w in ["父亲", "母亲", "家", "家里", "家人", "争吵", "拥抱", "沉默", "对视"])))
    checks.append(("有对应关系标注（附录）", "对应关系" in output or "对应表" in output))
    checks.append(("有质量自检", "自检" in output or "因果链" in output))
    # Route-C v2：检查映射标注中是否有系统概念锚定
    annotation = _extract_annotation(output)
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
