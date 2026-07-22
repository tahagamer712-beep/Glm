# -*- coding: utf-8 -*-
"""
  handler_settings.py — إعدادات المستخدم + لغة + تنبيهات

  يُصدِّر معالجات أوامر الإعدادات.
  """

import sys as _sys_legacy
import os
# ─── استيراد كل المتغيرات العالمية من bot_legacy ───
from bot_legacy import *
import state as gl  # noqa: F401,F403

def handle_pause_news(call):
    uid = call.from_user.id
    data = call.data
    bot.answer_callback_query(call.id)
    try:
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
    except Exception as _exc:
        _log_exc(_exc)
    user = users.get(str(uid), {})
    lang = user.get("lang", "العربية 🇮🇶")
    if data == "pause_news_cancel":
        bot.send_message(uid, "↩️ تم الإلغاء، الأخبار لا تزال مفعّلة.")
    elif data == "pause_news_off":
        users[str(uid)]["notifications"] = False
        users[str(uid)].pop("news_paused_until", None)
        _db_save_user(str(uid), users[str(uid)])
        bot.send_message(uid, "❌ تم إيقاف الأخبار نهائياً.\nاضغط زر الإشعارات لإعادة التفعيل.")
        send_main_menu(uid)
    else:
        hours_map = {"pause_news_1h": 1, "pause_news_6h": 6, "pause_news_24h": 24}
        hours = hours_map.get(data, 1)
        # نستخدم _now_sa() لضمان التطابق مع المقارنة في broadcast_news
        paused_until = (_now_sa() + datetime.timedelta(hours=hours)).isoformat()
        users[str(uid)]["news_paused_until"] = paused_until
        _db_save_user(str(uid), users[str(uid)])
        label = f"{hours} ساعة" if hours == 1 else f"{hours} ساعات" if hours < 24 else "يوم كامل"
        bot.send_message(uid, f"⏸ تم إيقاف الأخبار لمدة *{label}*.\nستعود تلقائياً بعد انتهاء المدة.", parse_mode="Markdown")

# ======== خطوات إدارة الأدمن ========
def send_interest_menu(uid):
    user = users.get(str(uid)) or {}
    lang = user.get("lang", "العربية 🇮🇶")
    options = INTERESTS.get(lang, INTERESTS["English 🇬🇧"])
    current = user.get("interests", [])
    markup = types.InlineKeyboardMarkup(row_width=2)
    for opt in options:
        check = "✅ " if opt in current else ""
        markup.add(types.InlineKeyboardButton(f"{check}{opt}", callback_data=f"interest_{opt}"))
    markup.add(types.InlineKeyboardButton("💾 حفظ", callback_data="interest_save"))
    bot.send_message(uid, "📌 *اختر اهتماماتك (يمكن أكثر من واحد):*", parse_mode="Markdown", reply_markup=markup)

def set_currency_alert_step(message):
    uid = message.from_user.id
    try:
        rate = float(message.text.strip())
        users[str(uid)]["currency_alert"] = rate
        _db_save_all_users(users)
        bot.send_message(uid, f"✅ سيتم تنبيهك عند وصول الدولار إلى `{rate}` من عملتك المحلية.", parse_mode="Markdown")
    except Exception:
        bot.send_message(uid, "❌ أرسل رقماً صحيحاً مثل: 1600")

def set_notif_time_step(message):
    uid = message.from_user.id
    try:
        hour = int(message.text.strip())
        if not (0 <= hour <= 23):
            raise ValueError
        users[str(uid)]["notif_hour"] = hour
        _db_save_all_users(users)
        bot.send_message(uid, f"✅ سيتم إرسال الملخص الصباحي في الساعة *{hour}:00* يومياً.", parse_mode="Markdown")
    except Exception:
        bot.send_message(uid, "❌ أرسل رقماً بين 0 و 23 (مثال: 8 للساعة 8 صباحاً)")

def cb_menu_settings(call):
    bot.answer_callback_query(call.id)
    uid = call.from_user.id
    user = users.get(str(uid))
    if not user:
        welcome_user(uid)
        return
    class _FakeMsg:
        from_user = type("U", (), {"id": uid})()
        chat = type("C", (), {"id": uid, "type": "private"})()
    cmd_settings_private(_FakeMsg())

@bot.callback_query_handler(func=lambda c: c.data == "menu_help")
def cmd_setlang(message):
    chat_id = message.chat.id
    user_id = message.from_user.id if message.from_user else None
    if not user_id or not is_chat_admin(chat_id, user_id):
        return
    args = message.text.strip().replace("/setlang", "").strip()
    matched_lang = None
    for lang in VALID_LANGS:
        if lang.lower().startswith(args.lower()) or args.lower() in lang.lower():
            matched_lang = lang
            break
    if not matched_lang:
        bot.send_message(chat_id,
            "❌ *لغة غير صحيحة.*\n\n"
            "اللغات المتاحة:\n"
            "• `العربية 🇮🇶`\n"
            "• `English 🇬🇧`\n"
            "• `فارسی 🇮🇷`\n"
            "• `Türkçe 🇹🇷`\n\n"
            "مثال: `/setlang العربية 🇮🇶`",
            parse_mode="Markdown"
        )
        return
    found = False
    for ch in channels_groups:
        if ch["id"] == chat_id:
            ch["lang"] = matched_lang
            ch["sent_news"] = []
            found = True
            break
    if not found:
        channels_groups.append({
            "id": chat_id,
            "title": message.chat.title or str(chat_id),
            "type": message.chat.type,
            "lang": matched_lang,
            "city": "",
            "sent_news": {}
        })
    save_channels_groups()
    bot.send_message(chat_id,
        f"✅ *تم تغيير لغة الأخبار إلى:* {matched_lang}\n"
        f"📰 سيبدأ إرسال الأخبار باللغة الجديدة في البث القادم.",
        parse_mode="Markdown"
    )

@bot.message_handler(commands=["setcity"], chat_types=["channel", "group", "supergroup"])
def cmd_setcity(message):
    chat_id = message.chat.id
    user_id = message.from_user.id if message.from_user else None
    if not user_id or not is_chat_admin(chat_id, user_id):
        return
    city = message.text.strip().replace("/setcity", "").strip()
    if not city:
        bot.send_message(chat_id,
            "❌ *أرسل اسم المدينة.*\n\nمثال: `/setcity بغداد`",
            parse_mode="Markdown"
        )
        return
    found = False
    for ch in channels_groups:
        if ch["id"] == chat_id:
            ch["city"] = city
            found = True
            break
    if not found:
        channels_groups.append({
            "id": chat_id,
            "title": message.chat.title or str(chat_id),
            "type": message.chat.type,
            "lang": "العربية 🇮🇶",
            "city": city,
            "sent_news": {}
        })
    save_channels_groups()
    bot.send_message(chat_id,
        f"✅ *تم تعيين المدينة إلى:* {city}",
        parse_mode="Markdown"
    )

@bot.message_handler(commands=["settings"], chat_types=["channel", "group", "supergroup"])
def cmd_settings(message):
    chat_id = message.chat.id
    user_id = message.from_user.id if message.from_user else None
    if not user_id or not is_chat_admin(chat_id, user_id):
        return
    ch_data = next((ch for ch in channels_groups if ch["id"] == chat_id), None)
    if not ch_data:
        bot.send_message(chat_id,
            "⚠️ هذه القناة/المجموعة غير مسجلة في البوت بعد.\n"
            "أضف البوت كأدمن وسيبدأ تلقائياً.",
            parse_mode="Markdown"
        )
        return
    lang = ch_data.get("lang", "العربية 🇮🇶")
    city = ch_data.get("city", "") or "غير محددة"
    chat_type = ch_data.get("type", "")
    type_label = "📢 قناة" if chat_type == "channel" else "👥 مجموعة"
    bot.send_message(chat_id,
        f"⚙️ *إعدادات هذه {type_label}:*\n\n"
        f"🌐 اللغة: *{lang}*\n"
        f"🏙 المدينة: *{city}*\n\n"
        f"🔧 لتغيير اللغة: `/setlang اسم اللغة`\n"
        f"🔧 لتغيير المدينة: `/setcity اسم المدينة`",
        parse_mode="Markdown"
    )

# ======== أوامر المصادر المخصصة لأدمن القناة/المجموعة ========
@bot.message_handler(commands=["setsource"], chat_types=["channel", "group", "supergroup"])
def cmd_setsource(message):
    chat_id = message.chat.id
    user_id = message.from_user.id if message.from_user else None
    if not user_id or not is_chat_admin(chat_id, user_id):
        return
    url = message.text.strip().replace("/setsource", "").strip()
    if not url.startswith("http"):
        bot.send_message(chat_id, "❌ أرسل رابط RSS صحيح يبدأ بـ http\nمثال: `/setsource https://feeds.bbcarabic.com/world-arabic-rss.xml`", parse_mode="Markdown")
        return
    ch_data = next((ch for ch in channels_groups if ch["id"] == chat_id), None)
    if not ch_data:
        channels_groups.append({"id": chat_id, "title": message.chat.title or str(chat_id),
                                 "type": message.chat.type, "lang": "العربية 🇮🇶",
                                 "custom_sources": [url], "sent_news": {}})
    else:
        sources = ch_data.setdefault("custom_sources", [])
        if url in sources:
            bot.send_message(chat_id, "⚠️ هذا المصدر مضاف مسبقاً.")
            return
        sources.append(url)
    save_channels_groups()
    bot.send_message(chat_id, f"✅ *تمت إضافة المصدر:*\n`{url}`", parse_mode="Markdown")

@bot.message_handler(commands=["removesource"], chat_types=["channel", "group", "supergroup"])
def cmd_removesource(message):
    chat_id = message.chat.id
    user_id = message.from_user.id if message.from_user else None
    if not user_id or not is_chat_admin(chat_id, user_id):
        return
    url = message.text.strip().replace("/removesource", "").strip()
    ch_data = next((ch for ch in channels_groups if ch["id"] == chat_id), None)
    if not ch_data or url not in ch_data.get("custom_sources", []):
        bot.send_message(chat_id, "⚠️ المصدر غير موجود.")
        return
    ch_data["custom_sources"].remove(url)
    save_channels_groups()
    bot.send_message(chat_id, f"✅ تم حذف المصدر:\n`{url}`", parse_mode="Markdown")

@bot.message_handler(commands=["listsources"], chat_types=["channel", "group", "supergroup"])
def cmd_listsources(message):
    chat_id = message.chat.id
    user_id = message.from_user.id if message.from_user else None
    if not user_id or not is_chat_admin(chat_id, user_id):
        return
    ch_data = next((ch for ch in channels_groups if ch["id"] == chat_id), None)
    sources = ch_data.get("custom_sources", []) if ch_data else []
    if not sources:
        bot.send_message(chat_id,
            "📋 لا توجد مصادر مخصصة.\n"
            "يستخدم البوت المصادر الافتراضية حسب اللغة.\n"
            "أضف مصدراً: `/setsource رابط_RSS`",
            parse_mode="Markdown"
        )
        return
    msg = "📋 *مصادر الأخبار المخصصة:*\n\n"
    for i, src in enumerate(sources, 1):
        msg += f"{i}. `{src}`\n"
    bot.send_message(chat_id, msg, parse_mode="Markdown")

@bot.message_handler(commands=["pause"], chat_types=["channel", "group", "supergroup"])
def cmd_pause(message):
    chat_id = message.chat.id
    user_id = message.from_user.id if message.from_user else None
    if not user_id or not is_chat_admin(chat_id, user_id):
        return
    ch_data = next((ch for ch in channels_groups if ch["id"] == chat_id), None)
    if not ch_data:
        bot.send_message(chat_id, "⚠️ هذه القناة/المجموعة غير مسجلة.")
        return
    ch_data["paused"] = True
    save_channels_groups()
    bot.send_message(chat_id, "⏸ *تم إيقاف البث مؤقتاً.*\nاستخدم `/resume` للاستئناف.", parse_mode="Markdown")

@bot.message_handler(commands=["resume"], chat_types=["channel", "group", "supergroup"])
def cmd_resume(message):
    chat_id = message.chat.id
    user_id = message.from_user.id if message.from_user else None
    if not user_id or not is_chat_admin(chat_id, user_id):
        return
    ch_data = next((ch for ch in channels_groups if ch["id"] == chat_id), None)
    if not ch_data:
        bot.send_message(chat_id, "⚠️ هذه القناة/المجموعة غير مسجلة.")
        return
    ch_data["paused"] = False
    save_channels_groups()
    bot.send_message(chat_id, "▶️ *تم استئناف البث.*\nستصلك الأخبار تلقائياً قريباً.", parse_mode="Markdown")

# ======== تقرير يومي للأدمن ========
def cmd_settings_private(m):
    if m.chat.type != "private":
        return
    uid = m.from_user.id
    user = users.get(str(uid))
    if not user:
        bot.send_message(uid, "⚠️ أرسل /start أولاً.")
        return
    lang = user.get("lang", "English 🇬🇧")
    markup = types.InlineKeyboardMarkup(row_width=2)
    alert_lv  = user.get("alert_level", "all")
    alert_labels = {"all": "🔔 كل الأخبار", "important": "⚡ المهمة فقط", "breaking": "🚨 العاجلة فقط"}
    digest_on = user.get("digest_mode", False)
    custom_hours = user.get("custom_schedule", [])
    sched_txt = ", ".join(f"{h}:00" for h in sorted(custom_hours)) if custom_hours else "طوال اليوم ✅"
    markup.add(
        types.InlineKeyboardButton("🌍 تغيير اللغة",    callback_data="settings_lang"),
        types.InlineKeyboardButton("🌆 تغيير المدينة",  callback_data="settings_city"),
        types.InlineKeyboardButton("🔔 الإشعارات",       callback_data="settings_notif"),
        types.InlineKeyboardButton("📌 الاهتمامات",      callback_data="prem_interests"),
    )
    markup.add(
        types.InlineKeyboardButton(
            f"📡 التنبيه: {alert_labels.get(alert_lv, alert_lv)}",
            callback_data="settings_alert_level"
        ),
        types.InlineKeyboardButton(
            f"{'📰' if digest_on else '📄'} الدايجست: {'رسالة واحدة ✅' if digest_on else 'فردية'}",
            callback_data="settings_digest_toggle"
        ),
    )
    markup.add(
        types.InlineKeyboardButton(
            f"🕐 جدول الاستلام: {sched_txt}",
            callback_data="settings_schedule"
        ),
        types.InlineKeyboardButton("📊 إحصائياتي", callback_data="settings_mystats"),
    )
    notif_status = "✅ مفعّلة" if user.get("notifications", True) else "❌ موقوفة"
    city = user.get("province", "—")
    msg = (
        f"⚙️ *إعداداتك الحالية*\n━━━━━━━━━━━━━━━\n"
        f"🌍 اللغة: `{lang}`\n"
        f"🌆 المدينة: `{city}`\n"
        f"🔔 الإشعارات: {notif_status}\n"
        f"📰 الأخبار: *24/7 بلا توقف* 🟢\n"
        f"📡 مستوى التنبيه: {alert_labels.get(alert_lv, alert_lv)}\n"
        f"{'📰' if digest_on else '📄'} الدايجست: {'✅ رسالة واحدة' if digest_on else 'رسائل فردية'}\n"
        f"🕐 جدول الاستلام: {sched_txt}\n"
        f"━━━━━━━━━━━━━━━\n"
        f"اختر ما تريد تعديله:"
    )
    bot.send_message(uid, msg, parse_mode="Markdown", reply_markup=markup)


@bot.callback_query_handler(func=lambda c: c.data == "settings_lang")
def cb_settings_lang(call):
    bot.answer_callback_query(call.id)
    uid = call.from_user.id
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    for lang_name in languages.values():
        markup.add(lang_name)
    bot.send_message(uid, "🌍 اختر لغتك:", reply_markup=markup)


@bot.callback_query_handler(func=lambda c: c.data == "settings_city")
def cb_settings_city(call):
    bot.answer_callback_query(call.id)
    uid = call.from_user.id
    bot.send_message(uid, "🌆 أرسل اسم مدينتك بالإنجليزية (مثال: Baghdad, London, Tehran):")
    bot.register_next_step_handler(call.message, lambda m: _save_city_step(m, uid))


def _save_city_step(message, uid):
    city = message.text.strip()
    if str(uid) in users:
        users[str(uid)]["province"] = city
        _db_save_user(uid, users[str(uid)])
        bot.send_message(uid, f"✅ تم تحديث مدينتك إلى: *{city}*\n\nاستخدم /weather لعرض الطقس.", parse_mode="Markdown")


@bot.callback_query_handler(func=lambda c: c.data == "settings_notif")
def cb_settings_notif(call):
    bot.answer_callback_query(call.id)
    uid = call.from_user.id
    if str(uid) not in users:
        return
    current = users[str(uid)].get("notifications", True)
    users[str(uid)]["notifications"] = not current
    _db_save_user(uid, users[str(uid)])
    status = "✅ مفعّلة" if not current else "❌ موقوفة"
    bot.send_message(uid, f"🔔 الإشعارات الآن: {status}")


# ======== جدول استلام مخصص ========
@bot.callback_query_handler(func=lambda c: c.data == "settings_schedule")
def cb_settings_schedule(call):
    bot.answer_callback_query(call.id)
    uid = call.from_user.id
    current = users.get(str(uid), {}).get("custom_schedule", [])
    cur_txt = ", ".join(f"{h}:00" for h in sorted(current)) if current else "طوال اليوم (افتراضي)"
    msg = bot.send_message(uid,
        f"🕐 *جدول استلام الأخبار*\n\n"
        f"الجدول الحالي: `{cur_txt}`\n\n"
        "أرسل الساعات التي تريد استلام الأخبار فيها مفصولة بمسافات:\n"
        "`7 12 18 21` — ستصلك الأخبار الساعة 7ص، 12م، 6م، 9م\n\n"
        "أرسل `0` لإلغاء الجدول والعودة للاستلام الدائم 24/7.",
        parse_mode="Markdown"
    )
    bot.register_next_step_handler(msg, _save_schedule_step)


def _save_schedule_step(message):
    uid = message.from_user.id
    txt = message.text.strip()
    if txt == "0":
        users[str(uid)]["custom_schedule"] = []
        _db_save_user(uid, users[str(uid)])
        bot.send_message(uid, "✅ *تم إلغاء الجدول* — ستصلك الأخبار 24/7 باستمرار.", parse_mode="Markdown")
        return
    try:
        hours = [int(h) for h in txt.split() if 0 <= int(h) <= 23]
        if not hours:
            raise ValueError
        hours = sorted(set(hours))
        users[str(uid)]["custom_schedule"] = hours
        _db_save_user(uid, users[str(uid)])
        sched_txt = ", ".join(f"{h}:00" for h in hours)
        bot.send_message(uid,
            f"✅ *تم حفظ الجدول!*\n\nستصلك الأخبار الساعة: `{sched_txt}`",
            parse_mode="Markdown"
        )
    except Exception:
        bot.send_message(uid, "❌ تنسيق خاطئ. مثال: `7 12 18 21`\nأو أرسل `0` للإلغاء.", parse_mode="Markdown")


# ======== إحصائياتي الشخصية ========
@bot.callback_query_handler(func=lambda c: c.data == "settings_alert_level")
def cb_alert_level_menu(call):
    bot.answer_callback_query(call.id)
    uid = call.from_user.id
    current = users.get(str(uid), {}).get("alert_level", "all")
    markup = types.InlineKeyboardMarkup(row_width=1)
    options = [
        ("🔔 كل الأخبار (افتراضي)",        "nlevel_all"),
        ("⚡ المهمة والعاجلة فقط",           "nlevel_important"),
        ("🚨 العاجلة فقط (Breaking News)",   "nlevel_breaking"),
    ]
    for label, cb in options:
        check = "✅ " if cb.replace("nlevel_", "") == current else ""
        markup.add(types.InlineKeyboardButton(f"{check}{label}", callback_data=cb))
    bot.send_message(uid, "📡 *اختر مستوى الأخبار التي تريد استقبالها:*", parse_mode="Markdown", reply_markup=markup)


@bot.callback_query_handler(func=lambda c: c.data.startswith("nlevel_"))
def cb_news_level_set(call):
    bot.answer_callback_query(call.id)
    uid = call.from_user.id
    level = call.data.replace("nlevel_", "")
    if level not in ("all", "important", "breaking"):
        return
    users[str(uid)]["alert_level"] = level
    _db_save_user(uid, users[str(uid)])
    labels = {"all": "🔔 كل الأخبار", "important": "⚡ المهمة والعاجلة", "breaking": "🚨 العاجلة فقط"}
    bot.send_message(uid, f"✅ مستوى التنبيه: *{labels[level]}*", parse_mode="Markdown")


# ======== إعداد وضع الدايجست ========
@bot.callback_query_handler(func=lambda c: c.data == "settings_digest_toggle")
def cb_digest_toggle(call):
    bot.answer_callback_query(call.id)
    uid = call.from_user.id
    if str(uid) not in users:
        return
    current = users[str(uid)].get("digest_mode", False)
    users[str(uid)]["digest_mode"] = not current
    _db_save_user(uid, users[str(uid)])
    state = "✅ مفعّل — ستصلك الأخبار في رسالة واحدة منظّمة" if not current else "❌ معطّل — ستصلك الأخبار فرادى"
    bot.send_message(uid,
        f"📰 *وضع الدايجست الآن: {state}*\n\n"
        "_يمكنك التبديل في أي وقت من /settings_",
        parse_mode="Markdown"
    )


# ======== /referral — نظام الإحالة المنفصل ========
@bot.message_handler(commands=["digest"])
def cmd_digest(m):
    uid = m.from_user.id
    if uid in banned: return
    uid_str = str(uid)
    if uid_str not in users:
        bot.send_message(uid, "⚠️ أرسل /start أولاً."); return

    user     = users[uid_str]
    enabled  = user.get("digest_mode", False)
    cur_hour = user.get("notif_hour", 8)

    status_icon = "✅ مفعّل" if enabled else "❌ معطّل"
    msg = (
        f"🌅 *الملخص الصباحي*\n"
        f"━━━━━━━━━━━━━━\n\n"
        f"الحالة: {status_icon}\n"
        f"وقت الإرسال: *{cur_hour:02d}:00*\n\n"
        f"يصلك كل صباح رسالة واحدة تحتوي:\n"
        f"  • أبرز 8 أخبار حسب لغتك\n"
        f"  • حالة الطقس (إذا ضبطت مدينتك)\n"
        f"  • أوقات الصلاة\n\n"
        f"اختر من الأزرار أدناه:"
    )
    markup = types.InlineKeyboardMarkup(row_width=2)
    toggle_lbl = "🔴 تعطيل الملخص" if enabled else "🟢 تفعيل الملخص"
    markup.add(types.InlineKeyboardButton(toggle_lbl, callback_data="digest_toggle"))
    markup.add(types.InlineKeyboardButton("━━━━ اختر وقت الإرسال ━━━━", callback_data="noop"))
    # أزرار الساعات 5 ← 12
    hours_row1 = [5, 6, 7, 8, 9, 10, 11, 12]
    btns1 = [types.InlineKeyboardButton(
        f"{'◀️' if h == cur_hour else ''}{h:02d}:00",
        callback_data=f"digest_hour_{h}"
    ) for h in hours_row1]
    markup.add(*btns1[:4])
    markup.add(*btns1[4:])
    bot.send_message(uid, msg, parse_mode="Markdown", reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data == "digest_toggle")
def cb_digest_toggle_cmd(call):
    bot.answer_callback_query(call.id)
    uid     = call.from_user.id
    uid_str = str(uid)
    if uid_str not in users: return
    current = users[uid_str].get("digest_mode", False)
    users[uid_str]["digest_mode"] = not current
    _db_save_user(uid, users[uid_str])
    new_state = "✅ تم تفعيل الملخص الصباحي!" if not current else "❌ تم تعطيل الملخص الصباحي."
    bot.answer_callback_query(call.id, new_state, show_alert=True)
    # أعد فتح القائمة محدّثة
    try:
        bot.delete_message(uid, call.message.message_id)
    except Exception as _exc:
        _log_exc(_exc)
    cmd_digest(call.message)

@bot.callback_query_handler(func=lambda c: c.data.startswith("digest_hour_"))
def cb_digest_hour(call):
    uid     = call.from_user.id
    uid_str = str(uid)
    if uid_str not in users:
        bot.answer_callback_query(call.id); return
    try:
        hour = int(call.data.split("digest_hour_")[1])
    except Exception:
        bot.answer_callback_query(call.id); return
    users[uid_str]["notif_hour"]  = hour
    users[uid_str]["digest_mode"] = True          # تفعيل تلقائي عند اختيار وقت
    _db_save_user(uid, users[uid_str])
    bot.answer_callback_query(call.id, f"✅ سيصلك الملخص الساعة {hour:02d}:00 كل يوم!", show_alert=True)
    try:
        bot.delete_message(uid, call.message.message_id)
    except Exception as _exc:
        _log_exc(_exc)
    cmd_digest(call.message)


# ======== /bookmarks — اختصار لـ /saved ========
