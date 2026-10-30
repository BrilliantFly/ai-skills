#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文本量化检查（去 AI 味的可数部分）
统计一章里能客观数出来的 AI 味指标：比喻密度、破折号密度、句长单调、段行单调、
裸对话标签、微表情套话、动作被减速修饰包住的处数。

只数「可核对」的项。凡需要判断修辞是否成功的（排比、意象质量、留白是否有效）
本脚本一律不判，也不假装判——数出来的次数只提示回看的位置，不代替作者决定改不改。

用法:
  python scripts/check_text_metrics.py <章节文件.md> [--per-1000] [--report-only]
  python scripts/check_text_metrics.py --all <目录> [--report-only]

退出码: 0 = 在阈内（或 --report-only）; 1 = 有超阈项; 2 = 用法或路径错误。

阈值（可用参数覆盖）默认按「千字」归一：比喻 ≤3、破折号 ≤2、
连续三句字数差 ≤2 的组 0 组、连续三段行数相同的组 0 组、裸对话标签占比 ≤25%。
"""

import argparse
import re
import sys
from pathlib import Path

if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

SIMILE_MARKERS = ('像', '如', '仿佛', '宛如', '犹如', '好似', '似乎', '般', '一样')
DASH_RE = re.compile(r'——|—')
CJK_RE = re.compile(r'[\u4e00-\u9fff]')
SENTENCE_SPLIT_RE = re.compile(r'[。！？…；\n]+')
BARE_DIALOG_RE = re.compile(r'^["“]?[^"”]{0,20}["”]?\s*(他说|她说|他道|她道|又说|答道)')
BODY_TELL_RE = re.compile(
    r'(嘴角勾起|勾起一抹|眼底闪过|眸中闪过|眼中闪过|瞳孔骤缩|眉头微蹙|眉头紧锁|'
    r'心中一凛|心中一动|不由自主|深吸一口气|狠狠地|清晰地看到|深深地看了)'
)
SLOWED_ACTION_RE = re.compile(r'(缓缓|慢慢|轻轻|徐徐)[^，。！？]{0,6}?(劈|斩|落|抬手|出手|落刀|抬剑|踏|掠|推|抽)')

DEFAULTS = {'simile_per_1000': 3, 'dash_per_1000': 2, 'bare_dialog_ratio': 0.25}


def strip_markdown(text: str) -> str:
    text = re.sub(r'^#{1,6}\s*', '', text, flags=re.M)
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
    text = re.sub(r'\*(.*?)\*', r'\1', text)
    text = re.sub(r'`{1,3}[^`]*`{1,3}', '', text)
    return text


def analyse(text: str, limits: dict) -> dict:
    body = strip_markdown(text)
    chars = len(CJK_RE.findall(body)) or 1
    per_1000 = chars / 1000.0

    simile = sum(body.count(marker) for marker in SIMILE_MARKERS)
    dash = len(DASH_RE.findall(body))
    sentences = [s.strip() for s in SENTENCE_SPLIT_RE.split(body) if len(CJK_RE.findall(s.strip())) >= 4]
    lengths = [len(CJK_RE.findall(s)) for s in sentences]

    monotone_groups = 0
    for i in range(len(lengths) - 2):
        a, b, c = lengths[i], lengths[i + 1], lengths[i + 2]
        if max(a, b, c) - min(a, b, c) <= 2:
            monotone_groups += 1

    paragraphs = [p for p in re.split(r'\n\s*\n', body) if p.strip()]
    line_counts = [len([l for l in p.splitlines() if l.strip()]) for p in paragraphs]
    same_block_groups = sum(
        1 for i in range(len(line_counts) - 2)
        if line_counts[i] == line_counts[i + 1] == line_counts[i + 2]
    )

    dialog_lines = [l for l in body.splitlines() if re.search(r'["“”]', l) or '说' in l or '道' in l]
    bare = sum(1 for l in dialog_lines if BARE_DIALOG_RE.match(l.strip()))
    bare_ratio = (bare / len(dialog_lines)) if dialog_lines else 0.0

    body_tells = len(BODY_TELL_RE.findall(body))
    slowed = len(SLOWED_ACTION_RE.findall(body))

    violations = []
    if simile / per_1000 > limits['simile_per_1000']:
        violations.append(f'比喻密度 {simile / per_1000:.1f} 处/千字，超过 {limits["simile_per_1000"]}')
    if dash / per_1000 > limits['dash_per_1000']:
        violations.append(f'破折号密度 {dash / per_1000:.1f} 处/千字，超过 {limits["dash_per_1000"]}')
    if monotone_groups:
        violations.append(f'{monotone_groups} 组连续三句字数几乎相同（差 ≤2），句式单调')
    if same_block_groups:
        violations.append(f'{same_block_groups} 组连续三段行数相同，段落形状单调')
    if bare_ratio > limits['bare_dialog_ratio']:
        violations.append(f'裸对话标签占比 {bare_ratio:.0%}，超过 {limits["bare_dialog_ratio"]:.0%}')

    notes = []
    if body_tells:
        notes.append(f'微表情/身体套话 {body_tells} 处命中黑名单：回看是否已被更具体的观察替代')
    if slowed:
        slowed_note = (f'动作被「缓缓/慢慢/轻轻」包住 {slowed} 处：关键接触前若为铺垫可留，'
                       '命中瞬间被减速则读不出力量——此条只提示，不判违规')
        notes.append(slowed_note)
    notes.append('排比、意象质量、留白效果需要人判，本脚本不数也不判')

    return {
        'chars': chars,
        'simile': simile,
        'dash': dash,
        'sentences': len(sentences),
        'body_tells': body_tells,
        'slowed': slowed,
        'bare_ratio': bare_ratio,
        'violations': violations,
        'notes': notes,
    }


def report(path: Path, result: dict, report_only: bool) -> int:
    print('\n' + '=' * 60)
    print(f'量化检查: {path.name}  （{result["chars"]:,} 汉字，{result["sentences"]} 句）')
    print('=' * 60)
    print(f'  比喻标记 {result["simile"]} 处 | 破折号 {result["dash"]} 处 | '
          f'裸对话标签占比 {result["bare_ratio"]:.0%} | 身体套话 {result["body_tells"]} 处 | '
          f'减速动作 {result["slowed"]} 处')
    for line in result['violations']:
        print(f'  ⚠️  {line}')
    for line in result['notes']:
        print(f'  · {line}')
    if not result['violations']:
        print('  ✅ 可数项均在阈内')
    if report_only:
        return 0
    return 1 if result['violations'] else 0


def main() -> int:
    parser = argparse.ArgumentParser(description='统计一章里可数的 AI 味指标')
    parser.add_argument('path', nargs='?', help='章节文件路径，或使用 --all 时的目录')
    parser.add_argument('--all', action='store_true', help='递归检查目录下 第*.md')
    parser.add_argument('--report-only', action='store_true', help='只报告，不影响退出码')
    parser.add_argument('--simile-per-1000', type=float, default=DEFAULTS['simile_per_1000'])
    parser.add_argument('--dash-per-1000', type=float, default=DEFAULTS['dash_per_1000'])
    parser.add_argument('--bare-dialog-ratio', type=float, default=DEFAULTS['bare_dialog_ratio'])
    args = parser.parse_args()

    if not args.path:
        print('错误: 需要章节文件路径，或 --all <目录>')
        return 2
    limits = {
        'simile_per_1000': args.simile_per_1000,
        'dash_per_1000': args.dash_per_1000,
        'bare_dialog_ratio': args.bare_dialog_ratio,
    }

    root = Path(args.path)
    if not root.exists():
        print(f'错误: 路径不存在 - {root}')
        return 2

    files = sorted(root.rglob('第*.md')) if args.all else ([root] if root.is_file() else [])
    if not files:
        print('没有找到章节文件')
        return 2

    code = 0
    for path in files:
        try:
            text = path.read_text(encoding='utf-8')
        except OSError as error:
            print(f'错误: 读取失败 {path} - {error}')
            code = max(code, 2)
            continue
        code = max(code, report(path, analyse(text, limits), args.report_only))
    return code


if __name__ == '__main__':
    sys.exit(main())
