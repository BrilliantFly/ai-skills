#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
小说 → drama-skills 原著 合并脚本
把 chinese-novelist 项目里的 第*.md 章节文件按序合并成单一 原著.txt，
供 drama-skills 的 short-drama-novel-analyze（novel_index.py 按章节标题切分）直接使用。

用法:
  python scripts/merge_novel_to_source.py novels/书名/            # 输出到 novels/书名/输入/原著.txt
  python scripts/merge_novel_to_source.py novels/书名/ -o 目标.txt
  python scripts/merge_novel_to_source.py --all novels/           # 批量处理所有小说项目
"""

import argparse
import re
import sys
from pathlib import Path

if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

CHAPTER_RE = re.compile(r'^第\d+章')


def find_chapters(project_dir: Path):
    chapters = sorted(
        [f for f in project_dir.glob('第*.md') if CHAPTER_RE.match(f.name)],
        key=lambda f: int(re.search(r'\d+', f.name).group()),
    )
    return chapters


def clean_markdown(text: str) -> str:
    """把章节 Markdown 降级为纯文本：去掉标题井号、粗体/斜体标记，保留标题行文字。"""
    lines = []
    for line in text.splitlines():
        line = re.sub(r'^#{1,6}\s*', '', line)
        line = re.sub(r'\*\*(.*?)\*\*', r'\1', line)
        line = re.sub(r'\*(.*?)\*', r'\1', line)
        line = re.sub(r'~~(.*?)~~', r'\1', line)
        line = re.sub(r'`(.*?)`', r'\1', line)
        lines.append(line.rstrip())
    return '\n'.join(lines).strip()


def merge_project(project_dir: Path, out_path: Path) -> dict:
    chapters = find_chapters(project_dir)
    if not chapters:
        return {'ok': False, 'msg': f'{project_dir}: 未找到 第*.md 章节文件'}

    parts = []
    total_chars = 0
    for f in chapters:
        body = clean_markdown(f.read_text(encoding='utf-8'))
        # 确保章节标题行以"第X章"开头，便于 novel_index.py 切分
        if not body.startswith('第') and not CHAPTER_RE.match(body):
            title = CHAPTER_RE.search(f.stem)
            if title:
                body = f.stem + '\n\n' + body
        parts.append(body)
        total_chars += len(re.findall(r'[\u4e00-\u9fff]', body))

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text('\n\n'.join(parts) + '\n', encoding='utf-8')
    return {
        'ok': True,
        'msg': (f'{project_dir.name}: 合并 {len(chapters)} 章，共 {total_chars:,} 汉字 '
                f'-> {out_path}'),
    }


def main():
    ap = argparse.ArgumentParser(description='把小说章节合并为 drama-skills 原著.txt')
    ap.add_argument('path', help='小说项目目录（含 第*.md）或 --all 时的总目录')
    ap.add_argument('-o', '--output', help='输出文件路径（默认 <项目>/输入/原著.txt）')
    ap.add_argument('--all', action='store_true', help='批量处理总目录下所有小说项目')
    args = ap.parse_args()

    root = Path(args.path)
    if not root.exists():
        print(f'错误: 路径不存在 - {root}')
        sys.exit(1)

    if args.all:
        projects = [d for d in root.iterdir() if d.is_dir() and list(find_chapters(d))]
        if not projects:
            print('未找到含章节文件的小说项目')
            sys.exit(1)
        results = [merge_project(p, p / '输入' / '原著.txt') for p in projects]
    else:
        out = Path(args.output) if args.output else root / '输入' / '原著.txt'
        results = [merge_project(root, out)]

    failed = 0
    for r in results:
        print(('✅ ' if r['ok'] else '❌ ') + r['msg'])
        failed += (not r['ok'])
    sys.exit(1 if failed else 0)


if __name__ == '__main__':
    main()
