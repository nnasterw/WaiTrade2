#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""batch_wfys.py: deprecated alias -> batch_diagnose.py --level=1

旧 L1 脚本已升级为 batch_diagnose.py 三层架构。直接调用转发参数。
推荐: python batch_diagnose.py --level=1|2|3
"""
import sys
import subprocess
from pathlib import Path

if __name__ == '__main__':
    args = [sys.executable,
            str(Path(__file__).parent / 'batch_diagnose.py'),
            '--level=1'] + sys.argv[1:]
    sys.exit(subprocess.call(args))
