# -*- coding: utf-8 -*-
"""
features_news.py — الأخبار والبث والـ RSS (re-export)

يُعيد تصدير كل دوال الأخبار والبث من bot_legacy والملفات المُقسَّمة.
تم الإصلاح: هذا الملف كان مفقوداً وكان يُسبِّب ImportError في main.py.
"""

import sys as _sys_mod
import os

from bot_legacy import *
import state as gl  # noqa: F401,F403

# تفعيل وحدات الأخبار المُقسَّمة
_news_modules = [
    "news_broadcaster",
    "news_dedup",
    "news_filter",
    "news_formatter",
    "news_scraper",
    "news_tracker",
    "rss_cache",
    "rss_fetcher",
    "rss_validator",
    "channel_broadcaster",
]

for _mod_name in _news_modules:
    try:
        __import__(_mod_name)
    except ImportError as _e:
        import logging as _lg
        _lg.getLogger(__name__).warning("features_news: لم يُحمَّل %s — %s", _mod_name, _e)
