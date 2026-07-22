# -*- coding: utf-8 -*-
"""
ai.py — محرك الذكاء الاصطناعي

يُوفِّر _export_all_to ويُعيد تصدير كل دوال الذكاء الاصطناعي
الموجودة في bot_legacy.py.
تم الإصلاح: هذا الملف كان مفقوداً وكان يُسبِّب ImportError في:
  • bot_legacy.py   (import ai as _ai_module) — في حالة وجوده
  • ai_engine.py    (from ai import *)
"""

import sys as _sys_mod

# استيراد كل شيء من bot_legacy
from bot_legacy import *
import state as gl  # noqa: F401,F403


def _export_all_to(target_globals: dict) -> None:
    """
    تصدير كل الأسماء المُعرَّفة في هذه الوحدة (بما فيها الأسماء التي تبدأ بـ _)
    إلى globals() الوحدة المُستدعِية.
    يُستخدَم من قِبل: ai_engine.py  —  _ai_module._export_all_to(globals())
    """
    _mod = _sys_mod.modules[__name__]
    for _name in dir(_mod):
        # FIX: نفس إصلاح db.py — تجاهل __file__/__name__/__doc__ لمنع إتلاف
        # هوية الوحدة المُستدعِية (ai_engine كان يفقد __file__ الحقيقي).
        if _name.startswith("__") and _name.endswith("__"):
            continue
        try:
            target_globals[_name] = getattr(_mod, _name)
        except Exception:
            pass
