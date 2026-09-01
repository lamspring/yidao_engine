# -*- coding: utf-8 -*-
"""
史官 CLI：先死后著——世界跑完、事件簿落盘、再选链成篇。

    python -m v6.shiguan --seed 42 --days 60 [--out-md out.md --out-json out.json]

本期（S1）：事件簿 + 可讲述性报告（纯规则，零 LLM）。
"""
import argparse
import os
import sys

from yidao_core.session import Session
from yidao_core.world import TICKS_PER_DAY

from .recorder import EventLedger
from .selector import ChainSelector


def _写文件(path: str, text: str):
    """落盘前自建目录——输出目录不存在不是世界的错。"""
    d = os.path.dirname(path)
    if d:
        os.makedirs(d, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="v6.shiguan", description="史官：事件簿与可讲述性报告")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--days", type=int, default=60)
    ap.add_argument("--out-md", default="")
    ap.add_argument("--out-json", default="")
    ap.add_argument("--write-top", type=int, default=0,
                    help="成篇：取评分 Top-N 链各写一篇（调 LLM，走既有 llm_client 基建）")
    ap.add_argument("--write-dir", default="outputs/shiguan",
                    help="成篇落盘目录（自建）")
    args = ap.parse_args(argv)

    ledger = EventLedger()
    session = Session.genesis(seed=args.seed, on_event=ledger.record)
    ledger.bind(session.spirits)          # 观心快照用（§2.6）
    session.run(args.days * TICKS_PER_DAY)

    sel = ChainSelector(ledger, session.spirits)
    md, js = sel.report(args.seed, args.days)
    if args.out_md:
        _写文件(args.out_md, md)
    if args.out_json:
        import json
        _写文件(args.out_json, json.dumps(js, ensure_ascii=False, indent=1))
    print(md)

    # 成篇（S3）：先死后著——世界跑完、事件簿落盘、再选链成篇
    if args.write_top > 0:
        from .inquest import Inquest
        from .writer import Writer
        iq = Inquest(ledger, session.spirits)
        w = Writer(ledger, iq)
        chains = sel.detect_all()
        import time
        for c in chains[:args.write_top]:
            t0 = time.time()
            r = w.write(c)
            耗 = time.time() - t0
            if r["ok"]:
                fn = f"{args.write_dir}/seed{args.seed}_{c.链型}_{c.主体}.md"
                _写文件(fn, r["text"])
                u = r.get("usage") or {}
                print(f"[成篇] {c.链型}·{c.主体} → {fn}"
                      f"（{r['attempts']} 试，{耗:.1f} 秒，"
                      f"tokens {u.get('total_tokens', '?')}）")
            else:
                print(f"[成篇失败] {c.链型}·{c.主体}——事实密度撑不起一篇文："
                      f"{'、'.join(r['违规'][:3])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
