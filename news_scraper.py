# -*- coding: utf-8 -*-
"""
  news_scraper.py — سكرابينغ قنوات تيليغرام + مواقع + دولار العراق

  يُصدِّر دوال استخراج الأخبار من التيليغرام والمواقع.
  """

import sys as _sys_legacy
import os
# ─── استيراد كل المتغيرات العالمية من bot_legacy ───
from bot_legacy import *
import state as gl  # noqa: F401,F403

def _scrape_telegram_channel(handle, max_items=8):
    """
    يسحب أحدث المنشورات من قناة تلغرام عامة عبر t.me/s/{handle}
    يُعيد قائمة من (text, link) — النص قبل تنظيف AI
    """
    if not _BS4_AVAILABLE:
        return []

    now = datetime.datetime.now()
    cached = _TG_SCRAPE_CACHE.get(handle)
    if cached:
        items, ts = cached
        if (now - ts).total_seconds() < _TG_SCRAPE_CACHE_TTL:
            return items

    url = f"https://t.me/s/{handle}"
    try:
        resp = requests.get(url, headers=_SCRAPE_HEADERS, timeout=8)
        resp.raise_for_status()
    except Exception:
        return []

    try:
        soup = BeautifulSoup(resp.text, "html.parser")
        posts = soup.select(".tgme_widget_message_wrap")[-max_items:]
        items = []
        now_utc = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
        for post in reversed(posts):
            # رابط المنشور
            link_tag = post.select_one(".tgme_widget_message_date")
            link = link_tag["href"] if link_tag and link_tag.has_attr("href") else ""

            # ─── استخراج وقت النشر من <time datetime="..."> ──────────
            pub_dt = None
            time_tag = post.select_one("time[datetime]")
            if time_tag:
                try:
                    dt_str = time_tag["datetime"]  # "2024-01-01T12:00:00+00:00"
                    # نُحوّل إلى UTC بدون timezone
                    import email.utils as _eu
                    from datetime import timezone as _tz
                    dt_parsed = datetime.datetime.fromisoformat(dt_str)
                    if dt_parsed.tzinfo is not None:
                        dt_parsed = dt_parsed.astimezone(_tz.utc).replace(tzinfo=None)
                    pub_dt = dt_parsed
                except Exception:
                    pub_dt = None

            # ─── فلترة حسب العمر (ساعتان كحد أقصى) ─────────────────
            if pub_dt is not None:
                age_minutes = (now_utc - pub_dt).total_seconds() / 60
                if age_minutes > _RSS_FRESHNESS_MINUTES:
                    continue  # منشور قديم — تجاهله

            # نص المنشور
            text_tag = post.select_one(".tgme_widget_message_text")
            if not text_tag:
                continue
            raw_text = text_tag.get_text(separator="\n", strip=True)
            # ─── حذف أسطر الروابط والتوقيعات من نهاية المنشور ────────
            import re as _re
            cleaned_lines = []
            for line in raw_text.splitlines():
                stripped = line.strip()
                if _re.match(r'^https?://t\.me/\S+$', stripped):
                    continue
                if _re.match(r'^@[A-Za-z0-9_]{3,}$', stripped):
                    continue
                if _re.match(r'^t\.me/\S+$', stripped):
                    continue
                cleaned_lines.append(line)
            raw_text = "\n".join(cleaned_lines).strip()
            if len(raw_text) < 20:
                continue
            items.append((raw_text, link, pub_dt))  # نُعيد pub_dt للمعالجة اللاحقة
        _TG_SCRAPE_CACHE[handle] = (items, now)
        return items
    except Exception:
        return []


# ─── سعر دولار السوق من قناة @dollariraqi ─────────────────────────
_DOLLAR_IRAQI_CACHE: dict = {"text": None, "ts": 0.0}
_DOLLAR_IRAQI_TTL = 600  # 10 دقائق

# الأنماط المسموح باستخراجها فقط (الأسعار)
_DOLLAR_IRAQI_ALLOWED_PATTERNS = [
    r'▣[^\n]+',            # عناوين المناطق  ▣بغداد-صيرفات:
    r'🔹[^\n]+',           # أسعار البيع والشراء
    r'💎[^\n]+',           # سعر الذهب
    r'[\U0001F1E0-\U0001F1FF]{2}[^\n]+',  # أعلام + سعر (اليورو، الدولار، إلخ)
    r'[٠-٩0-9,،.]+\s*(?:دينار|iqd|بيع|شراء|\$|IQD)',  # أرقام الأسعار
]

def _fetch_dollariraqi_market() -> str | None:
    """
    يسحب آخر رسالة من قناة @dollariraqi ويستخرج الأسعار فقط.
    يُعيد نص منظف يحتوي فقط على أسعار الصرف — بدون حقوق القناة.
    النتيجة مخزنة 10 دقائق.
    """
    now = time.time()
    # تحقق من الكاش
    if _DOLLAR_IRAQI_CACHE["text"] and now - _DOLLAR_IRAQI_CACHE["ts"] < _DOLLAR_IRAQI_TTL:
        return _DOLLAR_IRAQI_CACHE["text"]

    # سحب آخر رسالة من القناة
    posts = _scrape_telegram_channel("dollariraqi", max_items=5)
    if not posts:
        return None

    # آخر رسالة (الأحدث — القائمة مرتبة من الأقدم للأحدث، نأخذ الأخير)
    raw_text = posts[-1][0] if posts else ""
    if not raw_text or len(raw_text) < 20:
        return None

    # تنظيف AI: استخراج الأسعار فقط
    cleaned = _ai_extract_dollar_rates(raw_text)
    if cleaned:
        _DOLLAR_IRAQI_CACHE["text"] = cleaned
        _DOLLAR_IRAQI_CACHE["ts"]   = now
    return cleaned


def _ai_extract_dollar_rates(raw_text: str) -> str:
    """
    AI يستخرج فقط أسعار العملات والذهب من نص القناة —
    يحذف تلقائياً: اسم القناة، حقوق النشر، @mentions، الإعلانات،
    أي نص لا علاقة له بالأسعار.
    """
    # تنظيف regex أولي — حذف @mentions وروابط
    import re as _re_d
    text_clean = _re_d.sub(r'@\S+', '', raw_text)
    text_clean = _re_d.sub(r'https?://\S+', '', text_clean)
    text_clean = _re_d.sub(r'#\S+', '', text_clean).strip()

    # استخراج regex مباشر بدون AI (سريع وموثوق)
    lines = text_clean.split('\n')
    keep = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        # الأسطر المسموحة: تبدأ بـ ▣ أو 🔹 أو 💎 أو علم أو تحتوي على أرقام أسعار
        has_price = bool(_re_d.search(r'[0-9٠-٩][0-9٠-٩,،. ]{3,}', line))
        has_marker = any(line.startswith(m) for m in ['▣', '🔹', '💎', '🇦', '🇺', '🇪', '🇬', '🇸'])
        # تجاهل الأسطر الدعائية: تحتوي على "قناة" أو "اشتر" أو تبدأ بـ " — " أو قصيرة جداً
        is_promo = any(w in line for w in ['قناة', 'اشترك', 'تواصل', 'واتس', 'telegram', 'Telegram', 'bot', 'Bot', '©', 'حقوق'])
        if is_promo:
            continue
        if (has_price or has_marker) and len(line) < 120:
            keep.append(line)

    if keep:
        return '\n'.join(keep)

    # fallback: AI إذا فشل الاستخراج بـ regex
    if not _AI_AVAILABLE or not _AI_MODEL:
        return text_clean[:400]

    prompt = (
        "من النص التالي، استخرج فقط أسعار الدولار والعملات والذهب.\n"
        "القواعد الصارمة:\n"
        "✅ اقتصر على: ▣بغداد-صيرفات، 🔹البيع والشراء، 💎الذهب، 🇪🇺اليورو، أي عملة وسعرها\n"
        "❌ احذف تماماً: اسم القناة، @mentions، الروابط، عبارات الاشتراك، الإعلانات\n"
        "❌ احذف: أي جملة لا تحتوي على رقم سعر\n"
        "لا تضف أي تعليق — فقط الأسعار بنفس التنسيق الأصلي.\n\n"
        f"النص:\n{text_clean[:800]}"
    )
    _h = [text_clean[:300]]
    def _c():
        try:
            __h_result_ai = _ai_generate(prompt)
            if __h_result_ai:
                _h[0] = __h_result_ai  # FIX: write to mutable container, not local var
        except Exception as _exc:
            _log_exc(_exc)
    try:
        _AI_EXECUTOR.submit(_c).result(timeout=6)
    except Exception:
        pass
    return _h[0]  # FIX: was _h_result → NameError every time AI fallback ran


def _scrape_news_site(url, base_url, max_items=10):
    """
    يسحب الأخبار من صفحة موقع بدون RSS.
    يجرب أنماط CSS متعددة للعثور على العناوين والروابط تلقائياً.
    يُعيد قائمة من (title, full_link).
    """
    if not _BS4_AVAILABLE:
        return []

    # فحص الكاش أولاً
    with _SCRAPE_LOCK:
        cached = _SCRAPE_CACHE.get(url)
        if cached:
            items, ts = cached
            if (datetime.datetime.now() - ts).total_seconds() < _SCRAPE_CACHE_TTL:
                return items

    items = []
    seen_links = set()

    def _fetch():
        try:
            resp = requests.get(url, headers=_SCRAPE_HEADERS, timeout=_SCRAPE_TIMEOUT)
            resp.raise_for_status()
            return resp.text
        except Exception:
            return None

    # جلب الصفحة في thread منفصل حتى لا يُجمّد البوت
    result_html = [None]
    t = threading.Thread(target=lambda: result_html.__setitem__(0, _fetch()), daemon=True)
    t.start()
    t.join(_SCRAPE_TIMEOUT + 2)

    html = result_html[0]
    if not html:
        return []

    try:
        soup = BeautifulSoup(html, 'html.parser')

        # إزالة عناصر غير مفيدة (قوائم التنقل، تذييل الصفحة، الإعلانات)
        for tag in soup.select('nav, footer, header, script, style, .ad, .advertisement, .sidebar'):
            tag.decompose()

        candidates = []

        # ---- الأنماط المرتبة من الأدق إلى الأعم ----

        # النمط 1: روابط داخل وسم article
        for a in soup.select('article a[href]'):
            title = a.get_text(strip=True)
            href = a.get('href', '').strip()
            if len(title) > 25 and href:
                candidates.append((title, href))

        # النمط 2: h2/h3 داخل وسم article
        if len(candidates) < 5:
            for h in soup.select('article h2, article h3'):
                a = h.find('a', href=True)
                if a:
                    title = a.get_text(strip=True)
                    href = a['href'].strip()
                    if len(title) > 25:
                        candidates.append((title, href))

        # النمط 3: كلاسات شائعة لعناوين الأخبار
        if len(candidates) < 5:
            for sel in [
                'h2 a[href]', 'h3 a[href]',
                '.title a[href]', '.news-title a[href]',
                '.story-title a[href]', '.article-title a[href]',
                '.entry-title a[href]', '.headline a[href]',
                '.post-title a[href]', '.card-title a[href]',
                'a.title[href]', 'a.headline[href]',
            ]:
                for a in soup.select(sel):
                    title = a.get_text(strip=True)
                    href = a.get('href', '').strip()
                    if len(title) > 25 and href:
                        candidates.append((title, href))
                if len(candidates) >= 10:
                    break

        # ---- تنظيف الروابط وتحويلها إلى مطلقة ----
        for title, href in candidates:
            if len(items) >= max_items:
                break
            if not href:
                continue
            # تحويل النسبي إلى مطلق
            if href.startswith('//'):
                href = 'https:' + href
            elif href.startswith('/'):
                href = base_url.rstrip('/') + href
            elif not href.startswith('http'):
                continue
            # تجاهل روابط التصنيف والمؤلف والأنكور
            if any(x in href for x in ['#', 'javascript:', 'mailto:', '/tag/', '/category/', '/author/', '/page/']):
                continue
            if href in seen_links:
                continue
            seen_links.add(href)
            # تنظيف العنوان من رموز زائدة
            title = ' '.join(title.split())
            if len(title) > 200:
                title = title[:200] + '…'
            items.append((title, href))

    except Exception as _exc:
        _log_exc(_exc)

    # تخزين في الكاش حتى لو فارغة (لتجنب الطلبات المتكررة على موقع فاشل)
    with _SCRAPE_LOCK:
        _SCRAPE_CACHE[url] = (items, datetime.datetime.now())

    return items


def get_scraped_news(lang, max_per_source=5):
    """
    جلب الأخبار بالـ scraping من جميع مصادر لغة معينة.
    يُعيد قائمة من dicts: {title, link, source}
    """
    if not _BS4_AVAILABLE:
        return []
    sources = SCRAPE_SOURCES.get(lang, [])
    results = []
    for src in sources:
        try:
            items = _scrape_news_site(src['url'], src['base_url'], max_items=max_per_source)
            for title, link in items:
                results.append({
                    'title': title,
                    'link': link,
                    'source': src['name'],
                })
        except Exception as _exc:
            _log_exc(_exc)
    return results


# ======== الكلمات المفتاحية للمستخدمين المميزين ========
user_keywords = load_json(KEYWORDS_FILE, {})

def send_dollar_parallel(uid):
    user = users.get(str(uid))
    lang = user.get("lang", "English 🇬🇧") if user else "English 🇬🇧"
    now_str = _now_sa().strftime("%H:%M - %d/%m/%Y")

    # ─── المستخدمون العراقيون: مصدر @dollariraqi الحصري ─────────────
    if _is_iraqi_user(uid):
        wait_msg = bot.send_message(uid,
            "⏳ جاري جلب أسعار السوق الآن...", parse_mode="Markdown")
        market_text = _fetch_dollariraqi_market()
        try:
            bot.delete_message(uid, wait_msg.message_id)
        except Exception as _exc:
            _log_exc(_exc)
        if market_text:
            msg = (
                f"💵 *أسعار دولار السوق*\n"
                f"🕐 `{now_str}`\n"
                f"━━━━━━━━━━━━━━\n"
                f"{market_text}\n"
                f"━━━━━━━━━━━━━━\n"
                f"📡 _المصدر: @dollariraqi_\n"
                f"🤖 @{BOT_USERNAME}"
            )
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton(
                "🔄 تحديث الآن", callback_data="refresh_dollar_iraqi"
            ))
            markup.add(types.InlineKeyboardButton(
                "📢 قناة @dollariraqi", url="https://t.me/dollariraqi"
            ))
            bot.send_message(uid, msg, parse_mode="Markdown", reply_markup=markup)
            return
        else:
            # فشل الجلب — fallback للـ API العادي
            bot.send_message(uid,
                "⚠️ تعذر جلب أسعار @dollariraqi، جاري استخدام المصدر البديل...")

    # ─── المستخدمون غير العراقيين: API عالمي ────────────────────────
    rate = None
    source_note = ""
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get("https://dolarsoft.com/api/v1/price", headers=headers, timeout=8)
        data = r.json()
        sell = data.get("sell") or data.get("price") or data.get("usd_sell")
        buy  = data.get("buy") or data.get("usd_buy")
        if sell:
            rate = f"{t(lang, 'dollar_sell')}: `{sell}` IQD\n{t(lang, 'dollar_buy')}: `{buy or '-'}` IQD"
            source_note = "dolarsoft.com"
    except Exception as _exc:
        _log_exc(_exc)
    if not rate:
        try:
            r = requests.get("https://api.exchangerate-api.com/v4/latest/USD", timeout=10)
            iqd = r.json().get("rates", {}).get("IQD", None)
            if iqd:
                rate = t(lang, "dollar_official").format(price=f"{int(iqd):,}")
                source_note = "exchangerate-api.com"
        except Exception as _exc:
            _log_exc(_exc)
    if not rate:
        bot.send_message(uid, t(lang, "dollar_error"))
        return
    msg = t(lang, "dollar_header").format(
        rate=rate, time=now_str, source=source_note, username=BOT_USERNAME)
    bot.send_message(uid, msg, parse_mode="Markdown")

# ======== ملخص أسبوعي نصي ========
@bot.callback_query_handler(func=lambda c: c.data == "refresh_dollar_iraqi")
def cb_refresh_dollar_iraqi(call):
    """زر تحديث أسعار الدولار من @dollariraqi"""
    uid = call.from_user.id
    bot.answer_callback_query(call.id, "⏳ جاري التحديث...")
    # مسح الكاش لإجبار إعادة الجلب
    _DOLLAR_IRAQI_CACHE["text"] = None
    _DOLLAR_IRAQI_CACHE["ts"]   = 0.0
    market_text = _fetch_dollariraqi_market()
    now_str = _now_sa().strftime("%H:%M - %d/%m/%Y")
    if market_text:
        msg = (
            f"💵 *أسعار دولار السوق*\n"
            f"🕐 `{now_str}`\n"
            f"━━━━━━━━━━━━━━\n"
            f"{market_text}\n"
            f"━━━━━━━━━━━━━━\n"
            f"📡 _المصدر: @dollariraqi_\n"
            f"🤖 @{BOT_USERNAME}"
        )
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton(
            "🔄 تحديث الآن", callback_data="refresh_dollar_iraqi"
        ))
        markup.add(types.InlineKeyboardButton(
            "📢 قناة @dollariraqi", url="https://t.me/dollariraqi"
        ))
        try:
            bot.edit_message_text(msg, call.message.chat.id, call.message.message_id,
                                  parse_mode="Markdown", reply_markup=markup)
        except Exception:
            bot.send_message(uid, msg, parse_mode="Markdown", reply_markup=markup)
    else:
        bot.answer_callback_query(call.id, "⚠️ تعذر التحديث — حاول لاحقاً", show_alert=True)


