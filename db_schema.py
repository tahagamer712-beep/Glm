# -*- coding: utf-8 -*-
"""
  db_schema.py — إنشاء الجداول + WAL

  يُصدِّر دوال إنشاء قاعدة البيانات وضبط WAL.
  """

import sys as _sys_legacy
import os
# ─── استيراد كل المتغيرات العالمية من bot_legacy ───
from bot_legacy import *
import state as gl  # noqa: F401,F403
# FIX: استيراد صريح للأسماء الأساسية — ضمان للاستيراد الدائري
from bot_legacy import _logger, _db_conn, _db_cursor, _db_lock  # noqa: F811

# ملاحظة: الدوال المذكورة في __all__ موجودة في bot_legacy.py
# وتُستورد عبر السطر أعلاه (from bot_legacy import *)
