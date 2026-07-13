#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""定位 WaiTrade2 项目根目录。"""
import os
from pathlib import Path


def find_root():
    override = os.environ.get("WAITRADE2_ROOT")
    if override:
        candidate = Path(override).resolve()
        if (candidate / "config" / "strategies.yaml").exists():
            return candidate
    for start in (Path.cwd(), Path(__file__).resolve()):
        for candidate in (start,) + tuple(start.parents):
            if (candidate / "config" / "strategies.yaml").exists():
                return candidate
    raise RuntimeError("找不到 WaiTrade2 根目录，请设置 WAITRADE2_ROOT")


ROOT = find_root()
