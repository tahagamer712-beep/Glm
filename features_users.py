# -*- coding: utf-8 -*-
"""
features_users.py — المستخدمون والمكافآت (re-export)

يُعيد تصدير كل دوال المستخدمين من bot_legacy والملفات المُقسَّمة.
تم الإصلاح: هذا الملف كان مفقوداً وكان يُسبِّب ImportError في main.py.
"""

import sys as _sys_mod
import os

from bot_legacy import *
import state as gl  # noqa: F401,F403

_users_modules = [
    "users_core",
    "users_premium",
    "users_referral",
    "users_stats",
]

for _mod_name in _users_modules:
    try:
        __import__(_mod_name)
    except ImportError as _e:
        import logging as _lg
        _lg.getLogger(__name__).warning("features_users: لم يُحمَّل %s — %s", _mod_name, _e)
