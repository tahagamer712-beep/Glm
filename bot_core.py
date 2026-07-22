# -*- coding: utf-8 -*-
"""
bot_core.py — كائن البوت + logger + دوال الإرسال الآمن

يُعيد تصدير كائن البوت الرئيسي ودوال الإرسال الآمن من bot_legacy.
تم الإصلاح: هذا الملف كان مفقوداً وكان يُسبِّب ImportError في main.py.
"""

import sys as _sys_mod
import os

# استيراد كل شيء من bot_legacy
from bot_legacy import *
import state as gl  # noqa: F401,F403

# ── تصدير صريح للمكوّنات الأساسية ──────────────────────────────────────────
# (مُتاحة بالفعل عبر star import أعلاه؛ هذا توثيق صريح فقط)
__all__ = [
    "bot",
    "_logger",
    "_log_exc",
    "send_alert",
    "safe_send_message",
    "safe_send_audio",
    "safe_send_photo",
]
