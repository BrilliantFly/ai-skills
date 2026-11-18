#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""分镜可渲染性 lint：把 `voicetrack-renderability.md` 的规则变成可执行检查。

检查的是「这一镜交给单轨生成端能不能出声」，不是文学质量。

用法
  python storyboard_lint.py 分镜.md
  python storyboard_lint.py 分镜.md --fps 24 --ctx 22
  python storyboard_lint.py 分镜.md --strict      # 缺新字段也算失败（新项目用）
  python storyboard_lint.py 分镜.md --csv 分镜.csv # 同时导出机器可读表

退出码：0 全通过（允许 WARN）／1 有 FAIL／2 路径或解析错误
"""
from __future__ import annotations

import argparse
import csv
import io
import os
import re
import sys

MINIMUM_PYTHON = (3, 9)
if sys.version_info < MINIMUM_PYTHON:
    raise SystemExit("storyboard_lint.py requires Python 3.9 or newer")

SHOT_RE = re.compile(r"^##\s+(SHOT-[0-9A-Za-z\-]+)\s*[·:：]?\s*(.*)$", re.M)
FIELD_RE = re.compile(r"^-\s+\*\*(.+?)\*\*\s*[：:]\s*(.*)$", re.M)
QUOTE_RE = re.compile(r"「([^」]{1,60})」")
DECLARED_RE = re.compile(r"对白\s*([一二三四五六七八九十两\d]+)\s*句")
CN_NUM = {"一": 1, "两": 2, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6,
          "七": 7, "八": 8, "九": 9, "十": 10}

# 说话人识别：只在「名字 + 说话动词 + 「台词」」这种明确句式上认，避免把环境音当说话人
SPEAK_VERBS = ("问路", "问道", "追问", "反问", "低声道", "低声", "接话", "接口", "打趣", "嘟囔",
               "问", "答", "说", "道", "喊", "喝", "叫", "笑", "念", "骂")
_VERB_ALT = "|".join(sorted(SPEAK_VERBS, key=len, reverse=True))
SPEAKER_RE = re.compile(r"([\u4e00-\u9fa5]{2,4})(?:" + _VERB_ALT + r")$")
MAX_CHARS = 15          # 单句台词硬上限
MAX_LINES = 2           # 单镜台词句数上限

# ---- 打斗镜判据（见 references/action-choreography.md）
FIGHT_STRONG = ("出招", "交手", "对打", "对招", "招名", "兵刃相接", "格挡", "拆解",
                "反制", "拆招", "接刃", "过招", "刀剑相")
WEAPON_WORDS = ("剑尖", "剑锋", "剑身", "剑刃", "剑势", "刀尖", "刀锋", "刀背",
                "刀刃", "刀身", "刀势", "兵器")
STRIKE_VERBS = ("点", "压", "挑", "斩", "劈", "扫", "撩", "刺", "撞", "崩", "格",
                "架", "削", "切", "戳", "翻", "绕", "接")
DUEL_SYNC = ("同一时刻", "与此同时", "同时", "同一拍", "攻守", "反制", "拆解", "格开", "压住")
FACING_WORDS = ("面对面", "相对而立", "正面相对", "对峙")
SIDE_WORDS = ("画面左", "画面右", "左侧", "右侧")
MAX_REF_IMAGES = 9
FIGHT_MIN_REFS = 4      # 起始帧 + A 身份 + B 身份 + 场景
# 槽位起点：REF-xxx（顺序：n）· 或 PLAN-xxx（顺序：n）·
SLOT_START_RE = re.compile(r"(?:REF|PLAN)-[A-Za-z0-9\-]+（顺序：\d+）·")
SLOT_USE_RE = re.compile(r"用途：([^；;）)]+)")
IMG_NAME_RE = re.compile(r"([A-Za-z0-9\-_]+\.(?:png|jpg|jpeg|webp))")
# 路径正则：允许中文目录与「·」，用于取出带中文的图名（IMG_NAME_RE 只认 ASCII）
PATH_RE = re.compile(r"([^\s《》（）；;「」]+\.(?:png|jpg|jpeg|webp))")


def align17k5(n: int) -> int:
    if n <= 5:
        return 5
    return ((n - 5 + 16) // 17) * 17 + 5


def predict_export(length: int, ctx: int, first: bool) -> int:
    if first or ctx <= 0:
        return length
    return align17k5(length + ctx) - ctx


def split_shots(text: str) -> list[tuple[str, str, str]]:
    marks = list(SHOT_RE.finditer(text))
    out = []
    for i, m in enumerate(marks):
        end = marks[i + 1].start() if i + 1 < len(marks) else len(text)
        out.append((m.group(1), m.group(2).strip(), text[m.start():end]))
    return out


def fields_of(block: str) -> dict[str, str]:
    d: dict[str, str] = {}
    # 只取镜头字段区（### 之前），避免把冻结关键帧正文里的短句当字段
    head = block.split("\n###", 1)[0]
    for m in FIELD_RE.finditer(head):
        d[m.group(1).strip()] = m.group(2).strip()
    return d


def pick(d: dict[str, str], *names: str) -> str | None:
    for n in names:
        for k, v in d.items():
            if n in k:
                return v
    return None


def guess_speakers(line: str) -> list[str]:
    """从「声音」字段里猜说话人：只认「名字 + 说话动词 + 「台词」」句式。"""
    out = []
    for m in QUOTE_RE.finditer(line):
        head = line[max(0, m.start() - 16):m.start()]
        head = re.sub(r"[，,、；;：:（(）)「」\s]+$", "", head)
        hit = SPEAKER_RE.search(head)
        if hit:
            out.append(hit.group(1))
    return out


def parse_seconds(v: str | None) -> float | None:
    if not v:
        return None
    m = re.search(r"([0-9]+(?:\.[0-9]+)?)\s*(?:s|秒)", v)
    return float(m.group(1)) if m else None


def declared_lines(sound: str) -> int:
    """「对白六句」这类只报数量、不写原文的写法，也要算成有台词。"""
    total = 0
    for m in DECLARED_RE.finditer(sound):
        raw = m.group(1)
        total += CN_NUM.get(raw, int(raw) if raw.isdigit() else 0)
    return total


def parse_ref_slots(refs: str) -> list[tuple[str, str]]:
    """把「输入参考图」拆成 (用途, 文件名)。没有文件名（PLAN 写条目名）时返回空文件名。"""
    starts = [m.start() for m in SLOT_START_RE.finditer(refs)]
    if not starts:
        return []
    out: list[tuple[str, str]] = []
    for i, s in enumerate(starts):
        e = starts[i + 1] if i + 1 < len(starts) else len(refs)
        chunk = refs[s:e]
        use = SLOT_USE_RE.search(chunk)
        # 取路径最后一段作文件名：中文名（SHOT-008·断流_END.png）IMG_NAME_RE 抓不到
        path = PATH_RE.search(chunk)
        name = path.group(1).rsplit("/", 1)[-1] if path else ""
        out.append(((use.group(1).strip() if use else ""), name))
    return out


def is_fight_shot(action: str, block: str) -> bool:
    """判定打斗镜：强信号词命中，或「兵刃部位词 + 击打动词」同时出现。

    只提「背上背着一把剑」不算打斗——必须有兵刃参与动作，否则问路、按背这类镜会被误报。
    """
    text = (action or "") + block.split("\n###", 1)[0]
    if any(w in text for w in FIGHT_STRONG):
        return True
    return any(w in text for w in WEAPON_WORDS) and any(v in text for v in STRIKE_VERBS)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("storyboard")
    ap.add_argument("--fps", type=int, default=24)
    ap.add_argument("--ctx", type=int, default=22, help="continuityOverlapFrames；关闭连续链时传 0")
    ap.add_argument("--strict", action="store_true", help="缺 镜型/音色/验收基线 也算失败")
    ap.add_argument("--csv")
    a = ap.parse_args()

    if not os.path.exists(a.storyboard):
        print(f"找不到 {a.storyboard}")
        return 2
    text = io.open(a.storyboard, encoding="utf-8").read()
    shots = split_shots(text)
    if not shots:
        print("没解析到 `## SHOT-xxx · 名称` 镜头块")
        return 2

    fails, warns, rows = [], [], []
    handoffs: list[dict] = []   # 每镜的交接槽位，循环后逐缝核对
    seconds_only: list[str] = []
    total_design = total_actual = 0

    for idx, (sid, title, block) in enumerate(shots):
        f = fields_of(block)
        sound = pick(f, "声音", "音效") or ""
        kind = (pick(f, "镜型") or "").upper()
        frames_field = pick(f, "export_frames", "帧数")
        dur = parse_seconds(pick(f, "时长", "镜长"))
        voice = pick(f, "音色")
        base = pick(f, "验收基线")
        refs = pick(f, "输入参考图", "参考图") or ""

        quotes = QUOTE_RE.findall(sound)
        declared = declared_lines(sound)
        n_lines = max(len(quotes), declared)
        speakers = guess_speakers(sound)
        uniq = []
        for s in speakers:
            if s not in uniq:
                uniq.append(s)

        # 1 时长 / 帧数
        if frames_field:
            m = re.search(r"\d+", frames_field)
            length = int(m.group()) if m else 0
        elif dur is not None:
            length = int(round(dur * a.fps))
            seconds_only.append(f"{sid}({dur:g}s→{length})")
        else:
            length = 0
            if n_lines:
                warns.append(f"{sid} 有台词但没有可得出的镜长")
        if length:
            # 首段没有前文语境，不受 ctx 网格约束
            if not (idx == 0 and a.ctx > 0) and length % 17 != (5 - a.ctx) % 17:
                exp = predict_export(length, a.ctx, idx == 0)
                fails.append(f"{sid} length={length} 与 ctx={a.ctx} 不匹配，导出会变成 {exp}（{exp - length:+d} 帧）")
            total_design += length
            total_actual += predict_export(length, a.ctx, idx == 0)

        # 2 镜型与台词
        if n_lines:
            if not kind:
                (fails if a.strict else warns).append(
                    f"{sid} 有台词但未标 `镜型`（SOLO/OTS），下游无法判是否可渲染")
            elif kind == "DUO":
                fails.append(f"{sid} 镜型=DUO 却带 {n_lines} 句台词 —— DUO 不得有台词，必须拆镜")
            elif kind not in ("SOLO", "OTS"):
                fails.append(f"{sid} 镜型 `{kind}` 不是 SOLO/OTS/DUO")
            if n_lines > MAX_LINES:
                fails.append(f"{sid} 一镜 {n_lines} 句台词（上限 {MAX_LINES}）")
            if len(uniq) > 1:
                fails.append(f"{sid} 同镜出现 {len(uniq)} 个说话人（{'、'.join(uniq)}）—— 单轨只能一条音色")
            if declared and not quotes:
                warns.append(f"{sid} 只写「对白{declared}句」没写台词原文，出片后无从比对")
            for q in quotes:
                if len(q) > MAX_CHARS:
                    fails.append(f"{sid} 台词 {len(q)} 字超过 {MAX_CHARS}：「{q[:18]}…」")

        # 3 音色与验收基线
        if n_lines:
            if not voice:
                (fails if a.strict else warns).append(f"{sid} 有台词但没写 `音色`")
            if not base:
                (fails if a.strict else warns).append(f"{sid} 有台词但没写 `验收基线`（预期台词/最短发声秒/最长静音秒）")

        # 4 参考图（按槽位用途判，不再一刀切禁 IMG）
        action = pick(f, "唯一动作", "动作") or ""
        duel = pick(f, "对招")
        fight = is_fight_shot(action, block)
        slots = parse_ref_slots(refs)
        m_scene = re.search(r"(EP\d+-SC\d+)", pick(f, "来源") or "")
        handoffs.append({
            "sid": sid,
            "scene": m_scene.group(1) if m_scene else "",
            "fight": fight,
            "start": next((n for u, n in slots if u == "起始帧"), ""),
            "end": next((n for u, n in slots if u == "结束帧"), ""),
        })
        n_refs = len(re.findall(r"\.(?:png|jpg|jpeg|webp)", refs))
        if not refs:
            warns.append(f"{sid} 没有 `输入参考图`（无锚点镜，一致性只能靠文本）")
        else:
            for use, name in slots:
                if use == "起始帧" and name.upper().startswith("IMG-"):
                    fails.append(f"{sid} 用 IMG 条目（{name}）当 `用途：起始帧`——"
                                 f"多格排版板会被照抄成分屏，应换成该镜冻结关键帧起始帧")
            if n_refs > MAX_REF_IMAGES:
                fails.append(f"{sid} 挂 {n_refs} 张参考图，超过执行端上限 {MAX_REF_IMAGES}")

        # 5 打斗镜：双主语、面对面、参考图配给
        if fight:
            if not duel:
                (fails if a.strict else warns).append(
                    f"{sid} 判为打斗镜但没有 `对招` 列（攻=… → 守=… ｜结果=…），无法确认双主语")
            if not any(w in action for w in DUEL_SYNC):
                warns.append(f"{sid} 打斗镜的唯一动作没有攻守同步标记"
                             f"（「同一时刻」/「与此同时」/「反制」）——生成端会做成单人动作")
            if not any(w in action for w in FACING_WORDS):
                warns.append(f"{sid} 打斗镜没写朝向（「面对面」）——易出并肩站立")
            if not any(w in action for w in SIDE_WORDS):
                warns.append(f"{sid} 打斗镜没写左右站位（谁在画面哪侧）——易出站位乱跳")
            if n_refs and n_refs < FIGHT_MIN_REFS:
                (fails if a.strict else warns).append(
                    f"{sid} 打斗镜只挂 {n_refs} 张参考图（建议 ≥{FIGHT_MIN_REFS}："
                    f"起始帧 + 双方身份板 + 场景板）")

        rows.append({
            "镜号": sid, "名称": title, "镜型": kind or "", "帧数": length or "",
            "台词数": n_lines, "说话人": "/".join(uniq), "音色": voice or "",
            "参考图": n_refs, "结束帧": "有" if any(u == "结束帧" for u, _ in slots) else "",
            "打斗": "是" if fight else "", "对招": "有" if duel else "",
        })

    # 6 镜间交接帧（见 references/shot-handoff.md）
    #    同场景相邻镜：前一镜交出的结束帧，必须就是后一镜的起始帧（同一路径），换图等于没接。
    for prev, nxt in zip(handoffs, handoffs[1:]):
        same_scene = bool(prev["scene"]) and prev["scene"] == nxt["scene"]
        if prev["end"]:
            if not nxt["start"]:
                fails.append(f"{prev['sid']} 交了结束帧（{prev['end']}），但 {nxt['sid']} 没有 `用途：起始帧`"
                             f"——下一镜会从自己的图起手，动作接不住")
            elif nxt["start"] != prev["end"]:
                fails.append(f"{prev['sid']}→{nxt['sid']} 交接帧不同图："
                             f"结束帧 {prev['end']} vs 起始帧 {nxt['start']}——下游跟图不跟字，等于没接")
        elif same_scene and prev["fight"] and not prev["end"]:
            (fails if a.strict else warns).append(
                f"{prev['sid']}→{nxt['sid']} 同场连续打斗缺交接：{prev['sid']} 没有 `用途：结束帧`，"
                f"{nxt['sid']} 的起始帧只能另出一张——两镜各自起手，动作接不住")

    if seconds_only:
        warns.insert(0, f"{len(seconds_only)} 镜只写秒数未写 `export_frames`："
                        + "、".join(seconds_only[:8]) + ("…" if len(seconds_only) > 8 else ""))

    print(f"镜头数={len(shots)}  fps={a.fps}  ctx={a.ctx}  有台词镜={sum(1 for r in rows if r['台词数'])}"
          f"  打斗镜={sum(1 for r in rows if r['打斗'])}"
          f"  交接缝={sum(1 for p in handoffs if p['end'])}")
    if total_design:
        print(f"设计 {total_design} 帧 / {total_design / a.fps:.2f}s   "
              f"预测成片 {total_actual} 帧 / {total_actual / a.fps:.2f}s  "
              f"漂移 {total_actual - total_design:+d} 帧")
    if a.csv:
        with io.open(a.csv, "w", encoding="utf-8-sig", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)
        print(f"分镜表: {a.csv}")

    for m in warns[:20]:
        print("WARN:", m)
    if len(warns) > 20:
        print(f"WARN: …还有 {len(warns) - 20} 条同类提示")
    if fails:
        for m in fails[:25]:
            print("FAIL:", m)
        if len(fails) > 25:
            print(f"FAIL: …还有 {len(fails) - 25} 条")
        print(f"\n{len(fails)} 项不通过")
        return 1
    print("\nPASS — 镜型、台词体量、帧长、参考图都对得上")
    return 0


if __name__ == "__main__":
    sys.exit(main())
