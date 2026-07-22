# -*- coding: utf-8 -*-
"""
db.py — قاعدة البيانات (SQLite)

يُوفِّر _export_all_to ويُعيد تصدير كل دوال ومتغيرات قاعدة البيانات
الموجودة في bot_legacy.py.
تم الإصلاح: هذا الملف كان مفقوداً وكان يُسبِّب ImportError في:
  • bot_legacy.py  (import db as _db_module)
  • rss_cache.py   (from db import *)
"""

import sys as _sys_mod

# استيراد كل شيء من bot_legacy ليكون متاحاً هنا أيضاً
# (bot_legacy يحتوي على كل كود قاعدة البيانات الفعلي)
from bot_legacy import *
import state as gl  # noqa: F401,F403


def _export_all_to(target_globals: dict) -> None:
    """
    تصدير كل الأسماء المُعرَّفة في هذه الوحدة (بما فيها الأسماء التي تبدأ بـ _)
    إلى globals() الوحدة المُستدعِية.
    يُستخدَم من قِبل: rss_cache.py  —  _db_module._export_all_to(globals())
    """
    _mod = _sys_mod.modules[__name__]
    for _name in dir(_mod):
        # FIX: تجاهل الأسماء المزدوجة الشرطة (__file__, __name__, __doc__...)
        # كانت تُنسخ سابقاً فتُتلِف هوية الوحدة المُستدعِية (مثلاً bot_legacy
        # يفقد __file__ الحقيقي ويصبح يُشير خطأً إلى db.py)، مما يُفسِد رسائل
        # الأخطاء ويُربك أي كود يعتمد على __name__/__file__ الصحيحين.
        if _name.startswith("__") and _name.endswith("__"):
            continue
        try:
            target_globals[_name] = getattr(_mod, _name)
        except Exception:
            pass
