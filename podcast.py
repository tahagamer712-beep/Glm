# -*- coding: utf-8 -*-
"""
  podcast.py — البودكاست اليومي (AI script + TTS)

  يُصدِّر نظام البودكاست اليومي.
  """

import sys as _sys_legacy
import os
# ─── استيراد كل المتغيرات العالمية من bot_legacy ───
from bot_legacy import *
import state as gl  # noqa: F401,F403

# ملاحظة: الدوال المذكورة في __all__ موجودة في bot_legacy.py
# وتُستورد عبر السطر أعلاه (from bot_legacy import *)
