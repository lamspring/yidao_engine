# -*- coding: utf-8 -*-
"""
史官 · 成篇器（writer.py）——LLM 翻译 + 考据表（§四）。

成篇器吃一条链（不是整场事件簿）。史官是侦探不是解说员：
动机靠调查（§2.4 调查接口自动调取），不靠被喂。

文体：史记体 × 悬疑叙事的克制白描。短句。冷笔。
戏剧性交给事实的排列，不交给形容词。

LLM 调用纪律：单链成篇 LLM 调用 = 1 次（调查与压缩都在规则层）；
校验不过把违规清单拼入重试，至多 2 次；仍不过 → 成篇失败写入报告，不许放行。
"""

from .inquest import Inquest
from .validator import Validator

# ── 史官身份与禁止清单（§4.3，写进 system_prompt）──
SYSTEM_PROMPT = """你是一方世界的史官——全知但克制的侦探。世界层只留证据，你靠调查还原因果。

文体：史记体 × 悬疑叙事的克制白描。短句。冷笔。戏剧性交给事实本身的排列，不交给形容词。

禁止清单（违者即废）：
1. 不发明：不许出现事件簿中不存在的人名、事件、物品、地点、死因。
2. 不无因果巧合：不许写"恰好""恰巧""冥冥中"来缝合链上没有的关联。
3. 克制比喻：每篇比喻不超过 3 处；"仿佛/似乎"全篇不超过 2 处。
4. 不预言：不许写链尾之后的事。
5. 全知反讽仅限已记录事实。
6. 动机必有所本：凡写到"他为什么这么做"，该动机必须能指到调查所得（读数/快照记忆/旁证）中的一条。
7. "不可考"是合法结局：调查无获时，写"其因已不可考"，优先于任何推测。

禁用网文腔（"卧槽""绝绝子""炸裂"等一律禁止），禁用空泛抒情。"""

_考据指令 = """
【考据指令】每个自然段末尾必须标注锚点 [E{事件id}]；全文结束附考据表。
输出格式（硬性）：
# {标题}

{正文，每段末尾带 [E{事件id}] 锚点}

---

## 考据表
| 段落 | 锚定事件 | tick | 事件原文 |
|------|----------|------|----------|
| §1 | E{事件id} | {tick} | "{原文逐字}" |
"""


def _压缩节拍(beats: list) -> list:
    """token 预算有界：节拍超 12 时规则压缩——留首/转折/尾，中段折叠计数。"""
    if len(beats) <= 12:
        return beats
    首 = beats[:4]
    尾 = beats[-4:]
    中段数 = sum(len(ids) for _, ids in beats[4:-4])
    return 首 + [("……（中段折叠 %d 节）" % 中段数, [])] + 尾


class Writer:
    """LLM 成篇：一条链 → 一篇带考据的史记体短文。"""

    def __init__(self, ledger, inquest: Inquest, llm_caller=None):
        self.ledger = ledger
        self.inquest = inquest
        self._llm = llm_caller      # callable(system, user) -> (text, usage)

    def _call_llm(self, system: str, user: str) -> tuple:
        if self._llm is not None:
            return self._llm(system, user)
        # 真调用：复用既有 LLM 基建（不新建）
        import sys, os
        sys.path.insert(0, os.path.dirname(os.path.dirname(
            os.path.dirname(os.path.abspath(__file__)))))
        from pipeline.llm_client import LLMClient
        from pipeline.config import LLMConfig
        cfg = LLMConfig.from_provider("deepseek")
        return LLMClient(cfg).call(system, user)

    def _构_prompt(self, chain) -> str:
        """构造 user_prompt：链梗概 + 链上事件（按节拍） + 调查所得 + 考据指令。"""
        byid = self.ledger.byid if hasattr(self.ledger, "byid") else None
        lines = [f"【链梗概】{chain.summary}", "", "【链上事件】（按节拍）"]
        for kind, ids in _压缩节拍(chain.beats):
            if not ids:
                lines.append(f"- {kind}")
                continue
            for i in ids:
                e = self.ledger.by_id(i)
                lines.append(f"- [E{i}] 第{e['day']}日 {e['kind']}: "
                             f"{e['actor'] or ''}{'→' + e['target'] if e['target'] else ''} "
                             f"{e['text']}")
            # 关键节拍自动调查：链首、转折（kind 变化）、链尾必查
        lines += ["", "【调查所得】（关键节拍：链首、转折、链尾必查；读数近临界者亦查）"]
        查 = set()
        beat_kinds = [k for k, _ in chain.beats]
        for idx, (kind, ids) in enumerate(chain.beats):
            关键 = idx == 0 or idx == len(chain.beats) - 1
            if idx and kind != beat_kinds[idx - 1]:
                关键 = True
            if not 关键 and ids:
                e0 = self.ledger.by_id(ids[0])
                rd = e0.get("readings") or {}
                if rd.get("pressure", 0) > 0.7 or rd.get("阳", 100) < 30:
                    关键 = True     # 读数近临界
            if 关键:
                for i in ids[:1]:       # 每节拍打点查首事件
                    查.add(i)
        for i in sorted(查):
            r = self.inquest.why(i)
            e = self.ledger.by_id(i)
            lines.append(f"- [E{i}] {e['kind']} 调查：读数 {r['readings']}；"
                         f"当事人心（{r['actor_mind']['时效']}）："
                         f"压力 {r['actor_mind']['快照'].get('pressure')}，"
                         f"记忆首条 {r['actor_mind']['快照'].get('top_memories', [{}])[0].get('要义', '无')}"
                         f"；旁证 {len(r['旁证'])} 条")
        lines += ["", _考据指令]
        return "\n".join(lines)

    def write(self, chain) -> dict:
        """单链成篇。返回 {ok, text, usage, 违规, attempts}。"""
        user = self._构_prompt(chain)
        validator = Validator(self.ledger, chain, self.inquest)
        违规史 = []
        for attempt in range(3):        # 首试 + 至多 2 次重试
            text, usage = self._call_llm(SYSTEM_PROMPT, user)
            违规 = validator.validate(text)
            if not 违规:
                return {"ok": True, "text": text, "usage": usage,
                        "违规": [], "attempts": attempt + 1}
            违规史.append(违规)
            user += "\n\n【违规清单，须逐条修正后重写】\n" + "\n".join(
                f"- {v}" for v in 违规)
        return {"ok": False, "text": None, "usage": None,
                "违规": 违规史[-1], "attempts": 3}     # 成篇失败，不许放行
