#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""py_sh.py: Python shell - 零 PowerShell 依赖的 Unix-style 命令

目的: PowerShell 5.1 编码/转义问题的根本性解决
- 完全用 Python 实现, 跨平台一致
- UTF-8 默认 (无乱码)
- 无反引号转义问题 (Python 不解释)
- 无 chcp 问题
- 提供 head/tail/grep/which/ll/la/cat/print 8 个常用命令

用法:
  # CLI 模式 (单次命令)
  python py_sh.py head 5 file.md
  python py_sh.py tail 10 file.md
  python py_sh.py grep "wf-yhcl" research/notes/*.md
  python py_sh.py which python
  python py_sh.py ll C:/Users/Gnef/.agents/skills
  python py_sh.py cat file.md

  # API 模式 (import)
  from py_sh import head, tail, grep, which, ll, cat
  print(head(5, 'file.md'))
"""
import sys
import os
import re
import argparse
import subprocess
from pathlib import Path
from datetime import datetime


def _read_text(path):
    """读文本, 自动检测 UTF-8 / GBK / cp936"""
    p = Path(path)
    raw = p.read_bytes()
    for enc in ('utf-8-sig', 'utf-8', 'gb18030', 'gbk', 'cp936'):
        try:
            return raw.decode(enc)
        except (UnicodeDecodeError, LookupError):
            continue
    return raw.decode('utf-8', errors='replace')


def _read_lines(path, encoding='utf-8'):
    return _read_text(path).splitlines()


def head(n=10, path=None, stdin_data=None):
    """head N lines"""
    if stdin_data is not None:
        lines = stdin_data.splitlines()[:n]
    else:
        lines = _read_lines(path)[:n]
    for line in lines:
        print(line)
    return lines


def tail(n=10, path=None, stdin_data=None):
    """tail N lines"""
    if stdin_data is not None:
        all_lines = stdin_data.splitlines()
        lines = all_lines[-n:] if len(all_lines) > n else all_lines
    else:
        all_lines = _read_lines(path)
        lines = all_lines[-n:] if len(all_lines) > n else all_lines
    for line in lines:
        print(line)
    return lines


def grep(pattern, *paths, ignore_case=False, line_numbers=False, recursive=False):
    """grep pattern in files"""
    flag = re.IGNORECASE if ignore_case else 0
    try:
        pat = re.compile(pattern, flag)
    except re.error:
        pat = re.compile(re.escape(pattern), flag)
    hits = []
    for path in paths:
        p = Path(path)
        if p.is_dir():
            if recursive:
                for f in p.rglob('*'):
                    if f.is_file():
                        hits.extend(_grep_file(f, pat, line_numbers))
        else:
            hits.extend(_grep_file(p, pat, line_numbers))
    for h in hits:
        print(h)
    return hits


def _grep_file(path, pattern, show_line_numbers):
    out = []
    if not path.exists():
        return out
    try:
        text = _read_text(path)
    except Exception:
        return out
    for i, line in enumerate(text.splitlines(), 1):
        if pattern.search(line):
            prefix = '{}:'.format(i) if show_line_numbers else ''
            out.append('{}{}'.format(prefix, line))
    return out


def which(name, path_dirs=None):
    """which command (Python 3.8 兼容)"""
    if path_dirs is None:
        path_dirs = os.environ.get('PATH', '').split(os.pathsep)
    if sys.platform == 'win32':
        exts = ['', '.exe', '.bat', '.cmd', '.ps1']
    else:
        exts = ['']
    for d in path_dirs:
        for ext in exts:
            full = Path(d) / (name + ext)
            if full.exists() and os.access(full, os.X_OK):
                return str(full)
    return None


def ll(path='.', show_hidden=True):
    """ll - list directory"""
    p = Path(path)
    if not p.is_dir():
        print('Not a directory:', path)
        return []
    entries = list(p.iterdir())
    if not show_hidden:
        entries = [e for e in entries if not e.name.startswith('.')]
    entries.sort(key=lambda e: (not e.is_dir(), e.name.lower()))
    print('{:<30} {:>10} {:<20}'.format('Name', 'Size', 'Modified'))
    print('-' * 65)
    for e in entries:
        try:
            size = e.stat().st_size if e.is_file() else 0
            mtime = datetime.fromtimestamp(e.stat().st_mtime).strftime('%Y-%m-%d %H:%M')
        except Exception:
            size, mtime = 0, '?'
        kind = '/' if e.is_dir() else ''
        print('{:<29} {:>10} {}'.format(e.name + kind, size, mtime))
    return entries


def la(path='.'):
    """la - list with hidden"""
    return ll(path, show_hidden=True)


def cat(*paths):
    """cat - print file contents"""
    out = []
    for path in paths:
        text = _read_text(path)
        print(text, end='')
        out.append(text)
    return out


# ===== CLI =====

def main():
    parser = argparse.ArgumentParser(description='py_sh - Python shell tools (no PowerShell)')
    sub = parser.add_subparsers(dest='cmd', required=True)

    p_head = sub.add_parser('head', help='first N lines')
    p_head.add_argument('n', type=int, nargs='?', default=10)
    p_head.add_argument('path')

    p_tail = sub.add_parser('tail', help='last N lines')
    p_tail.add_argument('n', type=int, nargs='?', default=10)
    p_tail.add_argument('path')

    p_grep = sub.add_parser('grep', help='pattern match')
    p_grep.add_argument('pattern')
    p_grep.add_argument('paths', nargs='+')
    p_grep.add_argument('-i', '--ignore-case', action='store_true')
    p_grep.add_argument('-n', '--line-numbers', action='store_true')
    p_grep.add_argument('-r', '--recursive', action='store_true')

    p_which = sub.add_parser('which', help='find command')
    p_which.add_argument('name')

    p_ll = sub.add_parser('ll', help='list directory')
    p_ll.add_argument('path', nargs='?', default='.')

    p_la = sub.add_parser('la', help='list with hidden')
    p_la.add_argument('path', nargs='?', default='.')

    p_cat = sub.add_parser('cat', help='print file')
    p_cat.add_argument('paths', nargs='+')

    args = parser.parse_args()

    if args.cmd == 'head':
        head(args.n, args.path)
    elif args.cmd == 'tail':
        tail(args.n, args.path)
    elif args.cmd == 'grep':
        grep(args.pattern, *args.paths, ignore_case=args.ignore_case,
             line_numbers=args.line_numbers, recursive=args.recursive)
    elif args.cmd == 'which':
        r = which(args.name)
        print(r if r else 'not found: ' + args.name)
    elif args.cmd == 'll':
        ll(args.path)
    elif args.cmd == 'la':
        la(args.path)
    elif args.cmd == 'cat':
        cat(*args.paths)


if __name__ == '__main__':
    main()
