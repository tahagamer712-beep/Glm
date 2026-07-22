# -*- coding: utf-8 -*-
"""
  users_referral.py — نظام الإحالات + المكافآت

  يُصدِّر نظام الإحالات والمكافآت.
  """

import sys as _sys_legacy
import os
# ─── استيراد كل المتغيرات العالمية من bot_legacy ───
from bot_legacy import *
import state as gl  # noqa: F401,F403

def check_referral_rewards(referrer_id, new_member_name=""):
    uid_str = str(referrer_id)
    user = users.get(uid_str)
    if not user:
        return
    ref_count = len(user.get("referrals", []))
    rewarded = user.setdefault("rewarded_milestones", [])
    for milestone in REFERRAL_MILESTONES:
        if ref_count >= milestone and milestone not in rewarded:
            rewarded.append(milestone)
            users[uid_str]["rewarded_milestones"] = rewarded
            _db_save_all_users(users)
            if milestone == 25:
                expiry = datetime.datetime.now() + datetime.timedelta(days=30)
                users[uid_str]["ref_premium_expiry"] = expiry.isoformat()
                _db_save_all_users(users)
                try:
                    bot.send_message(
                        referrer_id,
                        "🎊 *تهانينا! وصلت إلى 25 دعوة!*\n\n"
                        "🌟 حصلت على *اشتراك مميز كامل لمدة شهر* مجاناً!\n"
                        "━━━━━━━━━━━━━━\n"
                        "📅 الاشتراك ساري لمدة 30 يوم\n"
                        "✨ استمتع بجميع الميزات المميزة!",
                        parse_mode="Markdown"
                    )
                except Exception as _exc:
                    _log_exc(_exc)
            else:
                try:
                    bot.send_message(
                        referrer_id,
                        f"🎉 *تهانينا! وصلت إلى {milestone} دعوة!*\n\n"
                        f"🎁 ربحت *ميزة مميزة مجانية* — اختر الميزة التي تريدها:",
                        parse_mode="Markdown"
                    )
                    send_feature_choice_menu(referrer_id)
                except Exception as _exc:
                    _log_exc(_exc)
            break

def ref_feature_callback(call):
    uid = call.from_user.id
    data = call.data
    bot.answer_callback_query(call.id)
    feat_key = data.replace("ref_feature_", "")
    if feat_key not in REFERRAL_FEATURES:
        return
    user = users.get(str(uid), {})
    lang = user.get("lang", "English 🇬🇧")
    unlocked = user.setdefault("unlocked_features", [])
    if feat_key in unlocked:
        bot.send_message(uid, _ui("feature_already_unlocked", lang))
        return
    unlocked.append(feat_key)
    users[str(uid)]["unlocked_features"] = unlocked
    _db_save_all_users(users)
    feat_name = REFERRAL_FEATURES[feat_key]
    _unlock_ok = {
        "العربية 🇮🇶":   f"✅ *تم فتح الميزة بنجاح!*\n\n🎁 *{feat_name}*\n\nيمكنك استخدامها الآن من /help.",
        "English 🇬🇧":   f"✅ *Feature unlocked!*\n\n🎁 *{feat_name}*\n\nUse /help to see all features.",
        "Русский 🇷🇺":   f"✅ *Функция разблокирована!*\n\n🎁 *{feat_name}*\n\nИспользуйте /help.",
        "فارسی 🇮🇷":     f"✅ *ویژگی باز شد!*\n\n🎁 *{feat_name}*\n\nاز /help استفاده کنید.",
        "Türkçe 🇹🇷":    f"✅ *Özellik açıldı!*\n\n🎁 *{feat_name}*\n\n/help ile tüm özellikleri görün.",
        "Deutsch 🇩🇪":   f"✅ *Funktion freigeschaltet!*\n\n🎁 *{feat_name}*\n\nNutze /help für alle Funktionen.",
        "Español 🇲🇽":   f"✅ *¡Función desbloqueada!*\n\n🎁 *{feat_name}*\n\nUsa /help para ver todo.",
        "Français 🇫🇷":  f"✅ *Fonctionnalité débloquée!*\n\n🎁 *{feat_name}*\n\nUtilisez /help.",
    }
    bot.send_message(uid, _unlock_ok.get(lang, _unlock_ok["English 🇬🇧"]), parse_mode="Markdown")

@bot.callback_query_handler(func=lambda c: c.data.startswith("prem_") or c.data.startswith("req_premium_") or c.data.startswith("interest_") or c.data == "premium_menu")
def send_top_referrers(uid):
    user = users.get(str(uid))
    lang = user.get("lang", "English 🇬🇧") if user else "English 🇬🇧"
    referral_counts = []
    for user_id, info in list(users.items()):
        refs = info.get("referrals", [])
        if refs:
            name = info.get("name", t(lang, "my_stats_user"))
            referral_counts.append((name, len(refs)))
    referral_counts.sort(key=lambda x: x[1], reverse=True)
    top = referral_counts[:10]
    if not top:
        bot.send_message(uid, t(lang, "top_referrers_empty"))
        return
    medals = ["🥇", "🥈", "🥉"] + ["4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
    invite_word = t(lang, "top_referrers_invite")
    msg = t(lang, "top_referrers_header")
    for i, (name, count) in enumerate(top):
        medal = medals[i] if i < len(medals) else f"{i+1}."
        msg += f"{medal} *{name}* — {count} {invite_word}\n"
    bot.send_message(uid, msg, parse_mode="Markdown")

# ======== تنظيف البيانات التلقائي (Auto-Clean) ========
def send_referral_stats(uid):
    user = users.get(str(uid))
    if not user:
        return
    lang = user.get("lang", "العربية 🇮🇶")
    ref_count = len(user.get("referrals", []))
    invite_link = f"https://t.me/{BOT_USERNAME}?start=ref_{uid}"
    msg = st(lang, "referral_header").format(link=invite_link, count=ref_count)
    markup = types.InlineKeyboardMarkup()
    share_url = f"https://t.me/share/url?url={invite_link}&text=📱 @{BOT_USERNAME}"
    markup.add(types.InlineKeyboardButton(st(lang, "referral_share_btn"), url=share_url))
    bot.send_message(uid, msg, parse_mode="Markdown", reply_markup=markup)

# ======== انشر البوت ========
def send_share_bot(uid):
    user = users.get(str(uid))
    lang = user.get("lang", "English 🇬🇧") if user else "English 🇬🇧"
    invite_link = f"https://t.me/{BOT_USERNAME}"
    msg = t(lang, "share_bot_header").format(username=BOT_USERNAME, link=invite_link)
    markup = types.InlineKeyboardMarkup()
    share_url = f"https://t.me/share/url?url={invite_link}&text=@{BOT_USERNAME}"
    markup.add(
        types.InlineKeyboardButton(t(lang, "share_bot_btn"), url=share_url),
        types.InlineKeyboardButton(t(lang, "open_bot_btn"), url=invite_link)
    )
    bot.send_message(uid, msg, parse_mode="Markdown", reply_markup=markup)

# ======== إحصائيات البوت العامة ========
@bot.message_handler(commands=["referral", "invite", "ref"])
def cmd_referral(m):
    uid = m.from_user.id
    if uid in banned: return
    uid_str = str(uid)
    if uid_str not in users:
        bot.send_message(uid, "⚠️ أرسل /start أولاً."); return

    lang = users[uid_str].get("lang", "العربية 🇮🇶")
    try:
        me = bot.get_me()
        bot_username = me.username
    except Exception:
        bot_username = "Iraqnowbot"

    ref_link = f"https://t.me/{bot_username}?start=ref_{uid}"
    user_data  = users[uid_str]
    ref_count  = len(user_data.get("referrals", []))
    rewarded   = user_data.get("rewarded_milestones", [])

    # أقرب مرحلة قادمة
    next_m = next((m_ for m_ in REFERRAL_MILESTONES if m_ > ref_count), None)
    progress = f"🎯 {next_m - ref_count} دعوة أخرى للمكافأة القادمة!" if next_m else "🏆 وصلت لأعلى مستوى!"

    # مراحل المكافآت
    milestones_txt = ""
    for ms in REFERRAL_MILESTONES:
        done = "✅" if ms in rewarded else ("▶️" if ms == next_m else "⬜")
        reward = "شهر مميز مجاناً ⭐" if ms == 25 else "ميزة مميزة 🎁"
        milestones_txt += f"  {done} {ms} دعوة → {reward}\n"

    msg = (
        f"🎁 *نظام الدعوات*\n"
        f"━━━━━━━━━━━━━━\n\n"
        f"🔗 *رابط دعوتك الخاص:*\n"
        f"`{ref_link}`\n\n"
        f"👥 *إجمالي من دعوتهم:* `{ref_count}` شخص\n"
        f"{progress}\n\n"
        f"━━━━━━━━━━━━━━\n"
        f"🏅 *مراحل المكافآت:*\n{milestones_txt}\n"
        f"📤 شارك الرابط مع أصدقائك — كل شخص ينضم عبر رابطك يُحتسب لك!"
    )
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton(
            "📤 شارك الرابط الآن",
            url=f"https://t.me/share/url?url={ref_link}&text=انضم+لبوت+الأخبار+الذكي+InsightX"
        ),
        types.InlineKeyboardButton("👥 من دعوتهم؟", callback_data="ref_show_list"),
    )
    bot.send_message(uid, msg, parse_mode="Markdown", reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data == "ref_show_list")
def cb_ref_show_list(call):
    uid     = call.from_user.id
    uid_str = str(uid)
    bot.answer_callback_query(call.id)
    refs = users.get(uid_str, {}).get("referrals", [])
    if not refs:
        bot.send_message(uid, "👥 لم تدعُ أحداً بعد.")
        return
    lines = ["👥 *من دعوتهم:*\n━━━━━━━━"]
    for i, r_id in enumerate(refs[-20:], 1):
        name = users.get(str(r_id), {}).get("name", str(r_id))
        lines.append(f"  {i}. {name}")
    if len(refs) > 20:
        lines.append(f"\n  ... و{len(refs)-20} آخرين")
    bot.send_message(uid, "\n".join(lines), parse_mode="Markdown")


# ======== /digest — ضبط الملخص الصباحي ========
