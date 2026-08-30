# -*- coding: utf-8 -*-
"""
tools/split_spirit.py —— M2 组件化拆分的一次性执行脚本。

铁律：行为不变。本脚本只做"文本搬运"，不改任何一行方法体：
  1. 解析 yidao_core/spirit.py，按方法边界（`    def`）切块；
  2. 头部（文档/导入/常量/辅助函数/Memory）→ spirit/base.py（自动生成 __all__）；
  3. 方法块按"九系统 + 核心"分族 → 各为一个 Mixin；
  4. spirit/__init__.py 组装 Spirit(*Mixins) 并全量再导出——对外接口零变化。

拆分正确性由外部裁判：45 项不变量测试 + 与拆分前鱼出口输出逐字节对照。
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "yidao_core" / "spirit.py"
PKG = ROOT / "yidao_core" / "spirit"

SYSTEMS = {
    "sense":     ["_感知半径", "_切比", "_感知", "_生疑", "_同悼", "_感知到", "_观察"],
    "subsist":   ["_区域键", "_区域有记忆", "_觅食", "_袋中食", "_吃", "_进食",
                  "_渔猎", "_狩猎", "_找水", "_灌罐", "_汲井", "_饮水", "_探索",
                  "_游荡", "_采集资源"],
    "learning":  ["_涨熟练", "_熟练", "_积学", "_摸器悟法"],
    "social":    ["_社交", "_对质", "_传闲话", "_人情往来"],
    "conflict":  ["_邻居们", "_身边威胁", "_逃离", "_尝试抢夺", "_旁观者记",
                  "_追击报复", "_尝试庇护", "_涌现", "_战斗"],
    "build":     ["_淋雨", "_尝试求庇", "_尝试夺屋", "_建材数", "_取建材",
                  "_营建", "_选址", "_井址", "_凿井", "_农事", "_有器",
                  "_最佳武器", "_数料", "_取料", "_磨损", "_百工", "_备料",
                  "_畜牧事"],
    "kinship":   ["_婚配", "_诞育", "_幼年", "_成年"],
    "migrate":   ["_察荒", "_起迁", "_弃产", "_行迁"],
    "settle":    ["_受冻", "_钻木", "_赴火", "_烹制", "_锻炼", "_栖身所",
                  "_檐下", "_安眠", "_祈雨聚"],
    "core":      ["__init__", "decide", "remember", "settle_day",
                  "remembers_robbery_by", "relation", "声望", "want",
                  "drop_goal", "_漂移", "_走向", "_移动到", "_耗阳", "_泵阳",
                  "_得物", "_转化", "_死否", "_盖棺", "_寿终", "_善后",
                  "_心情漂移", "关系"],
}

CN = {"sense": "感知", "subsist": "生计", "learning": "学习", "social": "社交",
      "conflict": "争斗", "build": "营建", "kinship": "婚育", "migrate": "徙居",
      "settle": "安身", "core": "核心"}
MIXIN = {k: f"{v}Mixin" for k, v in CN.items()}


def main():
    lines = SRC.read_text(encoding="utf-8").split("\n")
    cls_i = next(i for i, ln in enumerate(lines) if ln.startswith("class Spirit:"))
    header = "\n".join(lines[:cls_i]).rstrip() + "\n"
    body = lines[cls_i + 1:]

    # 切块：方法始于 `    def `；其间注释横幅随下一块走（横幅描述的是后来者）
    blocks = []          # [(name, [行])]
    cur, cur_name = [], None
    preamble = []
    for ln in body:
        m = re.match(r"^    def ([\w一-鿿]+)", ln)
        if m:
            if cur_name is None:
                preamble = cur
            else:
                blocks.append((cur_name, cur))
            cur, cur_name = [ln], m.group(1)
        else:
            cur.append(ln)
    if cur_name is not None:
        blocks.append((cur_name, cur))

    # 横幅迁徙：块尾的空行与"    # ──"横幅属于下一块
    for i in range(len(blocks) - 1):
        name, ls = blocks[i]
        j = len(ls)
        while j > 0 and (not ls[j - 1].strip() or ls[j - 1].lstrip().startswith("#")):
            j -= 1
        tail = ls[j:]
        if any(l.lstrip().startswith("# ──") for l in tail):
            blocks[i] = (name, ls[:j])
            blocks[i + 1] = (blocks[i + 1][0], tail + blocks[i + 1][1])

    by_name = {}
    for name, ls in blocks:
        assert name not in by_name, f"方法重名：{name}"
        by_name[name] = ls

    mapped = [m for ms in SYSTEMS.values() for m in ms]
    assert len(mapped) == len(set(mapped)), "方法族内有重复"
    assert not [m for m in mapped if m not in by_name], \
        f"方法族中查无此法：{[m for m in mapped if m not in by_name]}"
    assert not [n for n in by_name if n not in mapped], \
        f"方法族遗漏了：{[n for n in by_name if n not in mapped]}"

    # base.py：头部 + 自动 __all__（含下划线名与再导出的世界名，mixin 全靠 * 导入）
    # 用 AST 精确收集顶层公开名（赋值/函数/类/导入），正则会被文档串里的"="骗
    import ast as _ast
    tree = _ast.parse(header)
    names = set()
    for node in tree.body:
        if isinstance(node, _ast.Assign):
            names |= {t.id for t in node.targets if isinstance(t, _ast.Name)}
        elif isinstance(node, _ast.AnnAssign) and isinstance(node.target, _ast.Name):
            names.add(node.target.id)
        elif isinstance(node, (_ast.FunctionDef, _ast.ClassDef)):
            names.add(node.name)
        elif isinstance(node, _ast.Import):
            names |= {(a.asname or a.name).split(".")[0] for a in node.names}
        elif isinstance(node, (_ast.ImportFrom,)):
            names |= {(a.asname or a.name) for a in node.names if a.name != "*"}
        elif isinstance(node, _ast.Try):     # try/except 里的两套导入
            for sub in _ast.walk(node):
                if isinstance(sub, _ast.ImportFrom):
                    names |= {(a.asname or a.name) for a in sub.names if a.name != "*"}
                elif isinstance(sub, _ast.Import):
                    names |= {(a.asname or a.name).split(".")[0] for a in sub.names}
    base = header.replace("from .world import", "from ..world import")
    base = base.replace("from .qi import", "from ..qi import")
    base += "\n\n__all__ = [\n"
    for nm in sorted(names):
        base += f'    "{nm}",\n'
    base += "]\n"

    PKG.mkdir(exist_ok=True)
    (PKG / "base.py").write_text(base, encoding="utf-8")

    for mod, methods in SYSTEMS.items():
        parts = [f'"""灵体层 · {CN[mod]}系统（M2 组件化拆分：自 spirit.py 整段搬运，行为不变）"""\n',
                 "from .base import *\n"]
        if mod == "kinship":
            # 诞育自指：灵之新生仍是灵——方法体原文引用 Spirit，
            # 运行时由包组装后注入真身（见 __init__.py），方法体一行不动
            parts.append("Spirit = None  # 诞育自指，包组装后注入真身\n")
        parts += [f"class {MIXIN[mod]}:", f'    """灵之{CN[mod]}诸行。"""']
        for m in methods:
            blk = by_name[m]
            if m == "__init__" and preamble:
                blk = preamble + blk        # 类体前言（文档串）随核心
            parts.append("\n".join(blk).rstrip() + "\n")
        (PKG / f"{mod}.py").write_text("\n".join(parts), encoding="utf-8")

    order = [m for m in SYSTEMS if m != "core"] + ["core"]
    mixins = ", ".join(MIXIN[m] for m in order)
    init = ['"""灵体层包（M2 组件化拆分）：对外接口与旧 spirit.py 完全一致。"""',
            "from .base import *",
            ""]
    for m in order:
        init.append(f"from .{m} import {MIXIN[m]}")
    init += ["", "", f"class Spirit({mixins}):",
             '    """灵：记忆体。世界无史而人心有史。"""', "", "    pass", "",
             "", "# 诞育自指：注入真身（kinship._诞育 方法体原文引用 Spirit）",
             "from . import kinship as _kinship",
             "_kinship.Spirit = Spirit", ""]
    (PKG / "__init__.py").write_text("\n".join(init), encoding="utf-8")

    print(f"拆分完成：{len(blocks)} 个方法 → {len(SYSTEMS)} 系统模块 + base.py")
    for mod, ms in SYSTEMS.items():
        print(f"  {mod:9s} {CN[mod]}系统：{len(ms)} 法")
    return 0


if __name__ == "__main__":
    sys.exit(main())
