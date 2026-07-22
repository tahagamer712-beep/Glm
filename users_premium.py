# -*- coding: utf-8 -*-
"""
  users_premium.py — is_premium + has_feature + قائمة الميزات

  يُصدِّر نظام الميزات المميزة والاشتراكات.
  """

import sys as _sys_legacy
import os
# ─── استيراد كل المتغيرات العالمية من bot_legacy ───
from bot_legacy import *
import state as gl  # noqa: F401,F403

def is_premium(uid):
    """
    يتحقق فعلياً من أن المستخدم مميز.
    مصادر الميزة: premium_users في stats، أو users[uid]["premium_until"] لم يتجاوز اليوم.
    الأدمن دائماً مميز.
    """
    if is_admin(uid):
        return True
    # طريقة 1: قائمة premium_users
    if int(uid) in stats.get("premium_users", []):
        return True
    # طريقة 2: تاريخ انتهاء الاشتراك
    user = users.get(str(uid), {})
    prem_until = user.get("premium_until")
    if prem_until:
        try:
            exp = datetime.datetime.fromisoformat(str(prem_until))
            if datetime.datetime.now() < exp:
                return True
        except Exception as _exc:
            _log_exc(_exc)
    return False


def has_feature(uid, feature):
    """
    يتحقق من أن المستخدم يملك صلاحية الوصول لهذه الميزة
    بناءً على الـ mode في _FEATURE_REGISTRY.
    """
    if is_admin(uid):
        return True
    reg = _FEATURE_REGISTRY.get(feature, {})
    mode = reg.get("mode", "free")
    if mode == "free":
        return True
    if mode == "premium_only":
        return is_premium(uid)
    # limited → الجميع يملكه (الحد يُطبّق في _check_and_consume_feature)
    return True

# ======== ميزات الإحالة ========
REFERRAL_FEATURES = {
    "prem_7day":           "📅 توقعات طقس 7 أيام",
    "prem_hourly":         "⚡ أخبار فورية كل ساعة",
    "prem_addcity":        "🏙 إضافة مدينة إضافية",
    "prem_mycities":       "🗂 عرض مدنك المحفوظة",
    "prem_interests":      "🎯 أخبار حسب اهتماماتك",
    "prem_currency_alert": "💱 تنبيه سعر العملة",
    "prem_currency_table": "📊 جدول العملات الكامل",
    "prem_notif_time":     "🕐 وقت إشعار مخصص",
    "prem_weekly":         "📋 ملخص أسبوعي",
    "prem_keywords":       "🔑 تنبيه كلمات مفتاحية",
}
REFERRAL_MILESTONES = [5, 10, 15, 20, 25]

def send_feature_choice_menu(uid):
    user = users.get(str(uid), {})
    unlocked = user.get("unlocked_features", [])
    markup = types.InlineKeyboardMarkup(row_width=1)
    for feat_key, feat_name in REFERRAL_FEATURES.items():
        if feat_key not in unlocked:
            markup.add(types.InlineKeyboardButton(feat_name, callback_data=f"ref_feature_{feat_key}"))
    if not markup.keyboard:
        bot.send_message(uid, "✅ لقد فتحت جميع الميزات المتاحة بالفعل!")
        return
    bot.send_message(uid,
        "🎁 *اختر ميزة مميزة واحدة تريد فتحها:*\n"
        "━━━━━━━━━━━━━━\n"
        "الميزة المختارة ستكون متاحة لك دائماً مجاناً.",
        parse_mode="Markdown",
        reply_markup=markup
    )

# ======== لوحة تحكم الأدمن ========
def premium_callbacks(call):
    uid = call.from_user.id
    data = call.data
    bot.answer_callback_query(call.id)

    if data == "premium_menu":
        send_premium_menu(uid)
        return

    elif data.startswith("req_premium_"):
        requester_id = data.split("_")[-1]
        user = users.get(str(uid), {})
        name = user.get("name", "مجهول")
        lang = user.get("lang", "-")
        all_admins = [ADMIN_ID] + extra_admins
        for admin_id in all_admins:
            try:
                bot.send_message(admin_id,
                    f"⭐ *طلب اشتراك مميز*\n\n"
                    f"👤 الاسم: {name}\n"
                    f"🆔 ID: `{requester_id}`\n"
                    f"🗣 اللغة: {lang}\n\n"
                    f"لترقيته: /admin ← المستخدمون ← ترقية لمميز",
                    parse_mode="Markdown"
                )
            except Exception as _exc:
                _log_exc(_exc)
        bot.send_message(uid, "✅ تم إرسال طلبك للإدارة. سيتم التواصل معك قريباً.")
        return

    # الاهتمامات مجانية للجميع — لا تحتاج اشتراكاً مميزاً
    if data == "prem_interests":
        send_interest_menu(uid)
        return

    if not has_feature(uid, data):
        ref_count = len(users.get(str(uid), {}).get("referrals", []))
        next_milestone = next((m for m in REFERRAL_MILESTONES if m > ref_count), None)
        remaining = (next_milestone - ref_count) if next_milestone else 0
        bot.send_message(uid,
            "⭐ *هذه الميزة للمشتركين المميزين فقط.*\n\n"
            "💡 *يمكنك الحصول عليها مجاناً:*\n"
            "• دعوة 5 أصدقاء ← ميزة مجانية\n"
            "• دعوة 10 أصدقاء ← ميزتان مجانيتان\n"
            "• دعوة 25 صديق ← اشتراك مميز كامل شهر!\n\n"
            + (f"📊 دعواتك: `{ref_count}` — تحتاج `{remaining}` دعوة للمكافأة القادمة\n\n" if next_milestone else f"📊 دعواتك: `{ref_count}`\n\n")
            + "🔗 رابط دعوتك في قائمة *دعواتي*",
            parse_mode="Markdown"
        )
        return

    if data == "prem_7day":
        send_7day_forecast(uid)

    elif data == "prem_addcity":
        msg = bot.send_message(uid, "🏙 أرسل اسم المدينة التي تريد إضافتها (بالإنجليزي):")
        bot.register_next_step_handler(msg, lambda m: add_extra_city(m.from_user.id, m.text.strip()))

    elif data == "prem_interests":
        send_interest_menu(uid)

    elif data == "prem_currency_alert":
        user = users.get(str(uid), {})
        lang = user.get("lang", "English 🇬🇧")
        local_code, local_name = CURRENCY_MAP.get(lang, ("EUR", "Euro"))
        msg = bot.send_message(uid, f"💱 أرسل السعر المستهدف للدولار مقابل {local_name}:\n(مثال: 1600)")
        bot.register_next_step_handler(msg, set_currency_alert_step)

    elif data == "prem_notif_time":
        msg = bot.send_message(uid, "🕐 أرسل الساعة التي تريد استلام الملخص الصباحي فيها (0-23):\n(مثال: 8 للساعة 8 صباحاً)")
        bot.register_next_step_handler(msg, set_notif_time_step)

    elif data == "prem_hourly":
        send_hourly_weather_forecast(uid)

    elif data == "prem_mycities":
        user = users.get(str(uid), {})
        cities = [user.get("province", "")] + user.get("extra_cities", [])
        cities = [c for c in cities if c]
        if not cities:
            bot.send_message(uid, "⚠️ لا توجد مدن محفوظة.")
        else:
            msg = "🏙 *مدنك المحفوظة:*\n\n"
            for i, city in enumerate(cities):
                label = "(رئيسية)" if i == 0 else ""
                msg += f"  {i+1}. {city} {label}\n"
            bot.send_message(uid, msg, parse_mode="Markdown")

    elif data == "prem_currency_table":
        send_full_currency_table(uid)

    elif data == "prem_weekly":
        send_weekly_news_summary(uid)

    elif data == "prem_keywords":
        kws = user_keywords.get(str(uid), [])
        if kws:
            kw_list = "\n".join(f"• {k}" for k in kws)
            bot.send_message(uid,
                f"🔑 *كلماتك المفتاحية الحالية:*\n{kw_list}\n\n"
                "أرسل كلمة جديدة لإضافتها أو أرسل 'حذف كلمة' لحذفها:",
                parse_mode="Markdown"
            )
        else:
            bot.send_message(uid,
                "🔑 *تنبيه الكلمات المفتاحية*\n\n"
                "أرسل كلمات تريد تتبعها مفصولة بفاصلة:\n"
                "مثال: رواتب, ميسي, عطلة رسمية\n\n"
                "عند ظهور أي كلمة في خبر ستصلك تنبيه فوري! 🔔",
                parse_mode="Markdown"
            )
        user_states[uid] = "adding_keyword"

    elif data.startswith("interest_") and data != "interest_save":
        opt = data[len("interest_"):]
        user = users.get(str(uid), {})
        interests = user.get("interests", [])
        if opt in interests:
            interests.remove(opt)
        else:
            interests.append(opt)
        users[str(uid)]["interests"] = interests
        _db_save_all_users(users)
        send_interest_menu(uid)

    elif data == "interest_save":
        interests = users.get(str(uid), {}).get("interests", [])
        if interests:
            bot.send_message(uid, "✅ تم حفظ اهتماماتك:\n" + "\n".join(interests))
        else:
            bot.send_message(uid, "✅ لا توجد اهتمامات محددة — ستصلك جميع الأخبار.")


def send_premium_upgrade(uid):
    user = users.get(str(uid))
    lang = user.get("lang", "English 🇬🇧") if user else "English 🇬🇧"
    msg = PREMIUM_UPGRADE_MSG.get(lang, PREMIUM_UPGRADE_MSG["English 🇬🇧"])
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton(t(lang, "premium_subscribe_btn"), callback_data=f"req_premium_{uid}"))
    bot.send_message(uid, msg, parse_mode="Markdown", reply_markup=markup)

def send_premium_menu(uid):
    user = users.get(str(uid))
    lang = user.get("lang", "English 🇬🇧") if user else "English 🇬🇧"
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton(t(lang, "premium_btn_7day"), callback_data="prem_7day"),
        types.InlineKeyboardButton(t(lang, "premium_btn_hourly"), callback_data="prem_hourly"),
        types.InlineKeyboardButton(t(lang, "premium_btn_addcity"), callback_data="prem_addcity"),
        types.InlineKeyboardButton(t(lang, "premium_btn_mycities"), callback_data="prem_mycities"),
        types.InlineKeyboardButton(t(lang, "premium_btn_interests"), callback_data="prem_interests"),
        types.InlineKeyboardButton(t(lang, "premium_btn_currency_alert"), callback_data="prem_currency_alert"),
        types.InlineKeyboardButton(t(lang, "premium_btn_currency_table"), callback_data="prem_currency_table"),
        types.InlineKeyboardButton(t(lang, "premium_btn_notif_time"), callback_data="prem_notif_time"),
        types.InlineKeyboardButton(t(lang, "premium_btn_weekly"), callback_data="prem_weekly"),
        types.InlineKeyboardButton(t(lang, "premium_btn_keywords"), callback_data="prem_keywords"),
    )
    bot.send_message(uid, t(lang, "premium_menu_header"), parse_mode="Markdown", reply_markup=markup)

def _refresh_feature_flags():
    """يجلب كل الميزات من الداشبورد ويخزّنها في الكاش."""
    global _feature_flags_cache, _feature_flags_ts
    dash_url = os.getenv("DASHBOARD_API_URL", "").rstrip("/")
    if not dash_url:
        return
    try:
        r = requests.get(f"{dash_url}/api/features", timeout=5)
        if r.status_code == 200:
            data = r.json()            # list[{key, enabled, premiumOnly, ...}]
            _feature_flags_cache = {
                f["key"]: {"enabled": f["enabled"], "premiumOnly": f["premiumOnly"]}
                for f in data
            }
            _feature_flags_ts = time.time()
            _logger.debug(f"Feature flags refreshed: {len(_feature_flags_cache)} keys")
    except Exception as e:
        _logger.debug(f"Feature flags fetch error: {e}")

def _is_feature_enabled(key: str, uid=None) -> bool:
    """
    يتحقق إذا الميزة مفعّلة.
    - إذا premiumOnly=True و uid معطى → يتحقق من premium المستخدم
    - إذا الداشبورد غير مربوط → يعيد True (الافتراضي آمن)
    - الكاش يُحدّث كل 5 دقائق
    """
    # لا يوجد داشبورد → الميزات كلها متاحة
    if not os.getenv("DASHBOARD_API_URL", ""):
        return True
    # تحديث الكاش عند الحاجة
    if time.time() - _feature_flags_ts > _FEATURE_FLAGS_TTL:
        _AI_EXECUTOR.submit(_refresh_feature_flags)
        # إذا الكاش فارغ تماماً → انتظر ثانية واحدة للبيانات الأولى
        if not _feature_flags_cache:
            import time as _t; _t.sleep(1)
    flag = _feature_flags_cache.get(key)
    if flag is None:
        return True   # ميزة غير معروفة → مسموح بها افتراضياً
    if not flag["enabled"]:
        return False
    if flag["premiumOnly"] and uid is not None:
        user = users.get(str(uid), {})
        return bool(user.get("premium") or user.get("is_premium"))
    return True

def _feature_blocked_msg(uid, key: str) -> str:
    """يرجع رسالة الرفض المناسبة حسب لغة المستخدم."""
    user = users.get(str(uid), {})
    lang = user.get("lang", "العربية 🇮🇶")
    flag = _feature_flags_cache.get(key, {})
    if not flag.get("enabled", True):
        return _ui("feature_disabled", lang)
    if flag.get("premiumOnly"):
        return _ui("premium_only_msg", lang)
    return _ui("feature_disabled", lang)

# ======================================================
# ميزة: تجميع القصص المتكررة (Story Clustering)
# قصة واحدة من عدة مصادر → رسالة موحدة مع عداد المصادر
# ======================================================
def cmd_grantpremium(m):
    """
    /grantpremium <uid> [أيام]
    يمنح المستخدم اشتراكاً مميزاً.
    مثال: /grantpremium 123456789 30
    """
    uid = m.from_user.id
    if not is_admin(uid):
        return

    parts = m.text.strip().split()
    if len(parts) < 2 or not parts[1].isdigit():
        bot.send_message(uid,
            "📝 *استخدام:*\n`/grantpremium <uid> [أيام]`\n\n"
            "مثال: `/grantpremium 123456789 30` (30 يوماً)\n"
            "مثال: `/grantpremium 123456789` (دائم)",
            parse_mode="Markdown")
        return

    target_uid = int(parts[1])
    days = int(parts[2]) if len(parts) >= 3 and parts[2].isdigit() else None

    # إضافة للقائمة الدائمة
    prem_list = stats.setdefault("premium_users", [])
    if target_uid not in prem_list:
        prem_list.append(target_uid)

    # إضافة تاريخ انتهاء إذا حُدّدت أيام
    if days:
        until = (datetime.datetime.now() + datetime.timedelta(days=days)).isoformat()
        users.setdefault(str(target_uid), {})["premium_until"] = until
        save_users()
        save_stats()
        bot.send_message(uid,
            f"✅ تم منح المستخدم `{target_uid}` اشتراكاً مميزاً لمدة *{days} يوماً*.",
            parse_mode="Markdown")
    else:
        save_stats()
        bot.send_message(uid,
            f"✅ تم منح المستخدم `{target_uid}` اشتراكاً مميزاً *دائماً*.",
            parse_mode="Markdown")

    # إشعار المستخدم
    try:
        msg = (
            "⭐ *مبروك! حصلت على اشتراك مميز*\n━━━━━━━━━━━━━━\n\n"
            + ("\n".join(f"✅ {v['label']}" for v in _FEATURE_REGISTRY.values()))
            + "\n\n_أرسل /subscribe لعرض مميزاتك_"
        )
        bot.send_message(target_uid, msg, parse_mode="Markdown")
    except Exception as _exc:
        _log_exc(_exc)


@bot.message_handler(commands=["revokepremium"])
def cmd_revokepremium(m):
    """
    /revokepremium <uid>
    يسحب الاشتراك المميز من مستخدم.
    """
    uid = m.from_user.id
    if not is_admin(uid):
        return

    parts = m.text.strip().split()
    if len(parts) < 2 or not parts[1].isdigit():
        bot.send_message(uid,
            "📝 *استخدام:*\n`/revokepremium <uid>`",
            parse_mode="Markdown")
        return

    target_uid = int(parts[1])
    prem_list  = stats.get("premium_users", [])
    if target_uid in prem_list:
        prem_list.remove(target_uid)
        stats["premium_users"] = prem_list
        save_stats()

    user_data = users.get(str(target_uid), {})
    if "premium_until" in user_data:
        del user_data["premium_until"]
        save_users()

    bot.send_message(uid,
        f"✅ تم سحب الاشتراك المميز من المستخدم `{target_uid}`.",
        parse_mode="Markdown")


@bot.message_handler(commands=["premiumlist"])
def cmd_premiumlist(m):
    """يُظهر قائمة المستخدمين المميزين."""
    uid = m.from_user.id
    if not is_admin(uid):
        return

    prem_ids  = stats.get("premium_users", [])
    if not prem_ids:
        bot.send_message(uid, "📋 لا يوجد مستخدمون مميزون حالياً.")
        return

    lines = ["⭐ *المستخدمون المميزون:*\n━━━━━━━━━━━━━━"]
    for pid in prem_ids:
        u = users.get(str(pid), {})
        name  = u.get("name", "مجهول")
        until = u.get("premium_until", "دائم")
        lines.append(f"• `{pid}` — {name} — حتى: _{until}_")
    lines.append(f"\n━━━━━━━━━━━━━━\nالمجموع: *{len(prem_ids)}* مستخدم")

    bot.send_message(uid, "\n".join(lines), parse_mode="Markdown")


# ======== /compare — مقارنة مصادر متعددة لنفس الخبر ========
@bot.message_handler(commands=["subscribe"])
def cmd_subscribe(m):
    """
    يعرض خيارات الاشتراك المميز:
    - مجاني عبر دعوة الأصدقاء
    - مميز (جاهز لـ Telegram Stars عند التفعيل)
    """
    uid = m.from_user.id
    if uid in banned: return
    if bot_paused: return
    if str(uid) not in users:
        bot.send_message(uid, "⚠️ أرسل /start أولاً.")
        return

    user = users.get(str(uid), {})
    lang = user.get("lang", "العربية 🇮🇶")
    already_prem = is_premium(uid)
    ref_count    = len(user.get("referrals", []))
    ref_code     = user.get("ref_code", str(uid))
    ref_link     = f"https://t.me/{BOT_USERNAME}?start=ref_{ref_code}"
    sep = "━━━━━━━━━━━━━━"

    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("👥 دعوة صديق (احصل على ميزات مجاناً)", url=f"https://t.me/share/url?url={ref_link}&text=انضم+لأفضل+بوت+أخبار"),
        types.InlineKeyboardButton("📊 إحصاءاتي", callback_data="sub_stats"),
        types.InlineKeyboardButton("⭐ المميزات المتاحة", callback_data="sub_features"),
    )

    if already_prem:
        status_line = "✅ أنت حالياً مشترك مميز!"
    else:
        needed = 5 - (ref_count % 5) if ref_count % 5 != 0 else 5
        status_line = f"🎯 ادعُ {needed} صديق إضافي للحصول على ميزة مميزة جديدة!"

    msg = (
        f"⭐ *الاشتراك المميز*\n{sep}\n\n"
        f"{status_line}\n\n"
        f"👥 أصدقاء دعوتهم: *{ref_count}*\n"
        f"🔗 رابط دعوتك:\n`{ref_link}`\n\n"
        f"{sep}\n"
        f"*كل 5 دعوات = ميزة مميزة مجاناً*\n"
        f"*25 دعوة = شهر كامل مميز*\n"
        f"{sep}\n"
        f"_الدفع المباشر عبر Telegram Stars قادم قريباً_"
    )
    bot.send_message(uid, msg, parse_mode="Markdown", reply_markup=markup)


@bot.callback_query_handler(func=lambda c: c.data in ("sub_stats", "sub_features"))
def cb_subscribe_actions(call):
    uid  = call.from_user.id
    data = call.data
    user = users.get(str(uid), {})
    lang = user.get("lang", "العربية 🇮🇶")

    if data == "sub_stats":
        bot.answer_callback_query(call.id)
        ref_count = len(user.get("referrals", []))
        milestones_done = user.get("rewarded_milestones", [])
        next_ms = next((x for x in [5,10,15,20,25] if x not in milestones_done), None)
        left = (next_ms - ref_count) if next_ms else 0
        bot.send_message(uid,
            f"📊 *إحصاءات الإحالة*\n━━━━━━━━━━━━━━\n"
            f"👥 مجموع الإحالات: *{ref_count}*\n"
            f"🏆 المكافآت المُستلمة: {', '.join(str(x) for x in milestones_done) or 'لا يوجد بعد'}\n"
            + (f"🎯 الهدف التالي: *{next_ms}* دعوة ({left} متبقٍ)\n" if next_ms else "🌟 وصلت للمستوى الأعلى!\n"),
            parse_mode="Markdown")

    elif data == "sub_features":
        bot.answer_callback_query(call.id)
        features = [
            "📄 ملخص الخبر",
            "💡 لماذا يهمك؟",
            "🔮 ماذا بعد؟",
            "🧠 تقرير ذكي شامل",
            "📚 السياق التاريخي",
            "🔍 التحقق من الخبر",
            "🗓 خط الأحداث /storyline",
            "🔄 مقارنة المصادر /compare",
            "🎙 الموجز الإخباري /audiobriefing",
            "🌍 ترجمة تلقائية",
            "🔑 تنبيهات الكلمات المفتاحية",
            "📆 ملخص أسبوعي",
        ]
        bot.send_message(uid,
            "⭐ *المميزات المتاحة:*\n━━━━━━━━━━━━━━\n" +
            "\n".join(f"✅ {f}" for f in features),
            parse_mode="Markdown")


# ╔══════════════════════════════════════════════════════════════════════╗
# ║              InsightX FULL FEATURE SUITE — v5.0                     ║
# ║  26 ميزة جديدة: استقرار + أدمن + مستخدم + مميز + AI + مونيتايزيشن  ║
# ╚══════════════════════════════════════════════════════════════════════╝

# ─────────────────────────────────────────────────────────────────────────
# §1  STABILITY — بنية الاستقرار الفائق
# ─────────────────────────────────────────────────────────────────────────

# ── 1a. Circuit Breaker لـ Gemini AI ──────────────────────────────────────
_cb_fail_count: int = 0
_cb_open_until: float = 0.0
_cb_lock = threading.Lock()
_CB_MAX_FAILS   = 5      # عدد الفشل قبل الفتح
_CB_COOLDOWN    = 600    # ثواني الإغلاق (10 دقائق)
