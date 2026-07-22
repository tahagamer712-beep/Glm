# -*- coding: utf-8 -*-
"""
  handler_news.py — أوامر وأزرار الأخبار

  يُصدِّر معالجات أوامر الأخبار وأزرارها.
  """

import sys as _sys_legacy
import os
# ─── استيراد كل المتغيرات العالمية من bot_legacy ───
from bot_legacy import *
import state as gl  # noqa: F401,F403

@bot.callback_query_handler(func=lambda c: c.data == "read_open")
def handle_read_open(call):
    today = str(datetime.date.today())
    read_stats["total_opens"] = read_stats.get("total_opens", 0) + 1
    read_stats.setdefault("daily", {})[today] = read_stats["daily"].get(today, 0) + 1
    save_read_stats()
    bot.answer_callback_query(call.id)

# ======== معالج زر ملخص الخبر ========
@bot.callback_query_handler(func=lambda c: c.data.startswith("sum_"))
def handle_summary_button(call):
    uid = call.from_user.id
    user = users.get(str(uid), {})
    lang = user.get("lang", "English 🇬🇧")
    # ── فحص Feature Flag ──
    if not _is_feature_enabled("ai_summary", uid):
        bot.answer_callback_query(call.id, _feature_blocked_msg(uid, "ai_summary"), show_alert=True)
        return
    lbl = NEWS_SHARE_LABELS.get(lang, NEWS_SHARE_LABELS["English 🇬🇧"])
    sum_key = call.data[4:]
    cached = _news_summary_cache.get(sum_key)
    if not cached:
        bot.answer_callback_query(call.id, lbl["no_summary"], show_alert=True)
        return
    # دعم الكاش القديم (نص مباشر) والجديد (dict)
    if isinstance(cached, dict):
        summary_text = cached.get("text", "")
        news_title   = cached.get("title", "")
    else:
        summary_text = cached
        news_title   = ""
    clean = _clean_html(summary_text)
    if not clean:
        bot.answer_callback_query(call.id, lbl["no_summary"], show_alert=True)
        return
    bot.answer_callback_query(call.id)
    # تتبع النقرة لتحسين التوصيات الشخصية (InsightX Personalization)
    if news_title:
        _track_user_click(uid, news_title, action="summary")
    # إذا كان النص طويلاً (منشور قناة تلغرام أو مقال كامل) → توليد ملخص AI احترافي
    # إذا كان قصيراً (ملخص RSS جاهز) → تنظيف بسيط فقط
    if _AI_AVAILABLE and len(clean) > 120:
        try:
            clean = _ai_generate_summary(clean, title=news_title, lang=lang)
        except Exception as _exc:
            _log_exc(_exc)
    elif _AI_AVAILABLE and news_title:
        try:
            clean = _ai_clean_news(news_title, body=clean[:800])
        except Exception as _exc:
            _log_exc(_exc)
    # بناء رسالة الملخص الجميلة
    separator = "━━━━━━━━━━━━━━"
    title_line = f"📰 *{escape_md(news_title)}*\n{separator}\n" if news_title else ""
    full_msg = (
        f"{title_line}"
        f"*{lbl['summary_btn']}*\n\n"
        f"{escape_md(clean[:1800])}\n"
        f"{separator}"
    )
    bot.send_message(uid, full_msg, parse_mode="Markdown", disable_web_page_preview=True)
    user["used_summary"] = True
    _db_save_user(uid, user)


# FIX: زر/معالج "صورة المقال" (ogimg_) أُزيلا — صورة الخبر تُرسَل الآن مباشرة مع
# الخبر عند بثّه (bot.send_photo) إذا كانت متوفرة جاهزة بمصدر RSS، بدلاً من زر
# يطلب og:image بطلب شبكة منفصل عند الضغط.

# ======== 🔮 معالج زر توقع المستقبل (pred_) ========
@bot.callback_query_handler(func=lambda c: c.data.startswith("pred_"))
def handle_pred_button(call):
    uid      = call.from_user.id
    pred_key = call.data[5:]
    title    = _pred_key_cache.get(pred_key)
    lang     = users.get(str(uid), {}).get("lang", "العربية 🇮🇶")
    if not title:
        bot.answer_callback_query(call.id,
            _NEW_FEAT_I18N["pred_expired"].get(lang, _NEW_FEAT_I18N["pred_expired"]["العربية 🇮🇶"]),
            show_alert=True)
        return
    bot.answer_callback_query(call.id)
    wait = bot.send_message(uid,
        _NEW_FEAT_I18N["pred_wait"].get(lang, _NEW_FEAT_I18N["pred_wait"]["العربية 🇮🇶"]))
    prediction = _ai_predict_events(title)
    try: bot.delete_message(uid, wait.message_id)
    except Exception as _exc:
        _log_exc(_exc)
    _sep = "━━━━━━━━━━━━━━━━━━"
    _news_lbl = _NEW_FEAT_I18N["pred_news_label"].get(lang, _NEW_FEAT_I18N["pred_news_label"]["العربية 🇮🇶"])
    header = (
        _NEW_FEAT_I18N["pred_header"].get(lang, _NEW_FEAT_I18N["pred_header"]["العربية 🇮🇶"])
        + f"{_news_lbl}: _{escape_md(title[:120])}_\n{_sep}\n\n"
    )
    bot.send_message(uid, header + escape_md(prediction),
                     parse_mode="Markdown", disable_web_page_preview=True)


# ======== 🎧 معالج زر اسمع الخبر (tts_art_) ========
@bot.callback_query_handler(func=lambda c: c.data.startswith("tts_art_"))
def handle_tts_art_button(call):
    uid     = call.from_user.id
    art_key = call.data[8:]
    cached  = _tts_art_cache.get(art_key)
    lang    = users.get(str(uid), {}).get("lang", "العربية 🇮🇶")
    if not cached:
        bot.answer_callback_query(call.id,
            _NEW_FEAT_I18N["pred_expired"].get(lang, _NEW_FEAT_I18N["pred_expired"]["العربية 🇮🇶"]),
            show_alert=True)
        return
    bot.answer_callback_query(call.id)
    title   = cached.get("title", "")
    summary = cached.get("summary", "")
    text_to_read = f"{title}. {summary}" if summary else title
    wait = bot.send_message(uid,
        _NEW_FEAT_I18N["tts_wait"].get(lang, _NEW_FEAT_I18N["tts_wait"]["العربية 🇮🇶"]))
    try:
        import io
        from gtts import gTTS
        lang_tts = _NEW_FEAT_I18N["tts_lang_code"].get(lang, "ar")
        tts = gTTS(text=text_to_read[:500], lang=lang_tts, slow=False)
        buf = io.BytesIO()
        tts.write_to_fp(buf)
        buf.seek(0)
        try: bot.delete_message(uid, wait.message_id)
        except Exception as _exc:
            _log_exc(_exc)
        _prefix = _NEW_FEAT_I18N["tts_caption_prefix"].get(lang, _NEW_FEAT_I18N["tts_caption_prefix"]["العربية 🇮🇶"])
        caption = f"🎧 *{escape_md(title[:150])}*" if title else _prefix
        bot.send_voice(uid, buf, caption=caption, parse_mode="Markdown")
    except Exception:
        try: bot.delete_message(uid, wait.message_id)
        except Exception as _exc:
            _log_exc(_exc)
        bot.send_message(uid,
            _NEW_FEAT_I18N["tts_error"].get(lang, _NEW_FEAT_I18N["tts_error"]["العربية 🇮🇶"]))


# ======== 🤝 معالج زر ناقش مع صديق (disc_) ========
@bot.callback_query_handler(func=lambda c: c.data.startswith("disc_"))
def handle_disc_button(call):
    uid      = call.from_user.id
    disc_key = call.data[5:]
    cached   = _disc_key_cache.get(disc_key)
    lang     = users.get(str(uid), {}).get("lang", "العربية 🇮🇶")
    if not cached:
        bot.answer_callback_query(call.id,
            _NEW_FEAT_I18N["pred_expired"].get(lang, _NEW_FEAT_I18N["pred_expired"]["العربية 🇮🇶"]),
            show_alert=True)
        return
    bot.answer_callback_query(call.id)
    title   = cached.get("title", "")
    summary = cached.get("summary", "")
    link    = cached.get("link", "")
    import urllib.parse as _up
    _sep = "━━━━━━━━━━━━━━━━━━"
    _tag  = _NEW_FEAT_I18N["disc_tag"].get(lang, _NEW_FEAT_I18N["disc_tag"]["العربية 🇮🇶"])
    _disc_text = (
        f"📰 *{escape_md(title)}*\n{_sep}\n"
        f"{escape_md(summary[:300]) + chr(10) + chr(10) if summary else ''}"
        f"🔗 {link}\n{_sep}\n"
        f"{_tag}\n"
        f"✨ @{BOT_USERNAME}"
    )
    _tg_share = (
        f"https://t.me/share/url"
        f"?url={_up.quote(link, safe='')}"
        f"&text={_up.quote(_disc_text[:900], safe='')}"
    )
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton(
        _NEW_FEAT_I18N["disc_send_btn"].get(lang, _NEW_FEAT_I18N["disc_send_btn"]["العربية 🇮🇶"]),
        url=_tg_share))
    markup.add(types.InlineKeyboardButton(
        _NEW_FEAT_I18N["disc_invite_btn"].get(lang, _NEW_FEAT_I18N["disc_invite_btn"]["العربية 🇮🇶"]),
        url=f"https://t.me/{BOT_USERNAME}"))
    _header = _NEW_FEAT_I18N["disc_header"].get(lang, _NEW_FEAT_I18N["disc_header"]["العربية 🇮🇶"])
    bot.send_message(uid, _header + "\n\n" + _disc_text,
                     parse_mode="Markdown", reply_markup=markup,
                     disable_web_page_preview=True)


# ======== 🗺️ خريطة العراق الحية ========
def handle_rating(call):
    uid = call.from_user.id
    data = call.data
    try:
        parts = data.split("_")
        # إصلاح #12: استخدام parts[-1] لأمان أكثر (rate_bot_5 أو rate_news_5)
        rtype = parts[1]
        stars = int(parts[-1])
        bot.answer_callback_query(call.id, f"✅ شكراً! قيّمت بـ {stars}⭐")
        try:
            bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
        except Exception as _exc:
            _log_exc(_exc)
        if rtype == "bot":
            ratings_data["bot_sum"] = ratings_data.get("bot_sum", 0) + stars
            ratings_data["count"] = ratings_data.get("count", 0) + 1
        elif rtype == "news":
            ratings_data["news_sum"] = ratings_data.get("news_sum", 0) + stars
        ratings_data.setdefault("entries", []).append({
            "uid": uid, "type": rtype, "stars": stars,
            "time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        })
        save_ratings()
        # تحديث إحصائيات المستخدم الشخصية
        if str(uid) in users:
            if stars >= 4:
                users[str(uid)]["rated_positive"] = users[str(uid)].get("rated_positive", 0) + 1
            elif stars <= 2:
                users[str(uid)]["rated_negative"] = users[str(uid)].get("rated_negative", 0) + 1
            _db_save_user(uid, users[str(uid)])
    except Exception as _exc:
        _log_exc(_exc)

# ======== إيقاف الأخبار مؤقتاً للمستخدم ========
@bot.callback_query_handler(func=lambda c: c.data.startswith("pause_news_"))
def send_trending_news(uid):
    user = users.get(str(uid))
    if not user:
        return
    lang = user.get("lang", "English 🇬🇧")
    lang_code = LANG_CODES.get(lang, "en")
    try:
        url = f"https://newsapi.org/v2/top-headlines?language={lang_code}&pageSize=8&sortBy=popularity&apiKey={NEWS_KEY}"
        r = requests.get(url, timeout=10).json()
        articles = r.get("articles", [])
        if not articles:
            feeds = RSS.get(lang, [])
            if feeds:
                try:
                    feed = _parse_feed(feeds[0])
                    if feed is None:
                        feed = feedparser.parse(feeds[0])
                    if not feed:
                        raise Exception("feed is None")
                    articles_rss = feed.entries[:8]
                    bot.send_message(uid, t(lang, "trending_header"), parse_mode="Markdown")
                    for item in articles_rss:
                        title = getattr(item, 'title', '').strip()
                        link = getattr(item, 'link', '')
                        if title and link and _title_in_lang(title, lang):
                            item_sum = getattr(item, 'summary', '') or getattr(item, 'description', '')
                            markup = make_news_share_markup(link, title, lang, item_sum)
                            trending_src = get_source_name_from_url(link)
                            pub_time_str = _format_pub_time(_pub_dt_from_item(item), lang=lang)
                            bot.send_message(uid, format_news_item(t(lang, "label_trending"), title, lang, trending_src, pub_time_str, summary=item_sum), parse_mode="Markdown", reply_markup=markup)
                    return
                except Exception as _exc:
                    _log_exc(_exc)
            bot.send_message(uid, t(lang, "no_trending"))
            return
        bot.send_message(uid, t(lang, "trending_header"), parse_mode="Markdown")
        for article in articles[:8]:
            title = article.get("title", "").strip()
            link = article.get("url", "")
            if title and link and _title_in_lang(title, lang):
                art_sum = article.get("description", "") or article.get("content", "")
                markup = make_news_share_markup(link, title, lang, art_sum)
                api_src = (article.get("source") or {}).get("name", "") or get_source_name_from_url(link)
                na_pub_str = article.get("publishedAt", "")
                try:
                    import datetime as _dt
                    na_pub_dt = _dt.datetime.strptime(na_pub_str, "%Y-%m-%dT%H:%M:%SZ") if na_pub_str else None
                except Exception:
                    na_pub_dt = None
                pub_time_str = _format_pub_time(na_pub_dt, lang=lang)
                bot.send_message(uid, format_news_item(t(lang, "label_trending"), title, lang, api_src, pub_time_str, summary=art_sum), parse_mode="Markdown", reply_markup=markup)
    except Exception as e:
        bot.send_message(uid, t(lang, "no_trending"))
        notify_admin_error(f"خطأ في الأخبار الرائجة: {e}")

def send_weekly_news_summary(uid):
    user = users.get(str(uid))
    if not user:
        return
    lang = user.get("lang", "English 🇬🇧")
    feeds = RSS.get(lang, [])
    headlines = []
    for feed_url in feeds:
        try:
            feed = _parse_feed(feed_url)
            if feed is None:
                feed = feedparser.parse(feed_url)
            if not feed:
                continue
            for item in feed.entries[:5]:
                title = getattr(item, 'title', '')
                if title:
                    headlines.append(title)
            if len(headlines) >= 20:
                break
        except Exception as _exc:
            _log_exc(_exc)
    if not headlines:
        bot.send_message(uid, t(lang, "no_weekly"))
        return
    count = min(len(headlines), 20)
    msg = t(lang, "weekly_summary_header").format(count=count)
    for i, title in enumerate(headlines[:20], 1):
        msg += f"{i}. {title}\n\n"
    bot.send_message(uid, msg, parse_mode="Markdown")

def _get_quick_news(uid, count=5, keywords=None, use_user_cats=False):
    """جلب أخبار سريعة من RSS بحسب اللغة وكلمات مفتاحية اختيارية"""
    lang = users.get(str(uid), {}).get('lang', 'العربية 🇮🇶')

    # إذا مُرِّرت كلمات مفتاحية صريحة، استخدمها مباشرة
    # إذا use_user_cats=True، استخدم تفضيلات المستخدم
    if keywords is None and use_user_cats:
        keywords = _get_user_cat_keywords(uid) or None  # None = لا فلتر

    results = []
    seen = set()
    for feed_url in list(RSS.get(lang, RSS.get("العربية 🇮🇶", [])))[:15]:
        try:
            feed = _parse_feed(feed_url)
            if not feed: continue
            for entry in feed.entries[:10]:
                title = (getattr(entry, 'title', '') or '').strip()
                link  = (getattr(entry, 'link',  '') or '').strip()
                summ  = (getattr(entry, 'summary', '') or '').strip()
                if not title or title in seen: continue
                if keywords:
                    match = any(k.lower() in title.lower() or k.lower() in summ.lower() for k in keywords)
                    if not match: continue
                seen.add(title)
                pub = _pub_dt_from_item(entry)
                # استخراج اسم المصدر من feed_url
                src_name = ""
                for _domain, _name in SOURCE_NAMES.items():
                    if _domain in feed_url:
                        src_name = _name
                        break
                # تنظيف الملخص مسبقاً لإزالة أي روابط أو HTML
                clean_summ = _clean_html(summ)[:300]
                results.append({"title": title, "link": link, "summary": clean_summ, "pub": pub, "source": src_name})
                if len(results) >= count: return results
        except Exception as _exc:
            _log_exc(_exc)
    return results

# ── 1. ⚡ وضع 30 ثانية ─────────────────────────────────────────
def _handle_mode30(uid):
    lang = users.get(str(uid), {}).get('lang', 'العربية 🇮🇶')
    headers = {
        "العربية 🇮🇶": "⚡ *وضع 30 ثانية* — أبرز ما حدث:\n\n",
        "English 🇬🇧":  "⚡ *30-Second Mode* — Top headlines:\n\n",
        "Русский 🇷🇺":  "⚡ *Режим 30 секунд* — Главные новости:\n\n",
        "فارسی 🇮🇷":    "⚡ *حالت ۳۰ ثانیه* — مهمترین اخبار:\n\n",
        "हिन्दी 🇮🇳":   "⚡ *30 सेकंड मोड* — मुख्य खबरें:\n\n",
        "Português 🇧🇷": "⚡ *Modo 30 Segundos* — Principais manchetes:\n\n",
        "Türkçe 🇹🇷":   "⚡ *30 Saniye Modu* — Öne Çıkan Haberler:\n\n",
        "اردو 🇵🇰":      "⚡ *30 سیکنڈ موڈ* — اہم خبریں:\n\n",
        "Deutsch 🇩🇪":  "⚡ *30-Sekunden-Modus* — Top-Nachrichten:\n\n",
        "Українська 🇺🇦":"⚡ *Режим 30 секунд* — Головні новини:\n\n",
        "Italiano 🇮🇹": "⚡ *Modalità 30 Secondi* — Notizie principali:\n\n",
        "Español 🇲🇽":  "⚡ *Modo 30 Segundos* — Titulares principales:\n\n",
        "Français 🇫🇷": "⚡ *Mode 30 Secondes* — Titres principaux:\n\n",
    }
    items = _get_quick_news(uid, count=8)
    if not items:
        bot.send_message(uid, "⚠️ لا توجد أخبار متاحة الآن.")
        return
    # إرسال عنوان الوضع أولاً
    header_msg = headers.get(lang, headers["English 🇬🇧"]).strip()
    bot.send_message(uid, header_msg, parse_mode="Markdown")
    # إرسال كل خبر كرسالة مستقلة بنفس شكل الخبر الرئيسي
    for item in items:
        t_ = item["title"]
        l_ = item.get("link", "")
        s_ = item.get("summary", "")
        src_ = item.get("source", "")
        pub = item.get("pub")
        time_str = _format_pub_time(pub, lang=lang) if pub else ""
        try:
            news_text = format_news_item("⚡", t_, lang, src_, time_str, summary=s_)
            markup = make_news_share_markup(l_, t_, lang, s_) if l_ else None
            bot.send_message(uid, news_text, parse_mode="Markdown",
                             reply_markup=markup, disable_web_page_preview=True)
        except Exception as _exc:
            _log_exc(_exc)

# ── 2. 😐 بدون تحليل — إعداد دائم (toggle) ────────────────────
def _handle_noanalysis(uid):
    """يبدّل إعداد 'بدون تحليل' للمستخدم ويحفظه بشكل دائم."""
    user = users.get(str(uid), {})
    lang = user.get('lang', 'العربية 🇮🇶')
    current = user.get("no_analysis_mode", False)
    new_val = not current
    users[str(uid)]["no_analysis_mode"] = new_val
    _db_save_user(uid, users[str(uid)])

    _on_msgs = {
        "العربية 🇮🇶": "✅ *تم التفعيل* — الآن ستصلك الأخبار بدون أزرار تحليل.\nاضغط *بدون تحليل* مرة أخرى لإيقافه.",
        "English 🇬🇧":  "✅ *Enabled* — You'll now receive news without analysis buttons.\nPress *No Analysis* again to disable.",
        "Русский 🇷🇺":  "✅ *Включено* — Новости без кнопок анализа.\nНажмите снова для отключения.",
        "فارسی 🇮🇷":    "✅ *فعال شد* — اخبار بدون دکمه‌های تحلیل.\nدوباره بزنید تا غیرفعال شود.",
        "हिन्दी 🇮🇳":   "✅ *सक्रिय* — विश्लेषण बटन बिना समाचार मिलेगा।",
        "Português 🇧🇷": "✅ *Ativado* — Notícias sem botões de análise.",
        "Türkçe 🇹🇷":   "✅ *Etkin* — Haberler analiz butonları olmadan gelecek.",
        "اردو 🇵🇰":      "✅ *فعال* — خبریں تجزیہ بٹنوں کے بغیر آئیں گی۔",
        "Deutsch 🇩🇪":  "✅ *Aktiviert* — Nachrichten ohne Analyse-Schaltflächen.",
        "Українська 🇺🇦":"✅ *Увімкнено* — Новини без кнопок аналізу.",
        "Italiano 🇮🇹": "✅ *Attivato* — Notizie senza pulsanti di analisi.",
        "Español 🇲🇽":  "✅ *Activado* — Noticias sin botones de análisis.",
        "Français 🇫🇷": "✅ *Activé* — Actualités sans boutons d'analyse.",
    }
    _off_msgs = {
        "العربية 🇮🇶": "😐 *تم الإيقاف* — ستعود الأزرار التحليلية مع كل خبر.",
        "English 🇬🇧":  "😐 *Disabled* — Analysis buttons will appear with each news item.",
        "Русский 🇷🇺":  "😐 *Отключено* — Кнопки анализа вернутся к новостям.",
        "فارسی 🇮🇷":    "😐 *غیرفعال شد* — دکمه‌های تحلیل با اخبار برمی‌گردند.",
        "हिन्दी 🇮🇳":   "😐 *अक्षम* — विश्लेषण बटन वापस आएंगे।",
        "Português 🇧🇷": "😐 *Desativado* — Botões de análise voltarão.",
        "Türkçe 🇹🇷":   "😐 *Devre Dışı* — Analiz butonları geri gelecek.",
        "اردو 🇵🇰":      "😐 *غیر فعال* — تجزیہ بٹن واپس آئیں گے۔",
        "Deutsch 🇩🇪":  "😐 *Deaktiviert* — Analyse-Schaltflächen kommen zurück.",
        "Українська 🇺🇦":"😐 *Вимкнено* — Кнопки аналізу повернуться.",
        "Italiano 🇮🇹": "😐 *Disattivato* — I pulsanti di analisi torneranno.",
        "Español 🇲🇽":  "😐 *Desactivado* — Los botones de análisis volverán.",
        "Français 🇫🇷": "😐 *Désactivé* — Les boutons d'analyse reviendront.",
    }
    msgs = _on_msgs if new_val else _off_msgs
    bot.send_message(uid, msgs.get(lang, msgs["English 🇬🇧"]), parse_mode="Markdown")

# ── 3. 💡 زبدة الموضوع ──────────────────────────────────────
def _handle_zbda(uid):
    lang = users.get(str(uid), {}).get('lang', 'العربية 🇮🇶')
    wait_msgs = {
        "العربية 🇮🇶": "💡 جاري تلخيص آخر الأخبار في جملة واحدة...",
        "English 🇬🇧":  "💡 Summarizing latest news in one line...",
        "Русский 🇷🇺":  "💡 Составляем краткое резюме новостей...",
        "فارسی 🇮🇷":    "💡 در حال خلاصه کردن اخبار...",
        "हिन्दी 🇮🇳":   "💡 एक लाइन में खबरें...",
        "Português 🇧🇷": "💡 Resumindo as últimas notícias...",
        "Türkçe 🇹🇷":   "💡 Haberler özetleniyor...",
        "اردو 🇵🇰":      "💡 خبریں خلاصہ کر رہے ہیں...",
        "Deutsch 🇩🇪":  "💡 Nachrichten werden zusammengefasst...",
        "Українська 🇺🇦":"💡 Готуємо стислий огляд новин...",
        "Italiano 🇮🇹": "💡 Riassunto delle ultime notizie...",
        "Español 🇲🇽":  "💡 Resumiendo las últimas noticias...",
        "Français 🇫🇷": "💡 Résumé des dernières actualités...",
    }
    msg = bot.send_message(uid, wait_msgs.get(lang, wait_msgs["English 🇬🇧"]))
    items = _get_quick_news(uid, count=6)
    if not items:
        try: bot.edit_message_text("⚠️ لا توجد أخبار متاحة الآن.", uid, msg.message_id)
        except Exception: pass
        return
    titles_text = "\n".join([f"- {i['title']}" for i in items[:6]])
    write_lang = 'Arabic' if ('عربية' in lang or 'English' not in lang) else 'English'
    zbda_result = None
    if _AI_MODEL:
        try:
            prompt = f"""بناءً على هذه العناوين الإخبارية:
{titles_text}

اكتب جملة واحدة فقط (لا أكثر من 25 كلمة) تلخّص أبرز ما يحدث الآن.
اكتب بلغة: {write_lang}.
لا تضع أي مقدمة — الجملة فقط."""
            _resp_ai = _ai_generate(prompt)
            zbda_result = (_resp_ai or "")
        except Exception:
            zbda_result = None
    if not zbda_result:
        # Fallback: أول خبر فقط
        zbda_result = items[0]["title"] if items else "لا توجد أخبار متاحة."
    title_map = {
        "العربية 🇮🇶": "💡 *زبدة الموضوع:*",
        "English 🇬🇧":  "💡 *Quick Summary:*",
        "Русский 🇷🇺":  "💡 *Вкратце:*",
        "فارسی 🇮🇷":    "💡 *خلاصه:*",
        "हिन्दी 🇮🇳":   "💡 *संक्षेप:*",
        "Português 🇧🇷": "💡 *Resumo:*",
        "Türkçe 🇹🇷":   "💡 *Özet:*",
        "اردو 🇵🇰":      "💡 *خلاصہ:*",
        "Deutsch 🇩🇪":  "💡 *Kurzfassung:*",
        "Українська 🇺🇦":"💡 *Коротко:*",
        "Italiano 🇮🇹": "💡 *In breve:*",
        "Español 🇲🇽":  "💡 *En resumen:*",
        "Français 🇫🇷": "💡 *En bref:*",
    }
    reply = f"{title_map.get(lang, '💡 *Summary:*')}\n\n_{zbda_result}_"
    try:
        bot.edit_message_text(reply, uid, msg.message_id, parse_mode="Markdown")
    except Exception:
        bot.send_message(uid, reply, parse_mode="Markdown")

# ── 4. 🔮 قبل ما يصير ──────────────────────────────────────
def _handle_before_happen(uid):
    lang = users.get(str(uid), {}).get('lang', 'العربية 🇮🇶')
    wait_msgs = {
        "العربية 🇮🇶": "🔮 أُحلّل المشهد وأتوقع ما قد يحدث...",
        "English 🇬🇧":  "🔮 Analyzing the scene and predicting what might happen...",
        "Русский 🇷🇺":  "🔮 Анализируем ситуацию и предсказываем возможные события...",
        "فارسی 🇮🇷":    "🔮 در حال پیش‌بینی رویدادها...",
        "हिन्दी 🇮🇳":   "🔮 भविष्यवाणी की जा रही है...",
        "Português 🇧🇷": "🔮 Analisando e prevendo o que pode acontecer...",
        "Türkçe 🇹🇷":   "🔮 Ne olabileceği tahmin ediliyor...",
        "اردو 🇵🇰":      "🔮 پیش گوئی کی جا رہی ہے...",
        "Deutsch 🇩🇪":  "🔮 Analysiere und prognostiziere mögliche Ereignisse...",
        "Українська 🇺🇦":"🔮 Аналізуємо ситуацію та прогнозуємо події...",
        "Italiano 🇮🇹": "🔮 Analisi e previsione di cosa potrebbe accadere...",
        "Español 🇲🇽":  "🔮 Analizando y prediciendo lo que podría pasar...",
        "Français 🇫🇷": "🔮 Analyse et prévision de ce qui pourrait arriver...",
    }
    msg = bot.send_message(uid, wait_msgs.get(lang, wait_msgs["English 🇬🇧"]))
    items = _get_quick_news(uid, count=5)
    if not items:
        try: bot.edit_message_text("⚠️ لا توجد أخبار متاحة الآن.", uid, msg.message_id)
        except Exception: pass
        return
    titles_text = "\n".join([f"- {i['title']}" for i in items[:5]])
    write_lang = 'Arabic' if ('عربية' in lang or 'English' not in lang) else 'English'
    prediction = None
    if _AI_MODEL:
        try:
            prompt = f"""بناءً على هذه الأخبار الأخيرة:
{titles_text}

توقّع 3 أشياء قد تحدث قريباً — بشكل بسيط ومباشر جداً.
اكتب على شكل:
• ممكن يصير: [توقع قصير]
• ممكن يصير: [توقع قصير]
• ممكن يصير: [توقع قصير]

اكتب بلغة: {write_lang}.
لا مقدمات — ابدأ مباشرة بالنقاط."""
            _resp_ai = _ai_generate(prompt)
            prediction = (_resp_ai or "")
        except Exception:
            prediction = None
    if not prediction:
        # Fallback ذكي بدون AI — يعتمد على محتوى الأخبار الفعلية
        _fallback_parts = []
        for _item in items[:3]:
            _t = _item.get('title', '')
            if _t:
                _fb = _smart_fallback_next(_t)
                # استخرج أول سطر ذي محتوى من الـ fallback
                for _line in _fb.splitlines():
                    _l = _line.strip()
                    if _l and not _l.startswith('🔮') and not _l.startswith('•') is False:
                        _fallback_parts.append(_l)
                        break
        if not _fallback_parts:
            _fallback_parts = [
                "• ممكن يصير: تصريحات رسمية أو موقف حكومي قريباً",
                "• ممكن يصير: تطورات ميدانية خلال الـ 24 ساعة القادمة",
                "• ممكن يصير: تغطية إعلامية موسّعة لهذه الملفات",
            ]
        # دمج الـ fallbacks من مصادر الأخبار الحقيقية
        prediction = _smart_fallback_next(items[0].get('title', '')) if items else "\n".join(_fallback_parts)
    title_map = {
        "العربية 🇮🇶": "🔮 *قبل ما يصير...*\n\n_بناءً على المشهد الحالي:_\n\n",
        "English 🇬🇧":  "🔮 *What Might Happen...*\n\n_Based on current situation:_\n\n",
        "Русский 🇷🇺":  "🔮 *Что может случиться...*\n\n_На основе текущей ситуации:_\n\n",
        "فارسی 🇮🇷":    "🔮 *چه ممکن است رخ دهد...*\n\n",
        "हिन्दी 🇮🇳":   "🔮 *क्या हो सकता है...*\n\n",
        "Português 🇧🇷": "🔮 *O que pode acontecer...*\n\n_Com base na situação atual:_\n\n",
        "Türkçe 🇹🇷":   "🔮 *Ne olabilir...*\n\n_Mevcut duruma göre:_\n\n",
        "اردو 🇵🇰":      "🔮 *کیا ہو سکتا ہے...*\n\n",
        "Deutsch 🇩🇪":  "🔮 *Was könnte passieren...*\n\n_Basierend auf der aktuellen Lage:_\n\n",
        "Українська 🇺🇦":"🔮 *Що може статися...*\n\n_На основі поточної ситуації:_\n\n",
        "Italiano 🇮🇹": "🔮 *Cosa potrebbe succedere...*\n\n_In base alla situazione attuale:_\n\n",
        "Español 🇲🇽":  "🔮 *Qué podría pasar...*\n\n_Basado en la situación actual:_\n\n",
        "Français 🇫🇷": "🔮 *Ce qui pourrait arriver...*\n\n_En fonction de la situation actuelle:_\n\n",
    }
    reply = title_map.get(lang, "🔮 *Predictions:*\n\n") + prediction
    try:
        bot.edit_message_text(reply[:4096], uid, msg.message_id, parse_mode="Markdown")
    except Exception:
        bot.send_message(uid, reply[:4096], parse_mode="Markdown")

# ── 5. 🖼 خبر بصورة ─────────────────────────────────────────
def _handle_imgcard(uid):
    lang = users.get(str(uid), {}).get('lang', 'العربية 🇮🇶')
    sent_count = 0
    seen = set()
    for feed_url in list(RSS.get(lang, RSS.get("العربية 🇮🇶", [])))[:20]:
        try:
            feed = _parse_feed(feed_url)
            if not feed: continue
            for entry in feed.entries[:10]:
                title = (getattr(entry, 'title', '') or '').strip()
                link  = (getattr(entry, 'link',  '') or '').strip()
                summ  = (getattr(entry, 'summary', '') or '').strip()
                if not title or title in seen: continue
                # البحث عن صورة في الـ enclosures أو media أو في الـ summary
                img_url = None
                if hasattr(entry, 'media_content') and entry.media_content:
                    img_url = entry.media_content[0].get('url')
                elif hasattr(entry, 'enclosures') and entry.enclosures:
                    for enc in entry.enclosures:
                        if enc.get('type', '').startswith('image'):
                            img_url = enc.get('href') or enc.get('url')
                            break
                elif hasattr(entry, 'media_thumbnail') and entry.media_thumbnail:
                    img_url = entry.media_thumbnail[0].get('url')
                if not img_url: continue
                seen.add(title)
                pub = _pub_dt_from_item(entry)
                time_str = pub.strftime('%H:%M') if pub else ""
                caption_lines = [f"📰 *{title[:200]}*"]
                if summ:
                    caption_lines.append(f"\n_{summ[:280]}_")
                if time_str:
                    caption_lines.append(f"\n⏱ {time_str}")
                if link:
                    caption_lines.append(f"\n🔗 [اقرأ الخبر كاملاً]({link})")
                caption = "\n".join(caption_lines)[:1024]
                try:
                    bot.send_photo(uid, img_url, caption=caption, parse_mode="Markdown")
                    sent_count += 1
                    if sent_count >= 3:
                        return
                except Exception as _exc:
                    _log_exc(_exc)
        except Exception as _exc:
            _log_exc(_exc)
    if sent_count == 0:
        # fallback: أخبار نصية لو ما في صور
        items = _get_quick_news(uid, count=3)
        no_img_map = {
            "العربية 🇮🇶": "🖼 *خبر بصورة*\n\n_(لا توجد صور متاحة الآن — إليك آخر الأخبار:)_\n\n",
            "English 🇬🇧":  "🖼 *News Card*\n\n_(No images available now — here are the latest news:)_\n\n",
        }
        header = no_img_map.get(lang, no_img_map["English 🇬🇧"])
        lines = [f"📰 *{i['title']}*\n🔗 [اقرأ]({i['link']})" for i in items if i.get('link')]
        bot.send_message(uid, header + "\n\n".join(lines), parse_mode="Markdown", disable_web_page_preview=False)

# ══════════════════════════════════════════════════════════════
# 🗺 نظام اختيار الأخبار — 6 فئات × 13 لغة
# ══════════════════════════════════════════════════════════════

# الكلمات المفتاحية لكل فئة (مُوسَّعة)
_CATEGORY_KEYWORDS = {
    "all":     [],  # لا فلتر — كل الأخبار
    "world":   [
        "world","international","global","دولي","عالم","أوروبا","أمريكا","الأمم المتحدة",
        "الصين","روسيا","ناتو","أممي","أوكرانيا","إيران","تركيا","أوروبي","أطلسي",
        "أسيا","افريقيا","قمة","مجلس الأمن","أجنبي","خارجية",
        "nato","united nations","europe","asia","africa","summit","ukraine","foreign",
    ],
    "arab":    [
        "عربي","العراق","سوريا","لبنان","مصر","الخليج","السعودية","فلسطين","اليمن",
        "الأردن","المغرب","الإمارات","قطر","الكويت","البحرين","عمان","ليبيا","تونس",
        "الجزائر","السودان","الصومال","عربي","بغداد","دمشق","بيروت","القاهرة","غزة",
        "Arab","Iraq","Syria","Lebanon","Egypt","Saudi","Palestine","Yemen","Gulf",
    ],
    "economy": [
        "اقتصاد","نفط","دولار","بورصة","أسواق","بنك","تضخم","عملة","ميزانية","استثمار",
        "تجارة","سهم","ذهب","نمو","ركود","تصدير","استيراد","قرض","ديون","ريال","ين",
        "economy","oil","market","dollar","finance","bank","inflation","trade","gold",
        "budget","investment","stock","gdp","recession","export","import","currency",
    ],
    "sports":  [
        "رياضة","كرة قدم","مباراة","فريق","هدف","ملعب","منتخب","دوري","بطولة","لاعب",
        "ميسي","رونالدو","ريال مدريد","برشلونة","ليفربول","مانشستر","الدوري","كأس","أولمبياد",
        "كرة السلة","كرة الطائرة","تنس","سباحة","ملاكمة","أتلتيكو","أرسنال","يوفنتوس",
        "sports","football","soccer","match","team","goal","league","tournament","player",
        "FIFA","UEFA","Champions League","World Cup","NBA","tennis","olympic","boxing",
    ],
    "scitech": [
        "علوم","تقنية","تكنولوجيا","ذكاء اصطناعي","هاتف","إنترنت","تطبيق","برنامج","روبوت",
        "فضاء","ناسا","كوكب","اكتشاف","بحث علمي","طاقة","مناخ","بيئة","نووي","كوانتم",
        "ميتا","آبل","غوغل","سامسونغ","تسلا","إيلون ماسك","برمجة","سيبراني","هكر",
        "science","tech","technology","AI","artificial intelligence","space","NASA","robot",
        "discovery","research","app","software","climate","energy","cyber","quantum","bitcoin",
    ],
}

# تسميات الفئات بـ 13 لغة
_NEWS_CATS_LABELS = {
    "all":     {"العربية 🇮🇶":"📰 كل الأخبار","English 🇬🇧":"📰 All News","Русский 🇷🇺":"📰 Все новости","فارسی 🇮🇷":"📰 همه اخبار","हिन्दी 🇮🇳":"📰 सभी समाचार","Português 🇧🇷":"📰 Todas as Notícias","Türkçe 🇹🇷":"📰 Tüm Haberler","اردو 🇵🇰":"📰 تمام خبریں","Deutsch 🇩🇪":"📰 Alle Nachrichten","Українська 🇺🇦":"📰 Всі новини","Italiano 🇮🇹":"📰 Tutte le Notizie","Español 🇲🇽":"📰 Todas las Noticias","Français 🇫🇷":"📰 Toutes les Actualités"},
    "world":   {"العربية 🇮🇶":"🌍 عالمي","English 🇬🇧":"🌍 World","Русский 🇷🇺":"🌍 Мир","فارسی 🇮🇷":"🌍 جهانی","हिन्दी 🇮🇳":"🌍 विश्व","Português 🇧🇷":"🌍 Mundial","Türkçe 🇹🇷":"🌍 Dünya","اردو 🇵🇰":"🌍 عالمی","Deutsch 🇩🇪":"🌍 Welt","Українська 🇺🇦":"🌍 Світ","Italiano 🇮🇹":"🌍 Mondo","Español 🇲🇽":"🌍 Mundial","Français 🇫🇷":"🌍 Monde"},
    "arab":    {"العربية 🇮🇶":"🇮🇶 عربي","English 🇬🇧":"🇮🇶 Arab","Русский 🇷🇺":"🇮🇶 Арабский","فارسی 🇮🇷":"🇮🇶 عربی","हिन्दी 🇮🇳":"🇮🇶 अरब","Português 🇧🇷":"🇮🇶 Árabe","Türkçe 🇹🇷":"🇮🇶 Arap","اردو 🇵🇰":"🇮🇶 عربی","Deutsch 🇩🇪":"🇮🇶 Arabisch","Українська 🇺🇦":"🇮🇶 Арабський","Italiano 🇮🇹":"🇮🇶 Arabo","Español 🇲🇽":"🇮🇶 Árabe","Français 🇫🇷":"🇮🇶 Arabe"},
    "economy": {"العربية 🇮🇶":"💰 اقتصاد","English 🇬🇧":"💰 Economy","Русский 🇷🇺":"💰 Экономика","فارسی 🇮🇷":"💰 اقتصاد","हिन्दी 🇮🇳":"💰 अर्थव्यवस्था","Português 🇧🇷":"💰 Economia","Türkçe 🇹🇷":"💰 Ekonomi","اردو 🇵🇰":"💰 معیشت","Deutsch 🇩🇪":"💰 Wirtschaft","Українська 🇺🇦":"💰 Економіка","Italiano 🇮🇹":"💰 Economia","Español 🇲🇽":"💰 Economía","Français 🇫🇷":"💰 Économie"},
    "sports":  {"العربية 🇮🇶":"⚽ رياضة ومباريات","English 🇬🇧":"⚽ Sports & Matches","Русский 🇷🇺":"⚽ Спорт и матчи","فارسی 🇮🇷":"⚽ ورزش و مسابقات","हिन्दी 🇮🇳":"⚽ खेल और मैच","Português 🇧🇷":"⚽ Esportes e Jogos","Türkçe 🇹🇷":"⚽ Spor ve Maçlar","اردو 🇵🇰":"⚽ کھیل اور میچ","Deutsch 🇩🇪":"⚽ Sport und Spiele","Українська 🇺🇦":"⚽ Спорт і матчі","Italiano 🇮🇹":"⚽ Sport e Partite","Español 🇲🇽":"⚽ Deportes y Partidos","Français 🇫🇷":"⚽ Sports et Matchs"},
    "scitech": {"العربية 🇮🇶":"🔬 علوم وتقنية","English 🇬🇧":"🔬 Science & Tech","Русский 🇷🇺":"🔬 Наука и технологии","فارسی 🇮🇷":"🔬 علوم و فناوری","हिन्दी 🇮🇳":"🔬 विज्ञान और तकनीक","Português 🇧🇷":"🔬 Ciência e Tecnologia","Türkçe 🇹🇷":"🔬 Bilim ve Teknoloji","اردو 🇵🇰":"🔬 سائنس اور ٹیکنالوجی","Deutsch 🇩🇪":"🔬 Wissenschaft & Technik","Українська 🇺🇦":"🔬 Наука і технології","Italiano 🇮🇹":"🔬 Scienza e Tecnologia","Español 🇲🇽":"🔬 Ciencia y Tecnología","Français 🇫🇷":"🔬 Sciences et Technologie"},
}

_ALL_CAT_KEYS = ["all", "world", "arab", "economy", "sports", "scitech"]

# رسائل القائمة بـ 13 لغة
_NEWS_SELECT_TITLES = {
    "العربية 🇮🇶": "📋 *اختيار الأخبار*\n\nاختر الفئات التي تريد متابعتها:\n_(يمكن اختيار أكثر من فئة)_",
    "English 🇬🇧":  "📋 *Select News Types*\n\nChoose the categories you want to follow:\n_(multiple selections allowed)_",
    "Русский 🇷🇺":  "📋 *Выбор новостей*\n\nВыберите категории для отслеживания:\n_(можно выбрать несколько)_",
    "فارسی 🇮🇷":    "📋 *انتخاب خبر*\n\nدسته‌بندی‌هایی که می‌خواهید دنبال کنید:\n_(می‌توانید چندتا انتخاب کنید)_",
    "हिन्दी 🇮🇳":   "📋 *समाचार चुनें*\n\nकौन सी श्रेणियाँ फ़ॉलो करना चाहते हैं:\n_(एक से ज़्यादा चुन सकते हैं)_",
    "Português 🇧🇷": "📋 *Selecionar Notícias*\n\nEscolha as categorias que deseja acompanhar:\n_(múltiplas seleções permitidas)_",
    "Türkçe 🇹🇷":   "📋 *Haber Türü Seçin*\n\nTakip etmek istediğiniz kategorileri seçin:\n_(birden fazla seçilebilir)_",
    "اردو 🇵🇰":      "📋 *خبریں منتخب کریں*\n\nوہ زمرے منتخب کریں جن کو فالو کرنا چاہتے ہیں:\n_(ایک سے زیادہ منتخب کر سکتے ہیں)_",
    "Deutsch 🇩🇪":  "📋 *Nachrichten auswählen*\n\nWählen Sie die Kategorien aus, die Sie verfolgen möchten:\n_(Mehrfachauswahl möglich)_",
    "Українська 🇺🇦":"📋 *Вибір новин*\n\nОберіть категорії для відстеження:\n_(можна обрати декілька)_",
    "Italiano 🇮🇹": "📋 *Seleziona Notizie*\n\nScegli le categorie da seguire:\n_(selezione multipla consentita)_",
    "Español 🇲🇽":  "📋 *Seleccionar Noticias*\n\nElige las categorías que deseas seguir:\n_(puedes seleccionar varias)_",
    "Français 🇫🇷": "📋 *Sélectionner Actualités*\n\nChoisissez les catégories que vous souhaitez suivre:\n_(sélection multiple autorisée)_",
}
_NEWS_SELECT_SAVED = {
    "العربية 🇮🇶": "✅ *تم حفظ تفضيلاتك!*\n\nستصلك الأخبار حسب اختيارك:",
    "English 🇬🇧":  "✅ *Preferences saved!*\n\nYou'll receive news based on your selection:",
    "Русский 🇷🇺":  "✅ *Настройки сохранены!*\n\nВы будете получать новости по выбранным категориям:",
    "فارسی 🇮🇷":    "✅ *تنظیمات ذخیره شد!*\n\nاخبار بر اساس انتخاب شما ارسال می‌شود:",
    "हिन्दी 🇮🇳":   "✅ *प्राथमिकताएँ सहेजी गईं!*\n\nआपकी पसंद के अनुसार समाचार मिलेंगे:",
    "Português 🇧🇷": "✅ *Preferências salvas!*\n\nVocê receberá notícias de acordo com sua seleção:",
    "Türkçe 🇹🇷":   "✅ *Tercihler kaydedildi!*\n\nSeçiminize göre haberler gelecek:",
    "اردو 🇵🇰":      "✅ *ترجیحات محفوظ ہو گئیں!*\n\nآپ کے انتخاب کے مطابق خبریں ملیں گی:",
    "Deutsch 🇩🇪":  "✅ *Einstellungen gespeichert!*\n\nSie erhalten Nachrichten nach Ihrer Auswahl:",
    "Українська 🇺🇦":"✅ *Налаштування збережено!*\n\nВи будете отримувати новини за вашим вибором:",
    "Italiano 🇮🇹": "✅ *Preferenze salvate!*\n\nRiceverai notizie in base alla tua selezione:",
    "Español 🇲🇽":  "✅ *¡Preferencias guardadas!*\n\nRecibirás noticias según tu selección:",
    "Français 🇫🇷": "✅ *Préférences enregistrées!*\n\nVous recevrez des actualités selon votre sélection:",
}
_NEWS_SELECT_SAVE_BTN = {
    "العربية 🇮🇶":"💾 حفظ الاختيارات","English 🇬🇧":"💾 Save","Русский 🇷🇺":"💾 Сохранить",
    "فارسی 🇮🇷":"💾 ذخیره","हिन्दी 🇮🇳":"💾 सहेजें","Português 🇧🇷":"💾 Salvar",
    "Türkçe 🇹🇷":"💾 Kaydet","اردو 🇵🇰":"💾 محفوظ کریں","Deutsch 🇩🇪":"💾 Speichern",
    "Українська 🇺🇦":"💾 Зберегти","Italiano 🇮🇹":"💾 Salva","Español 🇲🇽":"💾 Guardar",
    "Français 🇫🇷":"💾 Enregistrer",
}

def _build_news_cats_keyboard(uid, lang):
    """يبني inline keyboard بـ 6 فئات قابلة للتفعيل/الإيقاف"""
    saved_cats = users.get(str(uid), {}).get("news_cats", _ALL_CAT_KEYS[:])  # default: كل الفئات
    markup = types.InlineKeyboardMarkup(row_width=2)
    buttons = []
    for cat in _ALL_CAT_KEYS:
        label = _NEWS_CATS_LABELS.get(cat, {}).get(lang, cat)
        active = cat in saved_cats
        check  = "✅ " if active else "☑️ "
        buttons.append(types.InlineKeyboardButton(f"{check}{label}", callback_data=f"ncat_{cat}"))
    # 3 rows of 2
    for i in range(0, len(buttons), 2):
        row = buttons[i:i+2]
        markup.add(*row)
    save_txt = _NEWS_SELECT_SAVE_BTN.get(lang, "💾 Save")
    markup.add(types.InlineKeyboardButton(save_txt, callback_data="ncat_save"))
    return markup

def _send_news_cats_menu(uid):
    """يرسل قائمة اختيار الأخبار"""
    lang = users.get(str(uid), {}).get('lang', 'العربية 🇮🇶')
    title = _NEWS_SELECT_TITLES.get(lang, _NEWS_SELECT_TITLES["English 🇬🇧"])
    kb = _build_news_cats_keyboard(uid, lang)
    bot.send_message(uid, title, parse_mode="Markdown", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("ncat_"))
def cb_news_cats(call):
    uid = call.from_user.id
    data = call.data
    lang = users.get(str(uid), {}).get('lang', 'العربية 🇮🇶')

    if data == "ncat_save":
        saved_cats = users.get(str(uid), {}).get("news_cats", _ALL_CAT_KEYS[:])
        if not saved_cats:
            saved_cats = _ALL_CAT_KEYS[:]
            users[str(uid)]["news_cats"] = saved_cats
        _db_save_all_users(users)
        # بناء ملخص الاختيار
        cat_names = [_NEWS_CATS_LABELS.get(c, {}).get(lang, c) for c in saved_cats]
        saved_msg = _NEWS_SELECT_SAVED.get(lang, "✅ Saved!") + "\n" + " • ".join(cat_names)
        bot.answer_callback_query(call.id, "✅ تم الحفظ!" if 'عربية' in lang else "✅ Saved!")
        try:
            bot.edit_message_text(saved_msg, call.message.chat.id, call.message.message_id,
                                  parse_mode="Markdown")
        except Exception:
            bot.send_message(uid, saved_msg, parse_mode="Markdown")
        return

    # toggle category
    cat = data[5:]  # remove "ncat_"
    if cat not in _ALL_CAT_KEYS:
        bot.answer_callback_query(call.id)
        return

    if "news_cats" not in users.get(str(uid), {}):
        users.setdefault(str(uid), {})["news_cats"] = _ALL_CAT_KEYS[:]

    cats = users[str(uid)]["news_cats"]

    # Special: if "all" selected → reset to all cats
    if cat == "all":
        if "all" in cats and len(cats) == len(_ALL_CAT_KEYS):
            # already all — deselect all except "all"
            cats = ["all"]
        else:
            cats = _ALL_CAT_KEYS[:]
    else:
        # toggle specific cat
        if cat in cats:
            cats.remove(cat)
            # if nothing left, keep at least "all"
            if not cats:
                cats = ["all"]
        else:
            cats.append(cat)
            # if all specific cats selected, add "all"
            if all(c in cats for c in _ALL_CAT_KEYS[1:]):
                if "all" not in cats:
                    cats.append("all")

    users[str(uid)]["news_cats"] = cats
    bot.answer_callback_query(call.id)
    try:
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id,
                                      reply_markup=_build_news_cats_keyboard(uid, lang))
    except Exception as _exc:
        _log_exc(_exc)
_CATEGORY_HEADERS = {
    "world": {
        "العربية 🇮🇶":"🌍 *أخبار عالمية*\n\n","English 🇬🇧":"🌍 *World News*\n\n",
        "Русский 🇷🇺":"🌍 *Мировые новости*\n\n","فارسی 🇮🇷":"🌍 *اخبار جهانی*\n\n",
        "हिन्दी 🇮🇳":"🌍 *विश्व समाचार*\n\n","Português 🇧🇷":"🌍 *Notícias Mundiais*\n\n",
        "Türkçe 🇹🇷":"🌍 *Dünya Haberleri*\n\n","اردو 🇵🇰":"🌍 *عالمی خبریں*\n\n",
        "Deutsch 🇩🇪":"🌍 *Weltnachrichten*\n\n","Українська 🇺🇦":"🌍 *Світові новини*\n\n",
        "Italiano 🇮🇹":"🌍 *Notizie Mondiali*\n\n","Español 🇲🇽":"🌍 *Noticias Mundiales*\n\n",
        "Français 🇫🇷":"🌍 *Actualités Mondiales*\n\n",
    },
    "arab": {
        "العربية 🇮🇶":"🇮🇶 *أخبار عربية*\n\n","English 🇬🇧":"🇮🇶 *Arab News*\n\n",
        "Русский 🇷🇺":"🇮🇶 *Арабские новости*\n\n","فارسی 🇮🇷":"🇮🇶 *اخبار عربی*\n\n",
        "हिन्दी 🇮🇳":"🇮🇶 *अरब समाचार*\n\n","Português 🇧🇷":"🇮🇶 *Notícias Árabes*\n\n",
        "Türkçe 🇹🇷":"🇮🇶 *Arap Haberleri*\n\n","اردو 🇵🇰":"🇮🇶 *عربی خبریں*\n\n",
        "Deutsch 🇩🇪":"🇮🇶 *Arabische Nachrichten*\n\n","Українська 🇺🇦":"🇮🇶 *Арабські новини*\n\n",
        "Italiano 🇮🇹":"🇮🇶 *Notizie Arabe*\n\n","Español 🇲🇽":"🇮🇶 *Noticias Árabes*\n\n",
        "Français 🇫🇷":"🇮🇶 *Actualités Arabes*\n\n",
    },
    "economy": {
        "العربية 🇮🇶":"💰 *أخبار اقتصادية*\n\n","English 🇬🇧":"💰 *Economy News*\n\n",
        "Русский 🇷🇺":"💰 *Экономические новости*\n\n","فارسی 🇮🇷":"💰 *اخبار اقتصادی*\n\n",
        "हिन्दी 🇮🇳":"💰 *आर्थिक समाचार*\n\n","Português 🇧🇷":"💰 *Notícias Econômicas*\n\n",
        "Türkçe 🇹🇷":"💰 *Ekonomi Haberleri*\n\n","اردو 🇵🇰":"💰 *معاشی خبریں*\n\n",
        "Deutsch 🇩🇪":"💰 *Wirtschaftsnachrichten*\n\n","Українська 🇺🇦":"💰 *Економічні новини*\n\n",
        "Italiano 🇮🇹":"💰 *Notizie Economiche*\n\n","Español 🇲🇽":"💰 *Noticias Económicas*\n\n",
        "Français 🇫🇷":"💰 *Actualités Économiques*\n\n",
    },
    "sports": {
        "العربية 🇮🇶":"⚽ *أخبار رياضية*\n\n","English 🇬🇧":"⚽ *Sports News*\n\n",
        "Русский 🇷🇺":"⚽ *Спортивные новости*\n\n","فارسی 🇮🇷":"⚽ *اخبار ورزشی*\n\n",
        "हिन्दी 🇮🇳":"⚽ *खेल समाचार*\n\n","Português 🇧🇷":"⚽ *Notícias Esportivas*\n\n",
        "Türkçe 🇹🇷":"⚽ *Spor Haberleri*\n\n","اردو 🇵🇰":"⚽ *کھیلوں کی خبریں*\n\n",
        "Deutsch 🇩🇪":"⚽ *Sportnachrichten*\n\n","Українська 🇺🇦":"⚽ *Спортивні новини*\n\n",
        "Italiano 🇮🇹":"⚽ *Notizie Sportive*\n\n","Español 🇲🇽":"⚽ *Noticias Deportivas*\n\n",
        "Français 🇫🇷":"⚽ *Actualités Sportives*\n\n",
    },
}

def _handle_category_news(uid, category: str):
    lang = users.get(str(uid), {}).get('lang', 'العربية 🇮🇶')
    keywords = _CATEGORY_KEYWORDS.get(category, [])
    items = _get_quick_news(uid, count=7, keywords=keywords)
    cat_headers = _CATEGORY_HEADERS.get(category, {})
    header = cat_headers.get(lang, cat_headers.get("English 🇬🇧", f"📰 *{category.title()} News*\n\n"))
    if not items:
        bot.send_message(uid, header + ("⚠️ لا توجد أخبار في هذه الفئة الآن." if 'عربية' in lang else "⚠️ No news in this category now."))
        return
    lines = []
    for i, item in enumerate(items, 1):
        t_ = item["title"]
        l_ = item.get("link", "")
        pub = item.get("pub")
        time_str = pub.strftime('%H:%M') if pub else ""
        line = f"{i}. "
        if l_:
            line += f"[{t_}]({l_})"
        else:
            line += t_
        if time_str:
            line += f"  `{time_str}`"
        lines.append(line)
    msg = header + "\n".join(lines)
    bot.send_message(uid, msg[:4096], parse_mode="Markdown", disable_web_page_preview=True)


# ======== اختيار طريقة الموقع: callback inline ========
@bot.callback_query_handler(func=lambda c: c.data in ("loc_choose_prov", "loc_share_gps"))
def send_hourly_news(uid):
    user = users.get(str(uid))
    if not user:
        return
    # ── فحص Feature Flag: broadcast ──
    if not _is_feature_enabled("broadcast", uid):
        return   # البث متوقف من الداشبورد — لا نُبلّغ المستخدم
    lang    = user.get("lang", "English 🇬🇧")
    country = user.get("country", "")
    feeds   = _get_feeds_for_user(lang, country)
    if not feeds:
        bot.send_message(uid, t(lang, "no_source"))
        return
    sent = user.setdefault("sent_news", {})
    count = 0
    for feed_url in feeds:
        try:
            feed = _parse_feed(feed_url)
            if not feed:
                continue
            src_name = get_source_name_from_feed(feed, feed_url)
            for item in feed.entries[:3]:
                if not hasattr(item, 'link') or item.link in sent:
                    continue
                title = getattr(item, 'title', '').strip()
                if not title:
                    continue
                if not _title_in_lang(title, lang):
                    continue
                item_sum_chk = getattr(item, 'summary', '') or ''
                if not _news_matches_user_cats(title, item_sum_chk, uid):
                    continue
                pub_struct = getattr(item, 'published_parsed', None) or getattr(item, 'updated_parsed', None)
                pub_dt = None
                if pub_struct:
                    try:
                        import calendar as _cal
                        pub_dt = datetime.datetime.utcfromtimestamp(_cal.timegm(pub_struct))
                    except Exception:
                        pub_dt = None
                pub_time_str = _format_pub_time(pub_dt, lang=lang)
                sent[item.link] = time.time()
                item_sum = getattr(item, 'summary', '') or getattr(item, 'description', '')
                markup = make_news_share_markup(item.link, title, lang, item_sum)
                news_body = format_news_item(t(lang, "label_news"), title, lang, src_name, pub_time_str, summary=item_sum)
                # FIX: تباعد بين الأخبار المتعددة بنفس الطلب (لا تصل كلها دفعة واحدة)
                if count > 0:
                    time.sleep(_NEWS_SPACING_SECONDS)
                # لا صورة من المصدر → شعار الوكالة الافتراضي بدل رسالة بلا صورة إطلاقاً
                item_img = _extract_entry_image(item) or DEFAULT_NEWS_IMAGE
                if item_img:
                    # صورة الخبر جاهزة من الـ RSS نفسه — نرسلها مباشرة بدل زر "صورة المقال"
                    try:
                        if isinstance(item_img, str) and os.path.isfile(item_img):
                            with open(item_img, "rb") as _f:
                                bot.send_photo(uid, _f, caption=news_body[:1024], parse_mode="Markdown", reply_markup=markup)
                        else:
                            bot.send_photo(uid, item_img, caption=news_body[:1024], parse_mode="Markdown", reply_markup=markup)
                    except Exception as _img_exc:
                        _log_exc(_img_exc)
                        bot.send_message(uid, news_body, parse_mode="Markdown", reply_markup=markup)
                else:
                    bot.send_message(uid, news_body, parse_mode="Markdown", reply_markup=markup)
                # ── نشر تلقائي على فيسبوك + انستغرام ──
                if _social_settings.get("enabled", True):
                    _post_social_media(title, item.link, lang)
                count += 1
        except Exception as _exc:
            _log_exc(_exc)  # فشل مصدر واحد لا يوقف باقي المصادر
    if count == 0:
        bot.send_message(uid, t(lang, "no_news"))
    else:
        _db_save_all_users(users)

def send_all_news(uid):
    user = users.get(str(uid))
    if not user:
        return
    lang    = user.get("lang", "English 🇬🇧")
    country = user.get("country", "")
    feeds   = _get_feeds_for_user(lang, country)
    if not feeds:
        bot.send_message(uid, t(lang, "no_source"))
        return
    sent = user.setdefault("sent_news", {})
    count = 0
    for feed_url in feeds:
        try:
            feed = _parse_feed(feed_url)
            if not feed:
                continue
            src_name = get_source_name_from_feed(feed, feed_url)
            for item in feed.entries[:15]:
                if not hasattr(item, 'link') or item.link in sent:
                    continue
                title = getattr(item, 'title', '').strip()
                if not title or not _title_in_lang(title, lang):
                    continue
                item_sum = getattr(item, 'summary', '') or getattr(item, 'description', '')
                if not _news_matches_user_cats(title, item_sum, uid):
                    continue
                pub_struct = getattr(item, 'published_parsed', None) or getattr(item, 'updated_parsed', None)
                pub_dt = None
                if pub_struct:
                    try:
                        import calendar as _cal
                        pub_dt = datetime.datetime.utcfromtimestamp(_cal.timegm(pub_struct))
                    except Exception:
                        pub_dt = None
                pub_time_str = _format_pub_time(pub_dt, lang=lang)
                sent[item.link] = time.time()
                markup = make_news_share_markup(item.link, title, lang, item_sum)
                bot.send_message(uid, format_news_item(t(lang, "label_breaking"), title, lang, src_name, pub_time_str, summary=item_sum), parse_mode="Markdown", reply_markup=markup)
                count += 1
        except Exception as _exc:
            _log_exc(_exc)  # فشل مصدر واحد لا يوقف باقي المصادر
    if count == 0:
        bot.send_message(uid, t(lang, "no_news"))
    else:
        _db_save_all_users(users)

def send_mena_politics(uid):
    user = users.get(str(uid))
    if not user:
        return
    lang = user.get("lang", "العربية 🇮🇶")
    mena_feeds = MENA_RSS.get(lang, MENA_RSS.get("العربية 🇮🇶", []))
    sent = user.setdefault("sent_news", {})
    count = 0
    headlines_sent = []
    for feed_url in mena_feeds:
        try:
            feed = _parse_feed(feed_url)
            if feed is None:
                feed = feedparser.parse(feed_url)
            if not feed:
                continue
            for item in feed.entries[:10]:
                title = getattr(item, 'title', '').strip()
                link = getattr(item, 'link', '')
                if not link or not title:
                    continue
                if link in sent:
                    continue
                if not _title_in_lang(title, lang):
                    continue
                sent[link] = time.time()
                item_sum = getattr(item, 'summary', '') or getattr(item, 'description', '')
                markup = make_news_share_markup(link, title, lang, item_sum)
                src_name = get_source_name_from_url(feed_url)
                pub_time_str = _format_pub_time(_pub_dt_from_item(item), lang=lang)
                bot.send_message(uid, format_news_item(t(lang, "label_mena"), title, lang, src_name, pub_time_str, summary=item_sum), parse_mode="Markdown", reply_markup=markup)
                headlines_sent.append(title)
                count += 1
                if count >= 10:
                    break
        except Exception as _exc:
            _log_exc(_exc)  # فشل مصدر MENA لا يوقف باقي المصادر
        if count >= 10:
            break
    if count == 0:
        general_feeds = RSS.get(lang, [])
        for feed_url in general_feeds:
            try:
                feed = _parse_feed(feed_url)
                if feed is None:
                    feed = feedparser.parse(feed_url)
                if not feed:
                    continue
                for item in feed.entries[:30]:
                    title = getattr(item, 'title', '')
                    link = getattr(item, 'link', '')
                    if not link or link in sent:
                        continue
                    title_lower = title.lower()
                    if any(kw.lower() in title_lower for kw in MENA_KEYWORDS):
                        if not _title_in_lang(title, lang):
                            continue
                        sent[link] = time.time()
                        item_sum = getattr(item, 'summary', '') or getattr(item, 'description', '')
                        markup = make_news_share_markup(link, title, lang, item_sum)
                        src_name2 = get_source_name_from_url(feed_url)
                        pub_time_str = _format_pub_time(_pub_dt_from_item(item), lang=lang)
                        bot.send_message(uid, format_news_item(t(lang, "label_mena"), title, lang, src_name2, pub_time_str, summary=item_sum), parse_mode="Markdown", reply_markup=markup)
                        count += 1
                        if count >= 5:
                            break
            except Exception as _exc:
                _log_exc(_exc)  # فشل fallback MENA لا يوقف باقي المصادر
            if count >= 5:
                break
    if count == 0:
        bot.send_message(uid, t(lang, "no_news"))
    else:
        _db_save_all_users(users)

# ======== البث التلقائي ========
def send_daily_summary(uid):
    user = users.get(str(uid))
    if not user:
        return
    lang = user.get("lang", "English 🇬🇧")
    feeds = RSS.get(lang, [])
    if not feeds:
        bot.send_message(uid, t(lang, "no_source"))
        return
    headlines = []
    for feed_url in feeds[:3]:
        try:
            feed = _parse_feed(feed_url)
            if feed is None:
                feed = feedparser.parse(feed_url)
            if not feed:
                continue
            for item in feed.entries[:5]:
                if hasattr(item, 'title') and item.title:
                    headlines.append(item.title)
            if len(headlines) >= 15:
                break
        except Exception as _exc:
            _log_exc(_exc)  # فشل مصدر واحد لا يوقف باقي المصادر
    if not headlines:
        bot.send_message(uid, t(lang, "no_news"))
        return
    today = datetime.date.today().strftime("%Y-%m-%d")
    msg = t(lang, "daily_summary_header").format(date=today)
    for i, title in enumerate(headlines[:10], 1):
        msg += f"{i}. {title}\n\n"
    msg += f"━━━━━━━━━━━━━━━\n{BOT_SIGNATURE}"
    bot.send_message(uid, msg, parse_mode="Markdown")

# ======== أسعار العملات الرقمية ========
@bot.callback_query_handler(func=lambda c: c.data == "menu_news")
def cb_menu_news(call):
    uid = call.from_user.id
    lang = users.get(str(uid), {}).get("lang", "العربية 🇮🇶")
    bot.answer_callback_query(call.id)
    bot.send_message(call.message.chat.id, _ui("cmd_menu_news_loading", lang))
    try:
        handle_news_command_inline(uid, call.message.chat.id)
    except Exception:
        bot.send_message(call.message.chat.id, "/news")

def handle_news_command_inline(uid, chat_id):
    """FIX: كان هذا يبني رسائل مبسّطة (عنوان + وقت + رابط) بدون أزرار ولا توقيع
    InsightX، بمسار منفصل تماماً عن format_news_item/make_news_share_markup —
    نفس المسار الغني المستخدم بأمر /news. الآن يستخدم نفس الدالة send_hourly_news
    ليحصل زر "الأخبار" بالقائمة الرئيسية على نفس التنسيق الكامل بالأزرار."""
    send_hourly_news(uid)

@bot.message_handler(commands=["news"])
def cmd_news(m):
    uid = m.from_user.id
    if uid in banned: return
    if bot_paused: return
    _update_user_last_command(uid, "/news")
    if str(uid) not in users:
        welcome_user(uid)
        return
    send_hourly_news(uid)


@bot.message_handler(commands=["trending"])
def cmd_trending(m):
    uid = m.from_user.id
    if uid in banned: return
    if bot_paused: return
    _update_user_last_command(uid, "/trending")
    if str(uid) not in users:
        welcome_user(uid)
        return
    send_trending_news(uid)


def send_daily_top3(uid):
    user = users.get(str(uid))
    if not user:
        return
    lang = user.get("lang", "English 🇬🇧")
    feeds = RSS.get(lang, [])
    headlines = []
    for feed_url in feeds:
        try:
            feed = _parse_feed(feed_url)
            if feed is None:
                feed = feedparser.parse(feed_url)
            if not feed:
                continue
            for item in feed.entries[:10]:
                title = getattr(item, 'title', '').strip()
                link  = getattr(item, 'link', '').strip()
                item_sum = getattr(item, 'summary', '') or getattr(item, 'description', '')
                if title and link and _title_in_lang(title, lang):
                    pub_dt = _pub_dt_from_item(item)
                    headlines.append((title, link, item_sum, feed_url, pub_dt))
            if len(headlines) >= 10:
                break
        except Exception as _exc:
            _log_exc(_exc)
    if not headlines:
        bot.send_message(uid, t(lang, "no_news"), parse_mode="Markdown")
        return
    top3 = headlines[:3]
    SUMMARY_HEADER = {
        "العربية 🇮🇶":   "📝 *أبرز 3 أحداث اليوم*\n━━━━━━━━━━━━━━━",
        "English 🇬🇧":  "📝 *Top 3 Events Today*\n━━━━━━━━━━━━━━━",
        "Русский 🇷🇺":  "📝 *Топ-3 события дня*\n━━━━━━━━━━━━━━━",
        "فارسی 🇮🇷":    "📝 *۳ رویداد برتر امروز*\n━━━━━━━━━━━━━━━",
        "हिन्दी 🇮🇳":   "📝 *आज की शीर्ष 3 घटनाएं*\n━━━━━━━━━━━━━━━",
        "Português 🇧🇷":"📝 *Top 3 Eventos de Hoje*\n━━━━━━━━━━━━━━━",
        "Türkçe 🇹🇷":   "📝 *Bugünün En Önemli 3 Olayı*\n━━━━━━━━━━━━━━━",
        "اردو 🇵🇰":     "📝 *آج کے سرفہرست 3 واقعات*\n━━━━━━━━━━━━━━━",
        "Deutsch 🇩🇪":  "📝 *Top 3 Ereignisse des Tages*\n━━━━━━━━━━━━━━━",
        "Українська 🇺🇦":"📝 *Топ-3 події дня*\n━━━━━━━━━━━━━━━",
        "Italiano 🇮🇹": "📝 *I 3 Principali Eventi di Oggi*\n━━━━━━━━━━━━━━━",
        "Español 🇲🇽":  "📝 *Top 3 Eventos de Hoy*\n━━━━━━━━━━━━━━━",
    }
    header = SUMMARY_HEADER.get(lang, SUMMARY_HEADER["English 🇬🇧"])
    bot.send_message(uid, header, parse_mode="Markdown")
    nums = ["1️⃣", "2️⃣", "3️⃣"]
    for i, (title, link, item_sum, feed_url, pub_dt) in enumerate(top3):
        markup = make_news_share_markup(link, title, lang, item_sum)
        src_name = get_source_name_from_url(feed_url)
        pub_time_str = _format_pub_time(pub_dt, lang=lang)
        num_label = nums[i] if i < len(nums) else f"{i+1}."
        label = f"{num_label} {t(lang, 'label_news')}"
        bot.send_message(uid,
            format_news_item(label, title, lang, src_name, pub_time_str, summary=item_sum),
            parse_mode="Markdown",
            reply_markup=markup
        )


@bot.message_handler(commands=["summary"])
def cmd_summary(m):
    uid = m.from_user.id
    if uid in banned: return
    if bot_paused: return
    _update_user_last_command(uid, "/summary")
    if str(uid) not in users:
        welcome_user(uid)
        return
    send_daily_top3(uid)


@bot.callback_query_handler(func=lambda c: c.data.startswith("vote_up_") or c.data.startswith("vote_dn_"))
def cb_news_vote(call):
    uid    = call.from_user.id
    data   = call.data
    vtype  = "up" if data.startswith("vote_up_") else "down"
    vkey   = data[len("vote_up_"):] if vtype == "up" else data[len("vote_dn_"):]

    _news_votes.setdefault(vkey, {"up": 0, "down": 0, "voters": []})
    entry = _news_votes[vkey]

    if uid in entry["voters"]:
        bot.answer_callback_query(call.id, "✋ صوّتَ مسبقاً!", show_alert=False); return

    entry["voters"].append(uid)
    entry[vtype] += 1
    _save_votes()

    emoji = "👍" if vtype == "up" else "👎"
    bot.answer_callback_query(call.id,
        f"{emoji} تم تسجيل صوتك! ({entry['up']}👍 {entry['down']}👎)",
        show_alert=False)


# ─────────────────────────────────────────────────────────────────────────
# §6  PREMIUM COMMANDS — أوامر المستخدم المميز
# ─────────────────────────────────────────────────────────────────────────

# ── /deepdive — تحليل عميق شامل ──────────────────────────────────────────
