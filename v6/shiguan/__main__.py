# -*- coding: utf-8 -*-
"""
史官 CLI：先死后著——世界跑完、事件簿落盘、再选链成篇。

    python -m v6.shiguan --seed 42 --days 60 [--out-md out.md --out-json out.json]

本期（S1）：事件簿 + 可讲述性报告（纯规则，零 LLM）。
"""
import argparse
import sys

from yidao_core.session import Session
from yidao_core.world import TICKS_PER_DAY

from .recorder import EventLedger
from .selector import ChainSelector


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="v6.shiguan", description="史官：事件簿与可讲述性报告")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--days", type=int, default=60)
    ap.add_argument("--out-md", default="")
    ap.add_argument("--out-json", default="")
    args = ap.parse_args(argv)

    ledger = EventLedger()
    session = Session.genesis(seed=args.seed, on_event=ledger.record)
    session.run(args.days * TICKS_PER_DAY)

    sel = ChainSelector(ledger, session.spirits)
    md, js = sel.report(args.seed, args.days)
    if args.out_md:
        with open(args.out_md, "w", encoding="utf-8") as f:
            f.write(md)
    if args.out_json:
        import json
        with open(args.out_json, "w", encoding="utf-8") as f:
            json.dump(js, f, ensure_ascii=False, indent=1)
    print(md)
    return 0


if __name__ == "__main__":
    sys.exit(main())
