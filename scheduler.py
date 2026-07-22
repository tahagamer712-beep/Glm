# -*- coding: utf-8 -*-
"""
  scheduler.py — كل المهام المجدولة (APScheduler)

  يحتوي على إعادة تصدير كائن الـ scheduler وكل الدوال المجدولة من bot_legacy.
  """

import sys as _sys_legacy
import os
# ─── استيراد كل المتغيرات العالمية من bot_legacy ───
from bot_legacy import *
import state as gl  # noqa: F401,F403
# FIX: استيراد صريح للأسماء الضرورية
from bot_legacy import _logger, _log_exc, _safe_job, _start_thread_once  # noqa: F811

# ملاحظة: الدوال المذكورة في __all__ موجودة في bot_legacy.py
# وتُستورد عبر السطر أعلاه (from bot_legacy import *)
