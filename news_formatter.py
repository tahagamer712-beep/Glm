# -*- coding: utf-8 -*-
"""
  news_formatter.py — تنسيق الخبر + escape markdown + OG image + وقت النشر

  يُصدِّر دوال تنسيق الأخبار وعرضها.
  """

import sys as _sys_legacy
import os
# ─── استيراد كل المتغيرات العالمية من bot_legacy ───
from bot_legacy import *
import state as gl  # noqa: F401,F403

# FIX: _get_og_image (طلب شبكة لجلب og:image لزر "صورة المقال") أُزيلت — لم تعد
# مستخدمة بعد إزالة الزر؛ صورة الخبر تُستخرج الآن مباشرة من بيانات RSS نفسها
# (انظر rss_fetcher._extract_entry_image) بدون أي طلب شبكة إضافي.

def _normalize_news_link(url: str) -> str:
    """
    تطبيع رابط الخبر لمنع التكرار بسبب طوابع زمنية/معاملات URL مختلفة.
    مثال: https://site.com/news?t=123&utm_source=tg → https://site.com/news
    """
    if not url:
        return url
    try:
        import urllib.parse as _up2
        p = _up2.urlparse(url.strip())
        # إبقاء fragment فقط إذا كان جزءاً حقيقياً من المسار (مقالات SPA)
        clean = _up2.urlunparse((p.scheme, p.netloc, p.path.rstrip('/'), '', '', ''))
        return clean.lower() if clean else url
    except Exception:
        return url

# ======== Edge TTS — تحويل الأخبار إلى صوت ========
def _format_pub_time(pub_dt, lang=None):
    """
    يُحوّل وقت النشر UTC إلى نص بسيط بلغة المستخدم.
    يحسب الفرق من لحظة الاستدعاء.
    إذا كان pub_dt فارغاً يُعرض "منذ لحظات" لأن الخبر اجتاز فلتر الحداثة.
    """
    if pub_dt is None:
        patterns = _PUB_TIME_I18N.get(lang) or _PUB_TIME_I18N["العربية 🇮🇶"]
        return f"🕐 {patterns[0]}"
    try:
        now_utc  = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
        diff_min = int((now_utc - pub_dt).total_seconds() / 60)
        if diff_min < 0:
            diff_min = 0

        # اختر نمط اللغة أو العربية كاحتياطي
        patterns = _PUB_TIME_I18N.get(lang) or _PUB_TIME_I18N["العربية 🇮🇶"]
        just_now_txt, min_fmt, hr_fmt = patterns

        if diff_min < 2:
            label = just_now_txt
        elif diff_min < 60:
            label = min_fmt.format(diff_min)
        elif diff_min < 1440:
            label = hr_fmt.format(diff_min // 60)
        else:
            # تاريخ بالتوقيت المحلي للمستخدم (العراق UTC+3)
            local_dt = pub_dt + datetime.timedelta(hours=3)
            label = local_dt.strftime("%d/%m %H:%M")

        return f"🕐 {label}"
    except Exception:
        return ""
# ======== ذاكرة تخزين مؤقت عالمية لـ RSS ========
# FIX: المتغيرات الثلاثة نُقلت إلى bot_legacy.py (مكان كل المتغيرات العالمية المشتركة).
#      هذا الملف يحصل عليها عبر `from bot_legacy import *` المُنفَّذة أعلاه.
#      لا تُعيد تعريفها هنا — التعريف المزدوج يكسر مشاركة الكائن الواحد بين الوحدات.


def _cache_summary(link, summary_text, title=""):
    """تخزين ملخص الخبر مع مفتاح MD5 مختصر."""
    key = hashlib.md5(link.encode("utf-8")).hexdigest()[:16]
    if len(_news_summary_cache) > 5000:
        oldest = list(_news_summary_cache.keys())[:500]
        for k in oldest:
            del _news_summary_cache[k]
    _news_summary_cache[key] = {"text": summary_text, "title": title}
    _save_button_cache("sum", {key: _news_summary_cache[key]})
    return key

def _clean_html(text):
    """إزالة وسوم HTML والروابط من الملخص."""
    import re
    text = re.sub(r'<[^>]+>', '', text or '')
    text = text.replace('&nbsp;', ' ').replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>').replace('&quot;', '"').replace('&#39;', "'")
    # حذف روابط t.me وURLs عامة من الملخص
    text = re.sub(r'https?://t\.me/\S*', '', text)
    text = re.sub(r'https?://\S+', '', text)
    # حذف @mention للقنوات
    text = re.sub(r'@[A-Za-z0-9_]{3,}', '', text)
    # حذف سطر "المصدر:" أو نحوه
    text = re.sub(r'(المصدر|Source|via|©|حصري)[^\n]*', '', text, flags=re.IGNORECASE)
    # تنظيف مسافات زائدة
    text = re.sub(r'\s{3,}', ' ', text)
    return text.strip()

def _pub_dt_from_item(item):
    """استخراج pub_dt من feedparser item."""
    pub_struct = (getattr(item, 'published_parsed', None)
                  or getattr(item, 'updated_parsed', None))
    if pub_struct:
        try:
            import calendar as _cal
            return datetime.datetime.utcfromtimestamp(_cal.timegm(pub_struct))
        except Exception as _exc:
            _log_exc(_exc)
    return None

# ======== قاموس أسماء المصادر ========
SOURCE_NAMES = {
    "alsumaria.tv": "السومرية",
    "shafaq.com": "شفق نيوز",
    "rudaw.net": "رووداو",
    "almaalomah.com": "المعلومة",
    "almada-paper.com": "المدى",
    "almadapaper.net": "المدى",
    "baghdadtoday.news": "بغداد اليوم",
    "ina.iq": "وكالة الأنباء العراقية",
    "buratha.com": "بوابة برثا",
    "mawazin.net": "موازين",
    "non14.net": "نون14",
    "aliraqnews.com": "الأخبار العراقية",
    "kitabat.com": "كتابات",
    "lvinpress.com": "لفين برس",
    "xebat.net": "خه بات",
    "nasiriyah.org": "ناصرية",
    "azzaman.com": "الزمان",
    "almasalah.com": "المصالح",
    "basnews.com": "باس نيوز",
    "alsharqiya.com": "قناة الشرقية",
    "sotaliraq.com": "صوت العراق",
    "imn.iq": "قناة العراقية",
    "mangish.net": "منكيش نت",
    "alarabiya.net": "العربية",
    "bbc.com": "بي بي سي",
    "bbc.co.uk": "بي بي سي",
    "aljazeera.net": "الجزيرة",
    "aljazeera.com": "الجزيرة",
    "skynewsarabia.com": "سكاي نيوز عربية",
    "rt.com": "روسيا اليوم",
    "independentarabia.com": "إندبندنت عربية",
    "france24.com": "فرانس 24",
    "euronews.com": "يورونيوز",
    "arabi21.com": "عربي 21",
    "middleeasteye.net": "ميدل إيست آي",
    "aawsat.com": "الشرق الأوسط",
    "almayadeen.net": "الميادين",
    "alhurra.com": "الحرة",
    "aa.com.tr": "الأناضول",
    "asharq.com": "الشرق",
    "raialyoum.com": "رأي اليوم",
    "noonpost.com": "نون بوست",
    "arabicpost.net": "ذا عربي بوست",
    "almasryalyoum.com": "المصري اليوم",
    "youm7.com": "اليوم السابع",
    "alquds.com": "القدس",
    "reuters.com": "رويترز",
    "nytimes.com": "نيويورك تايمز",
    "washingtonpost.com": "واشنطن بوست",
    "theguardian.com": "الغارديان",
    "cnn.com": "CNN",
    "apnews.com": "أسوشيتد برس",
    "dw.com": "DW",
    "hurriyet.com.tr": "حرييت",
    "sabah.com.tr": "صباح",
    "trtworld.com": "TRT World",
    "geo.tv": "جيو نيوز",
    "jang.com.pk": "جانج",
    # قنوات تلغرام
    "t.me/StevenNabilIraq": "ستيفن نبيل العراق",
    "t.me/baghdad7city": "بغداد سيتي",
    "t.me/iraq11e": "عراق نيوز",
    "t.me/iraqi1_news": "أخبار العراق 1",
    "t.me/iraqi1news": "شبكة أخبار العراق",
    "t.me/Iraqi1news": "شبكة أخبار العراق",
    "t.me/Iraq_now3": "عراق ناو",
    "t.me/iraqnow3": "عراق ناو",
    "t.me/RN24_IQ": "راديو نوا 24 عراق",
    "t.me/alsbaahiq": "الصباح العراقية",
    "t.me/inainaiq": "وكالة الأنباء العراقية",
    "t.me/IraqiMediaNet": "شبكة الإعلام العراقية",
    "t.me/alhadath_TV": "الحدث العراق",
    "t.me/AlHadathNews": "الحدث العراق",
    "t.me/AlRaedNews": "الرائد نيوز",
    "t.me/IraqNewsCh": "قناة أخبار العراق",
    "t.me/baghdad_breaking": "بغداد عاجل",
    "t.me/iraqbreaking": "عراق عاجل",
    "t.me/IraqBreakingNews": "عراق عاجل",
    "t.me/alsumariaTVNews": "السومرية نيوز",
    "t.me/AlSumaria": "السومرية",
    "t.me/alforatnews": "الفرات نيوز",
    "t.me/AlFurqan_1": "الفرقان",
    "t.me/AlAhad_TV": "الأحد نيوز",
    "t.me/mosulnews": "موصل نيوز",
    "t.me/basranews": "البصرة نيوز",
    "t.me/kurdistan_news": "كردستان نيوز",
}

# أسماء قنوات تلغرام للعرض السريع
_TG_CHANNEL_NAMES = {ch["handle"]: ch["name"]
                     for channels in TELEGRAM_NEWS_CHANNELS.values()
                     for ch in channels}

def escape_md(text):
    """
    FIX-5: يُزيل HTML entities أولاً ثم يُهرِّب رموز Markdown.
    يمنع تشويه الرسائل من عناوين تحتوي &amp; أو <b> إلخ.
    """
    if not text:
        return ""
    import html as _html, re as _re_esc
    text = _html.unescape(str(text))
    text = _re_esc.sub(r'<[^>]+>', '', text)
    return (text
        .replace('*', '\u2217')
        .replace('_', '\u2019')
        .replace('`', "'")
        .replace('[', '(')
        .replace(']', ')')
    )

# ── لاصقة "آخر الأخبار" لكل لغة (تُستخدم في البث التلقائي) ──────────────
_LABEL_LATEST = {
    "العربية 🇮🇶": "آخر الأخبار",
    "English 🇬🇧":  "Latest News",
    "Русский 🇷🇺":  "Последние новости",
    "فارسی 🇮🇷":   "آخرین اخبار",
    "हिंदी 🇮🇳":    "ताज़ा खबर",
    "Español 🇪🇸":  "Últimas noticias",
    "Türkçe 🇹🇷":  "Son Haberler",
    "اردو 🇵🇰":    "تازہ خبریں",
    "Français 🇫🇷": "Dernières nouvelles",
    "Deutsch 🇩🇪":  "Aktuelle Nachrichten",
    "中文 🇨🇳":     "最新新闻",
    "日本語 🇯🇵":   "最新ニュース",
}

_DEFAULT_NEWS_LABEL = "🚨 خبر عاجل"


# ======== 🧠 IQ الخبر — مؤشر ذكاء الخبر ========
_CREDIBLE_SOURCES = [
    "rudaw.net","shafaq.com","alsumaria.tv","aljazeera.net","bbc","reuters",
    "apnews.com","france24","sky","cnn","alhadath","almaalomah","al-monitor",
    "almada","aswataliraq","iraqnews","niqash","buratha","kitabat",
]

_IQ_LEVEL_LABELS = {
    # (exceptional, high, medium, normal)
    "العربية 🇮🇶":   ("استثنائي", "عالٍ",        "متوسط",     "عادي"),
    "English 🇬🇧":   ("Exceptional","High",        "Medium",    "Normal"),
    "Русский 🇷🇺":   ("Исключит.", "Высокий",     "Средний",   "Обычный"),
    "فارسی 🇮🇷":     ("استثنایی",  "بالا",         "متوسط",     "عادی"),
    "हिन्दी 🇮🇳":    ("असाधारण",   "उच्च",         "मध्यम",     "सामान्य"),
    "Português 🇧🇷": ("Excepcional","Alto",        "Médio",     "Normal"),
    "Türkçe 🇹🇷":   ("İstisnaî",  "Yüksek",      "Orta",      "Normal"),
    "اردو 🇵🇰":     ("غیر معمولی","اعلی",         "درمیانہ",   "عام"),
    "Deutsch 🇩🇪":  ("Außergewöhnl.","Hoch",      "Mittel",    "Normal"),
    "Українська 🇺🇦":("Винятковий","Високий",     "Середній",  "Звичайний"),
    "Italiano 🇮🇹": ("Eccezionale","Alto",        "Medio",     "Normale"),
    "Español 🇲🇽":  ("Excepcional","Alto",        "Medio",     "Normal"),
    "Français 🇫🇷": ("Exceptionnel","Élevé",      "Moyen",     "Normal"),
}
_IQ_IMPACT_LABELS = {
    # (regional, local, general)
    "العربية 🇮🇶":   ("🌍 إقليمي",  "🏛️ محلي",  "📋 عام"),
    "English 🇬🇧":   ("🌍 Regional","🏛️ Local", "📋 General"),
    "Русский 🇷🇺":   ("🌍 Регион.", "🏛️ Местн.","📋 Общее"),
    "فارسی 🇮🇷":     ("🌍 منطقهای","🏛️ محلی",   "📋 عمومی"),
    "हिन्दी 🇮🇳":    ("🌍 क्षेत्रीय","🏛️ स्थानीय","📋 सामान्य"),
    "Português 🇧🇷": ("🌍 Regional","🏛️ Local", "📋 Geral"),
    "Türkçe 🇹🇷":   ("🌍 Bölgesel","🏛️ Yerel",  "📋 Genel"),
    "اردو 🇵🇰":     ("🌍 علاقائی", "🏛️ مقامی", "📋 عام"),
    "Deutsch 🇩🇪":  ("🌍 Regional","🏛️ Lokal",  "📋 Allgemein"),
    "Українська 🇺🇦":("🌍 Регіон.", "🏛️ Місц.", "📋 Загальне"),
    "Italiano 🇮🇹": ("🌍 Regionale","🏛️ Locale","📋 Generale"),
    "Español 🇲🇽":  ("🌍 Regional","🏛️ Local",  "📋 General"),
    "Français 🇫🇷": ("🌍 Régional","🏛️ Local",  "📋 Général"),
}

def format_news_item(prefix, title, lang=None, source_name=None, pub_time_str=None, summary=None):
  """
  شكل الخبر المطابق للتصميم المطلوب:
  📰 🗞️ عنوان الخبر
  ━━━━━━━━━━━━━━━━━━
  آخر الأخبار 🗞️ · اسم المصدر 🗞️ · منذ لحظات 🕐
  ━━━━━━━━━━━━━━━━━━
  نص/ملخص الخبر
  لا تنسى المشاركة @Iraqnowbot
  """
  separator = "━━━━━━━━━━━━━━━━━━"
  safe_title = escape_md(title)

  # ── السطر الأول: عنوان الخبر مع أيقونة ──────────────────
  result = f"📰 🗞️ *{safe_title}*\n{separator}"

  # ── سطر المعلومات: التسمية + المصدر + الوقت ─────────────
  meta_parts = []
  custom_label = news_settings.get("label", _DEFAULT_NEWS_LABEL)
  _is_custom_label = (custom_label != _DEFAULT_NEWS_LABEL)
  if _is_custom_label:
      # يستخدم الترجمة المحفوظة لهذه اللغة إن وجدت، وإلا يبقى العربي الأصلي
      _label_i18n = news_settings.get("label_i18n", {})
      label = _label_i18n.get(lang, custom_label) if lang else custom_label
  else:
      label = prefix  # prefix هو المترجم عبر t(lang, "label_breaking") وما شابهه
  meta_parts.append(f"{label} 🗞️")
  if source_name:
      meta_parts.append(f"{escape_md(source_name)} 🗞️")
  if pub_time_str:
      meta_parts.append(f"{pub_time_str} 🕐")
  if meta_parts:
      result += "\n" + "  ·  ".join(meta_parts)

  result += f"\n{separator}"

  # ── ملخص/نص الخبر ────────────────────────────────────────
  if summary:
      clean_snip = _clean_html(summary)
      # لا نعرض الملخص إذا كان نفس العنوان أو أقصر من 30 حرف
      _title_norm = title.strip()[:80].lower()
      _snip_norm  = clean_snip.strip()[:80].lower() if clean_snip else ""
      _is_same    = _snip_norm and (_snip_norm == _title_norm or _title_norm in _snip_norm or _snip_norm in _title_norm)
      if clean_snip and len(clean_snip) > 30 and not _is_same:
          snip = clean_snip[:300].rsplit(' ', 1)[0] + '…' if len(clean_snip) > 300 else clean_snip
          result += f"\n\n{escape_md(snip)}"

  # ── التوقيع (Powered by InsightX) — مترجم حسب اللغة، محترم لإعدادات المدير ──
  _sig_block = get_news_signature(lang)  # يُرجع "\n{sep}\n{sig}"
  result += f"\n{_sig_block}"
  return result

def make_news_share_markup(link, title="", lang="العربية 🇮🇶", summary=""):
    """
    أزرار الخبر — كل زر في سطر منفصل:
    🔗 فتح الخبر        ← يفتح المقال مباشرةً (url)
    📩 شارك الخبر       ← يشارك الرابط عبر تيليغرام
    📄 ملخص الخبر
    🔔 تابع هذه القصة
    🔍 تحقق من الخبر
    🤖 شارك البوت @Iraqnowbot
    """
    import urllib.parse, hashlib as _hs

    markup = types.InlineKeyboardMarkup(row_width=1)

    # ── إعداد روابط المشاركة ────────────────────────────────────────
    _lnk_lower = (link or "").lower()
    is_valid_url = _lnk_lower.startswith("http://") or _lnk_lower.startswith("https://")
    is_tg_link   = "t.me/" in _lnk_lower or "telegram.me/" in _lnk_lower

    # ── تحميل نصوص الأزرار المترجمة حسب لغة المستخدم ────────────────
    _L = NEWS_SHARE_LABELS.get(lang) or NEWS_SHARE_LABELS.get("English 🇬🇧")

    via_txt      = _L.get("via", "via")
    promo_txt    = _L.get("bot_promo", "InsightX — AI News Bot")

    # ── استخراج اسم المصدر من الرابط ────────────────────────────────
    _src_name_share = ""
    for _dom, _nm in SOURCE_NAMES.items():
        if _dom in (link or "").lower():
            _src_name_share = _nm
            break

    # ── بناء نص المشاركة: عنوان + مصدر + ملخص + رابط + توقيع ────────
    _clean_sum_share = _clean_html(summary)[:250].strip() if summary else ""
    _share_parts = []
    if title:
        _share_parts.append(f"📰 {title[:120]}")
    if _src_name_share:
        _share_parts.append(f"📡 {_src_name_share}")
    if _clean_sum_share:
        _share_parts.append(f"\n{_clean_sum_share}")
    # FIX: حذف سطر الرابط الخام من نص المشاركة بناءً على طلب المستخدم —
    # الرابط يبقى مضمَّناً بخاصية url المشاركة نفسها (share_url) بدون عرضه كنص
    _share_parts.append(f"✨ {via_txt} @{BOT_USERNAME}")
    share_text = "\n".join(p for p in _share_parts if p)
    # FIX: لا نُمرِّر url= إطلاقاً — تيليغرام يُلحِق قيمة url تلقائياً بالرسالة
    # المُرسَلة عبر شاشة المشاركة حتى لو حُذف الرابط من النص، فيظهر الرابط
    # الخام رغم أننا أزلناه من share_text. نُمرِّر فقط text= لضمان عدم ظهوره أبداً.
    share_url    = f"https://t.me/share/url?text={urllib.parse.quote(share_text, safe='')}"
    bot_link     = f"https://t.me/{BOT_USERNAME}"
    _bot_share_txt = f"✨ InsightX @{BOT_USERNAME}\n{promo_txt}"
    bot_share_u  = f"https://t.me/share/url?url={urllib.parse.quote(bot_link, safe='')}&text={urllib.parse.quote(_bot_share_txt, safe='')}"

    # ── زر 0: صورة المقال (لوكالات الأخبار) / فتح في تيليغرام (للقنوات) ──
    if is_tg_link and is_valid_url and link:
        # استخراج اسم القناة من الرابط لعرضه بدلاً من "فتح في تلغرام"
        _tg_handle = ""
        try:
            _tg_parts = link.rstrip('/').split('t.me/')
            if len(_tg_parts) > 1:
                _tg_handle = "@" + _tg_parts[1].split('/')[0].lstrip('@')
        except Exception as _exc:
            _log_exc(_exc)
        _tg_btn_txt = f"📢 {_tg_handle}" if _tg_handle else "📢"
        markup.add(types.InlineKeyboardButton(_tg_btn_txt, url=link))
    # FIX: زر "صورة المقال" أُزيل — صورة الخبر تُرسَل مباشرة مع نص الخبر (عبر
    # bot.send_photo) عندما تكون متوفرة جاهزة في مصدر RSS نفسه، بدون طلب شبكة
    # إضافي وبدون حاجة لزر منفصل. راجع news_broadcaster.py/handler_news.py.

    # ── زر 1: شارك الخبر 📤 ────────────────────────────────────────
    if is_valid_url and link:
        markup.add(types.InlineKeyboardButton(_L.get("share_news", "📤 Share"), url=share_url))
    else:
        markup.add(types.InlineKeyboardButton(_L.get("share_news", "📤 Share"), url=bot_link))

    # ── زر 2: ملخص الخبر 📄 ────────────────────────────────────────
    clean_summary = _clean_html(summary) if summary else ""
    _is_real_summary = (
        clean_summary
        and len(clean_summary) > 30
        and clean_summary.strip()[:60].lower() != (title or "").strip()[:60].lower()
    )
    if _is_real_summary and link and _feat_ok("summary"):
        sum_key = _cache_summary(link, clean_summary, title=title)
        markup.add(types.InlineKeyboardButton(_L.get("summary_btn", "📄 Summary"), callback_data=f"sum_{sum_key}"))

    # ── زر 3: تابع هذه القصة 🔔 ────────────────────────────────────
    if title:
        story_key = _hs.md5((link or title).encode("utf-8")).hexdigest()[:16]
        kw = title[:40].rsplit(' ', 1)[0] if len(title) > 40 else title
        if len(_story_key_cache) > 3000:
            for _sk in list(_story_key_cache.keys())[:300]:
                del _story_key_cache[_sk]
        _story_key_cache[story_key] = kw
        _save_button_cache("story", {story_key: kw})
        # الزر محذوف (follow_story) — نحتفظ بالـ cache للتوافق العكسي

    # ── زر 4: تحقق من الخبر 🔍 ────────────────────────────────────
    if title:
        fc_key = _hs.md5(title.encode("utf-8")).hexdigest()[:16]
        if len(_factcheck_key_cache) > 3000:
            for _ok in list(_factcheck_key_cache.keys())[:300]:
                del _factcheck_key_cache[_ok]
        is_new_key = fc_key not in _factcheck_key_cache
        _factcheck_key_cache[fc_key] = title[:400]
        if is_new_key:
            _save_button_cache("fc", {fc_key: _factcheck_key_cache[fc_key]})
            _AI_EXECUTOR.submit(_save_factcheck_cache, _factcheck_key_cache.copy())
        if _feat_ok("factcheck"):
            markup.add(types.InlineKeyboardButton(_L.get("factcheck", "🔍 Fact Check"), callback_data=f"fc_{fc_key}"))

    # ── زر 5: لماذا يهمك؟ 💡 (InsightX) ────────────────────────────
    if title:
        why_key = _hs.md5((title[:80]).encode("utf-8")).hexdigest()[:16]
        if len(_why_key_cache) > 3000:
            for _wk in list(_why_key_cache.keys())[:300]:
                del _why_key_cache[_wk]
        _why_key_cache[why_key] = {"title": title[:400], "summary": (summary or "")[:400]}
        _save_button_cache("why", {why_key: _why_key_cache[why_key]})
        if _feat_ok("why_matters"):
            markup.add(types.InlineKeyboardButton(_L.get("why_matters", "💡 Why It Matters"), callback_data=f"why_{why_key}"))

    # ── زر 6: ماذا بعد؟ 🔮 (InsightX) ────────────────────────────
    if title:
        next_key = _hs.md5((title[:80] + "_next").encode("utf-8")).hexdigest()[:16]
        if len(_next_key_cache) > 3000:
            for _nk in list(_next_key_cache.keys())[:300]:
                del _next_key_cache[_nk]
        _next_key_cache[next_key] = {"title": title[:400], "summary": (summary or "")[:400]}
        _save_button_cache("next", {next_key: _next_key_cache[next_key]})
        if _feat_ok("what_next"):
            markup.add(types.InlineKeyboardButton(_L.get("what_next", "🔮 What's Next?"), callback_data=f"next_{next_key}"))

    # ── زر N1: 🔮 توقع المستقبل (AI Prediction) ────────────────────────────
    if title and _AI_AVAILABLE:
        pred_key = _hs.md5((title[:80] + "_pred").encode("utf-8")).hexdigest()[:16]
        if len(_pred_key_cache) > 3000:
            for _pk in list(_pred_key_cache.keys())[:300]:
                del _pred_key_cache[_pk]
        _pred_key_cache[pred_key] = title[:400]
        _pred_lbl = _NEW_FEAT_I18N["btn_pred"].get(lang, _NEW_FEAT_I18N["btn_pred"]["العربية 🇮🇶"])
        if _feat_ok("prediction"):
            markup.add(types.InlineKeyboardButton(_pred_lbl, callback_data=f"pred_{pred_key}"))

    # ── زر N2: 🎧 اسمع الخبر (TTS لمقال محدد) ─────────────────────────────
    if title:
        tts_art_key = _hs.md5((title[:80] + "_ttsart").encode("utf-8")).hexdigest()[:16]
        if len(_tts_art_cache) > 2000:
            for _tk in list(_tts_art_cache.keys())[:200]:
                del _tts_art_cache[_tk]
        _tts_art_cache[tts_art_key] = {"title": title[:300], "summary": _clean_html(summary or "")[:400]}
        _tts_lbl = _NEW_FEAT_I18N["btn_tts"].get(lang, _NEW_FEAT_I18N["btn_tts"]["العربية 🇮🇶"])
        if _feat_ok("audio_article"):
            markup.add(types.InlineKeyboardButton(_tts_lbl, callback_data=f"tts_art_{tts_art_key}"))

    # ── زر N3: 🤝 ناقش (Discussion Share Card) ──────────────────────────────
    if title and link:
        disc_key = _hs.md5((title[:80] + "_disc").encode("utf-8")).hexdigest()[:16]
        if len(_disc_key_cache) > 2000:
            for _dk in list(_disc_key_cache.keys())[:200]:
                del _disc_key_cache[_dk]
        _disc_key_cache[disc_key] = {"title": title[:300], "summary": _clean_html(summary or "")[:300], "link": link}
        _disc_lbl = _NEW_FEAT_I18N["btn_disc"].get(lang, _NEW_FEAT_I18N["btn_disc"]["العربية 🇮🇶"])
        if _feat_ok("discuss"):
            markup.add(types.InlineKeyboardButton(_disc_lbl, callback_data=f"disc_{disc_key}"))

    # ── زر 7: التقرير الذكي الشامل 🧠 (InsightX Full Intelligence) ──────────
    if title:
        intel_key = _hs.md5((title[:80] + "_intel").encode("utf-8")).hexdigest()[:16]
        if len(_intel_key_cache) > 3000:
            for _ik in list(_intel_key_cache.keys())[:300]:
                del _intel_key_cache[_ik]
        _intel_key_cache[intel_key] = {"title": title[:400], "summary": (summary or "")[:400]}
        _save_button_cache("intel", {intel_key: _intel_key_cache[intel_key]})
        # الزر محذوف (intel_report) — نحتفظ بالـ cache للتوافق العكسي

    # ── زر 8: السياق التاريخي 📚 (InsightX Context Builder) ─────────────────
    if title:
        ctx_key = _hs.md5((title[:80] + "_ctx").encode("utf-8")).hexdigest()[:16]
        if len(_ctx_key_cache) > 3000:
            for _ck in list(_ctx_key_cache.keys())[:300]:
                del _ctx_key_cache[_ck]
        _ctx_key_cache[ctx_key] = {"title": title[:400], "summary": (summary or "")[:400]}
        _save_button_cache("ctx", {ctx_key: _ctx_key_cache[ctx_key]})
        if _feat_ok("context"):
            markup.add(types.InlineKeyboardButton(_L.get("context", "📚 Historical Context"), callback_data=f"ctx_{ctx_key}"))

    # ── زر 9: حفظ الخبر 🔖 (Bookmark) ──────────────────────────────────────
    if title and link:
        bm_key = _hs.md5((link or title).encode("utf-8")).hexdigest()[:16]
        if len(_bm_key_cache) > 3000:
            for _bk in list(_bm_key_cache.keys())[:300]:
                del _bm_key_cache[_bk]
        _bm_key_cache[bm_key] = {
            "title":  title[:400],
            "link":   link,
            "source": get_source_name_from_url(link) if link else "",
        }
        _save_button_cache("bm", {bm_key: _bm_key_cache[bm_key]})
        if _feat_ok("bookmark"):
            markup.add(types.InlineKeyboardButton(_L.get("bookmark", "🔖 Save"), callback_data=f"bm_{bm_key}"))

    # ── زر 10: شارك InsightX 🤖 ────────────────────────────────────────────
    markup.add(types.InlineKeyboardButton(f"{_L.get('share_bot', '🤖 Share InsightX')} @{BOT_USERNAME}", url=bot_share_u))

    # ── زر 11: AI Duel ⚔️ ───────────────────────────────────────────────────
    if title and _AI_AVAILABLE:
        duel_key = _hs.md5((title[:80] + "_duel").encode("utf-8")).hexdigest()[:16]
        _duel_key_cache[duel_key] = {"title": title[:400], "summary": (summary or "")[:400]}
        _save_button_cache("duel", {duel_key: _duel_key_cache[duel_key]})
        if _feat_ok("ai_duel"):
            markup.add(types.InlineKeyboardButton("⚔️ " + _L.get("duel", "جدال ذكي"), callback_data=f"duel_{duel_key}"))

    # ── زر 12: News DNA 🧬 ──────────────────────────────────────────────────
    if title and _AI_AVAILABLE:
        dna_key = _hs.md5((title[:80] + "_dna").encode("utf-8")).hexdigest()[:16]
        _dna_key_cache[dna_key] = {"title": title[:400], "summary": (summary or "")[:400]}
        _save_button_cache("dna", {dna_key: _dna_key_cache[dna_key]})
        if _feat_ok("news_dna"):
            markup.add(types.InlineKeyboardButton("🧬 " + _L.get("dna", "بصمة الخبر"), callback_data=f"dna_{dna_key}"))

    return markup

def _format_clustered_news(lang, title, link, feeds, source_count, summary="", pub_time_str=""):
    """يُنسّق خبراً مجمّعاً مع إشارة للمصادر المتعددة"""
    sources_txt = ""
    if source_count > 1:
        sources_txt = f"\n📡 _غطّته {source_count} مصادر_"
    label = t(lang, "label_breaking")
    src_name = get_source_name_from_url(feeds[0]) if feeds else ""
    base = format_news_item(label, title, lang, src_name, pub_time_str, summary=summary)
    return base + sources_txt


# ======================================================
# ميزة: متابعة قصة بعينها (/follow)
# ======================================================
_story_followers = {}  # keyword → {uid: lang}
_story_key_cache = {}  # story_key (md5[:16]) → keyword string

# ── كاش التحقق من الأخبار — مع استمرارية على القرص لتجاوز إعادة التشغيل ──
_FACTCHECK_CACHE_FILE = "factcheck_key_cache.json"
