# -*- coding: utf-8 -*-
"""
  ai_personalization.py — تتبع اهتمامات المستخدم + تخصيص البث

  يُصدِّر نظام التخصيص وتتبع الاهتمامات.
  """

import sys as _sys_legacy
import os
# ─── استيراد كل المتغيرات العالمية من bot_legacy ───
from bot_legacy import *
import state as gl  # noqa: F401,F403

def _update_user_interests(uid: str, title: str, source: str):
    """يتتبع اهتمامات المستخدم من سلوكه"""
    prefs = _user_interests.setdefault(uid, {"topics": collections.Counter(), "sources": collections.Counter(), "count": 0})
    words = [w for w in title.split() if len(w) > 4]
    for w in words[:5]:
        prefs["topics"][w] += 1
    if source:
        prefs["sources"][source] += 1
    prefs["count"] = prefs.get("count", 0) + 1

def _ai_curate_news_for_user(uid: str, candidates: list) -> list:
    """يرتب الأخبار حسب اهتمامات المستخدم"""
    prefs = _user_interests.get(str(uid))
    if not prefs or prefs.get("count", 0) < 5:
        return candidates  # لا يكفي تاريخ
    top_topics = [w for w, _ in prefs["topics"].most_common(10)]
    top_sources = [s for s, _ in prefs["sources"].most_common(5)]
    def score(cand):
        title = cand[1].lower()
        src = cand[2]
        s = 0
        for topic in top_topics:
            if topic.lower() in title:
                s += 10
        if src in top_sources:
            s += 5
        return s
    return sorted(candidates, key=score, reverse=True)


# ═══════════════════════════════════════════════════════════════════
# 5. إنذار مبكر للأزمات
# ═══════════════════════════════════════════════════════════════════
def news_matches_interests(title, interests):
    if not interests:
        return True
    title_lower = title.lower()
    for interest in interests:
        key = interest.split(" ", 1)[-1].lower()
        keywords = INTEREST_KEYWORDS.get(key, [])
        for kw in keywords:
            if kw.lower() in title_lower:
                return True
    return False

def _get_user_cat_keywords(uid) -> list:
    """يُعيد قائمة الكلمات المفتاحية بناءً على فئات المستخدم المحفوظة"""
    cats = users.get(str(uid), {}).get("news_cats", None)
    if not cats or "all" in cats:
        return []  # لا فلتر — كل الأخبار
    kws = []
    for cat in cats:
        kws.extend(_CATEGORY_KEYWORDS.get(cat, []))
    return list(set(kws))

def _news_matches_user_cats(title: str, summary: str, uid) -> bool:
    """يتحقق إذا كان الخبر يطابق فئات المستخدم المحفوظة"""
    cats = users.get(str(uid), {}).get("news_cats", None)
    if not cats or "all" in cats:
        return True  # كل الأخبار
    kws = _get_user_cat_keywords(uid)
    if not kws:
        return True
    text_lower = f"{title} {summary}".lower()
    return any(k.lower() in text_lower for k in kws)
