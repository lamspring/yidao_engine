# -*- coding: utf-8 -*-
"""
阶段六 v2：五口之家家庭史诗 — 白描精修版
基于 stage6 的模拟数据，重写 Prompt 要求 LLM 用纯剧情/白描手法叙事，正文中零数据引用
"""

import sys
import io
if sys.platform == "win32" and hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import requests

API_BASE = "https://token-plan-cn.xiaomimimimo.com/v1"
API_KEY = os.environ.get("YIDAO_API_KEY", "")
MODEL = "mimo-v2.5-pro"

# 复用 stage6 的数据包
timeline_package = open("stage6_timeline_package.txt", "r", encoding="utf-8").read()
appendix = open("stage6_appendix.txt", "r", encoding="utf-8").read()

print("=" * 60)
print("【阶段六 v2】五口之家家庭史诗 — 白描精修版")
print("=" * 60)

system_prompt = """你是一位顶尖的中文家族史诗小说家。你的任务是把系统采集到的家庭观测数据，转化为一段**纯粹的白描式文学叙事**。

## 核心规则（白描手法 + 零数据引用）

1. **叙事正文零数据引用**：
   - ❌ 禁止出现任何卦名（如"坤卦""大有""比卦"）
   - ❌ 禁止出现任何数字数据（如"相位0.92""势能0.82""交互分14.7"）
   - ❌ 禁止出现任何系统术语（如"体协议""用协议""同卦共鸣""先天对卦"）
   - ✅ 所有系统概念必须通过**具象化的剧情、白描、隐喻、象征**来体现

2. **白描手法要求**：
   - 用动作代替状态（不要写"他的势能很高"，要写"他整夜在书房里踱步，烟灰缸堆成了小山"）
   - 用环境代替概念（不要写"家庭进入了深渊阶段"，要写"那盏客厅的水晶灯，从那天起再也没有亮过"）
   - 用对话代替解释（不要写"他的体从承载裂变为创序"，要写"‘我不想再当你们的好女儿了。’她说完，把墙上那幅《簪花仕女图》撕了下来"）
   - 用细节代替概括（不要写"家庭结构崩解"，要写"母亲每天多摆一副碗筷，又默默收回去"）

3. **角色差异化**：
   - 父亲：根基、秩序、承载 → 用"山""石""地基""沉默""规矩"等意象
   - 母亲：渗透、滋养、交换 → 用"水""汤""缝补""低语""温度"等意象
   - 长子：锋芒、开拓、刚健 → 用"剑""烈火""冲锋""责任"等意象
   - 次子：变动、探索、好奇 → 用"风""书""疑问""旁观"等意象
   - 幼女：生机、变数、柔软 → 用"芽""画""蓝""闪电""海"等意象

4. **史诗弧线**：
   - T-2 日常稳态：五口人的日常，温馨但压抑，暗流已伏
   - T-1 暗流涌动：个别成员的变化开始以细节形式渗透进家庭氛围
   - T0 家庭事件：核心冲突爆发，用**一个具体场景**（如晚餐、雨夜、某个物品破碎）承载全部张力
   - T+1 余波震荡：每个人都在用自己的方式消化冲击，写出差异化的创伤反应
   - T+2 新秩序：家庭重构了新的平衡，但已不再是原来的样子，用**一个具体意象**暗示新秩序

5. **结尾要求**：
   - 最后一个段落必须是**一个具体的、可感知的画面或动作**
   - 不要总结，不要议论，不要点题
   - 让读者自己感受到"大地原来也可以容纳海洋"

## 输出结构

### 镜中之家（纯文学叙事，1200-1800字）
- 分五节，每节对应一个时间切片
- 每节标题用文学化表达（如"大地的同频呼吸""裂缝始于最安静的角落"）
- 正文中零数据引用、零系统术语
- 所有概念通过剧情、白描、隐喻、象征体现

### 对应关系标注（附录式）
- 放在叙事之后，用折叠/附录的形式
- 此处可以引用系统数据，但用简洁方式
- 格式：时间 → 成员 → 剧情元素 → 对应系统概念

### 叙事质量自检
- 同样放在附录中
"""

user_prompt = f"""以下是系统从易道动态世界引擎跟踪一个五口之家采集到的底层数据。

请你把它转化为一段**纯粹的白描式文学叙事**。要求：
1. 正文不出现任何卦名、数字、系统术语
2. 用动作、环境、对话、细节代替抽象概念
3. 给每个家庭成员起一个有质感的中文名字
4. 写出真实的家庭互动：冲突、扶持、误解、默契
5. 结尾是一个具体的画面，不要总结

---

{timeline_package}

---

{appendix}

---

请生成纯文学叙事 + 附录式对应关系标注 + 叙事质量自检：
"""

print("\n调用 LLM API...")

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
}

payload = {
    "model": MODEL,
    "messages": [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ],
    "temperature": 0.75,
    "max_tokens": 5000,
}

try:
    resp = requests.post(
        f"{API_BASE}/chat/completions",
        headers=headers,
        json=payload,
        timeout=180,
    )
    resp.raise_for_status()
    result = resp.json()
    llm_output = result["choices"][0]["message"]["content"]
    usage_info = result.get("usage", {})

    print(f"  API 成功 | 输入: {usage_info.get('prompt_tokens', '?')} | 输出: {usage_info.get('completion_tokens', '?')}")

    with open("stage6_v2_llm_output.txt", "w", encoding="utf-8") as f:
        f.write(llm_output)
    print("  已保存: stage6_v2_llm_output.txt")

except Exception as e:
    print(f"  API 失败: {e}")
    sys.exit(1)

# 验证：正文零数据引用
print("\n" + "=" * 60)
print("【白描精修版验证】")
print("=" * 60)

output = llm_output

# 提取叙事正文（### 对应关系标注 之前的部分）
narrative_part = output.split("### 对应关系")[0] if "### 对应关系" in output else output

checks = []

# 禁止出现的系统术语
forbidden_terms = ["相位", "势能", "交互分", "同卦共鸣", "先天对卦", "体协议", "用协议", "卦象"]
for term in forbidden_terms:
    has_term = term in narrative_part
    checks.append((f"正文中无'{term}'", not has_term))

# 禁止出现的数字模式（小数如0.92）
import re
has_decimal = bool(re.search(r'\d+\.\d+', narrative_part))
checks.append(("正文中无小数数据", not has_decimal))

# 必须有感官细节
sensory = ["光", "暗", "声", "响", "静", "风", "火", "冷", "热", "味道", "颤抖", "震动", "笑", "泪"]
has_sensory = sum(1 for w in sensory if w in narrative_part) >= 3
checks.append(("有感官细节", has_sensory))

# 必须有对话
dialogue = '：' in narrative_part or '"' in narrative_part or '"' in narrative_part
has_dialogue = dialogue
checks.append(("有对话描写", has_dialogue))

# 必须有动作
action = any(w in narrative_part for w in ["撕", "画", "写", "走", "站", "坐", "推", "拉", "锁", "开", "放", "拿"])
checks.append(("有动作描写", action))

# 必须有五个角色
member_names = ["沉岩", "润音", "钧屹", "砚舟", "蘅芷"]  # 预设名字
has_all_chars = sum(1 for name in member_names if name in narrative_part) >= 3
checks.append(("至少有3个角色名出现", has_all_chars))

all_pass = True
for desc, ok in checks:
    status = "PASS" if ok else "FAIL"
    if not ok:
        all_pass = False
    print(f"  [{status}] {desc}")

print()
if all_pass:
    print(">>> 白描精修版测试通过")
else:
    print(">>> 部分验证未通过")
print("=" * 60)

print("\n【LLM 生成的白描精修版叙事】\n")
print(narrative_part[:2000])
print("\n... [截断，完整内容见 stage6_v2_llm_output.txt]")
