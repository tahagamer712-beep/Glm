# -*- coding: utf-8 -*-
"""
  ai_insight.py — InsightX: Why/Next/Impact/Bias/Sentiment/Entity/Risk

  يُصدِّر دوال التحليل والرؤى المتقدمة.
  """

import sys as _sys_legacy
import os
# ─── استيراد كل المتغيرات العالمية من bot_legacy ───
from bot_legacy import *
import state as gl  # noqa: F401,F403

def _news_iq_score(title: str, source_name: str = "", source_url: str = "", lang: str = "العربية 🇮🇶") -> dict:
    """يحسب مؤشر ذكاء الخبر (IQ Score) من 0 إلى 100 — مع نصوص مترجمة حسب اللغة"""
    score = 45
    importance = _news_importance_score(title)
    if importance == 2: score += 28
    elif importance == 1: score += 14

    src_lower = (source_name or source_url or "").lower()
    if any(s in src_lower for s in _CREDIBLE_SOURCES): score += 15

    words = title.split()
    if len(words) >= 7: score += 5
    if any(c.isdigit() for c in title): score += 4
    if len(title) > 60: score += 3

    score = min(100, max(28, score))

    _lvls  = _IQ_LEVEL_LABELS.get(lang,  _IQ_LEVEL_LABELS["English 🇬🇧"])
    _imps  = _IQ_IMPACT_LABELS.get(lang, _IQ_IMPACT_LABELS["English 🇬🇧"])

    if   score >= 88: level, color = _lvls[0], "🔴"
    elif score >= 72: level, color = _lvls[1], "🟠"
    elif score >= 55: level, color = _lvls[2], "🟡"
    else:             level, color = _lvls[3], "🟢"

    if   importance == 2: impact = _imps[0]
    elif importance == 1: impact = _imps[1]
    else:                 impact = _imps[2]

    bar_n = round(score / 10)
    bar   = "█" * bar_n + "░" * (10 - bar_n)
    return {"score": score, "level": level, "color": color,
            "impact": impact, "bar": bar}


# ======== 📡 رادار الأزمات — تتبع الأخبار متعددة المصادر ========
