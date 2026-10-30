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
SLOWED_RE = re.compile(r'(缓缓|慢慢|轻轻|徐徐)')
# 裁决二（2026-10-30）：减速词只在修饰「关键接触」的那一拍被判违规，
# 铺垫句里的单个减速词是风格（庄重、哀恸、镜头感），只提示。
CONTACT_VERB_RE = re.compile(
    r'(劈|斩|刺|扫|削|磕|格|撞|落刀|落剑|击中|命中|撞上|压下|递出|送出|挥出)'
)
SETUP_ACTION_RE = re.compile(r'(抬手|推门|走近|走近了|落座|转身|放下|起身|步入)')

DEFAULTS = {
    'simile_per_1000': 3,
    'dash_per_1000': 2,
    'bare_dialog_ratio': 0.25,
    'max_slowed': 4,
}


def strip_markdown(text: str) -> str:
    text = re.sub(r'^#{1,6}\s*', '', text, flags=re.M)
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
    text = re.sub(r'\*(.*?)\*', r'\1', text)
    text = re.sub(r'`{1,3}[^`]*`{1,3}', '', text)
    return text


def analyse(text: str, limits: dict, exempt_tells: bool = False) -> dict:
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
    slowed_sentences = [s for s in sentences if SLOWED_RE.search(s)]
    contact_slowed = [s for s in slowed_sentences if CONTACT_VERB_RE.search(s)]
    consecutive_slowed = any(
        SLOWED_RE.search(sentences[i]) and SLOWED_RE.search(sentences[i + 1])
        for i in range(len(sentences) - 1)
    )
    setup_only = [s for s in slowed_sentences if s not in contact_slowed]

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
    # 裁决一：套话是填空而不是观察，删掉后回合什么都不剩——按违规处理，除非显式豁免
    if body_tells and not exempt_tells:
        violations.append(
            f'身体/微表情套话 {body_tells} 处（嘴角勾起一抹、眼底闪过、瞳孔骤缩、心中一凛 等）；'
            '锚定单位已放宽到动作、物件、距离、沉默、呼吸，套话不计入。'
            '刻意克制或受限视角的章可用 --exempt-tells 退回提示'
        )
    # 裁决二：只有修饰关键接触的那一拍被判违规
    if contact_slowed:
        violations.append(
            f'{len(contact_slowed)} 句把减速词用在接触上（例：「{contact_slowed[0][:24]}…」）；'
            '力量感正是在这一拍被抹掉的，接触句改用短促动词与方向'
        )
    if consecutive_slowed:
        violations.append('连续两句都带减速词：节奏被拉平成腔调，留一处即可')
    if len(slowed_sentences) > limits['max_slowed']:
        violations.append(
            f'本章减速词 {len(slowed_sentences)} 处，超过 {limits["max_slowed"]}：'
            '不再是风格选择，是口癖'
        )

    notes = []
    if body_tells and exempt_tells:
        notes.append(f'身体套话 {body_tells} 处（已按 --exempt-tells 豁免，仅提示）')
    if setup_only:
        notes.append(
            f'铺垫类减速词 {len(setup_only)} 处未判违规（庄重、哀恸、镜头感语境是风格）；'
            '若某处其实是接触瞬间，请改写那句'
        )
    notes.append('排比、意象质量、留白效果需要人判，本脚本不数也不判')

    return {
        'chars': chars,
        'simile': simile,
        'dash': dash,
        'sentences': len(sentences),
        'body_tells': body_tells,
        'slowed': len(slowed_sentences),
        'slowed_contact': len(contact_slowed),
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
          f'减速词 {result["slowed"]} 处（其中接触句 {result["slowed_contact"]} 处）')
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
    parser.add_argument('--max-slowed', type=int, default=DEFAULTS['max_slowed'],
                        help='本章允许的减速词总数（裁决二阈值，默认 4）')
    parser.add_argument('--exempt-tells', action='store_true',
                        help='按裁决一的豁免条件（刻意克制文风、受限视角）把套话降为提示')
    args = parser.parse_args()

    if not args.path:
        print('错误: 需要章节文件路径，或 --all <目录>')
        return 2
    limits = {
        'simile_per_1000': args.simile_per_1000,
        'dash_per_1000': args.dash_per_1000,
        'bare_dialog_ratio': args.bare_dialog_ratio,
        'max_slowed': args.max_slowed,
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
        code = max(code, report(path, analyse(text, limits, args.exempt_tells), args.report_only))
    return code


if __name__ == '__main__':
    sys.exit(main())
