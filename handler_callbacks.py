# -*- coding: utf-8 -*-
"""
  handler_callbacks.py — callbacks العامة + antispam + بقية الأوامر

  يُصدِّر كل الـ callbacks العامة والأوامر المتبقية.
  """

import sys as _sys_legacy
import os
# ─── استيراد كل المتغيرات العالمية من bot_legacy ───
from bot_legacy import *
import state as gl  # noqa: F401,F403

def _cb_antispam(uid) -> bool:
    now = time.time()
    uid_s = str(uid)
    with _CB_ANTISPAM_LOCK:
        last = _CB_ANTISPAM.get(uid_s, 0.0)
        if now - last < _CB_GLOBAL_COOLDOWN:
            return True   # محجوب
        _CB_ANTISPAM[uid_s] = now
        # تنظيف المدخلات القديمة (> 60 ثانية) لمنع تضخم الذاكرة
        if len(_CB_ANTISPAM) > 5000:
            stale = [k for k, t in list(_CB_ANTISPAM.items()) if now - t > 60]
            for k in stale:
                _CB_ANTISPAM.pop(k, None)
    return False


# ─── Bot Health Monitoring (اقتراح للأدمن) ───────────────────────────────────
_bot_start_ts: float = time.time()    # وقت إقلاع البوت
_broadcast_call_log: list = []        # [(ts, count_sent), ...]  آخر 50 دورة
_broadcast_log_lock = threading.Lock()
_last_broadcast_alert_ts: float = 0.0

def _handle_cb_antispam(call):
    try:
        uid = str(call.from_user.id)
        lang = users.get(uid, {}).get("lang", "العربية 🇮🇶")
        bot.answer_callback_query(call.id, _ui("cb_antispam_text", lang), show_alert=False)
    except Exception as _exc:
        _log_exc(_exc)

@bot.callback_query_handler(func=lambda c: c.data.startswith("hcmd_"))
def cmd_iraq_map(m):
    uid  = m.from_user.id
    if uid in banned: return
    lang = users.get(str(uid), {}).get("lang", "العربية 🇮🇶")
    wait = bot.send_message(uid,
        _NEW_FEAT_I18N["map_loading"].get(lang, _NEW_FEAT_I18N["map_loading"]["العربية 🇮🇶"]))
    try:
        map_text = _generate_iraq_map_text(lang)
        try: bot.delete_message(uid, wait.message_id)
        except Exception as _exc:
            _log_exc(_exc)
    except Exception:
        try: bot.delete_message(uid, wait.message_id)
        except Exception as _exc:
            _log_exc(_exc)
        map_text = _NEW_FEAT_I18N["map_error"].get(lang, _NEW_FEAT_I18N["map_error"]["العربية 🇮🇶"])
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton(
        _NEW_FEAT_I18N["map_refresh_btn"].get(lang, "🔄"),
        callback_data=f"map_refresh_{uid}"))
    bot.send_message(uid, map_text, parse_mode="Markdown", reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data.startswith("map_refresh_"))
def handle_map_refresh(call):
    uid  = call.from_user.id
    lang = users.get(str(uid), {}).get("lang", "العربية 🇮🇶")
    bot.answer_callback_query(call.id,
        _NEW_FEAT_I18N["map_refresh_toast"].get(lang, "🔄..."))
    try:
        map_text = _generate_iraq_map_text(lang)
        markup   = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton(
            _NEW_FEAT_I18N["map_refresh_btn"].get(lang, "🔄"),
            callback_data=f"map_refresh_{uid}"))
        bot.edit_message_text(map_text, uid, call.message.message_id,
                              parse_mode="Markdown", reply_markup=markup)
    except Exception as _exc:
        _log_exc(_exc)



  # ======== Inline Mode — البحث في الأخبار من أي محادثة ========
@bot.inline_handler(func=lambda q: True)
def handle_inline_query(query):
    uid = query.from_user.id
    q_text = query.query.strip()
    user = users.get(str(uid), {})
    lang = user.get("lang", "العربية 🇮🇶")
    results = []
    try:
        # جلب أخبار من RSS للغة المستخدم
        feeds = RSS.get(lang, RSS.get("العربية 🇮🇶", []))
        candidates = []
        for feed_url in feeds[:4]:
            try:
                parsed = feedparser.parse(feed_url)
                for entry in parsed.entries[:10]:
                    title = getattr(entry, 'title', '').strip()
                    link = getattr(entry, 'link', '')
                    if not title or not link:
                        continue
                    if q_text and q_text.lower() not in title.lower():
                        continue
                    candidates.append((title, link))
                    if len(candidates) >= 20:
                        break
            except Exception as _exc:
                _log_exc(_exc)
            if len(candidates) >= 20:
                break

        # إذا ما في بحث، خذ أحدث الأخبار
        if not q_text and not candidates:
            for feed_url in feeds[:2]:
                try:
                    parsed = feedparser.parse(feed_url)
                    for entry in parsed.entries[:8]:
                        title = getattr(entry, 'title', '').strip()
                        link = getattr(entry, 'link', '')
                        if title and link:
                            candidates.append((title, link))
                except Exception as _exc:
                    _log_exc(_exc)

        for i, (title, link) in enumerate(candidates[:15]):
            results.append(
                types.InlineQueryResultArticle(
                    id=str(i),
                    title=title[:100],
                    input_message_content=types.InputTextMessageContent(
                        f"📰 {title}\n\n🔗 {link}"
                    ),
                    description=link[:80],
                    url=link,
                    hide_url=True,
                )
            )
    except Exception as _exc:
        _log_exc(_exc)

    if not results:
        results.append(
            types.InlineQueryResultArticle(
                id="0",
                title="🔍 لا توجد نتائج" if lang == "العربية 🇮🇶" else "🔍 No results found",
                input_message_content=types.InputTextMessageContent("لا توجد أخبار متاحة الآن."),
                description="حاول لاحقاً" if lang == "العربية 🇮🇶" else "Try again later",
            )
        )
    try:
        bot.answer_inline_query(query.id, results, cache_time=60)
    except Exception as _exc:
        _log_exc(_exc)

@bot.callback_query_handler(func=lambda c: c.data.startswith("rate_bot_") or c.data.startswith("rate_news_"))
def _forward_to_admin(m):
    uid = m.from_user.id
    user = users.get(str(uid), {})
    name = getattr(m.from_user, "first_name", "مجهول")
    utype = is_premium(uid)
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    entry = {
        "uid": uid,
        "name": name,
        "text": m.text or "",
        "premium": utype,
        "time": ts,
        "lang": user.get("lang", "-"),
        "country": user.get("country", "-"),
    }
    inbox_messages.append(entry)
    save_inbox()
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton(f"↩️ رد على {name}", callback_data=f"admin_reply_{uid}"))
    utype_label = "⭐ مميز" if utype else "👤 عادي"
    try:
        bot.send_message(ADMIN_ID,
            f"💬 *رسالة جديدة من مستخدم*\n\n"
            f"👤 الاسم: {name}\n"
            f"🆔 `{uid}` | {utype_label}\n"
            f"🌍 {user.get('country', '-')} | 🗣 {user.get('lang', '-')}\n"
            f"🕐 {ts}\n\n"
            f"📩 {m.text}",
            parse_mode="Markdown", reply_markup=markup)
    except Exception as _exc:
        _log_exc(_exc)

def handle_location_choice(call):
    uid  = call.from_user.id
    user = users.get(str(uid), {})
    lang = user.get("lang", "English 🇬🇧")
    country   = user.get("country", "")
    lang_data = countries.get(lang, {})
    provinces = lang_data.get(country, [])
    try:
        bot.answer_callback_query(call.id)
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except Exception as _exc:
        _log_exc(_exc)
    if call.data == "loc_choose_prov":
        if provinces:
            markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
            for prov in provinces:
                markup.add(prov)
            bot.send_message(uid, st(lang, "choose_province"), reply_markup=markup)
        else:
            capital = COUNTRY_CAPITALS.get(country, "")
            users[str(uid)]["province"] = capital if capital else country
            users[str(uid)].pop("awaiting_location", None)
            _db_save_all_users(users)
            update_stats("new_user", country=country, lang=lang)
            bot.send_message(uid, st(lang, "settings_saved"))
            send_main_menu(uid)
    else:
        users[str(uid)]["awaiting_location"] = True
        _db_save_all_users(users)
        bot.send_message(uid, st(lang, "location_share_prompt"),
                         reply_markup=_make_location_keyboard(lang))

# ======== استقبال الموقع الجغرافي GPS ========
@bot.message_handler(content_types=['location'])
def handle_location_message(message):
    uid  = message.from_user.id
    if uid in banned:
        return
    user = users.get(str(uid), {})
    if not user.get("awaiting_location"):
        return
    lang    = user.get("lang", "English 🇬🇧")
    lang_code = LANG_CODES.get(lang, "en")
    lat = message.location.latitude
    lon = message.location.longitude
    users[str(uid)]["location_lat"] = lat
    users[str(uid)]["location_lon"] = lon
    # Reverse geocoding باستخدام OWM Geocoding API
    city_name = ""
    try:
        geo_url = (
            f"https://api.openweathermap.org/geo/1.0/reverse"
            f"?lat={lat}&lon={lon}&limit=1&appid={WEATHER_KEY}"
        )
        geo_data = requests.get(geo_url, timeout=8).json()
        if isinstance(geo_data, list) and geo_data:
            local_names = geo_data[0].get("local_names", {})
            city_name = (local_names.get(lang_code)
                         or local_names.get("ar")
                         or geo_data[0].get("name", ""))
    except Exception as _exc:
        _log_exc(_exc)
    if not city_name:
        city_name = user.get("country", "")
    users[str(uid)]["province"] = city_name
    users[str(uid)].pop("awaiting_location", None)
    _db_save_all_users(users)
    country = user.get("country", city_name)
    update_stats("new_user", country=country, lang=lang)
    # إرسال تأكيد + القائمة الرئيسية
    bot.send_message(uid, st(lang, "location_saved"),
                     reply_markup=types.ReplyKeyboardRemove())
    send_main_menu(uid)

# ======== التعامل مع الرسائل ========
@bot.message_handler(func=lambda m: m.text is not None and not m.text.startswith('/'))
def handle_selection(m):
    uid = m.from_user.id
    text = m.text
    _update_last_seen(uid, message=m)
    if uid in banned:
        return
    if bot_paused and not is_admin(uid):
        _sel_lang = users.get(str(uid), {}).get("lang", "العربية 🇮🇶")
        bot.send_message(uid, _ui("bot_paused", _sel_lang) if not pause_message or pause_message == "🔧 البوت متوقف مؤقتاً، سيعود قريباً." else pause_message)
        return
    user = users.get(str(uid))
    if not user:
        bot.send_message(uid, _ui("start_first", users.get(str(uid), {}).get("lang", "العربية 🇮🇶")))
        return
    # FIX: إذا كان المستخدم قد حظر البوت سابقاً وعاد — أعد تفعيل البث
    if not user.get("notifications", True):
        user["notifications"] = True
        _logger.info("🔔 أُعيد تفعيل notifications للمستخدم %s بعد رسالة جديدة", uid)
    lang = user.get("lang", "English 🇬🇧")
    btn = BUTTONS.get(lang, BUTTONS["English 🇬🇧"])

    if user_states.get(uid) == "searching":
        user_states.pop(uid, None)
        search_news(uid, text)
        return

    if user_states.get(uid) == "converting_currency":
        user_states.pop(uid, None)
        parts = text.strip().split()
        if len(parts) >= 2:
            try:
                amount = float(parts[0].replace(",", ""))
                currency = parts[1].upper()
                convert_currency_msg(uid, amount, currency)
            except ValueError:
                bot.send_message(uid, st(lang, "convert_format_error"), parse_mode="Markdown")
        else:
            bot.send_message(uid, st(lang, "convert_send_both"), parse_mode="Markdown")
        return

    if user_states.get(uid) == "tracking_asset":
        user_states.pop(uid, None)
        symbol = text.strip().upper()
        if not symbol or len(symbol) > 15:
            bot.send_message(uid, "⚠️ رمز غير صحيح. أرسل مثال: AAPL أو BTC أو EUR")
            return
        existing = tracked_assets.get(str(uid), {}).get("assets", [])
        if symbol in existing:
            bot.send_message(uid, f"📌 *{symbol}* مضافة مسبقاً في قائمة التتبع.", parse_mode="Markdown")
        elif len(existing) >= 10:
            bot.send_message(uid, "⚠️ الحد الأقصى 10 أصول. أرسل /removetrack {رمز} لحذف واحدة.")
        else:
            price = fetch_asset_price(symbol)
            if price is None:
                bot.send_message(uid, f"⚠️ لم أتمكن من العثور على *{symbol}*. تأكد من الرمز وأعد المحاولة.", parse_mode="Markdown")
                return
            if str(uid) not in tracked_assets:
                tracked_assets[str(uid)] = {"assets": [], "last_prices": {}}
            tracked_assets[str(uid)]["assets"].append(symbol)
            tracked_assets[str(uid)]["last_prices"][symbol] = price
            save_tracked_assets()
            bot.send_message(uid,
                f"✅ تمت إضافة *{symbol}* للتتبع!\n"
                f"💰 السعر الحالي: `{price}`\n\n"
                f"🔔 ستصلك تنبيه عند تغير السعر بنسبة ±2%",
                parse_mode="Markdown"
            )
        return

    if user_states.get(uid) == "adding_keyword":
        user_states.pop(uid, None)
        if text.strip().startswith("حذف") or text.strip().startswith("delete"):
            user_keywords[str(uid)] = []
            save_keywords()
            bot.send_message(uid, "✅ تم حذف جميع كلماتك المفتاحية.")
        else:
            new_kws = [k.strip() for k in text.replace("،", ",").split(",") if k.strip()]
            existing = user_keywords.get(str(uid), [])
            for kw in new_kws:
                if kw not in existing:
                    existing.append(kw)
            user_keywords[str(uid)] = existing[:20]
            save_keywords()
            bot.send_message(uid, st(lang, "keywords_saved", n=len(new_kws)))
        return

    if "province" in user:
        update_stats("button", button=text)
        if text == btn["settings"]:
            users[str(uid)] = {"name": user["name"], "sent_news": {}}
            _db_save_all_users(users)
            welcome_user(uid)
        elif text == btn["weather"]:
            _track_feature(uid, "weather"); send_detailed_weather(uid)
        elif text == btn.get("forecast"):
            _track_feature(uid, "forecast"); send_3day_forecast(uid)
        elif text == btn["news"]:
            _track_feature(uid, "news"); send_hourly_news(uid)
        elif text == btn["all_news"]:
            _track_feature(uid, "all_news"); send_all_news(uid)
        elif text == btn["mena_politics"]:
            _track_feature(uid, "mena_politics"); send_mena_politics(uid)
        elif text == btn.get("trending"):
            _track_feature(uid, "trending"); send_trending_news(uid)
        elif text == btn.get("daily_summary"):
            _track_feature(uid, "daily_summary"); send_daily_summary(uid)
        elif text == btn.get("voice_news"):
            _track_feature(uid, "voice_news"); _send_voice_news_menu(uid)
        elif text == btn.get("audio_podcast") or text == "🎧 بودكاست يومي":
            _track_feature(uid, "audio_podcast"); _handle_podcast_btn(uid)
        elif text == btn.get("news_cats"):
            _track_feature(uid, "news_cats"); send_interest_menu(uid)
        elif text == btn.get("news_select"):
            _track_feature(uid, "news_select"); _send_news_cats_menu(uid)
        elif text == btn["currency"]:
            _track_feature(uid, "currency"); send_currency(uid)
        elif text == btn.get("crypto"):
            _track_feature(uid, "crypto"); send_crypto_prices(uid)
        elif text == btn.get("prayer"):
            _track_feature(uid, "prayer"); send_prayer_times(uid)
        elif text == btn["search"]:
            _track_feature(uid, "search")
            user_states[uid] = "searching"
            bot.send_message(uid, t(lang, "search_prompt"))
        elif text == btn.get("deepsearch", "🧠 بحث عميق بالذكاء الاصطناعي"):
            # فحص feature flag
            if not _FF.get("search", True):
                bot.send_message(uid, _ui("feature_disabled", lang))
            # فحص بحث جارٍ
            elif _deepsearch_active.get(str(uid)):
                _busy = {"العربية 🇮🇶": "⏳ بحث سابق لا يزال جارياً، انتظر حتى يكتمل", "English 🇬🇧": "⏳ Previous search still running, please wait."}
                bot.send_message(uid, _busy.get(lang, _busy["English 🇬🇧"]))
            # فحص كولداون
            elif _is_rate_limited(uid, "deepsearch") and not is_admin(uid):
                bot.send_message(uid, _ui("rate_limited", lang))
            # فحص الحصة اليومية
            elif not _check_daily_ai_limit(uid, "deepsearch")[0]:
                _used, _lim = _check_daily_ai_limit(uid, "deepsearch")[1], _check_daily_ai_limit(uid, "deepsearch")[2]
                _qmsg = {"العربية 🇮🇶": f"📊 استنفدت حصتك اليومية ({_used}/{_lim}). يتجدد الرصيد غداً.\n{'⭐ المميزون: 8 بحث/يوم.' if not is_premium(uid) else ''}", "English 🇬🇧": f"📊 Daily limit reached ({_used}/{_lim}). Resets tomorrow."}
                bot.send_message(uid, _qmsg.get(lang, _qmsg["English 🇬🇧"]), parse_mode="Markdown")
            else:
                _labels = {
                    "العربية 🇮🇶": "✏️ أرسل الموضوع الذي تريد البحث عنه الآن:\n_(مثال: الأزمة السياسية في العراق)_",
                    "English 🇬🇧": "✏️ Send the topic you want to deep search now:\n_(e.g., Iraq political crisis)_",
                    "Русский 🇷🇺": "✏️ Отправьте тему для глубокого поиска:",
                    "فارسی 🇮🇷": "✏️ موضوع مورد نظر را ارسال کنید:",
                    "हिन्दी 🇮🇳": "✏️ अभी खोज का विषय भेजें:",
                    "Português 🇧🇷": "✏️ Envie o tópico que deseja pesquisar:",
                    "Türkçe 🇹🇷": "✏️ Aramak istediğiniz konuyu şimdi gönderin:",
                    "اردو 🇵🇰": "✏️ ابھی موضوع بھیجیں جو آپ تلاش کرنا چاہتے ہیں:",
                    "Deutsch 🇩🇪": "✏️ Senden Sie jetzt das Thema, das Sie suchen möchten:",
                    "Українська 🇺🇦": "✏️ Надішліть тему для глибокого пошуку зараз:",
                    "Italiano 🇮🇹": "✏️ Invia ora l'argomento che vuoi cercare:",
                    "Español 🇲🇽": "✏️ Envía el tema que deseas buscar ahora:",
                }
                prompt_txt = _labels.get(lang, "✏️ Send the topic you want to deep search now:")
                sent = bot.send_message(uid, prompt_txt, parse_mode="Markdown")
                def _wait_for_topic_kbd(msg, _uid=uid, _lang=lang):
                    topic = (msg.text or "").strip()
                    if not topic:
                        return
                    if _deepsearch_active.get(str(_uid)):
                        _busy_msgs = {
                            "العربية 🇮🇶": "⏳ بحث سابق لا يزال جارياً، انتظر حتى يكتمل",
                            "English 🇬🇧": "⏳ A previous search is still running, please wait",
                            "Русский 🇷🇺": "⏳ Предыдущий поиск ещё выполняется, подождите",
                            "فارسی 🇮🇷": "⏳ جستجوی قبلی هنوز در حال اجراست، لطفاً صبر کنید",
                            "हिन्दी 🇮🇳": "⏳ पिछली खोज अभी भी चल रही है, कृपया प्रतीक्षा करें",
                            "Português 🇧🇷": "⏳ Uma pesquisa anterior ainda está em execução, aguarde",
                            "Türkçe 🇹🇷": "⏳ Önceki arama hâlâ devam ediyor, lütfen bekleyin",
                            "اردو 🇵🇰": "⏳ پچھلی تلاش ابھی جاری ہے، براہ کرم انتظار کریں",
                            "Deutsch 🇩🇪": "⏳ Eine vorherige Suche läuft noch, bitte warten",
                            "Українська 🇺🇦": "⏳ Попередній пошук ще виконується, зачекайте",
                            "Italiano 🇮🇹": "⏳ Una ricerca precedente è ancora in corso, attendere",
                            "Español 🇲🇽": "⏳ Una búsqueda anterior sigue en curso, espere",
                        }
                        bot.send_message(_uid, _busy_msgs.get(_lang, _busy_msgs["English 🇬🇧"]))
                        return
                    _deepsearch_active[str(_uid)] = True
                    _start_msgs = {
                        "العربية 🇮🇶": (
                            f"🔍 *DeepSearch بدأ*\n\n📌 الموضوع: *{topic}*\n\n"
                            f"⏳ جاري فحص:\n• مصادر RSS العربية والدولية\n"
                            f"• مواقع إخبارية بالسكرابنق\n• المصادر الرسمية والحكومية\n"
                            f"• قاعدة بيانات NewsAPI العالمية\n• تحليل عميق بالذكاء الاصطناعي\n\n"
                            f"_قد يستغرق 5-15 دقيقة..._"
                        ),
                        "English 🇬🇧": (
                            f"🔍 *DeepSearch Started*\n\n📌 Topic: *{topic}*\n\n"
                            f"⏳ Scanning:\n• Arabic & international RSS feeds\n"
                            f"• News sites via scraping\n• Official & government sources\n"
                            f"• NewsAPI global database\n• Deep AI analysis\n\n"
                            f"_May take 5-15 minutes..._"
                        ),
                    }
                    progress_msg = bot.send_message(
                        _uid,
                        _start_msgs.get(_lang, _start_msgs["English 🇬🇧"]),
                        parse_mode="Markdown"
                    )
                    import threading as _th
                    _th.Thread(
                        target=_deepsearch_worker,
                        args=(_uid, topic, progress_msg.message_id, _uid),
                        daemon=True
                    ).start()
                bot.register_next_step_handler(sent, _wait_for_topic_kbd)
        elif text == btn.get("referral"):
            _track_feature(uid, "referral"); send_referral_stats(uid)
        elif text == btn.get("top_referrers"):
            _track_feature(uid, "top_referrers"); send_top_referrers(uid)
        elif text == btn.get("sports"):
            _track_feature(uid, "sports"); send_sports_news(uid)
        elif text == btn.get("convert"):
            _track_feature(uid, "currency_convert")
            user_states[uid] = "converting_currency"
            bot.send_message(uid, st(lang, "convert_prompt"), parse_mode="Markdown")
        elif text == btn.get("my_stats"):
            _track_feature(uid, "my_stats"); send_my_stats(uid)
        elif text == btn.get("share_bot"):
            _track_feature(uid, "share_bot"); send_share_bot(uid)
        elif text == btn.get("public_stats"):
            _track_feature(uid, "public_stats"); send_public_stats(uid)
        elif text == btn.get("dollar_parallel"):
            _track_feature(uid, "dollar_parallel"); send_dollar_parallel(uid)
        elif text == btn.get("weekly_summary"):
            _track_feature(uid, "weekly_summary"); send_weekly_summary_text(uid)
        elif text == btn.get("track_asset"):
            _track_feature(uid, "track_asset"); start_track_asset(uid)
        elif text in (btn["notif_on"], btn["notif_off"]):
            current = users[str(uid)].get("notifications", True)
            if not current:
                # كانت مغلقة — أعد التفعيل فوراً
                users[str(uid)]["notifications"] = True
                users[str(uid)].pop("news_paused_until", None)
                _db_save_all_users(users)
                bot.send_message(uid, st(lang, "notif_enabled"))
                send_main_menu(uid)
            else:
                # مفعّلة — اعرض خيارات الإيقاف
                pause_markup = types.InlineKeyboardMarkup(row_width=2)
                pause_markup.add(
                    types.InlineKeyboardButton("⏸ ساعة واحدة", callback_data="pause_news_1h"),
                    types.InlineKeyboardButton("⏸ 6 ساعات", callback_data="pause_news_6h"),
                    types.InlineKeyboardButton("⏸ يوم كامل", callback_data="pause_news_24h"),
                    types.InlineKeyboardButton("❌ إيقاف نهائي", callback_data="pause_news_off"),
                    types.InlineKeyboardButton("↩️ إلغاء", callback_data="pause_news_cancel"),
                )
                bot.send_message(uid, "🔕 *كم تريد إيقاف الأخبار؟*", parse_mode="Markdown", reply_markup=pause_markup)
        elif text == btn.get("premium", "⭐ Premium"):
            lang = users.get(str(uid), {}).get('lang', 'العربية 🇮🇶')
            free_msg = {
                "العربية 🇮🇶":   "✅ *جميع المميزات مفتوحة للجميع مجاناً!*\n\nاستخدم /help لرؤية كل الميزات المتاحة.",
                "English 🇬🇧":   "✅ *All features are free for everyone!*\n\nUse /help to see all available features.",
                "Русский 🇷🇺":   "✅ *Все функции бесплатны для всех!*\n\nИспользуйте /help для просмотра доступных функций.",
                "فارسی 🇮🇷":    "✅ *همه امکانات برای همه رایگان است!*\n\nاز /help برای مشاهده امکانات استفاده کنید.",
                "हिन्दी 🇮🇳":   "✅ *सभी सुविधाएं सभी के लिए मुफ़्त हैं!*\n\n/help का उपयोग करें।",
                "Português 🇧🇷": "✅ *Todos os recursos são gratuitos para todos!*\n\nUse /help para ver todos os recursos.",
                "Türkçe 🇹🇷":   "✅ *Tüm özellikler herkese ücretsiz!*\n\nTüm özellikleri görmek için /help kullanın.",
                "اردو 🇵🇰":     "✅ *تمام خصوصیات سب کے لیے مفت ہیں!*\n\nتمام خصوصیات دیکھنے کے لیے /help استعمال کریں۔",
                "Deutsch 🇩🇪":  "✅ *Alle Funktionen sind für alle kostenlos!*\n\nVerwenden Sie /help, um alle Funktionen zu sehen.",
                "Українська 🇺🇦": "✅ *Усі функції безкоштовні для всіх!*\n\nВикористовуйте /help для перегляду функцій.",
                "Italiano 🇮🇹": "✅ *Tutte le funzionalità sono gratuite per tutti!*\n\nUsa /help per vedere tutte le funzionalità.",
                "Español 🇲🇽":  "✅ *¡Todas las funciones son gratuitas para todos!*\n\nUsa /help para ver todas las funciones disponibles.",
            }
            bot.send_message(uid, free_msg.get(lang, free_msg["English 🇬🇧"]), parse_mode="Markdown")

        # ══════════════════════════════════════════════════════════
        # ⚡ وضع 30 ثانية — أخبار سريعة دفعة واحدة
        # ══════════════════════════════════════════════════════════
        elif text == btn.get("mode30"):
            _handle_mode30(uid)

        # ══════════════════════════════════════════════════════════
        # 😐 بدون تحليل — خبر مباشر فقط
        # ══════════════════════════════════════════════════════════
        elif text == btn.get("noanalysis"):
            _handle_noanalysis(uid)

        # ══════════════════════════════════════════════════════════
        # 💡 زبدة الموضوع — جملة واحدة
        # ══════════════════════════════════════════════════════════
        elif text == btn.get("zbda"):
            _handle_zbda(uid)

        # ══════════════════════════════════════════════════════════
        # 🔮 قبل ما يصير — توقع بسيط
        # ══════════════════════════════════════════════════════════
        elif text == btn.get("before_happen"):
            _handle_before_happen(uid)

        # ══════════════════════════════════════════════════════════
        # 🖼 خبر بصورة — كارت بصري
        # ══════════════════════════════════════════════════════════
        elif text == btn.get("imgcard"):
            _handle_imgcard(uid)

        # ══════════════════════════════════════════════════════════
        # 🗺 الفئات السريعة
        # ══════════════════════════════════════════════════════════
        elif text == btn.get("cat_world"):
            _handle_category_news(uid, "world")
        elif text == btn.get("cat_arab"):
            _handle_category_news(uid, "arab")
        elif text == btn.get("cat_econ"):
            _handle_category_news(uid, "economy")
        elif text == btn.get("cat_sport"):
            _handle_category_news(uid, "sports")

        else:
            _forward_to_admin(m)
            bot.send_message(uid, "✅ تم إرسال رسالتك للإدارة، سيتم الرد عليك قريباً.")
        return

    if "lang" not in user:
        for key, val in languages.items():
            if text == val:
                if val not in countries:
                    bot.send_message(uid, "⚠️ هذه اللغة غير متوفرة بالكامل. اختر لغة أخرى.")
                    return
                users[str(uid)]["lang"] = val
                user_feeds = RSS.get(val, [])
                try:
                    news_count = 0
                    for feed_url in user_feeds[:3]:
                        try:
                            feed_data = _parse_feed(feed_url)
                            if feed_data is None:
                                feed_data = feedparser.parse(feed_url)
                            if not feed_data:
                                continue
                            for item in feed_data.entries[:2]:
                                title = getattr(item, 'title', '')
                                link = getattr(item, 'link', '')
                                if title and link:
                                    item_sum = getattr(item, 'summary', '') or getattr(item, 'description', '')
                                    markup_news = make_news_share_markup(link, title, val, item_sum)
                                    src_name = get_source_name_from_url(feed_url)
                                    pub_time_str = _format_pub_time(_pub_dt_from_item(item), lang=val)
                                    bot.send_message(uid,
                                        format_news_item(t(val, "label_news"), title, val, src_name, pub_time_str, summary=item_sum),
                                        parse_mode="Markdown",
                                        reply_markup=markup_news
                                    )
                                    news_count += 1
                                    if news_count >= 3:
                                        break
                        except Exception as _exc:
                            _log_exc(_exc)
                        if news_count >= 3:
                            break
                except Exception as _exc:
                    _log_exc(_exc)
                users[str(uid)]["sent_news"] = prefill_sent_news(user_feeds)  # returns dict
                _db_save_all_users(users)
                markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
                for country in countries[val]:
                    markup.add(country)
                country_msg_text = COUNTRY_SELECT_MSG.get(val, COUNTRY_SELECT_MSG.get("English 🇬🇧", "Please select your country."))
                sent_country = bot.send_message(uid, country_msg_text, reply_markup=markup)
                try:
                    bot.pin_chat_message(uid, sent_country.message_id, disable_notification=True)
                except Exception as _exc:
                    _log_exc(_exc)
                send_usage_hint(uid, val)
                return
        bot.send_message(uid, "👇 Please choose a language from the list.")
        return

    if "country" not in user:
        lang = users[str(uid)].get("lang", lang)
        if lang in countries and text in countries[lang]:
            users[str(uid)]["country"] = text
            _db_save_all_users(users)
            # عرض رسالة الإقناع بإرسال الموقع
            provinces = countries[lang][text]
            _send_location_choice(uid, lang, text, provinces)
        else:
            bot.send_message(uid, st(lang, "choose_country_from_list"))
        return

    # إذا كان البوت ينتظر إرسال الموقع، نتجاهل النصوص
    if user.get("awaiting_location"):
        lang = users[str(uid)].get("lang", lang)
        country = user.get("country", "")
        if country and lang in countries and country in countries[lang]:
            valid_provinces = countries[lang][country]
            if text in valid_provinces:
                users[str(uid)]["province"] = text
                users[str(uid)].pop("awaiting_location", None)
                _db_save_all_users(users)
                update_stats("new_user", country=country, lang=lang)
                bot.send_message(uid, st(lang, "settings_saved"),
                                 reply_markup=types.ReplyKeyboardRemove())
                send_main_menu(uid)
                return
        bot.send_message(uid, st(lang, "location_share_prompt"),
                         reply_markup=_make_location_keyboard(lang))
        return

    if "province" not in user:
        lang = users[str(uid)].get("lang", lang)
        country = user["country"]
        if lang in countries and country in countries[lang]:
            valid_provinces = countries[lang][country]
            if text in valid_provinces:
                users[str(uid)]["province"] = text
                users[str(uid)].pop("awaiting_location", None)
                _db_save_all_users(users)
                update_stats("new_user", country=country, lang=lang)
                bot.send_message(uid, st(lang, "settings_saved"))
                send_main_menu(uid)
            else:
                bot.send_message(uid, st(lang, "choose_province_from_list"))

# ======== اختيار طريقة تحديد الموقع (محافظة أو GPS) ========
def _handle_user_document(message):
    """يعالج الملفات التي يرسلها المستخدمون العاديون ويلخّصها بـ AI."""
    uid     = message.from_user.id
    uid_str = str(uid)
    lang    = users.get(uid_str, {}).get("lang", "العربية 🇮🇶")

    if uid in banned:
        return

    doc = message.document
    if not doc or not doc.file_name:
        return

    fname   = doc.file_name.lower()
    allowed = (".txt", ".csv", ".json", ".log", ".md", ".pdf")
    if not fname.endswith(allowed):
        types_ar = "TXT, CSV, JSON, PDF, MD, LOG"
        bot.send_message(
            message.chat.id,
            "📎 يمكنني قراءة الملفات من النوع:\n`" + types_ar + "`\n\nأرسل ملفاً من أحد هذه الأنواع وسأحلله لك.",
            parse_mode="Markdown"
        )
        return

    if doc.file_size and doc.file_size > 3 * 1024 * 1024:
        bot.send_message(message.chat.id, "❌ الملف كبير جداً (الحد الأقصى 3 MB).")
        return

    _rl_key = "doc_" + str(uid)
    _now_ts = time.time()
    _cd_map = _user_ai_cooldown.get(uid_str, {})
    if _cd_map.get(_rl_key, 0) and _now_ts - _cd_map[_rl_key] < 120:
        bot.send_message(message.chat.id, "⏳ انتظر دقيقتين بين كل ملف.")
        return

    wait_msg = bot.send_message(message.chat.id, "📂 جاري قراءة الملف...")
    try:
        file_info  = bot.get_file(doc.file_id)
        downloaded = bot.download_file(file_info.file_path)

        text = ""
        if fname.endswith(".pdf"):
            try:
                import re as _re2
                raw   = downloaded.decode("latin-1", errors="ignore")
                parts = _re2.findall(r'BT(.*?)ET', raw, _re2.DOTALL)
                tokens = []
                for part in parts:
                    for m in _re2.findall(r'\((.*?)\)', part):
                        tokens.append(m)
                text = " ".join(tokens)
                text = text.replace("\\n", "\n").replace("\\t", " ")
                if len(text.strip()) < 30:
                    text = "[PDF: تعذّر استخراج نص كافٍ. جرّب إرسال الملف بصيغة TXT.]"
            except Exception:
                text = "[PDF: تعذّر استخراج النص. جرّب إرسال الملف بصيغة TXT.]"
        else:
            try:
                text = downloaded.decode("utf-8", errors="replace")
            except Exception:
                text = downloaded.decode("latin-1", errors="replace")

        if not text.strip():
            bot.edit_message_text("❌ الملف فارغ أو لا يحتوي على نص.",
                                  message.chat.id, wait_msg.message_id)
            return

        text_for_ai = text[:6000]
        if len(text) > 6000:
            text_for_ai += "\n\n[... تم اقتصار الملف على 6000 حرف ...]"

        bot.edit_message_text("🤖 جاري تحليل المحتوى بـ AI...", message.chat.id, wait_msg.message_id)

        caption = message.caption or ""
        if caption.strip():
            text_for_ai = text_for_ai + "\n\nسؤال المستخدم: " + caption

        summary = _ai_generate_summary(
            text_for_ai,
            title="ملف: " + doc.file_name + (" — " + caption if caption.strip() else ""),
            lang=lang
        )

        reply = "📄 *" + escape_md(doc.file_name) + "*\n\n" + summary
        try:
            bot.edit_message_text(reply[:4096], message.chat.id, wait_msg.message_id,
                                  parse_mode="Markdown", disable_web_page_preview=True)
        except Exception:
            bot.send_message(message.chat.id, reply[:4096],
                             parse_mode="Markdown", disable_web_page_preview=True)

        if uid_str not in _user_ai_cooldown:
            _user_ai_cooldown[uid_str] = {}
        _user_ai_cooldown[uid_str][_rl_key] = _now_ts

    except Exception as exc:
        _log_exc(exc)
        try:
            bot.edit_message_text("❌ حدث خطأ أثناء معالجة الملف: " + str(exc)[:150],
                                  message.chat.id, wait_msg.message_id)
        except Exception:
            pass


# ======== استعادة البيانات من ملف .db أو .zip ========
@bot.message_handler(content_types=['document'])
def handle_document(message):
    global blacklist_words, news_settings, inbox_messages, welcome_override, broadcast_settings
    global extra_admins, channels_groups, user_keywords, tracked_assets, read_stats
    global ratings_data, stats, _db_conn, users
    import io, zipfile, shutil
    if not is_admin(message.from_user.id):
        # المستخدمون العاديون: معالجة الملف بـ AI
        _handle_user_document(message)
        return
    doc = message.document
    if not doc.file_name:
        return

    file_info = bot.get_file(doc.file_id)
    downloaded = bot.download_file(file_info.file_path)

    # ── استعادة الإعدادات من ملف ZIP (آمن — JSON فقط، بدون لمس البوت أو DB) ──
    if doc.file_name.endswith(".zip"):
        try:
            restored = []
            zip_buffer = io.BytesIO(downloaded)
            with zipfile.ZipFile(zip_buffer, "r") as zf:
                for name in zf.namelist():
                    # تجاهل bot.py وملفات .db وملفات التقرير — JSON فقط
                    if not name.endswith(".json") or name.startswith("backup_report"):
                        continue
                    data = zf.read(name)
                    with open(name, "wb") as f:
                        f.write(data)
                    # إعادة تحميل كل إعداد في الذاكرة فوراً
                    bn = name
                    if bn == os.path.basename(BLACKLIST_FILE):
                        blacklist_words = load_json(BLACKLIST_FILE, [])
                    elif bn == os.path.basename(NEWS_SETTINGS_FILE):
                        news_settings = load_json(NEWS_SETTINGS_FILE, {})
                    elif bn == os.path.basename(INBOX_FILE):
                        inbox_messages = load_json(INBOX_FILE, [])
                    elif bn == os.path.basename(WELCOME_FILE):
                        _wd = load_json(WELCOME_FILE, {"override": None})
                        welcome_override = _wd.get("override", None)
                    elif bn == os.path.basename(BROADCAST_SETTINGS_FILE):
                        broadcast_settings = load_json(BROADCAST_SETTINGS_FILE, {})
                    elif bn == os.path.basename(ADMINS_FILE):
                        extra_admins = [int(a) for a in load_json(ADMINS_FILE, [])]
                    elif bn == os.path.basename(CHANNELS_FILE):
                        channels_groups = load_json(CHANNELS_FILE, [])
                        _db_save_all_channels(channels_groups)  # sync to SQLite after restore
                    elif bn == os.path.basename(KEYWORDS_FILE):
                        user_keywords = load_json(KEYWORDS_FILE, {})
                    elif bn == os.path.basename(TRACK_FILE):
                        tracked_assets = load_json(TRACK_FILE, {})
                    elif bn == os.path.basename(READ_STATS_FILE):
                        read_stats = load_json(READ_STATS_FILE, {"total_opens": 0, "daily": {}})
                    elif bn == os.path.basename(RATINGS_FILE):
                        ratings_data = load_json(RATINGS_FILE, {"entries": [], "bot_sum": 0, "news_sum": 0, "count": 0})
                    elif bn == os.path.basename(STATS_FILE):
                        stats = load_json(STATS_FILE, {})
                    restored.append(f"✅ {name}")
            count = len(restored)
            bot.send_message(
                message.chat.id,
                f"✅ تم استعادة الإعدادات بنجاح!\n"
                f"📂 عدد الملفات المستعادة: {count}"
            )
        except Exception as e:
            bot.send_message(message.chat.id, f"❌ فشل استعادة الملف: {str(e)[:200]}")
        return

    # ── استعادة من ملف .db فقط (للتوافق مع النسخ القديمة) ──
    if doc.file_name.endswith(".db"):
        try:
            backup_path = DB_FILE + ".bak"
            if os.path.exists(DB_FILE):
                shutil.copy2(DB_FILE, backup_path)
            with open(DB_FILE, "wb") as f:
                f.write(downloaded)
            with _db_lock:
                _db_conn.close()
                _db_conn = sqlite3.connect(DB_FILE, check_same_thread=False)
                _db_conn.execute("PRAGMA journal_mode=WAL")
                _db_conn.execute("PRAGMA synchronous=NORMAL")
                # FIX: sync db.py module reference so scheduled jobs don't use closed conn
                _db_module._db_conn = _db_conn
            users = _db_load_users()
            bot.send_message(
                message.chat.id,
                f"✅ *تم استعادة قاعدة البيانات بنجاح!*\n"
                f"👥 عدد المستخدمين المحملين: `{len(users)}`",
                parse_mode="Markdown"
            )
        except Exception as e:
            bot.send_message(message.chat.id, f"❌ فشل استعادة البيانات: {e}")

# ======== الجدولة ========
# ======== تغليف آمن للمهام المجدولة ========
def cb_group_vote(call):
    uid = call.from_user.id
    parts = call.data.split("_")
    if len(parts) < 3:
        return
    vote_type = parts[1]  # yes / no
    mid = int(parts[2])
    vote_data = _group_votes.get(mid)
    if not vote_data:
        bot.answer_callback_query(call.id, "⏰ انتهت صلاحية التصويت")
        return
    # إزالة أي تصويت سابق للمستخدم
    vote_data["yes"].discard(uid)
    vote_data["no"].discard(uid)
    if vote_type == "yes":
        vote_data["yes"].add(uid)
        bot.answer_callback_query(call.id, "👍 صوّتت: مهم")
    else:
        vote_data["no"].add(uid)
        bot.answer_callback_query(call.id, "👎 صوّتت: غير مهم")
    # تحديث الأزرار بعداد التصويت
    yes_count = len(vote_data["yes"])
    no_count  = len(vote_data["no"])
    markup = types.InlineKeyboardMarkup(row_width=3)
    markup.add(
        types.InlineKeyboardButton(f"👍 {yes_count}", callback_data=f"gvote_yes_{mid}"),
        types.InlineKeyboardButton(f"👎 {no_count}",  callback_data=f"gvote_no_{mid}"),
        types.InlineKeyboardButton("🔗 فتح", url=vote_data["link"]),
    )
    try:
        bot.edit_message_reply_markup(vote_data["chat_id"], mid, reply_markup=markup)
    except Exception as _exc:
        _log_exc(_exc)
    # تعلّم من التصويت الإيجابي لتحسين التوصيات
    if vote_type == "yes":
        u = users.get(str(uid), {})
        u["rated_positive"] = u.get("rated_positive", 0) + 1
        _db_save_user(uid, u)
    else:
        u = users.get(str(uid), {})
        u["rated_negative"] = u.get("rated_negative", 0) + 1
        _db_save_user(uid, u)


def handle_sports_cmd(message):
    uid = message.from_user.id
    prefs = _get_user_sports(uid)
    # إصلاح #5: العربية هي اللغة الافتراضية لكل القسم الرياضي
    lang = users.get(str(uid), {}).get("lang", "العربية 🇮🇶")
    selected = prefs.get('leagues', [])
    leagues_text = _ul(lang, "sports_leagues", n=len(selected)) if selected else _ul(lang, "sports_no_leagues")
    alerts_text = _ul(lang, "sports_alerts_on") if prefs.get('live_alerts') else _ul(lang, "sports_alerts_off")
    prefs2   = _get_user_sports(uid)
    sel2     = prefs2.get('leagues', [])
    # ملخص الرياضات المختارة
    sport_summary2 = {}
    for lk2 in sel2:
        sp2 = SPORTS_LEAGUES.get(lk2, {}).get('sport', '')
        if sp2:
            sport_summary2[sp2] = sport_summary2.get(sp2, 0) + 1
    sport_lines = [
        f"  {SPORT_CATEGORIES.get(sp2,{}).get('flag','')} {SPORT_CATEGORIES.get(sp2,{}).get('name','')}: {cnt} دوري"
        for sp2, cnt in sport_summary2.items()
    ]
    summary_block = ("\n" + "\n".join(sport_lines)) if sport_lines else ""
    text = (
        _ul(lang, "sports_title")
        + f"📊 {leagues_text}{summary_block}\n"
        + f"🔔 {alerts_text}\n\n"
        + _ul(lang, "sports_choose")
    )
    bot.send_message(message.chat.id, text, parse_mode="Markdown",
                     reply_markup=_sports_main_keyboard(uid))

@bot.callback_query_handler(func=lambda c: c.data == "menu_weather")
def cb_menu_weather(call):
    bot.answer_callback_query(call.id)
    uid = call.from_user.id
    user = users.get(str(uid))
    if not user or not user.get("province"):
        bot.send_message(call.message.chat.id, "⚠️ لم تحدد مدينتك بعد. أرسل /start لإعداد حسابك.")
        return
    send_detailed_weather(uid)

@bot.callback_query_handler(func=lambda c: c.data == "menu_markets")
def cb_menu_markets(call):
    bot.answer_callback_query(call.id)
    uid = call.from_user.id
    user = users.get(str(uid))
    if not user:
        welcome_user(uid)
        return
    send_currency(uid)

@bot.callback_query_handler(func=lambda c: c.data == "menu_settings")
def cb_menu_help(call):
    uid = call.from_user.id
    lang = users.get(str(uid), {}).get('lang', 'العربية 🇮🇶')
    bot.answer_callback_query(call.id)
    # دالة مساعدة لبناء النص حسب اللغة
    _help_texts = {
        "العربية 🇮🇶":
            "📖 *دليل الأوامر*\n\n"
            "📰 `/news` — آخر الأخبار\n"
            "🔍 `/deepsearch موضوع` — بحث عميق\n"
            "✅ `/verify خبر` — كشف الأخبار الكاذبة\n"
            "🧠 `/analyze خبر` — تحليل سياسي\n"
            "🌐 `/compare موضوع` — مقارنة مصادر\n"
            "📅 `/timeline موضوع` — خط زمني\n"
            "🔮 `/predict موضوع` — توقعات\n"
            "🗺 `/influence اسم` — خريطة نفوذ\n"
            "🕵️ `/profile اسم` — ملف شخصية\n"
            "🏛 `/parliament` — ملخص البرلمان\n"
            "💬 `/ask سؤال` — اسألني\n"
            "📉 `/econ` — مؤشرات اقتصادية\n"
            "🔴 `/live حدث` — بث مباشر\n"
            "📢 `/submit خبر` — شارك خبراً\n"
            "📊 `/sources` — تصنيف المصادر\n"
            "🏅 `/sports` — الرياضة\n"
            "🌤 `/weather مدينة` — الطقس\n"
            "💱 `/currency` — العملات\n"
            "⚙️ `/settings` — الإعدادات",
        "Русский 🇷🇺":
            "📖 *Руководство по командам*\n\n"
            "📰 `/news` — Последние новости\n"
            "🔍 `/deepsearch тема` — Глубокий поиск\n"
            "✅ `/verify заголовок` — Проверка новости\n"
            "🧠 `/analyze заголовок` — Политический анализ\n"
            "🌐 `/compare тема` — Сравнение источников\n"
            "📅 `/timeline тема` — Хронология событий\n"
            "🔮 `/predict тема` — Прогнозы\n"
            "🗺 `/influence имя` — Карта влияния\n"
            "🕵️ `/profile имя` — Профиль личности\n"
            "🏛 `/parliament` — Краткое изложение\n"
            "💬 `/ask вопрос` — Задать вопрос\n"
            "📉 `/econ` — Экономические показатели\n"
            "🔴 `/live событие` — Прямой эфир\n"
            "📢 `/submit новость` — Поделиться\n"
            "🏅 `/sports` — Спорт\n"
            "🌤 `/weather город` — Погода\n"
            "💱 `/currency` — Курсы валют\n"
            "⚙️ `/settings` — Настройки",
        "فارسی 🇮🇷":
            "📖 *راهنمای دستورات*\n\n"
            "📰 `/news` — آخرین اخبار\n"
            "🔍 `/deepsearch موضوع` — جستجوی عمیق\n"
            "✅ `/verify خبر` — تأیید خبر\n"
            "🧠 `/analyze خبر` — تحلیل سیاسی\n"
            "🌐 `/compare موضوع` — مقایسه منابع\n"
            "📅 `/timeline موضوع` — خط زمانی\n"
            "🔮 `/predict موضوع` — پیشبینی\n"
            "🗺 `/influence نام` — نقشه نفوذ\n"
            "🕵️ `/profile نام` — پروفایل\n"
            "🏛 `/parliament` — خلاصه پارلمان\n"
            "💬 `/ask سوال` — بپرس\n"
            "📉 `/econ` — شاخصهای اقتصادی\n"
            "🔴 `/live رویداد` — زنده\n"
            "📢 `/submit خبر` — ارسال خبر\n"
            "🏅 `/sports` — ورزش\n"
            "🌤 `/weather شهر` — آبوهوا\n"
            "💱 `/currency` — نرخ ارز\n"
            "⚙️ `/settings` — تنظیمات",
        "हिन्दी 🇮🇳":
            "📖 *कमांड गाइड*\n\n"
            "📰 `/news` — ताज़ा समाचार\n"
            "🔍 `/deepsearch विषय` — गहन खोज\n"
            "✅ `/verify शीर्षक` — समाचार जांच\n"
            "🧠 `/analyze शीर्षक` — राजनीतिक विश्लेषण\n"
            "🌐 `/compare विषय` — स्रोत तुलना\n"
            "📅 `/timeline विषय` — समयरेखा\n"
            "🔮 `/predict विषय` — भविष्यवाणी\n"
            "🗺 `/influence नाम` — प्रभाव मानचित्र\n"
            "🕵️ `/profile नाम` — व्यक्ति प्रोफ़ाइल\n"
            "🏛 `/parliament` — संसद सारांश\n"
            "💬 `/ask प्रश्न` — मुझसे पूछें\n"
            "📉 `/econ` — आर्थिक संकेतक\n"
            "🔴 `/live इवेंट` — लाइव ट्रैकिंग\n"
            "📢 `/submit समाचार` — समाचार भेजें\n"
            "🏅 `/sports` — खेल\n"
            "🌤 `/weather शहर` — मौसम\n"
            "💱 `/currency` — मुद्रा दरें\n"
            "⚙️ `/settings` — सेटिंग्स",
        "Português 🇧🇷":
            "📖 *Guia de Comandos*\n\n"
            "📰 `/news` — Últimas notícias\n"
            "🔍 `/deepsearch tópico` — Pesquisa profunda\n"
            "✅ `/verify manchete` — Verificar notícia\n"
            "🧠 `/analyze manchete` — Análise política\n"
            "🌐 `/compare tópico` — Comparar fontes\n"
            "📅 `/timeline tópico` — Linha do tempo\n"
            "🔮 `/predict tópico` — Previsões\n"
            "🗺 `/influence nome` — Mapa de influência\n"
            "🕵️ `/profile nome` — Perfil de pessoa\n"
            "🏛 `/parliament` — Resumo do parlamento\n"
            "💬 `/ask pergunta` — Pergunte-me\n"
            "📉 `/econ` — Indicadores econômicos\n"
            "🔴 `/live evento` — Ao vivo\n"
            "📢 `/submit notícia` — Enviar notícia\n"
            "🏅 `/sports` — Esportes\n"
            "🌤 `/weather cidade` — Clima\n"
            "💱 `/currency` — Taxas de câmbio\n"
            "⚙️ `/settings` — Configurações",
        "Türkçe 🇹🇷":
            "📖 *Komut Rehberi*\n\n"
            "📰 `/news` — Son haberler\n"
            "🔍 `/deepsearch konu` — Derin araştırma\n"
            "✅ `/verify başlık` — Haber doğrula\n"
            "🧠 `/analyze başlık` — Siyasi analiz\n"
            "🌐 `/compare konu` — Kaynak karşılaştır\n"
            "📅 `/timeline konu` — Zaman çizelgesi\n"
            "🔮 `/predict konu` — Tahminler\n"
            "🗺 `/influence isim` — Nüfuz haritası\n"
            "🕵️ `/profile isim` — Kişi profili\n"
            "🏛 `/parliament` — Parlamento özeti\n"
            "💬 `/ask soru` — Bana sor\n"
            "📉 `/econ` — Ekonomik göstergeler\n"
            "🔴 `/live etkinlik` — Canlı takip\n"
            "📢 `/submit haber` — Haber gönder\n"
            "🏅 `/sports` — Spor\n"
            "🌤 `/weather şehir` — Hava durumu\n"
            "💱 `/currency` — Döviz kurları\n"
            "⚙️ `/settings` — Ayarlar",
        "اردو 🇵🇰":
            "📖 *کمانڈ گائیڈ*\n\n"
            "📰 `/news` — تازہ خبریں\n"
            "🔍 `/deepsearch موضوع` — گہری تحقیق\n"
            "✅ `/verify خبر` — خبر کی تصدیق\n"
            "🧠 `/analyze خبر` — سیاسی تجزیہ\n"
            "🌐 `/compare موضوع` — ذرائع کا موازنہ\n"
            "📅 `/timeline موضوع` — وقت کی لکیر\n"
            "🔮 `/predict موضوع` — پیشن گوئیاں\n"
            "🗺 `/influence نام` — اثر کا نقشہ\n"
            "🕵️ `/profile نام` — شخصیت پروفائل\n"
            "🏛 `/parliament` — پارلیمنٹ خلاصہ\n"
            "💬 `/ask سوال` — مجھ سے پوچھیں\n"
            "📉 `/econ` — معاشی اشارے\n"
            "🔴 `/live تقریب` — براہ راست\n"
            "📢 `/submit خبر` — خبر بھیجیں\n"
            "🏅 `/sports` — کھیل\n"
            "🌤 `/weather شہر` — موسم\n"
            "💱 `/currency` — کرنسی ریٹس\n"
            "⚙️ `/settings` — ترتیبات",
        "Deutsch 🇩🇪":
            "📖 *Befehlsanleitung*\n\n"
            "📰 `/news` — Aktuelle Nachrichten\n"
            "🔍 `/deepsearch Thema` — Tiefenrecherche\n"
            "✅ `/verify Überschrift` — Nachricht prüfen\n"
            "🧠 `/analyze Überschrift` — Politische Analyse\n"
            "🌐 `/compare Thema` — Quellen vergleichen\n"
            "📅 `/timeline Thema` — Zeitlinie\n"
            "🔮 `/predict Thema` — Vorhersagen\n"
            "🗺 `/influence Name` — Einfluss-Karte\n"
            "🕵️ `/profile Name` — Personen-Profil\n"
            "🏛 `/parliament` — Parlamentszusammenfassung\n"
            "💬 `/ask Frage` — Frag mich\n"
            "📉 `/econ` — Wirtschaftsindikatoren\n"
            "🔴 `/live Ereignis` — Live-Verfolgung\n"
            "📢 `/submit Nachricht` — Nachricht einreichen\n"
            "🏅 `/sports` — Sport\n"
            "🌤 `/weather Stadt` — Wetter\n"
            "💱 `/currency` — Währungskurse\n"
            "⚙️ `/settings` — Einstellungen",
        "Українська 🇺🇦":
            "📖 *Посібник команд*\n\n"
            "📰 `/news` — Останні новини\n"
            "🔍 `/deepsearch тема` — Глибокий пошук\n"
            "✅ `/verify заголовок` — Перевірка новини\n"
            "🧠 `/analyze заголовок` — Політичний аналіз\n"
            "🌐 `/compare тема` — Порівняння джерел\n"
            "📅 `/timeline тема` — Хронологія\n"
            "🔮 `/predict тема` — Прогнози\n"
            "🗺 `/influence ім\'я` — Карта впливу\n"
            "🕵️ `/profile ім\'я` — Профіль особи\n"
            "🏛 `/parliament` — Зведення парламенту\n"
            "💬 `/ask питання` — Запитай мене\n"
            "📉 `/econ` — Економічні показники\n"
            "🔴 `/live подія` — Пряма трансляція\n"
            "📢 `/submit новина` — Надіслати новину\n"
            "🏅 `/sports` — Спорт\n"
            "🌤 `/weather місто` — Погода\n"
            "💱 `/currency` — Курси валют\n"
            "⚙️ `/settings` — Налаштування",
        "Italiano 🇮🇹":
            "📖 *Guida ai Comandi*\n\n"
            "📰 `/news` — Ultime notizie\n"
            "🔍 `/deepsearch argomento` — Ricerca approfondita\n"
            "✅ `/verify titolo` — Verifica notizia\n"
            "🧠 `/analyze titolo` — Analisi politica\n"
            "🌐 `/compare argomento` — Confronta fonti\n"
            "📅 `/timeline argomento` — Linea del tempo\n"
            "🔮 `/predict argomento` — Previsioni\n"
            "🗺 `/influence nome` — Mappa influenza\n"
            "🕵️ `/profile nome` — Profilo persona\n"
            "🏛 `/parliament` — Riepilogo parlamento\n"
            "💬 `/ask domanda` — Chiedimi\n"
            "📉 `/econ` — Indicatori economici\n"
            "🔴 `/live evento` — Evento live\n"
            "📢 `/submit notizia` — Invia notizia\n"
            "🏅 `/sports` — Sport\n"
            "🌤 `/weather città` — Meteo\n"
            "💱 `/currency` — Tassi di cambio\n"
            "⚙️ `/settings` — Impostazioni",
        "Español 🇲🇽":
            "📖 *Guía de Comandos*\n\n"
            "📰 `/news` — Últimas noticias\n"
            "🔍 `/deepsearch tema` — Búsqueda profunda\n"
            "✅ `/verify titular` — Verificar noticia\n"
            "🧠 `/analyze titular` — Análisis político\n"
            "🌐 `/compare tema` — Comparar fuentes\n"
            "📅 `/timeline tema` — Línea de tiempo\n"
            "🔮 `/predict tema` — Predicciones\n"
            "🗺 `/influence nombre` — Mapa de influencia\n"
            "🕵️ `/profile nombre` — Perfil de persona\n"
            "🏛 `/parliament` — Resumen del parlamento\n"
            "💬 `/ask pregunta` — Pregúntame\n"
            "📉 `/econ` — Indicadores económicos\n"
            "🔴 `/live evento` — Seguimiento en vivo\n"
            "📢 `/submit noticia` — Enviar noticia\n"
            "🏅 `/sports` — Deportes\n"
            "🌤 `/weather ciudad` — Clima\n"
            "💱 `/currency` — Tipos de cambio\n"
            "⚙️ `/settings` — Configuración",
    }
    bot.send_message(call.message.chat.id,
        _help_texts.get(lang, _help_texts["English 🇬🇧"]), parse_mode="Markdown")

# ─── AI Menu callbacks ───────────────────────────────────────────
_aimenu_prompts = {
    "aimenu_verify": {
        "العربية 🇮🇶":   "أرسل:\n`/verify عنوان الخبر`",
        "English 🇬🇧":   "Send:\n`/verify headline`",
        "Русский 🇷🇺":   "Отправьте:\n`/verify заголовок`",
        "فارسی 🇮🇷":    "ارسال:\n`/verify تیتر خبر`",
        "हिन्दी 🇮🇳":   "भेजें:\n`/verify शीर्षक`",
        "Português 🇧🇷": "Envie:\n`/verify manchete`",
        "Türkçe 🇹🇷":   "Gönderin:\n`/verify başlık`",
        "اردو 🇵🇰":     "بھیجیں:\n`/verify خبر کا عنوان`",
        "Deutsch 🇩🇪":  "Senden:\n`/verify Schlagzeile`",
        "Українська 🇺🇦": "Надішліть:\n`/verify заголовок`",
        "Italiano 🇮🇹": "Invia:\n`/verify titolo`",
        "Español 🇲🇽":  "Envía:\n`/verify titular`",
    },
    "aimenu_analyze": {
        "العربية 🇮🇶":   "أرسل:\n`/analyze عنوان الخبر`",
        "English 🇬🇧":   "Send:\n`/analyze headline`",
        "Русский 🇷🇺":   "Отправьте:\n`/analyze заголовок`",
        "فارسی 🇮🇷":    "ارسال:\n`/analyze تیتر خبر`",
        "हिन्दी 🇮🇳":   "भेजें:\n`/analyze शीर्षक`",
        "Português 🇧🇷": "Envie:\n`/analyze manchete`",
        "Türkçe 🇹🇷":   "Gönderin:\n`/analyze başlık`",
        "اردو 🇵🇰":     "بھیجیں:\n`/analyze خبر کا عنوان`",
        "Deutsch 🇩🇪":  "Senden:\n`/analyze Schlagzeile`",
        "Українська 🇺🇦": "Надішліть:\n`/analyze заголовок`",
        "Italiano 🇮🇹": "Invia:\n`/analyze titolo`",
        "Español 🇲🇽":  "Envía:\n`/analyze titular`",
    },
    "aimenu_compare": {
        "العربية 🇮🇶":   "أرسل:\n`/compare الموضوع`",
        "English 🇬🇧":   "Send:\n`/compare topic`",
        "Русский 🇷🇺":   "Отправьте:\n`/compare тема`",
        "فارسی 🇮🇷":    "ارسال:\n`/compare موضوع`",
        "हिन्दी 🇮🇳":   "भेजें:\n`/compare विषय`",
        "Português 🇧🇷": "Envie:\n`/compare tópico`",
        "Türkçe 🇹🇷":   "Gönderin:\n`/compare konu`",
        "اردو 🇵🇰":     "بھیجیں:\n`/compare موضوع`",
        "Deutsch 🇩🇪":  "Senden:\n`/compare Thema`",
        "Українська 🇺🇦": "Надішліть:\n`/compare тема`",
        "Italiano 🇮🇹": "Invia:\n`/compare argomento`",
        "Español 🇲🇽":  "Envía:\n`/compare tema`",
    },
    "aimenu_timeline": {
        "العربية 🇮🇶":   "أرسل:\n`/timeline الموضوع`",
        "English 🇬🇧":   "Send:\n`/timeline topic`",
        "Русский 🇷🇺":   "Отправьте:\n`/timeline тема`",
        "فارسی 🇮🇷":    "ارسال:\n`/timeline موضوع`",
        "हिन्दी 🇮🇳":   "भेजें:\n`/timeline विषय`",
        "Português 🇧🇷": "Envie:\n`/timeline tópico`",
        "Türkçe 🇹🇷":   "Gönderin:\n`/timeline konu`",
        "اردو 🇵🇰":     "بھیجیں:\n`/timeline موضوع`",
        "Deutsch 🇩🇪":  "Senden:\n`/timeline Thema`",
        "Українська 🇺🇦": "Надішліть:\n`/timeline тема`",
        "Italiano 🇮🇹": "Invia:\n`/timeline argomento`",
        "Español 🇲🇽":  "Envía:\n`/timeline tema`",
    },
    "aimenu_predict": {
        "العربية 🇮🇶":   "أرسل:\n`/predict الموضوع`",
        "English 🇬🇧":   "Send:\n`/predict topic`",
        "Русский 🇷🇺":   "Отправьте:\n`/predict тема`",
        "فارسی 🇮🇷":    "ارسال:\n`/predict موضوع`",
        "हिन्दी 🇮🇳":   "भेजें:\n`/predict विषय`",
        "Português 🇧🇷": "Envie:\n`/predict tópico`",
        "Türkçe 🇹🇷":   "Gönderin:\n`/predict konu`",
        "اردو 🇵🇰":     "بھیجیں:\n`/predict موضوع`",
        "Deutsch 🇩🇪":  "Senden:\n`/predict Thema`",
        "Українська 🇺🇦": "Надішліть:\n`/predict тема`",
        "Italiano 🇮🇹": "Invia:\n`/predict argomento`",
        "Español 🇲🇽":  "Envía:\n`/predict tema`",
    },
    "aimenu_influence": {
        "العربية 🇮🇶":   "أرسل:\n`/influence الاسم`",
        "English 🇬🇧":   "Send:\n`/influence name`",
        "Русский 🇷🇺":   "Отправьте:\n`/influence имя`",
        "فارسی 🇮🇷":    "ارسال:\n`/influence نام`",
        "हिन्दी 🇮🇳":   "भेजें:\n`/influence नाम`",
        "Português 🇧🇷": "Envie:\n`/influence nome`",
        "Türkçe 🇹🇷":   "Gönderin:\n`/influence ad`",
        "اردو 🇵🇰":     "بھیجیں:\n`/influence نام`",
        "Deutsch 🇩🇪":  "Senden:\n`/influence Name`",
        "Українська 🇺🇦": "Надішліть:\n`/influence ім'я`",
        "Italiano 🇮🇹": "Invia:\n`/influence nome`",
        "Español 🇲🇽":  "Envía:\n`/influence nombre`",
    },
    "aimenu_profile": {
        "العربية 🇮🇶":   "أرسل:\n`/profile الاسم`",
        "English 🇬🇧":   "Send:\n`/profile name`",
        "Русский 🇷🇺":   "Отправьте:\n`/profile имя`",
        "فارسی 🇮🇷":    "ارسال:\n`/profile نام`",
        "हिन्दी 🇮🇳":   "भेजें:\n`/profile नाम`",
        "Português 🇧🇷": "Envie:\n`/profile nome`",
        "Türkçe 🇹🇷":   "Gönderin:\n`/profile ad`",
        "اردو 🇵🇰":     "بھیجیں:\n`/profile نام`",
        "Deutsch 🇩🇪":  "Senden:\n`/profile Name`",
        "Українська 🇺🇦": "Надішліть:\n`/profile ім'я`",
        "Italiano 🇮🇹": "Invia:\n`/profile nome`",
        "Español 🇲🇽":  "Envía:\n`/profile nombre`",
    },
    "aimenu_ask": {
        "العربية 🇮🇶":   "أرسل:\n`/ask سؤالك`",
        "English 🇬🇧":   "Send:\n`/ask your question`",
        "Русский 🇷🇺":   "Отправьте:\n`/ask ваш вопрос`",
        "فارسی 🇮🇷":    "ارسال:\n`/ask سوال شما`",
        "हिन्दी 🇮🇳":   "भेजें:\n`/ask आपका प्रश्न`",
        "Português 🇧🇷": "Envie:\n`/ask sua pergunta`",
        "Türkçe 🇹🇷":   "Gönderin:\n`/ask sorunuz`",
        "اردو 🇵🇰":     "بھیجیں:\n`/ask آپ کا سوال`",
        "Deutsch 🇩🇪":  "Senden:\n`/ask Ihre Frage`",
        "Українська 🇺🇦": "Надішліть:\n`/ask ваше питання`",
        "Italiano 🇮🇹": "Invia:\n`/ask la tua domanda`",
        "Español 🇲🇽":  "Envía:\n`/ask tu pregunta`",
    },
    "aimenu_parliament": {
        "العربية 🇮🇶":   "أرسل:\n`/parliament`\nللحصول على ملخص جلسات البرلمان",
        "English 🇬🇧":   "Send:\n`/parliament`\nTo get parliament session summaries",
        "Русский 🇷🇺":   "Отправьте:\n`/parliament`\nДля сводки заседаний парламента",
        "فارسی 🇮🇷":    "ارسال:\n`/parliament`\nبرای خلاصه جلسات پارلمان",
        "हिन्दी 🇮🇳":   "भेजें:\n`/parliament`\nसंसद सत्र सारांश के लिए",
        "Português 🇧🇷": "Envie:\n`/parliament`\nPara resumos das sessões do parlamento",
        "Türkçe 🇹🇷":   "Gönderin:\n`/parliament`\nMeclis oturumu özetleri için",
        "اردو 🇵🇰":     "بھیجیں:\n`/parliament`\nپارلیمنٹ کے اجلاس کے خلاصوں کے لیے",
        "Deutsch 🇩🇪":  "Senden:\n`/parliament`\nFür Parlamentssitzungs-Zusammenfassungen",
        "Українська 🇺🇦": "Надішліть:\n`/parliament`\nДля зведень засідань парламенту",
        "Italiano 🇮🇹": "Invia:\n`/parliament`\nPer i riepiloghi delle sessioni parlamentari",
        "Español 🇲🇽":  "Envía:\n`/parliament`\nPara resúmenes de sesiones parlamentarias",
    },
    "aimenu_econ": {
        "العربية 🇮🇶":   "أرسل:\n`/econ`\nللحصول على التقرير الاقتصادي",
        "English 🇬🇧":   "Send:\n`/econ`\nTo get the economic report",
        "Русский 🇷🇺":   "Отправьте:\n`/econ`\nДля получения экономического отчёта",
        "فارسی 🇮🇷":    "ارسال:\n`/econ`\nبرای دریافت گزارش اقتصادی",
        "हिन्दी 🇮🇳":   "भेजें:\n`/econ`\nआर्थिक रिपोर्ट के लिए",
        "Português 🇧🇷": "Envie:\n`/econ`\nPara obter o relatório econômico",
        "Türkçe 🇹🇷":   "Gönderin:\n`/econ`\nEkonomik rapor için",
        "اردو 🇵🇰":     "بھیجیں:\n`/econ`\nاقتصادی رپورٹ کے لیے",
        "Deutsch 🇩🇪":  "Senden:\n`/econ`\nFür den Wirtschaftsbericht",
        "Українська 🇺🇦": "Надішліть:\n`/econ`\nДля отримання економічного звіту",
        "Italiano 🇮🇹": "Invia:\n`/econ`\nPer ottenere il rapporto economico",
        "Español 🇲🇽":  "Envía:\n`/econ`\nPara obtener el informe económico",
    },
    "aimenu_live": {
        "العربية 🇮🇶":   "أرسل:\n`/live اسم الحدث`\nللمتابعة اللحظية",
        "English 🇬🇧":   "Send:\n`/live event name`\nFor live coverage",
        "Русский 🇷🇺":   "Отправьте:\n`/live название события`\nДля прямого освещения",
        "فارسی 🇮🇷":    "ارسال:\n`/live نام رویداد`\nبرای پوشش زنده",
        "हिन्दी 🇮🇳":   "भेजें:\n`/live घटना का नाम`\nलाइव कवरेज के लिए",
        "Português 🇧🇷": "Envie:\n`/live nome do evento`\nPara cobertura ao vivo",
        "Türkçe 🇹🇷":   "Gönderin:\n`/live etkinlik adı`\nCanlı yayın için",
        "اردو 🇵🇰":     "بھیجیں:\n`/live واقعہ کا نام`\nلائیو کوریج کے لیے",
        "Deutsch 🇩🇪":  "Senden:\n`/live Ereignisname`\nFür Live-Berichterstattung",
        "Українська 🇺🇦": "Надішліть:\n`/live назва події`\nДля прямого висвітлення",
        "Italiano 🇮🇹": "Invia:\n`/live nome evento`\nPer la copertura in diretta",
        "Español 🇲🇽":  "Envía:\n`/live nombre del evento`\nPara cobertura en vivo",
    },
    "aimenu_submit": {
        "العربية 🇮🇶":   "أرسل:\n`/submit نص الخبر`\nلتقديم خبر للنشر",
        "English 🇬🇧":   "Send:\n`/submit news text`\nTo submit news for publication",
        "Русский 🇷🇺":   "Отправьте:\n`/submit текст новости`\nДля подачи новости на публикацию",
        "فارسی 🇮🇷":    "ارسال:\n`/submit متن خبر`\nبرای ارسال خبر برای انتشار",
        "हिन्दी 🇮🇳":   "भेजें:\n`/submit समाचार पाठ`\nप्रकाशन के लिए समाचार सबमिट करें",
        "Português 🇧🇷": "Envie:\n`/submit texto da notícia`\nPara enviar notícia para publicação",
        "Türkçe 🇹🇷":   "Gönderin:\n`/submit haber metni`\nYayın için haber göndermek için",
        "اردو 🇵🇰":     "بھیجیں:\n`/submit خبر کا متن`\nاشاعت کے لیے خبر جمع کرانے کے لیے",
        "Deutsch 🇩🇪":  "Senden:\n`/submit Nachrichtentext`\nUm eine Nachricht zur Veröffentlichung einzureichen",
        "Українська 🇺🇦": "Надішліть:\n`/submit текст новини`\nДля подачі новини на публікацію",
        "Italiano 🇮🇹": "Invia:\n`/submit testo della notizia`\nPer inviare notizie per la pubblicazione",
        "Español 🇲🇽":  "Envía:\n`/submit texto de la noticia`\nPara enviar noticias para su publicación",
    },
}

@bot.callback_query_handler(func=lambda c: c.data in ("menu_saved", "menu_referral", "menu_digest"))
def cb_menu_extras(call):
    uid = call.from_user.id
    bot.answer_callback_query(call.id)
    if call.data == "menu_saved":
        class _FM:
            from_user = type("U", (), {"id": uid})()
            chat      = type("C", (), {"id": uid, "type": "private"})()
        cmd_saved(_FM())
    elif call.data == "menu_referral":
        class _FM:
            from_user = type("U", (), {"id": uid})()
            chat      = type("C", (), {"id": uid, "type": "private"})()
            text      = "/referral"
        cmd_referral(_FM())
    elif call.data == "menu_digest":
        class _FM:
            from_user = type("U", (), {"id": uid})()
            chat      = type("C", (), {"id": uid, "type": "private"})()
            text      = "/digest"
        cmd_digest(_FM())

# FIX: مكرَّرة عن bot_finance.cmd_chart (نفس الاسم) — الأمر الحقيقي /chart
# مسجَّل هناك بـ @bot.message_handler(commands=["chart"]). كانت هذه النسخة
# مربوطة خطأً بـ callback_data يبدأ بـ "aimenu_" مما يخطف كل أزرار قائمة AI.
def cmd_chart_dup_unused(m):
    uid = m.from_user.id
    _update_user_last_command(uid, "/chart")
    user = users.get(str(uid), {})
    lang = user.get("lang", "English 🇬🇧")
    _send_chart_categories(uid, lang)

@bot.callback_query_handler(func=lambda c: c.data.startswith("chart_cat_"))
def chart_cat_selected(call):
    uid = call.from_user.id
    cat = call.data.replace("chart_cat_", "")
    user = users.get(str(uid), {})
    lang = user.get("lang", "English 🇬🇧")
    bot.answer_callback_query(call.id)
    if cat == "custom":
        custom_text = (
            "🔍 *أرسل رمز الأصل:*\n\n"
            "🪙 عملات رقمية: `BTC`، `ETH`، `SOL`\n"
            "💱 فوركس: `EURUSD=X`، `GBPUSD=X`\n"
            "🥇 معادن: `GC=F` (ذهب)، `SI=F` (فضة)\n"
            "🛢 سلع: `CL=F` (نفط)، `NG=F` (غاز)\n"
            "📈 أسهم: `AAPL`، `TSLA`، `NVDA`\n"
            "📊 مؤشرات: `^GSPC`، `^IXIC`، `^DJI`"
            if lang == "العربية 🇮🇶" else
            "🔍 *Send the asset symbol:*\n\n"
            "🪙 Crypto: `BTC`, `ETH`, `SOL`\n"
            "💱 Forex: `EURUSD=X`, `GBPUSD=X`\n"
            "🥇 Metals: `GC=F` (Gold), `SI=F` (Silver)\n"
            "🛢 Commodities: `CL=F` (WTI Oil), `NG=F` (Gas)\n"
            "📈 Stocks: `AAPL`, `TSLA`, `NVDA`\n"
            "📊 Indices: `^GSPC`, `^IXIC`, `^DJI`"
        )
        try:
            bot.edit_message_text(custom_text, chat_id=uid,
                                  message_id=call.message.message_id, parse_mode="Markdown")
        except Exception:
            bot.send_message(uid, custom_text, parse_mode="Markdown")
        bot.register_next_step_handler_by_chat_id(uid, _chart_custom_symbol_step)
        return
    cat_data = CHART_CATEGORIES.get(cat)
    if not cat_data:
        return
    cat_label, assets = cat_data
    prompt = CHART_PROMPTS.get(lang, CHART_PROMPTS["English 🇬🇧"])
    markup = types.InlineKeyboardMarkup(row_width=4)
    buttons = [
        types.InlineKeyboardButton(CHART_ASSET_LABELS.get(s, s), callback_data=f"chart_asset_{s}")
        for s in assets
    ]
    for i in range(0, len(buttons), 4):
        markup.row(*buttons[i:i+4])
    back_label = "⬅️ رجوع" if lang == "العربية 🇮🇶" else "⬅️ Back"
    markup.row(types.InlineKeyboardButton(back_label, callback_data="chart_back_cats"))
    try:
        bot.edit_message_text(
            f"{cat_label}\n{prompt}",
            chat_id=uid,
            message_id=call.message.message_id,
            reply_markup=markup,
            parse_mode="Markdown"
        )
    except Exception:
        bot.send_message(uid, f"{cat_label}\n{prompt}", reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda c: c.data == "chart_back_cats")
def chart_back_cats(call):
    uid = call.from_user.id
    user = users.get(str(uid), {})
    lang = user.get("lang", "English 🇬🇧")
    bot.answer_callback_query(call.id)
    _send_chart_categories(uid, lang, edit_msg_id=call.message.message_id)

@bot.callback_query_handler(func=lambda c: c.data.startswith("chart_asset_"))
def chart_asset_selected(call):
    uid = call.from_user.id
    symbol = call.data.replace("chart_asset_", "")
    user = users.get(str(uid), {})
    lang = user.get("lang", "English 🇬🇧")
    bot.answer_callback_query(call.id)
    prompt = INTERVAL_PROMPTS.get(lang, INTERVAL_PROMPTS["English 🇬🇧"])
    markup = types.InlineKeyboardMarkup(row_width=3)
    markup.row(*[
        types.InlineKeyboardButton(k, callback_data=f"chart_interval_{symbol}_{k}")
        for k in CHART_INTERVALS.keys()
    ])
    back_label = "⬅️ رجوع" if lang == "العربية 🇮🇶" else "⬅️ Back"
    markup.row(types.InlineKeyboardButton(back_label, callback_data="chart_back_cats"))
    label = CHART_ASSET_LABELS.get(symbol, symbol)
    try:
        bot.edit_message_text(
            f"✅ *{label}*\n{prompt}",
            chat_id=uid,
            message_id=call.message.message_id,
            reply_markup=markup,
            parse_mode="Markdown"
        )
    except Exception:
        bot.send_message(uid, f"✅ *{label}*\n{prompt}", reply_markup=markup, parse_mode="Markdown")


@bot.callback_query_handler(func=lambda c: c.data.startswith("chart_interval_"))
def chart_interval_selected(call):
    uid = call.from_user.id
    bot.answer_callback_query(call.id, "⏳ جاري تحميل البيانات...")
    parts = call.data.split("_")
    interval_key = parts[-1]
    symbol = "_".join(parts[2:-1])
    user = users.get(str(uid), {})
    lang = user.get("lang", "English 🇬🇧")
    ivl = CHART_INTERVALS.get(interval_key, CHART_INTERVALS["Hours"])
    label = CHART_ASSET_LABELS.get(symbol, symbol)
    bot.edit_message_text(
        f"📊 *{label}* — {ivl['label_en']}\n⏳ جاري تحميل الشموع...",
        chat_id=uid,
        message_id=call.message.message_id,
        parse_mode="Markdown"
    )
    if symbol in CRYPTO_IDS:
        bars = _crypto_ohlc(symbol, ivl["yf_interval"], ivl["range"])
    else:
        bars = _fetch_ohlc(symbol, ivl["yf_interval"], ivl["range"])
    if not bars:
        bot.send_message(uid, f"⚠️ لم تتوفر بيانات لـ *{label}* بهذا الفاصل الزمني.", parse_mode="Markdown")
        return
    chart_text = _build_text_chart(symbol, bars, interval_key)
    if not chart_text:
        bot.send_message(uid, "⚠️ تعذّر بناء الرسم البياني.", parse_mode="Markdown")
        return
    bot.send_message(uid, f"<pre>{chart_text}</pre>", parse_mode="HTML")


# ======== أوامر الأخبار والطقس والأسواق ========

@bot.message_handler(commands=["weather"])
def cmd_weather(m):
    if not _FF.get("weather", True):
        bot.send_message(m.chat.id, "⚙️ هذه الميزة موقوفة مؤقتاً.")
        return
    uid = m.from_user.id
    if uid in banned: return
    if bot_paused: return
    _update_user_last_command(uid, "/weather")
    user = users.get(str(uid))
    if not user:
        welcome_user(uid)
        return
    province = user.get("province", "")
    if not province:
        bot.send_message(uid, "⚠️ لم تحدد مدينتك بعد. أرسل /start لإعادة الإعداد.")
        return
    send_detailed_weather(uid)


@bot.message_handler(commands=["currency"])
def cmd_currency(m):
    uid = m.from_user.id
    if uid in banned: return
    if bot_paused: return
    _update_user_last_command(uid, "/currency")
    user = users.get(str(uid))
    if not user:
        welcome_user(uid)
        return
    send_currency(uid)


@bot.message_handler(commands=["markets"])
def cmd_markets(m):
    uid = m.from_user.id
    if uid in banned: return
    if bot_paused: return
    _update_user_last_command(uid, "/markets")
    user = users.get(str(uid), {})
    lang = user.get("lang", "English 🇬🇧")
    bot.send_message(uid, "⏳ جاري تحميل أسعار الأسواق...", parse_mode="Markdown")

    MARKET_SYMBOLS = [
        ("💎 عملات رقمية", ["BTC", "ETH", "BNB", "SOL", "XRP", "DOGE"]),
        ("💱 عملات فيات", ["EUR", "GBP", "IQD", "SAR", "AED", "TRY"]),
        ("🏅 سلع", ["GC=F", "SI=F", "CL=F", "BZ=F"]),
        ("📈 مؤشرات", ["^GSPC", "^IXIC"]),
        ("📊 أسهم كبرى", ["AAPL", "MSFT", "TSLA", "NVDA", "AMZN"]),
    ]

    lines = ["📊 *أسعار الأسواق العالمية*\n━━━━━━━━━━━━━━━"]
    for section_title, symbols in MARKET_SYMBOLS:
        lines.append(f"\n*{section_title}:*")
        for sym in symbols:
            price = fetch_asset_price(sym)
            lines.append(f"  {format_asset_price(sym, price)}")

    lines.append(f"━━━━━━━━━━━━━━━\n🤖 @{BOT_USERNAME}")
    bot.send_message(uid, "\n".join(lines), parse_mode="Markdown")


@bot.message_handler(commands=["alerts"])
def cmd_alerts(m):
    uid = m.from_user.id
    if uid in banned: return
    if bot_paused: return
    _update_user_last_command(uid, "/alerts")
    user = users.get(str(uid), {})
    lang = user.get("lang", "English 🇬🇧")

    tracked = tracked_assets.get(str(uid), {}).get("assets", [])
    current_alert = user.get("currency_alert")

    markup = types.InlineKeyboardMarkup(row_width=1)

    if tracked:
        markup.add(types.InlineKeyboardButton(
            "💰 تنبيه سعر أصل من قائمة التتبع", callback_data="alerts_track"
        ))

    markup.add(types.InlineKeyboardButton(
        "💱 تنبيه سعر صرف الدولار", callback_data="prem_currency_alert"
    ))
    markup.add(types.InlineKeyboardButton(
        "📋 عرض قائمة التتبع", callback_data="alerts_show_track"
    ))

    msg = "🔔 *إدارة التنبيهات الذكية*\n━━━━━━━━━━━━━━━\n\n"
    if tracked:
        msg += f"📌 رموز تتبعك: `{'  '.join(tracked)}`\n"
    if current_alert:
        msg += f"💱 تنبيه الدولار مضبوط عند: `{current_alert}`\n"
    msg += "\nاختر نوع التنبيه:"

    bot.send_message(uid, msg, parse_mode="Markdown", reply_markup=markup)


@bot.callback_query_handler(func=lambda c: c.data == "alerts_show_track")
def cb_alerts_show_track(call):
    uid = call.from_user.id
    bot.answer_callback_query(call.id)
    # إصلاح #7: حُذف متغير وهمي كان هنا — الكود التالي لا يحتاجه
    data = tracked_assets.get(str(uid), {})
    assets = data.get("assets", [])
    user = users.get(str(uid), {})
    lang = user.get("lang", "English 🇬🇧")
    if not assets:
        bot.send_message(uid, t(lang, "track_empty"), parse_mode="Markdown")
        return
    last_prices = data.get("last_prices", {})
    msg = t(lang, "track_list_header")
    for sym in assets:
        price = fetch_asset_price(sym)
        if price:
            tracked_assets[str(uid)]["last_prices"][sym] = price
            save_tracked_assets()
        msg += f"• {format_asset_price(sym, price or last_prices.get(sym))}\n"
    msg += f"━━━━━━━━━━━━━━\n🤖 @{BOT_USERNAME}"
    bot.send_message(uid, msg, parse_mode="Markdown")


@bot.callback_query_handler(func=lambda c: c.data == "alerts_track")
def cb_alerts_track(call):
    uid = call.from_user.id
    bot.answer_callback_query(call.id)
    data = tracked_assets.get(str(uid), {})
    assets = data.get("assets", [])
    if not assets:
        bot.send_message(uid, "❌ قائمة التتبع فارغة. أضف رموزاً بـ /addtrack")
        return
    markup = types.InlineKeyboardMarkup(row_width=3)
    buttons = [types.InlineKeyboardButton(sym, callback_data=f"alert_asset_{sym}") for sym in assets]
    markup.add(*buttons)
    bot.send_message(uid, "📌 اختر الرمز الذي تريد متابعة سعره:", reply_markup=markup)


@bot.callback_query_handler(func=lambda c: c.data.startswith("alert_asset_"))
def cb_alert_asset(call):
    uid = call.from_user.id
    symbol = call.data.replace("alert_asset_", "")
    bot.answer_callback_query(call.id)
    price = fetch_asset_price(symbol)
    if price:
        markup = types.InlineKeyboardMarkup(row_width=2)
        pct_1_up = price * 1.01
        pct_1_dn = price * 0.99
        pct_5_up = price * 1.05
        pct_5_dn = price * 0.95
        markup.add(
            types.InlineKeyboardButton(f"🔼 +1% (${pct_1_up:,.4f})", callback_data=f"alert_set_{symbol}_{pct_1_up:.6f}"),
            types.InlineKeyboardButton(f"🔽 -1% (${pct_1_dn:,.4f})", callback_data=f"alert_set_{symbol}_{pct_1_dn:.6f}"),
            types.InlineKeyboardButton(f"🔼 +5% (${pct_5_up:,.4f})", callback_data=f"alert_set_{symbol}_{pct_5_up:.6f}"),
            types.InlineKeyboardButton(f"🔽 -5% (${pct_5_dn:,.4f})", callback_data=f"alert_set_{symbol}_{pct_5_dn:.6f}"),
        )
        bot.send_message(uid,
            f"💰 *{symbol}* — السعر الحالي: `${price:,.4f}`\n\nاختر مستوى التنبيه:",
            parse_mode="Markdown", reply_markup=markup
        )
    else:
        bot.send_message(uid, f"⚠️ لم أتمكن من جلب سعر {symbol} الآن.")


@bot.callback_query_handler(func=lambda c: c.data.startswith("alert_set_"))
def cb_alert_set(call):
    uid = call.from_user.id
    bot.answer_callback_query(call.id, "✅ تم ضبط التنبيه!")
    parts = call.data.split("_")
    symbol = parts[2]
    target = float(parts[3])
    if str(uid) not in users:
        return
    alerts_list = users[str(uid)].setdefault("price_alerts", [])
    alerts_list.append({"symbol": symbol, "target": target, "notified": False})
    _db_save_user(uid, users[str(uid)])
    bot.send_message(uid,
        f"✅ سيتم تنبيهك عندما يصل *{symbol}* إلى `${target:,.4f}`\n\n"
        f"💡 استخدم /alerts لإدارة التنبيهات.",
        parse_mode="Markdown"
    )


@bot.message_handler(commands=["mystats"])
def cmd_mystats(m):
    _show_mystats(m.from_user.id)


@bot.message_handler(commands=["weekly"])
def cmd_weekly(m):
    """يعرض الملخص الأسبوعي فوراً للمستخدم"""
    uid = m.from_user.id
    if uid in banned: return
    if bot_paused: return
    lang = users.get(str(uid), {}).get("lang", "العربية 🇮🇶")
    week_data = _weekly_top_news.get(lang, {})
    if not week_data:
        bot.send_message(uid,
            "📆 *الملخص الأسبوعي*\n\n"
            "لا توجد بيانات كافية بعد لهذا الأسبوع.\n"
            "يُرسل الملخص تلقائياً كل *جمعة الساعة 10:00 صباحاً*.",
            parse_mode="Markdown"
        )
        return
    top = sorted(week_data.values(), key=lambda x: x["count"], reverse=True)[:7]
    week_end   = datetime.date.today().strftime("%Y/%m/%d")
    week_start = (datetime.date.today() - datetime.timedelta(days=7)).strftime("%Y/%m/%d")
    lines = [f"{i}. [{item['title']}]({item['link']})" for i, item in enumerate(top, 1)]
    msg = (
        f"📆 *الملخص الأسبوعي*\n"
        f"🗓 {week_start} — {week_end}\n"
        f"━━━━━━━━━━━━━━\n\n"
        + "\n\n".join(lines) +
        "\n\n━━━━━━━━━━━━━━\n"
        "_أبرز ما غطّته مصادر متعددة هذا الأسبوع_"
    )
    bot.send_message(uid, msg, parse_mode="Markdown", disable_web_page_preview=True)


# ======== /analytics — لوحة تحليلات InsightX (أدمن فقط) ========
@bot.message_handler(commands=["compare"])
def cmd_compare(m):
    """
    /compare <موضوع أو جزء من عنوان الخبر>
    يبحث في RSS feeds ويُقارن كيف غطّت مصادر مختلفة نفس الموضوع.
    """
    uid = m.from_user.id
    if uid in banned: return
    if bot_paused: return
    if str(uid) not in users:
        bot.send_message(uid, "⚠️ أرسل /start أولاً.")
        return
    if _is_rate_limited(uid, "compare"):
        bot.send_message(uid, "⏳ انتظر لحظة قبل استخدام هذا الأمر مجدداً.")
        return

    user  = users.get(str(uid), {})
    lang  = user.get("lang", "العربية 🇮🇶")
    topic = m.text.strip()[len("/compare"):].strip()
    if not topic:
        bot.send_message(uid,
            "🔄 *مقارنة المصادر*\n\n"
            "أرسل: `/compare <موضوع>`\n\n"
            "مثال: `/compare حريق بغداد`\n"
            "_سأبحث عن هذا الموضوع في مصادر متعددة وأقارن كيف تم تغطيته_",
            parse_mode="Markdown")
        return

    wait_msg = bot.send_message(uid,
        f"🔄 *جاري البحث عن '{topic}' في مصادر متعددة...*", parse_mode="Markdown")

    def _do():
        feeds = RSS.get(lang, [])
        found = []
        for feed_url in feeds[:8]:
            try:
                feed = _parse_feed(feed_url)
                if feed is None:
                    import feedparser
                    feed = feedparser.parse(feed_url)
                if not feed:
                    continue
                for item in feed.entries[:10]:
                    title = getattr(item, 'title', '').strip()
                    link  = getattr(item, 'link', '')
                    if not title or not link:
                        continue
                    if any(w.lower() in title.lower() for w in topic.split() if len(w) > 2):
                        summ = getattr(item, 'summary', '') or getattr(item, 'description', '')
                        src  = get_source_name_from_url(feed_url)
                        found.append({"title": title, "source": src, "link": link, "summary": summ[:200]})
                        break
            except Exception:
                continue
            if len(found) >= 5:
                break

        if not found:
            try:
                bot.edit_message_text(
                    f"🔍 لم أجد أخباراً مطابقة لـ '*{topic}*' في المصادر المتاحة.",
                    uid, wait_msg.message_id, parse_mode="Markdown")
            except Exception as _exc:
                _log_exc(_exc)
            return

        # AI مقارنة المصادر
        sources_text = "\n".join(
            f"[{i+1}] {r['source']}: {r['title']}" for i, r in enumerate(found)
        )
        ai_analysis = ""
        if _AI_AVAILABLE and _AI_MODEL and len(found) > 1:
            try:
                lang_map = {"العربية 🇮🇶": "العربية", "English 🇬🇧": "English"}
                wlang = lang_map.get(lang, "Arabic")
                prompt = (
                    f"قارن كيف غطّت هذه المصادر الموضوع التالي: '{topic}'\n\n"
                    f"{sources_text}\n\n"
                    f"اكتب بـ 2-3 جمل باللغة {wlang}:\n"
                    "- أوجه الاتفاق بين المصادر\n"
                    "- أبرز الاختلافات في التأطير أو التفاصيل\n"
                    "ابدأ مباشرة."
                )
                _h_result = _ai_generate(prompt, timeout=8)
                ai_analysis = _h_result
            except Exception as _exc:
                _log_exc(_exc)

        sep = "━━━━━━━━━━━━━━"
        lines = [f"🔄 *مقارنة المصادر: {topic}*\n{sep}"]
        for i, r in enumerate(found):
            lines.append(f"\n*{i+1}. {r['source']}*\n_{r['title'][:80]}_\n[🔗 فتح]({r['link']})")
        if ai_analysis:
            lines.append(f"\n{sep}\n🤖 *تحليل المقارنة:*\n{ai_analysis}")
        lines.append(f"\n{sep}")
        reply = "\n".join(lines)
        try:
            bot.edit_message_text(reply, uid, wait_msg.message_id,
                                  parse_mode="Markdown", disable_web_page_preview=True)
        except Exception:
            try:
                bot.send_message(uid, reply, parse_mode="Markdown", disable_web_page_preview=True)
            except Exception as _exc:
                _log_exc(_exc)

    _AI_EXECUTOR.submit(_do)


# ======== /storyline — خط الأحداث التاريخي ========
@bot.callback_query_handler(func=lambda c: c.data.startswith("bm_"))
def cb_bookmark(call):
    try:
        uid     = call.from_user.id
        bm_key  = call.data[3:]
        cached  = _bm_key_cache.get(bm_key) or {}
        title   = cached.get("title", "")
        link    = cached.get("link", "")
        source  = cached.get("source", "")
        lang = (users.get(str(uid), {}) or {}).get("lang", "العربية 🇮🇶")
        if not title:
            bot.answer_callback_query(call.id, _ui("expired", lang), show_alert=True)
            return

        uid_str = str(uid)
        _bookmarks.setdefault(uid_str, [])
        if any(b.get("title") == title for b in _bookmarks[uid_str]):
            bot.answer_callback_query(call.id, _ui("bm_already", lang), show_alert=False)
            return
        if len(_bookmarks[uid_str]) >= 50:
            _bookmarks[uid_str].pop(0)
        _bookmarks[uid_str].append({"title": title, "link": link, "source": source, "ts": time.time()})
        _save_bookmarks()
        bot.answer_callback_query(call.id, _ui("bm_saved", lang), show_alert=False)
    except Exception:
        try:
            lang2 = (users.get(str(call.from_user.id), {}) or {}).get("lang", "العربية 🇮🇶")
            bot.answer_callback_query(call.id, _ui("bm_error", lang2), show_alert=True)
        except Exception as _exc:
            _log_exc(_exc)


@bot.message_handler(commands=["saved"])
def cmd_saved(m):
    uid = m.from_user.id
    if uid in banned: return
    if str(uid) not in users:
        bot.send_message(uid, "⚠️ أرسل /start أولاً."); return

    uid_str = str(uid)
    bms = _bookmarks.get(uid_str, [])
    if not bms:
        bot.send_message(uid,
            "🔖 *محفوظاتك فارغة*\n\n"
            "اضغط زر 🔖 على أي خبر لحفظه هنا.",
            parse_mode="Markdown"); return

    # تنظيف القديم (+7 أيام)
    cutoff = time.time() - 7 * 86400
    bms = [b for b in bms if b.get("ts", 0) > cutoff]
    _bookmarks[uid_str] = bms
    _save_bookmarks()

    sep   = "━━━━━━━━━━━━━━"
    lines = [f"🔖 *محفوظاتك ({len(bms)}):*\n{sep}"]
    markup = types.InlineKeyboardMarkup(row_width=1)
    for i, b in enumerate(bms[-20:]):
        date = datetime.datetime.fromtimestamp(b["ts"]).strftime("%d/%m %H:%M")
        lines.append(f"\n{i+1}. _{b['title'][:70]}_\n   📅 {date} | {b.get('source','')}")
        if b.get("link"):
            markup.add(types.InlineKeyboardButton(
                f"🔗 {i+1}. {b['title'][:30]}...", url=b["link"]))
    markup.add(types.InlineKeyboardButton("🗑 مسح كل المحفوظات", callback_data="bm_clear_all"))
    bot.send_message(uid, "\n".join(lines), parse_mode="Markdown", reply_markup=markup)


@bot.callback_query_handler(func=lambda c: c.data == "bm_clear_all")
def cb_bm_clear(call):
    uid = call.from_user.id
    _bookmarks[str(uid)] = []
    _save_bookmarks()
    bot.answer_callback_query(call.id, "✅ تم مسح المحفوظات.", show_alert=True)
    try:
        bot.delete_message(uid, call.message.message_id)
    except Exception as _exc:
        _log_exc(_exc)


# ── /quiz — اختبار الأخبار اليومي ────────────────────────────────────────
@bot.message_handler(commands=["quiz"])
def cmd_quiz(m):
    uid = m.from_user.id
    if uid in banned: return
    if str(uid) not in users:
        bot.send_message(uid, "⚠️ أرسل /start أولاً."); return
    if bot_paused: return

    user = users.get(str(uid), {})
    lang = user.get("lang", "العربية 🇮🇶")

    wait = bot.send_message(uid, "🧩 *جاري تجهيز سؤال اليوم...*", parse_mode="Markdown")

    def _do():
        feeds = RSS.get(lang, [])
        headlines = []
        for feed_url in feeds[:4]:
            try:
                import feedparser
                feed = feedparser.parse(feed_url)
                for item in feed.entries[:5]:
                    t = getattr(item, 'title', '').strip()
                    if t and _title_in_lang(t, lang):
                        headlines.append(t)
                if len(headlines) >= 6: break
            except Exception:
                continue

        question = answer = ""
        if headlines and _AI_AVAILABLE and _AI_MODEL:
            hl_txt = "\n".join(f"- {h}" for h in headlines[:5])
            prompt = (
                f"بناءً على هذه العناوين الإخبارية:\n{hl_txt}\n\n"
                "اصنع سؤالاً اختيارياً واحداً (4 خيارات) مع تحديد الجواب الصحيح.\n"
                "الصيغة:\n"
                "س: [السؤال]\n"
                "أ) [خيار]\nب) [خيار]\nج) [خيار]\nd) [خيار]\n"
                "الجواب: [الحرف]\n"
                f"اكتب باللغة {'العربية' if 'عرب' in lang else 'English'}."
            )
            raw = _ai_call_safe(prompt, timeout=10)
            if raw:
                question = raw
                for line in raw.split("\n"):
                    if line.strip().startswith("الجواب:") or line.strip().lower().startswith("answer:"):
                        answer = line.split(":", 1)[-1].strip()
                        break

        if not question:
            question = f"📰 ما أبرز حدث ورد في عناوين اليوم؟\n\n" + "\n".join(
                f"{'أبجد'[i]}) {h[:50]}" for i, h in enumerate(headlines[:4]))
            answer = "أ"

        uid_str = str(uid)
        _user_quiz[uid_str] = {
            "question": question,
            "answer":   answer,
            "answered": False,
            "score":    _user_quiz.get(uid_str, {}).get("score", 0),
            "date":     datetime.datetime.now().strftime("%Y-%m-%d"),
        }
        save_json(_QUIZ_FILE, _user_quiz)

        markup = types.InlineKeyboardMarkup(row_width=2)
        for ch in ["أ", "ب", "ج", "د"]:
            markup.add(types.InlineKeyboardButton(ch, callback_data=f"quiz_ans_{ch}"))

        try:
            bot.edit_message_text(
                f"🧩 *سؤال اليوم:*\n━━━━━━━━━━━━━━\n\n{question}\n\n"
                f"_🏆 نقاطك الكلية: {_user_quiz[uid_str]['score']}_",
                uid, wait.message_id, parse_mode="Markdown", reply_markup=markup)
        except Exception:
            bot.send_message(uid, f"🧩 *سؤال اليوم:*\n{question}", parse_mode="Markdown", reply_markup=markup)

    _AI_EXECUTOR.submit(_do)


@bot.callback_query_handler(func=lambda c: c.data.startswith("quiz_ans_"))
def cb_quiz_answer(call):
    uid     = call.from_user.id
    uid_str = str(uid)
    ans     = call.data[len("quiz_ans_"):]
    state   = _user_quiz.get(uid_str, {})

    if not state or state.get("answered"):
        bot.answer_callback_query(call.id, "✋ أجبت مسبقاً!", show_alert=False); return

    correct = state.get("answer", "").strip()
    is_right = ans.strip() == correct
    state["answered"] = True
    if is_right:
        state["score"] = state.get("score", 0) + 10
    _user_quiz[uid_str] = state
    save_json(_QUIZ_FILE, _user_quiz)

    if is_right:
        bot.answer_callback_query(call.id, "✅ إجابة صحيحة! +10 نقاط", show_alert=True)
    else:
        bot.answer_callback_query(call.id, f"❌ خطأ! الجواب الصحيح: {correct}", show_alert=True)

    try:
        new_text = call.message.text + f"\n\n{'✅ صحيح! +10 نقاط' if is_right else f'❌ الجواب: {correct}'}"
        bot.edit_message_text(new_text, uid, call.message.message_id, parse_mode="Markdown")
    except Exception as _exc:
        _log_exc(_exc)


# ── /sleep — وضع الصمت الذكي ─────────────────────────────────────────────
@bot.message_handler(commands=["sleep"])
def cmd_sleep(m):
    uid     = m.from_user.id
    if uid in banned: return
    uid_str = str(uid)
    current = _sleep_settings.get(uid_str, {"enabled": False, "start": 23, "end": 7})

    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton(
            "✅ مُفعَّل الآن — اضغط لإيقافه" if current["enabled"] else "⏸ موقوف — اضغط لتفعيله",
            callback_data="sleep_toggle"),
        types.InlineKeyboardButton("⏰ تغيير الساعات", callback_data="sleep_set_hours"),
    )
    status = f"من {current['start']}:00 حتى {current['end']}:00"
    bot.send_message(uid,
        f"😴 *وضع الصمت الذكي*\n━━━━━━━━━━━━━━\n\n"
        f"الحالة: {'✅ مُفعَّل' if current['enabled'] else '⏸ موقوف'}\n"
        f"ساعات الصمت: *{status}*\n\n"
        "_في أوقات الصمت لن تصلك أي إشعارات أخبار_",
        parse_mode="Markdown", reply_markup=markup)


@bot.callback_query_handler(func=lambda c: c.data == "sleep_toggle")
def cb_sleep_toggle(call):
    uid     = call.from_user.id
    uid_str = str(uid)
    current = _sleep_settings.get(uid_str, {"enabled": False, "start": 23, "end": 7})
    current["enabled"] = not current["enabled"]
    _sleep_settings[uid_str] = current
    _save_sleep()
    bot.answer_callback_query(call.id,
        f"{'😴 وضع الصمت مُفعَّل' if current['enabled'] else '🔔 وضع الصمت موقوف'}",
        show_alert=True)


@bot.callback_query_handler(func=lambda c: c.data == "sleep_set_hours")
def cb_sleep_set_hours(call):
    uid = call.from_user.id
    bot.answer_callback_query(call.id)
    bot.send_message(uid,
        "⏰ أرسل ساعة البداية والنهاية بالصيغة التالية:\n`23 7`\n\n"
        "_أي: ابدأ الصمت من الساعة 23 حتى 7 صباحاً_",
        parse_mode="Markdown")
    bot.register_next_step_handler_by_chat_id(uid, _save_sleep_hours)


@bot.message_handler(commands=["catchup"])
def cmd_catchup(m):
    uid = m.from_user.id
    if uid in banned: return
    if str(uid) not in users:
        bot.send_message(uid, "⚠️ أرسل /start أولاً."); return
    if bot_paused: return

    user = users.get(str(uid), {})
    lang = user.get("lang", "العربية 🇮🇶")
    last = _ts(user.get("last_active", 0))
    away_h = max(1, int((time.time() - last) / 3600)) if last else 6

    wait = bot.send_message(uid,
        f"⏩ *جاري تجهيز ما فاتك...*\n_كنت بعيداً ~{away_h} ساعة_",
        parse_mode="Markdown")

    def _do():
        feeds  = RSS.get(lang, [])
        since  = time.time() - max(away_h * 3600, 3600)
        items  = []
        import feedparser, email.utils
        for furl in feeds[:6]:
            try:
                fd = feedparser.parse(furl)
                for e in fd.entries[:8]:
                    t  = getattr(e, 'title', '').strip()
                    lk = getattr(e, 'link',  '').strip()
                    pub = getattr(e, 'published', '') or getattr(e, 'updated', '')
                    ts = 0
                    if pub:
                        try: ts = email.utils.parsedate_to_datetime(pub).timestamp()
                        except Exception:
                            try: ts = datetime.datetime.fromisoformat(pub).timestamp()
                            except: ts = time.time()
                    if ts >= since and t and lk:
                        items.append({"title": t, "link": lk, "ts": ts})
            except Exception:
                continue
            if len(items) >= 15: break

        # رتّب حسب الأحدث
        items.sort(key=lambda x: x["ts"], reverse=True)
        top = items[:8]

        if not top:
            try:
                bot.edit_message_text(
                    f"✅ لم تفتك أي أخبار مهمة في آخر {away_h} ساعة!",
                    uid, wait.message_id)
            except Exception: pass
            return

        # AI يلخّص
        summary = ""
        if _AI_AVAILABLE and _AI_MODEL and top:
            hl = "\n".join(f"- {i['title']}" for i in top[:6])
            lang_map = {"العربية 🇮🇶":"العربية","English 🇬🇧":"English"}
            prompt = (
                f"هذه أبرز أخبار آخر {away_h} ساعة:\n{hl}\n\n"
                f"اكتب ملخصاً سريعاً بـ3 جمل باللغة {lang_map.get(lang,'Arabic')} "
                "بأسلوب مختصر ومباشر كأنك تخبر صديقك بما فاته."
            )
            summary = _ai_call_safe(prompt, timeout=8)

        sep   = "━━━━━━━━━━━━━━"
        lines = [f"⏩ *ما فاتك في {away_h} ساعة ({len(top)} خبر):*\n{sep}"]
        markup = types.InlineKeyboardMarkup(row_width=1)
        for i, itm in enumerate(top):
            lines.append(f"\n{i+1}. _{itm['title'][:70]}_")
            markup.add(types.InlineKeyboardButton(
                f"🔗 {i+1}. {itm['title'][:35]}...", url=itm["link"]))
        if summary:
            lines.append(f"\n{sep}\n🤖 *الملخص الذكي:*\n{summary}")

        try:
            bot.edit_message_text("\n".join(lines), uid, wait.message_id,
                                  parse_mode="Markdown", reply_markup=markup,
                                  disable_web_page_preview=True)
        except Exception:
            bot.send_message(uid, "\n".join(lines), parse_mode="Markdown",
                             reply_markup=markup, disable_web_page_preview=True)

    _AI_EXECUTOR.submit(_do)


# ── 👍👎 News Voting ───────────────────────────────────────────────────────
@bot.message_handler(commands=["deepdive"])
def cmd_deepdive(m):
    uid = m.from_user.id
    if uid in banned: return
    if str(uid) not in users:
        bot.send_message(uid, "⚠️ أرسل /start أولاً."); return

    user = users.get(str(uid), {})
    lang = user.get("lang", "العربية 🇮🇶")

    if not _check_and_consume_feature(uid, "deepdive"):
        bot.send_message(uid, _get_limit_msg(lang, "deepdive")); return

    topic = m.text.strip()[len("/deepdive"):].strip()
    if not topic:
        bot.send_message(uid,
            "🔬 *التحليل العميق*\n\n"
            "أرسل: `/deepdive <موضوع>`\n\n"
            "مثال: `/deepdive الأزمة الاقتصادية في العراق`\n\n"
            "_سأكتب لك تقريراً شاملاً: خلفية تاريخية، وضع راهن، أطراف، توقعات_",
            parse_mode="Markdown"); return

    wait = bot.send_message(uid,
        f"🔬 *جاري كتابة تحليل عميق عن:*\n_{topic}_\n\n_هذا قد يستغرق 15-20 ثانية..._",
        parse_mode="Markdown")

    def _do():
        lang_map = {"العربية 🇮🇶": "العربية", "English 🇬🇧": "English"}
        wlang = lang_map.get(lang, "Arabic")
        prompt = (
            f"اكتب تقريراً صحفياً تحليلياً شاملاً بـ 500-700 كلمة باللغة {wlang} "
            f"حول موضوع: '{topic}'\n\n"
            "هيكل التقرير:\n"
            "1. المقدمة والسياق\n"
            "2. الخلفية التاريخية\n"
            "3. الوضع الراهن والأحداث الأخيرة\n"
            "4. الأطراف المعنية ومواقفهم\n"
            "5. التداعيات والتأثيرات\n"
            "6. التوقعات المستقبلية\n\n"
            "اكتب بأسلوب احترافي ومحايد. ابدأ مباشرة."
        )
        result = _ai_call_safe(prompt, timeout=20)
        if not result:
            result = f"⚠️ لم أتمكن من إنشاء التحليل حالياً. حاول لاحقاً."

        sep   = "━━━━━━━━━━━━━━"
        reply = f"🔬 *تحليل عميق: {topic}*\n{sep}\n\n{result}\n\n{sep}\n_بقلم: IraqNow AI_"

        # إرسال كرسالة طويلة (يُقسَّم إن تجاوز 4096)
        chunks = [reply[i:i+4000] for i in range(0, len(reply), 4000)]
        try:
            bot.edit_message_text(chunks[0], uid, wait.message_id, parse_mode="Markdown")
            for chunk in chunks[1:]:
                bot.send_message(uid, chunk, parse_mode="Markdown")
        except Exception:
            for chunk in chunks:
                try: bot.send_message(uid, chunk, parse_mode="Markdown")
                except: pass

    _AI_EXECUTOR.submit(_do)


# ── /addrss /myrss /delrss — مصادر مخصصة (مميز) ──────────────────────────
@bot.message_handler(commands=["track"])
def cmd_track(m):
    uid = m.from_user.id
    if uid in banned: return
    user = users.get(str(uid), {})
    lang = user.get("lang", "العربية 🇮🇶")

    if not _check_and_consume_feature(uid, "entity_track"):
        bot.send_message(uid, _get_limit_msg(lang, "entity_track")); return

    entity = m.text.strip()[len("/track"):].strip()
    if not entity:
        bot.send_message(uid,
            "📡 *تتبع شخص أو شركة أو موضوع*\n\n"
            "أرسل: `/track <الاسم>`\n\n"
            "مثال: `/track البنك المركزي العراقي`\n"
            "_كلما ظهر هذا الاسم في أي خبر ستصلك رسالة فورية_",
            parse_mode="Markdown"); return

    uid_str = str(uid)
    _entity_tracks.setdefault(uid_str, [])
    if len(_entity_tracks[uid_str]) >= 10:
        bot.send_message(uid, "⚠️ وصلت للحد الأقصى (10 كيانات). احذف بعضها بـ /untrack"); return
    if any(e["entity"].lower() == entity.lower() for e in _entity_tracks[uid_str]):
        bot.send_message(uid, f"⚠️ تتبع *{entity}* موجود مسبقاً.", parse_mode="Markdown"); return

    _entity_tracks[uid_str].append({"entity": entity, "added_ts": time.time()})
    _save_tracks()
    bot.send_message(uid,
        f"✅ *تم تفعيل التتبع:* _{entity}_\n\n"
        "سأُرسل لك تنبيهاً فورياً في كل مرة يُذكر فيها.",
        parse_mode="Markdown")


@bot.message_handler(commands=["mytracks"])
def cmd_mytracks(m):
    uid     = m.from_user.id
    uid_str = str(uid)
    tracks  = _entity_tracks.get(uid_str, [])
    if not tracks:
        bot.send_message(uid,
            "📡 لا تتبع أي كيان حالياً.\nابدأ بـ `/track <الاسم>`",
            parse_mode="Markdown"); return

    markup = types.InlineKeyboardMarkup(row_width=1)
    lines  = [f"📡 *قائمة تتبعاتك ({len(tracks)}):*\n━━━━━━━━━━━━━━"]
    for i, e in enumerate(tracks):
        lines.append(f"\n{i+1}. *{e['entity']}*")
        markup.add(types.InlineKeyboardButton(
            f"🗑 إيقاف تتبع: {e['entity'][:30]}", callback_data=f"untrack_{i}"))
    bot.send_message(uid, "\n".join(lines), parse_mode="Markdown", reply_markup=markup)


@bot.message_handler(commands=["untrack"])
def cmd_untrack(m):
    uid = m.from_user.id
    entity = m.text.strip()[len("/untrack"):].strip()
    if not entity:
        bot.send_message(uid, "أرسل /mytracks لعرض قائمة تتبعاتك والحذف منها."); return
    uid_str = str(uid)
    before  = len(_entity_tracks.get(uid_str, []))
    _entity_tracks[uid_str] = [e for e in _entity_tracks.get(uid_str, [])
                                if e["entity"].lower() != entity.lower()]
    _save_tracks()
    if len(_entity_tracks.get(uid_str, [])) < before:
        bot.send_message(uid, f"✅ تم إيقاف تتبع *{entity}*", parse_mode="Markdown")
    else:
        bot.send_message(uid, f"⚠️ لم أجد *{entity}* في قائمتك.", parse_mode="Markdown")


@bot.callback_query_handler(func=lambda c: c.data.startswith("untrack_"))
def cb_untrack(call):
    uid     = call.from_user.id
    uid_str = str(uid)
    try:
        idx = int(call.data[len("untrack_"):])
        tracks = _entity_tracks.get(uid_str, [])
        if 0 <= idx < len(tracks):
            removed = tracks.pop(idx)
            _save_tracks()
            bot.answer_callback_query(call.id,
                f"✅ إيقاف تتبع: {removed['entity']}", show_alert=True)
            try: bot.delete_message(uid, call.message.message_id)
            except: pass
        else:
            bot.answer_callback_query(call.id, "⚠️ غير موجود.")
    except Exception:
        bot.answer_callback_query(call.id, "⚠️ خطأ.")


# ── /crosslang — مقارنة متعددة اللغات ────────────────────────────────────
@bot.message_handler(commands=["crosslang"])
def cmd_crosslang(m):
    uid = m.from_user.id
    if uid in banned: return
    user = users.get(str(uid), {})
    lang = user.get("lang", "العربية 🇮🇶")

    if not _check_and_consume_feature(uid, "cross_lang"):
        bot.send_message(uid, _get_limit_msg(lang, "cross_lang")); return

    topic = m.text.strip()[len("/crosslang"):].strip()
    if not topic:
        bot.send_message(uid,
            "🌍 *مقارنة متعددة اللغات*\n\n"
            "أرسل: `/crosslang <موضوع>`\n\n"
            "مثال: `/crosslang Iraq oil exports`\n\n"
            "_سأجمع تغطية مصادر عربية وإنجليزية لنفس الحدث وأقارن الرواية_",
            parse_mode="Markdown"); return

    wait = bot.send_message(uid,
        f"🌍 *جاري تجميع تغطيات متعددة اللغات لـ:* _{topic}_",
        parse_mode="Markdown")

    def _do():
        import feedparser
        results = {}
        for check_lang in ["العربية 🇮🇶", "English 🇬🇧"]:
            feeds = RSS.get(check_lang, [])
            found = []
            for furl in feeds[:5]:
                try:
                    fd = feedparser.parse(furl)
                    for e in fd.entries[:8]:
                        t = getattr(e, 'title', '').strip()
                        lk = getattr(e, 'link', '').strip()
                        if t and lk and any(w.lower() in t.lower()
                                            for w in topic.split() if len(w) > 2):
                            src = get_source_name_from_url(furl) if 'get_source_name_from_url' in dir() else furl[:20]
                            cred = _get_credibility(src)
                            badge = _credibility_badge(cred)
                            found.append({"title": t, "src": src, "link": lk,
                                          "cred": cred, "badge": badge})
                            break
                except Exception:
                    continue
                if len(found) >= 3: break
            if found:
                results[check_lang] = found

        if not results:
            try:
                bot.edit_message_text(
                    f"🔍 لم أجد تغطية لـ *{topic}* في المصادر المتاحة.",
                    uid, wait.message_id, parse_mode="Markdown")
            except Exception: pass
            return

        # AI يحلّل الفروقات
        all_titles = []
        for lng, items in results.items():
            for it in items:
                all_titles.append(f"[{lng.split()[0]}] {it['src']}: {it['title']}")

        ai_text = ""
        if len(all_titles) >= 2:
            prompt = (
                f"قارن كيف يُغطّي الإعلام العربي والإنجليزي موضوع '{topic}':\n\n"
                + "\n".join(all_titles) + "\n\n"
                "اكتب بـ 3 جمل بالعربية:\n"
                "- أوجه التشابه\n"
                "- الاختلاف في الإطار أو التركيز\n"
                "- أي رواية تبدو أكثر شمولاً ولماذا"
            )
            ai_text = _ai_call_safe(prompt, timeout=10)

        sep   = "━━━━━━━━━━━━━━"
        lines = [f"🌍 *مقارنة متعددة اللغات: {topic}*\n{sep}"]
        markup = types.InlineKeyboardMarkup(row_width=1)
        for lng, items in results.items():
            flag = lng.split()[-1] if lang else ""
            lines.append(f"\n{flag} *{lng.split()[0]}:*")
            for it in items:
                lines.append(f"  {it['badge']} _{it['title'][:70]}_\n  [{it['src']}] — موثوقية: {it['cred']}%")
                markup.add(types.InlineKeyboardButton(
                    f"🔗 {it['src']}: {it['title'][:30]}...", url=it["link"]))
        if ai_text:
            lines.append(f"\n{sep}\n🤖 *تحليل المقارنة:*\n{ai_text}")
        lines.append(f"\n{sep}")

        try:
            bot.edit_message_text("\n".join(lines), uid, wait.message_id,
                                  parse_mode="Markdown", reply_markup=markup,
                                  disable_web_page_preview=True)
        except Exception:
            bot.send_message(uid, "\n".join(lines), parse_mode="Markdown",
                             reply_markup=markup, disable_web_page_preview=True)

    _AI_EXECUTOR.submit(_do)


# ─────────────────────────────────────────────────────────────────────────
# §7  AI INTELLIGENCE AUTO-FEATURES — كشف أوتوماتيكي
# ─────────────────────────────────────────────────────────────────────────

# ── Narrative Arc — /narratives ──────────────────────────────────────────
@bot.message_handler(commands=["narratives"])
def cmd_narratives(m):
    """يعرض أبرز القصص الحية المتعددة الأحداث."""
    uid = m.from_user.id
    if uid in banned: return
    if str(uid) not in users:
        bot.send_message(uid, "⚠️ أرسل /start أولاً."); return

    # أبرز المواضيع (أكثر من حدثين)
    multi = [(k, v) for k, v in _narrative_store.items() if len(v) >= 2]
    multi.sort(key=lambda x: x[1][-1]["ts"], reverse=True)
    top   = multi[:8]

    if not top:
        bot.send_message(uid,
            "🗓 *الأحداث المتطورة*\n\n"
            "_لم تتراكم أخبار كافية بعد. عُد لاحقاً._",
            parse_mode="Markdown"); return

    sep   = "━━━━━━━━━━━━━━"
    lines = [f"🗓 *الأحداث الحية والمتطورة*\n{sep}"]
    markup = types.InlineKeyboardMarkup(row_width=1)
    for i, (k, events) in enumerate(top):
        first = events[0]["title"][:50]
        count = len(events)
        last_ts = datetime.datetime.fromtimestamp(events[-1]["ts"]).strftime("%d/%m %H:%M")
        lines.append(f"\n*{i+1}.* _{first}..._\n   📅 {count} أحداث | آخر تحديث: {last_ts}")
        markup.add(types.InlineKeyboardButton(
            f"📖 {i+1}. تفاصيل القصة", callback_data=f"narr_{k}"))
    bot.send_message(uid, "\n".join(lines), parse_mode="Markdown", reply_markup=markup)


@bot.callback_query_handler(func=lambda c: c.data.startswith("narr_"))
def cb_narrative(call):
    uid = call.from_user.id
    key = call.data[5:]
    events = _narrative_store.get(key, [])
    if not events:
        bot.answer_callback_query(call.id, "⚠️ القصة غير موجودة."); return
    bot.answer_callback_query(call.id)

    sep   = "━━━━━━━━━━━━━━"
    lines = [f"🗓 *خط الأحداث:*\n{sep}"]
    for e in events:
        dt = datetime.datetime.fromtimestamp(e["ts"]).strftime("%d/%m %H:%M")
        lines.append(f"\n📍 `{dt}` — _{e['title'][:70]}_\n   _📰 {e['source']}_")
    lines.append(f"\n{sep}\n_إجمالي الأحداث: {len(events)}_")
    bot.send_message(uid, "\n".join(lines), parse_mode="Markdown")


# ── Predictive Signal — تنبيه إشارات التطور ──────────────────────────────
_predictive_counts: dict = {}    # {word: count_last_hour}
_predictive_last_reset: float = time.time()
_PREDICTIVE_THRESHOLD = 5        # إذا ظهر موضوع +5 مرات في ساعة → تنبيه
