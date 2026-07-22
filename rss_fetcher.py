# -*- coding: utf-8 -*-
"""
  rss_fetcher.py — feedparser + جلب RSS + timeout

  يُصدِّر دوال جلب RSS وتحليله.
  """

import sys as _sys_legacy
import os
# ─── استيراد كل المتغيرات العالمية من bot_legacy ───
from bot_legacy import *
import state as gl  # noqa: F401,F403
# FIX: _feed_is_healthy/_feed_record_ok/_feed_record_fail معرَّفة في rss_cache
# (محمَّل قبل rss_fetcher في features_news.py — الترتيب #7 vs #8)
from rss_cache import _feed_is_healthy, _feed_record_ok, _feed_record_fail  # noqa: F401

def _parse_feed(url, timeout=12):
    result = [None]
    def _fetch():
        try:
            result[0] = feedparser.parse(url)
        except Exception as _exc:
            _log_exc(_exc)
    t = threading.Thread(target=_fetch, daemon=True)
    t.start()
    t.join(timeout)
    return result[0]

def _parse_feed_with_backoff(url, timeout=12, max_retries=3):
    """FIX-10: Exponential backoff عند فشل جلب الـ feed."""
    import random as _rand
    for attempt in range(max_retries):
        result = _parse_feed(url, timeout)
        if result is not None and result.entries:
            return result
        if attempt < max_retries - 1:
            wait = min(2 ** attempt + _rand.uniform(0, 1), 60)
            time.sleep(wait)
    return result  # أعد آخر نتيجة حتى لو فارغة


# ======== جلب RSS متوازي مع وقت النشر الحقيقي ========
_RSS_FRESHNESS_MINUTES = 60   # نافذة الحداثة: 60 دقيقة — طلب المستخدم: لا بث لأي خبر عمره أكثر من ساعة (خاص وقنوات)
_RSS_FETCH_TIMEOUT     = 8     # ثواني لكل feed


# HEROKU FIX v4: ETag store for _fetch_one_feed
_rss_etag_store: dict = {}   # url -> {"etag": str, "last_modified": str, "entries": list}
# FIX (SSOT): كان يُنشئ Lock منفصلاً بنفس الاسم بدل استخدام قفل state.py
# الوحيد المُتشارَك مع bot_scheduled_jobs.py.
_rss_etag_lock  = gl._rss_etag_lock


import calendar as _calendar   # مُستورد مرة واحدة بدلاً من داخل كل loop

def _extract_entry_image(item):
    """يستخرج رابط صورة الخبر الجاهزة من عنصر RSS (media:content / media:thumbnail /
    enclosure) — بدون أي طلب شبكة إضافي، لأن هذي البيانات موجودة مسبقاً ضمن استجابة
    الـ feed نفسه. لا تأثير على سرعة البث."""
    try:
        media_content = getattr(item, "media_content", None)
        if media_content:
            for m in media_content:
                url = m.get("url") if isinstance(m, dict) else None
                if url:
                    return url
        media_thumb = getattr(item, "media_thumbnail", None)
        if media_thumb:
            for m in media_thumb:
                url = m.get("url") if isinstance(m, dict) else None
                if url:
                    return url
        for attr in ("links", "enclosures"):
            items_list = getattr(item, attr, None)
            if not items_list:
                continue
            for enc in items_list:
                if not isinstance(enc, dict):
                    continue
                etype = enc.get("type") or ""
                if etype.startswith("image/"):
                    url = enc.get("href") or enc.get("url")
                    if url:
                        return url
    except Exception:
        pass
    return None

def _fetch_one_feed(feed_url):
    """
    يجلب feed واحد ويعيد قائمة entries مرتبة حسب وقت النشر.
    كل entry: dict بـ link, title, summary, published_dt, feed_url
    HEROKU FIX v4: Uses ETag/Last-Modified to avoid re-fetching unchanged feeds.
    """
    # Track health
    if _FF.get("feed_health", True) and not _feed_is_healthy(feed_url):
        return []   # feed is auto-disabled due to repeated failures
    try:
        # Try HTTP GET with ETag/Last-Modified headers first
        entries_from_http = None
        if _FF.get("rss_etag", True):
            try:
                import requests as _req_etag
                with _rss_etag_lock:
                    cached_meta = _rss_etag_store.get(feed_url, {})
                headers = {"User-Agent": "IraqNowBot/1.0 +https://t.me/Iraqnowbot"}
                if cached_meta.get("etag"):
                    headers["If-None-Match"] = cached_meta["etag"]
                if cached_meta.get("last_modified"):
                    headers["If-Modified-Since"] = cached_meta["last_modified"]
                resp = _req_etag.get(feed_url, headers=headers,
                                     timeout=_RSS_FETCH_TIMEOUT, stream=False)
                if resp.status_code == 304:  # Not Modified
                    _feed_record_ok(feed_url)
                    with _rss_etag_lock:
                        return _rss_etag_store.get(feed_url, {}).get("entries", [])
                if resp.status_code == 200:
                    import io as _io_etag
                    parsed_http = feedparser.parse(
                        _io_etag.BytesIO(resp.content))
                    new_etag = resp.headers.get("ETag", "")
                    new_lm   = resp.headers.get("Last-Modified", "")
                    entries_from_http = (parsed_http, new_etag, new_lm)
            except Exception:
                entries_from_http = None  # fallback to feedparser direct
        if entries_from_http:
            parsed, new_etag, new_lm = entries_from_http
        else:
            parsed = _parse_feed(feed_url, timeout=_RSS_FETCH_TIMEOUT)
            new_etag, new_lm = "", ""
        if not parsed or not parsed.entries:
            _feed_record_fail(feed_url)
            return []
        entries_out = []
        for item in parsed.entries[:40]:
            link  = getattr(item, 'link',  None)
            title = getattr(item, 'title', '').strip()
            if not link or not title:
                continue
            summ  = getattr(item, 'summary', '') or getattr(item, 'description', '')
            # استخراج وقت النشر الفعلي
            pub_struct = (getattr(item, 'published_parsed', None)
                          or getattr(item, 'updated_parsed', None))
            if pub_struct:
                try:
                    pub_dt = datetime.datetime.utcfromtimestamp(
                        _calendar.timegm(pub_struct)
                    )
                except Exception:
                    pub_dt = None
            else:
                pub_dt = None
            entries_out.append({
                "link":         link,
                "title":        title,
                "summary":      summ,
                "published_dt": pub_dt,   # datetime UTC أو None
                "feed_url":     feed_url,
                "image":        _extract_entry_image(item),  # جاهزة من الـ feed — بدون طلب شبكة إضافي
            })
        # رتّب من الأحدث للأقدم
        entries_out.sort(
            key=lambda x: x["published_dt"] or datetime.datetime(2000, 1, 1),
            reverse=True
        )
        # Save ETag metadata for next request
        if _FF.get("rss_etag", True) and (new_etag or new_lm):
            with _rss_etag_lock:
                _rss_etag_store[feed_url] = {
                    "etag": new_etag, "last_modified": new_lm,
                    "entries": entries_out
                }
        _feed_record_ok(feed_url)
        return entries_out
    except Exception as _exc_feed:
        _logger.warning("⚠️ _fetch_one_feed فشل: %s — %s: %s",
                        feed_url[:80], type(_exc_feed).__name__, _exc_feed)
        _feed_record_fail(feed_url)
        return []


def _parallel_fetch_feeds(feed_urls, max_workers=8):
    """
    يجلب قائمة feeds بالتوازي ويدمج النتائج مرتبةً بوقت النشر.
    """
    all_entries = []
    workers = min(max_workers, len(feed_urls) or 1, 4)  # HEROKU: max 4
    try:
        with ThreadPoolExecutor(max_workers=workers) as ex:
            futures = {ex.submit(_fetch_one_feed, url): url for url in feed_urls}
            for future in as_completed(futures):  # بدون timeout — كل feed له timeout خاص
                try:
                    all_entries.extend(future.result())
                except Exception as _exc:
                    _log_exc(_exc)
    except (RuntimeError, OSError):
        # خيوط النظام مستنزفة — نجلب بشكل متسلسل كبديل
        for url in feed_urls[:5]:
            try:
                all_entries.extend(_fetch_one_feed(url))
            except Exception as _exc:
                _log_exc(_exc)
    # رتّب الكل من الأحدث للأقدم
    all_entries.sort(
        key=lambda x: x["published_dt"] or datetime.datetime(2000, 1, 1),
        reverse=True
    )
    return all_entries


def _is_fresh(pub_dt, window_minutes=_RSS_FRESHNESS_MINUTES):
    """هل الخبر منشور خلال النافذة الزمنية المحددة؟"""
    if pub_dt is None:
        return True   # مجهول الوقت → نقبله
    try:
        # FIX: نتعامل مع timezone-aware وnaive بشكل صحيح
        if pub_dt.tzinfo is not None:
            pub_naive = pub_dt.astimezone(datetime.timezone.utc).replace(tzinfo=None)
        else:
            pub_naive = pub_dt   # نفترض UTC
        now_utc = datetime.datetime.utcnow()
        age = (now_utc - pub_naive).total_seconds() / 60
        # نقبل حتى 60 دقيقة في المستقبل (drift بين مصادر مختلفة)
        return -60 <= age <= window_minutes
    except Exception:
        return True   # عند أي خطأ → نقبل الخبر


_PUB_TIME_I18N = {
    "العربية 🇮🇶": ("منذ لحظات", "منذ {} دقيقة", "منذ {} ساعة"),
    "English 🇬🇧":  ("just now",    "{} min ago",    "{} hr ago"),
    "Русский 🇷🇺":  ("только что",  "{} мин назад",  "{} ч назад"),
    "فارسی 🇮🇷":    ("لحظاتی پیش", "{} دقیقه پیش", "{} ساعت پیش"),
    "हिन्दी 🇮🇳":   ("अभी",        "{} मिनट पहले",  "{} घंटे पहले"),
    "Türkçe 🇹🇷":   ("az önce",    "{} dk önce",    "{} sa önce"),
    "Deutsch 🇩🇪":  ("gerade eben", "vor {} Min",    "vor {} Std"),
    "Español 🇲🇽":  ("hace un momento", "hace {} min", "hace {} h"),
    "Português 🇧🇷":("há pouco",   "há {} min",     "há {} h"),
    "Italiano 🇮🇹": ("or ora",     "{} min fa",     "{} ore fa"),
    "Українська 🇺🇦":("щойно",    "{} хв тому",    "{} год тому"),
    "اردو 🇵🇰":     ("ابھی",       "{} منٹ پہلے",   "{} گھنٹے پہلے"),
    "Français 🇫🇷": ("à l'instant", "il y a {} min", "il y a {} h"),
}

def _get_feeds_for_user(lang, country):
    """يدمج مصادر الدولة المحددة + مصادر اللغة معاً (الدولة أولاً)"""
    lang_feeds    = RSS.get(lang, [])
    flag          = _get_country_flag(country)
    country_feeds = COUNTRY_RSS.get(flag, [])
    if not country_feeds:
        return lang_feeds
    # دمج: مصادر الدولة أولاً ثم بقية مصادر اللغة التي ليست في قائمة الدولة
    country_set = set(country_feeds)
    extra = [f for f in lang_feeds if f not in country_set]
    return country_feeds + extra

# تحميل الـ feeds مع الدمج الذكي: الأفضلية للـ DEFAULT_RSS لكن مع الحفاظ على أي إضافات يدوية
_loaded_rss = load_json(RSS_FILE, {})
RSS = {}
for lang, feeds in DEFAULT_RSS.items():
    RSS[lang] = DEFAULT_RSS[lang]  # دائماً خذ المصادر الجديدة
for lang, feeds in _loaded_rss.items():
    if lang not in RSS:
        RSS[lang] = feeds  # أضف أي لغة أضافها الأدمن يدوياً

def _track_source_speed(source_name: str, pub_dt):
    """يسجّل توقيت نشر المصدر لقياس سرعته"""
    if pub_dt:
        _source_speed_log[source_name].append(pub_dt.timestamp())
        if len(_source_speed_log[source_name]) > 100:
            _source_speed_log[source_name] = _source_speed_log[source_name][-100:]

def _get_source_rankings() -> list:
    """يحسب ترتيب المصادر حسب السرعة والكمية"""
    now = time.time()
    rankings = []
    for source, timestamps in _source_speed_log.items():
        recent = [t for t in timestamps if now - t < 24 * 3600]
        if not recent:
            continue
        avg_gap = (max(recent) - min(recent)) / max(len(recent) - 1, 1) if len(recent) > 1 else 9999
        rankings.append({
            "source": source,
            "count_24h": len(recent),
            "avg_gap_min": round(avg_gap / 60, 1),
            "score": len(recent) * 100 / max(avg_gap / 60, 1),
        })
    return sorted(rankings, key=lambda x: x["score"], reverse=True)

# ═══════════════════════════════════════════════════════════════════
# 9. سكرابنق المصادر المظلمة (الرسمية)
# ═══════════════════════════════════════════════════════════════════
def get_source_name_from_url(feed_url):
    """استخراج اسم المصدر من رابط الـ RSS أو رابط تلغرام"""
    try:
        # روابط تلغرام: t.me/channelname أو t.me/channelname/123
        if "t.me/" in feed_url:
            # استخراج الهاندل بشكل موثوق
            clean_url = feed_url.replace("https://", "").replace("http://", "")
            parts = clean_url.split("/")
            # parts[0]="t.me", parts[1]=handle, parts[2]=message_id (اختياري)
            handle = parts[1] if len(parts) > 1 else parts[0].split("t.me/")[-1]
            handle = handle.split("?")[0].strip()  # حذف query params إن وجدت
            # بحث في قاموس القنوات المعروفة (TELEGRAM_NEWS_CHANNELS)
            if handle in _TG_CHANNEL_NAMES:
                return _TG_CHANNEL_NAMES[handle]
            # بحث في SOURCE_NAMES بشكل غير حساس لحالة الأحرف
            handle_lower = handle.lower()
            for key, name in SOURCE_NAMES.items():
                if key.startswith("t.me/") and key.split("t.me/")[-1].lower() == handle_lower:
                    return name
            # إعادة الهاندل كاسم نظيف (بدون رابط)
            return f"@{handle}"
        import urllib.parse as _up
        host = _up.urlparse(feed_url).netloc.lower()
        for prefix in ("www.", "feeds.", "rss.", "feed."):
            if host.startswith(prefix):
                host = host[len(prefix):]
        for key, name in SOURCE_NAMES.items():
            if key in host:
                return name
        parts = host.split(".")
        if len(parts) >= 2:
            return parts[-2].replace("-", " ").capitalize()
        return host
    except Exception:
        return ""

def get_source_name_from_feed(feed_obj, feed_url=""):
    """استخراج اسم المصدر من بيانات الـ feed أو من الـ URL"""
    try:
        feed_meta = getattr(feed_obj, 'feed', None)
        if feed_meta:
            feed_title = getattr(feed_meta, 'title', '')
            if feed_title and len(feed_title.strip()) > 1:
                clean = feed_title.strip().split('|')[0].split(' - ')[0].strip()
                if clean and len(clean) < 60:
                    return clean
    except Exception as _exc:
        _log_exc(_exc)
    return get_source_name_from_url(feed_url)

# ======== دوال الأخبار ========
