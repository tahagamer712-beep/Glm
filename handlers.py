# -*- coding: utf-8 -*-
"""
handlers.py — معالجات الأوامر (re-export)

يُعيد تصدير كل معالجات الأوامر والـ callbacks من bot_legacy
والملفات المُقسَّمة الأخرى.
تم الإصلاح: هذا الملف كان مفقوداً وكان يُسبِّب ImportError في main.py.
"""

import sys as _sys_mod
import os

# استيراد كل المعالجات من bot_legacy (يحتوي على كل @bot.message_handler)
from bot_legacy import *
import state as gl  # noqa: F401,F403

# استيراد الملفات المُقسَّمة التي تحتوي على معالجات إضافية
# (كل منها يُسجِّل معالجاته عند الاستيراد عبر @bot.message_handler)
try:
    import handler_start      # noqa: F401
except ImportError as _e:
    import logging; logging.getLogger(__name__).warning("handler_start: %s", _e)

try:
    import handler_admin      # noqa: F401
except ImportError as _e:
    import logging; logging.getLogger(__name__).warning("handler_admin: %s", _e)

try:
    import handler_ai         # noqa: F401
except ImportError as _e:
    import logging; logging.getLogger(__name__).warning("handler_ai: %s", _e)

try:
    import handler_help       # noqa: F401
except ImportError as _e:
    import logging; logging.getLogger(__name__).warning("handler_help: %s", _e)

try:
    import handler_news       # noqa: F401
except ImportError as _e:
    import logging; logging.getLogger(__name__).warning("handler_news: %s", _e)

try:
    import handler_settings   # noqa: F401
except ImportError as _e:
    import logging; logging.getLogger(__name__).warning("handler_settings: %s", _e)

try:
    import handler_sports     # noqa: F401
except ImportError as _e:
    import logging; logging.getLogger(__name__).warning("handler_sports: %s", _e)

try:
    import handler_voice      # noqa: F401
except ImportError as _e:
    import logging; logging.getLogger(__name__).warning("handler_voice: %s", _e)

try:
    import handler_callbacks  # noqa: F401
except ImportError as _e:
    import logging; logging.getLogger(__name__).warning("handler_callbacks: %s", _e)
