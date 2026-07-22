# -*- coding: utf-8 -*-
"""
  news_tracker.py — تتبع الأخبار المُرسلة عالمياً (sent_news)

  يُصدِّر نظام تتبع الأخبار المُرسلة.
  """

import sys as _sys_legacy
import os
# ─── استيراد كل المتغيرات العالمية من bot_legacy ───
from bot_legacy import *
import state as gl  # noqa: F401,F403

def _gsn_active_keys(lang_dict: dict) -> set:
    """يُعيد فقط الروابط التي لم تنتهِ صلاحيتها (أقل من TTL)."""
    now = time.time()
    return {lnk for lnk, ts in lang_dict.items() if (now - ts) < _GLOBAL_SENT_TTL}

def _user_sent_active(sent_data) -> dict:
    """
    يُحوّل user_sent من set/list قديمة إلى dict {link: timestamp}،
    ويُعيد فقط الروابط النشطة (أقل من USER_SENT_TTL).
    """
    now = time.time()
    if isinstance(sent_data, dict):
        return {lnk: ts for lnk, ts in sent_data.items() if (now - ts) < _USER_SENT_TTL}
    elif isinstance(sent_data, (set, list)):
        # بنية قديمة — نعطيها timestamp "الآن" حتى تعيش الـ TTL الكامل
        # FIX: كان now - TTL/2 مما يجعلها تنتهي بعد ساعة فقط وتُعاد إرسال الأخبار القديمة
        fake_ts = now
        return {lnk: fake_ts for lnk in sent_data}
    return {}

def _load_global_sent_news():
    """
    يحمّل روابط الأخبار المُرسَلة من الملف المحفوظ.
    البنية الجديدة: {lang: {link: timestamp}}
    الروابط الأقدم من TTL (4 ساعات) تُحذف تلقائياً — هذا يمنع توقف البث.
    """
    global _global_sent_news
    _global_sent_news = {}
    try:
        if not os.path.exists(_GLOBAL_SENT_FILE):
            _logger.info("global_sent_news.json غير موجود — ابتداء جديد")
            return
        with open(_GLOBAL_SENT_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        now = time.time()
        loaded = {}
        for lang, val in data.items():
            if isinstance(val, dict):
                # البنية الجديدة: {link: timestamp}
                active = {lnk: ts for lnk, ts in val.items() if (now - ts) < _GLOBAL_SENT_TTL}
            else:
                # توافق مع البنية القديمة (قائمة روابط بدون وقت)
                # نعطيها وقت حديث فقط إذا كان الملف أقدم من TTL كاملاً
                file_age = now - os.path.getmtime(_GLOBAL_SENT_FILE)
                if file_age >= _GLOBAL_SENT_TTL:
                    active = {}
                else:
                    fake_ts = now - file_age
                    active = {lnk: fake_ts for lnk in list(val)[-500:]}
            loaded[lang] = active
        _global_sent_news = loaded
        total = sum(len(s) for s in _global_sent_news.values())
        _logger.info(f"✅ تم تحميل global_sent_news: {total} رابط نشط لـ {len(_global_sent_news)} لغة")
    except Exception as e:
        _logger.warning(f"فشل تحميل global_sent_news: {e}")
        _global_sent_news = {}

def _save_global_sent_news():
    try:
        now = time.time()
        with _global_sent_lock:
            # حفظ الروابط النشطة فقط (بدون المنتهية الصلاحية)
            data = {}
            for lang, val in _global_sent_news.items():
                if isinstance(val, dict):
                    active = {lnk: ts for lnk, ts in val.items() if (now - ts) < _GLOBAL_SENT_TTL}
                    if active:
                        data[lang] = active
                else:
                    pass  # تجاهل البنية القديمة
        with open(_GLOBAL_SENT_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
    except Exception as _exc:
        _log_exc(_exc)

# ======== feedparser بـ timeout (12 ثانية) لتجنب التعليق اللانهائي ========
def auto_clean_sent_news():
    """
    تنظيف دوري لسجل الأخبار المُرسَلة:
    1. لكل مستخدم: الحد = 8000 مدخل.
    2. global_sent_news: حذف الروابط المنتهية الصلاحية (أقدم من TTL).
    """
    # ─── 1. تنظيف sent_news لكل مستخدم (مع TTL) ─────────────────
    cleaned = 0
    now_c = time.time()
    for uid, info in list(users.items()):
        sent = info.get("sent_news", {})
        # حوّل البنية القديمة (set/list) للجديدة (dict مع timestamp)
        if isinstance(sent, (set, list)):
            fake_ts = now_c - (_USER_SENT_TTL / 2)
            sent = {lnk: fake_ts for lnk in sent}
            info["sent_news"] = sent
            cleaned += 1
        elif isinstance(sent, dict):
            # احذف المنتهية الصلاحية
            before = len(sent)
            info["sent_news"] = {lnk: ts for lnk, ts in sent.items()
                                 if (now_c - ts) < _USER_SENT_TTL}
            if len(info["sent_news"]) < before:
                cleaned += 1
    if cleaned > 0:
        _db_save_all_users(users)
        _logger.info(f"✅ Auto-Clean: تم تنظيف/تحويل sent_news لـ {cleaned} مستخدم")

    # ─── 2. تنظيف global_sent_news من الروابط المنتهية الصلاحية ──
    now = time.time()
    total_removed = 0
    with _global_sent_lock:
        for lang in list(_global_sent_news.keys()):
            val = _global_sent_news[lang]
            if isinstance(val, dict):
                before = len(val)
                _global_sent_news[lang] = {
                    lnk: ts for lnk, ts in val.items()
                    if (now - ts) < _GLOBAL_SENT_TTL
                }
                total_removed += before - len(_global_sent_news[lang])
            else:
                # بنية قديمة — احذفها كلها لإجبار البنية الجديدة
                _global_sent_news[lang] = {}
                total_removed += 1
    if total_removed > 0:
        _logger.info(f"✅ Auto-Clean: حُذف {total_removed} رابط منتهي الصلاحية من global_sent_news")
        _save_global_sent_news()

# ======== فحص الكلمات المفتاحية للمميزين ========
def _record_weekly_news(title, link, lang):
    """يسجّل خبراً لقائمة الأسبوع"""
    if lang not in _weekly_top_news:
        _weekly_top_news[lang] = {}
    key = link
    if key not in _weekly_top_news[lang]:
        _weekly_top_news[lang][key] = {"title": title, "link": link, "count": 0}
    _weekly_top_news[lang][key]["count"] += 1


def _archive_news_item(title: str, url: str, source: str, lang: str,
                       summary: str = "", fact: dict = None):
    """يُضيف خبراً للأرشيف مع تنظيف القديم تلقائياً"""
    now = time.time()
    cutoff = now - _NEWS_ARCHIVE_DAYS * 86400
    item = {
        "title": title, "url": url, "source": source, "lang": lang,
        "ts": now, "summary": summary, "fact": fact or {}
    }
    with _news_archive_lock:
        _news_archive.append(item)
        # حذف القديم
        while _news_archive and _news_archive[0]["ts"] < cutoff:
            _news_archive.pop(0)
        # حد أقصى
        if len(_news_archive) > _NEWS_ARCHIVE_MAX:
            del _news_archive[:len(_news_archive) - _NEWS_ARCHIVE_MAX]


def search_news_archive(query: str, lang_filter: str = "", max_results: int = 10) -> list:
    """يبحث في الأرشيف بكلمة مفتاحية"""
    q = query.lower().strip()
    if not q:
        return []
    words = [w for w in q.split() if len(w) > 2]
    results = []
    with _news_archive_lock:
        items = list(reversed(_news_archive))  # الأحدث أولاً
    for item in items:
        if lang_filter and item.get("lang") != lang_filter:
            continue
        title_l = item["title"].lower()
        if any(w in title_l for w in words):
            results.append(item)
        if len(results) >= max_results:
            break
    return results


# ─── 2. تقرير صحة البوت اليومي للأدمن ──────────────────────────
