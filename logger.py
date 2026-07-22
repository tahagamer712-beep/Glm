# -*- coding: utf-8 -*-
"""
  logger.py — إعداد الـ logger

  يُصدِّر الـ logger المركزي ومساعد تسجيل الاستثناءات.
  """

import sys as _sys_legacy
import os
# ─── استيراد كل المتغيرات العالمية من bot_legacy ───
from bot_legacy import *
import state as gl  # noqa: F401,F403
# FIX: استيراد صريح للـ logger
from bot_legacy import _logger, _log_exc  # noqa: F811

def _log_exc(e: Exception, ctx: str = "") -> None:
    """يُسجّل الاستثناء الصامت: أخطاء متوقعة → DEBUG، غير متوقعة → WARNING."""
    err = str(e).lower()
    _expected = ("timeout", "timed out", "connection", "network", "429",
                 "quota", "read error", "eof", "reset", "refused",
                 "ssl", "certificate", "unreachable", "not found", "no such")
    if any(x in err for x in _expected):
        _logger.debug(f"[silenced] {ctx or e.__class__.__name__}: {e.__class__.__name__}")
    else:
        _logger.warning(f"[unexpected-silenced] {ctx or e.__class__.__name__}: {e!r}")
