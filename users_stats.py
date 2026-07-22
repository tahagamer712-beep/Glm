# -*- coding: utf-8 -*-
"""
  users_stats.py — إحصائيات الاستخدام + update_stats

  يُصدِّر دوال إحصائيات المستخدمين.
  """

import sys as _sys_legacy
import os
# ─── استيراد كل المتغيرات العالمية من bot_legacy ───
from bot_legacy import *
import state as gl  # noqa: F401,F403

def update_stats(action, uid=None, country=None, lang=None, button=None):
    with _stats_lock:
        today = str(datetime.date.today())
    if action == "new_user":
        stats["total_users"] = stats.get("total_users", 0) + 1
        stats["daily_users"][today] = stats["daily_users"].get(today, 0) + 1
        if lang:
            stats["languages_count"][lang] = stats["languages_count"].get(lang, 0) + 1
        if country:
            stats["countries_count"][country] = stats["countries_count"].get(country, 0) + 1
        total = stats["total_users"]
        if total in [100, 500, 1000, 5000, 10000]:
            all_admins = [ADMIN_ID] + extra_admins
            for admin_id in all_admins:
                try:
                    bot.send_message(admin_id, f"🎉 وصلت {total} مستخدم!")
                except Exception as _exc:
                    _log_exc(_exc)
    elif action == "button":
        if button:
            stats["button_presses"][button] = stats["button_presses"].get(button, 0) + 1
    save_json(STATS_FILE, stats)

# ======== دوال المميز ========
def send_my_stats(uid):
    user = users.get(str(uid))
    if not user:
        return
    lang = user.get("lang", "English 🇬🇧")
    name = user.get("name", t(lang, "my_stats_user"))
    province = user.get("province", "—")
    sent_news = user.get("sent_news", {})
    referrals = user.get("referrals", [])
    is_prem = t(lang, "my_stats_prem_yes") if is_premium(uid) else t(lang, "my_stats_prem_no")
    notif = t(lang, "my_stats_notif_on") if user.get("notifications", True) else t(lang, "my_stats_notif_off")
    join_date = user.get("join_date", "—")
    kws = user_keywords.get(str(uid), [])
    msg = t(lang, "my_stats_header").format(
        name=name, lang=lang, city=province, join=join_date,
        news=len(sent_news), refs=len(referrals), kws=len(kws),
        prem=is_prem, notif=notif
    )
    bot.send_message(uid, msg, parse_mode="Markdown")

# ======== توقعات 3 أيام (مجانية) ========
@bot.callback_query_handler(func=lambda c: c.data == "settings_mystats")
def cb_settings_mystats(call):
    bot.answer_callback_query(call.id)
    _show_mystats(call.from_user.id)


# ملاحظة: أمر /mystats الحقيقي مسجَّل في handler_callbacks.cmd_mystats الذي
# يستدعي هذه الدالة بـ uid صحيح. كان هنا ديكوريتر @bot.message_handler
# زائد يجعل تيليبوت يستدعيها مباشرة بكائن Message بدل uid، فتتكسر.
def _show_mystats(uid):
    user = users.get(str(uid), {})
    if not user:
        bot.send_message(uid, "⚠️ أرسل /start أولاً.")
        return
    lang          = user.get("lang", "—")
    city          = user.get("province", "—")
    joined        = user.get("joined", "—")
    total_sent    = user.get("total_news_received", 0)
    rated_pos     = user.get("rated_positive", 0)
    rated_neg     = user.get("rated_negative", 0)
    total_rated   = rated_pos + rated_neg
    fav_topics    = user.get("interests", [])
    searches      = user.get("total_searches", 0)
    streak_days   = user.get("reading_streak", 0)
    last_active   = user.get("last_active", "—")
    custom_sched  = user.get("custom_schedule", [])
    sched_txt     = ", ".join(f"{h}:00" for h in sorted(custom_sched)) if custom_sched else "24/7 🟢"
    digest_on     = user.get("digest_mode", False)
    followed      = user.get("followed_stories", [])
    # حساب نسبة الإيجابية
    if total_rated > 0:
        pos_pct = round(rated_pos / total_rated * 100)
        rating_txt = f"{rated_pos}👍 {rated_neg}👎 ({pos_pct}% إيجابية)"
    else:
        rating_txt = "لم تقيّم بعد"
    topics_txt = ", ".join(fav_topics[:5]) if fav_topics else "لم تُحدَّد"
    msg = (
        f"📊 *إحصائياتك الشخصية*\n"
        f"━━━━━━━━━━━━━━━\n"
        f"🌍 اللغة: `{lang}`\n"
        f"🌆 المدينة: `{city}`\n"
        f"📅 تاريخ الانضمام: `{joined}`\n"
        f"━━━━━━━━━━━━━━━\n"
        f"📰 أخبار استقبلتها: *{total_sent:,}*\n"
        f"⭐ التقييمات: {rating_txt}\n"
        f"🔍 عمليات البحث: *{searches}*\n"
        f"🔥 أيام المتابعة: *{streak_days}* يوم\n"
        f"━━━━━━━━━━━━━━━\n"
        f"📌 اهتماماتك: {topics_txt}\n"
        f"🕐 جدول الاستلام: {sched_txt}\n"
        f"{'📰' if digest_on else '📄'} الدايجست: {'✅' if digest_on else '❌'}\n"
        f"🔔 قصص تتابعها: *{len(followed)}*\n"
        f"━━━━━━━━━━━━━━━\n"
        f"🕒 آخر نشاط: `{last_active}`"
    )
    bot.send_message(uid, msg, parse_mode="Markdown")


# ======== إعدادات مستوى التنبيه ========
