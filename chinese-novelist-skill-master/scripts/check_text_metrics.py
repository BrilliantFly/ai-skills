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

阈值（可用参数覆盖）默认按「不惩罚已接受长稿」标定：比喻 ≤7、破折号 ≤10（均每千字）、
连续三句字数差 ≤2 的组 0 组、连续三段行数相同的组 0 组、裸对话标签占比 ≤25%、
减速词 ≤0.8 处/千字且每章不少于 4 处。想套用更严的外部口径就显式压参：
`--simile-per-1000 3 --dash-per-1000 2`。
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
# 裁决二（2026-10-30）：减速词只在**削弱发力**时判违规，不修饰力度本就很轻的动作。
# 实测《黑木崖·针与剑》第 01 章的「把剑尖在石面上轻轻磕了一下」是刻意的轻慢与不屑，
# 那里没有力量感可被抹掉——把它判违规属于规则误伤，反而教人删掉好句子。
CONTACT_VERB_RE = re.compile(
    r'(劈|斩|刺|扫|削|撞|落刀|落剑|击中|命中|撞上|压下|捅|挑|撩|挥出|递出|送出)'
)
TAP_VERB_RE = re.compile(r'(磕|点|弹|敲|碰|拂|拨|搭|按|移|挪|抬|放|落(?!刀|剑))')
SETUP_ACTION_RE = TAP_VERB_RE  # 轻触与铺垫同类，不判违规；保留别名便于阅读旧调用

# 阈值标定自本机已接受的 8 份真实章节（《MP3里的夏天》5 章 + 《白桦路上的318路》
# 初版与详尽版 + 《黑木崖·针与剑》第 01 章）：比喻中位 4.5、最高 6.7 处/千字；
# 破折号中位 6.4、最高 9.4 处/千字；裸对话标签中位 10%、最高 12.3%；
# 减速词最高密度 0.48 处/千字（详尽版 10,405 字 5 处）。
# 因此默认档取"不惩罚你自己已经在用的写法"：比喻 7、破折号 10、裸对话 25%、减速 0.8/千字且不少于 4 处。
# 想要外部（更严）口径就显式压参：--simile-per-1000 3 --dash-per-1000 2。
DEFAULTS = {
    'simile_per_1000': 7.0,
    'dash_per_1000': 10.0,
    'bare_dialog_ratio': 0.25,
    'max_slowed': 4,
    'slowed_per_1000': 0.8,
}


def strip_markdown(text: str) -> str:
    text = re.sub(r'^#{1,6}\s*', '', text, flags=re.M)
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
    text = re.sub(r'\*(.*?)\*', r'\1', text)
    text = re.sub(r'`{1,3}[^`]*`{1,3}', '', text)
    return text


def analyse(text: str, limits: dict, exempt_tells: bool = False,
            strict_sentences: bool = False) -> dict:
    body = strip_markdown(text)
    chars = len(CJK_RE.findall(body)) or 1
    per_1000 = chars / 1000.0

    simile = sum(body.count(marker) for marker in SIMILE_MARKERS)
    dash = len(DASH_RE.findall(body))
    sentences = [s.strip() for s in SENTENCE_SPLIT_RE.split(body) if len(CJK_RE.findall(s.strip())) >= 4]
    lengths = [len(CJK_RE.findall(s)) for s in sentences]

    # 段落单调量的是**字数**而不是行数：中文小说一行一段，行数为 1 是常态，
    # 早先按行数判在一篇 3,051 字的真稿上报出 65 组，是假阳性机器。
    # 带宽取相对值（±10%）并设 30 字下限：短段等长属正常节奏，长段连成一样高才是方块化。
    def monotony_runs(lengths, rel=0.10, floor=12, hard_floor=30):
        return sum(
            1 for i in range(len(lengths) - 2)
            if min(lengths[i:i + 3]) >= floor
            and (max(lengths[i:i + 3]) - min(lengths[i:i + 3])) <= rel * min(lengths[i:i + 3])
        )

    paragraphs = [p for p in re.split(r'\n\s*\n', body) if p.strip()]
    paragraph_lengths = [len(CJK_RE.findall(p)) for p in paragraphs]
    block_runs = sum(
        1 for i in range(len(paragraph_lengths) - 2)
        if min(paragraph_lengths[i:i + 3]) >= 30
        and (max(paragraph_lengths[i:i + 3]) - min(paragraph_lengths[i:i + 3]))
        <= 0.10 * min(paragraph_lengths[i:i + 3])
    )
    sentence_runs = monotony_runs(lengths)

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
    if block_runs:
        violations.append(
            f'{block_runs} 组连续三段字数几乎相同（±10% 内且各 ≥30 字）：段落被排成一样高的方块，'
            '读起来没有呼吸；长短段交替才有节奏'
        )
    # 句子单调只报告不判违规：7 篇已接受章节里最多出现 3 组，
    # 拿它当硬门会把正常稿判成不合格（假阳性比漏判更伤写作）。要看严就加 --strict-sentences。
    if sentence_runs and not strict_sentences:
        notes_extra = (f'连续三句长度接近（±10% 内、各 ≥12 字）{sentence_runs} 组：'
                       '未判违规，供回看句式是否单调')
    elif strict_sentences and sentence_runs:
        notes_extra = None
        violations.append(
            f'{sentence_runs} 组连续三句长度接近（±10% 内、各 ≥12 字）：句式单调'
        )
    else:
        notes_extra = None
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
    # 减速词按**千字密度**判，不按每章绝对数：长章节（如 10,405 字的详尽版）天然更多，
    # 绝对上限会把已达意的长稿判违规。留一个绝对下限，免得短章算出 0 或 1 的荒谬额度。
    slowed_allowed = max(
        limits['max_slowed'],
        int(limits['slowed_per_1000'] * per_1000 + 0.999),
    )
    if len(slowed_sentences) > slowed_allowed:
        violations.append(
            f'本章减速词 {len(slowed_sentences)} 处，超过本章额度 {slowed_allowed}'
            f'（按 {limits["slowed_per_1000"]} 处/千字、下限 {limits["max_slowed"]} 计）：'
            '不再是风格选择，是口癖'
        )

    notes = []
    if notes_extra:
        notes.append(notes_extra)
    if body_tells and exempt_tells:
        notes.append(f'身体套话 {body_tells} 处（已按 --exempt-tells 豁免，仅提示）')
    if setup_only:
        notes.append(
            f'铺垫或轻触类减速词 {len(setup_only)} 处未判违规（庄重、哀恸、镜头感，'
            '以及力度本就很轻的磕/点/弹属于风格）；若某处其实是发力接触，请改写那句'
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
                        help='减速词绝对下限额度（长章节按千字密度放宽，默认 4）')
    parser.add_argument('--max-slowed-per-1000', type=float,
                        default=DEFAULTS['slowed_per_1000'],
                        help='减速词千字额度（默认 0.8 处/千字，标定自已接受长稿）')
    parser.add_argument('--exempt-tells', action='store_true',
                        help='按裁决一的豁免条件（刻意克制文风、受限视角）把套话降为提示')
    parser.add_argument('--strict-sentences', action='store_true',
                        help='把"连续三句长度接近"从提示升级为违规（已接受长稿最多出现 3 组，默认不判）')
    args = parser.parse_args()

    if not args.path:
        print('错误: 需要章节文件路径，或 --all <目录>')
        return 2
    limits = {
        'simile_per_1000': args.simile_per_1000,
        'dash_per_1000': args.dash_per_1000,
        'bare_dialog_ratio': args.bare_dialog_ratio,
        'max_slowed': args.max_slowed,
        'slowed_per_1000': args.max_slowed_per_1000,
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
        code = max(code, report(path, analyse(text, limits, args.exempt_tells,
                                              args.strict_sentences), args.report_only))
    return code


if __name__ == '__main__':
    sys.exit(main())
