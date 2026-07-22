# -*- coding: utf-8 -*-
"""
  rss_validator.py — التحقق من صحة الـ feeds + auto-discover

  يُصدِّر دوال التحقق من صحة مصادر RSS واكتشافها تلقائياً.
  """

import sys as _sys_legacy
import os
# ─── استيراد كل المتغيرات العالمية من bot_legacy ───
from bot_legacy import *
import state as gl  # noqa: F401,F403
# FIX: استيراد صريح للأسماء الضرورية
from bot_legacy import _logger, _log_exc, _start_thread_once  # noqa: F811

def _validate_rss_feed(url):
    """يتحقق إذا كان الرابط RSS صالحاً ويُرجع True إذا تم تحليله بنجاح"""
    try:
        r = requests.get(url, timeout=8, headers={"User-Agent": "IraqNowBot/2.0"})
        if r.status_code != 200:
            return False
        feed = feedparser.parse(r.content)
        return bool(feed.entries)
    except Exception:
        return False

def _rss_auto_discover():
    """
    يعمل في خيط منفصل كل 12 ساعة.
    يجرّب مرشحَي RSS، يتحقق منهم، يضيف الصالح منهم للـ RSS dict.
    """
    import time as _time
    _time.sleep(60)  # انتظر دقيقة بعد بدء البوت قبل البدء
    while True:
        try:
            added_total = 0
            for lang, candidates in _RSS_CANDIDATES.items():
                checked = _rss_discovery_state.get(lang, [])
                for url in candidates:
                    if url in checked:
                        continue
                    if url in RSS.get(lang, []):
                        checked.append(url)
                        continue
                    if _validate_rss_feed(url):
                        if lang not in RSS:
                            RSS[lang] = []
                        if url not in RSS[lang]:
                            RSS[lang].append(url)
                            added_total += 1
                            _logger.info(f"🔍 RSS Discovery: أضفت مصدر جديد [{lang}]: {url}")
                    checked.append(url)
                    _rss_discovery_state[lang] = checked
                    _time.sleep(2)  # لا تضغط على الخوادم
            if added_total:
                save_rss()
                save_json(_RSS_DISCOVERY_STATE_FILE, _rss_discovery_state)
        except Exception as e:
            _logger.warning(f"⚠️ RSS Discovery error: {e}")
        _time.sleep(12 * 3600)  # كل 12 ساعة

import threading as _rss_disc_thread
_rss_disc_thread.Thread(target=_rss_auto_discover, daemon=True, name="RssDiscovery").start()

# ======== تحميل ودمج القنوات المخصصة (تيليغرام) ========
_custom_tg_channels = load_json(CUSTOM_TG_CHANNELS_FILE, {})
# ادمج القنوات المخصصة مع TELEGRAM_NEWS_CHANNELS
for _lang, _chs in _custom_tg_channels.items():
    if _lang not in TELEGRAM_NEWS_CHANNELS:
        TELEGRAM_NEWS_CHANNELS[_lang] = []
    _existing_handles = {c["handle"] for c in TELEGRAM_NEWS_CHANNELS[_lang]}
    for _ch in _chs:
        if _ch["handle"] not in _existing_handles:
            TELEGRAM_NEWS_CHANNELS[_lang].append(_ch)
            _existing_handles.add(_ch["handle"])

def _auto_discover_rss(url):
    """
    يكتشف رابط RSS من موقع ويب تلقائياً.
    يجرب أنماطاً شائعة مثل /feed, /rss, /rss.xml, /?feed=rss2 ...
    يعيد رابط RSS الصالح أو None إذا فشل.
    """
    if not url.startswith("http"):
        url = "https://" + url
    # إذا الرابط نفسه يبدو وكأنه RSS — تحقق منه مباشرة
    rss_patterns_suffix = ('.rss', '.xml', '/feed', '/rss', 'feed=rss', 'rss2', '/atom')
    is_direct = any(p in url.lower() for p in rss_patterns_suffix)
    candidates = [url] if is_direct else []
    # أضف أنماطاً قياسية
    base = url.rstrip('/')
    candidates += [
        f"{base}/feed",
        f"{base}/rss",
        f"{base}/rss.xml",
        f"{base}/feed.xml",
        f"{base}/index.xml",
        f"{base}/?feed=rss2",
        f"{base}/feeds/posts/default",
        f"{base}/atom.xml",
        f"{base}/news.rss",
    ]
    headers = {"User-Agent": "Mozilla/5.0 (compatible; NewsBot/1.0; +https://t.me/IraqnowBot)"}
    for cand in candidates:
        try:
            r = requests.head(cand, timeout=5, headers=headers, allow_redirects=True)
            if r.status_code == 200:
                ct = r.headers.get("Content-Type", "")
                if any(x in ct for x in ("xml", "rss", "atom", "feed")):
                    return cand
            # إذا HEAD لم يُخبرنا، جرّب feedparser مباشرة
            parsed = feedparser.parse(cand)
            if parsed.entries and len(parsed.entries) > 0:
                return cand
        except Exception as _exc:
            _log_exc(_exc)
    # محاولة أخيرة: ابحث عن رابط RSS في صفحة الموقع الرئيسية
    if not is_direct:
        try:
            r = requests.get(base, timeout=8, headers=headers)
            if r.status_code == 200 and _BS4_AVAILABLE:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(r.text, 'html.parser')
                for link_tag in soup.find_all('link', type=lambda t: t and ('rss' in t or 'atom' in t)):
                    href = link_tag.get('href', '')
                    if href:
                        if href.startswith('/'):
                            from urllib.parse import urlparse
                            parsed_url = urlparse(base)
                            href = f"{parsed_url.scheme}://{parsed_url.netloc}{href}"
                        return href
        except Exception as _exc:
            _log_exc(_exc)
    return None


def _validate_rss_sources():
    """يفحص كل مصادر RSS ليلاً ويُبلّغ الأدمن بالمصادر المعطوبة"""
    broken = {}
    headers = {"User-Agent": "Mozilla/5.0 (compatible; NewsBot/1.0)"}
    for lang, feeds in RSS.items():
        for url in feeds:
            try:
                parsed = feedparser.parse(url)
                if not parsed.entries:
                    broken.setdefault(lang, []).append(url)
            except Exception:
                broken.setdefault(lang, []).append(url)
    if broken:
        msg = "⚠️ *تقرير المصادر المعطوبة (فحص ليلي):*\n\n"
        for lang, urls in broken.items():
            msg += f"*{lang}:*\n" + "\n".join(f"• `{u}`" for u in urls) + "\n\n"
        msg += "يمكنك حذفها من لوحة الإدارة ← RSS."
        for admin_id in ADMINS:
            try:
                bot.send_message(admin_id, msg, parse_mode="Markdown")
            except Exception as _exc:
                _log_exc(_exc)
    else:
        _logger.info("✅ فحص ليلي: جميع مصادر RSS تعمل بشكل صحيح")


# ======== نشرة مسائية للأخبار العاجلة ========
# تُذكّر المستخدمين بأبرز الأخبار العاجلة عند المساء (18:00)
_evening_recap_sent = {}   # uid -> date_str (لمنع الإرسال المزدوج)

def _enhanced_rss_discovery():
    """
    اكتشاف مصادر RSS بشكل متوازٍ وسريع — لا يؤثر على البث.
    يعمل مرة يومياً فقط في الساعة 5 صباحاً.
    """
    from concurrent.futures import ThreadPoolExecutor as _TPE2, as_completed as _ac2

    _COMMON_RSS_PATHS = [
        '/feed', '/rss', '/rss.xml', '/feed.xml', '/atom.xml',
        '/news/rss', '/en/rss', '/ar/rss', '/?feed=rss2',
    ]

    _SEED_DOMAINS = {
        'العربية 🇮🇶': [
            'https://www.aljazeera.net', 'https://arabic.rt.com',
            'https://www.bbc.com/arabic', 'https://www.skynewsarabia.com',
            'https://www.france24.com/ar', 'https://www.dw.com/ar',
            'https://shafaq.com', 'https://www.rudaw.net/arabic',
        ],
        'English 🇬🇧': [
            'https://www.reuters.com', 'https://apnews.com',
            'https://www.bbc.com/news', 'https://www.aljazeera.com',
            'https://www.france24.com/en', 'https://www.middleeasteye.net',
        ],
        'Русский 🇷🇺': ['https://ria.ru', 'https://tass.ru', 'https://lenta.ru'],
        'Türkçe 🇹🇷': ['https://www.trthaber.com', 'https://www.aa.com.tr'],
        'فارسی 🇮🇷':  ['https://www.irna.ir', 'https://www.isna.ir'],
        'Deutsch 🇩🇪': ['https://www.dw.com/de', 'https://www.tagesschau.de'],
        'Español 🇲🇽': ['https://elpais.com', 'https://www.bbc.com/mundo'],
        'Français 🇫🇷': ['https://www.france24.com/fr', 'https://www.rfi.fr'],
        'Português 🇧🇷': ['https://www.bbc.com/portuguese', 'https://www.dw.com/pt-br'],
        'Italiano 🇮🇹': ['https://www.ansa.it', 'https://www.dw.com/it'],
        'Українська 🇺🇦': ['https://www.ukrinform.ua', 'https://www.bbc.com/ukrainian'],
        'اردو 🇵🇰': ['https://www.bbc.com/urdu', 'https://www.geo.tv/urdu'],
        'हिन्दी 🇮🇳': ['https://www.bbc.com/hindi', 'https://www.dw.com/hi'],
    }

    added_total = 0

    def _check_one(lang, domain, path):
        """يجرب مسار RSS واحد — يُعيد URL إذا صالح وإلا None."""
        candidate = domain.rstrip('/') + path
        existing  = RSS.get(lang, [])
        if candidate in existing:
            return None
        try:
            parsed = feedparser.parse(candidate)
            if parsed.entries and len(parsed.entries) >= 2:
                return (lang, candidate)
        except Exception:
            pass
        return None

    # تشغيل متوازٍ — 10 خيوط فقط حتى لا نضغط على النظام
    tasks = [
        (lang, domain, path)
        for lang, domains in _SEED_DOMAINS.items()
        for domain in domains
        for path in _COMMON_RSS_PATHS
        if domain.rstrip('/') + path not in RSS.get(lang, [])
    ]

    # نخلط القائمة لتجنب التحيز لنفس المصادر
    import random as _rnd
    _rnd.shuffle(tasks)
    # نحدّ بـ 100 طلب كحد أقصى لكل دورة
    tasks = tasks[:100]

    with _TPE2(max_workers=4, thread_name_prefix="RSSDiscover") as _pool:  # HEROKU: حد 4 خيوط
        futs = {_pool.submit(_check_one, *t): t for t in tasks}
        for fut in _ac2(futs, timeout=120):  # timeout كلي 2 دقيقة
            try:
                result = fut.result()
                if result:
                    lang2, url2 = result
                    if url2 not in RSS.get(lang2, []):
                        RSS.setdefault(lang2, []).append(url2)
                        added_total += 1
                        _logger.info("🔍 RSS Discovery: +%s [%s]", url2, lang2[:10])
            except Exception:
                pass

    if added_total > 0:
        save_rss()
        _logger.info("✅ Enhanced Discovery: +%d مصدر جديد", added_total)
        try:
            bot.send_message(ADMIN_ID,
                f"🔍 *RSS Discovery*: أضاف `{added_total}` مصدر جديد",
                parse_mode="Markdown")
        except Exception:
            pass


def _ai_auto_discover_feeds():
    """
    يستخدم Gemini للبحث عن مصادر RSS جديدة لكل لغة ويضيفها تلقائياً.
    - يغطي كل لغات المستخدمين الحاليين + يقترح لغات جديدة.
    - يختبر كل رابط قبل إضافته (feedparser validation).
    - يُسجّل الروابط المُضافة ويبلغ الأدمن بالنتيجة.
    """
    if not _AI_AVAILABLE or not _AI_MODEL:
        return

    # جمع اللغات الحالية + اللغات العالمية المطلوبة
    active_langs = list(set(
        info.get("lang", "") for info in users.values()
        if info.get("lang") and info.get("active", True)
    ))
    # اللغات العالمية الأساسية التي يجب تغطيتها دائماً
    global_langs_map = {
        "العربية 🇮🇶": "Arabic",
        "English 🇬🇧": "English",
        "Русский 🇷🇺": "Russian",
        "فارسی 🇮🇷": "Persian",
        "हिन्दी 🇮🇳": "Hindi",
        "Português 🇧🇷": "Portuguese",
        "Türkçe 🇹🇷": "Turkish",
        "اردو 🇵🇰": "Urdu",
        "Deutsch 🇩🇪": "German",
        "Українська 🇺🇦": "Ukrainian",
        "Italiano 🇮🇹": "Italian",
        "Español 🇲🇽": "Spanish",
        "Français 🇫🇷": "French",
    }
    headers_req = {"User-Agent": "Mozilla/5.0 (compatible; InsightXBot/2.0)"}
    added_total = 0
    report_lines = ["🤖 *تقرير الاكتشاف التلقائي للمصادر*\n"]

    for bot_lang, eng_name in global_langs_map.items():
        existing_feeds = RSS.get(bot_lang, [])
        existing_count = len(existing_feeds)
        # نطلب من Gemini 8 مصادر جديدة غير موجودة
        existing_sample = existing_feeds[:10]
        try:
            prompt = (
                f"Give me exactly 8 real working RSS feed URLs for top news websites in {eng_name} language. "
                f"These should be DIFFERENT from: {existing_sample}. "
                f"Only return raw URLs, one per line, no explanations, no numbering. "
                f"Only return URLs that end in /feed, /rss, /rss.xml, .rss, .xml, or similar RSS paths. "
                f"Focus on major international/national news agencies and newspapers."
            )
            _response_ai = _ai_generate(prompt)
            resp = (_response_ai or "")
            if not resp:
                continue
            candidate_urls = [u.strip() for u in resp.splitlines() if u.strip().startswith("http")]
        except Exception as e:
            _logger.warning(f"Auto-discover Gemini error for {bot_lang}: {e}")
            continue

        added_for_lang = 0
        for url in candidate_urls[:10]:
            if url in existing_feeds:
                continue
            # اختبر الرابط
            try:
                parsed = feedparser.parse(url)
                if parsed.entries and len(parsed.entries) >= 1:
                    RSS.setdefault(bot_lang, []).append(url)
                    _ai_discovered_log.setdefault(bot_lang, []).append(url)
                    added_for_lang += 1
                    added_total += 1
                else:
                    # جرّب اكتشاف RSS من الموقع نفسه
                    discovered = _auto_discover_rss(url)
                    if discovered and discovered not in existing_feeds:
                        parsed2 = feedparser.parse(discovered)
                        if parsed2.entries:
                            RSS.setdefault(bot_lang, []).append(discovered)
                            _ai_discovered_log.setdefault(bot_lang, []).append(discovered)
                            added_for_lang += 1
                            added_total += 1
            except Exception as _exc:
                _log_exc(_exc)

        if added_for_lang > 0:
            report_lines.append(f"✅ {bot_lang}: +{added_for_lang} مصدر جديد (الإجمالي: {existing_count + added_for_lang})")

    if added_total > 0:
        save_rss()
        save_json(_AI_DISCOVERED_RSS_FILE, _ai_discovered_log)
        report_lines.append(f"\n📊 المجموع المُضاف: *{added_total}* مصدر جديد")
        report = "\n".join(report_lines)
        for admin_id in ADMINS:
            try:
                bot.send_message(admin_id, report, parse_mode="Markdown")
            except Exception as _exc:
                _log_exc(_exc)
        _logger.info("✅ AI Auto-Discovery: أضاف %d مصدر RSS جديد", added_total)
    else:
        _logger.info("ℹ️ AI Auto-Discovery: لم يُضف مصادر جديدة في هذه الجولة")


scheduler.add_job(_safe_job(send_daily_report), 'cron', hour=8, minute=0)  # FIX: added _safe_job wrapper
scheduler.add_job(_safe_job(send_rating_request), 'cron', hour=20, minute=0, max_instances=1, coalesce=True)
scheduler.add_job(_safe_job(reset_daily_rating_flags), 'cron', hour=0, minute=0, max_instances=1, coalesce=True)
scheduler.add_job(_safe_job(check_inactive_users), 'cron', hour=10, minute=0, max_instances=1, coalesce=True)
scheduler.add_job(_safe_job(check_summary_hint), 'interval', hours=12, max_instances=1, coalesce=True)
scheduler.add_job(_safe_job(auto_backup), 'interval', hours=3, id="auto_backup_job")  # HEROKU FIX v3: 3h
scheduler.add_job(_safe_job(send_evening_recap), 'cron', hour=18, minute=0, max_instances=1, coalesce=True)
scheduler.add_job(_safe_job(_validate_rss_sources), 'cron', hour=3, minute=0, max_instances=1, coalesce=True)
# اكتشاف مصادر تلقائي: AI كل 24 ساعة + validate كل 12 ساعة
# ملاحظة: تعمل في أوقات محددة حتى لا تؤثر على البث
scheduler.add_job(_safe_job(_ai_auto_discover_feeds), 'cron', hour=3, minute=0, id='ai_discover_job', max_instances=1, coalesce=True)
scheduler.add_job(_safe_job(_enhanced_rss_discovery), 'cron', hour=5, minute=0, id='enhanced_discover_job', max_instances=1, coalesce=True)
scheduler.add_job(_safe_job(send_weekly_summary),  'cron', day_of_week='fri', hour=10, minute=0, max_instances=1, coalesce=True)

# ======== /addtrack ========
def _rss_health_check_loop():
    """يُراقب كل مصادر RSS في الخلفية كل 30 دقيقة."""
    import feedparser
    while True:
        try:
            all_urls = set()
            for feeds in RSS.values():
                all_urls.update(feeds)
            for url in all_urls:
                try:
                    start = time.time()
                    feed  = feedparser.parse(url)
                    elapsed = (time.time() - start) * 1000
                    if not feed or not feed.entries:
                        status = "dead"
                    elif elapsed > 10000:
                        status = "slow"
                    else:
                        status = "ok"
                    with _RSS_HEALTH_LOCK:
                        _rss_health[url] = {"status": status, "latency": int(elapsed), "last_check": time.time()}
                except Exception:
                    with _RSS_HEALTH_LOCK:
                        _rss_health[url] = {"status": "dead", "latency": -1, "last_check": time.time()}
                time.sleep(1)
        except Exception as _exc:
            _log_exc(_exc)
        time.sleep(1800)   # كل 30 دقيقة

_start_thread_once("RSSHealthMonitor", _rss_health_check_loop)


# ── 1c. Database Bloat Protection ─────────────────────────────────────────
