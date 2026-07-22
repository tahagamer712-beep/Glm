# -*- coding: utf-8 -*-
"""
  rss_cache.py — كاش RSS (TTL 55ث) + prefetcher

  يُصدِّر نظام التخزين المؤقت لـ RSS والـ prefetcher.
  """

import sys as _sys_legacy
import os
# ─── استيراد كل المتغيرات العالمية من bot_legacy ───
from bot_legacy import *
import state as gl  # noqa: F401,F403
from concurrent.futures import ThreadPoolExecutor, as_completed  # noqa: F401

# FIX: استيراد صريح لمتغيرات db_cache — db_cache مُحمَّل بواسطة bot_legacy قبل هذا الملف
# لذا هو متاح في sys.modules وهذا الاستيراد الصريح يعمل بشكل آمن.
from db_cache import (  # noqa: F401
    _feed_health, _feed_health_lock,
    _FEED_FAIL_RATIO, _FEED_MIN_SAMPLES,
)

# FIX: _fetch_one_feed معرَّفة في rss_fetcher.py الذي يُحمَّل بعد هذا الملف
# في قائمة features_news.py — نُعرِّف wrapper يُؤجِّل الاستيراد إلى وقت الاستدعاء الفعلي.
# هذا ليس حلاً مؤقتاً: Python يُخزِّن الوحدات في sys.modules ولا يُعيد تحميلها.
def _fetch_one_feed(feed_url):  # noqa: F811
    import rss_fetcher as _rf
    return _rf._fetch_one_feed(feed_url)

def _get_cached_feed(feed_url):
    """يعيد entries من الذاكرة المؤقتة إذا لم تنته صلاحيتها، وإلا يجلب ويخزّن."""
    now = time.time()
    with _global_rss_cache_lock:
        cached = _global_rss_cache.get(feed_url)
        if cached:
            entries, fetched_at = cached
            if (now - fetched_at) < _GLOBAL_RSS_CACHE_TTL:
                return entries   # استخدام الذاكرة المؤقتة
    # منتهية أو غير موجودة — اجلب جديدة
    entries = _fetch_one_feed(feed_url)
    with _global_rss_cache_lock:
        _global_rss_cache[feed_url] = (entries, now)
        # تنظيف الذاكرة من الـ feeds القديمة (> 10 دقائق)
        stale = [u for u, (_, t) in _global_rss_cache.items() if now - t > 600]
        for u in stale:
            _global_rss_cache.pop(u, None)
    return entries


# FIX: عدّاد إخفاقات الـ feeds — بعد 3 محاولات متتالية نُخفّض التسجيل إلى DEBUG
# هذا يُقلّل من ضجيج السجلات للـ feeds المحجوبة على Heroku (CNN, Reuters, إلخ)
_rss_fail_counts: dict = {}

def _rss_prefetcher():
    """
    🔑 المحمّل المسبق للـ RSS (الحل الجذري لمشكلة البطء):
    يجلب كل feeds جميع اللغات دفعةً واحدة في الخلفية كل 90 ثانية.
    broadcast_news يقرأ من الكاش مباشرة — لا يستغرق إلا ثوانٍ.
    """
    all_urls = set()
    try:
        _all_rss = globals().get('RSS') or DEFAULT_RSS
        for lang_feeds in _all_rss.values():
            all_urls.update(lang_feeds)
    except Exception as _exc:
        _log_exc(_exc)
    if not all_urls:
        return
    now = time.time()
    with _global_rss_cache_lock:
        stale_urls = [u for u in all_urls
                      if u not in _global_rss_cache
                      or (now - _global_rss_cache[u][1]) >= _GLOBAL_RSS_CACHE_TTL]
    if not stale_urls:
        _logger.info("✅ _rss_prefetcher: كل الـ feeds محدّثة (%d) — لا حاجة لتحديث", len(all_urls))
        return

    _logger.info("🔄 _rss_prefetcher: يجلب %d feed من أصل %d", len(stale_urls), len(all_urls))
    t0 = time.time()

    def _store(url):
        entries = _fetch_one_feed(url)
        if not entries:
            _rss_fail_counts[url] = _rss_fail_counts.get(url, 0) + 1
            # بعد 3 إخفاقات متتالية نُخفّض إلى DEBUG لتجنب ضجيج السجلات
            if _rss_fail_counts[url] <= 3:
                _logger.warning("⚠️ _rss_prefetcher: feed أعاد 0 خبر: %s", url[:80])
            else:
                _logger.debug("⚠️ _rss_prefetcher: feed أعاد 0 خبر (إخفاق #%d): %s",
                              _rss_fail_counts[url], url[:80])
        else:
            _rss_fail_counts[url] = 0  # إعادة العدّاد عند النجاح
        with _global_rss_cache_lock:
            _global_rss_cache[url] = (entries, time.time())

    # max_workers=15: توازن بين السرعة وعدم استنزاف خيوط Heroku
    # لا timeout على as_completed — كل feed له timeout خاص (12ث) في _fetch_one_feed
    # معادلة الوقت: 174 feed ÷ 15 عامل × 12ث = ~140ث في أسوأ حالة (مقبول في الخلفية)
    try:
        # PERF-FIX: استخدام _RSS_EXECUTOR الدائم من state.py بدلاً من إنشاء
        # ThreadPoolExecutor جديد في كل دفعة — إنشاء executor جديد يُولّد threads
        # جديدة في كل مرة مما يُشغّل الـ GIL ويُبطئ استجابة أوامر المستخدمين.
        # الـ executor الدائم يُعيد استخدام threads موجودة (تكلفة صفر تقريباً).
        _rss_ex = gl._RSS_EXECUTOR
        batch_size = 30  # نُقسّم على دفعات لمنع ضغط الذاكرة
        for i in range(0, len(stale_urls), batch_size):
            batch = stale_urls[i:i + batch_size]
            try:
                futs = {_rss_ex.submit(_store, url): url for url in batch}
                for fut in as_completed(futs):  # بدون timeout — كل feed له timeout خاص
                    try:
                        fut.result()
                    except Exception as _exc:
                        _log_exc(_exc)
            except (RuntimeError, OSError):
                # خيوط النظام مستنزفة — نجلب أهم الـ feeds فقط بشكل متسلسل
                for url in batch[:5]:
                    try:
                        _store(url)
                    except Exception as _exc:
                        _log_exc(_exc)
    except Exception as _exc:
        _log_exc(_exc)

    with _global_rss_cache_lock:
        total_entries = sum(len(v[0]) for v in _global_rss_cache.values())
    if total_entries == 0:
        _logger.error(
            "❌ _rss_prefetcher: انتهى لكن الكاش فارغ تماماً (%d feed)! "
            "تحقق من الشبكة أو حالة الـ feeds — لن تُرسَل أي أخبار.",
            len(_global_rss_cache)
        )
    else:
        _logger.info(
            "✅ _rss_prefetcher: انتهى خلال %.1f ثانية — %d خبر في الكاش من %d feed",
            time.time() - t0, total_entries, len(_global_rss_cache)
        )


# ======== حدّ أقصى لأخبار كل دورة بث (لمنع فيضان القائمة) ========
_MAX_NEWS_PER_CYCLE = 500   # FIX: كان 9999 — بلا حد يُجمّد الدورة ويمنع الدورة التالية

# ════════════════════════════════════════════════════════════════════
# قسم قاعدة البيانات (DB) — نُقل فعلياً إلى db.py
# ════════════════════════════════════════════════════════════════════
import db as _db_module  # noqa: F401
from db import *  # noqa: F401, F403
_db_module._export_all_to(globals())  # يجلب أيضاً الأسماء التي تبدأ بـ _

# ======== كاش الطقس (10 دقائق لكل مدينة) ========
_weather_cache = {}
_WEATHER_CACHE_TTL = 600

def _feed_record_ok(url: str):
    with _feed_health_lock:
        h = _feed_health.setdefault(url, {"ok": 0, "fail": 0, "disabled": False})
        h["ok"] = min(h["ok"] + 1, 1000)   # cap to avoid infinite growth
        if h["disabled"] and h["ok"] >= 3:  # auto re-enable after 3 successes
            h["disabled"] = False
            _logger.info("RSS feed re-enabled after recovery: %s", url)

def _feed_record_fail(url: str):
    with _feed_health_lock:
        h = _feed_health.setdefault(url, {"ok": 0, "fail": 0, "disabled": False})
        h["fail"] = min(h["fail"] + 1, 1000)
        total = h["ok"] + h["fail"]
        if (not h["disabled"]
                and _FF.get("feed_health", True)
                and total >= _FEED_MIN_SAMPLES
                and h["fail"] / total >= _FEED_FAIL_RATIO):
            h["disabled"] = True
            _logger.warning("RSS feed auto-disabled (%.0f%% fail rate): %s",
                            h["fail"] / total * 100, url)

# =============================================================================
# HEROKU FIX v4: Breaking News Detection
# If 3+ RSS sources publish a similar story within 10 minutes → flag as BREAKING
# =============================================================================
_breaking_counter: dict = {}    # title_key -> [(timestamp, source), ...]
_breaking_lock    = threading.Lock()
_BREAKING_THRESHOLD   = 3       # number of sources
_BREAKING_WINDOW_SECS = 600     # 10 minutes

def _feed_is_healthy(url: str) -> bool:
    with _feed_health_lock:
        return not _feed_health.get(url, {}).get("disabled", False)


def _rss_prefetcher_startup():
    time.sleep(3)
    _safe_job(_rss_prefetcher)()
_start_thread_once("RSSStartup", _rss_prefetcher_startup)
# ─── تنظيف ذاكرة الكاش كل ساعة ──────────────────────────────────
