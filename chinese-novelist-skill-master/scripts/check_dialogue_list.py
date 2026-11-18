#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""对白清单 lint：把 `renderable-dialogue.md` 的六条下限变成可执行检查。

检查对象是 novelist 输出的 `对白清单.csv`，它同时是 novelist → drama 的数据契约。
这里查的是「这句台词能不能变成一条音轨」，不是文笔。

用法
  python check_dialogue_list.py 对白清单.csv
  python check_dialogue_list.py 对白清单.csv --strict   # 缺列/缺值也算失败
退出码：0 通过（允许 WARN）／1 有 FAIL／2 文件或表头不对
"""
from __future__ import annotations

import argparse
import csv
import io
import re
import sys
from collections import Counter, defaultdict

REQUIRED = ["场次", "镜序", "说话人", "台词", "字数", "预计秒数", "情绪", "建议镜型", "可删等级"]
MAX_CHARS = 15
SOFT_CHARS = 12
MAX_LINES_PER_SHOT = 2
MUST_RATIO = 0.60

# 多音字：同一句里没有上下文时读音随机，容易念错
POLYPHONE = "重行长为了还差调发处降解数相给"
# 三字连读同韵（喊招类）：三个字以同一尾字收束，连读糊成一坨
SHOUT_TRIPLE = re.compile(r"^[\u4e00-\u9fa5]{2}[式刀剑招]$")

HAN = re.compile(r"[\u4e00-\u9fa5]")


def cn_len(s: str) -> int:
    return len(HAN.findall(s or ""))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("csvfile")
    ap.add_argument("--strict", action="store_true")
    a = ap.parse_args()

    try:
        rows = list(csv.DictReader(io.open(a.csvfile, encoding="utf-8-sig")))
    except OSError:
        print(f"打不开 {a.csvfile}")
        return 2
    if not rows:
        print("CSV 是空的")
        return 2

    header = list(rows[0].keys())
    missing = [c for c in REQUIRED if c not in header]
    if missing:
        print("FAIL: 缺列 " + "、".join(missing))
        print("      表头应为：" + ",".join(REQUIRED + ["是否念招"]))
        return 2

    fails, warns = [], []
    per_shot: dict[tuple[str, str], list[dict]] = defaultdict(list)
    levels = Counter()

    for i, r in enumerate(rows, start=2):        # 2 = 首行数据在 CSV 的第 2 行
        line = (r.get("台词") or "").strip()
        if not line:
            continue
        shot = (r.get("场次", "").strip(), r.get("镜序", "").strip())
        per_shot[shot].append(r)
        n = cn_len(line)
        tag = f"{shot[0]}-{shot[1]}"

        # 1 字数
        try:
            declared = int(str(r.get("字数") or "0").strip())
        except ValueError:
            declared = -1
            warns.append(f"{tag} 字数列不是整数")
        if declared >= 0 and declared != n:
            fails.append(f"{tag} 字数写 {declared}，实际 {n} 字：「{line[:14]}」")
        if n > MAX_CHARS:
            fails.append(f"{tag} {n} 字超过硬上限 {MAX_CHARS}：「{line[:14]}…」")
        elif n > SOFT_CHARS:
            warns.append(f"{tag} {n} 字偏长（建议 6~12）：「{line[:14]}」")

        # 2 发声窗口
        try:
            sec = float(str(r.get("预计秒数") or "0").strip())
        except ValueError:
            sec = 0.0
            warns.append(f"{tag} 预计秒数不是数字")
        if n and sec:
            lo, hi = n / 5.0, max(n / 4.0, 1.5)   # 短句（喊招）允许留到 1.5 秒
            if not (lo * 0.7 <= sec <= hi * 1.5):
                warns.append(f"{tag} 预计 {sec:g}s 与 {n} 字不匹配（4~5 字/秒应约 {lo:.1f}~{hi:.1f}s）")
        elif a.strict and n:
            fails.append(f"{tag} 缺「预计秒数」，下游算不出镜长")

        # 3 镜型
        kind = (r.get("建议镜型") or "").strip().upper()
        if kind not in ("SOLO", "OTS", "DUO"):
            (fails if a.strict else warns).append(f"{tag} 建议镜型 `{kind or '空'}` 不是 SOLO/OTS/DUO")
        elif kind == "DUO":
            fails.append(f"{tag} 建议镜型=DUO 却有台词 —— 双人同框不得带台词，改镜型或拆镜")

        # 4 可删等级
        lv = (r.get("可删等级") or "").strip()
        if lv not in ("必需", "可删", "点缀"):
            (fails if a.strict else warns).append(f"{tag} 可删等级 `{lv or '空'}` 不是 必需/可删/点缀")
        else:
            levels[lv] += 1

        # 5 念招
        if (r.get("是否念招") or "").strip() == "是":
            if n > 4:
                fails.append(f"{tag} 念招写 {n} 字（应 2~4 字）：「{line[:14]}」")
            if SHOUT_TRIPLE.match(line):
                warns.append(f"{tag} 「{line}」三字连读同韵，建议压成 2 字")

        # 6 糊音字
        hit = [c for c in POLYPHONE if c in line]
        if hit:
            warns.append(f"{tag} 含多音字 {''.join(hit)}，无上下文时读音随机：「{line[:14]}」")

    # 7 单镜约束
    for shot, items in per_shot.items():
        tag = f"{shot[0]}-{shot[1]}"
        if len(items) > MAX_LINES_PER_SHOT:
            fails.append(f"{tag} 一镜 {len(items)} 句台词（上限 {MAX_LINES_PER_SHOT}）")
        who = {((it.get("说话人") or "").strip()) for it in items}
        if len(who) > 1:
            fails.append(f"{tag} 一镜 {len(who)} 个说话人（{'、'.join(sorted(who))}）—— 单轨只能一条音色")

    total = sum(levels.values())
    if total:
        ratio = levels["必需"] / total
        line = "可删等级分布：" + "、".join(f"{k} {v}" for k, v in levels.items()) + f"（必需 {ratio:.0%}）"
        print(line)
        if ratio > MUST_RATIO:
            fails.append(f"`必需` 占 {ratio:.0%} 超过 {MUST_RATIO:.0%} —— 对白层失败时没有可删的退路")

    # 逐行检查会产生重复项（同镜多条台词触发同一条规则），去重但保序
    fails = list(dict.fromkeys(fails))
    warns = list(dict.fromkeys(warns))

    print(f"台词 {len(rows)} 条 / 有台词镜 {len(per_shot)} 个")
    for m in warns[:20]:
        print("WARN:", m)
    if len(warns) > 20:
        print(f"WARN: …还有 {len(warns) - 20} 条")
    if fails:
        for m in fails[:25]:
            print("FAIL:", m)
        if len(fails) > 25:
            print(f"FAIL: …还有 {len(fails) - 25} 条")
        print(f"\n{len(fails)} 项不通过")
        return 1
    print("\nPASS — 字数、发声窗口、镜型、可删比例都对得上")
    return 0


if __name__ == "__main__":
    sys.exit(main())
