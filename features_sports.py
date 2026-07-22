# -*- coding: utf-8 -*-
"""
features_sports.py — الرياضة v5+v6 (re-export)

يُعيد تصدير كل دوال الرياضة من bot_legacy والملفات المُقسَّمة.
تم الإصلاح: هذا الملف كان مفقوداً وكان يُسبِّب ImportError في main.py.
"""

import sys as _sys_mod
import os

from bot_legacy import *
import state as gl  # noqa: F401,F403

_sports_modules = [
    "sports_365",
    "sports_espn",
    "sports_field",
    "sports_fixtures",
    "sports_keyboards",
    "sports_live",
    "sports_news",
    "sports_notifications",
    "sports_preferences",
]

for _mod_name in _sports_modules:
    try:
        __import__(_mod_name)
    except ImportError as _e:
        import logging as _lg
        _lg.getLogger(__name__).warning("features_sports: لم يُحمَّل %s — %s", _mod_name, _e)
