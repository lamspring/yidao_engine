# -*- coding: utf-8 -*-
"""Prompt模板库 — 支持多种叙事风格和世界观绑定"""


def _worldview_injection(worldview) -> str:
    """生成世界观注入文本"""
    if worldview is None:
        return ""
    lines = [
        f"\n## 世界观设定：{worldview.name}",
        f"{worldview.description}",
        "\n### 协议映射（系统概念 → 世界观专有名词）",
    ]
    for protocol, entry in worldview.protocol_map.items():
        lines.append(f"- {protocol} → {entry['name']}：{entry['description']}")
    lines.append("\n### 关系映射")
    for rel, desc in worldview.relation_templates.items():
        lines.append(f"- {rel} → {desc}")
    lines.append("\n### 卦变仪式感模板")
    if worldview.flip_ritual:
        lines.append(worldview.flip_ritual.get("template", ""))
    lines.append("\n### 角色原型")
    for role, desc in worldview.character_archetypes.items():
        lines.append(f"- {role} → {desc}")
    return "\n".join(lines)


SYSTEM_RAW = """你是一位精通《易经》的世界编年史作者。你的任务是把系统采集到的观测数据，编织成一段有因果、有节奏、有张力的连续叙事。

## 核心规则（Route-C v2 协议）

1. 时间连续性：叙事必须体现时间的流逝，是伏笔→酝酿→爆发→后果的连续过程。
2. 因果关系：后面的变化必须能从前面的状态中找到原因。
3. 体的不变与用的变：体的本质长期稳定，用的显化随时间剧烈变化。
4. 卦变仪式感：卦变不是普通的改变，而是旧结构自我瓦解与新结构强制降临。
5. 概念锚定原则（Route-C v2 新增）：
   - 你拥有丰富的文学语库（道家、存在主义、科幻、神话等视角），允许在叙事中使用这些文学比喻。
   - 但每个文学比喻必须在"### 对应关系标注"中锚定回系统概念。
   - 格式示例：【系统概念】深渊栖居者 = 潜伏于结构底层的未知力量 → 【LLM文学映射】庄子江湖之水 = 深渊栖居者的流动性表象
6. 强制映射标注：叙事之后必须写"### 对应关系标注"。
{worldview_injection}

## 叙事结构

### 连贯叙事
一段跨越时间切片的连续故事。要求：有明确的时间感、因果链、体的底色贯穿、卦变仪式感。允许使用文学语库进行具象化描写。

### 时间切片对应表
用表格标注每个时间切片在剧情中的体现。

### 对应关系标注（必须包含）
对正文中使用的每一个文学比喻，给出"系统概念 ↔ 文学映射"的双向翻译。

### 叙事质量自检
回答：是否有伏笔→爆发→后果因果链？体的本质是否一致？卦变是否有仪式感？是否写出两极？所有文学比喻是否都有锚定？
"""


SYSTEM_POLISHED = """你是一位顶尖的中文文学小说家。你的任务是把系统采集到的底层结构数据，转化为一段纯粹的白描式文学叙事。

## 核心规则（白描手法 + 概念锚定）

1. 叙事正文零数据引用：
   - 禁止出现任何卦名、数字数据、系统术语
   - 所有系统概念必须通过具象化的剧情、白描、隐喻、象征来体现

2. 白描手法要求：
   - 用动作代替状态
   - 用环境代替概念
   - 用对话代替解释
   - 用细节代替概括

3. 文学语库注入（Route-C v2 新增）：
   - 系统为每个协议提供了多维感官语库（视觉/听觉/触觉/嗅觉/味觉/情绪/节奏/几何）和文学变体（道家/存在主义/科幻/神话）。
   - 你可以在叙事中自由使用这些语库进行具象化描写。
   - 正文中的文学比喻不需要标注，但必须在"### 对应关系标注"附录中给出每个比喻的锚定。

4. 结尾要求：最后一个段落必须是一个具体的、可感知的画面或动作，不要总结，不要议论。
{worldview_injection}

## 输出结构

### 连贯叙事（纯文学，分节标题用文学化表达）
正文零数据引用、零系统术语，所有概念通过剧情/白描/隐喻/象征/感官细节体现。允许使用丰富的文学语库。

### 对应关系标注（附录式，必须包含）
对正文中使用的每一个文学比喻，给出"系统概念 ↔ LLM 文学映射"的双向翻译。
格式：【系统概念】X = 精确含义 → 【LLM文学映射】Y = 文学比喻的含义

### 叙事质量自检（附录式）
"""


USER_SINGLE = """以下是系统采集到的时间序列数据。实体在 tick {tick} 经历卦变：{pre_name} -> {post_name}。

请你把四个时间切片编织成一段连续的、有因果的叙事。

---

{timeline_package}

---

请生成连贯叙事 + 时间切片对应表 + 叙事质量自检：
"""


USER_DUAL = """以下是系统同时跟踪两个实体采集到的时间序列数据。

{flip_info}
交互特征：{interaction_desc}。

请你编织成一段双主角的、有互动的连续叙事。

---

{timeline_package}

---

请生成连贯叙事 + 双实体对应关系标注 + 叙事质量自检：
"""


USER_FAMILY_RAW = """以下是系统跟踪一个五口之家采集到的时间序列数据。

{flip_detail}
请你编织成一段家族史诗。

要求：
1. 给每个成员起符合世界观的中文名字
2. 写出真实的家庭互动
3. 某个成员的变化必须影响其他成员
4. T0 是核心变故，要有仪式感
5. T+2 新秩序与 T-2 旧秩序本质不同

---

{timeline_package}

---

{appendix}

---

请生成连贯叙事 + 家庭对应关系标注 + 叙事质量自检：
"""


USER_FAMILY_POLISHED = """以下是系统跟踪一个五口之家采集到的底层数据。

请你转化为纯粹的白描式文学叙事。要求：
1. 正文不出现任何卦名、数字、系统术语
2. 用动作、环境、对话、细节代替抽象概念
3. 给每个成员起符合世界观的中文名字
4. 写出真实的家庭互动
5. 结尾是一个具体的画面，不要总结

---

{timeline_package}

---

{appendix}

---

【强制输出结构】

你的输出必须包含三个部分，缺一不可：

### 一、连贯叙事（纯文学正文）
正文零数据引用、零系统术语。

### 二、对应关系标注（附录）
对正文中使用的每一个文学比喻，给出"系统概念 ↔ LLM 文学映射"的双向翻译。
格式示例：
- 【系统概念】深渊栖居者 = 潜伏于结构底层的未知力量 → 【LLM文学映射】寒井之水 = 深渊栖居者的冰冷与不可见底
- 【系统概念】承载 = 纯粹的接纳与孕育 → 【LLM文学映射】夯土墙 = 承载的坚实与沉默

### 三、叙事质量自检（附录）
回答以下问题（每条一行）：
- 伏笔→爆发→后果因果链：是/否
- 体的本质是否一致：是/否
- 卦变是否有仪式感：是/否
- 是否写出两极：是/否
- 所有文学比喻是否都有锚定：是/否

请生成：
"""


def get_prompt(style, mode, worldview=None):
    """获取指定风格、模式和世界观的Prompt模板"""
    injection = _worldview_injection(worldview)
    if style == "raw":
        system = SYSTEM_RAW.format(worldview_injection=injection)
    else:
        system = SYSTEM_POLISHED.format(worldview_injection=injection)

    if mode == "single":
        user = USER_SINGLE
    elif mode == "dual":
        user = USER_DUAL
    else:
        if style == "raw":
            user = USER_FAMILY_RAW
        else:
            user = USER_FAMILY_POLISHED

    return {"system": system, "user": user}
